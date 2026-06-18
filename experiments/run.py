"""
Runs all experiments from definitions.py and saves results to CSV.

Usage (from thesis/ root):
    python experiments/run.py                  # run all experiments
    python experiments/run.py EXP1_medium      # run one specific experiment by id
"""

import sys
import csv
import time
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.embeddings import load_embeddings
from src.evaluation.experiment import (group_media, run_experiment,
                                        run_stratified_experiment,
                                        run_cross_medium_experiment)
from experiments.definitions import ALL_EXPERIMENTS

FEATURES_PKL = Path("features.pkl")

def main():
    # Optional: run only one experiment
    target = sys.argv[1] if len(sys.argv) > 1 else None

    experiments = ALL_EXPERIMENTS
    if target:
        experiments = [e for e in experiments if e["experiment_id"] == target]
        if not experiments:
            print(f"ERROR: no experiment with id '{target}'")
            print("Available:", [e["experiment_id"] for e in ALL_EXPERIMENTS])
            sys.exit(1)

    # Load data:
    df = pd.read_csv("training_set.csv")

    # Add group columns:
    df = group_media(df)

    # Load embeddings:
    embeddings = load_embeddings(FEATURES_PKL)

    # --- Run experiments ---
    results_name = target if target else "all_experiments"
    results_csv  = Path(f"results/{results_name}_results.csv")
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    all_results = []

    for config in experiments:
        t0 = time.time()

        if "stratify_by" in config:
            results = run_stratified_experiment(config, df, embeddings)
            for r in results:
                r["runtime_s"] = round(time.time() - t0, 1)
            all_results.extend(results)
        elif "combinations" in config:
            results = run_cross_medium_experiment(config, df, embeddings)
            for r in results:
                r["runtime_s"] = round(time.time() - t0, 1)
            all_results.extend(results)
        else:
            result = run_experiment(config, df, embeddings)
            result["runtime_s"] = round(time.time() - t0, 1)
            all_results.append(result)

        # Save after each experiment so results aren't lost if something crashes
        _save_results(all_results, results_csv)

    print(f"\nAll done. Results saved to {results_csv}")
    _print_summary(all_results)


def _save_results(results: list, path: Path) -> None:
    if not results:
        return
    # Strip private keys (prefixed with _) — they hold non-serialisable objects like numpy arrays
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    fieldnames = list(clean[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(clean)


def _print_summary(results: list) -> None:
    print(f"\n{'='*80}")
    print(f"  {'Experiment':<35} {'AUC':>7} {'macro_AUC':>10} {'EER':>7} {'TAR@1%':>8}")
    print(f"{'='*80}")
    for r in results:
        if "error" in r:
            print(f"  {r['experiment_id']:<35}  ERROR: {r['error']}")
            continue
        print(f"  {r['experiment_id']:<35} "
              f"{r.get('AUC', '-'):>7} "
              f"{r.get('macro_AUC', '-'):>10} "
              f"{r.get('EER', '-'):>7} "
              f"{r.get('TAR@FAR=0.01', '-'):>8}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
