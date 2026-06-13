"""Ranker interfaces for AI-SSHR experiments."""
from __future__ import annotations

from typing import Dict, Iterable, List, Protocol


class CandidateRanker(Protocol):
    def score(self, features: Dict[str, float]) -> float:
        ...

    def score_many(self, features_list: Iterable[Dict[str, float]]) -> List[float]:
        ...


class RuleRanker:
    """Deterministic baseline ranker used before training a real model."""

    def __init__(
        self,
        dim_weight: float = 4.0,
        cover_weight: float = 3.0,
        removal_weight: float = 0.5,
        cost_weight: float = 0.08,
        off_penalty: float = 2.0,
        singleton_penalty: float = 1.5,
    ):
        self.dim_weight = dim_weight
        self.cover_weight = cover_weight
        self.removal_weight = removal_weight
        self.cost_weight = cost_weight
        self.off_penalty = off_penalty
        self.singleton_penalty = singleton_penalty

    def score(self, f: Dict[str, float]) -> float:
        return (
            self.dim_weight * f["dim"]
            + self.cover_weight * f["cover_ratio"]
            + self.removal_weight * f["mono_removed"]
            - self.cost_weight * f["objective_cost"]
            - self.off_penalty * f["off_ratio"]
            - self.singleton_penalty * f["is_singleton"]
        )

    def score_many(self, features_list: Iterable[Dict[str, float]]) -> List[float]:
        return [self.score(f) for f in features_list]


class LinearRanker:
    """Simple linear model adapter for saved prototype weights."""

    def __init__(self, weights: Dict[str, float], bias: float = 0.0):
        self.weights = dict(weights)
        self.bias = float(bias)

    def score(self, f: Dict[str, float]) -> float:
        return self.bias + sum(self.weights.get(k, 0.0) * v for k, v in f.items())

    def score_many(self, features_list: Iterable[Dict[str, float]]) -> List[float]:
        return [self.score(f) for f in features_list]

