#!/usr/bin/env python3
"""Public-entrypoint tests for the structured policy/value synthesizer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.anf_utils import majority_function
from src.factor_plan import SearchConfig
from src.foundation.adapter import FoundationScorer
from src.resource_model import ResourceWeights
from src.synthesizers import synthesize


PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)


def _config() -> SearchConfig:
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        candidate_top_k=8,
        neural_mcts_simulations=4,
        max_polarities=4,
    )


def _checkpoint(path: Path) -> Path:
    FoundationScorer.untrained(hidden=16, layers=1, seed=7).save(path)
    return path


def test_foundation_nmcts_runs_through_public_entrypoint(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path / "foundation.pt")
    result = synthesize(
        "foundation_nmcts",
        majority_function(4),
        _config(),
        seed=3,
        model_path=str(checkpoint),
    )

    assert result.method == "foundation_nmcts"
    assert result.correct
    assert result.terms > 0
    assert result.gates > 0
    assert result.n_qubits >= 5


def test_foundation_nmcts_missing_checkpoint_fails_loudly(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pt"
    with pytest.raises(FileNotFoundError, match="foundation_nmcts checkpoint not found"):
        synthesize(
            "foundation_nmcts",
            majority_function(4),
            _config(),
            model_path=str(missing),
        )


def test_foundation_checkpoint_is_not_silently_reused_outside_training_domain(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint(tmp_path / "foundation.pt")
    with pytest.raises(ValueError, match="gate_mode='mct' only"):
        synthesize(
            "and_foundation_nmcts",
            majority_function(4),
            _config(),
            model_path=str(checkpoint),
        )
