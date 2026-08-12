"""Equivariant policy/value components for Boolean-oracle synthesis.

The search state is a set of ANF monomials over ``n`` variables, encoded as a
``T x n`` binary matrix.  That matrix carries two independent symmetries:

* rows (terms) are a *set*, so the encoder must be permutation **invariant**
* columns (variables) can be relabelled, so the encoder must be permutation
  **equivariant** -- relabelling the inputs relabels the outputs

Both are handled by :mod:`src.foundation.equivariant`, whose layer parameter
counts do not depend on ``T`` or ``n``.  Whether a trained checkpoint
generalises across problem sizes remains an empirical question.
"""

from src.foundation.encoding import (
    CONTEXT_CHANNELS,
    STATE_CHANNELS,
    collate_states,
    encode_state,
    infer_num_vars,
    terms_to_matrix,
)
from src.foundation.equivariant import EquivariantTrunk, ExchangeableLayer

__all__ = [
    "CONTEXT_CHANNELS",
    "STATE_CHANNELS",
    "EquivariantTrunk",
    "ExchangeableLayer",
    "collate_states",
    "encode_state",
    "infer_num_vars",
    "terms_to_matrix",
]
