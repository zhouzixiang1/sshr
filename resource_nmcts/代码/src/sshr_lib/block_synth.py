"""
Algorithm 1: Synthesize a quantum circuit block for a single parallelotope.

For a k-dimensional parallelotope in n-dimensional Boolean space:
  - Each basis vector α_j has support S_j (set of 1-bit positions).
  - Representative r_j = lowest bit of S_j.
  - Inner bits I_j = S_j \ {r_j}.
  - Common control bits = all bit positions NOT in any S_j.

Circuit structure:
  1. CNOT(r_j, b) for each inner bit b in I_j  ← forward pass
     After this, inner bit b = b_orig XOR r_j_orig.
     For any vertex of the parallelotope: b_orig XOR r_j_orig = v0[b] XOR v0[r_j] = c_{j,b} (constant).
  2. X(b) for inner bits b where c_{j,b} = 0   ← make them 1
     X(p) for common bits p where v0[p] = 0     ← 0-control pattern
  3. MCT(control_list, output_qubit)
     control_list = {all inner bits} ∪ {all common bits}
     NOTE: representatives are NOT in control_list.
  4. Reverse step 2 X gates
  5. Reverse step 1 CNOTs  ← restore inner bits to original values

This gives one (n − m)-MCT gate, as claimed by Theorem 1.
Representatives are excluded because they vary freely across the 2^m vertices,
while inner bits are constant (c_{j,b}) after the CNOT chain.
"""
from __future__ import annotations
from typing import List, Tuple
from src.sshr_lib.bool_func import QuantumCircuit, mct_cost
from src.sshr_lib.parallelotope import Parallelotope


def _set_bits(mask: int) -> List[int]:
    """Return sorted list of bit positions where mask has 1."""
    bits = []
    pos = 0
    while mask:
        if mask & 1:
            bits.append(pos)
        mask >>= 1
        pos += 1
    return bits


def synth_block(p: Parallelotope, n: int, output_qubit: int = -1) -> QuantumCircuit:
    """
    Synthesize the circuit block for parallelotope p in n-dimensional space.

    output_qubit: default n (last qubit of an n+1-qubit circuit).
    """
    if output_qubit < 0:
        output_qubit = n

    circuit = QuantumCircuit(n + 1)

    # ── Common bits: all positions, then remove those covered by basis vectors
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_bits = _set_bits((((1 << n) - 1) & ~covered))

    # ── Per-basis-vector processing
    cnot_pairs: List[Tuple[int, int]] = []  # (rep, inner_bit)
    control_list: List[int] = []
    x_wrap: List[int] = []

    for alpha in p.basis:
        bits = _set_bits(alpha)
        if not bits:
            continue
        rep = bits[0]       # representative — NOT added to control_list
        for b in bits[1:]:  # inner bits
            cnot_pairs.append((rep, b))
            c = ((p.v0 >> b) & 1) ^ ((p.v0 >> rep) & 1)
            control_list.append(b)
            if c == 0:
                x_wrap.append(b)

    # ── Common control bits
    for p_bit in common_bits:
        control_list.append(p_bit)
        if not ((p.v0 >> p_bit) & 1):
            x_wrap.append(p_bit)

    # ── Emit gates
    for ctrl, tgt in cnot_pairs:
        circuit.add_cnot(ctrl, tgt)

    for b in x_wrap:
        circuit.add_x(b)

    circuit.add_mct(control_list, output_qubit)

    for b in x_wrap:
        circuit.add_x(b)

    for ctrl, tgt in reversed(cnot_pairs):
        circuit.add_cnot(ctrl, tgt)

    return circuit


def block_cnot_cost(p: Parallelotope, n: int) -> int:
    """Estimate CNOT cost of the circuit block for p without building it."""
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_bits = _set_bits((((1 << n) - 1) & ~covered))

    n_inner = 0
    cnot_chain = 0
    for alpha in p.basis:
        bits = _set_bits(alpha)
        if len(bits) > 1:
            cnot_chain += len(bits) - 1  # one CNOT per inner bit
            n_inner += len(bits) - 1

    n_common = len(common_bits)
    n_controls = n_inner + n_common

    if n_controls == 0:
        mct_cnot = 0
    elif n_controls == 1:
        mct_cnot = 1
    else:
        mct_cnot = mct_cost(n_controls)["CNOT"]

    return 2 * cnot_chain + mct_cnot


def block_t_cost(p: Parallelotope, n: int) -> int:
    """Estimate T-count of the circuit block for p."""
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_bits = _set_bits((((1 << n) - 1) & ~covered))

    n_inner = sum(len(_set_bits(alpha)) - 1 for alpha in p.basis if _set_bits(alpha))
    n_controls = n_inner + len(common_bits)

    if n_controls < 2:
        return 0
    return mct_cost(n_controls)["T"]
