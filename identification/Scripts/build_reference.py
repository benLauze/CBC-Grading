"""
Build the reference image pairs and metadata used by the card identifier.

This script scans Card_Dataset, matches each dataset folder to a Pokemon TCG API
set, parses the card number from each filename, and downloads the official image
for each match. The results are saved in Reference/ for model training and later
card identification. The original dataset is only read and is not modified.

The basic matching process was created for this project, while Claude helped
work through several exceptions found during testing. These included the test
mode, alternate API set IDs, subset sets, unusual filename formats, request
timeouts, and support for resuming an interrupted run.
"""

import os
import csv
import json
import time
import re
from pathlib import Path

import requests

# Test mode and API configuration
# Claude helped create TEST_MODE so a few different folder and filename types
# could be checked before running the full dataset and downloading every image.
TEST_MODE = False

# These test folders cover a normal set, a manual alias, and promo numbering.
# When the list is empty, the script uses the first TEST_SET_LIMIT matched sets.
TEST_SETS = ["jungle", "base-set", "xy-promos"]
TEST_SET_LIMIT = 3

API_BASE = "https://api.pokemontcg.io/v2"
API_KEY = os.environ.get("POKEMONTCG_API_KEY")
# Use key.txt when the environment variable is unavailable.
# key.txt should remain outside shared repositories.
if not API_KEY:
    _key_file = Path(__file__).resolve().parent / "key.txt"
    if _key_file.exists():
        API_KEY = _key_file.read_text(encoding="utf-8").strip()

REQUEST_DELAY_SECONDS = 0.3
PAGE_SIZE = 250

# API timeout and failure handling (Claude-assisted)
# The API sometimes timed out during long runs, so failed requests are retried
# with a gradually increasing delay instead of immediately skipping the set.
MAX_RETRIES = 20
MAX_BACKOFF_SECONDS = 30

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Dataset folder and API set mismatches (Claude-assisted)
# Most folders match an API set by name. These mappings handle folders whose
# dataset name is different from the API name or internal set ID.
ALIAS_MAP = {
    "base-set": "base1",
    "expedition": "ecard1",
    "triumphant": "hgss4",
    "undaunted": "hgss3",
    "unleashed": "hgss2",
    "pokemon-go": "pgo",
    "rumble": "ru1",
    "pokemon-futsal-promos-2020": "fut20",
    "scarlet-violet-energy": "sve",
    "ex-trainer-kit-plusle": "tk2a",
    "ex-trainer-kit-minun": "tk2b",
    "xy-promos": "xyp",
    "scarlet-violet-promos": "svp",
    "sword-shield-promos": "swshp",
    "sun-moon-promos": "smp",
    "black-white-promos": "bwp",
    "diamond-pearl-promos": "dpp",
    "heartgold-soulsilver-promos": "hsp",
}

# Cards stored in separate API subsets (Claude-assisted)
# Some dataset folders include Trainer Gallery, Galarian Gallery, or Shiny Vault
# cards even though the API stores those cards under a different set ID.
SUBSET_FALLBACK = {
    "astral-radiance": ["swsh10tg"],   # Trainer Gallery TG01-TG30
    "brilliant-stars": ["swsh9tg"],
    "lost-origin":     ["swsh11tg"],
    "silver-tempest":  ["swsh12tg"],
    "crown-zenith":    ["swsh12pt5gg"], # Galarian Gallery GG01-GG70
    "shining-fates":   ["swsh45sv"],    # Shiny Vault SV001-SV122
}

# Project and reference output paths
# This script is expected to be inside the Scripts folder.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATASET_DIR = PROJECT_DIR / "Card_Dataset"

REFERENCE_DIR = PROJECT_DIR / "Reference"
API_IMAGE_DIR = REFERENCE_DIR / "api_images"
MANIFEST_PATH = REFERENCE_DIR / "reference_manifest.csv"
SETS_DUMP_PATH = REFERENCE_DIR / "api_sets.json"
REPORT_PATH = REFERENCE_DIR / "match_report.txt"
PROGRESS_PATH = REFERENCE_DIR / "completed_sets.txt"

REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
API_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


# Matching helpers
# These functions normalize set names and card numbers before comparing the
# dataset filenames against the values returned by the API.
def normalize_name(text):
    """Remove spacing and punctuation differences from set names."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def normalize_number(text):
    """Make filename and API card numbers use the same format for matching."""
    text = str(text).strip().lower()
    if text.isdigit():
        return str(int(text))
    # Keep prefixes and suffixes while removing leading zeros.
    m = re.fullmatch(r"([a-z]+)0*(\d+)([a-z]*)", text)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
    return text


def parse_number_from_filename(filename):
    """Find the card number inside the dataset's different filename formats."""
    stem = Path(filename).stem
    low = stem.lower()

    # Promo filenames usually store a letter-prefixed number such as XY01.
    if "promo" in low:
        m = re.search(r'(?<![A-Za-z0-9])([A-Za-z]{1,5}\d{1,4}[A-Za-z]?)(?![A-Za-z0-9])', stem)
        if m:
            return m.group(1).upper()

    # Subset filename exceptions (Claude-assisted)
    # Prefixes such as TG, GG, and H can be card numbers. "sv" is different
    # because it can also be the Scarlet & Violet set code at the filename start.
    SUBSET_PREFIXES = ['tg', 'gg', 'rc', 'sl', 'sv', 'ar', 'sh', 'h']
    POSITION0_FORBIDDEN = {'sv'}  # "sv" at the start is a set code
    prefixes_sorted = sorted(SUBSET_PREFIXES, key=len, reverse=True)
    subset_pat = (r'(?<![A-Za-z0-9])(' + '|'.join(prefixes_sorted)
                  + r')(\d{1,4})([A-Za-z]?)(?![A-Za-z0-9])')
    for m in re.finditer(subset_pat, stem, flags=re.IGNORECASE):
        if m.start() == 0 and m.group(1).lower() in POSITION0_FORBIDDEN:
            continue  # leading "svN" is the set code
        prefix = m.group(1).upper()
        digits = str(int(m.group(2)))
        suffix = m.group(3).upper()
        return prefix + digits + suffix

    tokens = re.split(r'[_\-]', stem)
    digit_tokens = [(i, t) for i, t in enumerate(tokens) if t.isdigit()]

    # Claude-assisted POP Series exception: the last number is the card number.
    if "pop-series" in low and digit_tokens:
        return digit_tokens[-1][1]

    # For standard filenames, prefer the most likely one-to-three digit card number.
    if digit_tokens:
        short = [(i, t) for i, t in digit_tokens if 1 <= len(t) <= 3]
        if short:
            short.sort(key=lambda it: (-len(it[1]), it[0]))
            return short[0][1]
        return digit_tokens[0][1]

    # Claude-assisted handling for single-letter card variants such as 107a.
    for t in tokens:
        if re.fullmatch(r'\d{1,3}[a-z]', t, flags=re.IGNORECASE):
            return t.upper()

    return None


def first_image_filename(folder):
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            return item.name
    return ""


def list_images(folder):
    return [f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]


def parse_setcode_from_filename(filename):
    parts = Path(filename).stem.split("_")
    return parts[1] if len(parts) >= 2 else ""


def extract_large_image_url(card):
    return card.get("images", {}).get("large", "")


def api_headers():
    return {"X-Api-Key": API_KEY} if API_KEY else {}


def api_get(path, params=None, retries=MAX_RETRIES):
    """Request one API page and retry temporary connection or server failures."""
    url = f"{API_BASE}/{path}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=api_headers(), params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as error:
            if attempt < retries:
                wait = min(2 * attempt, MAX_BACKOFF_SECONDS)  # increasing delay with a cap
                print(f"  ~ request failed (attempt {attempt}/{retries}), retrying in {wait}s: {error}")
                time.sleep(wait)
            else:
                print(f"  ! API request FAILED after {retries} attempts for {url}: {error}")
                return None


def api_get_all(path, params=None):
    # Continue requesting pages until the API's full result count is collected.
    if params is None:
        params = {}
    params = dict(params)
    params.setdefault("pageSize", PAGE_SIZE)
    all_items, page = [], 1
    while True:
        params["page"] = page
        payload = api_get(path, params=params)
        if not payload or "data" not in payload:
            break
        items = payload["data"]
        all_items.extend(items)
        total = payload.get("totalCount", 0)
        if len(all_items) >= total or not items:
            break
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)
    return all_items


def download_image(url, destination):
    # Keep existing successful downloads so rerunning the script does less work.
    if destination.exists() and destination.stat().st_size > 0:
        return True
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        destination.write_bytes(resp.content)
        return True
    except requests.RequestException as error:
        print(f"  ! Image download failed for {url}: {error}")
        return False


# Main reference-building process
# Match dataset folders to API sets, pair individual cards by number, download
# official images, and save the final manifest and unmatched-file report.
def main():
    if not API_KEY:
        print("WARNING: POKEMONTCG_API_KEY not set; the API will throttle heavily.")
        print('  export POKEMONTCG_API_KEY="your_key_here"\n')

    if not DATASET_DIR.exists():
        print(f"ERROR: Card_Dataset not found at {DATASET_DIR}")
        return

    dataset_folders = sorted([f for f in DATASET_DIR.iterdir() if f.is_dir()])
    print(f"Found {len(dataset_folders)} dataset folders.")

    print("Fetching set list from the API...")
    api_sets = api_get_all("sets")
    print(f"API returned {len(api_sets)} sets.")
    SETS_DUMP_PATH.write_text(json.dumps(api_sets, indent=2), encoding="utf-8")

    set_lookup, set_by_id = {}, {}
    for api_set in api_sets:
        set_by_id[api_set.get("id", "")] = api_set
        key = normalize_name(api_set.get("name", ""))
        if key:
            set_lookup[key] = api_set

    # Try the manual exception map first, then fall back to matching by set name.
    matched_folders, unmatched_folders = [], []
    for folder in dataset_folders:
        api_set = None
        if folder.name in ALIAS_MAP:
            api_set = set_by_id.get(ALIAS_MAP[folder.name])
        if api_set is None:
            api_set = set_lookup.get(normalize_name(folder.name))
        if api_set:
            matched_folders.append((folder, api_set))
        else:
            unmatched_folders.append(folder)

    print(f"Matched {len(matched_folders)} folders to sets.")
    print(f"Unmatched folders: {len(unmatched_folders)}")

    # Claude-assisted test mode can target specific folders or use a small limit.
    if TEST_MODE:
        if TEST_SETS:
            wanted = set(TEST_SETS)
            matched_folders = [(f, s) for (f, s) in matched_folders if f.name in wanted]
            print(f"\nTEST_MODE: processing only {[f.name for f, _ in matched_folders]}")
            missing = wanted - {f.name for f, _ in matched_folders}
            if missing:
                print(f"  (note: requested but not matched/found: {sorted(missing)})")
        else:
            matched_folders = matched_folders[:TEST_SET_LIMIT]
            print(f"\nTEST_MODE: processing first {TEST_SET_LIMIT} matched sets.")

    # Resume handling (Claude-assisted)
    # Completed folders are saved after successful matching so long runs can
    # continue without repeating work after a timeout, crash, or manual stop.
    completed = set()
    if PROGRESS_PATH.exists():
        completed = set(PROGRESS_PATH.read_text(encoding="utf-8").splitlines())
    if completed:
        before = len(matched_folders)
        matched_folders = [(f, s) for (f, s) in matched_folders if f.name not in completed]
        print(f"Resume: skipping {before - len(matched_folders)} already-completed folders.")

    manifest_rows = []
    total_dataset_images = 0
    total_card_matches = 0
    total_images_downloaded = 0
    unmatched_files_report = []

    for folder, api_set in matched_folders:
        set_id = api_set.get("id", "")
        set_name = api_set.get("name", "")
        print(f"\nFolder '{folder.name}' -> set '{set_name}' (id={set_id})")

        cards = api_get_all("cards", params={"q": f"set.id:{set_id}"})
        time.sleep(REQUEST_DELAY_SECONDS)

        # Build a lookup so each parsed filename number can find its API card.
        card_by_number = {}
        for card in cards:
            card_by_number[normalize_number(card.get("number", ""))] = card
        print(f"  API set has {len(cards)} cards.")

        # Merge subset exceptions (Claude-assisted)
        # Main-set cards keep priority, while prefixed subset numbers fill in
        # cards that could not otherwise be found in the folder's primary set.
        for sub_id in SUBSET_FALLBACK.get(folder.name, []):
            sub_cards = api_get_all("cards", params={"q": f"set.id:{sub_id}"})
            time.sleep(REQUEST_DELAY_SECONDS)
            added = 0
            for card in sub_cards:
                key = normalize_number(card.get("number", ""))
                if key not in card_by_number:
                    card_by_number[key] = card
                    added += 1
            print(f"  + subset '{sub_id}': {len(sub_cards)} cards ({added} new numbers merged).")

        set_image_dir = API_IMAGE_DIR / set_id
        set_image_dir.mkdir(parents=True, exist_ok=True)

        dataset_files = list_images(folder)
        total_dataset_images += len(dataset_files)
        set_matches = 0

        # Pair each local image with an API card using the parsed card number.
        for dataset_file in dataset_files:
            number = parse_number_from_filename(dataset_file.name)
            if number is None:
                unmatched_files_report.append(
                    (folder.name, dataset_file.name, "could not parse number"))
                continue

            card = card_by_number.get(normalize_number(number))
            if card is None:
                unmatched_files_report.append(
                    (folder.name, dataset_file.name, f"no card with number {number}"))
                continue

            image_url = extract_large_image_url(card)
            if not image_url:
                unmatched_files_report.append(
                    (folder.name, dataset_file.name, "card has no large image"))
                continue

            # A subset card keeps its own API set ID instead of the folder's
            # main set ID so the downloaded image and manifest stay accurate.
            card_set_id = card.get("set", {}).get("id", set_id)
            card_set_name = card.get("set", {}).get("name", set_name)
            card_id = card.get("id", f"{card_set_id}-{number}")
            card_image_dir = API_IMAGE_DIR / card_set_id
            card_image_dir.mkdir(parents=True, exist_ok=True)
            api_image_path = card_image_dir / f"{card_id}.png"
            ok = download_image(image_url, api_image_path)
            if ok:
                total_images_downloaded += 1
            time.sleep(REQUEST_DELAY_SECONDS)

            manifest_rows.append({
                "card_id": card_id,
                "set_folder": folder.name,
                "api_set_id": card_set_id,
                "api_set_name": card_set_name,
                "number": number,
                "name": card.get("name", ""),
                "rarity": card.get("rarity", ""),
                "dataset_image_path": str(dataset_file),
                "api_image_path": str(api_image_path) if ok else "",
                "api_image_url": image_url,
            })
            total_card_matches += 1
            set_matches += 1

        print(f"  paired {set_matches}/{len(dataset_files)} images in this folder.")
        if set_matches > 0:
            with open(PROGRESS_PATH, "a", encoding="utf-8") as pf:
                pf.write(folder.name + "\n")

    # Save one manifest row for every successful dataset-to-API pairing.
    if manifest_rows:
        with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_rows)

    # Record totals and the reasons that any files could not be paired.
    report = []
    report.append("=== Reference build report (pokemontcg.io) ===\n")
    report.append(f"TEST_MODE: {TEST_MODE}  TEST_SETS: {TEST_SETS}")
    report.append(f"Dataset folders found: {len(dataset_folders)}")
    report.append(f"Folders processed this run: {len(matched_folders)}")
    report.append(f"Dataset images seen (processed sets): {total_dataset_images}")
    report.append(f"Cards paired (image pairs created): {total_card_matches}")
    report.append(f"API images downloaded: {total_images_downloaded}")
    report.append("")
    report.append(f"--- Files that did not pair ({len(unmatched_files_report)}) ---")
    for folder_name, filename, reason in unmatched_files_report[:150]:
        report.append(f"  [{folder_name}] {filename}: {reason}")
    if len(unmatched_files_report) > 150:
        report.append(f"  ... and {len(unmatched_files_report) - 150} more")

    report_text = "\n".join(report)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    print(f"\nManifest: {MANIFEST_PATH}")
    print(f"Report:   {REPORT_PATH}")


if __name__ == "__main__":
    main()