"""Golden and validation tests for the logical OpenQASM 3 adapter."""

from __future__ import annotations

import pytest

from src.hardware.qasm import (
    GATE_MODE,
    LogicalCircuitIR,
    LogicalGateIR,
    QASMExportError,
    circuit_to_logical_ir,
    export_openqasm3,
    logical_ir_to_openqasm3,
)
from src.sshr_lib.bool_func import Gate, QuantumCircuit


def test_x_cnot_toffoli_and_mct_openqasm3_golden() -> None:
    circuit = QuantumCircuit(6)
    circuit.add_x(0)
    circuit.add_cnot(0, 1)
    circuit.add_mct([0, 1], 2)
    circuit.add_mct([0, 1, 2, 3], 5)

    exported = export_openqasm3(circuit)

    assert exported.qasm == (
        "OPENQASM 3.0;\n"
        'include "stdgates.inc";\n'
        "\n"
        "// gate_mode: logical-x-cnot-mct\n"
        "// MCT is preserved as ctrl(k) @ x; downstream decomposition is required.\n"
        "qubit[6] q;\n"
        "\n"
        "x q[0];\n"
        "cx q[0], q[1];\n"
        "ctrl(2) @ x q[0], q[1], q[2];\n"
        "ctrl(4) @ x q[0], q[1], q[2], q[3], q[5];\n"
    )
    assert exported.logical_ir == LogicalCircuitIR(
        n_qubits=6,
        gates=(
            LogicalGateIR("X", (), 0),
            LogicalGateIR("CNOT", (0,), 1),
            LogicalGateIR("MCT", (0, 1), 2),
            LogicalGateIR("MCT", (0, 1, 2, 3), 5),
        ),
    )

    metadata = exported.metadata
    assert metadata.qasm_version == "3.0"
    assert metadata.n_qubits == 6
    assert metadata.logical_gate_count == 4
    assert (metadata.x_count, metadata.cnot_count, metadata.mct_count) == (1, 1, 2)
    assert metadata.max_controls == 4
    assert metadata.requires_mcx_decomposition is True
    assert metadata.gate_mode == GATE_MODE
    assert "no native-gate decomposition" in metadata.claim_boundary
    assert "routing" in metadata.claim_boundary


def test_empty_and_x_cnot_only_circuits_do_not_require_mcx_decomposition() -> None:
    empty = export_openqasm3(QuantumCircuit(2))
    assert empty.metadata.logical_gate_count == 0
    assert empty.metadata.max_controls == 0
    assert empty.metadata.requires_mcx_decomposition is False

    circuit = QuantumCircuit(2)
    circuit.add_x(0)
    circuit.add_cnot(0, 1)
    exported = export_openqasm3(circuit)
    assert exported.metadata.max_controls == 1
    assert exported.metadata.requires_mcx_decomposition is False


def test_ir_is_a_copy_and_keeps_mct_undecomposed() -> None:
    circuit = QuantumCircuit(4)
    circuit.add_mct([0, 1, 2], 3)
    logical_ir = circuit_to_logical_ir(circuit)
    circuit.gates[0].controls.append(3)

    assert logical_ir.gates == (LogicalGateIR("MCT", (0, 1, 2), 3),)
    assert "ctrl(3) @ x" in logical_ir_to_openqasm3(logical_ir).qasm


@pytest.mark.parametrize(
    ("n_qubits", "gate", "message"),
    [
        (0, None, "positive integer"),
        (3, Gate("Y", [], 0), "unsupported type"),
        (3, Gate("X", [1], 0), "zero controls"),
        (3, Gate("CNOT", [], 0), "exactly one control"),
        (3, Gate("CNOT", [0, 1], 2), "exactly one control"),
        (3, Gate("MCT", [0], 2), "at least two controls"),
        (3, Gate("MCT", [0, 0], 2), "duplicate controls"),
        (3, Gate("MCT", [0, 1], 1), "also a control"),
        (3, Gate("X", [], 3), "outside the circuit range"),
        (3, Gate("CNOT", [True], 2), "integer qubit index"),
    ],
)
def test_invalid_circuits_are_rejected(
    n_qubits: int,
    gate: Gate | None,
    message: str,
) -> None:
    circuit = QuantumCircuit(n_qubits)
    if gate is not None:
        circuit.gates.append(gate)

    with pytest.raises(QASMExportError, match=message):
        export_openqasm3(circuit)


def test_noncanonical_gate_object_and_gate_mode_are_rejected() -> None:
    circuit = QuantumCircuit(2)
    circuit.gates.append(object())  # type: ignore[arg-type]
    with pytest.raises(QASMExportError, match="must be src.sshr_lib.bool_func.Gate"):
        export_openqasm3(circuit)

    logical_ir = LogicalCircuitIR(
        n_qubits=2,
        gates=(LogicalGateIR("X", (), 0),),
        gate_mode="native",
    )
    with pytest.raises(QASMExportError, match="unsupported gate_mode"):
        logical_ir_to_openqasm3(logical_ir)
