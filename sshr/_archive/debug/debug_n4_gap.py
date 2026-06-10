"""Debug the n=4 NPN reps SSHR-I gap vs paper (T=6596 vs 6028).
Check per-function: is SSHR-I <= ESOP? Are any functions degenerate?"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from esop_ilp import esop_ilp
from block_synth import block_cnot_cost, block_t_cost
from parallelotope_enum import enumerate_parallelotopes
from parallelotope import Parallelotope
from npn_reps_n4 import NPN_REPS_N4

def cnot_cost(circ):
    C = 0
    for g in circ.gates:
        if g.type == "MCT":
            C += mct_cost(len(g.controls))["CNOT"]
        elif g.type == "CNOT":
            C += 1
    return C

# Check: for each NPN rep, get SSHR-I and ESOP CNOT costs
print("Comparing per-function SSHR-I vs ESOP CNOT costs for n=4 NPN reps")
print(f"{'tt':>8}  {'SSHR-I':>7}  {'ESOP':>7}  {'diff':>6}  {'ILP-used?':>10}")

total_sshr = 0; total_esop = 0
worse_count = 0; equal_count = 0; better_count = 0
high_cost = []

for tt in NPN_REPS_N4:
    bf = BooleanFunction(4, tt)
    if not bf.onset:
        continue

    # Check if ILP is used (not fallback)
    onset = bf.onset
    all_minterms = list(range(16))
    plist = enumerate_parallelotopes(all_minterms, 4)
    seen = {p.vertices() for p in plist}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen:
            plist.append(Parallelotope(v, []))
    onset_set = set(onset)
    plist_filtered = [p for p in plist if p.vertices() & onset_set]

    circ_sshr = sshr_i(bf, objective="cnot", timeout=30)
    circ_esop = esop_ilp(bf, objective="cnot", timeout=30)

    c_sshr = cnot_cost(circ_sshr)
    c_esop = cnot_cost(circ_esop)

    total_sshr += c_sshr
    total_esop += c_esop

    diff = c_sshr - c_esop
    if diff > 0:
        worse_count += 1
        if diff > 5:
            high_cost.append((tt, c_sshr, c_esop, diff))
    elif diff < 0:
        better_count += 1
    else:
        equal_count += 1

print(f"\nSummary: total SSHR={total_sshr} ESOP={total_esop}")
print(f"SSHR worse than ESOP: {worse_count}")
print(f"SSHR equal to ESOP:   {equal_count}")
print(f"SSHR better than ESOP: {better_count}")
print(f"\nCases where SSHR-I > ESOP by >5 CNOT:")
for tt, s, e, d in sorted(high_cost, key=lambda x: -x[3])[:20]:
    print(f"  tt={tt:6d} (0x{tt:04x}) SSHR={s} ESOP={e} diff=+{d}")

# Spot check: for tt with biggest gap, check optimal manually
if high_cost:
    tt, c_sshr, c_esop, d = max(high_cost, key=lambda x: x[3])
    print(f"\nSpot-check worst case: tt={tt} (0x{tt:04x})")
    bf = BooleanFunction(4, tt)
    print(f"  Onset: {bf.onset}")
    print(f"  Onset size: {len(bf.onset)}")

    # List all parallelotopes from full universe with their costs
    pall = enumerate_parallelotopes(list(range(16)), 4)
    for v in range(16):
        s = frozenset([v])
        if not any(p.vertices() == s for p in pall):
            pall.append(Parallelotope(v, []))
    pall_f = [p for p in pall if p.vertices() & set(bf.onset)]
    print(f"  Parallelotopes intersecting onset: {len(pall_f)}")
    print(f"  Costs: {sorted(set(block_cnot_cost(p, 4) for p in pall_f))}")
    print(f"  SSHR-I CNOT: {c_sshr}, ESOP CNOT: {c_esop}")
