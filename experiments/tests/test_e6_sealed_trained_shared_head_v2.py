#!/usr/bin/env python3
"""Adversarial contracts for the development E6-v2 trained-head seal."""

from __future__ import annotations

import hashlib
from pathlib import Path
import pickle

import pytest
import torch

import e6.shared_model as shared_model_module
from e6.frozen_foundation_v4_shared_head_v2 import (
    FORMAL_V4_CHECKPOINT_SHA256,
    FrozenFoundationV4SharedPolicyValueV2,
)
from e6.sealed_trained_shared_head_v2 import (
    SEALED_HEAD_STATUS,
    SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA,
    TRAINING_REPORT_BINDING_V2_SCHEMA,
    SealedTrainedSharedHeadV2,
    build_trained_head_suite_manifest_payload_v2,
    clone_trained_head_state_v2,
    load_sealed_trained_shared_head_v2 as _load_sealed_trained_shared_head_v2,
    seal_trained_shared_head_v2,
    trained_head_suite_manifest_sha256_v2,
)
from e6.shared_oracle import VectorANF, enumerate_monomial_shared_actions
from src.contracts.codec import sha256_file


def load_sealed_trained_shared_head_v2(
    path: str | Path,
    *,
    suite_manifest_payload: dict[str, object],
    expected_suite_manifest_sha256: str,
) -> SealedTrainedSharedHeadV2:
    """Authenticate the exact test artifact before exercising semantic checks."""

    checkpoint = Path(path)
    return _load_sealed_trained_shared_head_v2(
        checkpoint,
        suite_manifest_payload=suite_manifest_payload,
        expected_suite_manifest_sha256=expected_suite_manifest_sha256,
        expected_checkpoint_sha256=sha256_file(checkpoint),
    )


class _MaliciousCheckpointPayload:
    def __init__(self, marker: Path) -> None:
        self.marker = str(marker)

    def __reduce__(self):
        expression = (
            "__import__('pathlib').Path(" + repr(self.marker) + ")"
            ".write_text('executed', encoding='utf-8')"
        )
        return eval, (expression,)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _vector_and_actions():
    vector = VectorANF(
        6,
        (
            frozenset({0b000111, 0b001011, 0b010101, 0b100001}),
            frozenset({0b000111, 0b001011, 0b011001, 0b100010}),
            frozenset({0b000111, 0b010101, 0b011001, 0b100100}),
        ),
    )
    actions = enumerate_monomial_shared_actions(vector)
    assert len(actions) >= 4
    return vector, actions


def _report(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": TRAINING_REPORT_BINDING_V2_SCHEMA,
        "training_run_id": "unit/e6-v2-sealed-trained-head",
        "report_payload_sha256": _sha("training-report-payload"),
        "trainer_source_sha256": _sha("trainer-source"),
        "training_source_manifest_sha256": _sha("training-source-manifest"),
        "split_registry_sha256": _sha("split-registry"),
        "case_roster_sha256": _sha("case-roster"),
        "foundation_checkpoint_sha256": metadata[
            "foundation_checkpoint_sha256"
        ],
        "initial_head_tensor_sha256": metadata[
            "head_initial_tensor_sha256"
        ],
        "final_head_tensor_sha256": metadata["head_current_tensor_sha256"],
        "source_arm": "classical_greedy_repeated_selection_replay",
        "sample_count": 2,
        "update_steps": 4,
        "training_completed": True,
        "formal_evaluation": False,
        "performance_evidence": False,
    }


def _materials():
    model = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=24,
        head_seed=20260907,
    )
    model.eval()
    with torch.no_grad():
        next(model.policy_head.parameters()).view(-1)[0].add_(0.125)
        next(model.value_head.parameters()).view(-1)[0].sub_(0.0625)
    assert model.head_training_status == "modified_unsealed"
    state = clone_trained_head_state_v2(model)
    metadata = model.metadata()
    report = _report(metadata)
    suite = build_trained_head_suite_manifest_payload_v2(
        trained_head_metadata=metadata,
        training_report_binding=report,
    )
    suite_sha = trained_head_suite_manifest_sha256_v2(suite)
    return model, state, metadata, report, suite, suite_sha


def _seal(tmp_path: Path):
    model, state, metadata, report, suite, suite_sha = _materials()
    path = tmp_path / "sealed-trained-head.pt"
    file_sha = seal_trained_shared_head_v2(
        path,
        head_state=state,
        trained_head_metadata=metadata,
        training_report_binding=report,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    return path, model, state, metadata, report, suite, suite_sha, file_sha


def _tamper_checkpoint(source: Path, target: Path, mutate) -> None:
    payload = torch.load(source, map_location="cpu", weights_only=True)
    mutate(payload)
    torch.save(payload, target)


@torch.no_grad()
def test_seal_load_roundtrip_is_forward_exact_and_externally_bound(
    tmp_path: Path,
) -> None:
    path, source, state, metadata, report, suite, suite_sha, file_sha = _seal(
        tmp_path
    )
    vector, actions = _vector_and_actions()
    expected_logits, expected_value = source.forward_one(vector, actions)

    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    actual_logits, actual_value = sealed.forward_one(vector, actions)
    sealed_metadata = sealed.metadata()

    assert isinstance(sealed, SealedTrainedSharedHeadV2)
    assert actual_logits.tolist() == pytest.approx(
        expected_logits.tolist(), abs=0.0, rel=0.0
    )
    assert float(actual_value) == pytest.approx(
        float(expected_value), abs=0.0, rel=0.0
    )
    assert actual_logits.requires_grad is False
    assert actual_value.requires_grad is False
    assert file_sha == sha256_file(path)
    assert sealed_metadata["schema_version"] == SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA
    assert sealed_metadata["suite_manifest_sha256"] == suite_sha
    assert sealed_metadata["head_training_status"] == SEALED_HEAD_STATUS
    assert sealed_metadata["artifact_role"] == (
        "trained_head_weights_only_development"
    )
    assert sealed_metadata["training_completed"] is True
    assert sealed_metadata["embedded_metadata_role"] == (
        "base_model_contract_snapshot_not_artifact_claim"
    )
    assert "training completed" in sealed_metadata["claim_boundary"]
    assert sealed_metadata["trained_head_tensor_sha256"] == metadata[
        "head_current_tensor_sha256"
    ]
    assert sealed_metadata["inference_only"] is True
    assert sealed_metadata["optimizer_resume_supported"] is False
    assert sealed_metadata["formal_evaluation"] is False
    assert sealed_metadata["performance_evidence"] is False

    payload = torch.load(path, map_location="cpu", weights_only=True)
    assert set(payload["head_state"]) == set(state)
    assert not any("foundation" in key for key in payload["head_state"])
    assert payload["training_report_binding"] == report


def test_wrapper_exposes_no_optimizer_resume_or_training_surface(
    tmp_path: Path,
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )

    assert sealed.inference_only is True
    assert sealed.head_training_status == SEALED_HEAD_STATUS
    for method, args in (
        (sealed.train, ()),
        (sealed.requires_grad_, (True,)),
        (sealed.parameters, ()),
        (sealed.state_dict, ()),
        (sealed.load_state_dict, ({},)),
    ):
        with pytest.raises(RuntimeError, match="inference-only|optimizer|resume"):
            method(*args)
    assert not hasattr(sealed, "optimizer")
    assert not hasattr(sealed, "fit")
    assert not hasattr(sealed, "resume")


@pytest.mark.parametrize(
    "slot_name,replacement",
    (
        (
            "_SealedTrainedSharedHeadV2__model_forward",
            lambda *_args, **_kwargs: (
                torch.full((1,), 123.0),
                torch.tensor(456.0),
            ),
        ),
        ("_SealedTrainedSharedHeadV2__trained_digest", "0" * 64),
        ("_SealedTrainedSharedHeadV2__head_tensor_bindings", ()),
        ("_SealedTrainedSharedHeadV2__metadata", {}),
        ("_SealedTrainedSharedHeadV2__model_class_callables", ()),
    ),
)
def test_wrapper_pinned_slots_are_immutable(
    tmp_path: Path, slot_name: str, replacement: object
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    before = sealed.assert_integrity()

    with pytest.raises(AttributeError, match="wrapper is immutable"):
        setattr(sealed, slot_name, replacement)
    with pytest.raises(AttributeError, match="wrapper is immutable"):
        delattr(sealed, slot_name)

    assert sealed.assert_integrity() == before


def test_every_forward_rechecks_trained_head_digest(tmp_path: Path) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    underlying = sealed._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    with torch.no_grad():
        next(underlying.policy_head.parameters()).view(-1)[0].add_(1.0)

    vector, actions = _vector_and_actions()
    with pytest.raises(RuntimeError, match="trained head tensor digest changed"):
        sealed.forward_one(vector, actions)


def test_sealed_execution_path_rejects_hooks_and_instance_overrides(
    tmp_path: Path,
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    underlying = sealed._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    underlying.policy_head.register_forward_hook(
        lambda _module, _inputs, output: torch.zeros_like(output)
    )
    vector, actions = _vector_and_actions()
    with pytest.raises(RuntimeError, match="hooks are forbidden"):
        sealed.forward_one(vector, actions)

    path2, _, _, _, _, suite2, suite_sha2, _ = _seal(tmp_path / "override")
    sealed2 = load_sealed_trained_shared_head_v2(
        path2,
        suite_manifest_payload=suite2,
        expected_suite_manifest_sha256=suite_sha2,
    )
    underlying2 = sealed2._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    underlying2.forward_one = lambda *_args, **_kwargs: (  # type: ignore[method-assign]
        torch.tensor([123.0]),
        torch.tensor(456.0),
    )
    with pytest.raises(RuntimeError, match="instance execution override"):
        sealed2.forward_one(vector, actions)

    path3, _, _, _, _, suite3, suite_sha3, _ = _seal(tmp_path / "helper")
    sealed3 = load_sealed_trained_shared_head_v2(
        path3,
        suite_manifest_payload=suite3,
        expected_suite_manifest_sha256=suite_sha3,
    )
    underlying3 = sealed3._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    underlying3._prepare_canonical_head_inputs = (  # type: ignore[method-assign]
        lambda *_args, **_kwargs: None
    )
    with pytest.raises(RuntimeError, match="instance execution override"):
        sealed3.forward_one(vector, actions)

    path4, _, _, _, _, suite4, suite_sha4, _ = _seal(tmp_path / "tensor-reader")
    sealed4 = load_sealed_trained_shared_head_v2(
        path4,
        suite_manifest_payload=suite4,
        expected_suite_manifest_sha256=suite_sha4,
    )
    underlying4 = sealed4._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    underlying4.policy_head.named_parameters = (  # type: ignore[method-assign]
        lambda *_args, **_kwargs: iter(())
    )
    with pytest.raises(RuntimeError, match="instance execution override"):
        sealed4.assert_integrity()


def test_sealed_execution_path_rejects_shared_model_helper_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    vector, actions = _vector_and_actions()
    original = shared_model_module._broadcast_pool

    def replaced_broadcast_pool(*args, **kwargs):
        return torch.zeros_like(original(*args, **kwargs))

    monkeypatch.setattr(
        shared_model_module, "_broadcast_pool", replaced_broadcast_pool
    )
    with pytest.raises(RuntimeError, match="execution helper changed"):
        sealed.forward_one(vector, actions)


def test_state_dict_hooks_cannot_cloak_a_mutated_trained_head(
    tmp_path: Path,
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    underlying = sealed._SealedTrainedSharedHeadV2__model  # noqa: SLF001
    snapshot = {
        name: tensor.detach().clone()
        for name, tensor in underlying.policy_head.state_dict().items()
    }
    with torch.no_grad():
        next(underlying.policy_head.parameters()).view(-1)[0].add_(1.0)

    def cloak(_module, state, _prefix, _metadata) -> None:
        state.clear()
        state.update({name: tensor.clone() for name, tensor in snapshot.items()})

    underlying.policy_head.register_state_dict_post_hook(cloak)
    with pytest.raises(RuntimeError, match="hooks are forbidden"):
        sealed.assert_integrity()


def test_loader_never_calls_legacy_base_load_state_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("legacy base load_state_dict was called")

    monkeypatch.setattr(
        FrozenFoundationV4SharedPolicyValueV2,
        "load_state_dict",
        forbidden,
    )
    sealed = load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    )
    sealed.assert_integrity()


def test_legacy_initialized_checkpoint_contract_stays_closed(
    tmp_path: Path,
) -> None:
    path, _, trained_state, _, _, suite, suite_sha, _ = _seal(tmp_path)
    with pytest.raises(ValueError, match="unsupported E6-v2 head checkpoint schema"):
        FrozenFoundationV4SharedPolicyValueV2.from_head_checkpoint(path)

    legacy = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=24, head_seed=20260907
    )
    legacy_state = legacy.state_dict()
    for name, tensor in trained_state.items():
        legacy_state[name] = tensor.clone()
    with pytest.raises(RuntimeError, match="modified/unsealed heads"):
        legacy.load_state_dict(legacy_state)
    assert legacy.head_training_status == "initialized"

    # The dedicated sealed loader remains the only successful path.
    load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
    ).assert_integrity()


def test_external_suite_manifest_sha_is_the_trust_root(tmp_path: Path) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    with pytest.raises(ValueError, match="external trust root"):
        load_sealed_trained_shared_head_v2(
            path,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256="0" * 64,
        )

    drifted = {**suite, "trained_head_tensor_sha256": "1" * 64}
    with pytest.raises(ValueError, match="external trust root"):
        load_sealed_trained_shared_head_v2(
            path,
            suite_manifest_payload=drifted,
            expected_suite_manifest_sha256=suite_sha,
        )


def test_loader_requires_an_independent_exact_checkpoint_byte_anchor(
    tmp_path: Path,
) -> None:
    path, _, _, _, _, suite, suite_sha, file_sha = _seal(tmp_path)
    _load_sealed_trained_shared_head_v2(
        path,
        suite_manifest_payload=suite,
        expected_suite_manifest_sha256=suite_sha,
        expected_checkpoint_sha256=file_sha,
    ).assert_integrity()

    trailer = tmp_path / "sealed-with-untrusted-trailer.pt"
    trailer.write_bytes(path.read_bytes() + b"UNTRUSTED-TRAILER")
    with pytest.raises(ValueError, match="independent anchor"):
        _load_sealed_trained_shared_head_v2(
            trailer,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
            expected_checkpoint_sha256=file_sha,
        )

    reserialized = tmp_path / "semantically-equal-reserialized.pt"
    payload = torch.load(path, map_location="cpu", weights_only=True)
    torch.save(payload, reserialized)
    assert sha256_file(reserialized) != file_sha
    with pytest.raises(ValueError, match="independent anchor"):
        _load_sealed_trained_shared_head_v2(
            reserialized,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
            expected_checkpoint_sha256=file_sha,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("head_hidden", True),
        ("head_seed", "20260907"),
        ("foundation_parameter_count", torch.tensor(10_016)),
        ("foundation_training_completed", 1),
    ),
)
def test_trained_metadata_requires_exact_native_types(
    tmp_path: Path, field: str, value: object
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    tampered = tmp_path / f"bad-metadata-{field}.pt"

    def mutate(payload) -> None:
        payload["trained_head_metadata"] = {
            **payload["trained_head_metadata"],
            field: value,
        }

    _tamper_checkpoint(path, tampered, mutate)
    with pytest.raises(TypeError, match=f"{field} must be a native"):
        load_sealed_trained_shared_head_v2(
            tampered,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )


@pytest.mark.parametrize("mutation", ("dtype", "shape", "nonfinite", "device"))
def test_head_tensors_require_exact_cpu_fp32_finite_shapes(
    tmp_path: Path, mutation: str
) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    tampered = tmp_path / f"bad-tensor-{mutation}.pt"

    def mutate(payload) -> None:
        key = sorted(payload["head_state"])[0]
        tensor = payload["head_state"][key]
        if mutation == "dtype":
            payload["head_state"][key] = tensor.double()
        elif mutation == "shape":
            payload["head_state"][key] = tensor.reshape(-1)[:-1]
        elif mutation == "nonfinite":
            changed = tensor.clone()
            changed.reshape(-1)[0] = float("nan")
            payload["head_state"][key] = changed
        elif mutation == "device":
            payload["head_state"][key] = torch.empty_like(tensor, device="meta")
        else:  # pragma: no cover
            raise AssertionError(mutation)

    _tamper_checkpoint(path, tampered, mutate)
    with pytest.raises(ValueError, match="FP32|shape mismatch|non-finite|CPU"):
        load_sealed_trained_shared_head_v2(
            tampered,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )


def test_tensor_and_metadata_digest_tampering_fail_closed(tmp_path: Path) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    changed_tensor = tmp_path / "changed-tensor.pt"

    def mutate_tensor(payload) -> None:
        key = sorted(payload["head_state"])[0]
        payload["head_state"][key] = payload["head_state"][key].clone()
        payload["head_state"][key].reshape(-1)[0] += 1.0

    _tamper_checkpoint(path, changed_tensor, mutate_tensor)
    with pytest.raises(ValueError, match="digest mismatch"):
        load_sealed_trained_shared_head_v2(
            changed_tensor,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )

    changed_metadata = tmp_path / "changed-sealed-metadata.pt"

    def mutate_metadata(payload) -> None:
        payload["metadata"] = {
            **payload["metadata"],
            "trained_head_tensor_sha256": "0" * 64,
        }

    _tamper_checkpoint(path, changed_metadata, mutate_metadata)
    with pytest.raises(ValueError, match="metadata binding mismatch"):
        load_sealed_trained_shared_head_v2(
            changed_metadata,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )


def test_report_claims_and_binding_tamper_fail_closed(tmp_path: Path) -> None:
    path, _, _, _, _, suite, suite_sha, _ = _seal(tmp_path)
    formal = tmp_path / "false-formal-claim.pt"

    def mutate_formal(payload) -> None:
        payload["training_report_binding"] = {
            **payload["training_report_binding"],
            "formal_evaluation": True,
        }

    _tamper_checkpoint(path, formal, mutate_formal)
    with pytest.raises(ValueError, match="training_report_binding_sha256 binding"):
        load_sealed_trained_shared_head_v2(
            formal,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )

    _, state, metadata, report, _, _ = _materials()
    report = {**report, "formal_evaluation": True}
    self_consistent_suite = build_trained_head_suite_manifest_payload_v2(
        trained_head_metadata=metadata,
        training_report_binding=report,
    )
    self_consistent_sha = trained_head_suite_manifest_sha256_v2(
        self_consistent_suite
    )
    with pytest.raises(ValueError, match="cannot claim formal evaluation"):
        seal_trained_shared_head_v2(
            tmp_path / "self-consistent-false-claim.pt",
            head_state=state,
            trained_head_metadata=metadata,
            training_report_binding=report,
            suite_manifest_payload=self_consistent_suite,
            expected_suite_manifest_sha256=self_consistent_sha,
        )

    rebound = tmp_path / "self-rebound-report.pt"

    def mutate_binding(payload) -> None:
        payload["training_report_binding"] = {
            **payload["training_report_binding"],
            "report_payload_sha256": _sha("attacker-report"),
        }

    _tamper_checkpoint(path, rebound, mutate_binding)
    with pytest.raises(ValueError, match="training_report_binding_sha256 binding"):
        load_sealed_trained_shared_head_v2(
            rebound,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )


def test_loader_uses_weights_only_and_rejects_pickle_execution(
    tmp_path: Path,
) -> None:
    _, _, _, _, suite, suite_sha = _materials()
    checkpoint = tmp_path / "malicious.pt"
    marker = tmp_path / "pickle-executed.txt"
    torch.save(_MaliciousCheckpointPayload(marker), checkpoint)

    with pytest.raises(pickle.UnpicklingError):
        load_sealed_trained_shared_head_v2(
            checkpoint,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )
    assert not marker.exists()


def test_seal_requires_detached_clones_and_never_overwrites(
    tmp_path: Path,
) -> None:
    _, state, metadata, report, suite, suite_sha = _materials()
    key = sorted(state)[0]
    state[key] = state[key].clone().requires_grad_(True)
    rejected = tmp_path / "rejected.pt"
    with pytest.raises(ValueError, match="detached training-party clone"):
        seal_trained_shared_head_v2(
            rejected,
            head_state=state,
            trained_head_metadata=metadata,
            training_report_binding=report,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )
    assert not rejected.exists()

    _, state, metadata, report, suite, suite_sha = _materials()
    existing = tmp_path / "existing.pt"
    existing.write_bytes(b"preserve-me")
    with pytest.raises(FileExistsError):
        seal_trained_shared_head_v2(
            existing,
            head_state=state,
            trained_head_metadata=metadata,
            training_report_binding=report,
            suite_manifest_payload=suite,
            expected_suite_manifest_sha256=suite_sha,
        )
    assert existing.read_bytes() == b"preserve-me"


def test_initialized_head_cannot_be_sealed_as_trained() -> None:
    model = FrozenFoundationV4SharedPolicyValueV2(
        head_hidden=24, head_seed=20260907
    )
    with pytest.raises(ValueError, match="modified_unsealed"):
        clone_trained_head_state_v2(model)
    assert model.foundation_identity.checkpoint_sha256 == FORMAL_V4_CHECKPOINT_SHA256
