#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a read-only inventory of *legacy* CSV result files.

This utility deliberately does **not** build the canonical experiment database.
It recursively inventories historical CSV files into a separate DuckDB with a
stable, loss-minimising schema:

``source_files``
    One row per CSV source, including content and schema hashes, file metadata,
    relative provenance, row count, and import status.

``raw_rows_json``
    One row per legacy CSV record.  The exact parsed cell vector and a keyed JSON
    representation are retained.  No table names are derived from CSV headers or
    file names, so adding a new legacy schema cannot change the database layout.

The output is first built transactionally in a temporary DuckDB in the target
directory and is published with ``os.replace`` only after validation succeeds.
Existing outputs are never overwritten unless ``--force`` is paired with an
explicit ``--output``.  The canonical names ``experiments.duckdb`` and
``hardware_validation.duckdb`` are unconditionally forbidden.

Default output: ``results/legacy_csv_inventory.duckdb``.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "results"
DEFAULT_OUTPUT_NAME = "legacy_csv_inventory.duckdb"
PROTECTED_DATABASE_NAMES = frozenset(
    {"experiments.duckdb", "hardware_validation.duckdb"}
)
INVENTORY_FORMAT = "resource-nmcts-legacy-csv-inventory"
INVENTORY_SCHEMA_VERSION = "1"
LEGACY_DATASET_ROLE = "legacy_wide_csv"
INSERT_BATCH_SIZE = 1_000
# Several high-dimensional legacy runs store complete truth tables or term
# payloads in one CSV cell.  Python's 128 KiB default would silently turn
# those sources into partial/error inventories.  The bound remains finite to
# avoid accepting unreasonably large accidental fields.
CSV_FIELD_SIZE_LIMIT = 64 * 1024 * 1024


class UnsafeOutputError(ValueError):
    """Raised when an output could touch a canonical or ambiguous database."""


@dataclass(frozen=True)
class BuildSummary:
    """Small, serialisable result returned after an inventory is published."""

    output_path: Path
    source_root: Path
    source_count: int
    row_count: int
    error_count: int


def _utc_from_ns(timestamp_ns: int) -> str:
    return (
        dt.datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=dt.timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=isinstance(value, dict),
    )


def schema_hash(header: Sequence[str]) -> str:
    """Return the SHA-256 of the exact ordered CSV header signature."""

    payload = _stable_json(list(header)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_id(relative_path: str, content_sha256: str) -> str:
    payload = f"{relative_path}\0{content_sha256}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalise_header_keys(header: Sequence[str]) -> list[str]:
    """Create unique JSON keys while retaining the exact header separately."""

    keys: list[str] = []
    counts: dict[str, int] = {}
    used: set[str] = set()
    for index, original in enumerate(header, start=1):
        base = original if original else f"__unnamed_column_{index}"
        occurrence = counts.get(base, 0) + 1
        counts[base] = occurrence
        candidate = base if occurrence == 1 else f"{base}__duplicate_{occurrence}"
        while candidate in used:
            occurrence += 1
            counts[base] = occurrence
            candidate = f"{base}__duplicate_{occurrence}"
        used.add(candidate)
        keys.append(candidate)
    return keys


def _row_object(keys: Sequence[str], cells: Sequence[str]) -> dict[str, object]:
    row: dict[str, object] = {
        key: cells[index] if index < len(cells) else None
        for index, key in enumerate(keys)
    }
    if len(cells) > len(keys):
        row["__extra_cells__"] = list(cells[len(keys) :])
    return row


def discover_csv_files(source_root: Path) -> list[Path]:
    """Recursively discover CSV files in deterministic relative-path order."""

    source_root = Path(source_root).resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"CSV source root is not a directory: {source_root}")
    files = [
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".csv"
    ]
    return sorted(
        files,
        key=lambda path: path.relative_to(source_root).as_posix().casefold(),
    )


def _resolve_output(
    source_root: Path,
    output: Path | None,
    *,
    force: bool,
) -> tuple[Path, bool]:
    explicit_output = output is not None
    resolved = (
        Path(output).expanduser().resolve()
        if explicit_output
        else (source_root / DEFAULT_OUTPUT_NAME).resolve()
    )

    if resolved.name.casefold() in PROTECTED_DATABASE_NAMES:
        raise UnsafeOutputError(
            f"refusing protected canonical database name: {resolved.name}"
        )
    if resolved.suffix.casefold() != ".duckdb":
        raise UnsafeOutputError(f"output must have a .duckdb suffix: {resolved}")
    if force and not explicit_output:
        raise UnsafeOutputError(
            "--force requires an explicit --output; the default target is not "
            "eligible for forced replacement"
        )
    if resolved.exists() and not force:
        raise FileExistsError(
            f"output already exists (use explicit --output with --force): {resolved}"
        )
    if resolved.exists() and not resolved.is_file():
        raise UnsafeOutputError(f"output exists and is not a regular file: {resolved}")
    return resolved, explicit_output


def _create_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE inventory_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE source_files (
            source_id VARCHAR PRIMARY KEY,
            relative_path VARCHAR UNIQUE NOT NULL,
            file_name VARCHAR NOT NULL,
            sha256 VARCHAR NOT NULL,
            size_bytes UBIGINT NOT NULL,
            mtime_ns BIGINT NOT NULL,
            mtime_utc VARCHAR NOT NULL,
            schema_hash VARCHAR NOT NULL,
            header_json VARCHAR NOT NULL,
            normalised_header_json VARCHAR NOT NULL,
            column_count INTEGER NOT NULL,
            row_count UBIGINT NOT NULL,
            import_status VARCHAR NOT NULL,
            import_note VARCHAR NOT NULL,
            dataset_role VARCHAR NOT NULL,
            is_legacy BOOLEAN NOT NULL,
            imported_at_utc VARCHAR NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE raw_rows_json (
            source_id VARCHAR NOT NULL,
            relative_path VARCHAR NOT NULL,
            row_number UBIGINT NOT NULL,
            row_json VARCHAR NOT NULL,
            raw_cells_json VARCHAR NOT NULL,
            width_matches_schema BOOLEAN NOT NULL,
            dataset_role VARCHAR NOT NULL,
            is_legacy BOOLEAN NOT NULL,
            PRIMARY KEY (source_id, row_number)
        )
        """
    )
    con.execute(
        """
        CREATE VIEW legacy_schema_summary AS
        SELECT
            schema_hash,
            COUNT(*) AS source_count,
            SUM(row_count) AS row_count,
            MIN(column_count) AS column_count,
            LIST(relative_path ORDER BY relative_path) AS source_paths
        FROM source_files
        GROUP BY schema_hash
        """
    )


def _insert_batches(
    con: duckdb.DuckDBPyConnection,
    rows: Iterable[tuple[object, ...]],
) -> int:
    batch: list[tuple[object, ...]] = []
    inserted = 0
    for row in rows:
        batch.append(row)
        if len(batch) >= INSERT_BATCH_SIZE:
            con.executemany(
                "INSERT INTO raw_rows_json VALUES (?,?,?,?,?,?,?,?)", batch
            )
            inserted += len(batch)
            batch.clear()
    if batch:
        con.executemany("INSERT INTO raw_rows_json VALUES (?,?,?,?,?,?,?,?)", batch)
        inserted += len(batch)
    return inserted


def _decode_csv(path: Path) -> tuple[str, str]:
    """Decode a legacy source, retaining a warning if replacement was required."""

    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig"), ""
    except UnicodeDecodeError as exc:
        return (
            raw.decode("utf-8-sig", errors="replace"),
            f"UTF-8 decode replacement used: {exc}",
        )


def _load_source(
    con: duckdb.DuckDBPyConnection,
    source_root: Path,
    path: Path,
    imported_at_utc: str,
) -> tuple[int, bool]:
    """Load one CSV and return ``(row_count, had_error)``."""

    stat = path.stat()
    relative_path = path.relative_to(source_root).as_posix()
    content_sha256 = _sha256_file(path)
    source_id = _source_id(relative_path, content_sha256)
    text, decode_note = _decode_csv(path)

    header: list[str] = []
    keys: list[str] = []
    status = "ok"
    notes: list[str] = [decode_note] if decode_note else []
    row_count = 0
    mismatch_count = 0
    pending_rows: list[tuple[object, ...]] = []

    try:
        csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)
        reader = csv.reader(text.splitlines(keepends=True), strict=True)
        try:
            header = next(reader)
        except StopIteration:
            status = "empty"
        else:
            keys = _normalise_header_keys(header)
            for row_number, cells in enumerate(reader, start=1):
                width_matches = len(cells) == len(header)
                mismatch_count += int(not width_matches)
                pending_rows.append(
                    (
                        source_id,
                        relative_path,
                        row_number,
                        _stable_json(_row_object(keys, cells)),
                        _stable_json(list(cells)),
                        width_matches,
                        LEGACY_DATASET_ROLE,
                        True,
                    )
                )
                row_count += 1
                if len(pending_rows) >= INSERT_BATCH_SIZE:
                    _insert_batches(con, pending_rows)
                    pending_rows.clear()
    except (csv.Error, UnicodeError) as exc:
        status = "error"
        notes.append(f"CSV parse error after {row_count} rows: {exc}")

    if pending_rows:
        _insert_batches(con, pending_rows)
    if status == "ok" and (decode_note or mismatch_count):
        status = "ok_with_warnings"
    if mismatch_count:
        notes.append(f"row-width mismatches: {mismatch_count}")

    con.execute(
        "INSERT INTO source_files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            source_id,
            relative_path,
            path.name,
            content_sha256,
            stat.st_size,
            stat.st_mtime_ns,
            _utc_from_ns(stat.st_mtime_ns),
            schema_hash(header),
            _stable_json(header),
            _stable_json(keys),
            len(header),
            row_count,
            status,
            " | ".join(notes),
            LEGACY_DATASET_ROLE,
            True,
            imported_at_utc,
        ],
    )
    return row_count, status == "error"


def _validate_database(con: duckdb.DuckDBPyConnection) -> None:
    source_count = con.execute("SELECT COUNT(*) FROM source_files").fetchone()[0]
    source_id_count = con.execute(
        "SELECT COUNT(DISTINCT source_id) FROM source_files"
    ).fetchone()[0]
    if source_count != source_id_count:
        raise RuntimeError("legacy inventory validation failed: duplicate source IDs")

    expected_rows = con.execute(
        "SELECT COALESCE(SUM(row_count), 0) FROM source_files"
    ).fetchone()[0]
    actual_rows = con.execute("SELECT COUNT(*) FROM raw_rows_json").fetchone()[0]
    if expected_rows != actual_rows:
        raise RuntimeError(
            "legacy inventory validation failed: source/row counts disagree "
            f"({expected_rows} != {actual_rows})"
        )

    nonlegacy = con.execute(
        """
        SELECT COUNT(*) FROM source_files
        WHERE NOT is_legacy OR dataset_role <> ?
        """,
        [LEGACY_DATASET_ROLE],
    ).fetchone()[0]
    if nonlegacy:
        raise RuntimeError("legacy inventory validation failed: unlabelled sources")


def _remove_temporary_database(path: Path) -> None:
    for candidate in (path, Path(f"{path}.wal")):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def build_legacy_inventory(
    source_root: Path = DEFAULT_SOURCE_ROOT,
    output: Path | None = None,
    *,
    force: bool = False,
) -> BuildSummary:
    """Build and atomically publish a fixed-schema legacy CSV inventory.

    ``force=True`` is accepted only when ``output`` is explicit.  Protected
    canonical database names are rejected regardless of location or force.
    Existing CSV files and canonical DuckDB files are never modified.
    """

    source_root = Path(source_root).expanduser().resolve()
    files = discover_csv_files(source_root)
    output_path, _ = _resolve_output(source_root, output, force=force)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}.",
        suffix=".tmp.duckdb",
        dir=output_path.parent,
    )
    os.close(descriptor)
    temp_path = Path(temp_name)
    # DuckDB expects to initialise a new file rather than a zero-byte mkstemp.
    temp_path.unlink()

    imported_at_utc = (
        dt.datetime.now(tz=dt.timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    con: duckdb.DuckDBPyConnection | None = None
    total_rows = 0
    error_count = 0
    try:
        con = duckdb.connect(str(temp_path))
        con.execute("BEGIN TRANSACTION")
        _create_schema(con)
        con.executemany(
            "INSERT INTO inventory_metadata VALUES (?,?)",
            [
                ("inventory_format", INVENTORY_FORMAT),
                ("schema_version", INVENTORY_SCHEMA_VERSION),
                ("dataset_role", LEGACY_DATASET_ROLE),
                ("source_root", str(source_root)),
                ("generated_at_utc", imported_at_utc),
                ("source_scan", "recursive"),
            ],
        )
        for path in files:
            rows, had_error = _load_source(
                con, source_root, path, imported_at_utc
            )
            total_rows += rows
            error_count += int(had_error)
        _validate_database(con)
        con.execute("COMMIT")
        con.execute("CHECKPOINT")
        con.close()
        con = None

        # Re-check immediately before publication so the non-force path never
        # replaces a database that appeared while the inventory was building.
        if output_path.exists() and not force:
            raise FileExistsError(f"output appeared during build: {output_path}")
        os.replace(temp_path, output_path)
    except BaseException:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass
        _remove_temporary_database(temp_path)
        raise

    return BuildSummary(
        output_path=output_path,
        source_root=source_root,
        source_count=len(files),
        row_count=total_rows,
        error_count=error_count,
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively inventory legacy CSV results into an isolated DuckDB. "
            "This command never writes the canonical experiment databases."
        )
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="legacy CSV tree to scan recursively (default: results/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "inventory DuckDB path (default: SOURCE_ROOT/"
            f"{DEFAULT_OUTPUT_NAME})"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace an existing explicit --output target",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    args = parser.parse_args(argv)
    try:
        summary = build_legacy_inventory(
            source_root=args.source_root,
            output=args.output,
            force=args.force,
        )
    except (FileNotFoundError, FileExistsError, UnsafeOutputError) as exc:
        parser.error(str(exc))
    print(
        "[legacy-inventory] "
        f"sources={summary.source_count} rows={summary.row_count} "
        f"import_errors={summary.error_count} output={summary.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
