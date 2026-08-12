"""Contract tests for actual small-scale Pauli-trajectory execution."""

from __future__ import annotations

from dataclasses import replace
import math

import pytest

from src.hardware.noise import (
    MAX_TRAJECTORY_QUBITS,
    MAX_TRAJECTORY_SHOTS,
    NoisySimulationError,
    PauliNoiseModel,
    simulate_noisy_shots,
)
from src.hardware.superconducting import (
    NativeGate,
    NoiseParameters,
    compile_superconducting,
    heavy_hex_like_profile,
    linear_profile,
)
from src.sshr_lib.bool_func import QuantumCircuit


def _zero_noise() -> PauliNoiseModel:
    return PauliNoiseModel(parameter_source="unit-test-zero")


def test_zero_noise_x_and_cnot_match_ideal_basis_output() -> None:
    circuit = QuantumCircuit(2)
    circuit.add_x(0)
    circuit.add_cnot(0, 1)
    compiled = compile_superconducting(circuit, linear_profile(2))

    result = simulate_noisy_shots(
        compiled,
        (0, 0),
        shots=64,
        seed=7,
        noise_model=_zero_noise(),
    )

    assert result.expected_logical_bits == (1, 1)
    assert result.expected_bitstring == "11"
    assert result.counts == {"11": 64}
    assert result.success_count == 64
    assert result.success_rate == 1.0
    assert result.noise_applied is False
    assert result.actual_noisy_simulation is True
    assert result.hardware_execution is False
    assert result.events.sampled_noise_events == 0
    assert "not calibrated hardware" in result.claim_boundary


def test_routed_cnot_is_decoded_with_final_logical_physical_mapping() -> None:
    circuit = QuantumCircuit(4)
    circuit.add_cnot(0, 3)
    compiled = compile_superconducting(circuit, linear_profile(4))
    assert compiled.diagnostics.final_logical_to_physical != (0, 1, 2, 3)

    result = simulate_noisy_shots(
        compiled,
        (1, 0, 0, 0),
        shots=48,
        seed=9,
        noise_model=_zero_noise(),
    )

    assert result.final_logical_to_physical == (2, 0, 1, 3)
    assert result.expected_logical_bits == (1, 0, 0, 1)
    assert result.counts == {"1001": 48}
    assert result.success_rate == 1.0


def test_small_mct_trajectory_matches_ideal_at_zero_noise() -> None:
    circuit = QuantumCircuit(3)
    circuit.add_mct([0, 1], 2)
    compiled = compile_superconducting(circuit, heavy_hex_like_profile(3))

    firing = simulate_noisy_shots(
        compiled,
        (1, 1, 0),
        shots=32,
        seed=11,
        noise_model=_zero_noise(),
    )
    idle = simulate_noisy_shots(
        compiled,
        (1, 0, 0),
        shots=32,
        seed=11,
        noise_model=_zero_noise(),
    )

    assert firing.counts == {"111": 32}
    assert idle.counts == {"001": 32}
    assert firing.success_rate == idle.success_rate == 1.0


def test_one_and_two_qubit_pauli_channels_are_actually_sampled() -> None:
    one_qubit = QuantumCircuit(1)
    one_qubit.add_x(0)
    one_compiled = compile_superconducting(one_qubit, linear_profile(1))
    one_result = simulate_noisy_shots(
        one_compiled,
        (0,),
        shots=600,
        seed=21,
        noise_model=PauliNoiseModel(
            one_qubit_error=1.0,
            parameter_source="unit-test-one-qubit",
        ),
    )
    assert one_result.events.one_qubit_channel_trials == 600
    assert one_result.events.one_qubit_error_events == 600
    assert set(one_result.counts) == {"0", "1"}
    assert 0.25 < one_result.success_rate < 0.45

    two_qubit = QuantumCircuit(2)
    two_qubit.add_cnot(0, 1)
    two_compiled = compile_superconducting(two_qubit, linear_profile(2))
    two_result = simulate_noisy_shots(
        two_compiled,
        (1, 0),
        shots=600,
        seed=22,
        noise_model=PauliNoiseModel(
            two_qubit_error=1.0,
            parameter_source="unit-test-two-qubit",
        ),
    )
    assert two_result.events.two_qubit_channel_trials == 600
    assert two_result.events.two_qubit_error_events == 600
    assert two_result.events.sampled_noise_events == 600
    assert two_result.success_rate < 0.35


def test_readout_probability_one_flips_every_physical_measurement() -> None:
    circuit = QuantumCircuit(2)
    circuit.add_x(0)
    compiled = compile_superconducting(circuit, linear_profile(2))
    result = simulate_noisy_shots(
        compiled,
        (0, 0),
        shots=40,
        seed=31,
        noise_model=PauliNoiseModel(
            readout_error=1.0,
            parameter_source="unit-test-readout",
        ),
    )

    assert result.expected_bitstring == "01"
    assert result.counts == {"10": 40}
    assert result.success_rate == 0.0
    assert result.events.readout_channel_trials == 80
    assert result.events.readout_bit_flips == 80


def test_fixed_seed_reproduces_counts_and_event_accounting() -> None:
    noise = NoiseParameters(
        model="synthetic-test-rates-v1",
        one_qubit_error=0.17,
        two_qubit_error=0.23,
        readout_error=0.11,
    )
    circuit = QuantumCircuit(3)
    circuit.add_x(0)
    circuit.add_cnot(0, 2)
    compiled = compile_superconducting(circuit, linear_profile(3, noise=noise))

    first = simulate_noisy_shots(compiled, (0, 1, 0), shots=128, seed=41)
    second = simulate_noisy_shots(compiled, (0, 1, 0), shots=128, seed=41)
    different = simulate_noisy_shots(compiled, (0, 1, 0), shots=128, seed=42)

    assert first == second
    assert first.noise_model.model == "independent-pauli-depolarizing-v1"
    assert first.noise_model.parameter_source.endswith("synthetic-test-rates-v1")
    assert first.noise_applied is True
    assert (first.counts, first.events) != (different.counts, different.events)
    assert sum(first.counts.values()) == first.shots


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"shots": 0, "seed": 1}, "shots"),
        ({"shots": True, "seed": 1}, "shots"),
        ({"shots": MAX_TRAJECTORY_SHOTS + 1, "seed": 1}, "shots"),
        ({"shots": 1, "seed": -1}, "seed"),
        ({"shots": 1, "seed": True}, "seed"),
        ({"shots": 1, "seed": 2**64}, "seed"),
        ({"shots": 1, "seed": 1, "max_qubits": 0}, "max_qubits"),
    ],
)
def test_invalid_shot_seed_and_limits_are_rejected(kwargs, message: str) -> None:
    compiled = compile_superconducting(QuantumCircuit(1), linear_profile(1))
    with pytest.raises(NoisySimulationError, match=message):
        simulate_noisy_shots(compiled, (0,), **kwargs)


@pytest.mark.parametrize(
    ("bits", "message"),
    [
        ((0,), "exactly"),
        ((0, 2), "integer 0/1"),
        ((False, 0), "integer 0/1"),
    ],
)
def test_invalid_logical_inputs_are_rejected(bits, message: str) -> None:
    compiled = compile_superconducting(QuantumCircuit(2), linear_profile(2))
    with pytest.raises(NoisySimulationError, match=message):
        simulate_noisy_shots(compiled, bits, shots=1, seed=1)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PauliNoiseModel(one_qubit_error=-0.01),
        lambda: PauliNoiseModel(two_qubit_error=1.01),
        lambda: PauliNoiseModel(readout_error=math.nan),
        lambda: PauliNoiseModel(one_qubit_error=True),
        lambda: PauliNoiseModel(model="ambiguous-model"),
        lambda: PauliNoiseModel(synthetic=False),
    ],
)
def test_invalid_noise_models_are_rejected(factory) -> None:
    with pytest.raises(NoisySimulationError):
        factory()


def test_oversize_topology_wrong_types_and_malformed_native_gate_are_rejected() -> None:
    oversized = compile_superconducting(
        QuantumCircuit(MAX_TRAJECTORY_QUBITS + 1),
        linear_profile(MAX_TRAJECTORY_QUBITS + 1),
    )
    with pytest.raises(NoisySimulationError, match="capped"):
        simulate_noisy_shots(oversized, (0,) * (MAX_TRAJECTORY_QUBITS + 1), shots=1, seed=1)

    with pytest.raises(NoisySimulationError, match="SuperconductingCompilation"):
        simulate_noisy_shots(object(), (0,), shots=1, seed=1)  # type: ignore[arg-type]

    compiled = compile_superconducting(QuantumCircuit(1), linear_profile(1))
    malformed = replace(
        compiled,
        native_gates=(NativeGate("bad", (0,), None, 0, "test"),),
    )
    with pytest.raises(NoisySimulationError, match="unsupported"):
        simulate_noisy_shots(malformed, (0,), shots=1, seed=1)
