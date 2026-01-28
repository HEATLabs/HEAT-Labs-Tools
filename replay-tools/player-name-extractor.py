import re

FILENAME = "../../HEAT-Labs-Replays/replays/1.replay"
OUTPUT_FILENAME = FILENAME + "_players.txt"

PLAYER_REGEX = re.compile(rb"\b[\w]{3,20}#[0-9]{3,6}\b")


def extract_player_names(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    matches = PLAYER_REGEX.findall(data)

    return sorted(set(s.decode("utf-8", errors="replace") for s in matches))


def main():
    try:
        print(f"Reading file: {FILENAME}")
        players = extract_player_names(FILENAME)

        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
            for name in players:
                out.write(name + "\n")

        print(f"Extracted {len(players)} unique player names.")
        print(f"Saved to {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
