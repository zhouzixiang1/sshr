#!/usr/bin/env python3
"""Run the E3 simulator-calibrated execution-feedback experiment.

The protocol has two immutable phases. ``calibrate`` measures actual native
Pauli-trajectory outcomes for root-action rollout completions and fits a
permutation-invariant execution-cost model. ``test`` loads that frozen model
without refitting and evaluates a 2x2 utility/scheduler intervention on
disjoint Boolean functions.  The only pre-registered primary comparison is
``feedback_qaoa_shot`` versus ``historical_qaoa_shot``.

This is a synthetic-topology NumPy experiment.  It is not a real-device or
calibrated-hardware result and it does not claim quantum speedup or advantage.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Sequence


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
from src.anf_utils import anf_monomials  # noqa: E402
from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import (  # noqa: E402
    canonical_hex,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from src.contracts.experiment import ExperimentManifest  # noqa: E402
from src.contracts.search import PlanTrace  # noqa: E402
from src.factor_plan import (  # noqa: E402
    FactorAction,
    Plan,
    SearchConfig,
    emit_plan_to_circuit,
    factor_cost,
    greedy_plan,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import FoundationScorer  # noqa: E402
from src.hardware.noise import PauliNoiseModel, simulate_noisy_shots  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    native_to_openqasm3,
    verify_basis_equivalence,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.search.execution_feedback import (  # noqa: E402
    ExecutionCalibrationRecord,
    RidgeExecutionCostModel,
)
from src.search.mcts_scheduler import DiversitySchedulerConfig  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


CONFIG_SCHEMA = "xa.e3-native-feedback-config.v1"
CALIBRATION_SCHEMA = "xa.e3-native-feedback-calibration.v1"
TEST_SCHEMA = "xa.e3-native-feedback-test.v1"
TRACK = "xa202609/e3-native-feedback"
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
VARIANTS = (
    "historical_greedy",
    "feedback_greedy",
    "historical_qaoa_shot",
    "feedback_qaoa_shot",
)
PAPER_WEIGHTS = ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _probability(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a probability")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return result


def load_config(path: str | Path, *, tiny: bool = False) -> dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported E3 config schema")
    required = {
        "schema_version",
        "experiment",
        "checkpoint",
        "calibration",
        "test",
        "search",
        "qaoa",
        "native_profile",
        "noise_execution",
        "feedback_model",
        "statistics",
        "claim_boundary",
    }
    if set(config) != required:
        raise ValueError("E3 config fields do not match the frozen schema")
    config = copy.deepcopy(config)
    if tiny:
        config["calibration"]["case_count"] = 1
        config["test"]["case_count"] = 1
        # The second frozen test seed has a non-empty candidate pool, allowing
        # tiny mode to exercise the QAOA path. Tiny is never performance data.
        config["test"]["seed_base"] += 1
        config["test"]["solver_seeds"] = [1]
        config["search"]["simulations"] = max(
            2, int(config["search"]["scheduler_budget"])
        )
        config["search"]["candidate_top_k"] = 4
        config["search"]["scheduler_pool_size"] = 4
        config["qaoa"]["shots"] = 64
        config["qaoa"]["optimizer_restarts"] = 1
        config["qaoa"]["optimizer_steps"] = 2
        config["noise_execution"]["shots_per_input"] = 1
        config["noise_execution"]["noise_seeds"] = [101]
        config["statistics"]["bootstrap_resamples"] = 200

    for phase in ("calibration", "test"):
        _positive_int(config[phase]["n"], f"{phase}.n")
        _positive_int(config[phase]["case_count"], f"{phase}.case_count")
        _positive_int(config[phase]["seed_base"], f"{phase}.seed_base")
    seeds = config["test"]["solver_seeds"]
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(_positive_int(seed, "test.solver_seeds") != seed for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ValueError("test.solver_seeds must be unique positive integers")
    search = config["search"]
    for name in (
        "simulations",
        "candidate_top_k",
        "max_factor_ancilla",
        "max_factor_size",
        "scheduler_pool_size",
        "scheduler_budget",
        "scheduler_min_candidates",
    ):
        _positive_int(search[name], f"search.{name}")
    if search["scheduler_budget"] > search["scheduler_pool_size"]:
        raise ValueError("scheduler budget cannot exceed pool size")
    if search["scheduler_pool_size"] > 12:
        raise ValueError("QAOA statevector pool cannot exceed 12")
    if search["candidate_top_k"] < search["scheduler_pool_size"]:
        raise ValueError("candidate_top_k must cover scheduler_pool_size")
    if search["simulations"] < search["scheduler_budget"]:
        raise ValueError("simulations must visit every admitted edge")
    for name in ("redundancy_weight", "redundancy_alpha", "utility_clip"):
        value = float(search[name])
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"search.{name} must be finite and non-negative")
    if search["utility_clip"] <= 0.0 or search["redundancy_alpha"] > 1.0:
        raise ValueError("invalid scheduler clipping/alpha")
    qaoa = config["qaoa"]
    for name in ("p", "shots", "optimizer_restarts"):
        _positive_int(qaoa[name], f"qaoa.{name}")
    if not isinstance(qaoa["optimizer_steps"], int) or qaoa["optimizer_steps"] < 0:
        raise ValueError("qaoa.optimizer_steps must be a non-negative integer")
    _probability(
        qaoa["measurement_bitflip_probability"],
        "qaoa.measurement_bitflip_probability",
    )
    profile = config["native_profile"]
    if tuple(profile["native_gate_set"]) != ("rz", "sx", "x", "cx"):
        raise ValueError("native gate set must be rz/sx/x/cx")
    for name in ("one_qubit_error", "two_qubit_error", "readout_error"):
        _probability(profile[name], f"native_profile.{name}")
    for name in ("one_qubit_duration_ns", "two_qubit_duration_ns"):
        if float(profile[name]) <= 0 or not math.isfinite(float(profile[name])):
            raise ValueError(f"native_profile.{name} must be finite and positive")
    noise = config["noise_execution"]
    _positive_int(noise["shots_per_input"], "noise_execution.shots_per_input")
    if noise.get("include_output_zero_and_one") is not True:
        raise ValueError("both output-ancilla inputs are required")
    _positive_int(noise["max_trajectory_qubits"], "max_trajectory_qubits")
    if not isinstance(noise["noise_seeds"], list) or not noise["noise_seeds"]:
        raise ValueError("noise_execution.noise_seeds must be non-empty")
    for seed in noise["noise_seeds"]:
        _positive_int(seed, "noise seed")
    feedback = config["feedback_model"]
    if not feedback["ridge_alpha_grid"] or any(
        float(alpha) <= 0.0 or not math.isfinite(float(alpha))
        for alpha in feedback["ridge_alpha_grid"]
    ):
        raise ValueError("ridge_alpha_grid must contain positive finite values")
    if float(feedback["penalty_weight"]) < 0.0:
        raise ValueError("penalty_weight must be non-negative")
    _positive_int(config["statistics"]["bootstrap_resamples"], "bootstrap_resamples")
    _positive_int(config["statistics"]["bootstrap_seed"], "bootstrap_seed")
    return config


def _config_sha256(config: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(config))


def _truth_table_sha256(bf: BooleanFunction) -> str:
    byte_count = ((1 << bf.n) + 7) // 8
    payload = int(bf.truth_table).to_bytes(byte_count, "little")
    return hashlib.sha256(payload).hexdigest()


def _cases(phase: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    phase_config = config[phase]
    n = int(phase_config["n"])
    cases = []
    for index in range(int(phase_config["case_count"])):
        seed = int(phase_config["seed_base"]) + index
        bf = BooleanFunction(n, random.Random(seed).getrandbits(1 << n))
        terms = frozenset(anf_monomials(bf))
        case = {
            "case_id": f"e3-{phase}-n{n}-k{index:02d}",
            "instance_seed": seed,
            "n_declared": n,
            "truth_table_hex": canonical_hex(
                int(bf.truth_table), min_nibbles=max(1, ((1 << n) + 3) // 4)
            ),
            "truth_table_sha256": _truth_table_sha256(bf),
            "anf_term_count": len(terms),
            "bf": bf,
            "terms": terms,
        }
        cases.append(case)
    hashes = [case["truth_table_sha256"] for case in cases]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError(f"duplicate truth tables in frozen {phase} split")
    return cases


def _dataset_record(phase: str, cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "phase": phase,
        "generation": "python-random-getrandbits-frozen-seed-v1",
        "cases": [
            {
                key: case[key]
                for key in (
                    "case_id",
                    "instance_seed",
                    "n_declared",
                    "truth_table_hex",
                    "truth_table_sha256",
                    "anf_term_count",
                )
            }
            for case in cases
        ],
    }
    return {**payload, "sha256": dataset_sha256(payload)}


def _search_config(config: dict[str, Any]) -> SearchConfig:
    search = config["search"]
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        candidate_top_k=int(search["candidate_top_k"]),
        max_factor_ancilla=int(search["max_factor_ancilla"]),
        max_factor_size=int(search["max_factor_size"]),
        mcts_simulations=int(search["simulations"]),
        neural_mcts_simulations=int(search["simulations"]),
        gate_mode="mct",
    )


def _scheduler_config(
    config: dict[str, Any], variant: str, *, scheduler_seed: int
) -> DiversitySchedulerConfig:
    search = config["search"]
    qaoa = config["qaoa"]
    method = "qaoa" if "qaoa" in variant else "greedy"
    return DiversitySchedulerConfig(
        method=method,
        budget_requested=int(search["scheduler_budget"]),
        pool_size=int(search["scheduler_pool_size"]),
        min_candidates=int(search["scheduler_min_candidates"]),
        max_depth=0,
        redundancy_weight=float(search["redundancy_weight"]),
        redundancy_alpha=float(search["redundancy_alpha"]),
        utility_clip=float(search["utility_clip"]),
        seed=int(scheduler_seed),
        qaoa_mode="shot",
        qaoa_p=int(qaoa["p"]),
        qaoa_shots=int(qaoa["shots"]),
        qaoa_noise_bitflip_probability=float(
            qaoa["measurement_bitflip_probability"]
        ),
        qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
        qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
    )


def _action_payload(action: FactorAction) -> dict[str, Any]:
    return {
        "factor": int(action.factor),
        "group": sorted(int(term) for term in action.group),
        "residuals": sorted(int(term) for term in action.residuals),
        "rest": sorted(int(term) for term in action.rest),
        "immediate_gain": float(action.immediate_gain),
        "prior": float(action.prior),
        "linear": bool(action.linear),
        "affine_const": bool(action.affine_const),
    }


def _state_payload(key: StateKey) -> dict[str, Any]:
    return {
        "terms": sorted(int(term) for term in key.terms),
        "prefix_len": int(key.prefix_len),
        "live_factor_ancilla": int(key.live_factor_ancilla),
    }


def _rollout_completion_plan(
    key: StateKey, action: FactorAction, config: SearchConfig
) -> Plan:
    memo: dict[tuple[frozenset[int], int, int], Plan] = {}
    group = greedy_plan(
        action.residuals,
        key.prefix_len + 1,
        key.live_factor_ancilla + 1,
        config,
        neural_scorer=None,
        memo=memo,
    )
    rest = greedy_plan(
        action.rest,
        key.prefix_len,
        key.live_factor_ancilla,
        config,
        neural_scorer=None,
        memo=memo,
    )
    return Plan(
        "factor",
        key.terms,
        factor_cost(action, group, rest, key.live_factor_ancilla, config),
        factor=action.factor,
        group=group,
        rest=rest,
    )


def _plan_sha256(plan: Plan) -> str:
    return sha256_bytes(canonical_json_bytes(PlanTrace.from_plan(plan).to_dict()))


def _profile_spec(config: dict[str, Any]) -> dict[str, Any]:
    profile = config["native_profile"]
    noise = config["noise_execution"]
    return {
        **profile,
        "topology_generation": "heavy_hex_like_profile(n_physical)",
        "routing": "deterministic-shortest-path-swap-v1",
        "mct_decomposition": "ancilla-free-exact-parity-phase",
        "noise_execution": "seeded-statevector-pauli-trajectory-shots-v1",
        "shots_per_input": int(noise["shots_per_input"]),
        "noise_seeds": list(noise["noise_seeds"]),
        "input_contract": "all x and y in {0,1}; work ancillas initialized to zero",
    }


def _noise_model(config: dict[str, Any]) -> PauliNoiseModel:
    profile = config["native_profile"]
    return PauliNoiseModel(
        one_qubit_error=float(profile["one_qubit_error"]),
        two_qubit_error=float(profile["two_qubit_error"]),
        readout_error=float(profile["readout_error"]),
        parameter_source=str(profile["family"]),
    )


def _derived_seed(*parts: object) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _compile_and_execute(
    *,
    plan: Plan,
    case: dict[str, Any],
    search_config: SearchConfig,
    config: dict[str, Any],
    seed_namespace: str,
) -> dict[str, Any]:
    bf: BooleanFunction = case["bf"]
    terms: frozenset[int] = case["terms"]
    plan_check = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(
        plan,
        bf.n,
        min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla),
    )
    circuit_check = verify_circuit_anf(circuit, bf.n, terms)
    oracle_ok = verify_oracle(circuit, bf)
    profile_values = config["native_profile"]
    parameters = NoiseParameters(
        model="independent-pauli-depolarizing-v1",
        one_qubit_error=float(profile_values["one_qubit_error"]),
        two_qubit_error=float(profile_values["two_qubit_error"]),
        readout_error=float(profile_values["readout_error"]),
    )
    profile = heavy_hex_like_profile(circuit.n_qubits, noise=parameters)
    compilation = compile_superconducting(circuit, profile)
    equivalence = verify_basis_equivalence(
        compilation,
        max_qubits=int(config["noise_execution"]["max_trajectory_qubits"]),
    )
    native_names_ok = all(
        gate.name in tuple(profile_values["native_gate_set"])
        for gate in compilation.native_gates
    )
    coupling_ok = all(
        tuple(sorted(gate.qubits)) in profile.coupling_edges
        for gate in compilation.native_gates
        if gate.name == "cx"
    )

    model = _noise_model(config)
    shots = int(config["noise_execution"]["shots_per_input"])
    total_success = 0
    total_shots = 0
    actual_noisy_all = True
    noise_applied_all = True
    task_contract_ok = True
    event_totals = {
        "one_qubit_channel_trials": 0,
        "one_qubit_error_events": 0,
        "two_qubit_channel_trials": 0,
        "two_qubit_error_events": 0,
        "readout_channel_trials": 0,
        "readout_bit_flips": 0,
    }
    for noise_seed in config["noise_execution"]["noise_seeds"]:
        for x in range(1 << bf.n):
            for y in (0, 1):
                logical_input = tuple((x >> bit) & 1 for bit in range(bf.n)) + (
                    int(y),
                ) + (0,) * (circuit.n_qubits - bf.n - 1)
                seed = _derived_seed(
                    "e3-noise-v1", seed_namespace, noise_seed, x, y
                )
                result = simulate_noisy_shots(
                    compilation,
                    logical_input,
                    shots=shots,
                    seed=seed,
                    noise_model=model,
                    max_qubits=int(
                        config["noise_execution"]["max_trajectory_qubits"]
                    ),
                )
                desired = list(logical_input)
                desired[bf.n] ^= int(bf.evaluate(x))
                task_contract_ok &= tuple(desired) == result.expected_logical_bits
                total_success += int(result.success_count)
                total_shots += int(result.shots)
                actual_noisy_all &= bool(result.actual_noisy_simulation)
                noise_applied_all &= bool(result.noise_applied)
                for name, value in asdict(result.events).items():
                    event_totals[name] += int(value)
    smoothed_probability = (total_success + 0.5) / (total_shots + 1.0)
    nll = -math.log(smoothed_probability)
    diagnostics = compilation.diagnostics
    estimated_duration_ns = (
        diagnostics.one_qubit_gate_count
        * float(profile_values["one_qubit_duration_ns"])
        + diagnostics.two_qubit_gate_count
        * float(profile_values["two_qubit_duration_ns"])
    )
    native_qasm = native_to_openqasm3(compilation)
    return {
        "plan_anf_ok": bool(plan_check.ok),
        "circuit_anf_ok": bool(circuit_check.ok),
        "oracle_ok": bool(oracle_ok),
        "logical_gate_count": len(circuit.gates),
        "physical_qubit_count": circuit.n_qubits,
        "native": {
            "profile_name": profile.name,
            "coupling_edges": [list(edge) for edge in profile.coupling_edges],
            "native_qasm_sha256": hashlib.sha256(
                native_qasm.encode("utf-8")
            ).hexdigest(),
            "diagnostics": asdict(diagnostics),
            "estimated_duration_ns": estimated_duration_ns,
            "native_gate_names_ok": native_names_ok,
            "coupling_ok": coupling_ok,
            "ideal_equivalence": asdict(equivalence),
        },
        "noisy_execution": {
            "success_count": total_success,
            "total_shots": total_shots,
            "empirical_success_probability": total_success / total_shots,
            "jeffreys_success_probability": smoothed_probability,
            "oracle_task_nll": nll,
            "actual_noisy_simulation_all": actual_noisy_all,
            "hardware_execution": False,
            "noise_applied_all": noise_applied_all,
            "task_contract_ok": task_contract_ok,
            "noise_model": asdict(model),
            "event_totals": event_totals,
        },
    }


def _fit_metrics(
    model: RidgeExecutionCostModel,
    records: Sequence[ExecutionCalibrationRecord],
) -> dict[str, float]:
    targets = np.asarray([record.execution_cost for record in records], dtype=float)
    predictions = np.asarray(
        [
            model.predict(record.state_key, (record.action,))[0]
            for record in records
        ],
        dtype=float,
    )
    residual = targets - predictions
    denominator = float(((targets - targets.mean()) ** 2).sum())
    r2 = 1.0 - float((residual**2).sum()) / denominator if denominator > 0 else 0.0

    def ranks(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="mergesort")
        result = np.empty(len(values), dtype=float)
        start = 0
        while start < len(values):
            stop = start + 1
            while stop < len(values) and values[order[stop]] == values[order[start]]:
                stop += 1
            result[order[start:stop]] = 0.5 * (start + stop - 1)
            start = stop
        return result

    target_ranks = ranks(targets)
    prediction_ranks = ranks(predictions)
    if np.std(target_ranks) == 0 or np.std(prediction_ranks) == 0:
        spearman = 0.0
    else:
        spearman = float(np.corrcoef(target_ranks, prediction_ranks)[0, 1])
    return {
        "mae": float(np.abs(residual).mean()),
        "rmse": float(np.sqrt((residual**2).mean())),
        "r2": r2,
        "spearman": spearman,
    }


def _select_ridge_alpha(
    records: Sequence[ExecutionCalibrationRecord],
    case_ids: Sequence[str],
    config: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    alphas = [float(value) for value in config["feedback_model"]["ridge_alpha_grid"]]
    unique_cases = sorted(set(case_ids))
    if len(unique_cases) < 2:
        return alphas[0], {
            "method": "unavailable-single-case-tiny",
            "selected_alpha": alphas[0],
            "scores": [],
        }
    scores = []
    for alpha in alphas:
        absolute_errors: list[float] = []
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
            if not train or not validation:
                continue
            model = RidgeExecutionCostModel(
                ridge_alpha=alpha,
                penalty_weight=float(config["feedback_model"]["penalty_weight"]),
            ).fit(train)
            for record in validation:
                prediction = float(model.predict(record.state_key, (record.action,))[0])
                absolute_errors.append(abs(prediction - record.execution_cost))
        scores.append(
            {
                "ridge_alpha": alpha,
                "grouped_leave_one_case_out_mae": statistics.mean(absolute_errors),
                "validation_observations": len(absolute_errors),
            }
        )
    selected = min(
        scores,
        key=lambda item: (
            item["grouped_leave_one_case_out_mae"],
            item["ridge_alpha"],
        ),
    )
    return float(selected["ridge_alpha"]), {
        "method": "leave-one-function-out-mae",
        "selected_alpha": float(selected["ridge_alpha"]),
        "scores": scores,
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
    claim_boundary: str,
) -> dict[str, Any]:
    manifest = ExperimentManifest(
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
        variants=("calibration",) if phase == "calibration" else VARIANTS,
        expected_artifacts=EXPECTED_ARTIFACTS,
        counts=counts,
        timing=timing,
        claim_boundary=claim_boundary,
    ).to_dict()
    manifest["phase"] = phase
    return manifest


def run_calibration(
    *,
    config: dict[str, Any],
    out_dir: Path,
    run_id: str,
    tiny: bool,
    config_path: Path,
) -> Path:
    created_at = utc_now()
    started = time.perf_counter()
    checkpoint = (PROJECT_ROOT / config["checkpoint"]).resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    cases = _cases("calibration", config)
    dataset = _dataset_record("calibration", cases)
    search_config = _search_config(config)
    profile_spec = _profile_spec(config)
    profile_sha = sha256_bytes(canonical_json_bytes(profile_spec))
    raw: list[dict[str, Any]] = [
        {
            "schema_version": CALIBRATION_SCHEMA,
            "record_type": "profile_audit",
            "profile": profile_spec,
            "profile_sha256": profile_sha,
        }
    ]
    events: list[dict[str, Any]] = [
        {"event": "calibration_started", "at_utc": created_at, "run_id": run_id}
    ]
    records: list[ExecutionCalibrationRecord] = []
    record_case_ids: list[str] = []
    candidate_rows: list[dict[str, Any]] = []

    for case in cases:
        events.append({"event": "case_started", "case_id": case["case_id"]})
        scorer = FoundationScorer.from_checkpoint(checkpoint)
        key = StateKey(case["terms"], 0, 0)
        probe = NeuralMCTSSolver(
            search_config,
            simulations=0,
            seed=0,
            neural_scorer=scorer,
            rollout_scorer=None,
        )
        node = probe._node(key)
        probe._expand(node)
        actions = tuple(node.actions[: int(config["search"]["scheduler_pool_size"])])
        raw.append(
            {
                "schema_version": CALIBRATION_SCHEMA,
                "record_type": "calibration_case",
                **{
                    key_name: case[key_name]
                    for key_name in (
                        "case_id",
                        "instance_seed",
                        "n_declared",
                        "truth_table_hex",
                        "truth_table_sha256",
                        "anf_term_count",
                    )
                },
                "candidate_count": len(actions),
                "case_retained_without_resampling": True,
            }
        )
        for action_index, action in enumerate(actions):
            plan = _rollout_completion_plan(key, action, search_config)
            execution = _compile_and_execute(
                plan=plan,
                case=case,
                search_config=search_config,
                config=config,
                seed_namespace=f"cal:{case['case_id']}:a{action_index}",
            )
            calibration_id = f"{case['case_id']}:a{action_index:02d}"
            record = ExecutionCalibrationRecord(
                calibration_id=calibration_id,
                state_key=key,
                action=action,
                execution_cost=float(execution["noisy_execution"]["oracle_task_nll"]),
            )
            records.append(record)
            record_case_ids.append(case["case_id"])
            row = {
                "schema_version": CALIBRATION_SCHEMA,
                "record_type": "calibration_observation",
                "calibration_id": calibration_id,
                "case_id": case["case_id"],
                "state": _state_payload(key),
                "action_index": action_index,
                "action": _action_payload(action),
                "rollout_plan_sha256": _plan_sha256(plan),
                "logical_score": plan.score(search_config.weights),
                "resource_cost": asdict(plan.cost),
                **execution,
            }
            candidate_rows.append(row)
            raw.append(row)
        events.append(
            {
                "event": "case_completed",
                "case_id": case["case_id"],
                "candidate_count": len(actions),
            }
        )

    if not records:
        raise RuntimeError("calibration produced no root actions")
    selected_alpha, grouped_cv = _select_ridge_alpha(
        records, record_case_ids, config
    )
    model = RidgeExecutionCostModel(
        ridge_alpha=selected_alpha,
        penalty_weight=float(config["feedback_model"]["penalty_weight"]),
    ).fit(records)
    metadata = model.metadata()
    fit_metrics = _fit_metrics(model, records)
    raw.append(
        {
            "schema_version": CALIBRATION_SCHEMA,
            "record_type": "feedback_fit",
            "model_metadata": metadata,
            "grouped_cross_validation": grouped_cv,
            "calibration_fit_metrics": fit_metrics,
        }
    )
    checks = {
        "dataset_truth_tables_unique": len(
            {case["truth_table_sha256"] for case in cases}
        )
        == len(cases),
        "all_cases_retained": len(cases) == int(config["calibration"]["case_count"]),
        "calibration_observations_present": bool(candidate_rows),
        "all_plan_anf_ok": all(row["plan_anf_ok"] for row in candidate_rows),
        "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in candidate_rows),
        "all_oracle_ok": all(row["oracle_ok"] for row in candidate_rows),
        "all_native_ideal_equivalent": all(
            row["native"]["ideal_equivalence"]["equivalent"]
            for row in candidate_rows
        ),
        "all_native_gates_whitelisted": all(
            row["native"]["native_gate_names_ok"] for row in candidate_rows
        ),
        "all_cx_coupled": all(row["native"]["coupling_ok"] for row in candidate_rows),
        "all_noise_runs_actual": all(
            row["noisy_execution"]["actual_noisy_simulation_all"]
            for row in candidate_rows
        ),
        "all_noise_applied": all(
            row["noisy_execution"]["noise_applied_all"] for row in candidate_rows
        ),
        "all_task_contracts_ok": all(
            row["noisy_execution"]["task_contract_ok"] for row in candidate_rows
        ),
        "all_probabilities_finite": all(
            math.isfinite(row["noisy_execution"]["jeffreys_success_probability"])
            and 0.0 < row["noisy_execution"]["jeffreys_success_probability"] < 1.0
            for row in candidate_rows
        ),
        "model_calibration_count_matches": int(metadata["calibration_count"])
        == len(records),
        "model_sha_present": len(str(metadata["model_sha256"])) == 64,
    }
    integrity_ok = all(checks.values())
    claim_boundary = (
        "Tiny contract smoke; no performance claim. " if tiny else ""
    ) + str(config["claim_boundary"])
    summary = {
        "schema_version": CALIBRATION_SCHEMA,
        "phase": "calibration",
        "run_id": run_id,
        "tiny": tiny,
        "config_sha256": _config_sha256(config),
        "dataset_sha256": dataset["sha256"],
        "truth_table_sha256": [case["truth_table_sha256"] for case in cases],
        "profile": profile_spec,
        "profile_sha256": profile_sha,
        "case_count": len(cases),
        "calibration_observation_count": len(records),
        "cases_with_no_actions": sum(
            1
            for row in raw
            if row.get("record_type") == "calibration_case"
            and row.get("candidate_count") == 0
        ),
        "grouped_cross_validation": grouped_cv,
        "calibration_fit_metrics": fit_metrics,
        "model_metadata": metadata,
        "model_sha256": metadata["model_sha256"],
        "calibration_sha256": metadata["calibration_sha256"],
        "integrity_ok": integrity_ok,
        "claim_boundary": claim_boundary,
    }
    verifier = {
        "schema_version": "xa.e3-native-feedback-verifier.v1",
        "phase": "calibration",
        "run_id": run_id,
        "ok": integrity_ok,
        "checks": checks,
        "failure_denominators": {
            "cases": len(cases),
            "observations": len(candidate_rows),
        },
    }
    elapsed = time.perf_counter() - started
    events.append(
        {"event": "calibration_completed", "run_id": run_id, "elapsed_s": elapsed}
    )
    run_record = _manifest(
        run_id=run_id,
        phase="calibration",
        status="complete" if integrity_ok else "failed",
        created_at=created_at,
        dataset=dataset,
        config=config,
        checkpoint=checkpoint,
        counts={"cases": len(cases), "observations": len(records)},
        timing={"wall_s": elapsed},
        command={
            "subcommand": "calibrate",
            "config": str(config_path),
            "tiny": tiny,
        },
        claim_boundary=claim_boundary,
    )
    run_dir = out_dir / run_id
    verification = write_pilot_bundle(
        run_dir=run_dir,
        run_record=run_record,
        raw_records=raw,
        summary=summary,
        verifier=verifier,
        events=events,
        track=TRACK,
    )
    if not verification.ok:
        raise RuntimeError(f"calibration bundle verification failed: {verification.errors}")
    print(f"calibration_bundle={run_dir}")
    print(f"observations={len(records)} model_sha256={metadata['model_sha256']}")
    return run_dir


def _qaoa_direct(diagnostics: dict[str, Any]) -> bool:
    qaoa = diagnostics.get("qaoa")
    nested = qaoa.get("diagnostics", {}) if isinstance(qaoa, dict) else {}
    return bool(
        diagnostics.get("qaoa_succeeded")
        and not diagnostics.get("qaoa_repaired")
        and not diagnostics.get("qaoa_fallback")
        and isinstance(nested, dict)
        and nested.get("direct_qaoa")
    )


def _qaoa_not_invoked(variant: str, status: str) -> bool:
    """Keep classical no-action rows outside the QAOA outcome partition."""

    return "qaoa" in variant and status in {
        "qaoa_not_invoked",
        "not_applicable_no_actions",
    }


def _bootstrap_ci(
    values: Sequence[float], *, seed: int, resamples: int
) -> tuple[float, float]:
    if not values:
        raise ValueError("bootstrap input must be non-empty")
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = random.Random(seed)
    means = sorted(
        statistics.mean(values[rng.randrange(len(values))] for _ in values)
        for _ in range(resamples)
    )
    return (
        float(means[int(0.025 * (resamples - 1))]),
        float(means[int(0.975 * (resamples - 1))]),
    )


def _test_statistics(
    trials: Sequence[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    by_variant: dict[str, Any] = {}
    for variant in VARIANTS:
        rows = [row for row in trials if row["variant"] == variant]
        by_variant[variant] = {
            "trial_count": len(rows),
            "oracle_task_nll_mean": statistics.mean(
                row["noisy_execution"]["oracle_task_nll"] for row in rows
            ),
            "jeffreys_success_probability_mean": statistics.mean(
                row["noisy_execution"]["jeffreys_success_probability"]
                for row in rows
            ),
            "logical_score_mean": statistics.mean(row["logical_score"] for row in rows),
            "native_2q_count_mean": statistics.mean(
                row["native"]["diagnostics"]["two_qubit_gate_count"] for row in rows
            ),
            "native_depth_mean": statistics.mean(
                row["native"]["diagnostics"]["native_depth"] for row in rows
            ),
            "qaoa": {
                "attempted": sum(row["qaoa_attempted"] for row in rows),
                "succeeded": sum(row["qaoa_succeeded"] for row in rows),
                "direct_nonfallback": sum(row["qaoa_direct_nonfallback"] for row in rows),
                "repaired": sum(row["qaoa_repaired"] for row in rows),
                "fallback": sum(row["qaoa_fallback"] for row in rows),
                "not_invoked": sum(row["qaoa_not_invoked"] for row in rows),
            },
        }

    case_ids = sorted({row["case_id"] for row in trials})
    case_diffs: list[float] = []
    case_log_ratios: list[float] = []
    case_rows = []
    for case_id in case_ids:
        historical = [
            row
            for row in trials
            if row["case_id"] == case_id
            and row["variant"] == "historical_qaoa_shot"
        ]
        feedback = [
            row
            for row in trials
            if row["case_id"] == case_id
            and row["variant"] == "feedback_qaoa_shot"
        ]
        historical_nll = statistics.mean(
            row["noisy_execution"]["oracle_task_nll"] for row in historical
        )
        feedback_nll = statistics.mean(
            row["noisy_execution"]["oracle_task_nll"] for row in feedback
        )
        historical_log_p = statistics.mean(
            math.log(row["noisy_execution"]["jeffreys_success_probability"])
            for row in historical
        )
        feedback_log_p = statistics.mean(
            math.log(row["noisy_execution"]["jeffreys_success_probability"])
            for row in feedback
        )
        delta = feedback_nll - historical_nll
        log_ratio = feedback_log_p - historical_log_p
        case_diffs.append(delta)
        case_log_ratios.append(log_ratio)
        case_rows.append(
            {
                "case_id": case_id,
                "historical_qaoa_nll": historical_nll,
                "feedback_qaoa_nll": feedback_nll,
                "delta_nll_feedback_minus_historical": delta,
                "success_probability_ratio_feedback_over_historical": math.exp(
                    log_ratio
                ),
            }
        )
    bootstrap = config["statistics"]
    diff_ci = _bootstrap_ci(
        case_diffs,
        seed=int(bootstrap["bootstrap_seed"]),
        resamples=int(bootstrap["bootstrap_resamples"]),
    )
    ratio_log_ci = _bootstrap_ci(
        case_log_ratios,
        seed=int(bootstrap["bootstrap_seed"]) + 1,
        resamples=int(bootstrap["bootstrap_resamples"]),
    )
    tolerance = 1e-12
    primary = {
        "comparison": "feedback_qaoa_shot_vs_historical_qaoa_shot",
        "independent_unit": "Boolean function",
        "function_clusters": len(case_ids),
        "delta_nll_mean": statistics.mean(case_diffs),
        "delta_nll_ci95": list(diff_ci),
        "geometric_success_probability_ratio": math.exp(
            statistics.mean(case_log_ratios)
        ),
        "geometric_success_probability_ratio_ci95": [
            math.exp(ratio_log_ci[0]),
            math.exp(ratio_log_ci[1]),
        ],
        "wlt_by_function": {
            "wins": sum(value < -tolerance for value in case_diffs),
            "losses": sum(value > tolerance for value in case_diffs),
            "ties": sum(abs(value) <= tolerance for value in case_diffs),
        },
        "case_rows": case_rows,
    }
    primary["claim_supported_by_ci"] = bool(
        primary["delta_nll_ci95"][1] < 0.0
        and primary["geometric_success_probability_ratio_ci95"][0] > 1.0
    )
    return {"variants": by_variant, "primary_comparison": primary}


def run_test(
    *,
    config: dict[str, Any],
    calibration_run: Path,
    out_dir: Path,
    run_id: str,
    tiny: bool,
    config_path: Path,
) -> Path:
    created_at = utc_now()
    started = time.perf_counter()
    calibration_verification = verify_bundle(
        calibration_run,
        required_roles=("run", "raw", "summary", "verifier", "events", "stdout", "stderr"),
    )
    if not calibration_verification.ok:
        raise ValueError(
            f"calibration bundle failed verification: {calibration_verification.errors}"
        )
    calibration_summary_path = calibration_run / "summary.json"
    calibration_summary = json.loads(
        calibration_summary_path.read_text(encoding="utf-8")
    )
    if calibration_summary.get("phase") != "calibration":
        raise ValueError("calibration_run does not contain a calibration summary")
    if calibration_summary.get("config_sha256") != _config_sha256(config):
        raise ValueError("test config does not match frozen calibration config")
    metadata = calibration_summary["model_metadata"]
    feedback_model = RidgeExecutionCostModel.from_metadata(
        metadata,
        penalty_weight=float(config["feedback_model"]["penalty_weight"]),
        expected_calibration_sha256=str(calibration_summary["calibration_sha256"]),
    )
    checkpoint = (PROJECT_ROOT / config["checkpoint"]).resolve()
    cases = _cases("test", config)
    dataset = _dataset_record("test", cases)
    calibration_hashes = set(calibration_summary["truth_table_sha256"])
    test_hashes = {case["truth_table_sha256"] for case in cases}
    if calibration_hashes & test_hashes:
        raise RuntimeError("calibration/test truth-table overlap")
    search_config = _search_config(config)
    profile_spec = _profile_spec(config)
    profile_sha = sha256_bytes(canonical_json_bytes(profile_spec))
    if profile_sha != calibration_summary["profile_sha256"]:
        raise ValueError("native/noise profile differs from calibration")
    calibration_summary_sha = sha256_file(calibration_summary_path)
    raw: list[dict[str, Any]] = [
        {
            "schema_version": TEST_SCHEMA,
            "record_type": "calibration_reference",
            "calibration_run_id": calibration_summary["run_id"],
            "calibration_summary_sha256": calibration_summary_sha,
            "calibration_dataset_sha256": calibration_summary["dataset_sha256"],
            "calibration_sha256": calibration_summary["calibration_sha256"],
            "feedback_model_sha256": calibration_summary["model_sha256"],
            "profile_sha256": profile_sha,
            "model_loaded_without_refit": True,
        }
    ]
    events: list[dict[str, Any]] = [
        {"event": "test_started", "at_utc": created_at, "run_id": run_id}
    ]
    trials: list[dict[str, Any]] = []

    for case_index, case in enumerate(cases):
        for solver_seed in config["test"]["solver_seeds"]:
            for variant in VARIANTS:
                scorer = FoundationScorer.from_checkpoint(checkpoint)
                scheduler_seed = 2026090300 + int(solver_seed)
                scheduler = _scheduler_config(
                    config, variant, scheduler_seed=scheduler_seed
                )
                solver = NeuralMCTSSolver(
                    search_config,
                    simulations=int(config["search"]["simulations"]),
                    seed=int(solver_seed),
                    neural_scorer=scorer,
                    value_estimator=None,
                    rollout_scorer=None,
                    scheduler_config=scheduler,
                    execution_utility_adjuster=(
                        feedback_model if variant.startswith("feedback_") else None
                    ),
                )
                solve_started = time.perf_counter()
                plan = solver.solve(case["terms"])
                solve_elapsed = time.perf_counter() - solve_started
                root_key = StateKey(case["terms"], 0, 0)
                root = solver.nodes[root_key]
                pool_actions = tuple(
                    root.actions[: int(config["search"]["scheduler_pool_size"])]
                )
                pool_payload = [_action_payload(action) for action in pool_actions]
                pool_sha = sha256_bytes(canonical_json_bytes(pool_payload))
                rollout_plan_hashes = [
                    _plan_sha256(
                        _rollout_completion_plan(root_key, action, search_config)
                    )
                    for action in pool_actions
                ]
                diagnostics = (
                    dict(root.scheduler_decision.diagnostics)
                    if root.scheduler_decision is not None
                    else {}
                )
                selected = tuple(root.admitted_indices or ())
                selected_set = set(selected)
                excluded_visits = sum(
                    stats.visits
                    for index, stats in root.stats.items()
                    if index not in selected_set
                ) if root.admitted_indices is not None else 0
                execution = _compile_and_execute(
                    plan=plan,
                    case=case,
                    search_config=search_config,
                    config=config,
                    seed_namespace=(
                        f"test:{case['case_id']}:solver{solver_seed}"
                    ),
                )
                status = str(diagnostics.get("status", "not_applicable_no_actions"))
                row = {
                    "schema_version": TEST_SCHEMA,
                    "record_type": "feedback_trial",
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "case_index": case_index,
                    "instance_seed": case["instance_seed"],
                    "n_declared": case["n_declared"],
                    "truth_table_hex": case["truth_table_hex"],
                    "truth_table_sha256": case["truth_table_sha256"],
                    "anf_term_count": case["anf_term_count"],
                    "solver_seed": int(solver_seed),
                    "scheduler_seed": scheduler_seed,
                    "variant": variant,
                    "utility_mode": (
                        "frozen_execution_feedback"
                        if variant.startswith("feedback_")
                        else "historical_logical"
                    ),
                    "scheduler_method": scheduler.method,
                    "candidate_count": len(pool_actions),
                    "candidate_pool_sha256": pool_sha,
                    "candidate_action_payloads": pool_payload,
                    "candidate_rollout_plan_sha256": rollout_plan_hashes,
                    "raw_utilities": list(diagnostics.get("raw_utilities", [])),
                    "adjusted_utilities": list(
                        diagnostics.get("adjusted_utilities", [])
                    ),
                    "selected_indices": list(selected),
                    "selected_action_visits": [
                        root.stats[index].visits for index in selected
                    ],
                    "excluded_action_visits_total": excluded_visits,
                    "scheduler_status": status,
                    "scheduler_diagnostics": diagnostics,
                    "feedback_model_sha256": (
                        metadata["model_sha256"]
                        if variant.startswith("feedback_")
                        else None
                    ),
                    "feedback_loaded_without_refit": variant.startswith("feedback_"),
                    "test_noisy_outcome_used_by_utility": False,
                    "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
                    "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
                    "qaoa_direct_nonfallback": _qaoa_direct(diagnostics),
                    "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
                    "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
                    "qaoa_not_invoked": _qaoa_not_invoked(variant, status),
                    "plan_sha256": _plan_sha256(plan),
                    "logical_score": plan.score(search_config.weights),
                    "resource_cost": asdict(plan.cost),
                    "search_nodes": len(solver.nodes),
                    "root_visits": root.visits,
                    "solve_elapsed_s": solve_elapsed,
                    **execution,
                }
                trials.append(row)
                raw.append(row)
        events.append({"event": "case_completed", "case_id": case["case_id"]})

    statistics_payload = _test_statistics(trials, config)
    primary = statistics_payload["primary_comparison"]
    for row in primary["case_rows"]:
        raw.append(
            {
                "schema_version": TEST_SCHEMA,
                "record_type": "paired_comparison",
                **row,
            }
        )
    group_keys = sorted(
        {
            (row["case_id"], row["solver_seed"])
            for row in trials
        }
    )
    pool_match = all(
        len(
            {
                row["candidate_pool_sha256"]
                for row in trials
                if (row["case_id"], row["solver_seed"]) == key
            }
        )
        == 1
        for key in group_keys
    )
    rollout_match = all(
        len(
            {
                tuple(row["candidate_rollout_plan_sha256"])
                for row in trials
                if (row["case_id"], row["solver_seed"]) == key
            }
        )
        == 1
        for key in group_keys
    )
    raw_utility_match = all(
        len(
            {
                tuple(row["raw_utilities"])
                for row in trials
                if (row["case_id"], row["solver_seed"]) == key
            }
        )
        == 1
        for key in group_keys
    )
    expected_trials = (
        len(cases) * len(config["test"]["solver_seeds"]) * len(VARIANTS)
    )
    checks = {
        "calibration_bundle_verified": calibration_verification.ok,
        "calibration_model_loaded_without_refit": True,
        "calibration_model_sha_matches": feedback_model.metadata()["model_sha256"]
        == calibration_summary["model_sha256"],
        "calibration_profile_sha_matches": profile_sha
        == calibration_summary["profile_sha256"],
        "calibration_test_truth_tables_disjoint": not (
            calibration_hashes & test_hashes
        ),
        "test_truth_tables_unique": len(test_hashes) == len(cases),
        "case_seed_variant_matrix_complete": len(trials) == expected_trials,
        "same_candidate_pool_within_pair": pool_match,
        "same_rollout_plans_within_pair": rollout_match,
        "same_raw_utilities_within_pair": raw_utility_match,
        "test_outcome_never_used_by_utility": all(
            row["test_noisy_outcome_used_by_utility"] is False for row in trials
        ),
        "feedback_rows_bind_frozen_model": all(
            row["feedback_model_sha256"] == calibration_summary["model_sha256"]
            for row in trials
            if row["variant"].startswith("feedback_")
        ),
        "all_plan_anf_ok": all(row["plan_anf_ok"] for row in trials),
        "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in trials),
        "all_oracle_ok": all(row["oracle_ok"] for row in trials),
        "all_native_ideal_equivalent": all(
            row["native"]["ideal_equivalence"]["equivalent"] for row in trials
        ),
        "all_native_gates_whitelisted": all(
            row["native"]["native_gate_names_ok"] for row in trials
        ),
        "all_cx_coupled": all(row["native"]["coupling_ok"] for row in trials),
        "all_noise_runs_actual": all(
            row["noisy_execution"]["actual_noisy_simulation_all"] for row in trials
        ),
        "all_noise_applied": all(
            row["noisy_execution"]["noise_applied_all"] for row in trials
        ),
        "all_task_contracts_ok": all(
            row["noisy_execution"]["task_contract_ok"] for row in trials
        ),
        "excluded_scheduled_edges_zero_visits": all(
            row["excluded_action_visits_total"] == 0 for row in trials
        ),
        "qaoa_outcomes_mutually_exclusive": all(
            sum(
                bool(row[name])
                for name in (
                    "qaoa_direct_nonfallback",
                    "qaoa_repaired",
                    "qaoa_fallback",
                    "qaoa_not_invoked",
                )
            )
            == (1 if "qaoa" in row["variant"] else 0)
            for row in trials
        ),
        "all_probabilities_finite": all(
            math.isfinite(row["noisy_execution"]["oracle_task_nll"])
            and 0.0 < row["noisy_execution"]["jeffreys_success_probability"] < 1.0
            for row in trials
        ),
    }
    integrity_ok = all(checks.values())
    primary["claim_supported"] = bool(
        primary["claim_supported_by_ci"] and integrity_ok and not tiny
    )
    claim_boundary = (
        "Tiny contract smoke; no performance claim. " if tiny else ""
    ) + str(config["claim_boundary"])
    summary = {
        "schema_version": TEST_SCHEMA,
        "phase": "test",
        "run_id": run_id,
        "tiny": tiny,
        "config_sha256": _config_sha256(config),
        "dataset_sha256": dataset["sha256"],
        "truth_table_sha256": sorted(test_hashes),
        "profile_sha256": profile_sha,
        "calibration_reference": {
            "run_id": calibration_summary["run_id"],
            "summary_sha256": calibration_summary_sha,
            "dataset_sha256": calibration_summary["dataset_sha256"],
            "calibration_sha256": calibration_summary["calibration_sha256"],
            "model_sha256": calibration_summary["model_sha256"],
        },
        "case_count": len(cases),
        "trial_count": len(trials),
        "variants": list(VARIANTS),
        "statistics": statistics_payload,
        "integrity_ok": integrity_ok,
        "claim_boundary": claim_boundary,
    }
    verifier = {
        "schema_version": "xa.e3-native-feedback-verifier.v1",
        "phase": "test",
        "run_id": run_id,
        "ok": integrity_ok,
        "checks": checks,
        "failure_denominators": {
            "cases": len(cases),
            "trials": len(trials),
            "native_equivalence_failures": sum(
                not row["native"]["ideal_equivalence"]["equivalent"]
                for row in trials
            ),
        },
    }
    elapsed = time.perf_counter() - started
    events.append({"event": "test_completed", "run_id": run_id, "elapsed_s": elapsed})
    run_record = _manifest(
        run_id=run_id,
        phase="test",
        status="complete" if integrity_ok else "failed",
        created_at=created_at,
        dataset=dataset,
        config=config,
        checkpoint=checkpoint,
        counts={"cases": len(cases), "trials": len(trials)},
        timing={"wall_s": elapsed},
        command={
            "subcommand": "test",
            "config": str(config_path),
            "calibration_run": str(calibration_run),
            "tiny": tiny,
        },
        claim_boundary=claim_boundary,
    )
    run_record["calibration_reference"] = summary["calibration_reference"]
    run_dir = out_dir / run_id
    verification = write_pilot_bundle(
        run_dir=run_dir,
        run_record=run_record,
        raw_records=raw,
        summary=summary,
        verifier=verifier,
        events=events,
        track=TRACK,
    )
    if not verification.ok:
        raise RuntimeError(f"test bundle verification failed: {verification.errors}")
    print(f"test_bundle={run_dir}")
    print(
        "primary_delta_nll="
        f"{primary['delta_nll_mean']:.6f} "
        f"ci95={primary['delta_nll_ci95']} "
        f"claim_supported={primary['claim_supported']}"
    )
    return run_dir


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    for phase in ("calibrate", "test"):
        child = subparsers.add_parser(phase)
        child.add_argument(
            "--config",
            type=Path,
            default=PROJECT_ROOT / "configs" / "xa202609" / "e3_native_feedback_v1.json",
        )
        child.add_argument(
            "--out-dir",
            type=Path,
            default=PROJECT_ROOT / "results" / "xa202609",
        )
        child.add_argument("--run-id", default=None)
        child.add_argument("--tiny", action="store_true")
        if phase == "test":
            child.add_argument("--calibration-run", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _args()
    torch.set_num_threads(1)
    config_path = args.config.expanduser().resolve()
    config = load_config(config_path, tiny=bool(args.tiny))
    started_at = utc_now()
    phase_label = "cal" if args.phase == "calibrate" else "test"
    split_seed = config["calibration" if args.phase == "calibrate" else "test"][
        "seed_base"
    ]
    run_id = args.run_id or (
        f"{started_at[:10].replace('-', '')}-{started_at[11:19].replace(':', '')}"
        f"-e3-{phase_label}-{'tiny' if args.tiny else 'native-feedback-v1'}-s{split_seed}"
    )
    out_dir = args.out_dir.expanduser().resolve()
    if args.phase == "calibrate":
        run_calibration(
            config=config,
            out_dir=out_dir,
            run_id=run_id,
            tiny=bool(args.tiny),
            config_path=config_path,
        )
    else:
        run_test(
            config=config,
            calibration_run=args.calibration_run.expanduser().resolve(),
            out_dir=out_dir,
            run_id=run_id,
            tiny=bool(args.tiny),
            config_path=config_path,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
