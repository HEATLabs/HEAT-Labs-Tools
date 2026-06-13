import os
import sys
import zipfile
import time
import shutil
from tqdm import tqdm


def clear_screen():
    """Clear the terminal screen based on OS."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Print a nice header for the application."""
    clear_screen()
    print("=" * 60)
    print("          HEAT Labs - File Extraction Utility         ")
    print("=" * 60)
    print()


def get_directory_size(path):
    """Calculate the size of a directory in GB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    return total_size / (1024 * 1024 * 1024)  # Convert to GB


def check_disk_space(path):
    """Check if there's enough free disk space at the specified path."""
    if sys.platform == "win32":
        import ctypes

        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)
        )
        free_gb = free_bytes.value / (1024 * 1024 * 1024)
    else:
        stats = os.statvfs(path)
        free_gb = (stats.f_bavail * stats.f_frsize) / (1024 * 1024 * 1024)

    return free_gb


def extract_zip_files_detailed(source_dir, output_dir, file_extensions=None):
    """
    Extract all ZIP files from source directory to output directory maintaining structure.
    If file_extensions is provided, only extract files with those extensions.
    """
    # Get assets directory
    assets_dir = os.path.join(source_dir, ".assets", "output")

    if not os.path.exists(assets_dir):
        print(f"\nERROR: Could not find .assets/output directory at {source_dir}")
        print(
            "Please make sure you've entered the correct Project CW installation path."
        )
        return False

    # Get list of ZIP files
    zip_files = [
        file for file in os.listdir(assets_dir) if file.lower().endswith(".zip")
    ]

    if not zip_files:
        print("\nNo ZIP files found in the specified directory.")
        return False

    print(f"\nFound {len(zip_files)} ZIP files to process.")

    if file_extensions:
        print(f"Will only extract files with extensions: {', '.join(file_extensions)}")

    # Process each ZIP file
    for i, zip_file in enumerate(
        tqdm(zip_files, desc="Processing ZIP files", unit="file")
    ):
        zip_path = os.path.join(assets_dir, zip_file)
        target_folder = os.path.join(output_dir, os.path.splitext(zip_file)[0])

        # Create target folder if it doesn't exist
        os.makedirs(target_folder, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                if file_extensions:
                    # Only extract files with specific extensions
                    for item in zip_ref.infolist():
                        file_ext = os.path.splitext(item.filename)[1].lower()
                        if file_ext in file_extensions:
                            zip_ref.extract(item, target_folder)
                else:
                    # Extract all files
                    zip_ref.extractall(target_folder)

            # Wait a second between each extraction
            if i < len(zip_files) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"\nError processing {zip_file}: {str(e)}")
            continue

    return True


def extract_zip_files_simple(source_dir, output_dir, file_extensions=None):
    # Get assets directory
    assets_dir = os.path.join(source_dir, ".assets", "output")

    if not os.path.exists(assets_dir):
        print(f"\nERROR: Could not find .assets/output directory at {source_dir}")
        print(
            "Please make sure you've entered the correct Project CW installation path."
        )
        return False

    # Get list of ZIP files
    zip_files = [
        file for file in os.listdir(assets_dir) if file.lower().endswith(".zip")
    ]

    if not zip_files:
        print("\nNo ZIP files found in the specified directory.")
        return False

    print(f"\nFound {len(zip_files)} ZIP files to process.")
    print("Simple mode: All files will be extracted directly to the output folder")
    print("without maintaining the original directory structure.")
    print("NOTE: If multiple files have the same name, they will be overwritten!\n")

    if file_extensions:
        print(f"Will only extract files with extensions: {', '.join(file_extensions)}")

    # Track processed files to warn about duplicates
    processed_files = set()
    duplicate_count = 0

    # Process each ZIP file
    for i, zip_file in enumerate(
            tqdm(zip_files, desc="Processing ZIP files", unit="file")
    ):
        zip_path = os.path.join(assets_dir, zip_file)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Get list of files to extract
                files_to_extract = []

                if file_extensions:
                    # Filter by extension
                    for item in zip_ref.infolist():
                        file_ext = os.path.splitext(item.filename)[1].lower()
                        if file_ext in file_extensions:
                            files_to_extract.append(item)
                else:
                    # Extract all files
                    files_to_extract = zip_ref.infolist()

                # Extract each file directly to output_dir
                for item in files_to_extract:
                    # Skip directories
                    if item.is_dir():
                        continue

                    # Get just the filename without path
                    original_filename = os.path.basename(item.filename)

                    # Check for duplicate filenames
                    if original_filename in processed_files:
                        duplicate_count += 1
                        # Add a suffix to avoid overwriting
                        name, ext = os.path.splitext(original_filename)
                        counter = 1
                        new_filename = f"{name}_{counter}{ext}"
                        while new_filename in processed_files:
                            counter += 1
                            new_filename = f"{name}_{counter}{ext}"
                        original_filename = new_filename

                    processed_files.add(original_filename)
                    target_path = os.path.join(output_dir, original_filename)

                    # Extract the file
                    with zip_ref.open(item) as source_file:
                        with open(target_path, 'wb') as target_file:
                            shutil.copyfileobj(source_file, target_file)

            # Wait a second between each extraction
            if i < len(zip_files) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"\nError processing {zip_file}: {str(e)}")
            continue

    if duplicate_count > 0:
        print(f"\nNOTE: {duplicate_count} duplicate filenames were found and renamed to avoid overwriting.")

    return True


def main():
    print_header()
    print("Welcome to the HEAT Labs File Extraction Utility.")
    print("This utility will extract files from your Project CW installation.")
    print()

    # Ask for extraction mode first
    print("Please select extraction mode:")
    print("1. Detailed Mode - Maintains original folder structure")
    print("2. Simple Mode - Extracts all files to a single folder (no subfolders)")
    print()

    while True:
        mode_choice = input("Enter your choice (1 or 2): ").strip()
        if mode_choice in ["1", "2"]:
            break
        print("Invalid choice. Please enter 1 or 2.")

    detailed_mode = (mode_choice == "1")

    while True:
        print("\nPlease enter the full path to your Project CW installation:")
        source_dir = input("> ").strip().strip("\"'")

        if not os.path.exists(source_dir):
            print("\nERROR: The specified directory does not exist. Please try again.")
            continue

        print("\nPlease enter the full path where you want to extract the files:")
        output_dir = input("> ").strip().strip("\"'")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Check available disk space
        free_space = check_disk_space(output_dir)
        print(f"\nAvailable disk space: {free_space:.2f} GB")

        if free_space < 50:
            print(
                "\nWARNING: You have less than 50 GB of free space on the selected drive."
            )
            print(
                "It is recommended to have at least 50 GB of free space for extraction."
            )
            print("\nDo you want to continue anyway? (y/n)")
            if input("> ").lower() != "y":
                print("\nExiting. Please free up space and try again.")
                return

        # Ask if user wants to extract all files or specific file types
        print(
            "\nDo you want to extract all files from the archives or only specific file types?"
        )
        print("1. Extract all files")
        print("2. Extract only specific file types")
        extraction_choice = input("> ").strip()

        file_extensions = None
        if extraction_choice == "2":
            print(
                "\nPlease enter the file extensions you want to extract (comma-separated, include the dot)"
            )
            print("Example: .dds, .spec, .scene")
            extensions_input = input("> ").strip()
            file_extensions = [
                ext.strip().lower() for ext in extensions_input.split(",")
            ]

            # Make sure all extensions have a dot prefix
            file_extensions = [
                ext if ext.startswith(".") else f".{ext}" for ext in file_extensions
            ]

        print("\nReady to extract files:")
        print(f"  Extraction Mode: {'Detailed (maintains structure)' if detailed_mode else 'Simple (flat output)'}")
        print(f"  Source directory: {source_dir}")
        print(f"  Output directory: {output_dir}")
        if file_extensions:
            print(f"  File types to extract: {', '.join(file_extensions)}")
        else:
            print("  Extracting all file types")

        if not detailed_mode:
            print("\n  NOTE: In Simple Mode, all files will be placed directly in the output folder")
            print("  without any subfolders. Files with the same name will be renamed.")

        print("\nPress Enter to continue or type 'exit' to quit.")

        if input("> ").lower() == "exit":
            return

        print_header()
        print("Extracting files. This may take a while...\n")

        # Call the appropriate extraction function
        if detailed_mode:
            success = extract_zip_files_detailed(source_dir, output_dir, file_extensions)
        else:
            success = extract_zip_files_simple(source_dir, output_dir, file_extensions)

        if success:
            print("\nExtraction completed successfully!")
            print(f"All files have been extracted to: {output_dir}")

            if not detailed_mode:
                print("\nFiles were extracted in Simple Mode (flat structure).")
                print("All files are in the main output folder without subdirectories.")

        print("\nPress Enter to exit.")
        input()
        break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {str(e)}")
        print("Please try running the script again.")