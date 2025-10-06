import os
import re
import json
import requests
import time
from datetime import datetime, timezone

# Configuration
TARGET_DIR = "../../heatlabs.github.io"
ADDITIONAL_DIRS = ["../../Database-Files", "../../HEAT-Labs-Configs"]
JSON_FILENAME = "../../HEAT-Labs-Configs/jsdelivr-data.json"
CDN_REGEX = re.compile(
    r'https://cdn\.jsdelivr\.net/gh/[\w\-]+/[\w\-]+@[\w\-]+/[^"\'\s)]+'
)

# Repository mapping for cleaner names
REPO_MAPPING = {
    TARGET_DIR: "heatlabs.github.io",
    "../../HEAT-Labs-Database": "HEAT-Labs-Database",
    "../../HEAT-Labs-Configs": "HEAT-Labs-Configs",
    "../../HEAT-Labs-Changelog": "HEAT-Labs-Changelog",
    "../../HEAT-Labs-Status": "HEAT-Labs-Status",
    "../../HEAT-Labs-Discord": "HEAT-Labs-Discord",
    "../../HEAT-Labs-Statistics": "HEAT-Labs-Statistics",
    "../../HEAT-Labs-Configurator": "HEAT-Labs-Configurator",
}


# Get clean repository name from directory path
def get_repo_name(directory):
    return REPO_MAPPING.get(directory, os.path.basename(directory))

    # Find jsDelivr URLs in a directory and return with metadata


def find_jsdelivr_urls(root_dir, scan_json=False):
    found_urls = {}
    repo_name = get_repo_name(root_dir)

    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            # Determine file extensions to scan
            if scan_json:
                valid_extensions = (".js", ".css", ".html", ".json")
            else:
                valid_extensions = (".js", ".css", ".html")

            if file.endswith(valid_extensions):
                full_path = os.path.join(dirpath, file)

                # Skip jsdelivr-data.json file to avoid self-reference
                if os.path.abspath(full_path) == os.path.abspath(JSON_FILENAME):
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        matches = CDN_REGEX.findall(content)
                        for url in matches:
                            found_urls[url] = {
                                "repository": repo_name,
                                "discovered": datetime.now(timezone.utc).isoformat(),
                                "last_purged": None,
                            }
                except Exception as e:
                    print(f"Could not read {full_path}: {e}")

    return found_urls


# Load existing URL data from JSON file
def load_existing_data(json_file):
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading existing data: {e}")
            return {}
    return {}


# Save URL data to JSON file
def save_data(json_file, urls_data):
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(urls_data, f, indent=2, sort_keys=True)
    except Exception as e:
        print(f"Error saving data: {e}")


# Update the last_purged timestamp for successfully purged URLs
def update_purge_timestamp(urls_data, purged_urls):
    current_time = datetime.now(timezone.utc).isoformat()
    for url in purged_urls:
        if url in urls_data:
            urls_data[url]["last_purged"] = current_time


# Purge URLs one by one
def purge_urls(urls, delay=0.2):
    successfully_purged = []
    for url in urls:
        if purge_single_url(url, delay):
            successfully_purged.append(url)
    return successfully_purged


# Purge a single URL
def purge_single_url(url, delay=1):
    purge_url = url.replace("https://cdn.jsdelivr.net/", "https://purge.jsdelivr.net/")
    try:
        response = requests.get(purge_url)
        if response.status_code == 200:
            print(f"Purged: {url}")
            if delay > 0:
                time.sleep(delay)
            return True
        else:
            print(f"Failed to purge: {url} | Status: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error purging {url}: {e}")
        return False


# Get choice from a list of options
def get_user_choice(prompt, options):
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    while True:
        try:
            choice = int(input(f"\nEnter your choice (1-{len(options)}): "))
            if 1 <= choice <= len(options):
                return choice - 1
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


# Scan all directories for jsDelivr URLs
def scan_for_urls():
    print("Scanning for jsDelivr URLs...")
    all_urls_data = {}

    # Scan main target directory
    main_urls = find_jsdelivr_urls(TARGET_DIR)
    print(f"Found {len(main_urls)} URLs in {get_repo_name(TARGET_DIR)}")
    all_urls_data.update(main_urls)

    # Scan additional directories
    for additional_dir in ADDITIONAL_DIRS:
        if os.path.exists(additional_dir):
            additional_urls = find_jsdelivr_urls(additional_dir, scan_json=True)
            print(
                f"Found {len(additional_urls)} URLs in {get_repo_name(additional_dir)}"
            )
            all_urls_data.update(additional_urls)
        else:
            print(f"Directory not found: {additional_dir}")

    return all_urls_data


# Filter URLs by repository name
def filter_urls_by_repo(urls_data, repo_name):
    if repo_name == "all":
        return urls_data

    filtered = {}
    for url, data in urls_data.items():
        if data.get("repository") == repo_name:
            filtered[url] = data
    return filtered


# Display statistics about URLs
def display_url_stats(urls_data):
    repo_counts = {}
    purged_count = 0

    for url, data in urls_data.items():
        repo = data.get("repository", "unknown")
        repo_counts[repo] = repo_counts.get(repo, 0) + 1
        if data.get("last_purged"):
            purged_count += 1

    print(f"\nURL Statistics:")
    print(f"   Total URLs: {len(urls_data)}")
    print(f"   Previously purged: {purged_count}")
    print(f"   Never purged: {len(urls_data) - purged_count}")

    print(f"\nURLs by repository:")
    for repo, count in sorted(repo_counts.items()):
        print(f"   {repo}: {count} URLs")


def main():
    # Ask if we scan for new URLs or use existing data
    scan_choice = get_user_choice(
        "What would you like to do?",
        [
            "Scan repositories for new URLs (and merge with existing)",
            "Use existing URL list only",
        ],
    )

    existing_urls_data = load_existing_data(JSON_FILENAME)

    if scan_choice == 0:
        # Scan for new URLs
        new_urls_data = scan_for_urls()

        # Merge with existing data, preserving purge history
        for url, new_data in new_urls_data.items():
            if url in existing_urls_data:
                # Keep existing purge history but update repository if needed
                existing_urls_data[url]["repository"] = new_data["repository"]
            else:
                existing_urls_data[url] = new_data

        # Save updated data
        save_data(JSON_FILENAME, existing_urls_data)
        print(f"Updated URL database saved to {JSON_FILENAME}")

    # Display current stats
    display_url_stats(existing_urls_data)

    if not existing_urls_data:
        print("No URLs found in database. Please scan repositories first.")
        return

    # Ask user what they want to purge
    repo_options = [
        "All repositories",
        "heatlabs.github.io",
        "Database-Files",
        "HEAT-Labs-Configs",
        "Don't purge anything",
    ]
    purge_choice = get_user_choice("What would you like to purge?", repo_options)

    if purge_choice == 4:  # Don't purge anything
        print("No purging performed. Exiting.")
        return

    # Filter URLs based on choice
    repo_map = ["all", "heatlabs.github.io", "Database-Files", "HEAT-Labs-Configs"]
    selected_repo = repo_map[purge_choice]

    urls_to_purge = filter_urls_by_repo(existing_urls_data, selected_repo)

    if not urls_to_purge:
        print(f"No URLs found for {repo_options[purge_choice]}")
        return

    print(
        f"\nSelected {len(urls_to_purge)} URLs from {repo_options[purge_choice]} for purging"
    )

    # Confirm purge operation
    confirm = (
        input(f"\nAre you sure you want to purge {len(urls_to_purge)} URLs? (y/N): ")
        .lower()
        .strip()
    )
    if confirm != "y":
        print("Purge cancelled.")
        return

    # Perform purging
    urls_list = list(urls_to_purge.keys())
    successfully_purged = []

    print(f"\nPurging {len(urls_list)} URLs one by one...")

    successfully_purged = purge_urls(urls_list)

    # Update purge timestamps for successfully purged URLs
    if successfully_purged:
        update_purge_timestamp(existing_urls_data, successfully_purged)
        save_data(JSON_FILENAME, existing_urls_data)
        print(f"\nSuccessfully purged {len(successfully_purged)} URLs")
        print(f"Updated purge timestamps saved to {JSON_FILENAME}")
    else:
        print("\nNo URLs were successfully purged")

    print(f"\nFinal statistics:")
    print(f"   Total URLs in database: {len(existing_urls_data)}")
    print(f"   URLs purged this session: {len(successfully_purged)}")


if __name__ == "__main__":
    main()
