#!/usr/bin/env python3
"""Contract tests for validated JSONL -> append-only DuckDB ingestion."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import run_hardware_validation as runner
from src.experiment_db import ExperimentDB
from src.factor_plan import SearchConfig
from src.hardware_map import CompileConfig, make_cx_full_target
from src.hardware_validation_ingest import (
    HardwareValidationIngestError,
    _method_identity,
    _transpile_identity,
    ingest_jsonl,
    load_jsonl,
)
from src.sshr_lib.bool_func import BooleanFunction


def _successful_row(method: str) -> dict:
    target = make_cx_full_target(5)
    compile_config = CompileConfig(optimization_level=1, seed_transpiler=5)
    functions = [("and3", "structured", BooleanFunction(3, 0b10000000))]
    suite_id = runner._suite_identity(functions, label="ingest-test-v1")
    row = runner._context_row(
        run_id="ingest-test-run",
        run_ts="2026-07-22T00:00:00+00:00",
        function_id="and3",
        family="structured",
        bf=functions[0][2],
        method=method,
        synthesis_seed=7,
        transpile_seed=5,
        model_path=None,
        model_hash=None,
        synthesis_config=SearchConfig(),
        target_name="cx_full",
        target_spec=target,
        compile_config=compile_config,
        benchmark_suite="ingest-test-v1",
        benchmark_suite_id=suite_id,
    )
    row.update(
        {
            "status": "ok",
            "stage": "complete",
            "result_method": method,
            "selected_method": method,
            "artifact_consistent": True,
            "mapping_provenance_consistent": True,
            "result_correct": True,
            "engine_correct": True,
            "engine_states_evaluated": 8,
            "synth_time_s": 0.10,
            "reported_synth_time_s": 0.09,
            "logical_verify_time_s": 0.01,
            "logic_T": 4,
            "logic_CNOT": 6 if method == "direct_anf" else 4,
            "logic_depth": 7 if method == "direct_anf" else 5,
            "logic_gates": 8 if method == "direct_anf" else 6,
            "logic_explicit_ancilla": 0,
            "logic_peak_ancilla": 0,
            "result_terms": 1,
            "engine_gates": 1,
            "engine_qubits": 4,
            "logical_qubits": 4,
            "work_qubits": 4,
            "physical_qubits": 5,
            "active_physical_qubits": 4,
            "compiler_ancillas": 0,
            "transpiler_added_qubits": 1,
            "mapped_gates": 3,
            "mapped_depth": 3,
            "native_oneq_count": 1,
            "native_twoq_count": 2,
            "native_twoq_depth": 2,
            "mapped_highq_count": 0,
            "native_gate_counts": {"rz": 1, "cx": 2},
            "native_rz_count": 1,
            "native_sx_count": 0,
            "native_x_count": 0,
            "native_cx_count": 2,
            "native_cz_count": 0,
            "native_ecr_count": 0,
            "basis_reference_gates": 3,
            "basis_reference_depth": 3,
            "basis_reference_twoq_count": 2,
            "routing_gate_delta": 0,
            "routing_depth_delta": 0,
            "routing_twoq_delta": 0,
            "routing_twoq_overhead_ratio": 0.0,
            "unsupported_instructions": 0,
            "coupling_violations": 0,
            "estimated_duration_s": None,
            "basis_reference_time_s": 0.01,
            "compile_time_s": 0.02,
            "map_time_s": 0.02,
            "mapped_verify_time_s": 0.03,
            "initial_layout": [0, 1, 2, 3],
            "final_layout": [0, 1, 2, 3],
            "mapped_verify_ok": True,
            "mapped_verification_complete": True,
            "mapped_verify_mode": "exact_xy_phase",
            "mapped_states_evaluated": 16,
            "mapped_mismatches": 0,
            "mapped_max_probability_error": 0.0,
            "mapped_max_leakage": 0.0,
            "mapped_max_phase_error": 0.0,
            "mapped_probability_tolerance": 1e-8,
            "mapped_phase_tolerance": 1e-8,
            "resource_monitor_backend": "psutil",
            "resource_guard_limit_percent": 70.0,
            "synth_peak_rss_mb": 123.5,
            "synth_peak_system_memory_percent": 24.0,
            "synth_resource_stage_peaks": {
                "synthesis": {
                    "peak_rss_mb": 123.5,
                    "peak_system_memory_percent": 24.0,
                }
            },
            "map_peak_rss_mb": 234.5,
            "map_peak_system_memory_percent": 25.0,
            "map_resource_stage_peaks": {
                "mapping": {
                    "peak_rss_mb": 234.5,
                    "peak_system_memory_percent": 25.0,
                }
            },
            "total_peak_rss_mb": 234.5,
            "total_peak_system_memory_percent": 25.0,
        }
    )
    return row


class HardwareValidationIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="hardware-ingest-test-")
        root = Path(self.temporary.name)
        self.jsonl = root / "facts.jsonl"
        self.db_path = root / "experiments.duckdb"
        self.rows = [_successful_row("direct_anf"), _successful_row("greedy_factor")]
        self.jsonl.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in self.rows),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_ingest_is_typed_paired_and_exact_source_resumable(self) -> None:
        first = ingest_jsonl(self.jsonl, self.db_path)
        self.assertFalse(first.already_ingested)
        self.assertEqual(first.source_rows, 2)
        self.assertEqual(first.synthesis_attempts, 2)
        self.assertEqual(first.mapping_attempts, 2)
        self.assertEqual(first.logical_verifications, 2)
        self.assertEqual(first.mapping_verifications, 2)

        second = ingest_jsonl(self.jsonl, self.db_path)
        self.assertTrue(second.already_ingested)
        self.assertEqual(second.batch_id, first.batch_id)

        with ExperimentDB(self.db_path, read_only=True) as db:
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM synthesis_attempts").fetchone()[0],
                2,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM mapping_attempts").fetchone()[0], 2
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM paired_logical_metrics").fetchone()[0],
                1,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM paired_mapping_metrics").fetchone()[0],
                1,
            )
            coverage = db.connection.execute(
                "SELECT canonical_success_cells, canonical_verified_cells FROM batch_coverage"
            ).fetchone()
            self.assertEqual(tuple(coverage), (2, 2))
            synth_peaks = db.connection.execute(
                "SELECT peak_rss_mb, peak_system_memory_percent "
                "FROM synthesis_attempts ORDER BY peak_rss_mb"
            ).fetchall()
            self.assertEqual(synth_peaks, [(123.5, 24.0), (123.5, 24.0)])
            map_peaks = db.connection.execute(
                "SELECT peak_rss_mb, peak_system_memory_percent, "
                "total_peak_rss_mb, total_peak_system_memory_percent "
                "FROM mapping_attempts ORDER BY peak_rss_mb"
            ).fetchall()
            self.assertEqual(
                map_peaks,
                [(234.5, 25.0, 234.5, 25.0), (234.5, 25.0, 234.5, 25.0)],
            )

    def test_exact_source_can_be_set_to_fail_instead_of_resume(self) -> None:
        ingest_jsonl(self.jsonl, self.db_path)
        with self.assertRaises(HardwareValidationIngestError):
            ingest_jsonl(self.jsonl, self.db_path, resume=False)

    def test_hash_tampering_is_rejected_before_database_creation(self) -> None:
        corrupted = dict(self.rows[0])
        corrupted["target_hash"] = "0" * 64
        self.jsonl.write_text(json.dumps(corrupted) + "\n", encoding="utf-8")
        with self.assertRaises(HardwareValidationIngestError):
            ingest_jsonl(self.jsonl, self.db_path)
        self.assertFalse(self.db_path.exists())

    def test_mapping_failure_is_preserved_but_not_paired(self) -> None:
        failed = dict(self.rows[1])
        for field in (
            "mapped_gates",
            "mapped_depth",
            "native_oneq_count",
            "native_twoq_count",
            "native_twoq_depth",
            "mapped_highq_count",
            "native_gate_counts",
            "basis_reference_gates",
            "basis_reference_depth",
            "basis_reference_twoq_count",
            "routing_gate_delta",
            "routing_depth_delta",
            "routing_twoq_delta",
            "routing_twoq_overhead_ratio",
            "unsupported_instructions",
            "coupling_violations",
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
        ):
            failed[field] = None
        for gate in runner.KNOWN_NATIVE_GATES:
            failed[f"native_{gate}_count"] = None
        failed.update(
            {
                "status": "timeout",
                "stage": "mapping",
                "error_code": "stage_timeout",
                "error_message": "mapping exceeded timeout",
                "mapping_provenance_consistent": None,
            }
        )
        self.jsonl.write_text(
            json.dumps(self.rows[0]) + "\n" + json.dumps(failed) + "\n",
            encoding="utf-8",
        )
        summary = ingest_jsonl(self.jsonl, self.db_path)
        self.assertEqual(summary.status_counts, {"success": 1, "timeout": 1})
        with ExperimentDB(self.db_path, read_only=True) as db:
            self.assertEqual(
                db.connection.execute(
                    "SELECT count(*) FROM mapping_attempts WHERE status='timeout'"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM paired_mapping_metrics").fetchone()[0],
                0,
            )

    def test_legacy_v2_file_is_normalized_and_ingested(self) -> None:
        legacy = dict(self.rows[0])
        legacy["schema_version"] = runner.LEGACY_SCHEMA_VERSION
        for field in runner.RESOURCE_ROW_FIELDS:
            legacy.pop(field)
        self.jsonl.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
        summary = ingest_jsonl(self.jsonl, self.db_path)
        self.assertEqual(summary.source_rows, 1)
        with ExperimentDB(self.db_path, read_only=True) as db:
            synth = db.connection.execute(
                "SELECT peak_rss_mb, peak_system_memory_percent, "
                "resource_stage_peaks_json FROM synthesis_attempts"
            ).fetchone()
            self.assertEqual(synth[0:2], (None, None))
            self.assertEqual(json.loads(synth[2]), {})
            mapping = db.connection.execute(
                "SELECT total_peak_rss_mb, total_peak_system_memory_percent "
                "FROM mapping_attempts"
            ).fetchone()
            self.assertEqual(mapping, (None, None))

    def test_v3_synthesis_timeout_allows_null_unreached_mapping_telemetry(self) -> None:
        timeout = dict(self.rows[0])
        for field in (
            "logic_T",
            "logic_CNOT",
            "logic_depth",
            "logic_gates",
            "engine_qubits",
        ):
            timeout[field] = None
        timeout.update(
            {
                "status": "timeout",
                "stage": "synthesis",
                "error_code": "stage_timeout",
                "error_message": "synthesis exceeded timeout",
                "map_peak_rss_mb": None,
                "map_peak_system_memory_percent": None,
                "map_resource_stage_peaks": None,
                "total_peak_rss_mb": timeout["synth_peak_rss_mb"],
                "total_peak_system_memory_percent": timeout[
                    "synth_peak_system_memory_percent"
                ],
            }
        )
        self.jsonl.write_text(json.dumps(timeout) + "\n", encoding="utf-8")

        rows, _source_sha256 = load_jsonl(self.jsonl)
        self.assertEqual(rows[0]["map_resource_stage_peaks"], {})

        summary = ingest_jsonl(self.jsonl, self.db_path)
        self.assertEqual(summary.status_counts, {"synthesis_timeout": 1})
        with ExperimentDB(self.db_path, read_only=True) as db:
            self.assertEqual(
                db.connection.execute(
                    "SELECT count(*) FROM synthesis_attempts WHERE status='timeout'"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM mapping_attempts").fetchone()[0],
                0,
            )

    def test_v2_and_v3_sources_share_one_semantic_method_spec(self) -> None:
        current_path = self.jsonl.with_name("current-v3.jsonl")
        current_path.write_text(json.dumps(self.rows[0]) + "\n", encoding="utf-8")

        legacy = dict(self.rows[0])
        legacy["schema_version"] = runner.LEGACY_SCHEMA_VERSION
        for field in runner.RESOURCE_ROW_FIELDS:
            legacy.pop(field)
        legacy_path = self.jsonl.with_name("legacy-v2.jsonl")
        legacy_path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

        ingest_jsonl(legacy_path, self.db_path)
        ingest_jsonl(current_path, self.db_path)
        with ExperimentDB(self.db_path, read_only=True) as db:
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM method_specs").fetchone()[0],
                1,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM synthesis_cells").fetchone()[0],
                1,
            )
            self.assertEqual(
                db.connection.execute("SELECT count(*) FROM synthesis_attempts").fetchone()[0],
                2,
            )
            method_spec = db.connection.execute(
                "SELECT spec_json FROM method_specs"
            ).fetchone()[0]
            self.assertNotIn("source_schema_version", json.loads(method_spec)["spec"])

    def test_resource_checkpoint_is_configured_not_claimed_as_learned(self) -> None:
        resource = _successful_row("resource_nmcts")
        resource["model_file"] = "action_scorer_competition.pt"
        resource["model_hash"] = "a" * 64
        display, spec = _method_identity(resource)
        self.assertEqual(display, "resource_nmcts[model-configured:aaaaaaaaaaaa]")
        self.assertEqual(spec["prior_variant"], "model-configured")
        self.assertEqual(spec["model_role"], "optional_candidate_prior")

        neural = dict(resource)
        neural["requested_method"] = "neural_mcts"
        display, spec = _method_identity(neural)
        self.assertEqual(display, "neural_mcts[learned:aaaaaaaaaaaa]")
        self.assertEqual(spec["prior_variant"], "learned")
        self.assertEqual(spec["model_role"], "active_action_prior")

    def test_verification_runtime_knobs_do_not_fragment_transpile_identity(self) -> None:
        first = _successful_row("direct_anf")
        second = json.loads(json.dumps(first))
        second["compile_config"].update(
            {
                "verification_batch_size": 16,
                "aer_max_parallel_threads": 16,
                "aer_max_parallel_experiments": 16,
            }
        )
        self.assertNotEqual(first["compile_config"], second["compile_config"])
        self.assertEqual(_transpile_identity(first), _transpile_identity(second))


if __name__ == "__main__":
    unittest.main()
