#!/usr/bin/env python3
"""Train a contextual-bandit policy for allocating Pareto-MCTS effort.

The policy observes structural and Resource-NMCTS result features, then chooses
between stopping and running the more expensive Pareto-Resource-NMCTS search.
Because both logged action outcomes are available during training, the script
supports either exact-expectation policy gradient or fitted-Q return regression;
the canonical artifact uses the fitted-Q objective.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch
from torch import nn

from anf_utils import anf_monomials
from bool_func import BooleanFunction


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_TRAIN = RESULTS / "raw_search_ablation_traditional.csv"
DEFAULT_TRAIN_SEED43 = RESULTS / "raw_mcts_budget_policy_train_seed43.csv"
DEFAULT_VALIDATION = RESULTS / "raw_mcts_budget_policy_validation_seed44.csv"
DEFAULT_OUTPUT = THIS_DIR / "models" / "mcts_budget_policy.pt"
DEFAULT_MANIFEST = RESULTS / "manifest_mcts_budget_policy_training.json"

RESOURCE_METHOD = "and_resource_nmcts"
PARETO_METHOD = "and_pareto_resource_nmcts"
FEATURE_NAMES = [
    "n",
    "anf_terms",
    "onset_density",
    "mean_anf_degree",
    "max_anf_degree",
    "nonlinear_terms",
    "degree3plus_terms",
    "resource_score",
    "resource_T",
    "resource_CNOT",
    "resource_depth",
    "resource_gates",
    "resource_peak_ancilla",
    "resource_terms",
]
RESOURCE_METRICS = ["score", "T", "CNOT", "depth", "gates", "peak_ancilla"]


@dataclass(frozen=True)
class BudgetSample:
    name: str
    fingerprint: tuple[int, int]
    features: list[float]
    resource_score: float
    pareto_score: float
    resource_time_s: float
    pareto_time_s: float
    resource_metrics: dict[str, float]
    pareto_metrics: dict[str, float]


class BudgetPolicy(nn.Module):
    def __init__(self, feature_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feature_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Linear(hidden // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def display_path(path: Path) -> str:
    """Use portable repository-relative paths in public manifests."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(THIS_DIR.resolve()))
    except ValueError:
        return str(resolved)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def usable(row: dict[str, str]) -> bool:
    return (
        not row.get("error")
        and not row.get("skipped")
        and str(row.get("correct")) == "True"
    )


def row_features(row: dict[str, str]) -> list[float]:
    n = int(row["n"])
    truth_table = int(row["truth_table_hex"], 16)
    terms = anf_monomials(BooleanFunction(n, truth_table))
    degrees = [int(term).bit_count() for term in terms] or [0]
    return [
        float(n),
        float(len(terms)),
        truth_table.bit_count() / float(1 << n),
        statistics.mean(degrees),
        float(max(degrees)),
        float(sum(degree >= 2 for degree in degrees)),
        float(sum(degree >= 3 for degree in degrees)),
        float(row["score"]),
        float(row["T"]),
        float(row["CNOT"]),
        float(row["depth"]),
        float(row["gates"]),
        float(row["peak_ancilla"]),
        float(row["terms"]),
    ]


def load_samples(paths: list[Path], random_truth_only: bool) -> list[BudgetSample]:
    samples: list[BudgetSample] = []
    seen: set[tuple[str, str]] = set()
    for path in paths:
        rows = [row for row in read_csv(path) if usable(row)]
        by_key = {(row["method"], row["name"]): row for row in rows}
        source = str(path.resolve())
        for (method, name), resource in sorted(by_key.items()):
            if method != RESOURCE_METHOD:
                continue
            if random_truth_only and not name.startswith("truth_"):
                continue
            pareto = by_key.get((PARETO_METHOD, name))
            if pareto is None:
                continue
            key = (source, name)
            if key in seen:
                continue
            seen.add(key)
            samples.append(
                BudgetSample(
                    name=f"{path.stem}:{name}",
                    fingerprint=(int(resource["n"]), int(resource["truth_table_hex"], 16)),
                    features=row_features(resource),
                    resource_score=float(resource["score"]),
                    pareto_score=float(pareto["score"]),
                    resource_time_s=float(resource["time_s"]),
                    pareto_time_s=float(pareto["time_s"]),
                    resource_metrics={
                        metric: float(resource[metric]) for metric in RESOURCE_METRICS
                    },
                    pareto_metrics={
                        metric: float(pareto[metric]) for metric in RESOURCE_METRICS
                    },
                )
            )
    if not samples:
        raise RuntimeError("no matched Resource/Pareto samples")
    return samples


def tensors(samples: list[BudgetSample]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    x = torch.tensor([sample.features for sample in samples], dtype=torch.float32)
    score_gain = torch.tensor(
        [
            (sample.resource_score - sample.pareto_score) / max(sample.resource_score, 1.0)
            for sample in samples
        ],
        dtype=torch.float32,
    )
    pareto_time = torch.tensor([sample.pareto_time_s for sample in samples], dtype=torch.float32)
    return x, score_gain, pareto_time


def run_reward(
    score_gain: torch.Tensor,
    pareto_time: torch.Tensor,
    median_pareto_time: float,
    time_penalty: float,
) -> torch.Tensor:
    normalized_time = torch.log1p(pareto_time / max(median_pareto_time, 1e-9)) / math.log(2.0)
    return score_gain - time_penalty * normalized_time


def entropy(probability: torch.Tensor) -> torch.Tensor:
    p = probability.clamp(1e-6, 1.0 - 1e-6)
    return -(p * torch.log(p) + (1.0 - p) * torch.log(1.0 - p))


def deterministic_utility(
    model: BudgetPolicy,
    x: torch.Tensor,
    samples: list[BudgetSample],
    mean: torch.Tensor,
    std: torch.Tensor,
    threshold: float,
    time_penalty: float,
    median_pareto_time: float,
) -> tuple[float, dict[str, float | int]]:
    model.eval()
    with torch.no_grad():
        probabilities = torch.sigmoid(model((x - mean) / std)).cpu().tolist()
    actions = [probability >= threshold for probability in probabilities]
    score_regrets = []
    normalized_times = []
    for action, sample in zip(actions, samples):
        chosen = sample.pareto_score if action else sample.resource_score
        score_regrets.append((chosen - sample.pareto_score) / max(sample.pareto_score, 1.0))
        total_time = sample.resource_time_s + (sample.pareto_time_s if action else 0.0)
        normalized_times.append(total_time / max(median_pareto_time, 1e-9))
    utility = statistics.mean(score_regrets) + time_penalty * statistics.mean(normalized_times)
    return utility, {
        "pairs": len(samples),
        "run_pareto": sum(actions),
        "stop": len(actions) - sum(actions),
        "mean_score_regret": statistics.mean(score_regrets),
        "mean_normalized_time": statistics.mean(normalized_times),
    }


def parse_paths(raw: str) -> list[Path]:
    paths = [Path(item.strip()) for item in raw.split(",") if item.strip()]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing CSV inputs: {', '.join(missing)}")
    return paths


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--train-csvs",
        default=f"{DEFAULT_TRAIN},{DEFAULT_TRAIN_SEED43}",
    )
    parser.add_argument("--validation-csvs", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed", type=int, default=20260742)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=3000)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--time-penalty", type=float, default=0.004)
    parser.add_argument("--entropy-bonus", type=float, default=2e-4)
    parser.add_argument(
        "--objective",
        choices=["policy_gradient", "fitted_q"],
        default="fitted_q",
    )
    parser.add_argument("--sign-loss-weight", type=float, default=0.35)
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--random-truth-only", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(4)

    train_paths = parse_paths(args.train_csvs)
    validation_paths = parse_paths(args.validation_csvs)
    train_samples = load_samples(train_paths, args.random_truth_only)
    validation_samples = load_samples(validation_paths, args.random_truth_only)
    train_x, train_gain, train_time = tensors(train_samples)
    validation_x, _validation_gain, _validation_time = tensors(validation_samples)
    mean = train_x.mean(dim=0)
    std = train_x.std(dim=0).clamp_min(1e-6)
    median_pareto_time = statistics.median(sample.pareto_time_s for sample in train_samples)
    rewards = run_reward(train_gain, train_time, median_pareto_time, args.time_penalty)
    reward_scale = float(rewards.abs().mean().clamp_min(1e-6))

    model = BudgetPolicy(len(FEATURE_NAMES), hidden=args.hidden)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    best_utility, best_validation = deterministic_utility(
        model,
        validation_x,
        validation_samples,
        mean,
        std,
        args.threshold,
        args.time_penalty,
        median_pareto_time,
    )
    stale = 0
    final_loss = float("nan")
    for epoch in range(args.epochs):
        model.train()
        output = model((train_x - mean) / std)
        probability = torch.sigmoid(output)
        if args.objective == "policy_gradient":
            # This is the exact expectation of REINFORCE for two logged actions:
            # stop has zero reward and run-Pareto has the measured reward above.
            expected_reward = probability * rewards
            loss = -expected_reward.mean() - args.entropy_bonus * entropy(probability).mean()
        else:
            # For this one-step contextual bandit, fitted Q iteration regresses
            # the observed return directly.  The sign term stabilizes the greedy
            # run/stop policy around Q=0 without changing the reward target.
            normalized_reward = rewards / reward_scale
            value_loss = torch.nn.functional.smooth_l1_loss(output, normalized_reward)
            sign_loss = torch.nn.functional.binary_cross_entropy_with_logits(
                output,
                (rewards > 0.0).to(dtype=torch.float32),
            )
            loss = value_loss + args.sign_loss_weight * sign_loss
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        final_loss = float(loss.detach())

        if epoch % 10 == 0 or epoch + 1 == args.epochs:
            utility, validation = deterministic_utility(
                model,
                validation_x,
                validation_samples,
                mean,
                std,
                args.threshold,
                args.time_penalty,
                median_pareto_time,
            )
            if utility < best_utility - 1e-12:
                best_utility = utility
                best_validation = validation
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                stale = 0
            else:
                stale += 1
            if epoch == 0 or (epoch + 1) % 200 == 0:
                print(
                    f"epoch={epoch + 1} loss={final_loss:.6f} "
                    f"validation_utility={utility:.6f} run={validation['run_pareto']}",
                    flush=True,
                )
            if stale >= 30:
                break

    model.load_state_dict(best_state)
    payload = {
        "state_dict": model.state_dict(),
        "feature_names": FEATURE_NAMES,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "hidden": args.hidden,
        "threshold": args.threshold,
        "time_penalty": args.time_penalty,
        "median_pareto_time_s": median_pareto_time,
        "training_kind": (
            "exact_expectation_contextual_bandit_policy_gradient"
            if args.objective == "policy_gradient"
            else "contextual_bandit_fitted_q_iteration"
        ),
        "objective": args.objective,
        "reward_scale": reward_scale,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, args.out)

    train_positive = sum(sample.pareto_score < sample.resource_score for sample in train_samples)
    manifest = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "status": "complete",
        "training_kind": (
            payload["training_kind"]
            if args.objective == "policy_gradient"
            else "contextual_bandit_fitted_q_iteration"
        ),
        "actions": ["stop_after_resource_nmcts", "run_pareto_resource_nmcts"],
        "reward": "relative score gain minus normalized Pareto runtime penalty",
        "feature_names": FEATURE_NAMES,
        "train_csvs": [display_path(path) for path in train_paths],
        "validation_csvs": [display_path(path) for path in validation_paths],
        "train_samples": len(train_samples),
        "train_pareto_improvements": train_positive,
        "validation_samples": len(validation_samples),
        "best_validation_utility": best_utility,
        "best_validation": best_validation,
        "final_policy_loss": final_loss,
        "epochs_requested": args.epochs,
        "epochs_completed": epoch + 1,
        "config": {
            "seed": args.seed,
            "hidden": args.hidden,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "time_penalty": args.time_penalty,
            "entropy_bonus": args.entropy_bonus,
            "objective": args.objective,
            "sign_loss_weight": args.sign_loss_weight,
            "reward_scale": reward_scale,
            "threshold": args.threshold,
            "random_truth_only": args.random_truth_only,
            "median_pareto_time_s": median_pareto_time,
        },
        "outputs": {
            "model": display_path(args.out),
            "manifest": display_path(args.manifest_out),
        },
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(best_validation, sort_keys=True))
    print(f"wrote {args.out}")
    print(f"wrote {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
