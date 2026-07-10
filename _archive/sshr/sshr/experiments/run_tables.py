"""
Reproduce Tables IV, VI, VII, VIII from the SSHR paper.
Run in mcts-qoracle conda environment (has Gurobi).

Usage:
    python run_tables.py [--tables 4 6 7 8] [--n 3 4 5] [--seed 42]
"""
import argparse, random, time, sys, os, math
from itertools import combinations
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost, mct_cost_rp
from sshr_h import sshr_h
from sshr_i import sshr_i
from paper_data import (
    TABLE_VIII_COUNTS, TABLE_IV_RAW, TABLE_V_SSHR_H,
    TABLE_V_ESOP, TABLE_V_XAG, TABLE_VI_SSHR_I_CNOT, TABLE_VII_SSHR_I_T,
    cnot_count, cnot_gain_vs,
)


# ── Test set generation ──────────────────────────────────────────────────────

def make_test_set(n: int, seed: int = 42, rand_count: int = 2000):
    if n <= 4:
        return [BooleanFunction(n, tt) for tt in range(1 << (1 << n))]
    rng = random.Random(seed)
    N = 1 << n
    out = []
    for _ in range(rand_count):
        k = rng.randint(1, N // 2)
        mints = set(rng.sample(range(N), k))
        tt = sum(1 << i for i in mints)
        out.append(BooleanFunction(n, tt))
    return out


# ── Gate-count accumulator ───────────────────────────────────────────────────

def gate_counts(circ, rp_toffoli=False):
    """Return raw gate-type counts AND decomposed T/CNOT/ancilla.
    rp_toffoli=True uses T=4 for k=2 MCT (relative-phase Toffoli)."""
    raw = {}
    T, CNOT, anc = 0, 0, 0
    cost_fn = mct_cost_rp if rp_toffoli else mct_cost
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            key = f"{k}-MCT"
            raw[key] = raw.get(key, 0) + 1
            c = cost_fn(k)
            T   += c["T"]
            CNOT += c["CNOT"]
            anc  += c["ancilla"]
        elif g.type == "CNOT":
            CNOT += 1
    return raw, {"T": T, "CNOT": CNOT, "ancilla": anc}


# ── Table IV: SSHR-H raw gate counts ────────────────────────────────────────

def run_table4(n_list, seed=42):
    print("\n" + "="*70)
    print("TABLE IV: SSHR-H raw gate counts")
    print(f"{'N':>3}  {'Alg':>8}  {'X':>7}  {'CNOT':>7}  "
          f"{'2-MCT':>6}  {'3-MCT':>6}  {'4-MCT':>6}  {'5-MCT':>6}  {'6-MCT':>6}")
    print("-"*70)
    for n in n_list:
        fns = make_test_set(n, seed)
        totals = {}
        for bf in fns:
            _, dc = gate_counts(sshr_h(bf))
            # Count raw gates
            for g in sshr_h(bf).gates:
                totals[g.type] = totals.get(g.type, 0) + 1
                if g.type == "MCT":
                    k = len(g.controls)
                    totals[f"{k}-MCT"] = totals.get(f"{k}-MCT", 0) + 1
        X    = totals.get("X", 0)
        CNOT = totals.get("CNOT", 0)
        m2   = totals.get("2-MCT", 0)
        m3   = totals.get("3-MCT", 0)
        m4   = totals.get("4-MCT", 0)
        m5   = totals.get("5-MCT", 0)
        m6   = totals.get("6-MCT", 0)
        print(f"{n:>3}  {'SSHR-H':>8}  {X:>7}  {CNOT:>7}  "
              f"{m2:>6}  {m3:>6}  {m4:>6}  {m5:>6}  {m6:>6}")
    # Paper reference
    print("\nPaper Table IV reference (SSHR-H):")
    for n in n_list:
        if n in TABLE_IV_RAW:
            v = TABLE_IV_RAW[n]
            print(f"  n={n}: X={v[0]}  CNOT={v[1]}  2MCT={v[2]}  3MCT={v[3]}  "
                  f"4MCT={v[4]}  5MCT={v[5]}  6MCT={v[6]}")


# ── Table V: SSHR-H T/CNOT/ancilla vs XAG ──────────────────────────────────

def run_table5(n_list, seed=42):
    print("\n" + "="*70)
    print("TABLE V: SSHR-H T-count / CNOT / Ancilla")
    print(f"{'N':>3}  {'T':>10}  {'CNOT':>10}  {'Ancilla':>9}")
    print("-"*40)
    for n in n_list:
        fns = make_test_set(n, seed)
        T, C, anc = 0, 0, 0
        for bf in fns:
            _, dc = gate_counts(sshr_h(bf))
            T += dc["T"]; C += dc["CNOT"]; anc += dc["ancilla"]
        print(f"{n:>3}  {T:>10}  {C:>10}  {anc:>9}")
    print("\nPaper Table V reference (SSHR-H):")
    for n in n_list:
        if n in TABLE_V_SSHR_H:
            v = TABLE_V_SSHR_H[n]
            print(f"  n={n}: T={v[0]}  CNOT={v[1]}  Ancilla={v[2]}")


# ── Table VI: SSHR-I CNOT objective ─────────────────────────────────────────

def run_table6(n_list, seed=42, timeout=120):
    print("\n" + "="*70)
    print("TABLE VI: SSHR-I (objective = min CNOT)")
    print(f"{'N':>3}  {'T':>8}  {'CNOT':>8}  {'Ancilla':>9}  {'CNOT%vsESOP':>12}  {'CNOT%vsXAG':>11}  {'time(s)':>8}")
    print("-"*75)
    for n in n_list:
        fns = make_test_set(n, seed)
        T, C, anc = 0, 0, 0
        t0 = time.time()
        for bf in fns:
            _, dc = gate_counts(sshr_i(bf, objective="cnot", timeout=timeout))
            T += dc["T"]; C += dc["CNOT"]; anc += dc["ancilla"]
        dt = time.time() - t0
        esop_gain = cnot_gain_vs(C, TABLE_V_ESOP, n) if n in TABLE_V_ESOP else float('nan')
        xag_gain  = cnot_gain_vs(C, TABLE_V_XAG, n) if n in TABLE_V_XAG else float('nan')
        print(f"{n:>3}  {T:>8}  {C:>8}  {anc:>9}  {esop_gain:>11.1f}%  {xag_gain:>10.1f}%  {dt:>7.1f}s")
    print("\nPaper Table VI reference (SSHR-I CNOT obj):")
    for n in n_list:
        if n in TABLE_VI_SSHR_I_CNOT:
            v = TABLE_VI_SSHR_I_CNOT[n]
            print(f"  n={n}: T={v[0]}  CNOT={v[1]}  Ancilla={v[2]}")


# ── Table VII: SSHR-I T-count objective ─────────────────────────────────────

def run_table7(n_list, seed=42, timeout=120):
    print("\n" + "="*70)
    print("TABLE VII: SSHR-I (objective = min T-count)")
    print(f"{'N':>3}  {'T':>8}  {'CNOT':>8}  {'Ancilla':>9}  {'time(s)':>8}")
    print("-"*45)
    for n in n_list:
        fns = make_test_set(n, seed)
        T, C, anc = 0, 0, 0
        t0 = time.time()
        for bf in fns:
            _, dc = gate_counts(sshr_i(bf, objective="t", timeout=timeout), rp_toffoli=True)
            T += dc["T"]; C += dc["CNOT"]; anc += dc["ancilla"]
        dt = time.time() - t0
        print(f"{n:>3}  {T:>8}  {C:>8}  {anc:>9}  {dt:>7.1f}s")
    print("\nPaper Table VII reference (SSHR-I T obj):")
    for n in n_list:
        if n in TABLE_VII_SSHR_I_T:
            v = TABLE_VII_SSHR_I_T[n]
            print(f"  n={n}: T={v[0]}  CNOT={v[1]}  Ancilla={v[2]}")


# ── Table VIII: Optimization space ──────────────────────────────────────────

def run_table8():
    from parallelotope_enum import enumerate_parallelotopes
    print("\n" + "="*50)
    print("TABLE VIII: Optimization space ESOP vs SSHR")
    print(f"{'n':>4}  {'ESOP':>8}  {'SSHR':>8}  {'Factor':>7}")
    print("-"*30)
    for n in range(3, 9):
        esop = sum(math.comb(n, k) * (2**k) for k in range(0, n+1))  # k=0 = constant "1" term
        universe = list(range(1 << n))
        ps = enumerate_parallelotopes(universe, n)
        sshr = len(ps) + len(universe)  # +2^n singleton (dim-0) parallelotopes
        factor = sshr / esop
        match = "✓" if sshr == TABLE_VIII_COUNTS.get(n, -1) else f"(paper={TABLE_VIII_COUNTS.get(n,'?')})"
        print(f"{n:>4}  {esop:>8}  {sshr:>8}  {factor:>6.1f}x  {match}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", nargs="+", type=int, default=[8], choices=[4,5,6,7,8])
    parser.add_argument("--n", nargs="+", type=int, default=[3])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    if 8 in args.tables:
        run_table8()
    if 4 in args.tables:
        run_table4(args.n, args.seed)
    if 5 in args.tables:
        run_table5(args.n, args.seed)
    if 6 in args.tables:
        run_table6(args.n, args.seed, args.timeout)
    if 7 in args.tables:
        run_table7(args.n, args.seed, args.timeout)


if __name__ == "__main__":
    main()
