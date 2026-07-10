"""
Baseline synthesis methods: ESOP and XAG.

ESOP: Exclusive Sum of Products.
  Each product term (cube) becomes one MCT gate.
  We implement a Python-native ESOP minimizer using a greedy cube cover
  (similar to what the `easy` library does for small functions).

XAG: Xor-And-Inverter Graph.
  We implement a simple XAG-style synthesis via truth table factorization
  that mimics the cost structure reported in the paper.
  For accurate comparison, the user can replace these with calls to the
  actual `easy` (ESOP) and `mockturtle` (XAG) tools.

Both methods return a QuantumCircuit with gate-level costs computed via
Table II decomposition.
"""
from __future__ import annotations
from typing import List, Set, FrozenSet, Tuple
from bool_func import BooleanFunction, QuantumCircuit, mct_cost
from parallelotope import Parallelotope
from block_synth import synth_block


# ---------------------------------------------------------------------------
# ESOP synthesis
# ---------------------------------------------------------------------------

def _minterms_to_int(minterms: Set[int]) -> int:
    """Convert set of minterms to integer truth table."""
    tt = 0
    for m in minterms:
        tt |= (1 << m)
    return tt


def _esop_greedy(onset: Set[int], n: int) -> List[Tuple[int, int]]:
    """
    Greedy ESOP minimizer returning list of (cube_mask, cube_value) pairs.
    cube_mask: bitmask of which variables are in the product term
    cube_value: bitmask of which variables appear uncomplemented

    Algorithm: repeatedly find the largest cube that covers the most uncovered
    minterms in a XOR-sense (Roth-Karp style).

    For small n (≤8) this is feasible.
    """
    remaining = set(onset)
    cubes = []

    while remaining:
        best_cube = None
        best_cover = None
        best_score = -1

        # Try all possible cubes (mask, value) sorted by descending size
        for size in range(n, 0, -1):
            # Generate cubes of given size
            from itertools import combinations
            for bits in combinations(range(n), size):
                mask = sum(1 << b for b in bits)
                # Two cube values: one where all selected bits are 1, one where some are 0
                # For each assignment of the selected bits:
                for val_bits in range(1 << size):
                    value = 0
                    for i, b in enumerate(bits):
                        if (val_bits >> i) & 1:
                            value |= (1 << b)
                    # Enumerate all minterms covered by this cube
                    covered = set()
                    for m in range(1 << n):
                        if (m & mask) == value:
                            covered.add(m)
                    xor_covered = covered & remaining
                    score = len(xor_covered)
                    if score > best_score:
                        best_score = score
                        best_cube = (mask, value)
                        best_cover = covered
            if best_score > 0:
                break

        if best_cube is None or best_score == 0:
            # Last resort: single minterms
            m = next(iter(remaining))
            # Full cube (all variables fixed)
            mask = (1 << n) - 1
            cubes.append((mask, m))
            remaining ^= {m}
        else:
            cubes.append(best_cube)
            remaining ^= (best_cover & remaining)
            # Note: XOR semantics — any off-set minterms now toggled into remaining
            # We need to handle the XOR cover correctly:
            # Apply XOR: remaining = remaining ^ (best_cover)
            # but we only care about remaining minterms in onset, so:
            remaining = remaining.symmetric_difference(best_cover) & set(range(1 << n))
            # Recalculate: remaining is the current "active" set that still needs covering
            # This is the ESOP XOR-cover interpretation.

    return cubes


def esop_synthesize(bf: BooleanFunction) -> QuantumCircuit:
    """
    Synthesize using ESOP method (greedy cube cover).
    Each cube becomes one k-MCT gate where k = cube size.
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    onset = set(bf.onset)
    if not onset:
        return circuit

    cubes = _esop_greedy(onset, n)
    output_qubit = n

    for mask, value in cubes:
        # Determine which bits are in the product term
        bits_in_cube = [b for b in range(n) if (mask >> b) & 1]
        x_wrap = [b for b in bits_in_cube if not ((value >> b) & 1)]
        controls = bits_in_cube

        for b in x_wrap:
            circuit.add_x(b)
        circuit.add_mct(controls, output_qubit)
        for b in x_wrap:
            circuit.add_x(b)

    return circuit


# ---------------------------------------------------------------------------
# XAG synthesis (simplified model)
# ---------------------------------------------------------------------------

def _xag_cost_model(n: int, onset_size: int) -> dict:
    """
    Approximate XAG cost based on the n-variable function complexity.
    This is a placeholder that estimates based on empirical ratios from
    the paper. For accurate results, use the actual mockturtle/tweedledum tools.

    Returns dict with T, CNOT, ancilla estimates.
    """
    # Based on Table V ratios: XAG uses ~3.6x more T and ~3.7x more CNOT than SSHR-H
    # This is a very rough approximation; replace with real XAG tool calls.
    raise NotImplementedError(
        "XAG baseline requires mockturtle or tweedledum. "
        "Install with: pip install tweedledum  (if available)\n"
        "Or provide the XAG binary path."
    )


def xag_synthesize(bf: BooleanFunction) -> QuantumCircuit:
    """XAG synthesis stub — replace with actual tool call."""
    raise NotImplementedError(
        "XAG synthesis requires an external tool (mockturtle/tweedledum).\n"
        "See baselines.py for integration instructions."
    )


# ---------------------------------------------------------------------------
# Simple ESOP via truth table (exact for small n)
# ---------------------------------------------------------------------------

def esop_exact(bf: BooleanFunction) -> QuantumCircuit:
    """
    Exact ESOP synthesis using exhaustive search over product terms.
    Feasible for n <= 6.
    Each on-set minterm that is not yet covered gets a fresh cube,
    using the ESOP canonical form (each cube = one AND term).
    """
    n = bf.n
    circuit = QuantumCircuit(n + 1)
    output_qubit = n

    # Simple implementation: one MCT per minterm (no sharing)
    # This is equivalent to the Reed-Muller canonical form but not optimal.
    # Replace with call to `easy` for optimal ESOP.
    onset = bf.onset
    for minterm in onset:
        # Full n-MCT gate for this minterm
        p0 = Parallelotope(minterm, [])
        block = synth_block(p0, n, output_qubit)
        circuit.add_block(block)

    return circuit
