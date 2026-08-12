#!/usr/bin/env python3
"""Contracts for calibration-only execution feedback in NMCTS scheduling."""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

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
from src.search.execution_feedback import (
    ExecutionCalibrationRecord,
    ExecutionUtilityAdjustment,
    RidgeExecutionCostModel,
    structural_feature_vector,
)
from src.search.mcts_scheduler import DiversitySchedulerConfig
from src.sshr_lib.bool_func import BooleanFunction


PAPER_WEIGHTS = ResourceWeights(
    t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0
)
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


def _scheduler_config() -> DiversitySchedulerConfig:
    return DiversitySchedulerConfig(
        method="top_b",
        budget_requested=1,
        pool_size=6,
        min_candidates=1,
        max_depth=0,
        seed=19,
    )


def _candidate_pool():
    solver = NeuralMCTSSolver(_search_config(), simulations=0, seed=3)
    key = StateKey(TERMS, 0, 0)
    node = solver._node(key)
    solver._expand(node)
    assert len(node.actions) >= 6
    return key, tuple(node.actions[:6])


def _calibration_records():
    key, actions = _candidate_pool()
    records = []
    for index, action in enumerate(actions):
        # Deterministic synthetic labels stand in for calibration-only native
        # execution measurements.  They are never supplied to predict().
        cost = (
            20.0
            + 5.0 * action.factor.bit_count()
            + 2.0 * len(action.group)
            + 0.5 * len(action.rest)
            + 0.125 * index
        )
        records.append(
            ExecutionCalibrationRecord(
                calibration_id=f"cal-{index:02d}",
                state_key=key,
                action=action,
                execution_cost=cost,
            )
        )
    return key, actions, tuple(records)


class _ForceIndexAdjuster:
    def __init__(self, target: int):
        self.target = target
        self.calls = 0

    def adjust(self, state_key, actions, raw_utilities):
        self.calls += 1
        adjusted = tuple(
            1000.0 if index == self.target else -1000.0
            for index in range(len(actions))
        )
        predicted = tuple(float(index) for index in range(len(actions)))
        penalties = tuple(float(index) / max(len(actions) - 1, 1) for index in range(len(actions)))
        return ExecutionUtilityAdjustment(
            adjusted_utilities=adjusted,
            predicted_execution_costs=predicted,
            normalized_execution_penalties=penalties,
            penalty_weight=7.5,
            cost_offset=0.0,
            cost_scale=max(float(len(actions) - 1), 1.0),
            model_metadata={
                "schema": "test-audited-adjuster-v1",
                "calibration_ids": ["cal-test"],
                "calibration_sha256": "2" * 64,
            },
            model_sha256="1" * 64,
        )


def test_none_adjuster_is_search_compatible_and_logs_identity() -> None:
    implicit = NeuralMCTSSolver(
        _search_config(),
        simulations=5,
        seed=7,
        scheduler_config=_scheduler_config(),
    )
    explicit = NeuralMCTSSolver(
        _search_config(),
        simulations=5,
        seed=7,
        scheduler_config=_scheduler_config(),
        execution_utility_adjuster=None,
    )

    implicit_plan = implicit.solve(TERMS)
    explicit_plan = explicit.solve(TERMS)

    assert explicit_plan == implicit_plan
    implicit_root = implicit.nodes[StateKey(TERMS, 0, 0)]
    explicit_root = explicit.nodes[StateKey(TERMS, 0, 0)]
    assert explicit_root.admitted_indices == implicit_root.admitted_indices
    diagnostics = explicit.scheduler_records[0]["diagnostics"]
    assert diagnostics["raw_utilities"] == diagnostics["adjusted_utilities"]
    assert diagnostics["execution_feedback_enabled"] is False
    assert diagnostics["execution_feedback_model_metadata"] == {}
    assert diagnostics["execution_feedback_model_sha256"] is None
    assert diagnostics["execution_feedback_penalty_weight"] == 0.0
    assert diagnostics["execution_feedback_elapsed_s"] >= 0.0


def test_adjuster_is_called_once_changes_selection_and_is_fully_audited() -> None:
    baseline = NeuralMCTSSolver(
        _search_config(),
        simulations=0,
        seed=11,
        scheduler_config=_scheduler_config(),
    )
    root_key = StateKey(TERMS, 0, 0)
    baseline._simulate(root_key)
    baseline_index = baseline.nodes[root_key].admitted_indices[0]
    target = (baseline_index + 1) % _scheduler_config().pool_size

    adjuster = _ForceIndexAdjuster(target)
    adjusted = NeuralMCTSSolver(
        _search_config(),
        simulations=0,
        seed=11,
        scheduler_config=_scheduler_config(),
        execution_utility_adjuster=adjuster,
    )
    for _ in range(4):
        adjusted._simulate(root_key)

    root = adjusted.nodes[root_key]
    assert root.admitted_indices == (target,)
    assert root.admitted_indices != baseline.nodes[root_key].admitted_indices
    assert adjuster.calls == 1

    diagnostics = adjusted.scheduler_records[0]["diagnostics"]
    assert diagnostics["raw_utilities"] != diagnostics["adjusted_utilities"]
    assert diagnostics["execution_feedback_enabled"] is True
    assert diagnostics["execution_feedback_model_sha256"] == "1" * 64
    assert diagnostics["execution_feedback_penalty_weight"] == 7.5
    assert diagnostics["execution_feedback_model_metadata"] == {
        "schema": "test-audited-adjuster-v1",
        "calibration_ids": ["cal-test"],
        "calibration_sha256": "2" * 64,
    }
    assert diagnostics["execution_feedback_elapsed_s"] >= 0.0
    assert diagnostics["execution_feedback"]["predicted_execution_costs"] == [
        float(index) for index in range(_scheduler_config().pool_size)
    ]


def test_ridge_fit_predict_adjust_and_hash_are_reproducible() -> None:
    key, actions, records = _calibration_records()
    first = RidgeExecutionCostModel(ridge_alpha=0.1, penalty_weight=0.6).fit(
        records
    )
    second = RidgeExecutionCostModel(ridge_alpha=0.1, penalty_weight=0.6).fit(
        tuple(reversed(records))
    )

    first_predictions = first.predict(key, actions)
    second_predictions = second.predict(key, actions)
    np.testing.assert_allclose(first_predictions, second_predictions, rtol=0, atol=0)
    assert np.all(first_predictions >= 0.0)
    assert first.metadata() == second.metadata()

    metadata = first.metadata()
    assert metadata["schema"] == "numpy-ridge-execution-cost-v1"
    assert metadata["calibration_ids"] == sorted(record.calibration_id for record in records)
    assert len(metadata["calibration_sha256"]) == 64
    assert len(metadata["model_sha256"]) == 64
    assert metadata["constant_features"]

    raw = tuple(0.5 - 0.03 * index for index in range(len(actions)))
    adjustment = first.adjust(key, actions, raw)
    assert len(adjustment.adjusted_utilities) == len(actions)
    assert adjustment.model_sha256 == metadata["model_sha256"]
    assert adjustment.penalty_weight == 0.6
    assert adjustment.cost_scale >= 1.0
    assert all(math.isfinite(value) for value in adjustment.adjusted_utilities)
    for source, penalty, result in zip(
        raw,
        adjustment.normalized_execution_penalties,
        adjustment.adjusted_utilities,
    ):
        assert result == pytest.approx(source - 0.6 * penalty)


def test_frozen_metadata_loads_without_refit_and_is_byte_stable() -> None:
    key, actions, records = _calibration_records()
    fitted = RidgeExecutionCostModel(ridge_alpha=0.1, penalty_weight=0.6).fit(
        records
    )
    frozen = fitted.metadata()
    loaded = RidgeExecutionCostModel.from_metadata(
        frozen,
        penalty_weight=0.6,
        expected_calibration_sha256=str(frozen["calibration_sha256"]),
    )

    assert loaded.metadata() == frozen
    assert loaded.metadata()["model_sha256"] == frozen["model_sha256"]
    np.testing.assert_array_equal(
        loaded.predict(key, actions), fitted.predict(key, actions)
    )
    raw = tuple(0.2 + index * 0.01 for index in range(len(actions)))
    assert loaded.adjust(key, actions, raw) == fitted.adjust(key, actions, raw)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item.update(schema="unknown-v9"), "model schema"),
        (lambda item: item["feature_names"].pop(), "feature_names"),
        (lambda item: item["coefficients"].pop(), "coefficients"),
        (lambda item: item.update(ridge_alpha=0.0), "positive"),
        (lambda item: item["standardization_mean"].__setitem__(0, math.inf), "finite"),
        (lambda item: item.update(model_sha256="0" * 64), "model SHA-256"),
        (lambda item: item.update(calibration_sha256="invalid"), "calibration_sha256"),
        (lambda item: item.update(unexpected="field"), "fields mismatch"),
    ],
)
def test_frozen_metadata_rejects_schema_numeric_and_hash_tampering(
    mutation, message
) -> None:
    _, _, records = _calibration_records()
    frozen = RidgeExecutionCostModel().fit(records).metadata()
    tampered = copy.deepcopy(frozen)
    mutation(tampered)

    with pytest.raises(ValueError, match=message):
        RidgeExecutionCostModel.from_metadata(tampered)


def test_frozen_metadata_rejects_wrong_calibration_manifest() -> None:
    _, _, records = _calibration_records()
    frozen = RidgeExecutionCostModel().fit(records).metadata()

    with pytest.raises(ValueError, match="frozen manifest"):
        RidgeExecutionCostModel.from_metadata(
            frozen,
            expected_calibration_sha256="f" * 64,
        )


def test_structural_features_are_invariant_to_variable_permutation() -> None:
    key, actions = _candidate_pool()
    action = actions[0]
    permutation = {0: 2, 1: 0, 2: 3, 3: 1}

    def permute(mask: int) -> int:
        result = 0
        for source, target in permutation.items():
            if mask & (1 << source):
                result |= 1 << target
        return result

    permuted_key = StateKey(
        frozenset(permute(term) for term in key.terms),
        key.prefix_len,
        key.live_factor_ancilla,
    )
    permuted_action = type(action)(
        factor=permute(action.factor),
        group=frozenset(permute(term) for term in action.group),
        residuals=frozenset(permute(term) for term in action.residuals),
        rest=frozenset(permute(term) for term in action.rest),
        immediate_gain=action.immediate_gain,
        prior=action.prior,
        linear=action.linear,
        affine_const=action.affine_const,
    )

    np.testing.assert_allclose(
        structural_feature_vector(key, action),
        structural_feature_vector(permuted_key, permuted_action),
        rtol=0,
        atol=0,
    )


def test_calibration_and_adjustment_reject_illegal_data() -> None:
    key, actions, records = _calibration_records()
    model = RidgeExecutionCostModel().fit(records)

    with pytest.raises(TypeError, match="only ExecutionCalibrationRecord"):
        RidgeExecutionCostModel().fit([{"calibration_id": "hidden-label"}])
    with pytest.raises(ValueError, match="unique"):
        RidgeExecutionCostModel().fit([records[0], records[0]])
    with pytest.raises(ValueError, match="finite"):
        RidgeExecutionCostModel().fit(
            [
                ExecutionCalibrationRecord(
                    "nan-target", key, actions[0], float("nan")
                )
            ]
        )
    with pytest.raises(ValueError, match="non-negative"):
        RidgeExecutionCostModel().fit(
            [ExecutionCalibrationRecord("negative", key, actions[0], -1.0)]
        )
    with pytest.raises(ValueError, match="must match"):
        model.adjust(key, actions, [0.0])
    with pytest.raises(ValueError, match="finite"):
        model.adjust(key, actions, [float("inf")] * len(actions))

    class WrongLengthAdjuster:
        def adjust(self, state_key, pool_actions, raw_utilities):
            count = len(pool_actions) - 1
            return ExecutionUtilityAdjustment(
                adjusted_utilities=(0.0,) * count,
                predicted_execution_costs=(0.0,) * count,
                normalized_execution_penalties=(0.0,) * count,
                penalty_weight=0.0,
                cost_offset=0.0,
                cost_scale=1.0,
                model_metadata={"schema": "wrong-length-test"},
                model_sha256="3" * 64,
            )

    solver = NeuralMCTSSolver(
        _search_config(),
        simulations=0,
        scheduler_config=_scheduler_config(),
        execution_utility_adjuster=WrongLengthAdjuster(),
    )
    with pytest.raises(ValueError, match="count must match"):
        solver._simulate(StateKey(TERMS, 0, 0))


def test_execution_feedback_changes_only_budgeting_not_oracle_semantics() -> None:
    solver = NeuralMCTSSolver(
        _search_config(),
        simulations=5,
        seed=23,
        scheduler_config=_scheduler_config(),
        execution_utility_adjuster=_ForceIndexAdjuster(5),
    )
    plan = solver.solve(TERMS)

    plan_check = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(plan, 4, _search_config().max_factor_ancilla)
    circuit_check = verify_circuit_anf(circuit, 4, TERMS)
    bf = BooleanFunction(4, truth_table_from_anf(4, TERMS))

    assert plan_check.ok
    assert circuit_check.ok
    assert verify_oracle(circuit, bf)
