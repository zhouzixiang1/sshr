"""Execution-aware utility for root-level NMCTS/QAOA candidate scheduling.

The adjuster in this module is deliberately outside logical synthesis.  For
each *existing* root ``FactorAction`` it completes the same scorer-free rollout
used by the experiment runners, emits an independently verifiable logical
oracle, and compiles that oracle against a declared synthetic coupling
profile.  The resulting native resource proxies may subtract a calibration-
frozen linear penalty from the utility consumed by both classical and QAOA
diversity schedulers.

There is no fit method and no noisy-outcome argument.  An optional frozen risk
model can see only the current ``StateKey`` and candidate actions.  Therefore a
held-out noisy outcome cannot enter the scheduling utility through this API.
All reported native counts and durations are deterministic synthetic-profile
proxies, not hardware measurements or hardware-performance evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import TYPE_CHECKING, Mapping, Sequence

from src.contracts.codec import canonical_json_bytes, sha256_bytes
from src.contracts.search import PlanTrace
from src.factor_plan import (
    FactorAction,
    Plan,
    SearchConfig,
    emit_plan_to_circuit,
    factor_cost,
    greedy_plan,
    verify_circuit_anf,
)
from src.hardware.superconducting import (
    CLAIM_BOUNDARY,
    NATIVE_GATE_SET,
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
)
from src.search.execution_feedback import (
    ExecutionUtilityAdjustment,
    RidgeExecutionCostModel,
)
from src.sshr_lib.bool_func import QuantumCircuit


if TYPE_CHECKING:  # Avoid a runtime cycle: nmcts_solver imports search contracts.
    from src.nmcts_solver import StateKey


PROFILE_SCHEMA = "synthetic-execution-profile-spec-v1"
WEIGHT_SCHEMA = "frozen-execution-penalty-weights-v1"
ADJUSTER_SCHEMA = "root-rollout-execution-aware-utility-v1"

EXECUTION_AWARE_CLAIM_BOUNDARY = (
    "Utility uses deterministic ideal compilation against a declared synthetic "
    "profile and optional calibration-frozen proxy risk. It is not hardware "
    "execution, a device calibration, or hardware-performance evidence."
)


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite non-negative number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite non-negative number") from exc
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return result


def _finite_positive(value: object, name: str) -> float:
    result = _finite_nonnegative(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _sha256(value: object, name: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return digest


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return int(value)


def _strict_terms(values: object, name: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of non-negative integers")
    try:
        raw = tuple(values)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError(f"{name} must be an iterable of non-negative integers") from exc
    terms: list[int] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must contain non-negative integers")
        terms.append(int(value))
    if len(set(terms)) != len(terms):
        raise ValueError(f"{name} must not contain duplicate terms")
    return tuple(sorted(terms))


def _state_parts(state_key: object) -> tuple[tuple[int, ...], int, int]:
    try:
        terms = _strict_terms(getattr(state_key, "terms"), "state_key.terms")
        prefix_len = _nonnegative_int(
            getattr(state_key, "prefix_len"), "state_key.prefix_len"
        )
        live_ancilla = _nonnegative_int(
            getattr(state_key, "live_factor_ancilla"),
            "state_key.live_factor_ancilla",
        )
    except AttributeError as exc:
        raise TypeError(
            "state_key must expose terms, prefix_len, and live_factor_ancilla"
        ) from exc
    return terms, prefix_len, live_ancilla


def _action_payload(action: FactorAction) -> dict[str, object]:
    if not isinstance(action, FactorAction):
        raise TypeError("actions must contain FactorAction objects")
    if isinstance(action.factor, bool) or not isinstance(action.factor, int):
        raise ValueError("action.factor must be a positive integer")
    if action.factor <= 0:
        raise ValueError("action.factor must be a positive integer")
    return {
        "factor": int(action.factor),
        "group": list(_strict_terms(action.group, "action.group")),
        "residuals": list(_strict_terms(action.residuals, "action.residuals")),
        "rest": list(_strict_terms(action.rest, "action.rest")),
        "immediate_gain": _finite(action.immediate_gain, "action.immediate_gain"),
        "prior": _finite(action.prior, "action.prior"),
        "linear": bool(action.linear),
        "affine_const": bool(action.affine_const),
    }


def _action_sha256(action: FactorAction) -> str:
    return sha256_bytes(canonical_json_bytes(_action_payload(action)))


@dataclass(frozen=True)
class SyntheticExecutionProfileSpec:
    """Frozen family-level specification for ideal synthetic compilation."""

    one_qubit_duration_ns: float
    two_qubit_duration_ns: float
    noise: NoiseParameters = NoiseParameters()
    topology_family: str = "heavy-hex-like"

    def __post_init__(self) -> None:
        if self.topology_family != "heavy-hex-like":
            raise ValueError("only the declared heavy-hex-like synthetic profile is supported")
        object.__setattr__(
            self,
            "one_qubit_duration_ns",
            _finite_positive(self.one_qubit_duration_ns, "one_qubit_duration_ns"),
        )
        object.__setattr__(
            self,
            "two_qubit_duration_ns",
            _finite_positive(self.two_qubit_duration_ns, "two_qubit_duration_ns"),
        )
        if not isinstance(self.noise, NoiseParameters):
            raise TypeError("noise must be NoiseParameters")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": PROFILE_SCHEMA,
            "synthetic": True,
            "calibration_source": None,
            "topology_family": self.topology_family,
            "topology_generation": "heavy_hex_like_profile(n_qubits)",
            "routing": "deterministic-shortest-path-swap-v1",
            "mct_decomposition": "ancilla-free-exact-parity-phase",
            "native_gate_set": list(NATIVE_GATE_SET),
            "one_qubit_duration_ns": self.one_qubit_duration_ns,
            "two_qubit_duration_ns": self.two_qubit_duration_ns,
            "duration_proxy": "additive-native-gate-duration-v1",
            "noise_parameters_recorded_not_applied": asdict(self.noise),
            "claim_boundary": CLAIM_BOUNDARY,
        }

    @property
    def profile_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.canonical_payload()))

    def build(self, n_qubits: int):
        if isinstance(n_qubits, bool) or not isinstance(n_qubits, int) or n_qubits <= 0:
            raise ValueError("n_qubits must be a positive integer")
        profile = heavy_hex_like_profile(n_qubits, noise=self.noise)
        if (
            not profile.synthetic
            or profile.calibration_source is not None
            or profile.topology_family != self.topology_family
            or tuple(profile.native_gate_set) != NATIVE_GATE_SET
        ):
            raise RuntimeError("constructed profile violates the frozen synthetic contract")
        return profile


@dataclass(frozen=True)
class FrozenExecutionPenaltyWeights:
    """Calibration-frozen non-negative coefficients already in utility units."""

    calibration_sha256: str
    profile_sha256: str
    native_one_qubit: float = 0.0
    native_two_qubit: float = 0.0
    inserted_swap: float = 0.0
    native_depth: float = 0.0
    duration_ns: float = 0.0
    model_risk: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "calibration_sha256",
            _sha256(self.calibration_sha256, "calibration_sha256"),
        )
        object.__setattr__(
            self,
            "profile_sha256",
            _sha256(self.profile_sha256, "profile_sha256"),
        )
        for name in (
            "native_one_qubit",
            "native_two_qubit",
            "inserted_swap",
            "native_depth",
            "duration_ns",
            "model_risk",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": WEIGHT_SCHEMA,
            "calibration_sha256": self.calibration_sha256,
            "profile_sha256": self.profile_sha256,
            "normalization": "none-frozen-coefficients-are-in-utility-units",
            "native_one_qubit": self.native_one_qubit,
            "native_two_qubit": self.native_two_qubit,
            "inserted_swap": self.inserted_swap,
            "native_depth": self.native_depth,
            "duration_ns": self.duration_ns,
            "model_risk": self.model_risk,
        }

    @property
    def weights_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.canonical_payload()))


def complete_root_action_rollout(
    state_key: "StateKey",
    action: FactorAction,
    config: SearchConfig,
) -> Plan:
    """Complete one root action with the frozen scorer-free greedy rollout."""

    terms, prefix_len, live_ancilla = _state_parts(state_key)
    if prefix_len != 0 or live_ancilla != 0:
        raise ValueError("execution-aware rollout compilation is root-only")
    if not isinstance(config, SearchConfig):
        raise TypeError("config must be SearchConfig")
    payload = _action_payload(action)
    state_terms = frozenset(terms)
    group = frozenset(int(value) for value in payload["group"])  # type: ignore[arg-type]
    rest_terms = frozenset(int(value) for value in payload["rest"])  # type: ignore[arg-type]
    if group & rest_terms or group | rest_terms != state_terms:
        raise ValueError("candidate action group/rest do not partition the state terms")

    memo: dict[tuple[frozenset[int], int, int], Plan] = {}
    group_plan = greedy_plan(
        action.residuals,
        1,
        1,
        config,
        neural_scorer=None,
        memo=memo,
    )
    rest_plan = greedy_plan(
        action.rest,
        0,
        0,
        config,
        neural_scorer=None,
        memo=memo,
    )
    plan = Plan(
        "linear_factor" if action.linear else "factor",
        state_terms,
        factor_cost(action, group_plan, rest_plan, 0, config),
        factor=action.factor,
        group=group_plan,
        rest=rest_plan,
        affine_const=action.affine_const,
    )
    # PlanTrace performs the canonical recursive ANF validation and refuses a
    # misaligned/tampered action before any physical proxy can affect utility.
    PlanTrace.from_plan(plan)
    return plan


class RootRolloutExecutionUtilityAdjuster:
    """Compile exact root rollout candidates before shared scheduler selection."""

    def __init__(
        self,
        *,
        n_inputs: int,
        search_config: SearchConfig,
        profile_spec: SyntheticExecutionProfileSpec,
        penalty_weights: FrozenExecutionPenaltyWeights,
        expected_profile_sha256: str,
        execution_n_qubits: int | None = None,
        risk_model: RidgeExecutionCostModel | None = None,
        expected_risk_model_sha256: str | None = None,
    ) -> None:
        if isinstance(n_inputs, bool) or not isinstance(n_inputs, int) or n_inputs <= 0:
            raise ValueError("n_inputs must be a positive integer")
        if not isinstance(search_config, SearchConfig):
            raise TypeError("search_config must be SearchConfig")
        if execution_n_qubits is not None:
            if (
                isinstance(execution_n_qubits, bool)
                or not isinstance(execution_n_qubits, int)
                or execution_n_qubits < n_inputs + 1
            ):
                raise ValueError(
                    "execution_n_qubits must accommodate inputs plus target"
                )
        if not isinstance(profile_spec, SyntheticExecutionProfileSpec):
            raise TypeError("profile_spec must be SyntheticExecutionProfileSpec")
        if not isinstance(penalty_weights, FrozenExecutionPenaltyWeights):
            raise TypeError("penalty_weights must be FrozenExecutionPenaltyWeights")
        expected_profile = _sha256(
            expected_profile_sha256, "expected_profile_sha256"
        )
        if profile_spec.profile_sha256 != expected_profile:
            raise ValueError("profile SHA-256 does not match the declared profile")
        if penalty_weights.profile_sha256 != expected_profile:
            raise ValueError("penalty weights are bound to a different profile SHA-256")

        if risk_model is None:
            if expected_risk_model_sha256 is not None:
                raise ValueError("expected risk-model SHA was provided without a risk model")
            if penalty_weights.model_risk != 0.0:
                raise ValueError("model_risk weight must be zero when no risk model is configured")
            risk_metadata: dict[str, object] | None = None
            risk_sha: str | None = None
        else:
            if not isinstance(risk_model, RidgeExecutionCostModel):
                raise TypeError("risk_model must be a frozen RidgeExecutionCostModel")
            if expected_risk_model_sha256 is None:
                raise ValueError("a frozen risk model requires expected_risk_model_sha256")
            risk_metadata = risk_model.metadata()
            risk_sha = _sha256(risk_metadata["model_sha256"], "risk model SHA-256")
            expected_risk = _sha256(
                expected_risk_model_sha256, "expected_risk_model_sha256"
            )
            if risk_sha != expected_risk:
                raise ValueError("risk-model SHA-256 does not match the frozen model")

        self.n_inputs = n_inputs
        self.execution_n_qubits = execution_n_qubits
        self.search_config = search_config
        self.profile_spec = profile_spec
        self.penalty_weights = penalty_weights
        self.risk_model = risk_model
        self._risk_metadata = risk_metadata
        self._risk_sha256 = risk_sha

        base_metadata = self._base_metadata()
        self.adjuster_sha256 = sha256_bytes(canonical_json_bytes(base_metadata))

    def _base_metadata(self) -> dict[str, object]:
        search_config_payload = asdict(self.search_config)
        return {
            "schema": ADJUSTER_SCHEMA,
            "n_inputs": self.n_inputs,
            "execution_n_qubits": self.execution_n_qubits,
            "search_config": search_config_payload,
            "search_config_sha256": sha256_bytes(
                canonical_json_bytes(search_config_payload)
            ),
            "profile": self.profile_spec.canonical_payload(),
            "profile_sha256": self.profile_spec.profile_sha256,
            "penalty_weights": self.penalty_weights.canonical_payload(),
            "penalty_weights_sha256": self.penalty_weights.weights_sha256,
            "risk_model_enabled": self.risk_model is not None,
            "risk_model_sha256": self._risk_sha256,
            "risk_model_metadata": self._risk_metadata,
            "rollout": "root-action-scorer-free-greedy-completion-v1",
            "candidate_ordering_contract": (
                "each penalty is candidate-local; reordering aligned actions and raw "
                "utilities only reorders outputs"
            ),
            "penalty_normalization": "none",
            "heldout_noisy_outcome_input": False,
            "hardware_execution": False,
            "performance_evidence": False,
            "claim_boundary": EXECUTION_AWARE_CLAIM_BOUNDARY,
        }

    def _validate_risk_model_frozen(self) -> None:
        if self.risk_model is None:
            return
        current_metadata = self.risk_model.metadata()
        current_sha = _sha256(
            current_metadata["model_sha256"], "current risk model SHA-256"
        )
        if current_sha != self._risk_sha256 or current_metadata != self._risk_metadata:
            raise RuntimeError("risk model changed after its SHA-256 was frozen")

    def _compile_candidate(
        self,
        state_key: "StateKey",
        action: FactorAction,
        candidate_index: int,
    ) -> dict[str, object]:
        terms, _, _ = _state_parts(state_key)
        if terms and max(terms).bit_length() > self.n_inputs:
            raise ValueError("state terms exceed the declared n_inputs width")
        plan = complete_root_action_rollout(state_key, action, self.search_config)
        allocated_ancilla = min(
            self.search_config.max_factor_ancilla,
            int(plan.cost.explicit_ancilla),
        )
        circuit = emit_plan_to_circuit(plan, self.n_inputs, allocated_ancilla)
        if self.execution_n_qubits is not None:
            if circuit.n_qubits > self.execution_n_qubits:
                raise ValueError(
                    "candidate circuit exceeds frozen execution_n_qubits"
                )
            if circuit.n_qubits < self.execution_n_qubits:
                padded = QuantumCircuit(self.execution_n_qubits)
                padded.gates = list(circuit.gates)
                circuit = padded
        circuit_check = verify_circuit_anf(circuit, self.n_inputs, frozenset(terms))
        if not circuit_check.ok:
            raise ValueError("candidate rollout circuit does not preserve the state ANF")
        profile = self.profile_spec.build(circuit.n_qubits)
        compilation = compile_superconducting(circuit, profile)
        diagnostics = compilation.diagnostics
        duration_ns = math.fsum(
            (
                diagnostics.one_qubit_gate_count
                * self.profile_spec.one_qubit_duration_ns,
                diagnostics.two_qubit_gate_count
                * self.profile_spec.two_qubit_duration_ns,
            )
        )
        if not math.isfinite(duration_ns) or duration_ns < 0.0:
            raise RuntimeError("duration proxy is non-finite")
        concrete_profile_payload = {
            "name": profile.name,
            "topology_family": profile.topology_family,
            "n_qubits": profile.n_qubits,
            "coupling_edges": [list(edge) for edge in profile.coupling_edges],
            "native_gate_set": list(profile.native_gate_set),
            "noise": asdict(profile.noise),
            "synthetic": profile.synthetic,
            "calibration_source": profile.calibration_source,
        }
        plan_payload = PlanTrace.from_plan(plan).to_dict()
        return {
            "candidate_index": candidate_index,
            "action_sha256": _action_sha256(action),
            "plan_sha256": sha256_bytes(canonical_json_bytes(plan_payload)),
            "logical_n_qubits": circuit.n_qubits,
            "allocated_factor_ancilla": allocated_ancilla,
            "plan_anf_ok": True,
            "circuit_anf_ok": True,
            "concrete_profile_name": profile.name,
            "profile_spec_sha256": self.profile_spec.profile_sha256,
            "concrete_profile_sha256": sha256_bytes(
                canonical_json_bytes(concrete_profile_payload)
            ),
            "native_one_qubit": diagnostics.one_qubit_gate_count,
            "native_two_qubit": diagnostics.two_qubit_gate_count,
            "inserted_swap": diagnostics.inserted_swap_count,
            "native_depth": diagnostics.native_depth,
            "duration_ns": duration_ns,
            "synthetic_profile": True,
            "hardware_execution": False,
        }

    def adjust(
        self,
        state_key: "StateKey",
        actions: Sequence[FactorAction],
        raw_utilities: Sequence[float],
    ) -> ExecutionUtilityAdjustment:
        terms, prefix_len, live_ancilla = _state_parts(state_key)
        if prefix_len != 0 or live_ancilla != 0:
            raise ValueError("execution-aware utility is root-only")
        if terms and max(terms).bit_length() > self.n_inputs:
            raise ValueError("state terms exceed the declared n_inputs width")
        if isinstance(actions, (str, bytes)):
            raise TypeError("actions must be a sequence of FactorAction objects")
        actions_tuple = tuple(actions)
        raw = tuple(_finite(value, "raw_utilities") for value in raw_utilities)
        if len(actions_tuple) != len(raw):
            raise ValueError("raw utility count must match the candidate action count")
        # Validate and freeze exact alignment before either model prediction or
        # compilation. Duplicate signatures are rejected because index-only
        # provenance would otherwise be ambiguous under pool permutations.
        action_hashes = tuple(_action_sha256(action) for action in actions_tuple)
        if len(set(action_hashes)) != len(action_hashes):
            raise ValueError("candidate actions must have unique signatures")

        if self.risk_model is None:
            risk_predictions = (0.0,) * len(actions_tuple)
        else:
            self._validate_risk_model_frozen()
            predicted = self.risk_model.predict(state_key, actions_tuple)
            risk_predictions = tuple(
                _finite_nonnegative(value, "predicted model risk") for value in predicted
            )
            if len(risk_predictions) != len(actions_tuple):
                raise RuntimeError("risk prediction count does not match candidate actions")

        candidate_records: list[dict[str, object]] = []
        penalties: list[float] = []
        adjusted: list[float] = []
        weights = self.penalty_weights
        for index, (action, raw_utility, model_risk) in enumerate(
            zip(actions_tuple, raw, risk_predictions)
        ):
            record = self._compile_candidate(state_key, action, index)
            if record["action_sha256"] != action_hashes[index]:
                raise RuntimeError("compiled candidate/action alignment changed unexpectedly")
            resources = {
                "native_one_qubit": float(record["native_one_qubit"]),
                "native_two_qubit": float(record["native_two_qubit"]),
                "inserted_swap": float(record["inserted_swap"]),
                "native_depth": float(record["native_depth"]),
                "duration_ns": float(record["duration_ns"]),
                "model_risk": model_risk,
            }
            contributions = {
                name: resources[name] * float(getattr(weights, name))
                for name in resources
            }
            if any(
                not math.isfinite(value) or value < 0.0
                for value in contributions.values()
            ):
                raise RuntimeError("execution penalty contribution is non-finite")
            total_penalty = math.fsum(contributions.values())
            adjusted_utility = raw_utility - total_penalty
            if not math.isfinite(adjusted_utility):
                raise RuntimeError("adjusted execution-aware utility is non-finite")
            penalties.append(total_penalty)
            adjusted.append(adjusted_utility)
            candidate_records.append(
                {
                    **record,
                    "raw_utility": raw_utility,
                    "adjusted_utility": adjusted_utility,
                    "resource_components": resources,
                    "penalty_contributions": contributions,
                    "total_penalty": total_penalty,
                }
            )

        metadata = {**self._base_metadata(), "adjuster_sha256": self.adjuster_sha256}
        diagnostics: Mapping[str, object] = {
            "schema": ADJUSTER_SCHEMA,
            "raw_utilities": list(raw),
            "adjusted_utilities": list(adjusted),
            "candidate_action_sha256": list(action_hashes),
            "candidates": candidate_records,
            "heldout_noisy_outcome_used": False,
            "synthetic_proxy_only": True,
            "hardware_execution": False,
            "performance_evidence": False,
            "claim_boundary": EXECUTION_AWARE_CLAIM_BOUNDARY,
        }
        return ExecutionUtilityAdjustment(
            adjusted_utilities=tuple(adjusted),
            predicted_execution_costs=risk_predictions,
            normalized_execution_penalties=tuple(penalties),
            penalty_weight=1.0,
            cost_offset=0.0,
            cost_scale=1.0,
            model_metadata=metadata,
            model_sha256=self.adjuster_sha256,
            diagnostics=diagnostics,
        )


def make_root_rollout_execution_utility_adjuster(
    *,
    n_inputs: int,
    search_config: SearchConfig,
    profile_spec: SyntheticExecutionProfileSpec,
    penalty_weights: FrozenExecutionPenaltyWeights,
    expected_profile_sha256: str,
    execution_n_qubits: int | None = None,
    risk_model: RidgeExecutionCostModel | None = None,
    expected_risk_model_sha256: str | None = None,
) -> RootRolloutExecutionUtilityAdjuster:
    """Runner-facing adapter; does not alter the public ``synthesize`` API."""

    return RootRolloutExecutionUtilityAdjuster(
        n_inputs=n_inputs,
        search_config=search_config,
        profile_spec=profile_spec,
        penalty_weights=penalty_weights,
        expected_profile_sha256=expected_profile_sha256,
        execution_n_qubits=execution_n_qubits,
        risk_model=risk_model,
        expected_risk_model_sha256=expected_risk_model_sha256,
    )


__all__ = [
    "ADJUSTER_SCHEMA",
    "EXECUTION_AWARE_CLAIM_BOUNDARY",
    "FrozenExecutionPenaltyWeights",
    "PROFILE_SCHEMA",
    "RootRolloutExecutionUtilityAdjuster",
    "SyntheticExecutionProfileSpec",
    "WEIGHT_SCHEMA",
    "complete_root_action_rollout",
    "make_root_rollout_execution_utility_adjuster",
]
