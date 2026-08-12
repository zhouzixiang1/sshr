"""Exact ideal ion-trap adapter for the logical X/CNOT/MCT circuit IR.

The adapter targets a fully connected reference alphabet ``{rz, rx, rxx}``.
Its two-qubit convention is

``RXX(theta) = exp(-i * theta * X tensor X / 2)``.

The existing ancilla-free parity-phase MCT decomposition is reused through a
fully connected internal reference compilation.  Every remaining ``x``/``sx``
and ``cx`` is then lowered to rotations and ``rxx``.  No routing operation or
SWAP is inserted.  This is an ideal resource adapter, not a pulse compiler,
device calibration, noise model, or hardware execution claim.
"""

from __future__ import annotations

import cmath
from dataclasses import dataclass
from itertools import combinations
import math
from typing import Iterable

import numpy as np

from src.hardware.qasm import (
    LogicalCircuitIR,
    circuit_to_logical_ir,
    validate_logical_ir,
)
from src.hardware.superconducting import (
    CouplingProfile,
    NoiseParameters,
    compile_superconducting,
)
from src.sshr_lib.bool_func import QuantumCircuit


ION_NATIVE_GATE_SET = ("rz", "rx", "rxx")
RXX_CONVENTION = "RXX(theta)=exp(-i theta X⊗X/2)"
EVIDENCE_STRENGTH = "ideal-full-basis-and-unitary-reference"
CLAIM_BOUNDARY = (
    "Deterministic ideal resource adaptation to a fully connected ion-trap "
    "reference alphabet; no device calibration, pulse schedule, crosstalk or "
    "heating model, noisy execution, real hardware execution, speedup, or "
    "quantum-advantage claim."
)


class IonTrapCompileError(ValueError):
    """Raised when the logical input or ideal native record is invalid."""


@dataclass(frozen=True)
class IonNativeGate:
    """One ideal native instruction with logical-source provenance."""

    name: str
    qubits: tuple[int, ...]
    angle: float
    logical_gate_index: int
    origin: str
    inserted_for_routing: bool = False
    layer: int = 0


@dataclass(frozen=True)
class IonTrapDiagnostics:
    logical_gate_count: int
    native_gate_count: int
    one_qubit_gate_count: int
    two_qubit_gate_count: int
    rxx_count: int
    native_depth: int
    inserted_swap_count: int
    fully_connected: bool
    source_mct_decomposition: str
    rxx_convention: str
    hardware_execution: bool
    noise_applied: bool
    evidence_strength: str
    claim_boundary: str


@dataclass(frozen=True)
class IonTrapCompilation:
    logical_ir: LogicalCircuitIR
    native_gates: tuple[IonNativeGate, ...]
    diagnostics: IonTrapDiagnostics


@dataclass(frozen=True)
class IonTrapEquivalenceCheck:
    basis_equivalent: bool
    unitary_equivalent_up_to_global_phase: bool
    tested_basis_states: int
    max_basis_failure_probability: float
    max_unitary_error: float
    global_phase_real: float
    global_phase_imag: float
    tolerance: float


def _h_sequence(qubit: int, origin: str) -> tuple[tuple[str, tuple[int, ...], float, str], ...]:
    # Rz(pi/2) Rx(pi/2) Rz(pi/2) = -i H.
    return (
        ("rz", (qubit,), math.pi / 2, origin),
        ("rx", (qubit,), math.pi / 2, origin),
        ("rz", (qubit,), math.pi / 2, origin),
    )


def _cx_to_rxx(
    control: int,
    target: int,
) -> tuple[tuple[str, tuple[int, ...], float, str], ...]:
    """Return a CNOT decomposition for the declared RXX convention.

    It follows ``CNOT = (I⊗H) CZ (I⊗H)`` and
    ``CZ ~ [Rz(-pi/2)⊗Rz(-pi/2)] (H⊗H) RXX(pi/2) (H⊗H)``.
    Adjacent target Hadamards cancel.  Equality is up to a single global phase.
    """

    emitted: list[tuple[str, tuple[int, ...], float, str]] = []
    emitted.extend(_h_sequence(control, "cx-rxx-basis-pre"))
    emitted.append(("rxx", (control, target), math.pi / 2, "cx-entangler"))
    emitted.extend(_h_sequence(control, "cx-rxx-basis-post"))
    emitted.extend(_h_sequence(target, "cx-target-basis"))
    emitted.append(("rz", (control,), -math.pi / 2, "cx-local-phase"))
    emitted.append(("rz", (target,), -math.pi / 2, "cx-local-phase"))
    emitted.extend(_h_sequence(target, "cx-target-output"))
    return tuple(emitted)


def compile_ion_trap(
    circuit: QuantumCircuit | LogicalCircuitIR,
) -> IonTrapCompilation:
    """Lower logical X/CNOT/MCT to fully connected ``rz/rx/rxx`` gates."""

    logical_ir = circuit if isinstance(circuit, LogicalCircuitIR) else circuit_to_logical_ir(circuit)
    validate_logical_ir(logical_ir)
    edges = tuple(combinations(range(logical_ir.n_qubits), 2))
    reference_profile = CouplingProfile(
        name=f"internal-fully-connected-decomposition-reference-{logical_ir.n_qubits}q-v1",
        topology_family="fully-connected-reference",
        n_qubits=logical_ir.n_qubits,
        coupling_edges=edges,
        noise=NoiseParameters(),
    )
    reference = compile_superconducting(logical_ir, reference_profile)
    if reference.diagnostics.inserted_swap_count != 0:
        raise AssertionError("fully connected reference unexpectedly inserted a SWAP")

    raw: list[tuple[str, tuple[int, ...], float, int, str]] = []
    for gate in reference.native_gates:
        if gate.inserted_for_routing:
            raise AssertionError("ion-trap adapter must not inherit routing gates")
        if gate.name == "rz":
            raw.append(("rz", gate.qubits, float(gate.angle), gate.logical_gate_index, gate.origin))
        elif gate.name == "sx":
            raw.append(("rx", gate.qubits, math.pi / 2, gate.logical_gate_index, "sx-to-rx"))
        elif gate.name == "x":
            raw.append(("rx", gate.qubits, math.pi, gate.logical_gate_index, "x-to-rx"))
        elif gate.name == "cx":
            control, target = gate.qubits
            for name, qubits, angle, origin in _cx_to_rxx(control, target):
                raw.append((name, qubits, angle, gate.logical_gate_index, origin))
        else:  # pragma: no cover - the reference compiler has a closed alphabet.
            raise IonTrapCompileError(f"unsupported reference gate {gate.name!r}")

    last_layer = [-1] * logical_ir.n_qubits
    native: list[IonNativeGate] = []
    for name, qubits, angle, logical_gate_index, origin in raw:
        if name not in ION_NATIVE_GATE_SET:
            raise AssertionError(f"non-ion native gate survived lowering: {name}")
        layer = 1 + max((last_layer[qubit] for qubit in qubits), default=-1)
        for qubit in qubits:
            last_layer[qubit] = layer
        native.append(
            IonNativeGate(
                name=name,
                qubits=qubits,
                angle=float(angle),
                logical_gate_index=logical_gate_index,
                origin=origin,
                inserted_for_routing=False,
                layer=layer,
            )
        )
    diagnostics = IonTrapDiagnostics(
        logical_gate_count=len(logical_ir.gates),
        native_gate_count=len(native),
        one_qubit_gate_count=sum(len(gate.qubits) == 1 for gate in native),
        two_qubit_gate_count=sum(len(gate.qubits) == 2 for gate in native),
        rxx_count=sum(gate.name == "rxx" for gate in native),
        native_depth=max((gate.layer for gate in native), default=-1) + 1,
        inserted_swap_count=0,
        fully_connected=True,
        source_mct_decomposition="ancilla-free-exact-parity-phase",
        rxx_convention=RXX_CONVENTION,
        hardware_execution=False,
        noise_applied=False,
        evidence_strength=EVIDENCE_STRENGTH,
        claim_boundary=CLAIM_BOUNDARY,
    )
    return IonTrapCompilation(logical_ir, tuple(native), diagnostics)


def _apply_one_qubit(state: np.ndarray, qubit: int, matrix: np.ndarray) -> None:
    stride = 1 << qubit
    period = stride << 1
    for start in range(0, state.size, period):
        for offset in range(stride):
            i0 = start + offset
            i1 = i0 + stride
            a0, a1 = state[i0], state[i1]
            state[i0] = matrix[0, 0] * a0 + matrix[0, 1] * a1
            state[i1] = matrix[1, 0] * a0 + matrix[1, 1] * a1


def _validate_native(compilation: IonTrapCompilation) -> None:
    if not isinstance(compilation, IonTrapCompilation):
        raise IonTrapCompileError("compilation must be IonTrapCompilation")
    n_qubits = compilation.logical_ir.n_qubits
    validate_logical_ir(compilation.logical_ir)
    for index, gate in enumerate(compilation.native_gates):
        if gate.name not in ION_NATIVE_GATE_SET:
            raise IonTrapCompileError(f"gate {index} is not ion-native")
        expected_arity = 2 if gate.name == "rxx" else 1
        if len(gate.qubits) != expected_arity or len(set(gate.qubits)) != expected_arity:
            raise IonTrapCompileError(f"gate {index} has invalid arity/qubits")
        if any(not isinstance(q, int) or isinstance(q, bool) or not 0 <= q < n_qubits for q in gate.qubits):
            raise IonTrapCompileError(f"gate {index} has an invalid qubit")
        if not isinstance(gate.angle, (int, float)) or isinstance(gate.angle, bool) or not math.isfinite(float(gate.angle)):
            raise IonTrapCompileError(f"gate {index} requires a finite angle")
        if gate.inserted_for_routing:
            raise IonTrapCompileError("ion-trap compilation cannot contain routing gates")


def simulate_ion_trap_basis(
    compilation: IonTrapCompilation,
    logical_input_bits: Iterable[int],
) -> np.ndarray:
    """Simulate one computational-basis input under the ideal native circuit."""

    _validate_native(compilation)
    bits = tuple(logical_input_bits)
    n_qubits = compilation.logical_ir.n_qubits
    if len(bits) != n_qubits or any(bit not in (0, 1) for bit in bits):
        raise IonTrapCompileError("input must contain one integer 0/1 bit per qubit")
    state = np.zeros(1 << n_qubits, dtype=np.complex128)
    state[sum(bit << qubit for qubit, bit in enumerate(bits))] = 1.0
    for gate in compilation.native_gates:
        angle = float(gate.angle)
        if gate.name == "rz":
            matrix = np.array(
                [[cmath.exp(-0.5j * angle), 0.0], [0.0, cmath.exp(0.5j * angle)]],
                dtype=np.complex128,
            )
            _apply_one_qubit(state, gate.qubits[0], matrix)
        elif gate.name == "rx":
            cosine = math.cos(angle / 2)
            sine = -1j * math.sin(angle / 2)
            matrix = np.array([[cosine, sine], [sine, cosine]], dtype=np.complex128)
            _apply_one_qubit(state, gate.qubits[0], matrix)
        else:
            # RXX(theta) = cos(theta/2) I - i sin(theta/2) X tensor X.
            old = state.copy()
            mask = (1 << gate.qubits[0]) | (1 << gate.qubits[1])
            indices = np.arange(state.size) ^ mask
            state[:] = math.cos(angle / 2) * old - 1j * math.sin(angle / 2) * old[indices]
    return state


def _logical_output(logical_ir: LogicalCircuitIR, basis_index: int) -> int:
    bits = [(basis_index >> qubit) & 1 for qubit in range(logical_ir.n_qubits)]
    for gate in logical_ir.gates:
        if gate.gate_type == "X":
            bits[gate.target] ^= 1
        elif gate.gate_type == "CNOT":
            if bits[gate.controls[0]]:
                bits[gate.target] ^= 1
        elif all(bits[control] for control in gate.controls):
            bits[gate.target] ^= 1
    return sum(bit << qubit for qubit, bit in enumerate(bits))


def ion_trap_unitary(
    compilation: IonTrapCompilation,
    *,
    max_qubits: int = 8,
) -> np.ndarray:
    """Return the ideal native unitary for small independent audits."""

    n_qubits = compilation.logical_ir.n_qubits
    if n_qubits > max_qubits:
        raise IonTrapCompileError(f"unitary construction is capped at {max_qubits} qubits")
    return np.column_stack(
        [
            simulate_ion_trap_basis(
                compilation,
                tuple((basis >> qubit) & 1 for qubit in range(n_qubits)),
            )
            for basis in range(1 << n_qubits)
        ]
    )


def verify_ion_trap_equivalence(
    compilation: IonTrapCompilation,
    *,
    tolerance: float = 1e-9,
    max_qubits: int = 8,
) -> IonTrapEquivalenceCheck:
    """Check all basis states and the full unitary up to one global phase."""

    unitary = ion_trap_unitary(compilation, max_qubits=max_qubits)
    dimension = unitary.shape[0]
    expected = np.zeros_like(unitary)
    max_failure = 0.0
    for basis in range(dimension):
        output = _logical_output(compilation.logical_ir, basis)
        expected[output, basis] = 1.0
        max_failure = max(max_failure, max(0.0, 1.0 - float(abs(unitary[output, basis]) ** 2)))
    reference_row, reference_col = np.argwhere(np.abs(expected) > 0)[0]
    phase = unitary[reference_row, reference_col]
    phase_ok = abs(abs(phase) - 1.0) <= tolerance
    max_error = float(np.max(np.abs(unitary - phase * expected)))
    return IonTrapEquivalenceCheck(
        basis_equivalent=max_failure <= tolerance,
        unitary_equivalent_up_to_global_phase=phase_ok and max_error <= tolerance,
        tested_basis_states=dimension,
        max_basis_failure_probability=max_failure,
        max_unitary_error=max_error,
        global_phase_real=float(phase.real),
        global_phase_imag=float(phase.imag),
        tolerance=tolerance,
    )


def ion_native_to_openqasm3(compilation: IonTrapCompilation) -> str:
    """Serialize the ideal fully connected native resource circuit."""

    _validate_native(compilation)
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "",
        "// route: ion-trap ideal fully-connected resource adapter",
        f"// rxx_convention: {RXX_CONVENTION}",
        "// hardware_execution: false",
        f"qubit[{compilation.logical_ir.n_qubits}] q;",
        "",
    ]
    for gate in compilation.native_gates:
        if gate.name == "rxx":
            lines.append(f"rxx({gate.angle:.17g}) q[{gate.qubits[0]}], q[{gate.qubits[1]}];")
        else:
            lines.append(f"{gate.name}({gate.angle:.17g}) q[{gate.qubits[0]}];")
    return "\n".join(lines) + "\n"


__all__ = [
    "CLAIM_BOUNDARY",
    "EVIDENCE_STRENGTH",
    "ION_NATIVE_GATE_SET",
    "RXX_CONVENTION",
    "IonNativeGate",
    "IonTrapCompilation",
    "IonTrapCompileError",
    "IonTrapDiagnostics",
    "IonTrapEquivalenceCheck",
    "compile_ion_trap",
    "ion_native_to_openqasm3",
    "ion_trap_unitary",
    "simulate_ion_trap_basis",
    "verify_ion_trap_equivalence",
]
