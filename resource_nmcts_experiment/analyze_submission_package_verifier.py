#!/usr/bin/env python3
"""Read-only verifier for the current submission package.

The verifier runs after the payload archive has been created.  It checks the
terminal package invariants that are easy to regress during final polishing:
compiled PDF availability, payload SHA consistency, readiness status, raw rerun
registry coverage, and LaTeX log cleanliness.  It writes a small audit report
but does not rerun experiments or alter manuscript sources.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
LOG = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.log"
PAYLOAD = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
READINESS = RESULTS / "summary_submission_readiness_audit.csv"
REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pdf_pages(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        proc = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return "unknown"
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return match.group(1) if match else "unknown"


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def verify_pdf() -> dict[str, str]:
    pages = pdf_pages(PDF)
    status = "pass" if pages not in {"missing", "unknown"} else "needs revision"
    return row(
        "Compiled PDF",
        status,
        f"{rel(PDF)} pages={pages}, bytes={PDF.stat().st_size if PDF.exists() else 0}.",
        "Rebuild the submission package and inspect latexmk output if the PDF is missing.",
    )


def verify_payload_sha() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not PAYLOAD.exists() or not PAYLOAD_SHA.exists():
        return [
            row(
                "Payload SHA sidecar",
                "needs revision",
                "Payload archive or SHA256 sidecar is missing.",
                "Run make_submission_payload_archive.py or rebuild_submission_package.sh.",
            )
        ]
    actual = sha256_file(PAYLOAD)
    sidecar = PAYLOAD_SHA.read_text(encoding="utf-8").split()[0]
    rows.append(
        row(
            "Payload SHA sidecar",
            "pass" if actual == sidecar else "needs revision",
            f"actual={actual}; sidecar={sidecar}.",
            "Regenerate the payload archive if the digests differ.",
        )
    )
    summary_rows = read_csv(PAYLOAD_SUMMARY)
    manifest = read_json(PAYLOAD_MANIFEST)
    summary_sha = summary_rows[0].get("sha256", "") if summary_rows else ""
    manifest_sha = str(manifest.get("sha256", ""))
    rows.append(
        row(
            "Payload manifest consistency",
            "pass" if actual == summary_sha == manifest_sha else "needs revision",
            f"summary={summary_sha}; manifest={manifest_sha}; file_count={manifest.get('file_count', 'missing')}.",
            "Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree.",
        )
    )
    return rows


def verify_readiness() -> dict[str, str]:
    rows = read_csv(READINESS)
    if not rows:
        return row(
            "Readiness audit terminal state",
            "needs revision",
            "Readiness summary CSV is missing or empty.",
            "Run analyze_submission_readiness_audit.py.",
        )
    rows = [item for item in rows if item.get("item") != "Terminal package verifier"]
    counts: dict[str, int] = {}
    for item in rows:
        counts[item.get("status", "")] = counts.get(item.get("status", ""), 0) + 1
    only_author_gate = counts.get("needs author input", 0) == 1 and counts.get("needs revision", 0) == 0
    return row(
        "Readiness audit terminal state",
        "pass" if only_author_gate else "needs revision",
        f"status_counts={counts}.",
        "Resolve any needs-revision rows; author-specific declarations remain manual.",
    )


def verify_registry() -> dict[str, str]:
    registry_rows = read_csv(REGISTRY_SUMMARY)
    manifest = read_json(REGISTRY_MANIFEST)
    actual_raw_count = len(list(RESULTS.glob("raw_*.csv")))
    complete = bool(registry_rows) and all(item.get("status") == "complete" for item in registry_rows)
    unique_raw_files = int(manifest.get("unique_raw_files", -1)) if manifest else -1
    status = "pass" if complete and unique_raw_files == actual_raw_count else "needs revision"
    return row(
        "Artifact rerun registry coverage",
        status,
        f"families={len(registry_rows)}; registry_raw={unique_raw_files}; actual_raw={actual_raw_count}.",
        "Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts.",
    )


def verify_latex_log() -> dict[str, str]:
    if not LOG.exists():
        return row("LaTeX log boundary", "needs revision", "LaTeX log is missing.", "Rebuild the PDF with latexmk.")
    bad_patterns = re.compile(r"Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun")
    allowed = (
        "Package: rerunfilecheck",
        r"LaTeX Warning: Command \showhyphens",
    )
    unexpected: list[str] = []
    for lineno, line in enumerate(LOG.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not bad_patterns.search(line):
            continue
        if any(token in line for token in allowed):
            continue
        unexpected.append(f"{lineno}:{line.strip()}")
    return row(
        "LaTeX log boundary",
        "pass" if not unexpected else "needs revision",
        "Only allowed rerunfilecheck/showhyphens log lines found." if not unexpected else "; ".join(unexpected[:5]),
        "Inspect the LaTeX log and fix unexpected warnings or errors.",
    )


def build_rows() -> list[dict[str, str]]:
    rows = [verify_pdf()]
    rows.extend(verify_payload_sha())
    rows.extend([verify_readiness(), verify_registry(), verify_latex_log()])
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Submission Package Verifier",
        "",
        "This read-only verifier checks the terminal package invariants after the payload archive has been created.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} | {item['next_action']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "outputs": {
            "summary": "results/summary_submission_package_verifier.csv",
            "analysis": "results/analysis_submission_package_verifier.md",
            "manifest": "results/manifest_submission_package_verifier.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_package_verifier.csv", rows)
    write_markdown(RESULTS / "analysis_submission_package_verifier.md", rows)
    write_manifest(RESULTS / "manifest_submission_package_verifier.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} submission package verifier rows")
    if failures:
        print(f"warning: {failures} verifier row(s) need revision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
