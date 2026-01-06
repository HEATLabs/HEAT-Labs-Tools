import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime


# Load .env file
def load_config():
    env_path = Path(__file__).parent / "../.env"
    load_dotenv(dotenv_path=env_path)

    steam_key = os.getenv("STEAM_KEY")
    steam_app_id = os.getenv("STEAM_APP_ID")

    if not steam_key:
        raise ValueError("STEAM_KEY not found in .env file")
    if not steam_app_id:
        raise ValueError("STEAM_APP_ID not found in .env file")

    return steam_key, steam_app_id


# Fetch achievements from Steam API
def fetch_steam_achievements(steam_key, steam_app_id):
    url = f"https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
    params = {"key": steam_key, "appid": steam_app_id}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "game" not in data or "availableGameStats" not in data["game"]:
            print(f"No achievements found for app ID: {steam_app_id}")
            return None

        achievements = data["game"]["availableGameStats"].get("achievements", [])
        return achievements

    except requests.exceptions.RequestException as e:
        print(f"Error fetching achievements: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None


# Update achievements JSON file
def update_achievements_file(achievements_data, output_path):
    try:
        # Create structure
        updated_data = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "achievements": achievements_data,
        }

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)

        print(f"Successfully updated {output_path}")
        print(f"Total achievements: {len(achievements_data)}")

    except IOError as e:
        print(f"Error writing to file {output_path}: {e}")
    except Exception as e:
        print(f"Error updating achievements file: {e}")


def main():
    OUTPUT_PATH = (
        Path(__file__).parent / "../../HEAT-Labs-Database/game-data/achievements.json"
    )

    try:
        # Load Steam API key and game ID
        steam_key, steam_app_id = load_config()
        print(f"Using Steam App ID: {steam_app_id}")

        # Fetch achievements from Steam API
        print("Fetching achievements from Steam API...")
        achievements = fetch_steam_achievements(steam_key, steam_app_id)

        if achievements is None:
            print("Failed to fetch achievements")
            return

        # Update achievements file
        update_achievements_file(achievements, OUTPUT_PATH)

    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
