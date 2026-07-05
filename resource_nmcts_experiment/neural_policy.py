#!/usr/bin/env python3
"""Small neural action scorer used as an optional MCTS prior."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence

import torch
from torch import nn


FEATURE_DIM = 12


class ActionNet(nn.Module):
    def __init__(self, hidden: int = 96) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(FEATURE_DIM, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def default_device() -> torch.device:
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class NeuralScorer:
    def __init__(self, model_path: str | Path, device: torch.device | None = None) -> None:
        # Inference is dominated by many small action batches.  CPU is faster and
        # more stable than MPS for this workload; training can still use MPS.
        self.device = torch.device("cpu") if device is None else device
        payload = torch.load(model_path, map_location="cpu")
        self.mean = torch.tensor(payload["mean"], dtype=torch.float32, device=self.device)
        self.std = torch.tensor(payload["std"], dtype=torch.float32, device=self.device)
        self.model = ActionNet()
        self.model.load_state_dict(payload["state_dict"])
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def score_one(self, features: Sequence[float]) -> float:
        x = torch.tensor([list(features)], dtype=torch.float32, device=self.device)
        x = (x - self.mean) / self.std.clamp_min(1e-6)
        return float(self.model(x).detach().cpu().item())

    @torch.no_grad()
    def score_many(self, features: Iterable[Sequence[float]]) -> List[float]:
        rows = [list(f) for f in features]
        if not rows:
            return []
        x = torch.tensor(rows, dtype=torch.float32, device=self.device)
        x = (x - self.mean) / self.std.clamp_min(1e-6)
        return self.model(x).detach().cpu().tolist()


def save_model(path: str | Path, model: ActionNet, mean: torch.Tensor, std: torch.Tensor) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.detach().cpu().tolist(),
            "std": std.detach().cpu().tolist(),
        },
        path,
    )
