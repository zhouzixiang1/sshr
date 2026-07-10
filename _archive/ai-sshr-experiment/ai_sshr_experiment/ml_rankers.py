"""ML model adapters implementing the CandidateRanker protocol.

Currently provides:
  - LightGBMRanker: LightGBM LambdaMART ranking model
  - SklearnRanker: Generic sklearn-based adapter (fallback)

All adapters implement score() and score_many() for drop-in replacement
of RuleRanker in ai_guided_beam and pruned_candidates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from feature_extractor import feature_names


class LightGBMRanker:
    """LightGBM ranking model adapter for candidate scoring.

    Uses LGBMRanker with LambdaMART objective. The model outputs raw
    relevance scores; higher score = better candidate.
    """

    def __init__(self, model=None):
        self.model = model
        self._feature_names = feature_names()

    def score(self, features: Dict[str, float]) -> float:
        """Score a single candidate."""
        import numpy as np
        row = np.array(
            [features.get(k, 0.0) for k in self._feature_names],
            dtype=np.float32,
        ).reshape(1, -1)
        return float(self.model.predict(row)[0])

    def score_many(self, features_list) -> List[float]:
        """Score multiple candidates via batch predict."""
        import numpy as np
        if not features_list:
            return []
        rows = np.array(
            [[f.get(k, 0.0) for k in self._feature_names] for f in features_list],
            dtype=np.float32,
        )
        return [float(v) for v in self.model.predict(rows)]

    def save(self, path: Path) -> None:
        """Save model to LightGBM text format."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path))

    @classmethod
    def load(cls, path: Path) -> "LightGBMRanker":
        """Load model from LightGBM text format."""
        import lightgbm as lgb
        model = lgb.Booster(model_file=str(path))
        return cls(model=model)

    def feature_importance(self, importance_type: str = "gain") -> Dict[str, float]:
        """Return feature importance dict."""
        gains = self.model.feature_importance(importance_type)
        return {name: float(g) for name, g in zip(self._feature_names, gains)}


class SklearnRanker:
    """Generic sklearn model adapter (for experiments / fallback)."""

    def __init__(self, model):
        self.model = model
        self._feature_names = feature_names()

    def score(self, features: Dict[str, float]) -> float:
        import numpy as np
        row = np.array(
            [features.get(k, 0.0) for k in self._feature_names],
            dtype=np.float32,
        ).reshape(1, -1)
        return float(self.model.predict(row)[0])

    def score_many(self, features_list) -> List[float]:
        import numpy as np
        if not features_list:
            return []
        rows = np.array(
            [[f.get(k, 0.0) for k in self._feature_names] for f in features_list],
            dtype=np.float32,
        )
        return [float(v) for v in self.model.predict(rows)]
