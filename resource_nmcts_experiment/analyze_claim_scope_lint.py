#!/usr/bin/env python3
"""Lint manuscript and handoff text for unsupported scope claims.

The paper deliberately makes a bounded logical-layer claim: T-count and
weighted-score improvements for Boolean-oracle synthesis, with explicit
CNOT/depth/ancilla tradeoffs and no hardware-mapping assertion.  This script
turns that boundary into a lightweight, reproducible pre-submission check.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

SCAN_FILES = [
    PAPER,
    SUBMISSION_PACKAGE / "README.md",
    SUBMISSION_PACKAGE / "cover_letter_template.md",
    SUBMISSION_PACKAGE / "artifact_reproduction_guide.md",
    SUBMISSION_PACKAGE / "editor_screening_brief.md",
    SUBMISSION_PACKAGE / "reviewer_concern_brief.md",
    SUBMISSION_PACKAGE / "target_venue_brief.md",
    SUBMISSION_PACKAGE / "author_declarations_template.md",
    SUBMISSION_PACKAGE / "submission_checklist.md",
]

REQUIRED_BOUNDARIES = [
    {
        "item": "logical-layer scope",
        "needles": ["logical-layer"],
        "evidence": "Manuscript and support files identify the contribution as logical-layer oracle synthesis.",
    },
    {
        "item": "hardware mapping excluded",
        "needles": ["not a hardware-mapped", "does not include hardware mapping", "does not claim hardware mapping"],
        "evidence": "Hardware mapping, routing, scheduling, and noise modeling are explicitly outside scope.",
    },
    {
        "item": "universal dominance excluded",
        "needles": ["not a hardware-mapped, depth-only, or universal-dominance claim", "not universal dominance", "Do not claim universal dominance", "No claim of universal"],
        "evidence": "The text excludes universal dominance over all resources and baselines.",
    },
    {
        "item": "multi-resource tradeoff reported",
        "needles": ["CNOT", "depth", "ancilla", "tradeoff"],
        "evidence": "The text keeps CNOT, depth, and ancilla as explicit tradeoff dimensions.",
    },
    {
        "item": "phase/Rz branch bounded",
        "needles": ["phase/Rz", "not a final Clifford+T", "does not output approximate rotation sequences"],
        "evidence": "The phase/Rz branch is framed as a logical proxy rather than a final Clifford+T compiler.",
    },
]


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    rationale: str


UNSUPPORTED_PATTERNS = [
    Pattern(
        "hardware mapping claim",
        re.compile(r"\b(?:hardware[- ]mapped|hardware mapping|routing|native[- ]gate scheduling|noise[- ]aware|noise modeling|magic[- ]state[- ]factory)\b", re.IGNORECASE),
        "Hardware mapping and physical-resource claims are outside the current logical-layer evidence.",
    ),
    Pattern(
        "universal dominance claim",
        re.compile(
            r"\b(?:universal[- ]dominance|dominates every metric|outperforms all(?: methods| baselines| tools)?|all metrics|complete dominance)\b",
            re.IGNORECASE,
        ),
        "The paper supports T-count and weighted-score advantages, not all-metric dominance.",
    ),
    Pattern(
        "unqualified optimality claim",
        re.compile(r"\b(?:optimal|optimality|state[- ]of[- ]the[- ]art|SOTA)\b", re.IGNORECASE),
        "Optimality and state-of-the-art language require stronger exhaustive or venue-specific evidence.",
    ),
    Pattern(
        "full external reproduction claim",
        re.compile(r"\b(?:full ROS|complete ROS|fully reproduced ROS|final Clifford\+T|full hardware compiler)\b", re.IGNORECASE),
        "The ROS and RevKit branches are bounded probes, not full external compiler reproductions.",
    ),
]

GUARD_TOKENS = [
    "not ",
    "no claim",
    "no ",
    "does not",
    "do not",
    "without ",
    "before ",
    "outside",
    "excluded",
    "intentionally absent",
    "scope boundary",
    "not supported",
    "not a",
    "not an",
    "rather than",
]


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def context_window(text: str, start: int, end: int, size: int = 180) -> str:
    left = max(0, start - size)
    right = min(len(text), end + size)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def is_guarded(window: str) -> bool:
    lower = window.lower()
    return any(token in lower for token in GUARD_TOKENS)


def boundary_rows(text_by_file: dict[Path, str]) -> list[dict[str, str]]:
    corpus = "\n".join(text_by_file.values())
    corpus_lower = corpus.lower()
    rows: list[dict[str, str]] = []
    for item in REQUIRED_BOUNDARIES:
        found = [needle for needle in item["needles"] if needle.lower() in corpus_lower]
        rows.append(
            {
                "check_type": "required_boundary",
                "item": item["item"],
                "status": "pass" if found else "needs revision",
                "file": "multiple",
                "line": "",
                "matched_text": "; ".join(found) if found else "",
                "evidence": item["evidence"],
                "next_action": "Keep this boundary visible in the manuscript and submission handoff files."
                if found
                else "Add an explicit scope/boundary sentence before submission.",
            }
        )
    return rows


def unsupported_rows(text_by_file: dict[Path, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path, text in text_by_file.items():
        for pattern in UNSUPPORTED_PATTERNS:
            for match in pattern.regex.finditer(text):
                window = context_window(text, match.start(), match.end())
                guarded = is_guarded(window)
                rows.append(
                    {
                        "check_type": "unsupported_claim",
                        "item": pattern.name,
                        "status": "guarded" if guarded else "needs revision",
                        "file": rel(path),
                        "line": str(line_number(text, match.start())),
                        "matched_text": window,
                        "evidence": pattern.rationale,
                        "next_action": "No action if the surrounding sentence is explicitly negative or limiting."
                        if guarded
                        else "Revise the sentence so it is bounded by the logical-layer evidence.",
                    }
                )
    return rows


def build_rows() -> list[dict[str, str]]:
    text_by_file = {path: read_text(path) for path in SCAN_FILES if path.exists()}
    rows = boundary_rows(text_by_file)
    rows.extend(unsupported_rows(text_by_file))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["check_type", "item", "status", "file", "line", "matched_text", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Claim Scope Lint",
        "",
        "This audit scans the manuscript and human-facing submission files for scope boundaries and unsupported overclaim language.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    unresolved = [row for row in rows if row["status"] == "needs revision"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pass` means a required boundary phrase is present.",
            "- `guarded` means a risky phrase appears only in a limiting or negative sentence.",
            "- `needs revision` means either a required boundary is missing or a risky phrase is not locally guarded.",
            "",
        ]
    )
    if unresolved:
        lines.extend(["## Items needing revision", ""])
        for row in unresolved:
            where = row["file"] if not row["line"] else f"{row['file']}:{row['line']}"
            lines.append(f"- {row['item']} at {where}: {row['matched_text'] or row['evidence']}")
        lines.append("")
    lines.extend(
        [
            "## Full rows",
            "",
            "| check type | item | status | file | line | matched text | next action |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {check_type} | {item} | {status} | {file} | {line} | {matched_text} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    manifest = {
        "name": "claim_scope_lint",
        "scan_files": [rel(path) for path in SCAN_FILES if path.exists()],
        "status_counts": counts,
        "unresolved_count": counts.get("needs revision", 0),
        "required_boundary_count": sum(1 for row in rows if row["check_type"] == "required_boundary"),
        "unsupported_claim_hit_count": sum(1 for row in rows if row["check_type"] == "unsupported_claim"),
        "outputs": [
            rel(RESULTS / "analysis_claim_scope_lint.md"),
            rel(RESULTS / "summary_claim_scope_lint.csv"),
            rel(RESULTS / "manifest_claim_scope_lint.json"),
        ],
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(RESULTS / "summary_claim_scope_lint.csv", rows)
    write_markdown(RESULTS / "analysis_claim_scope_lint.md", rows)
    write_manifest(RESULTS / "manifest_claim_scope_lint.json", rows)
    unresolved = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {RESULTS / 'summary_claim_scope_lint.csv'}")
    print(f"wrote {RESULTS / 'analysis_claim_scope_lint.md'}")
    print(f"wrote {RESULTS / 'manifest_claim_scope_lint.json'}")
    print(f"unresolved claim-scope items: {unresolved}")


if __name__ == "__main__":
    main()
