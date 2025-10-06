import os
import json
import shutil
from pathlib import Path
import re
from datetime import datetime

# Configuration
WEBSITE_DIR = "../../heatlabs.github.io"
IMAGES_DIR = "../../HEATLabs-Views-API/trackers"
BASE_PIXEL_NAME = "pcwstats-tracker-pixel.png"
BASE_CDN_URL = "https://views.heatlabs.net/api/track"
TRACKING_JSON_FILE = "../../Website-Configs/tracking-pixel.json"


def get_page_name_from_title(title):
    if not title:
        return "Unknown"
    clean_title = title.replace(" - HEAT Labs", "").strip()
    return clean_title if clean_title else "Unknown"


def get_page_identifier(html_file_path):
    filename = Path(html_file_path).stem
    identifier = re.sub(r"[^a-zA-Z0-9]", "-", filename).lower()
    identifier = re.sub(r"-+", "-", identifier).strip("-")
    return identifier


def create_tracking_pixel(base_pixel_path, new_pixel_path, page_identifier):
    try:
        if os.path.exists(base_pixel_path):
            shutil.copy2(base_pixel_path, new_pixel_path)
            print(f"Created tracking pixel: {os.path.basename(new_pixel_path)}")
            return True
        else:
            print(f"Warning: Base pixel not found at {base_pixel_path}")
            return False
    except Exception as e:
        print(f"Error creating pixel for {page_identifier}: {e}")
        return False


def add_tracking_pixel_to_html(html_file_path, pixel_url, page_identifier):
    try:
        with open(html_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        if "heatlabs-tracking-pixel" in content:
            print(
                f"Tracking pixel already exists in {os.path.basename(html_file_path)}"
            )
            return True

        pixel_comment = "<!-- Custom Privacy-Focused Tracking Pixel -->"
        pixel_img = f'<img src="{pixel_url}" alt="" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;" class="heatlabs-tracking-pixel" data-page="{page_identifier}">'
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

            print(f"Added tracking pixel to {os.path.basename(html_file_path)}")
            return True
        else:
            print(f"Warning: No opening <body> tag found in {html_file_path}")
            return False

    except Exception as e:
        print(f"Error processing {html_file_path}: {e}")
        return False


def get_html_title(html_file_path):
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
        print(f"Error reading title from {html_file_path}: {e}")
        return None


def load_existing_tracking_data():
    try:
        if os.path.exists(TRACKING_JSON_FILE):
            with open(TRACKING_JSON_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                # Convert the list of pixels to a dictionary for easier lookup
                existing_pixels = {
                    p["html_file"]: p for p in existing_data.get("pixels", [])
                }
                return existing_data, existing_pixels
    except Exception as e:
        print(f"Warning: Could not load existing tracking data: {e}")

    # Return default structure if file doesn't exist or can't be read
    return {
        "generated_at": datetime.now().isoformat(),
        "base_cdn_url": BASE_CDN_URL,
        "pixels": [],
    }, {}


def process_html_files():
    # Load existing data or create new structure
    tracking_data, existing_pixels = load_existing_tracking_data()
    tracking_data["generated_at"] = datetime.now().isoformat()  # Update generation time

    failed_files = []
    skipped_files = []
    new_pixels_added = 0

    website_path = Path(WEBSITE_DIR)
    images_path = Path(IMAGES_DIR)

    if not website_path.exists():
        print(f"Error: Website directory not found: {WEBSITE_DIR}")
        return

    if not images_path.exists():
        print(f"Error: Images directory not found: {IMAGES_DIR}")
        return

    base_pixel_path = images_path / BASE_PIXEL_NAME
    html_files = list(website_path.rglob("*.html"))

    if not html_files:
        print("No HTML files found in the website directory")
        return

    print(f"Found {len(html_files)} HTML files to process")

    for html_file in html_files:
        try:
            relative_path = html_file.relative_to(website_path)
            normalized_path = str(relative_path).replace(os.sep, "/")

            # Skip if this file is already in our tracking data
            if normalized_path in existing_pixels:
                skipped_files.append(str(html_file))
                continue

            page_identifier = get_page_identifier(html_file)
            html_title = get_html_title(html_file)
            page_name = get_page_name_from_title(html_title)

            pixel_filename = f"pcwstats-tracker-pixel-{page_identifier}.png"
            pixel_path = images_path / pixel_filename
            pixel_url = f"{BASE_CDN_URL}/{pixel_filename}"

            # Skip if pixel already exists in HTML (even if not in our JSON)
            with open(html_file, "r", encoding="utf-8") as file:
                if "pcwstats-tracking-pixel" in file.read():
                    skipped_files.append(str(html_file))
                    continue

            pixel_created = create_tracking_pixel(
                base_pixel_path, pixel_path, page_identifier
            )
            html_updated = False

            if pixel_created:
                html_updated = add_tracking_pixel_to_html(
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

        except Exception as e:
            print(f"Error processing {html_file}: {e}")
            failed_files.append(
                {"file": str(html_file), "reason": f"exception: {str(e)}"}
            )

    # Save tracking JSON
    json_path = Path(TRACKING_JSON_FILE)
    try:
        os.makedirs(json_path.parent, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        print(f"\nTracking data saved to: {json_path}")
    except Exception as e:
        print(f"Error saving tracking JSON: {e}")

    # Print comprehensive report
    print(f"\nProcessing complete!")
    print(f"Total HTML files found: {len(html_files)}")
    print(f"Existing tracking entries: {len(existing_pixels)}")
    print(f"New pixels added: {new_pixels_added}")
    print(f"Skipped (already had pixels): {len(skipped_files)}")
    print(f"Failed to process: {len(failed_files)}")

    if skipped_files:
        print("\nSkipped files (already had tracking pixels):")
        for file in skipped_files:
            print(f"  - {file}")

    if failed_files:
        print("\nFailed to process these files:")
        for failure in failed_files:
            print(f"  - {failure['file']} ({failure['reason']})")

    # Compare against all HTML files to find any completely missed files
    processed_files = {p["html_file"] for p in tracking_data["pixels"]}
    all_html_files = {
        str(f.relative_to(website_path).as_posix())
        for f in website_path.rglob("*.html")
    }
    missing_files = (
        all_html_files
        - processed_files
        - {
            str(Path(f["file"]).relative_to(website_path).as_posix())
            for f in failed_files
        }
        - {str(Path(f).relative_to(website_path).as_posix()) for f in skipped_files}
    )

    if missing_files:
        print("\nFiles not processed at all (not in success, failed or skipped lists):")
        for file in missing_files:
            print(f"  - {file}")


def main():
    print("HEAT Labs Tracking Pixel Generator")
    print("=" * 50)

    if not os.path.exists(WEBSITE_DIR):
        print(f"Error: Website directory not found: {WEBSITE_DIR}")
        print("Please make sure the path is correct and the directory exists.")
        return

    if not os.path.exists(IMAGES_DIR):
        print(f"Error: Images directory not found: {IMAGES_DIR}")
        print("Please make sure the path is correct and the directory exists.")
        return

    base_pixel = os.path.join(IMAGES_DIR, BASE_PIXEL_NAME)
    if not os.path.exists(base_pixel):
        print(f"Error: Base tracking pixel not found: {base_pixel}")
        print("Please make sure the base pixel file exists.")
        return

    print(f"Website directory: {WEBSITE_DIR}")
    print(f"Images directory: {IMAGES_DIR}")
    print(f"Base pixel: {BASE_PIXEL_NAME}")
    print()

    response = input("Do you want to proceed with adding tracking pixels? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        print("Operation cancelled.")
        return

    process_html_files()


if __name__ == "__main__":
    main()
