"""
Generate NPN-canonical representative truth tables for n=4 Boolean functions.

NPN equivalence: f ~ g if g(x) = f(pi(x) XOR c) XOR d
for some permutation pi of input bits, input complement mask c, output complement d.

We take the MINIMUM truth table in each NPN class as the representative.
"""
from __future__ import annotations
from typing import List, Set
from itertools import permutations


def npn_canon(tt: int, n: int) -> int:
    """Return the minimum truth table in the NPN equivalence class of tt."""
    N = 1 << n
    mask = N - 1
    best = tt

    # All input permutations
    for perm in permutations(range(n)):
        # All input complementation masks
        for c in range(N):
            # Compute permuted+complemented truth table (output complement 0)
            new_tt = 0
            for x in range(N):
                # Apply input complement and permutation
                cx = x ^ c
                # Permute bits: new input = pi^{-1}(original position)
                # perm[i] = j means bit i maps to position j in output
                new_x = 0
                for i, j in enumerate(perm):
                    if (cx >> i) & 1:
                        new_x |= (1 << j)
                if (tt >> new_x) & 1:
                    new_tt |= (1 << x)
            # Also try output complement
            best = min(best, new_tt, new_tt ^ mask)
    return best


def get_npn_representatives(n: int) -> List[int]:
    """Return one representative per NPN class for n-variable functions."""
    N = 1 << n
    all_tt = range(1 << N)
    seen: Set[int] = set()
    reps: List[int] = []

    for tt in all_tt:
        canon = npn_canon(tt, n)
        if canon not in seen:
            seen.add(canon)
            reps.append(canon)

    return sorted(reps)


if __name__ == "__main__":
    import time
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    print("Computing NPN representatives for n=4...")
    t0 = time.time()
    reps4 = get_npn_representatives(4)
    dt = time.time() - t0
    print(f"n=4: {len(reps4)} NPN representatives ({dt:.1f}s)")

    print(f"\nFirst 20 representatives: {[hex(r) for r in reps4[:20]]}")
    print(f"Last 10: {[hex(r) for r in reps4[-10:]]}")

    # Verify n=3
    reps3 = get_npn_representatives(3)
    print(f"\nn=3: {len(reps3)} NPN representatives (expected 14)")

    # Save n=4 representatives
    print(f"\nSaving n=4 representatives to npn_reps_n4.py...")
    with open(os.path.join(os.path.dirname(__file__), "npn_reps_n4.py"), "w") as f:
        f.write(f"# {len(reps4)} NPN-canonical representatives for n=4 Boolean functions\n")
        f.write(f"NPN_REPS_N4 = {reps4}\n")
    print("Done.")
