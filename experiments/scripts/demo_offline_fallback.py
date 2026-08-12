#!/usr/bin/env python3
"""Build the independent deterministic offline fallback demonstration asset.

This path deliberately excludes learned policy/value models and every QAOA
scheduler.  It emits the AES S-box output-bit-0 Oracle with the deterministic
direct ANF baseline, verifies its logical semantics, maps it to the declared
synthetic superconducting profile, and runs one seeded noisy trajectory smoke.
The resulting numbers are availability evidence only, never AI-for-Quantum or
Quantum-for-AI performance evidence.
"""

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

from scripts.verify_offline_fallback import verify_offline_fallback  # noqa: E402
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


INPUT_SCHEMA = "xa.offline-fallback-input.v1"
REPORT_SCHEMA = "xa.offline-fallback-report.v1"
MANIFEST_SCHEMA = "xa.offline-fallback-manifest.v1"
EXECUTION_MODE = "in_process_deterministic_fallback"
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
PAYLOAD_FILES = (
    ("input.json", "input_contract"),
    ("report.json", "machine_report"),
    ("report.md", "human_report"),
    ("execution.log", "execution_log"),
    ("logical.qasm", "logical_openqasm3"),
    ("native.qasm", "synthetic_native_openqasm3"),
)


def _int_literal(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer literal: {value!r}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


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


def _report_markdown(report: dict[str, Any]) -> str:
    logical = report["logical"]
    native = report["native_and_noise"]
    return f"""# XA-202609 离线确定性兜底（非 QAOA 成绩）

本资产只用于在 learned model 或 QAOA 路径不可用时维持可验证演示。它采用
`direct_anf`，不加载 learned policy/value，不调用 scheduler 或 QAOA。

- `fallback_only=true`
- `learned_policy_invoked=false`
- `qaoa_invoked=false`
- `performance_evidence=false`
- `hardware_execution=false`

## 逻辑语义

- AES S-box output bit 0，ANF 项数 `{logical['anf_term_count']}`，逻辑门数
  `{logical['logical_gate_count']}`。
- Plan ANF、Circuit ANF、完整 256 输入 Oracle 与 `256 × 2` 可逆语义检查：
  `{'全部通过' if logical['semantic_checks_all'] else '未通过'}`。
- 逻辑 QASM SHA-256：`{logical['logical_qasm3_sha256']}`。

## Synthetic native/noise 小例

- profile：`{native['profile']}`；原生总门 `{native['native_gate_count']}`，双比特门
  `{native['native_two_qubit_gate_count']}`，coupling 检查
  `{'通过' if native['coupling_ok'] else '未通过'}`。
- 固定输入 `{native['input_hex']}`、seed `{native['seed']}`、
  `{native['success_count']}/{native['shots']}` sampled success。

## 边界

该 sampled endpoint 仅验证离线软件链可执行。它不是 AI for Quantum 或
Quantum for AI 成绩，不是真机或真实校准证据，也不支持性能、加速或量子优势主张。
"""


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("aes_sbox_bit0",), required=True)
    parser.add_argument("--synthesizer", choices=("direct_anf",), required=True)
    parser.add_argument("--scheduler", choices=("none",), required=True)
    parser.add_argument(
        "--hardware", choices=("synthetic_superconducting_noise",), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=940000)
    parser.add_argument("--input-x", type=_int_literal, default=0x53)
    parser.add_argument("--shots", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = _args()
    if not 0 <= args.seed < 2**64:
        raise ValueError("seed must be in [0, 2**64)")
    if not 0 <= args.input_x < 256:
        raise ValueError("input-x must be a byte in [0, 255]")
    if not 1 <= args.shots <= 32:
        raise ValueError("shots must be in [1, 32]")
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(
            f"offline fallback output must be empty: {output}"
        )
    output.mkdir(parents=True, exist_ok=True)

    input_record = {
        "schema_version": INPUT_SCHEMA,
        "case": args.case,
        "output_bit": 0,
        "synthesizer": args.synthesizer,
        "scheduler": args.scheduler,
        "hardware": args.hardware,
        "seed": args.seed,
        "input_x": args.input_x,
        "shots": args.shots,
        "fallback_only": True,
        "learned_policy_enabled": False,
        "learned_value_enabled": False,
        "qaoa_enabled": False,
    }
    _write_json(output / "input.json", input_record)

    coordinate = get_crypto_oracle_coordinate("AES", 0)
    terms = frozenset(anf_monomials(coordinate.boolean_function))
    config = _fallback_config()
    plan = direct_plan(terms, 0, 0, config)
    circuit = emit_plan_to_circuit(plan, coordinate.input_width, 0)
    plan_check = verify_plan_anf(plan)
    circuit_check = verify_circuit_anf(circuit, coordinate.input_width, terms)
    oracle_ok = verify_oracle(circuit, coordinate.boolean_function)
    reversible_ok = _reversible_oracle_ok(circuit, coordinate)
    logical_export = export_openqasm3(circuit)
    (output / "logical.qasm").write_text(logical_export.qasm, encoding="utf-8")

    profile = heavy_hex_like_profile(circuit.n_qubits, noise=NOISE_PARAMETERS)
    compilation = compile_superconducting(circuit, profile)
    native_qasm = native_to_openqasm3(compilation)
    (output / "native.qasm").write_text(native_qasm, encoding="utf-8")
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
        (args.input_x >> bit) & 1 for bit in range(coordinate.input_width)
    ) + (0,)
    noisy = simulate_noisy_shots(
        compilation,
        logical_input,
        shots=args.shots,
        seed=args.seed,
        noise_model=NOISE_MODEL,
        max_qubits=10,
    )
    diagnostics = compilation.diagnostics
    semantic_checks_all = bool(
        plan_check.ok and circuit_check.ok and oracle_ok and reversible_ok
    )
    report = {
        "schema_version": REPORT_SCHEMA,
        "case": args.case,
        "output_bit": 0,
        "execution": {
            "execution_mode": EXECUTION_MODE,
            "fallback_only": True,
            "synthesizer": "direct_anf",
            "scheduler": "none",
            "deterministic": True,
            "seed": args.seed,
            "learned_policy_invoked": False,
            "learned_value_invoked": False,
            "qaoa_invoked": False,
        },
        "logical": {
            "truth_table_sha256": coordinate.truth_table_sha256,
            "input_width": coordinate.input_width,
            "n_qubits": circuit.n_qubits,
            "anf_term_count": len(terms),
            "logical_gate_count": len(circuit.gates),
            "resource_cost": asdict(plan.cost),
            "resource_score": plan.score(PAPER_WEIGHTS),
            "plan_anf_ok": bool(plan_check.ok),
            "circuit_anf_ok": bool(circuit_check.ok),
            "oracle_ok": bool(oracle_ok),
            "reversible_oracle_all_targets_ok": bool(reversible_ok),
            "semantic_checks_all": semantic_checks_all,
            "logical_qasm3_sha256": _sha256(output / "logical.qasm"),
        },
        "native_and_noise": {
            "profile": profile.name,
            "profile_synthetic": profile.synthetic,
            "native_gate_set": list(profile.native_gate_set),
            "native_gate_set_ok": native_gate_set_ok,
            "coupling_ok": coupling_ok,
            "native_gate_count": diagnostics.native_gate_count,
            "native_two_qubit_gate_count": diagnostics.two_qubit_gate_count,
            "native_depth": diagnostics.native_depth,
            "inserted_swap_count": diagnostics.inserted_swap_count,
            "native_qasm3_sha256": _sha256(output / "native.qasm"),
            "native_equivalence_scope": "not-run-at-aes-scale",
            "input_x": args.input_x,
            "input_hex": f"0x{args.input_x:02x}",
            "expected_coordinate": int(coordinate.evaluate(args.input_x)),
            "shots": noisy.shots,
            "seed": noisy.seed,
            "success_count": noisy.success_count,
            "success_rate": noisy.success_rate,
            "counts": noisy.counts,
            "expected_bitstring": noisy.expected_bitstring,
            "noise_model": asdict(noisy.noise_model),
            "noise_events": asdict(noisy.events),
            "execution_method": noisy.execution_method,
            "actual_noisy_simulation": noisy.actual_noisy_simulation,
            "noise_applied": noisy.noise_applied,
            "hardware_execution": False,
        },
        "scope": {
            "fallback_only": True,
            "learned_policy_invoked": False,
            "learned_value_invoked": False,
            "qaoa_invoked": False,
            "performance_evidence": False,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
        "claim_boundary": (
            "Fallback-only deterministic availability evidence. This direct-ANF "
            "path does not invoke learned policy/value or QAOA and must not be "
            "reported as AI-for-Quantum or Quantum-for-AI performance. The native "
            "and noisy endpoint uses a seeded synthetic profile, not hardware or "
            "device calibration; it is not performance evidence."
        ),
    }
    _write_json(output / "report.json", report)
    (output / "report.md").write_text(_report_markdown(report), encoding="utf-8")
    (output / "execution.log").write_text(
        "\n".join(
            (
                "entrypoint=experiments/scripts/demo_offline_fallback.py",
                f"execution_mode={EXECUTION_MODE}",
                "fallback_only=true",
                "synthesizer=direct_anf",
                "learned_policy_invoked=false",
                "learned_value_invoked=false",
                "qaoa_invoked=false",
                f"seed={args.seed}",
                f"input_x=0x{args.input_x:02x}",
                f"shots={args.shots}",
                f"semantic_checks_all={str(semantic_checks_all).lower()}",
                f"native_gate_set_ok={str(native_gate_set_ok).lower()}",
                f"coupling_ok={str(coupling_ok).lower()}",
                "performance_evidence=false",
                "hardware_execution=false",
                "",
            )
        ),
        encoding="utf-8",
    )

    manifest_files = [
        {
            "relative_path": name,
            "role": role,
            "sha256": _sha256(output / name),
            "size_bytes": (output / name).stat().st_size,
        }
        for name, role in PAYLOAD_FILES
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "artifact_kind": "offline_deterministic_fallback",
        "fallback_only": True,
        "learned_policy_invoked": False,
        "learned_value_invoked": False,
        "qaoa_invoked": False,
        "performance_evidence": False,
        "hardware_execution": False,
        "files": manifest_files,
    }
    _write_json(output / "fallback_manifest.json", manifest)
    checksum_names = [name for name, _ in PAYLOAD_FILES] + [
        "fallback_manifest.json"
    ]
    (output / "checksums.sha256").write_text(
        "".join(f"{_sha256(output / name)}  {name}\n" for name in checksum_names),
        encoding="utf-8",
    )

    verification = verify_offline_fallback(output)
    _write_json(output / "verification.json", verification)
    if not verification["ok"]:
        raise RuntimeError(
            f"offline fallback verification failed: {verification['errors']}"
        )
    print(f"offline_fallback_output={output}")
    print("fallback_only=true")
    print("learned_policy_invoked=false")
    print("qaoa_invoked=false")
    print("performance_evidence=false")
    print("hardware_execution=false")
    print("verification_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
