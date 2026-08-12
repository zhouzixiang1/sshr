#!/usr/bin/env python3
"""Development-only E6 shared head on the frozen formal-v4 foundation trunk.

The formal-v4 checkpoint supplies one scalar Boolean-oracle ``S_T x S_n``
equivariant trunk.  This module calls that frozen trunk exactly once on the
union of every output's ANF terms.  All output coordinates then share the same
``union-term x input`` coordinate system.  An output-by-union-term incidence
matrix produces output features, while a new thin action head pools target
outputs, shared term features and shared input features.

The supported symmetry is intentionally narrow: output-coordinate
permutations, input-variable permutations and candidate-list reorderings.
``S_T`` means invariance to the row ordering of a term *set*; it does not make
arbitrary monomial identities interchangeable. This base model does not embed
training or replay; the separate isolated trainer and sealed-head contracts
must revalidate their own external roots. No real replay run, formal evaluation
or performance assessment is implied by this architecture.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import io
import math
from pathlib import Path
from typing import Iterator, Mapping, Sequence
import weakref

import torch
from torch import nn
import torch.nn.functional as torch_functional
import torch.nn.modules.module as nn_module

from e6.shared_model import SHARED_ACTION_SCALARS, shared_action_scalars
from e6.shared_model import TripleExchangeableBlock, TripleExchangeableLayer
from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    SharedAction,
    VectorANF,
    action_polynomial_terms,
    validate_shared_action,
)
from e6.shared_scheduler import SharedUtilityWeights
from src.foundation.encoding import STATE_CHANNELS, StateContext, encode_state
import src.foundation.equivariant as foundation_equivariant
from src.foundation.equivariant import (
    EquivariantTrunk,
    ExchangeableBlock,
    ExchangeableLayer,
)
from src.foundation.heads import BooleanOracleModel


FROZEN_SHARED_HEAD_SCHEMA = "xa.e6-frozen-foundation-v4-shared-head.v2-development"
FORMAL_V4_CHECKPOINT_SHA256 = (
    "5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7"
)
FORMAL_V4_PROVENANCE_SCHEMA = "xa.foundation-checkpoint-provenance.v4"
FORMAL_V4_HIDDEN = 32
FORMAL_V4_LAYERS = 2
FORMAL_V4_SEED = 20260904
FORMAL_V4_MAX_FACTOR_ANCILLA = 4
FORMAL_V4_MLP_HIDDEN = 128
_MAX_FORMAL_V4_CHECKPOINT_BYTES = 16 * 1024 * 1024
FORMAL_V4_CANARY_OUTPUT_SHA256 = (
    "3dde070b83bd325dcd9fdfe98facc09e85813444e6b75170b2c9d843b6d1192c"
)

_FORMAL_V4_TOP_LEVEL_KEYS = frozenset(
    {"state_dict", "in_channels", "hidden", "layers", "mlp_hidden", "provenance"}
)
_FORMAL_V4_PROVENANCE = {
    "schema_version": FORMAL_V4_PROVENANCE_SCHEMA,
    "profile": "formal",
    "seed": FORMAL_V4_SEED,
    "initialization": "seeded_random_from_scratch",
    "parent_checkpoint": None,
    "v3_weights_loaded": False,
    "config_sha256": "45b6f8094b2866a6dcaa51e5f7975761ff315352c349058a1d984ebfb921af92",
    "source_manifest_sha256": "1ba583be4575a057fd30de5dc08addd910873d10f8c8a72e5fa2610e593b2b29",
    "dataset_manifest_sha256": "415025ad4d62497e1a347bce4cff2388a700de5aa53a96911b9f25c11e32a5f8",
    "command_sha256": "cc70c9fa2cb5a9a174281872bb0495caa149695dc8ad11eeaaf8573f35fc63b8",
    "training_log_sha256": "a78616164c09018f8889e9cb51a99596615bcaf94b31fecae91cf6b1c83f30ae",
}

DEFAULT_FORMAL_V4_CHECKPOINT = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "xa202609"
    / "20260812-foundation-v4-provenance-formal-s20260904"
    / "checkpoint.pt"
)

SYMMETRY_CONTRACT = (
    "output-coordinate permutations, input-variable permutations and candidate "
    "ordering only; not arbitrary term identities"
)
CLAIM_BOUNDARY = (
    "The formal-v4 foundation finished its provenance training, but has no "
    "performance status. A newly constructed E6-v2 head is initialized only "
    "and contains no embedded trainer. Separate audited trainer and sealed-head "
    "contracts exist, but no real replay training run, formal evaluation or "
    "performance evidence is implied. Modified heads must use the separate "
    "externally anchored sealed schema, never this initialized-only loader."
)
THREAT_MODEL = (
    "Fail closed on foundation hooks, instance/class execution overrides and "
    "replacement of known functional operators or equivariant helpers. Public "
    "vector, action and utility-weight inputs are copied from exact immutable "
    "active dataclasses before foundation integrity checks. Formal verification "
    "requires a fresh CPU-only process with no custom imports. Arbitrary hostile "
    "interpreter mutation and concurrent monkeypatch races are out of scope."
)

VALUE_SCALAR_NAMES = (
    "input_count_scaled",
    "output_count_scaled",
    "union_term_count_log_scaled",
    "anf_cell_density",
    "repeated_term_appearance_fraction",
)
_PINNED_STATE_KEYS = (
    "_pinned_checkpoint_sha256",
    "_pinned_foundation_tensor_sha256",
    "_pinned_foundation_parameter_count",
)
_FOUNDATION_HOOK_ATTRIBUTES = (
    "_forward_hooks",
    "_forward_pre_hooks",
    "_backward_hooks",
    "_backward_pre_hooks",
    "_state_dict_hooks",
    "_state_dict_pre_hooks",
    "_load_state_dict_pre_hooks",
    "_load_state_dict_post_hooks",
)
_GLOBAL_EXECUTION_HOOK_ATTRIBUTES = (
    "_global_forward_hooks",
    "_global_forward_pre_hooks",
    "_global_backward_hooks",
    "_global_backward_pre_hooks",
)
_PINNED_FUNCTIONAL_OPERATORS = {
    "linear": torch_functional.linear,
    "layer_norm": torch_functional.layer_norm,
    "gelu": torch_functional.gelu,
}
_PINNED_FOUNDATION_HELPERS = {
    "_cell_mask": foundation_equivariant._cell_mask,
    "masked_pool": foundation_equivariant.masked_pool,
}
_PINNED_FOUNDATION_CLASS_FORWARDS = {
    EquivariantTrunk: EquivariantTrunk.forward,
    ExchangeableLayer: ExchangeableLayer.forward,
    ExchangeableBlock: ExchangeableBlock.forward,
    nn.Linear: nn.Linear.forward,
    nn.LayerNorm: nn.LayerNorm.forward,
    nn.GELU: nn.GELU.forward,
    nn.Identity: nn.Identity.forward,
}


@dataclass(frozen=True)
class FormalV4TrunkIdentity:
    """Verified identity carried by one loaded formal-v4 trunk."""

    checkpoint_path: str
    checkpoint_sha256: str
    tensor_sha256: str
    parameter_count: int
    provenance_schema: str
    profile: str
    seed: int
    in_channels: int
    hidden: int
    layers: int
    initialization: str
    foundation_training_completed: bool = True
    foundation_performance: bool = False


@dataclass(frozen=True)
class FrozenSharedHeadInputsV2:
    """Joint-adapter output and final-head inputs after one trunk call."""

    joint_hidden: torch.Tensor
    policy_features: torch.Tensor
    value_features: torch.Tensor
    policy_relation_residual: torch.Tensor
    value_relation_residual: torch.Tensor

    def joint_representation(self) -> torch.Tensor:
        """Flatten the joint cell representation before policy/value pooling."""

        return self.joint_hidden.reshape(-1)


@dataclass(frozen=True)
class _FrozenJointFeatures:
    joint_hidden: torch.Tensor
    joint_global: torch.Tensor
    term_rows: Mapping[int, int]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fp32_module_tensor_sha256(module: nn.Module) -> str:
    """Hash exact names, shapes, dtypes and FP32 bytes of a module state."""

    digest = hashlib.sha256()
    for name, raw_tensor in sorted(module.state_dict().items()):
        if not isinstance(raw_tensor, torch.Tensor):
            raise RuntimeError(f"foundation state {name!r} is not a tensor")
        tensor = raw_tensor.detach().cpu().contiguous()
        if tensor.dtype != torch.float32:
            raise RuntimeError(
                f"foundation state {name!r} must remain FP32, got {tensor.dtype}"
            )
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _named_fp32_tensor_sha256(tensors: Mapping[str, torch.Tensor]) -> str:
    """Hash one exact FP32 named-tensor mapping without changing its device."""

    digest = hashlib.sha256()
    for name, raw_tensor in sorted(tensors.items()):
        if not isinstance(raw_tensor, torch.Tensor):
            raise RuntimeError(f"head state {name!r} is not a tensor")
        tensor = raw_tensor.detach().cpu().contiguous()
        if tensor.dtype != torch.float32:
            raise RuntimeError(f"head state {name!r} must remain FP32")
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _tensor_sha256(tensor: torch.Tensor) -> str:
    value = tensor.detach().cpu().contiguous()
    digest = hashlib.sha256()
    digest.update(str(tuple(value.shape)).encode("ascii"))
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _foundation_canary_input(device: torch.device) -> torch.Tensor:
    """Fixed input whose formal-v4 CPU output digest is source-pinned."""

    return (
        torch.arange(3 * 4 * STATE_CHANNELS, device=device, dtype=torch.float32)
        .remainder(17)
        .div(16.0)
        .reshape(3, 4, STATE_CHANNELS)
    )


def _assert_pinned_execution_globals() -> None:
    """Reject known execution-path replacement before foundation evaluation."""

    for name, pinned in _PINNED_FUNCTIONAL_OPERATORS.items():
        if getattr(torch_functional, name) is not pinned:
            raise RuntimeError(
                f"known foundation functional operator changed: {name}"
            )
    for name, pinned in _PINNED_FOUNDATION_HELPERS.items():
        if getattr(foundation_equivariant, name) is not pinned:
            raise RuntimeError(f"known foundation equivariant helper changed: {name}")
    for module_type, pinned in _PINNED_FOUNDATION_CLASS_FORWARDS.items():
        if module_type.forward is not pinned:
            raise RuntimeError(
                "known foundation class forward changed: "
                f"{module_type.__module__}.{module_type.__qualname__}"
            )


@lru_cache(maxsize=1)
def _formal_v4_state_schema() -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Return the exact named FP32 tensor schema of the pinned v4 model."""

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(0)
        expected_model = BooleanOracleModel(
            EquivariantTrunk(
                in_channels=STATE_CHANNELS,
                hidden=FORMAL_V4_HIDDEN,
                layers=FORMAL_V4_LAYERS,
            ),
            mlp_hidden=FORMAL_V4_MLP_HIDDEN,
        )
    return tuple(
        (name, tuple(tensor.shape))
        for name, tensor in expected_model.state_dict().items()
    )


def _validate_formal_v4_payload_schema(payload: object) -> dict[str, object]:
    """Reject every non-native, extra or type-coerced checkpoint field."""

    if type(payload) is not dict:
        raise ValueError("formal-v4 checkpoint payload must be a native dict")
    if any(type(key) is not str for key in payload):
        raise ValueError("formal-v4 checkpoint keys must be native strings")
    if set(payload) != _FORMAL_V4_TOP_LEVEL_KEYS:
        raise ValueError("formal-v4 checkpoint top-level key set mismatch")

    architecture = {
        "in_channels": STATE_CHANNELS,
        "hidden": FORMAL_V4_HIDDEN,
        "layers": FORMAL_V4_LAYERS,
        "mlp_hidden": FORMAL_V4_MLP_HIDDEN,
    }
    for key, expected in architecture.items():
        value = payload[key]
        if type(value) is not int:
            raise ValueError(f"formal-v4 checkpoint {key} must be a native int")
        if value != expected:
            raise ValueError(
                f"formal-v4 checkpoint {key} mismatch: "
                f"expected {expected}, got {value!r}"
            )

    provenance = payload["provenance"]
    if type(provenance) is not dict:
        raise ValueError("formal-v4 checkpoint provenance must be a native dict")
    if any(type(key) is not str for key in provenance):
        raise ValueError("formal-v4 checkpoint provenance keys must be native strings")
    if set(provenance) != set(_FORMAL_V4_PROVENANCE):
        raise ValueError("formal-v4 checkpoint provenance key set mismatch")
    for key, expected in _FORMAL_V4_PROVENANCE.items():
        value = provenance[key]
        if type(value) is not type(expected):
            raise ValueError(
                f"formal-v4 checkpoint provenance {key} type mismatch"
            )
        if value != expected:
            raise ValueError(
                f"formal-v4 checkpoint provenance {key} mismatch: "
                f"expected {expected!r}, got {value!r}"
            )

    state_dict = payload["state_dict"]
    if type(state_dict) is not OrderedDict:
        raise ValueError("formal-v4 checkpoint state_dict must be an OrderedDict")
    if any(type(key) is not str for key in state_dict):
        raise ValueError("formal-v4 checkpoint state keys must be native strings")
    expected_state = _formal_v4_state_schema()
    if tuple(state_dict) != tuple(name for name, _ in expected_state):
        raise ValueError("formal-v4 checkpoint state key/order contract mismatch")
    for name, expected_shape in expected_state:
        tensor = state_dict[name]
        if type(tensor) is not torch.Tensor:
            raise ValueError(f"formal-v4 checkpoint state {name!r} must be a Tensor")
        if (
            tensor.device.type != "cpu"
            or tensor.layout != torch.strided
            or tensor.dtype != torch.float32
            or tuple(tensor.shape) != expected_shape
            or tensor.requires_grad
        ):
            raise ValueError(
                f"formal-v4 checkpoint state {name!r} tensor contract mismatch"
            )
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"formal-v4 checkpoint state {name!r} is non-finite")
    return payload


def _validated_checkpoint_payload(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_file():
        raise FileNotFoundError(f"formal-v4 checkpoint does not exist: {path}")
    with path.open("rb") as handle:
        checkpoint_bytes = handle.read(_MAX_FORMAL_V4_CHECKPOINT_BYTES + 1)
    if len(checkpoint_bytes) > _MAX_FORMAL_V4_CHECKPOINT_BYTES:
        raise ValueError("formal-v4 checkpoint exceeds the bounded loader size")
    digest = hashlib.sha256(checkpoint_bytes).hexdigest()
    if digest != FORMAL_V4_CHECKPOINT_SHA256:
        raise ValueError(
            "formal-v4 checkpoint SHA-256 mismatch: "
            f"expected {FORMAL_V4_CHECKPOINT_SHA256}, got {digest}"
        )

    payload = torch.load(
        io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True
    )
    return _validate_formal_v4_payload_schema(payload), digest


def load_frozen_foundation_v4_trunk(
    checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
) -> tuple[EquivariantTrunk, FormalV4TrunkIdentity]:
    """Verify, strictly load and freeze only the formal-v4 trunk."""

    _assert_pinned_execution_globals()
    path = Path(checkpoint_path).expanduser().resolve()
    payload, checkpoint_digest = _validated_checkpoint_payload(path)
    state_dict = payload.get("state_dict")
    if not isinstance(state_dict, Mapping):
        raise ValueError("formal-v4 checkpoint state_dict is missing")

    trunk = EquivariantTrunk(
        in_channels=STATE_CHANNELS,
        hidden=FORMAL_V4_HIDDEN,
        layers=FORMAL_V4_LAYERS,
    )
    trunk_state = {
        str(name)[len("trunk.") :]: tensor
        for name, tensor in state_dict.items()
        if str(name).startswith("trunk.")
    }
    expected_keys = set(trunk.state_dict())
    actual_keys = set(trunk_state)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        raise ValueError(
            "formal-v4 trunk state contract mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )
    trunk.load_state_dict(trunk_state, strict=True)
    trunk.requires_grad_(False)
    trunk.eval()

    provenance = payload["provenance"]
    assert isinstance(provenance, Mapping)
    identity = FormalV4TrunkIdentity(
        checkpoint_path=str(path),
        checkpoint_sha256=checkpoint_digest,
        tensor_sha256=_fp32_module_tensor_sha256(trunk),
        parameter_count=sum(parameter.numel() for parameter in trunk.parameters()),
        provenance_schema=str(provenance["schema_version"]),
        profile=str(provenance["profile"]),
        seed=int(provenance["seed"]),
        in_channels=int(payload["in_channels"]),
        hidden=int(payload["hidden"]),
        layers=int(payload["layers"]),
        initialization=str(provenance["initialization"]),
    )
    return trunk, identity


def _thin_mlp(in_features: int, hidden: int) -> nn.Sequential:
    result = nn.Sequential(
        nn.Linear(in_features, hidden),
        nn.GELU(),
        nn.Linear(hidden, 1),
    )
    for module in result:
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            nn.init.zeros_(module.bias)
    return result


class FrozenJointEquivariantAdapterV2(nn.Module):
    """Thin trainable ``S_output x S_term x S_input`` joint-cell adapter."""

    def __init__(
        self,
        foundation_hidden: int,
        joint_hidden: int,
        *,
        blocks: int = 1,
    ) -> None:
        super().__init__()
        self.in_features = 2 * foundation_hidden + 1
        self.hidden = joint_hidden
        self.input_proj = TripleExchangeableLayer(self.in_features, joint_hidden)
        self.blocks = nn.ModuleList(
            [TripleExchangeableBlock(joint_hidden) for _ in range(blocks)]
        )
        self.out_norm = nn.LayerNorm(joint_hidden)

    def forward(self, cells: torch.Tensor) -> torch.Tensor:
        if cells.dim() != 4 or cells.shape[-1] != self.in_features:
            raise ValueError("joint cells violate the frozen E6-v2 contract")
        hidden = self.input_proj(cells.unsqueeze(0))
        for block in self.blocks:
            hidden = block(hidden)
        return self.out_norm(hidden).squeeze(0)


class FrozenSharedActionPolicyHeadV2(nn.Module):
    """Thin action head over already pooled, symmetry-safe features."""

    def __init__(self, joint_hidden: int, head_hidden: int) -> None:
        super().__init__()
        self.in_features = 5 * joint_hidden + SHARED_ACTION_SCALARS
        self.mlp = _thin_mlp(self.in_features, head_hidden)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if features.dim() != 2 or features.shape[-1] != self.in_features:
            raise ValueError("policy features violate the frozen E6-v2 contract")
        return self.mlp(features).squeeze(-1)


class FrozenSharedValueHeadV2(nn.Module):
    """Thin invariant value head for a vector Boolean-oracle state."""

    MIN_LOG_RATIO = 3.0

    def __init__(self, joint_hidden: int, head_hidden: int) -> None:
        super().__init__()
        self.in_features = joint_hidden + len(VALUE_SCALAR_NAMES)
        self.mlp = _thin_mlp(self.in_features, head_hidden)

    def forward(
        self, features: torch.Tensor, relation_residual: torch.Tensor
    ) -> torch.Tensor:
        if features.dim() != 1 or features.shape[-1] != self.in_features:
            raise ValueError("value features violate the frozen E6-v2 contract")
        if relation_residual.dim() != 0:
            raise ValueError("value relation residual must be scalar")
        return -self.MIN_LOG_RATIO * torch.sigmoid(
            self.mlp(features.unsqueeze(0)).squeeze() + relation_residual
        )


def _state_context(weights: SharedUtilityWeights) -> StateContext:
    return StateContext(
        prefix_len=0,
        live_factor_ancilla=0,
        max_factor_ancilla=FORMAL_V4_MAX_FACTOR_ANCILLA,
        weight_t=float(weights.t),
        weight_cnot=float(weights.cnot),
        weight_depth=float(weights.depth),
        weight_gates=float(weights.gates),
        weight_ancilla=float(weights.ancilla),
    )


def _canonicalize_public_inputs(
    vector: VectorANF,
    actions: Sequence[SharedAction],
    weights: SharedUtilityWeights,
) -> tuple[VectorANF, tuple[SharedAction, ...], SharedUtilityWeights]:
    """Copy exact frozen public inputs before any foundation integrity check.

    Rejecting subclasses and duck-typed objects before reading their attributes
    closes the caller-triggered hook window: no user-defined property can run
    between the integrity scan and the real frozen-trunk execution.  Rebuilding
    each active dataclass also reruns its finite/domain validation and leaves the
    sealed execution path with objects independent of the caller's instances.
    """

    if type(weights) is not SharedUtilityWeights:
        raise TypeError("weights must be exact SharedUtilityWeights")
    if type(vector) is not VectorANF:
        raise TypeError("vector must be exact VectorANF")

    canonical_weights = SharedUtilityWeights(
        t=weights.t,
        cnot=weights.cnot,
        depth=weights.depth,
        gates=weights.gates,
        ancilla=weights.ancilla,
    )
    canonical_vector = VectorANF(vector.input_count, vector.outputs)

    canonical_actions: list[SharedAction] = []
    for action in tuple(actions):
        if type(action) is MonomialSharedAction:
            canonical_actions.append(
                MonomialSharedAction(action.monomial, action.targets)
            )
        elif type(action) is SemiAffineSharedAction:
            canonical_actions.append(
                SemiAffineSharedAction(
                    action.base_monomial,
                    action.affine_mask,
                    action.affine_const,
                    action.targets,
                )
            )
        else:
            raise TypeError(
                "actions must contain exact MonomialSharedAction or "
                "SemiAffineSharedAction instances"
            )
    return canonical_vector, tuple(canonical_actions), canonical_weights


def _touched_input_indices(
    vector: VectorANF, action: SharedAction
) -> tuple[int, ...]:
    touched_mask = 0
    for term in action_polynomial_terms(action):
        touched_mask |= term
    if isinstance(action, SemiAffineSharedAction):
        touched_mask |= action.base_monomial | action.affine_mask
    return tuple(
        index
        for index in range(vector.input_count)
        if touched_mask & (1 << index)
    )


def _value_scalars(
    vector: VectorANF,
    *,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    union_terms = set().union(*vector.outputs)
    appearances = sum(len(output) for output in vector.outputs)
    repeated = sum(
        max(sum(term in output for output in vector.outputs) - 1, 0)
        for term in union_terms
    )
    values = (
        vector.input_count / 16.0,
        vector.output_count / 16.0,
        math.log1p(len(union_terms)) / 8.0,
        appearances / max(vector.output_count * (1 << vector.input_count), 1),
        repeated / max(appearances, 1),
    )
    return torch.tensor(values, device=device, dtype=dtype)


class FrozenFoundationV4SharedPolicyValueV2(nn.Module):
    """Immutable formal-v4 trunk plus new output/input-equivariant thin heads."""

    schema_version = FROZEN_SHARED_HEAD_SCHEMA
    symmetry_contract = SYMMETRY_CONTRACT
    claim_boundary = CLAIM_BOUNDARY
    foundation_training_completed = True
    foundation_performance = False
    head_formal_evaluation = False
    head_performance = False
    active_trainer_connected = False

    _PROTECTED_FOUNDATION_ATTRIBUTES = {
        "foundation_trunk",
        "_foundation_trunk",
        "foundation_identity",
        "_foundation_identity",
    }

    def __setattr__(self, name: str, value: object) -> None:
        if (
            name in self._PROTECTED_FOUNDATION_ATTRIBUTES
            and "_foundation_object_id" in self.__dict__
        ):
            raise AttributeError("the pinned formal-v4 foundation cannot be replaced")
        super().__setattr__(name, value)

    def __init__(
        self,
        checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
        *,
        head_hidden: int = 32,
        head_seed: int = 20260907,
    ) -> None:
        super().__init__()
        if isinstance(head_hidden, bool) or not isinstance(head_hidden, int):
            raise TypeError("head_hidden must be an integer")
        if head_hidden <= 0:
            raise ValueError("head_hidden must be positive")
        if isinstance(head_seed, bool) or not isinstance(head_seed, int):
            raise TypeError("head_seed must be an integer")

        trunk, identity = load_frozen_foundation_v4_trunk(checkpoint_path)
        # Bypass nn.Module.__setattr__: the immutable foundation must not enter
        # this E6 module's trainable parameter tree or serialised state_dict.
        object.__setattr__(self, "_foundation_trunk", trunk)
        object.__setattr__(self, "_foundation_identity", identity)
        self._foundation_object_id = id(trunk)
        self._foundation_state_keys = tuple(sorted(trunk.state_dict()))
        self._foundation_module_signature = tuple(
            (name, type(module)) for name, module in trunk.named_modules()
        )
        self.head_hidden = head_hidden
        self.joint_hidden = min(head_hidden, 12)
        self.head_seed = head_seed
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(head_seed)
            self.joint_adapter = FrozenJointEquivariantAdapterV2(
                identity.hidden, self.joint_hidden
            )
            self.policy_head = FrozenSharedActionPolicyHeadV2(
                self.joint_hidden, head_hidden
            )
            self.value_head = FrozenSharedValueHeadV2(
                self.joint_hidden, head_hidden
            )
        self.register_buffer(
            "_pinned_checkpoint_sha256",
            torch.tensor(list(bytes.fromhex(identity.checkpoint_sha256)), dtype=torch.uint8),
            persistent=True,
        )
        self.register_buffer(
            "_pinned_foundation_tensor_sha256",
            torch.tensor(list(bytes.fromhex(identity.tensor_sha256)), dtype=torch.uint8),
            persistent=True,
        )
        self.register_buffer(
            "_pinned_foundation_parameter_count",
            torch.tensor(identity.parameter_count, dtype=torch.int64),
            persistent=True,
        )
        self._initial_head_tensor_sha256 = self.current_head_tensor_sha256()
        self._serialized_state_keys = tuple(sorted(super().state_dict()))
        self._foundation_task_forward_count = 0
        self.register_load_state_dict_post_hook(self._post_load_integrity_hook)
        self.assert_foundation_integrity()

    @property
    def foundation_trunk(self) -> EquivariantTrunk:
        return object.__getattribute__(self, "_foundation_trunk")

    @property
    def foundation_identity(self) -> FormalV4TrunkIdentity:
        return object.__getattribute__(self, "_foundation_identity")

    @property
    def foundation_task_forward_count(self) -> int:
        """Diagnostic count excluding integrity-canary evaluations."""

        return int(self._foundation_task_forward_count)

    def _head_state_tensors(self) -> dict[str, torch.Tensor]:
        tensors: dict[str, torch.Tensor] = {}
        for prefix, module in (
            ("joint_adapter", self.joint_adapter),
            ("policy_head", self.policy_head),
            ("value_head", self.value_head),
        ):
            for name, tensor in module.state_dict().items():
                tensors[f"{prefix}.{name}"] = tensor
        return tensors

    def current_head_tensor_sha256(self) -> str:
        """Return the exact current digest of every new trainable head tensor."""

        return _named_fp32_tensor_sha256(self._head_state_tensors())

    @property
    def head_training_status(self) -> str:
        return (
            "initialized"
            if self.current_head_tensor_sha256()
            == self._initial_head_tensor_sha256
            else "modified_unsealed"
        )

    @staticmethod
    def _digest_buffer_hex(buffer: torch.Tensor) -> str:
        return bytes(int(item) for item in buffer.detach().cpu().tolist()).hex()

    def assert_foundation_integrity(self) -> str:
        """Fail closed unless structure, bytes and freeze state remain pinned."""

        trunk = self.foundation_trunk
        identity = self.foundation_identity
        if id(trunk) != self._foundation_object_id:
            raise RuntimeError("formal-v4 foundation object identity changed")
        if type(trunk) is not EquivariantTrunk:
            raise RuntimeError("formal-v4 foundation trunk type changed")
        _assert_pinned_execution_globals()
        for attribute in _GLOBAL_EXECUTION_HOOK_ATTRIBUTES:
            hooks = getattr(nn_module, attribute, None)
            if hooks:
                raise RuntimeError(
                    f"global execution hooks can alter foundation behavior: {attribute}"
                )
        current_modules = tuple(
            (name, type(module)) for name, module in trunk.named_modules()
        )
        if current_modules != self._foundation_module_signature:
            raise RuntimeError("formal-v4 foundation module tree changed")
        for name, module in trunk.named_modules():
            label = name or "<root>"
            if "forward" in module.__dict__ or "_call_impl" in module.__dict__:
                raise RuntimeError(
                    f"formal-v4 foundation instance execution override at {label}"
                )
            expected_forward = _PINNED_FOUNDATION_CLASS_FORWARDS.get(type(module))
            if expected_forward is not None and type(module).forward is not expected_forward:
                raise RuntimeError(
                    f"formal-v4 foundation class forward changed at {label}"
                )
            for attribute in _FOUNDATION_HOOK_ATTRIBUTES:
                hooks = getattr(module, attribute, None)
                if hooks:
                    raise RuntimeError(
                        f"formal-v4 foundation hooks are forbidden at "
                        f"{label}: {attribute}"
                    )
        if (
            type(trunk.input_proj) is not ExchangeableLayer
            or any(type(block) is not ExchangeableBlock for block in trunk.blocks)
            or type(trunk.out_norm) is not nn.LayerNorm
        ):
            raise RuntimeError("formal-v4 foundation module structure changed")
        if (
            trunk.in_channels != identity.in_channels
            or trunk.hidden != identity.hidden
            or len(trunk.blocks) != identity.layers
            or tuple(sorted(trunk.state_dict())) != self._foundation_state_keys
        ):
            raise RuntimeError("formal-v4 foundation architecture changed")
        parameter_count = sum(parameter.numel() for parameter in trunk.parameters())
        if parameter_count != identity.parameter_count:
            raise RuntimeError("formal-v4 foundation parameter count changed")
        if trunk.training:
            raise RuntimeError("formal-v4 foundation must remain in eval mode")
        if any(parameter.requires_grad for parameter in trunk.parameters()):
            raise RuntimeError("formal-v4 foundation requires_grad changed")
        if any(parameter.grad is not None for parameter in trunk.parameters()):
            raise RuntimeError("formal-v4 foundation accumulated a gradient")
        tensor_digest = _fp32_module_tensor_sha256(trunk)
        if tensor_digest != identity.tensor_sha256:
            raise RuntimeError("formal-v4 foundation FP32 tensor digest changed")
        if self._digest_buffer_hex(self._pinned_checkpoint_sha256) != (
            identity.checkpoint_sha256
        ):
            raise RuntimeError("pinned formal-v4 checkpoint identity changed")
        if self._digest_buffer_hex(self._pinned_foundation_tensor_sha256) != (
            identity.tensor_sha256
        ):
            raise RuntimeError("pinned formal-v4 tensor identity changed")
        if (
            self._pinned_checkpoint_sha256.dtype != torch.uint8
            or self._pinned_foundation_tensor_sha256.dtype != torch.uint8
            or self._pinned_foundation_parameter_count.dtype != torch.int64
        ):
            raise RuntimeError("pinned identity buffer dtype changed")
        if int(self._pinned_foundation_parameter_count) != identity.parameter_count:
            raise RuntimeError("pinned formal-v4 parameter count changed")

        foundation_devices = {parameter.device for parameter in trunk.parameters()}
        head_parameters = tuple(self.joint_adapter.parameters()) + tuple(
            self.policy_head.parameters()
        ) + tuple(self.value_head.parameters())
        head_devices = {parameter.device for parameter in head_parameters}
        if len(foundation_devices) != 1 or head_devices != foundation_devices:
            raise RuntimeError("foundation and E6-v2 heads must share one device")
        if any(parameter.dtype != torch.float32 for parameter in head_parameters):
            raise RuntimeError("E6-v2 heads must remain FP32 with the foundation")
        foundation_device = next(iter(foundation_devices))
        if foundation_device.type != "cpu":
            raise RuntimeError("formal-v4 E6-v2 execution is CPU-only")
        with torch.no_grad():
            canary_output = trunk(_foundation_canary_input(foundation_device))
        if _tensor_sha256(canary_output) != FORMAL_V4_CANARY_OUTPUT_SHA256:
            raise RuntimeError("formal-v4 foundation behavior canary changed")
        return tensor_digest

    def metadata(self) -> dict[str, object]:
        """Separate completed-foundation status from initialized-head status."""

        self.assert_foundation_integrity()
        return {
            "schema_version": self.schema_version,
            "foundation_checkpoint_sha256": self.foundation_identity.checkpoint_sha256,
            "foundation_tensor_sha256": self.foundation_identity.tensor_sha256,
            "foundation_parameter_count": self.foundation_identity.parameter_count,
            "foundation_training_completed": True,
            "foundation_performance": False,
            "head_initial_tensor_sha256": self._initial_head_tensor_sha256,
            "head_current_tensor_sha256": self.current_head_tensor_sha256(),
            "head_training_status": self.head_training_status,
            "head_formal_evaluation": False,
            "head_performance": False,
            "active_trainer_connected": False,
            "execution_device_contract": "fresh_process_cpu_only",
            "threat_model": THREAT_MODEL,
            "modified_checkpoint_policy": (
                "rejected_requires_future_sealed_schema"
            ),
            "symmetry_contract": self.symmetry_contract,
            "claim_boundary": self.claim_boundary,
            "head_hidden": self.head_hidden,
            "joint_hidden": self.joint_hidden,
            "head_seed": self.head_seed,
        }

    def train(self, mode: bool = True) -> "FrozenFoundationV4SharedPolicyValueV2":
        """Change head mode without registering or changing the foundation."""

        super().train(mode)
        self.assert_foundation_integrity()
        return self

    def requires_grad_(
        self, requires_grad: bool = True
    ) -> "FrozenFoundationV4SharedPolicyValueV2":
        """Apply gradient mode to the two new heads only."""

        super().requires_grad_(requires_grad)
        self.assert_foundation_integrity()
        return self

    def _apply(self, fn: object, recurse: bool = True) -> nn.Module:
        """Synchronise device moves and reject every dtype mutation up front.

        Public dtype conversions are rejected before mutation.  PyTorch device
        transfer failures themselves are not transactionally reversible; a
        caller must discard an instance after any failed device transfer.
        """

        self.assert_foundation_integrity()
        foundation_device = next(self.foundation_trunk.parameters()).device
        probes = (
            torch.empty(0, device=foundation_device, dtype=torch.float32),
            torch.empty(0, device=foundation_device, dtype=torch.uint8),
            torch.empty(0, device=foundation_device, dtype=torch.int64),
        )
        transformed = tuple(fn(probe) for probe in probes)  # type: ignore[operator]
        expected_dtypes = (torch.float32, torch.uint8, torch.int64)
        if tuple(item.dtype for item in transformed) != expected_dtypes:
            raise ValueError("E6-v2 dtype conversion is forbidden before mutation")
        target_devices = {item.device for item in transformed}
        if len(target_devices) != 1:
            raise RuntimeError("E6-v2 tensor transform produced mixed devices")
        target_device = next(iter(target_devices))
        if target_device.type != "cpu":
            raise ValueError(
                "E6-v2 formal-v4 execution is CPU-only; device move rejected"
            )
        result = super()._apply(fn, recurse=recurse)  # type: ignore[arg-type]
        self.foundation_trunk.to(device=target_device)
        self.assert_foundation_integrity()
        return result

    def to(self, *args: object, **kwargs: object) -> "FrozenFoundationV4SharedPolicyValueV2":
        """Safely migrate device while prohibiting non-FP32 conversion."""

        _, dtype, _, _ = torch._C._nn._parse_to(*args, **kwargs)
        if dtype is not None and dtype != torch.float32:
            raise ValueError("the pinned formal-v4 foundation must remain FP32")
        super().to(*args, **kwargs)
        self.assert_foundation_integrity()
        return self

    def type(self, dst_type: object | None = None) -> object:
        if dst_type is None:
            return super().type()
        raise ValueError("E6-v2 .type(...) conversion is forbidden")

    def double(self) -> "FrozenFoundationV4SharedPolicyValueV2":
        raise ValueError("the pinned formal-v4 foundation must remain FP32")

    def half(self) -> "FrozenFoundationV4SharedPolicyValueV2":
        raise ValueError("the pinned formal-v4 foundation must remain FP32")

    def bfloat16(self) -> "FrozenFoundationV4SharedPolicyValueV2":
        raise ValueError("the pinned formal-v4 foundation must remain FP32")

    def float(self) -> "FrozenFoundationV4SharedPolicyValueV2":
        return self.to(dtype=torch.float32)

    def state_dict(self, *args: object, **kwargs: object) -> dict[str, torch.Tensor]:
        """Serialise only new heads and pinned identity, never foundation tensors."""

        self.assert_foundation_integrity()
        state = super().state_dict(*args, **kwargs)
        if any("foundation_trunk" in key for key in state):
            raise RuntimeError("E6-v2 state_dict leaked foundation tensors")
        self.assert_foundation_integrity()
        return state

    def _load_from_state_dict(
        self,
        state_dict: Mapping[str, torch.Tensor],
        prefix: str,
        local_metadata: Mapping[str, object],
        strict: bool,
        missing_keys: list[str],
        unexpected_keys: list[str],
        error_msgs: list[str],
    ) -> None:
        """Prefix-aware fail-closed validation for direct and nested loads."""

        if bool(local_metadata.get("assign_to_params_buffers", False)):
            raise RuntimeError(
                f"E6-v2 nested assign=True load is forbidden at {prefix!r}"
            )
        self.assert_foundation_integrity()
        if self.head_training_status != "initialized":
            raise RuntimeError(
                f"E6-v2 nested load target is modified/unsealed at {prefix!r}"
            )
        actual = {
            key[len(prefix) :]
            for key in state_dict
            if key.startswith(prefix)
        }
        forbidden = sorted(key for key in actual if "foundation_trunk" in key)
        if forbidden:
            raise RuntimeError(
                f"E6-v2 nested load forbids foundation keys at {prefix!r}: {forbidden}"
            )
        expected = set(self._serialized_state_keys)
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise RuntimeError(
                f"E6-v2 nested state contract mismatch at {prefix!r}: "
                f"missing={missing}, unexpected={unexpected}"
            )

        current = super().state_dict()
        for local_key in _PINNED_STATE_KEYS:
            incoming = state_dict[prefix + local_key]
            if not isinstance(incoming, torch.Tensor) or not torch.equal(
                incoming.detach().cpu(), current[local_key].detach().cpu()
            ):
                raise RuntimeError(
                    f"E6-v2 pinned identity mismatch at {prefix + local_key}"
                )
        incoming_heads = {
            local_key: state_dict[prefix + local_key]
            for local_key in expected
            if local_key.startswith(
                ("joint_adapter.", "policy_head.", "value_head.")
            )
        }
        if _named_fp32_tensor_sha256(incoming_heads) != (
            self._initial_head_tensor_sha256
        ):
            raise RuntimeError(
                f"E6-v2 nested load rejects modified/unsealed heads at {prefix!r}"
            )
        super()._load_from_state_dict(
            state_dict,
            prefix,
            local_metadata,
            strict,
            missing_keys,
            unexpected_keys,
            error_msgs,
        )

    def _post_load_integrity_hook(
        self,
        module: nn.Module,
        incompatible_keys: torch.nn.modules.module._IncompatibleKeys,
    ) -> None:
        if module is not self:
            raise RuntimeError("E6-v2 post-load hook received the wrong module")
        self.assert_foundation_integrity()
        if self.head_training_status != "initialized":
            raise RuntimeError("E6-v2 load produced modified/unsealed heads")

    def load_state_dict(
        self,
        state_dict: Mapping[str, torch.Tensor],
        strict: bool = True,
        assign: bool = False,
    ) -> torch.nn.modules.module._IncompatibleKeys:
        """Load heads only; reject foundation keys even when ``strict=False``."""

        if assign:
            raise ValueError("E6-v2 load_state_dict(assign=True) is forbidden")
        self.assert_foundation_integrity()
        result = super().load_state_dict(state_dict, strict=strict, assign=assign)
        self.assert_foundation_integrity()
        return result

    def save_head_checkpoint(self, path: str | Path) -> None:
        """Save initialized state; modified heads await a new sealed schema."""

        self.assert_foundation_integrity()
        if self.head_training_status != "initialized":
            raise RuntimeError("modified_unsealed E6-v2 heads cannot be saved")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "schema_version": self.schema_version,
                "metadata": self.metadata(),
                "state_dict": self.state_dict(),
            },
            target,
        )
        self.assert_foundation_integrity()

    @classmethod
    def from_head_checkpoint(
        cls,
        path: str | Path,
        *,
        foundation_checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
    ) -> "FrozenFoundationV4SharedPolicyValueV2":
        """Restore initialized heads against the independently pinned foundation."""

        payload = torch.load(Path(path), map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != (
            FROZEN_SHARED_HEAD_SCHEMA
        ):
            raise ValueError("unsupported E6-v2 head checkpoint schema")
        metadata = payload.get("metadata")
        state_dict = payload.get("state_dict")
        if not isinstance(metadata, Mapping) or not isinstance(state_dict, Mapping):
            raise ValueError("E6-v2 head checkpoint is incomplete")
        metadata_type_contract = {
            "schema_version": str,
            "foundation_checkpoint_sha256": str,
            "foundation_tensor_sha256": str,
            "foundation_parameter_count": int,
            "foundation_training_completed": bool,
            "foundation_performance": bool,
            "head_initial_tensor_sha256": str,
            "head_current_tensor_sha256": str,
            "head_training_status": str,
            "head_formal_evaluation": bool,
            "head_performance": bool,
            "active_trainer_connected": bool,
            "execution_device_contract": str,
            "threat_model": str,
            "modified_checkpoint_policy": str,
            "symmetry_contract": str,
            "claim_boundary": str,
            "head_hidden": int,
            "joint_hidden": int,
            "head_seed": int,
        }
        if set(metadata) != set(metadata_type_contract):
            raise ValueError("E6-v2 head checkpoint metadata key set mismatch")
        for field, expected_type in metadata_type_contract.items():
            if type(metadata[field]) is not expected_type:
                raise ValueError(
                    f"E6-v2 head checkpoint {field} must be a native "
                    f"{expected_type.__name__}"
                )
        model = cls(
            foundation_checkpoint_path,
            head_hidden=metadata["head_hidden"],
            head_seed=metadata["head_seed"],
        )
        expected = model.metadata()
        if dict(metadata) != expected:
            raise ValueError("E6-v2 head checkpoint metadata identity mismatch")
        model.load_state_dict(state_dict, strict=True)
        model.assert_foundation_integrity()
        return model

    def head_named_parameters(self) -> Iterator[tuple[str, nn.Parameter]]:
        """Yield only new-head parameters; the formal-v4 trunk is excluded."""

        for prefix, module in (
            ("joint_adapter", self.joint_adapter),
            ("policy_head", self.policy_head),
            ("value_head", self.value_head),
        ):
            for name, parameter in module.named_parameters():
                yield f"{prefix}.{name}", parameter

    def head_parameters(self) -> tuple[nn.Parameter, ...]:
        return tuple(parameter for _, parameter in self.head_named_parameters())

    def _encode_union_once(
        self,
        vector: VectorANF,
        *,
        weights: SharedUtilityWeights,
    ) -> _FrozenJointFeatures:
        trunk = self.foundation_trunk
        device = next(trunk.parameters()).device
        dtype = next(trunk.parameters()).dtype
        union_terms = tuple(sorted(set().union(*vector.outputs)))
        axis_terms = union_terms or (0,)
        state = encode_state(
            axis_terms,
            vector.input_count,
            _state_context(weights),
            device=device,
            dtype=dtype,
        )
        # Everything derived from caller inputs is complete before this final
        # scan.  The next foundation operation is the real task forward, with
        # no intervening access to a caller-owned object or property.
        self.assert_foundation_integrity()
        # The immutable foundation is a feature extractor only.  Detaching is
        # explicit even though every foundation parameter is requires_grad=False.
        with torch.no_grad():
            self._foundation_task_forward_count += 1
            foundation_cells = trunk(state).detach()

        term_rows = {term: row for row, term in enumerate(union_terms)}
        incidence = torch.zeros(
            (vector.output_count, len(axis_terms)), device=device, dtype=dtype
        )
        for output, terms in enumerate(vector.outputs):
            for term in terms:
                incidence[output, term_rows[term]] = 1.0
        expanded = foundation_cells.unsqueeze(0).expand(
            vector.output_count, -1, -1, -1
        )
        incidence_cells = incidence[:, :, None, None].expand(
            -1, -1, vector.input_count, 1
        )
        joint_input = torch.cat(
            (expanded, incidence_cells, expanded * incidence_cells), dim=-1
        )
        joint_hidden = self.joint_adapter(joint_input)
        result = _FrozenJointFeatures(
            joint_hidden=joint_hidden,
            joint_global=joint_hidden.mean(dim=(0, 1, 2)),
            term_rows=term_rows,
        )
        self.assert_foundation_integrity()
        return result

    @staticmethod
    def _mean_or_zero(
        rows: Sequence[torch.Tensor], reference: torch.Tensor
    ) -> torch.Tensor:
        if not rows:
            return torch.zeros_like(reference)
        return torch.stack(tuple(rows), dim=0).mean(dim=0)

    def prepare_head_inputs(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> FrozenSharedHeadInputsV2:
        """Build detached policy/value inputs from one union-trunk evaluation."""

        vector, actions, weights = _canonicalize_public_inputs(
            vector, actions, weights
        )
        self.assert_foundation_integrity()
        return self._prepare_canonical_head_inputs(vector, actions, weights)

    def _prepare_canonical_head_inputs(
        self,
        vector: VectorANF,
        actions: tuple[SharedAction, ...],
        weights: SharedUtilityWeights,
    ) -> FrozenSharedHeadInputsV2:
        """Prepare inputs already copied into the sealed exact dataclasses."""

        for action in actions:
            validate_shared_action(vector, action)
        encoded = self._encode_union_once(vector, weights=weights)
        value_features = torch.cat(
            (
                encoded.joint_global,
                _value_scalars(
                    vector,
                    device=encoded.joint_global.device,
                    dtype=encoded.joint_global.dtype,
                ),
            )
        )
        if not actions:
            empty = encoded.joint_global.new_empty(
                (0, self.policy_head.in_features)
            )
            return FrozenSharedHeadInputsV2(
                encoded.joint_hidden,
                empty,
                value_features,
                encoded.joint_global.new_empty((0,)),
                encoded.joint_hidden.pow(3).mean(),
            )

        policy_rows: list[torch.Tensor] = []
        policy_relation_residuals: list[torch.Tensor] = []
        for action in actions:
            polynomial_terms = tuple(sorted(action_polynomial_terms(action)))
            touched_inputs = _touched_input_indices(vector, action)
            target_output_pool = encoded.joint_hidden[list(action.targets)].mean(
                dim=(0, 1, 2)
            )
            # LayerNorm makes first and second global moments nearly
            # degenerate.  The parameter-free third moment is a legitimate
            # set-invariant readout that preserves relation-distribution
            # information even before these development heads are trained.
            policy_relation_residuals.append(
                encoded.joint_hidden[list(action.targets)].pow(3).mean()
            )
            shared_term_pool = self._mean_or_zero(
                tuple(
                    encoded.joint_hidden[
                        list(action.targets), encoded.term_rows[term]
                    ].mean(dim=(0, 1))
                    for term in polynomial_terms
                ),
                encoded.joint_global,
            )
            shared_input_pool = self._mean_or_zero(
                tuple(
                    encoded.joint_hidden[list(action.targets), :, index].mean(
                        dim=(0, 1)
                    )
                    for index in touched_inputs
                ),
                encoded.joint_global,
            )
            footprint_pool = encoded.joint_hidden[
                list(action.targets)
            ][:, [encoded.term_rows[term] for term in polynomial_terms]][
                :, :, list(touched_inputs) if touched_inputs else slice(None)
            ].mean(dim=(0, 1, 2))
            scalars = torch.tensor(
                shared_action_scalars(vector, action, weights=weights),
                device=encoded.joint_global.device,
                dtype=encoded.joint_global.dtype,
            )
            policy_rows.append(
                torch.cat(
                    (
                        target_output_pool,
                        shared_term_pool,
                        shared_input_pool,
                        footprint_pool,
                        encoded.joint_global,
                        scalars,
                    )
                )
            )
        return FrozenSharedHeadInputsV2(
            encoded.joint_hidden,
            torch.stack(policy_rows),
            value_features,
            torch.stack(policy_relation_residuals),
            encoded.joint_hidden.pow(3).mean(),
        )

    def forward_one(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ordered candidate logits and one invariant state value."""

        vector, actions, weights = _canonicalize_public_inputs(
            vector, actions, weights
        )
        self.assert_foundation_integrity()
        inputs = self._prepare_canonical_head_inputs(vector, actions, weights)
        logits = (
            self.policy_head(inputs.policy_features)
            + inputs.policy_relation_residual
        )
        value = self.value_head(
            inputs.value_features, inputs.value_relation_residual
        )
        self.assert_foundation_integrity()
        return logits, value


class HeadOnlyIntegrityAdamW(torch.optim.AdamW):
    """Head-only AdamW that revalidates the foundation around every step."""

    _OPTION_KEYS = frozenset(
        {
            "lr",
            "betas",
            "eps",
            "weight_decay",
            "amsgrad",
            "maximize",
            "foreach",
            "capturable",
            "differentiable",
            "fused",
            "decoupled_weight_decay",
        }
    )
    _STATE_KEYS = frozenset({"step", "exp_avg", "exp_avg_sq"})

    def __init__(
        self,
        model: FrozenFoundationV4SharedPolicyValueV2,
        parameters: Sequence[nn.Parameter],
        *,
        learning_rate: float,
        weight_decay: float,
    ) -> None:
        if type(model) is not FrozenFoundationV4SharedPolicyValueV2:
            raise TypeError("HeadOnlyIntegrityAdamW requires the exact E6-v2 model")
        for name, value, positive in (
            ("learning_rate", learning_rate, True),
            ("weight_decay", weight_decay, False),
        ):
            if type(value) is not float or not math.isfinite(value):
                raise TypeError(f"{name} must be a native finite float")
            if (positive and value <= 0.0) or (not positive and value < 0.0):
                raise ValueError(f"{name} is outside the allowed range")
        provided = tuple(parameters)
        expected_named = tuple(model.head_named_parameters())
        expected = tuple(parameter for _, parameter in expected_named)
        provided_ids = tuple(id(parameter) for parameter in provided)
        expected_ids = tuple(id(parameter) for parameter in expected)
        if provided_ids != expected_ids or len(set(provided_ids)) != len(provided_ids):
            raise ValueError(
                "HeadOnlyIntegrityAdamW accepts exactly E6-v2 heads in canonical order"
            )
        foundation_ids = {id(parameter) for parameter in model.foundation_trunk.parameters()}
        if set(provided_ids) & foundation_ids:
            raise ValueError("foundation parameters are forbidden from the optimiser")
        self._model_ref = weakref.ref(model)
        self._expected_parameter_ids = expected_ids
        self._expected_parameter_names = tuple(name for name, _ in expected_named)
        self._expected_parameter_signatures = tuple(
            self._parameter_signature(name, parameter)
            for name, parameter in expected_named
        )
        self._pinned_head_storage = tuple(
            (name, self._storage_interval(parameter))
            for name, parameter in expected_named
        )
        self._completed_steps = 0
        self._pinned_state_storage: tuple[
            tuple[str, tuple[str, int, int] | None], ...
        ] | None = None
        self._expected_options = {
            "lr": learning_rate,
            "betas": (0.9, 0.999),
            "eps": 1.0e-8,
            "weight_decay": weight_decay,
            "amsgrad": False,
            "maximize": False,
            "foreach": False,
            "capturable": False,
            "differentiable": False,
            "fused": False,
            "decoupled_weight_decay": True,
        }
        self._initialising_parameter_group = True
        super().__init__(
            provided,
            lr=learning_rate,
            betas=(0.9, 0.999),
            eps=1.0e-8,
            weight_decay=weight_decay,
            amsgrad=False,
            maximize=False,
            foreach=False,
            capturable=False,
            differentiable=False,
            fused=False,
        )
        self._initialising_parameter_group = False
        self._assert_parameter_contract()
        self._assert_hyperparameter_contract()
        self._assert_optimizer_state_contract()
        self._assert_storage_contract()

    def _model(self) -> FrozenFoundationV4SharedPolicyValueV2:
        model = self._model_ref()
        if model is None:
            raise RuntimeError("E6-v2 model no longer exists")
        return model

    def _assert_parameter_contract(self) -> None:
        model = self._model()
        current_named = tuple(model.head_named_parameters())
        current_ids = tuple(id(parameter) for _, parameter in current_named)
        optimiser_ids = tuple(
            id(parameter)
            for group in self.param_groups
            for parameter in group["params"]
        )
        if (
            current_ids != self._expected_parameter_ids
            or optimiser_ids != self._expected_parameter_ids
            or tuple(name for name, _ in current_named)
            != self._expected_parameter_names
        ):
            raise RuntimeError("E6-v2 optimiser ordered parameter identity changed")
        signatures = tuple(
            self._parameter_signature(name, parameter)
            for name, parameter in current_named
        )
        if signatures != self._expected_parameter_signatures:
            raise RuntimeError("E6-v2 optimiser parameter tensor contract changed")
        foundation_ids = {
            id(parameter) for parameter in model.foundation_trunk.parameters()
        }
        if set(optimiser_ids) & foundation_ids:
            raise RuntimeError("foundation parameter entered the E6-v2 optimiser")

    @staticmethod
    def _parameter_signature(name: str, parameter: nn.Parameter) -> tuple[object, ...]:
        if type(parameter) is not nn.Parameter:
            raise RuntimeError(f"E6-v2 head {name!r} must be an exact Parameter")
        return (
            name,
            id(parameter),
            tuple(parameter.shape),
            tuple(parameter.stride()),
            int(parameter.storage_offset()),
            parameter.layout,
            parameter.dtype,
            str(parameter.device),
            parameter.requires_grad,
        )

    @staticmethod
    def _same_native_value(actual: object, expected: object) -> bool:
        if type(actual) is not type(expected):
            return False
        if isinstance(expected, tuple):
            return len(actual) == len(expected) and all(  # type: ignore[arg-type]
                HeadOnlyIntegrityAdamW._same_native_value(left, right)
                for left, right in zip(actual, expected)  # type: ignore[arg-type]
            )
        return bool(actual == expected)

    def _assert_hyperparameter_contract(self) -> None:
        if type(self.param_groups) is not list or len(self.param_groups) != 1:
            raise RuntimeError("E6-v2 optimiser requires exactly one parameter group")
        group = self.param_groups[0]
        if type(group) is not dict or set(group) != self._OPTION_KEYS | {"params"}:
            raise RuntimeError("E6-v2 optimiser parameter-group schema changed")
        if type(self.defaults) is not dict or set(self.defaults) != self._OPTION_KEYS:
            raise RuntimeError("E6-v2 optimiser defaults schema changed")
        if type(group["params"]) is not list:
            raise RuntimeError("E6-v2 optimiser params must remain a native list")
        for key, expected in self._expected_options.items():
            if not self._same_native_value(group[key], expected):
                raise RuntimeError(f"E6-v2 optimiser group option changed: {key}")
            if not self._same_native_value(self.defaults[key], expected):
                raise RuntimeError(f"E6-v2 optimiser default option changed: {key}")

    @staticmethod
    def _storage_interval(
        tensor: torch.Tensor,
    ) -> tuple[str, int, int] | None:
        """Return the whole backing-storage interval for conservative alias checks."""

        storage = tensor.untyped_storage()
        size = int(storage.nbytes())
        if size <= 0:
            return None
        start = int(storage.data_ptr())
        return str(tensor.device), start, start + size

    @classmethod
    def _iter_state_tensors(
        cls, value: object, prefix: str
    ) -> Iterator[tuple[str, torch.Tensor]]:
        if isinstance(value, torch.Tensor):
            yield prefix, value
        elif isinstance(value, Mapping):
            for key, item in value.items():
                yield from cls._iter_state_tensors(item, f"{prefix}.{key}")
        elif isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                yield from cls._iter_state_tensors(item, f"{prefix}[{index}]")

    @staticmethod
    def _intervals_overlap(
        left: tuple[str, int, int], right: tuple[str, int, int]
    ) -> bool:
        return (
            left[0] == right[0]
            and left[1] < right[2]
            and right[1] < left[2]
        )

    def _all_training_tensors(self) -> list[tuple[str, torch.Tensor]]:
        model = self._model()
        tensors: list[tuple[str, torch.Tensor]] = []
        for name, tensor in tuple(model.foundation_trunk.named_parameters()) + tuple(
            model.foundation_trunk.named_buffers()
        ):
            tensors.append((f"foundation.{name}", tensor))
        for name, tensor in model.named_buffers(recurse=False):
            tensors.append((f"identity_buffer.{name}", tensor))
        for name, parameter in model.head_named_parameters():
            tensors.append((f"head.data.{name}", parameter))
            if parameter.grad is not None:
                tensors.append((f"head.grad.{name}", parameter.grad))
        names_by_id = {
            id(parameter): name for name, parameter in model.head_named_parameters()
        }
        for parameter, state in self.state.items():
            parameter_name = names_by_id.get(id(parameter), f"unknown.{id(parameter)}")
            tensors.extend(
                self._iter_state_tensors(
                    state, f"optimizer.state.{parameter_name}"
                )
            )
        return tensors

    def _current_state_storage(
        self,
    ) -> tuple[tuple[str, tuple[str, int, int] | None], ...]:
        model = self._model()
        rows: list[tuple[str, tuple[str, int, int] | None]] = []
        for name, parameter in model.head_named_parameters():
            for state_name in ("step", "exp_avg", "exp_avg_sq"):
                value = self.state.get(parameter, {}).get(state_name)
                if isinstance(value, torch.Tensor):
                    rows.append(
                        (f"{name}.{state_name}", self._storage_interval(value))
                    )
        return tuple(rows)

    def _assert_storage_contract(self) -> None:
        """Require pinned head storage and global pairwise storage disjointness."""

        tensors = self._all_training_tensors()
        ranged: list[tuple[str, tuple[str, int, int]]] = []
        for name, tensor in tensors:
            interval = self._storage_interval(tensor)
            if interval is not None:
                ranged.append((name, interval))
        for left_index, (left_name, left) in enumerate(ranged):
            for right_name, right in ranged[left_index + 1 :]:
                if self._intervals_overlap(left, right):
                    raise RuntimeError(
                        "E6-v2 training tensor storage aliases frozen foundation "
                        "or another tensor: "
                        f"{left_name} overlaps {right_name}"
                    )
        current_head = tuple(
            (name, self._storage_interval(parameter))
            for name, parameter in self._model().head_named_parameters()
        )
        if current_head != self._pinned_head_storage:
            raise RuntimeError("E6-v2 head backing storage changed")
        current_state = self._current_state_storage()
        if self._pinned_state_storage is not None and (
            current_state != self._pinned_state_storage
        ):
            raise RuntimeError("E6-v2 optimiser-state backing storage changed")

    @staticmethod
    def _assert_finite_tensor(tensor: torch.Tensor, name: str) -> None:
        if not bool(torch.isfinite(tensor).all()):
            raise RuntimeError(f"E6-v2 training tensor is non-finite: {name}")

    def _assert_head_and_gradient_contract(self, *, require_gradients: bool) -> None:
        gradients_present = []
        for name, parameter in self._model().head_named_parameters():
            self._assert_finite_tensor(parameter, f"head.data.{name}")
            gradient = parameter.grad
            gradients_present.append(gradient is not None)
            if gradient is None:
                continue
            if (
                type(gradient) is not torch.Tensor
                or gradient.layout != torch.strided
                or gradient.dtype != torch.float32
                or gradient.device.type != "cpu"
                or tuple(gradient.shape) != tuple(parameter.shape)
                or gradient.requires_grad
            ):
                raise RuntimeError(f"E6-v2 head gradient contract changed: {name}")
            self._assert_finite_tensor(gradient, f"head.grad.{name}")
        if any(gradients_present) and not all(gradients_present):
            raise RuntimeError("E6-v2 head gradients are partially populated")
        if require_gradients and not all(gradients_present):
            raise RuntimeError("E6-v2 optimiser step requires every head gradient")

    def _assert_optimizer_state_contract(self) -> None:
        parameters = self._model().head_parameters()
        if self._completed_steps == 0:
            if len(self.state) != 0:
                raise RuntimeError("E6-v2 optimiser state must be empty before step one")
            return
        if set(self.state) != set(parameters) or len(self.state) != len(parameters):
            raise RuntimeError("E6-v2 optimiser state parameter set changed")
        for name, parameter in self._model().head_named_parameters():
            state = self.state[parameter]
            if type(state) is not dict or set(state) != self._STATE_KEYS:
                raise RuntimeError(f"E6-v2 optimiser state schema changed: {name}")
            step = state["step"]
            if (
                type(step) is not torch.Tensor
                or step.layout != torch.strided
                or step.dtype != torch.float32
                or step.device.type != "cpu"
                or tuple(step.shape) != ()
                or step.requires_grad
                or float(step) != float(self._completed_steps)
            ):
                raise RuntimeError(f"E6-v2 optimiser step state changed: {name}")
            self._assert_finite_tensor(step, f"optimizer.state.{name}.step")
            for state_name in ("exp_avg", "exp_avg_sq"):
                tensor = state[state_name]
                if (
                    type(tensor) is not torch.Tensor
                    or tensor.layout != torch.strided
                    or tensor.dtype != torch.float32
                    or tensor.device.type != "cpu"
                    or tuple(tensor.shape) != tuple(parameter.shape)
                    or tensor.requires_grad
                ):
                    raise RuntimeError(
                        f"E6-v2 optimiser {state_name} contract changed: {name}"
                    )
                self._assert_finite_tensor(
                    tensor, f"optimizer.state.{name}.{state_name}"
                )

    def add_param_group(self, param_group: dict[str, object]) -> None:
        if not getattr(self, "_initialising_parameter_group", False):
            raise RuntimeError("E6-v2 optimiser parameter groups are frozen")
        super().add_param_group(param_group)  # type: ignore[arg-type]

    def zero_grad(self, set_to_none: bool = True) -> None:
        if set_to_none is not True:
            raise ValueError("E6-v2 zero_grad requires set_to_none=True")
        model = self._model()
        self._assert_parameter_contract()
        self._assert_hyperparameter_contract()
        self._assert_storage_contract()
        self._assert_optimizer_state_contract()
        self._assert_head_and_gradient_contract(require_gradients=False)
        model.assert_foundation_integrity()
        super().zero_grad(set_to_none=True)
        if any(parameter.grad is not None for parameter in model.head_parameters()):
            raise RuntimeError("E6-v2 zero_grad did not clear every head gradient")
        self._assert_parameter_contract()
        self._assert_hyperparameter_contract()
        self._assert_optimizer_state_contract()
        self._assert_storage_contract()
        self._assert_head_and_gradient_contract(require_gradients=False)
        model.assert_foundation_integrity()

    def load_state_dict(self, state_dict: dict[str, object]) -> None:
        raise RuntimeError(
            "E6-v2 optimizer state loading requires a future sealed schema"
        )

    def step(self, closure: object | None = None) -> object | None:
        if closure is not None:
            raise ValueError("E6-v2 optimiser closures are forbidden")
        model = self._model()
        self._assert_parameter_contract()
        self._assert_hyperparameter_contract()
        self._assert_storage_contract()
        self._assert_optimizer_state_contract()
        model.assert_foundation_integrity()
        self._assert_head_and_gradient_contract(require_gradients=True)
        result = super().step(closure=None)
        self._completed_steps += 1
        self._assert_parameter_contract()
        self._assert_hyperparameter_contract()
        self._assert_optimizer_state_contract()
        self._assert_head_and_gradient_contract(require_gradients=True)
        if self._pinned_state_storage is None:
            self._pinned_state_storage = self._current_state_storage()
        self._assert_storage_contract()
        model.assert_foundation_integrity()
        return result


def build_head_only_optimizer(
    model: FrozenFoundationV4SharedPolicyValueV2,
    *,
    learning_rate: float = 1.0e-3,
    weight_decay: float = 1.0e-4,
) -> HeadOnlyIntegrityAdamW:
    """Create an optimiser whose parameter set is exactly the two new heads."""

    if type(model) is not FrozenFoundationV4SharedPolicyValueV2:
        raise TypeError("model must be exact FrozenFoundationV4SharedPolicyValueV2")
    model.assert_foundation_integrity()
    for name, value in (
        ("learning_rate", learning_rate),
        ("weight_decay", weight_decay),
    ):
        if type(value) is not float or not math.isfinite(value):
            raise TypeError(f"{name} must be a native finite float")
        if value < 0.0:
            raise ValueError(f"{name} must be non-negative")
    if learning_rate <= 0.0:
        raise ValueError("learning_rate must be positive")
    head_parameters = model.head_parameters()
    if not head_parameters or any(not parameter.requires_grad for parameter in head_parameters):
        raise RuntimeError("new shared heads must be trainable")
    optimiser = HeadOnlyIntegrityAdamW(
        model,
        head_parameters,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
    )
    model.assert_foundation_integrity()
    return optimiser


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_FORMAL_V4_CHECKPOINT",
    "FORMAL_V4_CHECKPOINT_SHA256",
    "FROZEN_SHARED_HEAD_SCHEMA",
    "SYMMETRY_CONTRACT",
    "VALUE_SCALAR_NAMES",
    "FormalV4TrunkIdentity",
    "FrozenFoundationV4SharedPolicyValueV2",
    "FrozenJointEquivariantAdapterV2",
    "FrozenSharedActionPolicyHeadV2",
    "FrozenSharedHeadInputsV2",
    "FrozenSharedValueHeadV2",
    "HeadOnlyIntegrityAdamW",
    "build_head_only_optimizer",
    "load_frozen_foundation_v4_trunk",
]
