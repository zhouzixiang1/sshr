"""Run SSHR-H for n=5,6 with 2000 random functions (Tables IV/V)."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from paper_data import TABLE_IV_RAW, TABLE_V_SSHR_H

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
    raw = {}; T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            key = f"{k}-MCT"
            raw[key] = raw.get(key, 0) + 1
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc

print("="*80)
print("SSHR-H: Tables IV & V for n=5,6")
print("="*80)
print(f"\n{'n':>3}  {'X':>7}  {'CNOT':>7}  {'2MCT':>6}  {'3MCT':>6}  {'4MCT':>6}  {'5MCT':>6}  {'6MCT':>6}  |  {'T':>8}  {'C':>8}  {'Anc':>6}  {'time':>6}")

for n in [5, 6]:
    fns = make_test_set(n)
    total = {}; T, C, anc = 0, 0, 0
    t0 = time.time()
    for i, bf in enumerate(fns):
        circ = sshr_h(bf)
        raw, t, c, a = gate_stats(circ)
        T += t; C += c; anc += a
        for k, v in raw.items():
            total[k] = total.get(k, 0) + v
        if (i+1) % 500 == 0:
            print(f"  n={n}: {i+1}/2000 ({time.time()-t0:.0f}s)", flush=True)
    dt = time.time() - t0
    m2 = total.get('2-MCT',0); m3 = total.get('3-MCT',0)
    m4 = total.get('4-MCT',0); m5 = total.get('5-MCT',0); m6 = total.get('6-MCT',0)
    print(f"{n:>3}  {total.get('X',0):>7}  {total.get('CNOT',0):>7}  {m2:>6}  {m3:>6}  {m4:>6}  {m5:>6}  {m6:>6}  |  {T:>8}  {C:>8}  {anc:>6}  {dt:>5.0f}s  [my]")
    if n in TABLE_IV_RAW:
        p4 = TABLE_IV_RAW[n]
        p5 = TABLE_V_SSHR_H[n]
        print(f"{n:>3}  {p4[0]:>7}  {p4[1]:>7}  {p4[2]:>6}  {p4[3]:>6}  {p4[4]:>6}  {p4[5]:>6}  {p4[6]:>6}  |  {p5[0]:>8}  {p5[1]:>8}  {p5[2]:>6}  [paper]")
    print()
