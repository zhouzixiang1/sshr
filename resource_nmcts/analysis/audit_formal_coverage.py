#!/usr/bin/env python3
"""Read-only coverage audit for the XA-202609 resource-safe core slice.

The audit deliberately treats the DuckDB database and the recovered JSONL files
as two representations of evidence, not as two independent experiments.  A
semantic grid key is:

    benchmark case x requested method x synthesis seed

for the fixed ``cx_full_12`` target and transpiler seed 3.  Database rows must be
canonical successes with passing logical and mapped verification.  Recovered
rows must satisfy the complete hardware-validation-v2/v3 success contract.
Version 3 adds resource telemetry without weakening any semantic or
target-legality gate.

No input file is modified.  The DuckDB connection is opened read-only and its
SHA-256 is checked before and after the query to reject a moving snapshot.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb


SCHEMA_VERSION = "xa202609-formal-coverage-audit-v1"
SUITE_VERSION = "xa202609-final-v1"

METHODS: tuple[str, ...] = (
    "direct_anf",
    "greedy_factor",
    "mcts_factor",
    "sshr_h",
    "sshr_beam",
    "resource_nmcts",
)

# Resource-safe core: the first three seeds in the frozen protocol.
CORE_SEEDS: tuple[int, ...] = (7, 17, 29)
# Formal protocol seeds.  This audit only evaluates their cx_full_12/seed-3
# slice; it does not imply coverage of every formal target/transpiler seed.
FORMAL_SEEDS: tuple[int, ...] = (7, 17, 29, 43, 71)

TARGET_ALIAS = "cx_full"
TARGET_NAME = "cx_full_12"
TARGET_NUM_QUBITS = 12
TRANSPILE_SEED = 3
HARDWARE_ROW_SCHEMA_VERSIONS = frozenset(
    {"hardware-validation-v2", "hardware-validation-v3"}
)
DEFAULT_RECOVERED_GLOB = "results/recovered/final_core_*_v1_ok.jsonl"

# Balanced, resource-safe primary analysis set chosen before this coverage
# calculation: n=3..8, all four benchmark families, easy and hard instances.
PRIMARY20: tuple[str, ...] = (
    "and3",
    "and4",
    "parity4",
    "parity6",
    "maj3",
    "maj5",
    "maj7",
    "thr6_t3",
    "randtt4_s101",
    "randtt4_s103",
    "randtt4_s107",
    "randtt4_s109",
    "randtt5_s113",
    "randtt6_s139",
    "randanf6_s151",
    "randanf6_s157",
    "randanf7_s163",
    "randanf8_s173",
    "aes_sbox_b0",
    "aes_sbox_b7",
)

GridKey = tuple[str, str, int]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _json_bool(row: Mapping[str, Any], key: str) -> bool:
    return row.get(key) is True


def _recovered_verified(row: Mapping[str, Any]) -> bool:
    """Apply the full success gate used for the recovered hardware rows."""

    return all(
        (
            row.get("schema_version") in HARDWARE_ROW_SCHEMA_VERSIONS,
            row.get("status") == "ok",
            row.get("stage") == "complete",
            row.get("error_code") is None,
            _json_bool(row, "result_correct"),
            _json_bool(row, "engine_correct"),
            _json_bool(row, "artifact_consistent"),
            _json_bool(row, "mapped_verify_ok"),
            _json_bool(row, "mapped_verification_complete"),
            _json_bool(row, "mapping_provenance_consistent"),
            row.get("mapped_mismatches") == 0,
            row.get("coupling_violations") == 0,
            row.get("unsupported_instructions") == 0,
        )
    )


def _load_suite(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("suite_version") != SUITE_VERSION:
        raise ValueError(
            f"suite version is {manifest.get('suite_version')!r}, expected {SUITE_VERSION!r}"
        )
    cases = manifest.get("cases", [])
    if len(cases) != 30 or manifest.get("case_count") != 30:
        raise ValueError("the frozen final suite must contain exactly 30 cases")
    by_id = {str(case["case_id"]): dict(case) for case in cases}
    if len(by_id) != len(cases):
        raise ValueError("duplicate case_id in benchmark manifest")
    missing_primary = sorted(set(PRIMARY20) - set(by_id))
    if missing_primary:
        raise ValueError(f"PRIMARY20 contains unknown cases: {missing_primary}")
    return manifest, by_id


DB_CANONICAL_SQL = """
SELECT
    cmr.case_label AS case_id,
    json_extract_string(bf.metadata_json, '$.function_truth_hash') AS function_truth_hash,
    json_extract_string(ms.spec_json, '$.spec.requested_method') AS requested_method,
    cmr.seed AS synthesis_seed,
    cmr.target_name,
    ht.num_qubits AS target_num_qubits,
    json_extract_string(ht.spec_json, '$.spec.runner_alias') AS target_alias,
    cmr.seed_transpiler AS transpile_seed,
    cmr.synthesis_attempt_id::VARCHAR AS synthesis_attempt_id,
    cmr.mapping_attempt_id::VARCHAR AS mapping_attempt_id,
    cmr.transpile_spec_id::VARCHAR AS transpile_spec_id
FROM canonical_mapping_results AS cmr
JOIN boolean_functions AS bf ON bf.function_id = cmr.function_id
JOIN method_specs AS ms ON ms.method_spec_id = cmr.method_spec_id
JOIN hardware_targets AS ht ON ht.target_id = cmr.target_id
WHERE cmr.suite = ?
  AND cmr.target_name = ?
  AND ht.num_qubits = ?
  AND json_extract_string(ht.spec_json, '$.spec.runner_alias') = ?
  AND cmr.seed_transpiler = ?
  AND cmr.logical_verified
  AND cmr.mapping_verified
  AND coalesce(cmr.target_violation_count, 0) = 0
  AND coalesce(cmr.direction_violation_count, 0) = 0
  AND EXISTS (
      SELECT 1
      FROM verification_results AS vr
      WHERE vr.mapping_attempt_id = cmr.mapping_attempt_id
        AND vr.status = 'pass'
        AND vr.passed
        AND coalesce(vr.mismatch_count, 0) = 0
  )
  AND NOT EXISTS (
      SELECT 1
      FROM verification_results AS vr
      WHERE vr.mapping_attempt_id = cmr.mapping_attempt_id
        AND (
            vr.status IN ('fail', 'error')
            OR vr.passed = false
            OR coalesce(vr.mismatch_count, 0) <> 0
        )
  )
ORDER BY case_id, requested_method, synthesis_seed, transpile_spec_id
"""


DB_ATTEMPTS_SQL = """
SELECT
    bc.case_label AS case_id,
    json_extract_string(bf.metadata_json, '$.function_truth_hash') AS function_truth_hash,
    json_extract_string(ms.spec_json, '$.spec.requested_method') AS requested_method,
    sc.seed AS synthesis_seed,
    ht.target_name,
    ht.num_qubits AS target_num_qubits,
    json_extract_string(ht.spec_json, '$.spec.runner_alias') AS target_alias,
    ma.seed_transpiler AS transpile_seed,
    sa.attempt_id::VARCHAR AS synthesis_attempt_id,
    ma.mapping_attempt_id::VARCHAR AS mapping_attempt_id,
    ma.transpile_spec_id::VARCHAR AS transpile_spec_id
FROM mapping_attempts AS ma
JOIN synthesis_attempts AS sa ON sa.attempt_id = ma.synthesis_attempt_id
JOIN synthesis_cells AS sc ON sc.cell_id = sa.cell_id
JOIN benchmark_cases AS bc ON bc.case_id = sc.case_id
JOIN boolean_functions AS bf ON bf.function_id = bc.function_id
JOIN method_specs AS ms ON ms.method_spec_id = sc.method_spec_id
JOIN transpile_specs AS ts ON ts.transpile_spec_id = ma.transpile_spec_id
JOIN hardware_targets AS ht ON ht.target_id = ts.target_id
JOIN logical_verification_summary AS lvs ON lvs.synthesis_attempt_id = sa.attempt_id
JOIN mapping_verification_summary AS mvs ON mvs.mapping_attempt_id = ma.mapping_attempt_id
LEFT JOIN mapping_metrics AS mm ON mm.mapping_attempt_id = ma.mapping_attempt_id
WHERE bc.suite = ?
  AND ht.target_name = ?
  AND ht.num_qubits = ?
  AND json_extract_string(ht.spec_json, '$.spec.runner_alias') = ?
  AND ma.seed_transpiler = ?
  AND sa.status = 'success'
  AND ma.status = 'success'
  AND lvs.verified
  AND mvs.verified
  AND coalesce(mm.target_violation_count, 0) = 0
  AND coalesce(mm.direction_violation_count, 0) = 0
  AND EXISTS (
      SELECT 1
      FROM verification_results AS vr
      WHERE vr.mapping_attempt_id = ma.mapping_attempt_id
        AND vr.status = 'pass'
        AND vr.passed
        AND coalesce(vr.mismatch_count, 0) = 0
  )
  AND NOT EXISTS (
      SELECT 1
      FROM verification_results AS vr
      WHERE vr.mapping_attempt_id = ma.mapping_attempt_id
        AND (
            vr.status IN ('fail', 'error')
            OR vr.passed = false
            OR coalesce(vr.mismatch_count, 0) <> 0
        )
  )
ORDER BY case_id, requested_method, synthesis_seed, transpile_spec_id,
         synthesis_attempt_id, mapping_attempt_id
"""


def _fetch_dicts(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    cursor = connection.execute(
        query,
        [SUITE_VERSION, TARGET_NAME, TARGET_NUM_QUBITS, TARGET_ALIAS, TRANSPILE_SEED],
    )
    columns = [str(description[0]) for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _load_db_rows(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    before = _sha256_file(path)
    connection = duckdb.connect(str(path), read_only=True)
    try:
        canonical = _fetch_dicts(connection, DB_CANONICAL_SQL)
        attempts = _fetch_dicts(connection, DB_ATTEMPTS_SQL)
    finally:
        connection.close()
    after = _sha256_file(path)
    if before != after:
        raise RuntimeError(
            "DuckDB changed during the read-only audit; rerun against a stable snapshot"
        )
    return canonical, attempts


def _load_recovered(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    parse_errors.append(
                        {"path": str(path), "line": line_no, "error": str(exc)}
                    )
                    continue
                row["_source_path"] = str(path)
                row["_source_line"] = line_no
                rows.append(row)
    return rows, parse_errors


def _resolve_recovered_paths(
    recovered_globs: Sequence[str] | None,
    recovered_jsonls: Sequence[Path] | None,
    *,
    project: Path,
) -> list[Path]:
    """Resolve strict, deterministic and path-deduplicated JSONL inputs.

    With no selectors, preserve the historical four-file input *pattern*.  A
    caller that supplies any glob or explicit JSONL opts into exactly the union
    of those selectors.  Every selector must resolve successfully so a typo
    cannot silently produce an incomplete coverage report.
    """

    globs = list(recovered_globs or ())
    explicit = list(recovered_jsonls or ())
    if not globs and not explicit:
        globs = [str(project / DEFAULT_RECOVERED_GLOB)]

    selected: list[Path] = []
    for pattern in globs:
        matches = sorted(Path(match) for match in glob.glob(pattern))
        if not matches:
            raise FileNotFoundError(f"recovered glob matched no files: {pattern!r}")
        selected.extend(matches)
    selected.extend(explicit)

    deduplicated: dict[str, Path] = {}
    for candidate in selected:
        resolved = candidate.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"recovered JSONL does not exist: {candidate}")
        if not resolved.is_file():
            raise FileNotFoundError(f"recovered JSONL is not a file: {candidate}")
        # Deduplicate under the host filesystem's normal case semantics (for
        # example, case-insensitive NTFS and case-sensitive Linux filesystems).
        key = os.path.normcase(str(resolved))
        deduplicated.setdefault(key, resolved)

    if not deduplicated:
        raise FileNotFoundError("no recovered JSONL files were selected")
    return sorted(deduplicated.values(), key=lambda path: os.path.normcase(str(path)))


def _key(row: Mapping[str, Any]) -> GridKey:
    return (
        str(row["case_id"]),
        str(row["requested_method"]),
        int(row["synthesis_seed"]),
    )


def _db_row_in_manifest(
    row: Mapping[str, Any], cases: Mapping[str, Mapping[str, Any]]
) -> bool:
    case = cases.get(str(row.get("case_id")))
    return bool(
        case
        and row.get("function_truth_hash") == case.get("function_key")
        and row.get("target_name") == TARGET_NAME
        and row.get("target_num_qubits") == TARGET_NUM_QUBITS
        and row.get("target_alias") == TARGET_ALIAS
        and row.get("transpile_seed") == TRANSPILE_SEED
    )


def _normalise_recovered(
    row: Mapping[str, Any], cases: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any] | None:
    case_id = str(row.get("function_id", ""))
    requested_method = str(row.get("requested_method") or row.get("method") or "")
    case = cases.get(case_id)
    if not case:
        return None
    if row.get("benchmark_suite") != SUITE_VERSION:
        return None
    if row.get("function_truth_hash") != case.get("function_key"):
        return None
    if row.get("target_name") != TARGET_ALIAS or row.get("target_id") != TARGET_NAME:
        return None
    if row.get("target_num_qubits") != TARGET_NUM_QUBITS:
        return None
    if row.get("transpile_seed") != TRANSPILE_SEED:
        return None
    if not _recovered_verified(row):
        return None
    return {
        "case_id": case_id,
        "function_truth_hash": row.get("function_truth_hash"),
        "requested_method": requested_method,
        "synthesis_seed": int(row["synthesis_seed"]),
        "target_name": row.get("target_id"),
        "target_num_qubits": row.get("target_num_qubits"),
        "target_alias": row.get("target_name"),
        "transpile_seed": row.get("transpile_seed"),
        "record_key": row.get("record_key"),
        "source_path": row.get("_source_path"),
        "source_line": row.get("_source_line"),
    }


def _grid(case_ids: Iterable[str], seeds: Sequence[int]) -> list[GridKey]:
    return [
        (case_id, method, seed)
        for case_id in case_ids
        for method in METHODS
        for seed in seeds
    ]


def _coverage(
    keys: Sequence[GridKey], db_counts: Counter[GridKey], recovered_counts: Counter[GridKey]
) -> dict[str, Any]:
    key_set = set(keys)
    db = key_set & set(db_counts)
    recovered = key_set & set(recovered_counts)
    union = db | recovered
    return {
        "intended_cells": len(key_set),
        "database_verified_cells": len(db),
        "recovered_verified_cells": len(recovered),
        "union_verified_cells": len(union),
        "missing_cells": len(key_set - union),
        "coverage_fraction": len(union) / len(key_set) if key_set else None,
        "database_only_cells": len(db - recovered),
        "recovered_only_cells": len(recovered - db),
        "source_overlap_cells": len(db & recovered),
    }


def _group_coverage(
    all_keys: Sequence[GridKey],
    db_counts: Counter[GridKey],
    recovered_counts: Counter[GridKey],
    field: str,
    cases: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[Any, list[GridKey]] = defaultdict(list)
    for key in all_keys:
        case_id, method, seed = key
        if field == "seed":
            value: Any = seed
        elif field == "method":
            value = method
        elif field == "family":
            value = cases[case_id]["family"]
        else:
            raise ValueError(field)
        grouped[value].append(key)
    output = []
    for value in sorted(grouped, key=str):
        item = {field: value}
        item.update(_coverage(grouped[value], db_counts, recovered_counts))
        output.append(item)
    return output


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _protocol_excerpt(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    synthesis = next((line for line in lines if "synthesis seeds" in line), None)
    transpile = next((line for line in lines if "transpiler seeds" in line), None)
    targets = [line for line in lines if line.startswith("- `cx_")]
    return {
        "path": str(path),
        "synthesis_seed_line": synthesis,
        "transpiler_seed_line": transpile,
        "cx_target_lines": targets,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", type=Path, default=project / "results" / "competition_experiments.duckdb"
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=project / "submission_competition" / "benchmark_suite_v1.json",
    )
    parser.add_argument(
        "--recovered-glob",
        action="append",
        dest="recovered_globs",
        metavar="PATTERN",
        help=(
            "Recovered JSONL glob; repeat to union multiple groups. If neither this "
            "nor --recovered-jsonl is supplied, use results/recovered/"
            "final_core_*_v1_ok.jsonl. Every supplied glob must match at least one file."
        ),
    )
    parser.add_argument(
        "--recovered-jsonl",
        action="append",
        dest="recovered_jsonls",
        type=Path,
        metavar="PATH",
        help=(
            "Explicit recovered JSONL path; repeat as needed. Inputs overlapping with "
            "each other or with --recovered-glob are read once."
        ),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=project / "submission_competition" / "EXPERIMENT_PROTOCOL.md",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=project / "submission_competition"
    )
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args()
    project = Path(__file__).resolve().parents[1]
    suite_manifest, cases = _load_suite(args.suite)
    case_order = [str(case["case_id"]) for case in suite_manifest["cases"]]
    recovered_paths = _resolve_recovered_paths(
        args.recovered_globs,
        args.recovered_jsonls,
        project=project,
    )

    db_sha_before = _sha256_file(args.db)
    canonical_db_rows, attempt_db_rows = _load_db_rows(args.db)
    db_sha_after = _sha256_file(args.db)
    if db_sha_before != db_sha_after:
        raise RuntimeError("database hash changed after snapshot validation")

    recovered_raw, parse_errors = _load_recovered(recovered_paths)
    if parse_errors:
        raise ValueError(f"recovered JSONL parse errors: {parse_errors}")
    recovered_rows = [
        normalised
        for row in recovered_raw
        if (normalised := _normalise_recovered(row, cases)) is not None
    ]

    db_valid_manifest = [row for row in canonical_db_rows if _db_row_in_manifest(row, cases)]
    attempt_valid_manifest = [row for row in attempt_db_rows if _db_row_in_manifest(row, cases)]

    db_formal_rows = [
        row
        for row in db_valid_manifest
        if row["requested_method"] in METHODS and row["synthesis_seed"] in FORMAL_SEEDS
    ]
    recovered_formal_rows = [
        row
        for row in recovered_rows
        if row["requested_method"] in METHODS and row["synthesis_seed"] in FORMAL_SEEDS
    ]
    attempt_formal_rows = [
        row
        for row in attempt_valid_manifest
        if row["requested_method"] in METHODS and row["synthesis_seed"] in FORMAL_SEEDS
    ]

    db_core_rows = [row for row in db_formal_rows if row["synthesis_seed"] in CORE_SEEDS]
    recovered_core_rows = [
        row for row in recovered_formal_rows if row["synthesis_seed"] in CORE_SEEDS
    ]
    attempt_core_rows = [
        row for row in attempt_formal_rows if row["synthesis_seed"] in CORE_SEEDS
    ]

    db_counts: Counter[GridKey] = Counter(_key(row) for row in db_core_rows)
    recovered_counts: Counter[GridKey] = Counter(_key(row) for row in recovered_core_rows)
    attempt_counts: Counter[GridKey] = Counter(_key(row) for row in attempt_core_rows)
    db_formal_counts: Counter[GridKey] = Counter(_key(row) for row in db_formal_rows)
    recovered_formal_counts: Counter[GridKey] = Counter(
        _key(row) for row in recovered_formal_rows
    )

    core_grid = _grid(case_order, CORE_SEEDS)
    formal_grid = _grid(case_order, FORMAL_SEEDS)
    primary_core_grid = _grid(PRIMARY20, CORE_SEEDS)
    primary_formal_grid = _grid(PRIMARY20, FORMAL_SEEDS)

    full_core_coverage = _coverage(core_grid, db_counts, recovered_counts)
    full_formal_coverage = _coverage(
        formal_grid, db_formal_counts, recovered_formal_counts
    )
    primary_core_coverage = _coverage(primary_core_grid, db_counts, recovered_counts)
    primary_formal_coverage = _coverage(
        primary_formal_grid, db_formal_counts, recovered_formal_counts
    )

    union_keys = set(db_counts) | set(recovered_counts)
    core_key_set = set(core_grid)
    formal_union_keys = set(db_formal_counts) | set(recovered_formal_counts)
    formal_key_set = set(formal_grid)
    missing_core = sorted(core_key_set - union_keys)
    missing_formal = sorted(formal_key_set - formal_union_keys)

    case_rows: list[dict[str, Any]] = []
    for case_id in case_order:
        case_keys = _grid([case_id], CORE_SEEDS)
        coverage = _coverage(case_keys, db_counts, recovered_counts)
        row: dict[str, Any] = {
            "case_id": case_id,
            "family": cases[case_id]["family"],
            "n_inputs": cases[case_id]["n_inputs"],
            "anf_terms": cases[case_id]["anf_terms"],
            "primary20": case_id in PRIMARY20,
            **coverage,
        }
        for seed in CORE_SEEDS:
            seed_keys = _grid([case_id], [seed])
            row[f"seed_{seed}_verified"] = _coverage(
                seed_keys, db_counts, recovered_counts
            )["union_verified_cells"]
        case_rows.append(row)

    missing_rows = [
        {
            "analysis_scope": "formal5" if seed in (43, 71) else "core3",
            "case_id": case_id,
            "family": cases[case_id]["family"],
            "n_inputs": cases[case_id]["n_inputs"],
            "anf_terms": cases[case_id]["anf_terms"],
            "primary20": case_id in PRIMARY20,
            "requested_method": method,
            "synthesis_seed": seed,
            "target_alias": TARGET_ALIAS,
            "target_name": TARGET_NAME,
            "target_num_qubits": TARGET_NUM_QUBITS,
            "transpile_seed": TRANSPILE_SEED,
            "database_verified_count": db_formal_counts[(case_id, method, seed)],
            "recovered_verified_count": recovered_formal_counts[(case_id, method, seed)],
        }
        for case_id, method, seed in missing_formal
    ]

    primary_recovery_groups: list[dict[str, Any]] = []
    for case_id in PRIMARY20:
        for seed in CORE_SEEDS:
            missing_methods = [
                method
                for method in METHODS
                if (case_id, method, seed) not in union_keys
            ]
            if not missing_methods:
                continue
            primary_recovery_groups.append(
                {
                    "case_id": case_id,
                    "family": cases[case_id]["family"],
                    "n_inputs": cases[case_id]["n_inputs"],
                    "anf_terms": cases[case_id]["anf_terms"],
                    "synthesis_seed": seed,
                    "missing_method_count": len(missing_methods),
                    "missing_methods": ",".join(missing_methods),
                    "target_alias": TARGET_ALIAS,
                    "target_name": TARGET_NAME,
                    "transpile_seed": TRANSPILE_SEED,
                }
            )

    duplicate_rows: list[dict[str, Any]] = []
    for source, counter in (
        ("database_canonical", db_counts),
        ("database_verified_attempts", attempt_counts),
        ("recovered_jsonl", recovered_counts),
    ):
        for (case_id, method, seed), count in sorted(counter.items()):
            if count > 1:
                duplicate_rows.append(
                    {
                        "duplicate_kind": source,
                        "case_id": case_id,
                        "requested_method": method,
                        "synthesis_seed": seed,
                        "count": count,
                        "extra_rows": count - 1,
                        "note": "multiple rows within one evidence representation",
                    }
                )
    for case_id, method, seed in sorted(set(db_counts) & set(recovered_counts)):
        duplicate_rows.append(
            {
                "duplicate_kind": "database_recovered_overlap",
                "case_id": case_id,
                "requested_method": method,
                "synthesis_seed": seed,
                "count": db_counts[(case_id, method, seed)]
                + recovered_counts[(case_id, method, seed)],
                "extra_rows": min(
                    db_counts[(case_id, method, seed)],
                    recovered_counts[(case_id, method, seed)],
                ),
                "note": "same semantic cell represented in DB and source JSONL; not independent coverage",
            }
        )

    core_by_seed = _group_coverage(
        core_grid, db_counts, recovered_counts, "seed", cases
    )
    core_by_method = _group_coverage(
        core_grid, db_counts, recovered_counts, "method", cases
    )
    core_by_family = _group_coverage(
        core_grid, db_counts, recovered_counts, "family", cases
    )

    recovered_all_seed_distribution = Counter(
        int(row["synthesis_seed"])
        for row in recovered_rows
        if row["requested_method"] in METHODS
    )
    db_all_seed_distribution = Counter(
        int(row["synthesis_seed"])
        for row in db_valid_manifest
        if row["requested_method"] in METHODS
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "formal_coverage_audit.json"
    case_csv_path = output_dir / "formal_coverage_by_case.csv"
    missing_csv_path = output_dir / "formal_coverage_missing.csv"
    duplicate_csv_path = output_dir / "formal_coverage_duplicates.csv"
    recovery_csv_path = output_dir / "formal_coverage_primary20_recovery_plan.csv"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": {
            "suite_version": SUITE_VERSION,
            "suite_id": suite_manifest.get("suite_id"),
            "case_count": len(case_order),
            "methods": list(METHODS),
            "core_synthesis_seeds": list(CORE_SEEDS),
            "formal_synthesis_seeds": list(FORMAL_SEEDS),
            "target_alias": TARGET_ALIAS,
            "actual_target_name": TARGET_NAME,
            "actual_target_num_qubits": TARGET_NUM_QUBITS,
            "transpile_seed": TRANSPILE_SEED,
            "scope_note": (
                "This is a resource-safe cx_full_12/transpile-seed-3 slice. It is not "
                "coverage of all four targets or all three transpiler seeds in the formal protocol."
            ),
        },
        "protocol_alignment": {
            "frozen_protocol": _protocol_excerpt(args.protocol),
            "core_seeds_are_first_three_formal_seeds": list(CORE_SEEDS)
            == list(FORMAL_SEEDS[:3]),
            "missing_formal_seed_extension": [43, 71],
            "target_deviation": {
                "actual": TARGET_NAME,
                "frozen_protocol": "cx_full_19",
                "material": True,
                "interpretation": (
                    "Current evidence is a 12-qubit resource-safe proxy and must not be "
                    "presented as the frozen 19-qubit target."
                ),
            },
        },
        "sources": {
            "database": {
                "path": _rel(args.db, project),
                "sha256": db_sha_after,
                "canonical_verified_rows_in_fixed_slice_all_methods_seeds": len(
                    canonical_db_rows
                ),
                "manifest_matched_rows": len(db_valid_manifest),
                "core_method_seed_rows": len(db_core_rows),
                "core_unique_cells": len(db_counts),
                "formal5_method_seed_rows": len(db_formal_rows),
                "formal5_unique_cells": len(db_formal_counts),
                "core_duplicate_canonical_extra_rows": sum(
                    max(0, count - 1) for count in db_counts.values()
                ),
                "verified_attempt_rows_in_fixed_slice": len(attempt_db_rows),
                "core_duplicate_attempt_extra_rows": sum(
                    max(0, count - 1) for count in attempt_counts.values()
                ),
                "six_method_seed_distribution": {
                    str(seed): count
                    for seed, count in sorted(db_all_seed_distribution.items())
                },
            },
            "recovered_jsonl": {
                "files": [
                    {
                        "path": _rel(path, project),
                        "sha256": _sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                    for path in recovered_paths
                ],
                "raw_rows": len(recovered_raw),
                "parse_error_count": len(parse_errors),
                "strict_verified_manifest_target_rows": len(recovered_rows),
                "core_method_seed_rows": len(recovered_core_rows),
                "core_unique_cells": len(recovered_counts),
                "formal5_method_seed_rows": len(recovered_formal_rows),
                "formal5_unique_cells": len(recovered_formal_counts),
                "core_duplicate_extra_rows": sum(
                    max(0, count - 1) for count in recovered_counts.values()
                ),
                "six_method_seed_distribution": {
                    str(seed): count
                    for seed, count in sorted(recovered_all_seed_distribution.items())
                },
            },
        },
        "coverage": {
            "full30_core3": full_core_coverage,
            "full30_formal5_same_hardware_slice": full_formal_coverage,
            "primary20_core3": primary_core_coverage,
            "primary20_formal5_same_hardware_slice": primary_formal_coverage,
            "full30_core3_by_seed": core_by_seed,
            "full30_core3_by_method": core_by_method,
            "full30_core3_by_family": core_by_family,
            "full30_core3_missing_cells": len(missing_core),
            "full30_formal5_missing_cells": len(missing_formal),
        },
        "duplicates": {
            "database_canonical_duplicate_keys": sum(
                count > 1 for count in db_counts.values()
            ),
            "database_verified_attempt_duplicate_keys": sum(
                count > 1 for count in attempt_counts.values()
            ),
            "recovered_duplicate_keys": sum(
                count > 1 for count in recovered_counts.values()
            ),
            "database_recovered_overlap_keys": len(set(db_counts) & set(recovered_counts)),
            "interpretation": (
                "DB/JSONL overlap is provenance overlap, because recovered rows were ingested; "
                "it is deduplicated in union coverage and is not an independent replicate."
            ),
        },
        "recommended_primary20": {
            "case_ids": list(PRIMARY20),
            "selection_basis": (
                "Balanced pre-analysis resource-safe slice spanning n=3..8, structured, "
                "random-truth, random-ANF and AES families, with both easy and high-complexity cases."
            ),
            "family_counts": dict(
                sorted(Counter(cases[case_id]["family"] for case_id in PRIMARY20).items())
            ),
            "core3": primary_core_coverage,
            "formal5_same_hardware_slice": primary_formal_coverage,
            "core3_recovery_group_count": len(primary_recovery_groups),
            "core3_recovery_groups": primary_recovery_groups,
        },
        "case_coverage": case_rows,
        "missing_cells": missing_rows,
        "output_files": {
            "json": _rel(json_path, project),
            "case_csv": _rel(case_csv_path, project),
            "missing_csv": _rel(missing_csv_path, project),
            "duplicates_csv": _rel(duplicate_csv_path, project),
            "primary20_recovery_csv": _rel(recovery_csv_path, project),
        },
    }

    _write_csv(
        case_csv_path,
        case_rows,
        (
            "case_id",
            "family",
            "n_inputs",
            "anf_terms",
            "primary20",
            "intended_cells",
            "database_verified_cells",
            "recovered_verified_cells",
            "union_verified_cells",
            "missing_cells",
            "coverage_fraction",
            "database_only_cells",
            "recovered_only_cells",
            "source_overlap_cells",
            "seed_7_verified",
            "seed_17_verified",
            "seed_29_verified",
        ),
    )
    _write_csv(
        missing_csv_path,
        missing_rows,
        (
            "analysis_scope",
            "case_id",
            "family",
            "n_inputs",
            "anf_terms",
            "primary20",
            "requested_method",
            "synthesis_seed",
            "target_alias",
            "target_name",
            "target_num_qubits",
            "transpile_seed",
            "database_verified_count",
            "recovered_verified_count",
        ),
    )
    _write_csv(
        duplicate_csv_path,
        duplicate_rows,
        (
            "duplicate_kind",
            "case_id",
            "requested_method",
            "synthesis_seed",
            "count",
            "extra_rows",
            "note",
        ),
    )
    _write_csv(
        recovery_csv_path,
        primary_recovery_groups,
        (
            "case_id",
            "family",
            "n_inputs",
            "anf_terms",
            "synthesis_seed",
            "missing_method_count",
            "missing_methods",
            "target_alias",
            "target_name",
            "transpile_seed",
        ),
    )
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "full30_core3": full_core_coverage,
        "primary20_core3": primary_core_coverage,
        "full30_formal5_same_hardware_slice": full_formal_coverage,
        "primary20_formal5_same_hardware_slice": primary_formal_coverage,
        "outputs": report["output_files"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
