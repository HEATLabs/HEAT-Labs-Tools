import os
import sys
import time
import subprocess
import importlib.util
import site


def check_and_install_packages():
    """Check for required packages and install them if needed."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    packages_dir = os.path.join(script_dir, "packages")

    # Create packages directory if it doesn't exist
    if not os.path.exists(packages_dir):
        os.makedirs(packages_dir)

    # Add packages directory to Python path
    if packages_dir not in sys.path:
        sys.path.insert(0, packages_dir)
        # Also add any potential site-packages subdirectory
        site_packages = os.path.join(
            packages_dir,
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        if os.path.exists(site_packages):
            sys.path.insert(0, site_packages)

    # List of required packages
    required_packages = {"Pillow": "PIL", "tqdm": "tqdm", "Wand": "wand"}

    # Check which packages need to be installed
    packages_to_install = []

    for package_name, import_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            print(f"✓ {package_name} is already available")
        except ImportError:
            packages_to_install.append(package_name)

    # Install missing packages if any
    if packages_to_install:
        print("\nInstalling required packages...")
        try:
            pip_command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                packages_dir,
            ] + packages_to_install

            result = subprocess.run(
                pip_command, capture_output=True, text=True, check=True
            )

            print(f"✓ Successfully installed: {', '.join(packages_to_install)}")

            # Re-add to path after installation
            if packages_dir not in sys.path:
                sys.path.insert(0, packages_dir)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e}")
            print(f"Error output: {e.stderr}")
            print("\nPlease manually install the required packages:")
            print(f"pip install {' '.join(packages_to_install)}")
            input("Press Enter to exit.")
            sys.exit(1)

    # Now try to import the packages we need
    try:
        global Image, WandImage, tqdm
        from PIL import Image
        from wand.image import Image as WandImage
        from tqdm import tqdm

        return True
    except ImportError as e:
        print(f"Error importing installed packages: {e}")
        print("Please try running the script again or manually install the packages.")
        input("Press Enter to exit.")
        return False


def clear_screen():
    """Clear the terminal screen based on OS."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Print a nice header for the application."""
    clear_screen()
    print("=" * 60)
    print("          PCWStats - DDS to PNG Converter         ")
    print("=" * 60)
    print()


def convert_dds_to_png(dds_path, png_path):
    """Convert a DDS file to PNG format using Wand."""
    try:
        with WandImage(filename=dds_path) as img:
            img.format = "png"
            img.save(filename=png_path)
        return True
    except Exception as e:
        print(f"\nError converting {dds_path}: {str(e)}")
        return False


def process_directory(main_input_dir):
    """Process each subdirectory in the main input directory."""
    # Check if the directory exists
    if not os.path.exists(main_input_dir):
        print(f"\nERROR: The specified directory does not exist: {main_input_dir}")
        return False

    # Find all subdirectories
    subdirs = [
        d
        for d in os.listdir(main_input_dir)
        if os.path.isdir(os.path.join(main_input_dir, d))
    ]

    if not subdirs:
        print(f"\nNo subdirectories found in {main_input_dir}")
        return False

    print(f"\nFound {len(subdirs)} directories to process.")

    total_converted = 0
    total_failed = 0

    # Process each subdirectory
    for i, subdir in enumerate(subdirs):
        subdir_path = os.path.join(main_input_dir, subdir)
        assets_dir = os.path.join(subdir_path, ".assets", "output")

        if not os.path.exists(assets_dir):
            print(f"\nSkipping {subdir}: No .assets/output directory found.")
            continue

        # Find all DDS files
        dds_files = []
        for root, _, files in os.walk(assets_dir):
            for file in files:
                if file.lower().endswith(".dds"):
                    dds_files.append(os.path.join(root, file))

        if not dds_files:
            print(f"\nNo DDS files found in {subdir}.")
            continue

        print(f"\nProcessing directory {i + 1}/{len(subdirs)}: {subdir}")
        print(f"Found {len(dds_files)} DDS files to convert.")

        converted = 0
        failed = 0

        # Convert each DDS file to PNG
        for dds_file in tqdm(dds_files, desc="Converting DDS to PNG", unit="file"):
            png_file = os.path.splitext(dds_file)[0] + ".png"

            if convert_dds_to_png(dds_file, png_file):
                # Delete the original DDS file after successful conversion
                try:
                    os.remove(dds_file)
                    converted += 1
                except Exception as e:
                    print(
                        f"\nWarning: Could not delete original file {dds_file}: {str(e)}"
                    )
            else:
                failed += 1

            # Add a short delay to prevent system overload
            time.sleep(0.05)

        total_converted += converted
        total_failed += failed

        print(f"\nDirectory {subdir} processed:")
        print(f"  - {converted} files converted successfully")
        print(f"  - {failed} files failed to convert")

        if i < len(subdirs) - 1:
            print("\nMoving to next directory...")
            time.sleep(1)

    print(f"\nAll directories processed:")
    print(f"  - Total files converted: {total_converted}")
    print(f"  - Total files failed: {total_failed}")

    return total_converted > 0


def main():
    print_header()
    print("Welcome to the PCWStats DDS to PNG Converter.")
    print(
        "This utility will convert all DDS files to PNG format in your Project CW folders."
    )
    print("Original DDS files will be deleted after successful conversion.")
    print()

    while True:
        print("Please enter the full path to your main input directory:")
        print(
            "(This directory should contain subdirectories with .assets/output folders)"
        )
        input_dir = input("> ").strip().strip("\"'")

        if not os.path.exists(input_dir):
            print("\nERROR: The specified directory does not exist. Please try again.")
            continue

        print("\nReady to convert DDS files to PNG:")
        print(f"  Input directory: {input_dir}")
        print("\nPress Enter to continue or type 'exit' to quit.")

        if input("> ").lower() == "exit":
            return

        print_header()
        print("Converting DDS files to PNG. This may take a while...\n")

        if process_directory(input_dir):
            print("\nConversion completed successfully!")
        else:
            print("\nNo files were converted or there was an error during conversion.")

        print("\nPress Enter to exit or type 'again' to convert another directory.")
        choice = input("> ").lower()
        if choice != "again":
            break

        print_header()


if __name__ == "__main__":
    try:
        print_header()
        print("Checking required packages...")
        if check_and_install_packages():
            print("\nAll required packages are available.")
            time.sleep(1)
            main()
        # Package installation failure is handled within check_and_install_packages

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {str(e)}")
        print("Please try running the script again.")
