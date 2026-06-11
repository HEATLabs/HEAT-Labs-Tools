import yt_dlp
import json
import os
import re
import signal
import sys
import time
from datetime import datetime

SEARCH_QUERIES = [
    "World of Tanks HEAT",
    "World of Tanks: HEAT",
    "WOT HEAT",
    "WoT: HEAT",
]
MAX_RESULTS = 10000
JSON_FILE = "../../HEAT-Labs-Configs/videos.json"

# Rate limiting configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 30
MAX_RETRY_DELAY = 300
RATE_LIMIT_SLEEP = 60


class SilentLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        # Capture rate limit warnings
        if "rate limit" in str(msg).lower() or "too many requests" in str(msg).lower():
            print(f"Rate limit warning: {msg}")
        pass

    def error(self, msg):
        if "rate limit" in str(msg).lower() or "too many requests" in str(msg).lower():
            print(f"Rate limit error: {msg}")
        pass


def clean_text(text):
    if not text:
        return ""

    # Replace newlines and carriage returns with spaces
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

    # Remove multiple spaces
    text = re.sub(r" +", " ", text)

    # Remove emojis and other Unicode symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)

    # Remove any remaining non-printable characters
    text = "".join(char for char in text if char.isprintable() or char.isspace())

    # Trim leading/trailing spaces
    text = text.strip()

    return text


def save_videos(videos_list):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(videos_list, f, indent=4, ensure_ascii=False)


def save_progress_state(query_idx, entry_idx, processed_ids):
    state = {
        "current_query_index": query_idx,
        "current_entry_index": entry_idx,
        "processed_video_ids": list(processed_ids),
        "last_updated": datetime.now().isoformat()
    }
    state_file = JSON_FILE.replace(".json", "_progress.json")
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"Saved state to {state_file}")


def load_progress_state():
    state_file = JSON_FILE.replace(".json", "_progress.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            print(f"Found saved state from {state.get('last_updated', 'unknown')}")
            return state
        except Exception as e:
            print(f"Error loading state: {e}")
    return None


def clear_progress_state():
    state_file = JSON_FILE.replace(".json", "_progress.json")
    if os.path.exists(state_file):
        os.remove(state_file)
        print("Cleared saved state")


def rate_limited_request(func, *args, **kwargs):
    retry_delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()

            # Check if this is a rate limit error
            if any(phrase in error_msg for phrase in ["rate limit", "too many requests", "429", "quota"]):
                if attempt < MAX_RETRIES - 1:
                    print(
                        f"Rate limited! Waiting {retry_delay} seconds before retry {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                else:
                    print(f"Max retries reached for rate limiting. Giving up.")
                    raise
            else:
                # Non-rate-limit error, just raise it
                raise


def extract_with_retry(ydl, url, is_search=False):
    for attempt in range(MAX_RETRIES):
        try:
            if is_search:
                if attempt > 0:
                    time.sleep(INITIAL_RETRY_DELAY * attempt)
                return ydl.extract_info(url, download=False)
            else:
                return rate_limited_request(ydl.extract_info, url, download=False)
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "too many requests" in error_msg:
                wait_time = min(INITIAL_RETRY_DELAY * (attempt + 1), RATE_LIMIT_SLEEP * 2)
                print(f"Pausing for {wait_time} seconds...")
                time.sleep(wait_time)
                if attempt == MAX_RETRIES - 1:
                    raise
            else:
                raise


def signal_handler(sig, frame):
    print("\n\nInterrupted by user. Saving current data...")
    save_videos(videos)
    print(f"Saved {len(videos)} videos to {JSON_FILE}")
    sys.exit(0)


# Load existing videos
videos = []
existing_video_ids = set()

if os.path.exists(JSON_FILE):
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            videos = json.load(f)
        print(f"Loaded {len(videos)} existing videos")

        # Track existing YouTube IDs
        for video in videos:
            url = video.get("url", "")
            if "watch?v=" in url:
                existing_video_ids.add(url.split("watch?v=")[-1].split("&")[0])
    except Exception as e:
        print(f"Error loading existing file: {e}")
        videos = []
        existing_video_ids = set()

# Load progress state
progress_state = load_progress_state()
resume_query_idx = 0
resume_entry_idx = 0

if progress_state:
    resume_query_idx = progress_state.get("current_query_index", 0)
    resume_entry_idx = progress_state.get("current_entry_index", 0)
    existing_video_ids.update(progress_state.get("processed_video_ids", []))
    print(f"Resuming from query {resume_query_idx}, entry {resume_entry_idx}")

signal.signal(signal.SIGINT, signal_handler)

# Config yt-dlp
ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "logger": SilentLogger(),
    "extract_flat": "in_playlist",
    "sleep_interval": 5,
    "max_sleep_interval": 30,
    "sleep_interval_requests": 1,
}

total_added = 0

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for query_idx, SEARCH_QUERY in enumerate(SEARCH_QUERIES):
        # Skip queries we've already processed
        if query_idx < resume_query_idx:
            print(f"\nAlready processed: {SEARCH_QUERY}")
            continue

        print(f"\nSearching for: {SEARCH_QUERY}")
        print(f"(Max results: {MAX_RESULTS})")

        try:
            # Add delay between searches to avoid rate limiting
            if query_idx > 0:
                print(f"Pausing 10 seconds before next search...")
                time.sleep(10)

            search_results = extract_with_retry(
                ydl,
                f"ytsearch{MAX_RESULTS}:{SEARCH_QUERY}",
                is_search=True
            )
        except Exception as e:
            print(f"Search failed for '{SEARCH_QUERY}': {e}")
            print(f"Pausing for {RATE_LIMIT_SLEEP} seconds before continuing...")
            time.sleep(RATE_LIMIT_SLEEP)
            continue

        next_id = len(videos) + 1
        added_count = 0

        entries = search_results.get("entries", [])
        print(f"Found {len(entries)} results")

        # Resume from last entry if needed
        start_entry = resume_entry_idx if query_idx == resume_query_idx else 0

        for entry_idx, entry in enumerate(entries):
            # Skip entries we've already processed
            if entry_idx < start_entry:
                continue

            video_id = entry.get("id")

            if not video_id:
                continue

            # Skip duplicates
            if video_id in existing_video_ids:
                continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            try:
                full_info = extract_with_retry(ydl, video_url)

                upload_date = ""

                if full_info.get("upload_date"):
                    raw = full_info["upload_date"]
                    upload_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

                # Get raw title and description
                raw_title = full_info.get("title", "")
                raw_description = full_info.get("description", "Description Coming Soon")

                # Clean the text
                cleaned_title = clean_text(raw_title)
                cleaned_description = clean_text(raw_description)

                # Fallback if cleaning removed everything
                if not cleaned_title:
                    cleaned_title = "Untitled Video"

                if not cleaned_description:
                    cleaned_description = "No description available"

                new_video = {
                    "id": str(next_id),
                    "title": cleaned_title,
                    "description": cleaned_description,
                    "thumbnail": full_info.get(
                        "thumbnail",
                        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    ),
                    "url": video_url,
                    "creator": clean_text(
                        full_info.get("uploader", full_info.get("channel", ""))
                    ),
                    "date": upload_date,
                    "type": "Gameplay",
                }

                videos.append(new_video)
                existing_video_ids.add(video_id)

                print(f"[{next_id}] Added: {cleaned_title[:50]}...")

                # SAVE AFTER EVERY VIDEO
                save_videos(videos)

                # Save progress state every 10 videos
                if len(videos) % 10 == 0:
                    save_progress_state(query_idx, entry_idx + 1, existing_video_ids)

                next_id += 1
                added_count += 1
                total_added += 1

            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                    print(f"\nRATE LIMITED at video {video_id}")
                    print(f"Pausing for {RATE_LIMIT_SLEEP} seconds...")
                    time.sleep(RATE_LIMIT_SLEEP)

                    try:
                        print(f"Attempting {video_url} again...")
                        time.sleep(5)
                        full_info = extract_with_retry(ydl, video_url)
                    except Exception as retry_error:
                        print(f"Failed again: {retry_error}")
                        continue
                else:
                    print(f"Failed: {video_url}")
                    print(f"Error: {error_msg[:100]}")

                # Save progress on error
                save_progress_state(query_idx, entry_idx, existing_video_ids)
                continue

        print(f"\n[Added {added_count} new videos from '{SEARCH_QUERY}'")
        print(f"Total so far: {len(videos)}")

        # Clear resume index for this query since we completed it
        if query_idx == resume_query_idx:
            resume_entry_idx = 0

# Final save
save_videos(videos)
clear_progress_state()

print(f"\nCOMPLETE!")
print(f"Added {total_added} new videos")
print(f"Total videos: {len(videos)}")
print(f"Output: {JSON_FILE}")