"""
src/audit.py
-------------
Audits the images folder against the full lref list from the dataset.
Produces two CSVs:
  - missing_lrefs.csv    : lrefs not found in the folder at all
  - corrupt_lrefs.csv    : lrefs that exist but are suspiciously small (no-access / blank)

Run from the thesis/ root folder:
    python 1_dataset_construction/src/audit.py
"""

import sys
import csv
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root -> config.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 1_dataset_construction -> src package

from config import IMAGES_DIR, MISSING_LREFS_CSV, CORRUPT_LREFS_CSV
from src.xml_parser import RKDDataset

CORRUPT_THRESHOLD_BYTES = 2000


def main():
    dataset = RKDDataset()
    dataset.parse()

    candidates = dataset.get_lrefs(best_only=False)
    print(f"Total lrefs in metadata: {len(candidates)}")

    # Build ground truth from disk — one single scan
    print("Scanning disk...")
    files_on_disk = {p.stem: p for p in IMAGES_DIR.iterdir() if p.is_file()}
    print(f"Files actually on disk: {len(files_on_disk)}")

    fields = list(candidates[0].keys())
    missing = []
    corrupt = []

    for item in tqdm(candidates, desc="Auditing"):
        stem = str(item["lref"])
        if stem not in files_on_disk:
            missing.append(item)
        elif files_on_disk[stem].stat().st_size <= CORRUPT_THRESHOLD_BYTES:
            corrupt.append(item)

    with open(MISSING_LREFS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(missing)

    with open(CORRUPT_LREFS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(corrupt)

    print(f"\nFiles on disk:                      {len(files_on_disk):>6}")
    print(f"Missing (not on disk):              {len(missing):>6}  -> {MISSING_LREFS_CSV}")
    print(f"Corrupt (<={CORRUPT_THRESHOLD_BYTES}B, no-access):       {len(corrupt):>6}  -> {CORRUPT_LREFS_CSV}")

    # Check for non-jpg files in the folder
    non_jpg = [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() != '.jpg']
    print(f"Non-jpg files on disk: {len(non_jpg)}")
    if non_jpg[:5]:
        print(f"Examples: {non_jpg[:5]}")

    # Check for duplicate lrefs in metadata
    lrefs = [str(item['lref']) for item in candidates]
    print(f"Unique lrefs in metadata: {len(set(lrefs))}")
    print(f"Duplicates: {len(lrefs) - len(set(lrefs))}")

    # Check if lref format matches filename format
    print(f"Example lref: {lrefs[0]}")
    print(f"Example disk stem: {list(files_on_disk.keys())[0]}")


if __name__ == "__main__":
    main()