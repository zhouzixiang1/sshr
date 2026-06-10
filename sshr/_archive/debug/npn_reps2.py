"""
Correct NPN canonical form for n-variable Boolean functions.
NPN equiv: f ~ g if g(x) = d XOR f(pi^{-1}(x XOR c))
or equivalently: f ~ g if g(pi(x) XOR c) = d XOR f(x)

We use: new_tt[x] = d XOR tt[perm^{-1}(x XOR c)]
by iterating over all (perm, c, d).
"""
from itertools import permutations
from typing import List


def apply_perm(x: int, perm: tuple, n: int) -> int:
    """Apply permutation: output bit perm[i] = input bit i."""
    result = 0
    for i in range(n):
        if (x >> i) & 1:
            result |= (1 << perm[i])
    return result


def npn_canon(tt: int, n: int) -> int:
    """Return canonical (minimum) truth table in NPN equivalence class."""
    N = 1 << n          # 2^n minterms
    mask = (1 << N) - 1  # truth table complement mask (2^n bits)
    best = tt

    for perm in permutations(range(n)):
        for c in range(N):
            # Compute g(x) = f(perm^{-1}(x XOR c)) for d=0 and d=1
            new_tt = 0
            for x in range(N):
                # xc = x XOR c
                xc = x ^ c
                # apply perm to xc
                new_x = apply_perm(xc, perm, n)
                if (tt >> new_x) & 1:
                    new_tt |= (1 << x)
            best = min(best, new_tt, new_tt ^ mask)
    return best


def get_npn_reps(n: int) -> List[int]:
    N = 1 << n
    seen = set()
    reps = []
    for tt in range(1 << N):
        canon = npn_canon(tt, n)
        if canon not in seen:
            seen.add(canon)
            reps.append(canon)
    return sorted(reps)


if __name__ == "__main__":
    import time

    print("Testing n=3 (expect 14)...")
    t0 = time.time()
    reps3 = get_npn_reps(3)
    print(f"n=3: {len(reps3)} NPN reps ({time.time()-t0:.1f}s)")
    print(f"  Representatives: {[hex(r) for r in reps3]}")

    # Only compute n=4 if n=3 gives 14
    if len(reps3) == 14:
        print("\nComputing n=4 (expect 222)...")
        t0 = time.time()
        reps4 = get_npn_reps(4)
        print(f"n=4: {len(reps4)} NPN reps ({time.time()-t0:.1f}s)")
        if len(reps4) == 222:
            import os, sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            with open(os.path.join(os.path.dirname(__file__), "npn_reps_n4.py"), "w") as f:
                f.write(f"# {len(reps4)} NPN-canonical representative truth tables for n=4\n")
                f.write(f"NPN_REPS_N4 = {reps4}\n")
            print("Saved to npn_reps_n4.py")
    else:
        print(f"n=3 FAILED: got {len(reps3)} instead of 14")
        print("Debugging first 5 equivalence issues...")
        # Check: are 0x00 and 0xFF in same class?
        print(f"  canon(0x00)={hex(npn_canon(0, 3))}")
        print(f"  canon(0xFF)={hex(npn_canon(0xFF, 3))}")
        # Check: are 0x01 and 0x02 in same class?
        print(f"  canon(0x01)={hex(npn_canon(1, 3))}")
        print(f"  canon(0x02)={hex(npn_canon(2, 3))}")
        print(f"  canon(0x04)={hex(npn_canon(4, 3))}")
        print(f"  canon(0x80)={hex(npn_canon(0x80, 3))}")
        print(f"  canon(0x69)={hex(npn_canon(0x69, 3))}")
        print(f"  canon(0x96)={hex(npn_canon(0x96, 3))}")
