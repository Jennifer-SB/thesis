import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from tqdm import tqdm
import os

# Print the first 100 lines ===================================================

# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     for i, line in enumerate(f):
#         print(line, end="")
#         if i >= 100:
#             break

# Collect all unique name tags ================================================

# tags = set()

# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     content = ""
#     for i, line in enumerate(f):
#         content += line
#         if i >= 1000:
#             break

# # Add closing tags to make it valid XML
# content += "</record></recordList></adlibXML>"

# try:
#     root = ET.fromstring(content)
#     for elem in root.iter():
#         tags.add(elem.tag)
# except ET.ParseError:
#     pass

# for tag in sorted(tags):
#     print(tag)

""""
persoonsnummer — the person's ID number (= your "identificationnumber_person")
persoonsnummer_linkref — the linked reference for the person
status_identificatie_portret — portrait identification status
zekerheid_identificatie_portret — certainty of the portrait identification (bonus — tells you how confident the identification is)
"""

# Check status_identificatie_portret ====================================================

# with open(r"D:\thesis\data\RKDimages.xml", "r", encoding="utf-8") as f:
#     for i, line in enumerate(f):
#         if "status_identificatie_portret" in line or "persoonsnummer" in line:
#             print(f"Line {i}: {line}", end="")
#         if i > 50000:
#             break

# Start counting double/triple portraits ================================================

# XML_FILE = r"D:\thesis\data\RKDimages.xml"
# file_size = os.path.getsize(XML_FILE)

# # priref → set of persoonsnummers in that record
# records = defaultdict(set)
# current_priref = None

# with open(XML_FILE, "r", encoding="utf-8") as f:
#     with tqdm(total=file_size, unit="B", unit_scale=True, desc="Scanning") as pbar:
#         for line in f:
#             pbar.update(len(line.encode("utf-8")))
#             stripped = line.strip()

#             # Detect record ID
#             if '<priref tag="%0"' in stripped and "/>" not in stripped:
#                 try:
#                     value = stripped.split(">")[1].split("<")[0].strip()
#                     if value:
#                         current_priref = value
#                 except IndexError:
#                     pass

#             # Detect persoonsnummer
#             elif '<persoonsnummer tag="z3"' in stripped and "linkref" not in stripped and "/>" not in stripped:
#                 if current_priref:
#                     try:
#                         value = stripped.split(">")[1].split("<")[0].strip()
#                         if value:
#                             records[current_priref].add(value)
#                     except IndexError:
#                         pass

# # Count portraits per sitter (by unique priref)
# persoon_counts = Counter()
# for priref, personen in records.items():
#     for p in personen:
#         persoon_counts[p] += 1

# portrait_distribution = Counter(persoon_counts.values())

# print(f"\n=== SITTER OVERVIEW (deduplicated by priref) ===")
# print(f"  Total unique artworks:  {len(records)}")
# print(f"  Artworks with sitter:   {sum(1 for v in records.values() if v)}")
# print(f"  Unique sitters:         {len(persoon_counts)}")

# print(f"\n=== PORTRAITS PER SITTER ===")
# print(f"  # portraits  |  # sitters")
# print(f"  -------------|----------")
# for n in sorted(portrait_distribution.keys()):
#     print(f"  {n:<13} |  {portrait_distribution[n]}")

# print(f"\n  Top 10 most-portrayed sitters:")
# for persoon, count in persoon_counts.most_common(10):
#     print(f"  persoonsnummer {persoon}: {count} portraits")

# See RKD images manually =================================================================

# XML_FILE = r"D:\thesis\data\RKDimages.xml"

# results = []

# with open(XML_FILE, "r", encoding="utf-8") as f:
#     for line in f:
#         stripped = line.strip()
#         if '<media.original_file_name_lref' in stripped and "/>" not in stripped:
#             try:
#                 value = stripped.split(">")[1].split("<")[0].strip()
#                 if value:
#                     url = f"https://media.rkd.nl/iiif/{value}/full/max/0/default.jpg"
#                     results.append((value, url))
#             except IndexError:
#                 pass
#         if len(results) >= 50:
#             break

# print(f"First 50 lref numbers and their URLs:\n")
# for i, (lref, url) in enumerate(results, 1):
#     print(f"{i:>3}. {lref:<15} {url}")

# Check images of person 107491 (258 portraits) to be sure =================================

# XML_FILE = r"D:\thesis\data\RKDimages.xml"
# file_size = os.path.getsize(XML_FILE)

# TARGET_PERSOON = "107491"

# # We need to collect: for each priref, the persoonsnummers and the lrefs
# current_priref = None
# current_personen = set()
# current_lrefs = []

# results = []  # list of (priref, lref) for our target person

# with open(XML_FILE, "r", encoding="utf-8") as f:
#     with tqdm(total=file_size, unit="B", unit_scale=True, desc="Scanning") as pbar:
#         for line in f:
#             pbar.update(len(line.encode("utf-8")))
#             stripped = line.strip()

#             # New record starts
#             if '<priref tag="%0"' in stripped and "/>" not in stripped:
#                 # Save previous record if relevant
#                 if current_priref and TARGET_PERSOON in current_personen:
#                     for lref in current_lrefs:
#                         results.append((current_priref, lref))
#                 # Reset
#                 try:
#                     current_priref = stripped.split(">")[1].split("<")[0].strip()
#                 except IndexError:
#                     current_priref = None
#                 current_personen = set()
#                 current_lrefs = []

#             elif '<persoonsnummer tag="z3"' in stripped and "linkref" not in stripped and "/>" not in stripped:
#                 try:
#                     value = stripped.split(">")[1].split("<")[0].strip()
#                     if value:
#                         current_personen.add(value)
#                 except IndexError:
#                     pass

#             elif '<media.original_file_name_lref' in stripped and "/>" not in stripped:
#                 try:
#                     value = stripped.split(">")[1].split("<")[0].strip()
#                     if value:
#                         current_lrefs.append(value)
#                 except IndexError:
#                     pass

# # Don't forget the last record
# if current_priref and TARGET_PERSOON in current_personen:
#     for lref in current_lrefs:
#         results.append((current_priref, lref))

# print(f"\nFound {len(results)} images for persoonsnummer {TARGET_PERSOON}:\n")
# for i, (priref, lref) in enumerate(results, 1):
#     url = f"https://media.rkd.nl/iiif/{lref}/full/max/0/default.jpg"
#     print(f"{i:>3}. priref={priref:<10} {url}")

# Check how many images have been saved multiple times and quality control ===================

"""
=== MEDIA OVERVIEW ===
  Total unique artworks (priref):     103637
  Artworks with 1 media/scan:         68424
  Artworks with 2+ scans:             35213
  Total lrefs (incl. duplicates):     150437
  Lrefs saved if 1 per priref:        103637
  Duplicates that would be removed:   46800
"""

# XML_FILE = r"D:\thesis\data\RKDimages.xml"
# file_size = os.path.getsize(XML_FILE)

# current_priref = None
# current_lref = None
# current_soort_val = None
# inside_soort = False
# priref_to_media = defaultdict(list)

# with open(XML_FILE, "r", encoding="utf-8") as f:
#     with tqdm(total=file_size, unit="B", unit_scale=True, desc="Scanning") as pbar:
#         for line in f:
#             pbar.update(len(line.encode("utf-8")))
#             stripped = line.strip()

#             if '<priref tag="%0"' in stripped and "/>" not in stripped:
#                 current_priref = stripped.split(">")[1].split("<")[0].strip()

#             elif '<media.original_file_name_lref' in stripped and "/>" not in stripped:
#                 try:
#                     current_lref = stripped.split(">")[1].split("<")[0].strip()
#                 except IndexError:
#                     pass

#             elif '<soort_afbeelding' in stripped:
#                 inside_soort = True
#                 current_soort_val = None

#             elif inside_soort and '<value lang="en-US"' in stripped:
#                 try:
#                     current_soort_val = stripped.split(">")[1].split("<")[0].strip()
#                     inside_soort = False
#                 except IndexError:
#                     pass

#             elif '</soort_afbeelding>' in stripped:
#                 inside_soort = False

#             elif '</media>' in stripped:
#                 if current_priref and current_lref:
#                     priref_to_media[current_priref].append({
#                         "lref": current_lref,
#                         "soort": current_soort_val or "unknown"
#                     })
#                 current_lref = None
#                 current_soort_val = None
#                 inside_soort = False

# # --- Quality types ---
# soort_counts = Counter()
# for media_list in priref_to_media.values():
#     for m in media_list:
#         soort_counts[m["soort"]] += 1

# print(f"\n=== SOORT AFBEELDING (image types) ===")
# for soort, count in soort_counts.most_common():
#     print(f"  {soort:<40} {count:>8}")

# # --- Show examples with multiple scans ---
# print(f"\n=== EXAMPLE: first 5 artworks with multiple scans ===")
# count = 0
# for priref, media_list in priref_to_media.items():
#     if len(media_list) > 1:
#         print(f"\n  priref {priref}:")
#         for m in media_list:
#             print(f"    lref={m['lref']:<12} soort={m['soort']}")
#         count += 1
#         if count >= 5:
#             break

# ===================================================================================
# OBJECT BASED ======================================================================
# ===================================================================================

"""
peek_xml.py — exploration scratchpad
"""

from xml_parser import RKDDataset
from downloader import RKDDownloader

dataset = RKDDataset()
dataset.parse()
dataset.overview()
dataset.sample_multi_scan(20)
# dataset.portraits_for_sitter("107491")
# dataset.multi_portrait_sitters(min_portraits=2)
# dataset.get_lrefs(best_only=True)

downloader = RKDDownloader(dataset, delay=1.0)
# Test with 10 images first
downloader.download(max_downloads=200)

# When happy with the result, run the full download:
# downloader.download()

