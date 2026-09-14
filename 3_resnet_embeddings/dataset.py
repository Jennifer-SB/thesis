"""
JEN added:
PyTorch Dataset for RKD portrait fine-tuning.

Reads training_set.csv + train_test_split.csv, filters by split and
optionally by medium group, and returns (image_tensor, class_label) pairs.

# EXP3: all media, train sitters:
ds = RKDFaceDataset(personen_dir, training_csv, split_csv, split="train")

# EXP4: oil paintings only, train sitters (≥2 oil paintings per sitter):
ds = RKDFaceDataset(personen_dir, training_csv, split_csv,
                    split="train", medium="Oil paintings")
"""

import sys
from pathlib import Path

import pandas as pd
from PIL import Image
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.evaluation.experiment import group_media   # adds medium_group column


class RKDFaceDataset:
    """
    personen_dir: path to personen/ folder  (D:/thesis/personen or /mnt/d/thesis/personen)
    training_csv: path to training_set.csv
    split_csv: path to train_test_split.csv
    split: "train" or "test"
    medium: if given, restrict to this medium_group AND sitters with ≥2 portraits in that medium (e.g. "Oil paintings")
    transform: torchvision transform; defaults to standard face recognition preprocessing
    """

    def __init__(self, personen_dir, training_csv, split_csv,
                 split="train", medium=None, transform=None):

        # Load df
        df = pd.read_csv(training_csv)
        df = group_media(df)        # adds medium_group (and artist_group)

        # Split df:
        split_df = pd.read_csv(split_csv)
        df = df.merge(split_df, on="sitter_id")
        df = df[df["split"] == split].copy()

        # Optional medium filter:
        if medium is not None:
            df = df[df["medium_group"] == medium].copy()
            # Keep only sitters with 2+ portraits in this medium
            # (sitters with 1 portrait contribute no intra-class variation for fine-tuning)
            counts        = df.groupby("sitter_id")["lref"].count()
            valid_sitters = counts[counts >= 2].index
            df            = df[df["sitter_id"].isin(valid_sitters)].copy()

        personen_dir = Path(personen_dir)

        # Extract sitter IDs from df:
        sitter_ids        = sorted(df["sitter_id"].unique())
        # lookup table to find OG sitter IDs instead of integer labels needed for PyTorch
        self.class_to_idx = {sid: i for i, sid in enumerate(sitter_ids)}
        self.classes      = sitter_ids
        # how many output 'neurons' to create for CosFace head:
        self.num_classes  = len(sitter_ids)

        # Check whether every file is present and add to sample list:
        self.samples = []
        n_missing    = 0
        for _, row in df.iterrows():
            img_path = personen_dir / str(row["sitter_id"]) / f"{row['lref']}.jpg"
            if img_path.exists():
                self.samples.append((img_path, self.class_to_idx[row["sitter_id"]]))
            else:
                n_missing += 1

        self.transform = transform or _default_transform()

        # Summary
        label = f"{split}" + (f" / {medium}" if medium else "")
        print(f"RKDFaceDataset [{label}]")
        print(f"Sitters: {self.num_classes:,}, images: {len(self.samples):,}"
              + (f" {n_missing} missing (skipped)" if n_missing else ""))

    # For PyTorch:
    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label


def _default_transform():
    """Preprocessing matching inference.py: resize to 112x112, normalize to [-1, 1]."""
    return transforms.Compose([
        transforms.Resize((112, 112)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
