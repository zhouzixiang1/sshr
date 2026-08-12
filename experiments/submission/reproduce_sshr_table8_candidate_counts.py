#!/usr/bin/env python3
"""Reproduce the SSHR Table VIII candidate-space counts.

This is a bounded SSHR-facing reproduction, not a full rerun of every SSHR
random benchmark.  It executes the local SSHR parallelotope enumerator on the
full n=3..8 hypercubes and checks the resulting optimization-space sizes
against the reference counts recorded in the SSHR implementation.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import csv
import json
import os
import sys
import time
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

REFERENCE_COUNTS = {3: 49, 4: 257, 5: 1539, 6: 10299, 7: 75905, 8: 609441}


def load_sshr_modules():
    from src.sshr_lib.parallelotope_enum import enumerate_parallelotopes
    # paper_data.py is not vendored — use hardcoded reference counts
    TABLE_VIII_COUNTS = REFERENCE_COUNTS
    return TABLE_VIII_COUNTS, enumerate_parallelotopes


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def reproduce_counts() -> list[dict[str, object]]:
    table_counts, enumerate_parallelotopes = load_sshr_modules()
    rows: list[dict[str, object]] = []
    for n in range(3, 9):
        universe = list(range(1 << n))
        parallelotopes = enumerate_parallelotopes(universe, n)
        dim_ge_1 = len(parallelotopes)
        singletons = len(universe)
        sshr_count = dim_ge_1 + singletons
        esop_count = 3**n
        reference_count = int(table_counts.get(n, REFERENCE_COUNTS[n]))
        rows.append(
            {
                "n": n,
                "esop_count": esop_count,
                "parallelotope_dim_ge_1_count": dim_ge_1,
                "singleton_count": singletons,
                "sshr_count": sshr_count,
                "reference_sshr_count": reference_count,
                "factor_vs_esop": sshr_count / esop_count,
                "matches_reference": sshr_count == reference_count,
            }
        )
    return rows


def write_raw_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "n",
        "esop_count",
        "parallelotope_dim_ge_1_count",
        "singleton_count",
        "sshr_count",
        "reference_sshr_count",
        "factor_vs_esop",
        "matches_reference",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["factor_vs_esop"] = f"{float(row['factor_vs_esop']):.6f}"
            writer.writerow(out)


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    matching = sum(1 for row in rows if bool(row["matches_reference"]))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rows",
                "matching_rows",
                "all_match",
                "min_n",
                "max_n",
                "max_sshr_count",
                "status",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "rows": len(rows),
                "matching_rows": matching,
                "all_match": matching == len(rows),
                "min_n": min(int(row["n"]) for row in rows),
                "max_n": max(int(row["n"]) for row in rows),
                "max_sshr_count": max(int(row["sshr_count"]) for row in rows),
                "status": "pass" if matching == len(rows) else "needs revision",
            }
        )


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    matching = sum(1 for row in rows if bool(row["matches_reference"]))
    lines = [
        "# SSHR Table VIII Candidate-Count Reproduction",
        "",
        "This report reruns the local SSHR parallelotope enumerator on full n=3..8 hypercubes and compares the resulting candidate-space sizes with the Table VIII reference counts.",
        "",
        f"- rows: {len(rows)}",
        f"- matching rows: {matching}/{len(rows)}",
        f"- status: {'pass' if matching == len(rows) else 'needs revision'}",
        "",
        "| n | ESOP terms | SSHR candidates | Reference | Factor | Match |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {n} | {esop} | {sshr} | {ref} | {factor:.1f}x | {match} |".format(
                n=row["n"],
                esop=row["esop_count"],
                sshr=row["sshr_count"],
                ref=row["reference_sshr_count"],
                factor=float(row["factor_vs_esop"]),
                match="yes" if bool(row["matches_reference"]) else "no",
            )
        )
    lines.extend(
        [
            "",
            "The reproduction supports only the SSHR search-space anchor used in the comparison discussion.  It does not rerun SSHR-I Gurobi tables or every random benchmark from the SSHR paper.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabular}{rrrrr}",
        r"\toprule",
        r"$n$ & ESOP terms & SSHR candidates & Reference & Factor \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{n} & {esop} & {sshr} & {ref} & {factor:.1f}$\\times$ \\\\".format(
                n=tex_escape(str(row["n"])),
                esop=int(row["esop_count"]),
                sshr=int(row["sshr_count"]),
                ref=int(row["reference_sshr_count"]),
                factor=float(row["factor_vs_esop"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    matching = sum(1 for row in rows if bool(row["matches_reference"]))
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "source": "sshr_lib/ (vendored)",
        "rows": len(rows),
        "matching_rows": matching,
        "all_match": matching == len(rows),
        "min_n": min(int(row["n"]) for row in rows),
        "max_n": max(int(row["n"]) for row in rows),
        "max_sshr_count": max(int(row["sshr_count"]) for row in rows),
        "runtime_policy": "wall-clock timings are printed to the terminal only and are not stored in tracked artifacts",
        "reference_counts": REFERENCE_COUNTS,
        "outputs": {
            "raw": "results/raw_sshr_table8_candidate_counts.csv",
            "summary": "results/summary_sshr_table8_candidate_counts.csv",
            "analysis": "results/analysis_sshr_table8_candidate_counts.md",
            "manifest": "results/manifest_sshr_table8_candidate_counts.json",
            "table": "paper_latex/tables/sshr_table8_candidate_counts.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    start = time.perf_counter()
    rows = reproduce_counts()
    total_runtime = time.perf_counter() - start
    write_raw_csv(RESULTS / "raw_sshr_table8_candidate_counts.csv", rows)
    write_summary_csv(RESULTS / "summary_sshr_table8_candidate_counts.csv", rows)
    write_markdown(RESULTS / "analysis_sshr_table8_candidate_counts.md", rows)
    write_latex(TABLES / "sshr_table8_candidate_counts.tex", rows)
    write_manifest(RESULTS / "manifest_sshr_table8_candidate_counts.json", rows)
    matching = sum(1 for row in rows if bool(row["matches_reference"]))
    print(f"wrote SSHR Table VIII candidate-count reproduction: {matching}/{len(rows)} matched")
    print(f"runtime_seconds={total_runtime:.2f}")
    return 0 if matching == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
