"""Fail-closed final-observation replay contracts for isolated E6-v2 work.

This development-only module separates three things that must not be blurred:

1. an immutable structural ledger for final bitstring-count observations;
2. teacher eligibility and target extraction;
3. an externally anchored four-arm group manifest.

The QAOA arm records only a distribution measured at the final parameter
payload.  It never claims to contain an optimiser trajectory.  Random and
greedy replay use canonical generators implemented below, so their recorded
counts can be recomputed rather than trusted.  A QAOA distribution remains an
unverified development ledger unless an external pre-seal lock binds the group
and the validator re-hashes the actual counts, final-parameter, and run-
attestation bytes.

Nothing here trains a model, runs a formal experiment, writes a bundle, or
changes the active E6-v1.1 synthesis path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from functools import lru_cache
import itertools
import json
import math
import re
from typing import Mapping, Sequence

from e6.frozen_case import (
    FrozenSharedCase,
    canonical_action_sha256,
    canonical_vector_payload,
    schedule_frozen_case,
    validate_frozen_shared_case,
)
from e6.shared_oracle import VectorANF, emit_shared_oracle
from e6.shared_scheduler import program_resource_summary
from src.contracts.codec import canonical_json_bytes, sha256_bytes


FINAL_MEASUREMENT_REPLAY_V2_SCHEMA = (
    "xa.e6-final-measurement-replay-observation.v2-development"
)
SPLIT_REGISTRY_V2_SCHEMA = "xa.e6-split-registry.v2-development"
REPLAY_GROUP_MANIFEST_V2_SCHEMA = "xa.e6-replay-group-manifest.v2-development"
EXTERNAL_REPLAY_LOCK_V2_SCHEMA = "xa.e6-external-replay-lock.v2-development"
EXTERNAL_LOCK_AUTHORITY = "local_preseal_external_lock"
MEASUREMENT_SEMANTICS = (
    "final_post_generator_bitstring_count_distribution_only_not_optimizer_trajectory"
)
COUNT_BIT_ORDER = "x0_to_xK_minus_1_real_actions_then_dummy_slots"
VALUE_TARGET_CONTRACT = (
    "signed_log_program_over_direct_audited_in_minus3_plus3;_"
    "teacher_range_minus3_to0;_harm_is_ineligible"
)
ORBIT_SEMANTICS = (
    "canonical_complete_vector_function_orbit_under_input_and_output_permutations"
)
ORBIT_MAX_INPUT_COUNT = 7
ORBIT_MAX_OUTPUT_COUNT = 8
ORBIT_MAX_TOTAL_TERMS = 512
TRAINER_REPLAY_CONTRACT = (
    "trainer_revalidates_external_lock_manifest_records_and_actual_payload_bytes_"
    "in_same_call;_trainer_accepts_no_prebuilt_python_capability_or_replay_targets;_"
    "trainer_must_not_build_manifest_registry_or_external_lock;_external_roots_must_"
    "be_persisted_before_training"
)
TRAIN_SPLIT_ROLE = "train_replay"
SOURCE_ARMS = (
    "classical_random_bitstring_replay",
    "classical_greedy_repeated_selection_replay",
    "qaoa_final_measurement_replay",
    "qaoa_permuted_label_control",
)
SPLIT_ROLES = (
    TRAIN_SPLIT_ROLE,
    "development_monitor",
    "formal_evaluation",
    "blind_evaluation",
)
QAOA_EXECUTION_CLASSES = (
    "direct_unrepaired",
    "direct_repaired",
    "fallback",
    "not_invoked",
)
QAOA_SOURCE_TRUST_LEVELS = (
    "unverified_development_ledger",
    "externally_attested_source",
)
CLASSICAL_EXECUTION_CLASS = "not_applicable"
GENERATOR_IDS = {
    "classical_random_bitstring_replay": "sha256_counter_uniform_augmented_bits_v2",
    "classical_greedy_repeated_selection_replay": "frozen_case_greedy_repeat_v2",
    "qaoa_final_measurement_replay": "qaoa_final_parameter_counts_capture_v2",
    "qaoa_permuted_label_control": "sha256_ranked_action_label_permutation_v2",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ORIGIN_KINDS = {"synthetic", "cryptographic"}
_CRYPTO_PARTITIONS = {
    "not_applicable",
    "development",
    "evaluation_holdout",
}


def _sha(payload: object) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def _strict_mapping(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{name} must be a native dict")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name} keys must be native strings")
    return value  # type: ignore[return-value]


def _strict_list(value: object, name: str) -> list[object]:
    if type(value) is not list:
        raise TypeError(f"{name} must be a native list")
    return value  # type: ignore[return-value]


def _strict_str(value: object, name: str, *, nonempty: bool = True) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a native string")
    if nonempty and not value:
        raise ValueError(f"{name} must be non-empty")
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} must not contain outer whitespace/control characters")
    return value


def _strict_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a native bool")
    return value


def _strict_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _strict_float(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
) -> float:
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a native finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def _require_sha256(value: object, name: str) -> str:
    text = _strict_str(value, name)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return text


def _optional_sha256(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_sha256(value, name)


def _exact_fields(payload: Mapping[str, object], expected: set[str], name: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"{name} field contract changed: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


@dataclass(frozen=True)
class ComputeBudgetV2:
    """Structured accounting; equality across arms is explicitly not claimed."""

    quantum_circuit_executions: int
    statevector_expectation_evaluations: int
    classical_candidate_evaluations: int
    qubo_assignments_audited: int
    greedy_candidate_scans_upper_bound: int
    bitstrings_generated: int
    declared_wall_seconds: float | None
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: object) -> "ComputeBudgetV2":
        payload = _strict_mapping(raw, "compute_budget")
        _exact_fields(payload, set(cls.__dataclass_fields__), "compute_budget")
        wall = payload["declared_wall_seconds"]
        return cls(
            quantum_circuit_executions=_strict_int(
                payload["quantum_circuit_executions"],
                "compute_budget.quantum_circuit_executions",
                minimum=0,
            ),
            statevector_expectation_evaluations=_strict_int(
                payload["statevector_expectation_evaluations"],
                "compute_budget.statevector_expectation_evaluations",
                minimum=0,
            ),
            classical_candidate_evaluations=_strict_int(
                payload["classical_candidate_evaluations"],
                "compute_budget.classical_candidate_evaluations",
                minimum=0,
            ),
            qubo_assignments_audited=_strict_int(
                payload["qubo_assignments_audited"],
                "compute_budget.qubo_assignments_audited",
                minimum=0,
            ),
            greedy_candidate_scans_upper_bound=_strict_int(
                payload["greedy_candidate_scans_upper_bound"],
                "compute_budget.greedy_candidate_scans_upper_bound",
                minimum=0,
            ),
            bitstrings_generated=_strict_int(
                payload["bitstrings_generated"],
                "compute_budget.bitstrings_generated",
                minimum=0,
            ),
            declared_wall_seconds=(
                None
                if wall is None
                else _strict_float(
                    wall, "compute_budget.declared_wall_seconds", minimum=0.0
                )
            ),
            notes=_strict_str(payload["notes"], "compute_budget.notes"),
        )


def _validate_compute_budget(value: ComputeBudgetV2) -> None:
    if not isinstance(value, ComputeBudgetV2):
        raise TypeError("compute_budget must be a ComputeBudgetV2")
    ComputeBudgetV2.from_dict(value.to_dict())


@dataclass(frozen=True)
class ObservationOriginV2:
    origin_kind: str
    origin_id: str
    origin_content_sha256: str
    cryptographic_primitive: str | None
    crypto_partition: str
    crypto_holdout_leakage_risk: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: object) -> "ObservationOriginV2":
        payload = _strict_mapping(raw, "origin")
        _exact_fields(payload, set(cls.__dataclass_fields__), "origin")
        primitive = payload["cryptographic_primitive"]
        return cls(
            origin_kind=_strict_str(payload["origin_kind"], "origin.origin_kind"),
            origin_id=_strict_str(payload["origin_id"], "origin.origin_id"),
            origin_content_sha256=_require_sha256(
                payload["origin_content_sha256"], "origin.origin_content_sha256"
            ),
            cryptographic_primitive=(
                None
                if primitive is None
                else _strict_str(
                    primitive, "origin.cryptographic_primitive"
                )
            ),
            crypto_partition=_strict_str(
                payload["crypto_partition"], "origin.crypto_partition"
            ),
            crypto_holdout_leakage_risk=_strict_bool(
                payload["crypto_holdout_leakage_risk"],
                "origin.crypto_holdout_leakage_risk",
            ),
        )


def _validate_origin(origin: ObservationOriginV2) -> None:
    if not isinstance(origin, ObservationOriginV2):
        raise TypeError("origin must be an ObservationOriginV2")
    parsed = ObservationOriginV2.from_dict(origin.to_dict())
    if parsed.origin_kind not in _ORIGIN_KINDS:
        raise ValueError(f"unregistered origin_kind: {parsed.origin_kind!r}")
    if parsed.crypto_partition not in _CRYPTO_PARTITIONS:
        raise ValueError(f"unregistered crypto_partition: {parsed.crypto_partition!r}")
    if parsed.origin_kind == "synthetic":
        if parsed.cryptographic_primitive is not None:
            raise ValueError("synthetic origins cannot name a cryptographic primitive")
        if parsed.crypto_partition != "not_applicable":
            raise ValueError("synthetic origins require crypto_partition=not_applicable")
        expected_leakage = False
    else:
        if parsed.cryptographic_primitive is None:
            raise ValueError("cryptographic origins require a primitive name")
        if parsed.crypto_partition == "not_applicable":
            raise ValueError("cryptographic origins require an explicit partition")
        expected_leakage = parsed.crypto_partition == "evaluation_holdout"
    if parsed.crypto_holdout_leakage_risk is not expected_leakage:
        raise ValueError(
            "crypto_holdout_leakage_risk must be derived from the origin partition"
        )


def _permute_monomial(mask: int, old_to_new: tuple[int, ...]) -> int:
    result = 0
    for old, new in enumerate(old_to_new):
        if mask & (1 << old):
            result |= 1 << new
    return result


@lru_cache(maxsize=512)
def canonical_vector_orbit_sha256(vector: VectorANF) -> str:
    """Canonicalise the full vector under input and output permutations.

    Output permutations are removed by sorting complete transformed output
    polynomials; only ``n!`` input permutations are enumerated.  This
    development schema fails closed above its explicit computational envelope;
    it never accepts an opaque precomputed orbit digest.
    """

    if not isinstance(vector, VectorANF):
        raise TypeError("vector must be a VectorANF")
    total_terms = sum(len(output) for output in vector.outputs)
    if vector.input_count > ORBIT_MAX_INPUT_COUNT:
        raise ValueError(
            f"orbit canonicalisation refuses input_count>{ORBIT_MAX_INPUT_COUNT}"
        )
    if vector.output_count > ORBIT_MAX_OUTPUT_COUNT:
        raise ValueError(
            f"orbit canonicalisation refuses output_count>{ORBIT_MAX_OUTPUT_COUNT}"
        )
    if total_terms > ORBIT_MAX_TOTAL_TERMS:
        raise ValueError(
            f"orbit canonicalisation refuses total_terms>{ORBIT_MAX_TOTAL_TERMS}"
        )

    canonical: tuple[tuple[int, ...], ...] | None = None
    for permutation in itertools.permutations(range(vector.input_count)):
        transformed = tuple(
            sorted(
                tuple(sorted(_permute_monomial(term, permutation) for term in output))
                for output in vector.outputs
            )
        )
        if canonical is None or transformed < canonical:
            canonical = transformed
    assert canonical is not None
    return _sha(
        {
            "schema_version": "xa.e6-vector-orbit.v2",
            "semantics": ORBIT_SEMANTICS,
            "input_count": vector.input_count,
            "output_count": vector.output_count,
            "canonical_outputs": [list(output) for output in canonical],
        }
    )


def whole_vector_cluster_id(vector_or_case: VectorANF | FrozenSharedCase) -> str:
    """Coordinate-preserving complete-vector identity, distinct from orbit ID."""

    vector = vector_or_case.vector if isinstance(vector_or_case, FrozenSharedCase) else vector_or_case
    if not isinstance(vector, VectorANF):
        raise TypeError("vector_or_case must contain a VectorANF")
    return _sha(
        {
            "schema_version": "xa.e6-whole-vector-cluster.v2",
            "cluster_unit": "complete_vector_boolean_function_all_outputs",
            "vector": canonical_vector_payload(vector),
        }
    )


@dataclass(frozen=True)
class SplitRegistrySourceV2:
    """In-memory registration request carrying the actual vector/case object."""

    family_id: str
    vector_or_case: VectorANF | FrozenSharedCase
    split_role: str
    origin: ObservationOriginV2


@dataclass(frozen=True)
class SplitRegistryEntryV2:
    family_id: str
    orbit_cluster_sha256: str
    vector_sha256: str
    split_role: str
    origin: ObservationOriginV2

    def to_dict(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "orbit_cluster_sha256": self.orbit_cluster_sha256,
            "vector_sha256": self.vector_sha256,
            "split_role": self.split_role,
            "origin": self.origin.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: object) -> "SplitRegistryEntryV2":
        payload = _strict_mapping(raw, "split_registry.entry")
        _exact_fields(payload, set(cls.__dataclass_fields__), "split_registry.entry")
        return cls(
            family_id=_strict_str(payload["family_id"], "entry.family_id"),
            orbit_cluster_sha256=_require_sha256(
                payload["orbit_cluster_sha256"], "entry.orbit_cluster_sha256"
            ),
            vector_sha256=_require_sha256(
                payload["vector_sha256"], "entry.vector_sha256"
            ),
            split_role=_strict_str(payload["split_role"], "entry.split_role"),
            origin=ObservationOriginV2.from_dict(payload["origin"]),
        )


@dataclass(frozen=True)
class SplitRegistryV2:
    schema_version: str
    orbit_semantics: str
    entries: tuple[SplitRegistryEntryV2, ...]
    registry_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "orbit_semantics": self.orbit_semantics,
            "entries": [entry.to_dict() for entry in self.entries],
            "registry_sha256": self.registry_sha256,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "SplitRegistryV2":
        payload = _strict_mapping(raw, "split_registry")
        _exact_fields(payload, set(cls.__dataclass_fields__), "split_registry")
        return cls(
            schema_version=_strict_str(
                payload["schema_version"], "split_registry.schema_version"
            ),
            orbit_semantics=_strict_str(
                payload["orbit_semantics"], "split_registry.orbit_semantics"
            ),
            entries=tuple(
                SplitRegistryEntryV2.from_dict(item)
                for item in _strict_list(payload["entries"], "split_registry.entries")
            ),
            registry_sha256=_require_sha256(
                payload["registry_sha256"], "split_registry.registry_sha256"
            ),
        )


def _split_registry_payload(registry: SplitRegistryV2) -> dict[str, object]:
    return {
        "schema_version": registry.schema_version,
        "orbit_semantics": registry.orbit_semantics,
        "entries": [entry.to_dict() for entry in registry.entries],
    }


def _validate_registry_entry(entry: SplitRegistryEntryV2) -> None:
    parsed = SplitRegistryEntryV2.from_dict(entry.to_dict())
    if parsed.split_role not in SPLIT_ROLES:
        raise ValueError(f"unregistered split_role: {parsed.split_role!r}")
    _validate_origin(parsed.origin)


def build_split_registry_v2(
    sources: Sequence[SplitRegistrySourceV2],
) -> SplitRegistryV2:
    """Build from actual vectors/cases; bare caller-provided hashes are rejected."""

    entries: list[SplitRegistryEntryV2] = []
    for index, source in enumerate(tuple(sources)):
        if not isinstance(source, SplitRegistrySourceV2):
            raise TypeError(
                f"sources[{index}] must be a SplitRegistrySourceV2 carrying an actual vector/case"
            )
        family = _strict_str(source.family_id, f"sources[{index}].family_id")
        if isinstance(source.vector_or_case, FrozenSharedCase):
            validate_frozen_shared_case(source.vector_or_case)
            vector = source.vector_or_case.vector
            vector_sha = source.vector_or_case.vector_sha256
        elif isinstance(source.vector_or_case, VectorANF):
            vector = source.vector_or_case
            vector_sha = _sha(canonical_vector_payload(vector))
        else:
            raise TypeError(
                f"sources[{index}].vector_or_case must be a FrozenSharedCase or VectorANF"
            )
        split = _strict_str(source.split_role, f"sources[{index}].split_role")
        if split not in SPLIT_ROLES:
            raise ValueError(f"unregistered split_role: {split!r}")
        _validate_origin(source.origin)
        entries.append(
            SplitRegistryEntryV2(
                family_id=family,
                orbit_cluster_sha256=canonical_vector_orbit_sha256(vector),
                vector_sha256=vector_sha,
                split_role=split,
                origin=source.origin,
            )
        )
    canonical = tuple(
        sorted(entries, key=lambda item: (item.family_id, item.orbit_cluster_sha256))
    )
    provisional = SplitRegistryV2(
        schema_version=SPLIT_REGISTRY_V2_SCHEMA,
        orbit_semantics=ORBIT_SEMANTICS,
        entries=canonical,
        registry_sha256="",
    )
    registry = replace(
        provisional, registry_sha256=_sha(_split_registry_payload(provisional))
    )
    validate_split_registry_v2(
        registry, expected_registry_sha256=registry.registry_sha256
    )
    return registry


def validate_split_registry_v2(
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
) -> None:
    if not isinstance(registry, SplitRegistryV2):
        raise TypeError("registry must be a SplitRegistryV2")
    external = _require_sha256(
        expected_registry_sha256, "expected_registry_sha256"
    )
    if registry.schema_version != SPLIT_REGISTRY_V2_SCHEMA:
        raise ValueError("unsupported split registry schema")
    if registry.orbit_semantics != ORBIT_SEMANTICS:
        raise ValueError("split registry orbit semantics changed")
    if not registry.entries:
        raise ValueError("split registry must contain at least one entry")
    for entry in registry.entries:
        _validate_registry_entry(entry)
    if registry.entries != tuple(
        sorted(registry.entries, key=lambda item: (item.family_id, item.orbit_cluster_sha256))
    ):
        raise ValueError("split registry entries are not in canonical order")
    families = [entry.family_id for entry in registry.entries]
    orbits = [entry.orbit_cluster_sha256 for entry in registry.entries]
    vectors = [entry.vector_sha256 for entry in registry.entries]
    if len(set(families)) != len(families):
        raise ValueError("each family_id must be registered exactly once")
    if len(set(orbits)) != len(orbits):
        raise ValueError("an orbit cluster cannot be registered across multiple splits")
    if len(set(vectors)) != len(vectors):
        raise ValueError("the same vector cannot be registered across multiple splits")
    expected = _sha(_split_registry_payload(registry))
    if registry.registry_sha256 != expected:
        raise ValueError("split registry canonical SHA mismatch")
    if registry.registry_sha256 != external:
        raise ValueError("split registry SHA does not match the external anchor")


def _lookup_registry_entry(
    registry: SplitRegistryV2,
    *,
    family_id: str,
    orbit_cluster_sha256: str,
) -> SplitRegistryEntryV2:
    matches = tuple(
        entry
        for entry in registry.entries
        if entry.family_id == family_id
        and entry.orbit_cluster_sha256 == orbit_cluster_sha256
    )
    if len(matches) != 1:
        raise ValueError("family/orbit pair is not uniquely registered")
    return matches[0]


@dataclass(frozen=True)
class GeneratorContractV2:
    generator_id: str
    algorithm_version: str
    seed: int
    deterministic_given_seed: bool
    final_distribution_only: bool
    optimizer_trajectory_included: bool
    source_payload_sha256: str
    compute_budget: ComputeBudgetV2

    def to_dict(self) -> dict[str, object]:
        return {
            "generator_id": self.generator_id,
            "algorithm_version": self.algorithm_version,
            "seed": self.seed,
            "deterministic_given_seed": self.deterministic_given_seed,
            "final_distribution_only": self.final_distribution_only,
            "optimizer_trajectory_included": self.optimizer_trajectory_included,
            "source_payload_sha256": self.source_payload_sha256,
            "compute_budget": self.compute_budget.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: object) -> "GeneratorContractV2":
        payload = _strict_mapping(raw, "generator_contract")
        _exact_fields(payload, set(cls.__dataclass_fields__), "generator_contract")
        return cls(
            generator_id=_strict_str(
                payload["generator_id"], "generator_contract.generator_id"
            ),
            algorithm_version=_strict_str(
                payload["algorithm_version"], "generator_contract.algorithm_version"
            ),
            seed=_strict_int(
                payload["seed"], "generator_contract.seed", minimum=0
            ),
            deterministic_given_seed=_strict_bool(
                payload["deterministic_given_seed"],
                "generator_contract.deterministic_given_seed",
            ),
            final_distribution_only=_strict_bool(
                payload["final_distribution_only"],
                "generator_contract.final_distribution_only",
            ),
            optimizer_trajectory_included=_strict_bool(
                payload["optimizer_trajectory_included"],
                "generator_contract.optimizer_trajectory_included",
            ),
            source_payload_sha256=_require_sha256(
                payload["source_payload_sha256"],
                "generator_contract.source_payload_sha256",
            ),
            compute_budget=ComputeBudgetV2.from_dict(payload["compute_budget"]),
        )


@dataclass(frozen=True)
class QAOAFinalMeasurementContractV2:
    scheduler_seed: int
    shots: int
    p: int
    optimizer_restarts: int
    optimizer_steps: int
    final_parameter_payload_sha256: str | None
    counts_source_sha256: str
    source_trust: str
    source_attestation_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: object) -> "QAOAFinalMeasurementContractV2":
        payload = _strict_mapping(raw, "qaoa_contract")
        _exact_fields(payload, set(cls.__dataclass_fields__), "qaoa_contract")
        return cls(
            scheduler_seed=_strict_int(
                payload["scheduler_seed"], "qaoa_contract.scheduler_seed", minimum=0
            ),
            shots=_strict_int(payload["shots"], "qaoa_contract.shots", minimum=1),
            p=_strict_int(payload["p"], "qaoa_contract.p", minimum=1),
            optimizer_restarts=_strict_int(
                payload["optimizer_restarts"],
                "qaoa_contract.optimizer_restarts",
                minimum=1,
            ),
            optimizer_steps=_strict_int(
                payload["optimizer_steps"],
                "qaoa_contract.optimizer_steps",
                minimum=0,
            ),
            final_parameter_payload_sha256=_optional_sha256(
                payload["final_parameter_payload_sha256"],
                "qaoa_contract.final_parameter_payload_sha256",
            ),
            counts_source_sha256=_require_sha256(
                payload["counts_source_sha256"],
                "qaoa_contract.counts_source_sha256",
            ),
            source_trust=_strict_str(
                payload["source_trust"], "qaoa_contract.source_trust"
            ),
            source_attestation_sha256=_optional_sha256(
                payload["source_attestation_sha256"],
                "qaoa_contract.source_attestation_sha256",
            ),
        )


def _validate_generator_contract(
    contract: GeneratorContractV2, source_arm: str
) -> None:
    if not isinstance(contract, GeneratorContractV2):
        raise TypeError("generator_contract must be a GeneratorContractV2")
    parsed = GeneratorContractV2.from_dict(contract.to_dict())
    if parsed.generator_id != GENERATOR_IDS[source_arm]:
        raise ValueError("generator_id does not match source_arm")
    if parsed.algorithm_version != "v2":
        raise ValueError("generator algorithm_version must be v2")
    if parsed.deterministic_given_seed is not True:
        raise ValueError("replay generators must be deterministic given seed")
    if parsed.final_distribution_only is not True:
        raise ValueError("only final distributions may enter replay")
    if parsed.optimizer_trajectory_included is not False:
        raise ValueError("optimizer trajectories are forbidden")
    _validate_compute_budget(parsed.compute_budget)


@dataclass(frozen=True)
class FinalMeasurementObservationV2:
    schema_version: str
    source_arm: str
    measurement_semantics: str
    count_bit_order: str
    value_target_contract: str
    case_sha256: str
    vector_sha256: str
    candidate_pool_sha256: str
    qubo_sha256: str
    action_signatures: tuple[str, ...]
    whole_vector_cluster_id: str
    family_id: str
    orbit_cluster_sha256: str
    split_registry_sha256: str
    group_nonce: str
    group_id: str
    split_role: str
    origin: ObservationOriginV2
    observation_budget: int
    counts: tuple[tuple[str, int], ...]
    generator_contract: GeneratorContractV2
    qaoa_contract: QAOAFinalMeasurementContractV2 | None
    qaoa_execution_class: str
    parent_qaoa_observation_sha256: str | None
    label_permutation_new_index_to_source_index: tuple[int, ...]
    compute_budget_equal: bool
    performance_evidence: bool
    distribution_sha256: str
    observation_sha256: str

    @property
    def counts_dict(self) -> dict[str, int]:
        return dict(self.counts)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_arm": self.source_arm,
            "measurement_semantics": self.measurement_semantics,
            "count_bit_order": self.count_bit_order,
            "value_target_contract": self.value_target_contract,
            "case_sha256": self.case_sha256,
            "vector_sha256": self.vector_sha256,
            "candidate_pool_sha256": self.candidate_pool_sha256,
            "qubo_sha256": self.qubo_sha256,
            "action_signatures": list(self.action_signatures),
            "whole_vector_cluster_id": self.whole_vector_cluster_id,
            "family_id": self.family_id,
            "orbit_cluster_sha256": self.orbit_cluster_sha256,
            "split_registry_sha256": self.split_registry_sha256,
            "group_nonce": self.group_nonce,
            "group_id": self.group_id,
            "split_role": self.split_role,
            "origin": self.origin.to_dict(),
            "observation_budget": self.observation_budget,
            "counts": [
                {"bitstring": key, "count": count} for key, count in self.counts
            ],
            "generator_contract": self.generator_contract.to_dict(),
            "qaoa_contract": (
                None if self.qaoa_contract is None else self.qaoa_contract.to_dict()
            ),
            "qaoa_execution_class": self.qaoa_execution_class,
            "parent_qaoa_observation_sha256": self.parent_qaoa_observation_sha256,
            "label_permutation_new_index_to_source_index": list(
                self.label_permutation_new_index_to_source_index
            ),
            "compute_budget_equal": self.compute_budget_equal,
            "performance_evidence": self.performance_evidence,
            "distribution_sha256": self.distribution_sha256,
            "observation_sha256": self.observation_sha256,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "FinalMeasurementObservationV2":
        payload = _strict_mapping(raw, "observation")
        _exact_fields(payload, set(cls.__dataclass_fields__), "observation")
        signatures = tuple(
            _require_sha256(item, f"action_signatures[{index}]")
            for index, item in enumerate(
                _strict_list(payload["action_signatures"], "action_signatures")
            )
        )
        counts: list[tuple[str, int]] = []
        for index, raw_entry in enumerate(
            _strict_list(payload["counts"], "counts")
        ):
            entry = _strict_mapping(raw_entry, f"counts[{index}]")
            _exact_fields(entry, {"bitstring", "count"}, f"counts[{index}]")
            counts.append(
                (
                    _strict_str(
                        entry["bitstring"],
                        f"counts[{index}].bitstring",
                        nonempty=False,
                    ),
                    _strict_int(
                        entry["count"], f"counts[{index}].count", minimum=1
                    ),
                )
            )
        permutation = tuple(
            _strict_int(item, f"label_permutation[{index}]", minimum=0)
            for index, item in enumerate(
                _strict_list(
                    payload["label_permutation_new_index_to_source_index"],
                    "label_permutation",
                )
            )
        )
        raw_qaoa = payload["qaoa_contract"]
        return cls(
            schema_version=_strict_str(payload["schema_version"], "schema_version"),
            source_arm=_strict_str(payload["source_arm"], "source_arm"),
            measurement_semantics=_strict_str(
                payload["measurement_semantics"], "measurement_semantics"
            ),
            count_bit_order=_strict_str(payload["count_bit_order"], "count_bit_order"),
            value_target_contract=_strict_str(
                payload["value_target_contract"], "value_target_contract"
            ),
            case_sha256=_require_sha256(payload["case_sha256"], "case_sha256"),
            vector_sha256=_require_sha256(payload["vector_sha256"], "vector_sha256"),
            candidate_pool_sha256=_require_sha256(
                payload["candidate_pool_sha256"], "candidate_pool_sha256"
            ),
            qubo_sha256=_require_sha256(payload["qubo_sha256"], "qubo_sha256"),
            action_signatures=signatures,
            whole_vector_cluster_id=_require_sha256(
                payload["whole_vector_cluster_id"], "whole_vector_cluster_id"
            ),
            family_id=_strict_str(payload["family_id"], "family_id"),
            orbit_cluster_sha256=_require_sha256(
                payload["orbit_cluster_sha256"], "orbit_cluster_sha256"
            ),
            split_registry_sha256=_require_sha256(
                payload["split_registry_sha256"], "split_registry_sha256"
            ),
            group_nonce=_strict_str(payload["group_nonce"], "group_nonce"),
            group_id=_require_sha256(payload["group_id"], "group_id"),
            split_role=_strict_str(payload["split_role"], "split_role"),
            origin=ObservationOriginV2.from_dict(payload["origin"]),
            observation_budget=_strict_int(
                payload["observation_budget"], "observation_budget", minimum=1
            ),
            counts=tuple(counts),
            generator_contract=GeneratorContractV2.from_dict(
                payload["generator_contract"]
            ),
            qaoa_contract=(
                None
                if raw_qaoa is None
                else QAOAFinalMeasurementContractV2.from_dict(raw_qaoa)
            ),
            qaoa_execution_class=_strict_str(
                payload["qaoa_execution_class"], "qaoa_execution_class"
            ),
            parent_qaoa_observation_sha256=_optional_sha256(
                payload["parent_qaoa_observation_sha256"],
                "parent_qaoa_observation_sha256",
            ),
            label_permutation_new_index_to_source_index=permutation,
            compute_budget_equal=_strict_bool(
                payload["compute_budget_equal"], "compute_budget_equal"
            ),
            performance_evidence=_strict_bool(
                payload["performance_evidence"], "performance_evidence"
            ),
            distribution_sha256=_require_sha256(
                payload["distribution_sha256"], "distribution_sha256"
            ),
            observation_sha256=_require_sha256(
                payload["observation_sha256"], "observation_sha256"
            ),
        )


@dataclass(frozen=True)
class BitstringAuditV2:
    bitstring: tuple[int, ...]
    count: int
    cardinality: int
    source_selected_real_indices: tuple[int, ...]
    label_aligned_selected_real_indices: tuple[int, ...]
    dummy_selected: int
    conflict_count: int
    feasible: bool
    phase_energy: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SignedValueAuditV2:
    feasible_expected_program_score: float
    direct_program_score: float
    score_ratio: float | None
    raw_signed_log_ratio: float | None
    signed_log_ratio_for_audit: float
    direction: str
    worse_than_direct: bool
    value_target_log_ratio: float
    target_minimum: float = -3.0
    target_maximum: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayLedgerAuditV2:
    observation_sha256: str
    source_arm: str
    structural_valid: bool
    action_signatures: tuple[str, ...]
    bitstring_audit: tuple[BitstringAuditV2, ...]
    total_observed: int
    declared_observation_budget: int
    observation_budget_complete: bool
    feasible_observed: int
    infeasible_observed: int
    feasible_fraction: float
    source_marginal_action_counts: tuple[int, ...]
    label_aligned_marginal_action_counts: tuple[int, ...]
    source_policy_target: tuple[float, ...]
    label_aligned_policy_target: tuple[float, ...]
    policy_observation_weight: float
    value_audit: SignedValueAuditV2
    whole_vector_cluster_id: str
    source_trusted: bool
    parent_validated: bool
    teacher_eligible: bool
    ineligibility_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "bitstring_audit": [item.to_dict() for item in self.bitstring_audit],
            "value_audit": self.value_audit.to_dict(),
        }


@dataclass(frozen=True)
class ReplayTargetsV2:
    observation_sha256: str
    source_arm: str
    action_signatures: tuple[str, ...]
    policy_target: tuple[float, ...]
    policy_observation_weight: float
    feasible_fraction: float
    value_observation_weight: float
    value_loss_weight_contract: str
    value_target_log_ratio: float
    value_audit: SignedValueAuditV2
    whole_vector_cluster_id: str
    trainer_replay_contract: str = TRAINER_REPLAY_CONTRACT

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "value_audit": self.value_audit.to_dict(),
        }


@dataclass(frozen=True)
class ReplayGroupManifestV2:
    schema_version: str
    group_id: str
    protocol_sha256: str
    source_manifest_sha256: str
    split_registry_sha256: str
    case_sha256: str
    candidate_pool_sha256: str
    family_id: str
    orbit_cluster_sha256: str
    split_role: str
    arm_observation_sha256: tuple[tuple[str, str], ...]
    parent_bindings: tuple[tuple[str, str, str], ...]
    generator_configuration_sha256: tuple[tuple[str, str], ...]
    source_payload_sha256: tuple[tuple[str, str], ...]
    manifest_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "group_id": self.group_id,
            "protocol_sha256": self.protocol_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "split_registry_sha256": self.split_registry_sha256,
            "case_sha256": self.case_sha256,
            "candidate_pool_sha256": self.candidate_pool_sha256,
            "family_id": self.family_id,
            "orbit_cluster_sha256": self.orbit_cluster_sha256,
            "split_role": self.split_role,
            "arm_observation_sha256": [list(item) for item in self.arm_observation_sha256],
            "parent_bindings": [list(item) for item in self.parent_bindings],
            "generator_configuration_sha256": [
                list(item) for item in self.generator_configuration_sha256
            ],
            "source_payload_sha256": [
                list(item) for item in self.source_payload_sha256
            ],
            "manifest_sha256": self.manifest_sha256,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "ReplayGroupManifestV2":
        payload = _strict_mapping(raw, "group_manifest")
        _exact_fields(payload, set(cls.__dataclass_fields__), "group_manifest")

        def pairs(field: str, width: int) -> tuple[tuple[str, ...], ...]:
            rows: list[tuple[str, ...]] = []
            for index, raw_row in enumerate(
                _strict_list(payload[field], f"group_manifest.{field}")
            ):
                row = _strict_list(raw_row, f"group_manifest.{field}[{index}]")
                if len(row) != width:
                    raise ValueError(f"group_manifest.{field}[{index}] width changed")
                rows.append(
                    tuple(
                        _strict_str(value, f"group_manifest.{field}[{index}][{offset}]")
                        for offset, value in enumerate(row)
                    )
                )
            return tuple(rows)

        arm_rows = pairs("arm_observation_sha256", 2)
        parent_rows = pairs("parent_bindings", 3)
        generator_rows = pairs("generator_configuration_sha256", 2)
        source_rows = pairs("source_payload_sha256", 2)
        for field, rows in (
            ("arm_observation_sha256", arm_rows),
            ("generator_configuration_sha256", generator_rows),
            ("source_payload_sha256", source_rows),
        ):
            for arm, digest in rows:
                _require_sha256(digest, f"group_manifest.{field}[{arm}]")
        for child, parent, digest in parent_rows:
            _strict_str(child, "parent child arm")
            _strict_str(parent, "parent source arm")
            _require_sha256(digest, "parent observation SHA")
        return cls(
            schema_version=_strict_str(payload["schema_version"], "manifest.schema_version"),
            group_id=_require_sha256(payload["group_id"], "manifest.group_id"),
            protocol_sha256=_require_sha256(
                payload["protocol_sha256"], "manifest.protocol_sha256"
            ),
            source_manifest_sha256=_require_sha256(
                payload["source_manifest_sha256"], "manifest.source_manifest_sha256"
            ),
            split_registry_sha256=_require_sha256(
                payload["split_registry_sha256"], "manifest.split_registry_sha256"
            ),
            case_sha256=_require_sha256(payload["case_sha256"], "manifest.case_sha256"),
            candidate_pool_sha256=_require_sha256(
                payload["candidate_pool_sha256"], "manifest.candidate_pool_sha256"
            ),
            family_id=_strict_str(payload["family_id"], "manifest.family_id"),
            orbit_cluster_sha256=_require_sha256(
                payload["orbit_cluster_sha256"], "manifest.orbit_cluster_sha256"
            ),
            split_role=_strict_str(payload["split_role"], "manifest.split_role"),
            arm_observation_sha256=arm_rows,  # type: ignore[arg-type]
            parent_bindings=parent_rows,  # type: ignore[arg-type]
            generator_configuration_sha256=generator_rows,  # type: ignore[arg-type]
            source_payload_sha256=source_rows,  # type: ignore[arg-type]
            manifest_sha256=_require_sha256(
                payload["manifest_sha256"], "manifest.manifest_sha256"
            ),
        )


@dataclass(frozen=True)
class ExternalReplayLockV2:
    """Externally persisted pre-seal lock; an authority label, not a signature."""

    schema_version: str
    authority: str
    manifest_sha256: str
    split_registry_sha256: str
    protocol_sha256: str
    source_manifest_sha256: str
    qaoa_observation_sha256: str
    qaoa_control_observation_sha256: str
    qaoa_counts_payload_sha256: str
    qaoa_final_parameter_payload_sha256: str
    qaoa_run_attestation_sha256: str
    lock_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> "ExternalReplayLockV2":
        payload = _strict_mapping(raw, "external_replay_lock")
        _exact_fields(payload, set(cls.__dataclass_fields__), "external_replay_lock")
        lock = cls(
            schema_version=_strict_str(
                payload["schema_version"], "external_replay_lock.schema_version"
            ),
            authority=_strict_str(
                payload["authority"], "external_replay_lock.authority"
            ),
            manifest_sha256=_require_sha256(
                payload["manifest_sha256"], "external_replay_lock.manifest_sha256"
            ),
            split_registry_sha256=_require_sha256(
                payload["split_registry_sha256"],
                "external_replay_lock.split_registry_sha256",
            ),
            protocol_sha256=_require_sha256(
                payload["protocol_sha256"], "external_replay_lock.protocol_sha256"
            ),
            source_manifest_sha256=_require_sha256(
                payload["source_manifest_sha256"],
                "external_replay_lock.source_manifest_sha256",
            ),
            qaoa_observation_sha256=_require_sha256(
                payload["qaoa_observation_sha256"],
                "external_replay_lock.qaoa_observation_sha256",
            ),
            qaoa_control_observation_sha256=_require_sha256(
                payload["qaoa_control_observation_sha256"],
                "external_replay_lock.qaoa_control_observation_sha256",
            ),
            qaoa_counts_payload_sha256=_require_sha256(
                payload["qaoa_counts_payload_sha256"],
                "external_replay_lock.qaoa_counts_payload_sha256",
            ),
            qaoa_final_parameter_payload_sha256=_require_sha256(
                payload["qaoa_final_parameter_payload_sha256"],
                "external_replay_lock.qaoa_final_parameter_payload_sha256",
            ),
            qaoa_run_attestation_sha256=_require_sha256(
                payload["qaoa_run_attestation_sha256"],
                "external_replay_lock.qaoa_run_attestation_sha256",
            ),
            lock_sha256=_require_sha256(
                payload["lock_sha256"], "external_replay_lock.lock_sha256"
            ),
        )
        if lock.schema_version != EXTERNAL_REPLAY_LOCK_V2_SCHEMA:
            raise ValueError("unsupported external replay lock schema")
        if lock.authority != EXTERNAL_LOCK_AUTHORITY:
            raise ValueError(
                "external lock authority must be local_preseal_external_lock; "
                "it is not a signature"
            )
        if lock.lock_sha256 != _sha(_external_lock_payload(lock)):
            raise ValueError("external replay lock canonical SHA mismatch")
        return lock

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ExternalReplayLockV2":
        if type(raw) is not bytes:
            raise TypeError("external replay lock payload must be native bytes")

        def reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key in external lock: {key!r}")
                result[key] = value
            return result

        try:
            decoded = json.loads(
                raw.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("external replay lock bytes are not strict UTF-8 JSON") from exc
        lock = cls.from_mapping(decoded)
        if raw != canonical_json_bytes(lock.to_dict()):
            raise ValueError("external replay lock bytes are not canonical JSON")
        return lock


def _external_lock_payload(lock: ExternalReplayLockV2) -> dict[str, object]:
    payload = lock.to_dict()
    payload.pop("lock_sha256")
    return payload


_VALIDATED_REPLAY_GROUP_TOKEN = object()


class _ValidatedReplayGroupV2:
    """Same-call validation result; never a public trainer trust capability."""

    __slots__ = (
        "_lock_sha256",
        "_manifest_sha256",
        "_case_sha256",
        "_split_registry_sha256",
        "_arm_observation_sha256",
        "_audits",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("_ValidatedReplayGroupV2 cannot be subclassed")

    def __init__(
        self,
        *,
        lock_sha256: str,
        manifest_sha256: str,
        case_sha256: str,
        split_registry_sha256: str,
        arm_observation_sha256: tuple[tuple[str, str], ...],
        audits: tuple[tuple[str, ReplayLedgerAuditV2], ...],
        _token: object,
    ) -> None:
        if _token is not _VALIDATED_REPLAY_GROUP_TOKEN:
            raise TypeError(
                "_ValidatedReplayGroupV2 can only be issued by external lock validation"
            )
        object.__setattr__(self, "_lock_sha256", lock_sha256)
        object.__setattr__(self, "_manifest_sha256", manifest_sha256)
        object.__setattr__(self, "_case_sha256", case_sha256)
        object.__setattr__(self, "_split_registry_sha256", split_registry_sha256)
        object.__setattr__(self, "_arm_observation_sha256", arm_observation_sha256)
        object.__setattr__(self, "_audits", audits)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("_ValidatedReplayGroupV2 is immutable")

    @property
    def lock_sha256(self) -> str:
        return self._lock_sha256

    @property
    def manifest_sha256(self) -> str:
        return self._manifest_sha256

    def audit_for(
        self,
        record: FinalMeasurementObservationV2,
        case: FrozenSharedCase,
        registry: SplitRegistryV2,
        *,
        expected_observation_sha256: str,
        expected_registry_sha256: str,
    ) -> ReplayLedgerAuditV2:
        if not isinstance(record, FinalMeasurementObservationV2):
            raise TypeError("record must be a FinalMeasurementObservationV2")
        validate_frozen_shared_case(case)
        validate_split_registry_v2(
            registry, expected_registry_sha256=expected_registry_sha256
        )
        external_observation = _require_sha256(
            expected_observation_sha256, "expected_observation_sha256"
        )
        if case.case_sha256 != self._case_sha256:
            raise ValueError("case is not bound to this verified replay capability")
        if registry.registry_sha256 != self._split_registry_sha256:
            raise ValueError("registry is not bound to this verified replay capability")
        if record.split_registry_sha256 != self._split_registry_sha256:
            raise ValueError("record registry is not bound to this verified capability")
        if record.observation_sha256 != external_observation:
            raise ValueError("record SHA does not match the requested external anchor")
        expected = dict(self._arm_observation_sha256).get(record.source_arm)
        if expected != record.observation_sha256:
            raise ValueError("record is not bound to this verified replay capability")
        try:
            audit = dict(self._audits)[record.source_arm]
        except KeyError as exc:  # pragma: no cover - constructor invariant
            raise RuntimeError("verified capability lost its arm audit") from exc
        if audit.observation_sha256 != record.observation_sha256:
            raise RuntimeError("verified capability audit binding changed")
        return audit


@dataclass(frozen=True)
class EqualObservationGroupAuditV2:
    manifest_sha256: str
    group_id: str
    source_arms: tuple[str, ...]
    declared_observation_budget: int
    total_observed_by_arm: tuple[tuple[str, int], ...]
    observation_budget_complete_by_arm: tuple[tuple[str, bool], ...]
    eligible_arms: tuple[str, ...]
    ineligible_reasons_by_arm: tuple[tuple[str, tuple[str, ...]], ...]
    qaoa_counts_identical_to_control: bool
    qaoa_distribution_sha_identical_to_control: bool
    label_permutation_nonidentity: bool
    permuted_policy_effective: bool
    whole_vector_cluster_id: str
    observation_budget_equal: bool = True
    compute_budget_equal: bool = False
    all_four_arms_present: bool = True
    structural_passed: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _group_id_payload(
    case: FrozenSharedCase,
    entry: SplitRegistryEntryV2,
    *,
    observation_budget: int,
    group_nonce: str,
) -> dict[str, object]:
    return {
        "schema_version": "xa.e6-replay-group-id.v2",
        "semantics": "design_group_identifier_not_an_artifact_manifest",
        "case_sha256": case.case_sha256,
        "candidate_pool_sha256": case.candidate_pool_sha256,
        "family_id": entry.family_id,
        "orbit_cluster_sha256": entry.orbit_cluster_sha256,
        "split_role": entry.split_role,
        "origin": entry.origin.to_dict(),
        "observation_budget": observation_budget,
        "group_nonce": group_nonce,
        "source_arms": list(SOURCE_ARMS),
        "observation_budget_equal": True,
        "compute_budget_equal": False,
    }


def replay_group_id_v2(
    case: FrozenSharedCase,
    entry: SplitRegistryEntryV2,
    *,
    observation_budget: int,
    group_nonce: str,
) -> str:
    validate_frozen_shared_case(case)
    _validate_registry_entry(entry)
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    nonce = _strict_str(group_nonce, "group_nonce")
    return _sha(
        _group_id_payload(
            case, entry, observation_budget=budget, group_nonce=nonce
        )
    )


def _canonical_counts(
    counts: Mapping[str, int] | Sequence[tuple[str, int]],
) -> tuple[tuple[str, int], ...]:
    if type(counts) is dict:
        items = tuple(counts.items())
    elif type(counts) in {list, tuple}:
        items = tuple(counts)
    else:
        raise TypeError("counts must be a native dict/list/tuple")
    result: list[tuple[str, int]] = []
    for index, item in enumerate(items):
        if type(item) not in {list, tuple} or len(item) != 2:
            raise TypeError(f"counts[{index}] must be a native pair")
        key = _strict_str(item[0], f"counts[{index}].bitstring", nonempty=False)
        count = _strict_int(item[1], f"counts[{index}].count", minimum=1)
        result.append((key, count))
    if len({key for key, _ in result}) != len(result):
        raise ValueError("counts contain duplicate bitstrings")
    return tuple(sorted(result))


def _decode_count_key(key: str, variable_count: int) -> tuple[int, ...]:
    if len(key) != variable_count:
        raise ValueError(
            "count key must contain exactly one x0..x(K-1) bit per augmented variable"
        )
    if any(character not in "01" for character in key):
        raise ValueError("count key contains a non-binary character")
    return tuple(int(character) for character in key)


def _bits_to_key(bits: Sequence[int]) -> str:
    return "".join(str(_strict_int(bit, "bit", minimum=0)) for bit in bits)


def _random_source_payload(
    case: FrozenSharedCase, observation_budget: int, seed: int
) -> dict[str, object]:
    return {
        "schema_version": "xa.e6-random-replay-source.v2",
        "algorithm": GENERATOR_IDS["classical_random_bitstring_replay"],
        "case_sha256": case.case_sha256,
        "augmented_variable_count": case.augmented_variable_count,
        "observation_budget": observation_budget,
        "seed": seed,
        "stream": "sha256(canonical_json(domain,case,seed,draw_index))_mod_2**K",
    }


def canonical_random_counts_v2(
    case: FrozenSharedCase, *, observation_budget: int, seed: int
) -> tuple[tuple[str, int], ...]:
    """Uniform augmented-bit samples from a versioned SHA-256 counter stream."""

    validate_frozen_shared_case(case)
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    generator_seed = _strict_int(seed, "seed", minimum=0)
    width = case.augmented_variable_count
    modulus = 1 << width
    counts: dict[str, int] = {}
    for draw_index in range(budget):
        digest = _sha(
            {
                "schema_version": "xa.e6-random-replay-draw.v2",
                "case_sha256": case.case_sha256,
                "seed": generator_seed,
                "draw_index": draw_index,
            }
        )
        value = int(digest, 16) % modulus
        key = "".join(str((value >> index) & 1) for index in range(width))
        counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(counts.items()))


def _greedy_source_payload(
    case: FrozenSharedCase,
    observation_budget: int,
    selected_augmented_bitstring: tuple[int, ...],
) -> dict[str, object]:
    return {
        "schema_version": "xa.e6-greedy-replay-source.v2",
        "algorithm": GENERATOR_IDS[
            "classical_greedy_repeated_selection_replay"
        ],
        "case_sha256": case.case_sha256,
        "candidate_pool_sha256": case.candidate_pool_sha256,
        "observation_budget": observation_budget,
        "selected_augmented_bitstring": list(selected_augmented_bitstring),
        "selection_recomputed_from_frozen_case": True,
    }


def canonical_greedy_counts_v2(
    case: FrozenSharedCase, *, observation_budget: int
) -> tuple[tuple[str, int], ...]:
    """Recompute frozen greedy selection once and repeat it exactly R times."""

    validate_frozen_shared_case(case)
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    result = schedule_frozen_case(case, "greedy")
    return ((_bits_to_key(result.augmented_bitstring), budget),)


def _greedy_compute_budget_v2(
    case: FrozenSharedCase, observation_budget: int
) -> ComputeBudgetV2:
    """Describe the work actually performed by ``schedule_frozen_case(greedy)``.

    The shared scheduler first audits every augmented QUBO assignment.  Its
    greedy loop then performs at most one full remaining-candidate scan for
    each effective budget slot; repetition into R observations does not rerun
    selection.
    """

    real_count = len(case.actions)
    budget_effective = case.qubo.budget_effective
    scan_upper_bound = sum(
        real_count - selected_count
        for selected_count in range(min(real_count, budget_effective))
    )
    return ComputeBudgetV2(
        quantum_circuit_executions=0,
        statevector_expectation_evaluations=0,
        classical_candidate_evaluations=scan_upper_bound,
        qubo_assignments_audited=1 << case.augmented_variable_count,
        greedy_candidate_scans_upper_bound=scan_upper_bound,
        bitstrings_generated=observation_budget,
        declared_wall_seconds=None,
        notes=(
            "one exhaustive augmented-QUBO audit plus one frozen greedy "
            "selection; scans bounded by sum(K_real-t,t=0..B_effective-1); "
            "selected bitstring repeated R times"
        ),
    )


def deterministic_label_permutation_v2(
    action_count: int,
    *,
    seed: int,
    parent_observation_sha256: str,
    candidate_pool_sha256: str,
) -> tuple[int, ...]:
    """Return ``new_label_index -> source_label_index`` deterministically."""

    count = _strict_int(action_count, "action_count", minimum=0)
    generator_seed = _strict_int(seed, "seed", minimum=0)
    parent = _require_sha256(
        parent_observation_sha256, "parent_observation_sha256"
    )
    pool = _require_sha256(candidate_pool_sha256, "candidate_pool_sha256")
    if count <= 1:
        return tuple(range(count))
    ranked = sorted(
        range(count),
        key=lambda index: _sha(
            {
                "schema_version": "xa.e6-label-permutation-key.v2",
                "seed": generator_seed,
                "parent_observation_sha256": parent,
                "candidate_pool_sha256": pool,
                "source_index": index,
            }
        ),
    )
    if ranked == list(range(count)):
        ranked = ranked[1:] + ranked[:1]
    return tuple(ranked)


def deterministic_nonidentity_label_permutation(
    action_count: int,
    *,
    seed: int,
    source_observation_sha256: str,
    candidate_pool_sha256: str,
) -> tuple[int, ...]:
    """Compatibility alias; identity is unavoidable and explicit for K<=1."""

    return deterministic_label_permutation_v2(
        action_count,
        seed=seed,
        parent_observation_sha256=source_observation_sha256,
        candidate_pool_sha256=candidate_pool_sha256,
    )


def qaoa_counts_payload_bytes_v2(
    case: FrozenSharedCase,
    counts: Mapping[str, int] | Sequence[tuple[str, int]],
    *,
    execution_class: str,
) -> bytes:
    """Canonical bytes that an external pre-seal lock must bind as actual counts."""

    validate_frozen_shared_case(case)
    execution = _strict_str(execution_class, "execution_class")
    if execution not in QAOA_EXECUTION_CLASSES:
        raise ValueError("unregistered qaoa_execution_class")
    canonical = _canonical_counts(counts)
    return canonical_json_bytes(
        {
            "schema_version": "xa.e6-qaoa-actual-counts-payload.v2",
            "count_bit_order": COUNT_BIT_ORDER,
            "case_sha256": case.case_sha256,
            "candidate_pool_sha256": case.candidate_pool_sha256,
            "qubo_sha256": case.qubo_sha256,
            "scheduler": {
                "seed": case.scheduler_config.qaoa_seed,
                "shots": case.scheduler_config.qaoa_shots,
                "p": case.scheduler_config.qaoa_p,
                "optimizer_restarts": case.scheduler_config.qaoa_optimizer_restarts,
                "optimizer_steps": case.scheduler_config.qaoa_optimizer_steps,
            },
            "execution_class": execution,
            "counts": [
                {"bitstring": key, "count": count} for key, count in canonical
            ],
        }
    )


def _distribution_payload(record: FinalMeasurementObservationV2) -> dict[str, object]:
    """Arm-neutral so QAOA and its label control bind the same distribution."""

    return {
        "schema_version": "xa.e6-final-count-distribution.v2",
        "measurement_semantics": record.measurement_semantics,
        "count_bit_order": record.count_bit_order,
        "case_sha256": record.case_sha256,
        "candidate_pool_sha256": record.candidate_pool_sha256,
        "qubo_sha256": record.qubo_sha256,
        "observation_budget": record.observation_budget,
        "counts": [list(item) for item in record.counts],
        "qaoa_contract": (
            None if record.qaoa_contract is None else record.qaoa_contract.to_dict()
        ),
        "qaoa_execution_class": record.qaoa_execution_class,
    }


def _observation_payload(record: FinalMeasurementObservationV2) -> dict[str, object]:
    payload = record.to_dict()
    payload.pop("observation_sha256")
    return payload


def _manifest_payload(manifest: ReplayGroupManifestV2) -> dict[str, object]:
    payload = manifest.to_dict()
    payload.pop("manifest_sha256")
    return payload


def _selected_program_score(
    case: FrozenSharedCase, selected_indices: Sequence[int]
) -> float:
    selected = tuple(case.actions[index] for index in selected_indices)
    return float(
        program_resource_summary(
            emit_shared_oracle(case.vector, selected),
            weights=case.utility_weights,
        ).total_abstract_score
    )


def _signed_value_audit(
    feasible_expected_program_score: float,
    direct_program_score: float,
) -> SignedValueAuditV2:
    numerator = _strict_float(
        feasible_expected_program_score,
        "feasible_expected_program_score",
        minimum=0.0,
    )
    denominator = _strict_float(
        direct_program_score, "direct_program_score", minimum=0.0
    )
    if denominator == 0.0:
        if numerator == 0.0:
            ratio: float | None = 1.0
            raw: float | None = 0.0
            signed = 0.0
        else:
            ratio = None
            raw = None
            signed = 3.0
    elif numerator == 0.0:
        ratio = 0.0
        raw = None
        signed = -3.0
    else:
        ratio = numerator / denominator
        raw = math.log(ratio)
        signed = float(max(-3.0, min(3.0, raw)))
    tolerance = 1.0e-12 * max(1.0, numerator, denominator)
    if numerator < denominator - tolerance:
        direction = "improvement"
    elif numerator > denominator + tolerance:
        direction = "harm"
    else:
        direction = "tie"
    return SignedValueAuditV2(
        feasible_expected_program_score=numerator,
        direct_program_score=denominator,
        score_ratio=ratio,
        raw_signed_log_ratio=raw,
        signed_log_ratio_for_audit=signed,
        direction=direction,
        worse_than_direct=direction == "harm",
        value_target_log_ratio=float(max(-3.0, min(0.0, signed))),
    )


def _generator_configuration_sha(record: FinalMeasurementObservationV2) -> str:
    return _sha(
        {
            "schema_version": "xa.e6-generator-configuration-binding.v2",
            "source_arm": record.source_arm,
            "generator_contract": record.generator_contract.to_dict(),
            "qaoa_contract": (
                None if record.qaoa_contract is None else record.qaoa_contract.to_dict()
            ),
            "qaoa_execution_class": record.qaoa_execution_class,
            "label_permutation_new_index_to_source_index": list(
                record.label_permutation_new_index_to_source_index
            ),
        }
    )


def _validate_qaoa_contract(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    *,
    trusted_qaoa_counts_source_sha256: str | None,
) -> bool:
    qaoa = record.qaoa_contract
    if qaoa is None:
        raise ValueError("QAOA replay arms require qaoa_contract")
    parsed = QAOAFinalMeasurementContractV2.from_dict(qaoa.to_dict())
    expected_config = {
        "scheduler_seed": case.scheduler_config.qaoa_seed,
        "shots": case.scheduler_config.qaoa_shots,
        "p": case.scheduler_config.qaoa_p,
        "optimizer_restarts": case.scheduler_config.qaoa_optimizer_restarts,
        "optimizer_steps": case.scheduler_config.qaoa_optimizer_steps,
    }
    for name, expected in expected_config.items():
        if getattr(parsed, name) != expected:
            raise ValueError(f"QAOA {name} drifted from the frozen case")
    if record.observation_budget != parsed.shots:
        raise ValueError("QAOA observation budget must equal frozen scheduler shots")
    if parsed.source_trust not in QAOA_SOURCE_TRUST_LEVELS:
        raise ValueError("unregistered QAOA source trust level")
    if parsed.source_trust == "unverified_development_ledger":
        if parsed.source_attestation_sha256 is not None:
            raise ValueError("unverified QAOA ledgers cannot claim an attestation")
        source_trusted = False
    else:
        if parsed.source_attestation_sha256 is None:
            raise ValueError("externally attested QAOA sources require attestation SHA")
        source_binding_matches = (
            trusted_qaoa_counts_source_sha256 is not None
            and _require_sha256(
                trusted_qaoa_counts_source_sha256,
                "trusted_qaoa_counts_source_sha256",
            )
            == parsed.counts_source_sha256
        )
        if trusted_qaoa_counts_source_sha256 is not None and not source_binding_matches:
            raise ValueError("QAOA counts source SHA does not match verified lock")
        source_trusted = source_binding_matches
    observed = record.qaoa_execution_class in {
        "direct_unrepaired",
        "direct_repaired",
    }
    if observed:
        if parsed.final_parameter_payload_sha256 is None:
            raise ValueError("direct QAOA requires a final parameter payload SHA")
        if not record.counts:
            raise ValueError("direct QAOA requires final measured counts")
    else:
        if parsed.final_parameter_payload_sha256 is not None or record.counts:
            raise ValueError(
                "fallback/not-invoked QAOA ledger cannot claim final parameters/counts"
            )
    return source_trusted


def _validate_arm_and_generator(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    *,
    trusted_qaoa_counts_source_sha256: str | None,
) -> bool:
    _validate_generator_contract(record.generator_contract, record.source_arm)
    arm = record.source_arm
    if arm == "classical_random_bitstring_replay":
        if record.qaoa_contract is not None or record.qaoa_execution_class != CLASSICAL_EXECUTION_CLASS:
            raise ValueError("classical random replay cannot claim QAOA execution")
        expected_counts = canonical_random_counts_v2(
            case,
            observation_budget=record.observation_budget,
            seed=record.generator_contract.seed,
        )
        expected_source = _sha(
            _random_source_payload(
                case, record.observation_budget, record.generator_contract.seed
            )
        )
        if record.counts != expected_counts:
            raise ValueError("random replay counts do not recompute from SHA stream")
        if record.generator_contract.source_payload_sha256 != expected_source:
            raise ValueError("random replay source payload SHA mismatch")
        expected_budget = ComputeBudgetV2(
            quantum_circuit_executions=0,
            statevector_expectation_evaluations=0,
            classical_candidate_evaluations=0,
            qubo_assignments_audited=0,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=record.observation_budget,
            declared_wall_seconds=None,
            notes="canonical SHA-256 counter draws",
        )
        if record.generator_contract.compute_budget != expected_budget:
            raise ValueError("random replay compute budget contract changed")
        return True
    if arm == "classical_greedy_repeated_selection_replay":
        if record.qaoa_contract is not None or record.qaoa_execution_class != CLASSICAL_EXECUTION_CLASS:
            raise ValueError("classical greedy replay cannot claim QAOA execution")
        expected_counts = canonical_greedy_counts_v2(
            case, observation_budget=record.observation_budget
        )
        bits = _decode_count_key(expected_counts[0][0], case.augmented_variable_count)
        expected_source = _sha(
            _greedy_source_payload(case, record.observation_budget, bits)
        )
        if record.counts != expected_counts:
            raise ValueError("greedy replay counts do not match frozen greedy selection")
        if record.generator_contract.source_payload_sha256 != expected_source:
            raise ValueError("greedy replay source payload SHA mismatch")
        expected_budget = _greedy_compute_budget_v2(
            case, record.observation_budget
        )
        if record.generator_contract.compute_budget != expected_budget:
            raise ValueError("greedy replay compute budget contract changed")
        return True
    if arm not in {"qaoa_final_measurement_replay", "qaoa_permuted_label_control"}:
        raise ValueError(f"unregistered source_arm: {arm!r}")
    if record.qaoa_execution_class not in QAOA_EXECUTION_CLASSES:
        raise ValueError("unregistered qaoa_execution_class")
    trusted = _validate_qaoa_contract(
        record,
        case,
        trusted_qaoa_counts_source_sha256=trusted_qaoa_counts_source_sha256,
    )
    if arm == "qaoa_final_measurement_replay":
        if record.parent_qaoa_observation_sha256 is not None:
            raise ValueError("QAOA source observation cannot name a parent")
        if record.label_permutation_new_index_to_source_index:
            raise ValueError("QAOA source observation cannot permute labels")
        if (
            record.generator_contract.source_payload_sha256
            != record.qaoa_contract.counts_source_sha256  # type: ignore[union-attr]
        ):
            raise ValueError("QAOA generator/source payload SHA mismatch")
        qaoa_budget = record.generator_contract.compute_budget
        observed_count = sum(count for _, count in record.counts)
        if qaoa_budget.bitstrings_generated != observed_count:
            raise ValueError("QAOA compute budget bitstring count changed")
        if qaoa_budget.qubo_assignments_audited != (
            1 << case.augmented_variable_count
        ):
            raise ValueError("QAOA compute budget must record exhaustive QUBO audit")
        if qaoa_budget.greedy_candidate_scans_upper_bound != 0:
            raise ValueError("QAOA direct replay cannot claim greedy candidate scans")
        if (
            record.qaoa_execution_class.startswith("direct_")
            and qaoa_budget.statevector_expectation_evaluations < 1
        ):
            raise ValueError("direct QAOA must record statevector expectation work")
    else:
        _require_sha256(
            record.parent_qaoa_observation_sha256,
            "parent_qaoa_observation_sha256",
        )
        permutation = record.label_permutation_new_index_to_source_index
        if len(permutation) != len(record.action_signatures):
            raise ValueError("control label permutation must align with action pool")
        if set(permutation) != set(range(len(permutation))):
            raise ValueError("control label permutation must be a bijection")
        if len(permutation) > 1 and permutation == tuple(range(len(permutation))):
            raise ValueError("non-degenerate label control requires non-identity permutation")
        expected_control_budget = ComputeBudgetV2(
            quantum_circuit_executions=0,
            statevector_expectation_evaluations=0,
            classical_candidate_evaluations=len(case.actions),
            qubo_assignments_audited=0,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=0,
            declared_wall_seconds=None,
            notes="reuse QAOA observations and deterministically relabel actions",
        )
        if record.generator_contract.compute_budget != expected_control_budget:
            raise ValueError("label-control compute budget contract changed")
    return trusted


def _aligned_indices(
    source_indices: tuple[int, ...], permutation: tuple[int, ...]
) -> tuple[int, ...]:
    if not permutation:
        return source_indices
    selected = set(source_indices)
    return tuple(
        new_index
        for new_index, source_index in enumerate(permutation)
        if source_index in selected
    )


def _audit_counts(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    *,
    source_trusted: bool,
    parent_validated: bool,
) -> ReplayLedgerAuditV2:
    model = case.qubo
    rows: list[BitstringAuditV2] = []
    feasible_rows: list[tuple[tuple[int, ...], int]] = []
    source_marginals = [0] * model.real_candidate_count
    total = 0
    permutation = record.label_permutation_new_index_to_source_index
    for key, count in record.counts:
        bits = _decode_count_key(key, model.variable_count)
        source_selected = model.selected_real(bits)
        aligned_selected = _aligned_indices(source_selected, permutation)
        conflicts = model.conflict_count(bits)
        feasible = model.is_feasible(bits)
        total += count
        if feasible:
            feasible_rows.append((bits, count))
            for index in source_selected:
                source_marginals[index] += count
        rows.append(
            BitstringAuditV2(
                bitstring=bits,
                count=count,
                cardinality=sum(bits),
                source_selected_real_indices=source_selected,
                label_aligned_selected_real_indices=aligned_selected,
                dummy_selected=sum(bits[model.real_candidate_count :]),
                conflict_count=conflicts,
                feasible=feasible,
                phase_energy=model.phase_energy(bits),
            )
        )
    expected_complete = record.qaoa_execution_class not in {"fallback", "not_invoked"}
    if expected_complete and total != record.observation_budget:
        raise ValueError(
            f"counts sum to {total}, expected observation budget {record.observation_budget}"
        )
    if not expected_complete and total != 0:
        raise ValueError("fallback/not-invoked ledgers must contain zero observations")
    feasible_total = sum(count for _, count in feasible_rows)
    source_mass = sum(source_marginals)
    source_policy = (
        ()
        if source_mass == 0
        else tuple(value / source_mass for value in source_marginals)
    )
    aligned_marginals = (
        tuple(source_marginals[index] for index in permutation)
        if permutation
        else tuple(source_marginals)
    )
    aligned_policy = (
        ()
        if source_mass == 0
        else tuple(value / source_mass for value in aligned_marginals)
    )
    denominator = total * model.budget_effective
    policy_weight = 0.0 if denominator == 0 else source_mass / denominator
    feasible_fraction = 0.0 if total == 0 else feasible_total / total
    direct_score = _selected_program_score(case, ())
    expected_score = (
        direct_score
        if feasible_total == 0
        else math.fsum(
            _selected_program_score(case, model.selected_real(bits)) * count
            for bits, count in feasible_rows
        )
        / feasible_total
    )
    value_audit = _signed_value_audit(expected_score, direct_score)

    reasons: list[str] = []
    if record.split_role != TRAIN_SPLIT_ROLE:
        reasons.append("split_role_forbids_training")
    if record.origin.crypto_holdout_leakage_risk:
        reasons.append("cryptographic_evaluation_holdout_leakage")
    if not expected_complete:
        reasons.append("observation_budget_not_realised")
    if feasible_total == 0:
        reasons.append("no_feasible_observations")
    if model.budget_effective == 0:
        reasons.append("zero_real_action_budget")
    if source_mass == 0:
        reasons.append("no_real_action_marginal_mass")
    if value_audit.worse_than_direct:
        reasons.append("harmful_vs_direct")
    if record.source_arm in {"qaoa_final_measurement_replay", "qaoa_permuted_label_control"}:
        if record.qaoa_execution_class != "direct_unrepaired":
            reasons.append("qaoa_execution_not_direct_unrepaired")
        if not source_trusted:
            reasons.append("qaoa_source_unverified")
    if record.source_arm == "qaoa_permuted_label_control":
        if not parent_validated:
            reasons.append("parent_qaoa_observation_not_validated")
        if len(permutation) <= 1:
            reasons.append("label_permutation_degenerate")
        elif aligned_policy == source_policy:
            reasons.append("permuted_policy_unchanged")
    return ReplayLedgerAuditV2(
        observation_sha256=record.observation_sha256,
        source_arm=record.source_arm,
        structural_valid=True,
        action_signatures=record.action_signatures,
        bitstring_audit=tuple(rows),
        total_observed=total,
        declared_observation_budget=record.observation_budget,
        observation_budget_complete=total == record.observation_budget,
        feasible_observed=feasible_total,
        infeasible_observed=total - feasible_total,
        feasible_fraction=float(feasible_fraction),
        source_marginal_action_counts=tuple(source_marginals),
        label_aligned_marginal_action_counts=aligned_marginals,
        source_policy_target=source_policy,
        label_aligned_policy_target=aligned_policy,
        policy_observation_weight=float(policy_weight),
        value_audit=value_audit,
        whole_vector_cluster_id=record.whole_vector_cluster_id,
        source_trusted=source_trusted,
        parent_validated=parent_validated,
        teacher_eligible=not reasons,
        ineligibility_reasons=tuple(reasons),
    )


def _validate_parent_relation(
    control: FinalMeasurementObservationV2,
    parent: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_parent_observation_sha256: str,
    trusted_qaoa_counts_source_sha256: str | None,
) -> ReplayLedgerAuditV2:
    parent_audit = _validate_final_measurement_observation_impl(
        parent,
        case,
        registry,
        expected_observation_sha256=expected_parent_observation_sha256,
        expected_registry_sha256=control.split_registry_sha256,
        trusted_qaoa_counts_source_sha256=trusted_qaoa_counts_source_sha256,
    )
    if parent.source_arm != "qaoa_final_measurement_replay":
        raise ValueError("label-control parent must be QAOA final measurement")
    if control.parent_qaoa_observation_sha256 != parent.observation_sha256:
        raise ValueError("label-control parent observation SHA mismatch")
    for name in (
        "case_sha256",
        "candidate_pool_sha256",
        "qubo_sha256",
        "whole_vector_cluster_id",
        "family_id",
        "orbit_cluster_sha256",
        "split_registry_sha256",
        "group_id",
        "split_role",
        "origin",
        "observation_budget",
        "counts",
        "qaoa_contract",
        "qaoa_execution_class",
        "distribution_sha256",
    ):
        if getattr(control, name) != getattr(parent, name):
            raise ValueError(f"label control must reuse parent QAOA {name}")
    expected_permutation = deterministic_label_permutation_v2(
        len(control.action_signatures),
        seed=control.generator_contract.seed,
        parent_observation_sha256=parent.observation_sha256,
        candidate_pool_sha256=case.candidate_pool_sha256,
    )
    if control.label_permutation_new_index_to_source_index != expected_permutation:
        raise ValueError("label-control permutation does not match seeded contract")
    if control.generator_contract.source_payload_sha256 != parent.distribution_sha256:
        raise ValueError("label-control source payload must bind parent distribution")
    return parent_audit


def _validate_final_measurement_observation_impl(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_observation_sha256: str,
    expected_registry_sha256: str,
    trusted_qaoa_counts_source_sha256: str | None = None,
    parent_qaoa_observation: FinalMeasurementObservationV2 | None = None,
    expected_parent_observation_sha256: str | None = None,
) -> ReplayLedgerAuditV2:
    """Validate one structural ledger; never extract a teacher implicitly."""

    if not isinstance(record, FinalMeasurementObservationV2):
        raise TypeError("record must be a FinalMeasurementObservationV2")
    validate_frozen_shared_case(case)
    validate_split_registry_v2(
        registry, expected_registry_sha256=expected_registry_sha256
    )
    external_observation = _require_sha256(
        expected_observation_sha256, "expected_observation_sha256"
    )
    parsed = FinalMeasurementObservationV2.from_dict(record.to_dict())
    if parsed.schema_version != FINAL_MEASUREMENT_REPLAY_V2_SCHEMA:
        raise ValueError("unsupported final-measurement observation schema")
    if parsed.source_arm not in SOURCE_ARMS:
        raise ValueError(f"unregistered source_arm: {parsed.source_arm!r}")
    if parsed.measurement_semantics != MEASUREMENT_SEMANTICS:
        raise ValueError("measurement semantics changed")
    if parsed.count_bit_order != COUNT_BIT_ORDER:
        raise ValueError("count bit order changed")
    if parsed.value_target_contract != VALUE_TARGET_CONTRACT:
        raise ValueError("value target contract changed")
    if parsed.compute_budget_equal is not False:
        raise ValueError("compute_budget_equal must remain false")
    if parsed.performance_evidence is not False:
        raise ValueError("development replay is not performance evidence")
    expected_bindings = {
        "case_sha256": case.case_sha256,
        "vector_sha256": case.vector_sha256,
        "candidate_pool_sha256": case.candidate_pool_sha256,
        "qubo_sha256": case.qubo_sha256,
        "whole_vector_cluster_id": whole_vector_cluster_id(case),
        "split_registry_sha256": registry.registry_sha256,
    }
    for name, expected in expected_bindings.items():
        if getattr(parsed, name) != expected:
            raise ValueError(f"observation {name} does not match frozen input")
    entry = _lookup_registry_entry(
        registry,
        family_id=parsed.family_id,
        orbit_cluster_sha256=parsed.orbit_cluster_sha256,
    )
    recomputed_orbit = canonical_vector_orbit_sha256(case.vector)
    if parsed.orbit_cluster_sha256 != recomputed_orbit:
        raise ValueError("observation orbit does not recompute from the frozen vector")
    if entry.orbit_cluster_sha256 != recomputed_orbit:
        raise ValueError("split registry orbit does not recompute from the frozen vector")
    if entry.vector_sha256 != case.vector_sha256:
        raise ValueError("registry vector SHA does not match frozen case")
    if parsed.split_role != entry.split_role:
        raise ValueError("observation split does not match split registry")
    if parsed.origin != entry.origin:
        raise ValueError("observation origin does not match split registry")
    expected_group_id = replay_group_id_v2(
        case,
        entry,
        observation_budget=parsed.observation_budget,
        group_nonce=parsed.group_nonce,
    )
    if parsed.group_id != expected_group_id:
        raise ValueError("observation group_id changed")
    expected_signatures = tuple(
        canonical_action_sha256(action) for action in case.actions
    )
    if parsed.action_signatures != expected_signatures:
        raise ValueError("action signatures do not match frozen pool")
    if parsed.counts != tuple(sorted(parsed.counts)):
        raise ValueError("counts are not in canonical order")
    if len({key for key, _ in parsed.counts}) != len(parsed.counts):
        raise ValueError("counts contain duplicate keys")
    for key, count in parsed.counts:
        _decode_count_key(key, case.augmented_variable_count)
        _strict_int(count, f"counts[{key!r}]", minimum=1)

    source_trusted = _validate_arm_and_generator(
        parsed,
        case,
        trusted_qaoa_counts_source_sha256=trusted_qaoa_counts_source_sha256,
    )
    if parsed.distribution_sha256 != _sha(_distribution_payload(parsed)):
        raise ValueError("distribution canonical SHA mismatch")
    if parsed.observation_sha256 != _sha(_observation_payload(parsed)):
        raise ValueError("observation canonical SHA mismatch")
    if parsed.observation_sha256 != external_observation:
        raise ValueError("observation SHA does not match external anchor")

    parent_validated = False
    if parsed.source_arm == "qaoa_permuted_label_control":
        if parent_qaoa_observation is not None:
            if expected_parent_observation_sha256 is None:
                raise TypeError("control parent requires an external parent SHA")
            parent_audit = _validate_parent_relation(
                parsed,
                parent_qaoa_observation,
                case,
                registry,
                expected_parent_observation_sha256=expected_parent_observation_sha256,
                trusted_qaoa_counts_source_sha256=trusted_qaoa_counts_source_sha256,
            )
            parent_validated = True
            source_trusted = parent_audit.source_trusted
        elif expected_parent_observation_sha256 is not None:
            raise ValueError("parent SHA supplied without parent observation")
    elif parent_qaoa_observation is not None or expected_parent_observation_sha256 is not None:
        raise ValueError("only label control accepts a parent observation")

    audit = _audit_counts(
        parsed,
        case,
        source_trusted=source_trusted,
        parent_validated=parent_validated,
    )
    if parsed.qaoa_execution_class == "direct_repaired" and audit.feasible_observed:
        raise ValueError("direct_repaired QAOA cannot contain feasible observed shots")
    return audit


def validate_final_measurement_observation_v2(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_observation_sha256: str,
    expected_registry_sha256: str,
    parent_qaoa_observation: FinalMeasurementObservationV2 | None = None,
    expected_parent_observation_sha256: str | None = None,
) -> ReplayLedgerAuditV2:
    """Validate a structural ledger; this public API never grants QAOA trust."""

    return _validate_final_measurement_observation_impl(
        record,
        case,
        registry,
        expected_observation_sha256=expected_observation_sha256,
        expected_registry_sha256=expected_registry_sha256,
        parent_qaoa_observation=parent_qaoa_observation,
        expected_parent_observation_sha256=expected_parent_observation_sha256,
    )


def _build_observation(
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
    family_id: str,
    source_arm: str,
    observation_budget: int,
    group_nonce: str,
    counts: Mapping[str, int] | Sequence[tuple[str, int]],
    generator_contract: GeneratorContractV2,
    qaoa_contract: QAOAFinalMeasurementContractV2 | None,
    qaoa_execution_class: str,
    parent_qaoa_observation_sha256: str | None = None,
    label_permutation_new_index_to_source_index: Sequence[int] = (),
) -> FinalMeasurementObservationV2:
    validate_frozen_shared_case(case)
    validate_split_registry_v2(
        registry, expected_registry_sha256=expected_registry_sha256
    )
    family = _strict_str(family_id, "family_id")
    entries = tuple(entry for entry in registry.entries if entry.family_id == family)
    if len(entries) != 1:
        raise ValueError("family_id is not uniquely registered")
    entry = entries[0]
    if entry.vector_sha256 != case.vector_sha256:
        raise ValueError("registry family does not bind this frozen vector")
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    nonce = _strict_str(group_nonce, "group_nonce")
    canonical_counts = _canonical_counts(counts)
    provisional = FinalMeasurementObservationV2(
        schema_version=FINAL_MEASUREMENT_REPLAY_V2_SCHEMA,
        source_arm=_strict_str(source_arm, "source_arm"),
        measurement_semantics=MEASUREMENT_SEMANTICS,
        count_bit_order=COUNT_BIT_ORDER,
        value_target_contract=VALUE_TARGET_CONTRACT,
        case_sha256=case.case_sha256,
        vector_sha256=case.vector_sha256,
        candidate_pool_sha256=case.candidate_pool_sha256,
        qubo_sha256=case.qubo_sha256,
        action_signatures=tuple(
            canonical_action_sha256(action) for action in case.actions
        ),
        whole_vector_cluster_id=whole_vector_cluster_id(case),
        family_id=family,
        orbit_cluster_sha256=entry.orbit_cluster_sha256,
        split_registry_sha256=registry.registry_sha256,
        group_nonce=nonce,
        group_id=replay_group_id_v2(
            case,
            entry,
            observation_budget=budget,
            group_nonce=nonce,
        ),
        split_role=entry.split_role,
        origin=entry.origin,
        observation_budget=budget,
        counts=canonical_counts,
        generator_contract=generator_contract,
        qaoa_contract=qaoa_contract,
        qaoa_execution_class=qaoa_execution_class,
        parent_qaoa_observation_sha256=_optional_sha256(
            parent_qaoa_observation_sha256,
            "parent_qaoa_observation_sha256",
        ),
        label_permutation_new_index_to_source_index=tuple(
            _strict_int(item, "label permutation entry", minimum=0)
            for item in label_permutation_new_index_to_source_index
        ),
        compute_budget_equal=False,
        performance_evidence=False,
        distribution_sha256="",
        observation_sha256="",
    )
    with_distribution = replace(
        provisional,
        distribution_sha256=_sha(_distribution_payload(provisional)),
    )
    return replace(
        with_distribution,
        observation_sha256=_sha(_observation_payload(with_distribution)),
    )


def build_classical_random_observation_v2(
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
    family_id: str,
    observation_budget: int,
    group_nonce: str,
    seed: int,
) -> FinalMeasurementObservationV2:
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    generator_seed = _strict_int(seed, "seed", minimum=0)
    contract = GeneratorContractV2(
        generator_id=GENERATOR_IDS["classical_random_bitstring_replay"],
        algorithm_version="v2",
        seed=generator_seed,
        deterministic_given_seed=True,
        final_distribution_only=True,
        optimizer_trajectory_included=False,
        source_payload_sha256=_sha(
            _random_source_payload(case, budget, generator_seed)
        ),
        compute_budget=ComputeBudgetV2(
            quantum_circuit_executions=0,
            statevector_expectation_evaluations=0,
            classical_candidate_evaluations=0,
            qubo_assignments_audited=0,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=budget,
            declared_wall_seconds=None,
            notes="canonical SHA-256 counter draws",
        ),
    )
    return _build_observation(
        case,
        registry,
        expected_registry_sha256=expected_registry_sha256,
        family_id=family_id,
        source_arm="classical_random_bitstring_replay",
        observation_budget=budget,
        group_nonce=group_nonce,
        counts=canonical_random_counts_v2(
            case, observation_budget=budget, seed=generator_seed
        ),
        generator_contract=contract,
        qaoa_contract=None,
        qaoa_execution_class=CLASSICAL_EXECUTION_CLASS,
    )


def build_classical_greedy_observation_v2(
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
    family_id: str,
    observation_budget: int,
    group_nonce: str,
    seed: int,
) -> FinalMeasurementObservationV2:
    budget = _strict_int(observation_budget, "observation_budget", minimum=1)
    generator_seed = _strict_int(seed, "seed", minimum=0)
    counts = canonical_greedy_counts_v2(case, observation_budget=budget)
    bits = _decode_count_key(counts[0][0], case.augmented_variable_count)
    contract = GeneratorContractV2(
        generator_id=GENERATOR_IDS[
            "classical_greedy_repeated_selection_replay"
        ],
        algorithm_version="v2",
        seed=generator_seed,
        deterministic_given_seed=True,
        final_distribution_only=True,
        optimizer_trajectory_included=False,
        source_payload_sha256=_sha(_greedy_source_payload(case, budget, bits)),
        compute_budget=_greedy_compute_budget_v2(case, budget),
    )
    return _build_observation(
        case,
        registry,
        expected_registry_sha256=expected_registry_sha256,
        family_id=family_id,
        source_arm="classical_greedy_repeated_selection_replay",
        observation_budget=budget,
        group_nonce=group_nonce,
        counts=counts,
        generator_contract=contract,
        qaoa_contract=None,
        qaoa_execution_class=CLASSICAL_EXECUTION_CLASS,
    )


def build_qaoa_final_measurement_observation_v2(
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
    family_id: str,
    group_nonce: str,
    counts: Mapping[str, int] | Sequence[tuple[str, int]],
    execution_class: str,
    final_parameter_payload_sha256: str | None,
    counts_source_sha256: str,
    source_trust: str = "unverified_development_ledger",
    source_attestation_sha256: str | None = None,
    compute_budget: ComputeBudgetV2,
) -> FinalMeasurementObservationV2:
    execution = _strict_str(execution_class, "execution_class")
    source_sha = _require_sha256(counts_source_sha256, "counts_source_sha256")
    budget = case.scheduler_config.qaoa_shots
    qaoa = QAOAFinalMeasurementContractV2(
        scheduler_seed=case.scheduler_config.qaoa_seed,
        shots=budget,
        p=case.scheduler_config.qaoa_p,
        optimizer_restarts=case.scheduler_config.qaoa_optimizer_restarts,
        optimizer_steps=case.scheduler_config.qaoa_optimizer_steps,
        final_parameter_payload_sha256=_optional_sha256(
            final_parameter_payload_sha256, "final_parameter_payload_sha256"
        ),
        counts_source_sha256=source_sha,
        source_trust=_strict_str(source_trust, "source_trust"),
        source_attestation_sha256=_optional_sha256(
            source_attestation_sha256, "source_attestation_sha256"
        ),
    )
    observed_count = sum(count for _, count in _canonical_counts(counts))
    structured_budget = compute_budget
    _validate_compute_budget(structured_budget)
    if structured_budget.bitstrings_generated != observed_count:
        raise ValueError("QAOA compute budget must match the observed count total")
    if structured_budget.qubo_assignments_audited != (
        1 << case.augmented_variable_count
    ):
        raise ValueError("QAOA compute budget must include the exhaustive QUBO audit")
    if structured_budget.greedy_candidate_scans_upper_bound != 0:
        raise ValueError("QAOA replay cannot report greedy candidate scans")
    if (
        execution.startswith("direct_")
        and structured_budget.statevector_expectation_evaluations < 1
    ):
        raise ValueError("direct QAOA must record statevector expectation work")
    generator = GeneratorContractV2(
        generator_id=GENERATOR_IDS["qaoa_final_measurement_replay"],
        algorithm_version="v2",
        seed=case.scheduler_config.qaoa_seed,
        deterministic_given_seed=True,
        final_distribution_only=True,
        optimizer_trajectory_included=False,
        source_payload_sha256=source_sha,
        compute_budget=structured_budget,
    )
    return _build_observation(
        case,
        registry,
        expected_registry_sha256=expected_registry_sha256,
        family_id=family_id,
        source_arm="qaoa_final_measurement_replay",
        observation_budget=budget,
        group_nonce=group_nonce,
        counts=counts,
        generator_contract=generator,
        qaoa_contract=qaoa,
        qaoa_execution_class=execution,
    )


def build_qaoa_permuted_label_control_v2(
    source_qaoa_observation: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_source_observation_sha256: str,
    expected_registry_sha256: str,
    permutation_seed: int,
) -> FinalMeasurementObservationV2:
    source_audit = validate_final_measurement_observation_v2(
        source_qaoa_observation,
        case,
        registry,
        expected_observation_sha256=expected_source_observation_sha256,
        expected_registry_sha256=expected_registry_sha256,
    )
    if source_qaoa_observation.source_arm != "qaoa_final_measurement_replay":
        raise ValueError("label control requires a QAOA source observation")
    seed = _strict_int(permutation_seed, "permutation_seed", minimum=0)
    permutation = deterministic_label_permutation_v2(
        len(case.actions),
        seed=seed,
        parent_observation_sha256=source_qaoa_observation.observation_sha256,
        candidate_pool_sha256=case.candidate_pool_sha256,
    )
    generator = GeneratorContractV2(
        generator_id=GENERATOR_IDS["qaoa_permuted_label_control"],
        algorithm_version="v2",
        seed=seed,
        deterministic_given_seed=True,
        final_distribution_only=True,
        optimizer_trajectory_included=False,
        source_payload_sha256=source_qaoa_observation.distribution_sha256,
        compute_budget=ComputeBudgetV2(
            quantum_circuit_executions=0,
            statevector_expectation_evaluations=0,
            classical_candidate_evaluations=len(case.actions),
            qubo_assignments_audited=0,
            greedy_candidate_scans_upper_bound=0,
            bitstrings_generated=0,
            declared_wall_seconds=None,
            notes="reuse QAOA observations and deterministically relabel actions",
        ),
    )
    record = _build_observation(
        case,
        registry,
        expected_registry_sha256=expected_registry_sha256,
        family_id=source_qaoa_observation.family_id,
        source_arm="qaoa_permuted_label_control",
        observation_budget=source_qaoa_observation.observation_budget,
        group_nonce=source_qaoa_observation.group_nonce,
        counts=source_qaoa_observation.counts,
        generator_contract=generator,
        qaoa_contract=source_qaoa_observation.qaoa_contract,
        qaoa_execution_class=source_qaoa_observation.qaoa_execution_class,
        parent_qaoa_observation_sha256=source_qaoa_observation.observation_sha256,
        label_permutation_new_index_to_source_index=permutation,
    )
    # Preserve an explicit read of source audit: construction is allowed even
    # when the source is structurally valid but not teacher-eligible.
    assert source_audit.structural_valid
    return record


def build_final_measurement_observation_v2(*args: object, **kwargs: object) -> FinalMeasurementObservationV2:
    """Fail closed against the former arbitrary-count constructor.

    Call one of the three source-specific builders above.  Keeping this name
    makes stale callers fail with an actionable message rather than silently
    self-signing arbitrary counts.
    """

    del args, kwargs
    raise TypeError(
        "use build_classical_random_observation_v2, "
        "build_classical_greedy_observation_v2, or "
        "build_qaoa_final_measurement_observation_v2"
    )


def derive_replay_targets_v2(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_observation_sha256: str,
    expected_registry_sha256: str,
    parent_qaoa_observation: FinalMeasurementObservationV2 | None = None,
    expected_parent_observation_sha256: str | None = None,
) -> ReplayTargetsV2:
    """Extract a classical teacher; QAOA uses the same-call external-lock API."""

    if record.source_arm in {
        "qaoa_final_measurement_replay",
        "qaoa_permuted_label_control",
    }:
        raise ValueError(
            "QAOA teacher extraction requires "
            "derive_qaoa_replay_targets_from_external_lock_v2"
        )
    audit = validate_final_measurement_observation_v2(
        record,
        case,
        registry,
        expected_observation_sha256=expected_observation_sha256,
        expected_registry_sha256=expected_registry_sha256,
        parent_qaoa_observation=parent_qaoa_observation,
        expected_parent_observation_sha256=expected_parent_observation_sha256,
    )
    return _replay_targets_from_audit(audit)


def _replay_targets_from_audit(audit: ReplayLedgerAuditV2) -> ReplayTargetsV2:
    if not audit.teacher_eligible:
        raise ValueError(
            "observation is ineligible for teacher extraction: "
            + ", ".join(audit.ineligibility_reasons)
        )
    return ReplayTargetsV2(
        observation_sha256=audit.observation_sha256,
        source_arm=audit.source_arm,
        action_signatures=audit.action_signatures,
        policy_target=audit.label_aligned_policy_target,
        policy_observation_weight=audit.policy_observation_weight,
        feasible_fraction=audit.feasible_fraction,
        value_observation_weight=audit.feasible_fraction,
        value_loss_weight_contract=(
            "trainer_must_multiply_each_observation_value_loss_by_"
            "value_observation_weight"
        ),
        value_target_log_ratio=audit.value_audit.value_target_log_ratio,
        value_audit=audit.value_audit,
        whole_vector_cluster_id=audit.whole_vector_cluster_id,
    )


def build_replay_group_manifest_v2(
    records: Sequence[FinalMeasurementObservationV2],
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_registry_sha256: str,
    protocol_sha256: str,
    source_manifest_sha256: str,
) -> ReplayGroupManifestV2:
    """Build a development manifest outside the trainer process.

    This helper is intentionally separate from teacher extraction.  The
    trainer contract forbids invoking it (or constructing an external lock) in
    the same training process that consumes replay targets.
    """

    records = tuple(records)
    if len(records) != len(SOURCE_ARMS):
        raise ValueError("group manifest requires exactly four observations")
    by_arm = {record.source_arm: record for record in records}
    if set(by_arm) != set(SOURCE_ARMS) or len(by_arm) != len(records):
        raise ValueError("group manifest requires each source arm exactly once")
    validate_split_registry_v2(
        registry, expected_registry_sha256=expected_registry_sha256
    )
    first = by_arm[SOURCE_ARMS[0]]
    common = (
        "group_id",
        "case_sha256",
        "candidate_pool_sha256",
        "family_id",
        "orbit_cluster_sha256",
        "split_registry_sha256",
        "split_role",
        "observation_budget",
    )
    for arm, record in by_arm.items():
        for field in common:
            if getattr(record, field) != getattr(first, field):
                raise ValueError(f"{arm} does not share group field {field}")
    qaoa = by_arm["qaoa_final_measurement_replay"]
    control = by_arm["qaoa_permuted_label_control"]
    if control.parent_qaoa_observation_sha256 != qaoa.observation_sha256:
        raise ValueError("group control parent binding is inconsistent")
    arm_observations = tuple(
        (arm, by_arm[arm].observation_sha256) for arm in SOURCE_ARMS
    )
    generator_shas = tuple(
        (arm, _generator_configuration_sha(by_arm[arm])) for arm in SOURCE_ARMS
    )
    source_shas = tuple(
        (arm, by_arm[arm].generator_contract.source_payload_sha256)
        for arm in SOURCE_ARMS
    )
    provisional = ReplayGroupManifestV2(
        schema_version=REPLAY_GROUP_MANIFEST_V2_SCHEMA,
        group_id=first.group_id,
        protocol_sha256=_require_sha256(protocol_sha256, "protocol_sha256"),
        source_manifest_sha256=_require_sha256(
            source_manifest_sha256, "source_manifest_sha256"
        ),
        split_registry_sha256=registry.registry_sha256,
        case_sha256=case.case_sha256,
        candidate_pool_sha256=case.candidate_pool_sha256,
        family_id=first.family_id,
        orbit_cluster_sha256=first.orbit_cluster_sha256,
        split_role=first.split_role,
        arm_observation_sha256=arm_observations,
        parent_bindings=((
            "qaoa_permuted_label_control",
            "qaoa_final_measurement_replay",
            qaoa.observation_sha256,
        ),),
        generator_configuration_sha256=generator_shas,
        source_payload_sha256=source_shas,
        manifest_sha256="",
    )
    return replace(
        provisional, manifest_sha256=_sha(_manifest_payload(provisional))
    )


def validate_replay_group_manifest_v2(
    manifest: ReplayGroupManifestV2,
    records: Sequence[FinalMeasurementObservationV2],
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_manifest_sha256: str,
) -> dict[str, ReplayLedgerAuditV2]:
    """Validate coordinated artifacts against one independent manifest anchor."""

    if not isinstance(manifest, ReplayGroupManifestV2):
        raise TypeError("manifest must be a ReplayGroupManifestV2")
    external = _require_sha256(
        expected_manifest_sha256, "expected_manifest_sha256"
    )
    parsed = ReplayGroupManifestV2.from_dict(manifest.to_dict())
    if parsed.schema_version != REPLAY_GROUP_MANIFEST_V2_SCHEMA:
        raise ValueError("unsupported replay group manifest schema")
    if parsed.manifest_sha256 != _sha(_manifest_payload(parsed)):
        raise ValueError("group manifest canonical SHA mismatch")
    if parsed.manifest_sha256 != external:
        raise ValueError("group manifest SHA does not match external anchor")
    validate_split_registry_v2(
        registry, expected_registry_sha256=parsed.split_registry_sha256
    )
    if parsed.case_sha256 != case.case_sha256:
        raise ValueError("manifest case SHA mismatch")
    if parsed.candidate_pool_sha256 != case.candidate_pool_sha256:
        raise ValueError("manifest candidate pool SHA mismatch")
    records = tuple(records)
    by_arm = {record.source_arm: record for record in records}
    if len(records) != len(SOURCE_ARMS) or set(by_arm) != set(SOURCE_ARMS):
        raise ValueError("manifest validation requires all four unique arms")
    expected_observations = dict(parsed.arm_observation_sha256)
    if tuple(expected_observations) != SOURCE_ARMS:
        raise ValueError("manifest arm observation order changed")
    expected_generators = dict(parsed.generator_configuration_sha256)
    expected_sources = dict(parsed.source_payload_sha256)
    if tuple(expected_generators) != SOURCE_ARMS or tuple(expected_sources) != SOURCE_ARMS:
        raise ValueError("manifest generator/source arm order changed")
    qaoa = by_arm["qaoa_final_measurement_replay"]
    expected_parent = ((
        "qaoa_permuted_label_control",
        "qaoa_final_measurement_replay",
        qaoa.observation_sha256,
    ),)
    if parsed.parent_bindings != expected_parent:
        raise ValueError("manifest parent binding changed")
    audits: dict[str, ReplayLedgerAuditV2] = {}
    for arm in SOURCE_ARMS:
        record = by_arm[arm]
        if _generator_configuration_sha(record) != expected_generators[arm]:
            raise ValueError(f"{arm} generator configuration SHA mismatch")
        if record.generator_contract.source_payload_sha256 != expected_sources[arm]:
            raise ValueError(f"{arm} source payload SHA mismatch")
        kwargs: dict[str, object] = {}
        if arm == "qaoa_permuted_label_control":
            kwargs = {
                "parent_qaoa_observation": qaoa,
                "expected_parent_observation_sha256": expected_observations[
                    "qaoa_final_measurement_replay"
                ],
            }
        audits[arm] = validate_final_measurement_observation_v2(
            record,
            case,
            registry,
            expected_observation_sha256=expected_observations[arm],
            expected_registry_sha256=parsed.split_registry_sha256,
            **kwargs,  # type: ignore[arg-type]
        )
    first = by_arm[SOURCE_ARMS[0]]
    for field in (
        "group_id",
        "case_sha256",
        "candidate_pool_sha256",
        "family_id",
        "orbit_cluster_sha256",
        "split_registry_sha256",
        "split_role",
        "observation_budget",
    ):
        if getattr(first, field) != getattr(parsed, field, getattr(first, field)):
            raise ValueError(f"manifest group field {field} mismatch")
        if any(getattr(record, field) != getattr(first, field) for record in records):
            raise ValueError(f"observations disagree on group field {field}")
    return audits


def validate_external_replay_lock_v2(
    lock: ExternalReplayLockV2,
    manifest: ReplayGroupManifestV2,
    records: Sequence[FinalMeasurementObservationV2],
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_lock_sha256: str,
    qaoa_counts_payload: bytes,
    final_parameter_payload: bytes,
    run_attestation: bytes,
) -> _ValidatedReplayGroupV2:
    """Validate an external lock and actual payload bytes for immediate use.

    This validator consumes a lock that must already exist outside the trainer
    process.  It intentionally provides no lock builder.  The authority label
    means a local pre-seal anchor, not a cryptographic signature.  A future
    formal workflow must persist the lock in an independent file or commit
    before training.  The returned object is an internal same-call result, not
    an unforgeable Python capability and not a public trainer input.
    """

    if not isinstance(lock, ExternalReplayLockV2):
        raise TypeError("lock must be an ExternalReplayLockV2")
    external_lock_sha = _require_sha256(
        expected_lock_sha256, "expected_lock_sha256"
    )
    for name, payload in (
        ("qaoa_counts_payload", qaoa_counts_payload),
        ("final_parameter_payload", final_parameter_payload),
        ("run_attestation", run_attestation),
    ):
        if type(payload) is not bytes:
            raise TypeError(f"{name} must be native bytes")
    parsed = ExternalReplayLockV2.from_mapping(lock.to_dict())
    if parsed.schema_version != EXTERNAL_REPLAY_LOCK_V2_SCHEMA:
        raise ValueError("unsupported external replay lock schema")
    if parsed.authority != EXTERNAL_LOCK_AUTHORITY:
        raise ValueError(
            "external lock authority must be local_preseal_external_lock; it is not a signature"
        )
    expected_canonical_lock = _sha(_external_lock_payload(parsed))
    if parsed.lock_sha256 != expected_canonical_lock:
        raise ValueError("external replay lock canonical SHA mismatch")
    if parsed.lock_sha256 != external_lock_sha:
        raise ValueError("external replay lock SHA does not match independent anchor")
    expected_lock_bindings = {
        "manifest_sha256": manifest.manifest_sha256,
        "split_registry_sha256": registry.registry_sha256,
        "protocol_sha256": manifest.protocol_sha256,
        "source_manifest_sha256": manifest.source_manifest_sha256,
    }
    for name, expected in expected_lock_bindings.items():
        if getattr(parsed, name) != expected:
            raise ValueError(f"external replay lock {name} binding mismatch")

    structural_audits = validate_replay_group_manifest_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=parsed.manifest_sha256,
    )
    by_arm = {record.source_arm: record for record in records}
    qaoa = by_arm["qaoa_final_measurement_replay"]
    control = by_arm["qaoa_permuted_label_control"]
    if parsed.qaoa_observation_sha256 != qaoa.observation_sha256:
        raise ValueError("external lock QAOA observation binding mismatch")
    if parsed.qaoa_control_observation_sha256 != control.observation_sha256:
        raise ValueError("external lock QAOA control binding mismatch")
    qaoa_contract = qaoa.qaoa_contract
    if qaoa_contract is None:
        raise ValueError("external lock requires a QAOA contract")
    if qaoa.qaoa_execution_class != "direct_unrepaired":
        raise ValueError("external trainer lock requires direct_unrepaired QAOA")
    expected_counts_bytes = qaoa_counts_payload_bytes_v2(
        case, qaoa.counts, execution_class=qaoa.qaoa_execution_class
    )
    if qaoa_counts_payload != expected_counts_bytes:
        raise ValueError("actual QAOA counts payload bytes do not match the record")
    actual_payload_shas = {
        "qaoa_counts_payload_sha256": sha256_bytes(qaoa_counts_payload),
        "qaoa_final_parameter_payload_sha256": sha256_bytes(
            final_parameter_payload
        ),
        "qaoa_run_attestation_sha256": sha256_bytes(run_attestation),
    }
    for name, actual in actual_payload_shas.items():
        if getattr(parsed, name) != actual:
            raise ValueError(f"actual {name} does not match external lock")
    if qaoa_contract.counts_source_sha256 != actual_payload_shas[
        "qaoa_counts_payload_sha256"
    ]:
        raise ValueError("QAOA record counts-source SHA does not match actual bytes")
    if qaoa_contract.final_parameter_payload_sha256 != actual_payload_shas[
        "qaoa_final_parameter_payload_sha256"
    ]:
        raise ValueError("QAOA final-parameter SHA does not match actual bytes")
    if qaoa_contract.source_attestation_sha256 != actual_payload_shas[
        "qaoa_run_attestation_sha256"
    ]:
        raise ValueError("QAOA run-attestation SHA does not match actual bytes")
    if control.qaoa_contract != qaoa_contract:
        raise ValueError("QAOA control did not retain the externally locked contract")

    trusted_audits = dict(structural_audits)
    trusted_source_sha = actual_payload_shas["qaoa_counts_payload_sha256"]
    trusted_audits["qaoa_final_measurement_replay"] = (
        _validate_final_measurement_observation_impl(
            qaoa,
            case,
            registry,
            expected_observation_sha256=qaoa.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            trusted_qaoa_counts_source_sha256=trusted_source_sha,
        )
    )
    trusted_audits["qaoa_permuted_label_control"] = (
        _validate_final_measurement_observation_impl(
            control,
            case,
            registry,
            expected_observation_sha256=control.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
            trusted_qaoa_counts_source_sha256=trusted_source_sha,
            parent_qaoa_observation=qaoa,
            expected_parent_observation_sha256=qaoa.observation_sha256,
        )
    )
    return _ValidatedReplayGroupV2(
        lock_sha256=parsed.lock_sha256,
        manifest_sha256=manifest.manifest_sha256,
        case_sha256=case.case_sha256,
        split_registry_sha256=registry.registry_sha256,
        arm_observation_sha256=manifest.arm_observation_sha256,
        audits=tuple((arm, trusted_audits[arm]) for arm in SOURCE_ARMS),
        _token=_VALIDATED_REPLAY_GROUP_TOKEN,
    )


def derive_qaoa_replay_targets_from_external_lock_v2(
    record: FinalMeasurementObservationV2,
    manifest: ReplayGroupManifestV2,
    records: Sequence[FinalMeasurementObservationV2],
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_observation_sha256: str,
    expected_registry_sha256: str,
    lock: ExternalReplayLockV2,
    expected_lock_sha256: str,
    qaoa_counts_payload: bytes,
    final_parameter_payload: bytes,
    run_attestation: bytes,
) -> ReplayTargetsV2:
    """Validate the external trust root and immediately derive a QAOA teacher.

    No pre-built Python capability is accepted.  A future trainer must obtain
    ``expected_lock_sha256`` from a read-only file, commit, or signature root
    outside the training process rather than deriving it from ``lock``.
    """

    if record.source_arm not in {
        "qaoa_final_measurement_replay",
        "qaoa_permuted_label_control",
    }:
        raise ValueError("external-lock QAOA teacher API accepts only QAOA arms")
    validated = validate_external_replay_lock_v2(
        lock,
        manifest,
        records,
        case,
        registry,
        expected_lock_sha256=expected_lock_sha256,
        qaoa_counts_payload=qaoa_counts_payload,
        final_parameter_payload=final_parameter_payload,
        run_attestation=run_attestation,
    )
    audit = validated.audit_for(
        record,
        case,
        registry,
        expected_observation_sha256=expected_observation_sha256,
        expected_registry_sha256=expected_registry_sha256,
    )
    return _replay_targets_from_audit(audit)


def audit_equal_observation_group_v2(
    manifest: ReplayGroupManifestV2,
    records: Sequence[FinalMeasurementObservationV2],
    case: FrozenSharedCase,
    registry: SplitRegistryV2,
    *,
    expected_manifest_sha256: str,
) -> EqualObservationGroupAuditV2:
    """Audit structure for all arms; eligibility is reported, never required."""

    audits = validate_replay_group_manifest_v2(
        manifest,
        records,
        case,
        registry,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    by_arm = {record.source_arm: record for record in records}
    qaoa = by_arm["qaoa_final_measurement_replay"]
    control = by_arm["qaoa_permuted_label_control"]
    counts_identical = qaoa.counts == control.counts
    distributions_identical = qaoa.distribution_sha256 == control.distribution_sha256
    if not counts_identical or not distributions_identical:
        raise ValueError("label control did not reuse exact QAOA observations")
    permutation = control.label_permutation_new_index_to_source_index
    nonidentity = permutation != tuple(range(len(permutation)))
    effective = (
        audits["qaoa_final_measurement_replay"].source_policy_target
        != audits["qaoa_permuted_label_control"].label_aligned_policy_target
    )
    first = by_arm[SOURCE_ARMS[0]]
    return EqualObservationGroupAuditV2(
        manifest_sha256=manifest.manifest_sha256,
        group_id=manifest.group_id,
        source_arms=SOURCE_ARMS,
        declared_observation_budget=first.observation_budget,
        total_observed_by_arm=tuple(
            (arm, audits[arm].total_observed) for arm in SOURCE_ARMS
        ),
        observation_budget_complete_by_arm=tuple(
            (arm, audits[arm].observation_budget_complete) for arm in SOURCE_ARMS
        ),
        eligible_arms=tuple(
            arm for arm in SOURCE_ARMS if audits[arm].teacher_eligible
        ),
        ineligible_reasons_by_arm=tuple(
            (arm, audits[arm].ineligibility_reasons)
            for arm in SOURCE_ARMS
            if not audits[arm].teacher_eligible
        ),
        qaoa_counts_identical_to_control=counts_identical,
        qaoa_distribution_sha_identical_to_control=distributions_identical,
        label_permutation_nonidentity=nonidentity,
        permuted_policy_effective=effective,
        whole_vector_cluster_id=first.whole_vector_cluster_id,
    )


__all__ = [
    "CLASSICAL_EXECUTION_CLASS",
    "COUNT_BIT_ORDER",
    "EXTERNAL_LOCK_AUTHORITY",
    "EXTERNAL_REPLAY_LOCK_V2_SCHEMA",
    "FINAL_MEASUREMENT_REPLAY_V2_SCHEMA",
    "GENERATOR_IDS",
    "MEASUREMENT_SEMANTICS",
    "ORBIT_SEMANTICS",
    "ORBIT_MAX_INPUT_COUNT",
    "ORBIT_MAX_OUTPUT_COUNT",
    "ORBIT_MAX_TOTAL_TERMS",
    "QAOA_EXECUTION_CLASSES",
    "QAOA_SOURCE_TRUST_LEVELS",
    "REPLAY_GROUP_MANIFEST_V2_SCHEMA",
    "SOURCE_ARMS",
    "SPLIT_REGISTRY_V2_SCHEMA",
    "SPLIT_ROLES",
    "TRAIN_SPLIT_ROLE",
    "TRAINER_REPLAY_CONTRACT",
    "VALUE_TARGET_CONTRACT",
    "BitstringAuditV2",
    "ComputeBudgetV2",
    "EqualObservationGroupAuditV2",
    "ExternalReplayLockV2",
    "FinalMeasurementObservationV2",
    "GeneratorContractV2",
    "ObservationOriginV2",
    "QAOAFinalMeasurementContractV2",
    "ReplayGroupManifestV2",
    "ReplayLedgerAuditV2",
    "ReplayTargetsV2",
    "SignedValueAuditV2",
    "SplitRegistryEntryV2",
    "SplitRegistrySourceV2",
    "SplitRegistryV2",
    "audit_equal_observation_group_v2",
    "build_classical_greedy_observation_v2",
    "build_classical_random_observation_v2",
    "build_final_measurement_observation_v2",
    "build_qaoa_final_measurement_observation_v2",
    "build_qaoa_permuted_label_control_v2",
    "build_replay_group_manifest_v2",
    "build_split_registry_v2",
    "canonical_greedy_counts_v2",
    "canonical_random_counts_v2",
    "canonical_vector_orbit_sha256",
    "derive_replay_targets_v2",
    "derive_qaoa_replay_targets_from_external_lock_v2",
    "deterministic_label_permutation_v2",
    "deterministic_nonidentity_label_permutation",
    "qaoa_counts_payload_bytes_v2",
    "replay_group_id_v2",
    "validate_final_measurement_observation_v2",
    "validate_external_replay_lock_v2",
    "validate_replay_group_manifest_v2",
    "validate_split_registry_v2",
    "whole_vector_cluster_id",
]
