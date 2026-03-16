"""
downloader.py
-------------
Downloads portrait images from RKDimages dataset.
Only downloads artworks with a known sitter (persoonsnummer).
Picks best quality scan per priref using QUALITY_RANK.
"""

import time
import csv
import requests
from pathlib import Path
from tqdm import tqdm
from config import IMAGES_DIR
from xml_parser import RKDDataset


class RKDDownloader:
    """
    Downloads portrait images from the RKD IIIF server.

    Usage:
        dataset = RKDDataset()
        dataset.parse()

        downloader = RKDDownloader(dataset)
        downloader.download()
    """

    FAILED_CSV  = Path("failed_downloads.csv")
    SKIPPED_CSV = Path("skipped_nolim.csv")

    def __init__(self, dataset: RKDDataset, images_dir: Path = IMAGES_DIR, delay: float = 0.5):
        self.dataset    = dataset
        self.images_dir = images_dir
        self.delay      = delay  # seconds between requests

    def download(self, max_downloads: int = None) -> None:
        """Download all portraits with a known sitter (persoonsnummer)."""
        self.dataset._check_parsed()

        candidates = [
            item for item in self.dataset.get_lrefs(best_only=True)
            if item["personen"]
        ]

        if max_downloads:
            candidates = candidates[:max_downloads]
            print(f"TEST MODE: limiting to {max_downloads} images")

        print(f"\nPortraits to download: {len(candidates)}")
        print(f"Saving to: {self.images_dir}\n")

        downloaded     = 0
        skipped        = 0
        failed         = []
        consecutive_fails = 0
        FAIL_THRESHOLD = 5    # pause after this many fails in a row
        LONG_PAUSE     = 60   # seconds to wait when server seems overloaded

        for item in tqdm(candidates, desc="Downloading"):
            save_path = self.images_dir / f"{item['lref']}.jpg"

            if save_path.exists():
                skipped += 1
                consecutive_fails = 0  # reset, things were fine before
                continue

            success = self._download_image(item["url"], save_path)

            if success:
                downloaded += 1
                consecutive_fails = 0  # reset on success
            else:
                failed.append(item)
                consecutive_fails += 1

                if consecutive_fails >= FAIL_THRESHOLD:
                    tqdm.write(f"\n⚠️  {consecutive_fails} failures in a row — server seems overloaded. Pausing {LONG_PAUSE}s...")
                    time.sleep(LONG_PAUSE)
                    consecutive_fails = 0  # reset after pause

            time.sleep(self.delay)

        self._save_failed(failed)
        self._print_summary(downloaded, skipped, failed)

    def _download_image(self, url: str, save_path: Path) -> bool:
        """Download a single image. Returns True if successful."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                save_path.write_bytes(response.content)
                return True
            return False
        except Exception:
            return False
        
    def _save_failed(self, failed: list) -> None:
        """Save failed downloads to CSV for later retry."""
        if not failed:
            return
        with open(self.FAILED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["priref", "lref", "soort", "url"])
            writer.writeheader()
            for item in failed:
                writer.writerow({
                    "priref": item["priref"],
                    "lref":   item["lref"],
                    "soort":  item["soort"],
                    "url":    item["url"],
                })
        print(f"Failed downloads saved to {self.FAILED_CSV}")

    def _print_summary(self, downloaded, skipped, failed) -> None:
        print(f"\n{'='*50}")
        print(f"  DOWNLOAD SUMMARY")
        print(f"{'='*50}")
        print(f"  Downloaded:   {downloaded:>8}")
        print(f"  Skipped:      {skipped:>8}  (already existed)")
        print(f"  Failed:       {len(failed):>8}  (saved to CSV)")
        print(f"  Total:        {downloaded + skipped + len(failed):>8}")
        print(f"{'='*50}\n")