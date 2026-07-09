#!/usr/bin/env python3
"""Write the comparison-role and claim-boundary matrix for the manuscript.

The quantitative evidence matrix reports coverage and headline outcomes.  This
companion table records why each baseline family is included, what claim it can
support, and which stronger claims are deliberately excluded.
"""
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "comparison_role": "Primary resource-efficiency baselines",
        "methods": "Direct ANF, AND-direct ANF, ESOP beam/MILP, BDD/ABC-ESOP, SSHR-H/SSHR-I",
        "why_it_matters": "These methods solve the same bit-flip Boolean-oracle task under the paper's logical resource model.",
        "supported_claim": "Resource-NMCTS improves T-count and weighted score on matched small functions while SSHR remains a strong CNOT counterpoint.",
        "excluded_claim": "Does not prove universal CNOT, depth, ancilla, or hardware-level optimality.",
    },
    {
        "comparison_role": "External logic-network probes",
        "methods": "ABC AIG/XAG/LUT, ROS-style LUT and garbage-budget proxy, mockturtle KLUT-to-XAG, CirKit AIG/MC",
        "why_it_matters": "They test whether mature Boolean-network optimization already removes the apparent advantage over direct algebraic baselines.",
        "supported_claim": "The score advantage persists against stronger exported-network and official-header tool probes.",
        "excluded_claim": "Does not reproduce full ROS SAT garbage management or reversible/hardware mapping.",
    },
    {
        "comparison_role": "Exact reversible-synthesis probe",
        "methods": "Legacy RevKit CLI TBS/DBS/RMS exact-oracle portfolio",
        "why_it_matters": "It embeds each function as (x,y)->(x,y xor f(x)) and checks a genuine reversible-synthesis toolchain.",
        "supported_claim": "Resource-NMCTS has lower T-count and weighted score against this portfolio but pays more auxiliary lines.",
        "excluded_claim": "Does not imply lower line count, routed depth, or mapped Clifford+T cost.",
    },
    {
        "comparison_role": "Phase/Rz branch",
        "methods": "RevKit oracle_synth, phase-parity ANF, fixed-polarity FPRM, affine FPRM, learned phase shortlist",
        "why_it_matters": "It tests whether the same search framing extends to phase-oracle and affine-preconditioned Rz cost proxies.",
        "supported_claim": "Affine and learned candidate pruning improve verified logical phase/Rz proxy objectives.",
        "excluded_claim": "Not a final Clifford+T decomposition; only a coarse sequence-smoke audit emits bounded single-qubit strings.",
    },
    {
        "comparison_role": "Internal search ablations",
        "methods": "No-MCTS portfolio, learned prior off, guard off, Pareto archive off, depth-frontier variants, sparse gate",
        "why_it_matters": "They separate representation effects from the contribution of search, neural ranking, guards, and budget control.",
        "supported_claim": "AI-guided search and guards add measurable gains or time savings beyond deterministic construction.",
        "excluded_claim": "Does not support a claim that deep reinforcement learning alone causes the whole improvement.",
    },
    {
        "comparison_role": "Scaling and correctness bridges",
        "methods": "n=20,24,28,32,40 term-set symbolic runs; n=48,56,64 ultra-scale symbolic stress; n=21-30 complete truth-table bridge rows",
        "why_it_matters": "They push semantic checks beyond the small truth-table slice while keeping full verification where still feasible.",
        "supported_claim": "The emitted logical-layer circuits remain symbolically and bridge-truth-table verified at larger dimensions.",
        "excluded_claim": "Does not make exhaustive high-dimensional truth-table benchmarking feasible or complete.",
    },
    {
        "comparison_role": "Trade-off audits",
        "methods": "Raw multi-resource dominance, line-aware LUT reselection, schedule proxy, sparse-threshold sweep",
        "why_it_matters": "They prevent a weighted-score result from hiding CNOT, depth, line-count, or planning-time tradeoffs.",
        "supported_claim": "The method occupies a strong T/score point with explicit depth, CNOT, ancilla, and runtime boundaries.",
        "excluded_claim": "Does not justify reporting a single-metric victory as complete dominance.",
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
        ("SSHR-H/SSHR-I", r"SSHR-H/SSHR-I"),
        ("Rz", r"\rz{}"),
        ("n=20,24,28,32,40", r"$n=20$, 24, 28, 32, 40"),
        ("n=48,56,64", r"$n=48$, 56, 64"),
        ("n=21-30", r"$n=21$--$30$"),
        ("n=21-25", r"$n=21$--$25$"),
        ("T-count", r"T-count"),
        ("CNOT", r"CNOT"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    escaped = escaped.replace("(x,y)->(x,y xor f(x))", r"$(x,y)\mapsto(x,y\oplus f(x))$")
    return escaped


def write_csv(path: Path) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROWS[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(ROWS)


def write_markdown(path: Path) -> None:
    lines = [
        "# Baseline Claim Matrix",
        "",
        "This table explains the role of each comparison family in the paper's argument.",
        "",
        "| comparison role | methods | supported claim | excluded claim |",
        "|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            "| {comparison_role} | {methods} | {supported_claim} | {excluded_claim} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.21\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.21\linewidth}>{\raggedright\arraybackslash}p{0.19\linewidth}}",
        r"\toprule",
        r"Role & Compared methods & Why it matters & Supported claim & Excluded claim \\",
        r"\midrule",
    ]
    for row in ROWS:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["comparison_role"]),
                latex_cell(row["methods"]),
                latex_cell(row["why_it_matters"]),
                latex_cell(row["supported_claim"]),
                latex_cell(row["excluded_claim"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_csv(RESULTS / "summary_baseline_claim_matrix.csv")
    write_markdown(RESULTS / "analysis_baseline_claim_matrix.md")
    write_latex(TABLES / "baseline_claim_matrix.tex")
    print(f"wrote {RESULTS / 'summary_baseline_claim_matrix.csv'}")
    print(f"wrote {RESULTS / 'analysis_baseline_claim_matrix.md'}")
    print(f"wrote {TABLES / 'baseline_claim_matrix.tex'}")


if __name__ == "__main__":
    main()
