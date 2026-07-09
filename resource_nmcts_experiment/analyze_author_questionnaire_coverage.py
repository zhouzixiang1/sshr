#!/usr/bin/env python3
"""Audit that the public author metadata questionnaire covers every private field.

The actual author and venue answers stay in ignored private files
submission_package/submission_metadata_answers.json and
submission_package/submission_metadata.json.  This audit checks only the
tracked questionnaire and templates so the remaining human gate is explicit,
complete, and safe to ship in the reviewer payload.
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
    THIS_DIR,
    read_json,
    rel,
    value_at,
)


QUESTIONNAIRE = SUBMISSION_PACKAGE / "AUTHOR_METADATA_QUESTIONNAIRE_zh.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def questionnaire_covers(path: str, text: str) -> bool:
    if path in text:
        return True
    if path == "authors":
        author_tokens = (
            "authors[]",
            "authors[].order",
            "authors[].name",
            "authors[].orcid",
            "authors[].affiliations",
            "authors[].email",
            "authors[].corresponding",
        )
        return all(token in text for token in author_tokens)
    return False


def missing_template_paths(template: object) -> list[str]:
    missing: list[str] = []
    for path in REQUIRED_METADATA_PATHS:
        if value_at(template, path) is None:
            missing.append(path)
    return missing


def check_file_and_private_workflow(text: str) -> dict[str, str]:
    tokens = (
        "submission_metadata_answers.json",
        "submission_metadata.json",
        "AUTHOR INPUT REQUIRED",
        "make_submission_metadata_from_answers.py",
        "validate_submission_metadata.py",
        "make_submission_text_preview.py",
        "Git 忽略",
        "不要把真实私人信息直接写进本文件",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Questionnaire file and private workflow",
        "pass" if QUESTIONNAIRE.exists() and not missing else "needs revision",
        f"questionnaire_exists={QUESTIONNAIRE.exists()}; missing_tokens={missing or 'none'}.",
        "Keep the questionnaire as a public checklist and store real values only in ignored private metadata answer/metadata files.",
    )


def check_required_path_coverage(text: str) -> dict[str, str]:
    missing = [path for path in REQUIRED_METADATA_PATHS if not questionnaire_covers(path, text)]
    return row(
        "Required metadata path coverage",
        "pass" if not missing else "needs revision",
        f"required_paths={len(REQUIRED_METADATA_PATHS)}; missing_paths={missing or 'none'}.",
        "Add every missing private metadata path to AUTHOR_METADATA_QUESTIONNAIRE_zh.md.",
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


def check_boundary_reminders(text: str) -> dict[str, str]:
    tokens = (
        "logical-layer quantum Boolean oracle synthesis",
        "hardware mapping",
        "ROS-style LUT proxy",
        "full official ROS SAT garbage-management reproduction",
        "weighted-score",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Claim-boundary reminders",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep overclaim boundaries visible where authors fill final submission text.",
    )


def check_anonymous_link_prompts(text: str) -> dict[str, str]:
    tokens = (
        "target_venue.anonymous_review_required",
        "data_availability.anonymous_review_link",
        "code_availability.anonymous_review_link",
        "双盲",
        "匿名",
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Anonymous-review link prompts",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep double-blind data/code link prompts visible until the target venue is selected.",
    )


def check_post_fill_commands(text: str) -> dict[str, str]:
    tokens = (
        "make_submission_metadata_from_answers.py --init-private-answers",
        "make_submission_metadata_from_answers.py --write-private",
        "validate_submission_metadata.py",
        "make_submission_text_preview.py",
        "./rebuild_submission_package.sh",
        "./verify_submission_package.sh",
        'rg -n "needs author input|needs revision"',
    )
    missing = [token for token in tokens if token not in text]
    return row(
        "Post-fill verification commands",
        "pass" if not missing else "needs revision",
        f"missing_tokens={missing or 'none'}.",
        "Keep the post-fill command sequence in the public questionnaire.",
    )


def build_rows() -> list[dict[str, str]]:
    text = read_text(QUESTIONNAIRE)
    return [
        check_file_and_private_workflow(text),
        check_required_path_coverage(text),
        check_template_parity(),
        check_boundary_reminders(text),
        check_anonymous_link_prompts(text),
        check_post_fill_commands(text),
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
        "# Author Questionnaire Coverage Audit",
        "",
        "This audit checks that the public Chinese author-metadata questionnaire covers every private author/venue field required by the structured metadata template.",
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
    text = read_text(QUESTIONNAIRE)
    missing_required = [path for path in REQUIRED_METADATA_PATHS if not questionnaire_covers(path, text)]
    template = read_json(METADATA_TEMPLATE)
    missing_template = missing_template_paths(template) if isinstance(template, dict) else list(REQUIRED_METADATA_PATHS)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "needs_revision_count": failures,
        "required_paths": len(REQUIRED_METADATA_PATHS),
        "missing_required_paths": missing_required,
        "missing_template_paths": missing_template,
        "questionnaire": rel(QUESTIONNAIRE),
        "template": rel(METADATA_TEMPLATE),
        "outputs": {
            "summary": "results/summary_author_questionnaire_coverage.csv",
            "analysis": "results/analysis_author_questionnaire_coverage.md",
            "manifest": "results/manifest_author_questionnaire_coverage.json",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_author_questionnaire_coverage.csv", rows)
    write_markdown(RESULTS / "analysis_author_questionnaire_coverage.md", rows)
    write_manifest(RESULTS / "manifest_author_questionnaire_coverage.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} author questionnaire coverage row(s)")
    if failures:
        print(f"warning: {failures} author questionnaire coverage row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
