#!/usr/bin/env python3
"""ANF utilities and benchmark Boolean-function generators."""
from __future__ import annotations

import random
from functools import lru_cache
from itertools import combinations
from typing import Iterable, List, Sequence, Set

from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


def anf_monomials(bf: BooleanFunction) -> Set[int]:
    """Return ANF monomial masks for ``bf``."""
    coeff = [(bf.truth_table >> i) & 1 for i in range(1 << bf.n)]
    for bit in range(bf.n):
        step = 1 << bit
        block = step << 1
        for start in range(0, 1 << bf.n, block):
            for mask in range(start + step, start + block):
                coeff[mask] ^= coeff[mask ^ step]
    return {i for i, v in enumerate(coeff) if v & 1}


def truth_table_from_anf(n: int, monomials: Iterable[int]) -> int:
    """Evaluate ANF monomials and return a truth-table integer.

    The truth table uses bit ``x`` for assignment ``x``.  For high-dimensional
    bridge tests it is much faster to evaluate each monomial as a large integer
    bit mask than to run a Python-level zeta transform over all coefficients.
    """
    size = 1 << n
    all_assignments = (1 << size) - 1
    variable_masks = _variable_truth_masks(n)
    tt = 0
    valid_variable_mask = (1 << n) - 1
    for raw in monomials:
        monomial = int(raw)
        if monomial & ~valid_variable_mask:
            raise ValueError(f"monomial mask {monomial:#x} has variables outside n={n}")
        term_tt = all_assignments
        remaining = monomial
        while remaining:
            bit = (remaining & -remaining).bit_length() - 1
            term_tt &= variable_masks[bit]
            remaining &= remaining - 1
        tt ^= term_tt
    return tt


@lru_cache(maxsize=4)
def _variable_truth_masks(n: int) -> tuple[int, ...]:
    """Return truth-table masks for variables x_0..x_{n-1}.

    The byte patterns are little-endian because truth-table bit ``x`` stores the
    value at assignment ``x``.  For example, x_0 is 0xaa, x_1 is 0xcc, and x_2 is
    0xf0 in every byte.
    """
    if n < 0:
        raise ValueError("n must be nonnegative")
    size = 1 << n
    if n < 3:
        masks: list[int] = []
        for bit in range(n):
            mask = 0
            for x in range(size):
                if (x >> bit) & 1:
                    mask |= 1 << x
            masks.append(mask)
        return tuple(masks)

    byte_count = 1 << (n - 3)
    masks = []
    single_byte_patterns = {0: 0xAA, 1: 0xCC, 2: 0xF0}
    for bit in range(n):
        if bit in single_byte_patterns:
            buf = bytes([single_byte_patterns[bit]]) * byte_count
        else:
            run = 1 << (bit - 3)
            pattern = (b"\x00" * run) + (b"\xff" * run)
            buf = pattern * (byte_count // len(pattern))
        masks.append(int.from_bytes(buf, "little"))
    return tuple(masks)


def boolean_from_anf(n: int, monomials: Iterable[int]) -> BooleanFunction:
    return BooleanFunction(n, truth_table_from_anf(n, monomials))


def shifted_function(bf: BooleanFunction, polarity: int) -> BooleanFunction:
    """Return g(z)=f(z xor polarity), used for fixed-polarity RM synthesis."""
    tt = 0
    for z in range(1 << bf.n):
        if bf.evaluate(z ^ polarity):
            tt |= 1 << z
    return BooleanFunction(bf.n, tt)


def random_truth_function(n: int, rng: random.Random) -> BooleanFunction:
    return BooleanFunction(n, rng.getrandbits(1 << n))


def random_anf_function(
    n: int,
    rng: random.Random,
    term_prob: float = 0.12,
    max_degree: int | None = None,
    ensure_nonzero: bool = True,
) -> BooleanFunction:
    max_degree = n if max_degree is None else min(max_degree, n)
    monomials: Set[int] = set()
    for m in range(1 << n):
        if m.bit_count() <= max_degree and rng.random() < term_prob:
            monomials.add(m)
    if ensure_nonzero and not monomials:
        monomials.add(1 << rng.randrange(n))
    return boolean_from_anf(n, monomials)


def parity_function(n: int) -> BooleanFunction:
    return boolean_from_anf(n, (1 << i for i in range(n)))


def majority_function(n: int) -> BooleanFunction:
    threshold = n // 2 + 1
    tt = 0
    for x in range(1 << n):
        if x.bit_count() >= threshold:
            tt |= 1 << x
    return BooleanFunction(n, tt)


def threshold_function(n: int, threshold: int) -> BooleanFunction:
    tt = 0
    for x in range(1 << n):
        if x.bit_count() >= threshold:
            tt |= 1 << x
    return BooleanFunction(n, tt)


def mux_function(select_bits: int, data_bits: int) -> BooleanFunction:
    """Return a small multiplexer Boolean function.

    Variables 0..select_bits-1 are select bits.  The following data bits are
    addressed by the select value modulo ``data_bits``.
    """
    n = select_bits + data_bits
    tt = 0
    for x in range(1 << n):
        sel = x & ((1 << select_bits) - 1)
        idx = sel % data_bits
        if (x >> (select_bits + idx)) & 1:
            tt |= 1 << x
    return BooleanFunction(n, tt)


def adder_carry_function(width: int) -> BooleanFunction:
    """Carry-out bit for adding two ``width``-bit unsigned integers."""
    n = 2 * width
    tt = 0
    mod = 1 << width
    for x in range(1 << n):
        a = x & (mod - 1)
        b = (x >> width) & (mod - 1)
        if a + b >= mod:
            tt |= 1 << x
    return BooleanFunction(n, tt)


def multiplier_bit_function(width: int, bit: int) -> BooleanFunction:
    """One output bit of multiplying two ``width``-bit unsigned integers."""
    n = 2 * width
    tt = 0
    for x in range(1 << n):
        a = x & ((1 << width) - 1)
        b = (x >> width) & ((1 << width) - 1)
        if ((a * b) >> bit) & 1:
            tt |= 1 << x
    return BooleanFunction(n, tt)


def structured_suite() -> List[tuple[str, BooleanFunction]]:
    out: List[tuple[str, BooleanFunction]] = []
    for n in range(3, 9):
        out.append((f"parity_n{n}", parity_function(n)))
        out.append((f"majority_n{n}", majority_function(n)))
        out.append((f"threshold{max(2, n//2)}_n{n}", threshold_function(n, max(2, n // 2))))
    out.append(("mux_2_4", mux_function(2, 4)))
    out.append(("mux_3_8", mux_function(3, 8)))
    for w in [2, 3, 4]:
        out.append((f"adder_carry_w{w}", adder_carry_function(w)))
    for w, bit in [(2, 1), (3, 2), (4, 3)]:
        out.append((f"mul_w{w}_bit{bit}", multiplier_bit_function(w, bit)))
    return out


def monomial_str(mask: int, n: int) -> str:
    if mask == 0:
        return "1"
    return "".join(f"x{i}" for i in range(n) if (mask >> i) & 1)


def anf_str(monomials: Sequence[int], n: int, limit: int = 32) -> str:
    terms = [monomial_str(m, n) for m in sorted(monomials, key=lambda x: (x.bit_count(), x))]
    if len(terms) > limit:
        return " + ".join(terms[:limit]) + f" + ... ({len(terms)} terms)"
    return " + ".join(terms) if terms else "0"
