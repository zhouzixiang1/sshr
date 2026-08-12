"""Auditable synthetic superconducting compilation and routing.

This module bridges the project's logical ``X/CNOT/MCT`` IR to a small
superconducting-style native alphabet (``rz``, ``sx``, ``x``, ``cx``).  The
profiles below are deterministic *synthetic topology models*, not vendor
devices and not calibration snapshots.  Their explicit noise parameters are
metadata only; this module performs ideal compilation and simulation.

Multi-controlled X gates are decomposed exactly (up to global phase) without
ancillas using a parity-phase expansion.  That construction is intentionally
simple and auditable, but exponential in the number of controls.  It is a
semantic reference backend, not a claim of an optimized pulse compiler.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
import cmath
import math
from typing import Iterable

import numpy as np

from src.hardware.qasm import (
    LogicalCircuitIR,
    LogicalGateIR,
    circuit_to_logical_ir,
    validate_logical_ir,
)
from src.sshr_lib.bool_func import QuantumCircuit


NATIVE_GATE_SET = ("rz", "sx", "x", "cx")

CLAIM_BOUNDARY = (
    "Deterministic ideal compilation against a synthetic coupling profile; "
    "not a physical device, calibration, pulse schedule, or noisy execution. "
    "Recorded noise parameters are not applied by this module."
)


class SuperconductingCompileError(ValueError):
    """Raised when a logical circuit or synthetic profile is invalid."""


@dataclass(frozen=True)
class NoiseParameters:
    """Explicit independent-error placeholders for downstream experiments.

    The compiler records these values but does not apply them.  Keeping the
    model and rates explicit prevents an ideal result from being mistaken for
    a calibrated hardware run.
    """

    model: str = "none"
    one_qubit_error: float = 0.0
    two_qubit_error: float = 0.0
    readout_error: float = 0.0

    def __post_init__(self) -> None:
        if not self.model:
            raise SuperconductingCompileError("noise model must be non-empty")
        for name in ("one_qubit_error", "two_qubit_error", "readout_error"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise SuperconductingCompileError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise SuperconductingCompileError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class CouplingProfile:
    """A declared synthetic coupling graph and native gate alphabet."""

    name: str
    topology_family: str
    n_qubits: int
    coupling_edges: tuple[tuple[int, int], ...]
    native_gate_set: tuple[str, ...] = NATIVE_GATE_SET
    noise: NoiseParameters = NoiseParameters()
    synthetic: bool = True
    calibration_source: str | None = None
    claim_boundary: str = CLAIM_BOUNDARY

    def __post_init__(self) -> None:
        if not isinstance(self.n_qubits, int) or isinstance(self.n_qubits, bool):
            raise SuperconductingCompileError("profile n_qubits must be an integer")
        if self.n_qubits <= 0:
            raise SuperconductingCompileError("profile n_qubits must be positive")
        if tuple(self.native_gate_set) != NATIVE_GATE_SET:
            raise SuperconductingCompileError(
                f"native_gate_set must be exactly {NATIVE_GATE_SET!r}"
            )
        normalized: list[tuple[int, int]] = []
        for raw_edge in self.coupling_edges:
            if len(raw_edge) != 2:
                raise SuperconductingCompileError("coupling edges must have two endpoints")
            a, b = raw_edge
            if (
                not isinstance(a, int)
                or isinstance(a, bool)
                or not isinstance(b, int)
                or isinstance(b, bool)
            ):
                raise SuperconductingCompileError("coupling endpoints must be integers")
            if not (0 <= a < self.n_qubits and 0 <= b < self.n_qubits):
                raise SuperconductingCompileError("coupling endpoint is out of range")
            if a == b:
                raise SuperconductingCompileError("coupling edges cannot be self-loops")
            normalized.append((min(a, b), max(a, b)))
        if tuple(sorted(set(normalized))) != self.coupling_edges:
            raise SuperconductingCompileError(
                "coupling_edges must be unique, normalized, and sorted"
            )
        if self.n_qubits > 1 and not _is_connected(self.n_qubits, self.coupling_edges):
            raise SuperconductingCompileError("coupling graph must be connected")
        if not self.synthetic or self.calibration_source is not None:
            raise SuperconductingCompileError(
                "built-in compiler accepts synthetic, uncalibrated profiles only"
            )


def linear_profile(
    n_qubits: int,
    *,
    noise: NoiseParameters = NoiseParameters(),
) -> CouplingProfile:
    """Return a deterministic nearest-neighbour line."""

    edges = tuple((q, q + 1) for q in range(n_qubits - 1))
    return CouplingProfile(
        name=f"synthetic-linear-{n_qubits}q-v1",
        topology_family="linear",
        n_qubits=n_qubits,
        coupling_edges=edges,
        noise=noise,
    )


def heavy_hex_like_profile(
    n_qubits: int,
    *,
    noise: NoiseParameters = NoiseParameters(),
) -> CouplingProfile:
    """Return a deterministic sparse degree-3 heavy-hex-like graph.

    This is deliberately named ``-like``: it is a connected chain with
    non-overlapping length-two chords, useful for topology sensitivity tests,
    and does not reproduce any vendor device layout.
    """

    edges = {(q, q + 1) for q in range(n_qubits - 1)}
    edges.update((q, q + 2) for q in range(0, n_qubits - 2, 4))
    return CouplingProfile(
        name=f"synthetic-heavy-hex-like-{n_qubits}q-v1",
        topology_family="heavy-hex-like",
        n_qubits=n_qubits,
        coupling_edges=tuple(sorted(edges)),
        noise=noise,
    )


@dataclass(frozen=True)
class NativeGate:
    """One physical native instruction with source provenance."""

    name: str
    qubits: tuple[int, ...]
    angle: float | None
    logical_gate_index: int
    origin: str
    inserted_for_routing: bool = False
    layer: int = 0


@dataclass(frozen=True)
class LogicalGateTrace:
    """Native range, mapping transition, and inserted swaps for one logical gate."""

    logical_gate_index: int
    logical_gate: LogicalGateIR
    decomposition: str
    native_start: int
    native_stop: int
    mapping_before: tuple[int, ...]
    mapping_after: tuple[int, ...]
    inserted_swaps: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class CompilationDiagnostics:
    logical_gate_count: int
    native_gate_count: int
    one_qubit_gate_count: int
    two_qubit_gate_count: int
    inserted_swap_count: int
    inserted_routing_cx_count: int
    native_depth: int
    initial_logical_to_physical: tuple[int, ...]
    final_logical_to_physical: tuple[int, ...]
    mct_decomposition: str
    noise_applied: bool
    claim_boundary: str


@dataclass(frozen=True)
class SuperconductingCompilation:
    logical_ir: LogicalCircuitIR
    profile: CouplingProfile
    native_gates: tuple[NativeGate, ...]
    traces: tuple[LogicalGateTrace, ...]
    diagnostics: CompilationDiagnostics


@dataclass(frozen=True)
class EquivalenceCheck:
    equivalent: bool
    tested_basis_states: int
    max_failure_probability: float
    tolerance: float


@dataclass(frozen=True)
class _AbstractGate:
    name: str
    logical_qubits: tuple[int, ...]
    angle: float | None = None
    origin: str = "logical"


def _is_connected(n_qubits: int, edges: Iterable[tuple[int, int]]) -> bool:
    if n_qubits == 1:
        return True
    adjacency = [[] for _ in range(n_qubits)]
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = {0}
    queue = deque([0])
    while queue:
        node = queue.popleft()
        for neighbour in adjacency[node]:
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return len(seen) == n_qubits


def _h(logical_qubit: int, origin: str) -> tuple[_AbstractGate, ...]:
    # H = Rz(pi/2) sqrt(X) Rz(pi/2), up to a global phase.
    return (
        _AbstractGate("rz", (logical_qubit,), math.pi / 2, origin),
        _AbstractGate("sx", (logical_qubit,), None, origin),
        _AbstractGate("rz", (logical_qubit,), math.pi / 2, origin),
    )


def _decompose_logical_gate(gate: LogicalGateIR) -> tuple[str, tuple[_AbstractGate, ...]]:
    if gate.gate_type == "X":
        return "native-x", (_AbstractGate("x", (gate.target,)),)
    if gate.gate_type == "CNOT":
        return "native-cx", (_AbstractGate("cx", (gate.controls[0], gate.target)),)

    # MCX = H(target) MCZ H(target).  For m Boolean variables,
    # AND(x_1,...,x_m) = 2^(1-m) sum_{S != empty} (-1)^(|S|+1) XOR(S).
    # Implement each parity phase with a CNOT compute/Rz/uncompute gadget.
    wires = (*gate.controls, gate.target)
    abstract: list[_AbstractGate] = list(_h(gate.target, "mcx-h"))
    denominator = 1 << (len(wires) - 1)
    for subset_size in range(1, len(wires) + 1):
        sign = 1.0 if subset_size % 2 else -1.0
        angle = sign * math.pi / denominator
        for subset in combinations(wires, subset_size):
            pivot = subset[-1]
            for logical_qubit in subset[:-1]:
                abstract.append(
                    _AbstractGate("cx", (logical_qubit, pivot), None, "mcx-parity")
                )
            abstract.append(_AbstractGate("rz", (pivot,), angle, "mcx-phase"))
            for logical_qubit in reversed(subset[:-1]):
                abstract.append(
                    _AbstractGate("cx", (logical_qubit, pivot), None, "mcx-parity")
                )
    abstract.extend(_h(gate.target, "mcx-h"))
    return "ancilla-free-exact-parity-phase", tuple(abstract)


def _shortest_path(profile: CouplingProfile, source: int, target: int) -> tuple[int, ...]:
    if source == target:
        return (source,)
    adjacency = [[] for _ in range(profile.n_qubits)]
    for a, b in profile.coupling_edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    parents: dict[int, int | None] = {source: None}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for neighbour in sorted(adjacency[node]):
            if neighbour in parents:
                continue
            parents[neighbour] = node
            if neighbour == target:
                queue.clear()
                break
            queue.append(neighbour)
    if target not in parents:
        raise SuperconductingCompileError("coupling graph has no routing path")
    reverse_path = [target]
    while reverse_path[-1] != source:
        reverse_path.append(parents[reverse_path[-1]])  # type: ignore[arg-type]
    return tuple(reversed(reverse_path))


def compile_superconducting(
    circuit: QuantumCircuit | LogicalCircuitIR,
    profile: CouplingProfile,
) -> SuperconductingCompilation:
    """Decompose and route a logical circuit against ``profile``.

    Placement starts at the identity.  Routing SWAPs are retained rather than
    restored, so ``final_logical_to_physical`` must be used when interpreting
    output wires.
    """

    logical_ir = circuit if isinstance(circuit, LogicalCircuitIR) else circuit_to_logical_ir(circuit)
    validate_logical_ir(logical_ir)
    if profile.n_qubits != logical_ir.n_qubits:
        raise SuperconductingCompileError(
            "profile and logical circuit must have the same number of qubits"
        )

    logical_to_physical = list(range(logical_ir.n_qubits))
    physical_to_logical = list(range(logical_ir.n_qubits))
    emitted: list[tuple[str, tuple[int, ...], float | None, int, str, bool]] = []
    traces: list[LogicalGateTrace] = []

    def emit_swap(a: int, b: int, logical_gate_index: int) -> None:
        for control, target in ((a, b), (b, a), (a, b)):
            emitted.append(
                ("cx", (control, target), None, logical_gate_index, "routing-swap", True)
            )
        logical_a, logical_b = physical_to_logical[a], physical_to_logical[b]
        physical_to_logical[a], physical_to_logical[b] = logical_b, logical_a
        logical_to_physical[logical_a], logical_to_physical[logical_b] = b, a

    for logical_gate_index, logical_gate in enumerate(logical_ir.gates):
        mapping_before = tuple(logical_to_physical)
        native_start = len(emitted)
        swaps: list[tuple[int, int]] = []
        decomposition, abstract_gates = _decompose_logical_gate(logical_gate)
        for abstract in abstract_gates:
            if abstract.name != "cx":
                physical = logical_to_physical[abstract.logical_qubits[0]]
                emitted.append(
                    (
                        abstract.name,
                        (physical,),
                        abstract.angle,
                        logical_gate_index,
                        abstract.origin,
                        False,
                    )
                )
                continue
            logical_control, logical_target = abstract.logical_qubits
            physical_control = logical_to_physical[logical_control]
            physical_target = logical_to_physical[logical_target]
            path = _shortest_path(profile, physical_control, physical_target)
            for edge_index in range(max(0, len(path) - 2)):
                edge = (path[edge_index], path[edge_index + 1])
                emit_swap(*edge, logical_gate_index)
                swaps.append(tuple(sorted(edge)))
            physical_control = logical_to_physical[logical_control]
            physical_target = logical_to_physical[logical_target]
            if tuple(sorted((physical_control, physical_target))) not in profile.coupling_edges:
                raise AssertionError("router failed to make CX operands adjacent")
            emitted.append(
                (
                    "cx",
                    (physical_control, physical_target),
                    None,
                    logical_gate_index,
                    abstract.origin,
                    False,
                )
            )
        traces.append(
            LogicalGateTrace(
                logical_gate_index=logical_gate_index,
                logical_gate=logical_gate,
                decomposition=decomposition,
                native_start=native_start,
                native_stop=len(emitted),
                mapping_before=mapping_before,
                mapping_after=tuple(logical_to_physical),
                inserted_swaps=tuple(swaps),
            )
        )

    last_layer = [-1] * profile.n_qubits
    native_gates: list[NativeGate] = []
    for name, qubits, angle, source_index, origin, inserted in emitted:
        layer = 1 + max((last_layer[q] for q in qubits), default=-1)
        for q in qubits:
            last_layer[q] = layer
        native_gates.append(
            NativeGate(name, qubits, angle, source_index, origin, inserted, layer)
        )

    inserted_swap_count = sum(len(trace.inserted_swaps) for trace in traces)
    diagnostics = CompilationDiagnostics(
        logical_gate_count=len(logical_ir.gates),
        native_gate_count=len(native_gates),
        one_qubit_gate_count=sum(len(gate.qubits) == 1 for gate in native_gates),
        two_qubit_gate_count=sum(len(gate.qubits) == 2 for gate in native_gates),
        inserted_swap_count=inserted_swap_count,
        inserted_routing_cx_count=3 * inserted_swap_count,
        native_depth=max((gate.layer for gate in native_gates), default=-1) + 1,
        initial_logical_to_physical=tuple(range(logical_ir.n_qubits)),
        final_logical_to_physical=tuple(logical_to_physical),
        mct_decomposition="ancilla-free-exact-parity-phase",
        noise_applied=False,
        claim_boundary=CLAIM_BOUNDARY,
    )
    return SuperconductingCompilation(
        logical_ir=logical_ir,
        profile=profile,
        native_gates=tuple(native_gates),
        traces=tuple(traces),
        diagnostics=diagnostics,
    )


def native_to_openqasm3(compilation: SuperconductingCompilation) -> str:
    """Serialize the physical native circuit with auditable mapping comments."""

    profile = compilation.profile
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "",
        f"// synthetic_profile: {profile.name}",
        f"// topology_family: {profile.topology_family}",
        f"// initial_logical_to_physical: {compilation.diagnostics.initial_logical_to_physical}",
        f"// final_logical_to_physical: {compilation.diagnostics.final_logical_to_physical}",
        "// noise_applied: false",
        f"qubit[{profile.n_qubits}] q;",
        "",
    ]
    for gate in compilation.native_gates:
        if gate.name == "rz":
            lines.append(f"rz({gate.angle:.17g}) q[{gate.qubits[0]}];")
        elif gate.name in {"sx", "x"}:
            lines.append(f"{gate.name} q[{gate.qubits[0]}];")
        else:
            lines.append(f"cx q[{gate.qubits[0]}], q[{gate.qubits[1]}];")
    return "\n".join(lines) + "\n"


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


def simulate_native_basis(
    compilation: SuperconductingCompilation,
    logical_input_bits: Iterable[int],
) -> np.ndarray:
    """Ideal-statevector simulation from a logical computational-basis input."""

    bits = tuple(logical_input_bits)
    n_qubits = compilation.profile.n_qubits
    if len(bits) != n_qubits or any(bit not in (0, 1) for bit in bits):
        raise SuperconductingCompileError("input must contain one 0/1 bit per qubit")
    initial_index = sum(bit << logical for logical, bit in enumerate(bits))
    state = np.zeros(1 << n_qubits, dtype=np.complex128)
    state[initial_index] = 1.0
    for gate in compilation.native_gates:
        if gate.name == "x":
            matrix = np.array([[0, 1], [1, 0]], dtype=np.complex128)
            _apply_one_qubit(state, gate.qubits[0], matrix)
        elif gate.name == "sx":
            matrix = 0.5 * np.array(
                [[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]],
                dtype=np.complex128,
            )
            _apply_one_qubit(state, gate.qubits[0], matrix)
        elif gate.name == "rz":
            angle = float(gate.angle)
            matrix = np.array(
                [[cmath.exp(-0.5j * angle), 0], [0, cmath.exp(0.5j * angle)]],
                dtype=np.complex128,
            )
            _apply_one_qubit(state, gate.qubits[0], matrix)
        elif gate.name == "cx":
            control, target = gate.qubits
            for index in range(state.size):
                if ((index >> control) & 1) and not ((index >> target) & 1):
                    partner = index | (1 << target)
                    state[index], state[partner] = state[partner], state[index]
        else:  # pragma: no cover - compilation construction prevents this.
            raise SuperconductingCompileError(f"unsupported native gate {gate.name!r}")
    return state


def _simulate_logical(logical_ir: LogicalCircuitIR, bits: tuple[int, ...]) -> tuple[int, ...]:
    output = list(bits)
    for gate in logical_ir.gates:
        if gate.gate_type == "X":
            output[gate.target] ^= 1
        elif gate.gate_type == "CNOT":
            if output[gate.controls[0]]:
                output[gate.target] ^= 1
        elif all(output[control] for control in gate.controls):
            output[gate.target] ^= 1
    return tuple(output)


def verify_basis_equivalence(
    compilation: SuperconductingCompilation,
    *,
    tolerance: float = 1e-9,
    max_qubits: int = 10,
) -> EquivalenceCheck:
    """Exhaustively compare logical and ideal native computational-basis action.

    The final routing permutation is explicitly decoded.  This checks the full
    reversible Boolean action, rather than only the target truth table for
    inputs with an output ancilla fixed to zero.  It does not certify relative
    phases between distinct computational-basis inputs.
    """

    n_qubits = compilation.profile.n_qubits
    if n_qubits > max_qubits:
        raise SuperconductingCompileError(
            f"exhaustive verification is capped at {max_qubits} qubits"
        )
    max_failure_probability = 0.0
    for basis_index in range(1 << n_qubits):
        input_bits = tuple((basis_index >> q) & 1 for q in range(n_qubits))
        expected_logical = _simulate_logical(compilation.logical_ir, input_bits)
        expected_physical_index = sum(
            expected_logical[logical] << physical
            for logical, physical in enumerate(
                compilation.diagnostics.final_logical_to_physical
            )
        )
        state = simulate_native_basis(compilation, input_bits)
        success_probability = float(abs(state[expected_physical_index]) ** 2)
        failure_probability = max(0.0, 1.0 - success_probability)
        max_failure_probability = max(max_failure_probability, failure_probability)
        if failure_probability > tolerance:
            return EquivalenceCheck(
                equivalent=False,
                tested_basis_states=basis_index + 1,
                max_failure_probability=max_failure_probability,
                tolerance=tolerance,
            )
    return EquivalenceCheck(
        equivalent=True,
        tested_basis_states=1 << n_qubits,
        max_failure_probability=max_failure_probability,
        tolerance=tolerance,
    )


__all__ = [
    "CLAIM_BOUNDARY",
    "NATIVE_GATE_SET",
    "CompilationDiagnostics",
    "CouplingProfile",
    "EquivalenceCheck",
    "LogicalGateTrace",
    "NativeGate",
    "NoiseParameters",
    "SuperconductingCompilation",
    "SuperconductingCompileError",
    "compile_superconducting",
    "heavy_hex_like_profile",
    "linear_profile",
    "native_to_openqasm3",
    "simulate_native_basis",
    "verify_basis_equivalence",
]
