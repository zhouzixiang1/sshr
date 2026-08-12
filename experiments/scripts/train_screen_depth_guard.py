#!/usr/bin/env python3
"""Train a conservative guard for skipping depth-2 Boolean-ring screening.

The depth policy predicts one of {single, depth-1, depth-2}.  That is useful
for showing structure learning, but it can lose score against a fixed depth-2
screen.  This guard asks a narrower question: after seeing structural features
of a high-dimensional ANF term set, can we safely use depth-1 instead of
depth-2?  The validation threshold is chosen under a zero-false-skip constraint,
so a predicted skip is only accepted when the model is sufficiently confident.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import argparse
import csv
import json
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch import nn

from src.factor_plan import SearchConfig
from src.neural_policy import default_device
from src.resource_model import ResourceWeights
from train_screen_depth_policy import FEATURE_NAMES, Example, make_examples, split_arg


THIS_DIR = Path(__file__).resolve().parent
SHALLOW_FEATURE_NAMES = [
    "single_score",
    "depth1_score",
    "depth1_vs_single_score_pct",
    "depth1_vs_single_T_pct",
    "depth1_vs_single_CNOT_pct",
    "depth1_vs_single_depth_pct",
    "single_T_per_term",
    "depth1_T_per_term",
    "single_CNOT_per_term",
    "depth1_CNOT_per_term",
    "single_depth_per_term",
    "depth1_depth_per_term",
    "single_peak_ancilla",
    "depth1_peak_ancilla",
    "depth1_time_s",
    "single_time_s",
    "shallow_time_s",
    "depth1_time_over_single",
]


class Depth2GuardNet(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 96) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Dropout(p=0.05),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


@dataclass(frozen=True)
class GuardStats:
    split: str
    pairs: int
    skips: int
    true_skips: int
    false_skips: int
    score_wins: int
    score_losses: int
    score_ties: int
    mean_rel_score_vs_depth2: float
    mean_rel_time_vs_depth2: float
    mean_rel_time_vs_all_depth: float


def safe_skip_label(ex: Example, eps: float) -> int:
    """Return 1 when depth-1 has the same resource score as depth-2."""
    return int(ex.evals[1].score <= ex.evals[2].score + eps)


def _pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def guard_feature_names(mode: str) -> list[str]:
    if mode == "static":
        return list(FEATURE_NAMES)
    if mode == "shallow":
        return [*FEATURE_NAMES, *SHALLOW_FEATURE_NAMES]
    raise ValueError(f"unknown feature mode: {mode}")


def guard_features(ex: Example, mode: str) -> list[float]:
    if mode == "static":
        return list(ex.features)
    if mode != "shallow":
        raise ValueError(f"unknown feature mode: {mode}")

    single = ex.evals[0]
    depth1 = ex.evals[1]
    term_count = max(len(ex.terms), 1)
    shallow = [
        single.score,
        depth1.score,
        _pct(depth1.score, single.score),
        _pct(float(depth1.t_count), float(single.t_count)),
        _pct(float(depth1.cnot), float(single.cnot)),
        _pct(float(depth1.depth_cost), float(single.depth_cost)),
        single.t_count / term_count,
        depth1.t_count / term_count,
        single.cnot / term_count,
        depth1.cnot / term_count,
        single.depth_cost / term_count,
        depth1.depth_cost / term_count,
        float(single.peak_ancilla),
        float(depth1.peak_ancilla),
        depth1.time_s,
        single.time_s,
        single.time_s + depth1.time_s,
        depth1.time_s / max(single.time_s, 1e-9),
    ]
    return [*ex.features, *shallow]


def _standardize(
    train: Sequence[Example],
    other: Sequence[Example],
    feature_mode: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    x_train = torch.tensor([guard_features(ex, feature_mode) for ex in train], dtype=torch.float32)
    x_other = torch.tensor([guard_features(ex, feature_mode) for ex in other], dtype=torch.float32)
    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    return (x_train - mean) / std, (x_other - mean) / std, mean, std


def train_guard(
    train: list[Example],
    valid: list[Example],
    seed: int,
    hidden: int,
    epochs: int,
    eps: float,
    feature_mode: str,
) -> tuple[Depth2GuardNet, torch.Tensor, torch.Tensor, dict[str, float]]:
    x_train, x_valid, mean, std = _standardize(train, valid, feature_mode)
    y_train = torch.tensor([safe_skip_label(ex, eps) for ex in train], dtype=torch.float32)
    y_valid = torch.tensor([safe_skip_label(ex, eps) for ex in valid], dtype=torch.float32)

    positive = y_train.sum().item()
    negative = max(float(len(y_train)) - positive, 1.0)
    pos_weight = torch.tensor([negative / max(positive, 1.0)], dtype=torch.float32)

    torch.manual_seed(seed)
    device = default_device()
    feature_names = guard_feature_names(feature_mode)
    model = Depth2GuardNet(len(feature_names), hidden=hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))

    x_train_d = x_train.to(device)
    y_train_d = y_train.to(device)
    x_valid_d = x_valid.to(device)
    y_valid_d = y_valid.to(device)

    best_state = None
    best_valid = float("inf")
    best_acc = 0.0
    for epoch in range(epochs):
        model.train()
        logits = model(x_train_d)
        loss = loss_fn(logits, y_train_d)
        opt.zero_grad()
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            valid_logits = model(x_valid_d)
            valid_loss = loss_fn(valid_logits, y_valid_d).item()
            valid_prob = torch.sigmoid(valid_logits)
            valid_pred = (valid_prob >= 0.5).float()
            valid_acc = (valid_pred == y_valid_d).float().mean().item()
        if valid_loss < best_valid:
            best_valid = valid_loss
            best_acc = valid_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 20 == 0:
            print(
                f"epoch={epoch+1} train_loss={loss.item():.4f} "
                f"valid_loss={valid_loss:.4f} valid_acc@0.5={valid_acc:.3f}"
            )

    if best_state is not None:
        model.load_state_dict(best_state)
    model.cpu().eval()
    return model, mean, std, {"valid_loss": best_valid, "valid_acc_at_0_5": best_acc}


@torch.no_grad()
def predict_skip_prob(
    model: Depth2GuardNet,
    mean: torch.Tensor,
    std: torch.Tensor,
    examples: Sequence[Example],
    feature_mode: str,
) -> list[float]:
    if not examples:
        return []
    x = torch.tensor([guard_features(ex, feature_mode) for ex in examples], dtype=torch.float32)
    x = (x - mean) / std
    return [float(v) for v in torch.sigmoid(model(x)).tolist()]


def target_eval_time(ex: Example, skip: bool, execution_mode: str) -> float:
    if execution_mode == "direct":
        return ex.evals[1].time_s if skip else ex.evals[2].time_s
    if execution_mode == "staged":
        return ex.evals[0].time_s + ex.evals[1].time_s + (0.0 if skip else ex.evals[2].time_s)
    raise ValueError(f"unknown execution mode: {execution_mode}")


def eval_guard(
    examples: Sequence[Example],
    probs: Sequence[float],
    threshold: float,
    eps: float,
    split: str,
    execution_mode: str,
) -> GuardStats:
    skips = true_skips = false_skips = wins = losses = ties = 0
    rel_score: list[float] = []
    rel_time_depth2: list[float] = []
    rel_time_all: list[float] = []
    for ex, prob in zip(examples, probs):
        skip = prob >= threshold
        if skip:
            skips += 1
        safe = safe_skip_label(ex, eps) == 1
        if skip and safe:
            true_skips += 1
        if skip and not safe:
            false_skips += 1

        target = ex.evals[1] if skip else ex.evals[2]
        depth2 = ex.evals[2]
        target_time = target_eval_time(ex, skip, execution_mode)
        all_time = ex.evals[0].time_s + ex.evals[1].time_s + ex.evals[2].time_s

        if target.score < depth2.score - 1e-9:
            wins += 1
        elif target.score > depth2.score + 1e-9:
            losses += 1
        else:
            ties += 1
        rel_score.append((target.score - depth2.score) / max(depth2.score, 1.0))
        rel_time_depth2.append((target_time - depth2.time_s) / max(depth2.time_s, 1e-9))
        rel_time_all.append((target_time - all_time) / max(all_time, 1e-9))

    return GuardStats(
        split=split,
        pairs=len(examples),
        skips=skips,
        true_skips=true_skips,
        false_skips=false_skips,
        score_wins=wins,
        score_losses=losses,
        score_ties=ties,
        mean_rel_score_vs_depth2=statistics.mean(rel_score) if rel_score else 0.0,
        mean_rel_time_vs_depth2=statistics.mean(rel_time_depth2) if rel_time_depth2 else 0.0,
        mean_rel_time_vs_all_depth=statistics.mean(rel_time_all) if rel_time_all else 0.0,
    )


def select_threshold(
    train: list[Example],
    valid: list[Example],
    train_prob: list[float],
    valid_prob: list[float],
    eps: float,
    execution_mode: str,
) -> tuple[float, GuardStats, GuardStats]:
    candidates = sorted(set(train_prob + valid_prob + [0.0, 0.5, 1.0]))
    # A value just above a probability is needed to express "skip none above this point".
    candidates.extend([min(1.0, p + 1e-9) for p in candidates])
    candidates = sorted(set(candidates))

    best: tuple[tuple[float, int, int], float, GuardStats, GuardStats] | None = None
    for threshold in candidates:
        train_stats = eval_guard(train, train_prob, threshold, eps, "train", execution_mode)
        valid_stats = eval_guard(valid, valid_prob, threshold, eps, "valid", execution_mode)
        if train_stats.false_skips or valid_stats.false_skips:
            continue
        key = (
            -valid_stats.mean_rel_time_vs_all_depth,
            valid_stats.skips,
            train_stats.skips,
        )
        candidate = (key, threshold, train_stats, valid_stats)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        threshold = 1.0
        return (
            threshold,
            eval_guard(train, train_prob, threshold, eps, "train", execution_mode),
            eval_guard(valid, valid_prob, threshold, eps, "valid", execution_mode),
        )
    return best[1], best[2], best[3]


def write_outputs(
    train: list[Example],
    valid: list[Example],
    test: list[Example],
    probs: dict[str, list[float]],
    stats: dict[str, GuardStats],
    threshold: float,
    model: Depth2GuardNet,
    mean: torch.Tensor,
    std: torch.Tensor,
    metrics: dict[str, float],
    args: argparse.Namespace,
) -> None:
    results_dir = Path(args.results_dir)
    tables_dir = Path(args.tables_dir)
    model_path = Path(args.model_out)
    json_path = Path(args.rule_out)
    results_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "feature_names": guard_feature_names(args.feature_mode),
            "feature_mode": args.feature_mode,
            "hidden": args.hidden,
            "threshold": threshold,
            "min_threshold": args.min_threshold,
            "execution_mode": args.execution_mode,
            "metrics": metrics,
        },
        model_path,
    )
    json_path.write_text(
        json.dumps(
            {
                "kind": "depth2_skip_guard",
                "threshold": threshold,
                "label": "skip_depth2_when_depth1_ties_depth2_score",
                "feature_names": guard_feature_names(args.feature_mode),
                "feature_mode": args.feature_mode,
                "min_threshold": args.min_threshold,
                "execution_mode": args.execution_mode,
                "stats": {name: asdict(value) for name, value in stats.items()},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    raw_path = results_dir / "raw_boolean_screen_depth_guard.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "split",
            "name",
            "n",
            "term_count",
            "safe_skip_label",
            "skip_probability",
            "skip_depth2",
            "target_depth",
            "target_score",
            "depth2_score",
            "single_time_s",
            "depth1_time_s",
            "depth2_time_s",
            "target_time_s",
            "all_depth_time_s",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for split, examples in [("train", train), ("valid", valid), ("test", test)]:
            for ex, prob in zip(examples, probs[split]):
                skip = prob >= threshold
                target = ex.evals[1] if skip else ex.evals[2]
                target_time = target_eval_time(ex, skip, args.execution_mode)
                writer.writerow(
                    {
                        "split": split,
                        "name": ex.name,
                        "n": ex.n,
                        "term_count": len(ex.terms),
                        "safe_skip_label": safe_skip_label(ex, args.score_eps),
                        "skip_probability": prob,
                        "skip_depth2": int(skip),
                        "target_depth": 1 if skip else 2,
                        "target_score": target.score,
                        "depth2_score": ex.evals[2].score,
                        "single_time_s": ex.evals[0].time_s,
                        "depth1_time_s": ex.evals[1].time_s,
                        "depth2_time_s": ex.evals[2].time_s,
                        "target_time_s": target_time,
                        "all_depth_time_s": ex.evals[0].time_s + ex.evals[1].time_s + ex.evals[2].time_s,
                    }
                )

    summary_path = results_dir / "summary_boolean_screen_depth_guard.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "pairs",
                "skips",
                "true_skips",
                "false_skips",
                "score_wins",
                "score_losses",
                "score_ties",
                "mean_rel_score_vs_depth2",
                "mean_rel_time_vs_depth2",
                "mean_rel_time_vs_all_depth",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for split in ["train", "valid", "test"]:
            writer.writerow(asdict(stats[split]))

    analysis_path = results_dir / "analysis_boolean_screen_depth_guard.md"
    with analysis_path.open("w", encoding="utf-8") as f:
        f.write("# Boolean Screen Depth-2 Guard\n\n")
        f.write("Conservative structure-level guard for skipping depth-2 Boolean-ring screening.\n\n")
        f.write(f"- train examples: {len(train)}\n")
        f.write(f"- validation examples: {len(valid)}\n")
        f.write(f"- held-out test examples: {len(test)}\n")
        f.write(f"- train n: {args.train_n}; test n: {args.test_n}\n")
        f.write(f"- feature mode: {args.feature_mode}\n")
        f.write(f"- execution mode: {args.execution_mode}\n")
        f.write(f"- minimum skip threshold: {args.min_threshold:.6f}\n")
        f.write(f"- selected skip threshold: {threshold:.6f}\n")
        f.write(f"- validation loss at best checkpoint: {metrics['valid_loss']:.4f}\n")
        f.write(f"- validation accuracy at 0.5: {metrics['valid_acc_at_0_5']:.3f}\n\n")
        if args.execution_mode == "direct":
            f.write("The guard uses only static ANF features to dispatch directly to depth-1 when the model predicts that depth-1 ties fixed depth-2 in score; otherwise it runs depth-2 directly.\n\n")
        else:
            f.write("The guard runs shallow screening and uses depth-1 only when the model predicts that depth-1 ties fixed depth-2 in score. Otherwise it falls back to depth-2.\n\n")
        f.write("| split | pairs | skips | false skips | score W/L/T vs depth-2 | mean score vs depth-2 | mean time vs depth-2 | mean time vs all-depth |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for split in ["train", "valid", "test"]:
            s = stats[split]
            f.write(
                f"| {split} | {s.pairs} | {s.skips} | {s.false_skips} | "
                f"{s.score_wins}/{s.score_losses}/{s.score_ties} | "
                f"{s.mean_rel_score_vs_depth2:+.2%} | "
                f"{s.mean_rel_time_vs_depth2:+.2%} | "
                f"{s.mean_rel_time_vs_all_depth:+.2%} |\n"
            )

    table_path = tables_dir / "boolean_screen_depth_guard.tex"
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrrrrrr}\n")
        f.write("\\toprule\n")
        f.write(
            "Split & Pairs & Skips & False skips & Score W/L/T & "
            "Mean $\\Delta$ score & Mean $\\Delta$ time vs D2 & "
            "Mean $\\Delta$ time vs all-depth \\\\\n"
        )
        f.write("\\midrule\n")
        for split in ["train", "valid", "test"]:
            s = stats[split]
            f.write(
                f"{split} & {s.pairs} & {s.skips} & {s.false_skips} & "
                f"{s.score_wins}/{s.score_losses}/{s.score_ties} & "
                f"{s.mean_rel_score_vs_depth2:+.2%} & "
                f"{s.mean_rel_time_vs_depth2:+.2%} & "
                f"{s.mean_rel_time_vs_all_depth:+.2%} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")

    print(f"wrote {model_path}")
    print(f"wrote {json_path}")
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260709)
    ap.add_argument("--train-n", default="14,16,18")
    ap.add_argument("--test-n", default="20")
    ap.add_argument("--train-per-n", type=int, default=160)
    ap.add_argument("--valid-per-n", type=int, default=48)
    ap.add_argument("--test-per-n", type=int, default=96)
    ap.add_argument("--epochs", type=int, default=180)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--gate-mode", choices=["mct", "logical_and"], default="mct")
    ap.add_argument("--score-eps", type=float, default=1e-9)
    ap.add_argument("--feature-mode", choices=["static", "shallow"], default="static")
    ap.add_argument("--execution-mode", choices=["direct", "staged"], default="direct")
    ap.add_argument(
        "--min-threshold",
        type=float,
        default=0.0,
        help="Conservative floor for skip probability after zero-false-skip calibration.",
    )
    ap.add_argument("--model-out", default=str(THIS_DIR / "models" / "boolean_screen_depth_guard.pt"))
    ap.add_argument("--rule-out", default=str(THIS_DIR / "models" / "boolean_screen_depth_guard.json"))
    ap.add_argument("--results-dir", default=str(THIS_DIR / "results"))
    ap.add_argument("--tables-dir", default=str(THIS_DIR / "paper_latex" / "tables"))
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.execution_mode == "direct" and args.feature_mode != "static":
        raise ValueError("direct execution mode requires static features; shallow features are only available after running shallow screens")

    config = SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=4,
        max_factor_size=5,
        candidate_top_k=24,
        gate_mode=args.gate_mode,
    )
    rng = random.Random(args.seed)
    train_ns = split_arg(args.train_n)
    test_ns = split_arg(args.test_n)

    print("building train examples")
    train = make_examples("train", train_ns, args.train_per_n, rng, config, args.action_width)
    print("building validation examples")
    valid = make_examples("valid", train_ns, args.valid_per_n, rng, config, args.action_width)
    print("building held-out test examples")
    test = make_examples("test", test_ns, args.test_per_n, rng, config, args.action_width)

    model, mean, std, metrics = train_guard(
        train,
        valid,
        args.seed,
        args.hidden,
        args.epochs,
        args.score_eps,
        args.feature_mode,
    )
    probs = {
        "train": predict_skip_prob(model, mean, std, train, args.feature_mode),
        "valid": predict_skip_prob(model, mean, std, valid, args.feature_mode),
        "test": predict_skip_prob(model, mean, std, test, args.feature_mode),
    }
    calibrated_threshold, _, _ = select_threshold(
        train,
        valid,
        probs["train"],
        probs["valid"],
        args.score_eps,
        args.execution_mode,
    )
    threshold = max(calibrated_threshold, args.min_threshold)
    stats = {
        "train": eval_guard(train, probs["train"], threshold, args.score_eps, "train", args.execution_mode),
        "valid": eval_guard(valid, probs["valid"], threshold, args.score_eps, "valid", args.execution_mode),
        "test": eval_guard(test, probs["test"], threshold, args.score_eps, "test", args.execution_mode),
    }
    write_outputs(train, valid, test, probs, stats, threshold, model, mean, std, metrics, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
