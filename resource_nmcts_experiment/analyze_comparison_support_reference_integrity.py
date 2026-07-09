#!/usr/bin/env python3
"""Check that comparison handoff files point to real evidence artifacts.

The Chinese comparison handoff documents are used when drafting cover-letter
text or reviewer replies.  This audit keeps their backticked evidence entry
points from drifting away from the generated result files and LaTeX tables.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

SOURCE_FILES = (
    SUBMISSION_PACKAGE / "COMPARISON_HANDOFF_zh.md",
    SUBMISSION_PACKAGE / "COMPARISON_SIGNIFICANCE_MATRIX_zh.md",
    SUBMISSION_PACKAGE / "reviewer_concern_brief.md",
)

SUMMARY = RESULTS / "summary_comparison_support_reference_integrity.csv"
ANALYSIS = RESULTS / "analysis_comparison_support_reference_integrity.md"
MANIFEST = RESULTS / "manifest_comparison_support_reference_integrity.json"

FILELIKE_SUFFIXES = (
    ".md",
    ".csv",
    ".json",
    ".tex",
    ".py",
    ".sh",
    ".pdf",
    ".bib",
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def backticked_file_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(r"`([^`\n]+)`", text):
        token = match.group(1).strip()
        if token.endswith(FILELIKE_SUFFIXES) or any(
            suffix in token for suffix in FILELIKE_SUFFIXES
        ):
            tokens.append(token)
    return tokens


def candidate_paths(token: str) -> list[Path]:
    cleaned = token.strip().strip(".,;:，。；：")
    path = Path(cleaned)
    basename = path.name
    candidates: list[Path] = []

    if path.parts and path.parts[0] in {"results", "paper_latex", "submission_package"}:
        candidates.append(THIS_DIR / path)

    if basename.startswith(("analysis_", "summary_", "manifest_", "raw_")):
        candidates.append(RESULTS / basename)

    if basename.endswith(".tex"):
        candidates.extend((TABLES / basename, THIS_DIR / basename))
    elif basename.endswith(".md"):
        candidates.extend((SUBMISSION_PACKAGE / basename, RESULTS / basename, THIS_DIR / basename))
    elif basename.endswith((".py", ".sh")):
        candidates.append(THIS_DIR / basename)
    elif basename.endswith(".bib"):
        candidates.extend((THIS_DIR / basename, THIS_DIR / "paper_latex" / basename))
    elif basename.endswith(".pdf"):
        candidates.extend(
            (
                THIS_DIR / basename,
                THIS_DIR / "paper_latex" / basename,
                THIS_DIR / "paper_latex" / "figures" / "submission_v36" / basename,
            )
        )

    # Preserve order while removing duplicates.
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def resolve_reference(token: str) -> tuple[str, list[str]]:
    candidates = candidate_paths(token)
    for candidate in candidates:
        if candidate.exists():
            return rel(candidate), [rel(path) for path in candidates]
    return "", [rel(path) for path in candidates]


def collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in SOURCE_FILES:
        text = read_text(source)
        if not text:
            rows.append(
                {
                    "source_file": rel(source),
                    "reference": "<source file missing>",
                    "resolved_path": "",
                    "status": "needs revision",
                    "candidate_paths": "",
                    "role": "source availability",
                }
            )
            continue
        for token in backticked_file_tokens(text):
            resolved, candidates = resolve_reference(token)
            rows.append(
                {
                    "source_file": rel(source),
                    "reference": token,
                    "resolved_path": resolved,
                    "status": "pass" if resolved else "needs revision",
                    "candidate_paths": "; ".join(candidates),
                    "role": "comparison evidence entrypoint",
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["source_file", "reference", "resolved_path", "status", "candidate_paths", "role"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Comparison Support Reference Integrity",
        "",
        "This audit checks that the Chinese comparison handoff files and reviewer brief point to existing evidence artifacts.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| source file | reference | resolved path | status | role |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {source_file} | `{reference}` | {resolved_path} | {status} | {role} |".format(**safe)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    missing = [row for row in rows if row["status"] != "pass"]
    counts = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in sorted({row["status"] for row in rows})
    }
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "files_scanned": [rel(path) for path in SOURCE_FILES],
        "reference_count": len(rows),
        "missing_count": len(missing),
        "status_counts": counts,
        "outputs": {
            "summary": "results/summary_comparison_support_reference_integrity.csv",
            "analysis": "results/analysis_comparison_support_reference_integrity.md",
            "manifest": "results/manifest_comparison_support_reference_integrity.json",
        },
        "missing_references": missing,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = collect_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_manifest(MANIFEST, rows)
    missing = sum(1 for row in rows if row["status"] != "pass")
    print(f"checked {len(rows)} comparison support references")
    if missing:
        print(f"warning: {missing} comparison support reference(s) need revision")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
