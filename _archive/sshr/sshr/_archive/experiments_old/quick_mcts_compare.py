"""Quick quality comparison: SSHR-H vs SSHR-MCTS on n=3 (all 256) and n=4 (222 NPN)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_mcts import sshr_mcts
from sshr_i import sshr_i
from npn_reps_n4 import NPN_REPS_N4

def gate_cost(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']; anc = max(anc, c['ancilla'])
        elif g.type == 'CNOT':
            C += 1
    return T, C, anc

def run_n(n, fns, methods, labels):
    totals = {l: [0,0,0] for l in labels}
    times = {l: 0.0 for l in labels}
    for bf in fns:
        if not bf.onset: continue
        for method, label in zip(methods, labels):
            t0 = time.time()
            circ = method(bf)
            times[label] += time.time() - t0
            T, C, anc = gate_cost(circ)
            totals[label][0] += T
            totals[label][1] += C
            totals[label][2] = max(totals[label][2], anc)
    print(f"\nn={n} ({len(fns)} fns)")
    print(f"  {'Method':<22} {'T':>7} {'CNOT':>7} {'Time(s)':>8}")
    print(f"  {'-'*22} {'-'*7} {'-'*7} {'-'*8}")
    h_cnot = None
    for l in labels:
        T, C, anc = totals[l]
        print(f"  {l:<22} {T:>7} {C:>7} {times[l]:>8.1f}")
        if 'SSHR-H' in l:
            h_cnot = C
    if h_cnot:
        print("  CNOT gain vs SSHR-H:")
        for l in labels:
            if 'SSHR-H' not in l:
                gain = (h_cnot - totals[l][1]) / h_cnot * 100
                print(f"    {l}: {gain:+.1f}%")

# ── n=3 all 256 ──────────────────────────────────────────────────────────────
fns3 = [BooleanFunction(3, tt) for tt in range(1, 256) if BooleanFunction(3,tt).onset]
methods3 = [
    sshr_h,
    lambda bf: sshr_mcts(bf, n_iterations=500,  time_limit=99, seed=42),
    lambda bf: sshr_mcts(bf, n_iterations=2000, time_limit=99, seed=42),
    lambda bf: sshr_i(bf, objective='cnot', timeout=30),
]
labels3 = ["SSHR-H", "SSHR-MCTS(500)", "SSHR-MCTS(2000)", "SSHR-I(opt)"]
run_n(3, fns3, methods3, labels3)

# ── n=4 NPN reps ─────────────────────────────────────────────────────────────
fns4 = [BooleanFunction(4, tt) for tt in NPN_REPS_N4 if BooleanFunction(4,tt).onset]
methods4 = [
    sshr_h,
    lambda bf: sshr_mcts(bf, n_iterations=500,  time_limit=99, seed=42),
    lambda bf: sshr_mcts(bf, n_iterations=2000, time_limit=99, seed=42),
]
labels4 = ["SSHR-H", "SSHR-MCTS(500)", "SSHR-MCTS(2000)"]
run_n(4, fns4, methods4, labels4)

print("\nDone.")
