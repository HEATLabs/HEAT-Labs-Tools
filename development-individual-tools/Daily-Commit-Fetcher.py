import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import os

# Load token from ../.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GitHub token not found in ../.env")

# Config
GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "HEATLabs"
COMMIT_HISTORY_DAYS = 30
REPOS = [
    ".github",
    "HEAT-Labs-Archives",
    "HEAT-Labs-Brand-Kit",
    "HEAT-Labs-Changelog",
    "HEAT-Labs-Configs",
    "HEAT-Labs-Configurator",
    "HEAT-Labs-Configurator-Development",
    "HEAT-Labs-Database",
    "HEAT-Labs-Desktop",
    "HEAT-Labs-Desktop-Development",
    "HEAT-Labs-Discord",
    "HEAT-Labs-Discord-Bot",
    "HEAT-Labs-Games",
    "HEAT-Labs-Images",
    "HEAT-Labs-Images-Blogs",
    "HEAT-Labs-Images-Features",
    "HEAT-Labs-Images-Gallery",
    "HEAT-Labs-Images-Guides",
    "HEAT-Labs-Images-Maps",
    "HEAT-Labs-Images-News",
    "HEAT-Labs-Images-Tanks",
    "HEAT-Labs-Images-Tournaments",
    "HEAT-Labs-Internal-Assets",
    "HEAT-Labs-Internal-Tools",
    "HEAT-Labs-Mobile-App",
    "HEAT-Labs-Models",
    "HEAT-Labs-Models-Development",
    "HEAT-Labs-Mods",
    "HEAT-Labs-Replay-Manager",
    "HEAT-Labs-Replay-Manager-Development",
    "HEAT-Labs-Search",
    "HEAT-Labs-Socials",
    "HEAT-Labs-Sounds",
    "HEAT-Labs-Stat-Tracker",
    "HEAT-Labs-Stat-Tracker-Development",
    "HEAT-Labs-Static",
    "HEAT-Labs-Statistics",
    "HEAT-Labs-Status",
    "HEAT-Labs-Steam-Assets",
    "HEAT-Labs-Store",
    "HEAT-Labs-Stream-Tools",
    "HEAT-Labs-Tank-Game",
    "HEAT-Labs-Tools",
    "HEAT-Labs-Videos",
    "HEAT-Labs-Website",
    "HEAT-Labs-Website-Development",
    "HEAT-Labs-WGC-API-Emulator",
]
EXTRA_REPOS = [
    {"owner": "ThatSINEWAVE", "repo": "HEAT-Labs-Views-API"},
]

EXTRA_REPO_NAMES = {r["repo"] for r in EXTRA_REPOS}
ORG_REPOS = [r for r in REPOS if r not in EXTRA_REPO_NAMES]


def get_all_commits(repo, owner=None, since=None):
    if owner:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits"
    else:
        url = f"{GITHUB_API_URL}/repos/{ORG_NAME}/{repo}/commits"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    all_commits = []
    page = 1

    while True:
        params = {"per_page": 100, "page": page}
        if since is not None:
            # GitHub expects ISO 8601 UTC, e.g. 2024-01-01T00:00:00Z
            params["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_commits = response.json()
        if not page_commits:
            break

        all_commits.extend(page_commits)
        page += 1

        # Stop paging early if the oldest commit on this page predates `since`
        if since is not None and page_commits:
            oldest = page_commits[-1].get("commit", {}).get("committer", {}).get("date")
            if oldest:
                try:
                    oldest_dt = datetime.strptime(oldest, "%Y-%m-%dT%H:%M:%SZ")
                    if oldest_dt < since:
                        break
                except ValueError:
                    pass

    return all_commits


def gather_commits(commits_data, cutoff_date):
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
            except (KeyError, ValueError):
                continue

            # Double-check cutoff client-side (in case API returned older items)
            if commit_date < cutoff_date:
                continue

            message = commit["commit"]["message"].split("\n")[0]
            entry = f"[{repo}] {message}"
            daily_commits[commit_date.isoformat()].append(entry)

    # Sort descending by date
    return dict(sorted(daily_commits.items(), reverse=True))


def main():
    # Cutoff = now - COMMIT_HISTORY_DAYS (UTC)
    now_utc = datetime.utcnow()
    since_dt = now_utc - timedelta(days=COMMIT_HISTORY_DAYS)
    cutoff_date = since_dt.date()

    print(
        f"Fetching commits since {since_dt.strftime('%Y-%m-%dT%H:%M:%SZ')} "
        f"(last {COMMIT_HISTORY_DAYS} days)"
    )

    all_commits = []

    for repo in ORG_REPOS:
        try:
            commits = get_all_commits(repo, since=since_dt)
            all_commits.append((repo, commits))
            print(f"Fetched {len(commits)} commits from {ORG_NAME}/{repo}")
        except Exception as e:
            print(f"Error fetching commits from {ORG_NAME}/{repo}: {str(e)}")

    # Get commits from extra repos
    for repo_info in EXTRA_REPOS:
        full_name = f"{repo_info['owner']}/{repo_info['repo']}"
        try:
            commits = get_all_commits(
                repo_info["repo"],
                owner=repo_info["owner"],
                since=since_dt,
            )
            all_commits.append({"repo": full_name, "commits": commits})
            print(f"Fetched {len(commits)} commits from {full_name}")
        except Exception as e:
            print(f"Error fetching commits from {full_name}: {str(e)}")

    daily_log = gather_commits(all_commits, cutoff_date)

    out_path = "../../HEAT-Labs-Configs/daily_commits.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(daily_log, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in daily_log.values())
    print(
        f"✅ Daily commit log saved to {out_path} "
        f"({len(daily_log)} days, {total} commits, last {COMMIT_HISTORY_DAYS} days)"
    )


if __name__ == "__main__":
    main()
