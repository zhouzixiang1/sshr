"""Check if paper n=4 results correspond to NPN representatives."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h

# Paper Table IV n=4: X=2282, CNOT=1094, 2MCT=249, 3MCT=218, 4MCT=90
# Paper Table V n=3: T=3588, CNOT=3672, Anc=128

# First check n=3 SSHR-H against paper
print("=== n=3 SSHR-H (all 256 functions) ===")
total = {"X": 0, "CNOT": 0, "2-MCT": 0, "3-MCT": 0}
T, C, anc = 0, 0, 0
for tt in range(256):
    bf = BooleanFunction(3, tt)
    circ = sshr_h(bf)
    for g in circ.gates:
        total[g.type] = total.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            total[f"{k}-MCT"] = total.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1

print(f"  X={total.get('X',0)}, CNOT={total.get('CNOT',0)}, 2MCT={total.get('2-MCT',0)}, 3MCT={total.get('3-MCT',0)}")
print(f"  T={T}, CNOT={C}, Anc={anc}")
print(f"  Paper Table IV: X=1100, CNOT=560, 2MCT=220, 3MCT=128")
print(f"  Paper Table V:  T=3588, CNOT=3672, Anc=128")

# Check n=4 with all functions
print("\n=== n=4 SSHR-H (all 65536 functions) ===")
total4 = {}
T4, C4, anc4 = 0, 0, 0
for tt in range(65536):
    bf = BooleanFunction(4, tt)
    circ = sshr_h(bf)
    for g in circ.gates:
        total4[g.type] = total4.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            total4[f"{k}-MCT"] = total4.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k)
            T4 += c["T"]; C4 += c["CNOT"]; anc4 += c["ancilla"]
        elif g.type == "CNOT":
            C4 += 1

print(f"  X={total4.get('X',0)}, CNOT={total4.get('CNOT',0)}, 2MCT={total4.get('2-MCT',0)}, 3MCT={total4.get('3-MCT',0)}, 4MCT={total4.get('4-MCT',0)}")
print(f"  T={T4}, CNOT={C4}, Anc={anc4}")
print(f"  Paper Table IV: X=2282, CNOT=1094, 2MCT=249, 3MCT=218, 4MCT=90")
print(f"  Paper Table V:  T=7391, CNOT=6540, Anc=308")
print(f"\n  Ratio total/paper for X: {total4.get('X',0)/2282:.1f}x")
print(f"  If paper uses NPN classes (222): ratio should be ~65536/222={65536/222:.0f}")
