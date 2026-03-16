"""
xml_parser.py
-------------
RKDDataset class for parsing and analyzing the RKDimages XML dataset.
"""

import os
import random
from collections import Counter, defaultdict
from tqdm import tqdm
from config import XML_FILE


QUALITY_RANK = [
    "digital color photograph",
    "digital image",
    "digital photograph",
    "digital file",
    "digital black-and-white photograph",
    "color photograph",
    "original photograph",
    "color reproduction",
    "ektachrome",
    "photograph",
    "slide (photo)",
    "black and white photograph",
    "old black-and-white photograph",
    "brown photograph",
    "black-and-white reproduction",
    "color photocopy",
    "black-and-white photocopy",
    "print",
    "printouts",
    "reproduction (derivative object)",
    "photo after reproduction",
    "heliography (process)",
    "cyanotype",
    "negative",
    "black-and-white negative",
    "filing card",
    "back-side (of image)",
]

EXCLUDE_TYPES = {"no (digital) image available"}


class RKDDataset:
    """
    Parses and analyzes the RKDimages XML dataset.

    Usage:
        dataset = RKDDataset()
        dataset.parse()
        dataset.overview()
    """

    def __init__(self, xml_file: str = XML_FILE):
        self.xml_file = xml_file
        self.records  = {}   # priref → {"priref", "personen", "media"}
        self._parsed  = False

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(self) -> None:
        """Parse the XML file. Must be called before any other method."""
        file_size = os.path.getsize(self.xml_file)

        current_priref   = None
        current_lref     = None
        current_soort    = None
        current_personen = set()
        current_media    = []
        inside_soort     = False

        with open(self.xml_file, "r", encoding="utf-8") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True, desc="Parsing XML") as pbar:
                for line in f:
                    pbar.update(len(line.encode("utf-8")))
                    s = line.strip()

                    if '<priref tag="%0"' in s and "/>" not in s:
                        if current_priref:
                            self._save_record(current_priref, current_personen, current_media)
                        current_priref   = self._extract(s)
                        current_personen = set()
                        current_media    = []

                    elif '<persoonsnummer tag="z3"' in s and "linkref" not in s and "/>" not in s:
                        val = self._extract(s)
                        if val:
                            current_personen.add(val)

                    elif '<media.original_file_name_lref' in s and "/>" not in s:
                        current_lref = self._extract(s)

                    elif '<soort_afbeelding' in s:
                        inside_soort  = True
                        current_soort = None

                    elif inside_soort and '<value lang="en-US"' in s:
                        current_soort = self._extract(s)
                        inside_soort  = False

                    elif '</soort_afbeelding>' in s:
                        inside_soort = False

                    elif '</media>' in s:
                        if current_lref:
                            soort = current_soort or "unknown"
                            if soort not in EXCLUDE_TYPES:
                                current_media.append({"lref": current_lref, "soort": soort})
                        current_lref  = None
                        current_soort = None
                        inside_soort  = False

        if current_priref:
            self._save_record(current_priref, current_personen, current_media)

        self._parsed = True
        print(f"Parsed {len(self.records)} records.")

    def _save_record(self, priref, personen, media):
        self.records[priref] = {
            "priref":   priref,
            "personen": personen.copy(),
            "media":    media.copy(),
        }

    # ------------------------------------------------------------------
    # Quality helpers
    # ------------------------------------------------------------------

    @staticmethod
    def quality_score(soort: str) -> int:
        """Lower score = better quality. Returns 999 for unknown types."""
        soort_lower = soort.lower()
        for i, rank in enumerate(QUALITY_RANK):
            if rank.lower() == soort_lower:
                return i
        return 999

    @staticmethod
    def build_url(lref: str) -> str:
        """Build IIIF image URL from lref."""
        return f"https://media.rkd.nl/iiif/{lref}/full/max/0/default.jpg"

    def best_media(self, media_list: list) -> dict | None:
        """Return the highest quality media item from a list."""
        if not media_list:
            return None
        return min(media_list, key=lambda m: self.quality_score(m["soort"]))

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_lrefs(self, best_only: bool = True) -> list[dict]:
        """
        Get a flat list of lrefs to download.

        Args:
            best_only: if True (default), pick best quality scan per priref

        Returns list of dicts with priref, lref, soort, url, personen.
        """
        self._check_parsed()
        result = []
        for rec in self.records.values():
            if not rec["media"]:
                continue
            items = [self.best_media(rec["media"])] if best_only else rec["media"]
            for m in items:
                result.append({
                    "priref":   rec["priref"],
                    "lref":     m["lref"],
                    "soort":    m["soort"],
                    "url":      self.build_url(m["lref"]),
                    "personen": rec["personen"],
                })
        return result

    def sitter_portrait_counts(self) -> Counter:
        """Count how many artworks each persoonsnummer appears in."""
        self._check_parsed()
        counts = Counter()
        for rec in self.records.values():
            for p in rec["personen"]:
                counts[p] += 1
        return counts

    def multi_portrait_sitters(self, min_portraits: int = 2) -> Counter:
        """Return sitters with at least min_portraits portraits."""
        return Counter({
            p: c for p, c in self.sitter_portrait_counts().items()
            if c >= min_portraits
        })

    def portraits_for_sitter(self, persoonsnummer: str) -> list[dict]:
        """Return all lrefs (best quality) for a specific persoonsnummer."""
        self._check_parsed()
        result = []
        for rec in self.records.values():
            if persoonsnummer in rec["personen"]:
                m = self.best_media(rec["media"])
                if m:
                    result.append({
                        "priref": rec["priref"],
                        "lref":   m["lref"],
                        "soort":  m["soort"],
                        "url":    self.build_url(m["lref"]),
                    })
        return result

    # ------------------------------------------------------------------
    # Analysis / printing
    # ------------------------------------------------------------------

    def overview(self) -> None:
        """Print a summary of the dataset."""
        self._check_parsed()
        total          = len(self.records)
        with_sitter    = sum(1 for r in self.records.values() if r["personen"])
        total_lrefs    = sum(len(r["media"]) for r in self.records.values())
        multi_scan     = sum(1 for r in self.records.values() if len(r["media"]) > 1)
        sitter_counts  = self.sitter_portrait_counts()
        multi_sitters  = self.multi_portrait_sitters()

        print(f"\n{'='*50}")
        print(f"  DATASET OVERVIEW")
        print(f"{'='*50}")
        print(f"  Total artworks (priref):        {total:>8}")
        print(f"  Artworks with known sitter:     {with_sitter:>8}")
        print(f"  Artworks without sitter:        {total - with_sitter:>8}")
        print(f"  Total scans (lrefs):            {total_lrefs:>8}")
        print(f"  Artworks with 2+ scans:         {multi_scan:>8}")
        print(f"  Unique sitters:                 {len(sitter_counts):>8}")
        print(f"  Sitters with 2+ portraits:      {len(multi_sitters):>8}")
        print(f"  Portraits usable for training:  {sum(multi_sitters.values()):>8}")
        print(f"{'='*50}\n")

    def sample_multi_scan(self, n: int = 20) -> None:
        """Print n random artworks with 2+ scans and the best pick for each."""
        self._check_parsed()
        multi = [(p, r) for p, r in self.records.items() if len(r["media"]) > 1]
        sample = random.sample(multi, min(n, len(multi)))

        print(f"\n{n} RANDOM ARTWORKS WITH 2+ SCANS\n")
        for priref, rec in sample:
            print(f"priref {priref}:")
            for m in rec["media"]:
                print(f"  [{self.quality_score(m['soort']):>3}] {m['soort']:<40} {self.build_url(m['lref'])}")
            pick = self.best_media(rec["media"])
            print(f"  >>> PICKED [{self.quality_score(pick['soort'])}] {pick['soort']}: {self.build_url(pick['lref'])}\n")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_parsed(self):
        if not self._parsed:
            raise RuntimeError("Call .parse() before using this method.")

    @staticmethod
    def _extract(line: str) -> str:
        try:
            return line.split(">")[1].split("<")[0].strip()
        except IndexError:
            return ""