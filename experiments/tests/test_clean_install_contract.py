#!/usr/bin/env python3
"""Regression test for the repository-relative clean-install verifier."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_clean_install_contract() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_clean_install.py"),
            "--quick",
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    assert report["mode"] == "quick"
    assert report["checks"]["dependencies"]["scipy_milp_probe"] is True
    assert report["checks"]["dependencies"]["pulp_model_probe"] is True
    assert report["checks"]["foundation_model"]["parameters"] == 60_450
    assert report["checks"]["foundation_model"]["checkpoint_sha256"] == (
        "87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d"
    )
    assert report["checks"]["qaoa_direct_mini"]["execution_mode"] == (
        "direct_qaoa_statevector"
    )
    assert report["checks"]["native_noise_mini"]["hardware_execution"] is False
    assert report["checks"]["competition_demo"]["executed"] is False
