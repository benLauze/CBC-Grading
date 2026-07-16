"""
Build a searchable embedding index for every card image in the dataset.

This script runs every image in Card_Dataset through the trained encoder and
saves its embedding with matching card metadata. Cards without confirmed API
metadata are still included using information from their folder and filename.
The completed index is later searched by identify.py to find the closest card.
"""

import csv
import re
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras

# Configuration, project paths, and model settings
TEST_MODE = False      # set False for the real run
TEST_LIMIT = 200      # images to process in TEST_MODE

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATASET_DIR = PROJECT_DIR / "Card_Dataset"
MANIFEST_PATH = PROJECT_DIR / "Reference" / "reference_manifest.csv"
MODEL_PATH = PROJECT_DIR / "Models" / "encoder_best.keras"

EMBEDDINGS_OUT = PROJECT_DIR / "Reference" / "card_index_embeddings.npy"
METADATA_OUT = PROJECT_DIR / "Reference" / "card_index_metadata.csv"

IMAGE_SIZE = 224
BATCH_SIZE = 32
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
AUTOTUNE = tf.data.AUTOTUNE


# Manifest lookup and unmatched-card metadata fallback
# Claude assisted with the Windows path normalization, missing-manifest,
# and local-only card cases handled in this section.
def manifest_key(path_str):
    parts = str(path_str).replace("\\", "/").split("/")
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return str(path_str)
    return f"{parts[-2]}/{parts[-1]}"


def load_manifest_lookup():
    lookup = {}
    if not MANIFEST_PATH.exists():
        print(f"WARNING: manifest not found at {MANIFEST_PATH}; "
              f"proceeding with NO API metadata (all cards will be local-only).")
        return lookup
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = manifest_key(row.get("dataset_image_path", ""))
            lookup[key] = row
    return lookup


def guess_name_from_filename(filename):
    """Create a display name from the filename when API metadata is unavailable."""
    stem = Path(filename).stem
    cleaned = re.sub(r"[-_]+", " ", stem).strip()
    return cleaned.title() if cleaned else stem


# Dataset image discovery and metadata row creation
def find_all_card_images():
    if not DATASET_DIR.exists():
        raise FileNotFoundError(f"Card_Dataset not found at {DATASET_DIR}")
    items = []
    for folder in sorted(p for p in DATASET_DIR.iterdir() if p.is_dir()):
        for file in sorted(folder.iterdir()):
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
                items.append((folder.name, file))
    return items


def build_metadata_rows(items, manifest_lookup):
    rows = []
    for folder_name, file_path in items:
        key = f"{folder_name}/{file_path.name}"
        m = manifest_lookup.get(key)
        if m:
            rows.append({
                "card_id": m.get("card_id", key),
                "name": m.get("name", ""),
                "set_folder": folder_name,
                "api_set_id": m.get("api_set_id", ""),
                "api_set_name": m.get("api_set_name", ""),
                "number": m.get("number", ""),
                "rarity": m.get("rarity", ""),
                "image_path": str(file_path),
                "matched": True,
            })
        else:
            rows.append({
                "card_id": f"local-{key}",
                "name": guess_name_from_filename(file_path.name),
                "set_folder": folder_name,
                "api_set_id": "",
                "api_set_name": "",
                "number": "",
                "rarity": "",
                "image_path": str(file_path),
                "matched": False,
            })
    return rows


# Image validation before embedding generation
# Claude assisted with the corrupt-image handling used to keep the
# metadata rows and embeddings in the same order.
def filter_readable(rows):
    good_rows, bad_paths = [], []
    for row in rows:
        path = row["image_path"]
        try:
            data = tf.io.read_file(path)
            img = tf.image.decode_image(data, channels=3, expand_animations=False)
            if img.shape[0] is None or tf.size(img) == 0:
                raise ValueError("empty image")
            good_rows.append(row)
        except Exception as error:
            bad_paths.append((path, str(error)))
    return good_rows, bad_paths


# Clean image preprocessing and batched embedding generation
def _read_image(path):
    data = tf.io.read_file(path)
    img = tf.image.decode_image(data, channels=3, expand_animations=False)
    img = tf.image.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
    return img / 255.0


def _preprocess(img01):
    return keras.applications.resnet50.preprocess_input(img01 * 255.0)


def make_encode_dataset(paths):
    ds = tf.data.Dataset.from_tensor_slices(paths)
    ds = ds.map(lambda p: _preprocess(_read_image(p)), num_parallel_calls=AUTOTUNE)
    return ds.batch(BATCH_SIZE).prefetch(AUTOTUNE)


# Index creation, output saving, and final safety checks
# Claude assisted with the Windows Unicode filename fallback and the
# final embedding-to-metadata alignment check.
def main():
    # Prevent Unicode filenames from causing console errors on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print(f"Loading encoder from {MODEL_PATH} ...")
    if not MODEL_PATH.exists():
        print("ERROR: trained model not found. Run train_embedding.py (Stage 2) first.")
        return
    model = keras.models.load_model(MODEL_PATH)
    print("Encoder loaded.\n")

    print("Scanning Card_Dataset/ for every card image (matched or not) ...")
    items = find_all_card_images()
    folder_count = len({f for f, _ in items})
    print(f"Found {len(items)} images across {folder_count} folders.")

    manifest_lookup = load_manifest_lookup()
    print(f"Manifest has metadata for {len(manifest_lookup)} cards.")

    rows = build_metadata_rows(items, manifest_lookup)
    matched_count = sum(1 for r in rows if r["matched"])
    print(f"{matched_count} / {len(rows)} images have confirmed API metadata.")
    print(f"{len(rows) - matched_count} images will use a best-effort filename-based name.\n")

    if TEST_MODE:
        rows = rows[:TEST_LIMIT]
        print(f"TEST_MODE: limiting to first {len(rows)} images.\n")

    print("Checking that every image file is readable (skips corrupt files "
          "safely, before encoding, so the index never gets misaligned)...")
    rows, bad = filter_readable(rows)
    if bad:
        print(f"  {len(bad)} unreadable file(s) skipped:")
        for path, reason in bad[:20]:
            print(f"    {path}: {reason}")
        if len(bad) > 20:
            print(f"    ... and {len(bad) - 20} more")
    else:
        print("  All files readable.")
    print(f"Proceeding with {len(rows)} images.\n")

    paths = [r["image_path"] for r in rows]
    print(f"Encoding {len(paths)} images through the model "
          f"(this is a single forward pass per image - no training, "
          f"so much faster than Stage 2, but still takes a while on CPU)...")
    ds = make_encode_dataset(paths)
    embeddings = model.predict(ds, verbose=1)
    print(f"\nDone encoding. Embeddings shape: {embeddings.shape}")

    # Confirm the embeddings and metadata stayed aligned.
    assert embeddings.shape[0] == len(rows), (
        f"MISALIGNMENT: {embeddings.shape[0]} embeddings but {len(rows)} metadata rows. "
        f"Do not use this output - tell Claude."
    )

    out_dir = PROJECT_DIR / "Reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_OUT, embeddings.astype("float32"))
    print(f"Saved embeddings -> {EMBEDDINGS_OUT}")

    with open(METADATA_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved metadata   -> {METADATA_OUT}")

    final_matched = sum(1 for r in rows if r["matched"])
    print(f"\nIndex complete: {len(rows)} cards searchable "
          f"({final_matched} API-verified, {len(rows) - final_matched} local-only).")
    if TEST_MODE:
        print("\nThis was a TEST_MODE run. Set TEST_MODE = True and re-run for the full index.")


if __name__ == "__main__":
    main()