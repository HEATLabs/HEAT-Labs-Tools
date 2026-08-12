import os
from PIL import Image
import glob


def convert_png_to_webp(input_path, output_path, quality=85):
    try:
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if necessary (WebP handles transparency)
            if img.mode in ("RGBA", "LA"):
                # Keep transparency for WebP
                img.save(output_path, "WebP", quality=quality, lossless=False)
            else:
                img.save(output_path, "WebP", quality=quality)

        print(f"✓ Converted: {input_path} → {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error converting {input_path}: {str(e)}")
        return False


def convert_dds_to_webp(input_path, output_path, quality=85):
    try:
        with Image.open(input_path) as img:
            # If the image has multiple frames/layers, get the first one
            if hasattr(img, "n_frames") and img.n_frames > 1:
                # For DDS with mipmaps, we want the first frame
                img.seek(0)

            # Convert to RGB if needed (WebP handles transparency)
            if img.mode in ("RGBA", "LA"):
                img.save(output_path, "WebP", quality=quality, lossless=False)
            elif img.mode == "P":
                # Convert palette-based images to RGB
                img = img.convert("RGB")
                img.save(output_path, "WebP", quality=quality)
            else:
                img.save(output_path, "WebP", quality=quality)

        print(f"✓ Converted: {input_path} → {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error converting {input_path}: {str(e)}")
        return False


def find_image_files(root_dir, extensions):
    """Find all image files with given extensions recursively."""
    image_files = []
    extensions_lower = [ext.lower() for ext in extensions]

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_lower = file.lower()
            for ext in extensions_lower:
                if file_lower.endswith(ext):
                    image_files.append(os.path.join(root, file))
                    break

    return image_files


def main():
    # Get current directory
    current_dir = os.getcwd()
    print(f"Looking for image files in: {current_dir} (including subdirectories)")

    # Define supported extensions
    supported_extensions = [".png", ".dds"]

    # Find all image files recursively
    image_files = find_image_files(current_dir, supported_extensions)

    if not image_files:
        print("No PNG or DDS files found in the current directory or subdirectories.")
        return

    print(f"Found {len(image_files)} image file(s) to convert:")

    # Separate files by extension for reporting
    png_files = [f for f in image_files if f.lower().endswith(".png")]
    dds_files = [f for f in image_files if f.lower().endswith(".dds")]

    if png_files:
        print(f"  PNG files: {len(png_files)}")
    if dds_files:
        print(f"  DDS files: {len(dds_files)}")

    print()  # Empty line for better readability

    # Convert each image file
    converted_count = 0
    failed_count = 0
    skipped_count = 0

    for image_file in image_files:
        # Create output filename (replace extension with .webp)
        base_name = os.path.splitext(image_file)[0]
        webp_file = f"{base_name}.webp"

        # Skip if WebP file already exists
        if os.path.exists(webp_file):
            rel_path = os.path.relpath(webp_file, current_dir)
            print(f"⚠ Skipped: {rel_path} already exists")
            skipped_count += 1
            continue

        # Determine conversion function based on file extension
        rel_path = os.path.relpath(image_file, current_dir)
        print(f"Converting: {rel_path}")

        if image_file.lower().endswith(".png"):
            success = convert_png_to_webp(image_file, webp_file)
        elif image_file.lower().endswith(".dds"):
            success = convert_dds_to_webp(image_file, webp_file)
        else:
            print(f"⚠ Unsupported format: {image_file}")
            failed_count += 1
            continue

        if success:
            converted_count += 1
        else:
            failed_count += 1

    # Summary
    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted_count} files")
    if skipped_count > 0:
        print(f"Skipped (already exist): {skipped_count} files")
    if failed_count > 0:
        print(f"Failed conversions: {failed_count} files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nConversion cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
