#!/usr/bin/env python3
"""Resource accounting for logical Boolean-oracle synthesis plans."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from src.sshr_lib.bool_func import mct_cost, mct_cost_rp


@dataclass(frozen=True)
class ResourceWeights:
    t: float = 1.0
    cnot: float = 0.05
    depth: float = 0.02
    gates: float = 0.01
    ancilla: float = 2.0


@dataclass(frozen=True)
class ResourceCost:
    T: int = 0
    CNOT: int = 0
    gates: int = 0
    depth: int = 0
    explicit_ancilla: int = 0
    peak_ancilla: int = 0

    def __add__(self, other: "ResourceCost") -> "ResourceCost":
        return ResourceCost(
            T=self.T + other.T,
            CNOT=self.CNOT + other.CNOT,
            gates=self.gates + other.gates,
            depth=self.depth + other.depth,
            explicit_ancilla=max(self.explicit_ancilla, other.explicit_ancilla),
            peak_ancilla=max(self.peak_ancilla, other.peak_ancilla),
        )

    def score(self, weights: ResourceWeights) -> float:
        return (
            weights.t * self.T
            + weights.cnot * self.CNOT
            + weights.depth * self.depth
            + weights.gates * self.gates
            + weights.ancilla * self.peak_ancilla
        )


def gate_cost(
    controls: int,
    live_factor_ancilla: int,
    weights: ResourceWeights | None = None,
    use_relative_phase: bool = True,
    alloc_target_ancilla: bool = False,
    gate_mode: str = "mct",
) -> ResourceCost:
    """Return resource estimate for one logical controlled-X operation."""
    live = live_factor_ancilla + (1 if alloc_target_ancilla else 0)
    if controls <= 0:
        return ResourceCost(gates=1, depth=1, explicit_ancilla=live, peak_ancilla=live)
    if controls == 1:
        return ResourceCost(CNOT=1, gates=1, depth=1, explicit_ancilla=live, peak_ancilla=live)
    if gate_mode == "logical_and":
        ands = controls - 1
        temp = max(0, controls - 2)
        return ResourceCost(
            T=4 * ands,
            CNOT=6 * ands + 1,
            gates=2 * ands + 1,
            depth=6 * ands + 1,
            explicit_ancilla=live,
            peak_ancilla=live + temp,
        )
    if gate_mode != "mct":
        raise ValueError(f"unknown gate_mode: {gate_mode}")
    c = mct_cost_rp(controls) if use_relative_phase else mct_cost(controls)
    # Sequential decomposed-depth estimate; enough for relative comparisons.
    depth = max(1, int(c["CNOT"]))
    helper = int(c.get("ancilla", 0))
    return ResourceCost(
        T=int(c["T"]),
        CNOT=int(c["CNOT"]),
        gates=1,
        depth=depth,
        explicit_ancilla=live,
        peak_ancilla=live + helper,
    )


def gate_uncompute_cost(
    controls: int,
    live_factor_ancilla: int,
    use_relative_phase: bool = True,
    alloc_target_ancilla: bool = False,
    gate_mode: str = "mct",
) -> ResourceCost:
    """Return the cleanup cost for a temporary logical conjunction.

    In ``logical_and`` mode this follows the common low-T accounting where a
    temporary logical AND is computed with four T gates and uncomputed with
    Clifford operations and measurement/feed-forward.  The emitted verifier
    circuit remains a deterministic MCT circuit; this function is only the
    logic-level resource model used by the search objective.
    """
    live = live_factor_ancilla + (1 if alloc_target_ancilla else 0)
    if gate_mode == "logical_and" and controls >= 2:
        ands = controls - 1
        temp = max(0, controls - 2)
        return ResourceCost(
            T=0,
            CNOT=3 * ands,
            gates=ands,
            depth=3 * ands,
            explicit_ancilla=live,
            peak_ancilla=live + temp,
        )
    return gate_cost(
        controls,
        live_factor_ancilla,
        use_relative_phase=use_relative_phase,
        alloc_target_ancilla=alloc_target_ancilla,
        gate_mode=gate_mode,
    )


@lru_cache(maxsize=200_000)
def direct_cost_for_terms(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    use_relative_phase: bool = True,
    gate_mode: str = "mct",
) -> ResourceCost:
    counts: dict[int, int] = {}
    for term in terms:
        controls = prefix_len + int(term).bit_count()
        counts[controls] = counts.get(controls, 0) + 1

    T = CNOT = gates = depth = 0
    peak = live_factor_ancilla
    for controls, count in counts.items():
        cost = gate_cost(
            controls,
            live_factor_ancilla=live_factor_ancilla,
            use_relative_phase=use_relative_phase,
            gate_mode=gate_mode,
        )
        T += cost.T * count
        CNOT += cost.CNOT * count
        gates += cost.gates * count
        depth += cost.depth * count
        peak = max(peak, cost.peak_ancilla)
    return ResourceCost(
        T=T,
        CNOT=CNOT,
        gates=gates,
        depth=depth,
        explicit_ancilla=live_factor_ancilla,
        peak_ancilla=peak,
    )
