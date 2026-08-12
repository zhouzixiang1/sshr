#!/usr/bin/env python3
"""Tests for the isolated E6 D2 resource-gain replay teacher."""

from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest

from e6.final_measurement_replay_v2 import (
    BitstringAuditV2,
    ReplayTargetsV2,
    validate_external_replay_lock_v2,
)
from e6.frozen_case import FrozenSharedCase, build_frozen_shared_case
from e6.replay_training_corpus_v1 import (
    CorpusBuildSpecV1,
    build_replay_training_corpus_v1,
)
from e6.resource_gain_replay_teacher_v1 import (
    POLICY_WEIGHT_FORMULA,
    RESOURCE_GAIN_FORMULA,
    derive_resource_gain_policy_from_bitstring_audit_v1,
    derive_resource_gain_replay_target_v1,
    derive_resource_gain_replay_teacher_pair_from_group_v1,
    derive_resource_gain_replay_teacher_pair_from_validated_v1,
    project_eligible_resource_gain_targets_v1,
)
from e6.shared_oracle import (
    MonomialSharedAction,
    VectorANF,
    emit_shared_oracle,
)
from e6.shared_scheduler import SharedSchedulerConfig, program_resource_summary


def _config(*, budget: int = 1, shots: int = 16) -> SharedSchedulerConfig:
    return SharedSchedulerConfig(
        method="greedy",
        budget_requested=budget,
        qaoa_seed=20261013,
        qaoa_shots=shots,
        qaoa_optimizer_restarts=1,
        qaoa_optimizer_steps=0,
        qaoa_max_variables=12,
        audit_max_variables=12,
    )


def _improving_case() -> FrozenSharedCase:
    vector = VectorANF(
        5,
        (
            frozenset({0b00111, 0b00001}),
            frozenset({0b00111, 0b00010}),
            frozenset({0b00111, 0b00100}),
            frozenset({0b00011, 0b01000}),
            frozenset({0b00011, 0b10000}),
            frozenset({0b00011, 0b00001}),
        ),
    )
    actions = (
        MonomialSharedAction(0b00111, (0, 1, 2)),
        MonomialSharedAction(0b00011, (3, 4, 5)),
    )
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256="a" * 64,
        config=_config(),
        raw_utilities=(1.0, 2.0),
        learned_utilities=(1.0, 2.0),
    )


def _harmful_case() -> FrozenSharedCase:
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
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256="b" * 64,
        config=_config(),
        raw_utilities=(1.0, 2.0),
        learned_utilities=(0.5, 0.6),
    )


def _row(
    case: FrozenSharedCase, bits: tuple[int, ...], count: int
) -> BitstringAuditV2:
    selected = case.qubo.selected_real(bits)
    return BitstringAuditV2(
        bitstring=bits,
        count=count,
        cardinality=sum(bits),
        source_selected_real_indices=selected,
        label_aligned_selected_real_indices=selected,
        dummy_selected=sum(bits[len(case.actions) :]),
        conflict_count=case.qubo.conflict_count(bits),
        feasible=case.qubo.is_feasible(bits),
        phase_energy=float(case.qubo.phase_energy(bits)),
    )


def _score(case: FrozenSharedCase, selected: tuple[int, ...]) -> float:
    return float(
        program_resource_summary(
            emit_shared_oracle(
                case.vector, tuple(case.actions[index] for index in selected)
            ),
            weights=case.utility_weights,
        ).total_abstract_score
    )


def test_exact_gain_credit_formula_excludes_infeasible_and_dummy_rows() -> None:
    case = _improving_case()
    rows = tuple(
        sorted(
            (
                _row(case, (1, 0, 0), 2),  # source action 0
                _row(case, (0, 1, 0), 3),  # source action 1
                _row(case, (0, 0, 1), 1),  # feasible dummy-only
                _row(case, (1, 1, 0), 4),  # infeasible: must add no credit
            ),
            key=lambda row: row.bitstring,
        )
    )
    result = derive_resource_gain_policy_from_bitstring_audit_v1(
        case, rows, total_observed=10
    )

    direct = _score(case, ())
    gain0 = max(0.0, 1.0 - _score(case, (0,)) / direct)
    gain1 = max(0.0, 1.0 - _score(case, (1,)) / direct)
    expected_credit = (2.0 * gain0, 3.0 * gain1)
    expected_total = math.fsum(expected_credit)

    assert result.eligible is True
    assert result.ineligibility_reasons == ()
    assert result.gain_formula == RESOURCE_GAIN_FORMULA
    assert result.policy_weight_formula == POLICY_WEIGHT_FORMULA
    assert result.direct_program_score == direct
    assert result.action_credits == pytest.approx(expected_credit, abs=1.0e-15)
    assert result.total_action_credit == pytest.approx(expected_total, abs=1.0e-15)
    assert result.policy_target == pytest.approx(
        tuple(value / expected_total for value in expected_credit), abs=1.0e-15
    )
    assert result.policy_observation_weight == pytest.approx(
        expected_total / (10 * case.budget_effective), abs=1.0e-15
    )
    assert result.feasible_observed == 6
    assert result.infeasible_observed == 4
    assert result.positive_gain_observed == 5
    assert result.positive_gain_bitstring_count == 2
    assert result.zero_gain_feasible_observed == 1

    diagnostics = {item.bitstring: item for item in result.bitstring_diagnostics}
    assert diagnostics[(0, 0, 1)].dummy_selected == 1
    assert diagnostics[(0, 0, 1)].resource_gain == 0.0
    assert diagnostics[(1, 1, 0)].feasible is False
    assert diagnostics[(1, 1, 0)].selected_program_score is None
    assert diagnostics[(1, 1, 0)].resource_gain == 0.0
    assert derive_resource_gain_policy_from_bitstring_audit_v1(
        case, rows, total_observed=10
    ) == result
    native = result.to_dict()
    assert type(native["policy_target"]) is list
    assert type(native["bitstring_diagnostics"]) is list
    json.dumps(native, allow_nan=False, sort_keys=True)


def test_all_zero_gain_is_explicitly_ineligible_without_fallback() -> None:
    case = _harmful_case()
    rows = tuple(
        sorted(
            (
                _row(case, (1, 0, 0), 5),  # selected action is harmful
                _row(case, (0, 0, 1), 3),  # dummy-only ties direct
            ),
            key=lambda row: row.bitstring,
        )
    )
    result = derive_resource_gain_policy_from_bitstring_audit_v1(
        case, rows, total_observed=8
    )

    assert _score(case, (0,)) > _score(case, ())
    assert result.eligible is False
    assert result.ineligibility_reasons == ("no_positive_resource_gain_credit",)
    assert result.action_credits == (0.0, 0.0)
    assert result.total_action_credit == 0.0
    assert result.policy_target == ()
    assert result.policy_observation_weight == 0.0
    assert result.positive_gain_observed == 0
    assert result.zero_gain_feasible_observed == 8


def test_bitstring_audit_is_strictly_rederived_from_frozen_case() -> None:
    case = _improving_case()
    valid = _row(case, (1, 0, 0), 1)
    forged = replace(valid, feasible=not valid.feasible)
    with pytest.raises(ValueError, match="feasibility changed"):
        derive_resource_gain_policy_from_bitstring_audit_v1(
            case, (forged,), total_observed=1
        )
    with pytest.raises(TypeError, match="native integer"):
        derive_resource_gain_policy_from_bitstring_audit_v1(
            case, (replace(valid, count=True),), total_observed=1
        )
    with pytest.raises(ValueError, match="canonical bitstring order"):
        derive_resource_gain_policy_from_bitstring_audit_v1(
            case,
            (_row(case, (1, 0, 0), 1), _row(case, (0, 1, 0), 1)),
            total_observed=2,
        )


@pytest.fixture(scope="module")
def new_seed_corpus():
    return build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=20261013,
            cases_per_width=1,
            observation_budget=16,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=0,
        )
    )


def test_new_seed_corpus_pair_preserves_permutation_mass_and_projects_targets(
    new_seed_corpus,
) -> None:
    assert len(new_seed_corpus.groups) == 2
    for group in new_seed_corpus.groups:
        pair = derive_resource_gain_replay_teacher_pair_from_group_v1(
            group, new_seed_corpus.registry
        )
        repeated = derive_resource_gain_replay_teacher_pair_from_group_v1(
            group, new_seed_corpus.registry
        )
        assert repeated == pair
        permutation = pair.label_permutation_new_index_to_source_index
        assert pair.control_is_exact_source_permutation is True
        assert pair.control.action_credits == tuple(
            pair.source.action_credits[index] for index in permutation
        )
        assert pair.control.policy_target == tuple(
            pair.source.policy_target[index] for index in permutation
        )
        assert math.fsum(pair.control.action_credits) == pytest.approx(
            math.fsum(pair.source.action_credits), abs=1.0e-15
        )
        assert math.fsum(pair.source.policy_target) == pytest.approx(1.0)
        assert math.fsum(pair.control.policy_target) == pytest.approx(1.0)
        assert pair.source.eligible is True
        assert pair.control.eligible is True
        assert type(pair.source_replay_target) is ReplayTargetsV2
        assert type(pair.control_replay_target) is ReplayTargetsV2

        source_record = group.material.records[2]
        legacy_source = dict(group.targets_by_arm)[source_record.source_arm]
        single = derive_resource_gain_replay_target_v1(
            record=source_record,
            case=group.material.case,
            legacy_target=legacy_source,
        )
        assert single.target == pair.source
        assert type(single.replay_target) is ReplayTargetsV2
        assert single.replay_target.policy_target == pair.source.policy_target
        assert single.replay_target.value_audit == legacy_source.value_audit
        assert (
            single.replay_target.value_target_log_ratio
            == legacy_source.value_target_log_ratio
        )

        projected = dict(project_eligible_resource_gain_targets_v1(pair, group))
        assert set(projected) == {
            "qaoa_final_measurement_replay",
            "qaoa_permuted_label_control",
        }
        for target in (pair.source, pair.control):
            prior = dict(group.targets_by_arm)[target.source_arm]
            updated = projected[target.source_arm]
            assert type(updated) is ReplayTargetsV2
            assert updated.policy_target == target.policy_target
            assert (
                updated.policy_observation_weight
                == target.policy_observation_weight
            )
            assert updated.value_audit == prior.value_audit
            assert updated.value_observation_weight == prior.value_observation_weight
            assert updated.value_target_log_ratio == prior.value_target_log_ratio
        json.dumps(pair.to_dict(), allow_nan=False, sort_keys=True)


def test_trainer_safe_pure_pair_equals_group_adapter_and_exact_permutation(
    new_seed_corpus,
) -> None:
    group = new_seed_corpus.groups[0]
    material = group.material
    validated = validate_external_replay_lock_v2(
        group.technical_lock,
        material.manifest,
        material.records,
        material.case,
        new_seed_corpus.registry,
        expected_lock_sha256=group.technical_lock.lock_sha256,
        qaoa_counts_payload=material.qaoa_counts_payload,
        final_parameter_payload=material.final_parameter_payload,
        run_attestation=material.run_attestation,
    )
    source_record = material.records[2]
    control_record = material.records[3]
    source_audit = validated.audit_for(
        source_record,
        material.case,
        new_seed_corpus.registry,
        expected_observation_sha256=source_record.observation_sha256,
        expected_registry_sha256=new_seed_corpus.registry.registry_sha256,
    )
    control_audit = validated.audit_for(
        control_record,
        material.case,
        new_seed_corpus.registry,
        expected_observation_sha256=control_record.observation_sha256,
        expected_registry_sha256=new_seed_corpus.registry.registry_sha256,
    )
    legacy = dict(group.targets_by_arm)
    pure = derive_resource_gain_replay_teacher_pair_from_validated_v1(
        source_record=source_record,
        control_record=control_record,
        case=material.case,
        source_legacy_target=legacy[source_record.source_arm],
        control_legacy_target=legacy[control_record.source_arm],
        source_audit=source_audit,
        control_audit=control_audit,
    )
    adapted = derive_resource_gain_replay_teacher_pair_from_group_v1(
        group, new_seed_corpus.registry
    )

    assert pure == adapted
    permutation = control_record.label_permutation_new_index_to_source_index
    assert pure.control.action_credits == tuple(
        pure.source.action_credits[index] for index in permutation
    )
    assert pure.control.policy_target == tuple(
        pure.source.policy_target[index] for index in permutation
    )
    assert pure.control_replay_target.policy_target == pure.control.policy_target
    assert pure.source_replay_target.value_audit == source_audit.value_audit
    assert pure.control_replay_target.value_audit == control_audit.value_audit


@pytest.mark.parametrize(
    "field",
    (
        "measurement_semantics",
        "count_bit_order",
        "compute_budget_equal",
        "performance_evidence",
    ),
)
def test_trainer_entrypoints_reject_stale_observation_sha(
    new_seed_corpus, field: str
) -> None:
    group = new_seed_corpus.groups[0]
    material = group.material
    validated = validate_external_replay_lock_v2(
        group.technical_lock,
        material.manifest,
        material.records,
        material.case,
        new_seed_corpus.registry,
        expected_lock_sha256=group.technical_lock.lock_sha256,
        qaoa_counts_payload=material.qaoa_counts_payload,
        final_parameter_payload=material.final_parameter_payload,
        run_attestation=material.run_attestation,
    )
    source_record = material.records[2]
    control_record = material.records[3]
    source_audit = validated.audit_for(
        source_record,
        material.case,
        new_seed_corpus.registry,
        expected_observation_sha256=source_record.observation_sha256,
        expected_registry_sha256=new_seed_corpus.registry.registry_sha256,
    )
    control_audit = validated.audit_for(
        control_record,
        material.case,
        new_seed_corpus.registry,
        expected_observation_sha256=control_record.observation_sha256,
        expected_registry_sha256=new_seed_corpus.registry.registry_sha256,
    )
    legacy = dict(group.targets_by_arm)

    def forged(record):
        original = getattr(record, field)
        changed = not original if type(original) is bool else original + "_forged"
        return replace(record, **{field: changed})

    with pytest.raises(ValueError, match="observation canonical SHA mismatch"):
        derive_resource_gain_replay_target_v1(
            record=forged(source_record),
            case=material.case,
            legacy_target=legacy[source_record.source_arm],
        )
    with pytest.raises(ValueError, match="observation canonical SHA mismatch"):
        derive_resource_gain_replay_teacher_pair_from_validated_v1(
            source_record=forged(source_record),
            control_record=control_record,
            case=material.case,
            source_legacy_target=legacy[source_record.source_arm],
            control_legacy_target=legacy[control_record.source_arm],
            source_audit=source_audit,
            control_audit=control_audit,
        )
    with pytest.raises(ValueError, match="observation canonical SHA mismatch"):
        derive_resource_gain_replay_teacher_pair_from_validated_v1(
            source_record=source_record,
            control_record=forged(control_record),
            case=material.case,
            source_legacy_target=legacy[source_record.source_arm],
            control_legacy_target=legacy[control_record.source_arm],
            source_audit=source_audit,
            control_audit=control_audit,
        )


def test_single_target_adapter_rejects_control_arm(new_seed_corpus) -> None:
    group = new_seed_corpus.groups[0]
    control_record = group.material.records[3]
    control_target = dict(group.targets_by_arm)[control_record.source_arm]
    with pytest.raises(ValueError, match="only QAOA source"):
        derive_resource_gain_replay_target_v1(
            record=control_record,
            case=group.material.case,
            legacy_target=control_target,
        )
