#!/usr/bin/env python3
"""Tests for the dependency-free fixed-budget diversity scheduler."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.search.diversity_scheduler import (
    audit_qubo_bitstrings,
    build_qubo_model,
    qubo_energy,
    schedule_diverse_candidates,
    selection_objective,
)


def zeros(size: int) -> list[list[float]]:
    return [[0.0 for _ in range(size)] for _ in range(size)]


def test_budget_requested_must_be_positive_integer() -> None:
    for invalid in (0, -1):
        with pytest.raises(ValueError, match="> 0"):
            schedule_diverse_candidates([1.0], [[0.0]], invalid)
    for invalid in (True, 1.5, "1"):
        with pytest.raises(TypeError, match="positive integer"):
            schedule_diverse_candidates([1.0], [[0.0]], invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("method", ["random", "top-B", "greedy", "exact"])
def test_empty_pool_returns_empty_selection(method: str) -> None:
    result = schedule_diverse_candidates([], [], 3, method=method, seed=7)
    assert result.selected_indices == ()
    assert result.bitstring == ()
    assert result.diagnostics.candidate_count == 0
    assert result.diagnostics.budget_requested == 3
    assert result.diagnostics.budget_effective == 0
    assert result.diagnostics.status == "skipped_no_candidates"
    assert not result.diagnostics.solver_invoked


@pytest.mark.parametrize("pool_size,budget", [(2, 4), (3, 3)])
@pytest.mark.parametrize("method", ["random", "top_b", "greedy", "exact"])
def test_budget_covering_pool_selects_every_candidate(
    pool_size: int, budget: int, method: str
) -> None:
    result = schedule_diverse_candidates(
        list(range(pool_size)), zeros(pool_size), budget, method=method
    )
    assert result.selected_indices == tuple(range(pool_size))
    assert result.diagnostics.budget_effective == pool_size
    assert result.diagnostics.status == "skipped_budget_covers_pool"
    assert not result.diagnostics.solver_invoked


@pytest.mark.parametrize("method", ["random", "top_b", "greedy", "exact"])
def test_k_greater_than_budget_selects_exactly_effective_budget(method: str) -> None:
    result = schedule_diverse_candidates(
        [4.0, 3.0, 2.0, 1.0], zeros(4), 2, method=method, seed=11
    )
    assert len(result.selected_indices) == 2
    assert sum(result.bitstring) == 2
    assert result.diagnostics.budget_effective == 2
    assert result.diagnostics.status == "selected"
    assert result.diagnostics.solver_invoked


def test_top_b_is_utility_only_while_greedy_and_exact_use_diversity() -> None:
    utilities = [10.0, 9.0, 8.0]
    redundancy = [
        [0.0, 10.0, 0.0],
        [10.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    ]
    top = schedule_diverse_candidates(
        utilities, redundancy, 2, method="top_b", redundancy_weight=1.0
    )
    greedy = schedule_diverse_candidates(
        utilities, redundancy, 2, method="greedy", redundancy_weight=1.0
    )
    exact = schedule_diverse_candidates(
        utilities, redundancy, 2, method="exact", redundancy_weight=1.0
    )

    assert top.selected_indices == (0, 1)
    assert greedy.selected_indices == (0, 2)
    assert exact.selected_indices == (0, 2)
    assert exact.diagnostics.utility_sum == 18.0
    assert exact.diagnostics.pair_redundancy_sum == 0.0
    assert exact.diagnostics.objective == 18.0
    assert exact.diagnostics.evaluations == math.comb(3, 2)


def test_all_deterministic_ties_prefer_lowest_indices() -> None:
    utilities = [1.0, 1.0, 1.0, 1.0]
    redundancy = zeros(4)
    for method in ("top_b", "greedy", "exact"):
        result = schedule_diverse_candidates(
            utilities, redundancy, 2, method=method
        )
        assert result.selected_indices == (0, 1), method
        assert result.diagnostics.selection_order == (0, 1), method
        assert result.diagnostics.tie_break == "lowest_candidate_index"


def test_random_is_reproducible_for_a_seed_and_reports_canonical_subset() -> None:
    first = schedule_diverse_candidates(
        list(range(10)), zeros(10), 4, method="random", seed=202609
    )
    second = schedule_diverse_candidates(
        list(range(10)), zeros(10), 4, method="random-B", seed=202609
    )
    assert first.selected_indices == second.selected_indices
    assert first.diagnostics.selection_order == second.diagnostics.selection_order
    assert first.selected_indices == tuple(sorted(first.selected_indices))
    assert first.diagnostics.seed == 202609


def test_objective_counts_each_pair_once_and_ignores_diagonal() -> None:
    utilities = [5.0, 4.0, 3.0]
    redundancy = [
        [999.0, 0.5, 0.25],
        [0.5, 999.0, 0.75],
        [0.25, 0.75, 999.0],
    ]
    assert selection_objective(
        utilities, redundancy, [0, 1, 2], redundancy_weight=2.0
    ) == pytest.approx(12.0 - 2.0 * (0.5 + 0.25 + 0.75))


@pytest.mark.parametrize(
    "utilities,redundancy,error",
    [
        ([1.0, float("nan")], [[0.0, 0.0], [0.0, 0.0]], "finite"),
        ([1.0, 2.0], [[0.0]], "square"),
        ([1.0, 2.0], [[0.0, 0.2], [0.3, 0.0]], "symmetric"),
        ([1.0, 2.0], [[0.0, 0.2], [0.2, float("inf")]], "finite"),
    ],
)
def test_problem_validation_rejects_nonfinite_nonsquare_or_asymmetric_data(
    utilities, redundancy, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        schedule_diverse_candidates(utilities, redundancy, 1)


def test_qubo_model_matches_direct_identity_for_every_bitstring() -> None:
    utilities = [1.5, -0.25, 0.75]
    redundancy = [
        [7.0, 0.2, 0.7],
        [0.2, 8.0, -0.1],
        [0.7, -0.1, 9.0],
    ]
    audit = audit_qubo_bitstrings(
        utilities,
        redundancy,
        2,
        redundancy_weight=0.6,
        rho=10.0,
    )

    assert len(audit.records) == 2**3
    assert audit.diagnostics.total_bitstrings == 8
    assert audit.diagnostics.feasible_bitstrings == math.comb(3, 2)
    assert audit.diagnostics.energy_identity_holds
    assert audit.diagnostics.feasible_ordering_matches
    assert audit.diagnostics.max_identity_error < 1e-9
    for record in audit.records:
        assert record.polynomial_energy == pytest.approx(record.identity_energy)


def test_qubo_constant_offset_and_public_energy_are_preserved() -> None:
    utilities = [3.0, 2.0]
    redundancy = [[0.0, 0.5], [0.5, 0.0]]
    model = build_qubo_model(
        utilities, redundancy, 1, redundancy_weight=2.0, rho=7.0
    )
    assert model.constant == 7.0
    for bits in ((0, 0), (0, 1), (1, 0), (1, 1)):
        assert model.energy(bits) == pytest.approx(
            qubo_energy(
                bits,
                utilities,
                redundancy,
                1,
                redundancy_weight=2.0,
                rho=7.0,
            )
        )


def test_audit_detects_insufficient_and_sufficient_cardinality_penalty() -> None:
    utilities = [10.0, 9.0, 8.0]
    redundancy = zeros(3)
    insufficient = audit_qubo_bitstrings(utilities, redundancy, 1, rho=0.1)
    sufficient = audit_qubo_bitstrings(utilities, redundancy, 1, rho=100.0)

    assert not insufficient.diagnostics.penalty_sufficient
    assert not insufficient.diagnostics.all_global_minima_feasible
    assert sufficient.diagnostics.penalty_sufficient
    assert sufficient.diagnostics.all_global_minima_feasible
    assert sufficient.diagnostics.global_minimum_bitstrings == ((1, 0, 0),)


def test_empty_qubo_audit_covers_the_unique_empty_assignment() -> None:
    audit = audit_qubo_bitstrings([], [], 0, rho=1.0)
    assert len(audit.records) == 1
    assert audit.records[0].bitstring == ()
    assert audit.records[0].feasible
    assert audit.diagnostics.penalty_sufficient
    assert audit.diagnostics.feasible_optimal_bitstrings == ((),)


def test_exhaustive_audit_has_an_explicit_size_guard() -> None:
    with pytest.raises(ValueError, match="exceeds max_candidates"):
        audit_qubo_bitstrings([0.0] * 4, zeros(4), 2, rho=1.0, max_candidates=3)


def main() -> int:
    """Allow the test module to serve as a lightweight standalone gate."""

    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    main()
