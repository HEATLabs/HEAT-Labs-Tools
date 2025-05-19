import tempfile
import matplotlib.pyplot as plt
from datetime import datetime
from discord import Embed, Color, File
from config import COUNTRY_CODES, GSC_SITE_URL


def country_name_from_code(code):
    return COUNTRY_CODES.get(code.lower(), code)


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
