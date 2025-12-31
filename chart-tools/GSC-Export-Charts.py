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
JSON_FILE_PATH = "../../HEAT-Labs-Configs/gsc_data.json"
OUTPUT_FOLDER = "output/gsc-export-charts"
HEAT_PRIMARY = "#ff8300"
HEAT_SECONDARY = "#333333"
HEAT_TERTIARY = "#666666"
HEAT_BACKGROUND = "#f8f8f8"


# Convert "N/A" strings to NaN
def convert_na_to_nan(value):
    if isinstance(value, str) and value == "N/A":
        return np.nan
    return value


# Create directory structure for today's charts
def create_output_directory():
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(OUTPUT_FOLDER) / today
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# Load and process JSON data
def load_and_process_data(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    # Convert to DataFrame
    rows = []
    for date_str, metrics in data.items():
        row = {
            "date": date_str,
            "date_dt": datetime.strptime(date_str, "%Y-%m-%d"),
            "indexed": convert_na_to_nan(metrics["coverage"]["indexed"]),
            "not_indexed": convert_na_to_nan(metrics["coverage"]["not_indexed"]),
            "impressions": convert_na_to_nan(metrics["coverage"]["impressions"]),
            "valid_breadcrumbs": convert_na_to_nan(metrics["breadcrumbs"]["valid"]),
            "invalid_breadcrumbs": convert_na_to_nan(metrics["breadcrumbs"]["invalid"]),
            "https_urls": convert_na_to_nan(metrics["https"]["https_urls"]),
            "non_https_urls": convert_na_to_nan(metrics["https"]["non_https_urls"]),
            "video_indexed": convert_na_to_nan(
                metrics["video_indexing"]["video_indexed"]
            ),
            "no_video_indexed": convert_na_to_nan(
                metrics["video_indexing"]["no_video_indexed"]
            ),
            "video_impressions": convert_na_to_nan(
                metrics["video_indexing"]["impressions"]
            ),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("date_dt")

    # Calculate derived metrics
    df["total_pages"] = df["indexed"] + df["not_indexed"]
    df["indexing_ratio"] = (df["indexed"] / df["total_pages"] * 100).replace(
        [np.inf, -np.inf], np.nan
    )
    df["breadcrumb_ratio"] = (
        df["valid_breadcrumbs"]
        / (df["valid_breadcrumbs"] + df["invalid_breadcrumbs"])
        * 100
    ).replace([np.inf, -np.inf], np.nan)
    df["https_ratio"] = (
        df["https_urls"] / (df["https_urls"] + df["non_https_urls"]) * 100
    ).replace([np.inf, -np.inf], np.nan)

    # Calculate rolling averages (7-day)
    for col in [
        "indexed",
        "not_indexed",
        "impressions",
        "valid_breadcrumbs",
        "https_urls",
    ]:
        df[f"{col}_7d_avg"] = df[col].rolling(window=7, min_periods=1).mean()

    # Calculate daily changes
    df["indexed_change"] = df["indexed"].diff()
    df["impressions_change"] = df["impressions"].diff()

    # Keep only last 30 days
    if len(df) > 30:
        df = df.tail(30)

    # Calculate summary statistics
    summary_stats = {
        "total_indexed": df["indexed"].max(),
        "total_not_indexed": df["not_indexed"].max(),
        "avg_impressions": df["impressions"].mean(),
        "max_impressions": df["impressions"].max(),
        "avg_indexing_ratio": df["indexing_ratio"].mean(),
        "avg_breadcrumb_ratio": df["breadcrumb_ratio"].mean(),
        "avg_https_ratio": df["https_ratio"].mean(),
        "total_valid_breadcrumbs": df["valid_breadcrumbs"].max(),
        "total_https_urls": df["https_urls"].max(),
        "total_video_indexed": df["video_indexed"].max()
        if not pd.isna(df["video_indexed"].max())
        else 0,
        "period_start": df["date"].iloc[0],
        "period_end": df["date"].iloc[-1],
        "period_days": len(df),
    }

    return df, summary_stats


# Create indexing coverage overview chart
def create_indexing_chart(df, output_dir):
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Set background color
    fig.patch.set_facecolor(HEAT_BACKGROUND)
    ax1.set_facecolor(HEAT_BACKGROUND)

    # Plot indexed pages (primary y-axis)
    bars1 = ax1.bar(
        df["date_dt"],
        df["indexed"],
        color=HEAT_PRIMARY,
        alpha=0.8,
        label="Indexed Pages",
        width=0.8,
    )

    # Plot not indexed pages on top
    bars2 = ax1.bar(
        df["date_dt"],
        df["not_indexed"],
        bottom=df["indexed"],
        color=HEAT_SECONDARY,
        alpha=0.6,
        label="Not Indexed",
        width=0.8,
    )

    # Create secondary y-axis for indexing ratio
    ax2 = ax1.twinx()
    ax2.plot(
        df["date_dt"],
        df["indexing_ratio"],
        color=HEAT_TERTIARY,
        linewidth=3,
        marker="o",
        markersize=4,
        label="Indexing Ratio %",
    )

    # Formatting
    period_start = df["date"].iloc[0]
    period_end = df["date"].iloc[-1]
    ax1.set_title(
        f"HEAT Labs - GSC Indexing Coverage\n{period_start} to {period_end}",
        fontsize=16,
        fontweight="bold",
        pad=20,
        color=HEAT_SECONDARY,
    )
    ax1.set_xlabel("Date", fontsize=12, color=HEAT_SECONDARY)
    ax1.set_ylabel("Number of Pages", fontsize=12, color=HEAT_SECONDARY)
    ax2.set_ylabel("Indexing Ratio (%)", fontsize=12, color=HEAT_TERTIARY)
    ax2.set_ylim(0, 100)

    # Format x-axis dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    # Show fewer x-ticks for better readability
    if len(df) > 15:
        step = 3
    else:
        step = 2
    plt.xticks(df["date_dt"][::step], rotation=45, ha="right")

    # Add grid
    ax1.grid(True, alpha=0.3, linestyle="--")

    # Combine legends and place on the right
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=10)

    # Add summary text
    current_indexing = (
        df["indexing_ratio"].iloc[-1]
        if not pd.isna(df["indexing_ratio"].iloc[-1])
        else 0
    )
    avg_indexing = df["indexing_ratio"].mean()

    text_str = f"Current Indexing: {current_indexing:.1f}%\n30-Day Average: {avg_indexing:.1f}%\nTotal Pages: {df['total_pages'].iloc[-1]:.0f}"
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
    plt.savefig(output_dir / "indexing_coverage.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create impressions and trends chart
def create_impressions_chart(df, output_dir):
    fig, ax = plt.subplots(figsize=(14, 7))

    # Set background color
    fig.patch.set_facecolor(HEAT_BACKGROUND)
    ax.set_facecolor(HEAT_BACKGROUND)

    # Create line for impressions
    (line,) = ax.plot(
        df["date_dt"],
        df["impressions"],
        color=HEAT_PRIMARY,
        linewidth=3,
        marker="o",
        markersize=5,
        label="Daily Impressions",
    )

    # Fill under the line
    ax.fill_between(df["date_dt"], df["impressions"], color=HEAT_PRIMARY, alpha=0.2)

    # Add 7-day moving average
    ax.plot(
        df["date_dt"],
        df["impressions_7d_avg"],
        color=HEAT_SECONDARY,
        linestyle="--",
        linewidth=2,
        label="7-Day Average",
    )

    # Add 30-day average line
    avg_impressions = df["impressions"].mean()
    ax.axhline(
        y=avg_impressions,
        color=HEAT_TERTIARY,
        linestyle=":",
        alpha=0.7,
        label=f"30-Day Average: {avg_impressions:.1f}",
    )

    # Formatting
    period_start = df["date"].iloc[0]
    period_end = df["date"].iloc[-1]
    ax.set_title(
        f"HEAT Labs - Search Impressions Trend\n{period_start} to {period_end}",
        fontsize=16,
        fontweight="bold",
        pad=20,
        color=HEAT_SECONDARY,
    )
    ax.set_xlabel("Date", fontsize=12, color=HEAT_SECONDARY)
    ax.set_ylabel("Impressions", fontsize=12, color=HEAT_SECONDARY)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    # Show fewer x-ticks for better readability
    if len(df) > 15:
        step = 3
    else:
        step = 2
    plt.xticks(df["date_dt"][::step], rotation=45, ha="right")

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--")

    # Set y-axis limits
    ax.set_ylim(bottom=0)

    # Add legend on the right
    ax.legend(loc="upper right", fontsize=10)

    # Add annotation for highest impressions
    max_idx = df["impressions"].idxmax()
    if not pd.isna(max_idx):
        max_date = df.loc[max_idx, "date_dt"]
        max_impressions = df.loc[max_idx, "impressions"]
        ax.annotate(
            f"Peak: {max_impressions:.0f}",
            xy=(max_date, max_impressions),
            xytext=(10, 10),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color=HEAT_SECONDARY),
            fontsize=9,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        )

    # Add 30-day growth metrics
    if len(df) > 1:
        first_imp = df["impressions"].iloc[0]
        last_imp = df["impressions"].iloc[-1]
        if not pd.isna(first_imp) and not pd.isna(last_imp) and first_imp > 0:
            growth_pct = ((last_imp - first_imp) / first_imp) * 100
            growth_text = f"30-Day Change: {growth_pct:+.1f}%"
        else:
            growth_text = "30-Day Change: N/A"

        ax.text(
            0.02,
            0.02,
            growth_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        )

    plt.tight_layout()
    plt.savefig(output_dir / "impressions_trend.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create technical SEO metrics chart
def create_technical_seo_chart(df, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()

    # Set overall background
    fig.patch.set_facecolor(HEAT_BACKGROUND)

    # Chart 1: HTTPS Implementation Progress
    (line1,) = axes[0].plot(
        df["date_dt"],
        df["https_urls"],
        color="#4CAF50",
        linewidth=2.5,
        marker="s",
        markersize=4,
        label="HTTPS URLs",
    )
    axes[0].fill_between(df["date_dt"], df["https_urls"], color="#4CAF50", alpha=0.2)
    axes[0].set_title(
        "HTTPS Implementation",
        fontsize=12,
        fontweight="bold",
        color=HEAT_SECONDARY,
    )
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("HTTPS URLs")
    axes[0].grid(True, alpha=0.3, linestyle="--")
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    # Show fewer x-ticks
    if len(df) > 15:
        step = 3
    else:
        step = 2
    axes[0].set_xticks(df["date_dt"][::step])
    axes[0].tick_params(axis="x", rotation=45)

    # Add current value and 30-day change
    current_https = (
        df["https_urls"].iloc[-1] if not pd.isna(df["https_urls"].iloc[-1]) else 0
    )
    first_https = (
        df["https_urls"].iloc[0] if not pd.isna(df["https_urls"].iloc[0]) else 0
    )
    https_change = current_https - first_https

    axes[0].text(
        0.05,
        0.95,
        f"Current: {current_https:.0f}\nChange: {https_change:+.0f}",
        transform=axes[0].transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # Chart 2: Breadcrumb Progress
    (line2,) = axes[1].plot(
        df["date_dt"],
        df["valid_breadcrumbs"],
        color="#2196F3",
        linewidth=2.5,
        marker="^",
        markersize=4,
        label="Valid Breadcrumbs",
    )
    axes[1].fill_between(
        df["date_dt"], df["valid_breadcrumbs"], color="#2196F3", alpha=0.2
    )
    axes[1].set_title(
        "Breadcrumb Implementation",
        fontsize=12,
        fontweight="bold",
        color=HEAT_SECONDARY,
    )
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Valid Breadcrumbs")
    axes[1].grid(True, alpha=0.3, linestyle="--")
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    axes[1].set_xticks(df["date_dt"][::step])
    axes[1].tick_params(axis="x", rotation=45)

    # Add current value and 30-day change
    current_breadcrumbs = (
        df["valid_breadcrumbs"].iloc[-1]
        if not pd.isna(df["valid_breadcrumbs"].iloc[-1])
        else 0
    )
    first_breadcrumbs = (
        df["valid_breadcrumbs"].iloc[0]
        if not pd.isna(df["valid_breadcrumbs"].iloc[0])
        else 0
    )
    breadcrumb_change = current_breadcrumbs - first_breadcrumbs

    axes[1].text(
        0.05,
        0.95,
        f"Current: {current_breadcrumbs:.0f}\nChange: {breadcrumb_change:+.0f}",
        transform=axes[1].transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # Chart 3: Video Indexing
    if not df["video_indexed"].isna().all() and df["video_indexed"].max() > 0:
        axes[2].bar(
            df["date_dt"],
            df["video_indexed"],
            color="#9C27B0",
            alpha=0.7,
            label="Video Indexed",
            width=0.8,
        )
        axes[2].set_title(
            "Video Indexing",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )
        axes[2].set_xlabel("Date")
        axes[2].set_ylabel("Videos Indexed")
        axes[2].grid(True, alpha=0.3, linestyle="--")
        axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        axes[2].set_xticks(df["date_dt"][::step])
        axes[2].tick_params(axis="x", rotation=45)

        # Add total and 30-day change
        current_videos = (
            df["video_indexed"].iloc[-1]
            if not pd.isna(df["video_indexed"].iloc[-1])
            else 0
        )
        first_videos = (
            df["video_indexed"].iloc[0]
            if not pd.isna(df["video_indexed"].iloc[0])
            else 0
        )
        video_change = current_videos - first_videos

        axes[2].text(
            0.05,
            0.95,
            f"Current: {current_videos:.0f}\nChange: {video_change:+.0f}",
            transform=axes[2].transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )
    else:
        axes[2].text(
            0.5,
            0.5,
            "No Video Indexing Data\n(Last 30 Days)",
            ha="center",
            va="center",
            fontsize=11,
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )
        axes[2].set_title(
            "Video Indexing",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )
        axes[2].axis("off")

    # Chart 4: Ratios Comparison
    last_7_days = df.tail(7)
    x = np.arange(len(last_7_days))
    width = 0.25

    # Only plot if we have valid data
    valid_indexing = ~last_7_days["indexing_ratio"].isna()
    valid_breadcrumb = ~last_7_days["breadcrumb_ratio"].isna()
    valid_https = ~last_7_days["https_ratio"].isna()

    if valid_indexing.any():
        axes[3].bar(
            x[valid_indexing] - width,
            last_7_days["indexing_ratio"][valid_indexing],
            width,
            label="Indexing Ratio",
            color=HEAT_PRIMARY,
            alpha=0.8,
        )
    if valid_breadcrumb.any():
        axes[3].bar(
            x[valid_breadcrumb],
            last_7_days["breadcrumb_ratio"][valid_breadcrumb],
            width,
            label="Breadcrumb Ratio",
            color="#2196F3",
            alpha=0.8,
        )
    if valid_https.any():
        axes[3].bar(
            x[valid_https] + width,
            last_7_days["https_ratio"][valid_https],
            width,
            label="HTTPS Ratio",
            color="#4CAF50",
            alpha=0.8,
        )

    axes[3].set_title(
        "SEO Ratios", fontsize=12, fontweight="bold", color=HEAT_SECONDARY
    )
    axes[3].set_xlabel("Date")
    axes[3].set_ylabel("Ratio (%)")
    axes[3].set_ylim(0, 100)
    axes[3].grid(True, alpha=0.3, linestyle="--", axis="y")

    # Set x-tick labels to dates
    date_labels = [d.strftime("%m-%d") for d in last_7_days["date_dt"]]
    axes[3].set_xticks(x)
    axes[3].set_xticklabels(date_labels, rotation=45)
    axes[3].legend(fontsize=9)

    # Add overall title
    period_start = df["date"].iloc[0]
    period_end = df["date"].iloc[-1]
    fig.suptitle(
        f"HEAT Labs - Technical SEO Progress\n{period_start} to {period_end}",
        fontsize=16,
        fontweight="bold",
        color=HEAT_SECONDARY,
        y=1.02,
    )

    plt.tight_layout()
    plt.savefig(output_dir / "technical_seo_metrics.png", dpi=150, bbox_inches="tight")
    plt.close()


# Create summary dashboard
def create_summary_dashboard(df, summary_stats, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Set overall background
    fig.patch.set_facecolor(HEAT_BACKGROUND)

    # Chart 1: Current Status Pie Chart
    labels = ["Indexed", "Not Indexed"]
    sizes = [summary_stats["total_indexed"], summary_stats["total_not_indexed"]]
    colors = ["#4CAF50", "#F44336"]

    # Only plot if we have data
    if not any(pd.isna(s) for s in sizes):
        axes[0].pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 10},
        )
        indexing_pct = (
            summary_stats["total_indexed"]
            / (summary_stats["total_indexed"] + summary_stats["total_not_indexed"])
        ) * 100
        axes[0].set_title(
            f"Indexing Status (30-Day Period)\n({indexing_pct:.1f}% Indexed)",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )
    else:
        axes[0].text(
            0.5,
            0.5,
            "No Indexing Data\n(Last 30 Days)",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )
        axes[0].set_title(
            "Indexing Status (30-Day Period)",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )

    # Chart 2: Impressions Distribution
    if not df["impressions"].isna().all():
        impression_bins = np.arange(0, df["impressions"].max() + 20, 20)
        axes[1].hist(
            df["impressions"].dropna(),
            bins=impression_bins,
            color=HEAT_PRIMARY,
            alpha=0.7,
            edgecolor="white",
        )
        axes[1].set_xlabel("Daily Impressions", fontsize=10, color=HEAT_SECONDARY)
        axes[1].set_ylabel("Frequency (Days)", fontsize=10, color=HEAT_SECONDARY)
        axes[1].set_title(
            "Impressions Distribution",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )
        axes[1].grid(True, alpha=0.3, linestyle="--")

        # Add statistics
        stats_text = f"30-Day Avg: {summary_stats['avg_impressions']:.1f}\n30-Day Max: {summary_stats['max_impressions']:.0f}"
        axes[1].text(
            0.95,
            0.95,
            stats_text,
            transform=axes[1].transAxes,
            fontsize=9,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )
    else:
        axes[1].text(
            0.5,
            0.5,
            "No Impressions Data\n(Last 30 Days)",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )
        axes[1].set_title(
            "Impressions Distribution",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )

    # Chart 3: 30-Day Average SEO Ratios
    metrics = ["Indexing Ratio", "Breadcrumb Ratio", "HTTPS Ratio"]
    values = [
        summary_stats["avg_indexing_ratio"],
        summary_stats["avg_breadcrumb_ratio"],
        summary_stats["avg_https_ratio"],
    ]

    # Filter out NaN values
    valid_metrics = []
    valid_values = []
    for metric, value in zip(metrics, values):
        if not pd.isna(value):
            valid_metrics.append(metric)
            valid_values.append(value)

    if valid_values:
        bars = axes[2].bar(
            valid_metrics,
            valid_values,
            color=[HEAT_PRIMARY, "#2196F3", "#4CAF50"],
            alpha=0.8,
        )
        axes[2].set_title(
            "30-Day Average SEO Ratios",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )
        axes[2].set_ylabel("Percentage (%)")

        # Set y-axis limit
        max_value = max(valid_values)
        y_max = min(110, max_value + (max_value * 0.1) + 5)
        axes[2].set_ylim(0, y_max)

        axes[2].grid(True, alpha=0.3, linestyle="--", axis="y")

        # Add value labels
        for bar, value in zip(bars, valid_values):
            if value > (y_max * 0.9):
                label_y = value - (y_max * 0.05)
                label_color = "white"
                label_fontweight = "bold"
            else:
                # Place label above the bar
                label_y = value + (y_max * 0.02)
                label_color = "black"
                label_fontweight = "bold"

            axes[2].text(
                bar.get_x() + bar.get_width() / 2,
                label_y,
                f"{value:.1f}%",
                ha="center",
                va="bottom" if label_color == "black" else "center",
                fontsize=9,
                fontweight=label_fontweight,
                color=label_color,
            )
        axes[2].set_ylim(0, y_max)
    else:
        axes[2].text(
            0.5,
            0.5,
            "No Ratio Data\n(Last 30 Days)",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.8),
        )
        axes[2].set_title(
            "30-Day Average SEO Ratios",
            fontsize=12,
            fontweight="bold",
            color=HEAT_SECONDARY,
        )

    # Chart 4: Key Metrics Table
    table_data = [
        ["Metric", "30-Day Value"],
        ["Total Indexed Pages", f"{summary_stats['total_indexed']:.0f}"],
        ["Total Not Indexed", f"{summary_stats['total_not_indexed']:.0f}"],
        ["Valid Breadcrumbs", f"{summary_stats['total_valid_breadcrumbs']:.0f}"],
        ["HTTPS URLs", f"{summary_stats['total_https_urls']:.0f}"],
        ["Videos Indexed", f"{summary_stats['total_video_indexed']:.0f}"],
        ["Avg Daily Impressions", f"{summary_stats['avg_impressions']:.1f}"],
        ["Max Daily Impressions", f"{summary_stats['max_impressions']:.0f}"],
        ["Period", f"{summary_stats['period_start']} to {summary_stats['period_end']}"],
    ]

    axes[3].axis("off")
    table = axes[3].table(cellText=table_data, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # Style the table
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            if i == 0:  # Header row
                table[(i, j)].set_facecolor(HEAT_PRIMARY)
                table[(i, j)].set_text_props(weight="bold", color="white")
            else:
                table[(i, j)].set_facecolor(HEAT_BACKGROUND)

    axes[3].set_title(
        "30-Day Key Metrics Summary",
        fontsize=12,
        fontweight="bold",
        color=HEAT_SECONDARY,
        pad=20,
    )

    # Add overall title
    fig.suptitle(
        f"HEAT Labs - GSC 30-Day Analytics Dashboard\n{summary_stats['period_start']} to {summary_stats['period_end']} ({summary_stats['period_days']} days)",
        fontsize=16,
        fontweight="bold",
        color=HEAT_SECONDARY,
        y=1.02,
    )

    plt.tight_layout()
    plt.savefig(output_dir / "gsc_summary_dashboard.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    try:
        # Load and process data
        df, summary_stats = load_and_process_data(JSON_FILE_PATH)

        # Create output directory for today
        output_dir = create_output_directory()

        # Create all charts
        print("Creating Indexing Coverage chart...")
        create_indexing_chart(df, output_dir)

        print("Creating Impressions Trend chart...")
        create_impressions_chart(df, output_dir)

        print("Creating Technical SEO Metrics chart...")
        create_technical_seo_chart(df, output_dir)

        print("Creating 30-Day Summary Dashboard...")
        create_summary_dashboard(df, summary_stats, output_dir)

        print("All charts generated successfully!")
        print(f"Output saved to: {output_dir}")
        print(
            f"Analyzed period: {summary_stats['period_start']} to {summary_stats['period_end']} ({summary_stats['period_days']} days)"
        )

    except FileNotFoundError:
        print(f"Error: JSON file not found at {JSON_FILE_PATH}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {JSON_FILE_PATH}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
