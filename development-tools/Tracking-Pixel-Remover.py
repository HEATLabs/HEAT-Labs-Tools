import os
import re


def remove_tracking_pixel(file_path):
    # Tracking pixel pattern
    tracking_pixel_pattern = re.compile(
        r"<!-- JsDelivr-based Tracking Pixel -->\s*"
        r'<img src="https://cdn\.jsdelivr\.net/gh/PCWStats/Website-Images@refs/heads/main/trackers/pcwstats-tracker-pixel-[a-zA-Z0-9-]+\.png" alt="" style="position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;" class="pcwstats-tracking-pixel" data-page="[a-zA-Z0-9-]+">\s*',
        re.IGNORECASE,
    )

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Remove all instances of the tracking pixel
        new_content = tracking_pixel_pattern.sub("", content)

        # Only write if content changed
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(new_content)
            print(f"Removed tracking pixel from: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")


def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                remove_tracking_pixel(file_path)


if __name__ == "__main__":
    # Path to site repository
    target_directory = "../../pcwstats.github.io"

    if os.path.exists(target_directory):
        print(f"Processing directory: {target_directory}")
        process_directory(target_directory)
        print("Finished processing all HTML files.")
    else:
        print(f"Directory not found: {target_directory}")
