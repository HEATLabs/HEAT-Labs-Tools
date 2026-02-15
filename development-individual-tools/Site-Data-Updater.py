import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


def update_humans_txt_files():
    # humans.txt files
    humans_txt_paths = [
        Path("../../HEAT-Labs-Changelog/site-data/humans.txt"),
        Path("../../HEAT-Labs-Configs/site-data/humans.txt"),
        Path("../../HEAT-Labs-Database/site-data/humans.txt"),
        Path("../../HEAT-Labs-Discord/site-data/humans.txt"),
        Path("../../HEAT-Labs-Discord-Bot/site-data/humans.txt"),
        Path("../../HEAT-Labs-Mobile-App/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Blogs/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Features/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Gallery/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Guides/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Maps/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-News/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Tanks/site-data/humans.txt"),
        Path("../../HEAT-Labs-Images-Tournaments/site-data/humans.txt"),
        Path("../../HEAT-Labs-Games/site-data/humans.txt"),
        Path("../../HEAT-Labs-Tank-Game/site-data/humans.txt"),
        Path("../../HEAT-Labs-Steam-Assets/site-data/humans.txt"),
        Path("../../HEAT-Labs-Models/site-data/humans.txt"),
        Path("../../HEAT-Labs-Search/site-data/humans.txt"),
        Path("../../HEAT-Labs-Mods/site-data/humans.txt"),
        Path("../../HEAT-Labs-Archives/site-data/humans.txt"),
        Path("../../HEAT-Labs-Socials/site-data/humans.txt"),
        Path("../../HEAT-Labs-Sounds/site-data/humans.txt"),
        Path("../../HEAT-Labs-Static/site-data/humans.txt"),
        Path("../../HEAT-Labs-Statistics/site-data/humans.txt"),
        Path("../../HEAT-Labs-Status/site-data/humans.txt"),
        Path("../../HEAT-Labs-Videos/site-data/humans.txt"),
        Path("../../HEAT-Labs-Views-API/site-data/humans.txt"),
        Path("../../HEAT-Labs-Website/site-data/humans.txt"),
        Path("../../HEAT-Labs-Website-Development/site-data/humans.txt"),
    ]

    # Get current date in the required format
    current_date = datetime.now().strftime("%Y/%m/%d")

    updated_count = 0

    for humans_txt_path in humans_txt_paths:
        # Check if the file exists
        if not humans_txt_path.exists():
            print(f"Warning: {humans_txt_path} does not exist, skipping...")
            continue

        # Read the file content
        with open(humans_txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace the Last update line
        old_content = content
        content = content.replace(
            "Last update: 2025/10/06", f"Last update: {current_date}"
        )

        # Try to find and replace any date in that format
        if content == old_content:
            # Use a more flexible pattern to find any date in "Last update" field
            import re

            pattern = r"Last update: \d{4}/\d{2}/\d{2}"
            content = re.sub(pattern, f"Last update: {current_date}", content)

        # Write the updated content back to the file
        with open(humans_txt_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Updated: {humans_txt_path}")
        updated_count += 1


def generate_sitemap():
    # Define paths
    base_dir = Path("../../HEAT-Labs-Website")
    sitemap_path = Path("../../HEAT-Labs-Website/site-data/sitemap.xml")

    # Define files to exclude from sitemap
    not_include = [
        "index.html",
        "placeholder_post.html",
        "maintenance.html",
        "game-data.html",
        "404.html",
        "tournament-maintenance.html",
        "test-model-viewer.html",
        "placeholder-tank.html",
        "placeholder-post.html",
        "guide-category-placeholder.html",
        "all-guides-placeholder.html",
        "placeholder-news.html",
        "placeholder-map.html",
        "placeholder-general-guide.html",
        "placeholder-map-guide.html",
        "placeholder-tank-guide.html",
        "maxwell.html",
        "bored-developers.html",
        "devsonly.html",
        "hungry-devs.html",
        "placeholder-bug-hunt.html",
        "feature-showcase-template.html",
        "meet-the-team-template.html",
        "placeholder-blog-post.html",
        "placeholder-announcement.html",
        "placeholder-agent.html",
    ]

    # Check if base directory exists
    if not base_dir.exists():
        print(f"Error: Directory {base_dir} does not exist!")
        return

    # Get current date in the required format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Create the root element for the sitemap
    urlset = ET.Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Find all HTML files in the base directory and subdirectories
    html_files = list(base_dir.rglob("*.html"))

    # Create a list to store URL data for sorting
    url_data = []

    # Process home page separately
    home_url_data = {
        "loc": "https://heatlabs.net",
        "depth": -1,
        "priority": "1.0",
        "lastmod": current_date,
        "changefreq": "weekly",
    }
    url_data.append(home_url_data)

    for html_file in html_files:
        # Skip the sitemap file itself
        if "sitemap.xml" in str(html_file):
            continue

        # Skip files in the not_include list
        if html_file.name in not_include:
            print(f"Skipping excluded file: {html_file.name}")
            continue

        # Calculate the relative path from base directory
        relative_path = html_file.relative_to(base_dir)

        # Calculate depth for priority assignment and sorting
        depth = (
            len(relative_path.parts) - 1
        )  # -1 because the file itself counts as a part

        # Assign priority based on depth
        if depth == 0:
            priority = "0.8"
        elif depth == 1:
            priority = "0.6"
        elif depth == 2:
            priority = "0.4"
        else:
            priority = "0.2"

        # Build the URL
        if depth == 0:
            # File is in root directory
            url_loc = f"https://heatlabs.net/{html_file.stem}"
        else:
            # File is in a subdirectory
            path_parts = list(relative_path.parts)
            # Remove .html from the filename
            filename_without_ext = Path(path_parts[-1]).stem
            path_parts[-1] = filename_without_ext
            url_path = "/".join(path_parts)
            url_loc = f"https://heatlabs.net/{url_path}"

        # Store URL data for sorting
        url_data.append(
            {
                "loc": url_loc,
                "depth": depth,
                "priority": priority,
                "lastmod": current_date,
                "changefreq": "weekly",
                "sort_key": str(relative_path).lower(),
            }
        )

    # Sort URLs first by depth then alphabetically by path
    url_data.sort(key=lambda x: (x["depth"], x["sort_key"] if "sort_key" in x else ""))

    # Add sorted URLs to the XML
    for data in url_data:
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = data["loc"]
        ET.SubElement(url_elem, "lastmod").text = data["lastmod"]
        ET.SubElement(url_elem, "changefreq").text = data["changefreq"]
        ET.SubElement(url_elem, "priority").text = data["priority"]

    # Create the site-data directory if it doesnt exist
    sitemap_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the sitemap to file
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset\n\txmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        # Format each URL entry properly
        for url_elem in urlset:
            f.write("\t<url>\n")
            for child in url_elem:
                tag = child.tag
                text = child.text
                if tag == "loc":
                    f.write(f"\t\t<loc>{text}</loc>\n")
                elif tag == "lastmod":
                    f.write(f"\t\t<lastmod>{text}</lastmod>\n")
                elif tag == "changefreq":
                    f.write(f"\t\t<changefreq>{text}</changefreq>\n")
                elif tag == "priority":
                    f.write(f"\t\t<priority>{text}</priority>\n")
            f.write("\t</url>\n")

        f.write("</urlset>")

    print(f"Found {len(html_files)} HTML files")
    excluded_count = len(not_include)
    included_count = len(url_data) - 1  # Subtract 1 for the home page
    print(f"Excluded {excluded_count} files from sitemap")
    print(f"Included {included_count} files in sitemap")
    print("URLs sorted by depth and alphabetically in sitemap.xml")
    print(f"Sitemap successfully updated at {sitemap_path}")


if __name__ == "__main__":
    generate_sitemap()
    update_humans_txt_files()
