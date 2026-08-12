#!/usr/bin/env python3
"""Integration tests for fixed-budget scheduling inside the real NMCTS loop."""
from __future__ import annotations

import sys
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.anf_utils import truth_table_from_anf
from src.factor_plan import (
    SearchConfig,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey
from src.resource_model import ResourceWeights
from src.search.mcts_scheduler import DiversitySchedulerConfig
from src.sshr_lib.bool_func import BooleanFunction


PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
TERMS = frozenset(
    [
        0b0011,
        0b0101,
        0b1001,
        0b0111,
        0b1011,
        0b1101,
        0b1110,
        0b1111,
    ]
)


def _search_config() -> SearchConfig:
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        candidate_top_k=12,
        max_factor_ancilla=3,
        max_factor_size=4,
        gate_mode="logical_and",
    )


def _scheduler_config(method: str = "top_b", **overrides) -> DiversitySchedulerConfig:
    values = {
        "method": method,
        "budget_requested": 3,
        "pool_size": 6,
        "min_candidates": 4,
        "max_depth": 0,
        "seed": 17,
    }
    values.update(overrides)
    return DiversitySchedulerConfig(**values)


def test_scheduler_off_is_exactly_compatible() -> None:
    config = _search_config()
    legacy = NeuralMCTSSolver(config, simulations=10, seed=3).solve(TERMS)
    explicit_off_solver = NeuralMCTSSolver(
        config,
        simulations=10,
        seed=3,
        scheduler_config=DiversitySchedulerConfig(method="off"),
    )
    explicit_off = explicit_off_solver.solve(TERMS)

    assert explicit_off == legacy
    assert explicit_off_solver.scheduler_records == []
    assert explicit_off_solver.scheduler_summary()["scheduler_decisions"] == 0


def test_selected_edges_are_independent_and_budget_fair() -> None:
    solver = NeuralMCTSSolver(
        _search_config(),
        simulations=0,
        seed=5,
        scheduler_config=_scheduler_config(),
    )
    root_key = StateKey(TERMS, 0, 0)

    for expected_evaluations in range(1, 4):
        solver._simulate(root_key)
        root = solver.nodes[root_key]
        selected = root.admitted_indices
        assert selected is not None and len(selected) == 3
        assert sum(root.stats[index].visits for index in selected) == expected_evaluations
        assert sum(stat.visits for stat in root.stats.values()) == expected_evaluations

    root = solver.nodes[root_key]
    assert all(root.stats[index].visits == 1 for index in root.admitted_indices or ())
    excluded = set(range(len(root.actions))) - set(root.admitted_indices or ())
    assert excluded
    assert all(root.stats[index].visits == 0 for index in excluded)


def test_build_best_cannot_reintroduce_an_excluded_edge() -> None:
    solver = NeuralMCTSSolver(
        _search_config(),
        simulations=1,
        seed=7,
        scheduler_config=_scheduler_config(),
    )
    solver.solve(TERMS)
    root_key = StateKey(TERMS, 0, 0)
    root = solver.nodes[root_key]
    admitted = set(root.admitted_indices or ())
    excluded_index = min(set(range(len(root.actions))) - admitted)

    # If _build_best accidentally scans all actions, this fabricated score
    # would force the excluded edge into the returned root plan.
    root.stats[excluded_index].visits = 1
    root.stats[excluded_index].q = -1e12
    rebuilt = solver._build_best(root_key)

    assert rebuilt.kind == "direct" or rebuilt.factor in {
        root.actions[index].factor for index in admitted
    }
    assert rebuilt.factor != root.actions[excluded_index].factor


def test_qaoa_scheduler_changes_the_search_and_preserves_oracle_semantics() -> None:
    config = _search_config()
    solver = NeuralMCTSSolver(
        config,
        simulations=4,
        seed=11,
        scheduler_config=_scheduler_config(
            "qaoa",
            qaoa_mode="ideal",
            qaoa_p=1,
            qaoa_optimizer_restarts=2,
            qaoa_optimizer_steps=3,
        ),
    )
    plan = solver.solve(TERMS)
    root = solver.nodes[StateKey(TERMS, 0, 0)]
    record = solver.scheduler_records[0]["diagnostics"]

    assert len(root.admitted_indices or ()) == 3
    assert len(root.admitted_indices or ()) < len(root.actions)
    assert record["qaoa_attempted"] is True
    assert record["qaoa_succeeded"] is True
    assert record["node_id"] == solver._state_id(root.key)
    assert len(record["selected_action_signatures"]) == 3
    assert solver.scheduler_summary()["selected_action_evaluations"] == 4

    plan_check = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(plan, 4, config.max_factor_ancilla)
    circuit_check = verify_circuit_anf(circuit, 4, TERMS)
    bf = BooleanFunction(4, truth_table_from_anf(4, TERMS))
    assert plan_check.ok
    assert circuit_check.ok
    assert verify_oracle(circuit, bf)


def test_scheduler_decision_is_persistent_per_node() -> None:
    solver = NeuralMCTSSolver(
        _search_config(),
        simulations=0,
        seed=13,
        scheduler_config=_scheduler_config("random"),
    )
    root_key = StateKey(TERMS, 0, 0)
    for _ in range(8):
        solver._simulate(root_key)

    assert len(solver.scheduler_records) == 1
    root = solver.nodes[root_key]
    assert root.scheduler_decision is not None
    assert tuple(root.scheduler_decision.selected_indices) == root.admitted_indices
