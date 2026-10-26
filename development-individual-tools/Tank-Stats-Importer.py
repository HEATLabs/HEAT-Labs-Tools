import csv
import json
import os
from pathlib import Path

# file paths
CSV_FILE_PATH = "../../HEAT-Labs-Database/importer-sheet/detailed_stat_sheet.csv"
TANKS_BASE_DIR = "../../HEAT-Labs-Database/tanks"

# Rows in the CSV that are structural (not stats)
SECTION_HEADERS = {
    'FIREPOWER', 'MOBILITY', 'SURVIVABILITY', 'RECON', 'UTILITY'
}
SKIP_ROWS = {
    'AGENT NAME', 'TANK NAME',
    'MAIN AMMO TYPE', 'SECONDARY AMMO TYPE',
    'MAIN SHELL TYPE', 'SECONDARY SHELL TYPE',
}


def is_range_string(value):
    if not isinstance(value, str):
        return False
    # must contain a '-' and both sides must be numeric
    parts = value.split('-')
    if len(parts) != 2:
        return False
    left, right = parts[0].strip(), parts[1].strip()
    try:
        float(left)
        float(right)
        return True
    except ValueError:
        return False


def normalize_range_string(value):
    """Collapse whitespace in a range string: '50 - 400' -> '50-400'."""
    parts = value.split('-')
    left, right = parts[0].strip(), parts[1].strip()
    return f"{left}-{right}"

# Convert a CSV cell string into the appropriate Python type.
def parse_cell_value(raw_value):
    if raw_value is None:
        return None
    value = raw_value.strip()
    if value == '' or value == '-':
        return None

    # Range value, e.g. "50-150" -> keep as string "50-150"
    if is_range_string(value):
        return normalize_range_string(value)

    # Plain numeric value
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_csv_data(csv_filepath):
    tanks_data = {}

    with open(csv_filepath, 'r', encoding='utf-8') as file:
        # Read all lines
        lines = file.readlines()

    # Find the TANK NAME row (it's the second row in CSV)
    tank_names = []
    for line in lines:
        if 'TANK NAME' in line:
            row = next(csv.reader([line]))
            tank_names = [name.strip() for name in row[1:] if name.strip()]
            break

    if not tank_names:
        raise RuntimeError("Could not find 'TANK NAME' header row in CSV")

    # Find the AMMO TYPE rows to get shell types
    main_ammo_types = {}
    secondary_ammo_types = {}
    for line in lines:
        row = next(csv.reader([line]))
        if not row:
            continue

        if row[0] == 'MAIN AMMO TYPE':
            for idx, tank_name in enumerate(tank_names):
                if idx + 1 < len(row):
                    value = row[idx + 1].strip()
                    if value and value != '-' and value != '':
                        main_ammo_types[tank_name] = value

        if row[0] == 'SECONDARY AMMO TYPE':
            for idx, tank_name in enumerate(tank_names):
                if idx + 1 < len(row):
                    value = row[idx + 1].strip()
                    if value and value != '-' and value != '':
                        secondary_ammo_types[tank_name] = value

    # Parse stat rows (skip structural rows)
    for line in lines:
        row = next(csv.reader([line]))
        if not row or not row[0]:
            continue

        stat_name = row[0].strip()

        # Skip structural / header rows
        if stat_name in SKIP_ROWS or stat_name in SECTION_HEADERS:
            continue
        if stat_name == '-' or stat_name == '':
            continue

        # For each tank, assign the value
        for idx, tank_name in enumerate(tank_names):
            if idx + 1 < len(row):
                parsed = parse_cell_value(row[idx + 1])
                if parsed is None:
                    continue
                tanks_data.setdefault(tank_name, {})[stat_name] = parsed

    # Add shell types to tanks_data
    for tank_name in tank_names:
        tanks_data.setdefault(tank_name, {})
        if tank_name in main_ammo_types:
            tanks_data[tank_name]['MAIN SHELL TYPE'] = main_ammo_types[tank_name]

        if tank_name in secondary_ammo_types:
            tanks_data[tank_name]['SECONDARY SHELL TYPE'] = secondary_ammo_types[tank_name]

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
        'M60A3E2': 'm60a3e2',
        'T-62AV': 't-62av',
        'T-72SH': 't-72sh',
        'Object 287': 'object-287',
        'HSTV-L': 'hstv-l',
        'M551A1': 'm551a1',
        'M1150 ABV': 'm1150-abv',
        'XM1-V': 'xm1-v',
        'M1E1': 'm1e1',
        'FV 4030/X': 'fv4030x',
        'Leopard 1A6A1': 'leopard-1a6a1',
        'Leopard 2FK': 'leopard-2fk',
        'Leopard 2K ST': 'leopard-2k-st',
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


def values_equal(a, b):
    """Compare two values, treating int 5 and float 5.0 as equal."""
    if isinstance(a, (int, float)) and not isinstance(a, bool) \
            and isinstance(b, (int, float)) and not isinstance(b, bool):
        return a == b
    return a == b


def coerce_to_match(old_value, new_value):
    # Existing JSON value is a range string -> store as range string
    if is_range_string(old_value):
        if is_range_string(new_value):
            return normalize_range_string(new_value)
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            return str(new_value)
        return new_value

    # Existing JSON value is numeric -> coerce new value to number
    if isinstance(old_value, (int, float)) and not isinstance(old_value, bool):
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            return new_value
        try:
            return float(new_value) if '.' in str(new_value) else int(new_value)
        except (ValueError, TypeError):
            return new_value

    # Existing JSON value is a plain string -> coerce numbers to string
    if isinstance(old_value, str):
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            return str(new_value)
        return new_value

    return new_value


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
        if section not in tank_json[tank_key]:
            print(f"  ⚠ Section '{section}' not found in {tank_key} JSON")
            continue

        section_obj = tank_json[tank_key][section]

        for stat_name, stat_value in tank_data.items():
            # Shell types can live in any section in your JSON — check all
            if stat_name in ('MAIN SHELL TYPE', 'SECONDARY SHELL TYPE'):
                if stat_name in section_obj:
                    old_value = section_obj[stat_name]
                    if not values_equal(old_value, stat_value):
                        section_obj[stat_name] = stat_value
                        print(f"    Updated {section}.{stat_name}: {old_value} → {stat_value}")
                        updated_count += 1
                continue

            # Normal stat: only update if it exists in this section
            if stat_name in section_obj:
                old_value = section_obj[stat_name]
                new_value = coerce_to_match(old_value, stat_value)

                if not values_equal(old_value, new_value):
                    section_obj[stat_name] = new_value
                    print(f"    Updated {section}.{stat_name}: {old_value} → {new_value}")
                    updated_count += 1

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
        sample_stats = list(tanks_data[first_tank].items())[:7]
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