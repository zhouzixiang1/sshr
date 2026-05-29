"""Run SSHR-I on 222 NPN representatives for n=4 and compare with paper."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from npn_reps_n4 import NPN_REPS_N4

n = 4
T, C, anc = 0, 0, 0
fails = 0
total_fns = 0
t0 = time.time()

for tt in NPN_REPS_N4:
    bf = BooleanFunction(n, tt)
    if not bf.onset:
        continue
    circ = sshr_i(bf, objective="cnot", timeout=30)

    # Verify
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            fails += 1
            break

    cost = circ.cost()
    T += cost["T"]; C += cost["CNOT"]; anc += cost["ancilla"]
    total_fns += 1

    if total_fns % 50 == 0:
        print(f"  {total_fns}/222 T={T} CNOT={C} ({time.time()-t0:.0f}s)", flush=True)

dt = time.time() - t0
p4 = TABLE_VI_SSHR_I_CNOT[4]
print(f"\nSSHR-I on 222 NPN reps: T={T} CNOT={C} Anc={anc} fails={fails} ({dt:.0f}s)")
print(f"Paper n=4:              T={p4[0]} CNOT={p4[1]} Anc={p4[2]}")
print(f"Difference:             T={T-p4[0]} CNOT={C-p4[1]}")

# Also run n=3 NPN reps (14 functions) as sanity check
from npn_reps2 import get_npn_reps
reps3 = get_npn_reps(3)
T3, C3, anc3 = 0, 0, 0
for tt in reps3:
    bf = BooleanFunction(3, tt)
    if not bf.onset: continue
    circ = sshr_i(bf, objective="cnot", timeout=10)
    cost = circ.cost()
    T3 += cost["T"]; C3 += cost["CNOT"]; anc3 += cost["ancilla"]
print(f"\nSSHR-I on 14 NPN reps (n=3): T={T3} CNOT={C3} Anc={anc3}")
print(f"Paper n=3 NPN: T=3280/14*14? (all 255 fns: T=3280)")
