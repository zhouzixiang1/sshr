from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "build_final_primary20_report.py"
SPEC = importlib.util.spec_from_file_location("build_final_primary20_report", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_claim_gate_is_strict_about_zero_touching_intervals() -> None:
    row = {
        "median_delta": -2.0,
        "median_delta_ci_high": -0.1,
        "median_relative_improvement_pct": 10.0,
        "median_relative_improvement_pct_ci_low": 0.1,
        "holm_reject": True,
    }
    assert MODULE.classify_claim(row) == ("strict_significant_better", True)

    row["median_delta_ci_high"] = 0.0
    assert MODULE.classify_claim(row) == (
        "holm_supported_ci_touches_zero",
        False,
    )


def test_checked_in_primary20_inputs_produce_expected_frozen_shape() -> None:
    payload, rows, _ = MODULE.build_summary(
        database=ROOT / "results" / "competition_primary20_final.duckdb",
        stats_dir=ROOT / "results" / "final_stats",
        coverage_path=ROOT
        / "submission_competition"
        / "formal_coverage_audit.json",
        consolidation_manifest_path=ROOT
        / "submission_competition"
        / "formal_primary20_core3_final_manifest_v2.json",
    )
    assert payload["coverage"]["planned_cells"] == 360
    assert payload["coverage"]["verified_cells"] == 354
    assert payload["coverage"]["missing_cells"] == 6
    assert len(payload["coverage"]["missing"]) == 6
    assert {row["requested_method"] for row in payload["coverage"]["missing"]} == {
        "sshr_beam"
    }
    assert len(rows) == 20
    assert sum(row["strict_significant_better"] for row in rows) == 10
    assert payload["analysis_id"].startswith("xa202609-primary20-")

