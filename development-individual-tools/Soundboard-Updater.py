import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCES = [
    Path(r"E:\Wargaming\HEAT-VFS\sounds\soundbank"),
    Path(r"E:\Wargaming\HEAT-VFS\sounds\soundbank\international"),
]
DEFAULT_OUT_DIR = (SCRIPT_DIR / "../../HEAT-Labs-Sounds/sounds").resolve()
DEFAULT_JSON = (SCRIPT_DIR / "../../HEAT-Labs-Configs/sounds.json").resolve()
STATE_FILE = SCRIPT_DIR / ".soundbank_state.json"
CDN_BASE = "https://cdn3.heatlabs.net/sounds"
AUDIO_EXT = ".webm"
VGMSTREAM_PATH = "modules/vgmstream"
FFMPEG_PATH = "modules/ffmpeg"


# BNK parsing
def extract_wems(bnk_path: Path):
    data = bnk_path.read_bytes()
    pos = 0
    index = []
    data_start = None

    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        body = pos + 8
        if tag == b"DIDX":
            for i in range(size // 12):
                index.append(struct.unpack_from("<III", data, body + i * 12))
        elif tag == b"DATA":
            data_start = body
        pos = body + size

    if not index or data_start is None:
        return []

    wems = []
    for wem_id, offset, size in index:
        start = data_start + offset
        end = start + size
        if size > 0 and end <= len(data):
            wems.append((wem_id, data[start:end]))
    return wems


# Conversion
def convert_wem(wem_bytes: bytes, dest: Path, vgmstream: str, ffmpeg: str, bitrate: str):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    with tempfile.TemporaryDirectory() as tmp:
        wem = Path(tmp) / "in.wem"
        wav = Path(tmp) / "out.wav"
        wem.write_bytes(wem_bytes)

        r = subprocess.run([vgmstream, "-o", str(wav), str(wem)], capture_output=True)
        if r.returncode != 0 or not wav.exists():
            raise RuntimeError("vgmstream failed: " + r.stderr.decode(errors="replace").strip()[-200:])

        try:
            with wave.open(str(wav)) as w:
                channels = w.getnchannels()
        except Exception:
            channels = 2

        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav),
               "-vn", "-c:a", "libopus", "-b:a", bitrate]
        if channels > 2:
            cmd += ["-ac", "2"]  # downmix surround so browsers can play it
        cmd += ["-f", "webm", str(part)]

        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0 or not part.exists():
            if part.exists():
                part.unlink()
            raise RuntimeError("ffmpeg failed: " + r.stderr.decode(errors="replace").strip()[-200:])

    os.replace(part, dest)


# Helpers
def load_json(path: Path, default):
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def pretty_name(stem: str) -> str:
    name = stem.replace("_", " ").strip()
    return name.title() if name.islower() else name


def trailing_number(sound_id: str):
    m = re.search(r"-(\d+)$", sound_id or "")
    return int(m.group(1)) if m else None


def find_tool(configured, names):
    if configured:
        p = Path(str(configured).strip().strip('"'))
        if p.is_dir():
            for n in names:
                candidate = p / n
                if candidate.is_file():
                    return str(candidate)
        elif p.is_file():
            return str(p)
        print(f"[warn] configured path not found: {p}")
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return None


def find_or_create_category(config: dict, folder: str) -> dict:
    """Match a category by the BNK it came from (fileID), so renaming a category by hand is safe."""
    for cat in config["categories"]:
        if any(it.get("fileID") == folder for it in cat.get("categoryItems", [])):
            return cat
    cat = {
        "categoryName": pretty_name(folder),
        "categoryDescription": f"Sound files from {folder}",
        "categoryItems": [],
    }
    config["categories"].append(cat)
    return cat


def collect_banks(sources):
    banks, seen = [], set()
    for src in sources:
        if not src.is_dir():
            print(f"[warn] source folder not found, skipping: {src}")
            continue
        for bnk in sorted(src.glob("*.bnk")):
            folder = bnk.stem
            if folder.lower() in seen:
                folder = f"{bnk.stem}_{src.name}"
            seen.add(folder.lower())
            banks.append((bnk, folder))
    return banks


# Main
def main():
    ap = argparse.ArgumentParser(description="Update the HEAT Labs soundboard from the game's soundbanks.")
    ap.add_argument("--sources", nargs="+", type=Path, default=DEFAULT_SOURCES, help="folders containing .bnk files")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR, help="output folder for converted audio")
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON, help="path of sounds.json")
    ap.add_argument("--names", type=Path, help='optional JSON map {"<gameID>": "Friendly name"}')
    ap.add_argument("--vgmstream", help="path to vgmstream-cli")
    ap.add_argument("--ffmpeg", help="path to ffmpeg")
    ap.add_argument("--bitrate", default="64k", help="opus bitrate (default 64k)")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="parallel conversions")
    ap.add_argument("--force", action="store_true", help="reconvert everything")
    args = ap.parse_args()

    vgmstream = find_tool(args.vgmstream or VGMSTREAM_PATH, ["vgmstream-cli.exe", "vgmstream-cli"])
    ffmpeg = find_tool(args.ffmpeg or FFMPEG_PATH, ["ffmpeg.exe", "ffmpeg"])
    if not vgmstream:
        sys.exit("vgmstream-cli not found. Set VGMSTREAM_PATH at the top of this script "
                 "to the folder (or .exe) from vgmstream-win64.zip.")
    if not ffmpeg:
        sys.exit("ffmpeg not found. Set FFMPEG_PATH at the top of this script "
                 "to the folder (or .exe) containing ffmpeg.exe.")

    config = load_json(args.json, {"categories": []})
    config.setdefault("categories", [])
    state = load_json(STATE_FILE, {})
    names = load_json(args.names, {}) if args.names else {}

    banks = collect_banks(args.sources)
    if not banks:
        sys.exit("No .bnk files found.")
    print(f"Found {len(banks)} soundbanks.\n")

    totals = {"new": 0, "updated": 0, "skipped": 0, "failed": 0}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for bnk, folder in banks:
            wems = extract_wems(bnk)
            if not wems:
                print(f"{folder}: no embedded audio (streamed-only or empty), skipping")
                continue

            cat = find_or_create_category(config, folder)
            cat_slug = slugify(cat["categoryName"]) or slugify(folder)
            items = cat["categoryItems"]
            by_gid = {it.get("gameID"): it for it in items}

            used = [trailing_number(it.get("soundID")) for it in items]
            next_num = max([n for n in used if n] + [0]) + 1

            futures = {}
            skipped = 0

            for wem_id, blob in wems:
                gid = str(wem_id)
                sha = hashlib.sha1(blob).hexdigest()
                key = f"{folder}/{gid}"
                item = by_gid.get(gid)

                if item and trailing_number(item.get("soundID")):
                    num = trailing_number(item["soundID"])
                else:
                    num = next_num
                    next_num += 1

                dest = args.out / folder / f"{num}{AUDIO_EXT}"
                unchanged = (
                    item is not None and dest.exists()
                    and state.get(key) in (None, sha) and not args.force
                )
                if unchanged:
                    state[key] = sha
                    skipped += 1
                    continue

                fut = pool.submit(convert_wem, blob, dest, vgmstream, ffmpeg, args.bitrate)
                futures[fut] = (gid, num, key, sha, item)

            new = updated = failed = 0
            for fut in as_completed(futures):
                gid, num, key, sha, item = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    failed += 1
                    print(f"  [fail] {folder}/{gid}: {e}")
                    continue

                state[key] = sha
                if item is None:
                    friendly = names.get(gid) or f"{cat['categoryName']} Sound #{num}"
                    items.append({
                        "fileID": folder,
                        "gameID": gid,
                        "soundID": f"{cat_slug}-{num}",
                        "soundType": cat["categoryName"],
                        "soundFile": f"{CDN_BASE}/{quote(folder)}/{num}{AUDIO_EXT}",
                        "soundName": friendly,
                        "soundDescription": f"Sound file from {folder}",
                    })
                    new += 1
                else:
                    updated += 1

            items.sort(key=lambda it: trailing_number(it.get("soundID")) or 0)

            print(f"{folder}: {new} new, {updated} updated, {skipped} unchanged, {failed} failed")
            totals["new"] += new
            totals["updated"] += updated
            totals["skipped"] += skipped
            totals["failed"] += failed

            # save after every bank so progress survives a crash / Ctrl+C
            save_json(args.json, config)
            save_json(STATE_FILE, state)

    config["categories"].sort(key=lambda c: c["categoryName"].lower())
    save_json(args.json, config)
    save_json(STATE_FILE, state)

    print(f"\nDone. {totals['new']} new, {totals['updated']} updated, "
          f"{totals['skipped']} unchanged, {totals['failed']} failed.")
    print(f"Audio : {args.out}")
    print(f"JSON  : {args.json}")


if __name__ == "__main__":
    main()