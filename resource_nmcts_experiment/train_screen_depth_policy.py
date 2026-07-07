#!/usr/bin/env python3
"""Train a structure-level policy for Boolean-ring screen depth selection.

The action-level neural prior in this project ranks individual factor actions.
This script targets a coarser decision that is closer to the current manuscript
gap: choose whether a high-dimensional ANF should use single, depth-1, or
depth-2 Boolean-ring screening.  Labels are produced by running the three
screen depths and selecting the lowest resource score, with lower runtime as a
tie-breaker.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch import nn

from factor_plan import SearchConfig, boolean_linear_factor_actions, linear_pair_screen_plan
from neural_policy import default_device
from resource_model import ResourceWeights


THIS_DIR = Path(__file__).resolve().parent
DEPTHS = (0, 1, 2)
DEPTH_NAMES = {0: "single", 1: "depth1", 2: "depth2"}


FEATURE_NAMES = [
    "n",
    "term_count",
    "mean_degree",
    "max_degree",
    "degree_std",
    "degree_0_frac",
    "degree_1_frac",
    "degree_2_frac",
    "degree_3_frac",
    "degree_4_frac",
    "degree_5_frac",
    "degree_6plus_frac",
    "support_frac",
    "mean_var_freq",
    "max_var_freq",
    "var_entropy",
    "pair_density",
    "mean_pair_freq",
    "max_pair_freq",
    "root_action_count",
    "top_gain_norm",
    "mean_gain_norm",
    "top_coverage",
    "mean_coverage",
    "top_rest_frac",
    "mean_rest_frac",
    "top_residual_terms",
    "mean_residual_terms",
]


@dataclass(frozen=True)
class PlanEval:
    depth: int
    score: float
    t_count: int
    cnot: int
    depth_cost: int
    gates: int
    peak_ancilla: int
    time_s: float


@dataclass(frozen=True)
class Example:
    split: str
    name: str
    n: int
    terms: frozenset[int]
    features: list[float]
    evals: dict[int, PlanEval]
    oracle_depth: int


class DepthPolicyNet(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 96) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Dropout(p=0.05),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, len(DEPTHS)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _bit_mask(rng: random.Random, n: int, degree: int) -> int:
    degree = max(0, min(degree, n))
    mask = 0
    for bit in rng.sample(range(n), degree):
        mask |= 1 << bit
    return mask


def _linear_boolean_expansion(factor: int, residual: int) -> frozenset[int]:
    out: set[int] = set()
    bits = int(factor)
    while bits:
        bit = bits & -bits
        term = int(residual) | bit
        if term in out:
            out.remove(term)
        else:
            out.add(term)
        bits ^= bit
    return frozenset(out)


def _add_boolean_block(
    terms: set[int],
    rng: random.Random,
    n: int,
    residual_count: int,
    degree_range: tuple[int, int],
    nested: bool,
) -> None:
    factor = _bit_mask(rng, n, 2)
    low, high = degree_range
    for _ in range(residual_count):
        residual = _bit_mask(rng, n, rng.randint(low, min(high, n)))
        for term in _linear_boolean_expansion(factor, residual):
            terms.symmetric_difference_update({term})
        if nested and rng.random() < 0.65:
            nested_factor = _bit_mask(rng, n, 2)
            nested_residual = residual | _bit_mask(rng, n, rng.randint(1, min(3, n)))
            for term in _linear_boolean_expansion(nested_factor, nested_residual):
                terms.symmetric_difference_update({term})


def generate_terms(n: int, rng: random.Random, profile: str) -> frozenset[int]:
    """Generate high-dimensional ANF term sets with controllable structure."""
    if profile == "shallow":
        base_terms = rng.randint(24, 72)
        blocks = rng.randint(0, 2)
        nested_prob = 0.05
    elif profile == "mixed":
        base_terms = rng.randint(42, 120)
        blocks = rng.randint(1, 5)
        nested_prob = 0.35
    elif profile == "deep":
        base_terms = rng.randint(64, 156)
        blocks = rng.randint(3, 8)
        nested_prob = 0.78
    else:
        raise ValueError(f"unknown profile: {profile}")

    terms: set[int] = set()
    max_degree = min(n, rng.choice([3, 4, 5, 6]))
    for _ in range(base_terms):
        degree = rng.choices(
            population=list(range(1, max_degree + 1)),
            weights=[1.0, 2.5, 3.0, 2.4, 1.5, 0.9][:max_degree],
            k=1,
        )[0]
        terms.symmetric_difference_update({_bit_mask(rng, n, degree)})

    for _ in range(blocks):
        _add_boolean_block(
            terms,
            rng,
            n,
            residual_count=rng.randint(2, 9),
            degree_range=(1, min(5, n)),
            nested=rng.random() < nested_prob,
        )

    if rng.random() < 0.12:
        terms.add(0)
    for bit in rng.sample(range(n), rng.randint(0, min(3, n))):
        if rng.random() < 0.35:
            terms.symmetric_difference_update({1 << bit})
    terms.discard(0) if rng.random() < 0.70 and len(terms) > 1 else None
    if not terms:
        terms.add(_bit_mask(rng, n, 2))
    return frozenset(terms)


def term_features(terms: frozenset[int], config: SearchConfig) -> list[float]:
    n = max((int(t).bit_length() for t in terms), default=1)
    n = max(1, n)
    degrees = [int(t).bit_count() for t in terms] or [0]
    term_count = len(terms)
    degree_hist = [sum(1 for d in degrees if d == k) / max(term_count, 1) for k in range(6)]
    degree_6plus = sum(1 for d in degrees if d >= 6) / max(term_count, 1)

    var_counts = [0] * n
    pair_counts: dict[tuple[int, int], int] = {}
    for term in terms:
        bits = [i for i in range(n) if (term >> i) & 1]
        for i in bits:
            var_counts[i] += 1
        for pos, i in enumerate(bits):
            for j in bits[pos + 1 :]:
                pair_counts[(i, j)] = pair_counts.get((i, j), 0) + 1

    active_vars = sum(1 for c in var_counts if c)
    var_freqs = [c / max(term_count, 1) for c in var_counts]
    mean_var_freq = statistics.mean(var_freqs) if var_freqs else 0.0
    max_var_freq = max(var_freqs) if var_freqs else 0.0
    total_var = sum(var_counts)
    if total_var:
        var_entropy = -sum((c / total_var) * math.log((c / total_var) + 1e-12) for c in var_counts if c)
        var_entropy /= math.log(n + 1e-12)
    else:
        var_entropy = 0.0

    possible_pairs = n * (n - 1) / 2
    pair_freqs = [c / max(term_count, 1) for c in pair_counts.values()]
    pair_density = len(pair_counts) / max(possible_pairs, 1.0)
    mean_pair_freq = statistics.mean(pair_freqs) if pair_freqs else 0.0
    max_pair_freq = max(pair_freqs) if pair_freqs else 0.0

    actions = boolean_linear_factor_actions(
        terms,
        prefix_len=0,
        live_factor_ancilla=0,
        config=config,
        action_width=32,
        max_linear_width=2,
    )
    direct_score = linear_pair_screen_plan(
        terms,
        config=config,
        action_width=1,
        recursive_depth=0,
        boolean_ring=True,
    ).score(config.weights)
    gain_norms = [a.immediate_gain / max(direct_score, 1.0) for a in actions]
    coverages = [len(a.group) / max(term_count, 1) for a in actions]
    rest_fracs = [len(a.rest) / max(term_count, 1) for a in actions]
    residual_terms = [len(a.residuals) for a in actions]

    return [
        float(n),
        float(term_count),
        float(statistics.mean(degrees)),
        float(max(degrees)),
        float(statistics.pstdev(degrees) if len(degrees) > 1 else 0.0),
        *[float(v) for v in degree_hist],
        float(degree_6plus),
        float(active_vars / max(n, 1)),
        float(mean_var_freq),
        float(max_var_freq),
        float(var_entropy),
        float(pair_density),
        float(mean_pair_freq),
        float(max_pair_freq),
        float(len(actions)),
        float(max(gain_norms) if gain_norms else 0.0),
        float(statistics.mean(gain_norms) if gain_norms else 0.0),
        float(max(coverages) if coverages else 0.0),
        float(statistics.mean(coverages) if coverages else 0.0),
        float(min(rest_fracs) if rest_fracs else 1.0),
        float(statistics.mean(rest_fracs) if rest_fracs else 1.0),
        float(max(residual_terms) if residual_terms else 0.0),
        float(statistics.mean(residual_terms) if residual_terms else 0.0),
    ]


def evaluate_depths(terms: frozenset[int], config: SearchConfig, action_width: int) -> dict[int, PlanEval]:
    out: dict[int, PlanEval] = {}
    for depth in DEPTHS:
        started = time.perf_counter()
        plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=action_width,
            recursive_depth=depth,
            boolean_ring=True,
        )
        elapsed = time.perf_counter() - started
        out[depth] = PlanEval(
            depth=depth,
            score=plan.score(config.weights),
            t_count=plan.cost.T,
            cnot=plan.cost.CNOT,
            depth_cost=plan.cost.depth,
            gates=plan.cost.gates,
            peak_ancilla=plan.cost.peak_ancilla,
            time_s=elapsed,
        )
    return out


def oracle_depth(evals: dict[int, PlanEval]) -> int:
    return min(DEPTHS, key=lambda d: (evals[d].score, evals[d].time_s, d))


def make_examples(
    split: str,
    ns: Sequence[int],
    count_per_n: int,
    rng: random.Random,
    config: SearchConfig,
    action_width: int,
) -> list[Example]:
    examples: list[Example] = []
    profiles = ["shallow", "mixed", "deep"]
    for n in ns:
        for i in range(count_per_n):
            profile = profiles[(i + rng.randrange(3)) % len(profiles)]
            terms = generate_terms(n, rng, profile)
            features = term_features(terms, config)
            evals = evaluate_depths(terms, config, action_width)
            examples.append(
                Example(
                    split=split,
                    name=f"{split}_n{n}_{i:04d}_{profile}",
                    n=n,
                    terms=terms,
                    features=features,
                    evals=evals,
                    oracle_depth=oracle_depth(evals),
                )
            )
    return examples


def split_arg(value: str) -> list[int]:
    return [int(v.strip()) for v in value.split(",") if v.strip()]


def train_model(
    train: list[Example],
    valid: list[Example],
    seed: int,
    hidden: int,
    epochs: int,
) -> tuple[DepthPolicyNet, torch.Tensor, torch.Tensor, dict[str, float]]:
    x_train = torch.tensor([ex.features for ex in train], dtype=torch.float32)
    y_train = torch.tensor([ex.oracle_depth for ex in train], dtype=torch.long)
    x_valid = torch.tensor([ex.features for ex in valid], dtype=torch.float32)
    y_valid = torch.tensor([ex.oracle_depth for ex in valid], dtype=torch.long)

    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    x_train = (x_train - mean) / std
    x_valid = (x_valid - mean) / std

    counts = torch.bincount(y_train, minlength=len(DEPTHS)).float()
    class_weights = counts.sum() / counts.clamp_min(1.0)
    class_weights = class_weights / class_weights.mean()

    torch.manual_seed(seed)
    device = default_device()
    model = DepthPolicyNet(len(FEATURE_NAMES), hidden=hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights.to(device))

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
            valid_acc = (valid_logits.argmax(dim=1) == y_valid_d).float().mean().item()
        if valid_loss < best_valid:
            best_valid = valid_loss
            best_acc = valid_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 20 == 0:
            print(f"epoch={epoch+1} train_loss={loss.item():.4f} valid_loss={valid_loss:.4f} valid_acc={valid_acc:.3f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    model.cpu().eval()
    return model, mean, std, {"valid_loss": best_valid, "valid_acc": best_acc}


@torch.no_grad()
def predict_depths(model: DepthPolicyNet, mean: torch.Tensor, std: torch.Tensor, examples: list[Example]) -> list[int]:
    if not examples:
        return []
    x = torch.tensor([ex.features for ex in examples], dtype=torch.float32)
    x = (x - mean) / std
    logits = model(x)
    return [int(v) for v in logits.argmax(dim=1).tolist()]


def comparison_stats(examples: list[Example], predicted: list[int], baseline_depth: int | None) -> dict[str, float | int | str]:
    wins = losses = ties = 0
    rel_score: list[float] = []
    rel_time: list[float] = []
    for ex, pred_depth in zip(examples, predicted):
        target = ex.evals[pred_depth]
        if baseline_depth is None:
            base_score = ex.evals[ex.oracle_depth].score
            base_time = sum(ex.evals[d].time_s for d in DEPTHS)
        else:
            base = ex.evals[baseline_depth]
            base_score = base.score
            base_time = base.time_s
        if target.score < base_score - 1e-9:
            wins += 1
        elif target.score > base_score + 1e-9:
            losses += 1
        else:
            ties += 1
        rel_score.append((target.score - base_score) / max(base_score, 1.0))
        rel_time.append((target.time_s - base_time) / max(base_time, 1e-9))
    return {
        "pairs": len(examples),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_rel_score": statistics.mean(rel_score) if rel_score else 0.0,
        "mean_rel_time": statistics.mean(rel_time) if rel_time else 0.0,
    }


def write_outputs(
    train: list[Example],
    valid: list[Example],
    test: list[Example],
    predictions: dict[str, list[int]],
    model: DepthPolicyNet,
    mean: torch.Tensor,
    std: torch.Tensor,
    metrics: dict[str, float],
    args: argparse.Namespace,
) -> None:
    results_dir = Path(args.results_dir)
    tables_dir = Path(args.tables_dir)
    model_path = Path(args.model_out)
    results_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "feature_names": FEATURE_NAMES,
            "depths": list(DEPTHS),
            "hidden": args.hidden,
            "metrics": metrics,
        },
        model_path,
    )

    raw_path = results_dir / "raw_boolean_screen_depth_policy.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "split",
            "name",
            "n",
            "term_count",
            "oracle_depth",
            "predicted_depth",
            "correct_depth",
        ]
        for depth in DEPTHS:
            prefix = DEPTH_NAMES[depth]
            fieldnames.extend(
                [
                    f"{prefix}_score",
                    f"{prefix}_T",
                    f"{prefix}_CNOT",
                    f"{prefix}_depth",
                    f"{prefix}_ancilla",
                    f"{prefix}_time_s",
                ]
            )
        fieldnames.extend(["policy_score", "policy_time_s", "oracle_score", "oracle_all_time_s"])
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for split_name, examples in [("train", train), ("valid", valid), ("test", test)]:
            preds = predictions[split_name]
            for ex, pred_depth in zip(examples, preds):
                row = {
                    "split": split_name,
                    "name": ex.name,
                    "n": ex.n,
                    "term_count": len(ex.terms),
                    "oracle_depth": ex.oracle_depth,
                    "predicted_depth": pred_depth,
                    "correct_depth": int(pred_depth == ex.oracle_depth),
                    "policy_score": ex.evals[pred_depth].score,
                    "policy_time_s": ex.evals[pred_depth].time_s,
                    "oracle_score": ex.evals[ex.oracle_depth].score,
                    "oracle_all_time_s": sum(ex.evals[d].time_s for d in DEPTHS),
                }
                for depth in DEPTHS:
                    ev = ex.evals[depth]
                    prefix = DEPTH_NAMES[depth]
                    row.update(
                        {
                            f"{prefix}_score": ev.score,
                            f"{prefix}_T": ev.t_count,
                            f"{prefix}_CNOT": ev.cnot,
                            f"{prefix}_depth": ev.depth_cost,
                            f"{prefix}_ancilla": ev.peak_ancilla,
                            f"{prefix}_time_s": ev.time_s,
                        }
                    )
                writer.writerow(row)

    test_pred = predictions["test"]
    rows = []
    for label, depth in [("single screen", 0), ("depth-1 screen", 1), ("depth-2 screen", 2)]:
        stats = comparison_stats(test, test_pred, depth)
        rows.append((label, stats))
    rows.append(("oracle adaptive all-depth", comparison_stats(test, test_pred, None)))

    depth_counts = {d: sum(1 for ex in test if ex.oracle_depth == d) for d in DEPTHS}
    pred_counts = {d: sum(1 for d_pred in test_pred if d_pred == d) for d in DEPTHS}
    accuracy = sum(1 for ex, pred in zip(test, test_pred) if ex.oracle_depth == pred) / max(len(test), 1)
    mean_oracle_gap = statistics.mean(
        (ex.evals[pred].score - ex.evals[ex.oracle_depth].score) / max(ex.evals[ex.oracle_depth].score, 1.0)
        for ex, pred in zip(test, test_pred)
    )
    mean_time_vs_oracle = statistics.mean(
        (ex.evals[pred].time_s - sum(ex.evals[d].time_s for d in DEPTHS))
        / max(sum(ex.evals[d].time_s for d in DEPTHS), 1e-9)
        for ex, pred in zip(test, test_pred)
    )

    summary_path = results_dir / "summary_boolean_screen_depth_policy.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "comparison",
                "pairs",
                "score_wins",
                "score_losses",
                "score_ties",
                "mean_rel_score",
                "mean_rel_time",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for label, stats in rows:
            writer.writerow(
                {
                    "comparison": f"policy_vs_{label.replace(' ', '_')}",
                    "pairs": stats["pairs"],
                    "score_wins": stats["wins"],
                    "score_losses": stats["losses"],
                    "score_ties": stats["ties"],
                    "mean_rel_score": stats["mean_rel_score"],
                    "mean_rel_time": stats["mean_rel_time"],
                }
            )

    analysis_path = results_dir / "analysis_boolean_screen_depth_policy.md"
    with analysis_path.open("w", encoding="utf-8") as f:
        f.write("# Boolean Screen Depth Policy\n\n")
        f.write("Structure-level policy for selecting single, depth-1, or depth-2 Boolean-ring screening.\n\n")
        f.write(f"- train examples: {len(train)}\n")
        f.write(f"- validation examples: {len(valid)}\n")
        f.write(f"- held-out test examples: {len(test)}\n")
        f.write(f"- train n: {args.train_n}; test n: {args.test_n}\n")
        f.write(f"- validation accuracy at best checkpoint: {metrics['valid_acc']:.3f}\n")
        f.write(f"- held-out depth accuracy: {accuracy:.3f}\n")
        f.write(f"- held-out mean score gap to oracle adaptive: {mean_oracle_gap:+.2%}\n")
        f.write(f"- held-out mean runtime vs all-depth oracle evaluation: {mean_time_vs_oracle:+.2%}\n\n")
        f.write("Oracle depth distribution on held-out test:\n\n")
        for depth in DEPTHS:
            f.write(f"- {DEPTH_NAMES[depth]}: {depth_counts[depth]} oracle / {pred_counts[depth]} predicted\n")
        f.write("\nPaired score comparisons on held-out test:\n\n")
        f.write("| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for label, stats in rows:
            f.write(
                f"| policy vs {label} | {stats['pairs']} | "
                f"{stats['wins']}/{stats['losses']}/{stats['ties']} | "
                f"{stats['mean_rel_score']:+.2%} | {stats['mean_rel_time']:+.2%} |\n"
            )

    table_path = tables_dir / "boolean_screen_depth_policy.tex"
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Pairs & Score W/L/T & Mean $\\Delta$ score & Mean $\\Delta$ time \\\\\n")
        f.write("\\midrule\n")
        for label, stats in rows:
            f.write(
                f"Policy vs {label} & {stats['pairs']} & "
                f"{stats['wins']}/{stats['losses']}/{stats['ties']} & "
                f"{stats['mean_rel_score']:+.2%} & {stats['mean_rel_time']:+.2%} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")

    print(f"wrote {model_path}")
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260708)
    ap.add_argument("--train-n", default="14,16,18")
    ap.add_argument("--test-n", default="20")
    ap.add_argument("--train-per-n", type=int, default=80)
    ap.add_argument("--valid-per-n", type=int, default=24)
    ap.add_argument("--test-per-n", type=int, default=48)
    ap.add_argument("--epochs", type=int, default=140)
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--gate-mode", choices=["mct", "logical_and"], default="mct")
    ap.add_argument("--model-out", default=str(THIS_DIR / "models" / "boolean_screen_depth_policy.pt"))
    ap.add_argument("--results-dir", default=str(THIS_DIR / "results"))
    ap.add_argument("--tables-dir", default=str(THIS_DIR / "paper_latex" / "tables"))
    args = ap.parse_args(list(argv) if argv is not None else None)

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

    model, mean, std, metrics = train_model(train, valid, args.seed, args.hidden, args.epochs)
    predictions = {
        "train": predict_depths(model, mean, std, train),
        "valid": predict_depths(model, mean, std, valid),
        "test": predict_depths(model, mean, std, test),
    }
    write_outputs(train, valid, test, predictions, model, mean, std, metrics, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
