from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from analysis import verify_e5_v11_fresh_validation_v2 as verifier
from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle
from src.contracts.codec import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _stream(text: str) -> dict[str, object]:
    payload = text.encode("utf-8")
    return {
        "text": text,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _fake_runtime() -> dict[str, object]:
    runtime = copy.deepcopy(verifier.science.REFERENCE_RUNTIME_BUILD_V2)
    runtime["python"]["executable"]["sha256"] = "0" * 64
    assert verifier.science.runtime_build_fingerprint_valid_v2(runtime)
    assert not verifier.science.runtime_matches_reference_v2(
        runtime, verifier.science.REFERENCE_RUNTIME_BUILD_V2
    )
    return runtime


def _fake_install_report() -> str:
    install = []
    for index, (name, version) in enumerate(
        sorted(verifier.EXPECTED_REQUIRED_PINS.items())
    ):
        install.append(
            {
                "download_info": {
                    "url": f"https://example.invalid/{name}-{version}.whl",
                    "archive_info": {"hashes": {"sha256": f"{index + 1:064x}"}},
                },
                "requested": True,
                "metadata": {"name": name, "version": version},
            }
        )
    return json.dumps(
        {"version": "1", "pip_version": "99.0", "install": install},
        ensure_ascii=False,
        sort_keys=True,
    )


def _path_context() -> dict[str, str]:
    temporary_root = (
        Path(tempfile.gettempdir()).resolve()
        / f"xa-e5-fresh-v2-synthetic-{os.getpid()}"
    )
    venv = temporary_root / "venv"
    return {
        "temporary_root": str(temporary_root),
        "venv_path": str(venv),
        "fresh_python": str(venv / "bin" / "python"),
        "pip_install_report": str(temporary_root / "pip-install-report.json"),
        "host_python": str(Path(sys.executable).resolve()),
    }


def _actual_argv(contract, paths):
    replacements = {
        "host-python": paths["host_python"],
        "fresh-python": paths["fresh_python"],
        "<fresh-venv>": paths["venv_path"],
        "<pip-install-report>": paths["pip_install_report"],
    }
    return [replacements.get(item, item) for item in contract["argv"]]


def _synthetic_bundle(parent: Path):
    bundle = parent / verifier.RUN_ID
    anchor_path = parent / "anchor.json"
    paths = _path_context()
    runtime = _fake_runtime()
    v3_report = {
        "schema_version": verifier.science.PORTABLE_V3_REPORT_SCHEMA,
        "ok": True,
        "checks": {f"check_{index}": True for index in range(20)},
        "runtime_build": runtime,
        "runtime_matches_reference": False,
        "runtime_build_differences": verifier.science.runtime_build_differences_v2(
            runtime, verifier.science.REFERENCE_RUNTIME_BUILD_V2
        ),
        "protocol_acceptance": False,
        "experiment_completed": False,
    }
    outputs = {
        "venv_create": "",
        "pip_version": "pip 99.0 from <fresh-venv>/pip (python 3.11)\n",
        "pip_install": "Successfully installed exact test packages\n",
        "pip_check": "No broken requirements found.\n",
        "targeted_e5": "50 passed in 1.00s\n",
        "full_pytest": "400 passed in 2.00s\n",
        "legacy_smoke": "smoke ok\n",
        "default_clean_install": json.dumps({"ok": True}, sort_keys=True) + "\n",
        "portable_v3_verifier": json.dumps(v3_report, sort_keys=True) + "\n",
    }
    rows = []
    for ordinal, contract in enumerate(verifier.COMMAND_CONTRACT):
        row = {
            "schema_version": verifier.ROW_SCHEMA,
            "ordinal": ordinal,
            "command_id": contract["command_id"],
            "executor": contract["executor"],
            "normalized_argv": list(contract["argv"]),
            "executed_argv": _actual_argv(contract, paths),
            "exit_code": 0,
            "duration_seconds": 0.1 + ordinal * 0.01,
            "stdout": _stream(outputs[contract["command_id"]]),
            "stderr": _stream(""),
            "success": True,
        }
        if contract["command_id"] == "pip_install":
            row["install_report"] = _stream(_fake_install_report())
        rows.append(row)

    closure = verifier.requirements_closure()
    science_binding = verifier.directory_snapshot_binding(
        PROJECT_ROOT / "results" / "xa202609" / verifier.SCIENCE_RUN_ID
    )
    sources = verifier.source_bindings()
    run = {
        "schema_version": verifier.RUN_SCHEMA,
        "track": verifier.TRACK,
        "run_id": verifier.RUN_ID,
        "status": "complete_fresh_validation_v2",
        "created_at_utc": "2026-08-12T00:00:00Z",
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "host_python": {"test": True},
        "path_context": paths,
        "requirements_closure": closure,
        "scientific_v3_bundle": science_binding,
        "source_files": sources,
        "fresh_runtime_build": runtime,
        "command_contract": list(verifier.COMMAND_CONTRACT),
        "expected_artifacts": sorted(verifier.EXPECTED_FILES),
    }
    summary = verifier.expected_summary_for_run(
        verifier.RUN_ID,
        rows,
        run=run,
        closure=closure,
        science_binding=science_binding,
        fresh_runtime=runtime,
    )
    declared = verifier.expected_declared_verifier(verifier.RUN_ID)
    events = [
        {"event": "fresh_validation_v2_started", "run_id": verifier.RUN_ID},
        {"event": "fresh_venv_created", "run_id": verifier.RUN_ID},
        {"event": "scientific_v3_bound", "run_id": verifier.RUN_ID},
        {"event": "fresh_validation_v2_completed", "run_id": verifier.RUN_ID},
    ]
    writer = ArtifactBundleWriter(bundle)
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
    writer.finalize(bundle_metadata={"run_id": verifier.RUN_ID})
    anchor = {
        "schema_version": verifier.ANCHOR_SCHEMA,
        "track": verifier.TRACK,
        "run_id": verifier.RUN_ID,
        "created_at_utc": "2026-08-12T00:00:00Z",
        "fresh_v2_bundle": verifier.directory_snapshot_binding(bundle),
        "scientific_v3_bundle": science_binding,
        "requirements_closure": closure,
        "source_files": sources,
        "predecessor_snapshots": verifier.predecessor_snapshots(),
        "trust_boundary": {
            "bundle_local_checksums_prevent_coordinated_resigning": False,
            "external_anchor_requires_submission_manifest_or_git_protection": True,
            "historical_commands_rerun_by_verifier": False,
        },
    }
    anchor_path.write_bytes(canonical_json_bytes(anchor))
    return bundle, anchor_path


def _resign_bundle(bundle: Path) -> None:
    manifest_path = bundle / "artifacts.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["artifacts"]:
        path = bundle / record["relative_path"]
        record["size_bytes"] = path.stat().st_size
        record["sha256"] = sha256_file(path)
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    names = [record["relative_path"] for record in manifest["artifacts"]]
    names.append("artifacts.manifest.json")
    (bundle / "checksums.sha256").write_text(
        "".join(f"{sha256_file(bundle / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def _rewrite_rows(bundle: Path, rows) -> None:
    (bundle / "raw.jsonl").write_text(
        "".join(canonical_json_text(row) + "\n" for row in rows), encoding="utf-8"
    )


def _update_anchor_snapshot(anchor_path: Path, bundle: Path) -> None:
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    anchor["fresh_v2_bundle"] = verifier.directory_snapshot_binding(bundle)
    anchor_path.write_bytes(canonical_json_bytes(anchor))


@pytest.fixture
def fake_science_report(monkeypatch):
    report = {
        "ok": True,
        "checks": {f"check_{index}": True for index in range(20)},
        "protocol_acceptance": False,
        "experiment_completed": False,
    }
    monkeypatch.setattr(
        verifier.science,
        "verify_portable_audit_bundle_v3",
        lambda _root: report,
    )
    return report


def test_requirements_closure_is_recursive_exact_and_path_safe() -> None:
    closure = verifier.requirements_closure()
    assert closure["entrypoint"] == "environment/requirements/dev.txt"
    assert [item["path"] for item in closure["files"]] == [
        "environment/requirements/core.txt",
        "environment/requirements/dev.txt",
    ]
    assert closure["pins"] == verifier.EXPECTED_REQUIRED_PINS
    assert closure["include_edges"] == [
        {
            "from": "environment/requirements/dev.txt",
            "to": "environment/requirements/core.txt",
        }
    ]
    with pytest.raises(verifier.ValidationMismatch):
        verifier.requirements_closure("../outside.txt")


def test_predecessors_and_scientific_sources_remain_byte_exact() -> None:
    assert verifier.predecessor_snapshots() == verifier.IMMUTABLE_PREDECESSOR_SNAPSHOTS
    bindings = verifier.source_bindings()
    for role, relative in verifier.SOURCE_PATHS.items():
        if role.startswith("scientific_"):
            assert bindings[role]["sha256"] == (
                verifier.IMMUTABLE_SCIENTIFIC_SOURCE_SHA256[relative]
            )


def test_synthetic_anchored_bundle_passes_and_does_not_claim_rerun(
    tmp_path, fake_science_report
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    assert verify_bundle(bundle, required_roles=verifier.REQUIRED_ROLES).ok
    report = verifier.verify_fresh_validation_v2(bundle, anchor, sha256_file(anchor))
    assert report["ok"] is True, report["errors"]
    assert report["historical_commands_authenticated"] is True
    assert report["historical_commands_independently_rerun"] is False
    assert report["runtime_matches_reference"] is False


def test_coordinated_999_stream_summary_and_local_resigning_fails_unchanged_anchor(
    tmp_path, fake_science_report
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    rows = [json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()]
    full = next(row for row in rows if row["command_id"] == "full_pytest")
    full["stdout"] = _stream("999 passed in 0.01s\n")
    _rewrite_rows(bundle, rows)
    summary_path = bundle / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["full_pytest_passed"] = 999
    summary_path.write_bytes(canonical_json_bytes(summary))
    _resign_bundle(bundle)
    expected_anchor_sha = sha256_file(anchor)
    report = verifier.verify_fresh_validation_v2(
        bundle, anchor, expected_anchor_sha
    )
    assert report["ok"] is False
    assert report["checks"]["bundle_snapshot_matches_external_anchor_before_parse"] is False


@pytest.mark.parametrize("target", ["bundle_root", "artifact"])
def test_bundle_root_and_artifact_symlinks_fail_closed(
    tmp_path, fake_science_report, target
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    candidate = bundle
    if target == "bundle_root":
        candidate = tmp_path / "bundle-link"
        candidate.symlink_to(bundle, target_is_directory=True)
    else:
        run_path = bundle / "run.json"
        external = tmp_path / "external-run.json"
        external.write_bytes(run_path.read_bytes())
        run_path.unlink()
        run_path.symlink_to(external)
    report = verifier.verify_fresh_validation_v2(
        candidate, anchor, sha256_file(anchor)
    )
    assert report["ok"] is False
    assert report["checks"]["bundle_snapshot_matches_external_anchor_before_parse"] is False


def test_runtime_rewritten_to_reference_fails_even_with_temporary_updated_anchor(
    tmp_path, fake_science_report
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    run_path = bundle / "run.json"
    run = json.loads(run_path.read_text())
    run["fresh_runtime_build"] = copy.deepcopy(
        verifier.science.REFERENCE_RUNTIME_BUILD_V2
    )
    run_path.write_bytes(canonical_json_bytes(run))
    rows = [json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()]
    row = next(item for item in rows if item["command_id"] == "portable_v3_verifier")
    payload = json.loads(row["stdout"]["text"])
    payload["runtime_build"] = copy.deepcopy(verifier.science.REFERENCE_RUNTIME_BUILD_V2)
    payload["runtime_matches_reference"] = True
    payload["runtime_build_differences"] = []
    row["stdout"] = _stream(json.dumps(payload, sort_keys=True) + "\n")
    _rewrite_rows(bundle, rows)
    summary_path = bundle / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["fresh_runtime_build"] = copy.deepcopy(
        verifier.science.REFERENCE_RUNTIME_BUILD_V2
    )
    summary["runtime_matches_reference"] = True
    summary["runtime_build_differences"] = []
    summary_path.write_bytes(canonical_json_bytes(summary))
    _resign_bundle(bundle)
    _update_anchor_snapshot(anchor, bundle)
    report = verifier.verify_fresh_validation_v2(
        bundle, anchor, sha256_file(anchor)
    )
    assert report["ok"] is False
    assert report["checks"]["runtime_fingerprint_independently_nonreference"] is False


@pytest.mark.parametrize("tamper", ["anchor_source", "closure_omission"])
def test_anchor_modification_or_requirements_closure_omission_fails(
    tmp_path, fake_science_report, tamper
) -> None:
    bundle, anchor_path = _synthetic_bundle(tmp_path)
    expected_anchor_sha = sha256_file(anchor_path)
    anchor = json.loads(anchor_path.read_text())
    if tamper == "anchor_source":
        anchor["source_files"]["fresh_verifier"]["sha256"] = "0" * 64
    else:
        anchor["requirements_closure"]["files"] = [
            item
            for item in anchor["requirements_closure"]["files"]
            if not item["path"].endswith("core.txt")
        ]
        payload = {
            key: anchor["requirements_closure"][key]
            for key in ("entrypoint", "files", "include_edges", "pins")
        }
        anchor["requirements_closure"]["closure_sha256"] = sha256_bytes(
            canonical_json_bytes(payload)
        )
    anchor_path.write_bytes(canonical_json_bytes(anchor))
    supplied_sha = (
        expected_anchor_sha
        if tamper == "anchor_source"
        else sha256_file(anchor_path)
    )
    report = verifier.verify_fresh_validation_v2(
        bundle, anchor_path, supplied_sha
    )
    assert report["ok"] is False
    if tamper == "anchor_source":
        assert report["checks"]["external_anchor_matches_expected_sha256"] is False
    else:
        assert report["checks"][
            "external_anchor_semantics_and_sources_recomputed"
        ] is False


def test_install_report_download_hash_tamper_fails_with_coordinated_resigning(
    tmp_path, fake_science_report
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    rows = [json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()]
    install = next(row for row in rows if row["command_id"] == "pip_install")
    report = json.loads(install["install_report"]["text"])
    report["install"][0]["download_info"]["archive_info"]["hashes"].pop("sha256")
    install["install_report"] = _stream(json.dumps(report, sort_keys=True))
    _rewrite_rows(bundle, rows)
    _resign_bundle(bundle)
    _update_anchor_snapshot(anchor, bundle)
    result = verifier.verify_fresh_validation_v2(
        bundle, anchor, sha256_file(anchor)
    )
    assert result["ok"] is False
    assert result["checks"]["pip_install_report_versions_and_download_hashes"] is False


@pytest.mark.parametrize("tamper", ["unknown_schema", "path_traversal"])
def test_unknown_schema_and_command_path_traversal_fail_closed(
    tmp_path, fake_science_report, tamper
) -> None:
    bundle, anchor = _synthetic_bundle(tmp_path)
    if tamper == "unknown_schema":
        run_path = bundle / "run.json"
        run = json.loads(run_path.read_text())
        run["schema_version"] = "attacker.unknown.v999"
        run_path.write_bytes(canonical_json_bytes(run))
    else:
        run_path = bundle / "run.json"
        run = json.loads(run_path.read_text())
        contract = next(
            item for item in run["command_contract"] if item["command_id"] == "pip_install"
        )
        contract["argv"][7] = "../dev.txt"
        run_path.write_bytes(canonical_json_bytes(run))
        rows = [
            json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()
        ]
        install = next(row for row in rows if row["command_id"] == "pip_install")
        install["normalized_argv"][7] = "../dev.txt"
        install["executed_argv"][7] = "../dev.txt"
        _rewrite_rows(bundle, rows)
    _resign_bundle(bundle)
    _update_anchor_snapshot(anchor, bundle)
    report = verifier.verify_fresh_validation_v2(
        bundle, anchor, sha256_file(anchor)
    )
    assert report["ok"] is False
    if tamper == "unknown_schema":
        assert report["checks"]["run_schema_track_and_id"] is False
    else:
        assert report["checks"]["run_command_whitelist"] is False
        assert report["checks"]["command_rows_paths_streams_and_exits"] is False


def test_cli_requires_anchor_and_fails_without_it(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "analysis" / "verify_e5_v11_fresh_validation_v2.py"), str(tmp_path)],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode != 0
    assert "--anchor" in completed.stderr
