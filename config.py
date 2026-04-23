"""
config.py
---------
Single source of truth for all paths and settings.
Change paths here when switching machines (e.g. Windows → Linux GPU).
"""

from pathlib import Path

# --- Machine-specific: change this when switching machines ---
DRIVE_PATH = Path("D:/")

# --- Input data ---
XML_FILE   = DRIVE_PATH / "thesis" / "data" / "RKDimages.xml"

# --- Output: downloaded images ---
IMAGES_DIR = DRIVE_PATH / "thesis" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# --- Output: charts ---
PLOTS_DIR  = Path("plots/dataset_evaluation")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Output: download logs ---
FAILED_CSV  = Path("failed_downloads.csv")

# --- Output: select images ---
MANIFEST_CSV  = Path("dataset_manifest.csv")
MIN_RESOLUTION = (224, 224)   # minimum width x height to include