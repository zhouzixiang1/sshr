#!/usr/bin/env python3
"""Build a small deterministic three-route hardware compatibility bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hardware.ion_trap import (  # noqa: E402
    CLAIM_BOUNDARY as ION_CLAIM_BOUNDARY,
    EVIDENCE_STRENGTH as ION_EVIDENCE_STRENGTH,
    ION_NATIVE_GATE_SET,
    RXX_CONVENTION,
    compile_ion_trap,
    ion_native_to_openqasm3,
    verify_ion_trap_equivalence,
)
from src.hardware.noise import simulate_noisy_shots  # noqa: E402
from src.hardware.photonic import photonic_capability_record  # noqa: E402
from src.hardware.qasm import GATE_MODE, LogicalCircuitIR, LogicalGateIR  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    native_to_openqasm3,
    verify_basis_equivalence,
)


SCHEMA = "xa.hardware-routes-manifest.v1"
SUPERCONDUCTING_CLAIM_BOUNDARY = (
    "Executable ideal compilation and actual seeded Pauli-trajectory shots "
    "against a declared synthetic heavy-hex-like profile. This is not a "
    "vendor device, calibration snapshot, pulse model, real hardware run, "
    "speedup result, or quantum-advantage result."
)
SUPERCONDUCTING_EVIDENCE_STRENGTH = (
    "synthetic-full-basis-and-seeded-noisy-trajectory"
)


class BundleBuildError(RuntimeError):
    """Raised when deterministic bundle construction cannot complete."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value: Any) -> Any:
    """Convert dataclasses/tuples into the canonical JSON value model."""

    return json.loads(canonical_json(value).decode("utf-8"))


def logical_record(logical_ir: LogicalCircuitIR) -> dict[str, Any]:
    return {
        "gate_mode": logical_ir.gate_mode,
        "n_qubits": logical_ir.n_qubits,
        "gates": [
            {
                "gate_type": gate.gate_type,
                "controls": list(gate.controls),
                "target": gate.target,
            }
            for gate in logical_ir.gates
        ],
    }


def native_records(gates: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [normalized(asdict(gate)) for gate in gates]


def ion_cases() -> tuple[tuple[str, LogicalCircuitIR], ...]:
    return (
        ("x", LogicalCircuitIR(1, (LogicalGateIR("X", (), 0),))),
        ("cnot", LogicalCircuitIR(2, (LogicalGateIR("CNOT", (0,), 1),))),
        ("toffoli", LogicalCircuitIR(3, (LogicalGateIR("MCT", (0, 1), 2),))),
        (
            "three-control-mct",
            LogicalCircuitIR(4, (LogicalGateIR("MCT", (0, 1, 2), 3),)),
        ),
    )


def superconducting_logical_ir() -> LogicalCircuitIR:
    return LogicalCircuitIR(
        3,
        (
            LogicalGateIR("X", (), 0),
            LogicalGateIR("CNOT", (0,), 2),
            LogicalGateIR("MCT", (0, 1), 2),
        ),
    )


def build_ion_artifact(run_id: str) -> dict[str, Any]:
    cases = []
    for case_id, logical_ir in ion_cases():
        compilation = compile_ion_trap(logical_ir)
        equivalence = verify_ion_trap_equivalence(
            compilation,
            tolerance=1e-9,
            max_qubits=4,
        )
        if not (
            equivalence.basis_equivalent
            and equivalence.unitary_equivalent_up_to_global_phase
        ):
            raise BundleBuildError(f"ion-trap equivalence failed for {case_id}")
        qasm = ion_native_to_openqasm3(compilation).encode("utf-8")
        cases.append(
            {
                "case_id": case_id,
                "logical_ir": logical_record(logical_ir),
                "native_gates": native_records(compilation.native_gates),
                "diagnostics": normalized(asdict(compilation.diagnostics)),
                "equivalence": normalized(asdict(equivalence)),
                "native_qasm3_sha256": sha256_bytes(qasm),
            }
        )
    return {
        "schema_version": "xa.ion-trap-route-evidence.v1",
        "run_id": run_id,
        "route_id": "ion_trap",
        "route_kind": "ideal_resource_adapter",
        "executable": True,
        "hardware_execution": False,
        "native_gate_set": list(ION_NATIVE_GATE_SET),
        "connectivity": "fully_connected",
        "routing_swaps_allowed": False,
        "rxx_convention": RXX_CONVENTION,
        "evidence_strength": ION_EVIDENCE_STRENGTH,
        "claim_boundary": ION_CLAIM_BOUNDARY,
        "cases": cases,
    }


def build_superconducting_artifact(run_id: str, seed: int) -> dict[str, Any]:
    logical_ir = superconducting_logical_ir()
    noise = NoiseParameters(
        model="synthetic-hardware-route-smoke-v1",
        one_qubit_error=0.001,
        two_qubit_error=0.01,
        readout_error=0.02,
    )
    profile = heavy_hex_like_profile(3, noise=noise)
    compilation = compile_superconducting(logical_ir, profile)
    equivalence = verify_basis_equivalence(compilation, tolerance=1e-9, max_qubits=3)
    if not equivalence.equivalent:
        raise BundleBuildError("superconducting ideal equivalence failed")
    logical_input = (0, 1, 0)
    noisy = simulate_noisy_shots(
        compilation,
        logical_input,
        shots=16,
        seed=seed,
        max_qubits=3,
    )
    if not noisy.actual_noisy_simulation or noisy.hardware_execution:
        raise BundleBuildError("superconducting noisy execution boundary failed")
    return {
        "schema_version": "xa.superconducting-route-evidence.v1",
        "run_id": run_id,
        "route_id": "superconducting",
        "route_kind": "synthetic_executable_noisy",
        "executable": True,
        "hardware_execution": False,
        "evidence_strength": SUPERCONDUCTING_EVIDENCE_STRENGTH,
        "claim_boundary": SUPERCONDUCTING_CLAIM_BOUNDARY,
        "logical_ir": logical_record(logical_ir),
        "profile": normalized(asdict(profile)),
        "native_gates": native_records(compilation.native_gates),
        "diagnostics": normalized(asdict(compilation.diagnostics)),
        "basis_equivalence": normalized(asdict(equivalence)),
        "native_qasm3_sha256": sha256_bytes(
            native_to_openqasm3(compilation).encode("utf-8")
        ),
        "noisy_execution": {
            "logical_input_bits": list(logical_input),
            "shots": 16,
            "seed": seed,
            "result": normalized(asdict(noisy)),
        },
    }


def route_descriptor(artifact_name: str, artifact: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "route_id": artifact["route_id"],
        "route_kind": artifact["route_kind"],
        "artifact": artifact_name,
        "artifact_sha256": sha256_file(path),
        "artifact_size_bytes": path.stat().st_size,
        "executable": artifact["executable"],
        "hardware_execution": artifact["hardware_execution"],
        "evidence_strength": artifact["evidence_strength"],
        "claim_boundary": artifact["claim_boundary"],
    }


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json(value))


def build_bundle(output: Path, run_id: str, seed: int) -> dict[str, Any]:
    output = output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise BundleBuildError(f"output directory must be absent or empty: {output}")
    created = not output.exists()
    output.mkdir(parents=True, exist_ok=True)
    try:
        artifacts = {
            "ion_trap.json": build_ion_artifact(run_id),
            "photonic.json": {
                **photonic_capability_record(),
                "run_id": run_id,
            },
            "superconducting.json": build_superconducting_artifact(run_id, seed),
        }
        for name, payload in artifacts.items():
            write_json(output / name, payload)

        logical_contract = {
            "gate_mode": GATE_MODE,
            "ion_cases": [
                {"case_id": case_id, "logical_ir": logical_record(logical_ir)}
                for case_id, logical_ir in ion_cases()
            ],
            "superconducting_case": logical_record(superconducting_logical_ir()),
        }
        routes = [
            route_descriptor(name, artifacts[name], output / name)
            for name in ("superconducting.json", "ion_trap.json", "photonic.json")
        ]
        manifest = {
            "schema_version": SCHEMA,
            "competition_id": "XA-202609",
            "run_id": run_id,
            "seed": seed,
            "deterministic": True,
            "hardware_execution": False,
            "logical_contract_sha256": sha256_bytes(canonical_json(logical_contract)),
            "rxx_convention": RXX_CONVENTION,
            "routes": routes,
            "claim_boundary": (
                "A route-specific compatibility manifest, not evidence of real "
                "hardware execution or quantum advantage. Evidence strengths and "
                "unsupported boundaries must be interpreted per route."
            ),
        }
        write_json(output / "routes_manifest.json", manifest)

        verifier_script = Path(__file__).with_name("verify_hardware_routes_bundle.py")
        completed = subprocess.run(
            [sys.executable, str(verifier_script), "--semantic-only", str(output)],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise BundleBuildError(
                "independent semantic verifier rejected generated payload: "
                + completed.stdout
                + completed.stderr
            )
        verifier_record = json.loads(completed.stdout)
        write_json(output / "verifier.json", verifier_record)

        roles = {
            "ion_trap.json": "ion_trap_ideal_evidence",
            "photonic.json": "photonic_boundary",
            "routes_manifest.json": "unified_route_manifest",
            "superconducting.json": "superconducting_synthetic_evidence",
            "verifier.json": "independent_semantic_verifier_record",
        }
        artifact_rows = []
        for name in sorted(roles):
            path = output / name
            artifact_rows.append(
                {
                    "relative_path": name,
                    "role": roles[name],
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        write_json(
            output / "artifacts.manifest.json",
            {
                "schema_version": "xa.hardware-routes-artifact-bundle.v1",
                "run_id": run_id,
                "artifacts": artifact_rows,
            },
        )
        checksum_names = sorted([*roles, "artifacts.manifest.json"])
        (output / "checksums.sha256").write_text(
            "".join(f"{sha256_file(output / name)}  {name}\n" for name in checksum_names),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "run_id": run_id,
            "output": str(output),
            "file_count": len(list(output.iterdir())),
            "checksums_sha256": sha256_file(output / "checksums.sha256"),
        }
    except Exception:
        if created:
            shutil.rmtree(output, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--output-dir", required=True, type=Path)
    command.add_argument("--run-id", required=True)
    command.add_argument("--seed", type=int, default=202609)
    return command


def main() -> int:
    args = parser().parse_args()
    if not args.run_id or args.seed < 0:
        raise SystemExit("run-id must be non-empty and seed must be non-negative")
    try:
        result = build_bundle(args.output_dir, args.run_id, args.seed)
    except (BundleBuildError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
