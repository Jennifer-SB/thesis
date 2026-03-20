"""
scripts/peek_xml.py: Run checks, test downloads, verify data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dataset.xml_parser import RKDDataset
from src.dataset.downloader import RKDDownloader

# ================================== EXPLORE XML FILE ==================================

dataset = RKDDataset()

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

# Print the full XML of the first record, nicely formatted
# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     inside = False
#     for line in f:
#         if '<record ' in line or '<record>' in line:
#             inside = True
#         if inside:
#             print(line, end="")
#         if '</record>' in line and inside:
#             break

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

# Print full info for 10 paintings with multiple sitters
# where at least one sitter is unidentified (nummer = None)
print("\n10 GROUP PORTRAITS WITH AT LEAST ONE UNIDENTIFIED SITTER\n")

count = 0
for rec in dataset.records.values():
    personen         = rec["personen"]
    has_multiple     = len(personen) >= 2
    has_unidentified = any(not p["nummer"] for p in personen)
    has_identified   = any(p["nummer"] for p in personen)

    if has_multiple and has_unidentified and has_identified:
        dataset.print_record(rec["priref"])
        count += 1
    if count >= 10:
        break

from collections import Counter

# Find all records with exactly 1 identified sitter and no unknowns
clean_records = {
    priref: rec for priref, rec in dataset.records.items()
    if sum(1 for p in rec["personen"] if p["nummer"]) == 1
    and sum(1 for p in rec["personen"] if not p["nummer"]) == 0
}

# Count how many times each sitter appears in this clean set
clean_sitter_counts = Counter()
for rec in clean_records.values():
    for p in rec["personen"]:
        if p["nummer"]:
            clean_sitter_counts[p["nummer"]] += 1

# Count distribution
portrait_distribution = Counter(clean_sitter_counts.values())
multi_sitters = {p: c for p, c in clean_sitter_counts.items() if c >= 2}

print(f"Total clean records (1 identified, no unknowns): {len(clean_records)}")
print(f"Unique sitters in clean set:                     {len(clean_sitter_counts)}")
print(f"Sitters with 2+ portraits in clean set:          {len(multi_sitters)}")
print(f"Portraits usable for training (clean set):       {sum(multi_sitters.values())}")
print(f"\n  # portraits  |  # sitters")
print(f"  -------------|----------")
for n in sorted(portrait_distribution.keys()):
    print(f"  {n:<13} |  {portrait_distribution[n]}")

# ================================== DOWNLOAD ==================================

# downloader = RKDDownloader(dataset)
# downloader.download(max_downloads=200)    # test first
# downloader.download()                     # full download — run overnight