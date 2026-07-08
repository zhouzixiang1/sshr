#!/usr/bin/env python3
"""Train a high-budget Boolean screen depth-frontier policy.

The earlier structure policy chooses among single/depth-1/depth-2 Boolean-ring
screens.  The depth-frontier experiment showed that depth-3 and depth-4 screens
can reduce circuit-resource score, but evaluating all depths is expensive.  This
script trains a coarse policy over depth-2/depth-3/depth-4 so the large-scale
harness can report a learned quality/runtime tradeoff instead of only an
offline oracle frontier.
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch import nn

from factor_plan import SearchConfig, linear_pair_screen_plan
from neural_policy import default_device
from resource_model import ResourceWeights
from train_screen_depth_policy import FEATURE_NAMES, DepthPolicyNet, generate_terms, term_features


THIS_DIR = Path(__file__).resolve().parent
FRONTIER_DEPTHS = (2, 3, 4)
DEPTH_NAMES = {2: "depth2", 3: "depth3", 4: "depth4"}


@dataclass(frozen=True)
class PlanEval:
    screen_depth: int
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
    profile: str
    term_count: int
    features: list[float]
    evals: dict[int, PlanEval]
    oracle_depth: int


@dataclass(frozen=True)
class LabelObjective:
    time_weight: float = 0.0
    ancilla_weight: float = 0.0
    baseline_depth: int = 2
    score_tolerance: float = 0.0


def split_arg(value: str) -> list[int]:
    return [int(v.strip()) for v in value.split(",") if v.strip()]


def make_config() -> SearchConfig:
    return SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=4,
        max_factor_size=5,
        candidate_top_k=24,
        gate_mode="logical_and",
    )


def evaluate_depths(
    terms: frozenset[int],
    config: SearchConfig,
    action_width: int,
    depths: Sequence[int],
) -> dict[int, PlanEval]:
    out: dict[int, PlanEval] = {}
    for screen_depth in depths:
        started = time.perf_counter()
        plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=action_width,
            recursive_depth=screen_depth,
            boolean_ring=True,
        )
        elapsed = time.perf_counter() - started
        out[screen_depth] = PlanEval(
            screen_depth=screen_depth,
            score=plan.score(config.weights),
            t_count=plan.cost.T,
            cnot=plan.cost.CNOT,
            depth_cost=plan.cost.depth,
            gates=plan.cost.gates,
            peak_ancilla=plan.cost.peak_ancilla,
            time_s=elapsed,
        )
    return out


def relative_delta(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def oracle_depth(evals: dict[int, PlanEval], depths: Sequence[int], objective: LabelObjective | None = None) -> int:
    if objective is None or (objective.time_weight == 0.0 and objective.ancilla_weight == 0.0):
        if objective is not None and objective.score_tolerance > 0.0:
            best_score = min(evals[d].score for d in depths)
            allowed = [
                d
                for d in depths
                if evals[d].score <= best_score * (1.0 + objective.score_tolerance) + 1e-9
            ]
            return min(allowed, key=lambda d: (evals[d].time_s, evals[d].score, d))
        return min(depths, key=lambda d: (evals[d].score, evals[d].time_s, d))
    base = evals.get(objective.baseline_depth, evals[depths[0]])

    def label_cost(depth: int) -> tuple[float, float, int]:
        ev = evals[depth]
        score_term = relative_delta(ev.score, base.score)
        time_term = max(0.0, relative_delta(ev.time_s, base.time_s, floor=1e-9))
        ancilla_term = max(0.0, relative_delta(float(ev.peak_ancilla), float(base.peak_ancilla)))
        objective_value = (
            score_term
            + objective.time_weight * time_term
            + objective.ancilla_weight * ancilla_term
        )
        return objective_value, ev.time_s, depth

    return min(depths, key=label_cost)


def build_one(task: tuple[str, int, int, int, str, int, tuple[int, ...], LabelObjective]) -> Example:
    split, n, index, seed, profile, action_width, depths, objective = task
    rng = random.Random(seed)
    config = make_config()
    terms = generate_terms(n, rng, profile)
    features = term_features(terms, config)
    evals = evaluate_depths(terms, config, action_width, depths)
    return Example(
        split=split,
        name=f"{split}_n{n}_{index:04d}_{profile}",
        n=n,
        profile=profile,
        term_count=len(terms),
        features=features,
        evals=evals,
        oracle_depth=oracle_depth(evals, depths, objective),
    )


def make_tasks(
    split: str,
    ns: Sequence[int],
    count_per_n: int,
    seed: int,
    action_width: int,
    depths: tuple[int, ...],
    objective: LabelObjective,
) -> list[tuple[str, int, int, int, str, int, tuple[int, ...], LabelObjective]]:
    profiles = ["shallow", "mixed", "deep"]
    tasks = []
    split_offset = {"train": 0, "valid": 1_000_000, "test": 2_000_000}[split]
    for n in ns:
        for i in range(count_per_n):
            profile = profiles[(i + n) % len(profiles)]
            tasks.append((split, n, i, seed + split_offset + n * 10_000 + i, profile, action_width, depths, objective))
    return tasks


def build_examples(
    split: str,
    ns: Sequence[int],
    count_per_n: int,
    seed: int,
    action_width: int,
    depths: tuple[int, ...],
    workers: int,
    objective: LabelObjective,
) -> list[Example]:
    tasks = make_tasks(split, ns, count_per_n, seed, action_width, depths, objective)
    examples: list[Example] = []
    if workers <= 1:
        for idx, task in enumerate(tasks, 1):
            examples.append(build_one(task))
            if idx % 25 == 0:
                print(f"{split}: {idx}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(build_one, task) for task in tasks]
            for idx, fut in enumerate(as_completed(futures), 1):
                examples.append(fut.result())
                if idx % 25 == 0:
                    print(f"{split}: {idx}/{len(tasks)}", flush=True)
    examples.sort(key=lambda ex: (ex.n, ex.name))
    return examples


def label_index(depth: int, depths: Sequence[int]) -> int:
    return list(depths).index(depth)


def train_model(
    train: list[Example],
    valid: list[Example],
    depths: tuple[int, ...],
    seed: int,
    hidden: int,
    epochs: int,
) -> tuple[DepthPolicyNet, torch.Tensor, torch.Tensor, dict[str, float]]:
    x_train = torch.tensor([ex.features for ex in train], dtype=torch.float32)
    y_train = torch.tensor([label_index(ex.oracle_depth, depths) for ex in train], dtype=torch.long)
    x_valid = torch.tensor([ex.features for ex in valid], dtype=torch.float32)
    y_valid = torch.tensor([label_index(ex.oracle_depth, depths) for ex in valid], dtype=torch.long)

    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    x_train = (x_train - mean) / std
    x_valid = (x_valid - mean) / std

    counts = torch.bincount(y_train, minlength=len(depths)).float()
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
            print(
                f"epoch={epoch+1} train_loss={loss.item():.4f} "
                f"valid_loss={valid_loss:.4f} valid_acc={valid_acc:.3f}",
                flush=True,
            )

    if best_state is not None:
        model.load_state_dict(best_state)
    model.cpu().eval()
    return model, mean, std, {"valid_loss": best_valid, "valid_acc": best_acc}


@torch.no_grad()
def predict_depths(
    model: DepthPolicyNet,
    mean: torch.Tensor,
    std: torch.Tensor,
    examples: list[Example],
    depths: tuple[int, ...],
) -> list[int]:
    if not examples:
        return []
    x = torch.tensor([ex.features for ex in examples], dtype=torch.float32)
    x = (x - mean) / std
    logits = model(x)
    indices = [int(v) for v in logits.argmax(dim=1).tolist()]
    return [depths[i] for i in indices]


def comparison_stats(
    examples: list[Example],
    predicted: list[int],
    baseline_depth: int | None,
    depths: tuple[int, ...],
) -> dict[str, float | int]:
    wins = losses = ties = 0
    rel_score: list[float] = []
    rel_time: list[float] = []
    for ex, pred_depth in zip(examples, predicted):
        target = ex.evals[pred_depth]
        if baseline_depth is None:
            oracle = ex.evals[ex.oracle_depth]
            base_score = oracle.score
            base_time = sum(ex.evals[d].time_s for d in depths)
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
    depths: tuple[int, ...],
    args: argparse.Namespace,
) -> None:
    results_dir = Path(args.results_dir)
    tables_dir = Path(args.tables_dir)
    model_path = Path(args.model_out)
    tag = f"_{args.tag.strip().replace('-', '_')}" if getattr(args, "tag", "").strip() else ""
    results_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "feature_names": FEATURE_NAMES,
            "depths": list(depths),
            "hidden": args.hidden,
            "metrics": metrics,
            "policy_kind": "boolean_screen_depth_frontier",
            "tag": getattr(args, "tag", ""),
            "train_n": args.train_n,
            "test_n": args.test_n,
            "train_per_n": args.train_per_n,
            "valid_per_n": args.valid_per_n,
            "test_per_n": args.test_per_n,
            "label_time_weight": args.label_time_weight,
            "label_ancilla_weight": args.label_ancilla_weight,
            "label_baseline_depth": args.label_baseline_depth,
            "label_score_tolerance": args.label_score_tolerance,
        },
        model_path,
    )

    raw_path = results_dir / f"raw_boolean_screen_depth_frontier_policy{tag}.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "split",
            "name",
            "n",
            "profile",
            "term_count",
            "oracle_depth",
            "predicted_depth",
            "correct_depth",
        ]
        for depth in depths:
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
                    "profile": ex.profile,
                    "term_count": ex.term_count,
                    "oracle_depth": ex.oracle_depth,
                    "predicted_depth": pred_depth,
                    "correct_depth": int(pred_depth == ex.oracle_depth),
                    "policy_score": ex.evals[pred_depth].score,
                    "policy_time_s": ex.evals[pred_depth].time_s,
                    "oracle_score": ex.evals[ex.oracle_depth].score,
                    "oracle_all_time_s": sum(ex.evals[d].time_s for d in depths),
                }
                for depth in depths:
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
    for depth in depths:
        rows.append((f"depth-{depth} screen", comparison_stats(test, test_pred, depth, depths)))
    rows.append(("oracle depth-2/3/4 frontier", comparison_stats(test, test_pred, None, depths)))

    depth_counts = {d: sum(1 for ex in test if ex.oracle_depth == d) for d in depths}
    pred_counts = {d: sum(1 for d_pred in test_pred if d_pred == d) for d in depths}
    accuracy = sum(1 for ex, pred in zip(test, test_pred) if ex.oracle_depth == pred) / max(len(test), 1)
    mean_oracle_gap = statistics.mean(
        (ex.evals[pred].score - ex.evals[ex.oracle_depth].score) / max(ex.evals[ex.oracle_depth].score, 1.0)
        for ex, pred in zip(test, test_pred)
    )
    mean_time_vs_oracle = statistics.mean(
        (ex.evals[pred].time_s - sum(ex.evals[d].time_s for d in depths))
        / max(sum(ex.evals[d].time_s for d in depths), 1e-9)
        for ex, pred in zip(test, test_pred)
    )

    summary_path = results_dir / f"summary_boolean_screen_depth_frontier_policy{tag}.csv"
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
                    "comparison": f"frontier_policy_vs_{label.replace(' ', '_').replace('/', '_')}",
                    "pairs": stats["pairs"],
                    "score_wins": stats["wins"],
                    "score_losses": stats["losses"],
                    "score_ties": stats["ties"],
                    "mean_rel_score": stats["mean_rel_score"],
                    "mean_rel_time": stats["mean_rel_time"],
                }
            )

    analysis_path = results_dir / f"analysis_boolean_screen_depth_frontier_policy{tag}.md"
    with analysis_path.open("w", encoding="utf-8") as f:
        f.write("# Boolean Screen Depth-Frontier Policy\n\n")
        f.write("Structure-level policy for selecting depth-2, depth-3, or depth-4 Boolean-ring screening.\n\n")
        f.write(f"- train examples: {len(train)}\n")
        f.write(f"- validation examples: {len(valid)}\n")
        f.write(f"- held-out test examples: {len(test)}\n")
        f.write(f"- train n: {args.train_n}; test n: {args.test_n}\n")
        if args.label_score_tolerance > 0.0:
            f.write(
                f"- label objective: fastest depth within {args.label_score_tolerance:.3%} "
                "of the score-only oracle frontier\n"
            )
        else:
            f.write(
                f"- label objective: score_delta + {args.label_time_weight:g}*time_delta "
                f"+ {args.label_ancilla_weight:g}*ancilla_delta vs depth-{args.label_baseline_depth}\n"
            )
        f.write(f"- parallel workers for data generation: {args.workers}\n")
        f.write(f"- validation accuracy at best checkpoint: {metrics['valid_acc']:.3f}\n")
        f.write(f"- held-out depth accuracy: {accuracy:.3f}\n")
        f.write(f"- held-out mean score gap to oracle frontier: {mean_oracle_gap:+.2%}\n")
        f.write(f"- held-out mean runtime vs all-depth frontier evaluation: {mean_time_vs_oracle:+.2%}\n\n")
        f.write("Oracle depth distribution on held-out test:\n\n")
        for depth in depths:
            f.write(f"- {DEPTH_NAMES[depth]}: {depth_counts[depth]} oracle / {pred_counts[depth]} predicted\n")
        f.write("\nPaired score comparisons on held-out test:\n\n")
        f.write("| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for label, stats in rows:
            f.write(
                f"| frontier policy vs {label} | {stats['pairs']} | "
                f"{stats['wins']}/{stats['losses']}/{stats['ties']} | "
                f"{stats['mean_rel_score']:+.2%} | {stats['mean_rel_time']:+.2%} |\n"
            )

    def latex_pct(value: float) -> str:
        return f"{value:+.2%}".replace("%", r"\%")

    table_path = tables_dir / f"boolean_screen_depth_frontier_policy{tag}.tex"
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{lrrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Pairs & Score W/L/T & Mean $\\Delta$ score & Mean $\\Delta$ time \\\\\n")
        f.write("\\midrule\n")
        for label, stats in rows:
            f.write(
                f"Frontier policy vs {label} & {stats['pairs']} & "
                f"{stats['wins']}/{stats['losses']}/{stats['ties']} & "
                f"{latex_pct(float(stats['mean_rel_score']))} & {latex_pct(float(stats['mean_rel_time']))} \\\\\n"
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
    ap.add_argument("--seed", type=int, default=20260711)
    ap.add_argument("--train-n", default="16,20,24")
    ap.add_argument("--test-n", default="28,40")
    ap.add_argument("--train-per-n", type=int, default=32)
    ap.add_argument("--valid-per-n", type=int, default=12)
    ap.add_argument("--test-per-n", type=int, default=16)
    ap.add_argument("--epochs", type=int, default=140)
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--model-out", default=str(THIS_DIR / "models" / "boolean_screen_depth_frontier_policy.pt"))
    ap.add_argument("--results-dir", default=str(THIS_DIR / "results"))
    ap.add_argument("--tables-dir", default=str(THIS_DIR / "paper_latex" / "tables"))
    ap.add_argument("--tag", default="", help="Optional filename suffix for model-result variants.")
    ap.add_argument(
        "--label-time-weight",
        type=float,
        default=0.0,
        help="Relative runtime penalty for selecting depth-frontier labels. Default keeps score-only labels.",
    )
    ap.add_argument(
        "--label-ancilla-weight",
        type=float,
        default=0.0,
        help="Relative peak-ancilla penalty for selecting depth-frontier labels.",
    )
    ap.add_argument(
        "--label-baseline-depth",
        type=int,
        default=2,
        choices=list(FRONTIER_DEPTHS),
        help="Baseline depth used by relative cost-aware label penalties.",
    )
    ap.add_argument(
        "--label-score-tolerance",
        type=float,
        default=0.0,
        help="When positive, label each example with the fastest depth whose score is within this relative tolerance of the score-only oracle frontier.",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    depths = FRONTIER_DEPTHS
    train_ns = split_arg(args.train_n)
    test_ns = split_arg(args.test_n)
    label_objective = LabelObjective(
        time_weight=args.label_time_weight,
        ancilla_weight=args.label_ancilla_weight,
        baseline_depth=args.label_baseline_depth,
        score_tolerance=args.label_score_tolerance,
    )

    started = time.time()
    print("building train examples", flush=True)
    train = build_examples(
        "train", train_ns, args.train_per_n, args.seed, args.action_width, depths, args.workers, label_objective
    )
    print("building validation examples", flush=True)
    valid = build_examples(
        "valid", train_ns, args.valid_per_n, args.seed, args.action_width, depths, args.workers, label_objective
    )
    print("building held-out test examples", flush=True)
    test = build_examples(
        "test", test_ns, args.test_per_n, args.seed, args.action_width, depths, args.workers, label_objective
    )

    model, mean, std, metrics = train_model(train, valid, depths, args.seed, args.hidden, args.epochs)
    predictions = {
        "train": predict_depths(model, mean, std, train, depths),
        "valid": predict_depths(model, mean, std, valid, depths),
        "test": predict_depths(model, mean, std, test, depths),
    }
    write_outputs(train, valid, test, predictions, model, mean, std, metrics, depths, args)
    print(f"elapsed {time.time() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
