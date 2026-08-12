#!/usr/bin/env python3
"""Independently verify a three-route hardware compatibility bundle.

This verifier does not import the bundle builder.  It checks structural hashes,
recompiles the synthetic superconducting and ideal ion-trap routes, reruns the
seeded noisy trajectory, and independently reconstructs every recorded ion
native unitary under ``RXX(theta)=exp(-i theta X⊗X/2)``.  Re-signing outer
checksums after modifying a native angle therefore cannot satisfy the semantic
checks.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import cmath
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np


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


SEMANTIC_SCHEMA = "xa.hardware-routes-semantic-verifier.v1"
FINAL_SCHEMA = "xa.hardware-routes-bundle-verifier.v1"
EXPECTED_FILES = {
    "artifacts.manifest.json",
    "checksums.sha256",
    "ion_trap.json",
    "photonic.json",
    "routes_manifest.json",
    "superconducting.json",
    "verifier.json",
}
CHECKSUM_FILES = EXPECTED_FILES - {"checksums.sha256"}
ARTIFACT_FILES = CHECKSUM_FILES - {"artifacts.manifest.json"}
SUPERCONDUCTING_CLAIM_BOUNDARY = (
    "Executable ideal compilation and actual seeded Pauli-trajectory shots "
    "against a declared synthetic heavy-hex-like profile. This is not a "
    "vendor device, calibration snapshot, pulse model, real hardware run, "
    "speedup result, or quantum-advantage result."
)
SUPERCONDUCTING_EVIDENCE_STRENGTH = (
    "synthetic-full-basis-and-seeded-noisy-trajectory"
)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def normalized(value: Any) -> Any:
    return json.loads(canonical_json(value).decode("utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _apply_one(state: np.ndarray, qubit: int, matrix: np.ndarray) -> None:
    stride = 1 << qubit
    period = stride << 1
    for start in range(0, state.size, period):
        for offset in range(stride):
            i0 = start + offset
            i1 = i0 + stride
            a0, a1 = state[i0], state[i1]
            state[i0] = matrix[0, 0] * a0 + matrix[0, 1] * a1
            state[i1] = matrix[1, 0] * a0 + matrix[1, 1] * a1


def independent_ion_unitary(case: dict[str, Any]) -> tuple[np.ndarray | None, bool]:
    """Build the recorded native unitary without calling the ion simulator."""

    try:
        logical = case["logical_ir"]
        n_qubits = int(logical["n_qubits"])
        dimension = 1 << n_qubits
        unitary = np.eye(dimension, dtype=np.complex128)
        native_ok = True
        for gate in case["native_gates"]:
            name = gate.get("name")
            qubits = gate.get("qubits")
            angle = gate.get("angle")
            if (
                name not in ION_NATIVE_GATE_SET
                or not isinstance(qubits, list)
                or len(qubits) != (2 if name == "rxx" else 1)
                or len(set(qubits)) != len(qubits)
                or any(not isinstance(q, int) or isinstance(q, bool) or not 0 <= q < n_qubits for q in qubits)
                or not isinstance(angle, (int, float))
                or isinstance(angle, bool)
                or not math.isfinite(float(angle))
                or gate.get("inserted_for_routing") is not False
            ):
                native_ok = False
                break
            angle = float(angle)
            for column in range(dimension):
                state = unitary[:, column].copy()
                if name == "rz":
                    matrix = np.array(
                        [
                            [cmath.exp(-0.5j * angle), 0.0],
                            [0.0, cmath.exp(0.5j * angle)],
                        ],
                        dtype=np.complex128,
                    )
                    _apply_one(state, qubits[0], matrix)
                elif name == "rx":
                    cosine = math.cos(angle / 2)
                    sine = -1j * math.sin(angle / 2)
                    _apply_one(
                        state,
                        qubits[0],
                        np.array(
                            [[cosine, sine], [sine, cosine]], dtype=np.complex128
                        ),
                    )
                else:
                    old = state.copy()
                    mask = (1 << qubits[0]) | (1 << qubits[1])
                    for index in range(dimension):
                        state[index] = (
                            math.cos(angle / 2) * old[index]
                            - 1j * math.sin(angle / 2) * old[index ^ mask]
                        )
                unitary[:, column] = state
        return (unitary if native_ok else None), native_ok
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, False


def expected_logical_unitary(logical_ir: LogicalCircuitIR) -> np.ndarray:
    dimension = 1 << logical_ir.n_qubits
    expected = np.zeros((dimension, dimension), dtype=np.complex128)
    for basis in range(dimension):
        bits = [(basis >> qubit) & 1 for qubit in range(logical_ir.n_qubits)]
        for gate in logical_ir.gates:
            if gate.gate_type == "X":
                bits[gate.target] ^= 1
            elif gate.gate_type == "CNOT":
                if bits[gate.controls[0]]:
                    bits[gate.target] ^= 1
            elif all(bits[control] for control in gate.controls):
                bits[gate.target] ^= 1
        expected[sum(bit << qubit for qubit, bit in enumerate(bits)), basis] = 1.0
    return expected


def verify_ion(artifact: dict[str, Any], run_id: str) -> dict[str, bool]:
    metadata_ok = (
        artifact.get("schema_version") == "xa.ion-trap-route-evidence.v1"
        and artifact.get("run_id") == run_id
        and artifact.get("route_id") == "ion_trap"
        and artifact.get("route_kind") == "ideal_resource_adapter"
        and artifact.get("executable") is True
        and artifact.get("hardware_execution") is False
        and artifact.get("native_gate_set") == list(ION_NATIVE_GATE_SET)
        and artifact.get("connectivity") == "fully_connected"
        and artifact.get("routing_swaps_allowed") is False
        and artifact.get("rxx_convention") == RXX_CONVENTION
        and artifact.get("evidence_strength") == ION_EVIDENCE_STRENGTH
        and artifact.get("claim_boundary") == ION_CLAIM_BOUNDARY
    )
    expected_cases = ion_cases()
    rows = artifact.get("cases")
    case_set_ok = (
        isinstance(rows, list)
        and [row.get("case_id") for row in rows if isinstance(row, dict)]
        == [case_id for case_id, _ in expected_cases]
    )
    native_contract = bool(case_set_ok)
    deterministic_recompile = bool(case_set_ok)
    full_basis = bool(case_set_ok)
    unitary_global_phase = bool(case_set_ok)
    if case_set_ok:
        for row, (case_id, logical_ir) in zip(rows, expected_cases):
            if row.get("logical_ir") != logical_record(logical_ir):
                deterministic_recompile = full_basis = unitary_global_phase = False
                continue
            recorded_unitary, valid_native = independent_ion_unitary(row)
            native_contract = native_contract and valid_native
            if recorded_unitary is None:
                full_basis = unitary_global_phase = False
            else:
                expected = expected_logical_unitary(logical_ir)
                for basis in range(expected.shape[0]):
                    output = int(np.argmax(np.abs(expected[:, basis])))
                    if 1.0 - float(abs(recorded_unitary[output, basis]) ** 2) > 1e-9:
                        full_basis = False
                ref_row, ref_column = np.argwhere(np.abs(expected) > 0)[0]
                phase = recorded_unitary[ref_row, ref_column]
                if (
                    abs(abs(phase) - 1.0) > 1e-9
                    or np.max(np.abs(recorded_unitary - phase * expected)) > 1e-9
                ):
                    unitary_global_phase = False
            fresh = compile_ion_trap(logical_ir)
            expected_row = {
                "case_id": case_id,
                "logical_ir": logical_record(logical_ir),
                "native_gates": native_records(fresh.native_gates),
                "diagnostics": normalized(asdict(fresh.diagnostics)),
                "native_qasm3_sha256": sha256_bytes(
                    ion_native_to_openqasm3(fresh).encode("utf-8")
                ),
            }
            for key, value in expected_row.items():
                if row.get(key) != value:
                    deterministic_recompile = False
            equivalence = row.get("equivalence", {})
            if (
                equivalence.get("basis_equivalent") is not True
                or equivalence.get("unitary_equivalent_up_to_global_phase") is not True
                or equivalence.get("tested_basis_states") != 1 << logical_ir.n_qubits
            ):
                deterministic_recompile = False
    return {
        "ion_metadata": metadata_ok,
        "ion_case_set": case_set_ok,
        "ion_native_contract_no_cx_or_swap": native_contract,
        "ion_deterministic_recompile": deterministic_recompile,
        "ion_full_basis_equivalence": full_basis,
        "ion_unitary_up_to_global_phase": unitary_global_phase,
    }


def verify_superconducting(
    artifact: dict[str, Any], run_id: str, seed: int
) -> dict[str, bool]:
    metadata_ok = (
        artifact.get("schema_version")
        == "xa.superconducting-route-evidence.v1"
        and artifact.get("run_id") == run_id
        and artifact.get("route_id") == "superconducting"
        and artifact.get("route_kind") == "synthetic_executable_noisy"
        and artifact.get("executable") is True
        and artifact.get("hardware_execution") is False
        and artifact.get("evidence_strength")
        == SUPERCONDUCTING_EVIDENCE_STRENGTH
        and artifact.get("claim_boundary") == SUPERCONDUCTING_CLAIM_BOUNDARY
    )
    logical_ir = superconducting_logical_ir()
    noise = NoiseParameters(
        model="synthetic-hardware-route-smoke-v1",
        one_qubit_error=0.001,
        two_qubit_error=0.01,
        readout_error=0.02,
    )
    profile = heavy_hex_like_profile(3, noise=noise)
    compilation = compile_superconducting(logical_ir, profile)
    ideal = verify_basis_equivalence(compilation, tolerance=1e-9, max_qubits=3)
    recomputed_ideal = (
        artifact.get("logical_ir") == logical_record(logical_ir)
        and artifact.get("profile") == normalized(asdict(profile))
        and artifact.get("native_gates") == native_records(compilation.native_gates)
        and artifact.get("diagnostics") == normalized(asdict(compilation.diagnostics))
        and artifact.get("basis_equivalence") == normalized(asdict(ideal))
        and artifact.get("native_qasm3_sha256")
        == sha256_bytes(native_to_openqasm3(compilation).encode("utf-8"))
        and ideal.equivalent
    )
    noisy_record = artifact.get("noisy_execution", {})
    recomputed_noisy = False
    if (
        noisy_record.get("logical_input_bits") == [0, 1, 0]
        and noisy_record.get("shots") == 16
        and noisy_record.get("seed") == seed
    ):
        noisy = simulate_noisy_shots(
            compilation,
            (0, 1, 0),
            shots=16,
            seed=seed,
            max_qubits=3,
        )
        recomputed_noisy = noisy_record.get("result") == normalized(asdict(noisy))
    noisy_boundary = bool(
        isinstance(noisy_record.get("result"), dict)
        and noisy_record["result"].get("actual_noisy_simulation") is True
        and noisy_record["result"].get("hardware_execution") is False
        and noisy_record["result"].get("noise_applied") is True
    )
    return {
        "superconducting_metadata": metadata_ok,
        "superconducting_ideal_recomputed": recomputed_ideal,
        "superconducting_noisy_recomputed": recomputed_noisy,
        "superconducting_synthetic_boundary": noisy_boundary,
    }


def verify_photonic(artifact: dict[str, Any], run_id: str) -> dict[str, bool]:
    expected = {**photonic_capability_record(), "run_id": run_id}
    forbidden_execution_keys = {
        "native_gates",
        "compiled_circuit",
        "native_qasm",
        "success_probability",
        "hardware_counts",
    }
    return {
        "photonic_boundary_exact": artifact == expected,
        "photonic_non_executable": artifact.get("executable") is False
        and artifact.get("hardware_execution") is False,
        "photonic_no_fake_mapping": not forbidden_execution_keys.intersection(artifact),
    }


def semantic_verify(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    required = (
        "routes_manifest.json",
        "superconducting.json",
        "ion_trap.json",
        "photonic.json",
    )
    payloads: dict[str, dict[str, Any]] = {}
    parse_ok = True
    for name in required:
        try:
            payload = json.loads((root / name).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("top-level object required")
            payloads[name] = payload
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            parse_ok = False
            errors.append(f"cannot parse {name}: {exc}")
    subject = {
        "routes_manifest_sha256": (
            sha256_file(root / "routes_manifest.json")
            if (root / "routes_manifest.json").is_file()
            else None
        ),
        "route_artifact_sha256": {
            name: sha256_file(root / name) if (root / name).is_file() else None
            for name in ("ion_trap.json", "photonic.json", "superconducting.json")
        },
    }
    checks: dict[str, bool] = {"payloads_parse": parse_ok}
    run_id = "unknown"
    if parse_ok:
        manifest = payloads["routes_manifest.json"]
        run_id = manifest.get("run_id", "unknown")
        seed = manifest.get("seed")
        manifest_schema = (
            manifest.get("schema_version") == "xa.hardware-routes-manifest.v1"
            and manifest.get("competition_id") == "XA-202609"
            and isinstance(run_id, str)
            and bool(run_id)
            and isinstance(seed, int)
            and not isinstance(seed, bool)
            and seed >= 0
            and manifest.get("deterministic") is True
            and manifest.get("hardware_execution") is False
            and manifest.get("rxx_convention") == RXX_CONVENTION
        )
        checks["manifest_schema_and_boundary"] = manifest_schema
        logical_contract = {
            "gate_mode": GATE_MODE,
            "ion_cases": [
                {"case_id": case_id, "logical_ir": logical_record(logical_ir)}
                for case_id, logical_ir in ion_cases()
            ],
            "superconducting_case": logical_record(superconducting_logical_ir()),
        }
        checks["logical_contract_sha"] = manifest.get(
            "logical_contract_sha256"
        ) == sha256_bytes(canonical_json(logical_contract))
        expected_order = ["superconducting", "ion_trap", "photonic"]
        routes = manifest.get("routes")
        route_set = (
            isinstance(routes, list)
            and [row.get("route_id") for row in routes if isinstance(row, dict)]
            == expected_order
        )
        checks["route_set"] = route_set
        artifact_hashes = bool(route_set)
        route_metadata = bool(route_set)
        artifact_by_route = {
            payloads[name].get("route_id"): (name, payloads[name])
            for name in ("superconducting.json", "ion_trap.json", "photonic.json")
        }
        if route_set:
            for row in routes:
                pair = artifact_by_route.get(row["route_id"])
                if pair is None:
                    artifact_hashes = route_metadata = False
                    continue
                name, artifact = pair
                path = root / name
                artifact_hashes = artifact_hashes and (
                    row.get("artifact") == name
                    and row.get("artifact_sha256") == sha256_file(path)
                    and row.get("artifact_size_bytes") == path.stat().st_size
                )
                route_metadata = route_metadata and all(
                    row.get(key) == artifact.get(key)
                    for key in (
                        "route_id",
                        "route_kind",
                        "executable",
                        "hardware_execution",
                        "evidence_strength",
                        "claim_boundary",
                    )
                )
        checks["manifest_artifact_hashes"] = artifact_hashes
        checks["manifest_route_metadata"] = route_metadata
        checks.update(verify_ion(payloads["ion_trap.json"], run_id))
        checks.update(
            verify_superconducting(
                payloads["superconducting.json"], run_id, seed if isinstance(seed, int) else -1
            )
        )
        checks.update(verify_photonic(payloads["photonic.json"], run_id))
        checks["all_routes_hardware_execution_false"] = all(
            payloads[name].get("hardware_execution") is False
            for name in ("superconducting.json", "ion_trap.json", "photonic.json")
        )
    for name, passed in checks.items():
        if not passed:
            errors.append(f"semantic check failed: {name}")
    return {
        "schema_version": SEMANTIC_SCHEMA,
        "run_id": run_id,
        "subject": subject,
        "checks": checks,
        "errors": errors,
        "ok": bool(checks) and all(checks.values()),
    }


def parse_checksums(path: Path) -> tuple[dict[str, str], bool]:
    rows: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows, False
    valid = True
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in rows:
            valid = False
            continue
        rows[match.group(2)] = match.group(1)
    return rows, valid


def verify_bundle(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    semantic = semantic_verify(root)
    errors = list(semantic["errors"])
    actual = {path.name for path in root.iterdir() if path.is_file()} if root.is_dir() else set()
    exact_files = actual == EXPECTED_FILES
    if not exact_files:
        errors.append(f"bundle file set mismatch: {sorted(actual)}")
    checksums, checksum_syntax = parse_checksums(root / "checksums.sha256")
    checksum_coverage = set(checksums) == CHECKSUM_FILES
    checksum_values = checksum_coverage and all(
        (root / name).is_file() and sha256_file(root / name) == digest
        for name, digest in checksums.items()
    )
    if not checksum_syntax:
        errors.append("invalid outer checksum syntax")
    if not checksum_coverage:
        errors.append("outer checksum coverage mismatch")
    if not checksum_values:
        errors.append("outer checksum value mismatch")

    artifact_manifest_ok = False
    try:
        artifact_manifest = json.loads(
            (root / "artifacts.manifest.json").read_text(encoding="utf-8")
        )
        rows = artifact_manifest.get("artifacts", [])
        artifact_manifest_ok = (
            artifact_manifest.get("schema_version")
            == "xa.hardware-routes-artifact-bundle.v1"
            and artifact_manifest.get("run_id") == semantic.get("run_id")
            and {row.get("relative_path") for row in rows} == ARTIFACT_FILES
            and all(
                (root / row["relative_path"]).is_file()
                and row.get("sha256") == sha256_file(root / row["relative_path"])
                and row.get("size_bytes") == (root / row["relative_path"]).stat().st_size
                for row in rows
            )
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        artifact_manifest_ok = False
    if not artifact_manifest_ok:
        errors.append("artifact manifest mismatch")

    recorded_verifier_ok = False
    try:
        recorded = json.loads((root / "verifier.json").read_text(encoding="utf-8"))
        recorded_verifier_ok = recorded == semantic
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        recorded_verifier_ok = False
    if not recorded_verifier_ok:
        errors.append("bundled semantic verifier record mismatch")

    local_path_free = True
    for name in actual:
        data = (root / name).read_bytes()
        if b"/Users/" in data or b"/home/" in data or b"file:///Users/" in data:
            local_path_free = False
    if not local_path_free:
        errors.append("bundle contains a local home path")

    checks = {
        **semantic["checks"],
        "exact_file_set": exact_files,
        "outer_checksum_syntax": checksum_syntax,
        "outer_checksum_coverage": checksum_coverage,
        "outer_checksum_values": checksum_values,
        "artifact_manifest": artifact_manifest_ok,
        "bundled_semantic_verifier_record": recorded_verifier_ok,
        "local_path_privacy": local_path_free,
    }
    return {
        "schema_version": FINAL_SCHEMA,
        "run_id": semantic.get("run_id"),
        "checks": checks,
        "errors": errors,
        "ok": bool(checks) and all(checks.values()),
        "hardware_execution": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--semantic-only", action="store_true")
    command.add_argument("bundle", type=Path)
    return command


def main() -> int:
    args = parser().parse_args()
    result = (
        semantic_verify(args.bundle.expanduser().resolve())
        if args.semantic_only
        else verify_bundle(args.bundle)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
