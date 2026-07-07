#!/usr/bin/env python3
"""Diagnose high-dimensional linear-pair root-action ranking.

This script evaluates the gap between the cheap heuristic ordering used by the
high-dimensional linear-pair guard and a bounded one-step oracle that scores a
wider root-action set using actual greedy child plans.  It is intentionally not
a global optimum: the goal is to quantify whether a learned root-action ranker
has useful headroom on large ANF instances.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import time
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from anf_utils import anf_monomials, shifted_function
from factor_plan import (
    FactorAction,
    Plan,
    SearchConfig,
    direct_plan,
    emit_plan_to_circuit,
    factor_cost,
    greedy_plan,
    linear_factor_actions,
    verify_oracle,
)
from neural_policy import NeuralScorer
from resource_model import ResourceCost, ResourceWeights
from run_experiments import make_suite
from synthesizers import _direct_screened_polarities


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def wrap_cost(polarity: int) -> ResourceCost:
    wraps = 2 * int(polarity).bit_count()
    return ResourceCost(gates=wraps, depth=wraps)


def plan_key(plan: Plan, weights: ResourceWeights) -> tuple[float, int, int, int, int]:
    return (plan.cost.score(weights), plan.cost.T, plan.cost.CNOT, plan.cost.depth, plan.cost.peak_ancilla)


def scored_plan_key(item: tuple[Plan, int], weights: ResourceWeights) -> tuple[float, int, int, int, int]:
    plan, polarity = item
    cost = plan.cost + wrap_cost(polarity)
    return (cost.score(weights), cost.T, cost.CNOT, cost.depth, cost.peak_ancilla)


def evaluate_action(
    terms: frozenset[int],
    action: FactorAction,
    config: SearchConfig,
    memo: dict[tuple[frozenset[int], int, int], Plan],
    rest_direct_limit: int,
) -> Plan:
    child_config = replace(config, greedy_eval_limit=1)
    group = greedy_plan(
        action.residuals,
        prefix_len=1,
        live_factor_ancilla=1,
        config=child_config,
        memo=memo,
    )
    if len(action.rest) > rest_direct_limit:
        rest = direct_plan(action.rest, prefix_len=0, live_factor_ancilla=0, config=child_config)
    else:
        rest = greedy_plan(
            action.rest,
            prefix_len=0,
            live_factor_ancilla=0,
            config=child_config,
            memo=memo,
        )
    cost = factor_cost(action, group, rest, live_factor_ancilla=0, config=config)
    return Plan(
        "linear_factor",
        terms,
        cost,
        factor=action.factor,
        group=group,
        rest=rest,
        affine_const=action.affine_const,
    )


def best_over_indices(
    terms: frozenset[int],
    actions: list[FactorAction],
    indices: Iterable[int],
    config: SearchConfig,
    memo: dict[tuple[frozenset[int], int, int], Plan],
    rest_direct_limit: int,
) -> tuple[Plan, int]:
    best: tuple[Plan, int] | None = None
    for idx in indices:
        if idx < 0 or idx >= len(actions):
            continue
        plan = evaluate_action(terms, actions[idx], config, memo, rest_direct_limit)
        item = (plan, idx)
        if best is None or plan_key(item[0], config.weights) < plan_key(best[0], config.weights):
            best = item
    if best is None:
        raise ValueError("no action index selected")
    return best


def neural_order(
    actions: list[FactorAction],
    terms: frozenset[int],
    config: SearchConfig,
    scorer: NeuralScorer,
    direct_score: float,
) -> list[int]:
    from factor_plan import action_features

    features = [
        action_features(
            terms,
            0,
            0,
            action.factor,
            action.group,
            action.residuals,
            action.rest,
            action.immediate_gain,
            direct_score,
        )
        for action in actions
    ]
    scores = scorer.score_many(features)
    ranked = sorted(
        range(len(actions)),
        key=lambda i: (-(actions[i].prior + config.neural_prior_weight * float(scores[i])), -actions[i].immediate_gain, i),
    )
    return ranked


def row_from_plan(
    *,
    name: str,
    n: int,
    method: str,
    plan: Plan,
    polarity: int,
    action_rank: int | None,
    elapsed: float,
    correct: bool,
    error: str = "",
) -> dict[str, object]:
    cost = plan.cost + wrap_cost(polarity)
    return {
        "name": name,
        "n": n,
        "method": method,
        "polarity": polarity,
        "action_rank": "" if action_rank is None else action_rank,
        "T": cost.T,
        "CNOT": cost.CNOT,
        "depth": cost.depth,
        "gates": cost.gates,
        "explicit_ancilla": cost.explicit_ancilla,
        "peak_ancilla": cost.peak_ancilla,
        "score": cost.score(ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)),
        "terms": len(plan.terms),
        "correct": correct,
        "time_s": elapsed,
        "error": error,
    }


def compare(rows: list[dict[str, str]], target: str, baseline: str, metric: str) -> tuple[int, int, int, float]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("error") or row.get("correct") not in {"True", "true", "1", True}:  # type: ignore[comparison-overlap]
            continue
        by_name.setdefault(str(row["name"]), {})[str(row["method"])] = row
    wins = losses = ties = 0
    changes = []
    for table in by_name.values():
        if target not in table or baseline not in table:
            continue
        new = float(table[target][metric])
        old = float(table[baseline][metric])
        changes.append(pct(new, old))
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties, statistics.mean(changes) if changes else float("nan")


def write_outputs(
    rows: list[dict[str, object]],
    raw_path: Path,
    summary_path: Path,
    analysis_path: Path,
    latex_path: Path,
    model_label: str,
) -> None:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "n",
        "method",
        "polarity",
        "action_rank",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "score",
        "terms",
        "correct",
        "time_s",
        "error",
    ]
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    str_rows = [{k: str(v) for k, v in row.items()} for row in rows]
    methods = sorted({str(row["method"]) for row in rows})
    summary_rows: list[dict[str, str]] = []
    for method in methods:
        items = [row for row in rows if row["method"] == method and row.get("correct") is True and not row.get("error")]
        if not items:
            continue
        summary_rows.append(
            {
                "method": method,
                "functions": str(len(items)),
                "mean_T": f"{statistics.mean(float(row['T']) for row in items):.4f}",
                "mean_CNOT": f"{statistics.mean(float(row['CNOT']) for row in items):.4f}",
                "mean_depth": f"{statistics.mean(float(row['depth']) for row in items):.4f}",
                "mean_peak_ancilla": f"{statistics.mean(float(row['peak_ancilla']) for row in items):.4f}",
                "mean_score": f"{statistics.mean(float(row['score']) for row in items):.4f}",
                "mean_time_s": f"{statistics.mean(float(row['time_s']) for row in items):.6f}",
            }
        )
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    comparisons = [
        ("root_beam4_oracle_eval", "root_heuristic_top1"),
        ("root_oracle12", "root_beam4_oracle_eval"),
        ("root_oracle24", "root_beam4_oracle_eval"),
        ("root_oracle24", "root_heuristic_top1"),
    ]
    if any(row["method"] == "root_neural_top4" for row in rows):
        comparisons.append(("root_neural_top4", "root_beam4_oracle_eval"))
        comparisons.append(("root_oracle24", "root_neural_top4"))

    lines = [
        "# High-dimensional root-action oracle analysis",
        "",
        "This diagnostic evaluates whether high-dimensional CNOT-only linear-pair",
        "root actions contain useful ranking headroom beyond the cheap heuristic.",
        "Each action is scored by building actual greedy child plans, so the",
        "oracle rows are a bounded one-step teacher signal rather than a global",
        "reversible-circuit optimum.",
        "",
        f"Model for optional neural ordering: `{model_label}`.",
        "",
        f"Rows: {len(rows)}; errors: {sum(1 for row in rows if row.get('error'))}; incorrect: {sum(1 for row in rows if row.get('correct') is not True)}.",
        "",
        "## Mean resources",
        "",
        "| method | functions | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {method} | {functions} | {mean_T} | {mean_CNOT} | {mean_depth} | {mean_peak_ancilla} | {mean_score} | {mean_time_s} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Pairwise comparisons",
            "",
            "| target | baseline | metric | W/L/T | mean relative |",
            "|---|---|---|---:|---:|",
        ]
    )
    comparison_rows = []
    for target, base in comparisons:
        for metric in ["score", "T", "CNOT"]:
            wins, losses, ties, mean = compare(str_rows, target, base, metric)
            comparison_rows.append((target, base, metric, wins, losses, ties, mean))
            lines.append(f"| {target} | {base} | {metric} | {wins}/{losses}/{ties} | {mean:+.2f}% |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `root_beam4_oracle_eval` measures the best action available inside the current heuristic top-4 window after true child evaluation.",
            "- `root_oracle12` and `root_oracle24` measure how much extra quality is available if a wider root-action set can be ranked correctly.",
            "- Positive headroom here is a supervised target for a stronger high-dimensional learned root-action ranker; it should not be presented as a final synthesis optimum.",
        ]
    )
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latex_path.parent.mkdir(parents=True, exist_ok=True)
    selected = [
        row
        for row in comparison_rows
        if row[2] == "score"
        and (row[0], row[1])
        in {
            ("root_oracle12", "root_beam4_oracle_eval"),
            ("root_oracle24", "root_beam4_oracle_eval"),
            ("root_oracle24", "root_heuristic_top1"),
            ("root_neural_top4", "root_beam4_oracle_eval"),
        }
    ]
    table = [
        r"\begin{tabular}{llrr}",
        r"\toprule",
        r"Target & Baseline & Score W/L/T & Mean $\Delta$ score \\",
        r"\midrule",
    ]
    labels = {
        "root_heuristic_top1": "heuristic top-1",
        "root_beam4_oracle_eval": "heuristic top-4",
        "root_oracle12": "oracle top-12",
        "root_oracle24": "oracle top-24",
        "root_neural_top4": "neural top-4",
    }
    for target, base, _metric, wins, losses, ties, mean in selected:
        table.append(f"{labels.get(target, target)} & {labels.get(base, base)} & {wins}/{losses}/{ties} & ${mean:+.2f}\\%$ \\\\")
    table.extend([r"\bottomrule", r"\end{tabular}"])
    latex_path.write_text("\n".join(table) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="highdim_neural_prior")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-functions", type=int, default=12)
    parser.add_argument("--candidate-width", type=int, default=24)
    parser.add_argument("--rest-direct-limit", type=int, default=450)
    parser.add_argument("--screen-budget", type=int, default=48)
    parser.add_argument("--screen-top-k", type=int, default=1)
    parser.add_argument("--neural-prior-weight", type=float, default=10.0)
    parser.add_argument("--model", default=str(THIS_DIR / "models" / "linear_action_scorer_highdim.pt"))
    parser.add_argument("--raw", type=Path, default=RESULTS / "raw_highdim_root_action_oracle.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_highdim_root_action_oracle.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_highdim_root_action_oracle.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "highdim_root_action_oracle.tex")
    args = parser.parse_args()

    weights = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
    config = SearchConfig(
        weights=weights,
        max_factor_ancilla=4,
        max_factor_size=5,
        candidate_top_k=24,
        min_factor_count=2,
        use_relative_phase=True,
        mcts_simulations=24,
        neural_mcts_simulations=32,
        max_polarities=12,
        gate_mode="logical_and",
        neural_prior_weight=args.neural_prior_weight,
    )
    scorer = NeuralScorer(args.model) if args.model and Path(args.model).exists() else None
    model_label = args.model if scorer is not None else ""
    rows: list[dict[str, object]] = []
    suite = list(make_suite(args.preset, args.seed))[: args.max_functions]

    for index, (name, bf) in enumerate(suite, start=1):
        start = time.time()
        try:
            ranked = _direct_screened_polarities(
                bf,
                config,
                args.seed,
                budget=args.screen_budget,
                top_k=args.screen_top_k,
            )
            if not ranked:
                raise RuntimeError("no screened polarity")
            _score, polarity, terms, _ = ranked[0]
            shifted_terms = frozenset(terms)
            direct = direct_plan(shifted_terms, 0, 0, config)
            direct_cost = direct.cost + wrap_cost(polarity)
            direct_score = direct_cost.score(weights)
            rows.append(
                row_from_plan(
                    name=name,
                    n=bf.n,
                    method="root_direct",
                    plan=direct,
                    polarity=polarity,
                    action_rank=None,
                    elapsed=time.time() - start,
                    correct=verify_oracle(emit_plan_to_circuit(direct, bf.n, 0, polarity=polarity), bf),
                )
            )

            actions = linear_factor_actions(
                shifted_terms,
                0,
                0,
                config,
                action_width=args.candidate_width,
            )
            if not actions:
                continue

            memo: dict[tuple[frozenset[int], int, int], Plan] = {}
            variants: list[tuple[str, list[int]]] = [
                ("root_heuristic_top1", [0]),
                ("root_beam4_oracle_eval", list(range(min(4, len(actions))))),
                ("root_oracle12", list(range(min(12, len(actions))))),
                ("root_oracle24", list(range(min(args.candidate_width, len(actions))))),
            ]
            if scorer is not None:
                order = neural_order(actions, shifted_terms, config, scorer, direct_score)
                variants.append(("root_neural_top4", order[: min(4, len(order))]))

            for method, indices in variants:
                before = time.time()
                plan, action_idx = best_over_indices(
                    shifted_terms,
                    actions,
                    indices,
                    config,
                    memo,
                    args.rest_direct_limit,
                )
                circ = emit_plan_to_circuit(
                    plan,
                    bf.n,
                    min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
                    polarity=polarity,
                )
                rows.append(
                    row_from_plan(
                        name=name,
                        n=bf.n,
                        method=method,
                        plan=plan,
                        polarity=polarity,
                        action_rank=action_idx,
                        elapsed=time.time() - before,
                        correct=verify_oracle(circ, bf),
                    )
                )
            print(f"{index}/{len(suite)} {name} actions={len(actions)} elapsed={time.time() - start:.2f}s")
        except Exception as exc:  # noqa: BLE001 - keep diagnostic rows explicit
            rows.append(
                {
                    "name": name,
                    "n": bf.n,
                    "method": "error",
                    "polarity": "",
                    "action_rank": "",
                    "T": "",
                    "CNOT": "",
                    "depth": "",
                    "gates": "",
                    "explicit_ancilla": "",
                    "peak_ancilla": "",
                    "score": "",
                    "terms": "",
                    "correct": False,
                    "time_s": time.time() - start,
                    "error": repr(exc),
                }
            )
            print(f"{index}/{len(suite)} {name} error={exc!r}")

    write_outputs(rows, args.raw, args.summary, args.analysis, args.latex_out, model_label)
    print(f"wrote {args.raw}")
    print(f"wrote {args.analysis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
