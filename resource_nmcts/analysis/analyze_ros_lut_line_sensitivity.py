#!/usr/bin/env python3
"""Line-aware post-analysis for the ROS-style LUT proxy sweep.

The existing ROS-style proxy chooses the best ABC LUT mapping under the paper's
default score.  This script reuses the already verified sweep rows and asks how
the comparison changes when the LUT baseline is selected with stricter line
pressure: higher ancilla weights, minimum peak ancilla, or a per-function line
cap no worse than the fixed K=4 mapping.

This remains a proxy.  It does not implement ROS SAT garbage management.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Iterable

THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "name",
        "n",
        "method",
        "selection_objective",
        "selected_k",
        "T",
        "CNOT",
        "depth",
        "gates",
        "peak_ancilla",
        "score",
        "line_score",
        "correct",
        "candidate_ks",
    ]
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def group_sweep(rows: Iterable[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        if usable(row):
            grouped.setdefault((row["dataset"], row["name"]), []).append(row)
    return grouped


def line_score(row: dict[str, str], ancilla_weight: float) -> float:
    # Existing score already includes ancilla weight 2.0.
    return float(row["score"]) + (ancilla_weight - 2.0) * float(row["peak_ancilla"])


def select_rows(
    sweep_rows: list[dict[str, str]],
    ancilla_weights: list[float],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for (_dataset, _name), rows in sorted(group_sweep(sweep_rows).items()):
        rows = sorted(rows, key=lambda row: int(row["selected_k"]))
        k4_rows = [row for row in rows if int(row["selected_k"]) == 4]
        k4_cap = float(k4_rows[0]["peak_ancilla"]) if k4_rows else float("inf")
        selectors: list[tuple[str, str, callable]] = [
            ("external_ros_lut_min_ancilla", "min_peak_ancilla_then_score", lambda row: (float(row["peak_ancilla"]), float(row["score"]), int(row["selected_k"]))),
            ("external_ros_lut_k4_line_cap", "best_score_with_peak_ancilla_le_k4", lambda row: (float(row["score"]), float(row["peak_ancilla"]), int(row["selected_k"]))),
        ]
        for method, objective, key_fn in selectors:
            pool = rows
            if method == "external_ros_lut_k4_line_cap":
                capped = [row for row in rows if float(row["peak_ancilla"]) <= k4_cap]
                pool = capped or rows
            best = min(pool, key=key_fn)
            out = dict(best)
            out["method"] = method
            out["selection_objective"] = objective
            out["candidate_ks"] = ",".join(str(row["selected_k"]) for row in rows)
            out["line_score"] = line_score(best, 2.0)
            selected.append(out)
        for weight in ancilla_weights:
            best = min(rows, key=lambda row, w=weight: (line_score(row, w), float(row["score"]), int(row["selected_k"])))
            out = dict(best)
            out["method"] = f"external_ros_lut_line_w{weight:g}".replace(".", "p")
            out["selection_objective"] = f"score_with_ancilla_weight_{weight:g}"
            out["candidate_ks"] = ",".join(str(row["selected_k"]) for row in rows)
            out["line_score"] = line_score(best, weight)
            selected.append(out)
    return selected


def load_internal(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.extend(row for row in load_csv(path) if not row.get("error") and not row.get("skipped"))
    return rows


def by_name_method(rows: Iterable[dict[str, object] | dict[str, str]]) -> dict[str, dict[str, dict[str, object] | dict[str, str]]]:
    out: dict[str, dict[str, dict[str, object] | dict[str, str]]] = {}
    for row in rows:
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def rel(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare(
    joined: dict[str, dict[str, dict[str, object] | dict[str, str]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    wins = losses = ties = 0
    relatives: list[float] = []
    for methods in joined.values():
        if target not in methods or baseline not in methods:
            continue
        try:
            target_value = float(methods[target][metric])
            baseline_value = float(methods[baseline][metric])
        except (KeyError, TypeError, ValueError):
            continue
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
    }


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["target", "baseline", "metric", "items", "wins", "losses", "ties", "mean_relative"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{value:+.2%}"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def mean_metric(rows: list[dict[str, object]], method: str, metric: str) -> float:
    values = [float(row[metric]) for row in rows if row["method"] == method]
    return statistics.mean(values) if values else float("nan")


def write_analysis(
    analysis_path: Path,
    latex_path: Path,
    selected_rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
) -> None:
    methods = sorted({str(row["method"]) for row in selected_rows})
    lines = [
        "# ROS-Style LUT Line Sensitivity",
        "",
        "This analysis reuses the verified ABC LUT sweep and reselects the best K",
        "under stricter line pressure. It is a garbage/ancilla sensitivity proxy,",
        "not the official ROS SAT garbage-management algorithm.",
        "",
        f"Selected rows: {len(selected_rows)}.",
        "",
        "## LUT selector means",
        "",
        "| method | mean K | mean peak ancilla | mean score |",
        "|---|---:|---:|---:|",
    ]
    for method in methods:
        method_rows = [row for row in selected_rows if row["method"] == method]
        lines.append(
            f"| {method} | {statistics.mean(float(row['selected_k']) for row in method_rows):.2f} | "
            f"{statistics.mean(float(row['peak_ancilla']) for row in method_rows):.2f} | "
            f"{statistics.mean(float(row['score']) for row in method_rows):.2f} |"
        )
    lines.extend(
        [
            "",
            "## Pairwise comparisons",
            "",
            "| target | baseline | metric | items | W/L/T | mean relative |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['target']} | {row['baseline']} | {row['metric']} | {row['items']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | {pct(float(row['mean_relative']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The line-aware selectors usually move toward larger K because larger LUTs reduce the number of intermediate nodes.",
            "- The min-ancilla selector explicitly reselects each LUT sweep group by peak ancilla before score.",
            "- These selectors make the LUT proxy more ancilla-sensitive, but they still do not implement ROS SAT garbage management.",
            "- Resource-NMCTS comparisons should therefore be framed as robustness to line-aware LUT proxy choices, not as a full official ROS reproduction.",
        ]
    )
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    focus = [
        ("and_pareto_resource_nmcts", "external_ros_lut_min_ancilla", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_min_ancilla", "peak_ancilla"),
        ("and_pareto_resource_nmcts", "external_ros_lut_line_w10", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_k4_line_cap", "score"),
        ("external_ros_lut_min_ancilla", "external_ros_lut_proxy", "peak_ancilla"),
        ("external_ros_lut_min_ancilla", "external_ros_lut_proxy", "score"),
    ]
    lookup = {(row["target"], row["baseline"], row["metric"]): row for row in summary_rows}
    latex_path.parent.mkdir(parents=True, exist_ok=True)
    with latex_path.open("w", encoding="utf-8") as f:
        f.write("\\resizebox{\\linewidth}{!}{%\n")
        f.write("\\begin{tabular}{llrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Metric & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for target, baseline, metric in focus:
            row = lookup.get((target, baseline, metric))
            if row is None:
                continue
            comparison = f"{target} vs {baseline}".replace("_", r"\_")
            metric_label = metric.replace("_", r"\_")
            f.write(
                f"{comparison} & {metric_label} & {row['items']} & "
                f"{row['wins']}/{row['losses']}/{row['ties']} & {latex_pct(float(row['mean_relative']))} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}%\n")
        f.write("}\n")


def parse_weights(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=Path, default=RESULTS / "raw_ros_lut_proxy_sweep.csv")
    parser.add_argument("--internal", type=Path, action="append", required=True)
    parser.add_argument("--ancilla-weights", default="10,25")
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_ros_lut_line_sensitivity.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_ros_lut_line_sensitivity.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_ros_lut_line_sensitivity.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "ros_lut_line_sensitivity.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_ros_lut_line_sensitivity.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    sweep_rows = load_csv(args.sweep)
    selected_rows = select_rows(sweep_rows, parse_weights(args.ancilla_weights))
    internal_rows = load_internal(args.internal)
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(selected_rows).items():
        joined.setdefault(name, {}).update(methods)
    # Include default score-selected proxy for sensitivity comparisons.
    default_proxy = load_csv(RESULTS / "raw_ros_lut_proxy_best.csv")
    for name, methods in by_name_method(default_proxy).items():
        joined.setdefault(name, {}).update(methods)

    baselines = sorted({str(row["method"]) for row in selected_rows})
    targets = ["and_resource_nmcts", "and_pareto_resource_nmcts", "and_direct_anf", "direct_anf"]
    summary_rows: list[dict[str, object]] = []
    for target in targets:
        for baseline in baselines:
            for metric in METRICS:
                row = compare(joined, target, baseline, metric)
                if row is not None:
                    summary_rows.append(row)
    for baseline in baselines:
        for metric in METRICS:
            row = compare(joined, baseline, "external_ros_lut_proxy", metric)
            if row is not None:
                summary_rows.append(row)

    write_csv(args.raw_out, selected_rows)
    write_summary(args.summary, summary_rows)
    write_analysis(args.analysis, args.latex_out, selected_rows, summary_rows)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(
            {
                "sweep": str(args.sweep),
                "internal": [str(path) for path in args.internal],
                "ancilla_weights": parse_weights(args.ancilla_weights),
                "selected_rows": len(selected_rows),
                "summary_rows": len(summary_rows),
                "elapsed_s": 0.0,
                "elapsed_note": "not recorded in deterministic rebuilds",
                "claim_boundary": "Line-aware ABC LUT proxy sensitivity; not official ROS SAT garbage management.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
