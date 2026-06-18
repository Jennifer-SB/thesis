"""
MAIN METHOD: loads face embeddings from features.pkl (and normalizes them).
as well: computes cosine similarity between pairs.

needed: features.pkl with folder (person_id), filename (lref) and embeddings.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize


def load_embeddings(pkl_path: str | Path = "features.pkl") -> dict:
    """
    Load face embeddings from features.pkl.
    Returns: dict mapping lref (str) --> L2-normalised embedding (numpy array, shape 512)
    """
    
    df    = pd.read_pickle(pkl_path)
    lrefs = df["filename"].astype(str).values
    embs  = np.stack(df["feature"].values).squeeze(1)  # (N, 512)
    embs  = normalize(embs, norm="l2")
    return dict(zip(lrefs, embs))


def score_pairs(pairs: list, embeddings: dict) -> tuple:
    """
    Compute cosine similarity for a list of pairs.

    Args:
        pairs:      list of (lref_a, lref_b, label, sitter_id_a, sitter_id_b)
        embeddings: dict from load_embeddings()

    Returns:
        scores:  numpy array of cosine similarities
        labels:  numpy array of 1 (genuine) or 0 (impostor)
        skipped: number of pairs where one embedding was missing
    """
    # 2 lists to collect the results:
    scores, labels = [], []
    # counter for skipped pairs:
    skipped = 0

    # only the lrefs and the label needed:
    for lref_a, lref_b, label, *_ in pairs:
        # look up each portrait embedding from the dict returned by load_embedding
        emb_a = embeddings.get(str(lref_a))
        emb_b = embeddings.get(str(lref_b))

        # double check:
        if emb_a is None or emb_b is None:
            skipped += 1
            continue
        
        # calculate cosine similarity and append answers to lists:
        sim = np.dot(emb_a, emb_b)      # (already normalized so cos_sim(a,b) = dot(a,b))
        scores.append(float(sim))
        labels.append(label)

    if skipped > 0:
        print(f"!!! {skipped} pairs skipped (embedding not found) !!!")

    return np.array(scores, dtype=np.float32), np.array(labels, dtype=np.int8)
