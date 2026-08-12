#!/usr/bin/env python3
"""Run the two-stage E4-v2 compile-only execution-aware AES experiment.

``calibrate`` freezes non-negative utility penalties from predeclared non-AES
Boolean functions and deterministic compile-time native features only.
``test`` is retained as a CLI compatibility alias for a post-E4 frozen AES
replication. It loads those weights without fitting and evaluates the four
paired historical/execution-aware x greedy/QAOA arms. No noisy outcome is
available during calibration; noisy success in replication is a
seeded diagnostic and never the primary endpoint or a tuning signal.

``--tiny`` preserves the phase boundary and all four test arms while reducing
case/seed/shot counts.  It is a contract smoke, not performance evidence.
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

import torch  # noqa: E402

from scripts import run_aes_bidirectional_pilot as aes_runner  # noqa: E402
from scripts._pilot_artifacts import (  # noqa: E402
    dataset_sha256,
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
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
from src.foundation.adapter import FoundationScorer, TermThresholdPolicyScorer  # noqa: E402
from src.hardware.superconducting import NoiseParameters  # noqa: E402
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.search.execution_aware_utility import (  # noqa: E402
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.mcts_scheduler import (  # noqa: E402
    action_redundancy_matrix,
)
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


CONFIG_SCHEMA = "xa.e4-v2-execution-aware-config.v1"
PROTOCOL_LOCK_SCHEMA = "xa.e4-v2-local-protocol-lock.v1"
RUNNER_SCHEMA = "xa.e4-v2-execution-aware-runner.v1"
CAL_ROW_SCHEMA = "xa.e4-v2-calibration-pool.v1"
TEST_ROW_SCHEMA = "xa.e4-v2-aes-test-trial.v1"
CAL_SUMMARY_SCHEMA = "xa.e4-v2-calibration-summary.v1"
TEST_SUMMARY_SCHEMA = "xa.e4-v2-test-summary.v1"
VERIFIER_SCHEMA = "xa.e4-v2-declared-verifier.v1"
TRACK = "xa202609/e4-v2-execution-aware"
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


def _enforce_compute_contract(config: dict[str, Any]) -> dict[str, Any]:
    """Set and verify the frozen PyTorch inference contract before scoring."""

    contract = config.get("compute_contract")
    expected = {
        "torch_device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    if contract != expected:
        raise ValueError("E4-v2 compute contract changed")
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError as exc:
            raise RuntimeError(
                "cannot establish frozen torch inter-op thread count before inference"
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


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite and non-negative")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and non-negative") from exc
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _probability(value: object, name: str) -> float:
    result = _finite_nonnegative(value, name)
    if result > 1.0:
        raise ValueError(f"{name} must lie in [0, 1]")
    return result


def load_config(path: str | Path, *, tiny: bool = False) -> dict[str, Any]:
    """Load and fail-closed validate the frozen E4-v2 configuration."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "experiment",
        "experiment_role",
        "dataset_role",
        "historically_seen_in_E4",
        "generalization_claim",
        "protocol_lock",
        "compute_contract",
        "checkpoint",
        "calibration",
        "test",
        "search",
        "qaoa",
        "native_profile",
        "weight_selection",
        "primary_endpoint",
        "statistics",
        "claim_boundary",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("E4-v2 config fields do not match the frozen schema")
    if value.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported E4-v2 config schema")
    if value.get("experiment_role") != "frozen_replication":
        raise ValueError("E4-v2 experiment_role must be frozen_replication")
    if value.get("dataset_role") != "post_e4_frozen_aes_replication":
        raise ValueError("E4-v2 dataset_role changed")
    if value.get("historically_seen_in_E4") is not True:
        raise ValueError("AES coordinates must be marked historically seen in E4")
    if value.get("generalization_claim") is not False:
        raise ValueError("frozen replication cannot make a generalization claim")
    if value.get("compute_contract") != {
        "torch_device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }:
        raise ValueError("E4-v2 compute contract must remain single-threaded CPU")
    protocol = value.get("protocol_lock")
    if (
        not isinstance(protocol, dict)
        or protocol.get("schema_version") != PROTOCOL_LOCK_SCHEMA
        or protocol.get("freeze_semantics") != "locally_frozen_prior_to_run"
        or protocol.get("path")
        != "configs/xa202609/e4_v2_execution_aware_v1.protocol.lock.json"
    ):
        raise ValueError("invalid local protocol-lock declaration")
    config = copy.deepcopy(value)
    if tiny:
        config["calibration"]["case_count"] = 1
        # Include bit 1 because its checkpoint priors expose cross-process
        # thread-reduction drift that bit 0 alone does not exercise.
        config["test"]["coordinates"] = [0, 1]
        config["test"]["solver_seeds"] = [1]
        config["test"]["endpoint_inputs"] = [0]
        config["test"]["noise_seed_anchors"] = [101]
        config["test"]["endpoint_shots"] = 1
        config["search"]["simulations"] = 3
        config["qaoa"]["shots"] = 16
        config["qaoa"]["optimizer_restarts"] = 1
        config["qaoa"]["optimizer_steps"] = 1
        config["statistics"]["bootstrap_resamples"] = 200

    checkpoint = config["checkpoint"]
    if set(checkpoint) != {"path", "sha256"}:
        raise ValueError("checkpoint must contain path and sha256")
    digest = str(checkpoint["sha256"])
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("checkpoint.sha256 must be a lowercase SHA-256")
    calibration = config["calibration"]
    if calibration.get("family") != "seeded-non-aes-boolean-functions":
        raise ValueError("calibration family must be the frozen non-AES family")
    for name in ("n", "case_count", "seed_base"):
        _positive_int(calibration[name], f"calibration.{name}")
    if calibration["n"] != 8:
        raise ValueError("E4-v2 calibration width is frozen at n=8")
    required_allowed = {
        "truth_table",
        "learned_policy_candidate_pool",
        "raw_scheduler_utility",
        "compile_time_native_features",
    }
    required_forbidden = {
        "replication_aes_coordinates",
        "test_plan",
        "test_native_result",
        "noisy_endpoint",
    }
    if set(calibration.get("allowed_inputs", [])) != required_allowed:
        raise ValueError("calibration allowed_inputs changed")
    if set(calibration.get("forbidden_inputs", [])) != required_forbidden:
        raise ValueError("calibration forbidden_inputs changed")

    test = config["test"]
    if (
        test.get("dataset_role") != "post_e4_frozen_aes_replication"
        or test.get("historically_seen_in_E4") is not True
        or test.get("generalization_claim") is not False
    ):
        raise ValueError("replication dataset-role boundary changed")
    coordinates = test.get("coordinates")
    if (
        not isinstance(coordinates, list)
        or not coordinates
        or len(set(coordinates)) != len(coordinates)
        or any(isinstance(bit, bool) or not isinstance(bit, int) or bit not in range(8) for bit in coordinates)
    ):
        raise ValueError("test.coordinates must be unique AES bits")
    seeds = test.get("solver_seeds")
    if not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("test.solver_seeds must be non-empty and unique")
    for seed in seeds:
        _positive_int(seed, "test.solver_seed")
    inputs = test.get("endpoint_inputs")
    if (
        not isinstance(inputs, list)
        or not inputs
        or len(set(inputs)) != len(inputs)
        or any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < 256 for x in inputs)
    ):
        raise ValueError("test.endpoint_inputs must be unique bytes")
    anchors = test.get("noise_seed_anchors")
    if not isinstance(anchors, list) or not anchors or len(set(anchors)) != len(anchors):
        raise ValueError("test.noise_seed_anchors must be non-empty and unique")
    for seed in anchors:
        _positive_int(seed, "test.noise_seed_anchor")
    _positive_int(test["endpoint_shots"], "test.endpoint_shots")

    search = config["search"]
    for name in (
        "simulations",
        "candidate_top_k",
        "max_factor_size",
        "scheduler_pool_size",
        "scheduler_budget",
        "scheduler_min_candidates",
        "scheduler_seed_base",
        "noise_seed_base",
    ):
        _positive_int(search[name], f"search.{name}")
    if search["max_factor_ancilla"] not in (0, 1):
        raise ValueError("search.max_factor_ancilla must be 0 or 1")
    if not isinstance(search["policy_term_threshold"], int) or search["policy_term_threshold"] < 0:
        raise ValueError("search.policy_term_threshold must be non-negative")
    if search["simulations"] < search["scheduler_budget"]:
        raise ValueError("simulations must cover every selected root edge")
    if search["candidate_top_k"] < search["scheduler_pool_size"]:
        raise ValueError("candidate_top_k must cover scheduler_pool_size")
    if not search["scheduler_budget"] < search["scheduler_min_candidates"] <= search["scheduler_pool_size"]:
        raise ValueError("require budget < min_candidates <= pool_size")
    if search["scheduler_pool_size"] > 12:
        raise ValueError("QAOA statevector candidate pool cannot exceed 12")
    _finite_nonnegative(search["redundancy_weight"], "search.redundancy_weight")
    alpha = _probability(search["redundancy_alpha"], "search.redundancy_alpha")
    if alpha > 1.0:
        raise ValueError("redundancy_alpha must lie in [0, 1]")
    if _finite_nonnegative(search["utility_clip"], "search.utility_clip") <= 0.0:
        raise ValueError("utility_clip must be positive")

    qaoa = config["qaoa"]
    if qaoa.get("mode") != "shot":
        raise ValueError("E4-v2 QAOA mode is frozen to shot")
    for name in ("p", "shots", "optimizer_restarts"):
        _positive_int(qaoa[name], f"qaoa.{name}")
    if not isinstance(qaoa["optimizer_steps"], int) or qaoa["optimizer_steps"] < 0:
        raise ValueError("qaoa.optimizer_steps must be non-negative")
    _probability(qaoa["measurement_bitflip_probability"], "qaoa.measurement_bitflip_probability")

    profile = config["native_profile"]
    if profile.get("family") != "synthetic-heavy-hex-like-fixed-10q-v1":
        raise ValueError("unsupported native profile family")
    if profile.get("frozen_n_qubits") != 10:
        raise ValueError("E4-v2 requires one frozen 10-qubit profile")
    if tuple(profile.get("native_gate_set", [])) != ("rz", "sx", "x", "cx"):
        raise ValueError("native gate set must be rz/sx/x/cx")
    for name in ("one_qubit_error", "two_qubit_error", "readout_error"):
        _probability(profile[name], f"native_profile.{name}")
    for name in ("one_qubit_duration_ns", "two_qubit_duration_ns"):
        if _finite_nonnegative(profile[name], f"native_profile.{name}") <= 0.0:
            raise ValueError(f"native_profile.{name} must be positive")

    selection = config["weight_selection"]
    if selection.get("rule") != "fixed-mixture-median-positive-scale-v1":
        raise ValueError("unsupported weight-selection rule")
    target = _finite_nonnegative(
        selection["target_penalty_at_component_medians"],
        "weight_selection.target_penalty_at_component_medians",
    )
    if target <= 0.0:
        raise ValueError("weight-selection target must be positive")
    mixture = selection.get("feature_mixture")
    if not isinstance(mixture, dict) or set(mixture) != set(FEATURES):
        raise ValueError("feature_mixture must declare every frozen feature")
    shares = {name: _finite_nonnegative(mixture[name], f"feature_mixture.{name}") for name in FEATURES}
    if not math.isclose(math.fsum(shares.values()), 1.0, abs_tol=1e-12):
        raise ValueError("feature mixture must sum to one")
    if shares["model_risk"] != 0.0:
        raise ValueError("compile-only calibration forbids model_risk fitting")
    endpoint = config["primary_endpoint"]
    if endpoint.get("metric") != "native.two_qubit_gate_count":
        raise ValueError("primary endpoint is frozen to native two-qubit count")
    if (
        endpoint.get("estimand") != "intention_to_treat_all_assigned_trials"
        or endpoint.get("cluster_unit") != "aes_output_bit"
        or endpoint.get("seed_aggregation_within_cluster") != "arithmetic_mean"
        or endpoint.get("direct_unrepaired_sensitivity") is not True
    ):
        raise ValueError("primary ITT/cluster estimand changed")
    if endpoint.get("noisy_success_role") != "diagnostic_only_not_a_tuning_or_primary_endpoint":
        raise ValueError("noisy success must remain diagnostic only")
    _positive_int(config["statistics"]["bootstrap_resamples"], "bootstrap_resamples")
    _positive_int(config["statistics"]["bootstrap_seed"], "bootstrap_seed")
    if float(config["statistics"]["confidence_level"]) != 0.95:
        raise ValueError("confidence level is frozen to 0.95")
    return config


def _config_sha256(config: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(config))


def load_protocol_lock(
    config: dict[str, Any],
) -> tuple[dict[str, Any], str, Path]:
    """Validate the external locally-frozen protocol lock before any run."""

    relative = Path(str(config["protocol_lock"]["path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("protocol-lock path must remain project-relative")
    lock_path = (PROJECT_ROOT / relative).resolve()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "freeze_semantics",
        "experiment_role",
        "dataset_role",
        "historically_seen_in_E4",
        "generalization_claim",
        "config",
        "sources",
        "model",
        "primary_endpoint",
        "primary_endpoint_sha256",
        "compute_contract",
        "compute_contract_sha256",
    }
    if not isinstance(lock, dict) or set(lock) != required:
        raise ValueError("protocol-lock fields do not match the frozen schema")
    if (
        lock.get("schema_version") != PROTOCOL_LOCK_SCHEMA
        or lock.get("freeze_semantics") != "locally_frozen_prior_to_run"
        or lock.get("experiment_role") != "frozen_replication"
        or lock.get("dataset_role") != config["dataset_role"]
        or lock.get("historically_seen_in_E4") is not True
        or lock.get("generalization_claim") is not False
    ):
        raise ValueError("protocol-lock scientific role boundary changed")
    config_record = lock.get("config")
    canonical_config_path = (
        PROJECT_ROOT / "configs/xa202609/e4_v2_execution_aware_v1.json"
    ).resolve()
    canonical_config = json.loads(canonical_config_path.read_text(encoding="utf-8"))
    if (
        not isinstance(config_record, dict)
        or config_record.get("path")
        != "configs/xa202609/e4_v2_execution_aware_v1.json"
        or config_record.get("canonical_sha256")
        != _config_sha256(canonical_config)
        or config_record.get("canonical_payload") != canonical_config
    ):
        raise ValueError("protocol-lock config SHA mismatch")
    expected_sources = {
        "runner": "scripts/run_e4_v2_execution_aware.py",
        "verifier": "scripts/verify_e4_v2_bundle.py",
        "execution_aware_core": "src/search/execution_aware_utility.py",
        "crypto_oracle_loader": "src/benchmarks/crypto_oracles.py",
        "contract_test": "tests/test_e4_v2_runner.py",
    }
    sources = lock.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(expected_sources):
        raise ValueError("protocol-lock source roles changed")
    for role, expected_path in expected_sources.items():
        record = sources[role]
        source_path = (PROJECT_ROOT / expected_path).resolve()
        if (
            not isinstance(record, dict)
            or record.get("path") != expected_path
            or record.get("sha256") != sha256_file(source_path)
        ):
            raise ValueError(f"protocol-lock source SHA mismatch: {role}")
    model = lock.get("model")
    if (
        not isinstance(model, dict)
        or model.get("path") != config["checkpoint"]["path"]
        or model.get("sha256") != config["checkpoint"]["sha256"]
        or model.get("sha256")
        != sha256_file((PROJECT_ROOT / str(model["path"])).resolve())
    ):
        raise ValueError("protocol-lock model SHA mismatch")
    endpoint = lock.get("primary_endpoint")
    if endpoint != config["primary_endpoint"] or lock.get(
        "primary_endpoint_sha256"
    ) != sha256_bytes(canonical_json_bytes(endpoint)):
        raise ValueError("protocol-lock primary endpoint mismatch")
    compute_contract = lock.get("compute_contract")
    if (
        compute_contract != config["compute_contract"]
        or lock.get("compute_contract_sha256")
        != sha256_bytes(canonical_json_bytes(compute_contract))
    ):
        raise ValueError("protocol-lock compute contract mismatch")
    return lock, sha256_bytes(canonical_json_bytes(lock)), lock_path


def _calibration_protocol(config: dict[str, Any]) -> dict[str, Any]:
    """Project the full config onto fields legally visible to calibration."""

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


def _checkpoint(config: dict[str, Any]) -> tuple[Path, dict[str, str]]:
    path = Path(config["checkpoint"]["path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.expanduser().resolve()
    metadata = model_record(path, PROJECT_ROOT)
    if metadata["sha256"] != config["checkpoint"]["sha256"]:
        raise ValueError("checkpoint SHA-256 does not match frozen config")
    return path, metadata


def _profile_spec(config: dict[str, Any]) -> SyntheticExecutionProfileSpec:
    profile = config["native_profile"]
    return SyntheticExecutionProfileSpec(
        one_qubit_duration_ns=float(profile["one_qubit_duration_ns"]),
        two_qubit_duration_ns=float(profile["two_qubit_duration_ns"]),
        noise=NoiseParameters(
            model="independent-pauli-depolarizing-v1",
            one_qubit_error=float(profile["one_qubit_error"]),
            two_qubit_error=float(profile["two_qubit_error"]),
            readout_error=float(profile["readout_error"]),
        ),
    )


def _frozen_concrete_profile(
    config: dict[str, Any], profile_spec: SyntheticExecutionProfileSpec
) -> tuple[dict[str, Any], str]:
    n_qubits = int(config["native_profile"]["frozen_n_qubits"])
    profile = profile_spec.build(n_qubits)
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


def _runner_args(config: dict[str, Any], *, solver_seed: int) -> argparse.Namespace:
    search = config["search"]
    qaoa = config["qaoa"]
    test = config["test"]
    profile = config["native_profile"]
    return argparse.Namespace(
        solver_seed=int(solver_seed),
        scheduler_seed_base=int(search["scheduler_seed_base"]) + 1000 * int(solver_seed),
        noise_seed_base=int(search["noise_seed_base"]),
        noise_seeds=list(test["noise_seed_anchors"]),
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
        endpoint_inputs=list(test["endpoint_inputs"]),
        endpoint_shots=int(test["endpoint_shots"]),
        one_qubit_error=float(profile["one_qubit_error"]),
        two_qubit_error=float(profile["two_qubit_error"]),
        readout_error=float(profile["readout_error"]),
        noise_parameter_source="synthetic-heavy-hex-like-fixed-10q-v1",
    )


def _calibration_args(config: dict[str, Any]) -> argparse.Namespace:
    """Return only search fields needed by compile-only calibration.

    Test inputs, test seeds, endpoint shots and noisy outcomes are deliberately
    absent from this namespace, so they cannot enter pool construction or the
    weight-selection rule even accidentally.
    """

    search = config["search"]
    qaoa = config["qaoa"]
    return argparse.Namespace(
        solver_seed=1,
        scheduler_seed_base=int(search["scheduler_seed_base"]),
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
    )


def _truth_table_sha256(bf: BooleanFunction) -> str:
    byte_count = ((1 << bf.n) + 7) // 8
    return hashlib.sha256(int(bf.truth_table).to_bytes(byte_count, "little")).hexdigest()


def _calibration_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    cal = config["calibration"]
    cases: list[dict[str, Any]] = []
    for index in range(int(cal["case_count"])):
        seed = int(cal["seed_base"]) + index
        bf = BooleanFunction(int(cal["n"]), random.Random(seed).getrandbits(1 << int(cal["n"])))
        digest = _truth_table_sha256(bf)
        cases.append(
            {
                "case_id": f"e4v2-cal-n8-k{index:02d}",
                "instance_seed": seed,
                "n": bf.n,
                "truth_table_hex": canonical_hex(int(bf.truth_table), min_nibbles=64),
                "truth_table_sha256": digest,
                "anf_term_count": len(anf_monomials(bf)),
                "bf": bf,
            }
        )
    hashes = [case["truth_table_sha256"] for case in cases]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("duplicate calibration truth tables")
    return cases


def _calibration_dataset(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "dataset_id": "e4v2-seeded-non-aes-n8-calibration-v1",
        "phase": "calibrate",
        "experiment_role": "frozen_replication",
        "dataset_role": "calibration_for_post_e4_frozen_aes_replication",
        "historically_seen_in_E4": True,
        "calibration_functions_historically_seen_in_E4": False,
        "generalization_claim": False,
        "generation": "python-random-getrandbits-frozen-seed-v1",
        "replication_family": "FIPS-197-AES-forward-S-box",
        "cases": [
            {key: case[key] for key in ("case_id", "instance_seed", "n", "truth_table_hex", "truth_table_sha256", "anf_term_count")}
            for case in cases
        ],
    }
    return {**payload, "dataset_sha256": dataset_sha256(payload)}


def _calibration_rows(
    *,
    cases: Sequence[dict[str, Any]],
    config: dict[str, Any],
    checkpoint: Path,
    checkpoint_sha256: str,
    dataset_sha: str,
    profile_spec: SyntheticExecutionProfileSpec,
    run_id: str,
) -> list[dict[str, Any]]:
    args = _calibration_args(config)
    search_config = aes_runner._search_config(args)
    zero_weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=dataset_sha,
        profile_sha256=profile_spec.profile_sha256,
    )
    adjuster = make_root_rollout_execution_utility_adjuster(
        n_inputs=8,
        search_config=search_config,
        profile_spec=profile_spec,
        penalty_weights=zero_weights,
        expected_profile_sha256=profile_spec.profile_sha256,
        execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
    )
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    policy = TermThresholdPolicyScorer(scorer, args.policy_term_threshold)
    rows: list[dict[str, Any]] = []
    for case in cases:
        terms = frozenset(anf_monomials(case["bf"]))
        scheduler_config = aes_runner._scheduler_config(
            args, "historical_greedy", scheduler_seed=args.scheduler_seed_base
        )
        solver = NeuralMCTSSolver(
            config=search_config,
            simulations=0,
            seed=1,
            neural_scorer=policy,
            value_estimator=None,
            rollout_scorer=None,
            scheduler_config=scheduler_config,
            execution_utility_adjuster=adjuster,
        )
        key = StateKey(terms, 0, 0)
        node = solver._node(key)
        solver._expand(node)
        if not node.actions:
            raise RuntimeError(f"empty calibration candidate pool: {case['case_id']}")
        solver._schedule_node(node, 0)
        if node.scheduler_decision is None:
            raise RuntimeError("calibration scheduler did not emit diagnostics")
        diagnostics = dict(node.scheduler_decision.diagnostics)
        width = int(diagnostics["candidate_count"])
        actions = tuple(node.actions[:width])
        raw_utilities = [float(value) for value in diagnostics["raw_utilities"]]
        redundancy = action_redundancy_matrix(actions, alpha=args.redundancy_alpha)
        pool_payload = {
            "schema_version": "xa.e4-v2-calibration-candidate-pool.v1",
            "case_id": case["case_id"],
            "truth_table_sha256": case["truth_table_sha256"],
            "node_id": diagnostics["node_id"],
            "candidate_count": width,
            "budget_requested": args.scheduler_budget,
            "budget_effective": min(args.scheduler_budget, width),
            "action_signatures": [aes_runner._action_signature(action) for action in actions],
            "raw_utilities": raw_utilities,
            "redundancy": [[float(value) for value in row] for row in redundancy],
        }
        feedback = diagnostics["execution_feedback"]
        compile_diagnostics = feedback["diagnostics"]
        candidate_records = compile_diagnostics["candidates"]
        rows.append(
            {
                "schema_version": CAL_ROW_SCHEMA,
                "record_type": "e4_v2_calibration_pool",
                "run_id": run_id,
                "phase": "calibrate",
                "case_id": case["case_id"],
                "instance_seed": case["instance_seed"],
                "n": case["n"],
                "truth_table_hex": case["truth_table_hex"],
                "truth_table_sha256": case["truth_table_sha256"],
                "anf_term_count": case["anf_term_count"],
                "checkpoint_sha256": checkpoint_sha256,
                "profile_spec_sha256": profile_spec.profile_sha256,
                "profile_sha256": candidate_records[0][
                    "concrete_profile_sha256"
                ],
                "candidate_pool": pool_payload,
                "candidate_pool_sha256": sha256_bytes(canonical_json_bytes(pool_payload)),
                "raw_scheduler_utilities": raw_utilities,
                "compile_time_candidates": candidate_records,
                "compile_time_only": True,
                "historically_seen_in_E4": True,
                "calibration_function_historically_seen_in_E4": False,
                "noisy_endpoint_accessed": False,
                "replication_aes_accessed": False,
                "heldout_aes_accessed": False,
                "test_outcome_accessed": False,
                "hardware_execution": False,
            }
        )
    return rows


def select_frozen_weights(
    *,
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    calibration_sha256: str,
    profile_sha256: str,
) -> tuple[FrozenExecutionPenaltyWeights, dict[str, Any]]:
    """Apply the single locally frozen compile-only median scaling rule."""

    mixture = {
        name: float(config["weight_selection"]["feature_mixture"][name])
        for name in FEATURES
    }
    target = float(config["weight_selection"]["target_penalty_at_component_medians"])
    scales: dict[str, float] = {}
    coefficients: dict[str, float] = {}
    for name in FEATURES:
        values = [
            float(candidate["resource_components"][name])
            for row in rows
            for candidate in row["compile_time_candidates"]
        ]
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValueError(f"non-finite calibration feature: {name}")
        positive = [value for value in values if value > 0.0]
        scale = statistics.median(positive) if positive else 0.0
        scales[name] = scale
        share = mixture[name]
        if share > 0.0 and scale <= 0.0:
            raise ValueError(f"positive mixture share has zero calibration scale: {name}")
        coefficients[name] = 0.0 if share == 0.0 else target * share / scale
    weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=calibration_sha256,
        profile_sha256=profile_sha256,
        **coefficients,
    )
    _, frozen_profile_sha = _frozen_concrete_profile(
        config, _profile_spec(config)
    )
    rule = {
        "schema_version": "xa.e4-v2-weight-selection-rule.v1",
        "rule": "fixed-mixture-median-positive-scale-v1",
        "target_penalty_at_component_medians": target,
        "feature_mixture": mixture,
        "positive_median_scales": scales,
        "coefficients": coefficients,
        "candidate_record_count": sum(len(row["compile_time_candidates"]) for row in rows),
        "all_candidates_fixed_10q_profile": all(
            candidate["logical_n_qubits"]
            == int(config["native_profile"]["frozen_n_qubits"])
            and candidate["concrete_profile_sha256"] == frozen_profile_sha
            for row in rows
            for candidate in row["compile_time_candidates"]
        ),
        "model_fit": False,
        "noisy_outcome_used": False,
        "heldout_test_used": False,
    }
    return weights, rule


def _declared_verifier(run_id: str, checks: dict[str, bool]) -> dict[str, Any]:
    return {
        "schema_version": VERIFIER_SCHEMA,
        "run_id": run_id,
        "checks": checks,
        "ok": all(checks.values()),
    }


def _write_and_verify(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    rows: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    verifier: dict[str, Any],
    events: Sequence[dict[str, Any]],
) -> None:
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
        raise RuntimeError(f"E4-v2 artifact bundle failed: {bundle.errors}")
    from scripts.verify_e4_v2_bundle import verify_e4_v2_bundle

    independent = verify_e4_v2_bundle(run_dir)
    if not independent["ok"]:
        raise RuntimeError(f"independent E4-v2 verifier failed: {independent['errors']}")
    print(f"bundle={run_dir}")
    print("bundle_ok=True")
    print("independent_verifier_ok=True")


def run_calibration(
    *,
    config_path: Path,
    config: dict[str, Any],
    out_dir: Path,
    run_id: str,
    tiny: bool,
) -> Path:
    compute_contract = _enforce_compute_contract(config)
    protocol_lock, protocol_lock_sha, _ = load_protocol_lock(config)
    started = time.perf_counter()
    created_at = utc_now()
    checkpoint, checkpoint_meta = _checkpoint(config)
    source = source_record(PROJECT_ROOT)
    cases = _calibration_cases(config)
    dataset = _calibration_dataset(cases)
    profile_spec = _profile_spec(config)
    frozen_profile, frozen_profile_sha = _frozen_concrete_profile(
        config, profile_spec
    )
    config_sha = _config_sha256(config)
    calibration_config_sha = sha256_bytes(
        canonical_json_bytes(_calibration_protocol(config))
    )
    rows = _calibration_rows(
        cases=cases,
        config=config,
        checkpoint=checkpoint,
        checkpoint_sha256=checkpoint_meta["sha256"],
        dataset_sha=dataset["dataset_sha256"],
        profile_spec=profile_spec,
        run_id=run_id,
    )
    rows_sha = sha256_bytes(canonical_json_bytes(rows))
    evidence_payload = {
        "schema_version": "xa.e4-v2-calibration-evidence-binding.v1",
        "calibration_config_sha256": calibration_config_sha,
        "dataset_sha256": dataset["dataset_sha256"],
        "profile_sha256": profile_spec.profile_sha256,
        "model_sha256": checkpoint_meta["sha256"],
        "source_tree_sha256": source["source_tree_sha256"],
        "calibration_rows_sha256": rows_sha,
    }
    calibration_sha = sha256_bytes(canonical_json_bytes(evidence_payload))
    weights, selection_rule = select_frozen_weights(
        rows=rows,
        config=config,
        calibration_sha256=calibration_sha,
        profile_sha256=profile_spec.profile_sha256,
    )
    summary = {
        "schema_version": CAL_SUMMARY_SCHEMA,
        "run_id": run_id,
        "phase": "calibrate",
        "experiment_role": "frozen_replication",
        "dataset_role": "calibration_for_post_e4_frozen_aes_replication",
        "historically_seen_in_E4": True,
        "calibration_functions_historically_seen_in_E4": False,
        "generalization_claim": False,
        "compute_contract": compute_contract,
        "tiny": tiny,
        "performance_evidence": False,
        "case_count": len(rows),
        "candidate_record_count": sum(len(row["compile_time_candidates"]) for row in rows),
        "dataset_sha256": dataset["dataset_sha256"],
        "config_sha256": config_sha,
        "calibration_config_sha256": calibration_config_sha,
        "config_file_sha256": sha256_file(config_path),
        "profile_spec_sha256": profile_spec.profile_sha256,
        "profile": frozen_profile,
        "profile_sha256": frozen_profile_sha,
        "model_sha256": checkpoint_meta["sha256"],
        "source_tree_sha256": source["source_tree_sha256"],
        "calibration_rows_sha256": rows_sha,
        "calibration_evidence_binding": evidence_payload,
        "calibration_sha256": calibration_sha,
        "weight_selection": selection_rule,
        "all_candidates_fixed_10q_profile": selection_rule[
            "all_candidates_fixed_10q_profile"
        ],
        "frozen_penalty_weights": weights.canonical_payload(),
        "weights_sha256": weights.weights_sha256,
        "calibration_access_contract": {
            "compile_time_only": True,
            "noisy_endpoint_accessed": False,
            "replication_aes_accessed": False,
            "heldout_aes_accessed": False,
            "test_outcome_accessed": False,
        },
        "protocol_lock": protocol_lock,
        "protocol_lock_sha256": protocol_lock_sha,
        "claim_boundary": config["claim_boundary"],
    }
    checks = {
        "calibration_nonempty": bool(rows),
        "compile_time_only": all(row["compile_time_only"] for row in rows),
        "no_noisy_or_test_access": all(
            not row["noisy_endpoint_accessed"]
            and not row["heldout_aes_accessed"]
            and not row["replication_aes_accessed"]
            and not row["test_outcome_accessed"]
            for row in rows
        ),
        "weights_nonnegative_finite": all(
            math.isfinite(float(getattr(weights, name))) and float(getattr(weights, name)) >= 0.0
            for name in FEATURES
        ),
        "profile_model_source_dataset_bound": all(
            isinstance(summary[name], str) and len(summary[name]) == 64
            for name in ("profile_sha256", "model_sha256", "source_tree_sha256", "dataset_sha256")
        ),
        "not_performance_evidence": summary["performance_evidence"] is False,
        "fixed_10q_profile": summary["all_candidates_fixed_10q_profile"],
        "frozen_compute_contract": summary["compute_contract"]
        == config["compute_contract"],
    }
    verifier = _declared_verifier(run_id, checks)
    elapsed = time.perf_counter() - started
    events = [
        {"event": "calibration_started", "run_id": run_id, "created_at_utc": created_at, "tiny": tiny},
        {"event": "weights_frozen", "weights_sha256": weights.weights_sha256, "calibration_sha256": calibration_sha},
        {"event": "calibration_completed", "run_id": run_id, "elapsed_s": elapsed, "declared_verifier_ok": verifier["ok"]},
    ]
    manifest = ExperimentManifest(
        run_id=run_id,
        track=TRACK,
        experiment="e4-v2-compile-only-calibration",
        status="complete" if verifier["ok"] else "failed",
        created_at_utc=created_at,
        source=source,
        environment=environment_record(),
        command={"entrypoint": "scripts/run_e4_v2_execution_aware.py", "phase": "calibrate", "tiny": tiny},
        dataset=dataset,
        config={
            "runner_schema": RUNNER_SCHEMA,
            "config_path_hint": "configs/xa202609/e4_v2_execution_aware_v1.json",
            "config_file_sha256": sha256_file(config_path),
            "config_sha256": config_sha,
            "calibration_config_sha256": calibration_config_sha,
            "effective_config": config,
            "profile_spec_sha256": profile_spec.profile_sha256,
            "profile_sha256": frozen_profile_sha,
            "experiment_role": "frozen_replication",
            "dataset_role": "calibration_for_post_e4_frozen_aes_replication",
            "historically_seen_in_E4": True,
            "calibration_functions_historically_seen_in_E4": False,
            "generalization_claim": False,
            "protocol_lock": protocol_lock,
            "protocol_lock_sha256": protocol_lock_sha,
            "compute_contract": compute_contract,
        },
        model=checkpoint_meta,
        variants=("compile_only_calibration",),
        expected_artifacts=EXPECTED_ARTIFACTS,
        counts={"cases": len(rows), "candidate_records": summary["candidate_record_count"], "noisy_shots": 0},
        timing={"wall_s": elapsed},
        claim_boundary=config["claim_boundary"],
    ).to_dict()
    manifest.update(
        experiment_role="frozen_replication",
        dataset_role="calibration_for_post_e4_frozen_aes_replication",
        historically_seen_in_E4=True,
        calibration_functions_historically_seen_in_E4=False,
        generalization_claim=False,
        protocol_lock_sha256=protocol_lock_sha,
        compute_contract=compute_contract,
    )
    run_dir = out_dir.expanduser().resolve() / run_id
    _write_and_verify(
        run_dir=run_dir,
        manifest=manifest,
        rows=rows,
        summary=summary,
        verifier=verifier,
        events=events,
    )
    return run_dir


def _load_calibration(
    calibration_bundle: Path,
    *,
    config: dict[str, Any],
) -> tuple[dict[str, Any], FrozenExecutionPenaltyWeights]:
    from scripts.verify_e4_v2_bundle import verify_e4_v2_bundle

    verified = verify_e4_v2_bundle(calibration_bundle)
    if not verified["ok"]:
        raise ValueError(f"calibration bundle did not verify: {verified['errors']}")
    run = json.loads((calibration_bundle / "run.json").read_text(encoding="utf-8"))
    summary = json.loads((calibration_bundle / "summary.json").read_text(encoding="utf-8"))
    if summary.get("phase") != "calibrate":
        raise ValueError("calibration bundle has the wrong phase")
    if run.get("config", {}).get("config_sha256") != _config_sha256(config):
        raise ValueError("calibration config SHA does not match the test config")
    payload = summary.get("frozen_penalty_weights")
    if not isinstance(payload, dict):
        raise ValueError("calibration summary is missing frozen weights")
    weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=str(payload["calibration_sha256"]),
        profile_sha256=str(payload["profile_sha256"]),
        **{name: float(payload[name]) for name in FEATURES},
    )
    if weights.weights_sha256 != summary.get("weights_sha256"):
        raise ValueError("frozen weight SHA mismatch")
    return summary, weights


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("percentile requires values")
    index = min(len(ordered) - 1, max(0, round(probability * (len(ordered) - 1))))
    return ordered[index]


def _paired_comparison(
    rows: Sequence[dict[str, Any]],
    *,
    historical: str,
    execution: str,
    config: dict[str, Any],
    direct_unrepaired_only: bool = False,
) -> dict[str, Any]:
    by_key = {(int(row["output_bit"]), int(row["solver_seed"]), row["variant"]): row for row in rows}
    keys = sorted({(int(row["output_bit"]), int(row["solver_seed"])) for row in rows})
    pairs = []
    for bit, seed in keys:
        left = by_key[(bit, seed, historical)]
        right = by_key[(bit, seed, execution)]
        if direct_unrepaired_only and (
            left.get("qaoa_execution") != "direct_unrepaired"
            or right.get("qaoa_execution") != "direct_unrepaired"
        ):
            continue
        pairs.append(
            {
                "output_bit": bit,
                "solver_seed": seed,
                "historical_native_two_qubit": int(left["native"]["two_qubit_gate_count"]),
                "execution_aware_native_two_qubit": int(right["native"]["two_qubit_gate_count"]),
                "delta_execution_minus_historical": int(right["native"]["two_qubit_gate_count"]) - int(left["native"]["two_qubit_gate_count"]),
            }
        )
    deltas_by_bit: dict[int, list[float]] = {}
    for pair in pairs:
        deltas_by_bit.setdefault(int(pair["output_bit"]), []).append(
            float(pair["delta_execution_minus_historical"])
        )
    clusters = [
        {
            "output_bit": bit,
            "solver_seed_count": len(values),
            "mean_delta_execution_minus_historical": statistics.mean(values),
        }
        for bit, values in sorted(deltas_by_bit.items())
    ]
    cluster_means = [
        float(cluster["mean_delta_execution_minus_historical"])
        for cluster in clusters
    ]
    if not cluster_means:
        return {
            "historical_variant": historical,
            "execution_aware_variant": execution,
            "metric": "native.two_qubit_gate_count",
            "direction": "lower_is_better",
            "estimand": (
                "direct_unrepaired_sensitivity"
                if direct_unrepaired_only
                else "intention_to_treat_all_assigned_trials"
            ),
            "pair_count": 0,
            "cluster_count": 0,
            "pairs": [],
            "cluster_means": [],
            "mean_delta_execution_minus_historical": None,
            "bootstrap_95_ci": None,
            "wins_losses_ties": {"wins": 0, "losses": 0, "ties": 0},
        }
    rng = random.Random(int(config["statistics"]["bootstrap_seed"]))
    bootstrap = [
        statistics.mean(rng.choice(cluster_means) for _ in cluster_means)
        for _ in range(int(config["statistics"]["bootstrap_resamples"]))
    ]
    return {
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
        "mean_delta_execution_minus_historical": statistics.mean(cluster_means),
        "bootstrap_95_ci": [_percentile(bootstrap, 0.025), _percentile(bootstrap, 0.975)],
        "wins_losses_ties": {
            "wins": sum(value < 0.0 for value in cluster_means),
            "losses": sum(value > 0.0 for value in cluster_means),
            "ties": sum(value == 0.0 for value in cluster_means),
        },
    }


def _test_dataset(config: dict[str, Any]) -> dict[str, Any]:
    coordinates = get_crypto_oracle_coordinates("AES")
    selected = set(config["test"]["coordinates"])
    payload = {
        "dataset_id": "e4v2-fips197-aes-post-e4-frozen-replication-v1",
        "phase": "replication",
        "legacy_phase_alias": "test",
        "experiment_role": "frozen_replication",
        "dataset_role": "post_e4_frozen_aes_replication",
        "historically_seen_in_E4": True,
        "generalization_claim": False,
        "family": "AES",
        "operation": "SubBytes forward S-box",
        "coordinates": [
            {
                "output_bit": coordinate.output_bit,
                "truth_table_sha256": coordinate.truth_table_sha256,
                "anf_term_count": len(anf_monomials(coordinate.boolean_function)),
            }
            for coordinate in coordinates
            if coordinate.output_bit in selected
        ],
        "solver_seeds": list(config["test"]["solver_seeds"]),
        "endpoint_inputs": list(config["test"]["endpoint_inputs"]),
        "noise_seed_anchors": list(config["test"]["noise_seed_anchors"]),
    }
    return {**payload, "dataset_sha256": dataset_sha256(payload)}


def _qaoa_execution_class(row: dict[str, Any]) -> str:
    scheduler = row["scheduler"]
    if not scheduler["qaoa_attempted"]:
        return "not_applicable"
    if scheduler["qaoa_fallback"]:
        return "fallback"
    if scheduler["qaoa_repaired"]:
        return "direct_repaired"
    if scheduler["qaoa_succeeded"]:
        return "direct_unrepaired"
    return "invalid_unaccounted"


def run_test(
    *,
    config_path: Path,
    config: dict[str, Any],
    calibration_bundle: Path,
    out_dir: Path,
    run_id: str,
    tiny: bool,
) -> Path:
    compute_contract = _enforce_compute_contract(config)
    protocol_lock, protocol_lock_sha, _ = load_protocol_lock(config)
    started = time.perf_counter()
    created_at = utc_now()
    checkpoint, checkpoint_meta = _checkpoint(config)
    source = source_record(PROJECT_ROOT)
    calibration_summary, weights = _load_calibration(calibration_bundle.resolve(), config=config)
    if source["source_tree_sha256"] != calibration_summary.get("source_tree_sha256"):
        raise ValueError(
            "source tree changed after calibration; rerun calibration before test"
        )
    if checkpoint_meta["sha256"] != calibration_summary.get("model_sha256"):
        raise ValueError("model changed after calibration")
    profile_spec = _profile_spec(config)
    frozen_profile, frozen_profile_sha = _frozen_concrete_profile(
        config, profile_spec
    )
    if weights.profile_sha256 != profile_spec.profile_sha256:
        raise ValueError("calibration weights are bound to another profile")
    coordinates = get_crypto_oracle_coordinates("AES")
    if len(coordinates) != 8 or not verify_crypto_oracle_family("AES", coordinates=coordinates):
        raise RuntimeError("AES family verification did not close")
    dataset = _test_dataset(config)
    config_sha = _config_sha256(config)
    selected_bits = set(config["test"]["coordinates"])
    rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = [
        {"event": "replication_started", "legacy_event_alias": "test_started", "run_id": run_id, "created_at_utc": created_at, "tiny": tiny, "weights_sha256": weights.weights_sha256}
    ]
    for solver_seed in config["test"]["solver_seeds"]:
        args = _runner_args(config, solver_seed=int(solver_seed))
        search_config = aes_runner._search_config(args)
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
        for coordinate in coordinates:
            if coordinate.output_bit not in selected_bits:
                continue
            namespace = f"{dataset['dataset_sha256']}:{config_sha}:seed={solver_seed}"
            for variant in VARIANTS:
                row = aes_runner._trial(
                    coordinate=coordinate,
                    coordinates=coordinates,
                    variant=variant,
                    args=args,
                    search_config=search_config,
                    checkpoint=checkpoint,
                    checkpoint_sha256=checkpoint_meta["sha256"],
                    run_id=run_id,
                    execution_utility_adjuster=(adjuster if variant.startswith("execution_aware_") else None),
                    paired_noise_seed_namespace=namespace,
                    include_audit_payload=True,
                    forced_logical_n_qubits=int(
                        config["native_profile"]["frozen_n_qubits"]
                    ),
                )
                row.update(
                    schema_version=TEST_ROW_SCHEMA,
                    record_type="e4_v2_aes_frozen_replication_trial",
                    legacy_record_type_alias="e4_v2_aes_test_trial",
                    phase="replication",
                    legacy_phase_alias="test",
                    experiment_role="frozen_replication",
                    dataset_role="post_e4_frozen_aes_replication",
                    historically_seen_in_E4=True,
                    generalization_claim=False,
                    calibration_run_id=calibration_summary["run_id"],
                    calibration_sha256=calibration_summary["calibration_sha256"],
                    weights_sha256=weights.weights_sha256,
                    profile_spec_sha256=profile_spec.profile_sha256,
                    profile_sha256=frozen_profile_sha,
                    primary_endpoint={
                        "metric": "native.two_qubit_gate_count",
                        "value": int(row["native"]["two_qubit_gate_count"]),
                        "direction": "lower_is_better",
                    },
                    search_config=asdict(search_config),
                    scheduler_config=aes_runner._scheduler_config(
                        args,
                        variant,
                        scheduler_seed=args.scheduler_seed_base
                        + coordinate.output_bit,
                    ).to_dict(),
                    assignment_estimand="intention_to_treat_all_assigned_trials",
                    noisy_success_role="diagnostic_only_not_a_tuning_or_primary_endpoint",
                    qaoa_execution=_qaoa_execution_class(row),
                )
                rows.append(row)
                events.append(
                    {
                        "event": "replication_trial_completed",
                        "legacy_event_alias": "test_trial_completed",
                        "output_bit": coordinate.output_bit,
                        "solver_seed": solver_seed,
                        "variant": variant,
                        "native_two_qubit": row["native"]["two_qubit_gate_count"],
                    }
                )
    rows.sort(key=lambda row: (int(row["output_bit"]), int(row["solver_seed"]), VARIANTS.index(row["variant"])))
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((int(row["output_bit"]), int(row["solver_seed"])), []).append(row)
    fairness = all(
        len(group) == 4
        and len({row["candidate_pool_sha256"] for row in group}) == 1
        and len({canonical_json_bytes(row["raw_scheduler_utilities"]) for row in group}) == 1
        and len({row["scheduler"]["budget_requested"] for row in group}) == 1
        for group in groups.values()
    )
    historical_identity = all(
        row["raw_scheduler_utilities"] == row["adjusted_scheduler_utilities"]
        for row in rows
        if row["variant"].startswith("historical_")
    )
    qaoa = [row for row in rows if row["variant"].endswith("qaoa_shot")]
    primary = _paired_comparison(
        rows,
        historical="historical_qaoa_shot",
        execution="execution_aware_qaoa_shot",
        config=config,
    )
    secondary = _paired_comparison(
        rows,
        historical="historical_greedy",
        execution="execution_aware_greedy",
        config=config,
    )
    direct_unrepaired_sensitivity = _paired_comparison(
        rows,
        historical="historical_qaoa_shot",
        execution="execution_aware_qaoa_shot",
        config=config,
        direct_unrepaired_only=True,
    )
    variants: dict[str, Any] = {}
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        variants[variant] = {
            "trial_count": len(selected),
            "native_two_qubit_mean": statistics.mean(row["native"]["two_qubit_gate_count"] for row in selected),
            "native_gate_count_mean": statistics.mean(row["native"]["native_gate_count"] for row in selected),
            "logical_resource_score_mean": statistics.mean(row["logical_resource_score"] for row in selected),
            "qaoa_direct_unrepaired": sum(
                row["qaoa_execution"] == "direct_unrepaired" for row in selected
            ),
            "qaoa_direct_repaired": sum(
                row["qaoa_execution"] == "direct_repaired" for row in selected
            ),
            "qaoa_fallback": sum(row["qaoa_execution"] == "fallback" for row in selected),
        }
    endpoints = [endpoint for row in rows for endpoint in row["noisy_endpoints"]]
    summary = {
        "schema_version": TEST_SUMMARY_SCHEMA,
        "run_id": run_id,
        "phase": "replication",
        "legacy_phase_alias": "test",
        "experiment_role": "frozen_replication",
        "dataset_role": "post_e4_frozen_aes_replication",
        "historically_seen_in_E4": True,
        "generalization_claim": False,
        "compute_contract": compute_contract,
        "tiny": tiny,
        "formal_statistical_evaluation": not tiny,
        "performance_claim_supported": bool(
            not tiny
            and primary["bootstrap_95_ci"] is not None
            and float(primary["bootstrap_95_ci"][1]) < 0.0
        ),
        "coordinate_count": len(selected_bits),
        "solver_seed_count": len(config["test"]["solver_seeds"]),
        "trial_count": len(rows),
        "variants": variants,
        "primary_endpoint": config["primary_endpoint"],
        "primary_comparison": primary,
        "secondary_comparison": secondary,
        "direct_unrepaired_sensitivity": direct_unrepaired_sensitivity,
        "candidate_pool_fairness_all": fairness,
        "historical_adjusted_equals_raw_all": historical_identity,
        "qaoa_accounting": {
            "rows": len(qaoa),
            "direct_unrepaired": sum(
                row["qaoa_execution"] == "direct_unrepaired" for row in qaoa
            ),
            "direct_repaired": sum(
                row["qaoa_execution"] == "direct_repaired" for row in qaoa
            ),
            "fallback": sum(row["qaoa_execution"] == "fallback" for row in qaoa),
            "invalid_unaccounted": sum(
                row["qaoa_execution"] == "invalid_unaccounted" for row in qaoa
            ),
        },
        "logical_semantics_all": all(
            row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"] and row["reversible_oracle_all_targets_ok"]
            for row in rows
        ),
        "native_contract_all": all(row["native"]["native_gate_set_ok"] and row["native"]["coupling_ok"] for row in rows),
        "frozen_profile": frozen_profile,
        "profile_spec_sha256": profile_spec.profile_sha256,
        "profile_sha256": frozen_profile_sha,
        "all_four_arms_fixed_10q_profile": all(
            row["logical_n_qubits"]
            == int(config["native_profile"]["frozen_n_qubits"])
            and row["native"]["n_qubits"]
            == int(config["native_profile"]["frozen_n_qubits"])
            and row["native"]["profile_sha256"] == frozen_profile_sha
            and row["profile_sha256"] == frozen_profile_sha
            for row in rows
        ),
        "noisy_diagnostic": {
            "role": "diagnostic_only_not_a_tuning_or_primary_endpoint",
            "endpoint_count": len(endpoints),
            "total_shots": sum(endpoint["shots"] for endpoint in endpoints),
            "success_count": sum(endpoint["success_count"] for endpoint in endpoints),
            "actual_simulation_all": all(endpoint["actual_noisy_simulation"] for endpoint in endpoints),
            "hardware_execution_any": any(endpoint["hardware_execution"] for endpoint in endpoints),
        },
        "calibration_binding": {
            "calibration_run_id": calibration_summary["run_id"],
            "calibration_bundle_hint": calibration_bundle.name,
            "calibration_summary_sha256": sha256_file(calibration_bundle / "summary.json"),
            "calibration_sha256": calibration_summary["calibration_sha256"],
            "weights_sha256": weights.weights_sha256,
            "profile_spec_sha256": profile_spec.profile_sha256,
            "profile_sha256": frozen_profile_sha,
            "model_sha256": checkpoint_meta["sha256"],
            "source_tree_sha256": source["source_tree_sha256"],
            "dataset_sha256": dataset["dataset_sha256"],
            "config_sha256": config_sha,
            "calibration_config_sha256": calibration_summary[
                "calibration_config_sha256"
            ],
            "refit_on_test": False,
            "test_noisy_outcome_used_by_utility": False,
        },
        "scope": {
            "synthetic_profile": True,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
            "noisy_success_primary_endpoint": False,
            "native_equivalence_scope": "not-run-at-aes-scale",
            "logical_equivalence_scope": "all-256-inputs-and-both-target-values",
            "experiment_role": "frozen_replication",
            "dataset_role": "post_e4_frozen_aes_replication",
            "historically_seen_in_E4": True,
            "generalization_claim": False,
        },
        "protocol_lock": protocol_lock,
        "protocol_lock_sha256": protocol_lock_sha,
        "claim_boundary": config["claim_boundary"],
    }
    expected_matrix = {
        (bit, seed, variant)
        for bit in selected_bits
        for seed in config["test"]["solver_seeds"]
        for variant in VARIANTS
    }
    actual_matrix = {(row["output_bit"], row["solver_seed"], row["variant"]) for row in rows}
    checks = {
        "complete_four_arm_matrix": actual_matrix == expected_matrix and len(rows) == len(expected_matrix),
        "frozen_candidate_pool_raw_utility_budget": fairness,
        "historical_utility_identity": historical_identity,
        "weights_frozen_without_test_refit": all(
            row["weights_sha256"] == weights.weights_sha256 and row["test_noisy_outcome_used_by_utility"] is False
            for row in rows
        ),
        "qaoa_itt_classification_accounted": all(
            row["qaoa_execution"]
            in {"direct_unrepaired", "direct_repaired", "fallback"}
            for row in qaoa
        ),
        "fixed_10q_profile_all_arms": summary[
            "all_four_arms_fixed_10q_profile"
        ],
        "logical_plan_qasm_semantics": summary["logical_semantics_all"] and all(row.get("plan_trace") and row.get("logical_qasm3") for row in rows),
        "native_and_noisy_contract": summary["native_contract_all"] and summary["noisy_diagnostic"]["actual_simulation_all"] and not summary["noisy_diagnostic"]["hardware_execution_any"],
        "primary_endpoint_locally_frozen_itt": summary["primary_endpoint"]["metric"] == "native.two_qubit_gate_count"
        and summary["primary_endpoint"]["estimand"]
        == "intention_to_treat_all_assigned_trials"
        and summary["noisy_diagnostic"]["role"]
        == "diagnostic_only_not_a_tuning_or_primary_endpoint",
        "replication_boundary_explicit": summary["historically_seen_in_E4"]
        is True
        and summary["experiment_role"] == "frozen_replication"
        and summary["generalization_claim"] is False,
        "frozen_compute_contract": summary["compute_contract"]
        == config["compute_contract"],
        "claim_boundary_no_hardware_or_advantage": summary["scope"]["hardware_execution"] is False and summary["scope"]["quantum_advantage_claimed"] is False,
    }
    verifier = _declared_verifier(run_id, checks)
    elapsed = time.perf_counter() - started
    events.append({"event": "replication_completed", "legacy_event_alias": "test_completed", "run_id": run_id, "elapsed_s": elapsed, "declared_verifier_ok": verifier["ok"]})
    manifest = ExperimentManifest(
        run_id=run_id,
        track=TRACK,
        experiment="e4-v2-post-e4-frozen-aes-four-arm-replication",
        status="complete" if verifier["ok"] else "failed",
        created_at_utc=created_at,
        source=source,
        environment=environment_record(),
        command={
            "entrypoint": "scripts/run_e4_v2_execution_aware.py",
            "phase": "replication",
            "legacy_phase_alias": "test",
            "tiny": tiny,
            "calibration_bundle_hint": calibration_bundle.name,
        },
        dataset=dataset,
        config={
            "runner_schema": RUNNER_SCHEMA,
            "config_path_hint": "configs/xa202609/e4_v2_execution_aware_v1.json",
            "config_file_sha256": sha256_file(config_path),
            "config_sha256": config_sha,
            "effective_config": config,
            "calibration_binding": summary["calibration_binding"],
            "frozen_penalty_weights": weights.canonical_payload(),
            "experiment_role": "frozen_replication",
            "dataset_role": "post_e4_frozen_aes_replication",
            "historically_seen_in_E4": True,
            "generalization_claim": False,
            "protocol_lock": protocol_lock,
            "protocol_lock_sha256": protocol_lock_sha,
            "compute_contract": compute_contract,
        },
        model=checkpoint_meta,
        variants=VARIANTS,
        expected_artifacts=EXPECTED_ARTIFACTS,
        counts={
            "coordinates": len(selected_bits),
            "solver_seeds": len(config["test"]["solver_seeds"]),
            "trials": len(rows),
            "noisy_endpoints": len(endpoints),
            "noisy_shots": summary["noisy_diagnostic"]["total_shots"],
        },
        timing={"wall_s": elapsed},
        claim_boundary=config["claim_boundary"],
    ).to_dict()
    manifest.update(
        experiment_role="frozen_replication",
        dataset_role="post_e4_frozen_aes_replication",
        historically_seen_in_E4=True,
        generalization_claim=False,
        protocol_lock_sha256=protocol_lock_sha,
        compute_contract=compute_contract,
    )
    run_dir = out_dir.expanduser().resolve() / run_id
    _write_and_verify(
        run_dir=run_dir,
        manifest=manifest,
        rows=rows,
        summary=summary,
        verifier=verifier,
        events=events,
    )
    return run_dir


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("calibrate", "test", "all"), default="all")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "xa202609" / "e4_v2_execution_aware_v1.json")
    parser.add_argument("--calibration-bundle", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "results" / "xa202609")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--tiny", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _args()
    config_path = args.config.expanduser().resolve()
    config = load_config(config_path, tiny=args.tiny)
    _enforce_compute_contract(config)
    # Fail before creating any artifact directory if the externally frozen
    # local protocol lock no longer matches config, sources, model or endpoint.
    load_protocol_lock(config)
    created = utc_now()
    base_id = args.run_id or (
        f"{created[:10].replace('-', '')}-{created[11:19].replace(':', '')}"
        f"-e4-v2-{'tiny' if args.tiny else 'execution-aware-v1'}"
    )
    out_dir = args.out_dir.expanduser().resolve()
    if args.phase == "calibrate":
        run_calibration(
            config_path=config_path,
            config=config,
            out_dir=out_dir,
            run_id=base_id,
            tiny=args.tiny,
        )
    elif args.phase == "test":
        if args.calibration_bundle is None:
            raise ValueError("--phase test requires --calibration-bundle")
        run_test(
            config_path=config_path,
            config=config,
            calibration_bundle=args.calibration_bundle.expanduser().resolve(),
            out_dir=out_dir,
            run_id=base_id,
            tiny=args.tiny,
        )
    else:
        if args.calibration_bundle is not None:
            raise ValueError("--phase all creates calibration; do not pass --calibration-bundle")
        calibration_dir = run_calibration(
            config_path=config_path,
            config=config,
            out_dir=out_dir,
            run_id=f"{base_id}-cal",
            tiny=args.tiny,
        )
        run_test(
            config_path=config_path,
            config=config,
            calibration_bundle=calibration_dir,
            out_dir=out_dir,
            run_id=f"{base_id}-test",
            tiny=args.tiny,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
