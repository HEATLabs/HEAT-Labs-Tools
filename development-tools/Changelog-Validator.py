import json
from pathlib import Path
from datetime import datetime


def format_date_long(date_str):
    """Convert date from YYYY-MM-DD to 'DD Month, YYYY'."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d %B, %Y")
    except ValueError:
        return date_str  # Return as-is if format is invalid


def calculate_correct_version_numbers(changelog):
    updates_chronological = changelog["updates"][::-1]  # Oldest to newest
    cumulative_changes = 0
    corrected_updates = []

    # Version transition configuration
    VERSION_TRANSITIONS = [
        {
            "from_version": "0.0.000",
            "major_version": 0
         },
        {
            "from_version": "0.9.000",
            "major_version": 1,
        },
        {
            "from_version": "1.9.000",
            "major_version": 2,
        },
    ]

    # Sort transitions by version for processing
    VERSION_TRANSITIONS.sort(
        key=lambda x: [int(n) for n in x["from_version"].split(".")]
    )

    for idx, update in enumerate(updates_chronological):
        # Count each type of change separately
        additions = len(update.get("added", []))
        changes = len(update.get("changed", []))
        fixes = len(update.get("fixed", []))
        removals = len(update.get("removed", []))

        # Sum all changes for version number calculation
        total_changes = additions + changes + fixes + removals
        cumulative_changes += total_changes

        # Determine major version based on transitions
        current_major_version = 0
        current_middle_version = 0
        current_minor_version = 0

        # Calculate what the version would be without transitions
        temp_middle = (cumulative_changes - 1) // 1000
        temp_minor = (cumulative_changes - 1) % 1000
        temp_version = f"0.{temp_middle}.{temp_minor:03d}"

        # Find the appropriate major version based on transitions
        for transition in reversed(VERSION_TRANSITIONS):
            transition_parts = [int(n) for n in transition["from_version"].split(".")]
            current_parts = [int(n) for n in temp_version.split(".")]

            # Compare versions: major.middle.minor
            if (
                current_parts[0] > transition_parts[0]
                or (
                    current_parts[0] == transition_parts[0]
                    and current_parts[1] > transition_parts[1]
                )
                or (
                    current_parts[0] == transition_parts[0]
                    and current_parts[1] == transition_parts[1]
                    and current_parts[2] >= transition_parts[2]
                )
            ):
                current_major_version = transition["major_version"]
                break

        # Calculate final version numbers
        base_transition = None
        for transition in VERSION_TRANSITIONS:
            if transition["major_version"] == current_major_version:
                base_transition = transition
                break

        if base_transition:
            # Calculate offset from the transition point
            transition_parts = [
                int(n) for n in base_transition["from_version"].split(".")
            ]
            transition_cumulative = (
                (transition_parts[1] * 1000) + transition_parts[2] + 1
            )

            if cumulative_changes >= transition_cumulative:
                offset = cumulative_changes - transition_cumulative
                current_middle_version = offset // 1000
                current_minor_version = offset % 1000
            else:
                # This shouldn't happen with proper configuration, but fallback
                current_middle_version = (cumulative_changes - 1) // 1000
                current_minor_version = (cumulative_changes - 1) % 1000
        else:
            # Fallback if no transition found
            current_middle_version = (cumulative_changes - 1) // 1000
            current_minor_version = (cumulative_changes - 1) % 1000

        correct_version = f"{current_major_version}.{current_middle_version}.{current_minor_version:03d}"

        corrected_update = update.copy()
        corrected_update["version"] = correct_version

        update_number = idx + 1
        pretty_date = format_date_long(update["date"])

        corrected_update["title"] = f"HEAT Labs - Update Number #{update_number}"
        corrected_update["description"] = (
            f"Full patch notes for Update v{correct_version} "
            f"(#{update_number}), detailing all changes made on {pretty_date}."
        )

        corrected_updates.append(corrected_update)

    corrected_updates = corrected_updates[::-1]  # Newest first
    corrected_changelog = changelog.copy()
    corrected_changelog["updates"] = corrected_updates
    return corrected_changelog, VERSION_TRANSITIONS


def verify_and_correct_changelog(file_path):
    with open(file_path, "r") as f:
        changelog = json.load(f)

    corrected_changelog, VERSION_TRANSITIONS = calculate_correct_version_numbers(
        changelog
    )

    version_issues = False
    author_issues = False
    title_issues = False
    description_issues = False

    mismatches = []

    for i, (original, corrected) in enumerate(
        zip(changelog["updates"], corrected_changelog["updates"])
    ):
        update_issues = {}
        update_issues["date"] = original["date"]

        if original["version"] != corrected["version"]:
            version_issues = True
            update_issues["version"] = {
                "current": original["version"],
                "correct": corrected["version"],
            }

        if original.get("author") != "HEAT Labs Team":
            author_issues = True
            update_issues["author"] = {
                "current": original.get("author", "MISSING"),
                "correct": "HEAT Labs Team",
            }

        if original.get("title") != corrected["title"]:
            title_issues = True
            update_issues["title"] = {
                "current": original.get("title", "MISSING"),
                "correct": corrected["title"],
            }

        if original.get("description") != corrected["description"]:
            description_issues = True
            update_issues["description"] = {
                "current": original.get("description", "MISSING"),
                "correct": corrected["description"],
            }

        if len(update_issues) > 1:
            mismatches.append(update_issues)

    if mismatches:
        print("\nISSUES FOUND:")
        for issue in mismatches:
            print(f"\nDate: {issue['date']}")
            for field, diff in issue.items():
                if field == "date":
                    continue
                print(f"  {field.title()} mismatch:")
                print(f"    Current: {diff['current']}")
                print(f"    Correct: {diff['correct']}")
    else:
        print("All updates are properly formatted and correct!")
        return

    response = input(
        "\nDo you want to automatically fix and overwrite the changelog? (y/n): "
    )
    if response.lower() == "y":
        changelog["updates"] = corrected_changelog["updates"]

        for update in changelog["updates"]:
            update["author"] = "HEAT Labs Team"

        with open(file_path, "w") as f:
            json.dump(changelog, f, indent=2)

        print(f"✅ {file_path} has been updated and corrected.")
    else:
        print("❌ No changes were made.")


if __name__ == "__main__":
    file_path = Path("../../HEAT-Labs-Configs/changelog.json")
    verify_and_correct_changelog(file_path)
