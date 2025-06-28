import os
import json
import glob

# CONFIGURATION
REPLAYS_FOLDER = "replays"
OUTPUT_FILENAME = "all_replays_output.txt"


def print_and_write(file, message):
    print(message)
    file.write(message + "\n")


def try_parse_json(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8")), True
    except Exception:
        return None, False


def process_replay_file(filename, out_file):
    if not os.path.exists(filename):
        print_and_write(out_file, f"File not found: {filename}")
        return

    with open(filename, "rb") as f:
        raw = f.read()

    print_and_write(out_file, f"\n\n=== Processing {filename} ===")
    print_and_write(out_file, f"File size: {len(raw)} bytes")

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
                        print_and_write(out_file, f"Found JSON segment at {i}-{j}")
                        break

    if not json_segments:
        print_and_write(out_file, "No JSON segments found in this file.")
    else:
        for index, (start, end, data) in enumerate(json_segments):
            print_and_write(out_file, f"\n--- JSON Segment {index + 1} ---")
            formatted = json.dumps(data, indent=2)
            out_file.write(formatted + "\n")


def process_all_replays():
    replay_files = glob.glob(os.path.join(REPLAYS_FOLDER, "*.REPLAY"))

    if not replay_files:
        print(f"No .REPLAY files found in {REPLAYS_FOLDER}")
        return

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        print_and_write(out, f"Processing {len(replay_files)} replay files...")

        for replay_file in replay_files:
            process_replay_file(replay_file, out)

    print(f"\nDone! All extracted data saved to {OUTPUT_FILENAME}")


process_all_replays()
