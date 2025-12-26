# file name: Tracking-Pixel-Toolkit.py
import os
import sys
import json
import re
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
DEFAULT_WEBSITE_DIR = "../../HEAT-Labs-Website"
DEFAULT_IMAGES_DIR = "../../HEAT-Labs-Views-API/trackers"
DEFAULT_BASE_PIXEL_NAME = "pcwstats-tracker-pixel.png"
DEFAULT_BASE_CDN_URL = "https://views.heatlabs.net/api/track"
DEFAULT_TRACKING_JSON = "../../HEAT-Labs-Configs/tracking-pixel.json"


# TRACKING PIXEL REMOVER (Tool 1)
class TrackingPixelRemover:
    def __init__(self, website_dir=None):
        self.website_dir = website_dir or DEFAULT_WEBSITE_DIR

    def remove_tracking_pixel(self, file_path):
        # Tracking pixel pattern (same as original)
        tracking_pixel_pattern = re.compile(
            r"<!-- JsDelivr-based Tracking Pixel -->\s*"
            r'<img src="https://cdn\.jsdelivr\.net/gh/HEATLabs/HEAT-Labs-Images@refs/heads/main/trackers/pcwstats-tracker-pixel-[a-zA-Z0-9-]+\.png" alt="HEAT Labs Tracking View Counter" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;" class="heatlabs-tracking-pixel" data-page="[a-zA-Z0-9-]+">\s*',
            re.IGNORECASE,
        )

        # Also try to match the newer pattern from the generator
        tracking_pixel_pattern_alt = re.compile(
            r"<!-- Custom Privacy-Focused Tracking Pixel -->\s*"
            r'<img src="https://views\.heatlabs\.net/api/track/pcwstats-tracker-pixel-[a-zA-Z0-9-]+\.png" alt="HEAT Labs Tracking View Counter" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;" class="heatlabs-tracking-pixel" data-page="[a-zA-Z0-9-]+">\s*',
            re.IGNORECASE,
        )

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            # Remove all instances of tracking pixels
            original_content = content
            content = tracking_pixel_pattern.sub("", content)
            content = tracking_pixel_pattern_alt.sub("", content)

            # Also remove any stray heatlabs-tracking-pixel class references
            if "heatlabs-tracking-pixel" in content:
                # Look for any img tags with this class
                generic_pattern = re.compile(
                    r'<img[^>]*class="[^"]*heatlabs-tracking-pixel[^"]*"[^>]*>\s*',
                    re.IGNORECASE,
                )
                content = generic_pattern.sub("", content)

            # Only write if content changed
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)
                return True
            return False

        except Exception as e:
            print(f"  Error processing {file_path}: {str(e)}")
            return False

    def process_directory(self):
        if not os.path.exists(self.website_dir):
            print(f"Error: Website directory not found: {self.website_dir}")
            return False

        html_files = []
        for root, _, files in os.walk(self.website_dir):
            for file in files:
                if file.endswith(".html"):
                    html_files.append(os.path.join(root, file))

        if not html_files:
            print("No HTML files found in the website directory")
            return True

        print(f"Found {len(html_files)} HTML files to process")

        removed_count = 0
        failed_count = 0

        for i, html_file in enumerate(html_files, 1):
            print(f"[{i}/{len(html_files)}] Processing: {os.path.basename(html_file)}")
            if self.remove_tracking_pixel(html_file):
                removed_count += 1
                print(f"  ✓ Removed tracking pixel")
            else:
                failed_count += 1
                print(f"  ⚠ No tracking pixel found or error")

        print(f"\nTracking Pixel Removal Complete:")
        print(f"Files processed: {len(html_files)}")
        print(f"Tracking pixels removed: {removed_count}")
        print(f"Files unchanged: {failed_count}")

        return True

    def run(self):
        print("RUNNING TRACKING PIXEL REMOVER")
        print("-" * 40)

        if not os.path.exists(self.website_dir):
            print(f"Error: Website directory not found: {self.website_dir}")
            input("\nPress Enter to return to main menu...")
            return False

        print(f"Website directory: {self.website_dir}")
        print("\nThis will remove all tracking pixels from HTML files.")

        response = input("\nProceed? (y/n): ").strip().lower()
        if response not in ["y", "yes"]:
            print("Operation cancelled.")
            input("\nPress Enter to return to main menu...")
            return True

        result = self.process_directory()
        input("\nPress Enter to return to main menu...")
        return result


# TRACKING PIXEL GENERATOR (Tool 2)
class TrackingPixelGenerator:
    def __init__(
        self,
        website_dir=None,
        images_dir=None,
        base_pixel_name=None,
        base_cdn_url=None,
        tracking_json=None,
    ):
        self.website_dir = website_dir or DEFAULT_WEBSITE_DIR
        self.images_dir = images_dir or DEFAULT_IMAGES_DIR
        self.base_pixel_name = base_pixel_name or DEFAULT_BASE_PIXEL_NAME
        self.base_cdn_url = base_cdn_url or DEFAULT_BASE_CDN_URL
        self.tracking_json = tracking_json or DEFAULT_TRACKING_JSON

    def get_page_name_from_title(self, title):
        if not title:
            return "Unknown"
        clean_title = title.replace(" - HEAT Labs", "").strip()
        return clean_title if clean_title else "Unknown"

    def get_page_identifier(self, html_file_path):
        filename = Path(html_file_path).stem
        identifier = re.sub(r"[^a-zA-Z0-9]", "-", filename).lower()
        identifier = re.sub(r"-+", "-", identifier).strip("-")
        return identifier

    def create_tracking_pixel(self, base_pixel_path, new_pixel_path, page_identifier):
        try:
            if os.path.exists(base_pixel_path):
                shutil.copy2(base_pixel_path, new_pixel_path)
                return True
            else:
                print(f"  Warning: Base pixel not found at {base_pixel_path}")
                return False
        except Exception as e:
            print(f"  Error creating pixel for {page_identifier}: {e}")
            return False

    def add_tracking_pixel_to_html(self, html_file_path, pixel_url, page_identifier):
        try:
            with open(html_file_path, "r", encoding="utf-8") as file:
                content = file.read()

            # Check if tracking pixel already exists
            if "heatlabs-tracking-pixel" in content:
                return True  # Already has a pixel

            pixel_comment = "<!-- Custom Privacy-Focused Tracking Pixel -->"
            pixel_img = f'<img src="{pixel_url}" alt="HEAT Labs Tracking View Counter" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;" class="heatlabs-tracking-pixel" data-page="{page_identifier}">'
            pixel_block = f"{pixel_comment}\n    {pixel_img}"

            body_open_pattern = r"(<body[^>]*>)(\s*)"

            if re.search(body_open_pattern, content, re.IGNORECASE):
                modified_content = re.sub(
                    body_open_pattern,
                    rf"\1\n    {pixel_block}\2",
                    content,
                    flags=re.IGNORECASE,
                )

                with open(html_file_path, "w", encoding="utf-8") as file:
                    file.write(modified_content)

                return True
            else:
                print(f"  Warning: No opening <body> tag found")
                return False

        except Exception as e:
            print(f"  Error processing HTML: {e}")
            return False

    def get_html_title(self, html_file_path):
        try:
            with open(html_file_path, "r", encoding="utf-8") as file:
                content = file.read()

            title_match = re.search(
                r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL
            )
            if title_match:
                return title_match.group(1).strip()
            return None
        except Exception as e:
            print(f"  Error reading title: {e}")
            return None

    def load_existing_tracking_data(self):
        try:
            if os.path.exists(self.tracking_json):
                with open(self.tracking_json, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_pixels = {
                        p["html_file"]: p for p in existing_data.get("pixels", [])
                    }
                    return existing_data, existing_pixels
        except Exception as e:
            print(f"Warning: Could not load existing tracking data: {e}")

        return {
            "generated_at": datetime.now().isoformat(),
            "base_cdn_url": self.base_cdn_url,
            "pixels": [],
        }, {}

    def run(self):
        print("RUNNING TRACKING PIXEL GENERATOR")
        print("-" * 40)

        # Verify directories exist
        if not os.path.exists(self.website_dir):
            print(f"Error: Website directory not found: {self.website_dir}")
            input("\nPress Enter to return to main menu...")
            return False

        if not os.path.exists(self.images_dir):
            print(f"Error: Images directory not found: {self.images_dir}")
            input("\nPress Enter to return to main menu...")
            return False

        base_pixel_path = os.path.join(self.images_dir, self.base_pixel_name)
        if not os.path.exists(base_pixel_path):
            print(f"Error: Base pixel not found: {base_pixel_path}")
            input("\nPress Enter to return to main menu...")
            return False

        print(f"Website directory: {self.website_dir}")
        print(f"Images directory: {self.images_dir}")
        print(f"Base pixel: {self.base_pixel_name}")
        print(f"Tracking JSON: {self.tracking_json}")

        response = (
            input("\nProceed with adding tracking pixels? (y/n): ").strip().lower()
        )
        if response not in ["y", "yes"]:
            print("Operation cancelled.")
            input("\nPress Enter to return to main menu...")
            return True

        # Load existing data
        tracking_data, existing_pixels = self.load_existing_tracking_data()
        tracking_data["generated_at"] = datetime.now().isoformat()

        website_path = Path(self.website_dir)
        images_path = Path(self.images_dir)
        html_files = list(website_path.rglob("*.html"))

        if not html_files:
            print("No HTML files found in the website directory")
            input("\nPress Enter to return to main menu...")
            return True

        print(f"\nFound {len(html_files)} HTML files to process")

        failed_files = []
        skipped_files = []
        new_pixels_added = 0

        for i, html_file in enumerate(html_files, 1):
            try:
                relative_path = html_file.relative_to(website_path)
                normalized_path = str(relative_path).replace(os.sep, "/")

                print(f"[{i}/{len(html_files)}] Processing: {relative_path}")

                # Skip if already in tracking data
                if normalized_path in existing_pixels:
                    skipped_files.append(str(html_file))
                    print("  ⚠ Already in tracking data - skipping")
                    continue

                page_identifier = self.get_page_identifier(html_file)
                html_title = self.get_html_title(html_file)
                page_name = self.get_page_name_from_title(html_title)

                pixel_filename = f"pcwstats-tracker-pixel-{page_identifier}.png"
                pixel_path = images_path / pixel_filename
                pixel_url = f"{self.base_cdn_url}/{pixel_filename}"

                # Skip if pixel already exists in HTML
                with open(html_file, "r", encoding="utf-8") as file:
                    if "pcwstats-tracking-pixel" in file.read():
                        skipped_files.append(str(html_file))
                        print("  ⚠ Already has tracking pixel - skipping")
                        continue

                pixel_created = self.create_tracking_pixel(
                    base_pixel_path, pixel_path, page_identifier
                )

                html_updated = False
                if pixel_created:
                    html_updated = self.add_tracking_pixel_to_html(
                        html_file, pixel_url, page_identifier
                    )

                if pixel_created and html_updated:
                    tracking_data["pixels"].append(
                        {
                            "page_name": page_name,
                            "page_identifier": page_identifier,
                            "html_file": normalized_path,
                            "pixel_filename": pixel_filename,
                            "pixel_url": pixel_url,
                            "html_title": html_title,
                        }
                    )
                    new_pixels_added += 1
                    print(f"  ✓ Added tracking pixel")
                else:
                    failure_reason = []
                    if not pixel_created:
                        failure_reason.append("pixel creation failed")
                    if not html_updated:
                        failure_reason.append("HTML update failed")
                    failed_files.append(
                        {
                            "file": str(html_file),
                            "reason": ", ".join(failure_reason) or "unknown reason",
                        }
                    )
                    print(f"  ✗ Failed: {', '.join(failure_reason)}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                failed_files.append(
                    {"file": str(html_file), "reason": f"exception: {str(e)}"}
                )

        # Save tracking JSON
        json_path = Path(self.tracking_json)
        try:
            os.makedirs(json_path.parent, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)
            print(f"\nTracking data saved to: {json_path}")
        except Exception as e:
            print(f"Error saving tracking JSON: {e}")

        print(f"\nTracking Pixel Generation Complete:")
        print(f"Total HTML files found: {len(html_files)}")
        print(f"Existing tracking entries: {len(existing_pixels)}")
        print(f"New pixels added: {new_pixels_added}")
        print(f"Skipped: {len(skipped_files)}")
        print(f"Failed: {len(failed_files)}")

        input("\nPress Enter to return to main menu...")
        return True


# MAIN UNIFIED TOOL
class TrackingPixelToolkit:
    def __init__(self):
        self.tools = {
            "1": ("Tracking Pixel Remover", self.run_pixel_remover),
            "2": ("Tracking Pixel Generator", self.run_pixel_generator),
            "3": ("Run Both Tools", self.run_both_tools),
            "0": ("Quit", self.quit_tool),
        }
        self.running = True

    def display_menu(self):
        os.system("cls" if os.name == "nt" else "clear")
        print("Tracking Pixel Manager")
        print("Available Tools:")

        for key, (name, _) in self.tools.items():
            print(f"{key}. {name}")

        print("\n" + "-" * 60)
        print(f"Default website directory: {DEFAULT_WEBSITE_DIR}")
        print(f"Default images directory: {DEFAULT_IMAGES_DIR}")
        print("-" * 60)

    def run_pixel_remover(self):
        # Option to customize directory
        default_dir = DEFAULT_WEBSITE_DIR
        response = input(f"Enter website directory (default: {default_dir}): ").strip()
        website_dir = response if response else default_dir

        tool = TrackingPixelRemover(website_dir=website_dir)
        return tool.run()

    def run_pixel_generator(self):
        # Option to customize settings
        default_website = DEFAULT_WEBSITE_DIR
        response = input(
            f"Enter website directory (default: {default_website}): "
        ).strip()
        website_dir = response if response else default_website

        default_images = DEFAULT_IMAGES_DIR
        response = input(
            f"Enter images directory (default: {default_images}): "
        ).strip()
        images_dir = response if response else default_images

        default_json = DEFAULT_TRACKING_JSON
        response = input(
            f"Enter tracking JSON path (default: {default_json}): "
        ).strip()
        tracking_json = response if response else default_json

        tool = TrackingPixelGenerator(
            website_dir=website_dir, images_dir=images_dir, tracking_json=tracking_json
        )
        return tool.run()

    def run_both_tools(self):
        print("RUNNING BOTH TRACKING PIXEL TOOLS")

        print("\nStep 1: Removing existing tracking pixels...")
        print("-" * 40)
        self.run_pixel_remover()

        print("\nStep 2: Generating new tracking pixels...")
        print("-" * 40)
        self.run_pixel_generator()

        print("BOTH TOOLS COMPLETED")
        input("\nPress Enter to return to main menu...")
        return True

    def quit_tool(self):
        print("\nThank you for using Tracking Pixel Manager!")
        self.running = False
        return False

    def run(self):
        while self.running:
            self.display_menu()
            choice = input("\nSelect an option (0-3): ").strip()

            if choice in self.tools:
                tool_name, tool_func = self.tools[choice]
                print(f"\nSelected: {tool_name}")
                print("-" * 40)
                tool_func()
            else:
                print(f"\nInvalid option: {choice}")
                print("Please select a valid option (0-3).")
                input("\nPress Enter to continue...")


# Command line interface
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Tracking Pixel Toolkit - Combine tracking pixel removal and generation tools"
    )
    parser.add_argument(
        "--tool",
        type=int,
        choices=range(0, 4),
        help="Directly run a specific tool (0-3, where 0=Quit, 3=Both Tools)",
    )
    parser.add_argument(
        "--website-dir",
        type=str,
        default=DEFAULT_WEBSITE_DIR,
        help=f"Website directory path (default: {DEFAULT_WEBSITE_DIR})",
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=DEFAULT_IMAGES_DIR,
        help=f"Images directory path (default: {DEFAULT_IMAGES_DIR})",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    toolkit = TrackingPixelToolkit()

    if args.tool is not None:
        # Direct mode
        choice = str(args.tool)
        if choice in toolkit.tools:
            tool_name, tool_func = toolkit.tools[choice]
            print(f"\nRunning: {tool_name}")
            if choice == "0":
                toolkit.quit_tool()
            else:
                # For direct mode, use command line arguments
                if choice == "1":
                    tool = TrackingPixelRemover(website_dir=args.website_dir)
                    tool.run()
                elif choice == "2":
                    tool = TrackingPixelGenerator(
                        website_dir=args.website_dir, images_dir=args.images_dir
                    )
                    tool.run()
                elif choice == "3":
                    print("\nRunning both tools sequentially...")
                    remover = TrackingPixelRemover(website_dir=args.website_dir)
                    remover.run()
                    print()
                    generator = TrackingPixelGenerator(
                        website_dir=args.website_dir, images_dir=args.images_dir
                    )
                    generator.run()
                print("\nTool execution completed.")
        else:
            print(f"Invalid tool number: {args.tool}")
    else:
        # Interactive mode
        toolkit.run()


if __name__ == "__main__":
    main()
