#!/usr/bin/env python3
"""Train a learned policy for pruning Affine-FPRM phase-search candidates.

The wide Affine-FPRM search evaluates all ``transform_budget * 2**n`` affine
forms for each function.  This script keeps the same logic-layer phase
polynomial model, but trains a small neural scorer from candidate features so a
policy-guided run can exact-score only the top-k predicted candidates.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch import nn

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from affine_search import candidate_transforms, identity_rows, linear_cnot_sequence, transform_function
from anf_utils import anf_monomials, shifted_function
from bool_func import BooleanFunction
from neural_policy import default_device
from run_phase_parity_affine_search import (
    count_angles,
    selection_key,
    stats_to_row,
    translate_affine_shifted_angles,
    verify_phase_truth_up_to_global,
)
from run_phase_parity_baseline import RESULTS, TABLES, load_csv, unique_truth_rows, write_csv
from run_phase_parity_fprm_search import compare_pairs, latex_pct, pct


FEATURE_NAMES = [
    "n_norm",
    "truth_density",
    "orig_terms_norm",
    "orig_max_degree_norm",
    "orig_mean_degree_norm",
    "orig_high_degree_frac",
    "transform_index_norm",
    "transform_random_region",
    "transform_weight_norm",
    "transform_mean_row_weight_norm",
    "transform_max_row_weight_norm",
    "transform_cnot_norm",
    "polarity_weight_norm",
    "shifted_terms_norm",
    "shifted_max_degree_norm",
    "shifted_mean_degree_norm",
    "shifted_high_degree_frac",
    "shifted_has_constant",
]


TARGET_METRIC = "score_synth_tperrz30"
RANK_METHOD = "phase_parity_affine_policy_tperrz30"


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    split: str
    n: int
    truth_table_hex: str
    transform_index: int
    transform_rows: tuple[int, ...]
    polarity: int
    features: tuple[float, ...]
    T: int
    CNOT: int
    depth: int
    gates: int
    score: float
    score_rz1: float
    score_synth_tperrz30: float
    rz_total: int
    rz_clifford: int
    rz_t_like: int
    rz_non_clifford: int
    rz_max_denominator: int
    parity_gadgets: int
    anf_terms: int
    shifted_constant_term: int
    global_phase_pi: str


class PhasePolicyNet(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 96) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def degree_stats(terms: Iterable[int], n: int) -> tuple[int, int, float, float]:
    degrees = [int(term).bit_count() for term in terms]
    if not degrees:
        return 0, 0, 0.0, 0.0
    return (
        len(degrees),
        max(degrees),
        statistics.mean(degrees),
        sum(1 for degree in degrees if degree >= 3) / max(1, len(degrees)),
    )


def transform_features(rows: Sequence[int], index: int, budget: int, n: int) -> tuple[float, ...]:
    weights = [int(row).bit_count() for row in rows]
    deterministic_prefix = 1 + n + n * (n - 1)
    try:
        cnot_cost = len(linear_cnot_sequence(rows))
    except ValueError:
        cnot_cost = n * n
    return (
        index / max(1, budget - 1),
        1.0 if index >= deterministic_prefix else 0.0,
        sum(weights) / max(1, n * n),
        statistics.mean(weights) / max(1, n),
        max(weights) / max(1, n),
        cnot_cost / max(1, n * n),
    )


def candidate_key(candidate: Candidate, metric: str = TARGET_METRIC) -> tuple[float, ...]:
    row = {
        "score": candidate.score,
        "score_rz1": candidate.score_rz1,
        "score_synth_tperrz30": candidate.score_synth_tperrz30,
        "rz_non_clifford": candidate.rz_non_clifford,
        "rz_total": candidate.rz_total,
        "CNOT": candidate.CNOT,
        "depth": candidate.depth,
        "transform_nonidentity": int(candidate.transform_rows != identity_rows(candidate.n)),
        "polarity_weight": int(candidate.polarity).bit_count(),
        "transform_index": candidate.transform_index,
        "polarity": candidate.polarity,
    }
    return selection_key(row, metric)


def make_candidate_row(
    candidate: Candidate,
    method: str,
    exact_eval_forms: int,
    candidate_affine_forms: int,
    prediction_rank: int | None = None,
) -> dict[str, object]:
    rows = candidate.transform_rows
    n = candidate.n
    truth = int(candidate.truth_table_hex, 16)
    bf = BooleanFunction(n, truth)
    transformed = transform_function(bf, rows)
    shifted = shifted_function(transformed, candidate.polarity)
    terms = anf_monomials(shifted)
    shifted_constant, global_phase, angles = translate_affine_shifted_angles(terms, rows, candidate.polarity)
    verified = verify_phase_truth_up_to_global(n, truth, global_phase, angles)
    stats_like = type(
        "StatsLike",
        (),
        {
            "name": candidate.name,
            "n": n,
            "truth_table_hex": candidate.truth_table_hex,
            "method": method,
            "rank_metric": TARGET_METRIC,
            "transform_index": candidate.transform_index,
            "transform_rows": rows,
            "polarity": candidate.polarity,
            "candidate_transforms": candidate_affine_forms // (1 << n),
            "candidate_polarities": 1 << n,
            "candidate_affine_forms": candidate_affine_forms,
            "anf_terms": len(terms),
            "shifted_constant_term": shifted_constant,
            "global_phase_pi": global_phase,
            "parity_gadgets": candidate.parity_gadgets,
            "rz_total": candidate.rz_total,
            "rz_clifford": candidate.rz_clifford,
            "rz_t_like": candidate.rz_t_like,
            "rz_non_clifford": candidate.rz_non_clifford,
            "rz_max_denominator": candidate.rz_max_denominator,
            "T": candidate.T,
            "CNOT": candidate.CNOT,
            "gates": candidate.gates,
            "depth": candidate.depth,
            "explicit_ancilla": 0,
            "peak_ancilla": 0,
            "score": candidate.score,
            "verified_up_to_global_phase": verified,
            "time_s": 0.0,
        },
    )()
    row = stats_to_row(stats_like)
    row["split"] = candidate.split
    row["exact_eval_forms"] = exact_eval_forms
    row["prediction_rank"] = "" if prediction_rank is None else prediction_rank
    row["policy_target_metric"] = TARGET_METRIC
    return row


def build_group(task: tuple[dict[str, str], str, int, int]) -> list[Candidate]:
    row, split, seed, transform_budget = task
    n = int(row["n"])
    truth = int(row["truth_table_hex"], 16)
    bf = BooleanFunction(n, truth)
    transforms = candidate_transforms(n, seed + n * 10_000, transform_budget)
    original_terms = anf_monomials(bf)
    orig_count, orig_max, orig_mean, orig_high = degree_stats(original_terms, n)
    truth_density = truth.bit_count() / max(1, 1 << n)
    base_features = (
        n / 10.0,
        truth_density,
        orig_count / max(1, 1 << n),
        orig_max / max(1, n),
        orig_mean / max(1, n),
        orig_high,
    )
    candidates: list[Candidate] = []
    for transform_index, transform in enumerate(transforms):
        transformed = transform_function(bf, transform.rows)
        t_features = transform_features(transform.rows, transform_index, transform_budget, n)
        for polarity in range(1 << n):
            shifted = shifted_function(transformed, polarity)
            terms = anf_monomials(shifted)
            shifted_count, shifted_max, shifted_mean, shifted_high = degree_stats(terms, n)
            shifted_constant, global_phase, angles = translate_affine_shifted_angles(
                terms, transform.rows, polarity
            )
            counts = count_angles(angles)
            features = base_features + t_features + (
                int(polarity).bit_count() / max(1, n),
                shifted_count / max(1, 1 << n),
                shifted_max / max(1, n),
                shifted_mean / max(1, n),
                shifted_high,
                1.0 if 0 in terms else 0.0,
            )
            candidates.append(
                Candidate(
                    name=row["name"],
                    split=split,
                    n=n,
                    truth_table_hex=row["truth_table_hex"],
                    transform_index=transform_index,
                    transform_rows=tuple(transform.rows),
                    polarity=polarity,
                    features=tuple(float(value) for value in features),
                    T=int(counts["T"]),
                    CNOT=int(counts["CNOT"]),
                    depth=int(counts["depth"]),
                    gates=int(counts["gates"]),
                    score=float(counts["score"]),
                    score_rz1=float(counts["score"]) + float(counts["rz_non_clifford"]),
                    score_synth_tperrz30=float(counts["score"]) + 30.0 * float(counts["rz_non_clifford"]),
                    rz_total=int(counts["rz_total"]),
                    rz_clifford=int(counts["rz_clifford"]),
                    rz_t_like=int(counts["rz_t_like"]),
                    rz_non_clifford=int(counts["rz_non_clifford"]),
                    rz_max_denominator=int(counts["rz_max_denominator"]),
                    parity_gadgets=int(counts["parity_gadgets"]),
                    anf_terms=len(terms),
                    shifted_constant_term=shifted_constant,
                    global_phase_pi=f"{global_phase.numerator}/{global_phase.denominator}",
                )
            )
    return candidates


def split_rows(rows: list[dict[str, str]], seed: int) -> dict[str, list[dict[str, str]]]:
    rng = random.Random(seed)
    train_valid = [row for row in rows if int(row["n"]) <= 5]
    test = [row for row in rows if int(row["n"]) == 6]
    rng.shuffle(train_valid)
    valid_count = max(1, round(0.18 * len(train_valid)))
    valid = sorted(train_valid[:valid_count], key=lambda row: (int(row["n"]), row["name"]))
    train = sorted(train_valid[valid_count:], key=lambda row: (int(row["n"]), row["name"]))
    return {"train": train, "valid": valid, "test_n6": sorted(test, key=lambda row: row["name"])}


def build_all_groups(
    splits: dict[str, list[dict[str, str]]],
    seed: int,
    transform_budget: int,
    workers: int,
) -> dict[str, list[list[Candidate]]]:
    tasks: list[tuple[dict[str, str], str, int, int]] = []
    for split, rows in splits.items():
        for row in rows:
            tasks.append((row, split, seed, transform_budget))
    groups_by_split: dict[str, list[list[Candidate]]] = {split: [] for split in splits}
    if workers <= 1:
        for idx, task in enumerate(tasks, 1):
            group = build_group(task)
            groups_by_split[task[1]].append(group)
            if idx % 10 == 0:
                print(f"built {idx}/{len(tasks)} candidate groups", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_split = {executor.submit(build_group, task): task[1] for task in tasks}
            for idx, future in enumerate(as_completed(future_to_split), 1):
                split = future_to_split[future]
                groups_by_split[split].append(future.result())
                if idx % 10 == 0:
                    print(f"built {idx}/{len(tasks)} candidate groups", flush=True)
    for split in groups_by_split:
        groups_by_split[split].sort(key=lambda group: group[0].name if group else "")
    return groups_by_split


def group_labels(groups: list[list[Candidate]]) -> tuple[torch.Tensor, torch.Tensor]:
    features: list[tuple[float, ...]] = []
    labels: list[float] = []
    for group in groups:
        values = [candidate.score_synth_tperrz30 for candidate in group]
        mean = statistics.mean(values)
        stdev = statistics.pstdev(values)
        if stdev <= 1e-9:
            rewards = [0.0 for _ in values]
        else:
            rewards = [max(-5.0, min(5.0, (mean - value) / stdev)) for value in values]
        for candidate, reward in zip(group, rewards):
            features.append(candidate.features)
            labels.append(reward)
    return torch.tensor(features, dtype=torch.float32), torch.tensor(labels, dtype=torch.float32)


def train_model(
    train_groups: list[list[Candidate]],
    valid_groups: list[list[Candidate]],
    seed: int,
    hidden: int,
    epochs: int,
    batch_size: int,
) -> tuple[PhasePolicyNet, torch.Tensor, torch.Tensor, dict[str, float]]:
    x_train, y_train = group_labels(train_groups)
    x_valid, y_valid = group_labels(valid_groups)
    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    x_train = (x_train - mean) / std
    x_valid = (x_valid - mean) / std

    torch.manual_seed(seed)
    device = default_device()
    model = PhasePolicyNet(len(FEATURE_NAMES), hidden=hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    best_state = None
    best_valid = float("inf")
    best_train = float("inf")

    x_train_d = x_train.to(device)
    y_train_d = y_train.to(device)
    x_valid_d = x_valid.to(device)
    y_valid_d = y_valid.to(device)
    gen = torch.Generator(device="cpu")
    gen.manual_seed(seed)

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(x_train.shape[0], generator=gen)
        train_losses: list[float] = []
        for start in range(0, x_train.shape[0], batch_size):
            idx = perm[start : start + batch_size].to(device)
            pred = model(x_train_d.index_select(0, idx))
            loss = loss_fn(pred, y_train_d.index_select(0, idx))
            opt.zero_grad()
            loss.backward()
            opt.step()
            train_losses.append(float(loss.detach().cpu()))
        model.eval()
        with torch.no_grad():
            valid_loss = float(loss_fn(model(x_valid_d), y_valid_d).detach().cpu())
        if valid_loss < best_valid:
            best_valid = valid_loss
            best_train = statistics.mean(train_losses)
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 10 == 0:
            print(
                f"epoch {epoch + 1:03d}/{epochs} train_mse={statistics.mean(train_losses):.4f} "
                f"valid_mse={valid_loss:.4f}",
                flush=True,
            )

    if best_state is not None:
        model.load_state_dict(best_state)
    return model.cpu(), mean, std, {"train_mse": best_train, "valid_mse": best_valid}


@torch.no_grad()
def predict_group(
    model: PhasePolicyNet,
    mean: torch.Tensor,
    std: torch.Tensor,
    group: list[Candidate],
) -> list[tuple[float, Candidate]]:
    model.eval()
    x = torch.tensor([candidate.features for candidate in group], dtype=torch.float32)
    x = (x - mean) / std
    pred = model(x).detach().cpu().tolist()
    return list(zip(pred, group))


def select_methods_for_group(
    group: list[Candidate],
    predictions: list[tuple[float, Candidate]],
    topks: Sequence[int],
    rng: random.Random,
    transform_budget: int,
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    candidate_affine_forms = len(group)
    prefix32 = [candidate for candidate in group if candidate.transform_index < 32]
    prefix16 = [candidate for candidate in group if candidate.transform_index < 16]
    wide = group
    ranked_predictions = sorted(predictions, key=lambda item: (-item[0], candidate_key(item[1])))

    baselines = [
        ("phase_affine_prefix16_tperrz30", prefix16, len(prefix16), None),
        ("phase_affine_budget32_tperrz30", prefix32, len(prefix32), None),
        ("phase_affine_wide128_tperrz30", wide, candidate_affine_forms, None),
    ]
    for method, pool, exact_eval_forms, prediction_rank in baselines:
        best = min(pool, key=candidate_key)
        selected.append(make_candidate_row(best, method, exact_eval_forms, candidate_affine_forms, prediction_rank))

    for topk in topks:
        pool = [candidate for _, candidate in ranked_predictions[: min(topk, len(ranked_predictions))]]
        best = min(pool, key=candidate_key)
        prediction_rank = next(i for i, (_, candidate) in enumerate(ranked_predictions, 1) if candidate is best)
        selected.append(
            make_candidate_row(
                best,
                f"{RANK_METHOD}_top{topk}",
                min(topk, candidate_affine_forms),
                candidate_affine_forms,
                prediction_rank,
            )
        )

    for topk in topks:
        pool = rng.sample(group, min(topk, len(group)))
        best = min(pool, key=candidate_key)
        selected.append(
            make_candidate_row(
                best,
                f"phase_affine_random_top{topk}",
                min(topk, candidate_affine_forms),
                candidate_affine_forms,
                None,
            )
        )
    return selected


def compare_method_rows(
    rows: list[dict[str, object]],
    split: str,
    target_method: str,
    baseline_method: str,
    metric: str,
) -> dict[str, object] | None:
    target = {
        str(row["name"]): row
        for row in rows
        if row.get("split") == split and row.get("method") == target_method and not row.get("error")
    }
    baseline = {
        str(row["name"]): row
        for row in rows
        if row.get("split") == split and row.get("method") == baseline_method and not row.get("error")
    }
    pairs = []
    for name, target_row in target.items():
        base = baseline.get(name)
        if base is None:
            continue
        pairs.append((float(target_row[metric]), float(base[metric])))
    if not pairs:
        return None
    return {
        "split": split,
        "target": target_method,
        "baseline": baseline_method,
        "metric": metric,
        **compare_pairs(pairs),
    }


def build_summary(rows: list[dict[str, object]], topks: Sequence[int]) -> list[dict[str, object]]:
    methods = [
        "phase_affine_prefix16_tperrz30",
        *(f"{RANK_METHOD}_top{topk}" for topk in topks),
        *(f"phase_affine_random_top{topk}" for topk in topks),
    ]
    baselines = [
        "phase_affine_budget32_tperrz30",
        "phase_affine_wide128_tperrz30",
        *(f"phase_affine_random_top{topk}" for topk in topks),
    ]
    metrics = [TARGET_METRIC, "score", "score_rz1", "rz_non_clifford", "rz_total", "CNOT", "depth"]
    summary: list[dict[str, object]] = []
    for split in sorted({str(row["split"]) for row in rows}):
        for method in methods:
            for baseline in baselines:
                if method == baseline:
                    continue
                for metric in metrics:
                    row = compare_method_rows(rows, split, method, baseline, metric)
                    if row is not None:
                        summary.append(row)
    return summary


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["split", "target", "baseline", "metric", "items", "wins", "losses", "ties", "mean_relative"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summary_lookup(
    rows: list[dict[str, object]], split: str, target: str, baseline: str, metric: str
) -> dict[str, object] | None:
    for row in rows:
        if row["split"] == split and row["target"] == target and row["baseline"] == baseline and row["metric"] == metric:
            return row
    return None


def write_latex(path: Path, summary: list[dict[str, object]], best_topk: int) -> None:
    focus = [
        (f"{RANK_METHOD}_top{best_topk}", "phase_affine_budget32_tperrz30", TARGET_METRIC, rf"Policy top-{best_topk} vs budget-32"),
        (f"{RANK_METHOD}_top{best_topk}", "phase_affine_wide128_tperrz30", TARGET_METRIC, rf"Policy top-{best_topk} vs wide-128"),
        (f"{RANK_METHOD}_top64", "phase_affine_random_top64", TARGET_METRIC, r"Policy top-64 vs random top-64"),
        (f"{RANK_METHOD}_top128", "phase_affine_random_top128", TARGET_METRIC, r"Policy top-128 vs random top-128"),
        (f"{RANK_METHOD}_top{best_topk}", "phase_affine_budget32_tperrz30", "rz_total", rf"Policy top-{best_topk} total Rz vs budget-32"),
        (f"{RANK_METHOD}_top{best_topk}", "phase_affine_budget32_tperrz30", "CNOT", rf"Policy top-{best_topk} CNOT vs budget-32"),
        (f"{RANK_METHOD}_top{best_topk}", "phase_affine_budget32_tperrz30", "depth", rf"Policy top-{best_topk} depth vs budget-32"),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for target, baseline, metric, label in focus:
            row = summary_lookup(summary, "test_n6", target, baseline, metric)
            if row is None:
                continue
            wlt = f"{row['wins']}/{row['losses']}/{row['ties']}"
            f.write(f"{label} & {row['items']} & {wlt} & {latex_pct(float(row['mean_relative']))} \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def method_mean(rows: list[dict[str, object]], split: str, method: str, metric: str) -> float:
    values = [
        float(row[metric])
        for row in rows
        if row.get("split") == split and row.get("method") == method and not row.get("error")
    ]
    return statistics.mean(values) if values else math.nan


def write_analysis(
    path: Path,
    selected_rows: list[dict[str, object]],
    summary: list[dict[str, object]],
    split_sizes: dict[str, int],
    model_stats: dict[str, float],
    topks: Sequence[int],
    best_topk: int,
    transform_budget: int,
    started: float,
) -> None:
    lines = [
        "# Learned Phase Affine Policy",
        "",
        "This experiment trains a neural scorer over Affine-FPRM phase-search candidates.",
        "Training uses n<=5 functions; the paper-facing test split is held-out n=6.",
        "The policy ranks all affine/polarity candidates from cheap structural features and exact-scores only a top-k shortlist.",
        "",
        f"- transform budget: {transform_budget}",
        f"- target metric: {TARGET_METRIC}",
        f"- train functions: {split_sizes['train']}",
        f"- valid functions: {split_sizes['valid']}",
        f"- held-out n=6 test functions: {split_sizes['test_n6']}",
        f"- train MSE: {model_stats['train_mse']:.4f}",
        f"- valid MSE: {model_stats['valid_mse']:.4f}",
        f"- elapsed seconds: {time.time() - started:.2f}",
        "",
        "## Held-out n=6 comparison",
        "",
        "| method | exact forms/function | mean target | vs budget-32 W/L/T | vs budget-32 mean relative | vs wide-128 W/L/T | vs wide-128 mean relative |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    methods = [
        "phase_affine_prefix16_tperrz30",
        *(f"{RANK_METHOD}_top{topk}" for topk in topks),
        *(f"phase_affine_random_top{topk}" for topk in topks),
        "phase_affine_budget32_tperrz30",
        "phase_affine_wide128_tperrz30",
    ]
    for method in methods:
        mean_target = method_mean(selected_rows, "test_n6", method, TARGET_METRIC)
        sample = next(
            (
                row
                for row in selected_rows
                if row.get("split") == "test_n6" and row.get("method") == method
            ),
            None,
        )
        exact_forms = "" if sample is None else str(sample["exact_eval_forms"])
        vs32 = summary_lookup(summary, "test_n6", method, "phase_affine_budget32_tperrz30", TARGET_METRIC)
        vswide = summary_lookup(summary, "test_n6", method, "phase_affine_wide128_tperrz30", TARGET_METRIC)
        if method == "phase_affine_budget32_tperrz30":
            vs32_text = "-"
            vs32_rel = "-"
        else:
            vs32_text = "-" if vs32 is None else f"{vs32['wins']}/{vs32['losses']}/{vs32['ties']}"
            vs32_rel = "-" if vs32 is None else pct(float(vs32["mean_relative"]))
        if method == "phase_affine_wide128_tperrz30":
            vswide_text = "-"
            vswide_rel = "-"
        else:
            vswide_text = "-" if vswide is None else f"{vswide['wins']}/{vswide['losses']}/{vswide['ties']}"
            vswide_rel = "-" if vswide is None else pct(float(vswide["mean_relative"]))
        lines.append(
            f"| {method} | {exact_forms} | {mean_target:.2f} | {vs32_text} | {vs32_rel} | {vswide_text} | {vswide_rel} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A positive row against budget-32 means the learned scorer found useful candidates outside the deterministic budget-32 prefix while exact-scoring fewer affine forms.",
            "- Same-budget random shortlists are intentionally included because this candidate space is dense; the current neural policy is best read as a pruned-search feasibility result, not as a decisive learned-vs-random win.",
            "- A small gap against wide-128 is expected because wide-128 is the exhaustive oracle over the same transform budget.",
            "- This remains a logic-layer phase-polynomial search result; it does not synthesize approximate rotations or include hardware mapping.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_model(path: Path, model: PhasePolicyNet, mean: torch.Tensor, std: torch.Tensor, stats: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "feature_names": FEATURE_NAMES,
            "target_metric": TARGET_METRIC,
            "hidden": model.net[0].out_features if isinstance(model.net[0], nn.Linear) else 96,
            "stats": stats,
        },
        path,
    )


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    selected_rows: list[dict[str, object]],
    split_sizes: dict[str, int],
    model_stats: dict[str, float],
    started: float,
) -> None:
    payload = {
        "input": str(args.input),
        "raw_out": str(args.raw_out),
        "summary": str(args.summary),
        "analysis": str(args.analysis),
        "latex_out": str(args.latex_out),
        "model_out": str(args.model_out),
        "seed": args.seed,
        "transform_budget": args.transform_budget,
        "topk": args.topk,
        "random_topk": args.topk,
        "split_sizes": split_sizes,
        "model_stats": model_stats,
        "rows": len(selected_rows),
        "verified_rows": sum(1 for row in selected_rows if str(row.get("verified_up_to_global_phase")) == "True"),
        "elapsed_s": time.time() - started,
        "claim_boundary": "Learned candidate pruning for logic-layer Affine-FPRM phase-polynomial search; not rotation sequence synthesis or hardware mapping.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_topk(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--seed", type=int, default=20260709)
    parser.add_argument("--transform-budget", type=int, default=128)
    parser.add_argument("--topk", default="64,128,256,512")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--hidden", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_phase_affine_policy.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_phase_affine_policy.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_phase_affine_policy.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "phase_affine_policy.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_phase_affine_policy.json")
    parser.add_argument("--model-out", type=Path, default=THIS_DIR / "models" / "phase_affine_policy_tperrz30.pt")
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    topks = parse_topk(args.topk)
    rows = unique_truth_rows(args.input, 6)
    splits = split_rows(rows, args.seed)
    split_sizes = {split: len(split_rows_) for split, split_rows_ in splits.items()}
    groups_by_split = build_all_groups(splits, args.seed, args.transform_budget, args.workers)
    model, mean, std, model_stats = train_model(
        groups_by_split["train"],
        groups_by_split["valid"],
        args.seed,
        args.hidden,
        args.epochs,
        args.batch_size,
    )
    save_model(args.model_out, model, mean, std, model_stats)

    rng = random.Random(args.seed + 991)
    selected_rows: list[dict[str, object]] = []
    for split, groups in groups_by_split.items():
        for group in groups:
            predictions = predict_group(model, mean, std, group)
            selected_rows.extend(
                select_methods_for_group(
                    group,
                    predictions,
                    topks,
                    rng,
                    args.transform_budget,
                )
            )
    write_csv(args.raw_out, selected_rows)
    summary = build_summary(selected_rows, topks)
    write_summary_csv(args.summary, summary)
    best_topk = max(topks)
    write_latex(args.latex_out, summary, best_topk)
    write_analysis(
        args.analysis,
        selected_rows,
        summary,
        split_sizes,
        model_stats,
        topks,
        best_topk,
        args.transform_budget,
        started,
    )
    write_manifest(args.manifest, args, selected_rows, split_sizes, model_stats, started)
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.manifest}")
    print(f"wrote {args.model_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
