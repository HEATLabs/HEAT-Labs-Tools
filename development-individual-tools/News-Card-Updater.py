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
IMAGES_DIR = "../../HEAT-Labs-Images-News/news-announcement"
IMAGE_BASE_URL = "https://cdn12.heatlabs.net/news-announcement"

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


# Load existing news.json
def load_existing_news():
    if os.path.exists(NEWS_JSON_PATH):
        try:
            with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("posts", [])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {NEWS_JSON_PATH}, starting fresh.")
    return []


# Save posts to news.json.
def save_news(posts):
    """Save posts to news.json."""
    data = {"posts": posts}
    with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(posts)} articles to {NEWS_JSON_PATH}")


def main():
    print("Starting news update process...")

    # Create images directory if it doesn't exist
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)

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

    # Load existing news
    existing_posts = load_existing_news()
    print(f"Found {len(existing_posts)} existing articles")

    # Create a mapping of existing posts by article ID for reference
    existing_map = {post.get("id", ""): post for post in existing_posts}

    # Create a mapping for image filenames
    image_name_map = {}

    # Process each article
    updated_posts = []

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

        # Check if we already have this article and its image
        existing_post = existing_map.get(article_id)
        existing_image = None

        if existing_post and "image" in existing_post:
            # Extract filename from existing image URL
            existing_image_url = existing_post.get("image", "")
            if existing_image_url:
                # Extract filename from URL
                match = re.search(
                    r"/([^/]+\.(?:webp|jpg|jpeg|png))$", existing_image_url
                )
                if match:
                    existing_image = match.group(1)

        # Determine image filename
        image_filename = get_image_filename(article_id, thumbnail_url, existing_image)

        # Full image URL
        image_url = f"{IMAGE_BASE_URL}/{image_filename}"
        image_path = os.path.join(IMAGES_DIR, image_filename)

        # Download and convert image if it doesn't exist
        if not os.path.exists(image_path) and thumbnail_url:
            print(f"Downloading image for: {article_id}")
            success = download_and_convert_image(thumbnail_url, image_path)
            if not success and existing_image:
                # If download fails but we had an existing image, keep using it
                image_url = existing_post.get("image", image_url)
        elif os.path.exists(image_path):
            print(f"Image exists for: {article_id}")

        # Build the post entry
        post = {
            "title": title,
            "description": description,
            "image": image_url,
            "url": f"https://cdn.wotheat.com/articles/{article_id}/index.html",
            "category": category,
            "raw_date": article.get("date", ""),
            "full_date": full_date,
        }

        updated_posts.append(post)
        print(f"Processed: {title}")

    # Sort posts by date (newest first)
    updated_posts.sort(key=lambda x: x.get("raw_date", ""), reverse=True)

    # Save updated posts
    save_news(updated_posts)

    print("\nUpdate complete!")
    print(f"Total articles: {len(updated_posts)}")


if __name__ == "__main__":
    main()
