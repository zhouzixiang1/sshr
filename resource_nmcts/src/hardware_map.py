#!/usr/bin/env python3
"""Hardware-compatibility validation layer for engine-synthesized oracle circuits.

This module bridges the engine's logic-level ``QuantumCircuit`` (X / CNOT / MCT
gates over data qubits ``0..n-1``, output qubit ``n``, factor ancillas
``n+1..`` — the exact layout produced by ``factor_plan.emit_plan_to_circuit``
and checked by ``factor_plan.verify_oracle``) to Qiskit:

* ``engine_to_qiskit`` converts an engine circuit to an equivalent Qiskit
  circuit implementing ``|x>|anc> -> |x>|anc XOR f(x)>``.
* ``map_to_basis`` / ``map_all_bases`` decompose multi-controlled Toffolis with
  Qiskit's standard high-level synthesis and transpile to superconducting
  native gate sets (CZ-based, IBM ECR-based, plus a CX+U reference) at
  ``optimization_level=1``.
* ``verify_oracle_aer`` checks functional equivalence exactly: the full
  permutation on all ``2**n`` input basis states is simulated with Aer
  statevector and compared against the Boolean function truth table,
  mirroring the semantics of ``factor_plan.verify_oracle``.
* ``mapped_metrics`` / ``collect_metrics`` produce the resource-metric rows
  stored by ``scripts/run_hardware_validation.py``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

import torch  # noqa: F401  (must load before qiskit)

from qiskit import QuantumCircuit as QiskitCircuit
from qiskit import transpile
from qiskit.circuit import AncillaRegister
from qiskit.synthesis.multi_controlled import (
    synth_mcx_1_clean_kg24,
    synth_mcx_n_clean_m15,
    synth_mcx_noaux_v24,
)
from qiskit.transpiler import CouplingMap, Target
from qiskit.transpiler.passes.synthesis.high_level_synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

from src.sshr_lib.bool_func import BooleanFunction
from src.sshr_lib.bool_func import QuantumCircuit as EngineCircuit


# ---------------------------------------------------------------------------
# Native basis definitions
# ---------------------------------------------------------------------------

# (a) CZ-based superconducting (Zuchongzhi-style), (b) IBM ECR-based,
# (c) trivial CX+U reference.
NATIVE_BASES: dict[str, list[str]] = {
    "cz_sx_x_rz": ["cz", "sx", "x", "rz"],
    "ecr_sx_x_rz": ["ecr", "sx", "x", "rz"],
    "cx_u": ["cx", "u"],
}

# Two-qubit entangling gate name(s) per basis, used for 2q count/depth metrics.
TWOQ_GATES: dict[str, frozenset[str]] = {
    "cz_sx_x_rz": frozenset({"cz"}),
    "ecr_sx_x_rz": frozenset({"ecr"}),
    "cx_u": frozenset({"cx"}),
}

# Cap on total qubits after adding clean decomposition ancillas, so that
# statevector simulation and transpilation stay cheap (spec: keep <= ~20).
MAX_MAPPING_QUBITS = 20


# ---------------------------------------------------------------------------
# Engine -> Qiskit conversion
# ---------------------------------------------------------------------------

def engine_to_qiskit(circ: EngineCircuit) -> QiskitCircuit:
    """Convert an engine ``QuantumCircuit`` to a Qiskit circuit.

    Qubit indices are mirrored one-to-one: engine qubit ``i`` maps to Qiskit
    qubit ``i`` (bit ``i`` of the statevector index), so data qubits are
    ``0..n-1``, the output qubit is ``n`` and ancillas are ``n+1..`` exactly
    as in ``factor_plan.emit_plan_to_circuit`` / ``verify_oracle``.
    """
    qc = QiskitCircuit(circ.n_qubits)
    for gate in circ.gates:
        if gate.type == "X":
            qc.x(gate.target)
        elif gate.type == "CNOT":
            if len(gate.controls) != 1:
                raise ValueError(f"CNOT gate with {len(gate.controls)} controls")
            qc.cx(gate.controls[0], gate.target)
        elif gate.type == "MCT":
            # Qiskit's standard MCX synthesis handles the decomposition down
            # to the basis during transpilation (clean/dirty ancilla v-chain
            # or no-auxiliary synthesis, chosen by HighLevelSynthesis).
            qc.mcx(list(gate.controls), gate.target)
        else:
            raise ValueError(f"unsupported engine gate type: {gate.type}")
    return qc


# ---------------------------------------------------------------------------
# Basis mapping
# ---------------------------------------------------------------------------

def _max_mct_controls(qc: QiskitCircuit) -> int:
    """Return the largest control count among MCX operations in ``qc``."""
    worst = 0
    for inst in qc.data:
        if inst.operation.name == "mcx":
            worst = max(worst, len(inst.qubits) - 1)
    return worst


def _lower_mcx_with_declared_ancillas(
    logical: QiskitCircuit,
    *,
    compiler_ancillas: int,
    methods: tuple[str, ...],
) -> QiskitCircuit:
    """Lower MCX gates without treating arbitrary oracle inputs as clean.

    Qiskit's ``qubits_initially_zero=True`` is unsafe for an oracle circuit:
    the data and output wires are prepared by the caller and are not generally
    in ``|0>``.  This routine explicitly assigns only newly appended
    ``AncillaRegister`` wires to clean-ancilla decompositions.  Every MCX is
    lowered before the generic transpiler runs with
    ``qubits_initially_zero=False``.
    """
    if compiler_ancillas < 0:
        raise ValueError("compiler_ancillas must be non-negative")
    work = logical.copy_empty_like()
    if compiler_ancillas:
        work.add_register(AncillaRegister(compiler_ancillas, "hls_anc"))
    ancilla_indices = list(range(logical.num_qubits, work.num_qubits))

    for instruction in logical.data:
        qindices = [logical.find_bit(qubit).index for qubit in instruction.qubits]
        cindices = [logical.find_bit(clbit).index for clbit in instruction.clbits]
        if instruction.operation.name != "mcx":
            work.append(
                instruction.operation,
                [work.qubits[index] for index in qindices],
                [work.clbits[index] for index in cindices],
            )
            continue

        controls = len(qindices) - 1
        if controls < 0:
            raise ValueError("invalid MCX arity")
        if (
            controls >= 3
            and "n_clean_m15" in methods
            and len(ancilla_indices) >= controls - 2
        ):
            decomposition = synth_mcx_n_clean_m15(controls)
            selected_ancillas = ancilla_indices[: controls - 2]
        elif controls >= 3 and "1_clean_kg24" in methods and ancilla_indices:
            decomposition = synth_mcx_1_clean_kg24(controls)
            selected_ancillas = ancilla_indices[:1]
        elif "noaux_v24" in methods or controls <= 2:
            decomposition = synth_mcx_noaux_v24(controls)
            selected_ancillas = []
        else:
            raise ValueError(
                f"no configured exact MCX lowering is feasible for {controls} controls "
                f"with {len(ancilla_indices)} declared clean ancillas"
            )
        work.compose(
            decomposition,
            qubits=[*qindices, *selected_ancillas],
            inplace=True,
        )
    return work


def map_to_basis(
    qc: QiskitCircuit,
    basis: str,
    optimization_level: int = 1,
) -> QiskitCircuit:
    """Transpile a converted oracle circuit to a native basis.

    Clean idle ancilla qubits (up to ``k_max - 2`` for the largest k-control
    MCX, capped by ``MAX_MAPPING_QUBITS``) are appended before transpilation so
    Qiskit's high-level synthesis can pick linear-depth clean-ancilla v-chain
    decompositions instead of exponential no-auxiliary ones.  The ancillas
    start and end in ``|0>`` and are reported in the mapped qubit count.
    """
    if basis not in NATIVE_BASES:
        raise ValueError(f"unknown basis: {basis}")
    extra = max(0, _max_mct_controls(qc) - 2)
    extra = min(extra, max(0, MAX_MAPPING_QUBITS - qc.num_qubits))
    work = _lower_mcx_with_declared_ancillas(
        qc,
        compiler_ancillas=extra,
        methods=("n_clean_m15", "1_clean_kg24", "noaux_v24"),
    )
    return transpile(
        work,
        basis_gates=NATIVE_BASES[basis],
        optimization_level=optimization_level,
        qubits_initially_zero=False,
    )


def _twoq_depth(qc: QiskitCircuit, twoq_names: frozenset[str]) -> int:
    """Depth of the circuit restricted to native two-qubit gates."""
    layers = [0] * qc.num_qubits
    depth = 0
    for inst in qc.data:
        if inst.operation.name not in twoq_names:
            continue
        qubits = [qc.find_bit(q).index for q in inst.qubits]
        layer = max(layers[q] for q in qubits) + 1
        for q in qubits:
            layers[q] = layer
        depth = max(depth, layer)
    return depth


def mapped_metrics(qc: QiskitCircuit, basis: str) -> dict[str, Any]:
    """Resource metrics of a basis-mapped circuit."""
    ops = qc.count_ops()
    twoq_names = TWOQ_GATES[basis]
    twoq_count = int(sum(ops.get(name, 0) for name in twoq_names))
    return {
        "gates": int(qc.size()),
        "depth": int(qc.depth()),
        "twoq_count": twoq_count,
        "twoq_depth": int(_twoq_depth(qc, twoq_names)),
        "swap_free": bool(ops.get("swap", 0) == 0),
        "num_qubits": int(qc.num_qubits),
    }


def map_all_bases(
    qc: QiskitCircuit,
    bases: dict[str, list[str]] | None = None,
    optimization_level: int = 1,
) -> dict[str, dict[str, Any]]:
    """Map to every native basis and return per-basis metric dicts."""
    bases = NATIVE_BASES if bases is None else bases
    return {
        basis: mapped_metrics(map_to_basis(qc, basis, optimization_level), basis)
        for basis in bases
    }


# ---------------------------------------------------------------------------
# Aer functional-equivalence check
# ---------------------------------------------------------------------------

@dataclass
class AerVerification:
    """Result of the exact basis-state equivalence simulation."""

    ok: bool
    evaluated: int
    mismatches: int
    max_prob_error: float


def verify_oracle_aer(
    bf: BooleanFunction,
    circ: EngineCircuit,
    simulator: AerSimulator | None = None,
) -> AerVerification:
    """Verify an engine circuit against the truth table with Aer statevector.

    Simulates the full permutation on all ``2**n`` input basis states: for
    every ``x`` the data qubits are prepared as ``|x>``, the oracle runs, and
    the final state must be peaked on ``|x>|f(x)>`` with all ancilla qubits
    returned to ``|0>`` — the same contract as ``factor_plan.verify_oracle``.
    """
    n = bf.n
    if circ.n_qubits <= n:
        return AerVerification(ok=False, evaluated=0, mismatches=1, max_prob_error=1.0)
    sim = simulator or AerSimulator(method="statevector")
    oracle = engine_to_qiskit(circ)
    nq = oracle.num_qubits

    tests = []
    expected = []
    for x in range(1 << n):
        test = QiskitCircuit(nq)
        for bit in range(n):
            if (x >> bit) & 1:
                test.x(bit)
        test.compose(oracle, inplace=True)
        test.save_statevector()
        tests.append(test)
        expected.append(x | (bf.evaluate(x) << n))

    result = sim.run(tests).result()
    mismatches = 0
    max_err = 0.0
    for i, want in enumerate(expected):
        probs = result.data(i)["statevector"].probabilities()
        got = int(probs.argmax())
        err = 1.0 - float(probs[want])
        max_err = max(max_err, err)
        if got != want or err > 1e-6:
            mismatches += 1
    return AerVerification(
        ok=mismatches == 0,
        evaluated=len(expected),
        mismatches=mismatches,
        max_prob_error=max_err,
    )


# ---------------------------------------------------------------------------
# Metric-row assembly
# ---------------------------------------------------------------------------

def collect_metrics(
    *,
    function_id: str,
    bf: BooleanFunction,
    method: str,
    result_cost: Any,
    circ: EngineCircuit,
    engine_correct: bool,
    aer: AerVerification,
    mapped: dict[str, dict[str, Any]],
    synth_time_s: float,
    map_time_s: float,
    run_ts: str,
) -> dict[str, Any]:
    """Flatten logic-level and per-basis mapped metrics into one row dict."""
    row: dict[str, Any] = {
        "run_ts": run_ts,
        "function_id": function_id,
        "n_inputs": int(bf.n),
        "method": method,
        "engine_correct": bool(engine_correct),
        "aer_correct": bool(aer.ok),
        "aer_states_evaluated": int(aer.evaluated),
        "aer_mismatches": int(aer.mismatches),
        "aer_max_prob_error": float(aer.max_prob_error),
        "logic_T": int(result_cost.T),
        "logic_CNOT": int(result_cost.CNOT),
        "logic_depth": int(result_cost.depth),
        "logic_gates": int(result_cost.gates),
        "logic_explicit_ancilla": int(result_cost.explicit_ancilla),
        "logic_peak_ancilla": int(result_cost.peak_ancilla),
        "engine_gates": int(len(circ.gates)),
        "engine_qubits": int(circ.n_qubits),
        "synth_time_s": float(synth_time_s),
        "map_time_s": float(map_time_s),
    }
    for basis, metrics in mapped.items():
        prefix = {"cz_sx_x_rz": "cz", "ecr_sx_x_rz": "ecr", "cx_u": "cxu"}.get(basis, basis)
        for key, value in metrics.items():
            row[f"{prefix}_{key}"] = value
    if row["logic_gates"]:
        row["cz_overhead"] = row["cz_gates"] / row["logic_gates"]
        row["ecr_overhead"] = row["ecr_gates"] / row["logic_gates"]
    return row


def timed_map_all_bases(
    circ: EngineCircuit,
    optimization_level: int = 1,
) -> tuple[dict[str, dict[str, Any]], float]:
    """Convert and map an engine circuit to all native bases, with timing."""
    t0 = time.time()
    mapped = map_all_bases(engine_to_qiskit(circ), optimization_level=optimization_level)
    return mapped, time.time() - t0


# ---------------------------------------------------------------------------
# Topology-aware compilation (Qiskit Target API)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TargetSpec:
    """Serializable description of a native gate set and coupling graph.

    ``coupling_edges`` contains directed Qiskit qargs.  When ``directed`` is
    false, reverse edges are added by :meth:`normalized_edges`; this is useful
    for symmetric CZ proxy targets.  A ``TargetSpec`` is deliberately kept
    independent of provider objects so that every experiment can persist a
    stable JSON manifest and configuration hash.
    """

    target_id: str
    num_qubits: int
    basis_gates: tuple[str, ...]
    twoq_gates: tuple[str, ...]
    coupling_edges: tuple[tuple[int, int], ...]
    directed: bool = True
    topology: str = "custom"
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id must be non-empty")
        if self.num_qubits < 1:
            raise ValueError("num_qubits must be positive")
        if not self.basis_gates:
            raise ValueError("basis_gates must be non-empty")
        missing = set(self.twoq_gates) - set(self.basis_gates)
        if missing:
            raise ValueError(f"two-qubit gates missing from basis: {sorted(missing)}")
        for edge in self.coupling_edges:
            if len(edge) != 2:
                raise ValueError(f"invalid coupling edge: {edge!r}")
            source, target = (int(edge[0]), int(edge[1]))
            if source == target:
                raise ValueError(f"self-loop coupling edge: {edge!r}")
            if not (0 <= source < self.num_qubits and 0 <= target < self.num_qubits):
                raise ValueError(f"coupling edge outside target width: {edge!r}")
        if self.num_qubits > 1 and self.twoq_gates and not self.coupling_edges:
            raise ValueError("a multi-qubit target requires coupling edges")

    @property
    def normalized_edges(self) -> tuple[tuple[int, int], ...]:
        edges = {(int(source), int(target)) for source, target in self.coupling_edges}
        if not self.directed:
            edges |= {(target, source) for source, target in edges}
        return tuple(sorted(edges))

    def coupling_map(self) -> CouplingMap:
        """Build a coupling map while retaining isolated physical qubits."""
        coupling = CouplingMap(description=f"{self.target_id}: {self.topology}")
        for qubit in range(self.num_qubits):
            coupling.add_physical_qubit(qubit)
        for source, target in self.normalized_edges:
            coupling.add_edge(source, target)
        return coupling

    def to_target(self) -> Target:
        """Construct the Qiskit :class:`~qiskit.transpiler.Target`."""
        return Target.from_configuration(
            basis_gates=list(self.basis_gates),
            num_qubits=self.num_qubits,
            coupling_map=self.coupling_map(),
        )

    def to_manifest(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "num_qubits": self.num_qubits,
            "basis_gates": list(self.basis_gates),
            "twoq_gates": list(self.twoq_gates),
            "coupling_edges": [list(edge) for edge in self.normalized_edges],
            "directed": self.directed,
            "topology": self.topology,
            "metadata": dict(self.metadata),
        }

    def config_hash(self) -> str:
        payload = json.dumps(
            self.to_manifest(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _spec_from_coupling(
    *,
    target_id: str,
    coupling: CouplingMap,
    basis_gates: tuple[str, ...],
    twoq_gate: str,
    directed: bool,
    topology: str,
    metadata: Mapping[str, Any] | None = None,
) -> TargetSpec:
    return TargetSpec(
        target_id=target_id,
        num_qubits=int(coupling.size()),
        basis_gates=basis_gates,
        twoq_gates=(twoq_gate,),
        coupling_edges=tuple((int(source), int(target)) for source, target in coupling.get_edges()),
        directed=directed,
        topology=topology,
        metadata={} if metadata is None else dict(metadata),
    )


def make_cx_full_target(num_qubits: int = 19) -> TargetSpec:
    """All-to-all CX reference target (not a claim about a real device)."""
    coupling = CouplingMap.from_full(num_qubits, bidirectional=True)
    return _spec_from_coupling(
        target_id=f"cx_full_{num_qubits}",
        coupling=coupling,
        basis_gates=("rz", "sx", "x", "cx"),
        twoq_gate="cx",
        directed=True,
        topology="full",
        metadata={"target_kind": "synthetic_reference"},
    )


def make_cx_line_target(num_qubits: int = 19, *, bidirectional: bool = True) -> TargetSpec:
    """Sparse nearest-neighbour CX line used as a routing stress target."""
    coupling = CouplingMap.from_line(num_qubits, bidirectional=bidirectional)
    suffix = "bidir" if bidirectional else "directed"
    return _spec_from_coupling(
        target_id=f"cx_line_{num_qubits}_{suffix}",
        coupling=coupling,
        basis_gates=("rz", "sx", "x", "cx"),
        twoq_gate="cx",
        directed=True,
        topology="line",
        metadata={"target_kind": "synthetic_topology"},
    )


def make_cz_grid_target(rows: int = 4, columns: int = 5) -> TargetSpec:
    """Bidirectional rectangular CZ grid proxy target."""
    coupling = CouplingMap.from_grid(rows, columns, bidirectional=True)
    return _spec_from_coupling(
        target_id=f"cz_grid_{rows}x{columns}",
        coupling=coupling,
        basis_gates=("rz", "sx", "x", "cz"),
        twoq_gate="cz",
        directed=False,
        topology=f"grid_{rows}x{columns}",
        metadata={"target_kind": "synthetic_topology"},
    )


def make_ecr_heavy_hex_target(distance: int = 3, *, bidirectional: bool = True) -> TargetSpec:
    """ECR heavy-hex proxy target; distance 3 contains 19 physical qubits."""
    coupling = CouplingMap.from_heavy_hex(distance, bidirectional=bidirectional)
    suffix = "bidir" if bidirectional else "directed"
    return _spec_from_coupling(
        target_id=f"ecr_heavy_hex_d{distance}_{suffix}",
        coupling=coupling,
        basis_gates=("rz", "sx", "x", "ecr"),
        twoq_gate="ecr",
        directed=True,
        topology=f"heavy_hex_d{distance}",
        metadata={"target_kind": "synthetic_topology"},
    )


@dataclass(frozen=True)
class CompileConfig:
    """Deterministic topology-aware transpilation policy."""

    optimization_level: int = 2
    layout_method: str | None = "sabre"
    routing_method: str | None = "sabre"
    seed_transpiler: int = 7
    hls_ancilla_budget: int = 0
    mcx_methods: tuple[str, ...] = ("n_clean_m15", "1_clean_kg24", "noaux_v24")
    verification_batch_size: int = 4
    aer_max_parallel_threads: int = 4
    aer_max_parallel_experiments: int = 1

    def __post_init__(self) -> None:
        if self.optimization_level not in {0, 1, 2, 3}:
            raise ValueError("optimization_level must be one of 0, 1, 2, 3")
        if self.hls_ancilla_budget < 0:
            raise ValueError("hls_ancilla_budget must be non-negative")
        if not self.mcx_methods:
            raise ValueError("mcx_methods must be non-empty")
        if self.verification_batch_size < 1:
            raise ValueError("verification_batch_size must be positive")
        if self.aer_max_parallel_threads < 1:
            raise ValueError("aer_max_parallel_threads must be positive")
        if self.aer_max_parallel_experiments < 1:
            raise ValueError("aer_max_parallel_experiments must be positive")

    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class OracleQubitRoles:
    """Logical roles before layout is applied."""

    data: tuple[int, ...]
    output: int
    engine_ancillas: tuple[int, ...]
    compiler_ancillas: tuple[int, ...]


@dataclass(frozen=True)
class TargetViolation:
    instruction_index: int
    operation: str
    qargs: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class HardwareMetrics:
    target_id: str
    target_hash: str
    compile_config_hash: str
    logical_qubits: int
    work_qubits: int
    physical_qubits: int
    active_physical_qubits: int
    compiler_ancillas: int
    transpiler_added_qubits: int
    gates: int
    depth: int
    oneq_count: int
    twoq_count: int
    twoq_depth: int
    highq_count: int
    gate_counts: dict[str, int]
    basis_reference_gates: int
    basis_reference_depth: int
    basis_reference_twoq_count: int
    routing_gate_delta: int
    routing_depth_delta: int
    routing_twoq_delta: int
    routing_twoq_overhead_ratio: float | None
    unsupported_instructions: int
    coupling_violations: int
    estimated_duration_s: float | None
    compile_time_s: float
    basis_reference_time_s: float


@dataclass(frozen=True)
class MappedVerification:
    """Phase-sensitive exact verification on the clean-ancilla subspace."""

    ok: bool
    mode: str
    evaluated: int
    mismatches: int
    max_probability_error: float
    max_leakage: float
    max_phase_error: float
    tolerance: float
    phase_tolerance: float


@dataclass
class MappedArtifact:
    """Logical, basis-only and topology-routed circuits plus evidence."""

    logical: QiskitCircuit
    work: QiskitCircuit
    basis_reference: QiskitCircuit
    mapped: QiskitCircuit
    target_spec: TargetSpec
    compile_config: CompileConfig
    roles: OracleQubitRoles | None
    initial_layout: tuple[int, ...]
    final_layout: tuple[int, ...]
    metrics: HardwareMetrics
    verification: MappedVerification | None = None


def validate_target_support(qc: QiskitCircuit, target: Target) -> tuple[TargetViolation, ...]:
    """Return every unsupported instruction/qarg pair in a compiled circuit."""
    violations: list[TargetViolation] = []
    operation_names = set(target.operation_names)
    for index, instruction in enumerate(qc.data):
        operation = instruction.operation
        if operation.name == "barrier":
            continue
        qargs = tuple(qc.find_bit(qubit).index for qubit in instruction.qubits)
        try:
            supported = target.instruction_supported(
                operation_name=operation.name,
                qargs=qargs,
                parameters=list(operation.params),
            )
        except (KeyError, TypeError, ValueError):
            supported = False
        if supported:
            continue
        if operation.name not in operation_names:
            reason = "unsupported_operation"
        elif len(qargs) == 2:
            reason = "unsupported_coupling_or_direction"
        else:
            reason = "unsupported_qargs_or_parameters"
        violations.append(TargetViolation(index, operation.name, qargs, reason))
    return tuple(violations)


def _arity_metrics(qc: QiskitCircuit) -> tuple[int, int, int, int]:
    oneq = 0
    twoq = 0
    highq = 0
    active: set[int] = set()
    for instruction in qc.data:
        if instruction.operation.name == "barrier":
            continue
        arity = len(instruction.qubits)
        active.update(qc.find_bit(qubit).index for qubit in instruction.qubits)
        if arity == 1:
            oneq += 1
        elif arity == 2:
            twoq += 1
        elif arity > 2:
            highq += 1
    return oneq, twoq, highq, len(active)


def _generic_twoq_depth(qc: QiskitCircuit) -> int:
    return int(
        qc.depth(
            filter_function=lambda instruction: (
                instruction.operation.name != "barrier" and len(instruction.qubits) == 2
            )
        )
    )


def _layout_indices(qc: QiskitCircuit, input_width: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if qc.layout is None:
        identity = tuple(range(input_width))
        return identity, identity
    initial = tuple(int(index) for index in qc.layout.initial_index_layout(filter_ancillas=True))
    final = tuple(int(index) for index in qc.layout.final_index_layout(filter_ancillas=True))
    if len(initial) != input_width or len(final) != input_width:
        raise RuntimeError(
            "transpiler layout width mismatch: "
            f"input={input_width}, initial={len(initial)}, final={len(final)}"
        )
    return initial, final


def _optional_duration(qc: QiskitCircuit, target: Target) -> float | None:
    try:
        value = float(qc.estimate_duration(target, unit="s"))
    except Exception:  # Calibration-free synthetic targets have no durations.
        return None
    return value


def _hardware_metrics(
    *,
    logical: QiskitCircuit,
    work: QiskitCircuit,
    basis_reference: QiskitCircuit,
    mapped: QiskitCircuit,
    target_spec: TargetSpec,
    target: Target,
    config: CompileConfig,
    violations: tuple[TargetViolation, ...],
    compile_time_s: float,
    basis_reference_time_s: float,
) -> HardwareMetrics:
    oneq, twoq, highq, active = _arity_metrics(mapped)
    _, basis_twoq, _, _ = _arity_metrics(basis_reference)
    ratio = None if basis_twoq == 0 else (twoq - basis_twoq) / basis_twoq
    coupling_violations = sum(
        violation.reason == "unsupported_coupling_or_direction" for violation in violations
    )
    return HardwareMetrics(
        target_id=target_spec.target_id,
        target_hash=target_spec.config_hash(),
        compile_config_hash=config.config_hash(),
        logical_qubits=int(logical.num_qubits),
        work_qubits=int(work.num_qubits),
        physical_qubits=int(mapped.num_qubits),
        active_physical_qubits=active,
        compiler_ancillas=int(work.num_qubits - logical.num_qubits),
        transpiler_added_qubits=int(mapped.num_qubits - work.num_qubits),
        gates=int(mapped.size()),
        depth=int(mapped.depth()),
        oneq_count=oneq,
        twoq_count=twoq,
        twoq_depth=_generic_twoq_depth(mapped),
        highq_count=highq,
        gate_counts={str(name): int(count) for name, count in mapped.count_ops().items()},
        basis_reference_gates=int(basis_reference.size()),
        basis_reference_depth=int(basis_reference.depth()),
        basis_reference_twoq_count=basis_twoq,
        routing_gate_delta=int(mapped.size() - basis_reference.size()),
        routing_depth_delta=int(mapped.depth() - basis_reference.depth()),
        routing_twoq_delta=int(twoq - basis_twoq),
        routing_twoq_overhead_ratio=ratio,
        unsupported_instructions=len(violations),
        coupling_violations=int(coupling_violations),
        estimated_duration_s=_optional_duration(mapped, target),
        compile_time_s=float(compile_time_s),
        basis_reference_time_s=float(basis_reference_time_s),
    )


def verify_mapped_oracle(
    bf: BooleanFunction,
    artifact: MappedArtifact,
    simulator: AerSimulator | None = None,
    *,
    max_n_inputs: int = 8,
    tolerance: float = 1e-8,
    phase_tolerance: float = 1e-8,
    batch_size: int | None = None,
) -> MappedVerification:
    """Exactly verify ``|x,y,0> -> |x,y XOR f(x),0>`` after routing.

    All ``2**(n+1)`` data/output basis states are prepared on the physical
    positions given by ``initial_layout`` and decoded with ``final_layout``.
    Requiring a common target amplitude phase across every case catches
    relative-phase errors that a probability-only truth-table check misses.
    """
    if bf.n > max_n_inputs:
        raise ValueError(
            f"exact mapped verification is limited to n <= {max_n_inputs}; got n={bf.n}"
        )
    if batch_size is None:
        batch_size = int(artifact.compile_config.verification_batch_size)
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if artifact.roles is None:
        raise ValueError("mapped artifact has no oracle qubit roles")
    roles = artifact.roles
    expected_data = tuple(range(bf.n))
    if roles.data != expected_data or roles.output != bf.n:
        raise ValueError("oracle roles do not match the BooleanFunction convention")
    if len(artifact.initial_layout) != artifact.work.num_qubits:
        raise ValueError("initial layout does not cover the work circuit")
    if len(artifact.final_layout) != artifact.work.num_qubits:
        raise ValueError("final layout does not cover the work circuit")

    if simulator is None:
        available_threads = max(1, int(os.cpu_count() or 1))
        max_parallel_threads = min(
            int(artifact.compile_config.aer_max_parallel_threads),
            available_threads,
        )
        # Parallelize only circuits already admitted by the bounded verification
        # batch.  This raises CPU utilization without recreating the unbounded
        # all-input-state submission that previously exhausted host memory.
        max_parallel_experiments = min(
            int(artifact.compile_config.aer_max_parallel_experiments),
            int(batch_size),
            max_parallel_threads,
        )
        sim = AerSimulator(
            method="statevector",
            enable_truncation=True,
            max_parallel_experiments=max_parallel_experiments,
            max_parallel_threads=max_parallel_threads,
        )
    else:
        sim = simulator
    cases = [(x, y) for x in range(1 << bf.n) for y in (0, 1)]
    amplitudes: list[complex] = []
    probability_errors: list[float] = []
    leakages: list[float] = []

    for start in range(0, len(cases), batch_size):
        batch = cases[start : start + batch_size]
        tests: list[QiskitCircuit] = []
        expected_indices: list[int] = []
        for x, y in batch:
            test = QiskitCircuit(artifact.mapped.num_qubits)
            for bit in range(bf.n):
                if (x >> bit) & 1:
                    test.x(artifact.initial_layout[bit])
            if y:
                test.x(artifact.initial_layout[roles.output])
            test.compose(artifact.mapped, inplace=True)
            test.save_statevector()
            tests.append(test)

            expected_index = 0
            for bit in range(bf.n):
                if (x >> bit) & 1:
                    expected_index |= 1 << artifact.final_layout[bit]
            if y ^ int(bool(bf.evaluate(x))):
                expected_index |= 1 << artifact.final_layout[roles.output]
            # Every engine/compiler/transpiler ancilla is implicitly expected
            # to be zero because no other physical bit is set in this index.
            expected_indices.append(expected_index)

        result = sim.run(tests).result()
        if not result.success:
            raise RuntimeError(f"Aer mapped verification failed: {result.status}")
        for index, expected_index in enumerate(expected_indices):
            statevector = result.data(index)["statevector"]
            amplitude = complex(statevector[expected_index])
            probability = abs(amplitude) ** 2
            if not math.isfinite(probability):
                probability_error = float("inf")
                leakage = float("inf")
            else:
                probability_error = abs(1.0 - probability)
                leakage = max(0.0, 1.0 - probability)
            amplitudes.append(amplitude)
            probability_errors.append(probability_error)
            leakages.append(leakage)

    phase_reference = 1.0 + 0.0j
    for amplitude in amplitudes:
        if math.isfinite(amplitude.real) and math.isfinite(amplitude.imag) and abs(amplitude) > tolerance:
            phase_reference = amplitude / abs(amplitude)
            break
    phase_errors = [
        abs(amplitude / phase_reference - 1.0)
        if math.isfinite(amplitude.real) and math.isfinite(amplitude.imag)
        else float("inf")
        for amplitude in amplitudes
    ]
    mismatches = sum(
        probability_error > tolerance or phase_error > phase_tolerance
        for probability_error, phase_error in zip(probability_errors, phase_errors)
    )
    max_probability_error = max(probability_errors, default=0.0)
    max_leakage = max(leakages, default=0.0)
    max_phase_error = max(phase_errors, default=0.0)
    return MappedVerification(
        ok=mismatches == 0,
        mode="exact_xy_phase",
        evaluated=len(cases),
        mismatches=int(mismatches),
        max_probability_error=float(max_probability_error),
        max_leakage=float(max_leakage),
        max_phase_error=float(max_phase_error),
        tolerance=float(tolerance),
        phase_tolerance=float(phase_tolerance),
    )


def compile_for_target(
    circ: EngineCircuit | QiskitCircuit,
    target_spec: TargetSpec,
    config: CompileConfig | None = None,
    *,
    bf: BooleanFunction | None = None,
    n_inputs: int | None = None,
    simulator: AerSimulator | None = None,
    verify: bool = True,
) -> MappedArtifact:
    """Compile an oracle to a native target and retain all mapping evidence.

    Passing ``bf`` enables exact post-mapping verification.  ``n_inputs`` is
    only needed when callers want qubit-role metadata without a truth table.
    """
    config = CompileConfig() if config is None else config
    if isinstance(circ, EngineCircuit):
        logical = engine_to_qiskit(circ)
    elif isinstance(circ, QiskitCircuit):
        logical = circ.copy()
    else:
        raise TypeError(f"unsupported circuit type: {type(circ).__name__}")

    if bf is not None:
        if n_inputs is not None and n_inputs != bf.n:
            raise ValueError("n_inputs disagrees with bf.n")
        n_inputs = bf.n
    if n_inputs is not None and not (0 <= n_inputs < logical.num_qubits):
        raise ValueError("n_inputs must leave one logical output qubit")
    if logical.num_qubits > target_spec.num_qubits:
        raise ValueError(
            f"target {target_spec.target_id} has {target_spec.num_qubits} qubits, "
            f"but the logical circuit needs {logical.num_qubits}"
        )

    needed_hls_ancillas = max(0, _max_mct_controls(logical) - 2)
    available = target_spec.num_qubits - logical.num_qubits
    compiler_ancillas = min(needed_hls_ancillas, config.hls_ancilla_budget, available)
    work = _lower_mcx_with_declared_ancillas(
        logical,
        compiler_ancillas=compiler_ancillas,
        methods=config.mcx_methods,
    )

    roles: OracleQubitRoles | None = None
    if n_inputs is not None:
        roles = OracleQubitRoles(
            data=tuple(range(n_inputs)),
            output=n_inputs,
            engine_ancillas=tuple(range(n_inputs + 1, logical.num_qubits)),
            compiler_ancillas=tuple(range(logical.num_qubits, work.num_qubits)),
        )

    hls_config = HLSConfig(mcx=list(config.mcx_methods))
    reference_start = time.perf_counter()
    basis_reference = transpile(
        work,
        basis_gates=list(target_spec.basis_gates),
        optimization_level=config.optimization_level,
        seed_transpiler=config.seed_transpiler,
        hls_config=hls_config,
        qubits_initially_zero=False,
    )
    reference_time = time.perf_counter() - reference_start

    target = target_spec.to_target()
    pass_manager = generate_preset_pass_manager(
        target=target,
        optimization_level=config.optimization_level,
        layout_method=config.layout_method,
        routing_method=config.routing_method,
        seed_transpiler=config.seed_transpiler,
        hls_config=hls_config,
        qubits_initially_zero=False,
    )
    compile_start = time.perf_counter()
    mapped = pass_manager.run(work)
    compile_time = time.perf_counter() - compile_start
    initial_layout, final_layout = _layout_indices(mapped, work.num_qubits)
    violations = validate_target_support(mapped, target)
    metrics = _hardware_metrics(
        logical=logical,
        work=work,
        basis_reference=basis_reference,
        mapped=mapped,
        target_spec=target_spec,
        target=target,
        config=config,
        violations=violations,
        compile_time_s=compile_time,
        basis_reference_time_s=reference_time,
    )
    artifact = MappedArtifact(
        logical=logical,
        work=work,
        basis_reference=basis_reference,
        mapped=mapped,
        target_spec=target_spec,
        compile_config=config,
        roles=roles,
        initial_layout=initial_layout,
        final_layout=final_layout,
        metrics=metrics,
    )
    if violations:
        preview = ", ".join(
            f"{violation.operation}{violation.qargs}" for violation in violations[:4]
        )
        raise RuntimeError(
            f"mapped circuit violates {target_spec.target_id}: {len(violations)} unsupported "
            f"instructions ({preview})"
        )
    if verify:
        if bf is None:
            if n_inputs is not None:
                raise ValueError("bf is required when verify=True and n_inputs is specified")
        else:
            artifact.verification = verify_mapped_oracle(bf, artifact, simulator=simulator)
            if not artifact.verification.ok:
                raise RuntimeError(
                    f"mapped oracle verification failed: {artifact.verification.mismatches}/"
                    f"{artifact.verification.evaluated} cases"
                )
    return artifact
