#!/usr/bin/env python3
"""Verify the externally anchored E5-v1.1 fresh-install validation v2 bundle.

The bundle checksum is only an integrity convenience.  This verifier requires
the separately supplied anchor as its trust root, authenticates the bundle
snapshot before parsing bundle claims, then recomputes the command, install,
requirements, runtime, and summary contracts.  Historical commands are
authenticated, not re-executed by this verifier.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
override = os.environ.get("XA_E5_PROJECT_ROOT")
if override and Path(override).resolve() != PROJECT_ROOT:
    raise RuntimeError("XA_E5_PROJECT_ROOT does not match the validation source tree")
os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis import verify_e5_v11_negative_audit_bundle as science  # noqa: E402
from src.contracts.artifacts import verify_bundle  # noqa: E402
from src.contracts.codec import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)


TRACK = "xa202609/e5-v11-portable-fresh-validation-v2"
RUN_SCHEMA = "xa.e5-v11-portable-fresh-validation-run.v2"
ROW_SCHEMA = "xa.e5-v11-portable-fresh-validation-command.v2"
SUMMARY_SCHEMA = "xa.e5-v11-portable-fresh-validation-summary.v2"
DECLARED_SCHEMA = "xa.e5-v11-portable-fresh-validation-declared-verifier.v2"
REPORT_SCHEMA = "xa.e5-v11-portable-fresh-validation-independent-report.v2"
ANCHOR_SCHEMA = "xa.e5-v11-portable-fresh-validation-anchor.v2"

RUN_ID = "20260812-e5-v11-portable-fresh-validation-v2-s970000"
SCIENCE_RUN_ID = science.PORTABLE_V3_RUN_ID
ANCHOR_RELATIVE_PATH = (
    "configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json"
)
REQUIREMENTS_ENTRYPOINT = "environment/requirements/dev.txt"

EXPECTED_FILES = frozenset(science.EXPECTED_FILES)
REQUIRED_ROLES = science.REQUIRED_ROLES
EXPECTED_REQUIRED_PINS = {
    "numpy": "2.4.6",
    "scipy": "1.17.1",
    "pulp": "3.3.1",
    "torch": "2.12.0",
    "pytest": "9.0.3",
}

IMMUTABLE_SCIENTIFIC_SOURCE_SHA256 = {
    "analysis/audit_e5_v11_negative_bundle.py": (
        "608d17da7ff76e6bc347be9d3e84cbd3f5e6cb3232822da2dc9ec002fa46a516"
    ),
    "analysis/verify_e5_v11_negative_audit_bundle.py": (
        "759f92f62559d5b544d55f4e8859fcf07d427570123a72281e882da09c8f1e0e"
    ),
    "tests/test_e5_v11_negative_audit.py": (
        "45b1bb977d60057603d6f33c362838ea53a2a742fc18db4e2b741164046f5d8f"
    ),
}
IMMUTABLE_PREDECESSOR_SNAPSHOTS = {
    "20260812-e5-v11-negative-audit-v1-s950000": (
        "eec9d17bd7d17e3d2219781d0f010d8bca553e530d23f2ea7efcb5546b0ea75c"
    ),
    "20260812-e5-v11-portable-negative-audit-v2-s950000": (
        "f57a5e2fe0605f413a1187e1de69b2a51a5e312f5205108a6532782dfa791974"
    ),
    "20260812-e5-v11-portable-negative-audit-v3-s950000": (
        "4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea"
    ),
    "20260812-e5-v11-portable-fresh-validation-v1-s960000": (
        "fc641602e29c1f8416dda6007d3ff64ce36d4b003b7e699ec0a5e202467ef4bc"
    ),
}

SOURCE_PATHS = {
    "fresh_builder": "analysis/build_e5_v11_fresh_validation_v2.py",
    "fresh_verifier": "analysis/verify_e5_v11_fresh_validation_v2.py",
    "fresh_test": "tests/test_e5_v11_fresh_validation_v2.py",
    "scientific_producer": "analysis/audit_e5_v11_negative_bundle.py",
    "scientific_verifier": "analysis/verify_e5_v11_negative_audit_bundle.py",
    "scientific_test": "tests/test_e5_v11_negative_audit.py",
}

COMMAND_CONTRACT: tuple[dict[str, Any], ...] = (
    {
        "command_id": "venv_create",
        "executor": "host",
        "argv": ["host-python", "-m", "venv", "<fresh-venv>"],
    },
    {
        "command_id": "pip_version",
        "executor": "fresh",
        "argv": ["fresh-python", "-m", "pip", "--version"],
    },
    {
        "command_id": "pip_install",
        "executor": "fresh",
        "argv": [
            "fresh-python",
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "-r",
            REQUIREMENTS_ENTRYPOINT,
            "--report",
            "<pip-install-report>",
        ],
    },
    {
        "command_id": "pip_check",
        "executor": "fresh",
        "argv": ["fresh-python", "-m", "pip", "check"],
    },
    {
        "command_id": "targeted_e5",
        "executor": "fresh",
        "argv": [
            "fresh-python",
            "-m",
            "pytest",
            "tests/test_e5_v11_negative_audit.py",
            "tests/test_e5_v11_fresh_validation_v2.py",
            "-q",
        ],
    },
    {
        "command_id": "full_pytest",
        "executor": "fresh",
        "argv": ["fresh-python", "-m", "pytest", "tests", "-q"],
    },
    {
        "command_id": "legacy_smoke",
        "executor": "fresh",
        "argv": ["fresh-python", "tests/tests_smoke.py"],
    },
    {
        "command_id": "default_clean_install",
        "executor": "fresh",
        "argv": ["fresh-python", "scripts/verify_clean_install.py"],
    },
    {
        "command_id": "portable_v3_verifier",
        "executor": "fresh",
        "argv": [
            "fresh-python",
            "analysis/verify_e5_v11_negative_audit_bundle.py",
            f"results/xa202609/{SCIENCE_RUN_ID}",
        ],
    },
)


class ValidationMismatch(RuntimeError):
    """An anchored validation contract was not satisfied."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationMismatch(message)


def _require_no_symlink_components(path: Path, label: str) -> None:
    absolute = Path(path).absolute()
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink():
            raise ValidationMismatch(f"{label} contains a symlink: {candidate}")


def _require_plain_regular_file(path: Path, label: str) -> None:
    _require_no_symlink_components(path, label)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValidationMismatch(f"{label} is missing: {path}") from exc
    _require(stat.S_ISREG(mode), f"{label} is not a regular file: {path}")


def _read_json(path: Path) -> dict[str, Any]:
    _require_plain_regular_file(path, "JSON artifact")
    text = path.read_text(encoding="utf-8")
    value = _strict_json_loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    if canonical_json_bytes(value) != text.encode("utf-8"):
        raise ValueError(f"{path} is not canonical JSON")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    _require_plain_regular_file(path, "JSONL artifact")
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        raise ValueError(f"{path.name} must end with one line feed")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            raise ValueError(f"{path.name} line {number} is empty")
        value = _strict_json_loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} line {number} is not an object")
        canonical_line = canonical_json_bytes(value)
        if not canonical_line.endswith(b"\n"):
            raise AssertionError("canonical JSON codec must append one newline")
        if canonical_line[:-1] != line.encode("utf-8"):
            raise ValueError(f"{path.name} line {number} is not canonical JSON")
        rows.append(value)
    return rows


def _strict_json_loads(text: str) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"non-finite JSON number: {value}")
        return parsed

    return json.loads(
        text,
        object_pairs_hook=object_pairs,
        parse_constant=reject_constant,
        parse_float=parse_float,
    )


def _payload_sha(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def directory_snapshot_binding(root: Path) -> dict[str, Any]:
    root = Path(root).absolute()
    _require_no_symlink_components(root, "snapshot root")
    try:
        root_mode = root.lstat().st_mode
    except OSError as exc:
        raise ValidationMismatch(f"snapshot root is missing: {root}") from exc
    _require(stat.S_ISDIR(root_mode), f"snapshot root is not a directory: {root}")
    records: list[list[Any]] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        _require_plain_regular_file(path, "snapshot artifact")
        records.append([path.name, path.stat().st_size, sha256_file(path)])
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "run_id": root.name,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": hashlib.sha256(payload).hexdigest(),
        "snapshot_files": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, size, digest in records
        ],
    }


def _safe_project_path(relative: str) -> Path:
    _require(isinstance(relative, str) and relative, "project path is empty")
    _require("\\" not in relative and "\x00" not in relative, "unsafe path encoding")
    raw_parts = relative.split("/")
    _require(
        all(part not in {"", ".", ".."} for part in raw_parts),
        f"unsafe project-relative path: {relative}",
    )
    pure = PurePosixPath(relative)
    _require(
        not pure.is_absolute() and ".." not in pure.parts and "." not in pure.parts,
        f"unsafe project-relative path: {relative}",
    )
    candidate = PROJECT_ROOT / Path(*pure.parts)
    _require_no_symlink_components(candidate, "project path")
    path = candidate.resolve()
    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValidationMismatch(f"project path escapes root: {relative}") from exc
    return path


def source_bindings() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for role, relative in sorted(SOURCE_PATHS.items()):
        path = _safe_project_path(relative)
        _require_plain_regular_file(path, "source file")
        result[role] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return result


def _parse_requirement_include(line: str) -> str | None:
    tokens = line.split()
    if len(tokens) == 2 and tokens[0] in {"-r", "--requirement"}:
        return tokens[1]
    if line.startswith("-r") and len(line) > 2 and not line[2].isspace():
        return line[2:]
    if line.startswith("--requirement="):
        return line.split("=", 1)[1]
    return None


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements_closure(entrypoint: str = REQUIREMENTS_ENTRYPOINT) -> dict[str, Any]:
    entry = _safe_project_path(entrypoint)
    allowed_root = (PROJECT_ROOT / "environment" / "requirements").resolve()
    _require_plain_regular_file(entry, "requirements entrypoint")
    try:
        entry.relative_to(allowed_root)
    except ValueError as exc:
        raise ValidationMismatch("requirements entrypoint escapes requirements root") from exc

    records: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    pins: dict[str, str] = {}
    active: set[Path] = set()

    def visit(path: Path) -> None:
        _require_plain_regular_file(path, "requirements file")
        path = path.resolve()
        try:
            path.relative_to(allowed_root)
        except ValueError as exc:
            raise ValidationMismatch("requirements include escapes requirements root") from exc
        _require_plain_regular_file(path, "included requirements file")
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if relative in records:
            return
        _require(path not in active, "requirements include cycle detected")
        active.add(path)
        payload = path.read_bytes()
        includes: list[str] = []
        file_pins: dict[str, str] = {}
        for raw_line in payload.decode("utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            include = _parse_requirement_include(line)
            if include is not None:
                _require(
                    "\\" not in include
                    and "\x00" not in include
                    and not PurePosixPath(include).is_absolute()
                    and all(
                        part not in {"", ".", ".."}
                        for part in include.split("/")
                    ),
                    f"requirements include traversal: {include}",
                )
                parent_relative = path.parent.relative_to(PROJECT_ROOT).as_posix()
                include_path = _safe_project_path(
                    (PurePosixPath(parent_relative) / include).as_posix()
                )
                try:
                    include_path.relative_to(allowed_root)
                except ValueError as exc:
                    raise ValidationMismatch(
                        f"requirements include traversal: {include}"
                    ) from exc
                include_relative = include_path.relative_to(PROJECT_ROOT).as_posix()
                includes.append(include_relative)
                edges.append({"from": relative, "to": include_relative})
                visit(include_path)
                continue
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
            _require(match is not None, f"non-exact requirement is forbidden: {line}")
            name = _normalize_package_name(match.group(1))
            version = match.group(2)
            _require(
                name not in pins or pins[name] == version,
                f"conflicting requirement pin: {name}",
            )
            pins[name] = version
            file_pins[name] = version
        records[relative] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "includes": sorted(includes),
            "pins": dict(sorted(file_pins.items())),
        }
        active.remove(path)

    visit(entry)
    ordered_records = [records[name] for name in sorted(records)]
    closure_payload = {
        "entrypoint": entrypoint,
        "files": ordered_records,
        "include_edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
        "pins": dict(sorted(pins.items())),
    }
    return {
        **closure_payload,
        "closure_sha256": _payload_sha(closure_payload),
    }


def predecessor_snapshots() -> dict[str, str]:
    root = PROJECT_ROOT / "results" / "xa202609"
    return {
        run_id: directory_snapshot_binding(root / run_id)["snapshot_sha256"]
        for run_id in sorted(IMMUTABLE_PREDECESSOR_SNAPSHOTS)
    }


def _stream_valid(stream: object) -> bool:
    if not isinstance(stream, Mapping) or set(stream) != {"text", "bytes", "sha256"}:
        return False
    text = stream.get("text")
    if not isinstance(text, str) or "\r" in text:
        return False
    payload = text.encode("utf-8")
    return (
        stream.get("bytes") == len(payload)
        and stream.get("sha256") == hashlib.sha256(payload).hexdigest()
    )


def _stdout(row: Mapping[str, Any]) -> str:
    stream = row.get("stdout")
    if not _stream_valid(stream):
        raise ValidationMismatch("stdout stream binding is invalid")
    return str(stream["text"])


def _json_stdout(row: Mapping[str, Any]) -> dict[str, Any]:
    value = _strict_json_loads(_stdout(row))
    if not isinstance(value, dict):
        raise ValidationMismatch("JSON stdout is not an object")
    return value


def _pytest_passed_count(text: str) -> int:
    matches = re.findall(r"(?:^|\s)(\d+) passed(?:[,\s]|$)", text)
    _require(bool(matches), "pytest passed count is missing")
    return int(matches[-1])


def _validate_path_context(run: Mapping[str, Any]) -> dict[str, str]:
    context = run.get("path_context")
    _require(isinstance(context, Mapping), "path context is missing")
    _require(
        set(context) == {
            "temporary_root",
            "venv_path",
            "fresh_python",
            "pip_install_report",
            "host_python",
        },
        "path context keys differ",
    )
    values = {key: str(value) for key, value in context.items()}
    for key, value in values.items():
        _require(Path(value).is_absolute(), f"path context {key} is not absolute")
        _require(".." not in Path(value).parts, f"path traversal in {key}")
    temporary_root = Path(values["temporary_root"])
    _require(
        temporary_root.parent == Path(tempfile.gettempdir()).resolve()
        and temporary_root.name.startswith("xa-e5-fresh-v2-"),
        "temporary root is outside the approved namespace",
    )
    _require(Path(values["venv_path"]) == temporary_root / "venv", "venv path mismatch")
    _require(
        Path(values["pip_install_report"]) == temporary_root / "pip-install-report.json",
        "pip report path mismatch",
    )
    _require(
        Path(values["fresh_python"]) == Path(values["venv_path"]) / "bin" / "python",
        "fresh Python path mismatch",
    )
    return values


def _expected_executed_argv(
    contract: Mapping[str, Any], paths: Mapping[str, str]
) -> list[str]:
    normalized = list(contract["argv"])
    replacements = {
        "host-python": paths["host_python"],
        "fresh-python": paths["fresh_python"],
        "<fresh-venv>": paths["venv_path"],
        "<pip-install-report>": paths["pip_install_report"],
    }
    return [replacements.get(value, value) for value in normalized]


def validate_command_rows(
    rows: Sequence[Mapping[str, Any]], run: Mapping[str, Any]
) -> dict[str, Mapping[str, Any]]:
    _require(len(rows) == len(COMMAND_CONTRACT), "command row count differs")
    paths = _validate_path_context(run)
    by_id: dict[str, Mapping[str, Any]] = {}
    for ordinal, (contract, row) in enumerate(zip(COMMAND_CONTRACT, rows)):
        _require(
            set(row)
            == {
                "schema_version",
                "ordinal",
                "command_id",
                "executor",
                "normalized_argv",
                "executed_argv",
                "exit_code",
                "duration_seconds",
                "stdout",
                "stderr",
                "success",
                *( ["install_report"] if contract["command_id"] == "pip_install" else [] ),
            },
            f"command row keys differ: {contract['command_id']}",
        )
        _require(row.get("schema_version") == ROW_SCHEMA, "command row schema differs")
        _require(row.get("ordinal") == ordinal, "command ordinal differs")
        _require(row.get("command_id") == contract["command_id"], "command id differs")
        _require(row.get("executor") == contract["executor"], "command executor differs")
        _require(row.get("normalized_argv") == contract["argv"], "command whitelist differs")
        _require(
            row.get("executed_argv") == _expected_executed_argv(contract, paths),
            "executed argv does not normalize to whitelist",
        )
        duration = row.get("duration_seconds")
        _require(
            isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and math.isfinite(float(duration))
            and float(duration) >= 0.0,
            "command duration is invalid",
        )
        _require(row.get("exit_code") == 0 and row.get("success") is True, "command failed")
        _require(_stream_valid(row.get("stdout")), "stdout stream is not hash-bound")
        _require(_stream_valid(row.get("stderr")), "stderr stream is not hash-bound")
        by_id[str(contract["command_id"])] = row
    return by_id


def install_report_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    evidence = row.get("install_report")
    _require(isinstance(evidence, Mapping), "pip install report evidence is missing")
    _require(
        set(evidence) == {"text", "bytes", "sha256"},
        "pip install report evidence keys differ",
    )
    _require(_stream_valid(evidence), "pip install report is not hash-bound")
    report = _strict_json_loads(str(evidence["text"]))
    _require(isinstance(report, dict), "pip install report is not an object")
    _require(report.get("version") == "1", "unsupported pip install report version")
    installs = report.get("install")
    _require(isinstance(installs, list) and installs, "pip install report has no installs")
    packages: list[dict[str, Any]] = []
    installed: dict[str, str] = {}
    for item in installs:
        _require(isinstance(item, Mapping), "pip install item is not an object")
        metadata = item.get("metadata")
        download = item.get("download_info")
        _require(
            isinstance(metadata, Mapping) and isinstance(download, Mapping),
            "pip install item lacks metadata/download_info",
        )
        name = _normalize_package_name(str(metadata.get("name", "")))
        version = str(metadata.get("version", ""))
        _require(name and version, "pip install item lacks name/version")
        archive = download.get("archive_info")
        _require(isinstance(archive, Mapping), "pip install item lacks archive_info")
        hashes = archive.get("hashes")
        _require(isinstance(hashes, Mapping), "pip install item lacks download hashes")
        sha = hashes.get("sha256")
        _require(
            isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
            "pip install item lacks a SHA-256 download hash",
        )
        _require(name not in installed, f"duplicate pip install record: {name}")
        installed[name] = version
        packages.append(
            {
                "name": name,
                "version": version,
                "requested": bool(item.get("requested")),
                "download_url": str(download.get("url", "")),
                "download_sha256": sha,
            }
        )
    for name, version in EXPECTED_REQUIRED_PINS.items():
        _require(installed.get(name) == version, f"required install pin differs: {name}")
    return {
        "report_sha256": str(evidence["sha256"]),
        "report_bytes": int(evidence["bytes"]),
        "packages": sorted(packages, key=lambda item: item["name"]),
        "installed_required_pins": {
            name: installed.get(name) for name in sorted(EXPECTED_REQUIRED_PINS)
        },
    }


def expected_summary_for_run(
    run_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    run: Mapping[str, Any],
    closure: Mapping[str, Any],
    science_binding: Mapping[str, Any],
    fresh_runtime: Mapping[str, Any],
) -> dict[str, Any]:
    by_id = validate_command_rows(rows, run)
    install = install_report_evidence(by_id["pip_install"])
    pip_version = _stdout(by_id["pip_version"]).strip()
    default_report = _json_stdout(by_id["default_clean_install"])
    v3_report = _json_stdout(by_id["portable_v3_verifier"])
    runtime_valid = science.runtime_build_fingerprint_valid_v2(fresh_runtime)
    _require(runtime_valid, "fresh runtime fingerprint is malformed")
    runtime_matches = science.runtime_matches_reference_v2(
        fresh_runtime, science.REFERENCE_RUNTIME_BUILD_V2
    )
    runtime_differences = science.runtime_build_differences_v2(
        fresh_runtime, science.REFERENCE_RUNTIME_BUILD_V2
    )
    _require(not runtime_matches and runtime_differences, "fresh runtime equals reference")
    _require(
        v3_report.get("schema_version") == science.PORTABLE_V3_REPORT_SCHEMA
        and v3_report.get("ok") is True
        and len(v3_report.get("checks", {})) == 20
        and all(v3_report.get("checks", {}).values())
        and v3_report.get("runtime_build") == fresh_runtime,
        "recorded v3 verifier report is invalid",
    )
    _require(
        "No broken requirements found." in _stdout(by_id["pip_check"]),
        "pip check success marker is missing",
    )
    _require(_stdout(by_id["legacy_smoke"]).strip() == "smoke ok", "smoke marker differs")
    _require(default_report.get("ok") is True, "default clean verifier failed")
    targeted = _pytest_passed_count(_stdout(by_id["targeted_e5"]))
    full = _pytest_passed_count(_stdout(by_id["full_pytest"]))
    return {
        "schema_version": SUMMARY_SCHEMA,
        "track": TRACK,
        "run_id": run_id,
        "validation_role": "externally_anchored_clean_install_software_evidence",
        "requirements_closure": copy.deepcopy(dict(closure)),
        "scientific_v3_bundle": copy.deepcopy(dict(science_binding)),
        "fresh_runtime_build": copy.deepcopy(dict(fresh_runtime)),
        "fresh_runtime_frozen_subset_sha256": _payload_sha(
            science.runtime_build_frozen_subset_v2(fresh_runtime)
        ),
        "runtime_matches_reference": runtime_matches,
        "runtime_build_differences": runtime_differences,
        "command_count": len(rows),
        "successful_command_count": len(rows),
        "total_duration_seconds": sum(float(row["duration_seconds"]) for row in rows),
        "pip_version": pip_version,
        "pip_install": install,
        "required_pins": dict(EXPECTED_REQUIRED_PINS),
        "targeted_e5_passed": targeted,
        "full_pytest_passed": full,
        "pip_check_ok": True,
        "legacy_smoke_ok": True,
        "default_clean_install_ok": True,
        "portable_v3_verifier_ok": True,
        "historical_commands_authenticated": True,
        "historical_commands_independently_rerun_by_bundle_verifier": False,
        "scientific_bundle_independently_recomputed": True,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "trust_boundary": (
            "The external anchor, later protected by the submission manifest and Git, "
            "is the trust root. Bundle-local checksums alone cannot prevent coordinated "
            "re-signing. Recorded commands are authenticated but not rerun here."
        ),
    }


def expected_declared_verifier(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": DECLARED_SCHEMA,
        "run_id": run_id,
        "ok": True,
        "software_validation_ok": True,
        "scientific_evidence": False,
        "independent_recomputation": False,
        "external_anchor_required": True,
        "historical_commands_authenticated": True,
        "historical_commands_independently_rerun": False,
        "scientific_bundle_independently_recomputed": True,
        "protocol_acceptance": False,
        "experiment_completed": False,
    }


def _anchor_semantics(anchor: Mapping[str, Any], bundle_root: Path) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "track",
        "run_id",
        "created_at_utc",
        "fresh_v2_bundle",
        "scientific_v3_bundle",
        "requirements_closure",
        "source_files",
        "predecessor_snapshots",
        "trust_boundary",
    }
    _require(set(anchor) == expected_keys, "anchor keys differ")
    _require(anchor.get("schema_version") == ANCHOR_SCHEMA, "anchor schema differs")
    _require(anchor.get("track") == TRACK and anchor.get("run_id") == RUN_ID, "anchor identity differs")
    _require(bundle_root.name == RUN_ID, "bundle run id is not authoritative")
    closure = requirements_closure()
    _require(anchor.get("requirements_closure") == closure, "anchor requirements closure differs")
    bindings = source_bindings()
    _require(anchor.get("source_files") == bindings, "anchor source bindings differ")
    for role, relative in SOURCE_PATHS.items():
        if role.startswith("scientific_"):
            _require(
                bindings[role]["sha256"]
                == IMMUTABLE_SCIENTIFIC_SOURCE_SHA256[relative],
                f"immutable scientific source changed: {relative}",
            )
    predecessors = predecessor_snapshots()
    _require(
        predecessors == IMMUTABLE_PREDECESSOR_SNAPSHOTS,
        "immutable predecessor snapshot changed",
    )
    _require(anchor.get("predecessor_snapshots") == predecessors, "anchor predecessor snapshots differ")
    science_root = PROJECT_ROOT / "results" / "xa202609" / SCIENCE_RUN_ID
    science_binding = directory_snapshot_binding(science_root)
    _require(anchor.get("scientific_v3_bundle") == science_binding, "anchor v3 science snapshot differs")
    _require(
        anchor.get("trust_boundary")
        == {
            "bundle_local_checksums_prevent_coordinated_resigning": False,
            "external_anchor_requires_submission_manifest_or_git_protection": True,
            "historical_commands_rerun_by_verifier": False,
        },
        "anchor trust boundary differs",
    )
    return {
        "closure": closure,
        "source_bindings": bindings,
        "science_binding": science_binding,
        "predecessor_snapshots": predecessors,
    }


def verify_fresh_validation_v2(
    bundle_root: Path,
    anchor_path: Path,
    expected_anchor_sha256: str,
) -> dict[str, Any]:
    bundle_root = Path(bundle_root).absolute()
    anchor_path = Path(anchor_path).absolute()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def check(value: bool, name: str) -> None:
        checks[name] = bool(value)
        if not value:
            errors.append(f"failed check: {name}")

    if re.fullmatch(r"[0-9a-f]{64}", expected_anchor_sha256 or "") is None:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(bundle_root),
            "anchor": str(anchor_path),
            "ok": False,
            "software_validation_ok": False,
            "checks": {"external_anchor_expected_sha256_valid": False},
            "errors": ["expected external anchor SHA-256 is missing or malformed"],
            "historical_commands_authenticated": False,
            "historical_commands_independently_rerun": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    actual_anchor_sha256 = sha256_file(anchor_path) if anchor_path.is_file() else None
    if actual_anchor_sha256 != expected_anchor_sha256:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(bundle_root),
            "anchor": str(anchor_path),
            "anchor_sha256": actual_anchor_sha256,
            "expected_anchor_sha256": expected_anchor_sha256,
            "ok": False,
            "software_validation_ok": False,
            "checks": {
                "external_anchor_expected_sha256_valid": True,
                "external_anchor_matches_expected_sha256": False,
            },
            "errors": ["external anchor SHA-256 does not match the caller trust root"],
            "historical_commands_authenticated": False,
            "historical_commands_independently_rerun": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }
    try:
        anchor = _read_json(anchor_path)
    except Exception as exc:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(bundle_root),
            "anchor": str(anchor_path),
            "ok": False,
            "software_validation_ok": False,
            "checks": {
                "external_anchor_expected_sha256_valid": True,
                "external_anchor_matches_expected_sha256": True,
                "external_anchor_readable": False,
            },
            "errors": [f"cannot read required external anchor: {type(exc).__name__}:{exc}"],
            "historical_commands_authenticated": False,
            "historical_commands_independently_rerun": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }

    check(True, "external_anchor_expected_sha256_valid")
    check(True, "external_anchor_matches_expected_sha256")
    check(True, "external_anchor_readable")
    try:
        bundle_binding = directory_snapshot_binding(bundle_root)
        anchored = anchor.get("fresh_v2_bundle") == bundle_binding
    except Exception as exc:
        errors.append(f"cannot compute bundle snapshot: {type(exc).__name__}:{exc}")
        anchored = False
        bundle_binding = None
    check(anchored, "bundle_snapshot_matches_external_anchor_before_parse")
    if not anchored:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(bundle_root),
            "anchor": str(anchor_path),
            "anchor_sha256": sha256_file(anchor_path),
            "ok": False,
            "software_validation_ok": False,
            "checks": checks,
            "errors": errors,
            "historical_commands_authenticated": False,
            "historical_commands_independently_rerun": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }

    try:
        anchor_context = _anchor_semantics(anchor, bundle_root)
    except Exception as exc:
        errors.append(f"external anchor semantics failed: {type(exc).__name__}:{exc}")
        anchor_context = None
    check(anchor_context is not None, "external_anchor_semantics_and_sources_recomputed")

    generic = verify_bundle(bundle_root, required_roles=REQUIRED_ROLES)
    check(generic.ok, "bundle_manifest_and_checksums")
    check(
        bundle_root.is_dir()
        and {path.name for path in bundle_root.iterdir()} == EXPECTED_FILES,
        "bundle_exact_nine_files",
    )
    try:
        run = _read_json(bundle_root / "run.json")
        rows = _read_jsonl(bundle_root / "raw.jsonl")
        summary = _read_json(bundle_root / "summary.json")
        declared = _read_json(bundle_root / "verifier.json")
        events = _read_jsonl(bundle_root / "events.jsonl")
    except Exception as exc:
        return {
            "schema_version": REPORT_SCHEMA,
            "bundle": str(bundle_root),
            "anchor": str(anchor_path),
            "anchor_sha256": sha256_file(anchor_path),
            "ok": False,
            "software_validation_ok": False,
            "checks": checks,
            "errors": [*errors, f"cannot parse anchored bundle: {type(exc).__name__}:{exc}"],
            "historical_commands_authenticated": False,
            "historical_commands_independently_rerun": False,
            "protocol_acceptance": False,
            "experiment_completed": False,
        }

    check(
        run.get("schema_version") == RUN_SCHEMA
        and run.get("track") == TRACK
        and run.get("run_id") == RUN_ID == bundle_root.name
        and summary.get("run_id") == RUN_ID
        and declared.get("run_id") == RUN_ID,
        "run_schema_track_and_id",
    )
    check(
        run.get("status") == "complete_fresh_validation_v2"
        and run.get("software_validation_ok") is True
        and run.get("scientific_evidence") is False
        and run.get("hardware_execution") is False
        and run.get("performance_claim_supported") is False
        and run.get("protocol_acceptance") is False
        and run.get("experiment_completed") is False
        and set(run.get("expected_artifacts", [])) == EXPECTED_FILES,
        "run_claim_boundary",
    )
    check(
        anchor_context is not None
        and run.get("requirements_closure") == anchor_context["closure"]
        and run.get("scientific_v3_bundle") == anchor_context["science_binding"]
        and run.get("source_files") == anchor_context["source_bindings"],
        "run_external_bindings_match_anchor",
    )
    check(
        run.get("command_contract") == list(COMMAND_CONTRACT),
        "run_command_whitelist",
    )

    try:
        by_id = validate_command_rows(rows, run)
        rows_ok = True
    except Exception as exc:
        errors.append(f"command rows failed: {type(exc).__name__}:{exc}")
        by_id = {}
        rows_ok = False
    check(rows_ok, "command_rows_paths_streams_and_exits")

    fresh_runtime = run.get("fresh_runtime_build")
    runtime_ok = science.runtime_build_fingerprint_valid_v2(fresh_runtime)
    if runtime_ok:
        runtime_matches = science.runtime_matches_reference_v2(
            fresh_runtime, science.REFERENCE_RUNTIME_BUILD_V2
        )
        runtime_differences = science.runtime_build_differences_v2(
            fresh_runtime, science.REFERENCE_RUNTIME_BUILD_V2
        )
    else:
        runtime_matches = True
        runtime_differences = []
    check(
        runtime_ok and not runtime_matches and bool(runtime_differences),
        "runtime_fingerprint_independently_nonreference",
    )

    install_ok = False
    if rows_ok:
        try:
            install = install_report_evidence(by_id["pip_install"])
            install_ok = (
                install["installed_required_pins"] == EXPECTED_REQUIRED_PINS
                and bool(install["packages"])
            )
        except Exception as exc:
            errors.append(f"pip install report failed: {type(exc).__name__}:{exc}")
    check(install_ok, "pip_install_report_versions_and_download_hashes")

    science_root = PROJECT_ROOT / "results" / "xa202609" / SCIENCE_RUN_ID
    try:
        science_report = science.verify_portable_audit_bundle_v3(science_root)
        science_ok = (
            science_report.get("ok") is True
            and len(science_report.get("checks", {})) == 20
            and all(science_report.get("checks", {}).values())
            and science_report.get("protocol_acceptance") is False
            and science_report.get("experiment_completed") is False
        )
    except Exception as exc:
        errors.append(f"v3 scientific verification failed: {type(exc).__name__}:{exc}")
        science_report = None
        science_ok = False
    check(science_ok, "scientific_v3_bundle_independently_recomputed")

    expected = None
    if rows_ok and anchor_context is not None and runtime_ok:
        try:
            expected = expected_summary_for_run(
                RUN_ID,
                rows,
                run=run,
                closure=anchor_context["closure"],
                science_binding=anchor_context["science_binding"],
                fresh_runtime=fresh_runtime,
            )
        except Exception as exc:
            errors.append(f"summary recomputation failed: {type(exc).__name__}:{exc}")
    check(expected is not None and summary == expected, "summary_independently_recomputed_from_raw")
    check(
        declared == expected_declared_verifier(RUN_ID),
        "declared_verifier_exact_and_nonindependent",
    )
    check(
        len(events) == 4
        and [event.get("event") for event in events]
        == [
            "fresh_validation_v2_started",
            "fresh_venv_created",
            "scientific_v3_bound",
            "fresh_validation_v2_completed",
        ]
        and all(event.get("run_id") == RUN_ID for event in events),
        "event_sequence",
    )
    check(
        (bundle_root / "stdout.log").read_text(encoding="utf-8")
        == (
            "Externally anchored fresh-validation v2 completed: 9/9 historical "
            "commands exited 0; commands are authenticated, not rerun by the bundle "
            "verifier; no scientific endpoint was accepted.\n"
        )
        and (bundle_root / "stderr.log").read_text(encoding="utf-8") == "",
        "terminal_logs_scope",
    )

    ok = bool(checks) and all(checks.values()) and not errors
    return {
        "schema_version": REPORT_SCHEMA,
        "bundle": str(bundle_root),
        "bundle_snapshot_sha256": (
            bundle_binding["snapshot_sha256"] if bundle_binding else None
        ),
        "anchor": str(anchor_path),
        "anchor_sha256": sha256_file(anchor_path),
        "expected_anchor_sha256": expected_anchor_sha256,
        "ok": ok,
        "software_validation_ok": ok,
        "scientific_evidence": False,
        "historical_commands_authenticated": ok,
        "historical_commands_independently_rerun": False,
        "scientific_bundle_independently_recomputed": science_ok,
        "runtime_matches_reference": runtime_matches if runtime_ok else None,
        "runtime_build_differences": runtime_differences,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "checks": checks,
        "errors": errors,
        "summary": expected,
        "scientific_bundle_report": science_report,
        "trust_boundary": (
            "The caller must protect the external anchor via the submission manifest "
            "or Git. Bundle-local checksums cannot prevent coordinated re-signing."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--anchor", required=True, type=Path)
    parser.add_argument("--expected-anchor-sha256", required=True)
    args = parser.parse_args()
    report = verify_fresh_validation_v2(
        args.bundle, args.anchor, args.expected_anchor_sha256
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
