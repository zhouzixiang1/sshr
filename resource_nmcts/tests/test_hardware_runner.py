#!/usr/bin/env python3
"""Fast integration checks for the topology-aware hardware runner."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts import run_hardware_validation as runner


class HardwareRunnerIntegrationTests(unittest.TestCase):
    def test_default_checkpoint_is_the_24_feature_competition_model(self) -> None:
        self.assertEqual(runner.DEFAULT_MODEL.name, "action_scorer_competition.pt")

    """Exercise 1 function x 2 methods x 2 real topology targets once."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="hardware-runner-test-")
        cls.output_path = Path(cls._temporary.name) / "small-grid.jsonl"
        common = [
            sys.executable,
            str(_PROJECT_ROOT / "scripts" / "run_hardware_validation.py"),
            "--functions",
            "and3",
            "--methods",
            "direct_anf,greedy_factor",
            "--seeds",
            "3",
            "--targets",
            "cx_full,cx_line",
            "--transpile-seeds",
            "5",
            "--cx-qubits",
            "5",
            "--optimization-level",
            "1",
            "--timeout",
            "60",
            "--max-system-memory-percent",
            "off",
        ]
        environment = os.environ.copy()
        environment["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        cls.completed = subprocess.run(
            [*common, "--output-jsonl", str(cls.output_path)],
            cwd=_PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if cls.completed.returncode != 0:
            raise AssertionError(
                "hardware runner failed\n"
                f"stdout:\n{cls.completed.stdout}\n"
                f"stderr:\n{cls.completed.stderr}"
            )
        cls.rows = [
            json.loads(line)
            for line in cls.output_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        cls.dry_run = subprocess.run(
            [*common, "--dry-run"],
            cwd=_PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if cls.dry_run.returncode != 0:
            raise AssertionError(
                "hardware runner dry-run failed\n"
                f"stdout:\n{cls.dry_run.stdout}\n"
                f"stderr:\n{cls.dry_run.stderr}"
            )
        cls.dry_manifest = json.loads(cls.dry_run.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def test_small_grid_cardinality_and_synthesis_reuse(self) -> None:
        self.assertEqual(len(self.rows), 4)
        self.assertEqual(
            {
                (row["function_id"], row["requested_method"], row["target_name"])
                for row in self.rows
            },
            {
                ("and3", method, target)
                for method in ("direct_anf", "greedy_factor")
                for target in ("cx_full", "cx_line")
            },
        )
        # One synthesis key occurs once per method and is reused across both
        # target compilations; record keys remain mapping-configuration unique.
        key_counts = Counter(row["synthesis_key"] for row in self.rows)
        self.assertEqual(sorted(key_counts.values()), [2, 2])
        self.assertEqual(len({row["record_key"] for row in self.rows}), 4)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in self.rows:
            grouped[row["requested_method"]].append(row)
        for rows in grouped.values():
            self.assertEqual(len({row["synth_time_s"] for row in rows}), 1)
            self.assertEqual(len({row["engine_gates"] for row in rows}), 1)

    def test_jsonl_has_fixed_provenance_schema(self) -> None:
        expected_fields = set(runner.ROW_FIELDS)
        for row in self.rows:
            self.assertEqual(set(row), expected_fields)
            self.assertEqual(row["schema_version"], runner.SCHEMA_VERSION)
            self.assertEqual(row["artifact_source"], "synthesize_artifact")
            self.assertTrue(row["artifact_consistent"])
            self.assertTrue(row["mapping_provenance_consistent"])
            self.assertEqual(row["selected_method"], row["requested_method"])
            for field in (
                "record_key",
                "synthesis_key",
                "function_truth_hash",
                "synthesis_config_hash",
                "compile_config_hash",
                "target_hash",
            ):
                self.assertEqual(len(row[field]), 64, field)
            self.assertEqual(row["target_manifest"]["target_id"], row["target_id"])
            self.assertEqual(row["compile_config"]["seed_transpiler"], 5)
            self.assertEqual(row["resource_monitor_backend"], "psutil")
            self.assertIsNone(row["resource_guard_limit_percent"])
            for field in (
                "synth_peak_rss_mb",
                "synth_peak_system_memory_percent",
                "map_peak_rss_mb",
                "map_peak_system_memory_percent",
                "total_peak_rss_mb",
                "total_peak_system_memory_percent",
            ):
                self.assertIsInstance(row[field], (int, float), field)
                self.assertGreater(row[field], 0.0, field)
            self.assertEqual(
                row["total_peak_rss_mb"],
                max(row["synth_peak_rss_mb"], row["map_peak_rss_mb"]),
            )
            self.assertEqual(
                row["total_peak_system_memory_percent"],
                max(
                    row["synth_peak_system_memory_percent"],
                    row["map_peak_system_memory_percent"],
                ),
            )
            self.assertTrue(row["synth_resource_stage_peaks"])
            self.assertTrue(row["map_resource_stage_peaks"])

    def test_target_legality_native_counts_and_complete_verification(self) -> None:
        for row in self.rows:
            with self.subTest(method=row["requested_method"], target=row["target_name"]):
                self.assertEqual(row["status"], "ok")
                self.assertEqual(row["stage"], "complete")
                self.assertIsNone(row["error_code"])
                self.assertEqual(row["unsupported_instructions"], 0)
                self.assertEqual(row["coupling_violations"], 0)
                self.assertEqual(row["mapped_highq_count"], 0)
                self.assertEqual(len(row["initial_layout"]), row["work_qubits"])
                self.assertEqual(len(row["final_layout"]), row["work_qubits"])
                self.assertEqual(sum(row["native_gate_counts"].values()), row["mapped_gates"])
                self.assertEqual(row["native_cx_count"], row["native_twoq_count"])
                self.assertTrue(row["mapped_verify_ok"])
                self.assertTrue(row["mapped_verification_complete"])
                self.assertEqual(row["mapped_verify_mode"], "exact_xy_phase")
                self.assertEqual(row["mapped_states_evaluated"], 16)
                self.assertEqual(row["mapped_mismatches"], 0)
                self.assertLess(row["mapped_max_leakage"], 1e-8)
                self.assertLess(row["mapped_max_phase_error"], 1e-8)

        full_rows = [row for row in self.rows if row["target_name"] == "cx_full"]
        line_rows = [row for row in self.rows if row["target_name"] == "cx_line"]
        self.assertTrue(all(row["routing_twoq_delta"] == 0 for row in full_rows))
        self.assertTrue(all(row["routing_twoq_delta"] > 0 for row in line_rows))

    def test_dry_run_reports_synthesis_once_map_many_plan(self) -> None:
        self.assertTrue(self.dry_manifest["dry_run"])
        self.assertEqual(self.dry_manifest["synthesis_tasks"], 2)
        self.assertEqual(self.dry_manifest["mapping_rows"], 4)
        self.assertEqual(set(self.dry_manifest["targets"]), {"cx_full", "cx_line"})
        self.assertIsNone(self.dry_manifest["max_system_memory_percent"])

    def test_failure_fields_are_independent_and_machine_readable(self) -> None:
        row = runner._blank_row()
        runner._apply_failure(
            row,
            "timeout",
            {
                "stage": "mapped_verification",
                "error_code": "stage_timeout",
                "error_message": "mapped_verification exceeded 1.000 seconds",
            },
        )
        self.assertEqual(row["status"], "timeout")
        self.assertEqual(row["stage"], "mapped_verification")
        self.assertEqual(row["error_code"], "stage_timeout")
        self.assertIn("exceeded", row["error_message"])

    def test_memory_guard_restarts_only_owned_worker(self) -> None:
        with runner.StageWorker(max_system_memory_percent=0.001) as worker:
            original_pid = worker._proc.pid
            status, payload = worker.run(
                ("unknown-task",), timeout=10.0, initial_stage="guard_test"
            )
            self.assertEqual(status, "error")
            self.assertEqual(payload["error_code"], "resource_guard")
            self.assertEqual(payload["stage"], "guard_test")
            self.assertGreater(payload["peak_system_memory_percent"], 0.001)
            self.assertNotEqual(worker._proc.pid, original_pid)
            self.assertTrue(worker._proc.is_alive())


if __name__ == "__main__":
    unittest.main()
