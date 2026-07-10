#!/usr/bin/env python3
"""
Paper-format comparison table generator.

Reproduces Table V and Table VI from Zheng et al. 2025 and compares
SSHR-H, SSHR-H (paper literal), Beam, MCTS, XOR-Beam(Rule), and
XOR-Beam(ML) against paper baselines.

Usage:
    # Full run (n=3,4,5,6)
    python run_paper_format_compare.py

    # Quick test (50 functions per n)
    python run_paper_format_compare.py --quick --n 5

    # Specific n values
    python run_paper_format_compare.py --n 5 6 --fns 2000
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Path setup ────────────────────────────────────────────────────────────────
SSHR_DIR = "/Users/zhouzixiang/Desktop/tzb/src/sshr"
AI_DIR = "/Users/zhouzixiang/Desktop/tzb/src/ai_sshr_experiment"
for p in [SSHR_DIR, AI_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from paper_data import (
    TABLE_V_SSHR_H,
    TABLE_V_ESOP,
    TABLE_V_XAG,
    TABLE_VI_SSHR_I_CNOT,
    OUR_TABLE_VI_CNOT,
    OUR_TABLE_VII_T,
    TABLE_VII_SSHR_I_T,
)


# ── Test set generation ──────────────────────────────────────────────────────

def make_test_set_all(n: int) -> List[BooleanFunction]:
    """All 2^(2^n) functions (n<=4 only)."""
    return [BooleanFunction(n, tt) for tt in range(1 << (1 << n))]


def make_test_set_random(n: int, seed: int = 42, count: int = 2000) -> List[BooleanFunction]:
    """Random functions with |onset| <= 2^(n-1), matching paper protocol."""
    rng = random.Random(seed)
    N = 1 << n
    out = []
    for _ in range(count):
        k = rng.randint(1, N // 2)
        mints = set(rng.sample(range(N), k))
        tt = sum(1 << i for i in mints)
        out.append(BooleanFunction(n, tt))
    return out


# ── Cost aggregation ─────────────────────────────────────────────────────────

def circuit_cost(circ: QuantumCircuit) -> Dict[str, int]:
    """Return {T, CNOT, ancilla} for a circuit."""
    T, CNOT, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            k = len(g.controls)
            c = mct_cost(k)
            T += c["T"]
            CNOT += c["CNOT"]
            anc += c["ancilla"]
        elif g.type == "CNOT":
            CNOT += 1
    return {"T": T, "CNOT": CNOT, "ancilla": anc}


def verify_circuit(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    """Verify circuit correctness via simulation."""
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        result = circ.simulate(bits)
        expected = bf.evaluate(x)
        if result[n] != expected:
            return False
    return True


# ── Method wrappers ──────────────────────────────────────────────────────────

def run_sshr_h(bf: BooleanFunction) -> QuantumCircuit:
    from sshr_h import sshr_h
    return sshr_h(bf, R=0.75)


def run_sshr_h_paper(bf: BooleanFunction) -> QuantumCircuit:
    from sshr_h_paper import sshr_h_paper
    return sshr_h_paper(bf, R=0.75)


def run_beam(bf: BooleanFunction) -> QuantumCircuit:
    from sshr_beam import sshr_beam
    return sshr_beam(bf, width=50, branch=10, objective="cnot")


def run_mcts(bf: BooleanFunction) -> QuantumCircuit:
    from sshr_mcts_v2 import sshr_mcts_v2
    return sshr_mcts_v2(bf, n_iterations=1000)


def run_xor_beam_rule(bf: BooleanFunction) -> QuantumCircuit:
    from ai_guided_beam import ai_guided_beam
    from rankers import RuleRanker
    result = ai_guided_beam(
        bf, objective="cnot", width=50, branch=10,
        ranker=RuleRanker(), mode="xor", R_threshold=0.75,
    )
    return result.circuit


def run_xor_beam_ml(bf: BooleanFunction) -> QuantumCircuit:
    from ai_guided_beam import ai_guided_beam
    from ml_rankers import LightGBMRanker
    model_path = Path(AI_DIR) / "results" / "models" / "ranker_cnot.txt"
    ranker = LightGBMRanker.load(model_path)
    result = ai_guided_beam(
        bf, objective="cnot", width=50, branch=10,
        ranker=ranker, mode="xor", R_threshold=0.75,
    )
    return result.circuit


# ── Method definitions ───────────────────────────────────────────────────────

# (name, function, which n to run on)
METHODS = [
    ("Our SSHR-H(XOR)",    run_sshr_h,       "all"),
    ("Our SSHR-H(literal)", run_sshr_h_paper, "all"),
    ("Our Beam",            run_beam,         "n56"),
    ("Our MCTS",            run_mcts,         "n56"),
    ("Our XOR-Beam(Rule)",  run_xor_beam_rule,"n56"),
    ("Our XOR-Beam(ML)",    run_xor_beam_ml,  "n56"),
]


# ── Formatting helpers ───────────────────────────────────────────────────────

def pct_delta(our: int, ref: int) -> str:
    """Percentage delta: (our - ref) / ref * 100."""
    if ref == 0:
        return "N/A"
    d = (our - ref) / ref * 100
    return f"{d:+.2f}%"


def pct_reduction(our: int, ref: int) -> str:
    """Percentage reduction vs baseline: (ref - our) / ref * 100."""
    if ref == 0:
        return "N/A"
    d = (ref - our) / ref * 100
    return f"{d:.2f}%"


# ── Main experiment loop ────────────────────────────────────────────────────

def run_experiment(
    n_list: List[int],
    fns_count: int,
    quick: bool,
):
    actual_count = 50 if quick else fns_count

    for n in n_list:
        # Generate test set
        if n <= 4:
            functions = make_test_set_all(n)
            test_desc = f"all {len(functions)} functions"
        else:
            functions = make_test_set_random(n, seed=42, count=actual_count)
            test_desc = f"{len(functions)} random functions (seed=42)"

        print()
        print("=" * 90)
        print(f"  n={n}  ({test_desc})")
        print("=" * 90)

        # Paper reference data
        paper_h = TABLE_V_SSHR_H.get(n)
        paper_esop = TABLE_V_ESOP.get(n)
        paper_xag = TABLE_V_XAG.get(n)
        paper_ilp_cnot = TABLE_VI_SSHR_I_CNOT.get(n)

        # Run each method
        results: Dict[str, Dict[str, int]] = {}
        errors: Dict[str, int] = {}

        for method_name, method_fn, n_scope in METHODS:
            # Determine if we should run this method for this n
            if n_scope == "n56" and n <= 4:
                continue

            print(f"\n  Running {method_name} ...", end="", flush=True)
            t0 = time.time()

            total_T = 0
            total_CNOT = 0
            total_anc = 0
            skip_count = 0
            err_count = 0

            for i, bf in enumerate(functions):
                # Skip zero function (tt=0) — no gates needed, just inflates count
                # Actually paper includes it, so keep it for exact comparison

                try:
                    circ = method_fn(bf)

                    # Verify correctness
                    if not verify_circuit(circ, bf):
                        skip_count += 1
                        continue

                    cost = circuit_cost(circ)
                    total_T += cost["T"]
                    total_CNOT += cost["CNOT"]
                    total_anc += cost["ancilla"]

                except Exception as e:
                    err_count += 1
                    if err_count <= 3:
                        print(f"\n    ERROR at fn {i}: {e}", end="", flush=True)

                if (i + 1) % (1000 if n <= 4 else 100) == 0:
                    print(f" {i+1}", end="", flush=True)

            elapsed = time.time() - t0
            print(f"  ({elapsed:.1f}s)")

            results[method_name] = {
                "T": total_T,
                "CNOT": total_CNOT,
                "ancilla": total_anc,
            }
            if err_count > 0:
                errors[method_name] = err_count

        # ── Print table ────────────────────────────────────────────────────
        print()
        print("-" * 90)
        print(f"  Results for n={n}")
        print("-" * 90)

        # Header
        if paper_esop and paper_xag:
            print(f"  {'Method':<22s} {'T-count':>10s} {'CNOT':>10s} {'Ancilla':>10s} "
                  f"{'vs ESOP':>10s} {'vs XAG':>10s} {'vs Paper-H':>12s}")
        else:
            print(f"  {'Method':<22s} {'T-count':>10s} {'CNOT':>10s} {'Ancilla':>10s} "
                  f"{'vs Paper-H':>12s}")

        print("  " + "-" * (76 if not (paper_esop and paper_xag) else 96))

        # Paper SSHR-H row
        if paper_h:
            ph_T, ph_CNOT, ph_anc = paper_h
            esop_str = ""
            xag_str = ""
            if paper_esop:
                esop_str = f"{pct_reduction(ph_CNOT, paper_esop[1]):>10s}"
            if paper_xag:
                xag_str = f"{pct_reduction(ph_CNOT, paper_xag[1]):>10s}"
            vs_paper = "       --"
            if paper_esop and paper_xag:
                print(f"  {'Paper SSHR-H':<22s} {ph_T:>10d} {ph_CNOT:>10d} {ph_anc:>10d} "
                      f"{esop_str}{xag_str}{vs_paper:>12s}")
            else:
                print(f"  {'Paper SSHR-H':<22s} {ph_T:>10d} {ph_CNOT:>10d} {ph_anc:>10d} "
                      f"{vs_paper:>12s}")

        # Paper SSHR-I row (CNOT objective)
        if paper_ilp_cnot:
            pi_T, pi_CNOT, pi_anc = paper_ilp_cnot
            esop_str = ""
            xag_str = ""
            if paper_esop:
                esop_str = f"{pct_reduction(pi_CNOT, paper_esop[1]):>10s}"
            if paper_xag:
                xag_str = f"{pct_reduction(pi_CNOT, paper_xag[1]):>10s}"
            vs_paper_h = pct_delta(pi_CNOT, ph_CNOT) if paper_h else "N/A"
            if paper_esop and paper_xag:
                print(f"  {'Paper SSHR-I(CNOT)':<22s} {pi_T:>10d} {pi_CNOT:>10d} {pi_anc:>10d} "
                      f"{esop_str}{xag_str}{vs_paper_h:>12s}")
            else:
                print(f"  {'Paper SSHR-I(CNOT)':<22s} {pi_T:>10d} {pi_CNOT:>10d} {pi_anc:>10d} "
                      f"{vs_paper_h:>12s}")

        # Our methods
        for method_name, method_fn, n_scope in METHODS:
            if n_scope == "n56" and n <= 4:
                continue
            if method_name not in results:
                continue
            r = results[method_name]
            our_T = r["T"]
            our_CNOT = r["CNOT"]
            our_anc = r["ancilla"]

            esop_str = ""
            xag_str = ""
            if paper_esop:
                esop_str = f"{pct_reduction(our_CNOT, paper_esop[1]):>10s}"
            if paper_xag:
                xag_str = f"{pct_reduction(our_CNOT, paper_xag[1]):>10s}"
            vs_paper_h = pct_delta(our_CNOT, ph_CNOT) if paper_h else "N/A"
            if paper_esop and paper_xag:
                print(f"  {method_name:<22s} {our_T:>10d} {our_CNOT:>10d} {our_anc:>10d} "
                      f"{esop_str}{xag_str}{vs_paper_h:>12s}")
            else:
                print(f"  {method_name:<22s} {our_T:>10d} {our_CNOT:>10d} {our_anc:>10d} "
                      f"{vs_paper_h:>12s}")

            if method_name in errors:
                print(f"    ({errors[method_name]} errors)")

        # Print paper baselines for reference
        if paper_esop:
            print(f"\n  Paper ref: ESOP CNOT={paper_esop[1]}, T={paper_esop[0]}, Anc={paper_esop[2]}")
        if paper_xag:
            print(f"  Paper ref: XAG  CNOT={paper_xag[1]}, T={paper_xag[0]}, Anc={paper_xag[2]}")

        # ── Table VI comparison (ILP) ─────────────────────────────────────
        if n <= 6 and paper_ilp_cnot:
            our_ilp = OUR_TABLE_VI_CNOT.get(n)
            print()
            print("  " + "-" * 60)
            print(f"  Table VI (ILP CNOT) comparison for n={n}:")
            print("  " + "-" * 60)
            pi_CNOT = paper_ilp_cnot[1]
            print(f"  {'Source':<22s} {'T':>10s} {'CNOT':>10s} {'Anc':>10s} {'vs Paper':>10s}")
            print(f"  {'Paper SSHR-I':<22s} {paper_ilp_cnot[0]:>10d} {pi_CNOT:>10d} {paper_ilp_cnot[2]:>10d} {'--':>10s}")
            if our_ilp:
                our_T_ilp = our_ilp[0] if our_ilp[0] is not None else 0
                our_CNOT_ilp = our_ilp[1]
                our_anc_ilp = our_ilp[2]
                delta = pct_delta(our_CNOT_ilp, pi_CNOT)
                print(f"  {'Our SSHR-I':<22s} {our_T_ilp:>10d} {our_CNOT_ilp:>10d} {our_anc_ilp:>10d} {delta:>10s}")

    print()
    print("=" * 90)
    print("  Done.")
    print("=" * 90)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Paper-format comparison: SSHR-H / Beam / MCTS / XOR-Beam vs paper baselines"
    )
    parser.add_argument(
        "--n", type=int, nargs="+", default=[3, 4, 5, 6],
        help="Variable counts to test (default: 3 4 5 6)",
    )
    parser.add_argument(
        "--fns", type=int, default=2000,
        help="Number of random functions for n>=5 (default: 2000)",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: only 50 functions per n (for testing)",
    )
    args = parser.parse_args()
    run_experiment(args.n, args.fns, args.quick)


if __name__ == "__main__":
    main()
