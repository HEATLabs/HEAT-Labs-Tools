import json
from collections import Counter, defaultdict
from datetime import datetime
import statistics


def analyze_replay_data(filename):
    # Load the data
    with open(filename, "r") as f:
        data = json.load(f)

    results = data["results"]

    # Basic statistics
    total_matches = len(results)
    print(f"=== REPLAY DATA ANALYSIS ===\n")
    print(f"Total files processed: {data['processed_files']}/{data['total_files']}")
    print(f"Matches analyzed: {total_matches}\n")

    # Win/Loss statistics
    wins = 0
    losses = 0
    unknown_results = 0
    match_results = []

    for replay_file, match_data in results.items():
        # Check if match_details exists
        if (
            "match_details" in match_data
            and match_data["match_details"]
            and len(match_data["match_details"]) > 0
        ):
            result = match_data["match_details"][0]["details"]["m_endGameType"]
            match_results.append(result)
            if result == "Win":
                wins += 1
            elif result == "Loose":
                losses += 1
            else:
                unknown_results += 1
        else:
            unknown_results += 1
            match_results.append("Unknown")

    win_ratio = wins / (wins + losses) if (wins + losses) > 0 else 0

    print(f"=== MATCH RESULTS ===")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Unknown/Invalid: {unknown_results}")
    print(f"Win Ratio: {win_ratio:.2%}")
    if (wins + losses) > 0:
        print(f"Loss Ratio: {(losses / (wins + losses)):.2%}")
    print()

    # Map statistics
    map_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "unknown": 0, "total": 0})

    for replay_file, match_data in results.items():
        map_name = match_data["map_info"]["map"]
        game_mode = match_data["map_info"]["mode"]

        # Safely get result
        result = "Unknown"
        if (
            "match_details" in match_data
            and match_data["match_details"]
            and len(match_data["match_details"]) > 0
        ):
            result = match_data["match_details"][0]["details"]["m_endGameType"]

        key = f"{map_name} ({game_mode})"
        map_stats[key]["total"] += 1
        if result == "Win":
            map_stats[key]["wins"] += 1
        elif result == "Loose":
            map_stats[key]["losses"] += 1
        else:
            map_stats[key]["unknown"] += 1

    print(f"=== MAP STATISTICS ===")
    for map_name, stats in map_stats.items():
        known_matches = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / known_matches if known_matches > 0 else 0
        print(f"{map_name}:")
        print(
            f"  Matches: {stats['total']} (WINS: {stats['wins']}, LOSSES: {stats['losses']}, UNKNOWN: {stats['unknown']})"
        )
        if known_matches > 0:
            print(f"  Win Rate: {win_rate:.2%}")
        else:
            print(f"  Win Rate: N/A (no known results)")
    print()

    # Player statistics
    player_stats = defaultdict(
        lambda: {"matches": 0, "wins": 0, "losses": 0, "unknown": 0}
    )
    player_teammates = defaultdict(set)

    for replay_file, match_data in results.items():
        # Safely get result
        result = "Unknown"
        if (
            "match_details" in match_data
            and match_data["match_details"]
            and len(match_data["match_details"]) > 0
        ):
            result = match_data["match_details"][0]["details"]["m_endGameType"]

        players = match_data["players"]

        # Record each player's performance
        for player in players:
            player_stats[player]["matches"] += 1
            if result == "Win":
                player_stats[player]["wins"] += 1
            elif result == "Loose":
                player_stats[player]["losses"] += 1
            else:
                player_stats[player]["unknown"] += 1

            # Record teammates
            for teammate in players:
                if teammate != player:
                    player_teammates[player].add(teammate)

    # Most active players
    print(f"=== PLAYER STATISTICS ===")
    print(f"Total unique players: {len(player_stats)}\n")

    # Top 10 most active players
    most_active = sorted(
        player_stats.items(), key=lambda x: x[1]["matches"], reverse=True
    )[:10]
    print("Top 10 Most Active Players:")
    for player, stats in most_active:
        known_matches = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / known_matches if known_matches > 0 else 0
        print(
            f"  {player}: {stats['matches']} matches ({win_rate:.2%} win rate, unknown: {stats['unknown']})"
        )
    print()

    # Players with highest win rate
    qualified_players = {
        p: s for p, s in player_stats.items() if (s["wins"] + s["losses"]) >= 2
    }
    if qualified_players:
        best_win_rate = sorted(
            qualified_players.items(),
            key=lambda x: x[1]["wins"] / (x[1]["wins"] + x[1]["losses"]),
            reverse=True,
        )[:5]
        print("Top 5 Players by Win Rate (min 2 known matches):")
        for player, stats in best_win_rate:
            win_rate = stats["wins"] / (stats["wins"] + stats["losses"])
            print(
                f"  {player}: {win_rate:.2%} ({stats['wins']}-{stats['losses']}, ?: {stats['unknown']})"
            )
        print()

    # Team size analysis
    team_sizes = [len(match_data["players"]) for match_data in results.values()]
    avg_team_size = statistics.mean(team_sizes) if team_sizes else 0
    min_team_size = min(team_sizes) if team_sizes else 0
    max_team_size = max(team_sizes) if team_sizes else 0

    print(f"=== PLAYERS PER MATCH ANALYSIS ===")
    print(f"Average players per match: {avg_team_size:.1f}")
    print(f"Minimum players per match: {min_team_size}")
    print(f"Maximum players per match: {max_team_size}")

    # Team size distribution
    size_distribution = Counter(team_sizes)
    print(f"\nTeam Size Distribution:")
    for size, count in sorted(size_distribution.items()):
        percentage = (count / total_matches) * 100
        print(f"  {size} players: {count} matches ({percentage:.1f}%)")
    print()

    # Player partnerships
    print(f"=== PLAYER PARTNERSHIPS ===")
    player_partnerships = Counter()

    for replay_file, match_data in results.items():
        players = match_data["players"]
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                pair = tuple(sorted([players[i], players[j]]))
                player_partnerships[pair] += 1

    # Top 10 most frequent partnerships
    top_partnerships = player_partnerships.most_common(10)
    print("Top 10 Most Frequent Teammate Pairs:")
    for (player1, player2), games_together in top_partnerships:
        print(f"  {player1} & {player2}: {games_together} matches together")
    print()

    # Match date analysis
    print(f"=== TIME ANALYSIS ===")
    dates = []
    problematic_files = []

    for filename in results.keys():
        # Extract date from filename
        try:
            parts = filename.split("_")
            if len(parts) < 7:
                problematic_files.append(filename)
                continue

            year, month, day = int(parts[3]), int(parts[4]), int(parts[5])
            dates.append((year, month, day))
        except (ValueError, IndexError) as e:
            problematic_files.append(filename)
            continue

    if dates:
        date_counter = Counter(dates)
        most_active_date, most_matches = date_counter.most_common(1)[0]
        print(
            f"Most active date: {most_active_date[1]}/{most_active_date[2]}/{most_active_date[0]} "
            f"({most_matches} matches)"
        )
        print(f"Total days with matches: {len(date_counter)}")
    else:
        print("No valid dates found in filenames")

    if problematic_files:
        print(
            f"\nNote: {len(problematic_files)} files had problematic filenames for date parsing"
        )

    # Additional analysis: Streaks
    print(f"\n=== STREAK ANALYSIS ===")
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0

    for match_data in results.values():
        # Safely get result
        result = "Unknown"
        if (
            "match_details" in match_data
            and match_data["match_details"]
            and len(match_data["match_details"]) > 0
        ):
            result = match_data["match_details"][0]["details"]["m_endGameType"]

        if result == "Win":
            if current_streak >= 0:
                current_streak += 1
            else:
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        elif result == "Loose":
            if current_streak <= 0:
                current_streak -= 1
            else:
                current_streak = -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))
        # Unknown results break streaks
        else:
            current_streak = 0

    print(f"Longest win streak: {max_win_streak}")
    print(f"Longest loss streak: {max_loss_streak}")

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total matches: {total_matches}")
    print(
        f"Matches with known results: {wins + losses} ({((wins + losses) / total_matches * 100):.1f}%)"
    )
    print(f"Overall win rate: {win_ratio:.2%}")
    print(f"Unique players: {len(player_stats)}")
    print(f"Average team size: {avg_team_size:.1f}")

    return {
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "unknown_results": unknown_results,
        "win_ratio": win_ratio,
        "unique_players": len(player_stats),
        "avg_team_size": avg_team_size,
        "player_stats": dict(player_stats),
        "map_stats": dict(map_stats),
    }


if __name__ == "__main__":
    filename = "../../HEAT-Labs-Configs/replays_output.json"
    try:
        analysis_results = analyze_replay_data(filename)
        print("\n=== ANALYSIS COMPLETE ===")
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except json.JSONDecodeError:
        print(f"Error: File '{filename}' contains invalid JSON.")
    except KeyError as e:
        print(f"Error: Missing expected key in data: {e}")
        print("Please check if your JSON structure matches the expected format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        print(f"Detailed error: {traceback.format_exc()}")
