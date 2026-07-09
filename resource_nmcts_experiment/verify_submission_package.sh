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

"$PYTHON_BIN" analyze_submission_package_verifier.py

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

if command -v rg >/dev/null 2>&1; then
  rg -n "pass:|needs author input|Payload SHA|registry_raw|unresolved_count|needs_revision_count|needs_author_input_count|synthetic_only|private_outputs_are_git_ignored|private_payload_hits|manifest_files|archive_files|metadata_issues|reviewer_entries|comparison_protocol_files|headline_numeric_files|extracted_files|smoke_scripts|figures=|source rows|claims=|computed|verified_total|dependency_count|Dependency types|tex_input|bibliography|file count|archive sha256|comparison layer|layers=" \
    results/analysis_submission_package_verifier.md \
    results/analysis_submission_readiness_audit.md \
    results/analysis_comparison_protocol_audit.md \
    results/analysis_headline_numeric_consistency.md \
    results/analysis_figure_asset_audit.md \
    results/analysis_latex_dependency_audit.md \
    results/analysis_submission_metadata_validator.md \
    results/analysis_submission_metadata_pipeline_selftest.md \
    results/analysis_anonymous_review_readiness.md \
    results/analysis_payload_roundtrip_audit.md \
    results/analysis_payload_extraction_smoke_audit.md \
    results/analysis_submission_text_preview.md \
    results/analysis_submission_payload_archive.md
fi

echo "Submission package verifier passed."
