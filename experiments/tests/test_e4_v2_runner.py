#!/usr/bin/env python3
"""E4-v2 two-stage runner, isolation, fairness and tamper contracts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_e4_v2_execution_aware as runner
from scripts.verify_e4_v2_bundle import verify_e4_v2_bundle
from src.contracts.artifacts import verify_bundle
from src.contracts.codec import canonical_json_bytes, sha256_bytes


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "configs" / "xa202609" / "e4_v2_execution_aware_v1.json"


def _rows(bundle: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (bundle / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resign_bundle(bundle: Path) -> None:
    """Update every outer manifest/checksum after a scientific-field edit."""

    manifest_path = bundle / "artifacts.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["artifacts"]:
        target = bundle / record["relative_path"]
        record["size_bytes"] = target.stat().st_size
        record["sha256"] = _sha(target)
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    names = [record["relative_path"] for record in manifest["artifacts"]]
    names.append("artifacts.manifest.json")
    (bundle / "checksums.sha256").write_text(
        "".join(f"{_sha(bundle / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def test_config_is_frozen_and_tiny_preserves_phase_and_four_arm_contract() -> None:
    formal = runner.load_config(CONFIG)
    tiny = runner.load_config(CONFIG, tiny=True)
    assert formal["test"]["coordinates"] == list(range(8))
    assert formal["test"]["solver_seeds"] == [1, 2]
    assert tiny["calibration"]["case_count"] == 1
    assert tiny["test"]["coordinates"] == [0, 1]
    assert tiny["test"]["solver_seeds"] == [1]
    assert tiny["experiment_role"] == "frozen_replication"
    assert tiny["dataset_role"] == "post_e4_frozen_aes_replication"
    assert tiny["historically_seen_in_E4"] is True
    assert tiny["generalization_claim"] is False
    assert tiny["native_profile"]["frozen_n_qubits"] == 10
    assert tiny["compute_contract"] == {
        "torch_device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    assert tiny["search"]["simulations"] == tiny["search"]["scheduler_budget"]
    assert tiny["primary_endpoint"]["metric"] == "native.two_qubit_gate_count"
    assert tiny["primary_endpoint"]["estimand"] == (
        "intention_to_treat_all_assigned_trials"
    )
    assert tiny["primary_endpoint"]["noisy_success_role"] == (
        "diagnostic_only_not_a_tuning_or_primary_endpoint"
    )
    assert tiny["calibration"]["forbidden_inputs"] == [
        "replication_aes_coordinates",
        "test_plan",
        "test_native_result",
        "noisy_endpoint",
    ]


def test_local_protocol_lock_binds_all_scientific_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = runner.load_config(CONFIG, tiny=True)
    lock = json.loads(
        (PROJECT_ROOT / config["protocol_lock"]["path"]).read_text(encoding="utf-8")
    )
    for record in lock["sources"].values():
        source = PROJECT_ROOT / record["path"]
        target = tmp_path / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    model_source = PROJECT_ROOT / lock["model"]["path"]
    model_target = tmp_path / lock["model"]["path"]
    model_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(model_source, model_target)
    config_target = tmp_path / lock["config"]["path"]
    config_target.parent.mkdir(parents=True, exist_ok=True)
    config_target.write_bytes(canonical_json_bytes(lock["config"]["canonical_payload"]))
    lock_target = tmp_path / config["protocol_lock"]["path"]
    lock_target.parent.mkdir(parents=True, exist_ok=True)
    lock_target.write_bytes(canonical_json_bytes(lock))

    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    validated, validated_sha, validated_path = runner.load_protocol_lock(config)
    assert validated == lock
    assert validated_sha == sha256_bytes(canonical_json_bytes(lock))
    assert validated_path == lock_target.resolve()
    assert lock["compute_contract"] == config["compute_contract"]
    assert lock["compute_contract_sha256"] == sha256_bytes(
        canonical_json_bytes(config["compute_contract"])
    )

    bound_source = tmp_path / lock["sources"]["execution_aware_core"]["path"]
    bound_source.write_bytes(bound_source.read_bytes() + b"\n# semantic tamper\n")
    with pytest.raises(ValueError, match="source SHA mismatch"):
        runner.load_protocol_lock(config)


def test_config_and_weight_selection_errors_fail_closed(tmp_path: Path) -> None:
    config = runner.load_config(CONFIG, tiny=True)
    config["weight_selection"]["feature_mixture"]["native_two_qubit"] = -0.1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="finite and non-negative"):
        runner.load_config(bad)

    bad_compute = runner.load_config(CONFIG, tiny=True)
    bad_compute["compute_contract"]["torch_intraop_threads"] = 2
    bad_compute_path = tmp_path / "bad-compute.json"
    bad_compute_path.write_text(json.dumps(bad_compute), encoding="utf-8")
    with pytest.raises(ValueError, match="compute contract"):
        runner.load_config(bad_compute_path)

    valid = runner.load_config(CONFIG, tiny=True)
    rows = [
        {
            "compile_time_candidates": [
                {
                    "resource_components": {
                        "native_one_qubit": 1.0,
                        "native_two_qubit": 0.0,
                        "inserted_swap": 0.0,
                        "native_depth": 1.0,
                        "duration_ns": 1.0,
                        "model_risk": 0.0,
                    }
                }
            ]
        }
    ]
    with pytest.raises(ValueError, match="zero calibration scale"):
        runner.select_frozen_weights(
            rows=rows,
            config=valid,
            calibration_sha256="a" * 64,
            profile_sha256="b" * 64,
        )


def test_compute_contract_fails_closed_before_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runner.load_config(CONFIG, tiny=True)
    monkeypatch.setattr(runner.torch, "get_num_interop_threads", lambda: 2)

    def reject_interop_change(_threads: int) -> None:
        raise RuntimeError("parallel work already started")

    monkeypatch.setattr(runner.torch, "set_num_interop_threads", reject_interop_change)
    with pytest.raises(RuntimeError, match="before inference"):
        runner._enforce_compute_contract(config)


def test_tiny_two_stage_bundle_closes_four_arms_and_detects_tampering(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_e4_v2_execution_aware.py"),
            "--tiny",
            "--phase",
            "all",
            "--out-dir",
            str(tmp_path),
            "--run-id",
            "e4v2-tiny-test",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    calibration = tmp_path / "e4v2-tiny-test-cal"
    test = tmp_path / "e4v2-tiny-test-test"
    expected_files = {
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
    for bundle in (calibration, test):
        assert verify_bundle(bundle).ok
        assert {path.name for path in bundle.iterdir()} == expected_files
        result = verify_e4_v2_bundle(bundle)
        assert result["ok"], result["errors"]

    cal_run = json.loads((calibration / "run.json").read_text(encoding="utf-8"))
    cal_summary = json.loads((calibration / "summary.json").read_text(encoding="utf-8"))
    cal_rows = _rows(calibration)
    assert cal_run["counts"]["noisy_shots"] == 0
    assert cal_summary["calibration_access_contract"] == {
        "compile_time_only": True,
        "replication_aes_accessed": False,
        "heldout_aes_accessed": False,
        "noisy_endpoint_accessed": False,
        "test_outcome_accessed": False,
    }
    assert cal_summary["experiment_role"] == "frozen_replication"
    assert cal_summary["historically_seen_in_E4"] is True
    assert cal_summary["calibration_functions_historically_seen_in_E4"] is False
    assert cal_summary["generalization_claim"] is False
    assert cal_summary["compute_contract"] == cal_run["compute_contract"]
    assert cal_run["environment"]["torch_threads"] == 1
    assert cal_run["environment"]["torch_interop_threads"] == 1
    assert cal_summary["performance_evidence"] is False
    assert len(cal_summary["weights_sha256"]) == 64
    assert all(
        row["compile_time_only"]
        and row["noisy_endpoint_accessed"] is False
        and row["heldout_aes_accessed"] is False
        and "noisy_endpoints" not in row
        for row in cal_rows
    )

    test_run = json.loads((test / "run.json").read_text(encoding="utf-8"))
    test_summary = json.loads((test / "summary.json").read_text(encoding="utf-8"))
    rows = _rows(test)
    assert str(tmp_path) not in (test / "run.json").read_text(encoding="utf-8")
    assert test_run["status"] == "complete"
    assert test_summary["tiny"] is True
    assert test_summary["phase"] == "replication"
    assert test_summary["legacy_phase_alias"] == "test"
    assert test_summary["experiment_role"] == "frozen_replication"
    assert test_summary["historically_seen_in_E4"] is True
    assert test_summary["generalization_claim"] is False
    assert test_summary["compute_contract"] == test_run["compute_contract"]
    assert test_run["environment"]["torch_threads"] == 1
    assert test_run["environment"]["torch_interop_threads"] == 1
    assert test_summary["formal_statistical_evaluation"] is False
    assert test_summary["performance_claim_supported"] is False
    assert test_summary["primary_endpoint"]["metric"] == "native.two_qubit_gate_count"
    assert test_summary["noisy_diagnostic"]["role"] == (
        "diagnostic_only_not_a_tuning_or_primary_endpoint"
    )
    assert {(row["output_bit"], row["solver_seed"], row["variant"]) for row in rows} == {
        (bit, 1, variant) for bit in (0, 1) for variant in runner.VARIANTS
    }
    for bit in (0, 1):
        bit_rows = [row for row in rows if row["output_bit"] == bit]
        assert len({row["candidate_pool_sha256"] for row in bit_rows}) == 1
        assert len(
            {
                json.dumps(row["raw_scheduler_utilities"], sort_keys=True)
                for row in bit_rows
            }
        ) == 1
    assert all(row["plan_trace"] and row["logical_qasm3"] for row in rows)
    assert all(row["native"]["native_qasm3"] for row in rows)
    assert all(
        row["logical_n_qubits"] == 10
        and row["native"]["n_qubits"] == 10
        and row["record_type"] == "e4_v2_aes_frozen_replication_trial"
        and row["legacy_record_type_alias"] == "e4_v2_aes_test_trial"
        for row in rows
    )
    assert all(
        row["test_noisy_outcome_used_by_utility"] is False
        and row["noisy_success_role"]
        == "diagnostic_only_not_a_tuning_or_primary_endpoint"
        for row in rows
    )
    qaoa = [row for row in rows if row["variant"].endswith("qaoa_shot")]
    assert all(
        row["qaoa_execution"]
        in {"direct_unrepaired", "direct_repaired", "fallback"}
        for row in qaoa
    )
    assert "independent_verifier_ok=True" in completed.stdout

    external = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_e4_v2_bundle.py"),
            str(test),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert external.returncode == 0, external.stdout + external.stderr
    external_result = json.loads(external.stdout)
    assert external_result["ok"] is True
    assert external_result["checks"][
        "frozen_compute_contract_enforced_before_checkpoint_inference"
    ] is True
    assert external_result["checks"][
        "checkpoint_seed_config_pool_utility_selection_plan_rebuilt"
    ] is True

    tampered_bundle = tmp_path / "e4v2-tiny-test-tampered"
    shutil.copytree(test, tampered_bundle)
    tampered_rows = _rows(tampered_bundle)
    for row in tampered_rows:
        row["candidate_pool"]["action_signatures"][0]["immediate_gain"] += 0.125
        row["candidate_pool_sha256"] = sha256_bytes(
            canonical_json_bytes(row["candidate_pool"])
        )
    (tampered_bundle / "raw.jsonl").write_text(
        "".join(
            canonical_json_bytes(row).decode("utf-8")
            for row in tampered_rows
        ),
        encoding="utf-8",
    )
    _resign_bundle(tampered_bundle)
    assert verify_bundle(tampered_bundle).ok
    tampered = verify_e4_v2_bundle(tampered_bundle)
    assert not tampered["ok"]
    assert tampered["checks"]["candidate_pool_hashes_recomputed"] is True
    assert tampered["checks"]["candidate_pool_raw_utility_budget_fair"] is True
    assert (
        tampered["checks"][
            "checkpoint_seed_config_pool_utility_selection_plan_rebuilt"
        ]
        is False
    )


def test_test_phase_requires_explicit_verified_calibration_bundle(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_e4_v2_execution_aware.py"),
            "--tiny",
            "--phase",
            "test",
            "--out-dir",
            str(tmp_path),
            "--run-id",
            "must-fail",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.returncode != 0
    assert "requires --calibration-bundle" in completed.stderr
