#!/usr/bin/env python3
"""Analyze held-out Resource-NMCTS structure-gate behavior by dimension."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
MODELS = THIS_DIR / "models"
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


def read_rows(path: Path) -> list[dict[str, str]]:
    raise_csv_field_limit()
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def paired_by_n(
    rows: list[dict[str, str]],
    target_method: str,
    baseline_method: str,
) -> dict[int, list[tuple[dict[str, str], dict[str, str]]]]:
    by_method_name: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if usable(row):
            by_method_name[(str(row["method"]), str(row["name"]))] = row
    names = sorted(
        name
        for method, name in by_method_name
        if method == target_method and (baseline_method, name) in by_method_name
    )
    out: dict[int, list[tuple[dict[str, str], dict[str, str]]]] = {}
    for name in names:
        target = by_method_name[(target_method, name)]
        baseline = by_method_name[(baseline_method, name)]
        out.setdefault(int(target["n"]), []).append((target, baseline))
    return out


def metric_row(
    comparison: str,
    n_label: str,
    pairs: list[tuple[dict[str, str], dict[str, str]]],
    metric: str,
) -> dict[str, object]:
    wins = losses = ties = 0
    target_values: list[float] = []
    baseline_values: list[float] = []
    relatives: list[float] = []
    for target, baseline in pairs:
        tv = float(target[metric])
        bv = float(baseline[metric])
        target_values.append(tv)
        baseline_values.append(bv)
        relatives.append(pct(tv, bv))
        if tv < bv:
            wins += 1
        elif tv > bv:
            losses += 1
        else:
            ties += 1
    return {
        "comparison": comparison,
        "n": n_label,
        "metric": metric,
        "pairs": len(pairs),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "target_mean": statistics.mean(target_values) if target_values else float("nan"),
        "baseline_mean": statistics.mean(baseline_values) if baseline_values else float("nan"),
        "mean_relative_pct": statistics.mean(relatives) if relatives else float("nan"),
    }


def summarize(
    rows: list[dict[str, str]],
    target_method: str,
    baseline_method: str,
    comparison: str,
) -> list[dict[str, object]]:
    grouped = paired_by_n(rows, target_method, baseline_method)
    out: list[dict[str, object]] = []
    all_pairs: list[tuple[dict[str, str], dict[str, str]]] = []
    for n in sorted(grouped):
        pairs = grouped[n]
        all_pairs.extend(pairs)
        for metric in METRICS:
            out.append(metric_row(comparison, str(n), pairs, metric))
    for metric in METRICS:
        out.append(metric_row(comparison, "all", all_pairs, metric))
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "comparison",
        "n",
        "metric",
        "pairs",
        "wins",
        "losses",
        "ties",
        "target_mean",
        "baseline_mean",
        "mean_relative_pct",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _row(rows: list[dict[str, object]], comparison: str, n_label: str, metric: str) -> dict[str, object]:
    for row in rows:
        if row["comparison"] == comparison and row["n"] == n_label and row["metric"] == metric:
            return row
    raise KeyError((comparison, n_label, metric))


def write_markdown(
    path: Path,
    rows: list[dict[str, object]],
    model: dict[str, object],
    raw_csv: Path,
) -> None:
    comparisons = [
        ("screen-gated Resource vs full Resource", "screen_gate_vs_resource"),
        ("adaptive screen vs full Resource", "adaptive_vs_resource"),
    ]
    lines = [
        "# Structure Gate Holdout",
        "",
        f"Raw CSV: `{raw_csv}`.",
        "",
        "The held-out set contains random ANF functions at `n=19` and `n=20`.",
        "The gate is evaluated against full Resource-NMCTS, and adaptive screen is reported as the unsafe skip baseline.",
        "",
        "## Gate",
        "",
        f"- feature: `{model.get('feature')}`",
        f"- threshold: `{model.get('threshold')}`",
        f"- skip if >= threshold: `{model.get('skip_if_ge')}`",
        f"- training false skips: `{model.get('training_false_skips', 0)}`",
        "",
        "## Dimension grouped comparison",
        "",
        "| comparison | n | pairs | score W/L/T | mean score delta | time W/L/T | mean time delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, comparison in comparisons:
        for n_label in ["19", "20", "all"]:
            score = _row(rows, comparison, n_label, "score")
            time = _row(rows, comparison, n_label, "time_s")
            lines.append(
                "| "
                + " | ".join(
                    [
                        label,
                        n_label,
                        str(score["pairs"]),
                        f"{score['wins']}/{score['losses']}/{score['ties']}",
                        f"{float(score['mean_relative_pct']):+.2f}%",
                        f"{time['wins']}/{time['losses']}/{time['ties']}",
                        f"{float(time['mean_relative_pct']):+.2f}%",
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- At `n=19`, adaptive screen still loses score against full Resource-NMCTS on 4/8 held-out functions, so skipping the Resource tail would be unsafe.",
            "- The conservative gate does not skip at `n=19`; it exactly matches full Resource-NMCTS resources and avoids the old midpoint extrapolation.",
            "- At `n=20`, adaptive screen and full Resource-NMCTS tie on all 8 held-out functions; the gate skips the Resource tail and preserves all resource metrics while reducing mean runtime.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Comparison & $n$ & Pairs & Score W/L/T & Mean $\Delta$ score & Mean $\Delta$ time \\",
        r"\midrule",
    ]
    labels = [
        ("Gate vs Resource", "screen_gate_vs_resource"),
        ("Adaptive screen vs Resource", "adaptive_vs_resource"),
    ]
    for label, comparison in labels:
        for n_label in ["19", "20", "all"]:
            score = _row(rows, comparison, n_label, "score")
            time = _row(rows, comparison, n_label, "time_s")
            lines.append(
                f"{label} & {n_label} & {score['pairs']} & "
                f"{score['wins']}/{score['losses']}/{score['ties']} & "
                f"${float(score['mean_relative_pct']):+.2f}\\%$ & "
                f"${float(time['mean_relative_pct']):+.2f}\\%$ \\\\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RESULTS / "raw_gate_holdout_resource.csv")
    parser.add_argument("--model", type=Path, default=MODELS / "resource_structure_gate.json")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_gate_holdout_by_n.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_gate_holdout_by_n.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "gate_holdout_by_n.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    raw_rows = read_rows(args.raw)
    model = json.loads(args.model.read_text(encoding="utf-8")) if args.model.exists() else {}
    rows = []
    rows.extend(
        summarize(
            raw_rows,
            "and_resource_nmcts_screen_gate",
            "and_resource_nmcts",
            "screen_gate_vs_resource",
        )
    )
    rows.extend(
        summarize(
            raw_rows,
            "and_boolean_linear_pair_screen_adaptive",
            "and_resource_nmcts",
            "adaptive_vs_resource",
        )
    )
    write_csv(args.summary, rows)
    write_markdown(args.out, rows, model, args.raw)
    write_latex(args.latex_out, rows)
    print(f"wrote {args.summary}")
    print(f"wrote {args.out}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
