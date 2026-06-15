import json
import os
from datetime import datetime, timezone
from pathlib import Path

# CONFIG
JSON_FILE_PATH = "../../HEAT-Labs-Configs/player-records.json"
CDN_BASE_URL = "https://cdn6.heatlabs.net/player-records/"


def load_existing_records():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print(f"Warning: {JSON_FILE_PATH} is corrupted. Creating new file.")
            return []
    return []


def save_records(records):
    # Ensure directory exists
    Path(JSON_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as file:
        json.dump(records, file, indent=2, ensure_ascii=False)


def get_record_input(record_type):
    print(f"Adding new {record_type} record:")

    record = {}

    while True:
        try:
            record['number'] = int(input(f"  {record_type} number: "))
            break
        except ValueError:
            print("  Please enter a valid number.")

    record['vehicle'] = input(f"  Vehicle used: ")
    record['agent'] = input(f"  Agent name: ")

    # Get just the filename, then prepend the CDN URL
    proof_filename = input(f"  Name of image proving the record: ")
    record['proof_image'] = f"{CDN_BASE_URL}{proof_filename}"

    record['player_name'] = input(f"  Player's name: ")
    record['map'] = input(f"  Map name: ")

    return record


def add_new_record_entry(records, record_type):
    print(f"\n[ Adding new {record_type} entry ]")

    # Get the record data
    record_data = get_record_input(record_type)

    # Create a new entry with ONLY the category that was entered
    new_entry = {
        record_type: record_data,
        'timestamp': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        'entry_id': len(records)  # Add an ID for reference
    }

    return new_entry


def display_menu():
    print("PLAYER RECORDS MANAGEMENT SYSTEM")
    print("What would you like to do?")
    print("1. Add Total Captures record")
    print("2. Add Total Vehicles Destroyed record")
    print("3. Add Total Deaths record")
    print("4. Add Total Assists record")
    print("5. Add Total Damage Caused record")
    print("6. Add Total Damage Blocked record")
    print("7. View all records")
    print("8. Exit")


def view_records(records):
    if not records:
        print("\n[ No records found in the database ]")
        return

    print(f"TOTAL RECORDS: {len(records)}")

    for i, record in enumerate(records):
        print(f"\n--- Record #{record.get('entry_id', i)} ---")
        print(f"Timestamp: {record.get('timestamp', 'Unknown')}")

        # Display each category that has data (skip metadata fields)
        for key, value in record.items():
            if key not in ['timestamp', 'entry_id']:
                if isinstance(value, dict):
                    print(f"\n  {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {key}: {value}")


def main():
    # Load existing records
    records = load_existing_records()

    # Define record types with their menu options
    record_categories = {
        1: "Total Captures",
        2: "Total Vehicles Destroyed",
        3: "Total Deaths",
        4: "Total Assists",
        5: "Total Damage Caused",
        6: "Total Damage Blocked"
    }

    while True:
        display_menu()

        try:
            choice = input("\nEnter your choice (1-8): ").strip()

            if choice == '8':
                print("Thank you for using Player Records System!")
                print(f"Total entries saved: {len(records)}")
                break

            elif choice == '7':
                view_records(records)
                continue

            elif choice in ['1', '2', '3', '4', '5', '6']:
                choice_num = int(choice)
                record_type = record_categories[choice_num]

                # Create and add new entry
                new_entry = add_new_record_entry(records, record_type)
                records.append(new_entry)

                # Save immediately after each entry
                save_records(records)

                print("RECORD SUCCESSFULLY ADDED AND SAVED!")
                print(f"Category: {record_type}")
                print(f"Entry ID: {new_entry['entry_id']}")
                print(f"Timestamp: {new_entry['timestamp']}")
                print(f"Saved to: {JSON_FILE_PATH}")

                # Ask if user wants to continue or go back to menu
                print("\nReturning to main menu...")

            else:
                print("\n[ Invalid choice! Please enter a number between 1 and 8 ]")

        except KeyboardInterrupt:
            print("\n\n[ Operation cancelled by user ]")
            break
        except Exception as e:
            print(f"\n[ An error occurred: {e} ]")
            print("[ Returning to menu... ]")


if __name__ == "__main__":
    main()