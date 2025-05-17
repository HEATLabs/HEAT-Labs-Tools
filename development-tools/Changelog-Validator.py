import json
from pathlib import Path


def calculate_correct_version_numbers(changelog):
    # Make a copy of updates in chronological order
    updates_chronological = changelog["updates"][::-1]  # Reverse the list

    cumulative_changes = 0
    corrected_updates = []

    for update in updates_chronological:
        # Calculate changes in this update
        changes = (
            len(update.get("added", []))
            + len(update.get("changed", []))
            + len(update.get("removed", []))
        )

        cumulative_changes += changes

        # Format version number with leading zeros
        correct_version = "0.0.{:04d}".format(cumulative_changes)

        # Create corrected update entry
        corrected_update = update.copy()
        corrected_update["version"] = correct_version
        corrected_updates.append(corrected_update)

    # Reverse back to original order (newest first)
    corrected_updates = corrected_updates[::-1]

    # Create corrected changelog
    corrected_changelog = changelog.copy()
    corrected_changelog["updates"] = corrected_updates

    return corrected_changelog


def verify_and_correct_changelog(file_path):
    # Read the original file
    with open(file_path, "r") as f:
        changelog = json.load(f)

    # Calculate correct versions
    corrected_changelog = calculate_correct_version_numbers(changelog)

    # Check for issues
    version_issues = False
    author_issues = False
    empty_field_issues = False

    # Prepare lists to store issues
    version_mismatches = []
    author_mismatches = []
    empty_fields = []

    for original, corrected in zip(
        changelog["updates"], corrected_changelog["updates"]
    ):
        # Check version numbers
        if original["version"] != corrected["version"]:
            version_issues = True
            version_mismatches.append(
                {
                    "date": original["date"],
                    "current": original["version"],
                    "correct": corrected["version"],
                }
            )

        # Check author field
        if original.get("author") != "PCWStats Team":
            author_issues = True
            author_mismatches.append(
                {
                    "date": original["date"],
                    "current": original.get("author", "MISSING"),
                    "correct": "PCWStats Team",
                }
            )

        # Check for empty title or description
        if not original.get("title", "").strip():
            empty_field_issues = True
            empty_fields.append(
                {
                    "date": original["date"],
                    "field": "title",
                    "current": original.get("title", "MISSING"),
                }
            )

        if not original.get("description", "").strip():
            empty_field_issues = True
            empty_fields.append(
                {
                    "date": original["date"],
                    "field": "description",
                    "current": original.get("description", "MISSING"),
                }
            )

    # Print all found issues
    if version_issues:
        print("\nVERSION NUMBER ISSUES:")
        for issue in version_mismatches:
            print(f"Date: {issue['date']}")
            print(f"  Current: {issue['current']}")
            print(f"  Correct: {issue['correct']}")

    if author_issues:
        print("\nAUTHOR FIELD ISSUES:")
        for issue in author_mismatches:
            print(f"Date: {issue['date']}")
            print(f"  Current: {issue['current']}")
            print(f"  Should be: {issue['correct']}")

    if empty_field_issues:
        print("\nEMPTY FIELD ISSUES:")
        for issue in empty_fields:
            print(f"Date: {issue['date']}")
            print(f"  Empty field: {issue['field']}")
            print(f"  Current value: '{issue['current']}'")

    if not any([version_issues, author_issues, empty_field_issues]):
        print("All version numbers, author fields, and required fields are correct!")
        return

    # Ask for confirmation to update
    response = input("\nDo you want to update the file with corrections? (y/n): ")
    if response.lower() == "y":
        # Apply all corrections
        for i in range(len(changelog["updates"])):
            corrected = corrected_changelog["updates"][i]

            # Update version if needed
            if version_issues:
                changelog["updates"][i]["version"] = corrected["version"]

            # Update author if needed
            if author_issues:
                changelog["updates"][i]["author"] = "PCWStats Team"

            # Can't automatically fix empty fields, just warn
            if empty_field_issues:
                current_update = changelog["updates"][i]
                if not current_update.get("title", "").strip():
                    print(
                        f"Warning: Empty title field for {current_update['date']} - please fill manually"
                    )
                if not current_update.get("description", "").strip():
                    print(
                        f"Warning: Empty description field for {current_update['date']} - please fill manually"
                    )

        # Write corrected file
        with open(file_path, "w") as f:
            json.dump(changelog, f, indent=2)
        print(f"Updated {file_path} with corrections")
    else:
        print("No changes were made.")


if __name__ == "__main__":
    file_path = Path("../../Website-Configs/changelog.json")
    verify_and_correct_changelog(file_path)
