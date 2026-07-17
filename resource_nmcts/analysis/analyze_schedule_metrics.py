#!/usr/bin/env python3
"""Analyze logic-level schedule proxy metrics from synthesis raw CSV files."""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

METRICS = [
    "score",
    "schedule_logical_depth",
    "schedule_cnot_depth_proxy",
    "schedule_t_depth_proxy",
    "explicit_ancilla_live_peak",
    "explicit_ancilla_lifetime_area",
    "peak_ancilla",
]

DEFAULT_COMPARISONS = [
    ("depth_frontier_policy", "screen_depth2"),
    ("depth_frontier_policy", "screen_depth4"),
    ("depth_frontier_policy", "adaptive_all_depth"),
    ("screen_depth4", "screen_depth2"),
    ("screen_depth3", "screen_depth2"),
    ("adaptive_all_depth", "screen_depth2"),
    ("depth_policy", "screen_depth2"),
    ("depth2_guard_direct", "screen_depth2"),
]

METRIC_LABELS = {
    "score": "Score",
    "schedule_logical_depth": "parallel logical depth",
    "schedule_cnot_depth_proxy": "CNOT-depth proxy",
    "schedule_t_depth_proxy": "T-depth proxy",
    "explicit_ancilla_live_peak": "explicit live ancilla peak",
    "explicit_ancilla_lifetime_area": "explicit ancilla lifetime area",
    "peak_ancilla": "peak ancilla",
}


def parse_input(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem.removeprefix("raw_"), path
    label, path = value.split("=", 1)
    return label.strip(), Path(path.strip())


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_ok(row: dict[str, str]) -> bool:
    checks = ["anf_verified", "circuit_anf_verified"]
    if "truth_verified" in row:
        checks.append("truth_verified")
    return all(str(row.get(key, "False")) == "True" for key in checks)


def build_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if not row_ok(row):
            continue
        out[(row["name"], row["method"])] = row
    return out


def as_float(row: dict[str, str], metric: str) -> float | None:
    value = row.get(metric, "")
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def compare(
    rows: list[dict[str, str]],
    dataset: str,
    method: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    index = build_index(rows)
    names = sorted({name for name, row_method in index if row_method in {method, baseline}})
    wins = losses = ties = 0
    relatives: list[float] = []
    by_n: dict[str, list[float]] = {}
    for name in names:
        target = index.get((name, method))
        base = index.get((name, baseline))
        if target is None or base is None:
            continue
        target_value = as_float(target, metric)
        base_value = as_float(base, metric)
        if target_value is None or base_value is None:
            continue
        if target_value < base_value - 1e-9:
            wins += 1
        elif target_value > base_value + 1e-9:
            losses += 1
        else:
            ties += 1
        relative = (target_value - base_value) / max(abs(base_value), 1.0)
        relatives.append(relative)
        by_n.setdefault(str(target.get("n", "?")), []).append(relative)
    if not relatives:
        return None
    return {
        "dataset": dataset,
        "method": method,
        "baseline": baseline,
        "metric": metric,
        "items": len(relatives),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives),
        "by_n": by_n,
    }


def format_pct(value: float) -> str:
    return f"{value:+.2%}"


def write_outputs(summary_path: Path, analysis_path: Path, table_path: Path, rows: list[dict[str, object]]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "method",
                "baseline",
                "metric",
                "items",
                "wins",
                "losses",
                "ties",
                "mean_relative",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    lines = [
        "# Logic-Level Schedule Proxy Analysis",
        "",
        "These metrics are computed from emitted X/CNOT/MCT oracle circuits without",
        "hardware mapping. They are backend-relevant logic-level proxies: parallel",
        "logical depth, CNOT-depth proxy, T-depth proxy, explicit live-ancilla peak,",
        "and explicit ancilla lifetime area.",
        "",
        "| dataset | method | baseline | metric | items | W/L/T | mean relative |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {method} | {baseline} | {metric} | {items} | {wins}/{losses}/{ties} | {rel} |".format(
                dataset=row["dataset"],
                method=row["method"],
                baseline=row["baseline"],
                metric=METRIC_LABELS.get(str(row["metric"]), str(row["metric"])),
                items=row["items"],
                wins=row["wins"],
                losses=row["losses"],
                ties=row["ties"],
                rel=format_pct(float(row["mean_relative"])),
            )
        )
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    table_path.parent.mkdir(parents=True, exist_ok=True)
    focus_metrics = {"score", "schedule_t_depth_proxy", "explicit_ancilla_lifetime_area"}
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lllrrr}\n")
        f.write("\\toprule\n")
        f.write("Dataset & Comparison & Metric & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for row in rows:
            if row["metric"] not in focus_metrics:
                continue
            comparison = f"{row['method']} vs {row['baseline']}"
            f.write(
                f"{row['dataset']} & {comparison} & {METRIC_LABELS.get(str(row['metric']), str(row['metric']))} "
                f"& {row['items']} & {row['wins']}/{row['losses']}/{row['ties']} "
                f"& {format_pct(float(row['mean_relative']))} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="LABEL=raw.csv; can be repeated")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_schedule_metrics.md")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_schedule_metrics.csv")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "schedule_metrics.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_rows: list[dict[str, object]] = []
    for raw_input in args.input:
        label, path = parse_input(raw_input)
        if not path.is_absolute():
            path = THIS_DIR / path
        rows = read_rows(path)
        available_methods = {row.get("method", "") for row in rows}
        for method, baseline in DEFAULT_COMPARISONS:
            if method not in available_methods or baseline not in available_methods:
                continue
            for metric in METRICS:
                result = compare(rows, label, method, baseline, metric)
                if result is not None:
                    output_rows.append(result)

    output_rows.sort(
        key=lambda row: (
            str(row["dataset"]),
            str(row["method"]),
            str(row["baseline"]),
            METRICS.index(str(row["metric"])) if row["metric"] in METRICS else len(METRICS),
        )
    )
    write_outputs(args.summary, args.out, args.latex_out, output_rows)
    print(f"wrote {args.summary}")
    print(f"wrote {args.out}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
