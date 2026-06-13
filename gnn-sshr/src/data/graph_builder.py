"""
Bipartite graph builder for SSHR candidate selection.

Constructs a heterogeneous bipartite graph with two node types:

* **Parity nodes** -- one per minterm in :math:`\\{0,1\\}^n`
  (``2**n`` total). Carry features describing the minterm's role in
  the current Boolean function (onset membership, Hamming weight,
  etc.).

* **Candidate nodes** -- one per :class:`Parallelotope` in the
  candidate pool. Carry features describing the block's geometric
  size and its overlap with the onset.

Two edge sets are produced:

* ``cover_edges`` -- bipartite edges connecting each parity to every
  candidate that covers it (i.e. the minterm is a vertex of that
  parallelotope).

* ``hypercube_edges`` -- intra-parity edges joining every pair of
  minterms at Hamming distance one (the Boolean hypercube graph).

The output is plain numpy; downstream code can wrap it into
torch_geometric ``HeteroData`` or any other GNN representation
without modification here.
"""
from __future__ import annotations

import argparse
import random
from typing import Any, List, Tuple

import numpy as np


PARITY_FEATURE_NAMES: Tuple[str, ...] = (
    "is_onset",
    "hamming_weight",
    "neighbor_onset_ratio",
    "cover_count",
    "n",
)

CANDIDATE_FEATURE_NAMES: Tuple[str, ...] = (
    "dim",
    "size",
    "log2_size",
    "on_overlap",
    "off_overlap",
    "on_ratio",
    "dim_density",
    "is_singleton",
    # --- Cost-aware features (appended; do not reorder the 8 above) ---
    "cnot_cost",
    "t_cost",
    "control_count",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _onset_mask(n: int, truth_table: int) -> np.ndarray:
    """Return an int8 array of length ``2**n`` with 1 on onset minterms."""
    N = 1 << n
    bits = np.zeros(N, dtype=np.int8)
    tt = int(truth_table)
    # Vectorised bit extraction: shift-then-AND in chunks would be fine
    # but a simple Python loop is O(2^n) which matches the budget.
    for k in range(N):
        bits[k] = (tt >> k) & 1
    return bits


def _hamming_weights(n: int) -> np.ndarray:
    """Hamming weight (popcount) of every integer in ``[0, 2**n)``."""
    N = 1 << n
    w = np.zeros(N, dtype=np.int32)
    for k in range(N):
        w[k] = bin(k).count("1")
    return w


def _hypercube_edges(n: int) -> np.ndarray:
    """All Hamming-distance-1 pairs ``(u, v)`` with ``u < v``.

    Returns
    -------
    np.ndarray
        Shape ``(2, n * 2**(n-1))``, dtype ``int64``. Row 0 are the
        smaller endpoints, row 1 the larger.
    """
    N = 1 << n
    if n == 0:
        return np.zeros((2, 0), dtype=np.int64)
    us: List[int] = []
    vs: List[int] = []
    for u in range(N):
        for b in range(n):
            v = u ^ (1 << b)
            if u < v:
                us.append(u)
                vs.append(v)
    return np.asarray([us, vs], dtype=np.int64)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_bipartite_graph(bf: Any, candidates: List[Any]) -> dict:
    """Build the bipartite parity/candidate graph for one SSHR instance.

    Parameters
    ----------
    bf : BooleanFunction
        Object exposing ``n`` (number of variables) and ``truth_table``
        (an integer bitmask of the onset; bit ``k`` set iff minterm
        ``k`` is in the onset).
    candidates : list of Parallelotope
        Each candidate must expose ``vertices()`` returning an iterable
        of minterm indices it covers, plus ``basis`` (list of basis
        vectors). ``vertex`` / ``v0`` is unused by the builder but
        documented for completeness.

    Returns
    -------
    dict
        Keys ``n``, ``num_parity``, ``num_candidates``,
        ``parity_features`` (float32, shape ``(2**n, 5)``),
        ``candidate_features`` (float32, shape
        ``(num_candidates, 11)``), ``cover_edges`` (int64, shape
        ``(2, E_cover)``) and ``hypercube_edges`` (int64, shape
        ``(2, E_hyp)``).
    """
    n = int(bf.n)
    N = 1 << n
    num_candidates = len(candidates)

    onset = _onset_mask(n, bf.truth_table)             # shape (N,)
    hweight = _hamming_weights(n).astype(np.float32)   # shape (N,)

    # Cover edges + per-candidate overlap accumulation in one pass.
    parity_indices: List[int] = []
    cand_indices: List[int] = []
    cover_count = np.zeros(N, dtype=np.int32)

    cand_dim = np.zeros(num_candidates, dtype=np.int32)
    cand_size = np.zeros(num_candidates, dtype=np.int32)
    cand_on_overlap = np.zeros(num_candidates, dtype=np.int32)
    cand_cnot = np.zeros(num_candidates, dtype=np.float32)
    cand_t = np.zeros(num_candidates, dtype=np.float32)
    cand_ctrl = np.zeros(num_candidates, dtype=np.float32)

    # Local import to keep module import light & avoid cycles.
    try:
        from sshr_core.block_synth import block_cnot_cost, block_t_cost
    except ImportError:  # pragma: no cover - alt layout
        from src.sshr_core.block_synth import (  # type: ignore
            block_cnot_cost,
            block_t_cost,
        )

    for j, p in enumerate(candidates):
        verts = list(p.vertices())
        size = len(verts)
        dim = len(p.basis)
        cand_dim[j] = dim
        cand_size[j] = size
        on_ov = 0
        for v in verts:
            parity_indices.append(int(v))
            cand_indices.append(j)
            cover_count[v] += 1
            on_ov += int(onset[v])
        cand_on_overlap[j] = on_ov
        # Cost-aware features (O(1) each, computed analytically).
        cand_cnot[j] = float(block_cnot_cost(p, n))
        cand_t[j] = float(block_t_cost(p, n))
        cand_ctrl[j] = float(int(p.v0).bit_count() + dim)

    if parity_indices:
        cover_edges = np.asarray([parity_indices, cand_indices], dtype=np.int64)
    else:
        cover_edges = np.zeros((2, 0), dtype=np.int64)

    # ------------------------------------------------------------------
    # Parity-side features
    # ------------------------------------------------------------------
    # neighbor_onset_ratio: fraction of n hypercube neighbours that lie
    # in the onset.
    neighbor_onset = np.zeros(N, dtype=np.float32)
    if n > 0:
        for k in range(N):
            cnt = 0
            for b in range(n):
                if onset[k ^ (1 << b)]:
                    cnt += 1
            neighbor_onset[k] = cnt / n

    parity_features = np.zeros((N, len(PARITY_FEATURE_NAMES)), dtype=np.float32)
    parity_features[:, 0] = onset.astype(np.float32)
    parity_features[:, 1] = hweight
    parity_features[:, 2] = neighbor_onset
    parity_features[:, 3] = cover_count.astype(np.float32)
    parity_features[:, 4] = float(n)

    # ------------------------------------------------------------------
    # Candidate-side features
    # ------------------------------------------------------------------
    cand_features = np.zeros(
        (num_candidates, len(CANDIDATE_FEATURE_NAMES)), dtype=np.float32
    )
    if num_candidates:
        size_f = cand_size.astype(np.float32)
        on_f = cand_on_overlap.astype(np.float32)
        off_f = size_f - on_f
        # log2(size) = dim for a parallelotope; compute defensively.
        with np.errstate(divide="ignore"):
            log2_size = np.log2(np.maximum(size_f, 1.0)).astype(np.float32)
        on_ratio = np.where(size_f > 0, on_f / size_f, 0.0).astype(np.float32)
        # 2**dim equals size for a parallelotope, but keep the formula
        # exactly as specified.
        denom = np.power(2.0, cand_dim.astype(np.float32))
        dim_density = np.where(denom > 0, on_f / denom, 0.0).astype(np.float32)
        is_singleton = (cand_dim == 0).astype(np.float32)

        cand_features[:, 0] = cand_dim.astype(np.float32)
        cand_features[:, 1] = size_f
        cand_features[:, 2] = log2_size
        cand_features[:, 3] = on_f
        cand_features[:, 4] = off_f
        cand_features[:, 5] = on_ratio
        cand_features[:, 6] = dim_density
        cand_features[:, 7] = is_singleton
        # Appended cost-aware features (must keep indices 8..10 to match
        # CANDIDATE_FEATURE_NAMES; older 8-dim checkpoints will surface a
        # clean shape error instead of silently misaligning).
        cand_features[:, 8] = cand_cnot
        cand_features[:, 9] = cand_t
        cand_features[:, 10] = cand_ctrl

    hypercube_edges = _hypercube_edges(n)

    return {
        "n": n,
        "num_parity": N,
        "num_candidates": num_candidates,
        "parity_features": parity_features,
        "candidate_features": cand_features,
        "cover_edges": cover_edges,
        "hypercube_edges": hypercube_edges,
    }


# ---------------------------------------------------------------------------
# Smoke test / CLI
# ---------------------------------------------------------------------------

def _smoke(n: int = 3, seed: int = 0) -> dict:
    """Build a graph for a random ``n``-variable onset and return it."""
    # Local imports so that bare module import has no heavy deps.
    try:
        from sshr_core.bool_func import BooleanFunction
        from sshr_core.parallelotope_enum import enumerate_parallelotopes
    except ImportError:  # pragma: no cover - fallback for alt layouts
        from src.sshr_core.bool_func import BooleanFunction  # type: ignore
        from src.sshr_core.parallelotope_enum import (  # type: ignore
            enumerate_parallelotopes,
        )

    rng = random.Random(seed)
    N = 1 << n
    tt = 0
    for k in range(N):
        if rng.random() < 0.5:
            tt |= 1 << k

    bf = BooleanFunction(n, tt)
    universe = list(range(1 << n))
    candidates = list(
        enumerate_parallelotopes(universe, n, include_singletons=True)
    )
    graph = build_bipartite_graph(bf, candidates)
    print(f"n={n}  truth_table=0x{tt:X}")
    print(f"num_parity         = {graph['num_parity']}")
    print(f"num_candidates     = {graph['num_candidates']}")
    print(f"parity_features    = {graph['parity_features'].shape}")
    print(f"candidate_features = {graph['candidate_features'].shape}")
    print(f"cover_edges        = {graph['cover_edges'].shape}")
    print(f"hypercube_edges    = {graph['hypercube_edges'].shape}")
    return graph


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=3, help="number of variables")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed")
    args = parser.parse_args()
    _smoke(n=args.n, seed=args.seed)


if __name__ == "__main__":
    _main()
