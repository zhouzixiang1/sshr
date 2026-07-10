#!/usr/bin/env python3
"""Audit the final human-only gate before claiming goal closure.

This audit is intentionally narrow.  It does not fill or infer private author
metadata.  Instead, it checks that the remaining non-pass state in the goal and
submission metadata chain is limited to author/venue input, while the
machine-checkable research, package, privacy, and metadata intake paths remain
free of needs-revision rows.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"

GOAL_SUMMARY = RESULTS / "summary_goal_completion_audit.csv"
GOAL_MANIFEST = RESULTS / "manifest_goal_completion_audit.json"
METADATA_SUMMARY = RESULTS / "summary_submission_metadata_audit.csv"
METADATA_VALIDATOR_SUMMARY = RESULTS / "summary_submission_metadata_validator.csv"
TEXT_PREVIEW_SUMMARY = RESULTS / "summary_submission_text_preview.csv"
FINAL_UPLOAD_PLAN_SUMMARY = RESULTS / "summary_final_upload_plan.csv"
FINAL_UPLOAD_PLAN_TOOL_SUMMARY = RESULTS / "summary_final_upload_plan_tool_audit.csv"
ANONYMOUS_REVIEW_SUMMARY = RESULTS / "summary_anonymous_review_readiness.csv"
AUTHOR_INPUT_CLOSURE_SUMMARY = RESULTS / "summary_author_input_closure_audit.csv"
METADATA_CLOSURE_SUMMARY = RESULTS / "summary_submission_metadata_closure_path.csv"
PAYLOAD_ROUNDTRIP_SUMMARY = RESULTS / "summary_payload_roundtrip_audit.csv"
SOURCE_PATH_PRIVACY_SUMMARY = RESULTS / "summary_source_path_privacy_audit.csv"

SUMMARY = RESULTS / "summary_final_human_gate_audit.csv"
ANALYSIS = RESULTS / "analysis_final_human_gate_audit.md"
MANIFEST = RESULTS / "manifest_final_human_gate_audit.json"

ALLOWED_GOAL_OPEN = {"Final author and venue metadata", "Overall goal closure gate"}
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


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


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def has_no_revision(rows: list[dict[str, str]]) -> bool:
    return bool(rows) and status_counts(rows).get("needs revision", 0) == 0


def all_pass(rows: list[dict[str, str]]) -> bool:
    counts = status_counts(rows)
    return bool(rows) and counts.get("needs revision", 0) == 0 and counts.get("needs author input", 0) == 0


def only_author_input_or_pass(rows: list[dict[str, str]]) -> bool:
    counts = status_counts(rows)
    allowed = {"pass", "needs author input"}
    return bool(rows) and set(counts).issubset(allowed) and counts.get("needs author input", 0) > 0


def open_goal_requirements(goal_rows: list[dict[str, str]]) -> list[str]:
    return [
        row.get("requirement", "")
        for row in goal_rows
        if row.get("status") != "pass"
    ]


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
    }


def build_rows() -> list[dict[str, str]]:
    goal_rows = read_csv(GOAL_SUMMARY)
    goal_manifest = read_json(GOAL_MANIFEST)
    goal_counts = status_counts(goal_rows)
    open_requirements = open_goal_requirements(goal_rows)
    goal_ok = (
        has_no_revision(goal_rows)
        and goal_counts.get("pass", 0) >= 13
        and goal_counts.get("needs author input", 0) == 2
        and set(open_requirements) == ALLOWED_GOAL_OPEN
        and goal_manifest.get("overall_closure") == "not complete"
    )

    metadata_rows = read_csv(METADATA_SUMMARY)
    metadata_counts = status_counts(metadata_rows)
    metadata_ok = (
        has_no_revision(metadata_rows)
        and metadata_counts.get("needs author input", 0) >= 12
        and metadata_counts.get("pass", 0) == 0
    )

    validator_rows = read_csv(METADATA_VALIDATOR_SUMMARY)
    preview_rows = read_csv(TEXT_PREVIEW_SUMMARY)
    final_upload_plan_rows = read_csv(FINAL_UPLOAD_PLAN_SUMMARY)
    final_upload_plan_tool_rows = read_csv(FINAL_UPLOAD_PLAN_TOOL_SUMMARY)
    validator_preview_ok = (
        only_author_input_or_pass(validator_rows)
        and only_author_input_or_pass(preview_rows)
        and only_author_input_or_pass(final_upload_plan_rows)
        and all_pass(final_upload_plan_tool_rows)
        and status_counts(validator_rows).get("needs revision", 0) == 0
        and status_counts(preview_rows).get("needs revision", 0) == 0
        and status_counts(final_upload_plan_rows).get("needs revision", 0) == 0
    )

    author_closure_rows = read_csv(AUTHOR_INPUT_CLOSURE_SUMMARY)
    metadata_closure_rows = read_csv(METADATA_CLOSURE_SUMMARY)
    closure_ok = all_pass(author_closure_rows) and all_pass(metadata_closure_rows)

    anonymous_rows = read_csv(ANONYMOUS_REVIEW_SUMMARY)
    anonymous_counts = status_counts(anonymous_rows)
    anonymous_ok = (
        has_no_revision(anonymous_rows)
        and anonymous_counts.get("needs author input", 0) == 3
        and anonymous_counts.get("pass", 0) == 3
    )

    payload_rows = read_csv(PAYLOAD_ROUNDTRIP_SUMMARY)
    privacy_rows = read_csv(SOURCE_PATH_PRIVACY_SUMMARY)
    payload_roundtrip_delegated = EXTRACTED_PAYLOAD_MODE and not payload_rows
    payload_privacy_ok = (payload_roundtrip_delegated or all_pass(payload_rows)) and all_pass(privacy_rows)

    rows = [
        row(
            "Goal audit open-state boundary",
            "pass" if goal_ok else "needs revision",
            f"goal_counts={goal_counts}; open_requirements={open_requirements}; overall_closure={goal_manifest.get('overall_closure', 'missing')}.",
            "Rerun analyze_goal_completion_audit.py and resolve any non-author open goal rows before treating the package as machine-side closed.",
        ),
        row(
            "Author metadata inventory boundary",
            "pass" if metadata_ok else "needs revision",
            f"metadata_counts={metadata_counts}; required author/venue field groups remain explicit.",
            "Rerun analyze_submission_metadata_audit.py and restore the AUTHOR INPUT REQUIRED inventory if counts or statuses drift.",
        ),
        row(
            "Validator and private-preview boundary",
            "pass" if validator_preview_ok else "needs revision",
            f"validator_counts={status_counts(validator_rows)}; preview_counts={status_counts(preview_rows)}; upload_plan_counts={status_counts(final_upload_plan_rows)}; upload_plan_tool_counts={status_counts(final_upload_plan_tool_rows)}.",
            "Run validate_submission_metadata.py, make_submission_text_preview.py, make_final_upload_plan.py, and analyze_final_upload_plan_tool_audit.py; needs-revision rows must be fixed, while missing private metadata remains author input.",
        ),
        row(
            "Author-input closure path",
            "pass" if closure_ok else "needs revision",
            f"author_input_closure_counts={status_counts(author_closure_rows)}; metadata_closure_counts={status_counts(metadata_closure_rows)}.",
            "Rerun analyze_author_input_closure_audit.py and analyze_submission_metadata_closure_path.py after changing metadata templates or handoff documents.",
        ),
        row(
            "Anonymous-review venue-decision boundary",
            "pass" if anonymous_ok else "needs revision",
            f"anonymous_review_counts={anonymous_counts}.",
            "Choose the target venue and double-blind policy, then regenerate anonymous submission artifacts if required.",
        ),
        row(
            "Payload and source-privacy boundary",
            "pass" if payload_privacy_ok else "needs revision",
            f"payload_roundtrip_counts={'delegated_to_source_worktree' if payload_roundtrip_delegated else status_counts(payload_rows)}; source_privacy_counts={status_counts(privacy_rows)}; extracted_payload_mode={EXTRACTED_PAYLOAD_MODE}.",
            "Rerun payload round-trip and source/path privacy audits after changing payload inputs or public support files.",
        ),
    ]

    machine_closed = all(item["status"] == "pass" for item in rows)
    rows.append(
        row(
            "Final human-only gate statement",
            "pass" if machine_closed else "needs revision",
            "All upstream machine-checkable gates pass; the remaining blocker class is author/venue metadata and target anonymous-review policy."
            if machine_closed
            else "At least one upstream machine-checkable gate needs revision.",
            "Do not mark the overall objective complete until private author/venue metadata are filled and the final audits are rerun.",
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
    counts = status_counts(rows)
    lines = [
        "# Final Human-Gate Audit",
        "",
        "This audit checks whether the remaining non-pass state is limited to author/venue input.",
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
    counts = status_counts(rows)
    failures = counts.get("needs revision", 0)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": failures,
        "human_gate_open": True,
        "remaining_blocker_class": "author/venue metadata and target anonymous-review policy",
        "allowed_open_goal_requirements": sorted(ALLOWED_GOAL_OPEN),
        "machine_side_closed": failures == 0,
        "source_summaries": [
            rel(GOAL_SUMMARY),
            rel(METADATA_SUMMARY),
            rel(METADATA_VALIDATOR_SUMMARY),
            rel(TEXT_PREVIEW_SUMMARY),
            rel(ANONYMOUS_REVIEW_SUMMARY),
            rel(AUTHOR_INPUT_CLOSURE_SUMMARY),
            rel(METADATA_CLOSURE_SUMMARY),
            rel(PAYLOAD_ROUNDTRIP_SUMMARY),
            rel(SOURCE_PATH_PRIVACY_SUMMARY),
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
    print(f"wrote {len(rows)} final human-gate audit rows")
    if failures:
        print(f"warning: {failures} final human-gate row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
