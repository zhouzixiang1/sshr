#!/usr/bin/env python3
"""Adversarial tests for the isolated E6-v2 final-observation contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import inspect

import pytest

import e6.final_measurement_replay_v2 as replay_module
from e6.final_measurement_replay_v2 import (
    CLASSICAL_EXECUTION_CLASS,
    EXTERNAL_LOCK_AUTHORITY,
    EXTERNAL_REPLAY_LOCK_V2_SCHEMA,
    GENERATOR_IDS,
    SOURCE_ARMS,
    ComputeBudgetV2,
    ExternalReplayLockV2,
    FinalMeasurementObservationV2,
    GeneratorContractV2,
    ObservationOriginV2,
    QAOAFinalMeasurementContractV2,
    ReplayGroupManifestV2,
    SplitRegistryEntryV2,
    SplitRegistrySourceV2,
    SplitRegistryV2,
    audit_equal_observation_group_v2,
    build_classical_greedy_observation_v2,
    build_classical_random_observation_v2,
    build_final_measurement_observation_v2,
    build_qaoa_final_measurement_observation_v2,
    build_qaoa_permuted_label_control_v2,
    build_replay_group_manifest_v2,
    build_split_registry_v2,
    canonical_greedy_counts_v2,
    canonical_random_counts_v2,
    canonical_vector_orbit_sha256,
    derive_replay_targets_v2,
    derive_qaoa_replay_targets_from_external_lock_v2,
    deterministic_label_permutation_v2,
    qaoa_counts_payload_bytes_v2,
    validate_external_replay_lock_v2,
    validate_final_measurement_observation_v2,
    validate_replay_group_manifest_v2,
    validate_split_registry_v2,
    whole_vector_cluster_id,
)
from e6.frozen_case import build_frozen_shared_case
from e6.shared_oracle import MonomialSharedAction, VectorANF
from e6.shared_scheduler import SharedSchedulerConfig
from src.contracts.codec import canonical_json_bytes, sha256_bytes


CHECKPOINT_SHA = "a" * 64
ORIGIN_SHA = "b" * 64
FINAL_PARAMETER_PAYLOAD = b'{"gammas":[0.2],"betas":[0.1]}'
RUN_ATTESTATION_PAYLOAD = b'{"backend":"numpy_statevector","run":"unit"}'
FINAL_PARAMETER_SHA = sha256_bytes(FINAL_PARAMETER_PAYLOAD)
SOURCE_ATTESTATION_SHA = sha256_bytes(RUN_ATTESTATION_PAYLOAD)
PROTOCOL_SHA = "f" * 64
SOURCE_MANIFEST_SHA = "1" * 64
FAMILY_ID = "synthetic/train/family-0001"
GROUP_NONCE = "unit/equal-observation-group-0001"
OBSERVATION_BUDGET = 80

QAOA_COUNTS = {
    "10100": 25,
    "01100": 15,
    "10010": 10,
    "01010": 5,
    "00110": 10,
    "00011": 5,
    "11000": 5,
    "00000": 5,
}


def _case(*, shots: int = OBSERVATION_BUDGET):
    vector = VectorANF(
        4,
        (
            frozenset({0b0111}),
            frozenset({0b0111}),
            frozenset({0b0111}),
            frozenset({0b0111}),
            frozenset({0b1011}),
            frozenset({0b1011}),
            frozenset({0b1011}),
        ),
    )
    actions = (
        MonomialSharedAction(0b0111, (0, 1, 2)),
        MonomialSharedAction(0b0111, (1, 2, 3)),
        MonomialSharedAction(0b1011, (4, 5, 6)),
    )
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=CHECKPOINT_SHA,
        config=SharedSchedulerConfig(
            budget_requested=2,
            qaoa_seed=20260907,
            qaoa_shots=shots,
            qaoa_p=1,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=2,
            qaoa_max_variables=12,
            audit_max_variables=12,
        ),
        raw_utilities=(3.0, 2.0, 1.0),
        learned_utilities=(3.0, 2.0, 1.0),
    )


def _origin(
    *,
    origin_id: str = "synthetic/source/vector-0001",
    partition: str = "not_applicable",
) -> ObservationOriginV2:
    if partition == "not_applicable":
        return ObservationOriginV2(
            "synthetic", origin_id, ORIGIN_SHA, None, partition, False
        )
    return ObservationOriginV2(
        "cryptographic",
        origin_id,
        ORIGIN_SHA,
        "PRESENT-S-box",
        partition,
        partition == "evaluation_holdout",
    )


def _registry(
    case=None,
    *,
    family_id: str = FAMILY_ID,
    split_role: str = "train_replay",
    origin: ObservationOriginV2 | None = None,
) -> SplitRegistryV2:
    case = _case() if case is None else case
    return build_split_registry_v2(
        (
            SplitRegistrySourceV2(
                family_id=family_id,
                vector_or_case=case,
                split_role=split_role,
                origin=_origin() if origin is None else origin,
            ),
        )
    )


def _random(case, registry, *, seed: int = 7):
    return build_classical_random_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        observation_budget=case.scheduler_config.qaoa_shots,
        group_nonce=GROUP_NONCE,
        seed=seed,
    )


def _greedy(case, registry, *, seed: int = 7):
    return build_classical_greedy_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        observation_budget=case.scheduler_config.qaoa_shots,
        group_nonce=GROUP_NONCE,
        seed=seed,
    )


def _qaoa(
    case,
    registry,
    *,
    counts=None,
    execution_class: str = "direct_unrepaired",
    trusted: bool = True,
    final_parameter_sha: str | None = FINAL_PARAMETER_SHA,
):
    if counts is None:
        counts = QAOA_COUNTS
    canonical_counts_payload = qaoa_counts_payload_bytes_v2(
        case, counts, execution_class=execution_class
    )
    if execution_class in {"fallback", "not_invoked"}:
        expectation_evaluations = 0 if execution_class == "not_invoked" else 1
    else:
        expectation_evaluations = max(
            2, case.scheduler_config.qaoa_optimizer_restarts
        ) + (
            case.scheduler_config.qaoa_optimizer_steps
            * 4
            * case.scheduler_config.qaoa_p
        )
    observed_count = sum(counts.values()) if type(counts) is dict else sum(
        count for _, count in counts
    )
    return build_qaoa_final_measurement_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        group_nonce=GROUP_NONCE,
        counts=counts,
        execution_class=execution_class,
        final_parameter_payload_sha256=final_parameter_sha,
        counts_source_sha256=sha256_bytes(canonical_counts_payload),
        source_trust=(
            "externally_attested_source"
            if trusted
            else "unverified_development_ledger"
        ),
        source_attestation_sha256=(SOURCE_ATTESTATION_SHA if trusted else None),
        compute_budget=ComputeBudgetV2(
            quantum_circuit_executions=expectation_evaluations,
            statevector_expectation_evaluations=expectation_evaluations,
            classical_candidate_evaluations=0,
            qubo_assignments_audited=1 << case.augmented_variable_count,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=observed_count,
            declared_wall_seconds=None,
            notes="actual test-ledger QAOA diagnostics; compute is not arm-equal",
        ),
    )


def _control(case, registry, qaoa, *, seed: int = 11):
    return build_qaoa_permuted_label_control_v2(
        qaoa,
        case,
        registry,
        expected_source_observation_sha256=qaoa.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
        permutation_seed=seed,
    )


def _group(
    *,
    case=None,
    registry=None,
    qaoa_counts=None,
    execution_class: str = "direct_unrepaired",
    trusted: bool = True,
    final_parameter_sha: str | None = FINAL_PARAMETER_SHA,
):
    case = _case() if case is None else case
    registry = _registry(case) if registry is None else registry
    random_record = _random(case, registry)
    greedy_record = _greedy(case, registry)
    qaoa = _qaoa(
        case,
        registry,
        counts=qaoa_counts,
        execution_class=execution_class,
        trusted=trusted,
        final_parameter_sha=final_parameter_sha,
    )
    control = _control(case, registry, qaoa)
    records = (random_record, greedy_record, qaoa, control)
    manifest = build_replay_group_manifest_v2(
        records,
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        protocol_sha256=PROTOCOL_SHA,
        source_manifest_sha256=SOURCE_MANIFEST_SHA,
    )
    return case, registry, records, manifest


def _external_lock_and_capability(
    case,
    registry,
    records,
    manifest,
    *,
    counts_payload: bytes | None = None,
    final_parameter_payload: bytes = FINAL_PARAMETER_PAYLOAD,
    run_attestation: bytes = RUN_ATTESTATION_PAYLOAD,
):
    by_arm = {record.source_arm: record for record in records}
    qaoa = by_arm["qaoa_final_measurement_replay"]
    control = by_arm["qaoa_permuted_label_control"]
    if counts_payload is None:
        counts_payload = qaoa_counts_payload_bytes_v2(
            case, qaoa.counts, execution_class=qaoa.qaoa_execution_class
        )
    unsigned = {
        "schema_version": EXTERNAL_REPLAY_LOCK_V2_SCHEMA,
        "authority": EXTERNAL_LOCK_AUTHORITY,
        "manifest_sha256": manifest.manifest_sha256,
        "split_registry_sha256": registry.registry_sha256,
        "protocol_sha256": manifest.protocol_sha256,
        "source_manifest_sha256": manifest.source_manifest_sha256,
        "qaoa_observation_sha256": qaoa.observation_sha256,
        "qaoa_control_observation_sha256": control.observation_sha256,
        "qaoa_counts_payload_sha256": sha256_bytes(counts_payload),
        "qaoa_final_parameter_payload_sha256": sha256_bytes(
            final_parameter_payload
        ),
        "qaoa_run_attestation_sha256": sha256_bytes(run_attestation),
    }
    lock = ExternalReplayLockV2.from_mapping(
        {**unsigned, "lock_sha256": replay_module._sha(unsigned)}  # noqa: SLF001
    )
    capability = validate_external_replay_lock_v2(
        lock,
        manifest,
        records,
        case,
        registry,
        expected_lock_sha256=lock.lock_sha256,
        qaoa_counts_payload=counts_payload,
        final_parameter_payload=final_parameter_payload,
        run_attestation=run_attestation,
    )
    return lock, capability


def _derive_qaoa_target_from_external_lock(
    case,
    registry,
    records,
    manifest,
    *,
    record=None,
):
    if record is None:
        record = records[2]
    counts_payload = qaoa_counts_payload_bytes_v2(
        case,
        records[2].counts,
        execution_class=records[2].qaoa_execution_class,
    )
    lock, _ = _external_lock_and_capability(
        case,
        registry,
        records,
        manifest,
        counts_payload=counts_payload,
    )
    target = derive_qaoa_replay_targets_from_external_lock_v2(
        record,
        manifest,
        records,
        case,
        registry,
        expected_observation_sha256=record.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
        lock=lock,
        expected_lock_sha256=lock.lock_sha256,
        qaoa_counts_payload=counts_payload,
        final_parameter_payload=FINAL_PARAMETER_PAYLOAD,
        run_attestation=RUN_ATTESTATION_PAYLOAD,
    )
    return lock, target


def _rehash_observation(record: FinalMeasurementObservationV2):
    distributed = replace(
        record,
        distribution_sha256=replay_module._sha(  # noqa: SLF001
            replay_module._distribution_payload(record)  # noqa: SLF001
        ),
    )
    return replace(
        distributed,
        observation_sha256=replay_module._sha(  # noqa: SLF001
            replay_module._observation_payload(distributed)  # noqa: SLF001
        ),
    )


def _rehash_manifest(manifest: ReplayGroupManifestV2):
    return replace(
        manifest,
        manifest_sha256=replay_module._sha(  # noqa: SLF001
            replay_module._manifest_payload(manifest)  # noqa: SLF001
        ),
    )


def _validate_record(record, case, registry, **kwargs):
    return validate_final_measurement_observation_v2(
        record,
        case,
        registry,
        expected_observation_sha256=record.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
        **kwargs,
    )


def test_four_source_arms_are_exact_and_arbitrary_constructor_fails_closed() -> None:
    assert SOURCE_ARMS == (
        "classical_random_bitstring_replay",
        "classical_greedy_repeated_selection_replay",
        "qaoa_final_measurement_replay",
        "qaoa_permuted_label_control",
    )
    assert "exact_teacher" not in SOURCE_ARMS
    with pytest.raises(TypeError, match="build_classical_random_observation_v2"):
        build_final_measurement_observation_v2()


def test_vector_orbit_is_invariant_to_input_and_output_permutations() -> None:
    vector = VectorANF(
        3,
        (
            frozenset({0b001, 0b011, 0b111}),
            frozenset({0, 0b101}),
            frozenset({0b010, 0b110}),
        ),
    )
    permuted = vector.permute_inputs((2, 0, 1)).permute_outputs((1, 2, 0))

    assert canonical_vector_orbit_sha256(vector) == canonical_vector_orbit_sha256(
        permuted
    )
    assert whole_vector_cluster_id(vector) != whole_vector_cluster_id(permuted)


def test_n8_vector_orbit_fails_closed_without_precomputed_digest_bypass() -> None:
    vector = VectorANF(8, (frozenset({1}), frozenset({2})))
    with pytest.raises(ValueError, match="input_count>7"):
        canonical_vector_orbit_sha256(vector)
    with pytest.raises(TypeError, match="unexpected keyword"):
        canonical_vector_orbit_sha256(  # type: ignore[call-arg]
            vector, external_precomputed_orbit_sha256="9" * 64
        )


def test_split_registry_rejects_family_or_orbit_cross_split_reuse() -> None:
    case = _case()
    first = SplitRegistrySourceV2(
        FAMILY_ID, case, "train_replay", _origin()
    )
    second = SplitRegistrySourceV2(
        "formal/family-copy",
        case.vector,
        "formal_evaluation",
        _origin(origin_id="synthetic/source/copy"),
    )
    with pytest.raises(ValueError, match="orbit cluster"):
        build_split_registry_v2((first, second))
    distinct_vector = VectorANF(2, (frozenset({0b11}),))
    same_family = SplitRegistrySourceV2(
        FAMILY_ID,
        distinct_vector,
        "formal_evaluation",
        _origin(origin_id="synthetic/source/distinct"),
    )
    with pytest.raises(ValueError, match="family_id"):
        build_split_registry_v2((first, same_family))
    bare_hash_entry = SplitRegistryEntryV2(
        FAMILY_ID,
        canonical_vector_orbit_sha256(case.vector),
        case.vector_sha256,
        "train_replay",
        _origin(),
    )
    with pytest.raises(TypeError, match="actual vector/case"):
        build_split_registry_v2((bare_hash_entry,))  # type: ignore[arg-type]


def test_fake_orbit_registry_is_rejected_against_actual_frozen_case() -> None:
    case = _case()
    registry = _registry(case)
    fake_entry = replace(registry.entries[0], orbit_cluster_sha256="8" * 64)
    provisional = replace(registry, entries=(fake_entry,), registry_sha256="0" * 64)
    fake_registry = replace(
        provisional,
        registry_sha256=replay_module._sha(  # noqa: SLF001
            replay_module._split_registry_payload(provisional)  # noqa: SLF001
        ),
    )
    record = _random(case, fake_registry)
    with pytest.raises(ValueError, match="orbit does not recompute"):
        _validate_record(record, case, fake_registry)


def test_registry_and_observation_require_external_anchors_and_registry_split() -> None:
    case = _case()
    registry = _registry(case)
    record = _random(case, registry)
    validate_split_registry_v2(
        registry, expected_registry_sha256=registry.registry_sha256
    )
    with pytest.raises(ValueError, match="external anchor"):
        validate_split_registry_v2(
            registry, expected_registry_sha256="0" * 64
        )

    drifted = _rehash_observation(
        replace(record, split_role="formal_evaluation")
    )
    with pytest.raises(ValueError, match="split registry"):
        _validate_record(drifted, case, registry)
    origin_drift = _rehash_observation(
        replace(record, origin=_origin(origin_id="synthetic/source/other"))
    )
    with pytest.raises(ValueError, match="origin"):
        _validate_record(origin_drift, case, registry)


def test_registry_and_observation_roundtrip_are_immutable_and_strict() -> None:
    case = _case()
    registry = _registry(case)
    record = _random(case, registry)
    assert SplitRegistryV2.from_dict(registry.to_dict()) == registry
    assert FinalMeasurementObservationV2.from_dict(record.to_dict()) == record
    with pytest.raises(FrozenInstanceError):
        record.source_arm = "changed"  # type: ignore[misc]

    payload = record.to_dict()
    payload["observation_budget"] = 80.0
    with pytest.raises(TypeError, match="native integer"):
        FinalMeasurementObservationV2.from_dict(payload)
    payload = record.to_dict()
    payload["compute_budget_equal"] = 0
    with pytest.raises(TypeError, match="native bool"):
        FinalMeasurementObservationV2.from_dict(payload)
    payload = record.to_dict()
    payload["action_signatures"][0] = 7  # type: ignore[index]
    with pytest.raises(TypeError, match="native string"):
        FinalMeasurementObservationV2.from_dict(payload)


def test_generator_native_types_seed_and_finite_compute_budget_are_strict() -> None:
    case = _case()
    registry = _registry(case)
    with pytest.raises(ValueError, match="seed"):
        build_classical_random_observation_v2(
            case,
            registry,
            expected_registry_sha256=registry.registry_sha256,
            family_id=FAMILY_ID,
            observation_budget=1,
            group_nonce=GROUP_NONCE,
            seed=-1,
        )
    with pytest.raises(TypeError, match="native integer"):
        build_classical_random_observation_v2(
            case,
            registry,
            expected_registry_sha256=registry.registry_sha256,
            family_id=FAMILY_ID,
            observation_budget=1,
            group_nonce=GROUP_NONCE,
            seed=True,
        )
    payload = ComputeBudgetV2(0, 0, 0, 0, 0, 1, None, "test").to_dict()
    payload["declared_wall_seconds"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        ComputeBudgetV2.from_dict(payload)


def test_random_sha_stream_is_deterministic_uniform_contract_and_supports_one_draw() -> None:
    case = _case()
    registry = _registry(case)
    first = canonical_random_counts_v2(case, observation_budget=80, seed=7)
    second = canonical_random_counts_v2(case, observation_budget=80, seed=7)
    other = canonical_random_counts_v2(case, observation_budget=80, seed=8)
    one = build_classical_random_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=FAMILY_ID,
        observation_budget=1,
        group_nonce="unit/one-draw",
        seed=7,
    )

    assert first == second
    assert first != other
    assert sum(count for _, count in first) == 80
    assert sum(count for _, count in one.counts) == 1
    assert one.generator_contract.generator_id == GENERATOR_IDS[
        "classical_random_bitstring_replay"
    ]


def test_random_replay_rejects_bad_counts_generator_and_source_payload() -> None:
    case = _case()
    registry = _registry(case)
    record = _random(case, registry)
    bad_counts = list(record.counts)
    bad_counts[0] = (bad_counts[0][0], bad_counts[0][1] + 1)
    donor = next(index for index, (_, count) in enumerate(bad_counts[1:], 1) if count > 1)
    bad_counts[donor] = (bad_counts[donor][0], bad_counts[donor][1] - 1)
    bad = _rehash_observation(replace(record, counts=tuple(bad_counts)))
    with pytest.raises(ValueError, match="do not recompute"):
        _validate_record(bad, case, registry)

    wrong_generator = _rehash_observation(
        replace(
            record,
            generator_contract=replace(
                record.generator_contract, generator_id="wrong-generator"
            ),
        )
    )
    with pytest.raises(ValueError, match="generator_id"):
        _validate_record(wrong_generator, case, registry)
    wrong_source = _rehash_observation(
        replace(
            record,
            generator_contract=replace(
                record.generator_contract, source_payload_sha256="7" * 64
            ),
        )
    )
    with pytest.raises(ValueError, match="source payload"):
        _validate_record(wrong_source, case, registry)


def test_greedy_selection_is_recomputed_and_repeated_exactly_r_times() -> None:
    case = _case()
    registry = _registry(case)
    record = _greedy(case, registry)
    assert record.counts == canonical_greedy_counts_v2(
        case, observation_budget=OBSERVATION_BUDGET
    )
    assert record.counts[0][1] == OBSERVATION_BUDGET
    assert _validate_record(record, case, registry).structural_valid is True

    changed = _rehash_observation(
        replace(record, counts=(("01100", OBSERVATION_BUDGET),))
    )
    with pytest.raises(ValueError, match="frozen greedy"):
        _validate_record(changed, case, registry)


def test_qaoa_contract_binds_all_frozen_scheduler_parameters() -> None:
    case = _case()
    registry = _registry(case)
    record = _qaoa(case, registry)
    contract = record.qaoa_contract
    assert contract is not None
    assert (
        contract.scheduler_seed,
        contract.shots,
        contract.p,
        contract.optimizer_restarts,
        contract.optimizer_steps,
    ) == (20260907, 80, 1, 1, 2)

    for field, value in (
        ("scheduler_seed", 20260908),
        ("shots", 81),
        ("p", 2),
        ("optimizer_restarts", 2),
        ("optimizer_steps", 3),
    ):
        changed = _rehash_observation(
            replace(record, qaoa_contract=replace(contract, **{field: value}))
        )
        with pytest.raises(ValueError, match="drifted|budget"):
            _validate_record(changed, case, registry)


def test_qaoa_one_of_eighty_counts_is_rejected_and_bool_counts_are_rejected() -> None:
    case = _case()
    registry = _registry(case)
    one = _qaoa(case, registry, counts={"10100": 1})
    with pytest.raises(ValueError, match="counts sum to 1"):
        _validate_record(one, case, registry)
    with pytest.raises(TypeError, match="native integer"):
        _qaoa(case, registry, counts={"10100": True})


def test_unverified_qaoa_is_valid_ledger_but_cannot_be_teacher() -> None:
    case, registry, records, manifest = _group(trusted=False)
    record = records[2]
    audit = _validate_record(record, case, registry)

    assert audit.structural_valid is True
    assert audit.source_trusted is False
    assert audit.teacher_eligible is False
    assert "qaoa_source_unverified" in audit.ineligibility_reasons
    with pytest.raises(ValueError, match="derive_qaoa_replay_targets"):
        derive_replay_targets_v2(
            record,
            case,
            registry,
            expected_observation_sha256=record.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
        )


def test_attested_qaoa_requires_attestation_and_public_bool_trust_entry_is_gone() -> None:
    case = _case()
    registry = _registry(case)
    record = _qaoa(case, registry)
    no_attestation = _rehash_observation(
        replace(
            record,
            qaoa_contract=replace(
                record.qaoa_contract, source_attestation_sha256=None  # type: ignore[arg-type]
            ),
        )
    )
    with pytest.raises(ValueError, match="attestation"):
        _validate_record(no_attestation, case, registry)

    parameters = inspect.signature(validate_final_measurement_observation_v2).parameters
    assert "_manifest_anchor_validated" not in parameters
    assert "expected_qaoa_counts_source_sha256" not in parameters
    with pytest.raises(TypeError, match="unexpected keyword"):
        validate_final_measurement_observation_v2(
            record,
            case,
            registry,
            expected_observation_sha256=record.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            _manifest_anchor_validated=True,  # type: ignore[call-arg]
        )


def test_structural_ledger_and_teacher_extraction_are_separate() -> None:
    case, registry, records, manifest = _group()
    record = records[2]
    standalone = _validate_record(record, case, registry)
    audits = validate_replay_group_manifest_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    audit = audits["qaoa_final_measurement_replay"]
    with pytest.raises(ValueError, match="derive_qaoa_replay_targets"):
        derive_replay_targets_v2(
            record,
            case,
            registry,
            expected_observation_sha256=record.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
        )
    lock, capability = _external_lock_and_capability(
        case, registry, records, manifest
    )
    _, target = _derive_qaoa_target_from_external_lock(
        case, registry, records, manifest, record=record
    )
    trusted_audit = capability.audit_for(
        record,
        case,
        registry,
        expected_observation_sha256=record.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
    )

    assert lock.authority == EXTERNAL_LOCK_AUTHORITY
    assert standalone.structural_valid is True
    assert standalone.teacher_eligible is False
    assert audit.structural_valid is True
    assert audit.teacher_eligible is False
    assert trusted_audit.teacher_eligible is True
    assert target.policy_target == trusted_audit.label_aligned_policy_target
    assert target.value_target_log_ratio == trusted_audit.value_audit.value_target_log_ratio


def test_external_lock_strict_bytes_roundtrip_and_no_public_capability_input() -> None:
    case, registry, records, manifest = _group()
    lock, capability = _external_lock_and_capability(
        case, registry, records, manifest
    )
    encoded = canonical_json_bytes(lock.to_dict())

    assert ExternalReplayLockV2.from_mapping(lock.to_dict()) == lock
    assert ExternalReplayLockV2.from_bytes(encoded) == lock
    assert capability.lock_sha256 == lock.lock_sha256
    assert capability.manifest_sha256 == manifest.manifest_sha256
    with pytest.raises(TypeError, match="native bytes"):
        ExternalReplayLockV2.from_bytes(encoded.decode("utf-8"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical JSON"):
        ExternalReplayLockV2.from_bytes(b" " + encoded)
    assert "VerifiedReplayGroupV2" not in replay_module.__all__
    assert "verified_group" not in inspect.signature(derive_replay_targets_v2).parameters
    forged = replay_module._ValidatedReplayGroupV2(  # noqa: SLF001
        lock_sha256=capability.lock_sha256,
        manifest_sha256=capability.manifest_sha256,
        case_sha256=case.case_sha256,
        split_registry_sha256=registry.registry_sha256,
        arm_observation_sha256=manifest.arm_observation_sha256,
        audits=capability._audits,  # noqa: SLF001
        _token=replay_module._VALIDATED_REPLAY_GROUP_TOKEN,  # noqa: SLF001
    )
    with pytest.raises(TypeError, match="unexpected keyword"):
        derive_replay_targets_v2(
            records[2],
            case,
            registry,
            expected_observation_sha256=records[2].observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            verified_group=forged,  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("field", "tampered"),
    (
        ("qaoa_counts_payload", b"tampered-counts"),
        ("final_parameter_payload", b"tampered-parameters"),
        ("run_attestation", b"tampered-attestation"),
    ),
)
def test_external_lock_rehashes_and_rejects_each_actual_payload_tamper(
    field: str, tampered: bytes
) -> None:
    case, registry, records, manifest = _group()
    lock, _ = _external_lock_and_capability(case, registry, records, manifest)
    actual = {
        "qaoa_counts_payload": qaoa_counts_payload_bytes_v2(
            case,
            records[2].counts,
            execution_class=records[2].qaoa_execution_class,
        ),
        "final_parameter_payload": FINAL_PARAMETER_PAYLOAD,
        "run_attestation": RUN_ATTESTATION_PAYLOAD,
    }
    actual[field] = tampered

    with pytest.raises(ValueError, match="actual QAOA counts|actual qaoa_"):
        derive_qaoa_replay_targets_from_external_lock_v2(
            records[2],
            manifest,
            records,
            case,
            registry,
            expected_observation_sha256=records[2].observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            lock=lock,
            expected_lock_sha256=lock.lock_sha256,
            **actual,
        )


def test_qaoa_teacher_rejects_mismatched_external_lock_anchor() -> None:
    case, registry, records, manifest = _group()
    lock, _ = _external_lock_and_capability(case, registry, records, manifest)
    with pytest.raises(ValueError, match="independent anchor"):
        derive_qaoa_replay_targets_from_external_lock_v2(
            records[2],
            manifest,
            records,
            case,
            registry,
            expected_observation_sha256=records[2].observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            lock=lock,
            expected_lock_sha256="0" * 64,
            qaoa_counts_payload=qaoa_counts_payload_bytes_v2(
                case,
                records[2].counts,
                execution_class=records[2].qaoa_execution_class,
            ),
            final_parameter_payload=FINAL_PARAMETER_PAYLOAD,
            run_attestation=RUN_ATTESTATION_PAYLOAD,
        )


def test_self_signed_manifest_without_external_lock_cannot_issue_qaoa_teacher() -> None:
    case, registry, records, manifest = _group()
    qaoa = records[2]
    # The manifest validates structurally against its own development digest,
    # but that digest is intentionally not a trainer capability.
    audits = validate_replay_group_manifest_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    assert audits["qaoa_final_measurement_replay"].teacher_eligible is False
    with pytest.raises(ValueError, match="derive_qaoa_replay_targets"):
        derive_replay_targets_v2(
            qaoa,
            case,
            registry,
            expected_observation_sha256=qaoa.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
        )


def test_feasible_fraction_and_policy_weight_use_total_observed_times_budget() -> None:
    case = _case()
    registry = _registry(case)
    record = _qaoa(case, registry)
    audit = _validate_record(record, case, registry)

    assert audit.total_observed == 80
    assert audit.feasible_observed == 70
    assert audit.feasible_fraction == pytest.approx(70 / 80)
    assert audit.source_marginal_action_counts == (35, 20, 50)
    assert audit.policy_observation_weight == pytest.approx(105 / (80 * 2))
    assert audit.source_policy_target == pytest.approx(
        (35 / 105, 20 / 105, 50 / 105)
    )


def test_one_of_eighty_feasible_shots_weights_policy_and_value_by_one_eightieth() -> None:
    case, registry, records, manifest = _group(
        qaoa_counts={"10100": 1, "00000": 79}
    )
    qaoa = records[2]
    _, target = _derive_qaoa_target_from_external_lock(
        case,
        registry,
        records,
        manifest,
        record=qaoa,
    )

    assert target.feasible_fraction == pytest.approx(1 / 80)
    assert target.policy_observation_weight == pytest.approx(1 / 80)
    assert target.value_observation_weight == pytest.approx(1 / 80)
    assert "multiply_each_observation_value_loss" in target.value_loss_weight_contract
    assert "trainer_must_not_build_manifest" in target.trainer_replay_contract


def test_label_control_exposes_source_and_label_aligned_marginals() -> None:
    case = _case()
    registry = _registry(case)
    qaoa = _qaoa(case, registry)
    control = _control(case, registry, qaoa)
    audit = _validate_record(
        control,
        case,
        registry,
        parent_qaoa_observation=qaoa,
        expected_parent_observation_sha256=qaoa.observation_sha256,
    )
    permutation = control.label_permutation_new_index_to_source_index

    assert control.counts == qaoa.counts
    assert control.distribution_sha256 == qaoa.distribution_sha256
    assert audit.source_marginal_action_counts == (35, 20, 50)
    assert audit.label_aligned_marginal_action_counts == tuple(
        audit.source_marginal_action_counts[index] for index in permutation
    )
    assert audit.source_policy_target != audit.label_aligned_policy_target
    row = next(item for item in audit.bitstring_audit if item.bitstring == (1, 0, 1, 0, 0))
    assert row.source_selected_real_indices == (0, 2)
    assert row.label_aligned_selected_real_indices == tuple(
        index for index, source in enumerate(permutation) if source in {0, 2}
    )


def test_group_manifest_binds_protocol_sources_registry_case_parents_and_generators() -> None:
    case, registry, records, manifest = _group()
    audits = validate_replay_group_manifest_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )

    assert manifest.protocol_sha256 == PROTOCOL_SHA
    assert manifest.source_manifest_sha256 == SOURCE_MANIFEST_SHA
    assert manifest.split_registry_sha256 == registry.registry_sha256
    assert manifest.case_sha256 == case.case_sha256
    assert tuple(arm for arm, _ in manifest.arm_observation_sha256) == SOURCE_ARMS
    assert manifest.parent_bindings == (
        (
            "qaoa_permuted_label_control",
            "qaoa_final_measurement_replay",
            dict(manifest.arm_observation_sha256)["qaoa_final_measurement_replay"],
        ),
    )
    assert set(audits) == set(SOURCE_ARMS)
    assert ReplayGroupManifestV2.from_dict(manifest.to_dict()) == manifest


def test_coordinated_resign_still_fails_against_old_manifest_anchor() -> None:
    case, registry, records, manifest = _group()
    random_record = records[0]
    tampered_generator = replace(
        random_record.generator_contract,
        compute_budget=replace(
            random_record.generator_contract.compute_budget,
            notes="coordinated attacker changed notes",
        ),
    )
    tampered_random = _rehash_observation(
        replace(random_record, generator_contract=tampered_generator)
    )
    tampered_records = (tampered_random,) + records[1:]
    resigned = build_replay_group_manifest_v2(
        tampered_records,
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        protocol_sha256=PROTOCOL_SHA,
        source_manifest_sha256=SOURCE_MANIFEST_SHA,
    )

    assert resigned.manifest_sha256 != manifest.manifest_sha256
    with pytest.raises(ValueError, match="external anchor"):
        validate_replay_group_manifest_v2(
            resigned,
            tampered_records,
            case,
            registry,
            expected_manifest_sha256=manifest.manifest_sha256,
        )


def test_manifest_rejects_generator_or_source_binding_drift() -> None:
    case, registry, records, manifest = _group()
    bad_generators = list(manifest.generator_configuration_sha256)
    bad_generators[0] = (bad_generators[0][0], "0" * 64)
    changed = _rehash_manifest(
        replace(manifest, generator_configuration_sha256=tuple(bad_generators))
    )
    with pytest.raises(ValueError, match="generator configuration"):
        validate_replay_group_manifest_v2(
            changed,
            records,
            case,
            registry,
            expected_manifest_sha256=changed.manifest_sha256,
        )

    bad_sources = list(manifest.source_payload_sha256)
    bad_sources[2] = (bad_sources[2][0], "0" * 64)
    changed = _rehash_manifest(
        replace(manifest, source_payload_sha256=tuple(bad_sources))
    )
    with pytest.raises(ValueError, match="source payload|external binding"):
        validate_replay_group_manifest_v2(
            changed,
            records,
            case,
            registry,
            expected_manifest_sha256=changed.manifest_sha256,
        )


def test_equal_group_reports_eligibility_without_requiring_it() -> None:
    case, registry, records, manifest = _group(trusted=False)
    audit = audit_equal_observation_group_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )

    assert audit.structural_passed is True
    assert audit.all_four_arms_present is True
    assert audit.observation_budget_equal is True
    assert audit.compute_budget_equal is False
    assert "qaoa_final_measurement_replay" not in audit.eligible_arms
    reasons = dict(audit.ineligible_reasons_by_arm)
    assert "qaoa_source_unverified" in reasons["qaoa_final_measurement_replay"]


@pytest.mark.parametrize("execution_class", ("fallback", "not_invoked"))
def test_fallback_and_not_invoked_remain_structurally_complete_group_ledgers(
    execution_class: str,
) -> None:
    case, registry, records, manifest = _group(
        qaoa_counts={},
        execution_class=execution_class,
        final_parameter_sha=None,
    )
    audit = audit_equal_observation_group_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    completeness = dict(audit.observation_budget_complete_by_arm)
    reasons = dict(audit.ineligible_reasons_by_arm)

    assert audit.structural_passed is True
    assert completeness["qaoa_final_measurement_replay"] is False
    assert completeness["qaoa_permuted_label_control"] is False
    assert "observation_budget_not_realised" in reasons[
        "qaoa_final_measurement_replay"
    ]


def test_repaired_and_direct_no_feasible_distributions_are_structural_not_teachers() -> None:
    infeasible = {"11000": OBSERVATION_BUDGET}
    for execution_class in ("direct_repaired", "direct_unrepaired"):
        case, registry, records, manifest = _group(
            qaoa_counts=infeasible,
            execution_class=execution_class,
        )
        audit = audit_equal_observation_group_v2(
            manifest,
            records,
            case,
            registry,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
        reasons = dict(audit.ineligible_reasons_by_arm)
        assert audit.structural_passed is True
        assert "no_feasible_observations" in reasons[
            "qaoa_final_measurement_replay"
        ]


def _zero_action_case(*, shots: int = 8):
    return build_frozen_shared_case(
        VectorANF(2, (frozenset(), frozenset())),
        (),
        checkpoint_sha256=CHECKPOINT_SHA,
        config=SharedSchedulerConfig(
            budget_requested=1,
            qaoa_shots=shots,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=0,
        ),
    )


def _one_action_case(*, shots: int = 8):
    vector = VectorANF(2, (frozenset({0b01}), frozenset({0b01})))
    return build_frozen_shared_case(
        vector,
        (MonomialSharedAction(0b01, (0, 1)),),
        checkpoint_sha256=CHECKPOINT_SHA,
        config=SharedSchedulerConfig(
            budget_requested=1,
            qaoa_shots=shots,
            qaoa_optimizer_restarts=1,
            qaoa_optimizer_steps=0,
        ),
        raw_utilities=(1.0,),
        learned_utilities=(1.0,),
    )


def _degenerate_group(case, qaoa_counts):
    registry = _registry(case)
    random_record = _random(case, registry)
    greedy_record = _greedy(case, registry)
    qaoa = _qaoa(case, registry, counts=qaoa_counts)
    control = _control(case, registry, qaoa)
    records = (random_record, greedy_record, qaoa, control)
    manifest = build_replay_group_manifest_v2(
        records,
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        protocol_sha256=PROTOCOL_SHA,
        source_manifest_sha256=SOURCE_MANIFEST_SHA,
    )
    return registry, records, manifest


def test_k0_group_is_structurally_valid_and_explicitly_ineligible() -> None:
    case = _zero_action_case()
    registry, records, manifest = _degenerate_group(case, {"": 8})
    audit = audit_equal_observation_group_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    reasons = dict(audit.ineligible_reasons_by_arm)

    assert audit.structural_passed is True
    assert audit.label_permutation_nonidentity is False
    assert audit.permuted_policy_effective is False
    assert audit.eligible_arms == ()
    assert all("zero_real_action_budget" in item for item in reasons.values())


def test_k1_group_allows_unavoidable_identity_control_but_marks_it_ineligible() -> None:
    case = _one_action_case()
    registry, records, manifest = _degenerate_group(case, {"10": 8})
    audit = audit_equal_observation_group_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    reasons = dict(audit.ineligible_reasons_by_arm)

    assert audit.structural_passed is True
    assert audit.label_permutation_nonidentity is False
    assert audit.permuted_policy_effective is False
    assert "label_permutation_degenerate" in reasons[
        "qaoa_permuted_label_control"
    ]


def test_symmetric_policy_control_is_structural_even_when_permutation_is_ineffective() -> None:
    symmetric_counts = {
        "10010": 26,
        "01010": 26,
        "00110": 26,
        "00011": 2,
    }
    case, registry, records, manifest = _group(qaoa_counts=symmetric_counts)
    audit = audit_equal_observation_group_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=manifest.manifest_sha256,
    )
    reasons = dict(audit.ineligible_reasons_by_arm)

    assert audit.structural_passed is True
    assert audit.label_permutation_nonidentity is True
    assert audit.permuted_policy_effective is False
    assert "permuted_policy_unchanged" in reasons[
        "qaoa_permuted_label_control"
    ]


def test_harm_is_not_collapsed_into_tie_for_teacher_eligibility() -> None:
    case = _one_action_case()
    # The shared single-control block adds compute/uncompute overhead and is
    # more expensive than direct output toggles for this tiny vector.
    registry = _registry(case)
    greedy = _greedy(case, registry)
    audit = _validate_record(greedy, case, registry)

    assert audit.value_audit.direction == "harm"
    assert audit.value_audit.worse_than_direct is True
    assert audit.value_audit.signed_log_ratio_for_audit > 0.0
    assert audit.value_audit.value_target_log_ratio == 0.0
    assert audit.teacher_eligible is False
    assert "harmful_vs_direct" in audit.ineligibility_reasons


def test_crypto_holdout_origin_is_registry_bound_and_never_teacher() -> None:
    case = _case()
    registry = _registry(
        case,
        split_role="formal_evaluation",
        origin=_origin(
            origin_id="crypto/PRESENT/holdout", partition="evaluation_holdout"
        ),
    )
    record = _random(case, registry)
    audit = _validate_record(record, case, registry)
    assert audit.structural_valid is True
    assert audit.teacher_eligible is False
    assert "split_role_forbids_training" in audit.ineligibility_reasons
    assert "cryptographic_evaluation_holdout_leakage" in audit.ineligibility_reasons


def test_compute_budget_is_structured_and_equality_claim_is_rejected() -> None:
    case = _case()
    registry = _registry(case)
    record = _random(case, registry)
    assert isinstance(record.generator_contract.compute_budget, ComputeBudgetV2)
    assert record.compute_budget_equal is False
    greedy_budget = _greedy(case, registry).generator_contract.compute_budget
    assert greedy_budget.qubo_assignments_audited == 2 ** case.augmented_variable_count
    assert greedy_budget.greedy_candidate_scans_upper_bound == 5
    assert greedy_budget.classical_candidate_evaluations == 5
    assert greedy_budget.bitstrings_generated == OBSERVATION_BUDGET
    poisoned = _rehash_observation(replace(record, compute_budget_equal=True))
    with pytest.raises(ValueError, match="compute_budget_equal"):
        _validate_record(poisoned, case, registry)


def test_manifest_native_types_and_external_anchor_are_strict() -> None:
    case, registry, records, manifest = _group()
    payload = manifest.to_dict()
    payload["arm_observation_sha256"] = tuple(
        payload["arm_observation_sha256"]  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="native list"):
        ReplayGroupManifestV2.from_dict(payload)
    with pytest.raises(ValueError, match="external anchor"):
        validate_replay_group_manifest_v2(
            manifest,
            records,
            case,
            registry,
            expected_manifest_sha256="0" * 64,
        )


def test_qaoa_contract_from_dict_rejects_negative_seed_float_and_nan() -> None:
    case = _case()
    registry = _registry(case)
    contract = _qaoa(case, registry).qaoa_contract
    assert contract is not None
    payload = contract.to_dict()
    payload["scheduler_seed"] = -1
    with pytest.raises(ValueError, match="scheduler_seed"):
        QAOAFinalMeasurementContractV2.from_dict(payload)
    payload = contract.to_dict()
    payload["shots"] = 80.0
    with pytest.raises(TypeError, match="native integer"):
        QAOAFinalMeasurementContractV2.from_dict(payload)
    generator = _random(case, registry).generator_contract.to_dict()
    generator["seed"] = float("nan")
    with pytest.raises(TypeError, match="native integer"):
        GeneratorContractV2.from_dict(generator)


def test_distribution_tamper_cannot_pass_old_observation_or_manifest_anchor() -> None:
    case, registry, records, manifest = _group()
    qaoa = records[2]
    counts = list(qaoa.counts)
    counts[0] = (counts[0][0], counts[0][1] + 1)
    counts[1] = (counts[1][0], counts[1][1] - 1)
    tampered = _rehash_observation(replace(qaoa, counts=tuple(counts)))

    with pytest.raises(ValueError, match="external anchor"):
        validate_final_measurement_observation_v2(
            tampered,
            case,
            registry,
            expected_observation_sha256=qaoa.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
        )
    tampered_records = records[:2] + (tampered,) + records[3:]
    with pytest.raises(ValueError, match="observation SHA|parent binding"):
        validate_replay_group_manifest_v2(
            manifest,
            tampered_records,
            case,
            registry,
            expected_manifest_sha256=manifest.manifest_sha256,
        )
