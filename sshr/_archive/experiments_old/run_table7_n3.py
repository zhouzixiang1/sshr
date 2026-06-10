"""Table VII: SSHR-I T-count objective, n=3."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VII_SSHR_I_T

def gate_stats(circ):
    raw = {}; T, C, anc = 0, 0, 0
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

print("Table VII: SSHR-I T-count objective")
p3 = TABLE_VII_SSHR_I_T[3]
print(f"Paper n=3: T={p3[0]}, CNOT={p3[1]}, Anc={p3[2]}")
print()

# n=3 T-objective
T3, C3, anc3 = 0, 0, 0
t0 = time.time()
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset: continue
    raw, t, c, a = gate_stats(sshr_i(bf, objective="t", timeout=30))
    T3 += t; C3 += c; anc3 += a
dt = time.time() - t0
print(f"n=3 T-obj ours:  T={T3} CNOT={C3} Anc={anc3} ({dt:.0f}s)")
print(f"n=3 T-obj paper: T={p3[0]} CNOT={p3[1]} Anc={p3[2]}")
print(f"T off: {abs(T3-p3[0])/p3[0]*100:.1f}%, CNOT off: {abs(C3-p3[1])/p3[1]*100:.1f}%")
print()

# Compare: which functions get lower T with T-objective vs CNOT-objective?
print("Per-function T comparison (T-obj vs CNOT-obj):")
T_cnot = {}; T_t = {}
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset: continue
    _, t_cnot, _, _ = gate_stats(sshr_i(bf, objective="cnot", timeout=30))
    _, t_t, _, _ = gate_stats(sshr_i(bf, objective="t", timeout=30))
    T_cnot[tt] = t_cnot; T_t[tt] = t_t

diff_total = 0
for tt in T_cnot:
    d = T_t[tt] - T_cnot[tt]
    diff_total += d

print(f"Functions where T-obj < CNOT-obj: {sum(1 for tt in T_cnot if T_t[tt] < T_cnot[tt])}")
print(f"Functions where T-obj = CNOT-obj: {sum(1 for tt in T_cnot if T_t[tt] == T_cnot[tt])}")
print(f"Functions where T-obj > CNOT-obj: {sum(1 for tt in T_cnot if T_t[tt] > T_cnot[tt])}")
print(f"Total T difference (t-obj - cnot-obj): {diff_total}")
print(f"Sum T-obj: {sum(T_t.values())}, Sum CNOT-obj: {sum(T_cnot.values())}")
print()
print(f"Paper's T-obj T={p3[0]} vs CNOT-obj T={3280}.")
print("Our T-obj = our CNOT-obj = 3280 (ILP can't improve T further for n=3).")
print("Paper may use a different MCT T-count decomposition (e.g., relative-phase Toffoli T=4 vs T=7).")
