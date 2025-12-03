import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Configuration paths
DEFAULT_SOUNDS_JSON = "../../HEAT-Labs-Configs/sounds.json"
DEFAULT_SOUNDS_FOLDER = "../../HEAT-Labs-Sounds/sounds"
DEFAULT_VIDEOS_DIR = "../../HEAT-Labs-Images/tankopedia/videos"
DEFAULT_FFMPEG_PATH = "ffmpeg"

# Try imports for optional dependencies
try:
    from mutagen import File
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.wave import WAVE

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import subprocess

    SUBPROCESS_AVAILABLE = True
except ImportError:
    SUBPROCESS_AVAILABLE = False

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# SOUND NUMBER SORTER (Tool 1)
class SoundNumberSorter:
    def __init__(self, sounds_json=None, sounds_folder=None):
        self.sounds_json = sounds_json or DEFAULT_SOUNDS_JSON
        self.sounds_folder = sounds_folder or DEFAULT_SOUNDS_FOLDER

    def clear_audio_metadata(self, file_path):
        if not MUTAGEN_AVAILABLE:
            print("  Warning: Mutagen not available. Cannot clear metadata.")
            return False

        try:
            if file_path.lower().endswith(".mp3"):
                try:
                    audio = MP3(file_path, ID3=ID3)
                    if audio.tags:
                        audio.delete()
                        audio.save()
                    audio.add_tags()
                    audio.save()
                except ID3NoHeaderError:
                    audio = MP3(file_path)
                    audio.add_tags()
                    audio.save()

            elif file_path.lower().endswith(".flac"):
                audio = FLAC(file_path)
                audio.delete()
                audio.save()

            elif file_path.lower().endswith((".ogg", ".oga")):
                audio = OggVorbis(file_path)
                audio.delete()
                audio.save()

            elif file_path.lower().endswith(".wav"):
                try:
                    audio = WAVE(file_path)
                    if audio.tags:
                        audio.delete()
                        audio.save()
                except:
                    pass

            elif file_path.lower().endswith((".m4a", ".aac")):
                print(f"  Note: Metadata clearing may be limited for AAC/M4A format")

            elif file_path.lower().endswith(".wma"):
                print(f"  Note: Metadata clearing may be limited for WMA format")

            return True

        except Exception as e:
            print(f"  Warning: Could not clear metadata: {str(e)}")
            return False

    def safe_rename(self, old_path, new_path, max_retries=5, retry_delay=0.1):
        for attempt in range(max_retries):
            try:
                if old_path != new_path:
                    os.rename(old_path, new_path)
                return True
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"  Error: Failed to rename after {max_retries} attempts")
                    return False
            except Exception as e:
                print(f"  Error renaming file: {str(e)}")
                return False
        return False

    def is_file_already_numbered(self, filename):
        name, ext = os.path.splitext(filename)
        return name.isdigit()

    def get_sound_id(self, folder_name, file_number):
        return f"{folder_name}-{file_number}"

    def is_sound_in_json(self, data, sound_id):
        for category in data.get("categories", []):
            for item in category.get("categoryItems", []):
                if item.get("soundID") == sound_id:
                    return True
        return False

    def rename_and_update_sounds(self):
        try:
            with open(self.sounds_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.sounds_json} not found!")
            return False
        except json.JSONDecodeError:
            print(f"Error: {self.sounds_json} is not valid JSON!")
            return False

        if not os.path.exists(self.sounds_folder):
            print(f"Error: Sounds folder not found: {self.sounds_folder}")
            return False

        total_files = 0
        renamed_files = 0
        json_updates = 0

        for root, dirs, files in os.walk(self.sounds_folder):
            rel_path = os.path.relpath(root, self.sounds_folder)
            if rel_path == ".":
                continue

            folder_name = os.path.basename(root)
            category_name = folder_name.replace("-", " ").title()

            if folder_name.lower().startswith("oat1"):
                sound_source = "Open Alpha Playtest #1"
            elif folder_name.lower().startswith("oat2"):
                sound_source = "Open Alpha Playtest #2"
            elif folder_name.lower().startswith("oat3"):
                sound_source = "Open Alpha Playtest #3"
            elif folder_name.lower().startswith("oat4"):
                sound_source = "Open Alpha Playtest #4"
            else:
                sound_source = folder_name

            audio_files = [
                f
                for f in files
                if f.lower().endswith(
                    (".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma")
                )
            ]
            audio_files.sort()

            for i, filename in enumerate(audio_files, start=1):
                total_files += 1
                ext = os.path.splitext(filename)[1]
                new_filename = f"{i}{ext}"
                sound_id = f"{folder_name}-{i}"

                if self.is_file_already_numbered(filename) and self.is_sound_in_json(
                    data, sound_id
                ):
                    continue

                old_file_path = os.path.join(root, filename)
                new_file_path = os.path.join(root, new_filename)

                if os.path.exists(new_file_path) and old_file_path != new_file_path:
                    print(f"  Error: {new_filename} already exists")
                    continue

                if MUTAGEN_AVAILABLE:
                    self.clear_audio_metadata(old_file_path)

                if old_file_path != new_file_path:
                    if self.safe_rename(old_file_path, new_file_path):
                        renamed_files += 1
                        print(f"Renamed {filename} to {new_filename} in {folder_name}/")
                    else:
                        continue

                github_path = f"{rel_path.replace(os.path.sep, '/')}/{new_filename}"

                if not self.is_sound_in_json(data, sound_id):
                    category = None
                    for cat in data["categories"]:
                        if cat["categoryName"] == category_name:
                            category = cat
                            break

                    if category is None:
                        category = {
                            "categoryName": category_name,
                            "categoryDescription": f"Sound files from {folder_name} directory",
                            "categoryItems": [],
                        }
                        data["categories"].append(category)

                    new_entry = {
                        "soundID": sound_id,
                        "soundType": folder_name,
                        "soundSource": sound_source,
                        "soundFile": f"https://cdn.jsdelivr.net/gh/HEATLabs/Sound-Bank@main/sounds/{github_path}",
                        "soundName": f"{folder_name} - Sound {i}",
                        "soundDescription": f"Sound file from {folder_name} directory",
                    }

                    category["categoryItems"].append(new_entry)
                    json_updates += 1

        data["categories"].sort(key=lambda x: x["categoryName"])
        for category in data["categories"]:
            category["categoryItems"].sort(key=lambda x: x["soundID"])

        with open(self.sounds_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSound Number Sorter Summary:")
        print(f"Total files processed: {total_files}")
        print(f"Files renamed: {renamed_files}")
        print(f"JSON entries added/updated: {json_updates}")
        print(f"Updated: {self.sounds_json}")

        return True

    def run(self):
        print("RUNNING SOUND NUMBER SORTER")
        print("-" * 40)

        if not MUTAGEN_AVAILABLE:
            print("Warning: Mutagen library not available.")
            print("Metadata clearing will be skipped.")
            print("Install with: pip install mutagen")

        result = self.rename_and_update_sounds()
        input("\nPress Enter to return to main menu...")
        return result


# WEBP CONVERTER (Tool 2)
class WebPConverter:
    def __init__(self, quality=85):
        self.quality = quality

    def convert_png_to_webp(self, input_path, output_path):
        if not PIL_AVAILABLE:
            print("  Error: PIL/Pillow not available.")
            print("  Install with: pip install Pillow")
            return False

        try:
            with Image.open(input_path) as img:
                if img.mode in ("RGBA", "LA"):
                    img.save(output_path, "WebP", quality=self.quality, lossless=False)
                else:
                    img.save(output_path, "WebP", quality=self.quality)

            print(
                f"✓ Converted: {os.path.basename(input_path)} → {os.path.basename(output_path)}"
            )
            return True
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False

    def find_png_files(self, root_dir):
        png_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(".png"):
                    png_files.append(os.path.join(root, file))
        return png_files

    def run(self):
        print("RUNNING WEBP CONVERTER")
        print("-" * 40)

        if not PIL_AVAILABLE:
            print("Error: PIL/Pillow library not available.")
            print("Install with: pip install Pillow")
            input("\nPress Enter to return to main menu...")
            return False

        current_dir = os.getcwd()
        print(f"Looking for PNG files in: {current_dir} (including subdirectories)")

        png_files = self.find_png_files(current_dir)

        if not png_files:
            print("No PNG files found.")
            input("\nPress Enter to return to main menu...")
            return True

        print(f"Found {len(png_files)} PNG file(s):")
        for png_file in png_files[:10]:
            rel_path = os.path.relpath(png_file, current_dir)
            print(f"  - {rel_path}")
        if len(png_files) > 10:
            print(f"  ... and {len(png_files) - 10} more")

        print(f"\nQuality setting: {self.quality}")

        response = input("\nProceed with conversion? (y/n): ").strip().lower()
        if response not in ["y", "yes"]:
            print("Conversion cancelled.")
            input("\nPress Enter to return to main menu...")
            return True

        converted_count = 0
        failed_count = 0
        skipped_count = 0

        for i, png_file in enumerate(png_files, 1):
            base_name = os.path.splitext(png_file)[0]
            webp_file = f"{base_name}.webp"

            if os.path.exists(webp_file):
                rel_path = os.path.relpath(webp_file, current_dir)
                print(f"⚠ Skipped: {rel_path} already exists")
                skipped_count += 1
                continue

            print(f"[{i}/{len(png_files)}] ", end="")
            if self.convert_png_to_webp(png_file, webp_file):
                converted_count += 1
            else:
                failed_count += 1

        print(f"\nConversion Complete:")
        print(f"Successfully converted: {converted_count} files")
        if skipped_count > 0:
            print(f"Skipped (already exist): {skipped_count} files")
        if failed_count > 0:
            print(f"Failed: {failed_count} files")

        input("\nPress Enter to return to main menu...")
        return True


# THUMBNAIL GENERATOR (Tool 3)
class ThumbnailGenerator:
    def __init__(self, videos_dir=None):
        self.videos_dir = videos_dir or DEFAULT_VIDEOS_DIR
        self.output_subfolder = "thumbnails"
        self.ext_in = ".webm"
        self.ext_out = ".webp"

    def has_ffmpeg(self):
        if not SUBPROCESS_AVAILABLE:
            return False

        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except Exception:
            return False

    def make_thumbnail_ffmpeg(self, input_path, output_path):
        if not SUBPROCESS_AVAILABLE:
            return False

        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vframes", "1", str(output_path)]
        try:
            completed = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
            )
            return completed.returncode == 0 and output_path.exists()
        except Exception:
            return False

    def make_thumbnail_moviepy(self, input_path, output_path):
        try:
            from moviepy.editor import VideoFileClip
            from PIL import Image
        except Exception:
            return False

        try:
            clip = VideoFileClip(str(input_path))
            frame = clip.get_frame(1)
            img = Image.fromarray(frame)
            img.save(str(output_path), format="WEBP")
            clip.reader.close()
            if clip.audio:
                clip.audio.reader.close_proc()
            return output_path.exists()
        except Exception:
            return False

    def run(self):
        print("RUNNING THUMBNAIL GENERATOR")
        print("-" * 40)

        videos_dir = Path(self.videos_dir)
        if not videos_dir.exists() or not videos_dir.is_dir():
            print(f"Error: Videos directory not found: {videos_dir}")
            input("\nPress Enter to return to main menu...")
            return False

        out_dir = videos_dir / self.output_subfolder
        out_dir.mkdir(exist_ok=True)

        use_ffmpeg = self.has_ffmpeg()
        if use_ffmpeg:
            print("Using ffmpeg for thumbnail extraction.")
        else:
            print("ffmpeg not found. Will attempt fallback using moviepy + Pillow.")

        files = sorted(videos_dir.iterdir())
        processed = 0
        skipped = 0
        failed = 0

        webm_files = [
            f for f in files if f.is_file() and f.suffix.lower() == self.ext_in
        ]

        if not webm_files:
            print(f"No {self.ext_in} files found in {videos_dir}")
            input("\nPress Enter to return to main menu...")
            return True

        print(f"Found {len(webm_files)} {self.ext_in} files to process")

        for i, f in enumerate(webm_files, 1):
            out_file = out_dir / (f.stem + self.ext_out)

            if out_file.exists():
                print(f"⚠ Skipping: {f.name} (thumbnail already exists)")
                skipped += 1
                continue

            print(f"[{i}/{len(webm_files)}] Processing: {f.name}")

            if use_ffmpeg:
                ok = self.make_thumbnail_ffmpeg(f, out_file)
                if not ok:
                    ok = self.make_thumbnail_moviepy(f, out_file)
            else:
                ok = self.make_thumbnail_moviepy(f, out_file)

            if ok:
                print(f"  ✓ Created: {out_file.relative_to(videos_dir)}")
                processed += 1
            else:
                print(f"  ✗ Failed: {f.name}")
                failed += 1

        print(f"\nThumbnail Generation Complete:")
        print(f"Processed: {processed}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Thumbnails saved to: {out_dir}")

        input("\nPress Enter to return to main menu...")
        return True


# SOUND SOURCE FIXER (Tool 4)
class SoundSourceFixer:
    def __init__(self, sounds_json=None):
        self.sounds_json = sounds_json or DEFAULT_SOUNDS_JSON

    def update_sound_source(self):
        try:
            with open(self.sounds_json, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            print(f"Error: {self.sounds_json} not found!")
            return False
        except json.JSONDecodeError:
            print(f"Error: {self.sounds_json} is not valid JSON!")
            return False

        updates = 0
        for category in data.get("categories", []):
            for item in category.get("categoryItems", []):
                sound_file = item.get("soundFile", "")
                old_source = item.get("soundSource", "")

                if "/OAT1/" in sound_file and old_source != "Open Alpha Playtest #1":
                    item["soundSource"] = "Open Alpha Playtest #1"
                    updates += 1
                    print(
                        f"Updated: {item.get('soundID', 'Unknown')} → Open Alpha Playtest #1"
                    )
                elif "/OAT2/" in sound_file and old_source != "Open Alpha Playtest #2":
                    item["soundSource"] = "Open Alpha Playtest #2"
                    updates += 1
                    print(
                        f"Updated: {item.get('soundID', 'Unknown')} → Open Alpha Playtest #2"
                    )
                elif "/OAT3/" in sound_file and old_source != "Open Alpha Playtest #3":
                    item["soundSource"] = "Open Alpha Playtest #3"
                    updates += 1
                elif "/OAT4/" in sound_file and old_source != "Open Alpha Playtest #4":
                    item["soundSource"] = "Open Alpha Playtest #4"
                    updates += 1

        with open(self.sounds_json, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        print(f"\nSound Source Fixer Complete:")
        print(f"Updated {updates} sound source entries")
        print(f"Saved to: {self.sounds_json}")

        return True

    def run(self):
        print("RUNNING SOUND SOURCE FIXER")
        print("-" * 40)

        result = self.update_sound_source()
        input("\nPress Enter to return to main menu...")
        return result


# WAV TO MP3 CONVERTER (Tool 5)
class WavToMp3Converter:
    def __init__(self, root_directory=None, ffmpeg_path=None, bitrate="192k"):
        self.root_directory = root_directory or DEFAULT_SOUNDS_FOLDER
        self.ffmpeg_path = ffmpeg_path or DEFAULT_FFMPEG_PATH
        self.bitrate = bitrate

    def setup_ffmpeg(self):
        print("Setting up FFmpeg...")

        if not PYDUB_AVAILABLE:
            print("Error: pydub not available.")
            print("Install with: pip install pydub")
            return False

        if not SUBPROCESS_AVAILABLE:
            print("Error: subprocess module not available")
            return False

        if not os.path.exists(self.ffmpeg_path):
            print(f"✗ FFmpeg path does not exist: {self.ffmpeg_path}")
            return False

        ffmpeg_exe = os.path.join(self.ffmpeg_path, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            print(f"✗ ffmpeg.exe not found in: {self.ffmpeg_path}")
            return False

        os.environ["PATH"] = self.ffmpeg_path + os.pathsep + os.environ["PATH"]

        try:
            AudioSegment.converter = ffmpeg_exe
            AudioSegment.ffmpeg = ffmpeg_exe
            AudioSegment.ffprobe = os.path.join(self.ffmpeg_path, "ffprobe.exe")
        except Exception as e:
            print(f"✗ Error configuring pydub: {str(e)}")
            return False

        print(f"✓ FFmpeg configured: {ffmpeg_exe}")
        return True

    def find_wav_files(self):
        wav_files = []

        if not os.path.exists(self.root_directory):
            print(f"✗ Directory not found: {self.root_directory}")
            return []

        for root, dirs, files in os.walk(self.root_directory):
            for file in files:
                if file.lower().endswith(".wav"):
                    full_path = os.path.join(root, file)
                    wav_files.append(full_path)

        return wav_files

    def convert_wav_to_mp3(self, wav_file):
        try:
            output_path = os.path.splitext(wav_file)[0] + ".mp3"

            if os.path.exists(output_path):
                wav_mtime = os.path.getmtime(wav_file)
                mp3_mtime = os.path.getmtime(output_path)
                if mp3_mtime >= wav_mtime:
                    return "skipped", output_path

            audio = AudioSegment.from_wav(wav_file)
            audio.export(output_path, format="mp3", bitrate=self.bitrate)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return "success", output_path
            else:
                return "failed", None

        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return "failed", None

    def run(self):
        print("RUNNING WAV TO MP3 CONVERTER")
        print("-" * 40)

        if not PYDUB_AVAILABLE:
            print("Error: pydub library not available.")
            print("Install with: pip install pydub")
            input("\nPress Enter to return to main menu...")
            return False

        if not self.setup_ffmpeg():
            input("\nPress Enter to return to main menu...")
            return False

        wav_files = self.find_wav_files()

        if not wav_files:
            print(f"No WAV files found in: {self.root_directory}")
            input("\nPress Enter to return to main menu...")
            return True

        print(f"Found {len(wav_files)} WAV files")
        print(f"MP3 Bitrate: {self.bitrate}")

        response = input("\nProceed with conversion? (y/n): ").strip().lower()
        if response not in ["y", "yes"]:
            print("Conversion cancelled.")
            input("\nPress Enter to return to main menu...")
            return True

        successful = 0
        failed = 0
        skipped = 0
        converted_files = []

        for i, wav_file in enumerate(wav_files, 1):
            print(f"[{i}/{len(wav_files)}] {os.path.basename(wav_file)}")
            result, mp3_path = self.convert_wav_to_mp3(wav_file)

            if result == "success":
                successful += 1
                converted_files.append(wav_file)
                print(f"  ✓ Converted to MP3")
            elif result == "skipped":
                skipped += 1
                print(f"  ⚠ Already converted")
            else:
                failed += 1
                print(f"  ✗ Failed")

        print(f"\nConversion Summary:")
        print(f"Successful: {successful}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")

        if successful > 0:
            response = (
                input("\nDelete original WAV files that were converted? (y/n): ")
                .strip()
                .lower()
            )
            if response in ["y", "yes"]:
                deleted = 0
                for wav_file in converted_files:
                    try:
                        os.remove(wav_file)
                        deleted += 1
                    except Exception as e:
                        print(
                            f"  Error deleting {os.path.basename(wav_file)}: {str(e)}"
                        )
                print(f"Deleted {deleted} original WAV files")

        input("\nPress Enter to return to main menu...")
        return True


# MAIN UNIFIED TOOL
class MediaProcessingToolkit:
    def __init__(self):
        self.tools = {
            "1": ("Sound Number Sorter", self.run_sound_sorter),
            "2": ("WebP Converter", self.run_webp_converter),
            "3": ("Thumbnail Generator", self.run_thumbnail_generator),
            "4": ("Sound Source Fixer", self.run_sound_fixer),
            "5": ("WAV to MP3 Converter", self.run_wav_converter),
            "6": ("Run All Tools", self.run_all_tools),
            "0": ("Quit", self.quit_tool),
        }
        self.running = True

    def display_menu(self):
        os.system("cls" if os.name == "nt" else "clear")
        print("Media Processing Suite")
        print("Available Tools:")

        for key, (name, _) in self.tools.items():
            print(f"{key}. {name}")

        print("\n" + "-" * 60)

        # Show dependency status
        print("Dependency Status:")
        print(
            f"Mutagen (audio metadata): {'✓ Available' if MUTAGEN_AVAILABLE else '✗ Not installed'}"
        )
        print(
            f"PIL/Pillow (image processing): {'✓ Available' if PIL_AVAILABLE else '✗ Not installed'}"
        )
        print(
            f"pydub (audio conversion): {'✓ Available' if PYDUB_AVAILABLE else '✗ Not installed'}"
        )
        print("-" * 60)

    def run_sound_sorter(self):
        tool = SoundNumberSorter()
        return tool.run()

    def run_webp_converter(self):
        # Ask for quality setting
        quality = 85
        response = input(f"Enter WebP quality (1-100, default 85): ").strip()
        if response and response.isdigit():
            q = int(response)
            if 1 <= q <= 100:
                quality = q
        tool = WebPConverter(quality=quality)
        return tool.run()

    def run_thumbnail_generator(self):
        # Ask for videos directory
        default_dir = DEFAULT_VIDEOS_DIR
        response = input(f"Enter videos directory (default: {default_dir}): ").strip()
        videos_dir = response if response else default_dir
        tool = ThumbnailGenerator(videos_dir=videos_dir)
        return tool.run()

    def run_sound_fixer(self):
        tool = SoundSourceFixer()
        return tool.run()

    def run_wav_converter(self):
        # Ask for bitrate
        bitrate = "192k"
        response = input(f"Enter MP3 bitrate (default: 192k): ").strip()
        if response:
            bitrate = response if response.endswith("k") else f"{response}k"

        # Ask for FFmpeg path
        ffmpeg_path = DEFAULT_FFMPEG_PATH
        response = input(f"Enter FFmpeg path (default: {ffmpeg_path}): ").strip()
        if response:
            ffmpeg_path = response

        tool = WavToMp3Converter(bitrate=bitrate, ffmpeg_path=ffmpeg_path)
        return tool.run()

    def run_all_tools(self):
        print("RUNNING ALL MEDIA PROCESSING TOOLS")

        tools_to_run = [
            ("Sound Number Sorter", self.run_sound_sorter),
            ("WebP Converter", self.run_webp_converter),
            ("Thumbnail Generator", self.run_thumbnail_generator),
            ("Sound Source Fixer", self.run_sound_fixer),
            ("WAV to MP3 Converter", self.run_wav_converter),
        ]

        for i, (name, func) in enumerate(tools_to_run, 1):
            print(f"\n[{i}/{len(tools_to_run)}] Running {name}...")
            print("-" * 40)
            try:
                func()
            except Exception as e:
                print(f"Error running {name}: {e}")
                continue

        print("\n" + "=" * 60)
        print("ALL MEDIA PROCESSING TOOLS COMPLETED")
        input("\nPress Enter to return to main menu...")
        return True

    def quit_tool(self):
        print("\nThank you for using Media Processing Toolkit!")
        self.running = False
        return False

    def run(self):
        while self.running:
            self.display_menu()
            choice = input("\nSelect an option (0-6): ").strip()

            if choice in self.tools:
                tool_name, tool_func = self.tools[choice]
                print(f"\nSelected: {tool_name}")
                print("-" * 40)
                tool_func()
            else:
                print(f"\nInvalid option: {choice}")
                print("Please select a valid option (0-6).")
                input("\nPress Enter to continue...")


# Command line interface
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Media Processing Toolkit - Combine all media processing tools into one application"
    )
    parser.add_argument(
        "--tool",
        type=int,
        choices=range(0, 7),
        help="Directly run a specific tool (0-6, where 0=Quit, 6=All Tools)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="WebP quality setting (1-100, default: 85)",
    )
    parser.add_argument(
        "--bitrate",
        type=str,
        default="192k",
        help="MP3 bitrate (e.g., 128k, 192k, 320k, default: 192k)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    toolkit = MediaProcessingToolkit()

    if args.tool is not None:
        # Direct mode
        choice = str(args.tool)
        if choice in toolkit.tools:
            tool_name, tool_func = toolkit.tools[choice]
            print(f"\nRunning: {tool_name}")
            if choice == "0":
                toolkit.quit_tool()
            else:
                tool_func()
                if choice != "6":
                    print("\nTool execution completed.")
        else:
            print(f"Invalid tool number: {args.tool}")
    else:
        # Interactive mode
        toolkit.run()


if __name__ == "__main__":
    main()
