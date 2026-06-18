"""
Experiment configurations.

Atomic configs are passed to run_experiment() for a single run.
Stratified configs (with "stratify_by") are passed to run_stratified_experiment(),
which loops over all unique values of that column and prints a summary table.
"""

# ------------------------------------------------------------------
# RQ1 — Baseline: pre-trained ResNet100 (no fine-tuning)
# ------------------------------------------------------------------

# Full dataset: one overall score
RQ1_full = {
    "experiment_id": "RQ1_full_dataset",
    "description":   "Baseline: full training set",
    "filter":        {},
    "impostor_ratio": 10,
    "seed":          42,
    "model":         "pretrained",
    "save_plots":    True,
    "plot_dir":      "plots/results/RQ1_full_dataset",
}

# RQ1-A: one run per medium group, results in a single table
EXP1_medium = {
    "experiment_id": "EXP1_medium",
    "description":   "Baseline: stratified by medium group",
    "filter":        {},
    "stratify_by":   "medium_group",
    "impostor_ratio": 10,
    "seed":          42,
    "model":         "pretrained",
    "save_plots":    True,
    "plot_dir":      "plots/results/EXP1_medium",
}

# EXP2: cross-medium genuine pairs — same sitter, different medium
EXP2_cross_medium = {
    "experiment_id":  "EXP2_cross_medium",
    "description":    "Cross-medium genuine pairs (baseline model)",
    "medium_col":     "medium_group",
    "combinations":   [                              # ordered by n_genuine (largest first)
        ("Oil paintings", "Prints"),
        ("Oil paintings", "Drawings"),
        ("Oil paintings", "Photographs"),
        ("Drawings",      "Prints"),
        ("Photographs",   "Prints"),
        ("Drawings",      "Photographs"),
    ],
    "impostor_ratio": 10,
    "seed":           42,
    "model":          "pretrained",
    "save_plots":     True,
    "plot_dir":       "plots/results/EXP2_cross_medium",
}

# RQ1-B: one run per artist group, results in a single table
EXP5_artist = {
    "experiment_id": "EXP5_artist",
    "description":   "Baseline: stratified by artist group",
    "filter":        {},
    "stratify_by":   "artist_group",
    "impostor_ratio": 10,
    "seed":          42,
    "model":         "pretrained",
    "save_plots":    True,
    "plot_dir":      "plots/results/EXP5_artist",
}

# ------------------------------------------------------------------
# RQ1-EXP3 — Fine-tuned ResNet100 (same structure, different model)
# Uncomment and set model path once fine-tuned weights are available.
# ------------------------------------------------------------------

# EXP3_medium = {
#     **EXP1_medium,
#     "experiment_id": "EXP3_medium_finetuned",
#     "description":   "Fine-tuned: stratified by medium group",
#     "model":         "path/to/finetuned_weights.pth",
#     "plot_dir":      "plots/results/EXP3_medium_finetuned",
# }

# ------------------------------------------------------------------
# Full list — ordered by priority
# ------------------------------------------------------------------

ALL_EXPERIMENTS = [
    RQ1_full,
    EXP1_medium,
    EXP2_cross_medium,
    EXP5_artist,
]
