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


def find_png_files(root_dir):
    png_files = []

    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(root_dir):
        # Find PNG files in current directory
        for file in files:
            if file.lower().endswith(".png"):
                png_files.append(os.path.join(root, file))

    return png_files


def main():
    # Get current directory
    current_dir = os.getcwd()
    print(f"Looking for PNG files in: {current_dir} (including subdirectories)")

    # Find all PNG files recursively
    png_files = find_png_files(current_dir)

    if not png_files:
        print("No PNG files found in the current directory or subdirectories.")
        return

    print(f"Found {len(png_files)} PNG file(s) to convert:")
    for png_file in png_files:
        # Show relative path for cleaner output
        rel_path = os.path.relpath(png_file, current_dir)
        print(f"  - {rel_path}")

    print()  # Empty line for better readability

    # Convert each PNG file
    converted_count = 0
    failed_count = 0
    skipped_count = 0

    for png_file in png_files:
        # Create output filename (replace .png with .webp)
        base_name = os.path.splitext(png_file)[0]
        webp_file = f"{base_name}.webp"

        # Skip if WebP file already exists
        if os.path.exists(webp_file):
            rel_path = os.path.relpath(webp_file, current_dir)
            print(f"⚠ Skipped: {rel_path} already exists")
            skipped_count += 1
            continue

        # Convert the file
        if convert_png_to_webp(png_file, webp_file):
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
