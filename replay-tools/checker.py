import os
import json
import zlib

# === CONFIGURATION ===
FILENAME = "replays/05_friendshipdam_conquest_2025_03_01_19_17_51_9147c5c8.replay"
OUTPUT_FILENAME = FILENAME + "_output.txt"


def print_and_write(file, message):
    print(message)
    file.write(message + "\n")


def try_parse_json(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8")), True
    except Exception:
        return None, False


def decompress_zlib(data_bytes):
    try:
        return zlib.decompress(data_bytes), True
    except Exception:
        return None, False


def extract_replay_data(filename):
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    with open(filename, "rb") as f:
        raw = f.read()

    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
        print_and_write(out, f"Opened {filename}, size: {len(raw)} bytes")

        # Step 1
        json_segments = []
        for i in range(len(raw)):
            if raw[i : i + 1] == b"{":
                for j in range(i + 10, min(i + 5000, len(raw))):
                    if raw[j : j + 1] == b"}":
                        possible_json = raw[i : j + 1]
                        data, ok = try_parse_json(possible_json)
                        if ok:
                            json_segments.append((i, j, data))
                            print_and_write(out, f"Found JSON segment at {i}-{j}")
                            break

        if not json_segments:
            print_and_write(out, "No plain JSON segments found.")

        for index, (start, end, data) in enumerate(json_segments):
            print_and_write(out, f"\n--- JSON Segment {index+1} ---")
            formatted = json.dumps(data, indent=2)
            out.write(formatted + "\n")

        # Step 2
        print_and_write(out, "\nScanning for zlib-compressed data...")
        found = 0
        for i in range(len(raw)):
            if raw[i : i + 2] == b"x\x9c":
                for j in range(i + 100, min(i + 50000, len(raw))):
                    chunk = raw[i:j]
                    decompressed, ok = decompress_zlib(chunk)
                    if ok:
                        found += 1
                        print_and_write(out, f"\n--- ZLIB Chunk {found} at {i}-{j} ---")
                        try:
                            decompressed_text = decompressed.decode("utf-8")
                            out.write(decompressed_text + "\n")
                        except Exception:
                            out.write("[BINARY NON-UTF8 DATA]\n")
                        break

        if found == 0:
            print_and_write(out, "No zlib-compressed chunks found.")

    print(f"\nDone! Extracted data saved to {OUTPUT_FILENAME}")


extract_replay_data(FILENAME)
