"""Deterministic signal diagnostics for the E6 replay-to-policy path.

The functions in this module are deliberately analysis-only.  They do not
train a model, mutate a corpus, write an artefact, or assign evidence status.
They expose the quantities needed to decide whether a replay teacher and a
trained policy rank the same actions as the arm-neutral raw-resource utility.

All public results contain only canonical JSON-compatible native Python types.
Undefined correlations (a constant input on either side) are represented by a
finite ``0.0`` together with an explicit ``*_defined=False`` flag; NaN and
infinity are never emitted.
"""

from __future__ import annotations

import math
from typing import Sequence

from e6.final_measurement_replay_v2 import SOURCE_ARMS, ReplayTargetsV2
from e6.frozen_case import canonical_action_sha256
from e6.replay_training_corpus_v1 import (
    CANDIDATE_CAP,
    SCHEDULER_BUDGET,
    ReplayTrainingCorpusV1,
    ReplayTrainingGroupV1,
)
from e6.shared_oracle import (
    SharedAction,
    VectorANF,
    emit_compute_fanout_uncompute,
    validate_shared_action,
    verify_vector_oracle_semantics,
)
from e6.shared_scheduler import (
    SharedSchedulerConfig,
    SharedUtilityWeights,
    program_resource_summary,
    schedule_shared_actions,
    shared_action_utility,
)


REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA = (
    "xa.e6-replay-signal-diagnostic-case.v1-development"
)
MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA = (
    "xa.e6-model-ranking-diagnostic-case.v1-development"
)
REPLAY_SIGNAL_DIAGNOSTIC_AGGREGATE_V1_SCHEMA = (
    "xa.e6-replay-signal-diagnostic-aggregate.v1-development"
)
MODEL_RANKING_DIAGNOSTIC_AGGREGATE_V1_SCHEMA = (
    "xa.e6-model-ranking-diagnostic-aggregate.v1-development"
)
TOP_K_RULE = "model_logit_desc_raw_utility_desc_action_sha256_asc"
RAW_BEST_RULE = "all_actions_exactly_equal_to_the_maximum_raw_utility"
PROJECTION_RULE = (
    "model_top_k_then_exact_conflict_aware_scheduler_using_only_arm_neutral_"
    "raw_utilities"
)
CORRELATION_RULE = (
    "pearson_and_tie_aware_average_rank_spearman;_constant_input_is_undefined_"
    "with_finite_zero_placeholder"
)


_MODEL_CASE_FIELDS = frozenset(
    {
        "schema_version",
        "split",
        "case_id",
        "arm",
        "value_weight",
        "candidate_count",
        "top_k",
        "scheduler_budget",
        "action_sha256",
        "raw_utilities",
        "model_logits",
        "model_policy",
        "model_value",
        "model_raw_pearson",
        "model_raw_pearson_defined",
        "model_raw_spearman",
        "model_raw_spearman_defined",
        "model_entropy",
        "model_normalized_entropy",
        "model_effective_support",
        "raw_best_source_indices",
        "raw_best_count",
        "top_k_source_indices",
        "raw_best_top_k_hit_count",
        "raw_best_top_k_recall",
        "selected_source_indices",
        "selected_count",
        "selected_empty",
        "projection_dummy_selected",
        "projection_objective",
        "projection_uses_arm_neutral_raw_utilities",
        "direct_resource_score",
        "final_resource_score",
        "score_ratio_y",
        "semantic_verification",
        "degraded",
        "direct_fallback_used",
        "fallback_reason",
    }
)

_CASE_FIELDS = _MODEL_CASE_FIELDS | frozenset(
    {
        "teacher_role",
        "teacher_policy",
        "teacher_value_target",
        "policy_observation_weight",
        "feasible_fraction",
        "value_observation_weight",
        "teacher_raw_pearson",
        "teacher_raw_pearson_defined",
        "teacher_raw_spearman",
        "teacher_raw_spearman_defined",
        "teacher_entropy",
        "teacher_normalized_entropy",
        "teacher_effective_support",
        "teacher_raw_positive_mass",
        "teacher_raw_best_mass",
        "teacher_argmax_source_indices",
        "teacher_argmax_count",
        "teacher_argmax_raw_best_hit_count",
        "teacher_argmax_raw_best_hit",
        "policy_cross_entropy",
        "policy_kl_divergence",
        "value_error",
        "value_absolute_error",
        "value_squared_error",
        "effective_value_loss_contribution",
    }
)


def _native_string(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a native string")
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


def _native_integer(
    value: object, name: str, *, minimum: int = 0, maximum: int | None = None
) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if value < minimum or (maximum is not None and value > maximum):
        suffix = f" and <= {maximum}" if maximum is not None else ""
        raise ValueError(f"{name} must be >= {minimum}{suffix}")
    return value


def _native_finite(
    value: object, name: str, *, minimum: float | None = None
) -> float:
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a native finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and converted < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return 0.0 if converted == 0.0 else converted


def _finite_result(value: float, name: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise FloatingPointError(f"computed {name} is not finite")
    return 0.0 if converted == 0.0 else converted


def _finite_tuple(value: object, name: str, *, nonempty: bool = True) -> tuple[float, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact native tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be non-empty")
    return tuple(
        _native_finite(item, f"{name}[{index}]")
        for index, item in enumerate(value)
    )


def _probability_tuple(value: object, name: str) -> tuple[float, ...]:
    probabilities = _finite_tuple(value, name)
    if any(item < 0.0 for item in probabilities):
        raise ValueError(f"{name} must contain non-negative probabilities")
    total = math.fsum(probabilities)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError(f"{name} must sum to one")
    return probabilities


def _softmax_and_log(values: tuple[float, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    maximum = max(values)
    shifted = tuple(value - maximum for value in values)
    exponentials = tuple(math.exp(value) for value in shifted)
    denominator = math.fsum(exponentials)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise FloatingPointError("softmax denominator is not finite and positive")
    log_denominator = math.log(denominator)
    log_probabilities = tuple(
        _finite_result(value - log_denominator, "log probability")
        for value in shifted
    )
    probabilities = tuple(
        _finite_result(math.exp(value), "model probability")
        for value in log_probabilities
    )
    return probabilities, log_probabilities


def _scaled_pearson(
    left: tuple[float, ...], right: tuple[float, ...]
) -> tuple[float, bool]:
    if len(left) != len(right):
        raise ValueError("correlation inputs must have equal length")
    if len(left) < 2:
        return 0.0, False

    def centred(values: tuple[float, ...]) -> tuple[float, ...]:
        scale = max(abs(value) for value in values)
        if scale == 0.0:
            return (0.0,) * len(values)
        scaled = tuple(value / scale for value in values)
        mean = math.fsum(scaled) / len(scaled)
        return tuple(value - mean for value in scaled)

    left_c = centred(left)
    right_c = centred(right)
    left_norm = math.fsum(value * value for value in left_c)
    right_norm = math.fsum(value * value for value in right_c)
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0, False
    correlation = math.fsum(
        left_value * right_value
        for left_value, right_value in zip(left_c, right_c)
    ) / math.sqrt(left_norm * right_norm)
    correlation = max(-1.0, min(1.0, correlation))
    return _finite_result(correlation, "correlation"), True


def _average_tie_ranks(values: tuple[float, ...]) -> tuple[float, ...]:
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        # Ranks are one-based.  The average of [start + 1, end] is below.
        average = (start + 1 + end) / 2.0
        for offset in range(start, end):
            ranks[ordered[offset]] = average
        start = end
    return tuple(ranks)


def _spearman(
    left: tuple[float, ...], right: tuple[float, ...]
) -> tuple[float, bool]:
    return _scaled_pearson(_average_tie_ranks(left), _average_tie_ranks(right))


def _entropy(probabilities: tuple[float, ...]) -> tuple[float, float, float]:
    entropy = -math.fsum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0.0
    )
    entropy = _finite_result(entropy, "entropy")
    normalized = (
        entropy / math.log(len(probabilities)) if len(probabilities) > 1 else 0.0
    )
    return (
        entropy,
        _finite_result(normalized, "normalized entropy"),
        _finite_result(math.exp(entropy), "effective support"),
    )


def _model_forward(
    model: object,
    vector: VectorANF,
    actions: tuple[SharedAction, ...],
    weights: SharedUtilityWeights,
) -> tuple[tuple[float, ...], float]:
    forward = getattr(model, "forward_one", None)
    if not callable(forward):
        raise TypeError("model must expose callable forward_one")
    raw = forward(vector, actions, weights=weights)
    if type(raw) not in {tuple, list} or len(raw) != 2:
        raise TypeError("model.forward_one must return exactly (logits, value)")
    raw_logits, raw_value = raw
    if hasattr(raw_logits, "detach"):
        detached = raw_logits.detach().cpu()
        if getattr(detached, "ndim", None) != 1:
            raise ValueError("model logits tensor must be one-dimensional")
        raw_logits = detached.tolist()
    if type(raw_logits) not in {tuple, list}:
        raise TypeError("model logits must be a native sequence or tensor")
    logits = tuple(
        _native_finite(value, f"model_logits[{index}]")
        for index, value in enumerate(raw_logits)
    )
    if len(logits) != len(actions):
        raise ValueError("model logits must align with actions")
    if hasattr(raw_value, "detach"):
        detached_value = raw_value.detach().cpu()
        if getattr(detached_value, "ndim", None) != 0:
            raise ValueError("model value tensor must be scalar")
        raw_value = detached_value.item()
    value = _native_finite(raw_value, "model_value")
    return logits, value


def _rank_top_k(
    logits: tuple[float, ...],
    raw_utilities: tuple[float, ...],
    action_shas: tuple[str, ...],
    top_k: int,
) -> tuple[int, ...]:
    return tuple(
        sorted(
            range(len(logits)),
            key=lambda index: (
                -logits[index],
                -raw_utilities[index],
                action_shas[index],
            ),
        )[:top_k]
    )


def diagnose_model_ranking_case_v1(
    *,
    split: str,
    case_id: str,
    arm: str,
    value_weight: float,
    vector: VectorANF,
    actions: tuple[SharedAction, ...],
    raw_utilities: tuple[float, ...],
    model: object,
    top_k: int,
    scheduler_budget: int,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> dict[str, object]:
    """Diagnose model ranking on an action pool that has no replay teacher.

    This is the correct entry point for an expanded validation/OOD view.  It
    intentionally has no teacher arguments or teacher-shaped output fields.
    """

    split = _native_string(split, "split")
    case_id = _native_string(case_id, "case_id")
    arm = _native_string(arm, "arm")
    value_weight = _native_finite(value_weight, "value_weight", minimum=0.0)
    if type(vector) is not VectorANF:
        raise TypeError("vector must be exact VectorANF")
    if type(actions) is not tuple or not actions:
        raise TypeError("actions must be an exact non-empty tuple")
    if type(weights) is not SharedUtilityWeights:
        raise TypeError("weights must be exact SharedUtilityWeights")
    for index, action in enumerate(actions):
        try:
            validate_shared_action(vector, action)
        except Exception as exc:
            raise type(exc)(f"actions[{index}] is invalid: {exc}") from exc
    action_shas = tuple(canonical_action_sha256(action) for action in actions)
    if len(set(action_shas)) != len(action_shas):
        raise ValueError("actions contain duplicate canonical identities")

    raw = _finite_tuple(raw_utilities, "raw_utilities")
    if len(raw) != len(actions):
        raise ValueError("actions and raw_utilities must align")
    derived_raw = tuple(
        _finite_result(
            shared_action_utility(action, weights=weights),
            f"derived_raw_utilities[{index}]",
        )
        for index, action in enumerate(actions)
    )
    if raw != derived_raw:
        raise ValueError(
            "raw_utilities must exactly equal shared_action_utility(action, weights) "
            "for every action"
        )
    top_k = _native_integer(top_k, "top_k", minimum=1, maximum=len(actions))
    scheduler_budget = _native_integer(
        scheduler_budget, "scheduler_budget", minimum=1
    )
    if top_k + min(top_k, scheduler_budget) > 12:
        raise ValueError("top_k plus effective scheduler budget must be <= 12")

    logits, model_value = _model_forward(model, vector, actions, weights)
    model_policy, _ = _softmax_and_log(logits)
    model_raw_pearson, model_raw_pearson_defined = _scaled_pearson(logits, raw)
    model_raw_spearman, model_raw_spearman_defined = _spearman(logits, raw)
    model_entropy, model_normalized_entropy, model_effective_support = _entropy(
        model_policy
    )

    raw_maximum = max(raw)
    raw_best = tuple(index for index, value in enumerate(raw) if value == raw_maximum)
    top_indices = _rank_top_k(logits, raw, action_shas, top_k)
    top_raw_hits = len(set(raw_best) & set(top_indices))

    # The model chooses the top-k *set*.  Canonicalise that set before exact
    # scheduling so equal-objective exact solutions cannot inherit the model's
    # logit order as an unintended tie-break.
    canonical_top_indices = tuple(sorted(top_indices, key=lambda index: action_shas[index]))
    top_actions = tuple(actions[index] for index in canonical_top_indices)
    top_raw = tuple(raw[index] for index in canonical_top_indices)
    schedule = schedule_shared_actions(
        top_actions,
        config=SharedSchedulerConfig(
            method="exact",
            budget_requested=scheduler_budget,
            qaoa_max_variables=12,
            audit_max_variables=12,
        ),
        utilities=top_raw,
        utility_weights=weights,
    )
    selected = tuple(
        canonical_top_indices[index] for index in schedule.selected_indices
    )
    objective = _native_finite(
        schedule.diagnostics.get("objective"), "projection_objective"
    )

    assignment_count = 1 << (vector.input_count + vector.output_count)
    if assignment_count > 1 << 16:
        raise ValueError(
            "exhaustive semantic projection is capped at 2**16 assignments"
        )
    direct_program = emit_compute_fanout_uncompute(vector, (), max_ancilla=2)
    direct_resource_score = _native_finite(
        program_resource_summary(direct_program, weights=weights).total_abstract_score,
        "direct_resource_score",
        minimum=0.0,
    )
    direct_semantics = verify_vector_oracle_semantics(
        direct_program, max_assignments=assignment_count
    )
    if direct_semantics.ok is not True:
        raise RuntimeError("direct program failed exhaustive vector semantics")

    degraded = False
    direct_fallback_used = False
    fallback_reason: str | None = None
    final_resource_score = direct_resource_score
    semantic_verification = True
    try:
        selected_actions = tuple(actions[index] for index in selected)
        selected_program = emit_compute_fanout_uncompute(
            vector, selected_actions, max_ancilla=2
        )
        attempted_score = _native_finite(
            program_resource_summary(
                selected_program, weights=weights
            ).total_abstract_score,
            "selected_resource_score",
            minimum=0.0,
        )
        attempted_semantics = verify_vector_oracle_semantics(
            selected_program, max_assignments=assignment_count
        )
        if attempted_semantics.ok is not True:
            raise RuntimeError("selected program failed exhaustive vector semantics")
        final_resource_score = attempted_score
    except Exception as exc:
        degraded = True
        direct_fallback_used = True
        fallback_reason = f"{type(exc).__name__}: {exc}"
        final_resource_score = direct_resource_score
        semantic_verification = True
    if direct_resource_score == 0.0:
        if final_resource_score != 0.0:
            raise ZeroDivisionError("nonzero final program has a zero direct score")
        score_ratio_y = 1.0
    else:
        score_ratio_y = _finite_result(
            final_resource_score / direct_resource_score, "score ratio Y"
        )

    row: dict[str, object] = {
        "schema_version": MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA,
        "split": split,
        "case_id": case_id,
        "arm": arm,
        "value_weight": value_weight,
        "candidate_count": len(actions),
        "top_k": top_k,
        "scheduler_budget": scheduler_budget,
        "action_sha256": list(action_shas),
        "raw_utilities": list(raw),
        "model_logits": list(logits),
        "model_policy": list(model_policy),
        "model_value": model_value,
        "model_raw_pearson": model_raw_pearson,
        "model_raw_pearson_defined": model_raw_pearson_defined,
        "model_raw_spearman": model_raw_spearman,
        "model_raw_spearman_defined": model_raw_spearman_defined,
        "model_entropy": model_entropy,
        "model_normalized_entropy": model_normalized_entropy,
        "model_effective_support": model_effective_support,
        "raw_best_source_indices": list(raw_best),
        "raw_best_count": len(raw_best),
        "top_k_source_indices": list(top_indices),
        "raw_best_top_k_hit_count": top_raw_hits,
        "raw_best_top_k_recall": _finite_result(
            top_raw_hits / len(raw_best), "raw-best top-k recall"
        ),
        "selected_source_indices": list(selected),
        "selected_count": len(selected),
        "selected_empty": len(selected) == 0,
        "projection_dummy_selected": int(schedule.dummy_selected),
        "projection_objective": objective,
        "projection_uses_arm_neutral_raw_utilities": True,
        "direct_resource_score": direct_resource_score,
        "final_resource_score": final_resource_score,
        "score_ratio_y": score_ratio_y,
        "semantic_verification": semantic_verification,
        "degraded": degraded,
        "direct_fallback_used": direct_fallback_used,
        "fallback_reason": fallback_reason,
    }
    if set(row) != _MODEL_CASE_FIELDS:  # pragma: no cover - construction invariant
        raise RuntimeError("model-ranking diagnostic field contract changed")
    return row


def diagnose_replay_signal_case_v1(
    *,
    split: str,
    case_id: str,
    arm: str,
    teacher_role: str,
    value_weight: float,
    vector: VectorANF,
    actions: tuple[SharedAction, ...],
    raw_utilities: tuple[float, ...],
    teacher_policy: tuple[float, ...],
    teacher_value_target: float,
    policy_observation_weight: float | None = None,
    feasible_fraction: float | None = None,
    value_observation_weight: float | None = None,
    model: object,
    top_k: int,
    scheduler_budget: int,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> dict[str, object]:
    """Diagnose one replay teacher/model/action-pool tuple without mutation."""

    teacher_role = _native_string(teacher_role, "teacher_role")
    teacher = _probability_tuple(teacher_policy, "teacher_policy")
    teacher_value = _native_finite(teacher_value_target, "teacher_value_target")
    observation_values = (
        policy_observation_weight,
        feasible_fraction,
        value_observation_weight,
    )
    if any(value is None for value in observation_values) and not all(
        value is None for value in observation_values
    ):
        raise ValueError(
            "policy_observation_weight, feasible_fraction and "
            "value_observation_weight must be supplied together or all omitted"
        )
    if all(value is not None for value in observation_values):
        policy_observation_weight = _native_finite(
            policy_observation_weight, "policy_observation_weight", minimum=0.0
        )
        value_observation_weight = _native_finite(
            value_observation_weight, "value_observation_weight", minimum=0.0
        )
        feasible_fraction = _native_finite(
            feasible_fraction, "feasible_fraction", minimum=0.0
        )
        if policy_observation_weight == 0.0 or value_observation_weight == 0.0:
            raise ValueError("observation weights must be > 0")
        if feasible_fraction > 1.0:
            raise ValueError("feasible_fraction must be <= 1")
    model_row = diagnose_model_ranking_case_v1(
        split=split,
        case_id=case_id,
        arm=arm,
        value_weight=value_weight,
        vector=vector,
        actions=actions,
        raw_utilities=raw_utilities,
        model=model,
        top_k=top_k,
        scheduler_budget=scheduler_budget,
        weights=weights,
    )
    if len(teacher) != int(model_row["candidate_count"]):
        raise ValueError("teacher_policy must align with actions")
    raw = tuple(float(value) for value in model_row["raw_utilities"])
    logits = tuple(float(value) for value in model_row["model_logits"])
    _, model_log_policy = _softmax_and_log(logits)
    teacher_raw_pearson, teacher_raw_pearson_defined = _scaled_pearson(teacher, raw)
    teacher_raw_spearman, teacher_raw_spearman_defined = _spearman(teacher, raw)
    teacher_entropy, teacher_normalized_entropy, teacher_effective_support = _entropy(
        teacher
    )

    # Explicitly skip teacher zeros: 0*log(0) is defined as zero here.
    cross_entropy = -math.fsum(
        probability * model_log_policy[index]
        for index, probability in enumerate(teacher)
        if probability > 0.0
    )
    kl_divergence = math.fsum(
        probability * (math.log(probability) - model_log_policy[index])
        for index, probability in enumerate(teacher)
        if probability > 0.0
    )
    if -1.0e-12 < kl_divergence < 0.0:
        kl_divergence = 0.0
    cross_entropy = _finite_result(cross_entropy, "policy cross entropy")
    kl_divergence = _finite_result(kl_divergence, "policy KL divergence")
    if kl_divergence < 0.0:
        raise FloatingPointError("computed policy KL divergence is negative")

    raw_best = tuple(int(index) for index in model_row["raw_best_source_indices"])
    teacher_maximum = max(teacher)
    teacher_argmax = tuple(
        index for index, value in enumerate(teacher) if value == teacher_maximum
    )
    teacher_raw_hits = len(set(raw_best) & set(teacher_argmax))
    teacher_raw_positive_mass = _finite_result(
        math.fsum(
            probability
            for probability, utility in zip(teacher, raw)
            if utility > 0.0
        ),
        "teacher raw-positive mass",
    )
    teacher_raw_best_mass = _finite_result(
        math.fsum(teacher[index] for index in raw_best),
        "teacher raw-best mass",
    )
    model_value = float(model_row["model_value"])
    value_error = _finite_result(model_value - teacher_value, "value error")
    value_squared_error = _finite_result(value_error * value_error, "value squared error")

    row = dict(model_row)
    row.update(
        {
            "schema_version": REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA,
            "teacher_role": teacher_role,
            "teacher_policy": list(teacher),
            "teacher_value_target": teacher_value,
            "policy_observation_weight": policy_observation_weight,
            "feasible_fraction": feasible_fraction,
            "value_observation_weight": value_observation_weight,
            "teacher_raw_pearson": teacher_raw_pearson,
            "teacher_raw_pearson_defined": teacher_raw_pearson_defined,
            "teacher_raw_spearman": teacher_raw_spearman,
            "teacher_raw_spearman_defined": teacher_raw_spearman_defined,
            "teacher_entropy": teacher_entropy,
            "teacher_normalized_entropy": teacher_normalized_entropy,
            "teacher_effective_support": teacher_effective_support,
            "teacher_raw_positive_mass": teacher_raw_positive_mass,
            "teacher_raw_best_mass": teacher_raw_best_mass,
            "teacher_argmax_source_indices": list(teacher_argmax),
            "teacher_argmax_count": len(teacher_argmax),
            "teacher_argmax_raw_best_hit_count": teacher_raw_hits,
            "teacher_argmax_raw_best_hit": teacher_raw_hits > 0,
            "policy_cross_entropy": cross_entropy,
            "policy_kl_divergence": kl_divergence,
            "value_error": value_error,
            "value_absolute_error": _finite_result(
                abs(value_error), "value absolute error"
            ),
            "value_squared_error": value_squared_error,
            "effective_value_loss_contribution": (
                _finite_result(
                    float(model_row["value_weight"])
                    * float(value_observation_weight)
                    * value_squared_error,
                    "effective value loss contribution",
                )
                if value_observation_weight is not None
                else None
            ),
        }
    )
    if set(row) != _CASE_FIELDS:  # pragma: no cover - local construction invariant
        raise RuntimeError("diagnostic case field contract changed")
    return row


def _case_sort_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row["split"],
        row["arm"],
        row["value_weight"],
        row["case_id"],
        row["teacher_role"],
    )


def _validate_projection_consistency(
    row: dict[str, object], index: int, candidate_count: int
) -> None:
    def indices(name: str) -> list[int]:
        raw = row[name]
        if type(raw) is not list or any(type(value) is not int for value in raw):
            raise TypeError(f"rows[{index}].{name} must contain native integers")
        if len(set(raw)) != len(raw) or any(
            value < 0 or value >= candidate_count for value in raw
        ):
            raise ValueError(f"rows[{index}].{name} contains invalid indices")
        return raw

    raw_best = indices("raw_best_source_indices")
    top_k = indices("top_k_source_indices")
    selected = indices("selected_source_indices")
    if len(raw_best) != row["raw_best_count"]:
        raise ValueError(f"rows[{index}] raw_best_count is inconsistent")
    if len(top_k) != row["top_k"]:
        raise ValueError(f"rows[{index}] top_k_source_indices is inconsistent")
    if len(selected) != row["selected_count"] or not set(selected) <= set(top_k):
        raise ValueError(f"rows[{index}] selected_source_indices is inconsistent")
    if row["selected_empty"] is not (len(selected) == 0):
        raise ValueError(f"rows[{index}] selected_empty is inconsistent")
    expected_hits = len(set(raw_best) & set(top_k))
    if row["raw_best_top_k_hit_count"] != expected_hits:
        raise ValueError(f"rows[{index}] raw-best top-k hit count is inconsistent")
    expected_recall = expected_hits / len(raw_best)
    recall = float(row["raw_best_top_k_recall"])
    if not 0.0 <= recall <= 1.0 or not math.isclose(
        recall, expected_recall, rel_tol=0.0, abs_tol=1.0e-15
    ):
        raise ValueError(f"rows[{index}] raw-best top-k recall is inconsistent")
    expected_cardinality = min(int(row["scheduler_budget"]), len(top_k))
    if len(selected) + int(row["projection_dummy_selected"]) != expected_cardinality:
        raise ValueError(f"rows[{index}] projected fixed cardinality is inconsistent")


def diagnose_replay_training_corpus_v1(
    corpus: ReplayTrainingCorpusV1,
    models_by_arm: dict[str, object],
    *,
    value_weight: float,
    top_k: int = CANDIDATE_CAP,
    scheduler_budget: int = SCHEDULER_BUDGET,
) -> tuple[dict[str, object], ...]:
    """Diagnose any non-empty subset of the four corpus replay arms."""

    if type(corpus) is not ReplayTrainingCorpusV1:
        raise TypeError("corpus must be exact ReplayTrainingCorpusV1")
    if type(models_by_arm) is not dict:
        raise TypeError("models_by_arm must be an exact native dict")
    if not models_by_arm:
        raise ValueError("models_by_arm must be non-empty")
    if any(type(arm) is not str for arm in models_by_arm):
        raise TypeError("models_by_arm keys must be native strings")
    unknown = set(models_by_arm) - set(SOURCE_ARMS)
    if unknown:
        raise ValueError(f"models_by_arm contains unknown source arms: {sorted(unknown)}")
    selected_arms = tuple(arm for arm in SOURCE_ARMS if arm in models_by_arm)

    roster_by_group: dict[str, str] = {}
    for descriptor in corpus.descriptor.case_roster:
        group_id = _native_string(descriptor.group_id, "descriptor.group_id")
        case_id = _native_string(descriptor.case_id, "descriptor.case_id")
        if group_id in roster_by_group:
            raise ValueError("corpus descriptor contains duplicate group_id")
        roster_by_group[group_id] = case_id

    rows: list[dict[str, object]] = []
    seen_groups: set[str] = set()
    for group in corpus.groups:
        if type(group) is not ReplayTrainingGroupV1:
            raise TypeError("corpus groups must be exact ReplayTrainingGroupV1")
        group_id = _native_string(group.material.manifest.group_id, "manifest.group_id")
        if group_id in seen_groups:
            raise ValueError("corpus contains duplicate group_id")
        seen_groups.add(group_id)
        if group_id not in roster_by_group:
            raise ValueError("corpus group is absent from descriptor roster")
        targets = dict(group.targets_by_arm)
        if tuple(arm for arm, _ in group.targets_by_arm) != SOURCE_ARMS:
            raise ValueError("corpus replay target arm order changed")
        case = group.material.case
        for arm in selected_arms:
            target = targets[arm]
            if type(target) is not ReplayTargetsV2:
                raise TypeError("corpus replay targets must be exact ReplayTargetsV2")
            rows.append(
                diagnose_replay_signal_case_v1(
                    split=_native_string(
                        group.material.manifest.split_role, "manifest.split_role"
                    ),
                    case_id=roster_by_group[group_id],
                    arm=arm,
                    teacher_role="replay_training_target",
                    value_weight=value_weight,
                    vector=case.vector,
                    actions=case.actions,
                    raw_utilities=case.raw_utilities,
                    teacher_policy=target.policy_target,
                    teacher_value_target=target.value_target_log_ratio,
                    policy_observation_weight=target.policy_observation_weight,
                    feasible_fraction=target.feasible_fraction,
                    value_observation_weight=target.value_observation_weight,
                    model=models_by_arm[arm],
                    top_k=top_k,
                    scheduler_budget=scheduler_budget,
                    weights=case.utility_weights,
                )
            )
    if seen_groups != set(roster_by_group):
        raise ValueError("corpus descriptor roster contains groups without material")
    return tuple(sorted(rows, key=_case_sort_key))


def _validate_case_row(row: object, index: int) -> dict[str, object]:
    if type(row) is not dict:
        raise TypeError(f"rows[{index}] must be an exact native dict")
    if set(row) != _CASE_FIELDS:
        raise ValueError(f"rows[{index}] field contract changed")
    if row["schema_version"] != REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA:
        raise ValueError(f"rows[{index}] has an unsupported schema")
    for name in ("split", "case_id", "arm", "teacher_role"):
        _native_string(row[name], f"rows[{index}].{name}")
    _native_finite(row["value_weight"], f"rows[{index}].value_weight", minimum=0.0)
    candidate_count = _native_integer(
        row["candidate_count"], f"rows[{index}].candidate_count", minimum=1
    )
    for name in ("top_k", "scheduler_budget", "raw_best_count", "teacher_argmax_count"):
        _native_integer(row[name], f"rows[{index}].{name}", minimum=1)
    for name in (
        "teacher_argmax_raw_best_hit_count",
        "raw_best_top_k_hit_count",
        "selected_count",
        "projection_dummy_selected",
    ):
        _native_integer(row[name], f"rows[{index}].{name}")
    for name in (
        "teacher_raw_pearson",
        "teacher_raw_spearman",
        "model_raw_pearson",
        "model_raw_spearman",
        "teacher_entropy",
        "teacher_normalized_entropy",
        "teacher_effective_support",
        "teacher_raw_positive_mass",
        "teacher_raw_best_mass",
        "model_entropy",
        "model_normalized_entropy",
        "model_effective_support",
        "raw_best_top_k_recall",
        "policy_cross_entropy",
        "policy_kl_divergence",
        "value_error",
        "value_absolute_error",
        "value_squared_error",
        "teacher_value_target",
        "model_value",
        "projection_objective",
        "direct_resource_score",
        "final_resource_score",
        "score_ratio_y",
    ):
        _native_finite(row[name], f"rows[{index}].{name}")
    effective_value_loss = row["effective_value_loss_contribution"]
    if effective_value_loss is not None:
        _native_finite(
            effective_value_loss,
            f"rows[{index}].effective_value_loss_contribution",
            minimum=0.0,
        )
    observation_values = tuple(
        row[name]
        for name in (
            "policy_observation_weight",
            "feasible_fraction",
            "value_observation_weight",
        )
    )
    if any(value is None for value in observation_values) and not all(
        value is None for value in observation_values
    ):
        raise ValueError(f"rows[{index}] observation diagnostics are partially defined")
    validated_value_observation_weight: float | None = None
    if all(value is not None for value in observation_values):
        policy_weight = _native_finite(
            observation_values[0],
            f"rows[{index}].policy_observation_weight",
            minimum=0.0,
        )
        feasible = _native_finite(
            observation_values[1], f"rows[{index}].feasible_fraction", minimum=0.0
        )
        validated_value_observation_weight = _native_finite(
            observation_values[2],
            f"rows[{index}].value_observation_weight",
            minimum=0.0,
        )
        if (
            policy_weight == 0.0
            or validated_value_observation_weight == 0.0
            or feasible > 1.0
        ):
            raise ValueError(f"rows[{index}] observation diagnostics are out of range")
    for name in (
        "teacher_raw_pearson_defined",
        "teacher_raw_spearman_defined",
        "model_raw_pearson_defined",
        "model_raw_spearman_defined",
        "teacher_argmax_raw_best_hit",
        "selected_empty",
        "projection_uses_arm_neutral_raw_utilities",
        "semantic_verification",
        "degraded",
        "direct_fallback_used",
    ):
        if type(row[name]) is not bool:
            raise TypeError(f"rows[{index}].{name} must be a native bool")
    for name in (
        "action_sha256",
        "raw_utilities",
        "teacher_policy",
        "model_logits",
        "model_policy",
        "raw_best_source_indices",
        "teacher_argmax_source_indices",
        "top_k_source_indices",
        "selected_source_indices",
    ):
        if type(row[name]) is not list:
            raise TypeError(f"rows[{index}].{name} must be a native list")
    if any(
        len(row[name]) != candidate_count
        for name in (
            "action_sha256",
            "raw_utilities",
            "teacher_policy",
            "model_logits",
            "model_policy",
        )
    ):
        raise ValueError(f"rows[{index}] candidate-aligned fields changed length")
    _validate_projection_consistency(row, index, candidate_count)
    teacher_argmax = row["teacher_argmax_source_indices"]
    if len(teacher_argmax) != row["teacher_argmax_count"]:
        raise ValueError(f"rows[{index}] teacher_argmax_count is inconsistent")
    teacher_hits = len(set(teacher_argmax) & set(row["raw_best_source_indices"]))
    if (
        row["teacher_argmax_raw_best_hit_count"] != teacher_hits
        or row["teacher_argmax_raw_best_hit"] is not (teacher_hits > 0)
    ):
        raise ValueError(f"rows[{index}] teacher raw-best hit is inconsistent")
    for name in ("teacher_raw_positive_mass", "teacher_raw_best_mass"):
        if not 0.0 <= float(row[name]) <= 1.0:
            raise ValueError(f"rows[{index}].{name} must lie in [0, 1]")
    if validated_value_observation_weight is None:
        if effective_value_loss is not None:
            raise ValueError(
                f"rows[{index}] effective value loss requires observation weight"
            )
    else:
        expected_effective = (
            float(row["value_weight"])
            * validated_value_observation_weight
            * float(row["value_squared_error"])
        )
        if effective_value_loss is None or not math.isclose(
            float(effective_value_loss),
            expected_effective,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            raise ValueError(f"rows[{index}] effective value loss is inconsistent")
    if row["projection_uses_arm_neutral_raw_utilities"] is not True:
        raise ValueError(f"rows[{index}] projection is not arm neutral")
    if row["fallback_reason"] is not None:
        _native_string(row["fallback_reason"], f"rows[{index}].fallback_reason")
    return row


def _validate_model_case_row(row: object, index: int) -> dict[str, object]:
    if type(row) is not dict:
        raise TypeError(f"rows[{index}] must be an exact native dict")
    if set(row) != _MODEL_CASE_FIELDS:
        raise ValueError(f"rows[{index}] model-ranking field contract changed")
    if row["schema_version"] != MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA:
        raise ValueError(f"rows[{index}] has an unsupported model-ranking schema")
    for name in ("split", "case_id", "arm"):
        _native_string(row[name], f"rows[{index}].{name}")
    _native_finite(row["value_weight"], f"rows[{index}].value_weight", minimum=0.0)
    candidate_count = _native_integer(
        row["candidate_count"], f"rows[{index}].candidate_count", minimum=1
    )
    for name in ("top_k", "scheduler_budget", "raw_best_count"):
        _native_integer(row[name], f"rows[{index}].{name}", minimum=1)
    for name in (
        "raw_best_top_k_hit_count",
        "selected_count",
        "projection_dummy_selected",
    ):
        _native_integer(row[name], f"rows[{index}].{name}")
    for name in (
        "model_value",
        "model_raw_pearson",
        "model_raw_spearman",
        "model_entropy",
        "model_normalized_entropy",
        "model_effective_support",
        "raw_best_top_k_recall",
        "projection_objective",
        "direct_resource_score",
        "final_resource_score",
        "score_ratio_y",
    ):
        _native_finite(row[name], f"rows[{index}].{name}")
    for name in (
        "model_raw_pearson_defined",
        "model_raw_spearman_defined",
        "selected_empty",
        "projection_uses_arm_neutral_raw_utilities",
        "semantic_verification",
        "degraded",
        "direct_fallback_used",
    ):
        if type(row[name]) is not bool:
            raise TypeError(f"rows[{index}].{name} must be a native bool")
    for name in (
        "action_sha256",
        "raw_utilities",
        "model_logits",
        "model_policy",
        "raw_best_source_indices",
        "top_k_source_indices",
        "selected_source_indices",
    ):
        if type(row[name]) is not list:
            raise TypeError(f"rows[{index}].{name} must be a native list")
    if any(
        len(row[name]) != candidate_count
        for name in ("action_sha256", "raw_utilities", "model_logits", "model_policy")
    ):
        raise ValueError(f"rows[{index}] candidate-aligned fields changed length")
    _validate_projection_consistency(row, index, candidate_count)
    if row["projection_uses_arm_neutral_raw_utilities"] is not True:
        raise ValueError(f"rows[{index}] projection is not arm neutral")
    if row["fallback_reason"] is not None:
        _native_string(row["fallback_reason"], f"rows[{index}].fallback_reason")
    return row


def _mean(rows: Sequence[dict[str, object]], name: str) -> float:
    return _finite_result(
        math.fsum(float(row[name]) for row in rows) / len(rows), f"mean {name}"
    )


def _defined_mean(
    rows: Sequence[dict[str, object]], value_name: str, flag_name: str
) -> tuple[float, float]:
    defined = [row for row in rows if row[flag_name] is True]
    rate = _finite_result(len(defined) / len(rows), f"{flag_name} rate")
    mean = _mean(defined, value_name) if defined else 0.0
    return mean, rate


def _optional_mean(
    rows: Sequence[dict[str, object]], name: str
) -> tuple[float, float]:
    defined = [row for row in rows if row[name] is not None]
    rate = _finite_result(len(defined) / len(rows), f"{name} defined rate")
    mean = _mean(defined, name) if defined else 0.0
    return mean, rate


def aggregate_replay_signal_diagnostics_v1(
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Canonically aggregate case diagnostics by split, arm and value weight."""

    if type(rows) is not tuple:
        raise TypeError("rows must be an exact native tuple")
    if not rows:
        raise ValueError("rows must be non-empty")
    parsed = tuple(_validate_case_row(row, index) for index, row in enumerate(rows))
    identities = [
        (
            row["split"],
            row["case_id"],
            row["arm"],
            row["value_weight"],
            row["teacher_role"],
        )
        for row in parsed
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("rows contain a duplicate diagnostic identity")

    grouped: dict[tuple[str, str, float], list[dict[str, object]]] = {}
    for row in parsed:
        key = (str(row["split"]), str(row["arm"]), float(row["value_weight"]))
        grouped.setdefault(key, []).append(row)

    aggregates: list[dict[str, object]] = []
    for (split, arm, value_weight), members in sorted(grouped.items()):
        members.sort(key=lambda row: (row["case_id"], row["teacher_role"]))
        teacher_pearson, teacher_pearson_rate = _defined_mean(
            members, "teacher_raw_pearson", "teacher_raw_pearson_defined"
        )
        teacher_spearman, teacher_spearman_rate = _defined_mean(
            members, "teacher_raw_spearman", "teacher_raw_spearman_defined"
        )
        model_pearson, model_pearson_rate = _defined_mean(
            members, "model_raw_pearson", "model_raw_pearson_defined"
        )
        model_spearman, model_spearman_rate = _defined_mean(
            members, "model_raw_spearman", "model_raw_spearman_defined"
        )
        policy_observation_weight, policy_observation_weight_rate = _optional_mean(
            members, "policy_observation_weight"
        )
        feasible_fraction, feasible_fraction_rate = _optional_mean(
            members, "feasible_fraction"
        )
        value_observation_weight, value_observation_weight_rate = _optional_mean(
            members, "value_observation_weight"
        )
        total_raw_best = sum(int(row["raw_best_count"]) for row in members)
        total_top_hits = sum(int(row["raw_best_top_k_hit_count"]) for row in members)
        aggregates.append(
            {
                "split": split,
                "arm": arm,
                "value_weight": value_weight,
                "case_count": len(members),
                "case_ids": [str(row["case_id"]) for row in members],
                "teacher_roles": sorted({str(row["teacher_role"]) for row in members}),
                "top_k_values": sorted({int(row["top_k"]) for row in members}),
                "scheduler_budget_values": sorted(
                    {int(row["scheduler_budget"]) for row in members}
                ),
                "teacher_raw_pearson_mean_defined": teacher_pearson,
                "teacher_raw_pearson_defined_rate": teacher_pearson_rate,
                "teacher_raw_spearman_mean_defined": teacher_spearman,
                "teacher_raw_spearman_defined_rate": teacher_spearman_rate,
                "model_raw_pearson_mean_defined": model_pearson,
                "model_raw_pearson_defined_rate": model_pearson_rate,
                "model_raw_spearman_mean_defined": model_spearman,
                "model_raw_spearman_defined_rate": model_spearman_rate,
                "teacher_entropy_mean": _mean(members, "teacher_entropy"),
                "teacher_normalized_entropy_mean": _mean(
                    members, "teacher_normalized_entropy"
                ),
                "teacher_effective_support_mean": _mean(
                    members, "teacher_effective_support"
                ),
                "teacher_raw_positive_mass_mean": _mean(
                    members, "teacher_raw_positive_mass"
                ),
                "teacher_raw_best_mass_mean": _mean(
                    members, "teacher_raw_best_mass"
                ),
                "policy_observation_weight_mean_defined": policy_observation_weight,
                "policy_observation_weight_defined_rate": (
                    policy_observation_weight_rate
                ),
                "feasible_fraction_mean_defined": feasible_fraction,
                "feasible_fraction_defined_rate": feasible_fraction_rate,
                "value_observation_weight_mean_defined": value_observation_weight,
                "value_observation_weight_defined_rate": value_observation_weight_rate,
                "model_entropy_mean": _mean(members, "model_entropy"),
                "model_normalized_entropy_mean": _mean(
                    members, "model_normalized_entropy"
                ),
                "model_effective_support_mean": _mean(
                    members, "model_effective_support"
                ),
                "teacher_argmax_raw_best_hit_rate": _finite_result(
                    sum(bool(row["teacher_argmax_raw_best_hit"]) for row in members)
                    / len(members),
                    "teacher argmax raw-best hit rate",
                ),
                "policy_cross_entropy_mean": _mean(
                    members, "policy_cross_entropy"
                ),
                "policy_kl_divergence_mean": _mean(
                    members, "policy_kl_divergence"
                ),
                "raw_best_top_k_recall_macro_mean": _mean(
                    members, "raw_best_top_k_recall"
                ),
                "raw_best_top_k_recall_micro": _finite_result(
                    total_top_hits / total_raw_best, "raw-best top-k micro recall"
                ),
                "raw_best_top_k_perfect_rate": _finite_result(
                    sum(
                        math.isclose(
                            float(row["raw_best_top_k_recall"]),
                            1.0,
                            rel_tol=0.0,
                            abs_tol=1.0e-15,
                        )
                        for row in members
                    )
                    / len(members),
                    "raw-best top-k perfect rate",
                ),
                "selected_empty_rate": _finite_result(
                    sum(bool(row["selected_empty"]) for row in members)
                    / len(members),
                    "selected empty rate",
                ),
                "selected_count_mean": _mean(members, "selected_count"),
                "score_ratio_y_mean": _mean(members, "score_ratio_y"),
                "semantic_verification_rate": _finite_result(
                    sum(bool(row["semantic_verification"]) for row in members)
                    / len(members),
                    "semantic verification rate",
                ),
                "degraded_rate": _finite_result(
                    sum(bool(row["degraded"]) for row in members) / len(members),
                    "degraded rate",
                ),
                "direct_fallback_rate": _finite_result(
                    sum(bool(row["direct_fallback_used"]) for row in members)
                    / len(members),
                    "direct fallback rate",
                ),
                "value_absolute_error_mean": _mean(
                    members, "value_absolute_error"
                ),
                "value_squared_error_mean": _mean(members, "value_squared_error"),
                "effective_value_loss_contribution_mean_defined": _optional_mean(
                    members, "effective_value_loss_contribution"
                )[0],
                "effective_value_loss_contribution_defined_rate": _optional_mean(
                    members, "effective_value_loss_contribution"
                )[1],
            }
        )

    return {
        "schema_version": REPLAY_SIGNAL_DIAGNOSTIC_AGGREGATE_V1_SCHEMA,
        "group_by": ["split", "arm", "value_weight"],
        "case_row_count": len(parsed),
        "group_count": len(aggregates),
        "metric_contracts": {
            "top_k": TOP_K_RULE,
            "raw_best": RAW_BEST_RULE,
            "projection": PROJECTION_RULE,
            "correlations": CORRELATION_RULE,
            "raw_best_top_k_recall_denominator": (
                "all_actions_tied_at_the_exact_maximum_raw_utility"
            ),
            "policy_zero_probability_semantics": "zero_times_log_zero_is_zero",
        },
        "groups": aggregates,
    }


def aggregate_model_ranking_diagnostics_v1(
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Aggregate teacher-free expanded/OOD model-ranking diagnostics."""

    if type(rows) is not tuple:
        raise TypeError("rows must be an exact native tuple")
    if not rows:
        raise ValueError("rows must be non-empty")
    parsed = tuple(
        _validate_model_case_row(row, index) for index, row in enumerate(rows)
    )
    identities = [
        (row["split"], row["case_id"], row["arm"], row["value_weight"])
        for row in parsed
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("rows contain a duplicate model-ranking identity")

    grouped: dict[tuple[str, str, float], list[dict[str, object]]] = {}
    for row in parsed:
        key = (str(row["split"]), str(row["arm"]), float(row["value_weight"]))
        grouped.setdefault(key, []).append(row)

    aggregates: list[dict[str, object]] = []
    for (split, arm, value_weight), members in sorted(grouped.items()):
        members.sort(key=lambda row: row["case_id"])
        model_pearson, model_pearson_rate = _defined_mean(
            members, "model_raw_pearson", "model_raw_pearson_defined"
        )
        model_spearman, model_spearman_rate = _defined_mean(
            members, "model_raw_spearman", "model_raw_spearman_defined"
        )
        total_raw_best = sum(int(row["raw_best_count"]) for row in members)
        total_top_hits = sum(int(row["raw_best_top_k_hit_count"]) for row in members)
        aggregates.append(
            {
                "split": split,
                "arm": arm,
                "value_weight": value_weight,
                "case_count": len(members),
                "case_ids": [str(row["case_id"]) for row in members],
                "top_k_values": sorted({int(row["top_k"]) for row in members}),
                "scheduler_budget_values": sorted(
                    {int(row["scheduler_budget"]) for row in members}
                ),
                "model_raw_pearson_mean_defined": model_pearson,
                "model_raw_pearson_defined_rate": model_pearson_rate,
                "model_raw_spearman_mean_defined": model_spearman,
                "model_raw_spearman_defined_rate": model_spearman_rate,
                "model_entropy_mean": _mean(members, "model_entropy"),
                "model_normalized_entropy_mean": _mean(
                    members, "model_normalized_entropy"
                ),
                "model_effective_support_mean": _mean(
                    members, "model_effective_support"
                ),
                "raw_best_top_k_recall_macro_mean": _mean(
                    members, "raw_best_top_k_recall"
                ),
                "raw_best_top_k_recall_micro": _finite_result(
                    total_top_hits / total_raw_best, "raw-best top-k micro recall"
                ),
                "raw_best_top_k_perfect_rate": _finite_result(
                    sum(
                        math.isclose(
                            float(row["raw_best_top_k_recall"]),
                            1.0,
                            rel_tol=0.0,
                            abs_tol=1.0e-15,
                        )
                        for row in members
                    )
                    / len(members),
                    "raw-best top-k perfect rate",
                ),
                "selected_empty_rate": _finite_result(
                    sum(bool(row["selected_empty"]) for row in members)
                    / len(members),
                    "selected empty rate",
                ),
                "selected_count_mean": _mean(members, "selected_count"),
                "score_ratio_y_mean": _mean(members, "score_ratio_y"),
                "semantic_verification_rate": _finite_result(
                    sum(bool(row["semantic_verification"]) for row in members)
                    / len(members),
                    "semantic verification rate",
                ),
                "degraded_rate": _finite_result(
                    sum(bool(row["degraded"]) for row in members) / len(members),
                    "degraded rate",
                ),
                "direct_fallback_rate": _finite_result(
                    sum(bool(row["direct_fallback_used"]) for row in members)
                    / len(members),
                    "direct fallback rate",
                ),
            }
        )

    return {
        "schema_version": MODEL_RANKING_DIAGNOSTIC_AGGREGATE_V1_SCHEMA,
        "group_by": ["split", "arm", "value_weight"],
        "case_row_count": len(parsed),
        "group_count": len(aggregates),
        "teacher_metrics_present": False,
        "metric_contracts": {
            "top_k": TOP_K_RULE,
            "raw_best": RAW_BEST_RULE,
            "projection": PROJECTION_RULE,
            "correlations": CORRELATION_RULE,
            "raw_best_top_k_recall_denominator": (
                "all_actions_tied_at_the_exact_maximum_raw_utility"
            ),
        },
        "groups": aggregates,
    }


__all__ = [
    "CORRELATION_RULE",
    "MODEL_RANKING_DIAGNOSTIC_AGGREGATE_V1_SCHEMA",
    "MODEL_RANKING_DIAGNOSTIC_CASE_V1_SCHEMA",
    "PROJECTION_RULE",
    "RAW_BEST_RULE",
    "REPLAY_SIGNAL_DIAGNOSTIC_AGGREGATE_V1_SCHEMA",
    "REPLAY_SIGNAL_DIAGNOSTIC_CASE_V1_SCHEMA",
    "TOP_K_RULE",
    "aggregate_model_ranking_diagnostics_v1",
    "aggregate_replay_signal_diagnostics_v1",
    "diagnose_model_ranking_case_v1",
    "diagnose_replay_signal_case_v1",
    "diagnose_replay_training_corpus_v1",
]
