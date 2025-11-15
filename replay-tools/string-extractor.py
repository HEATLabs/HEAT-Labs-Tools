import re

FILENAME = "../../HEAT-Labs-Database/replays/1.replay"
OUTPUT_FILENAME = FILENAME + "_strings.txt"


MIN_LENGTH = 4
STRING_REGEX = re.compile(rb'[\x20-\x7E]{' + str(MIN_LENGTH).encode() + rb',}')


def extract_strings(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    matches = STRING_REGEX.findall(data)
    return [s.decode("utf-8", errors="replace") for s in matches]


def main():
    try:
        print(f"Reading file: {FILENAME}")
        strings = extract_strings(FILENAME)

        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as out:
            for s in strings:
                out.write(s + "\n")

        print(f"Extracted {len(strings)} strings.")
        print(f"Saved to {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
