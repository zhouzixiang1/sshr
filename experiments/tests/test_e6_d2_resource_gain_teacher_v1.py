#!/usr/bin/env python3
"""Focused tests for the deterministic E6-D2 runner."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_e6_d2_resource_gain_teacher_v1.py"
CONFIG_PATH = PROJECT_ROOT / "configs/xa202609/e6_d2_resource_gain_teacher_v1.json"
SPEC = importlib.util.spec_from_file_location("e6_d2_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def tiny_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("e6-d2") / "bundle"
    report = runner.run_experiment(
        config_path=CONFIG_PATH,
        profile_name="tiny",
        output=output,
        run_id="unit-e6-d2-resource-gain-teacher-v1",
    )
    assert report["train_case_count"] == 2
    assert report["structured_validation_case_count"] == 2
    assert report["ood_case_count"] == 2
    assert report["performance_evidence"] is False
    return output


def test_tiny_bundle_has_exact_file_and_checksum_contract(tiny_bundle: Path) -> None:
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


def test_tiny_bundle_is_byte_deterministic(tiny_bundle: Path, tmp_path: Path) -> None:
    second = tmp_path / "second"
    runner.run_experiment(
        config_path=CONFIG_PATH,
        profile_name="tiny",
        output=second,
        run_id="unit-e6-d2-resource-gain-teacher-v1",
    )
    names = sorted(path.name for path in tiny_bundle.iterdir())
    assert {name: (tiny_bundle / name).read_bytes() for name in names} == {
        name: (second / name).read_bytes() for name in names
    }


def test_design_training_and_sequential_views_are_explicit(tiny_bundle: Path) -> None:
    results = json.loads((tiny_bundle / "results.json").read_text())
    diagnostics = json.loads((tiny_bundle / "diagnostics.json").read_text())
    effective = json.loads((tiny_bundle / "config.json").read_text())
    assert results["config_sha256"] == hashlib.sha256(
        runner.canonical_json_bytes(effective)
    ).hexdigest()
    assert results["primary_pair"] == [
        "gain_weighted_qaoa_vw0",
        "gain_weighted_permuted_vw0",
    ]
    assert results["diagnostic_anchors"] == [
        "legacy_unweighted_qaoa_vw0",
        "greedy_vw0",
        "frozen_initial_head",
    ]
    reports = results["training_report_by_cell"]
    assert set(reports) == {
        "gain_weighted_qaoa_vw0",
        "gain_weighted_permuted_vw0",
        "legacy_unweighted_qaoa_vw0",
        "greedy_vw0",
    }
    assert {
        reports[cell]["target_mode"]
        for cell in ("gain_weighted_qaoa_vw0", "gain_weighted_permuted_vw0")
    } == {"qaoa_resource_gain_credit_v1"}
    assert {
        reports[cell]["target_mode"]
        for cell in ("legacy_unweighted_qaoa_vw0", "greedy_vw0")
    } == {"legacy_replay_v2"}
    assert all(report["source_group_count"] == 2 for report in reports.values())
    assert all(report["zero_gain_skipped_group_count"] == 0 for report in reports.values())
    gain_reports = [
        reports["gain_weighted_qaoa_vw0"],
        reports["gain_weighted_permuted_vw0"],
    ]
    for field in (
        "sample_count",
        "group_ids",
        "training_schedule_sha256",
        "sample_presentations",
        "initial_head_tensor_sha256",
    ):
        assert gain_reports[0][field] == gain_reports[1][field]
    assert all(count == 0 for item in results["split_overlap_counts"].values() for count in item.values())
    assert results["structured_views"] == [
        "matched_6_replay_teacher",
        "expanded_cap256_no_teacher",
    ]
    assert results["ood_opened_after_structured_diagnostics"] is True
    assert diagnostics["structured_diagnostics_computed_before_ood_evaluation"] is True
    assert set(diagnostics["structured_primary_pair_contrasts"]) == {
        "matched_6",
        "expanded_cap256",
    }
    assert diagnostics["ood_primary_pair_contrast"]["available"] is True
    assert set(diagnostics["ood_primary_pair_contrast"]["difference"]) == {
        "model_raw_spearman",
        "raw_best_top_k_recall",
        "selected_empty",
        "score_ratio_y",
    }
    assert diagnostics["formal_evaluation"] is False
    assert diagnostics["performance_evidence"] is False


def test_gain_teachers_are_eligible_and_endpoints_are_teacher_free(tiny_bundle: Path) -> None:
    rows = [json.loads(line) for line in (tiny_bundle / "raw.jsonl").read_text().splitlines()]
    audits = [row for row in rows if row["record_type"] == "resource_gain_teacher_audit"]
    matched = [row for row in rows if row["record_type"] == "matched_teacher_diagnostic"]
    endpoints = [row for row in rows if row["record_type"] == "model_ranking_endpoint"]
    assert len(audits) == 4
    assert len(matched) == 16
    assert len(endpoints) == 20
    assert all(row["source"]["eligible"] is True for row in audits)
    assert all(row["control"]["eligible"] is True for row in audits)
    assert all(row["control_is_exact_source_permutation"] is True for row in audits)
    assert all(row["permuted_target_changed"] is True for row in audits)
    assert {row["arm"] for row in matched} == {
        "gain_weighted_qaoa_vw0",
        "gain_weighted_permuted_vw0",
        "legacy_unweighted_qaoa_vw0",
        "greedy_vw0",
    }
    assert all("teacher_policy" not in row for row in endpoints)
    assert all(row["semantic_verification"] is True for row in [*matched, *endpoints])
    assert all(row["direct_fallback_used"] is False for row in [*matched, *endpoints])
    assert all(row["degraded"] is False for row in [*matched, *endpoints])


def test_persisted_payloads_are_ordinary_development_outputs(tiny_bundle: Path) -> None:
    forbidden = ("seal", "preseal", "verifier", "manifest", "protocol", "lock")
    for name in ("config.json", "results.json", "raw.jsonl", "diagnostics.json"):
        payload = (tiny_bundle / name).read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in payload


def test_runner_refuses_existing_output_before_work(tmp_path: Path) -> None:
    output = tmp_path / "already-exists"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        runner.run_experiment(
            config_path=CONFIG_PATH,
            profile_name="tiny",
            output=output,
            run_id="must-not-run",
        )
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_endpoint_parameters_are_authoritative(tmp_path: Path) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["endpoint"]["candidate_universe_cap"] = 17
    config["endpoint"]["learned_top_k"] = 9
    config["endpoint"]["scheduler_budget"] = 1
    config_path = tmp_path / "tampered-endpoint.json"
    config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    output = tmp_path / "bundle"
    runner.run_experiment(
        config_path=config_path,
        profile_name="tiny",
        output=output,
        run_id="unit-e6-d2-authoritative-endpoint",
    )
    results = json.loads((output / "results.json").read_text())
    diagnostics = json.loads((output / "diagnostics.json").read_text())
    rows = [json.loads(line) for line in (output / "raw.jsonl").read_text().splitlines()]
    endpoints = [row for row in rows if row["record_type"] == "model_ranking_endpoint"]
    assert results["structured_views"] == [
        "matched_6_replay_teacher",
        "expanded_cap17_no_teacher",
    ]
    assert "expanded_cap17" in diagnostics["structured_primary_pair_contrasts"]
    assert {row["candidate_count"] for row in endpoints} == {17}
    assert {row["top_k"] for row in endpoints} == {9}
    assert {row["scheduler_budget"] for row in endpoints} == {1}


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
