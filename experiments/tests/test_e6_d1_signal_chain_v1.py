#!/usr/bin/env python3
"""Focused tests for the ordinary deterministic E6-D1 runner."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_e6_d1_signal_chain_v1.py"
SPEC = importlib.util.spec_from_file_location("e6_d1_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def tiny_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("e6-d1") / "bundle"
    report = runner.run_experiment(
        config_path=PROJECT_ROOT / "configs/xa202609/e6_d1_signal_chain_v1.json",
        profile_name="tiny",
        output=output,
        run_id="unit-e6-d1-signal-chain-v1",
    )
    assert report["train_case_count"] == 2
    assert report["structured_validation_case_count"] == 2
    assert report["ood_case_count"] == 2
    assert report["performance_evidence"] is False
    return output


def test_tiny_bundle_is_exactly_five_checksum_bound_files(tiny_bundle: Path) -> None:
    assert {path.name for path in tiny_bundle.iterdir()} == {
        "config.json",
        "results.json",
        "raw.jsonl",
        "diagnostics.json",
        "checksums.sha256",
    }
    parsed = {}
    for line in (tiny_bundle / "checksums.sha256").read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        parsed[name] = digest
    assert parsed == {
        name: _sha(tiny_bundle / name)
        for name in ("config.json", "diagnostics.json", "raw.jsonl", "results.json")
    }


def test_tiny_bundle_is_byte_deterministic(
    tiny_bundle: Path, tmp_path: Path
) -> None:
    second = tmp_path / "second"
    runner.run_experiment(
        config_path=PROJECT_ROOT / "configs/xa202609/e6_d1_signal_chain_v1.json",
        profile_name="tiny",
        output=second,
        run_id="unit-e6-d1-signal-chain-v1",
    )
    assert {
        name: (tiny_bundle / name).read_bytes()
        for name in sorted(path.name for path in tiny_bundle.iterdir())
    } == {
        name: (second / name).read_bytes()
        for name in sorted(path.name for path in second.iterdir())
    }


def test_design_splits_views_and_claim_boundary_are_explicit(tiny_bundle: Path) -> None:
    results = json.loads((tiny_bundle / "results.json").read_text())
    diagnostics = json.loads((tiny_bundle / "diagnostics.json").read_text())
    effective_config = json.loads((tiny_bundle / "config.json").read_text())
    assert results["config_sha256"] == hashlib.sha256(
        runner.canonical_json_bytes(effective_config)
    ).hexdigest()
    assert results["design_cells"] == [
        "qaoa_vw1",
        "qaoa_vw0",
        "permuted_vw1",
        "permuted_vw0",
    ]
    assert results["diagnostic_anchors"] == [
        "greedy_replay_vw1",
        "frozen_initial_head",
    ]
    assert results["structured_views"] == [
        "matched_6_replay_teacher",
        "expanded_cap256_no_teacher",
    ]
    assert results["ood_opened_after_structured_diagnostics"] is True
    assert all(
        count == 0
        for comparison in results["split_overlap_counts"].values()
        for count in comparison.values()
    )
    assert diagnostics["structured_diagnostics_computed_before_ood_evaluation"] is True
    assert set(diagnostics["structured_factorial_contrasts"]) == {
        "matched_6",
        "expanded_cap256",
    }
    matched_interaction = diagnostics["structured_factorial_contrasts"][
        "matched_6"
    ]["contrasts"]["label_by_value_weight_interaction"]
    assert set(matched_interaction) == {
        "teacher_raw_spearman",
        "model_raw_spearman",
        "policy_kl_divergence",
        "effective_value_loss_contribution",
    }
    assert "value_weighted_squared_error" not in json.dumps(diagnostics)
    assert diagnostics["formal_evaluation"] is False
    assert diagnostics["performance_evidence"] is False
    for name in ("config.json", "results.json", "raw.jsonl", "diagnostics.json"):
        payload = (tiny_bundle / name).read_text(encoding="utf-8").lower()
        for forbidden in ("seal", "preseal", "lock", "manifest", "protocol", "release"):
            assert forbidden not in payload
    assert "manifest" not in {path.name for path in tiny_bundle.iterdir()}


def test_raw_rows_do_not_forge_expanded_or_ood_teachers(tiny_bundle: Path) -> None:
    rows = [json.loads(line) for line in (tiny_bundle / "raw.jsonl").read_text().splitlines()]
    matched = [row for row in rows if row["record_type"] == "matched_teacher_diagnostic"]
    endpoints = [row for row in rows if row["record_type"] == "model_ranking_endpoint"]
    assert len(matched) == 20  # train + validation: 2 cases x five teacher-aware cells.
    assert len(endpoints) == 24  # validation + OOD: 2 cases x six cells.
    assert {row["arm"] for row in matched} == {
        "qaoa_vw1",
        "qaoa_vw0",
        "permuted_vw1",
        "permuted_vw0",
        "greedy_replay_vw1",
    }
    assert all(row["teacher_role"] == "replay_target_matched_6_pool" for row in matched)
    assert all("teacher_policy" not in row for row in endpoints)
    assert all(row["semantic_verification"] is True for row in rows)
    assert all(row["direct_fallback_used"] is False for row in rows)
    assert all(row["degraded"] is False for row in rows)


def test_runner_refuses_existing_output_before_work(tmp_path: Path) -> None:
    output = tmp_path / "already-exists"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        runner.run_experiment(
            config_path=PROJECT_ROOT / "configs/xa202609/e6_d1_signal_chain_v1.json",
            profile_name="tiny",
            output=output,
            run_id="must-not-run",
        )
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_split_overlap_guard_fails_closed() -> None:
    left = {
        "vector_sha256": {"a"},
        "orbit_cluster_sha256": {"b"},
        "whole_vector_cluster_sha256": {"c"},
    }
    right = {
        "vector_sha256": {"a"},
        "orbit_cluster_sha256": {"x"},
        "whole_vector_cluster_sha256": {"y"},
    }
    with pytest.raises(RuntimeError, match="split identity overlap"):
        runner._assert_disjoint(left, right, label="unit")
