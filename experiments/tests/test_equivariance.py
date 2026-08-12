#!/usr/bin/env python3
"""Symmetry tests for the foundation-model trunk.

These are the acceptance gate for L1.  The trunk claims three properties, and
every downstream story (one checkpoint replacing the per-regime models,
zero-shot transfer to unseen ``n``) depends on all three actually holding:

1. variable-permutation **equivariance** -- relabel the inputs, and the
   per-variable outputs come back relabelled the same way
2. term-permutation **invariance** -- monomials form a set, so row order is not
   allowed to matter
3. **size agnosticism** -- one parameter set applies to any ``T`` and ``n``

A fourth test checks that padded batches score identically to single states,
because the masking is easy to get subtly wrong and would silently corrupt
every batched training run.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch

from src.foundation.encoding import (
    SIZE_CHANNELS,
    StateContext,
    collate_states,
    encode_state,
    size_vector,
    terms_to_matrix,
)
from src.foundation.equivariant import EquivariantTrunk

TOL = 1e-4


def permute_term(term: int, perm: list[int]) -> int:
    """Relabel variables inside one monomial: bit ``v`` moves to ``perm[v]``."""
    out = 0
    for var, target in enumerate(perm):
        if term & (1 << var):
            out |= 1 << target
    return out


def random_terms(num_vars: int, count: int, rng: random.Random) -> list[int]:
    """Sample distinct non-constant monomials over ``num_vars`` variables."""
    seen: set[int] = set()
    while len(seen) < count:
        term = rng.randrange(1, 1 << num_vars)
        seen.add(term)
    return sorted(seen)


def build_trunk(seed: int = 0, hidden: int = 32, layers: int = 3) -> EquivariantTrunk:
    torch.manual_seed(seed)
    trunk = EquivariantTrunk(hidden=hidden, layers=layers)
    trunk.eval()
    return trunk


def test_variable_permutation_equivariance() -> None:
    """Relabelling variables must permute the per-variable outputs identically."""
    rng = random.Random(11)
    trunk = build_trunk()
    context = StateContext(prefix_len=2, live_factor_ancilla=1)

    for num_vars, count in ((6, 9), (10, 14)):
        terms = random_terms(num_vars, count, rng)
        perm = list(range(num_vars))
        rng.shuffle(perm)
        permuted = [permute_term(t, perm) for t in terms]

        with torch.no_grad():
            _, col, glob = trunk.pool(trunk(encode_state(terms, num_vars, context)))
            _, col_p, glob_p = trunk.pool(trunk(encode_state(permuted, num_vars, context)))

        # col_p[perm[v]] must equal col[v], i.e. indexing col_p by perm
        # recovers the original ordering.
        index = torch.tensor(perm, dtype=torch.long)
        assert torch.allclose(col_p[index], col, atol=TOL), (
            f"variable equivariance broken at n={num_vars}: "
            f"max delta {(col_p[index] - col).abs().max().item():.3e}"
        )
        # A permutation-invariant summary must be untouched.
        assert torch.allclose(glob_p, glob, atol=TOL), (
            f"global pooling is not permutation invariant at n={num_vars}"
        )


def test_term_permutation_invariance() -> None:
    """Monomials form a set, so row order must not change any summary."""
    rng = random.Random(23)
    trunk = build_trunk(seed=1)
    context = StateContext(prefix_len=1, live_factor_ancilla=0)

    num_vars, count = 8, 12
    terms = random_terms(num_vars, count, rng)
    state = encode_state(terms, num_vars, context)

    order = torch.randperm(state.shape[0])
    with torch.no_grad():
        row, col, glob = trunk.pool(trunk(state))
        row_s, col_s, glob_s = trunk.pool(trunk(state[order]))

    assert torch.allclose(col_s, col, atol=TOL), "per-variable output depends on row order"
    assert torch.allclose(glob_s, glob, atol=TOL), "global output depends on row order"
    # Per-term features are equivariant rather than invariant: they follow the
    # shuffle instead of ignoring it.
    assert torch.allclose(row_s, row[order], atol=TOL), "per-term output is not equivariant"


def test_size_agnostic() -> None:
    """One parameter set must accept any ``T`` and ``n`` without reshaping."""
    rng = random.Random(37)
    trunk = build_trunk(seed=2)
    context = StateContext()

    for num_vars in (4, 16, 40):
        for count in (1, 3, 25):
            count = min(count, (1 << num_vars) - 1)
            terms = random_terms(num_vars, count, rng)
            with torch.no_grad():
                out = trunk(encode_state(terms, num_vars, context))
            assert out.shape == (count, num_vars, trunk.hidden)
            assert torch.isfinite(out).all(), f"non-finite output at n={num_vars}, T={count}"


def test_padded_batch_matches_single() -> None:
    """Padding must be inert: a batch scores like its states run separately."""
    rng = random.Random(53)
    trunk = build_trunk(seed=3)
    context = StateContext(prefix_len=3, live_factor_ancilla=2)

    specs = [(5, 4), (9, 11), (7, 2)]
    states = [encode_state(random_terms(n, t, rng), n, context) for n, t in specs]

    with torch.no_grad():
        singles = [trunk.pool(trunk(s))[2] for s in states]
        batch, term_mask, var_mask = collate_states(states)
        _, _, batched = trunk.pool(trunk(batch, term_mask, var_mask), term_mask, var_mask)

    for i, expected in enumerate(singles):
        delta = (batched[i] - expected).abs().max().item()
        assert delta < TOL, f"padding leaked into state {i}: max delta {delta:.3e}"


def test_membership_matrix() -> None:
    """The encoder must place variable ``v`` of monomial ``t`` at cell (t, v)."""
    matrix = terms_to_matrix([0b0101, 0b1010], num_vars=4)
    expected = torch.tensor([[1.0, 0.0, 1.0, 0.0], [0.0, 1.0, 0.0, 1.0]])
    assert torch.equal(matrix, expected), f"membership encoding wrong:\n{matrix}"


def test_state_size_is_visible() -> None:
    """Term count must reach the network, because pooling cannot recover it.

    Every pool in the trunk is a *mean*, which is what makes one parameter set
    work at any shape -- and what makes the trunk exactly invariant to row
    multiplicity: duplicating every monomial leaves its output bit-identical.
    The achievable-cost ratio depends strongly on how many monomials there are,
    so the count enters as explicit broadcast channels instead.

    This guards a non-invariance.  The sibling tests above all assert that
    something must *not* change; this one asserts that something must.
    """
    trunk = build_trunk()
    rng = random.Random(11)
    terms = random_terms(6, 9, rng)
    state = encode_state(terms, 6, StateContext())

    # Hold the membership matrix and every other channel fixed, and vary only
    # the size channels.  Comparing states of *different* term counts would not
    # test this: their membership matrices differ too, so the output would move
    # even for a size-blind encoder.
    perturbed = state.clone()
    perturbed[..., -SIZE_CHANNELS:] = torch.tensor(size_vector(200, 6))

    _, _, base_glob = trunk.pool(trunk(state))
    _, _, moved_glob = trunk.pool(trunk(perturbed))
    delta = (base_glob - moved_glob).abs().max().item()
    assert delta > TOL, (
        "the size channels do not reach the trunk output -- they are being "
        f"dropped between encode_state and the network (max delta {delta:.3e})"
    )

    # A 60-monomial state at n=6 is a nearly full expansion; at n=12 it is
    # sparse.  Density is what separates them, so it must not collapse.
    dense, sparse = size_vector(60, 6), size_vector(60, 12)
    assert dense != sparse, "density channel does not distinguish n at fixed T"
    assert size_vector(3, 6) != size_vector(30, 6), "count channel is constant in T"


def main() -> int:
    test_membership_matrix()
    test_variable_permutation_equivariance()
    test_term_permutation_invariance()
    test_size_agnostic()
    test_state_size_is_visible()
    test_padded_batch_matches_single()
    print("equivariance ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
