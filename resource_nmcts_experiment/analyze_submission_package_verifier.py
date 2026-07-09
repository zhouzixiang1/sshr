#!/usr/bin/env python3
"""Read-only verifier for the current submission package.

The verifier runs after the payload archive has been created.  It checks the
terminal package invariants that are easy to regress during final polishing:
compiled PDF availability, payload SHA consistency, readiness status, raw rerun
registry coverage, claim-scope hygiene, comparison-protocol coverage,
search-control baseline coverage,
editorial screening support,
submission support packet coverage,
ROS reproduction-boundary support,
citation support,
headline-numeric consistency,
figure-asset coverage,
LaTeX dependency closure,
PDF visual rendering,
PDF text/searchability,
PDF metadata/privacy,
source/path privacy,
private-metadata starter dry-run, private-metadata validation,
synthetic metadata-pipeline self-testing, anonymous-review decision support,
author-input closure,
private-preview protection, private payload exclusion, payload round-trip
integrity, extracted-payload smoke checks, extracted-payload LaTeX compilation,
extracted-payload verifier smoke,
and LaTeX log cleanliness.  It
writes a small audit report but does not rerun experiments or alter manuscript
sources.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
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
COMPARISON_PROTOCOL_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_protocol_audit.tex"
ROS_GAP_MANIFEST = RESULTS / "manifest_ros_reproduction_gap_audit.json"
SCHEDULE_PROXY_MANIFEST = RESULTS / "manifest_schedule_proxy_audit.json"
SCHEDULE_PROXY_TABLE = THIS_DIR / "paper_latex" / "tables" / "schedule_proxy_audit.tex"
SEARCH_CONTROL_MANIFEST = RESULTS / "manifest_search_control_baseline_audit.json"
EDITORIAL_SCREENING_MANIFEST = RESULTS / "manifest_editorial_screening_audit.json"
SUPPORT_PACKET_MANIFEST = RESULTS / "manifest_submission_support_packet_audit.json"
CITATION_SUPPORT_MANIFEST = RESULTS / "manifest_citation_support_audit.json"
HEADLINE_NUMERIC_MANIFEST = RESULTS / "manifest_headline_numeric_consistency.json"
FIGURE_ASSET_MANIFEST = RESULTS / "manifest_figure_asset_audit.json"
LATEX_DEPENDENCY_MANIFEST = RESULTS / "manifest_latex_dependency_audit.json"
PDF_VISUAL_MANIFEST = RESULTS / "manifest_pdf_visual_audit.json"
PDF_TEXT_MANIFEST = RESULTS / "manifest_pdf_text_audit.json"
PDF_METADATA_MANIFEST = RESULTS / "manifest_pdf_metadata_audit.json"
SOURCE_PATH_PRIVACY_MANIFEST = RESULTS / "manifest_source_path_privacy_audit.json"
METADATA_VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
METADATA_PIPELINE_SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
AUTHOR_INPUT_CLOSURE_MANIFEST = RESULTS / "manifest_author_input_closure_audit.json"
METADATA_CLOSURE_MANIFEST = RESULTS / "manifest_submission_metadata_closure_path.json"
PAYLOAD_ROUNDTRIP_MANIFEST = RESULTS / "manifest_payload_roundtrip_audit.json"
PAYLOAD_EXTRACTION_SMOKE_MANIFEST = RESULTS / "manifest_payload_extraction_smoke_audit.json"
PAYLOAD_VERIFIER_SMOKE_MANIFEST = RESULTS / "manifest_payload_verifier_smoke_audit.json"
PAYLOAD_LATEX_COMPILE_MANIFEST = RESULTS / "manifest_payload_latex_compile_audit.json"
METADATA_STARTER = THIS_DIR / "make_submission_metadata_starter.py"
METADATA_FILE = THIS_DIR / "submission_package" / "submission_metadata.json"

PRIVATE_PAYLOAD_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


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
    if EXTRACTED_PAYLOAD_MODE and not PAYLOAD.exists():
        manifest = read_json(PAYLOAD_MANIFEST)
        return [
            row(
                "Payload archive self-check",
                "pass",
                f"extracted_payload_mode=1; archive_absent_by_design={not PAYLOAD.exists()}; manifest_file_count={manifest.get('file_count', 'missing') if manifest else 'missing'}.",
                "Run the full payload SHA and archive round-trip checks from the source worktree before distributing the tarball.",
            )
        ]
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
    if EXTRACTED_PAYLOAD_MODE and not READINESS.exists():
        return row(
            "Readiness audit terminal state",
            "pass",
            "extracted_payload_mode=1; readiness summary is a source-worktree terminal audit and is intentionally excluded from the upload payload.",
            "Run analyze_submission_readiness_audit.py in the source worktree after rebuilding the payload.",
        )
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
        f"status_counts={counts}; terminal_verifier_self_row_excluded=True.",
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
    table_exists = COMPARISON_PROTOCOL_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Comparison protocol audit",
        status,
        f"layers={layers}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_comparison_protocol_audit.py and restore missing baseline-role, evidence, comparability, counterpoint, or manuscript anchors.",
    )


def verify_ros_gap() -> dict[str, str]:
    manifest = read_json(ROS_GAP_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    coverage = manifest.get("coverage_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    boundary_explicit = bool(manifest.get("full_ros_boundary_is_explicit", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and full_ros is False and boundary_explicit else "needs revision"
    return row(
        "ROS reproduction gap audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; coverage_counts={coverage}; official_ros_fully_reproduced={full_ros}; full_ros_boundary_is_explicit={boundary_explicit}.",
        "Run analyze_ros_lut_line_sensitivity.py and analyze_ros_reproduction_gap_audit.py and restore ROS proxy/full-reproduction boundary anchors.",
    )


def verify_schedule_proxy() -> dict[str, str]:
    manifest = read_json(SCHEDULE_PROXY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = SCHEDULE_PROXY_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Schedule-proxy tradeoff audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_schedule_metrics.py and analyze_schedule_proxy_audit.py and restore schedule-proxy table anchors.",
    )


def verify_search_control() -> dict[str, str]:
    manifest = read_json(SEARCH_CONTROL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Search-control baseline audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_search_control_baseline_audit.py and restore heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, and phase random-control evidence rows.",
    )


def verify_editorial_screening() -> dict[str, str]:
    manifest = read_json(EDITORIAL_SCREENING_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Editorial screening audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_editorial_screening_audit.py and restore scope, novelty, comparison, counterpoint, AI-boundary, scale-boundary, reproducibility, author-gate, or editor-reading anchors.",
    )


def verify_support_packet() -> dict[str, str]:
    manifest = read_json(SUPPORT_PACKET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Submission support packet audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_submission_support_packet_audit.py and restore cover-letter, declaration, venue, checklist, handoff, anonymous-review, private-preview, or editor/reviewer support anchors.",
    )


def verify_citation_support() -> dict[str, str]:
    manifest = read_json(CITATION_SUPPORT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    cited_keys = manifest.get("cited_key_count", "missing") if manifest else "missing"
    bib_keys = manifest.get("bib_key_count", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Citation support audit",
        status,
        f"rows={rows}; cited_keys={cited_keys}; bib_keys={bib_keys}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_citation_support_audit.py and restore missing citations, BibTeX entries, or reference locators.",
    )


def verify_headline_numeric() -> dict[str, str]:
    manifest = read_json(HEADLINE_NUMERIC_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    claims = manifest.get("claims", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Headline numeric consistency",
        status,
        f"claims={claims}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_headline_numeric_consistency.py and align abstract tokens with CSV-derived evidence.",
    )


def verify_figure_assets() -> dict[str, str]:
    manifest = read_json(FIGURE_ASSET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    figures = manifest.get("figures", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Figure asset audit",
        status,
        f"figures={figures}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run make_submission_figures.py and analyze_figure_asset_audit.py to restore referenced PDF/PNG/SVG assets and source-data CSVs.",
    )


def verify_latex_dependencies() -> dict[str, str]:
    manifest = read_json(LATEX_DEPENDENCY_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "LaTeX dependency audit",
            "pass",
            "extracted_payload_mode=1; LaTeX dependency terminal manifest is intentionally excluded from the upload payload.",
            "Run analyze_latex_dependency_audit.py from the source worktree after rebuilding the payload archive.",
        )
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    dependencies = manifest.get("dependency_count", "missing") if manifest else "missing"
    type_counts = manifest.get("dependency_type_counts", {}) if manifest else {}
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "LaTeX dependency audit",
        status,
        f"dependencies={dependencies}; type_counts={type_counts}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_latex_dependency_audit.py after payload creation and restore missing TeX, table, figure, bibliography, or payload entries.",
    )


def verify_pdf_visual() -> dict[str, str]:
    manifest = read_json(PDF_VISUAL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF visual render audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_visual_audit.py and inspect rendered PDF pages for blank, clipped, or overfilled output.",
    )


def verify_pdf_text() -> dict[str, str]:
    manifest = read_json(PDF_TEXT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    anchors = manifest.get("required_anchor_count", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF text/searchability audit",
        status,
        f"rows={rows}; required_anchors={anchors}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_text_audit.py and inspect pdftotext output for missing anchors, identity leaks, or placeholder remnants.",
    )


def verify_pdf_metadata() -> dict[str, str]:
    manifest = read_json(PDF_METADATA_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF metadata/privacy audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_metadata_audit.py and inspect pdfinfo metadata for privacy leaks, encryption, JavaScript, forms, or page-geometry drift.",
    )


def verify_source_path_privacy() -> dict[str, str]:
    manifest = read_json(SOURCE_PATH_PRIVACY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    payload_local_path_files = manifest.get("payload_local_path_files", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Source/path privacy audit",
        status,
        f"rows={rows}; payload_local_path_files={payload_local_path_files}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_source_path_privacy_audit.py and move local paths out of manuscript/support sources while keeping toolchain paths only in provenance outputs.",
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
    expected_tokens = ("dry run only",) if EXTRACTED_PAYLOAD_MODE else (
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


def verify_author_input_closure() -> dict[str, str]:
    manifest = read_json(AUTHOR_INPUT_CLOSURE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_metadata_paths", "missing") if manifest else "missing"
    metadata_present = bool(manifest.get("metadata_present", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Author-input closure audit",
        status,
        f"needs_revision_count={needs_revision}; required_metadata_paths={required_paths}; metadata_present={metadata_present}; status_counts={counts}.",
        "Run analyze_author_input_closure_audit.py and restore author-packet coverage, private metadata protection, or support-document visibility.",
    )


def verify_metadata_closure_path() -> dict[str, str]:
    manifest = read_json(METADATA_CLOSURE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_metadata_paths", "missing") if manifest else "missing"
    metadata_present = bool(manifest.get("metadata_present", False)) if manifest else False
    ready = bool(manifest.get("closure_path_ready", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 and ready else "needs revision"
    return row(
        "Submission metadata closure path",
        status,
        f"needs_revision_count={needs_revision}; required_metadata_paths={required_paths}; metadata_present={metadata_present}; closure_path_ready={ready}; status_counts={counts}.",
        "Run analyze_submission_metadata_closure_path.py and keep the final author/venue metadata path explicit, ignored, and machine-checkable.",
    )


def verify_private_payload_exclusion() -> dict[str, str]:
    manifest = read_json(PAYLOAD_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Private metadata payload exclusion",
            "pass",
            f"extracted_payload_mode=1; payload manifest is intentionally excluded from the upload payload; checked_basenames={sorted(PRIVATE_PAYLOAD_BASENAMES)}.",
            "Run make_submission_payload_archive.py and analyze_payload_roundtrip_audit.py from the source worktree before distributing the tarball.",
        )
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
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload round-trip audit",
            "pass",
            "extracted_payload_mode=1; archive round-trip manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_roundtrip_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload round-trip audit",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}.",
        "Run analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues.",
    )


def verify_payload_extraction_smoke() -> dict[str, str]:
    manifest = read_json(PAYLOAD_EXTRACTION_SMOKE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload extraction smoke audit",
            "pass",
            "extracted_payload_mode=1; extraction-smoke terminal manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_extraction_smoke_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    smoke_scripts = manifest.get("smoke_scripts", []) if manifest else []
    script_count = len(smoke_scripts) if isinstance(smoke_scripts, list) else "invalid"
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload extraction smoke audit",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}; smoke_scripts={script_count}.",
        "Run analyze_payload_extraction_smoke_audit.py after payload creation and fix extracted-payload script failures.",
    )


def verify_payload_verifier_smoke() -> dict[str, str]:
    manifest = read_json(PAYLOAD_VERIFIER_SMOKE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload verifier smoke audit",
            "pass",
            "extracted_payload_mode=1; verifier-smoke terminal manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_verifier_smoke_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    verifier_returncode = manifest.get("verifier_returncode", "missing") if manifest else "missing"
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload verifier smoke audit",
        status,
        f"needs_revision_count={needs_revision}; verifier_returncode={verifier_returncode}; rows={rows}; status_counts={counts}.",
        "Run analyze_payload_verifier_smoke_audit.py after payload creation and fix extracted one-command verifier failures.",
    )


def verify_payload_latex_compile() -> dict[str, str]:
    manifest = read_json(PAYLOAD_LATEX_COMPILE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload LaTeX compile audit",
            "pass",
            "extracted_payload_mode=1; extracted-payload LaTeX compile manifest is intentionally excluded from the upload payload.",
            "Run analyze_payload_latex_compile_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    compiled = manifest.get("compiled_manuscripts", "missing") if manifest else "missing"
    try:
        compiled_count = int(compiled)
    except Exception:
        compiled_count = -1
    status = "pass" if manifest and needs_revision == 0 and compiled_count >= 2 else "needs revision"
    return row(
        "Payload LaTeX compile audit",
        status,
        f"needs_revision_count={needs_revision}; compiled_manuscripts={compiled}; status_counts={counts}.",
        "Run analyze_payload_latex_compile_audit.py and restore missing extracted-payload TeX, table, figure, or bibliography dependencies.",
    )


def verify_latex_log(path: Path, label: str) -> dict[str, str]:
    if not path.exists():
        if EXTRACTED_PAYLOAD_MODE:
            return row(
                label,
                "pass",
                "extracted_payload_mode=1; LaTeX logs are intentionally excluded from the upload payload while the compiled PDF is present.",
                "Run latexmk and the local verifier from the source worktree to inspect full LaTeX logs.",
            )
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
            verify_ros_gap(),
            verify_schedule_proxy(),
            verify_search_control(),
            verify_editorial_screening(),
            verify_support_packet(),
            verify_citation_support(),
            verify_headline_numeric(),
            verify_figure_assets(),
            verify_latex_dependencies(),
            verify_pdf_visual(),
            verify_pdf_text(),
            verify_pdf_metadata(),
            verify_source_path_privacy(),
            verify_metadata_starter_dry_run(),
            verify_metadata_validator(),
            verify_metadata_pipeline_selftest(),
            verify_anonymous_review_audit(),
            verify_author_input_closure(),
            verify_metadata_closure_path(),
            verify_text_preview(),
            verify_private_payload_exclusion(),
            verify_payload_roundtrip(),
            verify_payload_extraction_smoke(),
            verify_payload_verifier_smoke(),
            verify_payload_latex_compile(),
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
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "extracted_payload_mode": EXTRACTED_PAYLOAD_MODE,
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "needs_revision_count": failures,
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
