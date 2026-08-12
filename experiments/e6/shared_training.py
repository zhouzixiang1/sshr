"""Split-safe, equal-update training primitive for the E6 shared model.

This module deliberately accepts already verified policy/value targets.  QAOA
measurement records are converted into those targets by the replay layer; a
blind/evaluation record or a repaired/fallback QAOA record is rejected before
an optimiser is created.  The fixed number of update steps is part of the
contract so causal replay arms cannot gain an advantage merely by training
longer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import random
import re
from typing import Sequence

import torch

from e6.shared_model import SharedPolicyValueModel
from e6.shared_oracle import SharedAction, VectorANF, validate_shared_action
from e6.shared_scheduler import SharedUtilityWeights


SHARED_TRAINING_SCHEMA = "xa.e6-shared-replay-training.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_KINDS = {
    "base_resample_control",
    "shuffled_qaoa_control",
    "exact_teacher",
    "direct_qaoa_measurement",
}


@dataclass(frozen=True)
class SharedPolicyValueTarget:
    """One ordered candidate pool and its verified supervised targets."""

    vector: VectorANF
    actions: tuple[SharedAction, ...]
    policy_target: tuple[float, ...]
    value_target_log_ratio: float
    source_kind: str
    source_sha256: str
    split_role: str = "train_replay"
    qaoa_execution_class: str | None = None

    def __post_init__(self) -> None:
        actions = tuple(self.actions)
        policy = tuple(float(value) for value in self.policy_target)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "policy_target", policy)
        if not actions or len(policy) != len(actions):
            raise ValueError("policy target must align with a non-empty action pool")
        for action in actions:
            validate_shared_action(self.vector, action)
        if any(not math.isfinite(value) or value < 0.0 for value in policy):
            raise ValueError("policy target must contain finite non-negative values")
        if not math.isclose(sum(policy), 1.0, rel_tol=0.0, abs_tol=1e-8):
            raise ValueError("policy target must sum to one")
        value = float(self.value_target_log_ratio)
        if not math.isfinite(value) or not -3.0 <= value <= 0.0:
            raise ValueError("value target must be a finite log ratio in [-3, 0]")
        object.__setattr__(self, "value_target_log_ratio", value)
        if self.source_kind not in _SOURCE_KINDS:
            raise ValueError(f"unregistered E6 training source: {self.source_kind}")
        if not _SHA256.fullmatch(self.source_sha256):
            raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
        if self.source_kind in {
            "direct_qaoa_measurement",
            "shuffled_qaoa_control",
        } and self.qaoa_execution_class != "direct_unrepaired":
            raise ValueError(
                "QAOA replay training accepts direct-unrepaired trajectories only"
            )

    def assert_update_eligible(self) -> None:
        if self.split_role != "train_replay":
            raise ValueError(
                f"split_role={self.split_role!r} is forbidden from model updates"
            )


@dataclass(frozen=True)
class SharedTrainingConfig:
    update_steps: int = 32
    batch_size: int = 4
    learning_rate: float = 1.0e-3
    weight_decay: float = 1.0e-4
    policy_weight: float = 1.0
    value_weight: float = 1.0
    seed: int = 20260906

    def __post_init__(self) -> None:
        for name in ("update_steps", "batch_size"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in (
            "learning_rate",
            "weight_decay",
            "policy_weight",
            "value_weight",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
            object.__setattr__(self, name, value)
        if self.learning_rate <= 0.0:
            raise ValueError("learning_rate must be positive")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SharedTrainingReport:
    schema_version: str
    source_kind: str
    sample_count: int
    update_steps: int
    batch_size: int
    policy_observations: int
    initial_loss: float
    final_loss: float
    initial_parameter_sha256: str
    final_parameter_sha256: str
    split_roles: tuple[str, ...]
    qaoa_execution_classes: tuple[str, ...]
    performance_evidence: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def model_parameter_sha256(model: SharedPolicyValueModel) -> str:
    """Hash names, shapes, dtypes and exact CPU parameter bytes."""

    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _sample_loss(
    model: SharedPolicyValueModel,
    sample: SharedPolicyValueTarget,
    *,
    weights: SharedUtilityWeights,
    device: torch.device,
    policy_weight: float,
    value_weight: float,
) -> torch.Tensor:
    logits, value = model.forward_one(
        sample.vector, sample.actions, weights=weights, device=device
    )
    target = torch.tensor(
        sample.policy_target, dtype=logits.dtype, device=logits.device
    )
    policy_loss = -(target * torch.log_softmax(logits, dim=-1)).sum()
    value_target = torch.tensor(
        sample.value_target_log_ratio, dtype=value.dtype, device=value.device
    )
    value_loss = (value - value_target).square()
    return policy_weight * policy_loss + value_weight * value_loss


@torch.no_grad()
def mean_shared_training_loss(
    model: SharedPolicyValueModel,
    samples: Sequence[SharedPolicyValueTarget],
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
    device: torch.device | None = None,
    policy_weight: float = 1.0,
    value_weight: float = 1.0,
) -> float:
    if not samples:
        raise ValueError("at least one E6 training sample is required")
    target_device = torch.device("cpu") if device is None else device
    model.eval()
    return float(
        torch.stack(
            [
                _sample_loss(
                    model,
                    sample,
                    weights=weights,
                    device=target_device,
                    policy_weight=policy_weight,
                    value_weight=value_weight,
                )
                for sample in samples
            ]
        ).mean()
    )


def fit_shared_policy_value(
    model: SharedPolicyValueModel,
    samples: Sequence[SharedPolicyValueTarget],
    *,
    config: SharedTrainingConfig = SharedTrainingConfig(),
    weights: SharedUtilityWeights = SharedUtilityWeights(),
    device: torch.device | None = None,
) -> SharedTrainingReport:
    """Apply exactly ``update_steps`` updates to one declared causal arm."""

    samples = tuple(samples)
    if not samples:
        raise ValueError("at least one E6 training sample is required")
    for sample in samples:
        sample.assert_update_eligible()
    source_kinds = {sample.source_kind for sample in samples}
    if len(source_kinds) != 1:
        raise ValueError("one training run must contain exactly one causal source arm")

    target_device = torch.device("cpu") if device is None else device
    model.to(target_device)
    initial_sha = model_parameter_sha256(model)
    initial_loss = mean_shared_training_loss(
        model,
        samples,
        weights=weights,
        device=target_device,
        policy_weight=config.policy_weight,
        value_weight=config.value_weight,
    )
    optimiser = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    rng = random.Random(config.seed)
    order: list[int] = []
    cursor = 0
    model.train()
    for _ in range(config.update_steps):
        chosen: list[int] = []
        while len(chosen) < config.batch_size:
            if cursor >= len(order):
                order = list(range(len(samples)))
                rng.shuffle(order)
                cursor = 0
            chosen.append(order[cursor])
            cursor += 1
        loss = torch.stack(
            [
                _sample_loss(
                    model,
                    samples[index],
                    weights=weights,
                    device=target_device,
                    policy_weight=config.policy_weight,
                    value_weight=config.value_weight,
                )
                for index in chosen
            ]
        ).mean()
        optimiser.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimiser.step()
    model.eval()
    final_loss = mean_shared_training_loss(
        model,
        samples,
        weights=weights,
        device=target_device,
        policy_weight=config.policy_weight,
        value_weight=config.value_weight,
    )
    return SharedTrainingReport(
        schema_version=SHARED_TRAINING_SCHEMA,
        source_kind=next(iter(source_kinds)),
        sample_count=len(samples),
        update_steps=config.update_steps,
        batch_size=config.batch_size,
        policy_observations=config.update_steps * config.batch_size,
        initial_loss=initial_loss,
        final_loss=final_loss,
        initial_parameter_sha256=initial_sha,
        final_parameter_sha256=model_parameter_sha256(model),
        split_roles=tuple(sorted({sample.split_role for sample in samples})),
        qaoa_execution_classes=tuple(
            sorted(
                {
                    sample.qaoa_execution_class
                    for sample in samples
                    if sample.qaoa_execution_class is not None
                }
            )
        ),
        performance_evidence=False,
    )


__all__ = [
    "SHARED_TRAINING_SCHEMA",
    "SharedPolicyValueTarget",
    "SharedTrainingConfig",
    "SharedTrainingReport",
    "fit_shared_policy_value",
    "mean_shared_training_loss",
    "model_parameter_sha256",
]
