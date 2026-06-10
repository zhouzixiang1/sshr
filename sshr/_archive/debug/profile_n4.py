"""Profile n=4 SSHR-I to understand timing and estimate paper values."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from parallelotope_enum import enumerate_parallelotopes
from sshr_i import sshr_i

n = 4

# Time the parallelotope enumeration
t0 = time.time()
ps = enumerate_parallelotopes(list(range(1 << n)), n)
enum_time = time.time() - t0
print(f"n={n} full-universe parallelotopes: {len(ps)} (enumeration: {enum_time:.3f}s)")

# Profile a few individual functions
import random
rng = random.Random(42)
sample = rng.sample(range(1, 1 << (1 << n)), 10)

print(f"\nProfile of 10 functions:")
total_T = 0
for tt in sample:
    bf = BooleanFunction(n, tt)
    t0 = time.time()
    circ = sshr_i(bf, objective="cnot", timeout=10)
    dt = time.time() - t0
    cost = circ.cost()
    total_T += cost["T"]
    print(f"  tt=0x{tt:04X} onset_size={len(bf.onset):2d} T={cost['T']:4d} CNOT={cost['CNOT']:4d} ({dt:.3f}s)")

print(f"\n  Total T for sample: {total_T}")
print(f"  Projected for all 65535 functions: ~{total_T*65535//10}")
print(f"  Paper n=4 SSHR-I CNOT: T=6028, CNOT=4696, Anc=212")

# Check: does the paper's values make sense if we test only functions
# from NPN representatives or a specific subset?
print(f"\n  Comparison for context:")
print(f"  n=3 paper: T=3280 for ~255 functions = avg {3280/255:.1f} T/func")
print(f"  n=4 paper: T=6028 for all functions = avg {6028/65535:.3f} T/func ???")
print(f"  n=4 paper: T=6028 for 222 NPN repr = avg {6028/222:.1f} T/func")
print(f"  My sample: avg {total_T/10:.1f} T/func")
