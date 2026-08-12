#!/usr/bin/env python3
"""Externally anchored, inference-only seal for a trained E6-v2 head.

This module does not train or resume a model.  It accepts detached CPU/FP32
clones of the three trainable head submodules, binds them to strict metadata
and a strict training-report summary, and writes a development-only sealed
checkpoint.  Trust comes from a caller-supplied suite-manifest payload whose
SHA-256 is supplied independently; nothing inside the checkpoint is treated
as a self-authenticating root.

Restoration deliberately loads only ``joint_adapter``, ``policy_head`` and
``value_head``.  The legacy initialized-head checkpoint contract therefore
remains closed to modified heads.  The returned wrapper exposes inference
only, rechecking the immutable formal-v4 foundation and the exact trained-head
digest before and after every forward call.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping, Sequence

import torch

import e6.frozen_foundation_v4_shared_head_v2 as frozen_head_module
import e6.shared_model as shared_model_module
import e6.shared_oracle as shared_oracle_module
import e6.shared_scheduler as shared_scheduler_module
import src.foundation.encoding as foundation_encoding_module
from e6.frozen_foundation_v4_shared_head_v2 import (
    DEFAULT_FORMAL_V4_CHECKPOINT,
    FROZEN_SHARED_HEAD_SCHEMA,
    FrozenFoundationV4SharedPolicyValueV2,
)
from e6.shared_oracle import SharedAction, VectorANF
from e6.shared_scheduler import SharedUtilityWeights
from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file


SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA = (
    "xa.e6-sealed-trained-shared-head.v2-development"
)
TRAINING_REPORT_BINDING_V2_SCHEMA = (
    "xa.e6-trained-shared-head-report-binding.v2-development"
)
TRAINED_HEAD_SUITE_MANIFEST_V2_SCHEMA = (
    "xa.e6-trained-shared-head-suite-manifest.v2-development"
)
SEALED_HEAD_STATUS = "sealed_trained_development"
SEALED_ARTIFACT_ROLE = "trained_head_weights_only_development"
EMBEDDED_METADATA_ROLE = "base_model_contract_snapshot_not_artifact_claim"
SEALED_CLAIM_BOUNDARY = (
    "offline head-only training completed and sealed for development inference; "
    "no formal evaluation or performance evidence"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HEAD_PREFIXES = ("joint_adapter", "policy_head", "value_head")
_SOURCE_ARMS = {
    "classical_random_bitstring_replay",
    "classical_greedy_repeated_selection_replay",
    "qaoa_final_measurement_replay",
    "qaoa_permuted_label_control",
}
_MAX_SEALED_CHECKPOINT_BYTES = 16 * 1024 * 1024

# The sealed wrapper promises fail-closed development inference for the known
# E6 head execution graph. Pin module globals that class methods resolve at
# call time; changing any of them must be detected before a head forward.
_PINNED_HEAD_EXECUTION_GLOBALS = (
    (shared_model_module, "_cell_mask", shared_model_module._cell_mask),
    (shared_model_module, "_broadcast_pool", shared_model_module._broadcast_pool),
    (shared_model_module, "_POOL_AXES", shared_model_module._POOL_AXES),
    (
        shared_model_module,
        "shared_action_scalars",
        shared_model_module.shared_action_scalars,
    ),
    (
        shared_model_module,
        "validate_shared_action",
        shared_model_module.validate_shared_action,
    ),
    (
        shared_model_module,
        "action_polynomial_terms",
        shared_model_module.action_polynomial_terms,
    ),
    (
        shared_model_module,
        "shared_action_utility_breakdown",
        shared_model_module.shared_action_utility_breakdown,
    ),
    (
        shared_oracle_module,
        "validate_shared_action",
        shared_oracle_module.validate_shared_action,
    ),
    (
        shared_oracle_module,
        "action_polynomial_terms",
        shared_oracle_module.action_polynomial_terms,
    ),
    (
        shared_scheduler_module,
        "shared_action_utility_breakdown",
        shared_scheduler_module.shared_action_utility_breakdown,
    ),
    (
        foundation_encoding_module,
        "encode_state",
        foundation_encoding_module.encode_state,
    ),
    (
        frozen_head_module,
        "shared_action_scalars",
        frozen_head_module.shared_action_scalars,
    ),
    (
        frozen_head_module,
        "validate_shared_action",
        frozen_head_module.validate_shared_action,
    ),
    (
        frozen_head_module,
        "action_polynomial_terms",
        frozen_head_module.action_polynomial_terms,
    ),
    (frozen_head_module, "encode_state", frozen_head_module.encode_state),
    (
        frozen_head_module,
        "_canonicalize_public_inputs",
        frozen_head_module._canonicalize_public_inputs,
    ),
    (frozen_head_module, "_state_context", frozen_head_module._state_context),
    (frozen_head_module, "_value_scalars", frozen_head_module._value_scalars),
    (
        frozen_head_module,
        "_touched_input_indices",
        frozen_head_module._touched_input_indices,
    ),
    (
        frozen_head_module,
        "_assert_pinned_execution_globals",
        frozen_head_module._assert_pinned_execution_globals,
    ),
    (
        frozen_head_module,
        "FrozenSharedHeadInputsV2",
        frozen_head_module.FrozenSharedHeadInputsV2,
    ),
    (
        frozen_head_module,
        "_FrozenJointFeatures",
        frozen_head_module._FrozenJointFeatures,
    ),
)


def _assert_pinned_head_execution_globals() -> None:
    for module, name, expected in _PINNED_HEAD_EXECUTION_GLOBALS:
        if getattr(module, name) is not expected:
            raise RuntimeError(
                "known sealed trained-head execution helper changed: "
                f"{module.__name__}.{name}"
            )

_BASE_METADATA_TYPES: dict[str, type] = {
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

_REPORT_TYPES: dict[str, type] = {
    "schema_version": str,
    "training_run_id": str,
    "report_payload_sha256": str,
    "trainer_source_sha256": str,
    "training_source_manifest_sha256": str,
    "split_registry_sha256": str,
    "case_roster_sha256": str,
    "foundation_checkpoint_sha256": str,
    "initial_head_tensor_sha256": str,
    "final_head_tensor_sha256": str,
    "source_arm": str,
    "sample_count": int,
    "update_steps": int,
    "training_completed": bool,
    "formal_evaluation": bool,
    "performance_evidence": bool,
}

_SUITE_TYPES: dict[str, type] = {
    "schema_version": str,
    "sealed_schema_version": str,
    "base_head_schema_version": str,
    "foundation_checkpoint_sha256": str,
    "foundation_tensor_sha256": str,
    "trained_head_tensor_sha256": str,
    "trained_head_metadata_sha256": str,
    "training_report_binding_sha256": str,
    "artifact_role": str,
    "training_completed": bool,
    "embedded_metadata_role": str,
    "claim_boundary": str,
    "inference_only": bool,
    "optimizer_resume_supported": bool,
    "formal_evaluation": bool,
    "performance_evidence": bool,
}

_SEALED_METADATA_TYPES: dict[str, type] = {
    "schema_version": str,
    "suite_manifest_sha256": str,
    "base_head_schema_version": str,
    "foundation_checkpoint_sha256": str,
    "foundation_tensor_sha256": str,
    "foundation_parameter_count": int,
    "head_hidden": int,
    "joint_hidden": int,
    "head_seed": int,
    "initial_head_tensor_sha256": str,
    "trained_head_tensor_sha256": str,
    "trained_head_metadata_sha256": str,
    "training_report_binding_sha256": str,
    "artifact_role": str,
    "training_completed": bool,
    "embedded_metadata_role": str,
    "claim_boundary": str,
    "head_training_status": str,
    "inference_only": bool,
    "optimizer_resume_supported": bool,
    "formal_evaluation": bool,
    "performance_evidence": bool,
}

_TOP_LEVEL_KEYS = {
    "schema_version",
    "metadata",
    "trained_head_metadata",
    "training_report_binding",
    "head_state",
}


def _exact_native_mapping(
    raw: object,
    types: Mapping[str, type],
    name: str,
) -> dict[str, object]:
    if type(raw) is not dict:
        raise TypeError(f"{name} must be an exact dict")
    payload = dict(raw)
    if set(payload) != set(types):
        missing = sorted(set(types) - set(payload))
        unexpected = sorted(set(payload) - set(types))
        raise ValueError(
            f"{name} key set mismatch: missing={missing}, unexpected={unexpected}"
        )
    for field, expected_type in types.items():
        if type(payload[field]) is not expected_type:
            raise TypeError(
                f"{name}.{field} must be a native {expected_type.__name__}"
            )
    return payload


def _require_sha256(value: object, name: str) -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _mapping_sha256(payload: dict[str, object]) -> str:
    if type(payload) is not dict:
        raise TypeError("digest payload must be an exact dict")
    return sha256_bytes(canonical_json_bytes(payload))


def _named_head_tensor_sha256(state: Mapping[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _expected_head_state(
    model: FrozenFoundationV4SharedPolicyValueV2,
) -> dict[str, torch.Tensor]:
    result: dict[str, torch.Tensor] = {}
    for prefix in _HEAD_PREFIXES:
        module = getattr(model, prefix)
        for name, tensor in module.state_dict().items():
            result[f"{prefix}.{name}"] = tensor
    return result


def _validate_head_state(
    raw: object,
    model: FrozenFoundationV4SharedPolicyValueV2,
    *,
    require_detached_clones: bool,
) -> tuple[dict[str, torch.Tensor], str]:
    if type(raw) is not dict:
        raise TypeError("head_state must be an exact dict")
    state = dict(raw)
    if any(type(name) is not str for name in state):
        raise TypeError("head_state keys must be native strings")
    expected = _expected_head_state(model)
    if set(state) != set(expected):
        missing = sorted(set(expected) - set(state))
        unexpected = sorted(set(state) - set(expected))
        raise ValueError(
            "head_state key set mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )
    checked: dict[str, torch.Tensor] = {}
    for name in sorted(expected):
        tensor = state[name]
        reference = expected[name]
        if type(tensor) is not torch.Tensor:
            raise TypeError(f"head_state[{name!r}] must be an exact Tensor")
        if tensor.device.type != "cpu":
            raise ValueError(f"head_state[{name!r}] must be on CPU")
        if tensor.dtype != torch.float32:
            raise ValueError(f"head_state[{name!r}] must be FP32")
        if tuple(tensor.shape) != tuple(reference.shape):
            raise ValueError(
                f"head_state[{name!r}] shape mismatch: "
                f"{tuple(tensor.shape)} != {tuple(reference.shape)}"
            )
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"head_state[{name!r}] contains non-finite values")
        if require_detached_clones and (
            tensor.requires_grad or tensor.grad_fn is not None
        ):
            raise ValueError(
                f"head_state[{name!r}] must be a detached training-party clone"
            )
        checked[name] = tensor.detach().contiguous().clone()
    return checked, _named_head_tensor_sha256(checked)


def clone_trained_head_state_v2(
    model: FrozenFoundationV4SharedPolicyValueV2,
) -> dict[str, torch.Tensor]:
    """Return detached CPU/FP32 clones for a modified development head."""

    if type(model) is not FrozenFoundationV4SharedPolicyValueV2:
        raise TypeError("model must be an exact FrozenFoundationV4SharedPolicyValueV2")
    model.assert_foundation_integrity()
    if model.head_training_status != "modified_unsealed":
        raise ValueError("only a modified_unsealed trained head can be cloned")
    state = {
        name: tensor.detach().cpu().contiguous().clone()
        for name, tensor in _expected_head_state(model).items()
    }
    _validate_head_state(state, model, require_detached_clones=True)
    return state


def _validate_base_metadata(
    raw: object,
    model: FrozenFoundationV4SharedPolicyValueV2,
    trained_digest: str,
) -> dict[str, object]:
    metadata = _exact_native_mapping(raw, _BASE_METADATA_TYPES, "trained_head_metadata")
    for field in (
        "foundation_checkpoint_sha256",
        "foundation_tensor_sha256",
        "head_initial_tensor_sha256",
        "head_current_tensor_sha256",
    ):
        _require_sha256(metadata[field], f"trained_head_metadata.{field}")
    expected = model.metadata()
    mutable = {"head_current_tensor_sha256", "head_training_status"}
    for field in set(expected) - mutable:
        if metadata[field] != expected[field]:
            raise ValueError(f"trained_head_metadata.{field} identity mismatch")
    if metadata["head_current_tensor_sha256"] != trained_digest:
        raise ValueError("trained_head_metadata current head digest mismatch")
    if metadata["head_training_status"] != "modified_unsealed":
        raise ValueError("trained_head_metadata must describe modified_unsealed heads")
    if trained_digest == metadata["head_initial_tensor_sha256"]:
        raise ValueError("trained head digest must differ from initialized head digest")
    return metadata


def _validate_report_binding(
    raw: object,
    metadata: Mapping[str, object],
    trained_digest: str,
) -> dict[str, object]:
    report = _exact_native_mapping(
        raw, _REPORT_TYPES, "training_report_binding"
    )
    for field in (
        "report_payload_sha256",
        "trainer_source_sha256",
        "training_source_manifest_sha256",
        "split_registry_sha256",
        "case_roster_sha256",
        "foundation_checkpoint_sha256",
        "initial_head_tensor_sha256",
        "final_head_tensor_sha256",
    ):
        _require_sha256(report[field], f"training_report_binding.{field}")
    if not report["training_run_id"]:
        raise ValueError("training_report_binding.training_run_id must be non-empty")
    if report["schema_version"] != TRAINING_REPORT_BINDING_V2_SCHEMA:
        raise ValueError("unsupported training report binding schema")
    if report["source_arm"] not in _SOURCE_ARMS:
        raise ValueError("training_report_binding.source_arm is unregistered")
    for field in ("sample_count", "update_steps"):
        if report[field] <= 0:
            raise ValueError(f"training_report_binding.{field} must be positive")
    if report["training_completed"] is not True:
        raise ValueError("training report must declare completed training")
    if report["formal_evaluation"] is not False:
        raise ValueError("development seal cannot claim formal evaluation")
    if report["performance_evidence"] is not False:
        raise ValueError("development seal cannot claim performance evidence")
    if report["foundation_checkpoint_sha256"] != metadata[
        "foundation_checkpoint_sha256"
    ]:
        raise ValueError("training report foundation checkpoint mismatch")
    if report["initial_head_tensor_sha256"] != metadata[
        "head_initial_tensor_sha256"
    ]:
        raise ValueError("training report initial head digest mismatch")
    if report["final_head_tensor_sha256"] != trained_digest:
        raise ValueError("training report final head digest mismatch")
    return report


def build_trained_head_suite_manifest_payload_v2(
    *,
    trained_head_metadata: dict[str, object],
    training_report_binding: dict[str, object],
) -> dict[str, object]:
    """Build the strict outer payload; callers must anchor its SHA elsewhere."""

    if type(trained_head_metadata) is not dict:
        raise TypeError("trained_head_metadata must be an exact dict")
    if type(training_report_binding) is not dict:
        raise TypeError("training_report_binding must be an exact dict")
    metadata = _exact_native_mapping(
        trained_head_metadata, _BASE_METADATA_TYPES, "trained_head_metadata"
    )
    report = _exact_native_mapping(
        training_report_binding, _REPORT_TYPES, "training_report_binding"
    )
    for field in (
        "foundation_checkpoint_sha256",
        "foundation_tensor_sha256",
        "head_current_tensor_sha256",
    ):
        _require_sha256(metadata[field], f"trained_head_metadata.{field}")
    return {
        "schema_version": TRAINED_HEAD_SUITE_MANIFEST_V2_SCHEMA,
        "sealed_schema_version": SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA,
        "base_head_schema_version": FROZEN_SHARED_HEAD_SCHEMA,
        "foundation_checkpoint_sha256": metadata[
            "foundation_checkpoint_sha256"
        ],
        "foundation_tensor_sha256": metadata["foundation_tensor_sha256"],
        "trained_head_tensor_sha256": metadata["head_current_tensor_sha256"],
        "trained_head_metadata_sha256": _mapping_sha256(metadata),
        "training_report_binding_sha256": _mapping_sha256(report),
        "artifact_role": SEALED_ARTIFACT_ROLE,
        "training_completed": True,
        "embedded_metadata_role": EMBEDDED_METADATA_ROLE,
        "claim_boundary": SEALED_CLAIM_BOUNDARY,
        "inference_only": True,
        "optimizer_resume_supported": False,
        "formal_evaluation": False,
        "performance_evidence": False,
    }


def trained_head_suite_manifest_sha256_v2(payload: dict[str, object]) -> str:
    """Return the canonical SHA of one exact suite-manifest payload."""

    suite = _validate_suite_manifest_shape(payload)
    return _mapping_sha256(suite)


def _validate_suite_manifest_shape(raw: object) -> dict[str, object]:
    suite = _exact_native_mapping(raw, _SUITE_TYPES, "suite_manifest_payload")
    for field in (
        "foundation_checkpoint_sha256",
        "foundation_tensor_sha256",
        "trained_head_tensor_sha256",
        "trained_head_metadata_sha256",
        "training_report_binding_sha256",
    ):
        _require_sha256(suite[field], f"suite_manifest_payload.{field}")
    expected_constants = {
        "schema_version": TRAINED_HEAD_SUITE_MANIFEST_V2_SCHEMA,
        "sealed_schema_version": SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA,
        "base_head_schema_version": FROZEN_SHARED_HEAD_SCHEMA,
        "artifact_role": SEALED_ARTIFACT_ROLE,
        "training_completed": True,
        "embedded_metadata_role": EMBEDDED_METADATA_ROLE,
        "claim_boundary": SEALED_CLAIM_BOUNDARY,
        "inference_only": True,
        "optimizer_resume_supported": False,
        "formal_evaluation": False,
        "performance_evidence": False,
    }
    for field, expected in expected_constants.items():
        if suite[field] != expected:
            raise ValueError(f"suite_manifest_payload.{field} contract mismatch")
    return suite


def _validate_suite_manifest(
    raw: object,
    expected_sha256: str,
    *,
    metadata: Mapping[str, object],
    report: Mapping[str, object],
    trained_digest: str,
) -> tuple[dict[str, object], str]:
    suite = _validate_suite_manifest_shape(raw)
    external = _require_sha256(
        expected_sha256, "expected_suite_manifest_sha256"
    )
    actual = _mapping_sha256(suite)
    if actual != external:
        raise ValueError("suite manifest SHA does not match the external trust root")
    expected_bindings = {
        "foundation_checkpoint_sha256": metadata[
            "foundation_checkpoint_sha256"
        ],
        "foundation_tensor_sha256": metadata["foundation_tensor_sha256"],
        "trained_head_tensor_sha256": trained_digest,
        "trained_head_metadata_sha256": _mapping_sha256(dict(metadata)),
        "training_report_binding_sha256": _mapping_sha256(dict(report)),
    }
    for field, expected in expected_bindings.items():
        if suite[field] != expected:
            raise ValueError(f"suite manifest {field} binding mismatch")
    return suite, actual


def _validate_suite_trust_root_first(
    raw: object,
    expected_sha256: str,
    *,
    trained_head_metadata: object,
    training_report_binding: object,
) -> tuple[dict[str, object], str]:
    """Authenticate cheap metadata bindings before constructing any model."""

    suite = _validate_suite_manifest_shape(raw)
    external = _require_sha256(
        expected_sha256, "expected_suite_manifest_sha256"
    )
    actual = _mapping_sha256(suite)
    if actual != external:
        raise ValueError("suite manifest SHA does not match the external trust root")
    metadata = _exact_native_mapping(
        trained_head_metadata, _BASE_METADATA_TYPES, "trained_head_metadata"
    )
    report = _exact_native_mapping(
        training_report_binding, _REPORT_TYPES, "training_report_binding"
    )
    if _mapping_sha256(metadata) != suite["trained_head_metadata_sha256"]:
        raise ValueError("suite manifest trained_head_metadata_sha256 binding mismatch")
    if _mapping_sha256(report) != suite["training_report_binding_sha256"]:
        raise ValueError(
            "suite manifest training_report_binding_sha256 binding mismatch"
        )
    # This is a development thin head, not an unbounded architecture loader.
    if not 1 <= metadata["head_hidden"] <= 512:
        raise ValueError("trained_head_metadata.head_hidden is outside [1, 512]")
    return suite, actual


def _sealed_metadata(
    base: Mapping[str, object],
    report: Mapping[str, object],
    trained_digest: str,
    suite_sha: str,
) -> dict[str, object]:
    return {
        "schema_version": SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA,
        "suite_manifest_sha256": suite_sha,
        "base_head_schema_version": FROZEN_SHARED_HEAD_SCHEMA,
        "foundation_checkpoint_sha256": base["foundation_checkpoint_sha256"],
        "foundation_tensor_sha256": base["foundation_tensor_sha256"],
        "foundation_parameter_count": base["foundation_parameter_count"],
        "head_hidden": base["head_hidden"],
        "joint_hidden": base["joint_hidden"],
        "head_seed": base["head_seed"],
        "initial_head_tensor_sha256": base["head_initial_tensor_sha256"],
        "trained_head_tensor_sha256": trained_digest,
        "trained_head_metadata_sha256": _mapping_sha256(dict(base)),
        "training_report_binding_sha256": _mapping_sha256(dict(report)),
        "artifact_role": SEALED_ARTIFACT_ROLE,
        "training_completed": True,
        "embedded_metadata_role": EMBEDDED_METADATA_ROLE,
        "claim_boundary": SEALED_CLAIM_BOUNDARY,
        "head_training_status": SEALED_HEAD_STATUS,
        "inference_only": True,
        "optimizer_resume_supported": False,
        "formal_evaluation": False,
        "performance_evidence": False,
    }


def _new_initialized_model(
    raw_metadata: object,
    foundation_checkpoint_path: str | Path,
) -> FrozenFoundationV4SharedPolicyValueV2:
    metadata = _exact_native_mapping(
        raw_metadata, _BASE_METADATA_TYPES, "trained_head_metadata"
    )
    # Exact native types have been checked before these constructor arguments.
    model = FrozenFoundationV4SharedPolicyValueV2(
        foundation_checkpoint_path,
        head_hidden=metadata["head_hidden"],  # type: ignore[arg-type]
        head_seed=metadata["head_seed"],  # type: ignore[arg-type]
    )
    model.eval()
    return model


def _validate_components(
    *,
    head_state: object,
    trained_head_metadata: object,
    training_report_binding: object,
    suite_manifest_payload: object,
    expected_suite_manifest_sha256: str,
    foundation_checkpoint_path: str | Path,
    require_detached_clones: bool,
) -> tuple[
    FrozenFoundationV4SharedPolicyValueV2,
    dict[str, torch.Tensor],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    str,
]:
    _validate_suite_trust_root_first(
        suite_manifest_payload,
        expected_suite_manifest_sha256,
        trained_head_metadata=trained_head_metadata,
        training_report_binding=training_report_binding,
    )
    model = _new_initialized_model(
        trained_head_metadata, foundation_checkpoint_path
    )
    state, trained_digest = _validate_head_state(
        head_state, model, require_detached_clones=require_detached_clones
    )
    metadata = _validate_base_metadata(
        trained_head_metadata, model, trained_digest
    )
    report = _validate_report_binding(
        training_report_binding, metadata, trained_digest
    )
    suite, suite_sha = _validate_suite_manifest(
        suite_manifest_payload,
        expected_suite_manifest_sha256,
        metadata=metadata,
        report=report,
        trained_digest=trained_digest,
    )
    return model, state, metadata, report, suite, suite_sha


def _load_head_submodules_only(
    model: FrozenFoundationV4SharedPolicyValueV2,
    state: Mapping[str, torch.Tensor],
) -> None:
    """Restore only the three new heads, never the protected base module."""

    model.assert_foundation_integrity()
    if model.head_training_status != "initialized":
        raise RuntimeError("narrow head restore requires an initialized base")
    for prefix in _HEAD_PREFIXES:
        prefix_dot = prefix + "."
        local = {
            name[len(prefix_dot) :]: tensor.detach().clone()
            for name, tensor in state.items()
            if name.startswith(prefix_dot)
        }
        module = getattr(model, prefix)
        result = module.load_state_dict(local, strict=True, assign=False)
        if result.missing_keys or result.unexpected_keys:  # pragma: no cover
            raise RuntimeError(f"narrow {prefix} restore was incomplete")
    model.assert_foundation_integrity()


class SealedTrainedSharedHeadV2:
    """Inference-only view of one externally anchored trained development head."""

    __slots__ = (
        "__model",
        "__metadata",
        "__trained_digest",
        "__model_forward",
        "__model_class_callables",
        "__module_signature",
        "__class_forwards",
        "__head_tensor_bindings",
    )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("sealed trained-head wrapper is immutable")

    def __delattr__(self, name: str) -> None:
        del name
        raise AttributeError("sealed trained-head wrapper is immutable")

    def __init__(
        self,
        model: FrozenFoundationV4SharedPolicyValueV2,
        metadata: Mapping[str, object],
    ) -> None:
        if type(model) is not FrozenFoundationV4SharedPolicyValueV2:
            raise TypeError("sealed wrapper requires an exact E6-v2 base model")
        checked = _exact_native_mapping(
            dict(metadata), _SEALED_METADATA_TYPES, "sealed_metadata"
        )
        model.eval()
        model.requires_grad_(False)
        object.__setattr__(self, "_SealedTrainedSharedHeadV2__model", model)
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__metadata",
            MappingProxyType(dict(checked)),
        )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__trained_digest",
            checked["trained_head_tensor_sha256"],
        )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__model_forward",
            type(model).forward_one,
        )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__model_class_callables",
            tuple(
                (name, getattr(type(model), name))
                for name, value in type(model).__dict__.items()
                if callable(value)
            ),
        )
        named_modules = tuple(model.named_modules())
        module_signature = tuple(
            (name, type(module), id(module)) for name, module in named_modules
        )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__module_signature",
            module_signature,
        )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__class_forwards",
            tuple(
                (module_type, module_type.forward)
                for module_type in dict.fromkeys(
                    module_type for _, module_type, _ in module_signature
                )
            ),
        )
        head_bindings: list[tuple[str, torch.nn.Module, str, str, torch.Tensor]] = []
        for module_name, module in named_modules:
            if not any(
                module_name == prefix or module_name.startswith(prefix + ".")
                for prefix in _HEAD_PREFIXES
            ):
                continue
            for local_name, tensor in module._parameters.items():
                if tensor is not None:
                    head_bindings.append(
                        (
                            f"{module_name}.{local_name}",
                            module,
                            "parameter",
                            local_name,
                            tensor,
                        )
                    )
            for local_name, tensor in module._buffers.items():
                if tensor is not None:
                    head_bindings.append(
                        (
                            f"{module_name}.{local_name}",
                            module,
                            "buffer",
                            local_name,
                            tensor,
                        )
                    )
        object.__setattr__(
            self,
            "_SealedTrainedSharedHeadV2__head_tensor_bindings",
            tuple(sorted(head_bindings, key=lambda item: item[0])),
        )
        self.assert_integrity()

    @property
    def inference_only(self) -> bool:
        return True

    @property
    def head_training_status(self) -> str:
        return SEALED_HEAD_STATUS

    def metadata(self) -> dict[str, object]:
        self.assert_integrity()
        return dict(self.__metadata)

    def assert_integrity(self) -> str:
        _assert_pinned_head_execution_globals()
        model = self.__model
        callable_names = {name for name, _ in self.__model_class_callables}
        overridden = sorted(callable_names & set(model.__dict__))
        if overridden:
            raise RuntimeError(
                "sealed model instance execution override detected: "
                + ", ".join(overridden)
            )
        for name, expected_callable in self.__model_class_callables:
            if getattr(type(model), name) is not expected_callable:
                raise RuntimeError(
                    f"sealed model class execution helper changed: {name}"
                )
        current_modules = tuple(
            (name, type(module), id(module)) for name, module in model.named_modules()
        )
        if current_modules != self.__module_signature:
            raise RuntimeError("sealed trained-head module tree changed")
        for module_type, expected_forward in self.__class_forwards:
            if module_type.forward is not expected_forward:
                raise RuntimeError("sealed trained-head class forward changed")
        hook_attributes = (
            "_forward_hooks",
            "_forward_pre_hooks",
            "_backward_hooks",
            "_backward_pre_hooks",
            "_state_dict_hooks",
            "_state_dict_pre_hooks",
        )
        for name, module in model.named_modules():
            label = name or "<root>"
            forbidden_instance_methods = {
                "forward",
                "_call_impl",
                "parameters",
                "named_parameters",
                "buffers",
                "named_buffers",
                "state_dict",
            }
            if forbidden_instance_methods & set(module.__dict__):
                raise RuntimeError(
                    f"sealed trained-head instance execution override at {label}"
                )
            for attribute in hook_attributes:
                if getattr(module, attribute, None):
                    raise RuntimeError(
                        f"sealed trained-head hooks are forbidden at {label}"
                    )
        model.assert_foundation_integrity()
        if model.training:
            raise RuntimeError("sealed trained head must remain in evaluation mode")
        live_state: dict[str, torch.Tensor] = {}
        for full_name, owner, kind, local_name, tensor in self.__head_tensor_bindings:
            registry = owner._parameters if kind == "parameter" else owner._buffers
            if registry.get(local_name) is not tensor:
                raise RuntimeError(
                    f"sealed trained-head registered tensor changed: {full_name}"
                )
            live_state[full_name] = tensor
        if any(
            tensor.requires_grad
            for _, _, kind, _, tensor in self.__head_tensor_bindings
            if kind == "parameter"
        ):
            raise RuntimeError("sealed trained head parameters must not require gradients")
        expected = self.__trained_digest
        actual = _named_head_tensor_sha256(live_state)
        if actual != expected:
            raise RuntimeError("sealed trained head tensor digest changed")
        return actual

    def forward_one(
        self,
        vector: VectorANF,
        actions: Sequence[SharedAction],
        *,
        weights: SharedUtilityWeights = SharedUtilityWeights(),
    ) -> tuple[torch.Tensor, torch.Tensor]:
        self.assert_integrity()
        with torch.no_grad():
            logits, value = self.__model_forward(
                self.__model,
                vector, actions, weights=weights
            )
        self.assert_integrity()
        return logits.detach(), value.detach()

    __call__ = forward_one

    def train(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sealed trained head is inference-only")

    def requires_grad_(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sealed trained head is inference-only")

    def parameters(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sealed trained head exposes no optimizer parameters")

    def state_dict(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sealed trained head exposes no resume state")

    def load_state_dict(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("sealed trained head cannot resume or mutate")


def seal_trained_shared_head_v2(
    path: str | Path,
    *,
    head_state: dict[str, torch.Tensor],
    trained_head_metadata: dict[str, object],
    training_report_binding: dict[str, object],
    suite_manifest_payload: dict[str, object],
    expected_suite_manifest_sha256: str,
    foundation_checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
) -> str:
    """Write and immediately verify one non-overwriting development seal."""

    (
        _model,
        state,
        metadata,
        report,
        _suite,
        suite_sha,
    ) = _validate_components(
        head_state=head_state,
        trained_head_metadata=trained_head_metadata,
        training_report_binding=training_report_binding,
        suite_manifest_payload=suite_manifest_payload,
        expected_suite_manifest_sha256=expected_suite_manifest_sha256,
        foundation_checkpoint_path=foundation_checkpoint_path,
        require_detached_clones=True,
    )
    sealed_metadata = _sealed_metadata(
        metadata, report, metadata["head_current_tensor_sha256"], suite_sha
    )
    payload = {
        "schema_version": SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA,
        "metadata": sealed_metadata,
        "trained_head_metadata": dict(metadata),
        "training_report_binding": dict(report),
        "head_state": state,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with target.open("xb") as handle:
            created = True
            torch.save(payload, handle)
        checkpoint_sha256 = sha256_file(target)
        load_sealed_trained_shared_head_v2(
            target,
            suite_manifest_payload=suite_manifest_payload,
            expected_suite_manifest_sha256=expected_suite_manifest_sha256,
            expected_checkpoint_sha256=checkpoint_sha256,
            foundation_checkpoint_path=foundation_checkpoint_path,
        )
    except BaseException:
        if created and target.exists():
            target.unlink()
        raise
    return checkpoint_sha256


def load_sealed_trained_shared_head_v2(
    path: str | Path,
    *,
    suite_manifest_payload: dict[str, object],
    expected_suite_manifest_sha256: str,
    expected_checkpoint_sha256: str,
    foundation_checkpoint_path: str | Path = DEFAULT_FORMAL_V4_CHECKPOINT,
) -> SealedTrainedSharedHeadV2:
    """Load only bytes independently pinned outside the checkpoint itself."""

    checkpoint = Path(path)
    expected_checkpoint_sha = _require_sha256(
        expected_checkpoint_sha256, "expected_checkpoint_sha256"
    )
    with checkpoint.open("rb") as handle:
        checkpoint_bytes = handle.read(_MAX_SEALED_CHECKPOINT_BYTES + 1)
    if len(checkpoint_bytes) > _MAX_SEALED_CHECKPOINT_BYTES:
        raise ValueError("sealed checkpoint exceeds the bounded loader size")
    actual_checkpoint_sha = hashlib.sha256(checkpoint_bytes).hexdigest()
    if actual_checkpoint_sha != expected_checkpoint_sha:
        raise ValueError(
            "sealed checkpoint SHA-256 does not match the independent anchor"
        )
    payload = torch.load(
        io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True
    )
    if type(payload) is not dict:
        raise TypeError("sealed checkpoint payload must be an exact dict")
    if set(payload) != _TOP_LEVEL_KEYS:
        raise ValueError("sealed checkpoint top-level key set mismatch")
    if type(payload["schema_version"]) is not str or payload[
        "schema_version"
    ] != SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA:
        raise ValueError("unsupported sealed trained-head schema")
    (
        model,
        state,
        trained_metadata,
        report,
        _suite,
        suite_sha,
    ) = _validate_components(
        head_state=payload["head_state"],
        trained_head_metadata=payload["trained_head_metadata"],
        training_report_binding=payload["training_report_binding"],
        suite_manifest_payload=suite_manifest_payload,
        expected_suite_manifest_sha256=expected_suite_manifest_sha256,
        foundation_checkpoint_path=foundation_checkpoint_path,
        require_detached_clones=True,
    )
    sealed = _exact_native_mapping(
        payload["metadata"], _SEALED_METADATA_TYPES, "sealed_metadata"
    )
    expected_sealed = _sealed_metadata(
        trained_metadata,
        report,
        trained_metadata["head_current_tensor_sha256"],
        suite_sha,
    )
    if sealed != expected_sealed:
        raise ValueError("sealed checkpoint metadata binding mismatch")
    _load_head_submodules_only(model, state)
    trained_digest = trained_metadata["head_current_tensor_sha256"]
    if model.current_head_tensor_sha256() != trained_digest:
        raise RuntimeError("narrow trained-head restore digest mismatch")
    return SealedTrainedSharedHeadV2(model, sealed)


__all__ = [
    "SEALED_HEAD_STATUS",
    "SEALED_TRAINED_SHARED_HEAD_V2_SCHEMA",
    "TRAINED_HEAD_SUITE_MANIFEST_V2_SCHEMA",
    "TRAINING_REPORT_BINDING_V2_SCHEMA",
    "SealedTrainedSharedHeadV2",
    "build_trained_head_suite_manifest_payload_v2",
    "clone_trained_head_state_v2",
    "load_sealed_trained_shared_head_v2",
    "seal_trained_shared_head_v2",
    "trained_head_suite_manifest_sha256_v2",
]
