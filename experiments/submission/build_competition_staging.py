#!/usr/bin/env python3
"""Build a deterministic, whitelist-only XA-202609 competition staging tree.

Default operation is fail-closed: a distributable archive is not produced until
all human authorization documents and declarations pass the explicit gate.
``--allow-incomplete`` is limited to an unmistakably named internal audit draft.
It is useful for testing package mechanics, but is never a final deliverable.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[2]
SPEC_PATH = SCRIPT.with_name("competition_staging_spec.json")
E6_RESULT_BUNDLE_REL = (
    "experiments/results/xa202609/"
    "20260812-e6-q4ai-causal-v1-full-s20260912"
)
E6_RESULT_SNAPSHOT_SHA256 = (
    "18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a"
)
E6_RESULT_BASENAMES = {
    "config.json", "results.json", "raw.jsonl", "heldout_evaluation.json",
    "checksums.sha256",
}
TEXT_SUFFIXES = {
    ".cfg", ".csv", ".json", ".jsonl", ".log", ".md", ".py", ".qasm",
    ".sha256", ".sh", ".tex", ".txt", ".yaml", ".yml",
}
AUTH_DECLARATIONS = (
    "registration_approved",
    "submitting_university_confirmed",
    "authorized_submitter_confirmed",
    "project_license_approved",
    "ip_statement_approved",
    "code_provenance_approved",
    "sshr_lib_prehistory_confirmed",
    "redistribution_authorized",
    "third_party_notices_approved",
    "model_data_redistribution_authorized",
    "transitive_sbom_reviewed",
)
PLACEHOLDER_RE = re.compile(
    r"(?im)(?:\bTODO\b|\bTBD\b|\bPLACEHOLDER\b|\bYOUR\s+(?:NAME|DATE|INSTITUTION)\b|"
    r"待确认|待填写|<\s*(?:[^>]*\b(?:name|date|year|institution|submitter)\b[^>]*)>|"
    r"\[\s*(?:yyyy|year|name|institution)\s*\])"
)


class BuildError(RuntimeError):
    """A fail-closed staging error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def e6_result_snapshot_sha256(path: Path) -> str:
    files = {item.name for item in path.iterdir() if item.is_file() and not item.is_symlink()}
    if files != E6_RESULT_BASENAMES:
        raise BuildError("E6 development result bundle must contain exactly five files")
    records = [
        {"name": name, "sha256": sha256_file(path / name), "bytes": (path / name).stat().st_size}
        for name in sorted(files)
    ]
    payload = (json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return sha256_bytes(payload)


def canonical_json(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BuildError(f"unsafe repository-relative path: {value!r}")
    if "\\" in value:
        raise BuildError(f"backslash is not allowed in repository paths: {value!r}")
    return path


def sha256_argument(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise argparse.ArgumentTypeError("expected 64 lowercase hexadecimal characters")
    return value


def validate_generated_destination(path: Path, label: str) -> None:
    """Keep repository-local generated outputs inside the ignored staging area."""
    repo = REPO_ROOT.resolve()
    try:
        rel = path.resolve().relative_to(repo)
    except ValueError:
        return
    allowed = Path("docs/competition/submission/generated")
    if rel != allowed and allowed not in rel.parents:
        raise BuildError(
            f"repository-local {label} must be under docs/competition/submission/generated: {rel.as_posix()}"
        )


def resolve_repo_file(value: str) -> Path:
    rel = validate_relative_path(value)
    candidate = REPO_ROOT.joinpath(*rel.parts)
    if not candidate.exists() or not candidate.is_file():
        raise BuildError(f"required file is missing: {value}")
    if candidate.is_symlink():
        raise BuildError(f"symlink input is forbidden: {value}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise BuildError(f"input escapes repository root: {value}") from exc
    return candidate


def load_spec() -> dict[str, Any]:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "xa.competition-staging-spec.v1":
        raise BuildError("unsupported staging spec schema")
    if payload.get("competition_id") != "XA-202609":
        raise BuildError("competition id mismatch in staging spec")
    return payload


def collect_whitelist(spec: dict[str, Any]) -> list[str]:
    selected = set()
    for value in spec["required_files"]:
        resolve_repo_file(value)
        selected.add(value)
    for pattern in spec["required_globs"]:
        validate_relative_path(pattern.replace("*", "x"))
        matches = [path for path in REPO_ROOT.glob(pattern) if path.is_file() and not path.is_symlink()]
        if not matches:
            raise BuildError(f"required glob is empty: {pattern}")
        for path in matches:
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in {"__pycache__", ".git", ".venv"} for part in path.parts):
                raise BuildError(f"cache/build path entered whitelist: {rel}")
            selected.add(rel)
    model_release = spec.get("final_model_release", {})
    optional_model_files = [model_release.get("machine_model_card"), *model_release.get("evidence_files", [])]
    for value in optional_model_files:
        if not value:
            continue
        validate_relative_path(value)
        candidate = REPO_ROOT / value
        if candidate.is_file():
            resolve_repo_file(value)
            selected.add(value)
    anchored = spec.get("externally_anchored_bundles", {})
    for bundle in anchored.get("bundles", []):
        source_rel = bundle.get("source", "")
        validate_relative_path(source_rel)
        names = bundle.get("files", [])
        if not isinstance(names, list) or not names:
            raise BuildError(f"externally anchored bundle has no explicit files: {source_rel}")
        for name in names:
            if not isinstance(name, str) or PurePosixPath(name).name != name:
                raise BuildError(f"unsafe externally anchored bundle filename: {name!r}")
            value = f"{source_rel}/{name}"
            resolve_repo_file(value)
            selected.add(value)
    return sorted(selected)


def git_provenance() -> dict[str, Any]:
    def run(*args: str) -> bytes:
        try:
            return subprocess.check_output(
                ["git", "-C", str(REPO_ROOT), *args], stderr=subprocess.DEVNULL
            )
        except (OSError, subprocess.CalledProcessError):
            return b""

    commit = run("rev-parse", "HEAD").decode("utf-8", errors="replace").strip() or "unavailable"
    status = run("status", "--porcelain=v1", "--untracked-files=all")
    diff_index = run("diff", "--raw", "--no-abbrev", "--no-ext-diff", "HEAD", "--")
    return {
        "commit_sha": commit,
        "dirty": bool(status.strip()),
        "dirty_status_sha256": sha256_bytes(status),
        "dirty_diff_index_sha256": sha256_bytes(diff_index),
        "repository_root": ".",
    }


def python_source_tree_sha256(release: dict[str, Any]) -> tuple[str, int]:
    selected: set[Path] = set()
    for pattern in release.get("source_globs", []):
        selected.update(path for path in REPO_ROOT.glob(pattern) if path.is_file())
    for value in release.get("source_files", []):
        selected.add(resolve_repo_file(value))
    files = sorted(selected, key=lambda path: path.relative_to(REPO_ROOT).as_posix())
    digest = hashlib.sha256()
    count = 0
    for path in files:
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def parse_source_checksums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in rows:
            raise BuildError(f"invalid or duplicate checksum row in {path}")
        rows[match.group(2)] = match.group(1)
    return rows


def directory_snapshot_binding(path: Path) -> dict[str, Any]:
    records = []
    for item in sorted(path.iterdir(), key=lambda candidate: candidate.name):
        if not item.is_file() or item.is_symlink():
            raise BuildError(f"anchored bundle contains a non-regular entry: {item}")
        records.append([item.name, item.stat().st_size, sha256_file(item)])
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "run_id": path.name,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": sha256_bytes(payload),
        "snapshot_files": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, size, digest in records
        ],
    }


def externally_anchored_evidence_status(spec: dict[str, Any]) -> dict[str, Any]:
    """Bind the exact portable-E5 bundles to a repository-protected anchor."""
    section = spec.get("externally_anchored_bundles", {})
    anchor_spec = section.get("anchor", {})
    anchor_rel = anchor_spec.get("path", "")
    anchor_path = resolve_repo_file(anchor_rel)
    observed_anchor_sha = sha256_file(anchor_path)
    expected_anchor_sha = anchor_spec.get("sha256")
    if observed_anchor_sha != expected_anchor_sha:
        raise BuildError(
            "external E5 anchor SHA mismatch: "
            f"expected {expected_anchor_sha}, observed {observed_anchor_sha}"
        )
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"invalid external E5 anchor: {exc}") from exc
    if anchor.get("schema_version") != "xa.e5-v11-portable-fresh-validation-anchor.v2":
        raise BuildError("external E5 anchor schema mismatch")

    source_rows = anchor.get("source_files", {})
    if not isinstance(source_rows, dict) or set(source_rows) != {
        "fresh_builder", "fresh_test", "fresh_verifier",
        "scientific_producer", "scientific_test", "scientific_verifier",
    }:
        raise BuildError("external E5 anchor source inventory mismatch")
    for label, row in source_rows.items():
        rel = f"experiments/{row.get('path', '')}"
        source = resolve_repo_file(rel)
        if source.stat().st_size != row.get("bytes") or sha256_file(source) != row.get("sha256"):
            raise BuildError(f"external E5 anchor source mismatch: {label}")

    requirements = anchor.get("requirements_closure", {}).get("files", [])
    if not isinstance(requirements, list) or len(requirements) != 2:
        raise BuildError("external E5 anchor requirements closure is malformed")
    for row in requirements:
        rel = f"experiments/{row.get('path', '')}"
        requirement = resolve_repo_file(rel)
        if requirement.stat().st_size != row.get("bytes") or sha256_file(requirement) != row.get("sha256"):
            raise BuildError(f"external E5 anchor requirement mismatch: {rel}")

    bundle_reports = []
    bundle_specs = section.get("bundles", [])
    expected_bundle_ids = {
        "E5_V11_PREFLIGHT_SOURCE_LINK",
        "E5_V11_SEAL_SOURCE_LINK",
        "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR",
        "E5_NEGATIVE_V1_PREDECESSOR",
        "E5_PORTABLE_V2_PREDECESSOR",
        "E5_FRESH_V1_PREDECESSOR",
        "E5_PORTABLE_V3",
        "E5_FRESH_V2",
    }
    if not isinstance(bundle_specs, list) or {row.get("id") for row in bundle_specs} != expected_bundle_ids:
        raise BuildError("external E5 bundle inventory mismatch")
    for bundle in bundle_specs:
        bundle_id = bundle.get("id")
        source_rel = bundle.get("source", "")
        validate_relative_path(source_rel)
        source_dir = REPO_ROOT / source_rel
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise BuildError(f"externally anchored bundle is missing: {source_rel}")
        expected_names = bundle.get("files", [])
        if not isinstance(expected_names, list) or len(expected_names) != 9 or len(set(expected_names)) != 9:
            raise BuildError(f"externally anchored bundle is not an explicit nine-file set: {bundle_id}")
        actual_names = sorted(
            item.name for item in source_dir.iterdir() if item.is_file() and not item.is_symlink()
        )
        if actual_names != sorted(expected_names):
            raise BuildError(f"externally anchored bundle exact file set mismatch: {bundle_id}")
        binding = directory_snapshot_binding(source_dir)
        anchor_key = bundle.get("anchor_key")
        anchored_binding = anchor.get(anchor_key) if anchor_key else None
        anchor_run_id = bundle.get("anchor_run_id")
        if anchor_run_id:
            anchored_snapshot = anchored_binding.get(anchor_run_id) if isinstance(anchored_binding, dict) else None
            anchor_matches = binding.get("snapshot_sha256") == anchored_snapshot
        elif anchor_key:
            anchor_matches = binding == anchored_binding
        else:
            anchor_matches = bundle_id in {
                "E5_V11_PREFLIGHT_SOURCE_LINK",
                "E5_V11_SEAL_SOURCE_LINK",
                "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR",
            }
        if not anchor_matches:
            raise BuildError(f"externally anchored bundle does not match anchor: {bundle_id}")
        if binding.get("snapshot_sha256") != bundle.get("snapshot_sha256"):
            raise BuildError(f"externally anchored bundle snapshot mismatch: {bundle_id}")
        checksums = parse_source_checksums(source_dir / "checksums.sha256")
        if set(checksums) != set(expected_names) - {"checksums.sha256"}:
            raise BuildError(f"externally anchored bundle checksum coverage mismatch: {bundle_id}")
        for name, digest in checksums.items():
            if sha256_file(source_dir / name) != digest:
                raise BuildError(f"externally anchored bundle checksum mismatch: {bundle_id}/{name}")
        bundle_reports.append(
            {
                "id": bundle_id,
                "path": source_rel,
                "anchor_key": anchor_key,
                "anchor_run_id": anchor_run_id,
                "role": bundle.get("role"),
                "run_id": binding["run_id"],
                "snapshot_algorithm": binding["snapshot_algorithm"],
                "snapshot_sha256": binding["snapshot_sha256"],
                "files": binding["snapshot_files"],
                "exact_nine_file_set": True,
                "bundle_checksums_verified": True,
            }
        )

    reports_by_id = {row["id"]: row for row in bundle_reports}
    exception_ids = {"E5_FRESH_V1_PREDECESSOR", "E5_FRESH_V2"}
    locked_target = (
        "/Users/zhouzixiang/Desktop/tzb/experiments/results/xa202609/"
        "20260812-e5-v11-portable-negative-audit-v3-s950000"
    )
    observed_local_path_count = 0
    for row in bundle_reports:
        directory = REPO_ROOT / row["path"]
        bundle_occurrences = sum(
            item.read_bytes().count(b"/Users/")
            for item in directory.iterdir()
            if item.is_file()
        )
        observed_local_path_count += bundle_occurrences
        if row["id"] not in exception_ids:
            if bundle_occurrences:
                raise BuildError(f"unexpected local path in anchored bundle: {row['id']}")
            continue
        raw_rows = [
            json.loads(line)
            for line in (directory / "raw.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        matched = [
            command
            for command in raw_rows
            if isinstance(command, dict)
            and isinstance(command.get("stdout"), dict)
            and "/Users/" in str(command["stdout"].get("text", ""))
        ]
        if not (
            bundle_occurrences == 1
            and len(matched) == 1
            and matched[0].get("command_id") == "portable_v3_verifier"
            and matched[0].get("stdout", {}).get("text", "").count(locked_target) == 1
            and matched[0].get("stdout", {}).get("text", "").count("/Users/") == 1
        ):
            raise BuildError(f"locked local-path exception shape mismatch: {row['id']}")
    if observed_local_path_count != 2:
        raise BuildError("anchored bundles must contain exactly two locked local-path exceptions")

    portable = json.loads(
        (REPO_ROOT / reports_by_id["E5_PORTABLE_V3"]["path"] / "summary.json").read_text(encoding="utf-8")
    )
    scientific_source = json.loads(
        (
            REPO_ROOT
            / reports_by_id["E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR"]["path"]
            / "summary.json"
        ).read_text(encoding="utf-8")
    )
    scientific_source_verifier = json.loads(
        (
            REPO_ROOT
            / reports_by_id["E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR"]["path"]
            / "verifier.json"
        ).read_text(encoding="utf-8")
    )
    fresh = json.loads(
        (REPO_ROOT / reports_by_id["E5_FRESH_V2"]["path"] / "summary.json").read_text(encoding="utf-8")
    )
    if not (
        scientific_source.get("trial_count") == 90
        and scientific_source.get("complete_matrix") is True
        and scientific_source.get("v4_four_arm_fairness", {}).get(
            "family_schedulable_group_counts", {}
        ).get("ASCON") == 0
        and scientific_source_verifier.get("ok") is False
        and scientific_source_verifier.get("checks", {}).get(
            "each_family_has_schedulable_activity"
        ) is False
        and portable.get("schema_version") == "xa.e5-v11-portable-negative-audit-summary.v3"
        and portable.get("protocol_acceptance") is False
        and portable.get("experiment_completed") is False
        and portable.get("performance_claim_supported") is False
        and fresh.get("schema_version") == "xa.e5-v11-portable-fresh-validation-summary.v2"
        and fresh.get("full_pytest_passed") == 383
        and fresh.get("successful_command_count") == 9
        and fresh.get("software_validation_ok") is True
        and fresh.get("scientific_bundle_independently_recomputed") is True
        and fresh.get("scientific_evidence") is False
        and fresh.get("protocol_acceptance") is False
        and fresh.get("hardware_execution") is False
    ):
        raise BuildError("externally anchored E5 claim boundary mismatch")
    return {
        "schema_version": "xa.externally-anchored-evidence.v1",
        "status": "closed_software_validation_only",
        "anchor": {
            "path": anchor_rel,
            "sha256": observed_anchor_sha,
            "schema_version": anchor.get("schema_version"),
        },
        "bundles": bundle_reports,
        "source_files_verified": True,
        "requirements_closure_verified": True,
        "predecessor_role": "provenance_predecessor_only_not_performance_or_recommendation",
        "scientific_source_predecessor_role": "scientific_source_predecessor_only_unaccepted_endpoint",
        "scientific_source_link_roles": [
            "scientific_source_linked_preflight_only",
            "scientific_source_linked_seal_only",
        ],
        "locked_local_path_exceptions": {
            "count": 2,
            "files": [
                (
                    "experiments/results/xa202609/"
                    "20260812-e5-v11-portable-fresh-validation-v1-s960000/raw.jsonl"
                ),
                (
                    "experiments/results/xa202609/"
                    "20260812-e5-v11-portable-fresh-validation-v2-s970000/raw.jsonl"
                ),
            ],
            "json_field": "stdout.text",
            "command_id": "portable_v3_verifier",
            "target_run": "20260812-e5-v11-portable-negative-audit-v3-s950000",
            "purpose": "immutable historical stdout bytes; not a runtime dependency",
        },
        "fresh_validation": {
            "successful_command_count": 9,
            "full_pytest_passed": 383,
            "targeted_e5_passed": fresh.get("targeted_e5_passed"),
            "software_validation_ok": True,
            "historical_commands_authenticated": fresh.get("historical_commands_authenticated"),
            "historical_commands_independently_rerun_by_bundle_verifier": False,
        },
        "claim_boundary": (
            "Externally anchored software/portability evidence only; the scientific V3 bundle remains "
            "a negative audit with protocol_acceptance=false and supplies no accepted E5 endpoint, "
            "hardware result, performance evidence, or quantum-advantage claim."
        ),
    }


def formal_v4_provenance_status(release: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate the provenance-closed v4 candidate without promoting it to final."""
    blockers: list[str] = []
    bundle_rel = release.get("provenance_bundle", "")
    validate_relative_path(bundle_rel)
    bundle = REPO_ROOT / bundle_rel
    required = {
        "checkpoint.pt", "command.json", "config_snapshot.json", "dataset_manifest.json",
        "model_card.json", "resource_estimate.json", "self_checks.json", "source_manifest.json",
        "training_log.jsonl", "training_summary.json", "artifacts.manifest.json",
        "checksums.sha256",
    }
    if not bundle.is_dir() or bundle.is_symlink():
        return {
            "status": "missing",
            "closed": False,
            "bundle": bundle_rel or None,
        }, ["formal_v4_provenance_bundle_missing"]
    present = {path.name for path in bundle.iterdir() if path.is_file() and not path.is_symlink()}
    if not required <= present:
        blockers.append("formal_v4_provenance_files_missing")
    try:
        checksums = parse_source_checksums(bundle / "checksums.sha256")
    except (OSError, UnicodeDecodeError, BuildError):
        checksums = {}
        blockers.append("formal_v4_checksums_invalid")
    expected_covered = required - {"checksums.sha256"}
    if set(checksums) != expected_covered:
        blockers.append("formal_v4_checksum_coverage_invalid")
    for name, digest in checksums.items():
        target = bundle / name
        if not target.is_file() or target.is_symlink() or sha256_file(target) != digest:
            blockers.append("formal_v4_checksum_mismatch")
            break

    def load(name: str) -> dict[str, Any]:
        try:
            value = json.loads((bundle / name).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BuildError(f"invalid formal v4 JSON {name}: {exc}") from exc
        if not isinstance(value, dict):
            raise BuildError(f"formal v4 JSON must be an object: {name}")
        return value

    try:
        command = load("command.json")
        config = load("config_snapshot.json")
        dataset = load("dataset_manifest.json")
        card = load("model_card.json")
        summary = load("training_summary.json")
        self_checks = load("self_checks.json")
        source = load("source_manifest.json")
        artifacts = load("artifacts.manifest.json")
    except BuildError:
        command = config = dataset = card = summary = self_checks = source = artifacts = {}
        blockers.append("formal_v4_json_evidence_invalid")

    argv = command.get("argv", [])
    command_ok = (
        command.get("schema_version") == "xa.foundation-training-command.v4"
        and command.get("cwd") == "${PROJECT_ROOT}"
        and command.get("executable") == "python"
        and isinstance(argv, list)
        and argv[:1] == ["scripts/train_foundation_v4.py"]
        and not any(re.search(r"(?:/Users/|/home/|[A-Za-z]:\\\\)", str(part)) for part in argv)
    )
    if not command_ok:
        blockers.append("training_command_unverified")
    formal_profile = config.get("profiles", {}).get("formal", {})
    seed = formal_profile.get("seed")
    if (
        config.get("schema_version") != "xa.foundation-training-config.v4"
        or config.get("selected_profile") != "formal"
        or not isinstance(seed, int)
    ):
        blockers.extend(["training_config_unverified", "training_seeds_unverified"])
    records = dataset.get("records", [])
    identities = [(row.get("num_vars"), row.get("truth_table_sha256")) for row in records if isinstance(row, dict)]
    split_names = {row.get("split") for row in records if isinstance(row, dict)}
    crypto = dataset.get("crypto_exclusion", {})
    split_ok = (
        dataset.get("schema_version") == "xa.foundation-dataset-manifest.v4"
        and len(records) == 208
        and len(identities) == len(set(identities))
        and {"train", "holdout"} <= split_names
        and dataset.get("split_contract", {}).get("holdout_used_for_fit") is False
        and crypto.get("evaluation_not_accessed") is True
        and crypto.get("evaluation_module_imported_during_training") is False
    )
    if not split_ok:
        blockers.append("dataset_split_manifest_unverified")
    source_identity = source.get("git_identity", {})
    source_ok = (
        source.get("schema_version") == "xa.foundation-source-manifest.v4"
        and isinstance(source_identity.get("commit_sha"), str)
        and re.fullmatch(r"[0-9a-f]{40}", source_identity.get("commit_sha", ""))
        and re.fullmatch(r"[0-9a-f]{64}", source_identity.get("source_tree_sha256", ""))
        and bool(source.get("files"))
        and bool(source.get("trees"))
    )
    if not source_ok:
        blockers.append("training_source_sha_provenance_unverified")
    try:
        log_rows = [json.loads(line) for line in (bundle / "training_log.jsonl").read_text(encoding="utf-8").splitlines()]
        log_ok = bool(log_rows) and {row.get("event") for row in log_rows} >= {
            "initial_validation", "training_iteration", "final_validation"
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        log_ok = False
    if not log_ok:
        blockers.append("training_logs_or_hashes_unverified")
    checkpoint_sha = sha256_file(bundle / "checkpoint.pt") if (bundle / "checkpoint.pt").is_file() else None
    card_links = card.get("training", {}).get("hash_links", {})
    link_names = {
        "command_sha256": "command.json",
        "config_sha256": "config_snapshot.json",
        "dataset_manifest_sha256": "dataset_manifest.json",
        "resource_estimate_sha256": "resource_estimate.json",
        "source_manifest_sha256": "source_manifest.json",
        "training_log_sha256": "training_log.jsonl",
    }
    links_ok = all(card_links.get(key) == checksums.get(name) for key, name in link_names.items())
    checkpoint_ok = (
        checkpoint_sha == release.get("expected_checkpoint_sha256")
        and card.get("artifact", {}).get("sha256") == checkpoint_sha
        and summary.get("checkpoint", {}).get("sha256") == checkpoint_sha
    )
    if not checkpoint_ok:
        blockers.append("machine_model_card_checkpoint_mismatch")
    if not links_ok:
        blockers.append("training_evidence_hash_links_unverified")
    checks = self_checks.get("checks", {})
    evidence_boundary_ok = (
        card.get("schema_version") == release.get("candidate_schema_version")
        and card.get("model_id") == "boolean_oracle_fm_v4"
        and card.get("training", {}).get("seed") == seed
        and card.get("data", {}).get("crypto_oracle_training_examples") == 0
        and card.get("data", {}).get("evaluation_not_accessed") is True
        and summary.get("formal_training_completed") is True
        and summary.get("performance_evidence") is False
        and artifacts.get("bundle_metadata", {}).get("performance_evidence") is False
        and bool(checks)
        and all(value is True for value in checks.values())
    )
    if not evidence_boundary_ok:
        blockers.append("formal_v4_claim_boundary_unverified")
    provenance_blockers = {
        "training_command_unverified", "training_config_unverified",
        "dataset_split_manifest_unverified", "training_seeds_unverified",
        "training_logs_or_hashes_unverified", "training_source_sha_provenance_unverified",
        "training_evidence_hash_links_unverified", "formal_v4_provenance_files_missing",
        "formal_v4_checksums_invalid", "formal_v4_checksum_coverage_invalid",
        "formal_v4_checksum_mismatch", "formal_v4_json_evidence_invalid",
        "machine_model_card_checkpoint_mismatch",
    }
    closed = not any(blocker in provenance_blockers for blocker in blockers)
    return {
        "status": "provenance_closed_development_candidate" if closed else "incomplete",
        "closed": closed,
        "bundle": bundle_rel,
        "checkpoint_sha256": checkpoint_sha,
        "model_card_schema": card.get("schema_version"),
        "training_command_verified": command_ok,
        "config_verified": "training_config_unverified" not in blockers,
        "split_manifest_verified": split_ok,
        "seed": seed if isinstance(seed, int) else None,
        "training_log_verified": log_ok,
        "source_sha_provenance_verified": source_ok,
        "source_git_dirty": source_identity.get("dirty"),
        "performance_evidence": False,
        "claim_boundary": "Formal v4 closes training provenance only; it is not final-model or performance evidence.",
    }, blockers


def research_claim_status(external_evidence: dict[str, Any]) -> dict[str, Any]:
    e4 = json.loads(resolve_repo_file(
        "experiments/results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-test/summary.json"
    ).read_text(encoding="utf-8"))
    e5 = json.loads(resolve_repo_file(
        "experiments/results/xa202609/20260812-e5-v11-negative-audit-v1-s950000/summary.json"
    ).read_text(encoding="utf-8"))
    e6_mechanism = json.loads(resolve_repo_file(
        "experiments/configs/xa202609/e6_multioutput_shared_mvp_v1.json"
    ).read_text(encoding="utf-8"))
    e6_bundle_rel = validate_relative_path(E6_RESULT_BUNDLE_REL)
    e6_bundle = REPO_ROOT.joinpath(*e6_bundle_rel.parts)
    if not e6_bundle.is_dir() or e6_bundle.is_symlink():
        raise BuildError(f"required directory is missing or unsafe: {E6_RESULT_BUNDLE_REL}")
    e6_snapshot_sha256 = e6_result_snapshot_sha256(e6_bundle)
    if e6_snapshot_sha256 != E6_RESULT_SNAPSHOT_SHA256:
        raise BuildError("E6 development result bundle snapshot mismatch")
    e6_results = json.loads((e6_bundle / "results.json").read_text(encoding="utf-8"))
    e6_heldout = json.loads(
        (e6_bundle / "heldout_evaluation.json").read_text(encoding="utf-8")
    )
    e6_primary = e6_heldout.get("statistics", {}).get("primary", {})
    e6_bootstrap = e6_primary.get("bootstrap", {})
    e6_signflip = e6_primary.get("signflip", {})
    e6_reports = e6_results.get("training_report_by_arm", {})
    e6_sample_counts = {
        report.get("sample_count")
        for report in e6_reports.values()
        if isinstance(report, dict)
    }
    comparison = e4.get("primary_comparison", {})
    external_by_id = {row.get("id"): row for row in external_evidence.get("bundles", [])}
    return {
        "formal_v4": {
            "provenance_closed": True,
            "performance_evidence": False,
            "final_model": False,
        },
        "e4_v2": {
            "role": e4.get("scope", {}).get("dataset_role"),
            "generalization_claim": e4.get("scope", {}).get("generalization_claim"),
            "historically_seen_in_e4": e4.get("scope", {}).get("historically_seen_in_E4"),
            "mean_native_2q_delta": comparison.get("mean_delta_execution_minus_historical"),
            "bootstrap_95_ci": comparison.get("bootstrap_95_ci"),
            "improvement_supported": False,
        },
        "e5": {
            "v1_first_release_trial_rows": 0,
            "v11_matrix_rows": e5.get("counts", {}).get("row_count"),
            "protocol_acceptance": e5.get("protocol_acceptance"),
            "accepted_endpoint": False,
            "performance_claim_supported": e5.get("performance_claim_supported"),
            "ascon_schedulable_groups": e5.get("family_schedulable_group_counts", {}).get("ASCON"),
            "portable_v3_snapshot_sha256": (
                external_by_id.get("E5_PORTABLE_V3", {}).get("snapshot_sha256")
            ),
            "fresh_v2_snapshot_sha256": (
                external_by_id.get("E5_FRESH_V2", {}).get("snapshot_sha256")
            ),
            "external_anchor_sha256": external_evidence.get("anchor", {}).get("sha256"),
            "fresh_full_pytest_passed": external_evidence.get("fresh_validation", {}).get("full_pytest_passed"),
            "fresh_successful_command_count": external_evidence.get("fresh_validation", {}).get("successful_command_count"),
            "software_validation_ok": external_evidence.get("fresh_validation", {}).get("software_validation_ok"),
            "scientific_evidence": False,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
        "e6": {
            "status": "development_causal_negative_result_verified",
            "mechanism_status": e6_mechanism.get("status"),
            "development_result_bundle_present": True,
            "formal_result_bundle_present": False,
            "bundle_path": E6_RESULT_BUNDLE_REL,
            "bundle_snapshot_sha256": e6_snapshot_sha256,
            "run_id": e6_results.get("run_id"),
            "source_commit": e6_results.get("source_commit"),
            "training_or_finetuning_performed": bool(e6_reports),
            "train_case_count": next(iter(e6_sample_counts)) if len(e6_sample_counts) == 1 else None,
            "heldout_case_count": e6_primary.get("case_count"),
            "primary_comparison": e6_primary.get("comparison"),
            "mean_effect": e6_primary.get("effect_estimate"),
            "bootstrap_95_ci": [
                e6_bootstrap.get("ci_lower"),
                e6_bootstrap.get("ci_upper"),
            ],
            "signflip_p": e6_signflip.get("p_value"),
            "wins": e6_primary.get("wins"),
            "ties": e6_primary.get("ties"),
            "losses": e6_primary.get("losses"),
            "claim_supported": e6_heldout.get("statistics", {})
            .get("claim_gate", {})
            .get("claim_supported"),
            "compute_budget_equal": False,
            "development_conditional_only": True,
            "formal_evaluation": e6_heldout.get("formal_evaluation"),
            "performance_evidence": e6_heldout.get("performance_evidence"),
            "generalization_claim": False,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
    }


def final_model_release_status(
    spec: dict[str, Any],
    git: dict[str, Any],
    external_evidence: dict[str, Any],
) -> dict[str, Any]:
    release = spec.get("final_model_release", {})
    provenance, blockers = formal_v4_provenance_status(release)
    checkpoint_rel = release.get("checkpoint", "")
    machine_card_rel = release.get("machine_model_card", "")
    human_card_rel = release.get("human_model_card", "")
    checkpoint_sha = sha256_file(resolve_repo_file(checkpoint_rel))
    legacy_card = resolve_repo_file(human_card_rel).read_text(encoding="utf-8", errors="replace")
    development_markers = (
        "开发候选（development candidate）",
        "是否为 XA-202609 最终冻结模型**：否",
        "尚不能作为比赛最终模型交付",
    )
    legacy_status = "development_candidate" if any(marker in legacy_card for marker in development_markers) else "unclassified"
    if legacy_status == "development_candidate":
        blockers.append("legacy_v3_demo_model_is_development_candidate")
    card = json.loads(resolve_repo_file(machine_card_rel).read_text(encoding="utf-8"))
    final_schema = release.get("required_final_schema_version")
    final_card = (
        card.get("schema_version") == final_schema
        and card.get("status") == "final_frozen"
        and card.get("development_candidate") is False
    )
    if not final_card:
        blockers.append("machine_model_card_is_provenance_candidate_not_final_frozen")
    blockers.append("final_external_performance_evidence_missing")
    if git.get("dirty") is not False:
        blockers.append("repository_not_clean_frozen_commit")
    source_tree_sha, source_tree_files = python_source_tree_sha256(release)
    blockers = sorted(set(blockers))
    return {
        "schema_version": "xa.technical-release-status.v2",
        "ready_for_final": not blockers,
        "status": "ready" if not blockers else "incomplete",
        "candidate_status": provenance.get("status"),
        "blockers": blockers,
        "checkpoint": {"path": checkpoint_rel, "sha256": checkpoint_sha},
        "legacy_demo_model_card": {"path": human_card_rel, "status": legacy_status},
        "machine_model_card": {
            "path": machine_card_rel,
            "present": True,
            "schema_version": card.get("schema_version"),
            "required_final_schema_version": final_schema,
            "final_frozen": final_card,
            "development_candidate": not final_card,
        },
        "training_provenance": provenance,
        "training_evidence_whitelist": sorted(set(release.get("evidence_files", []))),
        "source": {
            "commit_sha": git.get("commit_sha"),
            "repository_dirty": git.get("dirty"),
            "source_tree_algorithm": "xa-python-source-tree.v1",
            "source_tree_sha256": source_tree_sha,
            "source_tree_file_count": source_tree_files,
        },
        "externally_anchored_evidence": external_evidence,
        "research_claims": research_claim_status(external_evidence),
        "claim_boundary": "Training provenance, human authorization, and performance acceptance are independent fail-closed gates.",
    }


def parse_requirements(path: Path, group: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+(?:\[[^]]+\])?)(.*)$", line)
        if not match:
            raise BuildError(f"cannot parse requirement {path}:{line_number}: {line}")
        name, constraint = match.groups()
        components.append(
            {
                "group": group,
                "name": name,
                "constraint": constraint,
                "exact_pin": constraint.startswith("==") and "," not in constraint,
                "source_line": line_number,
            }
        )
    return components


def build_sbom_lite() -> dict[str, Any]:
    requirement_dir = REPO_ROOT / "experiments/environment/requirements"
    files = sorted(requirement_dir.glob("*.txt"))
    components: list[dict[str, Any]] = []
    requirements = []
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        requirements.append({"path": rel, "sha256": sha256_file(path)})
        components.extend(parse_requirements(path, path.stem))
    return {
        "schema_version": "xa.sbom-lite.v1",
        "competition_id": "XA-202609",
        "scope": "declared direct requirements only",
        "not_a_transitive_sbom": True,
        "requirements": requirements,
        "components": components,
    }


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if not isinstance(value, str):
        return value
    repo = str(REPO_ROOT)
    if value == repo:
        return "${REPO_ROOT}"
    if value.startswith(repo + os.sep):
        rel = Path(value).relative_to(REPO_ROOT).as_posix()
        return "${REPO_ROOT}/" + rel
    if re.match(r"^/(?:Users|home|private/(?:tmp|var/folders)|tmp)/", value):
        return "${LOCAL_PATH_REDACTED}/" + Path(value).name
    if re.match(r"^[A-Za-z]:\\", value):
        return "${LOCAL_PATH_REDACTED}/" + PurePosixPath(value.replace("\\", "/")).name
    return value


def safe_write_bytes(root: Path, rel: str, data: bytes) -> dict[str, Any]:
    path = validate_relative_path(rel)
    target = root.joinpath(*path.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise BuildError(f"duplicate staging target: {rel}")
    target.write_bytes(data)
    return {"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)}


def copy_whitelisted(root: Path, rel_paths: list[str]) -> list[dict[str, Any]]:
    entries = []
    for rel in rel_paths:
        source = resolve_repo_file(rel)
        data = source.read_bytes()
        entry = safe_write_bytes(root, rel, data)
        entry.update({"kind": "repository_file", "source_path": rel, "source_sha256": sha256_bytes(data)})
        entries.append(entry)
    return entries


def evidence_snapshot(root: Path, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_entries: list[dict[str, Any]] = []
    snapshot_reports: list[dict[str, Any]] = []
    include_names = set(spec["evidence_snapshot_files"])
    for bundle in spec["evidence_bundles"]:
        bundle_id = bundle["id"]
        source_rel = bundle["source"]
        claim_profile = bundle.get("claim_profile", "historical_evidence")
        source_dir = REPO_ROOT / source_rel
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise BuildError(f"evidence bundle is missing: {source_rel}")
        source_inventory = []
        included = []
        omitted = []
        snapshot_prefix = f"evidence_snapshots/{bundle_id}"
        for source in sorted(source_dir.iterdir(), key=lambda item: item.name):
            if not source.is_file() or source.is_symlink():
                continue
            original_data = source.read_bytes()
            source_item = {
                "name": source.name,
                "bytes": len(original_data),
                "sha256": sha256_bytes(original_data),
            }
            source_inventory.append(source_item)
            if source.name not in include_names:
                omitted.append(source_item)
                continue
            target_name = "source_bundle_checksums.sha256" if source.name == "checksums.sha256" else source.name
            if source.suffix == ".json":
                payload = json.loads(original_data.decode("utf-8"))
                packaged_data = canonical_json(sanitize_json_value(payload))
                normalized = packaged_data != original_data
            else:
                packaged_data = original_data
                normalized = False
            target_rel = f"{snapshot_prefix}/{target_name}"
            entry = safe_write_bytes(root, target_rel, packaged_data)
            entry.update(
                {
                    "kind": "evidence_snapshot",
                    "source_path": f"{source_rel}/{source.name}",
                    "source_sha256": source_item["sha256"],
                    "normalized_for_local_path_privacy": normalized,
                }
            )
            manifest_entries.append(entry)
            included.append(
                {
                    "source_name": source.name,
                    "target_name": target_name,
                    "source_sha256": source_item["sha256"],
                    "packaged_sha256": entry["sha256"],
                    "normalized_for_local_path_privacy": normalized,
                }
            )
        snapshot_manifest = {
            "schema_version": "xa.evidence-snapshot.v1",
            "bundle_id": bundle_id,
            "source_bundle": source_rel,
            "claim_profile": claim_profile,
            "source_inventory": source_inventory,
            "included": included,
            "omitted_large_or_log_artifacts": omitted,
            "claim": "compact evidence snapshot; not a replacement for the immutable full source bundle",
        }
        snapshot_rel = f"{snapshot_prefix}/SNAPSHOT_MANIFEST.json"
        entry = safe_write_bytes(root, snapshot_rel, canonical_json(snapshot_manifest))
        entry.update({"kind": "generated_evidence_manifest"})
        manifest_entries.append(entry)
        checksum_rows = []
        for item in sorted(included, key=lambda row: row["target_name"]):
            checksum_rows.append(f"{item['packaged_sha256']}  {item['target_name']}")
        checksum_rows.append(f"{entry['sha256']}  SNAPSHOT_MANIFEST.json")
        checksum_data = ("\n".join(checksum_rows) + "\n").encode("utf-8")
        checksum_entry = safe_write_bytes(root, f"{snapshot_prefix}/CHECKSUMS.sha256", checksum_data)
        checksum_entry.update({"kind": "generated_evidence_checksums"})
        manifest_entries.append(checksum_entry)
        snapshot_reports.append(
            {
                "bundle_id": bundle_id,
                "source_bundle": source_rel,
                "claim_profile": claim_profile,
                "source_file_count": len(source_inventory),
                "included_file_count": len(included),
                "omitted_file_count": len(omitted),
            }
        )
    return manifest_entries, snapshot_reports


def report_release_status(spec: dict[str, Any]) -> dict[str, Any]:
    release = spec.get("report_release", {})
    rel = release.get("path", "")
    expected = release.get("sha256", "")
    pages = release.get("page_count")
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or not isinstance(pages, int) or pages <= 0:
        raise BuildError("report release lock is incomplete")
    observed = sha256_file(resolve_repo_file(rel))
    if observed != expected:
        raise BuildError(f"report SHA mismatch: expected {expected}, observed {observed}")
    return {
        "path": rel,
        "sha256": observed,
        "page_count": pages,
        "release_note": "SHA-locked 38-page Chinese competition manuscript",
    }


def validate_authorization(auth_dir: Path | None, spec: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, bytes]]]:
    required = list(spec["final_authorization_documents"])
    if auth_dir is None:
        return {
            "schema_version": "xa.authorization-status.v1",
            "status": "incomplete",
            "distributable": False,
            "missing_documents": required,
            "failed_declarations": list(AUTH_DECLARATIONS),
            "reason": "human authorization directory was not supplied",
        }, []
    auth_dir = auth_dir.expanduser().resolve()
    if not auth_dir.is_dir():
        raise BuildError(f"authorization directory does not exist: {auth_dir}")
    documents: list[tuple[str, bytes]] = []
    missing = []
    invalid = []
    for name in required:
        path = auth_dir / name
        if not path.is_file() or path.is_symlink():
            missing.append(name)
            continue
        data = path.read_bytes()
        if len(data) < 16:
            invalid.append(f"{name}: empty or implausibly short")
            continue
        if path.suffix.lower() in {".md", ".json"} or name == "LICENSE":
            text = data.decode("utf-8", errors="replace")
            if PLACEHOLDER_RE.search(text):
                invalid.append(f"{name}: contains placeholder markers")
                continue
        documents.append((name, data))
    auth_payload: dict[str, Any] = {}
    auth_path = auth_dir / "SUBMISSION_AUTHORIZATION.json"
    if auth_path.is_file():
        try:
            auth_payload = json.loads(auth_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            invalid.append(f"SUBMISSION_AUTHORIZATION.json: invalid JSON ({exc})")
    failed_declarations = [key for key in AUTH_DECLARATIONS if auth_payload.get("declarations", {}).get(key) is not True]
    if auth_payload.get("schema_version") != "xa.submission-authorization.v1":
        invalid.append("SUBMISSION_AUTHORIZATION.json: schema_version must be xa.submission-authorization.v1")
    if auth_payload.get("competition_id") != "XA-202609":
        invalid.append("SUBMISSION_AUTHORIZATION.json: competition_id mismatch")
    if auth_payload.get("status") != "approved":
        invalid.append("SUBMISSION_AUTHORIZATION.json: status must be approved")
    for key in ("attested_by", "attested_role", "attested_at_utc", "submitting_university", "authorized_submitter"):
        value = auth_payload.get(key)
        if not isinstance(value, str) or len(value.strip()) < 2 or PLACEHOLDER_RE.search(value):
            invalid.append(f"SUBMISSION_AUTHORIZATION.json: valid {key} is required")
    archive_name = auth_payload.get("archive_name", "")
    if not re.fullmatch(r"XA-202609_[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz", archive_name):
        invalid.append("SUBMISSION_AUTHORIZATION.json: unsafe or nonconforming archive_name")
    if "draft" in archive_name.lower():
        invalid.append("SUBMISSION_AUTHORIZATION.json: approved archive must not be named as a draft")
    registration = auth_dir / "REGISTRATION_APPROVAL.pdf"
    if registration.is_file() and not registration.read_bytes().startswith(b"%PDF-"):
        invalid.append("REGISTRATION_APPROVAL.pdf: not a PDF")
    cyclonedx = auth_dir / "SBOM.cdx.json"
    if cyclonedx.is_file():
        try:
            sbom = json.loads(cyclonedx.read_text(encoding="utf-8"))
            if sbom.get("bomFormat") != "CycloneDX":
                invalid.append("SBOM.cdx.json: bomFormat must be CycloneDX")
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append("SBOM.cdx.json: invalid JSON")
    provenance = auth_dir / "CODE_PROVENANCE.json"
    if provenance.is_file():
        try:
            if not isinstance(json.loads(provenance.read_text(encoding="utf-8")), dict):
                invalid.append("CODE_PROVENANCE.json: top-level object required")
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append("CODE_PROVENANCE.json: invalid JSON")
    approved = not missing and not invalid and not failed_declarations
    status = {
        "schema_version": "xa.authorization-status.v1",
        "status": "approved" if approved else "incomplete",
        "distributable": approved,
        "missing_documents": missing,
        "invalid_documents_or_fields": invalid,
        "failed_declarations": failed_declarations,
        "archive_name": archive_name if approved else None,
        "human_attestation": {
            key: auth_payload.get(key)
            for key in ("attested_by", "attested_role", "attested_at_utc", "submitting_university", "authorized_submitter")
        },
        "document_sha256": {name: sha256_bytes(data) for name, data in documents},
    }
    return status, documents


def package_readme(
    mode: str,
    archive_root: str,
    presentation: dict[str, Any],
    authorization: dict[str, Any],
    technical_release: dict[str, Any],
) -> bytes:
    lines = [
        "# XA-202609 competition package",
        "",
        f"- mode: `{mode}`",
        f"- distributable: `{str(authorization.get('distributable', False)).lower()}`",
        f"- presentation included: `{str(presentation['included']).lower()}`",
        f"- presentation SHA-256: `{presentation.get('sha256') or 'missing'}`",
        f"- final model/release evidence ready: `{str(technical_release['ready_for_final']).lower()}`",
        f"- formal v4 training provenance closed: `{str(technical_release['training_provenance']['closed']).lower()}`",
        f"- external E5 portability anchor: `{technical_release['externally_anchored_evidence']['anchor']['sha256']}`",
        "- raw experiment logs are excluded except the eight exact E5 verifier-closure nine-file bundles and the SHA-locked five-file E6 development result; `misc/archive/` is always excluded",
        "- two locked historical stdout local-path strings are allowed only in the exact fresh-v1/fresh-v2 raw artifacts and are not runtime dependencies",
        "- `SBOM-LITE.json` records declared direct requirements only; the approved final gate also requires `authorization/SBOM.cdx.json`",
        "",
        "Verify this extracted tree from its parent directory:",
        "",
        "```bash",
        f"python {archive_root}/experiments/submission/verify_competition_package.py {archive_root}",
        "```",
    ]
    if technical_release.get("blockers"):
        lines.extend(["", "## Unresolved technical release gates", ""])
        lines.extend(f"- `{blocker}`" for blocker in technical_release["blockers"])
        lines.extend(
            [
                "",
                "Foundation v3 remains the development demo checkpoint. Formal v4 closes training provenance only and is still a development candidate.",
                "Formal v4 is not performance evidence; human authorization cannot promote it to a final model.",
                "E4-v2 is post-E4 replication and E5 has no accepted endpoint. E6 contains a verified development conditional negative result, not formal or performance evidence.",
                "The E5 V3/fresh-v2 anchor closes software-portability provenance only; protocol/performance remain false.",
            ]
        )
    if mode == "internal_audit_draft":
        lines.extend(
            [
                "",
                "> **INTERNAL AUDIT DRAFT — NOT AUTHORIZED FOR SUBMISSION OR REDISTRIBUTION.**",
                "> Run the verifier without `--allow-incomplete` to confirm that this draft fails closed.",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_archive(staging: Path, archive: Path, archive_root: str) -> str:
    if archive.exists():
        raise BuildError(f"refusing to overwrite archive: {archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in sorted((item for item in staging.rglob("*") if item.is_file()), key=lambda item: item.relative_to(staging).as_posix()):
                    rel = path.relative_to(staging).as_posix()
                    data = path.read_bytes()
                    info = tarfile.TarInfo(f"{archive_root}/{rel}")
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o755 if path.suffix in {".py", ".sh"} else 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
    return sha256_file(archive)


def build(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_spec()
    report_release = report_release_status(spec)
    external_evidence = externally_anchored_evidence_status(spec)
    authorization, auth_documents = validate_authorization(args.authorization_dir, spec)
    authorization_approved = authorization.get("distributable") is True
    git_info = git_provenance()
    technical_release = final_model_release_status(spec, git_info, external_evidence)
    technical_ready = technical_release.get("ready_for_final") is True
    final_ready = authorization_approved and technical_ready
    if not final_ready and not args.allow_incomplete:
        details = {
            "missing_documents": authorization.get("missing_documents", []),
            "invalid_documents_or_fields": authorization.get("invalid_documents_or_fields", []),
            "failed_declarations": authorization.get("failed_declarations", []),
            "technical_release_blockers": technical_release.get("blockers", []),
        }
        raise BuildError(
            "final staging refused by authorization gate and/or technical gate: "
            + json.dumps(details, ensure_ascii=False)
        )
    mode = "final" if final_ready else "internal_audit_draft"
    authorization_for_package = dict(authorization)
    authorization_for_package["distributable"] = final_ready
    authorization_for_package["package_gate_status"] = "ready" if final_ready else "incomplete"
    output = args.output_dir.expanduser().resolve()
    validate_generated_destination(output, "output")
    if mode == "internal_audit_draft" and "internal-audit-draft" not in output.name.lower():
        raise BuildError("incomplete output directory name must contain 'internal-audit-draft'")
    if mode == "internal_audit_draft" and "final" in output.name.lower():
        raise BuildError("incomplete output directory must not be named as final")
    if mode == "final" and "draft" in output.name.lower():
        raise BuildError("approved final output directory must not be named as a draft")
    if mode == "final" and not args.expected_presentation_sha256:
        raise BuildError("approved final staging requires --expected-presentation-sha256")
    if mode == "final" and args.omit_presentation:
        raise BuildError("approved final staging cannot omit the presentation")
    archive_name = authorization.get("archive_name") if final_ready else "XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz"
    archive_path = args.archive.expanduser().resolve() if args.archive else output.parent / archive_name
    validate_generated_destination(archive_path, "archive")
    if archive_path.name != archive_name:
        raise BuildError(
            f"archive filename must match the {'human authorization' if final_ready else 'fixed internal-draft name'}: "
            f"{archive_name}"
        )
    if archive_path.exists():
        raise BuildError(f"refusing to overwrite archive: {archive_path}")
    if output.exists():
        raise BuildError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)
    try:
        whitelist = collect_whitelist(spec)
        entries = copy_whitelisted(output, whitelist)
        presentation_release = spec.get("presentation_release", {})
        presentation_release_path = presentation_release.get("path")
        presentation_release_sha = presentation_release.get("sha256")
        presentation_candidates = spec["presentation_candidates"]
        if presentation_candidates != [presentation_release_path]:
            raise BuildError("presentation candidate/release path mismatch in staging spec")
        if not isinstance(presentation_release_sha, str) or not re.fullmatch(
            r"[0-9a-f]{64}", presentation_release_sha
        ):
            raise BuildError("presentation release SHA is missing or invalid in staging spec")
        present = [] if args.omit_presentation else [
            path for path in presentation_candidates if (REPO_ROOT / path).is_file()
        ]
        if len(present) > 1:
            raise BuildError("multiple presentation candidates are present")
        presentation = {
            "included": bool(present),
            "path": present[0] if present else None,
            "sha256": None,
            "missing_candidates": [] if present else presentation_candidates,
            "intentionally_omitted_for_pre_lock_audit": bool(args.omit_presentation),
        }
        if present:
            if not args.expected_presentation_sha256:
                raise BuildError(
                    "presentation is present but no stable --expected-presentation-sha256 was supplied; "
                    "use --omit-presentation only for an internal pre-lock audit"
                )
            if args.expected_presentation_sha256 != presentation_release_sha:
                raise BuildError(
                    "expected presentation SHA does not match authoritative staging-spec lock: "
                    f"{args.expected_presentation_sha256} != {presentation_release_sha}"
                )
            presentation_path = resolve_repo_file(present[0])
            presentation_data = presentation_path.read_bytes()
            presentation_sha = sha256_bytes(presentation_data)
            expected_presentation_sha = args.expected_presentation_sha256
            if presentation_sha != presentation_release_sha or (
                expected_presentation_sha and presentation_sha != expected_presentation_sha
            ):
                raise BuildError(
                    "presentation SHA mismatch: "
                    f"expected {presentation_release_sha}, observed {presentation_sha}"
                )
            entry = safe_write_bytes(output, present[0], presentation_data)
            entry.update(
                {
                    "kind": "repository_file",
                    "source_path": present[0],
                    "source_sha256": presentation_sha,
                }
            )
            entries.append(entry)
            presentation["sha256"] = presentation_sha
        elif mode == "final":
            raise BuildError("approved final staging requires the final presentation")
        elif args.expected_presentation_sha256:
            raise BuildError("expected presentation SHA was supplied but presentation is missing")
        evidence_entries, evidence_reports = evidence_snapshot(output, spec)
        entries.extend(evidence_entries)
        for name, data in auth_documents if final_ready else []:
            entry = safe_write_bytes(output, f"authorization/{name}", data)
            entry.update({"kind": "human_authorization_document"})
            entries.append(entry)
        sbom_entry = safe_write_bytes(output, "SBOM-LITE.json", canonical_json(build_sbom_lite()))
        sbom_entry.update({"kind": "generated_sbom_lite"})
        entries.append(sbom_entry)
        auth_entry = safe_write_bytes(
            output,
            "AUTHORIZATION_STATUS.json",
            canonical_json(authorization_for_package),
        )
        auth_entry.update({"kind": "generated_authorization_status"})
        entries.append(auth_entry)
        technical_entry = safe_write_bytes(
            output,
            "TECHNICAL_RELEASE_STATUS.json",
            canonical_json(technical_release),
        )
        technical_entry.update({"kind": "generated_technical_release_status"})
        entries.append(technical_entry)
        provenance = {
            "schema_version": "xa.package-provenance.v1",
            "competition_id": "XA-202609",
            "mode": mode,
            "git": git_info,
            "license_status": "human_attested_approved" if authorization_approved else "unresolved",
            "technical_release_ready": technical_ready,
            "source_file_count": len([entry for entry in entries if entry.get("source_path")]),
            "files": [
                {
                    key: entry[key]
                    for key in ("path", "source_path", "source_sha256", "sha256")
                    if key in entry
                }
                for entry in entries
                if entry.get("source_path")
            ],
        }
        provenance_entry = safe_write_bytes(output, "PROVENANCE.json", canonical_json(provenance))
        provenance_entry.update({"kind": "generated_provenance"})
        entries.append(provenance_entry)
        archive_root = "XA-202609_submission" if final_ready else "XA-202609_INTERNAL_AUDIT_DRAFT"
        readme_entry = safe_write_bytes(
            output,
            "README_PACKAGE.md",
            package_readme(
                mode,
                archive_root,
                presentation,
                authorization_for_package,
                technical_release,
            ),
        )
        readme_entry.update({"kind": "generated_readme"})
        entries.append(readme_entry)
        if mode == "internal_audit_draft":
            marker = (
                "# INCOMPLETE INTERNAL AUDIT DRAFT\n\n"
                "This tree is not authorized for submission or redistribution. The absence of an approved LICENSE, "
                "IP statement, code provenance, third-party notices, registration evidence, human attestation, and "
                "transitive CycloneDX SBOM remains a hard blocker. Formal v4 has a verified command, split, seed, "
                "training log/hash, checkpoint identity, and source-SHA provenance, but remains a provenance-only "
                "development candidate without accepted external performance evidence. E5 has no accepted endpoint. "
                "E6 records a development conditional negative result, but formal/performance claims remain false; "
                "declarations cannot override these evidence boundaries.\n"
            ).encode("utf-8")
            marker_entry = safe_write_bytes(output, "INCOMPLETE_INTERNAL_AUDIT_DRAFT.md", marker)
            marker_entry.update({"kind": "incomplete_marker"})
            entries.append(marker_entry)
        manifest = {
            "schema_version": "xa.competition-package-manifest.v1",
            "competition_id": "XA-202609",
            "mode": mode,
            "distributable": final_ready,
            "archive_root": archive_root,
            "presentation": presentation,
            "report_release": report_release,
            "technical_release": technical_release,
            "evidence_snapshots": evidence_reports,
            "externally_anchored_evidence": external_evidence,
            "excluded_scopes": [
                "misc/archive",
                "legacy academic submission packages",
                "large raw.jsonl/event/log artifacts except the eight exact E5 verifier-closure nine-file bundles",
                "cache and build products",
                "unapproved private metadata",
            ],
            "files": sorted(entries, key=lambda entry: entry["path"]),
        }
        manifest_data = canonical_json(manifest)
        manifest_path = output / "MANIFEST.json"
        manifest_path.write_bytes(manifest_data)
        checksum_rows = []
        for path in sorted((item for item in output.rglob("*") if item.is_file()), key=lambda item: item.relative_to(output).as_posix()):
            rel = path.relative_to(output).as_posix()
            checksum_rows.append(f"{sha256_file(path)}  {rel}")
        (output / "CHECKSUMS.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
        archive_root = manifest["archive_root"]
        archive_sha = write_archive(output, archive_path, archive_root)
        return {
            "ok": True,
            "mode": mode,
            "distributable": final_ready,
            "staging": str(output),
            "archive": str(archive_path),
            "archive_sha256": archive_sha,
            "file_count": len(list(path for path in output.rglob("*") if path.is_file())),
            "presentation_included": presentation["included"],
            "authorization_status": authorization["status"],
            "technical_release_status": technical_release["status"],
        }
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--output-dir", type=Path, required=True, help="new staging directory; never overwritten")
    command.add_argument("--archive", type=Path, help="optional archive output path; never overwritten")
    command.add_argument("--authorization-dir", type=Path, help="human-approved authorization bundle")
    command.add_argument(
        "--expected-presentation-sha256",
        type=sha256_argument,
        help="required SHA lock whenever the one presentation file is copied into staging",
    )
    command.add_argument(
        "--omit-presentation",
        action="store_true",
        help="internal pre-lock audit only: do not stat, read, or package any presentation candidate",
    )
    command.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="build an INTERNAL_AUDIT_DRAFT only; never authorizes final submission",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build(args)
    except BuildError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
