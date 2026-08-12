#!/usr/bin/env python3
"""Tests for the deterministic E6 four-arm replay-training corpus."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from e6.final_measurement_replay_v2 import (
    SOURCE_ARMS,
    ExternalReplayLockV2,
    validate_external_replay_lock_v2,
)
from e6.replay_training_corpus_v1 import (
    CANDIDATE_CAP,
    CORPUS_BUILD_SPEC_V1_SCHEMA,
    INPUT_COUNTS,
    OUTPUT_COUNT,
    SCHEDULER_BUDGET,
    TECHNICAL_LOCK_SEMANTICS,
    CorpusBuildSpecV1,
    ReplayTrainingCorpusDescriptorV1,
    build_replay_training_corpus_v1,
    build_trainer_corpus_lock_payload_v1,
    rebuild_replay_training_corpus_v1,
)
from src.contracts.codec import canonical_json_bytes, sha256_bytes


@pytest.fixture(scope="module")
def tiny_corpus():
    return build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=20260912,
            cases_per_width=2,
            observation_budget=32,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=0,
        )
    )


def test_build_spec_is_strict_and_roundtrips() -> None:
    spec = CorpusBuildSpecV1(
        seed=17,
        cases_per_width=1,
        observation_budget=16,
        qaoa_optimizer_restarts=1,
        qaoa_optimizer_steps=0,
    )
    assert CorpusBuildSpecV1.from_dict(spec.to_dict()) == spec
    assert spec.to_dict()["schema_version"] == CORPUS_BUILD_SPEC_V1_SCHEMA

    missing = spec.to_dict()
    missing.pop("seed")
    with pytest.raises(ValueError, match="field contract"):
        CorpusBuildSpecV1.from_dict(missing)
    extra = {**spec.to_dict(), "unknown": 1}
    with pytest.raises(ValueError, match="field contract"):
        CorpusBuildSpecV1.from_dict(extra)
    with pytest.raises(TypeError, match="native integer"):
        CorpusBuildSpecV1.from_dict({**spec.to_dict(), "seed": True})


def test_tiny_multicase_corpus_has_complete_structured_sources_and_unique_orbits(
    tiny_corpus,
) -> None:
    descriptor = tiny_corpus.descriptor
    assert descriptor.input_counts == INPUT_COUNTS
    assert descriptor.output_count == OUTPUT_COUNT
    assert descriptor.candidate_cap == CANDIDATE_CAP
    assert descriptor.scheduler_budget == SCHEDULER_BUDGET
    assert descriptor.technical_lock_semantics == TECHNICAL_LOCK_SEMANTICS
    assert descriptor.performance_evidence is False
    assert len(descriptor.case_roster) == 4
    assert {item.input_count for item in descriptor.case_roster} == {6, 7}
    assert {
        width: sum(item.input_count == width for item in descriptor.case_roster)
        for width in INPUT_COUNTS
    } == {6: 2, 7: 2}
    assert len({item.vector_sha256 for item in descriptor.case_roster}) == 4
    assert len({item.orbit_cluster_sha256 for item in descriptor.case_roster}) == 4
    assert len({item.group_id for item in descriptor.case_roster}) == 4
    assert (
        tuple(entry.split_role for entry in tiny_corpus.registry.entries)
        == ("train_replay",) * 4
    )

    for row in descriptor.case_roster:
        assert row.output_count == OUTPUT_COUNT
        assert row.shared_monomial_blocks == 4
        assert row.semi_affine_blocks == 1
        assert row.unique_fillers == OUTPUT_COUNT
        assert row.source_candidate_count >= CANDIDATE_CAP
        assert row.candidate_cap_effective == CANDIDATE_CAP
        assert row.scheduler_budget == SCHEDULER_BUDGET
        assert row.augmented_variable_count == CANDIDATE_CAP + SCHEDULER_BUDGET
        assert row.raw_neutral_learned_equals_raw is True
        assert row.split_role == "train_replay"
        assert tuple(arm for arm, _ in row.arm_observation_sha256) == SOURCE_ARMS
        assert tuple(arm for arm, _ in row.target_sha256_by_arm) == SOURCE_ARMS
        assert row.teacher_eligible_arms == SOURCE_ARMS


def test_real_qaoa_schedule_populates_all_four_eligible_arms_and_actual_payloads(
    tiny_corpus,
) -> None:
    roster_by_case = {
        item.case_sha256: item for item in tiny_corpus.descriptor.case_roster
    }
    assert len(tiny_corpus.groups) == 4
    for group in tiny_corpus.groups:
        material = group.material
        row = roster_by_case[material.case.case_sha256]
        assert tuple(record.source_arm for record in material.records) == SOURCE_ARMS
        assert tuple(arm for arm, _ in group.targets_by_arm) == SOURCE_ARMS
        assert row.qaoa_execution_class == "direct_unrepaired"
        assert sum(count for _, count in row.qaoa_counts) == (
            tiny_corpus.descriptor.spec.observation_budget
        )
        assert len(row.qaoa_gammas) == 1
        assert len(row.qaoa_betas) == 1
        assert row.qaoa_counts_payload_sha256 == sha256_bytes(
            material.qaoa_counts_payload
        )
        assert row.qaoa_final_parameter_payload_sha256 == sha256_bytes(
            material.final_parameter_payload
        )
        assert row.qaoa_run_attestation_sha256 == sha256_bytes(material.run_attestation)
        receipt = json.loads(material.run_attestation)
        assert receipt["semantics"].endswith(
            "not_signature_not_hardware_not_independent_attestation"
        )
        assert (
            receipt["scheduler_result"]["diagnostics"]["qaoa_execution_class"]
            == "direct_unrepaired"
        )
        assert (
            receipt["scheduler_result"]["diagnostics"]["qaoa"]["diagnostics"]["backend"]
            == "numpy_statevector"
        )

        target_shas = {
            arm: sha256_bytes(canonical_json_bytes(target.to_dict()))
            for arm, target in group.targets_by_arm
        }
        assert target_shas == dict(row.target_sha256_by_arm)
        assert all(
            target.policy_observation_weight > 0.0 for _, target in group.targets_by_arm
        )
        assert all(
            target.value_observation_weight > 0.0 for _, target in group.targets_by_arm
        )

        parsed_lock = ExternalReplayLockV2.from_bytes(material.external_lock_payload)
        assert parsed_lock == group.technical_lock
        validate_external_replay_lock_v2(
            parsed_lock,
            material.manifest,
            material.records,
            material.case,
            tiny_corpus.registry,
            expected_lock_sha256=row.technical_lock_sha256,
            qaoa_counts_payload=material.qaoa_counts_payload,
            final_parameter_payload=material.final_parameter_payload,
            run_attestation=material.run_attestation,
        )


def test_descriptor_rebuild_is_deterministic_and_trainer_payload_recomputes(
    tiny_corpus,
) -> None:
    encoded = tiny_corpus.descriptor.to_dict()
    assert ReplayTrainingCorpusDescriptorV1.from_dict(encoded) == tiny_corpus.descriptor
    rebuilt = rebuild_replay_training_corpus_v1(encoded)
    assert rebuilt.descriptor == tiny_corpus.descriptor
    assert rebuilt.protocol_payload == tiny_corpus.protocol_payload
    assert rebuilt.source_manifest_payload == tiny_corpus.source_manifest_payload
    assert rebuilt.corpus_lock_payload == tiny_corpus.corpus_lock_payload
    assert build_trainer_corpus_lock_payload_v1(tiny_corpus) == (
        tiny_corpus.corpus_lock_payload
    )
    assert tuple(
        material.manifest.manifest_sha256 for material in rebuilt.materials
    ) == tuple(material.manifest.manifest_sha256 for material in tiny_corpus.materials)


def test_descriptor_and_actual_qaoa_payload_tampering_fail_closed(tiny_corpus) -> None:
    tampered = tiny_corpus.descriptor.to_dict()
    tampered["case_roster"][0]["qaoa_counts"][0][1] += 1
    unsigned = dict(tampered)
    unsigned.pop("corpus_sha256")
    tampered["corpus_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    with pytest.raises(ValueError, match="corpus descriptor"):
        rebuild_replay_training_corpus_v1(tampered)

    group = tiny_corpus.groups[0]
    material = group.material
    altered = replace(material, qaoa_counts_payload=material.qaoa_counts_payload + b" ")
    with pytest.raises(ValueError, match="actual QAOA counts payload"):
        validate_external_replay_lock_v2(
            group.technical_lock,
            altered.manifest,
            altered.records,
            altered.case,
            tiny_corpus.registry,
            expected_lock_sha256=group.technical_lock.lock_sha256,
            qaoa_counts_payload=altered.qaoa_counts_payload,
            final_parameter_payload=altered.final_parameter_payload,
            run_attestation=altered.run_attestation,
        )

    forged_descriptor = replace(
        tiny_corpus.descriptor, trainer_corpus_lock_payload_sha256="0" * 64
    )
    forged_corpus = replace(tiny_corpus, descriptor=forged_descriptor)
    with pytest.raises(ValueError, match="descriptor"):
        build_trainer_corpus_lock_payload_v1(forged_corpus)
