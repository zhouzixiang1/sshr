"""Benchmark: AI-Pruned ILP vs Full SSHR-I on NPN representatives (n=4).

Runs both methods on the first 50 non-zero NPN reps and compares:
  - CNOT cost
  - Wall-clock time
  - Candidate reduction ratio
  - Correctness verification
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import mean, stdev

# Ensure both directories are on the path (sshr first for shared modules)
sshr_dir = str(Path(__file__).resolve().parent.parent / "sshr")
ai_dir = str(Path(__file__).resolve().parent)
if sshr_dir not in sys.path:
    sys.path.insert(0, sshr_dir)
if ai_dir not in sys.path:
    sys.path.insert(0, ai_dir)

from bool_func import BooleanFunction, QuantumCircuit, mct_cost  # noqa: E402
from sshr_i import sshr_i  # noqa: E402
from ai_pruned_ilp import ai_pruned_ilp  # noqa: E402
from rankers import RuleRanker  # noqa: E402
from feature_extractor import build_candidates, onset_mask  # noqa: E402
from pruned_candidates import select_pruned_candidates  # noqa: E402
from npn_reps_n4 import NPN_REPS_N4  # noqa: E402


def circuit_cnot(circ: QuantumCircuit) -> int:
    """Count total CNOT gates in a circuit."""
    total = 0
    for g in circ.gates:
        if g.type == "MCT":
            total += mct_cost(len(g.controls))["CNOT"]
        elif g.type == "CNOT":
            total += 1
    return total


def verify_circuit(bf: BooleanFunction, circ: QuantumCircuit) -> bool:
    """Verify the circuit implements the Boolean function correctly."""
    for x in range(1 << bf.n):
        bits = [(x >> i) & 1 for i in range(bf.n)] + [0]
        if circ.simulate(bits)[bf.n] != bf.evaluate(x):
            return False
    return True


def main():
    timeout = 30
    keep_ratio = 0.1
    keep_min = 100
    objective = "cnot"

    # Get non-zero NPN reps
    reps = [tt for tt in NPN_REPS_N4 if tt != 0][:50]
    print(f"Benchmark: AI-Pruned ILP vs Full SSHR-I")
    print(f"n=4, {len(reps)} functions, timeout={timeout}s, "
          f"keep_ratio={keep_ratio}, keep_min={keep_min}")
    print("=" * 90)

    # Get full candidate count for n=4
    all_candidates = build_candidates(4)
    full_count = len(all_candidates)
    print(f"Full candidate pool size (n=4): {full_count}")
    print("=" * 90)

    results = []
    header = (f"{'#':>3} {'tt':>6} {'onset':>5} | "
              f"{'Full_CNOT':>10} {'Full_t(s)':>10} | "
              f"{'Pruned_CNOT':>12} {'Pruned_t(s)':>12} {'Pruned_n':>9} {'Reduction':>10} | "
              f"{'CNOT_d':>7} {'Correct':>8}")
    print(header)
    print("-" * len(header))

    ranker = RuleRanker()

    for idx, tt in enumerate(reps, 1):
        bf = BooleanFunction(4, tt)

        # Skip functions with empty onset (should not happen since we filter tt=0)
        if not bf.onset:
            continue

        # --- Full SSHR-I ---
        t0 = time.time()
        full_circ = sshr_i(bf, objective=objective, timeout=timeout, try_complement=False)
        full_time = time.time() - t0
        full_cnot = circuit_cnot(full_circ)

        # --- AI-Pruned ILP ---
        t0 = time.time()
        pruned_circ = ai_pruned_ilp(
            bf, objective=objective, timeout=timeout,
            keep_ratio=keep_ratio, keep_min=keep_min, ranker=ranker,
        )
        pruned_time = time.time() - t0
        pruned_cnot = circuit_cnot(pruned_circ)

        # Pruned candidate count
        pruned_set = select_pruned_candidates(
            bf, keep_ratio=keep_ratio, keep_min=keep_min,
            objective=objective, ranker=ranker,
        )
        pruned_count = len(pruned_set)
        reduction = (1 - pruned_count / full_count) * 100

        # Verify correctness
        correct = verify_circuit(bf, pruned_circ)
        cnot_diff = pruned_cnot - full_cnot

        results.append({
            "idx": idx,
            "tt": tt,
            "onset": len(bf.onset),
            "full_cnot": full_cnot,
            "full_time": full_time,
            "pruned_cnot": pruned_cnot,
            "pruned_time": pruned_time,
            "pruned_count": pruned_count,
            "full_count": full_count,
            "reduction": reduction,
            "cnot_diff": cnot_diff,
            "correct": correct,
        })

        print(f"{idx:3d} 0x{tt:04X} {len(bf.onset):5d} | "
              f"{full_cnot:10d} {full_time:10.2f} | "
              f"{pruned_cnot:12d} {pruned_time:12.2f} {pruned_count:9d} {reduction:9.1f}% | "
              f"{cnot_diff:+7d} {'OK' if correct else 'FAIL':>8}")

    # Summary
    print("=" * 90)
    print("\nSUMMARY")
    print("-" * 50)

    n_funcs = len(results)
    avg_full_cnot = mean(r["full_cnot"] for r in results)
    avg_pruned_cnot = mean(r["pruned_cnot"] for r in results)
    avg_full_time = mean(r["full_time"] for r in results)
    avg_pruned_time = mean(r["pruned_time"] for r in results)
    avg_reduction = mean(r["reduction"] for r in results)
    total_full_cnot = sum(r["full_cnot"] for r in results)
    total_pruned_cnot = sum(r["pruned_cnot"] for r in results)
    n_correct = sum(1 for r in results if r["correct"])
    n_better = sum(1 for r in results if r["cnot_diff"] < 0)
    n_equal = sum(1 for r in results if r["cnot_diff"] == 0)
    n_worse = sum(1 for r in results if r["cnot_diff"] > 0)
    max_degradation = max(r["cnot_diff"] for r in results)
    min_degradation = min(r["cnot_diff"] for r in results)

    cnot_diffs = [r["cnot_diff"] for r in results]

    print(f"Functions tested:          {n_funcs}")
    print(f"Correctness:               {n_correct}/{n_funcs}")
    print(f"")
    print(f"Avg CNOT (Full SSHR-I):    {avg_full_cnot:.2f}")
    print(f"Avg CNOT (AI-Pruned):      {avg_pruned_cnot:.2f}")
    print(f"Total CNOT (Full SSHR-I):  {total_full_cnot}")
    print(f"Total CNOT (AI-Pruned):    {total_pruned_cnot}")
    print(f"Total CNOT delta:          {total_pruned_cnot - total_full_cnot:+d} "
          f"({(total_pruned_cnot / total_full_cnot - 1) * 100:+.2f}%)")
    print(f"")
    print(f"Avg time (Full SSHR-I):    {avg_full_time:.2f}s")
    print(f"Avg time (AI-Pruned):      {avg_pruned_time:.2f}s")
    print(f"Speedup ratio:             {avg_full_time / avg_pruned_time:.2f}x")
    print(f"")
    print(f"Avg candidate reduction:   {avg_reduction:.1f}%")
    print(f"")
    print(f"Pruned BETTER (less CNOT): {n_better}")
    print(f"Pruned EQUAL:              {n_equal}")
    print(f"Pruned WORSE (more CNOT):  {n_worse}")
    print(f"Max CNOT degradation:      {max_degradation:+d}")
    print(f"Best CNOT improvement:     {min_degradation:+d}")
    if len(cnot_diffs) > 1:
        print(f"Stdev of CNOT diff:        {stdev(cnot_diffs):.2f}")


if __name__ == "__main__":
    main()
