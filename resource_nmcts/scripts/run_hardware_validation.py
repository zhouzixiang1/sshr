#!/usr/bin/env python3
"""Run reproducible topology-aware Boolean-oracle hardware validation.

The public :func:`src.synthesizers.synthesize_artifact` API is called exactly
once for each ``function x method x synthesis-seed`` cell.  The returned gate
artifact is then compiled independently for every requested synthetic target
and transpiler seed with :func:`src.hardware_map.compile_for_target`.

The output is an append-ready JSONL fact stream.  This script deliberately
does not create or mutate DuckDB tables; database ingestion is a separate
layer.  Successful rows retain target/configuration hashes, layouts, native
gate counts, basis-reference deltas, coupling checks, and the exact mapped
``|x,y,0> -> |x,y XOR f(x),0>`` phase-sensitive verification evidence.

Examples (run from ``resource_nmcts/``)::

    python scripts/run_hardware_validation.py --dry-run
    python scripts/run_hardware_validation.py \
      --functions maj3 --methods direct_anf,resource_nmcts \
      --seeds 7,11,19 --targets cx_full,cx_line,cz_grid,ecr_heavy_hex \
      --transpile-seeds 3,5,7 --timeout 120 \
      --output-jsonl results/hardware_validation_v2.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import queue
import random
import sys
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence, TypeVar

# Required on the Windows workstation when torch and Qiskit's MKL/OpenMP
# dependencies share one process.  It must be set before importing torch.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch  # noqa: E402,F401  (must load before qiskit_aer on Windows)
import psutil  # noqa: E402

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.anf_utils import (  # noqa: E402
    majority_function,
    parity_function,
    random_anf_function,
    random_truth_function,
    threshold_function,
)
from src.competition_benchmarks import (  # noqa: E402
    SUITE_VERSION as COMPETITION_SUITE_VERSION,
    competition_suite,
    function_key as competition_function_key,
    suite_manifest as competition_suite_manifest,
)
from src.factor_plan import SearchConfig, verify_oracle  # noqa: E402
from src.hardware_map import (  # noqa: E402
    CompileConfig,
    TargetSpec,
    compile_for_target,
    make_cx_full_target,
    make_cx_line_target,
    make_cz_grid_target,
    make_ecr_heavy_hex_target,
    verify_mapped_oracle,
)
from src.resource_model import ResourceCost, ResourceWeights  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction, Gate, QuantumCircuit  # noqa: E402
from src.synthesizers import synthesize_artifact  # noqa: E402


SCHEMA_VERSION = "hardware-validation-v3"
LEGACY_SCHEMA_VERSION = "hardware-validation-v2"
DEFAULT_MODEL = _PROJECT_ROOT / "models" / "action_scorer_competition.pt"
DEFAULT_TIMEOUT_S = 120.0

METHODS = (
    "direct_anf",
    "greedy_factor",
    "mcts_factor",
    "sshr_h",
    "sshr_beam",
    "neural_mcts",
    "resource_nmcts",
)
NEURAL_METHODS = frozenset({"neural_mcts", "resource_nmcts"})
TARGET_NAMES = ("cx_full", "cx_line", "cz_grid", "ecr_heavy_hex")
KNOWN_NATIVE_GATES = ("rz", "sx", "x", "cx", "cz", "ecr")
_NamedValue = TypeVar("_NamedValue")


# ---------------------------------------------------------------------------
# Benchmark inputs and stable provenance
# ---------------------------------------------------------------------------

def _aes_sbox_component(bit: int) -> BooleanFunction:
    path = _PROJECT_ROOT / "results" / "aes_sbox_functions.json"
    table = json.loads(path.read_text(encoding="utf-8"))["sbox"]
    truth_table = 0
    for x, value in enumerate(table):
        if (value >> bit) & 1:
            truth_table |= 1 << x
    return BooleanFunction(8, truth_table)


def benchmark_functions(suite: str = "smoke") -> list[tuple[str, str, BooleanFunction]]:
    """Return ``(function_id, family, BooleanFunction)`` benchmark tuples.

    ``smoke`` retains the compact historical runner set for fast integration
    tests. ``final`` is the frozen 30-case competition suite and is the only
    suite intended for reported competition comparisons.
    """
    if suite == "final":
        return [(case.case_id, case.family, case.function) for case in competition_suite()]
    if suite != "smoke":
        raise ValueError(f"unknown benchmark suite: {suite}")
    return [
        ("and3", "structured", BooleanFunction(3, 0b10000000)),
        ("parity4", "structured", parity_function(4)),
        ("maj3", "structured", majority_function(3)),
        ("maj5", "structured", majority_function(5)),
        ("thr6_t3", "structured", threshold_function(6, 3)),
        ("randtt4_s7", "random_truth", random_truth_function(4, random.Random(7))),
        ("randanf6_s11", "random_anf", random_anf_function(6, random.Random(11))),
        (
            "randanf8_s13",
            "random_anf",
            random_anf_function(8, random.Random(13), term_prob=0.10, max_degree=3),
        ),
        ("aes_sbox_b0", "aes_sbox", _aes_sbox_component(0)),
        ("aes_sbox_b7", "aes_sbox", _aes_sbox_component(7)),
    ]


def base_config() -> SearchConfig:
    return SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=3,
        max_factor_size=4,
        candidate_top_k=12,
        mcts_simulations=24,
        neural_mcts_simulations=32,
        max_polarities=8,
    )


def target_catalog(
    *,
    cx_qubits: int = 19,
    grid_rows: int = 4,
    grid_columns: int = 5,
    heavy_hex_distance: int = 3,
) -> dict[str, TargetSpec]:
    """Build the named synthetic targets used by the competition benchmark."""
    return {
        "cx_full": make_cx_full_target(cx_qubits),
        "cx_line": make_cx_line_target(cx_qubits),
        "cz_grid": make_cz_grid_target(grid_rows, grid_columns),
        "ecr_heavy_hex": make_ecr_heavy_hex_target(heavy_hex_distance),
    }


def _jsonable(value: Any) -> Any:
    """Convert dataclass-derived tuples/mappings into canonical JSON values."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value == "uniform-prior" or value.startswith("random-prior:"):
        return _canonical_hash({"virtual_prior": value})
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _truth_table_hex(bf: BooleanFunction) -> str:
    width = max(1, ((1 << bf.n) + 3) // 4)
    return f"0x{bf.truth_table:0{width}x}"


def _function_hash(bf: BooleanFunction) -> str:
    # This is deliberately the exact frozen-suite content key.  Training-set
    # exclusion, runner provenance, and database linkage must all identify the
    # same Boolean function byte-for-byte.
    return competition_function_key(bf)


def _synthesis_key(
    *,
    function_hash: str,
    method: str,
    seed: int,
    synthesis_config_hash: str,
    model_hash: str | None,
) -> str:
    return _canonical_hash(
        {
            "function_hash": function_hash,
            "method": method,
            "seed": seed,
            "synthesis_config_hash": synthesis_config_hash,
            "model_hash": model_hash,
        }
    )


def _record_key(synthesis_key: str, target_hash: str, compile_config_hash: str) -> str:
    return _canonical_hash(
        {
            "synthesis_key": synthesis_key,
            "target_hash": target_hash,
            "compile_config_hash": compile_config_hash,
        }
    )


def _suite_identity(
    functions: Sequence[tuple[str, str, BooleanFunction]], *, label: str
) -> str:
    return _canonical_hash(
        {
            "label": label,
            "cases": [
                {
                    "case_id": function_id,
                    "family": family,
                    "function_hash": _function_hash(bf),
                }
                for function_id, family, bf in functions
            ],
        }
    )


# ---------------------------------------------------------------------------
# Spawn-safe hard-timeout worker
# ---------------------------------------------------------------------------

def _pack_circuit(circ: QuantumCircuit) -> list[tuple[str, list[int], int]]:
    return [(gate.type, list(gate.controls), int(gate.target)) for gate in circ.gates]


def _unpack_circuit(gates: Sequence[Sequence[Any]], n_qubits: int) -> QuantumCircuit:
    circ = QuantumCircuit(int(n_qubits))
    for gate_type, controls, target in gates:
        circ.gates.append(Gate(str(gate_type), [int(q) for q in controls], int(target)))
    return circ


def synthesize_circuit(
    method: str,
    bf: BooleanFunction,
    config: SearchConfig,
    seed: int,
    model_path: str | None,
) -> tuple[ResourceCost, QuantumCircuit]:
    """Compatibility adapter backed by the public artifact API."""
    artifact = synthesize_artifact(method, bf, config, seed=seed, model_path=model_path)
    return artifact.result.cost, artifact.circuit


def _worker_main(task_q: Any, result_q: Any) -> None:
    """Execute one synthesis or topology-mapping task at a time."""
    while True:
        task = task_q.get()
        if task is None:
            return
        kind = str(task[0])
        stage = "worker_dispatch"
        try:
            if kind == "synth":
                stage = "synthesis"
                result_q.put(("progress", {"stage": stage}))
                _, method, bf, config, seed, model_path = task
                started = time.perf_counter()
                artifact = synthesize_artifact(
                    method,
                    bf,
                    config,
                    seed=int(seed),
                    model_path=model_path,
                )
                synth_time_s = time.perf_counter() - started
                circ = artifact.circuit

                stage = "logical_verification"
                result_q.put(("progress", {"stage": stage}))
                verify_started = time.perf_counter()
                engine_correct = bool(verify_oracle(circ, bf))
                logical_verify_time_s = time.perf_counter() - verify_started
                result_q.put(
                    (
                        "ok",
                        {
                            "cost": asdict(artifact.result.cost),
                            "gates": _pack_circuit(circ),
                            "n_qubits": int(circ.n_qubits),
                            "result_method": artifact.result.method,
                            "selected_method": artifact.selected_method,
                            "result_correct": bool(artifact.result.correct),
                            "result_terms": int(artifact.result.terms),
                            "result_gates": int(artifact.result.gates),
                            "result_n_qubits": int(artifact.result.n_qubits),
                            "reported_synth_time_s": float(artifact.result.time_s),
                            "engine_correct": engine_correct,
                            "engine_states_evaluated": int(1 << bf.n),
                            "synth_time_s": float(synth_time_s),
                            "logical_verify_time_s": float(logical_verify_time_s),
                        },
                    )
                )
            elif kind == "map":
                _, gates, n_qubits, bf, target_spec, compile_config = task
                circ = _unpack_circuit(gates, n_qubits)

                stage = "mapping"
                result_q.put(("progress", {"stage": stage}))
                started = time.perf_counter()
                mapped = compile_for_target(
                    circ,
                    target_spec,
                    compile_config,
                    bf=bf,
                    verify=False,
                )
                map_time_s = time.perf_counter() - started

                stage = "mapped_verification"
                result_q.put(("progress", {"stage": stage}))
                verify_started = time.perf_counter()
                verification = verify_mapped_oracle(bf, mapped)
                payload = {
                    "metrics": asdict(mapped.metrics),
                    "initial_layout": list(mapped.initial_layout),
                    "final_layout": list(mapped.final_layout),
                    "verification": asdict(verification),
                    "map_time_s": float(map_time_s),
                    "mapped_verify_time_s": float(time.perf_counter() - verify_started),
                }
                if verification.ok:
                    result_q.put(("ok", payload))
                else:
                    payload.update(
                        {
                            "stage": stage,
                            "error_code": "oracle_mismatch",
                            "error_message": (
                                f"mapped oracle mismatched {verification.mismatches}/"
                                f"{verification.evaluated} exact (x,y) cases"
                            ),
                        }
                    )
                    result_q.put(("mismatch", payload))
            else:
                raise ValueError(f"unknown worker task kind: {kind}")
        except Exception as exc:  # The parent records the stage/code/message.
            result_q.put(
                (
                    "error",
                    {
                        "stage": stage,
                        "error_code": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )
            )


class StageWorker:
    """Persistent spawned worker with bounded lifetime and memory protection.

    Resource sampling happens in the parent process while it waits on the
    result queue, so a wedged worker cannot suppress telemetry.  RSS is the
    sum of the exact worker process and its recursive children.  The guard
    never scans for, or terminates, unrelated Python processes.
    """

    def __init__(
        self,
        *,
        max_tasks: int = 8,
        max_system_memory_percent: float | None = 70.0,
    ) -> None:
        if max_tasks < 1:
            raise ValueError("max_tasks must be positive")
        if max_system_memory_percent is not None and not (
            0.0 < float(max_system_memory_percent) <= 100.0
        ):
            raise ValueError("max_system_memory_percent must be in (0, 100] or None")
        self._max_tasks = int(max_tasks)
        self._max_system_memory_percent = (
            None
            if max_system_memory_percent is None
            else float(max_system_memory_percent)
        )
        self._completed_tasks = 0
        self._ctx = mp.get_context("spawn")
        self._start()

    def _start(self) -> None:
        self._task_q = self._ctx.Queue()
        self._result_q = self._ctx.Queue()
        self._proc = self._ctx.Process(
            target=_worker_main,
            args=(self._task_q, self._result_q),
            daemon=True,
        )
        self._proc.start()
        self._completed_tasks = 0

    @staticmethod
    def _sample_process_tree(pid: int | None) -> tuple[float | None, float]:
        """Return ``(process-tree RSS MiB, system-memory percent)``.

        A process may disappear between enumeration and inspection; those
        races are expected during normal worker completion and are ignored.
        System memory remains observable even if the process has just exited.
        """
        system_percent = float(psutil.virtual_memory().percent)
        if pid is None:
            return None, system_percent
        try:
            root = psutil.Process(int(pid))
            processes = [root, *root.children(recursive=True)]
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return None, system_percent
        rss_bytes = 0
        observed = False
        for process in processes:
            try:
                rss_bytes += int(process.memory_info().rss)
                observed = True
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
        if not observed:
            return None, system_percent
        return rss_bytes / (1024.0 * 1024.0), system_percent

    @staticmethod
    def _update_resource_peaks(
        peaks: dict[str, dict[str, float | None]],
        stage: str,
        rss_mb: float | None,
        system_percent: float,
    ) -> None:
        values = peaks.setdefault(
            str(stage),
            {"peak_rss_mb": None, "peak_system_memory_percent": None},
        )
        if rss_mb is not None:
            old_rss = values["peak_rss_mb"]
            values["peak_rss_mb"] = (
                float(rss_mb) if old_rss is None else max(float(old_rss), float(rss_mb))
            )
        old_system = values["peak_system_memory_percent"]
        values["peak_system_memory_percent"] = (
            float(system_percent)
            if old_system is None
            else max(float(old_system), float(system_percent))
        )

    @staticmethod
    def _resource_payload(
        peaks: Mapping[str, Mapping[str, float | None]],
    ) -> dict[str, Any]:
        rss_values = [
            float(values["peak_rss_mb"])
            for values in peaks.values()
            if values.get("peak_rss_mb") is not None
        ]
        system_values = [
            float(values["peak_system_memory_percent"])
            for values in peaks.values()
            if values.get("peak_system_memory_percent") is not None
        ]
        return {
            "peak_rss_mb": round(max(rss_values), 3) if rss_values else None,
            "peak_system_memory_percent": (
                round(max(system_values), 3) if system_values else None
            ),
            "resource_stage_peaks": {
                str(stage): {
                    "peak_rss_mb": (
                        None
                        if values.get("peak_rss_mb") is None
                        else round(float(values["peak_rss_mb"]), 3)
                    ),
                    "peak_system_memory_percent": (
                        None
                        if values.get("peak_system_memory_percent") is None
                        else round(float(values["peak_system_memory_percent"]), 3)
                    ),
                }
                for stage, values in peaks.items()
            },
        }

    def _terminate_exact_worker_tree(self) -> None:
        """Terminate only the currently owned worker and its descendants."""
        pid = self._proc.pid
        if pid is None:
            return
        try:
            root = psutil.Process(int(pid))
            targets = [*root.children(recursive=True), root]
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return
        for process in targets:
            try:
                process.terminate()
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                pass
        _, alive = psutil.wait_procs(targets, timeout=3.0)
        for process in alive:
            try:
                process.kill()
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                pass
        if alive:
            psutil.wait_procs(alive, timeout=2.0)

    def _stop(self, *, force: bool) -> None:
        try:
            if force and self._proc.is_alive():
                self._terminate_exact_worker_tree()
            elif self._proc.is_alive():
                self._task_q.put(None)
            self._proc.join(5)
            if self._proc.is_alive():
                self._terminate_exact_worker_tree()
                self._proc.join(5)
        finally:
            for channel in (self._task_q, self._result_q):
                try:
                    channel.close()
                    channel.join_thread()
                except Exception:
                    pass

    def _restart(self) -> None:
        self._stop(force=True)
        self._start()

    def run(
        self,
        task: tuple[Any, ...],
        *,
        timeout: float,
        initial_stage: str,
    ) -> tuple[str, dict[str, Any]]:
        """Run one task and retain the last progress stage on hard timeout."""
        self._task_q.put(task)
        deadline = time.monotonic() + timeout
        stage = initial_stage
        resource_peaks: dict[str, dict[str, float | None]] = {}
        while True:
            rss_mb, system_percent = self._sample_process_tree(self._proc.pid)
            self._update_resource_peaks(resource_peaks, stage, rss_mb, system_percent)
            if (
                self._max_system_memory_percent is not None
                and system_percent > self._max_system_memory_percent
            ):
                resource_payload = self._resource_payload(resource_peaks)
                self._restart()
                return (
                    "error",
                    {
                        "stage": stage,
                        "error_code": "resource_guard",
                        "error_message": (
                            f"system memory {system_percent:.1f}% exceeded soft limit "
                            f"{self._max_system_memory_percent:.1f}%; terminated only the "
                            "current worker process tree"
                        ),
                        "resource_guard_limit_percent": self._max_system_memory_percent,
                        "resource_guard_observed_percent": float(system_percent),
                        **resource_payload,
                    },
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                resource_payload = self._resource_payload(resource_peaks)
                self._restart()
                return (
                    "timeout",
                    {
                        "stage": stage,
                        "error_code": "stage_timeout",
                        "error_message": f"{stage} exceeded {timeout:.3f} seconds",
                        **resource_payload,
                    },
                )
            try:
                status, payload = self._result_q.get(timeout=min(0.25, remaining))
            except queue.Empty:
                if not self._proc.is_alive():
                    exit_code = self._proc.exitcode
                    resource_payload = self._resource_payload(resource_peaks)
                    self._restart()
                    return (
                        "error",
                        {
                            "stage": stage,
                            "error_code": "worker_exit",
                            "error_message": f"spawned worker exited with code {exit_code}",
                            **resource_payload,
                        },
                    )
                continue
            if status == "progress":
                stage = str(payload["stage"])
                continue
            completed_status = str(status)
            completed_payload = dict(payload)
            completed_payload.update(self._resource_payload(resource_peaks))
            self._completed_tasks += 1
            if self._completed_tasks >= self._max_tasks:
                self._restart()
            return completed_status, completed_payload

    def close(self) -> None:
        self._stop(force=False)

    def __enter__(self) -> "StageWorker":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Fixed JSONL fact schema
# ---------------------------------------------------------------------------

RESOURCE_ROW_FIELDS = (
    "resource_monitor_backend",
    "resource_guard_limit_percent",
    "synth_peak_rss_mb",
    "synth_peak_system_memory_percent",
    "synth_resource_stage_peaks",
    "map_peak_rss_mb",
    "map_peak_system_memory_percent",
    "map_resource_stage_peaks",
    "total_peak_rss_mb",
    "total_peak_system_memory_percent",
)

ROW_FIELDS = (
    "schema_version",
    "run_id",
    "run_ts",
    "record_key",
    "synthesis_key",
    "status",
    "stage",
    "error_code",
    "error_message",
    "benchmark_suite",
    "benchmark_suite_id",
    "function_id",
    "family",
    "n_inputs",
    "truth_table_hex",
    "function_truth_hash",
    "method",
    "requested_method",
    "result_method",
    "selected_method",
    "synthesis_seed",
    "transpile_seed",
    "artifact_source",
    "artifact_consistent",
    "mapping_provenance_consistent",
    "result_correct",
    "engine_correct",
    "engine_states_evaluated",
    "model_file",
    "model_hash",
    "synthesis_config_hash",
    "synthesis_config",
    "compile_config_hash",
    "compile_config",
    "target_name",
    "target_id",
    "target_hash",
    "target_topology",
    "target_num_qubits",
    "target_basis_gates",
    "target_twoq_gates",
    "target_manifest",
    "synth_time_s",
    "reported_synth_time_s",
    "logical_verify_time_s",
    "logic_T",
    "logic_CNOT",
    "logic_depth",
    "logic_gates",
    "logic_explicit_ancilla",
    "logic_peak_ancilla",
    "result_terms",
    "engine_gates",
    "engine_qubits",
    "logical_qubits",
    "work_qubits",
    "physical_qubits",
    "active_physical_qubits",
    "compiler_ancillas",
    "transpiler_added_qubits",
    "mapped_gates",
    "mapped_depth",
    "native_oneq_count",
    "native_twoq_count",
    "native_twoq_depth",
    "mapped_highq_count",
    "native_gate_counts",
    "native_rz_count",
    "native_sx_count",
    "native_x_count",
    "native_cx_count",
    "native_cz_count",
    "native_ecr_count",
    "basis_reference_gates",
    "basis_reference_depth",
    "basis_reference_twoq_count",
    "routing_gate_delta",
    "routing_depth_delta",
    "routing_twoq_delta",
    "routing_twoq_overhead_ratio",
    "unsupported_instructions",
    "coupling_violations",
    "estimated_duration_s",
    "basis_reference_time_s",
    "compile_time_s",
    "map_time_s",
    "mapped_verify_time_s",
    "initial_layout",
    "final_layout",
    "mapped_verify_ok",
    "mapped_verification_complete",
    "mapped_verify_mode",
    "mapped_states_evaluated",
    "mapped_mismatches",
    "mapped_max_probability_error",
    "mapped_max_leakage",
    "mapped_max_phase_error",
    "mapped_probability_tolerance",
    "mapped_phase_tolerance",
    *RESOURCE_ROW_FIELDS,
)


def _blank_row() -> dict[str, Any]:
    return {field: None for field in ROW_FIELDS}


def _context_row(
    *,
    run_id: str,
    run_ts: str,
    function_id: str,
    family: str,
    bf: BooleanFunction,
    method: str,
    synthesis_seed: int,
    transpile_seed: int,
    model_path: str | None,
    model_hash: str | None,
    synthesis_config: SearchConfig,
    target_name: str,
    target_spec: TargetSpec,
    compile_config: CompileConfig,
    benchmark_suite: str,
    benchmark_suite_id: str,
    max_system_memory_percent: float | None = 70.0,
) -> dict[str, Any]:
    function_hash = _function_hash(bf)
    synthesis_manifest = _jsonable(asdict(synthesis_config))
    synthesis_config_hash = _canonical_hash(synthesis_manifest)
    compile_manifest = _jsonable(asdict(compile_config))
    synthesis_key = _synthesis_key(
        function_hash=function_hash,
        method=method,
        seed=synthesis_seed,
        synthesis_config_hash=synthesis_config_hash,
        model_hash=model_hash,
    )
    target_hash = target_spec.config_hash()
    compile_config_hash = compile_config.config_hash()
    row = _blank_row()
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "run_ts": run_ts,
            "record_key": _record_key(synthesis_key, target_hash, compile_config_hash),
            "synthesis_key": synthesis_key,
            "status": "pending",
            "stage": "pending",
            "benchmark_suite": benchmark_suite,
            "benchmark_suite_id": benchmark_suite_id,
            "function_id": function_id,
            "family": family,
            "n_inputs": int(bf.n),
            "truth_table_hex": _truth_table_hex(bf),
            "function_truth_hash": function_hash,
            "method": method,
            "requested_method": method,
            "synthesis_seed": int(synthesis_seed),
            "transpile_seed": int(transpile_seed),
            "artifact_source": "synthesize_artifact",
            "model_file": None if model_path is None else Path(model_path).name,
            "model_hash": model_hash,
            "synthesis_config_hash": synthesis_config_hash,
            "synthesis_config": synthesis_manifest,
            "compile_config_hash": compile_config_hash,
            "compile_config": compile_manifest,
            "target_name": target_name,
            "target_id": target_spec.target_id,
            "target_hash": target_hash,
            "target_topology": target_spec.topology,
            "target_num_qubits": int(target_spec.num_qubits),
            "target_basis_gates": list(target_spec.basis_gates),
            "target_twoq_gates": list(target_spec.twoq_gates),
            "target_manifest": target_spec.to_manifest(),
            "resource_monitor_backend": "psutil",
            "resource_guard_limit_percent": max_system_memory_percent,
        }
    )
    return row


def _apply_task_resources(
    row: dict[str, Any], task: str, payload: Mapping[str, Any]
) -> None:
    """Attach synthesis/mapping task telemetry and refresh row-wide peaks."""
    if task not in {"synth", "map"}:
        raise ValueError(f"unknown resource task: {task}")
    row[f"{task}_peak_rss_mb"] = payload.get("peak_rss_mb")
    row[f"{task}_peak_system_memory_percent"] = payload.get(
        "peak_system_memory_percent"
    )
    row[f"{task}_resource_stage_peaks"] = payload.get("resource_stage_peaks") or {}
    rss_values = [
        float(value)
        for value in (row.get("synth_peak_rss_mb"), row.get("map_peak_rss_mb"))
        if value is not None
    ]
    system_values = [
        float(value)
        for value in (
            row.get("synth_peak_system_memory_percent"),
            row.get("map_peak_system_memory_percent"),
        )
        if value is not None
    ]
    row["total_peak_rss_mb"] = max(rss_values) if rss_values else None
    row["total_peak_system_memory_percent"] = (
        max(system_values) if system_values else None
    )


def _apply_synthesis(row: dict[str, Any], payload: Mapping[str, Any]) -> None:
    cost = payload["cost"]
    row.update(
        {
            "result_method": payload["result_method"],
            "selected_method": payload["selected_method"],
            "artifact_consistent": bool(
                payload["result_gates"] == len(payload["gates"])
                and payload["result_n_qubits"] == payload["n_qubits"]
            ),
            "result_correct": bool(payload["result_correct"]),
            "engine_correct": bool(payload["engine_correct"]),
            "engine_states_evaluated": int(payload["engine_states_evaluated"]),
            "synth_time_s": float(payload["synth_time_s"]),
            "reported_synth_time_s": float(payload["reported_synth_time_s"]),
            "logical_verify_time_s": float(payload["logical_verify_time_s"]),
            "logic_T": int(cost["T"]),
            "logic_CNOT": int(cost["CNOT"]),
            "logic_depth": int(cost["depth"]),
            "logic_gates": int(cost["gates"]),
            "logic_explicit_ancilla": int(cost["explicit_ancilla"]),
            "logic_peak_ancilla": int(cost["peak_ancilla"]),
            "result_terms": int(payload["result_terms"]),
            "engine_gates": int(len(payload["gates"])),
            "engine_qubits": int(payload["n_qubits"]),
        }
    )


def _apply_mapping(row: dict[str, Any], payload: Mapping[str, Any]) -> None:
    metrics = payload["metrics"]
    counts = {str(name): int(count) for name, count in metrics["gate_counts"].items()}
    verification = payload["verification"]
    row.update(
        {
            "mapping_provenance_consistent": bool(
                metrics["target_id"] == row["target_id"]
                and metrics["target_hash"] == row["target_hash"]
                and metrics["compile_config_hash"] == row["compile_config_hash"]
            ),
            "logical_qubits": int(metrics["logical_qubits"]),
            "work_qubits": int(metrics["work_qubits"]),
            "physical_qubits": int(metrics["physical_qubits"]),
            "active_physical_qubits": int(metrics["active_physical_qubits"]),
            "compiler_ancillas": int(metrics["compiler_ancillas"]),
            "transpiler_added_qubits": int(metrics["transpiler_added_qubits"]),
            "mapped_gates": int(metrics["gates"]),
            "mapped_depth": int(metrics["depth"]),
            "native_oneq_count": int(metrics["oneq_count"]),
            "native_twoq_count": int(metrics["twoq_count"]),
            "native_twoq_depth": int(metrics["twoq_depth"]),
            "mapped_highq_count": int(metrics["highq_count"]),
            "native_gate_counts": counts,
            "basis_reference_gates": int(metrics["basis_reference_gates"]),
            "basis_reference_depth": int(metrics["basis_reference_depth"]),
            "basis_reference_twoq_count": int(metrics["basis_reference_twoq_count"]),
            "routing_gate_delta": int(metrics["routing_gate_delta"]),
            "routing_depth_delta": int(metrics["routing_depth_delta"]),
            "routing_twoq_delta": int(metrics["routing_twoq_delta"]),
            "routing_twoq_overhead_ratio": metrics["routing_twoq_overhead_ratio"],
            "unsupported_instructions": int(metrics["unsupported_instructions"]),
            "coupling_violations": int(metrics["coupling_violations"]),
            "estimated_duration_s": metrics["estimated_duration_s"],
            "basis_reference_time_s": float(metrics["basis_reference_time_s"]),
            "compile_time_s": float(metrics["compile_time_s"]),
            "map_time_s": float(payload["map_time_s"]),
            "mapped_verify_time_s": float(payload["mapped_verify_time_s"]),
            "initial_layout": [int(q) for q in payload["initial_layout"]],
            "final_layout": [int(q) for q in payload["final_layout"]],
            "mapped_verify_ok": bool(verification["ok"]),
            "mapped_verification_complete": bool(
                int(verification["evaluated"]) == (1 << (int(row["n_inputs"]) + 1))
            ),
            "mapped_verify_mode": verification["mode"],
            "mapped_states_evaluated": int(verification["evaluated"]),
            "mapped_mismatches": int(verification["mismatches"]),
            "mapped_max_probability_error": float(verification["max_probability_error"]),
            "mapped_max_leakage": float(verification["max_leakage"]),
            "mapped_max_phase_error": float(verification["max_phase_error"]),
            "mapped_probability_tolerance": float(verification["tolerance"]),
            "mapped_phase_tolerance": float(verification["phase_tolerance"]),
        }
    )
    for gate_name in KNOWN_NATIVE_GATES:
        row[f"native_{gate_name}_count"] = int(counts.get(gate_name, 0))


def _apply_failure(row: dict[str, Any], status: str, payload: Mapping[str, Any]) -> None:
    row.update(
        {
            "status": status,
            "stage": str(payload.get("stage", "unknown")),
            "error_code": str(payload.get("error_code", "unknown_error")),
            "error_message": str(payload.get("error_message", "")),
        }
    )


# ---------------------------------------------------------------------------
# Synthesis-once, map-many experiment iterator
# ---------------------------------------------------------------------------

def iter_hardware_validation_rows(
    *,
    functions: Sequence[tuple[str, str, BooleanFunction]],
    methods: Sequence[str],
    synthesis_seeds: Sequence[int],
    targets: Mapping[str, TargetSpec],
    transpile_seeds: Sequence[int],
    synthesis_config: SearchConfig,
    timeout_s: float,
    model_path: str | None,
    optimization_level: int = 2,
    layout_method: str | None = "sabre",
    routing_method: str | None = "sabre",
    hls_ancilla_budget: int = 0,
    verification_batch_size: int = 4,
    aer_max_parallel_threads: int = 4,
    aer_max_parallel_experiments: int = 1,
    worker_max_tasks: int = 8,
    max_system_memory_percent: float | None = 70.0,
    benchmark_suite: str = "custom",
    benchmark_suite_id: str | None = None,
    run_id: str | None = None,
    run_ts: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield one fixed-schema row per requested mapping configuration."""
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    if not functions or not methods or not synthesis_seeds or not targets or not transpile_seeds:
        raise ValueError("functions, methods, seeds, targets and transpile seeds must be non-empty")

    run_ts = run_ts or datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = run_id or f"{run_ts}-{uuid.uuid4().hex[:8]}"
    benchmark_suite_id = benchmark_suite_id or _suite_identity(
        functions, label=benchmark_suite
    )
    model_hash = _file_sha256(model_path)

    with StageWorker(
        max_tasks=worker_max_tasks,
        max_system_memory_percent=max_system_memory_percent,
    ) as worker:
        for function_id, family, bf in functions:
            for method in methods:
                use_model = model_path if method in NEURAL_METHODS else None
                use_model_hash = model_hash if use_model is not None else None
                for synthesis_seed in synthesis_seeds:
                    synth_status, synth_payload = worker.run(
                        (
                            "synth",
                            method,
                            bf,
                            synthesis_config,
                            int(synthesis_seed),
                            use_model,
                        ),
                        timeout=timeout_s,
                        initial_stage="synthesis_spawn",
                    )

                    # The synthesis result is intentionally retained and reused
                    # across every target/transpiler seed below.
                    for target_name, target_spec in targets.items():
                        for transpile_seed in transpile_seeds:
                            compile_config = CompileConfig(
                                optimization_level=optimization_level,
                                layout_method=layout_method,
                                routing_method=routing_method,
                                seed_transpiler=int(transpile_seed),
                                hls_ancilla_budget=hls_ancilla_budget,
                                verification_batch_size=verification_batch_size,
                                aer_max_parallel_threads=aer_max_parallel_threads,
                                aer_max_parallel_experiments=aer_max_parallel_experiments,
                            )
                            row = _context_row(
                                run_id=run_id,
                                run_ts=run_ts,
                                function_id=function_id,
                                family=family,
                                bf=bf,
                                method=method,
                                synthesis_seed=int(synthesis_seed),
                                transpile_seed=int(transpile_seed),
                                model_path=use_model,
                                model_hash=use_model_hash,
                                synthesis_config=synthesis_config,
                                target_name=target_name,
                                target_spec=target_spec,
                                compile_config=compile_config,
                                benchmark_suite=benchmark_suite,
                                benchmark_suite_id=benchmark_suite_id,
                                max_system_memory_percent=max_system_memory_percent,
                            )
                            _apply_task_resources(row, "synth", synth_payload)
                            if synth_status != "ok":
                                _apply_failure(row, synth_status, synth_payload)
                                yield row
                                continue

                            _apply_synthesis(row, synth_payload)
                            map_status, map_payload = worker.run(
                                (
                                    "map",
                                    synth_payload["gates"],
                                    synth_payload["n_qubits"],
                                    bf,
                                    target_spec,
                                    compile_config,
                                ),
                                timeout=timeout_s,
                                initial_stage="mapping_spawn",
                            )
                            _apply_task_resources(row, "map", map_payload)
                            if map_status in {"ok", "mismatch"}:
                                _apply_mapping(row, map_payload)
                            if map_status == "ok":
                                all_checks = bool(
                                    row["artifact_consistent"]
                                    and row["mapping_provenance_consistent"]
                                    and row["result_correct"]
                                    and row["engine_correct"]
                                    and row["mapped_verify_ok"]
                                    and row["mapped_verification_complete"]
                                    and row["unsupported_instructions"] == 0
                                    and row["coupling_violations"] == 0
                                )
                                if all_checks:
                                    row.update(
                                        {
                                            "status": "ok",
                                            "stage": "complete",
                                            "error_code": None,
                                            "error_message": None,
                                        }
                                    )
                                else:
                                    _apply_failure(
                                        row,
                                        "mismatch",
                                        {
                                            "stage": "validation",
                                            "error_code": "validation_invariant_failed",
                                            "error_message": (
                                                "one or more artifact, logical, mapped, or target "
                                                "validation invariants failed"
                                            ),
                                        },
                                    )
                            elif map_status == "mismatch":
                                _apply_failure(row, "mismatch", map_payload)
                            else:
                                _apply_failure(row, map_status, map_payload)
                            yield row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_csv(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(items))


def _parse_int_csv(value: str, *, option: str) -> list[int]:
    raw = _parse_csv(value)
    if not raw:
        raise ValueError(f"{option} must contain at least one integer")
    try:
        values = [int(item) for item in raw]
    except ValueError as exc:
        raise ValueError(f"{option} must be a comma-separated integer list") from exc
    if any(value < 0 for value in values):
        raise ValueError(f"{option} values must be non-negative")
    return values


def _select_named(
    requested: str,
    available: Mapping[str, _NamedValue],
    *,
    option: str,
) -> dict[str, _NamedValue]:
    names = list(available) if not requested else _parse_csv(requested)
    unknown = [name for name in names if name not in available]
    if unknown:
        raise ValueError(f"unknown {option}: {', '.join(unknown)}")
    return {name: available[name] for name in names}


def _select_methods(requested: str) -> list[str]:
    methods = list(METHODS) if not requested else _parse_csv(requested)
    unknown = [method for method in methods if method not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods: {', '.join(unknown)}")
    return methods


def _select_functions(
    requested: str, *, suite: str = "smoke"
) -> list[tuple[str, str, BooleanFunction]]:
    functions = benchmark_functions(suite)
    by_name = {function_id: item for item in functions for function_id in (item[0],)}
    names = list(by_name) if not requested else _parse_csv(requested)
    unknown = [name for name in names if name not in by_name]
    if unknown:
        raise ValueError(f"unknown functions: {', '.join(unknown)}")
    return [by_name[name] for name in names]


def _none_if_literal(value: str) -> str | None:
    return None if value.lower() in {"none", "null", "off"} else value


def _parse_memory_percent(value: str) -> float | None:
    literal = str(value).strip().lower()
    if literal in {"off", "none", "null"}:
        return None
    try:
        percent = float(literal)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "memory limit must be a percentage in (0, 100] or 'off'"
        ) from exc
    if not 0.0 < percent <= 100.0:
        raise argparse.ArgumentTypeError(
            "memory limit must be a percentage in (0, 100] or 'off'"
        )
    return percent


def _resolve_model_argument(value: str | Path) -> str | None:
    """Resolve a learned checkpoint or an explicit non-learned prior control."""
    literal = _none_if_literal(str(value))
    if literal is None:
        return None
    if literal == "uniform-prior" or literal.startswith("random-prior:"):
        if literal.startswith("random-prior:"):
            try:
                int(literal.split(":", 1)[1])
            except ValueError as exc:
                raise ValueError("random-prior must be random-prior:<integer-seed>") from exc
        return literal
    model_path = Path(literal).resolve()
    if not model_path.is_file():
        raise ValueError(f"neural model does not exist: {model_path}")
    return str(model_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=("smoke", "final"),
        default="smoke",
        help=(
            "smoke is the compact integration set; final is the frozen "
            f"{COMPETITION_SUITE_VERSION} 30-case competition suite"
        ),
    )
    parser.add_argument("--functions", default="", help="comma-separated function ids")
    parser.add_argument("--methods", default="", help="comma-separated synthesis methods")
    parser.add_argument("--seeds", default="7", help="comma-separated synthesis seeds")
    parser.add_argument(
        "--targets",
        default=",".join(TARGET_NAMES),
        help="comma-separated cx_full,cx_line,cz_grid,ecr_heavy_hex",
    )
    parser.add_argument(
        "--transpile-seeds",
        default="7",
        help="comma-separated Qiskit transpiler seeds",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="seconds per stage")
    parser.add_argument(
        "--model-path",
        default=str(DEFAULT_MODEL),
        help=(
            "learned checkpoint path, off/none for heuristic-only, "
            "uniform-prior, or random-prior:<seed>"
        ),
    )
    parser.add_argument("--cx-qubits", type=int, default=19)
    parser.add_argument("--grid-rows", type=int, default=4)
    parser.add_argument("--grid-columns", type=int, default=5)
    parser.add_argument("--heavy-hex-distance", type=int, default=3)
    parser.add_argument("--optimization-level", type=int, choices=(0, 1, 2, 3), default=2)
    parser.add_argument("--layout-method", default="sabre")
    parser.add_argument("--routing-method", default="sabre")
    parser.add_argument("--hls-ancilla-budget", type=int, default=0)
    parser.add_argument("--verification-batch-size", type=int, default=4)
    parser.add_argument("--aer-max-parallel-threads", type=int, default=4)
    parser.add_argument("--aer-max-parallel-experiments", type=int, default=1)
    parser.add_argument("--worker-max-tasks", type=int, default=8)
    parser.add_argument(
        "--max-system-memory-percent",
        type=_parse_memory_percent,
        default=70.0,
        metavar="PERCENT|off",
        help=(
            "soft system-memory guard (default: 70); exceeding it terminates "
            "only the current worker process tree; use off to disable"
        ),
    )
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output-jsonl", type=Path, help="new JSONL output path")
    destination.add_argument("--dry-run", action="store_true", help="print the planned grid only")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing --output-jsonl path",
    )
    return parser


def _dry_run_manifest(
    *,
    functions: Sequence[tuple[str, str, BooleanFunction]],
    methods: Sequence[str],
    synthesis_seeds: Sequence[int],
    targets: Mapping[str, TargetSpec],
    transpile_seeds: Sequence[int],
    config: SearchConfig,
    timeout_s: float,
    optimization_level: int,
    layout_method: str | None,
    routing_method: str | None,
    hls_ancilla_budget: int,
    verification_batch_size: int,
    aer_max_parallel_threads: int,
    aer_max_parallel_experiments: int,
    worker_max_tasks: int,
    max_system_memory_percent: float | None,
    benchmark_suite: str,
    benchmark_suite_id: str,
) -> dict[str, Any]:
    compile_configs = {
        str(seed): {
            "manifest": _jsonable(
                asdict(
                    CompileConfig(
                        optimization_level=optimization_level,
                        layout_method=layout_method,
                        routing_method=routing_method,
                        seed_transpiler=seed,
                        hls_ancilla_budget=hls_ancilla_budget,
                        verification_batch_size=verification_batch_size,
                        aer_max_parallel_threads=aer_max_parallel_threads,
                        aer_max_parallel_experiments=aer_max_parallel_experiments,
                    )
                )
            ),
            "hash": CompileConfig(
                optimization_level=optimization_level,
                layout_method=layout_method,
                routing_method=routing_method,
                seed_transpiler=seed,
                hls_ancilla_budget=hls_ancilla_budget,
                verification_batch_size=verification_batch_size,
                aer_max_parallel_threads=aer_max_parallel_threads,
                aer_max_parallel_experiments=aer_max_parallel_experiments,
            ).config_hash(),
        }
        for seed in transpile_seeds
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run": True,
        "benchmark_suite": benchmark_suite,
        "benchmark_suite_id": benchmark_suite_id,
        "functions": [function_id for function_id, _, _ in functions],
        "methods": list(methods),
        "synthesis_seeds": list(synthesis_seeds),
        "targets": {
            name: {"manifest": spec.to_manifest(), "hash": spec.config_hash()}
            for name, spec in targets.items()
        },
        "transpile_seeds": list(transpile_seeds),
        "synthesis_config": _jsonable(asdict(config)),
        "synthesis_config_hash": _canonical_hash(asdict(config)),
        "compile_configs": compile_configs,
        "timeout_s": timeout_s,
        "worker_max_tasks": worker_max_tasks,
        "max_system_memory_percent": max_system_memory_percent,
        "synthesis_tasks": len(functions) * len(methods) * len(synthesis_seeds),
        "mapping_rows": (
            len(functions)
            * len(methods)
            * len(synthesis_seeds)
            * len(targets)
            * len(transpile_seeds)
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        synthesis_seeds = _parse_int_csv(args.seeds, option="--seeds")
        transpile_seeds = _parse_int_csv(args.transpile_seeds, option="--transpile-seeds")
        methods = _select_methods(args.methods)
        functions = _select_functions(args.functions, suite=args.suite)
        catalog = target_catalog(
            cx_qubits=args.cx_qubits,
            grid_rows=args.grid_rows,
            grid_columns=args.grid_columns,
            heavy_hex_distance=args.heavy_hex_distance,
        )
        targets = _select_named(args.targets, catalog, option="targets")
        if args.timeout <= 0:
            raise ValueError("--timeout must be positive")
        if args.hls_ancilla_budget < 0:
            raise ValueError("--hls-ancilla-budget must be non-negative")
        if args.verification_batch_size < 1:
            raise ValueError("--verification-batch-size must be positive")
        if args.aer_max_parallel_threads < 1:
            raise ValueError("--aer-max-parallel-threads must be positive")
        if args.aer_max_parallel_experiments < 1:
            raise ValueError("--aer-max-parallel-experiments must be positive")
        if args.worker_max_tasks < 1:
            raise ValueError("--worker-max-tasks must be positive")
    except ValueError as exc:
        parser.error(str(exc))

    config = base_config()
    benchmark_suite = (
        COMPETITION_SUITE_VERSION if args.suite == "final" else "runner-smoke-v2"
    )
    benchmark_suite_id = (
        str(competition_suite_manifest()["suite_id"])
        if args.suite == "final"
        else _suite_identity(functions, label=benchmark_suite)
    )
    layout_method = _none_if_literal(args.layout_method)
    routing_method = _none_if_literal(args.routing_method)
    selected_model: str | None = None
    if any(method in NEURAL_METHODS for method in methods):
        try:
            selected_model = _resolve_model_argument(args.model_path)
        except ValueError as exc:
            parser.error(str(exc))

    if args.dry_run:
        manifest = _dry_run_manifest(
            functions=functions,
            methods=methods,
            synthesis_seeds=synthesis_seeds,
            targets=targets,
            transpile_seeds=transpile_seeds,
            config=config,
            timeout_s=args.timeout,
            optimization_level=args.optimization_level,
            layout_method=layout_method,
            routing_method=routing_method,
            hls_ancilla_budget=args.hls_ancilla_budget,
            verification_batch_size=args.verification_batch_size,
            aer_max_parallel_threads=args.aer_max_parallel_threads,
            aer_max_parallel_experiments=args.aer_max_parallel_experiments,
            worker_max_tasks=args.worker_max_tasks,
            max_system_memory_percent=args.max_system_memory_percent,
            benchmark_suite=benchmark_suite,
            benchmark_suite_id=benchmark_suite_id,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
        return 0

    output_path = args.output_jsonl.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = f"{run_ts}-{uuid.uuid4().hex[:8]}"
    started = time.perf_counter()
    counts = {"ok": 0, "mismatch": 0, "timeout": 0, "error": 0}
    try:
        with output_path.open(mode, encoding="utf-8", newline="\n") as stream:
            for row in iter_hardware_validation_rows(
                functions=functions,
                methods=methods,
                synthesis_seeds=synthesis_seeds,
                targets=targets,
                transpile_seeds=transpile_seeds,
                synthesis_config=config,
                timeout_s=args.timeout,
                model_path=selected_model,
                optimization_level=args.optimization_level,
                layout_method=layout_method,
                routing_method=routing_method,
                hls_ancilla_budget=args.hls_ancilla_budget,
                verification_batch_size=args.verification_batch_size,
                aer_max_parallel_threads=args.aer_max_parallel_threads,
                aer_max_parallel_experiments=args.aer_max_parallel_experiments,
                worker_max_tasks=args.worker_max_tasks,
                max_system_memory_percent=args.max_system_memory_percent,
                benchmark_suite=benchmark_suite,
                benchmark_suite_id=benchmark_suite_id,
                run_id=run_id,
                run_ts=run_ts,
            ):
                stream.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
                )
                stream.flush()
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                print(
                    f"[{row['function_id']}/{row['requested_method']}/s{row['synthesis_seed']} "
                    f"{row['target_name']}/t{row['transpile_seed']}] {row['status']}",
                    file=sys.stderr,
                    flush=True,
                )
    except FileExistsError:
        parser.error(f"output exists (pass --overwrite to replace it): {output_path}")

    elapsed = time.perf_counter() - started
    print(
        f"wrote {sum(counts.values())} rows to {output_path} in {elapsed:.1f}s; "
        + ", ".join(f"{key}={value}" for key, value in counts.items()),
        file=sys.stderr,
    )
    return 0 if all(counts.get(status, 0) == 0 for status in ("mismatch", "timeout", "error")) else 2


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
