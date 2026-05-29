"""Direct n=4 SSHR-I CNOT objective run with progress output."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from bool_func import BooleanFunction, mct_cost
from parallelotope_enum import enumerate_parallelotopes
from parallelotope import Parallelotope
from block_synth import synth_block, block_cnot_cost, block_t_cost
from sshr_i import _solve_ilp
from paper_data import TABLE_VI_SSHR_I_CNOT

n = 4

# Pre-enumerate all parallelotopes ONCE
t0 = time.time()
all_ps = enumerate_parallelotopes(list(range(1 << n)), n)
seen_vsets = {p.vertices() for p in all_ps}
all_minterms = list(range(1 << n))
for v in all_minterms:
    s = frozenset([v])
    if s not in seen_vsets:
        all_ps.append(Parallelotope(v, []))
        seen_vsets.add(s)

# Precompute costs
cnot_costs = [float(block_cnot_cost(p, n)) for p in all_ps]
t_costs    = [float(block_t_cost(p, n)) for p in all_ps]
print(f"Pre-enumeration done: {len(all_ps)} parallelotopes ({time.time()-t0:.3f}s)", flush=True)

T, C, anc = 0, 0, 0
fails = 0
total_fns = 0
t_start = time.time()

for tt in range(1 << (1 << n)):
    bf = BooleanFunction(n, tt)
    if not bf.onset:
        continue

    onset_set = set(bf.onset)
    # Filter parallelotopes to those intersecting onset
    valid_ps = [p for p in all_ps if p.vertices() & onset_set]
    costs = [float(block_cnot_cost(p, n)) for p in valid_ps]

    selected_idx = _solve_ilp(valid_ps, all_minterms, bf.onset, costs, timeout=30)

    for i in selected_idx:
        p = valid_ps[i]
        for g_type, g_controls in _get_gates(p, n):
            if g_type == "MCT":
                k = len(g_controls)
                c = mct_cost(k)
                T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
            elif g_type == "CNOT":
                C += 1

    total_fns += 1
    if total_fns % 5000 == 0:
        dt = time.time() - t_start
        print(f"  {total_fns}/65535 done T={T} CNOT={C} Anc={anc} ({dt:.0f}s)", flush=True)

print(f"\nFinal: T={T} CNOT={C} Anc={anc} ({time.time()-t_start:.0f}s)")
p4 = TABLE_VI_SSHR_I_CNOT[4]
print(f"Paper: T={p4[0]} CNOT={p4[1]} Anc={p4[2]}")
