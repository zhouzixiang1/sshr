#!/usr/bin/env python3
"""Auditable execution-cost feedback for fixed-budget MCTS scheduling.

This module deliberately keeps execution feedback outside the logical search
semantics.  A fitted model may re-rank which independent ``FactorAction``
edges receive a fixed evaluation budget, but it never changes an action, a
state, a rollout cost, or the emitted Boolean oracle.

The regression contract is intentionally narrow:

* fitting accepts only :class:`ExecutionCalibrationRecord` objects;
* prediction accepts a ``StateKey``-shaped object and label-free actions;
* every fit is identified by sorted calibration IDs and a content SHA-256;
* standardisation is learned from calibration data only, with constant
  features mapped safely to zero;
* the implementation depends only on NumPy, not an external ML package.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping, Protocol, Sequence, runtime_checkable

import numpy as np

from src.factor_plan import FactorAction


if TYPE_CHECKING:  # Avoid a runtime cycle: nmcts_solver imports this module.
    from src.nmcts_solver import StateKey


FEATURE_SCHEMA = "execution-cost-structural-v1"
MODEL_SCHEMA = "numpy-ridge-execution-cost-v1"
FEATURE_NAMES = (
    "state_term_count",
    "state_variable_count",
    "state_mean_degree",
    "state_degree_std",
    "state_max_degree",
    "state_prefix_len",
    "state_live_factor_ancilla",
    "action_factor_degree",
    "action_group_count",
    "action_residual_count",
    "action_rest_count",
    "action_group_fraction",
    "action_rest_fraction",
    "action_group_mean_degree",
    "action_residual_mean_degree",
    "action_rest_mean_degree",
    "action_immediate_gain",
    "action_prior",
    "action_linear",
    "action_affine_const",
)


def _finite_float(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if result != value or result < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return result


def _canonical_terms(values: object, name: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of non-negative integers")
    try:
        terms = tuple(sorted(_nonnegative_int(value, name) for value in values))  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"{name} must be an iterable of non-negative integers") from exc
    if len(set(terms)) != len(terms):
        raise ValueError(f"{name} must not contain duplicate terms")
    return terms


def _state_parts(state_key: object) -> tuple[tuple[int, ...], int, int]:
    """Validate and canonicalise the public ``StateKey`` structural fields."""

    try:
        raw_terms = state_key.terms  # type: ignore[attr-defined]
        raw_prefix = state_key.prefix_len  # type: ignore[attr-defined]
        raw_live = state_key.live_factor_ancilla  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise TypeError(
            "state_key must expose terms, prefix_len, and live_factor_ancilla"
        ) from exc
    return (
        _canonical_terms(raw_terms, "state_key.terms"),
        _nonnegative_int(raw_prefix, "state_key.prefix_len"),
        _nonnegative_int(raw_live, "state_key.live_factor_ancilla"),
    )


def _action_payload(action: FactorAction) -> dict[str, object]:
    if not isinstance(action, FactorAction):
        raise TypeError("action must be a FactorAction")
    return {
        "factor": _nonnegative_int(action.factor, "action.factor"),
        "group": list(_canonical_terms(action.group, "action.group")),
        "residuals": list(
            _canonical_terms(action.residuals, "action.residuals")
        ),
        "rest": list(_canonical_terms(action.rest, "action.rest")),
        "immediate_gain": _finite_float(
            action.immediate_gain, "action.immediate_gain"
        ),
        "prior": _finite_float(action.prior, "action.prior"),
        "linear": bool(action.linear),
        "affine_const": bool(action.affine_const),
    }


def _degree_stats(terms: Sequence[int]) -> tuple[float, float, float]:
    if not terms:
        return 0.0, 0.0, 0.0
    degrees = np.fromiter((int(term).bit_count() for term in terms), dtype=float)
    return float(degrees.mean()), float(degrees.std()), float(degrees.max())


def structural_feature_vector(
    state_key: "StateKey", action: FactorAction
) -> np.ndarray:
    """Return deterministic, permutation-invariant StateKey/action features.

    Variable identities are intentionally absent.  The vector uses only term
    counts, degree statistics, factor cardinality and the action's existing
    scalar diagnostics, so renaming Boolean variables leaves it unchanged.
    """

    state_terms, prefix_len, live_ancilla = _state_parts(state_key)
    payload = _action_payload(action)
    group = tuple(int(value) for value in payload["group"])
    residuals = tuple(int(value) for value in payload["residuals"])
    rest = tuple(int(value) for value in payload["rest"])
    factor = int(payload["factor"])

    state_mean, state_std, state_max = _degree_stats(state_terms)
    group_mean, _, _ = _degree_stats(group)
    residual_mean, _, _ = _degree_stats(residuals)
    rest_mean, _, _ = _degree_stats(rest)
    state_count = len(state_terms)
    all_masks = (*state_terms, factor, *group, *residuals, *rest)
    variable_union = 0
    for mask in all_masks:
        variable_union |= mask
    variable_count = variable_union.bit_count()
    denominator = max(state_count, 1)

    features = np.asarray(
        [
            state_count,
            variable_count,
            state_mean,
            state_std,
            state_max,
            prefix_len,
            live_ancilla,
            factor.bit_count(),
            len(group),
            len(residuals),
            len(rest),
            len(group) / denominator,
            len(rest) / denominator,
            group_mean,
            residual_mean,
            rest_mean,
            payload["immediate_gain"],
            payload["prior"],
            int(bool(payload["linear"])),
            int(bool(payload["affine_const"])),
        ],
        dtype=float,
    )
    if features.shape != (len(FEATURE_NAMES),) or not np.all(np.isfinite(features)):
        raise ValueError("StateKey/FactorAction features must all be finite")
    return features


@dataclass(frozen=True)
class ExecutionCalibrationRecord:
    """One explicitly labelled calibration observation.

    Test/held-out examples cannot be passed to :meth:`fit` without first being
    made explicit calibration records, which keeps split ownership visible to
    the experiment runner and to the recorded calibration ID/SHA manifest.
    """

    calibration_id: str
    state_key: "StateKey"
    action: FactorAction
    execution_cost: float

    def canonical_payload(self) -> dict[str, object]:
        identifier = str(self.calibration_id).strip()
        if not identifier:
            raise ValueError("calibration_id must be non-empty")
        state_terms, prefix_len, live_ancilla = _state_parts(self.state_key)
        cost = _finite_float(self.execution_cost, "execution_cost")
        if cost < 0.0:
            raise ValueError("execution_cost must be non-negative")
        return {
            "calibration_id": identifier,
            "state": {
                "terms": list(state_terms),
                "prefix_len": prefix_len,
                "live_factor_ancilla": live_ancilla,
            },
            "action": _action_payload(self.action),
            "execution_cost": cost,
        }


@dataclass(frozen=True)
class ExecutionUtilityAdjustment:
    """Validated result returned once for one scheduler candidate pool."""

    adjusted_utilities: tuple[float, ...]
    predicted_execution_costs: tuple[float, ...]
    normalized_execution_penalties: tuple[float, ...]
    penalty_weight: float
    cost_offset: float
    cost_scale: float
    model_metadata: Mapping[str, object]
    model_sha256: str
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        adjusted = tuple(
            _finite_float(value, "adjusted_utilities")
            for value in self.adjusted_utilities
        )
        predictions = tuple(
            _finite_float(value, "predicted_execution_costs")
            for value in self.predicted_execution_costs
        )
        penalties = tuple(
            _finite_float(value, "normalized_execution_penalties")
            for value in self.normalized_execution_penalties
        )
        if len(adjusted) != len(predictions) or len(adjusted) != len(penalties):
            raise ValueError("adjustment result arrays must have the same length")
        if any(value < 0.0 for value in predictions):
            raise ValueError("predicted execution costs must be non-negative")
        if any(value < 0.0 for value in penalties):
            raise ValueError("normalized execution penalties must be non-negative")
        weight = _finite_float(self.penalty_weight, "penalty_weight")
        if weight < 0.0:
            raise ValueError("penalty_weight must be non-negative")
        offset = _finite_float(self.cost_offset, "cost_offset")
        scale = _finite_float(self.cost_scale, "cost_scale")
        if scale <= 0.0:
            raise ValueError("cost_scale must be positive")
        digest = str(self.model_sha256)
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("model_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.model_metadata, Mapping):
            raise TypeError("model_metadata must be a mapping")
        if not isinstance(self.diagnostics, Mapping):
            raise TypeError("diagnostics must be a mapping")

        object.__setattr__(self, "adjusted_utilities", adjusted)
        object.__setattr__(self, "predicted_execution_costs", predictions)
        object.__setattr__(self, "normalized_execution_penalties", penalties)
        object.__setattr__(self, "penalty_weight", weight)
        object.__setattr__(self, "cost_offset", offset)
        object.__setattr__(self, "cost_scale", scale)
        object.__setattr__(self, "model_sha256", digest)
        object.__setattr__(self, "model_metadata", dict(self.model_metadata))
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))

    def audit_dict(self) -> dict[str, object]:
        return {
            "predicted_execution_costs": list(self.predicted_execution_costs),
            "normalized_execution_penalties": list(
                self.normalized_execution_penalties
            ),
            "penalty_weight": self.penalty_weight,
            "cost_offset": self.cost_offset,
            "cost_scale": self.cost_scale,
            "model_metadata": dict(self.model_metadata),
            "model_sha256": self.model_sha256,
            "diagnostics": dict(self.diagnostics),
        }


@runtime_checkable
class ExecutionUtilityAdjuster(Protocol):
    """Single-call interface consumed by ``NeuralMCTSSolver``."""

    def adjust(
        self,
        state_key: "StateKey",
        actions: Sequence[FactorAction],
        raw_utilities: Sequence[float],
    ) -> ExecutionUtilityAdjustment:
        ...


class RidgeExecutionCostModel:
    """Calibration-only, standardised NumPy ridge execution-cost model."""

    def __init__(self, *, ridge_alpha: float = 1.0, penalty_weight: float = 0.25):
        alpha = _finite_float(ridge_alpha, "ridge_alpha")
        weight = _finite_float(penalty_weight, "penalty_weight")
        if alpha <= 0.0:
            raise ValueError("ridge_alpha must be positive")
        if weight < 0.0:
            raise ValueError("penalty_weight must be non-negative")
        self.ridge_alpha = alpha
        self.penalty_weight = weight
        self._mean: np.ndarray | None = None
        self._scale: np.ndarray | None = None
        self._constant_mask: np.ndarray | None = None
        self._coef: np.ndarray | None = None
        self._intercept: float | None = None
        self._calibration_ids: tuple[str, ...] = ()
        self._calibration_sha256: str | None = None

    @staticmethod
    def _validate_sha256(value: object, name: str) -> str:
        digest = str(value)
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        return digest

    @classmethod
    def from_metadata(
        cls,
        metadata: Mapping[str, object],
        *,
        penalty_weight: float = 0.25,
        expected_calibration_sha256: str | None = None,
    ) -> "RidgeExecutionCostModel":
        """Load a frozen calibration model without fitting or accepting labels.

        ``expected_calibration_sha256`` lets an experiment runner bind the
        loaded model to a separately frozen calibration manifest.  Even when
        it is omitted, the calibration digest remains covered by the verified
        model SHA-256.
        """

        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        required_keys = {
            "schema",
            "feature_schema",
            "feature_names",
            "ridge_alpha",
            "prediction_lower_bound",
            "calibration_count",
            "calibration_ids",
            "calibration_sha256",
            "constant_features",
            "standardization_mean",
            "standardization_scale",
            "intercept",
            "coefficients",
            "model_sha256",
        }
        if set(metadata) != required_keys:
            missing = sorted(required_keys - set(metadata))
            extra = sorted(set(metadata) - required_keys)
            raise ValueError(
                f"metadata fields mismatch: missing={missing}, extra={extra}"
            )
        if metadata["schema"] != MODEL_SCHEMA:
            raise ValueError(f"unsupported model schema: {metadata['schema']!r}")
        if metadata["feature_schema"] != FEATURE_SCHEMA:
            raise ValueError(
                f"unsupported feature schema: {metadata['feature_schema']!r}"
            )
        if not isinstance(metadata["feature_names"], list) or tuple(
            metadata["feature_names"]
        ) != FEATURE_NAMES:
            raise ValueError("feature_names do not match the frozen feature schema")
        if _finite_float(
            metadata["prediction_lower_bound"], "prediction_lower_bound"
        ) != 0.0:
            raise ValueError("prediction_lower_bound must be exactly zero")

        count = _nonnegative_int(metadata["calibration_count"], "calibration_count")
        if count <= 0:
            raise ValueError("calibration_count must be positive")
        raw_ids = metadata["calibration_ids"]
        if not isinstance(raw_ids, list) or any(
            not isinstance(identifier, str) or not identifier.strip()
            for identifier in raw_ids
        ):
            raise ValueError("calibration_ids must be a list of non-empty strings")
        calibration_ids = tuple(raw_ids)
        if len(calibration_ids) != count:
            raise ValueError("calibration_count does not match calibration_ids")
        if tuple(sorted(calibration_ids)) != calibration_ids or len(
            set(calibration_ids)
        ) != len(calibration_ids):
            raise ValueError("calibration_ids must be unique and sorted")

        calibration_sha = cls._validate_sha256(
            metadata["calibration_sha256"], "calibration_sha256"
        )
        if expected_calibration_sha256 is not None:
            expected_sha = cls._validate_sha256(
                expected_calibration_sha256, "expected_calibration_sha256"
            )
            if calibration_sha != expected_sha:
                raise ValueError("calibration SHA-256 does not match frozen manifest")

        constant_features = metadata["constant_features"]
        if not isinstance(constant_features, list) or any(
            not isinstance(name, str) for name in constant_features
        ):
            raise ValueError("constant_features must be a list of feature names")
        expected_constant_order = [
            name for name in FEATURE_NAMES if name in set(constant_features)
        ]
        if constant_features != expected_constant_order or len(
            set(constant_features)
        ) != len(constant_features):
            raise ValueError(
                "constant_features must be a unique feature-schema-ordered subset"
            )

        def numeric_vector(name: str) -> np.ndarray:
            raw = metadata[name]
            if not isinstance(raw, list) or len(raw) != len(FEATURE_NAMES):
                raise ValueError(
                    f"{name} must have exactly {len(FEATURE_NAMES)} entries"
                )
            values = np.asarray(
                [_finite_float(value, name) for value in raw], dtype=float
            )
            if values.shape != (len(FEATURE_NAMES),):
                raise ValueError(f"{name} has an invalid shape")
            return values

        mean = numeric_vector("standardization_mean")
        scale = numeric_vector("standardization_scale")
        coef = numeric_vector("coefficients")
        if np.any(scale <= 0.0):
            raise ValueError("standardization_scale entries must be positive")
        constant_mask = np.asarray(
            [name in set(constant_features) for name in FEATURE_NAMES], dtype=bool
        )
        if np.any(scale[constant_mask] != 1.0):
            raise ValueError("constant feature scales must be exactly one")
        intercept = _finite_float(metadata["intercept"], "intercept")
        incoming_model_sha = cls._validate_sha256(
            metadata["model_sha256"], "model_sha256"
        )

        model = cls(
            ridge_alpha=_finite_float(metadata["ridge_alpha"], "ridge_alpha"),
            penalty_weight=penalty_weight,
        )
        model._mean = mean
        model._scale = scale
        model._constant_mask = constant_mask
        model._coef = coef
        model._intercept = intercept
        model._calibration_ids = calibration_ids
        model._calibration_sha256 = calibration_sha

        reconstructed = model.metadata()
        if reconstructed["model_sha256"] != incoming_model_sha:
            raise ValueError("model SHA-256 verification failed")
        try:
            incoming_bytes = json.dumps(
                dict(metadata),
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            reconstructed_bytes = json.dumps(
                reconstructed,
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be strictly JSON serialisable") from exc
        if incoming_bytes != reconstructed_bytes:
            raise ValueError("loaded metadata is not a byte-stable model encoding")
        return model

    @property
    def fitted(self) -> bool:
        return self._coef is not None

    def fit(
        self, records: Sequence[ExecutionCalibrationRecord]
    ) -> "RidgeExecutionCostModel":
        """Fit only from explicitly identified calibration observations."""

        if isinstance(records, (str, bytes)):
            raise TypeError("records must contain ExecutionCalibrationRecord objects")
        records_tuple = tuple(records)
        if not records_tuple:
            raise ValueError("at least one calibration record is required")
        if any(not isinstance(record, ExecutionCalibrationRecord) for record in records_tuple):
            raise TypeError("fit accepts only ExecutionCalibrationRecord objects")

        prepared = [(record.canonical_payload(), record) for record in records_tuple]
        prepared.sort(key=lambda item: str(item[0]["calibration_id"]))
        identifiers = tuple(str(item[0]["calibration_id"]) for item in prepared)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("calibration_id values must be unique")

        x = np.vstack(
            [structural_feature_vector(record.state_key, record.action) for _, record in prepared]
        )
        y = np.asarray(
            [float(payload["execution_cost"]) for payload, _ in prepared],
            dtype=float,
        )
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("calibration features and targets must all be finite")

        mean = x.mean(axis=0)
        raw_scale = x.std(axis=0)
        constant_mask = raw_scale <= np.finfo(float).eps * 32.0
        scale = raw_scale.copy()
        scale[constant_mask] = 1.0
        standardised = (x - mean) / scale
        # Make the constant-column contract exact rather than dependent on
        # floating-point subtraction of two equal values.
        standardised[:, constant_mask] = 0.0

        intercept = float(y.mean())
        centred_y = y - intercept
        gram = standardised.T @ standardised
        regularised = gram + self.ridge_alpha * np.eye(gram.shape[0])
        coef = np.linalg.solve(regularised, standardised.T @ centred_y)
        if not np.all(np.isfinite(coef)):
            raise RuntimeError("ridge fit produced non-finite coefficients")

        canonical_json = json.dumps(
            [payload for payload, _ in prepared],
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._mean = mean
        self._scale = scale
        self._constant_mask = constant_mask
        self._coef = coef
        self._intercept = intercept
        self._calibration_ids = identifiers
        self._calibration_sha256 = hashlib.sha256(canonical_json).hexdigest()
        return self

    def _require_fitted(
        self,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
        if (
            self._mean is None
            or self._scale is None
            or self._constant_mask is None
            or self._coef is None
            or self._intercept is None
        ):
            raise RuntimeError("execution-cost model must be fitted on calibration records")
        return (
            self._mean,
            self._scale,
            self._constant_mask,
            self._coef,
            self._intercept,
        )

    def predict(
        self, state_key: "StateKey", actions: Sequence[FactorAction]
    ) -> np.ndarray:
        """Predict non-negative costs without accepting any target labels."""

        mean, scale, constant_mask, coef, intercept = self._require_fitted()
        actions_tuple = tuple(actions)
        if not actions_tuple:
            return np.empty(0, dtype=float)
        x = np.vstack(
            [structural_feature_vector(state_key, action) for action in actions_tuple]
        )
        standardised = (x - mean) / scale
        standardised[:, constant_mask] = 0.0
        predictions = intercept + standardised @ coef
        if not np.all(np.isfinite(predictions)):
            raise RuntimeError("execution-cost prediction produced non-finite values")
        # Execution cost has a physical zero lower bound.  The clamp is part of
        # the declared model rather than a hidden post-processing heuristic.
        return np.maximum(predictions, 0.0)

    def _metadata_payload(self) -> dict[str, object]:
        mean, scale, constant_mask, coef, intercept = self._require_fitted()
        if self._calibration_sha256 is None:
            raise RuntimeError("fitted model is missing calibration provenance")
        return {
            "schema": MODEL_SCHEMA,
            "feature_schema": FEATURE_SCHEMA,
            "feature_names": list(FEATURE_NAMES),
            "ridge_alpha": self.ridge_alpha,
            "prediction_lower_bound": 0.0,
            "calibration_count": len(self._calibration_ids),
            "calibration_ids": list(self._calibration_ids),
            "calibration_sha256": self._calibration_sha256,
            "constant_features": [
                FEATURE_NAMES[index]
                for index, is_constant in enumerate(constant_mask)
                if bool(is_constant)
            ],
            "standardization_mean": mean.tolist(),
            "standardization_scale": scale.tolist(),
            "intercept": intercept,
            "coefficients": coef.tolist(),
        }

    def metadata(self) -> dict[str, object]:
        """Return JSON-serialisable parameters and a deterministic model SHA."""

        payload = self._metadata_payload()
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {**payload, "model_sha256": hashlib.sha256(encoded).hexdigest()}

    def adjust(
        self,
        state_key: "StateKey",
        actions: Sequence[FactorAction],
        raw_utilities: Sequence[float],
    ) -> ExecutionUtilityAdjustment:
        """Subtract a bounded relative execution penalty from scheduling utility."""

        actions_tuple = tuple(actions)
        raw = tuple(_finite_float(value, "raw_utilities") for value in raw_utilities)
        if len(actions_tuple) != len(raw):
            raise ValueError("raw utility count must match the candidate action count")
        predictions_array = self.predict(state_key, actions_tuple)
        predictions = tuple(float(value) for value in predictions_array)
        if predictions:
            offset = min(predictions)
            spread = max(predictions) - offset
            scale = max(spread, 1.0)
            penalties = tuple((value - offset) / scale for value in predictions)
        else:
            offset = 0.0
            scale = 1.0
            penalties = ()
        adjusted = tuple(
            utility - self.penalty_weight * penalty
            for utility, penalty in zip(raw, penalties)
        )
        metadata = self.metadata()
        return ExecutionUtilityAdjustment(
            adjusted_utilities=adjusted,
            predicted_execution_costs=predictions,
            normalized_execution_penalties=penalties,
            penalty_weight=self.penalty_weight,
            cost_offset=offset,
            cost_scale=scale,
            model_metadata=metadata,
            model_sha256=str(metadata["model_sha256"]),
        )
