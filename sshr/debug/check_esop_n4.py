"""Quick ESOP check on 221 NPN reps for n=4."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from esop_ilp import esop_ilp
from npn_reps_n4 import NPN_REPS_N4

def gate_stats(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            k = len(g.controls)
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return T, C, anc

T, C, anc = 0, 0, 0
n_tested = 0
t0 = time.time()
for tt in NPN_REPS_N4:
    bf = BooleanFunction(4, tt)
    if not bf.onset:
        continue
    circ = esop_ilp(bf, objective="cnot", timeout=60)
    t, c, a = gate_stats(circ)
    T += t; C += c; anc += a
    n_tested += 1
    if n_tested % 50 == 0:
        print(f"  {n_tested}/221 done ({time.time()-t0:.0f}s)")

dt = time.time() - t0
print(f"\nEsop-ILP on {n_tested} NPN reps: T={T} CNOT={C} Anc={anc} ({dt:.0f}s)")
print(f"Paper ESOP n=4: CNOT=9047")
print(f"Difference: CNOT={C - 9047}")
