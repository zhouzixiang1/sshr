"""Run Table VI SSHR-I (CNOT objective) for n=5, 2000 random functions."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT, TABLE_V_ESOP, cnot_count

def make_test_set(n, seed=42, rand_count=2000):
    rng = random.Random(seed)
    N = 1 << n
    out = []
    for _ in range(rand_count):
        k = rng.randint(1, N // 2)
        mints = set(rng.sample(range(N), k))
        tt = sum(1 << i for i in mints)
        out.append(BooleanFunction(n, tt))
    return out

def gate_stats(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == "MCT":
            c = mct_cost(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return T, C, anc

n = 5
fns = make_test_set(n)
T, C, anc = 0, 0, 0
fails = 0
t0 = time.time()

for i, bf in enumerate(fns):
    circ = sshr_i(bf, objective="cnot", timeout=60)
    # Verify correctness
    ok = True
    for x in range(1 << n):
        bits = [(x >> j) & 1 for j in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            ok = False; fails += 1; break
    t, c, a = gate_stats(circ)
    T += t; C += c; anc += a
    if (i+1) % 200 == 0:
        dt = time.time() - t0
        print(f"  n=5: {i+1}/2000 T={T} CNOT={C} ({dt:.0f}s)", flush=True)

dt = time.time() - t0
print(f"\nSSHR-I n=5 (2000 random, seed=42): T={T} CNOT={C} Anc={anc} fails={fails} ({dt:.0f}s)")
p5 = TABLE_VI_SSHR_I_CNOT[5]
print(f"Paper Table VI n=5:                T={p5[0]} CNOT={p5[1]} Anc={p5[2]}")
esop_c = cnot_count(TABLE_V_ESOP, 5)
print(f"Paper ESOP n=5:                    CNOT={esop_c}")
if C < esop_c:
    print(f"CNOT gain vs paper ESOP: {(esop_c-C)/esop_c*100:.1f}%")
