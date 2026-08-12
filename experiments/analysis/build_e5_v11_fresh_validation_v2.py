#!/usr/bin/env python3
"""Create an empty CPython 3.11 venv and anchored E5 fresh-validation v2 evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent
override = os.environ.get("XA_E5_PROJECT_ROOT")
if override and Path(override).resolve() != PROJECT_ROOT:
    raise RuntimeError("XA_E5_PROJECT_ROOT does not match the validation source tree")
os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis import verify_e5_v11_fresh_validation_v2 as independent  # noqa: E402
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle  # noqa: E402
from src.contracts.codec import canonical_json_bytes, canonical_json_text  # noqa: E402


DEFAULT_OUTPUT = (
    PROJECT_ROOT / "results" / "xa202609" / independent.RUN_ID
)
DEFAULT_ANCHOR = PROJECT_ROOT / independent.ANCHOR_RELATIVE_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stream_record(text: str) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    payload = normalized.encode("utf-8")
    return {
        "text": normalized,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
    )
    return environment


def _run_command(
    *,
    ordinal: int,
    contract: Mapping[str, Any],
    executed_argv: list[str],
    install_report_path: Path | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        executed_argv,
        cwd=PROJECT_ROOT,
        env=_clean_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    duration = time.perf_counter() - started
    row = {
        "schema_version": independent.ROW_SCHEMA,
        "ordinal": ordinal,
        "command_id": contract["command_id"],
        "executor": contract["executor"],
        "normalized_argv": list(contract["argv"]),
        "executed_argv": executed_argv,
        "exit_code": int(completed.returncode),
        "duration_seconds": duration,
        "stdout": _stream_record(completed.stdout),
        "stderr": _stream_record(completed.stderr),
        "success": completed.returncode == 0,
    }
    if install_report_path is not None:
        if install_report_path.is_file():
            row["install_report"] = _stream_record(
                install_report_path.read_text(encoding="utf-8")
            )
        else:
            row["install_report"] = _stream_record("")
    return row


def _python_binding(path: Path) -> dict[str, Any]:
    path = path.resolve()
    return {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": independent.sha256_file(path),
        },
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def _executed_argv(
    contract: Mapping[str, Any], paths: Mapping[str, str]
) -> list[str]:
    replacements = {
        "host-python": paths["host_python"],
        "fresh-python": paths["fresh_python"],
        "<fresh-venv>": paths["venv_path"],
        "<pip-install-report>": paths["pip_install_report"],
    }
    return [replacements.get(value, value) for value in contract["argv"]]


def _write_bundle(
    destination: Path,
    *,
    run: Mapping[str, Any],
    rows: list[dict[str, Any]],
    summary: Mapping[str, Any],
    declared: Mapping[str, Any],
    events: list[dict[str, Any]],
) -> None:
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
            "Externally anchored fresh-validation v2 completed: 9/9 historical "
            "commands exited 0; commands are authenticated, not rerun by the bundle "
            "verifier; no scientific endpoint was accepted.\n"
        ),
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(
        bundle_metadata={
            "run_id": independent.RUN_ID,
            "track": independent.TRACK,
            "software_validation_ok": True,
            "external_anchor_required": True,
            "scientific_evidence": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    )


def build_fresh_validation_v2(
    output: Path,
    anchor_path: Path,
    *,
    temporary_parent: Path | None = None,
) -> dict[str, Any]:
    destination = Path(output).resolve()
    anchor_path = Path(anchor_path).resolve()
    if destination.exists():
        raise FileExistsError(f"fresh-validation v2 bundle already exists: {destination}")
    if anchor_path.exists():
        raise FileExistsError(f"fresh-validation v2 anchor already exists: {anchor_path}")
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 11):
        raise RuntimeError("host must be CPython 3.11")
    if sys.prefix != sys.base_prefix:
        raise RuntimeError("builder must run from a host interpreter, not an active venv")

    source_before = independent.source_bindings()
    closure_before = independent.requirements_closure()
    if closure_before["pins"] != independent.EXPECTED_REQUIRED_PINS:
        raise RuntimeError("requirements closure does not equal the exact expected pins")
    predecessors_before = independent.predecessor_snapshots()
    if predecessors_before != independent.IMMUTABLE_PREDECESSOR_SNAPSHOTS:
        raise RuntimeError("an immutable predecessor bundle changed before validation")
    science_root = (
        PROJECT_ROOT / "results" / "xa202609" / independent.SCIENCE_RUN_ID
    )
    science_before = independent.directory_snapshot_binding(science_root)
    science_report = independent.science.verify_portable_audit_bundle_v3(science_root)
    if not science_report.get("ok"):
        raise RuntimeError("v3 scientific bundle failed before fresh validation")

    if temporary_parent is None:
        temporary_root = Path(
            tempfile.mkdtemp(prefix="xa-e5-fresh-v2-")
        ).resolve()
    else:
        parent = Path(temporary_parent).resolve()
        parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(prefix="xa-e5-fresh-v2-", dir=parent)
        ).resolve()
    # The verifier intentionally accepts only the platform temporary directory.
    if temporary_root.parent != Path(tempfile.gettempdir()).resolve():
        raise RuntimeError("temporary parent must be the platform temporary directory")
    venv_path = temporary_root / "venv"
    fresh_python = venv_path / "bin" / "python"
    pip_report = temporary_root / "pip-install-report.json"
    path_context = {
        "temporary_root": str(temporary_root),
        "venv_path": str(venv_path),
        "fresh_python": str(fresh_python),
        "pip_install_report": str(pip_report),
        "host_python": str(Path(sys.executable).resolve()),
    }

    rows: list[dict[str, Any]] = []
    for ordinal, contract in enumerate(independent.COMMAND_CONTRACT):
        actual = _executed_argv(contract, path_context)
        row = _run_command(
            ordinal=ordinal,
            contract=contract,
            executed_argv=actual,
            install_report_path=(
                pip_report if contract["command_id"] == "pip_install" else None
            ),
        )
        rows.append(row)
        if not row["success"]:
            raise RuntimeError(
                f"fresh-validation command failed: {contract['command_id']} "
                f"(temporary evidence retained at {temporary_root})"
            )
        if contract["command_id"] == "venv_create" and not fresh_python.is_file():
            raise RuntimeError("python -m venv did not create the fresh interpreter")

    by_id = {row["command_id"]: row for row in rows}
    v3_report = json.loads(by_id["portable_v3_verifier"]["stdout"]["text"])
    fresh_runtime = v3_report.get("runtime_build")
    if not independent.science.runtime_build_fingerprint_valid_v2(fresh_runtime):
        raise RuntimeError("fresh V3 verifier did not report a valid runtime fingerprint")
    if independent.science.runtime_matches_reference_v2(
        fresh_runtime, independent.science.REFERENCE_RUNTIME_BUILD_V2
    ):
        raise RuntimeError("new venv unexpectedly matches the reference runtime")

    if independent.source_bindings() != source_before:
        raise RuntimeError("source files changed during fresh validation")
    if independent.requirements_closure() != closure_before:
        raise RuntimeError("requirements closure changed during fresh validation")
    if independent.predecessor_snapshots() != predecessors_before:
        raise RuntimeError("a predecessor bundle changed during fresh validation")
    if independent.directory_snapshot_binding(science_root) != science_before:
        raise RuntimeError("v3 scientific bundle changed during fresh validation")

    created_at = _utc_now()
    run = {
        "schema_version": independent.RUN_SCHEMA,
        "track": independent.TRACK,
        "run_id": independent.RUN_ID,
        "status": "complete_fresh_validation_v2",
        "created_at_utc": created_at,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "host_python": _python_binding(Path(sys.executable)),
        "path_context": path_context,
        "requirements_closure": closure_before,
        "scientific_v3_bundle": science_before,
        "source_files": source_before,
        "fresh_runtime_build": fresh_runtime,
        "command_contract": list(independent.COMMAND_CONTRACT),
        "expected_artifacts": sorted(independent.EXPECTED_FILES),
    }
    summary = independent.expected_summary_for_run(
        independent.RUN_ID,
        rows,
        run=run,
        closure=closure_before,
        science_binding=science_before,
        fresh_runtime=fresh_runtime,
    )
    declared = independent.expected_declared_verifier(independent.RUN_ID)
    events = [
        {
            "event": "fresh_validation_v2_started",
            "run_id": independent.RUN_ID,
            "created_at_utc": created_at,
        },
        {
            "event": "fresh_venv_created",
            "run_id": independent.RUN_ID,
            "created_at_utc": created_at,
            "venv_create_exit_code": 0,
        },
        {
            "event": "scientific_v3_bound",
            "run_id": independent.RUN_ID,
            "created_at_utc": created_at,
            "scientific_run_id": independent.SCIENCE_RUN_ID,
            "scientific_snapshot_sha256": science_before["snapshot_sha256"],
        },
        {
            "event": "fresh_validation_v2_completed",
            "run_id": independent.RUN_ID,
            "created_at_utc": created_at,
            "successful_commands": len(rows),
            "software_validation_ok": True,
        },
    ]
    _write_bundle(
        destination,
        run=run,
        rows=rows,
        summary=summary,
        declared=declared,
        events=events,
    )
    generic = verify_bundle(destination, required_roles=independent.REQUIRED_ROLES)
    if not generic.ok:
        raise RuntimeError(f"generated fresh-v2 bundle is invalid: {generic.errors}")

    bundle_binding = independent.directory_snapshot_binding(destination)
    anchor = {
        "schema_version": independent.ANCHOR_SCHEMA,
        "track": independent.TRACK,
        "run_id": independent.RUN_ID,
        "created_at_utc": created_at,
        "fresh_v2_bundle": bundle_binding,
        "scientific_v3_bundle": science_before,
        "requirements_closure": closure_before,
        "source_files": source_before,
        "predecessor_snapshots": predecessors_before,
        "trust_boundary": {
            "bundle_local_checksums_prevent_coordinated_resigning": False,
            "external_anchor_requires_submission_manifest_or_git_protection": True,
            "historical_commands_rerun_by_verifier": False,
        },
    }
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    with anchor_path.open("xb") as stream:
        stream.write(canonical_json_bytes(anchor))

    anchor_sha256 = independent.sha256_file(anchor_path)
    report = independent.verify_fresh_validation_v2(
        destination, anchor_path, anchor_sha256
    )
    if not report.get("ok"):
        raise RuntimeError(
            "generated fresh-validation v2 failed independent verification: "
            f"{report.get('errors', [])}"
        )
    return {
        "bundle": str(destination),
        "bundle_snapshot_sha256": bundle_binding["snapshot_sha256"],
        "anchor": str(anchor_path),
        "anchor_sha256": anchor_sha256,
        "temporary_root": str(temporary_root),
        "venv_path": str(venv_path),
        "venv_retained": True,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR)
    args = parser.parse_args()
    result = build_fresh_validation_v2(args.output, args.anchor)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
