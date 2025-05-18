import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import tempfile

import discord
from discord import app_commands, Embed, Color, File
from discord.ext import tasks
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("../gsc_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger("gsc_discord_bot")

# Load environment variables
load_dotenv(Path("../../.env"))

# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
UPDATES_CHANNEL_ID = int(os.getenv("UPDATES_CHANNEL_ID"))
COMMANDS_CHANNEL_ID = int(os.getenv("COMMANDS_CHANNEL_ID"))

# Google Search Console configuration
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "https://pcwstats.github.io/")
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GSC_TOKEN_FILE = "../token.json"
GSC_CREDENTIALS_FILE = os.getenv("GSC_CREDENTIALS_FILE", "credentials.json")

# Report cached data file
CACHE_FILE = "../gsc_previous_data.json"
HISTORICAL_DATA_FILE = "../gsc_historical_data.json"

# Create Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# Get an authorized Google Search Console API service instance
async def get_gsc_service():
    creds = None

    # Load token from file if it exists
    if os.path.exists(GSC_TOKEN_FILE):
        with open(GSC_TOKEN_FILE, "r") as token:
            creds = Credentials.from_authorized_user_info(json.load(token), GSC_SCOPES)

    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GSC_CREDENTIALS_FILE, GSC_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(GSC_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    # Build and return the service
    return build("webmasters", "v3", credentials=creds)


# Fetch search analytics data from Google Search Console
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


# Load previously cached GSC data for comparison
async def load_cached_data():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
    return None


# Save current GSC data for future comparisons
async def save_cached_data(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving cached data: {e}")


# Update historical data with current metrics for trend analysis
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


# Create a combined 2x2 grid of all trend charts
async def create_combined_trend_chart(data_dict):
    if not data_dict.get("daily", {}).get("rows"):
        return None

    # Extract dates and metrics
    dates = [row["keys"][0] for row in data_dict["daily"]["rows"]]
    display_dates = [d[5:] for d in dates]  # Format dates for display (MM-DD)

    # Prepare data for all metrics
    metrics = {
        "clicks": [row.get("clicks", 0) for row in data_dict["daily"]["rows"]],
        "impressions": [
            row.get("impressions", 0) for row in data_dict["daily"]["rows"]
        ],
        "ctr": [
            row.get("ctr", 0) * 100 for row in data_dict["daily"]["rows"]
        ],  # Convert to percentage
        "position": [row.get("position", 0) for row in data_dict["daily"]["rows"]],
    }

    # Create figure with 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("Performance Trends (Last 7 Days)", fontsize=16)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95], pad=3.0)

    # Plot clicks
    axs[0, 0].plot(display_dates, metrics["clicks"], marker="o", color="blue")
    axs[0, 0].set_title("Clicks")
    axs[0, 0].set_ylabel("Clicks")
    axs[0, 0].grid(True, linestyle="--", alpha=0.7)
    axs[0, 0].tick_params(axis="x", rotation=45)

    # Plot impressions
    axs[0, 1].plot(display_dates, metrics["impressions"], marker="o", color="orange")
    axs[0, 1].set_title("Impressions")
    axs[0, 1].set_ylabel("Impressions")
    axs[0, 1].grid(True, linestyle="--", alpha=0.7)
    axs[0, 1].tick_params(axis="x", rotation=45)

    # Plot CTR
    axs[1, 0].plot(display_dates, metrics["ctr"], marker="o", color="green")
    axs[1, 0].set_title("Click-Through Rate (CTR)")
    axs[1, 0].set_ylabel("CTR (%)")
    axs[1, 0].grid(True, linestyle="--", alpha=0.7)
    axs[1, 0].tick_params(axis="x", rotation=45)

    # Plot position (inverted)
    axs[1, 1].plot(display_dates, metrics["position"], marker="o", color="purple")
    axs[1, 1].set_title("Average Position")
    axs[1, 1].set_ylabel("Position")
    axs[1, 1].invert_yaxis()
    axs[1, 1].grid(True, linestyle="--", alpha=0.7)
    axs[1, 1].tick_params(axis="x", rotation=45)

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name, bbox_inches="tight")
        plt.close()
        return tmp.name


# Create a pie chart showing device distribution
async def create_device_chart(data_dict):
    if not data_dict.get("devices", {}).get("rows"):
        return None

    devices = [row["keys"][0] for row in data_dict["devices"]["rows"]]
    clicks = [row.get("clicks", 0) for row in data_dict["devices"]["rows"]]

    # Create the plot
    plt.figure(figsize=(8, 8))
    colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99"]

    plt.pie(clicks, labels=devices, autopct="%1.1f%%", colors=colors, startangle=90)
    plt.axis("equal")
    plt.title("Clicks by Device Type")

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        plt.savefig(tmp.name)
        plt.close()
        return tmp.name


# Generate Discord embeds for GSC report with charts
async def generate_report_embeds(current_data, previous_data=None):
    if not current_data or not current_data.get("overall"):
        return [
            Embed(
                title="⚠️ GSC Report Error",
                description="No data available from Google Search Console.",
                color=Color.red(),
            )
        ]

    # Extract current metrics
    overall = current_data.get("overall", {}).get("rows", [{}])[0]
    current_clicks = overall.get("clicks", 0)
    current_impressions = overall.get("impressions", 0)
    current_ctr = overall.get("ctr", 0) * 100  # Convert to percentage
    current_position = overall.get("position", 0)

    # Extract previous metrics for comparison if available
    prev_clicks = 0
    prev_impressions = 0
    prev_ctr = 0
    prev_position = 0

    if previous_data and previous_data.get("overall", {}).get("rows"):
        prev_overall = previous_data.get("overall", {}).get("rows", [{}])[0]
        prev_clicks = prev_overall.get("clicks", 0)
        prev_impressions = prev_overall.get("impressions", 0)
        prev_ctr = prev_overall.get("ctr", 0) * 100
        prev_position = prev_overall.get("position", 0)

    # Calculate changes
    click_change = current_clicks - prev_clicks
    impression_change = current_impressions - prev_impressions
    ctr_change = current_ctr - prev_ctr
    position_change = prev_position - current_position  # Note: Lower position is better

    # Create embeds
    embeds = []

    # Main overview embed
    main_embed = Embed(
        title="🔍 PCWStats Search Console Report",
        description=f"Performance summary for the last 7 days\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        color=Color.blue(),
    )

    # Add metric fields with change indicators
    click_emoji = "📈" if click_change >= 0 else "📉"
    main_embed.add_field(
        name=f"{click_emoji} Clicks",
        value=f"**{current_clicks:,}** "
        + (f"({click_change:+,})" if previous_data else ""),
        inline=True,
    )

    imp_emoji = "📈" if impression_change >= 0 else "📉"
    main_embed.add_field(
        name=f"{imp_emoji} Impressions",
        value=f"**{current_impressions:,}** "
        + (f"({impression_change:+,})" if previous_data else ""),
        inline=True,
    )

    ctr_emoji = "📈" if ctr_change >= 0 else "📉"
    main_embed.add_field(
        name=f"{ctr_emoji} CTR",
        value=f"**{current_ctr:.2f}%** "
        + (f"({ctr_change:+.2f}%)" if previous_data else ""),
        inline=True,
    )

    pos_emoji = "📈" if position_change >= 0 else "📉"
    main_embed.add_field(
        name=f"{pos_emoji} Avg Position",
        value=f"**{current_position:.1f}** "
        + (f"({position_change:+.1f})" if previous_data else ""),
        inline=True,
    )

    # Add recommendation based on metrics
    main_embed.add_field(
        name="💡 Quick Insight",
        value=generate_insight(current_data, previous_data),
        inline=False,
    )

    main_embed.set_footer(text="PCWStats GSC Bot")
    embeds.append(main_embed)

    # Create combined content embed
    content_embed = Embed(
        title="📊 Performance Details",
        description="Top performing pages, queries, and geographic data",
        color=Color.dark_grey(),
    )

    # Add Top Pages section
    if current_data.get("pages", {}).get("rows"):
        pages_content = ""
        for i, page in enumerate(current_data["pages"]["rows"][:10], 1):
            page_path = page["keys"][0].replace(GSC_SITE_URL, "/")
            pages_content += f"{i}. **{page_path}**\n"
            pages_content += f"   ↳ {page['clicks']} clicks | {int(page['impressions']):,} impressions | {(page['ctr'] * 100):.1f}% CTR | Pos: {page['position']:.1f}\n"
        content_embed.add_field(
            name="📄 Top Performing Pages", value=pages_content, inline=False
        )

    # Add Top Queries section
    if current_data.get("queries", {}).get("rows"):
        queries_content = ""
        for i, query in enumerate(current_data["queries"]["rows"][:10], 1):
            queries_content += f"{i}. **{query['keys'][0]}**\n"
            queries_content += f"   ↳ {query['clicks']} clicks | {int(query['impressions']):,} impressions | {(query['ctr'] * 100):.1f}% CTR | Pos: {query['position']:.1f}\n"
        content_embed.add_field(
            name="🔎 Top Search Queries", value=queries_content, inline=False
        )

    # Add Geographic section
    if current_data.get("countries", {}).get("rows"):
        countries_content = ""
        for i, country in enumerate(current_data["countries"]["rows"][:10], 1):
            country_code = country["keys"][0]
            countries_content += f"{i}. **{country_name_from_code(country_code)}**\n"
            countries_content += f"   ↳ {country['clicks']} clicks | {int(country['impressions']):,} impressions | {(country['ctr'] * 100):.1f}% CTR\n"
        content_embed.add_field(
            name="🌎 Top Countries", value=countries_content, inline=False
        )

    # Add Device breakdown
    if current_data.get("devices", {}).get("rows"):
        device_content = ""
        for device in current_data["devices"]["rows"]:
            device_type = device["keys"][0]
            device_content += f"- **{device_type.capitalize()}**: {device['clicks']} clicks ({(device['clicks'] / current_clicks * 100):.1f}%)\n"
        content_embed.add_field(
            name="📱 Device Breakdown", value=device_content, inline=False
        )

    embeds.append(content_embed)

    return embeds


# Convert country code to country name
def country_name_from_code(code):
    countries = {
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
    return countries.get(code.lower(), code)


# Generate an insight based on the metrics
def generate_insight(current_data, previous_data):
    if not previous_data or not previous_data.get("overall", {}).get("rows"):
        return "Not enough historical data for insights yet."

    overall = current_data.get("overall", {}).get("rows", [{}])[0]
    prev_overall = previous_data.get("overall", {}).get("rows", [{}])[0]

    # Calculate changes
    click_change = overall.get("clicks", 0) - prev_overall.get("clicks", 0)
    click_change_percent = (
        (click_change / prev_overall.get("clicks", 1)) * 100
        if prev_overall.get("clicks", 0) > 0
        else 0
    )

    impression_change = overall.get("impressions", 0) - prev_overall.get(
        "impressions", 0
    )
    impression_change_percent = (
        (impression_change / prev_overall.get("impressions", 1)) * 100
        if prev_overall.get("impressions", 0) > 0
        else 0
    )

    ctr_change = (overall.get("ctr", 0) - prev_overall.get("ctr", 0)) * 100
    position_change = prev_overall.get("position", 0) - overall.get("position", 0)

    # Generate insight based on metrics
    insights = []

    if click_change_percent > 20:
        insights.append(
            f"Significant traffic increase! Clicks up by {click_change_percent:.1f}%."
        )
    elif click_change_percent < -20:
        insights.append(
            f"Traffic dropped by {abs(click_change_percent):.1f}%. Consider reviewing content strategy."
        )

    if impression_change_percent > 20:
        insights.append(f"Visibility improved by {impression_change_percent:.1f}%.")
    elif impression_change_percent < -20:
        insights.append(
            f"Site visibility decreased by {abs(impression_change_percent):.1f}%."
        )

    if ctr_change > 1:
        insights.append(
            f"CTR improved by {ctr_change:.1f}%. Your meta titles/descriptions are working well!"
        )
    elif ctr_change < -1:
        insights.append(
            f"CTR decreased by {abs(ctr_change):.1f}%. Consider optimizing meta titles/descriptions."
        )

    if position_change > 0.5:
        insights.append(f"Ranking improved by {position_change:.1f} positions!")
    elif position_change < -0.5:
        insights.append(f"Rankings dropped by {abs(position_change):.1f} positions.")

    if not insights:
        return "Metrics are stable compared to the previous period."

    # Return the most significant insight
    return insights[0]


# Send a GSC report with charts to the specified channel
async def send_report_with_charts(channel, current_data, previous_data=None):
    if not current_data:
        await channel.send("⚠️ No data available from Google Search Console.")
        return

    # Generate chart files
    chart_files = []
    try:
        # Generate combined trend chart (2x2 grid)
        combined_chart = await create_combined_trend_chart(current_data)
        if combined_chart:
            chart_files.append(("performance_trends.png", combined_chart))

        # Generate device distribution chart
        device_chart = await create_device_chart(current_data)
        if device_chart:
            chart_files.append(("device_distribution.png", device_chart))

    except Exception as e:
        logger.error(f"Error creating charts: {e}")

    # Generate embeds
    embeds = await generate_report_embeds(current_data, previous_data)

    # Send the report embeds first
    for embed in embeds:
        await channel.send(embed=embed)

    # Send all chart files as separate messages with proper embeds
    for i in range(len(chart_files)):
        file = File(chart_files[i][1], filename=chart_files[i][0])
        chart_embed = Embed(
            title=f"📊 {chart_files[i][0].replace('_', ' ').replace('.png', '').title()}"
        )
        chart_embed.set_image(url=f"attachment://{chart_files[i][0]}")
        await channel.send(embed=chart_embed, file=file)

    # Clean up temporary files
    for _, file_path in chart_files:
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error deleting temporary file {file_path}: {e}")


# Send the daily report at 12 UTC
async def send_daily_report():
    logger.info("Running daily GSC report")

    updates_channel = client.get_channel(UPDATES_CHANNEL_ID)
    if not updates_channel:
        logger.error(f"Could not find updates channel with ID {UPDATES_CHANNEL_ID}")
        return

    try:
        # Get GSC service
        service = await get_gsc_service()

        # Get data
        current_data = await fetch_search_analytics(service)
        previous_data = await load_cached_data()

        # Send the report to Discord with charts
        await send_report_with_charts(updates_channel, current_data, previous_data)

        # Update historical data for trend analysis
        await update_historical_data(current_data)

        # Save current data for next comparison
        await save_cached_data(current_data)

    except Exception as e:
        logger.error(f"Error in daily report: {e}")
        await updates_channel.send(
            embed=Embed(
                title="⚠️ GSC Report Error",
                description=f"Failed to generate GSC report: {str(e)}",
                color=Color.red(),
            )
        )


# Schedule the daily report to run at 12 UTC
async def schedule_daily_report():
    while True:
        now = datetime.now(timezone.utc)

        # Calculate next run time (today at 12:00 UTC or tomorrow if already past)
        next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()

        logger.info(
            f"Next report scheduled for {next_run} UTC (in {wait_seconds / 3600:.1f} hours)"
        )
        await asyncio.sleep(wait_seconds)

        # Send the report
        await send_daily_report()


# Command to immediately generate and send a GSC report on-demand
@tree.command(
    name="checknow",
    description="Get an immediate Google Search Console report",
    guild=discord.Object(id=GUILD_ID),
)
async def check_now(interaction: discord.Interaction):
    # Check if command is used in the correct channel
    if interaction.channel_id != COMMANDS_CHANNEL_ID:
        await interaction.response.send_message(
            f"⚠️ This command can only be used in the designated commands channel.",
            ephemeral=True,
        )
        return

    # Respond to let the user know we're working on it
    await interaction.response.defer(thinking=True)

    try:
        # Get GSC service
        service = await get_gsc_service()

        # Get data
        current_data = await fetch_search_analytics(service)
        previous_data = await load_cached_data()

        # Send the initial response to unblock the interaction
        await interaction.followup.send("Generating GSC report with visualizations...")

        # Send the full report with charts to the channel
        await send_report_with_charts(interaction.channel, current_data, previous_data)

        # Update historical data for trend analysis
        await update_historical_data(current_data)

    except Exception as e:
        logger.error(f"Error handling check_now command: {e}")
        await interaction.followup.send(
            embed=Embed(
                title="⚠️ GSC Report Error",
                description=f"Failed to generate GSC report: {str(e)}",
                color=Color.red(),
            )
        )


# Command to show long-term trends from historical data
@tree.command(
    name="trends",
    description="Get a 30-day performance trend report",
    guild=discord.Object(id=GUILD_ID),
)
async def trends(interaction: discord.Interaction):
    # Check if command is used in the correct channel
    if interaction.channel_id != COMMANDS_CHANNEL_ID:
        await interaction.response.send_message(
            f"⚠️ This command can only be used in the designated commands channel.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        # Load historical data
        historical_data = []
        if os.path.exists(HISTORICAL_DATA_FILE):
            with open(HISTORICAL_DATA_FILE, "r") as f:
                historical_data = json.load(f)

        if not historical_data or len(historical_data) < 2:
            await interaction.followup.send(
                "Not enough historical data available yet. Please try again later."
            )
            return

        # Create trend embed
        trend_embed = Embed(
            title="📈 PCWStats Performance Trends",
            description=f"Data from last {len(historical_data)} days",
            color=Color.blue(),
        )

        # Add metrics
        latest = historical_data[-1]
        oldest = historical_data[0]

        # Calculate percent changes
        click_change = latest["clicks"] - oldest["clicks"]
        click_pct = (
            (click_change / oldest["clicks"] * 100) if oldest["clicks"] > 0 else 0
        )

        imp_change = latest["impressions"] - oldest["impressions"]
        imp_pct = (
            (imp_change / oldest["impressions"] * 100)
            if oldest["impressions"] > 0
            else 0
        )

        trend_embed.add_field(
            name="Clicks Trend",
            value=f"{oldest['clicks']} → {latest['clicks']} ({click_change:+} / {click_pct:+.1f}%)",
            inline=True,
        )

        trend_embed.add_field(
            name="Impressions Trend",
            value=f"{oldest['impressions']} → {latest['impressions']} ({imp_change:+} / {imp_pct:+.1f}%)",
            inline=True,
        )

        trend_embed.add_field(
            name="CTR Trend",
            value=f"{oldest['ctr']:.2f}% → {latest['ctr']:.2f}% ({latest['ctr'] - oldest['ctr']:+.2f}%)",
            inline=True,
        )

        trend_embed.add_field(
            name="Position Trend",
            value=f"{oldest['position']:.1f} → {latest['position']:.1f} ({oldest['position'] - latest['position']:+.1f})",
            inline=True,
        )

        await interaction.followup.send(embed=trend_embed)

        # Create and send charts
        chart_files = []

        # Plot clicks trend
        plt.figure(figsize=(10, 5))
        dates = [item["date"][5:] for item in historical_data]  # Format: MM-DD
        clicks = [item["clicks"] for item in historical_data]
        plt.plot(dates, clicks, marker="o", color="blue")
        plt.title("Clicks (30-Day Trend)")
        plt.xlabel("Date")
        plt.ylabel("Clicks")
        plt.xticks(rotation=45)
        plt.tight_layout()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            plt.savefig(tmp.name)
            plt.close()
            chart_files.append(("clicks_trend_30day.png", tmp.name))

        # Plot impressions trend
        plt.figure(figsize=(10, 5))
        impressions = [item["impressions"] for item in historical_data]
        plt.plot(dates, impressions, marker="o", color="orange")
        plt.title("Impressions (30-Day Trend)")
        plt.xlabel("Date")
        plt.ylabel("Impressions")
        plt.xticks(rotation=45)
        plt.tight_layout()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            plt.savefig(tmp.name)
            plt.close()
            chart_files.append(("impressions_trend_30day.png", tmp.name))

        # Send charts
        for i, (filename, filepath) in enumerate(chart_files):
            chart_embed = Embed(
                title=f"📊 {filename.replace('_', ' ').replace('.png', '').title()}"
            )
            chart_embed.set_image(url=f"attachment://{filename}")
            await interaction.channel.send(
                embed=chart_embed, file=File(filepath, filename=filename)
            )

        # Clean up temporary files
        for _, file_path in chart_files:
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error deleting temporary file {file_path}: {e}")

    except Exception as e:
        logger.error(f"Error generating trends report: {e}")
        await interaction.followup.send(
            embed=Embed(
                title="⚠️ Trends Report Error",
                description=f"Failed to generate trends report: {str(e)}",
                color=Color.red(),
            )
        )


# Command to show top performing content with optimization suggestions
@tree.command(
    name="topperformers",
    description="Get the top performing content for optimization",
    guild=discord.Object(id=GUILD_ID),
)
async def top_performers(interaction: discord.Interaction):
    # Check if command is used in the correct channel
    if interaction.channel_id != COMMANDS_CHANNEL_ID:
        await interaction.response.send_message(
            f"⚠️ This command can only be used in the designated commands channel.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        # Get GSC service
        service = await get_gsc_service()

        # Get data for last 30 days for better analysis
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Get top pages with position between 4-20 (high potential for improvement)
        potential_pages = (
            service.searchanalytics()
            .query(
                siteUrl=GSC_SITE_URL,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["page"],
                    "rowLimit": 100,
                },
            )
            .execute()
        )

        # Filter pages with position between 4-20
        opportunity_pages = []
        if potential_pages.get("rows"):
            for page in potential_pages["rows"]:
                if 4 <= page["position"] <= 20:
                    opportunity_pages.append(page)

        # Sort by impressions (highest potential traffic)
        opportunity_pages.sort(key=lambda x: x["impressions"], reverse=True)

        # Create embed
        opportunity_embed = Embed(
            title="🚀 Optimization Opportunities",
            description="Pages with high potential for improvement",
            color=Color.gold(),
        )

        if opportunity_pages:
            content = ""
            for i, page in enumerate(opportunity_pages[:8], 1):
                page_path = page["keys"][0].replace(GSC_SITE_URL, "/")
                content += f"**{i}. {page_path}**\n"
                content += f"   Position: {page['position']:.1f} | Impressions: {int(page['impressions']):,} | CTR: {(page['ctr'] * 100):.1f}%\n"

                # Add optimization suggestions
                if page["position"] >= 10:
                    content += f"   *Suggestion: Consider adding more comprehensive content to improve ranking*\n\n"
                elif page["ctr"] * 100 < 2:
                    content += f"   *Suggestion: Improve meta title/description to increase CTR*\n\n"
                else:
                    content += f"   *Suggestion: Add more related keywords to capture additional traffic*\n\n"

            opportunity_embed.description = content
        else:
            opportunity_embed.description = "No optimization opportunities found"

        await interaction.followup.send(embed=opportunity_embed)

    except Exception as e:
        logger.error(f"Error generating top performers report: {e}")
        await interaction.followup.send(
            embed=Embed(
                title="⚠️ Report Error",
                description=f"Failed to generate top performers report: {str(e)}",
                color=Color.red(),
            )
        )


# Command to display help information
@tree.command(
    name="help",
    description="Get help with GSC bot commands",
    guild=discord.Object(id=GUILD_ID),
)
async def help_command(interaction: discord.Interaction):
    help_embed = Embed(
        title="🤖 GSC Monitor Commands",
        description="Here are the available commands for the GSC Monitor",
        color=Color.blue(),
    )

    help_embed.add_field(
        name="/checknow",
        value="Get an immediate Google Search Console report with detailed metrics and visualizations",
        inline=False,
    )

    help_embed.add_field(
        name="/trends",
        value="View 30-day performance trends for PCWStats",
        inline=False,
    )

    help_embed.add_field(
        name="/topperformers",
        value="Identify pages with high potential for optimization",
        inline=False,
    )

    help_embed.add_field(name="/help", value="Display this help message", inline=False)

    help_embed.add_field(
        name="Scheduled Reports",
        value="The bot automatically posts reports every day at 12:00 UTC",
        inline=False,
    )

    await interaction.response.send_message(embed=help_embed)


# Event triggered when the bot is ready
@client.event
async def on_ready():
    logger.info(f"Bot logged in as {client.user}")

    # Set custom status for the bot
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Google Search Console"
        )
    )

    # Sync the command tree with Discord
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    logger.info("Command tree synced")

    # Send initial report immediately
    await send_daily_report()

    # Start the daily scheduler
    await client.loop.create_task(schedule_daily_report())


# Main function to start the bot
def main():
    logger.info("Starting GSC Discord Bot")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
