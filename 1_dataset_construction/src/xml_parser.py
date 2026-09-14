"""
src/dataset/xml_parser.py
--------------------------
RKDDataset: single XML parser for the entire project.
Parses all fields needed by both downloader and analysis.

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
        priref               — unique artwork ID
        personen             — list of {nummer, zekerheid, beschrijving, status} dicts
                               note: verworpen (rejected) identifications are excluded
        media                — list of {lref, soort} dicts
        objectcat            — type of artwork (painting, print, etc.)
        date_datering        — date assigned by art historian
        date_zoekmarge       — earliest possible date (technical field)
        title_dutch          — Dutch title
        title_english        — English title
        artist_name          — name of the artist
        artist_id            — unique ID of the artist
        genre                — genre (e.g. portrait, history)
        materiaal            — list of materials (e.g. oil paint)
        drager               — support/carrier (e.g. canvas, panel)
        trefwoorden_en       — list of English keywords
        trefwoorden_nl       — list of Dutch keywords
        identificatie_grond  — list of bases for identification (e.g. herkomst, opschrift)
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

        # --- Per-record variables, reset for every new priref ---
        current_priref              = None
        current_personen            = []
        current_media               = []
        current_objectcat           = None
        current_date_datering       = None
        current_date_zoekmarge      = None
        current_lref                = None
        current_soort               = None
        current_title_dutch         = None
        current_title_english       = None
        current_artist_name         = None
        current_artist_id           = None
        current_genre               = None
        current_materiaal           = []
        current_drager              = None
        current_trefwoorden_en      = []
        current_trefwoorden_nl      = []
        current_trefwoord_en        = None
        current_trefwoord_nl        = None
        current_identificatie_grond = []

        # --- Flags: track whether we are inside a multi-line block ---
        inside_objectcat     = False
        inside_soort         = False
        inside_toeschrijving = False
        inside_trefwoord     = False
        inside_genre         = False
        inside_materiaal     = False
        inside_drager        = False

        # --- Pointer to last parsed sitter ---
        # Used to attach zekerheid, beschrijving and status to the right person.
        # Each time a new persoonsnummer is found, last_persoon is updated to
        # point to that person's dict. The next zekerheid/beschrijving/status
        # lines then update last_persoon directly.
        last_persoon = None

        with open(self.xml_file, "r", encoding="utf-8") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True,
                      desc="Parsing XML") as pbar:
                for line in f:
                    pbar.update(len(line.encode("utf-8")))
                    s = line.strip()

                    # --- New record ---
                    # Each <priref> marks the start of a new artwork.
                    # Save the previous record first, then reset everything.
                    if '<priref tag="%0"' in s and "/>" not in s:
                        if current_priref:
                            self._save_record(
                                current_priref, current_personen, current_media,
                                current_objectcat, current_date_datering,
                                current_date_zoekmarge, current_title_dutch,
                                current_title_english, current_artist_name,
                                current_artist_id, current_genre, current_materiaal,
                                current_drager, current_trefwoorden_en,
                                current_trefwoorden_nl, current_identificatie_grond,
                            )
                        current_priref              = self._extract(s)
                        current_personen            = []
                        current_media               = []
                        current_objectcat           = None
                        current_date_datering       = None
                        current_date_zoekmarge      = None
                        current_lref                = None
                        current_soort               = None
                        current_title_dutch         = None
                        current_title_english       = None
                        current_artist_name         = None
                        current_artist_id           = None
                        current_genre               = None
                        current_materiaal           = []
                        current_drager              = None
                        current_trefwoorden_en      = []
                        current_trefwoorden_nl      = []
                        current_trefwoord_en        = None
                        current_trefwoord_nl        = None
                        current_identificatie_grond = []
                        inside_objectcat            = False
                        inside_soort                = False
                        inside_toeschrijving        = False
                        inside_trefwoord            = False
                        inside_genre                = False
                        inside_materiaal            = False
                        inside_drager               = False
                        last_persoon                = None

                    # --- Persoonsnummer ---
                    # Unique ID of a depicted person.
                    # Self-closing (/>) = unidentified sitter (person present
                    # but unknown). We still add them to track group portraits.
                    # Status starts as None — updated when status tag is found.
                    elif '<persoonsnummer tag="z3"' in s and "linkref" not in s:
                        if "/>" not in s:
                            val = self._extract(s)
                            if val:
                                last_persoon = {
                                    "nummer":       val,
                                    "zekerheid":    None,
                                    "beschrijving": None,
                                    "status":       None,  # huidig / verworpen / None
                                }
                                current_personen.append(last_persoon)
                        else:
                            # Unidentified sitter — no number, but we track them
                            # so group portrait structure is preserved
                            last_persoon = {
                                "nummer":       None,
                                "zekerheid":    None,
                                "beschrijving": None,
                                "status":       None,
                            }
                            current_personen.append(last_persoon)

                    # --- Zekerheid (certainty of identification) ---
                    # Empty/self-closing = no qualifier given, stored as None.
                    # Possible values: waarschijnlijk (probably),
                    #                  mogelijk (possibly), genaamd (so-called)
                    elif '<zekerheid_identificatie_portret' in s:
                        if "/>" not in s and last_persoon is not None:
                            val = self._extract(s)
                            if val:
                                last_persoon["zekerheid"] = val

                    # --- Status identificatie portret ---
                    # Whether the identification is accepted or rejected.
                    # huidig   = current/accepted identification
                    # verworpen = rejected — was proposed but not accepted by RKD
                    # None     = no status given (treated as unidentified)
                    # IMPORTANT: verworpen sitters are filtered out in _save_record()
                    elif '<status_identificatie_portret' in s:
                        if "/>" not in s and last_persoon is not None:
                            val = self._extract(s)
                            if val:
                                last_persoon["status"] = val

                    # --- Persoonsbeschrijving ---
                    # Where the person is located in the painting.
                    # e.g. "tweede van links", "geheel rechts", "voorgrond"
                    elif '<persoonsbeschrijving' in s and "linkref" not in s:
                        if "/>" not in s and last_persoon is not None:
                            val = self._extract(s)
                            if val:
                                last_persoon["beschrijving"] = val

                    # --- Identificatie grond ---
                    # Basis for the identification — per artwork, not per sitter.
                    # e.g. herkomst (provenance), opschrift (inscription),
                    #      wapen (coat of arms), vererving (inheritance/descent)
                    elif '<identificatie_grond' in s and "/>" not in s:
                        val = self._extract(s)
                        if val:
                            current_identificatie_grond.append(val)

                    # --- Media lref ---
                    # The image scan ID — one per media block.
                    # A single artwork can have multiple lrefs (multiple scans).
                    elif '<media.original_file_name_lref' in s and "/>" not in s:
                        current_lref = self._extract(s)

                    # --- Soort afbeelding (image type, multi-line) ---
                    # e.g. digital image, photograph, black-and-white reproduction
                    # Used for quality ranking — see QUALITY_RANK above.
                    elif '<soort_afbeelding' in s:
                        inside_soort  = True
                        current_soort = None

                    elif inside_soort and '<value lang="en-US"' in s:
                        current_soort = self._extract(s)
                        inside_soort  = False

                    elif '</soort_afbeelding>' in s:
                        inside_soort = False

                    # --- End of media block ---
                    # When </media> is found, save lref + soort as one media item.
                    # Reset lref and soort for the next media block.
                    elif '</media>' in s:
                        if current_lref:
                            soort = current_soort or "unknown"
                            if soort not in EXCLUDE_TYPES:
                                current_media.append({
                                    "lref":  current_lref,
                                    "soort": soort,
                                })
                        current_lref  = None
                        current_soort = None
                        inside_soort  = False

                    # --- Object category (multi-line) ---
                    # e.g. painting, drawing, print, photograph, sculpture
                    # ! stores only first object category, since it seems to be the most important one
                    # print_unique_values('object_category') scans raw XML file so that will find more counts then records
                    # since sometimes there are stored more then one categorie per record
                    elif '<objectcategorie' in s and "linkref" not in s:
                        inside_objectcat = True

                    elif inside_objectcat and '<value lang="en-US"' in s:
                        current_objectcat = self._extract(s)
                        inside_objectcat  = False

                    elif '</objectcategorie>' in s:
                        inside_objectcat = False

                    # --- Genre (multi-line) ---
                    # e.g. portrait, history (visual work)
                    # Only the first occurrence per record is kept.
                    elif '<genre tag=' in s:
                        inside_genre = True

                    elif inside_genre and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val and not current_genre:
                            current_genre = val
                        inside_genre = False

                    elif '</genre>' in s:
                        inside_genre = False

                    # --- Materiaal (multi-line, multiple values per record) ---
                    # e.g. oil paint, watercolor, grisaille
                    # Multiple materials are stored as a list.
                    elif '<materiaal tag=' in s:
                        inside_materiaal = True

                    elif inside_materiaal and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val:
                            current_materiaal.append(val)
                        inside_materiaal = False

                    elif '</materiaal>' in s:
                        inside_materiaal = False

                    # --- Drager (multi-line) ---
                    # The physical support the artwork is made on.
                    # e.g. canvas, panel (wood), paper, copper
                    # Only the first occurrence per record is kept.
                    elif '<drager tag=' in s:
                        inside_drager = True

                    elif inside_drager and '<value lang="en-US"' in s:
                        val = self._extract(s)
                        if val and not current_drager:
                            current_drager = val
                        inside_drager = False

                    elif '</drager>' in s:
                        inside_drager = False

                    # --- Title Dutch ---
                    # benaming_kunstwerk = Dutch title of the artwork.
                    # Only first occurrence kept.
                    elif '<benaming_kunstwerk' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_title_dutch:
                            current_title_dutch = val

                    # --- Title English ---
                    elif '<titel_engels' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_title_english:
                            current_title_english = val

                    # --- Artist name + ID (inside toeschrijving block) ---
                    # toeschrijving = attribution (who made the artwork).
                    # The block can contain multiple attributions (e.g. "circle of",
                    # "attributed to"). We take the first name + ID found.
                    elif '<toeschrijving>' in s:
                        inside_toeschrijving = True

                    elif inside_toeschrijving and '<naam tag="na"' in s \
                            and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_artist_name:
                            current_artist_name = val

                    elif inside_toeschrijving and '<naam_linkref' in s \
                            and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_artist_id:
                            current_artist_id = val

                    elif '</toeschrijving>' in s:
                        inside_toeschrijving = False

                    # --- Datering (art historian assigned date) ---
                    # The date as assigned by the cataloguer.
                    # This is the preferred date field. Only first occurrence kept.
                    elif '<datering tag=' in s and "/>" not in s:
                        val = self._extract(s)
                        if val and not current_date_datering:
                            current_date_datering = val

                    # --- Zoekmarge begindatum (technical search range start) ---
                    # Database field for filtering by date range.
                    # Less precise than datering but more consistently filled.
                    # Used as fallback when datering is absent.
                    elif '<zoekmarge_begindatum' in s and "/>" not in s:
                        val = self._extract(s)
                        if val:
                            current_date_zoekmarge = val

                    # --- RKD algemene trefwoorden (keywords, multi-line) ---
                    # Subject keywords assigned by RKD cataloguers.
                    # Each keyword is a separate block with both Dutch + English.
                    # e.g. "woman's portrait", "half-length", "pearl necklace"
                    elif '<RKD_algemene_trefwoorden ' in s:
                        inside_trefwoord     = True
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

        # Save the last record — no new <priref> triggers the save at end of file
        if current_priref:
            self._save_record(
                current_priref, current_personen, current_media,
                current_objectcat, current_date_datering,
                current_date_zoekmarge, current_title_dutch,
                current_title_english, current_artist_name,
                current_artist_id, current_genre, current_materiaal,
                current_drager, current_trefwoorden_en,
                current_trefwoorden_nl, current_identificatie_grond,
            )

        self._parsed = True
        print(f"Parsed {len(self.records)} records.")

    def _save_record(self, priref, personen, media, objectcat,
                     date_datering, date_zoekmarge, title_dutch,
                     title_english, artist_name, artist_id, genre,
                     materiaal, drager, trefwoorden_en, trefwoorden_nl,
                     identificatie_grond):
        """
        Package all collected fields into a dict and store in self.records.

        Verworpen (rejected) identifications are filtered out here —
        they were proposed in the past but not accepted by the RKD.
        Blank proposal slots are also filtered out — these are <voorgestelde> entries
        where both status and persoonsbeschrijving are empty. They represent unused
        identification proposal fields, not real people in the painting (1379 cases).
        Empty-status entries WITH a persoonsbeschrijving are kept — these are real
        unidentified sitters whose position in the painting is known (312 cases).
        """
        # Filter out rejected identifications before saving.
        # verworpen = the RKD proposed this identification but later rejected it.
        # We use .lower() to handle capitalisation variants (e.g. "Verworpen").
        filtered_personen = [
            p for p in personen
            if not (p.get("status") or "").lower() == "verworpen"         # drop rejected
            and not (
                not (p.get("status") or "")                               # drop blank slots:
                and not (p.get("beschrijving") or "")                     # empty status + no position
            )
        ]

        self.records[priref] = {
            "priref":               priref,
            "personen":             filtered_personen,   # verworpen already removed
            "media":                media.copy(),
            "objectcat":            objectcat,
            "date_datering":        date_datering,
            "date_zoekmarge":       date_zoekmarge,
            "title_dutch":          title_dutch,
            "title_english":        title_english,
            "artist_name":          artist_name,
            "artist_id":            artist_id,
            "genre":                genre,
            "materiaal":            materiaal.copy(),
            "drager":               drager,
            "trefwoorden_en":       trefwoorden_en.copy(),
            "trefwoorden_nl":       trefwoorden_nl.copy(),
            "identificatie_grond":  identificatie_grond.copy(),
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
        Get a flat list of all lrefs to download.

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
        """
        Count how many artworks each persoonsnummer appears in.
        Only counts huidig (accepted) identifications — verworpen already
        filtered out during parsing.
        """
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

    def filter_records(self, filter_identified: bool = True,
                       filter_multi_portrait: bool = False) -> dict:
        """
        Return a filtered subset of records.

        filter_identified:
            Keep only artworks with at least one accepted persoonsnummer.
            Goes from ~103k → ~66k artworks.

        filter_multi_portrait:
            Keep only artworks where at least one sitter appears in 2+ artworks.
            Goes from ~66k → ~47k artworks.
            This is the training-ready subset — a model needs multiple examples
            per person to learn what they look like.
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
    # Printing / exploration
    # ------------------------------------------------------------------

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

    def print_record(self, priref: str = None) -> None:
        """
        Print all parsed fields for a single record.
        If no priref given, prints the first record.

        Args:
            priref: the priref ID to print. None = first record.
        """
        self._check_parsed()

        if priref:
            rec = self.records.get(str(priref))
            if not rec:
                print(f"priref '{priref}' not found.")
                return
        else:
            rec = next(iter(self.records.values()))

        m = self.best_media(rec["media"])

        print(f"\n{'='*60}")
        print(f"  RECORD: priref {rec['priref']}")
        print(f"{'='*60}")
        print(f"  Title (Dutch):        {rec['title_dutch']    or '—'}")
        print(f"  Title (English):      {rec['title_english']  or '—'}")
        print(f"  Artist:               {rec['artist_name']    or '—'} "
              f"(ID: {rec['artist_id'] or '—'})")
        print(f"  Genre:                {rec['genre']          or '—'}")
        print(f"  Object category:      {rec['objectcat']      or '—'}")
        print(f"  Material:             "
              f"{', '.join(rec['materiaal']) if rec['materiaal'] else '—'}")
        print(f"  Support (drager):     {rec['drager']         or '—'}")
        print(f"  Date (Dutch):         {rec['date_datering']  or '—'}")
        print(f"  Date range:           {rec['date_zoekmarge'] or '—'}")
        print(f"  Identification basis: "
              f"{', '.join(rec['identificatie_grond']) if rec['identificatie_grond'] else '—'}")
        print(f"\n  Keywords (EN): "
              f"{', '.join(rec['trefwoorden_en']) if rec['trefwoorden_en'] else '—'}")
        print(f"  Keywords (NL): "
              f"{', '.join(rec['trefwoorden_nl']) if rec['trefwoorden_nl'] else '—'}")

        # Print each sitter with all their fields.
        # Note: verworpen sitters are already excluded — these are only
        # huidig (accepted) or unknown (None status) sitters.
        print(f"\n  Sitters ({len(rec['personen'])}):")
        for p in rec["personen"]:
            nummer       = p["nummer"]       or "— (unidentified)"
            status       = p["status"]       or "—"   # huidig / None
            zekerheid    = p["zekerheid"]    or "—"   # waarschijnlijk / mogelijk / genaamd / None
            beschrijving = p["beschrijving"] or "—"   # position in painting
            print(f"    ID:           {nummer}")
            print(f"    Status:       {status}")
            print(f"    Certainty:    {zekerheid}")
            print(f"    Position:     {beschrijving}")
            print()

        print(f"  Media ({len(rec['media'])} scans):")
        for med in rec["media"]:
            score = self.quality_score(med["soort"])
            print(f"    [{score:>3}] {med['soort']:<40} lref={med['lref']}")

        if m:
            print(f"\n  Best image URL:")
            print(f"    {self.build_url(m['lref'])}")
        print(f"{'='*60}\n")

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

    def print_all_tags(self, n_lines: int = 1000) -> None:
        """
        Print all unique XML tag names found in the first n_lines of the file.
        Lightweight exploration — does not require .parse() first.
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

    def print_unique_values(self, tag_name: str,
                            n_lines: int = None) -> None:
        """
        Scan the XML and print all unique values for a given tag.
        Does not require .parse() first.

        Args:
            tag_name: the XML tag to search (e.g. "zekerheid_identificatie_portret")
            n_lines:  lines to scan. None = full file.

        Example:
            dataset.print_unique_values("status_identificatie_portret")
            dataset.print_unique_values("objectcategorie")
        """
        from collections import Counter

        file_size    = os.path.getsize(self.xml_file)
        value_counts = Counter()
        open_tag     = f"<{tag_name} "
        close_tag    = f"</{tag_name}>"
        inside       = False

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
                            val = self._extract(s)
                            if val:
                                # Inline value on same line as tag
                                value_counts[val] += 1
                            else:
                                # Value is on next lines (multi-line field)
                                inside = True

                    elif inside and "<value" in s and 'lang="en-US"' in s:
                        val = self._extract(s)
                        if val:
                            value_counts[val] += 1

                    elif inside and close_tag in s:
                        inside = False

                    if n_lines and i >= n_lines:
                        break

        print(f"\n  Unique values for '{tag_name}':\n")
        print(f"  {'Value':<50} {'Count':>8}")
        print(f"  {'-'*60}")
        for val, count in value_counts.most_common():
            print(f"  {val:<50} {count:>8}")
        print(f"\n  Total unique values: {len(value_counts)}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_parsed(self):
        """Raise an error if .parse() has not been called yet."""
        if not self._parsed:
            raise RuntimeError("Call .parse() before using this method.")

    @staticmethod
    def _extract(line: str) -> str:
        """Extract text content between > and < on a single XML line."""
        try:
            return line.split(">")[1].split("<")[0].strip()
        except IndexError:
            return ""