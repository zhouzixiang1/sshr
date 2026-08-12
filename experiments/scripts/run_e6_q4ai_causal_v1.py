#!/usr/bin/env python3
"""Run the small, single-researcher E6 Q4AI causal experiment.

This runner intentionally avoids a multi-stage release protocol.  It builds one
deterministic synthetic replay corpus, trains the four registered heads in
sequence from the same initialization, evaluates them on one fixed held-out
development set, and writes five ordinary files that can be checked by the
independent verifier.
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

from e6.final_measurement_replay_v2 import SOURCE_ARMS  # noqa: E402
from e6.frozen_foundation_v4_shared_head_v2 import (  # noqa: E402
    FORMAL_V4_CHECKPOINT_SHA256,
)
from e6.isolated_head_trainer_v2 import (  # noqa: E402
    ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
    fit_isolated_head_from_locked_replay_v2,
)
from e6.replay_training_corpus_v1 import (  # noqa: E402
    CorpusBuildSpecV1,
    build_replay_training_corpus_v1,
)
from e6.replay_training_evaluation_v1 import (  # noqa: E402
    evaluate_replay_training_heldout_v1,
)
from e6.shared_scheduler import SharedUtilityWeights  # noqa: E402
from src.contracts.codec import canonical_json_bytes, sha256_bytes  # noqa: E402


CONFIG_SCHEMA = "xa.e6-q4ai-causal-config.v1"
RESULTS_SCHEMA = "xa.e6-replay-training-results.v1-development"
RAW_SCHEMA = "xa.e6-replay-training-row.v1-development"
CLAIM_BOUNDARY = (
    "single-researcher deterministic development causal experiment; no "
    "equal-compute claim, hardware evidence, quantum advantage, cryptographic "
    "generalization, or formal performance evidence"
)
PAYLOAD_FILES = (
    "config.json",
    "heldout_evaluation.json",
    "raw.jsonl",
    "results.json",
)


def _strict_json(path: Path) -> dict[str, Any]:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs_hook,
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


def _tree_sha256(paths: Sequence[Path]) -> str:
    rows: list[dict[str, str]] = []
    seen: set[Path] = set()
    for root in paths:
        candidates = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in candidates:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            rows.append(
                {
                    "path": resolved.relative_to(PROJECT_ROOT.resolve()).as_posix(),
                    "sha256": _sha256_file(resolved),
                }
            )
    rows.sort(key=lambda row: row["path"])
    return sha256_bytes(canonical_json_bytes(rows))


def _git_source() -> dict[str, object]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        "commit_sha": head,
        "dirty": bool(status.strip()),
        "source_tree_sha256": _tree_sha256(
            (
                PROJECT_ROOT / "src",
                PROJECT_ROOT / "e6",
                PROJECT_ROOT / "scripts",
                PROJECT_ROOT / "tests",
            )
        ),
        "e6_tree_sha256": _tree_sha256((PROJECT_ROOT / "e6",)),
    }


def _training_config(base: dict[str, Any], profile: dict[str, Any], arm: str) -> bytes:
    head = base["head_training"]
    return canonical_json_bytes(
        {
            "schema_version": ISOLATED_HEAD_TRAINING_CONFIG_V2_SCHEMA,
            "source_arm": arm,
            "update_steps": profile["update_steps"],
            "batch_size": profile["batch_size"],
            "learning_rate": head["learning_rate"],
            "weight_decay": head["weight_decay"],
            "policy_loss_weight": head["policy_loss_weight"],
            "value_loss_weight": head["value_loss_weight"],
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


def _train_row(descriptor: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": RAW_SCHEMA,
        "record_type": "train_case",
        "case_id": descriptor["case_id"],
        "case_sha256": descriptor["case_sha256"],
        "input_count": descriptor["input_count"],
        "split_role": "train_replay",
        "observation_sha256_by_arm": dict(
            descriptor["arm_observation_sha256"]  # type: ignore[arg-type]
        ),
        "target_sha256_by_arm": dict(
            descriptor["target_sha256_by_arm"]  # type: ignore[arg-type]
        ),
        "case_descriptor": descriptor,
    }


def _eval_row(case: dict[str, object]) -> dict[str, object]:
    row = dict(case)
    row["schema_version"] = RAW_SCHEMA
    row["record_type"] = "eval_case"
    return row


def _write_bundle(
    output: Path,
    *,
    effective_config: dict[str, object],
    results: dict[str, object],
    raw_rows: Sequence[dict[str, object]],
    heldout: dict[str, object],
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_bytes(canonical_json_bytes(effective_config))
    (output / "results.json").write_bytes(canonical_json_bytes(results))
    (output / "raw.jsonl").write_bytes(
        b"".join(canonical_json_bytes(row) for row in raw_rows)
    )
    (output / "heldout_evaluation.json").write_bytes(canonical_json_bytes(heldout))
    checksum_lines = "".join(
        f"{_sha256_file(output / name)}  {name}\n" for name in sorted(PAYLOAD_FILES)
    )
    (output / "checksums.sha256").write_text(checksum_lines, encoding="ascii")


def run_experiment(
    *,
    config_path: Path,
    profile_name: str,
    output: Path,
    run_id: str,
) -> dict[str, object]:
    base = _strict_json(config_path)
    if base.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported E6 Q4AI config schema")
    if base.get("arms") != list(SOURCE_ARMS):
        raise ValueError("configured arm order does not match SOURCE_ARMS")
    if base.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("configured claim boundary changed")
    if (
        base.get("head_training", {}).get("foundation_checkpoint_sha256")
        != FORMAL_V4_CHECKPOINT_SHA256
    ):
        raise ValueError("configured foundation checkpoint identity changed")
    profiles = base.get("profiles")
    if type(profiles) is not dict or profile_name not in profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    profile = profiles[profile_name]
    if type(profile) is not dict:
        raise ValueError("selected profile must be a JSON object")
    train_case_count = profile.get("train_case_count")
    if (
        type(train_case_count) is not int
        or train_case_count < 2
        or train_case_count % 2
    ):
        raise ValueError("train_case_count must be a positive even integer")

    # Refuse an existing target before recording source state.  Because the
    # runner creates the directory only after all computation, its own five
    # output files can never make the recorded checkout appear dirty.
    if output.exists():
        raise FileExistsError(f"output path already exists: {output}")

    source = _git_source()
    effective_config: dict[str, object] = {
        "base_config": base,
        "profile_name": profile_name,
        "effective_profile": profile,
        "source": source,
        "base_config_file_sha256": _sha256_file(config_path),
    }

    corpus = build_replay_training_corpus_v1(
        CorpusBuildSpecV1(
            seed=base["seed"],
            cases_per_width=train_case_count // 2,
            observation_budget=profile["replay_observation_budget"],
            qaoa_optimizer_restarts=profile["qaoa_optimizer_restarts"],
            qaoa_optimizer_steps=profile["qaoa_optimizer_steps"],
        )
    )

    models: dict[str, object] = {}
    reports: dict[str, object] = {}
    for arm in SOURCE_ARMS:
        training_payload = _training_config(base, profile, arm)
        trained = fit_isolated_head_from_locked_replay_v2(
            corpus.materials,
            corpus.registry,
            corpus_lock_payload=corpus.corpus_lock_payload,
            expected_corpus_lock_payload_sha256=sha256_bytes(
                corpus.corpus_lock_payload
            ),
            config_payload=training_payload,
            expected_config_payload_sha256=sha256_bytes(training_payload),
        )
        models[arm] = trained.model
        reports[arm] = trained.report.to_dict()

    initial_heads = {
        report["initial_head_tensor_sha256"]  # type: ignore[index]
        for report in reports.values()
    }
    if len(initial_heads) != 1:
        raise RuntimeError("four arms did not start from the same initialized head")
    initial_head = next(iter(initial_heads))
    equal_report_fields = (
        "training_schedule_sha256",
        "sample_count",
        "group_ids",
        "input_counts",
        "update_steps",
        "batch_size",
        "sample_presentations",
        "foundation_checkpoint_sha256",
        "foundation_tensor_sha256",
    )
    for field in equal_report_fields:
        if len({canonical_json_bytes(report[field]) for report in reports.values()}) != 1:  # type: ignore[index]
            raise RuntimeError(f"four-arm training contract differs at {field}")
    for arm in SOURCE_ARMS:
        report = reports[arm]
        if report["source_arm"] != arm:  # type: ignore[index]
            raise RuntimeError(f"training report source arm mismatch: {arm}")
        if report["final_head_tensor_sha256"] == initial_head:  # type: ignore[index]
            raise RuntimeError(f"training did not change the {arm} head")

    heldout_config = base["heldout_evaluation"]
    configured_weights = base.get("resource_weights")
    if type(configured_weights) is not dict:
        raise ValueError("resource_weights must be a JSON object")
    utility_weights = SharedUtilityWeights(**configured_weights)
    heldout = evaluate_replay_training_heldout_v1(
        models,
        seed=profile["heldout_dataset_seed"],
        cases_per_width=profile["heldout_cases_per_input_count"],
        top_k=heldout_config["learned_top_k"],
        scheduler_budget=heldout_config["scheduler_budget"],
        bootstrap_resamples=profile["bootstrap_resamples"],
        signflip_resamples=profile["sign_flip_resamples"],
        bootstrap_seed=heldout_config["bootstrap_seed"],
        signflip_seed=heldout_config["sign_flip_seed"],
        utility_weights=utility_weights,
    )

    train_rows = [
        _train_row(descriptor.to_dict()) for descriptor in corpus.descriptor.case_roster
    ]
    eval_rows = [_eval_row(case) for case in heldout["case_rows"]]
    config_bytes = canonical_json_bytes(effective_config)
    results: dict[str, object] = {
        "schema_version": RESULTS_SCHEMA,
        "run_id": run_id,
        "source_commit": source["commit_sha"],
        "source_dirty": source["dirty"],
        "config_sha256": sha256_bytes(config_bytes),
        "corpus_sha256": corpus.descriptor.corpus_sha256,
        "arms": list(SOURCE_ARMS),
        "initial_head_sha": initial_head,
        "final_head_sha_by_arm": {
            arm: reports[arm]["final_head_tensor_sha256"]  # type: ignore[index]
            for arm in SOURCE_ARMS
        },
        "training_report_by_arm": reports,
        "timing": {
            "recorded": False,
            "reason": "excluded_from_bundle_for_deterministic_reproduction",
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "performance_evidence": False,
    }
    _write_bundle(
        output,
        effective_config=effective_config,
        results=results,
        raw_rows=(*train_rows, *eval_rows),
        heldout=heldout,
    )
    return {
        "run_id": run_id,
        "output": str(output.resolve()),
        "profile": profile_name,
        "train_case_count": len(train_rows),
        "heldout_case_count": len(eval_rows),
        "claim_supported": heldout["statistics"]["claim_gate"]["claim_supported"],
        "performance_evidence": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs/xa202609/e6_q4ai_causal_v1.json",
    )
    parser.add_argument("--profile", choices=("tiny", "full"), default="tiny")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    run_id = args.run_id or f"e6-q4ai-causal-v1-{args.profile}-s20260912"
    report = run_experiment(
        config_path=args.config.resolve(),
        profile_name=args.profile,
        output=args.output.resolve(),
        run_id=run_id,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
