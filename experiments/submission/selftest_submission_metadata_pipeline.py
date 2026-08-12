#!/usr/bin/env python3
"""Self-test the private metadata validation and preview pipeline.

This script uses synthetic, non-private metadata to exercise the same validator
checks and preview renderers that will run after the author fills
`submission_metadata.json`.  It does not create or modify the private metadata
file, and it does not write generated private preview files.  Public outputs
record only row counts and pass/fail statuses.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from analyze_submission_metadata_audit import REQUIRED_METADATA_PATHS, THIS_DIR, rel, value_at
from make_submission_text_preview import (
    build_author_declarations,
    build_availability_statements,
    build_cover_letter,
    build_submission_text,
    missing_paths,
)
from validate_submission_metadata import (
    check_author_contact_formats,
    check_author_structure,
    check_code_commit,
    check_corresponding_author_consistency,
    check_links,
    check_required_completeness,
    check_statement_lengths,
    check_target_policy_fields,
    current_head,
)


RESULTS = THIS_DIR / "results"


def synthetic_metadata() -> dict[str, object]:
    head = current_head() or "0" * 40
    return {
        "instructions": {
            "usage": "Synthetic self-test fixture; do not submit.",
            "privacy": "Synthetic values only.",
            "scope": "Submission metadata self-test only.",
        },
        "manuscript": {
            "title": "Resource-Constrained Neural Monte Carlo Tree Search with Reinforcement-Learned Budget Control for Quantum Boolean Oracle Synthesis",
            "scope_boundary": "Logical-layer quantum Boolean oracle synthesis only; no hardware mapping, routing, native-gate scheduling, noise model, or magic-state-factory resource estimate.",
        },
        "target_venue": {
            "name": "Synthetic Journal",
            "manuscript_type": "Article",
            "formatting_policy_checked": "checked",
            "reference_style_checked": "checked",
            "word_limit_checked": "checked",
            "supplementary_material_policy_checked": "checked",
            "ai_disclosure_policy_checked": "checked",
            "anonymous_review_required": "not required",
        },
        "authors": [
            {
                "order": 1,
                "name": "Synthetic Author",
                "orcid": "0000-0002-1825-0097",
                "affiliations": ["Synthetic Affiliation"],
                "email": "synthetic.author@example.com",
                "corresponding": "yes",
            }
        ],
        "corresponding_author": {
            "name": "Synthetic Author",
            "email": "synthetic.author@example.com",
            "affiliation": "Synthetic Affiliation",
            "postal_address": "Synthetic Address",
        },
        "author_contributions": {
            "conceptualization": "Synthetic Author",
            "methodology": "Synthetic Author",
            "software": "Synthetic Author",
            "validation": "Synthetic Author",
            "formal_analysis": "Synthetic Author",
            "investigation": "Synthetic Author",
            "data_curation": "Synthetic Author",
            "writing_original_draft": "Synthetic Author",
            "writing_review_editing": "Synthetic Author",
            "visualization": "Synthetic Author",
            "supervision": "Synthetic Author",
            "funding_acquisition": "Synthetic Author",
        },
        "funding": {
            "statement": "This synthetic self-test declares no external funding.",
            "grant_numbers": ["not applicable"],
        },
        "acknowledgements": {
            "statement": "This synthetic self-test has no acknowledgements to report.",
        },
        "competing_interests": {
            "statement": "The synthetic self-test declares no competing interests.",
        },
        "data_availability": {
            "archive_link_or_doi": "https://doi.org/10.5281/zenodo.1234567",
            "anonymous_review_link": "https://example.com/anonymous-data",
            "access_restrictions": "No access restrictions for the synthetic self-test.",
            "statement": "Synthetic data availability statement for pipeline validation only.",
        },
        "code_availability": {
            "repository_url": "https://github.com/zhouzixiang1/sshr",
            "commit_hash": head,
            "license": "MIT",
            "environment_notes": "mcts-qoracle environment; direct interpreter path /opt/anaconda3/envs/mcts-qoracle/bin/python.",
            "anonymous_review_link": "https://example.com/anonymous-code",
            "statement": "Synthetic code availability statement for pipeline validation only.",
        },
        "ai_assistance": {
            "statement": "Synthetic AI-assistance statement for pipeline validation only.",
        },
        "preprint_and_prior_submission": {
            "preprint_url_or_doi": "not applicable",
            "prior_submission_history": "No prior submission for this synthetic self-test.",
            "related_manuscripts": "No related manuscripts for this synthetic self-test.",
            "statement": "Synthetic prior-submission statement for pipeline validation only.",
        },
        "cover_letter": {
            "target_editor": "Editor",
            "suggested_reviewers": "Synthetic Reviewer One; Synthetic Reviewer Two",
            "excluded_reviewers": "none",
            "editorial_routing_statement": "Synthetic editorial routing statement for pipeline validation only.",
        },
        "permissions": {
            "third_party_material_confirmed": "yes",
            "statement": "Synthetic permissions statement for pipeline validation only.",
        },
    }


def row(item: str, status: str, evidence: str, next_action: str = "No action.") -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def validator_rows(data: dict[str, object]) -> list[dict[str, str]]:
    rows = [
        check_required_completeness(data),
        check_target_policy_fields(data),
        check_author_structure(data),
        check_author_contact_formats(data),
        check_corresponding_author_consistency(data),
        check_links(data),
        check_code_commit(data),
        check_statement_lengths(data),
    ]
    return [
        row(
            f"validator: {item['item']}",
            item["status"],
            f"{item['evidence']} fields={item['field_names'] or 'none'}",
            item["next_action"],
        )
        for item in rows
    ]


def required_path_rows(data: dict[str, object]) -> list[dict[str, str]]:
    missing = [path for path in REQUIRED_METADATA_PATHS if value_at(data, path) is None]
    placeholder_missing = missing_paths(data)
    return [
        row(
            "required path fixture coverage",
            "pass" if not missing else "needs revision",
            f"{len(REQUIRED_METADATA_PATHS) - len(missing)}/{len(REQUIRED_METADATA_PATHS)} required paths present.",
            "Update synthetic fixture when required metadata paths change.",
        ),
        row(
            "placeholder-free fixture",
            "pass" if not placeholder_missing else "needs revision",
            f"{len(placeholder_missing)} placeholder or empty field(s) remain.",
            "Remove placeholders from the synthetic fixture.",
        ),
    ]


def preview_rows(data: dict[str, object]) -> list[dict[str, str]]:
    previews = {
        "author declarations": build_author_declarations(data),
        "availability statements": build_availability_statements(data),
        "cover letter": build_cover_letter(data),
        "submission text packet": build_submission_text(data),
    }
    rows: list[dict[str, str]] = []
    for name, text in previews.items():
        has_placeholder = "AUTHOR INPUT REQUIRED" in text
        has_header = text.startswith("#")
        rows.append(
            row(
                f"preview renderer: {name}",
                "pass" if has_header and not has_placeholder else "needs revision",
                f"chars={len(text)}; has_header={has_header}; placeholder_present={has_placeholder}.",
                "Fix renderer output before relying on generated private preview files.",
            )
        )
    return rows


def build_rows() -> list[dict[str, str]]:
    data = synthetic_metadata()
    return required_path_rows(data) + validator_rows(data) + preview_rows(data)


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
        "# Submission Metadata Pipeline Self-Test",
        "",
        "This audit uses synthetic, non-private metadata to test the validator and private-preview renderers.",
        "",
        "It does not create `submission_metadata.json` and does not write `generated_*.md` private preview files.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "uses_synthetic_metadata_only": True,
        "writes_private_metadata": False,
        "writes_private_preview_files": False,
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_metadata_pipeline_selftest.csv"),
            "analysis": rel(RESULTS / "analysis_submission_metadata_pipeline_selftest.md"),
            "manifest": rel(RESULTS / "manifest_submission_metadata_pipeline_selftest.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_metadata_pipeline_selftest.csv", rows)
    write_markdown(RESULTS / "analysis_submission_metadata_pipeline_selftest.md", rows)
    write_manifest(RESULTS / "manifest_submission_metadata_pipeline_selftest.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} submission metadata pipeline self-test row(s)")
    if failures:
        print(f"warning: {failures} self-test row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
