import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import (
    GSC_SITE_URL,
    GSC_SCOPES,
    GSC_TOKEN_FILE,
    GSC_CREDENTIALS_FILE,
    CACHE_FILE,
    HISTORICAL_DATA_FILE,
)

logger = logging.getLogger("gsc_discord_bot.gsc_service")

# Store the auth code as a global variable
AUTH_CODE = None


async def get_gsc_service():
    creds = None

    # Load token from file if it exists
    if os.path.exists(GSC_TOKEN_FILE):
        try:
            with open(GSC_TOKEN_FILE, "r") as token:
                creds = Credentials.from_authorized_user_info(
                    json.load(token), GSC_SCOPES
                )
        except Exception as e:
            logger.error(f"Error loading token file: {e}")

    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            # Create flow with explicit localhost redirect
            flow = InstalledAppFlow.from_client_secrets_file(
                GSC_CREDENTIALS_FILE, GSC_SCOPES, redirect_uri="http://localhost"
            )

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                prompt="consent", access_type="offline", include_granted_scopes="true"
            )

            # Print instructions for manual authentication
            logger.info("########################################################")
            logger.info("## Google OAuth Authorization Required")
            logger.info("## Please follow these steps:")
            logger.info(f"## 1. Open this URL in any browser: {auth_url}")
            logger.info("## 2. Log in with your Google account if needed")
            logger.info("## 3. Approve the permissions request")
            logger.info("## 4. When redirected to localhost, copy the ENTIRE URL")
            logger.info("##    (It will look like: http://localhost/?code=XYZ123...)")
            logger.info("## 5. Use the /auth command in Discord to provide the code")
            logger.info("########################################################")

            # Wait for the auth code to be set via Discord command
            global AUTH_CODE
            while AUTH_CODE is None:
                await asyncio.sleep(1)

            # Exchange code for tokens
            try:
                flow.fetch_token(code=AUTH_CODE)
                creds = flow.credentials
                AUTH_CODE = None  # Reset for next use
            except Exception as e:
                logger.error(f"Failed to exchange code for tokens: {str(e)}")
                raise Exception("Authentication failed. Please try again.")

        # Save credentials for next run
        with open(GSC_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("webmasters", "v3", credentials=creds)


async def fetch_search_analytics(service, days=7):
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        # First request: Overall performance
        overall_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": [],
                    "rowLimit": 1,
                },
            )
            .execute()
        )

        # Get daily data for trends
        daily_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["date"],
                    "rowLimit": 10,
                },
            )
            .execute()
        )

        # Second request: Top pages
        pages_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["page"],
                    "rowLimit": 10,
                },
            )
            .execute()
        )

        # Third request: Top queries
        queries_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["query"],
                    "rowLimit": 10,
                },
            )
            .execute()
        )

        # Fourth request: Get device data
        devices_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["device"],
                    "rowLimit": 5,
                },
            )
            .execute()
        )

        # Fifth request: Get country data
        countries_data = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["country"],
                    "rowLimit": 10,
                },
            )
            .execute()
        )

        # We'll create a placeholder for coverage data
        coverage_data = {"inspectionResults": []}  # Empty list as placeholder

        return {
            "overall": overall_data,
            "daily": daily_data,
            "pages": pages_data,
            "queries": queries_data,
            "devices": devices_data,
            "countries": countries_data,
            "coverage": coverage_data,
        }
    except Exception as e:
        logger.error(f"Error fetching GSC data: {e}")
        return None


async def load_cached_data():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
    return None


async def save_cached_data(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving cached data: {e}")


async def update_historical_data(current_data):
    today = datetime.today().strftime("%Y-%m-%d")

    # Get the overall metrics
    if not current_data or not current_data.get("overall", {}).get("rows"):
        return

    overall = current_data["overall"]["rows"][0]

    # Create new entry for today
    new_entry = {
        "date": today,
        "clicks": overall.get("clicks", 0),
        "impressions": overall.get("impressions", 0),
        "ctr": overall.get("ctr", 0) * 100,  # Convert to percentage
        "position": overall.get("position", 0),
    }

    # Load existing historical data
    historical_data = []
    if os.path.exists(HISTORICAL_DATA_FILE):
        try:
            with open(HISTORICAL_DATA_FILE, "r") as f:
                historical_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")

    # Add new entry and keep last 30 days only
    historical_data.append(new_entry)
    historical_data = historical_data[-30:]  # Keep only last 30 days

    # Save updated historical data
    try:
        with open(HISTORICAL_DATA_FILE, "w") as f:
            json.dump(historical_data, f)
    except Exception as e:
        logger.error(f"Error saving historical data: {e}")
