#!/usr/bin/env python3
"""Run term-set scale tests for Boolean-ring screen policies.

The truth-table harness becomes expensive beyond n=20 because it must build
and verify 2^n bits.  This script keeps the logic-level ANF term-set problem
fixed and evaluates screen policies directly on term sets, which is the search
state used by Resource-NMCTS.  It is intended as large-scale structural
evidence, not as a replacement for truth-table verified small/medium tests.
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
from typing import Iterable

import torch

from factor_plan import (
    SearchConfig,
    direct_plan,
    emit_plan_to_circuit,
    linear_pair_screen_plan,
    verify_circuit_anf,
    verify_plan_anf,
)
from resource_model import ResourceWeights
from train_screen_depth_guard import Depth2GuardNet
from train_screen_depth_policy import (
    DEPTHS,
    FEATURE_NAMES,
    DepthPolicyNet,
    generate_terms,
    term_features,
)


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class MethodEval:
    method: str
    score: float
    t_count: int
    cnot: int
    depth: int
    gates: int
    peak_ancilla: int
    time_s: float
    anf_verified: bool
    plan_nodes: int
    plan_mismatches: int
    circuit_anf_verified: bool
    circuit_gates: int
    circuit_max_wire_terms: int
    circuit_mismatches: int


@dataclass(frozen=True)
class TermExample:
    name: str
    n: int
    profile: str
    term_count: int
    features: list[float]
    evals: dict[str, MethodEval]


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


def eval_plan(method: str, plan, elapsed: float, config: SearchConfig, n_inputs: int) -> MethodEval:
    plan_verification = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(plan, n_inputs, config.max_factor_ancilla)
    circuit_verification = verify_circuit_anf(circuit, n_inputs, plan.terms)
    return MethodEval(
        method=method,
        score=plan.score(config.weights),
        t_count=plan.cost.T,
        cnot=plan.cost.CNOT,
        depth=plan.cost.depth,
        gates=plan.cost.gates,
        peak_ancilla=plan.cost.peak_ancilla,
        time_s=elapsed,
        anf_verified=plan_verification.ok,
        plan_nodes=plan_verification.nodes,
        plan_mismatches=plan_verification.mismatches,
        circuit_anf_verified=circuit_verification.ok,
        circuit_gates=circuit_verification.gates,
        circuit_max_wire_terms=circuit_verification.max_wire_terms,
        circuit_mismatches=(
            circuit_verification.input_mismatches
            + circuit_verification.output_mismatch
            + circuit_verification.ancilla_mismatches
        ),
    )


def evaluate_one(task: tuple[int, int, int, str, int]) -> TermExample:
    n, index, seed, profile, action_width = task
    rng = random.Random(seed)
    config = make_config()
    terms = generate_terms(n, rng, profile)
    features = term_features(terms, config)

    evals: dict[str, MethodEval] = {}
    started = time.perf_counter()
    direct = direct_plan(terms, 0, 0, config)
    evals["direct_logical_and"] = eval_plan("direct_logical_and", direct, time.perf_counter() - started, config, n)

    screen_methods = {
        "screen_single": 0,
        "screen_depth1": 1,
        "screen_depth2": 2,
    }
    for method, recursive_depth in screen_methods.items():
        started = time.perf_counter()
        plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=action_width,
            recursive_depth=recursive_depth,
            boolean_ring=True,
        )
        evals[method] = eval_plan(method, plan, time.perf_counter() - started, config, n)

    best_screen = min(
        [evals["screen_single"], evals["screen_depth1"], evals["screen_depth2"]],
        key=lambda ev: (ev.score, ev.time_s),
    )
    all_depth_time = (
        evals["screen_single"].time_s + evals["screen_depth1"].time_s + evals["screen_depth2"].time_s
    )
    evals["adaptive_all_depth"] = MethodEval(
        method="adaptive_all_depth",
        score=best_screen.score,
        t_count=best_screen.t_count,
        cnot=best_screen.cnot,
        depth=best_screen.depth,
        gates=best_screen.gates,
        peak_ancilla=best_screen.peak_ancilla,
        time_s=all_depth_time,
        anf_verified=best_screen.anf_verified,
        plan_nodes=best_screen.plan_nodes,
        plan_mismatches=best_screen.plan_mismatches,
        circuit_anf_verified=best_screen.circuit_anf_verified,
        circuit_gates=best_screen.circuit_gates,
        circuit_max_wire_terms=best_screen.circuit_max_wire_terms,
        circuit_mismatches=best_screen.circuit_mismatches,
    )
    return TermExample(
        name=f"terms_n{n}_{index:04d}_{profile}",
        n=n,
        profile=profile,
        term_count=len(terms),
        features=features,
        evals=evals,
    )


def load_depth_policy(path: Path) -> tuple[DepthPolicyNet, torch.Tensor, torch.Tensor] | None:
    if not path.exists():
        return None
    ckpt = torch.load(path, map_location="cpu")
    hidden = int(ckpt.get("hidden", 96))
    model = DepthPolicyNet(len(FEATURE_NAMES), hidden=hidden)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, torch.tensor(ckpt["mean"], dtype=torch.float32), torch.tensor(ckpt["std"], dtype=torch.float32)


def load_depth2_guard(path: Path) -> tuple[Depth2GuardNet, torch.Tensor, torch.Tensor, float] | None:
    if not path.exists():
        return None
    ckpt = torch.load(path, map_location="cpu")
    if ckpt.get("feature_mode", "static") != "static":
        return None
    hidden = int(ckpt.get("hidden", 96))
    model = Depth2GuardNet(len(FEATURE_NAMES), hidden=hidden)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return (
        model,
        torch.tensor(ckpt["mean"], dtype=torch.float32),
        torch.tensor(ckpt["std"], dtype=torch.float32),
        float(ckpt["threshold"]),
    )


@torch.no_grad()
def add_learned_methods(
    examples: list[TermExample],
    policy_path: Path,
    guard_path: Path,
) -> list[TermExample]:
    policy = load_depth_policy(policy_path)
    guard = load_depth2_guard(guard_path)
    if policy is None and guard is None:
        return examples

    features = torch.tensor([ex.features for ex in examples], dtype=torch.float32)
    policy_depths: list[int] | None = None
    if policy is not None:
        model, mean, std = policy
        logits = model((features - mean) / std)
        policy_depths = [int(v) for v in logits.argmax(dim=1).tolist()]

    guard_depths: list[int] | None = None
    if guard is not None:
        model, mean, std, threshold = guard
        probs = torch.sigmoid(model((features - mean) / std)).tolist()
        guard_depths = [1 if float(p) >= threshold else 2 for p in probs]

    updated: list[TermExample] = []
    for idx, ex in enumerate(examples):
        evals = dict(ex.evals)
        if policy_depths is not None:
            chosen = evals[{0: "screen_single", 1: "screen_depth1", 2: "screen_depth2"}[policy_depths[idx]]]
            evals["depth_policy"] = MethodEval(
                method="depth_policy",
                score=chosen.score,
                t_count=chosen.t_count,
                cnot=chosen.cnot,
                depth=chosen.depth,
                gates=chosen.gates,
                peak_ancilla=chosen.peak_ancilla,
                time_s=chosen.time_s,
                anf_verified=chosen.anf_verified,
                plan_nodes=chosen.plan_nodes,
                plan_mismatches=chosen.plan_mismatches,
                circuit_anf_verified=chosen.circuit_anf_verified,
                circuit_gates=chosen.circuit_gates,
                circuit_max_wire_terms=chosen.circuit_max_wire_terms,
                circuit_mismatches=chosen.circuit_mismatches,
            )
        if guard_depths is not None:
            chosen = evals[{1: "screen_depth1", 2: "screen_depth2"}[guard_depths[idx]]]
            evals["depth2_guard_direct"] = MethodEval(
                method="depth2_guard_direct",
                score=chosen.score,
                t_count=chosen.t_count,
                cnot=chosen.cnot,
                depth=chosen.depth,
                gates=chosen.gates,
                peak_ancilla=chosen.peak_ancilla,
                time_s=chosen.time_s,
                anf_verified=chosen.anf_verified,
                plan_nodes=chosen.plan_nodes,
                plan_mismatches=chosen.plan_mismatches,
                circuit_anf_verified=chosen.circuit_anf_verified,
                circuit_gates=chosen.circuit_gates,
                circuit_max_wire_terms=chosen.circuit_max_wire_terms,
                circuit_mismatches=chosen.circuit_mismatches,
            )
        updated.append(
            TermExample(
                name=ex.name,
                n=ex.n,
                profile=ex.profile,
                term_count=ex.term_count,
                features=ex.features,
                evals=evals,
            )
        )
    return updated


def write_raw(path: Path, examples: list[TermExample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "n",
        "profile",
        "term_count",
        "method",
        "score",
        "T",
        "CNOT",
        "depth",
        "gates",
        "peak_ancilla",
        "time_s",
        "anf_verified",
        "plan_nodes",
        "plan_mismatches",
        "circuit_anf_verified",
        "circuit_gates",
        "circuit_max_wire_terms",
        "circuit_mismatches",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for ex in examples:
            for method, ev in sorted(ex.evals.items()):
                writer.writerow(
                    {
                        "name": ex.name,
                        "n": ex.n,
                        "profile": ex.profile,
                        "term_count": ex.term_count,
                        "method": method,
                        "score": ev.score,
                        "T": ev.t_count,
                        "CNOT": ev.cnot,
                        "depth": ev.depth,
                        "gates": ev.gates,
                        "peak_ancilla": ev.peak_ancilla,
                        "time_s": ev.time_s,
                        "anf_verified": ev.anf_verified,
                        "plan_nodes": ev.plan_nodes,
                        "plan_mismatches": ev.plan_mismatches,
                        "circuit_anf_verified": ev.circuit_anf_verified,
                        "circuit_gates": ev.circuit_gates,
                        "circuit_max_wire_terms": ev.circuit_max_wire_terms,
                        "circuit_mismatches": ev.circuit_mismatches,
                    }
                )


def _comparison(examples: list[TermExample], method: str, baseline: str) -> tuple[int, int, int, float, float]:
    wins = losses = ties = 0
    rel_score: list[float] = []
    rel_time: list[float] = []
    for ex in examples:
        if method not in ex.evals or baseline not in ex.evals:
            continue
        target = ex.evals[method]
        base = ex.evals[baseline]
        if target.score < base.score - 1e-9:
            wins += 1
        elif target.score > base.score + 1e-9:
            losses += 1
        else:
            ties += 1
        rel_score.append((target.score - base.score) / max(base.score, 1.0))
        rel_time.append((target.time_s - base.time_s) / max(base.time_s, 1e-9))
    return (
        wins,
        losses,
        ties,
        statistics.mean(rel_score) if rel_score else 0.0,
        statistics.mean(rel_time) if rel_time else 0.0,
    )


def write_summary(summary_path: Path, analysis_path: Path, table_path: Path, examples: list[TermExample]) -> None:
    methods = sorted({method for ex in examples for method in ex.evals})
    by_n = sorted({ex.n for ex in examples})
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "n",
                "method",
                "functions",
                "mean_terms",
                "mean_T",
                "mean_CNOT",
                "mean_depth",
                "mean_peak_ancilla",
                "mean_score",
                "mean_time_s",
                "verified_rows",
                "mean_plan_nodes",
                "circuit_verified_rows",
                "mean_circuit_gates",
                "mean_circuit_max_wire_terms",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for n in by_n:
            subset = [ex for ex in examples if ex.n == n]
            for method in methods:
                vals = [ex.evals[method] for ex in subset if method in ex.evals]
                if not vals:
                    continue
                writer.writerow(
                    {
                        "n": n,
                        "method": method,
                        "functions": len(vals),
                        "mean_terms": statistics.mean(ex.term_count for ex in subset),
                        "mean_T": statistics.mean(v.t_count for v in vals),
                        "mean_CNOT": statistics.mean(v.cnot for v in vals),
                        "mean_depth": statistics.mean(v.depth for v in vals),
                        "mean_peak_ancilla": statistics.mean(v.peak_ancilla for v in vals),
                        "mean_score": statistics.mean(v.score for v in vals),
                        "mean_time_s": statistics.mean(v.time_s for v in vals),
                        "verified_rows": sum(1 for v in vals if v.anf_verified),
                        "mean_plan_nodes": statistics.mean(v.plan_nodes for v in vals),
                        "circuit_verified_rows": sum(1 for v in vals if v.circuit_anf_verified),
                        "mean_circuit_gates": statistics.mean(v.circuit_gates for v in vals),
                        "mean_circuit_max_wire_terms": statistics.mean(v.circuit_max_wire_terms for v in vals),
                    }
                )

    comparisons = [
        ("adaptive_all_depth", "screen_single"),
        ("adaptive_all_depth", "screen_depth1"),
        ("adaptive_all_depth", "screen_depth2"),
        ("depth_policy", "screen_single"),
        ("depth_policy", "screen_depth2"),
        ("depth_policy", "adaptive_all_depth"),
        ("depth2_guard_direct", "screen_depth2"),
    ]
    lines = [
        "# Term-Set Boolean Screen Scale",
        "",
        "Large-scale logic-level ANF term-set evaluation. These rows do not build",
        "full truth tables; they evaluate the synthesis search state directly.",
        "Each method row is also checked twice: first by symbolic ANF plan",
        "expansion, then by symbolic simulation of the emitted X/CNOT/MCT",
        "oracle circuit over GF(2) polynomials.",
        "",
        f"ANF plan verification: {sum(1 for ex in examples for ev in ex.evals.values() if ev.anf_verified)}/"
        f"{sum(1 for ex in examples for _ in ex.evals.values())} method rows passed.",
        f"Emitted-circuit ANF verification: "
        f"{sum(1 for ex in examples for ev in ex.evals.values() if ev.circuit_anf_verified)}/"
        f"{sum(1 for ex in examples for _ in ex.evals.values())} method rows passed; "
        f"mismatches={sum(ev.circuit_mismatches for ex in examples for ev in ex.evals.values())}.",
        "",
        "## Paired comparisons",
        "",
        "| n | method | baseline | score W/L/T | mean score | mean time |",
        "|---:|---|---|---:|---:|---:|",
    ]
    grouped_examples: list[tuple[str, list[TermExample]]] = [
        *[(str(n), [ex for ex in examples if ex.n == n]) for n in by_n],
        ("all", examples),
    ]
    for n_label, subset in grouped_examples:
        for method, baseline in comparisons:
            if not all(method in ex.evals and baseline in ex.evals for ex in subset):
                continue
            wins, losses, ties, rel_score, rel_time = _comparison(subset, method, baseline)
            lines.append(
                f"| {n_label} | {method} | {baseline} | {wins}/{losses}/{ties} | "
                f"{rel_score:+.2%} | {rel_time:+.2%} |"
            )
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    table_path.parent.mkdir(parents=True, exist_ok=True)
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{rllrrr}\n")
        f.write("\\toprule\n")
        f.write("n & Method & Baseline & Score W/L/T & Mean $\\Delta$ score & Mean $\\Delta$ time \\\\\n")
        f.write("\\midrule\n")
        for n_label, subset in grouped_examples:
            for method, baseline in [
                ("adaptive_all_depth", "screen_single"),
                ("adaptive_all_depth", "screen_depth2"),
                ("depth_policy", "screen_single"),
                ("depth2_guard_direct", "screen_depth2"),
            ]:
                if not all(method in ex.evals and baseline in ex.evals for ex in subset):
                    continue
                wins, losses, ties, rel_score, rel_time = _comparison(subset, method, baseline)
                f.write(
                    f"{n_label} & {method} & {baseline} & {wins}/{losses}/{ties} & "
                    f"{rel_score:+.2%} & {rel_time:+.2%} \\\\\n"
                )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260710)
    ap.add_argument("--ns", default="20,22,24,28")
    ap.add_argument("--per-n", type=int, default=48)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--action-width", type=int, default=6)
    ap.add_argument("--policy-model", type=Path, default=THIS_DIR / "models" / "boolean_screen_depth_policy.pt")
    ap.add_argument("--guard-model", type=Path, default=THIS_DIR / "models" / "boolean_screen_depth_guard.pt")
    ap.add_argument("--results-dir", type=Path, default=RESULTS)
    ap.add_argument("--tables-dir", type=Path, default=TABLES)
    args = ap.parse_args(list(argv) if argv is not None else None)

    profiles = ["shallow", "mixed", "deep"]
    tasks: list[tuple[int, int, int, str, int]] = []
    for n in split_arg(args.ns):
        for i in range(args.per_n):
            profile = profiles[(i + n) % len(profiles)]
            tasks.append((n, i, args.seed + n * 10_000 + i, profile, args.action_width))

    examples: list[TermExample] = []
    started = time.time()
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            examples.append(evaluate_one(task))
            if i % 25 == 0:
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(evaluate_one, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                examples.append(fut.result())
                if i % 25 == 0:
                    print(f"{i}/{len(tasks)}", flush=True)
    examples.sort(key=lambda ex: (ex.n, ex.name))
    examples = add_learned_methods(examples, args.policy_model, args.guard_model)

    raw_path = args.results_dir / "raw_screen_scale_terms.csv"
    summary_path = args.results_dir / "summary_screen_scale_terms.csv"
    analysis_path = args.results_dir / "analysis_screen_scale_terms.md"
    table_path = args.tables_dir / "screen_scale_terms.tex"
    write_raw(raw_path, examples)
    write_summary(summary_path, analysis_path, table_path, examples)
    print(f"elapsed {time.time() - started:.2f}s")
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {analysis_path}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
