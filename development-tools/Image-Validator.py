import os
import sys
from PIL import Image, PngImagePlugin
from pathlib import Path
import concurrent.futures

# Configuration
BASE_IMAGE_DIR = "../../Website-Images/"
EXCLUDED_DIRS = {
    "android",
    "apple",
    "favicons",
    "hero-background",
    "microsoft",
    "miscellaneous",
}
METADATA_KEY = "Source"
METADATA_TEXT = "Image from PCWStats - https://pcwstats.github.io"


def has_correct_metadata(filepath: Path) -> bool:
    """Check if a PNG image already has the correct metadata."""
    try:
        with Image.open(filepath) as img:
            if img.format != "PNG":
                return False  # Only check metadata on PNGs
            info = img.info
            return info.get(METADATA_KEY) == METADATA_TEXT
    except Exception:
        return False


def process_image(filepath: Path):
    """Process a single image file according to the rules."""
    try:
        relative_path = filepath.relative_to(BASE_IMAGE_DIR)
        if any(part in EXCLUDED_DIRS for part in relative_path.parts):
            # Only PNGs in excluded dirs get metadata updates
            if filepath.suffix.lower() == ".png" and not has_correct_metadata(filepath):
                with Image.open(filepath) as img:
                    meta = PngImagePlugin.PngInfo()
                    meta.add_text(METADATA_KEY, METADATA_TEXT)
                    img.save(filepath, format="PNG", pnginfo=meta)
                return f"Updated metadata for {filepath}"
            return f"Skipped (excluded or already up-to-date): {filepath}"

        # For non-excluded directories
        if filepath.suffix.lower() != ".png":
            # Convert to PNG and add metadata
            with Image.open(filepath) as img:
                new_path = filepath.with_suffix(".png")
                meta = PngImagePlugin.PngInfo()
                meta.add_text(METADATA_KEY, METADATA_TEXT)
                img.save(new_path, format="PNG", pnginfo=meta)
                filepath.unlink()
                return f"Converted {filepath} to {new_path}"

        else:
            if not has_correct_metadata(filepath):
                with Image.open(filepath) as img:
                    meta = PngImagePlugin.PngInfo()
                    meta.add_text(METADATA_KEY, METADATA_TEXT)
                    img.save(filepath, format="PNG", pnginfo=meta)
                return f"Updated metadata for {filepath}"
            return f"Skipped (already has metadata): {filepath}"

    except Exception as e:
        return f"Error processing {filepath}: {str(e)}"


def find_image_files(directory: str):
    """Find all image files in directory recursively."""
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    for root, _, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                yield Path(root) / file


def main():
    print("Starting image processing...")
    print(f"Base directory: {BASE_IMAGE_DIR}")
    print(f"Excluded directories: {', '.join(EXCLUDED_DIRS)}")

    if not os.path.exists(BASE_IMAGE_DIR):
        print(f"Error: Base directory {BASE_IMAGE_DIR} does not exist")
        sys.exit(1)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_image, img_path)
            for img_path in find_image_files(BASE_IMAGE_DIR)
        ]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result)

    print("Image processing complete.")


if __name__ == "__main__":
    main()
