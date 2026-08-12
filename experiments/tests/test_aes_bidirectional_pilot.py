#!/usr/bin/env python3
"""End-to-end contract test for the AES bidirectional tiny pilot."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_aes_bidirectional_pilot as runner
from scripts.verify_aes_bidirectional_bundle import verify_aes_bundle
from src.contracts.artifacts import verify_bundle


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class _UnavailableProcessPool:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("process semaphores unavailable")


def test_process_pool_permission_error_falls_back_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = [
        {"output_bit": bit, "variant": variant, "seed": 930000 + bit}
        for bit in range(2)
        for variant in ("classical_greedy", "qaoa_shot")
    ]
    seen: list[dict[str, object]] = []
    completed: list[dict[str, object]] = []

    def worker(job: dict[str, object]) -> dict[str, object]:
        seen.append(dict(job))
        return {"job": dict(job)}

    monkeypatch.setattr(runner, "ProcessPoolExecutor", _UnavailableProcessPool)
    monkeypatch.setattr(runner, "_trial_worker", worker)

    mode = runner._run_trial_jobs(
        jobs,
        workers=2,
        record_completed=completed.append,
    )

    assert mode == "in_process_fallback"
    assert seen == jobs
    assert completed == [{"job": job} for job in jobs]


def test_process_pool_fallback_does_not_swallow_worker_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def worker(job: dict[str, object]) -> dict[str, object]:
        del job
        raise OSError("algorithm failure")

    monkeypatch.setattr(runner, "ProcessPoolExecutor", _UnavailableProcessPool)
    monkeypatch.setattr(runner, "_trial_worker", worker)

    with pytest.raises(OSError, match="algorithm failure"):
        runner._run_trial_jobs(
            [{"output_bit": 0, "variant": "qaoa_shot"}],
            workers=2,
            record_completed=lambda result: None,
        )


def test_aes_tiny_pilot_closes_all_eight_coordinates_and_detects_tampering(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_aes_bidirectional_pilot.py"),
            "--tiny",
            "--out-dir",
            str(tmp_path),
            "--run-id",
            "aes-bidirectional-tiny-test",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    bundle = tmp_path / "aes-bidirectional-tiny-test"
    integrity = verify_bundle(bundle)
    assert integrity.ok, integrity.errors
    assert {path.name for path in bundle.iterdir()} == {
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

    run = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    summary = json.loads((bundle / "summary.json").read_text(encoding="utf-8"))
    declared = json.loads((bundle / "verifier.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (bundle / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert run["track"] == "aes-bidirectional-pilot"
    assert run["status"] == "complete"
    assert run["command"]["workers"] >= 1
    assert run["command"]["execution_mode"] in {
        "in_process",
        "in_process_fallback",
        "process_pool",
    }
    assert str(tmp_path) not in (bundle / "run.json").read_text(encoding="utf-8")
    assert summary["coordinate_count"] == 8
    assert summary["trial_count"] == 16
    assert summary["scope"] == {
        "actual_noisy_simulation": True,
        "hardware_execution": False,
        "logical_equivalence_scope": "all-256-inputs-and-both-target-values",
        "native_equivalence_scope": "not-run-at-aes-scale",
        "native_execution_scope": "sampled-noisy-endpoints",
        "performance_evidence": False,
        "qaoa_backend": "small-statevector-shot-simulator",
        "quantum_advantage_claimed": False,
        "tiny": True,
    }
    assert declared["ok"] and all(declared["checks"].values())
    assert {
        (row["output_bit"], row["variant"])
        for row in rows
    } == {
        (bit, variant)
        for bit in range(8)
        for variant in ("classical_greedy", "qaoa_shot")
    }
    for bit in range(8):
        paired = [row for row in rows if row["output_bit"] == bit]
        assert len({row["candidate_pool_sha256"] for row in paired}) == 1
    assert all(
        row["plan_anf_ok"]
        and row["circuit_anf_ok"]
        and row["oracle_ok"]
        and row["reversible_oracle_all_targets_ok"]
        for row in rows
    )
    assert all(
        row["native"]["native_gate_set_ok"]
        and row["native"]["coupling_ok"]
        and row["native"]["hardware_execution"] is False
        and row["native"]["ideal_basis_equivalence"]["status"]
        == "not_run_scale_bound"
        for row in rows
    )
    assert all(
        endpoint["actual_noisy_simulation"]
        and endpoint["hardware_execution"] is False
        and endpoint["noise_applied"]
        and endpoint["task_contract_ok"]
        for row in rows
        for endpoint in row["noisy_endpoints"]
    )
    qaoa_rows = [row for row in rows if row["variant"] == "qaoa_shot"]
    assert len(qaoa_rows) == 8
    assert all(
        row["scheduler"]["qaoa_attempted"]
        and (
            row["scheduler"]["qaoa_succeeded"]
            or row["scheduler"]["qaoa_fallback"]
        )
        for row in qaoa_rows
    )
    independent = verify_aes_bundle(bundle)
    assert independent["ok"], independent["errors"]
    assert "bundle_ok=True" in completed.stdout
    assert "independent_verifier_ok=True" in completed.stdout

    summary_path = bundle / "summary.json"
    summary_path.write_text(
        summary_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    tampered = verify_aes_bundle(bundle)
    assert not tampered["ok"]
    assert any("mismatch" in error for error in tampered["errors"])
