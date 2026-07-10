"""Systematic benchmark comparing all AI-SSHR methods.

Methods compared:
  1. sshr_h      — Greedy heuristic (XOR semantics)
  2. beam        — Native beam search (monotone)
  3. mcts        — MCTS v2 (monotone)
  4. ai_beam_rule — AI-guided beam with RuleRanker
  5. ai_beam_ml  — AI-guided beam with trained LightGBM ranker
  6. ai_pruned_ilp — ML-pruned candidates + ILP solver (sshr env only)

Outputs CSV with per-function results + summary statistics.
"""
from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path
from typing import Dict, List, Optional

from ai_guided_beam import ai_guided_beam
from data_collector import get_functions
from feature_extractor import ensure_sshr_on_path
from rankers import RuleRanker

ensure_sshr_on_path()

from bool_func import BooleanFunction, QuantumCircuit, mct_cost, mct_cost_rp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_circuit(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    """Verify circuit correctness by classical simulation."""
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            return False
    return True


def circuit_cost(circ: QuantumCircuit, objective: str = "cnot") -> dict:
    """Compute T/CNOT/ancilla cost."""
    cost_fn = mct_cost_rp if objective == "t" else mct_cost
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            c = cost_fn(len(g.controls))
            T += c["T"]
            C += c["CNOT"]
            anc = max(anc, c["ancilla"])
        elif g.type == "CNOT":
            C += 1
    return {"T": T, "CNOT": C, "ancilla": anc}


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

ALL_METHODS = ["sshr_h", "beam", "mcts", "ai_beam_rule", "ai_beam_ml",
               "ai_pruned_ilp", "xor_rule", "xor_ml"]


def benchmark_one(
    bf: BooleanFunction,
    methods: List[str],
    objective: str,
    model_path: Optional[Path] = None,
    beam_width: int = 50,
    beam_branch: int = 10,
    mcts_iters: int = 1000,
    mcts_time: float = 30.0,
    ilp_timeout: float = 120.0,
    ilp_keep_ratio: float = 0.1,
) -> List[dict]:
    """Run all methods on one function and return result rows."""
    results = []
    ranker_ml = None

    for method in methods:
        row = {
            "method": method,
            "n": bf.n,
            "func_tt": hex(bf.truth_table),
            "objective": objective,
        }

        t0 = time.time()
        try:
            if method == "sshr_h":
                from sshr_h import sshr_h
                circ = sshr_h(bf)

            elif method == "beam":
                from sshr_beam import sshr_beam
                circ = sshr_beam(bf, objective=objective, width=beam_width, branch=beam_branch)

            elif method == "mcts":
                from sshr_mcts_v2 import sshr_mcts_v2
                circ = sshr_mcts_v2(
                    bf, objective=objective,
                    n_iterations=mcts_iters, time_limit=mcts_time,
                )

            elif method == "ai_beam_rule":
                result = ai_guided_beam(
                    bf, objective=objective,
                    width=beam_width, branch=beam_branch,
                    ranker=RuleRanker(), mode="monotone",
                )
                circ = result.circuit

            elif method == "ai_beam_ml":
                if ranker_ml is None:
                    if model_path and model_path.exists():
                        from ml_rankers import LightGBMRanker
                        ranker_ml = LightGBMRanker.load(model_path)
                    else:
                        row["error"] = f"model not found: {model_path}"
                        results.append(row)
                        continue
                result = ai_guided_beam(
                    bf, objective=objective,
                    width=beam_width, branch=beam_branch,
                    ranker=ranker_ml, mode="monotone",
                )
                circ = result.circuit

            elif method == "xor_rule":
                result = ai_guided_beam(
                    bf, objective=objective,
                    width=beam_width, branch=beam_branch,
                    ranker=RuleRanker(), mode="xor",
                )
                circ = result.circuit

            elif method == "xor_ml":
                if ranker_ml is None:
                    if model_path and model_path.exists():
                        from ml_rankers import LightGBMRanker
                        ranker_ml = LightGBMRanker.load(model_path)
                    else:
                        row["error"] = f"model not found: {model_path}"
                        results.append(row)
                        continue
                result = ai_guided_beam(
                    bf, objective=objective,
                    width=beam_width, branch=beam_branch,
                    ranker=ranker_ml, mode="xor",
                )
                circ = result.circuit

            elif method == "ai_pruned_ilp":
                try:
                    from ai_pruned_ilp import ai_pruned_ilp
                    if ranker_ml is None:
                        if model_path and model_path.exists():
                            from ml_rankers import LightGBMRanker
                            ranker_ml = LightGBMRanker.load(model_path)
                        else:
                            ranker_ml = RuleRanker()
                    circ = ai_pruned_ilp(
                        bf, objective=objective, timeout=ilp_timeout,
                        keep_ratio=ilp_keep_ratio, ranker=ranker_ml,
                    )
                except ImportError:
                    row["error"] = "gurobipy not available"
                    results.append(row)
                    continue

            else:
                continue

        except Exception as e:
            row["error"] = str(e)[:100]
            results.append(row)
            continue

        elapsed = time.time() - t0
        cost = circuit_cost(circ, objective)
        correct = verify_circuit(circ, bf)

        row.update({
            "T": cost["T"],
            "CNOT": cost["CNOT"],
            "ancilla": cost["ancilla"],
            "time_s": round(elapsed, 4),
            "correct": int(correct),
        })
        results.append(row)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AI-SSHR systematic benchmark")
    parser.add_argument("--n", nargs="+", type=int, default=[3, 4, 5, 6])
    parser.add_argument("--methods", nargs="+", default=["sshr_h", "beam", "ai_beam_rule", "xor_rule", "xor_ml"])
    parser.add_argument("--objective", choices=["cnot", "t"], default="cnot")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent / "results" / "ai_comparison")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--fns", type=int, default=2000)
    parser.add_argument("--max-fns", type=int, default=None,
                        help="Override max functions per n")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--beam-width", type=int, default=50)
    parser.add_argument("--beam-branch", type=int, default=10)
    parser.add_argument("--mcts-iters", type=int, default=1000)
    parser.add_argument("--mcts-time", type=float, default=30.0)
    parser.add_argument("--ilp-timeout", type=float, default=120.0)
    parser.add_argument("--ilp-keep-ratio", type=float, default=0.1)
    args = parser.parse_args()

    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"benchmark_{'_'.join(map(str, args.n))}_{args.objective}.csv"

    csv_cols = [
        "method", "n", "func_tt", "objective",
        "T", "CNOT", "ancilla", "time_s", "correct", "error",
    ]

    all_results = []

    for n in args.n:
        max_fns = args.max_fns or (None if n <= 4 else args.fns)
        fns = get_functions(n, args.seed, max_fns if max_fns else 999999)
        if max_fns:
            fns = fns[:max_fns]
        print(f"\nn={n}: {len(fns)} functions, methods={args.methods}")

        for i, bf in enumerate(fns):
            if not bf.onset:
                continue

            rows = benchmark_one(
                bf, args.methods, args.objective,
                model_path=args.model,
                beam_width=args.beam_width,
                beam_branch=args.beam_branch,
                mcts_iters=args.mcts_iters,
                mcts_time=args.mcts_time,
                ilp_timeout=args.ilp_timeout,
                ilp_keep_ratio=args.ilp_keep_ratio,
            )
            all_results.extend(rows)

            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(fns)} done")

    # Write CSV
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\nResults written to {csv_path}")

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"{'method':20s} {'n':>3s} {'CNOT':>8s} {'T':>8s} {'time_s':>10s} {'correct':>8s}")
    print("-" * 70)

    # Group by (method, n)
    from collections import defaultdict
    groups = defaultdict(list)
    for r in all_results:
        if "error" in r:
            continue
        groups[(r["method"], r["n"])].append(r)

    for method in args.methods:
        for n in args.n:
            entries = groups.get((method, n), [])
            if not entries:
                continue
            avg_cnot = sum(e["CNOT"] for e in entries) / len(entries)
            avg_t = sum(e["T"] for e in entries) / len(entries)
            avg_time = sum(e["time_s"] for e in entries) / len(entries)
            n_correct = sum(e["correct"] for e in entries)
            print(f"{method:20s} {n:3d} {avg_cnot:8.1f} {avg_t:8.1f} "
                  f"{avg_time:10.4f} {n_correct:5d}/{len(entries)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
