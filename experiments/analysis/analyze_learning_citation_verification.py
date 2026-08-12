#!/usr/bin/env python3
"""Verify source-backed positioning for learning-guided synthesis citations.

The general citation-support audit checks that BibTeX keys resolve and have
locators.  This focused audit checks the newer AI/MCTS related-work paragraph:
each cited work must carry a stable primary locator, a scope label, and a
manuscript boundary explaining why it is adjacent work rather than the same
Boolean-oracle synthesis benchmark.

The script is intentionally offline.  Live DOI/arXiv checks are part of author
due diligence; the rebuild verifies that the checked locators and boundaries
remain present in the submitted sources.
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
SUMMARY_OUT = RESULTS / "summary_learning_citation_verification.csv"
ANALYSIS_OUT = RESULTS / "analysis_learning_citation_verification.md"
MANIFEST_OUT = RESULTS / "manifest_learning_citation_verification.json"
TABLE_OUT = TABLES / "learning_citation_verification.tex"


@dataclass(frozen=True)
class ExpectedCitation:
    key: str
    title_fragment: str
    year: str
    locator_tokens: tuple[str, ...]
    primary_source: str
    verified_scope: str
    boundary: str
    context_tokens: tuple[str, ...]


EXPECTED = (
    ExpectedCitation(
        key="tsaras2024shortcircuit",
        title_fragment="ShortCircuit",
        year="2024",
        locator_tokens=("2408.09858",),
        primary_source="arXiv:2408.09858",
        verified_scope="AlphaZero-style classical Boolean/AIG circuit design",
        boundary="motivation only; not quantum Boolean-oracle ANF/FPRM resource synthesis",
        context_tokens=("ShortCircuit", "AlphaZero-style", "classical Boolean"),
    ),
    ExpectedCitation(
        key="wang2023nestedmcts",
        title_fragment="Automated Quantum Circuit Design With Nested Monte Carlo Tree Search",
        year="2023",
        locator_tokens=("10.1109/TQE.2023.3265709", "2207.00132"),
        primary_source="IEEE TQE / arXiv:2207.00132",
        verified_scope="nested MCTS for automated quantum ansatz/circuit design",
        boundary="adjacent MCTS design evidence; not Boolean-oracle term/factor search",
        context_tokens=("Nested", "automated ansatz", "circuit design"),
    ),
    ExpectedCitation(
        key="weiden2023qseed",
        title_fragment="Improving Quantum Circuit Synthesis with Machine Learning",
        year="2023",
        locator_tokens=("10.1109/QCE57702.2023.00093", "2306.05622"),
        primary_source="IEEE QCE / arXiv:2306.05622",
        verified_scope="learned seeding for unitary/circuit synthesis",
        boundary="unitary synthesis motivation; not logical Boolean-oracle benchmarking",
        context_tokens=("QSeed", "learn unitary", "circuit generators"),
    ),
    ExpectedCitation(
        key="furrutter2024diffusion",
        title_fragment="Quantum Circuit Synthesis with Diffusion Models",
        year="2024",
        locator_tokens=("10.1038/s42256-024-00831-9", "2311.02041"),
        primary_source="Nature Machine Intelligence / arXiv:2311.02041",
        verified_scope="diffusion-model circuit generation and unitary compilation",
        boundary="generative circuit model; not verified Boolean-algebraic oracle search",
        context_tokens=("diffusion models", "unitary", "circuit generators"),
    ),
    ExpectedCitation(
        key="rietsch2024unitary",
        title_fragment="Unitary Synthesis of Clifford+T Circuits with Reinforcement Learning",
        year="2024",
        locator_tokens=("10.1109/QCE60285.2024.00102", "2404.14865"),
        primary_source="IEEE QCE / arXiv:2404.14865",
        verified_scope="Gumbel AlphaZero for exact Clifford+T unitary synthesis",
        boundary="gate-by-gate unitary synthesis; not Boolean-function oracle synthesis",
        context_tokens=("Gumbel AlphaZero", "Clifford+T", "unitary synthesis"),
    ),
    ExpectedCitation(
        key="valcarce2025dynamic",
        title_fragment="Unitary Synthesis with AlphaZero via Dynamic Circuits",
        year="2025",
        locator_tokens=("2508.21217",),
        primary_source="arXiv:2508.21217",
        verified_scope="AlphaZero-inspired exact unitary synthesis with dynamic-circuit variants",
        boundary="discrete unitary subroutine synthesis; not Boolean-oracle resource search",
        context_tokens=("dynamic-circuit AlphaZero", "discrete", "unitary synthesis"),
    ),
    ExpectedCitation(
        key="kremer2025nonclifford",
        title_fragment="Optimizing the non-Clifford-count in unitary synthesis",
        year="2025",
        locator_tokens=("2509.21709",),
        primary_source="arXiv:2509.21709",
        verified_scope="RL optimization of T/CS count for exactly implementable unitaries",
        boundary="non-Clifford unitary objective; not multi-resource Boolean oracle synthesis",
        context_tokens=("non-Clifford", "counts", "unitary"),
    ),
    ExpectedCitation(
        key="dubal2025paulinetwork",
        title_fragment="Pauli Network Circuit Synthesis with Reinforcement Learning",
        year="2025",
        locator_tokens=("2503.14448",),
        primary_source="arXiv:2503.14448",
        verified_scope="RL resynthesis of Pauli-network blocks and transpiler passes",
        boundary="block resynthesis after circuits exist; not synthesis from Boolean functions",
        context_tokens=("Pauli-network", "blocks", "transpilation"),
    ),
    ExpectedCitation(
        key="riu2025rlzx",
        title_fragment="Reinforcement Learning Based Quantum Circuit Optimization via ZX-Calculus",
        year="2025",
        locator_tokens=("10.22331/q-2025-05-28-1758",),
        primary_source="Quantum 9, 1758",
        verified_scope="RL-guided ZX-calculus circuit optimization",
        boundary="ZX graph rewrite optimization; not ANF/FPRM oracle construction",
        context_tokens=("ZX", "rewrites", "reinforcement-learning"),
    ),
    ExpectedCitation(
        key="theissinger2026beyondrl",
        title_fragment="Beyond Reinforcement Learning: Fast and Scalable Quantum Circuit Synthesis",
        year="2026",
        locator_tokens=("2602.15146",),
        primary_source="arXiv:2602.15146",
        verified_scope="supervised residual-unitary estimates with stochastic beam search",
        boundary="generic residual unitary synthesis; not Boolean-oracle logical-resource search",
        context_tokens=("supervised-search", "residual unitary", "synthesis"),
    ),
    ExpectedCitation(
        key="zhou2022qctmcts",
        title_fragment="Quantum Circuit Transformation",
        year="2022",
        locator_tokens=("10.1145/3514239",),
        primary_source="ACM TODAES 27(6)",
        verified_scope="MCTS for quantum circuit transformation under connectivity constraints",
        boundary="hardware/connectivity transformation; explicitly outside this logical-layer scope",
        context_tokens=("connectivity constraints", "circuit transformation"),
    ),
    ExpectedCitation(
        key="machiya2026monteq",
        title_fragment="MonteQ",
        year="2026",
        locator_tokens=("2604.19029",),
        primary_source="arXiv:2604.19029",
        verified_scope="MCTS scheduling framework for Hamiltonian-simulation Pauli rotations",
        boundary="Hamiltonian-simulation scheduling; not Boolean-oracle term synthesis",
        context_tokens=("MonteQ", "Hamiltonian-simulation", "MCTS"),
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def normalize(text: str) -> str:
    text = text.replace(r"\mcts{}", "MCTS")
    text = text.replace(r"\method{}", "Resource-NMCTS")
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
    author_text = texts.get("author", "")
    anonymous_text = texts.get("anonymous", "")
    acm_text = texts.get("acm", "")
    related_text = texts.get("related_table", "")
    checks = {
        "bib": bool(entry),
        "author_cite": cite_present(author_text, expected.key),
        "anonymous_cite": cite_present(anonymous_text, expected.key),
        "acm_cite": cite_present(acm_text, expected.key),
        "related_table_cite": cite_present(related_text, expected.key),
        "title": normalize(expected.title_fragment) in entry_norm,
        "year": bool(re.search(rf"year\s*=\s*\{{?\s*{re.escape(expected.year)}\s*\}}?", entry_raw)),
        "locator": all(normalize(token) in entry_norm for token in expected.locator_tokens),
        "context": all(normalize(token) in combined_norm for token in expected.context_tokens),
    }
    missing = [name for name, ok in checks.items() if not ok]
    status = "pass" if not missing else "needs revision"
    return {
        "key": expected.key,
        "status": status,
        "primary_source": expected.primary_source,
        "verified_scope": expected.verified_scope,
        "boundary": expected.boundary,
        "evidence": f"missing={missing or 'none'}; locator_tokens={','.join(expected.locator_tokens)}.",
        "next_action": "Correct the BibTeX locator, related-work citation, or manuscript scope/boundary wording.",
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
        "logical-layer Boolean-oracle synthesizer",
        "not a hardware-routing or transpilation method",
        "not a gate-by-gate unitary generator",
        "not an SSHR parallelotope search",
    )
    boundary_missing = [token for token in boundary_tokens if normalize(token) not in normalize(combined)]
    rows.append(
        {
            "key": "learning_scope_boundary",
            "status": "pass" if not boundary_missing else "needs revision",
            "primary_source": "manuscript boundary text",
            "verified_scope": "global related-work boundary for learning-guided synthesis",
            "boundary": "keeps AI/MCTS citations as adjacent work unless they share Boolean-oracle ANF/FPRM synthesis scope",
            "evidence": f"missing_boundary_tokens={boundary_missing or 'none'}.",
            "next_action": "Restore the learning-guided synthesis boundary paragraph in the related-work section.",
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
        "# Learning-Citation Verification Audit",
        "",
        "This audit verifies that the learning-guided synthesis paragraph is source-backed and boundary-labeled. It is offline and checks DOI/arXiv/publisher locators already recorded in the BibTeX file.",
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
    shown = [row for row in rows if row["key"] != "learning_scope_boundary"]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.26\linewidth}>{\raggedright\arraybackslash}X}",
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
        "primary_sources": sorted({row["primary_source"] for row in rows if row["key"] != "learning_scope_boundary"}),
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
    print(f"wrote {len(rows)} learning-citation verification row(s)")
    if failures:
        print(f"warning: {failures} learning-citation verification row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
