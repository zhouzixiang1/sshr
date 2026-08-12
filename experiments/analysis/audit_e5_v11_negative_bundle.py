#!/usr/bin/env python3
"""Build the immutable E5-v1.1 post-hoc negative-audit evidence bundle.

This is an evidence-only operation over the already failed 90-row result.  It
does not run evaluate, refit a model, change any endpoint, or modify the source
bundle.  The independent verifier is the authority: this producer merely
serializes its source-grounded reconstruction into a non-overwriting nine-file
artifact bundle.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
override = os.environ.get("XA_E5_PROJECT_ROOT")
if override and Path(override).resolve() != PROJECT_ROOT:
    raise RuntimeError("XA_E5_PROJECT_ROOT does not match the audit source tree")
os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis import verify_e5_v11_negative_audit_bundle as independent  # noqa: E402
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_text  # noqa: E402


DEFAULT_SOURCE = (
    PROJECT_ROOT / "results" / "xa202609" / independent.SOURCE_RUN_ID
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-negative-audit-v1-s950000"
)
DEFAULT_PORTABLE_OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-portable-negative-audit-v2-s950000"
)
DEFAULT_PORTABLE_V3_OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-portable-negative-audit-v3-s950000"
)
DEFAULT_FRESH_VALIDATION_OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-portable-fresh-validation-v1-s960000"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_record(
    run_id: str,
    created_at: str,
    recomputed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": independent.RUN_SCHEMA,
        "track": independent.TRACK,
        "run_id": run_id,
        "phase": "posthoc_negative_audit",
        "status": "complete_negative_audit",
        "created_at_utc": created_at,
        "audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "source_bundle": recomputed["source_binding"],
        "normalization_contract": independent.normalization_contract(),
        "normalization_contract_sha256": independent.NORMALIZATION_CONTRACT_SHA256,
        "producer_sources": independent._producer_source_binding(),
        "counts": recomputed["counts"],
        "expected_artifacts": sorted(independent.EXPECTED_FILES),
        "command_contract": {
            "operation": "read_only_posthoc_negative_audit",
            "new_evaluate_started": False,
            "source_bundle_mutated": False,
            "model_refit": False,
            "endpoint_reclassified": False,
        },
    }


def _events(run_id: str, created_at: str, recomputed: dict[str, Any]) -> list[dict[str, Any]]:
    common = {"run_id": run_id, "created_at_utc": created_at}
    return [
        {"event": "negative_audit_started", **common},
        {
            "event": "original_bundle_authenticated",
            **common,
            "source_run_id": independent.SOURCE_RUN_ID,
            "source_snapshot_sha256": independent.SOURCE_SNAPSHOT_SHA256,
        },
        {
            "event": "ninety_rows_reconstructed",
            **common,
            "search_plan_scheduler": recomputed["counts"][
                "search_plan_scheduler_reconstructed"
            ],
            "logical_semantics_native_endpoint": recomputed["counts"][
                "logical_semantics_native_endpoint_reconstructed"
            ],
        },
        {
            "event": "negative_audit_completed",
            **common,
            "audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        },
    ]


def _portable_run_record(
    run_id: str,
    created_at: str,
    recomputed: dict[str, Any],
) -> dict[str, Any]:
    producer_runtime = independent.runtime_build_fingerprint()
    if producer_runtime != independent.REFERENCE_RUNTIME_BUILD:
        raise RuntimeError(
            "the canonical portable-audit bundle must be produced by the recorded "
            "reference build; non-reference runtimes remain valid independent verifiers"
        )
    return {
        "schema_version": independent.PORTABLE_RUN_SCHEMA,
        "track": independent.PORTABLE_TRACK,
        "run_id": run_id,
        "phase": "portable_posthoc_negative_audit",
        "status": "complete_portable_negative_audit",
        "created_at_utc": created_at,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "source_bundle": recomputed["source_binding"],
        "portable_normalization_contract": independent.portable_normalization_contract(),
        "portable_normalization_contract_sha256": (
            independent.PORTABLE_NORMALIZATION_CONTRACT_SHA256
        ),
        "reference_runtime_build": independent.REFERENCE_RUNTIME_BUILD,
        "producer_runtime_build": producer_runtime,
        "runtime_build_may_differ_from_reference_during_verification": True,
        "stored_historical_floats_resigned_by_replay": False,
        "producer_sources": independent._producer_source_binding(),
        "counts": recomputed["counts"],
        "expected_artifacts": sorted(independent.EXPECTED_FILES),
        "command_contract": {
            "operation": "read_only_cross_build_portable_posthoc_negative_audit",
            "new_evaluate_started": False,
            "source_bundle_mutated": False,
            "historical_floats_resigned": False,
            "model_refit": False,
            "endpoint_reclassified": False,
        },
    }


def _portable_events(
    run_id: str, created_at: str, recomputed: dict[str, Any]
) -> list[dict[str, Any]]:
    common = {"run_id": run_id, "created_at_utc": created_at}
    return [
        {"event": "portable_negative_audit_started", **common},
        {
            "event": "original_bundle_authenticated",
            **common,
            "source_run_id": independent.SOURCE_RUN_ID,
            "source_snapshot_sha256": independent.SOURCE_SNAPSHOT_SHA256,
        },
        {
            "event": "ninety_rows_portably_reconstructed",
            **common,
            "portable_search_plan_scheduler": recomputed["counts"][
                "portable_search_plan_scheduler_reconstructed"
            ],
            "logical_semantics_native_endpoint": recomputed["counts"][
                "logical_semantics_native_endpoint_reconstructed"
            ],
        },
        {
            "event": "portable_negative_audit_completed",
            **common,
            "portable_audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        },
    ]


def _portable_v3_run_record(
    run_id: str,
    created_at: str,
    recomputed: dict[str, Any],
) -> dict[str, Any]:
    producer_runtime = independent.runtime_build_fingerprint_v2()
    if not independent.runtime_matches_reference_v2(
        producer_runtime, independent.REFERENCE_RUNTIME_BUILD_V2
    ):
        raise RuntimeError(
            "the canonical portable-audit v3 bundle must be produced by the "
            "recorded full reference runtime; other runtimes may verify it"
        )
    return {
        "schema_version": independent.PORTABLE_V3_RUN_SCHEMA,
        "track": independent.PORTABLE_V3_TRACK,
        "run_id": run_id,
        "phase": "portable_posthoc_negative_audit_v3",
        "status": "complete_portable_negative_audit_v3",
        "created_at_utc": created_at,
        "portable_audit_evidence_ok": True,
        "audit_completed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "performance_claim_supported": False,
        "source_bundle": recomputed["source_binding"],
        "portable_normalization_contract": (
            independent.portable_normalization_contract_v3()
        ),
        "portable_normalization_contract_sha256": (
            independent.PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256
        ),
        "reference_runtime_build": independent.REFERENCE_RUNTIME_BUILD_V2,
        "producer_runtime_build": producer_runtime,
        "reference_runtime_frozen_subset_sha256": independent._payload_sha(
            independent.runtime_build_frozen_subset_v2(
                independent.REFERENCE_RUNTIME_BUILD_V2
            )
        ),
        "runtime_build_may_differ_from_reference_during_verification": True,
        "stored_historical_floats_resigned_by_replay": False,
        "producer_sources": independent._producer_source_binding(),
        "counts": recomputed["counts"],
        "expected_artifacts": sorted(independent.EXPECTED_FILES),
        "command_contract": {
            "operation": "read_only_cross_build_portable_posthoc_negative_audit_v3",
            "new_evaluate_started": False,
            "source_bundle_mutated": False,
            "historical_floats_resigned": False,
            "model_refit": False,
            "endpoint_reclassified": False,
        },
    }


def _portable_v3_events(
    run_id: str, created_at: str, recomputed: dict[str, Any]
) -> list[dict[str, Any]]:
    common = {"run_id": run_id, "created_at_utc": created_at}
    return [
        {"event": "portable_negative_audit_v3_started", **common},
        {
            "event": "original_bundle_authenticated",
            **common,
            "source_run_id": independent.SOURCE_RUN_ID,
            "source_snapshot_sha256": independent.SOURCE_SNAPSHOT_SHA256,
        },
        {
            "event": "ninety_rows_portably_reconstructed_v3",
            **common,
            "portable_search_plan_scheduler": recomputed["counts"][
                "portable_search_plan_scheduler_reconstructed"
            ],
            "logical_semantics_native_endpoint": recomputed["counts"][
                "logical_semantics_native_endpoint_reconstructed"
            ],
        },
        {
            "event": "portable_negative_audit_v3_completed",
            **common,
            "portable_audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        },
    ]


def build_negative_audit_bundle(source_bundle: Path, output: Path) -> Path:
    source = Path(source_bundle).resolve()
    destination = Path(output).resolve()
    if destination.exists():
        raise FileExistsError(f"negative-audit bundle already exists: {destination}")
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError("audit output cannot be inside the immutable source bundle")
    recomputed = independent.recompute_source_audit(source)
    run_id = destination.name
    created_at = _utc_now()
    run = _run_record(run_id, created_at, recomputed)
    summary = independent.expected_summary(run_id, recomputed)
    declared = independent.expected_declared_verifier(run_id)
    events = _events(run_id, created_at, recomputed)

    writer = ArtifactBundleWriter(destination)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(row) + "\n" for row in recomputed["audit_rows"]),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", declared)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text(
        "stdout",
        "stdout.log",
        "Post-hoc negative audit completed; no evaluate run was started and no endpoint was accepted.\n",
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(
        bundle_metadata={
            "run_id": run_id,
            "track": independent.TRACK,
            "audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    )
    generic = verify_bundle(destination, required_roles=independent.REQUIRED_ROLES)
    if not generic.ok:
        raise RuntimeError(f"generated negative-audit bundle is invalid: {generic.errors}")
    return destination


def build_portable_audit_bundle(source_bundle: Path, output: Path) -> Path:
    """Build a non-overwriting v2 bundle from the immutable v1.1 source."""

    source = Path(source_bundle).resolve()
    destination = Path(output).resolve()
    if destination.exists():
        raise FileExistsError(f"portable negative-audit bundle already exists: {destination}")
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError("portable audit output cannot be inside the immutable source bundle")
    recomputed = independent.recompute_source_portable_audit(source)
    run_id = destination.name
    created_at = _utc_now()
    run = _portable_run_record(run_id, created_at, recomputed)
    summary = independent.expected_portable_summary(run_id, recomputed)
    declared = independent.expected_portable_declared_verifier(run_id)
    events = _portable_events(run_id, created_at, recomputed)

    writer = ArtifactBundleWriter(destination)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(row) + "\n" for row in recomputed["audit_rows"]),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", declared)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text(
        "stdout",
        "stdout.log",
        (
            "Portable post-hoc negative audit completed; stored historical floats were "
            "not re-signed, no evaluate run was started, and no endpoint was accepted.\n"
        ),
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(
        bundle_metadata={
            "run_id": run_id,
            "track": independent.PORTABLE_TRACK,
            "portable_audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    )
    generic = verify_bundle(destination, required_roles=independent.REQUIRED_ROLES)
    if not generic.ok:
        raise RuntimeError(
            f"generated portable negative-audit bundle is invalid: {generic.errors}"
        )
    independent_report = independent.verify_portable_audit_bundle(destination)
    if not independent_report.get("ok"):
        raise RuntimeError(
            "generated portable negative-audit bundle failed independent verification: "
            f"{independent_report.get('errors', [])}"
        )
    return destination


def build_portable_audit_bundle_v3(source_bundle: Path, output: Path) -> Path:
    """Build a non-overwriting v3 bundle from the immutable v1.1 source."""

    source = Path(source_bundle).resolve()
    destination = Path(output).resolve()
    if destination.exists():
        raise FileExistsError(
            f"portable negative-audit v3 bundle already exists: {destination}"
        )
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError(
            "portable audit v3 output cannot be inside the immutable source bundle"
        )
    recomputed = independent.recompute_source_portable_audit_v3(source)
    run_id = destination.name
    created_at = _utc_now()
    run = _portable_v3_run_record(run_id, created_at, recomputed)
    summary = independent.expected_portable_summary_v3(run_id, recomputed)
    declared = independent.expected_portable_declared_verifier_v3(run_id)
    events = _portable_v3_events(run_id, created_at, recomputed)

    writer = ArtifactBundleWriter(destination)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(
            canonical_json_text(row) + "\n" for row in recomputed["audit_rows"]
        ),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", declared)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text(
        "stdout",
        "stdout.log",
        (
            "Portable post-hoc negative audit v3 completed with nested feedback SHA "
            "binding; stored historical floats were not re-signed, no evaluate run "
            "was started, and no endpoint was accepted.\n"
        ),
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(
        bundle_metadata={
            "run_id": run_id,
            "track": independent.PORTABLE_V3_TRACK,
            "portable_audit_evidence_ok": True,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    )
    generic = verify_bundle(destination, required_roles=independent.REQUIRED_ROLES)
    if not generic.ok:
        raise RuntimeError(
            f"generated portable v3 bundle is invalid: {generic.errors}"
        )
    independent_report = independent.verify_portable_audit_bundle_v3(destination)
    if not independent_report.get("ok"):
        raise RuntimeError(
            "generated portable v3 bundle failed independent verification: "
            f"{independent_report.get('errors', [])}"
        )
    return destination


def _stream_record(text: str) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    payload = normalized.encode("utf-8")
    return {
        "text": normalized,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _run_fresh_validation_command(
    ordinal: int, command_id: str, normalized_argv: tuple[str, ...]
) -> dict[str, Any]:
    actual_argv = [sys.executable, *normalized_argv[1:]]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.perf_counter()
    completed = subprocess.run(
        actual_argv,
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    duration = time.perf_counter() - started
    return {
        "schema_version": independent.FRESH_VALIDATION_ROW_SCHEMA,
        "ordinal": ordinal,
        "command_id": command_id,
        "argv": list(normalized_argv),
        "exit_code": int(completed.returncode),
        "duration_seconds": duration,
        "stdout": _stream_record(completed.stdout),
        "stderr": _stream_record(completed.stderr),
        "success": completed.returncode == 0,
    }


def build_fresh_validation_bundle(
    scientific_bundle: Path, output: Path
) -> Path:
    """Run and serialize fresh-venv software validation separately from science."""

    destination = Path(output).resolve()
    if destination.exists():
        raise FileExistsError(f"fresh-validation bundle already exists: {destination}")
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("fresh-validation production requires an active venv")
    fixed_scientific = (
        PROJECT_ROOT
        / "results"
        / "xa202609"
        / independent.PORTABLE_V3_RUN_ID
    ).resolve()
    if Path(scientific_bundle).resolve() != fixed_scientific:
        raise ValueError("fresh validation must bind the authoritative fixed v3 bundle")
    scientific_before = independent._directory_snapshot_binding(fixed_scientific)
    source_root = PROJECT_ROOT / "results" / "xa202609" / independent.SOURCE_RUN_ID
    source_before = independent._snapshot_records(source_root)
    initial_report = independent.verify_portable_audit_bundle_v3(fixed_scientific)
    if not initial_report.get("ok"):
        raise RuntimeError("v3 scientific bundle failed verification before validation")

    fresh_runtime = independent.runtime_build_fingerprint_v2()
    if independent.runtime_matches_reference_v2(
        fresh_runtime, independent.REFERENCE_RUNTIME_BUILD_V2
    ):
        raise RuntimeError(
            "fresh-validation runtime must differ from the canonical reference subset"
        )
    rows = [
        _run_fresh_validation_command(ordinal, command_id, argv)
        for ordinal, (command_id, argv) in enumerate(
            independent.FRESH_VALIDATION_COMMAND_CONTRACT
        )
    ]
    failed = [row["command_id"] for row in rows if not row["success"]]
    if failed:
        raise RuntimeError(f"fresh-validation commands failed: {failed}")
    if independent._snapshot_records(source_root) != source_before:
        raise RuntimeError("immutable 90-row source changed during fresh validation")
    scientific_after = independent._directory_snapshot_binding(fixed_scientific)
    if scientific_after != scientific_before:
        raise RuntimeError("v3 scientific bundle changed during fresh validation")

    requirements_path = PROJECT_ROOT / "environment" / "requirements" / "dev.txt"
    requirements_binding = {
        "path": "environment/requirements/dev.txt",
        "sha256": independent.sha256_file(requirements_path),
        "bytes": requirements_path.stat().st_size,
    }
    run_id = destination.name
    created_at = _utc_now()
    command_contract = [
        {"command_id": command_id, "argv": list(argv)}
        for command_id, argv in independent.FRESH_VALIDATION_COMMAND_CONTRACT
    ]
    run = {
        "schema_version": independent.FRESH_VALIDATION_RUN_SCHEMA,
        "track": independent.FRESH_VALIDATION_TRACK,
        "run_id": run_id,
        "status": "complete_fresh_validation",
        "created_at_utc": created_at,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "requirements": requirements_binding,
        "scientific_bundle": scientific_before,
        "fresh_runtime_build": fresh_runtime,
        "fresh_runtime_matches_reference": False,
        "producer_sources": independent._producer_source_binding(),
        "command_contract": command_contract,
        "expected_artifacts": sorted(independent.EXPECTED_FILES),
    }
    summary = independent.expected_fresh_validation_summary(
        run_id,
        rows,
        requirements_binding=requirements_binding,
        scientific_bundle_binding=scientific_before,
        fresh_runtime_build=fresh_runtime,
    )
    required_success = (
        summary["successful_command_count"] == len(command_contract)
        and summary["required_pins"] == summary["installed_required_pins"]
        and summary["pip_check_ok"] is True
        and summary["legacy_smoke_ok"] is True
        and summary["default_clean_install_ok"] is True
        and summary["portable_v3_verifier_ok"] is True
    )
    if not required_success:
        raise RuntimeError("fresh-validation command semantics did not pass")
    declared = independent.expected_fresh_validation_declared_verifier(run_id)
    events = [
        {"event": "fresh_validation_started", "run_id": run_id, "created_at_utc": created_at},
        {
            "event": "portable_v3_scientific_bundle_bound",
            "run_id": run_id,
            "created_at_utc": created_at,
            "scientific_run_id": independent.PORTABLE_V3_RUN_ID,
            "scientific_snapshot_sha256": scientific_before["snapshot_sha256"],
        },
        {
            "event": "fresh_validation_completed",
            "run_id": run_id,
            "created_at_utc": created_at,
            "successful_commands": len(rows),
            "software_validation_ok": True,
        },
    ]

    writer = ArtifactBundleWriter(destination)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(row) + "\n" for row in rows),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", declared)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text(
        "stdout",
        "stdout.log",
        (
            "Fresh-validation command evidence authenticated: 7/7 historical "
            "commands exited 0; the v3 scientific bundle was independently "
            "recomputed.\n"
        ),
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(
        bundle_metadata={
            "run_id": run_id,
            "track": independent.FRESH_VALIDATION_TRACK,
            "software_validation_ok": True,
            "scientific_evidence": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    )
    report = independent.verify_fresh_validation_bundle(destination)
    if not report.get("ok"):
        raise RuntimeError(
            "generated fresh-validation bundle failed independent verification: "
            f"{report.get('errors', [])}"
        )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bundle", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--scientific-bundle",
        type=Path,
        default=(
            PROJECT_ROOT
            / "results"
            / "xa202609"
            / independent.PORTABLE_V3_RUN_ID
        ),
    )
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--portable-v2",
        action="store_true",
        help="build a historical-schema v2 probe (formal v2 is immutable)",
    )
    mode.add_argument(
        "--portable-v3",
        action="store_true",
        help="build the fail-closed cross-build portable v3 audit bundle",
    )
    mode.add_argument(
        "--fresh-validation",
        action="store_true",
        help="run and build separate fresh-venv software-validation evidence",
    )
    args = parser.parse_args()
    if args.fresh_validation:
        destination = args.output or DEFAULT_FRESH_VALIDATION_OUTPUT
        output = build_fresh_validation_bundle(args.scientific_bundle, destination)
    elif args.portable_v3:
        destination = args.output or DEFAULT_PORTABLE_V3_OUTPUT
        output = build_portable_audit_bundle_v3(args.source_bundle, destination)
    elif args.portable_v2:
        destination = args.output or DEFAULT_PORTABLE_OUTPUT
        output = build_portable_audit_bundle(args.source_bundle, destination)
    else:
        destination = args.output or DEFAULT_OUTPUT
        output = build_negative_audit_bundle(args.source_bundle, destination)
    print(
        json.dumps(
            {
                "bundle": str(output),
                "audit_evidence_ok": not (
                    args.portable_v2 or args.portable_v3 or args.fresh_validation
                ),
                "portable_audit_evidence_ok": bool(
                    args.portable_v2 or args.portable_v3
                ),
                "software_validation_ok": bool(args.fresh_validation),
                "scientific_evidence": not args.fresh_validation,
                "protocol_acceptance": False,
                "experiment_completed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
