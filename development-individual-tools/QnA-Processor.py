import hashlib
import json
import os
import re
from datetime import datetime

# CONFIGURATION
INPUT_FOLDER = "../../HEAT-Labs-Database/raw-qna"
OUTPUT_JSON = "../../HEAT-Labs-Configs/questions-answers.json"


def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def strip_md(text):
    text = text.replace("**", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip(" \r\n\t*:")
    return text.strip()


def parse_filename(filename):
    name = os.path.splitext(filename)[0]

    ep_match = re.search(r"episode-(\d+)", name, re.IGNORECASE)
    episode_number = int(ep_match.group(1)) if ep_match else None

    date_match = re.search(r"(\d{2})(\d{2})(\d{4})", name)
    date_iso = None
    if date_match:
        day, month, year = date_match.groups()
        try:
            date_iso = datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            date_iso = None

    return episode_number, date_iso


def extract_tldr(text):
    match = re.search(
        r"\*\*\s*TL[;:]DR\s*-?\s*(.*?)\*\*", text, re.IGNORECASE | re.DOTALL
    )
    if match:
        return strip_md(match.group(1))
    return None


SPEAKER_LINE_RE = re.compile(
    r"(?:^|\n)[ \t]*\*{0,2}\(([^)]+)\)\*{0,2}[ \t]*"
    r"(.*?)(?=(?:\n[ \t]*\*{0,2}\([^)]+\)\*{0,2})|\Z)",
    re.DOTALL,
)

NOTE_NAME_HINTS = ("op ", "note from op", "op:", "op on")


def parse_answer_block(answer_text):
    answer_text = answer_text.strip()
    responses = []
    notes = []

    matches = list(SPEAKER_LINE_RE.finditer(answer_text))

    if not matches:
        # No "(Speaker)" tags at all - just store the raw answer text.
        cleaned = strip_md(answer_text)
        if cleaned:
            responses.append({"speaker": None, "text": cleaned})
        return responses, notes

    # Anything before the first speaker tag (rare, but keep it just in case)
    preamble = strip_md(answer_text[: matches[0].start()])
    if preamble:
        responses.append({"speaker": None, "text": preamble})

    for m in matches:
        speaker_raw = m.group(1).strip()
        content = strip_md(m.group(2))

        speaker_lower = speaker_raw.lower()
        if any(hint in speaker_lower for hint in NOTE_NAME_HINTS):
            # Notes are usually written entirely *inside* the parentheses,
            label_match = re.match(
                r"^(?:note from op|op on [^:]*)\s*:\s*(.*)$",
                speaker_raw,
                re.IGNORECASE | re.DOTALL,
            )
            note_text = (
                label_match.group(1).strip() if label_match else speaker_raw.strip()
            )
            if content:
                note_text = f"{note_text} {content}".strip()
            note_text = strip_md(note_text)
            if note_text:
                notes.append(note_text)
        elif content:
            responses.append({"speaker": speaker_raw, "text": content})

    return responses, notes


ENTRY_SPLIT_RE = re.compile(r"\r?\n[ \t]*(\d{1,3})\.?[ \t]*\r?\n(?=Q:)")


def parse_entries(body_text):
    # Find all entry-start markers ("1.\nQ:", "2.\nQ:", "10\nQ:", ...)
    starts = list(ENTRY_SPLIT_RE.finditer(body_text))
    if not starts:
        return [], body_text

    entries = []
    for i, m in enumerate(starts):
        number = int(m.group(1))
        content_start = m.end()
        content_end = starts[i + 1].start() if i + 1 < len(starts) else len(body_text)
        block = body_text[content_start:content_end]
        entries.append(_parse_single_entry(number, block))
    return entries, ""


def _parse_single_entry(number, block):
    q_match = re.search(r"Q:\s*(.*?)\n\s*A:\s*", block, re.DOTALL)
    if not q_match:
        # Malformed entry - store raw text so nothing gets silently dropped
        return {
            "number": number,
            "question": None,
            "answers": [],
            "notes": [],
            "raw": strip_md(block),
        }

    question_raw = q_match.group(1)
    is_chat_question = "[C]" in question_raw
    question_clean = strip_md(question_raw.replace("[C]", ""))

    answer_text = block[q_match.end():]
    answers, notes = parse_answer_block(answer_text)

    return {
        "number": number,
        "question": question_clean,
        "answers": answers,
        "notes": notes,
    }


def parse_episode_file(path):
    filename = os.path.basename(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    episode_number, date_iso = parse_filename(filename)
    tldr = extract_tldr(text)
    entries, extra_commentary = parse_entries(text)

    return {
        "filename": filename,
        "episode_number": episode_number,
        "date": date_iso,
        "tldr": tldr,
        "questions": entries,
        "extra_commentary": strip_md(extra_commentary)
        if extra_commentary.strip()
        else None,
        "source_hash": file_hash(path),
    }


# main sync logic
def load_existing(output_path):
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def build_json(input_folder, output_path):
    existing = load_existing(output_path)
    existing_episodes = existing.get("episodes", {})

    txt_files = sorted(
        f for f in os.listdir(input_folder) if f.lower().endswith(".txt")
    )

    new_episodes = {}
    parsed_count = 0
    reused_count = 0

    for filename in txt_files:
        path = os.path.join(input_folder, filename)
        current_hash = file_hash(path)
        cached = existing_episodes.get(filename)

        if cached and cached.get("source_hash") == current_hash:
            new_episodes[filename] = cached
            reused_count += 1
        else:
            new_episodes[filename] = parse_episode_file(path)
            parsed_count += 1

    # sort episodes by episode_number (falling back to filename)
    ordered = sorted(
        new_episodes.values(),
        key=lambda e: (
            e["episode_number"] if e["episode_number"] is not None else 9999,
            e["filename"],
        ),
    )

    output = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_folder": input_folder,
        "episode_count": len(ordered),
        "total_questions": sum(len(e["questions"]) for e in ordered),
        "episodes": {e["filename"]: e for e in ordered},
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    dropped = set(existing_episodes) - set(new_episodes)

    print(f"Scanned {len(txt_files)} .txt file(s) in {input_folder}")
    print(f"  Parsed (new/changed): {parsed_count}")
    print(f"  Reused (unchanged):   {reused_count}")
    if dropped:
        print(f"  Removed (no longer in folder): {len(dropped)} -> {sorted(dropped)}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    build_json(INPUT_FOLDER, OUTPUT_JSON)
