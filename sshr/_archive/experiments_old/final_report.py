"""
Final reproduction report: SSHR paper Tables IV-VIII.
"""
import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_i import sshr_i
from parallelotope_enum import enumerate_parallelotopes
from paper_data import (
    TABLE_VIII_COUNTS, TABLE_IV_RAW, TABLE_V_SSHR_H,
    TABLE_V_ESOP, TABLE_V_XAG, TABLE_VI_SSHR_I_CNOT,
    cnot_gain_vs,
)


def gate_stats(circ):
    raw = {}
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc


print("=" * 70)
print("SSHR Paper Reproduction Report")
print("=" * 70)

# ── TABLE VIII ────────────────────────────────────────────────────────────
print("\n--- Table VIII: Optimization Space ESOP vs SSHR ---")
print(f"{'n':>4}  {'ESOP':>8}  {'SSHR':>8}  {'Factor':>7}  Match")
for n in range(3, 9):
    esop = sum(math.comb(n, k) * (2**k) for k in range(n+1))
    ps = enumerate_parallelotopes(list(range(1 << n)), n)
    sshr = len(ps) + (1 << n)
    match = "✓" if sshr == TABLE_VIII_COUNTS.get(n) else f"(paper={TABLE_VIII_COUNTS.get(n)})"
    print(f"  {n:>2}  {esop:>8}  {sshr:>8}  {sshr/esop:>6.1f}x  {match}")

# ── TABLE V: SSHR-H n=3,4 ────────────────────────────────────────────────
print("\n--- Table IV/V: SSHR-H Gate Counts ---")
print(f"{'n':>3}  {'X':>7}  {'CNOT':>7}  {'2MCT':>6}  {'3MCT':>6}  {'4MCT':>6}  |  {'T':>8}  {'CNOT_t':>8}  {'Anc':>6}")
for n in [3, 4]:
    bfs = [BooleanFunction(n, tt) for tt in range(1 << (1 << n))]
    total = {}; T, C, anc = 0, 0, 0
    for bf in bfs:
        raw, t, c, a = gate_stats(sshr_h(bf))
        T += t; C += c; anc += a
        for k, v in raw.items():
            total[k] = total.get(k, 0) + v
    print(f"  {n:>2}  {total.get('X',0):>7}  {total.get('CNOT',0):>7}  "
          f"{total.get('2-MCT',0):>6}  {total.get('3-MCT',0):>6}  {total.get('4-MCT',0):>6}  |  "
          f"{T:>8}  {C:>8}  {anc:>6}  [my]")
    if n in TABLE_IV_RAW:
        p4 = TABLE_IV_RAW[n]
        p5 = TABLE_V_SSHR_H[n]
        print(f"  {n:>2}  {p4[0]:>7}  {p4[1]:>7}  {p4[2]:>6}  {p4[3]:>6}  {p4[4]:>6}  |  "
              f"{p5[0]:>8}  {p5[1]:>8}  {p5[2]:>6}  [paper]")
    print()

# ── TABLE VI: SSHR-I n=3 CNOT objective ──────────────────────────────────
print("--- Table VI: SSHR-I CNOT objective ---")
for n in [3]:
    bfs = [BooleanFunction(n, tt) for tt in range(1, 1 << (1 << n)) if BooleanFunction(n, tt).onset]
    T, C, anc = 0, 0, 0
    t0 = time.time()
    for bf in bfs:
        _, t, c, a = gate_stats(sshr_i(bf, objective="cnot", timeout=30))
        T += t; C += c; anc += a
    dt = time.time() - t0
    cg = cnot_gain_vs(C, TABLE_V_ESOP, n) if n in TABLE_V_ESOP else 0
    xg = cnot_gain_vs(C, TABLE_V_XAG, n) if n in TABLE_V_XAG else 0
    print(f"  n={n}: T={T} CNOT={C} Anc={anc} ({dt:.0f}s) CNOT_gain_vs_ESOP={cg:.1f}%")
    if n in TABLE_VI_SSHR_I_CNOT:
        p = TABLE_VI_SSHR_I_CNOT[n]
        print(f"  Paper:  T={p[0]} CNOT={p[1]} Anc={p[2]}")
    print()

# n=4 on NPN representatives
try:
    from npn_reps_n4 import NPN_REPS_N4
    T4, C4, anc4 = 0, 0, 0
    t0 = time.time()
    for tt in NPN_REPS_N4:
        bf = BooleanFunction(4, tt)
        if not bf.onset: continue
        _, t, c, a = gate_stats(sshr_i(bf, objective="cnot", timeout=30))
        T4 += t; C4 += c; anc4 += a
    dt4 = time.time() - t0
    print(f"  n=4 (222 NPN reps): T={T4} CNOT={C4} Anc={anc4} ({dt4:.0f}s)")
    if 4 in TABLE_VI_SSHR_I_CNOT:
        p = TABLE_VI_SSHR_I_CNOT[4]
        print(f"  Paper:              T={p[0]} CNOT={p[1]} Anc={p[2]}")
except ImportError:
    print("  n=4 NPN reps not available")
