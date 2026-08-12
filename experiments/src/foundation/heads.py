#!/usr/bin/env python3
"""Downstream heads on the shared equivariant trunk.

Every head reads the same backbone, which is the point: the project currently
carries 18 separate per-regime checkpoints, and they exist only because the old
24-scalar feature vector could not transfer across problem shapes.  A shared
trunk plus thin heads is what lets one checkpoint cover them.

Implemented here:

* :class:`ActionScoringHead` -- ranks candidate :class:`FactorAction` objects,
  the drop-in replacement for the ``action_features`` MLP
* :class:`ValueHead` -- predicts a plan's achievable resource score, replacing
  the classical greedy rollout in the MCTS
"""
from __future__ import annotations

from typing import Sequence

import torch
from torch import nn


def _mlp(in_dim: int, hidden: int, out_dim: int, dropout: float = 0.0) -> nn.Sequential:
    layers: list[nn.Module] = [nn.Linear(in_dim, hidden), nn.GELU()]
    if dropout > 0:
        layers.append(nn.Dropout(dropout))
    layers.extend([nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, out_dim)])
    mlp = nn.Sequential(*layers)
    for module in mlp:
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)
    return mlp


def selection_matrix(
    index_lists: Sequence[Sequence[int]],
    size: int,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """Row-normalised ``K x size`` indicator matrix for a list of index sets.

    Row ``k`` holds ``1/|S_k|`` at every index in ``S_k``, so multiplying it by
    a feature matrix mean-pools each set in one shot.  Empty sets give a zero
    row, the right neutral element: an action touching no variables contributes
    no variable evidence.
    """
    matrix = torch.zeros((len(index_lists), size), device=device, dtype=dtype)
    for row, indices in enumerate(index_lists):
        if not indices:
            continue
        matrix[row, list(indices)] = 1.0 / len(indices)
    return matrix


def subset_pool(
    features: torch.Tensor,
    index_lists: Sequence[Sequence[int]],
) -> torch.Tensor:
    """Mean-pool ``features`` (``size x C``) over each index list.

    Expressed as a single matmul rather than a per-set ``index_select``: this
    runs once per candidate action per search node, and the loop version issued
    enough small kernel launches to dominate the model it was feeding.
    """
    matrix = selection_matrix(index_lists, features.shape[0], features.device, features.dtype)
    return matrix @ features


class ActionScoringHead(nn.Module):
    """Score candidate factorisation actions against an encoded state.

    An action is characterised by *which monomials it consumes* (``group``) and
    *which variables it factors out* (``factor``), so it is scored by pooling
    the trunk over exactly those rows and columns, alongside the global state
    summary and two cheap scalars the search already computed.
    """

    #: ``immediate_gain / direct_total``, ``|group| / |terms|``, then the two
    #: *absolute* sizes.  The ratios alone do not transfer across problem size:
    #: a 20-monomial group is 0.74 of an n=6 state and 0.08 of an n=9 one, so a
    #: head trained on the former reads the latter as a different kind of
    #: action.  ``subset_pool`` cannot supply the missing scale either -- it
    #: mean-pools the group's rows, the same size blindness that forced
    #: ``SIZE_CHANNELS`` on the trunk (see src.foundation.encoding).  Measured
    #: before this fix: the prior beat a random ranking by 2.04% at n<=8 but lost
    #: to it by 2.48% at n=9.
    NUM_SCALARS = 4

    #: Keeps log-sizes at O(1) for term sets up to a few thousand monomials.
    LOG_SIZE_SCALE = 8.0

    def __init__(self, hidden: int, mlp_hidden: int = 128, dropout: float = 0.0) -> None:
        super().__init__()
        self.hidden = hidden
        self.mlp = _mlp(3 * hidden + self.NUM_SCALARS, mlp_hidden, 1, dropout)

    def forward(
        self,
        term_features: torch.Tensor,
        var_features: torch.Tensor,
        global_features: torch.Tensor,
        group_rows: Sequence[Sequence[int]],
        factor_vars: Sequence[Sequence[int]],
        scalars: torch.Tensor,
    ) -> torch.Tensor:
        group_pool = subset_pool(term_features, group_rows)
        factor_pool = subset_pool(var_features, factor_vars)
        glob = global_features.unsqueeze(0).expand(group_pool.shape[0], -1)
        stacked = torch.cat([group_pool, factor_pool, glob, scalars], dim=-1)
        return self.mlp(stacked).squeeze(-1)


class ValueHead(nn.Module):
    """Predict ``log(achieved_score / direct_score)`` for a state.

    Regressing that ratio rather than the raw score gives a more scale-stable
    training target because scores span orders of magnitude with ``n`` while
    the ratio stays in roughly ``[-1.2, 0]``.  Cross-scale generalisation still
    requires held-out evaluation.  The output is clamped at zero because
    ``direct_plan`` is always feasible -- search can only improve on it, never
    do worse.
    """

    #: Most improvement ratios sit in ``[-1.2, 0]``; ``-3`` (a 20x gain over
    #: direct) is far outside anything observed and serves as a hard floor.
    MIN_LOG_RATIO = 3.0

    def __init__(self, hidden: int, mlp_hidden: int = 128, dropout: float = 0.0) -> None:
        super().__init__()
        self.mlp = _mlp(hidden, mlp_hidden, 1, dropout)

    def forward(self, global_features: torch.Tensor) -> torch.Tensor:
        raw = self.mlp(global_features).squeeze(-1)
        # Bound the output into (-MIN_LOG_RATIO, 0) smoothly.  A hard clamp
        # would zero the gradient outside the range; a scaled sigmoid keeps the
        # head trainable everywhere while still guaranteeing v < 0.
        return -self.MIN_LOG_RATIO * torch.sigmoid(raw)


class BooleanOracleModel(nn.Module):
    """Trunk plus the heads needed for search: action scoring and value."""

    def __init__(
        self,
        trunk,
        mlp_hidden: int = 128,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.trunk = trunk
        self.action_head = ActionScoringHead(trunk.hidden, mlp_hidden, dropout)
        self.value_head = ValueHead(trunk.hidden, mlp_hidden, dropout)

    def encode(
        self,
        state: torch.Tensor,
        term_mask: torch.Tensor | None = None,
        var_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Run the trunk and return ``(per-term, per-variable, global)``."""
        return self.trunk.pool(self.trunk(state, term_mask, var_mask), term_mask, var_mask)
