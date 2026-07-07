#!/usr/bin/env python3
"""Analyze learned-prior versus no-prior resource synthesis runs."""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"
DEFAULT_METHODS = [
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
]
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score", "time_s"]


def read_rows(path: Path, variant: str, methods: set[str]) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("method") not in methods:
                continue
            row = dict(row)
            row["variant"] = variant
            rows.append(row)
    return rows


def usable(row: dict) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summary_rows(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        if usable(row):
            groups.setdefault((row["variant"], row["method"]), []).append(row)
    out = []
    for (variant, method), items in sorted(groups.items()):
        def vals(key: str) -> list[float]:
            return [float(row[key]) for row in items if row.get(key) not in {None, ""}]

        out.append(
            {
                "variant": variant,
                "method": method,
                "functions": len(items),
                "mean_T": statistics.mean(vals("T")),
                "mean_CNOT": statistics.mean(vals("CNOT")),
                "mean_depth": statistics.mean(vals("depth")),
                "mean_peak_ancilla": statistics.mean(vals("peak_ancilla")),
                "mean_score": statistics.mean(vals("score")),
                "mean_time_s": statistics.mean(vals("time_s")),
            }
        )
    return out


def paired_rows(rows: list[dict], methods: list[str]) -> list[dict]:
    by_key = {
        (row["variant"], row["method"], row["name"]): row
        for row in rows
        if usable(row)
    }
    out = []
    for method in methods:
        names = sorted(
            {
                name
                for variant, m, name in by_key
                if m == method and ("learned_prior", method, name) in by_key and ("no_prior", method, name) in by_key
            }
        )
        for metric in METRICS:
            learned_values = []
            no_prior_values = []
            rel = []
            wins = losses = ties = 0
            for name in names:
                learned = float(by_key[("learned_prior", method, name)][metric])
                no_prior = float(by_key[("no_prior", method, name)][metric])
                learned_values.append(learned)
                no_prior_values.append(no_prior)
                if learned < no_prior:
                    wins += 1
                elif learned > no_prior:
                    losses += 1
                else:
                    ties += 1
                if no_prior:
                    rel.append((learned - no_prior) / no_prior * 100.0)
            if not names:
                continue
            out.append(
                {
                    "method": method,
                    "metric": metric,
                    "pairs": len(names),
                    "learned_wins": wins,
                    "learned_losses": losses,
                    "ties": ties,
                    "mean_learned": statistics.mean(learned_values),
                    "mean_no_prior": statistics.mean(no_prior_values),
                    "mean_relative": statistics.mean(rel) if rel else 0.0,
                }
            )
    return out


def format_num(value: float, metric: str) -> str:
    if metric == "time_s":
        return f"{value:.3f}"
    return f"{value:.2f}"


def write_markdown(path: Path, rows: list[dict], summary: list[dict], paired: list[dict]) -> None:
    errors = [row for row in rows if row.get("error")]
    skipped = [row for row in rows if row.get("skipped")]
    lines = [
        "# Neural Prior Ablation",
        "",
        f"Rows: {len(rows)}; usable: {sum(1 for row in rows if usable(row))}; errors: {len(errors)}; skipped: {len(skipped)}.",
        "",
        "The learned-prior rows come from a matched `traditional_resource` rerun",
        "with `models/action_scorer_rollout_logical_and.pt`.  The no-prior rows",
        "rerun the same functions and methods with an absent model path, so the",
        "search keeps the heuristic PUCT/action prior but removes the learned",
        "action scorer.",
        "",
        "## Mean Resources",
        "",
        "| variant | method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            "| {variant} | {method} | {functions} | {mean_T:.2f} | {mean_CNOT:.2f} | {mean_depth:.2f} | {mean_peak_ancilla:.2f} | {mean_score:.2f} | {mean_time_s:.3f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Paired Learned-Prior Comparison",
            "",
            "| method | metric | pairs | learned wins | learned losses | ties | mean learned | mean no prior | mean relative |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in paired:
        metric = row["metric"]
        lines.append(
            f"| {row['method']} | {metric} | {row['pairs']} | {row['learned_wins']} | "
            f"{row['learned_losses']} | {row['ties']} | {format_num(row['mean_learned'], metric)} | "
            f"{format_num(row['mean_no_prior'], metric)} | {row['mean_relative']:+.2f}% |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, paired: list[dict]) -> None:
    labels = {
        "and_affine_nmcts": r"\affinemethod{}",
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"\paretomethod{}",
    }
    score_rows = [row for row in paired if row["metric"] == "score"]
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Method & Score wins & Score losses & Score ties & Mean score change \\",
        r"\midrule",
    ]
    for row in score_rows:
        label = labels.get(row["method"], row["method"].replace("_", r"\_"))
        lines.append(
            f"{label} & {row['learned_wins']} & {row['learned_losses']} & "
            f"{row['ties']} & ${row['mean_relative']:+.2f}\\%$ \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_methods(raw: str) -> list[str]:
    if not raw:
        return list(DEFAULT_METHODS)
    return [item.strip() for item in raw.split(",") if item.strip()]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learned-csv", type=Path, default=RESULTS / "raw_traditional_resource_learned_prior.csv")
    parser.add_argument("--no-prior-csv", type=Path, default=RESULTS / "raw_traditional_resource_no_prior.csv")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--out-raw", type=Path, default=RESULTS / "raw_neural_prior_ablation.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_neural_prior_ablation.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_neural_prior_ablation.md")
    parser.add_argument("--latex-out", type=Path, default=PAPER_TABLES / "neural_prior_ablation.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    methods = parse_methods(args.methods)
    method_set = set(methods)
    rows = read_rows(args.learned_csv, "learned_prior", method_set)
    rows.extend(read_rows(args.no_prior_csv, "no_prior", method_set))
    summary = summary_rows(rows)
    paired = paired_rows(rows, methods)
    write_csv(args.out_raw, rows)
    write_csv(args.summary, summary)
    write_markdown(args.out, rows, summary, paired)
    write_latex(args.latex_out, paired)
    print(f"wrote {args.out_raw}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.out}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
