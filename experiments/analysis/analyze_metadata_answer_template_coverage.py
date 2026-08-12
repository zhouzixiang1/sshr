#!/usr/bin/env python3
"""Audit the public short-answer metadata template.

The final author/venue metadata is private, but the public answer template is
the file authors are asked to copy and fill.  This audit proves that the short
template covers every required metadata path, except for the explicitly
starter-filled public checkout fields, and that the converter can read the
template without writing private outputs.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from analyze_submission_metadata_audit import (
    REQUIRED_METADATA_PATHS,
    RESULTS,
    SUBMISSION_PACKAGE,
    THIS_DIR,
    has_author_placeholder,
    read_json,
    rel,
    value_at,
)
from make_submission_metadata_from_answers import ANSWERS_TEMPLATE, build_from_answers
from make_submission_metadata_starter import build_starter


SUMMARY = RESULTS / "summary_metadata_answer_template_coverage.csv"
ANALYSIS = RESULTS / "analysis_metadata_answer_template_coverage.md"
MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"
AUTHOR_PLACEHOLDER = "AUTHOR INPUT REQUIRED"
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"

STARTER_ONLY_REQUIRED_PATHS = {
    "code_availability.repository_url",
    "code_availability.commit_hash",
    "code_availability.environment_notes",
}

PRIVATE_LIKE_PATTERNS = (
    re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+"),
    re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b"),
)


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def path_exists(data: object, dotted_path: str) -> bool:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True


def scalar_paths(value: object, prefix: str = "") -> list[tuple[str, object]]:
    if isinstance(value, dict):
        paths: list[tuple[str, object]] = []
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(scalar_paths(item, child))
        return paths
    if isinstance(value, list):
        if not value:
            return [(prefix or "<root>", value)]
        paths = []
        for item in value:
            child = f"{prefix}[]" if prefix else "[]"
            paths.extend(scalar_paths(item, child))
        return paths
    return [(prefix or "<root>", value)]


def non_instruction_placeholder_values(data: object) -> list[str]:
    offenders: list[str] = []
    for path, value in scalar_paths(data):
        if path.startswith("instructions."):
            continue
        if isinstance(value, str) and value.strip() == AUTHOR_PLACEHOLDER:
            continue
        if isinstance(value, list) and all(isinstance(item, str) and item.strip() == AUTHOR_PLACEHOLDER for item in value):
            continue
        if value == AUTHOR_PLACEHOLDER:
            continue
        offenders.append(path)
    return sorted(set(offenders))


def private_like_values(data: object) -> list[str]:
    hits: list[str] = []
    for path, value in scalar_paths(data):
        if path.startswith("instructions."):
            continue
        if not isinstance(value, str) or value.strip() == AUTHOR_PLACEHOLDER:
            continue
        if any(pattern.search(value) for pattern in PRIVATE_LIKE_PATTERNS):
            hits.append(path)
    return sorted(set(hits))


def answer_template_data() -> object:
    return read_json(ANSWERS_TEMPLATE)


def coverage_state(data: object) -> dict[str, object]:
    starter, starter_filled, starter_unavailable = build_starter()
    answer_required = sorted(path for path in REQUIRED_METADATA_PATHS if path_exists(data, path))
    omitted = sorted(path for path in REQUIRED_METADATA_PATHS if path not in answer_required)
    starter_filled_required = sorted(
        path for path in omitted if not has_author_placeholder(value_at(starter, path))
    )
    missing = sorted(
        path
        for path in omitted
        if path not in STARTER_ONLY_REQUIRED_PATHS
        or (not EXTRACTED_PAYLOAD_MODE and has_author_placeholder(value_at(starter, path)))
    )
    unexpected_omitted = sorted(path for path in omitted if path not in STARTER_ONLY_REQUIRED_PATHS)
    unexpected_starter_filled = sorted(
        path for path in starter_filled_required if path not in STARTER_ONLY_REQUIRED_PATHS
    )
    return {
        "answer_required": answer_required,
        "omitted": omitted,
        "starter_filled_required": starter_filled_required,
        "starter_filled": sorted(starter_filled),
        "starter_unavailable": sorted(starter_unavailable),
        "missing": missing,
        "unexpected_omitted": unexpected_omitted,
        "unexpected_starter_filled": unexpected_starter_filled,
    }


def check_required_coverage(data: object) -> tuple[dict[str, str], dict[str, object]]:
    state = coverage_state(data)
    missing = state["missing"]
    unexpected = state["unexpected_omitted"]
    status = "pass" if not missing and not unexpected else "needs revision"
    return (
        row(
            "Required-path coverage",
            status,
            (
                f"required_paths={len(REQUIRED_METADATA_PATHS)}; "
                f"answer_template_paths={len(state['answer_required'])}; "
                f"starter_only_paths={state['omitted'] or 'none'}; "
                f"missing={missing or 'none'}."
            ),
            "Add missing author-fillable paths to submission_metadata_answers_template.json, or explicitly whitelist public starter-only paths.",
        ),
        state,
    )


def check_starter_only_policy(state: dict[str, object]) -> dict[str, str]:
    omitted = set(state["omitted"])
    unavailable = set(state["starter_unavailable"])
    unexpected_starter = state["unexpected_starter_filled"]
    unavailable_ok = unavailable.issubset(STARTER_ONLY_REQUIRED_PATHS) and (
        EXTRACTED_PAYLOAD_MODE or not unavailable
    )
    return row(
        "Starter-only public-field policy",
        "pass" if omitted == STARTER_ONLY_REQUIRED_PATHS and not unexpected_starter and unavailable_ok else "needs revision",
        (
            f"expected_starter_only={sorted(STARTER_ONLY_REQUIRED_PATHS)}; "
            f"observed_starter_only={sorted(omitted)}; "
            f"starter_filled={state['starter_filled'] or 'none'}; "
            f"starter_unavailable={state['starter_unavailable'] or 'none'}; "
            f"extracted_payload_mode={EXTRACTED_PAYLOAD_MODE}."
        ),
        "Keep only repository URL, commit hash, and environment notes delegated to the public starter.",
    )


def check_converter_dry_run() -> tuple[dict[str, str], dict[str, object]]:
    try:
        _, filled, public_unavailable, unknown, remaining = build_from_answers(ANSWERS_TEMPLATE)
    except Exception as exc:
        return (
            row(
                "Answer-template converter dry-run",
                "needs revision",
                f"converter exception={type(exc).__name__}: {exc}.",
                "Fix make_submission_metadata_from_answers.py or the public answer template JSON.",
            ),
            {
                "filled": [],
                "public_unavailable": [],
                "unknown": ["converter exception"],
                "remaining": [],
            },
        )
    unavailable_ok = set(public_unavailable).issubset(STARTER_ONLY_REQUIRED_PATHS) and (
        EXTRACTED_PAYLOAD_MODE or not public_unavailable
    )
    status = "pass" if not unknown and remaining and unavailable_ok else "needs revision"
    return (
        row(
            "Answer-template converter dry-run",
            status,
            (
                f"filled_paths={len(filled)}; public_unavailable={public_unavailable or 'none'}; "
                f"unknown_answer_paths={unknown or 'none'}; remaining_author_paths={len(remaining)}."
            ),
            "The public template should dry-run without unknown paths and should still require author/venue input before writing private metadata.",
        ),
        {
            "filled": filled,
            "public_unavailable": public_unavailable,
            "unknown": unknown,
            "remaining": remaining,
        },
    )


def check_privacy_hygiene(data: object) -> tuple[dict[str, str], dict[str, object]]:
    non_placeholder = non_instruction_placeholder_values(data)
    private_like = private_like_values(data)
    return (
        row(
            "Public answer-template privacy hygiene",
            "pass" if not non_placeholder and not private_like else "needs revision",
            (
                f"non_instruction_non_placeholder_values={non_placeholder or 'none'}; "
                f"private_like_value_paths={private_like or 'none'}."
            ),
            "Keep tracked answer-template values as placeholders only; put real author metadata only in ignored private files.",
        ),
        {"non_placeholder": non_placeholder, "private_like": private_like},
    )


def build_rows() -> tuple[list[dict[str, str]], dict[str, object]]:
    data = answer_template_data()
    if not isinstance(data, dict):
        rows = [
            row(
                "Answer template JSON",
                "needs revision",
                f"{rel(ANSWERS_TEMPLATE)} is missing or invalid.",
                "Restore valid JSON before asking authors to fill private metadata.",
            )
        ]
        return rows, {"template_valid": False}
    coverage_row, coverage = check_required_coverage(data)
    converter_row, converter = check_converter_dry_run()
    privacy_row, privacy = check_privacy_hygiene(data)
    rows = [
        row(
            "Answer template JSON",
            "pass",
            f"{rel(ANSWERS_TEMPLATE)} exists and parses as a JSON object.",
            "Keep the public short-answer template tracked and free of private values.",
        ),
        coverage_row,
        check_starter_only_policy(coverage),
        converter_row,
        privacy_row,
    ]
    diagnostics = {
        "template_valid": True,
        "coverage": coverage,
        "converter": converter,
        "privacy": privacy,
    }
    return rows, diagnostics


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Metadata Answer Template Coverage",
        "",
        "This audit checks the tracked short-answer template used to collect final private author and venue metadata.",
        "",
        "It verifies that every required metadata path is either present in the answer template or intentionally delegated to the safe public metadata starter.",
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


def write_manifest(path: Path, rows: list[dict[str, str]], diagnostics: dict[str, object]) -> None:
    counts = Counter(item["status"] for item in rows)
    coverage = diagnostics.get("coverage", {}) if isinstance(diagnostics.get("coverage"), dict) else {}
    converter = diagnostics.get("converter", {}) if isinstance(diagnostics.get("converter"), dict) else {}
    privacy = diagnostics.get("privacy", {}) if isinstance(diagnostics.get("privacy"), dict) else {}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "extracted_payload_mode": EXTRACTED_PAYLOAD_MODE,
        "answer_template": rel(ANSWERS_TEMPLATE),
        "required_metadata_paths": len(REQUIRED_METADATA_PATHS),
        "answer_template_required_paths": len(coverage.get("answer_required", [])),
        "starter_only_required_paths": coverage.get("omitted", []),
        "expected_starter_only_required_paths": sorted(STARTER_ONLY_REQUIRED_PATHS),
        "missing_required_paths": coverage.get("missing", []),
        "unexpected_omitted_paths": coverage.get("unexpected_omitted", []),
        "unknown_answer_paths": converter.get("unknown", []),
        "remaining_author_paths_after_template_dry_run": len(converter.get("remaining", [])),
        "public_unavailable_paths": converter.get("public_unavailable", []),
        "non_placeholder_answer_paths": privacy.get("non_placeholder", []),
        "private_like_value_paths": privacy.get("private_like", []),
        "rows": len(rows),
        "status_counts": dict(counts),
        "needs_revision_count": counts.get("needs revision", 0),
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows, diagnostics = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_manifest(MANIFEST, rows, diagnostics)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} metadata answer-template coverage row(s)")
    if failures:
        print(f"warning: {failures} answer-template coverage row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
