import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path
from PIL import Image
from io import BytesIO
import hashlib

# Constants
ARTICLES_ENDPOINT = "https://cdn.wotheat.com/articles/homepage/articles.json"
LOCALES_ENDPOINT = "https://cdn.wotheat.com/articles/homepage/locales/en.json"
NEWS_JSON_PATH = "../../HEAT-Labs-Configs/news.json"
GUIDES_JSON_PATH = "../../HEAT-Labs-Configs/guides.json"
IMAGES_DIR = "../../HEAT-Labs-Images-News/news-announcement"
GUIDES_IMAGES_DIR = "../../HEAT-Labs-Images-Guides/guides/official"
IMAGE_BASE_URL = "https://cdn12.heatlabs.net/news-announcement"
GUIDES_IMAGE_BASE_URL = "https://cdn11.heatlabs.net/guides/official"


# Fetch JSON data from a URL.
def fetch_json(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


# Convert text to a URL-friendly slug.
def slugify(text):
    # Remove special characters and convert to lowercase
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
    # Replace spaces with hyphens
    text = re.sub(r"[\s]+", "-", text)
    # Remove multiple hyphens
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# Download an image from URL and convert to WebP.
def download_and_convert_image(url, output_path):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Open image with PIL
        img = Image.open(BytesIO(response.content))

        # Convert to RGB if necessary (for WebP compatibility)
        if img.mode in ("RGBA", "LA", "P"):
            # Create a white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Save as WebP with quality 85
        img.save(output_path, "WEBP", quality=85, optimize=True)
        print(f"Saved: {output_path}")
        return True
    except Exception as e:
        print(f"Error processing image: {e}")
        return False


# Determine the image filename.
def get_image_filename(article_id, thumbnail_url, existing_filename=None):
    if existing_filename:
        # Remove extension if present
        base_name = os.path.splitext(existing_filename)[0]
        return f"{base_name}.webp"

    # Generate from article ID
    return f"{article_id}.webp"


# Load existing JSON file
def load_existing_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("posts", [])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {file_path}, starting fresh.")
    return []


# Save posts to JSON file.
def save_json(file_path, posts):
    """Save posts to a JSON file."""
    data = {"posts": posts}
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(posts)} articles to {file_path}")


# Get the full URL for an article
def get_article_url(article_id):
    return f"https://cdn.wotheat.com/articles/{article_id}/index.html"


# Extract article ID from URL
def extract_article_id_from_url(url):
    """Extract the article ID/folder name from a URL."""
    # Pattern to match: https://cdn.wotheat.com/articles/ARTICLE_ID/index.html
    match = re.search(r"articles/([^/]+)/index\.html$", url)
    if match:
        return match.group(1)
    return None


def main():
    print("Starting news update process...")

    # Create images directories if they don't exist
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    Path(GUIDES_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

    # Fetch data from both endpoints
    print("Fetching articles data...")
    articles_data = fetch_json(ARTICLES_ENDPOINT)
    if not articles_data:
        print("Failed to fetch articles data. Aborting.")
        return

    print("Fetching locales data...")
    locales_data = fetch_json(LOCALES_ENDPOINT)
    if not locales_data:
        print("Failed to fetch locales data. Aborting.")
        return

    # Load existing news and guides
    existing_news_posts = load_existing_json(NEWS_JSON_PATH)
    existing_guides_posts = load_existing_json(GUIDES_JSON_PATH)
    print(f"Found {len(existing_news_posts)} existing news articles")
    print(f"Found {len(existing_guides_posts)} existing guide articles")

    # Create mappings by slug (URL) for guides
    # This is more reliable since the JSON stores the full URL as "slug"
    existing_guides_by_slug = {}
    for post in existing_guides_posts:
        slug = post.get("slug", "")
        if slug:
            existing_guides_by_slug[slug] = post

    # Also create mapping by article ID for reference
    existing_guides_by_id = {}
    for post in existing_guides_posts:
        slug = post.get("slug", "")
        article_id = extract_article_id_from_url(slug)
        if article_id:
            existing_guides_by_id[article_id] = post

    # Track which official guides we've processed
    official_guide_slugs = set()

    # Process each article from the CDN
    updated_news_posts = []
    official_guides_posts = []

    for article in articles_data.get("articles", []):
        article_id = article.get("id", "")
        if not article_id:
            print(f"Skipping article without ID: {article}")
            continue

        # Get localized data
        i18n = article.get("i18n", {})
        title_key = i18n.get("title", "")
        excerpt_key = i18n.get("excerpt", "")
        date_key = i18n.get("date", "")

        title = locales_data.get(title_key, title_key)
        description = locales_data.get(excerpt_key, excerpt_key)
        full_date = locales_data.get(date_key, date_key)

        # Determine category
        category = article.get("category", "community")

        # Get image information
        thumbnail_url = article.get("thumbnail", "")

        # Get the full URL for this article
        article_url = get_article_url(article_id)

        # Check if we already have this guide (by URL)
        existing_post = None
        existing_image = None
        existing_sections = None

        if category == "guides":
            # Try to find by full URL first
            existing_post = existing_guides_by_slug.get(article_url)
            # If not found, try by article ID
            if not existing_post:
                existing_post = existing_guides_by_id.get(article_id)

        if existing_post:
            # Extract existing image filename
            existing_image_url = existing_post.get("image", "")
            if existing_image_url:
                match = re.search(r"/([^/]+\.(?:webp|jpg|jpeg|png))$", existing_image_url)
                if match:
                    existing_image = match.group(1)

            # Get existing sections
            if category == "guides" and "sections" in existing_post:
                existing_sections = existing_post.get("sections")
                print(f"Found existing sections for '{title}': {existing_sections}")

        # Determine image filename
        image_filename = get_image_filename(article_id, thumbnail_url, existing_image)

        if category == "guides":
            image_url = f"{GUIDES_IMAGE_BASE_URL}/{image_filename}"
            image_path = os.path.join(GUIDES_IMAGES_DIR, image_filename)
        else:
            image_url = f"{IMAGE_BASE_URL}/{image_filename}"
            image_path = os.path.join(IMAGES_DIR, image_filename)

        # Download and convert image if it doesn't exist
        if not os.path.exists(image_path) and thumbnail_url:
            print(f"Downloading image for: {article_id}")
            success = download_and_convert_image(thumbnail_url, image_path)
            if not success and existing_post:
                image_url = existing_post.get("image", image_url)
        elif os.path.exists(image_path):
            print(f"Image exists for: {article_id}")

        if category == "guides":
            # Determine sections value - preserve existing if available, otherwise PLACEHOLDER
            sections_value = existing_sections if existing_sections else "PLACEHOLDER"

            # Build the official guide post entry
            post = {
                "title": title,
                "description": description,
                "image": image_url,
                "slug": article_url,
                "type": "official-guide",
                "type_name": "Official Guide",
                "sections": sections_value,
                "date": datetime.strptime(article.get("date", ""), "%Y-%m-%d").strftime("%m-%d-%Y") if article.get(
                    "date") else "",
                "raw_date": full_date,
                "author": "HEAT Team"
            }

            official_guides_posts.append(post)
            official_guide_slugs.add(article_url)

            if sections_value == "PLACEHOLDER":
                print(f"⚠️  New official guide (sections need manual setup): {title}")
            else:
                print(f"✓ Preserved sections for official guide: {title} -> {sections_value}")
        else:
            # Build the news post entry
            post = {
                "title": title,
                "description": description,
                "image": image_url,
                "url": article_url,
                "category": category,
                "raw_date": article.get("date", ""),
                "full_date": full_date,
            }

            updated_news_posts.append(post)
            print(f"Processed news: {title}")

    # Merge existing guides with official guides
    merged_guides_posts = []

    for guide in existing_guides_posts:
        guide_slug = guide.get("slug", "")
        if guide_slug not in official_guide_slugs:
            # This is a player-made guide, keep it
            merged_guides_posts.append(guide)
        else:
            print(f"Removed old version of official guide: {guide.get('title', 'Unknown')}")

    # Add the new official guides
    merged_guides_posts.extend(official_guides_posts)

    # Sort merged guides by date (newest first)
    merged_guides_posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Sort news posts by date (newest first)
    updated_news_posts.sort(key=lambda x: x.get("raw_date", ""), reverse=True)

    # Save updated posts
    save_json(NEWS_JSON_PATH, updated_news_posts)
    save_json(GUIDES_JSON_PATH, merged_guides_posts)

    print("\n" + "=" * 50)
    print("UPDATE COMPLETE!")
    print("=" * 50)
    print(f"Total news articles: {len(updated_news_posts)}")
    print(f"Total guide articles: {len(merged_guides_posts)}")
    print(f"  - Official guides: {len(official_guides_posts)}")
    print(f"  - Player-made guides: {len(merged_guides_posts) - len(official_guides_posts)}")

    # List guides that still have PLACEHOLDER sections
    placeholder_guides = [g for g in official_guides_posts if g.get("sections") == "PLACEHOLDER"]
    if placeholder_guides:
        print("\n⚠️  The following official guides need their 'sections' manually set:")
        for guide in placeholder_guides:
            print(f"  - {guide['title']} ({guide['slug']})")


if __name__ == "__main__":
    main()