#!/usr/bin/env python3
"""Run the deterministic single-researcher E6-D1 signal-chain diagnostic.

The run is intentionally ordinary: one 2x2 development diagnostic, one fresh
structured validation corpus viewed at matched-6 and expanded-cap-256 pools,
then one fresh n=4/5 OOD endpoint.  It writes five files and never overwrites an
existing directory.  There is no seal, preseal, release gate, or performance
claim.
"""

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
    ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
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


CONFIG_SCHEMA = "xa.e6-d1-signal-chain-config.v1"
RESULTS_SCHEMA = "xa.e6-d1-signal-chain-results.v1-development"
RAW_SCHEMA = "xa.e6-d1-signal-chain-row.v1-development"
DIAGNOSTICS_SCHEMA = "xa.e6-d1-signal-chain-diagnostics.v1-development"
CLAIM_BOUNDARY = (
    "single-researcher deterministic development diagnostic; no formal "
    "evaluation, equal-compute claim, hardware evidence, quantum advantage, "
    "cryptographic generalization, or performance evidence"
)
QAOA_ARM = "qaoa_final_measurement_replay"
CONTROL_ARM = "qaoa_permuted_label_control"
GREEDY_ARM = "classical_greedy_repeated_selection_replay"
PRIMARY_CELLS = (
    ("qaoa_vw1", QAOA_ARM, 1.0),
    ("qaoa_vw0", QAOA_ARM, 0.0),
    ("permuted_vw1", CONTROL_ARM, 1.0),
    ("permuted_vw0", CONTROL_ARM, 0.0),
)
REPLAY_TEACHER_SOURCE_ARM_BY_CELL = {
    **{cell: source_arm for cell, source_arm, _value_weight in PRIMARY_CELLS},
    "greedy_replay_vw1": GREEDY_ARM,
}
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_source() -> dict[str, object]:
    root = PROJECT_ROOT.parent
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
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
    base: dict[str, Any], profile: dict[str, Any], source_arm: str, value_weight: float
) -> bytes:
    head = base["head_training"]
    return canonical_json_bytes(
        {
            "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
            "source_arm": source_arm,
            "update_steps": profile["update_steps"],
            "batch_size": profile["batch_size"],
            "learning_rate": head["learning_rate"],
            "weight_decay": head["weight_decay"],
            "policy_loss_weight": head["policy_loss_weight"],
            "value_loss_weight": value_weight,
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
    """Keep the scientific receipt without release-protocol vocabulary."""

    fields = (
        "source_arm",
        "update_steps",
        "batch_size",
        "sample_count",
        "sample_presentations",
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
    result = {key: report[key] for key in fields}
    result["development_training_completed"] = True
    return result


def _build_corpus(base: dict[str, Any], profile: dict[str, Any], *, split: str):
    key = "train" if split == "train" else "structured_validation"
    return build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=base["splits"][key]["seed"],
            cases_per_width=profile[f"{key}_cases_per_input_count"],
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


def _expanded_pool(vector: VectorANF, weights: SharedUtilityWeights):
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
    )[:256]
    return tuple(item[0] for item in ranked), tuple(item[1] for item in ranked)


def _matched_rows(
    corpus: ReplayTrainingCorpusV1,
    models: dict[str, object],
    *,
    split: str,
    weights_by_cell: dict[str, float],
) -> list[dict[str, object]]:
    roster = {
        item.group_id: item.case_id for item in corpus.descriptor.case_roster
    }
    rows: list[dict[str, object]] = []
    for group in corpus.groups:
        case = group.material.case
        targets = dict(group.targets_by_arm)
        case_id = roster[group.material.manifest.group_id]
        for cell, model in models.items():
            if cell not in REPLAY_TEACHER_SOURCE_ARM_BY_CELL:
                continue
            source_arm = REPLAY_TEACHER_SOURCE_ARM_BY_CELL[cell]
            target = targets[source_arm]
            row = diagnose_replay_signal_case_v1(
                split=split,
                case_id=case_id,
                arm=cell,
                teacher_role="replay_target_matched_6_pool",
                value_weight=weights_by_cell[cell],
                vector=case.vector,
                actions=case.actions,
                raw_utilities=case.raw_utilities,
                teacher_policy=target.policy_target,
                teacher_value_target=target.value_target_log_ratio,
                policy_observation_weight=target.policy_observation_weight,
                feasible_fraction=target.feasible_fraction,
                value_observation_weight=target.value_observation_weight,
                model=model,
                top_k=len(case.actions),
                scheduler_budget=2,
                weights=case.utility_weights,
            )
            row["schema_version"] = RAW_SCHEMA
            row["record_type"] = "matched_teacher_diagnostic"
            rows.append(row)
    return rows


def _ranking_row(
    *,
    split: str,
    case_id: str,
    cell: str,
    value_weight: float,
    model: object,
    vector: VectorANF,
    actions: tuple,
    raw_utilities: tuple[float, ...],
    weights: SharedUtilityWeights,
) -> dict[str, object]:
    diagnostic = diagnose_model_ranking_case_v1(
        split=split,
        case_id=case_id,
        arm=cell,
        value_weight=value_weight,
        vector=vector,
        actions=actions,
        raw_utilities=raw_utilities,
        model=model,
        top_k=min(10, len(actions)),
        scheduler_budget=2,
        weights=weights,
    )
    return {
        **diagnostic,
        "schema_version": RAW_SCHEMA,
        "record_type": "model_ranking_endpoint",
    }


def _expanded_rows(
    corpus: ReplayTrainingCorpusV1,
    models: dict[str, object],
    *,
    split: str,
    weights_by_cell: dict[str, float],
) -> list[dict[str, object]]:
    roster = {item.group_id: item.case_id for item in corpus.descriptor.case_roster}
    rows: list[dict[str, object]] = []
    for group in corpus.groups:
        case = group.material.case
        actions, raw = _expanded_pool(case.vector, case.utility_weights)
        for cell, model in models.items():
            rows.append(
                _ranking_row(
                    split=split,
                    case_id=roster[group.material.manifest.group_id],
                    cell=cell,
                    value_weight=weights_by_cell[cell],
                    model=model,
                    vector=case.vector,
                    actions=actions,
                    raw_utilities=raw,
                    weights=case.utility_weights,
                )
            )
    return rows


def _ood_rows(
    base: dict[str, Any],
    profile: dict[str, Any],
    models: dict[str, object],
    weights_by_cell: dict[str, float],
    weights: SharedUtilityWeights,
) -> tuple[list[dict[str, object]], dict[str, set[str]]]:
    generated = generate_heldout_bijections_v1(
        seed=base["splits"]["ood_endpoint"]["seed"],
        cases_per_width=profile["ood_cases_per_input_count"],
    )
    rows: list[dict[str, object]] = []
    identities = {name: set() for name in ("vector_sha256", "orbit_cluster_sha256", "whole_vector_cluster_sha256")}
    for item in generated:
        vector = item["vector"]
        if type(vector) is not VectorANF:
            raise RuntimeError("OOD generator lost its VectorANF")
        actions, raw = _expanded_pool(vector, weights)
        identities["vector_sha256"].add(str(item["vector_sha256"]))
        identities["orbit_cluster_sha256"].add(str(item["orbit_cluster_sha256"]))
        identities["whole_vector_cluster_sha256"].add(str(item["whole_vector_cluster_sha256"]))
        for cell, model in models.items():
            rows.append(
                _ranking_row(
                    split="ood_endpoint_expanded_cap256",
                    case_id=str(item["case_id"]),
                    cell=cell,
                    value_weight=weights_by_cell[cell],
                    model=model,
                    vector=vector,
                    actions=actions,
                    raw_utilities=raw,
                    weights=weights,
                )
            )
    return rows, identities


def _aggregate_endpoint_rows(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    pure = tuple(
        {
            key: value
            for key, value in row.items()
            if key != "record_type"
        }
        | {"schema_version": "xa.e6-model-ranking-diagnostic-case.v1-development"}
        for row in rows
    )
    return aggregate_model_ranking_diagnostics_v1(pure)


def _factorial_contrasts(
    rows: Sequence[dict[str, object]], *, split: str, metrics: tuple[str, ...]
) -> dict[str, object]:
    design = {cell for cell, _source_arm, _value_weight in PRIMARY_CELLS}
    selected = [row for row in rows if row["split"] == split and row["arm"] in design]
    cells: dict[str, dict[str, float]] = {}
    for cell in sorted(design):
        members = [row for row in selected if row["arm"] == cell]
        if not members:
            raise RuntimeError(f"missing D1 contrast cell: {split}/{cell}")
        cells[cell] = {
            metric: sum(float(row[metric]) for row in members) / len(members)
            for metric in metrics
        }
    definitions = {
        "qaoa_minus_permuted_at_vw1": ("qaoa_vw1", "permuted_vw1"),
        "qaoa_minus_permuted_at_vw0": ("qaoa_vw0", "permuted_vw0"),
        "vw1_minus_vw0_with_qaoa": ("qaoa_vw1", "qaoa_vw0"),
        "vw1_minus_vw0_with_permuted": ("permuted_vw1", "permuted_vw0"),
    }
    contrasts = {
        name: {
            metric: cells[left][metric] - cells[right][metric]
            for metric in metrics
        }
        for name, (left, right) in definitions.items()
    }
    contrasts["label_by_value_weight_interaction"] = {
        metric: (
            cells["qaoa_vw1"][metric]
            - cells["qaoa_vw0"][metric]
            - cells["permuted_vw1"][metric]
            + cells["permuted_vw0"][metric]
        )
        for metric in metrics
    }
    return {
        "schema_version": "xa.e6-d1-factorial-contrasts.v1-development",
        "split": split,
        "cell_means": cells,
        "contrast_definition": "left_cell_mean_minus_right_cell_mean",
        "contrasts": contrasts,
        "diagnostic_only": True,
        "performance_gate": False,
    }


def _write_bundle(
    output: Path,
    *,
    config: dict[str, object],
    results: dict[str, object],
    rows: Sequence[dict[str, object]],
    diagnostics: dict[str, object],
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_bytes(canonical_json_bytes(config))
    (output / "results.json").write_bytes(canonical_json_bytes(results))
    (output / "diagnostics.json").write_bytes(canonical_json_bytes(diagnostics))
    (output / "raw.jsonl").write_bytes(b"".join(canonical_json_bytes(row) for row in rows))
    (output / "checksums.sha256").write_text(
        "".join(f"{_sha256_file(output / name)}  {name}\n" for name in sorted(PAYLOAD_FILES)),
        encoding="ascii",
    )


def run_experiment(
    *, config_path: Path, profile_name: str, output: Path, run_id: str
) -> dict[str, object]:
    base = _strict_json(config_path)
    if base.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported E6-D1 config schema")
    if base.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("E6-D1 claim boundary changed")
    if base.get("head_training", {}).get("foundation_checkpoint_sha256") != FORMAL_V4_CHECKPOINT_SHA256:
        raise ValueError("foundation checkpoint identity changed")
    profiles = base.get("profiles")
    if type(profiles) is not dict or profile_name not in profiles or type(profiles[profile_name]) is not dict:
        raise ValueError(f"unknown profile: {profile_name}")
    profile = profiles[profile_name]
    if output.exists():
        raise FileExistsError(f"output path already exists: {output}")
    source = _git_source()

    weights = SharedUtilityWeights(**base["resource_weights"])
    train = _build_corpus(base, profile, split="train")
    validation = _build_corpus(base, profile, split="structured_validation")
    for split_name, corpus in (("train", train), ("structured_validation", validation)):
        if any(group.material.case.utility_weights != weights for group in corpus.groups):
            raise RuntimeError(f"{split_name} corpus utility weights differ from D1 config")
    train_ids = _split_identities(train)
    validation_ids = _split_identities(validation)
    train_validation_overlap = _assert_disjoint(train_ids, validation_ids, label="train/structured_validation")

    models: dict[str, object] = {}
    reports: dict[str, object] = {}
    weights_by_cell: dict[str, float] = {}
    for cell, source_arm, value_weight in PRIMARY_CELLS:
        payload = _training_payload(base, profile, source_arm, value_weight)
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
        weights_by_cell[cell] = value_weight

    greedy_payload = _training_payload(base, profile, GREEDY_ARM, 1.0)
    greedy = fit_isolated_head_from_locked_replay_v2(
        train.materials,
        train.registry,
        corpus_lock_payload=train.corpus_lock_payload,
        expected_corpus_lock_payload_sha256=sha256_bytes(train.corpus_lock_payload),
        config_payload=greedy_payload,
        expected_config_payload_sha256=sha256_bytes(greedy_payload),
    )
    models["greedy_replay_vw1"] = greedy.model
    reports["greedy_replay_vw1"] = _ordinary_training_report(
        greedy.report.to_dict()
    )
    weights_by_cell["greedy_replay_vw1"] = 1.0
    frozen = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=base["head_training"]["head_hidden"],
        head_seed=base["head_training"]["head_seed"],
    )
    models["frozen_initial_head"] = frozen
    weights_by_cell["frozen_initial_head"] = 0.0

    matched_train = _matched_rows(train, models, split="train_matched_6", weights_by_cell=weights_by_cell)
    matched_validation = _matched_rows(validation, models, split="structured_validation_matched_6", weights_by_cell=weights_by_cell)
    expanded_validation = _expanded_rows(validation, models, split="structured_validation_expanded_cap256", weights_by_cell=weights_by_cell)
    structured_contrasts = {
        "matched_6": _factorial_contrasts(
            matched_validation,
            split="structured_validation_matched_6",
            metrics=(
                "teacher_raw_spearman",
                "model_raw_spearman",
                "policy_kl_divergence",
                "effective_value_loss_contribution",
            ),
        ),
        "expanded_cap256": _factorial_contrasts(
            expanded_validation,
            split="structured_validation_expanded_cap256",
            metrics=(
                "model_raw_spearman",
                "raw_best_top_k_recall",
                "selected_empty",
                "score_ratio_y",
            ),
        ),
    }
    # OOD generation/evaluation intentionally occurs only after both structured views.
    ood, ood_ids = _ood_rows(base, profile, models, weights_by_cell, weights)
    ood_train_overlap = _assert_disjoint(ood_ids, train_ids, label="ood/train")
    ood_validation_overlap = _assert_disjoint(ood_ids, validation_ids, label="ood/structured_validation")
    raw_rows = [*matched_train, *matched_validation, *expanded_validation, *ood]

    teacher_rows = tuple(
        {key: value for key, value in row.items() if key not in {"record_type"}}
        | {"schema_version": "xa.e6-replay-signal-diagnostic-case.v1-development"}
        for row in [*matched_train, *matched_validation]
    )
    diagnostics: dict[str, object] = {
        "schema_version": DIAGNOSTICS_SCHEMA,
        "teacher_aware": aggregate_replay_signal_diagnostics_v1(teacher_rows),
        "structured_expanded": _aggregate_endpoint_rows(expanded_validation),
        "ood_endpoint": _aggregate_endpoint_rows(ood),
        "structured_factorial_contrasts": structured_contrasts,
        "structured_diagnostics_computed_before_ood_evaluation": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    initial_shas = {report["initial_head_tensor_sha256"] for report in reports.values()}
    if initial_shas != {frozen.current_head_tensor_sha256()}:
        raise RuntimeError("D1 cells did not share the frozen initialized head")
    results: dict[str, object] = {
        "schema_version": RESULTS_SCHEMA,
        "run_id": run_id,
        "profile": profile_name,
        "source": source,
        "config_sha256": "",
        "design_cells": [cell for cell, _arm, _weight in PRIMARY_CELLS],
        "diagnostic_anchors": ["greedy_replay_vw1", "frozen_initial_head"],
        "replay_teacher_source_arm_by_cell": dict(REPLAY_TEACHER_SOURCE_ARM_BY_CELL),
        "training_report_by_cell": reports,
        "frozen_initial_head_sha256": frozen.current_head_tensor_sha256(),
        "split_case_counts": {
            "train": len(train.groups),
            "structured_validation": len(validation.groups),
            "ood_endpoint": len(ood) // len(models),
        },
        "split_overlap_counts": {
            "train_vs_structured_validation": train_validation_overlap,
            "ood_vs_train": ood_train_overlap,
            "ood_vs_structured_validation": ood_validation_overlap,
        },
        "structured_views": ["matched_6_replay_teacher", "expanded_cap256_no_teacher"],
        "ood_opened_after_structured_diagnostics": True,
        "raw_row_count": len(raw_rows),
        "timing": {"recorded": False, "reason": "excluded_for_deterministic_reproduction"},
        "claim_boundary": CLAIM_BOUNDARY,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    effective = {"base_config": base, "profile_name": profile_name, "effective_profile": profile, "source": source}
    results["config_sha256"] = sha256_bytes(canonical_json_bytes(effective))
    _write_bundle(output, config=effective, results=results, rows=raw_rows, diagnostics=diagnostics)
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
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/xa202609/e6_d1_signal_chain_v1.json")
    parser.add_argument("--profile", choices=("tiny", "full"), default="tiny")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    report = run_experiment(
        config_path=args.config.resolve(),
        profile_name=args.profile,
        output=args.output.resolve(),
        run_id=args.run_id or f"e6-d1-signal-chain-v1-{args.profile}-s20261001",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
