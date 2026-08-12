#!/usr/bin/env python3
"""Encode ANF term-set search states as ``T x n x C`` tensors.

A state is ``(terms, prefix_len, live_factor_ancilla)`` where ``terms`` is a
``frozenset[int]`` of monomials, each an integer bitmask over the ``n`` input
variables.  ``terms`` is turned into a binary membership matrix

    M[t, v] = 1  <=>  monomial ``t`` contains variable ``v``

and the scalar context (recursion depth, live ancilla, resource weights) is
broadcast across every cell as extra channels.  Broadcasting rather than
appending keeps the tensor a single ``T x n`` grid, which is what the
exchangeable layers in :mod:`src.foundation.equivariant` consume.

Feeding the resource weights in as *input* is deliberate: it lets one model
serve every weight profile (T-only, CNOT-only, ancilla-tight, ...) instead of
training a separate network per profile.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import torch

# Channel 0 is the monomial-membership indicator; the rest are broadcast
# context.  Keep this ordering stable -- checkpoints depend on it.
MEMBERSHIP_CHANNELS = 1
CONTEXT_CHANNELS = 8
# Size channels exist because the trunk cannot derive them.  Every pooling step
# in src.foundation.equivariant is a *mean*, which is exactly what makes one
# parameter set work at any T and n -- and exactly what erases how many
# monomials there are: duplicating every row leaves the network's output
# bit-identical.  The achievable-cost ratio depends strongly on that count, so
# it has to enter as an explicit scalar rather than be inferred.  Measured on
# 754 held-out states with a frozen trunk: adding these lifts value R^2 from
# 0.780 to 0.839 (MAE 0.0678 -> 0.0554), and they reach R^2 0.517 alone.
SIZE_CHANNELS = 3
STATE_CHANNELS = MEMBERSHIP_CHANNELS + CONTEXT_CHANNELS + SIZE_CHANNELS

# Divisors chosen so typical values land in roughly [0, 1]; exact scale does not
# matter because the trunk normalises, but keeping inputs O(1) helps early
# training.
_PREFIX_SCALE = 8.0
_LOG_TERMS_SCALE = 8.0
_VARS_SCALE = 16.0


def infer_num_vars(terms: Iterable[int]) -> int:
    """Smallest ``n`` that can represent every monomial in ``terms``.

    Callers that know the true variable count should pass it explicitly: a term
    set need not mention every variable of the function it came from, so
    inference can undercount.
    """
    return max((int(t).bit_length() for t in terms), default=0)


def sorted_terms(terms: Iterable[int]) -> list[int]:
    """Deterministic term order.

    The encoder is invariant to row order by construction, so this only exists
    to make tensors reproducible across runs.
    """
    return sorted(int(t) for t in terms)


def terms_to_matrix(
    terms: Iterable[int],
    num_vars: int,
    *,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Build the ``T x n`` binary membership matrix for ``terms``.

    Unpacked with a vectorised shift-and-mask rather than a per-cell loop: this
    runs once per value estimate inside the search, and at a few hundred
    monomials a Python double loop over individual tensor assignments dominates
    the forward pass it is feeding.
    """
    ordered = sorted_terms(terms)
    if not ordered:
        return torch.zeros((0, num_vars), device=device, dtype=dtype)

    # Monomials can exceed int64 at large n, so unpack through Python ints.
    bit_rows = [[(term >> var) & 1 for var in range(num_vars)] for term in ordered]
    return torch.tensor(bit_rows, device=device, dtype=dtype)


@dataclass(frozen=True)
class StateContext:
    """Scalar context broadcast across every cell of the membership matrix.

    The weight defaults are the *paper* profile that every ``scripts/run_*.py``
    passes explicitly (``cnot=0.04``, ``depth=0.015``), not the stale fallback
    still sitting on :class:`ResourceWeights`.  Those two disagree, so anything
    constructed from a bare ``SearchConfig()`` silently scores on a different
    objective than the published runs.  Prefer :meth:`from_config`, which reads
    the real weights off the config in play.
    """

    prefix_len: int = 0
    live_factor_ancilla: int = 0
    max_factor_ancilla: int = 4
    weight_t: float = 1.0
    weight_cnot: float = 0.04
    weight_depth: float = 0.015
    weight_gates: float = 0.01
    weight_ancilla: float = 2.0

    @classmethod
    def from_config(
        cls,
        config,
        prefix_len: int = 0,
        live_factor_ancilla: int = 0,
    ) -> "StateContext":
        """Read weights and the ancilla cap off a :class:`SearchConfig`."""
        weights = config.weights
        return cls(
            prefix_len=int(prefix_len),
            live_factor_ancilla=int(live_factor_ancilla),
            max_factor_ancilla=int(config.max_factor_ancilla),
            weight_t=float(weights.t),
            weight_cnot=float(weights.cnot),
            weight_depth=float(weights.depth),
            weight_gates=float(weights.gates),
            weight_ancilla=float(weights.ancilla),
        )

    def to_vector(self) -> list[float]:
        cap = max(int(self.max_factor_ancilla), 1)
        live = float(self.live_factor_ancilla)
        return [
            float(self.prefix_len) / _PREFIX_SCALE,
            live / cap,
            max(cap - live, 0.0) / cap,
            self.weight_t,
            self.weight_cnot,
            self.weight_depth,
            self.weight_gates,
            self.weight_ancilla,
        ]


def size_vector(n_terms: int, num_vars: int) -> list[float]:
    """The three scalars mean-pooling cannot recover: how big is this state.

    ``log1p`` for the count because achievable ratios vary with the *order of
    magnitude* of the term set, not its absolute size; ANF density because
    ``T / 2**n`` is the structural quantity that says how full the expansion is,
    and it is what makes a 60-monomial state at ``n=6`` a different problem from
    a 60-monomial state at ``n=12``.
    """
    density = float(n_terms) / float(1 << num_vars) if num_vars > 0 else 0.0
    return [
        math.log1p(n_terms) / _LOG_TERMS_SCALE,
        density,
        float(num_vars) / _VARS_SCALE,
    ]


def encode_state(
    terms: Iterable[int],
    num_vars: int,
    context: StateContext | None = None,
    *,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Encode one state as a ``T x n x STATE_CHANNELS`` tensor."""
    context = context or StateContext()
    membership = terms_to_matrix(terms, num_vars, device=device, dtype=dtype)
    n_terms = membership.shape[0]

    broadcast = context.to_vector() + size_vector(n_terms, num_vars)
    ctx = torch.tensor(broadcast, device=device, dtype=dtype)
    ctx = ctx.view(1, 1, len(broadcast)).expand(n_terms, num_vars, len(broadcast))
    return torch.cat([membership.unsqueeze(-1), ctx], dim=-1)


def collate_states(
    states: Sequence[torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Pad a batch of ``T_i x n_i x C`` tensors to a common shape.

    Returns ``(batch, term_mask, var_mask)`` where the masks are ``True`` on
    real entries.  Padding is never averaged over -- the trunk consumes the
    masks -- so a padded batch scores identically to the same states run one at
    a time.
    """
    if not states:
        raise ValueError("collate_states requires at least one state")

    channels = states[0].shape[-1]
    if any(s.shape[-1] != channels for s in states):
        raise ValueError("all states must share the channel dimension")

    max_terms = max(int(s.shape[0]) for s in states)
    max_vars = max(int(s.shape[1]) for s in states)
    device, dtype = states[0].device, states[0].dtype

    batch = torch.zeros((len(states), max_terms, max_vars, channels), device=device, dtype=dtype)
    term_mask = torch.zeros((len(states), max_terms), device=device, dtype=torch.bool)
    var_mask = torch.zeros((len(states), max_vars), device=device, dtype=torch.bool)

    for i, state in enumerate(states):
        n_terms, n_vars = int(state.shape[0]), int(state.shape[1])
        batch[i, :n_terms, :n_vars] = state
        term_mask[i, :n_terms] = True
        var_mask[i, :n_vars] = True

    return batch, term_mask, var_mask
