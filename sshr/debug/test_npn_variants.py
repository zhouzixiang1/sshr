"""Compare SSHR-I results with different NPN representative choices."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from itertools import permutations

def apply_perm(x, perm, n):
    y = 0
    for i, p in enumerate(perm):
        if (x >> p) & 1:
            y |= (1 << i)
    return y

def npn_orbit(tt, n):
    """Return the full NPN equivalence class of tt."""
    N = 1 << n
    mask = (1 << N) - 1
    orbit = set()
    for perm in permutations(range(n)):
        for c in range(N):
            new_tt = 0
            for x in range(N):
                xc = x ^ c
                new_x = apply_perm(xc, perm, n)
                if (tt >> new_x) & 1:
                    new_tt |= (1 << x)
            orbit.add(new_tt)
            orbit.add(new_tt ^ mask)
    return orbit

def get_npn_reps(n, mode='min'):
    """Get one representative per NPN class. mode='min' or 'max'."""
    N = 1 << n
    total = 1 << N
    visited = set()
    reps = []
    for tt in range(total):
        if tt in visited:
            continue
        orbit = npn_orbit(tt, n)
        visited.update(orbit)
        if mode == 'min':
            reps.append(min(orbit))
        elif mode == 'max':
            reps.append(max(orbit))
        elif mode == 'middle':
            s = sorted(orbit)
            reps.append(s[len(s)//2])
    return sorted(reps)

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

print("Testing different NPN representative choices for n=4 SSHR-I")
print("Paper reference: T=6028, CNOT=4696, Anc=212\n")

from npn_reps_n4 import NPN_REPS_N4

# Also load our min-reps (should be same as NPN_REPS_N4)
# and test a few variants

for label, reps_list in [("NPN_REPS_N4 (saved)", NPN_REPS_N4)]:
    T, C, anc = 0, 0, 0
    n_tested = 0
    t0 = time.time()
    for tt in reps_list:
        bf = BooleanFunction(4, tt)
        if not bf.onset:
            continue
        circ = sshr_i(bf, objective="cnot", timeout=60)
        _, t, c, a = gate_stats(circ)
        T += t; C += c; anc += a
        n_tested += 1
    dt = time.time() - t0
    print(f"{label}: n={n_tested} | T={T} CNOT={C} Anc={anc} ({dt:.0f}s)")

print()

# Check: what's the TT range of our reps?
print(f"NPN_REPS_N4 stats: count={len(NPN_REPS_N4)}, min={min(NPN_REPS_N4)}, max={max(NPN_REPS_N4)}")
print(f"Includes 0: {0 in NPN_REPS_N4}")
print(f"Non-zero reps: {sum(1 for x in NPN_REPS_N4 if x > 0)}")

# For n=4, the 222 classes - check if any of our reps are constant functions
print(f"\nSmall reps (<=15): {[x for x in NPN_REPS_N4 if x <= 15]}")

# Verify: for each rep, is it truly the minimum in its orbit?
print("\nVerifying minimum-TT property for first 10 reps...")
import random
random.seed(42)
for tt in NPN_REPS_N4[:10]:
    if tt == 0:
        continue
    # Check a few random orbit members
    N = 1 << 4
    mask = (1 << N) - 1
    # Quick check: just try output negation
    if (tt ^ mask) < tt:
        print(f"  BUG: tt={tt} but ~tt={tt^mask} < tt (orbit min should be {min(tt, tt^mask)})")
    else:
        print(f"  OK: tt={tt}, ~tt={tt^mask}")
