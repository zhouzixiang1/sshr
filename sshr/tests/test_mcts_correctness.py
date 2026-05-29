"""Quick correctness test for SSHR-MCTS on all n=3 functions."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction
from sshr_mcts import sshr_mcts

def verify(circ, bf):
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        for g in circ.gates:
            if g.type == 'CNOT':
                bits[g.target] ^= bits[g.controls[0]]
            elif g.type == 'X':
                bits[g.target] ^= 1
            elif g.type == 'MCT':
                if all(bits[c] for c in g.controls):
                    bits[g.target] ^= 1
        if bits[n] != bf.evaluate(x):
            return False, x
    return True, -1

t0 = time.time()
errors = 0
tested = 0
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset:
        continue
    circ = sshr_mcts(bf, objective='cnot', n_iterations=300, time_limit=10.0, seed=42)
    ok, bad = verify(circ, bf)
    tested += 1
    if not ok:
        print(f'FAIL tt=0x{tt:02x} x={bad}')
        errors += 1

print(f'n=3 correctness: {tested} functions, {errors} errors ({time.time()-t0:.1f}s)')

# Also test n=4 on 10 random functions
import random
rng = random.Random(0)
errors4 = 0
for _ in range(10):
    k = rng.randint(1, 8)
    mints = set(rng.sample(range(16), k))
    tt = sum(1<<i for i in mints)
    bf = BooleanFunction(4, tt)
    if not bf.onset: continue
    circ = sshr_mcts(bf, objective='cnot', n_iterations=200, time_limit=10.0, seed=0)
    ok, bad = verify(circ, bf)
    if not ok:
        print(f'FAIL n=4 tt=0x{tt:04x} x={bad}')
        errors4 += 1
print(f'n=4 spot check: 10 functions, {errors4} errors')
