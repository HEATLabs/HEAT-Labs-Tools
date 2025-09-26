from pathlib import Path
import subprocess
import sys

VIDEOS_DIR = r"../../Website-Images/tankopedia/videos"

OUTPUT_SUBFOLDER = "thumbnails"
EXT_IN = ".webm"
EXT_OUT = ".webp"


def has_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def make_thumbnail_ffmpeg(input_path: Path, output_path: Path) -> bool:
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vframes", "1", str(output_path)]
    try:
        completed = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        )
        return completed.returncode == 0 and output_path.exists()
    except Exception:
        return False


def make_thumbnail_moviepy(input_path: Path, output_path: Path) -> bool:
    try:
        from moviepy.editor import VideoFileClip
        from PIL import Image
    except Exception:
        return False

    try:
        clip = VideoFileClip(str(input_path))
        frame = clip.get_frame(1)
        img = Image.fromarray(frame)
        img.save(str(output_path), format="WEBP")
        clip.reader.close()
        if clip.audio:
            clip.audio.reader.close_proc()
        return output_path.exists()
    except Exception:
        return False


def main():
    videos_dir = Path(VIDEOS_DIR)
    if not videos_dir.exists() or not videos_dir.is_dir():
        print(f"Error: folder does not exist or is not a directory: {videos_dir}")
        sys.exit(1)

    out_dir = videos_dir / OUTPUT_SUBFOLDER
    out_dir.mkdir(exist_ok=True)

    use_ffmpeg = has_ffmpeg()
    if use_ffmpeg:
        print("Using ffmpeg for thumbnail extraction.")
    else:
        print(
            "ffmpeg not found. Will attempt fallback using moviepy + Pillow (if installed)."
        )

    files = sorted(videos_dir.iterdir())
    processed = 0
    skipped = 0

    for f in files:
        if not f.is_file():
            continue
        if f.suffix.lower() != EXT_IN:
            continue

        out_file = out_dir / (f.stem + EXT_OUT)

        if use_ffmpeg:
            ok = make_thumbnail_ffmpeg(f, out_file)
            if not ok:
                print(f"ffmpeg failed for {f.name}, trying moviepy fallback...")
                ok = make_thumbnail_moviepy(f, out_file)
        else:
            ok = make_thumbnail_moviepy(f, out_file)

        if ok:
            print(f"Created: {out_file.relative_to(videos_dir)}")
            processed += 1
        else:
            print(f"Failed to create thumbnail for: {f.name}")
            skipped += 1

    print(f"\nDone. Processed: {processed}, Failed/Skipped: {skipped}")
    print(f"Thumbnails are in: {out_dir}")


if __name__ == "__main__":
    main()
