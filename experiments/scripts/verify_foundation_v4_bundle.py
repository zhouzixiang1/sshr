#!/usr/bin/env python3
"""Independently verify a provenance-closed foundation v4 training bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

from src.anf_utils import anf_monomials
from src.contracts.artifacts import verify_bundle
from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file
from src.foundation.adapter import FoundationScorer
from src.sshr_lib.bool_func import BooleanFunction


CONFIG_SCHEMA = "xa.foundation-training-config.v4"
DATASET_SCHEMA = "xa.foundation-dataset-manifest.v4"
SOURCE_SCHEMA = "xa.foundation-source-manifest.v4"
SUMMARY_SCHEMA = "xa.foundation-training-summary.v4"
MODEL_CARD_SCHEMA = "xa.foundation-model-card.v4"
GENERATOR_ID = "xa.synthetic-uniform-shake256.v1"
EXPECTED_PARAMETER_COUNT = 60_450
EXPECTED_CRYPTO_TRUTH_TABLE_SHA256 = {
    "1e9824b17f9c4881346ee92a37d0ff4efc5d44cadf9c1e558f78ae190d662a05",
    "20b7cdfce4e67e25cb3b5dc4de26118f9b048c02981fa89ad1ceb54bd5274dd5",
    "25bff3db1032e49ddfc2d9bc9d5d48c985b1779930865e47f3780ff950984994",
    "2629f646e4e48c89d27a2fa15d806db1bb59721ec004c19415ae59ac2e72b48f",
    "2f5f6885b68f1f6fafed2be6ab614346c48a8528b51f7b4bdf4a0c1b609df97d",
    "3def4ec7c4026dc026162cdf2279a16a8e9e9f5efdde0521ebbfd91f3d5fec83",
    "3e1685e8e7f2b9529edafc5fd6d96e1174d858091a180d379cd89147ec286256",
    "4e970e8b7f2fb52a79c55db9c9dfaa44658eb64fd37e5ed9d3440a0905803e71",
    "651dfc9a16350c391f9b9f1e02afd433f951246a6fce4691301e3c463266bf71",
    "793b6367e6dd9217673ed5a6aa0bda6faa78da85239f47061ffb470e41c6151f",
    "80713771a1b2e8920d65ad892d27c8e2e8aba5874d587d4b24cf6cf074784ce7",
    "8a20f3428448f5e2bd8da3e9559cb7a3ae091759f4516e80cc65b8f616d6112d",
    "8bb9df77d8e16f65c91cc9fce1b1368b9f23332f6eb41419cc7fbd0ce39e2f4c",
    "8e63f8c394a1ee38340d3be6e9a33b7b8c86d752498720dc80c223b02562e959",
    "ac7c564edb9b2693a5ecf17f055281babf6b97433394169f5448d5af6fc950c2",
    "b3311960f4cf52c6db4d5cbb9cf0d47915e3666175b91f3eb4e08bad9932865a",
    "cac32e76240366ea1129102f26003cec2121742a1742f912da081106857743be",
    "e511dae0b4fd7953dd2e564003d3ef3b86f560ece76e073391bc525e9a45a97d",
    "f1993d2d5719218ea7fe15a97b9c7f977c03863e923def799fc948f669bc613f",
}
REQUIRED_ROLES = (
    "config",
    "source",
    "dataset",
    "command",
    "training_log",
    "checkpoint",
    "summary",
    "model_card",
    "resource_estimate",
    "self_checks",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def _tree_record(relative_root: str) -> dict[str, Any]:
    root = PROJECT_ROOT / relative_root
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        records.append(
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
        )
    return {
        "path": relative_root,
        "sha256": sha256_bytes(canonical_json_bytes(records)),
        "file_count": len(records),
    }


def _truth_bytes(num_vars: int, seed_material: bytes) -> tuple[bytes, int]:
    bit_count = 1 << num_vars
    byte_count = (bit_count + 7) // 8
    payload = bytearray(hashlib.shake_256(seed_material).digest(byte_count))
    excess = byte_count * 8 - bit_count
    if excess:
        payload[-1] &= (1 << (8 - excess)) - 1
    raw = bytes(payload)
    return raw, int.from_bytes(raw, "little")


def _regenerate_record(record: dict[str, Any], allowed_num_vars: list[int]) -> dict[str, Any]:
    seed = int(record["generator_seed"])
    split = str(record["split"])
    iteration = record["iteration"]
    draw_index = int(record["draw_index"])
    rotation_material = f"{GENERATOR_ID}|seed={seed}|split={split}|rotation".encode()
    rotation = int.from_bytes(hashlib.sha256(rotation_material).digest()[:8], "little")
    num_vars = allowed_num_vars[(rotation + draw_index) % len(allowed_num_vars)]
    nonce = int(record["generator_nonce"])
    label = (
        f"{GENERATOR_ID}|seed={seed}|split={split}|iteration={iteration}|"
        f"draw={draw_index}|n={num_vars}|nonce={nonce}"
    )
    raw, truth_table = _truth_bytes(num_vars, label.encode())
    terms = sorted(anf_monomials(BooleanFunction(num_vars, truth_table)))
    suffix = f"iter{int(iteration):03d}" if iteration is not None else "fixed"
    return {
        "function_id": f"synthetic-uniform/{split}/{suffix}/draw{draw_index:04d}/n{num_vars}",
        "source_kind": "synthetic_uniform_hashstream",
        "split": split,
        "iteration": iteration,
        "draw_index": draw_index,
        "generator_seed": seed,
        "generator_nonce": nonce,
        "num_vars": num_vars,
        "truth_table_sha256": hashlib.sha256(raw).hexdigest(),
        "truth_table_bytes": len(raw),
        "anf_sha256": sha256_bytes(canonical_json_bytes(terms)),
        "anf_terms": len(terms),
    }


def _check(condition: bool, name: str, checks: dict[str, bool], errors: list[str]) -> None:
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"check failed: {name}")


def verify_foundation_v4_bundle(
    run_dir: str | Path, *, require_current_source: bool = False
) -> dict[str, Any]:
    root = Path(run_dir)
    checks: dict[str, bool] = {}
    errors: list[str] = []
    generic = verify_bundle(root, required_roles=REQUIRED_ROLES)
    _check(generic.ok, "artifact_bundle", checks, errors)
    if not generic.ok:
        errors.extend(f"artifact: {error}" for error in generic.errors)
        return {"ok": False, "checks": checks, "errors": errors}

    try:
        config = _read_json(root / "config_snapshot.json")
        source = _read_json(root / "source_manifest.json")
        dataset = _read_json(root / "dataset_manifest.json")
        command = _read_json(root / "command.json")
        summary = _read_json(root / "training_summary.json")
        model_card = _read_json(root / "model_card.json")
        estimate = _read_json(root / "resource_estimate.json")
        self_checks = _read_json(root / "self_checks.json")
        log = [
            json.loads(line)
            for line in (root / "training_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot parse semantic artifacts: {exc}")
        return {"ok": False, "checks": checks, "errors": errors}

    _check(config.get("schema_version") == CONFIG_SCHEMA, "config_schema", checks, errors)
    _check(source.get("schema_version") == SOURCE_SCHEMA, "source_schema", checks, errors)
    _check(dataset.get("schema_version") == DATASET_SCHEMA, "dataset_schema", checks, errors)
    _check(summary.get("schema_version") == SUMMARY_SCHEMA, "summary_schema", checks, errors)
    _check(model_card.get("schema_version") == MODEL_CARD_SCHEMA, "model_card_schema", checks, errors)
    profile_name = config.get("selected_profile")
    profile = config.get("profiles", {}).get(profile_name, {})
    _check(isinstance(profile, dict) and bool(profile), "selected_profile", checks, errors)

    config_sha = sha256_file(root / "config_snapshot.json")
    source_sha = sha256_file(root / "source_manifest.json")
    dataset_file_sha = sha256_file(root / "dataset_manifest.json")
    command_sha = sha256_file(root / "command.json")
    log_sha = sha256_file(root / "training_log.jsonl")
    estimate_sha = sha256_file(root / "resource_estimate.json")
    links = summary.get("hash_links", {})
    _check(links.get("config_sha256") == config_sha, "config_hash_link", checks, errors)
    _check(
        links.get("source_manifest_sha256") == source_sha,
        "source_hash_link",
        checks,
        errors,
    )
    _check(
        links.get("dataset_manifest_sha256") == dataset_file_sha,
        "dataset_file_hash_link",
        checks,
        errors,
    )
    _check(links.get("command_sha256") == command_sha, "command_hash_link", checks, errors)
    _check(links.get("training_log_sha256") == log_sha, "log_hash_link", checks, errors)
    _check(
        links.get("resource_estimate_sha256") == estimate_sha,
        "estimate_hash_link",
        checks,
        errors,
    )

    source_records = source.get("files", [])
    contract_records = config.get("source_contract", {}).get("files", [])
    source_trees = source.get("trees", [])
    contract_trees = config.get("source_contract", {}).get("trees", [])
    _check(
        [(item.get("path"), item.get("sha256")) for item in source_records]
        == [(item.get("path"), item.get("sha256")) for item in contract_records],
        "source_contract_embedded",
        checks,
        errors,
    )
    source_sizes_valid = all(
        isinstance(item.get("size_bytes"), int) and item["size_bytes"] > 0
        for item in source_records
    ) and all(
        isinstance(tree.get("files"), list)
        and tree.get("file_count") == len(tree["files"])
        and all(
            isinstance(item.get("size_bytes"), int) and item["size_bytes"] > 0
            for item in tree["files"]
        )
        for tree in source_trees
    )
    _check(source_sizes_valid, "source_sizes", checks, errors)
    tree_embedded_ok = True
    if len(source_trees) != len(contract_trees):
        tree_embedded_ok = False
    for source_tree, contract_tree in zip(source_trees, contract_trees):
        identity_records = [
            {"path": item.get("path"), "sha256": item.get("sha256")}
            for item in source_tree.get("files", [])
        ]
        calculated = sha256_bytes(canonical_json_bytes(identity_records))
        if (
            source_tree.get("path") != contract_tree.get("path")
            or source_tree.get("sha256") != contract_tree.get("sha256")
            or source_tree.get("sha256") != calculated
        ):
            tree_embedded_ok = False
    _check(tree_embedded_ok, "source_trees_embedded", checks, errors)
    current_source_ok = True
    if require_current_source:
        for item in contract_records:
            path = PROJECT_ROOT / item["path"]
            if not path.is_file() or sha256_file(path) != item["sha256"]:
                current_source_ok = False
                errors.append(f"current source differs: {item['path']}")
        for item in contract_trees:
            actual = _tree_record(item["path"])
            if actual["sha256"] != item["sha256"]:
                current_source_ok = False
                errors.append(f"current source tree differs: {item['path']}")
    checks["current_source"] = current_source_ok

    manifest_without_sha = {key: value for key, value in dataset.items() if key != "dataset_sha256"}
    dataset_identity = sha256_bytes(canonical_json_bytes(manifest_without_sha))
    _check(
        dataset.get("dataset_sha256") == dataset_identity,
        "dataset_identity_hash",
        checks,
        errors,
    )
    allowed = [int(v) for v in profile.get("allowed_num_vars", [])]
    records = dataset.get("records", [])
    regenerated = []
    regeneration_ok = True
    try:
        for record in records:
            expected = _regenerate_record(record, allowed)
            regenerated.append(expected)
            if expected != record:
                regeneration_ok = False
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        regeneration_ok = False
    _check(regeneration_ok, "dataset_regeneration", checks, errors)
    identities = [(item.get("num_vars"), item.get("truth_table_sha256")) for item in records]
    _check(len(identities) == len(set(identities)), "dataset_unique", checks, errors)
    train_ids = {
        (item["num_vars"], item["truth_table_sha256"])
        for item in records
        if item.get("split") == "train"
    }
    holdout_ids = {
        (item["num_vars"], item["truth_table_sha256"])
        for item in records
        if item.get("split") == "holdout"
    }
    _check(not (train_ids & holdout_ids), "split_disjoint", checks, errors)
    expected_count = int(profile.get("iterations", 0)) * int(
        profile.get("functions_per_iteration", 0)
    ) + int(profile.get("holdout_functions", 0))
    _check(len(records) == expected_count, "dataset_count", checks, errors)

    crypto = dataset.get("crypto_exclusion", {})
    config_crypto = config.get("crypto_exclusion", {})
    registry = config_crypto.get("registered_families", [])
    registry_widths = {int(item["input_width"]) for item in registry}
    excluded_widths = {int(value) for value in config_crypto.get("excluded_input_widths", [])}
    forbidden_hashes = set(config_crypto.get("forbidden_truth_table_sha256", []))
    _check(registry_widths <= excluded_widths, "all_crypto_widths_excluded", checks, errors)
    _check(not (set(allowed) & excluded_widths), "profile_crypto_disjoint", checks, errors)
    _check(
        forbidden_hashes == EXPECTED_CRYPTO_TRUTH_TABLE_SHA256,
        "registered_crypto_hash_denylist",
        checks,
        errors,
    )
    _check(
        not ({item["truth_table_sha256"] for item in records} & forbidden_hashes),
        "dataset_crypto_hash_disjoint",
        checks,
        errors,
    )
    _check(
        crypto.get("registered_families") == registry
        and crypto.get("registry_sha256") == config_crypto.get("registry_sha256")
        and set(crypto.get("forbidden_truth_table_sha256", [])) == forbidden_hashes,
        "crypto_registry_bound",
        checks,
        errors,
    )
    _check(
        all(item.get("source_kind") == "synthetic_uniform_hashstream" for item in records),
        "synthetic_only",
        checks,
        errors,
    )

    expected_events = 2 + int(profile.get("iterations", 0))
    _check(len(log) == expected_events, "log_event_count", checks, errors)
    _check(
        bool(log)
        and log[0].get("event") == "initial_validation"
        and log[-1].get("event") == "final_validation",
        "log_boundaries",
        checks,
        errors,
    )
    _check(
        all(
            all(not isinstance(value, float) or math.isfinite(value) for value in event.values())
            for event in log
        ),
        "log_top_level_finite",
        checks,
        errors,
    )
    _check(
        all(
            event.get("verdict") in {"accept", "reject_and_rollback"}
            for event in log
            if event.get("event") == "training_iteration"
        ),
        "reject_policy_logged",
        checks,
        errors,
    )

    checkpoint_path = root / "checkpoint.pt"
    checkpoint_sha = sha256_file(checkpoint_path)
    checkpoint_meta = summary.get("checkpoint", {})
    _check(
        checkpoint_meta.get("sha256") == checkpoint_sha,
        "checkpoint_hash_link",
        checks,
        errors,
    )
    checkpoint_ok = True
    payload: dict[str, Any] = {}
    parameter_count = -1
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        scorer = FoundationScorer.from_checkpoint(checkpoint_path)
        parameter_count = sum(parameter.numel() for parameter in scorer.model.parameters())
        checkpoint_ok = all(
            bool(torch.isfinite(tensor).all()) for tensor in payload["state_dict"].values()
        )
    except (OSError, KeyError, RuntimeError, TypeError, ValueError):
        checkpoint_ok = False
    _check(checkpoint_ok, "checkpoint_load_and_finite", checks, errors)
    _check(
        parameter_count == checkpoint_meta.get("parameter_count")
        and parameter_count == EXPECTED_PARAMETER_COUNT,
        "parameter_count",
        checks,
        errors,
    )
    provenance = payload.get("provenance", {}) if isinstance(payload, dict) else {}
    _check(
        isinstance(payload, dict)
        and payload.get("hidden") == 32
        and payload.get("layers") == 2
        and payload.get("mlp_hidden") == 128,
        "checkpoint_architecture",
        checks,
        errors,
    )
    _check(
        provenance.get("initialization") == "seeded_random_from_scratch"
        and provenance.get("parent_checkpoint") is None
        and provenance.get("v3_weights_loaded") is False,
        "checkpoint_from_scratch",
        checks,
        errors,
    )
    _check(
        provenance.get("config_sha256") == config_sha
        and provenance.get("source_manifest_sha256") == source_sha
        and provenance.get("dataset_manifest_sha256") == dataset_file_sha
        and provenance.get("command_sha256") == command_sha
        and provenance.get("training_log_sha256") == log_sha,
        "checkpoint_provenance_links",
        checks,
        errors,
    )

    _check(
        model_card.get("artifact", {}).get("sha256") == checkpoint_sha
        and model_card.get("architecture", {}).get("parameter_count") == parameter_count,
        "model_card_checkpoint",
        checks,
        errors,
    )
    _check(
        model_card.get("training", {}).get("parent_checkpoint") is None
        and model_card.get("training", {}).get("v3_weights_loaded") is False,
        "model_card_from_scratch",
        checks,
        errors,
    )
    _check(
        model_card.get("data", {}).get("crypto_oracle_training_examples") == 0
        and model_card.get("data", {}).get("crypto_excluded") is True
        and model_card.get("data", {}).get("evaluation_not_accessed") is True,
        "model_card_crypto_exclusion",
        checks,
        errors,
    )
    _check(
        summary.get("performance_evidence") is False
        and (root / "artifacts.manifest.json").is_file(),
        "claim_boundary",
        checks,
        errors,
    )
    _check(
        all(self_checks.get("checks", {}).values()), "runner_self_checks", checks, errors
    )
    _check(
        command.get("cwd") == "${PROJECT_ROOT}"
        and all(str(PROJECT_ROOT) not in str(token) for token in command.get("argv", [])),
        "portable_command",
        checks,
        errors,
    )
    _check(
        estimate.get("status")
        in {"skipped_by_frozen_profile", "planning_estimate_not_benchmark_evidence"},
        "resource_estimate_boundary",
        checks,
        errors,
    )

    return {
        "ok": not errors and all(checks.values()),
        "bundle": str(root),
        "profile": profile_name,
        "checks": checks,
        "errors": errors,
        "checkpoint_sha256": checkpoint_sha,
        "parameter_count": parameter_count,
        "dataset_sha256": dataset.get("dataset_sha256"),
        "formal_training_completed": summary.get("formal_training_completed"),
        "performance_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--require-current-source", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = verify_foundation_v4_bundle(
        args.bundle, require_current_source=args.require_current_source
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
