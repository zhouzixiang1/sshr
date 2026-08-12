#!/usr/bin/env python3
"""Adversarial tests for the small E6 replay-training result format."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from e6.isolated_head_trainer_v2 import fit_isolated_head_from_locked_replay_v2
from e6.replay_training_evaluation_v1 import evaluate_replay_training_heldout_v1
from e6.replay_training_corpus_v1 import (
    CorpusBuildSpecV1,
    build_replay_training_corpus_v1,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_e6_replay_training_bundle_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "e6_replay_bundle_verifier", VERIFIER_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def _base_config() -> dict[str, object]:
    config = json.loads(
        (PROJECT_ROOT / "configs/xa202609/e6_q4ai_causal_v1.json").read_text()
    )
    return config


def _effective_config() -> dict[str, object]:
    base = _base_config()
    return {
        "base_config": base,
        "profile_name": "tiny",
        "effective_profile": copy.deepcopy(base["profiles"]["tiny"]),
        "source": {
            "commit_sha": "1" * 40,
            "dirty": False,
            "source_tree_sha256": _sha("source-tree"),
            "e6_tree_sha256": _sha("e6-tree"),
        },
        "base_config_file_sha256": verifier._sha256_file(
            PROJECT_ROOT / "configs/xa202609/e6_q4ai_causal_v1.json"
        ),
    }


def _train_row(descriptor: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": verifier.RAW_SCHEMA,
        "record_type": "train_case",
        "case_id": descriptor["case_id"],
        "case_sha256": descriptor["case_sha256"],
        "input_count": descriptor["input_count"],
        "split_role": "train_replay",
        "observation_sha256_by_arm": dict(descriptor["arm_observation_sha256"]),
        "target_sha256_by_arm": dict(descriptor["target_sha256_by_arm"]),
        "case_descriptor": descriptor,
    }


_HELDOUT_CACHE: dict[str, object] | None = None
_CORPUS_CACHE = None
_TRAINED_CACHE = None


def _heldout() -> dict[str, object]:
    global _HELDOUT_CACHE
    if _HELDOUT_CACHE is None:
        models, _reports = _trained()
        config = _effective_config()
        base = config["base_config"]
        profile = config["effective_profile"]
        heldout_config = base["heldout_evaluation"]
        _HELDOUT_CACHE = evaluate_replay_training_heldout_v1(
            models,
            seed=profile["heldout_dataset_seed"],
            cases_per_width=profile["heldout_cases_per_input_count"],
            top_k=heldout_config["learned_top_k"],
            scheduler_budget=heldout_config["scheduler_budget"],
            bootstrap_resamples=profile["bootstrap_resamples"],
            signflip_resamples=profile["sign_flip_resamples"],
            bootstrap_seed=heldout_config["bootstrap_seed"],
            signflip_seed=heldout_config["sign_flip_seed"],
            utility_weights=verifier.SharedUtilityWeights(**base["resource_weights"]),
        )
    return copy.deepcopy(_HELDOUT_CACHE)


def _corpus():
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        _CORPUS_CACHE = build_replay_training_corpus_v1(
            CorpusBuildSpecV1(
                seed=20260912,
                cases_per_width=2,
                observation_budget=64,
                qaoa_optimizer_restarts=1,
                qaoa_optimizer_steps=2,
            )
        )
    return _CORPUS_CACHE


def _trained():
    global _TRAINED_CACHE
    if _TRAINED_CACHE is None:
        corpus = _corpus()
        config = _effective_config()
        models = {}
        reports = {}
        for arm in verifier.SOURCE_ARMS:
            payload = verifier._training_config_payload(
                config["base_config"], config["effective_profile"], arm
            )
            trained = fit_isolated_head_from_locked_replay_v2(
                corpus.materials,
                corpus.registry,
                corpus_lock_payload=corpus.corpus_lock_payload,
                expected_corpus_lock_payload_sha256=verifier._sha256_bytes(
                    corpus.corpus_lock_payload
                ),
                config_payload=payload,
                expected_config_payload_sha256=verifier._sha256_bytes(payload),
            )
            models[arm] = trained.model
            reports[arm] = trained.report.to_dict()
        _TRAINED_CACHE = models, reports
    models, reports = _TRAINED_CACHE
    return models, copy.deepcopy(reports)


def _resign(root: Path) -> None:
    payloads = sorted(verifier.PAYLOAD_FILES)
    (root / "checksums.sha256").write_text(
        "".join(f"{verifier._sha256_file(root / name)}  {name}\n" for name in payloads),
        encoding="ascii",
    )


def _write_bundle(root: Path) -> None:
    root.mkdir()
    config = _effective_config()
    corpus = _corpus()
    train_rows = [_train_row(item.to_dict()) for item in corpus.descriptor.case_roster]
    heldout = _heldout()
    eval_rows = []
    for case in heldout["case_rows"]:
        row = copy.deepcopy(case)
        row["schema_version"] = verifier.RAW_SCHEMA
        row["record_type"] = "eval_case"
        eval_rows.append(row)
    corpus_sha = corpus.descriptor.corpus_sha256
    _models, reports = _trained()
    initial = reports[verifier.SOURCE_ARMS[0]]["initial_head_tensor_sha256"]
    finals = {
        arm: reports[arm]["final_head_tensor_sha256"] for arm in verifier.SOURCE_ARMS
    }
    results = {
        "schema_version": verifier.RESULTS_SCHEMA,
        "run_id": "unit-e6-replay-training",
        "source_commit": config["source"]["commit_sha"],
        "source_dirty": config["source"]["dirty"],
        "config_sha256": verifier._sha256_bytes(_canonical(config)),
        "corpus_sha256": corpus_sha,
        "arms": list(verifier.SOURCE_ARMS),
        "initial_head_sha": initial,
        "final_head_sha_by_arm": finals,
        "training_report_by_arm": reports,
        "timing": {
            "recorded": False,
            "reason": "excluded_from_bundle_for_deterministic_reproduction",
        },
        "claim_boundary": verifier.CLAIM_BOUNDARY,
        "performance_evidence": False,
    }
    (root / "config.json").write_bytes(_canonical(config))
    (root / "results.json").write_bytes(_canonical(results))
    (root / "raw.jsonl").write_bytes(
        b"".join(_canonical(row) for row in [*train_rows, *eval_rows])
    )
    (root / "heldout_evaluation.json").write_bytes(_canonical(heldout))
    _resign(root)


def test_valid_small_bundle_passes(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is True, report
    assert report["train_case_count"] == 4
    assert report["heldout_case_count"] == 4
    assert all(report["checks"].values())


def test_rejects_extra_file_and_symlink(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    (root / "extra.txt").write_text("unexpected")
    assert verifier.verify_e6_replay_training_bundle_v1(root)["ok"] is False
    (root / "extra.txt").unlink()
    (root / "config-link.json").symlink_to(root / "config.json")
    assert verifier.verify_e6_replay_training_bundle_v1(root)["ok"] is False


def test_rejects_noncanonical_json_even_when_resigned(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    value = json.loads((root / "results.json").read_text())
    (root / "results.json").write_text(json.dumps(value, indent=2) + "\n")
    _resign(root)
    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["canonical_payloads"] is False


def test_resigned_training_budget_tamper_fails_semantics(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    results = json.loads((root / "results.json").read_text())
    arm = verifier.SOURCE_ARMS[2]
    results["training_report_by_arm"][arm]["update_steps"] += 1
    (root / "results.json").write_bytes(_canonical(results))
    _resign(root)
    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["four_arm_training_fairness"] is False


def test_resigned_arm_report_and_final_head_swap_fails_full_replay(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    results = json.loads((root / "results.json").read_text())
    first, second = verifier.SOURCE_ARMS[:2]
    first_report = results["training_report_by_arm"][first]
    second_report = results["training_report_by_arm"][second]
    results["training_report_by_arm"][first] = second_report
    results["training_report_by_arm"][second] = first_report
    results["training_report_by_arm"][first]["source_arm"] = first
    results["training_report_by_arm"][second]["source_arm"] = second
    (
        results["final_head_sha_by_arm"][first],
        results["final_head_sha_by_arm"][second],
    ) = (
        results["final_head_sha_by_arm"][second],
        results["final_head_sha_by_arm"][first],
    )
    # Re-sign every field available to the result author; deterministic replay
    # must still recover the original arm-specific heads and reject the swap.
    for arm in (first, second):
        results["training_report_by_arm"][arm]["config_payload_sha256"] = (
            verifier._sha256_bytes(
                verifier._training_config_payload(
                    _effective_config()["base_config"],
                    _effective_config()["effective_profile"],
                    arm,
                )
            )
        )
    (root / "results.json").write_bytes(_canonical(results))
    _resign(root)

    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["deterministic_training_to_scheduler_replay"] is False
    assert any("training report mismatch" in error for error in report["errors"])


def test_resigned_eval_outcome_tamper_fails_recomputation(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    heldout = json.loads((root / "heldout_evaluation.json").read_text())
    heldout["statistics"]["primary"]["effect_estimate"] = 999.0
    heldout["statistics"]["claim_gate"]["claim_supported"] = True
    (root / "heldout_evaluation.json").write_bytes(_canonical(heldout))
    _resign(root)
    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["heldout_semantic_recomputation"] is False


@pytest.mark.parametrize(
    "field,replacement",
    (
        ("dataset_seed", 20269999),
        ("bootstrap_seed", 20269998),
        ("signflip_seed", 20269997),
        ("cases_per_width", 3),
        ("bootstrap_resamples", 1001),
        ("signflip_resamples_requested", 4097),
    ),
)
def test_resigned_heldout_protocol_config_drift_fails(
    tmp_path: Path, field: str, replacement: int
) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    heldout = json.loads((root / "heldout_evaluation.json").read_text())
    heldout["protocol"][field] = replacement
    unsigned = dict(heldout)
    unsigned.pop("evaluation_sha256")
    heldout["evaluation_sha256"] = verifier._sha256_bytes(_canonical(unsigned))
    (root / "heldout_evaluation.json").write_bytes(_canonical(heldout))
    _resign(root)

    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["heldout_semantic_recomputation"] is False
    assert any("protocol/config mismatch" in error for error in report["errors"])


@pytest.mark.parametrize(
    "field,replacement",
    (
        ("heldout_dataset_seed", 20269996),
        ("heldout_cases_per_input_count", 3),
    ),
)
def test_resigned_effective_profile_drift_fails(
    tmp_path: Path, field: str, replacement: int
) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    config = json.loads((root / "config.json").read_text())
    config["effective_profile"][field] = replacement
    # Also change the embedded profile and all outer bindings.  The verifier
    # still compares it to the versioned base config and rejects the rewrite.
    config["base_config"]["profiles"]["tiny"][field] = replacement
    results = json.loads((root / "results.json").read_text())
    results["config_sha256"] = verifier._sha256_bytes(_canonical(config))
    (root / "config.json").write_bytes(_canonical(config))
    (root / "results.json").write_bytes(_canonical(results))
    _resign(root)

    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["config_contract"] is False


def test_resigned_program_resource_forgery_fails_independent_recompute(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    rows = [json.loads(line) for line in (root / "raw.jsonl").read_text().splitlines()]
    eval_row = next(row for row in rows if row["record_type"] == "eval_case")
    eval_row["direct_resource_score"] += 1.0
    eval_row["direct_program_resource_summary"]["total_abstract_score"] += 1.0

    heldout = json.loads((root / "heldout_evaluation.json").read_text())
    heldout_case = heldout["case_rows"][0]
    heldout_case["direct_resource_score"] = eval_row["direct_resource_score"]
    heldout_case["direct_program_resource_summary"] = eval_row[
        "direct_program_resource_summary"
    ]
    unsigned = dict(heldout)
    unsigned.pop("evaluation_sha256")
    heldout["evaluation_sha256"] = verifier._sha256_bytes(_canonical(unsigned))
    (root / "raw.jsonl").write_bytes(b"".join(_canonical(row) for row in rows))
    (root / "heldout_evaluation.json").write_bytes(_canonical(heldout))
    _resign(root)

    report = verifier.verify_e6_replay_training_bundle_v1(root)
    assert report["ok"] is False
    assert report["checks"]["files_and_checksums"] is True
    assert report["checks"]["heldout_semantic_recomputation"] is False
    assert any("direct resources" in error for error in report["errors"])


@pytest.mark.parametrize("flag", [True, "false", 0])
def test_performance_claim_cannot_be_enabled_or_type_confused(
    tmp_path: Path, flag: object
) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    results = json.loads((root / "results.json").read_text())
    results["performance_evidence"] = flag
    (root / "results.json").write_bytes(_canonical(results))
    _resign(root)
    assert verifier.verify_e6_replay_training_bundle_v1(root)["ok"] is False


def test_real_runner_tiny_bundle_passes_independent_verifier(tmp_path: Path) -> None:
    output = tmp_path / "runner-tiny"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_e6_q4ai_causal_v1.py"),
            "--profile",
            "tiny",
            "--output",
            str(output),
            "--run-id",
            "pytest-e6-q4ai-causal-tiny",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    runner_report = json.loads(completed.stdout)
    report = verifier.verify_e6_replay_training_bundle_v1(output)

    assert set(path.name for path in output.iterdir()) == verifier.EXPECTED_FILES
    assert runner_report["train_case_count"] == 4
    assert runner_report["heldout_case_count"] == 4
    assert runner_report["performance_evidence"] is False
    assert report["ok"] is True, report
    assert all(report["checks"].values())
    assert report["claim_supported"] is False
    assert report["performance_evidence"] is False
