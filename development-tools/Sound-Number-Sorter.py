import os
import json
import time
from mutagen import File
from mutagen.id3 import (
    ID3,
    TXXX,
    TPE1,
    TIT2,
    TALB,
    TCON,
    TCOM,
    TDRC,
    APIC,
    ID3NoHeaderError,
)
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE


def clear_audio_metadata(file_path):
    try:
        if file_path.lower().endswith(".mp3"):
            # For MP3 files
            try:
                audio = MP3(file_path, ID3=ID3)
                # Remove existing ID3 tags
                if audio.tags:
                    audio.delete()
                    audio.save()
                # Create new empty ID3 tag
                audio.add_tags()
                audio.save()
            except ID3NoHeaderError:
                # File has no ID3 tag
                audio = MP3(file_path)
                audio.add_tags()
                audio.save()

        elif file_path.lower().endswith(".flac"):
            # For FLAC files
            audio = FLAC(file_path)
            audio.delete()
            audio.save()

        elif file_path.lower().endswith((".ogg", ".oga")):
            # For Ogg Vorbis files
            audio = OggVorbis(file_path)
            audio.delete()
            audio.save()

        elif file_path.lower().endswith(".wav"):
            # For WAV files
            try:
                audio = WAVE(file_path)
                # WAV files can have ID3 tags
                if audio.tags:
                    audio.delete()
                    audio.save()
            except:
                pass

        elif file_path.lower().endswith((".m4a", ".aac")):
            print(
                f"  Note: Metadata clearing for {os.path.basename(file_path)} may be limited (AAC/M4A format)"
            )

        elif file_path.lower().endswith(".wma"):
            print(
                f"  Note: Metadata clearing for {os.path.basename(file_path)} may be limited (WMA format)"
            )

        return True

    except Exception as e:
        print(
            f"  Warning: Could not clear metadata for {os.path.basename(file_path)}: {str(e)}"
        )
        return False


def safe_rename(old_path, new_path, max_retries=5, retry_delay=0.1):
    for attempt in range(max_retries):
        try:
            if old_path != new_path:
                os.rename(old_path, new_path)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(
                    f"  Permission error (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(
                    f"  Error: Failed to rename after {max_retries} attempts: {str(e)}"
                )
                return False
        except Exception as e:
            print(f"  Error renaming file: {str(e)}")
            return False
    return False


def is_file_already_numbered(filename):
    name, ext = os.path.splitext(filename)
    return name.isdigit()


def get_sound_id(folder_name, file_number):
    return f"{folder_name}-{file_number}"


def is_sound_in_json(data, sound_id):
    for category in data["categories"]:
        for item in category["categoryItems"]:
            if item["soundID"] == sound_id:
                return True
    return False


def rename_and_update_sounds(sounds_json_path, sounds_folder_path):
    try:
        # Load existing sounds.json
        with open(sounds_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {sounds_json_path} not found!")
        return
    except json.JSONDecodeError:
        print(f"Error: {sounds_json_path} is not valid JSON!")
        return

    # Walk through the sounds directory
    for root, dirs, files in os.walk(sounds_folder_path):
        # Sort files alphabetically for consistent numbering
        files.sort()

        # Get the relative path from sounds_folder_path
        rel_path = os.path.relpath(root, sounds_folder_path)

        # Skip the root sounds folder itself, only process subfolders
        if rel_path == ".":
            continue

        # Extract folder name for sound ID
        folder_name = os.path.basename(root)

        # Create category name from folder name
        category_name = folder_name.replace("-", " ").title()

        # Determine sound source based on folder name
        if folder_name.lower().startswith("oat1"):
            sound_source = "Open Alpha Playtest #1"
        elif folder_name.lower().startswith("oat2"):
            sound_source = "Open Alpha Playtest #2"
        elif folder_name.lower().startswith("oat3"):
            sound_source = "Open Alpha Playtest #3"
        elif folder_name.lower().startswith("oat4"):
            sound_source = "Open Alpha Playtest #4"
        else:
            sound_source = folder_name  # Fallback to folder name if not OAT format

        # Filter only audio files and sort them properly
        audio_files = [
            f
            for f in files
            if f.lower().endswith(
                (".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma")
            )
        ]
        audio_files.sort()

        # Process each file in the current directory
        for i, filename in enumerate(audio_files, start=1):
            # Get file extension
            ext = os.path.splitext(filename)[1]

            # Create new filename
            new_filename = f"{i}{ext}"

            # Create sound ID
            sound_id = f"{folder_name}-{i}"

            # Check if file is already numbered correctly AND exists in JSON
            if is_file_already_numbered(filename) and is_sound_in_json(data, sound_id):
                print(
                    f"File {filename} in {folder_name}/ is already correctly numbered and in JSON - skipping completely"
                )
                continue

            # Full paths for renaming
            old_file_path = os.path.join(root, filename)
            new_file_path = os.path.join(root, new_filename)

            # Check if target file already exists
            if os.path.exists(new_file_path) and old_file_path != new_file_path:
                print(
                    f"  Error: Target file {new_filename} already exists in {folder_name}/"
                )
                print(f"  Cannot rename {filename} - skipping this file")
                continue

            # Step 1: Clear metadata from the original file
            print(f"Clearing metadata from {filename}...")
            metadata_cleared = clear_audio_metadata(old_file_path)

            if metadata_cleared:
                print(f"  Metadata cleared from {filename}")

            # Step 2: Rename the file
            if old_file_path != new_file_path:
                success = safe_rename(old_file_path, new_file_path)
                if success:
                    print(f"Renamed {filename} to {new_filename} in {folder_name}/")
                else:
                    print(f"  Failed to rename {filename} - skipping this file")
                    continue
            else:
                print(f"File {filename} is already correctly named")

            # Create GitHub raw content URL path (use new filename)
            github_path = f"{rel_path.replace(os.path.sep, '/')}/{new_filename}"

            # Check if this sound is already in JSON
            if not is_sound_in_json(data, sound_id):
                # Find or create the category
                category = None
                for cat in data["categories"]:
                    if cat["categoryName"] == category_name:
                        category = cat
                        break

                # If category doesn't exist, create it
                if category is None:
                    category = {
                        "categoryName": category_name,
                        "categoryDescription": f"Sound files from {folder_name} directory",
                        "categoryItems": [],
                    }
                    data["categories"].append(category)
                    print(f"Created new category: {category_name}")

                # Create new entry
                new_entry = {
                    "soundID": sound_id,
                    "soundType": folder_name,
                    "soundSource": sound_source,
                    "soundFile": f"https://cdn.jsdelivr.net/gh/HEATLabs/Sound-Bank@main/sounds/{github_path}",
                    "soundName": f"{folder_name} - Sound {i}",
                    "soundDescription": f"Sound file from {folder_name} directory",
                }

                # Add to JSON data
                category["categoryItems"].append(new_entry)
                print(f"Added to JSON: {new_entry['soundID']}")
            else:
                print(f"Entry {sound_id} already exists in JSON - skipping")

    # Sort the JSON entries by soundID for consistency
    data["categories"].sort(key=lambda x: x["categoryName"])
    for category in data["categories"]:
        category["categoryItems"].sort(key=lambda x: x["soundID"])

    # Save updated JSON
    with open(sounds_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Updated {sounds_json_path} with new sound entries!")


def safe_rename_current_dir(old_name, new_name, max_retries=5, retry_delay=0.1):
    for attempt in range(max_retries):
        try:
            os.rename(old_name, new_name)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(
                    f"  Permission error (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(
                    f"  Error: Failed to rename after {max_retries} attempts: {str(e)}"
                )
                return False
        except Exception as e:
            print(f"  Error renaming file: {str(e)}")
            return False
    return False


def rename_files_in_current_directory():
    # Get the current script's filename
    script_name = os.path.basename(__file__)

    # Get all files in the current directory
    files = [f for f in os.listdir(".") if os.path.isfile(f) and f != script_name]

    # Sort files alphabetically
    files.sort()

    # Rename files starting from 1, but check for conflicts
    for i, filename in enumerate(files, start=1):
        # Skip if file is already numbered
        if is_file_already_numbered(filename):
            print(f"File {filename} is already correctly numbered - skipping")
            continue

        # Get the file extension
        ext = os.path.splitext(filename)[1]
        # Create new filename
        new_name = f"{i}{ext}"

        # Check if target file already exists
        if os.path.exists(new_name):
            print(
                f"Error: Target file {new_name} already exists! - skipping {filename}"
            )
            continue

        # Rename the file with safe rename
        success = safe_rename_current_dir(filename, new_name)
        if success:
            print(f"Renamed {filename} to {new_name}")
        else:
            print(f"Failed to rename {filename} - skipping")


def main():
    print("Starting file processing...")

    # Configuration
    SOUNDS_JSON_PATH = "../../HEAT-Labs-Configs/sounds.json"
    SOUNDS_FOLDER_PATH = "../../HEAT-Labs-Sounds/sounds"

    # Step 1: Rename files in current directory
    print("\n=== Step 1: Renaming files in current directory ===")
    rename_files_in_current_directory()

    # Step 2: Rename sound files in their folders, clear metadata, and update JSON
    print(
        "\n=== Step 2: Renaming sound files, clearing metadata, and updating sounds.json ==="
    )
    rename_and_update_sounds(SOUNDS_JSON_PATH, SOUNDS_FOLDER_PATH)

    print("\n=== Processing Complete! ===")


if __name__ == "__main__":
    main()
