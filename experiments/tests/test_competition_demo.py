#!/usr/bin/env python3
"""End-to-end tests for the offline XA competition demo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.verify_demo_output import verify_demo_output


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_competition_demo_runs_direct_qaoa_and_detects_tampering(
    tmp_path: Path,
) -> None:
    output = tmp_path / "demo"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "demo_competition.py"),
            "--case",
            "aes_sbox_bit0",
            "--synthesizer",
            "foundation_nmcts",
            "--scheduler",
            "qaoa_diversity",
            "--hardware",
            "superconducting_noise",
            "--output",
            str(output),
            "--workers",
            "2",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert "qaoa_direct_non_fallback=true" in completed.stdout
    assert "verification_ok=true" in completed.stdout
    verified = verify_demo_output(output)
    assert verified["ok"], verified["errors"]
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["ai_for_quantum"]["learned_policy_active"] is True
    assert report["ai_for_quantum"]["learned_value_enabled"] is False
    assert report["quantum_for_ai"]["direct_non_fallback"] is True
    assert report["native_and_noise"]["actual_noisy_simulation"] is True
    assert report["native_and_noise"]["hardware_execution"] is False
    assert report["scope"]["performance_evidence"] is False
    execution_log = (output / "execution.log").read_text(encoding="utf-8")
    assert str(PROJECT_ROOT) not in execution_log
    assert "${PROJECT_ROOT}" in execution_log

    report_path = output / "report.json"
    report_path.write_text(
        report_path.read_text(encoding="utf-8").replace(
            '"performance_evidence":false',
            '"performance_evidence":true',
            1,
        ),
        encoding="utf-8",
    )
    tampered = verify_demo_output(output)
    assert not tampered["ok"]
    assert "check failed: outer_checksums" in tampered["errors"]
