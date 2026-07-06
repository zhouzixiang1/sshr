#!/usr/bin/env python3
"""Train a small neural prior for ANF factor actions."""
from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import List, Tuple

import torch
from torch import nn

from anf_utils import anf_monomials, random_anf_function, random_truth_function, structured_suite
from factor_plan import SearchConfig, action_features, candidate_actions, direct_plan, factor_cost, greedy_plan
from neural_policy import ActionNet, default_device, save_model


THIS_DIR = Path(__file__).resolve().parent


PRESETS = {
    "smoke": {"samples": 80, "epochs": 30, "n_min": 3, "n_max": 7},
    "rollout": {"samples": 520, "epochs": 60, "n_min": 3, "n_max": 9},
    "main": {"samples": 2200, "epochs": 80, "n_min": 3, "n_max": 10},
}


def collect_from_terms(
    terms: frozenset[int],
    config: SearchConfig,
    rows: List[List[float]],
    labels: List[float],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    depth: int = 0,
    max_depth: int = 4,
    child_branch: int = 3,
    label_mode: str = "immediate",
    greedy_memo: dict | None = None,
) -> None:
    greedy_memo = {} if greedy_memo is None else greedy_memo
    direct_score = direct_plan(terms, prefix_len, live_factor_ancilla, config).score(config.weights)
    actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config)
    for action in actions:
        rows.append(
            action_features(
                terms,
                prefix_len,
                live_factor_ancilla,
                action.factor,
                action.group,
                action.residuals,
                action.rest,
                action.immediate_gain,
                direct_score,
            )
        )
        if label_mode == "rollout":
            group = greedy_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                config,
                memo=greedy_memo,
            )
            rest = greedy_plan(
                action.rest,
                prefix_len,
                live_factor_ancilla,
                config,
                memo=greedy_memo,
            )
            action_score = factor_cost(action, group, rest, live_factor_ancilla, config).score(config.weights)
            improvement = direct_score - action_score
        else:
            improvement = action.immediate_gain
        labels.append(max(-2.0, min(2.0, 8.0 * improvement / max(direct_score, 1.0))))
    if depth >= max_depth or not actions:
        return
    # Follow a few strong actions to collect child-state contexts.
    for action in actions[:child_branch]:
        collect_from_terms(
            action.residuals,
            config,
            rows,
            labels,
            prefix_len + 1,
            live_factor_ancilla + 1,
            depth + 1,
            max_depth,
            child_branch,
            label_mode,
            greedy_memo,
        )
        collect_from_terms(
            action.rest,
            config,
            rows,
            labels,
            prefix_len,
            live_factor_ancilla,
            depth + 1,
            max_depth,
            child_branch,
            label_mode,
            greedy_memo,
        )


def build_dataset(
    preset: str,
    seed: int,
    config: SearchConfig,
    label_mode: str,
    max_depth: int,
    child_branch: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    cfg = PRESETS[preset]
    rng = random.Random(seed)
    rows: List[List[float]] = []
    labels: List[float] = []

    for _, bf in structured_suite():
        if cfg["n_min"] <= bf.n <= cfg["n_max"]:
            collect_from_terms(
                frozenset(anf_monomials(bf)),
                config,
                rows,
                labels,
                max_depth=max_depth,
                child_branch=child_branch,
                label_mode=label_mode,
            )

    for _ in range(cfg["samples"]):
        n = rng.randint(cfg["n_min"], cfg["n_max"])
        if n <= 6 and rng.random() < 0.25:
            bf = random_truth_function(n, rng)
        else:
            term_prob = rng.uniform(0.04, 0.22)
            max_degree = rng.randint(2, min(n, 6))
            bf = random_anf_function(n, rng, term_prob=term_prob, max_degree=max_degree)
        collect_from_terms(
            frozenset(anf_monomials(bf)),
            config,
            rows,
            labels,
            max_depth=max_depth,
            child_branch=child_branch,
            label_mode=label_mode,
        )

    if not rows:
        raise RuntimeError("no training rows collected")
    return torch.tensor(rows, dtype=torch.float32), torch.tensor(labels, dtype=torch.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gate-mode", choices=["mct", "logical_and"], default="mct")
    ap.add_argument("--label-mode", choices=["immediate", "rollout"], default="immediate")
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--child-branch", type=int, default=3)
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--out", default=str(THIS_DIR / "models" / "action_scorer.pt"))
    args = ap.parse_args()

    config = SearchConfig(max_factor_ancilla=4, max_factor_size=5, candidate_top_k=24, gate_mode=args.gate_mode)
    x, y = build_dataset(args.preset, args.seed, config, args.label_mode, args.max_depth, args.child_branch)
    mean = x.mean(dim=0)
    std = x.std(dim=0).clamp_min(1e-6)
    x = (x - mean) / std

    rng = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(x.shape[0], generator=rng)
    split = max(1, int(0.85 * x.shape[0]))
    train_idx, valid_idx = perm[:split], perm[split:]

    device = default_device()
    model = ActionNet(hidden=args.hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss()
    cfg = PRESETS[args.preset]

    x_train, y_train = x[train_idx].to(device), y[train_idx].to(device)
    x_valid, y_valid = x[valid_idx].to(device), y[valid_idx].to(device)

    best_state = None
    best_valid = float("inf")
    for epoch in range(cfg["epochs"]):
        model.train()
        pred = model(x_train)
        loss = loss_fn(pred, y_train)
        opt.zero_grad()
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            valid = loss_fn(model(x_valid), y_valid).item() if len(valid_idx) else loss.item()
        if valid < best_valid:
            best_valid = valid
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 10 == 0:
            print(f"epoch={epoch+1} train={loss.item():.4f} valid={valid:.4f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    save_model(args.out, model.cpu(), mean, std)
    print(f"rows={x.shape[0]} valid_loss={best_valid:.4f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
