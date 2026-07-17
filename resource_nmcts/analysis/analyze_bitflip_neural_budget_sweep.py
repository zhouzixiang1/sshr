#!/usr/bin/env python3
"""Analyze low-budget learned-prior sweeps for bit-flip Resource-NMCTS."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

RAW = RESULTS / "raw_bitflip_neural_budget_sweep.csv"
LEARNED_FULL = RESULTS / "raw_traditional_resource_learned_prior.csv"
NO_PRIOR_FULL = RESULTS / "raw_traditional_resource_no_prior.csv"
SUMMARY = RESULTS / "summary_bitflip_neural_budget_sweep.csv"
ANALYSIS = RESULTS / "analysis_bitflip_neural_budget_sweep.md"
MANIFEST = RESULTS / "manifest_bitflip_neural_budget_sweep.json"
TABLE = TABLES / "bitflip_neural_budget_sweep.tex"

DEFAULT_METHODS = [
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
]
METRICS = ["score", "T", "CNOT", "depth", "peak_ancilla", "time_s"]
BUDGET_ORDER = ["top8_s8_n12", "top12_s12_n16", "top24_s24_n32"]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "budget",
        "method",
        "metric",
        "pairs",
        "learned_wins",
        "learned_losses",
        "ties",
        "mean_learned",
        "mean_no_prior",
        "mean_relative",
        "status",
    ]
    ordered = [field for field in preferred if field in fields]
    ordered.extend(field for field in fields if field not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def add_full_budget(rows: list[dict[str, str]], variant: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        row = dict(row)
        row["budget"] = "top24_s24_n32"
        row["variant"] = variant
        row.setdefault("candidate_top_k", "24")
        row.setdefault("mcts_simulations", "24")
        row.setdefault("neural_mcts_simulations", "32")
        out.append(row)
    return out


def method_label(method: str) -> str:
    return {
        "and_affine_nmcts": "Affine-Resource-NMCTS",
        "and_resource_nmcts": "Resource-NMCTS",
        "and_pareto_resource_nmcts": "Pareto-Resource-NMCTS",
    }.get(method, method)


def latex_method_label(method: str) -> str:
    return {
        "and_affine_nmcts": r"Affine-\method{}",
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"Pareto-\method{}",
    }.get(method, method.replace("_", r"\_"))


def budget_label(budget: str) -> str:
    return {
        "top8_s8_n12": "top-8, 8/12 sim.",
        "top12_s12_n16": "top-12, 12/16 sim.",
        "top24_s24_n32": "top-24, 24/32 sim.",
    }.get(budget, budget)


def compare(target: float, baseline: float) -> tuple[int, int, int]:
    if target < baseline:
        return (1, 0, 0)
    if target > baseline:
        return (0, 1, 0)
    return (0, 0, 1)


def paired_rows(rows: list[dict[str, str]], methods: list[str]) -> list[dict[str, object]]:
    by_key = {
        (row["budget"], row["variant"], row["method"], row["name"]): row
        for row in rows
        if usable(row) and row.get("method") in methods
    }
    out: list[dict[str, object]] = []
    budgets = [budget for budget in BUDGET_ORDER if any(key[0] == budget for key in by_key)]
    for budget in budgets:
        for method in methods:
            names = sorted(
                {
                    name
                    for b, _variant, m, name in by_key
                    if b == budget
                    and m == method
                    and (budget, "learned_prior", method, name) in by_key
                    and (budget, "no_prior", method, name) in by_key
                }
            )
            for metric in METRICS:
                wins = losses = ties = 0
                learned_values: list[float] = []
                no_prior_values: list[float] = []
                relatives: list[float] = []
                for name in names:
                    learned = float(by_key[(budget, "learned_prior", method, name)][metric])
                    no_prior = float(by_key[(budget, "no_prior", method, name)][metric])
                    w, l, t = compare(learned, no_prior)
                    wins += w
                    losses += l
                    ties += t
                    learned_values.append(learned)
                    no_prior_values.append(no_prior)
                    relatives.append((learned - no_prior) / no_prior if no_prior else 0.0)
                if not names:
                    continue
                out.append(
                    {
                        "budget": budget,
                        "method": method,
                        "metric": metric,
                        "pairs": len(names),
                        "learned_wins": wins,
                        "learned_losses": losses,
                        "ties": ties,
                        "mean_learned": statistics.mean(learned_values),
                        "mean_no_prior": statistics.mean(no_prior_values),
                        "mean_relative": statistics.mean(relatives),
                        "status": "pass",
                    }
                )
    return out


def row_for(rows: list[dict[str, object]], budget: str, method: str, metric: str) -> dict[str, object]:
    for row in rows:
        if row["budget"] == budget and row["method"] == method and row["metric"] == metric:
            return row
    raise KeyError((budget, method, metric))


def fmt_pct(value: object) -> str:
    return f"{100.0 * float(value):+.2f}%"


def fmt_latex_pct(value: object) -> str:
    return fmt_pct(value).replace("%", r"\%")


def write_markdown(path: Path, rows: list[dict[str, object]], raw_counts: Counter[str]) -> None:
    status_counts = Counter(str(row["status"]) for row in rows)
    lines = [
        "# Bit-Flip Neural Budget Sweep",
        "",
        "This analysis compares the learned bit-flip action prior with a matched no-prior search under tighter MCTS/candidate budgets.",
        "It asks whether the neural scorer is more useful when the search budget is explicitly constrained; correctness still comes from the same symbolic and truth-table checks.",
        "",
        "## Raw status counts",
        "",
    ]
    for status in sorted(raw_counts):
        lines.append(f"- {status}: {raw_counts[status]}")
    lines.extend(["", "## Paired score summary", "", "| budget | method | pairs | score W/L/T | mean score change | T W/L/T | runtime change |", "|---|---|---:|---:|---:|---:|---:|"])
    for budget in BUDGET_ORDER:
        methods = [method for method in DEFAULT_METHODS if any(row["budget"] == budget and row["method"] == method for row in rows)]
        for method in methods:
            score = row_for(rows, budget, method, "score")
            t_row = row_for(rows, budget, method, "T")
            time_row = row_for(rows, budget, method, "time_s")
            lines.append(
                f"| {budget_label(budget)} | {method_label(method)} | {score['pairs']} | "
                f"{score['learned_wins']}/{score['learned_losses']}/{score['ties']} | {fmt_pct(score['mean_relative'])} | "
                f"{t_row['learned_wins']}/{t_row['learned_losses']}/{t_row['ties']} | {fmt_pct(time_row['mean_relative'])} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The rows keep function set, method, legality checks, and verification route fixed while changing only the learned-prior availability and search budget.",
            "- This is a resource-constrained search-control test; it does not turn the learned prior into the main source of the paper's resource reduction.",
            "- Runtime changes include Python model-evaluation overhead on this workstation and are therefore reported separately from resource quality.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Budget & Method & Pairs & Score W/L/T & $\Delta$ score & $\Delta$ time \\",
        r"\midrule",
    ]
    for budget in BUDGET_ORDER:
        for method in DEFAULT_METHODS:
            if not any(row["budget"] == budget and row["method"] == method for row in rows):
                continue
            score = row_for(rows, budget, method, "score")
            time_row = row_for(rows, budget, method, "time_s")
            lines.append(
                f"{budget_label(budget)} & {latex_method_label(method)} & {int(score['pairs'])} & "
                f"{score['learned_wins']}/{score['learned_losses']}/{score['ties']} & "
                f"{fmt_latex_pct(score['mean_relative'])} & "
                f"{fmt_latex_pct(time_row['mean_relative'])} \\\\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, object]], raw_rows: list[dict[str, str]], full_rows: list[dict[str, str]]) -> None:
    raw_counts = Counter("pass" if usable(row) else "needs revision" for row in raw_rows)
    low_budget_score_rows = [
        row
        for row in rows
        if row["metric"] == "score" and row["budget"] in {"top8_s8_n12", "top12_s12_n16"}
    ]
    positive_low_budget = [
        row
        for row in low_budget_score_rows
        if int(row["learned_wins"]) > int(row["learned_losses"]) and float(row["mean_relative"]) < 0.0
    ]
    paper_text = PAPER.read_text(encoding="utf-8", errors="replace") if PAPER.exists() else ""
    data = {
        "script": Path(__file__).name,
        "raw_rows": len(raw_rows),
        "full_budget_rows_reused": len(full_rows),
        "paired_rows": len(rows),
        "low_budget_score_rows": len(low_budget_score_rows),
        "positive_low_budget_score_rows": len(positive_low_budget),
        "status_counts": dict(sorted(raw_counts.items())),
        "needs_revision_count": raw_counts.get("needs revision", 0),
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "tab:bitflip-budget-sweep" in paper_text,
        "outputs": {
            "summary": str(SUMMARY.relative_to(THIS_DIR)),
            "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
            "manifest": str(MANIFEST.relative_to(THIS_DIR)),
            "table": str(TABLE.relative_to(THIS_DIR)),
        },
        "input_raw": [
            str(RAW.relative_to(THIS_DIR)),
            str(LEARNED_FULL.relative_to(THIS_DIR)),
            str(NO_PRIOR_FULL.relative_to(THIS_DIR)),
        ],
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_methods(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()] or list(DEFAULT_METHODS)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--learned-full", type=Path, default=LEARNED_FULL)
    parser.add_argument("--no-prior-full", type=Path, default=NO_PRIOR_FULL)
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    args = parser.parse_args(list(argv) if argv is not None else None)

    methods = parse_methods(args.methods)
    raw_rows = read_csv(args.raw)
    full_rows = add_full_budget(read_csv(args.learned_full), "learned_prior") + add_full_budget(read_csv(args.no_prior_full), "no_prior")
    rows = raw_rows + full_rows
    paired = paired_rows(rows, methods)
    write_csv(SUMMARY, paired)
    raw_counts = Counter("pass" if usable(row) else "needs revision" for row in raw_rows)
    write_markdown(ANALYSIS, paired, raw_counts)
    write_latex(TABLE, paired)
    write_manifest(paired, raw_rows, full_rows)
    print(f"wrote {len(paired)} bit-flip neural budget-sweep paired rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
