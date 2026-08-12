#!/usr/bin/env python3
"""Run the E4-v2 calibration-frozen AES execution-aware evaluation.

``calibrate`` measures noisy rollout completions only on deterministic non-AES
8-input Boolean functions, selects a structural ridge model and non-negative
native-resource penalty, and freezes every input by SHA-256.  ``test`` loads
that artifact without fitting and evaluates four paired scheduler arms on all
eight held-out FIPS 197 AES S-box coordinates.

All native and noisy data use a declared synthetic profile.  Tiny mode is an
artifact/contract smoke and is never performance evidence.
"""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from scripts._pilot_artifacts import (  # noqa: E402
    dataset_sha256,
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
)
from scripts.run_aes_bidirectional_pilot import (  # noqa: E402
    EXPECTED_ARTIFACTS,
    PAPER_WEIGHTS,
    _action_signature,
    _search_config as _legacy_search_config,
    _trial as _aes_trial,
)
from src.anf_utils import anf_monomials  # noqa: E402
from src.benchmarks.crypto_oracles import (  # noqa: E402
    get_crypto_oracle_coordinates,
    verify_crypto_oracle_family,
)
from src.contracts.codec import (  # noqa: E402
    canonical_hex,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from src.contracts.experiment import ExperimentManifest  # noqa: E402
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
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.search.diversity_scheduler import (  # noqa: E402
    schedule_diverse_candidates,
    selection_objective,
)
from src.search.execution_aware_utility import (  # noqa: E402
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    complete_root_action_rollout,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.execution_feedback import (  # noqa: E402
    ExecutionCalibrationRecord,
    RidgeExecutionCostModel,
)
from src.search.mcts_scheduler import action_redundancy_matrix  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


CONFIG_SCHEMA = "xa.e4-execution-aware-config.v2"
CALIBRATION_SCHEMA = "xa.e4-execution-aware-calibration.v2"
TEST_SCHEMA = "xa.e4-execution-aware-test.v2"
VERIFIER_SCHEMA = "xa.e4-execution-aware-verifier.v2"
PRIMARY_METRIC_SCHEMA = "balanced-oracle-contract-metric-v1"
TRACK = "xa202609/e4-execution-aware-v2"
VARIANTS = (
    "historical_greedy",
    "execution_greedy",
    "historical_qaoa_shot",
    "execution_qaoa_shot",
)
RESOURCE_COMPONENTS = (
    "native_one_qubit",
    "native_two_qubit",
    "inserted_swap",
    "native_depth",
    "duration_ns",
    "model_risk",
)


def _sha_payload(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _config_sha256(config: Mapping[str, Any]) -> str:
    return _sha_payload(config)


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _probability(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a probability")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must lie in [0, 1]")
    return result


def load_config(path: str | Path, *, tiny: bool = False) -> dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "experiment",
        "checkpoint",
        "calibration",
        "test",
        "search",
        "qaoa",
        "native_profile",
        "primary_metric",
        "weight_selection",
        "statistics",
        "claim_boundary",
    }
    if config.get("schema_version") != CONFIG_SCHEMA or set(config) != required:
        raise ValueError("unsupported or malformed E4-v2 config")
    config = copy.deepcopy(config)
    if tiny:
        config["calibration"].update(
            case_count=1,
            input_anchors=[0],
            shots_per_input=1,
            noise_seeds=[101],
        )
        config["test"].update(
            solver_seeds=[1],
            input_anchors=[0],
            shots_per_input=1,
            noise_seeds=[101],
        )
        config["search"].update(
            simulations=3,
            candidate_top_k=4,
            scheduler_pool_size=4,
            scheduler_min_candidates=4,
        )
        config["qaoa"].update(shots=16, optimizer_restarts=1, optimizer_steps=1)
        config["weight_selection"]["lambda_grid"] = [0.0, 0.1]
        config["statistics"]["bootstrap_resamples"] = 200

    calibration = config["calibration"]
    test = config["test"]
    search = config["search"]
    qaoa = config["qaoa"]
    profile = config["native_profile"]
    primary_metric = config["primary_metric"]
    if _positive_int(calibration["n"], "calibration.n") != 8:
        raise ValueError("E4-v2 calibration must be scale-matched at n=8")
    for name in ("case_count", "seed_base", "shots_per_input"):
        _positive_int(calibration[name], f"calibration.{name}")
    for name in ("simulations", "candidate_top_k", "max_factor_size",
                 "scheduler_pool_size", "scheduler_budget",
                 "scheduler_min_candidates"):
        _positive_int(search[name], f"search.{name}")
    if search["max_factor_ancilla"] not in (0, 1):
        raise ValueError("AES trajectories support at most one factor ancilla")
    if search["simulations"] < search["scheduler_budget"]:
        raise ValueError("simulations must cover the selected root budget")
    if search["candidate_top_k"] < search["scheduler_pool_size"]:
        raise ValueError("candidate_top_k must cover scheduler_pool_size")
    if not (
        search["scheduler_budget"] < search["scheduler_min_candidates"]
        <= search["scheduler_pool_size"] <= 12
    ):
        raise ValueError("invalid QAOA pool/budget/min-candidate relation")
    if sorted(test["coordinates"]) != list(range(8)):
        raise ValueError("held-out test must retain all eight AES coordinates")
    for section_name, section in (("calibration", calibration), ("test", test)):
        anchors = section["input_anchors"]
        seeds = section["noise_seeds"]
        if not anchors or len(set(anchors)) != len(anchors) or any(
            not isinstance(value, int) or not 0 <= value < 256 for value in anchors
        ):
            raise ValueError(f"{section_name}.input_anchors must be unique bytes")
        if not seeds or len(set(seeds)) != len(seeds) or any(
            not isinstance(value, int) or value < 0 for value in seeds
        ):
            raise ValueError(f"{section_name}.noise_seeds must be unique nonnegative ints")
    if not test["solver_seeds"] or len(set(test["solver_seeds"])) != len(
        test["solver_seeds"]
    ):
        raise ValueError("test.solver_seeds must be non-empty and unique")
    for name in ("p", "shots", "optimizer_restarts"):
        _positive_int(qaoa[name], f"qaoa.{name}")
    if not isinstance(qaoa["optimizer_steps"], int) or qaoa["optimizer_steps"] < 0:
        raise ValueError("qaoa.optimizer_steps must be nonnegative")
    for name in ("one_qubit_error", "two_qubit_error", "readout_error"):
        _probability(profile[name], f"native_profile.{name}")
    if primary_metric.get("schema") != PRIMARY_METRIC_SCHEMA:
        raise ValueError("unsupported E4-v2 primary_metric schema")
    if primary_metric.get("source") != "NoisyExecutionResult.counts":
        raise ValueError("primary_metric must be recomputed from trajectory counts")
    if primary_metric.get("component_weighting") != "equal-over-three-components":
        raise ValueError("primary_metric components must have equal weight")
    if primary_metric.get("secondary_metric") != "exact-full-state-jeffreys-nll":
        raise ValueError("exact full-state NLL must remain the secondary metric")
    mixtures = config["weight_selection"]["component_mixtures"]
    if not mixtures:
        raise ValueError("at least one declared component mixture is required")
    for mixture in mixtures:
        if set(mixture) != {"name", *RESOURCE_COMPONENTS}:
            raise ValueError("component mixture fields mismatch")
        values = [float(mixture[name]) for name in RESOURCE_COMPONENTS]
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValueError("mixture weights must be finite and nonnegative")
        if not math.isclose(math.fsum(values), 1.0, abs_tol=1e-12):
            raise ValueError("each component mixture must sum to one")
    return config


def _profile_spec(config: Mapping[str, Any]) -> SyntheticExecutionProfileSpec:
    values = config["native_profile"]
    return SyntheticExecutionProfileSpec(
        one_qubit_duration_ns=float(values["one_qubit_duration_ns"]),
        two_qubit_duration_ns=float(values["two_qubit_duration_ns"]),
        noise=NoiseParameters(
            model="independent-pauli-depolarizing-v1",
            one_qubit_error=float(values["one_qubit_error"]),
            two_qubit_error=float(values["two_qubit_error"]),
            readout_error=float(values["readout_error"]),
        ),
    )


def _base_args(config: Mapping[str, Any], *, tiny: bool, solver_seed: int) -> argparse.Namespace:
    search = config["search"]
    qaoa = config["qaoa"]
    profile = config["native_profile"]
    test = config["test"]
    return argparse.Namespace(
        tiny=tiny,
        solver_seed=int(solver_seed),
        scheduler_seed_base=int(search["scheduler_seed_base"]) + 100 * int(solver_seed),
        noise_seed_base=int(search["noise_seed_base"]),
        noise_seeds=list(test["noise_seeds"]),
        simulations=int(search["simulations"]),
        candidate_top_k=int(search["candidate_top_k"]),
        max_factor_ancilla=int(search["max_factor_ancilla"]),
        max_factor_size=int(search["max_factor_size"]),
        policy_term_threshold=int(search["policy_term_threshold"]),
        scheduler_pool_size=int(search["scheduler_pool_size"]),
        scheduler_budget=int(search["scheduler_budget"]),
        scheduler_min_candidates=int(search["scheduler_min_candidates"]),
        redundancy_weight=float(search["redundancy_weight"]),
        redundancy_alpha=float(search["redundancy_alpha"]),
        utility_clip=float(search["utility_clip"]),
        qaoa_p=int(qaoa["p"]),
        qaoa_shots=int(qaoa["shots"]),
        qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
        qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
        endpoint_inputs=list(test["input_anchors"]),
        endpoint_shots=int(test["shots_per_input"]),
        one_qubit_error=float(profile["one_qubit_error"]),
        two_qubit_error=float(profile["two_qubit_error"]),
        readout_error=float(profile["readout_error"]),
    )


def _search_config(config: Mapping[str, Any]) -> SearchConfig:
    return _legacy_search_config(_base_args(config, tiny=False, solver_seed=1))


def _aes_truth_hashes() -> tuple[str, ...]:
    return tuple(
        coordinate.truth_table_sha256
        for coordinate in get_crypto_oracle_coordinates("AES")
    )


def _calibration_cases(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = config["calibration"]
    aes_hashes = set(_aes_truth_hashes())
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = 0
    while len(cases) < int(values["case_count"]):
        seed = int(values["seed_base"]) + offset
        offset += 1
        truth_table = random.Random(seed).getrandbits(1 << 8)
        function = BooleanFunction(8, truth_table)
        terms = frozenset(anf_monomials(function))
        truth_hex = canonical_hex(truth_table, min_nibbles=64)
        truth_sha = _sha_payload({"n": 8, "truth_table_hex": truth_hex})
        if truth_sha in aes_hashes or truth_sha in seen or len(terms) < 8:
            continue
        seen.add(truth_sha)
        cases.append(
            {
                "case_id": f"cal-n8-s{seed}",
                "instance_seed": seed,
                "truth_table": truth_table,
                "truth_table_hex": truth_hex,
                "truth_table_sha256": truth_sha,
                "boolean_function": function,
                "terms": terms,
                "anf_term_count": len(terms),
            }
        )
    return cases


def _calibration_dataset(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = {
        "dataset_id": "e4-v2-n8-non-aes-calibration-v1",
        "split": "calibration-only",
        "n": 8,
        "cases": [
            {
                "case_id": case["case_id"],
                "instance_seed": case["instance_seed"],
                "truth_table_sha256": case["truth_table_sha256"],
                "anf_term_count": case["anf_term_count"],
            }
            for case in cases
        ],
        "excluded_holdout_truth_table_sha256": list(_aes_truth_hashes()),
    }
    payload["dataset_sha256"] = dataset_sha256(payload)
    return payload


def _derived_seed(*parts: object) -> int:
    encoded = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")


def _contract_metric_from_success_counts(
    *,
    component_success: Mapping[str, int],
    shots: int,
    exact_success: int,
    n_inputs: int,
    target_index: int,
    n_qubits: int,
    ancilla_vacuous: bool,
) -> dict[str, Any]:
    component_names = ("input_preservation", "target_correct", "ancilla_zero")
    if shots <= 0 or set(component_success) != set(component_names):
        raise ValueError("balanced Oracle-contract metric needs three counted components")
    if any(not 0 <= int(component_success[name]) <= shots for name in component_names):
        raise ValueError("component success counts must lie in [0, shots]")
    if not 0 <= exact_success <= shots:
        raise ValueError("exact success count must lie in [0, shots]")
    components: dict[str, Any] = {}
    component_nll: list[float] = []
    for name in component_names:
        success = int(component_success[name])
        accuracy = success / shots
        probability = (success + 0.5) / (shots + 1.0)
        nll = -math.log(probability)
        component_nll.append(nll)
        components[name] = {
            "success_count": success,
            "shots": shots,
            "accuracy": accuracy,
            "jeffreys_probability": probability,
            "jeffreys_nll": nll,
            "vacuous": bool(ancilla_vacuous and name == "ancilla_zero"),
        }
    balanced_accuracy = statistics.mean(
        float(components[name]["accuracy"]) for name in component_names
    )
    balanced_nll = statistics.mean(component_nll)
    exact_probability = (exact_success + 0.5) / (shots + 1.0)
    return {
        "schema": PRIMARY_METRIC_SCHEMA,
        "source": "NoisyExecutionResult.counts",
        "bitstring_order": "logical-q[n-1]...q[0]",
        "n_inputs": n_inputs,
        "target_index": target_index,
        "n_qubits": n_qubits,
        "component_weighting": "equal-over-three-components",
        "components": components,
        "balanced_accuracy": balanced_accuracy,
        "balanced_geometric_probability": math.exp(-balanced_nll),
        "balanced_contract_nll": balanced_nll,
        "secondary_exact_full_state": {
            "success_count": exact_success,
            "shots": shots,
            "accuracy": exact_success / shots,
            "jeffreys_probability": exact_probability,
            "jeffreys_nll": -math.log(exact_probability),
        },
    }


def _balanced_oracle_contract_metrics(
    *,
    counts: Mapping[str, int],
    expected_logical_bits: Sequence[int],
    n_inputs: int = 8,
    target_index: int = 8,
) -> dict[str, Any]:
    expected = tuple(int(bit) for bit in expected_logical_bits)
    if any(bit not in (0, 1) for bit in expected):
        raise ValueError("expected_logical_bits must contain only 0/1")
    if len(expected) <= target_index or n_inputs != target_index:
        raise ValueError("expected bits do not match the declared Oracle layout")
    if any(expected[index] != 0 for index in range(target_index + 1, len(expected))):
        raise ValueError("ideal Oracle contract requires zero ancilla outputs")
    shots = 0
    component_success = {
        "input_preservation": 0,
        "target_correct": 0,
        "ancilla_zero": 0,
    }
    exact_success = 0
    ancilla_vacuous = len(expected) == target_index + 1
    for bitstring, raw_count in counts.items():
        if not isinstance(bitstring, str) or len(bitstring) != len(expected) or set(
            bitstring
        ) - {"0", "1"}:
            raise ValueError("trajectory count key violates logical bitstring layout")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
            raise ValueError("trajectory counts must be non-negative integers")
        count = int(raw_count)
        observed = tuple(int(bit) for bit in reversed(bitstring))
        shots += count
        if observed[:n_inputs] == expected[:n_inputs]:
            component_success["input_preservation"] += count
        if observed[target_index] == expected[target_index]:
            component_success["target_correct"] += count
        if ancilla_vacuous or all(
            observed[index] == 0 for index in range(target_index + 1, len(observed))
        ):
            component_success["ancilla_zero"] += count
        if observed == expected:
            exact_success += count
    return _contract_metric_from_success_counts(
        component_success=component_success,
        shots=shots,
        exact_success=exact_success,
        n_inputs=n_inputs,
        target_index=target_index,
        n_qubits=len(expected),
        ancilla_vacuous=ancilla_vacuous,
    )


def _aggregate_contract_metrics(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not metrics:
        raise ValueError("at least one endpoint metric is required")
    first = metrics[0]
    component_success = {
        name: sum(int(metric["components"][name]["success_count"]) for metric in metrics)
        for name in ("input_preservation", "target_correct", "ancilla_zero")
    }
    shots = sum(int(metric["components"]["input_preservation"]["shots"]) for metric in metrics)
    exact_success = sum(
        int(metric["secondary_exact_full_state"]["success_count"])
        for metric in metrics
    )
    if any(
        (metric["n_inputs"], metric["target_index"], metric["n_qubits"])
        != (first["n_inputs"], first["target_index"], first["n_qubits"])
        for metric in metrics
    ):
        raise ValueError("cannot aggregate endpoints with different Oracle layouts")
    return _contract_metric_from_success_counts(
        component_success=component_success,
        shots=shots,
        exact_success=exact_success,
        n_inputs=int(first["n_inputs"]),
        target_index=int(first["target_index"]),
        n_qubits=int(first["n_qubits"]),
        ancilla_vacuous=all(
            bool(metric["components"]["ancilla_zero"]["vacuous"])
            for metric in metrics
        ),
    )


def _execute_calibration_candidate(
    *,
    case: Mapping[str, Any],
    action: object,
    action_index: int,
    search_config: SearchConfig,
    profile_spec: SyntheticExecutionProfileSpec,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    key = StateKey(case["terms"], 0, 0)
    plan = complete_root_action_rollout(key, action, search_config)
    plan_check = verify_plan_anf(plan)
    allocated = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
    circuit = emit_plan_to_circuit(plan, 8, allocated)
    circuit_check = verify_circuit_anf(circuit, 8, case["terms"])
    oracle_ok = verify_oracle(circuit, case["boolean_function"])
    profile = profile_spec.build(circuit.n_qubits)
    compilation = compile_superconducting(circuit, profile)
    noise_values = config["native_profile"]
    noise_model = PauliNoiseModel(
        one_qubit_error=float(noise_values["one_qubit_error"]),
        two_qubit_error=float(noise_values["two_qubit_error"]),
        readout_error=float(noise_values["readout_error"]),
        parameter_source="synthetic-heavy-hex-like-e4-v2-calibration",
    )
    calibration = config["calibration"]
    output_inputs = (0, 1) if calibration["include_output_zero_and_one"] else (0,)
    endpoints: list[dict[str, Any]] = []
    for anchor in calibration["noise_seeds"]:
        for x in calibration["input_anchors"]:
            for y in output_inputs:
                logical_input = tuple((int(x) >> bit) & 1 for bit in range(8)) + (
                    int(y),
                ) + (0,) * (circuit.n_qubits - 9)
                seed = _derived_seed(
                    "e4-v2-calibration-noise",
                    case["case_id"],
                    action_index,
                    x,
                    y,
                    anchor,
                )
                result = simulate_noisy_shots(
                    compilation,
                    logical_input,
                    shots=int(calibration["shots_per_input"]),
                    seed=seed,
                    noise_model=noise_model,
                    max_qubits=10,
                )
                desired = list(logical_input)
                desired[8] ^= int(case["boolean_function"].evaluate(int(x)))
                contract_metrics = _balanced_oracle_contract_metrics(
                    counts=result.counts,
                    expected_logical_bits=result.expected_logical_bits,
                )
                endpoints.append(
                    {
                        "input_x": int(x),
                        "output_input": int(y),
                        "noise_seed_anchor": int(anchor),
                        "seed": int(result.seed),
                        "shots": int(result.shots),
                        "success_count": int(result.success_count),
                        "success_rate": float(result.success_rate),
                        "counts": dict(result.counts),
                        "expected_logical_bits": list(result.expected_logical_bits),
                        "expected_bitstring": result.expected_bitstring,
                        "bitstring_order": result.bitstring_order,
                        "oracle_contract_metrics": contract_metrics,
                        "task_contract_ok": tuple(desired) == result.expected_logical_bits,
                        "actual_noisy_simulation": bool(result.actual_noisy_simulation),
                        "hardware_execution": bool(result.hardware_execution),
                        "noise_applied": bool(result.noise_applied),
                    }
                )
    success = sum(row["success_count"] for row in endpoints)
    shots = sum(row["shots"] for row in endpoints)
    probability = (success + 0.5) / (shots + 1.0)
    aggregate_metrics = _aggregate_contract_metrics(
        [row["oracle_contract_metrics"] for row in endpoints]
    )
    if (
        aggregate_metrics["secondary_exact_full_state"]["success_count"] != success
        or aggregate_metrics["secondary_exact_full_state"]["shots"] != shots
    ):
        raise RuntimeError("recomputed exact full-state counts do not match simulator")
    return {
        "plan_anf_ok": bool(plan_check.ok),
        "circuit_anf_ok": bool(circuit_check.ok),
        "oracle_ok": bool(oracle_ok),
        "logical_score": float(plan.score(PAPER_WEIGHTS)),
        "logical_cost": asdict(plan.cost),
        "logical_n_qubits": circuit.n_qubits,
        "native_gate_set_ok": all(
            gate.name in {"rz", "sx", "x", "cx"} for gate in compilation.native_gates
        ),
        "coupling_ok": all(
            tuple(sorted(gate.qubits)) in profile.coupling_edges
            for gate in compilation.native_gates
            if gate.name == "cx"
        ),
        "noisy_endpoints": endpoints,
        "success_count": success,
        "total_shots": shots,
        "primary_metric": PRIMARY_METRIC_SCHEMA,
        "oracle_contract_metrics": aggregate_metrics,
        "balanced_contract_accuracy": aggregate_metrics["balanced_accuracy"],
        "balanced_contract_nll": aggregate_metrics["balanced_contract_nll"],
        "jeffreys_success_probability": probability,
        "secondary_exact_full_state_nll": -math.log(probability),
        # Backward-readable aliases; in v2 these are explicitly secondary.
        "oracle_task_nll": -math.log(probability),
    }


def _calibration_candidate_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Spawn-safe calibration worker for one frozen case/action pair."""

    torch.set_num_threads(1)
    case_payload = payload["case"]
    truth_table = int(case_payload["truth_table"])
    case = {
        **case_payload,
        "terms": frozenset(int(term) for term in case_payload["terms"]),
        "boolean_function": BooleanFunction(8, truth_table),
    }
    started = time.perf_counter()
    execution = _execute_calibration_candidate(
        case=case,
        action=payload["action"],
        action_index=int(payload["action_index"]),
        search_config=_search_config(payload["config"]),
        profile_spec=_profile_spec(payload["config"]),
        config=payload["config"],
    )
    return {
        "case_index": int(payload["case_index"]),
        "case_id": str(case_payload["case_id"]),
        "action_index": int(payload["action_index"]),
        "execution": execution,
        "worker_elapsed_s": time.perf_counter() - started,
    }


def _run_calibration_jobs(
    jobs: Sequence[dict[str, Any]],
    *,
    workers: int,
) -> tuple[list[dict[str, Any]], str]:
    """Execute calibration jobs and return a deterministic case/action order."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    if workers == 1:
        results = [_calibration_candidate_worker(job) for job in jobs]
        results.sort(key=lambda row: (row["case_index"], row["action_index"]))
        return results, "in_process"
    try:
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
        )
    except (PermissionError, OSError) as exc:
        print(
            f"execution_mode=in_process_fallback process_pool_error={type(exc).__name__}",
            flush=True,
        )
        results = [_calibration_candidate_worker(job) for job in jobs]
        results.sort(key=lambda row: (row["case_index"], row["action_index"]))
        return results, "in_process_fallback"
    results: list[dict[str, Any]] = []
    with executor:
        future_jobs = {
            executor.submit(_calibration_candidate_worker, job): job for job in jobs
        }
        for future in as_completed(future_jobs):
            job = future_jobs[future]
            try:
                results.append(future.result())
            except Exception as exc:
                raise RuntimeError(
                    f"E4-v2 calibration worker failed for "
                    f"case={job['case']['case_id']} action={job['action_index']}"
                ) from exc
    results.sort(key=lambda row: (row["case_index"], row["action_index"]))
    return results, "process_pool"


def _select_ridge_alpha(
    records: Sequence[ExecutionCalibrationRecord],
    case_ids: Sequence[str],
    config: Mapping[str, Any],
) -> tuple[float, dict[str, Any]]:
    alphas = [float(value) for value in config["weight_selection"]["ridge_alpha_grid"]]
    unique_cases = sorted(set(case_ids))
    if len(unique_cases) < 2:
        return alphas[0], {
            "method": "unavailable-single-case-tiny",
            "selected_alpha": alphas[0],
            "scores": [],
        }
    scores: list[dict[str, Any]] = []
    for alpha in alphas:
        errors: list[float] = []
        for held_out in unique_cases:
            train = [
                record
                for record, case_id in zip(records, case_ids)
                if case_id != held_out
            ]
            validation = [
                record
                for record, case_id in zip(records, case_ids)
                if case_id == held_out
            ]
            model = RidgeExecutionCostModel(ridge_alpha=alpha).fit(train)
            for record in validation:
                prediction = float(model.predict(record.state_key, (record.action,))[0])
                errors.append(abs(prediction - record.execution_cost))
        scores.append(
            {
                "ridge_alpha": alpha,
                "grouped_leave_one_case_out_mae": statistics.mean(errors),
                "validation_observations": len(errors),
            }
        )
    selected = min(
        scores,
        key=lambda row: (
            row["grouped_leave_one_case_out_mae"],
            row["ridge_alpha"],
        ),
    )
    return float(selected["ridge_alpha"]), {
        "method": "leave-one-function-out-mae",
        "selected_alpha": float(selected["ridge_alpha"]),
        "scores": scores,
    }


def _resource_scales(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    scales: dict[str, float] = {}
    for component in RESOURCE_COMPONENTS:
        values = np.asarray(
            [float(row["resource_components"][component]) for row in rows],
            dtype=float,
        )
        scale = float(np.quantile(values, 0.9))
        scales[component] = max(scale, 1.0e-12)
    return scales


def _select_penalty_weights(
    *,
    case_runtime: Sequence[Mapping[str, Any]],
    scales: Mapping[str, float],
    config: Mapping[str, Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    selection = config["weight_selection"]
    loss_gate = float(selection["max_mean_raw_objective_loss"])
    traces: list[dict[str, Any]] = []
    for mixture in selection["component_mixtures"]:
        for lambda_value_raw in selection["lambda_grid"]:
            lambda_value = float(lambda_value_raw)
            coefficients = {
                component: lambda_value * float(mixture[component]) / scales[component]
                for component in RESOURCE_COMPONENTS
            }
            case_rows: list[dict[str, Any]] = []
            for runtime in case_runtime:
                raw = tuple(float(value) for value in runtime["raw_utilities"])
                redundancy = runtime["redundancy"]
                resources = runtime["resources"]
                adjusted = tuple(
                    raw[index]
                    - math.fsum(
                        float(resources[index][component]) * coefficients[component]
                        for component in RESOURCE_COMPONENTS
                    )
                    for index in range(len(raw))
                )
                clipped_raw = tuple(
                    max(-float(config["search"]["utility_clip"]), min(
                        float(config["search"]["utility_clip"]), value
                    ))
                    for value in raw
                )
                clipped_adjusted = tuple(
                    max(-float(config["search"]["utility_clip"]), min(
                        float(config["search"]["utility_clip"]), value
                    ))
                    for value in adjusted
                )
                baseline = schedule_diverse_candidates(
                    clipped_raw,
                    redundancy,
                    int(config["search"]["scheduler_budget"]),
                    method="exact",
                    redundancy_weight=float(config["search"]["redundancy_weight"]),
                )
                chosen = schedule_diverse_candidates(
                    clipped_adjusted,
                    redundancy,
                    int(config["search"]["scheduler_budget"]),
                    method="exact",
                    redundancy_weight=float(config["search"]["redundancy_weight"]),
                )
                baseline_raw_objective = selection_objective(
                    clipped_raw,
                    redundancy,
                    baseline.selected_indices,
                    redundancy_weight=float(config["search"]["redundancy_weight"]),
                )
                selected_raw_objective = selection_objective(
                    clipped_raw,
                    redundancy,
                    chosen.selected_indices,
                    redundancy_weight=float(config["search"]["redundancy_weight"]),
                )
                raw_loss = max(
                    0.0,
                    (baseline_raw_objective - selected_raw_objective)
                    / max(abs(baseline_raw_objective), 1.0),
                )
                case_rows.append(
                    {
                        "case_id": runtime["case_id"],
                        "baseline_selected_indices": list(baseline.selected_indices),
                        "selected_indices": list(chosen.selected_indices),
                        "raw_objective_loss": raw_loss,
                        "selected_mean_balanced_contract_nll": statistics.mean(
                            float(runtime["nll"][index])
                            for index in chosen.selected_indices
                        ),
                    }
                )
            trace = {
                "mixture": str(mixture["name"]),
                "lambda": lambda_value,
                "coefficients": coefficients,
                "mean_raw_objective_loss": statistics.mean(
                    row["raw_objective_loss"] for row in case_rows
                ),
                "mean_selected_balanced_contract_nll": statistics.mean(
                    row["selected_mean_balanced_contract_nll"] for row in case_rows
                ),
                "cases": case_rows,
            }
            trace["passes_raw_objective_loss_gate"] = (
                trace["mean_raw_objective_loss"] <= loss_gate + 1e-15
            )
            traces.append(trace)
    eligible = [row for row in traces if row["passes_raw_objective_loss_gate"]]
    if not eligible:
        raise RuntimeError("no calibration-only penalty candidate passed the loss gate")
    selected = min(
        eligible,
        key=lambda row: (
            row["mean_selected_balanced_contract_nll"],
            row["mean_raw_objective_loss"],
            row["lambda"],
            row["mixture"],
        ),
    )
    return dict(selected["coefficients"]), {
        "selection_scope": "calibration-only-non-aes",
        "selection_method": "declared-grid-exact-scheduler-v1",
        "raw_objective_loss_gate": loss_gate,
        "selected": selected,
        "candidates": traces,
    }


def _manifest(
    *,
    run_id: str,
    phase: str,
    status: str,
    created_at: str,
    dataset: dict[str, Any],
    config: dict[str, Any],
    checkpoint: Path,
    counts: dict[str, Any],
    timing: dict[str, Any],
    command: dict[str, Any],
    variants: Sequence[str],
    claim_boundary: str,
) -> dict[str, Any]:
    record = ExperimentManifest(
        run_id=run_id,
        track=TRACK,
        experiment=f"{config['experiment']}:{phase}",
        status=status,
        created_at_utc=created_at,
        source=source_record(PROJECT_ROOT),
        environment=environment_record(),
        command=command,
        dataset=dataset,
        config={"sha256": _config_sha256(config), "payload": config},
        model=model_record(checkpoint, PROJECT_ROOT),
        variants=tuple(variants),
        expected_artifacts=EXPECTED_ARTIFACTS,
        counts=counts,
        timing=timing,
        claim_boundary=claim_boundary,
    ).to_dict()
    record["phase"] = phase
    return record


def run_calibration(
    *,
    config: dict[str, Any],
    out_dir: Path,
    run_id: str,
    tiny: bool,
    config_path: Path,
    workers: int = 1,
) -> Path:
    if workers <= 0:
        raise ValueError("workers must be positive")
    created_at = utc_now()
    started = time.perf_counter()
    checkpoint = (PROJECT_ROOT / config["checkpoint"]).resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    cases = _calibration_cases(config)
    dataset = _calibration_dataset(cases)
    search_config = _search_config(config)
    profile_spec = _profile_spec(config)
    zero_weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=str(dataset["dataset_sha256"]),
        profile_sha256=profile_spec.profile_sha256,
    )
    zero_adjuster = make_root_rollout_execution_utility_adjuster(
        n_inputs=8,
        search_config=search_config,
        profile_spec=profile_spec,
        penalty_weights=zero_weights,
        expected_profile_sha256=profile_spec.profile_sha256,
    )
    raw_rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    records: list[ExecutionCalibrationRecord] = []
    record_case_ids: list[str] = []
    case_runtime: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = [
        {"event": "calibration_started", "run_id": run_id, "at_utc": created_at}
    ]
    jobs: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases):
        scorer = FoundationScorer.from_checkpoint(checkpoint)
        policy = TermThresholdPolicyScorer(
            scorer, int(config["search"]["policy_term_threshold"])
        )
        key = StateKey(case["terms"], 0, 0)
        probe = NeuralMCTSSolver(
            config=search_config,
            simulations=0,
            seed=int(case["instance_seed"]),
            neural_scorer=policy,
            value_estimator=None,
            rollout_scorer=None,
        )
        node = probe._node(key)
        probe._expand(node)
        actions = tuple(node.actions[: int(config["search"]["scheduler_pool_size"])])
        if len(actions) < int(config["search"]["scheduler_budget"]):
            raise RuntimeError(f"calibration case {case['case_id']} has too few actions")
        direct_score = float(node.direct.score(search_config.weights))
        denominator = max(abs(direct_score), 1.0)
        raw_utilities = tuple(
            (direct_score - probe._rollout_action_cost(key, action)) / denominator
            for action in actions
        )
        profile_audit = zero_adjuster.adjust(key, actions, raw_utilities)
        resources = [
            dict(candidate["resource_components"])
            for candidate in profile_audit.diagnostics["candidates"]
        ]
        nll_values: list[float | None] = [None] * len(actions)
        worker_times: list[float | None] = [None] * len(actions)
        case_runtime.append(
            {
                "case_id": case["case_id"],
                "key": key,
                "actions": actions,
                "raw_utilities": raw_utilities,
                "redundancy": action_redundancy_matrix(
                    actions, alpha=float(config["search"]["redundancy_alpha"])
                ),
                "resources": resources,
                "nll": nll_values,
                "worker_elapsed_s": worker_times,
            }
        )
        for index, action in enumerate(actions):
            jobs.append(
                {
                    "case_index": case_index,
                    "case": {
                        "case_id": case["case_id"],
                        "instance_seed": case["instance_seed"],
                        "truth_table": case["truth_table"],
                        "truth_table_hex": case["truth_table_hex"],
                        "truth_table_sha256": case["truth_table_sha256"],
                        "terms": tuple(sorted(case["terms"])),
                        "anf_term_count": case["anf_term_count"],
                    },
                    "action_index": index,
                    "action": action,
                    "config": config,
                }
            )
    job_results, execution_mode = _run_calibration_jobs(jobs, workers=workers)
    for result in job_results:
        case_index = int(result["case_index"])
        action_index = int(result["action_index"])
        case = cases[case_index]
        runtime = case_runtime[case_index]
        action = runtime["actions"][action_index]
        execution = result["execution"]
        runtime["nll"][action_index] = float(execution["balanced_contract_nll"])
        runtime["worker_elapsed_s"][action_index] = float(result["worker_elapsed_s"])
        calibration_id = f"{case['case_id']}:a{action_index:02d}"
        record = ExecutionCalibrationRecord(
            calibration_id=calibration_id,
            state_key=runtime["key"],
            action=action,
            execution_cost=float(execution["balanced_contract_nll"]),
        )
        records.append(record)
        record_case_ids.append(str(case["case_id"]))
        observation = {
            "schema_version": CALIBRATION_SCHEMA,
            "record_type": "calibration_observation",
            "calibration_id": calibration_id,
            "case_id": case["case_id"],
            "truth_table_sha256": case["truth_table_sha256"],
            "state": {"terms": sorted(case["terms"]), "prefix_len": 0,
                      "live_factor_ancilla": 0},
            "action_index": action_index,
            "action": _action_signature(action),
            "raw_utility": float(runtime["raw_utilities"][action_index]),
            "resource_components": runtime["resources"][action_index],
            **execution,
        }
        observations.append(observation)
        raw_rows.append(observation)
    for runtime in case_runtime:
        if any(value is None for value in runtime["nll"]):
            raise RuntimeError(f"missing calibration result for {runtime['case_id']}")
        events.append(
            {
                "event": "calibration_case_completed",
                "case_id": runtime["case_id"],
                "candidate_count": len(runtime["actions"]),
                "worker_elapsed_s": math.fsum(
                    float(value) for value in runtime["worker_elapsed_s"]
                ),
            }
        )
    # Narrow the type after the completeness check above.  The scheduler only
    # receives fully materialized floating-point endpoint losses.
    for runtime in case_runtime:
        runtime["nll"] = [float(value) for value in runtime["nll"]]

    alpha, grouped_cv = _select_ridge_alpha(records, record_case_ids, config)
    risk_model = RidgeExecutionCostModel(ridge_alpha=alpha).fit(records)
    risk_metadata = risk_model.metadata()
    for runtime in case_runtime:
        predictions = risk_model.predict(runtime["key"], runtime["actions"])
        for resource, prediction in zip(runtime["resources"], predictions):
            resource["model_risk"] = float(prediction)
    for row, record in zip(observations, records):
        row["resource_components"]["model_risk"] = float(
            risk_model.predict(record.state_key, (record.action,))[0]
        )
    observations_payload = [
        {
            key: row[key]
            for key in (
                "calibration_id",
                "case_id",
                "truth_table_sha256",
                "state",
                "action",
                "raw_utility",
                "resource_components",
                "primary_metric",
                "oracle_contract_metrics",
                "balanced_contract_accuracy",
                "balanced_contract_nll",
                "secondary_exact_full_state_nll",
                "noisy_endpoints",
            )
        }
        for row in observations
    ]
    observations_sha = _sha_payload(observations_payload)
    scales = _resource_scales(observations)
    coefficients, selection_transcript = _select_penalty_weights(
        case_runtime=case_runtime,
        scales=scales,
        config=config,
    )
    weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=observations_sha,
        profile_sha256=profile_spec.profile_sha256,
        **coefficients,
    )
    raw_rows.append(
        {
            "schema_version": CALIBRATION_SCHEMA,
            "record_type": "calibration_freeze",
            "observations_sha256": observations_sha,
            "risk_model_metadata": risk_metadata,
            "penalty_weights": weights.canonical_payload(),
            "selection_transcript": selection_transcript,
            "resource_p90_scales": scales,
        }
    )
    checks = {
        "non_aes_calibration_hashes_disjoint": set(
            case["truth_table_sha256"] for case in cases
        ).isdisjoint(_aes_truth_hashes()),
        "all_calibration_observations_present": len(observations)
        == sum(len(runtime["actions"]) for runtime in case_runtime),
        "all_logical_semantics_verified": all(
            row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"]
            for row in observations
        ),
        "all_native_contracts_verified": all(
            row["native_gate_set_ok"] and row["coupling_ok"] for row in observations
        ),
        "all_noisy_runs_actual_and_labelled": all(
            all(
                endpoint["actual_noisy_simulation"]
                and endpoint["noise_applied"]
                and not endpoint["hardware_execution"]
                and endpoint["task_contract_ok"]
                for endpoint in row["noisy_endpoints"]
            )
            for row in observations
        ),
        "observations_sha_bound_to_weights": weights.calibration_sha256
        == observations_sha,
        "profile_sha_bound_to_weights": weights.profile_sha256
        == profile_spec.profile_sha256,
        "risk_model_fitted_on_calibration_only": set(
            risk_metadata["calibration_ids"]
        ) == {row["calibration_id"] for row in observations},
        "weight_selection_calibration_only": selection_transcript["selection_scope"]
        == "calibration-only-non-aes",
        "primary_metric_recomputed_from_counts": all(
            row["primary_metric"] == PRIMARY_METRIC_SCHEMA
            and math.isfinite(row["balanced_contract_nll"])
            and row["oracle_contract_metrics"]["source"]
            == "NoisyExecutionResult.counts"
            for row in observations
        ),
    }
    integrity_ok = all(checks.values())
    claim_boundary = (
        "Tiny integration smoke; numeric values are not performance evidence. "
        if tiny else ""
    ) + str(config["claim_boundary"])
    summary = {
        "schema_version": CALIBRATION_SCHEMA,
        "phase": "calibration",
        "run_id": run_id,
        "tiny": tiny,
        "config_sha256": _config_sha256(config),
        "dataset_sha256": dataset["dataset_sha256"],
        "calibration_truth_table_sha256": [
            case["truth_table_sha256"] for case in cases
        ],
        "aes_holdout_truth_table_sha256": list(_aes_truth_hashes()),
        "calibration_observation_count": len(observations),
        "observations_sha256": observations_sha,
        "profile": profile_spec.canonical_payload(),
        "profile_sha256": profile_spec.profile_sha256,
        "primary_metric": config["primary_metric"],
        "primary_metric_name": "balanced_contract_nll",
        "secondary_metric_name": "exact_full_state_jeffreys_nll",
        "calibration_primary_metric": {
            "count": len(observations),
            "mean": statistics.mean(
                row["balanced_contract_nll"] for row in observations
            ),
            "min": min(row["balanced_contract_nll"] for row in observations),
            "max": max(row["balanced_contract_nll"] for row in observations),
            "population_variance": statistics.pvariance(
                row["balanced_contract_nll"] for row in observations
            ),
        },
        "calibration_secondary_exact_metric": {
            "mean": statistics.mean(
                row["secondary_exact_full_state_nll"] for row in observations
            ),
            "min": min(
                row["secondary_exact_full_state_nll"] for row in observations
            ),
            "max": max(
                row["secondary_exact_full_state_nll"] for row in observations
            ),
        },
        "grouped_cross_validation": grouped_cv,
        "risk_model_metadata": risk_metadata,
        "risk_model_sha256": risk_metadata["model_sha256"],
        "model_calibration_sha256": risk_metadata["calibration_sha256"],
        "resource_p90_scales": scales,
        "penalty_weights": weights.canonical_payload(),
        "penalty_weights_sha256": weights.weights_sha256,
        "selection_transcript": selection_transcript,
        "integrity_ok": integrity_ok,
        "claim_boundary": claim_boundary,
    }
    verifier = {
        "schema_version": VERIFIER_SCHEMA,
        "phase": "calibration",
        "run_id": run_id,
        "checks": checks,
        "ok": integrity_ok,
    }
    elapsed = time.perf_counter() - started
    events.append(
        {"event": "calibration_completed", "run_id": run_id, "elapsed_s": elapsed}
    )
    manifest = _manifest(
        run_id=run_id,
        phase="calibration",
        status="complete" if integrity_ok else "failed",
        created_at=created_at,
        dataset=dataset,
        config=config,
        checkpoint=checkpoint,
        counts={"cases": len(cases), "observations": len(observations)},
        timing={"wall_s": elapsed},
        command={"entrypoint": "scripts/run_aes_execution_aware_eval.py",
                 "subcommand": "calibrate", "config": str(config_path),
                 "tiny": tiny, "workers": workers,
                 "execution_mode": execution_mode},
        variants=("calibration",),
        claim_boundary=claim_boundary,
    )
    run_dir = out_dir.resolve() / run_id
    bundle = write_pilot_bundle(
        run_dir=run_dir,
        run_record=manifest,
        raw_records=raw_rows,
        summary=summary,
        verifier=verifier,
        events=events,
        track=TRACK,
    )
    if not bundle.ok:
        raise RuntimeError(f"calibration bundle failed: {bundle.errors}")
    from scripts.verify_aes_execution_aware_bundle import verify_e4v2_bundle

    independent = verify_e4v2_bundle(run_dir)
    if not independent["ok"]:
        raise RuntimeError(f"independent calibration verification failed: {independent['errors']}")
    print(f"calibration_bundle={run_dir}")
    print(f"observations={len(observations)} weights_sha256={weights.weights_sha256}")
    return run_dir


def _weights_from_payload(payload: Mapping[str, Any]) -> FrozenExecutionPenaltyWeights:
    expected = {
        "schema",
        "calibration_sha256",
        "profile_sha256",
        "normalization",
        *RESOURCE_COMPONENTS,
    }
    if set(payload) != expected:
        raise ValueError("frozen penalty-weight fields mismatch")
    return FrozenExecutionPenaltyWeights(
        calibration_sha256=str(payload["calibration_sha256"]),
        profile_sha256=str(payload["profile_sha256"]),
        **{name: float(payload[name]) for name in RESOURCE_COMPONENTS},
    )


def _attach_and_aggregate_endpoint_metrics(row: dict[str, Any]) -> dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    for endpoint in row["noisy_endpoints"]:
        if endpoint.get("bitstring_order") not in (None, "logical-q[n-1]...q[0]"):
            raise ValueError("unsupported endpoint bitstring order")
        expected_bits = tuple(
            int(bit) for bit in reversed(str(endpoint["expected_bitstring"]))
        )
        metric = _balanced_oracle_contract_metrics(
            counts=endpoint["counts"],
            expected_logical_bits=expected_bits,
        )
        endpoint["expected_logical_bits"] = list(expected_bits)
        endpoint["bitstring_order"] = "logical-q[n-1]...q[0]"
        endpoint["oracle_contract_metrics"] = metric
        metrics.append(metric)
    return _aggregate_contract_metrics(metrics)


def _test_trial_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Spawn-safe held-out worker; reconstructs frozen objects without fitting."""

    torch.set_num_threads(1)
    config = payload["config"]
    calibration = payload["calibration_summary"]
    solver_seed = int(payload["solver_seed"])
    output_bit = int(payload["output_bit"])
    variant = str(payload["variant"])
    args = _base_args(config, tiny=bool(payload["tiny"]), solver_seed=solver_seed)
    search_config = _search_config(config)
    profile_spec = _profile_spec(config)
    risk_metadata = calibration["risk_model_metadata"]
    risk_model = RidgeExecutionCostModel.from_metadata(
        risk_metadata,
        penalty_weight=0.0,
        expected_calibration_sha256=str(calibration["model_calibration_sha256"]),
    )
    weights = _weights_from_payload(calibration["penalty_weights"])
    if weights.weights_sha256 != calibration["penalty_weights_sha256"]:
        raise ValueError("penalty-weight SHA mismatch before held-out execution")
    if profile_spec.profile_sha256 != calibration["profile_sha256"]:
        raise ValueError("profile SHA mismatch before held-out execution")
    execution_arm = variant.startswith("execution_")
    adjuster = (
        make_root_rollout_execution_utility_adjuster(
            n_inputs=8,
            search_config=search_config,
            profile_spec=profile_spec,
            penalty_weights=weights,
            expected_profile_sha256=profile_spec.profile_sha256,
            risk_model=risk_model,
            expected_risk_model_sha256=str(calibration["risk_model_sha256"]),
        )
        if execution_arm
        else None
    )
    coordinates = get_crypto_oracle_coordinates("AES")
    started = time.perf_counter()
    row = _aes_trial(
        coordinate=coordinates[output_bit],
        coordinates=coordinates,
        variant=variant,
        args=args,
        search_config=search_config,
        checkpoint=Path(payload["checkpoint"]),
        checkpoint_sha256=str(payload["checkpoint_sha256"]),
        run_id=str(payload["run_id"]),
        execution_utility_adjuster=adjuster,
        paired_noise_seed_namespace=(
            f"fips197-aes-heldout:solver{solver_seed}:bit{output_bit}"
        ),
    )
    contract_metrics = _attach_and_aggregate_endpoint_metrics(row)
    exact = contract_metrics["secondary_exact_full_state"]
    feedback = row["execution_feedback"]
    diagnostics = feedback.get("diagnostics", {}) if isinstance(feedback, dict) else {}
    row.update(
        schema_version=TEST_SCHEMA,
        record_type="execution_aware_aes_trial",
        utility_mode=("calibration_frozen_execution" if execution_arm else "historical_logical"),
        calibration_run_id=calibration["run_id"],
        calibration_observations_sha256=calibration["observations_sha256"],
        calibration_summary_sha256=str(payload["calibration_summary_sha256"]),
        profile_sha256=calibration["profile_sha256"],
        risk_model_sha256=calibration["risk_model_sha256"],
        penalty_weights_sha256=calibration["penalty_weights_sha256"],
        execution_adjuster_sha256=(
            feedback.get("model_sha256") if execution_arm else None
        ),
        risk_model_loaded_without_refit=execution_arm,
        calibration_only_weight_selection=True,
        test_noisy_outcome_used_by_utility=False,
        adjuster_heldout_noisy_outcome_used=(
            diagnostics.get("heldout_noisy_outcome_used") if execution_arm else False
        ),
        primary_metric=PRIMARY_METRIC_SCHEMA,
        endpoint_oracle_contract_metrics=contract_metrics,
        endpoint_balanced_contract_accuracy=contract_metrics["balanced_accuracy"],
        endpoint_balanced_contract_nll=contract_metrics["balanced_contract_nll"],
        endpoint_success_count=exact["success_count"],
        endpoint_total_shots=exact["shots"],
        endpoint_secondary_exact_full_state_nll=exact["jeffreys_nll"],
        # Backward-readable alias, explicitly secondary in schema v2.
        endpoint_oracle_task_nll=exact["jeffreys_nll"],
    )
    return {"row": row, "worker_elapsed_s": time.perf_counter() - started}


def _run_test_jobs(
    jobs: Sequence[dict[str, Any]],
    *,
    workers: int,
    record_completed: Callable[[dict[str, Any]], None],
) -> str:
    if workers == 1:
        for job in jobs:
            record_completed(_test_trial_worker(job))
        return "in_process"
    try:
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
        )
    except (PermissionError, OSError) as exc:
        print(
            f"execution_mode=in_process_fallback process_pool_error={type(exc).__name__}",
            flush=True,
        )
        for job in jobs:
            record_completed(_test_trial_worker(job))
        return "in_process_fallback"
    with executor:
        future_jobs = {executor.submit(_test_trial_worker, job): job for job in jobs}
        for future in as_completed(future_jobs):
            job = future_jobs[future]
            try:
                record_completed(future.result())
            except Exception as exc:
                raise RuntimeError(
                    f"E4-v2 worker failed for bit={job['output_bit']} "
                    f"seed={job['solver_seed']} variant={job['variant']}"
                ) from exc
    return "process_pool"


def _test_summary(
    *,
    run_id: str,
    rows: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
    tiny: bool,
    calibration_reference: dict[str, Any],
    claim_boundary: str,
) -> dict[str, Any]:
    by_variant: dict[str, Any] = {}
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        by_variant[variant] = {
            "trial_count": len(selected),
            "endpoint_balanced_contract_nll_mean": statistics.mean(
                row["endpoint_balanced_contract_nll"] for row in selected
            ),
            "endpoint_balanced_contract_accuracy_mean": statistics.mean(
                row["endpoint_balanced_contract_accuracy"] for row in selected
            ),
            "endpoint_secondary_exact_full_state_nll_mean": statistics.mean(
                row["endpoint_secondary_exact_full_state_nll"] for row in selected
            ),
            "logical_resource_score_mean": statistics.mean(
                row["logical_resource_score"] for row in selected
            ),
            "native_two_qubit_gate_count_mean": statistics.mean(
                row["native"]["two_qubit_gate_count"] for row in selected
            ),
            "qaoa_attempted": sum(
                bool(row["scheduler"]["qaoa_attempted"]) for row in selected
            ),
            "qaoa_succeeded": sum(
                bool(row["scheduler"]["qaoa_succeeded"]) for row in selected
            ),
            "qaoa_fallback": sum(
                bool(row["scheduler"]["qaoa_fallback"]) for row in selected
            ),
        }
    paired_blocks: list[dict[str, Any]] = []
    for output_bit in range(8):
        for solver_seed in config["test"]["solver_seeds"]:
            block = [
                row for row in rows
                if row["output_bit"] == output_bit and row["solver_seed"] == solver_seed
            ]
            paired_blocks.append(
                {
                    "output_bit": output_bit,
                    "solver_seed": solver_seed,
                    "execution_minus_historical_greedy_balanced_contract_nll": next(
                        row["endpoint_balanced_contract_nll"] for row in block
                        if row["variant"] == "execution_greedy"
                    ) - next(
                        row["endpoint_balanced_contract_nll"] for row in block
                        if row["variant"] == "historical_greedy"
                    ),
                    "execution_minus_historical_qaoa_balanced_contract_nll": next(
                        row["endpoint_balanced_contract_nll"] for row in block
                        if row["variant"] == "execution_qaoa_shot"
                    ) - next(
                        row["endpoint_balanced_contract_nll"] for row in block
                        if row["variant"] == "historical_qaoa_shot"
                    ),
                }
            )
    return {
        "schema_version": TEST_SCHEMA,
        "phase": "test",
        "run_id": run_id,
        "tiny": tiny,
        "performance_evidence": False if tiny else "diagnostic-synthetic-only",
        "config_sha256": _config_sha256(config),
        "variants": list(VARIANTS),
        "coordinate_count": 8,
        "solver_seeds": list(config["test"]["solver_seeds"]),
        "trial_count": len(rows),
        "calibration_reference": calibration_reference,
        "primary_metric": config["primary_metric"],
        "primary_metric_name": "balanced_contract_nll",
        "secondary_metric_name": "exact_full_state_jeffreys_nll",
        "variant_statistics": by_variant,
        "paired_blocks": paired_blocks,
        "all_logical_semantics_verified": all(
            row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"]
            and row["reversible_oracle_all_targets_ok"] for row in rows
        ),
        "all_native_contracts_verified": all(
            row["native"]["native_gate_set_ok"] and row["native"]["coupling_ok"]
            for row in rows
        ),
        "all_noisy_trajectories_actual": all(
            endpoint["actual_noisy_simulation"] and endpoint["noise_applied"]
            and not endpoint["hardware_execution"] and endpoint["task_contract_ok"]
            for row in rows for endpoint in row["noisy_endpoints"]
        ),
        "primary_metric_population_variance": statistics.pvariance(
            row["endpoint_balanced_contract_nll"] for row in rows
        ),
        "hardware_execution": False,
        "quantum_advantage_claimed": False,
        "claim_boundary": claim_boundary,
    }


def _declared_test_verifier(
    *, rows: Sequence[dict[str, Any]], summary: Mapping[str, Any]
) -> dict[str, Any]:
    seeds = summary["solver_seeds"]
    expected = {
        (bit, int(seed), variant)
        for bit in range(8) for seed in seeds for variant in VARIANTS
    }
    actual = {
        (row["output_bit"], row["solver_seed"], row["variant"]) for row in rows
    }
    groups = [(bit, int(seed)) for bit in range(8) for seed in seeds]
    execution_rows = [row for row in rows if row["variant"].startswith("execution_")]
    historical_rows = [row for row in rows if row["variant"].startswith("historical_")]
    qaoa_rows = [row for row in rows if row["variant"].endswith("qaoa_shot")]
    checks = {
        "complete_four_variant_aes_matrix": len(rows) == len(expected) and actual == expected,
        "raw_pool_and_utility_fairness": all(
            len({row["candidate_pool_sha256"] for row in rows
                 if (row["output_bit"], row["solver_seed"]) == group}) == 1
            and len({tuple(row["raw_scheduler_utilities"]) for row in rows
                     if (row["output_bit"], row["solver_seed"]) == group}) == 1
            for group in groups
        ),
        "historical_utility_identity": all(
            row["raw_scheduler_utilities"] == row["adjusted_scheduler_utilities"]
            for row in historical_rows
        ),
        "execution_utility_frozen_and_no_leakage": all(
            row["execution_feedback"].get("enabled") is True
            and row["risk_model_loaded_without_refit"] is True
            and row["test_noisy_outcome_used_by_utility"] is False
            and row["adjuster_heldout_noisy_outcome_used"] is False
            for row in execution_rows
        ),
        "primary_metric_counts_backed": all(
            row["primary_metric"] == PRIMARY_METRIC_SCHEMA
            and row["endpoint_oracle_contract_metrics"]["source"]
            == "NoisyExecutionResult.counts"
            and set(row["endpoint_oracle_contract_metrics"]["components"])
            == {"input_preservation", "target_correct", "ancilla_zero"}
            for row in rows
        ),
        "frozen_hashes_consistent": all(
            row["risk_model_sha256"]
            == summary["calibration_reference"]["risk_model_sha256"]
            and row["penalty_weights_sha256"]
            == summary["calibration_reference"]["penalty_weights_sha256"]
            and row["profile_sha256"]
            == summary["calibration_reference"]["profile_sha256"]
            for row in rows
        ),
        "common_noise_seeds_across_four_variants": all(
            len({endpoint["seed"] for row in rows
                 if (row["output_bit"], row["solver_seed"]) == group
                 for endpoint in row["noisy_endpoints"]
                 if (endpoint["input_x"], endpoint["noise_seed_anchor"])
                 == anchor}) == 1
            for group in groups
            for anchor in {
                (endpoint["input_x"], endpoint["noise_seed_anchor"])
                for row in rows if (row["output_bit"], row["solver_seed"]) == group
                for endpoint in row["noisy_endpoints"]
            }
        ),
        "qaoa_attempted_and_accounted": all(
            row["scheduler"]["qaoa_attempted"]
            and (row["scheduler"]["qaoa_succeeded"] or row["scheduler"]["qaoa_fallback"])
            for row in qaoa_rows
        ),
        "logical_native_noise_contracts": summary["all_logical_semantics_verified"]
        and summary["all_native_contracts_verified"]
        and summary["all_noisy_trajectories_actual"],
        "claim_boundary": summary["hardware_execution"] is False
        and summary["quantum_advantage_claimed"] is False,
    }
    return {
        "schema_version": VERIFIER_SCHEMA,
        "phase": "test",
        "run_id": summary["run_id"],
        "checks": checks,
        "ok": all(checks.values()),
    }


def run_test(
    *,
    config: dict[str, Any],
    out_dir: Path,
    run_id: str,
    tiny: bool,
    config_path: Path,
    calibration_run: Path,
    workers: int = 1,
) -> Path:
    if workers <= 0:
        raise ValueError("workers must be positive")
    created_at = utc_now()
    started = time.perf_counter()
    calibration_run = calibration_run.resolve()
    from scripts.verify_aes_execution_aware_bundle import verify_e4v2_bundle

    calibration_verification = verify_e4v2_bundle(calibration_run)
    if not calibration_verification["ok"]:
        raise ValueError(
            f"calibration bundle is not independently valid: {calibration_verification['errors']}"
        )
    calibration_summary_path = calibration_run / "summary.json"
    calibration = json.loads(calibration_summary_path.read_text(encoding="utf-8"))
    if calibration.get("phase") != "calibration":
        raise ValueError("calibration_run is not an E4-v2 calibration bundle")
    if calibration.get("config_sha256") != _config_sha256(config):
        raise ValueError("held-out config does not exactly match frozen calibration config")
    if set(calibration["calibration_truth_table_sha256"]) & set(_aes_truth_hashes()):
        raise ValueError("calibration/AES truth-table leakage detected")
    checkpoint = (PROJECT_ROOT / config["checkpoint"]).resolve()
    checkpoint_meta = model_record(checkpoint, PROJECT_ROOT)
    coordinates = get_crypto_oracle_coordinates("AES")
    if len(coordinates) != 8 or not verify_crypto_oracle_family("AES", coordinates=coordinates):
        raise RuntimeError("FIPS 197 AES family verification failed")
    calibration_summary_sha = sha256_file(calibration_summary_path)
    jobs = [
        {
            "config": config,
            "calibration_summary": calibration,
            "calibration_summary_sha256": calibration_summary_sha,
            "tiny": tiny,
            "solver_seed": solver_seed,
            "output_bit": output_bit,
            "variant": variant,
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": checkpoint_meta["sha256"],
            "run_id": run_id,
        }
        for output_bit in range(8)
        for solver_seed in config["test"]["solver_seeds"]
        for variant in VARIANTS
    ]
    rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = [
        {"event": "heldout_test_started", "run_id": run_id, "at_utc": created_at}
    ]

    def record_completed(result: dict[str, Any]) -> None:
        row = result["row"]
        rows.append(row)
        events.append(
            {"event": "heldout_trial_completed", "output_bit": row["output_bit"],
             "solver_seed": row["solver_seed"], "variant": row["variant"],
             "elapsed_s": result["worker_elapsed_s"]}
        )
        print(
            f"bit={row['output_bit']} seed={row['solver_seed']} variant={row['variant']} "
            f"score={row['logical_resource_score']:.3f} "
            f"endpoint={row['endpoint_success_count']}/{row['endpoint_total_shots']}",
            flush=True,
        )

    execution_mode = _run_test_jobs(jobs, workers=workers, record_completed=record_completed)
    rows.sort(
        key=lambda row: (
            int(row["output_bit"]),
            int(row["solver_seed"]),
            VARIANTS.index(row["variant"]),
        )
    )
    calibration_reference = {
        "run_id": calibration["run_id"],
        "summary_sha256": calibration_summary_sha,
        "config_sha256": calibration["config_sha256"],
        "dataset_sha256": calibration["dataset_sha256"],
        "observations_sha256": calibration["observations_sha256"],
        "risk_model_sha256": calibration["risk_model_sha256"],
        "model_calibration_sha256": calibration["model_calibration_sha256"],
        "penalty_weights_sha256": calibration["penalty_weights_sha256"],
        "profile_sha256": calibration["profile_sha256"],
        "loaded_without_fit": True,
    }
    claim_boundary = (
        "Tiny integration smoke; numeric values are not performance evidence. "
        if tiny else ""
    ) + str(config["claim_boundary"])
    summary = _test_summary(
        run_id=run_id,
        rows=rows,
        config=config,
        tiny=tiny,
        calibration_reference=calibration_reference,
        claim_boundary=claim_boundary,
    )
    verifier = _declared_test_verifier(rows=rows, summary=summary)
    elapsed = time.perf_counter() - started
    events.append(
        {"event": "heldout_test_completed", "run_id": run_id,
         "elapsed_s": elapsed, "execution_mode": execution_mode,
         "declared_verifier_ok": verifier["ok"]}
    )
    dataset = {
        "dataset_id": "aes-fips197-forward-sbox-coordinates-e4-v2",
        "split": "heldout-test-never-fit",
        "coordinates": [
            {"output_bit": coordinate.output_bit,
             "truth_table_sha256": coordinate.truth_table_sha256}
            for coordinate in coordinates
        ],
        "solver_seeds": list(config["test"]["solver_seeds"]),
        "input_anchors": list(config["test"]["input_anchors"]),
        "noise_seed_anchors": list(config["test"]["noise_seeds"]),
        "calibration_truth_table_sha256": calibration["calibration_truth_table_sha256"],
        "calibration_dataset_sha256": calibration["dataset_sha256"],
    }
    dataset["dataset_sha256"] = dataset_sha256(dataset)
    manifest = _manifest(
        run_id=run_id,
        phase="test",
        status="complete" if verifier["ok"] else "failed",
        created_at=created_at,
        dataset=dataset,
        config=config,
        checkpoint=checkpoint,
        counts={"coordinates": 8, "solver_seeds": len(config["test"]["solver_seeds"]),
                "trials": len(rows), "variants": len(VARIANTS)},
        timing={"wall_s": elapsed},
        command={"entrypoint": "scripts/run_aes_execution_aware_eval.py",
                 "subcommand": "test", "config": str(config_path), "tiny": tiny,
                 "workers": workers, "execution_mode": execution_mode,
                 "calibration_run_id": calibration["run_id"]},
        variants=VARIANTS,
        claim_boundary=claim_boundary,
    )
    run_dir = out_dir.resolve() / run_id
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
        raise RuntimeError(f"held-out bundle failed: {bundle.errors}")
    independent = verify_e4v2_bundle(run_dir, calibration_run=calibration_run)
    if not independent["ok"]:
        raise RuntimeError(f"independent held-out verification failed: {independent['errors']}")
    print(f"test_bundle={run_dir}")
    print(f"execution_mode={execution_mode} trials={len(rows)}")
    return run_dir


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "xa202609" / "e4_execution_aware_v2.json",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "xa202609",
    )
    parser.add_argument("--tiny", action="store_true")
    subparsers = parser.add_subparsers(dest="phase", required=True)
    calibration = subparsers.add_parser("calibrate")
    calibration.add_argument("--run-id", default=None)
    calibration.add_argument("--workers", type=int, default=1)
    test = subparsers.add_parser("test")
    test.add_argument("--run-id", default=None)
    test.add_argument("--calibration-run", type=Path, required=True)
    test.add_argument("--workers", type=int, default=1)
    return parser


def main() -> int:
    args = _parser().parse_args()
    torch.set_num_threads(1)
    config_path = args.config.expanduser().resolve()
    config = load_config(config_path, tiny=args.tiny)
    created = utc_now()
    stamp = created[:10].replace("-", "") + "-" + created[11:19].replace(":", "")
    if args.phase == "calibrate":
        run_calibration(
            config=config,
            out_dir=args.out_dir,
            run_id=args.run_id or f"{stamp}-e4v2-cal-{'tiny' if args.tiny else 'v1'}",
            tiny=args.tiny,
            config_path=config_path,
            workers=args.workers,
        )
    else:
        run_test(
            config=config,
            out_dir=args.out_dir,
            run_id=args.run_id or f"{stamp}-e4v2-test-{'tiny' if args.tiny else 'v1'}",
            tiny=args.tiny,
            config_path=config_path,
            calibration_run=args.calibration_run,
            workers=args.workers,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
