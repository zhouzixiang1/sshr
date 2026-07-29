#!/usr/bin/env python3
"""Capture a reproducible, privacy-conscious competition environment manifest.

Run with the ``mcts-qoracle`` interpreter from ``resource_nmcts``.  The script
records versions, GPU capability, Aer device support, git provenance and hashes
of critical code/model artifacts without embedding the local user name or an
absolute home-directory path.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "submission_competition" / "environment_manifest.json"
DEFAULT_PACKAGES = ROOT / "submission_competition" / "environment_packages.txt"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_text(args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip()


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def package_inventory() -> list[str]:
    rows = {
        f"{dist.metadata.get('Name', 'unknown')}=={dist.version}"
        for dist in importlib.metadata.distributions()
    }
    return sorted(rows, key=str.casefold)


def gpu_manifest(run_smoke: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_count": int(torch.cuda.device_count()),
    }
    devices = []
    if torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(index)
            devices.append(
                {
                    "index": index,
                    "name": props.name,
                    "compute_capability": [int(props.major), int(props.minor)],
                    "total_memory_bytes": int(props.total_memory),
                    "multi_processor_count": int(props.multi_processor_count),
                }
            )
    result["devices"] = devices

    query = run_text(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,compute_cap,pstate,power.limit",
            "--format=csv,noheader,nounits",
        ]
    )
    result["nvidia_smi_query"] = query.splitlines() if query else None

    smoke: dict[str, Any] = {"requested": bool(run_smoke), "ok": None}
    if run_smoke and torch.cuda.is_available():
        try:
            generator = torch.Generator(device="cuda").manual_seed(202609)
            left = torch.randn((2048, 2048), generator=generator, device="cuda")
            right = torch.randn((2048, 2048), generator=generator, device="cuda")
            torch.cuda.synchronize()
            start = time.perf_counter()
            product = left @ right
            checksum = float(product[:8, :8].float().sum().detach().cpu())
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            smoke.update(
                {
                    "ok": bool(torch.isfinite(product).all().item()),
                    "operation": "float32 matmul 2048x2048",
                    "elapsed_s": elapsed,
                    "checksum": checksum,
                }
            )
        except Exception as exc:  # Evidence should record the failure, not hide it.
            smoke.update({"ok": False, "error_type": type(exc).__name__, "error": str(exc)})
    result["smoke"] = smoke
    return result


def aer_manifest() -> dict[str, Any]:
    try:
        from qiskit_aer import AerSimulator

        simulator = AerSimulator()
        return {
            "available_devices": list(simulator.available_devices()),
            "available_methods": list(simulator.available_methods()),
        }
    except Exception as exc:
        return {"error_type": type(exc).__name__, "error": str(exc)}


def git_manifest() -> dict[str, Any]:
    commit = run_text(["git", "rev-parse", "HEAD"])
    status = run_text(["git", "status", "--short"])
    diff = run_text(["git", "diff", "--binary", "--", "."])
    return {
        "commit": commit,
        "dirty": bool(status),
        "status_lines": status.splitlines() if status else [],
        "tracked_diff_sha256": sha256_bytes((diff or "").encode("utf-8")),
    }


def artifact_manifest() -> list[dict[str, Any]]:
    candidates = [
        ROOT / "src" / "competition_benchmarks.py",
        ROOT / "src" / "factor_plan.py",
        ROOT / "src" / "neural_policy.py",
        ROOT / "src" / "synthesizers.py",
        ROOT / "src" / "hardware_map.py",
        ROOT / "src" / "experiment_db.py",
        ROOT / "src" / "hardware_validation_ingest.py",
        ROOT / "scripts" / "train_neural_policy.py",
        ROOT / "scripts" / "run_hardware_validation.py",
        ROOT / "analysis" / "analyze_competition_results.py",
        ROOT / "analysis" / "audit_formal_coverage.py",
        ROOT / "analysis" / "consolidate_verified_experiment.py",
        ROOT / "analysis" / "build_final_primary20_report.py",
        ROOT / "analysis" / "qa_competition_pdf.py",
        ROOT / "analysis" / "audit_competition_literature.ps1",
        ROOT / "models" / "action_scorer.pt",
        ROOT / "models" / "action_scorer_competition.pt",
        ROOT / "models" / "action_scorer_rollout_competition.pt",
        ROOT / "submission_competition" / "benchmark_suite_v1.json",
        ROOT / "submission_competition" / "training_manifest_competition.json",
        ROOT / "submission_competition" / "training_manifest_rollout_competition.json",
        ROOT / "submission_competition" / "main.tex",
        ROOT / "submission_competition" / "main.pdf",
        ROOT / "submission_competition" / "generated_final_numbers.tex",
        ROOT / "submission_competition" / "final_analysis_manifest.json",
        ROOT / "submission_competition" / "formal_coverage_audit.json",
        ROOT / "submission_competition" / "literature_verification_audit.json",
        ROOT / "submission_competition" / "figures" / "ai_ablation_figure_manifest.json",
        ROOT / "submission_competition" / "figures" / "primary_results_figure_manifest.json",
        ROOT / "submission_competition" / "figures" / "coverage_resource_figure_manifest.json",
        ROOT / "results" / "competition_primary20_final.duckdb",
        ROOT / "results" / "final_stats" / "primary20_headline.json",
    ]
    rows = []
    for path in candidates:
        if not path.exists():
            continue
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--packages", type=Path, default=DEFAULT_PACKAGES)
    parser.add_argument("--skip-gpu-smoke", action="store_true")
    args = parser.parse_args()

    packages = package_inventory()
    package_payload = "\n".join(packages) + "\n"
    args.packages.parent.mkdir(parents=True, exist_ok=True)
    args.packages.write_text(package_payload, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment_name": Path(sys.prefix).name,
        "shell_conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable_name": Path(sys.executable).name,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
        },
        "key_packages": {
            name: package_version(name)
            for name in (
                "torch",
                "qiskit",
                "qiskit-aer",
                "duckdb",
                "numpy",
                "pandas",
                "scipy",
                "matplotlib",
                "pylatexenc",
                "PyMuPDF",
            )
        },
        "gpu": gpu_manifest(run_smoke=not args.skip_gpu_smoke),
        "aer": aer_manifest(),
        "git": git_manifest(),
        "critical_artifacts": artifact_manifest(),
        "package_inventory": {
            "path": args.packages.name,
            "entries": len(packages),
            "sha256": sha256_bytes(package_payload.encode("utf-8")),
        },
        "privacy": "absolute user/home paths and host name intentionally omitted",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
