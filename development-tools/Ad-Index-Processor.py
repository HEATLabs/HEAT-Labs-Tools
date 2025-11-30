import pandas as pd
import json
import os
from datetime import datetime


def ad_index_processor(xlsx_path, json_path):
    try:
        # Read the Excel file
        df = pd.read_excel(xlsx_path, sheet_name="Sheet1")

        # Convert DataFrame to list of dictionaries
        new_data = df.replace({pd.NaT: None}).to_dict("records")

        # Replace None values with N/A
        for item in new_data:
            for key, value in item.items():
                if value is None:
                    item[key] = "N/A"

        # Load existing JSON data
        existing_data = []
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    try:
                        existing_data = json.loads(content)
                        if isinstance(existing_data, dict):
                            existing_data = []
                    except json.JSONDecodeError:
                        print(
                            "Warning: JSON file is corrupted or empty. Starting with empty data."
                        )
                        existing_data = []
                else:
                    existing_data = []

        # Create a dictionary of existing entries by AD_ID for lookup
        existing_dict = {item["AD_ID"]: item for item in existing_data}

        # Update or add new entries
        updated_data = existing_data.copy()
        new_entries_count = 0
        updated_entries_count = 0

        for new_item in new_data:
            ad_id = new_item["AD_ID"]

            if ad_id in existing_dict:
                # Update existing entry
                index = next(
                    i for i, item in enumerate(updated_data) if item["AD_ID"] == ad_id
                )
                updated_data[index] = new_item
                updated_entries_count += 1
            else:
                # Add new entry
                updated_data.append(new_item)
                new_entries_count += 1

        # Sort by NUMBER
        updated_data.sort(key=lambda x: x["NUMBER"])

        # Save to JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=4, ensure_ascii=False, default=str)

        print(f"JSON file updated successfully: {json_path}")
        print(f"Total entries: {len(updated_data)}")
        print(f"New entries added: {new_entries_count}")
        print(f"Entries updated: {updated_entries_count}")

        return updated_data

    except Exception as e:
        print(f"Error processing files: {e}")
        return None


def main():
    # File paths
    xlsx_file_path = "../../HEAT-Labs-Archives/google-ads/data/ad-index.xlsx"
    json_file_path = "../../HEAT-Labs-Archives/google-ads/data/ad-index.json"

    print(f"Processing Excel file: {xlsx_file_path}")
    print(f"Output JSON file: {json_file_path}")

    # Convert and update JSON
    result = ad_index_processor(xlsx_file_path, json_file_path)

    if result:
        print("Conversion completed successfully!")
    else:
        print("Conversion failed!")


if __name__ == "__main__":
    main()
