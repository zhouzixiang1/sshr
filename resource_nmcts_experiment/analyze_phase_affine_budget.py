#!/usr/bin/env python3
"""Compare two Affine-FPRM phase-search budgets on matched functions."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
TABLES = Path(__file__).resolve().parent / "paper_latex" / "tables"

METHODS = [
    "phase_parity_affine_fprm_opt_score",
    "phase_parity_affine_fprm_opt_rz1",
    "phase_parity_affine_fprm_opt_tperrz30",
]

METRICS = [
    "score",
    "score_rz1",
    "score_synth_tperrz30",
    "rz_non_clifford",
    "rz_total",
    "CNOT",
    "depth",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def usable_lookup(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    out = {}
    for row in read_csv(path):
        if row.get("error") or row.get("skipped"):
            continue
        out[(row["method"], row["name"])] = row
    return out


def compare_values(target: list[float], baseline: list[float]) -> dict[str, object]:
    wins = sum(1 for a, b in zip(target, baseline) if a < b)
    losses = sum(1 for a, b in zip(target, baseline) if a > b)
    ties = sum(1 for a, b in zip(target, baseline) if a == b)
    relatives = [(a - b) / max(abs(b), 1.0) for a, b in zip(target, baseline)]
    return {
        "pairs": len(target),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": sum(relatives) / len(relatives) if relatives else 0.0,
        "target_mean": sum(target) / len(target) if target else 0.0,
        "baseline_mean": sum(baseline) / len(baseline) if baseline else 0.0,
    }


def build_rows(target_path: Path, baseline_path: Path, label: str) -> list[dict[str, object]]:
    target_rows = usable_lookup(target_path)
    baseline_rows = usable_lookup(baseline_path)
    out: list[dict[str, object]] = []
    for method in METHODS:
        target_subset = [
            row for (row_method, _), row in target_rows.items()
            if row_method == method and (row_method, row["name"]) in baseline_rows
        ]
        for metric in METRICS:
            target_values = [float(row[metric]) for row in target_subset]
            baseline_values = [float(baseline_rows[(method, row["name"])][metric]) for row in target_subset]
            out.append(
                {
                    "comparison": label,
                    "method": method,
                    "metric": metric,
                    **compare_values(target_values, baseline_values),
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "comparison",
        "method",
        "metric",
        "pairs",
        "wins",
        "losses",
        "ties",
        "mean_relative",
        "target_mean",
        "baseline_mean",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{100 * value:+.2f}%"


def latex_pct(value: float) -> str:
    return f"${100 * value:+.2f}\\%$"


def write_markdown(path: Path, rows: list[dict[str, object]], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    focus = [
        ("phase_parity_affine_fprm_opt_score", "score"),
        ("phase_parity_affine_fprm_opt_rz1", "score_rz1"),
        ("phase_parity_affine_fprm_opt_tperrz30", "score_synth_tperrz30"),
        ("phase_parity_affine_fprm_opt_tperrz30", "rz_non_clifford"),
        ("phase_parity_affine_fprm_opt_tperrz30", "rz_total"),
        ("phase_parity_affine_fprm_opt_tperrz30", "CNOT"),
        ("phase_parity_affine_fprm_opt_tperrz30", "depth"),
    ]
    by_key = {(row["method"], row["metric"]): row for row in rows}
    lines = [
        "# Phase Affine Budget Comparison",
        "",
        f"Comparison: {label}.  Negative mean relative values favor the wider target search.",
        "",
        "| method | metric | pairs | W/L/T | target mean | baseline mean | mean relative |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for key in focus:
        row = by_key[key]
        lines.append(
            f"| {row['method']} | {row['metric']} | {row['pairs']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | "
            f"{float(row['target_mean']):.2f} | {float(row['baseline_mean']):.2f} | "
            f"{pct(float(row['mean_relative']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Increasing the affine transform budget gives a monotone selected-result improvement for the matched rank metric because the budget-32 candidates are contained in the wider search space for the same seed and deterministic prefix.",
            "- The strongest paper-facing row is the `score_synth_tperrz30` comparison for `phase_parity_affine_fprm_opt_tperrz30`: it isolates the phase/Rz cost proxy used against RevKit.",
            "- This is still a logic-layer phase-polynomial search result, not a hardware-mapped rotation synthesis result.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    focus = [
        ("phase_parity_affine_fprm_opt_score", "score", r"score target"),
        ("phase_parity_affine_fprm_opt_rz1", "score_rz1", r"score+1/Rz target"),
        ("phase_parity_affine_fprm_opt_tperrz30", "score_synth_tperrz30", r"$T/R_z=30$ target"),
        ("phase_parity_affine_fprm_opt_tperrz30", "rz_non_clifford", r"non-Clifford Rz"),
        ("phase_parity_affine_fprm_opt_tperrz30", "rz_total", r"total Rz"),
        ("phase_parity_affine_fprm_opt_tperrz30", "CNOT", r"CNOT"),
        ("phase_parity_affine_fprm_opt_tperrz30", "depth", r"depth"),
    ]
    by_key = {(row["method"], row["metric"]): row for row in rows}
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrr}\n")
        f.write("\\toprule\n")
        f.write("Metric & Pairs & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for method, metric, label in focus:
            row = by_key[(method, metric)]
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            f.write(f"{label} & {row['pairs']} & {wlt} & {latex_pct(float(row['mean_relative']))} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=RESULTS / "raw_phase_parity_affine_wide128.csv")
    parser.add_argument("--baseline", type=Path, default=RESULTS / "raw_phase_parity_affine.csv")
    parser.add_argument("--label", default="Affine-FPRM transform-budget 128 vs 32")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_affine_budget_wide128_vs_32.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_affine_budget_wide128_vs_32.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_affine_budget_wide128_vs_32.tex")
    args = parser.parse_args()

    rows = build_rows(args.target, args.baseline, args.label)
    write_csv(args.summary, rows)
    write_markdown(args.analysis, rows, args.label)
    write_latex(args.latex_out, rows)
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
