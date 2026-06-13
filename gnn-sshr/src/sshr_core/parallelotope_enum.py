"""
Enumerate all parallelotopes whose vertex set is a subset of `universe`.

Strategy (bottom-up BFS by dimension):
  dim=1: for each pair (v0, v1) in universe, alpha = v0^v1.
         P = Parallelotope(v0, [alpha]).
  dim=k: extend each (k-1)-dim parallelotope P with a new alpha_new such that:
           - alpha_new & combined_support(P.basis) == 0  (Lemma 1)
           - alpha_new != 0
           - all 2^k vertices of the extended parallelotope are in universe
         To avoid duplicates, enforce alpha_new > max(P.basis) in value.

Returns a list of Parallelotope objects, sorted descending by dimension.
"""
from __future__ import annotations
from typing import List, Set, FrozenSet
from .parallelotope import Parallelotope


def _all_subsets_xor(v0: int, basis: List[int]) -> FrozenSet[int]:
    """Compute all 2^k XOR-combinations of basis vectors added to v0."""
    verts = {v0}
    for alpha in basis:
        verts = verts | {v ^ alpha for v in verts}
    return frozenset(verts)


def enumerate_parallelotopes(
    universe: List[int],
    n: int,
    include_singletons: bool = False,
) -> List[Parallelotope]:
    """
    Enumerate all distinct parallelotopes of dimension >= 1 whose vertices
    are all in `universe`.

    include_singletons: if True, also return dim-0 (single vertex) entries
                        (used as fallback in SSHR-H).

    Returns list sorted by descending dimension (highest-dim first).
    """
    universe_set: Set[int] = set(universe)
    if not universe_set:
        return []

    # seen: set of frozensets of vertices (deduplication)
    seen: Set[FrozenSet[int]] = set()
    result_by_dim: List[List[Parallelotope]] = []

    # ---------- dim = 1 ----------
    dim1: List[Parallelotope] = []
    for v0 in universe_set:
        for v1 in universe_set:
            if v1 <= v0:
                continue
            alpha = v0 ^ v1
            if alpha == 0:
                continue
            p = Parallelotope(v0, [alpha])
            vset = p.vertices()
            if vset not in seen and vset <= universe_set:
                seen.add(vset)
                dim1.append(p)
    result_by_dim.append(dim1)

    # ---------- dim >= 2: extend previous dimension ----------
    prev_dim = dim1
    while prev_dim:
        next_dim: List[Parallelotope] = []
        for p in prev_dim:
            combined_support = 0
            for alpha in p.basis:
                combined_support |= alpha
            max_basis = max(p.basis)

            # Candidate new basis vectors: nonzero integers with disjoint support
            # and larger than max_basis (to avoid duplicate orderings)
            # We derive candidates from pairs of existing vertices of p plus
            # other universe elements.
            for v_extra in universe_set:
                # Try alpha_new = v_extra ^ v  for each vertex v of p
                for v in p.vertices():
                    alpha_new = v ^ v_extra
                    if alpha_new == 0:
                        continue
                    if alpha_new <= max_basis:
                        continue
                    if (alpha_new & combined_support) != 0:
                        continue
                    # Check all 2^(k+1) vertices are in universe
                    new_basis = p.basis + [alpha_new]
                    # Use base vertex v (which is a vertex of p, hence in universe)
                    # We need a canonical base vertex for the extended parallelotope.
                    # Use the minimum vertex of the new vertex set.
                    verts = _all_subsets_xor(p.v0, new_basis)
                    if not (verts <= universe_set):
                        continue
                    if verts in seen:
                        continue
                    seen.add(verts)
                    new_v0 = min(verts)
                    # Recompute basis relative to new_v0
                    # The basis vectors are still valid; just update v0
                    new_p = Parallelotope(new_v0, new_basis)
                    next_dim.append(new_p)
        if next_dim:
            result_by_dim.append(next_dim)
        prev_dim = next_dim

    # Flatten descending by dimension
    all_parallelotopes: List[Parallelotope] = []
    for dim_list in reversed(result_by_dim):
        all_parallelotopes.extend(dim_list)

    if include_singletons:
        for v in universe_set:
            all_parallelotopes.append(Parallelotope(v, []))

    return all_parallelotopes
