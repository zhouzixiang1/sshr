#!/usr/bin/env python3
"""Contract and tamper tests for the independent offline fallback asset."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.verify_offline_fallback import verify_offline_fallback


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_FILES = {
    "input.json",
    "report.json",
    "report.md",
    "execution.log",
    "logical.qasm",
    "native.qasm",
    "fallback_manifest.json",
    "checksums.sha256",
    "verification.json",
}


def _run(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "demo_offline_fallback.py"),
            "--case",
            "aes_sbox_bit0",
            "--synthesizer",
            "direct_anf",
            "--scheduler",
            "none",
            "--hardware",
            "synthetic_superconducting_noise",
            "--output",
            str(output),
            "--seed",
            "940000",
            "--input-x",
            "0x53",
            "--shots",
            "1",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_offline_fallback_is_deterministic_separate_and_tamper_evident(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    completed = _run(first)
    _run(second)

    assert {path.name for path in first.iterdir()} == EXPECTED_FILES
    assert {path.name for path in second.iterdir()} == EXPECTED_FILES
    assert {
        path.name: path.read_bytes() for path in first.iterdir()
    } == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    assert "fallback_only=true" in completed.stdout
    assert "learned_policy_invoked=false" in completed.stdout
    assert "qaoa_invoked=false" in completed.stdout
    assert "performance_evidence=false" in completed.stdout
    assert "hardware_execution=false" in completed.stdout
    assert "verification_ok=true" in completed.stdout

    verified = verify_offline_fallback(first)
    assert verified["ok"], verified["errors"]
    assert all(verified["checks"].values())
    persisted = json.loads(
        (first / "verification.json").read_text(encoding="utf-8")
    )
    assert persisted == verified

    input_record = json.loads((first / "input.json").read_text(encoding="utf-8"))
    report = json.loads((first / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (first / "fallback_manifest.json").read_text(encoding="utf-8")
    )
    assert input_record["synthesizer"] == "direct_anf"
    assert input_record["scheduler"] == "none"
    assert input_record["learned_policy_enabled"] is False
    assert input_record["qaoa_enabled"] is False
    assert report["execution"]["fallback_only"] is True
    assert report["execution"]["learned_policy_invoked"] is False
    assert report["execution"]["qaoa_invoked"] is False
    assert report["scope"]["performance_evidence"] is False
    assert report["scope"]["hardware_execution"] is False
    assert "quantum_for_ai" not in report
    assert report["logical"]["semantic_checks_all"] is True
    assert report["native_and_noise"]["actual_noisy_simulation"] is True
    assert manifest["artifact_kind"] == "offline_deterministic_fallback"
    assert manifest["fallback_only"] is True
    assert manifest["qaoa_invoked"] is False

    report_path = first / "report.json"
    report_path.write_text(
        report_path.read_text(encoding="utf-8").replace(
            '"fallback_only":true',
            '"fallback_only":false',
            1,
        ),
        encoding="utf-8",
    )
    tampered = verify_offline_fallback(first)
    assert not tampered["ok"]
    assert "check failed: outer_checksums" in tampered["errors"]
    assert "check failed: manifest_file_hashes" in tampered["errors"]
    assert "check failed: fallback_scope_report" in tampered["errors"]
