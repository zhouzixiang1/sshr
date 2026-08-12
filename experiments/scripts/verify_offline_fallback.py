#!/usr/bin/env python3
"""Independently verify the deterministic offline fallback asset."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anf_utils import anf_monomials  # noqa: E402
from src.benchmarks.crypto_oracles import get_crypto_oracle_coordinate  # noqa: E402
from src.factor_plan import (  # noqa: E402
    SearchConfig,
    direct_plan,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.hardware.noise import PauliNoiseModel, simulate_noisy_shots  # noqa: E402
from src.hardware.qasm import export_openqasm3  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    native_to_openqasm3,
)
from src.resource_model import ResourceWeights  # noqa: E402


VERIFIER_SCHEMA = "xa.offline-fallback-verifier.v1"
INPUT_SCHEMA = "xa.offline-fallback-input.v1"
REPORT_SCHEMA = "xa.offline-fallback-report.v1"
MANIFEST_SCHEMA = "xa.offline-fallback-manifest.v1"
EXECUTION_MODE = "in_process_deterministic_fallback"
PAYLOAD_ROLES = {
    "input.json": "input_contract",
    "report.json": "machine_report",
    "report.md": "human_report",
    "execution.log": "execution_log",
    "logical.qasm": "logical_openqasm3",
    "native.qasm": "synthetic_native_openqasm3",
}
CHECKSUM_FILES = set(PAYLOAD_ROLES) | {"fallback_manifest.json"}
REQUIRED_FILES = CHECKSUM_FILES | {"checksums.sha256"}
PAPER_WEIGHTS = ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)
NOISE_PARAMETERS = NoiseParameters(
    model="independent-pauli-depolarizing-v1",
    one_qubit_error=0.0002,
    two_qubit_error=0.003,
    readout_error=0.01,
)
NOISE_MODEL = PauliNoiseModel(
    one_qubit_error=0.0002,
    two_qubit_error=0.003,
    readout_error=0.01,
    parameter_source="offline-deterministic-fallback-v1",
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root)
    if not path.is_file():
        raise FileNotFoundError(relative)
    return path


def _check_outer_checksums(root: Path) -> bool:
    try:
        seen: set[str] = set()
        for line in (root / "checksums.sha256").read_text(
            encoding="utf-8"
        ).splitlines():
            expected, relative = line.split("  ", 1)
            if relative in seen:
                return False
            seen.add(relative)
            if _sha256(_safe_file(root, relative)) != expected:
                return False
        return seen == CHECKSUM_FILES
    except Exception:
        return False


def _check_manifest(root: Path, manifest: dict[str, Any]) -> bool:
    try:
        records = manifest["files"]
        if not isinstance(records, list) or len(records) != len(PAYLOAD_ROLES):
            return False
        seen: set[str] = set()
        for item in records:
            relative = item["relative_path"]
            if relative in seen or PAYLOAD_ROLES.get(relative) != item["role"]:
                return False
            seen.add(relative)
            path = _safe_file(root, relative)
            if _sha256(path) != item["sha256"] or path.stat().st_size != item[
                "size_bytes"
            ]:
                return False
        return seen == set(PAYLOAD_ROLES)
    except Exception:
        return False


def _fallback_config() -> SearchConfig:
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        max_factor_ancilla=0,
        max_factor_size=1,
        candidate_top_k=1,
        min_factor_count=2,
        use_relative_phase=True,
        mcts_simulations=1,
        neural_mcts_simulations=1,
        max_polarities=1,
        gate_mode="mct",
        neural_prior_weight=0.0,
        greedy_eval_limit=1,
    )


def _reversible_oracle_ok(circuit: object, coordinate: object) -> bool:
    input_width = int(getattr(coordinate, "input_width"))
    for x in range(1 << input_width):
        input_prefix = [(x >> bit) & 1 for bit in range(input_width)]
        expected_coordinate = int(getattr(coordinate, "evaluate")(x))
        for target_input in (0, 1):
            initial = input_prefix + [target_input]
            initial.extend([0] * (int(getattr(circuit, "n_qubits")) - len(initial)))
            observed = getattr(circuit, "simulate")(initial)
            if observed[:input_width] != input_prefix:
                return False
            if observed[input_width] != (target_input ^ expected_coordinate):
                return False
            if any(observed[input_width + 1 :]):
                return False
    return True


def _input_contract(record: dict[str, Any]) -> bool:
    try:
        expected = {
            "schema_version": INPUT_SCHEMA,
            "case": "aes_sbox_bit0",
            "output_bit": 0,
            "synthesizer": "direct_anf",
            "scheduler": "none",
            "hardware": "synthetic_superconducting_noise",
            "seed": record["seed"],
            "input_x": record["input_x"],
            "shots": record["shots"],
            "fallback_only": True,
            "learned_policy_enabled": False,
            "learned_value_enabled": False,
            "qaoa_enabled": False,
        }
        return (
            record == expected
            and isinstance(record["seed"], int)
            and not isinstance(record["seed"], bool)
            and 0 <= record["seed"] < 2**64
            and isinstance(record["input_x"], int)
            and not isinstance(record["input_x"], bool)
            and 0 <= record["input_x"] < 256
            and isinstance(record["shots"], int)
            and not isinstance(record["shots"], bool)
            and 1 <= record["shots"] <= 32
        )
    except Exception:
        return False


def _recomputed_checks(
    root: Path,
    input_record: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, bool]:
    coordinate = get_crypto_oracle_coordinate("AES", 0)
    terms = frozenset(anf_monomials(coordinate.boolean_function))
    plan = direct_plan(terms, 0, 0, _fallback_config())
    circuit = emit_plan_to_circuit(plan, coordinate.input_width, 0)
    plan_check = verify_plan_anf(plan)
    circuit_check = verify_circuit_anf(circuit, coordinate.input_width, terms)
    oracle_ok = verify_oracle(circuit, coordinate.boolean_function)
    reversible_ok = _reversible_oracle_ok(circuit, coordinate)
    logical_qasm = export_openqasm3(circuit).qasm

    profile = heavy_hex_like_profile(circuit.n_qubits, noise=NOISE_PARAMETERS)
    compilation = compile_superconducting(circuit, profile)
    native_qasm = native_to_openqasm3(compilation)
    diagnostics = compilation.diagnostics
    native_gate_set_ok = all(
        gate.name in {"rz", "sx", "x", "cx"}
        for gate in compilation.native_gates
    )
    coupling_ok = all(
        tuple(sorted(gate.qubits)) in profile.coupling_edges
        for gate in compilation.native_gates
        if gate.name == "cx"
    )
    logical_input = tuple(
        (input_record["input_x"] >> bit) & 1
        for bit in range(coordinate.input_width)
    ) + (0,)
    noisy = simulate_noisy_shots(
        compilation,
        logical_input,
        shots=input_record["shots"],
        seed=input_record["seed"],
        noise_model=NOISE_MODEL,
        max_qubits=10,
    )
    logical = report.get("logical", {})
    native = report.get("native_and_noise", {})
    return {
        "logical_semantics_recomputed": bool(
            plan_check.ok
            and circuit_check.ok
            and oracle_ok
            and reversible_ok
            and logical.get("plan_anf_ok") is True
            and logical.get("circuit_anf_ok") is True
            and logical.get("oracle_ok") is True
            and logical.get("reversible_oracle_all_targets_ok") is True
            and logical.get("semantic_checks_all") is True
        ),
        "logical_record_recomputed": logical
        == {
            "truth_table_sha256": coordinate.truth_table_sha256,
            "input_width": coordinate.input_width,
            "n_qubits": circuit.n_qubits,
            "anf_term_count": len(terms),
            "logical_gate_count": len(circuit.gates),
            "resource_cost": asdict(plan.cost),
            "resource_score": plan.score(PAPER_WEIGHTS),
            "plan_anf_ok": True,
            "circuit_anf_ok": True,
            "oracle_ok": True,
            "reversible_oracle_all_targets_ok": True,
            "semantic_checks_all": True,
            "logical_qasm3_sha256": _sha256(root / "logical.qasm"),
        },
        "logical_qasm_recomputed": (root / "logical.qasm").read_text(
            encoding="utf-8"
        )
        == logical_qasm,
        "native_mapping_recomputed": bool(
            native_gate_set_ok
            and coupling_ok
            and native.get("profile") == profile.name
            and native.get("profile_synthetic") is True
            and native.get("native_gate_set") == list(profile.native_gate_set)
            and native.get("native_gate_set_ok") is True
            and native.get("coupling_ok") is True
            and native.get("native_gate_count") == diagnostics.native_gate_count
            and native.get("native_two_qubit_gate_count")
            == diagnostics.two_qubit_gate_count
            and native.get("native_depth") == diagnostics.native_depth
            and native.get("inserted_swap_count")
            == diagnostics.inserted_swap_count
            and native.get("native_equivalence_scope")
            == "not-run-at-aes-scale"
        ),
        "native_qasm_recomputed": (root / "native.qasm").read_text(
            encoding="utf-8"
        )
        == native_qasm
        and native.get("native_qasm3_sha256") == _sha256(root / "native.qasm"),
        "noisy_execution_recomputed": bool(
            native.get("input_x") == input_record["input_x"]
            and native.get("input_hex") == f"0x{input_record['input_x']:02x}"
            and native.get("expected_coordinate")
            == int(coordinate.evaluate(input_record["input_x"]))
            and native.get("shots") == noisy.shots
            and native.get("seed") == noisy.seed
            and native.get("success_count") == noisy.success_count
            and native.get("success_rate") == noisy.success_rate
            and native.get("counts") == noisy.counts
            and native.get("expected_bitstring") == noisy.expected_bitstring
            and native.get("noise_model") == asdict(noisy.noise_model)
            and native.get("noise_events") == asdict(noisy.events)
            and native.get("execution_method") == noisy.execution_method
            and native.get("actual_noisy_simulation") is True
            and native.get("noise_applied") is True
            and native.get("hardware_execution") is False
        ),
    }


def verify_offline_fallback(output: str | Path) -> dict[str, Any]:
    root = Path(output).expanduser().resolve()
    if not root.is_dir():
        return {
            "schema_version": VERIFIER_SCHEMA,
            "ok": False,
            "checks": {},
            "errors": [f"not a directory: {root}"],
        }
    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    if missing:
        return {
            "schema_version": VERIFIER_SCHEMA,
            "ok": False,
            "checks": {"required_files": False},
            "errors": [f"missing files: {missing}"],
        }
    try:
        input_record = _json(root / "input.json")
        report = _json(root / "report.json")
        manifest = _json(root / "fallback_manifest.json")
        report_markdown = (root / "report.md").read_text(encoding="utf-8")
        execution_log = (root / "execution.log").read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "schema_version": VERIFIER_SCHEMA,
            "ok": False,
            "checks": {},
            "errors": [f"read/parse failure: {exc}"],
        }

    checks = {
        "required_files": True,
        "outer_checksums": _check_outer_checksums(root),
        "manifest_file_hashes": _check_manifest(root, manifest),
        "manifest_scope_separated": manifest
        == {
            "schema_version": MANIFEST_SCHEMA,
            "artifact_kind": "offline_deterministic_fallback",
            "fallback_only": True,
            "learned_policy_invoked": False,
            "learned_value_invoked": False,
            "qaoa_invoked": False,
            "performance_evidence": False,
            "hardware_execution": False,
            "files": manifest.get("files"),
        },
        "input_contract": _input_contract(input_record),
        "fallback_scope_report": bool(
            report.get("schema_version") == REPORT_SCHEMA
            and report.get("case") == "aes_sbox_bit0"
            and report.get("output_bit") == 0
            and report.get("execution")
            == {
                "execution_mode": EXECUTION_MODE,
                "fallback_only": True,
                "synthesizer": "direct_anf",
                "scheduler": "none",
                "deterministic": True,
                "seed": input_record.get("seed"),
                "learned_policy_invoked": False,
                "learned_value_invoked": False,
                "qaoa_invoked": False,
            }
            and report.get("scope")
            == {
                "fallback_only": True,
                "learned_policy_invoked": False,
                "learned_value_invoked": False,
                "qaoa_invoked": False,
                "performance_evidence": False,
                "hardware_execution": False,
                "quantum_advantage_claimed": False,
            }
            and "quantum_for_ai" not in report
            and "not performance evidence" in report.get("claim_boundary", "")
        ),
        "human_report_scope_separated": all(
            marker in report_markdown
            for marker in (
                "非 QAOA 成绩",
                "fallback_only=true",
                "qaoa_invoked=false",
                "performance_evidence=false",
                "hardware_execution=false",
            )
        ),
        "execution_log_scope_separated": all(
            marker in execution_log
            for marker in (
                f"execution_mode={EXECUTION_MODE}",
                "fallback_only=true",
                "synthesizer=direct_anf",
                "learned_policy_invoked=false",
                "qaoa_invoked=false",
                "performance_evidence=false",
                "hardware_execution=false",
            )
        ),
    }
    integrity_ready = all(
        checks[name]
        for name in (
            "outer_checksums",
            "manifest_file_hashes",
            "manifest_scope_separated",
            "input_contract",
            "fallback_scope_report",
        )
    )
    if integrity_ready:
        try:
            checks.update(_recomputed_checks(root, input_record, report))
        except Exception:
            checks.update(
                {
                    "logical_semantics_recomputed": False,
                    "logical_record_recomputed": False,
                    "logical_qasm_recomputed": False,
                    "native_mapping_recomputed": False,
                    "native_qasm_recomputed": False,
                    "noisy_execution_recomputed": False,
                }
            )
    else:
        checks.update(
            {
                "logical_semantics_recomputed": False,
                "logical_record_recomputed": False,
                "logical_qasm_recomputed": False,
                "native_mapping_recomputed": False,
                "native_qasm_recomputed": False,
                "noisy_execution_recomputed": False,
            }
        )
    errors = [f"check failed: {name}" for name, passed in checks.items() if not passed]
    return {
        "schema_version": VERIFIER_SCHEMA,
        "ok": not errors,
        "checks": checks,
        "errors": errors,
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _args()
    result = verify_offline_fallback(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
