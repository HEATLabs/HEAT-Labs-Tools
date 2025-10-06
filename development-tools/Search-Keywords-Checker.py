import os
import json
from urllib.parse import urlparse


def find_html_files(root_dir):
    html_files = set()
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                # Get relative path from the root directory
                rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                # Normalize path separators to forward slashes
                rel_path = rel_path.replace('\\', '/')
                html_files.add(rel_path)
    return html_files


def load_json_index(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    indexed_paths = set()
    for entry in data:
        # Extract the path part from the URL
        parsed = urlparse(entry['path'])
        path = parsed.path.lstrip('/')
        indexed_paths.add(path)

    return indexed_paths


def find_missing_pages(root_dir, json_file):
    # Find all HTML files in the directory
    html_files = find_html_files(root_dir)

    # Load indexed paths from JSON
    indexed_paths = load_json_index(json_file)

    # Find files not in the index
    missing_files = html_files - indexed_paths

    # Filter out common files that dont need to be indexed
    common_files = {'404.html', 'index.html'}

    # Return sorted list of missing files, excluding common files
    return sorted(missing_files - common_files)


if __name__ == "__main__":
    # Set directory and JSON file paths
    root_directory = '../../heatlabs.github.io'
    json_file_path = '../../HEAT-Labs-Configs/search-keywords.json'

    if not os.path.exists(root_directory):
        print(f"Error: Directory '{root_directory}' not found.")
    elif not os.path.exists(json_file_path):
        print(f"Error: JSON file '{json_file_path}' not found.")
    else:
        missing = find_missing_pages(root_directory, json_file_path)

        if missing:
            print("The following HTML files are not in the search index:")
            for file in missing:
                print(f"- {file}")
        else:
            print("All HTML files are indexed in the search-keywords.json file.")