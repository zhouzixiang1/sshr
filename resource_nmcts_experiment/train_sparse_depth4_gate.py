#!/usr/bin/env python3
"""Train a sparse frontier gate for depth-4 Boolean-ring screening.

The sparse depth-frontier audit showed that evaluating depth 2 and depth 4 can
match the full measured depth-2/3/4 frontier on current scale slices.  This
script adds a learned control layer on top of that sparse frontier: after the
depth-2 screen has been evaluated, a binary gate predicts whether depth 4 is
worth running.  The validation threshold is chosen conservatively to limit
false skips, because a false skip means depth 4 would have improved the score.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch
from torch import nn

from neural_policy import default_device
from train_screen_depth_frontier_policy import LabelObjective, build_examples, split_arg
from train_screen_depth_policy import FEATURE_NAMES


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
MODELS = THIS_DIR / "models"
TABLES = THIS_DIR / "paper_latex" / "tables"
GATE_DEPTHS = (2, 4)


EXTRA_FEATURE_NAMES = [
    "depth2_score",
    "depth2_T",
    "depth2_CNOT",
    "depth2_depth",
    "depth2_peak_ancilla",
    "depth2_time_s",
    "depth2_T_per_term",
    "depth2_CNOT_per_term",
    "depth2_depth_per_term",
]


class SparseDepth4GateNet(nn.Module):
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
class GateStats:
    split: str
    pairs: int
    run_depth4: int
    true_runs: int
    false_runs: int
    false_skips: int
    score_wins_vs_sparse: int
    score_losses_vs_sparse: int
    score_ties_vs_sparse: int
    mean_rel_score_vs_sparse: float
    mean_rel_time_vs_sparse: float
    score_wins_vs_depth2: int
    score_losses_vs_depth2: int
    score_ties_vs_depth2: int
    mean_rel_score_vs_depth2: float
    mean_rel_time_vs_depth2: float


def gate_feature_names() -> list[str]:
    return [*FEATURE_NAMES, *EXTRA_FEATURE_NAMES]


def gate_features(example) -> list[float]:
    depth2 = example.evals[2]
    terms = max(int(example.term_count), 1)
    return [
        *example.features,
        float(depth2.score),
        float(depth2.t_count),
        float(depth2.cnot),
        float(depth2.depth_cost),
        float(depth2.peak_ancilla),
        float(depth2.time_s),
        float(depth2.t_count) / terms,
        float(depth2.cnot) / terms,
        float(depth2.depth_cost) / terms,
    ]


def run_depth4_label(example, eps: float) -> int:
    d2 = example.evals[2]
    d4 = example.evals[4]
    return int(d4.score < d2.score - eps)


def sparse_score(example) -> float:
    d2 = example.evals[2]
    d4 = example.evals[4]
    return min(d2.score, d4.score)


def sparse_time(example) -> float:
    return example.evals[2].time_s + example.evals[4].time_s


def selected_score(example, run_depth4: bool) -> float:
    if not run_depth4:
        return example.evals[2].score
    return sparse_score(example)


def selected_time(example, run_depth4: bool) -> float:
    return example.evals[2].time_s + (example.evals[4].time_s if run_depth4 else 0.0)


def rel(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def standardize(train: list, other: list) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    x_train = torch.tensor([gate_features(ex) for ex in train], dtype=torch.float32)
    x_other = torch.tensor([gate_features(ex) for ex in other], dtype=torch.float32)
    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    return (x_train - mean) / std, (x_other - mean) / std, mean, std


def train_gate(
    train: list,
    valid: list,
    seed: int,
    hidden: int,
    epochs: int,
    eps: float,
) -> tuple[SparseDepth4GateNet, torch.Tensor, torch.Tensor, dict[str, float]]:
    x_train, x_valid, mean, std = standardize(train, valid)
    y_train = torch.tensor([run_depth4_label(ex, eps) for ex in train], dtype=torch.float32)
    y_valid = torch.tensor([run_depth4_label(ex, eps) for ex in valid], dtype=torch.float32)

    positives = y_train.sum().item()
    negatives = max(float(len(y_train)) - positives, 1.0)
    pos_weight = torch.tensor([negatives / max(positives, 1.0)], dtype=torch.float32)

    torch.manual_seed(seed)
    device = default_device()
    model = SparseDepth4GateNet(len(gate_feature_names()), hidden=hidden).to(device)
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
            valid_pred = (torch.sigmoid(valid_logits) >= 0.5).float()
            valid_acc = (valid_pred == y_valid_d).float().mean().item()
        if valid_loss < best_valid:
            best_valid = valid_loss
            best_acc = valid_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 20 == 0:
            print(
                f"epoch={epoch + 1} train_loss={loss.item():.4f} "
                f"valid_loss={valid_loss:.4f} valid_acc@0.5={valid_acc:.3f}",
                flush=True,
            )

    if best_state is not None:
        model.load_state_dict(best_state)
    model.cpu().eval()
    return model, mean, std, {"valid_loss": best_valid, "valid_acc_at_0_5": best_acc}


@torch.no_grad()
def predict_probs(model: SparseDepth4GateNet, mean: torch.Tensor, std: torch.Tensor, examples: list) -> list[float]:
    if not examples:
        return []
    x = torch.tensor([gate_features(ex) for ex in examples], dtype=torch.float32)
    x = (x - mean) / std
    return [float(value) for value in torch.sigmoid(model(x)).tolist()]


def evaluate_gate(examples: list, probs: list[float], threshold: float, eps: float, split: str) -> GateStats:
    run_depth4 = true_runs = false_runs = false_skips = 0
    sparse_wins = sparse_losses = sparse_ties = 0
    depth2_wins = depth2_losses = depth2_ties = 0
    rel_score_sparse: list[float] = []
    rel_time_sparse: list[float] = []
    rel_score_depth2: list[float] = []
    rel_time_depth2: list[float] = []
    for ex, prob in zip(examples, probs):
        run = prob >= threshold
        label = run_depth4_label(ex, eps) == 1
        if run:
            run_depth4 += 1
        if run and label:
            true_runs += 1
        if run and not label:
            false_runs += 1
        if (not run) and label:
            false_skips += 1

        target_score = selected_score(ex, run)
        target_time = selected_time(ex, run)
        sparse_base_score = sparse_score(ex)
        sparse_base_time = sparse_time(ex)
        depth2 = ex.evals[2]

        if target_score < sparse_base_score - 1e-9:
            sparse_wins += 1
        elif target_score > sparse_base_score + 1e-9:
            sparse_losses += 1
        else:
            sparse_ties += 1
        if target_score < depth2.score - 1e-9:
            depth2_wins += 1
        elif target_score > depth2.score + 1e-9:
            depth2_losses += 1
        else:
            depth2_ties += 1
        rel_score_sparse.append(rel(target_score, sparse_base_score))
        rel_time_sparse.append(rel(target_time, sparse_base_time, floor=1e-9))
        rel_score_depth2.append(rel(target_score, depth2.score))
        rel_time_depth2.append(rel(target_time, depth2.time_s, floor=1e-9))

    return GateStats(
        split=split,
        pairs=len(examples),
        run_depth4=run_depth4,
        true_runs=true_runs,
        false_runs=false_runs,
        false_skips=false_skips,
        score_wins_vs_sparse=sparse_wins,
        score_losses_vs_sparse=sparse_losses,
        score_ties_vs_sparse=sparse_ties,
        mean_rel_score_vs_sparse=statistics.mean(rel_score_sparse) if rel_score_sparse else 0.0,
        mean_rel_time_vs_sparse=statistics.mean(rel_time_sparse) if rel_time_sparse else 0.0,
        score_wins_vs_depth2=depth2_wins,
        score_losses_vs_depth2=depth2_losses,
        score_ties_vs_depth2=depth2_ties,
        mean_rel_score_vs_depth2=statistics.mean(rel_score_depth2) if rel_score_depth2 else 0.0,
        mean_rel_time_vs_depth2=statistics.mean(rel_time_depth2) if rel_time_depth2 else 0.0,
    )


def threshold_grid(probs: list[float]) -> list[float]:
    values = sorted(set(float(p) for p in probs))
    if not values:
        return [0.5]
    grid = [0.0, 1.0, values[0] - 1e-9, values[-1] + 1e-9]
    grid.extend(values)
    grid.extend((a + b) / 2.0 for a, b in zip(values, values[1:]))
    return sorted(set(max(0.0, min(1.0, value)) for value in grid))


def select_threshold(
    examples: list,
    probs: list[float],
    eps: float,
    max_false_skips: int,
    max_mean_score_gap: float,
    safety_factor: float,
) -> tuple[float, list[dict[str, float | int]]]:
    labels = [run_depth4_label(ex, eps) for ex in examples]
    positive_probs = [prob for prob, label in zip(probs, labels) if label == 1]
    conservative_ceiling = 1.0
    if positive_probs and 0.0 < safety_factor < 1.0:
        conservative_ceiling = max(0.0, min(positive_probs) * safety_factor)
    candidates = []
    best: tuple[float, float, int, float] | None = None
    for threshold in threshold_grid(probs):
        stats = evaluate_gate(examples, probs, threshold, eps, "valid")
        row = {
            "threshold": threshold,
            "run_depth4": stats.run_depth4,
            "false_skips": stats.false_skips,
            "mean_rel_score_vs_sparse": stats.mean_rel_score_vs_sparse,
            "mean_rel_time_vs_sparse": stats.mean_rel_time_vs_sparse,
        }
        candidates.append(row)
        if (
            threshold <= conservative_ceiling + 1e-12
            and stats.false_skips <= max_false_skips
            and stats.mean_rel_score_vs_sparse <= max_mean_score_gap
        ):
            key = (stats.mean_rel_time_vs_sparse, stats.mean_rel_score_vs_sparse, stats.run_depth4, threshold)
            if best is None or key < best:
                best = key
    if best is not None:
        return best[3], candidates

    fallback = min(
        candidates,
        key=lambda row: (
            int(row["false_skips"]),
            float(row["mean_rel_score_vs_sparse"]),
            float(row["mean_rel_time_vs_sparse"]),
        ),
    )
    return float(fallback["threshold"]), candidates


def pct(value: float) -> str:
    return f"{100.0 * float(value):+.2f}%"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def write_raw(path: Path, splits: list[tuple[str, list, list[float]]], threshold: float, eps: float) -> None:
    fields = [
        "split",
        "name",
        "n",
        "profile",
        "term_count",
        "run_depth4_label",
        "run_depth4_prob",
        "run_depth4_pred",
        "depth2_score",
        "depth4_score",
        "gate_score",
        "sparse_score",
        "depth2_time_s",
        "depth4_time_s",
        "gate_time_s",
        "sparse_time_s",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for split, examples, probs in splits:
            for ex, prob in zip(examples, probs):
                run = prob >= threshold
                writer.writerow(
                    {
                        "split": split,
                        "name": ex.name,
                        "n": ex.n,
                        "profile": ex.profile,
                        "term_count": ex.term_count,
                        "run_depth4_label": run_depth4_label(ex, eps),
                        "run_depth4_prob": prob,
                        "run_depth4_pred": int(run),
                        "depth2_score": ex.evals[2].score,
                        "depth4_score": ex.evals[4].score,
                        "gate_score": selected_score(ex, run),
                        "sparse_score": sparse_score(ex),
                        "depth2_time_s": ex.evals[2].time_s,
                        "depth4_time_s": ex.evals[4].time_s,
                        "gate_time_s": selected_time(ex, run),
                        "sparse_time_s": sparse_time(ex),
                    }
                )


def write_summary(path: Path, stats: list[GateStats]) -> None:
    fields = [
        "split",
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
        for st in stats:
            writer.writerow(
                {
                    "split": st.split,
                    "pairs": st.pairs,
                    "run_depth4": st.run_depth4,
                    "true_runs": st.true_runs,
                    "false_runs": st.false_runs,
                    "false_skips": st.false_skips,
                    "score_wlt_vs_sparse": (
                        f"{st.score_wins_vs_sparse}/{st.score_losses_vs_sparse}/{st.score_ties_vs_sparse}"
                    ),
                    "mean_rel_score_vs_sparse": st.mean_rel_score_vs_sparse,
                    "mean_rel_time_vs_sparse": st.mean_rel_time_vs_sparse,
                    "score_wlt_vs_depth2": (
                        f"{st.score_wins_vs_depth2}/{st.score_losses_vs_depth2}/{st.score_ties_vs_depth2}"
                    ),
                    "mean_rel_score_vs_depth2": st.mean_rel_score_vs_depth2,
                    "mean_rel_time_vs_depth2": st.mean_rel_time_vs_depth2,
                }
            )


def write_analysis(
    path: Path,
    stats: list[GateStats],
    threshold: float,
    train_count: int,
    valid_count: int,
    test_count: int,
    metrics: dict[str, float],
    args: argparse.Namespace,
) -> None:
    lines = [
        "# Sparse Depth-4 Gate",
        "",
        "The gate predicts whether depth-4 Boolean-ring screening should run after depth-2 has been evaluated.",
        "It is compared with the deterministic sparse depth-2/4 frontier and with a depth-2-only baseline.",
        "",
        f"- train examples: {train_count}",
        f"- validation examples: {valid_count}",
        f"- held-out test examples: {test_count}",
        f"- train n: {args.train_n}; test n: {args.test_n}",
        f"- validation loss: {metrics['valid_loss']:.4f}; validation accuracy at 0.5: {metrics['valid_acc_at_0_5']:.3f}",
        f"- selected threshold: {threshold:.6f}",
        f"- max validation false skips: {args.max_valid_false_skips}",
        f"- max validation mean score gap: {args.max_valid_score_gap:.4%}",
        f"- validation threshold safety factor: {args.threshold_safety_factor:g}",
        "",
        "| split | pairs | run depth-4 | false skips | score W/L/T vs sparse | mean score vs sparse | mean time vs sparse | score W/L/T vs depth-2 | mean score vs depth-2 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for st in stats:
        lines.append(
            "| "
            + " | ".join(
                [
                    st.split,
                    str(st.pairs),
                    str(st.run_depth4),
                    str(st.false_skips),
                    f"{st.score_wins_vs_sparse}/{st.score_losses_vs_sparse}/{st.score_ties_vs_sparse}",
                    pct(st.mean_rel_score_vs_sparse),
                    pct(st.mean_rel_time_vs_sparse),
                    f"{st.score_wins_vs_depth2}/{st.score_losses_vs_depth2}/{st.score_ties_vs_depth2}",
                    pct(st.mean_rel_score_vs_depth2),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- The gate is a learned budget controller for the sparse depth frontier, not a hardware scheduler.",
            "- False skips are the key risk because they skip a depth-4 run that would have improved score.",
            "- The deterministic sparse depth-2/4 frontier remains the quality reference; the learned gate trades some quality for additional planning-time reduction if false skips occur.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, stats: list[GateStats]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.12\linewidth}rrrr>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Split & Pairs & Run d4 & False skips & Score W/L/T vs sparse & Mean $\Delta$ score & Mean $\Delta$ time & Score W/L/T vs depth-2 \\",
        r"\midrule",
    ]
    for st in stats:
        lines.append(
            " & ".join(
                [
                    st.split,
                    str(st.pairs),
                    str(st.run_depth4),
                    str(st.false_skips),
                    f"{st.score_wins_vs_sparse}/{st.score_losses_vs_sparse}/{st.score_ties_vs_sparse}",
                    latex_pct(st.mean_rel_score_vs_sparse),
                    latex_pct(st.mean_rel_time_vs_sparse),
                    f"{st.score_wins_vs_depth2}/{st.score_losses_vs_depth2}/{st.score_ties_vs_depth2}",
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260712)
    ap.add_argument("--train-n", default="16,20,24")
    ap.add_argument("--test-n", default="28,40")
    ap.add_argument("--train-per-n", type=int, default=32)
    ap.add_argument("--valid-per-n", type=int, default=16)
    ap.add_argument("--test-per-n", type=int, default=24)
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--eps", type=float, default=1e-9)
    ap.add_argument("--max-valid-false-skips", type=int, default=0)
    ap.add_argument("--max-valid-score-gap", type=float, default=0.0005)
    ap.add_argument(
        "--threshold-safety-factor",
        type=float,
        default=0.1,
        help="Conservative multiplier on the smallest positive validation probability.",
    )
    ap.add_argument("--model-out", type=Path, default=MODELS / "sparse_depth4_gate.pt")
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    ap.add_argument("--tables-dir", type=Path, default=TABLES)
    args = ap.parse_args(list(argv) if argv is not None else None)

    train_ns = split_arg(args.train_n)
    test_ns = split_arg(args.test_n)
    objective = LabelObjective()
    print("building train examples", flush=True)
    train = build_examples(
        "train", train_ns, args.train_per_n, args.seed, args.action_width, GATE_DEPTHS, args.workers, objective
    )
    print("building validation examples", flush=True)
    valid = build_examples(
        "valid", train_ns, args.valid_per_n, args.seed, args.action_width, GATE_DEPTHS, args.workers, objective
    )
    print("building held-out test examples", flush=True)
    test = build_examples(
        "test", test_ns, args.test_per_n, args.seed, args.action_width, GATE_DEPTHS, args.workers, objective
    )

    model, mean, std, metrics = train_gate(train, valid, args.seed, args.hidden, args.epochs, args.eps)
    valid_probs = predict_probs(model, mean, std, valid)
    threshold, threshold_rows = select_threshold(
        valid,
        valid_probs,
        args.eps,
        args.max_valid_false_skips,
        args.max_valid_score_gap,
        args.threshold_safety_factor,
    )
    train_probs = predict_probs(model, mean, std, train)
    test_probs = predict_probs(model, mean, std, test)
    stats = [
        evaluate_gate(train, train_probs, threshold, args.eps, "train"),
        evaluate_gate(valid, valid_probs, threshold, args.eps, "valid"),
        evaluate_gate(test, test_probs, threshold, args.eps, "test"),
    ]

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "feature_names": gate_feature_names(),
            "hidden": args.hidden,
            "threshold": threshold,
            "metrics": metrics,
            "train_n": args.train_n,
            "test_n": args.test_n,
            "train_per_n": args.train_per_n,
            "valid_per_n": args.valid_per_n,
            "test_per_n": args.test_per_n,
            "threshold_grid": threshold_rows,
            "threshold_safety_factor": args.threshold_safety_factor,
        },
        args.model_out,
    )

    raw_path = args.results_dir / "raw_sparse_depth4_gate.csv"
    summary_path = args.results_dir / "summary_sparse_depth4_gate.csv"
    analysis_path = args.results_dir / "analysis_sparse_depth4_gate.md"
    table_path = args.tables_dir / "sparse_depth4_gate.tex"
    write_raw(raw_path, [("train", train, train_probs), ("valid", valid, valid_probs), ("test", test, test_probs)], threshold, args.eps)
    write_summary(summary_path, stats)
    write_analysis(analysis_path, stats, threshold, len(train), len(valid), len(test), metrics, args)
    write_latex(table_path, stats)
    print(f"wrote {args.model_out}")
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
