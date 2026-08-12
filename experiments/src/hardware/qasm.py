"""OpenQASM 3 export for the project's logical X/CNOT/MCT circuits.

This module is deliberately an interchange boundary, not a hardware compiler.
An ``MCT`` gate is preserved in :class:`LogicalGateIR` and serialized with the
standard OpenQASM 3 ``ctrl(k) @ x`` modifier.  It is *not* replaced by a
fictional native instruction or silently assigned a physical cost.

Downstream tools must explicitly decompose multi-controlled X gates before
native-gate execution and are responsible for placement, routing, scheduling,
calibration, and noise modelling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.sshr_lib.bool_func import Gate, QuantumCircuit


GATE_MODE = "logical-x-cnot-mct"
"""The only gate semantics accepted by this adapter."""

CLAIM_BOUNDARY = (
    "Logical OpenQASM 3 interchange only: MCT gates remain explicit "
    "multi-controlled X operations; no native-gate decomposition, placement, "
    "routing, scheduling, calibration, or noise modelling is performed."
)


class QASMExportError(ValueError):
    """Raised when a circuit or logical IR cannot be exported faithfully."""


@dataclass(frozen=True)
class LogicalGateIR:
    """Lossless logical representation of one X, CNOT, or MCT gate."""

    gate_type: str
    controls: tuple[int, ...]
    target: int


@dataclass(frozen=True)
class LogicalCircuitIR:
    """Backend-independent circuit IR that keeps MCT gates undecomposed."""

    n_qubits: int
    gates: tuple[LogicalGateIR, ...]
    gate_mode: str = GATE_MODE


@dataclass(frozen=True)
class QASMExportMetadata:
    """Machine-readable scope and gate statistics for an OpenQASM export."""

    qasm_version: str
    n_qubits: int
    logical_gate_count: int
    x_count: int
    cnot_count: int
    mct_count: int
    max_controls: int
    requires_mcx_decomposition: bool
    gate_mode: str
    claim_boundary: str


@dataclass(frozen=True)
class OpenQASM3Export:
    """OpenQASM text together with its lossless logical IR and metadata."""

    qasm: str
    logical_ir: LogicalCircuitIR
    metadata: QASMExportMetadata


def _is_qubit_index(value: object) -> bool:
    # ``bool`` is an ``int`` subclass, but accepting True as qubit 1 hides
    # malformed circuit construction.
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_qubit(index: object, n_qubits: int, label: str) -> int:
    if not _is_qubit_index(index):
        raise QASMExportError(f"{label} must be an integer qubit index, got {index!r}")
    if not 0 <= index < n_qubits:
        raise QASMExportError(
            f"{label} index {index} is outside the circuit range [0, {n_qubits})"
        )
    return index


def _validated_gate(
    gate_type: object,
    controls: Iterable[object],
    target: object,
    n_qubits: int,
    gate_index: int,
) -> LogicalGateIR:
    if not isinstance(gate_type, str):
        raise QASMExportError(
            f"gate {gate_index} type must be a string, got {gate_type!r}"
        )

    normalized_type = gate_type.upper()
    if normalized_type not in {"X", "CNOT", "MCT"}:
        raise QASMExportError(
            f"gate {gate_index} has unsupported type {gate_type!r}; "
            "only X, CNOT, and MCT are valid"
        )

    try:
        raw_controls = tuple(controls)
    except TypeError as exc:
        raise QASMExportError(f"gate {gate_index} controls must be iterable") from exc

    checked_controls = tuple(
        _validate_qubit(control, n_qubits, f"gate {gate_index} control {position}")
        for position, control in enumerate(raw_controls)
    )
    checked_target = _validate_qubit(target, n_qubits, f"gate {gate_index} target")

    expected_description: str | None = None
    if normalized_type == "X" and checked_controls:
        expected_description = "X must have zero controls"
    elif normalized_type == "CNOT" and len(checked_controls) != 1:
        expected_description = "CNOT must have exactly one control"
    elif normalized_type == "MCT" and len(checked_controls) < 2:
        expected_description = "MCT must have at least two controls"
    if expected_description is not None:
        raise QASMExportError(f"gate {gate_index}: {expected_description}")

    if len(set(checked_controls)) != len(checked_controls):
        raise QASMExportError(f"gate {gate_index} contains duplicate controls")
    if checked_target in checked_controls:
        raise QASMExportError(
            f"gate {gate_index} target q[{checked_target}] is also a control"
        )

    return LogicalGateIR(
        gate_type=normalized_type,
        controls=checked_controls,
        target=checked_target,
    )


def circuit_to_logical_ir(circuit: QuantumCircuit) -> LogicalCircuitIR:
    """Validate and copy the canonical circuit into immutable logical IR.

    The canonical source is ``src.sshr_lib.bool_func.QuantumCircuit``.  A
    structural copy is returned so later mutation of ``circuit.gates`` cannot
    change an already-created export.
    """

    if not isinstance(circuit, QuantumCircuit):
        raise QASMExportError(
            "circuit must be src.sshr_lib.bool_func.QuantumCircuit"
        )
    if not _is_qubit_index(circuit.n_qubits) or circuit.n_qubits <= 0:
        raise QASMExportError(
            f"circuit n_qubits must be a positive integer, got {circuit.n_qubits!r}"
        )
    if not isinstance(circuit.gates, list):
        raise QASMExportError("circuit gates must be a list")

    gates: list[LogicalGateIR] = []
    for index, gate in enumerate(circuit.gates):
        if not isinstance(gate, Gate):
            raise QASMExportError(
                f"gate {index} must be src.sshr_lib.bool_func.Gate, "
                f"got {type(gate).__name__}"
            )
        gates.append(
            _validated_gate(
                gate.type,
                gate.controls,
                gate.target,
                circuit.n_qubits,
                index,
            )
        )

    return LogicalCircuitIR(n_qubits=circuit.n_qubits, gates=tuple(gates))


def validate_logical_ir(logical_ir: LogicalCircuitIR) -> QASMExportMetadata:
    """Validate immutable IR and return gate statistics plus scope metadata."""

    if not isinstance(logical_ir, LogicalCircuitIR):
        raise QASMExportError("logical_ir must be a LogicalCircuitIR")
    if (
        not _is_qubit_index(logical_ir.n_qubits)
        or logical_ir.n_qubits <= 0
    ):
        raise QASMExportError(
            "logical_ir n_qubits must be a positive integer, "
            f"got {logical_ir.n_qubits!r}"
        )
    if logical_ir.gate_mode != GATE_MODE:
        raise QASMExportError(
            f"unsupported gate_mode {logical_ir.gate_mode!r}; expected {GATE_MODE!r}"
        )

    validated = tuple(
        _validated_gate(
            gate.gate_type,
            gate.controls,
            gate.target,
            logical_ir.n_qubits,
            index,
        )
        for index, gate in enumerate(logical_ir.gates)
    )
    if validated != logical_ir.gates:
        # At present this can only happen if a caller manually constructed IR
        # with non-canonical gate-name casing.
        raise QASMExportError("logical_ir gates must use canonical X/CNOT/MCT names")

    x_count = sum(gate.gate_type == "X" for gate in logical_ir.gates)
    cnot_count = sum(gate.gate_type == "CNOT" for gate in logical_ir.gates)
    mct_count = sum(gate.gate_type == "MCT" for gate in logical_ir.gates)
    max_controls = max(
        (len(gate.controls) for gate in logical_ir.gates),
        default=0,
    )
    return QASMExportMetadata(
        qasm_version="3.0",
        n_qubits=logical_ir.n_qubits,
        logical_gate_count=len(logical_ir.gates),
        x_count=x_count,
        cnot_count=cnot_count,
        mct_count=mct_count,
        max_controls=max_controls,
        requires_mcx_decomposition=mct_count > 0,
        gate_mode=GATE_MODE,
        claim_boundary=CLAIM_BOUNDARY,
    )


def _gate_to_openqasm3(gate: LogicalGateIR) -> str:
    if gate.gate_type == "X":
        return f"x q[{gate.target}];"
    if gate.gate_type == "CNOT":
        return f"cx q[{gate.controls[0]}], q[{gate.target}];"

    operands = ", ".join(
        f"q[{qubit}]" for qubit in (*gate.controls, gate.target)
    )
    return f"ctrl({len(gate.controls)}) @ x {operands};"


def logical_ir_to_openqasm3(logical_ir: LogicalCircuitIR) -> OpenQASM3Export:
    """Serialize validated logical IR using standard OpenQASM 3 syntax.

    ``ctrl(k) @ x`` exactly denotes a k-control X operation in OpenQASM 3.
    Keeping that modifier in the output avoids pretending that an MCT has
    already been decomposed into a target backend's native gate set.
    """

    metadata = validate_logical_ir(logical_ir)
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "",
        f"// gate_mode: {metadata.gate_mode}",
        "// MCT is preserved as ctrl(k) @ x; downstream decomposition is required.",
        f"qubit[{logical_ir.n_qubits}] q;",
    ]
    if logical_ir.gates:
        lines.append("")
        lines.extend(_gate_to_openqasm3(gate) for gate in logical_ir.gates)
    return OpenQASM3Export(
        qasm="\n".join(lines) + "\n",
        logical_ir=logical_ir,
        metadata=metadata,
    )


def export_openqasm3(circuit: QuantumCircuit) -> OpenQASM3Export:
    """Validate a canonical logical circuit and export OpenQASM 3."""

    return logical_ir_to_openqasm3(circuit_to_logical_ir(circuit))
