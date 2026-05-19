"""
scripts/build_training_table.py
--------------------------------
Builds the final training set metadata table by combining:
  1. dataset_manifest.csv  — base filtering (single known-sitter portraits)
  2. GEZICHTEN_DIR (config.py) — face detection results (keep only solo-face lrefs)
  3. RKDimages.xml         — extra metadata not in manifest

Filtering steps (counts printed at each step):
  1. Manifest rows (single known-sitter portraits)
  2. Solo-face: lrefs with exactly 1 face crop in gezichten
  3. Multi-sitter: keep only sitters appearing in 2+ portraits

Output: training_set.csv

Run from the thesis/ root folder:
    python scripts/build_training_table.py
"""

import sys
import csv
import os
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm
from config import MANIFEST_CSV, XML_FILE, GEZICHTEN_DIR

TRAINING_CSV = Path("training_set.csv")

OUTPUT_FIELDS = [
    # Image / artwork identity
    "priref", "lref",
    # Sitter
    "sitter_id", "sitter_zekerheid", "sitter_beschrijving", "sitter_status",
    # Dates
    "date_datering", "zoekmarge_begindatum", "zoekmarge_einddatum",
    # Artwork info
    "title_english", "title_dutch",
    "objectcat", "genre",
    "materiaal", "drager",
    "trefwoorden_en",
    "identificatie_grond",
    # Artist
    "artist_name", "artist_id",
    # Image technical
    "soort", "is_color", "width", "height", "megapixels", "path",
    # Face detection
    "face_crop_count",
    # Training stats
    "sitter_portrait_count",
]


# ------------------------------------------------------------------
# Step 1 — read manifest
# ------------------------------------------------------------------

print("\nReading dataset_manifest.csv ...")
with open(MANIFEST_CSV, newline="", encoding="utf-8") as f:
    manifest = list(csv.DictReader(f))

print(f"  Manifest rows (single known-sitter): {len(manifest):,}")


# ------------------------------------------------------------------
# Step 2 — scan gezichten to count crops per lref
# ------------------------------------------------------------------

print(f"\nScanning {GEZICHTEN_DIR} for face crops ...")
crop_counts: Counter = Counter()
for p in tqdm(list(GEZICHTEN_DIR.iterdir()), desc="Scanning crops"):
    if p.suffix == ".jpg":
        lref = p.stem.rsplit("_", 1)[0]
        crop_counts[lref] += 1

n_with_crop  = sum(1 for r in manifest if crop_counts.get(r["lref"], 0) > 0)
n_no_crop    = len(manifest) - n_with_crop
n_solo       = sum(1 for r in manifest if crop_counts.get(r["lref"], 0) == 1)
n_multi_face = sum(1 for r in manifest if crop_counts.get(r["lref"], 0) >= 2)
print(f"  lrefs with ≥1 crop:       {n_with_crop:,}")
print(f"  lrefs with 0 crops:       {n_no_crop:,}  (no face detected)")
print(f"  lrefs with exactly 1:     {n_solo:,}  → solo-face portraits")
print(f"  lrefs with 2+ crops:      {n_multi_face:,}  (multi-face, excluded)")


# ------------------------------------------------------------------
# Step 3 — filter to solo-face
# ------------------------------------------------------------------

solo = [r for r in manifest if crop_counts.get(r["lref"], 0) == 1]
print(f"\nAfter solo-face filter:   {len(solo):,}  (removed {len(manifest) - len(solo):,})")


# ------------------------------------------------------------------
# Step 4 — filter to sitters with 2+ portraits
# ------------------------------------------------------------------

sitter_counter: Counter = Counter(r["sitter_ids"] for r in solo)
multi_sitters  = {sid for sid, cnt in sitter_counter.items() if cnt >= 2}
training       = [r for r in solo if r["sitter_ids"] in multi_sitters]

print(f"Unique sitters (solo set):  {len(sitter_counter):,}")
print(f"  with 1 portrait:          {sum(1 for c in sitter_counter.values() if c == 1):,}  (excluded — can't form pairs)")
print(f"  with 2+ portraits:        {len(multi_sitters):,}")
print(f"After 2+ portrait filter:   {len(training):,}  (removed {len(solo) - len(training):,})")

sitter_portrait_counts = Counter(r["sitter_ids"] for r in training)


# ------------------------------------------------------------------
# Step 5 — parse XML for additional metadata (scoped to training prirefs)
# ------------------------------------------------------------------

target_prirefs = {r["priref"] for r in training}
print(f"\nParsing XML for {len(target_prirefs):,} prirefs ...")

def _extract(line: str) -> str:
    try:
        return line[line.index(">") + 1 : line.rindex("<")].strip()
    except ValueError:
        return ""

extra: dict[str, dict] = {}

current_priref         = None
inside_target          = False
buf: dict              = {}
materiaal_list         = []
id_grond_list          = []
trefwoorden_list       = []
last_persoon           = None
inside_soort           = False
inside_objectcat       = False
inside_genre           = False
inside_materiaal       = False
inside_drager          = False
inside_toeschrijving   = False
inside_trefwoord       = False
current_trefwoord_en   = None

def _flush():
    if current_priref and inside_target:
        extra[current_priref] = {
            "date_datering":       buf.get("date_datering", ""),
            "zoekmarge_begindatum": buf.get("zoekmarge_begindatum", ""),
            "zoekmarge_einddatum":  buf.get("zoekmarge_einddatum", ""),
            "title_english":       buf.get("title_english", ""),
            "title_dutch":         buf.get("title_dutch", ""),
            "genre":               buf.get("genre", ""),
            "materiaal":           "|".join(materiaal_list),
            "drager":              buf.get("drager", ""),
            "trefwoorden_en":      "|".join(trefwoorden_list),
            "identificatie_grond": "|".join(id_grond_list),
            "artist_id":           buf.get("artist_id", ""),
            # Sitter — first non-rejected person only (all in training set are huidig)
            "sitter_zekerheid":    last_persoon["zekerheid"]    if last_persoon else "",
            "sitter_beschrijving": last_persoon["beschrijving"] if last_persoon else "",
            "sitter_status":       last_persoon["status"]       if last_persoon else "",
        }

file_size = os.path.getsize(XML_FILE)

with open(XML_FILE, "r", encoding="utf-8") as f:
    with tqdm(total=file_size, unit="B", unit_scale=True, desc="Parsing XML") as pbar:
        for line in f:
            pbar.update(len(line.encode("utf-8")))
            s = line.strip()

            # --- New record ---
            if '<priref tag="%0"' in s and "/>" not in s:
                _flush()
                current_priref       = _extract(s)
                inside_target        = current_priref in target_prirefs
                buf                  = {}
                materiaal_list       = []
                id_grond_list        = []
                trefwoorden_list     = []
                last_persoon         = None
                inside_soort         = False
                inside_objectcat     = False
                inside_genre         = False
                inside_materiaal     = False
                inside_drager        = False
                inside_toeschrijving = False
                inside_trefwoord     = False
                current_trefwoord_en = None
                continue

            if not inside_target:
                continue

            # --- Sitter ---
            if '<persoonsnummer tag="z3"' in s and "linkref" not in s:
                if "/>" not in s:
                    val = _extract(s)
                    if val and last_persoon is None:    # only first sitter (single-sitter filter)
                        last_persoon = {
                            "zekerheid": None, "beschrijving": None, "status": None,
                        }
                continue

            if last_persoon is not None:
                if '<zekerheid_identificatie_portret' in s and "/>" not in s:
                    val = _extract(s)
                    if val and last_persoon["zekerheid"] is None:
                        last_persoon["zekerheid"] = val
                    continue
                if '<persoonsbeschrijving' in s and "linkref" not in s and "/>" not in s:
                    val = _extract(s)
                    if val and last_persoon["beschrijving"] is None:
                        last_persoon["beschrijving"] = val
                    continue
                if '<status_identificatie_portret' in s and "/>" not in s:
                    val = _extract(s)
                    if val and last_persoon["status"] is None:
                        last_persoon["status"] = val
                    continue

            # --- Dates ---
            if '<datering tag=' in s and "/>" not in s:
                if not buf.get("date_datering"):
                    buf["date_datering"] = _extract(s)
            elif '<zoekmarge_begindatum' in s and "/>" not in s:
                if not buf.get("zoekmarge_begindatum"):
                    buf["zoekmarge_begindatum"] = _extract(s)
            elif '<zoekmarge_einddatum' in s and "/>" not in s:
                if not buf.get("zoekmarge_einddatum"):
                    buf["zoekmarge_einddatum"] = _extract(s)

            # --- Titles ---
            elif '<benaming_kunstwerk' in s and "/>" not in s:
                if not buf.get("title_dutch"):
                    buf["title_dutch"] = _extract(s)
            elif '<titel_engels' in s and "/>" not in s:
                if not buf.get("title_english"):
                    buf["title_english"] = _extract(s)

            # --- Object category (multi-line, English) ---
            elif '<objectcategorie' in s and "linkref" not in s:
                inside_objectcat = True
            elif inside_objectcat and '<value lang="en-US"' in s:
                if not buf.get("objectcat_xml"):
                    buf["objectcat_xml"] = _extract(s)
                inside_objectcat = False
            elif '</objectcategorie>' in s:
                inside_objectcat = False

            # --- Genre (multi-line, English) ---
            elif '<genre tag=' in s:
                inside_genre = True
            elif inside_genre and '<value lang="en-US"' in s:
                if not buf.get("genre"):
                    buf["genre"] = _extract(s)
                inside_genre = False
            elif '</genre>' in s:
                inside_genre = False

            # --- Materiaal (multi-line, English) ---
            elif '<materiaal tag=' in s:
                inside_materiaal = True
            elif inside_materiaal and '<value lang="en-US"' in s:
                val = _extract(s)
                if val:
                    materiaal_list.append(val)
                inside_materiaal = False
            elif '</materiaal>' in s:
                inside_materiaal = False

            # --- Drager (multi-line, English) ---
            elif '<drager tag=' in s:
                inside_drager = True
            elif inside_drager and '<value lang="en-US"' in s:
                if not buf.get("drager"):
                    buf["drager"] = _extract(s)
                inside_drager = False
            elif '</drager>' in s:
                inside_drager = False

            # --- Trefwoorden / keywords (multi-line, English) ---
            elif '<RKD_algemene_trefwoorden ' in s:
                inside_trefwoord     = True
                current_trefwoord_en = None
            elif inside_trefwoord and '<value lang="en-US"' in s:
                current_trefwoord_en = _extract(s)
            elif inside_trefwoord and '</RKD_algemene_trefwoorden>' in s:
                if current_trefwoord_en:
                    trefwoorden_list.append(current_trefwoord_en)
                inside_trefwoord = False

            # --- Identificatie grond (basis of identification) ---
            elif '<identificatie_grond' in s and "/>" not in s and "linkref" not in s:
                val = _extract(s)
                if val:
                    id_grond_list.append(val)

            # --- Artist ---
            elif '<toeschrijving>' in s:
                inside_toeschrijving = True
            elif inside_toeschrijving and '<naam tag="na"' in s and "/>" not in s:
                if not buf.get("artist_name_xml"):
                    buf["artist_name_xml"] = _extract(s)
            elif inside_toeschrijving and '<naam_linkref' in s and "/>" not in s:
                if not buf.get("artist_id"):
                    buf["artist_id"] = _extract(s)
            elif '</toeschrijving>' in s:
                inside_toeschrijving = False

_flush()
print(f"  XML metadata collected for: {len(extra):,} / {len(target_prirefs):,} prirefs")


# ------------------------------------------------------------------
# Step 6 — merge and write training_set.csv
# ------------------------------------------------------------------

print(f"\nWriting {TRAINING_CSV} ...")
with open(TRAINING_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for r in training:
        xtra  = extra.get(r["priref"], {})
        row   = {
            "priref":               r["priref"],
            "lref":                 r["lref"],
            "sitter_id":            r["sitter_ids"],
            "sitter_zekerheid":     xtra.get("sitter_zekerheid", "") or "",
            "sitter_beschrijving":  xtra.get("sitter_beschrijving", "") or "",
            "sitter_status":        xtra.get("sitter_status", "") or "",
            "date_datering":        xtra.get("date_datering", "") or "",
            "zoekmarge_begindatum": xtra.get("zoekmarge_begindatum", "") or "",
            "zoekmarge_einddatum":  xtra.get("zoekmarge_einddatum", "") or "",
            "title_english":        xtra.get("title_english", "") or "",
            "title_dutch":          xtra.get("title_dutch", "") or "",
            "objectcat":            r["objectcat"],
            "genre":                xtra.get("genre", "") or "",
            "materiaal":            xtra.get("materiaal", "") or "",
            "drager":               xtra.get("drager", "") or "",
            "trefwoorden_en":       xtra.get("trefwoorden_en", "") or "",
            "identificatie_grond":  xtra.get("identificatie_grond", "") or "",
            "artist_name":          r["artist_name"],
            "artist_id":            xtra.get("artist_id", "") or "",
            "soort":                r["soort"],
            "is_color":             r["is_color"],
            "width":                r["width"],
            "height":               r["height"],
            "megapixels":           r["megapixels"],
            "path":                 r["path"],
            "face_crop_count":      crop_counts.get(r["lref"], 0),
            "sitter_portrait_count": sitter_portrait_counts[r["sitter_ids"]],
        }
        writer.writerow(row)

print(f"  Rows: {len(training):,}  |  Columns: {len(OUTPUT_FIELDS)}")


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

portrait_dist = Counter(sitter_portrait_counts[r["sitter_ids"]] for r in training)
portrait_dist_sitters = Counter(sitter_portrait_counts.values())

print(f"\n{'='*55}")
print(f"  TRAINING SET SUMMARY")
print(f"{'='*55}")
print(f"  Total portraits:     {len(training):,}")
print(f"  Unique sitters:      {len(multi_sitters):,}")
print(f"\n  Portraits per sitter:")
for n in sorted(portrait_dist_sitters):
    sitters = portrait_dist_sitters[n]
    portraits = n * sitters
    if n <= 15:
        print(f"    {n:>3} portrait(s): {sitters:>5,} sitters  ({portraits:>6,} portraits)")
    elif n == 16:
        tail_s = sum(v for k, v in portrait_dist_sitters.items() if k > 15)
        tail_p = sum(k * v for k, v in portrait_dist_sitters.items() if k > 15)
        print(f"    16+:            {tail_s:>5,} sitters  ({tail_p:>6,} portraits)")
        break
print(f"{'='*55}")
print(f"\n✅ Saved to {TRAINING_CSV}")
print(f"   Load with: import pandas as pd; df = pd.read_csv('{TRAINING_CSV}')")
