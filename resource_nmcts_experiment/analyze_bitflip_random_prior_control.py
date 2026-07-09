#!/usr/bin/env python3
"""Analyze same-budget random-prior controls for bit-flip Resource-NMCTS."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
DEFAULT_METHODS = [
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
]
METRICS = ["score", "T", "CNOT", "depth", "peak_ancilla", "time_s"]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def parse_methods(raw: str) -> list[str]:
    if not raw:
        return list(DEFAULT_METHODS)
    return [item.strip() for item in raw.split(",") if item.strip()]


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def compare_values(target: float, baseline: float) -> tuple[int, int, int]:
    if target < baseline:
        return (1, 0, 0)
    if target > baseline:
        return (0, 1, 0)
    return (0, 0, 1)


def relative(target: float, baseline: float) -> float:
    return (target - baseline) / baseline if baseline else 0.0


def metric_rows(
    learned_rows: list[dict[str, str]],
    random_rows: list[dict[str, str]],
    no_prior_rows: list[dict[str, str]],
    methods: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    learned = {
        (row["method"], row["name"]): row
        for row in learned_rows
        if usable(row) and row.get("method") in methods
    }
    no_prior = {
        (row["method"], row["name"]): row
        for row in no_prior_rows
        if usable(row) and row.get("method") in methods
    }
    random_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in random_rows:
        if usable(row) and row.get("method") in methods:
            random_by_key.setdefault((row["method"], row["name"]), []).append(row)

    metric_out: list[dict[str, str]] = []
    headline_out: list[dict[str, str]] = []
    for method in methods:
        names = sorted(
            name
            for (m, name), rows in random_by_key.items()
            if m == method and (method, name) in learned and rows
        )
        random_seeds = sorted(
            {
                row.get("random_seed", "")
                for (m, name), rows in random_by_key.items()
                if m == method and name in names
                for row in rows
            }
        )
        for metric in METRICS:
            wins = losses = ties = 0
            learned_values: list[float] = []
            random_mean_values: list[float] = []
            random_best_values: list[float] = []
            no_prior_values: list[float] = []
            rels: list[float] = []
            target_at_or_better_than_random_best = 0
            no_prior_wins = no_prior_losses = no_prior_ties = 0
            for name in names:
                target = float(learned[(method, name)][metric])
                random_values = [float(row[metric]) for row in random_by_key[(method, name)]]
                baseline = mean(random_values)
                random_best = min(random_values)
                w, l, t = compare_values(target, baseline)
                wins += w
                losses += l
                ties += t
                if target <= random_best:
                    target_at_or_better_than_random_best += 1
                learned_values.append(target)
                random_mean_values.append(baseline)
                random_best_values.append(random_best)
                rels.append(relative(target, baseline))
                if (method, name) in no_prior:
                    np_value = float(no_prior[(method, name)][metric])
                    no_prior_values.append(np_value)
                    w_np, l_np, t_np = compare_values(target, np_value)
                    no_prior_wins += w_np
                    no_prior_losses += l_np
                    no_prior_ties += t_np

            seed_means_beaten = 0
            for random_seed in random_seeds:
                seed_values = [
                    float(row[metric])
                    for name in names
                    for row in random_by_key[(method, name)]
                    if row.get("random_seed") == random_seed
                ]
                if learned_values and mean(learned_values) <= mean(seed_values):
                    seed_means_beaten += 1

            row = {
                "method": method,
                "metric": metric,
                "pairs": str(len(names)),
                "random_repeats": str(len(random_seeds)),
                "learned_wins": str(wins),
                "learned_losses": str(losses),
                "ties": str(ties),
                "mean_learned": f"{mean(learned_values):.10g}",
                "mean_random": f"{mean(random_mean_values):.10g}",
                "mean_random_best": f"{mean(random_best_values):.10g}",
                "mean_relative": f"{mean(rels):.10g}",
                "seed_means_beaten": str(seed_means_beaten),
                "target_at_or_better_than_random_best": str(target_at_or_better_than_random_best),
                "no_prior_pairs": str(len(no_prior_values)),
                "learned_vs_no_prior_wins": str(no_prior_wins),
                "learned_vs_no_prior_losses": str(no_prior_losses),
                "learned_vs_no_prior_ties": str(no_prior_ties),
                "status": "pass" if names and random_seeds else "needs revision",
            }
            metric_out.append(row)
            if metric == "score":
                headline_out.append(row)
    return metric_out, headline_out


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(raw: str) -> str:
    return f"{100.0 * float(raw):+.2f}%"


def method_label(method: str) -> str:
    labels = {
        "and_affine_nmcts": "Affine-Resource-NMCTS",
        "and_resource_nmcts": "Resource-NMCTS",
        "and_pareto_resource_nmcts": "Pareto-Resource-NMCTS",
    }
    return labels.get(method, method)


def latex_method_label(method: str) -> str:
    labels = {
        "and_affine_nmcts": r"Affine-\method{}",
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"Pareto-\method{}",
    }
    return labels.get(method, method.replace("_", r"\_"))


def write_markdown(path: Path, metric_rows: list[dict[str, str]], headline_rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    for row in metric_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    lines = [
        "# Bit-Flip Random-Prior Control",
        "",
        "This audit compares the learned bit-flip prior with same-budget deterministic random priors.",
        "The random-prior scorer has the same `score_many()` interface as the neural scorer and changes only action-prior ranking; all semantic checks and candidate legality remain unchanged.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")
    lines.extend(
        [
            "",
            "## Score headline",
            "",
            "| method | pairs | random repeats | W/L/T vs random mean | mean learned | mean random | mean relative | seed means beaten | learned <= best random | W/L/T vs no prior |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in headline_rows:
        lines.append(
            "| {method} | {pairs} | {random_repeats} | {learned_wins}/{learned_losses}/{ties} | "
            "{mean_learned} | {mean_random} | {mean_relative} | {seed_means_beaten}/{random_repeats} | "
            "{target_at_or_better_than_random_best}/{pairs} | {learned_vs_no_prior_wins}/{learned_vs_no_prior_losses}/{learned_vs_no_prior_ties} |".format(
                **{
                    **row,
                    "method": method_label(row["method"]),
                    "mean_relative": fmt_pct(row["mean_relative"]),
                }
            )
        )
    lines.extend(
        [
            "",
            "## Metric details",
            "",
            "| method | metric | W/L/T vs random mean | mean relative | W/L/T vs no prior |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in metric_rows:
        lines.append(
            "| {method} | {metric} | {learned_wins}/{learned_losses}/{ties} | {mean_relative} | "
            "{learned_vs_no_prior_wins}/{learned_vs_no_prior_losses}/{learned_vs_no_prior_ties} |".format(
                **{
                    **row,
                    "method": method_label(row["method"]),
                    "mean_relative": fmt_pct(row["mean_relative"]),
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, headline_rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth}rrrr>{\raggedleft\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Method & Pairs & Repeats & W/L/T & Best-random wins & Mean score change & Boundary \\",
        r"\midrule",
    ]
    for row in headline_rows:
        boundary = (
            "same-budget random-prior scorer; lower score favors learned prior"
            if row["status"] == "pass"
            else "missing random-prior evidence"
        )
        lines.append(
            "{} & {} & {} & {}/{}/{} & {}/{} & ${}\\%$ & {} \\\\".format(
                latex_method_label(row["method"]),
                row["pairs"],
                row["random_repeats"],
                row["learned_wins"],
                row["learned_losses"],
                row["ties"],
                row["target_at_or_better_than_random_best"],
                row["pairs"],
                f"{100.0 * float(row['mean_relative']):+.2f}",
                boundary,
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, metric_rows: list[dict[str, str]], args: argparse.Namespace) -> None:
    status_counts = {
        status: sum(1 for row in metric_rows if row["status"] == status)
        for status in sorted({row["status"] for row in metric_rows})
    }
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(metric_rows),
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "source_files": {
            "learned": str(args.learned_csv.relative_to(THIS_DIR)),
            "no_prior": str(args.no_prior_csv.relative_to(THIS_DIR)),
            "random_prior": str(args.random_csv.relative_to(THIS_DIR)),
        },
        "outputs": {
            "summary": str(args.summary.relative_to(THIS_DIR)),
            "analysis": str(args.out.relative_to(THIS_DIR)),
            "manifest": str(path.relative_to(THIS_DIR)),
            "table": str(args.latex_out.relative_to(THIS_DIR)),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learned-csv", type=Path, default=RESULTS / "raw_traditional_resource_learned_prior.csv")
    parser.add_argument("--no-prior-csv", type=Path, default=RESULTS / "raw_traditional_resource_no_prior.csv")
    parser.add_argument("--random-csv", type=Path, default=RESULTS / "raw_bitflip_random_prior_control.csv")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_bitflip_random_prior_control.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_bitflip_random_prior_control.md")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_bitflip_random_prior_control.json")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "bitflip_random_prior_control.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    methods = parse_methods(args.methods)
    metric_out, headline_out = metric_rows(
        read_csv(args.learned_csv),
        read_csv(args.random_csv),
        read_csv(args.no_prior_csv),
        methods,
    )
    write_csv(args.summary, metric_out)
    write_markdown(args.out, metric_out, headline_out)
    write_latex(args.latex_out, headline_out)
    write_manifest(args.manifest, metric_out, args)
    failures = sum(1 for row in metric_out if row["status"] != "pass")
    print(f"wrote {len(metric_out)} bit-flip random-prior metric rows")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
