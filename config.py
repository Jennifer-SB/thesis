from pathlib import Path

# --- Change these paths when switching machines ---
DRIVE_PATH = Path("D:/")

# Input
XML_FILE = DRIVE_PATH / "thesis" / "data" / "RKDimages.xml"

# Output
IMAGES_DIR = DRIVE_PATH / "thesis" / "images"

# Make sure the images folder exists when this config is loaded
IMAGES_DIR.mkdir(parents=True, exist_ok=True)