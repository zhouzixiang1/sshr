#!/usr/bin/env python3
"""Contract tests for the checksum-bound E6 frozen scheduling case."""

from __future__ import annotations

from dataclasses import replace
import itertools

import pytest

import e6.shared_scheduler as scheduler_module
from e6.frozen_case import (
    HASH_SEMANTICS,
    TOP_K_RULE,
    build_frozen_shared_case,
    schedule_frozen_case,
    validate_frozen_shared_case,
)
from e6.shared_oracle import (
    MonomialSharedAction,
    VectorANF,
    permute_action_outputs,
)
from e6.shared_scheduler import SharedSchedulerConfig
from src.search.qaoa_scheduler import QAOAResult


CHECKPOINT_SHA = "a" * 64


def _vector_and_actions():
    vector = VectorANF(
        3,
        (
            frozenset({0b011, 0b100}),
            frozenset({0b011, 0b001}),
            frozenset({0b101, 0b010}),
            frozenset({0b101, 0b110}),
        ),
    )
    actions = (
        MonomialSharedAction(0b011, (0, 1)),
        MonomialSharedAction(0b101, (2, 3)),
    )
    return vector, actions


def _config(*, budget: int = 1, shots: int = 64) -> SharedSchedulerConfig:
    return SharedSchedulerConfig(
        method="greedy",
        budget_requested=budget,
        qaoa_seed=609,
        qaoa_shots=shots,
        qaoa_optimizer_restarts=1,
        qaoa_optimizer_steps=2,
        qaoa_max_variables=12,
        audit_max_variables=12,
    )


def _case():
    vector, actions = _vector_and_actions()
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(),
        raw_utilities=(1.0, 2.0),
        learned_utilities=(0.5, 0.6),
    )


def test_candidate_input_order_is_canonical_but_output_relabel_changes_exact_sha() -> None:
    vector, actions = _vector_and_actions()
    forward = build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(),
        raw_utilities=(1.0, 2.0),
        learned_utilities=(0.5, 0.6),
    )
    reversed_input = build_frozen_shared_case(
        vector,
        tuple(reversed(actions)),
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(),
        raw_utilities=(2.0, 1.0),
        learned_utilities=(0.6, 0.5),
    )

    assert forward.case_sha256 == reversed_input.case_sha256
    assert forward.source_pool_sha256 == reversed_input.source_pool_sha256
    assert forward.candidate_pool_sha256 == reversed_input.candidate_pool_sha256
    assert forward.actions == reversed_input.actions == (actions[1], actions[0])
    assert forward.binding_dict()["top_k_rule"] == TOP_K_RULE
    assert forward.hash_semantics == HASH_SEMANTICS
    assert "non_semantic" in forward.hash_semantics.candidate_input_order

    permutation = (1, 2, 3, 0)  # old output -> new output
    relabelled_vector = vector.permute_outputs(permutation)
    relabelled_actions = tuple(
        permute_action_outputs(action, permutation, output_count=4)
        for action in actions
    )
    relabelled = build_frozen_shared_case(
        relabelled_vector,
        tuple(reversed(relabelled_actions)),
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(),
        raw_utilities=(2.0, 1.0),
        learned_utilities=(0.6, 0.5),
    )

    assert relabelled.vector_sha256 != forward.vector_sha256
    assert relabelled.candidate_pool_sha256 != forward.candidate_pool_sha256
    assert relabelled.case_sha256 != forward.case_sha256
    assert "exact_hashes_change" in relabelled.hash_semantics.output_relabeling
    assert "equivariance_is_a_separate_model_property" in (
        relabelled.hash_semantics.output_relabeling
    )


def test_scorer_is_called_once_before_common_top_k() -> None:
    vector, actions = _vector_and_actions()

    class CountingScorer:
        calls = 0

        def score_actions(self, _vector, received, *, weights):
            self.calls += 1
            assert tuple(received) == actions
            return [float(action.monomial) for action in received]

    scorer = CountingScorer()
    case = build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(),
        raw_utilities=(1.0, 2.0),
        scorer=scorer,
        candidate_cap=1,
    )

    assert scorer.calls == 1
    assert case.source_candidate_count == 2
    assert case.candidate_cap_effective == 1
    assert case.actions == (actions[1],)


def test_greedy_exact_qaoa_share_every_exact_frozen_binding() -> None:
    case = _case()
    results = {
        method: schedule_frozen_case(case, method)
        for method in ("greedy", "exact", "qaoa")
    }
    bindings = [result.diagnostics["frozen_case"] for result in results.values()]

    assert all(result.diagnostics["frozen_case_validated"] for result in results.values())
    assert len({binding["case_sha256"] for binding in bindings}) == 1
    for field in (
        "vector_sha256",
        "source_pool_sha256",
        "candidate_pool_sha256",
        "source_raw_utility_sha256",
        "source_learned_utility_sha256",
        "raw_utility_sha256",
        "learned_utility_sha256",
        "redundancy_sha256",
        "conflict_sha256",
        "qubo_sha256",
        "checkpoint_sha256",
        "budget_requested",
        "budget_effective",
        "augmented_variable_count",
    ):
        assert len({str(binding[field]) for binding in bindings}) == 1, field
    assert {result.diagnostics["method_requested"] for result in results.values()} == {
        "greedy",
        "exact",
        "qaoa",
    }
    assert results["qaoa"].diagnostics["qaoa_attempted"] is True


@pytest.mark.parametrize(
    "mutate",
    [
        lambda case: replace(case, learned_utility_sha256="0" * 64),
        lambda case: replace(
            case,
            ranked_learned_utilities=(99.0,) + case.ranked_learned_utilities[1:],
        ),
        lambda case: replace(case, qubo_sha256="0" * 64),
        lambda case: replace(case, checkpoint_sha256="b" * 64),
        lambda case: replace(case, ranked_actions=tuple(reversed(case.ranked_actions))),
    ],
)
def test_any_frozen_component_tamper_fails_closed(mutate) -> None:
    tampered = mutate(_case())
    with pytest.raises((ValueError, RuntimeError), match="frozen|binding|canonical"):
        validate_frozen_shared_case(tampered)
    with pytest.raises((ValueError, RuntimeError), match="frozen|binding|canonical"):
        schedule_frozen_case(tampered, "exact")


def test_common_candidate_cap_enforces_qaoa_twelve_variable_ceiling() -> None:
    # Fifteen pairwise-disjoint actions are present.  With B=2, the common
    # QAOA-safe pool is capped at K=10 so K+B=12 for every method.
    vector = VectorANF(
        5,
        tuple(frozenset({index // 2 + 1}) for index in range(30)),
    )
    actions = tuple(
        MonomialSharedAction(index + 1, (2 * index, 2 * index + 1))
        for index in range(15)
    )
    case = build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(budget=2),
        raw_utilities=tuple(float(index) for index in range(15)),
        learned_utilities=tuple(float(index) for index in range(15)),
        candidate_cap=100,
    )

    assert case.source_candidate_count == 15
    assert case.qaoa_safe_candidate_cap == 10
    assert case.candidate_cap_effective == len(case.actions) == 10
    assert case.budget_effective == 2
    assert case.augmented_variable_count == case.qubo.variable_count == 12
    assert tuple(action.monomial for action in case.actions) == tuple(
        range(15, 5, -1)
    )


def test_empty_candidate_case_is_preserved_for_all_three_methods() -> None:
    vector = VectorANF(3, (frozenset({0b001}), frozenset({0b010})))
    case = build_frozen_shared_case(
        vector,
        (),
        checkpoint_sha256=CHECKPOINT_SHA,
        config=_config(budget=2),
        raw_utilities=(),
        learned_utilities=(),
    )

    assert case.source_candidate_count == case.candidate_cap_effective == 0
    assert case.actions == case.raw_utilities == case.learned_utilities == ()
    assert case.budget_effective == case.augmented_variable_count == 0
    assert case.qubo.variable_count == 0
    for method in ("greedy", "exact", "qaoa"):
        result = schedule_frozen_case(case, method)
        assert result.selected_indices == ()
        assert result.augmented_bitstring == ()
        assert result.diagnostics["method_executed"] == "not_invoked_no_candidates"
        assert result.diagnostics["qaoa_execution_class"] == "not_invoked"
        assert result.diagnostics["frozen_case"]["case_sha256"] == case.case_sha256


def _fake_qaoa(
    linear,
    quadratic,
    *,
    feasible_sample: bool,
    **kwargs,
) -> QAOAResult:
    energies = []
    for bits in itertools.product((0, 1), repeat=kwargs["num_variables"]):
        energies.append(
            sum(linear.get(index, 0.0) * bit for index, bit in enumerate(bits))
            + sum(
                value * bits[left] * bits[right]
                for (left, right), value in quadratic.items()
            )
        )
    offset = min(energies)
    scale = max(energies) - offset
    if scale <= 1e-15:
        scale = 1.0
    bits = (
        (1,) + (0,) * (kwargs["num_variables"] - 1)
        if feasible_sample
        else (0,) * kwargs["num_variables"]
    )
    key = "".join(str(bit) for bit in bits)
    return QAOAResult(
        bitstring=bits,
        energy=0.0,
        probability=1.0,
        sampled_bitstring=bits,
        sampled_energy=0.0,
        is_feasible=feasible_sample,
        repaired=False,
        gammas=(0.1,),
        betas=(0.2,),
        counts={key: kwargs["shots"]},
        diagnostics={
            "qaoa_circuit_executed": True,
            "direct_qaoa": True,
            "repair_applied": False,
            "execution_mode": "direct_qaoa_statevector",
            "selection_mode": "direct_qaoa_sample",
            "objective_source": "qubo",
            "infeasible_penalty": None,
            "cost_offset": offset,
            "cost_scale": scale,
        },
    )


def test_wrapper_preserves_direct_repair_and_fallback_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case()

    monkeypatch.setattr(
        scheduler_module,
        "run_qaoa",
        lambda linear, quadratic, **kwargs: _fake_qaoa(
            linear, quadratic, feasible_sample=True, **kwargs
        ),
    )
    direct = schedule_frozen_case(case, "qaoa")
    assert direct.diagnostics["qaoa_execution_class"] == "direct_unrepaired"
    assert direct.diagnostics["qaoa_direct"] is True
    assert direct.diagnostics["qaoa_repaired"] is False
    assert direct.diagnostics["qaoa_fallback"] is False

    monkeypatch.setattr(
        scheduler_module,
        "run_qaoa",
        lambda linear, quadratic, **kwargs: _fake_qaoa(
            linear, quadratic, feasible_sample=False, **kwargs
        ),
    )
    repaired = schedule_frozen_case(case, "qaoa")
    assert repaired.diagnostics["qaoa_execution_class"] == "direct_repaired"
    assert repaired.diagnostics["qaoa_direct"] is False
    assert repaired.diagnostics["qaoa_repaired"] is True
    assert repaired.diagnostics["qaoa_fallback"] is False
    assert repaired.diagnostics["qaoa"]["postselection"]["repair_method"] == (
        "classical_exact_feasible_projection"
    )

    def fail(*_args, **_kwargs):
        raise RuntimeError("frozen-case backend unavailable")

    monkeypatch.setattr(scheduler_module, "run_qaoa", fail)
    fallback = schedule_frozen_case(case, "qaoa")
    assert fallback.diagnostics["qaoa_execution_class"] == "fallback"
    assert fallback.diagnostics["qaoa_direct"] is False
    assert fallback.diagnostics["qaoa_repaired"] is False
    assert fallback.diagnostics["qaoa_fallback"] is True
    assert fallback.diagnostics["fallback_reason"] == (
        "RuntimeError: frozen-case backend unavailable"
    )
    assert {
        result.diagnostics["frozen_case"]["case_sha256"]
        for result in (direct, repaired, fallback)
    } == {case.case_sha256}
