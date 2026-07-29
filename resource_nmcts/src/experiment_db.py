"""Versioned, append-only DuckDB storage for reproducible experiments.

The legacy CSV loaders in :mod:`analysis` intentionally remain separate from
this module.  This database is the write path for new competition experiments:

* immutable, content-addressed benchmark/method/target specifications;
* one logical synthesis cell per canonical experimental key;
* append-only synthesis and mapping attempts (retries never overwrite);
* typed metric tables plus canonical JSON provenance;
* first-success ``canonical_*`` and most-recent ``latest_*`` views; and
* event-sourced batch state and coverage views.

All mutating public methods are transactional and may be composed inside
``ExperimentDB.transaction()``.  IDs for content-addressed records are UUIDv5;
attempts, batches, events, verification records, and artifacts use UUIDv4.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import decimal
import enum
import hashlib
import json
import math
import pathlib
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import duckdb


SCHEMA_VERSION = 2

_ID_NAMESPACE = uuid.UUID("b5f73246-d7b0-5fb3-8bf0-109c98347572")
_TERMINAL_BATCH_STATES = frozenset({"completed", "failed", "cancelled"})
_BATCH_STATES = frozenset({"created", "running", *_TERMINAL_BATCH_STATES})
_ATTEMPT_STATES = frozenset({"success", "error", "timeout", "cancelled"})
_VERIFY_STATES = frozenset({"pass", "fail", "error", "skipped"})


class ExperimentDBError(RuntimeError):
    """Base error for experiment database contract violations."""


class SchemaVersionError(ExperimentDBError):
    """The database schema is newer than, or differs from, this implementation."""


class IdentityConflictError(ExperimentDBError):
    """A human-readable unique key was reused for different canonical content."""


class InvalidTransitionError(ExperimentDBError):
    """An invalid append-only batch state transition was requested."""


@dataclass(frozen=True)
class AttemptRef:
    """Stable identifier and monotonic number allocated to an attempt."""

    attempt_id: uuid.UUID
    attempt_no: int


@dataclass(frozen=True)
class BatchStatus:
    """Latest materialized state of a run batch."""

    batch_id: uuid.UUID
    event_no: int
    status: str
    message: str | None
    recorded_at: dt.datetime


def _normalise_json(value: Any) -> Any:
    """Convert supported Python values to deterministic JSON-compatible data."""

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _normalise_json(dataclasses.asdict(value))
    if isinstance(value, enum.Enum):
        return _normalise_json(value.value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, pathlib.Path):
        return value.as_posix()
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        if isinstance(value, dt.datetime) and value.tzinfo is None:
            raise ValueError("naive datetime is not canonical; provide a timezone")
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not valid canonical JSON")
        return format(value.normalize(), "f")
    if isinstance(value, bytes):
        return {"$bytes_base64": base64.b64encode(value).decode("ascii")}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity are not valid canonical JSON")
        return 0.0 if value == 0.0 else value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"canonical JSON object keys must be strings, got {type(key)!r}")
            out[key] = _normalise_json(item)
        return out
    if isinstance(value, (set, frozenset)):
        normalised = [_normalise_json(item) for item in value]
        return sorted(normalised, key=canonical_json)
    if isinstance(value, (list, tuple)):
        return [_normalise_json(item) for item in value]

    # NumPy scalar support without importing NumPy into this lightweight layer.
    item_method = getattr(value, "item", None)
    if callable(item_method) and type(value).__module__.split(".", 1)[0] == "numpy":
        return _normalise_json(item_method())
    raise TypeError(f"unsupported canonical JSON value: {type(value)!r}")


def canonical_json(value: Any) -> str:
    """Return UTF-8, key-sorted, whitespace-free canonical JSON.

    The function rejects non-finite floats and naive datetimes so hashes cannot
    vary silently across JSON implementations or local time zones.
    """

    return json.dumps(
        _normalise_json(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(value: bytes | str | Any) -> str:
    """Return SHA-256 for bytes, text, or a canonically encoded Python value."""

    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_payload(value: Any) -> tuple[str, str]:
    """Return ``(canonical_json, sha256)`` for a provenance payload."""

    payload = canonical_json(value)
    return payload, sha256_hex(payload)


def _content_uuid(kind: str, digest: str) -> uuid.UUID:
    return uuid.uuid5(_ID_NAMESPACE, f"{kind}:{digest}")


_MIGRATION_001 = r"""
CREATE TABLE experiments (
    experiment_id UUID PRIMARY KEY,
    slug VARCHAR NOT NULL UNIQUE,
    title VARCHAR NOT NULL,
    description VARCHAR,
    objective_json JSON NOT NULL,
    definition_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(definition_hash, '^[0-9a-f]{64}$')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE run_batches (
    batch_id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(experiment_id),
    label VARCHAR NOT NULL,
    config_json JSON NOT NULL,
    config_hash VARCHAR NOT NULL CHECK (regexp_matches(config_hash, '^[0-9a-f]{64}$')),
    planned_cell_count BIGINT CHECK (planned_cell_count IS NULL OR planned_cell_count >= 0),
    host_json JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    UNIQUE (experiment_id, label)
);

CREATE TABLE run_batch_status_events (
    event_id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES run_batches(batch_id),
    event_no INTEGER NOT NULL CHECK (event_no >= 1),
    status VARCHAR NOT NULL CHECK (status IN ('created', 'running', 'completed', 'failed', 'cancelled')),
    message VARCHAR,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    UNIQUE (batch_id, event_no)
);

CREATE TABLE boolean_functions (
    function_id UUID PRIMARY KEY,
    canonical_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(canonical_hash, '^[0-9a-f]{64}$')),
    name VARCHAR NOT NULL,
    n_inputs INTEGER NOT NULL CHECK (n_inputs >= 1),
    definition_json JSON NOT NULL,
    truth_table_hex VARCHAR,
    anf_json JSON,
    metadata_json JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE benchmark_cases (
    case_id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(experiment_id),
    function_id UUID NOT NULL REFERENCES boolean_functions(function_id),
    suite VARCHAR NOT NULL,
    case_label VARCHAR NOT NULL,
    metadata_json JSON NOT NULL,
    definition_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(definition_hash, '^[0-9a-f]{64}$')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    UNIQUE (experiment_id, suite, case_label)
);

CREATE TABLE method_specs (
    method_spec_id UUID PRIMARY KEY,
    method_name VARCHAR NOT NULL,
    spec_json JSON NOT NULL,
    spec_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(spec_hash, '^[0-9a-f]{64}$')),
    model_sha256 VARCHAR CHECK (model_sha256 IS NULL OR regexp_matches(model_sha256, '^[0-9a-f]{64}$')),
    code_revision VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE hardware_targets (
    target_id UUID PRIMARY KEY,
    target_name VARCHAR NOT NULL,
    num_qubits INTEGER NOT NULL CHECK (num_qubits >= 1),
    spec_json JSON NOT NULL,
    spec_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(spec_hash, '^[0-9a-f]{64}$')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE transpile_specs (
    transpile_spec_id UUID PRIMARY KEY,
    target_id UUID NOT NULL REFERENCES hardware_targets(target_id),
    spec_name VARCHAR NOT NULL,
    spec_json JSON NOT NULL,
    spec_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(spec_hash, '^[0-9a-f]{64}$')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE synthesis_cells (
    cell_id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(experiment_id),
    case_id UUID NOT NULL REFERENCES benchmark_cases(case_id),
    method_spec_id UUID NOT NULL REFERENCES method_specs(method_spec_id),
    seed BIGINT NOT NULL CHECK (seed >= 0),
    cell_key_json JSON NOT NULL,
    cell_key_hash VARCHAR NOT NULL UNIQUE CHECK (regexp_matches(cell_key_hash, '^[0-9a-f]{64}$')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    UNIQUE (experiment_id, case_id, method_spec_id, seed)
);

CREATE TABLE batch_cells (
    batch_id UUID NOT NULL REFERENCES run_batches(batch_id),
    cell_id UUID NOT NULL REFERENCES synthesis_cells(cell_id),
    ordinal INTEGER CHECK (ordinal IS NULL OR ordinal >= 0),
    added_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (batch_id, cell_id)
);

CREATE TABLE synthesis_attempts (
    attempt_id UUID PRIMARY KEY,
    cell_id UUID NOT NULL REFERENCES synthesis_cells(cell_id),
    batch_id UUID NOT NULL REFERENCES run_batches(batch_id),
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    status VARCHAR NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'cancelled')),
    selected_method VARCHAR,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    runtime_s DOUBLE CHECK (runtime_s IS NULL OR runtime_s >= 0),
    error_type VARCHAR,
    error_message VARCHAR,
    worker_json JSON NOT NULL,
    result_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at),
    UNIQUE (cell_id, attempt_no)
);

CREATE TABLE logical_metrics (
    logical_metric_id UUID PRIMARY KEY,
    synthesis_attempt_id UUID NOT NULL UNIQUE REFERENCES synthesis_attempts(attempt_id),
    t_count BIGINT CHECK (t_count IS NULL OR t_count >= 0),
    cnot_count BIGINT CHECK (cnot_count IS NULL OR cnot_count >= 0),
    depth BIGINT CHECK (depth IS NULL OR depth >= 0),
    gate_count BIGINT CHECK (gate_count IS NULL OR gate_count >= 0),
    ancilla_count BIGINT CHECK (ancilla_count IS NULL OR ancilla_count >= 0),
    n_qubits BIGINT CHECK (n_qubits IS NULL OR n_qubits >= 1),
    weighted_score DOUBLE,
    metric_payload_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE mapping_attempts (
    mapping_attempt_id UUID PRIMARY KEY,
    synthesis_attempt_id UUID NOT NULL REFERENCES synthesis_attempts(attempt_id),
    batch_id UUID NOT NULL REFERENCES run_batches(batch_id),
    transpile_spec_id UUID NOT NULL REFERENCES transpile_specs(transpile_spec_id),
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    status VARCHAR NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'cancelled')),
    seed_transpiler BIGINT CHECK (seed_transpiler IS NULL OR seed_transpiler >= 0),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    runtime_s DOUBLE CHECK (runtime_s IS NULL OR runtime_s >= 0),
    error_type VARCHAR,
    error_message VARCHAR,
    result_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at),
    UNIQUE (synthesis_attempt_id, transpile_spec_id, attempt_no)
);

CREATE TABLE mapping_metrics (
    mapping_metric_id UUID PRIMARY KEY,
    mapping_attempt_id UUID NOT NULL UNIQUE REFERENCES mapping_attempts(mapping_attempt_id),
    total_gate_count BIGINT CHECK (total_gate_count IS NULL OR total_gate_count >= 0),
    one_qubit_gate_count BIGINT CHECK (one_qubit_gate_count IS NULL OR one_qubit_gate_count >= 0),
    two_qubit_gate_count BIGINT CHECK (two_qubit_gate_count IS NULL OR two_qubit_gate_count >= 0),
    native_entangling_count BIGINT CHECK (native_entangling_count IS NULL OR native_entangling_count >= 0),
    swap_count BIGINT CHECK (swap_count IS NULL OR swap_count >= 0),
    depth BIGINT CHECK (depth IS NULL OR depth >= 0),
    two_qubit_depth BIGINT CHECK (two_qubit_depth IS NULL OR two_qubit_depth >= 0),
    target_violation_count BIGINT CHECK (target_violation_count IS NULL OR target_violation_count >= 0),
    direction_violation_count BIGINT CHECK (direction_violation_count IS NULL OR direction_violation_count >= 0),
    routing_overhead DOUBLE,
    estimated_error DOUBLE,
    metric_payload_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE verification_results (
    verification_id UUID PRIMARY KEY,
    verification_scope VARCHAR NOT NULL CHECK (verification_scope IN ('logical', 'mapping')),
    synthesis_attempt_id UUID REFERENCES synthesis_attempts(attempt_id),
    mapping_attempt_id UUID REFERENCES mapping_attempts(mapping_attempt_id),
    verifier_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('pass', 'fail', 'error', 'skipped')),
    passed BOOLEAN,
    basis_states_checked BIGINT CHECK (basis_states_checked IS NULL OR basis_states_checked >= 0),
    mismatch_count BIGINT CHECK (mismatch_count IS NULL OR mismatch_count >= 0),
    max_leakage DOUBLE,
    max_phase_error DOUBLE,
    tolerance DOUBLE,
    details_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    CHECK (
        (verification_scope = 'logical' AND synthesis_attempt_id IS NOT NULL AND mapping_attempt_id IS NULL)
        OR
        (verification_scope = 'mapping' AND synthesis_attempt_id IS NULL AND mapping_attempt_id IS NOT NULL)
    )
);

CREATE TABLE native_gate_counts (
    mapping_attempt_id UUID NOT NULL REFERENCES mapping_attempts(mapping_attempt_id),
    gate_name VARCHAR NOT NULL,
    gate_count BIGINT NOT NULL CHECK (gate_count >= 0),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (mapping_attempt_id, gate_name)
);

CREATE TABLE artifacts (
    artifact_id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(experiment_id),
    batch_id UUID REFERENCES run_batches(batch_id),
    synthesis_attempt_id UUID REFERENCES synthesis_attempts(attempt_id),
    mapping_attempt_id UUID REFERENCES mapping_attempts(mapping_attempt_id),
    artifact_kind VARCHAR NOT NULL,
    path_or_uri VARCHAR NOT NULL,
    content_sha256 VARCHAR NOT NULL CHECK (regexp_matches(content_sha256, '^[0-9a-f]{64}$')),
    byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
    mime_type VARCHAR,
    metadata_json JSON NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE VIEW run_batch_status AS
SELECT batch_id, event_no, status, message, recorded_at
FROM run_batch_status_events
QUALIFY row_number() OVER (
    PARTITION BY batch_id ORDER BY event_no DESC, recorded_at DESC, event_id DESC
) = 1;

CREATE VIEW latest_synthesis_attempts AS
SELECT *
FROM synthesis_attempts
QUALIFY row_number() OVER (
    PARTITION BY cell_id ORDER BY attempt_no DESC, recorded_at DESC, attempt_id DESC
) = 1;

CREATE VIEW canonical_synthesis_attempts AS
SELECT *
FROM synthesis_attempts
WHERE status = 'success'
QUALIFY row_number() OVER (
    PARTITION BY cell_id ORDER BY attempt_no ASC, recorded_at ASC, attempt_id ASC
) = 1;

CREATE VIEW latest_mapping_attempts AS
SELECT *
FROM mapping_attempts
QUALIFY row_number() OVER (
    PARTITION BY synthesis_attempt_id, transpile_spec_id
    ORDER BY attempt_no DESC, recorded_at DESC, mapping_attempt_id DESC
) = 1;

CREATE VIEW canonical_mapping_attempts AS
SELECT *
FROM mapping_attempts
WHERE status = 'success'
QUALIFY row_number() OVER (
    PARTITION BY synthesis_attempt_id, transpile_spec_id
    ORDER BY attempt_no ASC, recorded_at ASC, mapping_attempt_id ASC
) = 1;

CREATE VIEW logical_verification_summary AS
SELECT
    synthesis_attempt_id,
    count(*) AS verification_count,
    count(*) FILTER (WHERE status = 'pass') AS pass_count,
    count(*) FILTER (WHERE status IN ('fail', 'error')) AS adverse_count,
    count(*) FILTER (WHERE status = 'pass') > 0
      AND count(*) FILTER (WHERE status IN ('fail', 'error')) = 0 AS verified
FROM verification_results
WHERE verification_scope = 'logical'
GROUP BY synthesis_attempt_id;

CREATE VIEW mapping_verification_summary AS
SELECT
    mapping_attempt_id,
    count(*) AS verification_count,
    count(*) FILTER (WHERE status = 'pass') AS pass_count,
    count(*) FILTER (WHERE status IN ('fail', 'error')) AS adverse_count,
    count(*) FILTER (WHERE status = 'pass') > 0
      AND count(*) FILTER (WHERE status IN ('fail', 'error')) = 0 AS verified
FROM verification_results
WHERE verification_scope = 'mapping'
GROUP BY mapping_attempt_id;

CREATE VIEW canonical_logical_results AS
SELECT
    c.experiment_id,
    c.cell_id,
    c.case_id,
    bc.suite,
    bc.case_label,
    bc.function_id,
    bf.name AS function_name,
    bf.n_inputs,
    c.method_spec_id,
    ms.method_name,
    c.seed,
    sa.attempt_id AS synthesis_attempt_id,
    sa.attempt_no,
    sa.selected_method,
    sa.runtime_s,
    lm.t_count,
    lm.cnot_count,
    lm.depth,
    lm.gate_count,
    lm.ancilla_count,
    lm.n_qubits,
    lm.weighted_score,
    coalesce(lvs.verification_count, 0) AS logical_verification_count,
    coalesce(lvs.verified, false) AS logical_verified
FROM synthesis_cells c
JOIN benchmark_cases bc ON bc.case_id = c.case_id
JOIN boolean_functions bf ON bf.function_id = bc.function_id
JOIN method_specs ms ON ms.method_spec_id = c.method_spec_id
JOIN canonical_synthesis_attempts sa ON sa.cell_id = c.cell_id
LEFT JOIN logical_metrics lm ON lm.synthesis_attempt_id = sa.attempt_id
LEFT JOIN logical_verification_summary lvs ON lvs.synthesis_attempt_id = sa.attempt_id;

CREATE VIEW canonical_mapping_results AS
SELECT
    lr.*,
    ma.mapping_attempt_id,
    ma.transpile_spec_id,
    ts.target_id,
    ht.target_name,
    ma.attempt_no AS mapping_attempt_no,
    ma.seed_transpiler,
    ma.runtime_s AS mapping_runtime_s,
    mm.total_gate_count,
    mm.one_qubit_gate_count,
    mm.two_qubit_gate_count,
    mm.native_entangling_count,
    mm.swap_count,
    mm.depth AS mapped_depth,
    mm.two_qubit_depth,
    mm.target_violation_count,
    mm.direction_violation_count,
    mm.routing_overhead,
    mm.estimated_error,
    coalesce(mvs.verification_count, 0) AS mapping_verification_count,
    coalesce(mvs.verified, false) AS mapping_verified
FROM canonical_logical_results lr
JOIN canonical_mapping_attempts ma ON ma.synthesis_attempt_id = lr.synthesis_attempt_id
JOIN transpile_specs ts ON ts.transpile_spec_id = ma.transpile_spec_id
JOIN hardware_targets ht ON ht.target_id = ts.target_id
LEFT JOIN mapping_metrics mm ON mm.mapping_attempt_id = ma.mapping_attempt_id
LEFT JOIN mapping_verification_summary mvs ON mvs.mapping_attempt_id = ma.mapping_attempt_id;

CREATE VIEW batch_coverage AS
WITH cell_counts AS (
    SELECT
        b.batch_id,
        count(bc.cell_id) AS registered_cells,
        count(csa.attempt_id) AS canonical_success_cells,
        count(csa.attempt_id) FILTER (WHERE clr.logical_verified) AS canonical_verified_cells
    FROM run_batches b
    LEFT JOIN batch_cells bc ON bc.batch_id = b.batch_id
    LEFT JOIN canonical_synthesis_attempts csa ON csa.cell_id = bc.cell_id
    LEFT JOIN canonical_logical_results clr ON clr.cell_id = bc.cell_id
    GROUP BY b.batch_id
),
batch_attempts AS (
    SELECT
        b.batch_id,
        count(DISTINCT sa.cell_id) AS attempted_cells_in_batch,
        count(DISTINCT sa.cell_id) FILTER (WHERE sa.status = 'success') AS successful_cells_in_batch,
        count(sa.attempt_id) AS synthesis_attempt_count
    FROM run_batches b
    LEFT JOIN synthesis_attempts sa ON sa.batch_id = b.batch_id
    GROUP BY b.batch_id
)
SELECT
    b.batch_id,
    b.experiment_id,
    b.label,
    bs.status,
    b.planned_cell_count,
    cc.registered_cells,
    ba.attempted_cells_in_batch,
    ba.successful_cells_in_batch,
    cc.canonical_success_cells,
    cc.canonical_verified_cells,
    ba.synthesis_attempt_count,
    CASE
        WHEN coalesce(b.planned_cell_count, cc.registered_cells) = 0 THEN 0.0
        ELSE cc.canonical_success_cells::DOUBLE
             / coalesce(b.planned_cell_count, cc.registered_cells)
    END AS canonical_success_fraction
FROM run_batches b
JOIN run_batch_status bs ON bs.batch_id = b.batch_id
JOIN cell_counts cc ON cc.batch_id = b.batch_id
JOIN batch_attempts ba ON ba.batch_id = b.batch_id;

CREATE VIEW paired_logical_metrics AS
SELECT
    a.experiment_id,
    a.case_id,
    a.case_label,
    a.function_id,
    a.function_name,
    a.seed,
    a.method_spec_id AS method_a_spec_id,
    a.method_name AS method_a,
    b.method_spec_id AS method_b_spec_id,
    b.method_name AS method_b,
    a.synthesis_attempt_id AS method_a_attempt_id,
    b.synthesis_attempt_id AS method_b_attempt_id,
    a.t_count AS method_a_t_count,
    b.t_count AS method_b_t_count,
    b.t_count - a.t_count AS delta_b_minus_a_t_count,
    a.cnot_count AS method_a_cnot_count,
    b.cnot_count AS method_b_cnot_count,
    b.cnot_count - a.cnot_count AS delta_b_minus_a_cnot_count,
    a.depth AS method_a_depth,
    b.depth AS method_b_depth,
    b.depth - a.depth AS delta_b_minus_a_depth,
    a.gate_count AS method_a_gate_count,
    b.gate_count AS method_b_gate_count,
    b.gate_count - a.gate_count AS delta_b_minus_a_gate_count,
    a.weighted_score AS method_a_weighted_score,
    b.weighted_score AS method_b_weighted_score,
    b.weighted_score - a.weighted_score AS delta_b_minus_a_weighted_score,
    a.runtime_s AS method_a_runtime_s,
    b.runtime_s AS method_b_runtime_s
FROM canonical_logical_results a
JOIN canonical_logical_results b
  ON b.experiment_id = a.experiment_id
 AND b.case_id = a.case_id
 AND b.seed = a.seed
 AND cast(a.method_spec_id AS VARCHAR) < cast(b.method_spec_id AS VARCHAR)
WHERE a.logical_verified AND b.logical_verified;

CREATE VIEW paired_mapping_metrics AS
SELECT
    a.experiment_id,
    a.case_id,
    a.case_label,
    a.function_id,
    a.function_name,
    a.seed,
    a.transpile_spec_id,
    a.target_id,
    a.target_name,
    a.method_spec_id AS method_a_spec_id,
    a.method_name AS method_a,
    b.method_spec_id AS method_b_spec_id,
    b.method_name AS method_b,
    a.mapping_attempt_id AS method_a_mapping_attempt_id,
    b.mapping_attempt_id AS method_b_mapping_attempt_id,
    a.total_gate_count AS method_a_total_gate_count,
    b.total_gate_count AS method_b_total_gate_count,
    b.total_gate_count - a.total_gate_count AS delta_b_minus_a_total_gate_count,
    a.two_qubit_gate_count AS method_a_two_qubit_gate_count,
    b.two_qubit_gate_count AS method_b_two_qubit_gate_count,
    b.two_qubit_gate_count - a.two_qubit_gate_count AS delta_b_minus_a_two_qubit_gate_count,
    a.mapped_depth AS method_a_mapped_depth,
    b.mapped_depth AS method_b_mapped_depth,
    b.mapped_depth - a.mapped_depth AS delta_b_minus_a_mapped_depth,
    a.mapping_runtime_s AS method_a_mapping_runtime_s,
    b.mapping_runtime_s AS method_b_mapping_runtime_s
FROM canonical_mapping_results a
JOIN canonical_mapping_results b
  ON b.experiment_id = a.experiment_id
 AND b.case_id = a.case_id
 AND b.seed = a.seed
 AND b.transpile_spec_id = a.transpile_spec_id
 AND cast(a.method_spec_id AS VARCHAR) < cast(b.method_spec_id AS VARCHAR)
WHERE a.logical_verified AND b.logical_verified
  AND a.mapping_verified AND b.mapping_verified;
"""


_MIGRATION_002 = r"""
ALTER TABLE synthesis_attempts ADD COLUMN peak_rss_mb DOUBLE;
ALTER TABLE synthesis_attempts ADD COLUMN peak_system_memory_percent DOUBLE;
ALTER TABLE synthesis_attempts ADD COLUMN resource_stage_peaks_json JSON;

ALTER TABLE mapping_attempts ADD COLUMN peak_rss_mb DOUBLE;
ALTER TABLE mapping_attempts ADD COLUMN peak_system_memory_percent DOUBLE;
ALTER TABLE mapping_attempts ADD COLUMN total_peak_rss_mb DOUBLE;
ALTER TABLE mapping_attempts ADD COLUMN total_peak_system_memory_percent DOUBLE;
ALTER TABLE mapping_attempts ADD COLUMN resource_stage_peaks_json JSON;
"""


_MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (1, "initial_append_only_experiment_schema", _MIGRATION_001),
    (2, "attempt_resource_telemetry", _MIGRATION_002),
)


def _as_uuid(value: uuid.UUID | str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _json_or_empty(value: Any | None) -> str:
    return canonical_json({} if value is None else value)


def _metric_value(metrics: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in metrics:
            return metrics[name]
    return None


def _validate_sha256(value: str | None, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field_name} must be a 64-character lowercase SHA-256 hex digest")
    return value


def _validate_aware_timestamp(value: dt.datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_resource_peak(
    value: float | None, field_name: str, *, percent: bool = False
) -> None:
    if value is None:
        return
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{field_name} must be a finite non-negative number")
    if percent and number > 100.0:
        raise ValueError(f"{field_name} must not exceed 100")


class ExperimentDB:
    """Transactional API over the versioned experiment DuckDB schema."""

    def __init__(
        self,
        path: str | pathlib.Path = ":memory:",
        *,
        read_only: bool = False,
        initialize: bool = True,
    ) -> None:
        self.path = str(path)
        self.connection = duckdb.connect(self.path, read_only=read_only)
        self._read_only = read_only
        self._tx_depth = 0
        self._rollback_only = False
        if initialize:
            if read_only:
                self._validate_schema()
            else:
                self._apply_migrations()

    def __enter__(self) -> "ExperimentDB":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator["ExperimentDB"]:
        """Open a transaction; nested calls participate in the outer transaction."""

        outer = self._tx_depth == 0
        if outer:
            self.connection.execute("BEGIN TRANSACTION")
            self._rollback_only = False
        self._tx_depth += 1
        try:
            yield self
        except BaseException:
            self._rollback_only = True
            raise
        finally:
            self._tx_depth -= 1
            if outer:
                try:
                    if self._rollback_only:
                        self.connection.execute("ROLLBACK")
                    else:
                        self.connection.execute("COMMIT")
                finally:
                    self._rollback_only = False

    def _apply_migrations(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                checksum VARCHAR NOT NULL CHECK (regexp_matches(checksum, '^[0-9a-f]{64}$')),
                applied_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
            """
        )
        applied = {
            int(row[0]): (str(row[1]), str(row[2]))
            for row in self.connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        }
        if applied and max(applied) > SCHEMA_VERSION:
            raise SchemaVersionError(
                f"database schema v{max(applied)} is newer than supported v{SCHEMA_VERSION}"
            )
        for version, name, sql in _MIGRATIONS:
            checksum = sha256_hex(sql)
            if version in applied:
                if applied[version] != (name, checksum):
                    raise SchemaVersionError(
                        f"migration {version} checksum/name mismatch: database={applied[version]!r}, "
                        f"code={(name, checksum)!r}"
                    )
                continue
            with self.transaction():
                self.connection.execute(sql)
                self.connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum) VALUES (?, ?, ?)",
                    [version, name, checksum],
                )
        self._validate_schema()

    def _validate_schema(self) -> None:
        try:
            rows = self.connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        except duckdb.Error as exc:
            raise SchemaVersionError("database has no experiment schema") from exc
        if not rows or int(rows[-1][0]) != SCHEMA_VERSION:
            found = int(rows[-1][0]) if rows else 0
            raise SchemaVersionError(f"expected schema v{SCHEMA_VERSION}, found v{found}")
        expected = {version: (name, sha256_hex(sql)) for version, name, sql in _MIGRATIONS}
        for version, name, checksum in rows:
            if expected.get(int(version)) != (str(name), str(checksum)):
                raise SchemaVersionError(f"migration {version} does not match this implementation")

    @property
    def schema_version(self) -> int:
        row = self.connection.execute("SELECT max(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)

    def create_experiment(
        self,
        slug: str,
        title: str,
        *,
        description: str | None = None,
        objective: Any | None = None,
    ) -> uuid.UUID:
        definition = {
            "slug": slug,
            "title": title,
            "description": description,
            "objective": {} if objective is None else objective,
        }
        objective_json = _json_or_empty(objective)
        _, digest = canonical_payload(definition)
        experiment_id = _content_uuid("experiment", digest)
        with self.transaction():
            existing = self.connection.execute(
                "SELECT experiment_id, definition_hash FROM experiments WHERE slug = ?", [slug]
            ).fetchone()
            if existing is not None:
                if str(existing[1]) != digest:
                    raise IdentityConflictError(f"experiment slug {slug!r} has different content")
                return _as_uuid(existing[0])
            self.connection.execute(
                """INSERT INTO experiments
                   (experiment_id, slug, title, description, objective_json, definition_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [experiment_id, slug, title, description, objective_json, digest],
            )
        return experiment_id

    def create_run_batch(
        self,
        experiment_id: uuid.UUID | str,
        label: str,
        *,
        config: Any | None = None,
        planned_cell_count: int | None = None,
        host: Any | None = None,
    ) -> uuid.UUID:
        experiment_id = _as_uuid(experiment_id)
        config_json, config_hash = canonical_payload({} if config is None else config)
        batch_id = uuid.uuid4()
        event_id = uuid.uuid4()
        with self.transaction():
            self.connection.execute(
                """INSERT INTO run_batches
                   (batch_id, experiment_id, label, config_json, config_hash,
                    planned_cell_count, host_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    batch_id,
                    experiment_id,
                    label,
                    config_json,
                    config_hash,
                    planned_cell_count,
                    _json_or_empty(host),
                ],
            )
            self.connection.execute(
                """INSERT INTO run_batch_status_events
                   (event_id, batch_id, event_no, status, message)
                   VALUES (?, ?, 1, 'created', NULL)""",
                [event_id, batch_id],
            )
        return batch_id

    def get_batch_status(self, batch_id: uuid.UUID | str) -> BatchStatus:
        batch_id = _as_uuid(batch_id)
        row = self.connection.execute(
            """SELECT batch_id, event_no, status, message, recorded_at
               FROM run_batch_status WHERE batch_id = ?""",
            [batch_id],
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown batch {batch_id}")
        return BatchStatus(_as_uuid(row[0]), int(row[1]), str(row[2]), row[3], row[4])

    def set_batch_status(
        self, batch_id: uuid.UUID | str, status: str, *, message: str | None = None
    ) -> uuid.UUID:
        if status not in _BATCH_STATES:
            raise ValueError(f"invalid batch status {status!r}")
        batch_id = _as_uuid(batch_id)
        with self.transaction():
            current = self.get_batch_status(batch_id)
            if current.status == status:
                row = self.connection.execute(
                    "SELECT event_id FROM run_batch_status_events WHERE batch_id = ? AND event_no = ?",
                    [batch_id, current.event_no],
                ).fetchone()
                return _as_uuid(row[0])
            if current.status in _TERMINAL_BATCH_STATES:
                raise InvalidTransitionError(
                    f"batch {batch_id} is terminal ({current.status}); cannot transition to {status}"
                )
            if status == "created":
                raise InvalidTransitionError("a batch cannot transition back to created")
            event_id = uuid.uuid4()
            self.connection.execute(
                """INSERT INTO run_batch_status_events
                   (event_id, batch_id, event_no, status, message)
                   VALUES (?, ?, ?, ?, ?)""",
                [event_id, batch_id, current.event_no + 1, status, message],
            )
        return event_id

    def start_batch(self, batch_id: uuid.UUID | str, *, message: str | None = None) -> uuid.UUID:
        return self.set_batch_status(batch_id, "running", message=message)

    def complete_batch(self, batch_id: uuid.UUID | str, *, message: str | None = None) -> uuid.UUID:
        return self.set_batch_status(batch_id, "completed", message=message)

    def fail_batch(self, batch_id: uuid.UUID | str, *, message: str | None = None) -> uuid.UUID:
        return self.set_batch_status(batch_id, "failed", message=message)

    def register_boolean_function(
        self,
        name: str,
        n_inputs: int,
        definition: Any,
        *,
        truth_table_hex: str | None = None,
        anf: Any | None = None,
        metadata: Any | None = None,
    ) -> uuid.UUID:
        identity = {"n_inputs": n_inputs, "definition": definition}
        definition_json, digest = canonical_payload(identity)
        function_id = _content_uuid("boolean-function", digest)
        with self.transaction():
            self.connection.execute(
                """INSERT INTO boolean_functions
                   (function_id, canonical_hash, name, n_inputs, definition_json,
                    truth_table_hex, anf_json, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT DO NOTHING""",
                [
                    function_id,
                    digest,
                    name,
                    n_inputs,
                    definition_json,
                    truth_table_hex,
                    None if anf is None else canonical_json(anf),
                    _json_or_empty(metadata),
                ],
            )
            row = self.connection.execute(
                "SELECT function_id FROM boolean_functions WHERE canonical_hash = ?", [digest]
            ).fetchone()
        return _as_uuid(row[0])

    def register_benchmark_case(
        self,
        experiment_id: uuid.UUID | str,
        function_id: uuid.UUID | str,
        case_label: str,
        *,
        suite: str = "default",
        metadata: Any | None = None,
    ) -> uuid.UUID:
        experiment_id = _as_uuid(experiment_id)
        function_id = _as_uuid(function_id)
        identity = {
            "experiment_id": str(experiment_id),
            "function_id": str(function_id),
            "suite": suite,
            "case_label": case_label,
            "metadata": {} if metadata is None else metadata,
        }
        _, digest = canonical_payload(identity)
        case_id = _content_uuid("benchmark-case", digest)
        with self.transaction():
            existing = self.connection.execute(
                """SELECT case_id, definition_hash FROM benchmark_cases
                   WHERE experiment_id = ? AND suite = ? AND case_label = ?""",
                [experiment_id, suite, case_label],
            ).fetchone()
            if existing is not None:
                if str(existing[1]) != digest:
                    raise IdentityConflictError(
                        f"benchmark case {(suite, case_label)!r} has different content"
                    )
                return _as_uuid(existing[0])
            self.connection.execute(
                """INSERT INTO benchmark_cases
                   (case_id, experiment_id, function_id, suite, case_label,
                    metadata_json, definition_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    case_id,
                    experiment_id,
                    function_id,
                    suite,
                    case_label,
                    _json_or_empty(metadata),
                    digest,
                ],
            )
        return case_id

    def register_method_spec(
        self,
        method_name: str,
        spec: Any,
        *,
        model_sha256: str | None = None,
        code_revision: str | None = None,
    ) -> uuid.UUID:
        model_sha256 = _validate_sha256(model_sha256, "model_sha256", optional=True)
        identity = {
            "method_name": method_name,
            "spec": spec,
            "model_sha256": model_sha256,
            "code_revision": code_revision,
        }
        spec_json, digest = canonical_payload(identity)
        method_spec_id = _content_uuid("method-spec", digest)
        with self.transaction():
            self.connection.execute(
                """INSERT INTO method_specs
                   (method_spec_id, method_name, spec_json, spec_hash, model_sha256, code_revision)
                   VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                [method_spec_id, method_name, spec_json, digest, model_sha256, code_revision],
            )
            row = self.connection.execute(
                "SELECT method_spec_id FROM method_specs WHERE spec_hash = ?", [digest]
            ).fetchone()
        return _as_uuid(row[0])

    def register_hardware_target(
        self, target_name: str, num_qubits: int, spec: Any
    ) -> uuid.UUID:
        identity = {"target_name": target_name, "num_qubits": num_qubits, "spec": spec}
        spec_json, digest = canonical_payload(identity)
        target_id = _content_uuid("hardware-target", digest)
        with self.transaction():
            self.connection.execute(
                """INSERT INTO hardware_targets
                   (target_id, target_name, num_qubits, spec_json, spec_hash)
                   VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                [target_id, target_name, num_qubits, spec_json, digest],
            )
            row = self.connection.execute(
                "SELECT target_id FROM hardware_targets WHERE spec_hash = ?", [digest]
            ).fetchone()
        return _as_uuid(row[0])

    def register_transpile_spec(
        self,
        target_id: uuid.UUID | str,
        spec_name: str,
        spec: Any,
    ) -> uuid.UUID:
        target_id = _as_uuid(target_id)
        identity = {"target_id": str(target_id), "spec_name": spec_name, "spec": spec}
        spec_json, digest = canonical_payload(identity)
        transpile_spec_id = _content_uuid("transpile-spec", digest)
        with self.transaction():
            self.connection.execute(
                """INSERT INTO transpile_specs
                   (transpile_spec_id, target_id, spec_name, spec_json, spec_hash)
                   VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                [transpile_spec_id, target_id, spec_name, spec_json, digest],
            )
            row = self.connection.execute(
                "SELECT transpile_spec_id FROM transpile_specs WHERE spec_hash = ?", [digest]
            ).fetchone()
        return _as_uuid(row[0])

    def get_or_create_cell(
        self,
        experiment_id: uuid.UUID | str,
        case_id: uuid.UUID | str,
        method_spec_id: uuid.UUID | str,
        seed: int,
        *,
        batch_id: uuid.UUID | str | None = None,
        ordinal: int | None = None,
    ) -> uuid.UUID:
        experiment_id = _as_uuid(experiment_id)
        case_id = _as_uuid(case_id)
        method_spec_id = _as_uuid(method_spec_id)
        identity = {
            "experiment_id": str(experiment_id),
            "case_id": str(case_id),
            "method_spec_id": str(method_spec_id),
            "seed": int(seed),
        }
        key_json, key_hash = canonical_payload(identity)
        cell_id = _content_uuid("synthesis-cell", key_hash)
        with self.transaction():
            case_row = self.connection.execute(
                "SELECT experiment_id FROM benchmark_cases WHERE case_id = ?", [case_id]
            ).fetchone()
            if case_row is None:
                raise KeyError(f"unknown benchmark case {case_id}")
            if _as_uuid(case_row[0]) != experiment_id:
                raise ExperimentDBError(
                    "benchmark case and synthesis cell belong to different experiments"
                )
            self.connection.execute(
                """INSERT INTO synthesis_cells
                   (cell_id, experiment_id, case_id, method_spec_id, seed,
                    cell_key_json, cell_key_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                [
                    cell_id,
                    experiment_id,
                    case_id,
                    method_spec_id,
                    seed,
                    key_json,
                    key_hash,
                ],
            )
            row = self.connection.execute(
                "SELECT cell_id FROM synthesis_cells WHERE cell_key_hash = ?", [key_hash]
            ).fetchone()
            actual_id = _as_uuid(row[0])
            if batch_id is not None:
                self.attach_cell_to_batch(batch_id, actual_id, ordinal=ordinal)
        return actual_id

    def attach_cell_to_batch(
        self,
        batch_id: uuid.UUID | str,
        cell_id: uuid.UUID | str,
        *,
        ordinal: int | None = None,
    ) -> None:
        batch_id = _as_uuid(batch_id)
        cell_id = _as_uuid(cell_id)
        with self.transaction():
            batch_exp = self.connection.execute(
                "SELECT experiment_id FROM run_batches WHERE batch_id = ?", [batch_id]
            ).fetchone()
            cell_exp = self.connection.execute(
                "SELECT experiment_id FROM synthesis_cells WHERE cell_id = ?", [cell_id]
            ).fetchone()
            if batch_exp is None or cell_exp is None:
                raise KeyError("unknown batch or synthesis cell")
            if _as_uuid(batch_exp[0]) != _as_uuid(cell_exp[0]):
                raise ExperimentDBError("batch and synthesis cell belong to different experiments")
            self.connection.execute(
                """INSERT INTO batch_cells(batch_id, cell_id, ordinal)
                   VALUES (?, ?, ?) ON CONFLICT DO NOTHING""",
                [batch_id, cell_id, ordinal],
            )

    def record_synthesis_attempt(
        self,
        cell_id: uuid.UUID | str,
        batch_id: uuid.UUID | str,
        status: str,
        *,
        selected_method: str | None = None,
        started_at: dt.datetime | None = None,
        finished_at: dt.datetime | None = None,
        runtime_s: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        worker: Any | None = None,
        result: Any | None = None,
        logical_metrics: Mapping[str, Any] | None = None,
        peak_rss_mb: float | None = None,
        peak_system_memory_percent: float | None = None,
        resource_stage_peaks: Any | None = None,
    ) -> AttemptRef:
        if status not in _ATTEMPT_STATES:
            raise ValueError(f"invalid attempt status {status!r}")
        _validate_aware_timestamp(started_at, "started_at")
        _validate_aware_timestamp(finished_at, "finished_at")
        _validate_resource_peak(peak_rss_mb, "peak_rss_mb")
        _validate_resource_peak(
            peak_system_memory_percent,
            "peak_system_memory_percent",
            percent=True,
        )
        cell_id = _as_uuid(cell_id)
        batch_id = _as_uuid(batch_id)
        with self.transaction():
            self.attach_cell_to_batch(batch_id, cell_id)
            row = self.connection.execute(
                """SELECT attempt_no FROM synthesis_attempts
                   WHERE cell_id = ? ORDER BY attempt_no DESC LIMIT 1""",
                [cell_id],
            ).fetchone()
            attempt_no = 1 if row is None else int(row[0]) + 1
            attempt_id = uuid.uuid4()
            self.connection.execute(
                """INSERT INTO synthesis_attempts
                   (attempt_id, cell_id, batch_id, attempt_no, status, selected_method,
                    started_at, finished_at, runtime_s, error_type, error_message,
                    worker_json, result_json, peak_rss_mb,
                    peak_system_memory_percent, resource_stage_peaks_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    attempt_id,
                    cell_id,
                    batch_id,
                    attempt_no,
                    status,
                    selected_method,
                    started_at,
                    finished_at,
                    runtime_s,
                    error_type,
                    error_message,
                    _json_or_empty(worker),
                    _json_or_empty(result),
                    peak_rss_mb,
                    peak_system_memory_percent,
                    _json_or_empty(resource_stage_peaks),
                ],
            )
            if logical_metrics is not None:
                if status != "success":
                    raise ExperimentDBError("logical metrics may only be attached to a success attempt")
                self.record_logical_metrics(attempt_id, logical_metrics)
        return AttemptRef(attempt_id, attempt_no)

    def record_logical_metrics(
        self, synthesis_attempt_id: uuid.UUID | str, metrics: Mapping[str, Any]
    ) -> uuid.UUID:
        synthesis_attempt_id = _as_uuid(synthesis_attempt_id)
        metric_id = uuid.uuid4()
        with self.transaction():
            status_row = self.connection.execute(
                "SELECT status FROM synthesis_attempts WHERE attempt_id = ?", [synthesis_attempt_id]
            ).fetchone()
            if status_row is None:
                raise KeyError(f"unknown synthesis attempt {synthesis_attempt_id}")
            if status_row[0] != "success":
                raise ExperimentDBError("logical metrics require a successful synthesis attempt")
            self.connection.execute(
                """INSERT INTO logical_metrics
                   (logical_metric_id, synthesis_attempt_id, t_count, cnot_count,
                    depth, gate_count, ancilla_count, n_qubits, weighted_score,
                    metric_payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    metric_id,
                    synthesis_attempt_id,
                    _metric_value(metrics, "t_count", "t"),
                    _metric_value(metrics, "cnot_count", "cnot"),
                    _metric_value(metrics, "depth"),
                    _metric_value(metrics, "gate_count", "gates"),
                    _metric_value(metrics, "ancilla_count", "ancilla"),
                    _metric_value(metrics, "n_qubits"),
                    _metric_value(metrics, "weighted_score", "score"),
                    canonical_json(metrics),
                ],
            )
        return metric_id

    def record_mapping_attempt(
        self,
        synthesis_attempt_id: uuid.UUID | str,
        batch_id: uuid.UUID | str,
        transpile_spec_id: uuid.UUID | str,
        status: str,
        *,
        seed_transpiler: int | None = None,
        started_at: dt.datetime | None = None,
        finished_at: dt.datetime | None = None,
        runtime_s: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        result: Any | None = None,
        mapping_metrics: Mapping[str, Any] | None = None,
        native_gate_counts: Mapping[str, int] | None = None,
        peak_rss_mb: float | None = None,
        peak_system_memory_percent: float | None = None,
        total_peak_rss_mb: float | None = None,
        total_peak_system_memory_percent: float | None = None,
        resource_stage_peaks: Any | None = None,
    ) -> AttemptRef:
        if status not in _ATTEMPT_STATES:
            raise ValueError(f"invalid attempt status {status!r}")
        _validate_aware_timestamp(started_at, "started_at")
        _validate_aware_timestamp(finished_at, "finished_at")
        _validate_resource_peak(peak_rss_mb, "peak_rss_mb")
        _validate_resource_peak(
            peak_system_memory_percent,
            "peak_system_memory_percent",
            percent=True,
        )
        _validate_resource_peak(total_peak_rss_mb, "total_peak_rss_mb")
        _validate_resource_peak(
            total_peak_system_memory_percent,
            "total_peak_system_memory_percent",
            percent=True,
        )
        if (
            peak_rss_mb is not None
            and total_peak_rss_mb is not None
            and float(total_peak_rss_mb) < float(peak_rss_mb)
        ):
            raise ValueError("total_peak_rss_mb cannot be smaller than mapping peak_rss_mb")
        if (
            peak_system_memory_percent is not None
            and total_peak_system_memory_percent is not None
            and float(total_peak_system_memory_percent)
            < float(peak_system_memory_percent)
        ):
            raise ValueError(
                "total_peak_system_memory_percent cannot be smaller than mapping peak"
            )
        synthesis_attempt_id = _as_uuid(synthesis_attempt_id)
        batch_id = _as_uuid(batch_id)
        transpile_spec_id = _as_uuid(transpile_spec_id)
        with self.transaction():
            relation = self.connection.execute(
                """SELECT sc.experiment_id, rb.experiment_id, sa.status
                   FROM synthesis_attempts sa
                   JOIN synthesis_cells sc ON sc.cell_id = sa.cell_id
                   JOIN run_batches rb ON rb.batch_id = ?
                   WHERE sa.attempt_id = ?""",
                [batch_id, synthesis_attempt_id],
            ).fetchone()
            if relation is None:
                raise KeyError("unknown synthesis attempt or run batch")
            if _as_uuid(relation[0]) != _as_uuid(relation[1]):
                raise ExperimentDBError("mapping batch belongs to a different experiment")
            if relation[2] != "success":
                raise ExperimentDBError("only successful synthesis attempts can be mapped")
            row = self.connection.execute(
                """SELECT attempt_no FROM mapping_attempts
                   WHERE synthesis_attempt_id = ? AND transpile_spec_id = ?
                   ORDER BY attempt_no DESC LIMIT 1""",
                [synthesis_attempt_id, transpile_spec_id],
            ).fetchone()
            attempt_no = 1 if row is None else int(row[0]) + 1
            mapping_attempt_id = uuid.uuid4()
            self.connection.execute(
                """INSERT INTO mapping_attempts
                   (mapping_attempt_id, synthesis_attempt_id, batch_id,
                    transpile_spec_id, attempt_no, status, seed_transpiler,
                    started_at, finished_at, runtime_s, error_type, error_message,
                    result_json, peak_rss_mb, peak_system_memory_percent,
                    total_peak_rss_mb, total_peak_system_memory_percent,
                    resource_stage_peaks_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    mapping_attempt_id,
                    synthesis_attempt_id,
                    batch_id,
                    transpile_spec_id,
                    attempt_no,
                    status,
                    seed_transpiler,
                    started_at,
                    finished_at,
                    runtime_s,
                    error_type,
                    error_message,
                    _json_or_empty(result),
                    peak_rss_mb,
                    peak_system_memory_percent,
                    total_peak_rss_mb,
                    total_peak_system_memory_percent,
                    _json_or_empty(resource_stage_peaks),
                ],
            )
            if mapping_metrics is not None:
                if status != "success":
                    raise ExperimentDBError("mapping metrics may only be attached to a success attempt")
                self.record_mapping_metrics(mapping_attempt_id, mapping_metrics)
            if native_gate_counts is not None:
                if status != "success":
                    raise ExperimentDBError("native gate counts require a success attempt")
                self.record_native_gate_counts(mapping_attempt_id, native_gate_counts)
        return AttemptRef(mapping_attempt_id, attempt_no)

    def record_mapping_metrics(
        self, mapping_attempt_id: uuid.UUID | str, metrics: Mapping[str, Any]
    ) -> uuid.UUID:
        mapping_attempt_id = _as_uuid(mapping_attempt_id)
        metric_id = uuid.uuid4()
        with self.transaction():
            status_row = self.connection.execute(
                "SELECT status FROM mapping_attempts WHERE mapping_attempt_id = ?",
                [mapping_attempt_id],
            ).fetchone()
            if status_row is None:
                raise KeyError(f"unknown mapping attempt {mapping_attempt_id}")
            if status_row[0] != "success":
                raise ExperimentDBError("mapping metrics require a successful mapping attempt")
            self.connection.execute(
                """INSERT INTO mapping_metrics
                   (mapping_metric_id, mapping_attempt_id, total_gate_count,
                    one_qubit_gate_count, two_qubit_gate_count,
                    native_entangling_count, swap_count, depth, two_qubit_depth,
                    target_violation_count, direction_violation_count,
                    routing_overhead, estimated_error, metric_payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    metric_id,
                    mapping_attempt_id,
                    _metric_value(metrics, "total_gate_count", "total_gates", "gates"),
                    _metric_value(metrics, "one_qubit_gate_count", "oneq_gates"),
                    _metric_value(metrics, "two_qubit_gate_count", "twoq_gates"),
                    _metric_value(metrics, "native_entangling_count", "native_twoq_gates"),
                    _metric_value(metrics, "swap_count", "swaps"),
                    _metric_value(metrics, "depth", "mapped_depth"),
                    _metric_value(metrics, "two_qubit_depth", "twoq_depth"),
                    _metric_value(metrics, "target_violation_count", "target_violations"),
                    _metric_value(metrics, "direction_violation_count", "direction_violations"),
                    _metric_value(metrics, "routing_overhead"),
                    _metric_value(metrics, "estimated_error"),
                    canonical_json(metrics),
                ],
            )
        return metric_id

    def record_native_gate_counts(
        self, mapping_attempt_id: uuid.UUID | str, counts: Mapping[str, int]
    ) -> None:
        mapping_attempt_id = _as_uuid(mapping_attempt_id)
        with self.transaction():
            status_row = self.connection.execute(
                "SELECT status FROM mapping_attempts WHERE mapping_attempt_id = ?",
                [mapping_attempt_id],
            ).fetchone()
            if status_row is None:
                raise KeyError(f"unknown mapping attempt {mapping_attempt_id}")
            if status_row[0] != "success":
                raise ExperimentDBError("native gate counts require a successful mapping attempt")
            rows = [
                (mapping_attempt_id, str(gate_name), int(count))
                for gate_name, count in sorted(counts.items())
            ]
            if rows:
                self.connection.executemany(
                    """INSERT INTO native_gate_counts
                       (mapping_attempt_id, gate_name, gate_count) VALUES (?, ?, ?)""",
                    rows,
                )

    def record_verification(
        self,
        scope: str,
        owner_attempt_id: uuid.UUID | str,
        verifier_name: str,
        status: str,
        *,
        passed: bool | None = None,
        basis_states_checked: int | None = None,
        mismatch_count: int | None = None,
        max_leakage: float | None = None,
        max_phase_error: float | None = None,
        tolerance: float | None = None,
        details: Any | None = None,
    ) -> uuid.UUID:
        if scope not in {"logical", "mapping"}:
            raise ValueError("verification scope must be 'logical' or 'mapping'")
        if status not in _VERIFY_STATES:
            raise ValueError(f"invalid verification status {status!r}")
        if passed is not None and passed != (status == "pass"):
            raise ValueError("passed flag contradicts verification status")
        owner_attempt_id = _as_uuid(owner_attempt_id)
        verification_id = uuid.uuid4()
        synthesis_id = owner_attempt_id if scope == "logical" else None
        mapping_id = owner_attempt_id if scope == "mapping" else None
        with self.transaction():
            self.connection.execute(
                """INSERT INTO verification_results
                   (verification_id, verification_scope, synthesis_attempt_id,
                    mapping_attempt_id, verifier_name, status, passed,
                    basis_states_checked, mismatch_count, max_leakage,
                    max_phase_error, tolerance, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    verification_id,
                    scope,
                    synthesis_id,
                    mapping_id,
                    verifier_name,
                    status,
                    passed,
                    basis_states_checked,
                    mismatch_count,
                    max_leakage,
                    max_phase_error,
                    tolerance,
                    _json_or_empty(details),
                ],
            )
        return verification_id

    def record_artifact(
        self,
        experiment_id: uuid.UUID | str,
        artifact_kind: str,
        path_or_uri: str | pathlib.Path,
        content_sha256: str,
        *,
        batch_id: uuid.UUID | str | None = None,
        synthesis_attempt_id: uuid.UUID | str | None = None,
        mapping_attempt_id: uuid.UUID | str | None = None,
        byte_size: int | None = None,
        mime_type: str | None = None,
        metadata: Any | None = None,
    ) -> uuid.UUID:
        artifact_id = uuid.uuid4()
        content_sha256 = _validate_sha256(content_sha256, "content_sha256")
        with self.transaction():
            self.connection.execute(
                """INSERT INTO artifacts
                   (artifact_id, experiment_id, batch_id, synthesis_attempt_id,
                    mapping_attempt_id, artifact_kind, path_or_uri,
                    content_sha256, byte_size, mime_type, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    artifact_id,
                    _as_uuid(experiment_id),
                    None if batch_id is None else _as_uuid(batch_id),
                    None if synthesis_attempt_id is None else _as_uuid(synthesis_attempt_id),
                    None if mapping_attempt_id is None else _as_uuid(mapping_attempt_id),
                    artifact_kind,
                    pathlib.Path(path_or_uri).as_posix()
                    if isinstance(path_or_uri, pathlib.Path)
                    else str(path_or_uri),
                    content_sha256,
                    byte_size,
                    mime_type,
                    _json_or_empty(metadata),
                ],
            )
        return artifact_id


def open_experiment_db(
    path: str | pathlib.Path = ":memory:", *, read_only: bool = False
) -> ExperimentDB:
    """Open and validate/migrate an experiment database."""

    return ExperimentDB(path, read_only=read_only, initialize=True)


__all__ = [
    "AttemptRef",
    "BatchStatus",
    "ExperimentDB",
    "ExperimentDBError",
    "IdentityConflictError",
    "InvalidTransitionError",
    "SCHEMA_VERSION",
    "SchemaVersionError",
    "canonical_json",
    "canonical_payload",
    "open_experiment_db",
    "sha256_hex",
]
