#!/usr/bin/env python3
"""Affine input preconditioning for Boolean-oracle synthesis."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit

from src.resource_model import ResourceCost


@dataclass(frozen=True)
class AffineTransform:
    rows: tuple[int, ...]


def identity_rows(n: int) -> tuple[int, ...]:
    return tuple(1 << i for i in range(n))


def apply_rows(rows: Sequence[int], x: int) -> int:
    out = 0
    for i, row in enumerate(rows):
        if (row & x).bit_count() & 1:
            out |= 1 << i
    return out


def invert_rows(rows: Sequence[int]) -> tuple[int, ...]:
    n = len(rows)
    left = list(rows)
    right = [1 << i for i in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if (left[r] >> col) & 1), None)
        if pivot is None:
            raise ValueError("matrix is singular")
        if pivot != col:
            left[col], left[pivot] = left[pivot], left[col]
            right[col], right[pivot] = right[pivot], right[col]
        for r in range(n):
            if r != col and ((left[r] >> col) & 1):
                left[r] ^= left[col]
                right[r] ^= right[col]
    return tuple(right)


def transform_function(bf: BooleanFunction, rows: Sequence[int]) -> BooleanFunction:
    """Return h(y)=f(B^{-1}y), where rows encode y=B x."""
    inv = invert_rows(rows)
    tt = 0
    for y in range(1 << bf.n):
        x = apply_rows(inv, y)
        if bf.evaluate(x):
            tt |= 1 << y
    return BooleanFunction(bf.n, tt)


def linear_cnot_sequence(rows: Sequence[int]) -> list[tuple[int, int]]:
    """Return CNOTs implementing y=B x for row-encoded matrix B."""
    n = len(rows)
    work = list(rows)
    ops: list[tuple[int, int]] = []

    def row_add(control: int, target: int) -> None:
        work[target] ^= work[control]
        ops.append((control, target))

    def row_swap(i: int, j: int) -> None:
        row_add(j, i)
        row_add(i, j)
        row_add(j, i)

    for col in range(n):
        pivot = next((r for r in range(col, n) if (work[r] >> col) & 1), None)
        if pivot is None:
            raise ValueError("matrix is singular")
        if pivot != col:
            row_swap(col, pivot)
        for r in range(n):
            if r != col and ((work[r] >> col) & 1):
                row_add(col, r)
    if tuple(work) != identity_rows(n):
        raise ValueError("matrix reduction failed")
    return list(reversed(ops))


def affine_wrap_cost(rows: Sequence[int]) -> ResourceCost:
    cnot = 2 * len(linear_cnot_sequence(rows))
    return ResourceCost(CNOT=cnot, gates=cnot, depth=cnot)


def emit_affine_wrapped(body: QuantumCircuit, rows: Sequence[int]) -> QuantumCircuit:
    circ = QuantumCircuit(body.n_qubits)
    seq = linear_cnot_sequence(rows)
    for control, target in seq:
        circ.add_cnot(control, target)
    circ.add_block(body)
    for control, target in reversed(seq):
        circ.add_cnot(control, target)
    return circ


def candidate_transforms(n: int, seed: int, budget: int) -> list[AffineTransform]:
    rng = random.Random(seed)
    seen: set[tuple[int, ...]] = set()
    out: list[AffineTransform] = []

    def add(rows: Sequence[int]) -> None:
        key = tuple(rows)
        if key not in seen:
            seen.add(key)
            out.append(AffineTransform(key))

    add(identity_rows(n))

    for center in range(n):
        rows = list(identity_rows(n))
        for target in range(n):
            if target != center:
                rows[target] ^= rows[center]
        add(rows)
        if len(out) >= budget:
            return out[:budget]

    for control in range(n):
        for target in range(n):
            if control == target:
                continue
            rows = list(identity_rows(n))
            rows[target] ^= rows[control]
            add(rows)
            if len(out) >= budget:
                return out[:budget]

    while len(out) < budget:
        rows = list(identity_rows(n))
        steps = rng.randint(2, max(2, 2 * n))
        for _ in range(steps):
            control = rng.randrange(n)
            target = rng.randrange(n - 1)
            if target >= control:
                target += 1
            rows[target] ^= rows[control]
        add(rows)
    return out[:budget]

