"""
src/dataset/audit.py
---------------------
Audits the images folder against the full lref list from the dataset.
Produces two CSVs:
  - missing_lrefs.csv    : lrefs not found in the folder at all
  - corrupt_lrefs.csv    : lrefs that exist but are suspiciously small (no-access / blank)
"""

# from pathlib import Path
# import csv
# from tqdm import tqdm
# from config import IMAGES_DIR
# from src.dataset.xml_parser import RKDDataset

# # Files at or below this size are considered corrupt/blank (your no-access files are 518 bytes)
# CORRUPT_THRESHOLD_BYTES = 2000  # safe margin above 518

# dataset = RKDDataset()
# dataset.parse()

# candidates = dataset.get_lrefs(best_only=False)
# print(f"Total lrefs in metadata: {len(candidates)}")

# # Infer fieldnames dynamically from the first item
# fields = list(candidates[0].keys())

# missing = []
# corrupt = []

# for item in tqdm(candidates, desc="Auditing"):
#     path = IMAGES_DIR / f"{item['lref']}.jpg"
#     if not path.exists():
#         missing.append(item)
#     elif path.stat().st_size <= CORRUPT_THRESHOLD_BYTES:
#         corrupt.append(item)

# # Save missing
# with open("missing_lrefs.csv", "w", newline="", encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=fields)
#     writer.writeheader()
#     writer.writerows(missing)

# # Save corrupt
# with open("corrupt_lrefs.csv", "w", newline="", encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=fields)
#     writer.writeheader()
#     writer.writerows(corrupt)

# print(f"\nMissing (not in folder):            {len(missing):>6}  → missing_lrefs.csv")
# print(f"Corrupt (≤{CORRUPT_THRESHOLD_BYTES}B, no-access):       {len(corrupt):>6}  → corrupt_lrefs.csv")
# print(f"Accounted for:                      {len(missing) + len(corrupt):>6}")



# ==========================================================================================================
# ==========================================================================================================

from pathlib import Path
import csv
from tqdm import tqdm
from config import IMAGES_DIR
from src.dataset.xml_parser import RKDDataset

CORRUPT_THRESHOLD_BYTES = 2000

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

with open("missing_lrefs.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(missing)

with open("corrupt_lrefs.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(corrupt)

print(f"\nFiles on disk:                      {len(files_on_disk):>6}")
print(f"Missing (not on disk):              {len(missing):>6}  → missing_lrefs.csv")
print(f"Corrupt (≤{CORRUPT_THRESHOLD_BYTES}B, no-access):       {len(corrupt):>6}  → corrupt_lrefs.csv")


# ========================================================================================================
# ========================================================================================================


# After building files_on_disk, add:

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