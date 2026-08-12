#!/usr/bin/env python3
"""Contracts for synthetic execution-aware root scheduling utility."""

from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

from src.factor_plan import (
    FactorAction,
    SearchConfig,
    candidate_actions,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_plan_anf,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey
from src.resource_model import ResourceWeights
from src.search.execution_aware_utility import (
    ADJUSTER_SCHEMA,
    FrozenExecutionPenaltyWeights,
    SyntheticExecutionProfileSpec,
    complete_root_action_rollout,
    make_root_rollout_execution_utility_adjuster,
)
from src.search.execution_feedback import (
    ExecutionCalibrationRecord,
    RidgeExecutionCostModel,
)
from src.search.mcts_scheduler import DiversitySchedulerConfig


TERMS = frozenset((0b011, 0b101, 0b110, 0b111))
CALIBRATION_SHA256 = "a" * 64
PAPER_WEIGHTS = ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)


def _search_config() -> SearchConfig:
    return SearchConfig(
        weights=PAPER_WEIGHTS,
        candidate_top_k=8,
        max_factor_ancilla=2,
        max_factor_size=3,
        gate_mode="logical_and",
    )


def _pool() -> tuple[StateKey, tuple[FactorAction, ...]]:
    key = StateKey(TERMS, 0, 0)
    actions = tuple(candidate_actions(TERMS, 0, 0, _search_config(), None))
    assert len(actions) == 3
    return key, actions


def _profile() -> SyntheticExecutionProfileSpec:
    return SyntheticExecutionProfileSpec(
        one_qubit_duration_ns=35.0,
        two_qubit_duration_ns=300.0,
    )


def _weights(
    profile: SyntheticExecutionProfileSpec,
    **overrides: float,
) -> FrozenExecutionPenaltyWeights:
    values = {
        "native_one_qubit": 1.0e-4,
        "native_two_qubit": 2.0e-4,
        "inserted_swap": 1.0e-3,
        "native_depth": 1.0e-4,
        "duration_ns": 1.0e-7,
        "model_risk": 0.0,
    }
    values.update(overrides)
    return FrozenExecutionPenaltyWeights(
        calibration_sha256=CALIBRATION_SHA256,
        profile_sha256=profile.profile_sha256,
        **values,
    )


def _adjuster(
    profile: SyntheticExecutionProfileSpec,
    weights: FrozenExecutionPenaltyWeights,
    **kwargs,
):
    return make_root_rollout_execution_utility_adjuster(
        n_inputs=3,
        search_config=_search_config(),
        profile_spec=profile,
        penalty_weights=weights,
        expected_profile_sha256=profile.profile_sha256,
        **kwargs,
    )


def test_rollout_candidate_compilation_is_component_audited() -> None:
    key, actions = _pool()
    profile = _profile()
    weights = _weights(profile)
    raw = (0.3, 0.2, -0.1)
    result = _adjuster(profile, weights).adjust(key, actions, raw)

    assert result.model_metadata["schema"] == ADJUSTER_SCHEMA
    assert result.model_metadata["profile_sha256"] == profile.profile_sha256
    assert result.model_metadata["penalty_weights_sha256"] == weights.weights_sha256
    assert result.model_metadata["heldout_noisy_outcome_input"] is False
    assert result.diagnostics["heldout_noisy_outcome_used"] is False
    assert result.diagnostics["synthetic_proxy_only"] is True
    assert result.diagnostics["hardware_execution"] is False
    assert result.diagnostics["raw_utilities"] == list(raw)
    assert result.diagnostics["adjusted_utilities"] == list(result.adjusted_utilities)

    records = result.diagnostics["candidates"]
    assert len(records) == len(actions)
    assert len(set(result.diagnostics["candidate_action_sha256"])) == len(actions)
    for index, record in enumerate(records):
        assert record["candidate_index"] == index
        assert record["plan_anf_ok"] is True
        assert record["circuit_anf_ok"] is True
        assert record["synthetic_profile"] is True
        assert record["hardware_execution"] is False
        assert record["concrete_profile_name"].startswith(
            "synthetic-heavy-hex-like-"
        )
        assert len(record["concrete_profile_sha256"]) == 64
        resources = record["resource_components"]
        contributions = record["penalty_contributions"]
        assert set(resources) == {
            "native_one_qubit",
            "native_two_qubit",
            "inserted_swap",
            "native_depth",
            "duration_ns",
            "model_risk",
        }
        assert all(value >= 0.0 and math.isfinite(value) for value in resources.values())
        assert all(
            value >= 0.0 and math.isfinite(value) for value in contributions.values()
        )
        assert record["total_penalty"] == pytest.approx(
            math.fsum(contributions.values()), rel=0.0, abs=1e-15
        )
        assert result.adjusted_utilities[index] == pytest.approx(
            raw[index] - record["total_penalty"], rel=0.0, abs=1e-15
        )


def test_zero_weights_are_exact_identity_and_deterministic() -> None:
    key, actions = _pool()
    profile = _profile()
    zero = _weights(
        profile,
        native_one_qubit=0.0,
        native_two_qubit=0.0,
        inserted_swap=0.0,
        native_depth=0.0,
        duration_ns=0.0,
    )
    raw = (0.25, -0.125, 0.0)
    adjuster = _adjuster(profile, zero)
    first = adjuster.adjust(key, actions, raw)
    second = adjuster.adjust(key, actions, raw)

    assert first.adjusted_utilities == raw
    assert first.normalized_execution_penalties == (0.0, 0.0, 0.0)
    assert first == second


def test_candidate_order_permutation_only_permutes_outputs() -> None:
    key, actions = _pool()
    profile = _profile()
    adjuster = _adjuster(profile, _weights(profile))
    raw = (0.3, 0.2, 0.1)
    forward = adjuster.adjust(key, actions, raw)
    reverse = adjuster.adjust(key, tuple(reversed(actions)), tuple(reversed(raw)))

    assert reverse.adjusted_utilities == tuple(reversed(forward.adjusted_utilities))
    assert reverse.normalized_execution_penalties == tuple(
        reversed(forward.normalized_execution_penalties)
    )
    by_action_forward = {
        record["action_sha256"]: record for record in forward.diagnostics["candidates"]
    }
    by_action_reverse = {
        record["action_sha256"]: record for record in reverse.diagnostics["candidates"]
    }
    assert set(by_action_forward) == set(by_action_reverse)
    for digest in by_action_forward:
        left = by_action_forward[digest]
        right = by_action_reverse[digest]
        assert left["plan_sha256"] == right["plan_sha256"]
        assert left["concrete_profile_sha256"] == right["concrete_profile_sha256"]
        assert left["resource_components"] == right["resource_components"]
        assert left["total_penalty"] == right["total_penalty"]


def test_optional_risk_model_is_frozen_and_sha_bound() -> None:
    key, actions = _pool()
    records = tuple(
        ExecutionCalibrationRecord(
            calibration_id=f"cal-{index}",
            state_key=key,
            action=action,
            execution_cost=10.0 + 3.0 * index,
        )
        for index, action in enumerate(actions)
    )
    model = RidgeExecutionCostModel(ridge_alpha=0.5).fit(records)
    model_sha = str(model.metadata()["model_sha256"])
    profile = _profile()
    weights = _weights(profile, model_risk=0.01)
    adjuster = _adjuster(
        profile,
        weights,
        risk_model=model,
        expected_risk_model_sha256=model_sha,
    )
    result = adjuster.adjust(key, actions, (0.3, 0.2, 0.1))

    np.testing.assert_allclose(
        result.predicted_execution_costs,
        model.predict(key, actions),
        rtol=0.0,
        atol=0.0,
    )
    assert result.model_metadata["risk_model_sha256"] == model_sha
    for record, risk in zip(
        result.diagnostics["candidates"], result.predicted_execution_costs
    ):
        assert record["resource_components"]["model_risk"] == risk
        assert record["penalty_contributions"]["model_risk"] == pytest.approx(
            0.01 * risk
        )

    model.fit(
        tuple(
            ExecutionCalibrationRecord(
                calibration_id=f"mutated-{index}",
                state_key=key,
                action=action,
                execution_cost=100.0 + index,
            )
            for index, action in enumerate(actions)
        )
    )
    with pytest.raises(RuntimeError, match="changed after"):
        adjuster.adjust(key, actions, (0.3, 0.2, 0.1))


def test_profile_model_and_finite_value_contracts_fail_closed() -> None:
    key, actions = _pool()
    profile = _profile()
    weights = _weights(profile)
    with pytest.raises(ValueError, match="profile SHA-256"):
        make_root_rollout_execution_utility_adjuster(
            n_inputs=3,
            search_config=_search_config(),
            profile_spec=profile,
            penalty_weights=weights,
            expected_profile_sha256="b" * 64,
        )
    with pytest.raises(ValueError, match="finite non-negative"):
        _weights(profile, native_depth=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        _adjuster(profile, weights).adjust(key, actions, (0.0, float("inf"), 0.0))
    with pytest.raises(ValueError, match="count must match"):
        _adjuster(profile, weights).adjust(key, actions, (0.0,))
    with pytest.raises(ValueError, match="unique signatures"):
        _adjuster(profile, weights).adjust(
            key, (actions[0], actions[0]), (0.0, 0.0)
        )

    records = tuple(
        ExecutionCalibrationRecord(f"cal-{i}", key, action, 1.0 + i)
        for i, action in enumerate(actions)
    )
    model = RidgeExecutionCostModel().fit(records)
    with pytest.raises(ValueError, match="risk-model SHA-256"):
        _adjuster(
            profile,
            _weights(profile, model_risk=0.1),
            risk_model=model,
            expected_risk_model_sha256="c" * 64,
        )


def test_candidate_alignment_and_root_only_contracts_fail_closed() -> None:
    key, actions = _pool()
    profile = _profile()
    adjuster = _adjuster(profile, _weights(profile))
    tampered = replace(actions[0], rest=frozenset())
    with pytest.raises(ValueError, match="partition"):
        adjuster.adjust(key, (tampered,), (0.1,))
    with pytest.raises(ValueError, match="root-only"):
        adjuster.adjust(StateKey(TERMS, 1, 1), (actions[0],), (0.1,))
    too_wide = StateKey(frozenset((0b1000, 0b1001)), 0, 0)
    with pytest.raises(ValueError, match="n_inputs"):
        adjuster.adjust(too_wide, (actions[0],), (0.1,))


def test_runner_helper_preserves_candidate_plan_semantics() -> None:
    key, actions = _pool()
    plan = complete_root_action_rollout(key, actions[0], _search_config())
    plan_check = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(
        plan,
        3,
        min(_search_config().max_factor_ancilla, plan.cost.explicit_ancilla),
    )
    circuit_check = verify_circuit_anf(circuit, 3, TERMS)
    assert plan_check.ok
    assert circuit_check.ok


def test_classical_and_qaoa_paths_receive_the_same_adjusted_utility() -> None:
    profile = _profile()
    weights = _weights(profile)

    def scheduler(method: str) -> DiversitySchedulerConfig:
        return DiversitySchedulerConfig(
            method=method,
            budget_requested=2,
            pool_size=3,
            min_candidates=1,
            max_depth=0,
            seed=29,
            qaoa_mode="ideal",
            qaoa_p=1,
            qaoa_shots=16,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=0,
        )

    diagnostics = []
    for method in ("greedy", "qaoa"):
        solver = NeuralMCTSSolver(
            _search_config(),
            simulations=0,
            seed=7,
            scheduler_config=scheduler(method),
            execution_utility_adjuster=_adjuster(profile, weights),
        )
        solver._simulate(StateKey(TERMS, 0, 0))
        diagnostics.append(solver.scheduler_records[0]["diagnostics"])

    classical, qaoa = diagnostics
    assert classical["candidate_action_signatures"] == qaoa[
        "candidate_action_signatures"
    ]
    assert classical["raw_utilities"] == qaoa["raw_utilities"]
    assert classical["adjusted_utilities"] == qaoa["adjusted_utilities"]
    assert classical["execution_feedback"]["diagnostics"] == qaoa[
        "execution_feedback"
    ]["diagnostics"]
    assert classical["execution_feedback"]["diagnostics"][
        "heldout_noisy_outcome_used"
    ] is False


def test_adjuster_sha_binds_problem_width_search_config_and_execution_width() -> None:
    profile = _profile()
    weights = _weights(profile)
    baseline = _adjuster(profile, weights)
    wider_problem = make_root_rollout_execution_utility_adjuster(
        n_inputs=4,
        search_config=_search_config(),
        profile_spec=profile,
        penalty_weights=weights,
        expected_profile_sha256=profile.profile_sha256,
    )
    changed_search = make_root_rollout_execution_utility_adjuster(
        n_inputs=3,
        search_config=replace(_search_config(), candidate_top_k=7),
        profile_spec=profile,
        penalty_weights=weights,
        expected_profile_sha256=profile.profile_sha256,
    )
    fixed_ten_qubits = make_root_rollout_execution_utility_adjuster(
        n_inputs=3,
        search_config=_search_config(),
        profile_spec=profile,
        penalty_weights=weights,
        expected_profile_sha256=profile.profile_sha256,
        execution_n_qubits=10,
    )

    assert len(
        {
            baseline.adjuster_sha256,
            wider_problem.adjuster_sha256,
            changed_search.adjuster_sha256,
            fixed_ten_qubits.adjuster_sha256,
        }
    ) == 4
    metadata = fixed_ten_qubits._base_metadata()
    assert metadata["n_inputs"] == 3
    assert metadata["execution_n_qubits"] == 10
    assert len(metadata["search_config_sha256"]) == 64
