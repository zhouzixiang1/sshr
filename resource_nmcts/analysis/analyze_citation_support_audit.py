#!/usr/bin/env python3
"""Audit citation support for related-work and positioning claims.

This audit is intentionally mechanical.  It checks that the manuscript's main
literature families have cited BibTeX keys, that those keys resolve in
``references.bib``, and that each reference has at least one retrievable
locator such as DOI, URL, eprint, or howpublished.
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
PAPER_DIR = THIS_DIR / "paper_latex"
TABLES = PAPER_DIR / "tables"
AUTHOR_TEX = PAPER_DIR / "resource_nmcts_submission_v1.tex"
ANONYMOUS_TEX = PAPER_DIR / "resource_nmcts_submission_anonymous.tex"
REFERENCES = PAPER_DIR / "references.bib"
RELATED_TABLE = TABLES / "related_work_positioning.tex"


@dataclass(frozen=True)
class CitationFamily:
    item: str
    required_keys: tuple[str, ...]
    anchor: str
    role: str


FAMILIES = (
    CitationFamily(
        item="BDD reversible synthesis",
        required_keys=("wille2009bdd",),
        anchor="BDD-based reversible synthesis",
        role="large-function symbolic representation baseline",
    ),
    CitationFamily(
        item="ROS and back-end-aware oracle synthesis",
        required_keys=("meuli2020ros", "stgBenchmark", "yu2025backend"),
        anchor="LUT/ROS-style oracle synthesis",
        role="resource-aware LUT/oracle synthesis and published small-function counterpoint boundary",
    ),
    CitationFamily(
        item="Recent oracle-resource and Boolean-encoding work",
        required_keys=("li2026oracle", "assaad2026esop", "dutta2025tdepth"),
        anchor="Recent oracle-resource and Boolean-encoding work",
        role="recent adjacent oracle-resource context and non-baseline boundary",
    ),
    CitationFamily(
        item="XAG and multiplicative complexity",
        required_keys=("meuli2019multiplicative", "meuli2022xag"),
        anchor="XAG and multiplicative complexity",
        role="non-Clifford proxy and logic-network comparison",
    ),
    CitationFamily(
        item="Logic and reversible toolchains",
        required_keys=("brayton2010abc", "soeken2018epfl", "soeken2012revkit", "revkit", "mockturtle", "caterpillar", "cirkit"),
        anchor="Logic and reversible toolchains",
        role="external synthesis and reversible-toolchain probes",
    ),
    CitationFamily(
        item="SSHR geometric synthesis",
        required_keys=("zheng2025sshr",),
        anchor="SSHR geometric synthesis",
        role="CNOT-oriented small-function baseline",
    ),
    CitationFamily(
        item="Learning-guided circuit synthesis",
        required_keys=(
            "tsaras2024shortcircuit",
            "wang2023nestedmcts",
            "weiden2023qseed",
            "furrutter2024diffusion",
            "rietsch2024unitary",
            "valcarce2025dynamic",
            "kremer2025nonclifford",
            "dubal2025paulinetwork",
            "riu2025rlzx",
            "theissinger2026beyondrl",
            "zhou2022qctmcts",
            "machiya2026monteq",
        ),
        anchor="Learning-guided circuit synthesis",
        role="neural/RL/MCTS positioning boundary",
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def tex_sources() -> dict[str, str]:
    sources = {
        rel(AUTHOR_TEX): read_text(AUTHOR_TEX),
        rel(ANONYMOUS_TEX): read_text(ANONYMOUS_TEX),
    }
    if TABLES.exists():
        for path in sorted(TABLES.glob("*.tex")):
            sources[rel(path)] = read_text(path)
    return sources


def extract_cite_keys(text: str) -> set[str]:
    keys: set[str] = set()
    pattern = re.compile(r"\\cite[a-zA-Z*]*(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
    for match in pattern.finditer(text):
        for key in match.group(1).split(","):
            clean = key.strip()
            if clean:
                keys.add(clean)
    return keys


def parse_bib_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    starts = list(re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))
    for index, match in enumerate(starts):
        key = match.group(1)
        start = match.start()
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        entries[key] = text[start:end]
    return entries


def has_locator(entry: str) -> bool:
    lowered = entry.lower()
    return any(token in lowered for token in ("doi =", "url =", "eprint =", "howpublished ="))


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def build_rows() -> list[dict[str, str]]:
    sources = tex_sources()
    all_tex = "\n".join(sources.values())
    related_text = read_text(RELATED_TABLE)
    cited_keys = extract_cite_keys(all_tex)
    related_keys = extract_cite_keys(related_text)
    bib_entries = parse_bib_entries(read_text(REFERENCES))
    bib_keys = set(bib_entries)

    rows: list[dict[str, str]] = []
    for family in FAMILIES:
        required = set(family.required_keys)
        missing_citations = sorted(required - cited_keys)
        missing_related = sorted(required - related_keys)
        missing_bib = sorted(required - bib_keys)
        missing_locator = sorted(key for key in required if key in bib_entries and not has_locator(bib_entries[key]))
        anchor_ok = family.anchor in related_text
        status = (
            "pass"
            if not missing_citations
            and not missing_related
            and not missing_bib
            and not missing_locator
            and anchor_ok
            else "needs revision"
        )
        rows.append(
            row(
                family.item,
                status,
                (
                    f"role={family.role}; required={','.join(family.required_keys)}; "
                    f"missing_citations={missing_citations or 'none'}; "
                    f"missing_related_table={missing_related or 'none'}; "
                    f"missing_bib={missing_bib or 'none'}; "
                    f"missing_locator={missing_locator or 'none'}; anchor_present={anchor_ok}."
                ),
                "Restore the citation in the related-work table, add the BibTeX entry, or add a DOI/URL/eprint locator.",
            )
        )

    unresolved = sorted(cited_keys - bib_keys)
    rows.append(
        row(
            "All cited keys resolve",
            "pass" if not unresolved else "needs revision",
            f"cited_keys={len(cited_keys)}; unresolved={unresolved or 'none'}.",
            "Add missing BibTeX entries or correct citation keys.",
        )
    )

    unused = sorted(bib_keys - cited_keys)
    rows.append(
        row(
            "All bibliography keys are cited",
            "pass" if not unused else "needs revision",
            f"bib_keys={len(bib_keys)}; unused={unused or 'none'}.",
            "Remove unused BibTeX entries or cite them in the manuscript if they support a claim.",
        )
    )

    missing_locator = sorted(key for key, entry in bib_entries.items() if not has_locator(entry))
    rows.append(
        row(
            "Bibliography locator coverage",
            "pass" if bib_entries and not missing_locator else "needs revision",
            f"bib_entries={len(bib_entries)}; missing_locator={missing_locator or 'none'}.",
            "Add DOI, URL, eprint, or howpublished fields to every reference entry.",
        )
    )

    bibliography_commands = {
        "author": r"\bibliography{references}" in read_text(AUTHOR_TEX),
        "anonymous": r"\bibliography{references}" in read_text(ANONYMOUS_TEX),
    }
    rows.append(
        row(
            "Bibliography included in both manuscripts",
            "pass" if all(bibliography_commands.values()) else "needs revision",
            f"bibliography_commands={bibliography_commands}.",
            "Restore the references bibliography command in both author and anonymous TeX sources.",
        )
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Citation Support Audit",
        "",
        "This audit checks that related-work positioning claims have cited BibTeX keys, that cited keys resolve in `references.bib`, and that references include retrievable locators.",
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
    counts = Counter(row["status"] for row in rows)
    sources = tex_sources()
    cited_keys = sorted(extract_cite_keys("\n".join(sources.values())))
    bib_entries = parse_bib_entries(read_text(REFERENCES))
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "families": len(FAMILIES),
        "cited_key_count": len(cited_keys),
        "bib_key_count": len(bib_entries),
        "needs_revision_count": counts.get("needs revision", 0),
        "status_counts": dict(sorted(counts.items())),
        "cited_keys": cited_keys,
        "bib_keys": sorted(bib_entries),
        "source_files": {
            "author_tex": rel(AUTHOR_TEX),
            "anonymous_tex": rel(ANONYMOUS_TEX),
            "references": rel(REFERENCES),
            "related_table": rel(RELATED_TABLE),
        },
        "outputs": {
            "summary": "results/summary_citation_support_audit.csv",
            "analysis": "results/analysis_citation_support_audit.md",
            "manifest": "results/manifest_citation_support_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_citation_support_audit.csv", rows)
    write_markdown(RESULTS / "analysis_citation_support_audit.md", rows)
    write_manifest(RESULTS / "manifest_citation_support_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} citation support row(s)")
    if failures:
        print(f"warning: {failures} citation support row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
