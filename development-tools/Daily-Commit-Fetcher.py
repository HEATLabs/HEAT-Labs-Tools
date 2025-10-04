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
REPOS = [
    ".github",
    "heatlabs.github.io",
    "Website-Configs",
    "Website-Images",
    "Website-Images-Essentials",
    "Website-Images-Tanks",
    "Website-Images-Maps",
    "Website-Images-News",
    "Website-Images-Gallery",
    "Website-Images-Tournaments",
    "Database-Tools",
    "Database-Files",
    "Sound-Bank",
    "Tank-Models",
    "Website-Changelog",
    "Website-Statistics",
    "Website-Status",
    "HEATLabs-Configurator",
]

EXTRA_REPOS = [
    {"owner": "ThatSINEWAVE", "repo": "HEATLabs-Views-API"},
]


def get_all_commits(repo, owner=None):
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
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_commits = response.json()
        if not page_commits:
            break

        all_commits.extend(page_commits)
        page += 1

    return all_commits


def gather_commits(commits_data):
    daily_commits = defaultdict(list)

    for repo_data in commits_data:
        if isinstance(repo_data, tuple) and len(repo_data) == 2:
            repo, repo_commits = repo_data
        else:
            # Handle extra repos
            repo = repo_data["repo"]
            repo_commits = repo_data["commits"]

        for commit in repo_commits:
            if "commit" not in commit:
                continue

            commit_date = datetime.strptime(
                commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"
            ).date()

            message = commit["commit"]["message"].split("\n")[0]
            entry = f"[{repo}] {message}"

            daily_commits[commit_date.isoformat()].append(entry)

    # Sort descending by date
    return dict(sorted(daily_commits.items(), reverse=True))


def main():
    all_commits = []

    for repo in REPOS:
        try:
            commits = get_all_commits(repo)
            all_commits.append((repo, commits))
            print(f"Fetched {len(commits)} commits from {repo}")
        except Exception as e:
            print(f"Error fetching commits from {repo}: {str(e)}")

    # Get commits from extra repos
    for repo_info in EXTRA_REPOS:
        try:
            commits = get_all_commits(repo_info["repo"], owner=repo_info["owner"])
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

    daily_log = gather_commits(all_commits)

    with open("../../Website-Configs/daily_commits.json", "w", encoding="utf-8") as f:
        json.dump(daily_log, f, indent=2, ensure_ascii=False)

    print("✅ Daily commit log saved to daily_commits.json")


if __name__ == "__main__":
    main()
