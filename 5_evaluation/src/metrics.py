"""
Computes face verification metrics and generates plots.
AUC                     standard (pooled pairs)
macro_AUC               per-sitter AUC averaged across sitters
EER                     Equal Error Rate: threshold where FAR == FNR
TAR@FAR=0.01            True Accept Rate at 1% False Accept Rate
TAR@FAR=0.001           True Accept Rate at 0.1% False Accept Rate
score_distribution plot genuine vs impostor cosine similarity histograms
roc_curve               ROC curve with AUC and EER marked
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import roc_curve, auc


def _eer(fpr, tpr, thresholds):
    """Equal Error Rate: point where FPR is equal to FNR (= 1 - TPR)."""
    # false negative rate:
    fnr = 1.0 - tpr

    # find index on the roc curve where fpr and fnr are closest:
    idx = np.argmin(np.abs(fpr - fnr))

    # average fpr and fnr at closest point and return decision threshold at that point:
    eer = float((fpr[idx] + fnr[idx]) / 2)
    return eer, float(thresholds[idx])


def _tar_at_far(fpr, tpr, thresholds, target_far):
    """TAR (TPR) at the highest threshold where FAR lower or equal to target_far."""
    # all points on roc curve where FAR <= target FAR:
    valid = np.where(fpr <= target_far)[0]
    if len(valid) == 0:
        return 0.0, None
    # last valid index where FAR <= target, giving highest TAR:
    idx = valid[-1]
    return float(tpr[idx]), float(thresholds[idx])


def _per_sitter_auc(scores, labels, sitter_ids_a, sitter_ids_b):
    """
    Macro-averaged AUC: compute AUC per sitter, average across sitters.
    For each sitter i:
        genuine  = pairs where sitter_id_a == sitter_id_b == i
        impostor = pairs where sitter_id_a == i OR sitter_id_b == i (but not genuine)
    Sitters with no genuine pair or no impostor pair are skipped.
    """
    scores       = np.array(scores)
    labels       = np.array(labels)
    sitter_ids_a = np.array(sitter_ids_a)
    sitter_ids_b = np.array(sitter_ids_b)

    # collect all sitter IDs that are part of a genuine pair:
    genuine_sitters = set(sitter_ids_a[labels == 1])
    per_sitter = []


    for sid in genuine_sitters:
        gen_mask = (labels == 1) & (sitter_ids_a == sid)
        imp_mask = (labels == 0) & ((sitter_ids_a == sid) | (sitter_ids_b == sid))

        if gen_mask.sum() < 1 or imp_mask.sum() < 1:
            continue

        s = np.concatenate([scores[gen_mask], scores[imp_mask]])
        l = np.concatenate([np.ones(gen_mask.sum()), np.zeros(imp_mask.sum())])

        if len(np.unique(l)) < 2:
            continue
        try:
            fpr_s, tpr_s, _ = roc_curve(l, s, pos_label=1)
            per_sitter.append(auc(fpr_s, tpr_s))
        except Exception:
            continue

    if not per_sitter:
        return None
    return float(np.mean(per_sitter)), len(per_sitter)


def compute_metrics(scores, labels, pairs=None):
    """
    Compute all verification metrics.

    Args:
        scores:  array-like of cosine similarity scores
        labels:  array-like of 1 (genuine) or 0 (impostor)
        pairs:   optional list of (lref_a, lref_b, label, sitter_id_a, sitter_id_b)
                 — required for macro_AUC

    Returns:
        metrics:       dict of metric values
        roc_data:      (fpr, tpr, thresholds) for plotting
    """
    scores = np.array(scores, dtype=float)
    labels = np.array(labels, dtype=int)

    fpr, tpr, thresholds = roc_curve(labels, scores, pos_label=1)
    auc_score            = auc(fpr, tpr)
    eer, eer_thresh      = _eer(fpr, tpr, thresholds)
    tar_01, _            = _tar_at_far(fpr, tpr, thresholds, target_far=0.01)
    tar_001, _           = _tar_at_far(fpr, tpr, thresholds, target_far=0.001)

    metrics = {
        "n_genuine":      int(labels.sum()),
        "n_impostor":     int((labels == 0).sum()),
        "AUC":            round(auc_score, 4),
        "EER":            round(eer, 4),
        "EER_threshold":  round(eer_thresh, 4),
        "TAR@FAR=0.01":   round(tar_01, 4),
        "TAR@FAR=0.001":  round(tar_001, 4),
        "macro_AUC":      None,
        "macro_AUC_n_sitters": None,
    }

    if pairs is not None:
        sitter_ids_a = [p[3] for p in pairs if len(p) >= 5]
        sitter_ids_b = [p[4] for p in pairs if len(p) >= 5]
        # Only use pairs that were not skipped (same length as scores)
        sitter_ids_a = sitter_ids_a[:len(scores)]
        sitter_ids_b = sitter_ids_b[:len(scores)]
        result = _per_sitter_auc(scores, labels, sitter_ids_a, sitter_ids_b)
        if result is not None:
            macro, n_sitters = result
            metrics["macro_AUC"]          = round(macro, 4)
            metrics["macro_AUC_n_sitters"] = n_sitters

    return metrics, (fpr, tpr, thresholds)


def plot_score_distribution(scores, labels, save_path, title="Score Distribution",
                            eer_threshold=None):
    """
    Histogram of cosine similarity scores for genuine vs impostor pairs.
    Shows how well separated the two distributions are.
    """
    scores   = np.array(scores)
    labels   = np.array(labels)
    genuine  = scores[labels == 1]
    impostor = scores[labels == 0]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(impostor, bins=80, density=True, alpha=0.6,
            color="#E87D27", label=f"Impostor (n={len(impostor):,})")
    ax.hist(genuine,  bins=80, density=True, alpha=0.6,
            color="#4C72B0", label=f"Genuine  (n={len(genuine):,})")
    if eer_threshold is not None:
        ax.axvline(eer_threshold, color="#2CA02C", linestyle="--", linewidth=1.8,
                   label=f"EER threshold = {eer_threshold:.3f}")
    ax.set_xlabel("Cosine Similarity", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved: {save_path}")


def plot_roc_curve(fpr, tpr, thresholds, metrics, save_path, title="ROC Curve"):
    """
    ROC curve with AUC in the legend and EER marked as a dot.
    """
    eer     = metrics["EER"]
    auc_val = metrics["AUC"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(fpr, tpr, color="#4C72B0", lw=2,
            label=f"AUC = {auc_val:.4f}")
    ax.scatter([eer], [1 - eer], color="#C44E52", s=80, zorder=5,
               label=f"EER = {eer:.4f}")
    ax.set_xlabel("False Positive Rate (FAR)", fontsize=12)
    ax.set_ylabel("True Positive Rate (TAR)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xlim([1e-4, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, which="both", color="lightgrey", linewidth=0.7)
    ax.legend(fontsize=11)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved: {save_path}")


def plot_combined_roc_curves(roc_entries, save_path, title="ROC Curves"):
    """
    Overlay multiple ROC curves on one plot.

    Args:
        roc_entries: list of dicts with keys: label, fpr, tpr, auc, eer
    """
    colors = plt.cm.tab10.colors

    fig, ax = plt.subplots(figsize=(12, 7))
    for i, entry in enumerate(roc_entries):
        color = colors[i % len(colors)]
        ax.plot(entry["fpr"], entry["tpr"], color=color, lw=2,
                label=f"{entry['label']}  AUC={entry['auc']:.4f}  EER={entry['eer']:.4f}")
        ax.scatter([entry["eer"]], [1 - entry["eer"]], color=color, s=60, zorder=5)

    ax.set_xlabel("False Positive Rate (FAR)", fontsize=12)
    ax.set_ylabel("True Positive Rate (TAR)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xlim([1e-4, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, which="both", color="lightgrey", linewidth=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved: {save_path}")
