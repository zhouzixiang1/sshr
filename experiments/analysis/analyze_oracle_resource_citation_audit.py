#!/usr/bin/env python3
"""Verify recent oracle-resource citation positioning.

This audit protects the manuscript against a common reviewer concern: recent
oracle-resource papers are relevant, but they should not be silently promoted
to same-task experimental baselines.  The check is offline and source-local: it
verifies BibTeX locators, citation presence across all manuscript variants, and
scope-boundary wording in the related-work section/table.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex"
TABLES = PAPER / "tables"
AUTHOR_TEX = PAPER / "resource_nmcts_submission_v1.tex"
ANONYMOUS_TEX = PAPER / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = PAPER / "resource_nmcts_submission_acm_tqc.tex"
REFERENCES = PAPER / "references.bib"
RELATED_TABLE = TABLES / "related_work_positioning.tex"
SUMMARY_OUT = RESULTS / "summary_oracle_resource_citation_audit.csv"
ANALYSIS_OUT = RESULTS / "analysis_oracle_resource_citation_audit.md"
MANIFEST_OUT = RESULTS / "manifest_oracle_resource_citation_audit.json"
TABLE_OUT = TABLES / "oracle_resource_citation_audit.tex"


@dataclass(frozen=True)
class ExpectedCitation:
    key: str
    title_fragment: str
    year: str
    locator_token: str
    primary_source: str
    verified_scope: str
    boundary: str
    context_tokens: tuple[str, ...]


EXPECTED = (
    ExpectedCitation(
        key="li2026oracle",
        title_fragment="Modeling and Resource Optimization for Quantum Oracles",
        year="2026",
        locator_token="2605.21380",
        primary_source="arXiv:2605.21380",
        verified_scope="hierarchical quantum-oracle resource modeling with space-depth tradeoffs",
        boundary="adjacent oracle-resource modeling; not neural MCTS ANF/FPRM term search",
        context_tokens=("HRSE/ASDT", "hierarchical oracle", "space--depth"),
    ),
    ExpectedCitation(
        key="assaad2026esop",
        title_fragment="Performance Gains in Quantum SAT Solvers Using ESOP Encoding",
        year="2026",
        locator_token="2605.16202",
        primary_source="arXiv:2605.16202",
        verified_scope="ESOP encoding for Grover-SAT oracle resource reduction",
        boundary="application-level SAT encoding; not a general Boolean-oracle synthesis baseline",
        context_tokens=("ESOP encodings", "Grover-SAT", "oracle costs"),
    ),
    ExpectedCitation(
        key="dutta2025tdepth",
        title_fragment="Optimal T depth quantum circuits for implementing arbitrary Boolean functions",
        year="2025",
        locator_token="2506.01542",
        primary_source="arXiv:2506.01542",
        verified_scope="analytic T-depth construction for arbitrary Boolean functions",
        boundary="T-depth construction theorem; not multi-resource learned search",
        context_tokens=("T-depth bounds", "arbitrary Boolean functions", "analytic"),
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def normalize(text: str) -> str:
    text = text.replace(r"\mcts{}", "MCTS")
    text = text.replace(r"\anf{}", "ANF")
    text = text.replace(r"\fprm{}", "FPRM")
    text = text.replace("--", "-")
    text = re.sub(r"[{}\\]", "", text)
    text = re.sub(r"[^A-Za-z0-9+:/.-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_bib_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    starts = list(re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))
    for index, match in enumerate(starts):
        start = match.start()
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        entries[match.group(1)] = text[start:end]
    return entries


def cite_present(text: str, key: str) -> bool:
    pattern = re.compile(r"\\cite[a-zA-Z*]*(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
    for match in pattern.finditer(text):
        if key in {part.strip() for part in match.group(1).split(",")}:
            return True
    return False


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def status_row(expected: ExpectedCitation, texts: dict[str, str], bib_entries: dict[str, str]) -> dict[str, str]:
    entry = bib_entries.get(expected.key, "")
    entry_norm = normalize(entry)
    entry_raw = entry.lower()
    combined_norm = normalize("\n".join(texts.values()))
    related_text = texts.get("related_table", "")
    checks = {
        "bib": bool(entry),
        "author_cite": cite_present(texts.get("author", ""), expected.key),
        "anonymous_cite": cite_present(texts.get("anonymous", ""), expected.key),
        "acm_cite": cite_present(texts.get("acm", ""), expected.key),
        "related_table_cite": cite_present(related_text, expected.key),
        "title": normalize(expected.title_fragment) in entry_norm,
        "year": bool(re.search(rf"year\s*=\s*\{{?\s*{re.escape(expected.year)}\s*\}}?", entry_raw)),
        "locator": normalize(expected.locator_token) in entry_norm,
        "context": all(normalize(token) in combined_norm for token in expected.context_tokens),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "key": expected.key,
        "status": "pass" if not missing else "needs revision",
        "primary_source": expected.primary_source,
        "verified_scope": expected.verified_scope,
        "boundary": expected.boundary,
        "evidence": f"missing={missing or 'none'}; locator_token={expected.locator_token}.",
        "next_action": "Restore the citation, BibTeX locator, or related-work boundary wording.",
    }


def build_rows() -> list[dict[str, str]]:
    texts = {
        "author": read_text(AUTHOR_TEX),
        "anonymous": read_text(ANONYMOUS_TEX),
        "acm": read_text(ACM_TEX),
        "related_table": read_text(RELATED_TABLE),
    }
    bib_entries = parse_bib_entries(read_text(REFERENCES))
    rows = [status_row(expected, texts, bib_entries) for expected in EXPECTED]
    combined = "\n".join(texts.values())
    boundary_tokens = (
        "adjacent context rather than neural MCTS ANF/FPRM term-search baselines",
        "not as direct experimental baselines",
    )
    missing_boundary = [token for token in boundary_tokens if normalize(token) not in normalize(combined)]
    rows.append(
        {
            "key": "oracle_resource_scope_boundary",
            "status": "pass" if not missing_boundary else "needs revision",
            "primary_source": "manuscript boundary text",
            "verified_scope": "global boundary for recent oracle-resource citations",
            "boundary": "keeps recent oracle-resource work as context unless it shares the same synthesis objective",
            "evidence": f"missing_boundary_tokens={missing_boundary or 'none'}.",
            "next_action": "Restore the recent-oracle related-work boundary paragraph and related-work table row.",
        }
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["key", "status", "primary_source", "verified_scope", "boundary", "evidence", "next_action"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Oracle-Resource Citation Audit",
        "",
        "This audit verifies recent oracle-resource citations and keeps them boundary-labeled as adjacent context rather than direct experimental baselines.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| key | status | primary source | verified scope | boundary | evidence |", "|---|---|---|---|---|---|"])
    for row in rows:
        lines.append(
            "| {key} | {status} | {primary_source} | {verified_scope} | {boundary} | {evidence} |".format(
                **{key: value.replace("|", "\\|") for key, value in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, str]]) -> None:
    shown = [row for row in rows if row["key"] != "oracle_resource_scope_boundary"]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.28\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Citation key & Primary source & Verified adjacent scope & Boundary in this paper \\",
        r"\midrule",
    ]
    for row in shown:
        lines.append(
            " & ".join(
                [
                    latex_escape(row["key"]),
                    latex_escape(row["primary_source"]),
                    latex_escape(row["verified_scope"]),
                    latex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "citation_rows": len(EXPECTED),
        "needs_revision_count": counts.get("needs revision", 0),
        "status_counts": dict(sorted(counts.items())),
        "primary_sources": sorted({row["primary_source"] for row in rows if row["key"] != "oracle_resource_scope_boundary"}),
        "checked_keys": [item.key for item in EXPECTED],
        "source_files": {
            "author_tex": rel(AUTHOR_TEX),
            "anonymous_tex": rel(ANONYMOUS_TEX),
            "acm_tex": rel(ACM_TEX),
            "references": rel(REFERENCES),
            "related_table": rel(RELATED_TABLE),
        },
        "outputs": {
            "summary": rel(SUMMARY_OUT),
            "analysis": rel(ANALYSIS_OUT),
            "manifest": rel(MANIFEST_OUT),
            "table": rel(TABLE_OUT),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY_OUT, rows)
    write_markdown(ANALYSIS_OUT, rows)
    write_table(TABLE_OUT, rows)
    write_manifest(MANIFEST_OUT, rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} oracle-resource citation row(s)")
    if failures:
        print(f"warning: {failures} oracle-resource citation row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
