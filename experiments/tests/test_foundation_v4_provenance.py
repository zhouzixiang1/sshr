#!/usr/bin/env python3
"""Integration and tamper tests for the provenance-closed v4 trainer."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import torch

from scripts.train_foundation_v4 import _accept_or_restore_best, _state_dict_copy
from scripts.verify_foundation_v4_bundle import verify_foundation_v4_bundle
from src.foundation.equivariant import EquivariantTrunk
from src.foundation.heads import BooleanOracleModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "configs" / "xa202609" / "foundation_v4_provenance.json"


def test_foundation_v4_test_profile_trains_and_tamper_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "foundation-v4-test"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "train_foundation_v4.py"),
            "--config",
            str(CONFIG),
            "--profile",
            "test",
            "--output",
            str(bundle),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    runner_report = json.loads(completed.stdout)
    assert runner_report["ok"] is True
    assert runner_report["parameter_count"] == 60_450
    assert runner_report["formal_training_completed"] is False
    assert runner_report["performance_evidence"] is False

    verified = verify_foundation_v4_bundle(bundle, require_current_source=True)
    assert verified["ok"], verified["errors"]
    assert verified["checks"]["dataset_regeneration"] is True
    assert verified["checks"]["dataset_unique"] is True
    assert verified["checks"]["split_disjoint"] is True
    assert verified["checks"]["dataset_crypto_hash_disjoint"] is True
    assert verified["checks"]["checkpoint_from_scratch"] is True
    assert verified["checks"]["checkpoint_architecture"] is True
    assert verified["parameter_count"] == 60_450

    dataset = json.loads((bundle / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert {record["num_vars"] for record in dataset["records"]} == {6, 7}
    assert dataset["crypto_exclusion"]["evaluation_not_accessed"] is True
    assert dataset["crypto_exclusion"]["evaluation_module_imported_during_training"] is False

    tampered = tmp_path / "foundation-v4-tampered"
    shutil.copytree(bundle, tampered)
    dataset_path = tampered / "dataset_manifest.json"
    payload = dataset_path.read_text(encoding="utf-8")
    dataset_path.write_text(
        payload.replace(dataset["records"][0]["truth_table_sha256"], "0" * 64, 1),
        encoding="utf-8",
    )
    rejected = verify_foundation_v4_bundle(tampered)
    assert rejected["ok"] is False
    assert rejected["checks"]["artifact_bundle"] is False


def test_training_entrypoint_does_not_import_crypto_evaluation_module() -> None:
    source = (PROJECT_ROOT / "scripts" / "train_foundation_v4.py").read_text(
        encoding="utf-8"
    )
    assert "from src.benchmarks.crypto_oracles" not in source
    assert "import src.benchmarks.crypto_oracles" not in source


def test_rejected_iteration_restores_last_best_state() -> None:
    torch.manual_seed(7)
    model = BooleanOracleModel(EquivariantTrunk(hidden=32, layers=2), mlp_hidden=128)
    best_state = _state_dict_copy(model)
    with torch.no_grad():
        next(model.parameters()).add_(1.0)
    best_score, restored_state, accepted = _accept_or_restore_best(
        model,
        candidate_score=2.0,
        best_score=1.0,
        best_state=best_state,
    )
    assert accepted is False
    assert best_score == 1.0
    assert restored_state is best_state
    for key, tensor in model.state_dict().items():
        assert torch.equal(tensor, best_state[key])
