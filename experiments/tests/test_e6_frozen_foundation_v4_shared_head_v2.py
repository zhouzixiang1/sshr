#!/usr/bin/env python3
"""Isolation and symmetry tests for the development-only frozen E6-v2 head."""

from __future__ import annotations

from collections import OrderedDict
from itertools import permutations
from pathlib import Path
import pickle
import random

import pytest
import torch

from e6.frozen_foundation_v4_shared_head_v2 import (
    CLAIM_BOUNDARY,
    DEFAULT_FORMAL_V4_CHECKPOINT,
    FORMAL_V4_CHECKPOINT_SHA256,
    SYMMETRY_CONTRACT,
    THREAT_MODEL,
    FrozenFoundationV4SharedPolicyValueV2,
    HeadOnlyIntegrityAdamW,
    build_head_only_optimizer,
    load_frozen_foundation_v4_trunk,
)
from e6.shared_oracle import (
    MonomialSharedAction,
    VectorANF,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
    permute_action_inputs,
    permute_action_outputs,
)
from e6.shared_scheduler import SharedUtilityWeights
from src.foundation.equivariant import EquivariantTrunk
import src.foundation.equivariant as foundation_equivariant
import torch.nn.functional as torch_functional


TOL = 3.0e-5


class _NestedWrapper(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.shared = _model()
        self.sibling = torch.nn.Linear(2, 1)


class _MaliciousCheckpointPayload:
    def __init__(self, marker: Path) -> None:
        self.marker = str(marker)

    def __reduce__(self):
        expression = (
            "__import__('pathlib').Path(" + repr(self.marker) + ")"
            ".write_text('executed', encoding='utf-8')"
        )
        return eval, (expression,)


def _vector() -> VectorANF:
    shared = frozenset({0b001, 0b011, 0b101})
    return VectorANF(
        3,
        (
            shared | {0b110, 0},
            shared | {0b010},
            frozenset({0b011, 0b101, 0b110, 0}),
        ),
    )


def _actions(vector: VectorANF):
    actions = (
        enumerate_monomial_shared_actions(vector)
        + enumerate_semi_affine_shared_actions(vector, max_affine_weight=3)
    )
    assert len(actions) >= 5
    return actions


def _model() -> FrozenFoundationV4SharedPolicyValueV2:
    model = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=24,
        head_seed=20260907,
    )
    model.eval()
    return model


def _foundation_snapshot(
    model: FrozenFoundationV4SharedPolicyValueV2,
) -> dict[str, torch.Tensor]:
    return {
        name: tensor.detach().clone()
        for name, tensor in tuple(model.foundation_trunk.named_parameters())
        + tuple(model.foundation_trunk.named_buffers())
    }


def _assert_foundation_snapshot(
    model: FrozenFoundationV4SharedPolicyValueV2,
    expected: dict[str, torch.Tensor],
) -> None:
    actual = dict(model.foundation_trunk.named_parameters())
    actual.update(dict(model.foundation_trunk.named_buffers()))
    assert set(actual) == set(expected)
    assert all(torch.equal(actual[name].detach(), value) for name, value in expected.items())


def _head_and_foundation_alias_view(
    model: FrozenFoundationV4SharedPolicyValueV2,
) -> tuple[torch.nn.Parameter, torch.Tensor]:
    for head in model.head_parameters():
        for foundation in model.foundation_trunk.parameters():
            if foundation.numel() >= head.numel():
                alias = foundation.detach().reshape(-1)[: head.numel()].view_as(head)
                return head, alias
    raise AssertionError("test fixture requires one compatible storage alias")


def _input_output_equivalent(left: VectorANF, right: VectorANF) -> bool:
    if (
        left.input_count != right.input_count
        or left.output_count != right.output_count
    ):
        return False
    for input_order in permutations(range(left.input_count)):
        input_mapped = left.permute_inputs(input_order)
        for output_order in permutations(range(left.output_count)):
            if input_mapped.permute_outputs(output_order).outputs == right.outputs:
                return True
    return False


def test_exact_formal_v4_identity_and_fp32_digest_are_pinned() -> None:
    trunk, identity = load_frozen_foundation_v4_trunk()

    assert Path(identity.checkpoint_path) == DEFAULT_FORMAL_V4_CHECKPOINT.resolve()
    assert identity.checkpoint_sha256 == FORMAL_V4_CHECKPOINT_SHA256
    assert len(identity.tensor_sha256) == 64
    assert identity.parameter_count == 10016
    assert identity.provenance_schema == "xa.foundation-checkpoint-provenance.v4"
    assert identity.profile == "formal"
    assert identity.seed == 20260904
    assert (identity.in_channels, identity.hidden, identity.layers) == (12, 32, 2)
    assert identity.initialization == "seeded_random_from_scratch"
    assert identity.foundation_training_completed is True
    assert identity.foundation_performance is False
    assert trunk.training is False
    assert all(parameter.dtype == torch.float32 for parameter in trunk.parameters())
    assert all(parameter.requires_grad is False for parameter in trunk.parameters())


def test_checkpoint_sha_mismatch_fails_before_loading(tmp_path: Path) -> None:
    tampered = tmp_path / "tampered-formal-v4.pt"
    payload = bytearray(DEFAULT_FORMAL_V4_CHECKPOINT.read_bytes())
    payload[-1] ^= 0x01
    tampered.write_bytes(payload)

    with pytest.raises(ValueError, match="checkpoint SHA-256 mismatch"):
        load_frozen_foundation_v4_trunk(tampered)


@pytest.mark.parametrize(
    "hook_kind",
    ("forward", "forward_pre", "backward", "state_dict"),
)
def test_foundation_hooks_are_rejected_before_execution(hook_kind: str) -> None:
    model = _model()
    trunk = model.foundation_trunk
    if hook_kind == "forward":
        trunk.register_forward_hook(lambda _module, _inputs, output: output)
    elif hook_kind == "forward_pre":
        trunk.input_proj.register_forward_pre_hook(
            lambda _module, inputs: inputs
        )
    elif hook_kind == "backward":
        trunk.blocks[0].register_full_backward_hook(
            lambda _module, grad_input, _grad_output: grad_input
        )
    elif hook_kind == "state_dict":
        trunk.out_norm.register_state_dict_post_hook(
            lambda _module, _state, _prefix, _metadata: None
        )
    else:  # pragma: no cover - parameter table is closed above.
        raise AssertionError(hook_kind)

    with pytest.raises(RuntimeError, match="foundation hooks are forbidden"):
        model.assert_foundation_integrity()


def test_foundation_instance_and_class_forward_overrides_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance_model = _model()
    instance_model.foundation_trunk.forward = (  # type: ignore[method-assign]
        lambda state, *_args, **_kwargs: torch.zeros_like(state)
    )
    with pytest.raises(RuntimeError, match="instance execution override"):
        instance_model.assert_foundation_integrity()

    class_model = _model()
    monkeypatch.setattr(
        EquivariantTrunk,
        "forward",
        lambda self, state, *_args, **_kwargs: torch.zeros_like(state),
    )
    with pytest.raises(RuntimeError, match="class forward changed"):
        class_model.assert_foundation_integrity()


@pytest.mark.parametrize("operator_name", ("linear", "layer_norm", "gelu"))
def test_conditional_functional_operator_replacement_fails_before_task_forward(
    operator_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _model()
    original = getattr(torch_functional, operator_name)

    def conditional_wrapper(
        inputs: torch.Tensor, *args: object, **kwargs: object
    ) -> torch.Tensor:
        result = original(inputs, *args, **kwargs)
        if inputs.dim() >= 2 and tuple(inputs.shape[:2]) == (3, 4):
            return result
        return torch.zeros_like(result)

    monkeypatch.setattr(torch_functional, operator_name, conditional_wrapper)
    before = model.foundation_task_forward_count
    with pytest.raises(RuntimeError, match="functional operator changed"):
        model.forward_one(_vector(), _actions(_vector()))
    assert model.foundation_task_forward_count == before


@pytest.mark.parametrize("entrypoint", ("prepare_head_inputs", "forward_one"))
def test_duck_typed_weights_property_cannot_install_one_shot_hook(
    entrypoint: str,
) -> None:
    model = _model()
    vector = _vector()
    actions = _actions(vector)[:3]

    class MaliciousWeightsLike:
        accesses = 0

        @property
        def t(self) -> float:
            self.accesses += 1
            holder: dict[str, torch.utils.hooks.RemovableHandle] = {}

            def one_shot_hook(
                _module: torch.nn.Module,
                _inputs: tuple[torch.Tensor, ...],
                output: torch.Tensor,
            ) -> torch.Tensor:
                holder["handle"].remove()
                return torch.zeros_like(output)

            holder["handle"] = model.foundation_trunk.register_forward_hook(
                one_shot_hook
            )
            return 1.0

        cnot = 0.04
        depth = 0.015
        gates = 0.01
        ancilla = 2.0

    malicious = MaliciousWeightsLike()
    before = model.foundation_task_forward_count
    with pytest.raises(TypeError, match="exact SharedUtilityWeights"):
        getattr(model, entrypoint)(vector, actions, weights=malicious)

    assert malicious.accesses == 0
    assert not model.foundation_trunk._forward_hooks
    assert model.foundation_task_forward_count == before
    model.assert_foundation_integrity()


def test_public_inputs_require_exact_active_immutable_dataclasses() -> None:
    model = _model()
    vector = _vector()
    action = _actions(vector)[0]

    class VectorSubclass(VectorANF):
        pass

    class ActionSubclass(MonomialSharedAction):
        pass

    with pytest.raises(TypeError, match="exact VectorANF"):
        model.prepare_head_inputs(
            VectorSubclass(vector.input_count, vector.outputs), (action,)
        )
    assert isinstance(action, MonomialSharedAction)
    with pytest.raises(TypeError, match="actions must contain exact"):
        model.forward_one(
            vector, (ActionSubclass(action.monomial, action.targets),)
        )


def test_canonical_weight_copy_revalidates_finite_fields_before_integrity() -> None:
    model = _model()
    vector = _vector()
    weights = SharedUtilityWeights()
    object.__setattr__(weights, "t", float("nan"))
    before = model.foundation_task_forward_count

    with pytest.raises(ValueError, match="must be finite"):
        model.forward_one(vector, _actions(vector)[:2], weights=weights)

    assert model.foundation_task_forward_count == before
    model.assert_foundation_integrity()


def test_equivariant_helper_replacement_fails_before_task_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _model()
    original = foundation_equivariant.masked_pool

    def conditional_wrapper(
        values: torch.Tensor, *args: object, **kwargs: object
    ) -> object:
        pooled = original(values, *args, **kwargs)
        if values.dim() >= 2 and tuple(values.shape[:2]) == (3, 4):
            return pooled
        return tuple(torch.zeros_like(item) for item in pooled)

    monkeypatch.setattr(
        foundation_equivariant, "masked_pool", conditional_wrapper
    )
    with pytest.raises(RuntimeError, match="equivariant helper changed"):
        model.assert_foundation_integrity()


def test_union_term_state_calls_foundation_trunk_exactly_once() -> None:
    vector = _vector()
    actions = _actions(vector)
    model = _model()
    before = model.foundation_task_forward_count

    model.forward_one(vector, actions)

    assert model.foundation_task_forward_count == before + 1


def test_non_global_term_replacement_does_not_alias_before_heads() -> None:
    # No single input-variable permutation maps A to B: their variable-degree
    # multisets are (4,2,2,0) and (3,3,1,1), respectively.
    vector_a = VectorANF(
        4,
        (
            frozenset({1, 3, 7}),
            frozenset({5}),
            frozenset({5}),
        ),
    )
    vector_b = VectorANF(
        4,
        (
            frozenset({1, 3, 7}),
            frozenset({10}),
            frozenset({10}),
        ),
    )
    model = _model()
    before_a = model.prepare_head_inputs(
        vector_a, (MonomialSharedAction(5, (1, 2)),)
    ).joint_representation()
    before_b = model.prepare_head_inputs(
        vector_b, (MonomialSharedAction(10, (1, 2)),)
    ).joint_representation()

    assert before_a.shape == before_b.shape
    assert not torch.allclose(before_a, before_b, atol=1.0e-7, rtol=1.0e-7)


@torch.no_grad()
def test_joint_cells_bind_output_term_input_relation_for_audit_counterexample() -> None:
    full = frozenset(range(8))
    vector_a = VectorANF(
        3,
        (frozenset({5, 7}), frozenset({1, 7}), full),
    )
    vector_b = VectorANF(
        3,
        (frozenset({6, 7}), frozenset({1, 7}), full),
    )
    action = MonomialSharedAction(7, (0, 1))
    model = _model()

    assert not _input_output_equivalent(vector_a, vector_b)
    inputs_a = model.prepare_head_inputs(vector_a, (action,))
    inputs_b = model.prepare_head_inputs(vector_b, (action,))
    logits_a, value_a = model.forward_one(vector_a, (action,))
    logits_b, value_b = model.forward_one(vector_b, (action,))

    expected_shape = (3, 8, 3, model.joint_hidden)
    assert tuple(inputs_a.joint_hidden.shape) == expected_shape
    assert tuple(inputs_b.joint_hidden.shape) == expected_shape
    assert not torch.allclose(
        inputs_a.joint_representation(),
        inputs_b.joint_representation(),
        atol=1.0e-7,
        rtol=1.0e-7,
    )
    final_a = torch.cat((logits_a, value_a.unsqueeze(0)))
    final_b = torch.cat((logits_b, value_b.unsqueeze(0)))
    assert not torch.allclose(final_a, final_b)


@torch.no_grad()
def test_random_local_relation_changes_do_not_alias() -> None:
    rng = random.Random(20260909)
    full = frozenset(range(8))
    model = _model()
    accepted = 0
    attempts = 0
    while accepted < 24 and attempts < 500:
        attempts += 1
        left_term, right_term = rng.sample(range(1, 7), 2)
        anchor = rng.choice(range(1, 7))
        left = VectorANF(
            3,
            (
                frozenset({left_term, 7}),
                frozenset({anchor, 7}),
                full,
            ),
        )
        right = VectorANF(
            3,
            (
                frozenset({right_term, 7}),
                frozenset({anchor, 7}),
                full,
            ),
        )
        if _input_output_equivalent(left, right):
            continue
        action = MonomialSharedAction(7, (0, 1))
        left_inputs = model.prepare_head_inputs(left, (action,))
        right_inputs = model.prepare_head_inputs(right, (action,))
        left_logits, left_value = model.forward_one(left, (action,))
        right_logits, right_value = model.forward_one(right, (action,))
        assert not torch.allclose(
            left_inputs.joint_representation(),
            right_inputs.joint_representation(),
            atol=1.0e-7,
            rtol=1.0e-7,
        )
        assert not torch.allclose(
            torch.cat((left_logits, left_value.unsqueeze(0))),
            torch.cat((right_logits, right_value.unsqueeze(0))),
        )
        accepted += 1
    assert accepted == 24


def test_train_and_requires_grad_modes_never_reach_foundation() -> None:
    model = _model()
    model.train()
    model.requires_grad_(True)

    assert model.training is True
    assert model.policy_head.training is True
    assert model.value_head.training is True
    assert model.foundation_trunk.training is False
    assert all(
        parameter.requires_grad is False
        for parameter in model.foundation_trunk.parameters()
    )
    assert model.assert_foundation_integrity() == (
        model.foundation_identity.tensor_sha256
    )


def test_optimizer_and_backward_update_heads_only() -> None:
    vector = _vector()
    actions = _actions(vector)[:5]
    model = _model()
    model.train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    optimiser_ids = {
        id(parameter)
        for group in optimiser.param_groups
        for parameter in group["params"]
    }
    head_ids = {id(parameter) for parameter in model.head_parameters()}
    foundation_ids = {id(parameter) for parameter in model.foundation_trunk.parameters()}
    digest_before = model.assert_foundation_integrity()
    assert model.head_training_status == "initialized"

    logits, value = model.forward_one(vector, actions)
    loss = logits.square().mean() + value.square()
    optimiser.zero_grad()
    loss.backward()
    optimiser.step()

    assert optimiser_ids == head_ids
    assert optimiser_ids.isdisjoint(foundation_ids)
    assert sum(parameter.numel() for parameter in model.head_parameters()) < sum(
        parameter.numel() for parameter in model.foundation_trunk.parameters()
    )
    assert all(parameter.grad is None for parameter in model.foundation_trunk.parameters())
    assert model.assert_foundation_integrity() == digest_before
    assert model.head_training_status == "modified_unsealed"
    assert model.metadata()["head_training_status"] == "modified_unsealed"


def test_modified_unsealed_head_checkpoint_save_is_rejected(tmp_path: Path) -> None:
    model = _model()
    with torch.no_grad():
        next(iter(model.policy_head.parameters())).add_(0.25)

    assert model.head_training_status == "modified_unsealed"
    with pytest.raises(RuntimeError, match="modified_unsealed"):
        model.save_head_checkpoint(tmp_path / "forbidden.pt")
    assert not (tmp_path / "forbidden.pt").exists()


def test_optimizer_step_revalidates_foundation_before_mutation() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    with torch.no_grad():
        next(model.foundation_trunk.parameters()).add_(1.0)

    with pytest.raises(RuntimeError, match="tensor digest changed"):
        optimiser.step()


def test_optimizer_constructor_and_parameter_groups_are_head_only() -> None:
    model = _model().train().requires_grad_(True)
    with pytest.raises(ValueError, match="exactly E6-v2 heads"):
        HeadOnlyIntegrityAdamW(
            model,
            tuple(model.foundation_trunk.parameters()),
            learning_rate=1.0e-3,
            weight_decay=1.0e-4,
        )

    optimiser = build_head_only_optimizer(model)
    with pytest.raises(RuntimeError, match="parameter groups are frozen"):
        optimiser.add_param_group(
            {"params": [next(model.foundation_trunk.parameters())]}
        )


def test_optimizer_rejects_direct_group_injection_before_step() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    optimiser.param_groups[0]["params"].append(
        next(model.foundation_trunk.parameters())
    )

    with pytest.raises(RuntimeError, match="parameter identity changed"):
        optimiser.step()


def test_optimizer_closure_is_rejected_without_execution() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    called = False

    def malicious_closure() -> torch.Tensor:
        nonlocal called
        called = True
        with torch.no_grad():
            next(model.foundation_trunk.parameters()).add_(1.0)
        return torch.tensor(0.0)

    digest = model.assert_foundation_integrity()
    with pytest.raises(ValueError, match="closures are forbidden"):
        optimiser.step(malicious_closure)
    assert called is False
    assert model.assert_foundation_integrity() == digest


def test_zero_grad_rejects_foundation_storage_aliased_gradient() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    head, alias = _head_and_foundation_alias_view(model)
    snapshot = _foundation_snapshot(model)
    head.grad = alias

    with pytest.raises(ValueError, match="set_to_none=True"):
        optimiser.zero_grad(set_to_none=False)
    _assert_foundation_snapshot(model, snapshot)
    with pytest.raises(RuntimeError, match="storage aliases frozen foundation"):
        optimiser.zero_grad(set_to_none=True)
    _assert_foundation_snapshot(model, snapshot)


def test_step_rejects_head_data_aliased_to_foundation_before_mutation() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    head, alias = _head_and_foundation_alias_view(model)
    snapshot = _foundation_snapshot(model)
    head.data = alias

    with pytest.raises(RuntimeError, match="storage aliases frozen foundation"):
        optimiser.step()
    _assert_foundation_snapshot(model, snapshot)


def test_step_rejects_adam_state_aliased_to_foundation_before_mutation() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)
    for parameter in model.head_parameters():
        parameter.grad = torch.zeros_like(parameter)
    optimiser.step()
    optimiser.zero_grad()

    head, alias = _head_and_foundation_alias_view(model)
    assert "exp_avg" in optimiser.state[head]
    optimiser.state[head]["exp_avg"] = alias
    snapshot = _foundation_snapshot(model)

    with pytest.raises(RuntimeError, match="storage aliases frozen foundation"):
        optimiser.step()
    _assert_foundation_snapshot(model, snapshot)


def test_optimizer_state_loading_is_deferred_to_future_sealed_schema() -> None:
    model = _model().train().requires_grad_(True)
    optimiser = build_head_only_optimizer(model)

    with pytest.raises(RuntimeError, match="future sealed schema"):
        optimiser.load_state_dict(optimiser.state_dict())


def test_state_dict_is_head_only_and_foundation_injection_always_fails() -> None:
    model = _model()
    state = model.state_dict()

    assert set(key for key in state if key.startswith("_pinned_")) == {
        "_pinned_checkpoint_sha256",
        "_pinned_foundation_tensor_sha256",
        "_pinned_foundation_parameter_count",
    }
    assert any(key.startswith("policy_head.") for key in state)
    assert any(key.startswith("value_head.") for key in state)
    assert not any("foundation_trunk" in key for key in state)

    poisoned = OrderedDict(state)
    poisoned["foundation_trunk.input_proj.elem.weight"] = torch.zeros(1)
    with pytest.raises(RuntimeError, match="forbids foundation keys"):
        model.load_state_dict(poisoned, strict=False)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("delete_pinned", "nested state contract mismatch"),
        ("tamper_pinned", "pinned identity mismatch"),
        ("inject_foundation", "forbids foundation keys"),
        ("change_head", "modified/unsealed heads"),
    ),
)
def test_nested_strict_false_load_is_fail_closed(
    mutation: str, message: str
) -> None:
    source = _NestedWrapper()
    state = OrderedDict(
        (key, tensor.detach().clone())
        for key, tensor in source.state_dict().items()
    )
    if mutation == "delete_pinned":
        del state["shared._pinned_checkpoint_sha256"]
    elif mutation == "tamper_pinned":
        state["shared._pinned_checkpoint_sha256"][0] ^= 1
    elif mutation == "inject_foundation":
        state["shared.foundation_trunk.input_proj.elem.weight"] = torch.zeros(1)
    elif mutation == "change_head":
        key = next(key for key in state if key.startswith("shared.joint_adapter."))
        state[key].view(-1)[0] += 1.0
    else:  # pragma: no cover - the parameter table is closed above.
        raise AssertionError(mutation)

    target = _NestedWrapper()
    with pytest.raises(RuntimeError, match=message):
        target.load_state_dict(state, strict=False)


def test_nested_exact_initialized_state_loads_under_parent() -> None:
    source = _NestedWrapper()
    target = _NestedWrapper()

    result = target.load_state_dict(source.state_dict(), strict=False)

    assert result.missing_keys == []
    assert result.unexpected_keys == []
    assert target.shared.head_training_status == "initialized"
    target.shared.assert_foundation_integrity()


def test_nested_load_cannot_reset_a_modified_target_head() -> None:
    source = _NestedWrapper()
    target = _NestedWrapper()
    with torch.no_grad():
        next(target.shared.policy_head.parameters()).add_(0.5)

    with pytest.raises(RuntimeError, match="target is modified/unsealed"):
        target.load_state_dict(source.state_dict(), strict=False)


def test_assign_true_load_is_rejected_directly_and_when_nested() -> None:
    direct = _model()
    with pytest.raises(ValueError, match=r"assign=True"):
        direct.load_state_dict(direct.state_dict(), assign=True)

    source = _NestedWrapper()
    target = _NestedWrapper()
    with pytest.raises(RuntimeError, match=r"nested assign=True"):
        target.load_state_dict(source.state_dict(), strict=False, assign=True)


def test_pinned_identity_tampering_and_foundation_replacement_fail_closed() -> None:
    model = _model()
    state = OrderedDict(model.state_dict())
    state["_pinned_checkpoint_sha256"] = state[
        "_pinned_checkpoint_sha256"
    ].clone()
    state["_pinned_checkpoint_sha256"][0] ^= 1
    with pytest.raises(RuntimeError, match="pinned identity mismatch"):
        model.load_state_dict(state)

    with pytest.raises(AttributeError, match="cannot be replaced"):
        model._foundation_trunk = torch.nn.Identity()  # type: ignore[misc]


def test_safe_device_migration_revalidates_and_dtype_conversion_is_forbidden() -> None:
    model = _model()
    digest = model.assert_foundation_integrity()
    assert model.cpu() is model
    if torch.backends.mps.is_available():
        with pytest.raises(ValueError, match="CPU-only"):
            model.to(device=torch.device("mps"))
        assert next(model.policy_head.parameters()).device.type == "cpu"
        assert next(model.foundation_trunk.parameters()).device.type == "cpu"
    assert model.assert_foundation_integrity() == digest
    assert model._pinned_checkpoint_sha256.dtype == torch.uint8
    assert model._pinned_foundation_tensor_sha256.dtype == torch.uint8
    assert model._pinned_foundation_parameter_count.dtype == torch.int64

    with pytest.raises(ValueError, match="must remain FP32"):
        model.to(dtype=torch.float64)
    with pytest.raises(ValueError, match="must remain FP32"):
        model.double()
    with pytest.raises(ValueError, match=r"\.type"):
        model.type(torch.FloatTensor)
    assert model.assert_foundation_integrity() == digest


@torch.no_grad()
def test_head_checkpoint_roundtrip_keeps_split_metadata(tmp_path: Path) -> None:
    vector = _vector()
    actions = _actions(vector)
    model = _model()
    expected_logits, expected_value = model.forward_one(vector, actions)
    checkpoint = tmp_path / "e6-v2-head.pt"

    model.save_head_checkpoint(checkpoint)
    restored = FrozenFoundationV4SharedPolicyValueV2.from_head_checkpoint(checkpoint)
    actual_logits, actual_value = restored.forward_one(vector, actions)
    metadata = restored.metadata()

    assert actual_logits.tolist() == pytest.approx(
        expected_logits.tolist(), abs=0.0, rel=0.0
    )
    assert float(actual_value) == pytest.approx(
        float(expected_value), abs=0.0, rel=0.0
    )
    assert metadata["foundation_training_completed"] is True
    assert metadata["foundation_performance"] is False
    assert metadata["head_training_status"] == "initialized"
    assert metadata["active_trainer_connected"] is False
    assert metadata["modified_checkpoint_policy"] == (
        "rejected_requires_future_sealed_schema"
    )
    assert metadata["execution_device_contract"] == "fresh_process_cpu_only"
    assert metadata["threat_model"] == THREAT_MODEL
    assert "training_performed" not in metadata


def test_head_checkpoint_uses_weights_only_and_rejects_pickle_execution(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "malicious.pt"
    marker = tmp_path / "pickle-executed.txt"
    torch.save(_MaliciousCheckpointPayload(marker), checkpoint)

    with pytest.raises(pickle.UnpicklingError):
        FrozenFoundationV4SharedPolicyValueV2.from_head_checkpoint(checkpoint)
    assert not marker.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("head_hidden", True),
        ("head_seed", "20260907"),
        ("foundation_parameter_count", torch.tensor(10_016)),
        ("joint_hidden", torch.tensor(24)),
        ("foundation_training_completed", 1),
        ("foundation_performance", 0),
    ),
)
def test_head_checkpoint_rejects_non_native_integer_metadata(
    tmp_path: Path, field: str, value: object
) -> None:
    checkpoint = tmp_path / "valid.pt"
    tampered = tmp_path / f"tampered-{field}.pt"
    _model().save_head_checkpoint(checkpoint)
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    payload["metadata"] = {**payload["metadata"], field: value}
    torch.save(payload, tampered)

    with pytest.raises(ValueError, match=f"{field} must be a native"):
        FrozenFoundationV4SharedPolicyValueV2.from_head_checkpoint(tampered)


@torch.no_grad()
def test_output_permutation_preserves_aligned_policy_logits_and_value() -> None:
    vector = _vector()
    actions = _actions(vector)
    model = _model()
    logits, value = model.forward_one(vector, actions)

    old_to_new = (2, 0, 1)
    permuted_vector = vector.permute_outputs(old_to_new)
    permuted_actions = tuple(
        permute_action_outputs(
            action,
            old_to_new,
            output_count=vector.output_count,
        )
        for action in actions
    )
    permuted_logits, permuted_value = model.forward_one(
        permuted_vector, permuted_actions
    )

    assert permuted_logits.tolist() == pytest.approx(
        logits.tolist(), abs=TOL, rel=TOL
    )
    assert float(permuted_value) == pytest.approx(float(value), abs=TOL, rel=TOL)


@torch.no_grad()
def test_input_variable_permutation_preserves_aligned_logits_and_value() -> None:
    vector = _vector()
    actions = _actions(vector)
    model = _model()
    logits, value = model.forward_one(vector, actions)

    old_to_new = (1, 2, 0)
    permuted_vector = vector.permute_inputs(old_to_new)
    permuted_actions = tuple(
        permute_action_inputs(
            action,
            old_to_new,
            input_count=vector.input_count,
        )
        for action in actions
    )
    permuted_logits, permuted_value = model.forward_one(
        permuted_vector, permuted_actions
    )

    assert permuted_logits.tolist() == pytest.approx(
        logits.tolist(), abs=TOL, rel=TOL
    )
    assert float(permuted_value) == pytest.approx(float(value), abs=TOL, rel=TOL)


@torch.no_grad()
def test_candidate_reordering_only_reorders_logits() -> None:
    vector = _vector()
    actions = _actions(vector)
    model = _model()
    logits, value = model.forward_one(vector, actions)
    order = tuple(reversed(range(len(actions))))

    reordered, reordered_value = model.forward_one(
        vector,
        tuple(actions[index] for index in order),
    )

    assert reordered.tolist() == pytest.approx(
        [float(logits[index]) for index in order], abs=TOL, rel=TOL
    )
    assert float(reordered_value) == pytest.approx(float(value), abs=0.0, rel=0.0)


@torch.no_grad()
def test_empty_action_pool_and_constant_action_are_total() -> None:
    vector = VectorANF(
        3,
        (
            frozenset({0}),
            frozenset({0}),
            frozenset(),
        ),
    )
    action = MonomialSharedAction(0, (0, 1))
    model = _model()

    empty_logits, empty_value = model.forward_one(vector, ())
    logits, value = model.forward_one(vector, (action,))

    assert empty_logits.shape == (0,)
    assert logits.shape == (1,)
    assert torch.isfinite(empty_value)
    assert torch.isfinite(value)
    assert -3.0 <= float(value) <= 0.0


def test_claim_boundary_and_active_trainer_disconnect_are_explicit() -> None:
    model = _model()
    metadata = model.metadata()

    assert "not arbitrary term identities" in SYMMETRY_CONTRACT
    assert "not connected to the active trainer" in CLAIM_BOUNDARY
    assert model.foundation_training_completed is True
    assert model.foundation_performance is False
    assert model.head_training_status == "initialized"
    assert model.head_formal_evaluation is False
    assert model.head_performance is False
    assert model.active_trainer_connected is False
    assert not hasattr(model, "training_performed")
    assert not hasattr(model, "fit")
    assert metadata["active_trainer_connected"] is False
