#!/usr/bin/env python3
"""Audit Git policy for the generated upload payload archive.

The upload tarball is a deterministic generated artifact.  It must exist in
the source worktree after the rebuild and pass SHA checks, but it should not be
tracked as a Git blob because it is large and can be regenerated.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
from _paths import find as _find  # noqa: E402
ARCHIVE = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
SHA256 = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
REBUILD_SCRIPT = _find("rebuild_submission_package.sh")
VERIFY_SCRIPT = _find("verify_submission_package.sh")
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=THIS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=12,
        )
    except Exception:
        return None


def git_root() -> Path | None:
    proc = run_git(["rev-parse", "--show-toplevel"])
    if proc is None or proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def repo_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def run_git_at_root(root: Path, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=12,
        )
    except Exception:
        return None


def git_tracked(path: Path, root: Path) -> bool:
    proc = run_git_at_root(root, ["ls-files", "--error-unmatch", "--", repo_path(path, root)])
    return proc is not None and proc.returncode == 0


def git_ignored(path: Path, root: Path) -> bool:
    proc = run_git_at_root(root, ["check-ignore", "-q", "--", repo_path(path, root)])
    return proc is not None and proc.returncode == 0


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    root = git_root()

    if EXTRACTED_PAYLOAD_MODE and not ARCHIVE.exists():
        rows.append(
            row(
                "Extracted payload archive boundary",
                "pass",
                "extracted_payload_mode=1; upload tarball is intentionally absent from the extracted payload.",
                "Run the full archive existence and Git-policy checks in the source worktree after rebuilding.",
            )
        )
        rows.append(
            row(
                "Generated payload Git policy",
                "pass",
                f"git_worktree={root is not None}; source archive tracking check is not applicable inside extracted payload mode.",
                "No action needed for extracted payload verification.",
            )
        )
        return rows

    archive_exists = ARCHIVE.exists()
    sha_exists = SHA256.exists()
    rows.append(
        row(
            "Generated payload presence",
            "pass" if archive_exists and sha_exists else "needs revision",
            f"archive_exists={archive_exists}; sha256_exists={sha_exists}; archive={rel(ARCHIVE)}.",
            "Run make_submission_payload_archive.py or rebuild_submission_package.sh to regenerate the upload tarball and sidecar.",
        )
    )

    if archive_exists and sha_exists:
        actual = sha256_file(ARCHIVE)
        sidecar = SHA256.read_text(encoding="utf-8").split()[0]
        rows.append(
            row(
                "Generated payload SHA sidecar",
                "pass" if actual == sidecar else "needs revision",
                f"actual={actual}; sidecar={sidecar}; bytes={ARCHIVE.stat().st_size}.",
                "Regenerate the tarball and sidecar if their digests differ.",
            )
        )
    else:
        rows.append(
            row(
                "Generated payload SHA sidecar",
                "needs revision",
                "archive_or_sidecar_missing=True.",
                "Regenerate the tarball and sidecar before verifying upload readiness.",
            )
        )

    if root is None:
        rows.append(
            row(
                "Generated payload Git policy",
                "needs revision",
                "git_worktree=False; source-worktree Git ignore policy cannot be checked.",
                "Run this audit from the repository source worktree.",
            )
        )
    else:
        tracked = [repo_path(path, root) for path in (ARCHIVE, SHA256) if git_tracked(path, root)]
        ignored = [repo_path(path, root) for path in (ARCHIVE, SHA256) if git_ignored(path, root)]
        rows.append(
            row(
                "Generated payload Git policy",
                "pass" if not tracked and len(ignored) == 2 else "needs revision",
                f"tracked={tracked or 'none'}; ignored={ignored}; git_root={root}.",
                "Keep submission_package/dist/*.tar.gz and the SHA sidecar ignored and out of the Git index.",
            )
        )

    scripts_present = REBUILD_SCRIPT.exists() and VERIFY_SCRIPT.exists()
    rows.append(
        row(
            "Generated payload regeneration path",
            "pass" if scripts_present else "needs revision",
            f"rebuild_script={REBUILD_SCRIPT.exists()}; verify_script={VERIFY_SCRIPT.exists()}.",
            "Restore rebuild_submission_package.sh and verify_submission_package.sh if either entrypoint is missing.",
        )
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Payload Git Policy Audit",
        "",
        "This audit checks that the deterministic upload tarball is available locally after a rebuild but remains a generated, ignored Git artifact.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        safe = {key: value.replace("|", "\\|") for key, value in item.items()}
        lines.append("| {item} | {status} | {evidence} | {next_action} |".format(**safe))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "extracted_payload_mode": EXTRACTED_PAYLOAD_MODE,
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "archive": rel(ARCHIVE),
        "sha256_file": rel(SHA256),
        "outputs": {
            "summary": "results/summary_payload_git_policy_audit.csv",
            "analysis": "results/analysis_payload_git_policy_audit.md",
            "manifest": "results/manifest_payload_git_policy_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_git_policy_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_git_policy_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_git_policy_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload git-policy row(s)")
    if failures:
        print(f"warning: {failures} payload git-policy row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
