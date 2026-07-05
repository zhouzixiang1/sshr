#!/usr/bin/env python3
"""Resource accounting for logical Boolean-oracle synthesis plans."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import mct_cost, mct_cost_rp  # noqa: E402


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
) -> ResourceCost:
    """Return resource estimate for one logical controlled-X operation."""
    live = live_factor_ancilla + (1 if alloc_target_ancilla else 0)
    if controls <= 0:
        return ResourceCost(gates=1, depth=1, explicit_ancilla=live, peak_ancilla=live)
    if controls == 1:
        return ResourceCost(CNOT=1, gates=1, depth=1, explicit_ancilla=live, peak_ancilla=live)
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


def direct_cost_for_terms(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    use_relative_phase: bool = True,
) -> ResourceCost:
    out = ResourceCost(explicit_ancilla=live_factor_ancilla, peak_ancilla=live_factor_ancilla)
    for term in terms:
        out += gate_cost(
            prefix_len + int(term).bit_count(),
            live_factor_ancilla=live_factor_ancilla,
            use_relative_phase=use_relative_phase,
        )
    return out

