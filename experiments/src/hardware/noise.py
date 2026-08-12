"""Seeded small-scale noisy execution for compiled superconducting circuits.

The simulator in this module executes every shot as a statevector quantum
trajectory.  It applies the compiled native gate, samples an independent
Pauli error channel after that gate, samples a projective measurement, and
then applies independent classical readout flips.  Consequently, its noisy
results are executions of the declared stochastic model rather than an
analytic reliability proxy.

This backend is intentionally narrow.  It is suitable for small synthetic
topologies used in auditable experiments; it is not a device calibration,
hardware run, pulse simulation, or model of relaxation, leakage, crosstalk,
or time-correlated noise.
"""

from __future__ import annotations

from dataclasses import dataclass
import cmath
import math
from numbers import Integral, Real
from typing import Iterable

import numpy as np

from .superconducting import (
    NativeGate,
    NoiseParameters,
    SuperconductingCompilation,
)


PAULI_NOISE_MODEL = "independent-pauli-depolarizing-v1"
EXECUTION_METHOD = "seeded-statevector-pauli-trajectory-shots-v1"
MAX_TRAJECTORY_QUBITS = 10
MAX_TRAJECTORY_SHOTS = 100_000

CLAIM_BOUNDARY = (
    "Actual seeded statevector trajectories for an explicit independent "
    "Pauli-depolarizing and readout-bitflip model on a declared synthetic "
    "topology. Small-scale simulation only: not calibrated hardware, a pulse "
    "model, or evidence about relaxation, leakage, crosstalk, correlated "
    "noise, quantum speedup, or quantum advantage."
)


class NoisySimulationError(ValueError):
    """Raised when a noisy-execution request is outside the strict contract."""


def _probability(value: object, label: str) -> float:
    if not isinstance(value, Real) or isinstance(value, (bool, np.bool_)):
        raise NoisySimulationError(f"{label} must be a real number")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
        raise NoisySimulationError(f"{label} must be finite and in [0, 1]")
    return normalized


@dataclass(frozen=True)
class PauliNoiseModel:
    """Independent stochastic channels applied by :func:`simulate_noisy_shots`.

    ``one_qubit_error`` is the total probability of applying one uniformly
    sampled non-identity Pauli from ``{X, Y, Z}`` after a one-qubit native
    gate.  ``two_qubit_error`` similarly samples one of the 15 non-identity
    tensor products from ``{I, X, Y, Z}^{\u22972}`` after a CX.  Readout flips are
    sampled independently on every measured physical qubit before the final
    logical-layout decode.
    """

    one_qubit_error: float = 0.0
    two_qubit_error: float = 0.0
    readout_error: float = 0.0
    model: str = PAULI_NOISE_MODEL
    parameter_source: str = "explicit-synthetic"
    synthetic: bool = True
    calibration_source: None = None

    def __post_init__(self) -> None:
        if self.model != PAULI_NOISE_MODEL:
            raise NoisySimulationError(
                f"model must be exactly {PAULI_NOISE_MODEL!r}"
            )
        if not isinstance(self.parameter_source, str) or not self.parameter_source:
            raise NoisySimulationError("parameter_source must be a non-empty string")
        if self.synthetic is not True or self.calibration_source is not None:
            raise NoisySimulationError(
                "this backend accepts synthetic, uncalibrated noise models only"
            )
        for label in (
            "one_qubit_error",
            "two_qubit_error",
            "readout_error",
        ):
            object.__setattr__(self, label, _probability(getattr(self, label), label))

    @classmethod
    def from_parameters(
        cls,
        parameters: NoiseParameters,
        *,
        parameter_source: str,
    ) -> "PauliNoiseModel":
        """Translate profile parameters into the exact executable channel."""

        if not isinstance(parameters, NoiseParameters):
            raise NoisySimulationError("parameters must be NoiseParameters")
        return cls(
            one_qubit_error=parameters.one_qubit_error,
            two_qubit_error=parameters.two_qubit_error,
            readout_error=parameters.readout_error,
            parameter_source=f"{parameter_source}:{parameters.model}",
        )

    @property
    def has_nonzero_probability(self) -> bool:
        return any(
            probability > 0.0
            for probability in (
                self.one_qubit_error,
                self.two_qubit_error,
                self.readout_error,
            )
        )


@dataclass(frozen=True)
class NoiseEventCounts:
    """Channel opportunities and sampled events accumulated over all shots."""

    one_qubit_channel_trials: int
    one_qubit_error_events: int
    two_qubit_channel_trials: int
    two_qubit_error_events: int
    readout_channel_trials: int
    readout_bit_flips: int

    @property
    def sampled_noise_events(self) -> int:
        return (
            self.one_qubit_error_events
            + self.two_qubit_error_events
            + self.readout_bit_flips
        )


@dataclass(frozen=True)
class NoisyExecutionResult:
    """Empirical logical-output result of a real stochastic simulation run."""

    success_rate: float
    success_count: int
    counts: dict[str, int]
    shots: int
    seed: int
    logical_input_bits: tuple[int, ...]
    expected_logical_bits: tuple[int, ...]
    expected_bitstring: str
    bitstring_order: str
    final_logical_to_physical: tuple[int, ...]
    noise_model: PauliNoiseModel
    events: NoiseEventCounts
    execution_method: str
    actual_noisy_simulation: bool
    hardware_execution: bool
    noise_applied: bool
    claim_boundary: str


_I = np.eye(2, dtype=np.complex128)
_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_SX = 0.5 * np.array(
    [[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]],
    dtype=np.complex128,
)
_PAULIS = (_I, _X, _Y, _Z)


def _positive_integer(value: object, label: str, maximum: int) -> int:
    if not isinstance(value, Integral) or isinstance(value, (bool, np.bool_)):
        raise NoisySimulationError(f"{label} must be an integer")
    normalized = int(value)
    if not 1 <= normalized <= maximum:
        raise NoisySimulationError(f"{label} must be in [1, {maximum}]")
    return normalized


def _seed(value: object) -> int:
    if not isinstance(value, Integral) or isinstance(value, (bool, np.bool_)):
        raise NoisySimulationError("seed must be an integer")
    normalized = int(value)
    if not 0 <= normalized < 2**64:
        raise NoisySimulationError("seed must be in [0, 2**64)")
    return normalized


def _logical_bits(values: Iterable[int], n_qubits: int) -> tuple[int, ...]:
    try:
        bits = tuple(values)
    except TypeError as exc:
        raise NoisySimulationError("logical_input_bits must be iterable") from exc
    if len(bits) != n_qubits:
        raise NoisySimulationError(
            "logical_input_bits must contain exactly one bit per qubit"
        )
    if any(
        not isinstance(bit, Integral)
        or isinstance(bit, (bool, np.bool_))
        or int(bit) not in (0, 1)
        for bit in bits
    ):
        raise NoisySimulationError("logical_input_bits must contain only integer 0/1")
    return tuple(int(bit) for bit in bits)


def _validate_mapping(mapping: object, n_qubits: int, label: str) -> tuple[int, ...]:
    try:
        normalized = tuple(mapping)  # type: ignore[arg-type]
    except TypeError as exc:
        raise NoisySimulationError(f"{label} must be iterable") from exc
    if len(normalized) != n_qubits:
        raise NoisySimulationError(f"{label} must be a qubit permutation")
    if any(
        not isinstance(qubit, Integral)
        or isinstance(qubit, (bool, np.bool_))
        for qubit in normalized
    ):
        raise NoisySimulationError(f"{label} must contain integer qubits")
    integer_mapping = tuple(int(qubit) for qubit in normalized)
    if set(integer_mapping) != set(range(n_qubits)):
        raise NoisySimulationError(f"{label} must be a qubit permutation")
    return integer_mapping


def _validate_native_gate(gate: object, n_qubits: int, index: int) -> NativeGate:
    if not isinstance(gate, NativeGate):
        raise NoisySimulationError(f"native gate {index} must be NativeGate")
    expected_arity = {"rz": 1, "sx": 1, "x": 1, "cx": 2}
    if gate.name not in expected_arity:
        raise NoisySimulationError(
            f"native gate {index} has unsupported name {gate.name!r}"
        )
    if len(gate.qubits) != expected_arity[gate.name]:
        raise NoisySimulationError(
            f"native gate {index} has invalid arity for {gate.name}"
        )
    if any(
        not isinstance(qubit, Integral)
        or isinstance(qubit, (bool, np.bool_))
        or not 0 <= int(qubit) < n_qubits
        for qubit in gate.qubits
    ):
        raise NoisySimulationError(f"native gate {index} has an invalid qubit")
    if len(set(gate.qubits)) != len(gate.qubits):
        raise NoisySimulationError(f"native gate {index} repeats a qubit")
    if gate.name == "rz":
        if (
            not isinstance(gate.angle, Real)
            or isinstance(gate.angle, (bool, np.bool_))
            or not math.isfinite(float(gate.angle))
        ):
            raise NoisySimulationError(f"native gate {index} needs a finite rz angle")
    elif gate.angle is not None:
        raise NoisySimulationError(
            f"native gate {index} must not carry an angle for {gate.name}"
        )
    return gate


def _validate_compilation(
    compilation: object,
    *,
    max_qubits: int,
) -> tuple[
    SuperconductingCompilation,
    tuple[int, ...],
    tuple[int, ...],
    tuple[NativeGate, ...],
]:
    if not isinstance(compilation, SuperconductingCompilation):
        raise NoisySimulationError("compilation must be SuperconductingCompilation")
    n_qubits = compilation.profile.n_qubits
    if n_qubits != compilation.logical_ir.n_qubits:
        raise NoisySimulationError("profile and logical IR qubit counts differ")
    if n_qubits > max_qubits:
        raise NoisySimulationError(
            f"trajectory simulation is capped at {max_qubits} qubits"
        )
    initial = _validate_mapping(
        compilation.diagnostics.initial_logical_to_physical,
        n_qubits,
        "initial_logical_to_physical",
    )
    final = _validate_mapping(
        compilation.diagnostics.final_logical_to_physical,
        n_qubits,
        "final_logical_to_physical",
    )
    gates = tuple(
        _validate_native_gate(gate, n_qubits, index)
        for index, gate in enumerate(compilation.native_gates)
    )
    return compilation, initial, final, gates


def _resolve_noise_model(
    compilation: SuperconductingCompilation,
    noise_model: PauliNoiseModel | NoiseParameters | None,
) -> PauliNoiseModel:
    if noise_model is None:
        return PauliNoiseModel.from_parameters(
            compilation.profile.noise,
            parameter_source=f"profile:{compilation.profile.name}",
        )
    if isinstance(noise_model, PauliNoiseModel):
        return noise_model
    if isinstance(noise_model, NoiseParameters):
        return PauliNoiseModel.from_parameters(
            noise_model,
            parameter_source="explicit-noise-parameters",
        )
    raise NoisySimulationError(
        "noise_model must be PauliNoiseModel, NoiseParameters, or None"
    )


def _apply_one_qubit(
    state: np.ndarray,
    qubit: int,
    matrix: np.ndarray,
) -> None:
    stride = 1 << qubit
    period = stride << 1
    for start in range(0, state.size, period):
        for offset in range(stride):
            i0 = start + offset
            i1 = i0 + stride
            a0, a1 = state[i0], state[i1]
            state[i0] = matrix[0, 0] * a0 + matrix[0, 1] * a1
            state[i1] = matrix[1, 0] * a0 + matrix[1, 1] * a1


def _apply_cx(state: np.ndarray, control: int, target: int) -> None:
    for index in range(state.size):
        if ((index >> control) & 1) and not ((index >> target) & 1):
            partner = index | (1 << target)
            state[index], state[partner] = state[partner], state[index]


def _apply_native_gate(state: np.ndarray, gate: NativeGate) -> None:
    if gate.name == "x":
        _apply_one_qubit(state, gate.qubits[0], _X)
    elif gate.name == "sx":
        _apply_one_qubit(state, gate.qubits[0], _SX)
    elif gate.name == "rz":
        angle = float(gate.angle)
        matrix = np.array(
            [
                [cmath.exp(-0.5j * angle), 0.0],
                [0.0, cmath.exp(0.5j * angle)],
            ],
            dtype=np.complex128,
        )
        _apply_one_qubit(state, gate.qubits[0], matrix)
    else:
        _apply_cx(state, gate.qubits[0], gate.qubits[1])


def _apply_one_qubit_depolarizing(
    state: np.ndarray,
    qubit: int,
    rng: np.random.Generator,
) -> None:
    pauli_index = int(rng.integers(1, 4))
    _apply_one_qubit(state, qubit, _PAULIS[pauli_index])


def _apply_two_qubit_depolarizing(
    state: np.ndarray,
    qubits: tuple[int, int],
    rng: np.random.Generator,
) -> None:
    # Codes 1..15 enumerate all products except I\u2297I exactly once.
    pauli_code = int(rng.integers(1, 16))
    first, second = divmod(pauli_code, 4)
    if first:
        _apply_one_qubit(state, qubits[0], _PAULIS[first])
    if second:
        _apply_one_qubit(state, qubits[1], _PAULIS[second])


def _simulate_logical(
    compilation: SuperconductingCompilation,
    input_bits: tuple[int, ...],
) -> tuple[int, ...]:
    output = list(input_bits)
    for gate in compilation.logical_ir.gates:
        if gate.gate_type == "X":
            output[gate.target] ^= 1
        elif gate.gate_type == "CNOT":
            if output[gate.controls[0]]:
                output[gate.target] ^= 1
        elif all(output[control] for control in gate.controls):
            output[gate.target] ^= 1
    return tuple(output)


def _bitstring(logical_bits: tuple[int, ...]) -> str:
    """Return standard display order q[n-1]...q[0]."""

    return "".join(str(bit) for bit in reversed(logical_bits))


def simulate_noisy_shots(
    compilation: SuperconductingCompilation,
    logical_input_bits: Iterable[int],
    *,
    shots: int,
    seed: int,
    noise_model: PauliNoiseModel | NoiseParameters | None = None,
    max_qubits: int = MAX_TRAJECTORY_QUBITS,
) -> NoisyExecutionResult:
    """Execute seeded native-gate trajectories and return decoded counts.

    Counts are keyed by logical bitstrings in ``q[n-1]...q[0]`` display order.
    Measurement is performed on physical wires, readout error is applied on
    those wires, and the observed bits are then decoded with
    ``final_logical_to_physical``.  ``success_rate`` is the empirical fraction
    equal to the ideal logical-circuit output for the requested basis input.
    """

    checked_shots = _positive_integer(shots, "shots", MAX_TRAJECTORY_SHOTS)
    checked_seed = _seed(seed)
    checked_max_qubits = _positive_integer(
        max_qubits,
        "max_qubits",
        MAX_TRAJECTORY_QUBITS,
    )
    checked, initial_mapping, final_mapping, gates = _validate_compilation(
        compilation,
        max_qubits=checked_max_qubits,
    )
    n_qubits = checked.profile.n_qubits
    input_bits = _logical_bits(logical_input_bits, n_qubits)
    model = _resolve_noise_model(checked, noise_model)
    expected_bits = _simulate_logical(checked, input_bits)
    expected_bitstring = _bitstring(expected_bits)

    initial_index = sum(
        bit << initial_mapping[logical]
        for logical, bit in enumerate(input_bits)
    )
    initial_state = np.zeros(1 << n_qubits, dtype=np.complex128)
    initial_state[initial_index] = 1.0
    rng = np.random.default_rng(checked_seed)

    one_qubit_events = 0
    two_qubit_events = 0
    readout_flips = 0
    success_count = 0
    counts: dict[str, int] = {}
    one_qubit_gate_count = sum(len(gate.qubits) == 1 for gate in gates)
    two_qubit_gate_count = sum(len(gate.qubits) == 2 for gate in gates)

    for _ in range(checked_shots):
        state = initial_state.copy()
        for gate in gates:
            _apply_native_gate(state, gate)
            if len(gate.qubits) == 1:
                if (
                    model.one_qubit_error > 0.0
                    and rng.random() < model.one_qubit_error
                ):
                    _apply_one_qubit_depolarizing(state, gate.qubits[0], rng)
                    one_qubit_events += 1
            elif (
                model.two_qubit_error > 0.0
                and rng.random() < model.two_qubit_error
            ):
                _apply_two_qubit_depolarizing(state, gate.qubits, rng)
                two_qubit_events += 1

        probabilities = np.abs(state) ** 2
        norm = float(probabilities.sum())
        if not math.isfinite(norm) or norm <= 0.0:
            raise NoisySimulationError("trajectory produced an invalid state norm")
        probabilities /= norm
        physical_index = int(rng.choice(state.size, p=probabilities))
        physical_bits = [
            (physical_index >> physical_qubit) & 1
            for physical_qubit in range(n_qubits)
        ]
        if model.readout_error > 0.0:
            for physical_qubit in range(n_qubits):
                if rng.random() < model.readout_error:
                    physical_bits[physical_qubit] ^= 1
                    readout_flips += 1
        observed_logical = tuple(
            physical_bits[final_mapping[logical]]
            for logical in range(n_qubits)
        )
        observed_bitstring = _bitstring(observed_logical)
        counts[observed_bitstring] = counts.get(observed_bitstring, 0) + 1
        if observed_logical == expected_bits:
            success_count += 1

    events = NoiseEventCounts(
        one_qubit_channel_trials=checked_shots * one_qubit_gate_count,
        one_qubit_error_events=one_qubit_events,
        two_qubit_channel_trials=checked_shots * two_qubit_gate_count,
        two_qubit_error_events=two_qubit_events,
        readout_channel_trials=checked_shots * n_qubits,
        readout_bit_flips=readout_flips,
    )
    return NoisyExecutionResult(
        success_rate=success_count / checked_shots,
        success_count=success_count,
        counts=dict(sorted(counts.items())),
        shots=checked_shots,
        seed=checked_seed,
        logical_input_bits=input_bits,
        expected_logical_bits=expected_bits,
        expected_bitstring=expected_bitstring,
        bitstring_order="logical-q[n-1]...q[0]",
        final_logical_to_physical=final_mapping,
        noise_model=model,
        events=events,
        execution_method=EXECUTION_METHOD,
        actual_noisy_simulation=True,
        hardware_execution=False,
        noise_applied=model.has_nonzero_probability,
        claim_boundary=CLAIM_BOUNDARY,
    )


__all__ = [
    "CLAIM_BOUNDARY",
    "EXECUTION_METHOD",
    "MAX_TRAJECTORY_QUBITS",
    "MAX_TRAJECTORY_SHOTS",
    "PAULI_NOISE_MODEL",
    "NoiseEventCounts",
    "NoisyExecutionResult",
    "NoisySimulationError",
    "PauliNoiseModel",
    "simulate_noisy_shots",
]
