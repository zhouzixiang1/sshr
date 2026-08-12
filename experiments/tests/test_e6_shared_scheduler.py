#!/usr/bin/env python3
"""Contract tests for the isolated E6 conflict-aware shared scheduler."""

from __future__ import annotations

from dataclasses import replace
import itertools

import pytest

import e6.shared_scheduler as scheduler_module
from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    VectorANF,
    emit_shared_oracle,
    enumerate_monomial_shared_actions,
    verify_vector_oracle_semantics,
)
from e6.shared_scheduler import (
    SharedActionScheduler,
    SharedSchedulerConfig,
    SharedUtilityWeights,
    action_conflict_matrix,
    action_redundancy_matrix,
    audit_dummy_fixed_cardinality_qubo,
    build_dummy_fixed_cardinality_qubo,
    build_shared_scheduling_problem,
    program_resource_summary,
    schedule_shared_actions,
    shared_action_utility_breakdown,
)
from src.search.qaoa_scheduler import QAOAResult


def _pool():
    return (
        MonomialSharedAction(0b00111, (0, 1)),
        MonomialSharedAction(0b00111, (1, 2)),
        MonomialSharedAction(0b01011, (0, 1)),
    )


def _disjoint_pool():
    return (
        MonomialSharedAction(0b00111, (0, 1)),
        MonomialSharedAction(0b01011, (2, 3)),
        MonomialSharedAction(0b10101, (4, 5)),
    )


def _fake_qaoa_result(
    bitstring: tuple[int, ...],
    counts: dict[str, int],
    *,
    phase_diagnostics: dict[str, object] | None = None,
) -> QAOAResult:
    diagnostics = {
        "qaoa_circuit_executed": True,
        "direct_qaoa": True,
        "repair_applied": False,
        "execution_mode": "direct_qaoa_statevector",
        "selection_mode": "direct_qaoa_sample",
    }
    diagnostics.update(phase_diagnostics or {})
    return QAOAResult(
        bitstring=bitstring,
        energy=0.0,
        probability=max(counts.values()) / sum(counts.values()),
        sampled_bitstring=bitstring,
        sampled_energy=0.0,
        is_feasible=True,
        repaired=False,
        gammas=(0.1,),
        betas=(0.2,),
        counts=counts,
        diagnostics=diagnostics,
    )


def test_shared_utility_compares_direct_and_compute_fanout_uncompute() -> None:
    profitable = shared_action_utility_breakdown(
        MonomialSharedAction(0b111, (0, 1, 2))
    )
    unprofitable = shared_action_utility_breakdown(
        MonomialSharedAction(0b001, (0, 1))
    )
    semi_affine = shared_action_utility_breakdown(
        SemiAffineSharedAction(0b001, 0b110, True, (0, 1, 2))
    )

    assert profitable.direct_score > profitable.shared_score
    assert profitable.utility > 0.0
    assert unprofitable.utility < 0.0
    assert semi_affine.expanded_term_count == 3
    assert semi_affine.explicit_ancilla == 2
    assert semi_affine.metric == "abstract_logical_mct_proxy_not_hardware"
    assert semi_affine.explicit_ancilla_charge == 0.0


def test_conflict_and_soft_redundancy_are_distinct() -> None:
    actions = _pool()
    conflicts = action_conflict_matrix(actions)
    redundancy = action_redundancy_matrix(actions, alpha=0.7)

    # Actions 0/1 cover (output 1, monomial 0b111) twice: hard conflict.
    assert conflicts[0][1] and conflicts[1][0]
    assert not conflicts[0][2]
    # Same polynomial plus one-of-three target intersection gives 0.8.
    assert redundancy[0][1] == pytest.approx(0.8)
    # Different polynomial but identical targets retains soft target redundancy.
    assert redundancy[0][2] == pytest.approx(0.3)
    assert all(not conflicts[index][index] for index in range(3))
    assert all(redundancy[index][index] == 0.0 for index in range(3))


@pytest.mark.parametrize("method", ["greedy", "exact"])
def test_classical_schedulers_respect_conflicts_and_use_dummy_slots(method: str) -> None:
    actions = _pool()
    result = schedule_shared_actions(
        actions,
        config=SharedSchedulerConfig(method=method, budget_requested=2),
        utilities=(4.0, 3.9, 3.0),
    )

    assert result.selected_indices == (0, 2)
    assert result.dummy_selected == 0
    assert sum(result.augmented_bitstring) == 2
    assert result.diagnostics["footprint_conflict_free"] is True
    assert result.diagnostics["fixed_cardinality_holds"] is True
    assert result.diagnostics["performance_evidence"] is False

    # A negative second action is represented by a selected zero-utility dummy.
    with_dummy = schedule_shared_actions(
        _disjoint_pool(),
        config=SharedSchedulerConfig(method=method, budget_requested=2),
        utilities=(2.0, -0.5, -1.0),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )
    assert with_dummy.selected_indices == (0,)
    assert with_dummy.dummy_selected == 1
    assert sum(with_dummy.augmented_bitstring) == 2


def test_dummy_fixed_cardinality_qubo_audits_every_two_power_k_assignment() -> None:
    problem = build_shared_scheduling_problem(
        _pool(),
        2,
        utilities=(4.0, 3.9, 3.0),
        redundancy_weight=0.25,
        redundancy_alpha=0.7,
    )
    model = build_dummy_fixed_cardinality_qubo(problem)
    audit = audit_dummy_fixed_cardinality_qubo(model)

    assert model.real_candidate_count == 3
    assert model.dummy_count == model.budget_effective == 2
    assert model.variable_count == 5
    assert audit.diagnostics.total_bitstrings == audit.diagnostics.expected_bitstrings == 32
    assert len(audit.records) == 1 << model.variable_count
    assert audit.diagnostics.energy_identity_holds
    assert audit.diagnostics.phase_energy_identity_holds
    assert audit.diagnostics.phase_constant_offset_holds
    assert audit.diagnostics.analytic_penalty_bounds_hold
    assert audit.diagnostics.all_global_minima_feasible
    assert audit.diagnostics.exact_selection_matches_global_minima
    assert audit.diagnostics.penalty_sufficient
    assert audit.diagnostics.feasible_optimal_real_selections == ((0, 2),)
    assert all(
        record.cardinality == 2 and record.conflicts == 0
        for record in audit.records
        if record.bitstring in audit.diagnostics.global_minimum_bitstrings
    )
    assert all(
        record.phase_energy == pytest.approx(
            record.backend_coefficient_energy, rel=0.0, abs=1e-12
        )
        for record in audit.records
    )


def test_qaoa_adapter_uses_existing_direct_backend_and_fixed_cardinality() -> None:
    result = SharedActionScheduler(
        SharedSchedulerConfig(
            method="direct_qaoa",
            budget_requested=1,
            qaoa_shots=512,
            qaoa_p=1,
            qaoa_optimizer_restarts=2,
            qaoa_optimizer_steps=6,
            qaoa_seed=609,
        )
    ).select(
        _disjoint_pool(),
        utilities=(2.0, 0.5, -0.5),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )

    assert result.selected_indices == (0,)
    assert sum(result.augmented_bitstring) == 1
    assert result.diagnostics["qaoa_attempted"] is True
    assert result.diagnostics["qaoa_backend_succeeded"] is True
    assert result.diagnostics["qaoa_succeeded"] is True
    assert result.diagnostics["qaoa_direct"] is True
    assert result.diagnostics["qaoa_fallback"] is False
    assert result.diagnostics["qaoa_execution_class"] == "direct_unrepaired"
    qaoa = result.diagnostics["qaoa"]
    assert qaoa["diagnostics"]["qaoa_circuit_executed"] is True
    assert qaoa["diagnostics"]["direct_qaoa"] is True
    assert qaoa["repaired"] is False
    assert qaoa["diagnostics"]["execution_mode"] == "direct_qaoa_statevector"
    assert sum(qaoa["counts"].values()) == 512
    assert qaoa["phase_input"]["feasibility_oracle_passed_to_backend"] is False
    assert qaoa["phase_input"]["repair_function_passed_to_backend"] is False
    assert qaoa["postselection"]["selection_class"] == (
        "direct_feasible_measured_qaoa_sample"
    )


def test_qaoa_phase_backend_receives_only_frozen_qubo_coefficients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = scheduler_module.run_qaoa
    captured: dict[str, object] = {}

    def capture(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = dict(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(scheduler_module, "run_qaoa", capture)
    result = schedule_shared_actions(
        _disjoint_pool(),
        config=SharedSchedulerConfig(
            method="qaoa",
            budget_requested=1,
            qaoa_shots=256,
            qaoa_optimizer_restarts=2,
            qaoa_optimizer_steps=4,
            qaoa_seed=610,
        ),
        utilities=(2.0, 0.5, -0.5),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )

    kwargs = captured["kwargs"]
    assert "objective" not in kwargs
    assert "feasible" not in kwargs
    assert "repair" not in kwargs
    assert len(captured["args"]) == 2  # linear and quadratic QUBO only
    assert result.diagnostics["qaoa_backend_succeeded"] is True
    assert result.diagnostics["qubo_audit"]["phase_energy_identity_holds"] is True


def test_no_feasible_measured_qaoa_sample_is_repaired_and_accounted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def infeasible_qaoa(linear, quadratic, **kwargs):
        # K_real=3 plus one dummy.  Cardinality zero is infeasible.
        energies = [
            sum(linear.get(index, 0.0) * bit for index, bit in enumerate(bits))
            + sum(
                value * bits[left] * bits[right]
                for (left, right), value in quadratic.items()
            )
            for bits in itertools.product((0, 1), repeat=kwargs["num_variables"])
        ]
        offset = min(energies)
        scale = max(energies) - offset
        if scale <= 1e-15:
            scale = 1.0
        return _fake_qaoa_result(
            (0, 0, 0, 0),
            {"0000": 128},
            phase_diagnostics={
                "objective_source": "qubo",
                "infeasible_penalty": None,
                "cost_offset": offset,
                "cost_scale": scale,
            },
        )

    monkeypatch.setattr(scheduler_module, "run_qaoa", infeasible_qaoa)
    result = schedule_shared_actions(
        _disjoint_pool(),
        config=SharedSchedulerConfig(
            method="qaoa", budget_requested=1, qaoa_shots=128
        ),
        utilities=(2.0, 0.5, -0.5),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )

    assert result.selected_indices == (0,)
    assert result.augmented_bitstring == (1, 0, 0, 0)
    assert result.diagnostics["qaoa_backend_succeeded"] is True
    assert result.diagnostics["qaoa_succeeded"] is True
    assert result.diagnostics["qaoa_direct"] is False
    assert result.diagnostics["qaoa_repaired"] is True
    assert result.diagnostics["qaoa_fallback"] is False
    assert result.diagnostics["qaoa_execution_class"] == "direct_repaired"
    assert result.diagnostics["method_executed"] == (
        "qaoa_no_feasible_sample_exact_repair"
    )
    postselection = result.diagnostics["qaoa"]["postselection"]
    assert postselection["feasible_observed_bitstrings"] == 0
    assert postselection["returned_bitstring_was_measured"] is False
    assert postselection["repair_method"] == "classical_exact_feasible_projection"


def test_qaoa_failure_is_explicit_before_greedy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_qaoa(*_args, **_kwargs):
        raise RuntimeError("development backend unavailable")

    monkeypatch.setattr(scheduler_module, "run_qaoa", fail_qaoa)
    result = schedule_shared_actions(
        _disjoint_pool(),
        config=SharedSchedulerConfig(method="qaoa", budget_requested=1),
        utilities=(2.0, 0.5, -0.5),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )

    assert result.selected_indices == (0,)
    assert result.diagnostics["qaoa_attempted"] is True
    assert result.diagnostics["qaoa_backend_succeeded"] is False
    assert result.diagnostics["qaoa_succeeded"] is False
    assert result.diagnostics["qaoa_fallback"] is True
    assert result.diagnostics["qaoa_execution_class"] == "fallback"
    assert result.diagnostics["method_executed"] == "qaoa_fallback_greedy"
    assert result.diagnostics["fallback_reason"] == (
        "RuntimeError: development backend unavailable"
    )


def test_analytic_penalty_lower_bounds_and_failed_audit_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    problem = build_shared_scheduling_problem(
        _pool(), 2, utilities=(4.0, 3.9, 3.0)
    )
    valid_model = build_dummy_fixed_cardinality_qubo(problem)
    bound = valid_model.objective_magnitude_bound

    with pytest.raises(ValueError, match="rho override is analytically insufficient"):
        build_dummy_fixed_cardinality_qubo(
            problem, rho=bound, conflict_penalty=valid_model.conflict_penalty
        )
    with pytest.raises(
        ValueError, match="conflict_penalty override is analytically insufficient"
    ):
        build_dummy_fixed_cardinality_qubo(
            problem, rho=valid_model.rho, conflict_penalty=bound
        )

    valid_audit = audit_dummy_fixed_cardinality_qubo(valid_model)

    def failed_audit(*_args, **_kwargs):
        return replace(
            valid_audit,
            diagnostics=replace(
                valid_audit.diagnostics,
                analytic_penalty_bounds_hold=False,
                penalty_sufficient=False,
            ),
        )

    monkeypatch.setattr(
        scheduler_module, "audit_dummy_fixed_cardinality_qubo", failed_audit
    )
    with pytest.raises(RuntimeError, match="failed closed"):
        schedule_shared_actions(
            _pool(),
            config=SharedSchedulerConfig(method="exact", budget_requested=2),
            utilities=(4.0, 3.9, 3.0),
        )


def test_empty_pool_and_budget_above_real_pool_keep_dummy_contract_total() -> None:
    empty = schedule_shared_actions(
        (), config=SharedSchedulerConfig(method="exact", budget_requested=5)
    )
    assert empty.selected_indices == ()
    assert empty.augmented_bitstring == ()
    assert empty.dummy_selected == 0
    assert empty.diagnostics["budget_effective"] == 0
    assert empty.diagnostics["qubo_audit"]["total_bitstrings"] == 1

    actions = _disjoint_pool()[:2]
    result = schedule_shared_actions(
        actions,
        config=SharedSchedulerConfig(method="exact", budget_requested=5),
        utilities=(2.0, -0.5),
        redundancy=((0.0, 0.0), (0.0, 0.0)),
    )
    assert result.diagnostics["budget_requested"] == 5
    assert result.diagnostics["budget_effective"] == 2
    assert len(result.augmented_bitstring) == 4  # two real plus B_eff dummies
    assert result.selected_indices == (0,)
    assert result.dummy_selected == 1
    assert sum(result.augmented_bitstring) == 2


def test_partial_fanout_scheduler_to_emitter_is_correct_for_every_x_and_y() -> None:
    # Full sharing of term 0b0111 conflicts with the semi-affine action on
    # outputs 2/3.  The target-mask action on outputs 0/1 unlocks both blocks.
    vector = VectorANF(
        4,
        (
            frozenset({0b0111}),
            frozenset({0b0111}),
            frozenset({0b0111, 0b1011}),
            frozenset({0b0111, 0b1011}),
        ),
    )
    monomial_actions = enumerate_monomial_shared_actions(vector)
    full = next(
        action
        for action in monomial_actions
        if action.monomial == 0b0111 and action.target_mask == 0b1111
    )
    partial = next(
        action
        for action in monomial_actions
        if action.monomial == 0b0111 and action.target_mask == 0b0011
    )
    semi = SemiAffineSharedAction(0b0011, 0b1100, False, (2, 3))
    pool = (full, partial, semi)
    result = schedule_shared_actions(
        pool,
        config=SharedSchedulerConfig(method="exact", budget_requested=2),
        utilities=(10.0, 8.0, 7.0),
        redundancy=((0.0, 0.0, 0.0),) * 3,
    )

    assert result.selected_indices == (1, 2)
    program = emit_shared_oracle(vector, tuple(pool[index] for index in result.selected_indices))
    verification = verify_vector_oracle_semantics(program)
    resources = program_resource_summary(
        program, weights=SharedUtilityWeights(ancilla=2.0)
    )
    assert verification.ok
    assert verification.assignments_checked == 1 << (4 + 4)
    assert program.residual_outputs == (frozenset(),) * 4
    assert resources.explicit_workspace_peak == 2
    assert resources.explicit_workspace_peak_charge == 4.0
    assert resources.mct_decomposition_implicit_ancillas_included is False
    assert resources.exact_hardware_resource_claim is False


def test_audit_and_qaoa_variable_guards_fail_closed() -> None:
    actions = tuple(
        MonomialSharedAction((1 << (index + 2)) | 0b11, (2 * index, 2 * index + 1))
        for index in range(7)
    )
    problem = build_shared_scheduling_problem(
        actions, 2, utilities=tuple(float(index + 1) for index in range(7))
    )
    model = build_dummy_fixed_cardinality_qubo(problem)
    with pytest.raises(ValueError, match="exhaustive QUBO audit refused"):
        audit_dummy_fixed_cardinality_qubo(model, max_variables=8)

    with pytest.raises(ValueError, match="exceeds qaoa_max_variables"):
        schedule_shared_actions(
            actions,
            config=SharedSchedulerConfig(
                method="qaoa",
                budget_requested=6,
                qaoa_max_variables=12,
                audit_max_variables=16,
            ),
            utilities=tuple(float(index + 1) for index in range(7)),
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"method": "unknown"}, "method must be"),
        ({"budget_requested": 0}, "budget_requested must be"),
        ({"redundancy_weight": -0.1}, "redundancy_weight"),
        ({"redundancy_alpha": 1.1}, "redundancy_alpha"),
        ({"qaoa_max_variables": 13}, "at most 12"),
        ({"qaoa_optimizer_steps": -1}, "non-negative"),
    ],
)
def test_scheduler_config_rejects_invalid_contracts(kwargs, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        SharedSchedulerConfig(**kwargs)
