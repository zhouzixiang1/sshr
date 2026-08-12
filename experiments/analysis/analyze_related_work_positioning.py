#!/usr/bin/env python3
"""Build a related-work positioning matrix for the submission draft."""
from __future__ import annotations

import csv
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "line": "BDD-based reversible synthesis",
        "representative_plain": "BDD reversible synthesis",
        "representative_latex": r"BDD reversible synthesis~\cite{wille2009bdd}",
        "main_lever": "Symbolic decision-diagram representation for large Boolean functions.",
        "gap": "Representation scalability does not by itself optimize T, CNOT, depth, gates, and ancilla jointly.",
        "paper_use": "Used as a representation-level baseline family, not as the proposed search space.",
    },
    {
        "line": "LUT/ROS-style oracle synthesis",
        "representative_plain": "ROS, STG benchmarks, and back-end-aware oracle synthesis",
        "representative_latex": r"ROS, STG benchmarks, and back-end-aware oracle synthesis~\cite{meuli2020ros,stgBenchmark,yu2025backend}",
        "main_lever": "Resource-aware LUT mapping, small-function optimum libraries, and downstream implementation-cost estimates.",
        "gap": "Full ROS garbage-management and hardware/back-end mapping are outside the logical-layer claim, and STG is a small-function optimum counterpoint.",
        "paper_use": "Used through a verified ROS-style LUT proxy, line-aware reselection stress tests, and a published STG counterpoint.",
    },
    {
        "line": "Recent oracle-resource and Boolean-encoding work",
        "representative_plain": "HRSE/ASDT oracle modeling, ESOP SAT oracles, and T-depth Boolean-circuit constructions",
        "representative_latex": r"HRSE/ASDT oracle modeling, ESOP SAT oracles, and T-depth Boolean-circuit constructions~\cite{li2026oracle,assaad2026esop,dutta2025tdepth}",
        "main_lever": "Improves oracle resource modeling, application-level Boolean encodings, or analytic T-depth bounds.",
        "gap": "These works motivate oracle-resource pressure but do not provide a neural MCTS ANF/FPRM term-search baseline.",
        "paper_use": "Used as recent adjacent oracle-resource context, not as direct experimental baselines.",
    },
    {
        "line": "XAG and multiplicative complexity",
        "representative_plain": "XAG compilation and multiplicative-complexity oracle cost",
        "representative_latex": r"XAG compilation and multiplicative-complexity oracle cost~\cite{meuli2019multiplicative,meuli2022xag}",
        "main_lever": "Separates XOR-linear structure from AND nodes as a non-Clifford proxy.",
        "gap": "A fixed network optimization flow may miss algebraic FPRM/ANF search actions and Pareto tradeoffs.",
        "paper_use": "Used through ABC, mockturtle, and CirKit probes plus exact small XAG lower-bound checks.",
    },
    {
        "line": "Logic and reversible toolchains",
        "representative_plain": "ABC, EPFL libraries, RevKit, mockturtle, Caterpillar, and CirKit",
        "representative_latex": r"ABC, EPFL libraries, RevKit, mockturtle, Caterpillar, and CirKit~\cite{brayton2010abc,soeken2018epfl,soeken2012revkit,revkit,mockturtle,caterpillar,cirkit}",
        "main_lever": "Mature optimization passes and reversible-synthesis flows.",
        "gap": "Tool output defines strong baselines but does not expose the neural/MCTS algebraic action policy.",
        "paper_use": "Used as external probes, API-level implementation-family checks, and exact-oracle reversible-synthesis comparisons.",
    },
    {
        "line": "SSHR geometric synthesis",
        "representative_plain": "Parallelotope-based CNOT-oriented synthesis",
        "representative_latex": r"Parallelotope-based CNOT-oriented synthesis~\cite{zheng2025sshr}",
        "main_lever": "Small-scale Boolean hypercube geometry targeting CNOT-oriented covers.",
        "gap": "The objective is CNOT-oriented and small-function focused, not a general resource-weighted AI search.",
        "paper_use": "Used as a CNOT-oriented small-function baseline; not used by the proposed method.",
    },
    {
        "line": "Learning-guided circuit synthesis",
        "representative_plain": "AlphaZero, diffusion, reinforcement learning, supervised search, MCTS, and ZX-guided synthesis",
        "representative_latex": r"AlphaZero, diffusion, reinforcement learning, supervised search, MCTS, and ZX-guided synthesis~\cite{tsaras2024shortcircuit,wang2023nestedmcts,weiden2023qseed,furrutter2024diffusion,rietsch2024unitary,valcarce2025dynamic,kremer2025nonclifford,dubal2025paulinetwork,riu2025rlzx,theissinger2026beyondrl,zhou2022qctmcts,machiya2026monteq}",
        "main_lever": "Learns or searches over circuit-design, unitary-synthesis, block-resynthesis, and circuit-transformation actions.",
        "gap": "Most targets are classical circuits, ansatz design, unitary synthesis, transpilation/block resynthesis, ZX rewriting, or Hamiltonian simulation rather than Boolean-oracle ANF/FPRM term search.",
        "paper_use": "Motivates neural/MCTS control while keeping actions verifiable at the Boolean-algebraic oracle layer.",
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
    )


def write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["line", "representative_plain", "main_lever", "gap", "paper_use"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in ROWS:
            writer.writerow({name: row[name] for name in fieldnames})


def write_markdown(path: Path) -> None:
    lines = [
        "# Related-Work Positioning Matrix",
        "",
        "This matrix records how each literature family is used in the manuscript argument.",
        "",
        "| line | representative work | main lever | paper use |",
        "|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            "| {line} | {representative_plain} | {main_lever} | {paper_use} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}}",
        r"\toprule",
        r"Line of work & Representative work & Main lever & Gap for this paper & Manuscript use \\",
        r"\midrule",
    ]
    for row in ROWS:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["line"]),
                row["representative_latex"],
                latex_cell(row["main_lever"]),
                latex_cell(row["gap"]),
                latex_cell(row["paper_use"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_csv(RESULTS / "summary_related_work_positioning.csv")
    write_markdown(RESULTS / "analysis_related_work_positioning.md")
    write_latex(TABLES / "related_work_positioning.tex")
    print(f"wrote {RESULTS / 'summary_related_work_positioning.csv'}")
    print(f"wrote {RESULTS / 'analysis_related_work_positioning.md'}")
    print(f"wrote {TABLES / 'related_work_positioning.tex'}")


if __name__ == "__main__":
    main()
