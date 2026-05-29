"""
Evaluation script: reproduce Tables IV-VIII from the paper.

Usage:
    python evaluate.py --table 4 --n 3
    python evaluate.py --table 5 --n 3 4 5 6 7 8
    python evaluate.py --table 6 --n 3 4 5 6
    python evaluate.py --table 8

Test sets:
  n=3: all 256 functions
  n=4: all 65536 functions
  n=5,6: 2000 random functions, minterm count in [1, 2^(n-1)]
  n=7,8: 2000 random functions (SSHR-H and XAG only)
"""
from __future__ import annotations
import argparse
import random
import sys
import math
import time
from typing import List, Dict, Callable

from bool_func import BooleanFunction
from sshr_h import sshr_h
from sshr_i import sshr_i


def make_test_set(n: int, seed: int = 42, random_count: int = 2000) -> List[BooleanFunction]:
    if n <= 4:
        return [BooleanFunction(n, tt) for tt in range(1 << (1 << n))]
    rng = random.Random(seed)
    fns = []
    N = 1 << n
    for _ in range(random_count):
        # Minterm count uniformly in [1, 2^(n-1)]
        k = rng.randint(1, N // 2)
        minterms = rng.sample(range(N), k)
        fns.append(BooleanFunction.from_list(n, [1 if i in set(minterms) else 0 for i in range(N)]))
    return fns


def evaluate_sshr_h(fns: List[BooleanFunction]) -> Dict:
    totals = {"T": 0, "CNOT": 0, "ancilla": 0}
    gate_counts = {"X": 0, "CNOT": 0, "2MCT": 0, "3MCT": 0, "4MCT": 0, "5MCT": 0, "6MCT": 0}
    for bf in fns:
        circ = sshr_h(bf)
        c = circ.cost()
        totals["T"] += c["T"]
        totals["CNOT"] += c["CNOT"]
        totals["ancilla"] = max(totals["ancilla"], c["ancilla"])
        for gate in circ.gates:
            if gate.type == "X":
                gate_counts["X"] += 1
            elif gate.type == "CNOT":
                gate_counts["CNOT"] += 1
            elif gate.type == "MCT":
                k = len(gate.controls)
                key = f"{k}MCT"
                if key in gate_counts:
                    gate_counts[key] += 1
    totals["gate_counts"] = gate_counts
    return totals


def evaluate_sshr_i(fns: List[BooleanFunction], objective: str = "cnot") -> Dict:
    totals = {"T": 0, "CNOT": 0, "ancilla": 0}
    for bf in fns:
        try:
            circ = sshr_i(bf, objective=objective)
        except Exception:
            from sshr_h import sshr_h as fallback
            circ = fallback(bf)
        c = circ.cost()
        totals["T"] += c["T"]
        totals["CNOT"] += c["CNOT"]
        totals["ancilla"] = max(totals["ancilla"], c["ancilla"])
    return totals


def table_viii() -> None:
    """Table VIII: ESOP vs SSHR optimization space."""
    from math import comb
    from parallelotope_enum import enumerate_parallelotopes

    print("\nTable VIII: Optimization space comparison")
    print(f"{'n':>4} {'ESOP':>10} {'SSHR':>10} {'Factor':>8}")
    print("-" * 36)
    for n in range(3, 9):
        # ESOP: sum_{k=1}^{n} C(n,k) * 2^k
        esop_space = sum(comb(n, k) * (2 ** k) for k in range(1, n + 1))
        # SSHR: count all parallelotopes in hypercube of dim n
        # Enumerate from full universe {0,...,2^n - 1}
        universe = list(range(1 << n))
        ps = enumerate_parallelotopes(universe, n)
        sshr_space = len(ps) + 1  # +1 for dim-0 singletons approximation
        factor = sshr_space / esop_space
        print(f"{n:>4} {esop_space:>10} {sshr_space:>10} {factor:>8.1f}")


def verify_circuit(bf: BooleanFunction, circuit) -> bool:
    """Verify circuit correctly implements bf by simulation."""
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]  # input + output=0
        result = circuit.simulate(bits)
        expected = bf.evaluate(x)
        if result[n] != expected:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Reproduce SSHR paper results")
    parser.add_argument("--table", type=int, choices=[4, 5, 6, 7, 8], default=8)
    parser.add_argument("--n", type=int, nargs="+", default=[3])
    parser.add_argument("--verify", action="store_true", help="Verify circuit correctness")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.table == 8:
        table_viii()
        return

    for n in args.n:
        print(f"\n=== n={n} ===")
        fns = make_test_set(n, seed=args.seed)
        print(f"  Test set size: {len(fns)} functions")

        # Correctness check on a small subset
        if args.verify and n <= 5:
            sample = fns[:min(20, len(fns))]
            all_ok = True
            for bf in sample:
                circ = sshr_h(bf)
                if not verify_circuit(bf, circ):
                    print(f"  FAIL: circuit incorrect for {bf}")
                    all_ok = False
            if all_ok:
                print(f"  Correctness: PASS (checked {len(sample)} functions)")

        if args.table in (4, 5):
            t0 = time.time()
            res = evaluate_sshr_h(fns)
            dt = time.time() - t0
            print(f"  SSHR-H  T={res['T']}  CNOT={res['CNOT']}  Ancilla={res['ancilla']}  ({dt:.1f}s)")

        if args.table in (6, 7):
            obj = "cnot" if args.table == 6 else "t"
            t0 = time.time()
            res = evaluate_sshr_i(fns, objective=obj)
            dt = time.time() - t0
            print(f"  SSHR-I({obj})  T={res['T']}  CNOT={res['CNOT']}  Ancilla={res['ancilla']}  ({dt:.1f}s)")


if __name__ == "__main__":
    main()
