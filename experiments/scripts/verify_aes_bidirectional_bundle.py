#!/usr/bin/env python3
"""Independently verify an AES bidirectional-pilot evidence bundle."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, sha256_bytes  # noqa: E402
from src.benchmarks.crypto_oracles import get_crypto_oracle_coordinates  # noqa: E402


REQUIRED_ROLES = ("run", "raw", "summary", "verifier", "events", "stdout", "stderr")
EXPECTED_VARIANTS = ("classical_greedy", "qaoa_shot")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"raw.jsonl line {line_number} must be an object")
        rows.append(value)
    return rows


def _endpoint_contract_ok(row: dict[str, Any]) -> bool:
    endpoints = row.get("noisy_endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        return False
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            return False
        try:
            shots = int(endpoint["shots"])
            success_count = int(endpoint["success_count"])
            success_rate = float(endpoint["success_rate"])
            counts = endpoint["counts"]
        except (KeyError, TypeError, ValueError):
            return False
        if shots <= 0 or not 0 <= success_count <= shots:
            return False
        if not math.isclose(success_rate, success_count / shots, abs_tol=1e-12):
            return False
        if not isinstance(counts, dict) or sum(int(value) for value in counts.values()) != shots:
            return False
        if endpoint.get("actual_noisy_simulation") is not True:
            return False
        if endpoint.get("hardware_execution") is not False:
            return False
        if endpoint.get("noise_applied") is not True:
            return False
        if endpoint.get("task_contract_ok") is not True:
            return False
        if not isinstance(endpoint.get("noise_seed_anchor"), int):
            return False
    return True


def verify_aes_bundle(run_dir: str | Path) -> dict[str, Any]:
    """Recompute the bundle, matrix, semantic and scope contracts."""

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

    trials = [row for row in rows if row.get("record_type") == "aes_coordinate_trial"]
    bits = set(range(8))
    coordinate_bits = {row.get("output_bit") for row in trials}
    matrix = {
        (row.get("output_bit"), row.get("variant"))
        for row in trials
    }
    expected_matrix = {(bit, variant) for bit in bits for variant in EXPECTED_VARIANTS}
    pools_by_bit = {
        bit: {
            row.get("candidate_pool_sha256")
            for row in trials
            if row.get("output_bit") == bit
        }
        for bit in bits
    }
    qaoa_rows = [row for row in trials if row.get("variant") == "qaoa_shot"]
    expected_coordinates = get_crypto_oracle_coordinates("AES")
    expected_hashes = {
        coordinate.output_bit: coordinate.truth_table_sha256
        for coordinate in expected_coordinates
    }
    dataset = run.get("dataset", {})
    dataset_without_sha = dict(dataset) if isinstance(dataset, dict) else {}
    declared_dataset_sha = dataset_without_sha.pop("dataset_sha256", None)
    endpoint_shots = sum(
        int(endpoint.get("shots", 0))
        for row in trials
        for endpoint in row.get("noisy_endpoints", [])
        if isinstance(endpoint, dict)
    )
    endpoint_success = sum(
        int(endpoint.get("success_count", 0))
        for row in trials
        for endpoint in row.get("noisy_endpoints", [])
        if isinstance(endpoint, dict)
    )
    per_trial_shots = [
        sum(
            int(endpoint.get("shots", 0))
            for endpoint in row.get("noisy_endpoints", [])
            if isinstance(endpoint, dict)
        )
        for row in trials
    ]
    endpoint_inputs = sorted(
        {
            int(endpoint["input_x"])
            for row in trials
            for endpoint in row.get("noisy_endpoints", [])
            if isinstance(endpoint, dict) and "input_x" in endpoint
        }
    )
    noise_seed_anchors = sorted(
        {
            int(endpoint["noise_seed_anchor"])
            for row in trials
            for endpoint in row.get("noisy_endpoints", [])
            if isinstance(endpoint, dict) and "noise_seed_anchor" in endpoint
        }
    )

    scope = summary.get("scope", {})
    checks: dict[str, bool] = {
        "bundle_checksums_and_whitelist": bundle.ok,
        "run_id_consistent": bool(run.get("run_id"))
        and run.get("run_id") == summary.get("run_id") == declared.get("run_id"),
        "track_and_status": run.get("track") == "aes-bidirectional-pilot"
        and run.get("status") == "complete",
        "declared_verifier_ok": declared.get("ok") is True
        and bool(declared.get("checks"))
        and all(bool(value) for value in declared.get("checks", {}).values()),
        "exact_eight_coordinate_matrix": len(trials) == 16
        and coordinate_bits == bits
        and matrix == expected_matrix,
        "frozen_pool_fairness": all(len(pools_by_bit[bit]) == 1 for bit in bits),
        "coordinate_hashes_match_frozen_aes_contract": all(
            row.get("truth_table_sha256") == expected_hashes.get(row.get("output_bit"))
            for row in trials
        )
        and {
            item.get("output_bit"): item.get("truth_table_sha256")
            for item in dataset.get("coordinates", [])
            if isinstance(item, dict)
        }
        == expected_hashes,
        "dataset_sha_recomputed": isinstance(declared_dataset_sha, str)
        and sha256_bytes(canonical_json_bytes(dataset_without_sha))
        == declared_dataset_sha,
        "candidate_pool_hashes_recomputed": all(
            isinstance(row.get("candidate_pool"), dict)
            and sha256_bytes(canonical_json_bytes(row["candidate_pool"]))
            == row.get("candidate_pool_sha256")
            for row in trials
        ),
        "full_aes_family_verified": summary.get("aes_family_full_domain_verified") is True,
        "logical_semantics_recomputed": all(
            row.get("plan_anf_ok") is True
            and row.get("circuit_anf_ok") is True
            and row.get("oracle_ok") is True
            and row.get("reversible_oracle_all_targets_ok") is True
            for row in trials
        ),
        "native_contract_recomputed": all(
            row.get("native", {}).get("native_gate_set_ok") is True
            and row.get("native", {}).get("coupling_ok") is True
            and row.get("native", {}).get("native_gate_count", 0) > 0
            and row.get("native", {}).get("hardware_execution") is False
            for row in trials
        ),
        "noisy_endpoint_contract_recomputed": all(_endpoint_contract_ok(row) for row in trials),
        "qaoa_attempted_and_accounted": len(qaoa_rows) == 8
        and all(
            row.get("scheduler", {}).get("qaoa_attempted") is True
            and (
                row.get("scheduler", {}).get("qaoa_succeeded") is True
                or row.get("scheduler", {}).get("qaoa_fallback") is True
            )
            for row in qaoa_rows
        ),
        "scheduler_budget_and_edge_accounting": all(
            len(row.get("scheduler", {}).get("selected_indices", []))
            == row.get("scheduler", {}).get("budget_effective")
            and row.get("scheduler", {}).get("excluded_action_visits_total") == 0
            and row.get("scheduler", {}).get("selected_action_visits_total")
            == row.get("simulations")
            for row in trials
        ),
        "summary_counts_recomputed": summary.get("coordinate_count") == 8
        and summary.get("trial_count") == len(trials)
        and summary.get("noisy_endpoint", {}).get("total_shots") == endpoint_shots
        and summary.get("noisy_endpoint", {}).get("success_count") == endpoint_success
        and summary.get("noisy_endpoint", {}).get("shots_per_trial_min")
        == min(per_trial_shots, default=0)
        and summary.get("noisy_endpoint", {}).get("shots_per_trial_max")
        == max(per_trial_shots, default=0)
        and summary.get("noisy_endpoint", {}).get("input_anchors") == endpoint_inputs
        and summary.get("noisy_endpoint", {}).get("noise_seed_anchors")
        == noise_seed_anchors,
        "scope_boundary_explicit": scope.get("actual_noisy_simulation") is True
        and scope.get("hardware_execution") is False
        and scope.get("quantum_advantage_claimed") is False
        and scope.get("native_equivalence_scope") == "not-run-at-aes-scale"
        and scope.get("native_execution_scope") == "sampled-noisy-endpoints",
    }
    for name, passed in checks.items():
        if not passed:
            errors.append(f"failed check: {name}")
    return {"ok": not errors, "errors": errors, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = verify_aes_bundle(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
