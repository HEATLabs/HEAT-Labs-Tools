import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Required Google API libraries not found.")
    print(
        "Please install them with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    sys.exit(1)

# Google Search Console API scope
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# Target website - PCWStats GitHub Pages
TARGET_SITE = "https://pcwstats.github.io/"


# Initialize the indexing status checker with credentials
class PCWStatsIndexingChecker:
    def __init__(self, credentials_file: str = "../credentials.json"):
        self.credentials_file = credentials_file
        self.service = None
        self.creds = None
        self.target_site = TARGET_SITE

    # Authenticate with Google Search Console API
    def authenticate(self) -> bool:
        token_file = "token.json"

        # Load existing token if available
        if os.path.exists(token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except ValueError as e:
                print(f"Token file is corrupted: {e}")
                print("Deleting corrupted token file and getting new credentials...")
                os.remove(token_file)
                self.creds = None

        # If there are no valid credentials, get new ones
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

        # Save credentials for next run
        try:
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save token: {e}")

        # Build the service
        try:
            self.service = build("searchconsole", "v1", credentials=self.creds)
            print("Successfully authenticated and built service!")
            return True
        except Exception as e:
            print(f"Error building service: {e}")
            self.service = None
            return False

    # Get new credentials through OAuth flow
    def _get_new_credentials(self) -> bool:
        if not os.path.exists(self.credentials_file):
            print(f"Credentials file not found: {self.credentials_file}")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES
            )

            # Try different approaches for redirect URI
            try:
                # First try with specific port
                self.creds = flow.run_local_server(port=8080, open_browser=True)
            except Exception as e1:
                print(f"Failed with port 8080: {e1}")
                try:
                    # Try with port 0 (random available port)
                    self.creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as e2:
                    print(f"Failed with random port: {e2}")
                    # Try manual flow
                    print("\nTrying manual authorization flow...")
                    print(
                        "If the above fails, you may need to update your OAuth redirect URIs."
                    )
                    print(
                        "Go to Google Cloud Console > APIs & Credentials > OAuth 2.0 Client IDs"
                    )
                    print("Edit your client ID and add these redirect URIs:")
                    print("- http://localhost:8080")
                    print("- http://localhost:8080/")
                    print("- http://localhost")
                    print("- http://127.0.0.1:8080")
                    print("- http://127.0.0.1:8080/")

                    # Manual flow
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

    # Verify that PCWStats Pages are in Search Console properties
    def verify_pcwstats_property(self) -> bool:
        try:
            sites = self.service.sites().list().execute()
            properties = [site["siteUrl"] for site in sites.get("siteEntry", [])]

            print(f"Found properties: {properties}")

            # Check for exact match or variations
            pcwstats_variations = [
                "https://pcwstats.github.io/",
                "https://pcwstats.github.io",
                "sc-domain:pcwstats.github.io",
            ]

            for variation in pcwstats_variations:
                if variation in properties:
                    self.target_site = variation
                    print(f"Found PCWStats property: {self.target_site}")
                    return True

            print("PCWStats GitHub Pages not found in verified properties!")
            print(
                "Please verify https://pcwstats.github.io in Google Search Console first."
            )
            return False

        except HttpError as e:
            print(f"Error fetching properties: {e}")
            return False

    # Get indexing status specifically for PCWStats Pages
    def get_pcwstats_indexing_status(
        self, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

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
            # Get search analytics data to find indexed pages
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": 1000,
                "startRow": 0,
            }

            response = (
                self.service.searchanalytics()
                .query(siteUrl=self.target_site, body=request)
                .execute()
            )

            if "rows" in response:
                for row in response["rows"]:
                    page_url = row["keys"][0]

                    # Only include PCWStats URLs
                    if page_url.startswith("https://pcwstats.github.io"):
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
                        }
                        indexing_data["pages"].append(page_data)
                        indexing_data["summary"]["indexed_pages"] += 1

            indexing_data["summary"]["total_pages"] = len(indexing_data["pages"])

            # Get sitemap data
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
            print(f"Error fetching data for PCWStats: {e}")
            indexing_data["error"] = str(e)

        return indexing_data

    # Inspect specific PCWStats URLs for detailed indexing information
    def inspect_pcwstats_url(self, inspect_url: str) -> Dict[str, Any]:
        # Ensure the URL is a PCWStats URL
        if not inspect_url.startswith("https://pcwstats.github.io"):
            return {
                "url": inspect_url,
                "error": "URL is not a PCWStats GitHub Pages URL",
                "verdict": "INVALID_URL",
            }

        try:
            request_body = {"inspectionUrl": inspect_url, "siteUrl": self.target_site}

            response = (
                self.service.urlInspection()
                .index()
                .inspect(body=request_body)
                .execute()
            )

            inspection_result = response.get("inspectionResult", {})
            index_status = inspection_result.get("indexStatusResult", {})

            return {
                "url": inspect_url,
                "verdict": index_status.get("verdict", "UNKNOWN"),
                "coverage_state": index_status.get("coverageState", "UNKNOWN"),
                "robotstxt_state": index_status.get("robotsTxtState", "UNKNOWN"),
                "indexing_state": index_status.get("indexingState", "UNKNOWN"),
                "last_crawl_time": index_status.get("lastCrawlTime", ""),
                "page_fetch_state": index_status.get("pageFetchState", "UNKNOWN"),
                "google_canonical": index_status.get("googleCanonical", ""),
                "user_canonical": index_status.get("userCanonical", ""),
                "referring_urls": index_status.get("referringUrls", []),
                "crawled_as": index_status.get("crawledAs", "UNKNOWN"),
            }

        except HttpError as e:
            print(f"Error inspecting URL {inspect_url}: {e}")
            return {"url": inspect_url, "error": str(e), "verdict": "ERROR"}

    # Run a comprehensive indexing status check for PCWStats
    def run_pcwstats_check(
        self,
        specific_urls: List[str] = None,
        output_file: str = "../../Website-Configs/gsc-index.json",
    ) -> None:
        print("Starting authentication...")
        if not self.authenticate():
            print("Authentication failed! Cannot proceed.")
            return

        if self.service is None:
            print("Service not initialized properly. Authentication may have failed.")
            return

        print("Verifying PCWStats property...")
        if not self.verify_pcwstats_property():
            return

        print(f"Processing PCWStats indexing data for: {self.target_site}")

        # Get general indexing data
        site_data = self.get_pcwstats_indexing_status()

        # If specific URLs provided, inspect them individually
        if specific_urls:
            inspected_urls = []
            for url in specific_urls:
                if url.startswith("https://pcwstats.github.io"):
                    print(f"  Inspecting: {url}")
                    inspection = self.inspect_pcwstats_url(url)
                    inspected_urls.append(inspection)
                else:
                    print(f"  Skipping non-PCWStats URL: {url}")

            site_data["individual_inspections"] = inspected_urls

        all_data = {
            "generated_at": datetime.now().isoformat(),
            "site_url": self.target_site,
            "data": site_data,
            "summary": {
                "total_pages_found": site_data["summary"]["total_pages"],
                "indexed_pages": site_data["summary"]["indexed_pages"],
                "errors": site_data["summary"]["errors"],
            },
        }

        # Save to JSON file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            print(f"\nPCWStats indexing status data saved to: {output_file}")
            print(f"Total pages found: {all_data['summary']['total_pages_found']}")
            print(f"Indexed pages: {all_data['summary']['indexed_pages']}")

            # Show some sample URLs if found
            if site_data["pages"]:
                print(f"\nSample indexed URLs:")
                for page in site_data["pages"][:5]:  # Show first 5
                    print(f"  - {page['url']}")
                if len(site_data["pages"]) > 5:
                    print(f"  ... and {len(site_data['pages']) - 5} more")

        except Exception as e:
            print(f"Error saving to file: {e}")
            print("Data collected but could not save to file.")


# Help set up OAuth configuration properly
def setup_oauth_config():
    print("=== OAuth Configuration Setup ===")
    print("\nTo fix the redirect_uri_mismatch error, follow these steps:")
    print("\n1. Go to Google Cloud Console (https://console.cloud.google.com/)")
    print("2. Select your project: businessassistant-438415")
    print("3. Go to 'APIs & Services' > 'Credentials'")
    print("4. Find your OAuth 2.0 Client ID and click 'Edit'")
    print("5. In 'Authorized redirect URIs', add these URIs:")
    print("   - http://localhost:8080")
    print("   - http://localhost:8080/")
    print("   - http://localhost")
    print("   - http://127.0.0.1:8080")
    print("   - http://127.0.0.1:8080/")
    print("6. Save the changes")
    print("7. Also make sure these APIs are enabled:")
    print("   - Google Search Console API")
    print("   - Indexing API (optional, for URL inspection)")
    print(
        "\n8. Wait a few minutes for changes to propagate, then run the script again."
    )
    print("\nAlternatively, you can run with --manual flag for manual authorization.")


# Main function to run the PCWStats indexing status checker
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Check PCWStats GitHub Pages indexing status in Google Search Console"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Show OAuth setup instructions"
    )
    parser.add_argument("--urls", nargs="*", help="Specific PCWStats URLs to inspect")
    args = parser.parse_args()

    if args.setup:
        setup_oauth_config()
        return

    checker = PCWStatsIndexingChecker()

    # Use specific URLs if provided
    specific_urls = args.urls if args.urls else None

    # Run the PCWStats check
    checker.run_pcwstats_check(
        specific_urls=specific_urls, output_file="../../Website-Configs/gsc-index.json"
    )


if __name__ == "__main__":
    main()
