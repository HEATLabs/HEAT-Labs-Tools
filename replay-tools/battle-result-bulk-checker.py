import os
import json
import glob
from tqdm import tqdm

# CONFIGURATION
REPLAYS_FOLDER = "replays"
OUTPUT_FILENAME = "all_replays_output.txt"


def try_parse_json(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8")), True
    except Exception:
        return None, False


def process_replay_file(filename, out_file):
    if not os.path.exists(filename):
        out_file.write(f"File not found: {filename}\n")
        return

    with open(filename, "rb") as f:
        raw = f.read()

    out_file.write(f"\n\n=== Processing {filename} ===\n")
    out_file.write(f"File size: {len(raw)} bytes\n")

    # JSON scanning
    json_segments = []
    for i in range(len(raw)):
        if raw[i : i + 1] == b"{":
            for j in range(i + 10, min(i + 5000, len(raw))):
                if raw[j : j + 1] == b"}":
                    possible_json = raw[i : j + 1]
                    data, ok = try_parse_json(possible_json)
                    if ok:
                        json_segments.append((i, j, data))
                        out_file.write(f"Found JSON segment at {i}-{j}\n")
                        break

    if not json_segments:
        out_file.write("No JSON segments found in this file.\n")
    else:
        for index, (start, end, data) in enumerate(json_segments):
            out_file.write(f"\n--- JSON Segment {index + 1} ---\n")
            formatted = json.dumps(data, indent=2)
            out_file.write(formatted + "\n")


def process_all_replays():
    replay_files = glob.glob(os.path.join(REPLAYS_FOLDER, "*.REPLAY"))

    if not replay_files:
        print(f"No .REPLAY files found in {REPLAYS_FOLDER}")
        return

    total_files = len(replay_files)

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        out.write(f"Processing {total_files} replay files...\n")

        with tqdm(
            replay_files,
            desc="Processing replays",
            unit="file",
            bar_format="{l_bar}{bar:20}{r_bar}",
            colour="green",
        ) as pbar:
            for replay_file in pbar:
                process_replay_file(replay_file, out)
                pbar.set_postfix(file=os.path.basename(replay_file)[:15] + "...")

    print(f"\nSuccessfully processed {total_files} replay files")
    print(f"Output saved to: {OUTPUT_FILENAME}")


if __name__ == "__main__":
    process_all_replays()
