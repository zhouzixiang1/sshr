#!/usr/bin/env python3
"""Equivariance and checkpoint contracts for the E6 shared policy/value model."""

from __future__ import annotations

import math

import pytest
import torch

from e6.shared_model import (
    ACTION_SCALAR_NAMES,
    SHARED_MODEL_SCHEMA,
    STATE_CHANNEL_NAMES,
    SharedEquivariantTrunk,
    SharedPolicyValueModel,
    SharedPolicyValueScorer,
    encode_vector_anf,
)
from e6.shared_oracle import (
    SemiAffineSharedAction,
    VectorANF,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
    permute_action_inputs,
    permute_action_outputs,
)


TOL = 2.0e-5


def _vector() -> VectorANF:
    semi = frozenset({0b001, 0b011, 0b101})
    return VectorANF(
        3,
        (
            semi | {0b110, 0},
            semi | {0b010},
            frozenset({0b011, 0b101, 0b110, 0}),
        ),
    )


def _actions(vector: VectorANF):
    actions = (
        enumerate_monomial_shared_actions(vector)
        + enumerate_semi_affine_shared_actions(
            vector, max_affine_weight=3
        )
    )
    assert len(actions) >= 4
    return actions


def _permuted_input_value(x: int, old_to_new: tuple[int, ...]) -> int:
    result = 0
    for old, new in enumerate(old_to_new):
        result |= ((x >> old) & 1) << new
    return result


def test_input_permutation_maps_vector_semantics_and_actions() -> None:
    vector = _vector()
    action = SemiAffineSharedAction(0b001, 0b110, True, (0, 1))
    old_to_new = (2, 0, 1)
    permuted = vector.permute_inputs(old_to_new)
    mapped_action = permute_action_inputs(
        action, old_to_new, input_count=vector.input_count
    )

    for x in range(1 << vector.input_count):
        assert permuted.evaluate_bits(
            _permuted_input_value(x, old_to_new)
        ) == vector.evaluate_bits(x)
    assert mapped_action.polynomial_terms <= permuted.outputs[0]
    assert mapped_action.polynomial_terms <= permuted.outputs[1]


def test_shared_policy_and_value_respect_output_permutation() -> None:
    vector = _vector()
    actions = _actions(vector)
    scorer = SharedPolicyValueScorer.untrained(seed=609, hidden=24, layers=2)
    original = scorer.score_actions(vector, actions)
    original_value = scorer.predict_log_ratio(vector)

    old_to_new = (2, 0, 1)
    permuted = vector.permute_outputs(old_to_new)
    mapped = tuple(
        permute_action_outputs(
            action, old_to_new, output_count=vector.output_count
        )
        for action in actions
    )
    permuted_scores = scorer.score_actions(permuted, mapped)

    assert permuted_scores == pytest.approx(original, abs=TOL, rel=TOL)
    assert scorer.predict_log_ratio(permuted) == pytest.approx(
        original_value, abs=TOL, rel=TOL
    )


def test_shared_policy_and_value_respect_input_permutation() -> None:
    vector = _vector()
    actions = _actions(vector)
    scorer = SharedPolicyValueScorer.untrained(seed=610, hidden=24, layers=2)
    original = scorer.score_actions(vector, actions)
    original_value = scorer.predict_log_ratio(vector)

    old_to_new = (1, 2, 0)
    permuted = vector.permute_inputs(old_to_new)
    mapped = tuple(
        permute_action_inputs(
            action, old_to_new, input_count=vector.input_count
        )
        for action in actions
    )

    assert scorer.score_actions(permuted, mapped) == pytest.approx(
        original, abs=TOL, rel=TOL
    )
    assert scorer.predict_log_ratio(permuted) == pytest.approx(
        original_value, abs=TOL, rel=TOL
    )


def test_candidate_order_only_reorders_policy_logits() -> None:
    vector = _vector()
    actions = _actions(vector)
    scorer = SharedPolicyValueScorer.untrained(seed=611, hidden=24, layers=2)
    original = scorer.score_actions(vector, actions)
    order = tuple(reversed(range(len(actions))))

    reordered = scorer.score_actions(
        vector, tuple(actions[index] for index in order)
    )
    assert reordered == pytest.approx(
        [original[index] for index in order], abs=TOL, rel=TOL
    )


def test_shared_model_is_trainable_and_zero_vector_value_is_total() -> None:
    vector = _vector()
    actions = _actions(vector)[:5]
    torch.manual_seed(612)
    model = SharedPolicyValueModel(
        SharedEquivariantTrunk(hidden=20, layers=2), mlp_hidden=32
    )
    logits, value = model.forward_one(vector, actions)
    loss = logits.square().mean() + value.square()
    loss.backward()

    gradients = [
        parameter.grad
        for parameter in model.parameters()
        if parameter.requires_grad and parameter.grad is not None
    ]
    assert gradients
    assert all(torch.isfinite(gradient).all() for gradient in gradients)

    zero = VectorANF(3, (frozenset(), frozenset()))
    zero_encoding = encode_vector_anf(zero)
    assert zero_encoding.real_terms == ()
    assert zero_encoding.axis_terms == (0,)
    zero_logits, zero_value = model.forward_one(zero, ())
    assert zero_logits.shape == (0,)
    assert math.isfinite(float(zero_value.detach()))


def test_shared_checkpoint_roundtrip_and_channel_contract(tmp_path) -> None:
    vector = _vector()
    actions = _actions(vector)
    scorer = SharedPolicyValueScorer.untrained(seed=613, hidden=24, layers=2)
    expected = scorer.score_actions(vector, actions)
    checkpoint = tmp_path / "shared-model.pt"
    scorer.save(
        checkpoint,
        provenance={
            "role": "architecture-roundtrip-test-only",
            "training_performed": False,
        },
    )

    payload = torch.load(checkpoint, map_location="cpu")
    assert payload["schema_version"] == SHARED_MODEL_SCHEMA
    assert payload["state_channel_names"] == list(STATE_CHANNEL_NAMES)
    assert payload["action_scalar_names"] == list(ACTION_SCALAR_NAMES)
    assert payload["performance_evidence"] is False
    restored = SharedPolicyValueScorer.from_checkpoint(checkpoint)
    assert restored.score_actions(vector, actions) == pytest.approx(
        expected, abs=0.0, rel=0.0
    )

    payload["state_channel_names"][0] = "tampered"
    tampered = tmp_path / "tampered.pt"
    torch.save(payload, tampered)
    with pytest.raises(ValueError, match="state channel contract changed"):
        SharedPolicyValueScorer.from_checkpoint(tampered)
