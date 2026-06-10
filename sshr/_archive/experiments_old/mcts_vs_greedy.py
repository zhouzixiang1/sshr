"""MCTS vs SSHR-H (greedy) for n=3..8, 50 random functions each."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_mcts import sshr_mcts

def gate_cost(circ):
    T, C = 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']
        elif g.type == 'CNOT':
            C += 1
    return T, C

def make_fns(n, count=50, seed=42):
    rng = random.Random(seed)
    N = 1 << n
    fns = []
    while len(fns) < count:
        k = rng.randint(1, N // 2)
        tt = sum(1 << i for i in rng.sample(range(N), k))
        bf = BooleanFunction(n, tt)
        if bf.onset:
            fns.append(bf)
    return fns

print(f"{'n':>3}  {'H_T':>8} {'H_CNOT':>8}  {'M_T':>8} {'M_CNOT':>8}  {'CNOT_gain':>10}  {'Time(s)':>8}")
print("-" * 75)

for n in range(3, 9):
    fns = make_fns(n, count=50)
    TH, CH = 0, 0
    TM, CM = 0, 0
    t0 = time.time()
    for bf in fns:
        th, ch = gate_cost(sshr_h(bf))
        tm, cm = gate_cost(sshr_mcts(bf, n_iterations=500, time_limit=60.0, seed=42))
        TH += th; CH += ch
        TM += tm; CM += cm
    elapsed = time.time() - t0
    gain = 100 * (CH - CM) / CH if CH > 0 else 0
    print(f"{n:>3}  {TH:>8} {CH:>8}  {TM:>8} {CM:>8}  {gain:>+9.1f}%  {elapsed:>8.1f}", flush=True)
