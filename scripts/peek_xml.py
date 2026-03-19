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

dataset.parse()
dataset.overview()

# dataset.sample_multi_scan(20)
# dataset.portraits_for_sitter("107491")
# dataset.multi_portrait_sitters(min_portraits=2)
# dataset.get_lrefs(best_only=True)

# dataset.print_record("5")                              # Print first record 
#                                                        # Or other, based on priref
# dataset.print_record("19") 
# dataset.print_record("73")     

# ================================== DOWNLOAD ==================================

# downloader = RKDDownloader(dataset)
# downloader.download(max_downloads=200)    # test first
# downloader.download()                     # full download — run overnight