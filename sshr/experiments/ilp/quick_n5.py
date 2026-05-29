"""Quick n=5 SSHR-I sample (first 200 functions) to estimate timing."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT

rng = random.Random(42)
N = 32
fns = []
for _ in range(200):
    k = rng.randint(1, N//2)
    mints = set(rng.sample(range(N), k))
    tt = sum(1 << i for i in mints)
    fns.append(BooleanFunction(5, tt))

def cnot(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            c = mct_cost(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT": C += 1
    return T, C, anc

T, C, anc = 0, 0, 0
t0 = time.time()
for i, bf in enumerate(fns):
    t, c, a = cnot(sshr_i(bf, objective="cnot", timeout=60))
    T += t; C += c; anc += a
    if (i+1) % 50 == 0:
        print(f"  {i+1}/200 T={T} CNOT={C} ({time.time()-t0:.0f}s)", flush=True)

dt = time.time() - t0
print(f"\n200 functions: T={T} CNOT={C} Anc={anc} ({dt:.0f}s)")
print(f"Extrapolated to 2000: T~{T*10} CNOT~{C*10} Anc~{anc*10}")
print(f"Paper n=5: T={TABLE_VI_SSHR_I_CNOT[5][0]} CNOT={TABLE_VI_SSHR_I_CNOT[5][1]} Anc={TABLE_VI_SSHR_I_CNOT[5][2]}")
print(f"Est. time for 2000: ~{dt*10:.0f}s")
