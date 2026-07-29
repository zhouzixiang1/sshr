#!/usr/bin/env python3
"""Contract tests for the append-only experiment DuckDB."""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.experiment_db import (  # noqa: E402
    ExperimentDB,
    SCHEMA_VERSION,
    canonical_json,
    sha256_hex,
)
import src.experiment_db as experiment_db_module  # noqa: E402


class CanonicalPayloadTests(unittest.TestCase):
    def test_canonical_json_and_sha_are_order_independent(self) -> None:
        left = {"z": [3, 2, 1], "a": {"β": True, "x": 0.0}}
        right = {"a": {"x": -0.0, "β": True}, "z": [3, 2, 1]}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(sha256_hex(left), sha256_hex(right))
        self.assertEqual(len(sha256_hex(left)), 64)

    def test_non_finite_values_are_rejected(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json({"value": value})


class ExperimentDBMigrationTests(unittest.TestCase):
    def test_v1_database_is_additively_migrated_to_resource_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "v1.duckdb"
            connection = duckdb.connect(str(path))
            connection.execute(
                """CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    checksum VARCHAR NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT current_timestamp
                )"""
            )
            connection.execute(experiment_db_module._MIGRATION_001)
            connection.execute(
                "INSERT INTO schema_migrations(version, name, checksum) VALUES (1, ?, ?)",
                [
                    "initial_append_only_experiment_schema",
                    sha256_hex(experiment_db_module._MIGRATION_001),
                ],
            )
            connection.close()

            with ExperimentDB(path) as migrated:
                self.assertEqual(migrated.schema_version, SCHEMA_VERSION)
                synth_columns = {
                    row[0]
                    for row in migrated.connection.execute(
                        "DESCRIBE synthesis_attempts"
                    ).fetchall()
                }
                mapping_columns = {
                    row[0]
                    for row in migrated.connection.execute(
                        "DESCRIBE mapping_attempts"
                    ).fetchall()
                }
                self.assertIn("peak_rss_mb", synth_columns)
                self.assertIn("resource_stage_peaks_json", synth_columns)
                self.assertIn("total_peak_rss_mb", mapping_columns)
                self.assertIn("total_peak_system_memory_percent", mapping_columns)


class ExperimentDBTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "experiment.duckdb"
        self.db = ExperimentDB(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _base_records(self) -> dict[str, object]:
        experiment_id = self.db.create_experiment(
            "xa-202609-test",
            "hardware-aware Boolean oracle synthesis",
            objective={"claim_policy": "matched and verified only"},
        )
        batch_id = self.db.create_run_batch(
            experiment_id,
            "batch-001",
            config={"seeds": [0], "methods": ["direct_anf", "resource_nmcts"]},
            planned_cell_count=2,
            host={"gpu": "RTX 5090"},
        )
        function_id = self.db.register_boolean_function(
            "maj3",
            3,
            {"truth_table_lsb_hex": "e8"},
            truth_table_hex="e8",
            anf=[[0, 1], [0, 2], [1, 2]],
            metadata={"family": "majority"},
        )
        case_id = self.db.register_benchmark_case(
            experiment_id,
            function_id,
            "maj3",
            suite="structured-small",
        )
        method_a = self.db.register_method_spec(
            "direct_anf", {"gate_mode": "logical_and"}, code_revision="deadbeef"
        )
        method_b = self.db.register_method_spec(
            "resource_nmcts",
            {"iterations": 64, "gate_mode": "logical_and"},
            model_sha256="a" * 64,
            code_revision="deadbeef",
        )
        return {
            "experiment": experiment_id,
            "batch": batch_id,
            "function": function_id,
            "case": case_id,
            "method_a": method_a,
            "method_b": method_b,
        }

    def test_schema_is_versioned_and_uses_explicit_types(self) -> None:
        self.assertEqual(self.db.schema_version, SCHEMA_VERSION)
        logical_types = {
            row[0]: row[1]
            for row in self.db.connection.execute("DESCRIBE logical_metrics").fetchall()
        }
        attempt_types = {
            row[0]: row[1]
            for row in self.db.connection.execute("DESCRIBE synthesis_attempts").fetchall()
        }
        self.assertEqual(logical_types["logical_metric_id"], "UUID")
        self.assertEqual(logical_types["t_count"], "BIGINT")
        self.assertEqual(logical_types["weighted_score"], "DOUBLE")
        self.assertEqual(logical_types["metric_payload_json"], "JSON")
        self.assertEqual(attempt_types["recorded_at"], "TIMESTAMP WITH TIME ZONE")

        # Reopening must validate the same migration instead of reapplying it.
        self.db.close()
        self.db = ExperimentDB(self.db_path, read_only=True)
        self.assertEqual(self.db.schema_version, SCHEMA_VERSION)
        count = self.db.connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
        self.assertEqual(count, SCHEMA_VERSION)

    def test_cell_is_idempotent_and_retries_are_append_only(self) -> None:
        ids = self._base_records()
        self.db.start_batch(ids["batch"])
        cell = self.db.get_or_create_cell(
            ids["experiment"],
            ids["case"],
            ids["method_a"],
            0,
            batch_id=ids["batch"],
            ordinal=0,
        )
        duplicate = self.db.get_or_create_cell(
            ids["experiment"], ids["case"], ids["method_a"], 0, batch_id=ids["batch"]
        )
        self.assertEqual(cell, duplicate)
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM synthesis_cells").fetchone()[0], 1
        )

        failed = self.db.record_synthesis_attempt(
            cell, ids["batch"], "timeout", error_type="Timeout", runtime_s=1.0
        )
        first_success = self.db.record_synthesis_attempt(
            cell,
            ids["batch"],
            "success",
            selected_method="direct_anf",
            runtime_s=0.2,
            logical_metrics={
                "t_count": 12,
                "cnot_count": 18,
                "depth": 18,
                "gate_count": 9,
                "ancilla_count": 0,
                "n_qubits": 4,
                "weighted_score": 12.9,
            },
        )
        later_success = self.db.record_synthesis_attempt(
            cell,
            ids["batch"],
            "success",
            selected_method="direct_anf",
            runtime_s=0.1,
            logical_metrics={
                "t": 10,
                "cnot": 16,
                "depth": 16,
                "gates": 8,
                "ancilla": 0,
                "n_qubits": 4,
                "score": 10.8,
            },
        )
        self.assertEqual((failed.attempt_no, first_success.attempt_no, later_success.attempt_no), (1, 2, 3))
        canonical = self.db.connection.execute(
            "SELECT attempt_id, attempt_no FROM canonical_synthesis_attempts WHERE cell_id = ?",
            [cell],
        ).fetchone()
        latest = self.db.connection.execute(
            "SELECT attempt_id, attempt_no FROM latest_synthesis_attempts WHERE cell_id = ?",
            [cell],
        ).fetchone()
        self.assertEqual(str(canonical[0]), str(first_success.attempt_id))
        self.assertEqual(canonical[1], 2)
        self.assertEqual(str(latest[0]), str(later_success.attempt_id))
        self.assertEqual(latest[1], 3)
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM synthesis_attempts").fetchone()[0], 3
        )

        self.db.complete_batch(ids["batch"])
        self.assertEqual(self.db.get_batch_status(ids["batch"]).status, "completed")
        coverage = self.db.connection.execute(
            """SELECT registered_cells, attempted_cells_in_batch,
                      canonical_success_cells, synthesis_attempt_count
               FROM batch_coverage WHERE batch_id = ?""",
            [ids["batch"]],
        ).fetchone()
        self.assertEqual(tuple(coverage), (1, 1, 1, 3))

    def test_mapping_canonical_verification_artifact_and_paired_views(self) -> None:
        ids = self._base_records()
        self.db.start_batch(ids["batch"])
        target = self.db.register_hardware_target(
            "cx-line-5", 5, {"basis_gates": ["rz", "sx", "x", "cx"], "edges": [[0, 1], [1, 2], [2, 3], [3, 4]]}
        )
        transpile = self.db.register_transpile_spec(
            target,
            "sabre-o3-seed7",
            {"optimization_level": 3, "layout_method": "sabre", "routing_method": "sabre", "seed": 7},
        )

        synth_attempts = []
        for ordinal, (method_id, method_name, t_count, cnot_count) in enumerate(
            (
                (ids["method_a"], "direct_anf", 12, 18),
                (ids["method_b"], "resource_nmcts", 4, 11),
            )
        ):
            cell = self.db.get_or_create_cell(
                ids["experiment"],
                ids["case"],
                method_id,
                0,
                batch_id=ids["batch"],
                ordinal=ordinal,
            )
            synth = self.db.record_synthesis_attempt(
                cell,
                ids["batch"],
                "success",
                selected_method=method_name,
                logical_metrics={
                    "t_count": t_count,
                    "cnot_count": cnot_count,
                    "depth": cnot_count,
                    "gate_count": cnot_count,
                    "ancilla_count": 0,
                    "n_qubits": 4,
                    "weighted_score": float(t_count),
                },
            )
            synth_attempts.append(synth)
            self.db.record_verification(
                "logical", synth.attempt_id, "truth-table", "pass", passed=True, basis_states_checked=16, mismatch_count=0
            )

            if ordinal == 0:
                mapping_timeout = self.db.record_mapping_attempt(
                    synth.attempt_id, ids["batch"], transpile, "timeout", runtime_s=2.0
                )
                self.assertEqual(mapping_timeout.attempt_no, 1)
            mapping = self.db.record_mapping_attempt(
                synth.attempt_id,
                ids["batch"],
                transpile,
                "success",
                seed_transpiler=7,
                runtime_s=0.5,
                mapping_metrics={
                    "total_gate_count": 68 if ordinal == 0 else 38,
                    "one_qubit_gate_count": 26 if ordinal == 0 else 12,
                    "two_qubit_gate_count": 42 if ordinal == 0 else 26,
                    "native_entangling_count": 42 if ordinal == 0 else 26,
                    "swap_count": 0,
                    "depth": 57 if ordinal == 0 else 32,
                    "two_qubit_depth": 30 if ordinal == 0 else 20,
                    "target_violation_count": 0,
                    "direction_violation_count": 0,
                    "routing_overhead": 1.2,
                },
                native_gate_counts={"cx": 42 if ordinal == 0 else 26, "rz": 10},
            )
            self.db.record_verification(
                "mapping",
                mapping.attempt_id,
                "full-oracle-statevector",
                "pass",
                passed=True,
                basis_states_checked=16,
                mismatch_count=0,
                max_leakage=1e-16,
                max_phase_error=1e-16,
                tolerance=1e-9,
            )
            if ordinal == 0:
                canonical_mapping = mapping
                later = self.db.record_mapping_attempt(
                    synth.attempt_id,
                    ids["batch"],
                    transpile,
                    "success",
                    seed_transpiler=8,
                    mapping_metrics={"total_gate_count": 66, "depth": 55},
                )
                self.assertEqual(later.attempt_no, 3)

        canonical_row = self.db.connection.execute(
            """SELECT mapping_attempt_id, attempt_no FROM canonical_mapping_attempts
               WHERE synthesis_attempt_id = ? AND transpile_spec_id = ?""",
            [synth_attempts[0].attempt_id, transpile],
        ).fetchone()
        latest_row = self.db.connection.execute(
            """SELECT mapping_attempt_id, attempt_no FROM latest_mapping_attempts
               WHERE synthesis_attempt_id = ? AND transpile_spec_id = ?""",
            [synth_attempts[0].attempt_id, transpile],
        ).fetchone()
        self.assertEqual(str(canonical_row[0]), str(canonical_mapping.attempt_id))
        self.assertEqual(canonical_row[1], 2)
        self.assertEqual(latest_row[1], 3)
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM paired_logical_metrics").fetchone()[0], 1
        )
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM paired_mapping_metrics").fetchone()[0], 1
        )

        artifact_id = self.db.record_artifact(
            ids["experiment"],
            "mapped-qpy",
            Path("artifacts/maj3.qpy"),
            "b" * 64,
            batch_id=ids["batch"],
            mapping_attempt_id=canonical_mapping.attempt_id,
            byte_size=123,
            mime_type="application/octet-stream",
        )
        artifact = self.db.connection.execute(
            "SELECT path_or_uri, content_sha256 FROM artifacts WHERE artifact_id = ?", [artifact_id]
        ).fetchone()
        self.assertEqual(tuple(artifact), ("artifacts/maj3.qpy", "b" * 64))

    def test_paired_view_requires_non_adverse_verification_for_both_methods(self) -> None:
        ids = self._base_records()
        attempts = []
        for method_id, method_name in (
            (ids["method_a"], "direct_anf"),
            (ids["method_b"], "resource_nmcts"),
        ):
            cell = self.db.get_or_create_cell(
                ids["experiment"], ids["case"], method_id, 0, batch_id=ids["batch"]
            )
            attempts.append(
                self.db.record_synthesis_attempt(
                    cell,
                    ids["batch"],
                    "success",
                    selected_method=method_name,
                    logical_metrics={"t_count": 1, "n_qubits": 4},
                )
            )
        count = lambda: self.db.connection.execute(
            "SELECT count(*) FROM paired_logical_metrics"
        ).fetchone()[0]
        self.assertEqual(count(), 0)
        for attempt in attempts:
            self.db.record_verification(
                "logical", attempt.attempt_id, "truth-table", "pass", passed=True
            )
        self.assertEqual(count(), 1)
        self.db.record_verification(
            "logical", attempts[1].attempt_id, "phase-sensitive", "fail", passed=False
        )
        self.assertEqual(count(), 0)

    def test_nested_transaction_rolls_back_all_rows(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with self.db.transaction():
                experiment_id = self.db.create_experiment("rollback", "Rollback test")
                self.db.create_run_batch(experiment_id, "never-committed")
                raise RuntimeError("deliberate rollback")
        self.assertEqual(self.db.connection.execute("SELECT count(*) FROM experiments").fetchone()[0], 0)
        self.assertEqual(self.db.connection.execute("SELECT count(*) FROM run_batches").fetchone()[0], 0)
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM run_batch_status_events").fetchone()[0], 0
        )

    def test_failed_metric_constraint_rolls_back_attempt_allocation(self) -> None:
        ids = self._base_records()
        cell = self.db.get_or_create_cell(
            ids["experiment"], ids["case"], ids["method_a"], 0, batch_id=ids["batch"]
        )
        with self.assertRaises(Exception):
            self.db.record_synthesis_attempt(
                cell,
                ids["batch"],
                "success",
                logical_metrics={"t_count": -1, "n_qubits": 4},
            )
        self.assertEqual(
            self.db.connection.execute("SELECT count(*) FROM synthesis_attempts").fetchone()[0], 0
        )
        retry = self.db.record_synthesis_attempt(
            cell,
            ids["batch"],
            "success",
            logical_metrics={"t_count": 1, "n_qubits": 4},
        )
        self.assertEqual(retry.attempt_no, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
