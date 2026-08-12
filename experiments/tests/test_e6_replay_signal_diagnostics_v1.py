#!/usr/bin/env python3
"""Unit tests for deterministic E6 replay signal diagnostics."""

from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest

from e6.final_measurement_replay_v2 import SOURCE_ARMS, ReplayTargetsV2
from e6.frozen_case import build_frozen_shared_case, canonical_action_sha256
from e6.isolated_head_trainer_v2 import LockedReplayTrainingGroupV2
from e6.replay_signal_diagnostics_v1 import (
    MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA,
    REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA,
    aggregate_model_ranking_diagnostics_v1,
    aggregate_replay_signal_diagnostics_v1,
    diagnose_model_ranking_case_v1,
    diagnose_replay_signal_case_v1,
    diagnose_replay_training_corpus_v1,
)
from e6.replay_training_corpus_v1 import (
    ReplayTrainingCorpusV1,
    ReplayTrainingGroupV1,
)
from e6.shared_oracle import MonomialSharedAction, VectorANF
from e6.shared_scheduler import (
    SharedSchedulerConfig,
    SharedUtilityWeights,
    shared_action_utility,
)


TEST_WEIGHTS = SharedUtilityWeights(t=1.0, cnot=0.0, depth=0.0, gates=0.0, ancilla=0.0)


class _StaticModel:
    def __init__(self, logits, value=-0.25):
        self.logits = tuple(float(item) for item in logits)
        self.value = float(value)

    def forward_one(self, vector, actions, *, weights):
        assert type(vector) is VectorANF
        assert type(actions) is tuple
        assert type(weights) is SharedUtilityWeights
        return list(self.logits), self.value


def _vector_actions():
    vector = VectorANF(
        4,
        (
            frozenset({0b1111, 0b0111, 0b0011}),
            frozenset({0b1111, 0b0111, 0b0011}),
            frozenset({0b1111, 0b0111, 0b1011}),
            frozenset({0b1111, 0b1011}),
            frozenset({0b1111, 0b1011}),
        ),
    )
    actions = (
        MonomialSharedAction(0b1111, (0, 1, 2, 3, 4)),
        MonomialSharedAction(0b0111, (0, 1, 2)),
        MonomialSharedAction(0b0011, (0, 1)),
        MonomialSharedAction(0b1011, (2, 3, 4)),
    )
    return vector, actions


def _derived_raw(actions, weights=TEST_WEIGHTS):
    return tuple(shared_action_utility(action, weights=weights) for action in actions)


def _model_row(*, case_id="case-a", logits=None, weights=TEST_WEIGHTS):
    vector, actions = _vector_actions()
    raw = _derived_raw(actions, weights)
    return diagnose_model_ranking_case_v1(
        split="structured_validation_expanded",
        case_id=case_id,
        arm="qaoa_labels_value_weight_1",
        value_weight=1.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw,
        model=_StaticModel(raw if logits is None else logits),
        top_k=2,
        scheduler_budget=1,
        weights=weights,
    )


def _teacher_row(
    *, case_id="case-a", logits=None, weights=TEST_WEIGHTS, model_value=-0.5
):
    vector, actions = _vector_actions()
    raw = _derived_raw(actions, weights)
    maximum = max(raw)
    exponentials = tuple(math.exp(value - maximum) for value in raw)
    denominator = math.fsum(exponentials)
    teacher = tuple(value / denominator for value in exponentials)
    return diagnose_replay_signal_case_v1(
        split="structured_validation_matched6",
        case_id=case_id,
        arm="qaoa_labels_value_weight_1",
        teacher_role="replay_validation_target",
        value_weight=1.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw,
        teacher_policy=teacher,
        teacher_value_target=-0.25,
        policy_observation_weight=0.75,
        feasible_fraction=0.5,
        value_observation_weight=0.25,
        model=_StaticModel(raw if logits is None else logits, value=model_value),
        top_k=2,
        scheduler_budget=1,
        weights=weights,
    )


def _assert_native_finite(value):
    if type(value) is float:
        assert math.isfinite(value)
    elif type(value) is dict:
        assert all(type(key) is str for key in value)
        for child in value.values():
            _assert_native_finite(child)
    elif type(value) in {list, tuple}:
        for child in value:
            _assert_native_finite(child)
    else:
        assert value is None or type(value) in {str, int, bool}


def test_teacher_and_model_alignment_metrics_are_exact_and_semantic() -> None:
    row = _teacher_row()
    assert row["schema_version"] == REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA
    assert row["teacher_raw_pearson"] > 0.9
    assert row["teacher_raw_spearman"] == pytest.approx(1.0)
    assert row["model_raw_pearson"] == pytest.approx(1.0)
    assert row["model_raw_spearman"] == pytest.approx(1.0)
    assert row["policy_kl_divergence"] == pytest.approx(0.0, abs=1.0e-14)
    assert row["policy_cross_entropy"] == pytest.approx(row["teacher_entropy"])
    assert row["teacher_argmax_raw_best_hit"] is True
    assert row["teacher_raw_positive_mass"] > 0.99
    assert row["teacher_raw_best_mass"] == pytest.approx(row["teacher_policy"][0])
    assert row["policy_observation_weight"] == 0.75
    assert row["feasible_fraction"] == 0.5
    assert row["value_observation_weight"] == 0.25
    assert row["value_squared_error"] == pytest.approx(0.25**2)
    assert row["effective_value_loss_contribution"] == pytest.approx(
        1.0 * 0.25 * 0.25**2
    )
    assert row["raw_best_top_k_recall"] == 1.0
    assert row["semantic_verification"] is True
    assert row["degraded"] is False
    assert row["direct_fallback_used"] is False
    assert row["score_ratio_y"] > 0.0
    assert math.isfinite(row["score_ratio_y"])
    json.dumps(row, sort_keys=True, allow_nan=False)
    _assert_native_finite(row)


def test_ties_use_average_ranks_and_raw_best_recall_counts_all_maxima() -> None:
    vector, actions = _vector_actions()
    raw = _derived_raw(actions)
    row = diagnose_replay_signal_case_v1(
        split="validation",
        case_id="ties",
        arm="arbitrary_cell_label",
        teacher_role="sparse_test_teacher",
        value_weight=0.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw,
        teacher_policy=(1.0, 0.0, 0.0, 0.0),
        teacher_value_target=0.0,
        model=_StaticModel(raw, value=0.0),
        top_k=1,
        scheduler_budget=1,
        weights=TEST_WEIGHTS,
    )
    assert row["model_raw_spearman_defined"] is True
    assert row["model_raw_spearman"] == pytest.approx(1.0)
    assert row["raw_best_count"] == 1
    assert row["raw_best_top_k_hit_count"] == 1
    assert row["raw_best_top_k_recall"] == pytest.approx(1.0)
    assert math.isfinite(row["policy_cross_entropy"])
    assert math.isfinite(row["policy_kl_divergence"])
    assert row["effective_value_loss_contribution"] is None


def test_teacher_free_expanded_view_has_no_fabricated_teacher_and_empty_projection() -> None:
    zero_weights = SharedUtilityWeights(t=0.0, cnot=0.0, depth=0.0, gates=0.0, ancilla=0.0)
    row = _model_row(logits=(4.0, 3.0, 2.0, 1.0), weights=zero_weights)
    assert row["schema_version"] == MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA
    assert all("teacher" not in field for field in row)
    assert row["selected_empty"] is True
    assert row["selected_count"] == 0
    assert row["score_ratio_y"] == 1.0
    assert row["semantic_verification"] is True
    assert row["direct_fallback_used"] is False
    assert row["projection_uses_arm_neutral_raw_utilities"] is True


def test_exact_projection_tie_break_is_independent_of_model_logit_order() -> None:
    vector, actions = _vector_actions()
    raw = _derived_raw(actions)
    assert raw[1] == raw[3] > raw[2]
    base = dict(
        split="expanded",
        case_id="tie-order",
        arm="cell",
        value_weight=1.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw,
        top_k=2,
        scheduler_budget=1,
        weights=TEST_WEIGHTS,
    )
    left = diagnose_model_ranking_case_v1(
        **base, model=_StaticModel((-100.0, 2.0, -100.0, 1.0))
    )
    right = diagnose_model_ranking_case_v1(
        **base, model=_StaticModel((-100.0, 1.0, -100.0, 2.0))
    )
    assert set(left["top_k_source_indices"]) == set(right["top_k_source_indices"])
    assert left["top_k_source_indices"] != right["top_k_source_indices"]
    assert left["selected_source_indices"] == right["selected_source_indices"]
    assert left["projection_objective"] == right["projection_objective"]


def test_constant_inputs_are_explicitly_undefined_not_nan() -> None:
    zero_weights = SharedUtilityWeights(t=0.0, cnot=0.0, depth=0.0, gates=0.0, ancilla=0.0)
    row = _model_row(logits=(0.0, 0.0, 0.0, 0.0), weights=zero_weights)
    assert row["model_raw_pearson_defined"] is False
    assert row["model_raw_pearson"] == 0.0
    assert row["model_raw_spearman_defined"] is False
    assert row["model_raw_spearman"] == 0.0
    assert row["raw_best_count"] == 4
    assert row["raw_best_top_k_recall"] == 0.5


def test_aggregates_are_canonical_and_include_projection_endpoints() -> None:
    teacher_a = _teacher_row(case_id="b")
    teacher_b = _teacher_row(case_id="a")
    forward = aggregate_replay_signal_diagnostics_v1((teacher_a, teacher_b))
    reverse = aggregate_replay_signal_diagnostics_v1((teacher_b, teacher_a))
    assert forward == reverse
    group = forward["groups"][0]
    assert group["case_ids"] == ["a", "b"]
    assert group["selected_empty_rate"] == 0.0
    assert group["semantic_verification_rate"] == 1.0
    assert group["direct_fallback_rate"] == 0.0
    assert group["policy_observation_weight_mean_defined"] == 0.75
    assert group["policy_observation_weight_defined_rate"] == 1.0
    assert group["feasible_fraction_mean_defined"] == 0.5
    assert group["value_observation_weight_mean_defined"] == 0.25
    assert group["effective_value_loss_contribution_mean_defined"] == pytest.approx(
        1.0 * 0.25 * 0.25**2
    )
    assert group["effective_value_loss_contribution_defined_rate"] == 1.0
    assert group["teacher_raw_positive_mass_mean"] > 0.99
    assert math.isfinite(group["score_ratio_y_mean"])

    model_a = _model_row(case_id="b")
    model_b = _model_row(case_id="a")
    model_aggregate = aggregate_model_ranking_diagnostics_v1((model_a, model_b))
    assert model_aggregate["teacher_metrics_present"] is False
    assert model_aggregate["groups"][0]["case_ids"] == ["a", "b"]
    assert model_aggregate["groups"][0]["semantic_verification_rate"] == 1.0
    json.dumps(model_aggregate, sort_keys=True, allow_nan=False)


def test_case_api_rejects_non_native_nonfinite_and_oversized_projection() -> None:
    vector, actions = _vector_actions()
    raw = _derived_raw(actions)
    base = dict(
        split="validation",
        case_id="bad",
        arm="cell",
        value_weight=1.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw,
        model=_StaticModel(raw),
        top_k=2,
        scheduler_budget=1,
        weights=TEST_WEIGHTS,
    )
    with pytest.raises(TypeError, match="actions"):
        diagnose_model_ranking_case_v1(**{**base, "actions": list(actions)})
    with pytest.raises(ValueError, match="finite"):
        diagnose_model_ranking_case_v1(
            **{**base, "raw_utilities": (1.0, 2.0, math.nan, 4.0)}
        )
    with pytest.raises(ValueError, match="exactly equal"):
        diagnose_model_ranking_case_v1(
            **{**base, "raw_utilities": (1.0e9, *raw[1:])}
        )
    with pytest.raises(ValueError, match="top_k"):
        diagnose_model_ranking_case_v1(
            **{**base, "top_k": 5, "scheduler_budget": 1}
        )


def test_corpus_adapter_accepts_exact_nonempty_source_arm_subset() -> None:
    vector, actions = _vector_actions()
    case = build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256="a" * 64,
        config=SharedSchedulerConfig(budget_requested=1),
        utility_weights=TEST_WEIGHTS,
        raw_utilities=_derived_raw(actions),
        learned_utilities=_derived_raw(actions),
    )
    action_signatures = tuple(canonical_action_sha256(action) for action in case.actions)

    def target(arm):
        return ReplayTargetsV2(
            observation_sha256="b" * 64,
            source_arm=arm,
            action_signatures=action_signatures,
            policy_target=(0.25,) * 4,
            policy_observation_weight=1.0,
            feasible_fraction=1.0,
            value_observation_weight=1.0,
            value_loss_weight_contract="test",
            value_target_log_ratio=-0.25,
            value_audit=None,  # type: ignore[arg-type]
            whole_vector_cluster_id="cluster",
        )

    manifest = SimpleNamespace(group_id="group-1", split_role="train_replay")
    material = LockedReplayTrainingGroupV2(
        case=case,
        records=(),
        manifest=manifest,  # type: ignore[arg-type]
        external_lock_payload=b"",
        qaoa_counts_payload=b"",
        final_parameter_payload=b"",
        run_attestation=b"",
        protocol_payload=b"",
        source_manifest_payload=b"",
    )
    group = ReplayTrainingGroupV1(
        material=material,
        technical_lock=None,  # type: ignore[arg-type]
        targets_by_arm=tuple((arm, target(arm)) for arm in SOURCE_ARMS),
        qaoa_gammas=(0.0,),
        qaoa_betas=(0.0,),
        generation_attempt=0,
    )
    descriptor = SimpleNamespace(
        case_roster=(SimpleNamespace(group_id="group-1", case_id="train-1"),)
    )
    corpus = ReplayTrainingCorpusV1(
        descriptor=descriptor,  # type: ignore[arg-type]
        registry=None,  # type: ignore[arg-type]
        groups=(group,),
        protocol_payload=b"",
        source_manifest_payload=b"",
        corpus_lock_payload=b"",
    )
    selected = SOURCE_ARMS[2:]
    rows = diagnose_replay_training_corpus_v1(
        corpus,
        {arm: _StaticModel(_derived_raw(actions)) for arm in selected},
        value_weight=1.0,
        top_k=2,
        scheduler_budget=1,
    )
    assert tuple(row["arm"] for row in rows) == tuple(sorted(selected))
    assert all(row["teacher_role"] == "replay_training_target" for row in rows)
    assert all(row["policy_observation_weight"] == 1.0 for row in rows)
    assert all(row["feasible_fraction"] == 1.0 for row in rows)
    assert all(row["value_observation_weight"] == 1.0 for row in rows)
    with pytest.raises(ValueError, match="unknown source arms"):
        diagnose_replay_training_corpus_v1(
            corpus,
            {"not-an-arm": _StaticModel(_derived_raw(actions))},
            value_weight=1.0,
            top_k=2,
            scheduler_budget=1,
        )


def test_aggregate_tampering_and_duplicate_identity_fail_closed() -> None:
    row = _model_row()
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_model_ranking_diagnostics_v1((row, dict(row)))
    tampered = dict(row)
    tampered["model_raw_pearson"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        aggregate_model_ranking_diagnostics_v1((tampered,))
    inconsistent = dict(row)
    inconsistent["selected_count"] = int(row["selected_count"]) + 1
    with pytest.raises(ValueError, match="selected_source_indices"):
        aggregate_model_ranking_diagnostics_v1((inconsistent,))
    impossible_recall = dict(row)
    impossible_recall["raw_best_top_k_recall"] = 1.5
    with pytest.raises(ValueError, match="recall"):
        aggregate_model_ranking_diagnostics_v1((impossible_recall,))
