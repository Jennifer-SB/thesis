# Face Detection (RetinaFace)

Vendored from [InsightFace](https://github.com/deepinsight/insightface)'s RetinaFace, via [Sebastian Bunda's ArtFace fork](https://github.com/stbunda/ArtFace), with one addition: the 5-point-landmark alignment step (`face_align.py`'s `norm_crop`, added into `test_all.py`) that produces the aligned 112x112 crops the ResNet embedding stage expects.

See the root [`README.md`](../README.md) for how this stage fits into the full pipeline, including the `schilderijen` input-folder naming note.

## Setup

Requires a Linux environment with MXNet + GPU support (not part of the Windows pipeline).

```bash
pip install -r requirements.txt
make        # builds the cython/C++ NMS and anchor-generation tools in rcnn/
```

## Running

```bash
python test_all.py --folder <path with a schilderijen/ subfolder> --model ./model/R50/R50
```

`model/R50/` holds the pretrained RetinaFace-R50 weights (gitignored, not in this repo — see InsightFace's model zoo if you need to re-download them).

## Reference

```
@inproceedings{Deng2020CVPR,
  title = {RetinaFace: Single-Shot Multi-Level Face Localisation in the Wild},
  author = {Deng, Jiankang and Guo, Jia and Ververas, Evangelos and Kotsia, Irene and Zafeiriou, Stefanos},
  booktitle = {CVPR},
  year = {2020}
}
```
