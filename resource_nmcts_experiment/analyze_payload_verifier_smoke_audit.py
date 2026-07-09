#!/usr/bin/env python3
"""Run the package verifier from an extracted upload payload.

The payload round-trip audit proves archive integrity, and the extraction smoke
audit runs selected lightweight scripts.  This terminal audit checks the
reviewer-facing one-command path: extract the tarball to a clean directory and
run ``./verify_submission_package.sh`` from inside the extracted payload tree.

The upload payload intentionally does not contain its own tarball or terminal
self-audit outputs.  The verifier therefore runs in extracted-payload mode,
where archive-self checks are delegated to the source-worktree audits while
PDF, text, metadata, path/privacy, and package-invariant checks still execute.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

from make_submission_payload_archive import ARCHIVE, PAYLOAD_ROOT, THIS_DIR


RESULTS = THIS_DIR / "results"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def row(
    item: str,
    status: str,
    source: str,
    returncode: int | str,
    elapsed_seconds: float | str,
    evidence: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "source": source,
        "returncode": str(returncode),
        "elapsed_seconds": f"{elapsed_seconds:.3f}" if isinstance(elapsed_seconds, float) else str(elapsed_seconds),
        "evidence": evidence,
        "next_action": next_action,
    }


def safe_payload_path(path: str) -> bool:
    return bool(path) and not path.startswith("/") and not path.startswith("../") and "/../" not in path


def extract_payload(root: Path) -> tuple[Path | None, int, str]:
    if not ARCHIVE.exists():
        return None, 0, f"missing archive: {rel(ARCHIVE)}"
    payload_dir = root / PAYLOAD_ROOT
    try:
        count = 0
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if not member.name.startswith(f"{PAYLOAD_ROOT}/"):
                    return None, count, f"unsafe archive root: {member.name}"
                payload_rel = member.name.removeprefix(f"{PAYLOAD_ROOT}/")
                if not safe_payload_path(payload_rel):
                    return None, count, f"unsafe payload path: {member.name}"
                target = payload_dir / payload_rel
                resolved = target.resolve()
                if not str(resolved).startswith(str(payload_dir.resolve())):
                    return None, count, f"path escapes payload root: {member.name}"
                extracted = tar.extractfile(member)
                if extracted is None:
                    return None, count, f"cannot extract: {member.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(extracted.read())
                target.chmod(member.mode & 0o777)
                count += 1
        return payload_dir, count, ""
    except Exception as exc:
        return None, 0, f"{type(exc).__name__}: {exc}"


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_verifier(payload_dir: Path) -> dict[str, str]:
    script = payload_dir / "verify_submission_package.sh"
    if not script.exists():
        return row(
            "Extracted payload verifier command",
            "needs revision",
            "verify_submission_package.sh",
            "missing",
            "0.000",
            "missing verifier script in extracted payload.",
            "Regenerate the payload archive with verify_submission_package.sh included.",
        )
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["RESOURCE_NMCTS_EXTRACTED_PAYLOAD"] = "1"
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=payload_dir,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=240,
        )
    except Exception as exc:
        return row(
            "Extracted payload verifier command",
            "needs revision",
            "verify_submission_package.sh",
            "exception",
            "not_recorded",
            f"execution failed: {type(exc).__name__}: {exc}.",
            "Fix verify_submission_package.sh so it runs from an extracted payload tree.",
        )
    manifest = read_json(payload_dir / "results" / "manifest_submission_package_verifier.json")
    status_counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    extracted_mode = bool(manifest.get("extracted_payload_mode", False)) if manifest else False
    stderr_lines = proc.stderr.strip().splitlines()
    status = (
        "pass"
        if proc.returncode == 0 and manifest and needs_revision == 0 and rows >= 24 and extracted_mode
        else "needs revision"
    )
    evidence = (
        f"verifier_returncode={proc.returncode}; verifier_rows={rows}; "
        f"verifier_needs_revision_count={needs_revision}; extracted_payload_mode={extracted_mode}; "
        f"status_counts={status_counts}; stdout_lines={len(proc.stdout.splitlines())}; "
        f"stderr={stderr_lines[:2] or 'none'}."
    )
    return row(
        "Extracted payload verifier command",
        status,
        "verify_submission_package.sh",
        proc.returncode,
        "not_recorded",
        evidence,
        "Inspect the verifier outputs generated inside the extracted payload directory.",
    )


def build_rows() -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="resource_nmcts_payload_verifier_") as tmp:
        payload_dir, count, error = extract_payload(Path(tmp))
        rows = [
            row(
                "Payload extraction for verifier smoke",
                "pass" if payload_dir is not None and count > 0 and not error else "needs revision",
                rel(ARCHIVE),
                "n/a",
                "0.000",
                f"extracted_files={count}; error={error or 'none'}.",
                "Regenerate the payload archive if it cannot be safely extracted.",
            )
        ]
        if payload_dir is None:
            return rows
        rows.append(run_verifier(payload_dir))
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "source", "returncode", "elapsed_seconds", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Payload Verifier Smoke Audit",
        "",
        "This terminal audit extracts the upload payload and runs `verify_submission_package.sh` from inside the extracted tree.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| item | status | source | returncode | elapsed seconds | evidence | next action |",
            "|---|---|---|---:|---:|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            "| {item} | {status} | `{source}` | {returncode} | {elapsed_seconds} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    verifier_row = next((item for item in rows if item["item"] == "Extracted payload verifier command"), {})
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "verifier_returncode": verifier_row.get("returncode", "missing"),
        "rows_detail": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_payload_verifier_smoke_audit.csv"),
            "analysis": rel(RESULTS / "analysis_payload_verifier_smoke_audit.md"),
            "manifest": rel(RESULTS / "manifest_payload_verifier_smoke_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_verifier_smoke_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_verifier_smoke_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_verifier_smoke_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload verifier smoke row(s)")
    if failures:
        print(f"warning: {failures} payload verifier smoke row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
