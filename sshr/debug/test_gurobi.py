"""Quick test of SSHR-I with Gurobi and full SSHR-H evaluation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import gurobipy as gp
print("Gurobi version:", gp.gurobi.version())

from bool_func import BooleanFunction
from sshr_h import sshr_h
from sshr_i import sshr_i

def verify(bf, circ):
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        result = circ.simulate(bits)
        if result[n] != bf.evaluate(x):
            return False, x
    return True, None

# ── SSHR-I paper example 0x46B9 ──
bf = BooleanFunction.from_hex(4, "46B9")
circ = sshr_i(bf, objective="cnot", timeout=30)
ok, fail = verify(bf, circ)
print(f"\nSSHR-I 0x46B9 (CNOT obj): correct={ok}  cost={circ.cost()}")
assert ok, f"SSHR-I incorrect at x={fail}"

circ_t = sshr_i(bf, objective="t", timeout=30)
ok2, _ = verify(bf, circ_t)
print(f"SSHR-I 0x46B9 (T obj):    correct={ok2}  cost={circ_t.cost()}")
assert ok2

# ── SSHR-I all 3-bit functions ──
print("\nSSHR-I all 3-bit functions...")
fails = []
for tt in range(256):
    bf3 = BooleanFunction(3, tt)
    if not bf3.onset:
        continue
    c = sshr_i(bf3, objective="cnot", timeout=10)
    ok, fail = verify(bf3, c)
    if not ok:
        fails.append(hex(tt))
if fails:
    print(f"  FAIL: {fails}")
else:
    print("  All PASS")

# ── Table IV: SSHR-H gate counts n=3 ──
print("\nTable IV excerpt: SSHR-H n=3 (all 256 functions)")
from bool_func import QuantumCircuit
totals = {"X": 0, "CNOT": 0, "2MCT": 0, "3MCT": 0}
T_total = 0
for tt in range(256):
    bf3 = BooleanFunction(3, tt)
    circ = sshr_h(bf3)
    for g in circ.gates:
        if g.type == "X": totals["X"] += 1
        elif g.type == "CNOT": totals["CNOT"] += 1
        elif g.type == "MCT":
            k = len(g.controls)
            totals[f"{k}MCT"] = totals.get(f"{k}MCT", 0) + 1
    T_total += circ.cost()["T"]
print(f"  X={totals['X']}  CNOT={totals['CNOT']}  2MCT={totals.get('2MCT',0)}  3MCT={totals.get('3MCT',0)}  T_total={T_total}")
print("  Paper Table IV n=3: X=1100 CNOT=560 2MCT=220 3MCT=128")

# ── Table VI: SSHR-I n=3 CNOT objective ──
print("\nTable VI: SSHR-I n=3, CNOT objective (all 256 functions)")
T3, C3, anc3 = 0, 0, 0
for tt in range(256):
    bf3 = BooleanFunction(3, tt)
    if not bf3.onset:
        continue
    circ = sshr_i(bf3, objective="cnot", timeout=10)
    c = circ.cost()
    T3 += c["T"]; C3 += c["CNOT"]; anc3 = max(anc3, c["ancilla"])
print(f"  T={T3}  CNOT={C3}  Ancilla={anc3}")
print("  Paper Table VI n=3: T=3280 CNOT=3232 Ancilla=128")
