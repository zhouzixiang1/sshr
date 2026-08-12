"""Deterministic, fail-closed head-only trainer for isolated E6-v2 work.

This module deliberately exposes one fitting entry point.  It accepts raw
four-arm replay materials plus independently anchored canonical corpus/config
bytes; it never accepts a caller-supplied model, replay target, optimiser, or
Python trust capability.  Every group is fully revalidated before a model or
optimiser is created, including the actual QAOA counts, final-parameter and run
attestation bytes.  One call trains exactly one declared replay arm so later
four-arm causal suites can keep identical initialisation and update budgets.

The returned model remains ``modified_unsealed`` under the existing initialized
head contract.  This module neither saves nor blesses trained weights.  Its
report is a development training receipt, not formal or performance evidence.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path
import re
from typing import Iterator, Mapping, Sequence

import torch

from e6.final_measurement_replay_v2 import (
    SOURCE_ARMS,
    TRAINER_REPLAY_CONTRACT,
    TRAIN_SPLIT_ROLE,
    ExternalReplayLockV2,
    FinalMeasurementObservationV2,
    ReplayGroupManifestV2,
    ReplayTargetsV2,
    SplitRegistryEntryV2,
    SplitRegistryV2,
    GeneratorContractV2,
    QAOAFinalMeasurementContractV2,
    ComputeBudgetV2,
    ObservationOriginV2,
    derive_qaoa_replay_targets_from_external_lock_v2,
    derive_replay_targets_v2,
    validate_external_replay_lock_v2,
    validate_replay_group_manifest_v2,
    validate_split_registry_v2,
)
from e6.frozen_case import (
    FrozenCaseHashSemantics,
    FrozenSharedCase,
    canonical_action_sha256,
    validate_frozen_shared_case,
)
from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    VectorANF,
)
from e6.shared_scheduler import (
    DummyFixedCardinalityQUBO,
    SharedSchedulerConfig,
    SharedUtilityWeights,
)
from e6.frozen_foundation_v4_shared_head_v2 import (
    DEFAULT_FORMAL_V4_CHECKPOINT,
    FORMAL_V4_CHECKPOINT_SHA256,
    FrozenFoundationV4SharedPolicyValueV2,
    build_head_only_optimizer,
)
from src.contracts.codec import canonical_json_bytes, sha256_bytes


ISOLATED_HEAD_TRAINER_V2_SCHEMA = (
    "xa.e6-isolated-head-training-report.v2-development"
)
ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA = (
    "xa.e6-isolated-head-training-config.v2-development"
)
ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA = (
    "xa.e6-isolated-head-training-corpus-lock.v2-development"
)
CORPUS_LOCK_AUTHORITY = "local_preseal_external_lock_not_signature"
TRAINING_INPUT_COUNTS = (6, 7)
TRAINING_ORIGIN_KIND = "synthetic"
CLAIM_BOUNDARY = (
    "development head-only training receipt; modified heads are unsealed; "
    "no formal evaluation or performance claim"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LockedReplayTrainingGroupV2:
    """Raw material transported into one trainer invocation.

    The dataclass is not a trust capability.  All fields are parsed, hashed and
    revalidated from their independently anchored roots inside ``fit``.
    """

    case: FrozenSharedCase
    records: tuple[FinalMeasurementObservationV2, ...]
    manifest: ReplayGroupManifestV2
    external_lock_payload: bytes
    qaoa_counts_payload: bytes
    final_parameter_payload: bytes
    run_attestation: bytes
    protocol_payload: bytes
    source_manifest_payload: bytes


@dataclass(frozen=True)
class IsolatedHeadTrainingReportV2:
    schema_version: str
    source_arm: str
    sample_count: int
    group_ids: tuple[str, ...]
    input_counts: tuple[int, ...]
    update_steps: int
    batch_size: int
    sample_presentations: int
    training_schedule_sha256: str
    config_payload_sha256: str
    corpus_payload_sha256: str
    corpus_lock_sha256: str
    split_registry_sha256: str
    protocol_sha256: str
    source_manifest_sha256: str
    foundation_checkpoint_sha256: str
    foundation_tensor_sha256: str
    initial_head_tensor_sha256: str
    final_head_tensor_sha256: str
    initial_weighted_loss: float
    final_weighted_loss: float
    optimizer: str
    trainer_replay_contract: str
    head_training_status: str
    compute_budget_equal: bool
    formal_evaluation: bool
    performance_evidence: bool
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IsolatedHeadTrainingResultV2:
    model: FrozenFoundationV4SharedPolicyValueV2
    report: IsolatedHeadTrainingReportV2


@dataclass(frozen=True)
class _TrainingConfigV2:
    source_arm: str
    update_steps: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    policy_loss_weight: float
    value_loss_weight: float
    max_grad_norm: float
    head_hidden: int
    head_seed: int
    sampler_seed: int


@dataclass(frozen=True)
class _CorpusGroupBindingV2:
    group_id: str
    case_sha256: str
    manifest_sha256: str
    external_lock_sha256: str
    arm_observation_sha256: tuple[tuple[str, str], ...]
    qaoa_counts_payload_sha256: str
    qaoa_final_parameter_payload_sha256: str
    qaoa_run_attestation_sha256: str


@dataclass(frozen=True)
class _CorpusLockV2:
    foundation_checkpoint_sha256: str
    protocol_sha256: str
    source_manifest_sha256: str
    split_registry_sha256: str
    groups: tuple[_CorpusGroupBindingV2, ...]
    lock_sha256: str


@dataclass(frozen=True)
class _TrainingSampleV2:
    group_id: str
    case: FrozenSharedCase
    target: ReplayTargetsV2


_EXACT_PUBLIC_DATACLASS_TYPES = frozenset(
    {
        LockedReplayTrainingGroupV2,
        FrozenCaseHashSemantics,
        FrozenSharedCase,
        VectorANF,
        MonomialSharedAction,
        SemiAffineSharedAction,
        SharedSchedulerConfig,
        SharedUtilityWeights,
        DummyFixedCardinalityQUBO,
        ComputeBudgetV2,
        ObservationOriginV2,
        SplitRegistryEntryV2,
        SplitRegistryV2,
        GeneratorContractV2,
        QAOAFinalMeasurementContractV2,
        FinalMeasurementObservationV2,
        ReplayGroupManifestV2,
    }
)
_EXACT_PUBLIC_LEAF_TYPES = frozenset({str, int, float, bool, bytes, type(None)})


def _precheck_exact_public_graph(value: object, name: str) -> None:
    """Inspect only exact builtins/dataclass fields, invoking no public method.

    ``object.__getattribute__`` is deliberate: after rejecting every subclass,
    the preflight reads frozen dataclass storage without dispatching a hostile
    ``__getattribute__`` or ``to_dict`` implementation.  This pass completes
    before any validator, parser, model constructor or optimiser is called.
    """

    value_type = type(value)
    if value_type in _EXACT_PUBLIC_LEAF_TYPES:
        return
    if value_type is tuple:
        for index, item in enumerate(value):
            _precheck_exact_public_graph(item, f"{name}[{index}]")
        return
    if value_type is frozenset:
        for index, item in enumerate(value):
            _precheck_exact_public_graph(item, f"{name}{{{index}}}")
        return
    if value_type not in _EXACT_PUBLIC_DATACLASS_TYPES:
        raise TypeError(
            f"{name} has forbidden public graph type {value_type.__name__}; "
            "exact active dataclasses and native immutable containers are required"
        )
    for field in fields(value_type):
        field_value = object.__getattribute__(value, field.name)
        _precheck_exact_public_graph(field_value, f"{name}.{field.name}")


def _clone_exact_public_graph(value: object) -> object:
    """Copy the already prechecked graph into fresh exact immutable objects."""

    value_type = type(value)
    if value_type in _EXACT_PUBLIC_LEAF_TYPES:
        return value
    if value_type is tuple:
        return tuple(_clone_exact_public_graph(item) for item in value)
    if value_type is frozenset:
        return frozenset(_clone_exact_public_graph(item) for item in value)
    if value_type not in _EXACT_PUBLIC_DATACLASS_TYPES:  # pragma: no cover
        raise RuntimeError("public graph changed after exact-type preflight")
    kwargs = {
        field.name: _clone_exact_public_graph(
            object.__getattribute__(value, field.name)
        )
        for field in fields(value_type)
    }
    return value_type(**kwargs)


def _canonicalize_public_graph(
    materials: object, registry: object
) -> tuple[tuple[LockedReplayTrainingGroupV2, ...], SplitRegistryV2]:
    if type(materials) is not tuple:
        raise TypeError("materials must be an exact native tuple")
    if type(registry) is not SplitRegistryV2:
        raise TypeError("registry must be exact SplitRegistryV2")
    _precheck_exact_public_graph(materials, "materials")
    _precheck_exact_public_graph(registry, "registry")
    cloned_materials = _clone_exact_public_graph(materials)
    cloned_registry = _clone_exact_public_graph(registry)
    assert type(cloned_materials) is tuple
    assert type(cloned_registry) is SplitRegistryV2
    return cloned_materials, cloned_registry


def _require_sha256(value: object, name: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _require_native_string(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a native string")
    if not value or value != value.strip() or any(ord(item) < 32 for item in value):
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


def _require_native_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a native bool")
    return value


def _require_native_int(
    value: object, name: str, *, minimum: int | None = None
) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _require_finite_number(
    value: object, name: str, *, minimum: float | None = None
) -> float:
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a native finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and converted < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return converted


def _exact_fields(
    payload: Mapping[str, object], expected: set[str], name: str
) -> None:
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"{name} field contract changed: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _strict_canonical_json(
    raw: bytes, *, expected_sha256: str, name: str
) -> dict[str, object]:
    if type(raw) is not bytes:
        raise TypeError(f"{name} payload must be native bytes")
    expected = _require_sha256(expected_sha256, f"expected_{name}_sha256")
    actual = sha256_bytes(raw)
    if actual != expected:
        raise ValueError(f"{name} payload SHA does not match independent anchor")

    def reject_duplicate_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {name}: {key!r}")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} payload is not strict UTF-8 JSON") from exc
    if type(decoded) is not dict:
        raise TypeError(f"{name} payload must decode to a native dict")
    if raw != canonical_json_bytes(decoded):
        raise ValueError(f"{name} payload is not canonical JSON")
    return decoded


def _parse_training_config(
    raw: bytes, *, expected_sha256: str
) -> _TrainingConfigV2:
    payload = _strict_canonical_json(
        raw, expected_sha256=expected_sha256, name="training config"
    )
    expected_fields = {
        "schema_version",
        "source_arm",
        "update_steps",
        "batch_size",
        "learning_rate",
        "weight_decay",
        "policy_loss_weight",
        "value_loss_weight",
        "max_grad_norm",
        "head_hidden",
        "head_seed",
        "sampler_seed",
        "device",
        "dtype",
        "cpu_threads",
        "optimizer",
        "scheduler",
        "early_stopping",
        "resume",
        "performance_evidence",
    }
    _exact_fields(payload, expected_fields, "training config")
    if payload["schema_version"] != ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA:
        raise ValueError("unsupported isolated-head training config schema")
    source_arm = _require_native_string(payload["source_arm"], "source_arm")
    if source_arm not in SOURCE_ARMS:
        raise ValueError("training config source_arm is not registered")
    if payload["device"] != "cpu" or payload["dtype"] != "float32":
        raise ValueError("isolated-head trainer requires CPU FP32")
    if _require_native_int(payload["cpu_threads"], "cpu_threads", minimum=1) != 1:
        raise ValueError("isolated-head trainer requires cpu_threads=1")
    if payload["optimizer"] != "HeadOnlyIntegrityAdamW":
        raise ValueError("isolated-head trainer requires HeadOnlyIntegrityAdamW")
    if payload["scheduler"] != "none":
        raise ValueError("isolated-head trainer forbids learning-rate schedulers")
    if _require_native_bool(payload["early_stopping"], "early_stopping"):
        raise ValueError("isolated-head trainer forbids early stopping")
    if _require_native_bool(payload["resume"], "resume"):
        raise ValueError("isolated-head trainer forbids resume")
    if _require_native_bool(
        payload["performance_evidence"], "performance_evidence"
    ):
        raise ValueError("development training is not performance evidence")
    learning_rate = _require_finite_number(
        payload["learning_rate"], "learning_rate", minimum=0.0
    )
    if learning_rate <= 0.0:
        raise ValueError("learning_rate must be positive")
    max_grad_norm = _require_finite_number(
        payload["max_grad_norm"], "max_grad_norm", minimum=0.0
    )
    if max_grad_norm != 1.0:
        raise ValueError("isolated-head trainer fixes max_grad_norm=1.0")
    policy_loss_weight = _require_finite_number(
        payload["policy_loss_weight"], "policy_loss_weight", minimum=0.0
    )
    value_loss_weight = _require_finite_number(
        payload["value_loss_weight"], "value_loss_weight", minimum=0.0
    )
    if policy_loss_weight == 0.0 and value_loss_weight == 0.0:
        raise ValueError("at least one isolated-head loss weight must be positive")
    return _TrainingConfigV2(
        source_arm=source_arm,
        update_steps=_require_native_int(
            payload["update_steps"], "update_steps", minimum=1
        ),
        batch_size=_require_native_int(
            payload["batch_size"], "batch_size", minimum=1
        ),
        learning_rate=learning_rate,
        weight_decay=_require_finite_number(
            payload["weight_decay"], "weight_decay", minimum=0.0
        ),
        policy_loss_weight=policy_loss_weight,
        value_loss_weight=value_loss_weight,
        max_grad_norm=max_grad_norm,
        head_hidden=_require_native_int(
            payload["head_hidden"], "head_hidden", minimum=1
        ),
        head_seed=_require_native_int(
            payload["head_seed"], "head_seed", minimum=0
        ),
        sampler_seed=_require_native_int(
            payload["sampler_seed"], "sampler_seed", minimum=0
        ),
    )


def _parse_arm_bindings(raw: object) -> tuple[tuple[str, str], ...]:
    if type(raw) is not list:
        raise TypeError("corpus group arm_observation_sha256 must be a native list")
    rows: list[tuple[str, str]] = []
    for index, raw_row in enumerate(raw):
        if type(raw_row) is not list or len(raw_row) != 2:
            raise ValueError(
                f"corpus group arm_observation_sha256[{index}] width changed"
            )
        arm = _require_native_string(raw_row[0], f"arm binding {index} arm")
        digest = _require_sha256(raw_row[1], f"arm binding {index} SHA")
        rows.append((arm, digest))
    result = tuple(rows)
    if tuple(arm for arm, _ in result) != SOURCE_ARMS:
        raise ValueError("corpus group arm bindings must use exact SOURCE_ARMS order")
    return result


def _parse_corpus_lock(
    raw: bytes, *, expected_sha256: str
) -> _CorpusLockV2:
    payload = _strict_canonical_json(
        raw, expected_sha256=expected_sha256, name="training corpus lock"
    )
    expected_fields = {
        "schema_version",
        "authority",
        "foundation_checkpoint_sha256",
        "protocol_sha256",
        "source_manifest_sha256",
        "split_registry_sha256",
        "source_arms",
        "training_split_role",
        "training_input_counts",
        "origin_kind",
        "groups",
        "performance_evidence",
        "lock_sha256",
    }
    _exact_fields(payload, expected_fields, "training corpus lock")
    if payload["schema_version"] != ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA:
        raise ValueError("unsupported isolated-head training corpus lock schema")
    if payload["authority"] != CORPUS_LOCK_AUTHORITY:
        raise ValueError("training corpus lock authority changed")
    if payload["source_arms"] != list(SOURCE_ARMS):
        raise ValueError("training corpus lock source arms changed")
    if payload["training_split_role"] != TRAIN_SPLIT_ROLE:
        raise ValueError("training corpus lock split role changed")
    if payload["training_input_counts"] != list(TRAINING_INPUT_COUNTS):
        raise ValueError("training corpus lock input-count envelope changed")
    if payload["origin_kind"] != TRAINING_ORIGIN_KIND:
        raise ValueError("training corpus lock origin kind changed")
    if _require_native_bool(
        payload["performance_evidence"], "corpus performance_evidence"
    ):
        raise ValueError("development corpus is not performance evidence")
    foundation_sha = _require_sha256(
        payload["foundation_checkpoint_sha256"],
        "corpus foundation_checkpoint_sha256",
    )
    if foundation_sha != FORMAL_V4_CHECKPOINT_SHA256:
        raise ValueError("training corpus foundation checkpoint identity changed")
    raw_groups = payload["groups"]
    if type(raw_groups) is not list or not raw_groups:
        raise ValueError("training corpus lock requires at least one group")
    group_fields = {
        "group_id",
        "case_sha256",
        "manifest_sha256",
        "external_lock_sha256",
        "arm_observation_sha256",
        "qaoa_counts_payload_sha256",
        "qaoa_final_parameter_payload_sha256",
        "qaoa_run_attestation_sha256",
    }
    groups: list[_CorpusGroupBindingV2] = []
    for index, raw_group in enumerate(raw_groups):
        if type(raw_group) is not dict:
            raise TypeError(f"corpus groups[{index}] must be a native dict")
        _exact_fields(raw_group, group_fields, f"corpus groups[{index}]")
        groups.append(
            _CorpusGroupBindingV2(
                group_id=_require_sha256(raw_group["group_id"], "group_id"),
                case_sha256=_require_sha256(
                    raw_group["case_sha256"], "case_sha256"
                ),
                manifest_sha256=_require_sha256(
                    raw_group["manifest_sha256"], "manifest_sha256"
                ),
                external_lock_sha256=_require_sha256(
                    raw_group["external_lock_sha256"], "external_lock_sha256"
                ),
                arm_observation_sha256=_parse_arm_bindings(
                    raw_group["arm_observation_sha256"]
                ),
                qaoa_counts_payload_sha256=_require_sha256(
                    raw_group["qaoa_counts_payload_sha256"],
                    "qaoa_counts_payload_sha256",
                ),
                qaoa_final_parameter_payload_sha256=_require_sha256(
                    raw_group["qaoa_final_parameter_payload_sha256"],
                    "qaoa_final_parameter_payload_sha256",
                ),
                qaoa_run_attestation_sha256=_require_sha256(
                    raw_group["qaoa_run_attestation_sha256"],
                    "qaoa_run_attestation_sha256",
                ),
            )
        )
    canonical_groups = tuple(sorted(groups, key=lambda item: item.group_id))
    if tuple(groups) != canonical_groups:
        raise ValueError("training corpus groups are not in canonical group_id order")
    if len({item.group_id for item in groups}) != len(groups):
        raise ValueError("training corpus group_id values must be unique")
    preimage = dict(payload)
    preimage.pop("lock_sha256")
    lock_sha = _require_sha256(payload["lock_sha256"], "corpus lock_sha256")
    if lock_sha != sha256_bytes(canonical_json_bytes(preimage)):
        raise ValueError("training corpus lock canonical SHA mismatch")
    return _CorpusLockV2(
        foundation_checkpoint_sha256=foundation_sha,
        protocol_sha256=_require_sha256(
            payload["protocol_sha256"], "corpus protocol_sha256"
        ),
        source_manifest_sha256=_require_sha256(
            payload["source_manifest_sha256"], "corpus source_manifest_sha256"
        ),
        split_registry_sha256=_require_sha256(
            payload["split_registry_sha256"], "corpus split_registry_sha256"
        ),
        groups=canonical_groups,
        lock_sha256=lock_sha,
    )


def _validate_material_shape(material: LockedReplayTrainingGroupV2) -> None:
    if type(material) is not LockedReplayTrainingGroupV2:
        raise TypeError("training materials must be exact LockedReplayTrainingGroupV2")
    if type(material.case) is not FrozenSharedCase:
        raise TypeError("training material case must be exact FrozenSharedCase")
    if type(material.manifest) is not ReplayGroupManifestV2:
        raise TypeError("training material manifest must be exact ReplayGroupManifestV2")
    if type(material.records) is not tuple or len(material.records) != len(SOURCE_ARMS):
        raise ValueError("training material requires one exact four-arm record tuple")
    if any(type(record) is not FinalMeasurementObservationV2 for record in material.records):
        raise TypeError("training material records must be exact observations")
    if tuple(record.source_arm for record in material.records) != SOURCE_ARMS:
        raise ValueError("training material records must use exact SOURCE_ARMS order")
    for name in (
        "external_lock_payload",
        "qaoa_counts_payload",
        "final_parameter_payload",
        "run_attestation",
        "protocol_payload",
        "source_manifest_payload",
    ):
        if type(getattr(material, name)) is not bytes:
            raise TypeError(f"training material {name} must be native bytes")


def _validate_target(
    target: ReplayTargetsV2,
    case: FrozenSharedCase,
    *,
    source_arm: str,
    expected_observation_sha256: str,
) -> None:
    if type(target) is not ReplayTargetsV2:
        raise TypeError("replay target must be exact ReplayTargetsV2")
    if target.source_arm != source_arm:
        raise ValueError("derived replay target source arm changed")
    if target.observation_sha256 != expected_observation_sha256:
        raise ValueError("derived replay target observation binding changed")
    if target.trainer_replay_contract != TRAINER_REPLAY_CONTRACT:
        raise ValueError("derived replay target trainer contract changed")
    expected_signatures = tuple(canonical_action_sha256(action) for action in case.actions)
    if target.action_signatures != expected_signatures:
        raise ValueError("derived replay target action order changed")
    policy = target.policy_target
    if not policy or len(policy) != len(case.actions):
        raise ValueError("derived policy target must align with a non-empty action pool")
    if any(type(value) is not float or not math.isfinite(value) or value < 0.0 for value in policy):
        raise ValueError("derived policy target contains an invalid probability")
    if not math.isclose(math.fsum(policy), 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("derived policy target must sum to one")
    for name, value in (
        ("policy_observation_weight", target.policy_observation_weight),
        ("value_observation_weight", target.value_observation_weight),
        ("value_target_log_ratio", target.value_target_log_ratio),
    ):
        if type(value) is not float or not math.isfinite(value):
            raise ValueError(f"derived {name} must be a native finite float")
    if target.policy_observation_weight <= 0.0:
        raise ValueError("derived policy observation weight must be positive")
    if target.value_observation_weight <= 0.0:
        raise ValueError("derived value observation weight must be positive")
    if not -3.0 <= target.value_target_log_ratio <= 0.0:
        raise ValueError("derived value target must remain in [-3, 0]")
    if target.value_loss_weight_contract != (
        "trainer_must_multiply_each_observation_value_loss_by_"
        "value_observation_weight"
    ):
        raise ValueError("derived value-loss weight contract changed")


def _validate_and_derive_samples(
    materials: tuple[LockedReplayTrainingGroupV2, ...],
    registry: SplitRegistryV2,
    corpus: _CorpusLockV2,
    config: _TrainingConfigV2,
) -> tuple[_TrainingSampleV2, ...]:
    if type(registry) is not SplitRegistryV2:
        raise TypeError("registry must be exact SplitRegistryV2")
    validate_split_registry_v2(
        registry, expected_registry_sha256=corpus.split_registry_sha256
    )
    for entry in registry.entries:
        if entry.split_role != TRAIN_SPLIT_ROLE:
            raise ValueError("trainer registry may contain train_replay entries only")
        if entry.origin.origin_kind != TRAINING_ORIGIN_KIND:
            raise ValueError("trainer registry may contain synthetic origins only")
        if entry.origin.crypto_holdout_leakage_risk:
            raise ValueError("trainer registry contains cryptographic holdout leakage")
    material_tuple = tuple(materials)
    if not material_tuple:
        raise ValueError("at least one locked replay training group is required")
    for material in material_tuple:
        _validate_material_shape(material)
    by_group: dict[str, LockedReplayTrainingGroupV2] = {}
    for material in material_tuple:
        group_id = material.manifest.group_id
        if group_id in by_group:
            raise ValueError("training materials contain a duplicate group_id")
        by_group[group_id] = material
    expected_group_ids = tuple(binding.group_id for binding in corpus.groups)
    if set(by_group) != set(expected_group_ids) or len(by_group) != len(expected_group_ids):
        raise ValueError("training materials do not exactly match the corpus lock groups")

    samples: list[_TrainingSampleV2] = []
    seen_registry_vectors: set[str] = set()
    for binding in corpus.groups:
        material = by_group[binding.group_id]
        case = material.case
        records = material.records
        manifest = material.manifest
        validate_frozen_shared_case(case)
        if case.vector.input_count not in TRAINING_INPUT_COUNTS:
            raise ValueError("isolated-head training accepts synthetic n=6/7 only")
        if case.case_sha256 != binding.case_sha256:
            raise ValueError("training case SHA does not match corpus lock")
        if manifest.group_id != binding.group_id:
            raise ValueError("training manifest group_id does not match corpus lock")
        if manifest.manifest_sha256 != binding.manifest_sha256:
            raise ValueError("training manifest SHA does not match corpus lock")
        if manifest.protocol_sha256 != corpus.protocol_sha256:
            raise ValueError("training manifest protocol binding changed")
        if manifest.source_manifest_sha256 != corpus.source_manifest_sha256:
            raise ValueError("training manifest source-manifest binding changed")
        if manifest.split_registry_sha256 != corpus.split_registry_sha256:
            raise ValueError("training manifest registry binding changed")
        if manifest.split_role != TRAIN_SPLIT_ROLE:
            raise ValueError("training manifest split role forbids updates")
        if sha256_bytes(material.protocol_payload) != corpus.protocol_sha256:
            raise ValueError("actual protocol payload bytes do not match corpus lock")
        if sha256_bytes(material.source_manifest_payload) != corpus.source_manifest_sha256:
            raise ValueError("actual source-manifest payload bytes do not match corpus lock")
        if manifest.arm_observation_sha256 != binding.arm_observation_sha256:
            raise ValueError("training observation bindings do not match corpus lock")
        if sha256_bytes(material.qaoa_counts_payload) != binding.qaoa_counts_payload_sha256:
            raise ValueError("actual QAOA counts payload bytes do not match corpus lock")
        if sha256_bytes(material.final_parameter_payload) != (
            binding.qaoa_final_parameter_payload_sha256
        ):
            raise ValueError("actual QAOA final-parameter bytes do not match corpus lock")
        if sha256_bytes(material.run_attestation) != binding.qaoa_run_attestation_sha256:
            raise ValueError("actual QAOA run-attestation bytes do not match corpus lock")

        entries = tuple(
            entry
            for entry in registry.entries
            if entry.family_id == manifest.family_id
            and entry.orbit_cluster_sha256 == manifest.orbit_cluster_sha256
        )
        if len(entries) != 1:
            raise ValueError("training group is not uniquely registered")
        entry = entries[0]
        if entry.vector_sha256 != case.vector_sha256:
            raise ValueError("training registry vector binding changed")
        if entry.split_role != TRAIN_SPLIT_ROLE:
            raise ValueError("training registry split role forbids updates")
        if entry.origin.origin_kind != TRAINING_ORIGIN_KIND:
            raise ValueError("isolated-head training accepts synthetic origins only")
        if entry.origin.crypto_holdout_leakage_risk:
            raise ValueError("cryptographic holdout material cannot enter training")
        seen_registry_vectors.add(entry.vector_sha256)

        validate_replay_group_manifest_v2(
            manifest,
            records,
            case,
            registry,
            expected_manifest_sha256=binding.manifest_sha256,
        )
        lock = ExternalReplayLockV2.from_bytes(material.external_lock_payload)
        if lock.lock_sha256 != binding.external_lock_sha256:
            raise ValueError("external replay lock SHA does not match corpus lock")
        # The returned internal object is intentionally discarded.  It is not a
        # public trainer input or a durable trust capability.
        validate_external_replay_lock_v2(
            lock,
            manifest,
            records,
            case,
            registry,
            expected_lock_sha256=binding.external_lock_sha256,
            qaoa_counts_payload=material.qaoa_counts_payload,
            final_parameter_payload=material.final_parameter_payload,
            run_attestation=material.run_attestation,
        )

        by_arm = {record.source_arm: record for record in records}
        record = by_arm[config.source_arm]
        expected_observation_sha = dict(binding.arm_observation_sha256)[
            config.source_arm
        ]
        if config.source_arm in {
            "qaoa_final_measurement_replay",
            "qaoa_permuted_label_control",
        }:
            target = derive_qaoa_replay_targets_from_external_lock_v2(
                record,
                manifest,
                records,
                case,
                registry,
                expected_observation_sha256=expected_observation_sha,
                expected_registry_sha256=corpus.split_registry_sha256,
                lock=lock,
                expected_lock_sha256=binding.external_lock_sha256,
                qaoa_counts_payload=material.qaoa_counts_payload,
                final_parameter_payload=material.final_parameter_payload,
                run_attestation=material.run_attestation,
            )
        else:
            target = derive_replay_targets_v2(
                record,
                case,
                registry,
                expected_observation_sha256=expected_observation_sha,
                expected_registry_sha256=corpus.split_registry_sha256,
            )
        _validate_target(
            target,
            case,
            source_arm=config.source_arm,
            expected_observation_sha256=expected_observation_sha,
        )
        samples.append(_TrainingSampleV2(binding.group_id, case, target))

    registered_train_vectors = {
        entry.vector_sha256
        for entry in registry.entries
        if entry.split_role == TRAIN_SPLIT_ROLE
    }
    if registered_train_vectors != seen_registry_vectors:
        raise ValueError("global training registry contains unbound train vectors")
    return tuple(samples)


def _training_schedule(
    samples: Sequence[_TrainingSampleV2], config: _TrainingConfigV2
) -> tuple[tuple[int, ...], str]:
    required = config.update_steps * config.batch_size
    flat: list[int] = []
    epoch = 0
    while len(flat) < required:
        order = sorted(
            range(len(samples)),
            key=lambda index: sha256_bytes(
                canonical_json_bytes(
                    {
                        "schema_version": "xa.e6-isolated-head-sampler-key.v2",
                        "sampler_seed": config.sampler_seed,
                        "epoch": epoch,
                        "group_id": samples[index].group_id,
                    }
                )
            ),
        )
        flat.extend(order)
        epoch += 1
    selected = tuple(flat[:required])
    batches = tuple(
        selected[offset : offset + config.batch_size]
        for offset in range(0, required, config.batch_size)
    )
    schedule_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "xa.e6-isolated-head-training-schedule.v2",
                "sampler_seed": config.sampler_seed,
                "update_steps": config.update_steps,
                "batch_size": config.batch_size,
                "group_ids_by_presentation": [
                    samples[index].group_id for index in selected
                ],
            }
        )
    )
    return batches, schedule_sha


def _sample_weighted_loss(
    model: FrozenFoundationV4SharedPolicyValueV2,
    sample: _TrainingSampleV2,
    config: _TrainingConfigV2,
) -> torch.Tensor:
    logits, value = model.forward_one(
        sample.case.vector,
        sample.case.actions,
        weights=sample.case.utility_weights,
    )
    if logits.ndim != 1 or logits.numel() != len(sample.target.policy_target):
        raise RuntimeError("trainer logits no longer align with the replay target")
    if value.ndim != 0:
        raise RuntimeError("trainer value output must remain scalar")
    if not bool(torch.isfinite(logits).all()) or not bool(torch.isfinite(value)):
        raise FloatingPointError("trainer model output is non-finite")
    policy_target = torch.tensor(
        sample.target.policy_target, dtype=logits.dtype, device=logits.device
    )
    value_target = torch.tensor(
        sample.target.value_target_log_ratio,
        dtype=value.dtype,
        device=value.device,
    )
    policy_loss = -(
        policy_target * torch.log_softmax(logits, dim=-1)
    ).sum()
    value_loss = (value - value_target).square()
    loss = (
        config.policy_loss_weight
        * sample.target.policy_observation_weight
        * policy_loss
        + config.value_loss_weight
        * sample.target.value_observation_weight
        * value_loss
    )
    if loss.ndim != 0 or not bool(torch.isfinite(loss)):
        raise FloatingPointError("trainer weighted loss is non-finite")
    return loss


@torch.no_grad()
def _mean_weighted_loss(
    model: FrozenFoundationV4SharedPolicyValueV2,
    samples: Sequence[_TrainingSampleV2],
    config: _TrainingConfigV2,
) -> float:
    model.eval()
    result = torch.stack(
        tuple(_sample_weighted_loss(model, sample, config) for sample in samples)
    ).mean()
    if not bool(torch.isfinite(result)):
        raise FloatingPointError("trainer mean weighted loss is non-finite")
    return float(result)


@contextmanager
def _deterministic_cpu_context() -> Iterator[None]:
    previous_threads = torch.get_num_threads()
    previous_debug_mode = torch.get_deterministic_debug_mode()
    try:
        torch.set_num_threads(1)
        torch.set_deterministic_debug_mode("error")
        yield
    finally:
        torch.set_deterministic_debug_mode(previous_debug_mode)
        torch.set_num_threads(previous_threads)


def fit_isolated_head_from_locked_replay_v2(
    materials: tuple[LockedReplayTrainingGroupV2, ...],
    registry: SplitRegistryV2,
    *,
    corpus_lock_payload: bytes,
    expected_corpus_lock_payload_sha256: str,
    config_payload: bytes,
    expected_config_payload_sha256: str,
    foundation_checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
) -> IsolatedHeadTrainingResultV2:
    """Validate one locked corpus, train one arm, and return an unsealed model.

    All corpus, replay and payload validation completes before model/optimiser
    construction.  ``expected_*`` digests are independent roots and must not be
    derived from the supplied payloads inside the training process.
    """

    canonical_materials, canonical_registry = _canonicalize_public_graph(
        materials, registry
    )
    config = _parse_training_config(
        config_payload, expected_sha256=expected_config_payload_sha256
    )
    corpus = _parse_corpus_lock(
        corpus_lock_payload,
        expected_sha256=expected_corpus_lock_payload_sha256,
    )
    samples = _validate_and_derive_samples(
        canonical_materials, canonical_registry, corpus, config
    )
    batches, schedule_sha = _training_schedule(samples, config)

    with _deterministic_cpu_context():
        model = FrozenFoundationV4SharedPolicyValueV2(
            foundation_checkpoint_path,
            head_hidden=config.head_hidden,
            head_seed=config.head_seed,
        )
        if model.foundation_identity.checkpoint_sha256 != (
            corpus.foundation_checkpoint_sha256
        ):
            raise ValueError("loaded foundation does not match the corpus lock")
        initial_head_sha = model.current_head_tensor_sha256()
        initial_loss = _mean_weighted_loss(model, samples, config)
        model.train().requires_grad_(True)
        optimiser = build_head_only_optimizer(
            model,
            learning_rate=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        for batch in batches:
            optimiser.zero_grad(set_to_none=True)
            loss = torch.stack(
                tuple(
                    _sample_weighted_loss(model, samples[index], config)
                    for index in batch
                )
            ).mean()
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("trainer batch loss is non-finite")
            loss.backward()
            gradients = tuple(
                parameter.grad
                for parameter in model.head_parameters()
                if parameter.grad is not None
            )
            if not gradients or any(
                not bool(torch.isfinite(gradient).all()) for gradient in gradients
            ):
                raise FloatingPointError("trainer head gradient is missing or non-finite")
            if any(
                parameter.grad is not None
                for parameter in model.foundation_trunk.parameters()
            ):
                raise RuntimeError("frozen foundation accumulated a trainer gradient")
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.head_parameters(),
                config.max_grad_norm,
                error_if_nonfinite=True,
            )
            if not bool(torch.isfinite(gradient_norm)):
                raise FloatingPointError("trainer gradient norm is non-finite")
            optimiser.step()
        model.eval().requires_grad_(False)
        model.assert_foundation_integrity()
        final_head_sha = model.current_head_tensor_sha256()
        if final_head_sha == initial_head_sha:
            raise RuntimeError("head-only training performed no parameter mutation")
        if model.head_training_status != "modified_unsealed":
            raise RuntimeError("trained head must remain modified_unsealed")
        final_loss = _mean_weighted_loss(model, samples, config)
        model.assert_foundation_integrity()

    report = IsolatedHeadTrainingReportV2(
        schema_version=ISOLATED_HEAD_TRAINER_V2_SCHEMA,
        source_arm=config.source_arm,
        sample_count=len(samples),
        group_ids=tuple(sample.group_id for sample in samples),
        input_counts=tuple(sorted({sample.case.vector.input_count for sample in samples})),
        update_steps=config.update_steps,
        batch_size=config.batch_size,
        sample_presentations=config.update_steps * config.batch_size,
        training_schedule_sha256=schedule_sha,
        config_payload_sha256=sha256_bytes(config_payload),
        corpus_payload_sha256=sha256_bytes(corpus_lock_payload),
        corpus_lock_sha256=corpus.lock_sha256,
        split_registry_sha256=corpus.split_registry_sha256,
        protocol_sha256=corpus.protocol_sha256,
        source_manifest_sha256=corpus.source_manifest_sha256,
        foundation_checkpoint_sha256=model.foundation_identity.checkpoint_sha256,
        foundation_tensor_sha256=model.foundation_identity.tensor_sha256,
        initial_head_tensor_sha256=initial_head_sha,
        final_head_tensor_sha256=final_head_sha,
        initial_weighted_loss=initial_loss,
        final_weighted_loss=final_loss,
        optimizer="HeadOnlyIntegrityAdamW",
        trainer_replay_contract=TRAINER_REPLAY_CONTRACT,
        head_training_status="modified_unsealed",
        compute_budget_equal=False,
        formal_evaluation=False,
        performance_evidence=False,
        claim_boundary=CLAIM_BOUNDARY,
    )
    return IsolatedHeadTrainingResultV2(model=model, report=report)


__all__ = [
    "CLAIM_BOUNDARY",
    "CORPUS_LOCK_AUTHORITY",
    "ISOLATED_HEAD_TRAINER_V2_SCHEMA",
    "ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA",
    "ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA",
    "IsolatedHeadTrainingReportV2",
    "IsolatedHeadTrainingResultV2",
    "LockedReplayTrainingGroupV2",
    "fit_isolated_head_from_locked_replay_v2",
]
