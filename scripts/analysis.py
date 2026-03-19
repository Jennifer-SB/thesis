"""
scripts/analysis.py
--------------------
Generates charts and statistics about the RKDimages dataset.
Uses RKDDataset from src/dataset/xml_parser.py.
Saves all plots to the PLOTS_DIR defined in config.py.

Run from the thesis/ root folder:
    python scripts/analysis.py
"""

import sys
import re
from pathlib import Path
from collections import Counter

# Allow imports from thesis/ root
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from config import PLOTS_DIR
from src.dataset.xml_parser import RKDDataset


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def extract_century(date_str: str) -> int | None:
    """Convert a date string to a century number. E.g. '1632' → 17."""
    if not date_str:
        return None
    match = re.search(r'\b(\d{3,4})\b', date_str)
    if match:
        year = int(match.group(1))
        if 1000 <= year <= 2100:
            return ((year - 1) // 100) + 1
    return None


# ------------------------------------------------------------------
# Charts — all take a filtered records dict and a suffix for filenames
# ------------------------------------------------------------------

def chart_centuries(records: dict, suffix: str = "") -> None:
    """
    Two bar charts: artworks per century.
    One using datering (art historian date),
    one using zoekmarge_begindatum (technical search range).
    """
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
                match = re.search(r'\b(\d{3,4})\b', field)
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
            print(f"  ⚠️  No data for {label}, skipping")
            continue

        centuries = sorted(counter.keys())
        counts    = [counter[c] for c in centuries]
        labels    = [f"{c}th" for c in centuries]

        fig, ax = plt.subplots(figsize=(12, 5))
        bars = ax.bar(labels, counts, color=color, edgecolor="white")
        ax.set_title(f"Artworks per century ({label}){suffix}",
                     fontsize=14, fontweight="bold")
        ax.set_xlabel("Century")
        ax.set_ylabel("Number of artworks")
        ax.tick_params(axis='x', rotation=45)
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 20,
                    str(count), ha='center', va='bottom', fontsize=7)
        plt.tight_layout()
        fname = f"chart_centuries_{fname_label}{suffix}.png"
        plt.savefig(PLOTS_DIR / fname, dpi=150)
        plt.close()
        print(f"  ✅ {PLOTS_DIR / fname}")


def chart_object_categories(records: dict, suffix: str = "") -> None:
    """
    Horizontal bar chart: top 15 object categories.
    Full list printed to terminal.
    """
    cat_counts = Counter()
    for rec in records.values():
        cat = rec["objectcat"] or "unknown"
        cat_counts[cat] += 1

    print(f"\n  All object categories{suffix}:")
    for cat, count in cat_counts.most_common():
        print(f"    {cat:<50} {count:>8}")

    top    = cat_counts.most_common(15)
    labels = [t[0] for t in top]
    counts = [t[1] for t in top]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(labels[::-1], counts[::-1], color="#55A868", edgecolor="white")
    ax.set_title(f"Top 15 object categories{suffix}",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of artworks")
    for i, count in enumerate(counts[::-1]):
        ax.text(count + 20, i, str(count), va='center', fontsize=8)
    plt.tight_layout()
    fname = f"chart_objectcategories{suffix}.png"
    plt.savefig(PLOTS_DIR / fname, dpi=150)
    plt.close()
    print(f"  ✅ {PLOTS_DIR / fname}")


def chart_identification_certainty(records: dict, suffix: str = "") -> None:
    """
    Pie chart: certainty of sitter identification.
    Empty zekerheid = certain (no qualifier needed).
    Dutch values: waarschijnlijk=probably, mogelijk=possibly, genaamd=so-called.
    """
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
    ax.pie(counts, labels=labels, autopct='%1.1f%%',
           colors=colors[:len(labels)], startangle=140)
    ax.set_title(f"Identification certainty of sitters{suffix}",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    fname = f"chart_certainty{suffix}.png"
    plt.savefig(PLOTS_DIR / fname, dpi=150)
    plt.close()
    print(f"  ✅ {PLOTS_DIR / fname}")


def chart_multi_sitter(records: dict, suffix: str = "") -> None:
    """
    Bar chart: for artworks with 2+ sitters, how many had all/some/none identified?
    Single-sitter artworks are excluded.
    """
    all_identified  = 0
    some_identified = 0
    none_identified = 0

    for rec in records.values():
        personen = rec["personen"]
        if len(personen) < 2:
            continue
        identified = sum(1 for p in personen if p["nummer"])
        total      = len(personen)
        if identified == total:
            all_identified += 1
        elif identified > 0:
            some_identified += 1
        else:
            none_identified += 1

    total_multi = all_identified + some_identified + none_identified
    print(f"\n  Multi-sitter portraits{suffix}:")
    print(f"    Total:                {total_multi}")
    print(f"    All identified:       {all_identified}")
    print(f"    Some identified:      {some_identified}")
    print(f"    None identified:      {none_identified}")

    labels = ["All identified", "Some identified", "None identified"]
    counts = [all_identified, some_identified, none_identified]
    colors = ["#55A868", "#CCB974", "#C44E52"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, counts, color=colors, edgecolor="white")
    ax.set_title(f"Sitter identification in multi-sitter portraits{suffix}",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Number of artworks")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 10,
                str(count), ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    fname = f"chart_multisitter{suffix}.png"
    plt.savefig(PLOTS_DIR / fname, dpi=150)
    plt.close()
    print(f"  ✅ {PLOTS_DIR / fname}")


def run_charts(records: dict, suffix: str = "") -> None:
    """Run all four charts for a given filtered records dict."""
    chart_centuries(records, suffix)
    chart_object_categories(records, suffix)
    chart_identification_certainty(records, suffix)
    chart_multi_sitter(records, suffix)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    # Parse once, reuse for both filters
    dataset = RKDDataset()
    dataset.parse()

    # Filter 1: all identified portraits (~66k artworks)
    print("\n--- Filter 1: identified portraits ---")
    identified = dataset.filter_records(
        filter_identified=True,
        filter_multi_portrait=False
    )
    run_charts(identified, suffix="_identified")

    # Filter 2: training-ready subset (~47k artworks)
    # Only sitters that appear in 2+ artworks
    print("\n--- Filter 2: identified + multi-portrait sitters ---")
    multi = dataset.filter_records(
        filter_identified=True,
        filter_multi_portrait=True
    )
    run_charts(multi, suffix="_multi")

    print(f"\n✅ All charts saved to {PLOTS_DIR}")