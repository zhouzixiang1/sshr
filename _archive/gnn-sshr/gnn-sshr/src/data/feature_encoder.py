"""
Hand-crafted candidate feature encoder for the LightGBM baseline ranker.

Each row of the returned matrix describes a single parallelotope candidate
relative to the current Boolean function's onset.  The features are
deliberately simple and cheap to compute so they can serve as a strong
non-neural baseline against the GNN ranker.

Used by:
    - LightGBM training pipeline (legacy ranker)
    - Ablation studies in `gnn-sshr/experiments`

Feature columns (K = 14):
    0  dim                  : parallelotope dimension k (number of basis vectors)
    1  size                 : 2^k, number of vertices in the block
    2  log2_size            : log2(size) = dim
    3  on_overlap           : |vertices ∩ onset|
    4  off_overlap          : |vertices ∩ offset|
    5  on_ratio             : on_overlap / size
    6  cnot_cost_estimate   : 2*max(0, dim-1) + popcount(v0)*2  (rough proxy)
    7  t_cost_estimate      : 4*max(0, dim-1)
    8  control_count        : popcount(v0) + dim
    9  is_singleton         : 1.0 if dim == 0 else 0.0
   10  overlap_ratio        : (on_overlap + off_overlap) / size  (≈1 always)
   11  off_ratio            : off_overlap / size
   12  position_entropy     : average per-bit Shannon entropy across vertex bits
   13  structural_rarity    : 1 / count(candidates with same dim)
"""
from __future__ import annotations

import argparse
import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np


FEATURE_NAMES: Tuple[str, ...] = (
    "dim",
    "size",
    "log2_size",
    "on_overlap",
    "off_overlap",
    "on_ratio",
    "cnot_cost_estimate",
    "t_cost_estimate",
    "control_count",
    "is_singleton",
    "overlap_ratio",
    "off_ratio",
    "position_entropy",
    "structural_rarity",
)

NUM_FEATURES: int = len(FEATURE_NAMES)


def _popcount(x: int) -> int:
    """Return the number of set bits in a non-negative integer."""
    return int(x).bit_count() if hasattr(int(x), "bit_count") else bin(int(x)).count("1")


def _candidate_vertices(p: object) -> List[int]:
    """Resolve the list of integer-encoded vertices for a candidate object."""
    if hasattr(p, "vertices"):
        verts = p.vertices()
        return list(verts)
    if hasattr(p, "_vertices") and p._vertices is not None:
        return list(p._vertices)
    # Fall back: dim==0 candidate carrying just a vertex int.
    if hasattr(p, "v0"):
        return [int(p.v0)]
    raise AttributeError(
        f"Candidate {p!r} does not expose a vertex set (no .vertices() / .v0)."
    )


def _candidate_dim(p: object) -> int:
    """Return the parallelotope dimension k (number of basis vectors)."""
    if hasattr(p, "dim"):
        return int(p.dim)
    if hasattr(p, "basis"):
        return len(p.basis)
    return 0


def _candidate_vertex(p: object) -> int:
    """
    Resolve the canonical "vertex" attribute of a candidate.

    The spec talks about ``p.vertex`` (singular) which corresponds to the
    base-vertex ``v0`` in the project's Parallelotope dataclass.  Some
    legacy structures may name it ``vertex`` directly, so we accept both.
    """
    if hasattr(p, "v0"):
        return int(p.v0)
    if hasattr(p, "vertex"):
        return int(p.vertex)
    verts = _candidate_vertices(p)
    return int(min(verts)) if verts else 0


def _position_entropy(vertices: Sequence[int], n: int) -> float:
    """
    Average per-bit binary entropy across vertices in the block.

    For each of the n bit positions, compute the fraction p of vertices with
    that bit set, then take the Shannon entropy of (p, 1-p).  Average across
    bit positions and return a non-negative float in [0, 1].
    """
    if not vertices or n <= 0:
        return 0.0
    counts = np.zeros(n, dtype=np.int64)
    for v in vertices:
        for b in range(n):
            counts[b] += (int(v) >> b) & 1
    probs = counts.astype(np.float64) / float(len(vertices))
    h = 0.0
    for p in probs:
        if 0.0 < p < 1.0:
            h += -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))
    return float(h / n)


def _onset_offset_sets(bf: object) -> Tuple[set, set]:
    """Extract onset/offset as Python sets from a BooleanFunction-like object."""
    onset = set(int(x) for x in bf.onset)
    if hasattr(bf, "offset"):
        offset = set(int(x) for x in bf.offset)
    else:
        N = 1 << int(bf.n)
        offset = set(range(N)) - onset
    return onset, offset


def candidate_features(bf: object, candidates: Iterable[object]) -> np.ndarray:
    """
    Compute the per-candidate feature matrix.

    Parameters
    ----------
    bf : BooleanFunction-like
        Provides ``.n`` (qubit count) and ``.onset`` (iterable of int minterms).
    candidates : iterable of Parallelotope-like
        Each candidate must expose ``.v0`` (or ``.vertex``), ``.dim`` /
        ``.basis``, and ``.vertices()`` returning an iterable of ints.

    Returns
    -------
    np.ndarray
        Float64 array of shape ``(num_candidates, NUM_FEATURES)``.  Rows are
        in the same order as the input ``candidates`` iterable.
    """
    cand_list = list(candidates)
    if len(cand_list) == 0:
        return np.zeros((0, NUM_FEATURES), dtype=np.float64)

    n = int(bf.n)
    onset, offset = _onset_offset_sets(bf)

    # Pre-compute per-dim counts for structural_rarity.
    dim_counts: dict = {}
    cached_dims: List[int] = []
    for p in cand_list:
        d = _candidate_dim(p)
        cached_dims.append(d)
        dim_counts[d] = dim_counts.get(d, 0) + 1

    out = np.zeros((len(cand_list), NUM_FEATURES), dtype=np.float64)

    for row, p in enumerate(cand_list):
        dim = cached_dims[row]
        verts = _candidate_vertices(p)
        size = max(1, len(verts))  # singletons treated as size 1
        v0 = _candidate_vertex(p)
        pop_v0 = _popcount(v0)

        on_overlap = sum(1 for v in verts if int(v) in onset)
        off_overlap = sum(1 for v in verts if int(v) in offset)

        cnot_cost = 2 * max(0, dim - 1) + pop_v0 * 2
        t_cost = 4 * max(0, dim - 1)
        control_count = pop_v0 + dim
        is_singleton = 1.0 if dim == 0 else 0.0
        overlap_ratio = (on_overlap + off_overlap) / size
        on_ratio = on_overlap / size
        off_ratio = off_overlap / size
        pos_entropy = _position_entropy(verts, n)
        rarity = 1.0 / float(dim_counts.get(dim, 1))

        out[row, 0] = float(dim)
        out[row, 1] = float(size)
        out[row, 2] = float(dim)  # log2(size) == dim for parallelotopes
        out[row, 3] = float(on_overlap)
        out[row, 4] = float(off_overlap)
        out[row, 5] = float(on_ratio)
        out[row, 6] = float(cnot_cost)
        out[row, 7] = float(t_cost)
        out[row, 8] = float(control_count)
        out[row, 9] = float(is_singleton)
        out[row, 10] = float(overlap_ratio)
        out[row, 11] = float(off_ratio)
        out[row, 12] = float(pos_entropy)
        out[row, 13] = float(rarity)

    return out


# ---------------------------------------------------------------------------
# Smoke test / CLI
# ---------------------------------------------------------------------------

def _smoke_n3() -> None:
    """Run a tiny end-to-end sanity check on n=3."""
    # Local imports so the module remains importable even if sshr_core moves.
    from sshr_core.bool_func import BooleanFunction
    from sshr_core.parallelotope_enum import enumerate_parallelotopes

    bf = BooleanFunction.from_hex(3, "96")  # arbitrary 3-var function
    candidates = enumerate_parallelotopes(bf.onset, bf.n, include_singletons=True)
    feats = candidate_features(bf, candidates)
    print(f"n=3 onset={bf.onset}")
    print(f"#candidates={len(candidates)}, feature shape={feats.shape}")
    print(f"FEATURE_NAMES = {FEATURE_NAMES}")
    if feats.shape[0]:
        print(f"first row = {feats[0]}")
    assert feats.shape[1] == NUM_FEATURES == 14
    print("smoke OK")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Feature encoder smoke test for hand-crafted SSHR features."
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the n=3 smoke test (default action).",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    _smoke_n3()
