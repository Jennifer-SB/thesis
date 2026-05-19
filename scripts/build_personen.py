"""
scripts/build_personen.py
--------------------------
Copies face crops from gezichten/ into personen/, organised by sitter identity.

Source:  D:/thesis/gezichten/{lref}_0.jpg   (solo-face crops)
Dest:    D:/thesis/personen/{sitter_id}/{lref}.jpg

Only processes lrefs present in training_set.csv (27k training set).
Safe to re-run — skips files that already exist.

Run from the thesis/ root folder:
    python scripts/build_personen.py
"""

import sys
import csv
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from config import GEZICHTEN_DIR, PERSONEN_DIR

TRAINING_CSV = Path("training_set.csv")

# ------------------------------------------------------------------
# Load training set
# ------------------------------------------------------------------

print(f"\nReading {TRAINING_CSV} ...")
with open(TRAINING_CSV, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"  {len(rows):,} rows  ({len({r['sitter_id'] for r in rows}):,} unique sitters)")

# ------------------------------------------------------------------
# Copy crops
# ------------------------------------------------------------------

PERSONEN_DIR.mkdir(parents=True, exist_ok=True)

copied   = 0
skipped  = 0
missing  = []

for row in tqdm(rows, desc="Copying crops"):
    lref      = row["lref"]
    sitter_id = row["sitter_id"]

    src  = GEZICHTEN_DIR / f"{lref}_0.jpg"
    dest = PERSONEN_DIR / sitter_id / f"{lref}.jpg"

    if not src.exists():
        missing.append(lref)
        continue

    if dest.exists():
        skipped += 1
        continue

    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(src, dest)
    copied += 1

# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------

print(f"\n{'='*50}")
print(f"  BUILD PERSONEN SUMMARY")
print(f"{'='*50}")
print(f"  Copied:   {copied:>8,}")
print(f"  Skipped:  {skipped:>8,}  (already existed)")
print(f"  Missing:  {len(missing):>8,}  (crop not found in gezichten)")
print(f"{'='*50}")

if missing:
    print(f"\n  First 10 missing lrefs:")
    for lref in missing[:10]:
        print(f"    {lref}")
    if len(missing) > 10:
        print(f"    ... and {len(missing) - 10} more")

# Verify folder structure
sitter_dirs = [d for d in PERSONEN_DIR.iterdir() if d.is_dir()]
print(f"\n  Sitter folders created: {len(sitter_dirs):,}")
portrait_counts = [len(list(d.glob('*.jpg'))) for d in sitter_dirs]
if portrait_counts:
    print(f"  Portraits per sitter:  min={min(portrait_counts)}  "
          f"max={max(portrait_counts)}  "
          f"avg={sum(portrait_counts)/len(portrait_counts):.1f}")

print(f"\n✅ Done. Personen folder: {PERSONEN_DIR}")
