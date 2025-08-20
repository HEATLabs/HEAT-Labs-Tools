import os
import sys
from PIL import Image, PngImagePlugin
from PIL.ExifTags import TAGS
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
METADATA_TEXT = "Image from HEAT Labs - https://heatlabs.github.io"


def has_correct_metadata(filepath: Path) -> bool:
    """Check if a PNG image already has the correct metadata."""
    try:
        with Image.open(filepath) as img:
            if img.format == "PNG":
                info = img.info
                return info.get(METADATA_KEY) == METADATA_TEXT
            elif img.format in ["JPEG", "JPG"]:
                # Check EXIF data for JPEG images
                if hasattr(img, "_getexif") and img._getexif():
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == "ImageDescription" and value == METADATA_TEXT:
                            return True
                return False
            # For other formats, assume no metadata support
            return False
    except Exception:
        return False


def add_metadata_to_png(filepath: Path):
    """Add metadata to PNG image."""
    try:
        with Image.open(filepath) as img:
            meta = PngImagePlugin.PngInfo()
            # Preserve existing metadata
            if hasattr(img, "text"):
                for key, value in img.text.items():
                    if key != METADATA_KEY:  # Don't duplicate our metadata
                        meta.add_text(key, value)
            meta.add_text(METADATA_KEY, METADATA_TEXT)
            img.save(filepath, format="PNG", pnginfo=meta)
        return True
    except Exception as e:
        raise e


def add_metadata_to_jpeg(filepath: Path):
    """Add metadata to JPEG image."""
    try:
        with Image.open(filepath) as img:
            # For JPEG, we'll add it as EXIF ImageDescription
            exif_dict = {}
            if hasattr(img, "_getexif") and img._getexif():
                exif_dict = img._getexif() or {}

            # Add our metadata as ImageDescription (tag 270)
            exif_dict[270] = METADATA_TEXT

            # Convert back to EXIF format
            from PIL.ExifTags import Base

            exif_bytes = img.info.get("exif", b"")

            # Save with updated description in ImageDescription field
            img.save(
                filepath,
                format="JPEG",
                exif=exif_bytes,
                description=METADATA_TEXT,
                quality=95,
            )
        return True
    except Exception as e:
        # If EXIF manipulation fails, try a simpler approach
        try:
            with Image.open(filepath) as img:
                img.save(filepath, format="JPEG", quality=95)
            return True
        except:
            raise e


def process_image(filepath: Path):
    """Process a single image file according to the rules."""
    try:
        relative_path = filepath.relative_to(BASE_IMAGE_DIR)

        # Check if already has correct metadata
        if has_correct_metadata(filepath):
            return f"Skipped (already has metadata): {filepath}"

        # Add metadata based on file format
        if filepath.suffix.lower() == ".png":
            add_metadata_to_png(filepath)
            return f"Added metadata to PNG: {filepath}"
        elif filepath.suffix.lower() in [".jpg", ".jpeg"]:
            add_metadata_to_jpeg(filepath)
            return f"Added metadata to JPEG: {filepath}"
        else:
            # For other formats (WebP, BMP, GIF), try generic approach
            try:
                with Image.open(filepath) as img:
                    # Save in same format, some formats may not support metadata
                    img.save(filepath, format=img.format)
                return f"Processed (limited metadata support): {filepath}"
            except Exception as e:
                return f"Skipped (format not supported for metadata): {filepath}"

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
    print("Starting image metadata update...")
    print(f"Base directory: {BASE_IMAGE_DIR}")
    print(f"Excluded directories: {', '.join(EXCLUDED_DIRS)}")
    print(f"Adding metadata: {METADATA_KEY} = {METADATA_TEXT}")

    if not os.path.exists(BASE_IMAGE_DIR):
        print(f"Error: Base directory {BASE_IMAGE_DIR} does not exist")
        sys.exit(1)

    processed_count = 0
    skipped_count = 0
    error_count = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_image, img_path)
            for img_path in find_image_files(BASE_IMAGE_DIR)
        ]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result)

            if "Added metadata" in result:
                processed_count += 1
            elif "Skipped" in result:
                skipped_count += 1
            elif "Error" in result:
                error_count += 1

    print(f"\nMetadata update complete!")
    print(f"Images processed: {processed_count}")
    print(f"Images skipped: {skipped_count}")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    main()
