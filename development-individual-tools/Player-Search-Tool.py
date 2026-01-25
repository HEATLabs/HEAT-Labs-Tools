import requests
import json
import os
from time import sleep


# Search for all accounts matching search query
def search_accounts(username):
    url = "https://worldoftanks.eu/en/community/accounts/search/"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    all_accounts = []
    name_gt = ""
    page = 1

    print(f"Searching for accounts with username containing: '{username}'")

    while True:
        params = {"name": username, "name_gt": name_gt}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            accounts = data.get("response", [])
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
            print(f"Error fetching page {page}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON on page {page}: {e}")
            break

    return all_accounts


# Save accounts to JSON
def save_to_json(accounts, username):
    # Create search-results folder
    folder_name = "search-results"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}/")

    # Create filename with timestamp
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder_name}/{username}_{timestamp}.json"

    # Create a structured result dictionary
    result = {
        "search_summary": {
            "total_accounts": len(accounts),
            "unique_accounts": len(set(acc["account_id"] for acc in accounts)),
            "search_query": username,
            "search_timestamp": datetime.datetime.now().isoformat(),
        },
        "accounts": accounts,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return filename


# Display summary
def display_summary(accounts):
    if not accounts:
        print("\nNo accounts found!")
        return

    print("\nSEARCH RESULTS SUMMARY")
    print(f"Total accounts found: {len(accounts)}")
    print(f"Unique accounts: {len(set(acc['account_id'] for acc in accounts))}")


def main():
    print("Wargaming Account Search Tool")

    while True:
        # Get username to search for
        username = input("\nEnter username to search for (or 'quit' to exit): ").strip()

        if username.lower() == "quit":
            print("Exiting...")
            break

        if not username:
            print("Error: Username cannot be empty!")
            continue

        # Search for accounts
        accounts = search_accounts(username)

        if accounts:
            # Display summary
            display_summary(accounts)

            # Save to JSON
            filename = save_to_json(accounts, username)
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
