import os
import json
import glob
from tqdm import tqdm

# CONFIGURATION
REPLAYS_FOLDER = "replays"
OUTPUT_FILENAME = "all_replays_output.json"


def try_parse_json(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8")), True
    except Exception:
        return None, False


def initialize_output_file():
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        json.dump(
            {"total_files": 0, "processed_files": 0, "results": {}}, out, indent=2
        )


def update_output_file(filename, json_segments):
    try:
        with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"total_files": 0, "processed_files": 0, "results": {}}

    basename = os.path.basename(filename)
    data["results"][basename] = {"json_segments": json_segments}
    data["processed_files"] = len(data["results"])

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)


def process_replay_file(filename):
    if not os.path.exists(filename):
        update_output_file(filename, {"error": "File not found"})
        return []

    with open(filename, "rb") as f:
        raw = f.read()

    json_segments = []
    for i in range(len(raw)):
        if raw[i : i + 1] == b"{":
            for j in range(i + 10, min(i + 5000, len(raw))):
                if raw[j : j + 1] == b"}":
                    possible_json = raw[i : j + 1]
                    data, ok = try_parse_json(possible_json)
                    if ok:
                        json_segments.append({"content": data})
                        break

    update_output_file(filename, json_segments)
    return json_segments


def process_all_replays():
    replay_files = glob.glob(os.path.join(REPLAYS_FOLDER, "*.REPLAY"))

    if not replay_files:
        print(f"No .REPLAY files found in {REPLAYS_FOLDER}")
        return

    initialize_output_file()

    with open(OUTPUT_FILENAME, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["total_files"] = len(replay_files)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    with tqdm(
        replay_files,
        desc="Processing replays",
        unit="file",
        bar_format="{l_bar}{bar:20}{r_bar}",
        colour="green",
    ) as pbar:
        for replay_file in pbar:
            process_replay_file(replay_file)
            pbar.set_postfix(file=os.path.basename(replay_file)[:15] + "...")

    print(f"\nSuccessfully processed {len(replay_files)} replay files")
    print(f"Output saved to: {OUTPUT_FILENAME}")


if __name__ == "__main__":
    process_all_replays()
