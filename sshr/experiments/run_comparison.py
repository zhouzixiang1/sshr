"""
Run SSHR-I vs ESOP comparison for n=3 and n=4.
Reproduces Table VI (CNOT objective).
"""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from esop_ilp import esop_ilp
from paper_data import TABLE_VI_SSHR_I_CNOT, TABLE_V_ESOP


def verify(bf, circ):
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            return False
    return True


def total_cost(bf_list, synth_fn, **kwargs):
    T, C, anc = 0, 0, 0
    fail = 0
    for bf in bf_list:
        circ = synth_fn(bf, **kwargs)
        c = circ.cost()
        T += c["T"]; C += c["CNOT"]; anc += c["ancilla"]
        if not verify(bf, circ):
            fail += 1
    return T, C, anc, fail


print("="*70)
print("Reproducing Table VI: SSHR-I (CNOT objective) vs ESOP")
print("="*70)

for n in [3, 4]:
    if n <= 4:
        bf_list = [BooleanFunction(n, tt) for tt in range(1 << (1 << n))
                   if BooleanFunction(n, tt).onset]
    else:
        rng = random.Random(42)
        N = 1 << n
        bf_list = [BooleanFunction(n, rng.randint(1, (1<<N)-1)) for _ in range(2000)]
        bf_list = [bf for bf in bf_list if bf.onset]

    print(f"\n--- n={n}, {len(bf_list)} functions (with nonempty on-set) ---")

    # SSHR-I
    t0 = time.time()
    T_s, C_s, a_s, fail_s = total_cost(bf_list, sshr_i, objective="cnot", timeout=60)
    dt_s = time.time() - t0

    # ESOP-ILP
    t0 = time.time()
    T_e, C_e, a_e, fail_e = total_cost(bf_list, esop_ilp, objective="cnot", timeout=60)
    dt_e = time.time() - t0

    cnot_gain = (C_e - C_s) / C_e * 100 if C_e > 0 else 0

    print(f"  SSHR-I: T={T_s:>8}  CNOT={C_s:>8}  Anc={a_s:>6}  fails={fail_s}  ({dt_s:.0f}s)")
    print(f"  ESOP:   T={T_e:>8}  CNOT={C_e:>8}  Anc={a_e:>6}  fails={fail_e}  ({dt_e:.0f}s)")
    print(f"  CNOT gain (SSHR-I vs ESOP): {cnot_gain:.1f}%")

    if n in TABLE_VI_SSHR_I_CNOT:
        p_s = TABLE_VI_SSHR_I_CNOT[n]
        print(f"  Paper SSHR-I: T={p_s[0]}  CNOT={p_s[1]}  Anc={p_s[2]}")
    if n in TABLE_V_ESOP:
        p_e = TABLE_V_ESOP[n]
        print(f"  Paper ESOP:   T={p_e[0]}  CNOT={p_e[1]}  Anc={p_e[2]}")
        if n in TABLE_VI_SSHR_I_CNOT:
            pg = (p_e[1] - TABLE_VI_SSHR_I_CNOT[n][1]) / p_e[1] * 100
            print(f"  Paper CNOT gain: {pg:.1f}%")
