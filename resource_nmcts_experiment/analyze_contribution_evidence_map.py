#!/usr/bin/env python3
"""Build the introduction-level contribution-to-evidence map."""
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "contribution": "Resource-constrained Boolean-oracle search formulation",
        "implementation": "ANF/FPRM term-set state, Boolean-ring and affine actions, guarded candidate selection, symbolic circuit emission.",
        "evidence_latex": r"Fig.~\ref{fig:pipeline}; Table~\ref{tab:related-positioning}",
        "evidence_plain": "pipeline figure; related-work positioning matrix",
        "boundary": "Logical-layer oracle synthesis only; no routing, native-gate mapping, or noise model.",
    },
    {
        "contribution": "Neural/MCTS resource-search workflow",
        "implementation": "Neural action priors, MCTS/beam/portfolio search, Pareto archive, frontier policies, staged and sparse learned gates.",
        "evidence_latex": r"Tables~\ref{tab:contribution}, \ref{tab:search-control-baseline-audit}, \ref{tab:learned-control-audit}; Fig.~\ref{fig:learned-control-summary}",
        "evidence_plain": "contribution decomposition, search-control baseline audit, learned-control audit, learned-control figure",
        "boundary": "The largest gains come from searchable algebraic actions plus guarded selection; the paper does not claim deep RL alone explains all gains.",
    },
    {
        "contribution": "Broad baseline and toolchain comparison",
        "implementation": "Direct ANF, ESOP beam/MILP, SSHR, ABC/BDD, ROS-style LUT, mockturtle, CirKit, RevKit CLI, and phase/Rz probes.",
        "evidence_latex": r"Tables~\ref{tab:baseline-claim-matrix}, \ref{tab:evidence-matrix}, \ref{tab:paired-statistics}; Fig.~\ref{fig:baselines}",
        "evidence_plain": "baseline claim matrix, evidence matrix, paired statistics, baseline figure",
        "boundary": "Strong T-count and weighted-score evidence, not universal CNOT/depth/ancilla dominance or full ROS reproduction.",
    },
    {
        "contribution": "High-dimensional and phase-search verification envelope",
        "implementation": "n=20,24,28,32,40 symbolic term-set checks, n=48,56,64 ultra-scale symbolic stress, n=21--26 complete truth-table bridges, Affine-FPRM phase search, learned phase shortlist.",
        "evidence_latex": r"Tables~\ref{tab:scale-audit}, \ref{tab:ultra-scale64-stress}, \ref{tab:ultra-scale64-resource-profile}, \ref{tab:validation}, \ref{tab:phase-policy-random}; Fig.~\ref{fig:validation}",
        "evidence_plain": "scale audit, ultra-scale stress and resource-profile tables, validation table, phase random-control table, validation figure",
        "boundary": "Large rows are logically and symbolically verified; complete truth-table enumeration remains limited to bridge slices.",
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
    return (
        latex_escape(text)
        .replace("ANF", r"\anf{}")
        .replace("FPRM", r"\fprm{}")
        .replace("MCTS", r"\mcts{}")
        .replace("CNOT", r"CNOT")
        .replace("n=20,24,28,32,40", r"$n=20$, 24, 28, 32, 40")
        .replace("n=48,56,64", r"$n=48$, 56, 64")
        .replace("n=21--26", r"$n=21$--$26$")
        .replace("n=21--25", r"$n=21$--$25$")
    )


def write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["contribution", "implementation", "evidence_plain", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in ROWS:
            writer.writerow({name: row[name] for name in fieldnames})


def write_markdown(path: Path) -> None:
    lines = [
        "# Contribution-to-Evidence Map",
        "",
        "This map links the introduction-level contribution claims to concrete manuscript evidence.",
        "",
        "| contribution | implementation | evidence | boundary |",
        "|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            "| {contribution} | {implementation} | {evidence_plain} | {boundary} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.24\linewidth}}",
        r"\toprule",
        r"Contribution & Implementation & Paper evidence & Boundary \\",
        r"\midrule",
    ]
    for row in ROWS:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["contribution"]),
                latex_cell(row["implementation"]),
                row["evidence_latex"],
                latex_cell(row["boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_csv(RESULTS / "summary_contribution_evidence_map.csv")
    write_markdown(RESULTS / "analysis_contribution_evidence_map.md")
    write_latex(TABLES / "contribution_evidence_map.tex")
    print(f"wrote {RESULTS / 'summary_contribution_evidence_map.csv'}")
    print(f"wrote {RESULTS / 'analysis_contribution_evidence_map.md'}")
    print(f"wrote {TABLES / 'contribution_evidence_map.tex'}")


if __name__ == "__main__":
    main()
