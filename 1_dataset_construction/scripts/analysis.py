"""
scripts/analysis.py
--------------------
Generates charts and statistics about the RKDimages dataset.

Filter 1 & 2: read from RKDimages.xml via RKDDataset.
Filter 3:     read from training_set.csv (27k final training set).
              Run this section alone with:  python scripts/analysis.py --training-only

All plots saved to PLOTS_DIR (config.py).

Run from the thesis/ root folder:
    python scripts/analysis.py
    python scripts/analysis.py --training-only
"""

import sys
import re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import PLOTS_DIR

TRAINING_CSV   = Path("training_set.csv")
TRAINING_ONLY  = "--training-only" in sys.argv


# ==================================================================
# Shared helper
# ==================================================================

def extract_century(date_str: str) -> int | None:
    """Convert a date string to a century number. E.g. '1632' → 17."""
    if not date_str:
        return None
    match = re.search(r"\b(\d{3,4})\b", date_str)
    if match:
        year = int(match.group(1))
        if 1000 <= year <= 2100:
            return ((year - 1) // 100) + 1
    return None


# ==================================================================
# Charts — XML record dicts  (Filters 1 & 2)
# ==================================================================

def chart_centuries(records: dict, suffix: str = "") -> None:
    century_datering  = Counter()
    century_zoekmarge = Counter()
    earliest = (9999, None)
    latest   = (0, None)

    for priref, rec in records.items():
        for field, counter in [
            (rec["date_datering"],  century_datering),
            (rec["date_zoekmarge"], century_zoekmarge),
        ]:
            if field:
                century = extract_century(field)
                if century:
                    counter[century] += 1
                match = re.search(r"\b(\d{3,4})\b", field)
                if match:
                    year = int(match.group(1))
                    if 1000 <= year <= 2100:
                        if year < earliest[0]:
                            earliest = (year, priref)
                        if year > latest[0]:
                            latest = (year, priref)

    print(f"   Earliest artwork: {earliest[0]} (priref {earliest[1]})")
    print(f"   Latest artwork:   {latest[0]} (priref {latest[1]})")

    for counter, label, fname_label, color in [
        (century_datering,  "datering",            "datering",  "#4C72B0"),
        (century_zoekmarge, "zoekmarge_begindatum", "zoekmarge", "#C44E52"),
    ]:
        if not counter:
            print(f"  No data for {label}, skipping")
            continue
        centuries = sorted(counter.keys())
        counts    = [counter[c] for c in centuries]
        labels    = [f"{c}th" for c in centuries]
        fig, ax = plt.subplots(figsize=(12, 5))
        bars = ax.bar(labels, counts, color=color, edgecolor="white")
        ax.set_title(f"Artworks per century ({label}){suffix}", fontsize=14, fontweight="bold")
        ax.set_xlabel("Century")
        ax.set_ylabel("Number of artworks")
        ax.tick_params(axis="x", rotation=45)
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 20,
                    str(count), ha="center", va="bottom", fontsize=7)
        plt.tight_layout()
        fname = PLOTS_DIR / f"chart_centuries_{fname_label}{suffix}.png"
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"  {fname}")


def chart_object_categories(records: dict, suffix: str = "") -> None:
    cat_counts = Counter(rec["objectcat"] or "unknown" for rec in records.values())
    print(f"\n  All object categories{suffix}:")
    for cat, count in cat_counts.most_common():
        print(f"    {cat:<50} {count:>8}")
    top    = cat_counts.most_common(15)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(labels[::-1], counts[::-1], color="#55A868", edgecolor="white")
    ax.set_title(f"Top 15 object categories{suffix}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of artworks")
    for i, count in enumerate(counts[::-1]):
        ax.text(count + 20, i, str(count), va="center", fontsize=8)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_objectcategories{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_identification_certainty(records: dict, suffix: str = "") -> None:
    certainty_counts = Counter()
    for rec in records.values():
        for p in rec["personen"]:
            if p["nummer"]:
                z = p["zekerheid"] or "certain (no qualifier)"
                certainty_counts[z] += 1
    print(f"\n  Identification certainty{suffix}:")
    for z, count in certainty_counts.most_common():
        print(f"    {z:<40} {count:>8}")
    labels = list(certainty_counts.keys())
    counts = list(certainty_counts.values())
    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD"]
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(counts, labels=labels, autopct="%1.1f%%",
           colors=colors[:len(labels)], startangle=140)
    ax.set_title(f"Identification certainty of sitters{suffix}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_certainty{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_multi_sitter(records: dict, suffix: str = "") -> None:
    all_id, some_id, none_id = 0, 0, 0
    for rec in records.values():
        personen   = rec["personen"]
        if len(personen) < 2:
            continue
        identified = sum(1 for p in personen if p["nummer"])
        if identified == len(personen):
            all_id  += 1
        elif identified > 0:
            some_id += 1
        else:
            none_id += 1
    total = all_id + some_id + none_id
    print(f"\n  Multi-sitter portraits{suffix}:  {total}")
    labels = ["All identified", "Some identified", "None identified"]
    counts = [all_id, some_id, none_id]
    colors = ["#55A868", "#CCB974", "#C44E52"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, counts, color=colors, edgecolor="white")
    ax.set_title(f"Sitter identification in multi-sitter portraits{suffix}",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Number of artworks")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 10,
                str(count), ha="center", va="bottom", fontsize=10)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_multisitter{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def run_charts(records: dict, suffix: str = "") -> None:
    chart_centuries(records, suffix)
    chart_object_categories(records, suffix)
    chart_identification_certainty(records, suffix)
    chart_multi_sitter(records, suffix)


# ==================================================================
# Charts — training_set.csv DataFrame  (Filter 3)
# ==================================================================

# Warm autumn palette used for all training-set charts.
AUTUMN_DARK_RED     = "#8B1A1A"
AUTUMN_ORANGE       = "#D2691E"
AUTUMN_DARK_ORANGE  = "#CC5500"
AUTUMN_DARK_YELLOW  = "#B8860B"
AUTUMN_BURNT_SIENNA = "#A0522D"
AUTUMN_MAROON       = "#800000"
AUTUMN_AMBER        = "#C68E17"
AUTUMN_PALETTE      = [AUTUMN_DARK_RED, AUTUMN_ORANGE, AUTUMN_DARK_YELLOW,
                        AUTUMN_BURNT_SIENNA, AUTUMN_MAROON, AUTUMN_AMBER,
                        AUTUMN_DARK_ORANGE]

AXIS_LABEL_FONTSIZE = 13
TICK_LABEL_FONTSIZE = 11


def _style_axes(ax, xlabel=None, ylabel=None):
    """Apply consistent, larger axis-label / tick-label sizing."""
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=AXIS_LABEL_FONTSIZE)
    if ylabel is not None:
        ax.set_ylabel(ylabel, fontsize=AXIS_LABEL_FONTSIZE)
    ax.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE)


def _bar(ax, labels, counts, color, fontsize=8):
    bars = ax.bar(labels, counts, color=color, edgecolor="white")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(counts) * 0.01,
                str(count), ha="center", va="bottom", fontsize=fontsize)


def chart_centuries_training(df, suffix: str = "") -> None:
    """
    Three charts:
      1. Century from datering (art historian date, free-text)
      2. Century from zoekmarge midpoint (clean year range → midpoint)
      3. Year distribution within 15th–20th century (zoekmarge midpoint)
    """
    import pandas as pd

    # 1. datering free-text
    c_datering = Counter()
    for val in df["date_datering"].dropna():
        c = extract_century(str(val))
        if c:
            c_datering[c] += 1

    # 2 & 3. zoekmarge midpoint
    begin = pd.to_numeric(df["zoekmarge_begindatum"], errors="coerce")
    end   = pd.to_numeric(df["zoekmarge_einddatum"],  errors="coerce")
    mid   = ((begin + end) / 2).dropna()

    c_mid = Counter(int((y - 1) // 100) + 1 for y in mid if 1000 <= y <= 2100)

    for counter, label, fname_label, color in [
        (c_datering, "datering (free-text)",    "datering",  AUTUMN_DARK_RED),
        (c_mid,      "zoekmarge midpoint year", "zoekmarge", AUTUMN_ORANGE),
    ]:
        if not counter:
            continue
        centuries = sorted(counter.keys())
        counts    = [counter[c] for c in centuries]
        labels    = [f"{c}th" for c in centuries]
        fig, ax = plt.subplots(figsize=(12, 5))
        _bar(ax, labels, counts, color, fontsize=7)
        ax.set_title(f"Training set: artworks per century ({label})",
                     fontsize=14, fontweight="bold")
        _style_axes(ax, xlabel="Century", ylabel="Portraits")
        ax.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        fname = PLOTS_DIR / f"chart_centuries_{fname_label}{suffix}.png"
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"  {fname}")

    # Year-level distribution (25-year buckets, zoekmarge midpoint)
    valid_mid = [y for y in mid if 1400 <= y <= 1950]
    buckets   = Counter(int(y // 25) * 25 for y in valid_mid)
    years     = sorted(buckets.keys())
    counts    = [buckets[y] for y in years]
    labels    = [str(y) for y in years]
    fig, ax = plt.subplots(figsize=(16, 5))
    _bar(ax, labels, counts, AUTUMN_DARK_YELLOW, fontsize=9)
    ax.set_title("Training set: portraits per 25-year period",
                 fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Year (25-year bins)", ylabel="Portraits")
    ax.tick_params(axis="x", rotation=90)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_years_25yr{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_object_categories_training(df, suffix: str = "") -> None:
    cat_counts = Counter(df["objectcat"].fillna("unknown"))
    print(f"\n  Object categories{suffix}:")
    for cat, count in cat_counts.most_common():
        print(f"    {cat:<50} {count:>8}")
    top    = cat_counts.most_common(15)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(labels[::-1], counts[::-1], color=AUTUMN_DARK_RED, edgecolor="white")
    ax.set_title("Training set: top 15 object categories",
                 fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Number of portraits")
    for i, count in enumerate(counts[::-1]):
        ax.text(count + 20, i, str(count), va="center", fontsize=11)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_objectcategories{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_certainty_training(df, suffix: str = "") -> None:
    certainty = df["sitter_zekerheid"].fillna("").replace("", "certain (no qualifier)")
    counts_map = Counter(certainty)
    print(f"\n  Identification certainty{suffix}:")
    for z, count in counts_map.most_common():
        print(f"    {z:<40} {count:>8}")
    labels = list(counts_map.keys())
    counts = list(counts_map.values())
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(counts, labels=labels, autopct="%1.1f%%",
           colors=AUTUMN_PALETTE[:len(labels)], startangle=140)
    ax.set_title("Training set: identification certainty",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_certainty{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_portraits_per_sitter(df, suffix: str = "") -> None:
    """How many sitters have exactly N portraits in the training set."""
    sitter_counts = df.drop_duplicates("sitter_id")["sitter_portrait_count"]
    dist = Counter(sitter_counts)

    # Bin 11+ together
    labels, counts = [], []
    for n in sorted(dist.keys()):
        if n <= 10:
            labels.append(str(n))
            counts.append(dist[n])
        else:
            break
    tail = sum(v for k, v in dist.items() if k > 10)
    if tail:
        labels.append("11+")
        counts.append(tail)

    fig, ax = plt.subplots(figsize=(10, 5))
    _bar(ax, labels, counts, AUTUMN_DARK_ORANGE, fontsize=9)
    ax.set_title("Training set: sitters by portrait count",
                 fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Number of portraits per sitter", ylabel="Number of sitters")
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_portraits_per_sitter{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")

    total_sitters   = df["sitter_id"].nunique()
    total_portraits = len(df)
    print(f"  Sitters: {total_sitters:,}  |  Portraits: {total_portraits:,}  "
          f"|  Avg: {total_portraits / total_sitters:.1f}")


def chart_genre_training(df, suffix: str = "") -> None:
    genre_counts = Counter(df["genre"].fillna("unknown").replace("", "unknown"))
    print(f"\n  Genre{suffix}:")
    for g, count in genre_counts.most_common():
        print(f"    {g:<50} {count:>8}")
    top    = genre_counts.most_common(10)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.barh(labels[::-1], counts[::-1], color=AUTUMN_MAROON, edgecolor="white")
    ax.set_title("Training set: top genres", fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Number of portraits")
    for i, count in enumerate(counts[::-1]):
        ax.text(count + 20, i, str(count), va="center", fontsize=8)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_genre{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_materiaal_training(df, suffix: str = "") -> None:
    """Parse pipe-separated materials and count each material individually."""
    mat_counts = Counter()
    for val in df["materiaal"].dropna():
        for m in str(val).split("|"):
            m = m.strip()
            if m:
                mat_counts[m] += 1
    print(f"\n  Top materials{suffix}:")
    for m, count in mat_counts.most_common(20):
        print(f"    {m:<50} {count:>8}")
    top    = mat_counts.most_common(15)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(labels[::-1], counts[::-1], color=AUTUMN_ORANGE, edgecolor="white")
    ax.set_title("Training set: top 15 materials", fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Number of portraits")
    for i, count in enumerate(counts[::-1]):
        ax.text(count + 20, i, str(count), va="center", fontsize=11)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_materiaal{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_drager_training(df, suffix: str = "") -> None:
    drager_counts = Counter(df["drager"].fillna("unknown").replace("", "unknown"))
    print(f"\n  Support (drager){suffix}:")
    for d, count in drager_counts.most_common():
        print(f"    {d:<50} {count:>8}")
    top    = drager_counts.most_common(12)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]
    fig, ax = plt.subplots(figsize=(10, 5))
    _bar(ax, labels, counts, AUTUMN_DARK_YELLOW, fontsize=8)
    ax.set_title("Training set: support material (drager)",
                 fontsize=14, fontweight="bold")
    _style_axes(ax, xlabel="Support", ylabel="Number of portraits")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_drager{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")


def chart_color_training(df, suffix: str = "") -> None:
    color_counts = Counter(df["is_color"].map(
        lambda v: "color" if str(v).lower() in ("true", "1") else "B&W / other"
    ))
    labels = list(color_counts.keys())
    counts = list(color_counts.values())
    colors = [AUTUMN_DARK_RED, AUTUMN_DARK_YELLOW]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts, labels=labels, autopct="%1.1f%%",
           colors=colors[:len(labels)], startangle=90)
    ax.set_title("Training set: color vs B&W scan",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    fname = PLOTS_DIR / f"chart_color{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  {fname}")
    for label, count in color_counts.items():
        print(f"    {label}: {count:,}")


def run_charts_training(df, suffix: str = "") -> None:
    """Run all training-set charts for a given DataFrame."""
    chart_centuries_training(df, suffix)
    chart_object_categories_training(df, suffix)
    chart_certainty_training(df, suffix)
    chart_portraits_per_sitter(df, suffix)
    chart_genre_training(df, suffix)
    chart_materiaal_training(df, suffix)
    chart_drager_training(df, suffix)
    chart_color_training(df, suffix)


# ==================================================================
# Main
# ==================================================================

if __name__ == "__main__":

    # ------------------------------------------------------------------
    # Filter 3: 27k training set — from training_set.csv (no XML needed)
    # ------------------------------------------------------------------
    print("\n--- Filter 3: 27k training set (from training_set.csv) ---")
    if not TRAINING_CSV.exists():
        print(f"  ERROR: {TRAINING_CSV} not found — run scripts/build_training_table.py first")
    else:
        import pandas as pd
        df_training = pd.read_csv(TRAINING_CSV)
        print(f"  Loaded {len(df_training):,} rows, {len(df_training.columns)} columns")
        run_charts_training(df_training, suffix="_training")

    if TRAINING_ONLY:
        print(f"\nTraining charts saved to {PLOTS_DIR}")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Filter 1 & 2: full dataset — requires RKDimages.xml
    # ------------------------------------------------------------------
    from src.dataset.xml_parser import RKDDataset

    dataset = RKDDataset()
    dataset.parse()

    print("\n--- Filter 1: identified portraits ---")
    identified = dataset.filter_records(filter_identified=True, filter_multi_portrait=False)
    run_charts(identified, suffix="_identified")

    print("\n--- Filter 2: identified + multi-portrait sitters ---")
    multi = dataset.filter_records(filter_identified=True, filter_multi_portrait=True)
    run_charts(multi, suffix="_multi")

    print(f"\nAll charts saved to {PLOTS_DIR}")
