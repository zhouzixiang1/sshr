#!/usr/bin/env python3
"""Independently verify an E3 calibration or held-out test artifact bundle."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import sha256_file  # noqa: E402
from src.search.execution_feedback import RidgeExecutionCostModel  # noqa: E402


REQUIRED_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"raw.jsonl line {line_number} must be an object")
        rows.append(value)
    return rows


def verify_e3_bundle(run_dir: str | Path) -> dict:
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

    checks: dict[str, bool] = {
        "bundle_checksums_and_whitelist": bundle.ok,
        "run_id_consistent": bool(run.get("run_id"))
        and run.get("run_id") == summary.get("run_id") == declared.get("run_id"),
        "phase_consistent": run.get("phase")
        == summary.get("phase")
        == declared.get("phase"),
        "declared_verifier_ok": declared.get("ok") is True
        and all(declared.get("checks", {}).values()),
    }
    phase = summary.get("phase")
    if phase == "calibration":
        observations = [
            row for row in rows if row.get("record_type") == "calibration_observation"
        ]
        metadata = summary.get("model_metadata")
        try:
            loaded = RidgeExecutionCostModel.from_metadata(
                metadata,
                expected_calibration_sha256=str(summary.get("calibration_sha256")),
            )
            model_ok = loaded.metadata()["model_sha256"] == summary.get("model_sha256")
        except (TypeError, ValueError, RuntimeError):
            model_ok = False
        checks.update(
            {
                "calibration_observation_count_recomputed": len(observations)
                == summary.get("calibration_observation_count"),
                "calibration_model_frozen_encoding_valid": model_ok,
                "calibration_nll_recomputed": all(
                    abs(
                        float(row["noisy_execution"]["oracle_task_nll"])
                        + math.log(
                            (
                                int(row["noisy_execution"]["success_count"])
                                + 0.5
                            )
                            / (
                                int(row["noisy_execution"]["total_shots"])
                                + 1.0
                            )
                        )
                    )
                    <= 1e-12
                    for row in observations
                ),
                "calibration_native_and_noise_gates_recomputed": all(
                    row.get("native", {})
                    .get("ideal_equivalence", {})
                    .get("equivalent")
                    and row.get("noisy_execution", {}).get(
                        "actual_noisy_simulation_all"
                    )
                    for row in observations
                ),
            }
        )
    elif phase == "test":
        trials = [row for row in rows if row.get("record_type") == "feedback_trial"]
        variants = tuple(summary.get("variants", []))
        group_keys = {
            (row.get("case_id"), row.get("solver_seed")) for row in trials
        }
        checks.update(
            {
                "test_trial_count_recomputed": len(trials)
                == summary.get("trial_count"),
                "test_variant_matrix_recomputed": all(
                    {row.get("variant") for row in trials if (
                        row.get("case_id"), row.get("solver_seed")
                    ) == key}
                    == set(variants)
                    for key in group_keys
                ),
                "test_pool_fairness_recomputed": all(
                    len(
                        {
                            row.get("candidate_pool_sha256")
                            for row in trials
                            if (row.get("case_id"), row.get("solver_seed")) == key
                        }
                    )
                    == 1
                    for key in group_keys
                ),
                "test_rollout_fairness_recomputed": all(
                    len(
                        {
                            tuple(row.get("candidate_rollout_plan_sha256", []))
                            for row in trials
                            if (row.get("case_id"), row.get("solver_seed")) == key
                        }
                    )
                    == 1
                    for key in group_keys
                ),
                "test_nll_recomputed": all(
                    abs(
                        float(row["noisy_execution"]["oracle_task_nll"])
                        + math.log(
                            (
                                int(row["noisy_execution"]["success_count"])
                                + 0.5
                            )
                            / (
                                int(row["noisy_execution"]["total_shots"])
                                + 1.0
                            )
                        )
                    )
                    <= 1e-12
                    for row in trials
                ),
                "test_no_outcome_leakage_flag_recomputed": all(
                    row.get("test_noisy_outcome_used_by_utility") is False
                    for row in trials
                ),
                "test_native_and_noise_gates_recomputed": all(
                    row.get("plan_anf_ok")
                    and row.get("circuit_anf_ok")
                    and row.get("oracle_ok")
                    and row.get("native", {})
                    .get("ideal_equivalence", {})
                    .get("equivalent")
                    and row.get("noisy_execution", {}).get(
                        "actual_noisy_simulation_all"
                    )
                    for row in trials
                ),
            }
        )
        reference = summary.get("calibration_reference", {})
        calibration_run_id = reference.get("run_id")
        calibration_root = root.parent / str(calibration_run_id)
        calibration_summary = calibration_root / "summary.json"
        checks["calibration_reference_summary_sha"] = bool(
            calibration_summary.is_file()
            and sha256_file(calibration_summary) == reference.get("summary_sha256")
        )
    else:
        errors.append(f"unsupported E3 phase: {phase!r}")

    for name, passed in checks.items():
        if not passed:
            errors.append(f"failed check: {name}")
    return {"ok": not errors, "phase": phase, "errors": errors, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = verify_e3_bundle(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
