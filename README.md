# Thesis Jennifer: Face Recognition on RKD Historical Portrait Paintings

Face verification on the [RKD (Rijksbureau voor Kunsthistorische Documentatie)](https://rkd.nl) dataset of historical Dutch and Flamish portrait paintings.


## Research Questions

| | |
|---|---|
| **RQ1** | Evaluate baseline ResNet100 + CosFace (pre-trained, no fine-tuning) on RKD dataset (Klink & Bunda, 2025) |
| **RQ2** | SE-blocks (Squeeze-and-Excitation) in RetinaFace for face detection in paintings |
| **RQ3** | LoRA-CLIP + IResNet100 embeddings for face verification (fine-tuning) (Poh et al., 2025) |
| **RQ4** | *(if time)* Hyperbolic vs Euclidean CLIP embeddings for face recognition performance |


## Dataset Pipeline

```
RKDimages.xml  (103,637 artwork records)
      │
      ▼  src/dataset/downloader.py
D:/thesis/images/  (~144,763 .jpg files)
      │
      ▼  scripts/select_images.py  →  dataset_manifest.csv
Single known-sitter portraits  (56,740)
      │
      ▼  [WSL — InsightFace, see below]  →  D:/thesis/gezichten/
Solo-face portraits  (50,986)
      │
      ▼  scripts/build_training_table.py  →  training_set.csv
27,337 training portraits  |  7,981 identities
      │
      ▼  scripts/build_personen.py
D:/thesis/personen/{sitter_id}/{lref}.jpg  ← final training dataset
```


### Filtering summary

| Step | Remaining | Removed |
|---|---|---|
| XML artwork records | 103,637 | — |
| Images on disk (after download) | ~144,763 unique files | 73 failed permanently |
| Prirefs with usable image | ~97,941 | 5,696 (no image / placeholder only) |
| Single known-sitter filter | 56,740 | ~41,201 (group portraits / unknown sitters) |
| Solo-face filter (RetinaFace) | 50,986 | 3,755 no face · 1,999 multi-face |
| Identity filter (≥2 portraits) | **27,337 portraits / 7,981 identities** | ~23,649 (sitter appears only once) |

## Face Detection & Embedding (WSL — GPU required)

Face detection and embedding extraction were run in a **Linux WSL2 environment** using [InsightFace](https://github.com/deepinsight/insightface). This step requires a CUDA-capable GPU and is not part of the Windows pipeline.

**Models used:**
- **RetinaFace** — face detection and cropping (`D:/thesis/gezichten/{lref}_0.jpg`, `_1.jpg`, ...)
- **ArcFace ResNet100 trained on Glint360K** — face recognition embeddings → `features.pkl`

**To reproduce:**
```bash
# In WSL2 with CUDA
pip install insightface onnxruntime-gpu
# Run detection on all images in D:/thesis/images/
# Crops saved to D:/thesis/gezichten/
# Embeddings saved to features.pkl
```

> The crop results (`gezichten/`) and embeddings (`features.pkl`) are the outputs of this step.
> Re-running is only needed if the dataset is expanded.

---

## Repository Structure

```
thesis/
├── config.py                        # All paths — change DRIVE_PATH when switching machines
├── dataset_manifest.csv             # 56,740 single known-sitter portraits
├── training_set.csv                 # 27,337 final training portraits with full metadata
├── features.pkl                     # ArcFace embeddings (from WSL step)
├── prirefs_no_image.csv             # 5,696 prirefs with no usable image (+ reason)
├── prirefs_too_small.csv            # 1,896 prirefs below 224×224px (included in manifest)
├── lref_filename.csv                # Mapping for 631 privately-obtained images
├── scripts/
│   ├── select_images.py             # Builds dataset_manifest.csv from XML + images
│   ├── build_training_table.py      # Filters to 27k + enriches with XML metadata
│   ├── build_personen.py            # Copies crops to personen/ organised by sitter_id
│   └── analysis.py                  # Generates dataset charts (plots/dataset_evaluation/)
├── src/dataset/
│   ├── xml_parser.py                # RKDDataset: parses RKDimages.xml
│   ├── downloader.py                # Downloads images from RKD IIIF server
│   ├── audit.py                     # Checks disk vs XML for missing/corrupt files
│   └── retry_corrupt.py             # Re-downloads missing/corrupt images
└── plots/dataset_evaluation/        # Generated charts
```

---

## Data on Drive (not in repo)

| Path | Contents |
|---|---|
| `D:/thesis/data/RKDimages.xml` | Source XML (~985 MB) |
| `D:/thesis/images/` | Downloaded artwork images (~144,763 files) |
| `D:/thesis/gezichten/` | Face crops from RetinaFace detection |
| `D:/thesis/personen/` | Final training set, organised by sitter identity |

---

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Change `DRIVE_PATH` in `config.py` if the data lives on a different drive.

---

## Running the Pipeline

```bash
# 1. Parse XML and download images
python -m src.dataset.downloader

# 2. Select best image per artwork, filter to single known-sitter portraits
python scripts/select_images.py

# 3. [WSL] Detect and crop faces → gezichten/

# 4. Build enriched training table (requires XML + gezichten/)
python scripts/build_training_table.py

# 5. Copy crops into identity-organised folder
python scripts/build_personen.py

# 6. Generate dataset analysis charts
python scripts/analysis.py --training-only

# 7. Generate ResNet100 (Klink&Bunda algo) feature embeddings
ArcFace ResNet100 trained on Glint360K** — face recognition embeddings → `features.pkl`

# 8. Analyse embeddings: Klink & Bunda python code

```
