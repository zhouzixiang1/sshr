#!/usr/bin/env python3
"""Independently verify an E4-v2 calibration or held-out AES bundle."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file  # noqa: E402
from src.search.execution_aware_utility import FrozenExecutionPenaltyWeights  # noqa: E402
from src.search.execution_feedback import RidgeExecutionCostModel  # noqa: E402


CALIBRATION_SCHEMA_V1 = "xa.e4-execution-aware-calibration.v1"
CALIBRATION_SCHEMA = "xa.e4-execution-aware-calibration.v2"
TEST_SCHEMA_V1 = "xa.e4-execution-aware-test.v1"
TEST_SCHEMA = "xa.e4-execution-aware-test.v2"
PRIMARY_METRIC_SCHEMA = "balanced-oracle-contract-metric-v1"
VARIANTS = {
    "historical_greedy",
    "execution_greedy",
    "historical_qaoa_shot",
    "execution_qaoa_shot",
}
RESOURCE_COMPONENTS = (
    "native_one_qubit",
    "native_two_qubit",
    "inserted_swap",
    "native_depth",
    "duration_ns",
    "model_risk",
)
REQUIRED_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")


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


def _sha_payload(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _weights(payload: Mapping[str, Any]) -> FrozenExecutionPenaltyWeights:
    return FrozenExecutionPenaltyWeights(
        calibration_sha256=str(payload["calibration_sha256"]),
        profile_sha256=str(payload["profile_sha256"]),
        **{name: float(payload[name]) for name in RESOURCE_COMPONENTS},
    )


def _observation_payload(
    rows: list[dict[str, Any]], *, schema: str
) -> list[dict[str, Any]]:
    if schema == CALIBRATION_SCHEMA:
        fields = (
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
    else:
        fields = (
            "calibration_id",
            "case_id",
            "truth_table_sha256",
            "state",
            "action",
            "raw_utility",
            "resource_components",
            "success_count",
            "total_shots",
            "oracle_task_nll",
        )
    return [{key: row[key] for key in fields} for row in rows]


def _component_metric(
    component_success: Mapping[str, int],
    *,
    shots: int,
    exact_success: int,
    n_inputs: int,
    target_index: int,
    n_qubits: int,
    ancilla_vacuous: bool,
) -> dict[str, Any]:
    names = ("input_preservation", "target_correct", "ancilla_zero")
    components: dict[str, Any] = {}
    nlls: list[float] = []
    for name in names:
        success = int(component_success[name])
        probability = (success + 0.5) / (shots + 1.0)
        nll = -math.log(probability)
        nlls.append(nll)
        components[name] = {
            "success_count": success,
            "shots": shots,
            "accuracy": success / shots,
            "jeffreys_probability": probability,
            "jeffreys_nll": nll,
            "vacuous": bool(ancilla_vacuous and name == "ancilla_zero"),
        }
    balanced_nll = statistics.mean(nlls)
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
        "balanced_accuracy": statistics.mean(
            components[name]["accuracy"] for name in names
        ),
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


def _recompute_endpoint_metric(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    counts = endpoint["counts"]
    expected = tuple(int(bit) for bit in endpoint["expected_logical_bits"])
    n_inputs = 8
    target_index = 8
    ancilla_vacuous = len(expected) == 9
    successes = {"input_preservation": 0, "target_correct": 0, "ancilla_zero": 0}
    shots = 0
    exact = 0
    for bitstring, count_value in counts.items():
        count = int(count_value)
        observed = tuple(int(bit) for bit in reversed(bitstring))
        shots += count
        if observed[:n_inputs] == expected[:n_inputs]:
            successes["input_preservation"] += count
        if observed[target_index] == expected[target_index]:
            successes["target_correct"] += count
        if ancilla_vacuous or all(bit == 0 for bit in observed[target_index + 1 :]):
            successes["ancilla_zero"] += count
        if observed == expected:
            exact += count
    return _component_metric(
        successes,
        shots=shots,
        exact_success=exact,
        n_inputs=n_inputs,
        target_index=target_index,
        n_qubits=len(expected),
        ancilla_vacuous=ancilla_vacuous,
    )


def _aggregate_endpoint_metrics(endpoints: list[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = [_recompute_endpoint_metric(endpoint) for endpoint in endpoints]
    first = metrics[0]
    successes = {
        name: sum(metric["components"][name]["success_count"] for metric in metrics)
        for name in ("input_preservation", "target_correct", "ancilla_zero")
    }
    shots = sum(metric["components"]["input_preservation"]["shots"] for metric in metrics)
    exact = sum(metric["secondary_exact_full_state"]["success_count"] for metric in metrics)
    return _component_metric(
        successes,
        shots=shots,
        exact_success=exact,
        n_inputs=int(first["n_inputs"]),
        target_index=int(first["target_index"]),
        n_qubits=int(first["n_qubits"]),
        ancilla_vacuous=all(
            metric["components"]["ancilla_zero"]["vacuous"] for metric in metrics
        ),
    )


def _append_failures(checks: Mapping[str, bool], errors: list[str]) -> None:
    errors.extend(f"failed check: {name}" for name, passed in checks.items() if not passed)


def verify_e4v2_bundle(
    run_dir: str | Path,
    *,
    calibration_run: str | Path | None = None,
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
        return {"ok": False, "phase": None, "errors": errors, "checks": {}}

    phase = summary.get("phase")
    checks: dict[str, bool] = {
        "bundle_checksum_and_role_whitelist": bundle.ok,
        "run_id_consistent": bool(run.get("run_id"))
        and run.get("run_id") == summary.get("run_id") == declared.get("run_id"),
        "phase_consistent": run.get("phase") == phase == declared.get("phase"),
        "config_sha_consistent": run.get("config", {}).get("sha256")
        == summary.get("config_sha256"),
        "declared_verifier_passed": declared.get("ok") is True
        and all(declared.get("checks", {}).values()),
        "claim_boundary_is_synthetic": run.get("status") == "complete"
        and "quantum advantage" in str(run.get("claim_boundary", "")).lower()
        and "real-device" in str(run.get("claim_boundary", "")).lower(),
    }
    if phase == "calibration":
        calibration_schema = str(summary.get("schema_version"))
        calibration_v2 = calibration_schema == CALIBRATION_SCHEMA
        observations = [
            row for row in rows if row.get("record_type") == "calibration_observation"
        ]
        freezes = [row for row in rows if row.get("record_type") == "calibration_freeze"]
        try:
            risk_model = RidgeExecutionCostModel.from_metadata(
                summary["risk_model_metadata"],
                penalty_weight=0.0,
                expected_calibration_sha256=str(summary["model_calibration_sha256"]),
            )
            risk_model_ok = risk_model.metadata()["model_sha256"] == summary["risk_model_sha256"]
        except (KeyError, TypeError, ValueError, RuntimeError):
            risk_model_ok = False
        try:
            penalty_weights = _weights(summary["penalty_weights"])
            weights_ok = (
                penalty_weights.weights_sha256 == summary["penalty_weights_sha256"]
                and penalty_weights.calibration_sha256 == summary["observations_sha256"]
                and penalty_weights.profile_sha256 == summary["profile_sha256"]
            )
        except (KeyError, TypeError, ValueError):
            weights_ok = False
        observation_sha = (
            _sha_payload(_observation_payload(observations, schema=calibration_schema))
            if observations else None
        )
        calibration_hashes = set(summary.get("calibration_truth_table_sha256", []))
        aes_hashes = set(summary.get("aes_holdout_truth_table_sha256", []))
        checks.update(
            {
                "calibration_schema": calibration_schema
                in {CALIBRATION_SCHEMA_V1, CALIBRATION_SCHEMA},
                "single_freeze_record": len(freezes) == 1,
                "observation_count_recomputed": len(observations)
                == summary.get("calibration_observation_count"),
                "observation_sha_recomputed": observation_sha
                == summary.get("observations_sha256")
                and len(freezes) == 1
                and freezes[0].get("observations_sha256") == observation_sha,
                "calibration_holdout_disjoint": bool(calibration_hashes)
                and bool(aes_hashes)
                and calibration_hashes.isdisjoint(aes_hashes),
                "risk_model_encoding_valid": risk_model_ok,
                "penalty_weight_encoding_valid": weights_ok,
                "profile_sha_recomputed": _sha_payload(summary.get("profile"))
                == summary.get("profile_sha256"),
                "nll_recomputed": all(
                    abs(
                        float(row["oracle_task_nll"])
                        + math.log(
                            (int(row["success_count"]) + 0.5)
                            / (int(row["total_shots"]) + 1.0)
                        )
                    ) <= 1e-12
                    for row in observations
                ),
                "calibration_semantics_native_noise": all(
                    row.get("plan_anf_ok") and row.get("circuit_anf_ok")
                    and row.get("oracle_ok") and row.get("native_gate_set_ok")
                    and row.get("coupling_ok")
                    and all(
                        endpoint.get("actual_noisy_simulation")
                        and endpoint.get("noise_applied")
                        and endpoint.get("hardware_execution") is False
                        and endpoint.get("task_contract_ok")
                        for endpoint in row.get("noisy_endpoints", [])
                    )
                    for row in observations
                ),
                "selection_scope_calibration_only": summary.get(
                    "selection_transcript", {}
                ).get("selection_scope") == "calibration-only-non-aes",
            }
        )
        if calibration_v2:
            recomputed = [
                _aggregate_endpoint_metrics(row["noisy_endpoints"])
                for row in observations
            ]
            checks.update(
                {
                    "primary_metric_declared_v2": summary.get("primary_metric", {}).get(
                        "schema"
                    ) == PRIMARY_METRIC_SCHEMA
                    and summary.get("primary_metric_name") == "balanced_contract_nll"
                    and summary.get("secondary_metric_name")
                    == "exact_full_state_jeffreys_nll",
                    "primary_metric_recomputed_from_counts": all(
                        metric == row.get("oracle_contract_metrics")
                        and metric["balanced_contract_nll"]
                        == row.get("balanced_contract_nll")
                        and metric["balanced_accuracy"]
                        == row.get("balanced_contract_accuracy")
                        and metric["secondary_exact_full_state"]["jeffreys_nll"]
                        == row.get("secondary_exact_full_state_nll")
                        for metric, row in zip(recomputed, observations)
                    ),
                    "three_equal_components_and_vacuous_flag": all(
                        metric["component_weighting"] == "equal-over-three-components"
                        and set(metric["components"])
                        == {"input_preservation", "target_correct", "ancilla_zero"}
                        and isinstance(metric["components"]["ancilla_zero"]["vacuous"], bool)
                        for metric in recomputed
                    ),
                    "calibration_primary_variance_recomputed": abs(
                        float(summary["calibration_primary_metric"]["population_variance"])
                        - statistics.pvariance(
                            metric["balanced_contract_nll"] for metric in recomputed
                        )
                    ) <= 1e-15,
                }
            )
    elif phase == "test":
        test_schema = str(summary.get("schema_version"))
        test_v2 = test_schema == TEST_SCHEMA
        trials = [
            row for row in rows if row.get("record_type") == "execution_aware_aes_trial"
        ]
        seeds = tuple(summary.get("solver_seeds", []))
        groups = [(bit, seed) for bit in range(8) for seed in seeds]
        execution = [row for row in trials if str(row.get("variant", "")).startswith("execution_")]
        historical = [row for row in trials if str(row.get("variant", "")).startswith("historical_")]
        expected = {
            (bit, seed, variant) for bit, seed in groups for variant in VARIANTS
        }
        actual = {
            (row.get("output_bit"), row.get("solver_seed"), row.get("variant"))
            for row in trials
        }
        reference = summary.get("calibration_reference", {})
        calibration_root = (
            Path(calibration_run).resolve()
            if calibration_run is not None
            else root.parent / str(reference.get("run_id"))
        )
        calibration_summary_path = calibration_root / "summary.json"
        calibration_cross_ok = False
        calibration_disjoint = False
        if calibration_summary_path.is_file():
            try:
                cal_summary = _read_json(calibration_summary_path)
                cal_verify = verify_e4v2_bundle(calibration_root)
                calibration_cross_ok = (
                    cal_verify["ok"]
                    and sha256_file(calibration_summary_path) == reference.get("summary_sha256")
                    and cal_summary.get("observations_sha256")
                    == reference.get("observations_sha256")
                    and cal_summary.get("risk_model_sha256")
                    == reference.get("risk_model_sha256")
                    and cal_summary.get("penalty_weights_sha256")
                    == reference.get("penalty_weights_sha256")
                    and cal_summary.get("profile_sha256") == reference.get("profile_sha256")
                )
                calibration_disjoint = set(
                    cal_summary.get("calibration_truth_table_sha256", [])
                ).isdisjoint(
                    row.get("truth_table_sha256") for row in trials
                )
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                pass
        checks.update(
            {
                "test_schema": test_schema in {TEST_SCHEMA_V1, TEST_SCHEMA},
                "complete_four_arm_matrix": len(trials) == len(expected)
                and actual == expected,
                "raw_pool_sha_recomputed": all(
                    row.get("candidate_pool_sha256")
                    == _sha_payload(row.get("candidate_pool"))
                    and row.get("candidate_pool", {}).get("utilities")
                    == row.get("raw_scheduler_utilities")
                    for row in trials
                ),
                "raw_pool_and_utility_fairness": all(
                    len({row["candidate_pool_sha256"] for row in trials
                         if (row["output_bit"], row["solver_seed"]) == group}) == 1
                    and len({tuple(row["raw_scheduler_utilities"]) for row in trials
                             if (row["output_bit"], row["solver_seed"]) == group}) == 1
                    for group in groups
                ),
                "historical_identity": all(
                    row.get("raw_scheduler_utilities")
                    == row.get("adjusted_scheduler_utilities") for row in historical
                ),
                "execution_loaded_and_no_leakage": all(
                    row.get("risk_model_loaded_without_refit") is True
                    and row.get("test_noisy_outcome_used_by_utility") is False
                    and row.get("adjuster_heldout_noisy_outcome_used") is False
                    and row.get("execution_feedback", {}).get("enabled") is True
                    for row in execution
                ),
                "frozen_hashes_on_every_row": all(
                    row.get("risk_model_sha256") == reference.get("risk_model_sha256")
                    and row.get("penalty_weights_sha256")
                    == reference.get("penalty_weights_sha256")
                    and row.get("profile_sha256") == reference.get("profile_sha256")
                    and row.get("calibration_observations_sha256")
                    == reference.get("observations_sha256")
                    for row in trials
                ),
                "common_random_number_seeds": all(
                    len({endpoint["seed"] for row in trials
                         if (row["output_bit"], row["solver_seed"]) == group
                         for endpoint in row["noisy_endpoints"]
                         if (endpoint["input_x"], endpoint["noise_seed_anchor"]) == anchor}) == 1
                    for group in groups
                    for anchor in {
                        (endpoint["input_x"], endpoint["noise_seed_anchor"])
                        for row in trials
                        if (row["output_bit"], row["solver_seed"]) == group
                        for endpoint in row["noisy_endpoints"]
                    }
                ),
                "endpoint_nll_recomputed": all(
                    abs(
                        float(row["endpoint_oracle_task_nll"])
                        + math.log(
                            (int(row["endpoint_success_count"]) + 0.5)
                            / (int(row["endpoint_total_shots"]) + 1.0)
                        )
                    ) <= 1e-12
                    for row in trials
                ),
                "test_semantics_native_noise": all(
                    row.get("plan_anf_ok") and row.get("circuit_anf_ok")
                    and row.get("oracle_ok") and row.get("reversible_oracle_all_targets_ok")
                    and row.get("native", {}).get("native_gate_set_ok")
                    and row.get("native", {}).get("coupling_ok")
                    and all(
                        endpoint.get("actual_noisy_simulation")
                        and endpoint.get("noise_applied")
                        and endpoint.get("hardware_execution") is False
                        and endpoint.get("task_contract_ok")
                        for endpoint in row.get("noisy_endpoints", [])
                    )
                    for row in trials
                ),
                "calibration_bundle_cross_verified": calibration_cross_ok,
                "calibration_aes_hashes_disjoint": calibration_disjoint,
                "test_scope_no_performance_claim": summary.get("hardware_execution") is False
                and summary.get("quantum_advantage_claimed") is False
                and (not summary.get("tiny") or summary.get("performance_evidence") is False),
            }
        )
        if test_v2:
            recomputed_test = [
                _aggregate_endpoint_metrics(row["noisy_endpoints"])
                for row in trials
            ]
            checks.update(
                {
                    "test_primary_metric_declared_v2": summary.get(
                        "primary_metric", {}
                    ).get("schema") == PRIMARY_METRIC_SCHEMA
                    and summary.get("primary_metric_name") == "balanced_contract_nll"
                    and summary.get("secondary_metric_name")
                    == "exact_full_state_jeffreys_nll",
                    "test_primary_metric_recomputed_from_counts": all(
                        metric == row.get("endpoint_oracle_contract_metrics")
                        and metric["balanced_contract_nll"]
                        == row.get("endpoint_balanced_contract_nll")
                        and metric["balanced_accuracy"]
                        == row.get("endpoint_balanced_contract_accuracy")
                        and metric["secondary_exact_full_state"]["jeffreys_nll"]
                        == row.get("endpoint_secondary_exact_full_state_nll")
                        for metric, row in zip(recomputed_test, trials)
                    ),
                    "test_three_equal_components_and_vacuous_flag": all(
                        metric["component_weighting"] == "equal-over-three-components"
                        and set(metric["components"])
                        == {"input_preservation", "target_correct", "ancilla_zero"}
                        and isinstance(metric["components"]["ancilla_zero"]["vacuous"], bool)
                        for metric in recomputed_test
                    ),
                }
            )
    else:
        errors.append(f"unsupported E4-v2 phase: {phase!r}")

    _append_failures(checks, errors)
    return {"ok": not errors, "phase": phase, "errors": errors, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--calibration-run", type=Path, default=None)
    args = parser.parse_args()
    result = verify_e4v2_bundle(args.run_dir, calibration_run=args.calibration_run)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
