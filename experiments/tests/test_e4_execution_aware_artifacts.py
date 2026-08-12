#!/usr/bin/env python3
"""Regression contracts for the superseded E4-v2 noisy-calibration branch."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import scripts.run_aes_execution_aware_eval as e4_runner

from scripts.run_aes_execution_aware_eval import (
    CONFIG_SCHEMA,
    VARIANTS,
    _balanced_oracle_contract_metrics,
    load_config,
    run_calibration,
    run_test,
)
from scripts.verify_aes_execution_aware_bundle import verify_e4v2_bundle
from src.contracts.codec import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# This runner branch is retained only as a regression surface.  Its exact
# pre-audit config lives under test fixtures so it cannot be mistaken for the
# authoritative E4-v2 protocol in ``configs/xa202609``.
CONFIG_PATH = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "e4_execution_aware_v2.superseded-test-only.json"
)
EXPECTED_ARTIFACTS = {
    "run.json",
    "raw.jsonl",
    "summary.json",
    "verifier.json",
    "events.jsonl",
    "stdout.log",
    "stderr.log",
    "artifacts.manifest.json",
    "checksums.sha256",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _rebind_bundle_artifact(root: Path, relative_path: str) -> None:
    """Re-sign one changed artifact so semantic tampering reaches the verifier."""

    manifest_path = root / "artifacts.manifest.json"
    manifest = _json(manifest_path)
    target = root / relative_path
    for artifact in manifest["artifacts"]:
        if artifact["relative_path"] == relative_path:
            artifact["sha256"] = sha256_file(target)
            artifact["size_bytes"] = target.stat().st_size
            break
    else:
        raise AssertionError(f"artifact absent from manifest: {relative_path}")
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")
    checksum_lines = [
        f"{artifact['sha256']}  {artifact['relative_path']}\n"
        for artifact in manifest["artifacts"]
    ]
    checksum_lines.append(f"{sha256_file(manifest_path)}  artifacts.manifest.json\n")
    (root / "checksums.sha256").write_text("".join(checksum_lines), encoding="utf-8")


def test_e4v2_config_preserves_scale_split_and_four_arm_tiny_contract() -> None:
    regular = load_config(CONFIG_PATH)
    tiny = load_config(CONFIG_PATH, tiny=True)

    assert regular["schema_version"] == CONFIG_SCHEMA
    assert regular["calibration"]["n"] == 8
    assert regular["test"]["coordinates"] == list(range(8))
    assert regular["calibration"]["include_output_zero_and_one"] is True
    assert regular["native_profile"]["native_gate_set"] == ["rz", "sx", "x", "cx"]
    assert regular["primary_metric"]["schema"] == "balanced-oracle-contract-metric-v1"
    assert regular["primary_metric"]["component_weighting"] == (
        "equal-over-three-components"
    )
    assert regular["primary_metric"]["secondary_metric"] == (
        "exact-full-state-jeffreys-nll"
    )
    assert tiny["calibration"]["case_count"] == 1
    assert tiny["test"]["solver_seeds"] == [1]
    assert tiny["test"]["coordinates"] == list(range(8))
    assert tiny["search"]["scheduler_budget"] == regular["search"]["scheduler_budget"]
    assert len(VARIANTS) == 4


def test_balanced_contract_metric_uses_joint_input_and_vacuous_ancilla() -> None:
    # q8 is the target and q0..q7 are inputs; keys are displayed q8...q0.
    metric = _balanced_oracle_contract_metrics(
        counts={"100000000": 2, "000000000": 1, "100000001": 1},
        expected_logical_bits=(0, 0, 0, 0, 0, 0, 0, 0, 1),
    )

    components = metric["components"]
    assert components["input_preservation"]["success_count"] == 3
    assert components["target_correct"]["success_count"] == 3
    assert components["ancilla_zero"]["success_count"] == 4
    assert components["ancilla_zero"]["vacuous"] is True
    assert metric["balanced_accuracy"] == pytest.approx((0.75 + 0.75 + 1.0) / 3.0)
    assert metric["balanced_contract_nll"] == pytest.approx(
        (-math.log(0.7) - math.log(0.7) - math.log(0.9)) / 3.0
    )
    assert metric["secondary_exact_full_state"]["success_count"] == 2


def test_e4v2_rejects_incomplete_aes_holdout(tmp_path: Path) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["test"]["coordinates"] = list(range(7))
    invalid = tmp_path / "invalid-e4v2.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="all eight AES coordinates"):
        load_config(invalid)


def _fake_calibration_result(job: dict) -> dict:
    return {
        "case_index": job["case_index"],
        "case_id": job["case"]["case_id"],
        "action_index": job["action_index"],
        "execution": {"marker": job["case_index"] * 10 + job["action_index"]},
        "worker_elapsed_s": 0.0,
    }


def test_calibration_parallel_results_are_sorted_by_case_and_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = [
        {"case_index": 1, "case": {"case_id": "c1"}, "action_index": 1},
        {"case_index": 0, "case": {"case_id": "c0"}, "action_index": 1},
        {"case_index": 1, "case": {"case_id": "c1"}, "action_index": 0},
        {"case_index": 0, "case": {"case_id": "c0"}, "action_index": 0},
    ]

    class FakeFuture:
        def __init__(self, job: dict) -> None:
            self.job = job

        def result(self) -> dict:
            return _fake_calibration_result(self.job)

    class FakeExecutor:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> "FakeExecutor":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def submit(self, _worker: object, job: dict) -> FakeFuture:
            return FakeFuture(job)

    monkeypatch.setattr(e4_runner, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        e4_runner, "as_completed", lambda futures: reversed(list(futures))
    )
    results, mode = e4_runner._run_calibration_jobs(jobs, workers=4)

    assert mode == "process_pool"
    assert [
        (row["case_index"], row["action_index"]) for row in results
    ] == [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_calibration_pool_construction_failure_falls_back_to_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = [
        {"case_index": 0, "case": {"case_id": "c0"}, "action_index": 1},
        {"case_index": 0, "case": {"case_id": "c0"}, "action_index": 0},
    ]

    def denied_pool(**_: object) -> object:
        raise PermissionError("process pool unavailable")

    monkeypatch.setattr(e4_runner, "ProcessPoolExecutor", denied_pool)
    monkeypatch.setattr(
        e4_runner, "_calibration_candidate_worker", _fake_calibration_result
    )
    results, mode = e4_runner._run_calibration_jobs(jobs, workers=3)

    assert mode == "in_process_fallback"
    assert [row["action_index"] for row in results] == [0, 1]


def test_calibration_worker_failure_propagates_with_job_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {"case_index": 2, "case": {"case_id": "c2"}, "action_index": 5}

    class FailedFuture:
        def result(self) -> dict:
            raise ValueError("synthetic worker failure")

    class FailedExecutor:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> "FailedExecutor":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def submit(self, _worker: object, _job: dict) -> FailedFuture:
            return FailedFuture()

    monkeypatch.setattr(e4_runner, "ProcessPoolExecutor", FailedExecutor)
    monkeypatch.setattr(e4_runner, "as_completed", lambda futures: list(futures))

    with pytest.raises(
        RuntimeError, match=r"case=c2 action=5"
    ) as caught:
        e4_runner._run_calibration_jobs([job], workers=2)
    assert isinstance(caught.value.__cause__, ValueError)


def test_tiny_two_stage_bundle_closes_fairness_sha_and_leakage_contracts(
    tmp_path: Path,
) -> None:
    config = load_config(CONFIG_PATH, tiny=True)
    calibration = run_calibration(
        config=config,
        out_dir=tmp_path,
        run_id="test-e4v2-calibration-tiny",
        tiny=True,
        config_path=CONFIG_PATH,
    )
    calibration_verification = verify_e4v2_bundle(calibration)
    assert calibration_verification["ok"], calibration_verification["errors"]

    heldout = run_test(
        config=config,
        out_dir=tmp_path,
        run_id="test-e4v2-heldout-tiny",
        tiny=True,
        config_path=CONFIG_PATH,
        calibration_run=calibration,
        workers=1,
    )
    heldout_verification = verify_e4v2_bundle(
        heldout, calibration_run=calibration
    )
    assert heldout_verification["ok"], heldout_verification["errors"]
    assert {path.name for path in calibration.iterdir()} == EXPECTED_ARTIFACTS
    assert {path.name for path in heldout.iterdir()} == EXPECTED_ARTIFACTS

    calibration_summary = _json(calibration / "summary.json")
    heldout_summary = _json(heldout / "summary.json")
    heldout_run = _json(heldout / "run.json")
    observations = [
        row for row in _jsonl(calibration / "raw.jsonl")
        if row["record_type"] == "calibration_observation"
    ]
    trials = _jsonl(heldout / "raw.jsonl")

    assert calibration_summary["phase"] == "calibration"
    assert heldout_summary["phase"] == "test"
    assert heldout_summary["trial_count"] == 8 * len(VARIANTS)
    assert heldout_run["command"]["execution_mode"] == "in_process"
    assert heldout_summary["performance_evidence"] is False
    assert calibration_summary["primary_metric_name"] == "balanced_contract_nll"
    assert heldout_summary["primary_metric_name"] == "balanced_contract_nll"
    assert calibration_summary["secondary_metric_name"] == (
        "exact_full_state_jeffreys_nll"
    )
    assert set(calibration_summary["calibration_truth_table_sha256"]).isdisjoint(
        calibration_summary["aes_holdout_truth_table_sha256"]
    )
    assert {
        endpoint["output_input"]
        for row in observations
        for endpoint in row["noisy_endpoints"]
    } == {0, 1}
    assert calibration_summary["observations_sha256"] == (
        heldout_summary["calibration_reference"]["observations_sha256"]
    )
    assert calibration_summary["risk_model_sha256"] == (
        heldout_summary["calibration_reference"]["risk_model_sha256"]
    )
    assert calibration_summary["penalty_weights_sha256"] == (
        heldout_summary["calibration_reference"]["penalty_weights_sha256"]
    )
    assert all(
        row["primary_metric"] == "balanced-oracle-contract-metric-v1"
        and set(row["oracle_contract_metrics"]["components"])
        == {"input_preservation", "target_correct", "ancilla_zero"}
        for row in observations
    )

    for bit in range(8):
        block = [
            row for row in trials
            if row["output_bit"] == bit and row["solver_seed"] == 1
        ]
        assert {row["variant"] for row in block} == set(VARIANTS)
        assert len({row["candidate_pool_sha256"] for row in block}) == 1
        assert len({tuple(row["raw_scheduler_utilities"]) for row in block}) == 1
        for row in block:
            assert row["candidate_pool"]["utilities"] == row["raw_scheduler_utilities"]
            assert row["candidate_pool_sha256"] == sha256_bytes(
                canonical_json_bytes(row["candidate_pool"])
            )
            assert row["primary_metric"] == "balanced-oracle-contract-metric-v1"
            assert set(row["endpoint_oracle_contract_metrics"]["components"]) == {
                "input_preservation",
                "target_correct",
                "ancilla_zero",
            }
        endpoint_keys = {
            (endpoint["input_x"], endpoint["noise_seed_anchor"])
            for row in block for endpoint in row["noisy_endpoints"]
        }
        for endpoint_key in endpoint_keys:
            assert len(
                {
                    endpoint["seed"]
                    for row in block
                    for endpoint in row["noisy_endpoints"]
                    if (endpoint["input_x"], endpoint["noise_seed_anchor"])
                    == endpoint_key
                }
            ) == 1

    historical = [row for row in trials if row["variant"].startswith("historical_")]
    execution = [row for row in trials if row["variant"].startswith("execution_")]
    assert all(
        row["raw_scheduler_utilities"] == row["adjusted_scheduler_utilities"]
        for row in historical
    )
    assert all(
        row["risk_model_loaded_without_refit"]
        and row["test_noisy_outcome_used_by_utility"] is False
        and row["adjuster_heldout_noisy_outcome_used"] is False
        and row["execution_feedback"]["enabled"] is True
        for row in execution
    )

    # Change the claimed primary NLL while leaving its source counts untouched,
    # then update the bundle hashes.  Failure must therefore be semantic, not a
    # checksum-only alarm.
    trials[0]["endpoint_balanced_contract_nll"] += 0.25
    raw_path = heldout / "raw.jsonl"
    raw_path.write_text(
        "".join(canonical_json_text(row) + "\n" for row in trials),
        encoding="utf-8",
    )
    _rebind_bundle_artifact(heldout, "raw.jsonl")
    tampered = verify_e4v2_bundle(heldout, calibration_run=calibration)
    assert not tampered["ok"]
    assert tampered["checks"]["bundle_checksum_and_role_whitelist"] is True
    assert tampered["checks"]["test_primary_metric_recomputed_from_counts"] is False
