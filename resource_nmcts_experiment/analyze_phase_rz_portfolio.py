#!/usr/bin/env python3
"""Analyze phase/Rz-cost sensitivity against the RevKit oracle_synth baseline.

RevKit's Python ``oracle_synth`` baseline returns Rz-phase netlists.  The raw
RevKit score is therefore a lower bound whenever non-Clifford Rz rotations are
present.  This script keeps the current internal X/CNOT/MCT emitters unchanged
and asks a narrower, reproducible question:

If each non-Clifford Rz in the RevKit netlist is charged lambda score units,
when do the Resource-NMCTS candidates or their score-reranked portfolio become
competitive?

This is not hardware mapping and not exact rotation synthesis.  It is a
logic-layer sensitivity analysis and a concrete target for a future
phase/Rz-aware emitter.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

DEFAULT_LAMBDAS = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 4, 10]
RESOURCE_METHODS = [
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_polarity_archive",
]
BASELINE_METHODS = [
    "direct_anf",
    "and_direct_anf",
    "and_cube_beam",
    "and_esop_milp",
    "sshr_h",
]


@dataclass(frozen=True)
class PortfolioSpec:
    name: str
    methods: tuple[str, ...]


PORTFOLIOS = [
    PortfolioSpec("resource_nmcts_family", tuple(RESOURCE_METHODS)),
    PortfolioSpec("traditional_baseline_family", tuple(BASELINE_METHODS)),
    PortfolioSpec("all_internal_score_portfolio", tuple(RESOURCE_METHODS + BASELINE_METHODS + ["and_mcts_factor", "and_affine_nmcts"])),
]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and row.get("score") not in {"", None}


def by_name_method(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if not usable(row):
            continue
        out.setdefault(row["name"], {})[row["method"]] = row
    return out


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in {"", None}:
        return default
    return float(value)


def rel(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def fmt_lambda(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"


def select_best(methods: dict[str, dict[str, str]], candidates: Iterable[str]) -> dict[str, str] | None:
    rows = [methods[name] for name in candidates if name in methods and usable(methods[name])]
    if not rows:
        return None
    return min(rows, key=lambda row: (f(row, "score"), f(row, "T"), f(row, "CNOT"), row["method"]))


def compare_values(values: list[tuple[float, float]]) -> dict[str, object]:
    wins = losses = ties = 0
    relatives: list[float] = []
    for target, baseline in values:
        if target < baseline - 1e-9:
            wins += 1
        elif target > baseline + 1e-9:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(target, baseline))
    return {
        "items": len(values),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives) if relatives else 0.0,
    }


def summarize_winners(rows: list[dict[str, object]], portfolio: str) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        if row["portfolio"] != portfolio:
            continue
        method = str(row["selected_method"])
        counts[method] = counts.get(method, 0) + 1
    return ";".join(f"{method}:{count}" for method, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def analyze(
    internal_rows: list[dict[str, str]],
    revkit_rows: list[dict[str, str]],
    lambdas: list[float],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    internal = by_name_method(internal_rows)
    revkit = by_name_method(revkit_rows)
    raw: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []

    for name, baselines in sorted(revkit.items()):
        rev = baselines.get("external_revkit_oracle_synth")
        if rev is None or not usable(rev):
            continue
        methods = internal.get(name, {})
        lower = f(rev, "score")
        rz = f(rev, "rz_non_clifford")
        for spec in PORTFOLIOS:
            selected = select_best(methods, spec.methods)
            if selected is None:
                continue
            selected_score = f(selected, "score")
            if selected_score <= lower:
                break_even = 0.0
                impossible = False
            elif rz > 0:
                break_even = (selected_score - lower) / rz
                impossible = False
            else:
                break_even = float("inf")
                impossible = True
            method_times = [f(methods[method], "time_s") for method in spec.methods if method in methods]
            base = {
                "name": name,
                "n": int(rev["n"]),
                "portfolio": spec.name,
                "selected_method": selected["method"],
                "selected_score": selected_score,
                "selected_T": f(selected, "T"),
                "selected_CNOT": f(selected, "CNOT"),
                "selected_depth": f(selected, "depth"),
                "selected_peak_ancilla": f(selected, "peak_ancilla"),
                "selected_time_s": f(selected, "time_s"),
                "portfolio_run_all_time_s": sum(method_times),
                "revkit_lower_score": lower,
                "revkit_non_clifford_rz": rz,
                "revkit_total_rz": f(rev, "rz_total"),
                "break_even_rz_score": break_even,
                "break_even_impossible": int(impossible),
            }
            for lam in lambdas:
                baseline = lower + lam * rz
                base[f"revkit_score_rz{fmt_lambda(lam)}"] = baseline
                base[f"relative_rz{fmt_lambda(lam)}"] = rel(selected_score, baseline)
                base[f"wins_rz{fmt_lambda(lam)}"] = int(selected_score < baseline - 1e-9)
            raw.append(base)

    for spec in PORTFOLIOS:
        rows = [row for row in raw if row["portfolio"] == spec.name]
        if not rows:
            continue
        thresholds = [float(row["break_even_rz_score"]) for row in rows if not row["break_even_impossible"]]
        for lam in lambdas:
            key = fmt_lambda(lam)
            values = [(float(row["selected_score"]), float(row[f"revkit_score_rz{key}"])) for row in rows]
            stats = compare_values(values)
            summary.append(
                {
                    "portfolio": spec.name,
                    "lambda_rz_score": key,
                    "items": stats["items"],
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "ties": stats["ties"],
                    "mean_relative": stats["mean_relative"],
                    "mean_selected_score": statistics.mean(float(row["selected_score"]) for row in rows),
                    "mean_revkit_score": statistics.mean(float(row[f"revkit_score_rz{key}"]) for row in rows),
                    "median_break_even": statistics.median(thresholds) if thresholds else float("nan"),
                    "mean_break_even": statistics.mean(thresholds) if thresholds else float("nan"),
                    "covered_by_lambda": sum(1 for value in thresholds if value <= lam),
                    "impossible_rows": sum(int(row["break_even_impossible"]) for row in rows),
                    "mean_selected_time_s": statistics.mean(float(row["selected_time_s"]) for row in rows),
                    "mean_run_all_time_s": statistics.mean(float(row["portfolio_run_all_time_s"]) for row in rows),
                    "winner_counts": summarize_winners(rows, spec.name),
                }
            )
    return raw, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{value:+.2%}"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def write_analysis(path: Path, raw: list[dict[str, object]], summary: list[dict[str, object]], lambdas: list[float]) -> None:
    lines = [
        "# Phase/Rz Cost Portfolio Sensitivity",
        "",
        "This analysis keeps the internal X/CNOT/MCT emitters unchanged and",
        "compares score-reranked internal portfolios against the RevKit",
        "`oracle_synth` Rz-phase lower-bound baseline after charging each",
        "non-Clifford Rz rotation lambda score units.",
        "",
        "It is a logic-layer sensitivity study, not exact Clifford+T rotation",
        "synthesis and not hardware mapping.",
        "",
        "## Portfolio Definitions",
        "",
    ]
    for spec in PORTFOLIOS:
        lines.append(f"- `{spec.name}`: {', '.join(spec.methods)}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| portfolio | lambda | W/L/T | mean relative | median break-even | covered | mean selected time | mean run-all time |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    focus_lambdas = {fmt_lambda(v) for v in lambdas}
    for row in summary:
        if str(row["lambda_rz_score"]) not in focus_lambdas:
            continue
        lines.append(
            f"| {row['portfolio']} | {row['lambda_rz_score']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | {pct(float(row['mean_relative']))} | "
            f"{float(row['median_break_even']):.2f} | {row['covered_by_lambda']}/{row['items']} | "
            f"{float(row['mean_selected_time_s']):.4f} | {float(row['mean_run_all_time_s']):.4f} |"
        )
    lines.extend(["", "## Winner Counts", ""])
    for spec in PORTFOLIOS:
        winners = summarize_winners(raw, spec.name)
        lines.append(f"- `{spec.name}`: {winners}")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- A lower lambda means a more favorable interpretation of RevKit's non-Clifford Rz rotations.",
            "- The selected internal circuit remains the existing verified bit-flip oracle circuit.",
            "- A future phase/Rz-aware emitter should replace this proxy by exact or approximate rotation synthesis costs.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    focus = {
        ("resource_nmcts_family", "0"),
        ("resource_nmcts_family", "1"),
        ("resource_nmcts_family", "1.5"),
        ("resource_nmcts_family", "2"),
        ("traditional_baseline_family", "1"),
        ("traditional_baseline_family", "1.5"),
        ("traditional_baseline_family", "2"),
        ("all_internal_score_portfolio", "1"),
        ("all_internal_score_portfolio", "1.5"),
        ("all_internal_score_portfolio", "2"),
    }
    labels = {
        "resource_nmcts_family": "Resource-NMCTS family",
        "traditional_baseline_family": "Traditional baseline family",
        "all_internal_score_portfolio": "All-internal score portfolio",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrrr}\n")
        f.write("\\toprule\n")
        f.write("Portfolio & $\\lambda_{R_z}$ & Items & W/L/T & Mean $\\Delta$ & Covered \\\\\n")
        f.write("\\midrule\n")
        for row in summary:
            key = (str(row["portfolio"]), str(row["lambda_rz_score"]))
            if key not in focus:
                continue
            label = labels.get(str(row["portfolio"]), str(row["portfolio"]))
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            covered = f"{row['covered_by_lambda']}/{row['items']}"
            f.write(
                f"{label} & {row['lambda_rz_score']} & {row['items']} & {wlt} & "
                f"{latex_pct(float(row['mean_relative']))} & {covered} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--revkit", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_phase_rz_portfolio.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_rz_portfolio.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_rz_portfolio.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_rz_portfolio.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_phase_rz_portfolio.json")
    parser.add_argument("--lambdas", default=",".join(fmt_lambda(v) for v in DEFAULT_LAMBDAS))
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    lambdas = [float(item.strip()) for item in args.lambdas.split(",") if item.strip()]
    raw, summary = analyze(load_csv(args.internal), load_csv(args.revkit), lambdas)
    write_csv(args.raw_out, raw)
    write_csv(args.summary, summary)
    write_analysis(args.analysis, raw, summary, lambdas)
    write_latex(args.latex_out, summary)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(
            {
                "internal": str(args.internal),
                "revkit": str(args.revkit),
                "raw_out": str(args.raw_out),
                "summary": str(args.summary),
                "analysis": str(args.analysis),
                "latex_out": str(args.latex_out),
                "lambdas": lambdas,
                "rows": len(raw),
                "summary_rows": len(summary),
                "elapsed_s": time.time() - started,
                "claim_boundary": "Logic-layer non-Clifford Rz sensitivity; not exact rotation synthesis and not hardware mapping.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"elapsed {time.time() - started:.2f}s")
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
