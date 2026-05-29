"""Debug why T-objective and CNOT-objective give same T=3280 for n=3."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost
from parallelotope_enum import enumerate_parallelotopes
from block_synth import block_cnot_cost, block_t_cost, synth_block

n = 3
ps = enumerate_parallelotopes(list(range(1 << n)), n)

print(f"n={n}: {len(ps)} parallelotopes")
print(f"\nSample parallelotope costs:")
print(f"{'dim':>4}  {'v0':>4}  {'basis':>20}  {'cnot_cost':>10}  {'t_cost':>8}")
for p in sorted(ps, key=lambda x: -x.dim)[:20]:
    cc = block_cnot_cost(p, n)
    tc = block_t_cost(p, n)
    print(f"  {p.dim:>2}  {p.v0:>4}  {str(p.basis):>20}  {cc:>10}  {tc:>8}")

# Count unique (cnot_cost, t_cost) pairs
from collections import Counter
pairs = Counter((block_cnot_cost(p, n), block_t_cost(p, n)) for p in ps)
print(f"\nUnique (cnot, t) cost pairs: {len(pairs)}")
for (cc, tc), cnt in sorted(pairs.items()):
    print(f"  cnot={cc}, t={tc}: {cnt} parallelotopes")

# Check a specific 3-bit function
# onset = {0,1,2,3,4,5,6,7} minus a few to get a non-trivial function
from sshr_i import sshr_i

# Use the "3-majority" function: f=1 when at least 2 bits are 1
# onset = {3,5,6,7}
bf = BooleanFunction(3, (1<<3)|(1<<5)|(1<<6)|(1<<7))
print(f"\n3-majority function (onset={sorted(bf.onset)}):")

c_cnot = sshr_i(bf, objective="cnot", timeout=30)
c_t = sshr_i(bf, objective="t", timeout=30)

print(f"  CNOT-obj: {c_cnot.cost()}")
print(f"  T-obj:    {c_t.cost()}")

# Check all n=3 functions
from sshr_i import sshr_i
print(f"\nAll n=3 functions, T-obj vs CNOT-obj:")
total_cnot_obj_T = 0
total_t_obj_T = 0
diff_count = 0
for tt in range(1, 256):
    bf = BooleanFunction(3, tt)
    if not bf.onset:
        continue
    c1 = sshr_i(bf, objective="cnot", timeout=10)
    c2 = sshr_i(bf, objective="t", timeout=10)
    t1 = c1.cost()["T"]
    t2 = c2.cost()["T"]
    total_cnot_obj_T += t1
    total_t_obj_T += t2
    if t1 != t2:
        diff_count += 1
        if diff_count <= 5:
            print(f"  tt=0x{tt:02X}: cnot-obj T={t1}, t-obj T={t2}")

print(f"\nTotal T: cnot-obj={total_cnot_obj_T}, t-obj={total_t_obj_T}")
print(f"Functions with different T: {diff_count}")
