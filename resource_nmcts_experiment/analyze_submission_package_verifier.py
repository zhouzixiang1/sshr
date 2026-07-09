#!/usr/bin/env python3
"""Read-only verifier for the current submission package.

The verifier runs after the payload archive has been created.  It checks the
terminal package invariants that are easy to regress during final polishing:
compiled PDF availability, payload SHA consistency, readiness status, raw rerun
registry coverage, claim-scope hygiene, comparison-protocol coverage,
private-metadata starter dry-run, private-metadata validation,
synthetic metadata-pipeline self-testing, anonymous-review decision support,
private-preview protection, private payload exclusion, payload round-trip
integrity, and LaTeX log cleanliness.  It writes a small audit report but does
not rerun experiments or alter manuscript sources.
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
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
ANONYMOUS_LOG = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.log"
PAYLOAD = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
READINESS = RESULTS / "summary_submission_readiness_audit.csv"
REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"
METADATA_VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
METADATA_PIPELINE_SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
PAYLOAD_ROUNDTRIP_MANIFEST = RESULTS / "manifest_payload_roundtrip_audit.json"
METADATA_STARTER = THIS_DIR / "make_submission_metadata_starter.py"
METADATA_FILE = THIS_DIR / "submission_package" / "submission_metadata.json"

PRIVATE_PAYLOAD_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}


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


def verify_pdf(path: Path, label: str) -> dict[str, str]:
    pages = pdf_pages(path)
    status = "pass" if pages not in {"missing", "unknown"} else "needs revision"
    return row(
        label,
        status,
        f"{rel(path)} pages={pages}, bytes={path.stat().st_size if path.exists() else 0}.",
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


def verify_claim_scope() -> dict[str, str]:
    manifest = read_json(CLAIM_SCOPE_MANIFEST)
    unresolved = int(manifest.get("unresolved_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    status = "pass" if unresolved == 0 else "needs revision"
    return row(
        "Claim-scope lint",
        status,
        f"unresolved_count={unresolved}; status_counts={counts}.",
        "Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims.",
    )


def verify_comparison_protocol() -> dict[str, str]:
    manifest = read_json(COMPARISON_PROTOCOL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    layers = manifest.get("layers", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Comparison protocol audit",
        status,
        f"layers={layers}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_comparison_protocol_audit.py and restore missing baseline-role, evidence, comparability, counterpoint, or manuscript anchors.",
    )


def verify_text_preview() -> dict[str, str]:
    manifest = read_json(TEXT_PREVIEW_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    ignored = bool(manifest.get("private_outputs_are_git_ignored", False))
    status = "pass" if manifest and ignored else "needs revision"
    return row(
        "Private submission text preview",
        status,
        f"status_counts={counts}; private_outputs_are_git_ignored={ignored}.",
        "Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git.",
    )


def verify_metadata_validator() -> dict[str, str]:
    manifest = read_json(METADATA_VALIDATOR_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Private metadata validator",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}.",
        "Run validate_submission_metadata.py and fix metadata format or consistency rows before upload.",
    )


def verify_metadata_starter_dry_run() -> dict[str, str]:
    before_exists = METADATA_FILE.exists()
    before_stat = METADATA_FILE.stat() if before_exists else None
    try:
        proc = subprocess.run(
            [sys.executable, str(METADATA_STARTER)],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        return row(
            "Metadata starter dry-run",
            "needs revision",
            f"starter execution failed: {exc}.",
            "Run make_submission_metadata_starter.py without --write-private and fix the exception.",
        )
    after_exists = METADATA_FILE.exists()
    after_stat = METADATA_FILE.stat() if after_exists else None
    private_created = after_exists and not before_exists
    private_modified = (
        before_stat is not None
        and after_stat is not None
        and (before_stat.st_mtime_ns, before_stat.st_size) != (after_stat.st_mtime_ns, after_stat.st_size)
    )
    expected_tokens = (
        "filled: code_availability.repository_url",
        "filled: code_availability.commit_hash",
        "dry run only",
    )
    missing_tokens = [token for token in expected_tokens if token not in proc.stdout]
    status = (
        "pass"
        if proc.returncode == 0 and not missing_tokens and not private_created and not private_modified
        else "needs revision"
    )
    return row(
        "Metadata starter dry-run",
        status,
        f"returncode={proc.returncode}; missing_tokens={missing_tokens or 'none'}; private_preexisting={before_exists}; private_created={private_created}; private_modified={private_modified}.",
        "Run make_submission_metadata_starter.py without --write-private and keep it read-only until author input is explicit.",
    )


def verify_metadata_pipeline_selftest() -> dict[str, str]:
    manifest = read_json(METADATA_PIPELINE_SELFTEST_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    synthetic_only = bool(manifest.get("uses_synthetic_metadata_only", False))
    writes_private_metadata = bool(manifest.get("writes_private_metadata", True))
    writes_private_preview = bool(manifest.get("writes_private_preview_files", True))
    status = (
        "pass"
        if manifest
        and needs_revision == 0
        and synthetic_only
        and not writes_private_metadata
        and not writes_private_preview
        else "needs revision"
    )
    return row(
        "Metadata pipeline self-test",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}; synthetic_only={synthetic_only}; writes_private_metadata={writes_private_metadata}; writes_private_preview_files={writes_private_preview}.",
        "Run selftest_submission_metadata_pipeline.py and keep the fixture synthetic and non-private.",
    )


def verify_anonymous_review_audit() -> dict[str, str]:
    manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    needs_author_input = int(manifest.get("needs_author_input_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Anonymous-review readiness audit",
        status,
        f"needs_revision_count={needs_revision}; needs_author_input_count={needs_author_input}; status_counts={counts}.",
        "Run analyze_anonymous_review_readiness.py and resolve needs-revision rows; double-blind conversion remains venue-dependent author input.",
    )


def verify_private_payload_exclusion() -> dict[str, str]:
    manifest = read_json(PAYLOAD_MANIFEST)
    files = manifest.get("files", []) if manifest else []
    leaked: list[str] = []
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            if Path(path).name in PRIVATE_PAYLOAD_BASENAMES:
                leaked.append(path)
    else:
        leaked.append("<payload manifest has invalid files list>")
    return row(
        "Private metadata payload exclusion",
        "pass" if manifest and not leaked else "needs revision",
        f"private_payload_hits={leaked or 'none'}; checked_basenames={sorted(PRIVATE_PAYLOAD_BASENAMES)}.",
        "Regenerate the payload after removing ignored private metadata or preview files from package inputs.",
    )


def verify_payload_roundtrip() -> dict[str, str]:
    manifest = read_json(PAYLOAD_ROUNDTRIP_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload round-trip audit",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}.",
        "Run analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues.",
    )


def verify_latex_log(path: Path, label: str) -> dict[str, str]:
    if not path.exists():
        return row(label, "needs revision", "LaTeX log is missing.", "Rebuild the PDF with latexmk.")
    bad_patterns = re.compile(r"Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun")
    allowed = (
        "Package: rerunfilecheck",
        r"LaTeX Warning: Command \showhyphens",
    )
    unexpected: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not bad_patterns.search(line):
            continue
        if any(token in line for token in allowed):
            continue
        unexpected.append(f"{lineno}:{line.strip()}")
    return row(
        label,
        "pass" if not unexpected else "needs revision",
        "Only allowed rerunfilecheck/showhyphens log lines found." if not unexpected else "; ".join(unexpected[:5]),
        "Inspect the LaTeX log and fix unexpected warnings or errors.",
    )


def build_rows() -> list[dict[str, str]]:
    rows = [
        verify_pdf(PDF, "Compiled author PDF"),
        verify_pdf(ANONYMOUS_PDF, "Compiled anonymous PDF"),
    ]
    rows.extend(verify_payload_sha())
    rows.extend(
        [
            verify_readiness(),
            verify_registry(),
            verify_claim_scope(),
            verify_comparison_protocol(),
            verify_metadata_starter_dry_run(),
            verify_metadata_validator(),
            verify_metadata_pipeline_selftest(),
            verify_anonymous_review_audit(),
            verify_text_preview(),
            verify_private_payload_exclusion(),
            verify_payload_roundtrip(),
            verify_latex_log(LOG, "Author LaTeX log boundary"),
            verify_latex_log(ANONYMOUS_LOG, "Anonymous LaTeX log boundary"),
        ]
    )
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
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
