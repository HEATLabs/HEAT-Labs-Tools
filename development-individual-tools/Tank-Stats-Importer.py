import csv
import json
import os
from pathlib import Path

# file paths
CSV_FILE_PATH = "../../HEAT-Labs-Database/importer-sheet/detailed_stat_sheet.csv"
TANKS_BASE_DIR = "../../HEAT-Labs-Database/tanks"


def load_csv_data(csv_filepath):
    tanks_data = {}

    with open(csv_filepath, 'r', encoding='utf-8') as file:
        # Read all lines
        lines = file.readlines()

    # Find the TANK NAME row (it's the second row in CSV)
    tank_names = []
    for i, line in enumerate(lines):
        if 'TANK NAME' in line:
            row = next(csv.reader([line]))
            tank_names = [name.strip() for name in row[1:] if name.strip()]
            break

    # parse all subsequent rows for stat data
    for i, line in enumerate(lines):
        row = next(csv.reader([line]))
        if not row or not row[0] or row[0] == 'AGENT NAME' or row[0] == 'TANK NAME':
            continue

        stat_name = row[0].strip()
        if not stat_name or stat_name == '-' or stat_name == '':
            continue

        # For each tank, assign the value
        for idx, tank_name in enumerate(tank_names):
            if idx + 1 < len(row):
                value = row[idx + 1].strip()
                if value and value != '-' and value != '':
                    if tank_name not in tanks_data:
                        tanks_data[tank_name] = {}

                    # Convert to appropriate number type if possible
                    try:
                        if '.' in value:
                            tanks_data[tank_name][stat_name] = float(value)
                        else:
                            tanks_data[tank_name][stat_name] = int(value)
                    except ValueError:
                        tanks_data[tank_name][stat_name] = value

    return tanks_data


def get_user_sections():
    sections = {
        '1': 'FIREPOWER',
        '2': 'MOBILITY',
        '3': 'SURVIVABILITY',
        '4': 'RECON',
        '5': 'UTILITY'
    }

    print("\n=== Available Sections to Import ===")
    for key, section in sections.items():
        print(f"{key}. {section}")

    print("\nEnter the numbers of sections you want to import (e.g., '1 2 4' or '1,2,4' or 'all'):")
    choice = input("> ").strip().lower()

    selected_sections = []

    if choice == 'all':
        selected_sections = list(sections.values())
    else:
        # Parse the input
        parts = choice.replace(',', ' ').split()
        for part in parts:
            if part in sections:
                selected_sections.append(sections[part])

    if not selected_sections:
        print("No valid sections selected. Exiting.")
        exit()

    print(f"\nSelected sections: {', '.join(selected_sections)}")
    return selected_sections


def map_tank_name_to_folder(tank_name):
    mapping = {
        'ALVT': 'alvt',
        'XM1-90': 'xm1-90',
        'M60A1': 'm60a1',
        'M60A2': 'm60a2',
        'T-62AV': 't-62av',
        'Object 287': 'object-287',
        'HSTV-L': 'hstv-l',
        'M551A1': 'm551a1',
        'XM1-V': 'xm1-v',
        'M1E1': 'm1e1',
        'FV 4030/X': 'fv4030x',
        'Leopard 1A6A1': 'leopard-1a6a1',
        'AMX-10 RC': 'amx-10-rc',
        'M3A1 Bradley': 'm3a1-bradley',
        'Marder 1A3': 'marder-1a3'
    }

    # Check if we have a direct mapping
    if tank_name in mapping:
        return mapping[tank_name]

    # try to convert to lowercase and replace spaces/special chars
    folder_name = tank_name.lower()
    folder_name = folder_name.replace(' ', '-')
    folder_name = folder_name.replace('/', '-')
    folder_name = folder_name.replace('(', '')
    folder_name = folder_name.replace(')', '')

    return folder_name


def update_tank_json(tank_folder_path, tank_data, selected_sections):
    stock_json_path = tank_folder_path / 'stock.json'

    if not stock_json_path.exists():
        print(f"  ⚠ Warning: {stock_json_path} not found, skipping...")
        return False

    # Load existing JSON
    try:
        with open(stock_json_path, 'r', encoding='utf-8') as f:
            tank_json = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ✗ Error reading {stock_json_path}: {e}")
        return False

    # Get the tank's key (folder name) from the JSON
    tank_key = tank_folder_path.name

    # Check if the tank key exists in the JSON
    if tank_key not in tank_json:
        print(f"  ✗ Tank key '{tank_key}' not found in JSON structure")
        return False

    # Update each selected section
    updated_count = 0
    for section in selected_sections:
        if section in tank_json[tank_key]:
            # For each stat in the CSV data
            for stat_name, stat_value in tank_data.items():
                # Check if this stat belongs to the current section
                if stat_name in tank_json[tank_key][section]:
                    # Update the value
                    old_value = tank_json[tank_key][section][stat_name]

                    # Convert stat_value to the same type as old_value if possible
                    if isinstance(old_value, (int, float)):
                        try:
                            stat_value = float(stat_value) if '.' in str(stat_value) else int(stat_value)
                        except:
                            pass

                    if old_value != stat_value:
                        tank_json[tank_key][section][stat_name] = stat_value
                        print(f"    Updated {section}.{stat_name}: {old_value} → {stat_value}")
                        updated_count += 1
        else:
            print(f"  ⚠ Section '{section}' not found in {tank_key} JSON")

    if updated_count > 0:
        # Save the updated JSON
        try:
            with open(stock_json_path, 'w', encoding='utf-8') as f:
                json.dump(tank_json, f, indent=4, ensure_ascii=False)
            print(f"  ✓ Updated {updated_count} stats in {tank_folder_path.name}/stock.json")
            return True
        except Exception as e:
            print(f"  ✗ Error saving {stock_json_path}: {e}")
            return False
    else:
        print(f"  ℹ No matching stats found for {tank_folder_path.name}")
        return False


def main():
    # Resolve paths relative to this script
    script_dir = Path(__file__).parent
    csv_file = (script_dir / CSV_FILE_PATH).resolve()
    tanks_base_dir = (script_dir / TANKS_BASE_DIR).resolve()

    print(f"Looking for CSV at: {csv_file}")
    print(f"Looking for tanks at: {tanks_base_dir}")

    # Check if files/directories exist
    if not csv_file.exists():
        print(f"Error: CSV file not found at {csv_file}")
        print("Please check the CSV_FILE_PATH variable in the script")
        return

    if not tanks_base_dir.exists():
        print(f"Error: Tanks directory not found at {tanks_base_dir}")
        print("Please check the TANKS_BASE_DIR variable in the script")
        return

    # Load CSV data
    print("\nLoading CSV data...")
    tanks_data = load_csv_data(csv_file)
    print(f"Loaded data for {len(tanks_data)} tanks from CSV")

    # Debug: Show first tank's data
    if tanks_data:
        first_tank = list(tanks_data.keys())[0]
        print(f"\nSample data from {first_tank}:")
        sample_stats = list(tanks_data[first_tank].items())[:5]
        for stat, value in sample_stats:
            print(f"  {stat}: {value}")

    # Get user selection for sections
    selected_sections = get_user_sections()

    # Process each tank
    print("\n=== Starting Import ===")
    successful_updates = 0
    skipped_tanks = []
    missing_folders = []

    for tank_name, tank_stats in tanks_data.items():
        # Map to folder name
        folder_name = map_tank_name_to_folder(tank_name)
        tank_folder = tanks_base_dir / folder_name

        print(f"\nProcessing: {tank_name} → {folder_name}")

        # Check if the tank folder exists
        if not tank_folder.exists():
            print(f"  ✗ Tank folder not found: {tank_folder}")
            missing_folders.append(f"{tank_name} ({folder_name})")
            continue

        # Update the JSON
        if update_tank_json(tank_folder, tank_stats, selected_sections):
            successful_updates += 1
        else:
            skipped_tanks.append(tank_name)

    # Summary
    print("IMPORT SUMMARY")
    print(f"Total tanks in CSV: {len(tanks_data)}")
    print(f"Successfully updated: {successful_updates}")
    print(f"Skipped (JSON issues): {len(skipped_tanks)}")
    print(f"Missing folders: {len(missing_folders)}")

    if missing_folders:
        print("\nTanks with missing folders:")
        for tank in missing_folders:
            print(f"  - {tank}")

    if skipped_tanks:
        print("\nTanks skipped due to JSON errors:")
        for tank in skipped_tanks:
            print(f"  - {tank}")

    print("\nImport completed!")


if __name__ == "__main__":
    main()