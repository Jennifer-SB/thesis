"""
Constructs genuine and impostor pairs from a filtered DataFrame.

A pair is a tuple: (lref_a, lref_b, label, sitter_id_a, sitter_id_b)
    label 1 = genuine  (same sitter_id)
    label 0 = impostor (different sitter_id)
"""

import numpy as np
from itertools import combinations


def build_pairs(df, impostor_ratio: int = 10, seed: int = 42) -> list:
    """
    Build genuine pairs (all combinations per sitter) and sampled impostor pairs.

    Args:
        df:              filtered subset of training_set.csv.
                         Must have columns: lref, sitter_id.
        impostor_ratio:  number of impostor pairs to sample per genuine pair.
        seed:            random seed — fixes which impostors are sampled so
                         results are identical every run.

    Returns:
        list of (lref_a, lref_b, label, sitter_id_a, sitter_id_b)
    """
    # random number generator with fixed seed (same impostors picked every run):
    rng = np.random.default_rng(seed)

    # define/extract:
    lrefs   = df["lref"].astype(str).values
    sitters = df["sitter_id"].astype(str).values
    n       = len(df)

    # Genuine pairs: all portrait combinations per sitter
    genuine = []
    for sid, group in df.groupby("sitter_id"):
        lref_list = group["lref"].astype(str).tolist()
        # for each sitter with at least two portraits:...
        if len(lref_list) >= 2:
            # unique unordered pair(s):
            for la, lb in combinations(lref_list, 2):
                # store pairs as a tuple with label 1 (because Genuine)
                genuine.append((la, lb, 1, str(sid), str(sid)))

    # counts how many genuine pairs found:...
    n_genuine  = len(genuine)
    # and sets impostor target based on that (default 10 times more):
    n_impostor = n_genuine * impostor_ratio

    # Impostor pairs: random sampling across different sitters
    impostor = []
    while len(impostor) < n_impostor:
        # How many random draws to attempt this iteration.
        # Multiplies remaining needed by 3 to account for pairs that will be filtered out (same sitter or same index).
        # Caps at 200,000 to avoid allocating huge arrays.
        batch_size = min((n_impostor - len(impostor)) * 3, 200_000)
        idx_a = rng.integers(0, n, size=batch_size)
        idx_b = rng.integers(0, n, size=batch_size)
        
        # Filter out portraits paired with itself or Genuine pairs:
        valid = (idx_a != idx_b) & (sitters[idx_a] != sitters[idx_b])
        # loop over remaining valid pairs and append them:
        for ia, ib in zip(idx_a[valid], idx_b[valid]):
            if len(impostor) >= n_impostor:
                break
            impostor.append((
                lrefs[ia], lrefs[ib], 0,
                sitters[ia], sitters[ib]
            ))

    pairs = genuine + impostor
    print(f"Pairs built — genuine: {n_genuine:,}  impostor: {len(impostor):,}  "
          f"ratio: 1:{impostor_ratio}")
    return pairs


def build_cross_medium_pairs(df, medium_col: str, medium_a: str, medium_b: str,
                              impostor_ratio: int = 10, seed: int = 42) -> list:
    """
    Build cross-medium genuine pairs and sampled impostor pairs.

    Genuine:  same sitter, one portrait from medium_a and one from medium_b.
    Impostor: different sitter, one portrait from each medium (keeps the
              medium distribution identical to the genuine set).

    Args:
        df:             full DataFrame with columns lref, sitter_id, <medium_col>
        medium_col:     name of the medium column (e.g. "medium_group")
        medium_a/b:     the two media to pair (e.g. "Oil paintings", "Prints")
        impostor_ratio: impostor pairs per genuine pair
        seed:           random seed

    Returns:
        list of (lref_a, lref_b, label, sitter_id_a, sitter_id_b)
    """
    df_a = df[df[medium_col] == medium_a]
    df_b = df[df[medium_col] == medium_b]

    lrefs_a   = df_a["lref"].astype(str).values
    sitters_a = df_a["sitter_id"].astype(str).values
    lrefs_b   = df_b["lref"].astype(str).values
    sitters_b = df_b["sitter_id"].astype(str).values
    na, nb    = len(df_a), len(df_b)

    # Group lrefs by sitter for fast lookup
    groups_a = (df_a.assign(sitter_id=sitters_a)
                .groupby("sitter_id")["lref"]
                .apply(lambda x: x.astype(str).tolist())
                .to_dict())
    groups_b = (df_b.assign(sitter_id=sitters_b)
                .groupby("sitter_id")["lref"]
                .apply(lambda x: x.astype(str).tolist())
                .to_dict())

    # Genuine pairs: all (portrait_a, portrait_b) combos for shared sitters
    shared  = set(groups_a.keys()) & set(groups_b.keys())
    genuine = []
    for sid in shared:
        for la in groups_a[sid]:
            for lb in groups_b[sid]:
                genuine.append((la, lb, 1, sid, sid))

    n_genuine  = len(genuine)
    n_impostor = n_genuine * impostor_ratio

    # Impostor pairs: different sitter, one portrait from each medium
    rng      = np.random.default_rng(seed)
    impostor = []
    while len(impostor) < n_impostor:
        batch_size = min((n_impostor - len(impostor)) * 3, 200_000)
        idx_a = rng.integers(0, na, size=batch_size)
        idx_b = rng.integers(0, nb, size=batch_size)
        valid = sitters_a[idx_a] != sitters_b[idx_b]
        for ia, ib in zip(idx_a[valid], idx_b[valid]):
            if len(impostor) >= n_impostor:
                break
            impostor.append((lrefs_a[ia], lrefs_b[ib], 0, sitters_a[ia], sitters_b[ib]))

    pairs = genuine + impostor
    print(f"  Cross-medium ({medium_a} × {medium_b}) — "
          f"shared sitters: {len(shared):,}  genuine: {n_genuine:,}  impostor: {len(impostor):,}")
    return pairs
