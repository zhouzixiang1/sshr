"""Output/input/term permutation-equivariant policy/value model for E6-MSO.

The scalar Boolean-oracle model acts on a ``term x input`` grid.  A vector
Boolean oracle has one additional exchangeable axis: output coordinates.  This
module therefore represents a :class:`~e6.shared_oracle.VectorANF` as an
``output x union-term x input`` tensor and uses the complete eight-path linear
map for the product group ``S_output x S_term x S_input``.  Every subset of the
three axes is either retained or mean-pooled, giving ``2**3`` equivariant
paths.

The action head reads pooled features for the action's target outputs,
polynomial terms and touched inputs.  Consequently a simultaneous relabelling
of the vector and the action only relabels the candidate list; its score is
unchanged.  The value head reads a global invariant.  This file defines the
architecture and checkpoint contract only: an untrained model is not AI4Q
performance evidence, and QAOA trajectories do not update it until the
separate replay contract is satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Mapping, Sequence

import torch
from torch import nn

from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    SharedAction,
    VectorANF,
    action_polynomial_terms,
    validate_shared_action,
)
from e6.shared_scheduler import (
    SharedUtilityWeights,
    shared_action_utility_breakdown,
)


SHARED_MODEL_SCHEMA = "xa.e6-shared-policy-value-model.v1"
STATE_CHANNEL_NAMES = (
    "variable_in_union_term",
    "term_present_in_output",
    "presence_times_membership",
    "real_union_term",
    "term_degree_fraction",
    "term_output_frequency",
    "output_term_density",
    "input_count_scaled",
    "output_count_scaled",
    "union_term_count_log_scaled",
    "weight_t",
    "weight_cnot",
    "weight_depth",
    "weight_gates",
    "weight_ancilla",
)
SHARED_STATE_CHANNELS = len(STATE_CHANNEL_NAMES)
ACTION_SCALAR_NAMES = (
    "fanout_fraction",
    "polynomial_term_fraction",
    "footprint_fraction",
    "mean_polynomial_degree_fraction",
    "max_polynomial_degree_fraction",
    "touched_input_fraction",
    "semi_affine_indicator",
    "explicit_ancilla_fraction",
    "log_direct_score_scaled",
    "log_shared_score_scaled",
    "relative_proxy_utility",
)
SHARED_ACTION_SCALARS = len(ACTION_SCALAR_NAMES)


@dataclass(frozen=True)
class SharedStateEncoding:
    """One unbatched ``output x term x input x channel`` model input."""

    tensor: torch.Tensor
    real_terms: tuple[int, ...]
    axis_terms: tuple[int, ...]
    input_count: int
    output_count: int

    def __post_init__(self) -> None:
        expected = (
            self.output_count,
            len(self.axis_terms),
            self.input_count,
            SHARED_STATE_CHANNELS,
        )
        if tuple(self.tensor.shape) != expected:
            raise ValueError(
                f"shared-state tensor shape {tuple(self.tensor.shape)} != {expected}"
            )
        if self.real_terms and self.axis_terms != self.real_terms:
            raise ValueError("non-empty encodings must use the real union-term axis")
        if not self.real_terms and self.axis_terms != (0,):
            raise ValueError("zero functions require one declared sentinel term cell")

    @property
    def term_index(self) -> dict[int, int]:
        return {term: index for index, term in enumerate(self.real_terms)}


def encode_vector_anf(
    vector: VectorANF,
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> SharedStateEncoding:
    """Encode a vector ANF without choosing a canonical output labelling."""

    real_terms = tuple(sorted(set().union(*vector.outputs)))
    axis_terms = real_terms or (0,)
    n = vector.input_count
    m = vector.output_count
    t_count = len(real_terms)
    values = torch.zeros(
        (m, len(axis_terms), n, SHARED_STATE_CHANNELS),
        device=device,
        dtype=dtype,
    )
    union_scale = math.log1p(t_count) / 8.0
    for output, output_terms in enumerate(vector.outputs):
        output_density = len(output_terms) / max(t_count, 1)
        for term_index, term in enumerate(axis_terms):
            real = bool(real_terms)
            presence = float(real and term in output_terms)
            degree = term.bit_count() if real else 0
            frequency = (
                sum(term in terms for terms in vector.outputs) / m if real else 0.0
            )
            for variable in range(n):
                membership = float(real and bool(term & (1 << variable)))
                values[output, term_index, variable] = torch.tensor(
                    (
                        membership,
                        presence,
                        membership * presence,
                        float(real),
                        degree / max(n, 1),
                        frequency,
                        output_density,
                        n / 16.0,
                        m / 16.0,
                        union_scale,
                        weights.t,
                        weights.cnot,
                        weights.depth,
                        weights.gates,
                        weights.ancilla,
                    ),
                    device=device,
                    dtype=dtype,
                )
    return SharedStateEncoding(values, real_terms, axis_terms, n, m)


def _cell_mask(
    x: torch.Tensor,
    output_mask: torch.Tensor | None,
    term_mask: torch.Tensor | None,
    input_mask: torch.Tensor | None,
) -> torch.Tensor:
    batch, outputs, terms, inputs = x.shape[:4]
    if output_mask is None:
        output_mask = torch.ones(
            (batch, outputs), device=x.device, dtype=torch.bool
        )
    if term_mask is None:
        term_mask = torch.ones((batch, terms), device=x.device, dtype=torch.bool)
    if input_mask is None:
        input_mask = torch.ones((batch, inputs), device=x.device, dtype=torch.bool)
    return (
        output_mask[:, :, None, None]
        & term_mask[:, None, :, None]
        & input_mask[:, None, None, :]
    )


_POOL_AXES = (
    (),
    (1,),
    (2,),
    (3,),
    (1, 2),
    (1, 3),
    (2, 3),
    (1, 2, 3),
)


def _broadcast_pool(
    x: torch.Tensor, cell: torch.Tensor, axes: tuple[int, ...]
) -> torch.Tensor:
    if not axes:
        return x
    mask = cell.unsqueeze(-1).to(x.dtype)
    return (x * mask).sum(dim=axes, keepdim=True) / mask.sum(
        dim=axes, keepdim=True
    ).clamp(min=1.0)


class TripleExchangeableLayer(nn.Module):
    """Complete linear map equivariant to independent permutations of 3 axes."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.in_channels = int(in_channels)
        self.out_channels = int(out_channels)
        self.paths = nn.ModuleList(
            [
                nn.Linear(in_channels, out_channels, bias=(index == 0))
                for index in range(len(_POOL_AXES))
            ]
        )
        for index, path in enumerate(self.paths):
            nn.init.xavier_uniform_(path.weight)
            if path.bias is not None:
                nn.init.zeros_(path.bias)
            if index:
                path.weight.data.mul_(0.1)

    def forward(
        self,
        x: torch.Tensor,
        output_mask: torch.Tensor | None = None,
        term_mask: torch.Tensor | None = None,
        input_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if x.dim() != 5:
            raise ValueError("TripleExchangeableLayer expects B x O x T x n x C")
        cell = _cell_mask(x, output_mask, term_mask, input_mask)
        out = sum(
            path(_broadcast_pool(x, cell, axes))
            for path, axes in zip(self.paths, _POOL_AXES)
        )
        return out * cell.unsqueeze(-1).to(out.dtype)


class TripleExchangeableBlock(nn.Module):
    def __init__(self, channels: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(channels)
        self.layer = TripleExchangeableLayer(channels, channels)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        output_mask: torch.Tensor | None = None,
        term_mask: torch.Tensor | None = None,
        input_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        update = self.layer(
            self.norm(x), output_mask, term_mask, input_mask
        )
        return x + self.dropout(self.activation(update))


class SharedEquivariantTrunk(nn.Module):
    """``B x O x T x n x C`` backbone for vector Boolean functions."""

    def __init__(
        self,
        in_channels: int = SHARED_STATE_CHANNELS,
        hidden: int = 64,
        layers: int = 3,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.in_channels = int(in_channels)
        self.hidden = int(hidden)
        self.input_proj = TripleExchangeableLayer(in_channels, hidden)
        self.blocks = nn.ModuleList(
            [TripleExchangeableBlock(hidden, dropout) for _ in range(layers)]
        )
        self.out_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x: torch.Tensor,
        output_mask: torch.Tensor | None = None,
        term_mask: torch.Tensor | None = None,
        input_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        squeeze = x.dim() == 4
        if squeeze:
            x = x.unsqueeze(0)
            output_mask = None if output_mask is None else output_mask.unsqueeze(0)
            term_mask = None if term_mask is None else term_mask.unsqueeze(0)
            input_mask = None if input_mask is None else input_mask.unsqueeze(0)
        if x.dim() != 5:
            raise ValueError("shared trunk expects O x T x n x C or batched input")
        hidden = self.input_proj(x, output_mask, term_mask, input_mask)
        for block in self.blocks:
            hidden = block(hidden, output_mask, term_mask, input_mask)
        hidden = self.out_norm(hidden)
        cell = _cell_mask(hidden, output_mask, term_mask, input_mask)
        hidden = hidden * cell.unsqueeze(-1).to(hidden.dtype)
        return hidden.squeeze(0) if squeeze else hidden

    def pool(
        self,
        hidden: torch.Tensor,
        output_mask: torch.Tensor | None = None,
        term_mask: torch.Tensor | None = None,
        input_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        squeeze = hidden.dim() == 4
        if squeeze:
            hidden = hidden.unsqueeze(0)
            output_mask = None if output_mask is None else output_mask.unsqueeze(0)
            term_mask = None if term_mask is None else term_mask.unsqueeze(0)
            input_mask = None if input_mask is None else input_mask.unsqueeze(0)
        cell = _cell_mask(hidden, output_mask, term_mask, input_mask)
        mask = cell.unsqueeze(-1).to(hidden.dtype)

        def pooled(axes: tuple[int, ...]) -> torch.Tensor:
            return (hidden * mask).sum(dim=axes) / mask.sum(dim=axes).clamp(min=1.0)

        output = pooled((2, 3))
        term = pooled((1, 3))
        variable = pooled((1, 2))
        global_features = pooled((1, 2, 3))
        if squeeze:
            return (
                output.squeeze(0),
                term.squeeze(0),
                variable.squeeze(0),
                global_features.squeeze(0),
            )
        return output, term, variable, global_features


def _selection_matrix(
    index_lists: Sequence[Sequence[int]],
    size: int,
    *,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    matrix = torch.zeros((len(index_lists), size), device=device, dtype=dtype)
    for row, indices in enumerate(index_lists):
        if indices:
            matrix[row, list(indices)] = 1.0 / len(indices)
    return matrix


def _subset_pool(
    features: torch.Tensor, index_lists: Sequence[Sequence[int]]
) -> torch.Tensor:
    return _selection_matrix(
        index_lists,
        features.shape[0],
        device=features.device,
        dtype=features.dtype,
    ) @ features


def shared_action_scalars(
    vector: VectorANF,
    action: SharedAction,
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> tuple[float, ...]:
    """Invariant structural/resource scalars used by the learned action head."""

    validate_shared_action(vector, action)
    terms = tuple(action_polynomial_terms(action))
    degrees = tuple(term.bit_count() for term in terms)
    touched_mask = 0
    for term in terms:
        touched_mask |= term
    if isinstance(action, SemiAffineSharedAction):
        touched_mask |= action.base_monomial | action.affine_mask
    breakdown = shared_action_utility_breakdown(action, weights=weights)
    union_count = len(set().union(*vector.outputs))
    footprint = len(action.targets) * len(terms)
    return (
        len(action.targets) / vector.output_count,
        len(terms) / max(union_count, 1),
        footprint / max(vector.output_count * union_count, 1),
        sum(degrees) / max(len(degrees) * vector.input_count, 1),
        max(degrees, default=0) / vector.input_count,
        touched_mask.bit_count() / vector.input_count,
        float(isinstance(action, SemiAffineSharedAction)),
        action.ancilla_required / 2.0,
        math.log1p(max(breakdown.direct_score, 0.0)) / 10.0,
        math.log1p(max(breakdown.shared_score, 0.0)) / 10.0,
        breakdown.utility / max(abs(breakdown.direct_score), 1.0),
    )


def _mlp(in_dim: int, hidden: int, out_dim: int, dropout: float) -> nn.Sequential:
    layers: list[nn.Module] = [nn.Linear(in_dim, hidden), nn.GELU()]
    if dropout > 0:
        layers.append(nn.Dropout(dropout))
    layers.extend((nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, out_dim)))
    result = nn.Sequential(*layers)
    for module in result:
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)
    return result


class SharedActionScoringHead(nn.Module):
    """Score shared actions from target-output, term and input subset features."""

    def __init__(
        self, hidden: int, mlp_hidden: int = 128, dropout: float = 0.0
    ) -> None:
        super().__init__()
        self.mlp = _mlp(4 * hidden + SHARED_ACTION_SCALARS, mlp_hidden, 1, dropout)

    def forward(
        self,
        output_features: torch.Tensor,
        term_features: torch.Tensor,
        input_features: torch.Tensor,
        global_features: torch.Tensor,
        target_outputs: Sequence[Sequence[int]],
        polynomial_terms: Sequence[Sequence[int]],
        touched_inputs: Sequence[Sequence[int]],
        scalars: torch.Tensor,
    ) -> torch.Tensor:
        target_pool = _subset_pool(output_features, target_outputs)
        term_pool = _subset_pool(term_features, polynomial_terms)
        input_pool = _subset_pool(input_features, touched_inputs)
        global_pool = global_features.unsqueeze(0).expand(len(target_outputs), -1)
        return self.mlp(
            torch.cat(
                (target_pool, term_pool, input_pool, global_pool, scalars), dim=-1
            )
        ).squeeze(-1)


class SharedValueHead(nn.Module):
    """Invariant prediction of ``log(shared_score / direct_score)``."""

    MIN_LOG_RATIO = 3.0

    def __init__(self, hidden: int, mlp_hidden: int = 128, dropout: float = 0.0) -> None:
        super().__init__()
        self.mlp = _mlp(hidden, mlp_hidden, 1, dropout)

    def forward(self, global_features: torch.Tensor) -> torch.Tensor:
        return -self.MIN_LOG_RATIO * torch.sigmoid(
            self.mlp(global_features).squeeze(-1)
        )


class SharedPolicyValueModel(nn.Module):
    """Three-axis equivariant trunk plus shared-action policy and value heads."""

    def __init__(
        self,
        trunk: SharedEquivariantTrunk,
        mlp_hidden: int = 128,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.trunk = trunk
        self.action_head = SharedActionScoringHead(
            trunk.hidden, mlp_hidden, dropout
        )
        self.value_head = SharedValueHead(trunk.hidden, mlp_hidden, dropout)

    def forward_one(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
        device: torch.device | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        encoding = encode_vector_anf(vector, weights=weights, device=device)
        hidden = self.trunk(encoding.tensor)
        output, term, variable, global_features = self.trunk.pool(hidden)
        term_index = encoding.term_index
        target_outputs: list[list[int]] = []
        polynomial_terms: list[list[int]] = []
        touched_inputs: list[list[int]] = []
        scalar_rows: list[tuple[float, ...]] = []
        for action in actions:
            validate_shared_action(vector, action)
            terms = sorted(action_polynomial_terms(action))
            missing = [item for item in terms if item not in term_index]
            if missing:
                raise ValueError(f"action terms absent from vector union: {missing}")
            touched_mask = 0
            for item in terms:
                touched_mask |= item
            if isinstance(action, SemiAffineSharedAction):
                touched_mask |= action.base_monomial | action.affine_mask
            target_outputs.append(list(action.targets))
            polynomial_terms.append([term_index[item] for item in terms])
            touched_inputs.append(
                [
                    index
                    for index in range(vector.input_count)
                    if touched_mask & (1 << index)
                ]
            )
            scalar_rows.append(shared_action_scalars(vector, action, weights=weights))
        if actions:
            scalars = torch.tensor(
                scalar_rows,
                dtype=encoding.tensor.dtype,
                device=encoding.tensor.device,
            )
            logits = self.action_head(
                output,
                term,
                variable,
                global_features,
                target_outputs,
                polynomial_terms,
                touched_inputs,
                scalars,
            )
        else:
            logits = torch.empty(
                (0,), dtype=encoding.tensor.dtype, device=encoding.tensor.device
            )
        value = self.value_head(global_features.unsqueeze(0))[0]
        return logits, value


class SharedPolicyValueScorer:
    """Inference/checkpoint adapter; training evidence is deliberately separate."""

    def __init__(
        self,
        model: SharedPolicyValueModel,
        device: torch.device | None = None,
    ) -> None:
        self.device = torch.device("cpu") if device is None else device
        self.model = model.to(self.device)
        self.model.eval()

    @classmethod
    def untrained(
        cls,
        *,
        hidden: int = 64,
        layers: int = 3,
        mlp_hidden: int = 128,
        seed: int = 0,
        device: torch.device | None = None,
    ) -> "SharedPolicyValueScorer":
        torch.manual_seed(seed)
        trunk = SharedEquivariantTrunk(hidden=hidden, layers=layers)
        return cls(SharedPolicyValueModel(trunk, mlp_hidden=mlp_hidden), device)

    @torch.no_grad()
    def score_actions(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> list[float]:
        logits, _ = self.model.forward_one(
            vector, actions, weights=weights, device=self.device
        )
        return [float(value) for value in logits]

    @torch.no_grad()
    def predict_log_ratio(
        self,
        vector: VectorANF,
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> float:
        _, value = self.model.forward_one(
            vector, (), weights=weights, device=self.device
        )
        return float(value)

    def save(
        self,
        path: str | Path,
        *,
        provenance: Mapping[str, object] | None = None,
    ) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        trunk = self.model.trunk
        torch.save(
            {
                "schema_version": SHARED_MODEL_SCHEMA,
                "state_channel_names": list(STATE_CHANNEL_NAMES),
                "action_scalar_names": list(ACTION_SCALAR_NAMES),
                "in_channels": trunk.in_channels,
                "hidden": trunk.hidden,
                "layers": len(trunk.blocks),
                "mlp_hidden": self.model.action_head.mlp[0].out_features,
                "state_dict": self.model.state_dict(),
                "provenance": dict(provenance or {}),
                "performance_evidence": False,
            },
            target,
        )

    @classmethod
    def from_checkpoint(
        cls,
        path: str | Path,
        *,
        device: torch.device | None = None,
    ) -> "SharedPolicyValueScorer":
        payload = torch.load(Path(path), map_location="cpu")
        if payload.get("schema_version") != SHARED_MODEL_SCHEMA:
            raise ValueError("unsupported E6 shared-model checkpoint schema")
        if payload.get("state_channel_names") != list(STATE_CHANNEL_NAMES):
            raise ValueError("E6 shared-model state channel contract changed")
        if payload.get("action_scalar_names") != list(ACTION_SCALAR_NAMES):
            raise ValueError("E6 shared-model action scalar contract changed")
        if int(payload.get("in_channels", -1)) != SHARED_STATE_CHANNELS:
            raise ValueError("E6 shared-model input width changed")
        trunk = SharedEquivariantTrunk(
            in_channels=SHARED_STATE_CHANNELS,
            hidden=int(payload["hidden"]),
            layers=int(payload["layers"]),
        )
        model = SharedPolicyValueModel(
            trunk, mlp_hidden=int(payload["mlp_hidden"])
        )
        model.load_state_dict(payload["state_dict"])
        return cls(model, device)


__all__ = [
    "ACTION_SCALAR_NAMES",
    "SHARED_ACTION_SCALARS",
    "SHARED_MODEL_SCHEMA",
    "SHARED_STATE_CHANNELS",
    "STATE_CHANNEL_NAMES",
    "SharedActionScoringHead",
    "SharedEquivariantTrunk",
    "SharedPolicyValueModel",
    "SharedPolicyValueScorer",
    "SharedStateEncoding",
    "SharedValueHead",
    "TripleExchangeableBlock",
    "TripleExchangeableLayer",
    "encode_vector_anf",
    "shared_action_scalars",
]
