"""Quick test: SSHR-I on 10 n=5 functions."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i

rng = random.Random(42)
N = 32
fns = []
for _ in range(10):
    k = rng.randint(1, N//2)
    mints = set(rng.sample(range(N), k))
    tt = sum(1 << i for i in mints)
    fns.append(BooleanFunction(5, tt))

T, C, anc = 0, 0, 0
t0 = time.time()
for i, bf in enumerate(fns):
    circ = sshr_i(bf, objective="cnot", timeout=60)
    for g in circ.gates:
        if g.type == "MCT":
            c = mct_cost(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    print(f"  fn {i+1}: done ({time.time()-t0:.1f}s)", flush=True)

print(f"10 n=5 fns: T={T} CNOT={C} Anc={anc} ({time.time()-t0:.0f}s)")
