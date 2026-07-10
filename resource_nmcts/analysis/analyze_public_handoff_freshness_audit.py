#!/usr/bin/env python3
"""Check that public handoff docs expose the current package snapshot.

The submission package has several generated terminal audits.  This script
does not add scientific evidence; it prevents the public Chinese handoff and
checklist files from drifting away from the current PDF, payload, readiness,
registry, privacy, and comparison-audit counts.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DELIVERABLE = THIS_DIR / "DELIVERABLE_zh.md"
FINAL_HANDOFF = THIS_DIR / "submission_package" / "FINAL_SUBMISSION_HANDOFF_zh.md"
CHECKLIST = THIS_DIR / "submission_package" / "submission_checklist.md"

PDF_VISUAL = RESULTS / "summary_pdf_visual_audit.csv"
READINESS = RESULTS / "summary_submission_readiness_audit.csv"
PAYLOAD_ARCHIVE = RESULTS / "summary_submission_payload_archive.csv"
REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
SOURCE_PRIVACY = RESULTS / "summary_source_path_privacy_audit.csv"
COMPARISON_VALIDITY = RESULTS / "manifest_comparison_target_validity_audit.json"
NOVELTY_SCORECARD = RESULTS / "manifest_novelty_comparison_scorecard.json"
MCTS_BUDGET_POLICY = RESULTS / "summary_mcts_budget_policy.csv"

SUMMARY = RESULTS / "summary_public_handoff_freshness_audit.csv"
ANALYSIS = RESULTS / "analysis_public_handoff_freshness_audit.md"
MANIFEST = RESULTS / "manifest_public_handoff_freshness_audit.json"
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"
TOKEN_PREFIXES = (
    "PDF pages=",
    "readiness=",
    "payload_files=",
    "artifact_registry=",
    "source_privacy=",
    "comparison_validity=",
    "novelty_scorecard=",
    "rl_budget_policy=",
    "goal_gate=",
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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


def parse_int_from_evidence(evidence: str, key: str) -> int:
    match = re.search(rf"{re.escape(key)}=(\d+)", evidence)
    return int(match.group(1)) if match else -1


def extract_snapshot_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for prefix in TOKEN_PREFIXES:
        match = re.search(rf"{re.escape(prefix)}[^;\n]+", text)
        if match:
            tokens.append(match.group(0).strip().rstrip("."))
    return tuple(tokens)


def extracted_payload_snapshot() -> dict[str, object]:
    for path in (FINAL_HANDOFF, DELIVERABLE, CHECKLIST):
        tokens = extract_snapshot_tokens(read_text(path))
        if len(tokens) == len(TOKEN_PREFIXES):
            return {
                "extracted_payload_mode": True,
                "reference_document": rel(path),
                "snapshot_tokens": list(tokens),
            }
    return {
        "extracted_payload_mode": True,
        "reference_document": "missing",
        "snapshot_tokens": [],
    }


def current_snapshot() -> dict[str, object]:
    if EXTRACTED_PAYLOAD_MODE:
        return extracted_payload_snapshot()

    pdf_rows = read_csv(PDF_VISUAL)
    page_by_kind = {row.get("manuscript", ""): int(row.get("pages", "-1")) for row in pdf_rows if row.get("pages")}

    readiness_counts = status_counts(read_csv(READINESS))

    payload_rows = read_csv(PAYLOAD_ARCHIVE)
    payload_files = int(payload_rows[0].get("files", "-1")) if payload_rows else -1

    registry = read_json(REGISTRY_MANIFEST)
    registry_families = int(registry.get("rows", -1)) if registry else -1
    raw_files = int(registry.get("unique_raw_files", -1)) if registry else -1
    raw_rows = int(registry.get("unique_raw_rows", -1)) if registry else -1

    source_rows = read_csv(SOURCE_PRIVACY)
    strict_leaks = 0
    payload_text_files = -1
    provenance_local_files = -1
    for row in source_rows:
        item = row.get("item", "")
        if item in {"Manuscript source local-path hygiene", "Submission support local-path hygiene"}:
            strict_leaks += int(row.get("hits", "0") or 0)
        if item == "Payload local-path provenance classification":
            payload_text_files = int(row.get("files_scanned", "-1") or -1)
            provenance_local_files = parse_int_from_evidence(row.get("evidence", ""), "local_path_files")

    comparison = read_json(COMPARISON_VALIDITY)
    novelty = read_json(NOVELTY_SCORECARD)
    comparison_counts = comparison.get("status_counts", {}) if comparison else {}
    novelty_counts = novelty.get("status_counts", {}) if novelty else {}
    budget_rows = read_csv(MCTS_BUDGET_POLICY)
    budget = budget_rows[0] if budget_rows else {}

    return {
        "author_pages": page_by_kind.get("author", -1),
        "anonymous_pages": page_by_kind.get("anonymous", -1),
        "readiness_pass": readiness_counts.get("pass", 0),
        "readiness_author_input": readiness_counts.get("needs author input", 0),
        "payload_files": payload_files,
        "registry_families": registry_families,
        "raw_files": raw_files,
        "raw_rows": raw_rows,
        "strict_local_path_leaks": strict_leaks,
        "payload_text_files": payload_text_files,
        "provenance_local_path_files": provenance_local_files,
        "comparison_pass": int(comparison_counts.get("pass", -1)) if comparison_counts else -1,
        "comparison_rows": int(comparison.get("rows", -1)) if comparison else -1,
        "comparison_needs_revision": int(comparison.get("needs_revision_count", -1)) if comparison else -1,
        "novelty_pass": int(novelty_counts.get("pass", -1)) if novelty_counts else -1,
        "novelty_rows": int(novelty.get("rows", -1)) if novelty else -1,
        "novelty_needs_revision": int(novelty.get("needs_revision_count", -1)) if novelty else -1,
        "budget_pairs": int(budget.get("pairs", -1)) if budget else -1,
        "budget_run_pareto": int(budget.get("run_pareto", -1)) if budget else -1,
        "budget_score_vs_resource_pct": 100.0 * float(budget.get("mean_relative_vs_resource_score", "nan")),
        "budget_time_vs_pareto_pct": 100.0 * float(budget.get("time_change_vs_pareto", "nan")),
    }


def snapshot_tokens(snapshot: dict[str, object]) -> tuple[str, ...]:
    if "snapshot_tokens" in snapshot:
        return tuple(str(token) for token in snapshot["snapshot_tokens"])

    return (
        f"PDF pages={snapshot['author_pages']}/{snapshot['anonymous_pages']}",
        f"readiness={snapshot['readiness_pass']} pass + {snapshot['readiness_author_input']} needs author input",
        f"payload_files={snapshot['payload_files']}",
        (
            "artifact_registry="
            f"{snapshot['registry_families']} families / {snapshot['raw_files']} raw CSV / {snapshot['raw_rows']} raw rows"
        ),
        (
            "source_privacy="
            f"{snapshot['strict_local_path_leaks']} strict leaks / "
            f"{snapshot['provenance_local_path_files']} provenance files / "
            f"{snapshot['payload_text_files']} payload text files"
        ),
        f"comparison_validity={snapshot['comparison_pass']}/{snapshot['comparison_rows']} pass",
        f"novelty_scorecard={snapshot['novelty_pass']}/{snapshot['novelty_rows']} pass",
        (
            "rl_budget_policy="
            f"{snapshot['budget_pairs']} test functions / "
            f"{snapshot['budget_run_pareto']} Pareto calls / "
            f"{snapshot['budget_score_vs_resource_pct']:+.2f}% score vs Resource / "
            f"{snapshot['budget_time_vs_pareto_pct']:+.2f}% time vs always-Pareto"
        ),
        "goal_gate=author/venue metadata remains open",
    )


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def check_doc(path: Path, label: str, tokens: tuple[str, ...]) -> dict[str, str]:
    text = read_text(path)
    missing = [token for token in tokens if token not in text]
    return row(
        label,
        "pass" if path.exists() and not missing else "needs revision",
        f"file={rel(path)}; missing_tokens={missing or 'none'}.",
        "Refresh the public current-snapshot block from generated audit outputs.",
    )


def build_rows(snapshot: dict[str, object]) -> list[dict[str, str]]:
    if EXTRACTED_PAYLOAD_MODE:
        tokens = snapshot_tokens(snapshot)
        complete = len(tokens) == len(TOKEN_PREFIXES)
        return [
            row(
                "Extracted payload public snapshot boundary",
                "pass" if complete else "needs revision",
                (
                    "source terminal outputs intentionally excluded in extracted payload; "
                    f"reference_document={snapshot.get('reference_document', 'missing')}; "
                    f"tokens={tokens or 'none'}."
                ),
                "Regenerate the source-worktree handoff freshness audit before rebuilding the payload.",
            ),
            check_doc(DELIVERABLE, "Deliverable current snapshot", tokens),
            check_doc(FINAL_HANDOFF, "Final handoff current snapshot", tokens),
            check_doc(CHECKLIST, "Submission checklist current snapshot", tokens),
        ]

    required_files = (
        PDF_VISUAL,
        READINESS,
        PAYLOAD_ARCHIVE,
        REGISTRY_MANIFEST,
        SOURCE_PRIVACY,
        COMPARISON_VALIDITY,
        NOVELTY_SCORECARD,
        MCTS_BUDGET_POLICY,
    )
    missing_files = [rel(path) for path in required_files if not path.exists()]
    tokens = snapshot_tokens(snapshot)
    outputs_ok = (
        not missing_files
        and snapshot["author_pages"] > 0
        and snapshot["anonymous_pages"] > 0
        and snapshot["readiness_pass"] > 0
        and snapshot["readiness_author_input"] == 1
        and snapshot["payload_files"] > 0
        and snapshot["registry_families"] > 0
        and snapshot["strict_local_path_leaks"] == 0
        and snapshot["comparison_needs_revision"] == 0
        and snapshot["novelty_needs_revision"] == 0
        and snapshot["budget_pairs"] == 160
        and snapshot["budget_run_pareto"] < snapshot["budget_pairs"]
        and snapshot["budget_score_vs_resource_pct"] <= -3.0
        and snapshot["budget_time_vs_pareto_pct"] < 0.0
    )
    return [
        row(
            "Current audit outputs are readable",
            "pass" if outputs_ok else "needs revision",
            f"missing_files={missing_files or 'none'}; snapshot={snapshot}.",
            "Regenerate the terminal audits before refreshing public handoff docs.",
        ),
        check_doc(DELIVERABLE, "Deliverable current snapshot", tokens),
        check_doc(FINAL_HANDOFF, "Final handoff current snapshot", tokens),
        check_doc(CHECKLIST, "Submission checklist current snapshot", tokens),
    ]


def write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(path: Path, rows: list[dict[str, str]], snapshot: dict[str, object]) -> None:
    counts = status_counts(rows)
    tokens = snapshot_tokens(snapshot)
    lines = [
        "# Public Handoff Freshness Audit",
        "",
        "This terminal audit checks that the public handoff documents expose the current machine-generated package snapshot.",
        "",
        "## Status counts",
        "",
    ]
    lines.extend(f"- {status}: {count}" for status, count in sorted(counts.items()))
    lines.extend(
        [
            "",
            "## Current snapshot tokens",
            "",
        ]
    )
    lines.extend(f"- `{token}`" for token in tokens)
    lines.extend(
        [
            "",
            "| item | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {item['item']} | {item['status']} | {item['evidence']} | {item['next_action']} |"
        for item in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]], snapshot: dict[str, object]) -> None:
    counts = status_counts(rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "extracted_payload_mode": EXTRACTED_PAYLOAD_MODE,
        "snapshot": snapshot,
        "documents": [rel(DELIVERABLE), rel(FINAL_HANDOFF), rel(CHECKLIST)],
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    snapshot = current_snapshot()
    rows = build_rows(snapshot)
    write_summary(SUMMARY, rows)
    write_analysis(ANALYSIS, rows, snapshot)
    write_manifest(MANIFEST, rows, snapshot)
    print(f"wrote {len(rows)} public handoff freshness row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
