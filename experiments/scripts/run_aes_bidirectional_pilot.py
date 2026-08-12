#!/usr/bin/env python3
"""Run an auditable AES S-box AI-for-Quantum / Quantum-for-AI pilot.

Each of the eight FIPS 197 AES S-box coordinates is synthesized twice from an
identical learned-policy candidate pool.  A classical diversity-greedy and a
shot-based QAOA scheduler receive the same fixed expansion budget.  The emitted
logical circuit is exhaustively checked as a Boolean oracle, compiled to the
synthetic ``rz/sx/x/cx`` superconducting profile, and exercised with explicit
seeded noisy statevector trajectories on declared sample inputs.

``--tiny`` retains all eight coordinates and both schedulers, but reduces the
search and noisy endpoint to an integration smoke.  Its values are never
performance evidence.  This runner performs no hardware execution and makes no
claim of quantum speedup or quantum advantage.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import multiprocessing
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402

from scripts._pilot_artifacts import (  # noqa: E402
    dataset_sha256,
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
)
from scripts.verify_aes_bidirectional_bundle import verify_aes_bundle  # noqa: E402
from src.anf_utils import anf_monomials  # noqa: E402
from src.benchmarks.crypto_oracles import (  # noqa: E402
    CryptoOracleCoordinate,
    get_crypto_oracle_coordinates,
    reconstruct_substitution_value,
    verify_crypto_oracle_family,
)
from src.contracts.codec import (  # noqa: E402
    canonical_hex,
    canonical_json_bytes,
    sha256_bytes,
)
from src.contracts.experiment import ExperimentManifest  # noqa: E402
from src.contracts.search import PlanTrace  # noqa: E402
from src.factor_plan import (  # noqa: E402
    SearchConfig,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import (  # noqa: E402
    FoundationScorer,
    TermThresholdPolicyScorer,
)
from src.hardware.noise import PauliNoiseModel, simulate_noisy_shots  # noqa: E402
from src.hardware.qasm import export_openqasm3  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    native_to_openqasm3,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.search.mcts_scheduler import (  # noqa: E402
    DiversitySchedulerConfig,
    action_redundancy_matrix,
)
from src.sshr_lib.bool_func import QuantumCircuit  # noqa: E402


RUNNER_SCHEMA = "xa.aes-bidirectional-pilot-runner.v1"
TRIAL_SCHEMA = "xa.aes-bidirectional-coordinate-trial.v1"
SUMMARY_SCHEMA = "xa.aes-bidirectional-pilot-summary.v1"
VERIFIER_SCHEMA = "xa.aes-bidirectional-pilot-verifier.v1"
TRACK = "aes-bidirectional-pilot"
VARIANTS = ("classical_greedy", "qaoa_shot")
EXPECTED_ARTIFACTS = (
    "run.json",
    "raw.jsonl",
    "summary.json",
    "verifier.json",
    "events.jsonl",
    "stdout.log",
    "stderr.log",
    "artifacts.manifest.json",
    "checksums.sha256",
)
PAPER_WEIGHTS = ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)


def _int_literal(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer literal: {value!r}") from exc


def _derived_seed(*parts: object) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _action_signature(action: object) -> dict[str, Any]:
    return {
        "factor": int(getattr(action, "factor")),
        "group": sorted(int(term) for term in getattr(action, "group")),
        "residuals": sorted(int(term) for term in getattr(action, "residuals")),
        "rest": sorted(int(term) for term in getattr(action, "rest")),
        "immediate_gain": float(getattr(action, "immediate_gain")),
        "prior": float(getattr(action, "prior")),
        "linear": bool(getattr(action, "linear", False)),
        "affine_const": bool(getattr(action, "affine_const", False)),
    }


def _scheduler_config(
    args: argparse.Namespace,
    variant: str,
    *,
    scheduler_seed: int,
) -> DiversitySchedulerConfig:
    # E4-v2 prefixes the historical/execution utility arm while retaining the
    # same scheduler suffix.  Exact v1 names still take the identical branch.
    method = "greedy" if variant.endswith("greedy") else "qaoa"
    return DiversitySchedulerConfig(
        method=method,
        budget_requested=args.scheduler_budget,
        pool_size=args.scheduler_pool_size,
        min_candidates=args.scheduler_min_candidates,
        max_depth=0,
        redundancy_weight=args.redundancy_weight,
        redundancy_alpha=args.redundancy_alpha,
        utility_clip=args.utility_clip,
        exact_max_candidates=12,
        seed=scheduler_seed,
        qaoa_mode="shot",
        qaoa_p=args.qaoa_p,
        qaoa_shots=args.qaoa_shots,
        qaoa_noise_bitflip_probability=0.0,
        qaoa_optimizer_restarts=args.qaoa_optimizer_restarts,
        qaoa_optimizer_steps=args.qaoa_optimizer_steps,
    )


def _search_config(args: argparse.Namespace) -> SearchConfig:
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        max_factor_ancilla=args.max_factor_ancilla,
        max_factor_size=args.max_factor_size,
        candidate_top_k=args.candidate_top_k,
        mcts_simulations=args.simulations,
        neural_mcts_simulations=args.simulations,
        gate_mode="mct",
    )


def _pool_payload(
    *,
    coordinate: CryptoOracleCoordinate,
    node_id: str,
    actions: Sequence[object],
    utilities: Sequence[float],
    redundancy: Sequence[Sequence[float]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "schema_version": "xa.aes-bidirectional-pool.v1",
        "family": coordinate.family,
        "output_bit": coordinate.output_bit,
        "truth_table_sha256": coordinate.truth_table_sha256,
        "node_id": node_id,
        "candidate_count": len(actions),
        "budget_requested": args.scheduler_budget,
        "budget_effective": min(args.scheduler_budget, len(actions)),
        "action_signatures": [_action_signature(action) for action in actions],
        "utilities": [float(value) for value in utilities],
        "redundancy": [[float(value) for value in row] for row in redundancy],
        "redundancy_weight": args.redundancy_weight,
        "redundancy_alpha": args.redundancy_alpha,
    }


def _noise_model(args: argparse.Namespace) -> PauliNoiseModel:
    return PauliNoiseModel(
        one_qubit_error=args.one_qubit_error,
        two_qubit_error=args.two_qubit_error,
        readout_error=args.readout_error,
        parameter_source=getattr(
            args,
            "noise_parameter_source",
            "synthetic-heavy-hex-like-dynamic-v1",
        ),
    )


def _verify_reversible_oracle_all_targets(
    circuit: object,
    coordinate: CryptoOracleCoordinate,
) -> bool:
    """Independently check every ``|x,y,0> -> |x,y xor f(x),0>`` basis state."""

    for x in range(1 << coordinate.input_width):
        input_prefix = [
            (x >> bit) & 1 for bit in range(coordinate.input_width)
        ]
        for target_input in (0, 1):
            bits = input_prefix + [target_input]
            bits.extend(0 for _ in range(circuit.n_qubits - len(bits)))
            for gate in circuit.gates:
                if gate.type == "X":
                    bits[gate.target] ^= 1
                elif gate.type == "CNOT":
                    if bits[gate.controls[0]]:
                        bits[gate.target] ^= 1
                elif gate.type == "MCT":
                    if all(bits[control] for control in gate.controls):
                        bits[gate.target] ^= 1
                else:
                    return False
            expected_target = target_input ^ coordinate.evaluate(x)
            if bits[: coordinate.input_width] != input_prefix:
                return False
            if bits[coordinate.input_width] != expected_target:
                return False
            if any(bits[coordinate.input_width + 1 :]):
                return False
    return True


def _native_and_noisy_record(
    *,
    coordinate: CryptoOracleCoordinate,
    circuit: object,
    args: argparse.Namespace,
    run_id: str,
    variant: str,
    coordinates: Sequence[CryptoOracleCoordinate],
    paired_noise_seed_namespace: str | None = None,
    include_audit_payload: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parameters = NoiseParameters(
        model="independent-pauli-depolarizing-v1",
        one_qubit_error=args.one_qubit_error,
        two_qubit_error=args.two_qubit_error,
        readout_error=args.readout_error,
    )
    profile = heavy_hex_like_profile(circuit.n_qubits, noise=parameters)
    profile_payload = {
        "name": profile.name,
        "topology_family": profile.topology_family,
        "n_qubits": profile.n_qubits,
        "coupling_edges": [list(edge) for edge in profile.coupling_edges],
        "native_gate_set": list(profile.native_gate_set),
        "noise": asdict(profile.noise),
        "synthetic": profile.synthetic,
        "calibration_source": profile.calibration_source,
    }
    compilation = compile_superconducting(circuit, profile)
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
    native_qasm = native_to_openqasm3(compilation)
    native = {
        "profile_name": profile.name,
        "profile_sha256": sha256_bytes(canonical_json_bytes(profile_payload)),
        "topology_family": profile.topology_family,
        "n_qubits": profile.n_qubits,
        "coupling_edges": [list(edge) for edge in profile.coupling_edges],
        **asdict(diagnostics),
        "native_gate_set": ["rz", "sx", "x", "cx"],
        "native_gate_set_ok": native_gate_set_ok,
        "coupling_ok": coupling_ok,
        "native_qasm3_sha256": sha256_bytes(native_qasm.encode("utf-8")),
        "native_qasm3_bytes": len(native_qasm.encode("utf-8")),
        "ideal_basis_equivalence": {
            "status": "not_run_scale_bound",
            "reason": (
                "AES pilot uses 9 data/target wires plus up to one factor ancilla; "
                "exhaustive native statevector replay is intentionally replaced by "
                "declared sampled noisy endpoints. Logical oracle semantics remain "
                "exhaustively verified over all 256 inputs and both target values."
            ),
        },
        "hardware_execution": False,
    }
    if include_audit_payload:
        native["native_qasm3"] = native_qasm

    endpoints: list[dict[str, Any]] = []
    model = _noise_model(args)
    for noise_seed_anchor in args.noise_seeds:
        for x in args.endpoint_inputs:
            logical_input = tuple(
                (int(x) >> bit) & 1 for bit in range(coordinate.input_width)
            ) + (0,) + (0,) * (circuit.n_qubits - coordinate.input_width - 1)
            if paired_noise_seed_namespace is None:
                # Preserve the frozen v1 provenance byte-for-byte.
                seed = _derived_seed(
                    "aes-bidirectional-noise-v1",
                    run_id,
                    coordinate.output_bit,
                    variant,
                    x,
                    args.noise_seed_base,
                    noise_seed_anchor,
                )
                seed_contract = "variant-specific-v1"
            else:
                # E4-v2 uses common random numbers.  Neither variant nor run_id
                # enters this namespace, so all four arms in one paired block
                # receive the same trajectory seed.
                seed = _derived_seed(
                    "aes-execution-aware-noise-v2",
                    paired_noise_seed_namespace,
                    coordinate.output_bit,
                    x,
                    args.noise_seed_base,
                    noise_seed_anchor,
                )
                seed_contract = "paired-common-random-numbers-v2"
            result = simulate_noisy_shots(
                compilation,
                logical_input,
                shots=args.endpoint_shots,
                seed=seed,
                noise_model=model,
                max_qubits=10,
            )
            desired = list(logical_input)
            desired[coordinate.input_width] ^= int(coordinate.evaluate(int(x)))
            sbox_output = reconstruct_substitution_value(coordinates, int(x))
            endpoints.append(
                {
                    "input_x": int(x),
                    "input_hex": f"0x{int(x):02x}",
                    "noise_seed_anchor": int(noise_seed_anchor),
                    "output_ancilla_input": 0,
                    "aes_sbox_output": sbox_output,
                    "aes_sbox_output_hex": f"0x{sbox_output:02x}",
                    "coordinate_expected": int(coordinate.evaluate(int(x))),
                    "shots": result.shots,
                    "seed": result.seed,
                    "seed_contract": seed_contract,
                    "paired_noise_seed_namespace": paired_noise_seed_namespace,
                    "success_count": result.success_count,
                    "success_rate": result.success_rate,
                    "counts": result.counts,
                    "expected_bitstring": result.expected_bitstring,
                    "task_contract_ok": tuple(desired) == result.expected_logical_bits,
                    "events": asdict(result.events),
                    "execution_method": result.execution_method,
                    "actual_noisy_simulation": result.actual_noisy_simulation,
                    "hardware_execution": result.hardware_execution,
                    "noise_applied": result.noise_applied,
                    "claim_boundary": result.claim_boundary,
                }
            )
    return native, endpoints


def _trial(
    *,
    coordinate: CryptoOracleCoordinate,
    coordinates: Sequence[CryptoOracleCoordinate],
    variant: str,
    args: argparse.Namespace,
    search_config: SearchConfig,
    checkpoint: Path,
    checkpoint_sha256: str,
    run_id: str,
    execution_utility_adjuster: object | None = None,
    paired_noise_seed_namespace: str | None = None,
    include_audit_payload: bool = False,
    forced_logical_n_qubits: int | None = None,
) -> dict[str, Any]:
    terms = frozenset(anf_monomials(coordinate.boolean_function))
    scheduler_seed = args.scheduler_seed_base + coordinate.output_bit
    scheduler_config = _scheduler_config(
        args,
        variant,
        scheduler_seed=scheduler_seed,
    )
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    policy = TermThresholdPolicyScorer(scorer, args.policy_term_threshold)
    solver = NeuralMCTSSolver(
        config=search_config,
        simulations=args.simulations,
        seed=args.solver_seed,
        neural_scorer=policy,
        value_estimator=None,
        rollout_scorer=None,
        scheduler_config=scheduler_config,
        execution_utility_adjuster=execution_utility_adjuster,
    )
    started = time.perf_counter()
    plan = solver.solve(terms)
    solve_elapsed = time.perf_counter() - started
    root = solver.nodes.get(StateKey(terms, 0, 0))
    if root is None or root.scheduler_decision is None or root.admitted_indices is None:
        raise RuntimeError(
            f"root scheduler was not invoked for AES bit {coordinate.output_bit} / {variant}"
        )
    decision = root.scheduler_decision
    diagnostics = dict(decision.diagnostics)
    pool_width = int(diagnostics["candidate_count"])
    pool_actions = tuple(root.actions[:pool_width])
    # Pool identity is bound only to the pre-intervention utility.  This makes
    # historical/execution arms provably share the same candidate pool even
    # though the scheduler consumes different adjusted utilities.
    raw_utilities = tuple(
        float(value)
        for value in diagnostics.get("raw_utilities", diagnostics["utilities"])
    )
    adjusted_utilities = tuple(
        float(value)
        for value in diagnostics.get("adjusted_utilities", diagnostics["utilities"])
    )
    redundancy = action_redundancy_matrix(
        pool_actions,
        alpha=args.redundancy_alpha,
    )
    pool_payload = _pool_payload(
        coordinate=coordinate,
        node_id=str(diagnostics["node_id"]),
        actions=pool_actions,
        utilities=raw_utilities,
        redundancy=redundancy,
        args=args,
    )
    pool_sha256 = sha256_bytes(canonical_json_bytes(pool_payload))

    plan_check = verify_plan_anf(plan)
    allocated_ancilla = min(
        search_config.max_factor_ancilla,
        plan.cost.explicit_ancilla,
    )
    circuit = emit_plan_to_circuit(plan, coordinate.input_width, allocated_ancilla)
    if forced_logical_n_qubits is not None:
        if (
            isinstance(forced_logical_n_qubits, bool)
            or not isinstance(forced_logical_n_qubits, int)
            or forced_logical_n_qubits < circuit.n_qubits
        ):
            raise ValueError(
                "forced_logical_n_qubits must accommodate the emitted circuit"
            )
        if circuit.n_qubits < forced_logical_n_qubits:
            padded = QuantumCircuit(forced_logical_n_qubits)
            padded.gates = list(circuit.gates)
            circuit = padded
    circuit_check = verify_circuit_anf(circuit, coordinate.input_width, terms)
    oracle_ok = verify_oracle(circuit, coordinate.boolean_function)
    reversible_oracle_ok = _verify_reversible_oracle_all_targets(
        circuit,
        coordinate,
    )
    logical_export = export_openqasm3(circuit)
    native, endpoints = _native_and_noisy_record(
        coordinate=coordinate,
        circuit=circuit,
        args=args,
        run_id=run_id,
        variant=variant,
        coordinates=coordinates,
        paired_noise_seed_namespace=paired_noise_seed_namespace,
        include_audit_payload=include_audit_payload,
    )

    selected = tuple(int(index) for index in decision.selected_indices)
    selected_set = set(selected)
    action_visits = [root.stats[index].visits for index in range(len(root.actions))]
    scheduler_record = {
        "method": scheduler_config.method,
        "qaoa_mode": (
            scheduler_config.qaoa_mode if variant.endswith("qaoa_shot") else None
        ),
        "candidate_count": pool_width,
        "budget_requested": args.scheduler_budget,
        "budget_effective": min(args.scheduler_budget, pool_width),
        "selected_indices": list(selected),
        "selected_action_visits": [action_visits[index] for index in selected],
        "selected_action_visits_total": sum(action_visits[index] for index in selected),
        "excluded_action_visits_total": sum(
            visits for index, visits in enumerate(action_visits) if index not in selected_set
        ),
        "status": diagnostics.get("status"),
        "objective": diagnostics.get("effective_objective", diagnostics.get("objective")),
        "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
        "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
        "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
        "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
        "diagnostics": diagnostics,
    }
    scheduler_summary = solver.scheduler_summary()
    row = {
        "schema_version": TRIAL_SCHEMA,
        "record_type": "aes_coordinate_trial",
        "run_id": run_id,
        "family": coordinate.family,
        "operation": coordinate.operation,
        "output_bit": coordinate.output_bit,
        "input_width": coordinate.input_width,
        "output_width": coordinate.output_width,
        "bit_order": coordinate.bit_order,
        "source": coordinate.source,
        "truth_table_sha256": coordinate.truth_table_sha256,
        "truth_table_hex": canonical_hex(
            int(coordinate.boolean_function.truth_table),
            min_nibbles=64,
        ),
        "anf_term_count": len(terms),
        "variant": variant,
        "solver_seed": args.solver_seed,
        "scheduler_seed": scheduler_seed,
        "simulations": args.simulations,
        "checkpoint_sha256": checkpoint_sha256,
        "learned_policy_active_at_root": len(terms) >= args.policy_term_threshold,
        "learned_value_enabled": False,
        "candidate_pool_sha256": pool_sha256,
        "candidate_pool": pool_payload,
        "raw_scheduler_utilities": list(raw_utilities),
        "adjusted_scheduler_utilities": list(adjusted_utilities),
        "execution_feedback": diagnostics.get("execution_feedback", {}),
        "test_noisy_outcome_used_by_utility": False,
        "scheduler": scheduler_record,
        "logical_resource_score": plan.score(PAPER_WEIGHTS),
        "logical_cost": asdict(plan.cost),
        "logical_gate_count": len(circuit.gates),
        "logical_n_qubits": circuit.n_qubits,
        "allocated_factor_ancilla": allocated_ancilla,
        "plan_anf_ok": plan_check.ok,
        "circuit_anf_ok": circuit_check.ok,
        "oracle_ok": oracle_ok,
        "reversible_oracle_all_targets_ok": reversible_oracle_ok,
        "logical_qasm3_sha256": sha256_bytes(logical_export.qasm.encode("utf-8")),
        "logical_qasm3_metadata": asdict(logical_export.metadata),
        "native": native,
        "noisy_endpoints": endpoints,
        "search_nodes": len(solver.nodes),
        "root_visits": root.visits,
        "scheduler_wall_s": float(scheduler_summary["scheduler_wall_s"]),
        "solve_elapsed_s": solve_elapsed,
        "policy_cache_hits": scorer.cache_hits,
        "policy_cache_misses": scorer.cache_misses,
    }
    if include_audit_payload:
        row["plan_trace"] = PlanTrace.from_plan(plan).to_dict()
        row["logical_circuit_ir"] = {
            "n_qubits": logical_export.logical_ir.n_qubits,
            "gate_mode": logical_export.logical_ir.gate_mode,
            "gates": [
                {
                    "gate_type": gate.gate_type,
                    "controls": list(gate.controls),
                    "target": gate.target,
                }
                for gate in logical_export.logical_ir.gates
            ],
        }
        row["logical_qasm3"] = logical_export.qasm
    return row


def _trial_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Spawn-safe worker for one coordinate/scheduler/noise pipeline."""

    torch.set_num_threads(1)
    args = argparse.Namespace(**payload["args"])
    coordinates = get_crypto_oracle_coordinates("AES")
    coordinate = coordinates[int(payload["output_bit"])]
    started = time.perf_counter()
    row = _trial(
        coordinate=coordinate,
        coordinates=coordinates,
        variant=str(payload["variant"]),
        args=args,
        search_config=_search_config(args),
        checkpoint=Path(payload["checkpoint"]),
        checkpoint_sha256=str(payload["checkpoint_sha256"]),
        run_id=str(payload["run_id"]),
    )
    return {
        "row": row,
        "worker_elapsed_s": time.perf_counter() - started,
    }


def _run_trial_jobs(
    jobs: Sequence[dict[str, Any]],
    *,
    workers: int,
    record_completed: Callable[[dict[str, Any]], None],
) -> str:
    """Run trial jobs, falling back only when the process pool cannot initialize.

    The fallback consumes the original job payloads in their deterministic order.
    Its exception boundary intentionally excludes worker execution so algorithmic
    errors, including ``OSError`` raised by ``_trial_worker``, still propagate.
    """

    if workers == 1:
        for job in jobs:
            record_completed(_trial_worker(job))
        return "in_process"

    try:
        context = multiprocessing.get_context("spawn")
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
        )
    except (PermissionError, OSError) as exc:
        print(
            "execution_mode=in_process_fallback "
            f"process_pool_error={type(exc).__name__}",
            flush=True,
        )
        for job in jobs:
            record_completed(_trial_worker(job))
        return "in_process_fallback"

    with executor:
        future_jobs = {
            executor.submit(_trial_worker, job): job
            for job in jobs
        }
        for future in as_completed(future_jobs):
            job = future_jobs[future]
            try:
                record_completed(future.result())
            except Exception as exc:
                raise RuntimeError(
                    "AES worker failed for output_bit="
                    f"{job['output_bit']} variant={job['variant']}"
                ) from exc
    return "process_pool"


def _summarize(
    *,
    run_id: str,
    rows: Sequence[dict[str, Any]],
    tiny: bool,
    claim_boundary: str,
) -> dict[str, Any]:
    endpoints = [
        endpoint
        for row in rows
        for endpoint in row["noisy_endpoints"]
    ]
    per_trial_shots = [
        sum(endpoint["shots"] for endpoint in row["noisy_endpoints"])
        for row in rows
    ]
    variants: dict[str, Any] = {}
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        variants[variant] = {
            "coordinate_count": len(selected),
            "logical_resource_score_mean": statistics.mean(
                row["logical_resource_score"] for row in selected
            ),
            "logical_gate_count_mean": statistics.mean(
                row["logical_gate_count"] for row in selected
            ),
            "native_gate_count_mean": statistics.mean(
                row["native"]["native_gate_count"] for row in selected
            ),
            "native_two_qubit_gate_count_mean": statistics.mean(
                row["native"]["two_qubit_gate_count"] for row in selected
            ),
            "qaoa_attempted": sum(
                row["scheduler"]["qaoa_attempted"] for row in selected
            ),
            "qaoa_succeeded": sum(
                row["scheduler"]["qaoa_succeeded"] for row in selected
            ),
            "qaoa_repaired": sum(
                row["scheduler"]["qaoa_repaired"] for row in selected
            ),
            "qaoa_fallback": sum(
                row["scheduler"]["qaoa_fallback"] for row in selected
            ),
        }
    return {
        "schema_version": SUMMARY_SCHEMA,
        "run_id": run_id,
        "family": "AES",
        "operation": "SubBytes forward S-box",
        "coordinate_count": 8,
        "trial_count": len(rows),
        "variants": variants,
        "aes_family_full_domain_verified": True,
        "all_plan_anf_ok": all(row["plan_anf_ok"] for row in rows),
        "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in rows),
        "all_oracle_ok": all(row["oracle_ok"] for row in rows),
        "all_reversible_oracle_targets_ok": all(
            row["reversible_oracle_all_targets_ok"] for row in rows
        ),
        "all_native_gate_set_ok": all(
            row["native"]["native_gate_set_ok"] for row in rows
        ),
        "all_coupling_ok": all(row["native"]["coupling_ok"] for row in rows),
        "noisy_endpoint": {
            "endpoint_count": len(endpoints),
            "total_shots": sum(endpoint["shots"] for endpoint in endpoints),
            "success_count": sum(endpoint["success_count"] for endpoint in endpoints),
            "shots_per_trial_min": min(per_trial_shots),
            "shots_per_trial_max": max(per_trial_shots),
            "input_anchors": sorted({endpoint["input_x"] for endpoint in endpoints}),
            "noise_seed_anchors": sorted(
                {endpoint["noise_seed_anchor"] for endpoint in endpoints}
            ),
            "actual_noisy_simulation_all": all(
                endpoint["actual_noisy_simulation"] for endpoint in endpoints
            ),
            "hardware_execution_any": any(
                endpoint["hardware_execution"] for endpoint in endpoints
            ),
            "task_contract_all": all(
                endpoint["task_contract_ok"] for endpoint in endpoints
            ),
        },
        "scope": {
            "tiny": tiny,
            "performance_evidence": False,
            "actual_noisy_simulation": True,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
            "native_equivalence_scope": "not-run-at-aes-scale",
            "native_execution_scope": "sampled-noisy-endpoints",
            "logical_equivalence_scope": "all-256-inputs-and-both-target-values",
            "qaoa_backend": "small-statevector-shot-simulator",
        },
        "claim_boundary": claim_boundary,
    }


def _declared_verifier(
    *,
    run_id: str,
    rows: Sequence[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    expected_matrix = {
        (bit, variant) for bit in range(8) for variant in VARIANTS
    }
    actual_matrix = {(row["output_bit"], row["variant"]) for row in rows}
    pools = {
        bit: {
            row["candidate_pool_sha256"]
            for row in rows
            if row["output_bit"] == bit
        }
        for bit in range(8)
    }
    qaoa = [row for row in rows if row["variant"] == "qaoa_shot"]
    checks = {
        "complete_eight_coordinate_two_variant_matrix": len(rows) == 16
        and actual_matrix == expected_matrix,
        "full_aes_family_verified": summary["aes_family_full_domain_verified"],
        "same_frozen_pool_per_coordinate": all(
            len(pools[bit]) == 1 for bit in range(8)
        ),
        "learned_policy_active_all_roots": all(
            row["learned_policy_active_at_root"] for row in rows
        ),
        "learned_value_explicitly_disabled": all(
            row["learned_value_enabled"] is False for row in rows
        ),
        "fixed_budget_and_independent_edges": all(
            len(row["scheduler"]["selected_indices"])
            == row["scheduler"]["budget_effective"]
            and row["scheduler"]["excluded_action_visits_total"] == 0
            and row["scheduler"]["selected_action_visits_total"]
            == row["simulations"]
            for row in rows
        ),
        "qaoa_attempted_and_accounted": len(qaoa) == 8
        and all(
            row["scheduler"]["qaoa_attempted"]
            and (
                row["scheduler"]["qaoa_succeeded"]
                or row["scheduler"]["qaoa_fallback"]
            )
            for row in qaoa
        ),
        "plan_circuit_oracle_semantics": summary["all_plan_anf_ok"]
        and summary["all_circuit_anf_ok"]
        and summary["all_oracle_ok"]
        and summary["all_reversible_oracle_targets_ok"],
        "native_gate_and_routing_contract": summary["all_native_gate_set_ok"]
        and summary["all_coupling_ok"],
        "actual_noisy_simulation_contract": summary["noisy_endpoint"][
            "actual_noisy_simulation_all"
        ]
        and not summary["noisy_endpoint"]["hardware_execution_any"]
        and summary["noisy_endpoint"]["task_contract_all"],
        "claim_boundary_no_hardware_or_advantage": summary["scope"][
            "hardware_execution"
        ]
        is False
        and summary["scope"]["quantum_advantage_claimed"] is False,
    }
    return {
        "schema_version": VERIFIER_SCHEMA,
        "run_id": run_id,
        "checks": checks,
        "ok": all(checks.values()),
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="models/boolean_oracle_fm_v3.pt")
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--solver-seed", type=int, default=1)
    parser.add_argument("--scheduler-seed-base", type=int, default=202609)
    parser.add_argument("--noise-seed-base", type=int, default=720000)
    parser.add_argument("--noise-seeds", type=int, nargs="+", default=[101, 103])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--simulations", type=int, default=8)
    parser.add_argument("--candidate-top-k", type=int, default=8)
    parser.add_argument("--max-factor-ancilla", type=int, default=1)
    parser.add_argument("--max-factor-size", type=int, default=5)
    parser.add_argument("--policy-term-threshold", type=int, default=96)
    parser.add_argument("--scheduler-pool-size", type=int, default=6)
    parser.add_argument("--scheduler-budget", type=int, default=3)
    parser.add_argument("--scheduler-min-candidates", type=int, default=4)
    parser.add_argument("--redundancy-weight", type=float, default=0.25)
    parser.add_argument("--redundancy-alpha", type=float, default=0.7)
    parser.add_argument("--utility-clip", type=float, default=1.0)
    parser.add_argument("--qaoa-p", type=int, default=1)
    parser.add_argument("--qaoa-shots", type=int, default=128)
    parser.add_argument("--qaoa-optimizer-restarts", type=int, default=4)
    parser.add_argument("--qaoa-optimizer-steps", type=int, default=8)
    parser.add_argument(
        "--endpoint-inputs",
        type=_int_literal,
        nargs="+",
        default=[0x00, 0x53, 0xFF],
    )
    parser.add_argument("--endpoint-shots", type=int, default=2)
    parser.add_argument("--one-qubit-error", type=float, default=0.0002)
    parser.add_argument("--two-qubit-error", type=float, default=0.003)
    parser.add_argument("--readout-error", type=float, default=0.01)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "xa202609",
    )
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def _apply_tiny(args: argparse.Namespace) -> argparse.Namespace:
    if args.tiny:
        args.simulations = 3
        args.qaoa_shots = 16
        args.qaoa_optimizer_restarts = 1
        args.qaoa_optimizer_steps = 1
        args.endpoint_inputs = [0x00]
        args.noise_seeds = [101]
        args.endpoint_shots = 1
    return args


def _validate_args(args: argparse.Namespace) -> None:
    if args.solver_seed < 0 or args.scheduler_seed_base < 0 or args.noise_seed_base < 0:
        raise ValueError("all seeds must be non-negative")
    if args.max_factor_ancilla not in {0, 1}:
        raise ValueError("AES trajectory execution supports max_factor_ancilla 0 or 1")
    positive_names = (
        "simulations",
        "candidate_top_k",
        "max_factor_size",
        "scheduler_pool_size",
        "scheduler_budget",
        "scheduler_min_candidates",
        "qaoa_p",
        "qaoa_shots",
        "qaoa_optimizer_restarts",
        "endpoint_shots",
        "workers",
    )
    for name in positive_names:
        if int(getattr(args, name)) <= 0:
            raise ValueError(f"{name} must be positive")
    if args.qaoa_optimizer_steps < 0:
        raise ValueError("qaoa_optimizer_steps must be non-negative")
    if args.policy_term_threshold < 0:
        raise ValueError("policy_term_threshold must be non-negative")
    if args.simulations < args.scheduler_budget:
        raise ValueError("simulations must cover every selected root edge")
    if args.candidate_top_k < args.scheduler_pool_size:
        raise ValueError("candidate_top_k must be at least scheduler_pool_size")
    if not args.scheduler_budget < args.scheduler_min_candidates <= args.scheduler_pool_size:
        raise ValueError(
            "require scheduler_budget < scheduler_min_candidates <= scheduler_pool_size"
        )
    if args.scheduler_pool_size > 12:
        raise ValueError("statevector QAOA supports scheduler_pool_size <= 12")
    if not 0.0 <= args.redundancy_alpha <= 1.0:
        raise ValueError("redundancy_alpha must be in [0, 1]")
    if args.redundancy_weight < 0.0 or args.utility_clip <= 0.0:
        raise ValueError("redundancy_weight must be non-negative and utility_clip positive")
    probabilities = (
        args.one_qubit_error,
        args.two_qubit_error,
        args.readout_error,
    )
    if any(not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("noise probabilities must lie in [0, 1]")
    if not any(value > 0.0 for value in probabilities):
        raise ValueError("at least one noise probability must be nonzero")
    if not args.endpoint_inputs or len(set(args.endpoint_inputs)) != len(args.endpoint_inputs):
        raise ValueError("endpoint_inputs must be non-empty and unique")
    if any(not 0 <= value < 256 for value in args.endpoint_inputs):
        raise ValueError("AES endpoint inputs must be bytes in [0, 255]")
    if not args.noise_seeds or len(set(args.noise_seeds)) != len(args.noise_seeds):
        raise ValueError("noise_seeds must be non-empty and unique")
    if any(seed < 0 for seed in args.noise_seeds):
        raise ValueError("noise_seeds must be non-negative")
    _scheduler_config(
        args,
        "qaoa_shot",
        scheduler_seed=args.scheduler_seed_base,
    )


def main() -> int:
    args = _apply_tiny(_args())
    _validate_args(args)
    torch.set_num_threads(1)
    checkpoint = Path(args.checkpoint).expanduser()
    if not checkpoint.is_absolute():
        checkpoint = PROJECT_ROOT / checkpoint
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    checkpoint_meta = model_record(checkpoint, PROJECT_ROOT)
    coordinates = get_crypto_oracle_coordinates("AES")
    if len(coordinates) != 8 or not verify_crypto_oracle_family(
        "AES",
        coordinates=coordinates,
    ):
        raise RuntimeError("AES family verification did not close")
    search_config = _search_config(args)
    created_at = utc_now()
    run_id = args.run_id or (
        f"{created_at[:10].replace('-', '')}-{created_at[11:19].replace(':', '')}"
        f"-aes-bidirectional-{'tiny' if args.tiny else 'pilot-v1'}"
    )
    started = time.perf_counter()
    events: list[dict[str, Any]] = [
        {
            "event": "run_started",
            "run_id": run_id,
            "created_at_utc": created_at,
            "tiny": args.tiny,
        }
    ]
    rows: list[dict[str, Any]] = []
    print(
        f"coordinates=8 variants=2 simulations={args.simulations} "
        f"K={args.scheduler_pool_size} B={args.scheduler_budget} "
        f"endpoint_inputs={args.endpoint_inputs} noise_seeds={args.noise_seeds} "
        f"endpoint_shots={args.endpoint_shots} workers={args.workers}",
        flush=True,
    )
    jobs = [
        {
            "args": dict(vars(args)),
            "output_bit": coordinate.output_bit,
            "variant": variant,
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": checkpoint_meta["sha256"],
            "run_id": run_id,
        }
        for coordinate in coordinates
        for variant in VARIANTS
    ]

    def record_completed(result: dict[str, Any]) -> None:
        row = result["row"]
        rows.append(row)
        elapsed = float(result["worker_elapsed_s"])
        events.append(
            {
                "event": "coordinate_trial_completed",
                "output_bit": row["output_bit"],
                "variant": row["variant"],
                "elapsed_s": elapsed,
            }
        )
        print(
            f"bit={row['output_bit']} variant={row['variant']} "
            f"logical_score={row['logical_resource_score']:.3f} "
            f"native_gates={row['native']['native_gate_count']} "
            f"endpoint_success={sum(e['success_count'] for e in row['noisy_endpoints'])}/"
            f"{sum(e['shots'] for e in row['noisy_endpoints'])} elapsed_s={elapsed:.3f}",
            flush=True,
        )

    execution_mode = _run_trial_jobs(
        jobs,
        workers=args.workers,
        record_completed=record_completed,
    )

    rows.sort(key=lambda row: (int(row["output_bit"]), VARIANTS.index(row["variant"])))

    claim_boundary = (
        "All eight FIPS 197 AES S-box scalar coordinates are present and their logical "
        "Boolean-oracle semantics are exhaustively verified. Classical diversity-greedy "
        "and shot-based QAOA scheduling consume the same learned-policy root pool and "
        "fixed edge budget. Native counts and noisy endpoints use a declared synthetic "
        "heavy-hex-like topology and seeded NumPy statevector Pauli trajectories. "
        "Per-trial exhaustive native statevector equivalence is not run at AES scale; "
        "the endpoint uses multiple declared input and noise-seed anchors but remains "
        "sampled and diagnostic. There is no device calibration, real "
        "hardware execution, quantum speedup, or quantum-advantage claim."
    )
    if args.tiny:
        claim_boundary = (
            "--tiny is an execution-contract smoke and its numeric values are not "
            "performance evidence. " + claim_boundary
        )
    summary = _summarize(
        run_id=run_id,
        rows=rows,
        tiny=args.tiny,
        claim_boundary=claim_boundary,
    )
    verifier = _declared_verifier(run_id=run_id, rows=rows, summary=summary)
    elapsed = time.perf_counter() - started
    events.append(
        {
            "event": "run_completed",
            "run_id": run_id,
            "elapsed_s": elapsed,
            "declared_verifier_ok": verifier["ok"],
        }
    )
    dataset = {
        "dataset_id": "aes-fips197-forward-sbox-coordinates-v1",
        "family": "AES",
        "operation": "SubBytes forward S-box",
        "source": coordinates[0].source,
        "bit_order": coordinates[0].bit_order,
        "full_domain_size": 256,
        "coordinates": [
            {
                "output_bit": coordinate.output_bit,
                "truth_table_sha256": coordinate.truth_table_sha256,
                "anf_term_count": len(
                    anf_monomials(coordinate.boolean_function)
                ),
            }
            for coordinate in coordinates
        ],
        "endpoint_inputs": list(args.endpoint_inputs),
        "noise_seed_anchors": list(args.noise_seeds),
    }
    dataset["dataset_sha256"] = dataset_sha256(dataset)
    manifest = ExperimentManifest(
        run_id=run_id,
        track=TRACK,
        experiment="aes-sbox-fixed-budget-scheduler-native-noisy-pilot",
        status="complete" if verifier["ok"] else "failed",
        created_at_utc=created_at,
        source=source_record(PROJECT_ROOT),
        environment=environment_record(),
        command={
            "entrypoint": "scripts/run_aes_bidirectional_pilot.py",
            "tiny": args.tiny,
            "solver_seed": args.solver_seed,
            "scheduler_seed_base": args.scheduler_seed_base,
            "noise_seed_base": args.noise_seed_base,
            "noise_seed_anchors": list(args.noise_seeds),
            "workers": args.workers,
            "execution_mode": execution_mode,
            "endpoint_inputs": list(args.endpoint_inputs),
            "endpoint_shots": args.endpoint_shots,
        },
        dataset=dataset,
        config={
            "runner_schema": RUNNER_SCHEMA,
            "search": asdict(search_config),
            "scheduler_variants": {
                variant: _scheduler_config(
                    args,
                    variant,
                    scheduler_seed=args.scheduler_seed_base,
                ).to_dict()
                for variant in VARIANTS
            },
            "policy_term_threshold": args.policy_term_threshold,
            "noise": asdict(_noise_model(args)),
            "noise_seed_anchors": list(args.noise_seeds),
            "native_profile": "synthetic-heavy-hex-like-dynamic-v1",
            "native_gate_set": ["rz", "sx", "x", "cx"],
            "synthesis_api_boundary": (
                "NeuralMCTSSolver is called directly because synthesize_detailed() "
                "does not expose DiversitySchedulerConfig; Plan emission and all "
                "canonical semantic verifiers are reused without modification."
            ),
        },
        model=checkpoint_meta,
        variants=VARIANTS,
        expected_artifacts=EXPECTED_ARTIFACTS,
        counts={
            "coordinates": 8,
            "trials": len(rows),
            "noisy_endpoints": summary["noisy_endpoint"]["endpoint_count"],
            "noisy_shots": summary["noisy_endpoint"]["total_shots"],
        },
        timing={"wall_s": elapsed},
        claim_boundary=claim_boundary,
    ).to_dict()
    run_dir = args.out_dir.expanduser().resolve() / run_id
    bundle = write_pilot_bundle(
        run_dir=run_dir,
        run_record=manifest,
        raw_records=rows,
        summary=summary,
        verifier=verifier,
        events=events,
        track=TRACK,
    )
    if not bundle.ok:
        raise RuntimeError(f"artifact bundle verification failed: {bundle.errors}")
    independent = verify_aes_bundle(run_dir)
    if not independent["ok"]:
        raise RuntimeError(
            f"independent AES bundle verification failed: {independent['errors']}"
        )
    print(f"bundle={run_dir}")
    print(f"bundle_ok={bundle.ok}")
    print(f"independent_verifier_ok={independent['ok']}")
    print(f"claim_boundary={claim_boundary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
