"""
scripts/select_images.py
-------------------------
Prepares the dataset for training:
  1. Scans all downloaded images and reads their resolution via PIL.
  2. Groups images by priref.
  3. Picks the best image per priref using this priority:
        1. Highest resolution (width × height)
        2. Color over black-and-white (tiebreaker)
        3. Lower QUALITY_RANK index (tiebreaker)
  4. Filters out images below MIN_RESOLUTION.
  5. Writes a manifest CSV — the single source of truth for training.

The manifest CSV contains one row per selected priref with:
    priref, lref, path, width, height, megapixels,
    soort, is_color, sitter_count, sitter_ids, date, objectcat, artist_name

No files are copied — the manifest points to the existing images on disk.
Downstream training code reads the manifest directly.

Run from the thesis/ root folder:
    python scripts/select_images.py
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
Image.MAX_IMAGE_PIXELS = None   # disable decompression bomb check for trusted data
from tqdm import tqdm

from config import IMAGES_DIR, MANIFEST_CSV, MIN_RESOLUTION, PLOTS_DIR
from src.dataset.xml_parser import RKDDataset, QUALITY_RANK


# ------------------------------------------------------------------
# Color classification
# ------------------------------------------------------------------

# Soort values that are considered color images
COLOR_TYPES = {
    "digital color photograph",
    "color photograph",
    "color reproduction",
    "ektachrome",
    "color photocopy",
    "digital image",
    "digital photograph",
    "digital file",
}

# Soort values that are considered black-and-white
BW_TYPES = {
    "digital black-and-white photograph",
    "black and white photograph",
    "old black-and-white photograph",
    "brown photograph",
    "black-and-white reproduction",
    "black-and-white photocopy",
    "black-and-white negative",
    "negative",
    "original photograph",      # usually b&w in this period
    "photograph",               # usually b&w in this period
    "slide (photo)",
}


def color_score(soort: str) -> int:
    """
    Lower = more preferred.
      0 = known color type
      1 = unknown/ambiguous (neutral)
      2 = known black-and-white type
    """
    soort_lower = soort.lower()
    if soort_lower in {s.lower() for s in COLOR_TYPES}:
        return 0
    if soort_lower in {s.lower() for s in BW_TYPES}:
        return 2
    return 1   # ambiguous — ranked between color and b&w


def is_color(soort: str) -> bool:
    """Returns True if soort is a known color type."""
    return soort.lower() in {s.lower() for s in COLOR_TYPES}


# ------------------------------------------------------------------
# Selection key
# ------------------------------------------------------------------

def selection_key(candidate: dict, lref_info: dict) -> tuple:
    """
    Sorting key for picking the best image.
    Lower = better (use with min()).

    Priority:
        1. Resolution — higher is better (negated so min() works)
        2. Color score — 0=color, 1=ambiguous, 2=b&w
        3. Quality rank — lower index in QUALITY_RANK is better
    """
    info        = lref_info[candidate["lref"]]
    pixels      = info["width"] * info["height"]
    col_score   = color_score(candidate["soort"])
    qual_score  = RKDDataset.quality_score(candidate["soort"])

    return (
        -pixels,      # negate: we want highest resolution first
        col_score,    # 0=color preferred
        qual_score,   # lower QUALITY_RANK index preferred
    )


# ------------------------------------------------------------------
# Step 1: scan all downloaded images and read their resolution
# ------------------------------------------------------------------

def scan_images(images_dir: Path) -> dict:
    """
    Scan all .jpg files in images_dir and read their resolution.

    Returns:
        dict mapping lref (str) → {path, width, height, megapixels}
    """
    jpg_files = list(images_dir.glob("*.jpg"))
    print(f"\nFound {len(jpg_files):,} images in {images_dir}")

    lref_info = {}
    failed    = []

    for path in tqdm(jpg_files, desc="Reading resolutions"):
        lref = path.stem   # filename without .jpg = lref
        try:
            with Image.open(path) as img:
                w, h = img.size
                lref_info[lref] = {
                    "path":       path,
                    "width":      w,
                    "height":     h,
                    "megapixels": round((w * h) / 1_000_000, 3),
                }
        except Exception:
            failed.append(path)

    if failed:
        print(f"  ⚠️  Could not read {len(failed)} images (corrupt or truncated)")

    return lref_info


# ------------------------------------------------------------------
# Step 2: pick best image per priref
# ------------------------------------------------------------------

def pick_best_per_priref(dataset: RKDDataset,
                          lref_info: dict,
                          min_resolution: tuple) -> tuple:
    """
    For each priref, pick the best downloaded image using selection_key().
    Applies minimum resolution filter.

    Returns (selected, no_image_rows, too_small_rows).
    """
    min_w, min_h = min_resolution

    selected       = []
    no_image_rows  = []
    too_small_rows = []

    for rec in dataset.records.values():
        priref = rec["priref"]

        # Filter to only downloaded lrefs
        candidates = [
            m for m in rec["media"]
            if m["lref"] in lref_info
        ]

        if not candidates:
            no_image_rows.append({
                "priref":      priref,
                "artist_name": rec["artist_name"] or "",
                "date":        rec["date_zoekmarge"] or rec["date_datering"] or "",
                "objectcat":   rec["objectcat"] or "",
                "lrefs_in_xml": "|".join(m["lref"] for m in rec["media"]),
            })
            continue

        # Pick best using priority key
        best = min(candidates, key=lambda m: selection_key(m, lref_info))
        info = lref_info[best["lref"]]

        # Track below-resolution images for reference (but still include in manifest)
        if info["width"] < min_w or info["height"] < min_h:
            too_small_rows.append({
                "priref":      priref,
                "lref":        best["lref"],
                "width":       info["width"],
                "height":      info["height"],
                "megapixels":  info["megapixels"],
                "soort":       best["soort"],
                "artist_name": rec["artist_name"] or "",
                "date":        rec["date_zoekmarge"] or rec["date_datering"] or "",
                "objectcat":   rec["objectcat"] or "",
            })

        # Collect sitter info
        sitter_ids = [p["nummer"] for p in rec["personen"] if p["nummer"]]

        selected.append({
            "priref":       priref,
            "lref":         best["lref"],
            "path":         str(info["path"]),
            "width":        info["width"],
            "height":       info["height"],
            "megapixels":   info["megapixels"],
            "soort":        best["soort"],
            "is_color":     is_color(best["soort"]),
            "sitter_count": len(rec["personen"]),
            "sitter_ids":   "|".join(sitter_ids),
            "date":         rec["date_zoekmarge"] or rec["date_datering"] or "",
            "objectcat":    rec["objectcat"] or "",
            "artist_name":  rec["artist_name"] or "",
        })

    print(f"\n  Prirefs with no downloaded image:  {len(no_image_rows):>8}")
    print(f"  Rejected (below {min_w}x{min_h}):      {len(too_small_rows):>8}")
    print(f"  Selected:                          {len(selected):>8}")

    return selected, no_image_rows, too_small_rows


# ------------------------------------------------------------------
# Step 3: write manifest CSV
# ------------------------------------------------------------------

def write_manifest(selected: list, manifest_path: Path) -> None:
    """Write the selected images to a manifest CSV."""
    fieldnames = [
        "priref", "lref", "path", "width", "height", "megapixels",
        "soort", "is_color", "sitter_count", "sitter_ids",
        "date", "objectcat", "artist_name",
    ]
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    color_count = sum(1 for r in selected if r["is_color"])
    bw_count    = sum(1 for r in selected if not r["is_color"])

    print(f"\n  ✅ Manifest saved to {manifest_path}")
    print(f"     {len(selected):,} rows  ×  {len(fieldnames)} columns")
    print(f"     Color images:  {color_count:,}")
    print(f"     Other/B&W:     {bw_count:,}")


# ------------------------------------------------------------------
# Step 4: resolution distribution chart
# ------------------------------------------------------------------

def chart_resolution_distribution(selected: list) -> None:
    """Bar chart of megapixel buckets for selected images."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter

    buckets = Counter()
    for row in selected:
        mp = row["megapixels"]
        if mp < 0.1:
            bucket = "<0.1 MP"
        elif mp < 0.5:
            bucket = "0.1–0.5 MP"
        elif mp < 1.0:
            bucket = "0.5–1 MP"
        elif mp < 2.0:
            bucket = "1–2 MP"
        elif mp < 5.0:
            bucket = "2–5 MP"
        elif mp < 10.0:
            bucket = "5–10 MP"
        else:
            bucket = "10+ MP"
        buckets[bucket] += 1

    order  = ["<0.1 MP", "0.1–0.5 MP", "0.5–1 MP", "1–2 MP", "2–5 MP", "5–10 MP", "10+ MP"]
    labels = [b for b in order if b in buckets]
    counts = [buckets[b] for b in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, counts, color="#4C72B0", edgecolor="white")
    ax.set_title("Resolution distribution of selected images",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Megapixels")
    ax.set_ylabel("Number of images")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 20,
                str(count), ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    fname = PLOTS_DIR / "chart_resolution_distribution.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  ✅ {fname}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    dataset = RKDDataset()
    dataset.parse()

    lref_info = scan_images(IMAGES_DIR)

    print(f"\nSelecting best image per priref "
          f"(min {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]}, color preferred)...")
    selected, no_image_rows, too_small_rows = pick_best_per_priref(dataset, lref_info, MIN_RESOLUTION)

    write_manifest(selected, MANIFEST_CSV)

    no_image_csv = Path("prirefs_no_image.csv")
    with open(no_image_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["priref", "artist_name", "date", "objectcat", "lrefs_in_xml"])
        writer.writeheader()
        writer.writerows(no_image_rows)
    print(f"  ✅ {no_image_csv}  ({len(no_image_rows):,} rows)")

    too_small_csv = Path("prirefs_too_small.csv")
    with open(too_small_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["priref", "lref", "width", "height", "megapixels", "soort", "artist_name", "date", "objectcat"])
        writer.writeheader()
        writer.writerows(too_small_rows)
    print(f"  ✅ {too_small_csv}  ({len(too_small_rows):,} rows)")

    # Remove rows where lref == 10783267.
    # This scan returns an "image not available" placeholder (not a real artwork image).
    # The RKD assigned this lref to hundreds of different priref records, so it would
    # appear in hundreds of training samples under different sitter labels — corrupting
    # any model trained on this data. We drop all rows that reference it.
    EXCLUDE_LREFS = {"10783267"}
    before = len(selected)
    selected = [r for r in selected if r["lref"] not in EXCLUDE_LREFS]
    removed = before - len(selected)
    if removed:
        print(f"\n  Removed {removed} row(s) with excluded lref(s): {EXCLUDE_LREFS}")
        write_manifest(selected, MANIFEST_CSV)

    # Keep only rows with exactly one sitter who has a known ID.
    # sitter_count == 1: single-portrait artworks only — group portraits are excluded
    # because multiple faces in one image make it impossible to reliably assign a
    # single identity label for training.
    # sitter_ids != '': the one sitter must be identified (has a persoonsnummer).
    # Unidentified sitters (position known but no ID) cannot be used as training labels.
    before = len(selected)
    selected = [
        r for r in selected
        if r["sitter_count"] == "1" and r["sitter_ids"] != ""
    ]
    print(f"\n  Kept single known-sitter rows: {len(selected)}  (removed {before - len(selected)})")
    write_manifest(selected, MANIFEST_CSV)

    print("\nGenerating resolution chart...")
    chart_resolution_distribution(selected)

    print(f"\n✅ Done. Load the manifest in training with:")
    print(f"   import pandas as pd")
    print(f"   df = pd.read_csv('{MANIFEST_CSV}')")
    print(f"   # sitter_ids column is pipe-separated: df['sitter_ids'].str.split('|')")