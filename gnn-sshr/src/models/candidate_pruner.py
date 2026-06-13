"""HeteroGraphSAGE candidate pruner for SSHR.

Implements the architecture described in DESIGN.md §6.1:

* Input projection of parity (5-dim) and candidate (11-dim) features
  to a common hidden width ``H``.
* ``L`` HeteroGraphSAGE layers, each performing three message-passing
  steps wrapped in :class:`torch_geometric.nn.HeteroConv`:

    * ``parity --covers--> cand``    (bipartite, updates candidate side)
    * ``cand   --covered--> parity`` (bipartite, updates parity side)
    * ``parity --adj--> parity``     (Boolean hypercube, updates parity side)

* Per-candidate scoring head: an MLP fed with
  ``[cand_h_j, mean(parity_h), max(parity_h)]`` returning a real score.

The :func:`dict_to_hetero` helper wraps the numpy dict produced by
:func:`src.data.graph_builder.build_bipartite_graph` into a PyG
:class:`HeteroData` object, duplicating the undirected hypercube edges
in both directions.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv


# ---------------------------------------------------------------------------
# Graph dict -> HeteroData
# ---------------------------------------------------------------------------

def dict_to_hetero(graph_dict: dict, label: Optional[np.ndarray] = None) -> HeteroData:
    """Wrap the numpy dict from ``build_bipartite_graph`` into ``HeteroData``.

    Parameters
    ----------
    graph_dict : dict
        Output of :func:`src.data.graph_builder.build_bipartite_graph`.
    label : np.ndarray, optional
        Per-candidate target (shape ``(m,)``). If provided, attached as
        ``data["cand"].y``.

    Returns
    -------
    HeteroData
        ``data["parity"].x``                          (2**n, 5) float32
        ``data["cand"].x``                            (m, 11)   float32
        ``data["cand"].y``  (optional)                (m,)
        ``data["parity","covers","cand"].edge_index`` (2, E_cover)
        ``data["cand","covered","parity"].edge_index``(2, E_cover)
        ``data["parity","adj","parity"].edge_index``  (2, 2*E_hyp) -- bidir
    """
    data = HeteroData()

    parity_x = torch.from_numpy(np.ascontiguousarray(graph_dict["parity_features"]))
    cand_x = torch.from_numpy(np.ascontiguousarray(graph_dict["candidate_features"]))
    data["parity"].x = parity_x.float()
    data["cand"].x = cand_x.float()

    if label is not None:
        y = torch.from_numpy(np.ascontiguousarray(label)).float().view(-1)
        data["cand"].y = y

    cover = torch.from_numpy(np.ascontiguousarray(graph_dict["cover_edges"])).long()
    # Bipartite: ("parity","covers","cand") -- row 0 parity, row 1 cand.
    data["parity", "covers", "cand"].edge_index = cover
    # Reverse direction for messages from cand back to parity.
    data["cand", "covered", "parity"].edge_index = cover.flip(0)

    hyp = torch.from_numpy(np.ascontiguousarray(graph_dict["hypercube_edges"])).long()
    if hyp.numel() > 0:
        # hypercube_edges is stored with u<v only; duplicate as both
        # directions so message passing is symmetric.
        rev = hyp.flip(0)
        adj = torch.cat([hyp, rev], dim=1)
    else:
        adj = torch.zeros((2, 0), dtype=torch.long)
    data["parity", "adj", "parity"].edge_index = adj

    return data


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class CandidatePruner(nn.Module):
    """HeteroGraphSAGE candidate scorer.

    Parameters
    ----------
    parity_in_dim : int
        Number of parity-node input features (default 5).
    cand_in_dim : int
        Number of candidate-node input features (default 11: the eight
        original structural features plus three cost-aware features —
        cnot_cost, t_cost, control_count).
    hidden : int
        Hidden width used throughout the body and head.
    num_layers : int
        Number of stacked HeteroGraphSAGE blocks.
    dropout : float
        Dropout applied to candidate hidden states inside the scoring
        head.
    """

    def __init__(
        self,
        parity_in_dim: int = 5,
        cand_in_dim: int = 11,
        hidden: int = 128,
        num_layers: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()

        self.hidden = hidden
        self.num_layers = num_layers
        self.dropout = dropout

        self.parity_in = nn.Linear(parity_in_dim, hidden)
        self.cand_in = nn.Linear(cand_in_dim, hidden)

        self.convs = nn.ModuleList()
        self.parity_norms = nn.ModuleList()
        self.cand_norms = nn.ModuleList()
        for _ in range(num_layers):
            conv = HeteroConv(
                {
                    ("parity", "covers", "cand"): SAGEConv(
                        (hidden, hidden), hidden
                    ),
                    ("cand", "covered", "parity"): SAGEConv(
                        (hidden, hidden), hidden
                    ),
                    ("parity", "adj", "parity"): SAGEConv(
                        (hidden, hidden), hidden
                    ),
                },
                aggr="sum",
            )
            self.convs.append(conv)
            self.parity_norms.append(nn.LayerNorm(hidden))
            self.cand_norms.append(nn.LayerNorm(hidden))

        # Scoring head: [cand_h, mean(parity_h), max(parity_h)] -> R
        self.score_mlp = nn.Sequential(
            nn.Linear(3 * hidden, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, data: HeteroData) -> torch.Tensor:
        parity_h = self.parity_in(data["parity"].x)
        cand_h = self.cand_in(data["cand"].x)

        edge_index_dict = {
            ("parity", "covers", "cand"): data[
                "parity", "covers", "cand"
            ].edge_index,
            ("cand", "covered", "parity"): data[
                "cand", "covered", "parity"
            ].edge_index,
            ("parity", "adj", "parity"): data[
                "parity", "adj", "parity"
            ].edge_index,
        }

        for conv, p_norm, c_norm in zip(
            self.convs, self.parity_norms, self.cand_norms
        ):
            x_dict = {"parity": parity_h, "cand": cand_h}
            out = conv(x_dict, edge_index_dict)

            new_cand = out.get("cand", cand_h)
            new_parity = out.get("parity", parity_h)

            new_cand = c_norm(F.relu(new_cand))
            new_parity = p_norm(F.relu(new_parity))

            cand_h = new_cand
            parity_h = new_parity

        # Global parity pooling (single graph -- batch processing would
        # need a parity batch index; here we handle the m=1 graph case).
        parity_mean = parity_h.mean(dim=0, keepdim=True).expand(
            cand_h.size(0), -1
        )
        parity_max = parity_h.max(dim=0, keepdim=True).values.expand(
            cand_h.size(0), -1
        )

        feat = torch.cat([cand_h, parity_mean, parity_max], dim=-1)
        scores = self.score_mlp(feat).squeeze(-1)
        return scores


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def _smoke() -> None:
    # Local imports so the module is import-light.
    try:
        from data.graph_builder import build_bipartite_graph
        from sshr_core.bool_func import BooleanFunction
        from sshr_core.parallelotope_enum import enumerate_parallelotopes
    except ImportError:  # pragma: no cover - fallback layout
        from src.data.graph_builder import build_bipartite_graph  # type: ignore
        from src.sshr_core.bool_func import BooleanFunction  # type: ignore
        from src.sshr_core.parallelotope_enum import (  # type: ignore
            enumerate_parallelotopes,
        )

    n = 3
    tt = 0x05
    bf = BooleanFunction(n, tt)
    universe = list(range(1 << n))
    candidates = list(
        enumerate_parallelotopes(universe, n, include_singletons=True)
    )
    graph = build_bipartite_graph(bf, candidates)
    data = dict_to_hetero(graph)

    model = CandidatePruner()
    model.eval()
    with torch.no_grad():
        scores = model(data)
    print(f"scores shape: {scores.shape} dtype: {scores.dtype}")


if __name__ == "__main__":
    _smoke()
