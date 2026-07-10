#!/usr/bin/env python3
"""Analyze raw multi-resource dominance instead of weighted-score wins."""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

METRICS = ("T", "CNOT", "depth", "peak_ancilla")
TARGET = "and_pareto_resource_nmcts"


@dataclass(frozen=True)
class MethodSource:
    method: str
    label: str
    files: tuple[str, ...]


PAIRWISE_BASELINES = [
    MethodSource("direct_anf", "Direct ANF", ("raw_traditional_resource.csv",)),
    MethodSource("and_cube_beam", "ESOP beam", ("raw_traditional_resource.csv",)),
    MethodSource("and_esop_milp", "ESOP-MILP", ("raw_traditional_resource.csv",)),
    MethodSource("sshr_h", "SSHR-H", ("raw_traditional_resource.csv",)),
    MethodSource("external_sshr_i_cnot", "SSHR-I CNOT", ("raw_external_traditional_resource_n6.csv",)),
    MethodSource("external_abc_xag", "ABC-XAG", ("raw_external_traditional_resource_n6.csv",)),
    MethodSource("external_mockturtle_xag_k4", "mockturtle XAG", ("raw_mockturtle_xag_probe.csv",)),
    MethodSource("external_cirkit_aig_mc", "CirKit AIG/MC", ("raw_cirkit_aig_probe.csv",)),
    MethodSource(
        "external_revkit_cli_best_score",
        "RevKit CLI exact oracle",
        ("raw_revkit_cli_multiflow_traditional.csv",),
    ),
]

POOL_METHODS = [
    MethodSource("direct_anf", "Direct ANF", ("raw_traditional_resource.csv",)),
    MethodSource("and_direct_anf", "AND-direct ANF", ("raw_traditional_resource.csv",)),
    MethodSource("and_cube_beam", "ESOP beam", ("raw_traditional_resource.csv",)),
    MethodSource("and_esop_milp", "ESOP-MILP", ("raw_traditional_resource.csv",)),
    MethodSource("sshr_h", "SSHR-H", ("raw_traditional_resource.csv",)),
    MethodSource("and_resource_nmcts", "Resource-NMCTS", ("raw_traditional_resource.csv",)),
    MethodSource("and_pareto_resource_nmcts", "Pareto-Resource-NMCTS", ("raw_traditional_resource.csv",)),
    MethodSource("external_sshr_i_cnot", "SSHR-I CNOT", ("raw_external_traditional_resource_n6.csv",)),
    MethodSource("external_abc_xag", "ABC-XAG", ("raw_external_traditional_resource_n6.csv",)),
    MethodSource("external_mockturtle_xag_k4", "mockturtle XAG", ("raw_mockturtle_xag_probe.csv",)),
    MethodSource("external_cirkit_aig_mc", "CirKit AIG/MC", ("raw_cirkit_aig_probe.csv",)),
    MethodSource(
        "external_revkit_cli_best_score",
        "RevKit CLI exact oracle",
        ("raw_revkit_cli_multiflow_traditional.csv",),
    ),
]


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def falsey(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no"}


def usable(row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    for key in (
        "correct",
        "abc_blif_correct",
        "source_blif_correct",
        "verilog_correct",
        "anf_verified",
        "circuit_anf_verified",
        "verified_up_to_global_phase",
    ):
        if key in row and falsey(row.get(key)):
            return False
    return True


def read_method(source: MethodSource) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in source.files:
        path = RESULTS / name
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("method") == source.method and usable(row):
                    rows[row["name"]] = row
    return rows


def values(row: dict[str, str]) -> tuple[float, ...]:
    return tuple(float(row[metric]) for metric in METRICS)


def dominates(left: dict[str, str], right: dict[str, str]) -> bool:
    left_values = values(left)
    right_values = values(right)
    return all(a <= b + 1e-9 for a, b in zip(left_values, right_values)) and any(
        a < b - 1e-9 for a, b in zip(left_values, right_values)
    )


def equal_resources(left: dict[str, str], right: dict[str, str]) -> bool:
    return all(abs(float(left[metric]) - float(right[metric])) <= 1e-9 for metric in METRICS)


def pairwise_rows() -> list[dict[str, object]]:
    target_rows = read_method(MethodSource(TARGET, "Pareto-Resource-NMCTS", ("raw_traditional_resource.csv",)))
    rows: list[dict[str, object]] = []
    for baseline in PAIRWISE_BASELINES:
        baseline_rows = read_method(baseline)
        names = sorted(set(target_rows) & set(baseline_rows))
        target_dominates = baseline_dominates = equal = incomparable = 0
        target_score_wins = target_score_losses = target_score_ties = 0
        for name in names:
            target = target_rows[name]
            base = baseline_rows[name]
            if equal_resources(target, base):
                equal += 1
            elif dominates(target, base):
                target_dominates += 1
            elif dominates(base, target):
                baseline_dominates += 1
            else:
                incomparable += 1

            target_score = float(target["score"])
            baseline_score = float(base["score"])
            if target_score < baseline_score - 1e-9:
                target_score_wins += 1
            elif target_score > baseline_score + 1e-9:
                target_score_losses += 1
            else:
                target_score_ties += 1

        rows.append(
            {
                "baseline": baseline.label,
                "pairs": len(names),
                "target_dominates": target_dominates,
                "baseline_dominates": baseline_dominates,
                "incomparable": incomparable,
                "equal": equal,
                "score_wins": target_score_wins,
                "score_losses": target_score_losses,
                "score_ties": target_score_ties,
            }
        )
    return rows


def nondominated_rows() -> list[dict[str, object]]:
    by_method = {source.method: read_method(source) for source in POOL_METHODS}
    labels = {source.method: source.label for source in POOL_METHODS}
    names = sorted(set.intersection(*(set(rows) for rows in by_method.values())))
    out: list[dict[str, object]] = []
    for method, rows in by_method.items():
        nondominated = dominated = 0
        for name in names:
            row = rows[name]
            is_dominated = any(
                other_method != method and dominates(other_rows[name], row)
                for other_method, other_rows in by_method.items()
            )
            if is_dominated:
                dominated += 1
            else:
                nondominated += 1
        out.append(
            {
                "method": labels[method],
                "available": len(names),
                "nondominated": nondominated,
                "dominated": dominated,
                "nondominated_pct": 100.0 * nondominated / len(names),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    pairwise: list[dict[str, object]],
    nondominated: list[dict[str, object]],
) -> None:
    lines = [
        "# Multi-Metric Pareto Tradeoff Analysis",
        "",
        "Dominance is computed on raw logical resources: T, CNOT, depth, and peak ancilla.",
        "Weighted score is not part of the dominance predicate.",
        "",
        "## Pairwise dominance against Pareto-Resource-NMCTS",
        "",
        "| baseline | pairs | Pareto dominates | baseline dominates | incomparable | equal | score W/L/T |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in pairwise:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["baseline"]),
                    str(row["pairs"]),
                    str(row["target_dominates"]),
                    str(row["baseline_dominates"]),
                    str(row["incomparable"]),
                    str(row["equal"]),
                    f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Nondominated membership in the n<=6 method pool",
            "",
            "| method | rows | nondominated | dominated | nondominated share |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(nondominated, key=lambda item: (-int(item["nondominated"]), str(item["method"]))):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["method"]),
                    str(row["available"]),
                    str(row["nondominated"]),
                    str(row["dominated"]),
                    f"{float(row['nondominated_pct']):.1f}%",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def write_pairwise_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}Xrrrrr}",
        r"\toprule",
        r"Baseline & Pairs & Pareto dom. & Base dom. & Incomp. & Equal \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(str(row['baseline']))} & {row['pairs']} & "
            f"{row['target_dominates']} & {row['baseline_dominates']} & "
            f"{row['incomparable']} & {row['equal']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_nondominated_latex(path: Path, rows: list[dict[str, object]]) -> None:
    selected = sorted(rows, key=lambda item: (-int(item["nondominated"]), str(item["method"])))
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}Xrrr}",
        r"\toprule",
        r"Method & Rows & Non-dominated & Dominated \\",
        r"\midrule",
    ]
    for row in selected:
        lines.append(
            f"{tex_escape(str(row['method']))} & {row['available']} & "
            f"{row['nondominated']} & {row['dominated']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    raise_csv_field_limit()
    pairwise = pairwise_rows()
    nondominated = nondominated_rows()
    write_csv(RESULTS / "summary_multimetric_pairwise_dominance.csv", pairwise)
    write_csv(RESULTS / "summary_multimetric_nondominated.csv", nondominated)
    write_markdown(RESULTS / "analysis_multimetric_pareto_tradeoff.md", pairwise, nondominated)
    write_pairwise_latex(TABLES / "multimetric_pairwise_dominance.tex", pairwise)
    write_nondominated_latex(TABLES / "multimetric_nondominated.tex", nondominated)
    print(f"wrote {len(pairwise)} pairwise rows and {len(nondominated)} pool rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
