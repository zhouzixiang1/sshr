#!/usr/bin/env python3
"""Audit the submission draft for paper-level readiness markers.

This does not judge scientific merit.  It checks whether the current LaTeX
submission draft exposes the elements reviewers and editors usually look for:
bounded claims, baseline fairness, reproducibility, availability, limitations,
and a clean compiled PDF.
"""
from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
REBUILD_SCRIPT = THIS_DIR / "rebuild_submission_package.sh"
ARCHIVE_ANALYSIS = RESULTS / "analysis_submission_archive_manifest.md"
ARCHIVE_SUMMARY = RESULTS / "summary_submission_archive_manifest.csv"
ARCHIVE_MANIFEST = RESULTS / "manifest_submission_archive_manifest.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def pdf_pages(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        proc = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return "unknown"
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return match.group(1) if match else "unknown"


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def abstract_word_count(text: str) -> int:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, flags=re.DOTALL)
    if not match:
        return 0
    abstract = match.group(1)
    abstract = re.sub(r"\\[a-zA-Z]+(?:\{[^{}]*\})?", " ", abstract)
    abstract = re.sub(r"[^A-Za-z0-9.%/-]+", " ", abstract)
    return len([word for word in abstract.split() if word])


def build_rows() -> list[dict[str, str]]:
    text = read_text(PAPER)
    pages = pdf_pages(PDF)
    lower = text.lower()
    todo_hits = re.findall(r"\b(?:todo|tbd|placeholder)\b", lower)
    abstract_words = abstract_word_count(text)
    rebuild_cited = "rebuild_submission_package.sh" in text or r"rebuild\_submission\_package.sh" in text

    rows = [
        {
            "item": "Bounded abstract claim",
            "status": "pass"
            if contains_all(text, [r"\begin{abstract}", "logical-layer", "not a hardware-mapped"])
            else "needs revision",
            "evidence": "Abstract states logical-layer scope and excludes hardware-mapped/depth-only claims.",
            "next_action": "Keep hardware and mapping claims out of the abstract unless new evidence is added.",
        },
        {
            "item": "Abstract concision",
            "status": "pass" if 180 <= abstract_words <= 320 else "needs revision",
            "evidence": f"Abstract word count is {abstract_words}.",
            "next_action": "Keep the abstract compact; detailed per-baseline numbers belong in Results tables.",
        },
        {
            "item": "Contribution-to-evidence chain",
            "status": "pass" if "tab:contribution-map" in text else "needs revision",
            "evidence": "Introduction includes a contribution-to-evidence map.",
            "next_action": "Update the map whenever a headline contribution changes.",
        },
        {
            "item": "Executable method workflow",
            "status": "pass" if "tab:method-workflow" in text else "needs revision",
            "evidence": "Method includes an end-to-end synthesis and verification workflow table.",
            "next_action": "Keep the workflow table aligned with new candidate generators or verification stages.",
        },
        {
            "item": "Baseline fairness and scope",
            "status": "pass"
            if contains_all(text, ["tab:baseline-claim-matrix", "tab:evidence-matrix", "tab:comparability-audit"])
            else "needs revision",
            "evidence": "Experimental design includes claim, evidence, and comparability matrices.",
            "next_action": "Keep cross-toolchain claims tied to the comparability audit.",
        },
        {
            "item": "Reproducibility evidence",
            "status": "pass" if "tab:reproducibility" in text else "needs revision",
            "evidence": "Manuscript includes compute, worker, artifact, and external-tool provenance table.",
            "next_action": "Rerun analyze_reproducibility_audit.py after adding scripts, tables, or figures.",
        },
        {
            "item": "Claim-to-artifact traceability",
            "status": "pass" if "tab:traceability-audit" in text else "needs revision",
            "evidence": "Manuscript includes a submission traceability audit linking claim families to scripts, data, tables, and figures.",
            "next_action": "Rerun analyze_submission_traceability_audit.py after adding or moving headline evidence.",
        },
        {
            "item": "Archive package manifest",
            "status": "pass"
            if contains_all(text, ["tab:archive-manifest", "submission archive manifest"])
            and ARCHIVE_ANALYSIS.exists()
            and ARCHIVE_SUMMARY.exists()
            and ARCHIVE_MANIFEST.exists()
            else "needs revision",
            "evidence": "Manuscript includes an archive-level payload manifest with generated CSV, Markdown, and JSON outputs.",
            "next_action": "Rerun analyze_submission_archive_manifest.py after adding tables, figures, scripts, models, or result files.",
        },
        {
            "item": "Derived package rebuild command",
            "status": "pass" if REBUILD_SCRIPT.exists() and rebuild_cited else "needs revision",
            "evidence": "A lightweight rebuild script is present and cited in Data and Code Availability.",
            "next_action": "Keep the rebuild script aligned with paper-facing analysis, figure, audit, and PDF outputs.",
        },
        {
            "item": "Limitations and failure modes",
            "status": "pass"
            if contains_all(text, ["Several limitations are deliberate", "full ROS reproduction", "not a hardware mapping"])
            else "needs revision",
            "evidence": "Discussion names logical-layer, ROS-proxy, RevKit-derived, and high-dimensional bridge boundaries.",
            "next_action": "Add any new negative result to Discussion rather than hiding it in tables.",
        },
        {
            "item": "Data and code availability",
            "status": "pass" if "Data and Code Availability" in text else "needs revision",
            "evidence": "Manuscript has an availability section pointing to scripts, CSVs, manifests, tables, and figures.",
            "next_action": "Replace repository-relative wording with an archival DOI or anonymous link at submission time if required.",
        },
        {
            "item": "Clean submission source",
            "status": "pass" if not todo_hits else "needs revision",
            "evidence": f"{len(todo_hits)} TODO/TBD/placeholder markers in submission TeX.",
            "next_action": "Remove all source placeholders before journal upload.",
        },
        {
            "item": "Compiled PDF artifact",
            "status": "pass" if pages not in {"missing", "unknown"} else "needs revision",
            "evidence": f"Compiled PDF detected with {pages} pages.",
            "next_action": "Run latexmk and visual spot checks after each table or figure change.",
        },
        {
            "item": "Author-specific declarations",
            "status": "needs author input",
            "evidence": "Funding, acknowledgements, competing interests, and final archival links are author-specific.",
            "next_action": "Complete declarations at the target journal's submission step.",
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Readiness Audit",
        "",
        "This audit checks paper-level readiness markers in `paper_latex/resource_nmcts_submission_v1.tex` and the compiled PDF.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| item | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_readiness_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_readiness_audit.md", rows)
    print(f"wrote {RESULTS / 'summary_submission_readiness_audit.csv'}")
    print(f"wrote {RESULTS / 'analysis_submission_readiness_audit.md'}")


if __name__ == "__main__":
    main()
