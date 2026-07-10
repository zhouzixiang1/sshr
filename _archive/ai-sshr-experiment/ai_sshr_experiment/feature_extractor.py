"""Feature extraction utilities for AI-SSHR experiments.

This module keeps the experimental code outside the flat `sshr/` module
layout while still reusing the existing SSHR implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys
from typing import Dict, Iterable, List


def ensure_sshr_on_path() -> Path:
    """Add the repository's `sshr/` directory to sys.path and return it."""
    repo_root = Path(__file__).resolve().parents[1]
    sshr_dir = repo_root / "sshr"
    if str(sshr_dir) not in sys.path:
        sys.path.insert(0, str(sshr_dir))
    return sshr_dir


ensure_sshr_on_path()

from block_synth import block_cnot_cost  # noqa: E402
from bool_func import BooleanFunction, mct_cost  # noqa: E402
from parallelotope import Parallelotope  # noqa: E402
from parallelotope_enum import enumerate_parallelotopes  # noqa: E402


def popcount(x: int) -> int:
    return x.bit_count()


def vertices_to_mask(vertices: Iterable[int]) -> int:
    mask = 0
    for v in vertices:
        mask |= 1 << v
    return mask


def onset_mask(bf: BooleanFunction) -> int:
    return vertices_to_mask(bf.onset)


def support_size(mask: int) -> int:
    return mask.bit_count()


def block_t_cost_rp(p: Parallelotope, n: int) -> int:
    """Relative-phase Toffoli T cost used in Table VII style reporting."""
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_count = (((1 << n) - 1) & ~covered).bit_count()
    n_inner = sum(alpha.bit_count() - 1 for alpha in p.basis if alpha)
    controls = n_inner + common_count
    if controls < 2:
        return 0
    if controls == 2:
        return 4
    return mct_cost(controls)["T"]


def block_control_count(p: Parallelotope, n: int) -> int:
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    common_count = (((1 << n) - 1) & ~covered).bit_count()
    n_inner = sum(alpha.bit_count() - 1 for alpha in p.basis if alpha)
    return n_inner + common_count


@dataclass(frozen=True)
class CandidateRecord:
    idx: int
    p: Parallelotope
    mask: int
    size: int
    dim: int
    cnot_cost: int
    t_cost: int
    control_count: int
    is_singleton: bool
    covered_support: int

    def cost(self, objective: str) -> float:
        return float(self.cnot_cost if objective == "cnot" else self.t_cost)


@lru_cache(maxsize=8)
def build_candidates(n: int) -> List[CandidateRecord]:
    """Enumerate full-hypercube parallelotopes plus singleton fallbacks."""
    all_p: List[Parallelotope] = enumerate_parallelotopes(list(range(1 << n)), n)
    seen = {p.vertices() for p in all_p}
    for v in range(1 << n):
        singleton = frozenset([v])
        if singleton not in seen:
            all_p.append(Parallelotope(v, []))
            seen.add(singleton)

    records: List[CandidateRecord] = []
    for idx, p in enumerate(all_p):
        verts = p.vertices()
        covered_support = 0
        for alpha in p.basis:
            covered_support |= alpha
        records.append(
            CandidateRecord(
                idx=idx,
                p=p,
                mask=vertices_to_mask(verts),
                size=len(verts),
                dim=p.dim,
                cnot_cost=block_cnot_cost(p, n),
                t_cost=block_t_cost_rp(p, n),
                control_count=block_control_count(p, n),
                is_singleton=(p.dim == 0),
                covered_support=covered_support,
            )
        )
    return records


def singleton_index(records: List[CandidateRecord], vertex: int) -> int:
    target = 1 << vertex
    for rec in records:
        if rec.is_singleton and rec.mask == target:
            return rec.idx
    raise KeyError(f"missing singleton candidate for vertex {vertex}")


def candidate_features(
    rec: CandidateRecord,
    a_mask: int,
    n: int,
    current_cost: float = 0.0,
    objective: str = "cnot",
) -> Dict[str, float]:
    """Return numeric features for a candidate under active state A."""
    overlap = popcount(rec.mask & a_mask)
    off_count = rec.size - overlap
    active_size = popcount(a_mask)
    monotone_valid = 1.0 if (rec.mask & a_mask) == rec.mask else 0.0
    next_mask_mono = a_mask & ~rec.mask
    next_mask_xor = a_mask ^ rec.mask
    cost = rec.cost(objective)

    return {
        "n": float(n),
        "dim": float(rec.dim),
        "size": float(rec.size),
        "log_size": float(rec.size.bit_length() - 1),
        "cnot_cost": float(rec.cnot_cost),
        "t_cost": float(rec.t_cost),
        "objective_cost": float(cost),
        "control_count": float(rec.control_count),
        "is_singleton": 1.0 if rec.is_singleton else 0.0,
        "support_bits": float(support_size(rec.covered_support)),
        "active_size": float(active_size),
        "overlap": float(overlap),
        "off_count": float(off_count),
        "cover_ratio": float(overlap / rec.size if rec.size else 0.0),
        "off_ratio": float(off_count / rec.size if rec.size else 0.0),
        "monotone_valid": monotone_valid,
        "mono_removed": float(active_size - popcount(next_mask_mono)),
        "xor_next_size": float(popcount(next_mask_xor)),
        "mono_next_size": float(popcount(next_mask_mono)),
        "cost_per_overlap": float(cost / max(overlap, 1)),
        "cost_per_size": float(cost / max(rec.size, 1)),
        "current_cost": float(current_cost),
        # --- New features (appended after original 22) ---
        "t_cnot_ratio": float(rec.t_cost / max(rec.cnot_cost, 1)),
        "cover_per_dim": float(overlap / max(rec.dim, 1)),
        "xor_parity_flip": float(popcount(next_mask_xor) - active_size),
        "basis_overlap": float(
            popcount(rec.covered_support & a_mask)
            / max(support_size(rec.covered_support), 1)
        ),
        "dim_cost_ratio": float(rec.dim / max(cost, 1)),
        "size_cost_ratio": float(rec.size / max(cost, 1)),
        "off_active_ratio": float(off_count / max(active_size, 1)),
        "mono_xor_gap": float(popcount(next_mask_mono) - popcount(next_mask_xor)),
        "greedy_value": float(overlap / max(cost, 1)),
    }


def feature_names() -> List[str]:
    """Stable feature order for model adapters."""
    return [
        "n",
        "dim",
        "size",
        "log_size",
        "cnot_cost",
        "t_cost",
        "objective_cost",
        "control_count",
        "is_singleton",
        "support_bits",
        "active_size",
        "overlap",
        "off_count",
        "cover_ratio",
        "off_ratio",
        "monotone_valid",
        "mono_removed",
        "xor_next_size",
        "mono_next_size",
        "cost_per_overlap",
        "cost_per_size",
        "current_cost",
        # --- New features (appended after original 22) ---
        "t_cnot_ratio",
        "cover_per_dim",
        "xor_parity_flip",
        "basis_overlap",
        "dim_cost_ratio",
        "size_cost_ratio",
        "off_active_ratio",
        "mono_xor_gap",
        "greedy_value",
    ]

