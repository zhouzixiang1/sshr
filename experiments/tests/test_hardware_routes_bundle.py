"""Determinism and semantic tamper tests for the three-route bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BUILDER = EXPERIMENT_ROOT / "scripts/build_hardware_routes_bundle.py"
VERIFIER = EXPERIMENT_ROOT / "scripts/verify_hardware_routes_bundle.py"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        cwd=EXPERIMENT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _build(path: Path) -> None:
    result = _run(
        BUILDER,
        "--output-dir",
        path,
        "--run-id",
        "unit-test-hardware-routes",
        "--seed",
        "202609",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_bundle_is_byte_deterministic_and_independently_verified(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _build(first)
    _build(second)

    assert [path.name for path in sorted(first.iterdir())] == [
        path.name for path in sorted(second.iterdir())
    ]
    for path in sorted(first.iterdir()):
        assert path.read_bytes() == (second / path.name).read_bytes(), path.name
    verified = _run(VERIFIER, first)
    assert verified.returncode == 0, verified.stdout + verified.stderr
    payload = json.loads(verified.stdout)
    assert payload["ok"] is True
    assert payload["hardware_execution"] is False
    assert all(payload["checks"].values())


def _resign_structural_hashes(bundle: Path) -> None:
    """Simulate an attacker updating every structural hash after tampering."""

    routes = json.loads((bundle / "routes_manifest.json").read_text(encoding="utf-8"))
    ion_row = next(row for row in routes["routes"] if row["route_id"] == "ion_trap")
    ion_row["artifact_sha256"] = _sha(bundle / "ion_trap.json")
    ion_row["artifact_size_bytes"] = (bundle / "ion_trap.json").stat().st_size
    (bundle / "routes_manifest.json").write_bytes(_canonical(routes))

    verifier = json.loads((bundle / "verifier.json").read_text(encoding="utf-8"))
    verifier["subject"]["routes_manifest_sha256"] = _sha(
        bundle / "routes_manifest.json"
    )
    verifier["subject"]["route_artifact_sha256"]["ion_trap.json"] = _sha(
        bundle / "ion_trap.json"
    )
    (bundle / "verifier.json").write_bytes(_canonical(verifier))

    artifact_manifest = json.loads(
        (bundle / "artifacts.manifest.json").read_text(encoding="utf-8")
    )
    for row in artifact_manifest["artifacts"]:
        target = bundle / row["relative_path"]
        row["sha256"] = _sha(target)
        row["size_bytes"] = target.stat().st_size
    (bundle / "artifacts.manifest.json").write_bytes(_canonical(artifact_manifest))

    names = sorted(
        path.name for path in bundle.iterdir() if path.name != "checksums.sha256"
    )
    (bundle / "checksums.sha256").write_text(
        "".join(f"{_sha(bundle / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def test_tampered_rxx_fails_semantic_recompute_after_full_resign(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original"
    tampered = tmp_path / "tampered"
    _build(original)
    shutil.copytree(original, tampered)

    ion = json.loads((tampered / "ion_trap.json").read_text(encoding="utf-8"))
    cnot = next(case for case in ion["cases"] if case["case_id"] == "cnot")
    entangler = next(gate for gate in cnot["native_gates"] if gate["name"] == "rxx")
    entangler["angle"] += 0.125
    (tampered / "ion_trap.json").write_bytes(_canonical(ion))
    _resign_structural_hashes(tampered)

    rejected = _run(VERIFIER, tampered)
    assert rejected.returncode == 2
    payload = json.loads(rejected.stdout)
    assert payload["checks"]["outer_checksum_values"] is True
    assert payload["checks"]["artifact_manifest"] is True
    assert payload["checks"]["manifest_artifact_hashes"] is True
    assert payload["checks"]["ion_deterministic_recompile"] is False
    assert payload["checks"]["ion_unitary_up_to_global_phase"] is False
    assert payload["ok"] is False
