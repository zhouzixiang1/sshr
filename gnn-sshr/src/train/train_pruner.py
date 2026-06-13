"""Training loop for the HeteroGraphSAGE candidate pruner.

Reads a per-(function, candidate) CSV (see ``data_collector`` schema in
DESIGN.md §2.1), groups rows by ``func_id``, and for each function:

1. Reconstructs the :class:`BooleanFunction` from ``truth_table_hex`` / ``n``.
2. Enumerates parallelotope candidates (with singletons).
3. Builds the bipartite parity / candidate graph via
   :func:`data.graph_builder.build_bipartite_graph`.
4. Wraps the graph as a PyG :class:`HeteroData` object via
   :func:`models.candidate_pruner.dict_to_hetero`, attaching the per-candidate
   ``label`` vector (length ``m``, ordered by ``cand_idx``).

Training objective is::

    L = focal_bce(score, label, alpha=0.25, gamma=2)
        + 0.5 * pairwise_margin(score, label, per func_id)

Optimised with AdamW (lr=3e-4, weight_decay=1e-2), cosine schedule with a
linear 5-epoch warm-up, and gradient clipping (max_norm=1.0).

The script does **not** run training when this module is merely imported.
Use ``python -m train.train_pruner --csv ... --n 3 --out ...`` to launch.

CLI example::

    python -m train.train_pruner \\
        --csv data/ilp/n3_ilp_cnot.csv --n 3 \\
        --epochs 30 --hidden 128 --layers 3 \\
        --out results/models/gnn_pruner_n3.pt
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch import Tensor
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

# ---------------------------------------------------------------------------
# Project imports. Support both ``PYTHONPATH=src`` and src-as-package layouts.
# ---------------------------------------------------------------------------
try:  # ``PYTHONPATH=src`` style
    from data.graph_builder import build_bipartite_graph
    from models.candidate_pruner import CandidatePruner, dict_to_hetero
    from sshr_core.bool_func import BooleanFunction
    from sshr_core.parallelotope_enum import enumerate_parallelotopes
except ImportError:  # pragma: no cover - fallback for ``src.*`` style
    from src.data.graph_builder import build_bipartite_graph  # type: ignore
    from src.models.candidate_pruner import (  # type: ignore
        CandidatePruner,
        dict_to_hetero,
    )
    from src.sshr_core.bool_func import BooleanFunction  # type: ignore
    from src.sshr_core.parallelotope_enum import (  # type: ignore
        enumerate_parallelotopes,
    )

from torch_geometric.data import HeteroData  # noqa: E402
from torch_geometric.loader import DataLoader  # noqa: E402


# ---------------------------------------------------------------------------
# Dataset construction
# ---------------------------------------------------------------------------


@dataclass
class FuncSample:
    """One Boolean function rendered as a HeteroData graph + label vector."""

    func_id: int
    n: int
    data: HeteroData
    num_candidates: int


def _select_device() -> torch.device:
    """MPS if available, else CPU. CUDA is not part of the spec."""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _truth_table_from_hex(hex_str: str) -> int:
    return int(hex_str, 16)


def build_dataset(csv_path: Path, n_filter: Optional[int] = None) -> List[FuncSample]:
    """Group the CSV by ``func_id`` and build one HeteroData per function.

    Parameters
    ----------
    csv_path : Path
        Path to a per-row CSV produced by ``data_collector``.
    n_filter : int, optional
        If supplied, drop functions whose ``n`` does not match. Useful when
        a CSV mixes multiple variable counts.
    """
    df = pd.read_csv(csv_path)
    required = {"func_id", "n", "truth_table_hex", "cand_idx", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV {csv_path} is missing required columns: {sorted(missing)}"
        )

    if n_filter is not None:
        df = df[df["n"] == int(n_filter)].copy()

    samples: List[FuncSample] = []
    # Sort func_id ascending so train/val splits are reproducible.
    for func_id, sub in df.groupby("func_id", sort=True):
        sub = sub.sort_values("cand_idx").reset_index(drop=True)
        n = int(sub["n"].iloc[0])
        tt_hex = str(sub["truth_table_hex"].iloc[0])
        truth_table = _truth_table_from_hex(tt_hex)

        bf = BooleanFunction(n, truth_table)
        candidates = list(
            enumerate_parallelotopes(list(range(1 << n)), n, include_singletons=True)
        )
        # The CSV's cand_idx must be aligned with the enumeration order used
        # at collection time. We sanity-check the row count, not the
        # individual ordering, but the labels are placed by ``cand_idx``.
        m = len(candidates)
        if len(sub) != m:
            # Row count mismatch typically means the candidate enumeration
            # has drifted from data collection time; abort early so the user
            # regenerates the CSV.
            raise ValueError(
                f"func_id={func_id}: candidate count {m} != CSV rows {len(sub)}"
            )

        labels = np.zeros(m, dtype=np.float32)
        cand_idx = sub["cand_idx"].astype(int).to_numpy()
        lbl_vals = sub["label"].astype(int).to_numpy()
        if cand_idx.min() < 0 or cand_idx.max() >= m:
            raise ValueError(f"func_id={func_id}: cand_idx out of range")
        labels[cand_idx] = lbl_vals.astype(np.float32)

        graph = build_bipartite_graph(bf, candidates)
        data = dict_to_hetero(graph, label=labels)
        # Stash the func_id so we can stream it through the DataLoader.
        data["cand"].func_id = torch.full(
            (m,), int(func_id), dtype=torch.long
        )

        samples.append(
            FuncSample(func_id=int(func_id), n=n, data=data, num_candidates=m)
        )

    return samples


def split_train_val(
    samples: Sequence[FuncSample], val_frac: float = 0.2
) -> Tuple[List[FuncSample], List[FuncSample]]:
    """Last ``val_frac`` of func_ids (sorted ascending) become validation."""
    ordered = sorted(samples, key=lambda s: s.func_id)
    n_val = max(1, int(round(val_frac * len(ordered)))) if ordered else 0
    n_train = len(ordered) - n_val
    return list(ordered[:n_train]), list(ordered[n_train:])


# ---------------------------------------------------------------------------
# Losses
# ---------------------------------------------------------------------------


def focal_bce_with_logits(
    logits: Tensor,
    target: Tensor,
    alpha: float = 0.25,
    gamma: float = 2.0,
    eps: float = 1e-8,
) -> Tensor:
    """Focal binary cross-entropy on logits.

    Implementation follows Lin et al. (RetinaNet)::

        p   = sigmoid(z)
        p_t = p if y == 1 else 1 - p
        focal = -alpha * (1 - p_t) ** gamma * log(p_t)
    """
    p = torch.sigmoid(logits)
    p_t = torch.where(target > 0.5, p, 1.0 - p).clamp(min=eps, max=1.0 - eps)
    loss = -alpha * (1.0 - p_t).pow(gamma) * torch.log(p_t)
    return loss.mean()


def pairwise_margin_loss(
    scores: Tensor,
    target: Tensor,
    func_ids: Tensor,
    max_pairs_per_group: int = 256,
    generator: Optional[torch.Generator] = None,
) -> Tensor:
    """Softplus margin ranking loss applied within each ``func_id`` group.

    For every group with at least one positive and one negative candidate, we
    randomly sample up to ``max_pairs_per_group`` (positive, negative) pairs
    and return ``mean(softplus(neg_score - pos_score))`` averaged across
    groups. Returns ``0`` (with grad) if no valid pair exists, so the loss
    can always be summed into the total objective.
    """
    device = scores.device
    unique_ids = torch.unique(func_ids)
    losses: List[Tensor] = []
    for fid in unique_ids.tolist():
        mask = func_ids == fid
        pos_idx = torch.nonzero(mask & (target > 0.5), as_tuple=False).flatten()
        neg_idx = torch.nonzero(mask & (target <= 0.5), as_tuple=False).flatten()
        if pos_idx.numel() == 0 or neg_idx.numel() == 0:
            continue

        n_pairs = min(max_pairs_per_group, pos_idx.numel() * neg_idx.numel())
        # Sample with replacement; this matches LambdaRank-style heuristics
        # and avoids quadratic blow-ups.
        pi = torch.randint(
            0, pos_idx.numel(), (n_pairs,), device=device, generator=generator
        )
        ni = torch.randint(
            0, neg_idx.numel(), (n_pairs,), device=device, generator=generator
        )
        pos = scores[pos_idx[pi]]
        neg = scores[neg_idx[ni]]
        losses.append(F.softplus(neg - pos).mean())

    if not losses:
        return scores.new_zeros(())
    return torch.stack(losses).mean()


# ---------------------------------------------------------------------------
# Forward helpers (per-graph because the existing model uses global pooling)
# ---------------------------------------------------------------------------


def _forward_batch(
    model: CandidatePruner, batch: HeteroData, device: torch.device
) -> Tuple[Tensor, Tensor, Tensor]:
    """Run the model on each graph in the batch independently and concatenate.

    The reference :class:`CandidatePruner` pools parity nodes globally with a
    plain ``mean()``/``max()``. That is incorrect when several graphs are
    block-diagonally concatenated by PyG, so we materialise the data list
    and forward each entry separately. For tiny graphs (n<=4) this is still
    cheap.
    """
    data_list = batch.to_data_list()
    score_chunks: List[Tensor] = []
    label_chunks: List[Tensor] = []
    fid_chunks: List[Tensor] = []
    for d in data_list:
        d = d.to(device)
        score_chunks.append(model(d))
        label_chunks.append(d["cand"].y)
        fid_chunks.append(d["cand"].func_id)

    scores = torch.cat(score_chunks, dim=0)
    labels = torch.cat(label_chunks, dim=0)
    fids = torch.cat(fid_chunks, dim=0)
    return scores, labels, fids


def _compute_loss(
    scores: Tensor,
    labels: Tensor,
    fids: Tensor,
    pairwise_weight: float = 0.5,
) -> Tuple[Tensor, Dict[str, float]]:
    bce = focal_bce_with_logits(scores, labels)
    pair = pairwise_margin_loss(scores, labels, fids)
    total = bce + pairwise_weight * pair
    return total, {
        "loss": float(total.detach()),
        "loss_bce": float(bce.detach()),
        "loss_pair": float(pair.detach()),
    }


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------


def cosine_with_warmup(
    optimizer: AdamW, warmup_epochs: int, total_epochs: int
) -> LambdaLR:
    """Linear warm-up for ``warmup_epochs`` followed by cosine decay to zero."""

    def lr_lambda(epoch: int) -> float:
        if total_epochs <= 0:
            return 1.0
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(max(1, warmup_epochs))
        progress = (epoch - warmup_epochs) / max(1, total_epochs - warmup_epochs)
        progress = min(1.0, max(0.0, progress))
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    return LambdaLR(optimizer, lr_lambda=lr_lambda)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    if k >= scores.size:
        return np.argsort(-scores)
    # argpartition is O(m); we only need the top-k set.
    part = np.argpartition(-scores, k - 1)[:k]
    # Sort the top-k segment by score descending for deterministic ranking.
    return part[np.argsort(-scores[part])]


def recall_at_k(scores: np.ndarray, labels: np.ndarray, k: int) -> float:
    pos = int(labels.sum())
    if pos == 0:
        return float("nan")
    top = _topk_indices(scores, k)
    hits = int(labels[top].sum())
    return hits / pos


def ndcg_at_k(scores: np.ndarray, labels: np.ndarray, k: int) -> float:
    if labels.sum() == 0:
        return float("nan")
    order = np.argsort(-scores)
    gains = labels[order][:k].astype(np.float64)
    discounts = 1.0 / np.log2(np.arange(2, gains.size + 2))
    dcg = float((gains * discounts).sum())
    ideal_order = np.argsort(-labels)
    ideal_gains = labels[ideal_order][:k].astype(np.float64)
    idcg = float((ideal_gains * discounts).sum())
    if idcg <= 0.0:
        return float("nan")
    return dcg / idcg


def evaluate(
    model: CandidatePruner,
    loader: DataLoader,
    device: torch.device,
    keep_ratio: float = 0.10,
    pairwise_weight: float = 0.5,
) -> Dict[str, float]:
    """Run validation pass and return mean loss + ranking metrics."""
    model.eval()
    losses: List[float] = []
    per_func_scores: Dict[int, List[float]] = {}
    per_func_labels: Dict[int, List[int]] = {}

    with torch.no_grad():
        for batch in loader:
            scores, labels, fids = _forward_batch(model, batch, device)
            _, info = _compute_loss(scores, labels, fids, pairwise_weight)
            losses.append(info["loss"])

            scores_np = scores.detach().cpu().numpy()
            labels_np = labels.detach().cpu().numpy()
            fids_np = fids.detach().cpu().numpy()
            for s, l, f in zip(scores_np, labels_np, fids_np):
                per_func_scores.setdefault(int(f), []).append(float(s))
                per_func_labels.setdefault(int(f), []).append(int(l))

    recalls: List[float] = []
    ndcgs: List[float] = []
    for fid, slist in per_func_scores.items():
        s = np.asarray(slist, dtype=np.float32)
        y = np.asarray(per_func_labels[fid], dtype=np.float32)
        m = s.size
        k = max(1, math.ceil(keep_ratio * m))
        r = recall_at_k(s, y, k)
        nd = ndcg_at_k(s, y, k)
        if not math.isnan(r):
            recalls.append(r)
        if not math.isnan(nd):
            ndcgs.append(nd)

    return {
        "val_loss": float(np.mean(losses)) if losses else float("nan"),
        "val_recall_at_10pct": float(np.mean(recalls)) if recalls else float("nan"),
        "val_ndcg_at_10pct": float(np.mean(ndcgs)) if ndcgs else float("nan"),
    }


# ---------------------------------------------------------------------------
# Train loop
# ---------------------------------------------------------------------------


def train(args: argparse.Namespace) -> Dict[str, float]:
    csv_path = Path(args.csv).resolve()
    out_path = Path(args.out).resolve()
    log_path = Path(args.log) if args.log else _default_log_path(args.n)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    device = _select_device()
    print(f"[train_pruner] device={device}")

    samples = build_dataset(csv_path, n_filter=args.n)
    if not samples:
        raise RuntimeError(f"No usable samples found in {csv_path}")
    train_samples, val_samples = split_train_val(samples, val_frac=args.val_frac)
    print(
        f"[train_pruner] dataset: {len(samples)} funcs "
        f"(train={len(train_samples)}, val={len(val_samples)})"
    )

    train_loader = DataLoader(
        [s.data for s in train_samples],
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        [s.data for s in val_samples],
        batch_size=args.batch_size,
        shuffle=False,
    )

    model = CandidatePruner(
        hidden=args.hidden, num_layers=args.layers, dropout=args.dropout
    ).to(device)

    optimiser = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = cosine_with_warmup(
        optimiser, warmup_epochs=args.warmup_epochs, total_epochs=args.epochs
    )

    best_val = math.inf
    best_state: Optional[Dict[str, Tensor]] = None

    # Wipe the metrics jsonl so reruns don't append stale lines.
    if log_path.exists():
        log_path.unlink()

    for epoch in range(args.epochs):
        model.train()
        epoch_losses: List[float] = []
        for batch in train_loader:
            optimiser.zero_grad(set_to_none=True)
            scores, labels, fids = _forward_batch(model, batch, device)
            loss, info = _compute_loss(
                scores, labels, fids, pairwise_weight=args.pairwise_weight
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.clip_norm)
            optimiser.step()
            epoch_losses.append(info["loss"])

        scheduler.step()
        train_loss = float(np.mean(epoch_losses)) if epoch_losses else float("nan")

        val_metrics = evaluate(
            model,
            val_loader,
            device,
            keep_ratio=args.keep_ratio,
            pairwise_weight=args.pairwise_weight,
        )

        record = {
            "epoch": epoch,
            "lr": float(optimiser.param_groups[0]["lr"]),
            "train_loss": train_loss,
            **val_metrics,
        }
        with log_path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

        print(
            f"[epoch {epoch:3d}] train_loss={train_loss:.4f} "
            f"val_loss={val_metrics['val_loss']:.4f} "
            f"recall@10={val_metrics['val_recall_at_10pct']:.4f} "
            f"ndcg@10={val_metrics['val_ndcg_at_10pct']:.4f}"
        )

        if val_metrics["val_loss"] < best_val:
            best_val = val_metrics["val_loss"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            torch.save(
                {
                    "model_state": best_state,
                    "config": {
                        "hidden": args.hidden,
                        "layers": args.layers,
                        "dropout": args.dropout,
                        "n": args.n,
                        "parity_in_dim": 5,
                        "cand_in_dim": 11,
                    },
                    "val_loss": best_val,
                    "epoch": epoch,
                },
                out_path,
            )

    if best_state is None:
        # Save final model anyway so callers always find a checkpoint.
        torch.save(
            {
                "model_state": {
                    k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                },
                "config": {
                    "hidden": args.hidden,
                    "layers": args.layers,
                    "dropout": args.dropout,
                    "n": args.n,
                    "parity_in_dim": 5,
                    "cand_in_dim": 11,
                },
                "val_loss": best_val,
                "epoch": args.epochs - 1,
            },
            out_path,
        )

    print(f"[train_pruner] best val_loss={best_val:.4f}  ckpt={out_path}")
    return {"best_val_loss": best_val}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_log_path(n: int) -> Path:
    return Path("results/logs") / f"gnn_pruner_n{n}_metrics.jsonl"


def _default_out_path(n: int) -> Path:
    return Path("results/models") / f"gnn_pruner_n{n}.pt"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train the HeteroGraphSAGE candidate pruner.",
    )
    parser.add_argument(
        "--csv", type=str, required=True, help="Path to per-row training CSV."
    )
    parser.add_argument(
        "--n", type=int, required=True, help="Number of variables (filters CSV)."
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-2)
    parser.add_argument("--warmup-epochs", type=int, default=5)
    parser.add_argument("--clip-norm", type=float, default=1.0)
    parser.add_argument("--pairwise-weight", type=float, default=0.5)
    parser.add_argument("--keep-ratio", type=float, default=0.10)
    parser.add_argument("--val-frac", type=float, default=0.20)
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Checkpoint output path (default: results/models/gnn_pruner_n{n}.pt).",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Metrics jsonl path (default: results/logs/gnn_pruner_n{n}_metrics.jsonl).",
    )
    parser.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.out is None:
        args.out = str(_default_out_path(args.n))
    if args.log is None:
        args.log = str(_default_log_path(args.n))

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    train(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
