"""JSON adapters for the immutable logical circuit/QASM boundary."""

from __future__ import annotations

from dataclasses import asdict

from src.hardware.qasm import LogicalCircuitIR, QASMExportMetadata, validate_logical_ir


LOGICAL_IR_SCHEMA = "xa.logical-circuit-ir.v1"


def logical_ir_record(logical_ir: LogicalCircuitIR) -> dict:
    metadata = validate_logical_ir(logical_ir)
    return {
        "schema_version": LOGICAL_IR_SCHEMA,
        "n_qubits": int(logical_ir.n_qubits),
        "gate_mode": logical_ir.gate_mode,
        "gates": [
            {
                "gate_type": gate.gate_type,
                "controls": [int(control) for control in gate.controls],
                "target": int(gate.target),
            }
            for gate in logical_ir.gates
        ],
        "gate_statistics": {
            "logical_gate_count": metadata.logical_gate_count,
            "x_count": metadata.x_count,
            "cnot_count": metadata.cnot_count,
            "mct_count": metadata.mct_count,
            "max_controls": metadata.max_controls,
        },
    }


def qasm_metadata_record(metadata: QASMExportMetadata) -> dict:
    if not isinstance(metadata, QASMExportMetadata):
        raise TypeError("metadata must be QASMExportMetadata")
    return asdict(metadata)
