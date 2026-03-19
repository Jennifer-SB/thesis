"""
RKDDataset: single XML parser for the entire project.

Usage:
    from src.dataset.xml_parser import RKDDataset
    dataset = RKDDataset()
    dataset.parse()
    dataset.overview()
"""

import os
import random
from collections import Counter
from tqdm import tqdm
from config import XML_FILE
import xml.etree.ElementTree as ET


QUALITY_RANK = [
    "digital color photograph",
    "digital image",
    "digital photograph",
    "digital black-and-white photograph",
    "digital file",
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
    Parses and analyses the RKDimages XML dataset in a single pass.

    Each record (keyed by priref) contains:
        priref        — unique artwork ID
        personen      — list of {nummer, zekerheid} dicts
        media         — list of {lref, soort} dicts
        objectcat     — type of artwork (painting, print, etc.)
        date_datering — date assigned by art historian
        date_zoekmarge— earliest possible date (technical field)
    """

    def __init__(self, xml_file: str = XML_FILE):
        self.xml_file = xml_file
        self.records  = {}
        self._parsed  = False

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(self) -> None:
        """
        Parse the full XML file in a single pass.
        Must be called before any other method.
        """
        file_size = os.path.getsize(self.xml_file)

        current_priref         = None
        current_personen       = []
        current_media          = []
        current_objectcat      = None
        current_date_datering  = None
        current_date_zoekmarge = None
        current_lref           = None
        current_soort          = None
        current_title_dutch    = None
        current_title_english  = None
        current_artist_name    = None
        current_artist_id      = None
        current_genre          = None
        current_materiaal      = []
        current_drager         = None
        current_trefwoorden_en = []
        current_trefwoorden_nl = []
        current_trefwoord_en   = None
        current_trefwoord_nl   = None
        inside_objectcat       = False
        inside_soort           = False
        inside_toeschrijving   = False
        inside_trefwoord       = False
        inside_genre           = False 
        inside_materiaal       = False   
        inside_drager          = False   
        last_persoon           = None

        with open(self.xml_file, "r", encoding="utf-8") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True, desc="Parsing XML") as pbar:
                for line in f:
                    pbar.update(len(line.encode("utf-8")))
                    s = line.strip()

                    # New record detected?
                    if '<priref tag="%0"' in s and "/>" not in s:
                        # First save the old variables (if there where any):
                        if current_priref:
                            self._save_record(current_priref,
                                                current_personen,
                                                current_media,
                                                current_objectcat,
                                                current_date_datering,
                                                current_date_zoekmarge,
                                                current_title_dutch,
                                                current_title_english,
                                                current_artist_name,
                                                current_artist_id,
                                                current_genre,
                                                current_materiaal,
                                                current_drager,
                                                current_trefwoorden_en,
                                                current_trefwoorden_nl,
                            )
                        
                        # Then reset the variables for a new record:
                        current_priref         = self._extract(s)
                        current_personen       = []
                        current_media          = []
                        current_objectcat      = None
                        current_date_datering  = None
                        current_date_zoekmarge = None
                        current_title_dutch    = None
                        current_title_english  = None
                        current_artist_name    = None
                        current_artist_id      = None
                        current_genre          = None
                        current_materiaal      = []
                        current_drager         = None
                        current_trefwoorden_en = []
                        current_trefwoorden_nl = []
                        current_trefwoord_en   = None
                        current_trefwoord_nl   = None
                        inside_objectcat       = False
                        inside_soort           = False
                        inside_toeschrijving   = False
                        inside_trefwoord       = False
                        inside_genre           = False  
                        inside_materiaal       = False  
                        inside_drager          = False  
                        last_persoon           = None

                    # === PERSOONSNUMMER: Unique ID of a depicted person. ===
                    # If tag is empty (self closing) then sitter = unknown.
                    # ? set last_persoon as a pointer so the next zekerheid line can be attached to the right person.
                    elif '<persoonsnummer tag="z3"' in s and "linkref" not in s:
                        if "/>" not in s:
                            val = self._extract(s)
                            if val:
                                last_persoon = {"nummer": val, "zekerheid": None}
                                current_personen.append(last_persoon)
                        else:
                            last_persoon = {"nummer": None, "zekerheid": None}
                            current_personen.append(last_persoon)

                    # === ZEKERHEID: Certainty of identification) ===
                    # ? Empty = certain, otherwise: waarschijnlijk / mogelijk / genaamd
                    # ? Lijkt me niet correct? Even checken wat alle waardes zijn en vragen wat logisch is.
                    elif '<zekerheid_identificatie_portret' in s:
                        if "/>" not in s and last_persoon is not None:
                            val = self._extract(s)
                            if val:
                                last_persoon["zekerheid"] = val

                    # === MEDIA LREF: current image ID ===
                    elif '<media.original_file_name_lref' in s and "/>" not in s:
                        current_lref = self._extract(s)

                    # === SOORT AFBEELDING: image type (multi-line) ===
                    elif '<soort_afbeelding' in s:
                        inside_soort  = True
                        current_soort = None

                    elif inside_soort and '<value lang="en-US"' in s:
                        current_soort = self._extract(s)
                        inside_soort  = False

                    elif '</soort_afbeelding>' in s:
                        inside_soort = False

                    # === END OF MEDIA BLOCK ===
                    # Save current_lref + current_soort together bc we organize images per priref
                    elif '</media>' in s:
                        if current_lref:
                            soort = current_soort or "unknown"
                            if soort not in EXCLUDE_TYPES:
                                current_media.append({
                                    "lref":  current_lref,
                                    "soort": soort
                                })
                        # Refresh for next image
                        current_lref  = None
                        current_soort = None
                        inside_soort  = False

                    # === OBJECT CATEGORY (multi-line) ===
                    elif '<objectcategorie' in s and "linkref" not in s:
                        inside_objectcat = True

                    elif inside_objectcat and '<value lang="en-US"' in s:
                        current_objectcat = self._extract(s)
                        inside_objectcat  = False

                    elif '</objectcategorie>' in s:
                        inside_objectcat = False

                    # === DATERING ===
                    # ? only take first occurrence: why are there sometimes more then 1?
                    # as well with other variables, check. (see below)
                    elif '<datering tag=' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_date_datering:
                            current_date_datering = val

                    # === ZOEKMARGE BEGINDATUM ===
                    # ? check with Sabine. Less precise than datering but more consistently filled.
                    elif '<zoekmarge_begindatum' in s and "/>" not in s:
                        val = self._extract(s)
                        if val:
                            current_date_zoekmarge = val

                    # === TITLE DUTCH ===
                    elif '<benaming_kunstwerk' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_title_dutch:
                            current_title_dutch = val

                    # === TITLE ENGLISH ===
                    elif '<titel_engels' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_title_english:
                            current_title_english = val

                    # === ARTIST (inside toeschrijving, status=huidig only) ===
                    # HERE I LEFT IT !
                    elif '<toeschrijving>' in s:
                        inside_toeschrijving = True

                    elif inside_toeschrijving and '<naam tag="na"' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_artist_name:
                            current_artist_name = val

                    elif inside_toeschrijving and '<naam_linkref' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_artist_id:
                            current_artist_id = val

                    elif inside_toeschrijving and '</toeschrijving>' in s:
                        inside_toeschrijving = False

                    # === GENRE ===
                    elif '<genre tag=' in s:
                        inside_genre = True

                    elif inside_genre and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val and not current_genre:
                            current_genre = val
                        inside_genre = False

                    elif '</genre>' in s:
                        inside_genre = False

                    # --- Materiaal ---
                    elif '<materiaal tag=' in s:
                        inside_materiaal = True

                    elif inside_materiaal and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val:
                            current_materiaal.append(val)
                        inside_materiaal = False

                    elif '</materiaal>' in s:
                        inside_materiaal = False

                    # --- Drager ---
                    elif '<drager tag=' in s:
                        inside_drager = True

                    elif inside_drager and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val and not current_drager:
                            current_drager = val
                        inside_drager = False

                    elif '</drager>' in s:
                        inside_drager = False

                    # --- RKD_algemene_trefwoorden (keywords, multi-value) ---
                    elif '<RKD_algemene_trefwoorden ' in s:
                        inside_trefwoord    = True
                        current_trefwoord_en = None
                        current_trefwoord_nl = None

                    elif inside_trefwoord and '<value lang="en-US"' in s:
                        current_trefwoord_en = self._extract(s)

                    elif inside_trefwoord and '<value lang="nl-NL"' in s:
                        current_trefwoord_nl = self._extract(s)

                    elif inside_trefwoord and '</RKD_algemene_trefwoorden>' in s:
                        if current_trefwoord_en:
                            current_trefwoorden_en.append(current_trefwoord_en)
                        if current_trefwoord_nl:
                            current_trefwoorden_nl.append(current_trefwoord_nl)
                        inside_trefwoord = False

        # Save last record
        if current_priref:
            self._save_record(current_priref,
                              current_personen,
                              current_media,
                              current_objectcat,
                              current_date_datering,
                              current_date_zoekmarge,
                              current_title_dutch,
                              current_title_english,
                              current_artist_name,
                              current_artist_id,
                              current_genre,
                              current_materiaal,
                              current_drager,
                              current_trefwoorden_en,
                              current_trefwoorden_nl,)

        self._parsed = True
        print(f"Parsed {len(self.records)} records.")

    def _save_record(self, priref, personen, media, objectcat,
                    date_datering, date_zoekmarge,
                    title_dutch, title_english,
                    artist_name, artist_id,
                    genre, materiaal, drager,
                    trefwoorden_en, trefwoorden_nl                    
                    ):

        self.records[priref] = {
            "priref":           priref,
            "personen":         personen.copy(),
            "media":            media.copy(),
            "objectcat":        objectcat,
            "date_datering":    date_datering,
            "date_zoekmarge":   date_zoekmarge,
            "title_dutch":      title_dutch,
            "title_english":    title_english,
            "artist_name":      artist_name,
            "artist_id":        artist_id,
            "genre":            genre,
            "materiaal":        materiaal.copy(),
            "drager":           drager,
            "trefwoorden_en":   trefwoorden_en.copy(),
            "trefwoorden_nl":   trefwoorden_nl.copy(),
        }
    # ------------------------------------------------------------------
    # Quality helpers
    # ------------------------------------------------------------------

    @staticmethod
    def quality_score(soort: str) -> int:
        """Lower score = better quality. Returns 999 for unknown/archive types."""
        soort_lower = soort.lower()
        for i, rank in enumerate(QUALITY_RANK):
            if rank.lower() == soort_lower:
                return i
        return 999

    @staticmethod
    def build_url(lref: str) -> str:
        """Build IIIF image URL from lref number."""
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
        Get a flat list of all lrefs.

        Args:
            best_only: if True (default), one lref per priref (best quality scan)

        Returns list of dicts: priref, lref, soort, url, personen
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
                if p["nummer"]:
                    counts[p["nummer"]] += 1
        return counts

    def multi_portrait_sitters(self, min_portraits: int = 2) -> Counter:
        """Return only sitters with at least min_portraits portraits."""
        return Counter({
            p: c for p, c in self.sitter_portrait_counts().items()
            if c >= min_portraits
        })

    def portraits_for_sitter(self, persoonsnummer: str) -> list[dict]:
        """Return all best-quality lrefs for a specific sitter."""
        self._check_parsed()
        result = []
        for rec in self.records.values():
            if persoonsnummer in {p["nummer"] for p in rec["personen"]}:
                m = self.best_media(rec["media"])
                if m:
                    result.append({
                        "priref": rec["priref"],
                        "lref":   m["lref"],
                        "soort":  m["soort"],
                        "url":    self.build_url(m["lref"]),
                    })
        return result

    def filter_records(self, filter_identified=True,
                       filter_multi_portrait=False) -> dict:
        """
        Return a filtered subset of records.

        filter_identified:    keep only artworks with at least one persoonsnummer
        filter_multi_portrait: keep only artworks where at least one sitter
                               appears in 2+ artworks
        """
        self._check_parsed()
        records = self.records

        if filter_identified:
            records = {
                p: r for p, r in records.items()
                if any(s["nummer"] for s in r["personen"])
            }
            print(f"  After filter (identified):       {len(records):>8} artworks")

        if filter_multi_portrait:
            sitter_counts = Counter()
            for rec in records.values():
                for s in rec["personen"]:
                    if s["nummer"]:
                        sitter_counts[s["nummer"]] += 1
            records = {
                p: r for p, r in records.items()
                if any(
                    sitter_counts.get(s["nummer"], 0) >= 2
                    for s in r["personen"] if s["nummer"]
                )
            }
            print(f"  After filter (multi-portrait):   {len(records):>8} artworks")

        return records

    # ------------------------------------------------------------------
    # Analysis / printing
    # ------------------------------------------------------------------
    
    def print_all_tags(self, n_lines: int = 1000) -> None:
        """
        Print all unique XML tag names found in the first n_lines of the file.
        Lightweight exploration tool — does not require .parse() first.
        """
        import xml.etree.ElementTree as ET

        content = ""
        with open(self.xml_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                content += line
                if i >= n_lines:
                    break

        content += "</record></recordList></adlibXML>"

        tags = set()
        try:
            root = ET.fromstring(content)
            for elem in root.iter():
                tags.add(elem.tag)
        except ET.ParseError:
            pass

        print(f"\nAll unique tags in first {n_lines} lines:\n")
        for tag in sorted(tags):
            print(f"  {tag}")

    def print_unique_values(self, tag_name: str, n_lines: int = None) -> None:
        """
        Scan the XML and print all unique values found for a given tag.
        Does not require .parse() first.

        Args:
            tag_name: the XML tag to search for (e.g. "zekerheid_identificatie_portret")
            n_lines:  number of lines to scan. None = full file.

        Example:
            dataset.print_unique_values("zekerheid_identificatie_portret")
            dataset.print_unique_values("objectcategorie")
        """
        from collections import Counter

        file_size    = os.path.getsize(self.xml_file)
        value_counts = Counter()
        open_tag     = f"<{tag_name}"
        close_tag    = f"</{tag_name}>"
        inside       = False  # flag: are we inside the right tag?

        with open(self.xml_file, "r", encoding="utf-8") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True,
                    desc=f"Scanning '{tag_name}'") as pbar:
                for i, line in enumerate(f):
                    pbar.update(len(line.encode("utf-8")))
                    s = line.strip()

                    if open_tag in s:
                        if "/>" in s:
                            # Self-closing = empty value
                            value_counts["(empty)"] += 1
                        else:
                            # Try to get inline value first e.g. <zekerheid...>waarschijnlijk</zekerheid>
                            val = self._extract(s)
                            if val:
                                value_counts[val] += 1
                            else:
                                # Value is on next lines — set flag
                                inside = True

                    elif inside and "<value" in s and 'lang="en-US"' in s:
                        val = self._extract(s)
                        if val:
                            value_counts[val] += 1

                    elif inside and close_tag in s:
                        inside = False  # stop collecting once tag closes

                    if n_lines and i >= n_lines:
                        break

        print(f"\n  Unique values for '{tag_name}':\n")
        print(f"  {'Value':<50} {'Count':>8}")
        print(f"  {'-'*60}")
        for val, count in value_counts.most_common():
            print(f"  {val:<50} {count:>8}")
        print(f"\n  Total unique values: {len(value_counts)}")

    def print_record(self, priref: str = None) -> None:
        """
        Print all parsed fields for a single record.
        If no priref given, prints the first record in the dataset.

        Args:
            priref: the priref ID to print. None = first record.

        Example:
            dataset.print_record()
            dataset.print_record("107491")
        """
        self._check_parsed()

        if priref:
            rec = self.records.get(str(priref))
            if not rec:
                print(f"priref '{priref}' not found.")
                return
        else:
            rec = next(iter(self.records.values()))

        # Best media
        m = self.best_media(rec["media"])

        print(f"\n{'='*60}")
        print(f"  RECORD: priref {rec['priref']}")
        print(f"{'='*60}")
        print(f"  Title (Dutch):    {rec['title_dutch']  or '—'}")
        print(f"  Title (English):  {rec['title_english'] or '—'}")
        print(f"  Artist:           {rec['artist_name']  or '—'} (ID: {rec['artist_id'] or '—'})")
        print(f"  Genre:            {rec['genre']        or '—'}")
        print(f"  Object category:  {rec['objectcat']    or '—'}")
        print(f"  Material:         {', '.join(rec['materiaal']) or '—'}")
        print(f"  Support (drager): {rec['drager']       or '—'}")
        print(f"  Date (Dutch):     {rec['date_datering'] or '—'}")
        print(f"  Date range:       {rec['date_zoekmarge'] or '—'}")
        print(f"\n  Keywords (EN):    {', '.join(rec['trefwoorden_en']) or '—'}")
        print(f"  Keywords (NL):    {', '.join(rec['trefwoorden_nl']) or '—'}")
        print(f"\n  Sitters:")
        for p in rec["personen"]:
            certainty = p["zekerheid"] or "certain"
            nummer    = p["nummer"]    or "unknown"
            print(f"    persoonsnummer={nummer:<10} certainty={certainty}")
        print(f"\n  Media ({len(rec['media'])} scans):")
        for med in rec["media"]:
            score = self.quality_score(med["soort"])
            print(f"    [{score:>3}] {med['soort']:<40} lref={med['lref']}")
        if m:
            print(f"\n  Best image URL:")
            print(f"    {self.build_url(m['lref'])}")
        print(f"{'='*60}\n")

    def overview(self) -> None:
        """Print a summary of the full dataset."""
        self._check_parsed()
        total         = len(self.records)
        with_sitter   = sum(1 for r in self.records.values()
                            if any(p["nummer"] for p in r["personen"]))
        total_lrefs   = sum(len(r["media"]) for r in self.records.values())
        multi_scan    = sum(1 for r in self.records.values()
                            if len(r["media"]) > 1)
        sitter_counts = self.sitter_portrait_counts()
        multi_sitters = self.multi_portrait_sitters()

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
        multi  = [(p, r) for p, r in self.records.items()
                  if len(r["media"]) > 1]
        sample = random.sample(multi, min(n, len(multi)))

        print(f"\n{n} RANDOM ARTWORKS WITH 2+ SCANS\n")
        for priref, rec in sample:
            print(f"priref {priref}:")
            for m in rec["media"]:
                print(f"  [{self.quality_score(m['soort']):>3}]"
                      f" {m['soort']:<40}"
                      f" {self.build_url(m['lref'])}")
            pick = self.best_media(rec["media"])
            print(f"  >>> PICKED [{self.quality_score(pick['soort'])}]"
                  f" {pick['soort']}: {self.build_url(pick['lref'])}\n")

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