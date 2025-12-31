import json
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import matplotlib
import numpy as np
import pandas as pd
from pathlib import Path

# Config

JSON_FILE_PATH = "../../HEAT-Labs-Configs/cf-data.json"
OUTPUT_FOLDER = "output/cf-traffic-charts"
HEAT_PRIMARY = "#ff8300"
HEAT_SECONDARY = "#333333"
HEAT_TERTIARY = "#666666"
HEAT_BACKGROUND = "#f8f8f8"


# Convert bytes to gigabytes
def bytes_to_gb(bytes_value):
    return bytes_value / (1024**3)


# Create directory structure for today's charts
def create_output_directory():
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(OUTPUT_FOLDER) / today
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# Load JSON data and process it for visualization
def load_and_process_data(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    # Convert daily data to DataFrame
    daily_data = data["daily_data"]
    df = pd.DataFrame(daily_data)

    # Convert bytes to GB
    df["total_data_served_gb"] = df["total_data_served"].apply(bytes_to_gb)
    df["data_cached_gb"] = df["data_cached"].apply(bytes_to_gb)

    # Calculate cache ratio
    df["cache_ratio"] = (df["data_cached"] / df["total_data_served"] * 100).fillna(0)

    # Convert date string to datetime
    df["date"] = pd.to_datetime(df["date_iso"])

    # Sort by date and keep only last 30 days
    df = df.sort_values("date")
    df = df.tail(30)

    # Calculate daily averages for metrics
    daily_metrics = {
        "avg_data_served": df["total_data_served_gb"].mean(),
        "avg_data_cached": df["data_cached_gb"].mean(),
        "avg_requests": df["total_requests"].mean(),
        "avg_visitors": df["unique_visitors"].mean(),
        "avg_cache_ratio": df["cache_ratio"].mean(),
    }

    return df, data["totals"], daily_metrics


# Create traffic overview chart
def create_traffic_overview_chart(df, output_dir):
    fig, ax = plt.subplots(figsize=(14, 8))

    # Set background color
    fig.patch.set_facecolor(HEAT_BACKGROUND)
    ax.set_facecolor(HEAT_BACKGROUND)

    # Plot data served
    bars1 = ax.bar(
        df["date"],
        df["total_data_served_gb"],
        color=HEAT_PRIMARY,
        alpha=0.8,
        label="Data Served",
        width=0.8,
    )

    # Plot cached data on top
    bars2 = ax.bar(
        df["date"],
        df["data_cached_gb"],
        color=HEAT_SECONDARY,
        alpha=0.7,
        label="Cached Data",
        width=0.8,
    )

    # Formatting
    ax.set_title(
        "HEAT Labs - Daily Traffic Overview",
        fontsize=16,
        fontweight="bold",
        pad=20,
        color=HEAT_SECONDARY,
    )
    ax.set_xlabel("Date", fontsize=12, color=HEAT_SECONDARY)
    ax.set_ylabel("Data Volume (GB)", fontsize=12, color=HEAT_SECONDARY)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45, ha="right")

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--")

    # Add legend on the right
    ax.legend(loc="upper right", fontsize=10)

    # Add total served text
    total_served = df["total_data_served_gb"].sum()
    total_cached = df["data_cached_gb"].sum()
    cache_ratio = (total_cached / total_served * 100) if total_served > 0 else 0

    text_str = f"Total Served: {total_served:.2f} GB\nTotal Cached: {total_cached:.2f} GB\nCache Ratio: {cache_ratio:.1f}%"
    ax.text(
        0.02,
        0.98,
        text_str,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    plt.tight_layout()
    plt.savefig(output_dir / "traffic_overview.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create cache ratio chart
def create_cache_ratio_chart(df, output_dir):
    fig, ax = plt.subplots(figsize=(14, 7))

    # Set background color
    fig.patch.set_facecolor(HEAT_BACKGROUND)
    ax.set_facecolor(HEAT_BACKGROUND)

    # Create line for cache ratio
    (line,) = ax.plot(
        df["date"],
        df["cache_ratio"],
        color=HEAT_PRIMARY,
        linewidth=3,
        marker="o",
        markersize=5,
        label="Cache Ratio",
    )

    # Fill under the line
    ax.fill_between(df["date"], df["cache_ratio"], color=HEAT_PRIMARY, alpha=0.2)

    # Add average line
    avg_ratio = df["cache_ratio"].mean()
    ax.axhline(
        y=avg_ratio,
        color=HEAT_SECONDARY,
        linestyle="--",
        alpha=0.7,
        label=f"Average: {avg_ratio:.1f}%",
    )

    # Formatting
    ax.set_title(
        "HEAT Labs - Daily Cache Ratio",
        fontsize=16,
        fontweight="bold",
        pad=20,
        color=HEAT_SECONDARY,
    )
    ax.set_xlabel("Date", fontsize=12, color=HEAT_SECONDARY)
    ax.set_ylabel("Cache Ratio (%)", fontsize=12, color=HEAT_SECONDARY)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45, ha="right")

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--")

    # Set y-axis limits
    ax.set_ylim(bottom=0)

    # Add legend on the right
    ax.legend(loc="upper right", fontsize=10)

    # Add annotation for highest cache ratio
    max_idx = df["cache_ratio"].idxmax()
    max_date = df.loc[max_idx, "date"]
    max_ratio = df.loc[max_idx, "cache_ratio"]
    ax.annotate(
        f"Max: {max_ratio:.1f}%",
        xy=(max_date, max_ratio),
        xytext=(10, 10),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color=HEAT_SECONDARY),
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    plt.tight_layout()
    plt.savefig(output_dir / "cache_ratio.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create requests and visitors chart
def create_requests_visitors_chart(df, output_dir):
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Set background color
    fig.patch.set_facecolor(HEAT_BACKGROUND)
    ax1.set_facecolor(HEAT_BACKGROUND)

    # Plot requests (primary y-axis)
    ax1.bar(
        df["date"],
        df["total_requests"],
        color=HEAT_PRIMARY,
        alpha=0.7,
        label="Total Requests",
        width=0.8,
    )

    ax1.set_xlabel("Date", fontsize=12, color=HEAT_SECONDARY)
    ax1.set_ylabel("Total Requests", fontsize=12, color=HEAT_SECONDARY)

    # Create secondary y-axis
    ax2 = ax1.twinx()
    ax2.plot(
        df["date"],
        df["unique_visitors"],
        color=HEAT_SECONDARY,
        linewidth=3,
        marker="s",
        markersize=5,
        label="Unique Visitors",
    )

    ax2.set_ylabel("Unique Visitors", fontsize=12, color=HEAT_SECONDARY)

    # Formatting
    ax1.set_title(
        "HEAT Labs - Requests vs Unique Visitors",
        fontsize=16,
        fontweight="bold",
        pad=20,
        color=HEAT_SECONDARY,
    )

    # Format x-axis dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.xticks(rotation=45, ha="right")

    # Add grid
    ax1.grid(True, alpha=0.3, linestyle="--")

    # Combine legends and place on the right
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=10)

    # Add totals
    total_requests = df["total_requests"].sum()
    total_visitors = df["unique_visitors"].sum()

    text_str = f"Total Requests: {total_requests:,}\nTotal Visitors: {total_visitors:,}"
    ax1.text(
        0.02,
        0.98,
        text_str,
        transform=ax1.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    plt.tight_layout()
    plt.savefig(output_dir / "requests_visitors.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create summary dashboard with key metrics
def create_summary_chart(df, totals, daily_metrics, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Set overall background
    fig.patch.set_facecolor(HEAT_BACKGROUND)

    # Chart 1: Monthly totals (pie chart)
    labels = ["Data Served", "Data Cached", "Missed Cache"]
    served_gb = totals["all_time"]["data_served_gb"]
    cached_gb = totals["all_time"]["data_cached_gb"]
    missed_gb = served_gb - cached_gb
    sizes = [served_gb, cached_gb, missed_gb]
    colors = [HEAT_PRIMARY, HEAT_SECONDARY, HEAT_TERTIARY]

    axes[0].pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 10},
    )
    axes[0].set_title(
        "Data Distribution (GB)", fontsize=14, fontweight="bold", color=HEAT_SECONDARY
    )

    # Chart 2: Key metrics comparison
    metrics = ["Avg Data Served", "Avg Data Cached", "Avg Requests", "Avg Visitors"]
    values = [
        daily_metrics["avg_data_served"],
        daily_metrics["avg_data_cached"],
        daily_metrics["avg_requests"],
        daily_metrics["avg_visitors"],
    ]

    bars = axes[1].bar(metrics, values, color=HEAT_PRIMARY, alpha=0.8)
    axes[1].set_title(
        "Daily Averages", fontsize=14, fontweight="bold", color=HEAT_SECONDARY
    )
    axes[1].tick_params(axis="x", rotation=15)

    # Add value labels on bars
    for bar, value in zip(bars, values):
        if metrics[bars.index(bar)] in ["Avg Data Served", "Avg Data Cached"]:
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        else:
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{value:.0f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    # Chart 3: Cache ratio distribution
    cache_bins = np.arange(0, 101, 20)
    axes[2].hist(
        df["cache_ratio"],
        bins=cache_bins,
        color=HEAT_PRIMARY,
        alpha=0.7,
        edgecolor="white",
    )
    axes[2].set_xlabel("Cache Ratio (%)", fontsize=11, color=HEAT_SECONDARY)
    axes[2].set_ylabel("Frequency (Days)", fontsize=11, color=HEAT_SECONDARY)
    axes[2].set_title(
        "Cache Ratio Distribution", fontsize=14, fontweight="bold", color=HEAT_SECONDARY
    )
    axes[2].grid(True, alpha=0.3, linestyle="--")

    # Chart 4: Peak day analysis
    peak_data_day = df.loc[df["total_data_served_gb"].idxmax()]
    peak_requests_day = df.loc[df["total_requests"].idxmax()]
    peak_visitors_day = df.loc[df["unique_visitors"].idxmax()]

    peak_data = [
        peak_data_day["date_iso"],
        f"{peak_data_day['total_data_served_gb']:.2f} GB",
        f"{peak_data_day['cache_ratio']:.1f}%",
    ]
    peak_requests = [
        peak_requests_day["date_iso"],
        f"{peak_requests_day['total_requests']:,}",
        f"{peak_requests_day['unique_visitors']:,}",
    ]
    peak_visitors = [
        peak_visitors_day["date_iso"],
        f"{peak_visitors_day['unique_visitors']:,}",
        f"{peak_visitors_day['total_requests']:,}",
    ]

    # Create a table
    table_data = [
        ["Metric", "Date", "Value 1", "Value 2"],
        ["Peak Data", peak_data[0], peak_data[1], peak_data[2]],
        ["Peak Requests", peak_requests[0], peak_requests[1], peak_requests[2]],
        ["Peak Visitors", peak_visitors[0], peak_visitors[1], peak_visitors[2]],
    ]

    axes[3].axis("off")
    table = axes[3].table(cellText=table_data, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style the table
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            if i == 0:  # Header row
                table[(i, j)].set_facecolor(HEAT_PRIMARY)
                table[(i, j)].set_text_props(weight="bold", color="white")
            else:
                table[(i, j)].set_facecolor(HEAT_BACKGROUND)

    axes[3].set_title(
        "Peak Performance Days",
        fontsize=14,
        fontweight="bold",
        color=HEAT_SECONDARY,
        pad=20,
    )

    # Add branding
    fig.suptitle(
        "HEAT Labs - Cloudflare Analytics Dashboard",
        fontsize=18,
        fontweight="bold",
        color=HEAT_SECONDARY,
        y=1.02,
    )

    plt.tight_layout()
    plt.savefig(output_dir / "summary_dashboard.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    try:
        # Load and process data
        df, totals, daily_metrics = load_and_process_data(JSON_FILE_PATH)

        # Create output directory for today
        output_dir = create_output_directory()

        # Create all charts
        print("Creating Traffic Overview chart...")
        create_traffic_overview_chart(df, output_dir)

        print("Creating Cache Ratio chart...")
        create_cache_ratio_chart(df, output_dir)

        print("Creating Requests vs Visitors chart...")
        create_requests_visitors_chart(df, output_dir)

        print("Creating Summary Dashboard...")
        create_summary_chart(df, totals, daily_metrics, output_dir)

        print("All charts generated successfully!")

    except FileNotFoundError:
        print(f"Error: JSON file not found at {JSON_FILE_PATH}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {JSON_FILE_PATH}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
