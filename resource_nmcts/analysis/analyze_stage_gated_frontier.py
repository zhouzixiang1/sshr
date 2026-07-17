#!/usr/bin/env python3
"""Analyze a staged depth-frontier controller from measured depth rows.

The scale harness already measures depth-2, depth-3, and depth-4 Boolean-ring
screening independently.  This script turns those measurements into a
deployable staged controller:

1. evaluate depth 2 and depth 3;
2. run depth 4 only when depth 3 improved enough over depth 2;
3. choose the best score among the evaluated depths.

The threshold is selected on the large frontier policy's validation split and
then applied unchanged to the independent scale and truth-bridge files.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class EvalRow:
    source: str
    name: str
    n: int
    profile: str
    term_count: int
    method: str
    score: float
    time_s: float
    t_count: float = 0.0
    cnot: float = 0.0
    depth: float = 0.0
    gates: float = 0.0
    peak_ancilla: float = 0.0
    schedule_t_depth_proxy: float = 0.0
    explicit_ancilla_lifetime_area: float = 0.0
    verified: bool = True


@dataclass(frozen=True)
class StageEval:
    source: str
    name: str
    n: int
    profile: str
    term_count: int
    selected_depth: int
    run_depth4: bool
    score: float
    time_s: float
    t_count: float
    cnot: float
    depth: float
    gates: float
    peak_ancilla: float
    schedule_t_depth_proxy: float
    explicit_ancilla_lifetime_area: float
    verified: bool


def as_float(row: dict[str, str], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return float(value)
    return default


def as_bool(row: dict[str, str], *keys: str) -> bool:
    values = [row.get(key, "") for key in keys if key in row]
    if not values:
        return True
    return all(value in ("True", "1", "true") for value in values if value != "")


def load_training_depth_rows(path: Path, split: str = "valid") -> dict[str, dict[str, EvalRow]]:
    grouped: dict[str, dict[str, EvalRow]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["split"] != split:
                continue
            name = row["name"]
            n = int(row["n"])
            profile = row["profile"]
            term_count = int(row["term_count"])
            grouped[name] = {}
            for depth in (2, 3, 4):
                grouped[name][f"screen_depth{depth}"] = EvalRow(
                    source=f"training_{split}",
                    name=name,
                    n=n,
                    profile=profile,
                    term_count=term_count,
                    method=f"screen_depth{depth}",
                    score=float(row[f"depth{depth}_score"]),
                    time_s=float(row[f"depth{depth}_time_s"]),
                    t_count=float(row[f"depth{depth}_T"]),
                    cnot=float(row[f"depth{depth}_CNOT"]),
                    depth=float(row[f"depth{depth}_depth"]),
                    peak_ancilla=float(row[f"depth{depth}_ancilla"]),
                )
            grouped[name]["adaptive_all_depth"] = EvalRow(
                source=f"training_{split}",
                name=name,
                n=n,
                profile=profile,
                term_count=term_count,
                method="adaptive_all_depth",
                score=float(row["oracle_score"]),
                time_s=float(row["oracle_all_time_s"]),
            )
    return grouped


def load_method_rows(path: Path, source: str) -> dict[str, dict[str, EvalRow]]:
    grouped: dict[str, dict[str, EvalRow]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["name"]
            grouped.setdefault(name, {})[row["method"]] = EvalRow(
                source=source,
                name=name,
                n=int(row["n"]),
                profile=row["profile"],
                term_count=int(row["term_count"]),
                method=row["method"],
                score=as_float(row, "score"),
                time_s=as_float(row, "time_s", "plan_time_s"),
                t_count=as_float(row, "T"),
                cnot=as_float(row, "CNOT"),
                depth=as_float(row, "depth"),
                gates=as_float(row, "gates"),
                peak_ancilla=as_float(row, "peak_ancilla"),
                schedule_t_depth_proxy=as_float(row, "schedule_t_depth_proxy"),
                explicit_ancilla_lifetime_area=as_float(row, "explicit_ancilla_lifetime_area"),
                verified=as_bool(row, "truth_verified", "anf_verified", "circuit_anf_verified"),
            )
    return grouped


def stage_eval(methods: dict[str, EvalRow], threshold: float) -> StageEval:
    d2 = methods["screen_depth2"]
    d3 = methods["screen_depth3"]
    d4 = methods["screen_depth4"]
    improvement = (d2.score - d3.score) / max(d2.score, 1.0)
    run_depth4 = improvement >= threshold
    candidates = [d2, d3]
    if run_depth4:
        candidates.append(d4)
    selected = min(candidates, key=lambda row: (row.score, row.time_s, row.method))
    staged_time = d2.time_s + d3.time_s + (d4.time_s if run_depth4 else 0.0)
    selected_depth = int(selected.method.removeprefix("screen_depth"))
    return StageEval(
        source=selected.source,
        name=selected.name,
        n=selected.n,
        profile=selected.profile,
        term_count=selected.term_count,
        selected_depth=selected_depth,
        run_depth4=run_depth4,
        score=selected.score,
        time_s=staged_time,
        t_count=selected.t_count,
        cnot=selected.cnot,
        depth=selected.depth,
        gates=selected.gates,
        peak_ancilla=selected.peak_ancilla,
        schedule_t_depth_proxy=selected.schedule_t_depth_proxy,
        explicit_ancilla_lifetime_area=selected.explicit_ancilla_lifetime_area,
        verified=selected.verified,
    )


def rel(target: float, base: float, floor: float = 1.0) -> float:
    return (target - base) / max(abs(base), floor)


def compare(staged: list[StageEval], grouped: dict[str, dict[str, EvalRow]], baseline: str) -> dict[str, object]:
    wins = losses = ties = 0
    score_deltas: list[float] = []
    time_deltas: list[float] = []
    t_depth_deltas: list[float] = []
    aux_area_deltas: list[float] = []
    for ev in staged:
        methods = grouped[ev.name]
        if baseline not in methods:
            continue
        base = methods[baseline]
        if ev.score < base.score - 1e-9:
            wins += 1
        elif ev.score > base.score + 1e-9:
            losses += 1
        else:
            ties += 1
        score_deltas.append(rel(ev.score, base.score))
        time_deltas.append(rel(ev.time_s, base.time_s, floor=1e-9))
        if base.schedule_t_depth_proxy:
            t_depth_deltas.append(rel(ev.schedule_t_depth_proxy, base.schedule_t_depth_proxy))
        if base.explicit_ancilla_lifetime_area:
            aux_area_deltas.append(rel(ev.explicit_ancilla_lifetime_area, base.explicit_ancilla_lifetime_area))
    return {
        "pairs": wins + losses + ties,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_rel_score": statistics.mean(score_deltas) if score_deltas else 0.0,
        "mean_rel_time": statistics.mean(time_deltas) if time_deltas else 0.0,
        "mean_rel_t_depth": statistics.mean(t_depth_deltas) if t_depth_deltas else 0.0,
        "mean_rel_aux_area": statistics.mean(aux_area_deltas) if aux_area_deltas else 0.0,
    }


def select_threshold(
    validation: dict[str, dict[str, EvalRow]],
    thresholds: list[float],
    max_valid_score_gap: float,
) -> tuple[float, list[dict[str, object]]]:
    rows = []
    best: tuple[float, float, float] | None = None
    for threshold in thresholds:
        staged = [stage_eval(methods, threshold) for methods in validation.values()]
        cmp_all = compare(staged, validation, "adaptive_all_depth")
        run_depth4 = sum(1 for ev in staged if ev.run_depth4)
        rows.append(
            {
                "threshold": threshold,
                "valid_score_gap": cmp_all["mean_rel_score"],
                "valid_time_delta": cmp_all["mean_rel_time"],
                "run_depth4": run_depth4,
            }
        )
        score_gap = float(cmp_all["mean_rel_score"])
        time_delta = float(cmp_all["mean_rel_time"])
        if score_gap <= max_valid_score_gap:
            # Time delta is negative when staged evaluation is faster.
            candidate = (time_delta, score_gap, threshold)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        best_row = min(rows, key=lambda row: (abs(float(row["valid_score_gap"])), float(row["valid_time_delta"])))
        return float(best_row["threshold"]), rows
    return best[2], rows


def pct(value: object) -> str:
    return f"{float(value):+.2%}"


def latex_pct(value: object) -> str:
    return pct(value).replace("%", r"\%")


def latex_text(value: object) -> str:
    return str(value).replace("_", r"\_")


def write_outputs(
    validation: dict[str, dict[str, EvalRow]],
    datasets: list[tuple[str, dict[str, dict[str, EvalRow]]]],
    threshold: float,
    threshold_rows: list[dict[str, object]],
    args: argparse.Namespace,
) -> None:
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)

    raw_path = args.results_dir / "raw_stage_gated_frontier.csv"
    summary_path = args.results_dir / "summary_stage_gated_frontier.csv"
    analysis_path = args.results_dir / "analysis_stage_gated_frontier.md"
    manifest_path = args.results_dir / "manifest_stage_gated_frontier.json"
    table_path = args.tables_dir / "stage_gated_frontier.tex"

    all_raw: list[StageEval] = []
    summary_rows: list[dict[str, object]] = []

    for source, grouped in [("training_valid", validation), *datasets]:
        staged = [stage_eval(methods, threshold) for methods in grouped.values()]
        all_raw.extend(staged)
        baselines = ["adaptive_all_depth", "screen_depth2", "depth_frontier_policy"]
        if source == "training_valid":
            baselines = ["adaptive_all_depth", "screen_depth2"]
        for baseline in baselines:
            if not all(baseline in methods for methods in grouped.values()):
                continue
            stats = compare(staged, grouped, baseline)
            summary_rows.append(
                {
                    "source": source,
                    "method": "stage_gated_frontier",
                    "baseline": baseline,
                    "pairs": stats["pairs"],
                    "score_wins": stats["wins"],
                    "score_losses": stats["losses"],
                    "score_ties": stats["ties"],
                    "mean_rel_score": stats["mean_rel_score"],
                    "mean_rel_time": stats["mean_rel_time"],
                    "mean_rel_t_depth": stats["mean_rel_t_depth"],
                    "mean_rel_aux_area": stats["mean_rel_aux_area"],
                    "run_depth4": sum(1 for ev in staged if ev.run_depth4),
                    "selected_depth2": sum(1 for ev in staged if ev.selected_depth == 2),
                    "selected_depth3": sum(1 for ev in staged if ev.selected_depth == 3),
                    "selected_depth4": sum(1 for ev in staged if ev.selected_depth == 4),
                    "verified_rows": sum(1 for ev in staged if ev.verified),
                }
            )

    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "name",
                "n",
                "profile",
                "term_count",
                "selected_depth",
                "run_depth4",
                "score",
                "T",
                "CNOT",
                "depth",
                "gates",
                "peak_ancilla",
                "schedule_t_depth_proxy",
                "explicit_ancilla_lifetime_area",
                "time_s",
                "verified",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for ev in all_raw:
            writer.writerow(
                {
                    "source": ev.source,
                    "name": ev.name,
                    "n": ev.n,
                    "profile": ev.profile,
                    "term_count": ev.term_count,
                    "selected_depth": ev.selected_depth,
                    "run_depth4": int(ev.run_depth4),
                    "score": ev.score,
                    "T": ev.t_count,
                    "CNOT": ev.cnot,
                    "depth": ev.depth,
                    "gates": ev.gates,
                    "peak_ancilla": ev.peak_ancilla,
                    "schedule_t_depth_proxy": ev.schedule_t_depth_proxy,
                    "explicit_ancilla_lifetime_area": ev.explicit_ancilla_lifetime_area,
                    "time_s": ev.time_s,
                    "verified": int(ev.verified),
                }
            )

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrrrr}\n")
        f.write("\\toprule\n")
        f.write("Source & Baseline & Pairs & Score W/L/T & Mean $\\Delta$ score & Mean $\\Delta$ time & Run depth-4 \\\\\n")
        f.write("\\midrule\n")
        for row in summary_rows:
            if row["source"] not in {"scale_generalization", "truth_bridge_n23"}:
                continue
            if row["baseline"] not in {"adaptive_all_depth", "screen_depth2", "depth_frontier_policy"}:
                continue
            f.write(
                f"{latex_text(row['source'])} & "
                f"{latex_text(row['baseline'])} & "
                f"{row['pairs']} & {row['score_wins']}/{row['score_losses']}/{row['score_ties']} & "
                f"{latex_pct(row['mean_rel_score'])} & {latex_pct(row['mean_rel_time'])} & "
                f"{row['run_depth4']} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")

    scale_summary = [row for row in summary_rows if row["source"] == "scale_generalization"]
    truth_summary = [row for row in summary_rows if row["source"] == "truth_bridge_n23"]
    with analysis_path.open("w", encoding="utf-8") as f:
        f.write("# Stage-Gated Depth Frontier\n\n")
        f.write(
            "A progressive controller first evaluates depth-2 and depth-3 Boolean-ring "
            "screens, then evaluates depth-4 only when depth-3 improves over depth-2 "
            f"by at least {threshold:.3%}.  The threshold is selected on the large "
            "frontier policy validation split and then applied unchanged to the "
            "independent scale and truth-bridge rows.\n\n"
        )
        f.write("## Threshold selection\n\n")
        f.write(f"- validation score-gap budget: {args.max_valid_score_gap:.3%}\n")
        f.write(f"- selected threshold: {threshold:.3%}\n\n")
        f.write("| threshold | valid score gap | valid time | run depth-4 |\n")
        f.write("|---:|---:|---:|---:|\n")
        for row in threshold_rows:
            f.write(
                f"| {float(row['threshold']):.3%} | {pct(row['valid_score_gap'])} | "
                f"{pct(row['valid_time_delta'])} | {row['run_depth4']} |\n"
            )
        f.write("\n## Independent comparisons\n\n")
        f.write("| source | baseline | pairs | score W/L/T | mean score | mean time | T-depth | aux area | run depth-4 |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in [*scale_summary, *truth_summary]:
            f.write(
                f"| {row['source']} | {row['baseline']} | {row['pairs']} | "
                f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
                f"{pct(row['mean_rel_score'])} | {pct(row['mean_rel_time'])} | "
                f"{pct(row['mean_rel_t_depth'])} | {pct(row['mean_rel_aux_area'])} | "
                f"{row['run_depth4']} |\n"
            )
        f.write("\n## Verification\n\n")
        for source, grouped in datasets:
            staged = [stage_eval(methods, threshold) for methods in grouped.values()]
            f.write(f"- {source}: selected rows verified {sum(1 for ev in staged if ev.verified)}/{len(staged)}\n")

    manifest_path.write_text(
        json.dumps(
            {
                "threshold": threshold,
                "max_valid_score_gap": args.max_valid_score_gap,
                "training_frontier_raw": str(args.training_frontier_raw),
                "scale_raw": str(args.scale_raw),
                "truth_bridge_raw": str(args.truth_bridge_raw),
                "outputs": {
                    "raw": str(raw_path),
                    "summary": str(summary_path),
                    "analysis": str(analysis_path),
                    "table": str(table_path),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"selected threshold {threshold:.6f}")
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")
    print(f"wrote {manifest_path}")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--training-frontier-raw",
        type=Path,
        default=RESULTS / "raw_boolean_screen_depth_frontier_policy_large.csv",
    )
    ap.add_argument(
        "--scale-raw",
        type=Path,
        default=RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
    )
    ap.add_argument(
        "--truth-bridge-raw",
        type=Path,
        default=RESULTS / "raw_truth_bridge_n23_large_frontier_terms.csv",
    )
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    ap.add_argument("--tables-dir", type=Path, default=TABLES)
    ap.add_argument("--max-valid-score-gap", type=float, default=0.0005)
    ap.add_argument(
        "--threshold-grid",
        default="-0.01,0,0.0025,0.005,0.0075,0.01,0.0125,0.015,0.02,0.03,0.05",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    thresholds = [float(value.strip()) for value in args.threshold_grid.split(",") if value.strip()]
    validation = load_training_depth_rows(args.training_frontier_raw, split="valid")
    threshold, threshold_rows = select_threshold(validation, thresholds, args.max_valid_score_gap)
    datasets = [
        ("scale_generalization", load_method_rows(args.scale_raw, "scale_generalization")),
        ("truth_bridge_n23", load_method_rows(args.truth_bridge_raw, "truth_bridge_n23")),
    ]
    write_outputs(validation, datasets, threshold, threshold_rows, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
