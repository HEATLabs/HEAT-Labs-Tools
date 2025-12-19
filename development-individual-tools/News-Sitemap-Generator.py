import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re
from html import unescape

# Parse HTML file to extract info
def parse_html_for_news_info(html_file_path):
    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title from <title> tag
        title_match = re.search(
            r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title = unescape(title_match.group(1).strip())
            title = re.sub(r"\s*-\s*HEAT Labs\s*$", "", title, flags=re.IGNORECASE)
        else:
            title = html_file_path.stem.replace("-", " ").title()

        # Extract publication date from the calendar span
        date_pattern = r'<i class="[^"]*fa-calendar-alt[^"]*"[^>]*></i>([^<]+)</span>'
        date_match = re.search(date_pattern, content, re.IGNORECASE | re.DOTALL)

        if date_match:
            date_str = date_match.group(1).strip()
            try:
                date_str = unescape(date_str).strip()
                parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                return {"title": title, "publication_date": parsed_date}
            except ValueError:
                return None
        else:
            alt_date_pattern = r'<span[^>]*>\s*<i[^>]*class="[^"]*fa-calendar-alt[^"]*"[^>]*></i>\s*([^<]+)\s*</span>'
            alt_date_match = re.search(
                alt_date_pattern, content, re.IGNORECASE | re.DOTALL
            )
            if alt_date_match:
                date_str = alt_date_match.group(1).strip()
                try:
                    date_str = unescape(date_str).strip()
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    return {"title": title, "publication_date": parsed_date}
                except ValueError:
                    return None

        return None

    except Exception:
        return None


# Generate sitemap-news.xml
def generate_news_sitemap():
    base_dir = Path("../../HEAT-Labs-Website")
    directories_to_scan = [
        base_dir / "announcements",
        base_dir / "steam-news",
        base_dir / "news",
        base_dir / "blog",
    ]

    output_path = Path("../../HEAT-Labs-Website/site-data/sitemap-news.xml")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    timezone_offset = "+02:00"

    valid_directories = []
    for directory in directories_to_scan:
        if directory.exists():
            valid_directories.append(directory)

    if not valid_directories:
        print("No directories found.")
        return

    html_files = []
    for directory in valid_directories:
        html_files.extend(directory.rglob("*.html"))

    exclude_files = [
        "placeholder-news.html",
        "placeholder-post.html",
        "placeholder-announcement.html",
        "placeholder-blog-post.html",
        "index.html",
        "maintenance.html",
        "404.html",
    ]

    existing_items = []
    if output_path.exists():
        try:
            tree = ET.parse(output_path)
            root = tree.getroot()
            for url_elem in root.findall(".//url"):
                loc_elem = url_elem.find("loc")
                if loc_elem is not None and loc_elem.text:
                    existing_items.append(loc_elem.text)
        except:
            existing_items = []

    existing_count = len(existing_items)

    news_items = []

    for html_file in html_files:
        if html_file.name in exclude_files:
            continue

        if "template" in html_file.parts or "placeholder" in html_file.name.lower():
            continue

        news_info = parse_html_for_news_info(html_file)

        if news_info:
            try:
                relative_to_base = html_file.relative_to(base_dir)
                url_parts = list(relative_to_base.parts)
                filename_without_ext = Path(url_parts[-1]).stem
                url_parts[-1] = filename_without_ext
                url_path = "/".join(url_parts)
                url = f"https://heatlabs.net/{url_path}"

                pub_date_str = (
                    news_info["publication_date"].strftime("%Y-%m-%dT%H:%M:%S")
                    + timezone_offset
                )

                news_items.append(
                    {
                        "url": url,
                        "title": news_info["title"],
                        "publication_date": pub_date_str,
                        "pub_date_obj": news_info["publication_date"],
                    }
                )

            except ValueError:
                continue

    if not news_items:
        print("No news items found.")
        return

    news_items.sort(key=lambda x: x["pub_date_obj"], reverse=True)

    urlset = ET.Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset.set("xmlns:news", "http://www.google.com/schemas/sitemap-news/0.9")

    for item in news_items:
        url_elem = ET.SubElement(urlset, "url")

        loc_elem = ET.SubElement(url_elem, "loc")
        loc_elem.text = item["url"]

        news_elem = ET.SubElement(url_elem, "news:news")

        publication_elem = ET.SubElement(news_elem, "news:publication")
        name_elem = ET.SubElement(publication_elem, "news:name")
        name_elem.text = "HEAT Labs"
        language_elem = ET.SubElement(publication_elem, "news:language")
        language_elem.text = "en"

        pub_date_elem = ET.SubElement(news_elem, "news:publication_date")
        pub_date_elem.text = item["publication_date"]

        title_elem = ET.SubElement(news_elem, "news:title")
        title_elem.text = item["title"]

    try:
        tree = ET.ElementTree(urlset)

        from xml.dom import minidom

        rough_string = ET.tostring(urlset, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8")
        pretty_xml_str = pretty_xml.decode("utf-8")
        pretty_xml_str = "\n".join(
            [line for line in pretty_xml_str.split("\n") if line.strip()]
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(pretty_xml_str)

        new_count = len(news_items)
        print(f"Existing items: {existing_count}")
        print(f"New items added: {new_count}")
        print(f"Total items now: {new_count}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    generate_news_sitemap()
