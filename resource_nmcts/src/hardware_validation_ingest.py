"""Validated, append-only ingestion of hardware-validation JSONL facts.

The hardware runner is intentionally independent from DuckDB.  This module is
the audited bridge: it validates every content hash, collapses the runner's
synthesis-once/map-many rows to one synthesis attempt, and records all
mutations through :class:`src.experiment_db.ExperimentDB`.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

from scripts.run_hardware_validation import (
    LEGACY_SCHEMA_VERSION,
    RESOURCE_ROW_FIELDS,
    ROW_FIELDS,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    _canonical_hash,
    _function_hash,
    _record_key,
    _synthesis_key,
)
from src.experiment_db import ExperimentDB, canonical_json
from src.sshr_lib.bool_func import BooleanFunction


DEFAULT_EXPERIMENT_SLUG = "xa202609-hardware-validation-v1"
DEFAULT_EXPERIMENT_TITLE = "XA-202609 Boolean Oracle hardware validation"


class HardwareValidationIngestError(RuntimeError):
    """Raised when a source fact stream violates the ingestion contract."""


@dataclass(frozen=True)
class IngestSummary:
    experiment_id: str
    batch_id: str
    source_sha256: str
    source_rows: int
    synthesis_attempts: int
    mapping_attempts: int
    logical_verifications: int
    mapping_verifications: int
    status_counts: Mapping[str, int]
    already_ingested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SHA_FIELDS = (
    "record_key",
    "synthesis_key",
    "function_truth_hash",
    "synthesis_config_hash",
    "compile_config_hash",
    "target_hash",
    "benchmark_suite_id",
)

_SYNTHESIS_INVARIANT_FIELDS = (
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
    "artifact_source",
    "artifact_consistent",
    "result_correct",
    "engine_correct",
    "engine_states_evaluated",
    "model_file",
    "model_hash",
    "synthesis_config_hash",
    "synthesis_config",
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
    "resource_monitor_backend",
    "resource_guard_limit_percent",
    "synth_peak_rss_mb",
    "synth_peak_system_memory_percent",
    "synth_resource_stage_peaks",
)


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, field: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or len(value) != 64:
        raise HardwareValidationIngestError(f"{field} is not a 64-character SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise HardwareValidationIngestError(f"{field} is not hexadecimal") from exc


def _validate_row(row: Mapping[str, Any], line_no: int) -> None:
    version = row.get("schema_version")
    expected = set(ROW_FIELDS)
    actual = set(row)
    legacy_expected = expected - set(RESOURCE_ROW_FIELDS)
    valid_shape = actual == expected or (
        version == LEGACY_SCHEMA_VERSION and actual == legacy_expected
    )
    if not valid_shape:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise HardwareValidationIngestError(
            f"line {line_no}: fixed schema mismatch; missing={missing}, extra={extra}"
        )
    if version not in {SOURCE_SCHEMA_VERSION, LEGACY_SCHEMA_VERSION}:
        raise HardwareValidationIngestError(
            f"line {line_no}: expected {SOURCE_SCHEMA_VERSION} or "
            f"{LEGACY_SCHEMA_VERSION}, got {version!r}"
        )
    # canonical_json rejects NaN/Inf and unsupported values before anything is
    # committed to a JSON column.
    canonical_json(row)
    if actual == expected:
        if not isinstance(row["resource_monitor_backend"], str) or not row[
            "resource_monitor_backend"
        ]:
            raise HardwareValidationIngestError(
                f"line {line_no}: invalid resource monitor backend"
            )
        for field in (
            "synth_peak_rss_mb",
            "map_peak_rss_mb",
            "total_peak_rss_mb",
        ):
            value = row[field]
            if value is not None and (
                not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise HardwareValidationIngestError(
                    f"line {line_no}: invalid non-negative resource field {field}"
                )
        for field in (
            "resource_guard_limit_percent",
            "synth_peak_system_memory_percent",
            "map_peak_system_memory_percent",
            "total_peak_system_memory_percent",
        ):
            value = row[field]
            lower_bound = 0.0 if field != "resource_guard_limit_percent" else 1e-12
            if value is not None and (
                not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not lower_bound <= float(value) <= 100.0
            ):
                raise HardwareValidationIngestError(
                    f"line {line_no}: invalid percentage resource field {field}"
                )
        for field in ("synth_resource_stage_peaks", "map_resource_stage_peaks"):
            value = row[field]
            if value is not None and not isinstance(value, Mapping):
                raise HardwareValidationIngestError(
                    f"line {line_no}: {field} must be an object or null"
                )
        # A worker that times out during synthesis never enters the mapping
        # stage, so the runner deliberately emits null mapping telemetry.  If
        # a stage reports scalar peaks (or the row is a complete success), its
        # detailed stage object must still be present.
        if (
            row["synth_resource_stage_peaks"] is None
            and (
                row["synth_peak_rss_mb"] is not None
                or row["synth_peak_system_memory_percent"] is not None
            )
        ):
            raise HardwareValidationIngestError(
                f"line {line_no}: synthesis peaks require synth_resource_stage_peaks"
            )
        if (
            row["map_resource_stage_peaks"] is None
            and (
                row["map_peak_rss_mb"] is not None
                or row["map_peak_system_memory_percent"] is not None
            )
        ):
            raise HardwareValidationIngestError(
                f"line {line_no}: mapping peaks require map_resource_stage_peaks"
            )
        if row["status"] == "ok" and any(
            row[field] is None
            for field in ("synth_resource_stage_peaks", "map_resource_stage_peaks")
        ):
            raise HardwareValidationIngestError(
                f"line {line_no}: successful v3 rows require both resource-stage objects"
            )
        rss_parts = [row["synth_peak_rss_mb"], row["map_peak_rss_mb"]]
        if row["total_peak_rss_mb"] is not None and any(
            value is not None and float(value) > float(row["total_peak_rss_mb"])
            for value in rss_parts
        ):
            raise HardwareValidationIngestError(
                f"line {line_no}: total_peak_rss_mb is smaller than a stage peak"
            )
        system_parts = [
            row["synth_peak_system_memory_percent"],
            row["map_peak_system_memory_percent"],
        ]
        if row["total_peak_system_memory_percent"] is not None and any(
            value is not None
            and float(value) > float(row["total_peak_system_memory_percent"])
            for value in system_parts
        ):
            raise HardwareValidationIngestError(
                f"line {line_no}: total system-memory peak is smaller than a stage peak"
            )
    for field in _SHA_FIELDS:
        _require_sha256(row[field], f"line {line_no} {field}")
    _require_sha256(row["model_hash"], f"line {line_no} model_hash", optional=True)

    try:
        bf = BooleanFunction(int(row["n_inputs"]), int(str(row["truth_table_hex"]), 16))
    except (TypeError, ValueError) as exc:
        raise HardwareValidationIngestError(
            f"line {line_no}: invalid Boolean-function definition"
        ) from exc
    if _function_hash(bf) != row["function_truth_hash"]:
        raise HardwareValidationIngestError(f"line {line_no}: function hash mismatch")
    if _canonical_hash(row["synthesis_config"]) != row["synthesis_config_hash"]:
        raise HardwareValidationIngestError(f"line {line_no}: synthesis config hash mismatch")
    if _canonical_hash(row["compile_config"]) != row["compile_config_hash"]:
        raise HardwareValidationIngestError(f"line {line_no}: compile config hash mismatch")
    if _canonical_hash(row["target_manifest"]) != row["target_hash"]:
        raise HardwareValidationIngestError(f"line {line_no}: target manifest hash mismatch")
    expected_synthesis_key = _synthesis_key(
        function_hash=row["function_truth_hash"],
        method=row["requested_method"],
        seed=int(row["synthesis_seed"]),
        synthesis_config_hash=row["synthesis_config_hash"],
        model_hash=row["model_hash"],
    )
    if expected_synthesis_key != row["synthesis_key"]:
        raise HardwareValidationIngestError(f"line {line_no}: synthesis key mismatch")
    if _record_key(
        row["synthesis_key"], row["target_hash"], row["compile_config_hash"]
    ) != row["record_key"]:
        raise HardwareValidationIngestError(f"line {line_no}: record key mismatch")
    if row["target_manifest"].get("target_id") != row["target_id"]:
        raise HardwareValidationIngestError(f"line {line_no}: target id mismatch")
    if int(row["target_manifest"].get("num_qubits", -1)) != int(row["target_num_qubits"]):
        raise HardwareValidationIngestError(f"line {line_no}: target width mismatch")
    if int(row["compile_config"].get("seed_transpiler", -1)) != int(
        row["transpile_seed"]
    ):
        raise HardwareValidationIngestError(f"line {line_no}: transpiler seed mismatch")


def load_jsonl(path: str | pathlib.Path) -> tuple[list[dict[str, Any]], str]:
    """Load and fully validate one immutable JSONL source."""
    source = pathlib.Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    rows: list[dict[str, Any]] = []
    for line_no, text in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HardwareValidationIngestError(f"line {line_no}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise HardwareValidationIngestError(f"line {line_no}: row must be a JSON object")
        _validate_row(row, line_no)
        if row["schema_version"] == SOURCE_SCHEMA_VERSION:
            # Normalise a stage that was never entered to an empty JSON object
            # for the typed database layer while retaining the immutable
            # source bytes and SHA-256 as provenance.
            for field in ("synth_resource_stage_peaks", "map_resource_stage_peaks"):
                if row[field] is None:
                    row[field] = {}
        if row["schema_version"] == LEGACY_SCHEMA_VERSION:
            legacy_defaults = {
                "resource_monitor_backend": "unavailable-legacy",
                "resource_guard_limit_percent": None,
                "synth_peak_rss_mb": None,
                "synth_peak_system_memory_percent": None,
                "synth_resource_stage_peaks": {},
                "map_peak_rss_mb": None,
                "map_peak_system_memory_percent": None,
                "map_resource_stage_peaks": {},
                "total_peak_rss_mb": None,
                "total_peak_system_memory_percent": None,
            }
            for field, default in legacy_defaults.items():
                row.setdefault(field, default)
        rows.append(row)
    if not rows:
        raise HardwareValidationIngestError("JSONL source contains no rows")

    record_keys = [str(row["record_key"]) for row in rows]
    duplicates = [key for key, count in Counter(record_keys).items() if count > 1]
    if duplicates:
        raise HardwareValidationIngestError(
            f"duplicate record_key values in source: {duplicates[:3]}"
        )
    for field in (
        "schema_version",
        "run_id",
        "run_ts",
        "benchmark_suite",
        "benchmark_suite_id",
    ):
        values = {canonical_json(row[field]) for row in rows}
        if len(values) != 1:
            raise HardwareValidationIngestError(f"source mixes multiple {field} values")
    return rows, _sha256_file(source)


def _attempt_status(source_status: str) -> str:
    if source_status == "timeout":
        return "timeout"
    if source_status == "cancelled":
        return "cancelled"
    return "error"


def _has_logical_result(row: Mapping[str, Any]) -> bool:
    fields = ("logic_T", "logic_CNOT", "logic_depth", "logic_gates", "engine_qubits")
    present = [row[field] is not None for field in fields]
    if any(present) and not all(present):
        raise HardwareValidationIngestError("partial logical metrics in source row")
    return all(present)


def _method_identity(row: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    requested = str(row["requested_method"])
    model_file = row["model_file"]
    model_hash = row["model_hash"]
    if model_file is None:
        prior = "heuristic-only"
    elif model_file == "uniform-prior":
        prior = "uniform-prior"
    elif str(model_file).startswith("random-prior:"):
        prior = str(model_file)
    elif requested == "resource_nmcts":
        # The portfolio may never call, or may reject, its optional neural
        # candidate.  A configured checkpoint is therefore not evidence that
        # the emitted circuit was learned-policy selected.
        prior = "model-configured"
    else:
        prior = "learned"
    if requested in {"neural_mcts", "resource_nmcts"}:
        suffix = (
            prior
            if prior not in {"learned", "model-configured"}
            else f"{prior}:{str(model_hash)[:12]}"
        )
        display = f"{requested}[{suffix}]"
    else:
        display = requested
    spec = {
        "requested_method": requested,
        "prior_variant": prior,
        "model_role": (
            "optional_candidate_prior"
            if requested == "resource_nmcts" and model_file is not None
            else "active_action_prior"
            if requested == "neural_mcts" and model_file is not None
            else "none_or_control"
        ),
        "synthesis_config": row["synthesis_config"],
        "synthesis_config_hash": row["synthesis_config_hash"],
    }
    return display, spec


def _transpile_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return only circuit-affecting mapping semantics.

    Aer batching, thread counts and resource-monitor settings affect how the
    already-mapped circuit is verified, not which circuit Qiskit emits.  They
    remain in the immutable source row attached to each mapping attempt, but
    must not fragment strict target/transpile pairing across runner schemas.
    """

    config = row["compile_config"]
    mapping_config = {
        "seed_transpiler": int(row["transpile_seed"]),
        "optimization_level": int(config["optimization_level"]),
        "layout_method": config.get("layout_method"),
        "routing_method": config.get("routing_method"),
        "hls_ancilla_budget": int(config.get("hls_ancilla_budget", 0)),
        "mcx_methods": list(config.get("mcx_methods", [])),
    }
    return {
        "mapping_config_hash": _canonical_hash(mapping_config),
        "mapping_config": mapping_config,
        "verification_runtime_fields_excluded": True,
    }


def _logical_result_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_run_id": row["run_id"],
        "source_synthesis_key": row["synthesis_key"],
        "source_schema_version": row["schema_version"],
        "artifact_source": row["artifact_source"],
        "requested_method": row["requested_method"],
        "result_method": row["result_method"],
        "selected_method": row["selected_method"],
        "artifact_consistent": row["artifact_consistent"],
        "result_correct": row["result_correct"],
        "engine_correct": row["engine_correct"],
        "engine_states_evaluated": row["engine_states_evaluated"],
        "reported_synth_time_s": row["reported_synth_time_s"],
        "logical_verify_time_s": row["logical_verify_time_s"],
        "result_terms": row["result_terms"],
        "engine_gates": row["engine_gates"],
        "resource_monitor_backend": row["resource_monitor_backend"],
        "resource_guard_limit_percent": row["resource_guard_limit_percent"],
        "peak_rss_mb": row["synth_peak_rss_mb"],
        "peak_system_memory_percent": row["synth_peak_system_memory_percent"],
        "resource_stage_peaks": row["synth_resource_stage_peaks"],
    }


def _logical_metrics(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "t_count": row["logic_T"],
        "cnot_count": row["logic_CNOT"],
        "depth": row["logic_depth"],
        "gate_count": row["logic_gates"],
        "ancilla_count": row["logic_peak_ancilla"],
        "n_qubits": row["engine_qubits"],
        "explicit_ancilla_count": row["logic_explicit_ancilla"],
    }


def _mapping_metrics(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "total_gate_count": row["mapped_gates"],
        "one_qubit_gate_count": row["native_oneq_count"],
        "two_qubit_gate_count": row["native_twoq_count"],
        "native_entangling_count": row["native_twoq_count"],
        "swap_count": int((row["native_gate_counts"] or {}).get("swap", 0)),
        "depth": row["mapped_depth"],
        "two_qubit_depth": row["native_twoq_depth"],
        "target_violation_count": int(row["unsupported_instructions"])
        + int(row["coupling_violations"]),
        "direction_violation_count": row["coupling_violations"],
        "routing_overhead": row["routing_twoq_overhead_ratio"],
        "estimated_error": None,
        "basis_reference_gates": row["basis_reference_gates"],
        "basis_reference_depth": row["basis_reference_depth"],
        "basis_reference_twoq_count": row["basis_reference_twoq_count"],
        "routing_gate_delta": row["routing_gate_delta"],
        "routing_depth_delta": row["routing_depth_delta"],
        "routing_twoq_delta": row["routing_twoq_delta"],
        "active_physical_qubits": row["active_physical_qubits"],
        "compiler_ancillas": row["compiler_ancillas"],
        "transpiler_added_qubits": row["transpiler_added_qubits"],
    }


def _existing_batch(
    db: ExperimentDB, experiment_id: uuid.UUID, label: str
) -> tuple[uuid.UUID, str] | None:
    row = db.connection.execute(
        """SELECT rb.batch_id, rbs.status
           FROM run_batches rb
           JOIN run_batch_status rbs ON rbs.batch_id = rb.batch_id
           WHERE rb.experiment_id = ? AND rb.label = ?""",
        [experiment_id, label],
    ).fetchone()
    if row is None:
        return None
    return uuid.UUID(str(row[0])), str(row[1])


def _summary_for_existing(
    db: ExperimentDB,
    *,
    experiment_id: uuid.UUID,
    batch_id: uuid.UUID,
    source_sha256: str,
    source_rows: int,
) -> IngestSummary:
    synth_count = int(
        db.connection.execute(
            "SELECT count(*) FROM synthesis_attempts WHERE batch_id = ?", [batch_id]
        ).fetchone()[0]
    )
    map_count = int(
        db.connection.execute(
            "SELECT count(*) FROM mapping_attempts WHERE batch_id = ?", [batch_id]
        ).fetchone()[0]
    )
    logical_verify = int(
        db.connection.execute(
            """SELECT count(*) FROM verification_results vr
               JOIN synthesis_attempts sa ON sa.attempt_id = vr.synthesis_attempt_id
               WHERE sa.batch_id = ?""",
            [batch_id],
        ).fetchone()[0]
    )
    mapping_verify = int(
        db.connection.execute(
            """SELECT count(*) FROM verification_results vr
               JOIN mapping_attempts ma ON ma.mapping_attempt_id = vr.mapping_attempt_id
               WHERE ma.batch_id = ?""",
            [batch_id],
        ).fetchone()[0]
    )
    status_counts = {
        str(status): int(count)
        for status, count in db.connection.execute(
            "SELECT status, count(*) FROM mapping_attempts WHERE batch_id = ? GROUP BY status",
            [batch_id],
        ).fetchall()
    }
    return IngestSummary(
        str(experiment_id),
        str(batch_id),
        source_sha256,
        source_rows,
        synth_count,
        map_count,
        logical_verify,
        mapping_verify,
        status_counts,
        already_ingested=True,
    )


def ingest_rows(
    db: ExperimentDB,
    rows: Sequence[dict[str, Any]],
    *,
    source_sha256: str,
    source_path: str | pathlib.Path,
    source_byte_size: int,
    experiment_slug: str = DEFAULT_EXPERIMENT_SLUG,
    experiment_title: str = DEFAULT_EXPERIMENT_TITLE,
    resume: bool = True,
) -> IngestSummary:
    """Ingest validated rows atomically into an :class:`ExperimentDB`."""
    if not rows:
        raise HardwareValidationIngestError("cannot ingest an empty row sequence")
    for index, row in enumerate(rows, start=1):
        _validate_row(row, index)
    if len({row["record_key"] for row in rows}) != len(rows):
        raise HardwareValidationIngestError("duplicate record keys in row sequence")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["synthesis_key"])].append(row)
    for synthesis_key, group in groups.items():
        signatures = {
            canonical_json({field: row[field] for field in _SYNTHESIS_INVARIANT_FIELDS})
            for row in group
        }
        if len(signatures) != 1:
            raise HardwareValidationIngestError(
                f"synthesis group {synthesis_key} has inconsistent repeated evidence"
            )
        logical_presence = {_has_logical_result(row) for row in group}
        if len(logical_presence) != 1:
            raise HardwareValidationIngestError(
                f"synthesis group {synthesis_key} mixes success and failure rows"
            )

    experiment_id = db.create_experiment(
        experiment_slug,
        experiment_title,
        description="Append-only exact logical and topology-aware mapped oracle validation.",
        objective={
            "competition": "XA-202609",
            # Keep the experiment identity stable across additive source-schema
            # revisions; each run batch records its exact source version.
            "source_schema_version": LEGACY_SCHEMA_VERSION,
            "claim_policy": "verified paired comparisons only",
        },
    )
    batch_label = f"jsonl:{source_sha256[:20]}"
    existing = _existing_batch(db, experiment_id, batch_label)
    if existing is not None:
        batch_id, status = existing
        if not resume:
            raise HardwareValidationIngestError(
                f"source {source_sha256} was already ingested in batch {batch_id}"
            )
        if status != "completed":
            raise HardwareValidationIngestError(
                f"existing source batch {batch_id} is unexpectedly {status!r}"
            )
        return _summary_for_existing(
            db,
            experiment_id=experiment_id,
            batch_id=batch_id,
            source_sha256=source_sha256,
            source_rows=len(rows),
        )

    status_counts: Counter[str] = Counter()
    synthesis_attempt_count = 0
    mapping_attempt_count = 0
    logical_verification_count = 0
    mapping_verification_count = 0
    with db.transaction():
        batch_id = db.create_run_batch(
            experiment_id,
            batch_label,
            config={
                "source_sha256": source_sha256,
                "source_schema_version": rows[0]["schema_version"],
                "source_run_id": rows[0]["run_id"],
                "benchmark_suite": rows[0]["benchmark_suite"],
                "benchmark_suite_id": rows[0]["benchmark_suite_id"],
                "record_count": len(rows),
            },
            planned_cell_count=len(groups),
            host={"source_path": pathlib.Path(source_path).resolve().as_posix()},
        )
        db.start_batch(batch_id, message="validated JSONL ingestion started")

        for ordinal, synthesis_key in enumerate(sorted(groups), start=1):
            group = groups[synthesis_key]
            first = group[0]
            function_id = db.register_boolean_function(
                str(first["function_id"]),
                int(first["n_inputs"]),
                {
                    "n_inputs": int(first["n_inputs"]),
                    "truth_table_hex": first["truth_table_hex"],
                },
                truth_table_hex=str(first["truth_table_hex"]),
                metadata={
                    "function_truth_hash": first["function_truth_hash"],
                    "family": first["family"],
                },
            )
            case_id = db.register_benchmark_case(
                experiment_id,
                function_id,
                str(first["function_id"]),
                suite=str(first["benchmark_suite"]),
                metadata={
                    "benchmark_suite_id": first["benchmark_suite_id"],
                    "family": first["family"],
                    "function_truth_hash": first["function_truth_hash"],
                },
            )
            method_name, method_spec = _method_identity(first)
            method_spec_id = db.register_method_spec(
                method_name,
                method_spec,
                model_sha256=first["model_hash"],
            )
            cell_id = db.get_or_create_cell(
                experiment_id,
                case_id,
                method_spec_id,
                int(first["synthesis_seed"]),
            )

            logical_success = _has_logical_result(first)
            if logical_success:
                synth_ref = db.record_synthesis_attempt(
                    cell_id,
                    batch_id,
                    "success",
                    selected_method=first["selected_method"],
                    runtime_s=float(first["synth_time_s"])
                    + float(first["logical_verify_time_s"] or 0.0),
                    worker={"source_run_id": first["run_id"]},
                    result=_logical_result_payload(first),
                    logical_metrics=_logical_metrics(first),
                    peak_rss_mb=first["synth_peak_rss_mb"],
                    peak_system_memory_percent=first[
                        "synth_peak_system_memory_percent"
                    ],
                    resource_stage_peaks=first["synth_resource_stage_peaks"],
                )
                synthesis_attempt_count += 1
                logical_pass = bool(
                    first["artifact_consistent"]
                    and first["result_correct"]
                    and first["engine_correct"]
                )
                db.record_verification(
                    "logical",
                    synth_ref.attempt_id,
                    "verify_oracle+artifact_contract",
                    "pass" if logical_pass else "fail",
                    passed=logical_pass,
                    basis_states_checked=int(first["engine_states_evaluated"] or 0),
                    mismatch_count=0 if logical_pass else None,
                    details={
                        "artifact_consistent": first["artifact_consistent"],
                        "result_correct": first["result_correct"],
                        "engine_correct": first["engine_correct"],
                    },
                )
                logical_verification_count += 1
            else:
                source_status = str(first["status"])
                synth_ref = db.record_synthesis_attempt(
                    cell_id,
                    batch_id,
                    _attempt_status(source_status),
                    error_type=first["error_code"] or source_status,
                    error_message=first["error_message"],
                    worker={"source_run_id": first["run_id"], "stage": first["stage"]},
                    result={
                        "source_synthesis_key": first["synthesis_key"],
                        "source_status": source_status,
                    },
                    peak_rss_mb=first["synth_peak_rss_mb"],
                    peak_system_memory_percent=first[
                        "synth_peak_system_memory_percent"
                    ],
                    resource_stage_peaks=first["synth_resource_stage_peaks"],
                )
                synthesis_attempt_count += 1
                status_counts[f"synthesis_{source_status}"] += 1
                continue

            for row in sorted(group, key=lambda item: str(item["record_key"])):
                target_db_id = db.register_hardware_target(
                    str(row["target_id"]),
                    int(row["target_num_qubits"]),
                    {
                        "runner_alias": row["target_name"],
                        "target_hash": row["target_hash"],
                        "manifest": row["target_manifest"],
                    },
                )
                transpile_spec_id = db.register_transpile_spec(
                    target_db_id,
                    f"{row['target_id']}:seed-{int(row['transpile_seed'])}",
                    _transpile_identity(row),
                )
                source_status = str(row["status"])
                map_success = source_status == "ok"
                database_status = "success" if map_success else _attempt_status(source_status)
                runtime_s = None
                if row["map_time_s"] is not None:
                    runtime_s = float(row["map_time_s"]) + float(
                        row["mapped_verify_time_s"] or 0.0
                    )
                map_ref = db.record_mapping_attempt(
                    synth_ref.attempt_id,
                    batch_id,
                    transpile_spec_id,
                    database_status,
                    seed_transpiler=int(row["transpile_seed"]),
                    runtime_s=runtime_s,
                    error_type=None if map_success else (row["error_code"] or source_status),
                    error_message=None if map_success else row["error_message"],
                    result={
                        "source_record_key": row["record_key"],
                        "source_run_id": row["run_id"],
                        "source_status": source_status,
                        "row": row,
                    },
                    mapping_metrics=_mapping_metrics(row) if map_success else None,
                    native_gate_counts=row["native_gate_counts"] if map_success else None,
                    peak_rss_mb=row["map_peak_rss_mb"],
                    peak_system_memory_percent=row[
                        "map_peak_system_memory_percent"
                    ],
                    total_peak_rss_mb=row["total_peak_rss_mb"],
                    total_peak_system_memory_percent=row[
                        "total_peak_system_memory_percent"
                    ],
                    resource_stage_peaks=row["map_resource_stage_peaks"],
                )
                mapping_attempt_count += 1
                status_counts[database_status] += 1
                if row["mapped_verify_ok"] is not None:
                    mapped_pass = bool(
                        row["mapped_verify_ok"]
                        and row["mapped_verification_complete"]
                        and int(row["mapped_mismatches"] or 0) == 0
                        and int(row["unsupported_instructions"] or 0) == 0
                        and int(row["coupling_violations"] or 0) == 0
                    )
                    db.record_verification(
                        "mapping",
                        map_ref.attempt_id,
                        "exact_xy_phase_target_legality",
                        "pass" if mapped_pass else "fail",
                        passed=mapped_pass,
                        basis_states_checked=int(row["mapped_states_evaluated"] or 0),
                        mismatch_count=int(row["mapped_mismatches"] or 0),
                        max_leakage=row["mapped_max_leakage"],
                        max_phase_error=row["mapped_max_phase_error"],
                        tolerance=row["mapped_probability_tolerance"],
                        details={
                            "verification_mode": row["mapped_verify_mode"],
                            "max_probability_error": row["mapped_max_probability_error"],
                            "phase_tolerance": row["mapped_phase_tolerance"],
                            "unsupported_instructions": row["unsupported_instructions"],
                            "coupling_violations": row["coupling_violations"],
                            "mapping_provenance_consistent": row[
                                "mapping_provenance_consistent"
                            ],
                        },
                    )
                    mapping_verification_count += 1

        db.record_artifact(
            experiment_id,
            "hardware_validation_jsonl",
            pathlib.Path(source_path).resolve(),
            source_sha256,
            batch_id=batch_id,
            byte_size=int(source_byte_size),
            mime_type="application/x-ndjson",
            metadata={
                "source_schema_version": rows[0]["schema_version"],
                "source_run_id": rows[0]["run_id"],
                "record_count": len(rows),
            },
        )
        db.complete_batch(
            batch_id,
            message=(
                f"ingested {len(rows)} rows, {synthesis_attempt_count} synthesis attempts, "
                f"{mapping_attempt_count} mapping attempts"
            ),
        )

    return IngestSummary(
        str(experiment_id),
        str(batch_id),
        source_sha256,
        len(rows),
        synthesis_attempt_count,
        mapping_attempt_count,
        logical_verification_count,
        mapping_verification_count,
        dict(sorted(status_counts.items())),
    )


def ingest_jsonl(
    jsonl_path: str | pathlib.Path,
    db_path: str | pathlib.Path,
    *,
    experiment_slug: str = DEFAULT_EXPERIMENT_SLUG,
    experiment_title: str = DEFAULT_EXPERIMENT_TITLE,
    resume: bool = True,
) -> IngestSummary:
    """Validate and atomically ingest one runner output file."""
    source = pathlib.Path(jsonl_path).resolve()
    rows, source_sha256 = load_jsonl(source)
    with ExperimentDB(db_path) as db:
        return ingest_rows(
            db,
            rows,
            source_sha256=source_sha256,
            source_path=source,
            source_byte_size=source.stat().st_size,
            experiment_slug=experiment_slug,
            experiment_title=experiment_title,
            resume=resume,
        )


__all__ = [
    "DEFAULT_EXPERIMENT_SLUG",
    "DEFAULT_EXPERIMENT_TITLE",
    "HardwareValidationIngestError",
    "IngestSummary",
    "ingest_jsonl",
    "ingest_rows",
    "load_jsonl",
]
