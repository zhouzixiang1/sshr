#!/usr/bin/env python3
"""Tests for deterministic E6 replay-training held-out evaluation."""

from __future__ import annotations

from dataclasses import replace

import pytest

import e6.replay_training_evaluation_v1 as evaluation_module
from e6.final_measurement_replay_v2 import SOURCE_ARMS
from e6.replay_training_evaluation_v1 import (
    CLAIM_BOUNDARY,
    HELDOUT_EVALUATION_V1_SCHEMA,
    evaluate_replay_training_heldout_v1,
    generate_heldout_bijections_v1,
    paired_arm_statistics_v1,
)
from e6.shared_scheduler import SharedUtilityWeights, shared_action_utility


class _UtilityStub:
    """Callable inference stub whose ranking depends only on public actions."""

    def __init__(self, multiplier: float, offset: float = 0.0) -> None:
        self.multiplier = multiplier
        self.offset = offset

    def forward_one(self, vector, actions):
        del vector
        return (
            [
                self.offset + self.multiplier * shared_action_utility(action)
                for action in actions
            ],
            -1.0,
        )


class _ShiftedUtilityStub(_UtilityStub):
    """Same ordering with an arbitrary logit gauge shift."""


def _models() -> dict[str, object]:
    return {
        "classical_random_bitstring_replay": _UtilityStub(-0.75, 0.3),
        "classical_greedy_repeated_selection_replay": _UtilityStub(0.5, 0.2),
        "qaoa_final_measurement_replay": _UtilityStub(1.0, 0.1),
        "qaoa_permuted_label_control": _UtilityStub(-1.0, 0.4),
    }


def _stats_case(
    *,
    width: int,
    index: int,
    qaoa_y: float = 0.80,
    control_y: float = 1.00,
    qaoa_valid: bool = True,
) -> dict[str, object]:
    def arm(y: float, *, valid: bool = True) -> dict[str, object]:
        return {
            "itt_score_ratio_y": y,
            "valid_observation": valid,
            "direct_fallback_used": not valid,
        }

    return {
        "case_id": f"n{width}-{index}",
        "input_count": width,
        "whole_vector_cluster_sha256": f"{width:x}{index:063x}"[-64:],
        "arms": {
            "classical_random_bitstring_replay": arm(0.95),
            "classical_greedy_repeated_selection_replay": arm(0.90),
            "qaoa_final_measurement_replay": arm(
                qaoa_y if qaoa_valid else 1.0, valid=qaoa_valid
            ),
            "qaoa_permuted_label_control": arm(control_y),
        },
    }


def test_sha_ranked_heldout_bijections_are_deterministic_and_orbit_distinct() -> None:
    first = generate_heldout_bijections_v1(seed=1234, cases_per_width=3)
    second = generate_heldout_bijections_v1(seed=1234, cases_per_width=3)

    def projection(rows):
        return tuple(
            (
                row["case_id"],
                row["input_count"],
                row["value_table"],
                row["value_table_sha256"],
                row["vector_sha256"],
                row["orbit_cluster_sha256"],
            )
            for row in rows
        )

    assert projection(first) == projection(second)
    assert [row["input_count"] for row in first] == [4, 4, 4, 5, 5, 5]
    assert len({row["orbit_cluster_sha256"] for row in first}) == len(first)
    for row in first:
        width = row["input_count"]
        assert sorted(row["value_table"]) == list(range(1 << width))
        vector = row["vector"]
        assert (
            tuple(vector.evaluate_value(x) for x in range(1 << width))
            == row["value_table"]
        )

    different = generate_heldout_bijections_v1(seed=1235, cases_per_width=3)
    assert projection(first) != projection(different)
    with pytest.raises(ValueError, match="fixed at exact"):
        generate_heldout_bijections_v1(widths=(4,))


def test_four_arms_share_pool_and_evaluation_is_byte_deterministic() -> None:
    kwargs = dict(
        seed=20260917,
        cases_per_width=1,
        top_k=4,
        scheduler_budget=2,
        bootstrap_resamples=64,
        signflip_resamples=64,
    )
    first = evaluate_replay_training_heldout_v1(_models(), **kwargs)
    second = evaluate_replay_training_heldout_v1(_models(), **kwargs)

    assert first == second
    assert first["schema_version"] == HELDOUT_EVALUATION_V1_SCHEMA
    assert first["claim_boundary"] == CLAIM_BOUNDARY
    assert first["heldout_development_evaluation"] is True
    assert first["formal_evaluation"] is False
    assert first["performance_evidence"] is False
    assert len(first["case_rows"]) == 2
    for row in first["case_rows"]:
        assert set(row["arms"]) == set(SOURCE_ARMS)
        assert row["capped_candidate_count"] <= 256
        assert len(row["common_pool_action_sha256"]) == row["capped_candidate_count"]
        assert (
            len(set(row["common_pool_action_sha256"])) == row["capped_candidate_count"]
        )
        expected_assignments = 1 << (2 * row["input_count"])
        assert row["direct_semantic_verification"]["assignments_checked"] == (
            expected_assignments
        )
        for arm in SOURCE_ARMS:
            result = row["arms"][arm]
            assert len(result["model_logits"]) == row["capped_candidate_count"]
            assert result["semantic_verification"] is True
            assert result["degraded"] is False
            assert result["valid_observation"] is True
            assert result["score_ratio"] == result["itt_score_ratio_y"]
            assert len(result["ranked_top_k_source_indices"]) <= 4
            assert len(result["selected_source_indices"]) <= 2
            assert result["final_semantic_verification"]["ok"] is True
    assert first["statistics"]["claim_gate"]["formal_evaluation"] is False
    assert first["statistics"]["claim_gate"]["performance_evidence"] is False


def test_logit_global_shift_changes_neither_exact_selection_nor_y() -> None:
    # The enormous negative/positive gauges would change how many real actions
    # beat the scheduler's zero-utility dummy slots if logits leaked into its
    # objective.  They preserve the complete logit ordering exactly.
    base_models = {arm: _UtilityStub(1.0, -10_000.0) for arm in SOURCE_ARMS}
    shifted_models = {arm: _ShiftedUtilityStub(1.0, 10_000.0) for arm in SOURCE_ARMS}
    kwargs = dict(
        seed=20260921,
        cases_per_width=1,
        top_k=6,
        scheduler_budget=2,
        bootstrap_resamples=32,
        signflip_resamples=32,
        utility_weights=SharedUtilityWeights(
            t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0
        ),
    )
    base = evaluate_replay_training_heldout_v1(base_models, **kwargs)
    shifted = evaluate_replay_training_heldout_v1(shifted_models, **kwargs)

    assert base["protocol"]["scheduler_utility"] == ("arm_neutral_raw_analytic_utility")
    assert base["protocol"]["utility_weights"] == {
        "t": 1.0,
        "cnot": 0.04,
        "depth": 0.015,
        "gates": 0.01,
        "ancilla": 2.0,
    }
    for base_case, shifted_case in zip(base["case_rows"], shifted["case_rows"]):
        assert (
            base_case["common_pool_raw_utilities"]
            == shifted_case["common_pool_raw_utilities"]
        )
        for arm in SOURCE_ARMS:
            left = base_case["arms"][arm]
            right = shifted_case["arms"][arm]
            assert left["model_logits"] != right["model_logits"]
            assert (
                left["ranked_top_k_source_indices"]
                == right["ranked_top_k_source_indices"]
            )
            assert left["selected_source_indices"] == right["selected_source_indices"]
            assert left["selected_action_sha256"] == right["selected_action_sha256"]
            assert left["scheduler_objective"] == right["scheduler_objective"]
            assert left["score_ratio"] == right["score_ratio"]


def test_bad_emitted_semantics_falls_back_to_direct_and_closes_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_verify = evaluation_module.verify_vector_oracle_semantics

    def fail_non_direct(program, **kwargs):
        result = real_verify(program, **kwargs)
        if program.actions:
            return replace(
                result,
                ok=False,
                output_mismatches=max(1, result.output_mismatches),
                first_failure={"injected_test_failure": True},
            )
        return result

    monkeypatch.setattr(
        evaluation_module, "verify_vector_oracle_semantics", fail_non_direct
    )
    result = evaluate_replay_training_heldout_v1(
        _models(),
        seed=888,
        cases_per_width=1,
        top_k=4,
        bootstrap_resamples=32,
        signflip_resamples=32,
    )

    degraded = 0
    for row in result["case_rows"]:
        for arm in SOURCE_ARMS:
            arm_row = row["arms"][arm]
            # Some exact selections can legitimately use only dummy slots.  Any
            # non-direct attempted program, however, must fail closed to direct.
            if arm_row.get("attempted_selected_action_sha256"):
                degraded += 1
                assert arm_row["degraded"] is True
                assert arm_row["semantic_verification"] is True
                assert arm_row["attempted_semantic_verification"]["ok"] is False
                assert arm_row["selected_action_sha256"] == []
                assert arm_row["score_ratio"] == 1.0
                assert arm_row["observed_score_ratio_y"] is None
                assert arm_row["itt_score_ratio_y"] == 1.0
                assert arm_row["direct_fallback_used"] is True
                assert arm_row["failure_type"] == "SemanticVerificationFailure"
    assert degraded > 0
    assert result["statistics"]["claim_gate"]["claim_supported"] is False


def test_paired_statistics_are_width_equal_deterministic_and_claim_gated() -> None:
    rows = tuple(
        _stats_case(width=width, index=index) for width in (4, 5) for index in range(6)
    )
    first = paired_arm_statistics_v1(
        rows,
        resamples=256,
        signflip_resamples=256,
        bootstrap_seed=999,
        signflip_seed=1000,
    )
    second = paired_arm_statistics_v1(
        rows,
        resamples=256,
        signflip_resamples=256,
        bootstrap_seed=999,
        signflip_seed=1000,
    )

    assert first == second
    primary = first["primary"]
    assert primary["role"] == "primary_claim_gating_comparison"
    assert primary["case_count"] == 12
    assert primary["width_case_counts"] == {"4": 6, "5": 6}
    assert primary["effect_estimate"] == pytest.approx(-0.20)
    assert primary["width_mean_effects"] == pytest.approx({"4": -0.20, "5": -0.20})
    assert primary["bootstrap"]["ci_upper"] < 0.0
    assert primary["signflip"]["method"] == ("exact_all_cluster_sign_assignments")
    assert primary["signflip"]["assignments"] == 1 << 12
    assert primary["signflip"]["p_value"] < 0.05
    assert first["claim_gate"]["claim_supported"] is True
    assert all(
        comparison["role"] == "secondary_descriptive_only_not_claim_gating"
        for comparison in first["secondary"]
    )

    failed = list(rows)
    failed[0] = _stats_case(width=4, index=0, qaoa_valid=False)
    closed = paired_arm_statistics_v1(
        tuple(failed),
        resamples=64,
        signflip_resamples=64,
        bootstrap_seed=999,
        signflip_seed=1000,
    )
    assert closed["primary"]["direct_fallback_pair_count"] == 1
    assert closed["claim_gate"]["all_primary_pairs_valid_without_fallback"] is False
    assert closed["claim_gate"]["claim_supported"] is False


def test_bad_model_contract_is_itt_direct_fallback_not_a_partial_result() -> None:
    models = _models()
    models["qaoa_final_measurement_replay"] = lambda vector, actions: (
        [0.0] * (len(actions) - 1),
        -1.0,
    )
    result = evaluate_replay_training_heldout_v1(
        models,
        seed=222,
        cases_per_width=1,
        top_k=3,
        bootstrap_resamples=32,
        signflip_resamples=32,
    )
    for row in result["case_rows"]:
        arm = row["arms"]["qaoa_final_measurement_replay"]
        assert arm["failure_stage"] == "model_forward"
        assert arm["failure_type"] == "ValueError"
        assert arm["selected_action_sha256"] == []
        assert arm["score_ratio"] == arm["itt_score_ratio_y"] == 1.0
        assert arm["semantic_verification"] is True
        assert arm["degraded"] is True
    assert result["statistics"]["claim_gate"]["claim_supported"] is False


def test_model_mapping_and_fixed_protocol_bounds_fail_closed() -> None:
    class _ModelMap(dict):
        pass

    with pytest.raises(TypeError, match="exact native dict"):
        evaluate_replay_training_heldout_v1(_ModelMap())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exactly the four"):
        evaluate_replay_training_heldout_v1({})
    with pytest.raises(ValueError, match="top_k"):
        evaluate_replay_training_heldout_v1(_models(), top_k=11)
    with pytest.raises(ValueError, match="scheduler_budget"):
        evaluate_replay_training_heldout_v1(_models(), scheduler_budget=3)
    with pytest.raises(TypeError, match="exact SharedUtilityWeights"):
        evaluate_replay_training_heldout_v1(
            _models(), utility_weights={"t": 1.0}  # type: ignore[arg-type]
        )
