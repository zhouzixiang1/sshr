#!/usr/bin/env python3
"""Audit anonymous-review readiness without using private author metadata.

The current manuscript can be submitted to non-anonymous venues as a normal
author-labeled draft.  If the selected venue requires double-blind review,
authors must provide an anonymized manuscript and anonymous artifact links.
This audit keeps that decision explicit while checking that the package has the
metadata fields and private-file boundaries needed for either path.
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from analyze_submission_metadata_audit import METADATA_FILE, METADATA_TEMPLATE, THIS_DIR, rel, read_json, value_at


RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANONYMOUS_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
README = SUBMISSION_PACKAGE / "README.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
AUTHOR_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
AUTHOR_TEMPLATE = SUBMISSION_PACKAGE / "author_declarations_template.md"

PRIVATE_PATHS = (
    SUBMISSION_PACKAGE / "submission_metadata_answers.json",
    SUBMISSION_PACKAGE / "submission_metadata.json",
    SUBMISSION_PACKAGE / "generated_author_declarations.md",
    SUBMISSION_PACKAGE / "generated_availability_statements.md",
    SUBMISSION_PACKAGE / "generated_cover_letter.md",
    SUBMISSION_PACKAGE / "generated_submission_text.md",
    SUBMISSION_PACKAGE / "generated_upload_plan.md",
)

ANONYMIZED_AUTHOR_TOKENS = {
    "",
    "anonymous",
    "anonymous author",
    "anonymous authors",
    "anonymized",
    "blinded",
    "omitted for review",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def latex_author(text: str) -> str:
    match = re.search(r"\\author\{([^{}]*)\}", text)
    return match.group(1).strip() if match else ""


def data_code_section(text: str) -> str:
    match = re.search(r"\\section\*\{Data and Code Availability\}(.*?)(?:\\section|\\appendix|\\bibliographystyle|\\bibliography|\Z)", text, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def is_anonymized_author(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    return normalized in ANONYMIZED_AUTHOR_TOKENS


def ignored_private_paths() -> tuple[bool, list[str]]:
    if os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1":
        return True, []
    gitignore = THIS_DIR.parent / ".gitignore"
    text = read_text(gitignore)
    missing: list[str] = []
    for path in PRIVATE_PATHS:
        relative_from_repo = str(path.relative_to(THIS_DIR.parent))
        if relative_from_repo not in text:
            missing.append(relative_from_repo)
    return not missing, missing


def tracked_private_paths() -> list[str]:
    if os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1":
        return []
    paths = [rel(path) for path in PRIVATE_PATHS]
    proc = subprocess.run(
        ["git", "ls-files", "--", *paths],
        cwd=THIS_DIR,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
    )
    return sorted(line for line in proc.stdout.splitlines() if line.strip()) if proc.returncode == 0 else paths


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def metadata_decision_row() -> dict[str, str]:
    data = read_json(METADATA_FILE) if METADATA_FILE.exists() else read_json(METADATA_TEMPLATE)
    value = value_at(data, "target_venue.anonymous_review_required") if data is not None else None
    text = str(value or "").strip()
    missing = not text or "AUTHOR INPUT REQUIRED" in text
    return row(
        "Target anonymous-review decision",
        "needs author input" if missing else "pass",
        "target_venue.anonymous_review_required is not finalized." if missing else "target_venue.anonymous_review_required is populated.",
        "Set target_venue.anonymous_review_required after choosing the venue, then rerun the rebuild.",
    )


def manuscript_author_row(paper_text: str) -> dict[str, str]:
    author = latex_author(paper_text)
    anonymized = is_anonymized_author(author)
    return row(
        "Current manuscript author field",
        "pass" if anonymized else "needs author input",
        f"author_field={'anonymized/blank' if anonymized else 'present'}; double_blind_ready={anonymized}.",
        "For double-blind review, create a venue-specific anonymous copy with an anonymized author field; keep this author-labeled source for non-anonymous venues.",
    )


def availability_row(paper_text: str) -> dict[str, str]:
    section = data_code_section(paper_text)
    has_repo_relative = "resource\\_nmcts\\_experiment" in section or "resource_nmcts_experiment" in section
    has_anonymous_wording = "anonymous" in section.lower()
    ready = has_anonymous_wording and not has_repo_relative
    return row(
        "Anonymous artifact-link boundary",
        "pass" if ready else "needs author input",
        f"data_code_section_present={bool(section)}; repo_relative_link={has_repo_relative}; anonymous_wording={has_anonymous_wording}.",
        "If double-blind review is required, replace repository-relative availability wording with an anonymous review archive/link before upload.",
    )


def generated_anonymous_source_row() -> dict[str, str]:
    text = read_text(ANONYMOUS_PAPER)
    author = latex_author(text)
    section = data_code_section(text)
    author_ready = is_anonymized_author(author)
    has_author_name = "Zixiang Zhou" in text
    has_repo_relative = "resource\\_nmcts\\_experiment" in section or "resource_nmcts_experiment" in section
    has_anonymous_wording = "anonymous review" in section.lower()
    ready = bool(text) and author_ready and not has_author_name and not has_repo_relative and has_anonymous_wording
    return row(
        "Generated anonymous source draft",
        "pass" if ready else "needs revision",
        f"source_exists={ANONYMOUS_PAPER.exists()}; author_anonymized={author_ready}; author_name_present={has_author_name}; availability_repo_relative={has_repo_relative}; anonymous_wording={has_anonymous_wording}.",
        "Run make_anonymous_review_draft.py and inspect the generated source before double-blind upload.",
    )


def private_boundary_row() -> dict[str, str]:
    extracted_payload = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"
    present = [rel(path) for path in PRIVATE_PATHS if path.exists()]
    ignored, missing_ignored = ignored_private_paths()
    tracked = tracked_private_paths()
    safe_worktree = ignored and not tracked
    safe_payload = not extracted_payload or not present
    return row(
        "Private file boundary for anonymous review",
        "pass" if safe_worktree and safe_payload else "needs revision",
        f"extracted_payload={extracted_payload}; present_private_files={present or 'none'}; tracked_private_files={tracked or 'none'}; gitignore_covers_private_paths={ignored}; missing_gitignore_entries={missing_ignored or 'none'}.",
        "Keep private metadata ignored and untracked in the worktree, and absent from extracted public payloads.",
    )


def template_fields_row() -> dict[str, str]:
    data = read_json(METADATA_TEMPLATE)
    required_paths = (
        "target_venue.anonymous_review_required",
        "data_availability.anonymous_review_link",
        "code_availability.anonymous_review_link",
    )
    missing = [path for path in required_paths if value_at(data, path) is None]
    support_text = "\n".join(read_text(path) for path in (README, CHECKLIST, AUTHOR_PACKET, AUTHOR_TEMPLATE))
    mentions_anonymous = "anonymous review" in support_text.lower() or "anonymous-review" in support_text.lower()
    status = "pass" if not missing and mentions_anonymous else "needs revision"
    return row(
        "Anonymous-review metadata fields",
        status,
        f"missing_template_paths={missing or 'none'}; support_docs_mention_anonymous_review={mentions_anonymous}.",
        "Keep anonymous-review metadata fields and support-document instructions in sync.",
    )


def build_rows() -> list[dict[str, str]]:
    paper_text = read_text(PAPER)
    return [
        metadata_decision_row(),
        manuscript_author_row(paper_text),
        availability_row(paper_text),
        generated_anonymous_source_row(),
        private_boundary_row(),
        template_fields_row(),
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
        "# Anonymous Review Readiness Audit",
        "",
        "This audit separates the current author-labeled manuscript from the extra actions required by a double-blind venue.",
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
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "needs_author_input_count": counts.get("needs author input", 0),
        "current_manuscript_is_double_blind_ready": all(
            item["status"] == "pass"
            for item in rows
            if item["item"] in {"Current manuscript author field", "Anonymous artifact-link boundary"}
        ),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_anonymous_review_readiness.csv"),
            "analysis": rel(RESULTS / "analysis_anonymous_review_readiness.md"),
            "manifest": rel(RESULTS / "manifest_anonymous_review_readiness.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_anonymous_review_readiness.csv", rows)
    write_markdown(RESULTS / "analysis_anonymous_review_readiness.md", rows)
    write_manifest(RESULTS / "manifest_anonymous_review_readiness.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} anonymous review readiness row(s)")
    if failures:
        print(f"warning: {failures} anonymous-review row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
