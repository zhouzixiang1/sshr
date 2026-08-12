"""Independent unitary contracts for the ideal ion-trap adapter."""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from src.hardware.ion_trap import (
    ION_NATIVE_GATE_SET,
    RXX_CONVENTION,
    compile_ion_trap,
    ion_native_to_openqasm3,
    verify_ion_trap_equivalence,
)
from src.hardware.qasm import LogicalCircuitIR, LogicalGateIR


def _apply_one(state: np.ndarray, qubit: int, matrix: np.ndarray) -> None:
    for index in range(state.size):
        if (index >> qubit) & 1:
            continue
        partner = index | (1 << qubit)
        a0, a1 = state[index], state[partner]
        state[index] = matrix[0, 0] * a0 + matrix[0, 1] * a1
        state[partner] = matrix[1, 0] * a0 + matrix[1, 1] * a1


def _independent_native_unitary(compilation) -> np.ndarray:
    """Test-only simulator; it does not call the adapter simulator."""

    n_qubits = compilation.logical_ir.n_qubits
    columns = []
    for basis in range(1 << n_qubits):
        state = np.zeros(1 << n_qubits, dtype=np.complex128)
        state[basis] = 1.0
        for gate in compilation.native_gates:
            angle = gate.angle
            if gate.name == "rz":
                matrix = np.diag(
                    [cmath.exp(-0.5j * angle), cmath.exp(0.5j * angle)]
                )
                _apply_one(state, gate.qubits[0], matrix)
            elif gate.name == "rx":
                cosine = math.cos(angle / 2)
                sine = -1j * math.sin(angle / 2)
                _apply_one(
                    state,
                    gate.qubits[0],
                    np.array([[cosine, sine], [sine, cosine]], dtype=np.complex128),
                )
            elif gate.name == "rxx":
                old = state.copy()
                mask = (1 << gate.qubits[0]) | (1 << gate.qubits[1])
                for index in range(state.size):
                    state[index] = (
                        math.cos(angle / 2) * old[index]
                        - 1j * math.sin(angle / 2) * old[index ^ mask]
                    )
            else:  # pragma: no cover - the assertion below diagnoses this.
                raise AssertionError(gate.name)
        columns.append(state)
    return np.column_stack(columns)


def _expected_logical_unitary(logical_ir: LogicalCircuitIR) -> np.ndarray:
    dimension = 1 << logical_ir.n_qubits
    expected = np.zeros((dimension, dimension), dtype=np.complex128)
    for basis in range(dimension):
        bits = [(basis >> qubit) & 1 for qubit in range(logical_ir.n_qubits)]
        for gate in logical_ir.gates:
            if gate.gate_type == "X":
                bits[gate.target] ^= 1
            elif gate.gate_type == "CNOT":
                if bits[gate.controls[0]]:
                    bits[gate.target] ^= 1
            elif all(bits[control] for control in gate.controls):
                bits[gate.target] ^= 1
        output = sum(bit << qubit for qubit, bit in enumerate(bits))
        expected[output, basis] = 1.0
    return expected


def _assert_global_phase_equivalent(actual: np.ndarray, expected: np.ndarray) -> None:
    row, column = np.argwhere(np.abs(expected) > 0)[0]
    phase = actual[row, column]
    assert abs(abs(phase) - 1.0) < 1e-12
    assert np.max(np.abs(actual - phase * expected)) < 2e-12


def test_cnot_to_rxx_unitary_is_locked_independently() -> None:
    logical = LogicalCircuitIR(2, (LogicalGateIR("CNOT", (0,), 1),))
    compiled = compile_ion_trap(logical)

    assert RXX_CONVENTION == "RXX(theta)=exp(-i theta X⊗X/2)"
    assert [gate.angle for gate in compiled.native_gates if gate.name == "rxx"] == [
        math.pi / 2
    ]
    _assert_global_phase_equivalent(
        _independent_native_unitary(compiled),
        _expected_logical_unitary(logical),
    )


@pytest.mark.parametrize(
    "logical",
    [
        LogicalCircuitIR(1, (LogicalGateIR("X", (), 0),)),
        LogicalCircuitIR(2, (LogicalGateIR("CNOT", (0,), 1),)),
        LogicalCircuitIR(3, (LogicalGateIR("MCT", (0, 1), 2),)),
        LogicalCircuitIR(4, (LogicalGateIR("MCT", (0, 1, 2), 3),)),
    ],
    ids=("x", "cnot", "toffoli", "three-control-mct"),
)
def test_small_logical_gates_are_full_basis_and_unitary_equivalent(logical) -> None:
    compiled = compile_ion_trap(logical)
    check = verify_ion_trap_equivalence(compiled, tolerance=2e-12)

    assert {gate.name for gate in compiled.native_gates} <= set(ION_NATIVE_GATE_SET)
    assert all(not gate.inserted_for_routing for gate in compiled.native_gates)
    assert compiled.diagnostics.inserted_swap_count == 0
    assert compiled.diagnostics.fully_connected is True
    assert check.tested_basis_states == 1 << logical.n_qubits
    assert check.basis_equivalent
    assert check.unitary_equivalent_up_to_global_phase
    _assert_global_phase_equivalent(
        _independent_native_unitary(compiled),
        _expected_logical_unitary(logical),
    )


def test_ion_native_qasm_has_no_cx_or_swap_and_is_deterministic() -> None:
    logical = LogicalCircuitIR(4, (LogicalGateIR("MCT", (0, 1, 2), 3),))
    first = compile_ion_trap(logical)
    second = compile_ion_trap(logical)
    qasm = ion_native_to_openqasm3(first)

    assert first == second
    assert "rxx(" in qasm and "rx(" in qasm and "rz(" in qasm
    assert "cx " not in qasm.lower()
    assert "swap " not in qasm.lower()
    assert "hardware_execution: false" in qasm
    assert RXX_CONVENTION in qasm
