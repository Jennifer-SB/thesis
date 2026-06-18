"""
- MAIN METHOD: run_experiment(config, df, embeddings): reusable pipeline to run experiments with.
        Takes an settings-dict (experiment details), a pre-loaded df, and embeddings.
        Returns a results dict and saves plots.
- methods to apply medium- and artist group columns.
- method to select the data for each experiment


"""

import numpy as np
import pandas as pd
from pathlib import Path

from src.evaluation.pairs   import build_pairs, build_cross_medium_pairs
from src.evaluation.embeddings import score_pairs
from src.evaluation.metrics import (compute_metrics, plot_score_distribution,
                                    plot_roc_curve, plot_combined_roc_curves)

# Add group-columns (strata) after loading the data:
PHOTO_CATS  = {"carte-de-visite", "cabinet photograph", "photograph", "photomechanical print"}
PRINT_CATS  = {"print", "reproductive print", "book illustration"}
DRAW_CATS   = {"drawing (visual work)"}
PAINT_CATS  = {"painting", "oil sketch", "watercolor (painting)", "portrait miniature"}
SCULPT_CATS = {"sculpture", "bust (sculpture)", "relief", "medal (coin type)",
               "plaquette (sculpture)", "statue", "silhouette"}

# Defining portrait media groups:
def _classify_medium(row) -> str:

    # Read object category and material columns:
    cat = str(row["objectcat"]).lower() if pd.notna(row["objectcat"]) else ""
    mat = str(row["materiaal"]).lower() if pd.notna(row["materiaal"]) else ""

    # Material keyword lists (used both for fallback and oil/drawing distinction):
    oil_mats   = ["oil paint", "grisaille", "alkyd", "acrylic", "tempera", "encaustic"]
    draw_mats  = ["chalk", "pencil", "charcoal", "pastel", "watercolor", "watercolor",
                  "gouache", "aquarelle", "pen", "ink", "graphite", "metalpoint", "metal point"]
    photo_mats = ["albumen", "daguerreotype", "gelatin silver", "collodion", "salt print",
                  "cyanotype", "platinum", "carbon print", "photography", "vignetting"]
    print_mats = ["engraving", "etching", "lithograph", "woodcut", "mezzotint", "aquatint",
                  "stipple", "drypoint", "dry point", "heliograph", "zincograph", "collotype"]

    # OBJECT CATEGORY FIRST (priority order):

    # Photographs:
    if any(c in cat for c in ["carte-de-visite", "cabinet photograph", "photomechanical print"]):
        return "Photographs"
    if cat.strip() == "photograph":
        return "Photographs"

    # Portrait miniatures:
    if "portrait miniature" in cat:
        return "Portrait miniatures"

    # Sculpture/3D:
    if any(c in cat for c in ["sculpture", "relief", "medal", "plaquette", "statue", "bust"]):
        return "Sculpture"

    # Prints & engravings (includes reproductive print):
    if any(c in cat for c in ["print", "reproductive print", "book illustration"]):
        return "Prints"

    # Drawings:
    if "drawing" in cat:
        return "Drawings"

    # Use material to distinguishbetween oil paintings and drawings:
    if any(c in cat for c in ["painting", "oil sketch"]):
        if any(m in mat for m in oil_mats):
            return "Oil paintings"
        if any(m in mat for m in draw_mats):
            return "Drawings"
        
        # No material recorded, then oil painting:
        # Decision based on manual inspection (with the eye) of paintings without material recorded,
        # holds for our RKD-subset:
        return "Oil paintings"

    # MATERIAL NEXT:
    if any(m in mat for m in photo_mats): return "Photographs"
    if any(m in mat for m in print_mats): return "Prints"
    if any(m in mat for m in draw_mats):  return "Drawings"
    if any(m in mat for m in oil_mats):   return "Oil paintings"

    # if nothing noted:
    return "Other"


def _classify_artist_group(artist: str, objectcats: pd.Series) -> str:
    # If the artist is unknown:
    if artist == "Anoniem":
        return "Anoniem"
    n = len(objectcats)

    # No classified artworks:
    if n == 0:
        return "Other"
    
    # Decide what is the dominant object category:
    pct_photo  = objectcats.isin(PHOTO_CATS).sum()  / n
    pct_print  = objectcats.isin(PRINT_CATS).sum()  / n
    pct_draw   = objectcats.isin(DRAW_CATS).sum()   / n
    pct_paint  = objectcats.isin(PAINT_CATS).sum()  / n
    pct_sculpt = objectcats.isin(SCULPT_CATS).sum() / n
    
    scores = {
        "Photo studio": pct_photo,
        "Painter":      pct_paint,
        "Printmaker":   pct_print,
        "Draughtsman":  pct_draw,
        "Sculptor":     pct_sculpt,
    }

    dominant, pct = max(scores.items(), key=lambda x: x[1])
    return dominant if pct >= 0.40 else "Mixed"


def group_media(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add medium_group and artist_group columns to training_set DataFrame.
    Call once after loading; pass the groupeded df to all experiments.
    """
    df = df.copy()
    df["artist_name"] = df["artist_name"].str.replace("&amp;", "&", regex=False)

    # For each row (artwork), classify to a certain medium:
    df["medium_group"] = df.apply(_classify_medium, axis=1)

    artist_groups = {}
    for artist, grp in df.groupby("artist_name"):
        artist_groups[artist] = _classify_artist_group(artist, grp["objectcat"])
    df["artist_group"] = df["artist_name"].map(artist_groups)

    return df

def apply_filter(df: pd.DataFrame, filter_spec: dict) -> pd.DataFrame:
    """
    For all the different experiment we need different subgroups from the data,
    this function selects these subgroups by applying a filter over the dataframe.
    Based on the filter_spec dictionary, some rows are included, others excluded.
    
    filter_spec examples:
        {}                                    no filter, full dataset
        {"medium_group": "Oil paintings"}     single value
        {"medium_group": ["Oil paintings",    multiple allowed values
                          "Prints"]}          
        {"artist_group": "Painter",
         "medium_group": "Oil paintings"}     multiple conditions (AND)
    """

    # Complete dataset needed:
    if not filter_spec:
        return df
    
    # If filter dict given, apply all filters over the df rows (logical &):
    mask = pd.Series([True] * len(df), index=df.index)
    # For each key-value pair in the dict:
    for col, val in filter_spec.items():
        # If val = list: check if the row's value is any of those options
        if isinstance(val, list):
            mask &= df[col].isin(val)
        # If val = value: check for exact value
        else:
            mask &= (df[col] == val)
    return df[mask].copy()


def run_experiment(config: dict, df: pd.DataFrame, embeddings: dict) -> dict:
    """
    Run one experiment end-to-end.

    Args:
        config:     atomic experiment config dict (see experiments/definitions.py)
        df:         enriched training_set DataFrame (from group_media())
        embeddings: dict {lref: embedding} (from load_embeddings())

    Returns:
        results dict with metrics + config info
    """

    exp_id  = config["experiment_id"]
    print(f"\n{'='*60}")
    print(f"  {exp_id}")
    print(f"{'='*60}")

    # Filter the dataset:
    subset = apply_filter(df, config.get("filter", {}))
    print(f"  Portraits after filter: {len(subset):,} "
          f"({subset['sitter_id'].nunique():,} sitters)")

    if len(subset) < 10:
        print("  SKIP: too few portraits after filter")
        return {"experiment_id": exp_id, "error": "too few portraits"}

    # Build pairs: 
    pairs = build_pairs(
        subset,
        impostor_ratio=config.get("impostor_ratio", 10),
        seed=config.get("seed", 42),
    )

    # Score pairs:
    scores, labels = score_pairs(pairs, embeddings)

    if len(scores) == 0:
        print("  SKIP: no scoreable pairs (embeddings missing?)")
        return {"experiment_id": exp_id, "error": "no scoreable pairs"}

    # Results: compute metrics:
    metrics, roc_data = compute_metrics(scores, labels, pairs=pairs)
    fpr, tpr, thresholds = roc_data

    print(f"  AUC:          {metrics['AUC']}")
    print(f"  macro_AUC:    {metrics['macro_AUC']}  "
          f"(over {metrics['macro_AUC_n_sitters']} sitters)")
    print(f"  EER:          {metrics['EER']}")
    print(f"  TAR@FAR=0.01: {metrics['TAR@FAR=0.01']}")

    # Save plots:
    if config.get("save_plots", True):
        plot_dir = Path(config.get("plot_dir", f"plots/results/{exp_id}"))
        plot_dir.mkdir(parents=True, exist_ok=True)
        title = config.get("description", exp_id)
        plot_score_distribution(
            scores, labels,
            save_path=plot_dir / "score_distribution.png",
            title=f"Score distribution — {title}",
            eer_threshold=metrics["EER_threshold"],
        )
        plot_roc_curve(
            fpr, tpr, thresholds, metrics,
            save_path=plot_dir / "roc_curve.png",
            title=f"ROC curve — {title}",
        )

    return {
        "experiment_id":   exp_id,
        "description":     config.get("description", ""),
        "n_portraits":     len(subset),
        "n_sitters":       subset["sitter_id"].nunique(),
        **metrics,
        "_roc":            (fpr, tpr),   # stripped before CSV save, used for combined plot
    }


def run_stratified_experiment(config: dict, df: pd.DataFrame, embeddings: dict) -> list:
    """
    Run one experiment across all strata of a column and print a summary table.

    Expects config to have a "stratify_by" key naming a column in df (e.g. "medium_group").
    Runs run_experiment() once per stratum value, then prints results side-by-side.

    Returns:
        list of result dicts, one per stratum
    """
    col    = config["stratify_by"]
    strata = sorted(df[col].dropna().unique())

    all_results = []
    for stratum in strata:
        slug = stratum.lower().replace(" ", "_").replace("/", "_")
        sub_config = {
            **config,
            "experiment_id": f"{config['experiment_id']}_{slug}",
            "description":   f"{config.get('description', '')} — {stratum}",
            "filter":        {**config.get("filter", {}), col: stratum},
            "plot_dir":      f"{config.get('plot_dir', 'plots/results')}/{slug}",
        }
        result = run_experiment(sub_config, df, embeddings)
        result["stratum"] = stratum
        all_results.append(result)

    # Sort by number of portraits, largest first
    all_results.sort(key=lambda r: r.get("n_portraits", 0), reverse=True)

    # Combined ROC curve
    if config.get("save_plots", True):
        roc_entries = [
            {"label": r["stratum"], "fpr": r["_roc"][0], "tpr": r["_roc"][1],
             "auc": r["AUC"], "eer": r["EER"]}
            for r in all_results if "_roc" in r
        ]
        plot_dir = Path(config.get("plot_dir", "plots/results"))
        plot_combined_roc_curves(
            roc_entries,
            save_path=plot_dir / "roc_curves_combined.png",
            title=f"ROC curves — {config.get('description', config['experiment_id'])}",
        )

    # Summary table
    print(f"\n{'='*93}")
    print(f"  STRATIFIED RESULTS — {config['experiment_id']}")
    print(f"{'='*93}")
    header = f"  {'Stratum':<24} {'Portraits':>10} {'Sitters':>8} {'AUC':>7} {'EER':>7} {'TAR@1%':>7} {'TAR@0.1%':>9} {'macro_AUC':>10}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        if "error" in r:
            print(f"  {r['stratum']:<24}  SKIPPED: {r['error']}")
            continue
        macro = f"{r['macro_AUC']:.4f}" if r["macro_AUC"] is not None else "N/A"
        print(
            f"  {r['stratum']:<24} {r['n_portraits']:>10,} {r['n_sitters']:>8,} "
            f"{r['AUC']:>7.4f} {r['EER']:>7.4f} {r['TAR@FAR=0.01']:>7.4f} "
            f"{r['TAR@FAR=0.001']:>9.4f} {macro:>10}"
        )

    return all_results


def run_cross_medium_experiment(config: dict, df: pd.DataFrame, embeddings: dict) -> list:
    """
    Run EXP2: evaluate on cross-medium genuine pairs for every specified medium combination.

    Config must have:
        combinations: list of (medium_a, medium_b) tuples
        medium_col:   column name for medium (default "medium_group")

    For each combination:
        Genuine  = same sitter, portrait_a from medium_a, portrait_b from medium_b
        Impostor = different sitter, one portrait from each medium

    Returns:
        list of result dicts, one per combination, sorted by n_genuine descending
    """
    exp_id     = config["experiment_id"]
    medium_col = config.get("medium_col", "medium_group")

    print(f"\n{'='*60}")
    print(f"  {exp_id}  (cross-medium genuine pairs)")
    print(f"{'='*60}")

    all_results = []
    for medium_a, medium_b in config["combinations"]:
        label = f"{medium_a} × {medium_b}"
        slug  = (f"{medium_a.lower().replace(' ', '_')}"
                 f"_x_{medium_b.lower().replace(' ', '_')}")

        pairs = build_cross_medium_pairs(
            df, medium_col, medium_a, medium_b,
            impostor_ratio=config.get("impostor_ratio", 10),
            seed=config.get("seed", 42),
        )

        if not pairs:
            all_results.append({"combination": label, "error": "no pairs built"})
            continue

        scores, labels = score_pairs(pairs, embeddings)
        if len(scores) == 0:
            all_results.append({"combination": label, "error": "no scoreable pairs"})
            continue

        metrics, roc_data = compute_metrics(scores, labels, pairs=pairs)
        fpr, tpr, thresholds = roc_data

        if config.get("save_plots", True):
            plot_dir = Path(config.get("plot_dir", f"plots/results/{exp_id}")) / slug
            plot_dir.mkdir(parents=True, exist_ok=True)
            plot_score_distribution(
                scores, labels,
                save_path=plot_dir / "score_distribution.png",
                title=f"Score distribution — {label}",
                eer_threshold=metrics["EER_threshold"],
            )
            plot_roc_curve(
                fpr, tpr, thresholds, metrics,
                save_path=plot_dir / "roc_curve.png",
                title=f"ROC curve — {label}",
            )

        all_results.append({
            "experiment_id": f"{exp_id}_{slug}",
            "combination":   label,
            **metrics,
            "_roc":          (fpr, tpr),
        })

    # Sort by number of genuine pairs, largest first
    all_results.sort(key=lambda r: r.get("n_genuine", 0), reverse=True)

    # Combined ROC curve
    if config.get("save_plots", True):
        roc_entries = [
            {"label": r["combination"], "fpr": r["_roc"][0], "tpr": r["_roc"][1],
             "auc": r["AUC"], "eer": r["EER"]}
            for r in all_results if "_roc" in r
        ]
        plot_dir = Path(config.get("plot_dir", "plots/results"))
        plot_combined_roc_curves(
            roc_entries,
            save_path=plot_dir / "roc_curves_combined.png",
            title=f"ROC curves — {config.get('description', exp_id)}",
        )

    # Summary table
    print(f"\n{'='*97}")
    print(f"  CROSS-MEDIUM RESULTS — {exp_id}")
    print(f"{'='*97}")
    header = f"  {'Combination':<32} {'Genuine':>8} {'Impostor':>9} {'AUC':>7} {'EER':>7} {'TAR@1%':>7} {'TAR@0.1%':>9} {'macro_AUC':>10}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        if "error" in r:
            print(f"  {r['combination']:<32}  SKIPPED: {r['error']}")
            continue
        macro = f"{r['macro_AUC']:.4f}" if r["macro_AUC"] is not None else "N/A"
        print(
            f"  {r['combination']:<32} {r['n_genuine']:>8,} {r['n_impostor']:>9,} "
            f"{r['AUC']:>7.4f} {r['EER']:>7.4f} {r['TAR@FAR=0.01']:>7.4f} "
            f"{r['TAR@FAR=0.001']:>9.4f} {macro:>10}"
        )

    return all_results
