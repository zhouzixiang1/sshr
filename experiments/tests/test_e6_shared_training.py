#!/usr/bin/env python3
"""Split and equal-update contracts for E6 shared policy/value fitting."""

from __future__ import annotations

import hashlib

import pytest
import torch

from e6.shared_model import SharedEquivariantTrunk, SharedPolicyValueModel
from e6.shared_oracle import VectorANF, enumerate_monomial_shared_actions
from e6.shared_training import (
    SHARED_TRAINING_SCHEMA,
    SharedPolicyValueTarget,
    SharedTrainingConfig,
    fit_shared_policy_value,
    model_parameter_sha256,
)


def _problem():
    vector = VectorANF(
        3,
        (
            frozenset({0b011, 0b101, 0b110}),
            frozenset({0b011, 0b101}),
            frozenset({0b011, 0b110}),
        ),
    )
    actions = enumerate_monomial_shared_actions(vector)
    assert len(actions) >= 3
    return vector, actions


def _sample(
    *,
    source_kind: str = "direct_qaoa_measurement",
    split_role: str = "train_replay",
    qaoa_execution_class: str | None = "direct_unrepaired",
    best: int = 0,
) -> SharedPolicyValueTarget:
    vector, actions = _problem()
    target = tuple(float(index == best) for index in range(len(actions)))
    return SharedPolicyValueTarget(
        vector=vector,
        actions=actions,
        policy_target=target,
        value_target_log_ratio=-0.25,
        source_kind=source_kind,
        source_sha256=hashlib.sha256(
            f"{source_kind}:{split_role}:{best}".encode()
        ).hexdigest(),
        split_role=split_role,
        qaoa_execution_class=qaoa_execution_class,
    )


def _model(seed: int = 609) -> SharedPolicyValueModel:
    torch.manual_seed(seed)
    return SharedPolicyValueModel(
        SharedEquivariantTrunk(hidden=20, layers=2), mlp_hidden=32
    )


def test_equal_update_training_changes_parameters_and_reduces_target_loss() -> None:
    model = _model()
    config = SharedTrainingConfig(
        update_steps=40,
        batch_size=2,
        learning_rate=2.0e-3,
        seed=20260906,
    )
    report = fit_shared_policy_value(model, (_sample(),), config=config)

    assert report.schema_version == SHARED_TRAINING_SCHEMA
    assert report.source_kind == "direct_qaoa_measurement"
    assert report.update_steps == 40
    assert report.policy_observations == 80
    assert report.initial_parameter_sha256 != report.final_parameter_sha256
    assert report.final_loss < report.initial_loss
    assert report.split_roles == ("train_replay",)
    assert report.qaoa_execution_classes == ("direct_unrepaired",)
    assert report.performance_evidence is False


def test_blind_or_evaluation_split_is_rejected_before_any_update() -> None:
    for split in ("blind_evaluation", "test_evaluation", "validation_monitor"):
        model = _model()
        before = model_parameter_sha256(model)
        with pytest.raises(ValueError, match="forbidden from model updates"):
            fit_shared_policy_value(model, (_sample(split_role=split),))
        assert model_parameter_sha256(model) == before


def test_repaired_or_fallback_qaoa_cannot_be_labelled_quantum_teacher() -> None:
    for execution_class in ("direct_repaired", "fallback", "not_invoked", None):
        with pytest.raises(ValueError, match="direct-unrepaired"):
            _sample(qaoa_execution_class=execution_class)


def test_one_fit_run_cannot_mix_causal_source_arms() -> None:
    model = _model()
    qaoa = _sample()
    exact = _sample(
        source_kind="exact_teacher",
        qaoa_execution_class=None,
        best=1,
    )
    with pytest.raises(ValueError, match="exactly one causal source arm"):
        fit_shared_policy_value(model, (qaoa, exact))


@pytest.mark.parametrize(
    "policy",
    [
        (0.5, 0.5),
        (0.4, 0.4, 0.4, 0.4),
        (1.1, -0.1, 0.0, 0.0),
    ],
)
def test_policy_target_shape_normalization_and_sign_fail_closed(policy) -> None:
    vector, actions = _problem()
    with pytest.raises(ValueError, match="policy target"):
        SharedPolicyValueTarget(
            vector=vector,
            actions=actions,
            policy_target=policy,
            value_target_log_ratio=-0.2,
            source_kind="exact_teacher",
            source_sha256="0" * 64,
        )
