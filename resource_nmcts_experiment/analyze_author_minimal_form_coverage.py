#!/usr/bin/env python3
"""Audit that the short Chinese author response form covers required metadata.

The long questionnaire is field-by-field.  The minimal response form is the
document an author is most likely to answer in one pass, so this audit checks
that its grouped prompts still cover every private author/venue metadata path
without storing any private values in tracked files.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from analyze_submission_metadata_audit import (
    METADATA_TEMPLATE,
    REQUIRED_METADATA_PATHS,
    RESULTS,
    SUBMISSION_PACKAGE,
    read_json,
    rel,
    value_at,
)


MINIMAL_FORM = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
SUMMARY = RESULTS / "summary_author_minimal_form_coverage.csv"
ANALYSIS = RESULTS / "analysis_author_minimal_form_coverage.md"
MANIFEST = RESULTS / "manifest_author_minimal_form_coverage.json"

GROUP_COVERAGE_TOKENS = {
    "target_venue": ("target_venue.*",),
    "authors": ("authors[]", "作者顺序"),
    "corresponding_author": ("corresponding_author.*",),
    "author_contributions": ("author_contributions.*",),
    "funding": ("funding.*",),
    "data_availability": ("data_availability.*",),
    "code_availability": ("code_availability.*",),
    "preprint_and_prior_submission": ("preprint_and_prior_submission.*",),
    "cover_letter": ("cover_letter.*",),
    "permissions": ("permissions.*",),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def top_level(path: str) -> str:
    return path.split(".", 1)[0].split("[", 1)[0]


def minimal_form_covers(path: str, text: str) -> bool:
    if path in text:
        return True
    group = top_level(path)
    tokens = GROUP_COVERAGE_TOKENS.get(group, ())
    return any(token in text for token in tokens)


def missing_template_paths(template: object) -> list[str]:
    missing: list[str] = []
    for path in REQUIRED_METADATA_PATHS:
        if value_at(template, path) is None:
            missing.append(path)
    return missing


def check_file_and_private_workflow(text: str) -> dict[str, str]:
    tokens = (
        "不要把真实私人信息写进 tracked 文件",
        "submission_metadata_answers.json",
        "submission_metadata.json",
        "make_submission_metadata_from_answers.py --init-private-answers",
        "make_submission_metadata_from_answers.py --write-private",
        "validate_submission_metadata.py",
        "./rebuild_submission_package.sh",
        "./verify_submission_package.sh",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Minimal form file and private workflow",
        "pass" if MINIMAL_FORM.exists() and not missing else "needs revision",
        f"minimal_form_exists={MINIMAL_FORM.exists()}; missing_tokens={missing or 'none'}.",
        "Keep the minimal form as a public intake checklist; store real values only in ignored private metadata files.",
    )


def check_required_path_coverage(text: str) -> dict[str, str]:
    missing = [path for path in REQUIRED_METADATA_PATHS if not minimal_form_covers(path, text)]
    return row(
        "Required metadata path coverage",
        "pass" if not missing else "needs revision",
        f"required_paths={len(REQUIRED_METADATA_PATHS)}; missing_paths={missing or 'none'}.",
        "Add exact path prompts or grouped wildcard prompts to AUTHOR_MINIMAL_RESPONSE_FORM_zh.md.",
    )


def check_template_parity() -> dict[str, str]:
    template = read_json(METADATA_TEMPLATE)
    if not isinstance(template, dict):
        return row(
            "Template path parity",
            "needs revision",
            f"{rel(METADATA_TEMPLATE)} is missing or invalid JSON.",
            "Restore submission_metadata_template.json before author intake.",
        )
    missing = missing_template_paths(template)
    return row(
        "Template path parity",
        "pass" if not missing else "needs revision",
        f"required_paths={len(REQUIRED_METADATA_PATHS)}; missing_in_template={missing or 'none'}.",
        "Keep REQUIRED_METADATA_PATHS aligned with submission_metadata_template.json.",
    )


def check_one_pass_answerability(text: str) -> dict[str, str]:
    tokens = (
        "可接受简答",
        "none",
        "not applicable",
        "no ORCID",
        "不要留空",
        "填完后必须跑",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "One-pass answerability cues",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep explicit placeholder wording so the author can answer every field without guessing how to mark absent values.",
    )


def check_claim_boundary_reminders(text: str) -> dict[str, str]:
    tokens = (
        "COMPARISON_HANDOFF_zh.md",
        "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
        "logical-layer quantum Boolean oracle synthesis",
        "hardware mapping",
        "full official ROS SAT garbage-management reproduction",
        "weighted-score",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Claim-boundary reminders",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep comparison and overclaim boundaries visible in the short author-intake path.",
    )


def check_anonymous_review_prompts(text: str) -> dict[str, str]:
    tokens = (
        "target_venue.*",
        "双盲",
        "匿名链接",
        "data_availability.*",
        "code_availability.*",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Anonymous-review prompts",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep double-blind data/code-link prompts visible until the target venue is selected.",
    )


def build_rows() -> list[dict[str, str]]:
    text = read_text(MINIMAL_FORM)
    return [
        check_file_and_private_workflow(text),
        check_required_path_coverage(text),
        check_template_parity(),
        check_one_pass_answerability(text),
        check_claim_boundary_reminders(text),
        check_anonymous_review_prompts(text),
    ]


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
        "# Author Minimal Response Form Coverage Audit",
        "",
        "This audit checks that the short Chinese author response form covers every required private author/venue metadata field through explicit paths or grouped wildcard prompts.",
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
    text = read_text(MINIMAL_FORM)
    missing_required = [path for path in REQUIRED_METADATA_PATHS if not minimal_form_covers(path, text)]
    template = read_json(METADATA_TEMPLATE)
    missing_template = missing_template_paths(template) if isinstance(template, dict) else list(REQUIRED_METADATA_PATHS)
    counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "required_paths": len(REQUIRED_METADATA_PATHS),
        "missing_required_paths": missing_required,
        "missing_template_paths": missing_template,
        "minimal_form": rel(MINIMAL_FORM),
        "template": rel(METADATA_TEMPLATE),
        "group_coverage_tokens": {key: list(value) for key, value in GROUP_COVERAGE_TOKENS.items()},
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_manifest(MANIFEST, rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} author minimal-form coverage row(s)")
    if failures:
        print(f"warning: {failures} author minimal-form coverage row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
