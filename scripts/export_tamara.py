"""
Export portraits for Tamara's case study on sitters depicted by multiple artists.

Selects sitters from training_set.csv who meet both criteria:
  - MIN_PORTRAITS : at least this many portraits in the dataset
  - MIN_ARTISTS   : depicted by at least this many distinct artists

Copies full paintings to  OUTPUT_DIR/paintings/{sitter_id}/
Saves metadata CSV to     OUTPUT_DIR/records/metadata_tamara.csv
"""

import shutil
import sys
from pathlib import Path

import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────
MIN_PORTRAITS = 7    # minimum portraits per sitter
MIN_ARTISTS   = 2    # minimum distinct artists per sitter (set to 1 to disable)

OUTPUT_DIR   = Path("D:/TAMANA")
TRAINING_CSV = Path("training_set.csv")

# Images to exclude from public export
CORRUPT_CSV  = Path("csvs/onmyDrive_corrupt_images.csv")   # 555 corrupt images
MISSING_CSV  = Path("csvs/onmyDrive_missing_images.csv")   # 76 undownloadable
PRIVATE_CSV  = Path("lref_filename.csv")                   # 631 privately obtained from RKD (not public)
# ──────────────────────────────────────────────────────────────────────────────


def load_excluded_lrefs() -> set:
    excluded = set()
    for csv_path, col in [
        (CORRUPT_CSV, 'lref'),
        (MISSING_CSV, 'lref'),
        (PRIVATE_CSV, 'recordnummer'),
    ]:
        if csv_path.exists():
            lrefs = pd.read_csv(csv_path)[col].dropna().astype(int).tolist()
            excluded.update(lrefs)
            print(f"  Exclusion list {csv_path.name}: {len(lrefs):,} lrefs")
        else:
            print(f"  Warning: {csv_path} not found, skipping")
    return excluded


def main():
    if not TRAINING_CSV.exists():
        sys.exit(f"training_set.csv not found at {TRAINING_CSV.resolve()}")

    df = pd.read_csv(TRAINING_CSV)
    print(f"Loaded training_set.csv: {len(df):,} portraits, "
          f"{df['sitter_id'].nunique():,} sitters")

    # ── Exclude non-public images ──────────────────────────────────────────────
    print("\nLoading exclusion lists:")
    excluded_lrefs = load_excluded_lrefs()
    before = len(df)
    df = df[~df['lref'].isin(excluded_lrefs)].copy()
    print(f"Excluded {before - len(df):,} non-public portraits "
          f"({len(df):,} remaining)")

    # ── Step 1: sitters with ≥ MIN_PORTRAITS ──────────────────────────────────
    portrait_counts = df.groupby('sitter_id')['lref'].count()
    by_portraits    = set(portrait_counts[portrait_counts >= MIN_PORTRAITS].index)
    print(f"\nSitters with ≥{MIN_PORTRAITS} portraits:            {len(by_portraits):,}")

    # ── Step 2: of those, sitters with ≥ MIN_ARTISTS distinct artists ─────────
    artist_counts = (df[df['sitter_id'].isin(by_portraits)]
                     .groupby('sitter_id')['artist_id']
                     .nunique())
    by_artists = set(artist_counts[artist_counts >= MIN_ARTISTS].index)
    print(f"  …also depicted by ≥{MIN_ARTISTS} distinct artists: {len(by_artists):,}")

    dropped = len(by_portraits) - len(by_artists)
    if dropped:
        print(f"  ({dropped} sitters removed — likely photo studios / single artist)")

    df_out = df[df['sitter_id'].isin(by_artists)].copy()
    print(f"\nTotal portraits to export: {len(df_out):,}")

    # ── Step 3: summary table ─────────────────────────────────────────────────
    summary = (df_out.groupby('sitter_id').agg(
        n_portraits =('lref',                 'count'),
        n_artists   =('artist_id',            'nunique'),
        sitter_name =('sitter_beschrijving',  lambda x: x.dropna().iloc[0] if x.dropna().any() else ''),
        artist_names=('artist_name',          lambda x: ' | '.join(sorted(x.dropna().unique()))),
    ).sort_values('n_artists', ascending=False).reset_index())

    print("\nTop 20 sitters by number of distinct artists:")
    print(summary[['sitter_id', 'sitter_name', 'n_portraits',
                   'n_artists', 'artist_names']].head(20).to_string(index=False))

    # ── Step 4: save metadata CSV ─────────────────────────────────────────────
    records_dir = OUTPUT_DIR / "records"
    if records_dir.exists():
        shutil.rmtree(records_dir)
    records_dir.mkdir(parents=True)
    out_csv = records_dir / "metadata_tamara.csv"
    df_out.to_csv(out_csv, index=False)
    print(f"\nSaved metadata → {out_csv}")

    # ── Step 5: copy paintings ────────────────────────────────────────────────
    paintings_dir = OUTPUT_DIR / "paintings"
    if paintings_dir.exists():
        shutil.rmtree(paintings_dir)
    paintings_dir.mkdir(parents=True)

    copied, missing = 0, 0
    for _, row in df_out.iterrows():
        src = Path(str(row['path']))
        if not src.exists():
            missing += 1
            continue
        sitter_dir = paintings_dir / str(int(row['sitter_id']))
        sitter_dir.mkdir(exist_ok=True)
        dst = sitter_dir / src.name
        shutil.copy2(src, dst)
        copied += 1

    print(f"Copied {copied:,} paintings → {paintings_dir}")
    if missing:
        print(f"Warning: {missing:,} source files not found on disk")

    print(f"\nDone.\n  Paintings : {paintings_dir}\n  Records   : {out_csv}")


if __name__ == "__main__":
    main()
