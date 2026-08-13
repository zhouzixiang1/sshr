#!/usr/bin/env python3
"""ESOP cube search over arbitrary-polarity product terms.

This is a symbolic Boolean synthesis backend.  It searches axis-aligned cubes
with XOR semantics and does not use SSHR parallelotopes.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import heapq
from typing import Iterable, List, Sequence

from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit  # noqa: E402

from src.resource_model import ResourceCost, ResourceWeights, gate_cost


@dataclass(frozen=True)
class Cube:
    care: int
    value: int
    cover: int
    controls: int
    zeros: int
    cost: ResourceCost
    score: float


@dataclass
class CubePlan:
    cubes: List[Cube]
    cost: ResourceCost

    def score(self, weights: ResourceWeights) -> float:
        return self.cost.score(weights)


def _cube_cover_mask(n: int, care: int, value: int) -> int:
    mask = 0
    free_bits = [b for b in range(n) if not ((care >> b) & 1)]
    for z in range(1 << len(free_bits)):
        x = value
        for i, b in enumerate(free_bits):
            if (z >> i) & 1:
                x |= 1 << b
        mask |= 1 << x
    return mask


@lru_cache(maxsize=24)
def enumerate_cubes(
    n: int,
    max_controls: int,
    use_relative_phase: bool,
    gate_mode: str,
    weight_tuple: tuple[float, float, float, float, float],
) -> tuple[Cube, ...]:
    weights = ResourceWeights(*weight_tuple)
    out: list[Cube] = []
    for care in range(1 << n):
        controls = care.bit_count()
        if controls > max_controls:
            continue
        value = care
        sub = care
        # Iterate all assignments to cared literals.
        v = sub
        first = True
        value = care
        assignment = value
        assignments = []
        a = care
        # Submask iteration over cared bits gives all value masks.
        s = care
        while True:
            assignments.append(s)
            if s == 0:
                break
            s = (s - 1) & care
        for value in assignments:
            zeros = controls - (value & care).bit_count()
            cover = _cube_cover_mask(n, care, value)
            cost = gate_cost(
                controls,
                live_factor_ancilla=0,
                use_relative_phase=use_relative_phase,
                gate_mode=gate_mode,
            )
            wrap = 2 * zeros
            cost = ResourceCost(
                T=cost.T,
                CNOT=cost.CNOT,
                gates=cost.gates + wrap,
                depth=cost.depth + wrap,
                explicit_ancilla=cost.explicit_ancilla,
                peak_ancilla=cost.peak_ancilla,
            )
            out.append(
                Cube(
                    care=care,
                    value=value,
                    cover=cover,
                    controls=controls,
                    zeros=zeros,
                    cost=cost,
                    score=cost.score(weights),
                )
            )
    out.sort(key=lambda c: (c.score, c.controls, c.zeros, c.care, c.value))
    return tuple(out)


def onset_mask(bf: BooleanFunction) -> int:
    mask = 0
    for x in bf.onset:
        mask |= 1 << x
    return mask


def _add_cost(a: ResourceCost, b: ResourceCost) -> ResourceCost:
    return a + b


def _candidate_gain(active: int, cube: Cube) -> int:
    return active.bit_count() - (active ^ cube.cover).bit_count()


def _top_actions(
    active: int,
    cubes: Sequence[Cube],
    branch: int,
    allow_nonpositive: bool = False,
) -> list[tuple[float, int, Cube]]:
    actions: list[tuple[float, int, Cube]] = []
    for cube in cubes:
        gain = _candidate_gain(active, cube)
        if gain <= 0 and not allow_nonpositive:
            continue
        # Prefer large net reduction per resource, with a small absolute-gain
        # bonus so large cubes are not dominated by singletons.
        denom = max(gain, 0.25)
        priority = cube.score / denom - 0.03 * gain + 0.002 * cube.controls
        actions.append((priority, -gain, cube))
        if len(actions) > branch * 16:
            # Since cubes are sorted by intrinsic cost, this cap keeps very large
            # n runs tractable while preserving cheap candidates.
            actions = heapq.nsmallest(branch * 8, actions, key=lambda x: (x[0], x[1]))
    return heapq.nsmallest(branch, actions, key=lambda x: (x[0], x[1]))


def cube_greedy_plan(
    bf: BooleanFunction,
    weights: ResourceWeights,
    max_controls: int = 6,
    use_relative_phase: bool = True,
    gate_mode: str = "mct",
    branch: int = 64,
) -> CubePlan:
    cubes = enumerate_cubes(
        bf.n,
        max_controls,
        use_relative_phase,
        gate_mode,
        (weights.t, weights.cnot, weights.depth, weights.gates, weights.ancilla),
    )
    active = onset_mask(bf)
    path: list[Cube] = []
    cost = ResourceCost()
    seen = set()
    while active:
        if active in seen:
            break
        seen.add(active)
        actions = _top_actions(active, cubes, branch=branch)
        if not actions:
            # Singleton fallback always reduces the active set.
            x = (active & -active).bit_length() - 1
            care = (1 << bf.n) - 1
            value = x
            cover = 1 << x
            controls = bf.n
            zeros = bf.n - x.bit_count()
            base = gate_cost(controls, 0, use_relative_phase=use_relative_phase, gate_mode=gate_mode)
            cube = Cube(care, value, cover, controls, zeros, base, base.score(weights))
        else:
            cube = actions[0][2]
        path.append(cube)
        cost = _add_cost(cost, cube.cost)
        active ^= cube.cover
    return CubePlan(path, cost)


def cube_beam_plan(
    bf: BooleanFunction,
    weights: ResourceWeights,
    max_controls: int = 6,
    width: int = 24,
    branch: int = 16,
    max_steps: int | None = None,
    use_relative_phase: bool = True,
    gate_mode: str = "mct",
) -> CubePlan:
    cubes = enumerate_cubes(
        bf.n,
        max_controls,
        use_relative_phase,
        gate_mode,
        (weights.t, weights.cnot, weights.depth, weights.gates, weights.ancilla),
    )
    start = onset_mask(bf)
    if start == 0:
        return CubePlan([], ResourceCost())
    if max_steps is None:
        max_steps = max(1, min(4 * start.bit_count(), 2 * (1 << bf.n)))
    # State: estimated priority, active, cost, path.
    beam = [(0.0, start, ResourceCost(), [])]
    best: CubePlan | None = None
    seen_best: dict[int, float] = {start: 0.0}
    for _ in range(max_steps):
        nxt = []
        for _, active, cost, path in beam:
            if active == 0:
                plan = CubePlan(path, cost)
                if best is None or plan.score(weights) < best.score(weights):
                    best = plan
                continue
            actions = _top_actions(active, cubes, branch=branch)
            if not actions:
                continue
            for _, _, cube in actions:
                new_active = active ^ cube.cover
                new_cost = cost + cube.cost
                score = new_cost.score(weights)
                if score >= seen_best.get(new_active, float("inf")):
                    continue
                seen_best[new_active] = score
                # Lower bound: each remaining active bit can be fixed by at
                # least one CNOT/singleton-like operation; this is deliberately
                # weak but helps ranking.
                priority = score + 0.01 * new_active.bit_count()
                nxt.append((priority, new_active, new_cost, path + [cube]))
        if not nxt:
            break
        beam = heapq.nsmallest(width, nxt, key=lambda x: x[0])
    if best is not None:
        return best
    # Fall back to greedy if the beam did not finish.
    return cube_greedy_plan(
        bf,
        weights,
        max_controls=max_controls,
        use_relative_phase=use_relative_phase,
        gate_mode=gate_mode,
    )


def emit_cube_plan(plan: CubePlan, n_inputs: int) -> QuantumCircuit:
    circ = QuantumCircuit(n_inputs + 1)
    output = n_inputs
    for cube in plan.cubes:
        controls = [b for b in range(n_inputs) if (cube.care >> b) & 1]
        zeros = [b for b in controls if not ((cube.value >> b) & 1)]
        for b in zeros:
            circ.add_x(b)
        circ.add_mct(controls, output)
        for b in zeros:
            circ.add_x(b)
    return circ
