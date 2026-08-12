#!/usr/bin/env python3
"""Contract tests for the isolated E6-v2 single-arm head trainer."""

from __future__ import annotations

from dataclasses import replace
import inspect
import json
from types import SimpleNamespace

import pytest
import torch

import e6.isolated_head_trainer_v2 as trainer_module
from e6.final_measurement_replay_v2 import (
    EXTERNAL_LOCK_AUTHORITY,
    EXTERNAL_REPLAY_LOCK_V2_SCHEMA,
    SOURCE_ARMS,
    ComputeBudgetV2,
    ExternalReplayLockV2,
    ObservationOriginV2,
    SplitRegistryEntryV2,
    SplitRegistrySourceV2,
    build_classical_greedy_observation_v2,
    build_classical_random_observation_v2,
    build_qaoa_final_measurement_observation_v2,
    build_qaoa_permuted_label_control_v2,
    build_replay_group_manifest_v2,
    build_split_registry_v2,
    qaoa_counts_payload_bytes_v2,
)
from e6.frozen_case import build_frozen_shared_case
from e6.isolated_head_trainer_v2 import (
    CORPUS_LOCK_AUTHORITY,
    ISOLATED_HEAD_TRAINER_V3_SCHEMA,
    ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
    ISOLATED_HEAD_TRAINING_CONFIG_V3_SCHEMA,
    ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA,
    LEGACY_REPLAY_TARGET_MODE,
    QAOA_RESOURCE_GAIN_TARGET_MODE,
    LockedReplayTrainingGroupV2,
    fit_isolated_head_from_locked_replay_v2,
)
from e6.shared_oracle import MonomialSharedAction, VectorANF
from e6.shared_scheduler import SharedSchedulerConfig
from src.contracts.codec import canonical_json_bytes, sha256_bytes


CHECKPOINT_SHA = "a" * 64
ORIGIN_SHA = "b" * 64
FAMILY_ID = "synthetic/train/n6-family-0001"
GROUP_NONCE = "unit/n6-equal-observation-group-0001"
PROTOCOL_PAYLOAD = canonical_json_bytes(
    {"schema_version": "unit.e6-trainer-protocol.v1", "locked": True}
)
SOURCE_MANIFEST_PAYLOAD = canonical_json_bytes(
    {"schema_version": "unit.e6-trainer-source-manifest.v1", "groups": 1}
)
PROTOCOL_SHA = sha256_bytes(PROTOCOL_PAYLOAD)
SOURCE_MANIFEST_SHA = sha256_bytes(SOURCE_MANIFEST_PAYLOAD)
FINAL_PARAMETER_PAYLOAD = canonical_json_bytes(
    {"betas": [0.1], "gammas": [0.2]}
)
RUN_ATTESTATION = canonical_json_bytes(
    {"backend": "numpy_statevector", "run": "unit-n6"}
)
OBSERVATION_BUDGET = 16
QAOA_COUNTS = {
    "10100": 5,
    "01100": 3,
    "10010": 2,
    "01010": 1,
    "00110": 2,
    "00011": 1,
    "11000": 1,
    "00000": 1,
}


class _MaliciousRegistryEntry(SplitRegistryEntryV2):
    to_dict_calls = 0

    def to_dict(self):
        type(self).to_dict_calls += 1
        raise AssertionError("malicious registry entry to_dict executed")


class _VectorSubclass(VectorANF):
    pass


def _case(*, input_count: int = 6):
    vector = VectorANF(
        input_count,
        (
            frozenset({0b000111}),
            frozenset({0b000111}),
            frozenset({0b000111}),
            frozenset({0b000111}),
            frozenset({0b001011}),
            frozenset({0b001011}),
            frozenset({0b001011}),
        ),
    )
    actions = (
        MonomialSharedAction(0b000111, (0, 1, 2)),
        MonomialSharedAction(0b000111, (1, 2, 3)),
        MonomialSharedAction(0b001011, (4, 5, 6)),
    )
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=SharedSchedulerConfig(
            budget_requested=2,
            qaoa_seed=20260907,
            qaoa_shots=OBSERVATION_BUDGET,
            qaoa_p=1,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=2,
            qaoa_max_variables=12,
            audit_max_variables=12,
        ),
        raw_utilities=(3.0, 2.0, 1.0),
        learned_utilities=(3.0, 2.0, 1.0),
    )


def _locked_material(*, input_count: int = 6):
    case = _case(input_count=input_count)
    origin = ObservationOriginV2(
        origin_kind="synthetic",
        origin_id=f"synthetic/source/n{input_count}-0001",
        origin_content_sha256=ORIGIN_SHA,
        cryptographic_primitive=None,
        crypto_partition="not_applicable",
        crypto_holdout_leakage_risk=False,
    )
    registry = build_split_registry_v2(
        (
            SplitRegistrySourceV2(
                family_id=FAMILY_ID,
                vector_or_case=case,
                split_role="train_replay",
                origin=origin,
            ),
        )
    )
    random_record = build_classical_random_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        observation_budget=OBSERVATION_BUDGET,
        group_nonce=GROUP_NONCE,
        seed=7,
    )
    greedy_record = build_classical_greedy_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        observation_budget=OBSERVATION_BUDGET,
        group_nonce=GROUP_NONCE,
        seed=7,
    )
    counts_payload = qaoa_counts_payload_bytes_v2(
        case, QAOA_COUNTS, execution_class="direct_unrepaired"
    )
    qaoa_record = build_qaoa_final_measurement_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        group_nonce=GROUP_NONCE,
        counts=QAOA_COUNTS,
        execution_class="direct_unrepaired",
        final_parameter_payload_sha256=sha256_bytes(FINAL_PARAMETER_PAYLOAD),
        counts_source_sha256=sha256_bytes(counts_payload),
        source_trust="externally_attested_source",
        source_attestation_sha256=sha256_bytes(RUN_ATTESTATION),
        compute_budget=ComputeBudgetV2(
            quantum_circuit_executions=10,
            statevector_expectation_evaluations=10,
            classical_candidate_evaluations=0,
            qubo_assignments_audited=1 << case.augmented_variable_count,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=OBSERVATION_BUDGET,
            declared_wall_seconds=None,
            notes="unit QAOA final-measurement work; not arm-equal",
        ),
    )
    control_record = build_qaoa_permuted_label_control_v2(
        qaoa_record,
        case,
        registry,
        expected_source_observation_sha256=qaoa_record.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
        permutation_seed=11,
    )
    records = (random_record, greedy_record, qaoa_record, control_record)
    manifest = build_replay_group_manifest_v2(
        records,
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        protocol_sha256=PROTOCOL_SHA,
        source_manifest_sha256=SOURCE_MANIFEST_SHA,
    )
    unsigned_lock = {
        "schema_version": EXTERNAL_REPLAY_LOCK_V2_SCHEMA,
        "authority": EXTERNAL_LOCK_AUTHORITY,
        "manifest_sha256": manifest.manifest_sha256,
        "split_registry_sha256": registry.registry_sha256,
        "protocol_sha256": PROTOCOL_SHA,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA,
        "qaoa_observation_sha256": qaoa_record.observation_sha256,
        "qaoa_control_observation_sha256": control_record.observation_sha256,
        "qaoa_counts_payload_sha256": sha256_bytes(counts_payload),
        "qaoa_final_parameter_payload_sha256": sha256_bytes(
            FINAL_PARAMETER_PAYLOAD
        ),
        "qaoa_run_attestation_sha256": sha256_bytes(RUN_ATTESTATION),
    }
    lock = ExternalReplayLockV2.from_mapping(
        {
            **unsigned_lock,
            "lock_sha256": sha256_bytes(canonical_json_bytes(unsigned_lock)),
        }
    )
    material = LockedReplayTrainingGroupV2(
        case=case,
        records=records,
        manifest=manifest,
        external_lock_payload=canonical_json_bytes(lock.to_dict()),
        qaoa_counts_payload=counts_payload,
        final_parameter_payload=FINAL_PARAMETER_PAYLOAD,
        run_attestation=RUN_ATTESTATION,
        protocol_payload=PROTOCOL_PAYLOAD,
        source_manifest_payload=SOURCE_MANIFEST_PAYLOAD,
    )
    return material, registry, lock


def _config_payload(*, source_arm: str = "classical_greedy_repeated_selection_replay"):
    payload = {
        "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
        "source_arm": source_arm,
        "update_steps": 2,
        "batch_size": 1,
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
        "policy_loss_weight": 1.0,
        "value_loss_weight": 1.0,
        "max_grad_norm": 1.0,
        "head_hidden": 8,
        "head_seed": 20260907,
        "sampler_seed": 20260908,
        "device": "cpu",
        "dtype": "float32",
        "cpu_threads": 1,
        "optimizer": "HeadOnlyIntegrityAdamW",
        "scheduler": "none",
        "early_stopping": False,
        "resume": False,
        "performance_evidence": False,
    }
    return canonical_json_bytes(payload)


def _v3_config_payload(
    *,
    source_arm: str = "qaoa_final_measurement_replay",
    target_mode: str = QAOA_RESOURCE_GAIN_TARGET_MODE,
    policy_loss_weight: float = 1.0,
    value_loss_weight: float = 0.0,
):
    payload = json.loads(_config_payload(source_arm=source_arm))
    payload.update(
        {
            "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V3_SCHEMA,
            "target_mode": target_mode,
            "policy_loss_weight": policy_loss_weight,
            "value_loss_weight": value_loss_weight,
        }
    )
    return canonical_json_bytes(payload)


def _corpus_payload(material, registry, lock):
    group = {
        "group_id": material.manifest.group_id,
        "case_sha256": material.case.case_sha256,
        "manifest_sha256": material.manifest.manifest_sha256,
        "external_lock_sha256": lock.lock_sha256,
        "arm_observation_sha256": [
            list(item) for item in material.manifest.arm_observation_sha256
        ],
        "qaoa_counts_payload_sha256": sha256_bytes(
            material.qaoa_counts_payload
        ),
        "qaoa_final_parameter_payload_sha256": sha256_bytes(
            material.final_parameter_payload
        ),
        "qaoa_run_attestation_sha256": sha256_bytes(material.run_attestation),
    }
    unsigned = {
        "schema_version": ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA,
        "authority": CORPUS_LOCK_AUTHORITY,
        "foundation_checkpoint_sha256": trainer_module.FORMAL_V4_CHECKPOINT_SHA256,
        "protocol_sha256": PROTOCOL_SHA,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA,
        "split_registry_sha256": registry.registry_sha256,
        "source_arms": list(SOURCE_ARMS),
        "training_split_role": "train_replay",
        "training_input_counts": [6, 7],
        "origin_kind": "synthetic",
        "groups": [group],
        "performance_evidence": False,
    }
    return canonical_json_bytes(
        {**unsigned, "lock_sha256": sha256_bytes(canonical_json_bytes(unsigned))}
    )


def _fit(material, registry, corpus_payload, config_payload):
    return fit_isolated_head_from_locked_replay_v2(
        (material,),
        registry,
        corpus_lock_payload=corpus_payload,
        expected_corpus_lock_payload_sha256=sha256_bytes(corpus_payload),
        config_payload=config_payload,
        expected_config_payload_sha256=sha256_bytes(config_payload),
    )


def test_public_fit_is_raw_material_only_and_trains_heads_without_claims() -> None:
    parameters = inspect.signature(
        fit_isolated_head_from_locked_replay_v2
    ).parameters
    assert not {
        "model",
        "targets",
        "target",
        "target_mode",
        "policy_target_transform",
        "callback",
        "capability",
        "optimizer",
    } & set(parameters)
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()

    result = _fit(material, registry, corpus, config)
    report = result.report

    assert type(report) is trainer_module.IsolatedHeadTrainingReportV2
    assert report.schema_version == trainer_module.ISOLATED_HEAD_TRAINER_V2_SCHEMA
    assert report.source_arm == "classical_greedy_repeated_selection_replay"
    assert report.sample_count == 1
    assert report.input_counts == (6,)
    assert report.update_steps == 2
    assert report.sample_presentations == 2
    assert report.initial_head_tensor_sha256 != report.final_head_tensor_sha256
    assert result.model.current_head_tensor_sha256() == report.final_head_tensor_sha256
    assert result.model.head_training_status == "modified_unsealed"
    assert all(not parameter.requires_grad for parameter in result.model.head_parameters())
    assert all(parameter.grad is None for parameter in result.model.foundation_trunk.parameters())
    assert report.compute_budget_equal is False
    assert report.formal_evaluation is False
    assert report.performance_evidence is False
    assert "unsealed" in report.claim_boundary


def test_training_is_exactly_deterministic_for_the_same_locked_inputs() -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()

    left = _fit(material, registry, corpus, config).report
    right = _fit(material, registry, corpus, config).report

    assert left.training_schedule_sha256 == right.training_schedule_sha256
    assert left.initial_head_tensor_sha256 == right.initial_head_tensor_sha256
    assert left.final_head_tensor_sha256 == right.final_head_tensor_sha256
    assert left.initial_weighted_loss == right.initial_weighted_loss
    assert left.final_weighted_loss == right.final_weighted_loss
    assert left.training_schedule_sha256 == (
        "0c7122c0e689e33e0ade6da89a79e3ed0859b001353c6675f7cee7f8a294fd1f"
    )
    assert left.initial_head_tensor_sha256 == (
        "9119b1a067a65de718c1e22b389c05178b72b6bc8b1e5253766dbba6332d9fb0"
    )
    assert left.final_head_tensor_sha256 == (
        "5ded67de994587b2ea65a5e75dbd775401b977162b9c5aac13fd1d818b856726"
    )
    assert left.initial_weighted_loss == 2.8449807167053223
    assert left.final_weighted_loss == 1.443328619003296


def test_v3_legacy_mode_preserves_v2_training_semantics() -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    v2 = _fit(material, registry, corpus, _config_payload()).report
    v3 = _fit(
        material,
        registry,
        corpus,
        _v3_config_payload(
            source_arm="classical_greedy_repeated_selection_replay",
            target_mode=LEGACY_REPLAY_TARGET_MODE,
            value_loss_weight=1.0,
        ),
    ).report

    assert type(v2) is trainer_module.IsolatedHeadTrainingReportV2
    assert type(v3) is trainer_module.IsolatedHeadTrainingReportV3
    assert v2.initial_head_tensor_sha256 == v3.initial_head_tensor_sha256
    assert v2.final_head_tensor_sha256 == v3.final_head_tensor_sha256
    assert v2.initial_weighted_loss == v3.initial_weighted_loss
    assert v2.final_weighted_loss == v3.final_weighted_loss
    assert v3.schema_version == ISOLATED_HEAD_TRAINER_V3_SCHEMA
    assert v3.target_mode == LEGACY_REPLAY_TARGET_MODE
    assert v3.source_group_count == 1
    assert v3.zero_gain_skipped_group_count == 0
    assert v3.sample_count == 1
    assert v3.sample_presentations == v2.sample_presentations == 2


@pytest.mark.parametrize(
    "source_arm",
    ("qaoa_final_measurement_replay", "qaoa_permuted_label_control"),
)
def test_v3_resource_gain_source_and_control_are_deterministic(
    source_arm: str,
) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _v3_config_payload(source_arm=source_arm)

    left = _fit(material, registry, corpus, config).report
    right = _fit(material, registry, corpus, config).report

    assert type(left) is trainer_module.IsolatedHeadTrainingReportV3
    assert left == right
    assert left.schema_version == ISOLATED_HEAD_TRAINER_V3_SCHEMA
    assert left.target_mode == QAOA_RESOURCE_GAIN_TARGET_MODE
    assert left.source_arm == source_arm
    assert left.source_group_count == left.sample_count == 1
    assert left.zero_gain_skipped_group_count == 0
    assert left.sample_presentations == 2
    assert left.formal_evaluation is False
    assert left.performance_evidence is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        (
            {"source_arm": "classical_greedy_repeated_selection_replay"},
            "requires a QAOA source arm",
        ),
        ({"policy_loss_weight": 0.0}, "requires policy loss"),
        ({"value_loss_weight": 1.0}, "requires value_loss_weight=0"),
        ({"target_mode": "caller_defined"}, "target_mode is not registered"),
    ),
)
def test_v3_resource_gain_invalid_combinations_fail_before_model(
    monkeypatch, kwargs: dict[str, object], message: str
) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    model_calls = 0

    def forbidden_model(*args, **kw):
        nonlocal model_calls
        model_calls += 1
        raise AssertionError("model must not be constructed")

    monkeypatch.setattr(
        trainer_module, "FrozenFoundationV4SharedPolicyValueV2", forbidden_model
    )
    with pytest.raises(ValueError, match=message):
        _fit(material, registry, corpus, _v3_config_payload(**kwargs))
    assert model_calls == 0


def test_v3_resource_gain_all_zero_fails_before_model_or_optimizer(
    monkeypatch,
) -> None:
    import e6.resource_gain_replay_teacher_v1 as gain_module

    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    model_calls = 0
    optimizer_calls = 0

    def no_gain(**kwargs):
        del kwargs
        return SimpleNamespace(
            source_replay_target=None,
            control_replay_target=None,
        )

    def forbidden_model(*args, **kwargs):
        nonlocal model_calls
        model_calls += 1
        raise AssertionError("model must not be constructed")

    def forbidden_optimizer(*args, **kwargs):
        nonlocal optimizer_calls
        optimizer_calls += 1
        raise AssertionError("optimizer must not be constructed")

    monkeypatch.setattr(
        gain_module,
        "derive_resource_gain_replay_teacher_pair_from_validated_v1",
        no_gain,
    )
    monkeypatch.setattr(
        trainer_module, "FrozenFoundationV4SharedPolicyValueV2", forbidden_model
    )
    monkeypatch.setattr(
        trainer_module, "build_head_only_optimizer", forbidden_optimizer
    )
    with pytest.raises(ValueError, match="retained zero training groups"):
        _fit(
            material,
            registry,
            corpus,
            _v3_config_payload(),
        )
    assert model_calls == optimizer_calls == 0


def test_v3_resource_gain_mixed_groups_schedule_only_retained_samples(
    monkeypatch,
) -> None:
    import e6.resource_gain_replay_teacher_v1 as gain_module
    from e6.replay_training_corpus_v1 import (
        CorpusBuildSpecV1,
        build_replay_training_corpus_v1,
    )

    corpus = build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=20261011,
            cases_per_width=1,
            observation_budget=64,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=2,
        )
    )
    assert len(corpus.groups) == 2
    skipped_group_id = corpus.groups[0].material.manifest.group_id
    retained_group_id = corpus.groups[1].material.manifest.group_id
    original = gain_module.derive_resource_gain_replay_teacher_pair_from_validated_v1

    def skip_one(**kwargs):
        if kwargs["source_record"].group_id == skipped_group_id:
            return SimpleNamespace(
                source_replay_target=None,
                control_replay_target=None,
            )
        return original(**kwargs)

    monkeypatch.setattr(
        gain_module,
        "derive_resource_gain_replay_teacher_pair_from_validated_v1",
        skip_one,
    )
    config = _v3_config_payload()
    result = fit_isolated_head_from_locked_replay_v2(
        corpus.materials,
        corpus.registry,
        corpus_lock_payload=corpus.corpus_lock_payload,
        expected_corpus_lock_payload_sha256=sha256_bytes(
            corpus.corpus_lock_payload
        ),
        config_payload=config,
        expected_config_payload_sha256=sha256_bytes(config),
    )
    report = result.report
    assert type(report) is trainer_module.IsolatedHeadTrainingReportV3
    assert report.source_group_count == 2
    assert report.sample_count == 1
    assert report.zero_gain_skipped_group_count == 1
    assert report.group_ids == (retained_group_id,)
    assert report.sample_presentations == 2
    expected_schedule = canonical_json_bytes(
        {
            "schema_version": "xa.e6-isolated-head-training-schedule.v3",
            "sampler_seed": 20260908,
            "update_steps": 2,
            "batch_size": 1,
            "group_ids_by_presentation": [retained_group_id, retained_group_id],
            "target_mode": QAOA_RESOURCE_GAIN_TARGET_MODE,
            "source_group_count": 2,
            "zero_gain_skipped_group_count": 1,
            "retained_group_ids": [retained_group_id],
        }
    )
    assert report.training_schedule_sha256 == sha256_bytes(expected_schedule)
    assert "unsealed" not in report.claim_boundary
    assert report.formal_evaluation is False
    assert report.performance_evidence is False


@pytest.mark.parametrize(
    ("field", "tampered", "message"),
    (
        ("protocol_payload", b"tampered protocol", "protocol payload"),
        ("qaoa_counts_payload", b"tampered counts", "QAOA counts payload"),
        ("final_parameter_payload", b"tampered parameters", "final-parameter"),
        ("run_attestation", b"tampered attestation", "run-attestation"),
    ),
)
def test_actual_payload_tamper_fails_before_optimizer_and_mutates_nothing(
    monkeypatch, field: str, tampered: bytes, message: str
) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    original_case_sha = material.case.case_sha256
    original_head_builder = trainer_module.build_head_only_optimizer
    optimizer_calls = 0

    def counted_builder(*args, **kwargs):
        nonlocal optimizer_calls
        optimizer_calls += 1
        return original_head_builder(*args, **kwargs)

    monkeypatch.setattr(trainer_module, "build_head_only_optimizer", counted_builder)
    poisoned = replace(material, **{field: tampered})

    with pytest.raises(ValueError, match=message):
        _fit(poisoned, registry, corpus, config)

    assert optimizer_calls == 0
    assert material.case.case_sha256 == original_case_sha
    assert poisoned.case is material.case


def test_external_config_and_corpus_anchors_fail_before_optimizer(monkeypatch) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    optimizer_calls = 0

    def forbidden_builder(*args, **kwargs):
        nonlocal optimizer_calls
        optimizer_calls += 1
        raise AssertionError("optimizer must not be built")

    monkeypatch.setattr(trainer_module, "build_head_only_optimizer", forbidden_builder)
    with pytest.raises(ValueError, match="independent anchor"):
        fit_isolated_head_from_locked_replay_v2(
            (material,),
            registry,
            corpus_lock_payload=corpus,
            expected_corpus_lock_payload_sha256="0" * 64,
            config_payload=config,
            expected_config_payload_sha256=sha256_bytes(config),
        )
    with pytest.raises(ValueError, match="independent anchor"):
        fit_isolated_head_from_locked_replay_v2(
            (material,),
            registry,
            corpus_lock_payload=corpus,
            expected_corpus_lock_payload_sha256=sha256_bytes(corpus),
            config_payload=config,
            expected_config_payload_sha256="0" * 64,
        )
    assert optimizer_calls == 0


def test_n4_material_is_rejected_before_optimizer(monkeypatch) -> None:
    material, registry, lock = _locked_material(input_count=4)
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    optimizer_calls = 0

    def forbidden_builder(*args, **kwargs):
        nonlocal optimizer_calls
        optimizer_calls += 1
        raise AssertionError("optimizer must not be built")

    monkeypatch.setattr(trainer_module, "build_head_only_optimizer", forbidden_builder)
    with pytest.raises(ValueError, match="n=6/7"):
        _fit(material, registry, corpus, config)
    assert optimizer_calls == 0


def test_malicious_registry_entry_subclass_is_rejected_without_dispatch_or_model(
    monkeypatch,
) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    entry = registry.entries[0]
    malicious = _MaliciousRegistryEntry(
        family_id=entry.family_id,
        orbit_cluster_sha256=entry.orbit_cluster_sha256,
        vector_sha256=entry.vector_sha256,
        split_role=entry.split_role,
        origin=entry.origin,
    )
    poisoned_registry = replace(registry, entries=(malicious,))
    model_calls = 0

    def forbidden_model(*args, **kwargs):
        nonlocal model_calls
        model_calls += 1
        raise AssertionError("model constructor must not run")

    _MaliciousRegistryEntry.to_dict_calls = 0
    monkeypatch.setattr(
        trainer_module, "FrozenFoundationV4SharedPolicyValueV2", forbidden_model
    )
    with pytest.raises(TypeError, match="forbidden public graph type"):
        _fit(material, poisoned_registry, corpus, config)
    assert _MaliciousRegistryEntry.to_dict_calls == 0
    assert model_calls == 0


def test_vector_subclass_and_non_native_material_sequence_fail_before_model(
    monkeypatch,
) -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    vector = material.case.vector
    poisoned_vector = _VectorSubclass(vector.input_count, vector.outputs)
    poisoned_case = replace(material.case, vector=poisoned_vector)
    poisoned_material = replace(material, case=poisoned_case)
    model_calls = 0

    def forbidden_model(*args, **kwargs):
        nonlocal model_calls
        model_calls += 1
        raise AssertionError("model constructor must not run")

    monkeypatch.setattr(
        trainer_module, "FrozenFoundationV4SharedPolicyValueV2", forbidden_model
    )
    with pytest.raises(TypeError, match="forbidden public graph type"):
        _fit(poisoned_material, registry, corpus, config)
    with pytest.raises(TypeError, match="exact native tuple"):
        fit_isolated_head_from_locked_replay_v2(
            [material],  # type: ignore[arg-type]
            registry,
            corpus_lock_payload=corpus,
            expected_corpus_lock_payload_sha256=sha256_bytes(corpus),
            config_payload=config,
            expected_config_payload_sha256=sha256_bytes(config),
        )
    assert model_calls == 0


def test_deterministic_context_restores_warn_only_mode_exactly() -> None:
    material, registry, lock = _locked_material()
    corpus = _corpus_payload(material, registry, lock)
    config = _config_payload()
    previous_mode = torch.get_deterministic_debug_mode()
    try:
        torch.set_deterministic_debug_mode("warn")
        assert torch.get_deterministic_debug_mode() == 1
        _fit(material, registry, corpus, config)
        assert torch.get_deterministic_debug_mode() == 1
    finally:
        torch.set_deterministic_debug_mode(previous_mode)
