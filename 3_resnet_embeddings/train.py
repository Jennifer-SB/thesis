"""
JEN added:
Fine-tune IResNet100 on the RKD portrait dataset.

Freezes layer1-3, trains layer4 + head with CosFace loss.
Saves backbone only (no head): output drops straight into inference.py.

EXP3: train on all media (from repo root in WSL2):
    python face_recognition/train.py \
        --data    /mnt/d/thesis/personen \
        --weight  face_recognition/glint360k_cosface_r100/backbone.pth \
        --split   train_test_split.csv \
        --output  face_recognition/checkpoints_exp3

EXP4: train on oil paintings only:
    python face_recognition/train.py \
        --data    /mnt/d/thesis/personen \
        --weight  face_recognition/glint360k_cosface_r100/backbone.pth \
        --split   train_test_split.csv \
        --medium  "Oil paintings" \
        --output  face_recognition/checkpoints_exp4

After training, re-extract features with the fine-tuned backbone:
    cd face_recognition
    python inference.py \
        --weight checkpoints_exp3/best_backbone.pth \
        --folder /mnt/d/thesis/personen
"""

import argparse
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent))
from backbones import get_model
from dataset import RKDFaceDataset


# CosFace classification head
# Hyperparameters from Huber et al.: s=32, m=0.01

class CosFaceHead(nn.Module):
    def __init__(self, num_classes: int, embedding_size: int = 512,
                 s: float = 32.0, m: float = 0.01):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.empty(num_classes, embedding_size))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        cosine  = F.linear(F.normalize(embeddings), F.normalize(self.weight))
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)
        output  = self.s * (cosine - one_hot * self.m)
        return F.cross_entropy(output, labels)


def freeze_early_layers(backbone: nn.Module) -> None:
    """Freeze conv1/bn1/layer1-3. Unfreeze layer4 + BN head + fc + features."""
    for param in backbone.parameters():
        param.requires_grad = False
    for name in ['layer4', 'bn2', 'fc', 'features']:
        for param in getattr(backbone, name).parameters():
            param.requires_grad = True

    n_frozen    = sum(p.numel() for p in backbone.parameters() if not p.requires_grad)
    n_trainable = sum(p.numel() for p in backbone.parameters() if p.requires_grad)
    print(f"  Frozen params:    {n_frozen:,}")
    print(f"  Trainable params: {n_trainable:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',       required=True,
                        help='Path to personen/ folder')
    parser.add_argument('--weight',     required=True,
                        help='Pre-trained backbone.pth')
    parser.add_argument('--split',      required=True,
                        help='Path to train_test_split.csv')
    parser.add_argument('--medium',     default=None,
                        help='Medium group to train on (EXP4). '
                             'Omit for all media (EXP3). '
                             'Example: "Oil paintings"')
    parser.add_argument('--output',     default='face_recognition/checkpoints')
    parser.add_argument('--epochs',     type=int,   default=20)
    parser.add_argument('--batch_size', type=int,   default=32)
    parser.add_argument('--lr',         type=float, default=1e-4)
    parser.add_argument('--seed',       type=int,   default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device     = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Device: {device}")

    # Dataset:
    dataset = RKDFaceDataset(
        personen_dir=args.data,
        training_csv="training_set.csv",
        split_csv=args.split,
        split="train",
        medium=args.medium,
    )
    loader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=True,
        num_workers=4, pin_memory=True,
    )

    # Backbone:
    backbone = get_model('r100', fp16=False).to(device)
    state    = torch.load(args.weight, map_location=device)
    backbone.load_state_dict(state)
    print(f"Loaded backbone: {args.weight}")
    print("Freezing early layers (layer1-3), unfreezing layer4 + head:")
    freeze_early_layers(backbone)

    # CosFace head:
    head = CosFaceHead(dataset.num_classes, embedding_size=512, s=32.0, m=0.01).to(device)
    print(f"CosFace head: {dataset.num_classes:,} classes")

    # Optimiser: only trainable backbone params + full head
    params = (
        [p for p in backbone.parameters() if p.requires_grad]
        + list(head.parameters())
    )
    optimizer = torch.optim.Adam(params, lr=args.lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    # Training loop:
    best_loss = float('inf')
    for epoch in range(1, args.epochs + 1):
        backbone.train()
        head.train()
        total_loss, n_batches = 0.0, 0

        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = head(backbone(imgs), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches  += 1

        scheduler.step()
        avg_loss = total_loss / n_batches
        print(f"Epoch {epoch:3d}/{args.epochs}  loss={avg_loss:.4f}  lr={scheduler.get_last_lr()[0]:.2e}")

        # Save backbone only: head is discarded (not needed for inference.py)
        torch.save(backbone.state_dict(), output_dir / f"epoch_{epoch:02d}_backbone.pth")

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(backbone.state_dict(), output_dir / "best_backbone.pth")
            print(f"  -> new best (loss={best_loss:.4f})")

    print(f"\nDone. Run inference.py --weight {output_dir}/best_backbone.pth")


if __name__ == '__main__':
    main()
