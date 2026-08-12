#!/usr/bin/env python3
"""Run the sealed E5 external-family cryptographic holdout evaluation.

The formal workflow has three process-separated phases:

``preflight``
    Verify the provenance-closed formal v4 model and calibrate compile-only
    execution penalties on frozen synthetic n=6/7 functions.  Importing the
    crypto evaluation module is forbidden.
``seal``
    Independently verify the preflight bundle and bind it into an immutable
    evaluation lock.  The crypto evaluation module is still forbidden.
``evaluate``
    Validate the static protocol, formal model, preflight bundle and seal;
    only then lazily import and release ASCON followed by PRESENT.

There is intentionally no ``all`` phase.  The split is an access-control and
audit boundary, not merely a command-line convenience.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
import hashlib
import importlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import time
import traceback
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(
    os.environ.get("XA_E5_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).expanduser().resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402

from scripts._pilot_artifacts import (  # noqa: E402
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
)
from scripts.verify_foundation_v4_bundle import (  # noqa: E402
    verify_foundation_v4_bundle,
)
from src.anf_utils import anf_monomials  # noqa: E402
from src.contracts.codec import (  # noqa: E402
    canonical_hex,
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle  # noqa: E402
from src.contracts.search import PlanTrace  # noqa: E402
from src.factor_plan import (  # noqa: E402
    SearchConfig,
    candidate_actions,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import (  # noqa: E402
    FoundationScorer,
    TermThresholdPolicyScorer,
)
from src.hardware.qasm import export_openqasm3  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    native_to_openqasm3,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.search.execution_aware_utility import (  # noqa: E402
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.mcts_scheduler import (  # noqa: E402
    DiversitySchedulerConfig,
    action_redundancy_matrix,
)
from src.search.value_net import LearnedValueEstimator, ValueStats  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit  # noqa: E402


CONFIG_SCHEMA = "xa.e5-external-crypto-holdout-config.v1.1"
STATIC_LOCK_SCHEMA = "xa.e5-static-protocol-lock.v1.1"
EVALUATION_LOCK_SCHEMA = "xa.e5-evaluation-lock.v1.1"
PREFLIGHT_ROW_SCHEMA = "xa.e5-preflight-calibration-row.v1.1"
PREFLIGHT_SUMMARY_SCHEMA = "xa.e5-preflight-summary.v1.1"
SEAL_SUMMARY_SCHEMA = "xa.e5-seal-summary.v1.1"
EVALUATION_ROW_SCHEMA = "xa.e5-external-family-trial.v1.1"
EVALUATION_SUMMARY_SCHEMA = "xa.e5-external-family-summary.v1.1"
DECLARED_VERIFIER_SCHEMA = "xa.e5-declared-verifier.v1.1"
COMPUTE_RUNTIME_SCHEMA = "xa.e5-compute-runtime.v1"
TRACK = "xa202609/e5-external-crypto-holdout-v1.1"
CRYPTO_MODULE = "src.benchmarks.crypto_oracles"

EXECUTION_STATUSES = (
    "classical_invoked",
    "direct_unrepaired",
    "direct_repaired",
    "fallback",
    "not_invoked_degenerate",
    "not_invoked_small_pool",
    "invalid",
)

FEATURES = (
    "native_one_qubit",
    "native_two_qubit",
    "inserted_swap",
    "native_depth",
    "duration_ns",
    "model_risk",
)
ARMS = (
    "heuristic_historical_greedy",
    "v4_historical_greedy",
    "v4_execution_aware_greedy",
    "v4_historical_qaoa_shot",
    "v4_execution_aware_qaoa_shot",
)
V4_FOUR_ARMS = ARMS[1:]
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

_FAILURE_CONTEXT: dict[str, Any] = {
    "rows": [],
    "events": [],
    "holdout_released": False,
    "release_record": None,
}


def _read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha_payload(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be finite and non-negative")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _lower_sha(value: object, name: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{name} must be lowercase SHA-256 hex")
    return digest


def _assert_crypto_module_absent(context: str) -> None:
    if CRYPTO_MODULE in sys.modules:
        raise RuntimeError(
            f"{CRYPTO_MODULE} was imported during {context}; holdout release is forbidden"
        )


def _verify_parent_v1_frozen_contract(config: Mapping[str, Any]) -> None:
    """Bind the amendment to the archived v1 sources and released gate bundles."""

    _assert_crypto_module_absent("parent-v1 frozen-contract verification")
    parent = config["amendment"]["parent_v1"]
    snapshot = (
        PROJECT_ROOT.parent
        / "misc/archive/experiments/xa202609-development/"
        "e5-v1-frozen-snapshot-before-v1.1-20260812"
    ).resolve()
    archived_config_path = snapshot / "configs/xa202609/e5_external_crypto_holdout_v1.json"
    archived_lock_path = (
        snapshot
        / "configs/xa202609/e5_external_crypto_holdout_v1.protocol.lock.json"
    )
    source_bindings = {
        "runner_sha256": snapshot / "scripts/run_e5_external_crypto_holdout.py",
        "verifier_sha256": snapshot / "scripts/verify_e5_external_crypto_holdout_bundle.py",
        "contract_test_sha256": snapshot / "tests/test_e5_external_crypto_holdout.py",
    }
    if (
        not archived_config_path.is_file()
        or sha256_file(archived_config_path) != parent["config_file_sha256"]
        or not archived_lock_path.is_file()
        or any(
            not path.is_file() or sha256_file(path) != parent[name]
            for name, path in source_bindings.items()
        )
    ):
        raise ValueError("archived E5 v1 source/config snapshot changed")
    archived_config = _read_json(archived_config_path)
    archived_lock = _read_json(archived_lock_path)
    if (
        _sha_payload(archived_config) != parent["config_canonical_sha256"]
        or _sha_payload(archived_lock) != parent["static_lock_canonical_sha256"]
    ):
        raise ValueError("archived E5 v1 canonical protocol identity changed")
    frozen_fields = (
        "experiment_role",
        "dataset_role",
        "foundation_v4",
        "holdout_access",
        "preflight",
        "evaluation",
        "search",
        "qaoa",
        "native_profile",
        "compute_contract",
        "weight_selection",
        "primary_endpoint",
        "secondary_endpoints",
        "statistics",
        "noisy_diagnostic",
    )
    if any(config[field] != archived_config[field] for field in frozen_fields):
        raise ValueError("E5 v1.1 changed a parent-v1 frozen scientific field")

    for section in ("preflight", "seal"):
        binding = parent[section]
        bundle = (PROJECT_ROOT / binding["bundle"]).resolve()
        verification = verify_bundle(
            bundle,
            required_roles=(
                "run",
                "raw",
                "summary",
                "verifier",
                "events",
                "stdout",
                "stderr",
            ),
        )
        if not verification.ok:
            raise ValueError(f"parent v1 {section} bundle failed generic verification")
        expected_files = {
            "summary_sha256": "summary.json",
            "manifest_sha256": "artifacts.manifest.json",
            "checksums_sha256": "checksums.sha256",
        }
        if section == "preflight":
            expected_files["raw_sha256"] = "raw.jsonl"
        if any(
            sha256_file(bundle / filename) != binding[name]
            for name, filename in expected_files.items()
        ):
            raise ValueError(f"parent v1 {section} bundle hash changed")
        if section == "seal":
            seal_summary = _read_json(bundle / "summary.json")
            if (
                seal_summary.get("evaluation_lock_sha256")
                != binding["evaluation_lock_sha256"]
                or _sha_payload(seal_summary.get("evaluation_lock"))
                != binding["evaluation_lock_sha256"]
            ):
                raise ValueError("parent v1 evaluation lock binding changed")
    _assert_crypto_module_absent("parent-v1 frozen-contract verified")


def _derived_seed(*parts: object) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _tree_sha256(relative_root: str) -> str:
    root = PROJECT_ROOT / relative_root
    records = [
        {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    ]
    return _sha_payload(records)


def compute_contract_sha256(config: Mapping[str, Any]) -> str:
    return _sha_payload(config["compute_contract"])


def establish_compute_contract(
    config: Mapping[str, Any], *, context: str
) -> dict[str, Any]:
    """Set and verify deterministic CPU inference before any checkpoint use."""

    contract = dict(config["compute_contract"])
    expected = {
        "device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    if contract != expected:
        raise RuntimeError("refusing to establish an unfrozen E5 compute contract")

    before = {
        "device": str(torch.get_default_device()),
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "torch_deterministic_algorithms": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
    }
    setter_errors: list[str] = []
    for name, setter, value in (
        ("device", torch.set_default_device, "cpu"),
        ("torch_interop_threads", torch.set_num_interop_threads, 1),
        ("torch_intraop_threads", torch.set_num_threads, 1),
        (
            "torch_deterministic_algorithms",
            torch.use_deterministic_algorithms,
            True,
        ),
    ):
        try:
            setter(value)
        except Exception as exc:  # postconditions below decide fail-closed status
            setter_errors.append(f"{name}:{type(exc).__name__}:{exc}")

    observed = {
        "device": str(torch.get_default_device()),
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "torch_deterministic_algorithms": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
    }
    if observed != expected:
        detail = "; ".join(setter_errors) if setter_errors else "postcondition mismatch"
        raise RuntimeError(
            f"cannot establish E5 compute contract during {context}: "
            f"observed={observed}; errors={detail}"
        )
    return {
        "schema_version": COMPUTE_RUNTIME_SCHEMA,
        "context": context,
        "compute_contract": contract,
        "compute_contract_sha256": _sha_payload(contract),
        "observed_before": before,
        "observed_after": observed,
        "reset_applied": before != observed,
        "setter_errors_ignored_only_after_matching_postconditions": setter_errors,
        "established": True,
    }


def compute_runtime_matches(
    runtime: object, config: Mapping[str, Any]
) -> bool:
    return bool(
        isinstance(runtime, Mapping)
        and runtime.get("schema_version") == COMPUTE_RUNTIME_SCHEMA
        and runtime.get("compute_contract") == config["compute_contract"]
        and runtime.get("compute_contract_sha256") == compute_contract_sha256(config)
        and runtime.get("observed_after") == config["compute_contract"]
        and runtime.get("established") is True
    )


def load_config(path: str | Path) -> dict[str, Any]:
    """Fail-closed validation of the complete pre-registered E5 contract."""

    config = _read_json(path)
    required = {
        "schema_version",
        "status",
        "experiment",
        "experiment_role",
        "dataset_role",
        "amendment",
        "protocol_lock",
        "foundation_v4",
        "holdout_access",
        "preflight",
        "evaluation",
        "search",
        "qaoa",
        "native_profile",
        "compute_contract",
        "weight_selection",
        "primary_endpoint",
        "secondary_endpoints",
        "statistics",
        "noisy_diagnostic",
        "claim_boundary",
    }
    if set(config) != required or config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("E5 config fields/schema differ from the frozen contract")
    if config.get("status") != "post_release_pre_endpoint_amendment_pre_registered_unrun":
        raise ValueError("E5 v1.1 must remain a pre-endpoint amendment before phases")
    if config.get("experiment_role") != "external_family_holdout_evaluation":
        raise ValueError("E5 experiment role must remain external-family holdout")
    amendment = config["amendment"]
    amendment_required = {
        "schema_version",
        "classification",
        "scientific_reason",
        "parent_v1",
        "incident",
        "exposure_ledger",
        "frozen_invariants",
        "eligibility_rule",
        "root_eligibility_classes",
        "execution_status_taxonomy",
        "degenerate_estimand_rule",
        "schedulable_mechanism_rule",
        "family_activity_rule",
        "direct_sensitivity_rule",
        "failure_evidence_rule",
    }
    if (
        set(amendment) != amendment_required
        or amendment.get("schema_version") != "xa.e5-post-release-amendment.v1.1"
        or amendment.get("classification")
        != "post_release_pre_endpoint_protocol_amendment"
        or amendment.get("root_eligibility_classes")
        != ["schedulable", "degenerate_direct_root"]
        or amendment.get("execution_status_taxonomy") != list(EXECUTION_STATUSES)
    ):
        raise ValueError("E5 v1.1 amendment schema/taxonomy changed")
    parent = amendment["parent_v1"]
    if parent.get("static_lock_canonical_sha256") != (
        "029eb6d3ceb5afdf12fd1a2e406d96919a1ae7fa8f0359d510060d8e44cbde19"
    ):
        raise ValueError("E5 v1 parent static lock binding changed")
    for name in (
        "static_lock_canonical_sha256",
        "config_file_sha256",
        "config_canonical_sha256",
        "runner_sha256",
        "verifier_sha256",
        "contract_test_sha256",
    ):
        _lower_sha(parent[name], f"amendment.parent_v1.{name}")
    for section, names in {
        "preflight": (
            "summary_sha256",
            "raw_sha256",
            "manifest_sha256",
            "checksums_sha256",
            "calibration_sha256",
            "preflight_rows_sha256",
            "weights_sha256",
        ),
        "seal": (
            "summary_sha256",
            "manifest_sha256",
            "checksums_sha256",
            "evaluation_lock_sha256",
        ),
    }.items():
        for name in names:
            _lower_sha(parent[section][name], f"amendment.parent_v1.{section}.{name}")
    incident = amendment["incident"]
    if set(incident) != {
        "path",
        "readme_sha256",
        "attempt_sha256",
        "checksums_sha256",
        "first_release_run_id",
        "first_trial_error",
    }:
        raise ValueError("E5 v1 incident binding fields changed")
    for name in ("readme_sha256", "attempt_sha256", "checksums_sha256"):
        _lower_sha(incident[name], f"amendment.incident.{name}")
    incident_root = (PROJECT_ROOT.parent / incident["path"]).resolve()
    incident_files = {
        "readme_sha256": "README.md",
        "attempt_sha256": "attempt.json",
        "checksums_sha256": "checksums.sha256",
    }
    if any(
        not (incident_root / filename).is_file()
        or sha256_file(incident_root / filename) != incident[name]
        for name, filename in incident_files.items()
    ):
        raise ValueError("E5 v1 incident evidence binding changed")
    exposure = amendment["exposure_ledger"]
    if set(exposure) != {
        "release_gate_completed",
        "tables_verified_at_release",
        "trial_search_entered",
        "trial_search_not_entered_for_remaining_assignments",
        "persisted_trial_rows",
        "performance_outcomes_observed",
        "endpoint_results_observed",
        "comparisons_observed",
        "noisy_outcomes_observed",
        "model_selection_after_release",
        "weight_refit_after_release",
    }:
        raise ValueError("E5 v1 exposure-ledger fields changed")
    if (
        exposure.get("persisted_trial_rows") != 0
        or exposure.get("performance_outcomes_observed") is not False
        or exposure.get("endpoint_results_observed") is not False
        or exposure.get("comparisons_observed") is not False
        or exposure.get("noisy_outcomes_observed") is not False
        or exposure.get("model_selection_after_release") is not False
        or exposure.get("weight_refit_after_release") is not False
    ):
        raise ValueError("E5 v1 exposure ledger no longer describes a pre-endpoint failure")
    if set(amendment["frozen_invariants"]) != {
        "model_changed",
        "weights_changed",
        "search_hyperparameters_changed",
        "qaoa_hyperparameters_changed",
        "solver_seeds_changed",
        "native_profile_changed",
        "primary_endpoint_changed",
        "secondary_endpoints_changed",
    } or any(amendment["frozen_invariants"].values()):
        raise ValueError("E5 v1.1 changed a frozen scientific invariant")
    protocol = config["protocol_lock"]
    if (
        set(protocol) != {"schema_version", "path", "freeze_semantics"}
        or protocol["schema_version"] != STATIC_LOCK_SCHEMA
        or protocol["freeze_semantics"]
        != "freeze_runner_verifier_config_sources_before_preflight"
    ):
        raise ValueError("invalid E5 static protocol declaration")

    foundation = config["foundation_v4"]
    for name in (
        "checkpoint_sha256",
        "model_card_sha256",
        "training_summary_sha256",
        "dataset_manifest_file_sha256",
        "dataset_sha256",
        "source_manifest_sha256",
        "artifact_manifest_sha256",
        "checksums_sha256",
    ):
        _lower_sha(foundation[name], f"foundation_v4.{name}")
    if (
        foundation["required_profile"] != "formal"
        or foundation["required_parameter_count"] != 60_450
        or foundation["required_allowed_num_vars"] != [6, 7]
        or foundation["required_excluded_crypto_widths"] != [4, 5, 8]
        or foundation["required_crypto_training_examples"] != 0
        or foundation["require_current_source"] is not True
    ):
        raise ValueError("foundation v4 gate was weakened")

    access = config["holdout_access"]
    if (
        access["first_allowed_phase"]
        != "evaluate_after_static_lock_model_gate_preflight_and_evaluation_seal"
        or access["preflight_module_import_forbidden"] != CRYPTO_MODULE
    ):
        raise ValueError("holdout release boundary changed")
    _lower_sha(access["registry_sha256"], "holdout_access.registry_sha256")
    if not access.get("family_exclusion_label"):
        raise ValueError("family exclusion label must be explicit")
    if list(access["families"]) != ["ASCON", "PRESENT"]:
        raise ValueError("family order must be ASCON then PRESENT")
    expected_widths = {"ASCON": 5, "PRESENT": 4}
    expected_roles = {"ASCON": "primary", "PRESENT": "secondary"}
    for family, width in expected_widths.items():
        spec = access["families"][family]
        if (
            spec["role"] != expected_roles[family]
            or spec["input_width"] != width
            or spec["output_width"] != width
            or spec["coordinates"] != list(range(width))
            or len(spec["coordinate_truth_table_sha256"]) != width
        ):
            raise ValueError(f"{family} complete-coordinate contract changed")
        _lower_sha(spec["vector_truth_table_sha256"], f"{family}.vector SHA")
        for index, digest in enumerate(spec["coordinate_truth_table_sha256"]):
            _lower_sha(digest, f"{family}[{index}] SHA")

    preflight = config["preflight"]
    if preflight["widths"] != [6, 7] or preflight["cases_per_width"] != 6:
        raise ValueError("preflight must use six frozen n=6 and six frozen n=7 cases")
    if set(preflight["widths"]) & {4, 5, 8}:
        raise ValueError("preflight widths overlap registered crypto widths")
    forbidden = set(preflight["forbidden_inputs"])
    if not {
        "crypto_evaluation_module",
        "ascon_truth_tables",
        "present_truth_tables",
        "evaluation_plan",
        "evaluation_native_result",
        "noisy_endpoint",
    } <= forbidden:
        raise ValueError("preflight forbidden-input contract was weakened")

    evaluation = config["evaluation"]
    if evaluation["family_order"] != ["ASCON", "PRESENT"]:
        raise ValueError("evaluation family order changed")
    seeds = evaluation["solver_seeds"]
    if seeds != [1, 2]:
        raise ValueError("E5 solver seeds are frozen to [1, 2]")
    arms = evaluation["arms"]
    if [arm.get("name") for arm in arms] != list(ARMS):
        raise ValueError("E5 five-arm order changed")
    for arm in arms[1:]:
        if arm.get("learned_policy") is not True or arm.get("learned_value") is not True:
            raise ValueError("all four v4 arms require learned policy and value")
        if arm.get("same_pool_group") != "v4_four_arm":
            raise ValueError("v4 arms must share the frozen pool group")
    if any(arm.get("learned_policy") or arm.get("learned_value") for arm in arms[:1]):
        raise ValueError("heuristic reference must not load learned policy/value")

    search = config["search"]
    for name in (
        "simulations",
        "candidate_top_k",
        "max_factor_size",
        "scheduler_pool_size",
        "scheduler_budget",
        "scheduler_min_candidates",
        "scheduler_seed_base",
    ):
        _positive_int(search[name], f"search.{name}")
    if search["max_factor_ancilla"] not in (0, 1):
        raise ValueError("max_factor_ancilla must be zero or one")
    if search["policy_term_threshold"] != 0 or search["learned_value_required"] is not True:
        raise ValueError("E5 must activate learned policy and value at schedulable v4 roots")
    if search["simulations"] < search["scheduler_budget"]:
        raise ValueError("simulations must cover every admitted root edge")
    if not (
        search["scheduler_budget"]
        < search["scheduler_min_candidates"]
        <= search["scheduler_pool_size"]
        <= search["candidate_top_k"]
        <= 12
    ):
        raise ValueError("invalid common candidate-pool/budget contract")
    for name in ("redundancy_weight", "redundancy_alpha", "utility_clip"):
        _finite_nonnegative(search[name], f"search.{name}")
    if not 0.0 <= float(search["redundancy_alpha"]) <= 1.0:
        raise ValueError("redundancy_alpha must lie in [0, 1]")
    if float(search["utility_clip"]) <= 0.0:
        raise ValueError("utility_clip must be positive")

    qaoa = config["qaoa"]
    if qaoa["mode"] != "shot" or float(qaoa["measurement_bitflip_probability"]) != 0.0:
        raise ValueError("QAOA must remain ideal-circuit shot mode with zero readout bitflip")
    for name in ("p", "shots", "optimizer_restarts"):
        _positive_int(qaoa[name], f"qaoa.{name}")
    if not isinstance(qaoa["optimizer_steps"], int) or qaoa["optimizer_steps"] < 0:
        raise ValueError("qaoa.optimizer_steps must be non-negative")

    profile = config["native_profile"]
    if (
        profile["family"] != "synthetic-heavy-hex-like-fixed-10q-v1"
        or profile["frozen_n_qubits"] != 10
        or profile["native_gate_set"] != ["rz", "sx", "x", "cx"]
    ):
        raise ValueError("E5 requires one fixed synthetic 10q rz/sx/x/cx profile")
    for name in ("one_qubit_error", "two_qubit_error", "readout_error"):
        value = _finite_nonnegative(profile[name], f"native_profile.{name}")
        if value > 1.0:
            raise ValueError(f"native_profile.{name} must be a probability")
    for name in ("one_qubit_duration_ns", "two_qubit_duration_ns"):
        if _finite_nonnegative(profile[name], f"native_profile.{name}") <= 0.0:
            raise ValueError(f"native_profile.{name} must be positive")

    if config["compute_contract"] != {
        "device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }:
        raise ValueError(
            "E5 compute contract must freeze CPU, one intra/inter-op thread, "
            "and deterministic algorithms"
        )

    selection = config["weight_selection"]
    if selection["rule"] != "fixed-mixture-median-positive-scale-v1":
        raise ValueError("weight-selection rule changed")
    mixture = selection["feature_mixture"]
    if set(mixture) != set(FEATURES):
        raise ValueError("feature mixture must declare every component")
    shares = {name: _finite_nonnegative(mixture[name], name) for name in FEATURES}
    if not math.isclose(math.fsum(shares.values()), 1.0, abs_tol=1e-12):
        raise ValueError("feature mixture must sum to one")
    if shares["model_risk"] != 0.0:
        raise ValueError("preflight cannot fit model risk")

    endpoint = config["primary_endpoint"]
    if (
        endpoint["family"] != "ASCON"
        or endpoint["metric"] != "native.two_qubit_gate_count"
        or endpoint["comparison"]
        != "v4_execution_aware_qaoa_shot-minus-v4_historical_qaoa_shot"
        or endpoint["estimand"] != "intention_to_treat_all_assigned_trials"
        or endpoint["cluster_unit"] != ["family", "output_bit"]
        or endpoint["seed_aggregation_within_cluster"] != "arithmetic_mean"
        or endpoint["direct_unrepaired_sensitivity"] is not True
        or endpoint["claim_rule"]
        != "effect_estimate_only_no_binary_superiority_due_five_clusters"
    ):
        raise ValueError("primary endpoint/cluster claim contract changed")
    statistics_config = config["statistics"]
    _positive_int(statistics_config["bootstrap_resamples"], "bootstrap_resamples")
    _positive_int(statistics_config["bootstrap_seed"], "bootstrap_seed")
    if (
        float(statistics_config["confidence_level"]) != 0.95
        or statistics_config["exact_cluster_sign_flip"] is not True
        or statistics_config[
            "solver_seeds_are_repeated_measurements_not_independent_clusters"
        ]
        is not True
    ):
        raise ValueError("cluster statistics contract changed")
    if config["noisy_diagnostic"] != {
        "enabled": False,
        "role": "separate_post_seal_diagnostic_only",
        "may_change_primary_summary": False,
    }:
        raise ValueError("formal E5 must not run noisy diagnostics")
    _verify_parent_v1_frozen_contract(config)
    return copy.deepcopy(config)


def load_static_protocol_lock(
    config: Mapping[str, Any],
    *,
    lock_path: str | Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Bind config, E5 sources, stable cores, formal model and endpoint."""

    path = Path(lock_path or config["protocol_lock"]["path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    lock = _read_json(path)
    required = {
        "schema_version",
        "freeze_semantics",
        "config",
        "amendment",
        "amendment_sha256",
        "parent_v1_static_lock_canonical_sha256",
        "sources",
        "source_tree_sha256",
        "foundation_v4",
        "crypto_registry",
        "compute_contract",
        "compute_contract_sha256",
        "primary_endpoint",
        "primary_endpoint_sha256",
        "arm_matrix_sha256",
    }
    if set(lock) != required or lock.get("schema_version") != STATIC_LOCK_SCHEMA:
        raise ValueError("E5 static protocol lock fields/schema differ")
    if lock["freeze_semantics"] != "frozen_before_preflight_and_holdout_release":
        raise ValueError("E5 static lock freeze semantics changed")
    config_record = lock["config"]
    config_path = PROJECT_ROOT / "configs/xa202609/e5_external_crypto_holdout_v1.json"
    if (
        config_record.get("path")
        != "configs/xa202609/e5_external_crypto_holdout_v1.json"
        or config_record.get("file_sha256") != sha256_file(config_path)
        or config_record.get("canonical_sha256") != _sha_payload(config)
    ):
        raise ValueError("static lock does not bind the effective config")
    if (
        lock["amendment"] != config["amendment"]
        or lock["amendment_sha256"] != _sha_payload(config["amendment"])
        or lock["parent_v1_static_lock_canonical_sha256"]
        != config["amendment"]["parent_v1"]["static_lock_canonical_sha256"]
    ):
        raise ValueError("static lock does not bind the v1.1 amendment/parent")
    expected_sources = {
        "runner": "scripts/run_e5_external_crypto_holdout.py",
        "verifier": "scripts/verify_e5_external_crypto_holdout_bundle.py",
        "contract_test": "tests/test_e5_external_crypto_holdout.py",
        "execution_aware_core": "src/search/execution_aware_utility.py",
        "foundation_adapter": "src/foundation/adapter.py",
        "value_estimator": "src/search/value_net.py",
        "solver": "src/nmcts_solver.py",
        "scheduler": "src/search/mcts_scheduler.py",
        "compiler": "src/hardware/superconducting.py",
    }
    sources = lock["sources"]
    if set(sources) != set(expected_sources):
        raise ValueError("static lock source roles changed")
    for role, relative in expected_sources.items():
        record = sources[role]
        if record.get("path") != relative or record.get("sha256") != sha256_file(
            PROJECT_ROOT / relative
        ):
            raise ValueError(f"static source mismatch: {role}")
    if lock["source_tree_sha256"] != _tree_sha256("src"):
        raise ValueError("static lock source tree mismatch")
    foundation = config["foundation_v4"]
    if lock["foundation_v4"] != {
        "bundle": foundation["bundle"],
        "checkpoint_sha256": foundation["checkpoint_sha256"],
        "model_card_sha256": foundation["model_card_sha256"],
        "dataset_sha256": foundation["dataset_sha256"],
        "source_manifest_sha256": foundation["source_manifest_sha256"],
    }:
        raise ValueError("static lock formal v4 identity changed")
    registry = lock["crypto_registry"]
    if (
        registry.get("path") != config["holdout_access"]["registry_path"]
        or registry.get("sha256") != config["holdout_access"]["registry_sha256"]
        or sha256_file(PROJECT_ROOT / registry["path"]) != registry["sha256"]
    ):
        raise ValueError("static lock crypto registry mismatch")
    if (
        lock["compute_contract"] != config["compute_contract"]
        or lock["compute_contract_sha256"] != compute_contract_sha256(config)
    ):
        raise ValueError("static lock compute contract mismatch")
    endpoint = config["primary_endpoint"]
    if (
        lock["primary_endpoint"] != endpoint
        or lock["primary_endpoint_sha256"] != _sha_payload(endpoint)
        or lock["arm_matrix_sha256"] != _sha_payload(config["evaluation"]["arms"])
    ):
        raise ValueError("static lock endpoint/arm matrix mismatch")
    return lock, _sha_payload(lock)


def verify_formal_v4_gate(config: Mapping[str, Any]) -> dict[str, Any]:
    """Verify formal provenance, model card and every frozen hash link."""

    _assert_crypto_module_absent("foundation-v4 gate")
    compute_runtime = establish_compute_contract(
        config, context="runner-foundation-v4-before-checkpoint-inference"
    )
    foundation = config["foundation_v4"]
    bundle = (PROJECT_ROOT / foundation["bundle"]).resolve()
    result = verify_foundation_v4_bundle(bundle, require_current_source=True)
    if not result.get("ok"):
        raise ValueError(f"formal v4 bundle failed verification: {result.get('errors')}")
    if (
        result.get("profile") != "formal"
        or result.get("formal_training_completed") is not True
        or result.get("performance_evidence") is not False
        or result.get("checkpoint_sha256") != foundation["checkpoint_sha256"]
        or result.get("dataset_sha256") != foundation["dataset_sha256"]
        or result.get("parameter_count") != foundation["required_parameter_count"]
    ):
        raise ValueError("formal v4 verifier result differs from E5 gate")
    exact_files = {
        "checkpoint.pt": "checkpoint_sha256",
        "model_card.json": "model_card_sha256",
        "training_summary.json": "training_summary_sha256",
        "dataset_manifest.json": "dataset_manifest_file_sha256",
        "source_manifest.json": "source_manifest_sha256",
        "artifacts.manifest.json": "artifact_manifest_sha256",
        "checksums.sha256": "checksums_sha256",
    }
    for relative, key in exact_files.items():
        if sha256_file(bundle / relative) != foundation[key]:
            raise ValueError(f"formal v4 file hash changed: {relative}")
    card = _read_json(bundle / "model_card.json")
    summary = _read_json(bundle / "training_summary.json")
    config_snapshot = _read_json(bundle / "config_snapshot.json")
    if (
        card.get("model_id") != "boolean_oracle_fm_v4"
        or card.get("training", {}).get("profile") != "formal"
        or card.get("training", {}).get("parent_checkpoint") is not None
        or card.get("training", {}).get("v3_weights_loaded") is not False
        or card.get("artifact", {}).get("sha256") != foundation["checkpoint_sha256"]
        or card.get("architecture", {}).get("parameter_count")
        != foundation["required_parameter_count"]
        or card.get("data", {}).get("allowed_num_vars")
        != foundation["required_allowed_num_vars"]
        or card.get("data", {}).get("crypto_oracle_training_examples") != 0
        or card.get("data", {}).get("crypto_excluded") is not True
        or card.get("data", {}).get("evaluation_not_accessed") is not True
        or card.get("data", {}).get("test_split") is not None
        or summary.get("profile") != "formal"
        or summary.get("formal_training_completed") is not True
        or summary.get("performance_evidence") is not False
        or config_snapshot.get("crypto_exclusion", {}).get("excluded_input_widths")
        != foundation["required_excluded_crypto_widths"]
        or config_snapshot.get("crypto_exclusion", {}).get(
            "evaluation_module_imported_during_training"
        )
        is not False
    ):
        raise ValueError("formal v4 model-card/data exclusion gate failed")
    checkpoint = (PROJECT_ROOT / foundation["checkpoint"]).resolve()
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    parameter_count = sum(parameter.numel() for parameter in scorer.model.parameters())
    if parameter_count != foundation["required_parameter_count"]:
        raise ValueError("loaded formal v4 parameter count changed")
    if any(parameter.device.type != "cpu" for parameter in scorer.model.parameters()):
        raise RuntimeError("formal v4 scorer violated the frozen CPU compute contract")
    _assert_crypto_module_absent("foundation-v4 checkpoint load")
    return {
        "schema_version": "xa.e5-foundation-v4-gate.v1",
        "bundle_hint": bundle.name,
        "checkpoint_sha256": foundation["checkpoint_sha256"],
        "model_card_sha256": foundation["model_card_sha256"],
        "dataset_sha256": foundation["dataset_sha256"],
        "source_manifest_sha256": foundation["source_manifest_sha256"],
        "profile": "formal",
        "parameter_count": parameter_count,
        "crypto_training_examples": 0,
        "evaluation_module_imported": False,
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "compute_runtime": compute_runtime,
        "ok": True,
    }


def _profile_spec(config: Mapping[str, Any]) -> SyntheticExecutionProfileSpec:
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
    config: Mapping[str, Any], profile_spec: SyntheticExecutionProfileSpec
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
    return payload, _sha_payload(payload)


def _search_config(config: Mapping[str, Any]) -> SearchConfig:
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


def _scheduler_config(
    config: Mapping[str, Any], arm: str, *, scheduler_seed: int
) -> DiversitySchedulerConfig:
    if arm not in ARMS and arm != "preflight_historical_greedy":
        raise ValueError(f"unknown E5 arm: {arm}")
    search = config["search"]
    qaoa = config["qaoa"]
    return DiversitySchedulerConfig(
        method="qaoa" if arm.endswith("qaoa_shot") else "greedy",
        budget_requested=int(search["scheduler_budget"]),
        pool_size=int(search["scheduler_pool_size"]),
        min_candidates=int(search["scheduler_min_candidates"]),
        max_depth=0,
        redundancy_weight=float(search["redundancy_weight"]),
        redundancy_alpha=float(search["redundancy_alpha"]),
        utility_clip=float(search["utility_clip"]),
        exact_max_candidates=12,
        seed=int(scheduler_seed),
        qaoa_mode="shot",
        qaoa_p=int(qaoa["p"]),
        qaoa_shots=int(qaoa["shots"]),
        qaoa_noise_bitflip_probability=0.0,
        qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
        qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
    )


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


def _truth_table_sha256(bf: BooleanFunction) -> str:
    byte_count = ((1 << bf.n) + 7) // 8
    return hashlib.sha256(
        int(bf.truth_table).to_bytes(byte_count, "little")
    ).hexdigest()


def _checkpoint_path(config: Mapping[str, Any]) -> Path:
    path = Path(str(config["foundation_v4"]["checkpoint"]))
    path = path if path.is_absolute() else PROJECT_ROOT / path
    path = path.resolve()
    if sha256_file(path) != config["foundation_v4"]["checkpoint_sha256"]:
        raise ValueError("formal v4 checkpoint changed")
    return path


def _preflight_cases(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Generate frozen compile-only functions without touching hold-out code."""

    _assert_crypto_module_absent("preflight case generation")
    spec = config["preflight"]
    cases: list[dict[str, Any]] = []
    ordinal = 0
    for n in spec["widths"]:
        for index in range(int(spec["cases_per_width"])):
            seed = int(spec["seed_base"]) + ordinal
            ordinal += 1
            bf = BooleanFunction(int(n), random.Random(seed).getrandbits(1 << int(n)))
            digest = _truth_table_sha256(bf)
            cases.append(
                {
                    "case_id": f"e5-preflight-n{n}-k{index:02d}",
                    "instance_seed": seed,
                    "n": int(n),
                    "truth_table_hex": canonical_hex(
                        int(bf.truth_table), min_nibbles=1 << max(0, int(n) - 2)
                    ),
                    "truth_table_sha256": digest,
                    "anf_term_count": len(anf_monomials(bf)),
                    "bf": bf,
                }
            )
    if len({case["truth_table_sha256"] for case in cases}) != len(cases):
        raise RuntimeError("duplicate E5 preflight truth table")
    _assert_crypto_module_absent("preflight case generation complete")
    return cases


def _preflight_rows(
    *,
    cases: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
    checkpoint: Path,
    profile_spec: SyntheticExecutionProfileSpec,
    run_id: str,
) -> list[dict[str, Any]]:
    """Collect compile features from v4 pools; no outcome is available here."""

    _assert_crypto_module_absent("preflight row construction")
    search_config = _search_config(config)
    zero_weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=_sha_payload(
            [
                {key: case[key] for key in ("case_id", "n", "truth_table_sha256")}
                for case in cases
            ]
        ),
        profile_sha256=profile_spec.profile_sha256,
    )
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    policy = TermThresholdPolicyScorer(
        scorer, int(config["search"]["policy_term_threshold"])
    )
    if any(parameter.device.type != "cpu" for parameter in scorer.model.parameters()):
        raise RuntimeError("E5 preflight scorer violated the CPU compute contract")
    rows: list[dict[str, Any]] = []
    for case in cases:
        terms = frozenset(anf_monomials(case["bf"]))
        value_stats = ValueStats()
        value = LearnedValueEstimator(scorer, search_config, value_stats)
        scheduler_seed = int(config["search"]["scheduler_seed_base"]) + int(
            case["instance_seed"]
        )
        scheduler = _scheduler_config(
            config, "preflight_historical_greedy", scheduler_seed=scheduler_seed
        )
        adjuster = make_root_rollout_execution_utility_adjuster(
            n_inputs=int(case["n"]),
            search_config=search_config,
            profile_spec=profile_spec,
            penalty_weights=zero_weights,
            expected_profile_sha256=profile_spec.profile_sha256,
            execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
        )
        solver = NeuralMCTSSolver(
            config=search_config,
            simulations=0,
            seed=int(case["instance_seed"]),
            neural_scorer=policy,
            value_estimator=value,
            rollout_scorer=None,
            scheduler_config=scheduler,
            execution_utility_adjuster=adjuster,
        )
        node = solver._node(StateKey(terms, 0, 0))
        solver._expand(node)
        if not node.actions:
            raise RuntimeError(f"empty E5 preflight pool: {case['case_id']}")
        solver._schedule_node(node, 0)
        if node.scheduler_decision is None:
            raise RuntimeError("preflight scheduler emitted no decision")
        diagnostics = dict(node.scheduler_decision.diagnostics)
        width = int(diagnostics["candidate_count"])
        actions = tuple(node.actions[:width])
        raw = [float(value_) for value_ in diagnostics["raw_utilities"]]
        redundancy = action_redundancy_matrix(
            actions, alpha=float(config["search"]["redundancy_alpha"])
        )
        feedback = diagnostics.get("execution_feedback", {})
        candidates = feedback.get("diagnostics", {}).get("candidates", [])
        if len(candidates) != width:
            raise RuntimeError("preflight compile candidates do not match pool")
        pool = {
            "schema_version": "xa.e5-preflight-candidate-pool.v1",
            "case_id": case["case_id"],
            "truth_table_sha256": case["truth_table_sha256"],
            "node_id": diagnostics["node_id"],
            "candidate_count": width,
            "budget_requested": int(config["search"]["scheduler_budget"]),
            "budget_effective": min(int(config["search"]["scheduler_budget"]), width),
            "action_signatures": [_action_signature(action) for action in actions],
            "raw_utilities": raw,
            "redundancy": [[float(item) for item in row] for row in redundancy],
        }
        rows.append(
            {
                "schema_version": PREFLIGHT_ROW_SCHEMA,
                "record_type": "e5_preflight_compile_only_calibration",
                "run_id": run_id,
                "phase": "preflight",
                "case_id": case["case_id"],
                "instance_seed": case["instance_seed"],
                "n": case["n"],
                "truth_table_hex": case["truth_table_hex"],
                "truth_table_sha256": case["truth_table_sha256"],
                "anf_term_count": case["anf_term_count"],
                "checkpoint_sha256": config["foundation_v4"]["checkpoint_sha256"],
                "profile_spec_sha256": profile_spec.profile_sha256,
                "profile_sha256": candidates[0]["concrete_profile_sha256"],
                "candidate_pool": pool,
                "candidate_pool_sha256": _sha_payload(pool),
                "raw_scheduler_utilities": raw,
                "compile_time_candidates": candidates,
                "learned_policy_active_at_root": True,
                "learned_value_enabled": True,
                "learned_value_stats": value_stats.as_dict(),
                "compile_time_only": True,
                "crypto_module_imported": False,
                "crypto_evaluation_module_imported": False,
                "holdout_truth_table_accessed": False,
                "holdout_oracle_accessed": False,
                "evaluation_result_accessed": False,
                "evaluation_outcome_accessed": False,
                "noisy_endpoint_accessed": False,
                "hardware_execution": False,
            }
        )
    _assert_crypto_module_absent("preflight row construction complete")
    return rows


def select_frozen_weights(
    *,
    rows: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
    calibration_sha256: str,
    profile_sha256: str,
) -> tuple[FrozenExecutionPenaltyWeights, dict[str, Any]]:
    """Apply the sole pre-registered median scaling rule."""

    target = float(config["weight_selection"]["target_penalty_at_component_medians"])
    mixture = {
        name: float(config["weight_selection"]["feature_mixture"][name])
        for name in FEATURES
    }
    scales: dict[str, float] = {}
    coefficients: dict[str, float] = {}
    for name in FEATURES:
        values = [
            float(candidate["resource_components"][name])
            for row in rows
            for candidate in row["compile_time_candidates"]
        ]
        if any(not math.isfinite(item) or item < 0.0 for item in values):
            raise ValueError(f"non-finite preflight feature: {name}")
        positive = [item for item in values if item > 0.0]
        scale = statistics.median(positive) if positive else 0.0
        scales[name] = scale
        share = mixture[name]
        if share > 0.0 and scale <= 0.0:
            raise ValueError(f"positive mixture share has zero preflight scale: {name}")
        coefficients[name] = 0.0 if share == 0.0 else target * share / scale
    weights = FrozenExecutionPenaltyWeights(
        calibration_sha256=calibration_sha256,
        profile_sha256=profile_sha256,
        **coefficients,
    )
    rule = {
        "schema_version": "xa.e5-weight-selection-rule.v1",
        "rule": "fixed-mixture-median-positive-scale-v1",
        "target_penalty_at_component_medians": target,
        "feature_mixture": mixture,
        "positive_median_scales": scales,
        "coefficients": coefficients,
        "candidate_record_count": sum(
            len(row["compile_time_candidates"]) for row in rows
        ),
        "model_fit": False,
        "holdout_used": False,
        "noisy_outcome_used": False,
    }
    return weights, rule


def _parent_v1_preflight_evidence(
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    """Read the frozen v1 calibration only; never route it through v1.1 gates."""

    _assert_crypto_module_absent("parent-v1 preflight evidence load")
    binding = config["amendment"]["parent_v1"]["preflight"]
    bundle = (PROJECT_ROOT / binding["bundle"]).resolve()
    verification = verify_bundle(
        bundle,
        required_roles=("run", "raw", "summary", "verifier", "events", "stdout", "stderr"),
    )
    if not verification.ok:
        raise ValueError(f"parent v1 preflight bundle failed generic verification: {verification.errors}")
    files = {
        "summary_sha256": "summary.json",
        "raw_sha256": "raw.jsonl",
        "manifest_sha256": "artifacts.manifest.json",
        "checksums_sha256": "checksums.sha256",
    }
    if any(sha256_file(bundle / filename) != binding[name] for name, filename in files.items()):
        raise ValueError("parent v1 preflight file hash changed")
    summary = _read_json(bundle / "summary.json")
    rows = [
        json.loads(line)
        for line in (bundle / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        summary.get("calibration_sha256") != binding["calibration_sha256"]
        or summary.get("preflight_rows_sha256") != binding["preflight_rows_sha256"]
        or summary.get("weights_sha256") != binding["weights_sha256"]
        or len(rows) != 12
    ):
        raise ValueError("parent v1 preflight scientific binding changed")
    _assert_crypto_module_absent("parent-v1 preflight evidence loaded")
    return summary, rows, bundle


def _preflight_scientific_projection(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Drop version/run labels while retaining every scientific row field."""

    return [
        {key: copy.deepcopy(value) for key, value in row.items() if key not in {"schema_version", "run_id"}}
        for row in rows
    ]


def _declared_verifier(run_id: str, checks: Mapping[str, bool]) -> dict[str, Any]:
    values = {str(key): bool(value) for key, value in checks.items()}
    return {
        "schema_version": DECLARED_VERIFIER_SCHEMA,
        "run_id": run_id,
        "checks": values,
        "ok": all(values.values()),
        "evidence_ok": all(values.values()),
        "experiment_completed": all(values.values()),
        "independent_recomputation": False,
    }


def _run_record(
    *,
    run_id: str,
    phase: str,
    status: str,
    created_at: str,
    config_path: Path,
    config: Mapping[str, Any],
    source: Mapping[str, Any],
    counts: Mapping[str, int],
    model: Mapping[str, Any] | None,
    binding: Mapping[str, Any],
    compute_runtime: Mapping[str, Any],
    elapsed_s: float,
) -> dict[str, Any]:
    return {
        "schema_version": "xa.e5-external-crypto-holdout-run.v1.1",
        "run_id": run_id,
        "track": TRACK,
        "experiment": str(config["experiment"]),
        "phase": phase,
        "status": status,
        "evidence_ok": status == "complete",
        "experiment_completed": status == "complete",
        "created_at_utc": created_at,
        "source": dict(source),
        "environment": environment_record(),
        "command": {
            "entrypoint": "scripts/run_e5_external_crypto_holdout.py",
            "phase": phase,
        },
        "config": {
            "runner_schema": "xa.e5-external-crypto-holdout-runner.v1.1",
            "path_hint": config_path.name,
            "file_sha256": sha256_file(config_path),
            "config_sha256": _sha_payload(config),
            "canonical_sha256": _sha_payload(config),
            "effective_config": copy.deepcopy(dict(config)),
        },
        "model": None if model is None else dict(model),
        "binding": dict(binding),
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "compute_runtime": copy.deepcopy(dict(compute_runtime)),
        "counts": dict(counts),
        "timing": {"wall_s": float(elapsed_s)},
        "claim_boundary": config["claim_boundary"],
        "amendment": {
            "classification": config["amendment"]["classification"],
            "sha256": _sha_payload(config["amendment"]),
            "parent_v1_static_lock_canonical_sha256": config["amendment"][
                "parent_v1"
            ]["static_lock_canonical_sha256"],
        },
        "expected_artifacts": list(EXPECTED_ARTIFACTS),
        "holdout_accessed": phase == "evaluate",
    }


def _write_and_independently_verify(
    *,
    run_dir: Path,
    run_record: dict[str, Any],
    rows: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    declared: dict[str, Any],
    events: Sequence[dict[str, Any]],
) -> None:
    bundle = write_pilot_bundle(
        run_dir=run_dir,
        run_record=run_record,
        raw_records=rows,
        summary=summary,
        verifier=declared,
        events=events,
        track=TRACK,
    )
    if not bundle.ok:
        raise RuntimeError(f"E5 artifact bundle failed: {bundle.errors}")
    verifier_module = importlib.import_module(
        "scripts.verify_e5_external_crypto_holdout_bundle"
    )
    independent = verifier_module.verify_e5_external_crypto_holdout_bundle(run_dir)
    if not independent.get("ok"):
        raise RuntimeError(f"independent E5 verifier failed: {independent.get('errors')}")
    print(f"bundle={run_dir}")
    print("bundle_ok=True")
    print("independent_verifier_ok=True")


def _reserve_run_id(out_dir: Path, run_id: str) -> Path:
    """Reserve one requested identifier without creating the artifact bundle."""

    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = out_dir / run_id
    if run_dir.exists():
        raise FileExistsError(f"E5 run id already exists: {run_dir}")
    reservation = out_dir / f".{run_id}.e5-reservation"
    descriptor = os.open(reservation, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(
            descriptor,
            canonical_json_bytes(
                {
                    "schema_version": "xa.e5-run-reservation.v1.1",
                    "run_id": run_id,
                    "created_at_utc": utc_now(),
                }
            ),
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return reservation


def _failure_bundle_path(out_dir: Path, run_id: str, error_text: str) -> Path:
    requested = out_dir / run_id
    reservation = out_dir / f".{run_id}.e5-reservation"
    if not requested.exists() and not reservation.exists():
        return requested
    suffix = sha256_bytes(
        f"{run_id}:{time.time_ns()}:{error_text}".encode("utf-8")
    )[:12]
    sibling = out_dir / f"{run_id}-failed-attempt-{suffix}"
    if sibling.exists():
        raise FileExistsError(f"failed-attempt bundle collision: {sibling}")
    return sibling


def _write_failed_attempt_bundle(
    *,
    out_dir: Path,
    run_id: str,
    phase: str,
    config_path: Path,
    config: Mapping[str, Any] | None,
    exception: BaseException,
    traceback_text: str,
    terminal_capture_available: bool,
    retrospective: bool = False,
    attempt_run_id: str | None = None,
    requested_command: Mapping[str, Any] | None = None,
) -> Path:
    """Persist one immutable nine-file failure record without claiming completion."""

    out_dir.mkdir(parents=True, exist_ok=True)
    error_text = f"{type(exception).__name__}: {exception}"
    run_dir = _failure_bundle_path(out_dir, run_id, error_text)
    rows = [copy.deepcopy(dict(row)) for row in _FAILURE_CONTEXT.get("rows", [])]
    events = [copy.deepcopy(dict(event)) for event in _FAILURE_CONTEXT.get("events", [])]
    evidence_created_at = utc_now()
    requested_attempt_run_id = attempt_run_id or run_id
    config_sha = _sha_payload(config) if config is not None else None
    config_file_sha = sha256_file(config_path) if config_path.is_file() else None
    amendment = None if config is None else config.get("amendment")
    parent_v1 = (
        amendment["parent_v1"] if isinstance(amendment, Mapping) else None
    )
    attempt_config = (
        {
            "schema_version": "xa.e5-attempt-config-binding.v1",
            "config_file_sha256": parent_v1["config_file_sha256"],
            "config_canonical_sha256": parent_v1["config_canonical_sha256"],
            "static_lock_canonical_sha256": parent_v1[
                "static_lock_canonical_sha256"
            ],
            "runner_sha256": parent_v1["runner_sha256"],
            "verifier_sha256": parent_v1["verifier_sha256"],
            "contract_test_sha256": parent_v1["contract_test_sha256"],
            "protocol_version": "v1",
        }
        if retrospective and parent_v1 is not None
        else {
            "schema_version": "xa.e5-attempt-config-binding.v1.1",
            "config_file_sha256": config_file_sha,
            "config_canonical_sha256": config_sha,
            "protocol_version": "v1.1",
        }
    )
    evidence_recorder_config = {
        "schema_version": CONFIG_SCHEMA if config is not None else None,
        "config_file_sha256": config_file_sha,
        "config_canonical_sha256": config_sha,
        "amendment_sha256": (
            _sha_payload(amendment) if amendment is not None else None
        ),
        "role": "retrospective_evidence_recorder" if retrospective else "failure_evidence_recorder",
    }
    summary = {
        "schema_version": "xa.e5-failed-attempt-summary.v1.1",
        "run_id": run_dir.name,
        "requested_run_id": requested_attempt_run_id,
        "phase": phase,
        "status": "failed_attempt_evidence",
        "evidence_ok": True,
        "experiment_completed": False,
        "retrospective": bool(retrospective),
        "record_created_at_utc": evidence_created_at,
        "attempt_time_utc": None if retrospective else evidence_created_at,
        "attempt_time_status": (
            "unknown_not_captured" if retrospective else "failure_record_creation_time"
        ),
        "terminal_capture_available": bool(terminal_capture_available),
        "terminal_transcript_fabricated": False,
        "exception": {
            "type": type(exception).__name__,
            "message": str(exception),
            "traceback_persisted": bool(traceback_text),
        },
        "completed_trial_row_count": len(rows),
        "holdout_released": bool(_FAILURE_CONTEXT.get("holdout_released")),
        "release_record": copy.deepcopy(_FAILURE_CONTEXT.get("release_record")),
        "performance_outcome_available": bool(rows),
        "endpoint_summary_available": False,
        "comparison_available": False,
        "model_selection_performed": False,
        "weight_refit_performed": False,
        "noisy_diagnostic_performed": False,
        "attempt_config": attempt_config,
        "evidence_recorder_config": evidence_recorder_config,
        "amendment_sha256": _sha_payload(amendment) if amendment is not None else None,
        "parent_v1_binding": (
            copy.deepcopy(amendment["parent_v1"])
            if isinstance(amendment, Mapping)
            else None
        ),
    }
    run = {
        "schema_version": "xa.e5-external-crypto-holdout-run.v1.1",
        "run_id": run_dir.name,
        "requested_run_id": requested_attempt_run_id,
        "track": TRACK,
        "phase": phase,
        "status": "failed",
        "evidence_ok": True,
        "experiment_completed": False,
        "record_created_at_utc": evidence_created_at,
        "attempt_time_utc": None if retrospective else evidence_created_at,
        "attempt_time_status": (
            "unknown_not_captured" if retrospective else "failure_record_creation_time"
        ),
        "command": dict(
            requested_command
            or {
                "entrypoint": "scripts/run_e5_external_crypto_holdout.py",
                "phase": phase,
            }
        ),
        "attempt_config": attempt_config,
        "evidence_recorder_config": evidence_recorder_config,
        "exception": summary["exception"],
        "counts": {
            "rows": len(rows),
            "holdout_coordinates": 0,
            "noisy_shots": 0,
        },
        "expected_artifacts": list(EXPECTED_ARTIFACTS),
    }
    verifier = {
        "schema_version": "xa.e5-failed-attempt-verifier.v1.1",
        "run_id": run_dir.name,
        "checks": {
            "failure_not_mislabelled_complete": True,
            "evidence_and_completion_separated": True,
            "terminal_transcript_not_fabricated": True,
            "endpoint_summary_absent": True,
            "model_selection_and_refit_absent": True,
        },
        "ok": True,
        "evidence_ok": True,
        "experiment_completed": False,
        "independent_recomputation": False,
    }
    events.append(
        {
            "event": "failed_attempt_persisted",
            "run_id": run_dir.name,
            "requested_run_id": requested_attempt_run_id,
            "phase": phase,
            "created_at_utc": evidence_created_at,
            "exception_type": type(exception).__name__,
        }
    )
    stdout_text = (
        "RETROSPECTIVE EXPLANATION, NOT ORIGINAL TERMINAL CAPTURE. No terminal "
        "stdout transcript was captured for the original v1 process; this evidence "
        "does not reconstruct one.\n"
        if retrospective
        else "Runner failure evidence bundle created; stdout was not internally captured.\n"
    )
    stderr_text = (
        "RETROSPECTIVE EXPLANATION, NOT ORIGINAL TERMINAL CAPTURE. No terminal "
        "stderr transcript was captured for the original v1 process. "
        f"The bound incident record reports: {error_text}\n"
        if retrospective
        else traceback_text
    )
    writer = ArtifactBundleWriter(run_dir)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(row) + "\n" for row in rows),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", verifier)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text("stdout", "stdout.log", stdout_text)
    writer.add_text("stderr", "stderr.log", stderr_text)
    writer.finalize(bundle_metadata={"run_id": run_dir.name, "track": TRACK})
    verification = verify_bundle(
        run_dir,
        required_roles=("run", "raw", "summary", "verifier", "events", "stdout", "stderr"),
    )
    if not verification.ok:
        raise RuntimeError(f"failed-attempt evidence bundle is invalid: {verification.errors}")
    return run_dir


def write_retrospective_v1_failure_bundle(config_path: str | Path, run_dir: str | Path) -> Path:
    """Create the explicit v1 retrospective without inventing terminal output."""

    global _FAILURE_CONTEXT
    config_file = Path(config_path).expanduser().resolve()
    config = load_config(config_file)
    incident = config["amendment"]["incident"]
    _FAILURE_CONTEXT = {
        "rows": [],
        "events": [
            {
                "event": "retrospective_bound_to_v1_incident",
                "incident": copy.deepcopy(incident),
                "parent_v1": copy.deepcopy(config["amendment"]["parent_v1"]),
            }
        ],
        "holdout_released": True,
        "release_record": {
            "tables_verified_at_release": ["ASCON", "PRESENT"],
            "first_trial_entered": {
                "family": "ASCON",
                "output_bit": 0,
                "solver_seed": 1,
                "arm": "heuristic_historical_greedy",
            },
            "remaining_trials_entered": False,
        },
    }
    target = Path(run_dir).expanduser().resolve()
    exception = RuntimeError(str(incident["first_trial_error"]))
    return _write_failed_attempt_bundle(
        out_dir=target.parent,
        run_id=target.name,
        phase="evaluate",
        config_path=config_file,
        config=config,
        exception=exception,
        traceback_text="",
        terminal_capture_available=False,
        retrospective=True,
        attempt_run_id=str(incident["first_release_run_id"]),
        requested_command={
            "entrypoint": "scripts/run_e5_external_crypto_holdout.py",
            "phase": "evaluate",
            "run_id": incident["first_release_run_id"],
            "preflight_bundle": config["amendment"]["parent_v1"]["preflight"]["bundle"],
            "seal_bundle": config["amendment"]["parent_v1"]["seal"]["bundle"],
        },
    )


def run_preflight(
    *,
    config_path: Path,
    config: Mapping[str, Any],
    out_dir: Path,
    run_id: str,
) -> Path:
    """Freeze compile-only weights while the hold-out module is inaccessible."""

    started = time.perf_counter()
    created_at = utc_now()
    _assert_crypto_module_absent("preflight entry")
    compute_runtime = establish_compute_contract(
        config, context="runner-preflight-before-checkpoint-inference"
    )
    _, static_lock_sha = load_static_protocol_lock(config)
    model_gate = verify_formal_v4_gate(config)
    checkpoint = _checkpoint_path(config)
    source = source_record(PROJECT_ROOT)
    profile_spec = _profile_spec(config)
    frozen_profile, profile_sha = _frozen_concrete_profile(config, profile_spec)
    cases = _preflight_cases(config)
    rows = _preflight_rows(
        cases=cases,
        config=config,
        checkpoint=checkpoint,
        profile_spec=profile_spec,
        run_id=run_id,
    )
    parent_summary, parent_rows, parent_bundle = _parent_v1_preflight_evidence(config)
    scientific_projection_sha = _sha_payload(_preflight_scientific_projection(rows))
    parent_scientific_projection_sha = _sha_payload(
        _preflight_scientific_projection(parent_rows)
    )
    if scientific_projection_sha != parent_scientific_projection_sha:
        raise RuntimeError("v1.1 preflight scientific rows differ from frozen parent v1")
    calibration_payload = {
        "schema_version": "xa.e5-preflight-dataset.v1",
        "generator": config["preflight"]["generator"],
        "cases": [
            {key: row[key] for key in ("case_id", "instance_seed", "n", "truth_table_sha256")}
            for row in rows
        ],
    }
    preflight_rows_sha = _sha_payload(rows)
    preflight_evidence = {
        "schema_version": "xa.e5-preflight-evidence-binding.v1",
        "config_sha256": _sha_payload(config),
        "foundation_v4_checkpoint_sha256": model_gate["checkpoint_sha256"],
        "foundation_v4_model_card_sha256": model_gate["model_card_sha256"],
        "foundation_v4_source_manifest_sha256": model_gate["source_manifest_sha256"],
        "profile_spec_sha256": profile_spec.profile_sha256,
        "concrete_profile_sha256": profile_sha,
        "compute_contract_sha256": compute_contract_sha256(config),
        "preflight_rows_sha256": preflight_rows_sha,
    }
    reproduction_evidence_sha = _sha_payload(preflight_evidence)
    calibration_sha = str(parent_summary["calibration_sha256"])
    weights, rule = select_frozen_weights(
        rows=rows,
        config=config,
        calibration_sha256=calibration_sha,
        profile_sha256=profile_spec.profile_sha256,
    )
    if (
        weights.canonical_payload() != parent_summary["frozen_penalty_weights"]
        or weights.weights_sha256 != parent_summary["weights_sha256"]
        or rule != parent_summary["weight_selection"]
    ):
        raise RuntimeError("v1.1 recomputed weights are not exactly equal to parent v1")
    _assert_crypto_module_absent("preflight completion")
    access = {
        "crypto_module_imported": False,
        "ascon_accessed": False,
        "present_accessed": False,
        "evaluation_result_accessed": False,
        "noisy_endpoint_accessed": False,
        "compile_time_only": True,
    }
    summary = {
        "schema_version": PREFLIGHT_SUMMARY_SCHEMA,
        "run_id": run_id,
        "phase": "preflight",
        "evidence_ok": True,
        "experiment_completed": True,
        "amendment_classification": config["amendment"]["classification"],
        "amendment_sha256": _sha_payload(config["amendment"]),
        "row_count": len(rows),
        "width_counts": {
            str(n): sum(row["n"] == n for row in rows)
            for n in config["preflight"]["widths"]
        },
        "config_sha256": _sha_payload(config),
        "static_lock_sha256": static_lock_sha,
        "source_tree_sha256": source["source_tree_sha256"],
        "model_gate": model_gate,
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "compute_runtime": compute_runtime,
        "profile_spec_sha256": profile_spec.profile_sha256,
        "profile_sha256": profile_sha,
        "frozen_profile": frozen_profile,
        "calibration_dataset": calibration_payload,
        "preflight_evidence_binding": preflight_evidence,
        "reproduction_evidence_sha256": reproduction_evidence_sha,
        "scientific_projection_sha256": scientific_projection_sha,
        "parent_v1_binding": {
            "bundle_hint": parent_bundle.name,
            "summary_sha256": sha256_file(parent_bundle / "summary.json"),
            "raw_sha256": sha256_file(parent_bundle / "raw.jsonl"),
            "calibration_sha256": parent_summary["calibration_sha256"],
            "weights_sha256": parent_summary["weights_sha256"],
            "scientific_projection_sha256": parent_scientific_projection_sha,
            "exact_weights_reused_after_independent_recomputation": True,
        },
        "preflight_rows_sha256": preflight_rows_sha,
        "calibration_sha256": calibration_sha,
        "frozen_penalty_weights": weights.canonical_payload(),
        "weights_sha256": weights.weights_sha256,
        "weight_selection": rule,
        "learned_policy_active_all": all(
            row["learned_policy_active_at_root"] for row in rows
        ),
        "learned_value_enabled_all": all(row["learned_value_enabled"] for row in rows),
        "access_contract": access,
        "performance_evidence": False,
        "holdout_model_selection": False,
        "holdout_accessed": False,
        "hardware_execution": False,
    }
    checks = {
        "twelve_n6_n7_rows": len(rows) == 12
        and {row["n"] for row in rows} == {6, 7},
        "unique_synthetic_tables": len({row["truth_table_sha256"] for row in rows})
        == len(rows),
        "compile_only_access_closed": access["compile_time_only"] is True
        and all(
            value is False for key, value in access.items() if key != "compile_time_only"
        ),
        "fixed_profile_all_candidates": all(
            candidate["logical_n_qubits"]
            == int(config["native_profile"]["frozen_n_qubits"])
            and candidate["concrete_profile_sha256"] == profile_sha
            for row in rows
            for candidate in row["compile_time_candidates"]
        ),
        "formal_model_gate": model_gate["ok"] is True,
        "compute_contract_established_before_inference": compute_runtime_matches(
            compute_runtime, config
        )
        and model_gate["compute_contract_sha256"] == compute_contract_sha256(config),
        "weights_no_holdout_fit": rule["holdout_used"] is False
        and rule["noisy_outcome_used"] is False,
        "parent_v1_scientific_rows_exact": scientific_projection_sha
        == parent_scientific_projection_sha,
        "parent_v1_weights_exact": weights.canonical_payload()
        == parent_summary["frozen_penalty_weights"]
        and weights.weights_sha256 == parent_summary["weights_sha256"],
    }
    declared = _declared_verifier(run_id, checks)
    summary["evidence_ok"] = True
    summary["experiment_completed"] = bool(declared["ok"])
    elapsed = time.perf_counter() - started
    run = _run_record(
        run_id=run_id,
        phase="preflight",
        status="complete" if declared["ok"] else "failed",
        created_at=created_at,
        config_path=config_path,
        config=config,
        source=source,
        counts={"rows": len(rows), "holdout_coordinates": 0, "noisy_shots": 0},
        model=model_record(checkpoint, PROJECT_ROOT),
        binding={
            "static_lock_sha256": static_lock_sha,
            "weights_sha256": weights.weights_sha256,
            "compute_contract_sha256": compute_contract_sha256(config),
        },
        compute_runtime=compute_runtime,
        elapsed_s=elapsed,
    )
    events = [
        {"event": "preflight_started", "run_id": run_id, "created_at_utc": created_at},
        {
            "event": "preflight_completed",
            "run_id": run_id,
            "elapsed_s": elapsed,
            "weights_sha256": weights.weights_sha256,
        },
    ]
    run_dir = out_dir.resolve() / run_id
    _write_and_independently_verify(
        run_dir=run_dir,
        run_record=run,
        rows=rows,
        summary=summary,
        declared=declared,
        events=events,
    )
    return run_dir


def _weights_from_payload(payload: Mapping[str, Any]) -> FrozenExecutionPenaltyWeights:
    expected = {
        "schema",
        "calibration_sha256",
        "profile_sha256",
        "normalization",
        *FEATURES,
    }
    if set(payload) != expected:
        raise ValueError("frozen penalty-weight payload fields changed")
    return FrozenExecutionPenaltyWeights(
        calibration_sha256=str(payload["calibration_sha256"]),
        profile_sha256=str(payload["profile_sha256"]),
        **{name: float(payload[name]) for name in FEATURES},
    )


def _independent_bundle_result(bundle: Path) -> dict[str, Any]:
    module = importlib.import_module("scripts.verify_e5_external_crypto_holdout_bundle")
    result = module.verify_e5_external_crypto_holdout_bundle(bundle.resolve())
    if not result.get("ok"):
        raise ValueError(f"E5 prerequisite bundle failed verification: {result.get('errors')}")
    return result


def _load_verified_preflight(
    bundle: Path,
    *,
    config: Mapping[str, Any],
    static_lock_sha256: str,
    current_source_tree_sha256: str,
) -> tuple[dict[str, Any], FrozenExecutionPenaltyWeights, str]:
    _assert_crypto_module_absent("preflight bundle verification")
    _independent_bundle_result(bundle)
    summary = _read_json(bundle / "summary.json")
    summary_sha = sha256_file(bundle / "summary.json")
    if (
        summary.get("schema_version") != PREFLIGHT_SUMMARY_SCHEMA
        or summary.get("phase") != "preflight"
        or summary.get("amendment_classification")
        != config["amendment"]["classification"]
        or summary.get("amendment_sha256") != _sha_payload(config["amendment"])
        or summary.get("row_count") != 12
        or summary.get("config_sha256") != _sha_payload(config)
        or summary.get("static_lock_sha256") != static_lock_sha256
        or summary.get("source_tree_sha256") != current_source_tree_sha256
        or summary.get("model_gate", {}).get("checkpoint_sha256")
        != config["foundation_v4"]["checkpoint_sha256"]
        or summary.get("compute_contract") != config["compute_contract"]
        or summary.get("compute_contract_sha256") != compute_contract_sha256(config)
        or not compute_runtime_matches(summary.get("compute_runtime"), config)
        or summary.get("model_gate", {}).get("compute_contract_sha256")
        != compute_contract_sha256(config)
        or summary.get("access_contract")
        != {
            "crypto_module_imported": False,
            "ascon_accessed": False,
            "present_accessed": False,
            "evaluation_result_accessed": False,
            "noisy_endpoint_accessed": False,
            "compile_time_only": True,
        }
        or summary.get("holdout_model_selection") is not False
        or summary.get("performance_evidence") is not False
        or summary.get("parent_v1_binding", {}).get("weights_sha256")
        != config["amendment"]["parent_v1"]["preflight"]["weights_sha256"]
        or summary.get("parent_v1_binding", {}).get(
            "exact_weights_reused_after_independent_recomputation"
        )
        is not True
    ):
        raise ValueError("preflight summary does not satisfy the E5 release gate")
    weights = _weights_from_payload(summary["frozen_penalty_weights"])
    if (
        weights.weights_sha256 != summary.get("weights_sha256")
        or weights.calibration_sha256 != summary.get("calibration_sha256")
        or weights.profile_sha256 != summary.get("profile_spec_sha256")
        or weights.weights_sha256
        != config["amendment"]["parent_v1"]["preflight"]["weights_sha256"]
        or weights.calibration_sha256
        != config["amendment"]["parent_v1"]["preflight"]["calibration_sha256"]
    ):
        raise ValueError("preflight frozen-weight binding changed")
    _assert_crypto_module_absent("preflight bundle verified")
    return summary, weights, summary_sha


def _evaluation_lock_payload(
    *,
    config: Mapping[str, Any],
    static_lock_sha256: str,
    preflight_bundle: Path,
    preflight_summary: Mapping[str, Any],
    preflight_summary_sha256: str,
) -> dict[str, Any]:
    endpoint = config["primary_endpoint"]
    preflight_binding = {
        "bundle_hint": preflight_bundle.name,
        "summary_sha256": preflight_summary_sha256,
        "raw_sha256": sha256_file(preflight_bundle / "raw.jsonl"),
        "run_id": preflight_summary["run_id"],
        "calibration_sha256": preflight_summary["calibration_sha256"],
        "weights_sha256": preflight_summary["weights_sha256"],
        "profile_spec_sha256": preflight_summary["profile_spec_sha256"],
        "profile_sha256": preflight_summary["profile_sha256"],
        "compute_contract_sha256": preflight_summary["compute_contract_sha256"],
    }
    evaluation_contract = {
        "amendment": config["amendment"],
        "family_order": config["evaluation"]["family_order"],
        "solver_seeds": config["evaluation"]["solver_seeds"],
        "arms": config["evaluation"]["arms"],
        "search": config["search"],
        "qaoa": config["qaoa"],
        "native_profile": config["native_profile"],
        "compute_contract": config["compute_contract"],
        "primary_endpoint": config["primary_endpoint"],
        "secondary_endpoints": config["secondary_endpoints"],
        "statistics": config["statistics"],
        "noisy_diagnostic": config["noisy_diagnostic"],
        "family_exclusion_label": config["holdout_access"]["family_exclusion_label"],
        "family_contracts": config["holdout_access"]["families"],
    }
    return {
        "schema_version": EVALUATION_LOCK_SCHEMA,
        "freeze_semantics": "frozen_after_verified_preflight_before_holdout_release",
        "amendment_classification": config["amendment"]["classification"],
        "amendment_sha256": _sha_payload(config["amendment"]),
        "parent_v1_static_lock_canonical_sha256": config["amendment"]["parent_v1"][
            "static_lock_canonical_sha256"
        ],
        "parent_v1_evaluation_lock_sha256": config["amendment"]["parent_v1"][
            "seal"
        ]["evaluation_lock_sha256"],
        "incident_sha256": _sha_payload(config["amendment"]["incident"]),
        "exposure_ledger_sha256": _sha_payload(
            config["amendment"]["exposure_ledger"]
        ),
        "config_sha256": _sha_payload(config),
        "static_lock_sha256": static_lock_sha256,
        "source_tree_sha256": preflight_summary["source_tree_sha256"],
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "formal_v4": {
            "checkpoint_sha256": config["foundation_v4"]["checkpoint_sha256"],
            "model_card_sha256": config["foundation_v4"]["model_card_sha256"],
            "dataset_sha256": config["foundation_v4"]["dataset_sha256"],
            "source_manifest_sha256": config["foundation_v4"]["source_manifest_sha256"],
        },
        "preflight": preflight_binding,
        "preflight_binding": preflight_binding,
        "weights_sha256": preflight_summary["weights_sha256"],
        "frozen_penalty_weights": preflight_summary["frozen_penalty_weights"],
        "profile_spec_sha256": preflight_summary["profile_spec_sha256"],
        "profile_sha256": preflight_summary["profile_sha256"],
        "holdout_registry": {
            "path": config["holdout_access"]["registry_path"],
            "sha256": config["holdout_access"]["registry_sha256"],
            "family_exclusion_label": config["holdout_access"]["family_exclusion_label"],
            "family_order": config["evaluation"]["family_order"],
            "families_sha256": _sha_payload(config["holdout_access"]["families"]),
        },
        "evaluation_matrix": {
            "arms": [arm["name"] for arm in config["evaluation"]["arms"]],
            "arms_sha256": _sha_payload(config["evaluation"]["arms"]),
            "solver_seeds": config["evaluation"]["solver_seeds"],
            "expected_rows": 90,
            "same_pool_group": "v4_four_arm",
            "eligibility_rule": config["amendment"]["eligibility_rule"],
            "execution_status_taxonomy": list(EXECUTION_STATUSES),
            "degenerate_assigned_to_all_arms_and_itt": True,
            "schedulable_only_secondary": True,
        },
        "native_profile": {
            "frozen_n_qubits": config["native_profile"]["frozen_n_qubits"],
            "profile_spec_sha256": preflight_summary["profile_spec_sha256"],
            "profile_sha256": preflight_summary["profile_sha256"],
        },
        "primary_endpoint": endpoint,
        "primary_endpoint_sha256": _sha_payload(endpoint),
        "statistics": config["statistics"],
        "noisy_diagnostic": config["noisy_diagnostic"],
        "evaluation_contract": evaluation_contract,
        "holdout_accessed_while_sealing": False,
        "holdout_release": {
            "allowed_phase": "evaluate",
            "first_import_must_follow_all_gate_checks": True,
            "release_token": "e5-sealed-evaluate-only",
            "model_or_protocol_selection_after_release": False,
        },
    }


def run_seal(
    *,
    config_path: Path,
    config: Mapping[str, Any],
    preflight_bundle: Path,
    out_dir: Path,
    run_id: str,
) -> Path:
    """Seal the verified preflight into a hold-out release lock."""

    started = time.perf_counter()
    created_at = utc_now()
    _assert_crypto_module_absent("seal entry")
    compute_runtime = establish_compute_contract(
        config, context="runner-seal-before-checkpoint-inference"
    )
    _, static_lock_sha = load_static_protocol_lock(config)
    model_gate = verify_formal_v4_gate(config)
    source = source_record(PROJECT_ROOT)
    preflight, weights, preflight_sha = _load_verified_preflight(
        preflight_bundle.resolve(),
        config=config,
        static_lock_sha256=static_lock_sha,
        current_source_tree_sha256=source["source_tree_sha256"],
    )
    evaluation_lock = _evaluation_lock_payload(
        config=config,
        static_lock_sha256=static_lock_sha,
        preflight_bundle=preflight_bundle.resolve(),
        preflight_summary=preflight,
        preflight_summary_sha256=preflight_sha,
    )
    evaluation_lock_sha = _sha_payload(evaluation_lock)
    access = {
        "crypto_module_imported": False,
        "crypto_evaluation_module_imported": False,
        "ascon_accessed": False,
        "present_accessed": False,
        "evaluation_started": False,
        "release_authorized_for_future_process": True,
    }
    _assert_crypto_module_absent("seal completion")
    summary = {
        "schema_version": SEAL_SUMMARY_SCHEMA,
        "run_id": run_id,
        "phase": "seal",
        "evidence_ok": True,
        "experiment_completed": True,
        "amendment_classification": config["amendment"]["classification"],
        "amendment_sha256": _sha_payload(config["amendment"]),
        "config_sha256": _sha_payload(config),
        "static_lock_sha256": static_lock_sha,
        "source_tree_sha256": source["source_tree_sha256"],
        "model_gate": model_gate,
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "compute_runtime": compute_runtime,
        "preflight_binding": {
            "bundle_hint": preflight_bundle.name,
            "run_id": preflight["run_id"],
            "summary_sha256": preflight_sha,
            "raw_sha256": sha256_file(preflight_bundle / "raw.jsonl"),
            "calibration_sha256": preflight["calibration_sha256"],
            "weights_sha256": weights.weights_sha256,
            "profile_spec_sha256": preflight["profile_spec_sha256"],
            "profile_sha256": preflight["profile_sha256"],
            "compute_contract_sha256": preflight["compute_contract_sha256"],
        },
        "evaluation_lock": evaluation_lock,
        "evaluation_lock_sha256": evaluation_lock_sha,
        "access_contract": access,
        "performance_evidence": False,
        "row_count": 0,
        "holdout_accessed": False,
    }
    checks = {
        "preflight_independently_verified": True,
        "formal_model_reverified": model_gate["ok"] is True,
        "weights_bound_without_refit": weights.weights_sha256
        == preflight["weights_sha256"],
        "complete_evaluation_matrix_frozen": evaluation_lock["evaluation_matrix"][
            "expected_rows"
        ]
        == 90,
        "primary_endpoint_frozen": evaluation_lock["primary_endpoint_sha256"]
        == _sha_payload(config["primary_endpoint"]),
        "holdout_still_unloaded": CRYPTO_MODULE not in sys.modules,
        "compute_contract_established": compute_runtime_matches(compute_runtime, config)
        and evaluation_lock["compute_contract_sha256"]
        == compute_contract_sha256(config),
    }
    declared = _declared_verifier(run_id, checks)
    summary["evidence_ok"] = True
    summary["experiment_completed"] = bool(declared["ok"])
    elapsed = time.perf_counter() - started
    run = _run_record(
        run_id=run_id,
        phase="seal",
        status="complete" if declared["ok"] else "failed",
        created_at=created_at,
        config_path=config_path,
        config=config,
        source=source,
        counts={"rows": 0, "holdout_coordinates": 0, "noisy_shots": 0},
        model=model_record(_checkpoint_path(config), PROJECT_ROOT),
        binding={
            "static_lock_sha256": static_lock_sha,
            "preflight_summary_sha256": preflight_sha,
            "evaluation_lock_sha256": evaluation_lock_sha,
            "compute_contract_sha256": compute_contract_sha256(config),
        },
        compute_runtime=compute_runtime,
        elapsed_s=elapsed,
    )
    events = [
        {"event": "seal_started", "run_id": run_id, "created_at_utc": created_at},
        {
            "event": "seal_completed",
            "run_id": run_id,
            "elapsed_s": elapsed,
            "evaluation_lock_sha256": evaluation_lock_sha,
            "holdout_module_imported": False,
        },
    ]
    run_dir = out_dir.resolve() / run_id
    _write_and_independently_verify(
        run_dir=run_dir,
        run_record=run,
        rows=[],
        summary=summary,
        declared=declared,
        events=events,
    )
    return run_dir


def _load_verified_seal(
    bundle: Path,
    *,
    config: Mapping[str, Any],
    static_lock_sha256: str,
    preflight_bundle: Path,
    preflight_summary: Mapping[str, Any],
    preflight_summary_sha256: str,
) -> tuple[dict[str, Any], str]:
    _assert_crypto_module_absent("seal bundle verification")
    _independent_bundle_result(bundle)
    summary = _read_json(bundle / "summary.json")
    if (
        summary.get("schema_version") != SEAL_SUMMARY_SCHEMA
        or summary.get("phase") != "seal"
        or summary.get("amendment_classification")
        != config["amendment"]["classification"]
        or summary.get("amendment_sha256") != _sha_payload(config["amendment"])
        or summary.get("config_sha256") != _sha_payload(config)
        or summary.get("static_lock_sha256") != static_lock_sha256
        or summary.get("preflight_binding", {}).get("summary_sha256")
        != preflight_summary_sha256
        or summary.get("compute_contract") != config["compute_contract"]
        or summary.get("compute_contract_sha256") != compute_contract_sha256(config)
        or not compute_runtime_matches(summary.get("compute_runtime"), config)
        or summary.get("access_contract", {}).get("crypto_module_imported") is not False
        or summary.get("access_contract", {}).get("evaluation_started") is not False
    ):
        raise ValueError("seal summary does not satisfy the E5 release gate")
    expected = _evaluation_lock_payload(
        config=config,
        static_lock_sha256=static_lock_sha256,
        preflight_bundle=preflight_bundle,
        preflight_summary=preflight_summary,
        preflight_summary_sha256=preflight_summary_sha256,
    )
    if (
        summary.get("evaluation_lock") != expected
        or summary.get("evaluation_lock_sha256") != _sha_payload(expected)
    ):
        raise ValueError("evaluation lock differs from independently rebuilt lock")
    _assert_crypto_module_absent("seal bundle verified")
    return expected, sha256_file(bundle / "summary.json")


def _release_holdout_families_after_all_gates(
    config: Mapping[str, Any],
) -> tuple[dict[str, tuple[object, ...]], dict[str, Any]]:
    """The only function permitted to import/load external-family tables."""

    _assert_crypto_module_absent("evaluate release boundary")
    registry_path = PROJECT_ROOT / config["holdout_access"]["registry_path"]
    if sha256_file(registry_path) != config["holdout_access"]["registry_sha256"]:
        raise ValueError("holdout registry changed immediately before release")
    module = importlib.import_module(CRYPTO_MODULE)
    label = str(config["holdout_access"]["family_exclusion_label"])
    if getattr(module, "CRYPTO_HOLDOUT_EXCLUSION_LABEL") != label:
        raise ValueError("runtime family-exclusion label changed")
    families: dict[str, tuple[object, ...]] = {}
    records: dict[str, Any] = {}
    for family in config["evaluation"]["family_order"]:
        expected = config["holdout_access"]["families"][family]
        coordinates = tuple(
            module.get_crypto_holdout_oracle_coordinates(
                family, family_exclusion_label=label
            )
        )
        if not module.verify_crypto_holdout_oracle_family(
            family,
            coordinates=coordinates,
            family_exclusion_label=label,
        ):
            raise ValueError(f"{family} holdout family failed complete verification")
        spec = module.get_crypto_oracle_family_spec(family)
        coordinate_hashes = [coordinate.truth_table_sha256 for coordinate in coordinates]
        if (
            spec.benchmark_partition != "external_crypto_family_holdout"
            or spec.training_access_allowed is not False
            or spec.family_exclusion_label != label
            or spec.vector_truth_table_sha256 != expected["vector_truth_table_sha256"]
            or spec.input_width != expected["input_width"]
            or spec.output_width != expected["output_width"]
            or [coordinate.output_bit for coordinate in coordinates]
            != expected["coordinates"]
            or coordinate_hashes != expected["coordinate_truth_table_sha256"]
        ):
            raise ValueError(f"{family} runtime holdout contract changed")
        families[family] = coordinates
        records[family] = {
            "role": expected["role"],
            "coordinate_count": len(coordinates),
            "vector_truth_table_sha256": spec.vector_truth_table_sha256,
            "coordinate_truth_table_sha256": coordinate_hashes,
            "complete_domain_verified": True,
            "bijective": True,
            "training_access_allowed": False,
            "family_exclusion_label": label,
        }
    return families, {
        "schema_version": "xa.e5-holdout-release-record.v1",
        "module": CRYPTO_MODULE,
        "registry_sha256": config["holdout_access"]["registry_sha256"],
        "release_phase": "evaluate",
        "family_order": list(families),
        "families": records,
        "model_or_protocol_selection_after_release": False,
    }


def _verify_reversible_oracle_all_targets(circuit: object, coordinate: object) -> bool:
    for x in range(1 << int(getattr(coordinate, "input_width"))):
        prefix = [
            (x >> bit) & 1 for bit in range(int(getattr(coordinate, "input_width")))
        ]
        for target_input in (0, 1):
            bits = prefix + [target_input]
            bits.extend(0 for _ in range(int(getattr(circuit, "n_qubits")) - len(bits)))
            for gate in getattr(circuit, "gates"):
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
            expected = target_input ^ int(coordinate.evaluate(x))
            width = int(getattr(coordinate, "input_width"))
            if bits[:width] != prefix or bits[width] != expected or any(bits[width + 1 :]):
                return False
    return True


def _qaoa_execution_class(diagnostics: Mapping[str, Any], arm: str) -> str:
    if diagnostics.get("root_eligibility") == "degenerate_direct_root":
        return "not_invoked_degenerate"
    if not arm.endswith("qaoa_shot"):
        return "classical_invoked"
    if diagnostics.get("status") == "qaoa_not_invoked":
        return "not_invoked_small_pool"
    if diagnostics.get("qaoa_fallback"):
        return "fallback"
    if diagnostics.get("qaoa_repaired"):
        return "direct_repaired"
    if diagnostics.get("qaoa_succeeded"):
        return "direct_unrepaired"
    return "invalid"


def _evaluation_trial(
    *,
    coordinate: object,
    arm_spec: Mapping[str, Any],
    solver_seed: int,
    config: Mapping[str, Any],
    scorer: FoundationScorer,
    checkpoint_sha256: str,
    weights: FrozenExecutionPenaltyWeights,
    profile_spec: SyntheticExecutionProfileSpec,
    frozen_profile: Mapping[str, Any],
    frozen_profile_sha256: str,
    run_id: str,
) -> dict[str, Any]:
    arm = str(arm_spec["name"])
    terms = frozenset(anf_monomials(coordinate.boolean_function))
    search_config = _search_config(config)
    structural_root_actions = candidate_actions(
        terms,
        0,
        0,
        search_config,
        neural_scorer=None,
    )
    root_action_count = len(structural_root_actions)
    root_eligibility = (
        "schedulable" if root_action_count > 0 else "degenerate_direct_root"
    )
    scheduler_seed = _derived_seed(
        "e5-scheduler-v1",
        config["search"]["scheduler_seed_base"],
        coordinate.family,
        coordinate.output_bit,
        solver_seed,
    )
    scheduler = _scheduler_config(config, arm, scheduler_seed=scheduler_seed)
    learned = bool(arm_spec["learned_policy"])
    value_stats = ValueStats()
    if learned:
        scorer.clear_cache()
        policy: object | None = TermThresholdPolicyScorer(
            scorer, int(config["search"]["policy_term_threshold"])
        )
        value: object | None = LearnedValueEstimator(scorer, search_config, value_stats)
    else:
        policy = None
        value = None
    adjuster = None
    if arm_spec["execution_aware"]:
        adjuster = make_root_rollout_execution_utility_adjuster(
            n_inputs=int(coordinate.input_width),
            search_config=search_config,
            profile_spec=profile_spec,
            penalty_weights=weights,
            expected_profile_sha256=profile_spec.profile_sha256,
            execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
        )
    solver = NeuralMCTSSolver(
        config=search_config,
        simulations=int(config["search"]["simulations"]),
        seed=int(solver_seed),
        neural_scorer=policy,
        value_estimator=value,
        rollout_scorer=None,
        scheduler_config=scheduler,
        execution_utility_adjuster=adjuster,
    )
    started = time.perf_counter()
    plan = solver.solve(terms)
    solve_elapsed = time.perf_counter() - started
    root = solver.nodes.get(StateKey(terms, 0, 0))
    if root is None or len(root.actions) != root_action_count:
        raise RuntimeError("arm-dependent E5 root action count detected")
    if root_action_count == 0:
        if root.scheduler_decision is not None or root.admitted_indices is not None:
            raise RuntimeError("degenerate direct root unexpectedly invoked a scheduler")
        decision = None
        diagnostics = {
            "root_eligibility": root_eligibility,
            "status": "not_invoked_degenerate_direct_root",
            "node_id": NeuralMCTSSolver._state_id(StateKey(terms, 0, 0)),
            "candidate_count": 0,
            "utilities": [],
            "raw_utilities": [],
            "adjusted_utilities": [],
            "execution_feedback": {"enabled": False, "reason": "degenerate_direct_root"},
            "qaoa_attempted": False,
            "qaoa_succeeded": False,
            "qaoa_repaired": False,
            "qaoa_fallback": False,
            "not_invoked_reason": "root_action_count_zero",
        }
        pool_width = 0
        pool_actions = ()
        raw: list[float] = []
        adjusted: list[float] = []
        redundancy: list[list[float]] = []
    else:
        if root.scheduler_decision is None or root.admitted_indices is None:
            raise RuntimeError(
                f"E5 schedulable root scheduler missing for {coordinate.family} bit "
                f"{coordinate.output_bit}, seed {solver_seed}, arm {arm}"
            )
        decision = root.scheduler_decision
        diagnostics = dict(decision.diagnostics)
        diagnostics["root_eligibility"] = root_eligibility
        pool_width = int(diagnostics["candidate_count"])
        pool_actions = tuple(root.actions[:pool_width])
        raw = [
            float(item)
            for item in diagnostics.get("raw_utilities", diagnostics["utilities"])
        ]
        adjusted = [
            float(item)
            for item in diagnostics.get("adjusted_utilities", diagnostics["utilities"])
        ]
        redundancy = action_redundancy_matrix(
            pool_actions, alpha=float(config["search"]["redundancy_alpha"])
        )
    pool = {
        "schema_version": "xa.e5-external-family-candidate-pool.v1",
        "family": coordinate.family,
        "output_bit": coordinate.output_bit,
        "truth_table_sha256": coordinate.truth_table_sha256,
        "node_id": diagnostics["node_id"],
        "candidate_count": pool_width,
        "budget_requested": int(config["search"]["scheduler_budget"]),
        "budget_effective": min(int(config["search"]["scheduler_budget"]), pool_width),
        "action_signatures": [_action_signature(action) for action in pool_actions],
        "utilities": raw,
        "redundancy": [[float(item) for item in row] for row in redundancy],
        "redundancy_weight": float(config["search"]["redundancy_weight"]),
        "redundancy_alpha": float(config["search"]["redundancy_alpha"]),
    }
    plan_check = verify_plan_anf(plan)
    allocated_ancilla = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
    circuit = emit_plan_to_circuit(plan, coordinate.input_width, allocated_ancilla)
    target_qubits = int(config["native_profile"]["frozen_n_qubits"])
    if circuit.n_qubits > target_qubits:
        raise RuntimeError("E5 circuit exceeds the frozen 10q profile")
    if circuit.n_qubits < target_qubits:
        padded = QuantumCircuit(target_qubits)
        padded.gates = list(circuit.gates)
        circuit = padded
    circuit_check = verify_circuit_anf(circuit, coordinate.input_width, terms)
    oracle_ok = verify_oracle(circuit, coordinate.boolean_function)
    reversible_ok = _verify_reversible_oracle_all_targets(circuit, coordinate)
    logical_export = export_openqasm3(circuit)
    profile = profile_spec.build(target_qubits)
    compilation = compile_superconducting(circuit, profile)
    native_diagnostics = compilation.diagnostics
    native_qasm = native_to_openqasm3(compilation)
    native = {
        "profile_name": profile.name,
        "profile_sha256": frozen_profile_sha256,
        "topology_family": profile.topology_family,
        "n_qubits": profile.n_qubits,
        "coupling_edges": [list(edge) for edge in profile.coupling_edges],
        **asdict(native_diagnostics),
        "native_gate_set": ["rz", "sx", "x", "cx"],
        "native_gate_set_ok": all(
            gate.name in {"rz", "sx", "x", "cx"} for gate in compilation.native_gates
        ),
        "coupling_ok": all(
            tuple(sorted(gate.qubits)) in profile.coupling_edges
            for gate in compilation.native_gates
            if gate.name == "cx"
        ),
        "native_qasm3": native_qasm,
        "native_qasm3_sha256": sha256_bytes(native_qasm.encode("utf-8")),
        "hardware_execution": False,
        "noisy_simulation": False,
    }
    selected = (
        tuple(int(index) for index in decision.selected_indices)
        if decision is not None
        else ()
    )
    selected_set = set(selected)
    visits = [root.stats[index].visits for index in range(len(root.actions))]
    value_record = value_stats.as_dict()
    scheduler_record = {
        "method": scheduler.method,
        "qaoa_mode": scheduler.qaoa_mode if arm.endswith("qaoa_shot") else None,
        "candidate_count": pool_width,
        "budget_requested": int(config["search"]["scheduler_budget"]),
        "budget_effective": min(int(config["search"]["scheduler_budget"]), pool_width),
        "selected_indices": list(selected),
        "selected_action_visits": [visits[index] for index in selected],
        "selected_action_visits_total": sum(visits[index] for index in selected),
        "excluded_action_visits_total": sum(
            count for index, count in enumerate(visits) if index not in selected_set
        ),
        "status": diagnostics.get("status"),
        "objective": diagnostics.get("effective_objective", diagnostics.get("objective")),
        "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
        "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
        "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
        "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
        "diagnostics": diagnostics,
    }
    execution_status = _qaoa_execution_class(diagnostics, arm)
    if execution_status not in EXECUTION_STATUSES:
        raise RuntimeError(f"unregistered E5 execution status: {execution_status}")
    plan_trace = PlanTrace.from_plan(plan).to_dict()
    plan_trace_sha256 = _sha_payload(plan_trace)
    native_record_sha256 = _sha_payload(native)
    primary_endpoint = {
        "metric": "native.two_qubit_gate_count",
        "value": int(native["two_qubit_gate_count"]),
        "direction": "lower_is_better",
    }
    return {
        "schema_version": EVALUATION_ROW_SCHEMA,
        "record_type": "e5_external_family_trial",
        "run_id": run_id,
        "phase": "evaluate",
        "family": coordinate.family,
        "family_role": config["holdout_access"]["families"][coordinate.family]["role"],
        "operation": coordinate.operation,
        "output_bit": coordinate.output_bit,
        "input_width": coordinate.input_width,
        "output_width": coordinate.output_width,
        "bit_order": coordinate.bit_order,
        "source": coordinate.source,
        "provenance": coordinate.provenance,
        "benchmark_partition": coordinate.benchmark_partition,
        "training_access_allowed": coordinate.training_access_allowed,
        "family_exclusion_label": coordinate.family_exclusion_label,
        "vector_truth_table_sha256": coordinate.vector_truth_table_sha256,
        "truth_table_sha256": coordinate.truth_table_sha256,
        "truth_table_hex": canonical_hex(
            int(coordinate.boolean_function.truth_table),
            min_nibbles=1 << max(0, int(coordinate.input_width) - 2),
        ),
        "anf_term_count": len(terms),
        "root_action_count": root_action_count,
        "root_eligibility": root_eligibility,
        "root_structural_action_signatures": [
            _action_signature(action) for action in structural_root_actions
        ],
        "solver_seed": int(solver_seed),
        "scheduler_seed": scheduler_seed,
        "simulations": int(config["search"]["simulations"]),
        "arm": arm,
        "arm_spec": dict(arm_spec),
        "same_pool_group": arm_spec["same_pool_group"],
        "checkpoint_sha256": checkpoint_sha256 if learned else None,
        "learned_policy_enabled": learned,
        "learned_policy_active_at_root": learned
        and root_action_count > 0
        and int(getattr(policy, "learned_states", 0)) > 0,
        "learned_policy_stats": {
            "learned_states": int(getattr(policy, "learned_states", 0)),
            "gated_states": int(getattr(policy, "gated_states", 0)),
        },
        "learned_value_enabled": learned,
        "learned_value_active": learned and int(value_record.get("value_calls", 0)) > 0,
        "learned_value_stats": value_record,
        "candidate_pool": pool,
        "candidate_pool_sha256": _sha_payload(pool),
        "raw_scheduler_utilities": raw,
        "adjusted_scheduler_utilities": adjusted,
        "execution_feedback": diagnostics.get("execution_feedback", {}),
        "weights_sha256": weights.weights_sha256,
        "holdout_outcome_used_by_utility": False,
        "noisy_outcome_used_by_utility": False,
        "search_config": asdict(search_config),
        "scheduler_config": scheduler.to_dict(),
        "scheduler": scheduler_record,
        "execution_status": execution_status,
        "qaoa_execution": execution_status,
        "logical_resource_score": plan.score(PAPER_WEIGHTS),
        "logical_cost": asdict(plan.cost),
        "logical_gate_count": len(circuit.gates),
        "logical_n_qubits": circuit.n_qubits,
        "allocated_factor_ancilla": allocated_ancilla,
        "plan_anf_ok": plan_check.ok,
        "circuit_anf_ok": circuit_check.ok,
        "oracle_ok": oracle_ok,
        "reversible_oracle_all_targets_ok": reversible_ok,
        "plan_trace": plan_trace,
        "plan_trace_sha256": plan_trace_sha256,
        "logical_circuit_ir": {
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
        },
        "logical_qasm3": logical_export.qasm,
        "logical_qasm3_sha256": sha256_bytes(logical_export.qasm.encode("utf-8")),
        "native": native,
        "native_record_sha256": native_record_sha256,
        "profile_spec_sha256": profile_spec.profile_sha256,
        "profile_sha256": frozen_profile_sha256,
        "frozen_profile": dict(frozen_profile),
        "primary_endpoint": primary_endpoint,
        "primary_endpoint_sha256": _sha_payload(primary_endpoint),
        "search_nodes": len(solver.nodes),
        "root_visits": root.visits,
        "scheduler_wall_s": float(solver.scheduler_summary()["scheduler_wall_s"]),
        "solve_elapsed_s": solve_elapsed,
        "policy_cache_hits": scorer.cache_hits if learned else 0,
        "policy_cache_misses": scorer.cache_misses if learned else 0,
        "hardware_execution": False,
        "noisy_endpoint": None,
        "noisy_endpoints": [],
        "noisy_diagnostic_run": False,
    }


def _linear_quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("quantile requires at least one value")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    fraction = position - lower
    return float(
        sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction
    )


def cluster_paired_comparison(
    rows: Sequence[Mapping[str, Any]],
    *,
    family: str,
    historical_arm: str,
    execution_arm: str,
    config: Mapping[str, Any],
    direct_unrepaired_only: bool = False,
    schedulable_only: bool = False,
) -> dict[str, Any]:
    """Recompute one paired contrast with family-bit as the only iid unit."""

    if historical_arm == execution_arm:
        raise ValueError("paired comparison requires distinct arms")
    family_spec = config["holdout_access"]["families"][family]
    bits = [int(bit) for bit in family_spec["coordinates"]]
    seeds = [int(seed) for seed in config["evaluation"]["solver_seeds"]]
    index: dict[tuple[int, int, str], Mapping[str, Any]] = {}
    for row in rows:
        if row.get("family") != family or row.get("arm") not in {
            historical_arm,
            execution_arm,
        }:
            continue
        key = (int(row["output_bit"]), int(row["solver_seed"]), str(row["arm"]))
        if key in index:
            raise ValueError(f"duplicate paired row: {family}/{key}")
        index[key] = row
    expected = {
        (bit, seed, arm)
        for bit in bits
        for seed in seeds
        for arm in (historical_arm, execution_arm)
    }
    if set(index) != expected:
        raise ValueError(
            f"incomplete paired matrix for {family}: expected {len(expected)}, got {len(index)}"
        )

    eligible_bits: list[int] = []
    excluded_bits: list[int] = []
    excluded_reasons: list[dict[str, Any]] = []
    for bit in bits:
        bit_rows = [
            index[(bit, seed, arm)]
            for seed in seeds
            for arm in (historical_arm, execution_arm)
        ]
        schedulable = all(row.get("root_eligibility") == "schedulable" for row in bit_rows)
        direct = all(
            index[(bit, seed, historical_arm)].get("execution_status")
            == "direct_unrepaired"
            and index[(bit, seed, execution_arm)].get("execution_status")
            == "direct_unrepaired"
            for seed in seeds
        )
        reasons: list[str] = []
        if schedulable_only and not schedulable:
            reasons.append("excluded_from_schedulable_only_secondary")
        if direct_unrepaired_only and not direct:
            statuses = sorted({str(row.get("execution_status")) for row in bit_rows})
            reasons.append("not_both_arms_direct_unrepaired_all_seeds:" + ",".join(statuses))
        if reasons:
            excluded_bits.append(bit)
            excluded_reasons.append({"output_bit": bit, "reasons": reasons})
        else:
            eligible_bits.append(bit)
    cluster_records: list[dict[str, Any]] = []
    for bit in eligible_bits:
        seed_differences = [
            float(index[(bit, seed, execution_arm)]["primary_endpoint"]["value"])
            - float(index[(bit, seed, historical_arm)]["primary_endpoint"]["value"])
            for seed in seeds
        ]
        cluster_records.append(
            {
                "family": family,
                "output_bit": bit,
                "solver_seed_count": len(seeds),
                "seed_differences": seed_differences,
                "cluster_mean_difference": statistics.mean(seed_differences),
            }
        )
    effects = [float(record["cluster_mean_difference"]) for record in cluster_records]
    if not effects:
        return {
            "family": family,
            "metric": "native.two_qubit_gate_count",
            "comparison": f"{execution_arm}-minus-{historical_arm}",
            "estimand": (
                "schedulable_only_secondary"
                if schedulable_only
                else (
                    "direct_unrepaired_sensitivity"
                    if direct_unrepaired_only
                    else "intention_to_treat_all_assigned_trials"
                )
            ),
            "direct_unrepaired_only": direct_unrepaired_only,
            "schedulable_only": schedulable_only,
            "direct_filter_rule": "retain_family_bit_only_if_both_arms_direct_unrepaired_for_all_solver_seeds",
            "eligible_clusters": [],
            "excluded_clusters": excluded_bits,
            "excluded_cluster_reasons": excluded_reasons,
            "cluster_count": 0,
            "paired_seed_observation_count": 0,
            "cluster_effects": [],
            "mean_difference": None,
            "bootstrap_95_ci": None,
            "exact_two_sided_sign_flip_p": None,
            "inference_available": False,
            "wins_losses_ties": {"wins": 0, "losses": 0, "ties": 0},
            "nonzero_cluster_count": 0,
            "zero_cluster_count": 0,
            "effective_exact_sign_flip_permutations": 0,
        }
    observed = statistics.mean(effects)
    nonzero_effects = [effect for effect in effects if not math.isclose(effect, 0.0, abs_tol=1e-12)]
    sign_means = [
        statistics.mean(
            [sign * effect for sign, effect in zip(signs, nonzero_effects)]
            + [0.0] * (len(effects) - len(nonzero_effects))
        )
        for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero_effects))
    ]
    exact_p = sum(abs(item) >= abs(observed) - 1e-12 for item in sign_means) / len(
        sign_means
    )
    bootstrap_count = int(config["statistics"]["bootstrap_resamples"])
    seed = _derived_seed(
        "e5-cluster-bootstrap-v1",
        config["statistics"]["bootstrap_seed"],
        family,
        historical_arm,
        execution_arm,
        direct_unrepaired_only,
        schedulable_only,
    )
    rng = random.Random(seed)
    boot = sorted(
        statistics.mean(rng.choice(effects) for _ in effects)
        for _ in range(bootstrap_count)
    )
    return {
        "family": family,
        "metric": "native.two_qubit_gate_count",
        "direction": "negative_favors_second_execution_arm",
        "comparison": f"{execution_arm}-minus-{historical_arm}",
        "estimand": (
            "schedulable_only_secondary"
            if schedulable_only
            else (
                "direct_unrepaired_sensitivity"
                if direct_unrepaired_only
                else "intention_to_treat_all_assigned_trials"
            )
        ),
        "cluster_unit": ["family", "output_bit"],
        "seed_aggregation_within_cluster": "arithmetic_mean",
        "solver_seeds_are_repeated_measurements": True,
        "direct_unrepaired_only": direct_unrepaired_only,
        "schedulable_only": schedulable_only,
        "direct_filter_rule": "retain_family_bit_only_if_both_arms_direct_unrepaired_for_all_solver_seeds",
        "eligible_clusters": eligible_bits,
        "excluded_clusters": excluded_bits,
        "excluded_cluster_reasons": excluded_reasons,
        "cluster_count": len(effects),
        "paired_seed_observation_count": len(effects) * len(seeds),
        "cluster_effects": cluster_records,
        "mean_difference": observed,
        "bootstrap_seed": seed,
        "bootstrap_resamples": bootstrap_count,
        "bootstrap_95_ci": [
            _linear_quantile(boot, 0.025),
            _linear_quantile(boot, 0.975),
        ],
        "wins_losses_ties": {
            "wins": sum(effect < -1e-12 for effect in effects),
            "losses": sum(effect > 1e-12 for effect in effects),
            "ties": sum(math.isclose(effect, 0.0, abs_tol=1e-12) for effect in effects),
        },
        "nonzero_cluster_count": len(nonzero_effects),
        "zero_cluster_count": len(effects) - len(nonzero_effects),
        "exact_sign_flip_permutations": 1 << len(nonzero_effects),
        "effective_exact_sign_flip_permutations": 1 << len(nonzero_effects),
        "minimum_attainable_two_sided_sign_flip_p": (
            1.0 if not nonzero_effects else min(1.0, 2.0 / (1 << len(nonzero_effects)))
        ),
        "exact_two_sided_sign_flip_p": exact_p,
        "inference_available": True,
        "claim_rule": (
            "effect_estimate_only_no_binary_superiority_due_five_clusters"
            if family == "ASCON" and not direct_unrepaired_only
            else "secondary_or_sensitivity_effect_estimate_only"
        ),
    }


def _v4_pool_fairness(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        if row["arm"] in V4_FOUR_ARMS and row.get("root_eligibility") == "schedulable":
            groups.setdefault(
                (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])),
                [],
            ).append(row)
    records: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        arms = {str(row["arm"]) for row in group}
        pool_shas = {str(row["candidate_pool_sha256"]) for row in group}
        raw_shas = {_sha_payload(row["raw_scheduler_utilities"]) for row in group}
        budgets = {
            (
                int(row["simulations"]),
                int(row["search_config"]["candidate_top_k"]),
                int(row["scheduler"]["budget_requested"]),
                int(row["scheduler"]["budget_effective"]),
                int(row["scheduler"]["candidate_count"]),
            )
            for row in group
        }
        records.append(
            {
                "family": key[0],
                "output_bit": key[1],
                "solver_seed": key[2],
                "four_arms_present": arms == set(V4_FOUR_ARMS),
                "same_candidate_pool": len(pool_shas) == 1,
                "same_raw_utility": len(raw_shas) == 1,
                "same_simulations_k_budget_and_pool_width": len(budgets) == 1,
            }
        )
    all_group_keys = {
        (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"]))
        for row in rows
    }
    degenerate_group_keys = {
        (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"]))
        for row in rows
        if row.get("root_eligibility") == "degenerate_direct_root"
    }
    expected_groups = len(all_group_keys - degenerate_group_keys)
    family_schedulable_counts = {
        family: sum(record["family"] == family for record in records)
        for family in ("ASCON", "PRESENT")
    }
    return {
        "same_pool_group": "v4_four_arm",
        "eligibility_scope": "schedulable_root_action_count_positive_only",
        "group_count": len(records),
        "expected_group_count": expected_groups,
        "degenerate_group_count": len(degenerate_group_keys),
        "degenerate_groups_excluded_from_same_pool_claim": [
            {"family": family, "output_bit": bit, "solver_seed": seed}
            for family, bit, seed in sorted(degenerate_group_keys)
        ],
        "family_schedulable_group_counts": family_schedulable_counts,
        "each_family_has_schedulable_activity": all(
            count > 0 for count in family_schedulable_counts.values()
        ),
        "groups": records,
        "all": len(records) == expected_groups
        and all(count > 0 for count in family_schedulable_counts.values())
        and all(
            record["four_arms_present"]
            and record["same_candidate_pool"]
            and record["same_raw_utility"]
            and record["same_simulations_k_budget_and_pool_width"]
            for record in records
        ),
        "heuristic_reference_excluded_from_same_pool_claim": True,
    }


def _arm_summaries(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        qaoa = [row for row in selected if arm.endswith("qaoa_shot")]
        summaries[arm] = {
            "trial_count": len(selected),
            "execution_status_counts": {
                status: sum(row["execution_status"] == status for row in selected)
                for status in EXECUTION_STATUSES
            },
            "native_two_qubit_mean": statistics.mean(
                float(row["native"]["two_qubit_gate_count"]) for row in selected
            ),
            "native_gate_count_mean": statistics.mean(
                float(row["native"]["native_gate_count"]) for row in selected
            ),
            "logical_resource_score_mean": statistics.mean(
                float(row["logical_resource_score"]) for row in selected
            ),
            "qaoa_direct_unrepaired": sum(
                row["qaoa_execution"] == "direct_unrepaired" for row in qaoa
            ),
            "qaoa_direct_repaired": sum(
                row["qaoa_execution"] == "direct_repaired" for row in qaoa
            ),
            "qaoa_fallback": sum(row["qaoa_execution"] == "fallback" for row in qaoa),
            "not_invoked_degenerate": sum(
                row["execution_status"] == "not_invoked_degenerate" for row in selected
            ),
            "not_invoked_small_pool": sum(
                row["execution_status"] == "not_invoked_small_pool" for row in selected
            ),
        }
    return summaries


def _eligibility_and_degenerate_identity(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(
            (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])),
            [],
        ).append(row)
    records: list[dict[str, Any]] = []
    for (family, bit, seed), group in sorted(groups.items()):
        counts = {int(row["root_action_count"]) for row in group}
        structural_action_shas = {
            _sha_payload(row["root_structural_action_signatures"]) for row in group
        }
        eligibilities = {str(row["root_eligibility"]) for row in group}
        arm_complete = {str(row["arm"]) for row in group} == set(ARMS)
        count = next(iter(counts)) if len(counts) == 1 else -1
        expected_eligibility = (
            "schedulable" if count > 0 else "degenerate_direct_root"
        )
        degenerate = expected_eligibility == "degenerate_direct_root"
        identity_fields = {
            "plan_trace_sha256": {str(row["plan_trace_sha256"]) for row in group},
            "logical_qasm3_sha256": {
                str(row["logical_qasm3_sha256"]) for row in group
            },
            "native_record_sha256": {
                str(row["native_record_sha256"]) for row in group
            },
            "native_qasm3_sha256": {
                str(row["native"]["native_qasm3_sha256"]) for row in group
            },
            "primary_endpoint_sha256": {
                str(row["primary_endpoint_sha256"]) for row in group
            },
        }
        degenerate_identity = (
            all(len(values) == 1 for values in identity_fields.values())
            and all(
                row["execution_status"] == "not_invoked_degenerate"
                and row["scheduler"]["candidate_count"] == 0
                and row["scheduler"]["selected_indices"] == []
                and row["plan_anf_ok"]
                and row["circuit_anf_ok"]
                and row["oracle_ok"]
                and row["reversible_oracle_all_targets_ok"]
                and row["native"]["native_gate_set_ok"]
                and row["native"]["coupling_ok"]
                for row in group
            )
        ) if degenerate else True
        degenerate_itt_zero = (
            len({float(row["primary_endpoint"]["value"]) for row in group}) == 1
            if degenerate
            else True
        )
        records.append(
            {
                "family": family,
                "output_bit": bit,
                "solver_seed": seed,
                "five_arms_present": arm_complete,
                "arm_independent_root_action_count": len(counts) == 1,
                "arm_independent_root_structural_actions": len(structural_action_shas)
                == 1,
                "root_action_count": count,
                "root_eligibility": expected_eligibility,
                "eligibility_consistent": eligibilities == {expected_eligibility},
                "degenerate_five_arm_plan_qasm_native_endpoint_identical": degenerate_identity,
                "degenerate_itt_zero_difference": degenerate_itt_zero,
            }
        )
    status_counts = {
        status: sum(row.get("execution_status") == status for row in rows)
        for status in EXECUTION_STATUSES
    }
    return {
        "group_count": len(records),
        "expected_group_count": 18,
        "groups": records,
        "degenerate_group_count": sum(
            record["root_eligibility"] == "degenerate_direct_root" for record in records
        ),
        "schedulable_group_count": sum(
            record["root_eligibility"] == "schedulable" for record in records
        ),
        "status_counts": status_counts,
        "status_total": sum(status_counts.values()),
        "status_taxonomy_closed": sum(status_counts.values()) == len(rows),
        "all": len(records) == 18
        and all(
            record["five_arms_present"]
            and record["arm_independent_root_action_count"]
            and record["arm_independent_root_structural_actions"]
            and record["eligibility_consistent"]
            and record["degenerate_five_arm_plan_qasm_native_endpoint_identical"]
            and record["degenerate_itt_zero_difference"]
            for record in records
        ),
    }


def run_evaluate(
    *,
    config_path: Path,
    config: Mapping[str, Any],
    preflight_bundle: Path,
    seal_bundle: Path,
    out_dir: Path,
    run_id: str,
) -> Path:
    """Evaluate the frozen model exactly once after every release gate closes."""

    global _FAILURE_CONTEXT
    _FAILURE_CONTEXT = {
        "rows": [],
        "events": [],
        "holdout_released": False,
        "release_record": None,
    }
    started = time.perf_counter()
    created_at = utc_now()
    _assert_crypto_module_absent("evaluate entry")
    compute_runtime = establish_compute_contract(
        config, context="runner-evaluate-before-checkpoint-inference"
    )
    _, static_lock_sha = load_static_protocol_lock(config)
    model_gate = verify_formal_v4_gate(config)
    source = source_record(PROJECT_ROOT)
    preflight, weights, preflight_sha = _load_verified_preflight(
        preflight_bundle.resolve(),
        config=config,
        static_lock_sha256=static_lock_sha,
        current_source_tree_sha256=source["source_tree_sha256"],
    )
    evaluation_lock, seal_summary_sha = _load_verified_seal(
        seal_bundle.resolve(),
        config=config,
        static_lock_sha256=static_lock_sha,
        preflight_bundle=preflight_bundle.resolve(),
        preflight_summary=preflight,
        preflight_summary_sha256=preflight_sha,
    )
    if evaluation_lock["source_tree_sha256"] != source["source_tree_sha256"]:
        raise ValueError("source tree changed after E5 seal")
    profile_spec = _profile_spec(config)
    frozen_profile, profile_sha = _frozen_concrete_profile(config, profile_spec)
    if (
        weights.profile_sha256 != profile_spec.profile_sha256
        or preflight["profile_sha256"] != profile_sha
    ):
        raise ValueError("evaluation profile differs from preflight")
    checkpoint = _checkpoint_path(config)
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    if any(parameter.device.type != "cpu" for parameter in scorer.model.parameters()):
        raise RuntimeError("E5 evaluation scorer violated the CPU compute contract")
    # This call is the first and only table-release point.  No data-dependent
    # branch above can inspect ASCON/PRESENT values, plans, or native outcomes.
    families, release_record = _release_holdout_families_after_all_gates(config)
    _FAILURE_CONTEXT["holdout_released"] = True
    _FAILURE_CONTEXT["release_record"] = copy.deepcopy(release_record)

    rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = [
        {
            "event": "evaluation_released",
            "run_id": run_id,
            "created_at_utc": created_at,
            "evaluation_lock_sha256": _sha_payload(evaluation_lock),
            "family_order": list(families),
        }
    ]
    _FAILURE_CONTEXT["events"] = events
    for family in config["evaluation"]["family_order"]:
        for coordinate in families[family]:
            for solver_seed in config["evaluation"]["solver_seeds"]:
                for arm_spec in config["evaluation"]["arms"]:
                    row = _evaluation_trial(
                        coordinate=coordinate,
                        arm_spec=arm_spec,
                        solver_seed=int(solver_seed),
                        config=config,
                        scorer=scorer,
                        checkpoint_sha256=config["foundation_v4"]["checkpoint_sha256"],
                        weights=weights,
                        profile_spec=profile_spec,
                        frozen_profile=frozen_profile,
                        frozen_profile_sha256=profile_sha,
                        run_id=run_id,
                    )
                    rows.append(row)
                    _FAILURE_CONTEXT["rows"].append(row)
                    events.append(
                        {
                            "event": "evaluation_trial_completed",
                            "family": family,
                            "output_bit": coordinate.output_bit,
                            "solver_seed": solver_seed,
                            "arm": arm_spec["name"],
                            "native_two_qubit": row["native"]["two_qubit_gate_count"],
                        }
                    )
    rows.sort(
        key=lambda row: (
            config["evaluation"]["family_order"].index(row["family"]),
            int(row["output_bit"]),
            int(row["solver_seed"]),
            ARMS.index(row["arm"]),
        )
    )
    expected_matrix = {
        (family, bit, seed, arm)
        for family in config["evaluation"]["family_order"]
        for bit in config["holdout_access"]["families"][family]["coordinates"]
        for seed in config["evaluation"]["solver_seeds"]
        for arm in ARMS
    }
    actual_matrix = {
        (row["family"], row["output_bit"], row["solver_seed"], row["arm"])
        for row in rows
    }
    fairness = _v4_pool_fairness(rows)
    primary = cluster_paired_comparison(
        rows,
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
    )
    direct = cluster_paired_comparison(
        rows,
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
        direct_unrepaired_only=True,
    )
    secondary = {
        "present_qaoa_execution_aware": cluster_paired_comparison(
            rows,
            family="PRESENT",
            historical_arm="v4_historical_qaoa_shot",
            execution_arm="v4_execution_aware_qaoa_shot",
            config=config,
            schedulable_only=True,
        ),
        "ascon_greedy_execution_aware": cluster_paired_comparison(
            rows,
            family="ASCON",
            historical_arm="v4_historical_greedy",
            execution_arm="v4_execution_aware_greedy",
            config=config,
            schedulable_only=True,
        ),
        "ascon_v4_model_reference": cluster_paired_comparison(
            rows,
            family="ASCON",
            historical_arm="heuristic_historical_greedy",
            execution_arm="v4_historical_greedy",
            config=config,
            schedulable_only=True,
        ),
        "present_v4_model_reference": cluster_paired_comparison(
            rows,
            family="PRESENT",
            historical_arm="heuristic_historical_greedy",
            execution_arm="v4_historical_greedy",
            config=config,
            schedulable_only=True,
        ),
    }
    eligibility_identity = _eligibility_and_degenerate_identity(rows)
    v4_rows = [row for row in rows if row["arm"] in V4_FOUR_ARMS]
    schedulable_v4_rows = [
        row for row in v4_rows if row["root_eligibility"] == "schedulable"
    ]
    heuristic_rows = [row for row in rows if row["arm"] == ARMS[0]]
    qaoa_rows = [row for row in rows if row["arm"].endswith("qaoa_shot")]
    summary = {
        "schema_version": EVALUATION_SUMMARY_SCHEMA,
        "run_id": run_id,
        "phase": "evaluate",
        "evidence_ok": True,
        "experiment_completed": True,
        "amendment_classification": config["amendment"]["classification"],
        "amendment_sha256": _sha_payload(config["amendment"]),
        "experiment_role": "external_family_holdout_evaluation",
        "dataset_role": config["dataset_role"],
        "config_sha256": _sha_payload(config),
        "compute_contract": copy.deepcopy(dict(config["compute_contract"])),
        "compute_contract_sha256": compute_contract_sha256(config),
        "compute_runtime": compute_runtime,
        "trial_count": len(rows),
        "expected_trial_count": 90,
        "complete_matrix": actual_matrix == expected_matrix and len(rows) == 90,
        "family_coordinate_counts": {family: len(families[family]) for family in families},
        "solver_seed_count": len(config["evaluation"]["solver_seeds"]),
        "arm_summaries": _arm_summaries(rows),
        "v4_four_arm_fairness": fairness,
        "root_eligibility_and_degenerate_identity": eligibility_identity,
        "fairness": {"v4_four_arm_same_pool": fairness["all"]},
        "learned_mechanism": {
            "v4_policy_active_all": all(
                row["learned_policy_active_at_root"] and row["policy_cache_misses"] > 0
                for row in schedulable_v4_rows
            ),
            "v4_value_active_all": all(
                row["learned_value_enabled"]
                and row["learned_value_stats"]["value_calls"] > 0
                for row in schedulable_v4_rows
            ),
            "scope": "schedulable_v4_rows_only",
            "schedulable_v4_row_count": len(schedulable_v4_rows),
            "degenerate_v4_rows_exempt_from_inference_activity": len(v4_rows)
            - len(schedulable_v4_rows),
            "heuristic_policy_value_disabled_all": all(
                not row["learned_policy_active_at_root"]
                and not row["learned_value_enabled"]
                for row in heuristic_rows
            ),
        },
        "model_activation": {
            "all_v4_policy_active": all(
                row["learned_policy_active_at_root"] and row["policy_cache_misses"] > 0
                for row in schedulable_v4_rows
            ),
            "all_v4_value_active": all(
                row["learned_value_enabled"]
                and row["learned_value_stats"]["value_calls"] > 0
                for row in schedulable_v4_rows
            ),
            "activity_scope": "schedulable_v4_rows_only",
        },
        "primary_endpoint": config["primary_endpoint"],
        "primary_comparison": primary,
        "primary": primary,
        "direct_unrepaired_sensitivity": direct,
        "direct_sensitivity": direct,
        "secondary_comparisons": secondary,
        "secondary": secondary,
        "performance_claim_supported": False,
        "claim_rule_applied": "effect_estimate_only_no_binary_superiority_due_five_clusters",
        "qaoa_accounting": {
            "rows": len(qaoa_rows),
            "direct_unrepaired": sum(
                row["qaoa_execution"] == "direct_unrepaired" for row in qaoa_rows
            ),
            "direct_repaired": sum(
                row["qaoa_execution"] == "direct_repaired" for row in qaoa_rows
            ),
            "fallback": sum(row["qaoa_execution"] == "fallback" for row in qaoa_rows),
            "not_invoked_degenerate": sum(
                row["execution_status"] == "not_invoked_degenerate" for row in qaoa_rows
            ),
            "not_invoked_small_pool": sum(
                row["execution_status"] == "not_invoked_small_pool" for row in qaoa_rows
            ),
            "invalid": sum(row["execution_status"] == "invalid" for row in qaoa_rows),
            "status_taxonomy": list(EXECUTION_STATUSES),
            "status_counts_all_arms": eligibility_identity["status_counts"],
            "status_total_all_arms": eligibility_identity["status_total"],
            "status_taxonomy_closed": eligibility_identity["status_taxonomy_closed"],
        },
        "logical_semantics_all": all(
            row["plan_anf_ok"]
            and row["circuit_anf_ok"]
            and row["oracle_ok"]
            and row["reversible_oracle_all_targets_ok"]
            for row in rows
        ),
        "native_contract_all": all(
            row["native"]["native_gate_set_ok"]
            and row["native"]["coupling_ok"]
            and row["native"]["n_qubits"] == 10
            and row["profile_sha256"] == profile_sha
            for row in rows
        ),
        "holdout_release": release_record,
        "access_contract": {
            "family_exclusion_label": config["holdout_access"]["family_exclusion_label"],
            "release_order": list(families),
            "training_access_allowed": False,
            "first_load_after_all_gates": True,
        },
        "bindings": {
            "config_sha256": _sha_payload(config),
            "static_lock_sha256": static_lock_sha,
            "source_tree_sha256": source["source_tree_sha256"],
            "checkpoint_sha256": config["foundation_v4"]["checkpoint_sha256"],
            "model_card_sha256": config["foundation_v4"]["model_card_sha256"],
            "preflight_run_id": preflight["run_id"],
            "preflight_summary_sha256": preflight_sha,
            "seal_bundle_hint": seal_bundle.name,
            "seal_summary_sha256": seal_summary_sha,
            "evaluation_lock_sha256": _sha_payload(evaluation_lock),
            "seal": {
                "bundle_hint": seal_bundle.name,
                "summary_sha256": seal_summary_sha,
                "evaluation_lock_sha256": _sha_payload(evaluation_lock),
                "static_lock_sha256": static_lock_sha,
            },
            "weights_sha256": weights.weights_sha256,
            "profile_spec_sha256": profile_spec.profile_sha256,
            "profile_sha256": profile_sha,
            "compute_contract_sha256": compute_contract_sha256(config),
            "refit_after_holdout_release": False,
            "model_selection_after_holdout_release": False,
        },
        "frozen_profile": frozen_profile,
        "profile_spec_sha256": profile_spec.profile_sha256,
        "profile_sha256": profile_sha,
        "noisy_diagnostic": {
            "enabled": False,
            "endpoint_count": 0,
            "shots": 0,
            "used_by_primary_summary": False,
        },
        "scope": {
            "external_family_holdout": True,
            "researcher_blinded": False,
            "synthetic_profile": True,
            "hardware_execution": False,
            "noisy_performance_evidence": False,
            "quantum_speedup_claimed": False,
            "quantum_advantage_claimed": False,
            "noisy_diagnostic_run": False,
            "binary_superiority_claimed": False,
            "primary_iid_cluster_count": 5,
            "primary_nonzero_cluster_count": primary["nonzero_cluster_count"],
            "primary_zero_cluster_count": primary["zero_cluster_count"],
            "minimum_attainable_two_sided_exact_p": primary[
                "minimum_attainable_two_sided_sign_flip_p"
            ],
        },
        "claim_boundary": config["claim_boundary"],
    }
    checks = {
        "complete_ninety_trial_matrix": summary["complete_matrix"],
        "ascon_primary_present_secondary_complete": release_record["families"]["ASCON"][
            "coordinate_count"
        ]
        == 5
        and release_record["families"]["PRESENT"]["coordinate_count"] == 4,
        "v4_four_arm_pool_raw_budget_fairness": fairness["all"],
        "arm_independent_eligibility_and_degenerate_identity": eligibility_identity[
            "all"
        ],
        "each_family_has_schedulable_activity": fairness[
            "each_family_has_schedulable_activity"
        ],
        "learned_policy_and_value_active": all(
            summary["learned_mechanism"][key]
            for key in (
                "v4_policy_active_all",
                "v4_value_active_all",
                "heuristic_policy_value_disabled_all",
            )
        ),
        "historical_adjusted_equals_raw": all(
            row["raw_scheduler_utilities"] == row["adjusted_scheduler_utilities"]
            for row in rows
            if not row["arm_spec"]["execution_aware"]
        ),
        "qaoa_itt_accounted": summary["qaoa_accounting"]["invalid"] == 0
        and summary["qaoa_accounting"]["status_taxonomy_closed"],
        "logical_and_native_contract": summary["logical_semantics_all"]
        and summary["native_contract_all"],
        "cluster_statistics_predeclared": primary["cluster_count"] == 5
        and primary["paired_seed_observation_count"] == 10,
        "direct_filter_is_complete_pair_cluster_filter": direct["direct_filter_rule"]
        == "retain_family_bit_only_if_both_arms_direct_unrepaired_for_all_solver_seeds"
        and len(direct["excluded_cluster_reasons"])
        == len(direct["excluded_clusters"]),
        "no_post_release_refit_or_noisy_endpoint": not summary["bindings"][
            "refit_after_holdout_release"
        ]
        and not summary["bindings"]["model_selection_after_holdout_release"]
        and summary["noisy_diagnostic"]["endpoint_count"] == 0,
        "claim_boundary_no_superiority_hardware_or_advantage": summary[
            "performance_claim_supported"
        ]
        is False
        and summary["scope"]["hardware_execution"] is False
        and summary["scope"]["quantum_advantage_claimed"] is False,
        "compute_contract_established_before_inference": compute_runtime_matches(
            compute_runtime, config
        )
        and model_gate["compute_contract_sha256"] == compute_contract_sha256(config)
        and evaluation_lock["compute_contract_sha256"]
        == compute_contract_sha256(config),
    }
    declared = _declared_verifier(run_id, checks)
    summary["evidence_ok"] = True
    summary["experiment_completed"] = bool(declared["ok"])
    elapsed = time.perf_counter() - started
    events.append(
        {
            "event": "evaluation_completed",
            "run_id": run_id,
            "elapsed_s": elapsed,
            "trial_count": len(rows),
            "declared_verifier_ok": declared["ok"],
        }
    )
    run = _run_record(
        run_id=run_id,
        phase="evaluate",
        status="complete" if declared["ok"] else "failed",
        created_at=created_at,
        config_path=config_path,
        config=config,
        source=source,
        counts={
            "rows": len(rows),
            "holdout_coordinates": sum(len(items) for items in families.values()),
            "noisy_shots": 0,
        },
        model=model_record(checkpoint, PROJECT_ROOT),
        binding=summary["bindings"],
        compute_runtime=compute_runtime,
        elapsed_s=elapsed,
    )
    run_dir = out_dir.resolve() / run_id
    _write_and_independently_verify(
        run_dir=run_dir,
        run_record=run,
        rows=rows,
        summary=summary,
        declared=declared,
        events=events,
    )
    return run_dir


def _args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("preflight", "seal", "evaluate"),
        required=True,
        help="There is deliberately no combined/all phase.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT
        / "configs"
        / "xa202609"
        / "e5_external_crypto_holdout_v1.json",
    )
    parser.add_argument("--preflight-bundle", type=Path)
    parser.add_argument("--seal-bundle", type=Path)
    parser.add_argument(
        "--out-dir", type=Path, default=PROJECT_ROOT / "results" / "xa202609"
    )
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _args(argv)
    config_path = args.config.expanduser().resolve()
    created = utc_now()
    run_id = args.run_id or (
        f"{created[:10].replace('-', '')}-{created[11:19].replace(':', '')}"
        f"-e5-{args.phase}-external-crypto-v1.1"
    )
    out_dir = args.out_dir.expanduser().resolve()
    config: dict[str, Any] | None = None
    reservation: Path | None = None
    global _FAILURE_CONTEXT
    _FAILURE_CONTEXT = {
        "rows": [],
        "events": [
            {
                "event": "run_requested",
                "run_id": run_id,
                "phase": args.phase,
                "created_at_utc": created,
            }
        ],
        "holdout_released": False,
        "release_record": None,
    }
    try:
        reservation = _reserve_run_id(out_dir, run_id)
        config = load_config(config_path)
        _assert_crypto_module_absent("CLI config validation")
        if args.phase == "preflight":
            if args.preflight_bundle is not None or args.seal_bundle is not None:
                raise ValueError("preflight cannot receive preflight/seal bundle inputs")
            run_preflight(
                config_path=config_path,
                config=config,
                out_dir=out_dir,
                run_id=run_id,
            )
        elif args.phase == "seal":
            if args.preflight_bundle is None or args.seal_bundle is not None:
                raise ValueError("seal requires --preflight-bundle and forbids --seal-bundle")
            run_seal(
                config_path=config_path,
                config=config,
                preflight_bundle=args.preflight_bundle.expanduser().resolve(),
                out_dir=out_dir,
                run_id=run_id,
            )
        else:
            if args.preflight_bundle is None or args.seal_bundle is None:
                raise ValueError("evaluate requires --preflight-bundle and --seal-bundle")
            run_evaluate(
                config_path=config_path,
                config=config,
                preflight_bundle=args.preflight_bundle.expanduser().resolve(),
                seal_bundle=args.seal_bundle.expanduser().resolve(),
                out_dir=out_dir,
                run_id=run_id,
            )
    except Exception as exc:
        captured_traceback = traceback.format_exc()
        if reservation is not None:
            try:
                reservation.unlink()
            except FileNotFoundError:
                pass
            reservation = None
        try:
            failure_dir = _write_failed_attempt_bundle(
                out_dir=out_dir,
                run_id=run_id,
                phase=args.phase,
                config_path=config_path,
                config=config,
                exception=exc,
                traceback_text=captured_traceback,
                terminal_capture_available=False,
                requested_command={
                    "entrypoint": "scripts/run_e5_external_crypto_holdout.py",
                    "phase": args.phase,
                    "config": str(config_path),
                    "preflight_bundle": (
                        None
                        if args.preflight_bundle is None
                        else str(args.preflight_bundle.expanduser().resolve())
                    ),
                    "seal_bundle": (
                        None
                        if args.seal_bundle is None
                        else str(args.seal_bundle.expanduser().resolve())
                    ),
                    "out_dir": str(out_dir),
                    "run_id": run_id,
                },
            )
            print(f"failed_attempt_bundle={failure_dir}", file=sys.stderr)
            print("evidence_ok=True", file=sys.stderr)
            print("experiment_completed=False", file=sys.stderr)
        except Exception as evidence_exc:
            print(
                f"failed to persist E5 failed-attempt evidence: {evidence_exc}",
                file=sys.stderr,
            )
        raise
    finally:
        if reservation is not None:
            try:
                reservation.unlink()
            except FileNotFoundError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
