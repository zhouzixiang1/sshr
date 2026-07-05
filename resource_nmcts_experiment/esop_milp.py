#!/usr/bin/env python3
"""Weighted ESOP synthesis via SciPy MILP."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import List

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, hstack

ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import BooleanFunction  # noqa: E402

from cube_search import Cube, CubePlan, emit_cube_plan, enumerate_cubes
from resource_model import ResourceCost, ResourceWeights


@dataclass
class MilpResult:
    plan: CubePlan
    success: bool
    status: int
    message: str


def _bits(mask: int):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def esop_milp_plan(
    bf: BooleanFunction,
    weights: ResourceWeights,
    max_controls: int | None = None,
    timeout: float = 20.0,
    use_relative_phase: bool = True,
    gate_mode: str = "mct",
) -> MilpResult:
    n = bf.n
    max_controls = n if max_controls is None else min(max_controls, n)
    cubes = list(
        enumerate_cubes(
            n,
            max_controls,
            use_relative_phase,
            gate_mode,
            (weights.t, weights.cnot, weights.depth, weights.gates, weights.ancilla),
        )
    )
    m = len(cubes)
    N = 1 << n

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for i, cube in enumerate(cubes):
        for x in _bits(cube.cover):
            rows.append(x)
            cols.append(i)
            data.append(1.0)
    A_x = coo_matrix((data, (rows, cols)), shape=(N, m)).tocsr()
    A_y = coo_matrix(([-2.0] * N, (range(N), range(N))), shape=(N, N)).tocsr()
    A = hstack([A_x, A_y], format="csr")

    b = np.array([(bf.truth_table >> x) & 1 for x in range(N)], dtype=float)
    c = np.array([cube.score for cube in cubes] + [0.0] * N, dtype=float)
    lb = np.zeros(m + N)
    ub = np.array([1.0] * m + [max(1.0, float(m))] * N)
    integrality = np.ones(m + N, dtype=int)
    constraints = LinearConstraint(A, b, b)
    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=constraints,
        options={"time_limit": timeout, "mip_rel_gap": 0.0},
    )
    if result.x is None:
        return MilpResult(CubePlan([], ResourceCost()), False, int(result.status), str(result.message))
    selected = [cubes[i] for i in range(m) if result.x[i] > 0.5]
    cost = ResourceCost()
    for cube in selected:
        cost += cube.cost
    return MilpResult(
        CubePlan(selected, cost),
        bool(result.success),
        int(result.status),
        str(result.message),
    )


def synthesize_esop_milp_circuit(
    bf: BooleanFunction,
    weights: ResourceWeights,
    max_controls: int | None = None,
    timeout: float = 20.0,
    gate_mode: str = "mct",
):
    result = esop_milp_plan(bf, weights, max_controls=max_controls, timeout=timeout, gate_mode=gate_mode)
    return emit_cube_plan(result.plan, bf.n), result
