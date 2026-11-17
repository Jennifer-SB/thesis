# ResNet Embeddings (RQ1 / RQ2)

Vendored from InsightFace's [`arcface_torch`](https://github.com/deepinsight/insightface/tree/master/recognition/arcface_torch), used two ways:

- **Pretrained baseline (RQ1):** Glint360K IResNet100 + CosFace weights, unmodified. Embeddings via `inference.py`.
- **Fine-tuned (RQ2):** `train.py` continues training with a CosFace head (margin 0.01, scale 32) on the RKD train split, freezing everything except `layer4` + head. See `train.py`'s docstring for the exact commands for the all-media (EXP3) and oil-only (EXP4) variants.

See the root [`README.md`](../README.md) for how this stage fits into the full pipeline.

## Setup

```bash
pip install -r requirements.txt
```

## Outputs

`output/features_UNFINETUNED.pkl` (baseline), `output/features_exp3.pkl` (all-media fine-tune), `output/features_exp4.pkl` (oil-only fine-tune) — all consumed by `5_evaluation/evaluation2.ipynb`.

## Reference

```
@inproceedings{deng2019arcface,
  title={Arcface: Additive angular margin loss for deep face recognition},
  author={Deng, Jiankang and Guo, Jia and Xue, Niannan and Zafeiriou, Stefanos},
  booktitle={CVPR},
  year={2019}
}
@inproceedings{an2022partialfc,
  author={An, Xiang and Deng, Jiankang and Guo, Jia and Feng, Ziyong and Zhu, XuHan and Yang, Jing and Liu, Tongliang},
  title={Killing Two Birds With One Stone: Efficient and Robust Training of Face Recognition CNNs by Partial FC},
  booktitle={CVPR},
  year={2022}
}
```
