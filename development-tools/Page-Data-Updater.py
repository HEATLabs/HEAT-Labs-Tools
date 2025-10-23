import pandas as pd
import json
import os
from collections import Counter


def convert_xlsx_to_json():
    # File paths
    xlsx_path = "../../HEAT-Labs-Configs/page-data.xlsx"
    json_path = "../../HEAT-Labs-Configs/page-data.json"

    # Read the Excel file
    df = pd.read_excel(xlsx_path, sheet_name="pages")

    # Remove empty columns
    df = df.dropna(axis=1, how="all")
    df = df.fillna("")

    # Extract the main data (pages)
    pages_data = []

    for index, row in df.iterrows():
        # Skip rows that are part of the statistics
        if (
            pd.isna(row["-PAGE-"])
            or not str(row["-PAGE-"]).startswith("http")
            or any(
                keyword in str(row["-PAGE-"])
                for keyword in [
                    "GOOGLE INDEX DATA",
                    "GOOGLE API STATUS",
                    "HTTPS PAGE STATUS",
                    "BREADCRUMB STATUS",
                ]
            )
        ):
            continue

        page_info = {
            "url": row["-PAGE-"],
            "gsc_status": row["-GSC-"],
            "g_api_status": row["-G-API-"],
            "https_status": row["-HTTPS-"],
            "breadcrumb_status": row["-BREAD-"],
        }
        pages_data.append(page_info)

    # Calculate statistics dynamically
    stats = {}

    # Extract all status values
    gsc_statuses = [page["gsc_status"] for page in pages_data]
    g_api_statuses = [page["g_api_status"] for page in pages_data]
    https_statuses = [page["https_status"] for page in pages_data]
    breadcrumb_statuses = [page["breadcrumb_status"] for page in pages_data]

    # Count each status
    stats["google_index_data"] = {
        "pending": gsc_statuses.count("PENDING"),
        "not_indexed": gsc_statuses.count("NOT INDEXED"),
        "indexed": gsc_statuses.count("INDEXED"),
    }

    stats["google_api_status"] = {
        "pending": g_api_statuses.count("PENDING"),
        "not_indexed": g_api_statuses.count("NOT INDEXED"),
        "indexed": g_api_statuses.count("INDEXED"),
    }

    stats["https_page_status"] = {
        "unknown": https_statuses.count("UNKNOWN"),
        "not_https": https_statuses.count("NOT HTTPS"),
        "https": https_statuses.count("HTTPS"),
    }

    stats["breadcrumb_status"] = {
        "unknown": breadcrumb_statuses.count("UNKNOWN"),
        "invalid": breadcrumb_statuses.count("INVALID"),
        "valid": breadcrumb_statuses.count("VALID"),
    }

    # Create JSON structure
    result = {
        "metadata": {
            "total_pages": len(pages_data),
            "source_file": "page-data.xlsx",
            "export_timestamp": pd.Timestamp.now().isoformat(),
        },
        "pages": pages_data,
        "statistics": stats,
    }

    # Write JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {len(pages_data)} pages")

    # Print summary
    print("\nSTATISTICS SUMMARY")
    print(f"Total pages processed: {len(pages_data)}")
    print("\nGoogle Index Status:")
    for status, count in stats["google_index_data"].items():
        print(f"  {status.replace('_', ' ').title()}: {count}")

    print("\nGoogle API Status:")
    for status, count in stats["google_api_status"].items():
        print(f"  {status.replace('_', ' ').title()}: {count}")

    print("\nHTTPS Status:")
    for status, count in stats["https_page_status"].items():
        print(f"  {status.replace('_', ' ').title()}: {count}")

    print("\nBreadcrumb Status:")
    for status, count in stats["breadcrumb_status"].items():
        print(f"  {status.replace('_', ' ').title()}: {count}")


if __name__ == "__main__":
    convert_xlsx_to_json()
