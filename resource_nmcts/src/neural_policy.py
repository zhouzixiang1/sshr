#!/usr/bin/env python3
"""Small neural action scorer used as an optional MCTS prior."""
from __future__ import annotations

from pathlib import Path
import hashlib
from typing import Iterable, List, Sequence

import torch
from torch import nn


FEATURE_DIM = 24


class ActionNet(nn.Module):
    def __init__(self, hidden: int = 128, feature_dim: int = FEATURE_DIM) -> None:
        super().__init__()
        self.feature_dim = feature_dim
        layers: list = [nn.Linear(feature_dim, hidden), nn.ReLU()]
        if feature_dim >= 20:
            layers.extend([nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(0.1)])
        layers.extend([nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1)])
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.net:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

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
        feat_dim = len(payload.get("mean", []))
        self.model = ActionNet(hidden=int(payload.get("hidden", 96)), feature_dim=max(feat_dim, 1))
        self.model.load_state_dict(payload["state_dict"])
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def score_one(self, features: Sequence[float]) -> float:
        d = self.model.feature_dim
        x = torch.tensor([list(features)[:d]], dtype=torch.float32, device=self.device)
        x = (x - self.mean) / self.std.clamp_min(1e-6)
        return float(self.model(x).detach().cpu().item())

    @torch.no_grad()
    def score_many(self, features: Iterable[Sequence[float]]) -> List[float]:
        d = self.model.feature_dim
        rows = [list(f)[:d] for f in features]
        if not rows:
            return []
        x = torch.tensor(rows, dtype=torch.float32, device=self.device)
        x = (x - self.mean) / self.std.clamp_min(1e-6)
        return self.model(x).detach().cpu().tolist()


class RandomPriorScorer:
    """Deterministic same-budget random scorer for prior-control experiments."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)

    def _score(self, features: Sequence[float]) -> float:
        payload = f"{self.seed}|" + ",".join(f"{float(value):.8g}" for value in features)
        digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
        unit = int.from_bytes(digest, "big") / float(1 << 64)
        return 2.0 * unit - 1.0

    def score_one(self, features: Sequence[float]) -> float:
        return self._score(features)

    def score_many(self, features: Iterable[Sequence[float]]) -> List[float]:
        return [self._score(row) for row in features]


def save_model(path: str | Path, model: ActionNet, mean: torch.Tensor, std: torch.Tensor) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    first_linear = model.net[0]
    hidden = int(first_linear.out_features) if isinstance(first_linear, nn.Linear) else 96
    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.detach().cpu().tolist(),
            "std": std.detach().cpu().tolist(),
            "hidden": hidden,
        },
        path,
    )
