import os
import re


def find_html_files(root_dir):
    html_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.html'):
                html_files.append(os.path.join(dirpath, filename))
    return html_files


def remove_duplicate_links_and_scripts(content):
    css_pattern = r'<link[^>]*?rel="stylesheet"[^>]*?>'
    script_pattern = r'<script[^>]*?src="[^"]*"[^>]*?></script>'

    css_matches = []
    for match in re.finditer(css_pattern, content, re.IGNORECASE | re.DOTALL):
        href_match = re.search(r'href="([^"]*)"', match.group())
        if href_match:
            css_matches.append((match.start(), match.end(), href_match.group(1)))

    script_matches = []
    for match in re.finditer(script_pattern, content, re.IGNORECASE | re.DOTALL):
        src_match = re.search(r'src="([^"]*)"', match.group())
        if src_match:
            script_matches.append((match.start(), match.end(), src_match.group(1)))

    unique_css = {}
    css_to_remove = []
    unique_scripts = {}
    scripts_to_remove = []

    for start, end, href in css_matches:
        if href in unique_css:
            css_to_remove.append((start, end))
        else:
            unique_css[href] = (start, end)

    for start, end, src in script_matches:
        if src in unique_scripts:
            scripts_to_remove.append((start, end))
        else:
            unique_scripts[src] = (start, end)

    all_to_remove = sorted(css_to_remove + scripts_to_remove, key=lambda x: x[0], reverse=True)

    for start, end in all_to_remove:
        before = content[:start]
        after = content[end:]

        before_end_newline = before.endswith('\n') if before else False
        after_start_newline = after.startswith('\n') if after else False

        if before_end_newline and after_start_newline:
            after = after[1:]

        content = before + after

    return content


def process_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    original_content = content
    content = remove_duplicate_links_and_scripts(content)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True

    return False


def main():
    root_dir = input("Enter the path to folder: ").strip()

    if not os.path.exists(root_dir):
        print(f"Error: Directory '{root_dir}' does not exist.")
        return

    print(f"Scanning for HTML files in: {root_dir}")

    html_files = find_html_files(root_dir)
    print(f"Found {len(html_files)} HTML file(s)")

    modified_files = []

    for file_path in html_files:
        print(f"Processing: {file_path}")
        try:
            if process_html_file(file_path):
                modified_files.append(file_path)
                print(f"Fixed duplicates in: {os.path.basename(file_path)}")
            else:
                print(f"No duplicates found in: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print(f"Summary:")
    print(f"Total HTML files scanned: {len(html_files)}")
    print(f"Files modified: {len(modified_files)}")

    if modified_files:
        print("\nModified files:")
        for file in modified_files:
            print(f"  - {file}")


if __name__ == "__main__":
    main()