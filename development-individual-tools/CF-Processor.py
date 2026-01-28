import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configs
EXCEL_FOLDER = "../../HEAT-Labs-Configs/cf-export"
JSON_OUTPUT_PATH = "../../HEAT-Labs-Configs/cf-data.json"
YEAR = 2025


class DataAggregator:
    def __init__(self, excel_folder: str, json_path: str, base_year: int = 2025):
        self.excel_folder = Path(excel_folder)
        self.json_path = Path(json_path)
        self.base_year = base_year
        self.required_files = [
            "total_data_served.csv",
            "total_requests.csv",
            "unique_visitors.csv",
            "data_cached.csv",
        ]

    def parse_date(self, day_str: str) -> datetime:
        day_num, month_abbr = day_str.split()
        day_num = int(day_num)

        # Map month to month numbers
        month_map = {
            "JAN": 1,
            "FEB": 2,
            "MAR": 3,
            "APR": 4,
            "MAY": 5,
            "JUN": 6,
            "JUL": 7,
            "AUG": 8,
            "SEP": 9,
            "OCT": 10,
            "NOV": 11,
            "DEC": 12,
        }

        month_num = month_map.get(month_abbr.upper())
        if month_num is None:
            raise ValueError(f"Invalid month abbreviation: {month_abbr}")

        # Calculate year based on month
        if month_num == 12:
            year = self.base_year
        else:
            year = self.base_year + 1

        return datetime(year, month_num, day_num)

    def read_csv_files(self) -> pd.DataFrame:
        unique_visitors_path = self.excel_folder / "unique_visitors.csv"
        if not unique_visitors_path.exists():
            raise FileNotFoundError(
                f"unique_visitors.csv not found in {self.excel_folder}"
            )

        # Read unique visitors with dates
        df_visitors = pd.read_csv(unique_visitors_path)
        df_visitors.rename(
            columns={"timestamp": "date", "value": "unique_visitors"}, inplace=True
        )

        # Parse dates from unique_visitors
        df_visitors["datetime"] = df_visitors["date"].apply(self.parse_date)
        df_visitors = df_visitors.sort_values("datetime")
        df_visitors["date_iso"] = df_visitors["datetime"].dt.strftime("%Y-%m-%d")

        # Create base dataframe with dates from unique_visitors
        base_df = df_visitors[
            ["date", "date_iso", "datetime", "unique_visitors"]
        ].copy()

        # Read total_data_served.csv
        total_data_path = self.excel_folder / "total_data_served.csv"
        if total_data_path.exists():
            df_total_data = pd.read_csv(total_data_path)
            df_total_data["date"] = df_visitors["date"].values[: len(df_total_data)]
            df_total_data.rename(columns={"value": "total_data_served"}, inplace=True)

            # Merge with base dataframe
            base_df = pd.merge(
                base_df,
                df_total_data[["date", "total_data_served"]],
                on="date",
                how="left",
            )

        # Read total_requests.csv
        total_requests_path = self.excel_folder / "total_requests.csv"
        if total_requests_path.exists():
            df_requests = pd.read_csv(total_requests_path)
            df_requests["date"] = df_visitors["date"].values[: len(df_requests)]
            df_requests.rename(columns={"value": "total_requests"}, inplace=True)

            # Merge with base dataframe
            base_df = pd.merge(
                base_df, df_requests[["date", "total_requests"]], on="date", how="left"
            )

        # Read data_cached.csv
        data_cached_path = self.excel_folder / "data_cached.csv"
        if data_cached_path.exists():
            df_cached = pd.read_csv(data_cached_path)
            df_cached["date"] = df_visitors["date"].values[: len(df_cached)]
            df_cached.rename(columns={"value": "data_cached"}, inplace=True)

            # Merge with base dataframe
            base_df = pd.merge(
                base_df, df_cached[["date", "data_cached"]], on="date", how="left"
            )

        # Fill NaN values with 0 for numerical columns
        numerical_cols = [
            "total_data_served",
            "total_requests",
            "data_cached",
            "unique_visitors",
        ]
        for col in numerical_cols:
            if col in base_df.columns:
                base_df[col] = base_df[col].fillna(0).astype(int)

        return base_df

    def load_existing_json(self) -> Dict[str, Any]:
        if not self.json_path.exists():
            initial_data = {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_days": 0,
                },
                "daily_data": [],
                "totals": {
                    "all_time": {
                        "data_served_gb": 0,
                        "data_cached_gb": 0,
                        "total_requests": 0,
                        "total_visitors": 0,
                    },
                    "monthly": {},
                },
            }
            self.save_json(initial_data)
            return initial_data

        with open(self.json_path, "r") as f:
            return json.load(f)

    def get_latest_date_in_json(self, json_data: Dict[str, Any]) -> Optional[datetime]:
        if not json_data.get("daily_data"):
            return None

        dates = [
            datetime.fromisoformat(item["date_iso"]) for item in json_data["daily_data"]
        ]
        return max(dates) if dates else None

    def convert_df_to_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        records = []
        for _, row in df.iterrows():
            record = {
                "date_iso": row["date_iso"],
                "total_data_served": int(row.get("total_data_served", 0)),
                "data_cached": int(row.get("data_cached", 0)),
                "total_requests": int(row.get("total_requests", 0)),
                "unique_visitors": int(row.get("unique_visitors", 0)),
            }
            records.append(record)
        return records

    # Calculate totals and monthly summaries
    def calculate_totals(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Initialize totals
        total_data_served = 0
        total_data_cached = 0
        total_requests = 0
        total_visitors = 0

        # Initialize monthly totals
        monthly_totals = {}

        for record in records:
            # Update all-time totals
            total_data_served += record["total_data_served"]
            total_data_cached += record["data_cached"]
            total_requests += record["total_requests"]
            total_visitors += record["unique_visitors"]

            # Extract month from date
            month_key = record["date_iso"][:7]

            # Initialize month entry if not exists
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {
                    "data_served": 0,
                    "data_cached": 0,
                    "requests": 0,
                    "visitors": 0,
                }

            # Update monthly totals
            monthly_totals[month_key]["data_served"] += record["total_data_served"]
            monthly_totals[month_key]["data_cached"] += record["data_cached"]
            monthly_totals[month_key]["requests"] += record["total_requests"]
            monthly_totals[month_key]["visitors"] += record["unique_visitors"]

        # Convert bytes to GB for data served and cached
        BYTES_TO_GB = 1_000_000_000

        return {
            "all_time": {
                "data_served_gb": round(total_data_served / BYTES_TO_GB, 2),
                "data_cached_gb": round(total_data_cached / BYTES_TO_GB, 2),
                "total_requests": total_requests,
                "total_visitors": total_visitors,
            },
            "monthly": {
                month: {
                    "data_served_gb": round(data["data_served"] / BYTES_TO_GB, 2),
                    "data_cached_gb": round(data["data_cached"] / BYTES_TO_GB, 2),
                    "requests": data["requests"],
                    "visitors": data["visitors"],
                }
                for month, data in monthly_totals.items()
            },
        }

    def update_json_data(
        self, new_records: List[Dict[str, Any]], existing_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        existing_records = existing_data.get("daily_data", [])
        existing_dates = {record["date_iso"] for record in existing_records}

        # Filter out records that already exist
        new_unique_records = [
            record for record in new_records if record["date_iso"] not in existing_dates
        ]

        if new_unique_records:
            all_records = existing_records + new_unique_records
            # Sort by date
            all_records.sort(key=lambda x: x["date_iso"])

            # Calculate totals
            totals = self.calculate_totals(all_records)

            # Update metadata
            metadata = existing_data.get("metadata", {})
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["total_days"] = len(all_records)

            if all_records:
                metadata["date_range"] = {
                    "start": all_records[0]["date_iso"],
                    "end": all_records[-1]["date_iso"],
                }
            return {"metadata": metadata, "daily_data": all_records, "totals": totals}
        else:
            existing_data["metadata"]["last_updated"] = datetime.now().isoformat()
            return existing_data

    def save_json(self, data: Dict[str, Any]) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.json_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def process(self) -> Dict[str, Any]:
        # Load existing JSON data
        existing_data = self.load_existing_json()
        existing_days = len(existing_data.get("daily_data", []))

        # Read and process CSV files
        try:
            df = self.read_csv_files()
            new_records = self.convert_df_to_records(df)

            # Update with existing data
            updated_data = self.update_json_data(new_records, existing_data)

            # Get counts
            new_days = len(updated_data.get("daily_data", [])) - existing_days
            total_days = len(updated_data.get("daily_data", []))

            print(f"Days in JSON: {existing_days}")
            print(f"New days added: {new_days}")
            print(f"Total days now: {total_days}")

            # Save to JSON
            self.save_json(updated_data)

            return updated_data

        except Exception as e:
            print(f"Error processing data: {e}")
            import traceback

            traceback.print_exc()
            return existing_data


def main():
    # Initialize the aggregator
    aggregator = DataAggregator(
        excel_folder=EXCEL_FOLDER, json_path=JSON_OUTPUT_PATH, base_year=YEAR
    )

    # Process the data
    aggregator.process()


if __name__ == "__main__":
    main()
