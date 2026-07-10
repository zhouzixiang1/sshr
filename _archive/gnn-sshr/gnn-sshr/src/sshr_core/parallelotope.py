"""
Parallelotope in an n-dimensional Boolean hypercube.

A k-dimensional parallelotope is defined by:
  - a base vertex v0  (integer, bit-representation of {0,1}^n)
  - k basis vectors  alpha_1, ..., alpha_k  (integers in {0,1}^n)

Lemma 1 (paper): basis vectors must satisfy alpha_i & alpha_j == 0 for i != j
(disjoint support in the hypercube).

The 2^k vertices are all Minkowski-sum combinations:
  v0 XOR (subset of {alpha_1,...,alpha_k})
because XOR on {0,1}^n equals addition mod 2 and, given disjoint supports,
also equals ordinary integer addition restricted to {0,1}^n.
"""
from __future__ import annotations
from typing import List, FrozenSet


def support(v: int) -> int:
    """Return v itself (support mask = bit positions where v has 1)."""
    return v


def disjoint(a: int, b: int) -> bool:
    return (a & b) == 0


def is_valid_basis(basis: List[int]) -> bool:
    """Check Lemma 1: pairwise disjoint support."""
    for i in range(len(basis)):
        for j in range(i + 1, len(basis)):
            if not disjoint(basis[i], basis[j]):
                return False
    return True


class Parallelotope:
    """
    A k-dimensional parallelotope in an n-dimensional Boolean hypercube.

    v0     : base vertex (int)
    basis  : list of k basis vectors (ints), pairwise disjoint support
    """

    __slots__ = ("v0", "basis", "_vertices")

    def __init__(self, v0: int, basis: List[int]):
        self.v0 = v0
        self.basis = list(basis)
        self._vertices: FrozenSet[int] | None = None

    @property
    def dim(self) -> int:
        return len(self.basis)

    def vertices(self) -> FrozenSet[int]:
        if self._vertices is None:
            verts = {self.v0}
            for alpha in self.basis:
                verts = verts | {v ^ alpha for v in verts}
            self._vertices = frozenset(verts)
        return self._vertices

    def __len__(self) -> int:
        return 1 << len(self.basis)   # 2^k

    def __repr__(self):
        return (f"Parallelotope(v0={self.v0:b}, "
                f"basis={[f'{b:b}' for b in self.basis]}, "
                f"dim={self.dim})")

    # For deduplication: two parallelotopes are equal iff same vertex set
    def __eq__(self, other):
        if not isinstance(other, Parallelotope):
            return NotImplemented
        return self.vertices() == other.vertices()

    def __hash__(self):
        return hash(self.vertices())
