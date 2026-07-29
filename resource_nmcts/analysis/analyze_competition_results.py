#!/usr/bin/env python3
"""Strict paired statistics for the XA-202609 competition DuckDB.

The database is opened read-only.  Logical observations are paired on
``experiment × suite × case × synthesis seed``; mapped observations add the
*exact*, content-addressed target and transpile specification.  Seed-level
differences are first reduced to one median difference per independent Boolean
function.  Wilcoxon, rank-biserial effects, and all bootstrap intervals then use
the Boolean function -- never the seed row -- as the resampling/inference unit.
Only canonical successful attempts with non-adverse verification enter quality
statistics.  Missing, unverified, illegal, or metric-incomplete observations
are retained as explicit exclusions.

Sign convention
---------------
All registered metrics are lower-is-better.  ``delta`` is
``candidate - reference`` (negative favours the candidate), while relative
improvement and paired rank-biserial effect are positive when the candidate is
better.  Wilcoxon uses the two-sided signed-rank test with
``zero_method='wilcox'``: exact zero differences are discarded from the test
statistic but remain ties in descriptive counts.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from scipy.stats import rankdata, wilcoxon

from src.experiment_db import ExperimentDB, canonical_json


DEFAULT_DB = _PROJECT_ROOT / "results" / "competition_experiments.duckdb"
DEFAULT_CSV = _PROJECT_ROOT / "results" / "summary_competition_results.csv"
DEFAULT_JSON = _PROJECT_ROOT / "results" / "summary_competition_results.json"
BOOTSTRAP_SEED = 20260915
BOOTSTRAP_SAMPLES = 5000
ALPHA = 0.05
ZERO_METHOD = "wilcox"


# Frozen before the formal analysis.  The competition wording uses ``logic_T``,
# ``logic_CNOT``, and ``native_twoq_count``; the database's canonical column
# names are listed here.  Each family receives its own Holm correction.  A
# global Holm correction is emitted separately as a sensitivity analysis.
LOGICAL_PRIMARY_METRICS = frozenset({"t_count", "cnot_count"})
MAPPING_PRIMARY_METRICS = frozenset({"native_entangling_count", "mapped_depth"})


LOGICAL_METRICS: tuple[str, ...] = (
    "t_count",
    "cnot_count",
    "depth",
    "gate_count",
    "ancilla_count",
    "n_qubits",
    "weighted_score",
    "runtime_s",
)

MAPPING_METRICS: tuple[str, ...] = (
    "total_gate_count",
    "one_qubit_gate_count",
    "two_qubit_gate_count",
    "native_entangling_count",
    "swap_count",
    "mapped_depth",
    "two_qubit_depth",
    "routing_overhead",
    "estimated_error",
    "mapping_runtime_s",
)


SUMMARY_FIELDS: tuple[str, ...] = (
    "scope",
    "experiment_id",
    "experiment_slug",
    "experiment_title",
    "suite",
    "target_id",
    "target_name",
    "target_spec_hash",
    "transpile_spec_id",
    "transpile_spec_name",
    "transpile_spec_hash",
    "reference_method_spec_id",
    "reference_method",
    "reference_method_spec_hash",
    "candidate_method_spec_id",
    "candidate_method",
    "candidate_method_spec_hash",
    "metric",
    "lower_is_better",
    "delta_definition",
    "relative_improvement_definition",
    "analysis_mode",
    "required_seeds_json",
    "n_required_seeds",
    "inference_unit",
    "within_function_aggregation",
    "n_candidate_keys",
    "n_function_candidate_keys",
    "n_paired_view_verified_keys",
    "n_base_eligible_pairs",
    "n_seed_pairs_available",
    "n_seed_pairs",
    "n_pairs",
    "n_functions_complete_observed",
    "n_functions_incomplete_observed",
    "n_functions_required_seed_complete",
    "n_functions_required_seed_incomplete",
    "seed_pairs_per_function_min",
    "seed_pairs_per_function_median",
    "seed_pairs_per_function_max",
    "function_seed_completeness_json",
    "n_relative_defined",
    "n_excluded",
    "win_count",
    "tie_count",
    "loss_count",
    "reference_mean",
    "reference_median",
    "candidate_mean",
    "candidate_median",
    "mean_delta",
    "mean_delta_ci_low",
    "mean_delta_ci_high",
    "median_delta",
    "median_delta_ci_low",
    "median_delta_ci_high",
    "delta_iqr",
    "delta_std",
    "n_geometric_ratio_defined",
    "geometric_mean_candidate_reference_ratio",
    "geometric_mean_candidate_reference_ratio_ci_low",
    "geometric_mean_candidate_reference_ratio_ci_high",
    "mean_relative_improvement_pct",
    "mean_relative_improvement_pct_ci_low",
    "mean_relative_improvement_pct_ci_high",
    "median_relative_improvement_pct",
    "median_relative_improvement_pct_ci_low",
    "median_relative_improvement_pct_ci_high",
    "wilcoxon_statistic",
    "wilcoxon_p_raw",
    "wilcoxon_zero_method",
    "wilcoxon_nonzero_pairs",
    "rank_biserial",
    "rank_biserial_ci_low",
    "rank_biserial_ci_high",
    "holm_family",
    "holm_family_size",
    "holm_p_adjusted",
    "holm_reject",
    "global_holm_family",
    "global_holm_family_size",
    "global_holm_p_adjusted",
    "global_holm_reject",
    "alpha",
    "exclusion_counts_json",
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _query_dicts(connection: Any, sql: str) -> list[dict[str, Any]]:
    cursor = connection.execute(sql)
    columns = [str(item[0]) for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _method_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["method_spec_id"]),
        str(row["method_name"]),
        str(row["method_spec_hash"]),
    )


def _unit_key(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["case_id"]), int(row["seed"])


def _logical_pair_view_key(
    experiment_id: str,
    case_id: str,
    seed: int,
    left_spec: str,
    right_spec: str,
) -> tuple[str, str, int, tuple[str, str]]:
    return experiment_id, case_id, int(seed), tuple(sorted((left_spec, right_spec)))


def _mapping_pair_view_key(
    experiment_id: str,
    case_id: str,
    seed: int,
    transpile_spec_id: str,
    left_spec: str,
    right_spec: str,
) -> tuple[str, str, int, str, tuple[str, str]]:
    return (
        experiment_id,
        case_id,
        int(seed),
        transpile_spec_id,
        tuple(sorted((left_spec, right_spec))),
    )


def _load_logical_rows(connection: Any) -> list[dict[str, Any]]:
    return _query_dicts(
        connection,
        """
        SELECT
            cast(sc.experiment_id AS VARCHAR) AS experiment_id,
            e.slug AS experiment_slug,
            e.title AS experiment_title,
            bc.suite,
            cast(sc.case_id AS VARCHAR) AS case_id,
            bc.case_label,
            cast(bc.function_id AS VARCHAR) AS function_id,
            bf.name AS function_name,
            bf.n_inputs,
            sc.seed,
            cast(sc.method_spec_id AS VARCHAR) AS method_spec_id,
            ms.method_name,
            ms.spec_hash AS method_spec_hash,
            cast(clr.synthesis_attempt_id AS VARCHAR) AS synthesis_attempt_id,
            clr.logical_verification_count,
            clr.logical_verified,
            clr.t_count,
            clr.cnot_count,
            clr.depth,
            clr.gate_count,
            clr.ancilla_count,
            clr.n_qubits,
            clr.weighted_score,
            clr.runtime_s
        FROM synthesis_cells sc
        JOIN experiments e ON e.experiment_id = sc.experiment_id
        JOIN benchmark_cases bc ON bc.case_id = sc.case_id
        JOIN boolean_functions bf ON bf.function_id = bc.function_id
        JOIN method_specs ms ON ms.method_spec_id = sc.method_spec_id
        LEFT JOIN canonical_logical_results clr ON clr.cell_id = sc.cell_id
        """,
    )


def _load_mapping_rows(connection: Any) -> list[dict[str, Any]]:
    return _query_dicts(
        connection,
        """
        WITH attempted_specs AS (
            SELECT DISTINCT ma.synthesis_attempt_id, ma.transpile_spec_id
            FROM mapping_attempts ma
            JOIN canonical_synthesis_attempts csa
              ON csa.attempt_id = ma.synthesis_attempt_id
        )
        SELECT
            cast(sc.experiment_id AS VARCHAR) AS experiment_id,
            e.slug AS experiment_slug,
            e.title AS experiment_title,
            bc.suite,
            cast(sc.case_id AS VARCHAR) AS case_id,
            bc.case_label,
            cast(bc.function_id AS VARCHAR) AS function_id,
            bf.name AS function_name,
            bf.n_inputs,
            sc.seed,
            cast(sc.method_spec_id AS VARCHAR) AS method_spec_id,
            ms.method_name,
            ms.spec_hash AS method_spec_hash,
            cast(csa.attempt_id AS VARCHAR) AS synthesis_attempt_id,
            cast(attempted.transpile_spec_id AS VARCHAR) AS transpile_spec_id,
            ts.spec_name AS transpile_spec_name,
            ts.spec_hash AS transpile_spec_hash,
            cast(ts.target_id AS VARCHAR) AS target_id,
            ht.target_name,
            ht.spec_hash AS target_spec_hash,
            cast(cmr.mapping_attempt_id AS VARCHAR) AS mapping_attempt_id,
            cmr.mapping_verification_count,
            cmr.mapping_verified,
            cmr.total_gate_count,
            cmr.one_qubit_gate_count,
            cmr.two_qubit_gate_count,
            cmr.native_entangling_count,
            cmr.swap_count,
            cmr.mapped_depth,
            cmr.two_qubit_depth,
            cmr.target_violation_count,
            cmr.direction_violation_count,
            cmr.routing_overhead,
            cmr.estimated_error,
            cmr.mapping_runtime_s
        FROM synthesis_cells sc
        JOIN experiments e ON e.experiment_id = sc.experiment_id
        JOIN benchmark_cases bc ON bc.case_id = sc.case_id
        JOIN boolean_functions bf ON bf.function_id = bc.function_id
        JOIN method_specs ms ON ms.method_spec_id = sc.method_spec_id
        JOIN canonical_synthesis_attempts csa ON csa.cell_id = sc.cell_id
        JOIN attempted_specs attempted ON attempted.synthesis_attempt_id = csa.attempt_id
        JOIN transpile_specs ts ON ts.transpile_spec_id = attempted.transpile_spec_id
        JOIN hardware_targets ht ON ht.target_id = ts.target_id
        LEFT JOIN canonical_mapping_results cmr
          ON cmr.synthesis_attempt_id = csa.attempt_id
         AND cmr.transpile_spec_id = attempted.transpile_spec_id
        """,
    )


def _load_paired_view_keys(connection: Any) -> tuple[set[tuple[Any, ...]], set[tuple[Any, ...]]]:
    logical_rows = _query_dicts(
        connection,
        """
        SELECT cast(experiment_id AS VARCHAR) AS experiment_id,
               cast(case_id AS VARCHAR) AS case_id,
               seed,
               cast(method_a_spec_id AS VARCHAR) AS method_a_spec_id,
               cast(method_b_spec_id AS VARCHAR) AS method_b_spec_id
        FROM paired_logical_metrics
        """,
    )
    mapping_rows = _query_dicts(
        connection,
        """
        SELECT cast(experiment_id AS VARCHAR) AS experiment_id,
               cast(case_id AS VARCHAR) AS case_id,
               seed,
               cast(transpile_spec_id AS VARCHAR) AS transpile_spec_id,
               cast(method_a_spec_id AS VARCHAR) AS method_a_spec_id,
               cast(method_b_spec_id AS VARCHAR) AS method_b_spec_id
        FROM paired_mapping_metrics
        """,
    )
    logical = {
        _logical_pair_view_key(
            row["experiment_id"],
            row["case_id"],
            row["seed"],
            row["method_a_spec_id"],
            row["method_b_spec_id"],
        )
        for row in logical_rows
    }
    mapping = {
        _mapping_pair_view_key(
            row["experiment_id"],
            row["case_id"],
            row["seed"],
            row["transpile_spec_id"],
            row["method_a_spec_id"],
            row["method_b_spec_id"],
        )
        for row in mapping_rows
    }
    return logical, mapping


def _filtered(
    row: Mapping[str, Any], experiment_slugs: set[str], suites: set[str]
) -> bool:
    return (
        (not experiment_slugs or str(row["experiment_slug"]) in experiment_slugs)
        and (not suites or str(row["suite"]) in suites)
    )


def _method_pairs(
    methods: Iterable[tuple[str, str, str]],
    reference_methods: set[str],
    candidate_methods: set[str],
) -> list[tuple[tuple[str, str, str], tuple[str, str, str]]]:
    ordered = sorted(set(methods), key=lambda item: (item[1], item[2], item[0]))
    if reference_methods or candidate_methods:
        if not reference_methods or not candidate_methods:
            raise ValueError("reference_methods and candidate_methods must be provided together")
        return [
            (reference, candidate)
            for reference in ordered
            for candidate in ordered
            if reference[0] != candidate[0]
            and reference[1] in reference_methods
            and candidate[1] in candidate_methods
        ]
    return [
        (ordered[left], ordered[right])
        for left in range(len(ordered))
        for right in range(left + 1, len(ordered))
    ]


def _finite_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _function_candidate_counts(
    unit_functions: Mapping[tuple[str, int], str],
) -> Counter[str]:
    """Count observed synthesis seeds per function and reject duplicate cases."""

    seen: set[tuple[str, int]] = set()
    counts: Counter[str] = Counter()
    for (_case_id, seed), function_id in sorted(unit_functions.items()):
        key = (str(function_id), int(seed))
        if key in seen:
            raise RuntimeError(
                "multiple benchmark cases expose the same Boolean function and synthesis "
                f"seed in one analysis partition: {key}"
            )
        seen.add(key)
        counts[str(function_id)] += 1
    return counts


def _pair_units_and_functions(
    records: Mapping[tuple[str, tuple[str, int]], Mapping[str, Any]],
    reference_method_spec_id: str,
    candidate_method_spec_id: str,
    required_seeds: Sequence[int],
) -> tuple[list[tuple[str, int]], dict[tuple[str, int], str], Counter[str]]:
    """Build the exact case/seed grid for one method pair.

    With a required-seed contract, the function/case universe comes from every
    registered row in the current experiment/suite partition (not merely rows
    already attached to this method-spec pair) and is crossed with *every*
    required seed.  This makes fragmented method specs and absent cells explicit
    instead of silently reducing either the function or seed count.
    Without a contract, the historical observed-union sensitivity analysis is
    preserved.
    """

    method_ids = {reference_method_spec_id, candidate_method_spec_id}
    relevant = [
        (method_id, unit, row)
        for (method_id, unit), row in records.items()
        if method_id in method_ids
    ]
    if required_seeds:
        cases_by_function: dict[str, set[str]] = defaultdict(set)
        for (_method_id, (case_id, _seed)), row in records.items():
            cases_by_function[str(row["function_id"])].add(str(case_id))
        for function_id, case_ids in cases_by_function.items():
            if len(case_ids) != 1:
                raise RuntimeError(
                    "required-seed analysis needs one benchmark case per Boolean function; "
                    f"function {function_id} has cases {sorted(case_ids)}"
                )
        unit_functions = {
            (next(iter(case_ids)), int(seed)): function_id
            for function_id, case_ids in sorted(cases_by_function.items())
            for seed in required_seeds
        }
    else:
        units = sorted({unit for _method_id, unit, _row in relevant})
        unit_functions: dict[tuple[str, int], str] = {}
        for unit in units:
            function_ids = {
                str(row["function_id"])
                for method_id in (reference_method_spec_id, candidate_method_spec_id)
                if (row := records.get((method_id, unit))) is not None
            }
            if len(function_ids) != 1:
                raise RuntimeError(
                    f"case {unit[0]} seed {unit[1]} does not resolve to one Boolean "
                    f"function: {sorted(function_ids)}"
                )
            unit_functions[unit] = next(iter(function_ids))
    units = sorted(unit_functions)
    return units, unit_functions, _function_candidate_counts(unit_functions)


def percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def geometric_mean_nonnegative(values: Sequence[float]) -> float:
    """Geometric mean for finite non-negative ratios (zero is preserved)."""

    if not values:
        raise ValueError("geometric_mean_nonnegative requires values")
    clean = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0.0 for value in clean):
        raise ValueError("geometric mean ratios must be finite and non-negative")
    if any(value == 0.0 for value in clean):
        return 0.0
    return math.exp(math.fsum(math.log(value) for value in clean) / len(clean))


def deterministic_bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float],
    *,
    samples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if samples < 1:
        raise ValueError("bootstrap samples must be positive")
    if len(values) == 1:
        value = float(statistic(values))
        return value, value
    rng = random.Random(seed)
    size = len(values)
    estimates = [
        float(statistic([values[rng.randrange(size)] for _ in range(size)]))
        for _ in range(samples)
    ]
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def paired_rank_biserial(improvements: Sequence[float]) -> float:
    """Matched-pairs rank-biserial; positive values favour the candidate."""

    nonzero = [float(value) for value in improvements if float(value) != 0.0]
    if not nonzero:
        return 0.0
    ranks = rankdata([abs(value) for value in nonzero], method="average")
    positive = sum(float(rank) for rank, value in zip(ranks, nonzero) if value > 0.0)
    negative = sum(float(rank) for rank, value in zip(ranks, nonzero) if value < 0.0)
    denominator = positive + negative
    return 0.0 if denominator == 0.0 else (positive - negative) / denominator


def _wilcoxon(deltas: Sequence[float]) -> tuple[float | None, float | None, int]:
    nonzero = [float(value) for value in deltas if float(value) != 0.0]
    if not nonzero:
        return 0.0, 1.0, 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = wilcoxon(
            nonzero,
            zero_method=ZERO_METHOD,
            correction=False,
            alternative="two-sided",
            method="auto",
        )
    statistic_value = float(result.statistic)
    p_value = float(result.pvalue)
    if not (math.isfinite(statistic_value) and math.isfinite(p_value)):
        return None, None, len(nonzero)
    return statistic_value, p_value, len(nonzero)


def _stable_seed(base_seed: int, payload: Mapping[str, Any], suffix: str) -> int:
    digest = hashlib.sha256(
        (canonical_json(payload) + "\0" + suffix).encode("utf-8")
    ).digest()
    return int(base_seed) ^ int.from_bytes(digest[:8], "big")


def _exclusion(
    *,
    scope: str,
    context: Mapping[str, Any],
    reference: tuple[str, str, str],
    candidate: tuple[str, str, str],
    metric: str,
    unit: tuple[str, int],
    function_id: str | None,
    case_label: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "experiment_id": context["experiment_id"],
        "experiment_slug": context["experiment_slug"],
        "suite": context["suite"],
        "target_id": context.get("target_id"),
        "target_name": context.get("target_name"),
        "transpile_spec_id": context.get("transpile_spec_id"),
        "reference_method_spec_id": reference[0],
        "reference_method": reference[1],
        "candidate_method_spec_id": candidate[0],
        "candidate_method": candidate[1],
        "metric": metric,
        "exclusion_level": "seed",
        "function_id": function_id,
        "case_id": unit[0],
        "case_label": case_label,
        "seed": unit[1],
        "reason": reason,
    }


def _required_function_exclusion(
    *,
    scope: str,
    context: Mapping[str, Any],
    reference: tuple[str, str, str],
    candidate: tuple[str, str, str],
    metric: str,
    function_id: str,
    case_id: str,
    completeness: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "experiment_id": context["experiment_id"],
        "experiment_slug": context["experiment_slug"],
        "suite": context["suite"],
        "target_id": context.get("target_id"),
        "target_name": context.get("target_name"),
        "transpile_spec_id": context.get("transpile_spec_id"),
        "reference_method_spec_id": reference[0],
        "reference_method": reference[1],
        "candidate_method_spec_id": candidate[0],
        "candidate_method": candidate[1],
        "metric": metric,
        "exclusion_level": "function",
        "function_id": function_id,
        "case_id": case_id,
        "case_label": None,
        "seed": None,
        "reason": "function_incomplete_required_seed_set",
        "required_seeds": list(completeness["required_seeds"]),
        "metric_valid_seed_ids": list(completeness["metric_valid_seed_ids"]),
        "missing_or_invalid_required_seeds": list(
            completeness["missing_or_invalid_required_seeds"]
        ),
    }


def _logical_reason(reference: Mapping[str, Any] | None, candidate: Mapping[str, Any] | None) -> str | None:
    if reference is None and candidate is None:
        return "missing_both_cells"
    if reference is None:
        return "missing_reference_cell"
    if candidate is None:
        return "missing_candidate_cell"
    if reference.get("synthesis_attempt_id") is None:
        return "reference_no_canonical_success"
    if candidate.get("synthesis_attempt_id") is None:
        return "candidate_no_canonical_success"
    if reference.get("logical_verified") is not True:
        return "reference_logical_unverified"
    if candidate.get("logical_verified") is not True:
        return "candidate_logical_unverified"
    return None


def _mapping_verification_reason(
    reference_logical: Mapping[str, Any] | None,
    candidate_logical: Mapping[str, Any] | None,
    reference_mapping: Mapping[str, Any] | None,
    candidate_mapping: Mapping[str, Any] | None,
) -> str | None:
    logical_reason = _logical_reason(reference_logical, candidate_logical)
    if logical_reason is not None:
        return logical_reason
    if reference_mapping is None:
        return "missing_reference_mapping_attempt"
    if candidate_mapping is None:
        return "missing_candidate_mapping_attempt"
    if reference_mapping.get("mapping_attempt_id") is None:
        return "reference_mapping_no_canonical_success"
    if candidate_mapping.get("mapping_attempt_id") is None:
        return "candidate_mapping_no_canonical_success"
    if reference_mapping.get("mapping_verified") is not True:
        return "reference_mapping_unverified"
    if candidate_mapping.get("mapping_verified") is not True:
        return "candidate_mapping_unverified"
    return None


def _mapping_legality_reason(
    reference_mapping: Mapping[str, Any],
    candidate_mapping: Mapping[str, Any],
) -> str | None:
    for side, row in (("reference", reference_mapping), ("candidate", candidate_mapping)):
        target_violations = row.get("target_violation_count")
        direction_violations = row.get("direction_violation_count")
        if target_violations is None:
            return f"{side}_target_legality_missing"
        if direction_violations is None:
            return f"{side}_direction_legality_missing"
        if int(target_violations) != 0:
            return f"{side}_target_violation"
        if int(direction_violations) != 0:
            return f"{side}_direction_violation"
    return None


def _empty_summary(
    *,
    scope: str,
    context: Mapping[str, Any],
    reference: tuple[str, str, str],
    candidate: tuple[str, str, str],
    metric: str,
    n_candidate_keys: int,
    function_candidate_counts: Mapping[str, int],
    n_paired_view_verified_keys: int,
    n_base_eligible_pairs: int,
    exclusion_counts: Counter[str],
    required_seeds: Sequence[int],
    alpha: float,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "experiment_id": context["experiment_id"],
        "experiment_slug": context["experiment_slug"],
        "experiment_title": context["experiment_title"],
        "suite": context["suite"],
        "target_id": context.get("target_id"),
        "target_name": context.get("target_name", "logical" if scope == "logical" else None),
        "target_spec_hash": context.get("target_spec_hash"),
        "transpile_spec_id": context.get("transpile_spec_id"),
        "transpile_spec_name": context.get("transpile_spec_name"),
        "transpile_spec_hash": context.get("transpile_spec_hash"),
        "reference_method_spec_id": reference[0],
        "reference_method": reference[1],
        "reference_method_spec_hash": reference[2],
        "candidate_method_spec_id": candidate[0],
        "candidate_method": candidate[1],
        "candidate_method_spec_hash": candidate[2],
        "metric": metric,
        "lower_is_better": True,
        "delta_definition": (
            "within each Boolean function: median over strictly paired seeds of "
            "(candidate - reference); negative favours candidate"
        ),
        "relative_improvement_definition": (
            "within each Boolean function: median over strictly paired seeds of "
            "100 * (reference - candidate) / abs(reference); reference=0 omitted; "
            "positive favours candidate"
        ),
        "analysis_mode": (
            "required_seed_complete_case_primary"
            if required_seeds
            else "available_seed_sensitivity"
        ),
        "required_seeds_json": canonical_json(list(required_seeds)),
        "n_required_seeds": len(required_seeds),
        "inference_unit": "independent_boolean_function",
        "within_function_aggregation": "median_of_strict_case_seed_pairs",
        "n_candidate_keys": n_candidate_keys,
        "n_function_candidate_keys": len(function_candidate_counts),
        "n_paired_view_verified_keys": n_paired_view_verified_keys,
        "n_base_eligible_pairs": n_base_eligible_pairs,
        "n_seed_pairs_available": 0,
        "n_seed_pairs": 0,
        "n_pairs": 0,
        "n_functions_complete_observed": 0,
        "n_functions_incomplete_observed": len(function_candidate_counts),
        "n_functions_required_seed_complete": 0,
        "n_functions_required_seed_incomplete": (
            len(function_candidate_counts) if required_seeds else 0
        ),
        "seed_pairs_per_function_min": None,
        "seed_pairs_per_function_median": None,
        "seed_pairs_per_function_max": None,
        "function_seed_completeness_json": canonical_json(
            {
                function_id: {
                    "observed_candidate_seeds": int(count),
                    "metric_valid_paired_seeds": 0,
                    "metric_valid_seed_ids": [],
                    "required_seeds": list(required_seeds),
                    "missing_or_invalid_required_seeds": list(required_seeds),
                    "eligible_for_inference": False,
                    "complete_within_observed_keys": False,
                }
                for function_id, count in sorted(function_candidate_counts.items())
            }
        ),
        "n_relative_defined": 0,
        "n_excluded": n_candidate_keys,
        "win_count": 0,
        "tie_count": 0,
        "loss_count": 0,
        "reference_mean": None,
        "reference_median": None,
        "candidate_mean": None,
        "candidate_median": None,
        "mean_delta": None,
        "mean_delta_ci_low": None,
        "mean_delta_ci_high": None,
        "median_delta": None,
        "median_delta_ci_low": None,
        "median_delta_ci_high": None,
        "delta_iqr": None,
        "delta_std": None,
        "n_geometric_ratio_defined": 0,
        "geometric_mean_candidate_reference_ratio": None,
        "geometric_mean_candidate_reference_ratio_ci_low": None,
        "geometric_mean_candidate_reference_ratio_ci_high": None,
        "mean_relative_improvement_pct": None,
        "mean_relative_improvement_pct_ci_low": None,
        "mean_relative_improvement_pct_ci_high": None,
        "median_relative_improvement_pct": None,
        "median_relative_improvement_pct_ci_low": None,
        "median_relative_improvement_pct_ci_high": None,
        "wilcoxon_statistic": None,
        "wilcoxon_p_raw": None,
        "wilcoxon_zero_method": ZERO_METHOD,
        "wilcoxon_nonzero_pairs": 0,
        "rank_biserial": None,
        "rank_biserial_ci_low": None,
        "rank_biserial_ci_high": None,
        "holm_family": None,
        "holm_family_size": 0,
        "holm_p_adjusted": None,
        "holm_reject": False,
        "global_holm_family": "global_sensitivity_all_emitted_hypotheses",
        "global_holm_family_size": 0,
        "global_holm_p_adjusted": None,
        "global_holm_reject": False,
        "alpha": alpha,
        "exclusion_counts_json": canonical_json(dict(sorted(exclusion_counts.items()))),
    }


def _summarize_values(
    summary: dict[str, Any],
    seed_pairs: Sequence[Mapping[str, Any]],
    function_candidate_counts: Mapping[str, int],
    *,
    required_seeds: Sequence[int],
    bootstrap_samples: int,
    bootstrap_seed: int,
) -> dict[str, dict[str, Any]]:
    by_function: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen_function_seeds: set[tuple[str, int]] = set()
    for pair in seed_pairs:
        function_id = str(pair["function_id"])
        function_seed = (function_id, int(pair["seed"]))
        if function_seed in seen_function_seeds:
            raise RuntimeError(
                "duplicate case rows for the same Boolean function and synthesis seed; "
                f"cannot preserve an independent seed pairing unit: {function_seed}"
            )
        seen_function_seeds.add(function_seed)
        by_function[function_id].append(pair)

    required_set = set(int(seed) for seed in required_seeds)
    valid_seed_ids = {
        function_id: {int(row["seed"]) for row in rows}
        for function_id, rows in by_function.items()
    }
    completeness: dict[str, dict[str, Any]] = {}
    for function_id, expected_count in sorted(function_candidate_counts.items()):
        valid_ids = valid_seed_ids.get(function_id, set())
        missing_required = sorted(required_set - valid_ids)
        complete_observed = len(valid_ids) == int(expected_count)
        required_complete = bool(required_seeds) and not missing_required
        eligible = required_complete if required_seeds else bool(valid_ids)
        completeness[function_id] = {
            "observed_candidate_seeds": int(expected_count),
            "candidate_seed_slots": int(expected_count),
            "candidate_seed_slot_basis": (
                "required_seed_contract" if required_seeds else "database_observed_union"
            ),
            "metric_valid_paired_seeds": len(valid_ids),
            "metric_valid_seed_ids": sorted(valid_ids),
            "required_seeds": list(required_seeds),
            "missing_or_invalid_required_seeds": missing_required,
            "eligible_for_inference": eligible,
            "complete_within_observed_keys": complete_observed,
        }

    summary["n_seed_pairs_available"] = len(seed_pairs)
    summary["n_functions_complete_observed"] = sum(
        bool(item["complete_within_observed_keys"]) for item in completeness.values()
    )
    summary["n_functions_incomplete_observed"] = (
        len(function_candidate_counts) - summary["n_functions_complete_observed"]
    )
    if required_seeds:
        summary["n_functions_required_seed_complete"] = sum(
            bool(item["eligible_for_inference"]) for item in completeness.values()
        )
        summary["n_functions_required_seed_incomplete"] = (
            len(function_candidate_counts)
            - summary["n_functions_required_seed_complete"]
        )
    summary["function_seed_completeness_json"] = canonical_json(completeness)

    inference_function_ids = {
        function_id
        for function_id, item in completeness.items()
        if bool(item["eligible_for_inference"])
    }
    inference_pairs = [
        pair for pair in seed_pairs if str(pair["function_id"]) in inference_function_ids
    ]
    summary["n_seed_pairs"] = len(inference_pairs)
    summary["n_excluded"] = int(summary["n_candidate_keys"]) - len(inference_pairs)
    if not inference_pairs:
        return completeness

    inference_by_function: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pair in inference_pairs:
        inference_by_function[str(pair["function_id"])].append(pair)

    function_records: list[dict[str, float | str | None]] = []
    paired_counts: dict[str, int] = {}
    for function_id, rows in sorted(inference_by_function.items()):
        references_for_function = [float(row["reference"]) for row in rows]
        candidates_for_function = [float(row["candidate"]) for row in rows]
        seed_deltas = [candidate - reference for reference, candidate in zip(references_for_function, candidates_for_function)]
        seed_relatives = [
            100.0 * (reference - candidate) / abs(reference)
            for reference, candidate in zip(references_for_function, candidates_for_function)
            if reference != 0.0
        ]
        paired_counts[function_id] = len(rows)
        function_records.append(
            {
                "function_id": function_id,
                "reference": float(statistics.median(references_for_function)),
                "candidate": float(statistics.median(candidates_for_function)),
                "delta": float(statistics.median(seed_deltas)),
                "relative": (
                    float(statistics.median(seed_relatives)) if seed_relatives else None
                ),
            }
        )

    references = [float(row["reference"]) for row in function_records]
    candidates = [float(row["candidate"]) for row in function_records]
    deltas = [float(row["delta"]) for row in function_records]
    improvements = [-value for value in deltas]
    relatives = [
        float(row["relative"])
        for row in function_records
        if row["relative"] is not None
    ]
    ratios = [
        float(row["candidate"]) / float(row["reference"])
        for row in function_records
        if float(row["reference"]) > 0.0 and float(row["candidate"]) >= 0.0
    ]
    summary["n_pairs"] = len(function_records)
    summary["n_relative_defined"] = len(relatives)
    summary["win_count"] = sum(delta < 0.0 for delta in deltas)
    summary["tie_count"] = sum(delta == 0.0 for delta in deltas)
    summary["loss_count"] = sum(delta > 0.0 for delta in deltas)
    counts = list(paired_counts.values())
    summary["seed_pairs_per_function_min"] = min(counts)
    summary["seed_pairs_per_function_median"] = statistics.median(counts)
    summary["seed_pairs_per_function_max"] = max(counts)
    summary["reference_mean"] = statistics.mean(references)
    summary["reference_median"] = statistics.median(references)
    summary["candidate_mean"] = statistics.mean(candidates)
    summary["candidate_median"] = statistics.median(candidates)
    summary["mean_delta"] = statistics.mean(deltas)
    summary["median_delta"] = statistics.median(deltas)
    summary["delta_iqr"] = percentile(deltas, 0.75) - percentile(deltas, 0.25)
    summary["delta_std"] = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    summary["n_geometric_ratio_defined"] = len(ratios)
    summary["geometric_mean_candidate_reference_ratio"] = (
        geometric_mean_nonnegative(ratios) if ratios else None
    )
    summary["mean_relative_improvement_pct"] = statistics.mean(relatives) if relatives else None
    summary["median_relative_improvement_pct"] = statistics.median(relatives) if relatives else None
    statistic, p_value, nonzero_count = _wilcoxon(deltas)
    summary["wilcoxon_statistic"] = statistic
    summary["wilcoxon_p_raw"] = p_value
    summary["wilcoxon_nonzero_pairs"] = nonzero_count
    summary["rank_biserial"] = paired_rank_biserial(improvements)

    seed_payload = {
        field: summary[field]
        for field in (
            "scope",
            "experiment_id",
            "suite",
            "target_id",
            "transpile_spec_id",
            "reference_method_spec_id",
            "candidate_method_spec_id",
            "metric",
            "required_seeds_json",
        )
    }
    for values, stat, prefix in (
        (deltas, statistics.mean, "mean_delta"),
        (deltas, statistics.median, "median_delta"),
        (relatives, statistics.mean, "mean_relative_improvement_pct"),
        (relatives, statistics.median, "median_relative_improvement_pct"),
        (
            ratios,
            geometric_mean_nonnegative,
            "geometric_mean_candidate_reference_ratio",
        ),
        (improvements, paired_rank_biserial, "rank_biserial"),
    ):
        low, high = deterministic_bootstrap_ci(
            values,
            stat,
            samples=bootstrap_samples,
            seed=_stable_seed(bootstrap_seed, seed_payload, prefix),
        )
        summary[f"{prefix}_ci_low"] = low
        summary[f"{prefix}_ci_high"] = high
    return completeness


def _holm_family(row: Mapping[str, Any]) -> str:
    scope = str(row["scope"])
    metric = str(row["metric"])
    if scope == "logical":
        return "logical_primary" if metric in LOGICAL_PRIMARY_METRICS else "logical_secondary"
    if scope == "mapping":
        return "mapping_primary" if metric in MAPPING_PRIMARY_METRICS else "mapping_secondary"
    raise ValueError(f"unknown analysis scope {scope!r}")


def _apply_holm_indices(
    rows: list[dict[str, Any]],
    eligible: Sequence[int],
    *,
    alpha: float,
    size_field: str,
    adjusted_field: str,
    reject_field: str,
) -> None:
    ordered = sorted(
        eligible,
        key=lambda index: (
            float(rows[index]["wilcoxon_p_raw"]),
            str(rows[index]["experiment_id"]),
            str(rows[index]["suite"]),
            str(rows[index]["scope"]),
            str(rows[index]["target_id"]),
            str(rows[index]["reference_method_spec_id"]),
            str(rows[index]["candidate_method_spec_id"]),
            str(rows[index]["metric"]),
        ),
    )
    family_size = len(ordered)
    running = 0.0
    for rank, index in enumerate(ordered):
        adjusted = min(1.0, (family_size - rank) * float(rows[index]["wilcoxon_p_raw"]))
        running = max(running, adjusted)
        rows[index][size_field] = family_size
        rows[index][adjusted_field] = running
        rows[index][reject_field] = running <= alpha


def _apply_holm(rows: list[dict[str, Any]], alpha: float) -> None:
    by_family: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        family = _holm_family(row)
        row["holm_family"] = family
        if row["wilcoxon_p_raw"] is not None:
            by_family[family].append(index)
    for family in ("logical_primary", "mapping_primary", "logical_secondary", "mapping_secondary"):
        indices = by_family.get(family, [])
        _apply_holm_indices(
            rows,
            indices,
            alpha=alpha,
            size_field="holm_family_size",
            adjusted_field="holm_p_adjusted",
            reject_field="holm_reject",
        )
        family_size = len(indices)
        for row in rows:
            if row["holm_family"] == family and row["wilcoxon_p_raw"] is None:
                row["holm_family_size"] = family_size

    global_indices = [
        index for index, row in enumerate(rows) if row["wilcoxon_p_raw"] is not None
    ]
    _apply_holm_indices(
        rows,
        global_indices,
        alpha=alpha,
        size_field="global_holm_family_size",
        adjusted_field="global_holm_p_adjusted",
        reject_field="global_holm_reject",
    )
    global_size = len(global_indices)
    for row in rows:
        if row["wilcoxon_p_raw"] is None:
            row["global_holm_family_size"] = global_size


def _analyse_logical(
    logical_rows: Sequence[dict[str, Any]],
    paired_keys: set[tuple[Any, ...]],
    *,
    reference_methods: set[str],
    candidate_methods: set[str],
    required_seeds: Sequence[int],
    bootstrap_samples: int,
    bootstrap_seed: int,
    alpha: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in logical_rows:
        grouped[(str(row["experiment_id"]), str(row["suite"]))].append(row)

    summaries: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for _, rows in sorted(grouped.items()):
        context = rows[0]
        methods = {_method_key(row) for row in rows}
        records = {(_method_key(row)[0], _unit_key(row)): row for row in rows}
        for reference, candidate in _method_pairs(methods, reference_methods, candidate_methods):
            units, unit_functions, function_candidate_counts = _pair_units_and_functions(
                records,
                reference[0],
                candidate[0],
                required_seeds,
            )
            for metric in LOGICAL_METRICS:
                pairs: list[dict[str, Any]] = []
                reasons: Counter[str] = Counter()
                paired_view_count = 0
                base_eligible = 0
                for unit in units:
                    reference_row = records.get((reference[0], unit))
                    candidate_row = records.get((candidate[0], unit))
                    reason = _logical_reason(reference_row, candidate_row)
                    case_label = str((reference_row or candidate_row or {}).get("case_label") or "")
                    if reason is None:
                        view_key = _logical_pair_view_key(
                            str(context["experiment_id"]), unit[0], unit[1], reference[0], candidate[0]
                        )
                        if view_key not in paired_keys:
                            raise RuntimeError(f"canonical/paired logical view disagreement for {view_key}")
                        paired_view_count += 1
                        base_eligible += 1
                        reference_value = _finite_number(reference_row.get(metric))
                        candidate_value = _finite_number(candidate_row.get(metric))
                        if reference_value is None:
                            reason = "reference_metric_missing_or_nonfinite"
                        elif candidate_value is None:
                            reason = "candidate_metric_missing_or_nonfinite"
                        else:
                            pairs.append(
                                {
                                    "function_id": unit_functions[unit],
                                    "case_id": unit[0],
                                    "seed": unit[1],
                                    "reference": reference_value,
                                    "candidate": candidate_value,
                                }
                            )
                    if reason is not None:
                        reasons[reason] += 1
                        exclusions.append(
                            _exclusion(
                                scope="logical",
                                context=context,
                                reference=reference,
                                candidate=candidate,
                                metric=metric,
                                unit=unit,
                                function_id=unit_functions[unit],
                                case_label=case_label,
                                reason=reason,
                            )
                        )
                summary = _empty_summary(
                    scope="logical",
                    context=context,
                    reference=reference,
                    candidate=candidate,
                    metric=metric,
                    n_candidate_keys=len(units),
                    function_candidate_counts=function_candidate_counts,
                    n_paired_view_verified_keys=paired_view_count,
                    n_base_eligible_pairs=base_eligible,
                    exclusion_counts=reasons,
                    required_seeds=required_seeds,
                    alpha=alpha,
                )
                completeness = _summarize_values(
                    summary,
                    pairs,
                    function_candidate_counts,
                    required_seeds=required_seeds,
                    bootstrap_samples=bootstrap_samples,
                    bootstrap_seed=bootstrap_seed,
                )
                if required_seeds:
                    case_by_function = {
                        function_id: case_id
                        for (case_id, _seed), function_id in unit_functions.items()
                    }
                    for function_id, item in sorted(completeness.items()):
                        if not bool(item["eligible_for_inference"]):
                            reasons["function_incomplete_required_seed_set"] += 1
                            exclusions.append(
                                _required_function_exclusion(
                                    scope="logical",
                                    context=context,
                                    reference=reference,
                                    candidate=candidate,
                                    metric=metric,
                                    function_id=function_id,
                                    case_id=case_by_function[function_id],
                                    completeness=item,
                                )
                            )
                    summary["exclusion_counts_json"] = canonical_json(
                        dict(sorted(reasons.items()))
                    )
                summaries.append(summary)
    return summaries, exclusions


def _analyse_mapping(
    logical_rows: Sequence[dict[str, Any]],
    mapping_rows: Sequence[dict[str, Any]],
    paired_keys: set[tuple[Any, ...]],
    *,
    reference_methods: set[str],
    candidate_methods: set[str],
    required_seeds: Sequence[int],
    bootstrap_samples: int,
    bootstrap_seed: int,
    alpha: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    logical_by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in logical_rows:
        logical_by_group[(str(row["experiment_id"]), str(row["suite"]))].append(row)
    mapping_by_context: dict[
        tuple[str, str, str, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in mapping_rows:
        mapping_by_context[
            (
                str(row["experiment_id"]),
                str(row["suite"]),
                str(row["target_id"]),
                str(row["target_spec_hash"]),
                str(row["transpile_spec_id"]),
                str(row["transpile_spec_hash"]),
            )
        ].append(row)

    summaries: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for (experiment_id, suite), logical_group in sorted(logical_by_group.items()):
        methods = {_method_key(row) for row in logical_group}
        logical_records = {
            (_method_key(row)[0], _unit_key(row)): row for row in logical_group
        }
        for reference, candidate in _method_pairs(methods, reference_methods, candidate_methods):
            contexts = [
                rows
                for (
                    candidate_experiment,
                    candidate_suite,
                    _target_id,
                    _target_hash,
                    _transpile_id,
                    _transpile_hash,
                ), rows in sorted(mapping_by_context.items())
                if candidate_experiment == experiment_id
                and candidate_suite == suite
                and any(
                    _method_key(row)[0] in {reference[0], candidate[0]} for row in rows
                )
            ]
            for rows in contexts:
                context = rows[0]
                mapping_records = {
                    (_method_key(row)[0], _unit_key(row)): row for row in rows
                }
                # In required-seed mode, build the full function/seed grid from
                # logical cells so a mapping missing on *both* sides is visible.
                # Available-seed sensitivity retains the mapping-observed union.
                unit_source = logical_records if required_seeds else mapping_records
                units, unit_functions, function_candidate_counts = _pair_units_and_functions(
                    unit_source,
                    reference[0],
                    candidate[0],
                    required_seeds,
                )
                for metric in MAPPING_METRICS:
                    pairs: list[dict[str, Any]] = []
                    reasons: Counter[str] = Counter()
                    paired_view_count = 0
                    base_eligible = 0
                    for unit in units:
                        reference_logical = logical_records.get((reference[0], unit))
                        candidate_logical = logical_records.get((candidate[0], unit))
                        reference_mapping = mapping_records.get((reference[0], unit))
                        candidate_mapping = mapping_records.get((candidate[0], unit))
                        reason = _mapping_verification_reason(
                            reference_logical,
                            candidate_logical,
                            reference_mapping,
                            candidate_mapping,
                        )
                        case_label = str(
                            (
                                reference_mapping
                                or candidate_mapping
                                or reference_logical
                                or candidate_logical
                                or {}
                            ).get("case_label")
                            or ""
                        )
                        if reason is None:
                            view_key = _mapping_pair_view_key(
                                experiment_id,
                                unit[0],
                                unit[1],
                                str(context["transpile_spec_id"]),
                                reference[0],
                                candidate[0],
                            )
                            if view_key not in paired_keys:
                                raise RuntimeError(f"canonical/paired mapping view disagreement for {view_key}")
                            paired_view_count += 1
                            reason = _mapping_legality_reason(reference_mapping, candidate_mapping)
                            if reason is None:
                                base_eligible += 1
                                reference_value = _finite_number(reference_mapping.get(metric))
                                candidate_value = _finite_number(candidate_mapping.get(metric))
                                if reference_value is None:
                                    reason = "reference_metric_missing_or_nonfinite"
                                elif candidate_value is None:
                                    reason = "candidate_metric_missing_or_nonfinite"
                                else:
                                    pairs.append(
                                        {
                                            "function_id": unit_functions[unit],
                                            "case_id": unit[0],
                                            "seed": unit[1],
                                            "reference": reference_value,
                                            "candidate": candidate_value,
                                        }
                                    )
                        if reason is not None:
                            reasons[reason] += 1
                            exclusions.append(
                                _exclusion(
                                    scope="mapping",
                                    context=context,
                                    reference=reference,
                                    candidate=candidate,
                                    metric=metric,
                                    unit=unit,
                                    function_id=unit_functions[unit],
                                    case_label=case_label,
                                    reason=reason,
                                )
                            )
                    summary = _empty_summary(
                        scope="mapping",
                        context=context,
                        reference=reference,
                        candidate=candidate,
                        metric=metric,
                        n_candidate_keys=len(units),
                        function_candidate_counts=function_candidate_counts,
                        n_paired_view_verified_keys=paired_view_count,
                        n_base_eligible_pairs=base_eligible,
                        exclusion_counts=reasons,
                        required_seeds=required_seeds,
                        alpha=alpha,
                    )
                    completeness = _summarize_values(
                        summary,
                        pairs,
                        function_candidate_counts,
                        required_seeds=required_seeds,
                        bootstrap_samples=bootstrap_samples,
                        bootstrap_seed=bootstrap_seed,
                    )
                    if required_seeds:
                        case_by_function = {
                            function_id: case_id
                            for (case_id, _seed), function_id in unit_functions.items()
                        }
                        for function_id, item in sorted(completeness.items()):
                            if not bool(item["eligible_for_inference"]):
                                reasons["function_incomplete_required_seed_set"] += 1
                                exclusions.append(
                                    _required_function_exclusion(
                                        scope="mapping",
                                        context=context,
                                        reference=reference,
                                        candidate=candidate,
                                        metric=metric,
                                        function_id=function_id,
                                        case_id=case_by_function[function_id],
                                        completeness=item,
                                    )
                                )
                        summary["exclusion_counts_json"] = canonical_json(
                            dict(sorted(reasons.items()))
                        )
                    summaries.append(summary)
    return summaries, exclusions


def analyze_database(
    db_path: str | Path,
    *,
    experiment_slugs: Iterable[str] = (),
    suites: Iterable[str] = (),
    reference_methods: Iterable[str] = (),
    candidate_methods: Iterable[str] = (),
    required_seeds: Iterable[int] = (),
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Read and analyse a canonical experiment database without mutating it."""

    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    before_hash = _file_sha256(path)
    experiment_filter = set(experiment_slugs)
    suite_filter = set(suites)
    reference_filter = set(reference_methods)
    candidate_filter = set(candidate_methods)
    required_seed_values = [int(seed) for seed in required_seeds]
    if any(seed < 0 for seed in required_seed_values):
        raise ValueError("required seeds must be non-negative")
    if len(required_seed_values) != len(set(required_seed_values)):
        raise ValueError("required seeds must be unique")
    required_seed_tuple = tuple(sorted(required_seed_values))
    if bool(reference_filter) != bool(candidate_filter):
        raise ValueError("reference_methods and candidate_methods must be supplied together")

    with ExperimentDB(path, read_only=True) as database:
        logical_rows = [
            row
            for row in _load_logical_rows(database.connection)
            if _filtered(row, experiment_filter, suite_filter)
        ]
        mapping_rows = [
            row
            for row in _load_mapping_rows(database.connection)
            if _filtered(row, experiment_filter, suite_filter)
        ]
        logical_paired_keys, mapping_paired_keys = _load_paired_view_keys(database.connection)
        schema_version = database.schema_version

    after_hash = _file_sha256(path)
    if before_hash != after_hash:
        raise RuntimeError("read-only analysis changed the DuckDB content hash")
    logical_summaries, logical_exclusions = _analyse_logical(
        logical_rows,
        logical_paired_keys,
        reference_methods=reference_filter,
        candidate_methods=candidate_filter,
        required_seeds=required_seed_tuple,
        bootstrap_samples=bootstrap_samples,
        bootstrap_seed=bootstrap_seed,
        alpha=alpha,
    )
    mapping_summaries, mapping_exclusions = _analyse_mapping(
        logical_rows,
        mapping_rows,
        mapping_paired_keys,
        reference_methods=reference_filter,
        candidate_methods=candidate_filter,
        required_seeds=required_seed_tuple,
        bootstrap_samples=bootstrap_samples,
        bootstrap_seed=bootstrap_seed,
        alpha=alpha,
    )
    summaries = logical_summaries + mapping_summaries
    if not summaries:
        raise RuntimeError(
            "no method-pair summaries matched the requested experiment/suite/method filters"
        )
    summaries.sort(
        key=lambda row: (
            str(row["experiment_slug"]),
            str(row["suite"]),
            str(row["scope"]),
            str(row["target_name"]),
            str(row["transpile_spec_name"]),
            str(row["reference_method"]),
            str(row["reference_method_spec_hash"]),
            str(row["candidate_method"]),
            str(row["candidate_method_spec_hash"]),
            str(row["metric"]),
        )
    )
    _apply_holm(summaries, alpha)
    exclusions = logical_exclusions + mapping_exclusions
    exclusions.sort(
        key=lambda row: (
            str(row["experiment_slug"]),
            str(row["suite"]),
            str(row["scope"]),
            str(row["target_name"]),
            str(row["reference_method"]),
            str(row["candidate_method"]),
            str(row["metric"]),
            str(row.get("function_id")),
            str(row["case_label"]),
            row.get("seed") is None,
            -1 if row.get("seed") is None else int(row["seed"]),
            str(row.get("exclusion_level")),
            str(row["reason"]),
        )
    )
    frozen_hypothesis_families = {
        "logical_primary": {
            "competition_names": ["logic_T", "logic_CNOT"],
            "database_metrics": ["t_count", "cnot_count"],
        },
        "mapping_primary": {
            "competition_names": ["native_twoq_count", "mapped_depth"],
            "database_metrics": ["native_entangling_count", "mapped_depth"],
        },
        "logical_secondary": {
            "database_metrics": sorted(set(LOGICAL_METRICS) - LOGICAL_PRIMARY_METRICS),
        },
        "mapping_secondary": {
            "database_metrics": sorted(set(MAPPING_METRICS) - MAPPING_PRIMARY_METRICS),
        },
    }
    analysis_contract = {
        "strict_seed_pair_key": [
            "experiment_id",
            "suite",
            "case_id",
            "synthesis_seed",
        ],
        "mapping_pair_key_additions": [
            "target_id",
            "target_spec_hash",
            "transpile_spec_id",
            "transpile_spec_hash",
        ],
        "mapping_spec_semantics": (
            "content-addressed transpile spec includes target and the full compile config "
            "(transpiler seed, optimization, layout, routing, and HLS settings)"
        ),
        "within_function_aggregation": "median seed-paired difference",
        "required_seeds": list(required_seed_tuple),
        "analysis_mode": (
            "required_seed_complete_case_primary"
            if required_seed_tuple
            else "available_seed_sensitivity"
        ),
        "inference_unit": "independent Boolean function",
        "hypothesis_families": frozen_hypothesis_families,
    }
    experiment_partitions = sorted(
        {
            (str(row["experiment_id"]), str(row["experiment_slug"]), str(row["suite"]))
            for row in logical_rows
        }
    )
    return {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "database": str(path),
            "database_sha256_before": before_hash,
            "database_sha256_after": after_hash,
            "database_unchanged": before_hash == after_hash,
            "experiment_db_schema_version": schema_version,
            "opened_read_only": True,
            "source_views": [
                "canonical_logical_results",
                "canonical_mapping_results",
                "paired_logical_metrics",
                "paired_mapping_metrics",
            ],
            "experiment_partitions": [
                {
                    "experiment_id": experiment_id,
                    "experiment_slug": experiment_slug,
                    "suite": suite,
                }
                for experiment_id, experiment_slug, suite in experiment_partitions
            ],
        },
        "filters": {
            "experiment_slugs": sorted(experiment_filter),
            "suites": sorted(suite_filter),
            "reference_methods": sorted(reference_filter),
            "candidate_methods": sorted(candidate_filter),
            "required_seeds": list(required_seed_tuple),
        },
        "statistics": {
            "method_pair_orientation": (
                "explicit --reference-method/--candidate-method roles"
                if reference_filter
                else "all unordered method-spec pairs; lexicographically earlier (method_name, spec_hash, spec_id) is reference"
            ),
            "analysis_contract": analysis_contract,
            "analysis_contract_sha256": hashlib.sha256(
                canonical_json(analysis_contract).encode("utf-8")
            ).hexdigest(),
            "seed_pairing": (
                "strict experiment x suite x case x synthesis-seed; mapping additionally "
                "requires identical content-addressed target and transpile specs"
            ),
            "within_function_aggregation": (
                "median of valid strictly paired seed differences; one aggregate per "
                "independent Boolean function"
            ),
            "analysis_mode": (
                "required_seed_complete_case_primary"
                if required_seed_tuple
                else "available_seed_sensitivity"
            ),
            "required_seeds": list(required_seed_tuple),
            "required_seed_complete_case_rule": (
                "when required_seeds is non-empty, a Boolean function enters inference only "
                "if every required seed is a finite, verified candidate/reference pair in "
                "the same analysis scope and exact mapping context"
            ),
            "summary_count_semantics": {
                "n_seed_pairs_available": (
                    "finite verified strict seed pairs before the required-seed complete-case "
                    "function filter"
                ),
                "n_seed_pairs": "seed pairs belonging to functions admitted to inference",
                "n_pairs": "Boolean functions admitted to inference",
                "n_excluded": (
                    "candidate seed slots not used by inference; function-level exclusion "
                    "records additionally explain complete-case drops"
                ),
            },
            "inference_unit": "independent Boolean function",
            "cross_experiment_pooling": False,
            "formal_claim_partition_rule": (
                "each experiment_id x suite is analysed separately; formal claims require "
                "one consolidated frozen experiment rather than stitching partial slugs"
            ),
            "metric_direction": "all metrics lower-is-better",
            "delta": (
                "per-function median over paired seeds of candidate - reference; "
                "negative favours candidate"
            ),
            "relative_improvement": (
                "per-function median over paired seeds of 100 * (reference - candidate) / "
                "abs(reference); reference=0 observations omitted; positive favours candidate"
            ),
            "wilcoxon": {
                "alternative": "two-sided",
                "zero_method": ZERO_METHOD,
                "zero_policy": "exact zero deltas are discarded from signed-rank statistic and retained as descriptive ties",
                "method": "scipy auto",
            },
            "rank_biserial": (
                "paired signed-rank effect over Boolean-function aggregates; positive "
                "favours candidate"
            ),
            "bootstrap": {
                "method": (
                    "deterministic percentile bootstrap over independent Boolean-function "
                    "aggregates (seeds are never resampled as independent observations)"
                ),
                "samples": bootstrap_samples,
                "seed": bootstrap_seed,
                "confidence_level": 0.95,
            },
            "multiple_testing": {
                "method": "Holm step-down family-wise error control",
                "frozen_families": frozen_hypothesis_families,
                "family_rule": (
                    "logical_primary and mapping_primary are corrected separately; "
                    "logical_secondary and mapping_secondary are each corrected separately"
                ),
                "primary_adjusted_columns": [
                    "holm_family",
                    "holm_family_size",
                    "holm_p_adjusted",
                    "holm_reject",
                ],
                "global_sensitivity_columns": [
                    "global_holm_family",
                    "global_holm_family_size",
                    "global_holm_p_adjusted",
                    "global_holm_reject",
                ],
                "alpha": alpha,
            },
        },
        "coverage_boundary": {
            "quality_statistics_only": True,
            "experiment_partition_count": len(experiment_partitions),
            "cross_experiment_pooling": False,
            "formal_claim_requires_consolidated_frozen_experiment": True,
            "logical_candidate_keys": (
                "every required seed crossed with each Boolean function/case visible in "
                "the current experiment/suite partition"
                if required_seed_tuple
                else "union of registered synthesis cells for the compared method specs"
            ),
            "mapping_candidate_keys": (
                "every required seed crossed with each logical Boolean function/case in the "
                "current experiment/suite partition, "
                "within each exact content-addressed mapping context visible for either method"
                if required_seed_tuple
                else "union of exact content-addressed transpile specs attempted by either "
                "compared method on the canonical synthesis attempt"
            ),
            "observed_seed_completeness": (
                "required-seed completeness is enforced within every emitted experiment/suite/"
                "scope/mapping partition, but the function and mapping-context universe remains "
                "limited to what is visible in this database; it is not planned-run coverage"
                if required_seed_tuple
                else "summary completeness is relative only to the union of keys observable in "
                "this database, and is not planned-run coverage"
            ),
            "timeouts_and_planned_coverage_status": "not_inferred_from_this_analysis_database",
            "requires_external_recovery_manifest": True,
            "external_manifest_requirement": (
                "report timeout counts, worker failures, interrupted rows, filtered-success "
                "ingestion, and planned-grid coverage from the append-only raw/recovery "
                "manifest; a success-only DuckDB cannot recover those denominators"
            ),
            "unobservable": (
                "unregistered cells, unattempted transpile specs, and failures omitted by a "
                "success-filtered ingestion are not inferable and are never claimed as coverage"
            ),
            "inclusion": "canonical success, non-adverse verification on both sides, zero known target/direction violations for mapping, and finite metric values",
        },
        "summary_row_count": len(summaries),
        "exclusion_row_count": len(exclusions),
        "summaries": summaries,
        "exclusions": exclusions,
    }


def write_tidy_csv(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in SUMMARY_FIELDS})


def write_json(path: str | Path, result: Mapping[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_required_seeds(value: str) -> tuple[int, ...]:
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(not part for part in parts):
        raise argparse.ArgumentTypeError(
            "--required-seeds must be a comma-separated non-empty integer list"
        )
    try:
        seeds = [int(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--required-seeds values must be integers"
        ) from exc
    if any(seed < 0 for seed in seeds):
        raise argparse.ArgumentTypeError("--required-seeds values must be non-negative")
    if len(seeds) != len(set(seeds)):
        raise argparse.ArgumentTypeError("--required-seeds values must be unique")
    return tuple(sorted(seeds))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--experiment", action="append", default=[], metavar="SLUG")
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--reference-method", action="append", default=[])
    parser.add_argument("--candidate-method", action="append", default=[])
    parser.add_argument(
        "--required-seeds",
        type=parse_required_seeds,
        default=(),
        metavar="S1,S2,...",
        help=(
            "complete-case seed contract for the primary analysis (for example 7,17,29); "
            "omit for the available-seed sensitivity analysis"
        ),
    )
    parser.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAP_SAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--alpha", type=float, default=ALPHA)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = analyze_database(
        args.db,
        experiment_slugs=args.experiment,
        suites=args.suite,
        reference_methods=args.reference_method,
        candidate_methods=args.candidate_method,
        required_seeds=args.required_seeds,
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
        alpha=args.alpha,
    )
    write_tidy_csv(args.csv, result["summaries"])
    write_json(args.json, result)
    print(
        f"wrote {result['summary_row_count']} summary rows and "
        f"{result['exclusion_row_count']} explicit exclusions"
    )
    print(f"csv={Path(args.csv).resolve()}")
    print(f"json={Path(args.json).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
