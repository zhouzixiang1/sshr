#!/usr/bin/env python3
"""Permutation-equivariant layers over ``T x n`` term-set matrices.

The state matrix has one symmetry per axis: monomials (rows) form a set, and
input variables (columns) may be relabelled.  A linear map that is equivariant
to both -- to the product group ``S_T x S_n`` -- has exactly four free weight
matrices per channel pair (Hartford et al., *Deep Models of Interactions Across
Sets*, ICML 2018):

    Y[t,v] = X[t,v] W1 + rowmean(X)[t] W2 + colmean(X)[v] W3 + mean(X) W4 + b

That parameterisation is complete: any ``S_T x S_n`` equivariant linear map can
be written this way.  Because the weights are indexed by *channel* and never by
term or variable index, the same parameters apply to any ``T`` and ``n`` -- the
property the whole cross-size transfer story rests on.
"""
from __future__ import annotations

import torch
from torch import nn

from src.foundation.encoding import STATE_CHANNELS


def _cell_mask(
    x: torch.Tensor,
    term_mask: torch.Tensor | None,
    var_mask: torch.Tensor | None,
) -> torch.Tensor:
    """Broadcast row/column masks into a ``B x T x n`` cell mask."""
    batch, n_terms, n_vars = x.shape[0], x.shape[1], x.shape[2]
    if term_mask is None:
        term_mask = torch.ones((batch, n_terms), device=x.device, dtype=torch.bool)
    if var_mask is None:
        var_mask = torch.ones((batch, n_vars), device=x.device, dtype=torch.bool)
    return term_mask.unsqueeze(-1) & var_mask.unsqueeze(1)


def masked_pool(
    x: torch.Tensor,
    term_mask: torch.Tensor | None = None,
    var_mask: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Row, column and global means that ignore padding.

    Returns ``(row, col, glob)`` shaped ``B x T x C``, ``B x n x C`` and
    ``B x C``.  Counts are clamped at 1 so an all-padding slice yields zeros
    rather than NaN.
    """
    cell = _cell_mask(x, term_mask, var_mask).unsqueeze(-1).to(x.dtype)
    masked = x * cell

    row = masked.sum(dim=2) / cell.sum(dim=2).clamp(min=1.0)
    col = masked.sum(dim=1) / cell.sum(dim=1).clamp(min=1.0)
    glob = masked.sum(dim=(1, 2)) / cell.sum(dim=(1, 2)).clamp(min=1.0)
    return row, col, glob


class ExchangeableLayer(nn.Module):
    """One ``S_T x S_n`` equivariant linear map plus bias."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.elem = nn.Linear(in_channels, out_channels, bias=True)
        self.row = nn.Linear(in_channels, out_channels, bias=False)
        self.col = nn.Linear(in_channels, out_channels, bias=False)
        self.glob = nn.Linear(in_channels, out_channels, bias=False)
        self._init_weights()

    def _init_weights(self) -> None:
        for module in (self.elem, self.row, self.col, self.glob):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        # The pooled terms start small so the layer begins close to a per-cell
        # map and learns to bring in context, which trains more stably than
        # having all four paths at equal scale.
        for module in (self.row, self.col, self.glob):
            module.weight.data.mul_(0.1)

    def forward(
        self,
        x: torch.Tensor,
        term_mask: torch.Tensor | None = None,
        var_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        row, col, glob = masked_pool(x, term_mask, var_mask)
        out = (
            self.elem(x)
            + self.row(row).unsqueeze(2)
            + self.col(col).unsqueeze(1)
            + self.glob(glob).unsqueeze(1).unsqueeze(1)
        )
        cell = _cell_mask(x, term_mask, var_mask).unsqueeze(-1).to(out.dtype)
        return out * cell


class ExchangeableBlock(nn.Module):
    """Pre-norm residual block wrapping one :class:`ExchangeableLayer`."""

    def __init__(self, channels: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(channels)
        self.layer = ExchangeableLayer(channels, channels)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        term_mask: torch.Tensor | None = None,
        var_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        h = self.layer(self.norm(x), term_mask, var_mask)
        return x + self.dropout(self.act(h))


class EquivariantTrunk(nn.Module):
    """Shared backbone: ``B x T x n x C_in`` -> ``B x T x n x hidden``.

    Every downstream head reads this same trunk, which is what lets one
    checkpoint replace the per-regime models the project accumulated.
    """

    def __init__(
        self,
        in_channels: int = STATE_CHANNELS,
        hidden: int = 128,
        layers: int = 6,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.hidden = hidden
        self.input_proj = ExchangeableLayer(in_channels, hidden)
        self.blocks = nn.ModuleList(
            [ExchangeableBlock(hidden, dropout=dropout) for _ in range(layers)]
        )
        self.out_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x: torch.Tensor,
        term_mask: torch.Tensor | None = None,
        var_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        squeeze_batch = x.dim() == 3
        if squeeze_batch:
            x = x.unsqueeze(0)
            if term_mask is not None and term_mask.dim() == 1:
                term_mask = term_mask.unsqueeze(0)
            if var_mask is not None and var_mask.dim() == 1:
                var_mask = var_mask.unsqueeze(0)

        h = self.input_proj(x, term_mask, var_mask)
        for block in self.blocks:
            h = block(h, term_mask, var_mask)
        h = self.out_norm(h)

        cell = _cell_mask(h, term_mask, var_mask).unsqueeze(-1).to(h.dtype)
        h = h * cell
        return h.squeeze(0) if squeeze_batch else h

    def pool(
        self,
        h: torch.Tensor,
        term_mask: torch.Tensor | None = None,
        var_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Per-term, per-variable and global summaries of a trunk output."""
        squeeze_batch = h.dim() == 3
        if squeeze_batch:
            h = h.unsqueeze(0)
            if term_mask is not None and term_mask.dim() == 1:
                term_mask = term_mask.unsqueeze(0)
            if var_mask is not None and var_mask.dim() == 1:
                var_mask = var_mask.unsqueeze(0)

        row, col, glob = masked_pool(h, term_mask, var_mask)
        if squeeze_batch:
            return row.squeeze(0), col.squeeze(0), glob.squeeze(0)
        return row, col, glob
