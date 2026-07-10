#!/usr/bin/env python3
"""Audit sparse depth-4 gate generalization across independent seeds."""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path
from typing import Iterable

import torch

from train_screen_depth_frontier_policy import LabelObjective, build_examples, split_arg
from train_sparse_depth4_gate import (
    GATE_DEPTHS,
    SparseDepth4GateNet,
    evaluate_gate,
    gate_feature_names,
    predict_probs,
    run_depth4_label,
    selected_score,
    selected_time,
    sparse_score,
    sparse_time,
)


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
MODELS = THIS_DIR / "models"


def pct(value: float) -> str:
    return f"{100.0 * float(value):+.2f}%"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def load_gate(path: Path) -> tuple[SparseDepth4GateNet, torch.Tensor, torch.Tensor, float, dict]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    feature_names = checkpoint.get("feature_names", gate_feature_names())
    expected = gate_feature_names()
    if list(feature_names) != expected:
        raise ValueError(
            "checkpoint feature_names do not match current gate features: "
            f"{feature_names!r} != {expected!r}"
        )
    hidden = int(checkpoint.get("hidden", 96))
    model = SparseDepth4GateNet(len(expected), hidden=hidden)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    mean = torch.tensor(checkpoint["mean"], dtype=torch.float32)
    std = torch.tensor(checkpoint["std"], dtype=torch.float32)
    threshold = float(checkpoint["threshold"])
    return model, mean, std, threshold, checkpoint


def rel(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def raw_rows(seed: int, examples: list, probs: list[float], threshold: float, eps: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for ex, prob in zip(examples, probs):
        run = prob >= threshold
        depth2 = ex.evals[2]
        depth4 = ex.evals[4]
        rows.append(
            {
                "seed": seed,
                "name": ex.name,
                "n": ex.n,
                "profile": ex.profile,
                "term_count": ex.term_count,
                "run_depth4_label": run_depth4_label(ex, eps),
                "run_depth4_prob": prob,
                "run_depth4_pred": int(run),
                "false_skip": int((not run) and run_depth4_label(ex, eps) == 1),
                "depth2_score": depth2.score,
                "depth4_score": depth4.score,
                "gate_score": selected_score(ex, run),
                "sparse_score": sparse_score(ex),
                "depth2_time_s": depth2.time_s,
                "depth4_time_s": depth4.time_s,
                "gate_time_s": selected_time(ex, run),
                "sparse_time_s": sparse_time(ex),
                "rel_score_vs_sparse": rel(selected_score(ex, run), sparse_score(ex)),
                "rel_time_vs_sparse": rel(selected_time(ex, run), sparse_time(ex), floor=1e-9),
                "rel_score_vs_depth2": rel(selected_score(ex, run), depth2.score),
                "rel_time_vs_depth2": rel(selected_time(ex, run), depth2.time_s, floor=1e-9),
            }
        )
    return rows


def write_raw(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "seed",
        "name",
        "n",
        "profile",
        "term_count",
        "run_depth4_label",
        "run_depth4_prob",
        "run_depth4_pred",
        "false_skip",
        "depth2_score",
        "depth4_score",
        "gate_score",
        "sparse_score",
        "depth2_time_s",
        "depth4_time_s",
        "gate_time_s",
        "sparse_time_s",
        "rel_score_vs_sparse",
        "rel_time_vs_sparse",
        "rel_score_vs_depth2",
        "rel_time_vs_depth2",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def stats_row(scope: str, examples: list, probs: list[float], threshold: float, eps: float) -> dict[str, object]:
    stats = evaluate_gate(examples, probs, threshold, eps, scope)
    return {
        "scope": scope,
        "pairs": stats.pairs,
        "run_depth4": stats.run_depth4,
        "true_runs": stats.true_runs,
        "false_runs": stats.false_runs,
        "false_skips": stats.false_skips,
        "score_wlt_vs_sparse": (
            f"{stats.score_wins_vs_sparse}/{stats.score_losses_vs_sparse}/{stats.score_ties_vs_sparse}"
        ),
        "mean_rel_score_vs_sparse": stats.mean_rel_score_vs_sparse,
        "mean_rel_time_vs_sparse": stats.mean_rel_time_vs_sparse,
        "score_wlt_vs_depth2": (
            f"{stats.score_wins_vs_depth2}/{stats.score_losses_vs_depth2}/{stats.score_ties_vs_depth2}"
        ),
        "mean_rel_score_vs_depth2": stats.mean_rel_score_vs_depth2,
        "mean_rel_time_vs_depth2": stats.mean_rel_time_vs_depth2,
    }


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "scope",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(path: Path, rows: list[dict[str, object]], args: argparse.Namespace, checkpoint: dict, threshold: float) -> None:
    all_row = rows[0]
    false_skips = [int(row["false_skips"]) for row in rows if row["scope"].startswith("seed=")]
    try:
        model_path = str(args.model.resolve().relative_to(THIS_DIR))
    except ValueError:
        model_path = str(args.model)
    lines = [
        "# Sparse Depth-4 Gate Generalization Audit",
        "",
        "The trained sparse depth-4 gate is evaluated without retraining on independent generated term sets.",
        "The deterministic sparse depth-2/4 frontier remains the quality reference.",
        "",
        f"- model: `{model_path}`",
        f"- checkpoint train n: {checkpoint.get('train_n')}; checkpoint test n: {checkpoint.get('test_n')}",
        f"- audit seeds: {args.seeds}",
        f"- audit n: {args.ns}; per n per seed: {args.per_n}",
        f"- threshold: {threshold:.6f}",
        f"- total audit pairs: {all_row['pairs']}",
        f"- total false skips: {all_row['false_skips']}",
        f"- seed false skips: min {min(false_skips) if false_skips else 0}, max {max(false_skips) if false_skips else 0}",
        "",
        "| scope | pairs | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse | score W/L/T vs depth-2 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["scope"]),
                    str(row["pairs"]),
                    str(row["run_depth4"]),
                    str(row["false_skips"]),
                    str(row["score_wlt_vs_sparse"]),
                    pct(float(row["mean_rel_score_vs_sparse"])),
                    pct(float(row["mean_rel_time_vs_sparse"])),
                    str(row["score_wlt_vs_depth2"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- This audit tests deployment stability of the learned budget gate, not a new quality frontier.",
            "- A zero false-skip row means the gate did not skip any depth-4 case that would have improved over depth 2 under the current score.",
            "- Mean time is measured relative to evaluating both depth 2 and depth 4 in the deterministic sparse frontier.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def table_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    keep = [row for row in rows if row["scope"] == "all" or str(row["scope"]).startswith("n=")]
    return keep


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.13\linewidth}rrrr>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Scope & Pairs & Run d4 & False skips & Score W/L/T vs sparse & Mean $\Delta$ score & Mean $\Delta$ time & Score W/L/T vs depth-2 \\",
        r"\midrule",
    ]
    for row in table_rows(rows):
        lines.append(
            " & ".join(
                [
                    tex_escape(str(row["scope"])),
                    str(row["pairs"]),
                    str(row["run_depth4"]),
                    str(row["false_skips"]),
                    str(row["score_wlt_vs_sparse"]),
                    latex_pct(float(row["mean_rel_score_vs_sparse"])),
                    latex_pct(float(row["mean_rel_time_vs_sparse"])),
                    str(row["score_wlt_vs_depth2"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=MODELS / "sparse_depth4_gate.pt")
    ap.add_argument("--seeds", default="20260801,20260802,20260803")
    ap.add_argument("--ns", default="24,28,32,40")
    ap.add_argument("--per-n", type=int, default=12)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--eps", type=float, default=1e-9)
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    ap.add_argument("--tables-dir", type=Path, default=TABLES)
    args = ap.parse_args(list(argv) if argv is not None else None)

    seeds = split_arg(args.seeds)
    ns = split_arg(args.ns)
    model, mean, std, threshold, checkpoint = load_gate(args.model)
    objective = LabelObjective()

    all_examples = []
    all_probs: list[float] = []
    by_seed: dict[int, tuple[list, list[float]]] = {}
    by_n: dict[int, tuple[list, list[float]]] = {n: ([], []) for n in ns}
    raw: list[dict[str, object]] = []

    for seed in seeds:
        print(f"building audit examples seed={seed}", flush=True)
        examples = build_examples(
            "test",
            ns,
            args.per_n,
            seed,
            args.action_width,
            GATE_DEPTHS,
            args.workers,
            objective,
        )
        probs = predict_probs(model, mean, std, examples)
        by_seed[seed] = (examples, probs)
        all_examples.extend(examples)
        all_probs.extend(probs)
        raw.extend(raw_rows(seed, examples, probs, threshold, args.eps))
        for n in ns:
            n_examples = [ex for ex in examples if ex.n == n]
            n_probs = [prob for ex, prob in zip(examples, probs) if ex.n == n]
            by_n[n][0].extend(n_examples)
            by_n[n][1].extend(n_probs)

    summary = [stats_row("all", all_examples, all_probs, threshold, args.eps)]
    for seed in seeds:
        examples, probs = by_seed[seed]
        summary.append(stats_row(f"seed={seed}", examples, probs, threshold, args.eps))
    for n in ns:
        examples, probs = by_n[n]
        summary.append(stats_row(f"n={n}", examples, probs, threshold, args.eps))

    raw_path = args.results_dir / "raw_sparse_depth4_gate_generalization.csv"
    summary_path = args.results_dir / "summary_sparse_depth4_gate_generalization.csv"
    analysis_path = args.results_dir / "analysis_sparse_depth4_gate_generalization.md"
    table_path = args.tables_dir / "sparse_depth4_gate_generalization.tex"
    write_raw(raw_path, raw)
    write_summary(summary_path, summary)
    write_analysis(analysis_path, summary, args, checkpoint, threshold)
    write_latex(table_path, summary)

    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
