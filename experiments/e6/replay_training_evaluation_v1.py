#!/usr/bin/env python3
"""Deterministic held-out development evaluation for E6 replay-trained heads.

The evaluator deliberately has a narrow evidence role.  It generates fresh
synthetic ``n=4`` and ``n=5`` Boolean bijections from a fixed integer seed,
without Python's pseudo-random generator, and evaluates the four replay arms
on exactly the same arm-neutral action universe.  The learned heads rank
candidates; the existing exhaustive scheduler makes the final budget-two
decision; and the emitted oracle must pass exhaustive ``all x / all y``
semantics before its abstract logical-resource ratio is admitted.

This is a reproducible *held-out development evaluation*.  It is neither a
blind release nor formal/performance evidence.  A failed arm is assigned the
direct program and ``Y=1`` for intention-to-treat (ITT) accounting.  Such a
failure also closes the development claim gate.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import asdict
from numbers import Real
from typing import Mapping, Sequence

from e6.final_measurement_replay_v2 import (
    SOURCE_ARMS,
    canonical_vector_orbit_sha256,
    whole_vector_cluster_id,
)
from e6.frozen_case import (
    canonical_action_payload,
    canonical_action_sha256,
    canonical_vector_payload,
)
from e6.shared_oracle import (
    SharedAction,
    VectorANF,
    emit_compute_fanout_uncompute,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
    verify_vector_oracle_semantics,
)
from e6.shared_scheduler import (
    SharedSchedulerConfig,
    SharedUtilityWeights,
    program_resource_summary,
    schedule_shared_actions,
    shared_action_utility,
)
from src.contracts.codec import canonical_json_bytes, sha256_bytes


HELDOUT_EVALUATION_V1_SCHEMA = "xa.e6-replay-training-heldout-evaluation.v1-development"
HELDOUT_CASE_V1_SCHEMA = "xa.e6-replay-training-heldout-case.v1-development"
HELDOUT_STATISTICS_V1_SCHEMA = "xa.e6-replay-training-heldout-statistics.v1-development"
HELDOUT_WIDTHS = (4, 5)
DEFAULT_HELDOUT_SEED = 20260921
DEFAULT_BOOTSTRAP_SEED = 20260914
DEFAULT_SIGNFLIP_SEED = 20260915
DEFAULT_CASES_PER_WIDTH = 8
SOURCE_CANDIDATE_CAP = 256
DEFAULT_TOP_K = 10
DEFAULT_SCHEDULER_BUDGET = 2
DEFAULT_BOOTSTRAP_RESAMPLES = 4096
MAX_CASES_PER_WIDTH = 32
MAX_EXACT_SIGNFLIP_CLUSTERS = 20
DEFAULT_SIGNFLIP_RESAMPLES = 100000
TOP_K_RULE = "model_logit_desc_raw_utility_desc_action_sha256_asc"
SOURCE_CAP_RULE = "raw_utility_desc_action_sha256_asc_then_cap_256"
OUTCOME_CONTRACT = (
    "Y=emitted_total_abstract_score/direct_total_abstract_score;_lower_is_better;_"
    "failed_arm_uses_direct_fallback_and_ITT_Y=1"
)
CLAIM_BOUNDARY = (
    "single-researcher deterministic development causal experiment; no equal-"
    "compute claim, hardware evidence, quantum advantage, cryptographic "
    "generalization, or formal performance evidence"
)

_PRIMARY_TREATMENT = "qaoa_final_measurement_replay"
_PRIMARY_REFERENCE = "qaoa_permuted_label_control"
_SECONDARY_REFERENCES = (
    "classical_random_bitstring_replay",
    "classical_greedy_repeated_selection_replay",
)


def _sha(payload: object) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def _native_int(
    value: object,
    name: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        try:
            value = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{name} must be a finite real number") from exc
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _sha_ranked_bijection(
    *, seed: int, input_count: int, attempt: int
) -> tuple[int, ...]:
    """Return a permutation of ``range(2**n)`` using only SHA-256 ranking."""

    ranked: list[tuple[bytes, int]] = []
    for value in range(1 << input_count):
        payload = canonical_json_bytes(
            {
                "schema_version": "xa.e6-sha-ranked-bijection-key.v1",
                "seed": seed,
                "input_count": input_count,
                "attempt": attempt,
                "value": value,
            }
        )
        ranked.append((hashlib.sha256(payload).digest(), value))
    return tuple(value for _, value in sorted(ranked))


def generate_heldout_bijections_v1(
    *,
    seed: int = DEFAULT_HELDOUT_SEED,
    cases_per_width: int = DEFAULT_CASES_PER_WIDTH,
    widths: tuple[int, ...] = HELDOUT_WIDTHS,
) -> tuple[dict[str, object], ...]:
    """Generate fixed-seed ``n=4/5`` bijections with global orbit de-duplication.

    Returned dictionaries intentionally carry the actual :class:`VectorANF`
    for immediate evaluation.  Persisted evaluation rows carry the complete
    value table instead and can therefore reconstruct the vector independently.
    """

    seed = _native_int(seed, "seed")
    count = _native_int(
        cases_per_width,
        "cases_per_width",
        minimum=1,
        maximum=MAX_CASES_PER_WIDTH,
    )
    if type(widths) is not tuple or widths != HELDOUT_WIDTHS:
        raise ValueError("held-out development widths are fixed at exact (4, 5)")

    rows: list[dict[str, object]] = []
    seen_orbits: set[str] = set()
    for input_count in HELDOUT_WIDTHS:
        accepted = 0
        attempt = 0
        while accepted < count:
            if attempt >= count * 4096:
                raise RuntimeError("could not derive enough orbit-distinct bijections")
            values = _sha_ranked_bijection(
                seed=seed, input_count=input_count, attempt=attempt
            )
            if len(set(values)) != 1 << input_count:
                raise RuntimeError("SHA ranking failed to produce a bijection")
            vector = VectorANF.from_value_table(input_count, input_count, values)
            orbit_sha = canonical_vector_orbit_sha256(vector)
            current_attempt = attempt
            attempt += 1
            if orbit_sha in seen_orbits:
                continue
            seen_orbits.add(orbit_sha)
            vector_sha = _sha(canonical_vector_payload(vector))
            value_table_sha = _sha(
                {
                    "schema_version": "xa.e6-heldout-bijection-value-table.v1",
                    "input_count": input_count,
                    "output_count": input_count,
                    "values": list(values),
                }
            )
            case_id = (
                f"heldout-n{input_count}-c{accepted:03d}-" f"{value_table_sha[:12]}"
            )
            rows.append(
                {
                    "case_id": case_id,
                    "input_count": input_count,
                    "output_count": input_count,
                    "accepted_index": accepted,
                    "derivation_attempt": current_attempt,
                    "value_table": values,
                    "value_table_sha256": value_table_sha,
                    "vector": vector,
                    "vector_sha256": vector_sha,
                    "orbit_cluster_sha256": orbit_sha,
                    "whole_vector_cluster_sha256": whole_vector_cluster_id(vector),
                }
            )
            accepted += 1
    if len(seen_orbits) != len(rows):  # pragma: no cover - construction invariant
        raise RuntimeError("held-out orbit de-duplication failed")
    return tuple(rows)


def _arm_neutral_action_universe(
    vector: VectorANF, weights: SharedUtilityWeights
) -> tuple[tuple[SharedAction, ...], tuple[float, ...], tuple[str, ...], int]:
    generated = enumerate_monomial_shared_actions(
        vector
    ) + enumerate_semi_affine_shared_actions(vector, max_affine_weight=3)
    by_sha: dict[str, tuple[SharedAction, float]] = {}
    for action in generated:
        action_sha = canonical_action_sha256(action)
        utility = float(shared_action_utility(action, weights=weights))
        previous = by_sha.get(action_sha)
        if previous is not None and previous[0] != action:
            raise RuntimeError("canonical action SHA collision")
        by_sha[action_sha] = (action, utility)
    ranked = sorted(
        (
            (action, utility, action_sha)
            for action_sha, (action, utility) in by_sha.items()
        ),
        key=lambda item: (-item[1], item[2]),
    )
    capped = ranked[:SOURCE_CANDIDATE_CAP]
    return (
        tuple(item[0] for item in capped),
        tuple(item[1] for item in capped),
        tuple(item[2] for item in capped),
        len(ranked),
    )


def _model_forward(
    model: object,
    vector: VectorANF,
    actions: tuple[SharedAction, ...],
) -> tuple[tuple[float, ...], float]:
    forward = getattr(model, "forward_one", None)
    if callable(forward):
        raw = forward(vector, actions)
    elif callable(model):
        raw = model(vector, actions)
    else:
        raise TypeError("arm model must be callable or expose forward_one")
    if type(raw) not in {tuple, list} or len(raw) != 2:
        raise TypeError("model forward must return exactly (logits, value)")
    raw_logits, raw_value = raw
    if hasattr(raw_logits, "detach"):
        raw_logits = raw_logits.detach().cpu().reshape(-1).tolist()
    if not isinstance(raw_logits, Sequence) or isinstance(
        raw_logits, (str, bytes, bytearray)
    ):
        raise TypeError("model logits must be a finite one-dimensional sequence")
    logits = tuple(
        _finite_float(value, f"model_logits[{index}]")
        for index, value in enumerate(raw_logits)
    )
    if len(logits) != len(actions):
        raise ValueError("model logits must align with the common source pool")
    if hasattr(raw_value, "detach"):
        detached = raw_value.detach().cpu()
        if detached.numel() != 1:
            raise ValueError("model value must be scalar")
        raw_value = detached.item()
    value = _finite_float(raw_value, "model_value")
    return logits, value


def _semantic_dict(verification: object) -> dict[str, object]:
    to_dict = getattr(verification, "to_dict", None)
    if not callable(to_dict):
        raise TypeError("semantic verifier must return an object exposing to_dict")
    payload = to_dict()
    if type(payload) is not dict or type(payload.get("ok")) is not bool:
        raise TypeError("semantic verification payload violates its exact contract")
    return dict(payload)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        if numerator == 0.0:
            return 1.0
        raise ZeroDivisionError("nonzero program has a zero-score direct baseline")
    return float(numerator / denominator)


def _fallback_arm_row(
    *,
    failure_stage: str,
    failure_type: str,
    direct_resources: dict[str, object],
    direct_semantics: dict[str, object],
    logits: Sequence[float] = (),
    model_value: float | None = None,
    top_indices: Sequence[int] = (),
    selected_source_indices: Sequence[int] = (),
    selected_actions: Sequence[SharedAction] = (),
    attempted_resources: dict[str, object] | None = None,
    attempted_semantics: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "model_logits": list(logits),
        "model_value": model_value,
        "ranked_top_k_source_indices": list(top_indices),
        "attempted_selected_source_indices": list(selected_source_indices),
        "attempted_selected_action_sha256": [
            canonical_action_sha256(action) for action in selected_actions
        ],
        "attempted_selected_actions": [
            canonical_action_payload(action) for action in selected_actions
        ],
        "selected_source_indices": [],
        "selected_action_sha256": [],
        "selected_actions": [],
        "scheduler_objective": None,
        "attempted_program_resource_summary": attempted_resources,
        "attempted_semantic_verification": attempted_semantics,
        "final_program_resource_summary": dict(direct_resources),
        "final_semantic_verification": dict(direct_semantics),
        "score_ratio": 1.0,
        "semantic_verification": bool(direct_semantics["ok"]),
        "degraded": True,
        "observed_score_ratio_y": None,
        "itt_score_ratio_y": 1.0,
        "valid_observation": False,
        "analysis_eligible": False,
        "direct_fallback_used": True,
        "failure_stage": failure_stage,
        "failure_type": failure_type,
    }


def _evaluate_arm(
    *,
    model: object,
    vector: VectorANF,
    actions: tuple[SharedAction, ...],
    raw_utilities: tuple[float, ...],
    action_shas: tuple[str, ...],
    top_k: int,
    scheduler_budget: int,
    weights: SharedUtilityWeights,
    direct_resources: dict[str, object],
    direct_semantics: dict[str, object],
) -> dict[str, object]:
    logits: tuple[float, ...] = ()
    model_value: float | None = None
    top_indices: tuple[int, ...] = ()
    selected_source_indices: tuple[int, ...] = ()
    selected_actions: tuple[SharedAction, ...] = ()
    attempted_resources: dict[str, object] | None = None
    attempted_semantics: dict[str, object] | None = None
    stage = "model_forward"
    try:
        logits, model_value = _model_forward(model, vector, actions)
        stage = "top_k_ranking"
        top_indices = tuple(
            sorted(
                range(len(actions)),
                key=lambda index: (
                    -logits[index],
                    -raw_utilities[index],
                    action_shas[index],
                ),
            )[: min(top_k, len(actions))]
        )
        top_actions = tuple(actions[index] for index in top_indices)
        top_raw_utilities = tuple(raw_utilities[index] for index in top_indices)
        stage = "exact_scheduler"
        schedule = schedule_shared_actions(
            top_actions,
            config=SharedSchedulerConfig(
                method="exact",
                budget_requested=scheduler_budget,
                qaoa_max_variables=12,
                audit_max_variables=12,
            ),
            utilities=top_raw_utilities,
            utility_weights=weights,
        )
        selected_source_indices = tuple(
            top_indices[index] for index in schedule.selected_indices
        )
        selected_actions = tuple(actions[index] for index in selected_source_indices)
        stage = "emit"
        program = emit_compute_fanout_uncompute(vector, selected_actions, max_ancilla=2)
        attempted_resources = program_resource_summary(
            program, weights=weights
        ).to_dict()
        stage = "all_x_all_y_semantics"
        attempted_semantics = _semantic_dict(
            verify_vector_oracle_semantics(program, max_assignments=1 << 12)
        )
        if attempted_semantics["ok"] is not True:
            return _fallback_arm_row(
                failure_stage=stage,
                failure_type="SemanticVerificationFailure",
                direct_resources=direct_resources,
                direct_semantics=direct_semantics,
                logits=logits,
                model_value=model_value,
                top_indices=top_indices,
                selected_source_indices=selected_source_indices,
                selected_actions=selected_actions,
                attempted_resources=attempted_resources,
                attempted_semantics=attempted_semantics,
            )
        ratio = _ratio(
            float(attempted_resources["total_abstract_score"]),
            float(direct_resources["total_abstract_score"]),
        )
        return {
            "model_logits": list(logits),
            "model_value": model_value,
            "ranked_top_k_source_indices": list(top_indices),
            "selected_source_indices": list(selected_source_indices),
            "selected_action_sha256": [
                canonical_action_sha256(action) for action in selected_actions
            ],
            "selected_actions": [
                canonical_action_payload(action) for action in selected_actions
            ],
            "scheduler_objective": float(schedule.diagnostics["objective"]),
            "attempted_program_resource_summary": attempted_resources,
            "attempted_semantic_verification": attempted_semantics,
            "final_program_resource_summary": attempted_resources,
            "final_semantic_verification": attempted_semantics,
            "score_ratio": ratio,
            "semantic_verification": bool(attempted_semantics["ok"]),
            "degraded": False,
            "observed_score_ratio_y": ratio,
            "itt_score_ratio_y": ratio,
            "valid_observation": True,
            "analysis_eligible": True,
            "direct_fallback_used": False,
            "failure_stage": None,
            "failure_type": None,
        }
    except Exception as exc:
        return _fallback_arm_row(
            failure_stage=stage,
            failure_type=type(exc).__name__,
            direct_resources=direct_resources,
            direct_semantics=direct_semantics,
            logits=logits,
            model_value=model_value,
            top_indices=top_indices,
            selected_source_indices=selected_source_indices,
            selected_actions=selected_actions,
            attempted_resources=attempted_resources,
            attempted_semantics=attempted_semantics,
        )


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    ordered = sorted(float(value) for value in values)
    location = probability * (len(ordered) - 1)
    lower = int(math.floor(location))
    upper = int(math.ceil(location))
    if lower == upper:
        return ordered[lower]
    fraction = location - lower
    return float(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction)


def _equal_width_effect(
    effects_by_width: Mapping[int, Sequence[float]],
) -> tuple[dict[str, float], float]:
    width_means: dict[str, float] = {}
    for width in HELDOUT_WIDTHS:
        values = tuple(effects_by_width[width])
        if not values:
            raise ValueError(f"comparison has no n={width} clusters")
        width_means[str(width)] = float(sum(values) / len(values))
    estimate = float(sum(width_means.values()) / len(HELDOUT_WIDTHS))
    return width_means, estimate


def _bootstrap_distribution(
    effects_by_width: Mapping[int, Sequence[float]],
    *,
    seed: int,
    comparison: str,
    resamples: int,
) -> tuple[float, ...]:
    distribution: list[float] = []
    for replicate in range(resamples):
        sampled: dict[int, list[float]] = {width: [] for width in HELDOUT_WIDTHS}
        for width in HELDOUT_WIDTHS:
            values = tuple(effects_by_width[width])
            for slot in range(len(values)):
                digest = hashlib.sha256(
                    canonical_json_bytes(
                        {
                            "schema_version": "xa.e6-heldout-cluster-bootstrap-key.v1",
                            "seed": seed,
                            "comparison": comparison,
                            "replicate": replicate,
                            "input_count": width,
                            "draw_slot": slot,
                        }
                    )
                ).digest()
                index = int.from_bytes(digest[:8], "big") % len(values)
                sampled[width].append(values[index])
        _, effect = _equal_width_effect(sampled)
        distribution.append(effect)
    return tuple(distribution)


def _signflip_distribution(
    ordered_effects: Sequence[tuple[int, str, float]],
    *,
    seed: int,
    comparison: str,
    resamples: int,
) -> tuple[tuple[float, ...], str]:
    count = len(ordered_effects)
    distributions: list[float] = []
    if count <= MAX_EXACT_SIGNFLIP_CLUSTERS:
        sign_rows = itertools.product((-1.0, 1.0), repeat=count)
        method = "exact_all_cluster_sign_assignments"
    else:
        roster_sha256 = _sha(
            [
                {
                    "input_count": width,
                    "whole_vector_cluster_sha256": cluster,
                }
                for width, cluster, _ in ordered_effects
            ]
        )

        def deterministic_rows():
            for replicate in range(resamples):
                # One SHA block supplies 256 independent deterministic sign
                # bits.  Packing avoids millions of redundant JSON/SHA calls
                # in the full 32-cluster, 100k-assignment profile while still
                # binding every bit to the ordered whole-vector roster.
                blocks = tuple(
                    hashlib.sha256(
                        canonical_json_bytes(
                            {
                                "schema_version": (
                                    "xa.e6-heldout-packed-signflip-key.v1"
                                ),
                                "seed": seed,
                                "comparison": comparison,
                                "replicate": replicate,
                                "block": block,
                                "cluster_roster_sha256": roster_sha256,
                            }
                        )
                    ).digest()
                    for block in range((count + 255) // 256)
                )
                signs = tuple(
                    (
                        -1.0
                        if blocks[index // 256][(index % 256) // 8] & (1 << (index % 8))
                        else 1.0
                    )
                    for index in range(count)
                )
                yield tuple(signs)

        sign_rows = deterministic_rows()
        method = "sha256_deterministic_packed_cluster_sign_assignments"
    for signs in sign_rows:
        by_width: dict[int, list[float]] = {width: [] for width in HELDOUT_WIDTHS}
        for sign, (width, _, effect) in zip(signs, ordered_effects):
            by_width[width].append(sign * effect)
        _, null_effect = _equal_width_effect(by_width)
        distributions.append(null_effect)
    return tuple(distributions), method


def _comparison_statistics(
    case_rows: tuple[dict[str, object], ...],
    *,
    treatment_arm: str,
    reference_arm: str,
    role: str,
    bootstrap_seed: int,
    signflip_seed: int,
    bootstrap_resamples: int,
    signflip_resamples: int,
) -> dict[str, object]:
    comparison = f"{treatment_arm}_minus_{reference_arm}"
    effects_by_width: dict[int, list[float]] = {width: [] for width in HELDOUT_WIDTHS}
    ordered_effects: list[tuple[int, str, float]] = []
    valid_pairs = 0
    fallback_pairs = 0
    wins = losses = ties = 0
    for row in sorted(
        case_rows,
        key=lambda item: (int(item["input_count"]), str(item["case_id"])),
    ):
        width = int(row["input_count"])
        if width not in effects_by_width:
            raise ValueError("statistics require only fixed n=4/5 rows")
        arms = row["arms"]
        if type(arms) is not dict:
            raise TypeError("case row arms must be an exact dict")
        treatment = arms[treatment_arm]
        reference = arms[reference_arm]
        if type(treatment) is not dict or type(reference) is not dict:
            raise TypeError("arm rows must be exact dicts")
        treatment_y = _finite_float(treatment["itt_score_ratio_y"], "treatment ITT Y")
        reference_y = _finite_float(reference["itt_score_ratio_y"], "reference ITT Y")
        effect = treatment_y - reference_y
        cluster = str(row["whole_vector_cluster_sha256"])
        effects_by_width[width].append(effect)
        ordered_effects.append((width, cluster, effect))
        pair_valid = (
            treatment.get("valid_observation") is True
            and reference.get("valid_observation") is True
            and treatment.get("direct_fallback_used") is False
            and reference.get("direct_fallback_used") is False
        )
        valid_pairs += int(pair_valid)
        fallback_pairs += int(not pair_valid)
        tolerance = 1.0e-12 * max(1.0, abs(treatment_y), abs(reference_y))
        if treatment_y < reference_y - tolerance:
            wins += 1
        elif treatment_y > reference_y + tolerance:
            losses += 1
        else:
            ties += 1

    width_means, estimate = _equal_width_effect(effects_by_width)
    bootstrap = _bootstrap_distribution(
        effects_by_width,
        seed=bootstrap_seed,
        comparison=comparison,
        resamples=bootstrap_resamples,
    )
    signflip, signflip_method = _signflip_distribution(
        ordered_effects,
        seed=signflip_seed,
        comparison=comparison,
        resamples=signflip_resamples,
    )
    extreme = sum(abs(value) >= abs(estimate) - 1.0e-15 for value in signflip)
    # Use the same conservative plus-one convention for exact and sampled
    # assignments so tiny/full profiles cannot switch p-value conventions.
    p_value = float((extreme + 1) / (len(signflip) + 1))
    return {
        "comparison": comparison,
        "role": role,
        "treatment_arm": treatment_arm,
        "reference_arm": reference_arm,
        "estimand": (
            "equal_n4_n5_weighted_mean_paired_ITT_Y_difference;_negative_favours_"
            "treatment"
        ),
        "cluster_unit": "whole_vector_boolean_function_all_outputs",
        "case_count": len(ordered_effects),
        "width_case_counts": {
            str(width): len(effects_by_width[width]) for width in HELDOUT_WIDTHS
        },
        "valid_pair_count": valid_pairs,
        "direct_fallback_pair_count": fallback_pairs,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "width_mean_effects": width_means,
        "effect_estimate": estimate,
        "bootstrap": {
            "method": "sha256_deterministic_within_width_cluster_resampling",
            "resamples": bootstrap_resamples,
            "confidence_level": 0.95,
            "ci_lower": _quantile(bootstrap, 0.025),
            "ci_upper": _quantile(bootstrap, 0.975),
            "distribution_sha256": _sha(list(bootstrap)),
        },
        "signflip": {
            "method": signflip_method,
            "assignments": len(signflip),
            "alternative": "two_sided",
            "p_value": p_value,
            "distribution_sha256": _sha(list(signflip)),
        },
    }


def paired_arm_statistics_v1(
    case_rows: tuple[dict[str, object], ...],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    signflip_resamples: int = DEFAULT_SIGNFLIP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    signflip_seed: int = DEFAULT_SIGNFLIP_SEED,
    utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> dict[str, object]:
    """Compute width-equal paired cluster inference and the claim gate."""

    if type(case_rows) is not tuple or not case_rows:
        raise TypeError("case_rows must be a non-empty exact tuple")
    seen_case_ids: set[str] = set()
    seen_clusters: set[str] = set()
    stratum_counts = {width: 0 for width in HELDOUT_WIDTHS}
    for index, row in enumerate(case_rows):
        if type(row) is not dict:
            raise TypeError(f"case_rows[{index}] must be an exact dict")
        case_id = row.get("case_id")
        if type(case_id) is not str or not case_id or case_id in seen_case_ids:
            raise ValueError("statistics case IDs must be non-empty and unique")
        seen_case_ids.add(case_id)
        width = row.get("input_count")
        if type(width) is not int or width not in HELDOUT_WIDTHS:
            raise ValueError("statistics rows must use only native n=4/5 widths")
        stratum_counts[width] += 1
        cluster = row.get("whole_vector_cluster_sha256")
        if (
            type(cluster) is not str
            or len(cluster) != 64
            or any(character not in "0123456789abcdef" for character in cluster)
            or cluster in seen_clusters
        ):
            raise ValueError(
                "whole-vector cluster SHA values must be lowercase and globally unique"
            )
        seen_clusters.add(cluster)
        arms = row.get("arms")
        if type(arms) is not dict or set(arms) != set(SOURCE_ARMS):
            raise ValueError("statistics rows require exactly the four source arms")
    if len(set(stratum_counts.values())) != 1 or 0 in stratum_counts.values():
        raise ValueError("statistics require equal non-empty n=4 and n=5 strata")
    bootstrap_seed = _native_int(bootstrap_seed, "bootstrap_seed")
    signflip_seed = _native_int(signflip_seed, "signflip_seed")
    resamples = _native_int(resamples, "resamples", minimum=32, maximum=1_000_000)
    signflip_resamples = _native_int(
        signflip_resamples,
        "signflip_resamples",
        minimum=32,
        maximum=1_000_000,
    )
    primary = _comparison_statistics(
        case_rows,
        treatment_arm=_PRIMARY_TREATMENT,
        reference_arm=_PRIMARY_REFERENCE,
        role="primary_claim_gating_comparison",
        bootstrap_seed=bootstrap_seed,
        bootstrap_resamples=resamples,
        signflip_resamples=signflip_resamples,
        signflip_seed=signflip_seed,
    )
    secondary = [
        _comparison_statistics(
            case_rows,
            treatment_arm=_PRIMARY_TREATMENT,
            reference_arm=reference,
            role="secondary_descriptive_only_not_claim_gating",
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=resamples,
            signflip_resamples=signflip_resamples,
            signflip_seed=signflip_seed,
        )
        for reference in _SECONDARY_REFERENCES
    ]
    primary_bootstrap = primary["bootstrap"]
    primary_signflip = primary["signflip"]
    assert isinstance(primary_bootstrap, dict)
    assert isinstance(primary_signflip, dict)
    all_primary_pairs_valid = (
        primary["valid_pair_count"] == primary["case_count"]
        and primary["direct_fallback_pair_count"] == 0
    )
    both_width_effects_below_zero = all(
        float(primary["width_mean_effects"][str(width)]) < 0.0
        for width in HELDOUT_WIDTHS
    )
    claim_supported = bool(
        all_primary_pairs_valid
        and float(primary["effect_estimate"]) < 0.0
        and both_width_effects_below_zero
        and float(primary_bootstrap["ci_upper"]) < 0.0
        and float(primary_signflip["p_value"]) < 0.05
    )
    return {
        "schema_version": HELDOUT_STATISTICS_V1_SCHEMA,
        "outcome_contract": OUTCOME_CONTRACT,
        "bootstrap_seed": bootstrap_seed,
        "signflip_seed": signflip_seed,
        "width_weighting": "n4_and_n5_each_weight_one_half",
        "primary": primary,
        "secondary": secondary,
        "claim_gate": {
            "scope": "heldout_development_effect_only",
            "requires_all_primary_pairs_valid_without_fallback": True,
            "requires_primary_effect_below_zero": True,
            "requires_both_width_mean_effects_below_zero": True,
            "requires_primary_bootstrap_ci_upper_below_zero": True,
            "requires_two_sided_signflip_p_below_0_05": True,
            "all_primary_pairs_valid_without_fallback": all_primary_pairs_valid,
            "both_width_mean_effects_below_zero": both_width_effects_below_zero,
            "claim_supported": claim_supported,
            "formal_evaluation": False,
            "performance_evidence": False,
        },
    }


def evaluate_replay_training_heldout_v1(
    models: dict[str, object],
    *,
    seed: int = DEFAULT_HELDOUT_SEED,
    cases_per_width: int = DEFAULT_CASES_PER_WIDTH,
    top_k: int = DEFAULT_TOP_K,
    scheduler_budget: int = DEFAULT_SCHEDULER_BUDGET,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    signflip_resamples: int = DEFAULT_SIGNFLIP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    signflip_seed: int = DEFAULT_SIGNFLIP_SEED,
    utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> dict[str, object]:
    """Evaluate four replay-trained inference models on one common held-out set."""

    if type(models) is not dict:
        raise TypeError("models must be an exact native dict")
    if set(models) != set(SOURCE_ARMS):
        raise ValueError("models must contain exactly the four registered source arms")
    if type(utility_weights) is not SharedUtilityWeights:
        raise TypeError("utility_weights must be exact SharedUtilityWeights")
    weights = SharedUtilityWeights(**asdict(utility_weights))
    seed = _native_int(seed, "seed")
    bootstrap_seed = _native_int(bootstrap_seed, "bootstrap_seed")
    signflip_seed = _native_int(signflip_seed, "signflip_seed")
    cases_per_width = _native_int(
        cases_per_width,
        "cases_per_width",
        minimum=1,
        maximum=MAX_CASES_PER_WIDTH,
    )
    top_k = _native_int(top_k, "top_k", minimum=1, maximum=DEFAULT_TOP_K)
    scheduler_budget = _native_int(
        scheduler_budget,
        "scheduler_budget",
        minimum=1,
        maximum=DEFAULT_SCHEDULER_BUDGET,
    )
    bootstrap_resamples = _native_int(
        bootstrap_resamples,
        "bootstrap_resamples",
        minimum=32,
        maximum=1_000_000,
    )
    signflip_resamples = _native_int(
        signflip_resamples,
        "signflip_resamples",
        minimum=32,
        maximum=1_000_000,
    )
    generated = generate_heldout_bijections_v1(
        seed=seed, cases_per_width=cases_per_width
    )
    case_rows: list[dict[str, object]] = []
    for generated_row in generated:
        vector = generated_row["vector"]
        if type(vector) is not VectorANF:  # pragma: no cover - construction invariant
            raise RuntimeError("generated held-out case lost its VectorANF")
        actions, raw_utilities, action_shas, source_count = (
            _arm_neutral_action_universe(vector, weights)
        )
        direct_program = emit_compute_fanout_uncompute(vector, (), max_ancilla=2)
        direct_resources = program_resource_summary(
            direct_program, weights=weights
        ).to_dict()
        direct_semantics = _semantic_dict(
            verify_vector_oracle_semantics(direct_program, max_assignments=1 << 12)
        )
        if direct_semantics["ok"] is not True:
            raise RuntimeError("direct fallback failed exhaustive oracle semantics")
        arm_rows = {
            arm: _evaluate_arm(
                model=models[arm],
                vector=vector,
                actions=actions,
                raw_utilities=raw_utilities,
                action_shas=action_shas,
                top_k=top_k,
                scheduler_budget=scheduler_budget,
                weights=weights,
                direct_resources=direct_resources,
                direct_semantics=direct_semantics,
            )
            for arm in SOURCE_ARMS
        }
        case_rows.append(
            {
                "schema_version": HELDOUT_CASE_V1_SCHEMA,
                "case_id": generated_row["case_id"],
                "input_count": generated_row["input_count"],
                "output_count": generated_row["output_count"],
                "accepted_index": generated_row["accepted_index"],
                "derivation_attempt": generated_row["derivation_attempt"],
                "value_table": list(generated_row["value_table"]),
                "value_table_sha256": generated_row["value_table_sha256"],
                "vector_sha256": generated_row["vector_sha256"],
                "orbit_cluster_sha256": generated_row["orbit_cluster_sha256"],
                "whole_vector_cluster_sha256": generated_row[
                    "whole_vector_cluster_sha256"
                ],
                "source_candidate_count": source_count,
                "capped_candidate_count": len(actions),
                "common_pool_action_sha256": list(action_shas),
                "common_pool_raw_utilities": list(raw_utilities),
                "direct_resource_score": float(
                    direct_resources["total_abstract_score"]
                ),
                "direct_program_resource_summary": direct_resources,
                "direct_semantic_verification": direct_semantics,
                "arms": arm_rows,
                "formal_evaluation": False,
                "performance_evidence": False,
            }
        )
    statistics = paired_arm_statistics_v1(
        tuple(case_rows),
        resamples=bootstrap_resamples,
        signflip_resamples=signflip_resamples,
        bootstrap_seed=bootstrap_seed,
        signflip_seed=signflip_seed,
    )
    result: dict[str, object] = {
        "schema_version": HELDOUT_EVALUATION_V1_SCHEMA,
        "protocol": {
            "evaluation_role": "deterministic_synthetic_heldout_development",
            "dataset_generator": "sha256_ranked_bijections_no_python_rng",
            "input_widths": list(HELDOUT_WIDTHS),
            "dataset_seed": seed,
            "cases_per_width": cases_per_width,
            "global_orbit_deduplication": True,
            "source_candidate_cap": SOURCE_CANDIDATE_CAP,
            "source_candidate_cap_rule": SOURCE_CAP_RULE,
            "semi_affine_max_factor_weight": 3,
            "top_k": top_k,
            "top_k_rule": TOP_K_RULE,
            "scheduler": "exact_conflict_aware_shared_action_scheduler",
            "scheduler_utility": "arm_neutral_raw_analytic_utility",
            "scheduler_budget": scheduler_budget,
            "utility_weights": asdict(weights),
            "semantic_verification": "exhaustive_all_x_all_initial_y",
            "arm_order": list(SOURCE_ARMS),
            "outcome_contract": OUTCOME_CONTRACT,
            "cluster_unit": "whole_vector_boolean_function_all_outputs",
            "width_weighting": "n4_and_n5_each_weight_one_half",
            "bootstrap_resamples": bootstrap_resamples,
            "bootstrap_seed": bootstrap_seed,
            "signflip_resamples_requested": signflip_resamples,
            "signflip_seed": signflip_seed,
            "signflip_exact_threshold_clusters": MAX_EXACT_SIGNFLIP_CLUSTERS,
        },
        "case_rows": case_rows,
        "statistics": statistics,
        "claim_boundary": CLAIM_BOUNDARY,
        "heldout_development_evaluation": True,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    result["evaluation_sha256"] = _sha(result)
    return result


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "DEFAULT_BOOTSTRAP_SEED",
    "DEFAULT_CASES_PER_WIDTH",
    "DEFAULT_HELDOUT_SEED",
    "DEFAULT_SCHEDULER_BUDGET",
    "DEFAULT_SIGNFLIP_RESAMPLES",
    "DEFAULT_SIGNFLIP_SEED",
    "DEFAULT_TOP_K",
    "HELDOUT_CASE_V1_SCHEMA",
    "HELDOUT_EVALUATION_V1_SCHEMA",
    "HELDOUT_STATISTICS_V1_SCHEMA",
    "HELDOUT_WIDTHS",
    "OUTCOME_CONTRACT",
    "SOURCE_CANDIDATE_CAP",
    "SOURCE_CAP_RULE",
    "TOP_K_RULE",
    "evaluate_replay_training_heldout_v1",
    "generate_heldout_bijections_v1",
    "paired_arm_statistics_v1",
]
