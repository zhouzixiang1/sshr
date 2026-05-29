"""Diagnose MCTS quality issues."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction
from sshr_mcts import _greedy_cost_from_state, _get_cost_fn
from parallelotope_enum import enumerate_parallelotopes
from parallelotope import Parallelotope

bf = BooleanFunction(3, 0x96)
n = 3
full_universe = list(range(8))
all_p = enumerate_parallelotopes(full_universe, n)
for v in range(8):
    all_p.append(Parallelotope(v, []))
cost_fn = _get_cost_fn('cnot')
costs = [float(cost_fn(p, n)) for p in all_p]
vert_sets = [p.vertices() for p in all_p]
A_frozen = frozenset(bf.onset)

# 1. How many parallelotopes fit in A (all vertices in A)?
subset_valid = [i for i, vs in enumerate(vert_sets) if vs.issubset(A_frozen)]
ratio_valid = [i for i, vs in enumerate(vert_sets) if len(vs & A_frozen) / len(vs) >= 0.25]
print(f'Total parallelotopes: {len(all_p)}')
print(f'Valid (vs ⊆ A):        {len(subset_valid)}')
print(f'Valid (ratio>=0.25):   {len(ratio_valid)}')
print(f'onset = {bf.onset}')

# 2. Greedy cost with subset-only filter (correct approach)
A2 = set(bf.onset)
cost2 = 0.0
steps = []
for _ in range(20):
    if not A2: break
    best_i, best_score = -1, -1.0
    for i, vs in enumerate(vert_sets):
        if not vs.issubset(A2): continue
        score = len(vs) - costs[i] * 1e-9
        if score > best_score:
            best_score = score
            best_i = i
    if best_i == -1: break
    steps.append((best_i, costs[best_i], vert_sets[best_i]))
    cost2 += costs[best_i]
    A2 ^= vert_sets[best_i]
print(f'\nGreedy (subset-only): cost={cost2:.0f}, remaining={A2}')
for i, c, vs in steps:
    print(f'  P[{i}] cost={c:.0f} vertices={vs}')

# 3. Current greedy with full universe
cost3 = _greedy_cost_from_state(A_frozen, all_p, costs, vert_sets, n, R_min=0.0)
print(f'\nGreedy (full universe, R=0): cost={cost3:.0f}')
cost4 = _greedy_cost_from_state(A_frozen, all_p, costs, vert_sets, n, R_min=0.25)
print(f'Greedy (full universe, R=0.25): cost={cost4:.0f}')
