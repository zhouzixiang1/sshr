#!/usr/bin/env python3
"""Synthetic-DB tests for strict competition result statistics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.analyze_competition_results import (  # noqa: E402
    _apply_holm,
    _wilcoxon,
    analyze_database,
    parse_required_seeds,
    paired_rank_biserial,
    write_json,
    write_tidy_csv,
)
from src.experiment_db import ExperimentDB  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class CompetitionResultAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "synthetic.duckdb"
        self._build_database()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _build_database(self) -> None:
        with ExperimentDB(self.db_path) as db:
            experiment = db.create_experiment(
                "competition-analysis-test",
                "Synthetic strict-pairing test",
                objective={"direction": "lower is better"},
            )
            batch = db.create_run_batch(
                experiment,
                "batch",
                config={"seeds": list(range(6))},
                planned_cell_count=14,
            )
            function = db.register_boolean_function(
                "maj3",
                3,
                {"n": 3, "truth_table_hex": "e8"},
                truth_table_hex="e8",
                metadata={"family": "structured"},
            )
            case = db.register_benchmark_case(
                experiment,
                function,
                "maj3",
                suite="frozen-suite-v1",
            )
            baseline = db.register_method_spec(
                "baseline",
                {"kind": "reference"},
                code_revision="test",
            )
            candidate = db.register_method_spec(
                "resource_nmcts",
                {"kind": "candidate"},
                model_sha256="a" * 64,
                code_revision="test",
            )
            target = db.register_hardware_target(
                "cx-line-5",
                5,
                {"basis_gates": ["rz", "sx", "x", "cx"], "edges": [[0, 1], [1, 2]]},
            )
            spec_a = db.register_transpile_spec(
                target,
                "sabre-seed-7",
                {"seed": 7, "layout_method": "sabre", "routing_method": "sabre"},
            )
            spec_b = db.register_transpile_spec(
                target,
                "sabre-seed-11",
                {"seed": 11, "layout_method": "sabre", "routing_method": "sabre"},
            )

            attempts: dict[tuple[str, int], object] = {}
            candidate_t = {0: 8, 1: 7, 2: None, 4: 8, 5: 9}
            candidate_cnot = {0: 18, 1: 17, 2: 19, 4: 20, 5: 17}
            for seed in range(6):
                baseline_cell = db.get_or_create_cell(
                    experiment, case, baseline, seed, batch_id=batch, ordinal=2 * seed
                )
                baseline_attempt = db.record_synthesis_attempt(
                    baseline_cell,
                    batch,
                    "success",
                    selected_method="baseline",
                    runtime_s=2.0,
                    logical_metrics={
                        "t_count": 10,
                        "cnot_count": 20,
                        "depth": 20,
                        "gate_count": 25,
                        "ancilla_count": 1,
                        "n_qubits": 5,
                        "weighted_score": 11.0,
                    },
                )
                db.record_verification(
                    "logical",
                    baseline_attempt.attempt_id,
                    "truth-table",
                    "pass",
                    passed=True,
                )
                attempts[("baseline", seed)] = baseline_attempt

                if seed == 3:
                    continue
                candidate_cell = db.get_or_create_cell(
                    experiment, case, candidate, seed, batch_id=batch, ordinal=2 * seed + 1
                )
                candidate_attempt = db.record_synthesis_attempt(
                    candidate_cell,
                    batch,
                    "success",
                    selected_method="resource_nmcts",
                    runtime_s=1.0,
                    logical_metrics={
                        "t_count": candidate_t[seed],
                        "cnot_count": candidate_cnot[seed],
                        "depth": candidate_cnot[seed],
                        "gate_count": candidate_cnot[seed] + 2,
                        "ancilla_count": 1,
                        "n_qubits": 5,
                        "weighted_score": float(candidate_t[seed] or 8),
                    },
                )
                if seed != 1:
                    db.record_verification(
                        "logical",
                        candidate_attempt.attempt_id,
                        "truth-table",
                        "pass",
                        passed=True,
                    )
                attempts[("candidate", seed)] = candidate_attempt

            # A second independent function contributes only one paired seed and
            # is slightly worse.  If seed rows were incorrectly treated as
            # independent, the three valid maj3 seeds would outweigh this
            # function.  Correct inference has exactly two units: maj3 and xor3.
            second_function = db.register_boolean_function(
                "xor3",
                3,
                {"n": 3, "truth_table_hex": "96"},
                truth_table_hex="96",
                metadata={"family": "structured"},
            )
            second_case = db.register_benchmark_case(
                experiment,
                second_function,
                "xor3",
                suite="frozen-suite-v1",
            )
            second_baseline_cell = db.get_or_create_cell(
                experiment, second_case, baseline, 0, batch_id=batch, ordinal=12
            )
            second_baseline_attempt = db.record_synthesis_attempt(
                second_baseline_cell,
                batch,
                "success",
                selected_method="baseline",
                logical_metrics={
                    "t_count": 10,
                    "cnot_count": 20,
                    "depth": 20,
                    "gate_count": 25,
                    "ancilla_count": 1,
                    "n_qubits": 5,
                    "weighted_score": 11.0,
                },
            )
            db.record_verification(
                "logical",
                second_baseline_attempt.attempt_id,
                "truth-table",
                "pass",
                passed=True,
            )
            second_candidate_cell = db.get_or_create_cell(
                experiment, second_case, candidate, 0, batch_id=batch, ordinal=13
            )
            second_candidate_attempt = db.record_synthesis_attempt(
                second_candidate_cell,
                batch,
                "success",
                selected_method="resource_nmcts",
                logical_metrics={
                    "t_count": 11,
                    "cnot_count": 21,
                    "depth": 21,
                    "gate_count": 26,
                    "ancilla_count": 1,
                    "n_qubits": 5,
                    "weighted_score": 12.0,
                },
            )
            db.record_verification(
                "logical",
                second_candidate_attempt.attempt_id,
                "truth-table",
                "pass",
                passed=True,
            )

            def map_attempt(
                owner: object,
                spec: object,
                *,
                total: int | None,
                depth: int,
                verified: bool = True,
                target_violations: int = 0,
            ) -> None:
                mapping = db.record_mapping_attempt(
                    owner.attempt_id,
                    batch,
                    spec,
                    "success",
                    seed_transpiler=7,
                    mapping_metrics={
                        "total_gate_count": total,
                        "one_qubit_gate_count": None if total is None else total // 2,
                        "two_qubit_gate_count": None if total is None else total // 2,
                        "native_entangling_count": None if total is None else total // 2,
                        "swap_count": 0,
                        "depth": depth,
                        "two_qubit_depth": depth // 2,
                        "target_violation_count": target_violations,
                        "direction_violation_count": 0,
                        "routing_overhead": 1.0,
                        "estimated_error": 0.01,
                    },
                )
                if verified:
                    db.record_verification(
                        "mapping",
                        mapping.attempt_id,
                        "full-oracle-statevector",
                        "pass",
                        passed=True,
                    )

            # Exact spec A: one eligible pair plus four different explicit exclusions.
            map_attempt(attempts[("baseline", 0)], spec_a, total=100, depth=60)
            map_attempt(attempts[("candidate", 0)], spec_a, total=80, depth=50)
            map_attempt(attempts[("baseline", 1)], spec_a, total=100, depth=60)
            map_attempt(attempts[("candidate", 1)], spec_a, total=75, depth=45)
            map_attempt(attempts[("baseline", 2)], spec_a, total=100, depth=60)
            map_attempt(attempts[("candidate", 2)], spec_a, total=85, depth=52, verified=False)
            map_attempt(attempts[("baseline", 3)], spec_a, total=100, depth=60)
            map_attempt(attempts[("baseline", 4)], spec_a, total=100, depth=60)
            map_attempt(
                attempts[("candidate", 4)],
                spec_a,
                total=82,
                depth=49,
                target_violations=1,
            )
            map_attempt(attempts[("baseline", 5)], spec_a, total=100, depth=60)
            map_attempt(attempts[("candidate", 5)], spec_a, total=None, depth=55)

            # Spec B is deliberately attempted on opposite sides/different seeds.
            # A correct analysis must not cross-pair these observations.
            map_attempt(attempts[("baseline", 0)], spec_b, total=95, depth=58)
            map_attempt(attempts[("candidate", 2)], spec_b, total=70, depth=44)

    def _analyze(self, required_seeds: tuple[int, ...] = ()) -> dict[str, object]:
        return analyze_database(
            self.db_path,
            reference_methods=["baseline"],
            candidate_methods=["resource_nmcts"],
            required_seeds=required_seeds,
            bootstrap_samples=250,
            bootstrap_seed=1234,
        )

    def test_function_is_inference_unit_not_repeated_seed(self) -> None:
        result = self._analyze()
        row = next(
            item
            for item in result["summaries"]
            if item["scope"] == "logical" and item["metric"] == "t_count"
        )
        self.assertEqual(row["n_candidate_keys"], 7)
        self.assertEqual(row["n_function_candidate_keys"], 2)
        self.assertEqual(row["n_seed_pairs"], 4)
        self.assertEqual(row["n_pairs"], 2)
        self.assertEqual(row["inference_unit"], "independent_boolean_function")
        self.assertEqual((row["win_count"], row["tie_count"], row["loss_count"]), (1, 0, 1))
        self.assertLess(row["mean_delta"], 0.0)
        self.assertGreater(row["mean_relative_improvement_pct"], 0.0)
        self.assertAlmostEqual(row["rank_biserial"], 1.0 / 3.0)
        self.assertEqual(row["wilcoxon_nonzero_pairs"], 2)
        self.assertEqual(row["n_functions_complete_observed"], 1)
        self.assertEqual(row["n_functions_incomplete_observed"], 1)
        self.assertEqual(row["seed_pairs_per_function_min"], 1)
        self.assertEqual(row["seed_pairs_per_function_median"], 2.0)
        self.assertEqual(row["seed_pairs_per_function_max"], 3)
        completeness = json.loads(row["function_seed_completeness_json"])
        self.assertEqual(
            sorted(
                (
                    value["observed_candidate_seeds"],
                    value["metric_valid_paired_seeds"],
                    value["complete_within_observed_keys"],
                )
                for value in completeness.values()
            ),
            [(1, 1, True), (6, 3, False)],
        )
        self.assertGreaterEqual(row["holm_p_adjusted"], row["wilcoxon_p_raw"])
        self.assertGreaterEqual(row["global_holm_p_adjusted"], row["wilcoxon_p_raw"])
        self.assertEqual(result["statistics"]["wilcoxon"]["zero_method"], "wilcox")
        self.assertIn("discarded", result["statistics"]["wilcoxon"]["zero_policy"])
        self.assertEqual(result["statistics"]["inference_unit"], "independent Boolean function")
        self.assertEqual(_wilcoxon([0.0, 0.0]), (0.0, 1.0, 0))
        self.assertEqual(paired_rank_biserial([0.0, 0.0]), 0.0)

    def test_required_seed_primary_drops_entire_incomplete_function(self) -> None:
        result = self._analyze((0, 4, 5))
        row = next(
            item
            for item in result["summaries"]
            if item["scope"] == "logical" and item["metric"] == "t_count"
        )
        self.assertEqual(row["analysis_mode"], "required_seed_complete_case_primary")
        self.assertEqual(json.loads(row["required_seeds_json"]), [0, 4, 5])
        self.assertEqual(row["n_required_seeds"], 3)
        self.assertEqual(row["n_function_candidate_keys"], 2)
        self.assertEqual(row["n_candidate_keys"], 6)
        self.assertEqual(row["n_seed_pairs_available"], 4)
        self.assertEqual(row["n_seed_pairs"], 3)
        self.assertEqual(row["n_pairs"], 1)
        self.assertEqual(row["n_functions_required_seed_complete"], 1)
        self.assertEqual(row["n_functions_required_seed_incomplete"], 1)
        self.assertEqual((row["win_count"], row["tie_count"], row["loss_count"]), (1, 0, 0))
        completeness = json.loads(row["function_seed_completeness_json"])
        complete, incomplete = sorted(
            completeness.values(), key=lambda item: item["metric_valid_paired_seeds"], reverse=True
        )
        self.assertTrue(complete["eligible_for_inference"])
        self.assertEqual(complete["metric_valid_seed_ids"], [0, 4, 5])
        self.assertFalse(incomplete["eligible_for_inference"])
        self.assertEqual(incomplete["metric_valid_seed_ids"], [0])
        self.assertEqual(incomplete["missing_or_invalid_required_seeds"], [4, 5])
        function_exclusions = [
            item
            for item in result["exclusions"]
            if item["scope"] == "logical"
            and item["metric"] == "t_count"
            and item["reason"] == "function_incomplete_required_seed_set"
        ]
        self.assertEqual(len(function_exclusions), 1)
        self.assertEqual(function_exclusions[0]["exclusion_level"], "function")
        self.assertIsNone(function_exclusions[0]["seed"])
        self.assertEqual(function_exclusions[0]["missing_or_invalid_required_seeds"], [4, 5])
        self.assertEqual(result["filters"]["required_seeds"], [0, 4, 5])
        self.assertEqual(result["statistics"]["required_seeds"], [0, 4, 5])

    def test_one_or_two_required_seeds_cannot_masquerade_as_complete(self) -> None:
        result = self._analyze((0, 1, 4))
        row = next(
            item
            for item in result["summaries"]
            if item["scope"] == "logical" and item["metric"] == "t_count"
        )
        self.assertEqual(row["n_seed_pairs_available"], 3)
        self.assertEqual(row["n_seed_pairs"], 0)
        self.assertEqual(row["n_pairs"], 0)
        self.assertEqual(row["n_functions_required_seed_complete"], 0)
        self.assertEqual(row["n_functions_required_seed_incomplete"], 2)
        self.assertIsNone(row["wilcoxon_p_raw"])
        function_exclusions = [
            item
            for item in result["exclusions"]
            if item["scope"] == "logical"
            and item["metric"] == "t_count"
            and item["reason"] == "function_incomplete_required_seed_set"
        ]
        self.assertEqual(len(function_exclusions), 2)

    def test_required_seed_contract_applies_inside_exact_mapping_context(self) -> None:
        result = self._analyze((0,))
        row = next(
            item
            for item in result["summaries"]
            if item["scope"] == "mapping"
            and item["metric"] == "total_gate_count"
            and item["transpile_spec_name"] == "sabre-seed-7"
        )
        self.assertEqual(row["n_function_candidate_keys"], 2)
        self.assertEqual(row["n_seed_pairs_available"], 1)
        self.assertEqual(row["n_seed_pairs"], 1)
        self.assertEqual(row["n_pairs"], 1)
        self.assertEqual(row["n_functions_required_seed_complete"], 1)
        self.assertEqual(row["n_functions_required_seed_incomplete"], 1)

    def test_required_seed_cli_parser_is_strict_and_canonical(self) -> None:
        self.assertEqual(parse_required_seeds("29,7,17"), (7, 17, 29))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_required_seeds("7,7")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_required_seeds("7,-1")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_required_seeds("7,")

    def test_holm_adjustment_is_step_down_and_monotone(self) -> None:
        rows = []
        for metric, p_value in (("a", 0.01), ("b", 0.04), ("c", 0.03)):
            rows.append(
                {
                    "wilcoxon_p_raw": p_value,
                    "experiment_id": "e",
                    "suite": "s",
                    "scope": "logical",
                    "target_id": None,
                    "reference_method_spec_id": "r",
                    "candidate_method_spec_id": "c",
                    "metric": metric,
                }
            )
        _apply_holm(rows, 0.05)
        adjusted = {row["metric"]: row["holm_p_adjusted"] for row in rows}
        self.assertAlmostEqual(adjusted["a"], 0.03)
        self.assertAlmostEqual(adjusted["c"], 0.06)
        self.assertAlmostEqual(adjusted["b"], 0.06)
        self.assertTrue(rows[0]["holm_reject"])
        self.assertFalse(rows[1]["holm_reject"])

    def test_frozen_hypothesis_families_and_global_sensitivity_are_separate(self) -> None:
        result = self._analyze()

        def get(scope: str, metric: str, spec_name: str | None = None) -> dict[str, object]:
            return next(
                row
                for row in result["summaries"]
                if row["scope"] == scope
                and row["metric"] == metric
                and (spec_name is None or row["transpile_spec_name"] == spec_name)
            )

        logical_t = get("logical", "t_count")
        logical_cnot = get("logical", "cnot_count")
        logical_depth = get("logical", "depth")
        mapped_native = get("mapping", "native_entangling_count", "sabre-seed-7")
        mapped_depth = get("mapping", "mapped_depth", "sabre-seed-7")
        mapped_total = get("mapping", "total_gate_count", "sabre-seed-7")
        self.assertEqual(logical_t["holm_family"], "logical_primary")
        self.assertEqual(logical_cnot["holm_family"], "logical_primary")
        self.assertEqual(logical_depth["holm_family"], "logical_secondary")
        self.assertEqual(mapped_native["holm_family"], "mapping_primary")
        self.assertEqual(mapped_depth["holm_family"], "mapping_primary")
        self.assertEqual(mapped_total["holm_family"], "mapping_secondary")
        self.assertEqual(logical_t["holm_family_size"], 2)
        self.assertEqual(mapped_native["holm_family_size"], 2)
        self.assertEqual(
            logical_t["global_holm_family"],
            "global_sensitivity_all_emitted_hypotheses",
        )
        self.assertGreaterEqual(
            logical_t["global_holm_family_size"], logical_t["holm_family_size"]
        )
        families = result["statistics"]["multiple_testing"]["frozen_families"]
        self.assertEqual(
            families["logical_primary"]["database_metrics"],
            ["t_count", "cnot_count"],
        )
        self.assertEqual(
            families["mapping_primary"]["database_metrics"],
            ["native_entangling_count", "mapped_depth"],
        )

    def test_coverage_metadata_refuses_to_infer_timeouts_from_success_only_db(self) -> None:
        result = self._analyze()
        boundary = result["coverage_boundary"]
        self.assertTrue(boundary["quality_statistics_only"])
        self.assertTrue(boundary["requires_external_recovery_manifest"])
        self.assertEqual(
            boundary["timeouts_and_planned_coverage_status"],
            "not_inferred_from_this_analysis_database",
        )
        self.assertFalse(boundary["cross_experiment_pooling"])
        self.assertTrue(boundary["formal_claim_requires_consolidated_frozen_experiment"])
        self.assertFalse(result["statistics"]["cross_experiment_pooling"])
        self.assertEqual(len(result["input"]["experiment_partitions"]), 1)
        self.assertEqual(len(result["statistics"]["analysis_contract_sha256"]), 64)

    def test_unverified_missing_illegal_and_metric_missing_are_excluded(self) -> None:
        result = self._analyze()
        t_row = next(
            item
            for item in result["summaries"]
            if item["scope"] == "logical" and item["metric"] == "t_count"
        )
        reasons = json.loads(t_row["exclusion_counts_json"])
        self.assertEqual(reasons["candidate_logical_unverified"], 1)
        self.assertEqual(reasons["candidate_metric_missing_or_nonfinite"], 1)
        self.assertEqual(reasons["missing_candidate_cell"], 1)

        spec_a_total = next(
            item
            for item in result["summaries"]
            if item["scope"] == "mapping"
            and item["metric"] == "total_gate_count"
            and item["transpile_spec_name"] == "sabre-seed-7"
        )
        self.assertEqual(spec_a_total["n_candidate_keys"], 6)
        self.assertEqual(spec_a_total["n_paired_view_verified_keys"], 3)
        self.assertEqual(spec_a_total["n_base_eligible_pairs"], 2)
        self.assertEqual(spec_a_total["n_pairs"], 1)
        self.assertEqual(spec_a_total["win_count"], 1)
        self.assertEqual(spec_a_total["mean_delta"], -20.0)
        self.assertEqual(spec_a_total["mean_relative_improvement_pct"], 20.0)
        mapping_reasons = json.loads(spec_a_total["exclusion_counts_json"])
        self.assertEqual(mapping_reasons["candidate_logical_unverified"], 1)
        self.assertEqual(mapping_reasons["candidate_mapping_unverified"], 1)
        self.assertEqual(mapping_reasons["missing_candidate_cell"], 1)
        self.assertEqual(mapping_reasons["candidate_target_violation"], 1)
        self.assertEqual(mapping_reasons["candidate_metric_missing_or_nonfinite"], 1)

        spec_b_total = next(
            item
            for item in result["summaries"]
            if item["scope"] == "mapping"
            and item["metric"] == "total_gate_count"
            and item["transpile_spec_name"] == "sabre-seed-11"
        )
        self.assertEqual(spec_b_total["n_candidate_keys"], 2)
        self.assertEqual(spec_b_total["n_pairs"], 0)
        self.assertIsNone(spec_b_total["wilcoxon_p_raw"])
        self.assertEqual(spec_b_total["n_excluded"], 2)

    def test_analysis_is_read_only_deterministic_and_writes_tidy_outputs(self) -> None:
        before = sha256_file(self.db_path)
        first = self._analyze()
        middle = sha256_file(self.db_path)
        second = self._analyze()
        after = sha256_file(self.db_path)
        self.assertEqual(before, middle)
        self.assertEqual(middle, after)
        self.assertTrue(first["input"]["opened_read_only"])
        self.assertTrue(first["input"]["database_unchanged"])
        self.assertEqual(first["summaries"], second["summaries"])
        self.assertEqual(first["exclusions"], second["exclusions"])

        csv_path = self.root / "summary.csv"
        json_path = self.root / "summary.json"
        write_tidy_csv(csv_path, first["summaries"])
        write_json(json_path, first)
        with csv_path.open("r", encoding="utf-8", newline="") as stream:
            csv_rows = list(csv.DictReader(stream))
        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(csv_rows), first["summary_row_count"])
        self.assertEqual(json_payload["exclusion_row_count"], len(first["exclusions"]))
        self.assertIn("n_pairs", csv_rows[0])
        self.assertIn("analysis_mode", csv_rows[0])
        self.assertIn("required_seeds_json", csv_rows[0])
        self.assertIn("holm_p_adjusted", csv_rows[0])
        self.assertGreater(json_payload["exclusion_row_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
