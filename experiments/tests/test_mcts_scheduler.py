#!/usr/bin/env python3
"""Contract tests for the MCTS-facing utility--diversity scheduler."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import src.search.mcts_scheduler as scheduler_module
from src.search.mcts_scheduler import (
    DiversitySchedulerConfig,
    MCTSDiversityScheduler,
    action_redundancy_matrix,
)
from src.search.qaoa_scheduler import QAOAResult


@dataclass(frozen=True)
class _Action:
    """Small FactorAction-shaped fixture; only group/rest define redundancy."""

    group: frozenset[int]
    rest: frozenset[int]


def _disjoint_actions(count: int) -> list[_Action]:
    return [
        _Action(frozenset({index}), frozenset({100 + index}))
        for index in range(count)
    ]


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"method": "unknown"}, "unsupported scheduler method"),
        ({"qaoa_mode": "hardware"}, "unsupported qaoa_mode"),
        ({"budget_requested": 0}, "positive integer"),
        ({"pool_size": True}, "positive integer"),
        ({"min_candidates": 1.5}, "positive integer"),
        ({"max_depth": -1}, "non-negative integer"),
        ({"qaoa_optimizer_steps": -1}, "non-negative integer"),
        ({"redundancy_weight": -0.1}, ">= 0"),
        ({"redundancy_alpha": 1.1}, "lie in"),
        ({"utility_clip": 0.0}, "> 0"),
        ({"qaoa_noise_bitflip_probability": -0.1}, "lie in"),
        ({"qaoa_penalty_rho": math.inf}, "finite and > 0"),
        ({"method": "qaoa", "pool_size": 13}, "pool_size <= 12"),
    ],
)
def test_configuration_rejects_invalid_values(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        DiversitySchedulerConfig(**overrides)  # type: ignore[arg-type]


def test_configuration_normalizes_aliases_and_is_json_ready() -> None:
    config = DiversitySchedulerConfig(method=" TOP-B ", qaoa_mode="IDEAL")

    assert config.method == "top_b"
    assert config.qaoa_mode == "ideal"
    assert config.to_dict()["budget_requested"] == 4


def test_action_redundancy_combines_group_and_rest_jaccard() -> None:
    actions = [
        _Action(frozenset({1, 2}), frozenset({8})),
        _Action(frozenset({2, 3}), frozenset({8, 9})),
        _Action(frozenset({4}), frozenset({10})),
    ]

    matrix = action_redundancy_matrix(actions, alpha=0.6)

    # 0.6 * J({1,2},{2,3}) + 0.4 * J({8},{8,9}) = 0.4.
    assert matrix[0][1] == pytest.approx(0.4)
    assert matrix[1][0] == pytest.approx(0.4)
    assert matrix[0][2] == matrix[2][0] == 0.0
    assert matrix[1][2] == matrix[2][1] == 0.0
    assert all(matrix[index][index] == 0.0 for index in range(3))


@pytest.mark.parametrize("alpha", [-0.1, 1.1, float("nan")])
def test_action_redundancy_rejects_invalid_alpha(alpha: float) -> None:
    with pytest.raises(ValueError, match="alpha must lie"):
        action_redundancy_matrix(_disjoint_actions(2), alpha=alpha)


@pytest.mark.parametrize("method", ["random", "top_b", "greedy", "exact"])
def test_classical_schedulers_preserve_exact_effective_budget(method: str) -> None:
    decision = MCTSDiversityScheduler(
        DiversitySchedulerConfig(
            method=method,
            budget_requested=2,
            pool_size=4,
            redundancy_weight=0.8,
        )
    ).select(_disjoint_actions(4), [4.0, 3.0, 2.0, 1.0], decision_seed=17)

    assert len(decision.selected_indices) == 2
    assert len(set(decision.selected_indices)) == 2
    assert decision.diagnostics["budget_requested"] == 2
    assert decision.diagnostics["budget_effective"] == 2
    assert decision.diagnostics["status"] == "selected"
    assert decision.diagnostics["qaoa_attempted"] is False


def test_exact_classical_scheduler_uses_diversity_not_only_top_utilities() -> None:
    actions = [
        _Action(frozenset({1, 2}), frozenset({8})),
        _Action(frozenset({1, 2}), frozenset({8})),
        _Action(frozenset({3}), frozenset({9})),
    ]
    config = DiversitySchedulerConfig(
        method="exact",
        budget_requested=2,
        pool_size=3,
        redundancy_weight=1.0,
        redundancy_alpha=1.0,
    )

    decision = MCTSDiversityScheduler(config).select(
        actions, [1.0, 0.95, 0.90], decision_seed=0
    )

    assert decision.selected_indices == (0, 2)
    assert decision.diagnostics["objective"] == pytest.approx(1.9)


@pytest.mark.parametrize(
    "mode, expected_sampling_mode, expect_counts",
    [
        ("ideal", "ideal_statevector", False),
        ("shot", "shots", True),
    ],
)
def test_qaoa_ideal_and_shot_paths_execute_and_keep_exact_budget(
    mode: str, expected_sampling_mode: str, expect_counts: bool
) -> None:
    config = DiversitySchedulerConfig(
        method="qaoa",
        budget_requested=1,
        pool_size=3,
        min_candidates=2,
        qaoa_mode=mode,
        qaoa_shots=256,
        qaoa_optimizer_restarts=2,
        qaoa_optimizer_steps=4,
    )

    decision = MCTSDiversityScheduler(config).select(
        _disjoint_actions(3), [1.0, 0.2, -0.2], decision_seed=3
    )
    qaoa = decision.diagnostics["qaoa"]

    assert len(decision.selected_indices) == 1
    assert decision.diagnostics["status"] == "qaoa_selected"
    assert decision.diagnostics["qaoa_eligible"] is True
    assert decision.diagnostics["qaoa_attempted"] is True
    assert decision.diagnostics["qaoa_succeeded"] is True
    assert decision.diagnostics["qaoa_fallback"] is False
    assert qaoa["diagnostics"]["sampling_mode"] == expected_sampling_mode
    assert bool(qaoa["counts"]) is expect_counts
    if expect_counts:
        assert sum(qaoa["counts"].values()) == 256
    else:
        assert qaoa["diagnostics"]["returned_bitstring_was_measured"] is False


@pytest.mark.parametrize(
    "count, budget, minimum, reason",
    [
        (2, 2, 2, "skipped_budget_covers_pool"),
        (3, 1, 4, "below_min_candidates"),
    ],
)
def test_ineligible_qaoa_is_not_reported_as_attempted_or_failed(
    count: int, budget: int, minimum: int, reason: str
) -> None:
    config = DiversitySchedulerConfig(
        method="qaoa",
        budget_requested=budget,
        pool_size=max(count, minimum),
        min_candidates=minimum,
    )

    decision = MCTSDiversityScheduler(config).select(
        _disjoint_actions(count), list(reversed(range(count))), decision_seed=9
    )

    assert len(decision.selected_indices) == min(count, budget)
    assert decision.diagnostics["status"] == "qaoa_not_invoked"
    assert decision.diagnostics["not_invoked_reason"] == reason
    assert decision.diagnostics["qaoa_eligible"] is False
    assert decision.diagnostics["qaoa_attempted"] is False
    assert decision.diagnostics["qaoa_succeeded"] is False
    assert decision.diagnostics["qaoa_fallback"] is False
    assert decision.diagnostics["fallback_reason"] is None


def test_qaoa_exception_falls_back_to_greedy_with_explicit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_qaoa(*_args, **_kwargs):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(scheduler_module, "run_qaoa", fail_qaoa)
    config = DiversitySchedulerConfig(
        method="qaoa",
        budget_requested=2,
        pool_size=4,
        min_candidates=3,
    )

    decision = MCTSDiversityScheduler(config).select(
        _disjoint_actions(4), [4.0, 3.0, 2.0, 1.0], decision_seed=5
    )

    assert decision.selected_indices == (0, 1)
    assert decision.diagnostics["status"] == "qaoa_fallback"
    assert decision.diagnostics["qaoa_attempted"] is True
    assert decision.diagnostics["qaoa_succeeded"] is False
    assert decision.diagnostics["qaoa_fallback"] is True
    assert decision.diagnostics["fallback_solver"] == "greedy"
    assert decision.diagnostics["fallback_reason"] == (
        "RuntimeError: backend unavailable"
    )


def test_qaoa_repair_is_disclosed_separately_from_raw_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def repaired_qaoa(*_args, **_kwargs) -> QAOAResult:
        return QAOAResult(
            bitstring=(1, 0, 0),
            energy=-1.0,
            probability=0.75,
            sampled_bitstring=(0, 0, 0),
            sampled_energy=0.0,
            is_feasible=True,
            repaired=True,
            gammas=(0.1,),
            betas=(0.2,),
            counts={"000": 96, "100": 32},
            diagnostics={
                "qaoa_circuit_executed": True,
                "direct_qaoa": False,
                "repair_applied": True,
                "selection_mode": "repaired_qaoa_sample",
                "returned_bitstring_was_measured": False,
            },
        )

    monkeypatch.setattr(scheduler_module, "run_qaoa", repaired_qaoa)
    config = DiversitySchedulerConfig(
        method="qaoa",
        budget_requested=1,
        pool_size=3,
        min_candidates=2,
        qaoa_mode="shot",
        qaoa_shots=128,
    )

    decision = MCTSDiversityScheduler(config).select(
        _disjoint_actions(3), [1.0, 0.5, 0.25], decision_seed=11
    )

    assert decision.selected_indices == (0,)
    assert decision.diagnostics["status"] == "qaoa_selected"
    assert decision.diagnostics["qaoa_succeeded"] is True
    assert decision.diagnostics["qaoa_repaired"] is True
    assert decision.diagnostics["qaoa_fallback"] is False
    assert decision.diagnostics["raw_qaoa_indices"] == []
    assert decision.diagnostics["selected_indices"] == [0]
    assert decision.diagnostics["qaoa"]["diagnostics"]["direct_qaoa"] is False


def test_select_rejects_length_mismatch_and_nonfinite_utilities() -> None:
    scheduler = MCTSDiversityScheduler(
        DiversitySchedulerConfig(method="greedy", pool_size=2)
    )
    with pytest.raises(ValueError, match="same length"):
        scheduler.select(_disjoint_actions(2), [1.0], decision_seed=0)
    with pytest.raises(ValueError, match="finite"):
        scheduler.select(
            _disjoint_actions(2), [1.0, float("nan")], decision_seed=0
        )
