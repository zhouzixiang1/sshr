#!/usr/bin/env bash
# Rebuild the lightweight submission package from existing experiment artifacts.
#
# This script regenerates paper-facing analysis tables, figures, audit files,
# and the English submission PDF.  It intentionally does not rerun the raw
# benchmark sweeps, most external-toolchain probes, or neural training jobs.
# It does rerun the bounded Caterpillar API probe because it is a fast local
# compile/run check that protects the ROS-facing comparison boundary.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/anaconda3/envs/mcts-qoracle/bin/python}"
LATEXMK_BIN="${LATEXMK_BIN:-latexmk}"
PDFLATEX_BIN="${PDFLATEX_BIN:-pdflatex}"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1767225600}"

export SOURCE_DATE_EPOCH
export FORCE_SOURCE_DATE="${FORCE_SOURCE_DATE:-1}"
export TZ="${TZ:-UTC}"

cd "$ROOT_DIR"

run_py() {
  local script="$1"
  echo "==> ${PYTHON_BIN} ${script}"
  "$PYTHON_BIN" "$script"
}

echo "==> Using Python: ${PYTHON_BIN}"

run_py analyze_contribution_evidence_map.py
run_py analyze_novelty_comparison_scorecard.py
run_py analyze_method_workflow_table.py
run_py analyze_algorithm_contract_table.py
run_py analyze_search_budget_contract.py
run_py analyze_related_work_positioning.py
run_py analyze_citation_support_audit.py
run_py analyze_baseline_claim_matrix.py
run_py run_caterpillar_xag_api_probe.py
run_py analyze_comparison_evidence_matrix.py
run_py analyze_baseline_comparability_audit.py
run_py analyze_counterpoint_claim_boundary.py
run_py analyze_comparison_protocol_audit.py
run_py analyze_comparison_target_validity_audit.py
run_py analyze_comparison_answer_scorecard.py
run_py analyze_sshr_reproduction_scope_audit.py
run_py analyze_claim_scope_lint.py
run_py analyze_stg_published_benchmark.py
run_py analyze_traditional_structure_mechanism.py
echo "==> ${PYTHON_BIN} analyze_ros_lut_line_sensitivity.py"
"$PYTHON_BIN" analyze_ros_lut_line_sensitivity.py \
  --internal results/raw_traditional_resource.csv \
  --internal results/raw_highdim_resource.csv \
  --internal results/raw_highdim_scale_resource.csv \
  --internal results/raw_ultra_highdim_resource.csv \
  --internal results/raw_mega_highdim_resource.csv \
	  --ancilla-weights 10,25
run_py analyze_ros_lut_garbage_proxy.py
run_py analyze_ros_lut_garbage_budget_frontier.py
run_py analyze_ros_lut_checkpoint_optimizer.py
run_py analyze_caterpillar_ros_family_probe.py
run_py analyze_ros_reproduction_gap_audit.py
run_py analyze_paired_statistical_evidence.py
run_py analyze_paired_effect_uncertainty.py
run_py analyze_multimetric_pareto_tradeoff.py
run_py analyze_search_contribution.py
run_py analyze_bitflip_random_prior_control.py
run_py analyze_bitflip_neural_budget_sweep.py
run_py analyze_frontier_random_depth_control.py
run_py analyze_phase_rotation_precision_audit.py
run_py analyze_phase_rotation_sequence_smoke_audit.py
run_py analyze_rotation_synthesis_backend_audit.py
run_py analyze_phase_policy_budget_frontier.py
run_py analyze_search_control_baseline_audit.py
run_py analyze_boolean_ring_structural_evidence.py
run_py analyze_sparse_depth_frontier.py
run_py analyze_sparse_depth4_gate_sensitivity.py
echo "==> ${PYTHON_BIN} analyze_schedule_metrics.py"
"$PYTHON_BIN" analyze_schedule_metrics.py \
  --input schedule_generalization=results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv \
  --input schedule_truth_bridge=results/raw_schedule_truth_bridge_terms.csv \
  --input schedule_truth_bridge_n23=results/raw_schedule_truth_bridge_n23_terms.csv \
  --summary results/summary_schedule_metrics.csv \
  --out results/analysis_schedule_metrics.md \
  --latex-out paper_latex/tables/schedule_metrics.tex
run_py analyze_schedule_proxy_audit.py
run_py analyze_root_action_ranker_audit.py
run_py analyze_learned_control_audit.py
run_py analyze_ultra_scale64_stress.py
run_py analyze_ultra_scale64_resource_profile.py
run_py analyze_scaling_resource_audit.py
run_py analyze_weight_robustness.py
run_py analyze_resource_weight_sensitivity_audit.py
run_py analyze_cnot_constraint_profile_audit.py
run_py analyze_artifact_rerun_registry.py
run_py analyze_reproducibility_audit.py
run_py analyze_submission_metadata_audit.py
run_py validate_submission_metadata.py
run_py make_author_input_packet.py
run_py analyze_author_questionnaire_coverage.py
run_py make_submission_text_preview.py
run_py selftest_submission_metadata_pipeline.py
run_py make_anonymous_review_draft.py
run_py make_acm_tqc_review_draft.py
run_py analyze_anonymous_review_readiness.py
run_py analyze_author_input_closure_audit.py
run_py make_submission_figures.py
run_py analyze_figure_asset_audit.py
run_py analyze_headline_numeric_consistency.py
run_py analyze_submission_archive_manifest.py
run_py analyze_threats_to_validity_audit.py
run_py analyze_neural_mcts_claim_calibration.py
run_py analyze_submission_traceability_audit.py

echo "==> Building English submission PDF"
(
  cd paper_latex
  rm -f resource_nmcts_submission_{v1,anonymous,acm_tqc}.{aux,bbl,blg,fdb_latexmk,fls,out,log,toc,lof,lot}
  "$LATEXMK_BIN" -pdf -g -interaction=nonstopmode -halt-on-error resource_nmcts_submission_v1.tex
  "$LATEXMK_BIN" -pdf -g -interaction=nonstopmode -halt-on-error resource_nmcts_submission_anonymous.tex
  "$LATEXMK_BIN" -pdf -g -interaction=nonstopmode -halt-on-error resource_nmcts_submission_acm_tqc.tex
)

run_py analyze_pdf_visual_audit.py
run_py analyze_pdf_text_audit.py
run_py analyze_pdf_metadata_audit.py
run_py analyze_goal_completion_audit.py
run_py analyze_submission_metadata_closure_path.py
run_py analyze_editorial_screening_audit.py
run_py analyze_target_venue_decision_audit.py
run_py analyze_target_venue_format_smoke.py
run_py analyze_submission_support_packet_audit.py
run_py make_submission_payload_archive.py
run_py analyze_payload_git_policy_audit.py
run_py analyze_latex_dependency_audit.py
run_py analyze_payload_roundtrip_audit.py
run_py analyze_source_path_privacy_audit.py
run_py analyze_payload_extraction_smoke_audit.py
run_py analyze_payload_latex_compile_audit.py
run_py analyze_payload_verifier_smoke_audit.py
run_py analyze_submission_readiness_audit.py
run_py analyze_public_handoff_freshness_audit.py
run_py analyze_submission_package_verifier.py

echo "==> Submission package rebuilt"
