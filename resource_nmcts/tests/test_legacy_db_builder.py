#!/usr/bin/env python3
"""Safety and provenance tests for the isolated legacy CSV inventory builder."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis import build_experiments_db as legacy_builder


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


class LegacyInventoryBuilderTests(unittest.TestCase):
    def test_default_is_isolated_and_never_overwrites_canonical_databases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "results"
            _write_text(source_root / "legacy.csv", "name,value\na,1\n")
            canonical = {
                source_root / "experiments.duckdb": b"canonical-experiments-sentinel",
                source_root / "hardware_validation.duckdb": b"canonical-hw-sentinel",
            }
            for path, sentinel in canonical.items():
                path.write_bytes(sentinel)

            summary = legacy_builder.build_legacy_inventory(source_root)

            self.assertEqual(
                summary.output_path,
                (source_root / "legacy_csv_inventory.duckdb").resolve(),
            )
            self.assertEqual(summary.source_count, 1)
            self.assertEqual(summary.row_count, 1)
            for path, sentinel in canonical.items():
                self.assertEqual(path.read_bytes(), sentinel)

            con = duckdb.connect(str(summary.output_path), read_only=True)
            try:
                tables = {
                    row[0]
                    for row in con.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()
                }
                self.assertEqual(
                    tables,
                    {
                        "inventory_metadata",
                        "raw_rows_json",
                        "source_files",
                        "legacy_schema_summary",
                    },
                )
                metadata = dict(
                    con.execute("SELECT key, value FROM inventory_metadata").fetchall()
                )
                self.assertEqual(
                    metadata["inventory_format"], legacy_builder.INVENTORY_FORMAT
                )
                self.assertEqual(
                    metadata["dataset_role"], legacy_builder.LEGACY_DATASET_ROLE
                )
            finally:
                con.close()

            before = summary.output_path.read_bytes()
            with self.assertRaises(FileExistsError):
                legacy_builder.build_legacy_inventory(source_root)
            self.assertEqual(summary.output_path.read_bytes(), before)
            with self.assertRaises(legacy_builder.UnsafeOutputError):
                legacy_builder.build_legacy_inventory(source_root, force=True)

    def test_protected_names_are_rejected_even_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "csv"
            _write_text(source_root / "one.csv", "x\n1\n")

            for name in ("experiments.duckdb", "hardware_validation.duckdb"):
                with self.subTest(name=name):
                    target = Path(temporary) / "elsewhere" / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    sentinel = f"do-not-touch-{name}".encode("ascii")
                    target.write_bytes(sentinel)
                    with self.assertRaises(legacy_builder.UnsafeOutputError):
                        legacy_builder.build_legacy_inventory(
                            source_root, output=target, force=True
                        )
                    self.assertEqual(target.read_bytes(), sentinel)

    def test_recursive_manifest_hashes_and_raw_rows_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "legacy-results"
            nested = source_root / "archive" / "v1" / "odd.CSV"
            _write_text(
                nested,
                'a,a,\n"hello,world","line 1\nline 2",tail\nx,y\n',
            )
            _write_text(source_root / "root.csv", "id,label\n1,根\n")
            expected_sha256 = hashlib.sha256(nested.read_bytes()).hexdigest()
            expected_stat = nested.stat()
            expected_schema_hash = legacy_builder.schema_hash(["a", "a", ""])
            output = Path(temporary) / "inventory.duckdb"

            summary = legacy_builder.build_legacy_inventory(
                source_root, output=output
            )

            self.assertEqual(summary.source_count, 2)
            self.assertEqual(summary.row_count, 3)
            con = duckdb.connect(str(output), read_only=True)
            try:
                source = con.execute(
                    """
                    SELECT relative_path, sha256, size_bytes, mtime_ns,
                           schema_hash, header_json, normalised_header_json,
                           row_count, import_status, dataset_role, is_legacy
                    FROM source_files WHERE relative_path = ?
                    """,
                    ["archive/v1/odd.CSV"],
                ).fetchone()
                self.assertIsNotNone(source)
                self.assertEqual(source[0], "archive/v1/odd.CSV")
                self.assertEqual(source[1], expected_sha256)
                self.assertEqual(source[2], expected_stat.st_size)
                self.assertEqual(source[3], expected_stat.st_mtime_ns)
                self.assertEqual(source[4], expected_schema_hash)
                self.assertEqual(json.loads(source[5]), ["a", "a", ""])
                self.assertEqual(
                    json.loads(source[6]),
                    ["a", "a__duplicate_2", "__unnamed_column_3"],
                )
                self.assertEqual(source[7], 2)
                self.assertEqual(source[8], "ok_with_warnings")
                self.assertEqual(source[9], legacy_builder.LEGACY_DATASET_ROLE)
                self.assertTrue(source[10])

                rows = con.execute(
                    """
                    SELECT row_number, row_json, raw_cells_json,
                           width_matches_schema, dataset_role, is_legacy
                    FROM raw_rows_json
                    WHERE relative_path = ? ORDER BY row_number
                    """,
                    ["archive/v1/odd.CSV"],
                ).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(
                    json.loads(rows[0][2]),
                    ["hello,world", "line 1\nline 2", "tail"],
                )
                first_object = json.loads(rows[0][1])
                self.assertEqual(first_object["a"], "hello,world")
                self.assertEqual(first_object["a__duplicate_2"], "line 1\nline 2")
                self.assertTrue(rows[0][3])
                second_object = json.loads(rows[1][1])
                self.assertIsNone(second_object["__unnamed_column_3"])
                self.assertFalse(rows[1][3])
                self.assertTrue(all(row[4] == legacy_builder.LEGACY_DATASET_ROLE for row in rows))
                self.assertTrue(all(row[5] for row in rows))
            finally:
                con.close()

    def test_explicit_force_replaces_only_the_named_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "csv"
            _write_text(source_root / "one.csv", "x\n1\n")
            output = Path(temporary) / "custom_legacy.duckdb"
            sentinel = b"existing-custom-inventory"
            output.write_bytes(sentinel)

            with self.assertRaises(FileExistsError):
                legacy_builder.build_legacy_inventory(source_root, output=output)
            self.assertEqual(output.read_bytes(), sentinel)

            summary = legacy_builder.build_legacy_inventory(
                source_root, output=output, force=True
            )
            self.assertEqual(summary.output_path, output.resolve())
            self.assertNotEqual(output.read_bytes(), sentinel)
            con = duckdb.connect(str(output), read_only=True)
            try:
                self.assertEqual(
                    con.execute("SELECT COUNT(*) FROM source_files").fetchone()[0], 1
                )
            finally:
                con.close()
            self.assertEqual(list(output.parent.glob(".custom_legacy.*.tmp.duckdb*")), [])

    def test_large_legacy_field_is_preserved_without_partial_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "csv"
            payload = "f" * 200_000
            _write_text(source_root / "large.csv", f"name,payload\ncase,{payload}\n")
            output = Path(temporary) / "inventory.duckdb"

            summary = legacy_builder.build_legacy_inventory(source_root, output=output)
            self.assertEqual(summary.error_count, 0)
            self.assertEqual(summary.row_count, 1)
            con = duckdb.connect(str(output), read_only=True)
            try:
                status, row_json = con.execute(
                    """
                    SELECT s.import_status, r.row_json
                    FROM source_files s JOIN raw_rows_json r USING (source_id)
                    """
                ).fetchone()
                self.assertEqual(status, "ok")
                self.assertEqual(json.loads(row_json)["payload"], payload)
            finally:
                con.close()

    def test_failed_forced_build_preserves_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary) / "csv"
            _write_text(source_root / "one.csv", "x\n1\n")
            output = Path(temporary) / "custom_legacy.duckdb"
            sentinel = b"last-known-good-inventory"
            output.write_bytes(sentinel)

            with mock.patch.object(
                legacy_builder, "_load_source", side_effect=RuntimeError("injected")
            ):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    legacy_builder.build_legacy_inventory(
                        source_root, output=output, force=True
                    )

            self.assertEqual(output.read_bytes(), sentinel)
            self.assertEqual(list(output.parent.glob(".custom_legacy.*.tmp.duckdb*")), [])


if __name__ == "__main__":
    unittest.main()
