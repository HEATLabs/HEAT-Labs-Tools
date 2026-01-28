import os
import json
from typing import Dict, List, Union, Any
import sys


def validate_generic_json(file_path: str) -> bool:
    """Validate that a file is properly formatted JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False


def validate_tank_agents(file_path: str) -> bool:
    """Validate agents.json structure for tanks."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print(f"agents.json should be a dictionary in {file_path}")
            return False

        if "agents" not in data:
            print(f"Missing 'agents' key in {file_path}")
            return False

        if not isinstance(data["agents"], list):
            print(f"'agents' should be a list in {file_path}")
            return False

        for agent in data["agents"]:
            required_keys = [
                "name",
                "image",
                "specialty",
                "description",
                "story",
                "compatibleTanks",
            ]
            for key in required_keys:
                if key not in agent:
                    print(f"Missing key '{key}' in agent in {file_path}")
                    return False

            if not isinstance(agent["compatibleTanks"], list):
                print(f"'compatibleTanks' should be a list in {file_path}")
                return False

            for tank in agent["compatibleTanks"]:
                if "name" not in tank or "image" not in tank:
                    print(f"Missing name/image in compatible tank in {file_path}")
                    return False

        return True

    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return False


def validate_stats_file(file_path: str) -> bool:
    """Validate files with stats structure (equipments, perks, stock, upgrades)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print(f"File should be a dictionary in {file_path}")
            return False

        # Check for at least one valid section
        valid_sections = ["FIREPOWER", "MOBILITY", "SURVIVABILITY", "RECON", "UTILITY"]
        found_section = False

        for key in data:
            if isinstance(data[key], dict):
                for section in valid_sections:
                    if section in data[key]:
                        found_section = True
                        break

        if not found_section:
            print(f"No valid sections found in {file_path}")
            return False

        return True

    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return False


def validate_tank_details(file_path: str) -> bool:
    """Validate details.json structure for tanks."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"details.json should be a list in {file_path}")
            return False

        return True

    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return False


def validate_tournament_file(file_path: str) -> bool:
    """Validate tournament JSON files."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print(f"Tournament file should be a dictionary in {file_path}")
            return False

        required_keys = ["total_teams", "top_3_teams"]
        for key in required_keys:
            if key not in data:
                print(f"Missing key '{key}' in tournament file {file_path}")
                return False

        if not isinstance(data["top_3_teams"], list) or len(data["top_3_teams"]) != 3:
            print(f"'top_3_teams' should be a list of 3 teams in {file_path}")
            return False

        for team in data["top_3_teams"]:
            team_required_keys = [
                "team_name",
                "team_logo",
                "team_captain",
                "team_description",
                "team_motto",
                "team_members",
                "team_tanks",
            ]
            for key in team_required_keys:
                if key not in team:
                    print(f"Missing key '{key}' in team in {file_path}")
                    return False

            if not isinstance(team["team_tanks"], list):
                print(f"'team_tanks' should be a list in {file_path}")
                return False

            for tank in team["team_tanks"]:
                if (
                    "player_name" not in tank
                    or "tank_name" not in tank
                    or "tank_image" not in tank
                ):
                    print(f"Missing required tank fields in {file_path}")
                    return False

        return True

    except Exception as e:
        print(f"Error validating tournament file {file_path}: {e}")
        return False


def validate_banner(file_path: str) -> bool:
    """Validate banner.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = [
            "id",
            "active",
            "startDate",
            "endDate",
            "message",
            "ctaText",
            "ctaUrl",
            "backgroundColor",
            "textColor",
            "buttonColor",
        ]

        for key in required_keys:
            if key not in data:
                print(f"Missing key '{key}' in banner.json")
                return False

        if not isinstance(data["active"], bool):
            print("'active' should be a boolean in banner.json")
            return False

        return True

    except Exception as e:
        print(f"Error validating banner.json: {e}")
        return False


def validate_changelog(file_path: str) -> bool:
    """Validate changelog.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "updates" not in data:
            print("Missing 'updates' key in changelog.json")
            return False

        if not isinstance(data["updates"], list):
            print("'updates' should be a list in changelog.json")
            return False

        for update in data["updates"]:
            required_keys = [
                "version",
                "date",
                "author",
                "title",
                "description",
                "added",
                "changed",
                "removed",
            ]
            for key in required_keys:
                if key not in update:
                    print(f"Missing key '{key}' in update in changelog.json")
                    return False

            if (
                not isinstance(update["added"], list)
                or not isinstance(update["changed"], list)
                or not isinstance(update["removed"], list)
            ):
                print("added/changed/removed should be lists in changelog.json")
                return False

        return True

    except Exception as e:
        print(f"Error validating changelog.json: {e}")
        return False


def validate_search_keywords(file_path: str) -> bool:
    """Validate search-keywords.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("search-keywords.json should be a list")
            return False

        for item in data:
            required_keys = ["name", "description", "path", "keywords"]
            for key in required_keys:
                if key not in item:
                    print(f"Missing key '{key}' in search keyword item")
                    return False

            if not isinstance(item["keywords"], list):
                print("'keywords' should be a list in search-keywords.json")
                return False

        return True

    except Exception as e:
        print(f"Error validating search-keywords.json: {e}")
        return False


def validate_tankopedia(file_path: str) -> bool:
    """Validate tankopedia.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = ["category_order", "categories"]
        for key in required_keys:
            if key not in data:
                print(f"Missing key '{key}' in tankopedia.json")
                return False

        if not isinstance(data["category_order"], list):
            print("'category_order' should be a list in tankopedia.json")
            return False

        if not isinstance(data["categories"], list):
            print("'categories' should be a list in tankopedia.json")
            return False

        for category in data["categories"]:
            if (
                "name" not in category
                or "description" not in category
                or "items" not in category
            ):
                print("Missing required keys in category in tankopedia.json")
                return False

            if not isinstance(category["items"], list):
                print("'items' should be a list in tankopedia.json category")
                return False

            for item in category["items"]:
                if (
                    "id" not in item
                    or "image" not in item
                    or "name" not in item
                    or "description" not in item
                ):
                    print("Missing required keys in item in tankopedia.json")
                    return False

        return True

    except Exception as e:
        print(f"Error validating tankopedia.json: {e}")
        return False


def validate_tanks_list(file_path: str) -> bool:
    """Validate tanks.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("tanks.json should be a list")
            return False

        for tank in data:
            required_keys = [
                "id",
                "name",
                "slug",
                "nation",
                "type",
                "class",
                "image",
                "stock",
                "upgrades",
                "equipments",
                "perks",
                "agents",
                "details",
            ]
            for key in required_keys:
                if key not in tank:
                    print(f"Missing key '{key}' in tank in tanks.json")
                    return False

        return True

    except Exception as e:
        print(f"Error validating tanks.json: {e}")
        return False


def validate_tournaments_list(file_path: str) -> bool:
    """Validate tournaments.json structure."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("tournaments.json should be a list")
            return False

        for tournament in data:
            if "tournament-id" not in tournament or "tournament-data" not in tournament:
                print("Missing required keys in tournament in tournaments.json")
                return False

        return True

    except Exception as e:
        print(f"Error validating tournaments.json: {e}")
        return False


def validate_json_files(base_path: str):
    """Main function to validate all JSON files."""
    total_files = 0
    failed_files = 0

    print(f"\nValidating JSON files in {base_path}...")

    # Walk through all directories
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                total_files += 1

                # Determine which validation function to use based on file name and path
                if (
                    "tanks/" in file_path
                    and "../../HEAT-Labs-Database/tanks/" in file_path
                ):
                    tank_folder = os.path.basename(os.path.dirname(file_path))

                    if file == "agents.json":
                        valid = validate_tank_agents(file_path)
                    elif file in [
                        "equipments.json",
                        "perks.json",
                        "stock.json",
                        "upgrades.json",
                    ]:
                        valid = validate_stats_file(file_path)
                    elif file == "details.json":
                        valid = validate_tank_details(file_path)
                    else:
                        valid = validate_generic_json(file_path)

                elif "../../Database-Files/tournaments/" in file_path and file.endswith(
                    ".json"
                ):
                    valid = validate_tournament_file(file_path)

                elif "../../HEAT-Labs-Configs/" in file_path:
                    if file == "banner.json":
                        valid = validate_banner(file_path)
                    elif file == "changelog.json":
                        valid = validate_changelog(file_path)
                    elif file == "search-keywords.json":
                        valid = validate_search_keywords(file_path)
                    elif file == "tankopedia.json":
                        valid = validate_tankopedia(file_path)
                    elif file == "tanks.json":
                        valid = validate_tanks_list(file_path)
                    elif file == "tournaments.json":
                        valid = validate_tournaments_list(file_path)
                    else:
                        valid = validate_generic_json(file_path)

                else:
                    valid = validate_generic_json(file_path)

                if not valid:
                    failed_files += 1

    print(f"\nValidation complete. Checked {total_files} files.")
    if failed_files == 0:
        print("All JSON files are valid!")
    else:
        print(f"Found {failed_files} invalid JSON files.")

    return failed_files == 0


if __name__ == "__main__":
    # Define the base paths to scan
    base_paths = [
        "../../HEAT-Labs-Database/tanks/",
        "../../HEAT-Labs-Database/tournaments/",
        "../../HEAT-Labs-Configs/",
    ]

    all_valid = True

    for path in base_paths:
        if not os.path.exists(path):
            print(f"Error: Path {path} does not exist")
            all_valid = False
            continue

        if not validate_json_files(path):
            all_valid = False

    if not all_valid:
        sys.exit(1)
    else:
        sys.exit(0)
