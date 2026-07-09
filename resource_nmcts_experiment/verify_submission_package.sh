#!/usr/bin/env bash
# Fast pre-upload/artifact check for the already-built submission package.
#
# This script does not rebuild the paper or rerun experiments.  It verifies
# terminal package invariants from the current PDF, payload archive, manifests,
# readiness audit, raw-rerun registry, private metadata/preview protection, and LaTeX log.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/anaconda3/envs/mcts-qoracle/bin/python}"

cd "$ROOT_DIR"

if [[ ! -f submission_package/dist/resource_nmcts_submission_payload.tar.gz ]]; then
  export RESOURCE_NMCTS_EXTRACTED_PAYLOAD="${RESOURCE_NMCTS_EXTRACTED_PAYLOAD:-1}"
fi

"$PYTHON_BIN" analyze_pdf_visual_audit.py
"$PYTHON_BIN" analyze_pdf_text_audit.py
"$PYTHON_BIN" analyze_pdf_metadata_audit.py
"$PYTHON_BIN" analyze_source_path_privacy_audit.py
"$PYTHON_BIN" analyze_author_questionnaire_coverage.py
"$PYTHON_BIN" analyze_author_minimal_form_coverage.py
"$PYTHON_BIN" analyze_metadata_answer_template_coverage.py
"$PYTHON_BIN" validate_submission_metadata.py
"$PYTHON_BIN" make_submission_text_preview.py
"$PYTHON_BIN" analyze_anonymous_review_readiness.py
"$PYTHON_BIN" analyze_author_input_closure_audit.py
"$PYTHON_BIN" analyze_submission_metadata_closure_path.py
"$PYTHON_BIN" analyze_editorial_screening_audit.py
"$PYTHON_BIN" analyze_target_venue_decision_audit.py
"$PYTHON_BIN" analyze_target_venue_policy_checklist.py
"$PYTHON_BIN" analyze_target_venue_format_smoke.py
"$PYTHON_BIN" analyze_submission_support_packet_audit.py
"$PYTHON_BIN" analyze_learning_citation_verification.py
"$PYTHON_BIN" analyze_ros_lut_garbage_proxy.py
"$PYTHON_BIN" analyze_ros_lut_garbage_budget_frontier.py
"$PYTHON_BIN" analyze_ros_lut_checkpoint_optimizer.py
if [[ "${RESOURCE_NMCTS_EXTRACTED_PAYLOAD:-0}" != "1" ]]; then
  "$PYTHON_BIN" analyze_caterpillar_ros_family_probe.py
  "$PYTHON_BIN" run_caterpillar_xag_api_probe.py
fi
"$PYTHON_BIN" analyze_ros_reproduction_gap_audit.py
"$PYTHON_BIN" analyze_novelty_comparison_scorecard.py
"$PYTHON_BIN" analyze_comparison_evidence_matrix.py
"$PYTHON_BIN" analyze_comparison_target_validity_audit.py
"$PYTHON_BIN" analyze_comparison_answer_scorecard.py
"$PYTHON_BIN" analyze_comparison_route_decision_audit.py
"$PYTHON_BIN" analyze_benchmark_suite_audit.py
"$PYTHON_BIN" analyze_benchmark_function_diversity_audit.py
"$PYTHON_BIN" analyze_comparison_support_reference_integrity.py
"$PYTHON_BIN" analyze_sshr_reproduction_scope_audit.py
"$PYTHON_BIN" analyze_weight_robustness.py
"$PYTHON_BIN" analyze_stg_published_benchmark.py
"$PYTHON_BIN" analyze_bitflip_neural_budget_sweep.py
"$PYTHON_BIN" analyze_phase_policy_random_control.py
"$PYTHON_BIN" analyze_stochastic_control_stability.py
"$PYTHON_BIN" analyze_root_action_ranker_audit.py
"$PYTHON_BIN" analyze_phase_rotation_precision_audit.py
"$PYTHON_BIN" analyze_phase_rotation_sequence_smoke_audit.py
"$PYTHON_BIN" analyze_rotation_synthesis_backend_audit.py
"$PYTHON_BIN" analyze_phase_policy_budget_frontier.py
"$PYTHON_BIN" analyze_learned_control_audit.py
"$PYTHON_BIN" analyze_runtime_envelope_audit.py
"$PYTHON_BIN" analyze_threats_to_validity_audit.py
"$PYTHON_BIN" analyze_ultra_scale64_stress.py
"$PYTHON_BIN" analyze_ultra_scale64_resource_profile.py
"$PYTHON_BIN" analyze_resource_weight_sensitivity_audit.py
"$PYTHON_BIN" analyze_cnot_constraint_profile_audit.py
"$PYTHON_BIN" analyze_neural_mcts_claim_calibration.py
"$PYTHON_BIN" analyze_submission_archive_manifest.py
"$PYTHON_BIN" analyze_payload_git_policy_audit.py
if [[ "${RESOURCE_NMCTS_EXTRACTED_PAYLOAD:-0}" != "1" ]]; then
  "$PYTHON_BIN" analyze_payload_roundtrip_audit.py
fi
"$PYTHON_BIN" analyze_goal_completion_audit.py
if [[ "${RESOURCE_NMCTS_EXTRACTED_PAYLOAD:-0}" != "1" ]]; then
  "$PYTHON_BIN" analyze_final_human_gate_audit.py
  "$PYTHON_BIN" analyze_final_upload_sequence_audit.py
  "$PYTHON_BIN" analyze_submission_readiness_audit.py
fi
"$PYTHON_BIN" analyze_public_handoff_freshness_audit.py
"$PYTHON_BIN" analyze_submission_package_verifier.py

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

if command -v rg >/dev/null 2>&1; then
  reports=(
    results/analysis_submission_package_verifier.md
    results/analysis_submission_readiness_audit.md
    results/analysis_comparison_protocol_audit.md
    results/analysis_comparison_target_validity_audit.md
    results/analysis_comparison_answer_scorecard.md
    results/analysis_comparison_route_decision_audit.md
    results/analysis_benchmark_suite_audit.md
    results/analysis_benchmark_function_diversity_audit.md
    results/analysis_comparison_support_reference_integrity.md
    results/analysis_weight_robustness.md
    results/analysis_cnot_constraint_profile_audit.md
    results/analysis_stg_published_benchmark.md
    results/analysis_bitflip_neural_budget_sweep.md
    results/analysis_phase_policy_random_control.md
    results/analysis_stochastic_control_stability.md
    results/analysis_root_action_ranker_audit.md
    results/analysis_phase_rotation_precision_audit.md
    results/analysis_phase_rotation_sequence_smoke_audit.md
    results/analysis_rotation_synthesis_backend_audit.md
    results/analysis_phase_policy_budget_frontier.md
    results/analysis_learned_control_audit.md
    results/analysis_runtime_envelope_audit.md
    results/analysis_threats_to_validity_audit.md
    results/analysis_neural_mcts_claim_calibration.md
    results/analysis_editorial_screening_audit.md
    results/analysis_target_venue_decision_audit.md
    results/analysis_target_venue_policy_checklist.md
    results/analysis_target_venue_format_smoke.md
	    results/analysis_submission_support_packet_audit.md
	    results/analysis_ros_lut_garbage_proxy.md
	    results/analysis_ros_lut_garbage_budget_frontier.md
	    results/analysis_ros_lut_checkpoint_optimizer.md
	    results/analysis_caterpillar_ros_family_probe.md
	    results/analysis_caterpillar_xag_api_probe.md
	    results/analysis_ros_reproduction_gap_audit.md
	    results/analysis_sshr_reproduction_scope_audit.md
	    results/analysis_resource_weight_sensitivity_audit.md
    results/analysis_novelty_comparison_scorecard.md
    results/analysis_screen_scale_ultra_scale64_stress.md
    results/analysis_screen_scale_ultra_scale64_resource_profile.md
    results/analysis_citation_support_audit.md
    results/analysis_learning_citation_verification.md
    results/analysis_author_input_closure_audit.md
    results/analysis_author_questionnaire_coverage.md
    results/analysis_author_minimal_form_coverage.md
    results/analysis_metadata_answer_template_coverage.md
    results/analysis_submission_metadata_closure_path.md
    results/analysis_final_human_gate_audit.md
    results/analysis_final_upload_sequence_audit.md
    results/analysis_headline_numeric_consistency.md
    results/analysis_figure_asset_audit.md
    results/analysis_latex_dependency_audit.md
    results/analysis_submission_archive_manifest.md
    results/analysis_pdf_visual_audit.md
    results/analysis_pdf_text_audit.md
    results/analysis_pdf_metadata_audit.md
    results/analysis_source_path_privacy_audit.md
    results/analysis_submission_metadata_validator.md
    results/analysis_submission_metadata_pipeline_selftest.md
    results/analysis_anonymous_review_readiness.md
    results/analysis_payload_roundtrip_audit.md
    results/analysis_payload_git_policy_audit.md
    results/analysis_payload_extraction_smoke_audit.md
    results/analysis_payload_verifier_smoke_audit.md
    results/analysis_payload_latex_compile_audit.md
    results/analysis_submission_text_preview.md
    results/analysis_submission_payload_archive.md
    results/analysis_public_handoff_freshness_audit.md
  )
  existing_reports=()
  for report in "${reports[@]}"; do
    if [[ -f "$report" ]]; then
      existing_reports+=("$report")
    fi
  done
  if (( ${#existing_reports[@]} > 0 )); then
  rg -n "pass:|needs author input|Payload SHA|Payload Git|Generated payload|tracked=|ignored=|registry_raw|unresolved_count|needs_revision_count|needs_author_input_count|synthetic_only|private_outputs_are_git_ignored|private_payload_hits|manifest_files|archive_files|metadata_issues|reviewer_entries|comparison_protocol_files|comparison_answer_files|comparison answer|comparison target|comparison route|route decision|benchmark suite|Benchmark Suite|benchmark function|function diversity|verified rows across suite|comparison support|reference_count|missing_count|summary_categories|manifest_categories|categories_consistent|target family|SSHR Reproduction|sshr_reproduction|source_tree_available|weight robustness|Weight profiles|compact checks|runtime envelope|Runtime Envelope|wall-clock|threats|Threats|validity|stochastic|Stochastic|seed means|claim-calibration|Claim Calibration|claim anchor|evidence gate|roles=|novelty|scorecard|reviewer question|ultra-scale|resource profile|raw rows|plan ANF verified|emitted-circuit ANF verified|public handoff|handoff|snapshot|PDF pages=|payload_files=|artifact_registry=|source_privacy=|goal_gate=|editorial screening|screening|support_packet_files|support-packet|target venue|target-venue format|ACM TQC|acmart|recommended_first_choice|strong_fit_count|garbage proxy|caterpillar|Caterpillar|compile smoke|standalone CLI|API probe|API row|best API|ros_gap_files|ROS Reproduction|official_ros_fully_reproduced|full_ros_boundary_is_explicit|headline_numeric_files|citation_support_files|learning-citation|primary source|verified adjacent scope|author_input_closure_files|metadata_closure_files|required_metadata_paths|answer_template_required_paths|starter_only_required_paths|remaining_author_paths|closure_path_ready|final upload|upload sequence|sequence_ready|private preview|archive-link|extracted_files|verifier_returncode|extracted_payload_mode|source_verifier_rows|row_delta|expected_row_delta|row_delta_reason|smoke_scripts|compiled_manuscripts|compile seconds|figures=|source rows|claims=|computed|verified_total|dependency_count|Dependency types|tex_input|bibliography|cited_keys|bib_keys|locator|dimensions|ink range|rendered|characters|missing anchors|forbidden hits|identity anchors|encrypted|javascript|forbidden metadata|local_path_files|strict_local_path_files|private_members|old_workspace_path_files|file count|archive sha256|comparison layer|layers=|root-action|budget sweep|low-budget|rotation-precision|rotation-sequence|rotation-synthesis|backend|sequence smoke|precision-sensitive|budget frontier|exact-scores|Eval cut" "${existing_reports[@]}" || true
  fi
fi

echo "Submission package verifier passed."
