"""
Boolean function representation and quantum circuit primitives.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Tuple


# ---------------------------------------------------------------------------
# MCT gate decomposition cost (Table II in the paper)
# ---------------------------------------------------------------------------

def mct_cost_rp(k: int) -> dict:
    """MCT cost using relative-phase Toffoli (T=4 for k=2, standard otherwise)."""
    if k == 2:
        return {"T": 4, "H": 0, "CNOT": 6, "ancilla": 0}
    return mct_cost(k)


def mct_cost(k: int) -> dict:
    """
    Return the T/H/CNOT/ancilla cost of a k-control MCT gate.
    k is the number of control qubits (Toffoli = k=2).
    For k=1 (CNOT), cost is just 1 CNOT, 0 T, 0 ancilla.
    """
    if k == 1:
        return {"T": 0, "H": 0, "CNOT": 1, "ancilla": 0}
    elif k == 2:
        return {"T": 7, "H": 2, "CNOT": 6, "ancilla": 0}
    elif k == 3:
        return {"T": 16, "H": 6, "CNOT": 14, "ancilla": 1}
    else:  # k >= 4
        return {
            "T": 8 * k - 8,
            "H": 8 * k - 12,
            "CNOT": 4 * k - 6,
            "ancilla": math.ceil((k - 2) / 2),
        }


# ---------------------------------------------------------------------------
# Gate dataclass
# ---------------------------------------------------------------------------

@dataclass
class Gate:
    type: str          # 'CNOT', 'X', 'MCT'
    controls: List[int] = field(default_factory=list)
    target: int = -1


# ---------------------------------------------------------------------------
# Quantum circuit
# ---------------------------------------------------------------------------

class QuantumCircuit:
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
        self.gates: List[Gate] = []

    def add_cnot(self, control: int, target: int):
        self.gates.append(Gate("CNOT", [control], target))

    def add_x(self, qubit: int):
        self.gates.append(Gate("X", [], qubit))

    def add_mct(self, controls: List[int], target: int):
        k = len(controls)
        if k == 0:
            # No controls: just an X gate on target
            self.gates.append(Gate("X", [], target))
        elif k == 1:
            self.gates.append(Gate("CNOT", list(controls), target))
        else:
            self.gates.append(Gate("MCT", list(controls), target))

    def add_block(self, other: "QuantumCircuit"):
        self.gates.extend(other.gates)

    def cost(self) -> dict:
        """Aggregate T-count, CNOT count, max ancilla across all gates."""
        t_count = 0
        cnot_count = 0
        ancilla = 0
        for g in self.gates:
            if g.type == "CNOT":
                cnot_count += 1
            elif g.type == "X":
                pass
            elif g.type == "MCT":
                k = len(g.controls)
                c = mct_cost(k)
                t_count += c["T"]
                cnot_count += c["CNOT"]
                ancilla += c["ancilla"]
        return {"T": t_count, "CNOT": cnot_count, "ancilla": ancilla}

    def simulate(self, input_bits: List[int]) -> List[int]:
        """
        Simulate the circuit on classical bits.
        input_bits: list of n_qubits bits (0 or 1), last bit is output qubit.
        Returns updated bit string.
        """
        bits = list(input_bits)
        for g in self.gates:
            if g.type == "X":
                bits[g.target] ^= 1
            elif g.type == "CNOT":
                if bits[g.controls[0]] == 1:
                    bits[g.target] ^= 1
            elif g.type == "MCT":
                if all(bits[c] == 1 for c in g.controls):
                    bits[g.target] ^= 1
        return bits


# ---------------------------------------------------------------------------
# Boolean function
# ---------------------------------------------------------------------------

class BooleanFunction:
    """
    n-variable Boolean function f: {0,1}^n -> {0,1}.
    truth_table is an integer (bit-string f_{2^n-1} ... f_1 f_0).
    Bit x of truth_table gives f(x).
    """

    def __init__(self, n: int, truth_table: int):
        self.n = n
        self.N = 1 << n
        self.truth_table = truth_table & ((1 << self.N) - 1)

    @classmethod
    def from_hex(cls, n: int, hex_str: str) -> "BooleanFunction":
        return cls(n, int(hex_str, 16))

    @classmethod
    def from_list(cls, n: int, values: List[int]) -> "BooleanFunction":
        tt = 0
        for i, v in enumerate(values):
            if v:
                tt |= 1 << i
        return cls(n, tt)

    def evaluate(self, x: int) -> int:
        return (self.truth_table >> x) & 1

    @property
    def onset(self) -> List[int]:
        return [x for x in range(self.N) if self.evaluate(x)]

    @property
    def offset(self) -> List[int]:
        return [x for x in range(self.N) if not self.evaluate(x)]

    def __repr__(self):
        return f"BooleanFunction(n={self.n}, tt=0x{self.truth_table:0{self.N//4}X})"
