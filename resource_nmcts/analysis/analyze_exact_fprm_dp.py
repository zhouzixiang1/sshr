#!/usr/bin/env python3
"""Exact bounded FPRM factorization analysis for small Boolean functions.

This script solves the same fixed-polarity ANF/FPRM factor-plan model used by
the heuristic search, but replaces greedy/beam/MCTS choices with dynamic
programming over every monomial factor and CNOT-only linear-pair factor.  It is
intended as a small exact slice, not a scalable synthesis backend.
"""
from __future__ import annotations

import argparse
import csv
import functools
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from src.anf_utils import anf_monomials, shifted_function
from src.factor_plan import (
    FactorAction,
    Plan,
    SearchConfig,
    action_features,
    direct_plan,
    factor_cost,
    emit_plan_to_circuit,
    verify_oracle,
)
from src.resource_model import ResourceCost, ResourceWeights, direct_cost_for_terms, gate_cost, gate_uncompute_cost
from run_experiments import make_suite
from src.synthesizers import synthesize


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"
METHOD = "and_exact_fprm_dp"
METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]


def bits(mask: int) -> Iterable[int]:
    while mask:
        low = mask & -mask
        yield low
        mask ^= low


def subsets(mask: int, min_size: int, max_size: int) -> Iterable[int]:
    bit_values = list(bits(mask))
    limit = min(max_size, len(bit_values))
    from itertools import combinations

    for size in range(min_size, limit + 1):
        for combo in combinations(bit_values, size):
            out = 0
            for bit in combo:
                out |= bit
            yield out


def linear_resource(factor: int, live_factor_ancilla: int) -> ResourceCost:
    width = int(factor).bit_count()
    live = live_factor_ancilla + 1
    return ResourceCost(CNOT=width, gates=width, depth=width, explicit_ancilla=live, peak_ancilla=live)


def all_monomial_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
) -> list[FactorAction]:
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < config.min_factor_count:
        return []
    counts: dict[int, int] = {}
    for term in terms:
        if int(term).bit_count() < 2:
            continue
        for factor in subsets(int(term), 2, config.max_factor_size):
            counts[factor] = counts.get(factor, 0) + 1

    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: list[FactorAction] = []
    for factor, count in counts.items():
        if count < config.min_factor_count:
            continue
        group_items: list[int] = []
        residual_items: list[int] = []
        rest_items: list[int] = []
        for term in terms:
            if (int(term) & factor) == factor:
                group_items.append(int(term))
                residual_items.append(int(term) ^ factor)
            else:
                rest_items.append(int(term))
        residuals = frozenset(residual_items)
        if not residuals:
            continue
        group = frozenset(group_items)
        rest = frozenset(rest_items)
        group_direct = direct_cost_for_terms(
            group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        residual_direct = direct_cost_for_terms(
            residuals, prefix_len + 1, live_factor_ancilla + 1, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        compute = gate_cost(
            factor.bit_count(),
            live_factor_ancilla,
            use_relative_phase=config.use_relative_phase,
            alloc_target_ancilla=True,
            gate_mode=config.gate_mode,
        )
        uncompute = gate_uncompute_cost(
            factor.bit_count(),
            live_factor_ancilla,
            use_relative_phase=config.use_relative_phase,
            alloc_target_ancilla=True,
            gate_mode=config.gate_mode,
        )
        gain = group_direct - compute.score(config.weights) - uncompute.score(config.weights) - residual_direct
        actions.append(
            FactorAction(
                factor=factor,
                group=group,
                residuals=residuals,
                rest=rest,
                immediate_gain=gain,
                prior=gain / max(direct_total, 1.0),
            )
        )
    return actions


def all_linear_pair_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
) -> list[FactorAction]:
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < 2 * config.min_factor_count:
        return []
    n_bits = max((int(term).bit_length() for term in terms), default=0)
    if n_bits < 2:
        return []

    support_by_residual: dict[int, int] = {}
    for term in terms:
        for bit in bits(int(term)):
            residual = int(term) ^ bit
            support_by_residual[residual] = support_by_residual.get(residual, 0) | bit

    residuals_by_factor: dict[int, set[int]] = {}
    for residual, support in support_by_residual.items():
        available = support & ~residual
        for factor in subsets(available, 2, 2):
            residuals_by_factor.setdefault(factor, set()).add(residual)

    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: list[FactorAction] = []
    for factor, residuals_raw in residuals_by_factor.items():
        if len(residuals_raw) < config.min_factor_count:
            continue
        factor_bits = list(bits(factor))
        group_terms = {residual | bit for residual in residuals_raw for bit in factor_bits}
        group = frozenset(group_terms)
        residuals = frozenset(residuals_raw)
        rest = frozenset(int(term) for term in terms if int(term) not in group_terms)
        group_direct = direct_cost_for_terms(
            group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        residual_direct = direct_cost_for_terms(
            residuals, prefix_len + 1, live_factor_ancilla + 1, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        compute = linear_resource(factor, live_factor_ancilla)
        gain = group_direct - compute.score(config.weights) - compute.score(config.weights) - residual_direct
        actions.append(
            FactorAction(
                factor=factor,
                group=group,
                residuals=residuals,
                rest=rest,
                immediate_gain=gain,
                prior=gain / max(direct_total, 1.0),
                linear=True,
            )
        )
    return actions


def better(lhs: Plan, rhs: Plan, weights: ResourceWeights) -> bool:
    left = lhs.cost.score(weights)
    right = rhs.cost.score(weights)
    if left != right:
        return left < right
    return (
        lhs.cost.T,
        lhs.cost.CNOT,
        lhs.cost.depth,
        lhs.cost.peak_ancilla,
        lhs.cost.gates,
    ) < (
        rhs.cost.T,
        rhs.cost.CNOT,
        rhs.cost.depth,
        rhs.cost.peak_ancilla,
        rhs.cost.gates,
    )


def exact_plan(terms: frozenset[int], config: SearchConfig) -> tuple[Plan, int]:
    calls = 0

    @functools.lru_cache(maxsize=None)
    def solve(state: frozenset[int], prefix_len: int, live_factor_ancilla: int) -> Plan:
        nonlocal calls
        calls += 1
        best = direct_plan(state, prefix_len, live_factor_ancilla, config)
        actions = all_monomial_actions(state, prefix_len, live_factor_ancilla, config)
        actions.extend(all_linear_pair_actions(state, prefix_len, live_factor_ancilla, config))
        for action in actions:
            group_plan = solve(action.residuals, prefix_len + 1, live_factor_ancilla + 1)
            rest_plan = solve(action.rest, prefix_len, live_factor_ancilla)
            plan = Plan(
                "linear_factor" if action.linear else "factor",
                state,
                factor_cost(action, group_plan, rest_plan, live_factor_ancilla, config),
                factor=action.factor,
                group=group_plan,
                rest=rest_plan,
                affine_const=action.affine_const,
            )
            if better(plan, best, config.weights):
                best = plan
        return best

    return solve(terms, 0, 0), calls


def wrap_cost(polarity: int) -> ResourceCost:
    wraps = 2 * int(polarity).bit_count()
    return ResourceCost(gates=wraps, depth=wraps)


def exact_for_function(name: str, bf, config: SearchConfig) -> dict[str, str | int | float | bool]:
    start = time.time()
    best: tuple[float, int, frozenset[int], Plan, ResourceCost, int] | None = None
    for polarity in range(1 << bf.n):
        shifted = shifted_function(bf, polarity)
        terms = frozenset(anf_monomials(shifted))
        plan, states = exact_plan(terms, config)
        cost = plan.cost + wrap_cost(polarity)
        score = cost.score(config.weights)
        item = (score, polarity, terms, plan, cost, states)
        if best is None or (score, cost.T, cost.CNOT, cost.depth, cost.peak_ancilla) < (
            best[0],
            best[4].T,
            best[4].CNOT,
            best[4].depth,
            best[4].peak_ancilla,
        ):
            best = item
    assert best is not None
    _, polarity, terms, plan, cost, states = best
    circ = emit_plan_to_circuit(
        plan,
        bf.n,
        min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
        polarity=polarity,
    )
    correct = verify_oracle(circ, bf)
    row = {
        "name": name,
        "n": bf.n,
        "truth_table_hex": f"{bf.truth_table:X}",
        "anf_terms": len(anf_monomials(bf)),
        "method": METHOD,
        "correct": correct,
        "T": cost.T,
        "CNOT": cost.CNOT,
        "gates": cost.gates,
        "depth": cost.depth,
        "explicit_ancilla": cost.explicit_ancilla,
        "peak_ancilla": cost.peak_ancilla,
        "score": cost.score(config.weights),
        "terms": len(terms),
        "n_qubits": circ.n_qubits,
        "polarity": polarity,
        "dp_states": states,
        "time_s": time.time() - start,
        "skipped": "",
        "error": "",
    }
    return row


def load_usable(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        row
        for row in rows
        if not row.get("error")
        and not row.get("skipped")
        and str(row.get("correct", "True")) != "False"
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paired(rows: list[dict[str, str]], target: str, baseline: str) -> list[tuple[dict[str, str], dict[str, str]]]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        by_name.setdefault(row["name"], {})[row["method"]] = row
    return [(table[target], table[baseline]) for table in by_name.values() if target in table and baseline in table]


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def compare_rows(rows: list[dict[str, str]], target: str, baseline: str) -> dict[str, str]:
    pairs = paired(rows, target, baseline)
    out = {"target": target, "baseline": baseline, "pairs": str(len(pairs))}
    for metric in METRICS:
        wins = losses = ties = 0
        rels: list[float] = []
        target_vals: list[float] = []
        baseline_vals: list[float] = []
        for target_row, baseline_row in pairs:
            target_value = float(target_row[metric])
            baseline_value = float(baseline_row[metric])
            target_vals.append(target_value)
            baseline_vals.append(baseline_value)
            rels.append(pct(target_value, baseline_value))
            if target_value < baseline_value:
                wins += 1
            elif target_value > baseline_value:
                losses += 1
            else:
                ties += 1
        prefix = metric.lower()
        out[f"{prefix}_wlt"] = f"{wins}/{losses}/{ties}"
        out[f"{prefix}_relative_pct"] = f"{(sum(rels) / len(rels)):+.2f}" if rels else ""
        out[f"{prefix}_target_mean"] = f"{(sum(target_vals) / len(target_vals)):.2f}" if target_vals else ""
        out[f"{prefix}_baseline_mean"] = f"{(sum(baseline_vals) / len(baseline_vals)):.2f}" if baseline_vals else ""
    return out


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_")


def write_latex(path: Path, comparisons: list[dict[str, str]]) -> None:
    labels = {
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"\paretomethod{}",
        "and_esop_milp": r"ESOP MILP",
        "external_sshr_i_cnot": r"SSHR-I CNOT",
        "external_sshr_i_t": r"SSHR-I T",
        METHOD: r"Exact FPRM-DP",
    }
    selected = [
        ("and_resource_nmcts", METHOD),
        ("and_pareto_resource_nmcts", METHOD),
        (METHOD, "and_esop_milp"),
        (METHOD, "external_sshr_i_cnot"),
        (METHOD, "external_sshr_i_t"),
    ]
    by_pair = {(row["target"], row["baseline"]): row for row in comparisons}
    lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Comparison & Pairs & Score W/L/T & Mean $\Delta$ score \\",
        r"\midrule",
    ]
    for target, baseline in selected:
        row = by_pair.get((target, baseline))
        if not row:
            continue
        label = f"{labels.get(target, latex_escape(target))} vs {labels.get(baseline, latex_escape(baseline))}"
        lines.append(
            f"{label} & {row['pairs']} & {row['score_wlt']} & ${float(row['score_relative_pct']):+.2f}\\%$ \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown(path: Path, raw_rows: list[dict], comparisons: list[dict[str, str]]) -> None:
    errors = [row for row in raw_rows if row.get("error")]
    skipped = [row for row in raw_rows if row.get("skipped")]
    lines = [
        "# Exact FPRM-DP Analysis",
        "",
        (
            "This exact slice solves a bounded fixed-polarity FPRM factorization "
            "model with dynamic programming over all monomial factors and "
            "CNOT-only linear-pair factors.  It is exact only for this model; "
            "it is not a global reversible-circuit optimum."
        ),
        "",
        f"Rows: {len(raw_rows)}; errors: {len(errors)}; skipped: {len(skipped)}.",
        "",
        "## Mean Exact Resources",
        "",
        "| n | functions | mean T | mean CNOT | mean peak ancilla | mean score | mean time s | mean DP states |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    by_n: dict[int, list[dict]] = {}
    for row in raw_rows:
        if not row.get("error") and not row.get("skipped"):
            by_n.setdefault(int(row["n"]), []).append(row)
    for n, items in sorted(by_n.items()):
        def mean_value(key: str) -> float:
            return sum(float(row[key]) for row in items) / len(items)

        lines.append(
            f"| {n} | {len(items)} | {mean_value('T'):.2f} | {mean_value('CNOT'):.2f} | "
            f"{mean_value('peak_ancilla'):.2f} | {mean_value('score'):.2f} | "
            f"{mean_value('time_s'):.3f} | {mean_value('dp_states'):.1f} |"
        )
    lines.extend(
        [
            "",
            "## Matched Comparisons",
            "",
            "| target | baseline | pairs | score W/L/T | mean score change | mean T change | mean CNOT change |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["target"],
                    row["baseline"],
                    row["pairs"],
                    row["score_wlt"],
                    f"{float(row['score_relative_pct']):+.2f}%" if row["score_relative_pct"] else "",
                    f"{float(row['t_relative_pct']):+.2f}%" if row["t_relative_pct"] else "",
                    f"{float(row['cnot_relative_pct']):+.2f}%" if row["cnot_relative_pct"] else "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Exact FPRM-DP is a same-model optimum for the bounded fixed-polarity ANF/FPRM factor search, so it measures how much room remains inside this local search family.",
            "- If Resource/Pareto rows beat exact FPRM-DP on some functions, that means their portfolio found a circuit outside this exact FPRM-DP model, not that the exact solver failed.",
            "- This slice is intentionally restricted to n<=4 because the exact state space grows over term subsets, polarities, and live factor ancilla.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_exact_fprm_dp.csv")
    parser.add_argument("--summary-out", type=Path, default=RESULTS / "summary_exact_fprm_dp.csv")
    parser.add_argument("--analysis-out", type=Path, default=RESULTS / "analysis_exact_fprm_dp.md")
    parser.add_argument("--latex-out", type=Path, default=PAPER_TABLES / "exact_fprm_dp.tex")
    args = parser.parse_args(list(argv) if argv is not None else None)

    weights = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
    config = SearchConfig(
        weights=weights,
        max_factor_ancilla=4,
        max_factor_size=5,
        candidate_top_k=64,
        min_factor_count=2,
        use_relative_phase=True,
        gate_mode="logical_and",
    )
    suite = [(name, bf) for name, bf in make_suite("traditional_resource", args.seed) if bf.n <= args.max_n]

    raw_rows: list[dict] = []
    for index, (name, bf) in enumerate(suite, 1):
        print(f"{index}/{len(suite)} {name}", flush=True)
        try:
            raw_rows.append(exact_for_function(name, bf, config))
        except Exception as exc:
            raw_rows.append(
                {
                    "name": name,
                    "n": bf.n,
                    "truth_table_hex": f"{bf.truth_table:X}",
                    "anf_terms": len(anf_monomials(bf)),
                    "method": METHOD,
                    "correct": False,
                    "skipped": "",
                    "error": repr(exc),
                }
            )
    write_csv(args.raw_out, raw_rows)

    rows_for_comparison = [dict(row) for row in raw_rows]
    rows_for_comparison.extend(load_usable(RESULTS / "raw_traditional_resource.csv"))
    rows_for_comparison.extend(load_usable(RESULTS / "raw_external_traditional_resource_n4.csv"))
    comparisons = [
        compare_rows(rows_for_comparison, "and_resource_nmcts", METHOD),
        compare_rows(rows_for_comparison, "and_pareto_resource_nmcts", METHOD),
        compare_rows(rows_for_comparison, METHOD, "direct_anf"),
        compare_rows(rows_for_comparison, METHOD, "and_direct_anf"),
        compare_rows(rows_for_comparison, METHOD, "and_esop_milp"),
        compare_rows(rows_for_comparison, METHOD, "external_sshr_i_cnot"),
        compare_rows(rows_for_comparison, METHOD, "external_sshr_i_t"),
        compare_rows(rows_for_comparison, "and_resource_nmcts", "external_sshr_i_cnot"),
        compare_rows(rows_for_comparison, "and_resource_nmcts", "external_sshr_i_t"),
    ]
    write_csv(args.summary_out, comparisons)
    write_markdown(args.analysis_out, raw_rows, comparisons)
    write_latex(args.latex_out, comparisons)
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary_out}")
    print(f"wrote {args.analysis_out}")
    print(f"wrote {args.latex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
