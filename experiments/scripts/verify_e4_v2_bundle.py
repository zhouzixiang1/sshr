#!/usr/bin/env python3
"""Independently recompute E4-v2 calibration or frozen AES replication contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402

from src.anf_utils import anf_monomials  # noqa: E402
from src.benchmarks.crypto_oracles import get_crypto_oracle_coordinates  # noqa: E402
from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file  # noqa: E402
from src.contracts.search import PlanTrace  # noqa: E402
from src.factor_plan import (  # noqa: E402
    FactorAction,
    Plan,
    SearchConfig,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.hardware.noise import PauliNoiseModel, simulate_noisy_shots  # noqa: E402
from src.hardware.qasm import circuit_to_logical_ir, export_openqasm3  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    native_to_openqasm3,
)
from src.foundation.adapter import FoundationScorer, TermThresholdPolicyScorer  # noqa: E402
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceCost, ResourceWeights  # noqa: E402
from src.search.execution_aware_utility import (  # noqa: E402
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    complete_root_action_rollout,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.mcts_scheduler import DiversitySchedulerConfig, action_redundancy_matrix  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction, Gate, QuantumCircuit  # noqa: E402


REQUIRED_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")
EXPECTED_FILES = {
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
VARIANTS = (
    "historical_greedy",
    "execution_aware_greedy",
    "historical_qaoa_shot",
    "execution_aware_qaoa_shot",
)
FEATURES = (
    "native_one_qubit",
    "native_two_qubit",
    "inserted_swap",
    "native_depth",
    "duration_ns",
    "model_risk",
)
PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
PROTOCOL_LOCK_SCHEMA = "xa.e4-v2-local-protocol-lock.v1"


def _enforce_compute_contract(config: dict[str, Any]) -> dict[str, Any]:
    """Independently establish the frozen inference environment."""

    expected = {
        "torch_device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    if config.get("compute_contract") != expected:
        raise ValueError("bundle compute contract differs from the frozen contract")
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError as exc:
            raise RuntimeError(
                "cannot establish frozen torch inter-op thread count before verification"
            ) from exc
    if torch.get_num_threads() != 1:
        torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    observed = {
        "torch_device": "cpu",
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "torch_deterministic_algorithms": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
    }
    if observed != expected:
        raise RuntimeError("failed to establish frozen E4-v2 compute contract")
    return observed


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"raw.jsonl line {number} must be an object")
        rows.append(value)
    return rows


def _truth_table_sha256(bf: BooleanFunction) -> str:
    byte_count = ((1 << bf.n) + 7) // 8
    return hashlib.sha256(int(bf.truth_table).to_bytes(byte_count, "little")).hexdigest()


def _profile_spec(config: dict[str, Any]) -> SyntheticExecutionProfileSpec:
    raw = config["native_profile"]
    return SyntheticExecutionProfileSpec(
        one_qubit_duration_ns=float(raw["one_qubit_duration_ns"]),
        two_qubit_duration_ns=float(raw["two_qubit_duration_ns"]),
        noise=NoiseParameters(
            model="independent-pauli-depolarizing-v1",
            one_qubit_error=float(raw["one_qubit_error"]),
            two_qubit_error=float(raw["two_qubit_error"]),
            readout_error=float(raw["readout_error"]),
        ),
    )


def _frozen_concrete_profile(
    config: dict[str, Any], profile_spec: SyntheticExecutionProfileSpec
) -> tuple[dict[str, Any], str]:
    profile = profile_spec.build(int(config["native_profile"]["frozen_n_qubits"]))
    payload = {
        "name": profile.name,
        "topology_family": profile.topology_family,
        "n_qubits": profile.n_qubits,
        "coupling_edges": [list(edge) for edge in profile.coupling_edges],
        "native_gate_set": list(profile.native_gate_set),
        "noise": asdict(profile.noise),
        "synthetic": profile.synthetic,
        "calibration_source": profile.calibration_source,
    }
    return payload, sha256_bytes(canonical_json_bytes(payload))


def _calibration_protocol(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": config["schema_version"],
        "experiment": config["experiment"],
        "experiment_role": config["experiment_role"],
        "dataset_role": config["dataset_role"],
        "historically_seen_in_E4": config["historically_seen_in_E4"],
        "generalization_claim": config["generalization_claim"],
        "protocol_lock": config["protocol_lock"],
        "compute_contract": config["compute_contract"],
        "checkpoint": config["checkpoint"],
        "calibration": config["calibration"],
        "search": config["search"],
        "qaoa": config["qaoa"],
        "native_profile": config["native_profile"],
        "weight_selection": config["weight_selection"],
    }


def _protocol_lock_ok(
    run: dict[str, Any], summary: dict[str, Any], config: dict[str, Any]
) -> bool:
    try:
        frozen = summary["protocol_lock"]
        if not isinstance(frozen, dict):
            return False
        lock_sha = sha256_bytes(canonical_json_bytes(frozen))
        if (
            lock_sha != summary.get("protocol_lock_sha256")
            or lock_sha != run.get("protocol_lock_sha256")
            or frozen != run.get("config", {}).get("protocol_lock")
            or lock_sha != run.get("config", {}).get("protocol_lock_sha256")
        ):
            return False
        if (
            frozen.get("schema_version") != PROTOCOL_LOCK_SCHEMA
            or frozen.get("freeze_semantics") != "locally_frozen_prior_to_run"
            or frozen.get("experiment_role") != "frozen_replication"
            or frozen.get("dataset_role")
            != "post_e4_frozen_aes_replication"
            or frozen.get("historically_seen_in_E4") is not True
            or frozen.get("generalization_claim") is not False
            or frozen.get("compute_contract") != config.get("compute_contract")
            or frozen.get("compute_contract_sha256")
            != sha256_bytes(canonical_json_bytes(config.get("compute_contract")))
        ):
            return False
        canonical = frozen["config"]["canonical_payload"]
        canonical_config_path = PROJECT_ROOT / str(frozen["config"]["path"])
        if (
            frozen["config"]["path"]
            != "configs/xa202609/e4_v2_execution_aware_v1.json"
            or frozen["config"]["canonical_sha256"]
            != sha256_bytes(canonical_json_bytes(canonical))
            or not canonical_config_path.is_file()
            or canonical != _read_json(canonical_config_path)
            or canonical.get("primary_endpoint") != config.get("primary_endpoint")
            or canonical.get("dataset_role") != config.get("dataset_role")
        ):
            return False
        endpoint = frozen["primary_endpoint"]
        if (
            endpoint != config["primary_endpoint"]
            or frozen["primary_endpoint_sha256"]
            != sha256_bytes(canonical_json_bytes(endpoint))
        ):
            return False
        model = frozen["model"]
        if (
            model["path"] != run["model"]["path_hint"]
            or model["sha256"] != run["model"]["sha256"]
            or sha256_file(PROJECT_ROOT / model["path"]) != model["sha256"]
        ):
            return False
        expected_sources = {
            "runner": "scripts/run_e4_v2_execution_aware.py",
            "verifier": "scripts/verify_e4_v2_bundle.py",
            "execution_aware_core": "src/search/execution_aware_utility.py",
            "crypto_oracle_loader": "src/benchmarks/crypto_oracles.py",
            "contract_test": "tests/test_e4_v2_runner.py",
        }
        if set(frozen["sources"]) != set(expected_sources):
            return False
        for role, path in expected_sources.items():
            if (
                frozen["sources"][role]["path"] != path
                or frozen["sources"][role]["sha256"]
                != sha256_file(PROJECT_ROOT / path)
            ):
                return False
        canonical_lock_path = PROJECT_ROOT / str(config["protocol_lock"]["path"])
        if canonical_lock_path.is_file():
            repository_lock = _read_json(canonical_lock_path)
            if repository_lock != frozen:
                return False
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False


def _search_config(config: dict[str, Any]) -> SearchConfig:
    search = config["search"]
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        max_factor_ancilla=int(search["max_factor_ancilla"]),
        max_factor_size=int(search["max_factor_size"]),
        candidate_top_k=int(search["candidate_top_k"]),
        mcts_simulations=int(search["simulations"]),
        neural_mcts_simulations=int(search["simulations"]),
        gate_mode="mct",
    )


def _action_from_signature(value: dict[str, Any]) -> FactorAction:
    return FactorAction(
        factor=int(value["factor"]),
        group=frozenset(int(item) for item in value["group"]),
        residuals=frozenset(int(item) for item in value["residuals"]),
        rest=frozenset(int(item) for item in value["rest"]),
        immediate_gain=float(value["immediate_gain"]),
        prior=float(value["prior"]),
        linear=bool(value["linear"]),
        affine_const=bool(value["affine_const"]),
    )


def _calibration_compile_records_ok(row: dict[str, Any], config: dict[str, Any], profile_spec: SyntheticExecutionProfileSpec) -> bool:
    try:
        bf = BooleanFunction(int(row["n"]), int(row["truth_table_hex"], 16))
        terms = frozenset(anf_monomials(bf))
        signatures = row["candidate_pool"]["action_signatures"]
        records = row["compile_time_candidates"]
        if len(signatures) != len(records):
            return False
        search_config = _search_config(config)
        for index, (signature, record) in enumerate(zip(signatures, records)):
            action = _action_from_signature(signature)
            plan = complete_root_action_rollout(StateKey(terms, 0, 0), action, search_config)
            circuit = emit_plan_to_circuit(
                plan,
                int(row["n"]),
                min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla),
            )
            execution_n_qubits = int(
                config["native_profile"]["frozen_n_qubits"]
            )
            if circuit.n_qubits > execution_n_qubits:
                return False
            if circuit.n_qubits < execution_n_qubits:
                padded = QuantumCircuit(execution_n_qubits)
                padded.gates = list(circuit.gates)
                circuit = padded
            compilation = compile_superconducting(circuit, profile_spec.build(circuit.n_qubits))
            diagnostics = compilation.diagnostics
            expected = {
                "native_one_qubit": diagnostics.one_qubit_gate_count,
                "native_two_qubit": diagnostics.two_qubit_gate_count,
                "inserted_swap": diagnostics.inserted_swap_count,
                "native_depth": diagnostics.native_depth,
                "duration_ns": (
                    diagnostics.one_qubit_gate_count * profile_spec.one_qubit_duration_ns
                    + diagnostics.two_qubit_gate_count * profile_spec.two_qubit_duration_ns
                ),
                "model_risk": 0.0,
            }
            if int(record["candidate_index"]) != index:
                return False
            actual = record["resource_components"]
            if any(not math.isclose(float(actual[name]), float(expected[name]), rel_tol=0.0, abs_tol=1e-12) for name in FEATURES):
                return False
            if record.get("plan_anf_ok") is not True or record.get("circuit_anf_ok") is not True:
                return False
            if record.get("hardware_execution") is not False or record.get("synthetic_profile") is not True:
                return False
            if int(record.get("logical_n_qubits", -1)) != execution_n_qubits:
                return False
        return True
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


def _recomputed_weights(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    *,
    calibration_sha256: str,
    profile_sha256: str,
) -> tuple[FrozenExecutionPenaltyWeights, dict[str, float]]:
    target = float(config["weight_selection"]["target_penalty_at_component_medians"])
    mixture = config["weight_selection"]["feature_mixture"]
    scales: dict[str, float] = {}
    coefficients: dict[str, float] = {}
    for name in FEATURES:
        values = [
            float(candidate["resource_components"][name])
            for row in rows
            for candidate in row["compile_time_candidates"]
        ]
        positive = [value for value in values if value > 0.0]
        scale = statistics.median(positive) if positive else 0.0
        scales[name] = scale
        share = float(mixture[name])
        if share > 0.0 and scale <= 0.0:
            raise ValueError(f"zero scale for weighted feature {name}")
        coefficients[name] = 0.0 if share == 0.0 else target * share / scale
    return (
        FrozenExecutionPenaltyWeights(
            calibration_sha256=calibration_sha256,
            profile_sha256=profile_sha256,
            **coefficients,
        ),
        scales,
    )


def _verify_calibration(
    root: Path,
    run: dict[str, Any],
    summary: dict[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, bool]:
    config = run.get("config", {}).get("effective_config")
    if not isinstance(config, dict):
        return {"effective_config_present": False}
    config_sha = sha256_bytes(canonical_json_bytes(config))
    calibration_config_sha = sha256_bytes(
        canonical_json_bytes(_calibration_protocol(config))
    )
    profile_spec = _profile_spec(config)
    frozen_profile, frozen_profile_sha = _frozen_concrete_profile(
        config, profile_spec
    )
    aes_hashes = {coordinate.truth_table_sha256 for coordinate in get_crypto_oracle_coordinates("AES")}
    cal = config["calibration"]
    expected_cases = []
    for index in range(int(cal["case_count"])):
        seed = int(cal["seed_base"]) + index
        bf = BooleanFunction(int(cal["n"]), random.Random(seed).getrandbits(1 << int(cal["n"])))
        expected_cases.append((f"e4v2-cal-n8-k{index:02d}", seed, _truth_table_sha256(bf), int(bf.truth_table)))
    actual_cases = [
        (row.get("case_id"), row.get("instance_seed"), row.get("truth_table_sha256"), int(row.get("truth_table_hex", "0"), 16))
        for row in rows
    ]
    dataset = dict(run.get("dataset", {}))
    declared_dataset_sha = dataset.pop("dataset_sha256", None)
    rows_sha = sha256_bytes(canonical_json_bytes(rows))
    evidence = {
        "schema_version": "xa.e4-v2-calibration-evidence-binding.v1",
        "calibration_config_sha256": calibration_config_sha,
        "dataset_sha256": declared_dataset_sha,
        "profile_sha256": profile_spec.profile_sha256,
        "model_sha256": run.get("model", {}).get("sha256"),
        "source_tree_sha256": run.get("source", {}).get("source_tree_sha256"),
        "calibration_rows_sha256": rows_sha,
    }
    calibration_sha = sha256_bytes(canonical_json_bytes(evidence))
    try:
        weights, scales = _recomputed_weights(
            rows,
            config,
            calibration_sha256=calibration_sha,
            profile_sha256=profile_spec.profile_sha256,
        )
        weights_ok = weights.canonical_payload() == summary.get("frozen_penalty_weights") and weights.weights_sha256 == summary.get("weights_sha256")
        scales_ok = all(
            math.isclose(float(scales[name]), float(summary["weight_selection"]["positive_median_scales"][name]), rel_tol=0.0, abs_tol=1e-12)
            for name in FEATURES
        )
    except (KeyError, TypeError, ValueError):
        weights_ok = False
        scales_ok = False
    checks = {
        "phase_and_status": summary.get("phase") == "calibrate" and run.get("status") == "complete",
        "config_sha_recomputed": config_sha == run.get("config", {}).get("config_sha256") == summary.get("config_sha256"),
        "calibration_config_projection_recomputed": calibration_config_sha
        == run.get("config", {}).get("calibration_config_sha256")
        == summary.get("calibration_config_sha256"),
        "dataset_sha_recomputed": isinstance(declared_dataset_sha, str) and sha256_bytes(canonical_json_bytes(dataset)) == declared_dataset_sha == summary.get("dataset_sha256"),
        "locally_frozen_non_aes_cases_recomputed": actual_cases == expected_cases and all(item[2] not in aes_hashes for item in actual_cases),
        "split_mutually_exclusive": not ({item[2] for item in actual_cases} & aes_hashes),
        "candidate_pool_sha_recomputed": all(
            sha256_bytes(canonical_json_bytes(row.get("candidate_pool"))) == row.get("candidate_pool_sha256")
            for row in rows
        ),
        "compile_features_independently_recomputed": bool(rows) and all(_calibration_compile_records_ok(row, config, profile_spec) for row in rows),
        "calibration_access_boundary": all(
            row.get("compile_time_only") is True
            and row.get("noisy_endpoint_accessed") is False
            and row.get("replication_aes_accessed") is False
            and row.get("heldout_aes_accessed") is False
            and row.get("test_outcome_accessed") is False
            and "noisy_endpoints" not in row
            for row in rows
        ),
        "calibration_rows_sha_recomputed": rows_sha == summary.get("calibration_rows_sha256"),
        "fixed_profile_sha_recomputed": summary.get("profile") == frozen_profile
        and summary.get("profile_sha256") == frozen_profile_sha
        and summary.get("profile_spec_sha256") == profile_spec.profile_sha256
        and run.get("config", {}).get("profile_sha256") == frozen_profile_sha,
        "all_calibration_candidates_fixed_10q_profile": summary.get(
            "all_candidates_fixed_10q_profile"
        )
        is True
        and all(
            row.get("profile_sha256") == frozen_profile_sha
            and all(
                candidate.get("logical_n_qubits")
                == int(config["native_profile"]["frozen_n_qubits"])
                and candidate.get("concrete_profile_sha256")
                == frozen_profile_sha
                for candidate in row.get("compile_time_candidates", [])
            )
            for row in rows
        ),
        "model_source_dataset_sha_bound": summary.get("model_sha256") == run.get("model", {}).get("sha256")
        and summary.get("source_tree_sha256") == run.get("source", {}).get("source_tree_sha256")
        and summary.get("dataset_sha256") == declared_dataset_sha,
        "calibration_evidence_sha_recomputed": evidence == summary.get("calibration_evidence_binding")
        and calibration_sha == summary.get("calibration_sha256"),
        "weights_frozen_recomputed": weights_ok and scales_ok,
        "weights_nonnegative_finite": weights_ok and all(
            math.isfinite(float(summary["frozen_penalty_weights"][name]))
            and float(summary["frozen_penalty_weights"][name]) >= 0.0
            for name in FEATURES
        ),
        "no_performance_claim": summary.get("performance_evidence") is False,
        "frozen_replication_role_explicit": run.get("experiment_role")
        == summary.get("experiment_role")
        == "frozen_replication"
        and run.get("historically_seen_in_E4") is True
        and summary.get("historically_seen_in_E4") is True
        and run.get("calibration_functions_historically_seen_in_E4") is False
        and summary.get("calibration_functions_historically_seen_in_E4")
        is False
        and all(
            row.get("historically_seen_in_E4") is True
            and row.get("calibration_function_historically_seen_in_E4")
            is False
            for row in rows
        )
        and run.get("generalization_claim") is False
        and summary.get("generalization_claim") is False,
        "frozen_compute_contract_bound": run.get("compute_contract")
        == summary.get("compute_contract")
        == config.get("compute_contract"),
        "local_protocol_lock_verified": _protocol_lock_ok(run, summary, config),
    }
    return checks


def _plan_from_trace(payload: dict[str, Any]) -> Plan:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("plan trace nodes missing")
    by_id = {str(node["node_id"]): node for node in nodes}
    if len(by_id) != len(nodes) or payload.get("root_id") not in by_id:
        raise ValueError("invalid plan trace ids")
    children: dict[tuple[str, str], str] = {}
    for node in nodes:
        parent = node.get("parent_id")
        edge = node.get("edge")
        if parent is not None:
            key = (str(parent), str(edge))
            if key in children:
                raise ValueError("duplicate plan child")
            children[key] = str(node["node_id"])

    def build(node_id: str) -> Plan:
        node = by_id[node_id]
        kind = str(node["kind"])
        group_id = children.get((node_id, "group"))
        rest_id = children.get((node_id, "rest"))
        if kind == "direct" and (group_id is not None or rest_id is not None):
            raise ValueError("direct plan has children")
        if kind != "direct" and (group_id is None or rest_id is None):
            raise ValueError("factor plan lacks children")
        return Plan(
            kind=kind,
            terms=frozenset(int(value, 16) for value in node["terms_hex"]),
            cost=ResourceCost(**{key: int(value) for key, value in node["resource_cost"].items()}),
            factor=int(node["factor_hex"], 16),
            group=build(group_id) if group_id is not None else None,
            rest=build(rest_id) if rest_id is not None else None,
            affine_const=bool(node["affine_const"]),
        )

    return build(str(payload["root_id"]))


def _circuit_from_ir(payload: dict[str, Any]) -> QuantumCircuit:
    circuit = QuantumCircuit(int(payload["n_qubits"]))
    circuit.gates = [
        Gate(str(gate["gate_type"]), [int(value) for value in gate["controls"]], int(gate["target"]))
        for gate in payload["gates"]
    ]
    return circuit


def _scheduler_config(
    config: dict[str, Any], variant: str, *, output_bit: int, solver_seed: int
) -> DiversitySchedulerConfig:
    search = config["search"]
    qaoa = config["qaoa"]
    return DiversitySchedulerConfig(
        method="qaoa" if variant.endswith("qaoa_shot") else "greedy",
        budget_requested=int(search["scheduler_budget"]),
        pool_size=int(search["scheduler_pool_size"]),
        min_candidates=int(search["scheduler_min_candidates"]),
        max_depth=0,
        redundancy_weight=float(search["redundancy_weight"]),
        redundancy_alpha=float(search["redundancy_alpha"]),
        utility_clip=float(search["utility_clip"]),
        exact_max_candidates=12,
        seed=int(search["scheduler_seed_base"])
        + 1000 * int(solver_seed)
        + int(output_bit),
        qaoa_mode="shot",
        qaoa_p=int(qaoa["p"]),
        qaoa_shots=int(qaoa["shots"]),
        qaoa_noise_bitflip_probability=float(
            qaoa["measurement_bitflip_probability"]
        ),
        qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
        qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
    )


def _action_signature(action: FactorAction) -> dict[str, Any]:
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


def _rebuild_pool_schedule_and_plan(
    row: dict[str, Any],
    config: dict[str, Any],
    weights: FrozenExecutionPenaltyWeights,
    checkpoint: Path,
) -> bool:
    """Rebuild the assigned arm from truth table, checkpoint, seed and configs."""

    try:
        bit = int(row["output_bit"])
        solver_seed = int(row["solver_seed"])
        variant = str(row["variant"])
        coordinate = get_crypto_oracle_coordinates("AES")[bit]
        terms = frozenset(anf_monomials(coordinate.boolean_function))
        search_config = _search_config(config)
        scheduler_config = _scheduler_config(
            config,
            variant,
            output_bit=bit,
            solver_seed=solver_seed,
        )
        if asdict(search_config) != row.get("search_config"):
            return False
        if scheduler_config.to_dict() != row.get("scheduler_config"):
            return False
        if (
            row.get("simulations") != int(config["search"]["simulations"])
            or row.get("solver_seed") != solver_seed
            or row.get("scheduler_seed") != scheduler_config.seed
        ):
            return False
        profile_spec = _profile_spec(config)
        adjuster = None
        if variant.startswith("execution_aware_"):
            adjuster = make_root_rollout_execution_utility_adjuster(
                n_inputs=8,
                search_config=search_config,
                profile_spec=profile_spec,
                penalty_weights=weights,
                expected_profile_sha256=profile_spec.profile_sha256,
                execution_n_qubits=int(
                    config["native_profile"]["frozen_n_qubits"]
                ),
            )
        scorer = FoundationScorer.from_checkpoint(checkpoint)
        policy = TermThresholdPolicyScorer(
            scorer, int(config["search"]["policy_term_threshold"])
        )
        solver = NeuralMCTSSolver(
            config=search_config,
            simulations=int(config["search"]["simulations"]),
            seed=solver_seed,
            neural_scorer=policy,
            value_estimator=None,
            rollout_scorer=None,
            scheduler_config=scheduler_config,
            execution_utility_adjuster=adjuster,
        )
        plan = solver.solve(terms)
        root = solver.nodes.get(StateKey(terms, 0, 0))
        if root is None or root.scheduler_decision is None:
            return False
        diagnostics = dict(root.scheduler_decision.diagnostics)
        width = int(diagnostics["candidate_count"])
        actions = tuple(root.actions[:width])
        raw = [float(value) for value in diagnostics["raw_utilities"]]
        adjusted = [float(value) for value in diagnostics["adjusted_utilities"]]
        pool = row["candidate_pool"]
        if (
            pool.get("node_id") != diagnostics.get("node_id")
            or pool.get("candidate_count") != width
            or pool.get("budget_requested") != scheduler_config.budget_requested
            or pool.get("budget_effective")
            != min(scheduler_config.budget_requested, width)
            or pool.get("action_signatures")
            != [_action_signature(action) for action in actions]
            or pool.get("utilities") != raw
            or pool.get("redundancy")
            != [
                [float(value) for value in values]
                for values in action_redundancy_matrix(
                    actions, alpha=scheduler_config.redundancy_alpha
                )
            ]
            or row.get("raw_scheduler_utilities") != raw
            or row.get("adjusted_scheduler_utilities") != adjusted
        ):
            return False
        stored_scheduler = row["scheduler"]
        selected = [int(value) for value in root.scheduler_decision.selected_indices]
        if (
            stored_scheduler.get("selected_indices") != selected
            or stored_scheduler.get("method") != scheduler_config.method
            or stored_scheduler.get("qaoa_mode")
            != ("shot" if variant.endswith("qaoa_shot") else None)
            or stored_scheduler.get("status") != diagnostics.get("status")
            or stored_scheduler.get("qaoa_attempted")
            != bool(diagnostics.get("qaoa_attempted"))
            or stored_scheduler.get("qaoa_succeeded")
            != bool(diagnostics.get("qaoa_succeeded"))
            or stored_scheduler.get("qaoa_repaired")
            != bool(diagnostics.get("qaoa_repaired"))
            or stored_scheduler.get("qaoa_fallback")
            != bool(diagnostics.get("qaoa_fallback"))
            or diagnostics.get("seed")
            != stored_scheduler.get("diagnostics", {}).get("seed")
            or diagnostics.get("qaoa")
            != stored_scheduler.get("diagnostics", {}).get("qaoa")
            or diagnostics.get("qubo")
            != stored_scheduler.get("diagnostics", {}).get("qubo")
        ):
            return False
        if row.get("execution_feedback") != diagnostics.get("execution_feedback"):
            return False
        if variant.startswith("execution_aware_"):
            metadata = diagnostics["execution_feedback"]["model_metadata"]
            if (
                metadata.get("n_inputs") != 8
                or metadata.get("execution_n_qubits") != 10
                or metadata.get("search_config") != asdict(search_config)
                or metadata.get("search_config_sha256")
                != sha256_bytes(canonical_json_bytes(asdict(search_config)))
            ):
                return False
        trace = PlanTrace.from_plan(plan).to_dict()
        if (
            canonical_json_bytes(trace)
            != canonical_json_bytes(row.get("plan_trace"))
            or asdict(plan.cost) != row.get("logical_cost")
        ):
            return False
        allocated = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
        circuit = emit_plan_to_circuit(plan, 8, allocated)
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if circuit.n_qubits < frozen_n:
            padded = QuantumCircuit(frozen_n)
            padded.gates = list(circuit.gates)
            circuit = padded
        logical = export_openqasm3(circuit)
        return (
            circuit_to_logical_ir(circuit)
            == circuit_to_logical_ir(_circuit_from_ir(row["logical_circuit_ir"]))
            and logical.qasm == row.get("logical_qasm3")
            and sha256_bytes(logical.qasm.encode("utf-8"))
            == row.get("logical_qasm3_sha256")
            and plan.score(PAPER_WEIGHTS)
            == row.get("logical_resource_score")
            and root.visits == row.get("root_visits")
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


def _native_record_matches(row: dict[str, Any], compilation: object) -> bool:
    diagnostics = compilation.diagnostics
    native = row["native"]
    for name in (
        "logical_gate_count",
        "native_gate_count",
        "one_qubit_gate_count",
        "two_qubit_gate_count",
        "inserted_swap_count",
        "inserted_routing_cx_count",
        "native_depth",
    ):
        if int(native[name]) != int(getattr(diagnostics, name)):
            return False
    qasm = native_to_openqasm3(compilation)
    return (
        native.get("native_qasm3") == qasm
        and native.get("native_qasm3_sha256") == sha256_bytes(qasm.encode("utf-8"))
        and all(gate.name in {"rz", "sx", "x", "cx"} for gate in compilation.native_gates)
        and all(
            tuple(sorted(gate.qubits)) in compilation.profile.coupling_edges
            for gate in compilation.native_gates
            if gate.name == "cx"
        )
    )


def _test_trial_recomputed(row: dict[str, Any], config: dict[str, Any]) -> bool:
    try:
        bit = int(row["output_bit"])
        coordinate = get_crypto_oracle_coordinates("AES")[bit]
        if row["truth_table_sha256"] != coordinate.truth_table_sha256:
            return False
        plan = _plan_from_trace(row["plan_trace"])
        if not verify_plan_anf(plan).ok:
            return False
        terms = frozenset(anf_monomials(coordinate.boolean_function))
        if plan.terms != terms or asdict(plan.cost) != row["logical_cost"]:
            return False
        emitted = emit_plan_to_circuit(plan, coordinate.input_width, int(row["allocated_factor_ancilla"]))
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if emitted.n_qubits < frozen_n:
            padded = QuantumCircuit(frozen_n)
            padded.gates = list(emitted.gates)
            emitted = padded
        stored = _circuit_from_ir(row["logical_circuit_ir"])
        if circuit_to_logical_ir(emitted) != circuit_to_logical_ir(stored):
            return False
        logical = export_openqasm3(stored)
        if row["logical_qasm3"] != logical.qasm or row["logical_qasm3_sha256"] != sha256_bytes(logical.qasm.encode("utf-8")):
            return False
        if not verify_circuit_anf(stored, coordinate.input_width, terms).ok or not verify_oracle(stored, coordinate.boolean_function):
            return False
        profile_raw = config["native_profile"]
        profile = heavy_hex_like_profile(
            stored.n_qubits,
            noise=NoiseParameters(
                model="independent-pauli-depolarizing-v1",
                one_qubit_error=float(profile_raw["one_qubit_error"]),
                two_qubit_error=float(profile_raw["two_qubit_error"]),
                readout_error=float(profile_raw["readout_error"]),
            ),
        )
        compilation = compile_superconducting(stored, profile)
        _, profile_sha = _frozen_concrete_profile(
            config, _profile_spec(config)
        )
        if (
            stored.n_qubits != int(config["native_profile"]["frozen_n_qubits"])
            or profile.n_qubits != int(
                config["native_profile"]["frozen_n_qubits"]
            )
            or row.get("profile_sha256") != profile_sha
            or row.get("native", {}).get("profile_sha256") != profile_sha
            or not _native_record_matches(row, compilation)
        ):
            return False
        model = PauliNoiseModel(
            one_qubit_error=float(profile_raw["one_qubit_error"]),
            two_qubit_error=float(profile_raw["two_qubit_error"]),
            readout_error=float(profile_raw["readout_error"]),
            parameter_source="synthetic-heavy-hex-like-fixed-10q-v1",
        )
        for endpoint in row["noisy_endpoints"]:
            x = int(endpoint["input_x"])
            logical_input = tuple((x >> index) & 1 for index in range(coordinate.input_width)) + (0,) + (0,) * (stored.n_qubits - coordinate.input_width - 1)
            rerun = simulate_noisy_shots(
                compilation,
                logical_input,
                shots=int(endpoint["shots"]),
                seed=int(endpoint["seed"]),
                noise_model=model,
                max_qubits=10,
            )
            if (
                endpoint.get("counts") != rerun.counts
                or int(endpoint["success_count"]) != rerun.success_count
                or not math.isclose(float(endpoint["success_rate"]), rerun.success_rate, abs_tol=1e-15)
                or endpoint.get("expected_bitstring") != rerun.expected_bitstring
                or endpoint.get("events") != asdict(rerun.events)
                or endpoint.get("actual_noisy_simulation") is not True
                or endpoint.get("hardware_execution") is not False
                or endpoint.get("noise_applied") is not True
                or endpoint.get("task_contract_ok") is not True
                or endpoint.get("seed_contract") != "paired-common-random-numbers-v2"
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    index = min(
        len(ordered) - 1,
        max(0, round(probability * (len(ordered) - 1))),
    )
    return ordered[index]


def _recompute_cluster_comparison(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    *,
    historical: str,
    execution: str,
    direct_unrepaired_only: bool = False,
) -> dict[str, Any]:
    by_key = {
        (int(row["output_bit"]), int(row["solver_seed"]), row["variant"]): row
        for row in rows
    }
    keys = sorted(
        {(int(row["output_bit"]), int(row["solver_seed"])) for row in rows}
    )
    pairs = []
    for bit, seed in keys:
        left = by_key[(bit, seed, historical)]
        right = by_key[(bit, seed, execution)]
        if direct_unrepaired_only and (
            left.get("qaoa_execution") != "direct_unrepaired"
            or right.get("qaoa_execution") != "direct_unrepaired"
        ):
            continue
        left_value = int(left["native"]["two_qubit_gate_count"])
        right_value = int(right["native"]["two_qubit_gate_count"])
        pairs.append(
            {
                "output_bit": bit,
                "solver_seed": seed,
                "historical_native_two_qubit": left_value,
                "execution_aware_native_two_qubit": right_value,
                "delta_execution_minus_historical": right_value - left_value,
            }
        )
    by_bit: dict[int, list[float]] = {}
    for pair in pairs:
        by_bit.setdefault(int(pair["output_bit"]), []).append(
            float(pair["delta_execution_minus_historical"])
        )
    clusters = [
        {
            "output_bit": bit,
            "solver_seed_count": len(values),
            "mean_delta_execution_minus_historical": statistics.mean(values),
        }
        for bit, values in sorted(by_bit.items())
    ]
    means = [float(item["mean_delta_execution_minus_historical"]) for item in clusters]
    base = {
        "historical_variant": historical,
        "execution_aware_variant": execution,
        "metric": "native.two_qubit_gate_count",
        "direction": "lower_is_better",
        "estimand": (
            "direct_unrepaired_sensitivity"
            if direct_unrepaired_only
            else "intention_to_treat_all_assigned_trials"
        ),
        "pair_count": len(pairs),
        "cluster_count": len(clusters),
        "pairs": pairs,
        "cluster_means": clusters,
    }
    if not means:
        return {
            **base,
            "mean_delta_execution_minus_historical": None,
            "bootstrap_95_ci": None,
            "wins_losses_ties": {"wins": 0, "losses": 0, "ties": 0},
        }
    rng = random.Random(int(config["statistics"]["bootstrap_seed"]))
    bootstrap = [
        statistics.mean(rng.choice(means) for _ in means)
        for _ in range(int(config["statistics"]["bootstrap_resamples"]))
    ]
    return {
        **base,
        "mean_delta_execution_minus_historical": statistics.mean(means),
        "bootstrap_95_ci": [
            _percentile(bootstrap, 0.025),
            _percentile(bootstrap, 0.975),
        ],
        "wins_losses_ties": {
            "wins": sum(value < 0.0 for value in means),
            "losses": sum(value > 0.0 for value in means),
            "ties": sum(value == 0.0 for value in means),
        },
    }


def _verify_test(
    root: Path,
    run: dict[str, Any],
    summary: dict[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, bool]:
    config = run.get("config", {}).get("effective_config")
    if not isinstance(config, dict):
        return {"effective_config_present": False}
    config_sha = sha256_bytes(canonical_json_bytes(config))
    dataset = dict(run.get("dataset", {}))
    declared_dataset_sha = dataset.pop("dataset_sha256", None)
    binding = summary.get("calibration_binding", {})
    cal_hint = binding.get("calibration_bundle_hint")
    cal_root = root.parent / str(cal_hint)
    cal_exists = cal_root.is_dir()
    cal_verification: dict[str, Any] = {"ok": False}
    cal_summary: dict[str, Any] = {}
    cal_rows: list[dict[str, Any]] = []
    if cal_exists and cal_root.resolve() != root.resolve():
        cal_verification = verify_e4_v2_bundle(cal_root, _allow_test_calibration_link=False)
        try:
            cal_summary = _read_json(cal_root / "summary.json")
            cal_rows = _read_jsonl(cal_root / "raw.jsonl")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            cal_verification = {"ok": False}
    selected_bits = set(int(value) for value in config["test"]["coordinates"])
    seeds = set(int(value) for value in config["test"]["solver_seeds"])
    expected_matrix = {(bit, seed, variant) for bit in selected_bits for seed in seeds for variant in VARIANTS}
    actual_matrix = {(row.get("output_bit"), row.get("solver_seed"), row.get("variant")) for row in rows}
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((int(row["output_bit"]), int(row["solver_seed"])), []).append(row)
    fairness = all(
        len(group) == 4
        and len({row.get("candidate_pool_sha256") for row in group}) == 1
        and len({canonical_json_bytes(row.get("raw_scheduler_utilities")) for row in group}) == 1
        and len({row.get("scheduler", {}).get("budget_requested") for row in group}) == 1
        for group in groups.values()
    )
    pool_hashes = all(
        sha256_bytes(canonical_json_bytes(row.get("candidate_pool"))) == row.get("candidate_pool_sha256")
        for row in rows
    )
    qaoa = [row for row in rows if str(row.get("variant", "")).endswith("qaoa_shot")]
    def expected_qaoa_class(row: dict[str, Any]) -> str:
        scheduler = row.get("scheduler", {})
        if scheduler.get("qaoa_fallback") is True:
            return "fallback"
        if scheduler.get("qaoa_repaired") is True:
            return "direct_repaired"
        if scheduler.get("qaoa_succeeded") is True:
            return "direct_unrepaired"
        return "invalid_unaccounted"

    qaoa_ok = all(
        row.get("scheduler", {}).get("qaoa_attempted") is True
        and row.get("qaoa_execution") == expected_qaoa_class(row)
        and row.get("qaoa_execution")
        in {"direct_unrepaired", "direct_repaired", "fallback"}
        for row in qaoa
    )
    selection_ok = all(
        len(row["scheduler"]["selected_indices"]) == row["scheduler"]["budget_effective"]
        and len(set(row["scheduler"]["selected_indices"])) == len(row["scheduler"]["selected_indices"])
        and all(0 <= int(index) < int(row["scheduler"]["candidate_count"]) for index in row["scheduler"]["selected_indices"])
        and row["scheduler"]["selected_action_visits_total"] == row["simulations"]
        and row["scheduler"]["excluded_action_visits_total"] == 0
        for row in rows
    )
    common_noise = all(
        len({
            endpoint["seed"]
            for row in group
            for endpoint in row["noisy_endpoints"]
            if endpoint["input_x"] == x and endpoint["noise_seed_anchor"] == anchor
        }) == 1
        for group in groups.values()
        for x in config["test"]["endpoint_inputs"]
        for anchor in config["test"]["noise_seed_anchors"]
    )
    expected_coordinates = {coordinate.output_bit: coordinate.truth_table_sha256 for coordinate in get_crypto_oracle_coordinates("AES") if coordinate.output_bit in selected_bits}
    dataset_coordinates = {item["output_bit"]: item["truth_table_sha256"] for item in run.get("dataset", {}).get("coordinates", [])}
    cal_hashes = {row.get("truth_table_sha256") for row in cal_rows}
    test_hashes = {row.get("truth_table_sha256") for row in rows}
    weights_payload = run.get("config", {}).get("frozen_penalty_weights")
    weights: FrozenExecutionPenaltyWeights | None = None
    weights_ok = False
    if isinstance(weights_payload, dict):
        try:
            weights = FrozenExecutionPenaltyWeights(
                calibration_sha256=str(weights_payload["calibration_sha256"]),
                profile_sha256=str(weights_payload["profile_sha256"]),
                **{name: float(weights_payload[name]) for name in FEATURES},
            )
            weights_ok = (
                weights.weights_sha256 == binding.get("weights_sha256") == cal_summary.get("weights_sha256")
                and weights.canonical_payload() == cal_summary.get("frozen_penalty_weights")
                and all(row.get("weights_sha256") == weights.weights_sha256 for row in rows)
            )
        except (KeyError, TypeError, ValueError):
            weights_ok = False
    primary_recomputed = _recompute_cluster_comparison(
        rows,
        config,
        historical="historical_qaoa_shot",
        execution="execution_aware_qaoa_shot",
    )
    secondary_recomputed = _recompute_cluster_comparison(
        rows,
        config,
        historical="historical_greedy",
        execution="execution_aware_greedy",
    )
    sensitivity_recomputed = _recompute_cluster_comparison(
        rows,
        config,
        historical="historical_qaoa_shot",
        execution="execution_aware_qaoa_shot",
        direct_unrepaired_only=True,
    )
    paired_summary_ok = (
        summary.get("primary_comparison") == primary_recomputed
        and summary.get("secondary_comparison") == secondary_recomputed
        and summary.get("direct_unrepaired_sensitivity")
        == sensitivity_recomputed
    )
    performance_supported = bool(
        summary.get("formal_statistical_evaluation") is True
        and primary_recomputed["bootstrap_95_ci"] is not None
        and float(primary_recomputed["bootstrap_95_ci"][1]) < 0.0
    )
    profile_spec = _profile_spec(config)
    frozen_profile, frozen_profile_sha = _frozen_concrete_profile(
        config, profile_spec
    )
    checkpoint_path = PROJECT_ROOT / str(run.get("model", {}).get("path_hint", ""))
    independent_schedule_rebuild = bool(weights is not None and checkpoint_path.is_file()) and all(
        _rebuild_pool_schedule_and_plan(row, config, weights, checkpoint_path)
        for row in rows
    )
    endpoint_count = sum(len(row.get("noisy_endpoints", [])) for row in rows)
    shots = sum(int(endpoint["shots"]) for row in rows for endpoint in row.get("noisy_endpoints", []))
    successes = sum(int(endpoint["success_count"]) for row in rows for endpoint in row.get("noisy_endpoints", []))
    checks = {
        "phase_and_status": summary.get("phase") == "replication"
        and summary.get("legacy_phase_alias") == "test"
        and run.get("status") == "complete",
        "config_sha_recomputed": config_sha == run.get("config", {}).get("config_sha256") == binding.get("config_sha256"),
        "dataset_sha_recomputed": isinstance(declared_dataset_sha, str) and sha256_bytes(canonical_json_bytes(dataset)) == declared_dataset_sha == binding.get("dataset_sha256"),
        "calibration_bundle_link_verified": cal_exists and cal_verification.get("ok") is True
        and binding.get("calibration_summary_sha256") == sha256_file(cal_root / "summary.json"),
        "calibration_split_mutually_exclusive": bool(cal_hashes) and not (cal_hashes & test_hashes),
        "aes_coordinate_hashes_recomputed": dataset_coordinates == expected_coordinates
        and all(row.get("truth_table_sha256") == expected_coordinates.get(row.get("output_bit")) for row in rows),
        "complete_four_arm_matrix": actual_matrix == expected_matrix and len(rows) == len(expected_matrix),
        "candidate_pool_hashes_recomputed": pool_hashes,
        "candidate_pool_raw_utility_budget_fair": fairness,
        "historical_adjusted_equals_raw": all(
            row.get("adjusted_scheduler_utilities") == row.get("raw_scheduler_utilities")
            for row in rows
            if str(row.get("variant", "")).startswith("historical_")
        ),
        "execution_adjustment_frozen": all(
            row.get("test_noisy_outcome_used_by_utility") is False
            and row.get("execution_feedback", {}).get("model_sha256") is not None
            and row.get("execution_feedback", {}).get("diagnostics", {}).get("heldout_noisy_outcome_used") is False
            for row in rows
            if str(row.get("variant", "")).startswith("execution_aware_")
        ),
        "weights_calibration_profile_model_source_bound": weights_ok
        and binding.get("calibration_sha256") == cal_summary.get("calibration_sha256")
        and binding.get("profile_sha256") == cal_summary.get("profile_sha256")
        and binding.get("profile_spec_sha256")
        == cal_summary.get("profile_spec_sha256")
        and binding.get("model_sha256") == cal_summary.get("model_sha256") == run.get("model", {}).get("sha256")
        and binding.get("source_tree_sha256") == cal_summary.get("source_tree_sha256") == run.get("source", {}).get("source_tree_sha256")
        and binding.get("refit_on_test") is False,
        "selection_and_budget_recomputed": selection_ok,
        "qaoa_itt_direct_repaired_fallback_accounted": bool(qaoa) and qaoa_ok,
        "checkpoint_seed_config_pool_utility_selection_plan_rebuilt": independent_schedule_rebuild,
        "plan_qasm_semantics_native_noisy_recomputed": bool(rows) and all(_test_trial_recomputed(row, config) for row in rows),
        "fixed_10q_profile_all_four_arms": summary.get(
            "all_four_arms_fixed_10q_profile"
        )
        is True
        and summary.get("frozen_profile") == frozen_profile
        and summary.get("profile_sha256") == frozen_profile_sha
        and summary.get("profile_spec_sha256") == profile_spec.profile_sha256
        and all(
            row.get("logical_n_qubits") == 10
            and row.get("native", {}).get("n_qubits") == 10
            and row.get("profile_sha256") == frozen_profile_sha
            and row.get("native", {}).get("profile_sha256")
            == frozen_profile_sha
            for row in rows
        ),
        "paired_common_random_numbers": common_noise,
        "primary_endpoint_locally_frozen_itt": summary.get("primary_endpoint", {}).get("metric") == "native.two_qubit_gate_count"
        and summary.get("primary_endpoint", {}).get("estimand")
        == "intention_to_treat_all_assigned_trials"
        and all(
            row.get("assignment_estimand")
            == "intention_to_treat_all_assigned_trials"
            for row in rows
        )
        and summary.get("noisy_diagnostic", {}).get("role") == "diagnostic_only_not_a_tuning_or_primary_endpoint",
        "bit_cluster_pairs_ci_wlt_and_sensitivity_recomputed": paired_summary_ok,
        "formal_evaluation_separate_from_performance_support": summary.get(
            "formal_statistical_evaluation"
        )
        is (not bool(summary.get("tiny")))
        and summary.get("performance_claim_supported")
        is performance_supported,
        "post_e4_replication_no_generalization": run.get("experiment_role")
        == summary.get("experiment_role")
        == "frozen_replication"
        and run.get("dataset_role")
        == summary.get("dataset_role")
        == "post_e4_frozen_aes_replication"
        and run.get("historically_seen_in_E4") is True
        and summary.get("historically_seen_in_E4") is True
        and run.get("generalization_claim") is False
        and summary.get("generalization_claim") is False
        and all(
            row.get("historically_seen_in_E4") is True
            and row.get("generalization_claim") is False
            for row in rows
        ),
        "frozen_compute_contract_bound": run.get("compute_contract")
        == summary.get("compute_contract")
        == config.get("compute_contract"),
        "local_protocol_lock_verified": _protocol_lock_ok(run, summary, config),
        "summary_counts_recomputed": summary.get("trial_count") == len(rows)
        and summary.get("noisy_diagnostic", {}).get("endpoint_count") == endpoint_count
        and summary.get("noisy_diagnostic", {}).get("total_shots") == shots
        and summary.get("noisy_diagnostic", {}).get("success_count") == successes,
        "scope_boundary_explicit": summary.get("scope", {}).get("synthetic_profile") is True
        and summary.get("scope", {}).get("hardware_execution") is False
        and summary.get("scope", {}).get("quantum_advantage_claimed") is False
        and summary.get("scope", {}).get("noisy_success_primary_endpoint") is False
        and summary.get("scope", {}).get("generalization_claim") is False,
    }
    return checks


def verify_e4_v2_bundle(
    run_dir: str | Path,
    *,
    _allow_test_calibration_link: bool = True,
) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    bundle = verify_bundle(root, required_roles=REQUIRED_ROLES)
    errors = list(bundle.errors)
    try:
        run = _read_json(root / "run.json")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        rows = _read_jsonl(root / "raw.jsonl")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return {"ok": False, "errors": errors, "checks": {}}
    effective_config = run.get("config", {}).get("effective_config")
    observed_compute_contract: dict[str, Any] | None = None
    compute_contract_error: str | None = None
    if isinstance(effective_config, dict):
        try:
            observed_compute_contract = _enforce_compute_contract(effective_config)
        except (RuntimeError, ValueError) as exc:
            compute_contract_error = str(exc)
    else:
        compute_contract_error = "effective config missing before compute-contract enforcement"
    checks: dict[str, bool] = {
        "bundle_checksums_manifest_roles": bundle.ok,
        "exact_nine_file_bundle": root.is_dir() and {path.name for path in root.iterdir()} == EXPECTED_FILES,
        "run_id_consistent": bool(run.get("run_id")) and run.get("run_id") == summary.get("run_id") == declared.get("run_id"),
        "track_and_schema": run.get("track") == "xa202609/e4-v2-execution-aware"
        and run.get("config", {}).get("runner_schema") == "xa.e4-v2-execution-aware-runner.v1",
        "declared_verifier_ok": declared.get("ok") is True
        and bool(declared.get("checks"))
        and all(bool(value) for value in declared.get("checks", {}).values()),
        "frozen_compute_contract_enforced_before_checkpoint_inference": compute_contract_error
        is None
        and observed_compute_contract == effective_config.get("compute_contract"),
    }
    phase = summary.get("phase")
    if compute_contract_error is not None:
        errors.append(f"compute contract error: {compute_contract_error}")
    elif phase == "calibrate":
        checks.update(_verify_calibration(root, run, summary, rows))
    elif phase == "replication" and _allow_test_calibration_link:
        checks.update(_verify_test(root, run, summary, rows))
    else:
        checks["supported_phase"] = False
    for name, passed in checks.items():
        if not passed:
            errors.append(f"failed check: {name}")
    return {"ok": not errors, "errors": errors, "checks": checks, "phase": phase}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = verify_e4_v2_bundle(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
