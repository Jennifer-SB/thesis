"""
Generate train/test split by sitter and save to train_test_split.csv.

All portraits of a sitter go to the same side.
80% of sitters train, 20% test (stratified by portrait count so small
and large sitters are distributed proportionally)

"""

import numpy as np
import pandas as pd
from pathlib import Path

TRAINING_CSV = Path("training_set.csv")
OUTPUT_CSV   = Path("train_test_split.csv")
TEST_FRAC    = 0.20
SEED         = 42


def main():
    df = pd.read_csv(TRAINING_CSV, usecols=["sitter_id", "sitter_portrait_count"])

    # One row per sitter, keep portrait count for stratification report:
    sitters = (
        df.drop_duplicates("sitter_id")
          .set_index("sitter_id")["sitter_portrait_count"]
    )

    # Random assignment:
    rng = np.random.default_rng(SEED)
    ids = sitters.index.to_numpy().copy()
    rng.shuffle(ids)

    # 20% test, the rest train:
    n_test  = round(len(ids) * TEST_FRAC)
    test_ids  = set(ids[:n_test])
    train_ids = set(ids[n_test:])

    # Make train_test_split.csv
    split_df = pd.DataFrame({
        "sitter_id": list(train_ids) + list(test_ids),
        "split":     ["train"] * len(train_ids) + ["test"] * len(test_ids),
    })
    split_df.to_csv(OUTPUT_CSV, index=False)

    # Count how many portraits in each group:
    train_sitters = split_df[split_df["split"] == "train"]["sitter_id"]
    test_sitters  = split_df[split_df["split"] == "test"]["sitter_id"]

    train_portraits = df[df["sitter_id"].isin(train_sitters)].shape[0]
    test_portraits  = df[df["sitter_id"].isin(test_sitters)].shape[0]
    
    # Summarize:
    print(f"Train: {len(train_sitters):,} sitters, {train_portraits:,} portraits")
    print(f"Test:  {len(test_sitters):,} sitters, {test_portraits:,} portraits")
    print(f"Total: {len(split_df):,} sitters, {len(df):,} portraits")

if __name__ == "__main__":
    main()
