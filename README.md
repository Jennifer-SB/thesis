# Thesis Jennifer: Face Recognition on RKD Historical Portrait Paintings

Face verification on the [RKD (Rijksbureau voor Kunsthistorische Documentatie)](https://rkd.nl) dataset of historical Dutch and Flemish portrait paintings.

## Research Questions

| | |
|---|---|
| **RQ1** | Evaluate the pretrained ResNet100 + CosFace baseline (Glint360K weights, no fine-tuning) on the full RKD dataset (Klink & Bunda, 2025) |
| **RQ2** | Fine-tune the same backbone on the RKD train split (all-media vs. oil-paintings-only) — does medium-specific specialization help? |
| **RQ3** | Fuse CLIP ViT-B/16 + LoRA with the pretrained/fine-tuned embeddings (Poh et al., 2025) — does this fusion approach, shown to help on a small curated benchmark, hold up at RKD's larger and more varied scale? |

**Central finding:** fusion (RQ3) does not improve on the pretrained baseline at this scale — it underperforms both the pretrained and fine-tuned models overall, does not close the gap between media, and increases artist-style bias on every measure tested. Fine-tuning (RQ2) gives small, fairly consistent gains; the oil-only fine-tune underperforming the all-media fine-tune is a second standalone negative result. See `5_evaluation/evaluation2.ipynb` for every number behind these claims.

## Repository Structure

The pipeline is organized into five numbered stages, each roughly a folder you can read top to bottom:

```
thesis/
├── 1_dataset_construction/   # RKDimages.xml -> training_set.csv (27,337 portraits / 7,981 sitters)
├── 2_face_detection/          # RetinaFace detection + alignment -> aligned face crops
├── 3_resnet_embeddings/       # Baseline + fine-tuned IResNet100+CosFace embeddings (RQ1 / RQ2)
├── 4_fusion_embeddings/       # Pointer only -- see note below, code lives outside this repo
├── 5_evaluation/              # evaluation2.ipynb -- the notebook behind every result in the thesis
├── config.py                  # Paths shared across every stage; change DRIVE_PATH per machine
└── requirements.txt
```

### 1. Dataset construction

```
RKDimages.xml  (103,637 artwork records)
      │
      ▼  1_dataset_construction/src/downloader.py
D:/thesis/images/  (~144,763 .jpg files)
      │
      ▼  1_dataset_construction/scripts/select_images.py  ->  data/dataset_manifest.csv
Single known-sitter portraits  (56,740)
      │
      ▼  [2_face_detection, see below]  ->  D:/thesis/gezichten/
Solo-face portraits  (50,986)
      │
      ▼  1_dataset_construction/scripts/build_training_table.py  ->  data/training_set.csv
27,337 training portraits  |  7,981 identities
      │
      ▼  2_face_detection/scripts/build_personen.py
D:/thesis/personen/{sitter_id}/{lref}.jpg  <- final training dataset
```

**Filtering summary**

| Step | Remaining | Removed |
|---|---|---|
| XML artwork records | 103,637 | - |
| Images on disk (after download) | ~144,763 unique files | 73+555 failed permanently |
| Prirefs with usable image | ~97,941 | 5,696 (no image / placeholder only) |
| Single known-sitter filter | 56,740 | ~41,201 (group portraits / unknown sitters) |
| Solo-face filter (RetinaFace) | 50,986 | 3,755 no face · 1,999 multi-face |
| Identity filter (>=2 portraits) | **27,337 portraits / 7,981 identities** | ~23,649 (sitter appears only once) |

Everything here runs from the Windows side. See `1_dataset_construction/`'s own files for `audit.py`/`retry_corrupt.py` (download integrity tools) and `analysis.py` (dataset charts).

### 2. Face detection

RetinaFace detection + 5-point-landmark alignment to a 112x112 crop, run in a Linux/WSL2 environment with a CUDA GPU (not part of the Windows pipeline above).

The code is based on [Sebastian Bunda's ArtFace](https://github.com/stbunda/ArtFace) fork of [InsightFace](https://github.com/deepinsight/insightface), with one addition: the alignment step (`norm_crop`, via `face_align.py`) added into `test_all.py`. **Note:** `test_all.py` expects an input subfolder literally named `schilderijen` (Dutch for "paintings") — that's how Bunda's original pipeline was organized, and it's where this was actually run, rather than against this repo's own `D:/thesis/images/` naming.

```bash
# In WSL2 with CUDA, from 2_face_detection/
python test_all.py --folder <path with a schilderijen/ subfolder> --model ./model/R50/R50
```

Outputs: aligned face crops in `gezichten/{lref}_0.jpg`, `_1.jpg`, ... (one per detected face). `2_face_detection/scripts/build_personen.py` then copies the solo-face crops into `personen/{sitter_id}/{lref}.jpg`, keyed off `training_set.csv`.

### 3. ResNet embeddings (RQ1 / RQ2)

`3_resnet_embeddings/` is InsightFace's `arcface_torch`, used two ways:
- **Pretrained baseline (RQ1):** Glint360K weights, no fine-tuning, embeddings extracted via `inference.py`.
- **Fine-tuned (RQ2):** `train.py` continues training with a CosFace head (margin 0.01, scale 32) on the RKD train split, freezing everything except `layer4` + head. Run once on all media, once on oil-paintings only — see the docstring in `train.py` for exact commands.

Outputs land in `3_resnet_embeddings/output/`: `features_UNFINETUNED.pkl` (baseline), `features_exp3.pkl` (all-media fine-tune), `features_exp4.pkl` (oil-only fine-tune).

### 4. Fusion embeddings (RQ3)

**Not reproduced in this repo.** The CLIP ViT-B/16 + LoRA fusion pipeline (Poh et al.-style: pretrained IResNet100 + fine-tuned IResNet100 + CLIP+LoRA, concatenated and re-normalized) lives in an external pipeline. `4_fusion_embeddings/` is a permanent pointer, not a placeholder awaiting a future copy-in. Only its *output* embeddings are consumed, loaded directly from `D:/thesis/Swiss_team_rerun_embeddings/` inside the evaluation notebook.

### 5. Evaluation

`5_evaluation/evaluation2.ipynb` is the notebook behind every number in the thesis — experiments EXP1 through EXP14, covering RQ1 (full dataset), RQ2 and RQ3 (held-out test split). Shared evaluation code (pair-building, metrics, medium/artist classification) lives in `5_evaluation/src/`. The sitter-level train/test split is `5_evaluation/train_test_split.csv`, built by `5_evaluation/scripts/make_split.py`.

Open the notebook from its own folder (`5_evaluation/`) — its data-loading cells assume that as the working directory, which is the Jupyter/VS Code default when opening a notebook directly.

## Data on Drive (not in repo)

| Path | Contents |
|---|---|
| `D:/thesis/data/RKDimages.xml` | Source XML (~985 MB) |
| `D:/thesis/images/` | Downloaded artwork images (~144,763 files) |
| `D:/thesis/gezichten/` | Face crops from RetinaFace detection |
| `D:/thesis/personen/` | Final training set, organised by sitter identity |
| `D:/thesis/Swiss_team_rerun_embeddings/` | External CLIP base / CLIP+LoRA / fusion embeddings (RQ3) |

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Change `DRIVE_PATH` in `config.py` if the data lives on a different drive.

## Running the Pipeline

```bash
# 1. Parse XML and download images
python -m src.downloader          # from within 1_dataset_construction/

# 2. Select best image per artwork, filter to single known-sitter portraits
python 1_dataset_construction/scripts/select_images.py

# 3. [WSL] Detect and crop faces -> gezichten/ (see "2. Face detection" above)

# 4. Build enriched training table (requires XML + gezichten/)
python 1_dataset_construction/scripts/build_training_table.py

# 5. Copy crops into identity-organised folder
python 2_face_detection/scripts/build_personen.py

# 6. Generate dataset analysis charts
python 1_dataset_construction/scripts/analysis.py --training-only

# 7. Fine-tune + extract ResNet embeddings (see 3_resnet_embeddings/train.py docstring)

# 8. Run 5_evaluation/evaluation2.ipynb for every result in the thesis
```
