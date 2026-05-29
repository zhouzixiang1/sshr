"""Check SSHR-H and SSHR-I on NPN reps for n=3,4."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_i import sshr_i
from npn_reps2 import get_npn_reps

def gate_stats(circ):
    raw = {}; T, C, anc = 0, 0, 0
    for g in circ.gates:
        raw[g.type] = raw.get(g.type, 0) + 1
        if g.type == "MCT":
            k = len(g.controls)
            raw[f"{k}-MCT"] = raw.get(f"{k}-MCT", 0) + 1
            c = mct_cost(k)
            T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        elif g.type == "CNOT":
            C += 1
    return raw, T, C, anc

# n=3 ALL functions (for reference)
print("=== SSHR-H: n=3 ALL 256 functions ===")
total = {}; T, C, anc = 0, 0, 0
for tt in range(256):
    raw, t, c, a = gate_stats(sshr_h(BooleanFunction(3, tt)))
    T += t; C += c; anc += a
    for k, v in raw.items(): total[k] = total.get(k, 0) + v
print(f"  X={total.get('X',0)} CNOT={total.get('CNOT',0)} 2MCT={total.get('2-MCT',0)} "
      f"3MCT={total.get('3-MCT',0)} | T={T} CNOT_t={C} Anc={anc}")
print(f"  Paper: X=1100 CNOT=560 2MCT=220 3MCT=128 | T=3588 C=3672 Anc=128")

# n=3 NPN reps (14)
reps3 = get_npn_reps(3)
print(f"\n=== SSHR-H: n=3 {len(reps3)} NPN reps ===")
total = {}; T, C, anc = 0, 0, 0
for tt in reps3:
    raw, t, c, a = gate_stats(sshr_h(BooleanFunction(3, tt)))
    T += t; C += c; anc += a
    for k, v in raw.items(): total[k] = total.get(k, 0) + v
print(f"  X={total.get('X',0)} CNOT={total.get('CNOT',0)} 2MCT={total.get('2-MCT',0)} "
      f"3MCT={total.get('3-MCT',0)} | T={T} CNOT_t={C} Anc={anc}")

# n=4 NPN reps (222)
try:
    from npn_reps_n4 import NPN_REPS_N4
    print(f"\n=== SSHR-H: n=4 {len(NPN_REPS_N4)} NPN reps ===")
    total = {}; T, C, anc = 0, 0, 0
    for tt in NPN_REPS_N4:
        raw, t, c, a = gate_stats(sshr_h(BooleanFunction(4, tt)))
        T += t; C += c; anc += a
        for k, v in raw.items(): total[k] = total.get(k, 0) + v
    print(f"  X={total.get('X',0)} CNOT={total.get('CNOT',0)} 2MCT={total.get('2-MCT',0)} "
          f"3MCT={total.get('3-MCT',0)} 4MCT={total.get('4-MCT',0)} | T={T} CNOT_t={C} Anc={anc}")
    print(f"  Paper: X=2282 CNOT=1094 2MCT=249 3MCT=218 4MCT=90 | T=7391 C=6540 Anc=308")
except ImportError:
    print("NPN reps n=4 not available")
