"""Debug SSHR-H performance for n=4."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction
from sshr_h import sshr_h

# Check a few 4-bit functions
test_cases = [0x46B9, 0xF0F0, 0xAAAA, 0x0F0F, 0x6996, 0x1]
for tt in test_cases:
    bf = BooleanFunction(4, tt)
    circ = sshr_h(bf)
    c = circ.cost()
    raw = {}
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
    print(f"  0x{tt:04X}: gates={raw}, cost={c}")

# Count 4-bit functions to check
total = {"X":0, "CNOT":0, "MCT":0}
max_gates = 0
worst_tt = 0
for tt in range(65536):
    bf = BooleanFunction(4, tt)
    circ = sshr_h(bf)
    ng = len(circ.gates)
    if ng > max_gates:
        max_gates = ng
        worst_tt = tt
    for g in circ.gates:
        total[g.type] = total.get(g.type, 0) + 1

print(f"\nTotal gates n=4: {total}")
print(f"Worst function: 0x{worst_tt:04X} with {max_gates} gates")
bf = BooleanFunction(4, worst_tt)
print(f"  onset size: {len(bf.onset)}")
