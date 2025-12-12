import os
import json
import sys
from pathlib import Path


def main():
    # Define paths
    script_dir = Path(__file__).parent.absolute()

    # Image folder path
    image_folder = script_dir / "../../HEAT-Labs-Images/miscellaneous/meme"
    image_folder = image_folder.resolve()

    # JSON file path
    json_file = script_dir / "../../HEAT-Labs-Configs/memes.json"
    json_file = json_file.resolve()

    # Create directories if they don't exist
    image_folder.mkdir(parents=True, exist_ok=True)
    json_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if folders exist
    if not image_folder.exists():
        print(f"Error: Image folder not found at {image_folder}")
        sys.exit(1)

    # Load existing JSON if it exists
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

    # Get all image files from folder
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
    image_files = []

    for file in image_folder.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            image_files.append(file.name)

    print(f"Found {len(image_files)} images in folder")

    # Create a dictionary of existing entries
    existing_entries = {
        entry["path"].split("/")[-1]: entry
        for entry in existing_data
        if "path" in entry
    }

    # Create set of existing filenames
    existing_filenames = set(existing_entries.keys())

    # Find new images
    current_filenames = set(image_files)
    new_images = current_filenames - existing_filenames

    print(f"Found {len(new_images)} new images to add")

    # Add new images to the data
    for filename in sorted(new_images):
        # Create a name from the filename
        nice_name = Path(filename).stem
        nice_name = nice_name.replace("_", " ").replace("-", " ")
        # Capitalize first letter of each word
        nice_name = " ".join(word.capitalize() for word in nice_name.split())

        # Create new entry
        new_entry = {
            "name": nice_name,
            "author": "HEAT Labs Team",
            "path": f"https://cdn5.heatlabs.net/miscellaneous/meme/{filename}",
        }

        existing_data.append(new_entry)
        print(f"  Added: {filename} -> {nice_name}")

    # Sort the data by name for consistency
    existing_data.sort(key=lambda x: x.get("name", "").lower())

    # Save to JSON file
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully updated {json_file}")
    print(f"Total entries: {len(existing_data)}")

    # Summary
    if new_images:
        print(f"Added {len(new_images)} new images")
    else:
        print("No new images to add")


if __name__ == "__main__":
    main()
