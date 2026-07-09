#!/usr/bin/env bash
# Rebuild the lightweight submission package from existing experiment artifacts.
#
# This script regenerates paper-facing analysis tables, figures, audit files,
# and the English submission PDF.  It intentionally does not rerun the raw
# benchmark sweeps, external-toolchain probes, or neural training jobs.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/anaconda3/envs/mcts-qoracle/bin/python}"
LATEXMK_BIN="${LATEXMK_BIN:-latexmk}"

cd "$ROOT_DIR"

run_py() {
  local script="$1"
  echo "==> ${PYTHON_BIN} ${script}"
  "$PYTHON_BIN" "$script"
}

echo "==> Using Python: ${PYTHON_BIN}"

run_py analyze_contribution_evidence_map.py
run_py analyze_method_workflow_table.py
run_py analyze_related_work_positioning.py
run_py analyze_baseline_claim_matrix.py
run_py analyze_comparison_evidence_matrix.py
run_py analyze_baseline_comparability_audit.py
run_py analyze_counterpoint_claim_boundary.py
run_py analyze_comparison_protocol_audit.py
run_py analyze_claim_scope_lint.py
run_py analyze_paired_statistical_evidence.py
run_py analyze_paired_effect_uncertainty.py
run_py analyze_multimetric_pareto_tradeoff.py
run_py analyze_search_contribution.py
run_py analyze_boolean_ring_structural_evidence.py
run_py analyze_sparse_depth_frontier.py
run_py analyze_sparse_depth4_gate_sensitivity.py
run_py analyze_learned_control_audit.py
run_py analyze_scaling_resource_audit.py
run_py analyze_weight_robustness.py
run_py analyze_artifact_rerun_registry.py
run_py analyze_reproducibility_audit.py
run_py analyze_submission_metadata_audit.py
run_py validate_submission_metadata.py
run_py make_author_input_packet.py
run_py make_submission_text_preview.py
run_py selftest_submission_metadata_pipeline.py
run_py make_anonymous_review_draft.py
run_py analyze_anonymous_review_readiness.py
run_py make_submission_figures.py
run_py analyze_figure_asset_audit.py
run_py analyze_submission_archive_manifest.py
run_py analyze_submission_traceability_audit.py

echo "==> Building English submission PDF"
(
  cd paper_latex
  "$LATEXMK_BIN" -pdf -interaction=nonstopmode -halt-on-error resource_nmcts_submission_v1.tex
  "$LATEXMK_BIN" -pdf -interaction=nonstopmode -halt-on-error resource_nmcts_submission_anonymous.tex
)

run_py analyze_goal_completion_audit.py
run_py make_submission_payload_archive.py
run_py analyze_payload_roundtrip_audit.py
run_py analyze_payload_extraction_smoke_audit.py
run_py analyze_submission_readiness_audit.py
run_py analyze_submission_package_verifier.py

echo "==> Submission package rebuilt"
