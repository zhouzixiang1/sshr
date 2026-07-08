#!/usr/bin/env python3
"""Truth-table verified bridge tests for high-dimensional ANF term sets.

The screen-scale experiments above n=20 use symbolic ANF verification because
full truth-table construction is the expensive part.  This script deliberately
builds full truth tables for a small high-dimensional bridge set, then verifies
the emitted X/CNOT/MCT circuit with the bit-parallel oracle verifier.  The goal
is not a large sample count; it is to close the evidence gap between full
function-level verification and the larger symbolic term-set scale tests.
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

from anf_utils import boolean_from_anf
from factor_plan import (
    SearchConfig,
    analyze_circuit_schedule,
    direct_plan,
    emit_plan_to_circuit,
    linear_pair_screen_plan,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from resource_model import ResourceWeights
from train_screen_depth_guard import Depth2GuardNet
from train_screen_depth_policy import FEATURE_NAMES, DepthPolicyNet, generate_terms, term_features


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
    schedule_logical_depth: int
    schedule_cnot_depth_proxy: int
    schedule_t_depth_proxy: int
    explicit_ancilla_live_peak: int
    explicit_ancilla_lifetime_area: int
    plan_time_s: float
    truth_verify_time_s: float
    anf_verified: bool
    plan_nodes: int
    plan_mismatches: int
    circuit_anf_verified: bool
    circuit_gates: int
    circuit_max_wire_terms: int
    circuit_mismatches: int
    truth_verified: bool


@dataclass(frozen=True)
class TruthExample:
    name: str
    n: int
    profile: str
    term_count: int
    truth_build_time_s: float
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


def eval_plan(method: str, plan, plan_time_s: float, config: SearchConfig, n_inputs: int, bf) -> MethodEval:
    plan_verification = verify_plan_anf(plan)
    circuit = emit_plan_to_circuit(plan, n_inputs, config.max_factor_ancilla)
    circuit_verification = verify_circuit_anf(circuit, n_inputs, plan.terms)
    schedule = analyze_circuit_schedule(circuit, n_inputs, config.use_relative_phase)
    started = time.perf_counter()
    truth_verified = verify_oracle(circuit, bf)
    truth_verify_time_s = time.perf_counter() - started
    return MethodEval(
        method=method,
        score=plan.score(config.weights),
        t_count=plan.cost.T,
        cnot=plan.cost.CNOT,
        depth=plan.cost.depth,
        gates=plan.cost.gates,
        peak_ancilla=plan.cost.peak_ancilla,
        schedule_logical_depth=schedule.logical_depth,
        schedule_cnot_depth_proxy=schedule.cnot_depth_proxy,
        schedule_t_depth_proxy=schedule.t_depth_proxy,
        explicit_ancilla_live_peak=schedule.explicit_ancilla_live_peak,
        explicit_ancilla_lifetime_area=schedule.explicit_ancilla_lifetime_area,
        plan_time_s=plan_time_s,
        truth_verify_time_s=truth_verify_time_s,
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
        truth_verified=truth_verified,
    )


def evaluate_one(task: tuple[int, int, int, str, int, int]) -> TruthExample:
    n, index, seed, profile, action_width, max_screen_depth = task
    rng = random.Random(seed)
    config = make_config()
    terms = generate_terms(n, rng, profile)
    features = term_features(terms, config)

    started = time.perf_counter()
    bf = boolean_from_anf(n, terms)
    truth_build_time_s = time.perf_counter() - started

    evals: dict[str, MethodEval] = {}
    started = time.perf_counter()
    direct = direct_plan(terms, 0, 0, config)
    evals["direct_logical_and"] = eval_plan(
        "direct_logical_and",
        direct,
        time.perf_counter() - started,
        config,
        n,
        bf,
    )

    screen_methods = [("screen_single", 0)]
    screen_methods.extend((f"screen_depth{depth}", depth) for depth in range(1, max_screen_depth + 1))
    for method, recursive_depth in screen_methods:
        started = time.perf_counter()
        plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=action_width,
            recursive_depth=recursive_depth,
            boolean_ring=True,
        )
        evals[method] = eval_plan(method, plan, time.perf_counter() - started, config, n, bf)

    screen_evals = [evals[method] for method, _depth in screen_methods]
    best_screen = min(screen_evals, key=lambda ev: (ev.score, ev.plan_time_s))
    evals["adaptive_all_depth"] = MethodEval(
        method="adaptive_all_depth",
        score=best_screen.score,
        t_count=best_screen.t_count,
        cnot=best_screen.cnot,
        depth=best_screen.depth,
        gates=best_screen.gates,
        peak_ancilla=best_screen.peak_ancilla,
        schedule_logical_depth=best_screen.schedule_logical_depth,
        schedule_cnot_depth_proxy=best_screen.schedule_cnot_depth_proxy,
        schedule_t_depth_proxy=best_screen.schedule_t_depth_proxy,
        explicit_ancilla_live_peak=best_screen.explicit_ancilla_live_peak,
        explicit_ancilla_lifetime_area=best_screen.explicit_ancilla_lifetime_area,
        plan_time_s=sum(ev.plan_time_s for ev in screen_evals),
        truth_verify_time_s=best_screen.truth_verify_time_s,
        anf_verified=best_screen.anf_verified,
        plan_nodes=best_screen.plan_nodes,
        plan_mismatches=best_screen.plan_mismatches,
        circuit_anf_verified=best_screen.circuit_anf_verified,
        circuit_gates=best_screen.circuit_gates,
        circuit_max_wire_terms=best_screen.circuit_max_wire_terms,
        circuit_mismatches=best_screen.circuit_mismatches,
        truth_verified=best_screen.truth_verified,
    )

    return TruthExample(
        name=f"truth_bridge_n{n}_{index:03d}_{profile}",
        n=n,
        profile=profile,
        term_count=len(terms),
        truth_build_time_s=truth_build_time_s,
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


def load_frontier_policy(path: Path) -> tuple[DepthPolicyNet, torch.Tensor, torch.Tensor, list[int]] | None:
    if not path.exists():
        return None
    ckpt = torch.load(path, map_location="cpu")
    depths = [int(v) for v in ckpt.get("depths", [])]
    if not depths or min(depths) < 2:
        return None
    hidden = int(ckpt.get("hidden", 96))
    model = DepthPolicyNet(len(FEATURE_NAMES), hidden=hidden)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return (
        model,
        torch.tensor(ckpt["mean"], dtype=torch.float32),
        torch.tensor(ckpt["std"], dtype=torch.float32),
        depths,
    )


@torch.no_grad()
def add_learned_methods(
    examples: list[TruthExample],
    policy_path: Path,
    guard_path: Path,
    frontier_policy_path: Path,
) -> list[TruthExample]:
    policy = load_depth_policy(policy_path)
    guard = load_depth2_guard(guard_path)
    frontier_policy = load_frontier_policy(frontier_policy_path)
    if policy is None and guard is None and frontier_policy is None:
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

    frontier_depths: list[int] | None = None
    if frontier_policy is not None:
        model, mean, std, depths = frontier_policy
        logits = model((features - mean) / std)
        indices = [int(v) for v in logits.argmax(dim=1).tolist()]
        frontier_depths = [depths[min(index, len(depths) - 1)] for index in indices]

    updated: list[TruthExample] = []
    for idx, ex in enumerate(examples):
        evals = dict(ex.evals)
        if policy_depths is not None:
            key = {0: "screen_single", 1: "screen_depth1", 2: "screen_depth2"}[policy_depths[idx]]
            chosen = evals[key]
            evals["depth_policy"] = MethodEval(
                method="depth_policy",
                score=chosen.score,
                t_count=chosen.t_count,
                cnot=chosen.cnot,
                depth=chosen.depth,
                gates=chosen.gates,
                peak_ancilla=chosen.peak_ancilla,
                schedule_logical_depth=chosen.schedule_logical_depth,
                schedule_cnot_depth_proxy=chosen.schedule_cnot_depth_proxy,
                schedule_t_depth_proxy=chosen.schedule_t_depth_proxy,
                explicit_ancilla_live_peak=chosen.explicit_ancilla_live_peak,
                explicit_ancilla_lifetime_area=chosen.explicit_ancilla_lifetime_area,
                plan_time_s=chosen.plan_time_s,
                truth_verify_time_s=chosen.truth_verify_time_s,
                anf_verified=chosen.anf_verified,
                plan_nodes=chosen.plan_nodes,
                plan_mismatches=chosen.plan_mismatches,
                circuit_anf_verified=chosen.circuit_anf_verified,
                circuit_gates=chosen.circuit_gates,
                circuit_max_wire_terms=chosen.circuit_max_wire_terms,
                circuit_mismatches=chosen.circuit_mismatches,
                truth_verified=chosen.truth_verified,
            )
        if guard_depths is not None:
            key = {1: "screen_depth1", 2: "screen_depth2"}[guard_depths[idx]]
            chosen = evals[key]
            evals["depth2_guard_direct"] = MethodEval(
                method="depth2_guard_direct",
                score=chosen.score,
                t_count=chosen.t_count,
                cnot=chosen.cnot,
                depth=chosen.depth,
                gates=chosen.gates,
                peak_ancilla=chosen.peak_ancilla,
                schedule_logical_depth=chosen.schedule_logical_depth,
                schedule_cnot_depth_proxy=chosen.schedule_cnot_depth_proxy,
                schedule_t_depth_proxy=chosen.schedule_t_depth_proxy,
                explicit_ancilla_live_peak=chosen.explicit_ancilla_live_peak,
                explicit_ancilla_lifetime_area=chosen.explicit_ancilla_lifetime_area,
                plan_time_s=chosen.plan_time_s,
                truth_verify_time_s=chosen.truth_verify_time_s,
                anf_verified=chosen.anf_verified,
                plan_nodes=chosen.plan_nodes,
                plan_mismatches=chosen.plan_mismatches,
                circuit_anf_verified=chosen.circuit_anf_verified,
                circuit_gates=chosen.circuit_gates,
                circuit_max_wire_terms=chosen.circuit_max_wire_terms,
                circuit_mismatches=chosen.circuit_mismatches,
                truth_verified=chosen.truth_verified,
            )
        if frontier_depths is not None:
            key = f"screen_depth{frontier_depths[idx]}"
            if key in evals:
                chosen = evals[key]
                evals["depth_frontier_policy"] = MethodEval(
                    method="depth_frontier_policy",
                    score=chosen.score,
                    t_count=chosen.t_count,
                    cnot=chosen.cnot,
                    depth=chosen.depth,
                    gates=chosen.gates,
                    peak_ancilla=chosen.peak_ancilla,
                    schedule_logical_depth=chosen.schedule_logical_depth,
                    schedule_cnot_depth_proxy=chosen.schedule_cnot_depth_proxy,
                    schedule_t_depth_proxy=chosen.schedule_t_depth_proxy,
                    explicit_ancilla_live_peak=chosen.explicit_ancilla_live_peak,
                    explicit_ancilla_lifetime_area=chosen.explicit_ancilla_lifetime_area,
                    plan_time_s=chosen.plan_time_s,
                    truth_verify_time_s=chosen.truth_verify_time_s,
                    anf_verified=chosen.anf_verified,
                    plan_nodes=chosen.plan_nodes,
                    plan_mismatches=chosen.plan_mismatches,
                    circuit_anf_verified=chosen.circuit_anf_verified,
                    circuit_gates=chosen.circuit_gates,
                    circuit_max_wire_terms=chosen.circuit_max_wire_terms,
                    circuit_mismatches=chosen.circuit_mismatches,
                    truth_verified=chosen.truth_verified,
                )
        updated.append(
            TruthExample(
                name=ex.name,
                n=ex.n,
                profile=ex.profile,
                term_count=ex.term_count,
                truth_build_time_s=ex.truth_build_time_s,
                features=ex.features,
                evals=evals,
            )
        )
    return updated


def write_raw(path: Path, examples: list[TruthExample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "n",
        "profile",
        "term_count",
        "truth_build_time_s",
        "method",
        "score",
        "T",
        "CNOT",
        "depth",
        "gates",
        "peak_ancilla",
        "schedule_logical_depth",
        "schedule_cnot_depth_proxy",
        "schedule_t_depth_proxy",
        "explicit_ancilla_live_peak",
        "explicit_ancilla_lifetime_area",
        "plan_time_s",
        "truth_verify_time_s",
        "truth_verified",
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
                        "truth_build_time_s": ex.truth_build_time_s,
                        "method": method,
                        "score": ev.score,
                        "T": ev.t_count,
                        "CNOT": ev.cnot,
                        "depth": ev.depth,
                        "gates": ev.gates,
                        "peak_ancilla": ev.peak_ancilla,
                        "schedule_logical_depth": ev.schedule_logical_depth,
                        "schedule_cnot_depth_proxy": ev.schedule_cnot_depth_proxy,
                        "schedule_t_depth_proxy": ev.schedule_t_depth_proxy,
                        "explicit_ancilla_live_peak": ev.explicit_ancilla_live_peak,
                        "explicit_ancilla_lifetime_area": ev.explicit_ancilla_lifetime_area,
                        "plan_time_s": ev.plan_time_s,
                        "truth_verify_time_s": ev.truth_verify_time_s,
                        "truth_verified": ev.truth_verified,
                        "anf_verified": ev.anf_verified,
                        "plan_nodes": ev.plan_nodes,
                        "plan_mismatches": ev.plan_mismatches,
                        "circuit_anf_verified": ev.circuit_anf_verified,
                        "circuit_gates": ev.circuit_gates,
                        "circuit_max_wire_terms": ev.circuit_max_wire_terms,
                        "circuit_mismatches": ev.circuit_mismatches,
                    }
                )


def _comparison(examples: list[TruthExample], method: str, baseline: str) -> tuple[int, int, int, float, float]:
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
        rel_time.append((target.plan_time_s - base.plan_time_s) / max(base.plan_time_s, 1e-9))
    return (
        wins,
        losses,
        ties,
        statistics.mean(rel_score) if rel_score else 0.0,
        statistics.mean(rel_time) if rel_time else 0.0,
    )


def format_n_set(values: list[int]) -> str:
    if not values:
        return "n=?"
    if len(values) == 1:
        return f"n={values[0]}"
    return "n=" + ",".join(str(v) for v in values)


def write_summary(summary_path: Path, analysis_path: Path, table_path: Path, examples: list[TruthExample]) -> None:
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
                "mean_schedule_logical_depth",
                "mean_schedule_cnot_depth_proxy",
                "mean_schedule_t_depth_proxy",
                "mean_explicit_ancilla_live_peak",
                "mean_explicit_ancilla_lifetime_area",
                "mean_score",
                "mean_plan_time_s",
                "mean_truth_build_time_s",
                "mean_truth_verify_time_s",
                "truth_verified_rows",
                "anf_verified_rows",
                "circuit_verified_rows",
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
                        "mean_schedule_logical_depth": statistics.mean(v.schedule_logical_depth for v in vals),
                        "mean_schedule_cnot_depth_proxy": statistics.mean(v.schedule_cnot_depth_proxy for v in vals),
                        "mean_schedule_t_depth_proxy": statistics.mean(v.schedule_t_depth_proxy for v in vals),
                        "mean_explicit_ancilla_live_peak": statistics.mean(v.explicit_ancilla_live_peak for v in vals),
                        "mean_explicit_ancilla_lifetime_area": statistics.mean(
                            v.explicit_ancilla_lifetime_area for v in vals
                        ),
                        "mean_score": statistics.mean(v.score for v in vals),
                        "mean_plan_time_s": statistics.mean(v.plan_time_s for v in vals),
                        "mean_truth_build_time_s": statistics.mean(ex.truth_build_time_s for ex in subset),
                        "mean_truth_verify_time_s": statistics.mean(v.truth_verify_time_s for v in vals),
                        "truth_verified_rows": sum(1 for v in vals if v.truth_verified),
                        "anf_verified_rows": sum(1 for v in vals if v.anf_verified),
                        "circuit_verified_rows": sum(1 for v in vals if v.circuit_anf_verified),
                        "mean_circuit_max_wire_terms": statistics.mean(v.circuit_max_wire_terms for v in vals),
                    }
                )

    comparisons = [
        ("adaptive_all_depth", "screen_single"),
        ("adaptive_all_depth", "screen_depth2"),
        ("depth_policy", "screen_single"),
        ("depth_policy", "adaptive_all_depth"),
        ("depth_frontier_policy", "screen_depth2"),
        ("depth_frontier_policy", "screen_depth4"),
        ("depth_frontier_policy", "adaptive_all_depth"),
        ("depth2_guard_direct", "screen_depth2"),
    ]
    max_screen_depth = max(
        [0]
        + [
            int(method.removeprefix("screen_depth"))
            for method in methods
            if method.startswith("screen_depth") and method.removeprefix("screen_depth").isdigit()
        ]
    )
    for depth in range(3, max_screen_depth + 1):
        comparisons.append((f"screen_depth{depth}", "screen_depth2"))
        if depth > 3:
            comparisons.append((f"screen_depth{depth}", f"screen_depth{depth - 1}"))

    total_rows = sum(1 for ex in examples for _ in ex.evals.values())
    truth_ok = sum(1 for ex in examples for ev in ex.evals.values() if ev.truth_verified)
    anf_ok = sum(1 for ex in examples for ev in ex.evals.values() if ev.anf_verified)
    circuit_ok = sum(1 for ex in examples for ev in ex.evals.values() if ev.circuit_anf_verified)
    circuit_mismatches = sum(ev.circuit_mismatches for ex in examples for ev in ex.evals.values())
    lines = [
        "# Truth-Table Bridge for High-Dimensional Boolean Screen",
        "",
        f"This bridge set builds full truth tables for generated {format_n_set(by_n)} ANF",
        "term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit",
        "with the bit-parallel truth-table oracle checker.  It is smaller than",
        "the symbolic n=20--40 scale tests because truth-table construction is",
        "the dominant cost.",
        "",
        f"Truth-table verification: {truth_ok}/{total_rows} method rows passed.",
        f"ANF plan verification: {anf_ok}/{total_rows} method rows passed.",
        f"Emitted-circuit ANF verification: {circuit_ok}/{total_rows} method rows passed; "
        f"mismatches={circuit_mismatches}.",
        f"Mean truth-table build time per function: "
        f"{statistics.mean(ex.truth_build_time_s for ex in examples):.2f}s.",
        "",
        "## Paired comparisons",
        "",
        "| n | method | baseline | score W/L/T | mean score | mean plan time |",
        "|---:|---|---|---:|---:|---:|",
    ]
    grouped_examples: list[tuple[str, list[TruthExample]]] = [
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

    def latex_pct(value: float) -> str:
        return f"{value:+.2%}".replace("%", r"\%")

    def latex_text(value: str) -> str:
        return value.replace("_", r"\_")

    table_path.parent.mkdir(parents=True, exist_ok=True)
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{rllrrr}\n")
        f.write("\\toprule\n")
        f.write("n & Method & Baseline & Score W/L/T & Mean $\\Delta$ score & Mean $\\Delta$ plan time \\\\\n")
        f.write("\\midrule\n")
        table_comparisons = [
            ("adaptive_all_depth", "screen_single"),
            ("adaptive_all_depth", "screen_depth2"),
            ("depth_policy", "screen_single"),
            ("depth_frontier_policy", "screen_depth2"),
            ("depth_frontier_policy", "screen_depth4"),
            ("depth2_guard_direct", "screen_depth2"),
        ]
        for depth in range(3, max_screen_depth + 1):
            table_comparisons.append((f"screen_depth{depth}", "screen_depth2"))
        for n_label, subset in grouped_examples:
            for method, baseline in table_comparisons:
                if not all(method in ex.evals and baseline in ex.evals for ex in subset):
                    continue
                wins, losses, ties, rel_score, rel_time = _comparison(subset, method, baseline)
                f.write(
                    f"{n_label} & {latex_text(method)} & {latex_text(baseline)} & {wins}/{losses}/{ties} & "
                    f"{latex_pct(rel_score)} & {latex_pct(rel_time)} \\\\\n"
                )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--ns", default="21,22")
    parser.add_argument("--per-n", type=int, default=6)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--action-width", type=int, default=6)
    parser.add_argument("--max-screen-depth", type=int, default=4)
    parser.add_argument("--policy-model", type=Path, default=THIS_DIR / "models" / "boolean_screen_depth_policy.pt")
    parser.add_argument("--guard-model", type=Path, default=THIS_DIR / "models" / "boolean_screen_depth_guard.pt")
    parser.add_argument(
        "--frontier-policy-model",
        type=Path,
        default=THIS_DIR / "models" / "boolean_screen_depth_frontier_policy.pt",
    )
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--tables-dir", type=Path, default=TABLES)
    parser.add_argument("--tag", default="truth_bridge")
    args = parser.parse_args(list(argv) if argv is not None else None)

    profiles = ["shallow", "mixed", "deep"]
    tasks: list[tuple[int, int, int, str, int, int]] = []
    for n in split_arg(args.ns):
        for i in range(args.per_n):
            profile = profiles[(i + n) % len(profiles)]
            tasks.append((n, i, args.seed + n * 10_000 + i, profile, args.action_width, args.max_screen_depth))

    examples: list[TruthExample] = []
    started = time.time()
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            examples.append(evaluate_one(task))
            print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(evaluate_one, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                examples.append(fut.result())
                print(f"{i}/{len(tasks)}", flush=True)
    examples.sort(key=lambda ex: (ex.n, ex.name))
    examples = add_learned_methods(examples, args.policy_model, args.guard_model, args.frontier_policy_model)

    tag = f"_{args.tag.strip().replace('-', '_')}" if args.tag.strip() else ""
    raw_path = args.results_dir / f"raw{tag}_terms.csv"
    summary_path = args.results_dir / f"summary{tag}_terms.csv"
    analysis_path = args.results_dir / f"analysis{tag}_terms.md"
    table_path = args.tables_dir / f"{args.tag.strip().replace('-', '_')}_terms.tex"
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
