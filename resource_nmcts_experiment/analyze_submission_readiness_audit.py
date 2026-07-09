#!/usr/bin/env python3
"""Audit the submission draft for paper-level readiness markers.

This does not judge scientific merit.  It checks whether the current LaTeX
submission draft exposes the elements reviewers and editors usually look for:
bounded claims, baseline fairness, reproducibility, availability, limitations,
and a clean compiled PDF.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
REBUILD_SCRIPT = THIS_DIR / "rebuild_submission_package.sh"
VERIFY_SCRIPT = THIS_DIR / "verify_submission_package.sh"
ARCHIVE_ANALYSIS = RESULTS / "analysis_submission_archive_manifest.md"
ARCHIVE_SUMMARY = RESULTS / "summary_submission_archive_manifest.csv"
ARCHIVE_MANIFEST = RESULTS / "manifest_submission_archive_manifest.json"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
AUTHOR_INPUT_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
PAYLOAD_ARCHIVE = SUBMISSION_PACKAGE / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA256 = SUBMISSION_PACKAGE / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
PAYLOAD_ANALYSIS = RESULTS / "analysis_submission_payload_archive.md"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
VERIFIER_ANALYSIS = RESULTS / "analysis_submission_package_verifier.md"
VERIFIER_SUMMARY = RESULTS / "summary_submission_package_verifier.csv"
VERIFIER_MANIFEST = RESULTS / "manifest_submission_package_verifier.json"
METADATA_ANALYSIS = RESULTS / "analysis_submission_metadata_audit.md"
METADATA_SUMMARY = RESULTS / "summary_submission_metadata_audit.csv"
METADATA_MANIFEST = RESULTS / "manifest_submission_metadata_audit.json"
METADATA_VALIDATOR_ANALYSIS = RESULTS / "analysis_submission_metadata_validator.md"
METADATA_VALIDATOR_SUMMARY = RESULTS / "summary_submission_metadata_validator.csv"
METADATA_VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_ANALYSIS = RESULTS / "analysis_submission_text_preview.md"
TEXT_PREVIEW_SUMMARY = RESULTS / "summary_submission_text_preview.csv"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
METADATA_PIPELINE_SELFTEST_ANALYSIS = RESULTS / "analysis_submission_metadata_pipeline_selftest.md"
METADATA_PIPELINE_SELFTEST_SUMMARY = RESULTS / "summary_submission_metadata_pipeline_selftest.csv"
METADATA_PIPELINE_SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_REVIEW_ANALYSIS = RESULTS / "analysis_anonymous_review_readiness.md"
ANONYMOUS_REVIEW_SUMMARY = RESULTS / "summary_anonymous_review_readiness.csv"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
GOAL_ANALYSIS = RESULTS / "analysis_goal_completion_audit.md"
GOAL_SUMMARY = RESULTS / "summary_goal_completion_audit.csv"
GOAL_MANIFEST = RESULTS / "manifest_goal_completion_audit.json"
CLAIM_SCOPE_ANALYSIS = RESULTS / "analysis_claim_scope_lint.md"
CLAIM_SCOPE_SUMMARY = RESULTS / "summary_claim_scope_lint.csv"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
RERUN_REGISTRY_ANALYSIS = RESULTS / "analysis_artifact_rerun_registry.md"
RERUN_REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
RERUN_REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
RERUN_REGISTRY_TABLE = THIS_DIR / "paper_latex" / "tables" / "artifact_rerun_registry.tex"
SUPPORT_FILES = [
    SUBMISSION_PACKAGE / "README.md",
    AUTHOR_INPUT_PACKET,
    SUBMISSION_PACKAGE / "artifact_reproduction_guide.md",
    SUBMISSION_PACKAGE / "cover_letter_template.md",
    SUBMISSION_PACKAGE / "author_declarations_template.md",
    SUBMISSION_PACKAGE / "submission_checklist.md",
    SUBMISSION_PACKAGE / "reviewer_concern_brief.md",
    SUBMISSION_PACKAGE / "editor_screening_brief.md",
    SUBMISSION_PACKAGE / "target_venue_brief.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def abstract_word_count(text: str) -> int:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, flags=re.DOTALL)
    if not match:
        return 0
    abstract = match.group(1)
    abstract = re.sub(r"\\[a-zA-Z]+(?:\{[^{}]*\})?", " ", abstract)
    abstract = re.sub(r"[^A-Za-z0-9.%/-]+", " ", abstract)
    return len([word for word in abstract.split() if word])


def build_rows() -> list[dict[str, str]]:
    text = read_text(PAPER)
    pages = pdf_pages(PDF)
    claim_scope_manifest = read_json(CLAIM_SCOPE_MANIFEST)
    claim_scope_unresolved = int(claim_scope_manifest.get("unresolved_count", -1)) if claim_scope_manifest else -1
    text_preview_manifest = read_json(TEXT_PREVIEW_MANIFEST)
    text_preview_counts = text_preview_manifest.get("status_counts", {}) if text_preview_manifest else {}
    private_outputs_ignored = bool(text_preview_manifest.get("private_outputs_are_git_ignored", False))
    metadata_validator_manifest = read_json(METADATA_VALIDATOR_MANIFEST)
    metadata_validator_revisions = int(metadata_validator_manifest.get("needs_revision_count", -1)) if metadata_validator_manifest else -1
    metadata_validator_counts = metadata_validator_manifest.get("status_counts", {}) if metadata_validator_manifest else {}
    metadata_selftest_manifest = read_json(METADATA_PIPELINE_SELFTEST_MANIFEST)
    metadata_selftest_revisions = int(metadata_selftest_manifest.get("needs_revision_count", -1)) if metadata_selftest_manifest else -1
    metadata_selftest_counts = metadata_selftest_manifest.get("status_counts", {}) if metadata_selftest_manifest else {}
    metadata_selftest_synthetic = bool(metadata_selftest_manifest.get("uses_synthetic_metadata_only", False))
    metadata_selftest_writes_private = bool(metadata_selftest_manifest.get("writes_private_metadata", True)) or bool(
        metadata_selftest_manifest.get("writes_private_preview_files", True)
    )
    anonymous_manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    anonymous_counts = anonymous_manifest.get("status_counts", {}) if anonymous_manifest else {}
    anonymous_revisions = int(anonymous_manifest.get("needs_revision_count", -1)) if anonymous_manifest else -1
    anonymous_author_input = int(anonymous_manifest.get("needs_author_input_count", -1)) if anonymous_manifest else -1
    lower = text.lower()
    todo_hits = re.findall(r"\b(?:todo|tbd|placeholder)\b", lower)
    abstract_words = abstract_word_count(text)
    rebuild_cited = "rebuild_submission_package.sh" in text or r"rebuild\_submission\_package.sh" in text

    rows = [
        {
            "item": "Bounded abstract claim",
            "status": "pass"
            if contains_all(text, [r"\begin{abstract}", "logical-layer", "not a hardware-mapped"])
            else "needs revision",
            "evidence": "Abstract states logical-layer scope and excludes hardware-mapped/depth-only claims.",
            "next_action": "Keep hardware and mapping claims out of the abstract unless new evidence is added.",
        },
        {
            "item": "Abstract concision",
            "status": "pass" if 180 <= abstract_words <= 320 else "needs revision",
            "evidence": f"Abstract word count is {abstract_words}.",
            "next_action": "Keep the abstract compact; detailed per-baseline numbers belong in Results tables.",
        },
        {
            "item": "First-pages scope and assumptions",
            "status": "pass"
            if contains_all(
                text,
                [
                    "Scope and assumptions",
                    "logical-layer Boolean-oracle synthesis",
                    "hardware mapping",
                    "baseline comparability audit",
                    "universal leaderboard",
                ],
            )
            else "needs revision",
            "evidence": "Introduction states the logical-layer scope, excluded hardware assumptions, score role, and comparison boundary.",
            "next_action": "Keep the scope and assumptions visible in the first pages after venue-specific template conversion.",
        },
        {
            "item": "Contribution-to-evidence chain",
            "status": "pass" if "tab:contribution-map" in text else "needs revision",
            "evidence": "Introduction includes a contribution-to-evidence map.",
            "next_action": "Update the map whenever a headline contribution changes.",
        },
        {
            "item": "Executable method workflow",
            "status": "pass" if "tab:method-workflow" in text else "needs revision",
            "evidence": "Method includes an end-to-end synthesis and verification workflow table.",
            "next_action": "Keep the workflow table aligned with new candidate generators or verification stages.",
        },
        {
            "item": "Baseline fairness and scope",
            "status": "pass"
            if contains_all(text, ["tab:baseline-claim-matrix", "tab:evidence-matrix", "tab:comparability-audit"])
            else "needs revision",
            "evidence": "Experimental design includes claim, evidence, and comparability matrices.",
            "next_action": "Keep cross-toolchain claims tied to the comparability audit.",
        },
        {
            "item": "Claim-scope lint",
            "status": "pass"
            if CLAIM_SCOPE_ANALYSIS.exists()
            and CLAIM_SCOPE_SUMMARY.exists()
            and CLAIM_SCOPE_MANIFEST.exists()
            and claim_scope_unresolved == 0
            else "needs revision",
            "evidence": f"Claim-scope lint scans manuscript and handoff files; unresolved_count={claim_scope_unresolved}.",
            "next_action": "Rerun analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims.",
        },
        {
            "item": "Reproducibility evidence",
            "status": "pass" if "tab:reproducibility" in text else "needs revision",
            "evidence": "Manuscript includes compute, worker, artifact, and external-tool provenance table.",
            "next_action": "Rerun analyze_reproducibility_audit.py after adding scripts, tables, or figures.",
        },
        {
            "item": "Raw rerun registry",
            "status": "pass"
            if RERUN_REGISTRY_ANALYSIS.exists()
            and RERUN_REGISTRY_SUMMARY.exists()
            and RERUN_REGISTRY_MANIFEST.exists()
            and RERUN_REGISTRY_TABLE.exists()
            else "needs revision",
            "evidence": "Artifact rerun registry maps evidence families to driver scripts, raw CSV coverage, manifests, rerun tiers, and dependency boundaries.",
            "next_action": "Rerun analyze_artifact_rerun_registry.py after adding raw data families, run scripts, or external-tool probes.",
        },
        {
            "item": "Claim-to-artifact traceability",
            "status": "pass" if "tab:traceability-audit" in text else "needs revision",
            "evidence": "Manuscript includes a submission traceability audit linking claim families to scripts, data, tables, and figures.",
            "next_action": "Rerun analyze_submission_traceability_audit.py after adding or moving headline evidence.",
        },
        {
            "item": "Archive package manifest",
            "status": "pass"
            if contains_all(text, ["tab:archive-manifest", "submission archive manifest"])
            and ARCHIVE_ANALYSIS.exists()
            and ARCHIVE_SUMMARY.exists()
            and ARCHIVE_MANIFEST.exists()
            else "needs revision",
            "evidence": "Manuscript includes an archive-level payload manifest with generated CSV, Markdown, and JSON outputs.",
            "next_action": "Rerun analyze_submission_archive_manifest.py after adding tables, figures, scripts, models, or result files.",
        },
        {
            "item": "Submission support templates",
            "status": "pass" if all(path.exists() for path in SUPPORT_FILES) else "needs revision",
            "evidence": "Package README, author-input packet, artifact guide, cover letter, author declarations, upload checklist, reviewer-concern brief, editor-screening brief, and target-venue brief are present.",
            "next_action": "Fill the author-specific fields before journal upload.",
        },
        {
            "item": "Submission metadata audit",
            "status": "pass"
            if METADATA_ANALYSIS.exists() and METADATA_SUMMARY.exists() and METADATA_MANIFEST.exists()
            else "needs revision",
            "evidence": "Author- and venue-specific metadata fields are enumerated in CSV, Markdown, and JSON audit outputs.",
            "next_action": "Rerun analyze_submission_metadata_audit.py after filling author declarations or choosing a target venue.",
        },
        {
            "item": "Submission metadata validator",
            "status": "pass"
            if METADATA_VALIDATOR_ANALYSIS.exists()
            and METADATA_VALIDATOR_SUMMARY.exists()
            and METADATA_VALIDATOR_MANIFEST.exists()
            and metadata_validator_revisions == 0
            else "needs revision",
            "evidence": f"Private metadata format validator exists; status_counts={metadata_validator_counts}; needs_revision_count={metadata_validator_revisions}.",
            "next_action": "Rerun validate_submission_metadata.py after filling private metadata; fix format or consistency rows before upload.",
        },
        {
            "item": "Submission metadata pipeline self-test",
            "status": "pass"
            if METADATA_PIPELINE_SELFTEST_ANALYSIS.exists()
            and METADATA_PIPELINE_SELFTEST_SUMMARY.exists()
            and METADATA_PIPELINE_SELFTEST_MANIFEST.exists()
            and metadata_selftest_revisions == 0
            and metadata_selftest_synthetic
            and not metadata_selftest_writes_private
            else "needs revision",
            "evidence": f"Synthetic metadata self-test exercises validator and preview renderers; status_counts={metadata_selftest_counts}; needs_revision_count={metadata_selftest_revisions}; synthetic_only={metadata_selftest_synthetic}; writes_private_outputs={metadata_selftest_writes_private}.",
            "next_action": "Rerun selftest_submission_metadata_pipeline.py after changing required metadata paths, validators, or preview renderers.",
        },
        {
            "item": "Private submission text preview",
            "status": "pass"
            if TEXT_PREVIEW_ANALYSIS.exists()
            and TEXT_PREVIEW_SUMMARY.exists()
            and TEXT_PREVIEW_MANIFEST.exists()
            and private_outputs_ignored
            else "needs revision",
            "evidence": f"Private preview generator audit exists; status_counts={text_preview_counts}; private_outputs_are_git_ignored={private_outputs_ignored}.",
            "next_action": "Rerun make_submission_text_preview.py after filling private metadata; generated_*.md files must remain ignored by Git.",
        },
        {
            "item": "Anonymous-review readiness path",
            "status": "pass"
            if ANONYMOUS_REVIEW_ANALYSIS.exists()
            and ANONYMOUS_REVIEW_SUMMARY.exists()
            and ANONYMOUS_REVIEW_MANIFEST.exists()
            and anonymous_revisions == 0
            else "needs revision",
            "evidence": f"Anonymous-review audit exists; status_counts={anonymous_counts}; needs_revision_count={anonymous_revisions}; needs_author_input_count={anonymous_author_input}.",
            "next_action": "If the selected venue requires double-blind review, produce an anonymized manuscript copy and anonymous artifact links before upload.",
        },
        {
            "item": "Goal completion audit",
            "status": "pass"
            if GOAL_ANALYSIS.exists() and GOAL_SUMMARY.exists() and GOAL_MANIFEST.exists()
            else "needs revision",
            "evidence": "The original project objective is mapped to concrete evidence files, boundaries, and remaining author-gated items.",
            "next_action": "Rerun analyze_goal_completion_audit.py after adding major evidence or filling author/venue metadata.",
        },
        {
            "item": "Uploadable payload archive",
            "status": "pass"
            if PAYLOAD_ARCHIVE.exists()
            and PAYLOAD_SHA256.exists()
            and PAYLOAD_ANALYSIS.exists()
            and PAYLOAD_SUMMARY.exists()
            and PAYLOAD_MANIFEST.exists()
            else "needs revision",
            "evidence": "Deterministic submission payload tarball, SHA256 sidecar, CSV, Markdown, and JSON manifest are present.",
            "next_action": "Rerun make_submission_payload_archive.py after adding or removing upload payload files.",
        },
        {
            "item": "Terminal package verifier",
            "status": "pass"
            if VERIFY_SCRIPT.exists()
            and VERIFIER_ANALYSIS.exists()
            and VERIFIER_SUMMARY.exists()
            and VERIFIER_MANIFEST.exists()
            else "needs revision",
            "evidence": "Fast pre-upload verifier script and read-only verifier outputs check PDF availability, payload SHA consistency, readiness state, raw registry coverage, claim-scope lint, private metadata validation, metadata-pipeline self-test, anonymous-review readiness, private-preview protection, private payload exclusion, and LaTeX log boundaries.",
            "next_action": "Run verify_submission_package.sh after rebuilding the payload archive.",
        },
        {
            "item": "Derived package rebuild command",
            "status": "pass" if REBUILD_SCRIPT.exists() and rebuild_cited else "needs revision",
            "evidence": "A lightweight rebuild script is present and cited in Data and Code Availability.",
            "next_action": "Keep the rebuild script aligned with paper-facing analysis, figure, audit, and PDF outputs.",
        },
        {
            "item": "Limitations and failure modes",
            "status": "pass"
            if contains_all(text, ["Several limitations are deliberate", "full ROS reproduction", "not a hardware mapping"])
            else "needs revision",
            "evidence": "Discussion names logical-layer, ROS-proxy, RevKit-derived, and high-dimensional bridge boundaries.",
            "next_action": "Add any new negative result to Discussion rather than hiding it in tables.",
        },
        {
            "item": "Data and code availability",
            "status": "pass" if "Data and Code Availability" in text else "needs revision",
            "evidence": "Manuscript has an availability section pointing to scripts, CSVs, manifests, tables, and figures.",
            "next_action": "Replace repository-relative wording with an archival DOI or anonymous link at submission time if required.",
        },
        {
            "item": "Clean submission source",
            "status": "pass" if not todo_hits else "needs revision",
            "evidence": f"{len(todo_hits)} TODO/TBD/placeholder markers in submission TeX.",
            "next_action": "Remove all source placeholders before journal upload.",
        },
        {
            "item": "Compiled PDF artifact",
            "status": "pass" if pages not in {"missing", "unknown"} else "needs revision",
            "evidence": f"Compiled PDF detected with {pages} pages.",
            "next_action": "Run latexmk and visual spot checks after each table or figure change.",
        },
        {
            "item": "Author-specific declarations",
            "status": "needs author input",
            "evidence": "Funding, acknowledgements, author metadata, competing interests, target-venue fields, and final archival links are author-specific even though templates, metadata audit, and goal-completion audit are prepared.",
            "next_action": "Complete `submission_package/author_declarations_template.md`, update the cover letter/checklist, and replace repository-relative availability links at the target journal's submission step.",
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Readiness Audit",
        "",
        "This audit checks paper-level readiness markers in `paper_latex/resource_nmcts_submission_v1.tex` and the compiled PDF.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| item | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_readiness_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_readiness_audit.md", rows)
    print(f"wrote {RESULTS / 'summary_submission_readiness_audit.csv'}")
    print(f"wrote {RESULTS / 'analysis_submission_readiness_audit.md'}")


if __name__ == "__main__":
    main()
