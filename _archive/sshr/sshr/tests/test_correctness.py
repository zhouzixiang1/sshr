"""
Correctness tests for SSHR algorithms.

Run with: cd sshr && python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from bool_func import BooleanFunction, mct_cost
from parallelotope import Parallelotope, is_valid_basis
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block
from sshr_h import sshr_h


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def circuit_implements(bf: BooleanFunction, circuit) -> bool:
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        result = circuit.simulate(bits)
        if result[n] != bf.evaluate(x):
            return False
    return True


# ---------------------------------------------------------------------------
# Tests: MCT cost table
# ---------------------------------------------------------------------------

def test_mct_cost_k1():
    c = mct_cost(1)
    assert c["CNOT"] == 1
    assert c["T"] == 0

def test_mct_cost_k2():
    c = mct_cost(2)
    assert c["T"] == 7
    assert c["CNOT"] == 6
    assert c["ancilla"] == 0

def test_mct_cost_k3():
    c = mct_cost(3)
    assert c["T"] == 16
    assert c["CNOT"] == 14
    assert c["ancilla"] == 1

def test_mct_cost_k4():
    c = mct_cost(4)
    assert c["T"] == 24
    assert c["CNOT"] == 10
    assert c["ancilla"] == 1


# ---------------------------------------------------------------------------
# Tests: Parallelotope
# ---------------------------------------------------------------------------

def test_parallelotope_vertices_1d():
    # 1D: segment v0=0b00, alpha=0b11 -> vertices {0b00, 0b11}
    p = Parallelotope(0b00, [0b11])
    assert p.vertices() == frozenset({0b00, 0b11})
    assert len(p) == 2

def test_parallelotope_vertices_2d():
    # 2D parallelotope: v0=0b000, basis=[0b001, 0b110]
    # Disjoint support: 001 & 110 = 0 ✓
    p = Parallelotope(0b000, [0b001, 0b110])
    assert len(p) == 4
    assert p.vertices() == frozenset({0b000, 0b001, 0b110, 0b111})

def test_valid_basis():
    assert is_valid_basis([0b001, 0b110])
    assert not is_valid_basis([0b011, 0b110])  # 011 & 110 = 010 != 0


# ---------------------------------------------------------------------------
# Tests: Parallelotope enumeration
# ---------------------------------------------------------------------------

def test_enum_3majority():
    # 3-Majority: f(x) = 1 iff popcount(x) >= 2
    # on-set = {3,5,6,7} = {011, 101, 110, 111}
    onset = [3, 5, 6, 7]
    ps = enumerate_parallelotopes(onset, 3)
    # All vertices must be in onset
    for p in ps:
        assert p.vertices() <= set(onset), f"Parallelotope {p} has vertices outside onset"
    print(f"  3-majority: found {len(ps)} parallelotopes")
    assert len(ps) >= 1


# ---------------------------------------------------------------------------
# Tests: Block synthesis + simulation (Algorithm 1)
# ---------------------------------------------------------------------------

def test_block_single_minterm():
    """Single minterm 5 (=0b101) for n=3."""
    n = 3
    p = Parallelotope(5, [])  # dim-0
    circ = synth_block(p, n)
    # Simulate: input x=5 (101) -> output should flip
    bits_in = [1, 0, 1, 0]  # q0,q1,q2,out
    bits_out = circ.simulate(bits_in)
    assert bits_out[3] == 1, f"Expected output=1, got {bits_out}"
    # Other inputs should not flip output
    for x in range(8):
        if x == 5:
            continue
        bits_in = [(x >> i) & 1 for i in range(3)] + [0]
        bits_out = circ.simulate(bits_in)
        assert bits_out[3] == 0, f"x={x}: expected output=0, got {bits_out}"


def test_block_2d_parallelotope():
    """2D parallelotope covering {0,1,2,3} for n=3."""
    n = 3
    # basis=[0b001, 0b010], v0=0b000 -> vertices={0,1,2,3}
    p = Parallelotope(0b000, [0b001, 0b010])
    assert p.vertices() == frozenset({0, 1, 2, 3})
    circ = synth_block(p, n)
    for x in range(8):
        bits_in = [(x >> i) & 1 for i in range(3)] + [0]
        bits_out = circ.simulate(bits_in)
        if x in {0, 1, 2, 3}:
            assert bits_out[3] == 1, f"x={x:03b}: expected 1, got {bits_out[3]}"
        else:
            assert bits_out[3] == 0, f"x={x:03b}: expected 0, got {bits_out[3]}"


# ---------------------------------------------------------------------------
# Tests: SSHR-H full synthesis
# ---------------------------------------------------------------------------

def test_sshr_h_3majority():
    """3-Majority function."""
    n = 3
    # f = 1 iff popcount >= 2: onset = {3,5,6,7}
    bf = BooleanFunction.from_list(n, [0,0,0,1,0,1,1,1])
    circ = sshr_h(bf)
    assert circuit_implements(bf, circ), "SSHR-H failed for 3-majority"


def test_sshr_h_paper_example():
    """Paper example: 4-bit function with ID=0x46B9."""
    n = 4
    bf = BooleanFunction.from_hex(n, "46B9")
    circ = sshr_h(bf)
    assert circuit_implements(bf, circ), "SSHR-H failed for paper example 0x46B9"


def test_sshr_h_all_3bit():
    """All 256 3-bit Boolean functions."""
    n = 3
    fails = []
    for tt in range(256):
        bf = BooleanFunction(n, tt)
        if not bf.onset:
            continue
        circ = sshr_h(bf)
        if not circuit_implements(bf, circ):
            fails.append(tt)
    assert not fails, f"SSHR-H failed for truth tables: {[hex(t) for t in fails]}"


def test_sshr_h_all_4bit_sample():
    """Sample of 4-bit Boolean functions."""
    import random
    n = 4
    rng = random.Random(0)
    tts = rng.sample(range(1 << 16), 200)
    fails = []
    for tt in tts:
        bf = BooleanFunction(n, tt)
        if not bf.onset:
            continue
        circ = sshr_h(bf)
        if not circuit_implements(bf, circ):
            fails.append(tt)
    assert not fails, f"SSHR-H failed for {len(fails)}/200 4-bit functions"


# ---------------------------------------------------------------------------
# Tests: SSHR-I (only if ILP solver available)
# ---------------------------------------------------------------------------

def test_sshr_i_paper_example():
    """Paper example: 4-bit function with ID=0x46B9 using SSHR-I."""
    try:
        import gurobipy
    except ImportError:
        pytest.skip("gurobipy not installed")
    from sshr_i import sshr_i
    n = 4
    bf = BooleanFunction.from_hex(n, "46B9")
    circ = sshr_i(bf, objective="cnot", timeout=30)
    assert circuit_implements(bf, circ), "SSHR-I failed for paper example 0x46B9"
