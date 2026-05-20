"""
src/dataset/retry_corrupt.py
-----------------------------
Re-downloads all images listed in corrupt_lrefs.csv, overwriting existing files.
"""

import time
import csv
import random
import requests
from pathlib import Path
from tqdm import tqdm
from config import IMAGES_DIR, FAILED_CSV


def _download_image(url: str, save_path: Path) -> bool:
    """Download a single image with up to 3 retries. Returns True if successful."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                save_path.write_bytes(response.content)
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


# Load corrupt lrefs
# with open("corrupt_lrefs.csv", newline="", encoding="utf-8") as f:

# Load missing lrefs
with open("missing_lrefs.csv", newline="", encoding="utf-8") as f:
    candidates = list(csv.DictReader(f))

# print(f"\nTotal corrupt images to retry: {len(candidates)}")
print(f"\nTotal missing images to download: {len(candidates)}")
print(f"Saving to:                     {IMAGES_DIR}\n")

downloaded        = 0
failed            = []
consecutive_fails = 0
FAIL_THRESHOLD    = 5
LONG_PAUSE        = 60

for item in tqdm(candidates, desc="Retrying"):
    save_path = IMAGES_DIR / f"{item['lref']}.jpg"

    # Delete corrupt file before re-downloading
    if save_path.exists():
        save_path.unlink()

    success = _download_image(item["url"], save_path)

    if success:
        downloaded += 1
        consecutive_fails = 0
    else:
        failed.append(item)
        consecutive_fails += 1

        if consecutive_fails >= FAIL_THRESHOLD:
            tqdm.write(
                f"\nWARNING: {consecutive_fails} failures in a row — "
                f"pausing {LONG_PAUSE}s..."
            )
            time.sleep(LONG_PAUSE)
            consecutive_fails = 0

    time.sleep(1.0 + random.uniform(0.5, 2.0))

# Save failed
if failed:
    with open(FAILED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(candidates[0].keys()))
        writer.writeheader()
        writer.writerows(failed)

print(f"\n{'='*50}")
print(f"  RETRY SUMMARY")
print(f"{'='*50}")
print(f"  Re-downloaded:  {downloaded:>8}")
print(f"  Failed:         {len(failed):>8}  (saved to {FAILED_CSV})")
print(f"  Total:          {len(candidates):>8}")
print(f"{'='*50}\n")