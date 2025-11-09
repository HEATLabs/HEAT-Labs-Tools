import os
import json
import pandas as pd
from datetime import datetime, timedelta
import warnings
import glob

# Suppress the openpyxl style warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.styles.stylesheet')


class GSCDataProcessor:
    def __init__(self, input_folder, output_path):
        self.input_folder = input_folder
        self.output_path = output_path
        self.all_data = {}

    # Safely convert value to int, return None if not possible
    def safe_int(self, value):
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            # Try to convert to float, then to int to handle both string numbers and floats (thanks microsoft)
            return int(float(value))
        except (ValueError, TypeError):
            return None

    # Parse date from various formats
    def parse_date(self, date_value):
        if pd.isna(date_value) or date_value is None:
            return None

        date_str = str(date_value).strip()
        if ' ' in date_str:
            date_str = date_str.split()[0]

        try:
            # Try parsing as date
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return None

    # Extract date range from all Excel files dynamically
    def get_date_range_from_files(self):
        all_dates = set()

        # Look for all Excel files in the input folder
        excel_files = glob.glob(os.path.join(self.input_folder, "*.xlsx"))

        if not excel_files:
            print("No Excel files found")
            # Fallback to hardcoded range if no files found
            start_date = datetime(2025, 10, 5)
            end_date = datetime(2025, 11, 7)
        else:
            print(f"Found {len(excel_files)} Excel files")

            for file_path in excel_files:
                try:
                    # Try to look for dates in the 'Chart' page
                    df = pd.read_excel(file_path, sheet_name='Chart')
                    if 'Date' in df.columns:
                        for date_val in df['Date']:
                            parsed_date = self.parse_date(date_val)
                            if parsed_date:
                                all_dates.add(parsed_date)
                except Exception as e:
                    print(f"Warning reading {os.path.basename(file_path)}: {e}")

            if not all_dates:
                print("No dates found in files, using default range")
                # Fallback to hardcoded range
                start_date = datetime(2025, 10, 5)
                end_date = datetime(2025, 11, 7)
            else:
                # Convert string dates to datetime objects for sorting
                date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in all_dates]
                start_date = min(date_objects)
                end_date = max(date_objects)

        # Generate complete date range
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        return dates

    # Initialize the data structure with all dates
    def initialize_data_structure(self, dates):
        for date in dates:
            self.all_data[date] = {
                "breadcrumbs": {
                    "invalid": "N/A",
                    "valid": "N/A"
                },
                "coverage": {
                    "not_indexed": "N/A",
                    "indexed": "N/A",
                    "impressions": "N/A"
                },
                "https": {
                    "non_https_urls": "N/A",
                    "https_urls": "N/A"
                },
                "video_indexing": {
                    "no_video_indexed": "N/A",
                    "video_indexed": "N/A",
                    "impressions": "N/A"
                }
            }

    # Process Breadcrumbs file
    def process_breadcrumbs_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name='Chart')
            for _, row in df.iterrows():
                date_str = self.parse_date(row['Date'])
                if date_str and date_str in self.all_data:
                    invalid_val = self.safe_int(row['Invalid'])
                    valid_val = self.safe_int(row['Valid'])

                    self.all_data[date_str]['breadcrumbs'][
                        'invalid'] = invalid_val if invalid_val is not None else "N/A"
                    self.all_data[date_str]['breadcrumbs']['valid'] = valid_val if valid_val is not None else "N/A"
            print(f"Processed Breadcrumbs data")
        except Exception as e:
            print(f"Error processing Breadcrumbs file: {e}")

    # Process Coverage file
    def process_coverage_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name='Chart')
            for _, row in df.iterrows():
                date_str = self.parse_date(row['Date'])
                if date_str and date_str in self.all_data:
                    not_indexed_val = self.safe_int(row['Not indexed'])
                    indexed_val = self.safe_int(row['Indexed'])
                    impressions_val = self.safe_int(row['Impressions'])

                    self.all_data[date_str]['coverage'][
                        'not_indexed'] = not_indexed_val if not_indexed_val is not None else "N/A"
                    self.all_data[date_str]['coverage']['indexed'] = indexed_val if indexed_val is not None else "N/A"
                    self.all_data[date_str]['coverage'][
                        'impressions'] = impressions_val if impressions_val is not None else "N/A"
            print(f"Processed Coverage data")
        except Exception as e:
            print(f"Error processing Coverage file: {e}")

    # Process HTTPS file
    def process_https_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name='Chart')
            for _, row in df.iterrows():
                date_str = self.parse_date(row['Date'])
                if date_str and date_str in self.all_data:
                    non_https_val = self.safe_int(row['Non-HTTPS URLs'])
                    https_val = self.safe_int(row['HTTPS URLs'])

                    self.all_data[date_str]['https'][
                        'non_https_urls'] = non_https_val if non_https_val is not None else "N/A"
                    self.all_data[date_str]['https']['https_urls'] = https_val if https_val is not None else "N/A"
            print(f"Processed HTTPS data")
        except Exception as e:
            print(f"Error processing HTTPS file: {e}")

    # Process video indexing file
    def process_video_indexing_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name='Chart')
            for _, row in df.iterrows():
                date_str = self.parse_date(row['Date'])
                if date_str and date_str in self.all_data:
                    no_video_val = self.safe_int(row['No video indexed'])
                    video_val = self.safe_int(row['Video indexed'])
                    impressions_val = self.safe_int(row['Impressions'])

                    self.all_data[date_str]['video_indexing'][
                        'no_video_indexed'] = no_video_val if no_video_val is not None else "N/A"
                    self.all_data[date_str]['video_indexing'][
                        'video_indexed'] = video_val if video_val is not None else "N/A"
                    self.all_data[date_str]['video_indexing'][
                        'impressions'] = impressions_val if impressions_val is not None else "N/A"
            print(f"Processed Video Indexing data")
        except Exception as e:
            print(f"Error processing Video Indexing file: {e}")

    # Find all Excel files
    def find_excel_files(self):
        excel_files = {}

        # Look for files
        file_patterns = {
            'breadcrumbs': ['Breadcrumbs.xlsx', 'heatlabs.net-Breadcrumbs.xlsx'],
            'coverage': ['Coverage.xlsx', 'heatlabs.net-Coverage.xlsx'],
            'https': ['HTTPS.xlsx', 'Https.xlsx', 'heatlabs.net-Https.xlsx'],
            'video_indexing': ['Video-Indexing.xlsx', 'Video-indexing.xlsx', 'heatlabs.net-Video-indexing.xlsx']
        }

        for file_type, patterns in file_patterns.items():
            for pattern in patterns:
                file_path = os.path.join(self.input_folder, pattern)
                if os.path.exists(file_path):
                    excel_files[file_type] = file_path
                    break
            else:
                print(f"No file found for {file_type}")

        return excel_files

    # Process all Excel files
    def process_all_files(self):
        print("Starting GSC data processing...")

        # Get complete date range dynamically
        dates = self.get_date_range_from_files()
        self.initialize_data_structure(dates)

        # Find and process each file
        excel_files = self.find_excel_files()

        processors = {
            'breadcrumbs': self.process_breadcrumbs_file,
            'coverage': self.process_coverage_file,
            'https': self.process_https_file,
            'video_indexing': self.process_video_indexing_file
        }

        for file_type, processor_func in processors.items():
            if file_type in excel_files:
                processor_func(excel_files[file_type])
            else:
                print(f"Skipping {file_type}: file not found")

        # Save to JSON
        self.save_to_json()

    # Save the processed data to JSON file
    def save_to_json(self):
        try:
            # Create the file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving JSON file: {e}")


def main():
    # Configuration
    INPUT_FOLDER = "../../HEAT-Labs-Configs/gsc-export"
    OUTPUT_PATH = "../../HEAT-Labs-Configs/gsc_data.json"

    # Verify input folder exists
    if not os.path.exists(INPUT_FOLDER):
        print(f"Input folder does not exist: {INPUT_FOLDER}")
        return

    # Create processor and run
    processor = GSCDataProcessor(INPUT_FOLDER, OUTPUT_PATH)
    processor.process_all_files()


if __name__ == "__main__":
    main()
