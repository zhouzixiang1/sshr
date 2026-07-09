#!/usr/bin/env python3
"""Audit uploadable artifact bundles for the final submission path.

This terminal audit answers a practical last-mile question: after the target
venue is chosen, which files are ready to upload, which files are local-only,
and which boundary applies to each bundle?  It does not fill or infer private
author metadata.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex"
SUBMISSION = THIS_DIR / "submission_package"
DIST = SUBMISSION / "dist"

AUTHOR_TEX = PAPER / "resource_nmcts_submission_v1.tex"
AUTHOR_PDF = PAPER / "resource_nmcts_submission_v1.pdf"
ANON_TEX = PAPER / "resource_nmcts_submission_anonymous.tex"
ANON_PDF = PAPER / "resource_nmcts_submission_anonymous.pdf"
ACM_TEX = PAPER / "resource_nmcts_submission_acm_tqc.tex"
ACM_PDF = PAPER / "resource_nmcts_submission_acm_tqc.pdf"
BIB = PAPER / "references.bib"
PAYLOAD = DIST / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA = DIST / "resource_nmcts_submission_payload.tar.gz.sha256"

README = SUBMISSION / "README.md"
CHECKLIST = SUBMISSION / "submission_checklist.md"
AUTHOR_INPUT = SUBMISSION / "AUTHOR_INPUT_REQUIRED.md"
LAST_MILE = SUBMISSION / "LAST_MILE_ACTION_CARD_zh.md"
FINAL_HANDOFF = SUBMISSION / "FINAL_SUBMISSION_HANDOFF_zh.md"
COVER_TEMPLATE = SUBMISSION / "cover_letter_template.md"
DECLARATIONS_TEMPLATE = SUBMISSION / "author_declarations_template.md"
METADATA_TEMPLATE = SUBMISSION / "submission_metadata_template.json"
ANSWERS_TEMPLATE = SUBMISSION / "submission_metadata_answers_template.json"

PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
PAYLOAD_GIT_POLICY = RESULTS / "manifest_payload_git_policy_audit.json"
PAYLOAD_ROUNDTRIP = RESULTS / "manifest_payload_roundtrip_audit.json"
PAYLOAD_EXTRACTION_SMOKE = RESULTS / "manifest_payload_extraction_smoke_audit.json"
PAYLOAD_VERIFIER_SMOKE = RESULTS / "manifest_payload_verifier_smoke_audit.json"
PAYLOAD_LATEX_COMPILE = RESULTS / "manifest_payload_latex_compile_audit.json"
PDF_VISUAL = RESULTS / "manifest_pdf_visual_audit.json"
PDF_TEXT = RESULTS / "manifest_pdf_text_audit.json"
PDF_METADATA = RESULTS / "manifest_pdf_metadata_audit.json"
LATEX_DEPENDENCY = RESULTS / "manifest_latex_dependency_audit.json"
ANONYMOUS_REVIEW = RESULTS / "manifest_anonymous_review_readiness.json"
TARGET_FORMAT = RESULTS / "manifest_target_venue_format_smoke.json"
TARGET_DECISION = RESULTS / "manifest_target_venue_decision_audit.json"
SUPPORT_PACKET = RESULTS / "manifest_submission_support_packet_audit.json"
SOURCE_PRIVACY = RESULTS / "manifest_source_path_privacy_audit.json"
FINAL_UPLOAD_SEQUENCE = RESULTS / "manifest_final_upload_sequence_audit.json"
FINAL_HUMAN_GATE = RESULTS / "manifest_final_human_gate_audit.json"

PRIVATE_BASENAMES = {
    "submission_metadata_answers.json",
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}

SUMMARY = RESULTS / "summary_upload_bundle_matrix_audit.csv"
ANALYSIS = RESULTS / "analysis_upload_bundle_matrix_audit.md"
MANIFEST = RESULTS / "manifest_upload_bundle_matrix_audit.json"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def manifest_revisions(path: Path) -> int:
    data = read_json(path)
    try:
        return int(data.get("needs_revision_count", -1))
    except Exception:
        return -1


def manifest_value(path: Path, key: str, default: object = "missing") -> object:
    return read_json(path).get(key, default)


def status_counts(path: Path) -> dict[str, object]:
    counts = read_json(path).get("status_counts", {})
    return counts if isinstance(counts, dict) else {}


def existing(paths: tuple[Path, ...]) -> tuple[bool, list[str]]:
    missing = [rel(path) for path in paths if not path.exists()]
    return not missing, missing


def payload_paths() -> set[str]:
    manifest = read_json(PAYLOAD_MANIFEST)
    files = manifest.get("files", [])
    out: set[str] = set()
    if isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                out.add(item["path"])
    return out


def payload_private_hits() -> list[str]:
    hits: list[str] = []
    for path in payload_paths():
        if Path(path).name in PRIVATE_BASENAMES:
            hits.append(path)
    return sorted(hits)


def token_missing(path: Path, tokens: tuple[str, ...]) -> list[str]:
    text = read_text(path)
    return [token for token in tokens if token not in text]


def row(
    bundle: str,
    status: str,
    upload_use: str,
    files: tuple[Path, ...],
    evidence: str,
    boundary: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "bundle": bundle,
        "status": status,
        "upload_use": upload_use,
        "files": "; ".join(rel(path) for path in files),
        "evidence": evidence,
        "boundary": boundary,
        "next_action": next_action,
    }


def build_rows() -> list[dict[str, str]]:
    payload_file_set = payload_paths()

    author_files = (AUTHOR_PDF, AUTHOR_TEX, BIB)
    author_exists, author_missing = existing(author_files)
    author_ok = (
        author_exists
        and manifest_revisions(PDF_VISUAL) == 0
        and manifest_revisions(PDF_TEXT) == 0
        and manifest_revisions(PDF_METADATA) == 0
        and manifest_revisions(LATEX_DEPENDENCY) == 0
    )

    anon_files = (ANON_PDF, ANON_TEX, BIB)
    anon_exists, anon_missing = existing(anon_files)
    anon_counts = status_counts(ANONYMOUS_REVIEW)
    anon_ok = anon_exists and manifest_revisions(ANONYMOUS_REVIEW) == 0 and anon_counts.get("pass", 0) >= 3

    acm_files = (ACM_PDF, ACM_TEX, BIB)
    acm_exists, acm_missing = existing(acm_files)
    acm_ok = acm_exists and manifest_revisions(TARGET_FORMAT) == 0

    payload_files = (PAYLOAD, PAYLOAD_SHA)
    payload_exists, payload_missing = existing(payload_files)
    payload_ok = (
        payload_exists
        and manifest_revisions(PAYLOAD_GIT_POLICY) == 0
        and manifest_revisions(PAYLOAD_ROUNDTRIP) == 0
        and manifest_revisions(PAYLOAD_EXTRACTION_SMOKE) == 0
        and manifest_revisions(PAYLOAD_VERIFIER_SMOKE) == 0
        and manifest_revisions(PAYLOAD_LATEX_COMPILE) == 0
        and int(manifest_value(PAYLOAD_MANIFEST, "file_count", -1)) > 0
    )

    support_files = (
        README,
        CHECKLIST,
        AUTHOR_INPUT,
        LAST_MILE,
        FINAL_HANDOFF,
        COVER_TEMPLATE,
        DECLARATIONS_TEMPLATE,
        METADATA_TEMPLATE,
        ANSWERS_TEMPLATE,
    )
    support_exists, support_missing = existing(support_files)
    support_tokens_missing = token_missing(README, ("LAST_MILE_ACTION_CARD_zh.md", "AUTHOR_INPUT_REQUIRED.md"))
    support_ok = support_exists and manifest_revisions(SUPPORT_PACKET) == 0 and not support_tokens_missing

    private_hits = payload_private_hits()
    source_privacy_ok = manifest_revisions(SOURCE_PRIVACY) == 0
    final_sequence_ok = (
        manifest_revisions(FINAL_UPLOAD_SEQUENCE) == 0
        and bool(manifest_value(FINAL_UPLOAD_SEQUENCE, "sequence_ready", False))
        and manifest_revisions(FINAL_HUMAN_GATE) == 0
        and bool(manifest_value(FINAL_HUMAN_GATE, "human_gate_open", False))
    )

    decision_ok = (
        manifest_revisions(TARGET_DECISION) == 0
        and manifest_revisions(FINAL_UPLOAD_SEQUENCE) == 0
        and read_json(TARGET_DECISION).get("recommended_first_choice") == "ACM Transactions on Quantum Computing"
    )

    return [
        row(
            "Author manuscript bundle",
            "pass" if author_ok else "needs revision",
            "Non-anonymous venue upload or author-labeled review copy.",
            author_files,
            (
                f"missing_files={author_missing or 'none'}; "
                f"pdf_visual_revisions={manifest_revisions(PDF_VISUAL)}; "
                f"pdf_text_revisions={manifest_revisions(PDF_TEXT)}; "
                f"pdf_metadata_revisions={manifest_revisions(PDF_METADATA)}; "
                f"latex_dependency_revisions={manifest_revisions(LATEX_DEPENDENCY)}."
            ),
            "Author declarations and final availability links still require private author/venue input.",
            "Rebuild PDFs and rerun visual, text, metadata, and LaTeX dependency audits.",
        ),
        row(
            "Generic anonymous-review bundle",
            "pass" if anon_ok else "needs revision",
            "Double-blind venue upload when a generic anonymous format is accepted.",
            anon_files,
            f"missing_files={anon_missing or 'none'}; anonymous_counts={anon_counts}; anonymous_revisions={manifest_revisions(ANONYMOUS_REVIEW)}.",
            "Anonymous artifact links remain target-venue author input if double-blind review is required.",
            "Regenerate the anonymous draft and anonymous-review readiness audit after target policy is chosen.",
        ),
        row(
            "ACM/TQC review-format bundle",
            "pass" if acm_ok else "needs revision",
            "ACM Transactions on Quantum Computing review-format route.",
            acm_files,
            (
                f"missing_files={acm_missing or 'none'}; "
                f"format_revisions={manifest_revisions(TARGET_FORMAT)}; "
                f"pages={manifest_value(TARGET_FORMAT, 'pdf_pages', manifest_value(TARGET_FORMAT, 'pages', 'missing'))}; "
                f"recommended_first_choice={manifest_value(TARGET_DECISION, 'recommended_first_choice', 'missing')}."
            ),
            "Final ACM rights, named authors, ORCIDs, CCS/keywords, and publication metadata remain author/venue decisions.",
            "Rerun make_acm_tqc_review_draft.py, compile ACM/TQC source, and rerun target-format smoke.",
        ),
        row(
            "Source/data payload bundle",
            "pass" if payload_ok else "needs revision",
            "Reviewer/source-data archive uploaded with the manuscript or deposited externally.",
            payload_files,
            (
                f"missing_files={payload_missing or 'none'}; "
                f"payload_files={manifest_value(PAYLOAD_MANIFEST, 'file_count', 'missing')}; "
                f"git_policy_revisions={manifest_revisions(PAYLOAD_GIT_POLICY)}; "
                f"roundtrip_revisions={manifest_revisions(PAYLOAD_ROUNDTRIP)}; "
                f"extraction_revisions={manifest_revisions(PAYLOAD_EXTRACTION_SMOKE)}; "
                f"verifier_revisions={manifest_revisions(PAYLOAD_VERIFIER_SMOKE)}; "
                f"latex_compile_revisions={manifest_revisions(PAYLOAD_LATEX_COMPILE)}."
            ),
            "The payload excludes private metadata and excludes its own generated tarball from Git.",
            "Regenerate the payload archive and rerun round-trip, extraction, verifier, and LaTeX compile audits.",
        ),
        row(
            "Support and declaration templates",
            "pass" if support_ok else "needs revision",
            "Human-facing upload support: README, checklist, author input, last-mile card, cover letter, declarations, and metadata templates.",
            support_files,
            (
                f"missing_files={support_missing or 'none'}; "
                f"readme_missing_tokens={support_tokens_missing or 'none'}; "
                f"support_packet_revisions={manifest_revisions(SUPPORT_PACKET)}."
            ),
            "Templates deliberately contain author-input placeholders and should not contain real private metadata while tracked.",
            "Restore support files and rerun the submission support packet audit.",
        ),
        row(
            "Private local-only metadata boundary",
            "pass" if source_privacy_ok and not private_hits else "needs revision",
            "Local-only author metadata and generated submission text after the author fills private JSON.",
            tuple(SUBMISSION / name for name in sorted(PRIVATE_BASENAMES)),
            (
                f"private_payload_hits={private_hits or 'none'}; "
                f"source_privacy_revisions={manifest_revisions(SOURCE_PRIVACY)}; "
                f"payload_manifest_contains_private={bool(private_hits)}; "
                f"payload_path_count={len(payload_file_set)}."
            ),
            "These files must stay ignored, local, and outside the public upload payload unless a venue explicitly requires private upload text.",
            "Keep private metadata out of Git and out of the source/data payload; regenerate source/path privacy and payload manifests after changes.",
        ),
        row(
            "Venue decision and final-sequence gate",
            "pass" if decision_ok and final_sequence_ok else "needs revision",
            "Decision support before choosing author-labeled, anonymous, or ACM/TQC route.",
            (FINAL_HANDOFF, LAST_MILE, CHECKLIST),
            (
                f"target_decision_revisions={manifest_revisions(TARGET_DECISION)}; "
                f"recommended_first_choice={manifest_value(TARGET_DECISION, 'recommended_first_choice', 'missing')}; "
                f"final_upload_revisions={manifest_revisions(FINAL_UPLOAD_SEQUENCE)}; "
                f"sequence_ready={manifest_value(FINAL_UPLOAD_SEQUENCE, 'sequence_ready', False)}; "
                f"human_gate_open={manifest_value(FINAL_HUMAN_GATE, 'human_gate_open', False)}."
            ),
            "The repository can prepare the route, but the author must still choose the target venue and fill author/venue metadata.",
            "Use the last-mile action card and rerun final upload sequence and final human-gate audits after author decisions.",
        ),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["bundle", "status", "upload_use", "files", "evidence", "boundary", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Upload Bundle Matrix Audit",
        "",
        "This terminal audit maps venue-facing upload bundles to checked files, evidence gates, and claim/privacy boundaries.",
        "",
        "## Status counts",
        "",
    ]
    lines.extend(f"- {status}: {counts[status]}" for status in sorted(counts))
    lines.extend(["", "| bundle | status | upload use | evidence | boundary |", "|---|---|---|---|---|"])
    for item in rows:
        lines.append(
            f"| {item['bundle']} | {item['status']} | {item['upload_use']} | {item['evidence']} | {item['boundary']} |"
        )
    lines.extend(["", "## Bundle files", ""])
    for item in rows:
        lines.append(f"- **{item['bundle']}**: {item['files']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "bundle_matrix_ready": counts.get("needs revision", 0) == 0,
        "terminal_audit": True,
        "bundles": [item["bundle"] for item in rows],
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_manifest(MANIFEST, rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} upload bundle matrix row(s)")
    if failures:
        print(f"warning: {failures} upload bundle matrix row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
