#!/usr/bin/env python3
"""Generate ESOP-centered comparisons for the paper."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class BaselineSpec:
    label: str
    method: str
    source: str


TARGET = "and_pareto_resource_nmcts"
BASELINES = [
    BaselineSpec("Internal ESOP-MILP", "and_esop_milp", "internal"),
    BaselineSpec("ABC-ESOP export", "external_abc_esop", "external"),
]
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]


def load_usable(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        row
        for row in rows
        if not row.get("error")
        and not row.get("skipped")
        and str(row.get("correct", "True")) != "False"
    ]


def by_name(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["name"], {})[row["method"]] = row
    return out


def rel(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def fmt_int(value: float) -> str:
    return f"{int(round(value))}"


def fmt_pct(value: float) -> str:
    return f"{value:+.1f}\\%"


def latex_pct(value: float) -> str:
    return f"${fmt_pct(value)}$"


def joined_rows(
    internal: dict[str, dict[str, dict[str, str]]],
    external: dict[str, dict[str, dict[str, str]]],
    baseline: BaselineSpec,
) -> list[tuple[dict[str, str], dict[str, str]]]:
    pairs: list[tuple[dict[str, str], dict[str, str]]] = []
    for name, methods in sorted(internal.items()):
        target = methods.get(TARGET)
        if not target:
            continue
        baseline_row = methods.get(baseline.method)
        if baseline.source == "external":
            baseline_row = external.get(name, {}).get(baseline.method)
        if baseline_row:
            pairs.append((target, baseline_row))
    return pairs


def win_loss_tie(pairs: list[tuple[dict[str, str], dict[str, str]]], metric: str) -> tuple[int, int, int]:
    wins = losses = ties = 0
    for target, baseline in pairs:
        new = float(target[metric])
        old = float(baseline[metric])
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties


def aggregate(pairs: list[tuple[dict[str, str], dict[str, str]]]) -> dict[str, tuple[float, float, float]]:
    out: dict[str, tuple[float, float, float]] = {}
    for metric in METRICS:
        target_total = sum(float(target[metric]) for target, _ in pairs)
        baseline_total = sum(float(baseline[metric]) for _, baseline in pairs)
        out[metric] = (target_total, baseline_total, rel(target_total, baseline_total))
    return out


def write_latex_table(
    rows: list[dict[str, str]],
    out: Path,
) -> None:
    lines = [
        r"\begin{tabular}{@{}llrllrrrr@{}}",
        r"\toprule",
        r"$n$ & ESOP baseline & Func. & ESOP T/C/A & Ours T/C/A & $\Delta T$ & $\Delta$ CNOT & $\Delta A$ & Score W/L/T \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    row["n"],
                    row["baseline"],
                    row["functions"],
                    row["baseline_tca"],
                    row["target_tca"],
                    row["delta_t"],
                    row["delta_cnot"],
                    row["delta_ancilla"],
                    row["score_wlt"],
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(rows: list[dict[str, str]], out: Path) -> None:
    if not rows:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    internal_rows = load_usable(RESULTS / "raw_traditional_resource.csv")
    external_rows = load_usable(RESULTS / "raw_external_traditional_resource_n6.csv")
    internal = by_name(internal_rows)
    external = by_name(external_rows)

    summary_rows: list[dict[str, str]] = []
    latex_rows: list[dict[str, str]] = []
    markdown = [
        "# ESOP Baseline Analysis",
        "",
        (
            "This analysis uses Pareto-Resource-NMCTS as the reported method and "
            "compares it with ESOP baselines on exactly matched benchmark functions. "
            "The internal ESOP-MILP rows come from `raw_traditional_resource.csv`; "
            "the external ABC-ESOP rows come from `raw_external_traditional_resource_n6.csv`."
        ),
        "",
        (
            "The SSHR-paper ESOP table is not directly comparable unless the same "
            "function set and cost model are used.  The tables below are same-benchmark "
            "comparisons and are therefore the evidence used in the manuscript."
        ),
        "",
        "## Aggregate by baseline",
        "",
        "| baseline | functions | T ours/base/change | CNOT ours/base/change | ancilla ours/base/change | score ours/base/change | score W/L/T |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for spec in BASELINES:
        pairs = joined_rows(internal, external, spec)
        totals = aggregate(pairs)
        score_wlt = win_loss_tie(pairs, "score")
        markdown.append(
            "| "
            + " | ".join(
                [
                    spec.label,
                    str(len(pairs)),
                    f"{totals['T'][0]:.0f}/{totals['T'][1]:.0f}/{totals['T'][2]:+.2f}%",
                    f"{totals['CNOT'][0]:.0f}/{totals['CNOT'][1]:.0f}/{totals['CNOT'][2]:+.2f}%",
                    f"{totals['peak_ancilla'][0]:.0f}/{totals['peak_ancilla'][1]:.0f}/{totals['peak_ancilla'][2]:+.2f}%",
                    f"{totals['score'][0]:.2f}/{totals['score'][1]:.2f}/{totals['score'][2]:+.2f}%",
                    f"{score_wlt[0]}/{score_wlt[1]}/{score_wlt[2]}",
                ]
            )
            + " |"
        )

    markdown.extend(
        [
            "",
            "## Aggregate by n",
            "",
            "| n | baseline | functions | ESOP T/CNOT/ancilla | ours T/CNOT/ancilla | T change | CNOT change | ancilla change | score W/L/T |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for spec in BASELINES:
        pairs = joined_rows(internal, external, spec)
        by_n: dict[int, list[tuple[dict[str, str], dict[str, str]]]] = {}
        for target, baseline in pairs:
            by_n.setdefault(int(target["n"]), []).append((target, baseline))
        for n, items in sorted(by_n.items()):
            totals = aggregate(items)
            score_wlt = win_loss_tie(items, "score")
            baseline_tca = (
                f"{fmt_int(totals['T'][1])}/"
                f"{fmt_int(totals['CNOT'][1])}/"
                f"{fmt_int(totals['peak_ancilla'][1])}"
            )
            target_tca = (
                f"{fmt_int(totals['T'][0])}/"
                f"{fmt_int(totals['CNOT'][0])}/"
                f"{fmt_int(totals['peak_ancilla'][0])}"
            )
            summary_row = {
                "n": str(n),
                "baseline": spec.label,
                "functions": str(len(items)),
                "baseline_T": f"{totals['T'][1]:.0f}",
                "target_T": f"{totals['T'][0]:.0f}",
                "delta_T_pct": f"{totals['T'][2]:+.2f}",
                "baseline_CNOT": f"{totals['CNOT'][1]:.0f}",
                "target_CNOT": f"{totals['CNOT'][0]:.0f}",
                "delta_CNOT_pct": f"{totals['CNOT'][2]:+.2f}",
                "baseline_peak_ancilla": f"{totals['peak_ancilla'][1]:.0f}",
                "target_peak_ancilla": f"{totals['peak_ancilla'][0]:.0f}",
                "delta_peak_ancilla_pct": f"{totals['peak_ancilla'][2]:+.2f}",
                "baseline_score": f"{totals['score'][1]:.4f}",
                "target_score": f"{totals['score'][0]:.4f}",
                "delta_score_pct": f"{totals['score'][2]:+.2f}",
                "score_wins": str(score_wlt[0]),
                "score_losses": str(score_wlt[1]),
                "score_ties": str(score_wlt[2]),
            }
            summary_rows.append(summary_row)
            latex_rows.append(
                {
                    "n": str(n),
                    "baseline": spec.label.replace("-", r"\mbox{-}"),
                    "functions": str(len(items)),
                    "baseline_tca": baseline_tca,
                    "target_tca": target_tca,
                    "delta_t": latex_pct(totals["T"][2]),
                    "delta_cnot": latex_pct(totals["CNOT"][2]),
                    "delta_ancilla": latex_pct(totals["peak_ancilla"][2]),
                    "score_wlt": f"{score_wlt[0]}/{score_wlt[1]}/{score_wlt[2]}",
                }
            )
            markdown.append(
                "| "
                + " | ".join(
                    [
                        str(n),
                        spec.label,
                        str(len(items)),
                        baseline_tca,
                        target_tca,
                        f"{totals['T'][2]:+.2f}%",
                        f"{totals['CNOT'][2]:+.2f}%",
                        f"{totals['peak_ancilla'][2]:+.2f}%",
                        f"{score_wlt[0]}/{score_wlt[1]}/{score_wlt[2]}",
                    ]
                )
                + " |"
            )

    markdown.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Against the internal ESOP-MILP baseline, Pareto-Resource-NMCTS "
                "has lower aggregate T-count and CNOT count for every n=3..6 group; "
                "aggregate peak ancilla is tied at n=3 and lower for n=4..6."
            ),
            (
                "Against external ABC-ESOP, Pareto-Resource-NMCTS has lower "
                "aggregate T-count and peak ancilla for every n=3..6 group.  "
                "Aggregate CNOT is lower for n=3..5 and is 0.41% higher at n=6, "
                "so the correct claim is weighted-resource/low-T superiority, "
                "not strict CNOT dominance over every ESOP export group."
            ),
        ]
    )

    write_csv(summary_rows, RESULTS / "summary_esop_baseline.csv")
    write_latex_table(latex_rows, PAPER_TABLES / "esop_baseline_by_n.tex")
    (RESULTS / "analysis_esop_baseline.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS / 'analysis_esop_baseline.md'}")
    print(f"wrote {RESULTS / 'summary_esop_baseline.csv'}")
    print(f"wrote {PAPER_TABLES / 'esop_baseline_by_n.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
