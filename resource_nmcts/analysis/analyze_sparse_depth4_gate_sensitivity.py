#!/usr/bin/env python3
"""Analyze threshold sensitivity for the sparse depth-4 gate."""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rel(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def pct(value: float) -> str:
    return f"{100.0 * float(value):+.2f}%"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def threshold_grid(probs: list[float], selected_threshold: float) -> list[float]:
    values = sorted(set(probs))
    grid = {0.0, selected_threshold}
    if values:
        grid.add(values[-1] + 1e-9)
    grid.update(values)
    grid.update((a + b) / 2.0 for a, b in zip(values, values[1:]))
    for q in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 0.75):
        grid.add(q)
    return sorted(max(0.0, value) for value in grid)


def evaluate(rows: list[dict[str, str]], threshold: float) -> dict[str, object]:
    run_depth4 = true_runs = false_runs = false_skips = 0
    sparse_wins = sparse_losses = sparse_ties = 0
    depth2_wins = depth2_losses = depth2_ties = 0
    rel_score_sparse: list[float] = []
    rel_time_sparse: list[float] = []
    rel_score_depth2: list[float] = []
    rel_time_depth2: list[float] = []

    for row in rows:
        prob = float(row["run_depth4_prob"])
        label = int(row["run_depth4_label"]) == 1
        run = prob >= threshold
        depth2_score = float(row["depth2_score"])
        depth4_score = float(row["depth4_score"])
        depth2_time = float(row["depth2_time_s"])
        depth4_time = float(row["depth4_time_s"])
        sparse_score = min(depth2_score, depth4_score)
        sparse_time = depth2_time + depth4_time
        target_score = sparse_score if run else depth2_score
        target_time = sparse_time if run else depth2_time

        if run:
            run_depth4 += 1
        if run and label:
            true_runs += 1
        if run and not label:
            false_runs += 1
        if (not run) and label:
            false_skips += 1

        if target_score < sparse_score - 1e-9:
            sparse_wins += 1
        elif target_score > sparse_score + 1e-9:
            sparse_losses += 1
        else:
            sparse_ties += 1
        if target_score < depth2_score - 1e-9:
            depth2_wins += 1
        elif target_score > depth2_score + 1e-9:
            depth2_losses += 1
        else:
            depth2_ties += 1
        rel_score_sparse.append(rel(target_score, sparse_score))
        rel_time_sparse.append(rel(target_time, sparse_time, floor=1e-9))
        rel_score_depth2.append(rel(target_score, depth2_score))
        rel_time_depth2.append(rel(target_time, depth2_time, floor=1e-9))

    return {
        "threshold": threshold,
        "pairs": len(rows),
        "run_depth4": run_depth4,
        "true_runs": true_runs,
        "false_runs": false_runs,
        "false_skips": false_skips,
        "score_wlt_vs_sparse": f"{sparse_wins}/{sparse_losses}/{sparse_ties}",
        "mean_rel_score_vs_sparse": statistics.mean(rel_score_sparse) if rel_score_sparse else 0.0,
        "mean_rel_time_vs_sparse": statistics.mean(rel_time_sparse) if rel_time_sparse else 0.0,
        "score_wlt_vs_depth2": f"{depth2_wins}/{depth2_losses}/{depth2_ties}",
        "mean_rel_score_vs_depth2": statistics.mean(rel_score_depth2) if rel_score_depth2 else 0.0,
        "mean_rel_time_vs_depth2": statistics.mean(rel_time_depth2) if rel_time_depth2 else 0.0,
    }


def parse_checkpoint_threshold(summary: Path, default: float) -> float:
    for row in read_csv(summary):
        if row.get("scope") == "all":
            return default
    return default


def choose_operating_points(rows: list[dict[str, object]], selected_threshold: float) -> list[dict[str, object]]:
    selected = min(rows, key=lambda r: abs(float(r["threshold"]) - selected_threshold))
    zero_skip = [r for r in rows if int(r["false_skips"]) == 0]
    max_zero_skip = min(zero_skip, key=lambda r: float(r["mean_rel_time_vs_sparse"])) if zero_skip else selected
    one_skip = [r for r in rows if int(r["false_skips"]) <= 1]
    max_one_skip = min(one_skip, key=lambda r: float(r["mean_rel_time_vs_sparse"])) if one_skip else selected
    skip_all = max(rows, key=lambda r: float(r["threshold"]))
    eager = min(rows, key=lambda r: abs(float(r["threshold"]) - 0.0))
    out = [
        {"label": "eager sparse", **eager},
        {"label": "selected", **selected},
        {"label": "max zero-skip saving", **max_zero_skip},
        {"label": "max one-skip saving", **max_one_skip},
        {"label": "depth-2 only", **skip_all},
    ]
    # Preserve order but remove duplicate thresholds.
    seen = set()
    unique: list[dict[str, object]] = []
    for row in out:
        key = round(float(row["threshold"]), 12)
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(path: Path, rows: list[dict[str, object]], operating: list[dict[str, object]], selected_threshold: float) -> None:
    selected = next(r for r in operating if r["label"] == "selected")
    max_zero = next((r for r in operating if r["label"] == "max zero-skip saving"), selected)
    lines = [
        "# Sparse Depth-4 Gate Threshold Sensitivity",
        "",
        "This analysis sweeps the deployment threshold of the trained sparse depth-4 gate on the 144-pair independent-seed audit.",
        "It does not retrain the model or rerun synthesis.",
        "",
        f"- selected threshold: {selected_threshold:.6f}",
        f"- selected false skips: {selected['false_skips']}",
        f"- selected time vs sparse: {pct(float(selected['mean_rel_time_vs_sparse']))}",
        f"- best zero-false-skip time vs sparse in sweep: {pct(float(max_zero['mean_rel_time_vs_sparse']))}",
        "",
        "| operating point | threshold | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in operating:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["label"]),
                    f"{float(row['threshold']):.6f}",
                    str(row["run_depth4"]),
                    str(row["false_skips"]),
                    str(row["score_wlt_vs_sparse"]),
                    pct(float(row["mean_rel_score_vs_sparse"])),
                    pct(float(row["mean_rel_time_vs_sparse"])),
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


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth}rrrr>{\raggedright\arraybackslash}p{0.14\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Operating point & Threshold & Run d4 & False skips & Score W/L/T vs sparse & Mean $\Delta$ score & Mean $\Delta$ time \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(str(row["label"])),
                    f"{float(row['threshold']):.4f}",
                    str(row["run_depth4"]),
                    str(row["false_skips"]),
                    str(row["score_wlt_vs_sparse"]),
                    latex_pct(float(row["mean_rel_score_vs_sparse"])),
                    latex_pct(float(row["mean_rel_time_vs_sparse"])),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=RESULTS / "raw_sparse_depth4_gate_generalization.csv")
    ap.add_argument("--selected-threshold", type=float, default=0.005312)
    ap.add_argument("--out", type=Path, default=RESULTS / "summary_sparse_depth4_gate_threshold_sensitivity.csv")
    ap.add_argument("--operating-out", type=Path, default=RESULTS / "summary_sparse_depth4_gate_threshold_operating_points.csv")
    ap.add_argument("--analysis-out", type=Path, default=RESULTS / "analysis_sparse_depth4_gate_threshold_sensitivity.md")
    ap.add_argument("--latex-out", type=Path, default=TABLES / "sparse_depth4_gate_threshold_sensitivity.tex")
    args = ap.parse_args(list(argv) if argv is not None else None)

    raw = read_csv(args.raw)
    probs = [float(row["run_depth4_prob"]) for row in raw]
    rows = [evaluate(raw, threshold) for threshold in threshold_grid(probs, args.selected_threshold)]
    operating = choose_operating_points(rows, args.selected_threshold)
    fields = [
        "threshold",
        "pairs",
        "run_depth4",
        "true_runs",
        "false_runs",
        "false_skips",
        "score_wlt_vs_sparse",
        "mean_rel_score_vs_sparse",
        "mean_rel_time_vs_sparse",
        "score_wlt_vs_depth2",
        "mean_rel_score_vs_depth2",
        "mean_rel_time_vs_depth2",
    ]
    write_csv(args.out, rows, fields)
    write_csv(args.operating_out, operating, ["label", *fields])
    write_analysis(args.analysis_out, rows, operating, args.selected_threshold)
    write_latex(args.latex_out, operating)
    print(f"wrote {args.out}")
    print(f"wrote {args.operating_out}")
    print(f"wrote {args.analysis_out}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
