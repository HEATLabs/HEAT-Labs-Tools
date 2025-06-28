import os
import json
import glob
import re
from tqdm import tqdm

# CONFIGURATION
REPLAYS_FOLDER = "replays"
OUTPUT_FILENAME = "all_replays_output.json"

# Player name pattern
PLAYER_REGEX = re.compile(rb"\b[\w]{3,20}#[0-9]{3,6}\b")


def try_parse_json(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8")), True
    except Exception:
        return None, False


def extract_build_info(raw_data):
    build_info = {"build": None, "branch": None}

    try:
        data_str = raw_data.decode("utf-8", errors="ignore")
    except:
        return build_info

    build_prefix = "build: '"
    build_start = data_str.find(build_prefix)
    if build_start != -1:
        build_start += len(build_prefix)
        build_end = data_str.find("'", build_start)
        if build_end != -1:
            build_info["build"] = data_str[build_start:build_end]

    branch_prefix = "branch: '"
    branch_start = data_str.find(branch_prefix)
    if branch_start != -1:
        branch_start += len(branch_prefix)
        branch_end = data_str.find("'", branch_start)
        if branch_end != -1:
            build_info["branch"] = data_str[branch_start:branch_end]

    return build_info


def extract_player_names(raw_data):
    matches = PLAYER_REGEX.findall(raw_data)
    names = sorted(set(s.decode("utf-8", errors="replace") for s in matches))
    return names


def initialize_output_file():
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        json.dump(
            {"total_files": 0, "processed_files": 0, "results": {}}, out, indent=2
        )


def update_output_file(filename, json_segments, build_info, player_names):
    try:
        with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"total_files": 0, "processed_files": 0, "results": {}}

    basename = os.path.basename(filename)
    data["results"][basename] = {
        "match_details": json_segments,
        "game_version": build_info,
        "players": player_names,
    }
    data["processed_files"] = len(data["results"])

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)


def process_replay_file(filename):
    if not os.path.exists(filename):
        update_output_file(filename, {"error": "File not found"}, {}, [])
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
                        json_segments.append({"details": data})
                        break

    build_info = extract_build_info(raw)
    player_names = extract_player_names(raw)

    update_output_file(filename, json_segments, build_info, player_names)
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
        json.dump(data, f, indent=4)
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
