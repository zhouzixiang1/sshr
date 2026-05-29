"""Quick n=4 SSHR-I CNOT objective check."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT

n = 4
T, C, anc = 0, 0, 0
total_fns = 0
t0 = time.time()

for tt in range(1 << (1 << n)):
    bf = BooleanFunction(n, tt)
    if not bf.onset:
        continue
    circ = sshr_i(bf, objective="cnot", timeout=30)
    total_fns += 1
    for g in circ.gates:
        if g.type == "MCT":
            k = len(g.controls)
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    if total_fns % 1000 == 0:
        print(f"  Done {total_fns}/65535 (t={time.time()-t0:.0f}s) T={T} CNOT={C} Anc={anc}", flush=True)

dt = time.time() - t0
print(f"\nFinal n=4 SSHR-I CNOT: T={T} CNOT={C} Anc={anc} ({dt:.0f}s)")
print(f"Paper: T={TABLE_VI_SSHR_I_CNOT[4][0]} CNOT={TABLE_VI_SSHR_I_CNOT[4][1]} Anc={TABLE_VI_SSHR_I_CNOT[4][2]}")
