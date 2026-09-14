# """
# src/dataset/downloader.py
# --------------------------
# RKDDownloader: downloads portrait images from the RKD IIIF server.

# Usage:
#     from src.dataset.xml_parser import RKDDataset
#     from src.dataset.downloader import RKDDownloader

#     dataset = RKDDataset()
#     dataset.parse()

#     downloader = RKDDownloader(dataset)
#     downloader.download()
# """

# import time
# import csv
# import random
# import requests
# from pathlib import Path
# from tqdm import tqdm
# from config import IMAGES_DIR, FAILED_CSV
# from src.dataset.xml_parser import RKDDataset


# class RKDDownloader:
#     """
#     Downloads portrait images (artworks with a known sitter) from RKD.
#     Picks best quality scan per priref.
#     Skips already downloaded files — safe to restart after interruption.
#     Includes retry logic and a circuit breaker for server overload.
#     """

#     def __init__(self, dataset: RKDDataset,
#                  images_dir: Path = IMAGES_DIR,
#                  delay: float = 1.0):
#         self.dataset    = dataset
#         self.images_dir = images_dir
#         self.delay      = delay

#     def download(self, max_downloads: int = None) -> None:
#         """
#         Download all portraits with a known sitter.

#         Args:
#             max_downloads: limit to N images (for testing). None = download all.
#         """
#         self.dataset._check_parsed()

#         # Only download artworks that have at least one persoonsnummer
#         candidates = [
#             item for item in self.dataset.get_lrefs(best_only=True)
#             if item["personen"]
#         ]

#         if max_downloads:
#             candidates = candidates[:max_downloads]
#             print(f"TEST MODE: limiting to {max_downloads} images")

#         print(f"\nPortraits to download: {len(candidates)}")
#         print(f"Saving to:             {self.images_dir}\n")

#         downloaded        = 0
#         skipped           = 0
#         failed            = []
#         consecutive_fails = 0
#         FAIL_THRESHOLD    = 5
#         LONG_PAUSE        = 60

#         for item in tqdm(candidates, desc="Downloading"):
#             save_path = self.images_dir / f"{item['lref']}.jpg"

#             # Skip already downloaded files
#             if save_path.exists():
#                 skipped += 1
#                 consecutive_fails = 0
#                 continue

#             success = self._download_image(item["url"], save_path)

#             if success:
#                 downloaded += 1
#                 consecutive_fails = 0
#             else:
#                 failed.append(item)
#                 consecutive_fails += 1

#                 # Circuit breaker: pause if server seems overloaded
#                 if consecutive_fails >= FAIL_THRESHOLD:
#                     tqdm.write(
#                         f"\n⚠️  {consecutive_fails} failures in a row — "
#                         f"pausing {LONG_PAUSE}s..."
#                     )
#                     time.sleep(LONG_PAUSE)
#                     consecutive_fails = 0

#             time.sleep(self.delay + random.uniform(0.5, 2.0))

#         self._save_failed(failed)
#         self._print_summary(downloaded, skipped, failed)

#     def _download_image(self, url: str, save_path: Path) -> bool:
#         """Download a single image with up to 3 retries. Returns True if successful."""
#         headers = {
#             "User-Agent": (
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/120.0.0.0 Safari/537.36"
#             )
#         }
#         for attempt in range(3):
#             try:
#                 response = requests.get(url, headers=headers, timeout=15)
#                 if response.status_code == 200:
#                     save_path.write_bytes(response.content)
#                     return True
#             except Exception:
#                 pass
#             time.sleep(2)
#         return False

#     def _save_failed(self, failed: list) -> None:
#         """Save failed downloads to CSV for later retry."""
#         if not failed:
#             return
#         with open(FAILED_CSV, "w", newline="", encoding="utf-8") as f:
#             writer = csv.DictWriter(
#                 f, fieldnames=["priref", "lref", "soort", "url"]
#             )
#             writer.writeheader()
#             for item in failed:
#                 writer.writerow({
#                     "priref": item["priref"],
#                     "lref":   item["lref"],
#                     "soort":  item["soort"],
#                     "url":    item["url"],
#                 })
#         print(f"Failed downloads saved to {FAILED_CSV}")

#     def _print_summary(self, downloaded, skipped, failed) -> None:
#         print(f"\n{'='*50}")
#         print(f"  DOWNLOAD SUMMARY")
#         print(f"{'='*50}")
#         print(f"  Downloaded:   {downloaded:>8}")
#         print(f"  Skipped:      {skipped:>8}  (already existed)")
#         print(f"  Failed:       {len(failed):>8}  (saved to {FAILED_CSV})")
#         print(f"  Total:        {downloaded + skipped + len(failed):>8}")
#         print(f"{'='*50}\n")

"""
src/dataset/downloader.py
--------------------------
RKDDownloader: downloads all images from the RKD IIIF server.

Usage:
    from src.dataset.xml_parser import RKDDataset
    from src.dataset.downloader import RKDDownloader

    dataset = RKDDataset()
    dataset.parse()

    downloader = RKDDownloader(dataset)
    downloader.download()
"""

import time
import csv
import random
import requests
from pathlib import Path
from tqdm import tqdm
from config import IMAGES_DIR, FAILED_CSV
from src.dataset.xml_parser import RKDDataset


class RKDDownloader:
    """
    Downloads all images from RKD — regardless of whether sitters are identified.
    Downloads every lref per priref, not just the best quality scan.
    Skips already downloaded files — safe to restart after interruption.
    Includes retry logic and a circuit breaker for server overload.
    """

    def __init__(self, dataset: RKDDataset,
                 images_dir: Path = IMAGES_DIR,
                 delay: float = 1.0):
        self.dataset    = dataset
        self.images_dir = images_dir
        self.delay      = delay

    def download(self, max_downloads: int = None) -> None:
        """
        Download all images for all records — all lrefs, all prirefs.

        Args:
            max_downloads: limit to N images (for testing). None = download all.
        """
        self.dataset._check_parsed()

        # All lrefs across all records, not filtered by sitter or quality
        candidates = self.dataset.get_lrefs(best_only=False)

        if max_downloads:
            candidates = candidates[:max_downloads]
            print(f"TEST MODE: limiting to {max_downloads} images")

        print(f"\nTotal images to download: {len(candidates)}")
        print(f"Saving to:                {self.images_dir}\n")

        downloaded        = 0
        skipped           = 0
        failed            = []
        consecutive_fails = 0
        FAIL_THRESHOLD    = 5
        LONG_PAUSE        = 60

        for item in tqdm(candidates, desc="Downloading"):
            save_path = self.images_dir / f"{item['lref']}.jpg"

            # Skip already downloaded files
            if save_path.exists() and save_path.stat().st_size > 5000:
                skipped += 1
                consecutive_fails = 0
                continue

            success = self._download_image(item["url"], save_path)

            if success:
                downloaded += 1
                consecutive_fails = 0
            else:
                failed.append(item)
                consecutive_fails += 1

                # Circuit breaker: pause if server seems overloaded
                if consecutive_fails >= FAIL_THRESHOLD:
                    tqdm.write(
                        f"\nWARNING: {consecutive_fails} failures in a row — "
                        f"pausing {LONG_PAUSE}s..."
                    )
                    time.sleep(LONG_PAUSE)
                    consecutive_fails = 0

            time.sleep(self.delay + random.uniform(0.5, 2.0))

        self._save_failed(failed)
        self._print_summary(downloaded, skipped, failed)

    def _download_image(self, url: str, save_path: Path) -> bool:
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

    def _save_failed(self, failed: list) -> None:
        """Save failed downloads to CSV for later retry."""
        if not failed:
            return
        with open(FAILED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["priref", "lref", "soort", "url"]
            )
            writer.writeheader()
            for item in failed:
                writer.writerow({
                    "priref": item["priref"],
                    "lref":   item["lref"],
                    "soort":  item["soort"],
                    "url":    item["url"],
                })
        print(f"Failed downloads saved to {FAILED_CSV}")

    def _print_summary(self, downloaded, skipped, failed) -> None:
        print(f"\n{'='*50}")
        print(f"  DOWNLOAD SUMMARY")
        print(f"{'='*50}")
        print(f"  Downloaded:   {downloaded:>8}")
        print(f"  Skipped:      {skipped:>8}  (already existed)")
        print(f"  Failed:       {len(failed):>8}  (saved to {FAILED_CSV})")
        print(f"  Total:        {downloaded + skipped + len(failed):>8}")
        print(f"{'='*50}\n")