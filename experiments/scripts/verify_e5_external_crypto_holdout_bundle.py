#!/usr/bin/env python3
"""Independently verify the sealed E5 external-family hold-out experiment.

The verifier deliberately has no top-level import of ``crypto_oracles``.  A
preflight or seal bundle can therefore be verified without loading ASCON or
PRESENT.  The labelled hold-out loader is imported only after an evaluate
bundle has passed its v4, preflight, protocol-lock, and evaluation-lock gates.

This is a pre-registered contract for three separately executed phases:

``preflight``
    Verify the provenance-closed foundation-v4 model and compile-only n=6/7
    calibration used to freeze non-negative execution penalty weights.
``seal``
    Verify that the protocol and evaluation locks bind the config, source,
    v4 model, preflight evidence, fixed-10q profile, matrix, and statistics
    before any external-family table is accessed.
``evaluate``
    Open the labelled ASCON/PRESENT loader, reconstruct the complete five-arm
    matrix, plans, scheduler decisions, native compilations, and family-bit
    cluster statistics.

The module never trusts ``summary.json`` as evidence: every reported endpoint
is recomputed from ``raw.jsonl`` and immutable inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import random
import statistics
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch


def _discover_project_root() -> Path:
    override = os.environ.get("XA_E5_PROJECT_ROOT") or os.environ.get("XA_PROJECT_ROOT")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.extend(
        (
            Path(__file__).resolve().parent.parent,
            Path.cwd(),
            Path.cwd() / "experiments",
        )
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "src").is_dir() and (resolved / "scripts").is_dir():
            return resolved
    # The file is intended to live under experiments/scripts.  Returning this
    # path gives a useful import failure if a standalone copy is executed elsewhere
    # without XA_PROJECT_ROOT, while py_compile remains available.
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _discover_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# No src.benchmarks.crypto_oracles import is allowed here.  See
# _load_and_verify_holdouts(), which is reached only after all sealed gates.
from src.anf_utils import anf_monomials  # noqa: E402
from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file  # noqa: E402
from src.contracts.search import PlanTrace  # noqa: E402
from src.factor_plan import (  # noqa: E402
    FactorAction,
    Plan,
    SearchConfig,
    candidate_actions,
    direct_plan,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import FoundationScorer, TermThresholdPolicyScorer  # noqa: E402
from src.hardware.qasm import circuit_to_logical_ir, export_openqasm3  # noqa: E402
from src.hardware.superconducting import (  # noqa: E402
    NoiseParameters,
    compile_superconducting,
    native_to_openqasm3,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceCost, ResourceWeights  # noqa: E402
from src.search.execution_aware_utility import (  # noqa: E402
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    complete_root_action_rollout,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.mcts_scheduler import DiversitySchedulerConfig, action_redundancy_matrix  # noqa: E402
from src.search.value_net import LearnedValueEstimator, ValueStats  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction, Gate, QuantumCircuit  # noqa: E402
from scripts.verify_foundation_v4_bundle import verify_foundation_v4_bundle  # noqa: E402


TRACK = "xa202609/e5-external-crypto-holdout-v1.1"
RUNNER_SCHEMA = "xa.e5-external-crypto-holdout-runner.v1.1"
RUN_SCHEMA = "xa.e5-external-crypto-holdout-run.v1.1"
CONFIG_SCHEMA = "xa.e5-external-crypto-holdout-config.v1.1"
PROTOCOL_LOCK_SCHEMA = "xa.e5-static-protocol-lock.v1.1"
EVALUATION_LOCK_SCHEMA = "xa.e5-evaluation-lock.v1.1"
PREFLIGHT_ROW_SCHEMA = "xa.e5-preflight-calibration-row.v1.1"
PREFLIGHT_SUMMARY_SCHEMA = "xa.e5-preflight-summary.v1.1"
SEAL_SUMMARY_SCHEMA = "xa.e5-seal-summary.v1.1"
EVALUATION_ROW_SCHEMA = "xa.e5-external-family-trial.v1.1"
EVALUATION_SUMMARY_SCHEMA = "xa.e5-external-family-summary.v1.1"
FAILED_ATTEMPT_SUMMARY_SCHEMA = "xa.e5-failed-attempt-summary.v1.1"
FAILED_ATTEMPT_VERIFIER_SCHEMA = "xa.e5-failed-attempt-verifier.v1.1"
DECLARED_VERIFIER_SCHEMA = "xa.e5-declared-verifier.v1.1"
COMPUTE_RUNTIME_SCHEMA = "xa.e5-compute-runtime.v1"
HOLDOUT_LABEL = (
    "external_crypto_family_holdout_excluded_from_training_calibration_"
    "and_model_selection"
)

COMMON_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")
PHASE_ROLES = {phase: COMMON_ROLES for phase in ("preflight", "seal", "evaluate")}
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
FIVE_ARMS = (
    "heuristic_historical_greedy",
    "v4_historical_greedy",
    "v4_execution_aware_greedy",
    "v4_historical_qaoa_shot",
    "v4_execution_aware_qaoa_shot",
)
V4_ARMS = FIVE_ARMS[1:]
EXECUTION_AWARE_ARMS = (
    "v4_execution_aware_greedy",
    "v4_execution_aware_qaoa_shot",
)
QAOA_ARMS = (
    "v4_historical_qaoa_shot",
    "v4_execution_aware_qaoa_shot",
)
ROOT_ELIGIBILITIES = ("schedulable", "degenerate_direct_root")
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
PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
EXPECTED_PARAMETER_COUNT = 60_450

PARENT_V1_STATIC_CANONICAL_SHA256 = (
    "029eb6d3ceb5afdf12fd1a2e406d96919a1ae7fa8f0359d510060d8e44cbde19"
)
PARENT_V1_EVALUATION_LOCK_SHA256 = (
    "dd05ab6a3370dd64252e36d429b4a12507d4d99309c176f1dce443b988adceba"
)
INCIDENT_README_SHA256 = (
    "f9df9fd23b223abcc84c44a8042a74c394bd3e5fc10a6d39d4952d308dec4ec6"
)
INCIDENT_ATTEMPT_SHA256 = (
    "4d528325dfed821af01fe98a422636347b5d90a35d8d5ff533cac64babde5423"
)
INCIDENT_CHECKSUMS_SHA256 = (
    "04f043ecf8b48338f15dbf1c7591d77cf24e29335aba9d657fa22e739f26c0bd"
)

HOLDOUT_SPECS: dict[str, dict[str, Any]] = {
    "ASCON": {
        "input_width": 5,
        "output_width": 5,
        "vector_sha256": "2f5f6885b68f1f6fafed2be6ab614346c48a8528b51f7b4bdf4a0c1b609df97d",
        "coordinate_sha256": (
            "2629f646e4e48c89d27a2fa15d806db1bb59721ec004c19415ae59ac2e72b48f",
            "80713771a1b2e8920d65ad892d27c8e2e8aba5874d587d4b24cf6cf074784ce7",
            "8a20f3428448f5e2bd8da3e9559cb7a3ae091759f4516e80cc65b8f616d6112d",
            "e511dae0b4fd7953dd2e564003d3ef3b86f560ece76e073391bc525e9a45a97d",
            "cac32e76240366ea1129102f26003cec2121742a1742f912da081106857743be",
        ),
        "role": "primary",
    },
    "PRESENT": {
        "input_width": 4,
        "output_width": 4,
        "vector_sha256": "8e63f8c394a1ee38340d3be6e9a33b7b8c86d752498720dc80c223b02562e959",
        "coordinate_sha256": (
            "4e970e8b7f2fb52a79c55db9c9dfaa44658eb64fd37e5ed9d3440a0905803e71",
            "b3311960f4cf52c6db4d5cbb9cf0d47915e3666175b91f3eb4e08bad9932865a",
            "651dfc9a16350c391f9b9f1e02afd433f951246a6fce4691301e3c463266bf71",
            "3def4ec7c4026dc026162cdf2279a16a8e9e9f5efdde0521ebbfd91f3d5fec83",
        ),
        "role": "secondary",
    },
}
EXPECTED_SOURCE_PATHS = {
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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} line {number} must contain an object")
        rows.append(value)
    return rows


def _effective_config(run: Mapping[str, Any]) -> dict[str, Any]:
    record = run.get("config", {})
    embedded = record.get("effective_config") if isinstance(record, Mapping) else None
    if isinstance(embedded, dict):
        return embedded
    hint = record.get("path_hint") if isinstance(record, Mapping) else None
    if not isinstance(hint, str) or Path(hint).name != hint:
        raise ValueError("run config path_hint must be one filename")
    candidates = (
        PROJECT_ROOT / "configs" / "xa202609" / hint,
        PROJECT_ROOT / "configs" / hint,
    )
    for path in candidates:
        if not path.is_file():
            continue
        config = _read_json(path)
        if (
            sha256_file(path) == record.get("file_sha256")
            and sha256_bytes(canonical_json_bytes(config))
            == record.get("canonical_sha256")
        ):
            return config
    raise ValueError("cannot resolve or authenticate run config")


def _is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _verified_project_path(relative: object, *, directory: bool = False) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("amendment path must be a non-empty relative path")
    path = (PROJECT_ROOT / relative).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    if (path.is_dir() if directory else path.is_file()):
        return path
    raise ValueError(f"amendment path is unavailable: {relative}")


def _verify_amendment_ledger(config: Mapping[str, Any]) -> bool:
    """Authenticate the consumed v1 release and the pre-endpoint v1.1 amendment."""

    try:
        amendment = config["amendment"]
        required = {
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
            set(amendment) != required
            or amendment["schema_version"] != "xa.e5-post-release-amendment.v1.1"
            or amendment["classification"]
            != "post_release_pre_endpoint_protocol_amendment"
            or not str(amendment["scientific_reason"]).strip()
            or amendment["eligibility_rule"]
            != "arm_independent_root_action_count_from_unscored_structural_candidate_actions"
            or amendment["root_eligibility_classes"] != list(ROOT_ELIGIBILITIES)
            or amendment["execution_status_taxonomy"] != list(EXECUTION_STATUSES)
            or amendment["degenerate_estimand_rule"]
            != "all_five_assigned_arms_solve_compile_and_enter_itt_with_zero_within_assignment_difference"
            or amendment["schedulable_mechanism_rule"]
            != "learned_policy_value_activity_and_four_arm_same_pool_are_required_only_when_root_action_count_is_positive"
            or amendment["family_activity_rule"]
            != "each_family_must_contain_at_least_one_schedulable_family_bit_seed_group"
            or amendment["direct_sensitivity_rule"]
            != "exclude_not_invoked_rows_and_record_per_cluster_reason"
            or amendment["failure_evidence_rule"]
            != "every_exception_writes_a_non_overwriting_nine_file_failed_attempt_bundle_and_separates_evidence_ok_from_experiment_completed"
        ):
            return False

        parent = amendment["parent_v1"]
        expected_parent_scalars = {
            "static_lock_canonical_sha256": PARENT_V1_STATIC_CANONICAL_SHA256,
            "config_file_sha256": "d1b8559f2cdd34f448d9c0c27c0d6672817aaf43e6c7aeae8a0dbbb8ae351e44",
            "config_canonical_sha256": "6a01191cdb326506db9f3a4f01fd6bd2022f0c65e7de472d098a028fd3960929",
            "runner_sha256": "611a27cb0eefe6134e254a695d44a7e40758d672e3fb8d928a399eb4a9ff9738",
            "verifier_sha256": "628abde452cdaf4bced0fec8cdcf1c7ea689ce25c748f56b86d0bad47cdf118f",
            "contract_test_sha256": "40dfb9133d17df4d848f08111b2b9bc80c092c2842a0c95ebb27c84e6a914f52",
        }
        if (
            set(parent) != {*expected_parent_scalars, "preflight", "seal"}
            or any(
                parent.get(key) != value
                for key, value in expected_parent_scalars.items()
            )
        ):
            return False
        if not all(
            _is_sha256(value)
            for key, value in parent.items()
            if key not in {"preflight", "seal"}
        ):
            return False

        preflight_binding = parent["preflight"]
        seal_binding = parent["seal"]
        if set(preflight_binding) != {
            "bundle",
            "summary_sha256",
            "raw_sha256",
            "manifest_sha256",
            "checksums_sha256",
            "calibration_sha256",
            "preflight_rows_sha256",
            "weights_sha256",
        } or set(seal_binding) != {
            "bundle",
            "summary_sha256",
            "manifest_sha256",
            "checksums_sha256",
            "evaluation_lock_sha256",
        }:
            return False
        preflight_root = _verified_project_path(
            preflight_binding["bundle"], directory=True
        )
        seal_root = _verified_project_path(seal_binding["bundle"], directory=True)
        preflight_rows = _read_jsonl(preflight_root / "raw.jsonl")
        preflight_summary = _read_json(preflight_root / "summary.json")
        seal_summary = _read_json(seal_root / "summary.json")
        if (
            not verify_bundle(preflight_root).ok
            or not verify_bundle(seal_root).ok
            or sha256_file(preflight_root / "summary.json")
            != preflight_binding["summary_sha256"]
            or sha256_file(preflight_root / "raw.jsonl")
            != preflight_binding["raw_sha256"]
            or sha256_file(preflight_root / "artifacts.manifest.json")
            != preflight_binding["manifest_sha256"]
            or sha256_file(preflight_root / "checksums.sha256")
            != preflight_binding["checksums_sha256"]
            or sha256_bytes(canonical_json_bytes(preflight_rows))
            != preflight_binding["preflight_rows_sha256"]
            or preflight_summary.get("calibration_sha256")
            != preflight_binding["calibration_sha256"]
            or preflight_summary.get("weights_sha256")
            != preflight_binding["weights_sha256"]
            or sha256_file(seal_root / "summary.json")
            != seal_binding["summary_sha256"]
            or sha256_file(seal_root / "artifacts.manifest.json")
            != seal_binding["manifest_sha256"]
            or sha256_file(seal_root / "checksums.sha256")
            != seal_binding["checksums_sha256"]
            or seal_binding["evaluation_lock_sha256"]
            != PARENT_V1_EVALUATION_LOCK_SHA256
            or seal_summary.get("evaluation_lock_sha256")
            != PARENT_V1_EVALUATION_LOCK_SHA256
            or sha256_bytes(canonical_json_bytes(seal_summary["evaluation_lock"]))
            != PARENT_V1_EVALUATION_LOCK_SHA256
            or seal_summary.get("static_lock_sha256")
            != PARENT_V1_STATIC_CANONICAL_SHA256
        ):
            return False

        incident = amendment["incident"]
        if (
            set(incident)
            != {
                "path",
                "readme_sha256",
                "attempt_sha256",
                "checksums_sha256",
                "first_release_run_id",
                "first_trial_error",
            }
            or incident.get("readme_sha256") != INCIDENT_README_SHA256
            or incident.get("attempt_sha256") != INCIDENT_ATTEMPT_SHA256
            or incident.get("checksums_sha256") != INCIDENT_CHECKSUMS_SHA256
            or incident.get("first_release_run_id")
            != "20260812-e5-ascon-primary-present-secondary-v1-s940000"
            or incident.get("first_trial_error")
            != "E5 root scheduler missing for ASCON bit 0, seed 1, arm heuristic_historical_greedy"
        ):
            return False
        repository_root = PROJECT_ROOT.parent.resolve()
        incident_root = (repository_root / str(incident["path"])).resolve()
        incident_root.relative_to(repository_root)
        readme = incident_root / "README.md"
        attempt_path = incident_root / "attempt.json"
        checksums_path = incident_root / "checksums.sha256"
        if (
            not incident_root.is_dir()
            or sha256_file(readme) != INCIDENT_README_SHA256
            or sha256_file(attempt_path) != INCIDENT_ATTEMPT_SHA256
            or sha256_file(checksums_path) != INCIDENT_CHECKSUMS_SHA256
        ):
            return False
        checksum_lines = {
            line.strip() for line in checksums_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if checksum_lines != {
            f"{INCIDENT_README_SHA256}  README.md",
            f"{INCIDENT_ATTEMPT_SHA256}  attempt.json",
        }:
            return False
        attempt = _read_json(attempt_path)
        if (
            attempt.get("schema_version") != "xa.e5-failed-first-release-attempt.v1"
            or attempt.get("attempt_id") != incident["first_release_run_id"]
            or attempt.get("status") != "failed_before_bundle_commit"
            or attempt.get("phase") != "evaluate"
            or attempt.get("track") != "xa202609/e5-external-crypto-holdout"
            or attempt.get("failure", {}).get("matrix_key")
            != {
                "family": "ASCON",
                "output_bit": 0,
                "solver_seed": 1,
                "arm": "heuristic_historical_greedy",
            }
            or attempt.get("failure", {}).get("failed_before_first_row_completed")
            is not True
            or attempt.get("artifact_state", {}).get("completed_evaluation_rows") != 0
            or attempt.get("artifact_state", {}).get("performance_outcome_available")
            is not False
            or attempt.get("release_state", {}).get("model_or_protocol_selection_after_release")
            is not False
            or attempt.get("claim_boundary", {}).get("performance_evidence") is not False
            or attempt.get("frozen_bindings", {}).get("static_protocol_lock", {}).get(
                "canonical_sha256"
            )
            != PARENT_V1_STATIC_CANONICAL_SHA256
            or attempt.get("frozen_bindings", {}).get("seal", {}).get(
                "evaluation_lock_sha256"
            )
            != PARENT_V1_EVALUATION_LOCK_SHA256
        ):
            return False

        exposure = amendment["exposure_ledger"]
        if exposure != {
            "release_gate_completed": True,
            "tables_verified_at_release": ["ASCON", "PRESENT"],
            "trial_search_entered": [
                {
                    "family": "ASCON",
                    "output_bit": 0,
                    "solver_seed": 1,
                    "arm": "heuristic_historical_greedy",
                }
            ],
            "trial_search_not_entered_for_remaining_assignments": True,
            "persisted_trial_rows": 0,
            "performance_outcomes_observed": False,
            "endpoint_results_observed": False,
            "comparisons_observed": False,
            "noisy_outcomes_observed": False,
            "model_selection_after_release": False,
            "weight_refit_after_release": False,
        }:
            return False
        frozen = amendment["frozen_invariants"]
        return bool(
            set(frozen)
            == {
                "model_changed",
                "weights_changed",
                "search_hyperparameters_changed",
                "qaoa_hyperparameters_changed",
                "solver_seeds_changed",
                "native_profile_changed",
                "primary_endpoint_changed",
                "secondary_endpoints_changed",
            }
            and all(value is False for value in frozen.values())
        )
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False


def _check(condition: object, name: str, checks: dict[str, bool], errors: list[str]) -> None:
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"failed check: {name}")


def _truth_table_sha256(bf: BooleanFunction) -> str:
    count = ((1 << bf.n) + 7) // 8
    return hashlib.sha256(int(bf.truth_table).to_bytes(count, "little")).hexdigest()


def _tree_record(relative_root: str) -> dict[str, Any]:
    root = PROJECT_ROOT / relative_root
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        records.append(
            {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(path)}
        )
    return {
        "path": relative_root,
        "sha256": sha256_bytes(canonical_json_bytes(records)),
        "file_count": len(records),
    }


def _source_tree_sha256() -> str:
    records = []
    for relative_root in ("src", "scripts", "tests"):
        for path in sorted((PROJECT_ROOT / relative_root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            records.append(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
    return sha256_bytes(canonical_json_bytes(records))


def _compute_contract_sha256(config: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(config["compute_contract"]))


def _establish_compute_contract(
    config: Mapping[str, Any], *, context: str
) -> dict[str, Any]:
    contract = dict(config["compute_contract"])
    expected = {
        "device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    if contract != expected:
        raise RuntimeError("refusing an unfrozen E5 verifier compute contract")
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
        except Exception as exc:
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
            f"cannot establish E5 verifier compute contract during {context}: "
            f"observed={observed}; errors={detail}"
        )
    return {
        "schema_version": COMPUTE_RUNTIME_SCHEMA,
        "context": context,
        "compute_contract": contract,
        "compute_contract_sha256": _compute_contract_sha256(config),
        "observed_before": before,
        "observed_after": observed,
        "reset_applied": before != observed,
        "setter_errors_ignored_only_after_matching_postconditions": setter_errors,
        "established": True,
    }


def _compute_runtime_matches(runtime: object, config: Mapping[str, Any]) -> bool:
    return bool(
        isinstance(runtime, Mapping)
        and runtime.get("schema_version") == COMPUTE_RUNTIME_SCHEMA
        and runtime.get("compute_contract") == config["compute_contract"]
        and runtime.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and runtime.get("observed_after") == config["compute_contract"]
        and runtime.get("established") is True
    )


def _resolve_link(bundle_root: Path, hint: object) -> Path:
    if not isinstance(hint, str) or not hint:
        raise ValueError("bundle link must be a non-empty path string")
    raw = Path(hint)
    candidates = [raw] if raw.is_absolute() else [bundle_root.parent / raw, PROJECT_ROOT / raw]
    project = PROJECT_ROOT.resolve()
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(project)
        except ValueError:
            continue
        if resolved.is_dir():
            return resolved
    raise ValueError(f"linked bundle is unavailable or outside project root: {hint}")


def _profile_spec(config: Mapping[str, Any]) -> SyntheticExecutionProfileSpec:
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


def _frozen_profile(config: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    spec = _profile_spec(config)
    profile = spec.build(int(config["native_profile"]["frozen_n_qubits"]))
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


def _search_config(config: Mapping[str, Any]) -> SearchConfig:
    raw = config["search"]
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        max_factor_ancilla=int(raw["max_factor_ancilla"]),
        max_factor_size=int(raw["max_factor_size"]),
        candidate_top_k=int(raw["candidate_top_k"]),
        mcts_simulations=int(raw["simulations"]),
        neural_mcts_simulations=int(raw["simulations"]),
        gate_mode="mct",
    )


def _action_from_signature(value: Mapping[str, Any]) -> FactorAction:
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


def _plan_from_trace(payload: Mapping[str, Any]) -> Plan:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("plan trace nodes missing")
    by_id = {str(node["node_id"]): node for node in nodes}
    root_id = str(payload.get("root_id"))
    if len(by_id) != len(nodes) or root_id not in by_id:
        raise ValueError("invalid plan trace ids")
    children: dict[tuple[str, str], str] = {}
    for node in nodes:
        parent = node.get("parent_id")
        if parent is not None:
            key = (str(parent), str(node.get("edge")))
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

    return build(root_id)


def _circuit_from_ir(payload: Mapping[str, Any]) -> QuantumCircuit:
    circuit = QuantumCircuit(int(payload["n_qubits"]))
    circuit.gates = [
        Gate(
            str(gate["gate_type"]),
            [int(value) for value in gate["controls"]],
            int(gate["target"]),
        )
        for gate in payload["gates"]
    ]
    return circuit


def _weights_from_payload(payload: Mapping[str, Any]) -> FrozenExecutionPenaltyWeights:
    return FrozenExecutionPenaltyWeights(
        calibration_sha256=str(payload["calibration_sha256"]),
        profile_sha256=str(payload["profile_sha256"]),
        **{name: float(payload[name]) for name in FEATURES},
    )


def _recompute_weights(
    rows: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
    *,
    calibration_sha256: str,
    profile_sha256: str,
) -> tuple[FrozenExecutionPenaltyWeights, dict[str, float]]:
    rule = config["weight_selection"]
    target = float(rule["target_penalty_at_component_medians"])
    mixture = rule["feature_mixture"]
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
        share = float(mixture[name])
        if share > 0.0 and scale <= 0.0:
            raise ValueError(f"zero scale for weighted feature {name}")
        scales[name] = scale
        coefficients[name] = 0.0 if share == 0.0 else target * share / scale
    return (
        FrozenExecutionPenaltyWeights(
            calibration_sha256=calibration_sha256,
            profile_sha256=profile_sha256,
            **coefficients,
        ),
        scales,
    )


def _verify_v4_gate(config: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    try:
        compute_runtime = _establish_compute_contract(
            config, context="verifier-v4-before-checkpoint-inference"
        )
        gate = config["foundation_v4"]
        root = (PROJECT_ROOT / str(gate["bundle"])).resolve()
        root.relative_to(PROJECT_ROOT.resolve())
        report = verify_foundation_v4_bundle(root, require_current_source=True)
        summary = _read_json(root / "training_summary.json")
        model_card = _read_json(root / "model_card.json")
        source = _read_json(root / "source_manifest.json")
        dataset = _read_json(root / "dataset_manifest.json")
        checkpoint = root / "checkpoint.pt"
        model_card_sha = sha256_file(root / "model_card.json")
        source_sha = sha256_file(root / "source_manifest.json")
        ok = bool(
            report.get("ok") is True
            and report.get("profile") == "formal"
            and report.get("formal_training_completed") is True
            and report.get("parameter_count") == EXPECTED_PARAMETER_COUNT
            and summary.get("formal_training_completed") is True
            and summary.get("profile") == "formal"
            and sha256_file(checkpoint) == gate["checkpoint_sha256"]
            == model_card.get("artifact", {}).get("sha256")
            and model_card_sha == gate["model_card_sha256"]
            and sha256_file(root / "training_summary.json")
            == gate["training_summary_sha256"]
            and sha256_file(root / "dataset_manifest.json")
            == gate["dataset_manifest_file_sha256"]
            and dataset.get("dataset_sha256") == gate["dataset_sha256"]
            and source_sha == gate["source_manifest_sha256"]
            and sha256_file(root / "artifacts.manifest.json")
            == gate["artifact_manifest_sha256"]
            and sha256_file(root / "checksums.sha256") == gate["checksums_sha256"]
            and model_card.get("training", {}).get("profile") == "formal"
            and model_card.get("training", {}).get("initialization")
            == "seeded_random_from_scratch"
            and model_card.get("training", {}).get("parent_checkpoint") is None
            and model_card.get("training", {}).get("v3_weights_loaded") is False
            and model_card.get("data", {}).get("crypto_oracle_training_examples") == 0
            and model_card.get("data", {}).get("crypto_excluded") is True
            and model_card.get("data", {}).get("evaluation_not_accessed") is True
            and model_card.get("data", {}).get("allowed_num_vars")
            == gate["required_allowed_num_vars"]
            and model_card.get("data", {}).get("crypto_oracle_training_examples")
            == gate["required_crypto_training_examples"]
            and source.get("schema_version") == "xa.foundation-source-manifest.v4"
        )
        return ok, {
            "bundle": root,
            "checkpoint": checkpoint,
            "checkpoint_sha256": sha256_file(checkpoint),
            "model_card_sha256": model_card_sha,
            "source_manifest_sha256": source_sha,
            "report": report,
            "compute_contract": dict(config["compute_contract"]),
            "compute_contract_sha256": _compute_contract_sha256(config),
            "compute_runtime": compute_runtime,
        }
    except (KeyError, TypeError, ValueError, OSError, RuntimeError):
        return False, {}


def _preflight_cases(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = config["preflight"]
    widths = [int(value) for value in raw["widths"]]
    count = int(raw["cases_per_width"])
    seed_base = int(raw["seed_base"])
    cases: list[dict[str, Any]] = []
    ordinal = 0
    for width in widths:
        for index in range(count):
            seed = seed_base + ordinal
            bf = BooleanFunction(width, random.Random(seed).getrandbits(1 << width))
            cases.append(
                {
                    "case_id": f"e5-preflight-n{width}-k{index:02d}",
                    "n": width,
                    "instance_seed": seed,
                    "truth_table_sha256": _truth_table_sha256(bf),
                    "truth_table_hex": (
                        f"0x{int(bf.truth_table):0{1 << max(0, width - 2)}x}"
                    ),
                }
            )
            ordinal += 1
    return cases


def _preflight_scientific_projection(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if key not in {"schema_version", "run_id"}}
        for row in rows
    ]


def _parent_v1_preflight(
    config: Mapping[str, Any],
) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    binding = config["amendment"]["parent_v1"]["preflight"]
    root = _verified_project_path(binding["bundle"], directory=True)
    summary = _read_json(root / "summary.json")
    rows = _read_jsonl(root / "raw.jsonl")
    if (
        not verify_bundle(root).ok
        or sha256_file(root / "summary.json") != binding["summary_sha256"]
        or sha256_file(root / "raw.jsonl") != binding["raw_sha256"]
        or summary.get("calibration_sha256") != binding["calibration_sha256"]
        or summary.get("weights_sha256") != binding["weights_sha256"]
        or len(rows) != 12
    ):
        raise ValueError("parent v1 preflight binding is invalid")
    return root, summary, rows


def _preflight_compile_row_ok(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    profile_spec: SyntheticExecutionProfileSpec,
) -> bool:
    try:
        bf = BooleanFunction(int(row["n"]), int(str(row["truth_table_hex"]), 16))
        terms = frozenset(anf_monomials(bf))
        signatures = row["candidate_pool"]["action_signatures"]
        records = row["compile_time_candidates"]
        if len(signatures) != len(records):
            return False
        search_config = _search_config(config)
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        _, frozen_sha = _frozen_profile(config)
        for index, (signature, record) in enumerate(zip(signatures, records)):
            action = _action_from_signature(signature)
            plan = complete_root_action_rollout(
                StateKey(terms, 0, 0), action, search_config
            )
            if not verify_plan_anf(plan).ok:
                return False
            allocated = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
            circuit = emit_plan_to_circuit(plan, bf.n, allocated)
            if circuit.n_qubits > frozen_n:
                return False
            if circuit.n_qubits < frozen_n:
                padded = QuantumCircuit(frozen_n)
                padded.gates = list(circuit.gates)
                circuit = padded
            compilation = compile_superconducting(circuit, profile_spec.build(frozen_n))
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
            actual = record["resource_components"]
            if (
                int(record["candidate_index"]) != index
                or record.get("plan_anf_ok") is not True
                or record.get("circuit_anf_ok") is not True
                or record.get("synthetic_profile") is not True
                or record.get("hardware_execution") is not False
                or int(record.get("logical_n_qubits", -1)) != frozen_n
                or record.get("concrete_profile_sha256") != frozen_sha
                or any(
                    not math.isclose(
                        float(actual[name]), float(expected[name]), rel_tol=0.0, abs_tol=1e-12
                    )
                    for name in FEATURES
                )
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


def _preflight_pool_ok(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    checkpoint: Path,
    profile_spec: SyntheticExecutionProfileSpec,
) -> bool:
    """Recreate the v4 root pool without importing any hold-out module."""

    try:
        bf = BooleanFunction(int(row["n"]), int(str(row["truth_table_hex"]), 16))
        terms = frozenset(anf_monomials(bf))
        search_config = _search_config(config)
        cases = _preflight_cases(config)
        zero_calibration_sha = sha256_bytes(
            canonical_json_bytes(
                [
                    {
                        key: case[key]
                        for key in ("case_id", "n", "truth_table_sha256")
                    }
                    for case in cases
                ]
            )
        )
        zero_weights = FrozenExecutionPenaltyWeights(
            calibration_sha256=zero_calibration_sha,
            profile_sha256=profile_spec.profile_sha256,
        )
        scorer = FoundationScorer.from_checkpoint(checkpoint)
        if any(parameter.device.type != "cpu" for parameter in scorer.model.parameters()):
            return False
        policy = TermThresholdPolicyScorer(
            scorer, int(config["search"]["policy_term_threshold"])
        )
        value = LearnedValueEstimator(scorer, search_config)
        search = config["search"]
        qaoa = config["qaoa"]
        scheduler = DiversitySchedulerConfig(
            method="greedy",
            budget_requested=int(search["scheduler_budget"]),
            pool_size=int(search["scheduler_pool_size"]),
            min_candidates=int(search["scheduler_min_candidates"]),
            max_depth=0,
            redundancy_weight=float(search["redundancy_weight"]),
            redundancy_alpha=float(search["redundancy_alpha"]),
            utility_clip=float(search["utility_clip"]),
            exact_max_candidates=12,
            seed=int(search["scheduler_seed_base"]) + int(row["instance_seed"]),
            qaoa_mode="shot",
            qaoa_p=int(qaoa["p"]),
            qaoa_shots=int(qaoa["shots"]),
            qaoa_noise_bitflip_probability=0.0,
            qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
            qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
        )
        adjuster = make_root_rollout_execution_utility_adjuster(
            n_inputs=int(row["n"]),
            search_config=search_config,
            profile_spec=profile_spec,
            penalty_weights=zero_weights,
            expected_profile_sha256=profile_spec.profile_sha256,
            execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
        )
        solver = NeuralMCTSSolver(
            config=search_config,
            simulations=0,
            seed=int(row["instance_seed"]),
            neural_scorer=policy,
            value_estimator=value,
            rollout_scorer=None,
            scheduler_config=scheduler,
            execution_utility_adjuster=adjuster,
        )
        node = solver._node(StateKey(terms, 0, 0))
        solver._expand(node)
        solver._schedule_node(node, 0)
        if node.scheduler_decision is None:
            return False
        diagnostics = dict(node.scheduler_decision.diagnostics)
        width = int(diagnostics["candidate_count"])
        actions = tuple(node.actions[:width])
        raw = [float(item) for item in diagnostics["raw_utilities"]]
        pool = {
            "schema_version": "xa.e5-preflight-candidate-pool.v1",
            "case_id": row["case_id"],
            "truth_table_sha256": row["truth_table_sha256"],
            "node_id": diagnostics["node_id"],
            "candidate_count": width,
            "budget_requested": int(search["scheduler_budget"]),
            "budget_effective": min(int(search["scheduler_budget"]), width),
            "action_signatures": [_action_signature(action) for action in actions],
            "raw_utilities": raw,
            "redundancy": [
                [float(item) for item in values]
                for values in action_redundancy_matrix(
                    actions, alpha=float(search["redundancy_alpha"])
                )
            ],
        }
        candidates = diagnostics.get("execution_feedback", {}).get(
            "diagnostics", {}
        ).get("candidates", [])
        return bool(
            row.get("candidate_pool") == pool
            and row.get("candidate_pool_sha256")
            == sha256_bytes(canonical_json_bytes(pool))
            and row.get("raw_scheduler_utilities") == raw
            and row.get("compile_time_candidates") == candidates
            and row.get("learned_policy_active_at_root") is True
            and policy.learned_states > 0
            and row.get("learned_value_enabled") is True
            and row.get("learned_value_stats") == value.stats.as_dict()
        )
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return False


def _verify_preflight(
    root: Path,
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        config = _effective_config(run)
    except (KeyError, TypeError, ValueError, OSError):
        return {"effective_config_present": False}
    config_sha = sha256_bytes(canonical_json_bytes(config))
    v4_ok, v4 = _verify_v4_gate(config)
    static_ok, _, static_sha = _verify_static_lock(config)
    amendment_ok = _verify_amendment_ledger(config)
    profile_spec = _profile_spec(config)
    concrete_profile, concrete_sha = _frozen_profile(config)
    expected = _preflight_cases(config)
    actual = [
        {
            "case_id": row.get("case_id"),
            "n": row.get("n"),
            "instance_seed": row.get("instance_seed"),
            "truth_table_sha256": row.get("truth_table_sha256"),
            "truth_table_hex": row.get("truth_table_hex"),
        }
        for row in rows
    ]
    calibration_dataset = {
        "schema_version": "xa.e5-preflight-dataset.v1",
        "generator": config["preflight"]["generator"],
        "cases": [
            {
                key: row[key]
                for key in ("case_id", "instance_seed", "n", "truth_table_sha256")
            }
            for row in rows
        ],
    }
    rows_sha = sha256_bytes(canonical_json_bytes(rows))
    evidence = {
        "schema_version": "xa.e5-preflight-evidence-binding.v1",
        "config_sha256": config_sha,
        "foundation_v4_checkpoint_sha256": v4.get("checkpoint_sha256"),
        "foundation_v4_model_card_sha256": v4.get("model_card_sha256"),
        "foundation_v4_source_manifest_sha256": v4.get("source_manifest_sha256"),
        "profile_spec_sha256": profile_spec.profile_sha256,
        "concrete_profile_sha256": concrete_sha,
        "compute_contract_sha256": _compute_contract_sha256(config),
        "preflight_rows_sha256": rows_sha,
    }
    reproduction_evidence_sha = sha256_bytes(canonical_json_bytes(evidence))
    try:
        parent_root, parent_summary, parent_rows = _parent_v1_preflight(config)
        parent_projection_sha = sha256_bytes(
            canonical_json_bytes(_preflight_scientific_projection(parent_rows))
        )
        projection_sha = sha256_bytes(
            canonical_json_bytes(_preflight_scientific_projection(rows))
        )
        calibration_sha = str(parent_summary["calibration_sha256"])
        parent_ok = projection_sha == parent_projection_sha
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        parent_root = Path("/nonexistent")
        parent_summary = {}
        parent_projection_sha = ""
        projection_sha = ""
        calibration_sha = ""
        parent_ok = False
    weights_ok = False
    scales_ok = False
    try:
        weights, scales = _recompute_weights(
            rows,
            config,
            calibration_sha256=calibration_sha,
            profile_sha256=profile_spec.profile_sha256,
        )
        weights_ok = (
            weights.canonical_payload() == summary.get("frozen_penalty_weights")
            and weights.weights_sha256 == summary.get("weights_sha256")
        )
        scales_ok = all(
            math.isclose(
                scales[name],
                float(summary["weight_selection"]["positive_median_scales"][name]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for name in FEATURES
        )
    except (KeyError, TypeError, ValueError):
        pass

    _check(
        summary.get("schema_version") == PREFLIGHT_SUMMARY_SCHEMA
        and summary.get("phase") == "preflight"
        and run.get("status") == "complete"
        and summary.get("evidence_ok") is True
        and summary.get("experiment_completed") is True
        and summary.get("amendment_classification")
        == config["amendment"]["classification"]
        and summary.get("amendment_sha256")
        == sha256_bytes(canonical_json_bytes(config["amendment"])),
        "preflight_phase_schema_status",
        checks,
        errors,
    )
    _check(
        config.get("schema_version") == CONFIG_SCHEMA
        and config_sha == run.get("config", {}).get("canonical_sha256")
        == summary.get("config_sha256"),
        "preflight_config_identity",
        checks,
        errors,
    )
    _check(
        summary.get("compute_contract") == config.get("compute_contract")
        and summary.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(summary.get("compute_runtime"), config)
        and run.get("compute_contract") == config.get("compute_contract")
        and run.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(run.get("compute_runtime"), config),
        "preflight_compute_contract_bound",
        checks,
        errors,
    )
    _check(v4_ok, "foundation_v4_formal_current_source_gate", checks, errors)
    _check(
        static_ok
        and amendment_ok
        and summary.get("static_lock_sha256") == static_sha
        and summary.get("source_tree_sha256") == _source_tree_sha256()
        == run.get("source", {}).get("source_tree_sha256"),
        "preflight_static_lock_and_source_tree",
        checks,
        errors,
    )
    model_gate = summary.get("model_gate", {})
    _check(
        model_gate.get("ok") is True
        and model_gate.get("profile") == "formal"
        and model_gate.get("parameter_count") == EXPECTED_PARAMETER_COUNT
        and model_gate.get("checkpoint_sha256") == v4.get("checkpoint_sha256")
        and model_gate.get("model_card_sha256") == v4.get("model_card_sha256")
        and model_gate.get("source_manifest_sha256") == v4.get("source_manifest_sha256")
        and model_gate.get("crypto_training_examples") == 0
        and model_gate.get("evaluation_module_imported") is False
        and model_gate.get("compute_contract") == config["compute_contract"]
        and model_gate.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(model_gate.get("compute_runtime"), config)
        and v4.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(v4.get("compute_runtime"), config),
        "preflight_model_gate_bound",
        checks,
        errors,
    )
    _check(
        len(rows) == 12
        and all(row.get("schema_version") == PREFLIGHT_ROW_SCHEMA for row in rows)
        and actual == expected,
        "twelve_frozen_n6_n7_cases_recomputed",
        checks,
        errors,
    )
    _check(
        not (
            {row.get("truth_table_sha256") for row in rows}
            & {
                str(digest)
                for family in config["holdout_access"]["families"].values()
                for digest in (
                    family["vector_truth_table_sha256"],
                    *family["coordinate_truth_table_sha256"],
                )
            }
        ),
        "preflight_holdout_hash_disjoint",
        checks,
        errors,
    )
    _check(
        all(
            row.get("compile_time_only") is True
            and row.get("crypto_module_imported") is False
            and row.get("holdout_truth_table_accessed") is False
            and row.get("evaluation_result_accessed") is False
            and row.get("noisy_endpoint_accessed") is False
            and row.get("hardware_execution") is False
            and "family" not in row
            and "ascon" not in canonical_json_bytes(row).decode("utf-8").lower()
            and "present" not in canonical_json_bytes(row).decode("utf-8").lower()
            for row in rows
        )
        and summary.get("access_contract")
        == {
            "crypto_module_imported": False,
            "ascon_accessed": False,
            "present_accessed": False,
            "evaluation_result_accessed": False,
            "noisy_endpoint_accessed": False,
            "compile_time_only": True,
        },
        "preflight_runtime_holdout_access_boundary",
        checks,
        errors,
    )
    checkpoint = Path(v4.get("checkpoint", "/nonexistent"))
    _check(
        bool(rows)
        and checkpoint.is_file()
        and all(
            sha256_bytes(canonical_json_bytes(row.get("candidate_pool")))
            == row.get("candidate_pool_sha256")
            and _preflight_pool_ok(row, config, checkpoint, profile_spec)
            and _preflight_compile_row_ok(row, config, profile_spec)
            for row in rows
        ),
        "preflight_pool_and_native_features_recomputed",
        checks,
        errors,
    )
    _check(
        summary.get("frozen_profile") == concrete_profile
        and summary.get("profile_sha256") == concrete_sha
        and summary.get("profile_spec_sha256") == profile_spec.profile_sha256
        and int(config["native_profile"]["frozen_n_qubits"]) == 10,
        "preflight_fixed10q_profile_recomputed",
        checks,
        errors,
    )
    _check(
        evidence == summary.get("preflight_evidence_binding")
        and reproduction_evidence_sha == summary.get("reproduction_evidence_sha256")
        and parent_ok
        and projection_sha == summary.get("scientific_projection_sha256")
        and calibration_sha == summary.get("calibration_sha256")
        and rows_sha == summary.get("preflight_rows_sha256")
        and calibration_dataset == summary.get("calibration_dataset")
        and summary.get("parent_v1_binding")
        == {
            "bundle_hint": parent_root.name,
            "summary_sha256": sha256_file(parent_root / "summary.json"),
            "raw_sha256": sha256_file(parent_root / "raw.jsonl"),
            "calibration_sha256": parent_summary.get("calibration_sha256"),
            "weights_sha256": parent_summary.get("weights_sha256"),
            "scientific_projection_sha256": parent_projection_sha,
            "exact_weights_reused_after_independent_recomputation": True,
        },
        "preflight_evidence_hash_chain",
        checks,
        errors,
    )
    _check(
        weights_ok
        and scales_ok
        and parent_ok
        and summary.get("frozen_penalty_weights")
        == parent_summary.get("frozen_penalty_weights")
        and summary.get("weights_sha256") == parent_summary.get("weights_sha256")
        and summary.get("weight_selection") == parent_summary.get("weight_selection")
        and all(
            math.isfinite(float(summary["frozen_penalty_weights"][name]))
            and float(summary["frozen_penalty_weights"][name]) >= 0.0
            for name in FEATURES
        ),
        "preflight_nonnegative_weights_recomputed",
        checks,
        errors,
    )
    _check(
        summary.get("performance_evidence") is False
        and summary.get("holdout_model_selection") is False
        and summary.get("learned_policy_active_all") is True
        and summary.get("learned_value_enabled_all") is True,
        "preflight_no_performance_claim",
        checks,
        errors,
    )
    return checks


def _verify_static_lock(config: Mapping[str, Any]) -> tuple[bool, dict[str, Any], str]:
    try:
        path = PROJECT_ROOT / str(config["protocol_lock"]["path"])
        lock = _read_json(path)
        lock_sha = sha256_bytes(canonical_json_bytes(lock))
        config_sha = sha256_bytes(canonical_json_bytes(config))
        sources = lock["sources"]
        expected_foundation = {
            "bundle": config["foundation_v4"]["bundle"],
            "checkpoint_sha256": config["foundation_v4"]["checkpoint_sha256"],
            "model_card_sha256": config["foundation_v4"]["model_card_sha256"],
            "dataset_sha256": config["foundation_v4"]["dataset_sha256"],
            "source_manifest_sha256": config["foundation_v4"]["source_manifest_sha256"],
        }
        ok = bool(
            set(lock)
            == {
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
            and lock.get("schema_version") == PROTOCOL_LOCK_SCHEMA
            and lock.get("freeze_semantics") == "frozen_before_preflight_and_holdout_release"
            and lock.get("config", {}).get("path")
            == "configs/xa202609/e5_external_crypto_holdout_v1.json"
            and set(lock.get("config", {}))
            == {"path", "file_sha256", "canonical_sha256"}
            and lock.get("config", {}).get("file_sha256")
            == sha256_file(
                PROJECT_ROOT / "configs/xa202609/e5_external_crypto_holdout_v1.json"
            )
            and lock.get("config", {}).get("canonical_sha256") == config_sha
            and lock.get("amendment") == config["amendment"]
            and lock.get("amendment_sha256")
            == sha256_bytes(canonical_json_bytes(config["amendment"]))
            and lock.get("parent_v1_static_lock_canonical_sha256")
            == PARENT_V1_STATIC_CANONICAL_SHA256
            and set(sources) == set(EXPECTED_SOURCE_PATHS)
            and all(
                sources[role].get("path") == relative
                and sources[role].get("sha256") == sha256_file(PROJECT_ROOT / relative)
                for role, relative in EXPECTED_SOURCE_PATHS.items()
            )
            and lock.get("source_tree_sha256") == _tree_record("src")["sha256"]
            and lock.get("foundation_v4") == expected_foundation
            and lock.get("crypto_registry", {}).get("path")
            == config["holdout_access"]["registry_path"]
            and lock.get("crypto_registry", {}).get("sha256")
            == config["holdout_access"]["registry_sha256"]
            == sha256_file(PROJECT_ROOT / config["holdout_access"]["registry_path"])
            and lock.get("compute_contract") == config["compute_contract"]
            and lock.get("compute_contract_sha256")
            == _compute_contract_sha256(config)
            and lock.get("primary_endpoint") == config["primary_endpoint"]
            and lock.get("primary_endpoint_sha256")
            == sha256_bytes(canonical_json_bytes(config["primary_endpoint"]))
            and lock.get("arm_matrix_sha256")
            == sha256_bytes(canonical_json_bytes(config["evaluation"]["arms"]))
        )
        return ok, lock, lock_sha
    except (KeyError, TypeError, ValueError, OSError):
        return False, {}, ""


def _linked_preflight(
    current_root: Path,
    binding: Mapping[str, Any],
) -> tuple[bool, Path | None, dict[str, Any], list[dict[str, Any]]]:
    try:
        hint = binding.get("bundle") or binding.get("bundle_hint")
        root = _resolve_link(current_root, hint)
        if root == current_root:
            return False, None, {}, []
        report = verify_e5_external_crypto_holdout_bundle(
            root, _allow_links=False, _expected_phase="preflight"
        )
        summary = _read_json(root / "summary.json")
        rows = _read_jsonl(root / "raw.jsonl")
        ok = bool(
            report.get("ok") is True
            and binding.get("summary_sha256") == sha256_file(root / "summary.json")
            and binding.get("raw_sha256") == sha256_file(root / "raw.jsonl")
            and binding.get("calibration_sha256") == summary.get("calibration_sha256")
            and binding.get("weights_sha256") == summary.get("weights_sha256")
            and binding.get("profile_sha256") == summary.get("profile_sha256")
            and binding.get("profile_spec_sha256") == summary.get("profile_spec_sha256")
            and binding.get("compute_contract_sha256")
            == summary.get("compute_contract_sha256")
            == _compute_contract_sha256(_effective_config(_read_json(root / "run.json")))
        )
        return ok, root, summary, rows
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False, None, {}, []


def _evaluation_lock_ok(
    lock: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    static_lock_sha: str,
    preflight_binding: Mapping[str, Any],
    preflight_summary: Mapping[str, Any],
) -> bool:
    try:
        expected = {
            "schema_version": EVALUATION_LOCK_SCHEMA,
            "freeze_semantics": "frozen_after_verified_preflight_before_holdout_release",
            "amendment_classification": config["amendment"]["classification"],
            "amendment_sha256": sha256_bytes(
                canonical_json_bytes(config["amendment"])
            ),
            "parent_v1_static_lock_canonical_sha256": (
                PARENT_V1_STATIC_CANONICAL_SHA256
            ),
            "parent_v1_evaluation_lock_sha256": (
                PARENT_V1_EVALUATION_LOCK_SHA256
            ),
            "incident_sha256": sha256_bytes(
                canonical_json_bytes(config["amendment"]["incident"])
            ),
            "exposure_ledger_sha256": sha256_bytes(
                canonical_json_bytes(config["amendment"]["exposure_ledger"])
            ),
            "config_sha256": sha256_bytes(canonical_json_bytes(config)),
            "static_lock_sha256": static_lock_sha,
            "source_tree_sha256": preflight_summary["source_tree_sha256"],
            "compute_contract": dict(config["compute_contract"]),
            "compute_contract_sha256": _compute_contract_sha256(config),
            "formal_v4": {
                "checkpoint_sha256": config["foundation_v4"]["checkpoint_sha256"],
                "model_card_sha256": config["foundation_v4"]["model_card_sha256"],
                "dataset_sha256": config["foundation_v4"]["dataset_sha256"],
                "source_manifest_sha256": config["foundation_v4"]["source_manifest_sha256"],
            },
            "preflight": dict(preflight_binding),
            "preflight_binding": dict(preflight_binding),
            "weights_sha256": preflight_summary["weights_sha256"],
            "frozen_penalty_weights": preflight_summary["frozen_penalty_weights"],
            "profile_spec_sha256": preflight_summary["profile_spec_sha256"],
            "profile_sha256": preflight_summary["profile_sha256"],
            "holdout_registry": {
                "path": config["holdout_access"]["registry_path"],
                "sha256": config["holdout_access"]["registry_sha256"],
                "family_exclusion_label": config["holdout_access"]["family_exclusion_label"],
                "family_order": config["evaluation"]["family_order"],
                "families_sha256": sha256_bytes(
                    canonical_json_bytes(config["holdout_access"]["families"])
                ),
            },
            "evaluation_matrix": {
                "arms": [arm["name"] for arm in config["evaluation"]["arms"]],
                "arms_sha256": sha256_bytes(
                    canonical_json_bytes(config["evaluation"]["arms"])
                ),
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
            "primary_endpoint": config["primary_endpoint"],
            "primary_endpoint_sha256": sha256_bytes(
                canonical_json_bytes(config["primary_endpoint"])
            ),
            "statistics": config["statistics"],
            "noisy_diagnostic": config["noisy_diagnostic"],
            "evaluation_contract": {
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
                "family_exclusion_label": config["holdout_access"][
                    "family_exclusion_label"
                ],
                "family_contracts": config["holdout_access"]["families"],
            },
            "holdout_accessed_while_sealing": False,
            "holdout_release": {
                "allowed_phase": "evaluate",
                "first_import_must_follow_all_gate_checks": True,
                "release_token": "e5-sealed-evaluate-only",
                "model_or_protocol_selection_after_release": False,
            },
        }
        return lock == expected
    except (KeyError, TypeError, ValueError, OSError):
        return False


def _verify_seal(
    root: Path,
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        config = _effective_config(run)
    except (KeyError, TypeError, ValueError, OSError):
        return {"effective_config_present": False}
    config_sha = sha256_bytes(canonical_json_bytes(config))
    static_ok, static_lock, static_sha = _verify_static_lock(config)
    v4_ok, v4 = _verify_v4_gate(config)
    binding = summary.get("preflight_binding", {})
    linked_ok, _, preflight_summary, _ = _linked_preflight(root, binding)
    evaluation_lock = summary.get("evaluation_lock", {})
    evaluation_lock_sha = sha256_bytes(canonical_json_bytes(evaluation_lock))

    _check(
        summary.get("schema_version") == SEAL_SUMMARY_SCHEMA
        and summary.get("phase") == "seal"
        and run.get("status") == "complete"
        and summary.get("evidence_ok") is True
        and summary.get("experiment_completed") is True
        and summary.get("amendment_classification")
        == config["amendment"]["classification"]
        and summary.get("amendment_sha256")
        == sha256_bytes(canonical_json_bytes(config["amendment"])),
        "seal_phase_schema_status",
        checks,
        errors,
    )
    _check(
        not rows and summary.get("row_count", 0) == 0,
        "seal_has_no_evaluation_rows",
        checks,
        errors,
    )
    _check(
        config_sha == run.get("config", {}).get("canonical_sha256")
        == summary.get("config_sha256"),
        "seal_config_identity",
        checks,
        errors,
    )
    _check(
        summary.get("compute_contract") == config["compute_contract"]
        and summary.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(summary.get("compute_runtime"), config)
        and run.get("compute_contract") == config["compute_contract"]
        and run.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(run.get("compute_runtime"), config)
        and binding.get("compute_contract_sha256")
        == preflight_summary.get("compute_contract_sha256")
        == _compute_contract_sha256(config),
        "seal_compute_contract_bound",
        checks,
        errors,
    )
    _check(static_ok and _verify_amendment_ledger(config)
           and summary.get("static_lock_sha256") == static_sha,
           "seal_static_protocol_lock", checks, errors)
    model_gate = summary.get("model_gate", {})
    _check(
        v4_ok
        and v4.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(v4.get("compute_runtime"), config)
        and model_gate.get("ok") is True
        and model_gate.get("checkpoint_sha256") == v4.get("checkpoint_sha256")
        and model_gate.get("compute_contract") == config["compute_contract"]
        and model_gate.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(model_gate.get("compute_runtime"), config),
        "seal_foundation_v4_gate",
        checks,
        errors,
    )
    _check(linked_ok, "seal_preflight_bundle_independently_verified", checks, errors)
    _check(
        summary.get("source_tree_sha256") == _source_tree_sha256()
        == run.get("source", {}).get("source_tree_sha256")
        == preflight_summary.get("source_tree_sha256"),
        "seal_cross_phase_complete_source_tree",
        checks,
        errors,
    )
    _check(
        isinstance(evaluation_lock, dict)
        and bool(evaluation_lock)
        and evaluation_lock_sha == summary.get("evaluation_lock_sha256")
        and _evaluation_lock_ok(
            evaluation_lock,
            config,
            static_lock_sha=static_sha,
            preflight_binding=binding,
            preflight_summary=preflight_summary,
        ),
        "evaluation_lock_recomputed",
        checks,
        errors,
    )
    _check(
        summary.get("access_contract", {}).get("crypto_module_imported") is False
        and summary.get("access_contract", {}).get("ascon_accessed") is False
        and summary.get("access_contract", {}).get("present_accessed") is False
        and summary.get("access_contract", {}).get("evaluation_started") is False
        and summary.get("access_contract", {}).get(
            "release_authorized_for_future_process"
        )
        is True
        and summary.get("performance_evidence") is False,
        "seal_before_holdout_release",
        checks,
        errors,
    )
    _check(
        static_lock.get("crypto_registry", {}).get("sha256")
        == config["holdout_access"]["registry_sha256"]
        and config["holdout_access"]["family_exclusion_label"] == HOLDOUT_LABEL,
        "seal_registry_and_exclusion_label_bound",
        checks,
        errors,
    )
    return checks


def _derived_seed(*parts: object) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _scheduler_seed(
    config: Mapping[str, Any], family: str, output_bit: int, solver_seed: int
) -> int:
    return _derived_seed(
        "e5-scheduler-v1",
        int(config["search"]["scheduler_seed_base"]),
        family,
        int(output_bit),
        int(solver_seed),
    )


def _arm_contract(config: Mapping[str, Any], arm: str) -> Mapping[str, Any]:
    by_name = {str(item["name"]): item for item in config["evaluation"]["arms"]}
    return by_name[arm]


def _scheduler_config(
    config: Mapping[str, Any],
    arm: str,
    *,
    family: str,
    output_bit: int,
    solver_seed: int,
) -> DiversitySchedulerConfig:
    search = config["search"]
    qaoa = config["qaoa"]
    arm_spec = _arm_contract(config, arm)
    return DiversitySchedulerConfig(
        method="qaoa" if arm_spec["scheduler"] == "qaoa" else "greedy",
        budget_requested=int(search["scheduler_budget"]),
        pool_size=int(search["scheduler_pool_size"]),
        min_candidates=int(search["scheduler_min_candidates"]),
        max_depth=0,
        redundancy_weight=float(search["redundancy_weight"]),
        redundancy_alpha=float(search["redundancy_alpha"]),
        utility_clip=float(search["utility_clip"]),
        exact_max_candidates=12,
        seed=_scheduler_seed(config, family, output_bit, solver_seed),
        qaoa_mode="shot",
        qaoa_p=int(qaoa["p"]),
        qaoa_shots=int(qaoa["shots"]),
        qaoa_noise_bitflip_probability=float(qaoa["measurement_bitflip_probability"]),
        qaoa_optimizer_restarts=int(qaoa["optimizer_restarts"]),
        qaoa_optimizer_steps=int(qaoa["optimizer_steps"]),
    )


def _load_and_verify_holdouts(config: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    """Release the two families only after the caller has passed every gate."""

    # Local import is an intentional access-control boundary.
    from src.benchmarks.crypto_oracles import (  # noqa: PLC0415
        CRYPTO_HOLDOUT_EXCLUSION_LABEL,
        get_crypto_holdout_oracle_coordinates,
        reconstruct_substitution_value,
        verify_crypto_holdout_oracle_family,
    )

    label = str(config["holdout_access"]["family_exclusion_label"])
    if label != HOLDOUT_LABEL or CRYPTO_HOLDOUT_EXCLUSION_LABEL != HOLDOUT_LABEL:
        raise ValueError("holdout exclusion label differs from the sealed contract")
    if sha256_file(PROJECT_ROOT / config["holdout_access"]["registry_path"]) != config[
        "holdout_access"
    ]["registry_sha256"]:
        raise ValueError("holdout registry differs from the sealed SHA")

    loaded: dict[str, tuple[Any, ...]] = {}
    # Dict insertion order and this loop are both ASCON then PRESENT.
    for family in config["evaluation"]["family_order"]:
        coordinates = tuple(
            get_crypto_holdout_oracle_coordinates(
                family, family_exclusion_label=label
            )
        )
        verify_crypto_holdout_oracle_family(
            family,
            coordinates=coordinates,
            family_exclusion_label=label,
        )
        frozen = HOLDOUT_SPECS[family]
        configured = config["holdout_access"]["families"][family]
        if (
            configured["input_width"] != frozen["input_width"]
            or configured["output_width"] != frozen["output_width"]
            or configured["role"] != frozen["role"]
            or configured["coordinates"] != list(range(frozen["output_width"]))
            or configured["vector_truth_table_sha256"] != frozen["vector_sha256"]
            or configured["coordinate_truth_table_sha256"]
            != list(frozen["coordinate_sha256"])
            or len(coordinates) != frozen["output_width"]
        ):
            raise ValueError(f"{family} sealed family contract mismatch")
        for bit, coordinate in enumerate(coordinates):
            expected_sha = hashlib.sha256(
                coordinate.canonical_truth_table_bytes()
            ).hexdigest()
            if (
                coordinate.output_bit != bit
                or coordinate.input_width != frozen["input_width"]
                or coordinate.output_width != frozen["output_width"]
                or coordinate.truth_table_sha256 != expected_sha
                or expected_sha != frozen["coordinate_sha256"][bit]
                or coordinate.training_access_allowed is not False
                or coordinate.family_exclusion_label != HOLDOUT_LABEL
            ):
                raise ValueError(f"{family}[{bit}] coordinate contract mismatch")
        outputs = [
            reconstruct_substitution_value(coordinates, x)
            for x in range(1 << int(frozen["input_width"]))
        ]
        if hashlib.sha256(bytes(outputs)).hexdigest() != frozen["vector_sha256"]:
            raise ValueError(f"{family} complete vector-table SHA mismatch")
        if len(set(outputs)) != len(outputs):
            raise ValueError(f"{family} forward S-box is not bijective")
        loaded[family] = coordinates
    return loaded


def _policy_stats_from_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("learned_policy_stats", row.get("policy_stats", {}))
    return value if isinstance(value, Mapping) else {}


def _value_stats_from_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("learned_value_stats", row.get("value_stats", {}))
    return value if isinstance(value, Mapping) else {}


def _rebuild_search_row(
    row: Mapping[str, Any],
    config: Mapping[str, Any],
    weights: FrozenExecutionPenaltyWeights,
    checkpoint: Path,
    coordinate: Any,
) -> bool:
    try:
        family = str(row["family"])
        bit = int(row["output_bit"])
        solver_seed = int(row["solver_seed"])
        arm = str(row["arm"])
        arm_spec = _arm_contract(config, arm)
        terms = frozenset(anf_monomials(coordinate.boolean_function))
        search_config = _search_config(config)
        structural_actions = candidate_actions(
            terms, 0, 0, search_config, neural_scorer=None
        )
        root_action_count = len(structural_actions)
        root_eligibility = (
            "schedulable" if root_action_count > 0 else "degenerate_direct_root"
        )
        scheduler_config = _scheduler_config(
            config,
            arm,
            family=family,
            output_bit=bit,
            solver_seed=solver_seed,
        )
        if (
            row.get("record_type") != "e5_external_family_trial"
            or row.get("phase") != "evaluate"
            or row.get("arm_spec") != dict(arm_spec)
            or row.get("same_pool_group") != arm_spec["same_pool_group"]
            or row.get("search_config") != asdict(search_config)
            or row.get("scheduler_config") != scheduler_config.to_dict()
            or row.get("simulations") != int(config["search"]["simulations"])
            or row.get("scheduler_seed") != scheduler_config.seed
            or row.get("root_action_count") != root_action_count
            or row.get("root_eligibility") != root_eligibility
            or row.get("root_structural_action_signatures")
            != [_action_signature(action) for action in structural_actions]
        ):
            return False

        scorer: FoundationScorer | None = None
        policy: TermThresholdPolicyScorer | None = None
        value_estimator: LearnedValueEstimator | None = None
        if arm_spec["learned_policy"]:
            scorer = FoundationScorer.from_checkpoint(checkpoint)
            if any(
                parameter.device.type != "cpu" for parameter in scorer.model.parameters()
            ):
                return False
            policy = TermThresholdPolicyScorer(
                scorer, int(config["search"]["policy_term_threshold"])
            )
            value_estimator = LearnedValueEstimator(scorer, search_config)
        adjuster = None
        if arm_spec["execution_aware"]:
            adjuster = make_root_rollout_execution_utility_adjuster(
                n_inputs=int(coordinate.input_width),
                search_config=search_config,
                profile_spec=_profile_spec(config),
                penalty_weights=weights,
                expected_profile_sha256=_profile_spec(config).profile_sha256,
                execution_n_qubits=int(config["native_profile"]["frozen_n_qubits"]),
            )
        solver = NeuralMCTSSolver(
            config=search_config,
            simulations=int(config["search"]["simulations"]),
            seed=solver_seed,
            neural_scorer=policy,
            value_estimator=value_estimator,
            rollout_scorer=None,
            scheduler_config=scheduler_config,
            execution_utility_adjuster=adjuster,
        )
        plan = solver.solve(terms)
        root = solver.nodes.get(StateKey(terms, 0, 0))
        if root is None or len(root.actions) != root_action_count:
            return False
        if root_eligibility == "degenerate_direct_root":
            if root.scheduler_decision is not None or root.admitted_indices is not None:
                return False
            decision = None
            diagnostics = {
                "root_eligibility": root_eligibility,
                "status": "not_invoked_degenerate_direct_root",
                "node_id": NeuralMCTSSolver._state_id(StateKey(terms, 0, 0)),
                "candidate_count": 0,
                "utilities": [],
                "raw_utilities": [],
                "adjusted_utilities": [],
                "execution_feedback": {
                    "enabled": False,
                    "reason": "degenerate_direct_root",
                },
                "qaoa_attempted": False,
                "qaoa_succeeded": False,
                "qaoa_repaired": False,
                "qaoa_fallback": False,
                "not_invoked_reason": "root_action_count_zero",
            }
            width = 0
            actions: tuple[FactorAction, ...] = ()
            raw: list[float] = []
            adjusted: list[float] = []
            redundancy: list[list[float]] = []
            if PlanTrace.from_plan(plan).to_dict() != PlanTrace.from_plan(
                direct_plan(terms, 0, 0, search_config)
            ).to_dict():
                return False
        else:
            if root.scheduler_decision is None or root.admitted_indices is None:
                return False
            decision = root.scheduler_decision
            diagnostics = dict(decision.diagnostics)
            diagnostics["root_eligibility"] = root_eligibility
            width = int(diagnostics["candidate_count"])
            actions = tuple(root.actions[:width])
            raw = [
                float(value)
                for value in diagnostics.get("raw_utilities", diagnostics["utilities"])
            ]
            adjusted = [
                float(value)
                for value in diagnostics.get(
                    "adjusted_utilities", diagnostics["utilities"]
                )
            ]
            redundancy = [
                [float(value) for value in values]
                for values in action_redundancy_matrix(
                    actions, alpha=scheduler_config.redundancy_alpha
                )
            ]
        expected_pool = {
            "schema_version": "xa.e5-external-family-candidate-pool.v1",
            "family": family,
            "output_bit": bit,
            "truth_table_sha256": coordinate.truth_table_sha256,
            "node_id": diagnostics["node_id"],
            "candidate_count": width,
            "budget_requested": int(config["search"]["scheduler_budget"]),
            "budget_effective": min(
                int(config["search"]["scheduler_budget"]), width
            ),
            "action_signatures": [_action_signature(action) for action in actions],
            "utilities": raw,
            "redundancy": redundancy,
            "redundancy_weight": float(config["search"]["redundancy_weight"]),
            "redundancy_alpha": float(config["search"]["redundancy_alpha"]),
        }
        pool = row["candidate_pool"]
        if (
            pool != expected_pool
            or sha256_bytes(canonical_json_bytes(pool))
            != row.get("candidate_pool_sha256")
            or row.get("raw_scheduler_utilities") != raw
            or row.get("adjusted_scheduler_utilities") != adjusted
        ):
            return False

        stored_scheduler = row["scheduler"]
        selected = (
            [int(value) for value in decision.selected_indices]
            if decision is not None
            else []
        )
        selected_set = set(selected)
        visits = [root.stats[index].visits for index in range(len(root.actions))]
        expected_scheduler = {
            "method": scheduler_config.method,
            "qaoa_mode": (
                scheduler_config.qaoa_mode if arm.endswith("qaoa_shot") else None
            ),
            "candidate_count": width,
            "budget_requested": int(config["search"]["scheduler_budget"]),
            "budget_effective": min(
                int(config["search"]["scheduler_budget"]), width
            ),
            "selected_indices": selected,
            "selected_action_visits": [visits[index] for index in selected],
            "selected_action_visits_total": sum(visits[index] for index in selected),
            "excluded_action_visits_total": sum(
                count
                for index, count in enumerate(visits)
                if index not in selected_set
            ),
            "status": diagnostics.get("status"),
            "objective": diagnostics.get(
                "effective_objective", diagnostics.get("objective")
            ),
            "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
            "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
            "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
            "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
            "diagnostics": diagnostics,
        }
        if stored_scheduler != expected_scheduler:
            return False

        if root_eligibility == "degenerate_direct_root":
            expected_execution_status = "not_invoked_degenerate"
        elif not arm.endswith("qaoa_shot"):
            expected_execution_status = "classical_invoked"
        elif diagnostics.get("status") == "qaoa_not_invoked":
            expected_execution_status = "not_invoked_small_pool"
        else:
            if diagnostics.get("qaoa_fallback"):
                expected_execution_status = "fallback"
            elif diagnostics.get("qaoa_repaired"):
                expected_execution_status = "direct_repaired"
            elif diagnostics.get("qaoa_succeeded"):
                expected_execution_status = "direct_unrepaired"
            else:
                expected_execution_status = "invalid"
        if (
            expected_execution_status not in EXECUTION_STATUSES
            or row.get("execution_status") != expected_execution_status
            or row.get("qaoa_execution") != expected_execution_status
        ):
            return False

        if root_eligibility == "degenerate_direct_root":
            if (
                row.get("execution_feedback")
                != {"enabled": False, "reason": "degenerate_direct_root"}
                or raw
                or adjusted
            ):
                return False
        elif arm_spec["execution_aware"]:
            feedback = diagnostics.get("execution_feedback", {})
            if (
                row.get("execution_feedback") != feedback
                or feedback.get("model_metadata", {}).get("n_inputs")
                != coordinate.input_width
                or feedback.get("model_metadata", {}).get("execution_n_qubits") != 10
                or feedback.get("diagnostics", {}).get("heldout_noisy_outcome_used")
                is not False
            ):
                return False
        elif (
            adjusted != raw
            or row.get("execution_feedback")
            != diagnostics.get("execution_feedback", {})
        ):
            return False

        policy_record = _policy_stats_from_row(row)
        value_record = _value_stats_from_row(row)
        if policy is None:
            if (
                row.get("checkpoint_sha256") is not None
                or row.get("learned_policy_enabled") is not False
                or row.get("learned_policy_active_at_root") is not False
                or row.get("learned_value_enabled") is not False
                or row.get("learned_value_active") is not False
                or any(int(value or 0) != 0 for value in policy_record.values())
                or any(int(value or 0) != 0 for value in value_record.values())
                or row.get("learned_policy_stats")
                != {"learned_states": 0, "gated_states": 0}
                or row.get("learned_value_stats") != ValueStats().as_dict()
            ):
                return False
        else:
            expected_policy = {
                "learned_states": policy.learned_states,
                "gated_states": policy.gated_states,
            }
            expected_value = value_estimator.stats.as_dict() if value_estimator else {}
            expected_policy_active = bool(
                root_eligibility == "schedulable" and policy.learned_states > 0
            )
            expected_value_active = bool(
                root_eligibility == "schedulable"
                and expected_value.get("value_calls", 0) > 0
            )
            if (
                row.get("checkpoint_sha256")
                != config["foundation_v4"]["checkpoint_sha256"]
                or row.get("learned_policy_enabled") is not True
                or row.get("learned_policy_active_at_root")
                is not expected_policy_active
                or row.get("learned_value_enabled") is not True
                or row.get("learned_value_active") is not expected_value_active
                or any(policy_record.get(key) != value for key, value in expected_policy.items())
                or any(value_record.get(key) != value for key, value in expected_value.items())
                or row.get("learned_policy_stats") != expected_policy
                or row.get("learned_value_stats") != expected_value
                or row.get("policy_cache_hits") != scorer.cache_hits
                or row.get("policy_cache_misses") != scorer.cache_misses
                or (
                    root_eligibility == "schedulable"
                    and (
                        policy.learned_states <= 0
                        or expected_value.get("value_calls", 0) <= 0
                    )
                )
            ):
                return False

        trace = PlanTrace.from_plan(plan).to_dict()
        if (
            canonical_json_bytes(trace) != canonical_json_bytes(row.get("plan_trace"))
            or row.get("plan_trace_sha256")
            != sha256_bytes(canonical_json_bytes(trace))
            or asdict(plan.cost) != row.get("logical_cost")
            or plan.score(PAPER_WEIGHTS) != row.get("logical_resource_score")
            or root.visits != row.get("root_visits")
            or len(solver.nodes) != row.get("search_nodes")
            or not math.isfinite(float(row.get("scheduler_wall_s", -1.0)))
            or float(row.get("scheduler_wall_s", -1.0)) < 0.0
            or not math.isfinite(float(row.get("solve_elapsed_s", -1.0)))
            or float(row.get("solve_elapsed_s", -1.0)) < 0.0
        ):
            return False
        allocated = min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla)
        circuit = emit_plan_to_circuit(plan, coordinate.input_width, allocated)
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if circuit.n_qubits < frozen_n:
            padded = QuantumCircuit(frozen_n)
            padded.gates = list(circuit.gates)
            circuit = padded
        logical = export_openqasm3(circuit)
        return bool(
            circuit_to_logical_ir(circuit)
            == circuit_to_logical_ir(_circuit_from_ir(row["logical_circuit_ir"]))
            and row.get("allocated_factor_ancilla") == allocated
            and logical.qasm == row.get("logical_qasm3")
            and sha256_bytes(logical.qasm.encode("utf-8"))
            == row.get("logical_qasm3_sha256")
        )
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return False


def _native_record_matches(row: Mapping[str, Any], compilation: Any) -> bool:
    try:
        native = row["native"]
        diagnostics = compilation.diagnostics
        qasm = native_to_openqasm3(compilation)
        expected = {
            "profile_name": compilation.profile.name,
            "profile_sha256": native["profile_sha256"],
            "topology_family": compilation.profile.topology_family,
            "n_qubits": compilation.profile.n_qubits,
            "coupling_edges": [list(edge) for edge in compilation.profile.coupling_edges],
            **asdict(diagnostics),
            "native_gate_set": ["rz", "sx", "x", "cx"],
            "native_gate_set_ok": all(
                gate.name in {"rz", "sx", "x", "cx"}
                for gate in compilation.native_gates
            ),
            "coupling_ok": all(
                tuple(sorted(gate.qubits)) in compilation.profile.coupling_edges
                for gate in compilation.native_gates
                if gate.name == "cx"
            ),
            "native_qasm3": qasm,
            "native_qasm3_sha256": sha256_bytes(qasm.encode("utf-8")),
            "hardware_execution": False,
            "noisy_simulation": False,
        }
        return bool(
            native == expected
            and row.get("native_record_sha256")
            == sha256_bytes(canonical_json_bytes(expected))
        )
    except (KeyError, TypeError, ValueError):
        return False


def _verify_reversible_oracle_all_targets(circuit: QuantumCircuit, coordinate: Any) -> bool:
    for x in range(1 << int(coordinate.input_width)):
        prefix = [(x >> bit) & 1 for bit in range(int(coordinate.input_width))]
        for target_input in (0, 1):
            bits = prefix + [target_input]
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
            width = int(coordinate.input_width)
            if (
                bits[:width] != prefix
                or bits[width] != (target_input ^ int(coordinate.evaluate(x)))
                or any(bits[width + 1 :])
            ):
                return False
    return True


def _trial_semantics_native_ok(
    row: Mapping[str, Any], config: Mapping[str, Any], coordinate: Any
) -> bool:
    try:
        if (
            row.get("schema_version") != EVALUATION_ROW_SCHEMA
            or row.get("record_type") != "e5_external_family_trial"
            or row.get("phase") != "evaluate"
            or row.get("family") != coordinate.family
            or row.get("family_role")
            != config["holdout_access"]["families"][coordinate.family]["role"]
            or row.get("operation") != coordinate.operation
            or row.get("output_bit") != coordinate.output_bit
            or row.get("input_width") != coordinate.input_width
            or row.get("output_width") != coordinate.output_width
            or row.get("bit_order") != coordinate.bit_order
            or row.get("source") != coordinate.source
            or row.get("provenance") != coordinate.provenance
            or row.get("vector_truth_table_sha256")
            != coordinate.vector_truth_table_sha256
            or row.get("truth_table_sha256") != coordinate.truth_table_sha256
            or int(str(row["truth_table_hex"]), 16)
            != int(coordinate.boolean_function.truth_table)
            or row.get("family_exclusion_label") != HOLDOUT_LABEL
            or row.get("benchmark_partition") != "external_crypto_family_holdout"
            or row.get("training_access_allowed") is not False
        ):
            return False
        plan = _plan_from_trace(row["plan_trace"])
        terms = frozenset(anf_monomials(coordinate.boolean_function))
        if (
            row.get("anf_term_count") != len(terms)
            or not verify_plan_anf(plan).ok
            or plan.terms != terms
            or asdict(plan.cost) != row["logical_cost"]
            or row.get("plan_trace_sha256")
            != sha256_bytes(canonical_json_bytes(row["plan_trace"]))
        ):
            return False
        circuit = emit_plan_to_circuit(
            plan, coordinate.input_width, int(row["allocated_factor_ancilla"])
        )
        frozen_n = int(config["native_profile"]["frozen_n_qubits"])
        if circuit.n_qubits < frozen_n:
            padded = QuantumCircuit(frozen_n)
            padded.gates = list(circuit.gates)
            circuit = padded
        expected_logical = export_openqasm3(circuit)
        expected_ir = {
            "n_qubits": expected_logical.logical_ir.n_qubits,
            "gate_mode": expected_logical.logical_ir.gate_mode,
            "gates": [
                {
                    "gate_type": gate.gate_type,
                    "controls": list(gate.controls),
                    "target": gate.target,
                }
                for gate in expected_logical.logical_ir.gates
            ],
        }
        stored = _circuit_from_ir(row["logical_circuit_ir"])
        if (
            row.get("logical_circuit_ir") != expected_ir
            or circuit_to_logical_ir(circuit) != circuit_to_logical_ir(stored)
            or not verify_circuit_anf(stored, coordinate.input_width, terms).ok
            or not verify_oracle(stored, coordinate.boolean_function)
            or not _verify_reversible_oracle_all_targets(stored, coordinate)
            or row.get("plan_anf_ok") is not True
            or row.get("circuit_anf_ok") is not True
            or row.get("oracle_ok") is not True
            or row.get("reversible_oracle_all_targets_ok") is not True
        ):
            return False
        logical = export_openqasm3(stored)
        if (
            row.get("logical_qasm3") != logical.qasm
            or row.get("logical_qasm3_sha256")
            != sha256_bytes(logical.qasm.encode("utf-8"))
            or row.get("logical_gate_count") != len(stored.gates)
        ):
            return False
        profile_spec = _profile_spec(config)
        profile = profile_spec.build(frozen_n)
        compilation = compile_superconducting(stored, profile)
        frozen_profile, profile_sha = _frozen_profile(config)
        endpoint = {
            "metric": "native.two_qubit_gate_count",
            "value": int(compilation.diagnostics.two_qubit_gate_count),
            "direction": "lower_is_better",
        }
        return bool(
            stored.n_qubits == frozen_n == 10
            and row.get("logical_n_qubits") == frozen_n
            and row.get("profile_spec_sha256") == profile_spec.profile_sha256
            and row.get("profile_sha256") == profile_sha
            and row.get("frozen_profile") == frozen_profile
            and row.get("native", {}).get("profile_sha256") == profile_sha
            and row.get("native", {}).get("n_qubits") == frozen_n
            and _native_record_matches(row, compilation)
            and row.get("primary_endpoint") == endpoint
            and row.get("primary_endpoint_sha256")
            == sha256_bytes(canonical_json_bytes(endpoint))
            and row.get("noisy_endpoint") is None
            and not row.get("noisy_endpoints")
            and row.get("hardware_execution") is False
            and row.get("noisy_diagnostic_run") is False
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


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
        sorted_values[lower] * (1.0 - fraction)
        + sorted_values[upper] * fraction
    )


def _cluster_comparison(
    rows: Sequence[dict[str, Any]],
    config: Mapping[str, Any],
    *,
    family: str,
    reference_arm: str,
    candidate_arm: str,
    direct_unrepaired_only: bool = False,
    schedulable_only: bool = False,
) -> dict[str, Any]:
    bits = [int(bit) for bit in config["holdout_access"]["families"][family]["coordinates"]]
    seeds = [int(seed) for seed in config["evaluation"]["solver_seeds"]]
    index: dict[tuple[int, int, str], Mapping[str, Any]] = {}
    for row in rows:
        if row.get("family") != family or row.get("arm") not in {
            reference_arm,
            candidate_arm,
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
        for arm in (reference_arm, candidate_arm)
    }
    if set(index) != expected:
        raise ValueError(f"incomplete paired matrix for {family}")
    eligible_bits: list[int] = []
    excluded_bits: list[int] = []
    excluded_reasons: list[dict[str, Any]] = []
    for bit in bits:
        bit_rows = [
            index[(bit, seed, arm)]
            for seed in seeds
            for arm in (reference_arm, candidate_arm)
        ]
        schedulable = all(
            row.get("root_eligibility") == "schedulable" for row in bit_rows
        )
        direct = all(
            index[(bit, seed, reference_arm)].get("execution_status")
            == "direct_unrepaired"
            and index[(bit, seed, candidate_arm)].get("execution_status")
            == "direct_unrepaired"
            for seed in seeds
        )
        reasons: list[str] = []
        if schedulable_only and not schedulable:
            reasons.append("excluded_from_schedulable_only_secondary")
        if direct_unrepaired_only and not direct:
            statuses = sorted(
                {str(row.get("execution_status")) for row in bit_rows}
            )
            reasons.append(
                "not_both_arms_direct_unrepaired_all_seeds:" + ",".join(statuses)
            )
        if reasons:
            excluded_bits.append(bit)
            excluded_reasons.append({"output_bit": bit, "reasons": reasons})
        else:
            eligible_bits.append(bit)
    clusters = []
    for bit in eligible_bits:
        seed_differences = [
            float(index[(bit, seed, candidate_arm)]["primary_endpoint"]["value"])
            - float(index[(bit, seed, reference_arm)]["primary_endpoint"]["value"])
            for seed in seeds
        ]
        clusters.append(
            {
                "family": family,
                "output_bit": bit,
                "solver_seed_count": len(seeds),
                "seed_differences": seed_differences,
                "cluster_mean_difference": statistics.mean(seed_differences),
            }
        )
    effects = [float(record["cluster_mean_difference"]) for record in clusters]
    if not effects:
        return {
            "family": family,
            "metric": "native.two_qubit_gate_count",
            "comparison": f"{candidate_arm}-minus-{reference_arm}",
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
    nonzero_effects = [
        effect for effect in effects if not math.isclose(effect, 0.0, abs_tol=1e-12)
    ]
    sign_means = [
        statistics.mean(
            [sign * effect for sign, effect in zip(signs, nonzero_effects)]
            + [0.0] * (len(effects) - len(nonzero_effects))
        )
        for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero_effects))
    ]
    exact_p = sum(
        abs(item) >= abs(observed) - 1e-12 for item in sign_means
    ) / len(sign_means)
    bootstrap_count = int(config["statistics"]["bootstrap_resamples"])
    seed = _derived_seed(
        "e5-cluster-bootstrap-v1",
        config["statistics"]["bootstrap_seed"],
        family,
        reference_arm,
        candidate_arm,
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
        "comparison": f"{candidate_arm}-minus-{reference_arm}",
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
        "cluster_effects": clusters,
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
            "ties": sum(
                math.isclose(effect, 0.0, abs_tol=1e-12) for effect in effects
            ),
        },
        "nonzero_cluster_count": len(nonzero_effects),
        "zero_cluster_count": len(effects) - len(nonzero_effects),
        "exact_sign_flip_permutations": 1 << len(nonzero_effects),
        "effective_exact_sign_flip_permutations": 1 << len(nonzero_effects),
        "minimum_attainable_two_sided_sign_flip_p": (
            1.0
            if not nonzero_effects
            else min(1.0, 2.0 / (1 << len(nonzero_effects)))
        ),
        "exact_two_sided_sign_flip_p": exact_p,
        "inference_available": True,
        "claim_rule": (
            "effect_estimate_only_no_binary_superiority_due_five_clusters"
            if family == "ASCON" and not direct_unrepaired_only
            else "secondary_or_sensitivity_effect_estimate_only"
        ),
    }


def _all_comparisons(
    rows: Sequence[dict[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    primary = _cluster_comparison(
        rows,
        config,
        family="ASCON",
        reference_arm="v4_historical_qaoa_shot",
        candidate_arm="v4_execution_aware_qaoa_shot",
    )
    secondary = {
        "present_qaoa_execution_aware": _cluster_comparison(
            rows,
            config,
            family="PRESENT",
            reference_arm="v4_historical_qaoa_shot",
            candidate_arm="v4_execution_aware_qaoa_shot",
            schedulable_only=True,
        ),
        "ascon_greedy_execution_aware": _cluster_comparison(
            rows,
            config,
            family="ASCON",
            reference_arm="v4_historical_greedy",
            candidate_arm="v4_execution_aware_greedy",
            schedulable_only=True,
        ),
        "ascon_v4_model_reference": _cluster_comparison(
            rows,
            config,
            family="ASCON",
            reference_arm="heuristic_historical_greedy",
            candidate_arm="v4_historical_greedy",
            schedulable_only=True,
        ),
        "present_v4_model_reference": _cluster_comparison(
            rows,
            config,
            family="PRESENT",
            reference_arm="heuristic_historical_greedy",
            candidate_arm="v4_historical_greedy",
            schedulable_only=True,
        ),
    }
    sensitivity = _cluster_comparison(
        rows,
        config,
        family="ASCON",
        reference_arm="v4_historical_qaoa_shot",
        candidate_arm="v4_execution_aware_qaoa_shot",
        direct_unrepaired_only=True,
    )
    return {"primary": primary, "secondary": secondary, "direct_sensitivity": sensitivity}


def _v4_pool_fairness(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        if row.get("arm") in V4_ARMS and row.get("root_eligibility") == "schedulable":
            groups.setdefault(
                (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])),
                [],
            ).append(row)
    records: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        arms = {str(row["arm"]) for row in group}
        pool_shas = {str(row["candidate_pool_sha256"]) for row in group}
        raw_shas = {
            sha256_bytes(canonical_json_bytes(row["raw_scheduler_utilities"]))
            for row in group
        }
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
                "four_arms_present": arms == set(V4_ARMS),
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
    family_counts = {
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
        "family_schedulable_group_counts": family_counts,
        "each_family_has_schedulable_activity": all(
            count > 0 for count in family_counts.values()
        ),
        "groups": records,
        "all": len(records) == expected_groups
        and all(count > 0 for count in family_counts.values())
        and all(
            record["four_arms_present"]
            and record["same_candidate_pool"]
            and record["same_raw_utility"]
            and record["same_simulations_k_budget_and_pool_width"]
            for record in records
        ),
        "heuristic_reference_excluded_from_same_pool_claim": True,
    }


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
        action_hashes = {
            sha256_bytes(canonical_json_bytes(row["root_structural_action_signatures"]))
            for row in group
        }
        eligibilities = {str(row["root_eligibility"]) for row in group}
        count = next(iter(counts)) if len(counts) == 1 else -1
        expected = "schedulable" if count > 0 else "degenerate_direct_root"
        degenerate = expected == "degenerate_direct_root"
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
                "five_arms_present": {str(row["arm"]) for row in group}
                == set(FIVE_ARMS),
                "arm_independent_root_action_count": len(counts) == 1,
                "arm_independent_root_structural_actions": len(action_hashes) == 1,
                "root_action_count": count,
                "root_eligibility": expected,
                "eligibility_consistent": eligibilities == {expected},
                "degenerate_five_arm_plan_qasm_native_endpoint_identical": (
                    degenerate_identity
                ),
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
            record["root_eligibility"] == "degenerate_direct_root"
            for record in records
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


def _linked_seal(
    current_root: Path, binding: Mapping[str, Any]
) -> tuple[bool, Path | None, dict[str, Any]]:
    try:
        hint = binding.get("bundle") or binding.get("bundle_hint")
        root = _resolve_link(current_root, hint)
        if root == current_root:
            return False, None, {}
        report = verify_e5_external_crypto_holdout_bundle(
            root, _allow_links=True, _expected_phase="seal"
        )
        summary = _read_json(root / "summary.json")
        ok = bool(
            report.get("ok") is True
            and binding.get("summary_sha256") == sha256_file(root / "summary.json")
            and binding.get("evaluation_lock_sha256")
            == summary.get("evaluation_lock_sha256")
            and binding.get("static_lock_sha256") == summary.get("static_lock_sha256")
        )
        return ok, root, summary
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False, None, {}


def _verify_evaluate(
    root: Path,
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        config = _effective_config(run)
    except (KeyError, TypeError, ValueError, OSError):
        return {"effective_config_present": False}
    config_sha = sha256_bytes(canonical_json_bytes(config))

    # Gate block: do not import crypto_oracles unless every sealed dependency is
    # independently proven in this process.
    static_ok, _, static_sha = _verify_static_lock(config)
    amendment_ok = _verify_amendment_ledger(config)
    v4_ok, v4 = _verify_v4_gate(config)
    bindings = summary.get("bindings", {})
    seal_binding = bindings.get("seal", summary.get("seal_binding", {}))
    seal_ok, seal_root, seal_summary = _linked_seal(root, seal_binding)
    gate_ok = bool(
        static_ok
        and amendment_ok
        and v4_ok
        and seal_ok
        and seal_summary.get("static_lock_sha256") == static_sha
        and seal_binding.get("evaluation_lock_sha256")
        == seal_summary.get("evaluation_lock_sha256")
        and bindings.get("source_tree_sha256") == _source_tree_sha256()
        == run.get("source", {}).get("source_tree_sha256")
        == seal_summary.get("source_tree_sha256")
        == seal_summary.get("evaluation_lock", {}).get("source_tree_sha256")
        and bindings.get("config_sha256") == config_sha
        and bindings.get("checkpoint_sha256")
        == config["foundation_v4"]["checkpoint_sha256"]
        and bindings.get("model_card_sha256")
        == config["foundation_v4"]["model_card_sha256"]
        and bindings.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and v4.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(v4.get("compute_runtime"), config)
        and seal_summary.get("compute_contract") == config["compute_contract"]
        and seal_summary.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(seal_summary.get("compute_runtime"), config)
        and seal_summary.get("evaluation_lock", {}).get("compute_contract")
        == config["compute_contract"]
        and seal_summary.get("evaluation_lock", {}).get("compute_contract_sha256")
        == _compute_contract_sha256(config)
    )
    _check(gate_ok, "evaluate_all_pre_release_gates", checks, errors)
    if not gate_ok:
        checks.update(
            {
                "labelled_holdout_loader_verified": False,
                "complete_five_arm_matrix": False,
                "independent_search_plan_native_reconstruction": False,
                "family_bit_cluster_statistics_recomputed": False,
            }
        )
        return checks

    try:
        coordinates = _load_and_verify_holdouts(config)
        holdouts_ok = True
    except (KeyError, TypeError, ValueError, OSError, RuntimeError, ImportError):
        coordinates = {}
        holdouts_ok = False
    _check(holdouts_ok, "labelled_holdout_loader_verified", checks, errors)
    if not holdouts_ok:
        checks.update(
            {
                "complete_five_arm_matrix": False,
                "independent_search_plan_native_reconstruction": False,
                "family_bit_cluster_statistics_recomputed": False,
            }
        )
        return checks

    release = summary.get("holdout_release", {})
    _check(
        release.get("module") == "src.benchmarks.crypto_oracles"
        and release.get("registry_sha256")
        == config["holdout_access"]["registry_sha256"]
        and release.get("release_phase") == "evaluate"
        and release.get("family_order") == ["ASCON", "PRESENT"]
        and all(
            release.get("families", {}).get(family, {}).get("coordinate_count")
            == HOLDOUT_SPECS[family]["output_width"]
            and release.get("families", {}).get(family, {}).get(
                "vector_truth_table_sha256"
            )
            == HOLDOUT_SPECS[family]["vector_sha256"]
            and release.get("families", {}).get(family, {}).get(
                "coordinate_truth_table_sha256"
            )
            == list(HOLDOUT_SPECS[family]["coordinate_sha256"])
            and release.get("families", {}).get(family, {}).get(
                "training_access_allowed"
            )
            is False
            for family in ("ASCON", "PRESENT")
        ),
        "holdout_release_record_recomputed",
        checks,
        errors,
    )

    expected_order = [
        (family, bit, seed, arm)
        for family in config["evaluation"]["family_order"]
        for bit in config["holdout_access"]["families"][family]["coordinates"]
        for seed in config["evaluation"]["solver_seeds"]
        for arm in FIVE_ARMS
    ]
    actual_order = [
        (row.get("family"), row.get("output_bit"), row.get("solver_seed"), row.get("arm"))
        for row in rows
    ]
    expected_matrix = set(expected_order)
    actual_matrix = set(actual_order)
    matrix_ok = bool(
        len(rows) == len(expected_order) == 90
        and actual_matrix == expected_matrix
        and actual_order == expected_order
        and all(row.get("schema_version") == EVALUATION_ROW_SCHEMA for row in rows)
        and all(row.get("run_id") == run.get("run_id") for row in rows)
    )
    _check(
        matrix_ok,
        "complete_five_arm_matrix",
        checks,
        errors,
    )
    if not matrix_ok:
        checks.update(
            {
                "v4_four_arm_same_pool_raw_utility_budget": False,
                "heuristic_reference_equal_compute_budget": False,
                "sealed_preflight_weights_bound": False,
                "independent_search_plan_native_reconstruction": False,
                "learned_policy_value_active_in_all_v4_arms": False,
                "scheduler_selection_and_qaoa_itt": False,
                "family_bit_cluster_statistics_recomputed": False,
            }
        )
        return checks

    groups: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(
            (str(row["family"]), int(row["output_bit"]), int(row["solver_seed"])), []
        ).append(row)
    fairness = _v4_pool_fairness(rows)
    eligibility_identity = _eligibility_and_degenerate_identity(rows)
    _check(
        fairness.get("all") is True
        and fairness.get("each_family_has_schedulable_activity") is True
        and summary.get("v4_four_arm_fairness") == fairness,
        "schedulable_v4_four_arm_same_pool_raw_utility_budget",
        checks,
        errors,
    )
    _check(
        eligibility_identity.get("all") is True
        and summary.get("root_eligibility_and_degenerate_identity")
        == eligibility_identity,
        "arm_independent_root_eligibility_and_degenerate_identity",
        checks,
        errors,
    )
    heuristic_budget = all(
        (
            by_arm["heuristic_historical_greedy"].get("simulations")
            == by_arm["v4_historical_greedy"].get("simulations")
            and by_arm["heuristic_historical_greedy"].get("search_config", {}).get(
                "candidate_top_k"
            )
            == by_arm["v4_historical_greedy"].get("search_config", {}).get(
                "candidate_top_k"
            )
            and by_arm["heuristic_historical_greedy"].get("scheduler", {}).get(
                "budget_requested"
            )
            == by_arm["v4_historical_greedy"].get("scheduler", {}).get(
                "budget_requested"
            )
            and by_arm["heuristic_historical_greedy"].get("same_pool_group")
            == "heuristic_reference"
        )
        for group in groups.values()
        if (by_arm := {str(row["arm"]): row for row in group})[
            "v4_historical_greedy"
        ].get("root_eligibility")
        == "schedulable"
    )
    _check(heuristic_budget, "heuristic_reference_equal_compute_budget", checks, errors)

    preflight_binding = seal_summary.get("preflight_binding", {})
    preflight_ok, preflight_root, preflight_summary, _ = _linked_preflight(
        root, preflight_binding
    )
    weights_ok = False
    weights: FrozenExecutionPenaltyWeights | None = None
    try:
        weights = _weights_from_payload(preflight_summary["frozen_penalty_weights"])
        weights_ok = bool(
            preflight_ok
            and weights.weights_sha256 == preflight_summary["weights_sha256"]
            and seal_summary.get("evaluation_lock", {}).get("frozen_penalty_weights")
            == preflight_summary["frozen_penalty_weights"]
            and bindings.get("weights_sha256") == weights.weights_sha256
            and preflight_root is not None
            and bindings.get("preflight_summary_sha256")
            == sha256_file(preflight_root / "summary.json")
            and seal_root is not None
            and bindings.get("seal_summary_sha256")
            == sha256_file(seal_root / "summary.json")
            and bindings.get("evaluation_lock_sha256")
            == seal_summary.get("evaluation_lock_sha256")
            and bindings.get("profile_spec_sha256")
            == preflight_summary["profile_spec_sha256"]
            and bindings.get("profile_sha256") == preflight_summary["profile_sha256"]
            and bindings.get("compute_contract_sha256")
            == preflight_summary["compute_contract_sha256"]
            == seal_summary.get("compute_contract_sha256")
            == _compute_contract_sha256(config)
            and bindings.get("refit_after_holdout_release") is False
            and bindings.get("model_selection_after_holdout_release") is False
            and all(row.get("weights_sha256") == weights.weights_sha256 for row in rows)
        )
    except (KeyError, TypeError, ValueError):
        pass
    _check(weights_ok, "sealed_preflight_weights_bound", checks, errors)

    checkpoint = v4.get("checkpoint", Path("/nonexistent"))
    rebuilt = bool(weights is not None and Path(checkpoint).is_file()) and all(
        _rebuild_search_row(
            row,
            config,
            weights,
            Path(checkpoint),
            coordinates[str(row["family"])][int(row["output_bit"])],
        )
        and _trial_semantics_native_ok(
            row, config, coordinates[str(row["family"])][int(row["output_bit"])]
        )
        for row in rows
    )
    _check(
        rebuilt,
        "independent_search_plan_native_reconstruction",
        checks,
        errors,
    )

    schedulable_v4_rows = [
        row
        for row in rows
        if row.get("arm") in V4_ARMS and row.get("root_eligibility") == "schedulable"
    ]
    activation_ok = bool(schedulable_v4_rows) and all(
        (
            row.get("learned_policy_active_at_root") is True
            and row.get("learned_value_active") is True
            and int(_policy_stats_from_row(row).get("learned_states", 0)) > 0
            and int(_value_stats_from_row(row).get("value_calls", 0)) > 0
        )
        if row.get("arm") in V4_ARMS and row.get("root_eligibility") == "schedulable"
        else (
            row.get("learned_policy_active_at_root") is False
            and row.get("learned_value_active") is False
        )
        if row.get("arm") not in V4_ARMS
        else True
        for row in rows
    )
    _check(
        activation_ok
        and fairness.get("each_family_has_schedulable_activity") is True,
        "learned_policy_value_active_in_schedulable_v4_arms",
        checks,
        errors,
    )

    qaoa_rows = [row for row in rows if row.get("arm") in QAOA_ARMS]
    qaoa_ok = all(
        (
            row.get("execution_status") == "not_invoked_degenerate"
            and row.get("scheduler", {}).get("qaoa_attempted") is False
        )
        if row.get("root_eligibility") == "degenerate_direct_root"
        else (
            row.get("execution_status")
            in {
                "direct_unrepaired",
                "direct_repaired",
                "fallback",
                "not_invoked_small_pool",
            }
            and (
                row.get("scheduler", {}).get("qaoa_attempted") is True
            )
            is (row.get("execution_status") != "not_invoked_small_pool")
        )
        for row in qaoa_rows
    )
    selection_ok = all(
        (
            row["scheduler"]["candidate_count"] == 0
            and row["scheduler"]["budget_effective"] == 0
            and row["scheduler"]["selected_indices"] == []
            and row["scheduler"]["selected_action_visits_total"] == 0
            and row["scheduler"]["excluded_action_visits_total"] == 0
        )
        if row.get("root_eligibility") == "degenerate_direct_root"
        else (
            len(row["scheduler"]["selected_indices"])
            == row["scheduler"]["budget_effective"]
            and len(set(row["scheduler"]["selected_indices"]))
            == len(row["scheduler"]["selected_indices"])
            and all(
                0 <= int(index) < int(row["scheduler"]["candidate_count"])
                for index in row["scheduler"]["selected_indices"]
            )
            and row["scheduler"]["selected_action_visits_total"]
            == row["simulations"]
            and row["scheduler"]["excluded_action_visits_total"] == 0
        )
        for row in rows
    )
    _check(qaoa_ok and selection_ok, "scheduler_selection_and_qaoa_itt", checks, errors)
    _check(
        summary.get("qaoa_accounting") == {
            "rows": len(qaoa_rows),
            "direct_unrepaired": sum(
                row.get("qaoa_execution") == "direct_unrepaired" for row in qaoa_rows
            ),
            "direct_repaired": sum(
                row.get("qaoa_execution") == "direct_repaired" for row in qaoa_rows
            ),
            "fallback": sum(
                row.get("qaoa_execution") == "fallback" for row in qaoa_rows
            ),
            "not_invoked_degenerate": sum(
                row.get("execution_status") == "not_invoked_degenerate"
                for row in qaoa_rows
            ),
            "not_invoked_small_pool": sum(
                row.get("execution_status") == "not_invoked_small_pool"
                for row in qaoa_rows
            ),
            "invalid": sum(
                row.get("execution_status") == "invalid" for row in qaoa_rows
            ),
            "status_taxonomy": list(EXECUTION_STATUSES),
            "status_counts_all_arms": eligibility_identity["status_counts"],
            "status_total_all_arms": eligibility_identity["status_total"],
            "status_taxonomy_closed": eligibility_identity[
                "status_taxonomy_closed"
            ],
        }
        and all(
            row.get("holdout_outcome_used_by_utility") is False
            and row.get("noisy_outcome_used_by_utility") is False
            for row in rows
        ),
        "qaoa_counts_and_no_outcome_feedback_recomputed",
        checks,
        errors,
    )

    profile, profile_sha = _frozen_profile(config)
    _check(
        summary.get("frozen_profile") == profile
        and summary.get("profile_sha256") == profile_sha
        and summary.get("profile_spec_sha256") == _profile_spec(config).profile_sha256
        and all(
            row.get("logical_n_qubits") == 10
            and row.get("native", {}).get("n_qubits") == 10
            and row.get("profile_sha256") == profile_sha
            and row.get("native", {}).get("profile_sha256") == profile_sha
            for row in rows
        ),
        "fixed10q_all_five_arms",
        checks,
        errors,
    )

    recomputed = _all_comparisons(rows, config)
    summary_comparisons = {
        "primary": summary.get("primary"),
        "secondary": summary.get("secondary"),
        "direct_sensitivity": summary.get("direct_sensitivity"),
    }
    _check(
        summary_comparisons == recomputed
        and summary.get("primary_comparison") == recomputed["primary"]
        and summary.get("secondary_comparisons") == recomputed["secondary"]
        and summary.get("direct_unrepaired_sensitivity")
        == recomputed["direct_sensitivity"],
        "family_bit_cluster_statistics_recomputed",
        checks,
        errors,
    )
    _check(
        recomputed["primary"]["family"] == "ASCON"
        and recomputed["primary"]["cluster_count"] == 5
        and recomputed["primary"]["nonzero_cluster_count"]
        + recomputed["primary"]["zero_cluster_count"]
        == 5
        and recomputed["primary"]["effective_exact_sign_flip_permutations"]
        == 1 << recomputed["primary"]["nonzero_cluster_count"]
        and recomputed["primary"]["exact_two_sided_sign_flip_p"] is not None
        and float(recomputed["primary"]["exact_two_sided_sign_flip_p"])
        >= float(
            recomputed["primary"]["minimum_attainable_two_sided_sign_flip_p"]
        )
        and all(
            comparison.get("schedulable_only") is True
            and comparison.get("estimand") == "schedulable_only_secondary"
            for comparison in recomputed["secondary"].values()
        )
        and len(recomputed["direct_sensitivity"]["excluded_cluster_reasons"])
        == len(recomputed["direct_sensitivity"]["excluded_clusters"]),
        "five_cluster_claim_boundary",
        checks,
        errors,
    )
    _check(
        summary.get("schema_version") == EVALUATION_SUMMARY_SCHEMA
        and summary.get("phase") == "evaluate"
        and run.get("status") == "complete"
        and summary.get("evidence_ok") is True
        and summary.get("experiment_completed") is True
        and summary.get("amendment_classification")
        == config["amendment"]["classification"]
        and summary.get("amendment_sha256")
        == sha256_bytes(canonical_json_bytes(config["amendment"]))
        and config_sha == run.get("config", {}).get("canonical_sha256")
        == summary.get("config_sha256"),
        "evaluate_phase_schema_config_status",
        checks,
        errors,
    )
    _check(
        summary.get("compute_contract") == config["compute_contract"]
        and summary.get("compute_contract_sha256")
        == _compute_contract_sha256(config)
        and _compute_runtime_matches(summary.get("compute_runtime"), config)
        and run.get("compute_contract") == config["compute_contract"]
        and run.get("compute_contract_sha256") == _compute_contract_sha256(config)
        and _compute_runtime_matches(run.get("compute_runtime"), config),
        "evaluate_compute_contract_bound",
        checks,
        errors,
    )
    _check(
        summary.get("complete_matrix") is True
        and summary.get("trial_count") == 90
        and summary.get("expected_trial_count") == 90
        and summary.get("fairness", {}).get("v4_four_arm_same_pool") is True
        and summary.get("v4_four_arm_fairness") == fairness
        and summary.get("root_eligibility_and_degenerate_identity")
        == eligibility_identity
        and summary.get("model_activation", {}).get("all_v4_policy_active") is True
        and summary.get("model_activation", {}).get("all_v4_value_active") is True
        and summary.get("model_activation", {}).get("activity_scope")
        == "schedulable_v4_rows_only"
        and summary.get("learned_mechanism")
        == {
            "v4_policy_active_all": all(
                row.get("learned_policy_active_at_root") is True
                and int(row.get("policy_cache_misses", 0)) > 0
                for row in schedulable_v4_rows
            ),
            "v4_value_active_all": all(
                row.get("learned_value_enabled") is True
                and int(_value_stats_from_row(row).get("value_calls", 0)) > 0
                for row in schedulable_v4_rows
            ),
            "scope": "schedulable_v4_rows_only",
            "schedulable_v4_row_count": len(schedulable_v4_rows),
            "degenerate_v4_rows_exempt_from_inference_activity": sum(
                row.get("arm") in V4_ARMS
                and row.get("root_eligibility") == "degenerate_direct_root"
                for row in rows
            ),
            "heuristic_policy_value_disabled_all": all(
                row.get("learned_policy_active_at_root") is False
                and row.get("learned_value_enabled") is False
                for row in rows
                if row.get("arm") == FIVE_ARMS[0]
            ),
        }
        and summary.get("logical_semantics_all") is True
        and summary.get("native_contract_all") is True
        and summary.get("performance_claim_supported") is False
        and summary.get("primary_endpoint") == config["primary_endpoint"],
        "evaluate_summary_matrix_fairness_activation",
        checks,
        errors,
    )
    _check(
        summary.get("access_contract", {}).get("family_exclusion_label") == HOLDOUT_LABEL
        and summary.get("access_contract", {}).get("release_order") == ["ASCON", "PRESENT"]
        and summary.get("access_contract", {}).get("training_access_allowed") is False,
        "evaluate_labelled_release_order",
        checks,
        errors,
    )
    _check(
        summary.get("scope", {}).get("synthetic_profile") is True
        and summary.get("scope", {}).get("hardware_execution") is False
        and summary.get("scope", {}).get("noisy_diagnostic_run") is False
        and summary.get("scope", {}).get("quantum_speedup_claimed") is False
        and summary.get("scope", {}).get("quantum_advantage_claimed") is False
        and summary.get("scope", {}).get("binary_superiority_claimed") is False
        and summary.get("scope", {}).get("primary_iid_cluster_count") == 5
        and summary.get("scope", {}).get("primary_nonzero_cluster_count")
        == recomputed["primary"]["nonzero_cluster_count"]
        and summary.get("scope", {}).get("primary_zero_cluster_count")
        == recomputed["primary"]["zero_cluster_count"]
        and summary.get("scope", {}).get(
            "minimum_attainable_two_sided_exact_p"
        )
        == recomputed["primary"]["minimum_attainable_two_sided_sign_flip_p"],
        "evaluate_scope_boundary",
        checks,
        errors,
    )
    return checks


def _failure_config_binding(
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    """Authenticate the recorder config without requiring it to have loaded.

    A failure may occur while parsing the requested config.  Such an attempt is
    still valid failure evidence, but it cannot claim an authenticated v1.1
    amendment.  Retrospective v1 evidence, in contrast, is written by the v1.1
    recorder and must bind the complete current amendment ledger.
    """

    try:
        attempt = summary["attempt_config"]
        recorder = summary["evidence_recorder_config"]
        if (
            not isinstance(attempt, Mapping)
            or not isinstance(recorder, Mapping)
            or run.get("attempt_config") != attempt
            or run.get("evidence_recorder_config") != recorder
            or set(recorder)
            != {
                "schema_version",
                "config_file_sha256",
                "config_canonical_sha256",
                "amendment_sha256",
                "role",
            }
        ):
            return False, None

        candidates = [
            PROJECT_ROOT
            / "configs"
            / "xa202609"
            / "e5_external_crypto_holdout_v1.json"
        ]
        command_path = run.get("command", {}).get("config")
        if isinstance(command_path, str) and command_path:
            candidates.append(Path(command_path).expanduser())
        authenticated: dict[str, Any] | None = None
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                if not resolved.is_file():
                    continue
                config = _read_json(resolved)
                if (
                    sha256_file(resolved) == recorder.get("config_file_sha256")
                    and sha256_bytes(canonical_json_bytes(config))
                    == recorder.get("config_canonical_sha256")
                ):
                    authenticated = config
                    break
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                continue

        if authenticated is None:
            # This is the only accepted unauthenticated state: the runner failed
            # before a config object or amendment could be loaded.  The available
            # file digest remains an opaque attempt identifier, not a protocol
            # authentication claim.
            unavailable = bool(
                recorder.get("schema_version") is None
                and recorder.get("config_canonical_sha256") is None
                and recorder.get("amendment_sha256") is None
                and recorder.get("role") == "failure_evidence_recorder"
                and summary.get("amendment_sha256") is None
                and summary.get("parent_v1_binding") is None
                and attempt
                == {
                    "schema_version": "xa.e5-attempt-config-binding.v1.1",
                    "config_file_sha256": recorder.get("config_file_sha256"),
                    "config_canonical_sha256": None,
                    "protocol_version": "v1.1",
                }
                and (
                    recorder.get("config_file_sha256") is None
                    or _is_sha256(recorder.get("config_file_sha256"))
                )
            )
            return unavailable, None

        amendment = authenticated.get("amendment")
        amendment_sha = sha256_bytes(canonical_json_bytes(amendment))
        if (
            authenticated.get("schema_version") != CONFIG_SCHEMA
            or not _verify_amendment_ledger(authenticated)
            or recorder.get("schema_version") != CONFIG_SCHEMA
            or recorder.get("amendment_sha256") != amendment_sha
            or summary.get("amendment_sha256") != amendment_sha
            or summary.get("parent_v1_binding") != amendment.get("parent_v1")
        ):
            return False, None

        if summary.get("retrospective") is True:
            parent = amendment["parent_v1"]
            expected_attempt = {
                "schema_version": "xa.e5-attempt-config-binding.v1",
                "config_file_sha256": parent["config_file_sha256"],
                "config_canonical_sha256": parent["config_canonical_sha256"],
                "static_lock_canonical_sha256": parent[
                    "static_lock_canonical_sha256"
                ],
                "runner_sha256": parent["runner_sha256"],
                "verifier_sha256": parent["verifier_sha256"],
                "contract_test_sha256": parent["contract_test_sha256"],
                "protocol_version": "v1",
            }
            role = "retrospective_evidence_recorder"
        else:
            expected_attempt = {
                "schema_version": "xa.e5-attempt-config-binding.v1.1",
                "config_file_sha256": recorder["config_file_sha256"],
                "config_canonical_sha256": recorder["config_canonical_sha256"],
                "protocol_version": "v1.1",
            }
            role = "failure_evidence_recorder"
        return bool(attempt == expected_attempt and recorder.get("role") == role), authenticated
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False, None


def _failed_partial_rows_ok(
    rows: Sequence[Mapping[str, Any]],
    *,
    phase: str,
    requested_run_id: object,
    config: Mapping[str, Any] | None,
) -> bool:
    """Verify self-contained partial-row evidence without opening hold-outs."""

    if rows and phase != "evaluate":
        return False
    actual_keys: list[tuple[Any, Any, Any, Any]] = []
    for row in rows:
        try:
            eligibility = str(row["root_eligibility"])
            action_count = int(row["root_action_count"])
            native = row["native"]
            endpoint = row["primary_endpoint"]
            bf = BooleanFunction(
                int(row["input_width"]), int(str(row["truth_table_hex"]), 16)
            )
            key = (
                row["family"],
                int(row["output_bit"]),
                int(row["solver_seed"]),
                row["arm"],
            )
            if (
                row.get("schema_version") != EVALUATION_ROW_SCHEMA
                or row.get("run_id") != requested_run_id
                or row.get("phase") != "evaluate"
                or eligibility not in ROOT_ELIGIBILITIES
                or eligibility
                != ("schedulable" if action_count > 0 else "degenerate_direct_root")
                or action_count != len(row["root_structural_action_signatures"])
                or row.get("execution_status") not in EXECUTION_STATUSES
                or row.get("qaoa_execution") != row.get("execution_status")
                or row.get("truth_table_sha256") != _truth_table_sha256(bf)
                or row.get("plan_trace_sha256")
                != sha256_bytes(canonical_json_bytes(row["plan_trace"]))
                or row.get("logical_qasm3_sha256")
                != sha256_bytes(str(row["logical_qasm3"]).encode("utf-8"))
                or native.get("native_qasm3_sha256")
                != sha256_bytes(str(native["native_qasm3"]).encode("utf-8"))
                or row.get("native_record_sha256")
                != sha256_bytes(canonical_json_bytes(native))
                or row.get("primary_endpoint_sha256")
                != sha256_bytes(canonical_json_bytes(endpoint))
                or endpoint.get("metric") != "native.two_qubit_gate_count"
                or endpoint.get("direction") != "lower_is_better"
            ):
                return False
            actual_keys.append(key)
        except (KeyError, TypeError, ValueError):
            return False
    if len(actual_keys) != len(set(actual_keys)):
        return False
    if config is not None:
        try:
            expected = [
                (family, bit, seed, arm)
                for family in config["evaluation"]["family_order"]
                for bit in config["holdout_access"]["families"][family]["coordinates"]
                for seed in config["evaluation"]["solver_seeds"]
                for arm in FIVE_ARMS
            ]
            if actual_keys != expected[: len(actual_keys)]:
                return False
            for row in rows:
                family = str(row["family"])
                bit = int(row["output_bit"])
                family_contract = config["holdout_access"]["families"][family]
                if (
                    row.get("truth_table_sha256")
                    != family_contract["coordinate_truth_table_sha256"][bit]
                    or row.get("vector_truth_table_sha256")
                    != family_contract["vector_truth_table_sha256"]
                    or row.get("family_exclusion_label") != HOLDOUT_LABEL
                    or row.get("benchmark_partition")
                    != "external_crypto_family_holdout"
                    or row.get("training_access_allowed") is not False
                ):
                    return False
        except (KeyError, TypeError, ValueError, IndexError):
            return False
    return True


def _verify_failed_attempt(
    root: Path,
    run: Mapping[str, Any],
    summary: Mapping[str, Any],
    declared: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    stdout_text: str,
    stderr_text: str,
) -> dict[str, bool]:
    """Independently validate a failed-attempt bundle as evidence, not a result."""

    checks: dict[str, bool] = {}
    errors: list[str] = []
    phase = str(summary.get("phase", ""))
    retrospective = summary.get("retrospective") is True
    requested_run_id = summary.get("requested_run_id")
    config_ok, config = _failure_config_binding(run, summary)

    _check(
        summary.get("schema_version") == FAILED_ATTEMPT_SUMMARY_SCHEMA
        and run.get("schema_version") == RUN_SCHEMA
        and declared.get("schema_version") == FAILED_ATTEMPT_VERIFIER_SCHEMA
        and run.get("track") == TRACK
        and phase in PHASE_ROLES,
        "failed_attempt_v1_1_schemas_and_track",
        checks,
        errors,
    )
    _check(
        bool(requested_run_id)
        and root.name
        == run.get("run_id")
        == summary.get("run_id")
        == declared.get("run_id")
        and run.get("requested_run_id") == requested_run_id
        and run.get("phase") == phase,
        "failed_attempt_identity",
        checks,
        errors,
    )
    _check(
        isinstance(run.get("command"), Mapping)
        and run.get("command", {}).get("entrypoint")
        == "scripts/run_e5_external_crypto_holdout.py"
        and run.get("command", {}).get("phase") == phase,
        "failed_attempt_requested_command",
        checks,
        errors,
    )
    _check(
        run.get("status") == "failed"
        and summary.get("status") == "failed_attempt_evidence"
        and run.get("evidence_ok") is True
        and summary.get("evidence_ok") is True
        and declared.get("evidence_ok") is True
        and run.get("experiment_completed") is False
        and summary.get("experiment_completed") is False
        and declared.get("experiment_completed") is False,
        "failed_attempt_evidence_completion_separated",
        checks,
        errors,
    )
    _check(config_ok, "failed_attempt_config_and_amendment_binding", checks, errors)
    _check(
        run.get("counts")
        == {"rows": len(rows), "holdout_coordinates": 0, "noisy_shots": 0}
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES
        and int(summary.get("completed_trial_row_count", -1)) == len(rows),
        "failed_attempt_counts_and_nine_artifacts",
        checks,
        errors,
    )

    exception = summary.get("exception", {})
    last_event = events[-1] if events else {}
    exception_ok = bool(
        isinstance(exception, Mapping)
        and str(exception.get("type", "")).strip()
        and str(exception.get("message", "")).strip()
        and run.get("exception") == exception
        and last_event.get("event") == "failed_attempt_persisted"
        and last_event.get("run_id") == root.name
        and last_event.get("requested_run_id") == requested_run_id
        and last_event.get("phase") == phase
        and last_event.get("exception_type") == exception.get("type")
        and last_event.get("created_at_utc") == summary.get("record_created_at_utc")
    )
    _check(exception_ok, "failed_attempt_exception_and_terminal_event", checks, errors)

    common_time_ok = bool(
        run.get("record_created_at_utc") == summary.get("record_created_at_utc")
        and str(summary.get("record_created_at_utc", "")).strip()
        and run.get("attempt_time_utc") == summary.get("attempt_time_utc")
        and run.get("attempt_time_status") == summary.get("attempt_time_status")
        and summary.get("terminal_transcript_fabricated") is False
    )
    if retrospective:
        terminal_ok = bool(
            common_time_ok
            and summary.get("attempt_time_utc") is None
            and summary.get("attempt_time_status") == "unknown_not_captured"
            and summary.get("terminal_capture_available") is False
            and exception.get("traceback_persisted") is False
            and stdout_text.startswith(
                "RETROSPECTIVE EXPLANATION, NOT ORIGINAL TERMINAL CAPTURE."
            )
            and stderr_text.startswith(
                "RETROSPECTIVE EXPLANATION, NOT ORIGINAL TERMINAL CAPTURE."
            )
            and "does not reconstruct one" in stdout_text
            and not rows
        )
    else:
        terminal_ok = bool(
            common_time_ok
            and summary.get("attempt_time_utc")
            == summary.get("record_created_at_utc")
            and summary.get("attempt_time_status") == "failure_record_creation_time"
            and summary.get("terminal_capture_available") is False
            and exception.get("traceback_persisted") is True
            and stdout_text
            == "Runner failure evidence bundle created; stdout was not internally captured.\n"
            and "Traceback (most recent call last)" in stderr_text
            and str(exception.get("type")) in stderr_text
            and str(exception.get("message")) in stderr_text
        )
    _check(terminal_ok, "failed_attempt_time_and_terminal_semantics", checks, errors)

    if retrospective and config is not None:
        incident = config["amendment"]["incident"]
        retrospective_ok = bool(
            phase == "evaluate"
            and requested_run_id == incident["first_release_run_id"]
            and exception.get("type") == "RuntimeError"
            and exception.get("message") == incident["first_trial_error"]
            and len(events) == 2
            and events[0]
            == {
                "event": "retrospective_bound_to_v1_incident",
                "incident": incident,
                "parent_v1": config["amendment"]["parent_v1"],
            }
            and summary.get("holdout_released") is True
            and summary.get("release_record")
            == {
                "tables_verified_at_release": ["ASCON", "PRESENT"],
                "first_trial_entered": {
                    "family": "ASCON",
                    "output_bit": 0,
                    "solver_seed": 1,
                    "arm": "heuristic_historical_greedy",
                },
                "remaining_trials_entered": False,
            }
        )
    else:
        retrospective_ok = summary.get("retrospective") is False
    _check(
        retrospective_ok,
        "failed_attempt_retrospective_parent_incident",
        checks,
        errors,
    )

    _check(
        summary.get("endpoint_summary_available") is False
        and summary.get("comparison_available") is False
        and summary.get("model_selection_performed") is False
        and summary.get("weight_refit_performed") is False
        and summary.get("noisy_diagnostic_performed") is False
        and summary.get("performance_outcome_available") is bool(rows)
        and summary.get("holdout_released") is bool(summary.get("release_record"))
        and (not rows or summary.get("holdout_released") is True),
        "failed_attempt_claim_absence_and_release_state",
        checks,
        errors,
    )
    _check(
        _failed_partial_rows_ok(
            rows,
            phase=phase,
            requested_run_id=requested_run_id,
            config=config,
        ),
        "failed_attempt_partial_rows_self_bound",
        checks,
        errors,
    )
    _check(
        declared
        == {
            "schema_version": FAILED_ATTEMPT_VERIFIER_SCHEMA,
            "run_id": root.name,
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
        },
        "failed_attempt_declared_report_exact",
        checks,
        errors,
    )
    return checks


def verify_e5_external_crypto_holdout_bundle(
    run_dir: str | Path,
    *,
    _allow_links: bool = True,
    _expected_phase: str | None = None,
) -> dict[str, Any]:
    """Verify one immutable E5 phase bundle and return all named checks."""

    root = Path(run_dir).resolve()
    generic = verify_bundle(root)
    errors = list(generic.errors)
    checks: dict[str, bool] = {
        "artifact_checksums_manifest": generic.ok,
        "exact_nine_file_bundle": root.is_dir()
        and {path.name for path in root.iterdir()} == EXPECTED_FILES,
    }
    try:
        run = _read_json(root / "run.json")
        summary = _read_json(root / "summary.json")
        declared = _read_json(root / "verifier.json")
        rows = _read_jsonl(root / "raw.jsonl")
        events = _read_jsonl(root / "events.jsonl")
        stdout_text = (root / "stdout.log").read_text(encoding="utf-8")
        stderr_text = (root / "stderr.log").read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot parse E5 semantic artifacts: {exc}")
        return {
            "ok": False,
            "evidence_ok": False,
            "experiment_completed": False,
            "phase": None,
            "checks": checks,
            "errors": errors,
        }

    phase = str(summary.get("phase", ""))
    required = PHASE_ROLES.get(phase)
    roles_ok = False
    if required is not None:
        phase_bundle = verify_bundle(root, required_roles=required)
        roles_ok = phase_bundle.ok
        if not phase_bundle.ok:
            errors.extend(f"artifact: {message}" for message in phase_bundle.errors)
    _check(roles_ok, "phase_artifact_roles", checks, errors)
    _check(
        _expected_phase is None or phase == _expected_phase,
        "expected_phase",
        checks,
        errors,
    )
    if summary.get("schema_version") == FAILED_ATTEMPT_SUMMARY_SCHEMA:
        checks.update(
            _verify_failed_attempt(
                root,
                run,
                summary,
                declared,
                rows,
                events,
                stdout_text,
                stderr_text,
            )
        )
        for name, passed in checks.items():
            if not passed and f"failed check: {name}" not in errors:
                errors.append(f"failed check: {name}")
        evidence_ok = not errors and all(checks.values())
        return {
            "ok": evidence_ok,
            "evidence_ok": evidence_ok,
            "experiment_completed": False,
            "phase": phase,
            "bundle": str(root),
            "checks": checks,
            "errors": errors,
            "verifier_compute_runtime": {},
        }

    _check(
        bool(run.get("run_id"))
        and run.get("run_id") == summary.get("run_id") == declared.get("run_id"),
        "run_id_consistent",
        checks,
        errors,
    )
    _check(
        run.get("phase") == phase
        and int(run.get("counts", {}).get("rows", -1)) == len(rows)
        and run.get("holdout_accessed") is (phase == "evaluate")
        and run.get("status") == "complete"
        and run.get("evidence_ok") is True
        and run.get("experiment_completed") is True
        and summary.get("evidence_ok") is True
        and summary.get("experiment_completed") is True
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "run_phase_counts_access_and_artifacts",
        checks,
        errors,
    )
    _check(
        run.get("track") == TRACK
        and run.get("schema_version") == RUN_SCHEMA
        and run.get("config", {}).get("runner_schema") == RUNNER_SCHEMA,
        "track_and_runner_schema",
        checks,
        errors,
    )
    _check(
        declared.get("schema_version") == DECLARED_VERIFIER_SCHEMA
        and declared.get("ok") is True
        and declared.get("evidence_ok") is True
        and declared.get("experiment_completed") is True
        and declared.get("independent_recomputation") is False
        and isinstance(declared.get("checks"), dict)
        and bool(declared.get("checks"))
        and all(bool(value) for value in declared.get("checks", {}).values()),
        "runner_declared_verifier_passed",
        checks,
        errors,
    )
    try:
        config = _effective_config(run)
    except (KeyError, TypeError, ValueError, OSError):
        config = {}
    config_shape_ok = config.get("schema_version") == CONFIG_SCHEMA
    _check(config_shape_ok, "effective_config_schema", checks, errors)
    if config_shape_ok:
        config_sha = sha256_bytes(canonical_json_bytes(config))
        config_record = run.get("config", {})
        if not isinstance(config_record, Mapping):
            config_record = {}
        config_path = (
            PROJECT_ROOT
            / "configs"
            / "xa202609"
            / "e5_external_crypto_holdout_v1.json"
        )
        _check(
            config_path.is_file()
            and config_record.get("path_hint") == config_path.name
            and config_record.get("file_sha256") == sha256_file(config_path)
            and config_record.get("config_sha256") == config_sha
            and config_record.get("canonical_sha256") == config_sha
            and config_record.get("effective_config") == config,
            "effective_config_hash_and_file_identity",
            checks,
            errors,
        )
        _check(
            config.get("status")
            == "post_release_pre_endpoint_amendment_pre_registered_unrun"
            and config.get("experiment_role") == "external_family_holdout_evaluation"
            and config.get("dataset_role")
            == "never_trained_ascon_primary_present_secondary"
            and _verify_amendment_ledger(config)
            and config.get("holdout_access", {}).get("family_exclusion_label")
            == HOLDOUT_LABEL
            and config.get("search", {}).get("policy_term_threshold") == 0
            and config.get("search", {}).get("learned_value_required") is True
            and config.get("evaluation", {}).get("family_order") == ["ASCON", "PRESENT"]
            and [item.get("name") for item in config.get("evaluation", {}).get("arms", [])]
            == list(FIVE_ARMS)
            and config.get("native_profile", {}).get("frozen_n_qubits") == 10
            and config.get("compute_contract")
            == {
                "device": "cpu",
                "torch_intraop_threads": 1,
                "torch_interop_threads": 1,
                "torch_deterministic_algorithms": True,
            }
            and config.get("noisy_diagnostic", {}).get("enabled") is False,
            "frozen_config_semantics",
            checks,
            errors,
        )

    verifier_compute_runtime: dict[str, Any] = {}
    compute_ok = False
    if config_shape_ok:
        try:
            verifier_compute_runtime = _establish_compute_contract(
                config,
                context=f"verifier-{phase}-before-checkpoint-inference",
            )
            compute_ok = _compute_runtime_matches(verifier_compute_runtime, config)
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            errors.append(f"cannot establish verifier compute contract: {exc}")
    _check(
        compute_ok,
        "verifier_compute_contract_established_before_checkpoint_inference",
        checks,
        errors,
    )
    if config_shape_ok:
        bundle_compute_ok = False
        try:
            bundle_compute_ok = bool(
                run.get("compute_contract") == config.get("compute_contract")
                and run.get("compute_contract_sha256")
                == _compute_contract_sha256(config)
                and run.get("binding", {}).get("compute_contract_sha256")
                == _compute_contract_sha256(config)
                and _compute_runtime_matches(run.get("compute_runtime"), config)
                and summary.get("compute_contract") == config.get("compute_contract")
                and summary.get("compute_contract_sha256")
                == _compute_contract_sha256(config)
                and _compute_runtime_matches(summary.get("compute_runtime"), config)
            )
        except (KeyError, TypeError, ValueError):
            bundle_compute_ok = False
        _check(
            bundle_compute_ok,
            "bundle_compute_contract_identity_and_runtime",
            checks,
            errors,
        )

    if compute_ok and phase == "preflight":
        checks.update(_verify_preflight(root, run, summary, rows))
    elif compute_ok and phase == "seal" and _allow_links:
        checks.update(_verify_seal(root, run, summary, rows))
    elif compute_ok and phase == "evaluate" and _allow_links:
        checks.update(_verify_evaluate(root, run, summary, rows))
    else:
        checks["supported_phase_and_link_policy"] = False

    for name, passed in checks.items():
        if not passed and f"failed check: {name}" not in errors:
            errors.append(f"failed check: {name}")
    return {
        "ok": not errors and all(checks.values()),
        "evidence_ok": not errors and all(checks.values()),
        "experiment_completed": not errors and all(checks.values()),
        "phase": phase,
        "bundle": str(root),
        "checks": checks,
        "errors": errors,
        "verifier_compute_runtime": verifier_compute_runtime,
    }


# Public name consumed by the runner and prerequisite-bundle loader.
verify_e5_bundle = verify_e5_external_crypto_holdout_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Set XA_PROJECT_ROOT before launching when verifying a standalone copy outside experiments/scripts.",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.project_root is not None and args.project_root.resolve() != PROJECT_ROOT:
        parser.error(
            "--project-root is an early-import setting; relaunch with "
            "XA_E5_PROJECT_ROOT=/path/to/experiments"
        )
    report = verify_e5_external_crypto_holdout_bundle(args.run_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
