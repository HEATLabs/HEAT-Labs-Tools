import os
import glob
import sys
from pydub import AudioSegment

# Path to FFmpeg
FFMPEG_PATH = "ffmpeg"

# Root directory
ROOT_DIRECTORY = "../../HEAT-Labs-Sounds/sounds"

# MP3 quality settings
MP3_BITRATE = "192k"  # "128k", "256k", "320k"


def setup_ffmpeg(ffmpeg_path):
    print("Setting up FFmpeg...")

    # Check if the provided path exists
    if not os.path.exists(ffmpeg_path):
        print(f"✗ FFmpeg path does not exist: {ffmpeg_path}")
        return False

    # Check for ffmpeg.exe in the provided path
    ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_exe):
        print(f"✗ ffmpeg.exe not found in: {ffmpeg_path}")
        print("Please make sure the path points to the folder containing ffmpeg.exe")
        return False

    # Add FFmpeg to the system PATH
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]

    # Set the path for pydub explicitly
    AudioSegment.converter = ffmpeg_exe
    AudioSegment.ffmpeg = ffmpeg_exe
    AudioSegment.ffprobe = os.path.join(ffmpeg_path, "ffprobe.exe")

    print(f"✓ FFmpeg configured successfully: {ffmpeg_exe}")
    return True


def find_wav_files(root_directory):
    wav_files = []

    print(f"Searching for WAV files in: {root_directory}")

    if not os.path.exists(root_directory):
        print(f"✗ Root directory does not exist: {root_directory}")
        return []

    # Recursively search for all WAV files
    for root, dirs, files in os.walk(root_directory):
        for file in files:
            if file.lower().endswith(".wav"):
                full_path = os.path.join(root, file)
                wav_files.append(full_path)

    print(f"✓ Found {len(wav_files)} WAV files")
    return wav_files


def convert_wav_to_mp3(wav_file, output_dir=None):
    try:
        # Determine output path
        if output_dir is None:
            # Save in same directory as original WAV file
            output_path = os.path.splitext(wav_file)[0] + ".mp3"
        else:
            # Maintain folder structure in output directory
            relative_path = os.path.relpath(wav_file, ROOT_DIRECTORY)
            relative_path_no_ext = os.path.splitext(relative_path)[0]
            output_path = os.path.join(output_dir, relative_path_no_ext + ".mp3")

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Skip if MP3 already exists and is newer than WAV
        if os.path.exists(output_path):
            wav_mtime = os.path.getmtime(wav_file)
            mp3_mtime = os.path.getmtime(output_path)
            if mp3_mtime >= wav_mtime:
                print(f"⚠ Skipping (already converted): {os.path.basename(wav_file)}")
                return True, output_path

        print(f"Converting: {os.path.basename(wav_file)}")

        # Load WAV file and convert to MP3
        audio = AudioSegment.from_wav(wav_file)
        audio.export(output_path, format="mp3", bitrate=MP3_BITRATE)

        # Verify conversion was successful
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(
                f"✓ Success: {os.path.basename(wav_file)} → {os.path.basename(output_path)}"
            )
            return True, output_path
        else:
            print(f"✗ Failed: {os.path.basename(wav_file)} - Output file problem")
            return False, None

    except Exception as e:
        print(f"✗ Error converting {os.path.basename(wav_file)}: {str(e)}")
        return False, None


def delete_wav_files(wav_files_to_delete):
    if not wav_files_to_delete:
        print("No WAV files to delete.")
        return

    print(f"\nAbout to delete {len(wav_files_to_delete)} WAV files:")

    # Show a preview of files to be deleted
    for i, wav_file in enumerate(wav_files_to_delete[:5]):
        print(f"  {os.path.basename(wav_file)}")
    if len(wav_files_to_delete) > 5:
        print(f"  ... and {len(wav_files_to_delete) - 5} more files")

    # Get final confirmation
    response = (
        input(
            f"\nAre you sure you want to delete these {len(wav_files_to_delete)} WAV files? (y/n): "
        )
        .strip()
        .lower()
    )

    if response not in ["y", "yes"]:
        print("Deletion cancelled.")
        return 0

    # Delete files
    deleted_count = 0
    failed_deletions = []

    print("\nDeleting WAV files...")
    for wav_file in wav_files_to_delete:
        try:
            os.remove(wav_file)
            if not os.path.exists(wav_file):
                print(f"✓ Deleted: {os.path.basename(wav_file)}")
                deleted_count += 1
            else:
                print(f"✗ Failed to delete: {os.path.basename(wav_file)}")
                failed_deletions.append(wav_file)
        except Exception as e:
            print(f"✗ Error deleting {os.path.basename(wav_file)}: {str(e)}")
            failed_deletions.append(wav_file)

    print(f"\nDeletion summary:")
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed to delete: {len(failed_deletions)}")

    return deleted_count


def main():
    print("=" * 70)
    print("WAV to MP3 Batch Converter")
    print("=" * 70)
    print(f"FFmpeg Path: {FFMPEG_PATH}")
    print(f"Root Directory: {ROOT_DIRECTORY}")
    print(f"MP3 Bitrate: {MP3_BITRATE}")
    print("=" * 70)

    # Setup FFmpeg
    if not setup_ffmpeg(FFMPEG_PATH):
        print("\nFFmpeg setup failed. Please check the path in the configuration.")
        input("Press Enter to exit...")
        return

    # Find all WAV files
    wav_files = find_wav_files(ROOT_DIRECTORY)

    if not wav_files:
        print("No WAV files found. Please check the root directory path.")
        input("Press Enter to exit...")
        return

    # Ask user if they want to proceed
    print(f"\nReady to convert {len(wav_files)} WAV files to MP3.")
    response = input("Proceed? (y/n): ").strip().lower()

    if response not in ["y", "yes"]:
        print("Conversion cancelled.")
        return

    print("\nStarting conversion...")
    print("-" * 50)

    # Convert all files and track successfully converted ones
    successful = 0
    failed = 0
    skipped = 0
    successfully_converted_files = []

    for i, wav_file in enumerate(wav_files, 1):
        print(f"[{i}/{len(wav_files)}] ", end="")
        result, mp3_path = convert_wav_to_mp3(wav_file)

        if result is True:
            successful += 1
            # Only add to deletion list if this was a new conversion (not skipped)
            if mp3_path and os.path.exists(mp3_path):
                # Check if MP3 was just created (not pre-existing)
                if (
                    not os.path.exists(mp3_path)
                    or os.path.getmtime(mp3_path) > os.path.getmtime(wav_file) - 10
                ):  # 10 second buffer
                    successfully_converted_files.append(wav_file)
        elif result is False:
            failed += 1
        else:
            skipped += 1

    # Print conversion summary
    print("-" * 50)
    print("CONVERSION SUMMARY:")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Total: {len(wav_files)}")

    if failed > 0:
        print("\nSome files failed to convert. Check the error messages above.")

    # Ask about deleting old WAV files
    if successful > 0:
        print(f"\nConversion completed successfully for {successful} files.")
        response = (
            input(
                "Do you want to delete the original WAV files that were successfully converted? (y/n): "
            )
            .strip()
            .lower()
        )

        if response in ["y", "yes"]:
            deleted_count = delete_wav_files(successfully_converted_files)
            print(f"\nFinal summary:")
            print(f"Files converted: {successful}")
            print(f"Original WAV files deleted: {deleted_count}")
        else:
            print("WAV files were not deleted.")
    else:
        print(
            "\nNo files were successfully converted, so no WAV files will be deleted."
        )

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
