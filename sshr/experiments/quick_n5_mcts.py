"""Quick n=5 MCTS vs SSHR-H on 50 functions."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_mcts import sshr_mcts

def costs(circ):
    T, C = 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']
        elif g.type == 'CNOT':
            C += 1
    return T, C

rng = random.Random(42)
n, N = 5, 32
fns = []
while len(fns) < 50:
    k = rng.randint(1, N//2)
    tt = sum(1 << i for i in rng.sample(range(N), k))
    bf = BooleanFunction(n, tt)
    if bf.onset: fns.append(bf)

TH, CH, TM100, CM100, TM500, CM500 = 0,0,0,0,0,0
t0 = time.time()
for i, bf in enumerate(fns):
    th, ch = costs(sshr_h(bf))
    tm1, cm1 = costs(sshr_mcts(bf, n_iterations=100,  time_limit=99, seed=0))
    tm5, cm5 = costs(sshr_mcts(bf, n_iterations=500,  time_limit=99, seed=0))
    TH+=th; CH+=ch; TM100+=tm1; CM100+=cm1; TM500+=tm5; CM500+=cm5
    if (i+1) % 10 == 0:
        print(f'  {i+1}/50 ({time.time()-t0:.0f}s)', flush=True)

print(f'\nn=5 (50 fns):')
print(f'  SSHR-H:          T={TH} CNOT={CH}')
print(f'  SSHR-MCTS(100):  T={TM100} CNOT={CM100}  gain={100*(CH-CM100)/CH:.1f}%')
print(f'  SSHR-MCTS(500):  T={TM500} CNOT={CM500}  gain={100*(CH-CM500)/CH:.1f}%')
print(f'  Time: {time.time()-t0:.0f}s')
