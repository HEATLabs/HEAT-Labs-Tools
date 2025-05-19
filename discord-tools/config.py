import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path("../.env"))

# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
UPDATES_CHANNEL_ID = int(os.getenv("UPDATES_CHANNEL_ID"))
COMMANDS_CHANNEL_ID = int(os.getenv("COMMANDS_CHANNEL_ID"))

# Google Search Console configuration
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "https://pcwstats.github.io/")
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GSC_TOKEN_FILE = "token.json"
GSC_CREDENTIALS_FILE = os.getenv("GSC_CREDENTIALS_FILE", "credentials.json")

# Report cached data file
CACHE_FILE = "gsc_previous_data.json"
HISTORICAL_DATA_FILE = "gsc_historical_data.json"

# Country code mapping
COUNTRY_CODES = {
    "us": "United States",
    "gb": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "in": "India",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
    "br": "Brazil",
    "ru": "Russia",
    "cn": "China",
    "es": "Spain",
    "it": "Italy",
    "mx": "Mexico",
    "nl": "Netherlands",
    "se": "Sweden",
    "kr": "South Korea",
    "za": "South Africa",
}
