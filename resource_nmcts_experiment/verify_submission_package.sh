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
"$PYTHON_BIN" analyze_submission_metadata_closure_path.py
"$PYTHON_BIN" analyze_editorial_screening_audit.py
"$PYTHON_BIN" analyze_submission_support_packet_audit.py
"$PYTHON_BIN" analyze_ros_reproduction_gap_audit.py
"$PYTHON_BIN" analyze_submission_package_verifier.py

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

if command -v rg >/dev/null 2>&1; then
  reports=(
    results/analysis_submission_package_verifier.md
    results/analysis_submission_readiness_audit.md
    results/analysis_comparison_protocol_audit.md
    results/analysis_editorial_screening_audit.md
    results/analysis_submission_support_packet_audit.md
    results/analysis_ros_reproduction_gap_audit.md
    results/analysis_citation_support_audit.md
    results/analysis_author_input_closure_audit.md
    results/analysis_submission_metadata_closure_path.md
    results/analysis_headline_numeric_consistency.md
    results/analysis_figure_asset_audit.md
    results/analysis_latex_dependency_audit.md
    results/analysis_pdf_visual_audit.md
    results/analysis_pdf_text_audit.md
    results/analysis_pdf_metadata_audit.md
    results/analysis_source_path_privacy_audit.md
    results/analysis_submission_metadata_validator.md
    results/analysis_submission_metadata_pipeline_selftest.md
    results/analysis_anonymous_review_readiness.md
    results/analysis_payload_roundtrip_audit.md
    results/analysis_payload_extraction_smoke_audit.md
    results/analysis_payload_verifier_smoke_audit.md
    results/analysis_payload_latex_compile_audit.md
    results/analysis_submission_text_preview.md
    results/analysis_submission_payload_archive.md
  )
  existing_reports=()
  for report in "${reports[@]}"; do
    if [[ -f "$report" ]]; then
      existing_reports+=("$report")
    fi
  done
  if (( ${#existing_reports[@]} > 0 )); then
    rg -n "pass:|needs author input|Payload SHA|registry_raw|unresolved_count|needs_revision_count|needs_author_input_count|synthetic_only|private_outputs_are_git_ignored|private_payload_hits|manifest_files|archive_files|metadata_issues|reviewer_entries|comparison_protocol_files|editorial screening|screening|support_packet_files|support-packet|ros_gap_files|ROS Reproduction|official_ros_fully_reproduced|full_ros_boundary_is_explicit|headline_numeric_files|citation_support_files|author_input_closure_files|metadata_closure_files|required_metadata_paths|closure_path_ready|extracted_files|verifier_returncode|extracted_payload_mode|smoke_scripts|compiled_manuscripts|compile seconds|figures=|source rows|claims=|computed|verified_total|dependency_count|Dependency types|tex_input|bibliography|cited_keys|bib_keys|locator|dimensions|ink range|rendered|characters|missing anchors|forbidden hits|identity anchors|encrypted|javascript|forbidden metadata|local_path_files|strict_local_path_files|private_members|old_workspace_path_files|file count|archive sha256|comparison layer|layers=" "${existing_reports[@]}" || true
  fi
fi

echo "Submission package verifier passed."
