#!/usr/bin/env python3
"""Train a small neural prior for ANF factor actions."""
from __future__ import annotations

import argparse
import random
import statistics
from dataclasses import replace
from pathlib import Path
from typing import List, Tuple

import torch
from torch import nn

from anf_utils import anf_monomials, random_anf_function, random_truth_function, structured_suite
from factor_plan import (
    SearchConfig,
    action_features,
    candidate_actions,
    direct_plan,
    factor_cost,
    greedy_plan,
    linear_factor_actions,
)
from neural_policy import ActionNet, default_device, save_model


THIS_DIR = Path(__file__).resolve().parent


PRESETS = {
    "smoke": {"samples": 80, "epochs": 30, "n_min": 3, "n_max": 7},
    "rollout": {"samples": 520, "epochs": 60, "n_min": 3, "n_max": 9},
    "linear_highdim": {"samples": 260, "epochs": 50, "n_min": 8, "n_max": 14},
    "linear_root_teacher": {"samples": 140, "epochs": 70, "n_min": 10, "n_max": 14},
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
    action_family: str = "factor",
    greedy_memo: dict | None = None,
    root_teacher_width: int = 24,
    rest_direct_limit: int = 450,
) -> None:
    greedy_memo = {} if greedy_memo is None else greedy_memo
    direct_score = direct_plan(terms, prefix_len, live_factor_ancilla, config).score(config.weights)
    if action_family == "linear":
        actions = linear_factor_actions(
            terms,
            prefix_len,
            live_factor_ancilla,
            config,
            action_width=max(2, min(config.candidate_top_k, 24)),
        )
    else:
        actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config)
    if not actions:
        return
    if label_mode == "root_teacher":
        teacher_actions = actions[: max(1, min(root_teacher_width, len(actions)))]
        child_config = replace(config, greedy_eval_limit=1)
        action_scores = []
        for action in teacher_actions:
            group = greedy_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                child_config,
                memo=greedy_memo,
            )
            if len(action.rest) > rest_direct_limit:
                rest = direct_plan(action.rest, prefix_len, live_factor_ancilla, child_config)
            else:
                rest = greedy_plan(
                    action.rest,
                    prefix_len,
                    live_factor_ancilla,
                    child_config,
                    memo=greedy_memo,
                )
            action_scores.append(factor_cost(action, group, rest, live_factor_ancilla, config).score(config.weights))
        mean_score = statistics.mean(action_scores)
        spread = statistics.pstdev(action_scores)
        for action, action_score in zip(teacher_actions, action_scores):
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
            if spread <= 1e-9:
                label = 0.0
            else:
                label = (mean_score - action_score) / spread
            labels.append(max(-2.0, min(2.0, label)))
    else:
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
            action_family,
            greedy_memo,
            root_teacher_width,
            rest_direct_limit,
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
            action_family,
            greedy_memo,
            root_teacher_width,
            rest_direct_limit,
        )


def build_dataset(
    preset: str,
    seed: int,
    config: SearchConfig,
    label_mode: str,
    max_depth: int,
    child_branch: int,
    action_family: str,
    root_teacher_width: int,
    rest_direct_limit: int,
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
                action_family=action_family,
                root_teacher_width=root_teacher_width,
                rest_direct_limit=rest_direct_limit,
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
            action_family=action_family,
            root_teacher_width=root_teacher_width,
            rest_direct_limit=rest_direct_limit,
        )

    if not rows:
        raise RuntimeError("no training rows collected")
    return torch.tensor(rows, dtype=torch.float32), torch.tensor(labels, dtype=torch.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gate-mode", choices=["mct", "logical_and"], default="mct")
    ap.add_argument("--label-mode", choices=["immediate", "rollout", "root_teacher"], default="immediate")
    ap.add_argument("--action-family", choices=["factor", "linear"], default="factor")
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--child-branch", type=int, default=3)
    ap.add_argument("--root-teacher-width", type=int, default=24)
    ap.add_argument("--rest-direct-limit", type=int, default=450)
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--out", default=str(THIS_DIR / "models" / "action_scorer.pt"))
    args = ap.parse_args()

    config = SearchConfig(max_factor_ancilla=4, max_factor_size=5, candidate_top_k=24, gate_mode=args.gate_mode)
    x, y = build_dataset(
        args.preset,
        args.seed,
        config,
        args.label_mode,
        args.max_depth,
        args.child_branch,
        args.action_family,
        args.root_teacher_width,
        args.rest_direct_limit,
    )
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
