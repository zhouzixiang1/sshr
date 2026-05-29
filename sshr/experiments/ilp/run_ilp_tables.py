"""
Reproduce paper Table VI (SSHR-I CNOT objective) and Table VII (SSHR-I T objective).

Usage:
  /opt/anaconda3/envs/sshr/bin/python experiments/ilp/run_ilp_tables.py
  /opt/anaconda3/envs/sshr/bin/python experiments/ilp/run_ilp_tables.py --n 3 4 --timeout 60
  /opt/anaconda3/envs/sshr/bin/python experiments/ilp/run_ilp_tables.py --n 5 6 --timeout 120 --fns 2000

Requirements:
  - Gurobi (gurobipy) license in sshr conda environment
  - Run with: /opt/anaconda3/envs/sshr/bin/python
"""
import sys
import os
import time
import random
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT, TABLE_VII_SSHR_I_T
from npn_reps_n4 import NPN_REPS_N4


def gate_cost(circ, rp_toffoli=False):
    """Compute T/CNOT/ancilla cost.

    rp_toffoli=True: use RP-Toffoli cost (k=2 MCT → T=4 instead of 7).
    Used when reporting Table VII T-objective results.
    """
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            k = len(g.controls)
            c = mct_cost(k)
            t_cost = 4 if (rp_toffoli and k == 2) else c['T']
            T += t_cost; C += c['CNOT']; anc += c['ancilla']
        elif g.type == 'CNOT':
            C += 1
    return T, C, anc


def get_fns(n, count=2000, seed=42):
    """Get test functions for each n (matching paper's test set)."""
    if n == 3:
        # All 255 non-zero functions
        return [BooleanFunction(3, tt) for tt in range(1, 256) if BooleanFunction(3, tt).onset]
    elif n == 4:
        # 221 non-zero NPN representatives
        return [BooleanFunction(4, tt) for tt in NPN_REPS_N4 if BooleanFunction(4, tt).onset]
    else:
        # 2000 random functions (seed=42), |onset| <= 2^(n-1)
        rng = random.Random(seed)
        N = 1 << n
        fns = []
        while len(fns) < count:
            k = rng.randint(1, N // 2)
            tt = sum(1 << i for i in rng.sample(range(N), k))
            bf = BooleanFunction(n, tt)
            if bf.onset:
                fns.append(bf)
        return fns


def verify_circuit(circ, bf):
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            return False
    return True


def run_ilp(n, objective, timeout, fns, ref_table, label):
    """Run SSHR-I on all fns with given objective and report results."""
    T_total, C_total, anc_total = 0, 0, 0
    fails = 0
    timeouts = 0
    t0 = time.time()

    print(f"\n{'─'*72}")
    print(f"n={n}  {label}  [{len(fns)} functions, timeout={timeout}s]")
    print(f"{'─'*72}")

    for i, bf in enumerate(fns):
        t_fn = time.time()
        circ = sshr_i(bf, objective=objective, timeout=timeout)
        elapsed_fn = time.time() - t_fn

        if elapsed_fn >= timeout * 0.99:
            timeouts += 1

        if not verify_circuit(circ, bf):
            fails += 1

        T, C, anc = gate_cost(circ, rp_toffoli=(objective == 't'))
        T_total += T; C_total += C; anc_total += anc

        if (i + 1) % 50 == 0 or (i + 1) == len(fns):
            elapsed = time.time() - t0
            print(f"  {i+1:4d}/{len(fns)}  T={T_total:8d}  CNOT={C_total:8d}  "
                  f"timeouts={timeouts}  ({elapsed:.0f}s)", flush=True)

    dt = time.time() - t0
    ref = ref_table.get(n)

    print(f"\n  Result:  T={T_total}  CNOT={C_total}  Anc={anc_total}  fails={fails}  "
          f"timeouts={timeouts}  ({dt:.1f}s)")
    if ref:
        dT = T_total - ref[0]
        dC = C_total - ref[1]
        print(f"  Paper:   T={ref[0]}  CNOT={ref[1]}  Anc={ref[2]}")
        pct_t = 100 * dT / ref[0] if ref[0] else 0
        pct_c = 100 * dC / ref[1] if ref[1] else 0
        print(f"  Delta:   T={dT:+d} ({pct_t:+.1f}%)  CNOT={dC:+d} ({pct_c:+.1f}%)")
    return T_total, C_total, anc_total, fails, timeouts, dt


def main():
    parser = argparse.ArgumentParser(description='Reproduce Table VI/VII: SSHR-I ILP results')
    parser.add_argument('--n', type=int, nargs='+', default=[3, 4, 5, 6])
    parser.add_argument('--timeout', type=float, default=None,
                        help='ILP timeout per function (default: 30s for n≤4, 120s for n≥5)')
    parser.add_argument('--fns', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--cnot-only', action='store_true', help='Only run CNOT objective')
    parser.add_argument('--t-only', action='store_true', help='Only run T objective')
    args = parser.parse_args()

    print("=" * 72)
    print("SSHR-I ILP Reproduction: Table VI (CNOT) and Table VII (T)")
    print("=" * 72)

    summary_cnot = {}
    summary_t = {}

    for n in args.n:
        fns = get_fns(n, count=args.fns, seed=args.seed)
        timeout = args.timeout if args.timeout else (30 if n <= 4 else 120)

        if not args.t_only:
            T, C, anc, fails, tos, dt = run_ilp(
                n, 'cnot', timeout, fns, TABLE_VI_SSHR_I_CNOT,
                label='Table VI: CNOT objective'
            )
            summary_cnot[n] = (T, C, anc, fails, tos, dt)

        if not args.cnot_only:
            T, C, anc, fails, tos, dt = run_ilp(
                n, 't', timeout, fns, TABLE_VII_SSHR_I_T,
                label='Table VII: T objective (RP-Toffoli)'
            )
            summary_t[n] = (T, C, anc, fails, tos, dt)

    # Summary table
    print(f"\n{'='*72}")
    print("SUMMARY")
    print(f"{'='*72}")

    if summary_cnot:
        print("\nTable VI — CNOT objective:")
        print(f"  {'n':>3}  {'T':>8}  {'CNOT':>8}  {'Anc':>6}  {'dT':>8}  {'dCNOT':>8}  {'TO':>4}  {'time':>7}")
        print(f"  {'─'*3}  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*8}  {'─'*4}  {'─'*7}")
        for n, (T, C, anc, fails, tos, dt) in summary_cnot.items():
            ref = TABLE_VI_SSHR_I_CNOT.get(n)
            if ref:
                dT = f'{T-ref[0]:+d}'; dC = f'{C-ref[1]:+d}'
            else:
                dT = 'n/a'; dC = 'n/a'
            print(f"  {n:>3}  {T:>8}  {C:>8}  {anc:>6}  {dT:>8}  {dC:>8}  {tos:>4}  {dt:>6.0f}s")

    if summary_t:
        print("\nTable VII — T objective (RP-Toffoli):")
        print(f"  {'n':>3}  {'T':>8}  {'CNOT':>8}  {'Anc':>6}  {'dT':>8}  {'dCNOT':>8}  {'TO':>4}  {'time':>7}")
        print(f"  {'─'*3}  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*8}  {'─'*8}  {'─'*4}  {'─'*7}")
        for n, (T, C, anc, fails, tos, dt) in summary_t.items():
            ref = TABLE_VII_SSHR_I_T.get(n)
            if ref:
                dT = f'{T-ref[0]:+d}'; dC = f'{C-ref[1]:+d}'
            else:
                dT = 'n/a'; dC = 'n/a'
            print(f"  {n:>3}  {T:>8}  {C:>8}  {anc:>6}  {dT:>8}  {dC:>8}  {tos:>4}  {dt:>6.0f}s")


if __name__ == '__main__':
    main()
