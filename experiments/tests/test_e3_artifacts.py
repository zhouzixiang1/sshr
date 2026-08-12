#!/usr/bin/env python3
"""End-to-end contract tests for E3 calibration/test evidence bundles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_hardware_feedback_eval import (
    CONFIG_SCHEMA,
    _qaoa_not_invoked,
    load_config,
    run_calibration,
    run_test,
)
from scripts.verify_hardware_feedback_bundle import verify_e3_bundle


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "xa202609" / "e3_native_feedback_v1.json"


def test_e3_config_is_frozen_and_tiny_preserves_the_full_intervention() -> None:
    regular = load_config(CONFIG_PATH)
    tiny = load_config(CONFIG_PATH, tiny=True)

    assert regular["schema_version"] == CONFIG_SCHEMA
    assert regular["calibration"]["seed_base"] != regular["test"]["seed_base"]
    assert regular["noise_execution"]["include_output_zero_and_one"] is True
    assert regular["native_profile"]["native_gate_set"] == ["rz", "sx", "x", "cx"]
    assert tiny["calibration"]["case_count"] == 1
    assert tiny["test"]["case_count"] == 1
    assert tiny["noise_execution"]["shots_per_input"] == 1
    assert tiny["search"]["scheduler_budget"] == regular["search"]["scheduler_budget"]


def test_invalid_e3_config_is_rejected(tmp_path: Path) -> None:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    value["noise_execution"]["include_output_zero_and_one"] = False
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="output-ancilla"):
        load_config(path)


def test_qaoa_outcome_partition_excludes_classical_no_action_rows() -> None:
    assert _qaoa_not_invoked("historical_qaoa_shot", "not_applicable_no_actions")
    assert _qaoa_not_invoked("feedback_qaoa_shot", "qaoa_not_invoked")
    assert not _qaoa_not_invoked("historical_greedy", "not_applicable_no_actions")


def test_tiny_calibration_and_test_are_separate_verified_bundles(
    tmp_path: Path,
) -> None:
    config = load_config(CONFIG_PATH, tiny=True)
    calibration = run_calibration(
        config=config,
        out_dir=tmp_path,
        run_id="test-e3-calibration-tiny",
        tiny=True,
        config_path=CONFIG_PATH,
    )
    calibration_verification = verify_e3_bundle(calibration)
    assert calibration_verification["ok"], calibration_verification["errors"]

    test = run_test(
        config=config,
        calibration_run=calibration,
        out_dir=tmp_path,
        run_id="test-e3-heldout-tiny",
        tiny=True,
        config_path=CONFIG_PATH,
    )
    test_verification = verify_e3_bundle(test)
    assert test_verification["ok"], test_verification["errors"]

    calibration_summary = json.loads(
        (calibration / "summary.json").read_text(encoding="utf-8")
    )
    test_summary = json.loads((test / "summary.json").read_text(encoding="utf-8"))
    test_declared = json.loads((test / "verifier.json").read_text(encoding="utf-8"))
    assert calibration_summary["phase"] == "calibration"
    assert test_summary["phase"] == "test"
    assert calibration_summary["model_sha256"] == (
        test_summary["calibration_reference"]["model_sha256"]
    )
    assert set(calibration_summary["truth_table_sha256"]).isdisjoint(
        test_summary["truth_table_sha256"]
    )
    assert test_summary["trial_count"] == 4
    assert test_summary["statistics"]["primary_comparison"]["claim_supported"] is False
    assert all(test_declared["checks"].values())


def test_independent_verifier_detects_bundle_tampering(tmp_path: Path) -> None:
    config = load_config(CONFIG_PATH, tiny=True)
    calibration = run_calibration(
        config=config,
        out_dir=tmp_path,
        run_id="test-e3-tamper-source",
        tiny=True,
        config_path=CONFIG_PATH,
    )
    summary_path = calibration / "summary.json"
    summary_path.write_text(summary_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = verify_e3_bundle(calibration)
    assert not result["ok"]
    assert any("mismatch" in error for error in result["errors"])
