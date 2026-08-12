"""Deterministic synthetic corpus builder for the E6 replay-training experiment.

The builder joins the already-audited E6 components into ordinary in-memory
training inputs:

* structured synthetic vector Boolean functions at n=6/7;
* complete monomial and semi-affine candidate enumeration;
* a common six-action, budget-two frozen scheduling pool;
* real ``schedule_frozen_case(..., "qaoa")`` final-measurement counts; and
* all four replay arms accepted by the isolated head trainer.

The ``ExternalReplayLockV2`` object produced here is only a compatibility
payload required by the existing trainer API.  It is generated and consumed in
one ordinary run, is not an independent trust root or signature, and confers no
formal-evidence status.  The public descriptor is sufficient to rebuild the
complete corpus and compare every canonical binding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math
import re
from typing import Mapping

from e6.final_measurement_replay_v2 import (
    EXTERNAL_LOCK_AUTHORITY,
    EXTERNAL_REPLAY_LOCK_V2_SCHEMA,
    SOURCE_ARMS,
    TRAIN_SPLIT_ROLE,
    ComputeBudgetV2,
    ExternalReplayLockV2,
    ObservationOriginV2,
    ReplayTargetsV2,
    SplitRegistrySourceV2,
    SplitRegistryV2,
    build_classical_greedy_observation_v2,
    build_classical_random_observation_v2,
    build_qaoa_final_measurement_observation_v2,
    build_qaoa_permuted_label_control_v2,
    build_replay_group_manifest_v2,
    build_split_registry_v2,
    canonical_vector_orbit_sha256,
    derive_qaoa_replay_targets_from_external_lock_v2,
    derive_replay_targets_v2,
    qaoa_counts_payload_bytes_v2,
    validate_external_replay_lock_v2,
)
from e6.frozen_case import (
    FrozenSharedCase,
    build_frozen_shared_case,
    canonical_action_sha256,
    schedule_frozen_case,
)
from e6.frozen_foundation_v4_shared_head_v2 import FORMAL_V4_CHECKPOINT_SHA256
from e6.isolated_head_trainer_v2 import (
    CORPUS_LOCK_AUTHORITY,
    ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA,
    LockedReplayTrainingGroupV2,
)
from e6.shared_oracle import (
    SharedAction,
    VectorANF,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
)
from e6.shared_scheduler import SharedSchedulerConfig, shared_action_utility
from src.contracts.codec import canonical_json_bytes, sha256_bytes


CORPUS_BUILD_SPEC_V1_SCHEMA = "xa.e6-replay-training-corpus-build-spec.v1-development"
CORPUS_DESCRIPTOR_V1_SCHEMA = "xa.e6-replay-training-corpus-descriptor.v1-development"
CORPUS_CASE_DESCRIPTOR_V1_SCHEMA = (
    "xa.e6-replay-training-corpus-case-descriptor.v1-development"
)
CORPUS_GENERATOR_ID = "sha256-ranked-structured-vector-anf-v1"
PROTOCOL_SCHEMA = "xa.e6-replay-training-protocol.v1-development"
SOURCE_MANIFEST_SCHEMA = "xa.e6-replay-training-source-manifest.v1-development"
FINAL_PARAMETER_SCHEMA = "xa.e6-qaoa-final-parameter-payload.v1-development"
RUN_ATTESTATION_SCHEMA = "xa.e6-local-qaoa-run-receipt.v1-development"
TECHNICAL_LOCK_SEMANTICS = "same_process_trainer_api_compatibility_only_not_signature_or_independent_trust_root"
INPUT_COUNTS = (6, 7)
OUTPUT_COUNT = 6
SHARED_MONOMIAL_BLOCK_COUNT = 4
SEMI_AFFINE_BLOCK_COUNT = 1
UNIQUE_FILLER_COUNT = OUTPUT_COUNT
CANDIDATE_CAP = 6
SCHEDULER_BUDGET = 2
QAOA_P = 1
MAX_GENERATION_ATTEMPTS = 128

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _native_dict(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{name} must be a native dict")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name} keys must be native strings")
    return value  # type: ignore[return-value]


def _native_list(value: object, name: str) -> list[object]:
    if type(value) is not list:
        raise TypeError(f"{name} must be a native list")
    return value  # type: ignore[return-value]


def _exact_fields(value: Mapping[str, object], expected: set[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{name} field contract changed: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _string(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a native string")
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


def _boolean(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a native bool")
    return value


def _digest(value: object, name: str) -> str:
    text = _string(value, name)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return text


def _finite_tuple(raw: object, name: str) -> tuple[float, ...]:
    values = _native_list(raw, name)
    result: list[float] = []
    for index, value in enumerate(values):
        if type(value) not in {int, float}:
            raise TypeError(f"{name}[{index}] must be a native finite number")
        converted = float(value)
        if not math.isfinite(converted):
            raise ValueError(f"{name}[{index}] must be finite")
        result.append(converted)
    return tuple(result)


def _pair_tuple(
    raw: object, name: str, *, digest_value: bool
) -> tuple[tuple[str, object], ...]:
    rows = _native_list(raw, name)
    result: list[tuple[str, object]] = []
    for index, row in enumerate(rows):
        if type(row) is not list or len(row) != 2:
            raise ValueError(f"{name}[{index}] must be a two-item native list")
        key = _string(row[0], f"{name}[{index}].key")
        value = (
            _digest(row[1], f"{name}[{index}].value")
            if digest_value
            else _integer(row[1], f"{name}[{index}].value", minimum=1)
        )
        result.append((key, value))
    if len({key for key, _ in result}) != len(result):
        raise ValueError(f"{name} contains duplicate keys")
    return tuple(result)


@dataclass(frozen=True)
class CorpusBuildSpecV1:
    seed: int = 20260912
    cases_per_width: int = 2
    observation_budget: int = 128
    qaoa_optimizer_restarts: int = 1
    qaoa_optimizer_steps: int = 2

    def __post_init__(self) -> None:
        for name, minimum in (
            ("seed", 0),
            ("cases_per_width", 1),
            ("observation_budget", 1),
            ("qaoa_optimizer_restarts", 1),
            ("qaoa_optimizer_steps", 0),
        ):
            object.__setattr__(
                self, name, _integer(getattr(self, name), name, minimum=minimum)
            )
        if self.cases_per_width > 32:
            raise ValueError("cases_per_width must be <= 32")

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": CORPUS_BUILD_SPEC_V1_SCHEMA, **asdict(self)}

    @classmethod
    def from_dict(cls, raw: object) -> "CorpusBuildSpecV1":
        payload = _native_dict(raw, "corpus build spec")
        expected = {"schema_version", *cls.__dataclass_fields__}
        _exact_fields(payload, expected, "corpus build spec")
        if payload["schema_version"] != CORPUS_BUILD_SPEC_V1_SCHEMA:
            raise ValueError("unsupported corpus build spec schema")
        return cls(
            seed=_integer(payload["seed"], "seed"),
            cases_per_width=_integer(
                payload["cases_per_width"], "cases_per_width", minimum=1
            ),
            observation_budget=_integer(
                payload["observation_budget"], "observation_budget", minimum=1
            ),
            qaoa_optimizer_restarts=_integer(
                payload["qaoa_optimizer_restarts"], "qaoa_optimizer_restarts", minimum=1
            ),
            qaoa_optimizer_steps=_integer(
                payload["qaoa_optimizer_steps"], "qaoa_optimizer_steps"
            ),
        )


@dataclass(frozen=True)
class CorpusCaseDescriptorV1:
    schema_version: str
    case_id: str
    family_id: str
    case_index: int
    generation_attempt: int
    input_count: int
    output_count: int
    shared_monomial_blocks: int
    semi_affine_blocks: int
    unique_fillers: int
    vector_sha256: str
    orbit_cluster_sha256: str
    case_sha256: str
    source_candidate_count: int
    candidate_cap_effective: int
    scheduler_budget: int
    augmented_variable_count: int
    raw_neutral_learned_equals_raw: bool
    group_id: str
    split_role: str
    manifest_sha256: str
    technical_lock_sha256: str
    qaoa_execution_class: str
    qaoa_counts_payload_sha256: str
    qaoa_final_parameter_payload_sha256: str
    qaoa_run_attestation_sha256: str
    qaoa_gammas: tuple[float, ...]
    qaoa_betas: tuple[float, ...]
    qaoa_counts: tuple[tuple[str, int], ...]
    arm_observation_sha256: tuple[tuple[str, str], ...]
    target_sha256_by_arm: tuple[tuple[str, str], ...]
    teacher_eligible_arms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["qaoa_gammas"] = list(self.qaoa_gammas)
        payload["qaoa_betas"] = list(self.qaoa_betas)
        payload["qaoa_counts"] = [list(item) for item in self.qaoa_counts]
        payload["arm_observation_sha256"] = [
            list(item) for item in self.arm_observation_sha256
        ]
        payload["target_sha256_by_arm"] = [
            list(item) for item in self.target_sha256_by_arm
        ]
        payload["teacher_eligible_arms"] = list(self.teacher_eligible_arms)
        return payload

    @classmethod
    def from_dict(cls, raw: object) -> "CorpusCaseDescriptorV1":
        payload = _native_dict(raw, "corpus case descriptor")
        _exact_fields(payload, set(cls.__dataclass_fields__), "corpus case descriptor")
        if payload["schema_version"] != CORPUS_CASE_DESCRIPTOR_V1_SCHEMA:
            raise ValueError("unsupported corpus case descriptor schema")
        arms = tuple(
            _string(value, f"teacher_eligible_arms[{index}]")
            for index, value in enumerate(
                _native_list(payload["teacher_eligible_arms"], "teacher_eligible_arms")
            )
        )
        if arms != SOURCE_ARMS:
            raise ValueError("all four source arms must be teacher eligible")
        arm_shas_raw = _pair_tuple(
            payload["arm_observation_sha256"],
            "arm_observation_sha256",
            digest_value=True,
        )
        arm_shas = tuple((key, str(value)) for key, value in arm_shas_raw)
        if tuple(key for key, _ in arm_shas) != SOURCE_ARMS:
            raise ValueError("arm observation bindings changed order")
        target_shas_raw = _pair_tuple(
            payload["target_sha256_by_arm"],
            "target_sha256_by_arm",
            digest_value=True,
        )
        target_shas = tuple((key, str(value)) for key, value in target_shas_raw)
        if tuple(key for key, _ in target_shas) != SOURCE_ARMS:
            raise ValueError("target bindings changed order")
        counts_raw = _pair_tuple(
            payload["qaoa_counts"], "qaoa_counts", digest_value=False
        )
        counts = tuple((key, int(value)) for key, value in counts_raw)
        if counts != tuple(sorted(counts)):
            raise ValueError("qaoa_counts must be in canonical bitstring order")
        result = cls(
            schema_version=CORPUS_CASE_DESCRIPTOR_V1_SCHEMA,
            case_id=_string(payload["case_id"], "case_id"),
            family_id=_string(payload["family_id"], "family_id"),
            case_index=_integer(payload["case_index"], "case_index"),
            generation_attempt=_integer(
                payload["generation_attempt"], "generation_attempt"
            ),
            input_count=_integer(payload["input_count"], "input_count", minimum=1),
            output_count=_integer(payload["output_count"], "output_count", minimum=1),
            shared_monomial_blocks=_integer(
                payload["shared_monomial_blocks"], "shared_monomial_blocks", minimum=1
            ),
            semi_affine_blocks=_integer(
                payload["semi_affine_blocks"], "semi_affine_blocks", minimum=1
            ),
            unique_fillers=_integer(
                payload["unique_fillers"], "unique_fillers", minimum=1
            ),
            vector_sha256=_digest(payload["vector_sha256"], "vector_sha256"),
            orbit_cluster_sha256=_digest(
                payload["orbit_cluster_sha256"], "orbit_cluster_sha256"
            ),
            case_sha256=_digest(payload["case_sha256"], "case_sha256"),
            source_candidate_count=_integer(
                payload["source_candidate_count"], "source_candidate_count", minimum=1
            ),
            candidate_cap_effective=_integer(
                payload["candidate_cap_effective"], "candidate_cap_effective", minimum=1
            ),
            scheduler_budget=_integer(
                payload["scheduler_budget"], "scheduler_budget", minimum=1
            ),
            augmented_variable_count=_integer(
                payload["augmented_variable_count"],
                "augmented_variable_count",
                minimum=1,
            ),
            raw_neutral_learned_equals_raw=_boolean(
                payload["raw_neutral_learned_equals_raw"],
                "raw_neutral_learned_equals_raw",
            ),
            group_id=_digest(payload["group_id"], "group_id"),
            split_role=_string(payload["split_role"], "split_role"),
            manifest_sha256=_digest(payload["manifest_sha256"], "manifest_sha256"),
            technical_lock_sha256=_digest(
                payload["technical_lock_sha256"], "technical_lock_sha256"
            ),
            qaoa_execution_class=_string(
                payload["qaoa_execution_class"], "qaoa_execution_class"
            ),
            qaoa_counts_payload_sha256=_digest(
                payload["qaoa_counts_payload_sha256"], "qaoa_counts_payload_sha256"
            ),
            qaoa_final_parameter_payload_sha256=_digest(
                payload["qaoa_final_parameter_payload_sha256"],
                "qaoa_final_parameter_payload_sha256",
            ),
            qaoa_run_attestation_sha256=_digest(
                payload["qaoa_run_attestation_sha256"], "qaoa_run_attestation_sha256"
            ),
            qaoa_gammas=_finite_tuple(payload["qaoa_gammas"], "qaoa_gammas"),
            qaoa_betas=_finite_tuple(payload["qaoa_betas"], "qaoa_betas"),
            qaoa_counts=counts,
            arm_observation_sha256=arm_shas,
            target_sha256_by_arm=target_shas,
            teacher_eligible_arms=arms,
        )
        if (
            result.input_count not in INPUT_COUNTS
            or result.output_count != OUTPUT_COUNT
        ):
            raise ValueError("corpus case shape changed")
        if (
            result.shared_monomial_blocks != SHARED_MONOMIAL_BLOCK_COUNT
            or result.semi_affine_blocks != SEMI_AFFINE_BLOCK_COUNT
            or result.unique_fillers != UNIQUE_FILLER_COUNT
            or result.candidate_cap_effective != CANDIDATE_CAP
            or result.scheduler_budget != SCHEDULER_BUDGET
            or not result.raw_neutral_learned_equals_raw
            or result.qaoa_execution_class != "direct_unrepaired"
            or result.split_role != TRAIN_SPLIT_ROLE
            or result.source_candidate_count < CANDIDATE_CAP
            or result.augmented_variable_count != CANDIDATE_CAP + SCHEDULER_BUDGET
            or len(result.qaoa_gammas) != QAOA_P
            or len(result.qaoa_betas) != QAOA_P
        ):
            raise ValueError("corpus case mechanism contract changed")
        return result


@dataclass(frozen=True)
class ReplayTrainingCorpusDescriptorV1:
    schema_version: str
    generator_id: str
    spec: CorpusBuildSpecV1
    input_counts: tuple[int, ...]
    output_count: int
    candidate_enumeration: str
    candidate_cap: int
    scheduler_budget: int
    qaoa_p: int
    protocol_sha256: str
    source_manifest_sha256: str
    registry_sha256: str
    trainer_corpus_lock_payload_sha256: str
    technical_lock_semantics: str
    case_roster: tuple[CorpusCaseDescriptorV1, ...]
    performance_evidence: bool
    corpus_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generator_id": self.generator_id,
            "spec": self.spec.to_dict(),
            "input_counts": list(self.input_counts),
            "output_count": self.output_count,
            "candidate_enumeration": self.candidate_enumeration,
            "candidate_cap": self.candidate_cap,
            "scheduler_budget": self.scheduler_budget,
            "qaoa_p": self.qaoa_p,
            "protocol_sha256": self.protocol_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "registry_sha256": self.registry_sha256,
            "trainer_corpus_lock_payload_sha256": self.trainer_corpus_lock_payload_sha256,
            "technical_lock_semantics": self.technical_lock_semantics,
            "case_roster": [item.to_dict() for item in self.case_roster],
            "performance_evidence": self.performance_evidence,
            "corpus_sha256": self.corpus_sha256,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "ReplayTrainingCorpusDescriptorV1":
        payload = _native_dict(raw, "corpus descriptor")
        _exact_fields(payload, set(cls.__dataclass_fields__), "corpus descriptor")
        if payload["schema_version"] != CORPUS_DESCRIPTOR_V1_SCHEMA:
            raise ValueError("unsupported corpus descriptor schema")
        result = cls(
            schema_version=CORPUS_DESCRIPTOR_V1_SCHEMA,
            generator_id=_string(payload["generator_id"], "generator_id"),
            spec=CorpusBuildSpecV1.from_dict(payload["spec"]),
            input_counts=tuple(
                _integer(value, f"input_counts[{index}]", minimum=1)
                for index, value in enumerate(
                    _native_list(payload["input_counts"], "input_counts")
                )
            ),
            output_count=_integer(payload["output_count"], "output_count", minimum=1),
            candidate_enumeration=_string(
                payload["candidate_enumeration"], "candidate_enumeration"
            ),
            candidate_cap=_integer(
                payload["candidate_cap"], "candidate_cap", minimum=1
            ),
            scheduler_budget=_integer(
                payload["scheduler_budget"], "scheduler_budget", minimum=1
            ),
            qaoa_p=_integer(payload["qaoa_p"], "qaoa_p", minimum=1),
            protocol_sha256=_digest(payload["protocol_sha256"], "protocol_sha256"),
            source_manifest_sha256=_digest(
                payload["source_manifest_sha256"], "source_manifest_sha256"
            ),
            registry_sha256=_digest(payload["registry_sha256"], "registry_sha256"),
            trainer_corpus_lock_payload_sha256=_digest(
                payload["trainer_corpus_lock_payload_sha256"],
                "trainer_corpus_lock_payload_sha256",
            ),
            technical_lock_semantics=_string(
                payload["technical_lock_semantics"], "technical_lock_semantics"
            ),
            case_roster=tuple(
                CorpusCaseDescriptorV1.from_dict(value)
                for value in _native_list(payload["case_roster"], "case_roster")
            ),
            performance_evidence=_boolean(
                payload["performance_evidence"], "performance_evidence"
            ),
            corpus_sha256=_digest(payload["corpus_sha256"], "corpus_sha256"),
        )
        if (
            result.generator_id != CORPUS_GENERATOR_ID
            or result.input_counts != INPUT_COUNTS
            or result.output_count != OUTPUT_COUNT
            or result.candidate_enumeration
            != "complete_monomial_plus_complete_bounded_semi_affine_deduplicated_by_action_sha"
            or result.candidate_cap != CANDIDATE_CAP
            or result.scheduler_budget != SCHEDULER_BUDGET
            or result.qaoa_p != QAOA_P
            or result.technical_lock_semantics != TECHNICAL_LOCK_SEMANTICS
            or result.performance_evidence
        ):
            raise ValueError("corpus descriptor mechanism contract changed")
        if len(result.case_roster) != len(INPUT_COUNTS) * result.spec.cases_per_width:
            raise ValueError("corpus descriptor case count changed")
        if result.case_roster != tuple(
            sorted(result.case_roster, key=lambda item: item.group_id)
        ):
            raise ValueError(
                "corpus descriptor case roster is not in canonical group order"
            )
        for name, values in (
            ("case_id", [item.case_id for item in result.case_roster]),
            ("family_id", [item.family_id for item in result.case_roster]),
            ("case_index", [item.case_index for item in result.case_roster]),
            ("vector_sha256", [item.vector_sha256 for item in result.case_roster]),
            (
                "orbit_cluster_sha256",
                [item.orbit_cluster_sha256 for item in result.case_roster],
            ),
            ("case_sha256", [item.case_sha256 for item in result.case_roster]),
            ("group_id", [item.group_id for item in result.case_roster]),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"corpus descriptor contains duplicate {name}")
        if set(item.case_index for item in result.case_roster) != set(
            range(len(result.case_roster))
        ):
            raise ValueError("corpus descriptor case indices are not contiguous")
        for width in INPUT_COUNTS:
            if sum(item.input_count == width for item in result.case_roster) != (
                result.spec.cases_per_width
            ):
                raise ValueError("corpus descriptor width allocation changed")
        if any(
            sum(count for _, count in item.qaoa_counts)
            != result.spec.observation_budget
            for item in result.case_roster
        ):
            raise ValueError("corpus descriptor QAOA observation budget changed")
        if result.corpus_sha256 != _descriptor_sha(result):
            raise ValueError("corpus descriptor canonical SHA mismatch")
        return result


@dataclass(frozen=True)
class ReplayTrainingGroupV1:
    material: LockedReplayTrainingGroupV2
    technical_lock: ExternalReplayLockV2
    targets_by_arm: tuple[tuple[str, ReplayTargetsV2], ...]
    qaoa_gammas: tuple[float, ...]
    qaoa_betas: tuple[float, ...]
    generation_attempt: int


@dataclass(frozen=True)
class ReplayTrainingCorpusV1:
    descriptor: ReplayTrainingCorpusDescriptorV1
    registry: SplitRegistryV2
    groups: tuple[ReplayTrainingGroupV1, ...]
    protocol_payload: bytes
    source_manifest_payload: bytes
    corpus_lock_payload: bytes

    @property
    def materials(self) -> tuple[LockedReplayTrainingGroupV2, ...]:
        return tuple(group.material for group in self.groups)

    def to_dict(self) -> dict[str, object]:
        return self.descriptor.to_dict()


@dataclass(frozen=True)
class _PreparedCase:
    family_id: str
    case_index: int
    generation_attempt: int
    case: FrozenSharedCase


def _ranked(
    domain: str, spec: CorpusBuildSpecV1, n: int, attempt: int, values: list[int]
) -> list[int]:
    return sorted(
        values,
        key=lambda value: _sha(
            {
                "schema_version": "xa.e6-sha-ranked-choice.v1",
                "domain": domain,
                "generator_id": CORPUS_GENERATOR_ID,
                "seed": spec.seed,
                "input_count": n,
                "generation_attempt": attempt,
                "value": value,
            }
        ),
    )


def _structured_vector(spec: CorpusBuildSpecV1, n: int, attempt: int) -> VectorANF:
    masks = list(range(1, 1 << n))
    degree_three = [mask for mask in masks if mask.bit_count() == 3]
    shared = _ranked("shared-monomial", spec, n, attempt, degree_three)[:4]

    target_masks = [
        mask for mask in range(1, 1 << OUTPUT_COUNT) if mask.bit_count() == 3
    ]
    ranked_targets = _ranked("shared-target-triple", spec, n, attempt, target_masks)
    outputs: list[set[int]] = [set() for _ in range(OUTPUT_COUNT)]
    for monomial, target_mask in zip(shared, ranked_targets[:4]):
        for output in range(OUTPUT_COUNT):
            if target_mask & (1 << output):
                outputs[output].add(monomial)

    # One authored semi-affine block: base * (x_a xor x_b), shared by three
    # outputs.  Its two expanded monomials are SHA-ranked and kept distinct
    # from the four authored monomial blocks.
    bases = _ranked(
        "semi-affine-base",
        spec,
        n,
        attempt,
        [mask for mask in masks if mask.bit_count() == 2],
    )
    semi_terms: tuple[int, int] | None = None
    for base in bases:
        remaining_bits = [bit for bit in range(n) if not (base & (1 << bit))]
        bit_masks = _ranked(
            f"semi-affine-bits-{base}",
            spec,
            n,
            attempt,
            [1 << bit for bit in remaining_bits],
        )
        if len(bit_masks) < 2:
            continue
        candidate = (base | bit_masks[0], base | bit_masks[1])
        if not set(candidate) & set(shared):
            semi_terms = candidate
            break
    if semi_terms is None:  # pragma: no cover - n=6/7 guarantees choices
        raise RuntimeError("structured generator could not construct semi-affine terms")
    semi_target = _ranked("semi-affine-target-triple", spec, n, attempt, target_masks)[
        0
    ]
    for output in range(OUTPUT_COUNT):
        if semi_target & (1 << output):
            outputs[output].update(semi_terms)

    # One output-unique degree-two filler prevents the corpus from degenerating
    # to a pure repeated-block fixture while introducing no additional
    # monomial fanout candidate.
    fillers = _ranked(
        "unique-filler",
        spec,
        n,
        attempt,
        [mask for mask in masks if mask.bit_count() == 2],
    )
    used = set().union(*outputs)
    cursor = 0
    for output in range(OUTPUT_COUNT):
        while fillers[cursor] in used:
            cursor += 1
        filler = fillers[cursor]
        cursor += 1
        outputs[output].add(filler)
        used.add(filler)
    return VectorANF(n, tuple(frozenset(output) for output in outputs))


def _all_actions(vector: VectorANF) -> tuple[SharedAction, ...]:
    candidates = (
        *enumerate_monomial_shared_actions(vector, min_fanout=2),
        *enumerate_semi_affine_shared_actions(
            vector, min_fanout=2, max_affine_weight=3
        ),
    )
    # Enumeration is complete within the explicitly bounded semi-affine
    # contract.  Deduplication uses the actions' stable JSON representation,
    # not Python object hashes or input order.
    by_sha: dict[str, SharedAction] = {}
    for action in candidates:
        digest = canonical_action_sha256(action)
        if digest in by_sha and by_sha[digest] != action:
            raise RuntimeError("canonical action SHA collision")
        by_sha[digest] = action
    return tuple(by_sha[digest] for digest in sorted(by_sha))


def _derived_seed(spec: CorpusBuildSpecV1, domain: str, n: int, attempt: int) -> int:
    return int(
        _sha(
            {
                "schema_version": "xa.e6-derived-corpus-seed.v1",
                "seed": spec.seed,
                "domain": domain,
                "input_count": n,
                "generation_attempt": attempt,
            }
        )[:15],
        16,
    )


def _freeze_case(spec: CorpusBuildSpecV1, n: int, attempt: int) -> FrozenSharedCase:
    vector = _structured_vector(spec, n, attempt)
    actions = _all_actions(vector)
    if len(actions) < CANDIDATE_CAP:
        raise RuntimeError("structured vector produced fewer than six actions")
    raw = tuple(shared_action_utility(action) for action in actions)
    return build_frozen_shared_case(
        vector,
        actions,
        checkpoint_sha256=FORMAL_V4_CHECKPOINT_SHA256,
        config=SharedSchedulerConfig(
            budget_requested=SCHEDULER_BUDGET,
            qaoa_seed=_derived_seed(spec, "qaoa", n, attempt),
            qaoa_shots=spec.observation_budget,
            qaoa_p=QAOA_P,
            qaoa_optimizer_restarts=spec.qaoa_optimizer_restarts,
            qaoa_optimizer_steps=spec.qaoa_optimizer_steps,
            qaoa_max_variables=12,
            audit_max_variables=12,
        ),
        raw_utilities=raw,
        learned_utilities=raw,
        candidate_cap=CANDIDATE_CAP,
    )


def _protocol_payload(spec: CorpusBuildSpecV1) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": PROTOCOL_SCHEMA,
            "generator_id": CORPUS_GENERATOR_ID,
            "spec": spec.to_dict(),
            "input_counts": list(INPUT_COUNTS),
            "output_count": OUTPUT_COUNT,
            "structured_blocks": {
                "shared_monomial": SHARED_MONOMIAL_BLOCK_COUNT,
                "semi_affine": SEMI_AFFINE_BLOCK_COUNT,
                "unique_filler": UNIQUE_FILLER_COUNT,
            },
            "candidate_enumeration": (
                "complete_monomial_plus_complete_bounded_semi_affine_"
                "deduplicated_by_action_sha"
            ),
            "candidate_cap": CANDIDATE_CAP,
            "scheduler_budget": SCHEDULER_BUDGET,
            "learned_utility": "raw_neutral_equals_raw_utility",
            "source_arms": list(SOURCE_ARMS),
            "split_role": TRAIN_SPLIT_ROLE,
            "technical_lock_semantics": TECHNICAL_LOCK_SEMANTICS,
            "performance_evidence": False,
        }
    )


def _source_manifest_payload(
    prepared: tuple[_PreparedCase, ...], registry: SplitRegistryV2
) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": SOURCE_MANIFEST_SCHEMA,
            "generator_id": CORPUS_GENERATOR_ID,
            "registry_sha256": registry.registry_sha256,
            "cases": [
                {
                    "family_id": item.family_id,
                    "case_index": item.case_index,
                    "generation_attempt": item.generation_attempt,
                    "input_count": item.case.vector.input_count,
                    "vector_sha256": item.case.vector_sha256,
                    "orbit_cluster_sha256": canonical_vector_orbit_sha256(
                        item.case.vector
                    ),
                    "case_sha256": item.case.case_sha256,
                    "source_candidate_count": item.case.source_candidate_count,
                    "candidate_cap_effective": item.case.candidate_cap_effective,
                    "candidate_pool_sha256": item.case.candidate_pool_sha256,
                    "raw_neutral_learned_equals_raw": (
                        item.case.ranked_raw_utilities
                        == item.case.ranked_learned_utilities
                    ),
                }
                for item in prepared
            ],
            "performance_evidence": False,
        }
    )


def _prepare_cases(
    spec: CorpusBuildSpecV1,
) -> tuple[tuple[_PreparedCase, ...], SplitRegistryV2]:
    prepared: list[_PreparedCase] = []
    seen_orbits: set[str] = set()
    case_index = 0
    for n in INPUT_COUNTS:
        accepted = 0
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            case = _freeze_case(spec, n, attempt)
            orbit = canonical_vector_orbit_sha256(case.vector)
            if orbit in seen_orbits:
                continue
            # A direct, unrepaired QAOA observation is an explicit corpus
            # inclusion condition.  This is development training data, not an
            # evaluation endpoint, and the accepted attempt is recorded.
            qaoa = schedule_frozen_case(case, "qaoa")
            if qaoa.diagnostics["qaoa_execution_class"] != "direct_unrepaired":
                continue
            raw_qaoa = qaoa.diagnostics.get("qaoa")
            counts = raw_qaoa.get("counts") if type(raw_qaoa) is dict else None
            if type(counts) is not dict:
                continue
            marginals = [0] * len(case.actions)
            for key, count in counts.items():
                if type(key) is not str or type(count) is not int:
                    continue
                bits = tuple(int(character) for character in key)
                if len(
                    bits
                ) != case.augmented_variable_count or not case.qubo.is_feasible(bits):
                    continue
                for selected in case.qubo.selected_real(bits):
                    marginals[selected] += count
            # Teacher extraction requires real-action mass.  The label-control
            # arm additionally needs a non-uniform marginal vector so at least
            # one deterministic non-identity relabelling changes its policy.
            if sum(marginals) == 0 or len(set(marginals)) <= 1:
                continue
            family_id = (
                f"synthetic/e6-replay-train/n{n}/case-{accepted:04d}-a{attempt:04d}"
            )
            prepared.append(_PreparedCase(family_id, case_index, attempt, case))
            seen_orbits.add(orbit)
            case_index += 1
            accepted += 1
            if accepted == spec.cases_per_width:
                break
        if accepted != spec.cases_per_width:
            raise RuntimeError(
                f"could not generate {spec.cases_per_width} eligible n={n} cases "
                f"within {MAX_GENERATION_ATTEMPTS} attempts"
            )

    registry = build_split_registry_v2(
        tuple(
            SplitRegistrySourceV2(
                family_id=item.family_id,
                vector_or_case=item.case,
                split_role=TRAIN_SPLIT_ROLE,
                origin=ObservationOriginV2(
                    origin_kind="synthetic",
                    origin_id=item.family_id,
                    origin_content_sha256=item.case.vector_sha256,
                    cryptographic_primitive=None,
                    crypto_partition="not_applicable",
                    crypto_holdout_leakage_risk=False,
                ),
            )
            for item in prepared
        )
    )
    return tuple(prepared), registry


def _qaoa_payloads(
    case: FrozenSharedCase,
) -> tuple[
    tuple[tuple[str, int], ...],
    tuple[float, ...],
    tuple[float, ...],
    bytes,
    bytes,
    bytes,
    int,
]:
    result = schedule_frozen_case(case, "qaoa")
    if result.diagnostics["qaoa_execution_class"] != "direct_unrepaired":
        raise RuntimeError(
            "accepted corpus case no longer yields direct-unrepaired QAOA"
        )
    raw_qaoa = result.diagnostics.get("qaoa")
    if type(raw_qaoa) is not dict:
        raise RuntimeError(
            "real QAOA schedule did not expose a native diagnostics payload"
        )
    raw_counts = raw_qaoa.get("counts")
    if type(raw_counts) is not dict or any(
        type(key) is not str or type(value) is not int
        for key, value in raw_counts.items()
    ):
        raise RuntimeError("real QAOA schedule counts payload changed")
    counts = tuple(sorted((str(key), int(value)) for key, value in raw_counts.items()))
    gammas_raw = raw_qaoa.get("gammas")
    betas_raw = raw_qaoa.get("betas")
    if type(gammas_raw) is not list or type(betas_raw) is not list:
        raise RuntimeError("real QAOA schedule final parameters changed shape")
    gammas = tuple(float(value) for value in gammas_raw)
    betas = tuple(float(value) for value in betas_raw)
    if (
        len(gammas) != QAOA_P
        or len(betas) != QAOA_P
        or not all(math.isfinite(value) for value in (*gammas, *betas))
    ):
        raise RuntimeError("real QAOA schedule final parameters are invalid")
    counts_payload = qaoa_counts_payload_bytes_v2(
        case, counts, execution_class="direct_unrepaired"
    )
    final_parameter_payload = canonical_json_bytes(
        {
            "schema_version": FINAL_PARAMETER_SCHEMA,
            "case_sha256": case.case_sha256,
            "p": QAOA_P,
            "gammas": list(gammas),
            "betas": list(betas),
            "optimizer": (
                raw_qaoa["diagnostics"].get("optimizer")
                if type(raw_qaoa.get("diagnostics")) is dict
                else None
            ),
            "optimized_expected_energy": (
                raw_qaoa["diagnostics"].get("optimized_expected_energy")
                if type(raw_qaoa.get("diagnostics")) is dict
                else None
            ),
        }
    )
    diagnostics = raw_qaoa.get("diagnostics")
    if type(diagnostics) is not dict:
        raise RuntimeError("real QAOA schedule backend diagnostics changed shape")
    evaluations = diagnostics.get("optimizer_function_evaluations")
    if type(evaluations) is not int or evaluations < 1:
        raise RuntimeError("real QAOA schedule did not report expectation evaluations")
    run_attestation = canonical_json_bytes(
        {
            "schema_version": RUN_ATTESTATION_SCHEMA,
            "semantics": (
                "deterministic_local_numpy_statevector_run_receipt_not_signature_"
                "not_hardware_not_independent_attestation"
            ),
            "case_sha256": case.case_sha256,
            "counts_payload_sha256": sha256_bytes(counts_payload),
            "final_parameter_payload_sha256": sha256_bytes(final_parameter_payload),
            "scheduler_result": result.to_dict(),
            "performance_evidence": False,
        }
    )
    return (
        counts,
        gammas,
        betas,
        counts_payload,
        final_parameter_payload,
        run_attestation,
        evaluations,
    )


def _technical_lock(
    manifest: object,
    registry: SplitRegistryV2,
    records: tuple[object, ...],
    counts_payload: bytes,
    final_parameter_payload: bytes,
    run_attestation: bytes,
) -> ExternalReplayLockV2:
    qaoa = records[2]
    control = records[3]
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
        "qaoa_final_parameter_payload_sha256": sha256_bytes(final_parameter_payload),
        "qaoa_run_attestation_sha256": sha256_bytes(run_attestation),
    }
    return ExternalReplayLockV2.from_mapping(
        {**unsigned, "lock_sha256": _sha(unsigned)}
    )


def _build_group(
    spec: CorpusBuildSpecV1,
    prepared: _PreparedCase,
    registry: SplitRegistryV2,
    protocol_payload: bytes,
    source_manifest_payload: bytes,
) -> ReplayTrainingGroupV1:
    case = prepared.case
    (
        counts,
        gammas,
        betas,
        counts_payload,
        final_parameters,
        attestation,
        evaluations,
    ) = _qaoa_payloads(case)
    group_nonce = (
        f"e6-replay-training-v1/n{case.vector.input_count}/"
        f"case-{prepared.case_index:04d}/attempt-{prepared.generation_attempt:04d}"
    )
    random_record = None
    random_target = None
    for retry in range(MAX_GENERATION_ATTEMPTS):
        candidate_record = build_classical_random_observation_v2(
            case,
            registry,
            expected_registry_sha256=registry.registry_sha256,
            family_id=prepared.family_id,
            observation_budget=spec.observation_budget,
            group_nonce=group_nonce,
            seed=_derived_seed(
                spec,
                f"random-replay-retry-{retry}",
                case.vector.input_count,
                prepared.generation_attempt,
            ),
        )
        try:
            candidate_target = derive_replay_targets_v2(
                candidate_record,
                case,
                registry,
                expected_observation_sha256=candidate_record.observation_sha256,
                expected_registry_sha256=registry.registry_sha256,
            )
        except ValueError:
            continue
        random_record = candidate_record
        random_target = candidate_target
        break
    if random_record is None or random_target is None:
        raise RuntimeError(
            "could not construct an eligible deterministic random replay arm"
        )
    greedy_record = build_classical_greedy_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=prepared.family_id,
        observation_budget=spec.observation_budget,
        group_nonce=group_nonce,
        seed=_derived_seed(
            spec, "greedy-replay", case.vector.input_count, prepared.generation_attempt
        ),
    )
    qaoa_record = build_qaoa_final_measurement_observation_v2(
        case,
        registry,
        expected_registry_sha256=registry.registry_sha256,
        family_id=prepared.family_id,
        group_nonce=group_nonce,
        counts=counts,
        execution_class="direct_unrepaired",
        final_parameter_payload_sha256=sha256_bytes(final_parameters),
        counts_source_sha256=sha256_bytes(counts_payload),
        source_trust="externally_attested_source",
        source_attestation_sha256=sha256_bytes(attestation),
        compute_budget=ComputeBudgetV2(
            quantum_circuit_executions=evaluations,
            statevector_expectation_evaluations=evaluations,
            classical_candidate_evaluations=0,
            qubo_assignments_audited=1 << case.augmented_variable_count,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=spec.observation_budget,
            declared_wall_seconds=None,
            notes=(
                "deterministic local numpy-statevector QAOA expectation evaluations "
                "plus final shots; compute is not arm-equal"
            ),
        ),
    )
    greedy_target = derive_replay_targets_v2(
        greedy_record,
        case,
        registry,
        expected_observation_sha256=greedy_record.observation_sha256,
        expected_registry_sha256=registry.registry_sha256,
    )
    records = None
    manifest = None
    lock = None
    qaoa_target = None
    control_target = None
    last_control_error: ValueError | None = None
    for retry in range(MAX_GENERATION_ATTEMPTS):
        candidate_control = build_qaoa_permuted_label_control_v2(
            qaoa_record,
            case,
            registry,
            expected_source_observation_sha256=qaoa_record.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            permutation_seed=_derived_seed(
                spec,
                f"qaoa-label-control-retry-{retry}",
                case.vector.input_count,
                prepared.generation_attempt,
            ),
        )
        candidate_records = (
            random_record,
            greedy_record,
            qaoa_record,
            candidate_control,
        )
        candidate_manifest = build_replay_group_manifest_v2(
            candidate_records,
            case,
            registry,
            expected_registry_sha256=registry.registry_sha256,
            protocol_sha256=sha256_bytes(protocol_payload),
            source_manifest_sha256=sha256_bytes(source_manifest_payload),
        )
        candidate_lock = _technical_lock(
            candidate_manifest,
            registry,
            candidate_records,
            counts_payload,
            final_parameters,
            attestation,
        )
        try:
            validate_external_replay_lock_v2(
                candidate_lock,
                candidate_manifest,
                candidate_records,
                case,
                registry,
                expected_lock_sha256=candidate_lock.lock_sha256,
                qaoa_counts_payload=counts_payload,
                final_parameter_payload=final_parameters,
                run_attestation=attestation,
            )
            candidate_qaoa_target = derive_qaoa_replay_targets_from_external_lock_v2(
                qaoa_record,
                candidate_manifest,
                candidate_records,
                case,
                registry,
                expected_observation_sha256=qaoa_record.observation_sha256,
                expected_registry_sha256=registry.registry_sha256,
                lock=candidate_lock,
                expected_lock_sha256=candidate_lock.lock_sha256,
                qaoa_counts_payload=counts_payload,
                final_parameter_payload=final_parameters,
                run_attestation=attestation,
            )
            candidate_control_target = derive_qaoa_replay_targets_from_external_lock_v2(
                candidate_control,
                candidate_manifest,
                candidate_records,
                case,
                registry,
                expected_observation_sha256=candidate_control.observation_sha256,
                expected_registry_sha256=registry.registry_sha256,
                lock=candidate_lock,
                expected_lock_sha256=candidate_lock.lock_sha256,
                qaoa_counts_payload=counts_payload,
                final_parameter_payload=final_parameters,
                run_attestation=attestation,
            )
        except ValueError as exc:
            last_control_error = exc
            continue
        records = candidate_records
        manifest = candidate_manifest
        lock = candidate_lock
        qaoa_target = candidate_qaoa_target
        control_target = candidate_control_target
        break
    if (
        records is None
        or manifest is None
        or lock is None
        or qaoa_target is None
        or control_target is None
    ):
        raise RuntimeError(
            "could not construct eligible QAOA and label-control replay arms; "
            f"last rejection: {last_control_error}"
        )
    targets: list[tuple[str, ReplayTargetsV2]] = [
        (SOURCE_ARMS[0], random_target),
        (SOURCE_ARMS[1], greedy_target),
        (SOURCE_ARMS[2], qaoa_target),
        (SOURCE_ARMS[3], control_target),
    ]
    if tuple(arm for arm, _ in targets) != SOURCE_ARMS:
        raise RuntimeError("four-arm replay target order changed")
    material = LockedReplayTrainingGroupV2(
        case=case,
        records=records,
        manifest=manifest,
        external_lock_payload=canonical_json_bytes(lock.to_dict()),
        qaoa_counts_payload=counts_payload,
        final_parameter_payload=final_parameters,
        run_attestation=attestation,
        protocol_payload=protocol_payload,
        source_manifest_payload=source_manifest_payload,
    )
    return ReplayTrainingGroupV1(
        material=material,
        technical_lock=lock,
        targets_by_arm=tuple(targets),
        qaoa_gammas=gammas,
        qaoa_betas=betas,
        generation_attempt=prepared.generation_attempt,
    )


def _trainer_corpus_lock_payload(
    groups: tuple[ReplayTrainingGroupV1, ...],
    registry: SplitRegistryV2,
    protocol_payload: bytes,
    source_manifest_payload: bytes,
) -> bytes:
    rows = []
    for group in sorted(groups, key=lambda item: item.material.manifest.group_id):
        material = group.material
        rows.append(
            {
                "group_id": material.manifest.group_id,
                "case_sha256": material.case.case_sha256,
                "manifest_sha256": material.manifest.manifest_sha256,
                "external_lock_sha256": group.technical_lock.lock_sha256,
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
        )
    unsigned = {
        "schema_version": ISOLATED_HEAD_TRAINING_CORPUS_LOCK_V2_SCHEMA,
        "authority": CORPUS_LOCK_AUTHORITY,
        "foundation_checkpoint_sha256": FORMAL_V4_CHECKPOINT_SHA256,
        "protocol_sha256": sha256_bytes(protocol_payload),
        "source_manifest_sha256": sha256_bytes(source_manifest_payload),
        "split_registry_sha256": registry.registry_sha256,
        "source_arms": list(SOURCE_ARMS),
        "training_split_role": TRAIN_SPLIT_ROLE,
        "training_input_counts": list(INPUT_COUNTS),
        "origin_kind": "synthetic",
        "groups": rows,
        "performance_evidence": False,
    }
    return canonical_json_bytes({**unsigned, "lock_sha256": _sha(unsigned)})


def _case_descriptor(
    prepared: _PreparedCase, group: ReplayTrainingGroupV1
) -> CorpusCaseDescriptorV1:
    material = group.material
    qaoa = material.records[2]
    return CorpusCaseDescriptorV1(
        schema_version=CORPUS_CASE_DESCRIPTOR_V1_SCHEMA,
        case_id=(
            f"e6-train-n{material.case.vector.input_count}-"
            f"c{prepared.case_index:04d}-a{prepared.generation_attempt:04d}"
        ),
        family_id=prepared.family_id,
        case_index=prepared.case_index,
        generation_attempt=prepared.generation_attempt,
        input_count=material.case.vector.input_count,
        output_count=material.case.vector.output_count,
        shared_monomial_blocks=SHARED_MONOMIAL_BLOCK_COUNT,
        semi_affine_blocks=SEMI_AFFINE_BLOCK_COUNT,
        unique_fillers=UNIQUE_FILLER_COUNT,
        vector_sha256=material.case.vector_sha256,
        orbit_cluster_sha256=canonical_vector_orbit_sha256(material.case.vector),
        case_sha256=material.case.case_sha256,
        source_candidate_count=material.case.source_candidate_count,
        candidate_cap_effective=material.case.candidate_cap_effective,
        scheduler_budget=material.case.scheduler_config.budget_requested,
        augmented_variable_count=material.case.augmented_variable_count,
        raw_neutral_learned_equals_raw=(
            material.case.ranked_raw_utilities == material.case.ranked_learned_utilities
        ),
        group_id=material.manifest.group_id,
        split_role=material.manifest.split_role,
        manifest_sha256=material.manifest.manifest_sha256,
        technical_lock_sha256=group.technical_lock.lock_sha256,
        qaoa_execution_class=qaoa.qaoa_execution_class,
        qaoa_counts_payload_sha256=sha256_bytes(material.qaoa_counts_payload),
        qaoa_final_parameter_payload_sha256=sha256_bytes(
            material.final_parameter_payload
        ),
        qaoa_run_attestation_sha256=sha256_bytes(material.run_attestation),
        qaoa_gammas=group.qaoa_gammas,
        qaoa_betas=group.qaoa_betas,
        qaoa_counts=qaoa.counts,
        arm_observation_sha256=material.manifest.arm_observation_sha256,
        target_sha256_by_arm=tuple(
            (arm, replay_target_sha256_v1(target))
            for arm, target in group.targets_by_arm
        ),
        teacher_eligible_arms=tuple(arm for arm, _ in group.targets_by_arm),
    )


def _descriptor_sha(descriptor: ReplayTrainingCorpusDescriptorV1) -> str:
    payload = descriptor.to_dict()
    payload.pop("corpus_sha256")
    return _sha(payload)


def replay_target_sha256_v1(target: ReplayTargetsV2) -> str:
    """Canonical target identity shared by the corpus, runner and verifier."""

    if type(target) is not ReplayTargetsV2:
        raise TypeError("target must be exact ReplayTargetsV2")
    return _sha(target.to_dict())


def build_replay_training_corpus_v1(
    spec: CorpusBuildSpecV1 = CorpusBuildSpecV1(),
) -> ReplayTrainingCorpusV1:
    """Build ordinary deterministic four-arm replay materials for one runner."""

    if type(spec) is not CorpusBuildSpecV1:
        raise TypeError("spec must be exact CorpusBuildSpecV1")
    prepared, registry = _prepare_cases(spec)
    protocol_payload = _protocol_payload(spec)
    source_manifest_payload = _source_manifest_payload(prepared, registry)
    groups = tuple(
        _build_group(spec, item, registry, protocol_payload, source_manifest_payload)
        for item in prepared
    )
    groups = tuple(sorted(groups, key=lambda item: item.material.manifest.group_id))
    by_case_sha = {item.case.case_sha256: item for item in prepared}
    roster = tuple(
        _case_descriptor(by_case_sha[group.material.case.case_sha256], group)
        for group in groups
    )
    corpus_lock_payload = _trainer_corpus_lock_payload(
        groups, registry, protocol_payload, source_manifest_payload
    )
    provisional = ReplayTrainingCorpusDescriptorV1(
        schema_version=CORPUS_DESCRIPTOR_V1_SCHEMA,
        generator_id=CORPUS_GENERATOR_ID,
        spec=spec,
        input_counts=INPUT_COUNTS,
        output_count=OUTPUT_COUNT,
        candidate_enumeration=(
            "complete_monomial_plus_complete_bounded_semi_affine_"
            "deduplicated_by_action_sha"
        ),
        candidate_cap=CANDIDATE_CAP,
        scheduler_budget=SCHEDULER_BUDGET,
        qaoa_p=QAOA_P,
        protocol_sha256=sha256_bytes(protocol_payload),
        source_manifest_sha256=sha256_bytes(source_manifest_payload),
        registry_sha256=registry.registry_sha256,
        trainer_corpus_lock_payload_sha256=sha256_bytes(corpus_lock_payload),
        technical_lock_semantics=TECHNICAL_LOCK_SEMANTICS,
        case_roster=roster,
        performance_evidence=False,
        corpus_sha256="",
    )
    descriptor = replace(provisional, corpus_sha256=_descriptor_sha(provisional))
    ReplayTrainingCorpusDescriptorV1.from_dict(descriptor.to_dict())
    return ReplayTrainingCorpusV1(
        descriptor=descriptor,
        registry=registry,
        groups=groups,
        protocol_payload=protocol_payload,
        source_manifest_payload=source_manifest_payload,
        corpus_lock_payload=corpus_lock_payload,
    )


def rebuild_replay_training_corpus_v1(raw_descriptor: object) -> ReplayTrainingCorpusV1:
    """Strictly parse a descriptor, rebuild every source, and compare exactly."""

    parsed = ReplayTrainingCorpusDescriptorV1.from_dict(raw_descriptor)
    rebuilt = build_replay_training_corpus_v1(parsed.spec)
    if rebuilt.descriptor != parsed:
        raise ValueError("rebuilt corpus descriptor does not match supplied descriptor")
    return rebuilt


def build_trainer_corpus_lock_payload_v1(corpus: ReplayTrainingCorpusV1) -> bytes:
    """Return and independently recompute the trainer-compatibility payload."""

    if type(corpus) is not ReplayTrainingCorpusV1:
        raise TypeError("corpus must be exact ReplayTrainingCorpusV1")
    rebuilt = _trainer_corpus_lock_payload(
        corpus.groups,
        corpus.registry,
        corpus.protocol_payload,
        corpus.source_manifest_payload,
    )
    if rebuilt != corpus.corpus_lock_payload:
        raise ValueError("corpus trainer-compatibility payload changed")
    if sha256_bytes(rebuilt) != corpus.descriptor.trainer_corpus_lock_payload_sha256:
        raise ValueError("corpus lock payload SHA does not match descriptor")
    return rebuilt


__all__ = [
    "CANDIDATE_CAP",
    "CORPUS_BUILD_SPEC_V1_SCHEMA",
    "CORPUS_CASE_DESCRIPTOR_V1_SCHEMA",
    "CORPUS_DESCRIPTOR_V1_SCHEMA",
    "CORPUS_GENERATOR_ID",
    "INPUT_COUNTS",
    "OUTPUT_COUNT",
    "QAOA_P",
    "SCHEDULER_BUDGET",
    "TECHNICAL_LOCK_SEMANTICS",
    "CorpusBuildSpecV1",
    "CorpusCaseDescriptorV1",
    "ReplayTrainingCorpusDescriptorV1",
    "ReplayTrainingCorpusV1",
    "ReplayTrainingGroupV1",
    "build_replay_training_corpus_v1",
    "build_trainer_corpus_lock_payload_v1",
    "replay_target_sha256_v1",
    "rebuild_replay_training_corpus_v1",
]
