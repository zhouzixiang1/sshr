"""Find exactly which n=3 functions cause 2-MCT discrepancy vs paper."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h

# Paper: 2MCT=220, 3MCT=128
# Mine:  2MCT=252, 3MCT=128

# Collect per-function gate stats
funcs_2mct = []
for tt in range(256):
    bf = BooleanFunction(3, tt)
    circ = sshr_h(bf)
    mct2 = sum(1 for g in circ.gates if g.type=="MCT" and len(g.controls)==2)
    mct3 = sum(1 for g in circ.gates if g.type=="MCT" and len(g.controls)==3)
    X = sum(1 for g in circ.gates if g.type=="X")
    if mct2 > 0:
        funcs_2mct.append((tt, mct2, mct3, X, bf.onset))

print(f"Functions using 2-MCT: {len(funcs_2mct)}")
print(f"Total 2-MCT from my code: {sum(x[1] for x in funcs_2mct)}")
print(f"\nFunctions with 2-MCT > 2 (potential over-use):")
for tt, m2, m3, X, onset in sorted(funcs_2mct, key=lambda x: -x[1]):
    if m2 > 2:
        print(f"  tt=0x{tt:02X} onset={sorted(onset)} 2MCT={m2} 3MCT={m3} X={X}")

print(f"\nAll functions needing >= 2 dim-1 (2-MCT) gates:")
big_cases = [(tt, m2, m3, onset) for (tt, m2, m3, X, onset) in funcs_2mct if m2 >= 2]
print(f"  Count: {len(big_cases)}")

# Total expected 2-MCT breakdown
print(f"\nDistribution of 2-MCT usage:")
from collections import Counter
cnt = Counter(x[1] for x in funcs_2mct)
for k, v in sorted(cnt.items()):
    print(f"  {k} 2-MCT gates: {v} functions (total contribution: {k*v})")
print(f"  Sum: {sum(x[1] for x in funcs_2mct)}")
