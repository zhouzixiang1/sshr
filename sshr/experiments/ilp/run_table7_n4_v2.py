"""Table VII n=4: T-obj two-stage with relative-phase Toffoli."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost, mct_cost_rp
from sshr_i import sshr_i
from npn_reps_n4 import NPN_REPS_N4
from paper_data import TABLE_VII_SSHR_I_T

def gs(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            c = mct_cost_rp(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return T, C, anc

T4, C4, anc4 = 0, 0, 0
t0 = time.time()
for tt in NPN_REPS_N4:
    bf = BooleanFunction(4, tt)
    if not bf.onset: continue
    t, c, a = gs(sshr_i(bf, objective="t", timeout=60))
    T4 += t; C4 += c; anc4 += a
dt = time.time() - t0
print(f"n=4 T-obj two-stage (RP): T={T4} CNOT={C4} Anc={anc4} ({dt:.0f}s)")
p4 = TABLE_VII_SSHR_I_T[4]
print(f"Paper n=4 T-obj: T={p4[0]} CNOT={p4[1]} Anc={p4[2]}")
