"""Table VII: SSHR-I T-count objective, n=4 NPN reps."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from npn_reps_n4 import NPN_REPS_N4
from paper_data import TABLE_VII_SSHR_I_T

def gate_stats(circ, t4_toffoli=False):
    raw = {}; T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            if t4_toffoli and k == 2:
                T += 4; C += 6; anc += 0
            else:
                c = mct_cost(k)
                T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc

p4 = TABLE_VII_SSHR_I_T[4]
print("Table VII: SSHR-I T-count objective, n=4 (221 NPN reps)")
print(f"Paper: T={p4[0]}, CNOT={p4[1]}, Anc={p4[2]}")
print()

T4, C4, anc4 = 0, 0, 0
raw4 = {}
t0 = time.time()
circs = []
for tt in NPN_REPS_N4:
    bf = BooleanFunction(4, tt)
    if not bf.onset: continue
    circ = sshr_i(bf, objective="t", timeout=60)
    circs.append(circ)
    raw, t, c, a = gate_stats(circ)
    T4 += t; C4 += c; anc4 += a
    for k, v in raw.items(): raw4[k] = raw4.get(k,0)+v
dt = time.time() - t0

print(f"Standard T:    T={T4} CNOT={C4} Anc={anc4} ({dt:.0f}s)")
print(f"  2MCT={raw4.get('2-MCT',0)}, 3MCT={raw4.get('3-MCT',0)}, 4MCT={raw4.get('4-MCT',0)}")

# Recount with T=4 Toffoli
T4_rp = 0; C4_rp = 0
for circ in circs:
    _, t, c, _ = gate_stats(circ, t4_toffoli=True)
    T4_rp += t; C4_rp += c
print(f"T=4 Toffoli:   T={T4_rp} CNOT={C4_rp}")
print()
print(f"Paper:         T={p4[0]} CNOT={p4[1]} Anc={p4[2]}")
print(f"CNOT-obj (for comparison): T=6596 CNOT=5342")
