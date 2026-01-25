import requests
import json
import os
from time import sleep

# Region configuration
REGIONS = {
    "EU": "worldoftanks.eu",
    "NA": "worldoftanks.com",
    "ASIA": "worldoftanks.asia",
    "ALL": ["worldoftanks.eu", "worldoftanks.com", "worldoftanks.asia"],
}

# Domain to region name mapping
DOMAIN_TO_REGION_NAME = {
    "worldoftanks.eu": "EU",
    "worldoftanks.com": "NA",
    "worldoftanks.asia": "ASIA",
}


# Get region name from domain
def get_region_name(domain):
    return DOMAIN_TO_REGION_NAME.get(domain, domain.replace("worldoftanks.", ""))


# Search for all accounts matching search query
def search_accounts(username, domain):
    url = f"https://{domain}/en/community/accounts/search/"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    all_accounts = []
    name_gt = ""
    page = 1

    region_name = get_region_name(domain)
    print(
        f"Searching on {region_name} region for accounts with username containing: '{username}'"
    )

    while True:
        params = {"name": username, "name_gt": name_gt}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            accounts = data.get("response", [])

            # Add region information
            for account in accounts:
                account["region"] = region_name

            all_accounts.extend(accounts)

            print(f"Page {page}: Found {len(accounts)} accounts")

            # Check if there are more results
            if data.get("show_more_accounts", False):
                name_gt = data.get("name_gt", "")
                if not name_gt:
                    break
                page += 1
                sleep(1)  # Small delay to be polite to WG (and also avoid rate limits)
            else:
                break

        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page} from {region_name} region: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON on page {page} from {region_name} region: {e}")
            break

    return all_accounts


# Search in all regions
def search_all_regions(username):
    all_accounts = []

    print(f"\nSearching in ALL regions for: '{username}'")

    for domain in REGIONS["ALL"]:
        region_name = get_region_name(domain)
        print(f"\nSearching on: {region_name} region")
        region_accounts = search_accounts(username, domain)
        all_accounts.extend(region_accounts)
        print(f"  Total found on {region_name} region: {len(region_accounts)}")
        sleep(1)  # Delay between regions

    return all_accounts


# Save accounts to JSON
def save_to_json(accounts, username, region_choice):
    # Create search-results folder
    folder_name = "search-results"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}/")

    # Create filename with timestamp
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create region identifier for filename
    if region_choice == "ALL":
        region_id = "all_regions"
    else:
        region_id = region_choice.lower()

    filename = f"{folder_name}/{username}_{region_id}_{timestamp}.json"

    # Group results by region for summary
    accounts_by_region = {}
    for acc in accounts:
        region = acc.get("region", "unknown")
        if region not in accounts_by_region:
            accounts_by_region[region] = 0
        accounts_by_region[region] += 1

    # Create a structured result dictionary
    result = {
        "search_summary": {
            "total_accounts": len(accounts),
            "unique_accounts": len(set(acc["account_id"] for acc in accounts)),
            "search_query": username,
            "search_region": region_choice,
            "accounts_by_region": accounts_by_region,
            "search_timestamp": datetime.datetime.now().isoformat(),
        },
        "accounts": accounts,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return filename


# Display summary
def display_summary(accounts, region_choice):
    if not accounts:
        print("\nNo accounts found!")
        return

    print("\nSEARCH RESULTS SUMMARY")
    print(f"Region searched: {region_choice}")
    print(f"Total accounts found: {len(accounts)}")
    print(f"Unique accounts: {len(set(acc['account_id'] for acc in accounts))}")

    # Show breakdown by region
    if region_choice == "ALL" or region_choice == "all":
        print("\nBreakdown by region:")
        regions_count = {}
        for acc in accounts:
            region = acc.get("region", "unknown")
            if region not in regions_count:
                regions_count[region] = 0
            regions_count[region] += 1

        for region, count in regions_count.items():
            print(f"- {region}: {count} accounts")


def main():
    print("Wargaming Account Search Tool")

    while True:
        # Get region choice
        print("\nSelect region to search in:")
        print("1. EU (Europe)")
        print("2. NA (North America)")
        print("3. ASIA (Asia)")
        print("4. ALL (Search all regions)")
        print("5. Quit")

        region_choice = input("\nEnter choice (1-5): ").strip()

        if region_choice == "5":
            print("Exiting...")
            break

        region_map = {"1": "EU", "2": "NA", "3": "ASIA", "4": "ALL"}

        if region_choice not in region_map:
            print("Error: Invalid choice! Please enter 1, 2, 3, 4, or 5.")
            continue

        selected_region = region_map[region_choice]

        # Get username to search for
        username = input("\nEnter username to search for: ").strip()

        if not username:
            print("Error: Username cannot be empty!")
            continue

        # Search for accounts
        if selected_region == "ALL":
            accounts = search_all_regions(username)
        else:
            domain = REGIONS[selected_region]
            accounts = search_accounts(username, domain)

        if accounts:
            # Display summary
            display_summary(accounts, selected_region)

            # Save to JSON
            filename = save_to_json(accounts, username, selected_region)
            print(f"Results saved to: {filename}")
        else:
            print("\nNo accounts found matching your search.")

        # Ask to do another search
        choice = input("\nPerform another search? (y/n): ").lower()
        if choice != "y":
            print("Exiting...")
            break


if __name__ == "__main__":
    main()
