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
    print("          PCWStats - File Extraction Utility         ")
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


def extract_zip_files(source_dir, output_dir):
    """Extract all ZIP files from source directory to output directory."""
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

    print(f"\nFound {len(zip_files)} ZIP files to extract.")

    # Process each ZIP file
    for i, zip_file in enumerate(
        tqdm(zip_files, desc="Extracting ZIP files", unit="file")
    ):
        zip_path = os.path.join(assets_dir, zip_file)
        target_folder = os.path.join(output_dir, os.path.splitext(zip_file)[0])

        # Create target folder if it doesn't exist
        os.makedirs(target_folder, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(target_folder)

            # Wait a second between each extraction
            if i < len(zip_files) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"\nError extracting {zip_file}: {str(e)}")
            continue

    return True


def main():
    print_header()
    print("Welcome to the PCWStats File Extraction Utility.")
    print("This utility will extract all ZIP files from your Project CW installation.")
    print()

    while True:
        print("Please enter the full path to your Project CW installation:")
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

        print("\nReady to extract files:")
        print(f"  Source directory: {source_dir}")
        print(f"  Output directory: {output_dir}")
        print("\nPress Enter to continue or type 'exit' to quit.")

        if input("> ").lower() == "exit":
            return

        print_header()
        print("Extracting ZIP files. This may take a while...\n")

        if extract_zip_files(source_dir, output_dir):
            print("\nExtraction completed successfully!")
            print(f"All files have been extracted to: {output_dir}")

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
