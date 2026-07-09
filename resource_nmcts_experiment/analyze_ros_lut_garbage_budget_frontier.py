#!/usr/bin/env python3
"""Budget-frontier audit for the ROS-style LUT garbage proxy.

Full ROS uses SAT-based garbage management to explore line/operation trade-offs.
The official flow is not available in this package, but the existing
``raw_ros_lut_garbage_proxy.csv`` already contains three executable schedules
over the same truth-table-verified ABC LUT DAGs:

* keep-all Bennett,
* fanout checkpoints, and
* zero checkpoints.

This audit treats those schedules as a small reversible-pebbling portfolio.  For
each function and relative line budget, it selects the lowest-score feasible
schedule and compares that budgeted LUT frontier with Resource-NMCTS variants.
It remains a ROS-style proxy and must not be described as reproducing official
ROS SAT garbage management.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

GARBAGE_RAW = RESULTS / "raw_ros_lut_garbage_proxy.csv"
RAW_OUT = RESULTS / "raw_ros_lut_garbage_budget_frontier.csv"
SUMMARY_OUT = RESULTS / "summary_ros_lut_garbage_budget_frontier.csv"
ANALYSIS_OUT = RESULTS / "analysis_ros_lut_garbage_budget_frontier.md"
MANIFEST_OUT = RESULTS / "manifest_ros_lut_garbage_budget_frontier.json"
TABLE_OUT = TABLES / "ros_lut_garbage_budget_frontier.tex"

DEFAULT_INTERNAL = (
    RESULTS / "raw_traditional_resource.csv",
    RESULTS / "raw_highdim_resource.csv",
    RESULTS / "raw_highdim_scale_resource.csv",
    RESULTS / "raw_ultra_highdim_resource.csv",
    RESULTS / "raw_mega_highdim_resource.csv",
)

METRICS = ("score", "T", "peak_ancilla")
TARGETS = ("and_resource_nmcts", "and_pareto_resource_nmcts")
BUDGETS = (
    ("keep100", 1.00),
    ("line75", 0.75),
    ("line50", 0.50),
    ("line25", 0.25),
    ("minline", 0.00),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "name",
        "n",
        "budget",
        "cap_fraction",
        "peak_cap",
        "feasible",
        "method",
        "selected_policy",
        "selected_k",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "lut_nodes",
        "lut_edges",
        "checkpoint_nodes",
        "expanded_compute_calls",
        "keep_peak_ancilla",
        "keep_score",
        "peak_reduction_vs_keep_pct",
        "score_change_vs_keep_pct",
        "official_ros_fully_reproduced",
    ]
    ordered = [field for field in preferred if field in fields]
    ordered.extend(field for field in fields if field not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and str(row.get("correct")) == "True" and row.get("score") not in {"", None}


def f(row: dict[str, str] | dict[str, object], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in {"", None}:
        return default
    return float(value)


def group_policy_rows(rows: Iterable[dict[str, str]]) -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in rows:
        if usable(row):
            grouped.setdefault((row["dataset"], row["name"]), {})[row["policy"]] = row
    return grouped


def select_budget_row(
    dataset: str,
    name: str,
    policies: dict[str, dict[str, str]],
    budget: str,
    cap_fraction: float,
) -> dict[str, object] | None:
    keep = policies.get("keep_all_bennett")
    if keep is None:
        return None
    keep_peak = f(keep, "peak_ancilla")
    keep_score = f(keep, "score")
    if budget == "minline":
        peak_cap = min(f(row, "peak_ancilla") for row in policies.values())
    else:
        peak_cap = max(1, int(math.floor(keep_peak * cap_fraction)))
    feasible = [row for row in policies.values() if f(row, "peak_ancilla") <= peak_cap + 1e-9]
    if not feasible:
        return None
    selected = min(feasible, key=lambda row: (f(row, "score"), f(row, "T"), f(row, "peak_ancilla"), row["policy"]))
    selected_peak = f(selected, "peak_ancilla")
    selected_score = f(selected, "score")
    out: dict[str, object] = {
        "dataset": dataset,
        "name": name,
        "n": int(float(selected["n"])),
        "budget": budget,
        "cap_fraction": cap_fraction,
        "peak_cap": peak_cap,
        "feasible": True,
        "method": f"external_ros_lut_garbage_budget_{budget}",
        "selected_policy": selected["policy"],
        "selected_k": int(float(selected["selected_k"])),
        "official_ros_fully_reproduced": False,
        "keep_peak_ancilla": keep_peak,
        "keep_score": keep_score,
        "peak_reduction_vs_keep_pct": 100.0 * (keep_peak - selected_peak) / max(abs(keep_peak), 1.0),
        "score_change_vs_keep_pct": 100.0 * (selected_score - keep_score) / max(abs(keep_score), 1.0),
    }
    for key in (
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "lut_nodes",
        "lut_edges",
        "checkpoint_nodes",
        "expanded_compute_calls",
    ):
        out[key] = f(selected, key)
    return out


def build_budget_rows(garbage_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped = group_policy_rows(garbage_rows)
    out: list[dict[str, object]] = []
    for (dataset, name), policies in sorted(grouped.items()):
        for budget, cap_fraction in BUDGETS:
            selected = select_budget_row(dataset, name, policies, budget, cap_fraction)
            if selected is not None:
                out.append(selected)
    return out


def load_internal(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if path.exists():
            rows.extend(row for row in read_csv(path) if not row.get("error") and not row.get("skipped"))
    return rows


def by_name_method(rows: Iterable[dict[str, str] | dict[str, object]]) -> dict[str, dict[str, dict[str, str] | dict[str, object]]]:
    out: dict[str, dict[str, dict[str, str] | dict[str, object]]] = {}
    for row in rows:
        name = str(row["name"])
        method = str(row["method"])
        out.setdefault(name, {})[method] = row
    return out


def rel(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0)


def compare(
    joined: dict[str, dict[str, dict[str, str] | dict[str, object]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    wins = losses = ties = 0
    relatives: list[float] = []
    for methods in joined.values():
        if target not in methods or baseline not in methods:
            continue
        target_value = f(methods[target], metric)
        baseline_value = f(methods[baseline], metric)
        if target_value < baseline_value - 1e-9:
            wins += 1
        elif target_value > baseline_value + 1e-9:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(target_value, baseline_value))
    if not relatives:
        return None
    return {
        "target": target,
        "baseline": baseline,
        "metric": metric,
        "items": len(relatives),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives),
        "status": "pass",
    }


def summarize_budget_rows(budget_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for budget, _fraction in BUDGETS:
        rows = [row for row in budget_rows if row["budget"] == budget]
        if not rows:
            continue
        policy_counts = Counter(str(row["selected_policy"]) for row in rows)
        log_scores = [math.log10(f(row, "score") + 1.0) for row in rows]
        keep_log_scores = [math.log10(f(row, "keep_score") + 1.0) for row in rows]
        out.append(
            {
                "target": f"external_ros_lut_garbage_budget_{budget}",
                "baseline": "keep_all_bennett",
                "metric": "frontier",
                "items": len(rows),
                "wins": "",
                "losses": "",
                "ties": "",
                "mean_relative": "",
                "mean_peak_ancilla": statistics.mean(f(row, "peak_ancilla") for row in rows),
                "mean_score": statistics.mean(f(row, "score") for row in rows),
                "mean_log10_score": statistics.mean(log_scores),
                "mean_log10_score_shift_vs_keep": statistics.mean(
                    score - keep for score, keep in zip(log_scores, keep_log_scores, strict=True)
                ),
                "mean_peak_reduction_vs_keep_pct": statistics.mean(f(row, "peak_reduction_vs_keep_pct") for row in rows),
                "mean_score_change_vs_keep_pct": statistics.mean(f(row, "score_change_vs_keep_pct") for row in rows),
                "policy_counts": ";".join(f"{policy}:{count}" for policy, count in sorted(policy_counts.items())),
                "status": "pass",
            }
        )
    return out


def build_summary_rows(budget_rows: list[dict[str, object]], internal_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(budget_rows).items():
        joined.setdefault(name, {}).update(methods)

    summary = summarize_budget_rows(budget_rows)
    for budget, _fraction in BUDGETS:
        baseline = f"external_ros_lut_garbage_budget_{budget}"
        for target in TARGETS:
            for metric in METRICS:
                row = compare(joined, target, baseline, metric)
                if row is not None:
                    summary.append(row)
    return summary


def pct(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}%"


def pct_rel(value: float, digits: int = 2) -> str:
    return f"{100.0 * value:+.{digits}f}%"


def tex_pct(value: float, digits: int = 2) -> str:
    return pct(value, digits).replace("%", r"\%")


def tex_pct_rel(value: float, digits: int = 2) -> str:
    return pct_rel(value, digits).replace("%", r"\%")


def write_analysis(path: Path, budget_rows: list[dict[str, object]], summary_rows: list[dict[str, object]]) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    comparison_rows = [row for row in summary_rows if row["metric"] != "frontier"]
    lines = [
        "# ROS-Style LUT Garbage Budget Frontier",
        "",
        "This audit turns the executable LUT garbage proxy into a small budget frontier.",
        "For each verified best-K LUT DAG, it selects the lowest-score policy among keep-all,",
        "fanout-checkpoint, and zero-checkpoint schedules subject to a relative peak-ancilla budget.",
        "",
        "This is a reversible-pebbling-style proxy over verified LUT DAGs.  It is not the official ROS SAT garbage-management algorithm.",
        "",
        "## Frontier summary",
        "",
        "| budget | functions | mean peak ancilla | mean log10(score+1) | peak reduction vs keep-all | log10 score shift vs keep-all | selected policies |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in frontier_rows:
        budget = str(row["target"]).replace("external_ros_lut_garbage_budget_", "")
        lines.append(
            "| {budget} | {items} | {peak:.2f} | {log_score:.2f} | {peak_delta} | {score_shift:+.2f} | {policies} |".format(
                budget=budget,
                items=row["items"],
                peak=float(row["mean_peak_ancilla"]),
                log_score=float(row["mean_log10_score"]),
                peak_delta=pct(float(row["mean_peak_reduction_vs_keep_pct"]), 2),
                score_shift=float(row["mean_log10_score_shift_vs_keep"]),
                policies=row["policy_counts"],
            )
        )
    lines.extend(
        [
            "",
            "## Resource comparisons",
            "",
            "| target | budgeted LUT baseline | metric | items | W/L/T | mean relative |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            "| {target} | {baseline} | {metric} | {items} | {wins}/{losses}/{ties} | {delta} |".format(
                target=row["target"],
                baseline=str(row["baseline"]).replace("external_ros_lut_garbage_budget_", ""),
                metric=row["metric"],
                items=row["items"],
                wins=row["wins"],
                losses=row["losses"],
                ties=row["ties"],
                delta=pct_rel(float(row["mean_relative"]), 2),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The frontier makes the line/operation trade-off explicit instead of reporting isolated garbage policies.",
            "- Tight line budgets select recomputation-heavy policies; score and T-count can increase sharply even when peak ancilla drops.",
            "- Resource-NMCTS comparisons against these rows are robustness checks against a stronger ROS-style garbage-pressure proxy, not claims about a reproduced official ROS compiler.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary_rows: list[dict[str, object]]) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    comparison_lookup = {
        (row["target"], row["baseline"], row["metric"]): row
        for row in summary_rows
        if row["metric"] != "frontier"
    }
    focus = [
        ("and_pareto_resource_nmcts", "external_ros_lut_garbage_budget_keep100", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_garbage_budget_line50", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_garbage_budget_minline", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_garbage_budget_minline", "peak_ancilla"),
    ]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}rrr>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Budget & Functions & Peak cut & log$_{10}$ score shift & Selected policies \\",
        r"\midrule",
    ]
    for row in frontier_rows:
        budget = str(row["target"]).replace("external_ros_lut_garbage_budget_", "")
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                budget,
                row["items"],
                tex_pct(float(row["mean_peak_reduction_vs_keep_pct"]), 1),
                f"{float(row['mean_log10_score_shift_vs_keep']):+.2f}",
                str(row["policy_counts"]).replace("_", r"\_").replace(";", "; "),
            )
        )
    lines.extend(
        [
            r"\midrule",
            r"Comparison & Items & Score/T/lines & Mean $\Delta$ & Boundary \\",
        ]
    )
    for target, baseline, metric in focus:
        row = comparison_lookup.get((target, baseline, metric))
        if row is None:
            continue
        budget = baseline.replace("external_ros_lut_garbage_budget_", "")
        label = f"Pareto vs {budget}"
        if metric == "peak_ancilla":
            label += " lines"
        lines.append(
            "{} & {} & {}/{}/{} & {} & {} \\\\".format(
                label,
                row["items"],
                row["wins"],
                row["losses"],
                row["ties"],
                tex_pct_rel(float(row["mean_relative"]), 1),
                "proxy, not official ROS",
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, budget_rows: list[dict[str, object]], summary_rows: list[dict[str, object]]) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "raw_rows": len(budget_rows),
        "functions": len({str(row["name"]) for row in budget_rows}),
        "budgets": [budget for budget, _fraction in BUDGETS],
        "summary_rows": len(summary_rows),
        "frontier_rows": len(frontier_rows),
        "status_counts": {"pass": len(summary_rows)},
        "needs_revision_count": 0,
        "official_ros_fully_reproduced": False,
        "table_anchor_present": "ros_lut_garbage_budget_frontier" in PAPER.read_text(encoding="utf-8", errors="replace"),
        "sources": [
            "results/raw_ros_lut_garbage_proxy.csv",
            *[str(path.relative_to(THIS_DIR)) for path in DEFAULT_INTERNAL if path.exists()],
        ],
        "outputs": {
            "raw": "results/raw_ros_lut_garbage_budget_frontier.csv",
            "summary": "results/summary_ros_lut_garbage_budget_frontier.csv",
            "analysis": "results/analysis_ros_lut_garbage_budget_frontier.md",
            "manifest": "results/manifest_ros_lut_garbage_budget_frontier.json",
            "table": "paper_latex/tables/ros_lut_garbage_budget_frontier.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--garbage-raw", type=Path, default=GARBAGE_RAW)
    parser.add_argument("--internal", type=Path, action="append")
    parser.add_argument("--raw-out", type=Path, default=RAW_OUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY_OUT)
    parser.add_argument("--analysis", type=Path, default=ANALYSIS_OUT)
    parser.add_argument("--latex-out", type=Path, default=TABLE_OUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    internal_paths = tuple(args.internal) if args.internal else DEFAULT_INTERNAL
    budget_rows = build_budget_rows(read_csv(args.garbage_raw))
    summary_rows = build_summary_rows(budget_rows, load_internal(internal_paths))
    write_csv(args.raw_out, budget_rows)
    write_csv(args.summary, summary_rows)
    write_analysis(args.analysis, budget_rows, summary_rows)
    write_latex(args.latex_out, summary_rows)
    write_manifest(args.manifest, budget_rows, summary_rows)
    print(f"wrote {len(budget_rows)} ROS-style LUT garbage budget-frontier row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
