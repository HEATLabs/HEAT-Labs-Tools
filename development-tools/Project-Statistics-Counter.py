import os
import re
import sys
import argparse
import json
from collections import defaultdict
from datetime import datetime

# path to the directory
TARGET_DIRECTORY = r"E:\GitHub\HEAT-Labs"

# path to the JSON file
JSON_FILE_PATH = "../../Website-Configs/home-stats.json"

# File extensions to analyze
TEXT_EXTENSIONS = {
    "Code": [
        ".py",
        ".js",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".sql",
        ".sh",
        ".bash",
        ".bat",
        ".ps1",
        ".cmd",
        ".lua",
        ".r",
        ".pl",
        ".pm",
        ".tcl",
        ".awk",
        ".sed",
        ".dart",
        ".groovy",
        ".vb",
        ".vbs",
        ".asm",
        ".f",
        ".f90",
        ".f95",
        ".m",
        ".ml",
        ".mli",
        ".swift",
        ".vue",
        ".elm",
        ".clj",
        ".cljs",
        ".cljc",
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        ".lisp",
        ".lsp",
        ".hs",
        ".purs",
        ".ada",
        ".d",
        ".nim",
        ".zig",
        ".jl",
        ".cr",
        ".json5",
        ".hx",
        ".wren",
        ".p4",
        ".rkt",
        ".idris",
        ".e",
        ".pike",
        ".lean",
        ".v",
        ".agda",
        ".cob",
        ".cpy",
        ".abap",
        ".rpg",
        ".4gl",
        ".chpl",
        ".rex",
        ".omgrofl",
    ],
    "Markup": [
        ".md",
        ".rst",
        ".txt",
        ".tex",
        ".latex",
        ".bib",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".csv",
        ".tsv",
        ".xml",
        ".xsl",
        ".xsd",
        ".xslt",
        ".xhtml",
        ".svg",
        ".rss",
        ".atom",
    ],
    "Documentation": [
        ".doc",
        ".docx",
        ".pdf",
        ".rtf",
        ".odt",
        ".fodt",
        ".sxw",
        ".wpd",
        ".texi",
        ".me",
        ".ms",
    ],
    "Scripts": [
        ".ps1",
        ".cmd",
        ".bat",
        ".vbs",
        ".applescript",
        ".ahk",
        ".ksh",
        ".zsh",
        ".fish",
        ".csh",
        ".tcsh",
        ".mak",
        ".mk",
        ".ninja",
        ".ebuild",
        ".eclass",
        ".pkgbuild",
    ],
    "Config": [
        ".env",
        ".venv",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".gitmodules",
        ".dockerfile",
        ".npmrc",
        ".yarnrc",
        ".babelrc",
        ".eslint",
        ".prettierrc",
        ".stylelintrc",
        ".condarc",
        ".flake8",
        ".pylintrc",
        ".mypy.ini",
        ".pydocstyle",
        ".phpcs",
        ".phpmd",
    ],
}

# Directories to exclude from analysis
EXCLUDE_DIRS = [
    ".git",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".idea",
    ".vscode",
    "vendor",
    "bin",
    "obj",
]

# Binary file signatures to detect quickly
BINARY_SIGNATURES = [
    b"\x89PNG",
    b"GIF8",
    b"BM",
    b"\xFF\xD8\xFF",
    b"PK\x03\x04",
    b"%PDF",
    b"\x7FELF",
    b"MZ",
    b"\xCF\xFA\xED\xFE",
    b"\xCA\xFE\xBA\xBE",
]


# Check if a file is binary by reading its first few bytes.
def is_binary(file_path, sample_size=8192):
    try:
        with open(file_path, "rb") as f:
            header = f.read(sample_size)

            # Check for known binary signatures
            for signature in BINARY_SIGNATURES:
                if header.startswith(signature):
                    return True

            # Check for null bytes which commonly indicate binary files
            if b"\x00" in header:
                return True

            # If more than 30% of the bytes are non-text, it's likely binary
            text_characters = bytes(range(32, 127)) + b"\r\n\t\b"
            binary_chars = sum(1 for byte in header if byte not in text_characters)
            return binary_chars / len(header) > 0.3 if header else False
    except (IOError, OSError):
        return True  # If we can't read the file, consider it binary to be safe


# Determine the category of a file based on its extension.
def get_file_extension_category(file_path):
    _, ext = os.path.splitext(file_path.lower())

    for category, extensions in TEXT_EXTENSIONS.items():
        if ext in extensions:
            return category

    # For unknown extensions, try to determine if it's text or binary
    if not is_binary(file_path):
        return "Other Text"

    return None  # Not a text file we're interested in


# Count the number of lines and characters in a file.
# Returns a tuple of (lines, characters)
def count_lines_and_chars(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.count("\n") + (
                1 if content and not content.endswith("\n") else 0
            )
            chars = len(content)
            return lines, chars
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0


# Format a number with thousands separators."""
def format_number(num):
    return f"{num:,}"


# Get the size of a file in bytes
def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError):
        return 0


# Convert bytes to GB
def bytes_to_gb(bytes_size):
    return bytes_size / (1024**3)


# Analyze files in the specified directory and return statistics.
def analyze_directory(target_dir):
    dir_stats = defaultdict(lambda: {"files": 0, "lines": 0, "chars": 0})
    dir_total_files = 0
    dir_total_lines = 0
    dir_total_chars = 0
    total_size_bytes = 0
    total_folders = 0

    print(f"\nScanning files in {target_dir}...\n")

    for root, dirs, files in os.walk(target_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        # Count folders (excluding excluded ones)
        total_folders += len(dirs)

        for file in files:
            file_path = os.path.join(root, file)

            # Skip this script itself
            if os.path.abspath(file_path) == os.path.abspath(__file__):
                continue

            # Get file size
            file_size = get_file_size(file_path)
            total_size_bytes += file_size

            category = get_file_extension_category(file_path)
            if not category:
                continue  # Skip binary or undesired files

            lines, chars = count_lines_and_chars(file_path)

            dir_stats[category]["files"] += 1
            dir_stats[category]["lines"] += lines
            dir_stats[category]["chars"] += chars

            dir_total_files += 1
            dir_total_lines += lines
            dir_total_chars += chars

    return (
        dir_stats,
        dir_total_files,
        dir_total_lines,
        dir_total_chars,
        total_folders,
        total_size_bytes,
    )


# Format the statistics as a string.
def format_statistics(
    stat_dict, files_count, lines_count, chars_count, folders_count, total_size_gb
):
    output = ["=" * 80, f"PROJECT STATISTICS SUMMARY", "=" * 80]

    # Print by category
    categories = sorted(stat_dict.keys())
    for category in categories:
        cat_stats = stat_dict[category]
        output.append(f"\n{category} Files:")
        output.append(f"  Files:      {format_number(cat_stats['files'])}")
        output.append(f"  Lines:      {format_number(cat_stats['lines'])}")
        output.append(f"  Characters: {format_number(cat_stats['chars'])}")

    # Print totals
    output.append("\n" + "=" * 80)
    output.append(
        f"TOTAL: {format_number(files_count)} files, {format_number(folders_count)} folders, {format_number(lines_count)} lines, {format_number(chars_count)} characters"
    )
    output.append(f"TOTAL SIZE: {total_size_gb:.2f} GB")
    output.append("=" * 80)

    return "\n".join(output)


# Save the statistics to a text file and return the file path.
def save_statistics_to_file(stats_output):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"project_stats_{timestamp}.txt"
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(stats_output)

    return file_path


# Update the JSON file
def update_json_file(
    json_path, lines_of_code, files_count, folders_count, total_size_gb
):
    try:
        # Try to read existing JSON file
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            # Create new structure if file doesn't exist
            data = {
                "creationDate": datetime.now().strftime("%B %d, %Y %H:%M:%S"),
                "coffeePerDay": 0,
                "stats": {
                    "teamMembers": 0,
                    "linesOfCode": 0,
                    "contributors": 0,
                    "filesCount": 0,
                    "foldersCount": 0,
                    "totalSizeGB": 0,
                },
            }

        # Update the statistics
        data["stats"]["linesOfCode"] = lines_of_code
        data["stats"]["filesCount"] = files_count
        data["stats"]["foldersCount"] = folders_count
        data["stats"]["totalSizeGB"] = round(total_size_gb, 2)

        # Write back to the JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Statistics updated in JSON file: {json_path}")
        return True
    except Exception as e:
        print(f"Error updating JSON file: {e}")
        return False


# Display statistics and show interactive menu.
def display_and_menu(
    stat_dict,
    files_count,
    lines_count,
    chars_count,
    folders_count,
    total_size_gb,
    args_obj,
    json_path,
):
    stats_output = format_statistics(
        stat_dict, files_count, lines_count, chars_count, folders_count, total_size_gb
    )
    print(stats_output)

    # Update the JSON file with the new statistics
    update_json_file(json_path, lines_count, files_count, folders_count, total_size_gb)

    while True:
        print("\nOptions:")
        print("1. Save statistics to a text file")
        print("2. Quit")
        if not args_obj.dir:  # Only offer to run again if not in command-line mode
            print("3. Run again")

        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == "1":
            # Save the file immediately when option is chosen
            file_path = save_statistics_to_file(stats_output)
            print(f"\nStatistics saved to: {file_path}")

            # Now ask what to do next
            print("\nOptions:")
            print("1. Quit")
            print("2. Run again")

            next_choice = input("\nEnter your choice (1-2): ").strip()
            if next_choice == "1" or next_choice.lower() == "q":
                print("Exiting program.")
                sys.exit(0)
            elif next_choice == "2":
                return True  # Run again

        elif choice == "2" or choice.lower() == "q":
            print("Exiting program.")
            sys.exit(0)
        elif choice == "3" and not args_obj.dir:
            return True  # Run again
        else:
            print("Invalid choice. Please try again.")


# Parse command line arguments.
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Project Statistics Counter - Analyze and count files, lines, and characters in a project."
    )
    parser.add_argument(
        "-dir",
        "--directory",
        dest="dir",
        help="Directory to analyze (default: configured directory)",
    )
    parser.add_argument(
        "-json",
        "--json-file",
        dest="json",
        help="JSON file path to update (default: configured JSON path)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    while True:
        # Use command line arguments if provided, otherwise use configured paths
        target_directory = args.dir if args.dir else TARGET_DIRECTORY
        json_file_path = args.json if args.json else JSON_FILE_PATH

        (
            directory_stats,
            directory_total_files,
            directory_total_lines,
            directory_total_chars,
            directory_total_folders,
            directory_total_size_bytes,
        ) = analyze_directory(target_directory)

        directory_total_size_gb = bytes_to_gb(directory_total_size_bytes)

        if not display_and_menu(
            directory_stats,
            directory_total_files,
            directory_total_lines,
            directory_total_chars,
            directory_total_folders,
            directory_total_size_gb,
            args,
            json_file_path,
        ):
            break

        # If running again and in command-line mode, exit after one run
        if args.dir:
            break
