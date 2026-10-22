import os
import json
import sys
import shutil
import subprocess
from pathlib import Path

from PIL import Image

# Config
GIF_QUALITY = 80
WEBP_METHOD = 0
RASTER_TO_WEBP = {".gif", ".png", ".jpg", ".jpeg", ".bmp"}
VIDEO_TO_WEBM = {".mov, .mp4"}
KEEP_EXTENSIONS = {".webp", ".webm", ".svg"}
INDEX_EXTENSIONS = RASTER_TO_WEBP | VIDEO_TO_WEBM | KEEP_EXTENSIONS


# Conversion helpers
def raster_to_webp(
    src: Path, dst: Path, quality: int = GIF_QUALITY, method: int = WEBP_METHOD
) -> None:
    with Image.open(src) as im:
        frames, durations = [], []
        try:
            while True:
                frame = (
                    im.convert("RGBA")
                    if im.mode in ("RGBA", "LA", "P")
                    else im.convert("RGB")
                )
                frames.append(frame.copy())
                durations.append(im.info.get("duration", 100))
                im.seek(im.tell() + 1)
        except EOFError:
            pass

        if not frames:
            raise RuntimeError("no frames found")

        # Single-frame -> plain still WebP
        if len(frames) == 1:
            frames[0].save(dst, format="WEBP", quality=quality, method=method)
            return

        frames[0].save(
            dst,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=im.info.get("loop", 0),
            quality=quality,
            method=method,
            minimize_size=False,
        )


def mov_to_webm(src: Path, dst: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH (required for .mov -> .webm)")

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "32",
        "-c:a",
        "libopus",
        "-b:a",
        "96k",
        "-loglevel",
        "error",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def convert_folder(image_folder: Path) -> tuple[int, int]:
    converted = 0
    failed = 0

    files = sorted(f for f in image_folder.iterdir() if f.is_file())

    for src in files:
        suffix = src.suffix.lower()

        if suffix in RASTER_TO_WEBP:
            dst = src.with_suffix(".webp")
            print(f"[IMG -> WebP] {src.name}")
            try:
                raster_to_webp(src, dst)
                size_kb = dst.stat().st_size / 1024
                src.unlink()  # delete original only after success
                print(f"  OK {dst.name} ({size_kb:.1f} KB)  (removed {src.name})")
                converted += 1
            except Exception as e:
                print(f"  FAILED: {e}")
                # Clean up partial output so a retry can succeed cleanly
                if dst.exists():
                    try:
                        dst.unlink()
                    except OSError:
                        pass
                failed += 1

        elif suffix in VIDEO_TO_WEBM:
            dst = src.with_suffix(".webm")
            print(f"[MOV -> WebM] {src.name}")
            try:
                mov_to_webm(src, dst)
                size_kb = dst.stat().st_size / 1024
                src.unlink()
                print(f"  OK {dst.name} ({size_kb:.1f} KB)  (removed {src.name})")
                converted += 1
            except Exception as e:
                print(f"  FAILED: {e}")
                if dst.exists():
                    try:
                        dst.unlink()
                    except OSError:
                        pass
                failed += 1

        # else: leave .webp/.webm/.mp4/.svg and anything else untouched

    return converted, failed


# Indexing
def index_memes(image_folder: Path, json_file: Path) -> None:
    existing_data = []
    if json_file.exists():
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"Loaded existing JSON with {len(existing_data)} entries")
        except json.JSONDecodeError:
            print("Warning: Existing JSON file is corrupted or empty. Starting fresh.")
            existing_data = []
    else:
        print("No existing JSON file found. Creating new one.")

    # Collect current image files
    image_files = [
        f.name
        for f in image_folder.iterdir()
        if f.is_file() and f.suffix.lower() in INDEX_EXTENSIONS
    ]
    print(f"Found {len(image_files)} meme files in folder")

    # Index existing entries by filename (last path segment)
    existing_entries = {
        entry["path"].split("/")[-1]: entry
        for entry in existing_data
        if "path" in entry
    }
    existing_filenames = set(existing_entries.keys())

    current_filenames = set(image_files)
    new_images = current_filenames - existing_filenames

    print(f"Found {len(new_images)} new files to add")

    for filename in sorted(new_images):
        nice_name = Path(filename).stem
        nice_name = nice_name.replace("_", " ").replace("-", " ")
        nice_name = " ".join(word.capitalize() for word in nice_name.split())

        new_entry = {
            "name": nice_name,
            "author": "HEAT Labs Team",
            "path": f"https://cdn5.heatlabs.net/memes/{filename}",
        }
        existing_data.append(new_entry)
        print(f"  Added: {filename} -> {nice_name}")

    existing_data.sort(key=lambda x: x.get("name", "").lower())

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully updated {json_file}")
    print(f"Total entries: {len(existing_data)}")
    if new_images:
        print(f"Added {len(new_images)} new files")
    else:
        print("No new files to add")


# Main
def main():
    script_dir = Path(__file__).parent.absolute()

    image_folder = (script_dir / "../../HEAT-Labs-Images/memes").resolve()
    json_file = (script_dir / "../../HEAT-Labs-Configs/memes.json").resolve()

    image_folder.mkdir(parents=True, exist_ok=True)
    json_file.parent.mkdir(parents=True, exist_ok=True)

    if not image_folder.exists():
        print(f"Error: Image folder not found at {image_folder}")
        sys.exit(1)

    # 1) Convert first (in-place, deleting originals on success)
    print(f"Scanning for conversions in: {image_folder}\n")
    converted, failed = convert_folder(image_folder)
    print(f"\nConversion done: {converted} converted, {failed} failed\n")

    # 2) Then index the (now-converted) folder
    print("Indexing...\n")
    index_memes(image_folder, json_file)

    # Non-zero exit if any conversion failed so CI/callers can detect it
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
