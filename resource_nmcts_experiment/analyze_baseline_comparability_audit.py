#!/usr/bin/env python3
"""Write a reviewer-facing baseline comparability audit.

The claim and evidence matrices say what was compared and what the headline
outcomes are.  This audit answers a different reviewer question: whether each
comparison is fair enough to support the stated claim, and what residual
abstraction mismatch remains.
"""
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "baseline_family": "Direct algebraic and ESOP baselines",
        "task_alignment": "Same bit-flip Boolean oracle target and the same logical resource model.",
        "fairness_control": "Matched n<=6 functions, complete truth-table checks, identical score coefficients, and paired per-function comparisons.",
        "residual_risk": "These baselines are representation-level constructions, not mature external compilers.",
        "usable_claim": "Primary evidence for lower T-count and weighted score under the paper's own oracle model.",
    },
    {
        "baseline_family": "SSHR-H and SSHR-I",
        "task_alignment": "Same small Boolean-function oracle setting, but with a CNOT-oriented parallelotope search objective.",
        "fairness_control": "Matched functions and resource extraction; SSHR-I timeout rows are separated from completed rows.",
        "residual_risk": "SSHR is optimized for CNOT structure and small n, so it is a counterpoint rather than the method's design parent.",
        "usable_claim": "Resource-NMCTS improves score and T-count while SSHR remains the strongest CNOT reference.",
    },
    {
        "baseline_family": "ABC/BDD and exported logic networks",
        "task_alignment": "Same exported Boolean functions, evaluated through logical AIG/XAG/LUT/BDD resource proxies.",
        "fairness_control": "Rows with errors, skips, or failed truth-table checks are excluded; paired comparisons use matched names.",
        "residual_risk": "Network-level counts are proxies and do not include reversible garbage management or quantum routing.",
        "usable_claim": "Mature classical logic optimization does not by itself remove the T/score advantage.",
    },
    {
        "baseline_family": "ROS-style LUT and XAG/AIG/API probes",
        "task_alignment": "Same benchmark functions pass through LUT, XAG, AIG, and Caterpillar API probes with export/readback checks where available.",
        "fairness_control": "The LUT proxy includes best-K, line-aware reselection, and an executable garbage-budget frontier; mockturtle, CirKit, and Caterpillar use official source/toolchain/API paths and row-level correctness checks.",
        "residual_risk": "These are not full ROS SAT garbage-management optimizers or hardware-mapped reversible flows.",
        "usable_claim": "The advantage persists beyond self-written baselines, with CirKit and Caterpillar exposing real CNOT/depth tradeoffs.",
    },
    {
        "baseline_family": "Legacy RevKit CLI exact-oracle portfolio",
        "task_alignment": "Each function is embedded as the exact reversible permutation (x,y)->(x,y xor f(x)).",
        "fairness_control": "TBS, DBS, and RMS are all run and reduced to a per-function best-score portfolio.",
        "residual_risk": "CNOT and depth are derived from Toffoli-control distributions; RevKit uses fewer auxiliary lines on most rows.",
        "usable_claim": "A genuine reversible-synthesis probe still favors Resource-NMCTS on T-count and score, but not on line count.",
    },
    {
        "baseline_family": "Phase/Rz baselines and learned shortlist",
        "task_alignment": "Same Boolean functions are evaluated as phase-oracle or affine-FPRM phase-search instances.",
        "fairness_control": "Rows are verified up to global phase; learned shortlists are checked against same-budget random controls and wide exact search.",
        "residual_risk": "The branch is a logical Rz/phase proxy and does not output rotation-synthesis sequences.",
        "usable_claim": "The search framing extends to verified phase/Rz proxies, but it is not a finished Clifford+T compiler.",
    },
    {
        "baseline_family": "High-dimensional symbolic and bridge checks",
        "task_alignment": "Large term-set instances and n=21--30 bridge functions test the same emitted logical oracle semantics.",
        "fairness_control": "Symbolic ANF/circuit checks cover all reported high-dimensional rows; bridge slices add complete truth-table checks.",
        "residual_risk": "Complete truth-table enumeration is limited to bridge slices and generated functions.",
        "usable_claim": "The large-scale evidence supports semantic correctness and scaling of the logical search, not exhaustive high-dimensional optimality.",
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
    escaped = escaped.replace("/", r"/\allowbreak{}")
    replacements = [
        ("Resource-NMCTS", r"\method{}"),
        ("ANF", r"\anf{}"),
        ("FPRM", r"\fprm{}"),
        ("MCTS", r"\mcts{}"),
        ("CNOT", r"CNOT"),
        ("Rz", r"\rz{}"),
        ("n<=6", r"$n\leq6$"),
        ("n=21--30", r"$n=21$--$30$"),
        ("n=21--25", r"$n=21$--$25$"),
        ("(x,y)->(x,y xor f(x))", r"$(x,y)\mapsto(x,y\oplus f(x))$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROWS[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(ROWS)


def write_markdown(path: Path) -> None:
    lines = [
        "# Baseline Comparability Audit",
        "",
        "This audit records why each baseline family is comparable enough for the manuscript's bounded claims, and where the comparison boundary remains.",
        "",
        "| baseline family | task alignment | fairness control | residual risk | usable claim |",
        "|---|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            "| {baseline_family} | {task_alignment} | {fairness_control} | {residual_risk} | {usable_claim} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}}",
        r"\toprule",
        r"Baseline family & Task alignment & Fairness control & Residual risk & Usable claim \\",
        r"\midrule",
    ]
    for row in ROWS:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["baseline_family"]),
                latex_cell(row["task_alignment"]),
                latex_cell(row["fairness_control"]),
                latex_cell(row["residual_risk"]),
                latex_cell(row["usable_claim"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    write_csv(RESULTS / "summary_baseline_comparability_audit.csv")
    write_markdown(RESULTS / "analysis_baseline_comparability_audit.md")
    write_latex(TABLES / "baseline_comparability_audit.tex")
    print(f"wrote {RESULTS / 'summary_baseline_comparability_audit.csv'}")
    print(f"wrote {RESULTS / 'analysis_baseline_comparability_audit.md'}")
    print(f"wrote {TABLES / 'baseline_comparability_audit.tex'}")


if __name__ == "__main__":
    main()
