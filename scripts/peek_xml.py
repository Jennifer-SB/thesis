"""
scripts/peek_xml.py: Run checks, test downloads, verify data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dataset.xml_parser import RKDDataset
from src.dataset.downloader import RKDDownloader

from collections import Counter

# ================================== EXPLORE XML FILE ==================================

dataset = RKDDataset()
dataset.parse()

# Print all unique XML tags from the first 1000 lines
# dataset.print_all_tags()

"""
Relevant fields:
- persoonsnummer:                unique person ID
- zekerheid_identificatie_portret: certainty of identification
- objectcategorie:               type of artwork
- soort_afbeelding:              type of scan/image
- afbeelding_tonen_leveren:      whether image is freely downloadable (NOLIM)
"""

# Explore what values specific fields contain (scans full file by default)
# dataset.print_unique_values("zekerheid_identificatie_portret")          # is counted per sitter, not per artwork
# dataset.print_unique_values("objectcategorie")
# dataset.print_unique_values("soort_afbeelding")
# dataset.print_unique_values("afbeelding_tonen_leveren")
# dataset.print_unique_values("RKD_algemene_trefwoorden")
# dataset.print_unique_values('genre')
# dataset.print_unique_values('materiaal')

# ===== STARTING SET: RKDimages filtered on keywords that contained 'portrait' ======
# portrait_keywords = Counter()

# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     inside = False
#     for line in f:
#         s = line.strip()
#         if '<RKD_algemene_trefwoorden' in s:
#             inside = True
#         elif inside and '<value lang="en-US"' in s:
#             val = dataset._extract(s)
#             if val and "portrait" in val.lower():
#                 portrait_keywords[val] += 1
#             inside = False
#         elif '</RKD_algemene_trefwoorden>' in s:
#             inside = False

# print(f"\n=== PORTRAIT-RELATED KEYWORDS ===\n")
# print(f"  {'Keyword':<50} {'Count':>8}")
# print(f"  {'-'*60}")
# for val, count in portrait_keywords.most_common():
#     print(f"  {val:<50} {count:>8}")
# print(f"\n  Total portrait keywords: {len(portrait_keywords)}")

# Print the full XML of the first record, nicely formatted ----------------------------
# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     inside = False
#     for line in f:
#         if '<record ' in line or '<record>' in line:
#             inside = True
#         if inside:
#             print(line, end="")
#         if '</record>' in line and inside:
#             break

# RESEARCH: status identificatie portret? ----------------------------------------------

# dataset.print_unique_values("status_identificatie_portret")
"""
Unique values for 'status_identificatie_portret':

  Value                                                 Count
  ------------------------------------------------------------
  huidig                                                77498
  verworpen                                              2455
  (empty)                                                1691
  Huidig                                                    1
"""

# dataset.parse()
# print("\nExamples of records with empty status_identificatie_portret:\n")

# count = 0
# for rec in dataset.records.values():
#     priref_val = rec["priref"]

#     # Scan raw XML for this record's status lines
#     statuses   = []
#     personen   = []
#     inside     = False

#     with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#         for line in f:
#             if 'priref="' + priref_val + '"' in line:
#                 inside = True
#             if inside:
#                 if "status_identificatie_portret" in line:
#                     if "/>" in line:
#                         statuses.append("(empty)")
#                     else:
#                         statuses.append(dataset._extract(line))
#                 if '<persoonsnummer tag="z3"' in line and "linkref" not in line:
#                     if "/>" in line:
#                         personen.append("(unknown)")
#                     else:
#                         personen.append(dataset._extract(line))
#             if '</record>' in line and inside and \
#                'priref="' + priref_val + '"' not in line:
#                 break

#     # Only show records that have at least one empty status
#     if "(empty)" in statuses and len(statuses) > 0:
#         print(f"priref: {priref_val} — {rec['title_dutch']}")
#         print(f"  Persoonsnummers: {personen}")
#         print(f"  Statuses:        {statuses}")
#         print(f"  URL: {dataset.build_url(dataset.best_media(rec['media'])['lref']) if rec['media'] else '—'}")
#         print()
#         count += 1

#     if count >= 10:
#         break

"""
[...]
priref: 2237 — Portrait historié van Salomon de Bray (1597-1664), met zijn familie en een bediende
  Persoonsnummers: ['7615', '203516', '7612', '203517', '133764', '203519', '203520', '122275', '203521', '(unknown)']
  Statuses:        ['huidig', 'huidig', 'huidig', 'huidig', 'huidig', 'huidig', 'huidig', 'huidig', 'huidig', '(empty)']
  URL: https://media.rkd.nl/iiif/9205919/full/max/0/default.jpg
[...]
"""

# ====================================================================

# dataset.parse()
# dataset.print_record(priref="21990")
# dataset.print_record("2237")
# dataset.print_record("743")
# dataset.print_record("8856")
# dataset.print_record("104254")

# print("\n10 artworks with both known AND unknown sitters:\n")

# count = 0
# for rec in dataset.records.values():
#     has_known   = any(p["nummer"] for p in rec["personen"])
#     has_unknown = any(not p["nummer"] for p in rec["personen"])

#     if has_known and has_unknown:
#         m = dataset.best_media(rec["media"])
#         url = dataset.build_url(m["lref"]) if m else "—"
#         print(f"priref: {rec['priref']}")
#         print(f"title:  {rec['title_dutch'] or '—'}")
#         print(f"url:    {url}")
#         print(f"sitters ({len(rec['personen'])}):")
#         for p in rec["personen"]:
#             nummer = p["nummer"] or "— (unknown)"
#             print(f"  ID: {nummer:<15} status: {p['status'] or '—':<10} position: {p['beschrijving'] or '—'}")
#         print()
#         count += 1
#     if count >= 10:
#         break

# ================================== PARSE ==================================

# dataset.parse()
# dataset.overview()

# dataset.sample_multi_scan(20)
# dataset.portraits_for_sitter("107491")
# dataset.multi_portrait_sitters(min_portraits=2)
# dataset.get_lrefs(best_only=True)

# dataset.print_record("5")                              # Print first record 
#                                                        # Or other, based on priref
# dataset.print_record("19") 
# dataset.print_record("73")     

# === How are people on group portraits saved (identified vs. unidentified) ===

# # Print full info for 10 paintings with multiple sitters
# # where at least one sitter is unidentified (nummer = None)
# print("\n10 GROUP PORTRAITS WITH AT LEAST ONE UNIDENTIFIED SITTER\n")

# count = 0
# for rec in dataset.records.values():
#     personen         = rec["personen"]
#     has_multiple     = len(personen) >= 2
#     has_unidentified = any(not p["nummer"] for p in personen)
#     has_identified   = any(p["nummer"] for p in personen)

#     if has_multiple and has_unidentified and has_identified:
#         dataset.print_record(rec["priref"])
#         count += 1
#     if count >= 10:
#         break

# # =============== CLEAN SET: ====================

# dataset.parse()

# from collections import Counter

# # --- Clean set definition ---
# # After parsing, verworpen (rejected) identifications are already removed.
# # A "clean" record must have:
# #   1. Exactly 1 identified sitter (nummer is not None)
# #   2. No unidentified sitters (no None nummer entries)
# # This gives us single-person portraits with one unambiguous ID.

# clean_records = {
#     priref: rec for priref, rec in dataset.records.items()
#     if sum(1 for p in rec["personen"] if p["nummer"]) == 1       # exactly 1 known
#     and sum(1 for p in rec["personen"] if not p["nummer"]) == 0  # zero unknown
# }

# # Count portraits per sitter within the clean set
# clean_sitter_counts = Counter()
# for rec in clean_records.values():
#     for p in rec["personen"]:
#         if p["nummer"]:
#             clean_sitter_counts[p["nummer"]] += 1

# # Only sitters with 2+ portraits are usable for training
# multi_sitters = {p: c for p, c in clean_sitter_counts.items() if c >= 2}

# print(f"\n=== CLEAN SET (after verworpen filter) ===\n")
# print(f"  How we filtered:")
# print(f"  1. verworpen/unknown+no_description identifications removed during parsing")
# print(f"  2. kept only records with exactly 1 known sitter")
# print(f"  3. kept only records with zero unknown sitters")
# print(f"\n  Clean records:                    {len(clean_records)}")
# print(f"  Unique sitters in clean set:      {len(clean_sitter_counts)}")
# print(f"  Sitters with 2+ portraits:        {len(multi_sitters)}")
# print(f"  Portraits usable for training:    {sum(multi_sitters.values())}")

# ================================== DOWNLOAD ==================================

# dataset.parse()

downloader = RKDDownloader(dataset)
# # downloader.download(max_downloads=200)    # test first
downloader.download()                         # full download: run overnight