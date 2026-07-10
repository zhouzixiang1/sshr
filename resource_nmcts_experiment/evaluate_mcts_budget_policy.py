#!/usr/bin/env python3
"""Evaluate a contextual-bandit Pareto-MCTS budget policy."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
from pathlib import Path
from typing import Iterable

import torch

from train_mcts_budget_policy import (
    BudgetPolicy,
    FEATURE_NAMES,
    RESOURCE_METRICS,
    display_path,
    load_samples,
)


BOOTSTRAP_SAMPLES = 4000
BOOTSTRAP_SEED = 20260745
THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_MODEL = THIS_DIR / "models" / "mcts_budget_policy.pt"
DEFAULT_TEST = RESULTS / "raw_mcts_budget_policy_test_seed45.csv"
DEFAULT_SUMMARY = RESULTS / "summary_mcts_budget_policy.csv"
DEFAULT_ANALYSIS = RESULTS / "analysis_mcts_budget_policy.md"
DEFAULT_MANIFEST = RESULTS / "manifest_mcts_budget_policy.json"
DEFAULT_TRAINING_MANIFEST = RESULTS / "manifest_mcts_budget_policy_training.json"
DEFAULT_DECISIONS = RESULTS / "raw_mcts_budget_policy_decisions.csv"
DEFAULT_LATEX = THIS_DIR / "paper_latex" / "tables" / "mcts_budget_policy.tex"


def parse_thresholds(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def resolve_manifest_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else THIS_DIR / path


def compare(target: float, baseline: float) -> tuple[int, int, int]:
    if target < baseline:
        return 1, 0, 0
    if target > baseline:
        return 0, 1, 0
    return 0, 0, 1


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def bootstrap_intervals(samples, run: list[bool]) -> dict[str, float]:
    rng = random.Random(BOOTSTRAP_SEED)
    score_regrets: list[float] = []
    time_changes: list[float] = []
    retained: list[float] = []
    n = len(samples)
    for _ in range(BOOTSTRAP_SAMPLES):
        indices = [rng.randrange(n) for _ in range(n)]
        chosen_scores = [
            samples[index].pareto_score if run[index] else samples[index].resource_score
            for index in indices
        ]
        pareto_scores = [samples[index].pareto_score for index in indices]
        resource_scores = [samples[index].resource_score for index in indices]
        policy_times = [
            samples[index].resource_time_s
            + (samples[index].pareto_time_s if run[index] else 0.0)
            for index in indices
        ]
        pareto_times = [samples[index].pareto_time_s for index in indices]
        score_regrets.append(
            statistics.mean(
                (target - baseline) / baseline if baseline else 0.0
                for target, baseline in zip(chosen_scores, pareto_scores)
            )
        )
        time_changes.append(sum(policy_times) / sum(pareto_times) - 1.0)
        pareto_gain = statistics.mean(resource_scores) - statistics.mean(pareto_scores)
        policy_gain = statistics.mean(resource_scores) - statistics.mean(chosen_scores)
        retained.append(policy_gain / pareto_gain if pareto_gain > 1e-12 else 1.0)
    return {
        "score_regret_ci_low": percentile(score_regrets, 0.025),
        "score_regret_ci_high": percentile(score_regrets, 0.975),
        "time_change_ci_low": percentile(time_changes, 0.025),
        "time_change_ci_high": percentile(time_changes, 0.975),
        "quality_retained_ci_low": percentile(retained, 0.025),
        "quality_retained_ci_high": percentile(retained, 0.975),
    }


def evaluate(samples, probabilities: list[float], threshold: float) -> dict[str, object]:
    run = [probability >= threshold for probability in probabilities]
    chosen_scores = [
        sample.pareto_score if action else sample.resource_score
        for sample, action in zip(samples, run)
    ]
    policy_times = [
        sample.resource_time_s + (sample.pareto_time_s if action else 0.0)
        for sample, action in zip(samples, run)
    ]
    pareto_scores = [sample.pareto_score for sample in samples]
    resource_scores = [sample.resource_score for sample in samples]
    pareto_times = [sample.pareto_time_s for sample in samples]

    vs_pareto = [compare(target, baseline) for target, baseline in zip(chosen_scores, pareto_scores)]
    vs_resource = [compare(target, baseline) for target, baseline in zip(chosen_scores, resource_scores)]
    pareto_gain = statistics.mean(resource_scores) - statistics.mean(pareto_scores)
    policy_gain = statistics.mean(resource_scores) - statistics.mean(chosen_scores)
    score_regrets = [
        (target - baseline) / baseline if baseline else 0.0
        for target, baseline in zip(chosen_scores, pareto_scores)
    ]
    row: dict[str, object] = {
        "threshold": threshold,
        "pairs": len(samples),
        "run_pareto": sum(run),
        "stop": len(run) - sum(run),
        "run_fraction": sum(run) / len(run),
        "vs_pareto_wins": sum(item[0] for item in vs_pareto),
        "vs_pareto_losses": sum(item[1] for item in vs_pareto),
        "vs_pareto_ties": sum(item[2] for item in vs_pareto),
        "vs_resource_wins": sum(item[0] for item in vs_resource),
        "vs_resource_losses": sum(item[1] for item in vs_resource),
        "vs_resource_ties": sum(item[2] for item in vs_resource),
        "mean_policy_score": statistics.mean(chosen_scores),
        "mean_pareto_score": statistics.mean(pareto_scores),
        "mean_resource_score": statistics.mean(resource_scores),
        "mean_score_regret_vs_pareto": statistics.mean(score_regrets),
        "max_score_regret_vs_pareto": max(score_regrets),
        "quality_gain_retained": policy_gain / pareto_gain if pareto_gain > 1e-12 else 1.0,
        "policy_total_time_s": sum(policy_times),
        "pareto_total_time_s": sum(pareto_times),
        "time_change_vs_pareto": sum(policy_times) / sum(pareto_times) - 1.0,
    }
    for metric in RESOURCE_METRICS:
        policy_values = [
            sample.pareto_metrics[metric] if action else sample.resource_metrics[metric]
            for sample, action in zip(samples, run)
        ]
        resource_values = [sample.resource_metrics[metric] for sample in samples]
        pareto_values = [sample.pareto_metrics[metric] for sample in samples]
        relative_resource = [
            (target - baseline) / baseline if baseline else 0.0
            for target, baseline in zip(policy_values, resource_values)
        ]
        relative_pareto = [
            (target - baseline) / baseline if baseline else 0.0
            for target, baseline in zip(policy_values, pareto_values)
        ]
        row[f"mean_policy_{metric}"] = statistics.mean(policy_values)
        row[f"mean_resource_{metric}"] = statistics.mean(resource_values)
        row[f"mean_pareto_{metric}"] = statistics.mean(pareto_values)
        row[f"mean_relative_vs_resource_{metric}"] = statistics.mean(relative_resource)
        row[f"mean_relative_vs_pareto_{metric}"] = statistics.mean(relative_pareto)
    row.update(bootstrap_intervals(samples, run))
    return row


def decision_rows(samples, probabilities: list[float], thresholds: list[float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for threshold in thresholds:
        for sample, probability in zip(samples, probabilities):
            run = probability >= threshold
            row: dict[str, object] = {
                "name": sample.name,
                "verified": True,
                "threshold": threshold,
                "run_probability": probability,
                "action": "run_pareto" if run else "stop_after_resource",
                "resource_time_s": sample.resource_time_s,
                "pareto_time_s": sample.pareto_time_s,
                "policy_time_s": sample.resource_time_s + (sample.pareto_time_s if run else 0.0),
            }
            for metric in RESOURCE_METRICS:
                row[f"resource_{metric}"] = sample.resource_metrics[metric]
                row[f"pareto_{metric}"] = sample.pareto_metrics[metric]
                row[f"policy_{metric}"] = (
                    sample.pareto_metrics[metric] if run else sample.resource_metrics[metric]
                )
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# MCTS Budget Policy Evaluation",
        "",
        "The policy first obtains a verified Resource-NMCTS result and then chooses whether to run the more expensive Pareto-Resource-NMCTS search.",
        "Reported time is conservative: Resource-NMCTS time is added even when Pareto-Resource-NMCTS internally repeats some candidates.",
        "",
        f"Bootstrap intervals use {BOOTSTRAP_SAMPLES} deterministic paired resamples.",
        "",
        "| threshold | pairs | run/stop | vs Pareto W/L/T | vs Resource W/L/T | mean score regret [95% CI] | quality gain retained [95% CI] | time change [95% CI] |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {float(row['threshold']):.3f} | {row['pairs']} | {row['run_pareto']}/{row['stop']} | "
            f"{row['vs_pareto_wins']}/{row['vs_pareto_losses']}/{row['vs_pareto_ties']} | "
            f"{row['vs_resource_wins']}/{row['vs_resource_losses']}/{row['vs_resource_ties']} | "
            f"{100.0 * float(row['mean_score_regret_vs_pareto']):+.3f}% "
            f"[{100.0 * float(row['score_regret_ci_low']):+.3f}, {100.0 * float(row['score_regret_ci_high']):+.3f}] | "
            f"{100.0 * float(row['quality_gain_retained']):.2f}% "
            f"[{100.0 * float(row['quality_retained_ci_low']):.2f}, {100.0 * float(row['quality_retained_ci_high']):.2f}] | "
            f"{100.0 * float(row['time_change_vs_pareto']):+.2f}% "
            f"[{100.0 * float(row['time_change_ci_low']):+.2f}, {100.0 * float(row['time_change_ci_high']):+.2f}] |"
        )
    lines.extend(
        [
            "",
            "## Resource metrics",
            "",
            "| threshold | metric | policy mean | Resource mean | Pareto mean | policy vs Resource | policy vs Pareto |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        for metric in RESOURCE_METRICS:
            lines.append(
                f"| {float(row['threshold']):.3f} | {metric} | "
                f"{float(row[f'mean_policy_{metric}']):.4f} | "
                f"{float(row[f'mean_resource_{metric}']):.4f} | "
                f"{float(row[f'mean_pareto_{metric}']):.4f} | "
                f"{100.0 * float(row[f'mean_relative_vs_resource_{metric}']):+.3f}% | "
                f"{100.0 * float(row[f'mean_relative_vs_pareto_{metric}']):+.3f}% |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{lrrrrr>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Threshold & Run/stop & Vs. Pareto & Vs. Resource & Score regret & Time change & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{float(row['threshold']):.2f} & {row['run_pareto']}/{row['stop']} & "
            f"{row['vs_pareto_wins']}/{row['vs_pareto_losses']}/{row['vs_pareto_ties']} & "
            f"{row['vs_resource_wins']}/{row['vs_resource_losses']}/{row['vs_resource_ties']} & "
            f"{100.0 * float(row['mean_score_regret_vs_pareto']):+.2f}\\% & "
            f"{100.0 * float(row['time_change_vs_pareto']):+.2f}\\% & "
            f"Retains {100.0 * float(row['quality_gain_retained']):.1f}\\% of the Pareto score gain \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--csvs", default=str(DEFAULT_TEST))
    parser.add_argument("--thresholds", default="0.6")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--training-manifest", type=Path, default=DEFAULT_TRAINING_MANIFEST)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--latex", type=Path, default=DEFAULT_LATEX)
    parser.add_argument("--random-truth-only", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    payload = torch.load(args.model, map_location="cpu")
    if list(payload["feature_names"]) != FEATURE_NAMES:
        raise RuntimeError("budget-policy feature contract mismatch")
    model = BudgetPolicy(len(FEATURE_NAMES), hidden=int(payload["hidden"]))
    model.load_state_dict(payload["state_dict"])
    model.eval()
    mean = torch.tensor(payload["mean"], dtype=torch.float32)
    std = torch.tensor(payload["std"], dtype=torch.float32).clamp_min(1e-6)
    paths = [Path(item.strip()) for item in args.csvs.split(",") if item.strip()]
    samples = load_samples(paths, args.random_truth_only)
    x = torch.tensor([sample.features for sample in samples], dtype=torch.float32)
    with torch.no_grad():
        probabilities = torch.sigmoid(model((x - mean) / std)).tolist()
    thresholds = parse_thresholds(args.thresholds)
    rows = [evaluate(samples, probabilities, threshold) for threshold in thresholds]
    write_csv(args.summary, rows)
    write_markdown(args.analysis, rows)
    if args.decisions is not None:
        write_csv(args.decisions, decision_rows(samples, probabilities, thresholds))
    if args.latex is not None:
        write_latex(args.latex, rows)
    training_manifest = json.loads(args.training_manifest.read_text(encoding="utf-8"))
    train_paths = [
        resolve_manifest_path(path) for path in training_manifest.get("train_csvs", [])
    ]
    validation_paths = [
        resolve_manifest_path(path)
        for path in training_manifest.get("validation_csvs", [])
    ]
    reference_samples = load_samples(train_paths + validation_paths, args.random_truth_only)
    reference_fingerprints = {sample.fingerprint for sample in reference_samples}
    test_fingerprints = {sample.fingerprint for sample in samples}
    overlap_count = len(reference_fingerprints & test_fingerprints)
    selected = rows[0]
    decision_count = len(samples) * len(thresholds)
    gates = [
        {
            "gate": "disjoint train/validation/test functions",
            "status": "pass" if overlap_count == 0 else "needs revision",
            "evidence": (
                f"train={training_manifest.get('train_samples')}; "
                f"validation={training_manifest.get('validation_samples')}; "
                f"test={len(samples)}; exact_fingerprint_overlap={overlap_count}"
            ),
        },
        {
            "gate": "statistically supported search-time reduction",
            "status": "pass"
            if float(selected["time_change_ci_high"]) < 0.0
            and int(selected["run_pareto"]) < int(selected["pairs"])
            else "needs revision",
            "evidence": (
                f"time_change={float(selected['time_change_vs_pareto']):+.6f}; "
                f"ci=[{float(selected['time_change_ci_low']):+.6f},"
                f"{float(selected['time_change_ci_high']):+.6f}]; "
                f"run={selected['run_pareto']}/{selected['pairs']}"
            ),
        },
        {
            "gate": "Pareto quality-gain retention",
            "status": "pass"
            if float(selected["quality_retained_ci_low"]) >= 0.90
            else "needs revision",
            "evidence": (
                f"retained={float(selected['quality_gain_retained']):.6f}; "
                f"ci=[{float(selected['quality_retained_ci_low']):.6f},"
                f"{float(selected['quality_retained_ci_high']):.6f}]"
            ),
        },
        {
            "gate": "non-degrading score advantage over base Resource-NMCTS",
            "status": "pass"
            if int(selected["vs_resource_losses"]) == 0
            and float(selected["mean_relative_vs_resource_score"]) <= -0.03
            else "needs revision",
            "evidence": (
                f"W/L/T={selected['vs_resource_wins']}/{selected['vs_resource_losses']}/"
                f"{selected['vs_resource_ties']}; "
                f"mean_relative={float(selected['mean_relative_vs_resource_score']):+.6f}"
            ),
        },
        {
            "gate": "Pareto tradeoff remains explicit",
            "status": "pass"
            if 0 < int(selected["vs_pareto_losses"]) < int(selected["pairs"])
            and float(selected["score_regret_ci_high"]) <= 0.01
            else "needs revision",
            "evidence": (
                f"W/L/T={selected['vs_pareto_wins']}/{selected['vs_pareto_losses']}/"
                f"{selected['vs_pareto_ties']}; "
                f"regret_ci_high={float(selected['score_regret_ci_high']):.6f}"
            ),
        },
        {
            "gate": "multi-resource reporting",
            "status": "pass"
            if all(f"mean_policy_{metric}" in selected for metric in RESOURCE_METRICS)
            else "needs revision",
            "evidence": f"metrics={RESOURCE_METRICS}",
        },
        {
            "gate": "per-instance policy decisions",
            "status": "pass"
            if args.decisions is not None and decision_count == len(samples)
            else "needs revision",
            "evidence": f"decision_rows={decision_count}; expected={len(samples)}",
        },
    ]
    status_counts = {
        status: sum(1 for gate in gates if gate["status"] == status)
        for status in sorted({str(gate["status"]) for gate in gates})
    }
    manifest = {
        "script": Path(__file__).name,
        "status": "complete" if status_counts.get("needs revision", 0) == 0 else "needs revision",
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "gates": gates,
        "model": display_path(args.model),
        "model_sha256": sha256(args.model),
        "csvs": [display_path(path) for path in paths],
        "training_manifest": display_path(args.training_manifest),
        "exact_fingerprint_overlap": overlap_count,
        "csv_sha256": {display_path(path): sha256(path) for path in paths},
        "pairs": len(samples),
        "thresholds": [row["threshold"] for row in rows],
        "selected_operating_point": selected,
        "outputs": {
            "summary": display_path(args.summary),
            "analysis": display_path(args.analysis),
            "manifest": display_path(args.manifest),
            "decisions": display_path(args.decisions) if args.decisions else None,
            "latex": display_path(args.latex) if args.latex else None,
        },
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} MCTS budget-policy operating points")
    return 1 if status_counts.get("needs revision", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
