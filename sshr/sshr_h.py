"""
Algorithm 2: SSHR-H — Greedy heuristic for Boolean function synthesis.

Threshold R=3/4: a parallelotope P is selected if |A ∩ P| / |P| >= R.

Update rule: A ^= vertices(P)  (XOR / symmetric difference)
  - on-set minterms covered by P are removed from A (they've been flipped to 1)
  - off-set minterms in P that are in A get added (they've been flipped back)

The algorithm terminates when A = ∅.

Key design (matching paper Algorithm 2):
  - S is enumerated ONCE from the FULL hypercube {0..2^n-1} before the loop.
  - Each iteration filters S for candidates with ratio >= R; the best is chosen.
  - When no candidate qualifies, remaining minterms are handled as singletons
    (dim-0 parallelotopes → n-MCT gates).  No relaxed fallback that can oscillate.
"""
from __future__ import annotations
from functools import lru_cache
from typing import List, Set
from bool_func import BooleanFunction, QuantumCircuit
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block


@lru_cache(maxsize=8)
def _full_hypercube_parallelotopes(n: int) -> List[Parallelotope]:
    """Return all parallelotopes in the full n-dimensional hypercube (cached)."""
    return enumerate_parallelotopes(list(range(1 << n)), n)


def sshr_h(
    bf: BooleanFunction,
    R: float = 3 / 4,
) -> QuantumCircuit:
    """
    Synthesize a quantum oracle for Boolean function `bf` using SSHR-H.

    Follows paper Algorithm 2: candidate set S is enumerated once from the
    full hypercube; each step picks the highest-dim parallelotope with
    |A ∩ P| / |P| >= R; A is updated via XOR.

    Parameters
    ----------
    bf : BooleanFunction
    R  : selection threshold (paper uses 3/4)

    Returns
    -------
    QuantumCircuit  (n+1 qubits, last qubit is output)
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)

    A: Set[int] = set(bf.onset)
    if not A:
        return circuit

    # S enumerated ONCE from the full hypercube (dim-descending order).
    # This allows parallelotopes with off-set vertices (ratio >= R < 1),
    # matching the paper's Algorithm 2 which considers all parallelotopes
    # in {0..2^n-1}, not just those contained in the current on-set A.
    S: List[Parallelotope] = _full_hypercube_parallelotopes(n)

    while A:
        # Filter: candidates must have at least R fraction of vertices in A
        candidates = [
            P for P in S
            if len(P.vertices() & A) / len(P.vertices()) >= R
        ]

        if not candidates:
            # No parallelotope qualifies; handle remaining minterms as singletons
            break

        # Pick the first (highest-dim, then enumeration order) candidate
        chosen = candidates[0]
        circuit.add_block(synth_block(chosen, n))
        A ^= chosen.vertices()   # XOR update

    # Handle any remaining minterms with dim-0 (singleton → n-MCT) parallelotopes
    for minterm in list(A):
        p0 = Parallelotope(minterm, [])
        circuit.add_block(synth_block(p0, n))

    return circuit
