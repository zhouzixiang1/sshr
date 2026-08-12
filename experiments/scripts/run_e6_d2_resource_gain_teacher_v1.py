#!/usr/bin/env python3
"""Run the deterministic single-researcher E6-D2 teacher diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from e6.frozen_foundation_v4_shared_head_v2 import (  # noqa: E402
    FORMAL_V4_CHECKPOINT_SHA256,
    FrozenFoundationV4SharedPolicyValueV2,
)
from e6.frozen_case import canonical_action_sha256  # noqa: E402
from e6.isolated_head_trainer_v2 import (  # noqa: E402
    ISOLATED_HEAD_TRAINING_CONFIG_V3_SCHEMA,
    fit_isolated_head_from_locked_replay_v2,
)
from e6.replay_signal_diagnostics_v1 import (  # noqa: E402
    aggregate_model_ranking_diagnostics_v1,
    aggregate_replay_signal_diagnostics_v1,
    diagnose_model_ranking_case_v1,
    diagnose_replay_signal_case_v1,
)
from e6.replay_training_corpus_v1 import (  # noqa: E402
    CorpusBuildSpecV1,
    ReplayTrainingCorpusV1,
    build_replay_training_corpus_v1,
)
from e6.replay_training_evaluation_v1 import (  # noqa: E402
    generate_heldout_bijections_v1,
)
from e6.resource_gain_replay_teacher_v1 import (  # noqa: E402
    derive_resource_gain_replay_teacher_pair_from_group_v1,
)
from e6.shared_oracle import (  # noqa: E402
    VectorANF,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
)
from e6.shared_scheduler import (  # noqa: E402
    SharedUtilityWeights,
    shared_action_utility,
)
from src.contracts.codec import canonical_json_bytes, sha256_bytes  # noqa: E402


CONFIG_SCHEMA = "xa.e6-d2-resource-gain-teacher-config.v1"
RESULTS_SCHEMA = "xa.e6-d2-resource-gain-teacher-results.v1-development"
RAW_SCHEMA = "xa.e6-d2-resource-gain-teacher-row.v1-development"
DIAGNOSTICS_SCHEMA = "xa.e6-d2-resource-gain-teacher-diagnostics.v1-development"
CLAIM_BOUNDARY = (
    "single-researcher deterministic development diagnostic; no formal "
    "evaluation, equal-compute claim, hardware evidence, quantum advantage, "
    "cryptographic generalization, or performance evidence"
)
QAOA_ARM = "qaoa_final_measurement_replay"
CONTROL_ARM = "qaoa_permuted_label_control"
GREEDY_ARM = "classical_greedy_repeated_selection_replay"
GAIN_MODE = "qaoa_resource_gain_credit_v1"
LEGACY_MODE = "legacy_replay_v2"
TRAINED_CELLS = (
    ("gain_weighted_qaoa_vw0", QAOA_ARM, GAIN_MODE),
    ("gain_weighted_permuted_vw0", CONTROL_ARM, GAIN_MODE),
    ("legacy_unweighted_qaoa_vw0", QAOA_ARM, LEGACY_MODE),
    ("greedy_vw0", GREEDY_ARM, LEGACY_MODE),
)
PRIMARY_PAIR = ("gain_weighted_qaoa_vw0", "gain_weighted_permuted_vw0")
ALL_CELLS = tuple(cell for cell, _arm, _mode in TRAINED_CELLS) + (
    "frozen_initial_head",
)
PAYLOAD_FILES = ("config.json", "diagnostics.json", "raw.jsonl", "results.json")


def _strict_json(path: Path) -> dict[str, Any]:
    def hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=hook,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON value in {path}: {token}")
        ),
    )
    if type(value) is not dict:
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _exact_fields(value: object, expected: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{name} must be a native object")
    missing = expected - set(value)
    extra = set(value) - expected
    if missing or extra:
        raise ValueError(
            f"{name} fields changed: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return value


def _native_int(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a native integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _finite_number(
    value: object, name: str, *, minimum: float = 0.0, strict: bool = False
) -> float:
    if type(value) not in {int, float}:
        raise TypeError(f"{name} must be a native finite number")
    converted = float(value)
    if not converted == converted or converted in {float("inf"), float("-inf")}:
        raise ValueError(f"{name} must be finite")
    if (strict and converted <= minimum) or (not strict and converted < minimum):
        relation = ">" if strict else ">="
        raise ValueError(f"{name} must be {relation} {minimum}")
    return converted


def _validate_experiment_config(base: dict[str, Any], profile_name: str) -> dict[str, int]:
    endpoint = _exact_fields(
        base.get("endpoint"),
        {
            "candidate_universe_cap",
            "learned_top_k",
            "head_role",
            "scheduler",
            "scheduler_utility",
            "scheduler_budget",
            "outcome",
            "semantic_verification",
        },
        "endpoint",
    )
    cap = _native_int(endpoint["candidate_universe_cap"], "candidate_universe_cap", minimum=1)
    top_k = _native_int(endpoint["learned_top_k"], "learned_top_k", minimum=1)
    budget = _native_int(endpoint["scheduler_budget"], "scheduler_budget", minimum=1)
    if top_k > cap:
        raise ValueError("learned_top_k cannot exceed candidate_universe_cap")
    if top_k + min(top_k, budget) > 12:
        raise ValueError("learned_top_k plus effective scheduler budget must be <= 12")
    expected_endpoint = {
        "head_role": "rank_top_k_only",
        "scheduler": "exact",
        "scheduler_utility": "arm_neutral_raw_analytic_utility",
        "outcome": "total_abstract_score_over_direct_total_abstract_score_lower_is_better",
        "semantic_verification": "all_x_all_initial_y_inputs_preserved_ancillas_zero",
    }
    for key, expected in expected_endpoint.items():
        if endpoint[key] != expected:
            raise ValueError(f"endpoint {key} changed")

    raw_weights = _exact_fields(
        base.get("resource_weights"), {"t", "cnot", "depth", "gates", "ancilla"}, "resource_weights"
    )
    for name, value in raw_weights.items():
        _finite_number(value, f"resource_weights.{name}", strict=True)

    replay = _exact_fields(
        base.get("replay"),
        {
            "observation_budget",
            "qaoa_p",
            "qaoa_optimizer_restarts",
            "qaoa_optimizer_steps",
            "required_execution_class",
            "compute_budget_equal",
        },
        "replay",
    )
    _native_int(replay["observation_budget"], "replay.observation_budget", minimum=1)
    if _native_int(replay["qaoa_p"], "replay.qaoa_p", minimum=1) != 1:
        raise ValueError("replay.qaoa_p must remain 1")
    _native_int(replay["qaoa_optimizer_restarts"], "replay.qaoa_optimizer_restarts", minimum=1)
    _native_int(replay["qaoa_optimizer_steps"], "replay.qaoa_optimizer_steps", minimum=1)
    if replay["required_execution_class"] != "direct_unrepaired":
        raise ValueError("replay execution class changed")
    if type(replay["compute_budget_equal"]) is not bool or replay["compute_budget_equal"] is not False:
        raise ValueError("replay.compute_budget_equal must be false")

    head = _exact_fields(
        base.get("head_training"),
        {
            "foundation_checkpoint_sha256", "head_hidden", "head_seed", "learning_rate",
            "weight_decay", "policy_loss_weight", "value_loss_weight", "max_grad_norm",
            "sampler_seed", "device", "dtype", "cpu_threads", "optimizer", "scheduler",
            "early_stopping", "resume",
        },
        "head_training",
    )
    if head["foundation_checkpoint_sha256"] != FORMAL_V4_CHECKPOINT_SHA256:
        raise ValueError("foundation checkpoint identity changed")
    _native_int(head["head_hidden"], "head_training.head_hidden", minimum=1)
    _native_int(head["head_seed"], "head_training.head_seed")
    _native_int(head["sampler_seed"], "head_training.sampler_seed")
    _finite_number(head["learning_rate"], "head_training.learning_rate", strict=True)
    _finite_number(head["weight_decay"], "head_training.weight_decay")
    _finite_number(head["policy_loss_weight"], "head_training.policy_loss_weight", strict=True)
    if _finite_number(head["value_loss_weight"], "head_training.value_loss_weight") != 0.0:
        raise ValueError("E6-D2 requires value_loss_weight=0")
    _finite_number(head["max_grad_norm"], "head_training.max_grad_norm", strict=True)
    if (head["device"], head["dtype"], head["cpu_threads"], head["optimizer"], head["scheduler"]) != (
        "cpu", "float32", 1, "HeadOnlyIntegrityAdamW", "none"
    ):
        raise ValueError("head execution contract changed")
    if type(head["early_stopping"]) is not bool or head["early_stopping"] is not False:
        raise ValueError("head_training.early_stopping must be false")
    if type(head["resume"]) is not bool or head["resume"] is not False:
        raise ValueError("head_training.resume must be false")

    profiles = base.get("profiles")
    if type(profiles) is not dict or profile_name not in profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    profile = _exact_fields(
        profiles[profile_name],
        {
            "role", "train_cases_per_input_count", "structured_validation_cases_per_input_count",
            "ood_cases_per_input_count", "update_steps", "batch_size",
            "replay_observation_budget", "qaoa_optimizer_restarts", "qaoa_optimizer_steps",
        },
        f"profiles.{profile_name}",
    )
    for name in (
        "train_cases_per_input_count", "structured_validation_cases_per_input_count",
        "ood_cases_per_input_count", "update_steps", "batch_size", "replay_observation_budget",
        "qaoa_optimizer_restarts", "qaoa_optimizer_steps",
    ):
        _native_int(profile[name], f"profiles.{profile_name}.{name}", minimum=1)
    return {"candidate_cap": cap, "top_k": top_k, "scheduler_budget": budget}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_source() -> dict[str, object]:
    root = PROJECT_ROOT.parent
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"commit_sha": commit, "dirty": bool(status.strip())}


def _training_payload(
    base: dict[str, Any],
    profile: dict[str, Any],
    *,
    source_arm: str,
    target_mode: str,
) -> bytes:
    head = base["head_training"]
    return canonical_json_bytes(
        {
            "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V3_SCHEMA,
            "target_mode": target_mode,
            "source_arm": source_arm,
            "update_steps": profile["update_steps"],
            "batch_size": profile["batch_size"],
            "learning_rate": head["learning_rate"],
            "weight_decay": head["weight_decay"],
            "policy_loss_weight": head["policy_loss_weight"],
            "value_loss_weight": 0.0,
            "max_grad_norm": head["max_grad_norm"],
            "head_hidden": head["head_hidden"],
            "head_seed": head["head_seed"],
            "sampler_seed": head["sampler_seed"],
            "device": head["device"],
            "dtype": head["dtype"],
            "cpu_threads": head["cpu_threads"],
            "optimizer": head["optimizer"],
            "scheduler": head["scheduler"],
            "early_stopping": head["early_stopping"],
            "resume": head["resume"],
            "performance_evidence": False,
        }
    )


def _ordinary_training_report(report: dict[str, object]) -> dict[str, object]:
    fields = (
        "source_arm",
        "target_mode",
        "source_group_count",
        "zero_gain_skipped_group_count",
        "update_steps",
        "batch_size",
        "sample_count",
        "sample_presentations",
        "group_ids",
        "training_schedule_sha256",
        "input_counts",
        "initial_weighted_loss",
        "final_weighted_loss",
        "initial_head_tensor_sha256",
        "final_head_tensor_sha256",
        "foundation_checkpoint_sha256",
        "foundation_tensor_sha256",
        "optimizer",
        "formal_evaluation",
        "performance_evidence",
    )
    missing = set(fields) - set(report)
    if missing:
        raise RuntimeError(f"training report missing scientific fields: {sorted(missing)}")
    return {key: report[key] for key in fields} | {
        "development_training_completed": True
    }


def _build_corpus(
    base: dict[str, Any], profile: dict[str, Any], *, split: str
) -> ReplayTrainingCorpusV1:
    return build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=base["splits"][split]["seed"],
            cases_per_width=profile[f"{split}_cases_per_input_count"],
            observation_budget=profile["replay_observation_budget"],
            qaoa_optimizer_restarts=profile["qaoa_optimizer_restarts"],
            qaoa_optimizer_steps=profile["qaoa_optimizer_steps"],
        )
    )


def _split_identities(corpus: ReplayTrainingCorpusV1) -> dict[str, set[str]]:
    return {
        "vector_sha256": {item.vector_sha256 for item in corpus.descriptor.case_roster},
        "orbit_cluster_sha256": {
            item.orbit_cluster_sha256 for item in corpus.descriptor.case_roster
        },
        "whole_vector_cluster_sha256": {
            group.material.records[0].whole_vector_cluster_id for group in corpus.groups
        },
    }


def _assert_disjoint(
    left: dict[str, set[str]], right: dict[str, set[str]], *, label: str
) -> dict[str, int]:
    counts = {name: len(left[name] & right[name]) for name in sorted(left)}
    if any(counts.values()):
        raise RuntimeError(f"split identity overlap at {label}: {counts}")
    return counts


def _expanded_pool(
    vector: VectorANF, weights: SharedUtilityWeights, *, candidate_cap: int
):
    generated = enumerate_monomial_shared_actions(vector) + enumerate_semi_affine_shared_actions(
        vector, max_affine_weight=3
    )
    by_sha = {}
    for action in generated:
        digest = canonical_action_sha256(action)
        previous = by_sha.get(digest)
        if previous is not None and previous != action:
            raise RuntimeError("canonical action SHA collision")
        by_sha[digest] = action
    ranked = sorted(
        (
            (action, float(shared_action_utility(action, weights=weights)), digest)
            for digest, action in by_sha.items()
        ),
        key=lambda item: (-item[1], item[2]),
    )[:candidate_cap]
    return tuple(item[0] for item in ranked), tuple(item[1] for item in ranked)


def _teacher_material(
    corpus: ReplayTrainingCorpusV1, *, split: str
) -> tuple[dict[str, tuple[object, ...]], list[dict[str, object]]]:
    roster = {item.group_id: item.case_id for item in corpus.descriptor.case_roster}
    targets: dict[str, tuple[object, ...]] = {}
    audits: list[dict[str, object]] = []
    for group in corpus.groups:
        group_id = group.material.manifest.group_id
        pair = derive_resource_gain_replay_teacher_pair_from_group_v1(
            group, corpus.registry
        )
        base = dict(group.targets_by_arm)
        targets[group_id] = (
            pair.source_replay_target,
            pair.control_replay_target,
            base[QAOA_ARM],
            base[GREEDY_ARM],
        )
        audits.append(
            {
                "schema_version": RAW_SCHEMA,
                "record_type": "resource_gain_teacher_audit",
                "split": split,
                "case_id": roster[group_id],
                "group_id": group_id,
                "source": pair.source.to_dict(),
                "control": pair.control.to_dict(),
                "policy_audit": pair.policy_audit.to_dict(),
                "control_is_exact_source_permutation": (
                    pair.control_is_exact_source_permutation
                ),
                "permuted_target_changed": pair.permuted_target_changed,
            }
        )
    return targets, audits


def _matched_rows(
    corpus: ReplayTrainingCorpusV1,
    models: dict[str, object],
    *,
    split: str,
    teacher_targets: dict[str, tuple[object, ...]],
) -> list[dict[str, object]]:
    roster = {item.group_id: item.case_id for item in corpus.descriptor.case_roster}
    cells = TRAINED_CELLS
    rows: list[dict[str, object]] = []
    for group in corpus.groups:
        case = group.material.case
        group_id = group.material.manifest.group_id
        per_cell = dict(
            zip((cell for cell, _arm, _mode in cells), teacher_targets[group_id])
        )
        for cell, _arm, mode in cells:
            target = per_cell[cell]
            if target is None:
                continue
            row = diagnose_replay_signal_case_v1(
                split=split,
                case_id=roster[group_id],
                arm=cell,
                teacher_role=(
                    "resource_gain_weighted_matched_6"
                    if mode == GAIN_MODE
                    else "legacy_replay_matched_6"
                ),
                value_weight=0.0,
                vector=case.vector,
                actions=case.actions,
                raw_utilities=case.raw_utilities,
                teacher_policy=target.policy_target,
                teacher_value_target=target.value_target_log_ratio,
                policy_observation_weight=target.policy_observation_weight,
                feasible_fraction=target.feasible_fraction,
                value_observation_weight=target.value_observation_weight,
                model=models[cell],
                top_k=len(case.actions),
                scheduler_budget=2,
                weights=case.utility_weights,
            )
            row["schema_version"] = RAW_SCHEMA
            row["record_type"] = "matched_teacher_diagnostic"
            rows.append(row)
    return rows


def _ranking_row(
    *, split: str, case_id: str, cell: str, model: object, vector: VectorANF,
    actions: tuple, raw_utilities: tuple[float, ...], weights: SharedUtilityWeights,
    top_k: int, scheduler_budget: int,
) -> dict[str, object]:
    row = diagnose_model_ranking_case_v1(
        split=split,
        case_id=case_id,
        arm=cell,
        value_weight=0.0,
        vector=vector,
        actions=actions,
        raw_utilities=raw_utilities,
        model=model,
        top_k=min(top_k, len(actions)),
        scheduler_budget=scheduler_budget,
        weights=weights,
    )
    row["schema_version"] = RAW_SCHEMA
    row["record_type"] = "model_ranking_endpoint"
    return row


def _expanded_rows(
    corpus: ReplayTrainingCorpusV1, models: dict[str, object], *, split: str,
    candidate_cap: int, top_k: int, scheduler_budget: int,
) -> list[dict[str, object]]:
    roster = {item.group_id: item.case_id for item in corpus.descriptor.case_roster}
    rows: list[dict[str, object]] = []
    for group in corpus.groups:
        case = group.material.case
        actions, raw = _expanded_pool(
            case.vector, case.utility_weights, candidate_cap=candidate_cap
        )
        for cell in ALL_CELLS:
            rows.append(
                _ranking_row(
                    split=split,
                    case_id=roster[group.material.manifest.group_id],
                    cell=cell,
                    model=models[cell],
                    vector=case.vector,
                    actions=actions,
                    raw_utilities=raw,
                    weights=case.utility_weights,
                    top_k=top_k,
                    scheduler_budget=scheduler_budget,
                )
            )
    return rows


def _ood_rows(
    base: dict[str, Any], profile: dict[str, Any], models: dict[str, object],
    weights: SharedUtilityWeights, *, candidate_cap: int, top_k: int,
    scheduler_budget: int,
) -> tuple[list[dict[str, object]], dict[str, set[str]]]:
    generated = generate_heldout_bijections_v1(
        seed=base["splits"]["ood_endpoint"]["seed"],
        cases_per_width=profile["ood_cases_per_input_count"],
    )
    identities = {
        name: set()
        for name in (
            "vector_sha256",
            "orbit_cluster_sha256",
            "whole_vector_cluster_sha256",
        )
    }
    rows: list[dict[str, object]] = []
    for item in generated:
        vector = item["vector"]
        if type(vector) is not VectorANF:
            raise RuntimeError("OOD generator lost its VectorANF")
        actions, raw = _expanded_pool(vector, weights, candidate_cap=candidate_cap)
        for name in identities:
            identities[name].add(str(item[name]))
        for cell in ALL_CELLS:
            rows.append(
                _ranking_row(
                    split=f"ood_endpoint_expanded_cap{candidate_cap}",
                    case_id=str(item["case_id"]),
                    cell=cell,
                    model=models[cell],
                    vector=vector,
                    actions=actions,
                    raw_utilities=raw,
                    weights=weights,
                    top_k=top_k,
                    scheduler_budget=scheduler_budget,
                )
            )
    return rows, identities


def _aggregate_teacher(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    pure = tuple(
        {key: value for key, value in row.items() if key != "record_type"}
        | {"schema_version": "xa.e6-replay-signal-diagnostic-case.v1-development"}
        for row in rows
    )
    return aggregate_replay_signal_diagnostics_v1(pure)


def _aggregate_ranking(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    pure = tuple(
        {key: value for key, value in row.items() if key != "record_type"}
        | {"schema_version": "xa.e6-model-ranking-diagnostic-case.v1-development"}
        for row in rows
    )
    return aggregate_model_ranking_diagnostics_v1(pure)


def _primary_contrast(
    rows: Sequence[dict[str, object]], *, split: str, metrics: tuple[str, ...]
) -> dict[str, object]:
    members = {
        cell: [row for row in rows if row["split"] == split and row["arm"] == cell]
        for cell in PRIMARY_PAIR
    }
    ids = {cell: {str(row["case_id"]) for row in selected} for cell, selected in members.items()}
    if ids[PRIMARY_PAIR[0]] != ids[PRIMARY_PAIR[1]]:
        raise RuntimeError("primary pair does not use the same diagnostic cases")
    count = len(ids[PRIMARY_PAIR[0]])
    if count == 0:
        return {
            "available": False,
            "paired_case_count": 0,
            "reason": "no_eligible_resource_gain_teacher_cases",
        }
    means = {
        cell: {
            metric: sum(float(row[metric]) for row in selected) / len(selected)
            for metric in metrics
        }
        for cell, selected in members.items()
    }
    return {
        "available": True,
        "paired_case_count": count,
        "definition": "gain_weighted_qaoa_vw0_minus_gain_weighted_permuted_vw0",
        "cell_means": means,
        "difference": {
            metric: means[PRIMARY_PAIR[0]][metric] - means[PRIMARY_PAIR[1]][metric]
            for metric in metrics
        },
        "diagnostic_only": True,
        "performance_gate": False,
    }


def _teacher_audit_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    by_split: dict[str, dict[str, object]] = {}
    for split in sorted({str(row["split"]) for row in rows}):
        selected = [row for row in rows if row["split"] == split]
        eligible = [row for row in selected if row["source"]["eligible"] is True]
        by_split[split] = {
            "case_count": len(selected),
            "eligible_case_count": len(eligible),
            "ineligible_case_count": len(selected) - len(eligible),
            "permuted_target_changed_count": sum(
                row["permuted_target_changed"] is True for row in selected
            ),
            "mean_policy_observation_weight_over_eligible": (
                None
                if not eligible
                else sum(float(row["source"]["policy_observation_weight"]) for row in eligible)
                / len(eligible)
            ),
        }
    return by_split


def _write_bundle(
    output: Path, *, config: dict[str, object], results: dict[str, object],
    rows: Sequence[dict[str, object]], diagnostics: dict[str, object],
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_bytes(canonical_json_bytes(config))
    (output / "results.json").write_bytes(canonical_json_bytes(results))
    (output / "diagnostics.json").write_bytes(canonical_json_bytes(diagnostics))
    (output / "raw.jsonl").write_bytes(
        b"".join(canonical_json_bytes(row) for row in rows)
    )
    (output / "checksums.sha256").write_text(
        "".join(
            f"{_sha256_file(output / name)}  {name}\n"
            for name in sorted(PAYLOAD_FILES)
        ),
        encoding="ascii",
    )


def run_experiment(
    *, config_path: Path, profile_name: str, output: Path, run_id: str
) -> dict[str, object]:
    base = _strict_json(config_path)
    if base.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported E6-D2 config schema")
    if base.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("E6-D2 claim boundary changed")
    if base.get("design", {}).get("primary_pair") != list(PRIMARY_PAIR):
        raise ValueError("E6-D2 primary pair changed")
    endpoint = _validate_experiment_config(base, profile_name)
    profile = base["profiles"][profile_name]
    if output.exists():
        raise FileExistsError(f"output path already exists: {output}")
    source = _git_source()

    weights = SharedUtilityWeights(**base["resource_weights"])
    train = _build_corpus(base, profile, split="train")
    validation = _build_corpus(base, profile, split="structured_validation")
    for split_name, corpus in (("train", train), ("structured_validation", validation)):
        if any(group.material.case.utility_weights != weights for group in corpus.groups):
            raise RuntimeError(f"{split_name} corpus utility weights differ from D2 config")
    train_ids = _split_identities(train)
    validation_ids = _split_identities(validation)
    train_validation_overlap = _assert_disjoint(
        train_ids, validation_ids, label="train/structured_validation"
    )

    models: dict[str, object] = {}
    reports: dict[str, object] = {}
    for cell, source_arm, target_mode in TRAINED_CELLS:
        payload = _training_payload(
            base, profile, source_arm=source_arm, target_mode=target_mode
        )
        trained = fit_isolated_head_from_locked_replay_v2(
            train.materials,
            train.registry,
            corpus_lock_payload=train.corpus_lock_payload,
            expected_corpus_lock_payload_sha256=sha256_bytes(train.corpus_lock_payload),
            config_payload=payload,
            expected_config_payload_sha256=sha256_bytes(payload),
        )
        models[cell] = trained.model
        reports[cell] = _ordinary_training_report(trained.report.to_dict())

    frozen = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=base["head_training"]["head_hidden"],
        head_seed=base["head_training"]["head_seed"],
    )
    models["frozen_initial_head"] = frozen
    initial_shas = {report["initial_head_tensor_sha256"] for report in reports.values()}
    if initial_shas != {frozen.current_head_tensor_sha256()}:
        raise RuntimeError("D2 cells did not share the frozen initialized head")
    gain_reports = [reports[cell] for cell in PRIMARY_PAIR]
    for field in (
        "sample_count",
        "group_ids",
        "training_schedule_sha256",
        "sample_presentations",
        "initial_head_tensor_sha256",
    ):
        if gain_reports[0][field] != gain_reports[1][field]:
            raise RuntimeError(f"D2 primary training alignment changed at {field}")

    train_targets, train_audits = _teacher_material(train, split="train")
    validation_targets, validation_audits = _teacher_material(
        validation, split="structured_validation"
    )
    matched_train = _matched_rows(
        train,
        models,
        split="train_matched_6",
        teacher_targets=train_targets,
    )
    matched_validation = _matched_rows(
        validation,
        models,
        split="structured_validation_matched_6",
        teacher_targets=validation_targets,
    )
    expanded_split = f"structured_validation_expanded_cap{endpoint['candidate_cap']}"
    expanded_validation = _expanded_rows(
        validation,
        models,
        split=expanded_split,
        candidate_cap=endpoint["candidate_cap"],
        top_k=endpoint["top_k"],
        scheduler_budget=endpoint["scheduler_budget"],
    )
    structured_contrasts = {
        "matched_6": _primary_contrast(
            matched_validation,
            split="structured_validation_matched_6",
            metrics=(
                "teacher_raw_spearman",
                "model_raw_spearman",
                "policy_kl_divergence",
            ),
        ),
        f"expanded_cap{endpoint['candidate_cap']}": _primary_contrast(
            expanded_validation,
            split=expanded_split,
            metrics=(
                "model_raw_spearman",
                "raw_best_top_k_recall",
                "selected_empty",
                "score_ratio_y",
            ),
        ),
    }

    ood, ood_ids = _ood_rows(
        base,
        profile,
        models,
        weights,
        candidate_cap=endpoint["candidate_cap"],
        top_k=endpoint["top_k"],
        scheduler_budget=endpoint["scheduler_budget"],
    )
    ood_train_overlap = _assert_disjoint(ood_ids, train_ids, label="ood/train")
    ood_validation_overlap = _assert_disjoint(
        ood_ids, validation_ids, label="ood/structured_validation"
    )
    audit_rows = [*train_audits, *validation_audits]
    raw_rows = [
        *audit_rows,
        *matched_train,
        *matched_validation,
        *expanded_validation,
        *ood,
    ]

    diagnostics: dict[str, object] = {
        "schema_version": DIAGNOSTICS_SCHEMA,
        "resource_gain_teacher_audit": _teacher_audit_summary(audit_rows),
        "teacher_aware": _aggregate_teacher([*matched_train, *matched_validation]),
        "structured_expanded": _aggregate_ranking(expanded_validation),
        "ood_endpoint": _aggregate_ranking(ood),
        "structured_primary_pair_contrasts": structured_contrasts,
        "ood_primary_pair_contrast": _primary_contrast(
            ood,
            split=f"ood_endpoint_expanded_cap{endpoint['candidate_cap']}",
            metrics=(
                "model_raw_spearman",
                "raw_best_top_k_recall",
                "selected_empty",
                "score_ratio_y",
            ),
        ),
        "structured_diagnostics_computed_before_ood_evaluation": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    results: dict[str, object] = {
        "schema_version": RESULTS_SCHEMA,
        "run_id": run_id,
        "profile": profile_name,
        "source": source,
        "config_sha256": "",
        "primary_pair": list(PRIMARY_PAIR),
        "diagnostic_anchors": [
            "legacy_unweighted_qaoa_vw0",
            "greedy_vw0",
            "frozen_initial_head",
        ],
        "training_report_by_cell": reports,
        "frozen_initial_head_sha256": frozen.current_head_tensor_sha256(),
        "split_case_counts": {
            "train": len(train.groups),
            "structured_validation": len(validation.groups),
            "ood_endpoint": len(ood) // len(models),
        },
        "gain_teacher_eligibility": _teacher_audit_summary(audit_rows),
        "split_overlap_counts": {
            "train_vs_structured_validation": train_validation_overlap,
            "ood_vs_train": ood_train_overlap,
            "ood_vs_structured_validation": ood_validation_overlap,
        },
        "structured_views": [
            "matched_6_replay_teacher",
            f"expanded_cap{endpoint['candidate_cap']}_no_teacher",
        ],
        "ood_opened_after_structured_diagnostics": True,
        "raw_row_count": len(raw_rows),
        "timing": {"recorded": False, "reason": "excluded_for_deterministic_reproduction"},
        "claim_boundary": CLAIM_BOUNDARY,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    effective = {
        "base_config": base,
        "profile_name": profile_name,
        "effective_profile": profile,
        "source": source,
    }
    results["config_sha256"] = sha256_bytes(canonical_json_bytes(effective))
    _write_bundle(
        output,
        config=effective,
        results=results,
        rows=raw_rows,
        diagnostics=diagnostics,
    )
    return {
        "run_id": run_id,
        "output": str(output.resolve()),
        "profile": profile_name,
        "train_case_count": len(train.groups),
        "structured_validation_case_count": len(validation.groups),
        "ood_case_count": len(ood) // len(models),
        "raw_row_count": len(raw_rows),
        "performance_evidence": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs/xa202609/e6_d2_resource_gain_teacher_v1.json",
    )
    parser.add_argument("--profile", choices=("tiny", "full"), default="tiny")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    report = run_experiment(
        config_path=args.config.resolve(),
        profile_name=args.profile,
        output=args.output.resolve(),
        run_id=args.run_id or f"e6-d2-resource-gain-teacher-v1-{args.profile}-s20261011",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
