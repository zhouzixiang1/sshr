#!/usr/bin/env python3
"""Audit the final author-facing upload sequence.

This is a terminal submission audit.  It does not infer or write private
author metadata.  Instead, it verifies that the public handoff documents expose
an ordered path from target-venue selection to private metadata intake,
rebuild/verification, private preview review, availability-link replacement,
and the final human-only goal gate.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

FINAL_HANDOFF = SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
README = SUBMISSION_PACKAGE / "README.md"
AUTHOR_INPUT = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
MINIMAL_FORM = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
TARGET_POLICY = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
TARGET_BRIEF = SUBMISSION_PACKAGE / "target_venue_brief.md"
COMPARISON_HANDOFF = SUBMISSION_PACKAGE / "COMPARISON_HANDOFF_zh.md"
COMPARISON_MATRIX = SUBMISSION_PACKAGE / "COMPARISON_SIGNIFICANCE_MATRIX_zh.md"
ANSWER_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_answers_template.json"
METADATA_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_template.json"
REBUILD_SCRIPT = THIS_DIR / "rebuild_submission_package.sh"
VERIFY_SCRIPT = THIS_DIR / "verify_submission_package.sh"
METADATA_FROM_ANSWERS = THIS_DIR / "make_submission_metadata_from_answers.py"

TARGET_VENUE_DECISION_MANIFEST = RESULTS / "manifest_target_venue_decision_audit.json"
TARGET_POLICY_MANIFEST = RESULTS / "manifest_target_venue_policy_checklist.json"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
SUPPORT_PACKET_MANIFEST = RESULTS / "manifest_submission_support_packet_audit.json"
AUTHOR_MINIMAL_FORM_MANIFEST = RESULTS / "manifest_author_minimal_form_coverage.json"
METADATA_ANSWER_TEMPLATE_MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"
METADATA_CLOSURE_MANIFEST = RESULTS / "manifest_submission_metadata_closure_path.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
FINAL_HUMAN_GATE_MANIFEST = RESULTS / "manifest_final_human_gate_audit.json"

SUMMARY = RESULTS / "summary_final_upload_sequence_audit.csv"
ANALYSIS = RESULTS / "analysis_final_upload_sequence_audit.md"
MANIFEST = RESULTS / "manifest_final_upload_sequence_audit.json"


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


def status_counts(manifest: dict[str, object]) -> dict[str, int]:
    counts = manifest.get("status_counts", {}) if manifest else {}
    if not isinstance(counts, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in counts.items():
        try:
            out[str(key)] = int(value)
        except Exception:
            out[str(key)] = 0
    return out


def needs_revision(manifest: dict[str, object]) -> int:
    try:
        return int(manifest.get("needs_revision_count", -1))
    except Exception:
        return -1


def contains_all(text: str, tokens: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [token for token in tokens if token not in text]
    return not missing, missing


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
    }


def build_rows() -> list[dict[str, str]]:
    handoff = read_text(FINAL_HANDOFF)
    checklist = read_text(CHECKLIST)
    readme = read_text(README)
    author_input = read_text(AUTHOR_INPUT)
    minimal_form = read_text(MINIMAL_FORM)
    target_policy = read_text(TARGET_POLICY)
    target_brief = read_text(TARGET_BRIEF)
    comparison_docs = read_text(COMPARISON_HANDOFF) + "\n" + read_text(COMPARISON_MATRIX)
    all_docs = "\n".join(
        [handoff, checklist, readme, author_input, minimal_form, target_policy, target_brief, comparison_docs]
    )

    target_manifest = read_json(TARGET_VENUE_DECISION_MANIFEST)
    policy_manifest = read_json(TARGET_POLICY_MANIFEST)
    anonymous_manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    support_manifest = read_json(SUPPORT_PACKET_MANIFEST)
    minimal_manifest = read_json(AUTHOR_MINIMAL_FORM_MANIFEST)
    answer_manifest = read_json(METADATA_ANSWER_TEMPLATE_MANIFEST)
    closure_manifest = read_json(METADATA_CLOSURE_MANIFEST)
    preview_manifest = read_json(TEXT_PREVIEW_MANIFEST)
    final_gate_manifest = read_json(FINAL_HUMAN_GATE_MANIFEST)

    rows: list[dict[str, str]] = []

    venue_tokens = (
        "target_venue.*",
        "anonymous review",
        "TARGET_VENUE_POLICY_CHECKLIST_zh.md",
        "target_venue_brief.md",
    )
    venue_ok, venue_missing = contains_all(all_docs, venue_tokens)
    target_ok = bool(target_manifest) and needs_revision(target_manifest) == 0
    policy_ok = bool(policy_manifest) and needs_revision(policy_manifest) == 0
    anonymous_ok = (
        bool(anonymous_manifest)
        and needs_revision(anonymous_manifest) == 0
        and int(anonymous_manifest.get("needs_author_input_count", -1)) == 3
    )
    rows.append(
        row(
            "Target venue and anonymous-policy first",
            "pass" if venue_ok and target_ok and policy_ok and anonymous_ok else "needs revision",
            (
                f"missing_doc_tokens={venue_missing or 'none'}; "
                f"target_venue_revisions={needs_revision(target_manifest)}; "
                f"policy_revisions={needs_revision(policy_manifest)}; "
                f"anonymous_counts={status_counts(anonymous_manifest)}."
            ),
            "Keep target-venue choice and anonymous-review policy before private metadata generation in the final handoff.",
        )
    )

    answer_tokens = (
        "make_submission_metadata_from_answers.py --init-private-answers",
        "submission_metadata_answers.json",
        "submission_metadata_answers_template.json",
        "AUTHOR INPUT REQUIRED",
    )
    answer_ok, answer_missing = contains_all(all_docs, answer_tokens)
    template_ok = (
        bool(ANSWER_TEMPLATE.exists())
        and bool(METADATA_FROM_ANSWERS.exists())
        and bool(answer_manifest)
        and needs_revision(answer_manifest) == 0
        and not answer_manifest.get("missing_required_paths", [])
        and bool(minimal_manifest)
        and needs_revision(minimal_manifest) == 0
        and not minimal_manifest.get("missing_required_paths", [])
    )
    rows.append(
        row(
            "Private short-answer intake path",
            "pass" if answer_ok and template_ok else "needs revision",
            (
                f"missing_doc_tokens={answer_missing or 'none'}; "
                f"answer_template_exists={ANSWER_TEMPLATE.exists()}; "
                f"minimal_form_exists={MINIMAL_FORM.exists()}; "
                f"answer_template_revisions={needs_revision(answer_manifest)}; "
                f"minimal_form_revisions={needs_revision(minimal_manifest)}."
            ),
            "Keep the short private answer path aligned with the structured metadata template and Chinese minimal response form.",
        )
    )

    metadata_tokens = (
        "make_submission_metadata_from_answers.py --write-private",
        "submission_metadata.json",
        "ignored by Git",
        "Git",
    )
    metadata_ok, metadata_missing = contains_all(all_docs, metadata_tokens)
    closure_ready = bool(closure_manifest.get("closure_path_ready", False)) if closure_manifest else False
    private_path_ok = (
        bool(METADATA_TEMPLATE.exists())
        and bool(closure_manifest)
        and needs_revision(closure_manifest) == 0
        and closure_ready
        and bool(support_manifest)
        and needs_revision(support_manifest) == 0
    )
    rows.append(
        row(
            "Private metadata write and Git protection",
            "pass" if metadata_ok and private_path_ok else "needs revision",
            (
                f"missing_doc_tokens={metadata_missing or 'none'}; "
                f"metadata_template_exists={METADATA_TEMPLATE.exists()}; "
                f"closure_path_ready={closure_ready}; "
                f"metadata_closure_revisions={needs_revision(closure_manifest)}; "
                f"support_packet_revisions={needs_revision(support_manifest)}."
            ),
            "Do not write or track private author metadata outside the ignored metadata and generated-preview files.",
        )
    )

    preview_tokens = (
        "generated_author_declarations.md",
        "generated_availability_statements.md",
        "generated_cover_letter.md",
        "generated_submission_text.md",
    )
    preview_ok, preview_missing = contains_all(all_docs, preview_tokens)
    preview_counts = status_counts(preview_manifest)
    previews_ignored = bool(preview_manifest.get("private_outputs_are_git_ignored", False)) if preview_manifest else False
    rows.append(
        row(
            "Private preview review path",
            "pass" if preview_ok and previews_ignored and preview_counts.get("needs revision", 0) == 0 else "needs revision",
            (
                f"missing_doc_tokens={preview_missing or 'none'}; "
                f"preview_counts={preview_counts}; private_outputs_are_git_ignored={previews_ignored}."
            ),
            "Review generated private declarations, availability text, cover letter, and submission-system text before upload.",
        )
    )

    rebuild_tokens = ("./rebuild_submission_package.sh", "./verify_submission_package.sh")
    rebuild_ok, rebuild_missing = contains_all(all_docs, rebuild_tokens)
    rows.append(
        row(
            "Rebuild and verifier sequence",
            "pass" if rebuild_ok and REBUILD_SCRIPT.exists() and VERIFY_SCRIPT.exists() else "needs revision",
            (
                f"missing_doc_tokens={rebuild_missing or 'none'}; "
                f"rebuild_exists={REBUILD_SCRIPT.exists()}; verify_exists={VERIFY_SCRIPT.exists()}."
            ),
            "Run rebuild before the terminal verifier after author metadata or target-venue decisions change.",
        )
    )

    availability_tokens = ("archive DOI", "repository URL", "anonymous review link", "availability", "license")
    availability_ok, availability_missing = contains_all(all_docs, availability_tokens)
    rows.append(
        row(
            "Availability and archive-link replacement gate",
            "pass" if availability_ok else "needs revision",
            f"missing_doc_tokens={availability_missing or 'none'}.",
            "Replace repository-relative or placeholder availability text with the target venue's final archive DOI, repository URL, or anonymous review link.",
        )
    )

    claim_tokens = (
        "COMPARISON_HANDOFF_zh.md",
        "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
        "weighted-score",
        "CNOT/depth/ancilla",
        "hardware mapping",
    )
    claim_ok, claim_missing = contains_all(all_docs, claim_tokens)
    rows.append(
        row(
            "Comparison-claim boundary before cover-letter text",
            "pass" if claim_ok else "needs revision",
            f"missing_doc_tokens={claim_missing or 'none'}.",
            "Keep cover-letter, submission-system, and response text aligned with the comparison handoff before upload.",
        )
    )

    final_gate_docs = (
        "goal_gate=author/venue metadata remains open",
        "final goal closure should not be marked complete",
        "Do not infer",
    )
    final_gate_ok, final_gate_missing = contains_all(all_docs, final_gate_docs)
    human_gate_open = bool(final_gate_manifest.get("human_gate_open", False)) if final_gate_manifest else False
    machine_side_closed = bool(final_gate_manifest.get("machine_side_closed", False)) if final_gate_manifest else False
    rows.append(
        row(
            "Goal-closure protection",
            "pass"
            if final_gate_ok
            and bool(final_gate_manifest)
            and needs_revision(final_gate_manifest) == 0
            and human_gate_open
            and machine_side_closed
            else "needs revision",
            (
                f"missing_doc_tokens={final_gate_missing or 'none'}; "
                f"human_gate_open={human_gate_open}; machine_side_closed={machine_side_closed}; "
                f"final_gate_revisions={needs_revision(final_gate_manifest)}."
            ),
            "Do not mark the full objective complete until author/venue metadata are supplied and final audits pass again.",
        )
    )

    sequence_ready = all(item["status"] == "pass" for item in rows)
    rows.append(
        row(
            "Final upload sequence ready",
            "pass" if sequence_ready else "needs revision",
            "All author-facing upload steps are documented, ordered, private where required, and tied to machine-checkable audits."
            if sequence_ready
            else "At least one final upload step is missing from public handoff docs or generated audit evidence.",
            "Resolve the failing rows above before treating the package as ready for author-side upload execution.",
        )
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
        "# Final Upload Sequence Audit",
        "",
        "This terminal audit checks that the author-facing upload sequence is ordered, private where required, and machine-checkable.",
        "",
        "## Status counts",
        "",
    ]
    lines.extend(f"- {status}: {counts[status]}" for status in sorted(counts))
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} | {item['next_action']} |")
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
        "sequence_ready": counts.get("needs revision", 0) == 0,
        "terminal_audit": True,
        "source_documents": [
            rel(FINAL_HANDOFF),
            rel(CHECKLIST),
            rel(README),
            rel(AUTHOR_INPUT),
            rel(MINIMAL_FORM),
            rel(TARGET_POLICY),
            rel(TARGET_BRIEF),
            rel(COMPARISON_HANDOFF),
            rel(COMPARISON_MATRIX),
        ],
        "source_manifests": [
            rel(TARGET_VENUE_DECISION_MANIFEST),
            rel(TARGET_POLICY_MANIFEST),
            rel(ANONYMOUS_REVIEW_MANIFEST),
            rel(SUPPORT_PACKET_MANIFEST),
            rel(AUTHOR_MINIMAL_FORM_MANIFEST),
            rel(METADATA_ANSWER_TEMPLATE_MANIFEST),
            rel(METADATA_CLOSURE_MANIFEST),
            rel(TEXT_PREVIEW_MANIFEST),
            rel(FINAL_HUMAN_GATE_MANIFEST),
        ],
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
    print(f"wrote {len(rows)} final upload sequence rows")
    if failures:
        print(f"warning: {failures} final upload sequence row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
