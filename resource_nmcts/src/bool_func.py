"""Boolean-function and simple reversible-circuit primitives.

This local copy keeps the submission payload self-contained.  The active
resource-NMCTS scripts historically imported the same interface from the
neighboring ``sshr`` package; payload extraction runs do not include that parent
directory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List


def mct_cost_rp(k: int) -> dict[str, int]:
    """MCT cost using relative-phase Toffoli for the two-control case."""
    if k == 2:
        return {"T": 4, "H": 0, "CNOT": 6, "ancilla": 0}
    return mct_cost(k)


def mct_cost(k: int) -> dict[str, int]:
    """Return the logical cost of a k-control MCT gate."""
    if k == 1:
        return {"T": 0, "H": 0, "CNOT": 1, "ancilla": 0}
    if k == 2:
        return {"T": 7, "H": 2, "CNOT": 6, "ancilla": 0}
    if k == 3:
        return {"T": 16, "H": 6, "CNOT": 14, "ancilla": 1}
    return {
        "T": 8 * k - 8,
        "H": 8 * k - 12,
        "CNOT": 4 * k - 6,
        "ancilla": math.ceil((k - 2) / 2),
    }


@dataclass
class Gate:
    type: str
    controls: List[int] = field(default_factory=list)
    target: int = -1


class QuantumCircuit:
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
        self.gates: List[Gate] = []

    def add_cnot(self, control: int, target: int) -> None:
        self.gates.append(Gate("CNOT", [control], target))

    def add_x(self, qubit: int) -> None:
        self.gates.append(Gate("X", [], qubit))

    def add_mct(self, controls: List[int], target: int) -> None:
        k = len(controls)
        if k == 0:
            self.gates.append(Gate("X", [], target))
        elif k == 1:
            self.gates.append(Gate("CNOT", list(controls), target))
        else:
            self.gates.append(Gate("MCT", list(controls), target))

    def add_block(self, other: "QuantumCircuit") -> None:
        self.gates.extend(other.gates)

    def cost(self) -> dict[str, int]:
        t_count = 0
        cnot_count = 0
        ancilla = 0
        for gate in self.gates:
            if gate.type == "CNOT":
                cnot_count += 1
            elif gate.type == "MCT":
                cost = mct_cost(len(gate.controls))
                t_count += cost["T"]
                cnot_count += cost["CNOT"]
                ancilla += cost["ancilla"]
        return {"T": t_count, "CNOT": cnot_count, "ancilla": ancilla}

    def simulate(self, input_bits: List[int]) -> List[int]:
        bits = list(input_bits)
        for gate in self.gates:
            if gate.type == "X":
                bits[gate.target] ^= 1
            elif gate.type == "CNOT":
                if bits[gate.controls[0]]:
                    bits[gate.target] ^= 1
            elif gate.type == "MCT":
                if all(bits[control] for control in gate.controls):
                    bits[gate.target] ^= 1
        return bits


class BooleanFunction:
    """n-variable Boolean function stored as an integer truth table."""

    def __init__(self, n: int, truth_table: int):
        self.n = n
        self.N = 1 << n
        self.truth_table = truth_table & ((1 << self.N) - 1)

    @classmethod
    def from_hex(cls, n: int, hex_str: str) -> "BooleanFunction":
        return cls(n, int(hex_str, 16))

    @classmethod
    def from_list(cls, n: int, values: List[int]) -> "BooleanFunction":
        truth_table = 0
        for index, value in enumerate(values):
            if value:
                truth_table |= 1 << index
        return cls(n, truth_table)

    def evaluate(self, x: int) -> int:
        return (self.truth_table >> x) & 1

    @property
    def onset(self) -> List[int]:
        return [x for x in range(self.N) if self.evaluate(x)]

    @property
    def offset(self) -> List[int]:
        return [x for x in range(self.N) if not self.evaluate(x)]

    def __repr__(self) -> str:
        return f"BooleanFunction(n={self.n}, tt=0x{self.truth_table:0{self.N // 4}X})"
