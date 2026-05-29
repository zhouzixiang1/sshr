"""Quick sample of n=4 functions to verify SSHR-I is working and estimate totals."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT

n = 4
rng = random.Random(42)
all_tts = list(range(1, 1 << (1 << n)))  # all non-zero truth tables for n=4

# Estimate: sample 500 functions
sample = rng.sample(all_tts, 500)
T, C, anc = 0, 0, 0
fails = 0
t0 = time.time()

for tt in sample:
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
    for g in circ.gates:
        if g.type == "MCT":
            k = len(g.controls)
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1

dt = time.time() - t0
print(f"Sample of 500 n=4 functions: T={T}, CNOT={C}, Anc={anc}, fails={fails}, t={dt:.1f}s")
print(f"Estimated full (65535): T~{T*65535//500}, CNOT~{C*65535//500}")
print(f"Paper n=4: T={TABLE_VI_SSHR_I_CNOT[4][0]}, CNOT={TABLE_VI_SSHR_I_CNOT[4][1]}, Anc={TABLE_VI_SSHR_I_CNOT[4][2]}")
