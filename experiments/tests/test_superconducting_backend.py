"""Contract tests for the synthetic superconducting reference backend."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.hardware.qasm import LogicalCircuitIR, LogicalGateIR
from src.hardware.superconducting import (
    CouplingProfile,
    NoiseParameters,
    SuperconductingCompileError,
    compile_superconducting,
    heavy_hex_like_profile,
    linear_profile,
    native_to_openqasm3,
    simulate_native_basis,
    verify_basis_equivalence,
)
from src.sshr_lib.bool_func import QuantumCircuit


def test_profiles_are_deterministic_synthetic_and_explicit() -> None:
    noise = NoiseParameters(
        model="independent-placeholder-v1",
        one_qubit_error=1e-4,
        two_qubit_error=8e-3,
        readout_error=2e-2,
    )
    linear = linear_profile(6, noise=noise)
    heavy = heavy_hex_like_profile(6, noise=noise)

    assert linear.coupling_edges == ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5))
    assert heavy.coupling_edges == (
        (0, 1),
        (0, 2),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
    )
    assert linear.synthetic is heavy.synthetic is True
    assert linear.calibration_source is None
    assert linear.noise == noise
    assert "not a physical device" in linear.claim_boundary


@pytest.mark.parametrize(
    "noise",
    [
        NoiseParameters(one_qubit_error=0.0),
        NoiseParameters(two_qubit_error=1.0),
    ],
)
def test_noise_boundary_values_are_valid(noise: NoiseParameters) -> None:
    assert linear_profile(2, noise=noise).noise == noise


def test_nonlocal_cnot_routes_and_preserves_mapping_trace() -> None:
    circuit = QuantumCircuit(4)
    circuit.add_cnot(0, 3)
    compiled = compile_superconducting(circuit, linear_profile(4))

    assert compiled.diagnostics.inserted_swap_count == 2
    assert compiled.diagnostics.inserted_routing_cx_count == 6
    assert compiled.diagnostics.final_logical_to_physical == (2, 0, 1, 3)
    assert compiled.traces[0].mapping_before == (0, 1, 2, 3)
    assert compiled.traces[0].mapping_after == (2, 0, 1, 3)
    assert compiled.traces[0].inserted_swaps == ((0, 1), (1, 2))
    assert all(
        tuple(sorted(gate.qubits)) in compiled.profile.coupling_edges
        for gate in compiled.native_gates
        if gate.name == "cx"
    )
    assert verify_basis_equivalence(compiled).equivalent


def test_x_cnot_toffoli_mct_decompose_to_native_and_verify() -> None:
    circuit = QuantumCircuit(4)
    circuit.add_x(0)
    circuit.add_cnot(0, 2)
    circuit.add_mct([0, 1], 3)
    circuit.add_mct([0, 1, 2], 3)
    compiled = compile_superconducting(circuit, heavy_hex_like_profile(4))

    assert {gate.name for gate in compiled.native_gates} <= {"rz", "sx", "x", "cx"}
    assert compiled.traces[2].decomposition == "ancilla-free-exact-parity-phase"
    assert compiled.traces[3].decomposition == "ancilla-free-exact-parity-phase"
    assert compiled.diagnostics.native_gate_count == len(compiled.native_gates)
    assert compiled.diagnostics.native_depth > 0
    assert compiled.diagnostics.noise_applied is False
    assert verify_basis_equivalence(compiled, tolerance=2e-9).equivalent


@pytest.mark.parametrize("control_count", [2, 3])
def test_mct_decomposition_is_unitary_equivalent_up_to_global_phase(
    control_count: int,
) -> None:
    """Protect the relative phases that basis-probability checks cannot see."""

    n_qubits = control_count + 1
    target = n_qubits - 1
    controls = list(range(control_count))
    circuit = QuantumCircuit(n_qubits)
    circuit.add_mct(controls, target)
    compiled = compile_superconducting(circuit, heavy_hex_like_profile(n_qubits))

    physical_unitary = np.column_stack(
        [
            simulate_native_basis(
                compiled,
                tuple((basis >> qubit) & 1 for qubit in range(n_qubits)),
            )
            for basis in range(1 << n_qubits)
        ]
    )
    logical_unitary = np.zeros_like(physical_unitary)
    expected = np.zeros_like(physical_unitary)
    for logical_output in range(1 << n_qubits):
        output_bits = tuple(
            (logical_output >> qubit) & 1 for qubit in range(n_qubits)
        )
        physical_output = sum(
            output_bits[logical] << physical
            for logical, physical in enumerate(
                compiled.diagnostics.final_logical_to_physical
            )
        )
        logical_unitary[logical_output, :] = physical_unitary[physical_output, :]
    for logical_input in range(1 << n_qubits):
        output_bits = [
            (logical_input >> qubit) & 1 for qubit in range(n_qubits)
        ]
        if all(output_bits[control] for control in controls):
            output_bits[target] ^= 1
        logical_output = sum(
            bit << qubit for qubit, bit in enumerate(output_bits)
        )
        expected[logical_output, logical_input] = 1.0

    reference_row, reference_col = np.argwhere(np.abs(expected) > 0)[0]
    global_phase = logical_unitary[reference_row, reference_col]
    assert abs(abs(global_phase) - 1.0) < 1e-12
    assert np.max(np.abs(logical_unitary - global_phase * expected)) < 1e-12


def test_native_qasm_records_profile_mapping_and_only_native_gates() -> None:
    logical_ir = LogicalCircuitIR(
        n_qubits=3,
        gates=(LogicalGateIR("MCT", (0, 1), 2),),
    )
    compiled = compile_superconducting(logical_ir, linear_profile(3))
    qasm = native_to_openqasm3(compiled)

    assert qasm.startswith("OPENQASM 3.0;")
    assert "synthetic_profile: synthetic-linear-3q-v1" in qasm
    assert "final_logical_to_physical:" in qasm
    assert "noise_applied: false" in qasm
    assert "ctrl(" not in qasm
    assert "rz(" in qasm and "sx q[" in qasm and "cx q[" in qasm


def test_compilation_is_deterministic_including_layers_and_routes() -> None:
    circuit = QuantumCircuit(5)
    circuit.add_mct([0, 2, 4], 1)
    first = compile_superconducting(circuit, linear_profile(5))
    second = compile_superconducting(circuit, linear_profile(5))

    assert first == second
    last_layer = [-1] * 5
    for gate in first.native_gates:
        assert all(gate.layer > last_layer[qubit] for qubit in gate.qubits)
        for qubit in gate.qubits:
            last_layer[qubit] = gate.layer
    assert first.diagnostics.native_depth == max(last_layer) + 1


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: linear_profile(0), "positive"),
        (
            lambda: CouplingProfile(
                name="bad",
                topology_family="bad",
                n_qubits=3,
                coupling_edges=((0, 1),),
            ),
            "connected",
        ),
        (lambda: NoiseParameters(two_qubit_error=math.nan), r"in \[0, 1\]"),
    ],
)
def test_invalid_profile_and_noise_are_rejected(factory, message: str) -> None:
    with pytest.raises(SuperconductingCompileError, match=message):
        factory()


def test_profile_size_mismatch_and_verification_cap_are_explicit() -> None:
    circuit = QuantumCircuit(3)
    with pytest.raises(SuperconductingCompileError, match="same number"):
        compile_superconducting(circuit, linear_profile(4))

    compiled = compile_superconducting(circuit, linear_profile(3))
    with pytest.raises(SuperconductingCompileError, match="capped"):
        verify_basis_equivalence(compiled, max_qubits=2)
