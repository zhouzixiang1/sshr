#!/usr/bin/env python3
"""Generic matched function-level comparison between two synthesis CSVs."""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score", "time_s"]


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def read_method(path: Path, method: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("method") == method and usable(row):
                out[str(row["name"])] = dict(row)
    return out


def pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(baseline, 1.0) * 100.0


def metric_stats(
    target: dict[str, dict[str, str]],
    baseline: dict[str, dict[str, str]],
    names: list[str],
    metric: str,
) -> dict[str, object]:
    wins = losses = ties = 0
    target_values: list[float] = []
    baseline_values: list[float] = []
    relatives: list[float] = []
    for name in names:
        t = float(target[name][metric])
        b = float(baseline[name][metric])
        target_values.append(t)
        baseline_values.append(b)
        relatives.append(pct(t, b))
        if t < b:
            wins += 1
        elif t > b:
            losses += 1
        else:
            ties += 1
    return {
        "metric": metric,
        "pairs": len(names),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_target": statistics.mean(target_values) if target_values else float("nan"),
        "mean_baseline": statistics.mean(baseline_values) if baseline_values else float("nan"),
        "mean_relative_pct": statistics.mean(relatives) if relatives else float("nan"),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    *,
    target_label: str,
    baseline_label: str,
    target_method: str,
    baseline_method: str,
    target_csv: Path,
    baseline_csv: Path,
    summary: list[dict[str, object]],
) -> None:
    lines = [
        "# Paired Method Comparison",
        "",
        f"Target: `{target_label}` from `{target_csv}` method `{target_method}`.",
        f"Baseline: `{baseline_label}` from `{baseline_csv}` method `{baseline_method}`.",
        "",
        "Rows are matched by function name and include only correct, non-skipped, non-error results.",
        "Negative mean relative values favor the target.",
        "",
        "| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        metric = str(row["metric"])
        lines.append(
            "| "
            + " | ".join(
                [
                    metric,
                    str(row["pairs"]),
                    str(row["wins"]),
                    str(row["losses"]),
                    str(row["ties"]),
                    f"{float(row['mean_target']):.3f}",
                    f"{float(row['mean_baseline']):.3f}",
                    f"{float(row['mean_relative_pct']):+.2f}%",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary: list[dict[str, object]], target_label: str, baseline_label: str) -> None:
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Metric & Target wins & Target losses & Ties & Mean relative \\",
        r"\midrule",
    ]
    for row in summary:
        if row["metric"] not in {"T", "CNOT", "depth", "peak_ancilla", "score"}:
            continue
        lines.append(
            f"{row['metric']} & {row['wins']} & {row['losses']} & {row['ties']} & "
            f"${float(row['mean_relative_pct']):+.2f}\\%$ \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            f"% target={target_label}; baseline={baseline_label}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    raise_csv_field_limit()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-csv", type=Path, required=True)
    parser.add_argument("--target-method", required=True)
    parser.add_argument("--target-label", default="target")
    parser.add_argument("--baseline-csv", type=Path, required=True)
    parser.add_argument("--baseline-method", required=True)
    parser.add_argument("--baseline-label", default="baseline")
    parser.add_argument("--out-raw", type=Path, default=RESULTS / "raw_paired_method_comparison.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_paired_method_comparison.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_paired_method_comparison.md")
    parser.add_argument("--latex-out", type=Path, default=PAPER_TABLES / "paired_method_comparison.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    target = read_method(args.target_csv, args.target_method)
    baseline = read_method(args.baseline_csv, args.baseline_method)
    names = sorted(set(target) & set(baseline))
    if not names:
        raise SystemExit("no matched usable rows")

    raw_rows: list[dict[str, object]] = []
    for name in names:
        row: dict[str, object] = {"name": name}
        for metric in METRICS:
            t = float(target[name][metric])
            b = float(baseline[name][metric])
            row[f"target_{metric}"] = t
            row[f"baseline_{metric}"] = b
            row[f"relative_{metric}_pct"] = pct(t, b)
        raw_rows.append(row)

    summary = [
        metric_stats(target, baseline, names, metric)
        for metric in METRICS
    ]
    write_csv(args.out_raw, raw_rows)
    write_csv(args.summary, summary)
    write_markdown(
        args.out,
        target_label=args.target_label,
        baseline_label=args.baseline_label,
        target_method=args.target_method,
        baseline_method=args.baseline_method,
        target_csv=args.target_csv,
        baseline_csv=args.baseline_csv,
        summary=summary,
    )
    write_latex(args.latex_out, summary, args.target_label, args.baseline_label)
    print(f"matched functions: {len(names)}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
