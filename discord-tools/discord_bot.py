import os
import json
import asyncio
import logging
import tempfile
import asyncio
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt

import discord
from discord import app_commands, Embed, Color, File
from discord.ext import tasks

from config import (
    DISCORD_TOKEN,
    GUILD_ID,
    UPDATES_CHANNEL_ID,
    COMMANDS_CHANNEL_ID,
    GSC_SITE_URL,
    HISTORICAL_DATA_FILE,
    CACHE_FILE,
)
from gsc_service import (
    get_gsc_service,
    fetch_search_analytics,
    load_cached_data,
    save_cached_data,
    update_historical_data,
)
from data_processing import (
    generate_report_embeds,
    create_combined_trend_chart,
    create_device_chart,
)

logger = logging.getLogger("gsc_discord_bot.discord_bot")

# Create Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


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


async def send_daily_report():
    logger.info("Running daily GSC report")

    updates_channel = client.get_channel(UPDATES_CHANNEL_ID)
    if not updates_channel:
        logger.error(f"Could not find updates channel with ID {UPDATES_CHANNEL_ID}")
        return

    try:
        # Get GSC service - this may require authentication
        try:
            service = await get_gsc_service()
            if service is None:
                await updates_channel.send(
                    embed=Embed(
                        title="⚠️ GSC Authentication Required",
                        description="Please use the `/auth` command with your Google OAuth code to authenticate.\n\n"
                        "1. Visit the auth URL printed in the logs\n"
                        "2. Approve the permissions\n"
                        "3. Copy the code from the redirect URL\n"
                        "4. Use `/auth <code>` in this channel",
                        color=Color.orange(),
                    )
                )
                return
        except Exception as auth_error:
            logger.error(f"GSC authentication error: {auth_error}")
            await updates_channel.send(
                embed=Embed(
                    title="⚠️ GSC Authentication Error",
                    description=f"Failed to authenticate with Google Search Console: {str(auth_error)}\n\n"
                    "Please check the logs and try authenticating again with `/auth`.",
                    color=Color.red(),
                )
            )
            return

        # Get current data
        current_data = await fetch_search_analytics(service)
        if not current_data:
            await updates_channel.send(
                embed=Embed(
                    title="⚠️ GSC Data Error",
                    description="No data available from Google Search Console.",
                    color=Color.red(),
                )
            )
            return

        # Get previous data for comparison
        previous_data = await load_cached_data()

        # Send the report to Discord with charts
        await send_report_with_charts(updates_channel, current_data, previous_data)

        # Update historical data for trend analysis
        await update_historical_data(current_data)

        # Save current data for next comparison
        await save_cached_data(current_data)

        logger.info("Daily report completed successfully")

    except Exception as e:
        logger.error(f"Error in daily report: {e}", exc_info=True)
        error_embed = Embed(
            title="⚠️ GSC Report Error",
            description=f"An error occurred while generating the daily report: {str(e)}",
            color=Color.red(),
        )

        # More specific troubleshooting for common issues
        if "quota" in str(e).lower():
            error_embed.add_field(
                name="Possible Solution",
                value="Google API quota may be exceeded. Try again later.",
                inline=False,
            )
        elif "token" in str(e).lower() or "credentials" in str(e).lower():
            error_embed.add_field(
                name="Possible Solution",
                value="Authentication may have expired. Try re-authenticating with `/auth`.",
                inline=False,
            )

        await updates_channel.send(embed=error_embed)


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


@tree.command(
    name="auth",
    description="Provide Google OAuth authorization code",
    guild=discord.Object(id=GUILD_ID),
)
async def auth_command(interaction: discord.Interaction, code: str):
    from gsc_service import AUTH_CODE

    # Check if command is used in the correct channel
    if interaction.channel_id != COMMANDS_CHANNEL_ID:
        await interaction.response.send_message(
            f"⚠️ This command can only be used in the designated commands channel.",
            ephemeral=True,
        )
        return

    # Set the auth code globally
    global AUTH_CODE
    AUTH_CODE = code.strip()

    await interaction.response.send_message(
        "✅ Authorization code received. Processing authentication...", ephemeral=True
    )


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

    try:
        # Send initial report immediately
        await send_daily_report()
    except Exception as e:
        logger.error(f"Initial report failed: {e}")

    # Start the daily scheduler
    await client.loop.create_task(schedule_daily_report())
