"""Resource-gain-weighted replay teachers for the isolated E6 D2 study.

The existing replay ledger remains the observation source.  This module only
changes how a *validated feasible final bitstring* contributes policy credit:

``gain(S) = max(0, 1 - score(S) / score(empty))``

and action ``i`` receives ``count * gain(S)`` iff ``i`` is selected by that
bitstring.  Harmful, tied, infeasible, and dummy-only observations therefore
add no policy mass.  There is deliberately no uniform or raw-utility fallback:
zero total credit is an explicit ineligible result.

The QAOA label control is formed only after the source target has been fully
derived.  Its credit and probability vectors are exact applications of the
already-recorded ``new_index -> source_index`` permutation; resource scores
are never recomputed under control labels.

This is a deterministic pure derivation layer.  It does not train, persist,
seal, or bless a model or replay artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import TYPE_CHECKING, Sequence

from e6.final_measurement_replay_v2 import (
    SOURCE_ARMS,
    TRAINER_REPLAY_CONTRACT,
    BitstringAuditV2,
    ExternalReplayLockV2,
    FinalMeasurementObservationV2,
    ReplayLedgerAuditV2,
    ReplayTargetsV2,
    SplitRegistryV2,
    validate_external_replay_lock_v2,
)
from e6.frozen_case import (
    FrozenSharedCase,
    canonical_action_sha256,
    validate_frozen_shared_case,
)
from e6.shared_oracle import emit_shared_oracle
from e6.shared_scheduler import program_resource_summary
from src.contracts.codec import canonical_json_bytes, sha256_bytes

if TYPE_CHECKING:
    from e6.replay_training_corpus_v1 import ReplayTrainingGroupV1


RESOURCE_GAIN_POLICY_AUDIT_V1_SCHEMA = (
    "xa.e6-resource-gain-policy-audit.v1-development"
)
RESOURCE_GAIN_REPLAY_TARGET_V1_SCHEMA = (
    "xa.e6-resource-gain-replay-target.v1-development"
)
RESOURCE_GAIN_REPLAY_TEACHER_PAIR_V1_SCHEMA = (
    "xa.e6-resource-gain-replay-teacher-pair.v1-development"
)
RESOURCE_GAIN_FORMULA = "max(0,1-selected_program_score/direct_program_score)"
POLICY_WEIGHT_FORMULA = (
    "sum_action_credit/(total_observed*effective_real_action_budget)"
)

_SOURCE_ARM = "qaoa_final_measurement_replay"
_CONTROL_ARM = "qaoa_permuted_label_control"
_VALUE_LOSS_WEIGHT_CONTRACT = (
    "trainer_must_multiply_each_observation_value_loss_by_"
    "value_observation_weight"
)


def _native_finite(value: object, name: str, *, minimum: float | None = None) -> float:
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a native finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and converted < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return converted


def _native_int(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1.0e-12)


def _validate_observation_sha(record: FinalMeasurementObservationV2) -> None:
    if type(record) is not FinalMeasurementObservationV2:
        raise TypeError("record must be exact FinalMeasurementObservationV2")
    payload = record.to_dict()
    payload.pop("observation_sha256")
    expected = sha256_bytes(canonical_json_bytes(payload))
    if record.observation_sha256 != expected:
        raise ValueError("observation canonical SHA mismatch")


def _program_score(case: FrozenSharedCase, selected: Sequence[int]) -> float:
    selected_actions = tuple(case.actions[index] for index in selected)
    score = float(
        program_resource_summary(
            emit_shared_oracle(case.vector, selected_actions),
            weights=case.utility_weights,
        ).total_abstract_score
    )
    if not math.isfinite(score) or score < 0.0:
        raise ValueError("program resource score must be finite and non-negative")
    return score


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


@dataclass(frozen=True)
class ResourceGainBitstringDiagnosticV1:
    bitstring: tuple[int, ...]
    count: int
    feasible: bool
    source_selected_real_indices: tuple[int, ...]
    dummy_selected: int
    selected_program_score: float | None
    score_ratio: float | None
    resource_gain: float
    gain_weighted_observation_count: float

    def to_dict(self) -> dict[str, object]:
        return {
            "bitstring": list(self.bitstring),
            "count": self.count,
            "feasible": self.feasible,
            "source_selected_real_indices": list(
                self.source_selected_real_indices
            ),
            "dummy_selected": self.dummy_selected,
            "selected_program_score": self.selected_program_score,
            "score_ratio": self.score_ratio,
            "resource_gain": self.resource_gain,
            "gain_weighted_observation_count": (
                self.gain_weighted_observation_count
            ),
        }


@dataclass(frozen=True)
class ResourceGainPolicyAuditV1:
    schema_version: str
    gain_formula: str
    policy_weight_formula: str
    eligible: bool
    ineligibility_reasons: tuple[str, ...]
    action_credits: tuple[float, ...]
    policy_target: tuple[float, ...]
    policy_observation_weight: float
    total_action_credit: float
    total_observed: int
    effective_real_action_budget: int
    direct_program_score: float
    feasible_observed: int
    infeasible_observed: int
    positive_gain_observed: int
    positive_gain_bitstring_count: int
    zero_gain_feasible_observed: int
    gain_weighted_observation_count: float
    mean_resource_gain_per_observation: float
    max_resource_gain: float
    bitstring_diagnostics: tuple[ResourceGainBitstringDiagnosticV1, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "gain_formula": self.gain_formula,
            "policy_weight_formula": self.policy_weight_formula,
            "eligible": self.eligible,
            "ineligibility_reasons": list(self.ineligibility_reasons),
            "action_credits": list(self.action_credits),
            "policy_target": list(self.policy_target),
            "policy_observation_weight": self.policy_observation_weight,
            "total_action_credit": self.total_action_credit,
            "total_observed": self.total_observed,
            "effective_real_action_budget": self.effective_real_action_budget,
            "direct_program_score": self.direct_program_score,
            "feasible_observed": self.feasible_observed,
            "infeasible_observed": self.infeasible_observed,
            "positive_gain_observed": self.positive_gain_observed,
            "positive_gain_bitstring_count": self.positive_gain_bitstring_count,
            "zero_gain_feasible_observed": self.zero_gain_feasible_observed,
            "gain_weighted_observation_count": (
                self.gain_weighted_observation_count
            ),
            "mean_resource_gain_per_observation": (
                self.mean_resource_gain_per_observation
            ),
            "max_resource_gain": self.max_resource_gain,
            "bitstring_diagnostics": [
                item.to_dict() for item in self.bitstring_diagnostics
            ],
        }


@dataclass(frozen=True)
class ResourceGainReplayTargetV1:
    schema_version: str
    source_arm: str
    target_role: str
    observation_sha256: str
    action_signatures: tuple[str, ...]
    eligible: bool
    ineligibility_reasons: tuple[str, ...]
    action_credits: tuple[float, ...]
    policy_target: tuple[float, ...]
    policy_observation_weight: float

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_arm": self.source_arm,
            "target_role": self.target_role,
            "observation_sha256": self.observation_sha256,
            "action_signatures": list(self.action_signatures),
            "eligible": self.eligible,
            "ineligibility_reasons": list(self.ineligibility_reasons),
            "action_credits": list(self.action_credits),
            "policy_target": list(self.policy_target),
            "policy_observation_weight": self.policy_observation_weight,
        }


@dataclass(frozen=True)
class ResourceGainReplayTeacherPairV1:
    schema_version: str
    group_id: str
    case_sha256: str
    candidate_pool_sha256: str
    label_permutation_new_index_to_source_index: tuple[int, ...]
    source: ResourceGainReplayTargetV1
    control: ResourceGainReplayTargetV1
    source_replay_target: ReplayTargetsV2 | None
    control_replay_target: ReplayTargetsV2 | None
    policy_audit: ResourceGainPolicyAuditV1
    control_is_exact_source_permutation: bool
    permuted_target_changed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "group_id": self.group_id,
            "case_sha256": self.case_sha256,
            "candidate_pool_sha256": self.candidate_pool_sha256,
            "label_permutation_new_index_to_source_index": list(
                self.label_permutation_new_index_to_source_index
            ),
            "source": self.source.to_dict(),
            "control": self.control.to_dict(),
            "source_replay_target": (
                None
                if self.source_replay_target is None
                else self.source_replay_target.to_dict()
            ),
            "control_replay_target": (
                None
                if self.control_replay_target is None
                else self.control_replay_target.to_dict()
            ),
            "policy_audit": self.policy_audit.to_dict(),
            "control_is_exact_source_permutation": (
                self.control_is_exact_source_permutation
            ),
            "permuted_target_changed": self.permuted_target_changed,
        }


@dataclass(frozen=True)
class ResourceGainReplayTeacherV1:
    """One source-arm derivation plus its optional trainer-ready projection."""

    target: ResourceGainReplayTargetV1
    policy_audit: ResourceGainPolicyAuditV1
    replay_target: ReplayTargetsV2 | None

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target.to_dict(),
            "policy_audit": self.policy_audit.to_dict(),
            "replay_target": (
                None if self.replay_target is None else self.replay_target.to_dict()
            ),
        }


def _validate_bitstring_rows(
    case: FrozenSharedCase,
    rows: tuple[BitstringAuditV2, ...],
    *,
    total_observed: int,
    permutation: tuple[int, ...] = (),
) -> None:
    if type(rows) is not tuple:
        raise TypeError("bitstring_audit must be a native tuple")
    total = _native_int(total_observed, "total_observed")
    action_count = len(case.actions)
    if permutation:
        if type(permutation) is not tuple:
            raise TypeError("permutation must be a native tuple")
        if any(type(index) is not int for index in permutation):
            raise TypeError("permutation entries must be native integers")
        if len(permutation) != action_count or set(permutation) != set(
            range(action_count)
        ):
            raise ValueError("permutation must be an action-aligned bijection")
    elif permutation != ():
        raise TypeError("permutation must be a native tuple")

    bitstrings: list[tuple[int, ...]] = []
    observed = 0
    for row_index, row in enumerate(rows):
        if type(row) is not BitstringAuditV2:
            raise TypeError(
                f"bitstring_audit[{row_index}] must be exact BitstringAuditV2"
            )
        bits = row.bitstring
        if type(bits) is not tuple or len(bits) != case.qubo.variable_count:
            raise ValueError("bitstring audit row has the wrong variable width")
        if any(type(bit) is not int or bit not in {0, 1} for bit in bits):
            raise TypeError("bitstring audit bits must be native binary integers")
        count = _native_int(row.count, f"bitstring_audit[{row_index}].count", minimum=1)
        selected = case.qubo.selected_real(bits)
        expected_aligned = _aligned_indices(selected, permutation)
        expected_dummy = sum(bits[action_count:])
        expected_conflicts = case.qubo.conflict_count(bits)
        expected_feasible = case.qubo.is_feasible(bits)
        expected_phase = float(case.qubo.phase_energy(bits))
        if row.cardinality != sum(bits):
            raise ValueError("bitstring audit cardinality changed")
        if row.source_selected_real_indices != selected:
            raise ValueError("bitstring audit source selection changed")
        if row.label_aligned_selected_real_indices != expected_aligned:
            raise ValueError("bitstring audit aligned selection changed")
        if row.dummy_selected != expected_dummy:
            raise ValueError("bitstring audit dummy count changed")
        if row.conflict_count != expected_conflicts:
            raise ValueError("bitstring audit conflict count changed")
        if type(row.feasible) is not bool or row.feasible != expected_feasible:
            raise ValueError("bitstring audit feasibility changed")
        observed_phase = _native_finite(
            row.phase_energy, f"bitstring_audit[{row_index}].phase_energy"
        )
        if observed_phase != expected_phase:
            raise ValueError("bitstring audit phase energy changed")
        bitstrings.append(bits)
        observed += count
    if tuple(bitstrings) != tuple(sorted(bitstrings)):
        raise ValueError("bitstring audit rows must use canonical bitstring order")
    if len(set(bitstrings)) != len(bitstrings):
        raise ValueError("bitstring audit contains duplicate bitstrings")
    if observed != total:
        raise ValueError("bitstring audit counts do not sum to total_observed")


def derive_resource_gain_policy_from_bitstring_audit_v1(
    case: FrozenSharedCase,
    bitstring_audit: tuple[BitstringAuditV2, ...],
    *,
    total_observed: int,
) -> ResourceGainPolicyAuditV1:
    """Derive one arm-neutral gain-weighted policy from exact audit rows.

    ``total_observed`` includes feasible, infeasible, and dummy-only rows.  The
    observation weight denominator is exactly
    ``total_observed * case.budget_effective``.  An ineligible result carries
    aligned zero credits, an empty policy target, and zero weight.
    """

    if type(case) is not FrozenSharedCase:
        raise TypeError("case must be exact FrozenSharedCase")
    validate_frozen_shared_case(case)
    total = _native_int(total_observed, "total_observed")
    rows = bitstring_audit
    _validate_bitstring_rows(case, rows, total_observed=total)

    direct_score = _program_score(case, ())
    credits = [0.0] * len(case.actions)
    diagnostics: list[ResourceGainBitstringDiagnosticV1] = []
    feasible_observed = 0
    positive_gain_observed = 0
    positive_gain_bitstrings = 0
    zero_gain_feasible_observed = 0
    weighted_gains: list[float] = []
    max_gain = 0.0

    for row in rows:
        selected_score: float | None = None
        ratio: float | None = None
        gain = 0.0
        if row.feasible:
            feasible_observed += row.count
            selected_score = _program_score(
                case, row.source_selected_real_indices
            )
            if direct_score > 0.0:
                ratio = selected_score / direct_score
                gain = float(max(0.0, 1.0 - ratio))
            if not math.isfinite(gain) or not 0.0 <= gain <= 1.0:
                raise RuntimeError("derived resource gain left [0, 1]")
            if gain > 0.0:
                positive_gain_observed += row.count
                positive_gain_bitstrings += 1
                weighted = float(row.count * gain)
                weighted_gains.append(weighted)
                max_gain = max(max_gain, gain)
                for action_index in row.source_selected_real_indices:
                    credits[action_index] = math.fsum(
                        (credits[action_index], weighted)
                    )
            else:
                zero_gain_feasible_observed += row.count
        diagnostics.append(
            ResourceGainBitstringDiagnosticV1(
                bitstring=row.bitstring,
                count=row.count,
                feasible=row.feasible,
                source_selected_real_indices=row.source_selected_real_indices,
                dummy_selected=row.dummy_selected,
                selected_program_score=selected_score,
                score_ratio=ratio,
                resource_gain=gain,
                gain_weighted_observation_count=float(row.count * gain),
            )
        )

    action_credits = tuple(float(value) for value in credits)
    total_credit = float(math.fsum(action_credits))
    gain_weighted_count = float(math.fsum(weighted_gains))
    reasons: list[str] = []
    if total == 0:
        reasons.append("no_observations")
    if case.budget_effective == 0:
        reasons.append("zero_effective_real_action_budget")
    if direct_score <= 0.0:
        reasons.append("nonpositive_direct_program_score")
    if feasible_observed == 0:
        reasons.append("no_feasible_observations")
    if total_credit <= 0.0:
        reasons.append("no_positive_resource_gain_credit")
    eligible = not reasons
    if eligible:
        policy = tuple(float(value / total_credit) for value in action_credits)
        denominator = total * case.budget_effective
        weight = float(total_credit / denominator)
        if not _close(math.fsum(policy), 1.0):
            raise RuntimeError("resource-gain policy does not sum to one")
        if not math.isfinite(weight) or not 0.0 < weight <= 1.0:
            raise RuntimeError("resource-gain policy weight left (0, 1]")
    else:
        policy = ()
        weight = 0.0

    infeasible_observed = total - feasible_observed
    mean_gain = 0.0 if total == 0 else float(gain_weighted_count / total)
    return ResourceGainPolicyAuditV1(
        schema_version=RESOURCE_GAIN_POLICY_AUDIT_V1_SCHEMA,
        gain_formula=RESOURCE_GAIN_FORMULA,
        policy_weight_formula=POLICY_WEIGHT_FORMULA,
        eligible=eligible,
        ineligibility_reasons=tuple(reasons),
        action_credits=action_credits,
        policy_target=policy,
        policy_observation_weight=weight,
        total_action_credit=total_credit,
        total_observed=total,
        effective_real_action_budget=case.budget_effective,
        direct_program_score=direct_score,
        feasible_observed=feasible_observed,
        infeasible_observed=infeasible_observed,
        positive_gain_observed=positive_gain_observed,
        positive_gain_bitstring_count=positive_gain_bitstrings,
        zero_gain_feasible_observed=zero_gain_feasible_observed,
        gain_weighted_observation_count=gain_weighted_count,
        mean_resource_gain_per_observation=mean_gain,
        max_resource_gain=float(max_gain),
        bitstring_diagnostics=tuple(diagnostics),
    )


def _bitstring_rows_from_record(
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
) -> tuple[BitstringAuditV2, ...]:
    if type(record.counts) is not tuple:
        raise TypeError("observation counts must be a native tuple")
    if record.counts != tuple(sorted(record.counts)):
        raise ValueError("observation counts must use canonical bitstring order")
    if len({key for key, _ in record.counts}) != len(record.counts):
        raise ValueError("observation counts contain duplicate bitstrings")
    rows: list[BitstringAuditV2] = []
    for row_index, (key, count) in enumerate(record.counts):
        if type(key) is not str:
            raise TypeError(f"observation counts[{row_index}] key must be native str")
        if len(key) != case.qubo.variable_count or any(bit not in "01" for bit in key):
            raise ValueError("observation count key has invalid binary width")
        observed_count = _native_int(
            count, f"observation counts[{row_index}] count", minimum=1
        )
        bits = tuple(int(bit) for bit in key)
        selected = case.qubo.selected_real(bits)
        permutation = record.label_permutation_new_index_to_source_index
        rows.append(
            BitstringAuditV2(
                bitstring=bits,
                count=observed_count,
                cardinality=sum(bits),
                source_selected_real_indices=selected,
                label_aligned_selected_real_indices=_aligned_indices(
                    selected, permutation
                ),
                dummy_selected=sum(bits[len(case.actions) :]),
                conflict_count=case.qubo.conflict_count(bits),
                feasible=case.qubo.is_feasible(bits),
                phase_energy=float(case.qubo.phase_energy(bits)),
            )
        )
    return tuple(rows)


def derive_resource_gain_replay_target_v1(
    *,
    record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    legacy_target: ReplayTargetsV2,
) -> ResourceGainReplayTeacherV1:
    """Derive one trainer-ready source target after same-call validation.

    This narrow adapter is intended for a trainer that has already obtained
    ``legacy_target`` by validating the external replay lock in the same call.
    It accepts only the QAOA source arm.  A zero-gain result has
    ``target.eligible == False`` and ``replay_target is None``.
    """

    if type(record) is not FinalMeasurementObservationV2:
        raise TypeError("record must be exact FinalMeasurementObservationV2")
    if type(case) is not FrozenSharedCase:
        raise TypeError("case must be exact FrozenSharedCase")
    if type(legacy_target) is not ReplayTargetsV2:
        raise TypeError("legacy_target must be exact ReplayTargetsV2")
    _validate_observation_sha(record)
    validate_frozen_shared_case(case)
    if record.source_arm != _SOURCE_ARM:
        raise ValueError("single-target resource-gain adapter accepts only QAOA source")
    if record.qaoa_execution_class != "direct_unrepaired":
        raise ValueError("resource-gain source requires direct_unrepaired QAOA")
    if record.case_sha256 != case.case_sha256:
        raise ValueError("record case binding changed")
    if record.candidate_pool_sha256 != case.candidate_pool_sha256:
        raise ValueError("record candidate-pool binding changed")
    if record.qubo_sha256 != case.qubo_sha256:
        raise ValueError("record QUBO binding changed")
    expected_signatures = tuple(
        canonical_action_sha256(action) for action in case.actions
    )
    if record.action_signatures != expected_signatures:
        raise ValueError("record action signatures changed")
    if record.label_permutation_new_index_to_source_index:
        raise ValueError("QAOA source record cannot carry a label permutation")
    if legacy_target.source_arm != _SOURCE_ARM:
        raise ValueError("legacy target source arm changed")
    if legacy_target.observation_sha256 != record.observation_sha256:
        raise ValueError("legacy target observation binding changed")
    if legacy_target.action_signatures != expected_signatures:
        raise ValueError("legacy target action signatures changed")
    if legacy_target.value_loss_weight_contract != _VALUE_LOSS_WEIGHT_CONTRACT:
        raise ValueError("legacy target value-loss contract changed")
    if legacy_target.trainer_replay_contract != TRAINER_REPLAY_CONTRACT:
        raise ValueError("legacy target trainer replay contract changed")
    if legacy_target.whole_vector_cluster_id != record.whole_vector_cluster_id:
        raise ValueError("legacy target whole-vector cluster binding changed")

    rows = _bitstring_rows_from_record(record, case)
    total = sum(row.count for row in rows)
    if total != record.observation_budget:
        raise ValueError("QAOA source counts do not realise observation budget")
    feasible = sum(row.count for row in rows if row.feasible)
    marginals = [0] * len(case.actions)
    for row in rows:
        if row.feasible:
            for index in row.source_selected_real_indices:
                marginals[index] += row.count
    source_mass = sum(marginals)
    legacy_policy = (
        ()
        if source_mass == 0
        else tuple(float(value / source_mass) for value in marginals)
    )
    denominator = total * case.budget_effective
    legacy_weight = 0.0 if denominator == 0 else float(source_mass / denominator)
    feasible_fraction = 0.0 if total == 0 else float(feasible / total)
    if legacy_target.policy_target != legacy_policy:
        raise ValueError("legacy target is not the source marginal of this record")
    if not _close(legacy_target.policy_observation_weight, legacy_weight):
        raise ValueError("legacy target policy weight changed")
    if not _close(legacy_target.feasible_fraction, feasible_fraction):
        raise ValueError("legacy target feasible fraction changed")
    if not _close(legacy_target.value_observation_weight, feasible_fraction):
        raise ValueError("legacy target value observation weight changed")

    policy = derive_resource_gain_policy_from_bitstring_audit_v1(
        case, rows, total_observed=total
    )
    target = ResourceGainReplayTargetV1(
        schema_version=RESOURCE_GAIN_REPLAY_TARGET_V1_SCHEMA,
        source_arm=_SOURCE_ARM,
        target_role="resource_gain_weighted_source",
        observation_sha256=record.observation_sha256,
        action_signatures=expected_signatures,
        eligible=policy.eligible,
        ineligibility_reasons=policy.ineligibility_reasons,
        action_credits=policy.action_credits,
        policy_target=policy.policy_target,
        policy_observation_weight=policy.policy_observation_weight,
    )
    projected = (
        None
        if not policy.eligible
        else replace(
            legacy_target,
            policy_target=policy.policy_target,
            policy_observation_weight=policy.policy_observation_weight,
        )
    )
    return ResourceGainReplayTeacherV1(
        target=target,
        policy_audit=policy,
        replay_target=projected,
    )


def _record_by_arm(
    group: ReplayTrainingGroupV1,
) -> dict[str, FinalMeasurementObservationV2]:
    # Local import keeps the trainer-facing single-target API free of the
    # replay_training_corpus -> isolated_head_trainer import cycle.
    from e6.replay_training_corpus_v1 import ReplayTrainingGroupV1

    if type(group) is not ReplayTrainingGroupV1:
        raise TypeError("group must be exact ReplayTrainingGroupV1")
    records = group.material.records
    if type(records) is not tuple or len(records) != len(SOURCE_ARMS):
        raise ValueError("replay group must contain the exact four-arm record tuple")
    if any(type(record) is not FinalMeasurementObservationV2 for record in records):
        raise TypeError("replay group records must be exact observations")
    if tuple(record.source_arm for record in records) != SOURCE_ARMS:
        raise ValueError("replay group record order changed")
    return {record.source_arm: record for record in records}


def _base_target_by_arm(
    group: ReplayTrainingGroupV1,
) -> dict[str, ReplayTargetsV2]:
    targets = group.targets_by_arm
    if type(targets) is not tuple or tuple(arm for arm, _ in targets) != SOURCE_ARMS:
        raise ValueError("replay group target order changed")
    if any(type(target) is not ReplayTargetsV2 for _, target in targets):
        raise TypeError("replay group targets must be exact ReplayTargetsV2")
    return dict(targets)


def _validate_audit_binding(
    case: FrozenSharedCase,
    record: FinalMeasurementObservationV2,
    audit: ReplayLedgerAuditV2,
    base_target: ReplayTargetsV2,
) -> None:
    if type(audit) is not ReplayLedgerAuditV2:
        raise TypeError("audit must be exact ReplayLedgerAuditV2")
    if audit.source_arm != record.source_arm:
        raise ValueError("audit source arm does not match its record")
    if audit.observation_sha256 != record.observation_sha256:
        raise ValueError("audit observation SHA does not match its record")
    expected_signatures = tuple(
        canonical_action_sha256(action) for action in case.actions
    )
    if audit.action_signatures != expected_signatures:
        raise ValueError("audit action signatures changed")
    if record.action_signatures != expected_signatures:
        raise ValueError("record action signatures changed")
    if audit.structural_valid is not True:
        raise ValueError("resource-gain derivation requires a structural audit")
    if audit.total_observed != sum(count for _, count in record.counts):
        raise ValueError("audit total_observed changed")
    if audit.declared_observation_budget != record.observation_budget:
        raise ValueError("audit declared observation budget changed")
    if audit.observation_budget_complete != (
        audit.total_observed == record.observation_budget
    ):
        raise ValueError("audit observation budget completeness changed")
    _validate_bitstring_rows(
        case,
        audit.bitstring_audit,
        total_observed=audit.total_observed,
        permutation=record.label_permutation_new_index_to_source_index,
    )
    record_rows = tuple(
        (tuple(int(bit) for bit in key), count) for key, count in record.counts
    )
    audit_rows = tuple((row.bitstring, row.count) for row in audit.bitstring_audit)
    if audit_rows != record_rows:
        raise ValueError("audit bitstring rows do not match the observation ledger")

    feasible = sum(row.count for row in audit.bitstring_audit if row.feasible)
    infeasible = audit.total_observed - feasible
    marginals = [0] * len(case.actions)
    for row in audit.bitstring_audit:
        if row.feasible:
            for index in row.source_selected_real_indices:
                marginals[index] += row.count
    source_marginals = tuple(marginals)
    permutation = record.label_permutation_new_index_to_source_index
    aligned_marginals = (
        tuple(source_marginals[index] for index in permutation)
        if permutation
        else source_marginals
    )
    source_mass = sum(source_marginals)
    source_policy = (
        ()
        if source_mass == 0
        else tuple(float(value / source_mass) for value in source_marginals)
    )
    aligned_policy = (
        ()
        if source_mass == 0
        else tuple(float(value / source_mass) for value in aligned_marginals)
    )
    denominator = audit.total_observed * case.budget_effective
    old_weight = 0.0 if denominator == 0 else float(source_mass / denominator)
    feasible_fraction = (
        0.0 if audit.total_observed == 0 else float(feasible / audit.total_observed)
    )
    if audit.feasible_observed != feasible or audit.infeasible_observed != infeasible:
        raise ValueError("audit feasible observation accounting changed")
    if not _close(audit.feasible_fraction, feasible_fraction):
        raise ValueError("audit feasible fraction changed")
    if audit.source_marginal_action_counts != source_marginals:
        raise ValueError("audit source marginals changed")
    if audit.label_aligned_marginal_action_counts != aligned_marginals:
        raise ValueError("audit aligned marginals changed")
    if audit.source_policy_target != source_policy:
        raise ValueError("audit source policy changed")
    if audit.label_aligned_policy_target != aligned_policy:
        raise ValueError("audit aligned policy changed")
    if not _close(audit.policy_observation_weight, old_weight):
        raise ValueError("audit policy weight changed")
    if audit.source_trusted is not True:
        raise ValueError("resource-gain replay requires a trusted QAOA source audit")
    if record.source_arm == _CONTROL_ARM and audit.parent_validated is not True:
        raise ValueError("resource-gain control requires a validated source parent")
    if audit.teacher_eligible is not True or audit.ineligibility_reasons:
        raise ValueError("group audit does not match its eligible legacy target")

    if base_target.source_arm != record.source_arm:
        raise ValueError("base target source arm changed")
    if base_target.observation_sha256 != audit.observation_sha256:
        raise ValueError("base target observation binding changed")
    if base_target.action_signatures != audit.action_signatures:
        raise ValueError("base target action binding changed")
    if base_target.policy_target != audit.label_aligned_policy_target:
        raise ValueError("base target no longer derives from the supplied audit")
    if not _close(
        base_target.policy_observation_weight, audit.policy_observation_weight
    ):
        raise ValueError("base target policy weight changed")
    if not _close(base_target.feasible_fraction, audit.feasible_fraction):
        raise ValueError("base target feasible fraction changed")
    if not _close(base_target.value_observation_weight, audit.feasible_fraction):
        raise ValueError("base target value observation weight changed")
    if base_target.value_loss_weight_contract != _VALUE_LOSS_WEIGHT_CONTRACT:
        raise ValueError("base target value-loss contract changed")
    if not _close(
        base_target.value_target_log_ratio,
        audit.value_audit.value_target_log_ratio,
    ):
        raise ValueError("base target value target changed")
    if base_target.value_audit != audit.value_audit:
        raise ValueError("base target value audit changed")
    if base_target.whole_vector_cluster_id != audit.whole_vector_cluster_id:
        raise ValueError("base target whole-vector cluster binding changed")
    if base_target.trainer_replay_contract != TRAINER_REPLAY_CONTRACT:
        raise ValueError("base target trainer replay contract changed")


def _target(
    audit: ReplayLedgerAuditV2,
    policy: ResourceGainPolicyAuditV1,
    *,
    target_role: str,
    credits: tuple[float, ...],
    probabilities: tuple[float, ...],
) -> ResourceGainReplayTargetV1:
    return ResourceGainReplayTargetV1(
        schema_version=RESOURCE_GAIN_REPLAY_TARGET_V1_SCHEMA,
        source_arm=audit.source_arm,
        target_role=target_role,
        observation_sha256=audit.observation_sha256,
        action_signatures=audit.action_signatures,
        eligible=policy.eligible,
        ineligibility_reasons=policy.ineligibility_reasons,
        action_credits=credits,
        policy_target=probabilities,
        policy_observation_weight=policy.policy_observation_weight,
    )


def derive_resource_gain_replay_teacher_pair_from_validated_v1(
    *,
    source_record: FinalMeasurementObservationV2,
    control_record: FinalMeasurementObservationV2,
    case: FrozenSharedCase,
    source_legacy_target: ReplayTargetsV2,
    control_legacy_target: ReplayTargetsV2,
    source_audit: ReplayLedgerAuditV2,
    control_audit: ReplayLedgerAuditV2,
) -> ResourceGainReplayTeacherPairV1:
    """Derive a trainer-ready source/control pair from same-call validation.

    The function has no corpus or trainer import.  A trainer first validates
    the external lock, derives both legacy targets/audits in that same call,
    then invokes this pure adapter.  Eligible output carries two exact
    ``ReplayTargetsV2`` projections; ineligible output carries ``None`` for
    both projections and cannot silently fall back.
    """

    if type(source_record) is not FinalMeasurementObservationV2:
        raise TypeError("source_record must be exact FinalMeasurementObservationV2")
    if type(control_record) is not FinalMeasurementObservationV2:
        raise TypeError("control_record must be exact FinalMeasurementObservationV2")
    if type(case) is not FrozenSharedCase:
        raise TypeError("case must be exact FrozenSharedCase")
    if type(source_legacy_target) is not ReplayTargetsV2:
        raise TypeError("source_legacy_target must be exact ReplayTargetsV2")
    if type(control_legacy_target) is not ReplayTargetsV2:
        raise TypeError("control_legacy_target must be exact ReplayTargetsV2")
    _validate_observation_sha(source_record)
    _validate_observation_sha(control_record)
    validate_frozen_shared_case(case)
    if source_record.source_arm != _SOURCE_ARM:
        raise ValueError("source_record must be the QAOA source arm")
    if control_record.source_arm != _CONTROL_ARM:
        raise ValueError("control_record must be the QAOA permuted control arm")
    for name, record in (
        ("source_record", source_record),
        ("control_record", control_record),
    ):
        if record.case_sha256 != case.case_sha256:
            raise ValueError(f"{name} case binding changed")
        if record.vector_sha256 != case.vector_sha256:
            raise ValueError(f"{name} vector binding changed")
        if record.candidate_pool_sha256 != case.candidate_pool_sha256:
            raise ValueError(f"{name} candidate-pool binding changed")
        if record.qubo_sha256 != case.qubo_sha256:
            raise ValueError(f"{name} QUBO binding changed")
        if record.qaoa_execution_class != "direct_unrepaired":
            raise ValueError(f"{name} requires direct_unrepaired QAOA")
    if source_record.group_id != control_record.group_id:
        raise ValueError("QAOA source/control group IDs differ")
    if source_record.group_nonce != control_record.group_nonce:
        raise ValueError("QAOA source/control group nonces differ")
    if source_record.observation_budget != control_record.observation_budget:
        raise ValueError("QAOA source/control observation budgets differ")
    if source_record.whole_vector_cluster_id != (
        control_record.whole_vector_cluster_id
    ):
        raise ValueError("QAOA source/control whole-vector clusters differ")
    if source_record.family_id != control_record.family_id:
        raise ValueError("QAOA source/control families differ")
    if source_record.orbit_cluster_sha256 != control_record.orbit_cluster_sha256:
        raise ValueError("QAOA source/control orbit clusters differ")
    if source_record.split_registry_sha256 != (
        control_record.split_registry_sha256
    ):
        raise ValueError("QAOA source/control split registries differ")
    if source_record.split_role != control_record.split_role:
        raise ValueError("QAOA source/control split roles differ")
    if source_record.origin != control_record.origin:
        raise ValueError("QAOA source/control origins differ")
    if source_record.action_signatures != control_record.action_signatures:
        raise ValueError("QAOA source/control action signatures differ")
    if source_record.qaoa_contract != control_record.qaoa_contract:
        raise ValueError("QAOA control changed the source execution contract")
    if source_record.distribution_sha256 != control_record.distribution_sha256:
        raise ValueError("QAOA control changed the source distribution binding")
    if source_record.parent_qaoa_observation_sha256 is not None:
        raise ValueError("QAOA source record cannot name a parent")
    if source_record.label_permutation_new_index_to_source_index:
        raise ValueError("QAOA source record cannot carry a label permutation")
    _validate_audit_binding(
        case, source_record, source_audit, source_legacy_target
    )
    _validate_audit_binding(
        case, control_record, control_audit, control_legacy_target
    )
    if source_record.counts != control_record.counts:
        raise ValueError("QAOA control must reuse the exact source counts")
    if control_record.parent_qaoa_observation_sha256 != (
        source_record.observation_sha256
    ):
        raise ValueError("QAOA control parent binding changed")
    if source_audit.source_marginal_action_counts != (
        control_audit.source_marginal_action_counts
    ):
        raise ValueError("control audit changed source-coordinate marginals")
    if tuple(
        (row.bitstring, row.count, row.source_selected_real_indices, row.feasible)
        for row in source_audit.bitstring_audit
    ) != tuple(
        (row.bitstring, row.count, row.source_selected_real_indices, row.feasible)
        for row in control_audit.bitstring_audit
    ):
        raise ValueError("control audit changed source-coordinate bitstring evidence")

    policy = derive_resource_gain_policy_from_bitstring_audit_v1(
        case,
        source_audit.bitstring_audit,
        total_observed=source_audit.total_observed,
    )
    permutation = control_record.label_permutation_new_index_to_source_index
    if len(permutation) != len(case.actions) or set(permutation) != set(
        range(len(case.actions))
    ):
        raise ValueError("control label permutation is not an action-aligned bijection")
    control_credits = tuple(policy.action_credits[index] for index in permutation)
    control_policy = (
        ()
        if not policy.eligible
        else tuple(policy.policy_target[index] for index in permutation)
    )
    source = _target(
        source_audit,
        policy,
        target_role="resource_gain_weighted_source",
        credits=policy.action_credits,
        probabilities=policy.policy_target,
    )
    control = _target(
        control_audit,
        policy,
        target_role="permuted_after_resource_gain_source_target",
        credits=control_credits,
        probabilities=control_policy,
    )
    if control.action_credits != tuple(
        source.action_credits[index] for index in permutation
    ):
        raise RuntimeError("control credits are not the exact source permutation")
    expected_control_policy = (
        ()
        if not source.eligible
        else tuple(source.policy_target[index] for index in permutation)
    )
    if control.policy_target != expected_control_policy:
        raise RuntimeError("control probabilities are not the exact source permutation")
    if not _close(
        math.fsum(control.action_credits), math.fsum(source.action_credits)
    ):
        raise RuntimeError("control permutation changed total credit mass")
    if policy.eligible and not _close(math.fsum(control.policy_target), 1.0):
        raise RuntimeError("control permutation changed probability mass")
    source_projection = (
        None
        if not policy.eligible
        else replace(
            source_legacy_target,
            policy_target=source.policy_target,
            policy_observation_weight=source.policy_observation_weight,
        )
    )
    control_projection = (
        None
        if not policy.eligible
        else replace(
            control_legacy_target,
            policy_target=control.policy_target,
            policy_observation_weight=control.policy_observation_weight,
        )
    )
    if (source_projection is None) != (control_projection is None):
        raise RuntimeError("source/control projection eligibility diverged")
    return ResourceGainReplayTeacherPairV1(
        schema_version=RESOURCE_GAIN_REPLAY_TEACHER_PAIR_V1_SCHEMA,
        group_id=source_record.group_id,
        case_sha256=case.case_sha256,
        candidate_pool_sha256=case.candidate_pool_sha256,
        label_permutation_new_index_to_source_index=permutation,
        source=source,
        control=control,
        source_replay_target=source_projection,
        control_replay_target=control_projection,
        policy_audit=policy,
        control_is_exact_source_permutation=True,
        permuted_target_changed=(source.policy_target != control.policy_target),
    )


def derive_resource_gain_replay_teacher_pair_v1(
    group: ReplayTrainingGroupV1,
    source_audit: ReplayLedgerAuditV2,
    control_audit: ReplayLedgerAuditV2,
) -> ResourceGainReplayTeacherPairV1:
    """Thin corpus adapter for the same trainer-safe pair derivation."""

    records = _record_by_arm(group)
    targets = _base_target_by_arm(group)
    return derive_resource_gain_replay_teacher_pair_from_validated_v1(
        source_record=records[_SOURCE_ARM],
        control_record=records[_CONTROL_ARM],
        case=group.material.case,
        source_legacy_target=targets[_SOURCE_ARM],
        control_legacy_target=targets[_CONTROL_ARM],
        source_audit=source_audit,
        control_audit=control_audit,
    )


def derive_resource_gain_replay_teacher_pair_from_group_v1(
    group: ReplayTrainingGroupV1,
    registry: SplitRegistryV2,
) -> ResourceGainReplayTeacherPairV1:
    """Revalidate one existing group and derive its trusted D2 teacher pair.

    This convenience adapter reads the group's existing lock and actual payload
    bytes.  It creates no manifest, lock, seal, or training artifact.
    """

    records = _record_by_arm(group)
    if type(registry) is not SplitRegistryV2:
        raise TypeError("registry must be exact SplitRegistryV2")
    material = group.material
    if type(material.external_lock_payload) is not bytes:
        raise TypeError("external lock payload must be native bytes")
    if type(group.technical_lock) is not ExternalReplayLockV2:
        raise TypeError("group technical lock must be exact ExternalReplayLockV2")
    parsed_lock = ExternalReplayLockV2.from_bytes(material.external_lock_payload)
    if parsed_lock != group.technical_lock:
        raise ValueError("group technical lock differs from its canonical payload")
    validated = validate_external_replay_lock_v2(
        group.technical_lock,
        material.manifest,
        material.records,
        material.case,
        registry,
        expected_lock_sha256=group.technical_lock.lock_sha256,
        qaoa_counts_payload=material.qaoa_counts_payload,
        final_parameter_payload=material.final_parameter_payload,
        run_attestation=material.run_attestation,
    )
    audits: dict[str, ReplayLedgerAuditV2] = {}
    for arm in (_SOURCE_ARM, _CONTROL_ARM):
        record = records[arm]
        audits[arm] = validated.audit_for(
            record,
            material.case,
            registry,
            expected_observation_sha256=record.observation_sha256,
            expected_registry_sha256=registry.registry_sha256,
        )
    return derive_resource_gain_replay_teacher_pair_v1(
        group, audits[_SOURCE_ARM], audits[_CONTROL_ARM]
    )


def project_eligible_resource_gain_targets_v1(
    pair: ResourceGainReplayTeacherPairV1,
    group: ReplayTrainingGroupV1,
) -> tuple[tuple[str, ReplayTargetsV2], ...]:
    """Project an eligible pair to exact ``ReplayTargetsV2`` instances.

    Only policy target and policy observation weight change.  Existing value
    targets/audits are retained byte-for-byte; a D2 run with ``value_weight=0``
    therefore has an explicit trainer-compatible value payload without making
    it part of the intervention.  The current legacy trainer still re-derives
    its own targets internally, so a separate controlled trainer adapter must
    call this function rather than accepting caller-supplied targets.
    """

    from e6.replay_training_corpus_v1 import ReplayTrainingGroupV1

    if type(pair) is not ResourceGainReplayTeacherPairV1:
        raise TypeError("pair must be exact ResourceGainReplayTeacherPairV1")
    if type(group) is not ReplayTrainingGroupV1:
        raise TypeError("group must be exact ReplayTrainingGroupV1")
    case = group.material.case
    validate_frozen_shared_case(case)
    if pair.group_id != group.material.manifest.group_id:
        raise ValueError("resource-gain pair group binding changed")
    if pair.case_sha256 != case.case_sha256:
        raise ValueError("resource-gain pair case binding changed")
    if pair.candidate_pool_sha256 != case.candidate_pool_sha256:
        raise ValueError("resource-gain pair pool binding changed")
    if not pair.source.eligible or not pair.control.eligible:
        raise ValueError(
            "ineligible resource-gain teacher has no ReplayTargetsV2 projection"
        )
    if pair.source.ineligibility_reasons or pair.control.ineligibility_reasons:
        raise ValueError("eligible resource-gain target carries ineligibility reasons")
    if pair.source_replay_target is None or pair.control_replay_target is None:
        raise ValueError("eligible resource-gain pair lost trainer-ready projections")
    expected_signatures = tuple(
        canonical_action_sha256(action) for action in case.actions
    )
    permutation = pair.label_permutation_new_index_to_source_index
    if pair.source.action_signatures != expected_signatures:
        raise ValueError("resource-gain source action binding changed")
    if pair.control.action_signatures != expected_signatures:
        raise ValueError("resource-gain control action binding changed")
    if pair.control.action_credits != tuple(
        pair.source.action_credits[index] for index in permutation
    ):
        raise ValueError("resource-gain control credit permutation changed")
    if pair.control.policy_target != tuple(
        pair.source.policy_target[index] for index in permutation
    ):
        raise ValueError("resource-gain control policy permutation changed")
    for target in (pair.source, pair.control):
        if len(target.policy_target) != len(case.actions):
            raise ValueError("resource-gain policy no longer aligns with actions")
        if any(
            type(value) is not float or not math.isfinite(value) or value < 0.0
            for value in target.policy_target
        ):
            raise ValueError("resource-gain policy contains an invalid probability")
        if not _close(math.fsum(target.policy_target), 1.0):
            raise ValueError("resource-gain policy no longer sums to one")
        if (
            type(target.policy_observation_weight) is not float
            or not math.isfinite(target.policy_observation_weight)
            or target.policy_observation_weight <= 0.0
        ):
            raise ValueError("resource-gain policy weight must be a positive float")

    base = _base_target_by_arm(group)
    projected: list[tuple[str, ReplayTargetsV2]] = []
    for target, carried in (
        (pair.source, pair.source_replay_target),
        (pair.control, pair.control_replay_target),
    ):
        prior = base[target.source_arm]
        if prior.value_loss_weight_contract != _VALUE_LOSS_WEIGHT_CONTRACT:
            raise ValueError("base target value-loss contract changed")
        expected = replace(
            prior,
            policy_target=target.policy_target,
            policy_observation_weight=target.policy_observation_weight,
        )
        if carried != expected:
            raise ValueError("resource-gain carried projection changed")
        projected.append((target.source_arm, carried))
    return tuple(projected)


__all__ = [
    "POLICY_WEIGHT_FORMULA",
    "RESOURCE_GAIN_FORMULA",
    "RESOURCE_GAIN_POLICY_AUDIT_V1_SCHEMA",
    "RESOURCE_GAIN_REPLAY_TARGET_V1_SCHEMA",
    "RESOURCE_GAIN_REPLAY_TEACHER_PAIR_V1_SCHEMA",
    "ResourceGainBitstringDiagnosticV1",
    "ResourceGainPolicyAuditV1",
    "ResourceGainReplayTargetV1",
    "ResourceGainReplayTeacherV1",
    "ResourceGainReplayTeacherPairV1",
    "derive_resource_gain_policy_from_bitstring_audit_v1",
    "derive_resource_gain_replay_teacher_pair_from_group_v1",
    "derive_resource_gain_replay_teacher_pair_from_validated_v1",
    "derive_resource_gain_replay_teacher_pair_v1",
    "derive_resource_gain_replay_target_v1",
    "project_eligible_resource_gain_targets_v1",
]
