"""Frozen, checksum-bound scheduling cases for E6 shared actions.

The mechanism modules deliberately accept ordinary Python sequences.  That is
useful during development, but it is not enough for a paired greedy/exact/QAOA
comparison: three independent calls could enumerate, score, truncate, or order
their candidates differently.  This module closes that gap without changing
the underlying scheduler.

``build_frozen_shared_case`` scores the full candidate set once, applies one
common top-K rule, materialises the scheduling matrices and QUBO, and binds
every component by SHA-256.  ``schedule_frozen_case`` validates all bindings
before invoking one of the existing solvers on the already frozen action pool.

Hash semantics are intentionally explicit:

* the order in which a caller supplies candidates is *not* semantic; candidates
  are ranked by learned utility, raw utility, then action SHA before hashing;
* the resulting execution-pool order *is* semantic because utilities and solver
  bit positions are aligned to it;
* output-wire labels *are* semantic for exact hashes.  Relabelling outputs
  therefore changes vector/pool/case SHA even when an equivariant model gives
  corresponding scores.  Model equivariance must be tested as a mathematical
  relation, not inferred from byte-identical hashes.

This is a development/freeze layer, not a blind-test runner or performance
claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math
import re
from typing import Iterable, Protocol, Sequence

from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    SharedAction,
    VectorANF,
    validate_shared_action,
)
from e6.shared_scheduler import (
    DummyFixedCardinalityQUBO,
    SharedScheduleResult,
    SharedSchedulerConfig,
    SharedUtilityWeights,
    action_conflict_matrix,
    action_redundancy_matrix,
    build_dummy_fixed_cardinality_qubo,
    build_shared_scheduling_problem,
    schedule_shared_actions,
    shared_action_utility,
)
from src.contracts.codec import canonical_json_bytes, sha256_bytes


FROZEN_CASE_SCHEMA = "xa.e6-frozen-shared-case.v1"
TOP_K_RULE = "learned_desc_raw_desc_action_sha256_asc"
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class SharedActionScorer(Protocol):
    """Structural protocol implemented by ``SharedPolicyValueScorer``."""

    def score_actions(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> Sequence[float]: ...


@dataclass(frozen=True)
class FrozenCaseHashSemantics:
    """Machine-readable distinction between ordering and relabelling claims."""

    candidate_input_order: str = (
        "non_semantic_canonicalised_once_by_learned_raw_action_sha_ranking"
    )
    execution_pool_order: str = (
        "semantic_binds_action_utility_matrix_and_qubo_variable_alignment"
    )
    output_relabeling: str = (
        "coordinate_preserving_exact_hashes_change_under_output_relabeling;_"
        "equivariance_is_a_separate_model_property"
    )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


HASH_SEMANTICS = FrozenCaseHashSemantics()


def _sha(payload: object) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def _finite_tuple(values: Iterable[float], name: str) -> tuple[float, ...]:
    converted: list[float] = []
    for index, raw in enumerate(values):
        if isinstance(raw, bool):
            raise TypeError(f"{name}[{index}] must be a finite real number")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{name}[{index}] must be a finite real number"
            ) from exc
        if not math.isfinite(value):
            raise ValueError(f"{name}[{index}] must be finite")
        converted.append(value)
    return tuple(converted)


def _require_sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lower-case SHA-256 hex digest")
    return value


def canonical_vector_payload(vector: VectorANF) -> dict[str, object]:
    """Coordinate-preserving canonical JSON payload for a vector ANF."""

    if not isinstance(vector, VectorANF):
        raise TypeError("vector must be a VectorANF")
    return {
        "schema_version": "xa.e6-canonical-vector-anf.v1",
        "input_count": vector.input_count,
        "output_count": vector.output_count,
        "output_order": "exact_lsb_indexed_output_wire_order",
        "outputs": [sorted(terms) for terms in vector.outputs],
    }


def canonical_action_payload(action: SharedAction) -> dict[str, object]:
    """Coordinate-preserving identity of one E6 shared action."""

    if isinstance(action, MonomialSharedAction):
        identity: dict[str, object] = {
            "kind": "monomial",
            "monomial": action.monomial,
            "targets": list(action.targets),
        }
    elif isinstance(action, SemiAffineSharedAction):
        identity = {
            "kind": "semi_affine",
            "base_monomial": action.base_monomial,
            "affine_mask": action.affine_mask,
            "affine_const": action.affine_const,
            "targets": list(action.targets),
        }
    else:
        raise TypeError("unsupported E6 shared-action type")
    return {
        "schema_version": "xa.e6-canonical-shared-action.v1",
        "output_order": "exact_lsb_indexed_output_wire_order",
        **identity,
        "polynomial_terms": sorted(action.polynomial_terms),
        "footprint": [list(item) for item in sorted(action.footprint)],
        "ancilla_required": action.ancilla_required,
    }


def canonical_action_sha256(action: SharedAction) -> str:
    return _sha(canonical_action_payload(action))


def canonical_pool_payload(
    actions: Sequence[SharedAction],
    *,
    role: str = "selected_execution_pool",
) -> dict[str, object]:
    """Order-binding pool payload; callers must pass canonical ranked order."""

    return {
        "schema_version": "xa.e6-canonical-ordered-shared-pool.v1",
        "role": role,
        "ordering": TOP_K_RULE,
        "actions": [canonical_action_payload(action) for action in actions],
    }


def _utility_payload(
    values: Sequence[float], pool_sha256: str, role: str
) -> dict[str, object]:
    return {
        "schema_version": "xa.e6-aligned-utility-vector.v1",
        "role": role,
        "alignment": "ordered_pool_index",
        "pool_sha256": pool_sha256,
        "values": list(values),
    }


def _matrix_payload(
    matrix: Sequence[Sequence[object]], pool_sha256: str, role: str
) -> dict[str, object]:
    return {
        "schema_version": "xa.e6-aligned-pair-matrix.v1",
        "role": role,
        "alignment": "ordered_pool_row_and_column_index",
        "pool_sha256": pool_sha256,
        "rows": [list(row) for row in matrix],
    }


def _safe_candidate_cap(budget_requested: int, variable_limit: int) -> int:
    """Largest K satisfying ``K + min(B, K) <= variable_limit``."""

    for count in range(variable_limit, -1, -1):
        if count + min(budget_requested, count) <= variable_limit:
            return count
    return 0  # pragma: no cover - count=0 always satisfies the inequality


@dataclass(frozen=True)
class FrozenSharedCase:
    """One immutable, checksum-bound input shared by all scheduler methods."""

    schema_version: str
    vector: VectorANF
    ranked_actions: tuple[SharedAction, ...]
    ranked_raw_utilities: tuple[float, ...]
    ranked_learned_utilities: tuple[float, ...]
    candidate_cap_requested: int | None
    candidate_cap_effective: int
    qaoa_safe_candidate_cap: int
    scheduler_config: SharedSchedulerConfig
    utility_weights: SharedUtilityWeights
    redundancy: tuple[tuple[float, ...], ...]
    conflicts: tuple[tuple[bool, ...], ...]
    qubo: DummyFixedCardinalityQUBO
    checkpoint_sha256: str
    hash_semantics: FrozenCaseHashSemantics
    vector_sha256: str
    source_pool_sha256: str
    candidate_pool_sha256: str
    source_raw_utility_sha256: str
    source_learned_utility_sha256: str
    raw_utility_sha256: str
    learned_utility_sha256: str
    redundancy_sha256: str
    conflict_sha256: str
    qubo_sha256: str
    case_sha256: str

    @property
    def source_candidate_count(self) -> int:
        return len(self.ranked_actions)

    @property
    def actions(self) -> tuple[SharedAction, ...]:
        return self.ranked_actions[: self.candidate_cap_effective]

    @property
    def raw_utilities(self) -> tuple[float, ...]:
        return self.ranked_raw_utilities[: self.candidate_cap_effective]

    @property
    def learned_utilities(self) -> tuple[float, ...]:
        return self.ranked_learned_utilities[: self.candidate_cap_effective]

    @property
    def budget_effective(self) -> int:
        return min(self.scheduler_config.budget_requested, len(self.actions))

    @property
    def augmented_variable_count(self) -> int:
        return len(self.actions) + self.budget_effective

    def binding_dict(self) -> dict[str, object]:
        """Compact binding copied unchanged into every method result."""

        return {
            "schema_version": self.schema_version,
            "case_sha256": self.case_sha256,
            "vector_sha256": self.vector_sha256,
            "source_pool_sha256": self.source_pool_sha256,
            "candidate_pool_sha256": self.candidate_pool_sha256,
            "source_raw_utility_sha256": self.source_raw_utility_sha256,
            "source_learned_utility_sha256": self.source_learned_utility_sha256,
            "raw_utility_sha256": self.raw_utility_sha256,
            "learned_utility_sha256": self.learned_utility_sha256,
            "redundancy_sha256": self.redundancy_sha256,
            "conflict_sha256": self.conflict_sha256,
            "qubo_sha256": self.qubo_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "source_candidate_count": self.source_candidate_count,
            "candidate_cap_requested": self.candidate_cap_requested,
            "candidate_cap_effective": self.candidate_cap_effective,
            "qaoa_safe_candidate_cap": self.qaoa_safe_candidate_cap,
            "budget_requested": self.scheduler_config.budget_requested,
            "budget_effective": self.budget_effective,
            "augmented_variable_count": self.augmented_variable_count,
            "top_k_rule": TOP_K_RULE,
            "scheduler_utility": "learned_utility",
            "hash_semantics": self.hash_semantics.to_dict(),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.binding_dict(),
            "vector": canonical_vector_payload(self.vector),
            "source_actions": [
                canonical_action_payload(action) for action in self.ranked_actions
            ],
            "source_raw_utilities": list(self.ranked_raw_utilities),
            "source_learned_utilities": list(self.ranked_learned_utilities),
            "selected_actions": [
                canonical_action_payload(action) for action in self.actions
            ],
            "selected_raw_utilities": list(self.raw_utilities),
            "selected_learned_utilities": list(self.learned_utilities),
            "redundancy": [list(row) for row in self.redundancy],
            "conflicts": [list(row) for row in self.conflicts],
            "qubo": self.qubo.to_dict(),
            "scheduler_config": self.scheduler_config.to_dict(),
            "utility_weights": asdict(self.utility_weights),
            "performance_evidence": False,
        }


def _case_payload(case: FrozenSharedCase) -> dict[str, object]:
    """Hash preimage containing all scientific/solver component bindings."""

    return {
        "schema_version": case.schema_version,
        "hash_semantics": case.hash_semantics.to_dict(),
        "top_k_rule": TOP_K_RULE,
        "scheduler_utility": "learned_utility",
        "candidate_cap_requested": case.candidate_cap_requested,
        "candidate_cap_effective": case.candidate_cap_effective,
        "qaoa_safe_candidate_cap": case.qaoa_safe_candidate_cap,
        "scheduler_config": case.scheduler_config.to_dict(),
        "utility_weights": asdict(case.utility_weights),
        "bindings": {
            "vector_sha256": case.vector_sha256,
            "source_pool_sha256": case.source_pool_sha256,
            "candidate_pool_sha256": case.candidate_pool_sha256,
            "source_raw_utility_sha256": case.source_raw_utility_sha256,
            "source_learned_utility_sha256": (
                case.source_learned_utility_sha256
            ),
            "raw_utility_sha256": case.raw_utility_sha256,
            "learned_utility_sha256": case.learned_utility_sha256,
            "redundancy_sha256": case.redundancy_sha256,
            "conflict_sha256": case.conflict_sha256,
            "qubo_sha256": case.qubo_sha256,
            "checkpoint_sha256": case.checkpoint_sha256,
        },
    }


def build_frozen_shared_case(
    vector: VectorANF,
    actions: Sequence[SharedAction] | Iterable[SharedAction],
    *,
    checkpoint_sha256: str,
    config: SharedSchedulerConfig = SharedSchedulerConfig(),
    utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
    raw_utilities: Sequence[float] | Iterable[float] | None = None,
    learned_utilities: Sequence[float] | Iterable[float] | None = None,
    scorer: SharedActionScorer | None = None,
    candidate_cap: int | None = None,
) -> FrozenSharedCase:
    """Build and hash one common pool; learned scoring occurs at most once."""

    checkpoint = _require_sha256(checkpoint_sha256, "checkpoint_sha256")
    candidates = tuple(actions)
    for action in candidates:
        validate_shared_action(vector, action)
    action_shas = tuple(canonical_action_sha256(action) for action in candidates)
    if len(set(action_shas)) != len(action_shas):
        raise ValueError("candidate actions must have unique canonical identities")

    if raw_utilities is None:
        raw = tuple(
            shared_action_utility(action, weights=utility_weights)
            for action in candidates
        )
    else:
        raw = _finite_tuple(raw_utilities, "raw_utilities")
    if len(raw) != len(candidates):
        raise ValueError("raw_utilities must align with the full candidate set")

    if scorer is not None and learned_utilities is not None:
        raise ValueError("provide scorer or learned_utilities, not both")
    if scorer is not None:
        learned = _finite_tuple(
            scorer.score_actions(vector, candidates, weights=utility_weights),
            "scorer output",
        )
    elif learned_utilities is not None:
        learned = _finite_tuple(learned_utilities, "learned_utilities")
    elif candidates:
        raise ValueError("non-empty frozen cases require learned utilities or a scorer")
    else:
        learned = ()
    if len(learned) != len(candidates):
        raise ValueError("learned utilities must align with the full candidate set")

    ranked = sorted(
        zip(candidates, raw, learned, action_shas),
        key=lambda item: (-item[2], -item[1], item[3]),
    )
    ranked_actions = tuple(item[0] for item in ranked)
    ranked_raw = tuple(item[1] for item in ranked)
    ranked_learned = tuple(item[2] for item in ranked)

    if candidate_cap is not None:
        if isinstance(candidate_cap, bool) or not isinstance(candidate_cap, int):
            raise TypeError("candidate_cap must be a positive integer or None")
        if candidate_cap <= 0:
            raise ValueError("candidate_cap must be positive")
    common_config = replace(config, method="greedy")
    variable_limit = min(
        common_config.qaoa_max_variables, common_config.audit_max_variables
    )
    qaoa_safe_cap = _safe_candidate_cap(
        common_config.budget_requested, variable_limit
    )
    requested_cap = len(ranked_actions) if candidate_cap is None else candidate_cap
    effective_cap = min(len(ranked_actions), requested_cap, qaoa_safe_cap)
    selected_actions = ranked_actions[:effective_cap]
    selected_raw = ranked_raw[:effective_cap]
    selected_learned = ranked_learned[:effective_cap]

    vector_sha = _sha(canonical_vector_payload(vector))
    source_pool_sha = _sha(
        canonical_pool_payload(ranked_actions, role="ranked_source_pool")
    )
    pool_sha = _sha(canonical_pool_payload(selected_actions))
    source_raw_sha = _sha(
        _utility_payload(ranked_raw, source_pool_sha, "source_raw_utility")
    )
    source_learned_sha = _sha(
        _utility_payload(
            ranked_learned, source_pool_sha, "source_learned_utility"
        )
    )
    raw_sha = _sha(_utility_payload(selected_raw, pool_sha, "raw_utility"))
    learned_sha = _sha(
        _utility_payload(selected_learned, pool_sha, "learned_utility")
    )
    redundancy = action_redundancy_matrix(
        selected_actions, alpha=common_config.redundancy_alpha
    )
    conflicts = action_conflict_matrix(selected_actions)
    redundancy_sha = _sha(_matrix_payload(redundancy, pool_sha, "redundancy"))
    conflict_sha = _sha(_matrix_payload(conflicts, pool_sha, "conflict"))
    problem = build_shared_scheduling_problem(
        selected_actions,
        common_config.budget_requested,
        utilities=selected_learned,
        redundancy=redundancy,
        redundancy_weight=common_config.redundancy_weight,
        redundancy_alpha=common_config.redundancy_alpha,
    )
    if problem.conflicts != conflicts:  # pragma: no cover - construction invariant
        raise RuntimeError("frozen conflict matrix drifted during problem construction")
    qubo = build_dummy_fixed_cardinality_qubo(
        problem,
        rho=common_config.rho,
        conflict_penalty=common_config.conflict_penalty,
    )
    qubo_sha = _sha(qubo.to_dict())

    provisional = FrozenSharedCase(
        schema_version=FROZEN_CASE_SCHEMA,
        vector=vector,
        ranked_actions=ranked_actions,
        ranked_raw_utilities=ranked_raw,
        ranked_learned_utilities=ranked_learned,
        candidate_cap_requested=candidate_cap,
        candidate_cap_effective=effective_cap,
        qaoa_safe_candidate_cap=qaoa_safe_cap,
        scheduler_config=common_config,
        utility_weights=utility_weights,
        redundancy=redundancy,
        conflicts=conflicts,
        qubo=qubo,
        checkpoint_sha256=checkpoint,
        hash_semantics=HASH_SEMANTICS,
        vector_sha256=vector_sha,
        source_pool_sha256=source_pool_sha,
        candidate_pool_sha256=pool_sha,
        source_raw_utility_sha256=source_raw_sha,
        source_learned_utility_sha256=source_learned_sha,
        raw_utility_sha256=raw_sha,
        learned_utility_sha256=learned_sha,
        redundancy_sha256=redundancy_sha,
        conflict_sha256=conflict_sha,
        qubo_sha256=qubo_sha,
        case_sha256="",
    )
    frozen = replace(provisional, case_sha256=_sha(_case_payload(provisional)))
    validate_frozen_shared_case(frozen)
    return frozen


def validate_frozen_shared_case(case: FrozenSharedCase) -> None:
    """Recompute every binding and fail closed on any in-memory tampering."""

    if not isinstance(case, FrozenSharedCase):
        raise TypeError("case must be a FrozenSharedCase")
    if case.schema_version != FROZEN_CASE_SCHEMA:
        raise ValueError("unsupported E6 frozen-case schema")
    _require_sha256(case.checkpoint_sha256, "checkpoint_sha256")
    if case.hash_semantics != HASH_SEMANTICS:
        raise ValueError("frozen-case hash semantics changed")
    if case.scheduler_config.method != "greedy":
        raise ValueError("frozen-case common scheduler config must be method-neutral")
    lengths = {
        len(case.ranked_actions),
        len(case.ranked_raw_utilities),
        len(case.ranked_learned_utilities),
    }
    if len(lengths) != 1:
        raise ValueError("frozen source actions and utilities are misaligned")
    for action in case.ranked_actions:
        validate_shared_action(case.vector, action)
    action_shas = tuple(
        canonical_action_sha256(action) for action in case.ranked_actions
    )
    if len(set(action_shas)) != len(action_shas):
        raise ValueError("frozen source pool contains duplicate actions")
    reranked = tuple(
        sorted(
            zip(
                case.ranked_actions,
                case.ranked_raw_utilities,
                case.ranked_learned_utilities,
                action_shas,
            ),
            key=lambda item: (-item[2], -item[1], item[3]),
        )
    )
    if tuple(item[0] for item in reranked) != case.ranked_actions:
        raise ValueError("frozen source pool no longer follows the canonical top-K order")
    if tuple(item[1] for item in reranked) != case.ranked_raw_utilities:
        raise ValueError("frozen raw utilities no longer align with actions")
    if tuple(item[2] for item in reranked) != case.ranked_learned_utilities:
        raise ValueError("frozen learned utilities no longer align with actions")

    variable_limit = min(
        case.scheduler_config.qaoa_max_variables,
        case.scheduler_config.audit_max_variables,
    )
    safe_cap = _safe_candidate_cap(
        case.scheduler_config.budget_requested, variable_limit
    )
    requested_cap = (
        len(case.ranked_actions)
        if case.candidate_cap_requested is None
        else case.candidate_cap_requested
    )
    expected_cap = min(len(case.ranked_actions), requested_cap, safe_cap)
    if case.qaoa_safe_candidate_cap != safe_cap:
        raise ValueError("frozen QAOA-safe candidate cap changed")
    if case.candidate_cap_effective != expected_cap:
        raise ValueError("frozen effective candidate cap changed")
    if case.augmented_variable_count > variable_limit:
        raise ValueError("frozen case exceeds the common QAOA/audit variable limit")

    expected: dict[str, str] = {}
    expected["vector_sha256"] = _sha(canonical_vector_payload(case.vector))
    expected["source_pool_sha256"] = _sha(
        canonical_pool_payload(case.ranked_actions, role="ranked_source_pool")
    )
    expected["candidate_pool_sha256"] = _sha(
        canonical_pool_payload(case.actions)
    )
    expected["source_raw_utility_sha256"] = _sha(
        _utility_payload(
            case.ranked_raw_utilities,
            expected["source_pool_sha256"],
            "source_raw_utility",
        )
    )
    expected["source_learned_utility_sha256"] = _sha(
        _utility_payload(
            case.ranked_learned_utilities,
            expected["source_pool_sha256"],
            "source_learned_utility",
        )
    )
    expected["raw_utility_sha256"] = _sha(
        _utility_payload(
            case.raw_utilities, expected["candidate_pool_sha256"], "raw_utility"
        )
    )
    expected["learned_utility_sha256"] = _sha(
        _utility_payload(
            case.learned_utilities,
            expected["candidate_pool_sha256"],
            "learned_utility",
        )
    )
    recomputed_redundancy = action_redundancy_matrix(
        case.actions, alpha=case.scheduler_config.redundancy_alpha
    )
    recomputed_conflicts = action_conflict_matrix(case.actions)
    if case.redundancy != recomputed_redundancy:
        raise ValueError("frozen redundancy matrix changed")
    if case.conflicts != recomputed_conflicts:
        raise ValueError("frozen conflict matrix changed")
    expected["redundancy_sha256"] = _sha(
        _matrix_payload(
            case.redundancy, expected["candidate_pool_sha256"], "redundancy"
        )
    )
    expected["conflict_sha256"] = _sha(
        _matrix_payload(
            case.conflicts, expected["candidate_pool_sha256"], "conflict"
        )
    )
    problem = build_shared_scheduling_problem(
        case.actions,
        case.scheduler_config.budget_requested,
        utilities=case.learned_utilities,
        redundancy=case.redundancy,
        redundancy_weight=case.scheduler_config.redundancy_weight,
        redundancy_alpha=case.scheduler_config.redundancy_alpha,
    )
    recomputed_qubo = build_dummy_fixed_cardinality_qubo(
        problem,
        rho=case.scheduler_config.rho,
        conflict_penalty=case.scheduler_config.conflict_penalty,
    )
    if case.qubo != recomputed_qubo:
        raise ValueError("frozen QUBO changed")
    expected["qubo_sha256"] = _sha(case.qubo.to_dict())
    for field, value in expected.items():
        if getattr(case, field) != value:
            raise ValueError(f"frozen-case {field} binding mismatch")
    if _require_sha256(case.case_sha256, "case_sha256") != _sha(
        _case_payload(case)
    ):
        raise ValueError("frozen-case case_sha256 binding mismatch")


def schedule_frozen_case(
    case: FrozenSharedCase,
    method: str,
) -> SharedScheduleResult:
    """Run one method on a validated case without enumerating or scoring again."""

    validate_frozen_shared_case(case)
    method_config = replace(case.scheduler_config, method=method)
    result = schedule_shared_actions(
        case.actions,
        config=method_config,
        utilities=case.learned_utilities,
        utility_weights=case.utility_weights,
        redundancy=case.redundancy,
    )
    observed_qubo_sha = _sha(result.diagnostics["qubo"])
    if observed_qubo_sha != case.qubo_sha256:
        raise RuntimeError("scheduler reconstructed a QUBO different from the frozen case")
    if tuple(result.diagnostics["selected_indices"]) != result.selected_indices:
        raise RuntimeError("scheduler selected-index diagnostics drifted")
    diagnostics = dict(result.diagnostics)
    diagnostics["frozen_case_validated"] = True
    diagnostics["frozen_case"] = case.binding_dict()
    return SharedScheduleResult(
        selected_indices=result.selected_indices,
        real_bitstring=result.real_bitstring,
        augmented_bitstring=result.augmented_bitstring,
        dummy_selected=result.dummy_selected,
        diagnostics=diagnostics,
    )


__all__ = [
    "FROZEN_CASE_SCHEMA",
    "HASH_SEMANTICS",
    "TOP_K_RULE",
    "FrozenCaseHashSemantics",
    "FrozenSharedCase",
    "SharedActionScorer",
    "build_frozen_shared_case",
    "canonical_action_payload",
    "canonical_action_sha256",
    "canonical_pool_payload",
    "canonical_vector_payload",
    "schedule_frozen_case",
    "validate_frozen_shared_case",
]
