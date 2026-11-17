# Fusion embeddings (RQ3)

The CLIP+LoRA fusion pipeline (Poh et al.-style 3-component fusion: pretrained IResNet100 + fine-tuned IResNet100 + CLIP ViT-B/16+LoRA, concatenated and re-normalized) is **not reproduced in this repo** — this folder is a permanent pointer, not a placeholder awaiting a future copy-in.

Only its *output* embeddings are consumed, loaded directly from `D:/thesis/Swiss_team_rerun_embeddings/` inside `5_evaluation/evaluation2.ipynb`. See the root [`README.md`](../README.md) for the full pipeline picture.
