#!/usr/bin/env python3
"""Generate the end-to-end method workflow table for the manuscript."""
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "stage": "Input normalization",
        "mechanism": "Convert a truth table, exported benchmark, or supplied term set into a square-free ANF monomial mask set M.",
        "invariant": "The term set must evaluate to the target Boolean function before any search step is trusted.",
        "artifact": "ANF terms, preset name, and source manifest.",
    },
    {
        "stage": "Candidate generation",
        "mechanism": "Generate direct ANF, FPRM polarity, common-factor, Boolean-ring linear-factor, affine, and depth-frontier candidates.",
        "invariant": "Every action must have an explicit GF(2) expansion back to the original variables.",
        "artifact": "Candidate logical plans with resource estimates.",
    },
    {
        "stage": "Search control",
        "mechanism": "Use neural action priors, MCTS/beam expansion, staged frontiers, sparse learned gates, and fitted-Q Pareto invocation to allocate the search budget.",
        "invariant": "Learned decisions rank or skip evaluations; they do not define semantic correctness.",
        "artifact": "Scored candidate pool and search-time diagnostics.",
    },
    {
        "stage": "Guarded selection",
        "mechanism": "Compare learned and expensive candidates with deterministic baselines, then apply Pareto filtering before active-score selection.",
        "invariant": "A selected plan must be a valid generated candidate and remains bounded by the stated guard and score model.",
        "artifact": "Selected logical plan and non-dominated archive entry.",
    },
    {
        "stage": "Circuit emission",
        "mechanism": "Expand the selected plan into X/CNOT/MCT compute-action-uncompute operations and compute logical resource counts.",
        "invariant": "The reported score is a ranking objective; T, CNOT, depth, gates, and ancilla are retained separately.",
        "artifact": "Logical circuit proxy and resource row.",
    },
    {
        "stage": "Verification and reporting",
        "mechanism": "Check the plan algebraically, check emitted-circuit ANF semantics, add full truth-table or phase checks where feasible, and write raw CSV plus manifest rows.",
        "invariant": "Paper comparisons use matched rows that pass the relevant semantic checks and exclude errors, skips, and timeouts.",
        "artifact": "raw_*.csv, summary_*.csv, manifest_*.json, and paper tables.",
    },
]


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("Resource-NMCTS", r"\method{}"),
        ("ANF", r"\anf{}"),
        ("FPRM", r"\fprm{}"),
        ("MCTS", r"\mcts{}"),
        ("CNOT", r"CNOT"),
        ("MCT", r"\mct{}"),
        ("GF(2)", r"GF(2)"),
        ("raw\\_*.csv", r"\texttt{raw\_*.csv}"),
        ("summary\\_*.csv", r"\texttt{summary\_*.csv}"),
        ("manifest\\_*.json", r"\texttt{manifest\_*.json}"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    escaped = escaped.replace("mask set M", r"mask set $\mathcal{M}$")
    return escaped


def write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROWS[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(ROWS)


def write_markdown(path: Path) -> None:
    lines = [
        "# Method Workflow Table",
        "",
        "This table summarizes the end-to-end Resource-NMCTS synthesis workflow and the verification invariant attached to each stage.",
        "",
        "| stage | mechanism | invariant | artifact |",
        "|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            "| {stage} | {mechanism} | {invariant} | {artifact} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}}",
        r"\toprule",
        r"Stage & Mechanism & Invariant & Artifact \\",
        r"\midrule",
    ]
    for row in ROWS:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["stage"]),
                latex_cell(row["mechanism"]),
                latex_cell(row["invariant"]),
                latex_cell(row["artifact"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_csv(RESULTS / "summary_method_workflow.csv")
    write_markdown(RESULTS / "analysis_method_workflow.md")
    write_latex(TABLES / "method_workflow.tex")
    print(f"wrote {RESULTS / 'summary_method_workflow.csv'}")
    print(f"wrote {RESULTS / 'analysis_method_workflow.md'}")
    print(f"wrote {TABLES / 'method_workflow.tex'}")


if __name__ == "__main__":
    main()
