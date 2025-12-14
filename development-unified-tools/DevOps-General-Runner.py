import os
import sys
import json
import re
import xml.etree.ElementTree as ET
import pandas as pd
import argparse
import warnings
import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional

# Import dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Import Google API libraries
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Import requests
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Suppress warnings
warnings.filterwarnings(
    "ignore", category=UserWarning, module="openpyxl.styles.stylesheet"
)

# Configuration paths
DEFAULT_TARGET_DIRECTORY = "../../"
DEFAULT_JSON_FILE_PATH = "../../HEAT-Labs-Configs/home-stats.json"
DEFAULT_TXT_OUTPUT_DIR = "statistics"
DEFAULT_CREDENTIALS_FILE = "../credentials.json"
DEFAULT_GSC_OUTPUT = "../../HEAT-Labs-Configs/gsc-index.json"
DEFAULT_PAGE_DATA_XLSX = "../../HEAT-Labs-Configs/page-data.xlsx"
DEFAULT_PAGE_DATA_JSON = "../../HEAT-Labs-Configs/page-data.json"
DEFAULT_CHANGELOG_PATH = "../../HEAT-Labs-Configs/changelog.json"
DEFAULT_SEARCH_KEYWORDS = "../../HEAT-Labs-Configs/search-keywords.json"
DEFAULT_DAILY_COMMITS = "../../HEAT-Labs-Configs/daily_commits.json"
DEFAULT_GSC_EXPORT_DIR = "../../HEAT-Labs-Configs/gsc-export"
DEFAULT_GSC_DATA_JSON = "../../HEAT-Labs-Configs/gsc_data.json"

# File extensions to analyze
TEXT_EXTENSIONS = {
    "Code": [
        ".py",
        ".js",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".sql",
        ".sh",
        ".bash",
        ".bat",
        ".ps1",
        ".cmd",
        ".lua",
        ".r",
        ".pl",
        ".pm",
        ".tcl",
        ".awk",
        ".sed",
        ".dart",
        ".groovy",
        ".vb",
        ".vbs",
        ".asm",
        ".f",
        ".f90",
        ".f95",
        ".m",
        ".ml",
        ".mli",
        ".swift",
        ".vue",
        ".elm",
        ".clj",
        ".cljs",
        ".cljc",
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        ".lisp",
        ".lsp",
        ".hs",
        ".purs",
        ".ada",
        ".d",
        ".nim",
        ".zig",
        ".jl",
        ".cr",
        ".json5",
        ".hx",
        ".wren",
        ".p4",
        ".rkt",
        ".idris",
        ".e",
        ".pike",
        ".lean",
        ".v",
        ".agda",
        ".cob",
        ".cpy",
        ".abap",
        ".rpg",
        ".4gl",
        ".chpl",
        ".rex",
        ".omgrofl",
    ],
    "Markup": [
        ".md",
        ".rst",
        ".txt",
        ".tex",
        ".latex",
        ".bib",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".csv",
        ".tsv",
        ".xml",
        ".xsl",
        ".xsd",
        ".xslt",
        ".xhtml",
        ".svg",
        ".rss",
        ".atom",
    ],
    "Documentation": [
        ".doc",
        ".docx",
        ".pdf",
        ".rtf",
        ".odt",
        ".fodt",
        ".sxw",
        ".wpd",
        ".texi",
        ".me",
        ".ms",
    ],
    "Scripts": [
        ".ps1",
        ".cmd",
        ".bat",
        ".vbs",
        ".applescript",
        ".ahk",
        ".ksh",
        ".zsh",
        ".fish",
        ".csh",
        ".tcsh",
        ".mak",
        ".mk",
        ".ninja",
        ".ebuild",
        ".eclass",
        ".pkgbuild",
    ],
    "Config": [
        ".env",
        ".venv",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".gitmodules",
        ".dockerfile",
        ".npmrc",
        ".yarnrc",
        ".babelrc",
        ".eslint",
        ".prettierrc",
        ".stylelintrc",
        ".condarc",
        ".flake8",
        ".pylintrc",
        ".mypy.ini",
        ".pydocstyle",
        ".phpcs",
        ".phpmd",
    ],
}

# Directories to exclude from analysis
EXCLUDE_DIRS = [
    ".git",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".idea",
    ".vscode",
    "vendor",
    "bin",
    "obj",
]

# Binary file signatures to detect quickly
BINARY_SIGNATURES = [
    b"\x89PNG",
    b"GIF8",
    b"BM",
    b"\xFF\xD8\xFF",
    b"PK\x03\x04",
    b"%PDF",
    b"\x7FELF",
    b"MZ",
    b"\xCF\xFA\xED\xFE",
    b"\xCA\xFE\xBA\xBE",
]


# PROJECT STATISTICS COUNTER (Tool 1)
class ProjectStatisticsCounter:
    def __init__(self, target_dir=None, json_path=None, txt_dir=None):
        self.target_directory = target_dir or DEFAULT_TARGET_DIRECTORY
        self.json_file_path = json_path or DEFAULT_JSON_FILE_PATH
        self.txt_output_dir = txt_dir or DEFAULT_TXT_OUTPUT_DIR

    def is_binary(self, file_path, sample_size=8192):
        try:
            with open(file_path, "rb") as f:
                header = f.read(sample_size)

                for signature in BINARY_SIGNATURES:
                    if header.startswith(signature):
                        return True

                if b"\x00" in header:
                    return True

                text_characters = bytes(range(32, 127)) + b"\r\n\t\b"
                binary_chars = sum(1 for byte in header if byte not in text_characters)
                return binary_chars / len(header) > 0.3 if header else False
        except (IOError, OSError):
            return True

    def get_file_extension_category(self, file_path):
        _, ext = os.path.splitext(file_path.lower())

        for category, extensions in TEXT_EXTENSIONS.items():
            if ext in extensions:
                return category

        if not self.is_binary(file_path):
            return "Other Text"

        return None

    def count_lines_and_chars(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.count("\n") + (
                    1 if content and not content.endswith("\n") else 0
                )
                chars = len(content)
                return lines, chars
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 0, 0

    def format_number(self, num):
        return f"{num:,}"

    def get_file_size(self, file_path):
        try:
            return os.path.getsize(file_path)
        except (OSError, IOError):
            return 0

    def bytes_to_gb(self, bytes_size):
        return bytes_size / (1024**3)

    def analyze_directory(self):
        dir_stats = defaultdict(lambda: {"files": 0, "lines": 0, "chars": 0, "size": 0})
        dir_total_files = 0
        dir_total_lines = 0
        dir_total_chars = 0
        total_size_bytes = 0
        total_folders = 0
        binary_files_count = 0
        binary_files_size = 0
        all_files_count = 0
        all_files_size = 0

        print(f"\nScanning files in {self.target_directory}...\n")

        for root, dirs, files in os.walk(self.target_directory):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            total_folders += len(dirs)

            for file in files:
                file_path = os.path.join(root, file)
                all_files_count += 1

                if os.path.abspath(file_path) == os.path.abspath(__file__):
                    continue

                file_size = self.get_file_size(file_path)
                all_files_size += file_size
                total_size_bytes += file_size

                category = self.get_file_extension_category(file_path)

                if not category:
                    binary_files_count += 1
                    binary_files_size += file_size
                    continue

                lines, chars = self.count_lines_and_chars(file_path)

                dir_stats[category]["files"] += 1
                dir_stats[category]["lines"] += lines
                dir_stats[category]["chars"] += chars
                dir_stats[category]["size"] += file_size

                dir_total_files += 1
                dir_total_lines += lines
                dir_total_chars += chars

        print(f"\n{'=' * 50}")
        print("FILE ANALYSIS BREAKDOWN:")
        print(f"{'=' * 50}")
        print(
            f"Text files:      {self.format_number(dir_total_files)} files, {self.bytes_to_gb(sum(cat_stats['size'] for cat_stats in dir_stats.values())):.2f} GB"
        )
        print(
            f"Binary files:    {self.format_number(binary_files_count)} files, {self.bytes_to_gb(binary_files_size):.2f} GB"
        )
        print(
            f"Total all files: {self.format_number(all_files_count)} files, {self.bytes_to_gb(all_files_size):.2f} GB"
        )
        print(f"{'=' * 50}")

        return (
            dir_stats,
            dir_total_files,
            dir_total_lines,
            dir_total_chars,
            total_folders,
            total_size_bytes,
            all_files_count,
            all_files_size,
        )

    def format_statistics(
        self,
        stat_dict,
        files_count,
        lines_count,
        chars_count,
        folders_count,
        total_size_gb,
    ):
        output = ["=" * 80, f"PROJECT STATISTICS SUMMARY", "=" * 80]

        categories = sorted(stat_dict.keys())
        for category in categories:
            cat_stats = stat_dict[category]
            output.append(f"\n{category} Files:")
            output.append(f"  Files:      {self.format_number(cat_stats['files'])}")
            output.append(f"  Lines:      {self.format_number(cat_stats['lines'])}")
            output.append(f"  Characters: {self.format_number(cat_stats['chars'])}")

        output.append("\n" + "=" * 80)
        output.append(
            f"TOTAL: {self.format_number(files_count)} files, {self.format_number(folders_count)} folders, {self.format_number(lines_count)} lines, {self.format_number(chars_count)} characters"
        )
        output.append(f"TOTAL SIZE: {total_size_gb:.2f} GB")
        output.append("=" * 80)

        return "\n".join(output)

    def save_statistics_to_file(self, stats_output):
        if not os.path.exists(self.txt_output_dir):
            os.makedirs(self.txt_output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"project_stats_{timestamp}.txt"
        file_path = os.path.join(self.txt_output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(stats_output)

        return file_path

    def update_json_file(
        self, lines_of_code, files_count, folders_count, total_size_gb
    ):
        try:
            if os.path.exists(self.json_file_path):
                with open(self.json_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "creationDate": datetime.now().strftime("%B %d, %Y %H:%M:%S"),
                    "coffeePerDay": 0,
                    "stats": {
                        "teamMembers": 0,
                        "linesOfCode": 0,
                        "contributors": 0,
                        "filesCount": 0,
                        "foldersCount": 0,
                        "totalSizeGB": 0,
                    },
                }

            data["stats"]["linesOfCode"] = lines_of_code
            data["stats"]["filesCount"] = files_count
            data["stats"]["foldersCount"] = folders_count
            data["stats"]["totalSizeGB"] = round(total_size_gb, 2)

            with open(self.json_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            print(f"Statistics updated in JSON file: {self.json_file_path}")
            return True
        except Exception as e:
            print(f"Error updating JSON file: {e}")
            return False

    def run(self):
        print("RUNNING PROJECT STATISTICS COUNTER")

        (
            directory_stats,
            directory_total_files,
            directory_total_lines,
            directory_total_chars,
            directory_total_folders,
            directory_total_size_bytes,
            all_files_count,
            all_files_size,
        ) = self.analyze_directory()

        directory_total_size_gb = self.bytes_to_gb(all_files_size)

        stats_output = self.format_statistics(
            directory_stats,
            directory_total_files,
            directory_total_lines,
            directory_total_chars,
            directory_total_folders,
            directory_total_size_gb,
        )

        print(stats_output)

        # Ask user what to do with the results
        while True:
            print("\nOptions:")
            print("1. Save statistics to a text file")
            print("2. Save statistics to JSON file")
            print("3. Save to both text and JSON files")
            print("4. Return to main menu (without saving)")

            choice = input("\nEnter your choice (1-4): ").strip()

            if choice == "1":
                file_path = self.save_statistics_to_file(stats_output)
                print(f"\nStatistics saved to: {file_path}")
                input("\nPress Enter to return to main menu...")
                return True
            elif choice == "2":
                if self.update_json_file(
                    directory_total_lines,
                    directory_total_files,
                    directory_total_folders,
                    directory_total_size_gb,
                ):
                    print(f"Statistics saved to JSON file: {self.json_file_path}")
                input("\nPress Enter to return to main menu...")
                return True
            elif choice == "3":
                file_path = self.save_statistics_to_file(stats_output)
                print(f"\nStatistics saved to: {file_path}")
                if self.update_json_file(
                    directory_total_lines,
                    directory_total_files,
                    directory_total_folders,
                    directory_total_size_gb,
                ):
                    print(f"Statistics saved to JSON file: {self.json_file_path}")
                input("\nPress Enter to return to main menu...")
                return True
            elif choice == "4":
                return True
            else:
                print("Invalid choice. Please try again.")


# GSC INDEX CHECKER (Tool 2)
class GSCIndexChecker:
    def __init__(self, credentials_file=None, output_file=None):
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self.output_file = output_file or DEFAULT_GSC_OUTPUT
        self.service = None
        self.creds = None
        self.target_site = "https://heatlabs.net/"

        if not GOOGLE_API_AVAILABLE:
            print("Google API libraries not available. Install with:")
            print(
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
            self.service = None

    def authenticate(self):
        if not GOOGLE_API_AVAILABLE:
            return False

        SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
        token_file = "token.json"

        if os.path.exists(token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except ValueError as e:
                print(f"Token file is corrupted: {e}")
                print("Deleting corrupted token file and getting new credentials...")
                os.remove(token_file)
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    if not self._get_new_credentials():
                        return False
            else:
                if not self._get_new_credentials():
                    return False

        try:
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save token: {e}")

        try:
            self.service = build("searchconsole", "v1", credentials=self.creds)
            print("Successfully authenticated and built service!")
            return True
        except Exception as e:
            print(f"Error building service: {e}")
            self.service = None
            return False

    def _get_new_credentials(self):
        SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

        if not os.path.exists(self.credentials_file):
            print(f"Credentials file not found: {self.credentials_file}")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES
            )
            try:
                self.creds = flow.run_local_server(port=8080, open_browser=True)
            except Exception as e1:
                print(f"Failed with port 8080: {e1}")
                try:
                    self.creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as e2:
                    print(f"Failed with random port: {e2}")
                    print("\nTrying manual authorization flow...")
                    auth_url, _ = flow.authorization_url(prompt="consent")
                    print(
                        f"\nPlease visit this URL to authorize the application:\n{auth_url}"
                    )
                    auth_code = input("Enter the authorization code: ")
                    flow.fetch_token(code=auth_code)
                    self.creds = flow.credentials
            return True
        except Exception as e:
            print(f"Error getting new credentials: {e}")
            return False

    def verify_heatlabs_property(self):
        try:
            sites = self.service.sites().list().execute()
            properties = [site["siteUrl"] for site in sites.get("siteEntry", [])]

            print(f"Found properties: {properties}")

            heatlabs_variations = [
                "https://heatlabs.net/",
                "https://heatlabs.net",
                "sc-domain:heatlabs.net",
            ]

            for variation in heatlabs_variations:
                if variation in properties:
                    self.target_site = variation
                    print(f"Found HEAT Labs property: {self.target_site}")
                    return True

            print("HEAT Labs GitHub Pages not found in verified properties!")
            print("Please verify https://heatlabs.net in Google Search Console first.")
            return False
        except HttpError as e:
            print(f"Error fetching properties: {e}")
            return False

    def get_heatlabs_indexing_status(self, start_date=None, end_date=None):
        if not start_date:
            start_date = "2025-05-16"
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        print(f"Fetching data from {start_date} to {end_date} (all available data)")

        indexing_data = {
            "site_url": self.target_site,
            "last_checked": datetime.now().isoformat(),
            "date_range": {"start_date": start_date, "end_date": end_date},
            "pages": [],
            "summary": {
                "total_pages": 0,
                "indexed_pages": 0,
                "not_indexed_pages": 0,
                "errors": 0,
            },
        }

        try:
            all_pages = []
            start_row = 0
            row_limit = 1000

            while True:
                request = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["page"],
                    "rowLimit": row_limit,
                    "startRow": start_row,
                }

                response = (
                    self.service.searchanalytics()
                    .query(siteUrl=self.target_site, body=request)
                    .execute()
                )

                if "rows" not in response or len(response["rows"]) == 0:
                    break

                for row in response["rows"]:
                    page_url = row["keys"][0]
                    if page_url.startswith("https://heatlabs.net"):
                        page_data = {
                            "url": page_url,
                            "status": "indexed_and_served",
                            "last_crawled": None,
                            "indexing_state": "INDEXED",
                            "coverage_state": "VALID",
                            "discovery_date": None,
                            "crawl_time": None,
                            "robots_txt_state": "ALLOWED",
                            "user_agent": "DESKTOP",
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": row.get("ctr", 0),
                            "position": row.get("position", 0),
                        }
                        all_pages.append(page_data)

                if len(response["rows"]) < row_limit:
                    break

                start_row += row_limit
                print(f"Fetched {len(all_pages)} pages so far...")

            indexing_data["pages"] = all_pages
            indexing_data["summary"]["indexed_pages"] = len(all_pages)
            indexing_data["summary"]["total_pages"] = len(all_pages)

            print(f"Total pages found in all-time data: {len(all_pages)}")

            try:
                sitemaps = (
                    self.service.sitemaps().list(siteUrl=self.target_site).execute()
                )
                indexing_data["sitemaps"] = []
                for sitemap in sitemaps.get("sitemap", []):
                    sitemap_data = {
                        "path": sitemap.get("path", ""),
                        "last_submitted": sitemap.get("lastSubmitted", ""),
                        "is_pending": sitemap.get("isPending", False),
                        "is_sitemaps_index": sitemap.get("isSitemapsIndex", False),
                        "type": sitemap.get("type", ""),
                        "last_downloaded": sitemap.get("lastDownloaded", ""),
                        "warnings": sitemap.get("warnings", 0),
                        "errors": sitemap.get("errors", 0),
                    }
                    indexing_data["sitemaps"].append(sitemap_data)
            except HttpError as e:
                print(f"Error fetching sitemaps: {e}")
                indexing_data["sitemaps"] = []

        except HttpError as e:
            print(f"Error fetching data for HEAT Labs: {e}")
            indexing_data["error"] = str(e)

        return indexing_data

    def run(self, specific_urls=None, all_time=True):
        print("RUNNING GSC INDEX CHECKER")

        if not GOOGLE_API_AVAILABLE:
            print("Google API libraries not available. Cannot run GSC Index Checker.")
            input("\nPress Enter to return to main menu...")
            return True

        print("Starting authentication...")
        if not self.authenticate():
            print("Authentication failed! Cannot proceed.")
            input("\nPress Enter to return to main menu...")
            return True

        if self.service is None:
            print("Service not initialized properly. Authentication may have failed.")
            input("\nPress Enter to return to main menu...")
            return True

        print("Verifying HEAT Labs property...")
        if not self.verify_heatlabs_property():
            input("\nPress Enter to return to main menu...")
            return True

        print(f"Processing HEAT Labs indexing data for: {self.target_site}")

        if all_time:
            print("Fetching ALL-TIME data...")
            site_data = self.get_heatlabs_indexing_status()
        else:
            print("Fetching last 30 days data...")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            site_data = self.get_heatlabs_indexing_status(start_date=start_date)

        if specific_urls:
            inspected_urls = []
            for url in specific_urls:
                if url.startswith("https://heatlabs.net"):
                    print(f"  Inspecting: {url}")
                else:
                    print(f"  Skipping non HEAT Labs URL: {url}")
            site_data["individual_inspections"] = inspected_urls

        all_data = {
            "generated_at": datetime.now().isoformat(),
            "site_url": self.target_site,
            "data_type": "all_time" if all_time else "last_30_days",
            "data": site_data,
            "summary": {
                "total_pages_found": site_data["summary"]["total_pages"],
                "indexed_pages": site_data["summary"]["indexed_pages"],
                "errors": site_data["summary"]["errors"],
            },
        }

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            print(f"\nHEAT Labs indexing status data saved to: {self.output_file}")
            print(f"Data type: {'All-time' if all_time else 'Last 30 days'}")
            print(f"Total pages found: {all_data['summary']['total_pages_found']}")
            print(f"Indexed pages: {all_data['summary']['indexed_pages']}")

            if site_data["pages"]:
                print(f"\nSample indexed URLs:")
                for page in site_data["pages"][:5]:
                    print(f"  - {page['url']}")
                    if page.get("impressions", 0) > 0:
                        print(
                            f"    Impressions: {page['impressions']}, Clicks: {page['clicks']}"
                        )
                if len(site_data["pages"]) > 5:
                    print(f"  ... and {len(site_data['pages']) - 5} more")

        except Exception as e:
            print(f"Error saving to file: {e}")
            print("Data collected but could not save to file.")

        input("\nPress Enter to return to main menu...")
        return True


# GSC PROCESSOR (Tool 3)
class GSCProcessor:
    def __init__(self, input_folder=None, output_path=None):
        self.input_folder = input_folder or DEFAULT_GSC_EXPORT_DIR
        self.output_path = output_path or DEFAULT_GSC_DATA_JSON
        self.all_data = {}

    def safe_int(self, value):
        if pd.isna(value) or value == "" or value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def parse_date(self, date_value):
        if pd.isna(date_value) or date_value is None:
            return None

        date_str = str(date_value).strip()
        if " " in date_str:
            date_str = date_str.split()[0]

        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def get_date_range_from_files(self):
        all_dates = set()
        excel_files = glob.glob(os.path.join(self.input_folder, "*.xlsx"))

        if not excel_files:
            print("No Excel files found")
            start_date = datetime(2025, 10, 5)
            end_date = datetime(2025, 11, 7)
        else:
            print(f"Found {len(excel_files)} Excel files")

            for file_path in excel_files:
                try:
                    df = pd.read_excel(file_path, sheet_name="Chart")
                    if "Date" in df.columns:
                        for date_val in df["Date"]:
                            parsed_date = self.parse_date(date_val)
                            if parsed_date:
                                all_dates.add(parsed_date)
                except Exception as e:
                    print(f"Warning reading {os.path.basename(file_path)}: {e}")

            if not all_dates:
                print("No dates found in files, using default range")
                start_date = datetime(2025, 10, 5)
                end_date = datetime(2025, 11, 7)
            else:
                date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in all_dates]
                start_date = min(date_objects)
                end_date = max(date_objects)

        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        return dates

    def initialize_data_structure(self, dates):
        for date in dates:
            self.all_data[date] = {
                "breadcrumbs": {"invalid": "N/A", "valid": "N/A"},
                "coverage": {
                    "not_indexed": "N/A",
                    "indexed": "N/A",
                    "impressions": "N/A",
                },
                "https": {"non_https_urls": "N/A", "https_urls": "N/A"},
                "video_indexing": {
                    "no_video_indexed": "N/A",
                    "video_indexed": "N/A",
                    "impressions": "N/A",
                },
            }

    def find_excel_files(self):
        excel_files = {}
        file_patterns = {
            "breadcrumbs": ["Breadcrumbs.xlsx", "heatlabs.net-Breadcrumbs.xlsx"],
            "coverage": ["Coverage.xlsx", "heatlabs.net-Coverage.xlsx"],
            "https": ["HTTPS.xlsx", "Https.xlsx", "heatlabs.net-Https.xlsx"],
            "video_indexing": [
                "Video-Indexing.xlsx",
                "Video-indexing.xlsx",
                "heatlabs.net-Video-indexing.xlsx",
            ],
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

    def process_all_files(self):
        dates = self.get_date_range_from_files()
        self.initialize_data_structure(dates)
        excel_files = self.find_excel_files()

        processors = {
            "breadcrumbs": self.process_breadcrumbs_file,
            "coverage": self.process_coverage_file,
            "https": self.process_https_file,
            "video_indexing": self.process_video_indexing_file,
        }

        for file_type, processor_func in processors.items():
            if file_type in excel_files:
                processor_func(excel_files[file_type])
            else:
                print(f"Skipping {file_type}: file not found")

        self.save_to_json()

    def process_breadcrumbs_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name="Chart")
            for _, row in df.iterrows():
                date_str = self.parse_date(row["Date"])
                if date_str and date_str in self.all_data:
                    invalid_val = self.safe_int(row["Invalid"])
                    valid_val = self.safe_int(row["Valid"])
                    self.all_data[date_str]["breadcrumbs"]["invalid"] = (
                        invalid_val if invalid_val is not None else "N/A"
                    )
                    self.all_data[date_str]["breadcrumbs"]["valid"] = (
                        valid_val if valid_val is not None else "N/A"
                    )
            print(f"Processed Breadcrumbs data")
        except Exception as e:
            print(f"Error processing Breadcrumbs file: {e}")

    def process_coverage_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name="Chart")
            for _, row in df.iterrows():
                date_str = self.parse_date(row["Date"])
                if date_str and date_str in self.all_data:
                    not_indexed_val = self.safe_int(row["Not indexed"])
                    indexed_val = self.safe_int(row["Indexed"])
                    impressions_val = self.safe_int(row["Impressions"])
                    self.all_data[date_str]["coverage"]["not_indexed"] = (
                        not_indexed_val if not_indexed_val is not None else "N/A"
                    )
                    self.all_data[date_str]["coverage"]["indexed"] = (
                        indexed_val if indexed_val is not None else "N/A"
                    )
                    self.all_data[date_str]["coverage"]["impressions"] = (
                        impressions_val if impressions_val is not None else "N/A"
                    )
            print(f"Processed Coverage data")
        except Exception as e:
            print(f"Error processing Coverage file: {e}")

    def process_https_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name="Chart")
            for _, row in df.iterrows():
                date_str = self.parse_date(row["Date"])
                if date_str and date_str in self.all_data:
                    non_https_val = self.safe_int(row["Non-HTTPS URLs"])
                    https_val = self.safe_int(row["HTTPS URLs"])
                    self.all_data[date_str]["https"]["non_https_urls"] = (
                        non_https_val if non_https_val is not None else "N/A"
                    )
                    self.all_data[date_str]["https"]["https_urls"] = (
                        https_val if https_val is not None else "N/A"
                    )
            print(f"Processed HTTPS data")
        except Exception as e:
            print(f"Error processing HTTPS file: {e}")

    def process_video_indexing_file(self, file_path):
        try:
            df = pd.read_excel(file_path, sheet_name="Chart")
            for _, row in df.iterrows():
                date_str = self.parse_date(row["Date"])
                if date_str and date_str in self.all_data:
                    no_video_val = self.safe_int(row["No video indexed"])
                    video_val = self.safe_int(row["Video indexed"])
                    impressions_val = self.safe_int(row["Impressions"])
                    self.all_data[date_str]["video_indexing"]["no_video_indexed"] = (
                        no_video_val if no_video_val is not None else "N/A"
                    )
                    self.all_data[date_str]["video_indexing"]["video_indexed"] = (
                        video_val if video_val is not None else "N/A"
                    )
                    self.all_data[date_str]["video_indexing"]["impressions"] = (
                        impressions_val if impressions_val is not None else "N/A"
                    )
            print(f"Processed Video Indexing data")
        except Exception as e:
            print(f"Error processing Video Indexing file: {e}")

    def save_to_json(self):
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            print(f"GSC data saved to: {self.output_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

    def run(self):
        print("RUNNING GSC PROCESSOR")

        if not os.path.exists(self.input_folder):
            print(f"Input folder does not exist: {self.input_folder}")
            input("\nPress Enter to return to main menu...")
            return True

        self.process_all_files()
        input("\nPress Enter to return to main menu...")
        return True


# DAILY COMMIT FETCHER (Tool 4)
class DailyCommitFetcher:
    def __init__(self, output_file=None):
        self.output_file = output_file or DEFAULT_DAILY_COMMITS
        self.github_token = None
        self.load_token()

        self.org_name = "HEATLabs"
        self.repos = [
            ".github",
            "HEAT-Labs-Changelog",
            "HEAT-Labs-Configurator",
            "HEAT-Labs-Configs",
            "HEAT-Labs-Database",
            "HEAT-Labs-Discord",
            "HEAT-Labs-Discord-Bot",
            "HEAT-Labs-Socials",
            "HEAT-Labs-Videos",
            "HEAT-Labs-Brand-Kit",
            "HEAT-Labs-Mobile-App",
            "HEAT-Labs-Images",
            "HEAT-Labs-Images-Blogs",
            "HEAT-Labs-Images-Features",
            "HEAT-Labs-Images-Gallery",
            "HEAT-Labs-Images-Guides",
            "HEAT-Labs-Images-Maps",
            "HEAT-Labs-Images-News",
            "HEAT-Labs-Images-Tanks",
            "HEAT-Labs-Images-Tournaments",
            "HEAT-Labs-Games",
            "HEAT-Labs-Models",
            "HEAT-Labs-Mods",
            "HEAT-Labs-Archives",
            "HEAT-Labs-Sounds",
            "HEAT-Labs-Static",
            "HEAT-Labs-Statistics",
            "HEAT-Labs-Desktop",
            "HEAT-Labs-Status",
            "HEAT-Labs-Tools",
            "HEAT-Labs-Website",
            "HEAT-Labs-Website-Development",
        ]

        self.extra_repos = [
            {"owner": "ThatSINEWAVE", "repo": "HEAT-Labs-Views-API"},
        ]

    def load_token(self):
        if load_dotenv:
            load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
            self.github_token = os.getenv("GITHUB_TOKEN")
        else:
            self.github_token = None

    def get_all_commits(self, repo, owner=None):
        if not REQUESTS_AVAILABLE:
            print("Requests library not available. Install with: pip install requests")
            return []

        if not self.github_token:
            print("GitHub token not found. Please set GITHUB_TOKEN in ../.env")
            return []

        if owner:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        else:
            url = f"https://api.github.com/repos/{self.org_name}/{repo}/commits"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        all_commits = []
        page = 1

        while True:
            params = {"per_page": 100, "page": page}
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                page_commits = response.json()
                if not page_commits:
                    break
                all_commits.extend(page_commits)
                page += 1
            except Exception as e:
                print(f"Error fetching commits: {e}")
                break

        return all_commits

    def gather_commits(self, commits_data):
        daily_commits = defaultdict(list)

        for repo_data in commits_data:
            if isinstance(repo_data, tuple) and len(repo_data) == 2:
                repo, repo_commits = repo_data
            else:
                repo = repo_data["repo"]
                repo_commits = repo_data["commits"]

            for commit in repo_commits:
                if "commit" not in commit:
                    continue

                try:
                    commit_date = datetime.strptime(
                        commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"
                    ).date()
                    message = commit["commit"]["message"].split("\n")[0]
                    entry = f"[{repo}] {message}"
                    daily_commits[commit_date.isoformat()].append(entry)
                except Exception as e:
                    continue

        return dict(sorted(daily_commits.items(), reverse=True))

    def run(self):
        print("RUNNING DAILY COMMIT FETCHER")

        if not REQUESTS_AVAILABLE:
            print("Requests library not available. Cannot run Daily Commit Fetcher.")
            input("\nPress Enter to return to main menu...")
            return True

        if not self.github_token:
            print("GitHub token not found. Please set GITHUB_TOKEN in ../.env")
            input("\nPress Enter to return to main menu...")
            return True

        all_commits = []

        for repo in self.repos:
            try:
                commits = self.get_all_commits(repo)
                all_commits.append((repo, commits))
                print(f"Fetched {len(commits)} commits from {repo}")
            except Exception as e:
                print(f"Error fetching commits from {repo}: {str(e)}")

        for repo_info in self.extra_repos:
            try:
                commits = self.get_all_commits(
                    repo_info["repo"], owner=repo_info["owner"]
                )
                all_commits.append(
                    {
                        "repo": f"{repo_info['owner']}/{repo_info['repo']}",
                        "commits": commits,
                    }
                )
                print(
                    f"Fetched {len(commits)} commits from {repo_info['owner']}/{repo_info['repo']}"
                )
            except Exception as e:
                print(
                    f"Error fetching commits from {repo_info['owner']}/{repo_info['repo']}: {str(e)}"
                )

        daily_log = self.gather_commits(all_commits)

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(daily_log, f, indent=2, ensure_ascii=False)
            print(f"✅ Daily commit log saved to: {self.output_file}")
            print(f"Total days with commits: {len(daily_log)}")
        except Exception as e:
            print(f"Error saving commit log: {e}")

        input("\nPress Enter to return to main menu...")
        return True


# CHANGELOG VALIDATOR (Tool 5)
class ChangelogValidator:
    def __init__(self, changelog_path=None):
        self.changelog_path = changelog_path or DEFAULT_CHANGELOG_PATH

    def format_date_long(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d %B, %Y")
        except ValueError:
            return date_str

    def calculate_correct_version_numbers(self, changelog):
        updates_chronological = changelog["updates"][::-1]
        cumulative_changes = 0
        corrected_updates = []

        VERSION_TRANSITIONS = [
            {"from_version": "0.0.000", "major_version": 0},
            {"from_version": "0.9.000", "major_version": 1},
            {"from_version": "1.9.000", "major_version": 2},
        ]

        VERSION_TRANSITIONS.sort(
            key=lambda x: [int(n) for n in x["from_version"].split(".")]
        )

        for idx, update in enumerate(updates_chronological):
            additions = len(update.get("added", []))
            changes = len(update.get("changed", []))
            fixes = len(update.get("fixed", []))
            removals = len(update.get("removed", []))

            total_changes = additions + changes + fixes + removals
            cumulative_changes += total_changes

            current_major_version = 0
            current_middle_version = 0
            current_minor_version = 0

            temp_middle = (cumulative_changes - 1) // 1000
            temp_minor = (cumulative_changes - 1) % 1000
            temp_version = f"0.{temp_middle}.{temp_minor:03d}"

            for transition in reversed(VERSION_TRANSITIONS):
                transition_parts = [
                    int(n) for n in transition["from_version"].split(".")
                ]
                current_parts = [int(n) for n in temp_version.split(".")]

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

            base_transition = None
            for transition in VERSION_TRANSITIONS:
                if transition["major_version"] == current_major_version:
                    base_transition = transition
                    break

            if base_transition:
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
                    current_middle_version = (cumulative_changes - 1) // 1000
                    current_minor_version = (cumulative_changes - 1) % 1000
            else:
                current_middle_version = (cumulative_changes - 1) // 1000
                current_minor_version = (cumulative_changes - 1) % 1000

            correct_version = f"{current_major_version}.{current_middle_version}.{current_minor_version:03d}"

            corrected_update = update.copy()
            corrected_update["version"] = correct_version

            update_number = idx + 1
            pretty_date = self.format_date_long(update["date"])

            corrected_update["title"] = f"Update Number #{update_number}"
            corrected_update["description"] = (
                f"Full patch notes for Update v{correct_version} "
                f"(#{update_number}), detailing all changes made on {pretty_date}."
            )

            corrected_updates.append(corrected_update)

        corrected_updates = corrected_updates[::-1]
        corrected_changelog = changelog.copy()
        corrected_changelog["updates"] = corrected_updates
        return corrected_changelog, VERSION_TRANSITIONS

    def run(self):
        print("RUNNING CHANGELOG VALIDATOR")

        if not os.path.exists(self.changelog_path):
            print(f"Error: Changelog file not found at {self.changelog_path}")
            input("\nPress Enter to return to main menu...")
            return True

        try:
            with open(self.changelog_path, "r") as f:
                changelog = json.load(f)
        except Exception as e:
            print(f"Error reading changelog file: {e}")
            input("\nPress Enter to return to main menu...")
            return True

        (
            corrected_changelog,
            VERSION_TRANSITIONS,
        ) = self.calculate_correct_version_numbers(changelog)

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

            response = input(
                "\nDo you want to automatically fix and overwrite the changelog? (y/n): "
            )
            if response.lower() == "y":
                changelog["updates"] = corrected_changelog["updates"]
                for update in changelog["updates"]:
                    update["author"] = "HEAT Labs Team"

                with open(self.changelog_path, "w") as f:
                    json.dump(changelog, f, indent=2)
                print(f"✅ {self.changelog_path} has been updated and corrected.")
            else:
                print("❌ No changes were made.")
        else:
            print("All updates are properly formatted and correct!")

        input("\nPress Enter to return to main menu...")
        return True


# PAGE DATA UPDATER (Tool 6)
class PageDataUpdater:
    def __init__(self, xlsx_path=None, json_path=None):
        self.xlsx_path = xlsx_path or DEFAULT_PAGE_DATA_XLSX
        self.json_path = json_path or DEFAULT_PAGE_DATA_JSON

    def run(self):
        print("RUNNING PAGE DATA UPDATER")

        if not os.path.exists(self.xlsx_path):
            print(f"Error: Excel file not found at {self.xlsx_path}")
            input("\nPress Enter to return to main menu...")
            return True

        try:
            df = pd.read_excel(self.xlsx_path, sheet_name="pages")
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            input("\nPress Enter to return to main menu...")
            return True

        df = df.dropna(axis=1, how="all")
        df = df.fillna("")

        pages_data = []

        for index, row in df.iterrows():
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

        stats = {}
        gsc_statuses = [page["gsc_status"] for page in pages_data]
        g_api_statuses = [page["g_api_status"] for page in pages_data]
        https_statuses = [page["https_status"] for page in pages_data]
        breadcrumb_statuses = [page["breadcrumb_status"] for page in pages_data]

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

        result = {
            "metadata": {
                "total_pages": len(pages_data),
                "source_file": "page-data.xlsx",
                "export_timestamp": pd.Timestamp.now().isoformat(),
            },
            "pages": pages_data,
            "statistics": stats,
        }

        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✅ Successfully updated {len(pages_data)} pages to {self.json_path}")
        except Exception as e:
            print(f"Error writing JSON file: {e}")
            input("\nPress Enter to return to main menu...")
            return True

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

        input("\nPress Enter to return to main menu...")
        return True


# MAIN UNIFIED TOOL
class UnifiedHEATLabsTool:
    def __init__(self):
        self.tools = {
            "1": ("Project Statistics Counter", self.run_statistics_counter),
            "2": ("GSC Index Checker", self.run_gsc_checker),
            "3": ("GSC Processor", self.run_gsc_processor),
            "4": ("Daily Commit Fetcher", self.run_commit_fetcher),
            "5": ("Changelog Validator", self.run_changelog_validator),
            "6": ("Page Data Updater", self.run_page_updater),
            "7": ("Run All Tools", self.run_all_tools),
            "0": ("Quit", self.quit_tool),
        }

        self.running = True

    def display_menu(self):
        os.system("cls" if os.name == "nt" else "clear")
        print("DevOps General Runner")
        print("Available Tools:")

        for key, (name, _) in self.tools.items():
            print(f"{key}. {name}")

        print("\n" + "-" * 60)

    def run_statistics_counter(self):
        tool = ProjectStatisticsCounter()
        return tool.run()

    def run_gsc_checker(self):
        tool = GSCIndexChecker()
        return tool.run()

    def run_gsc_processor(self):
        tool = GSCProcessor()
        return tool.run()

    def run_commit_fetcher(self):
        tool = DailyCommitFetcher()
        return tool.run()

    def run_changelog_validator(self):
        tool = ChangelogValidator()
        return tool.run()

    def run_page_updater(self):
        tool = PageDataUpdater()
        return tool.run()

    def run_all_tools(self):
        print("RUNNING ALL TOOLS")

        tools_to_run = [
            ("Project Statistics Counter", self.run_statistics_counter),
            ("GSC Index Checker", self.run_gsc_checker),
            ("GSC Processor", self.run_gsc_processor),
            ("Daily Commit Fetcher", self.run_commit_fetcher),
            ("Changelog Validator", self.run_changelog_validator),
            ("Page Data Updater", self.run_page_updater),
        ]

        for i, (name, func) in enumerate(tools_to_run, 1):
            print(f"\n[{i}/{len(tools_to_run)}] Running {name}...")
            print("-" * 40)
            try:
                func()
            except Exception as e:
                print(f"Error running {name}: {e}")
                continue

        print("ALL TOOLS COMPLETED")
        input("\nPress Enter to return to main menu...")
        return True

    def quit_tool(self):
        print("\nThank you for using DevOps General Runner!")
        self.running = False
        return False

    def run(self):
        while self.running:
            self.display_menu()

            choice = input("\nSelect an option (0-7): ").strip()

            if choice in self.tools:
                tool_name, tool_func = self.tools[choice]
                print(f"\nSelected: {tool_name}")
                print("-" * 40)

                # Run the selected tool
                tool_func()
            else:
                print(f"\nInvalid option: {choice}")
                print("Please select a valid option (0-7).")
                input("\nPress Enter to continue...")


# MAIN EXECUTION
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="HEAT Labs Unified Tool - Integrates all 6 tools into one application"
    )
    parser.add_argument(
        "--tool",
        type=int,
        choices=range(0, 8),
        help="Directly run a specific tool (0-7, where 0=Quit, 7=All Tools)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    tool = UnifiedHEATLabsTool()

    if args.tool is not None:
        # Direct mode - run specific tool and exit
        choice = str(args.tool)
        if choice in tool.tools:
            tool_name, tool_func = tool.tools[choice]
            print(f"\nRunning: {tool_name}")
            if choice == "0":
                tool.quit_tool()
            else:
                tool_func()
                if choice != "7":  # Don't show menu after running single tool
                    print("\nTool execution completed.")
        else:
            print(f"Invalid tool number: {args.tool}")
    else:
        # Interactive mode
        tool.run()


if __name__ == "__main__":
    main()
