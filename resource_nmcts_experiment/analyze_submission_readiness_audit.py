#!/usr/bin/env python3
"""Audit the submission draft for paper-level readiness markers.

This does not judge scientific merit.  It checks whether the current LaTeX
submission draft exposes the elements reviewers and editors usually look for:
bounded claims, baseline fairness, reproducibility, availability, limitations,
and a clean compiled PDF.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
REBUILD_SCRIPT = THIS_DIR / "rebuild_submission_package.sh"
VERIFY_SCRIPT = THIS_DIR / "verify_submission_package.sh"
ARCHIVE_ANALYSIS = RESULTS / "analysis_submission_archive_manifest.md"
ARCHIVE_SUMMARY = RESULTS / "summary_submission_archive_manifest.csv"
ARCHIVE_MANIFEST = RESULTS / "manifest_submission_archive_manifest.json"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
AUTHOR_INPUT_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
PAYLOAD_ARCHIVE = SUBMISSION_PACKAGE / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA256 = SUBMISSION_PACKAGE / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
PAYLOAD_ANALYSIS = RESULTS / "analysis_submission_payload_archive.md"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
VERIFIER_ANALYSIS = RESULTS / "analysis_submission_package_verifier.md"
VERIFIER_SUMMARY = RESULTS / "summary_submission_package_verifier.csv"
VERIFIER_MANIFEST = RESULTS / "manifest_submission_package_verifier.json"
METADATA_ANALYSIS = RESULTS / "analysis_submission_metadata_audit.md"
METADATA_SUMMARY = RESULTS / "summary_submission_metadata_audit.csv"
METADATA_MANIFEST = RESULTS / "manifest_submission_metadata_audit.json"
METADATA_VALIDATOR_ANALYSIS = RESULTS / "analysis_submission_metadata_validator.md"
METADATA_VALIDATOR_SUMMARY = RESULTS / "summary_submission_metadata_validator.csv"
METADATA_VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_ANALYSIS = RESULTS / "analysis_submission_text_preview.md"
TEXT_PREVIEW_SUMMARY = RESULTS / "summary_submission_text_preview.csv"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
METADATA_PIPELINE_SELFTEST_ANALYSIS = RESULTS / "analysis_submission_metadata_pipeline_selftest.md"
METADATA_PIPELINE_SELFTEST_SUMMARY = RESULTS / "summary_submission_metadata_pipeline_selftest.csv"
METADATA_PIPELINE_SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_REVIEW_ANALYSIS = RESULTS / "analysis_anonymous_review_readiness.md"
ANONYMOUS_REVIEW_SUMMARY = RESULTS / "summary_anonymous_review_readiness.csv"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
AUTHOR_INPUT_CLOSURE_ANALYSIS = RESULTS / "analysis_author_input_closure_audit.md"
AUTHOR_INPUT_CLOSURE_SUMMARY = RESULTS / "summary_author_input_closure_audit.csv"
AUTHOR_INPUT_CLOSURE_MANIFEST = RESULTS / "manifest_author_input_closure_audit.json"
AUTHOR_QUESTIONNAIRE_COVERAGE_ANALYSIS = RESULTS / "analysis_author_questionnaire_coverage.md"
AUTHOR_QUESTIONNAIRE_COVERAGE_SUMMARY = RESULTS / "summary_author_questionnaire_coverage.csv"
AUTHOR_QUESTIONNAIRE_COVERAGE_MANIFEST = RESULTS / "manifest_author_questionnaire_coverage.json"
METADATA_ANSWER_TEMPLATE_ANALYSIS = RESULTS / "analysis_metadata_answer_template_coverage.md"
METADATA_ANSWER_TEMPLATE_SUMMARY = RESULTS / "summary_metadata_answer_template_coverage.csv"
METADATA_ANSWER_TEMPLATE_MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"
METADATA_CLOSURE_ANALYSIS = RESULTS / "analysis_submission_metadata_closure_path.md"
METADATA_CLOSURE_SUMMARY = RESULTS / "summary_submission_metadata_closure_path.csv"
METADATA_CLOSURE_MANIFEST = RESULTS / "manifest_submission_metadata_closure_path.json"
PAYLOAD_ROUNDTRIP_ANALYSIS = RESULTS / "analysis_payload_roundtrip_audit.md"
PAYLOAD_ROUNDTRIP_SUMMARY = RESULTS / "summary_payload_roundtrip_audit.csv"
PAYLOAD_ROUNDTRIP_MANIFEST = RESULTS / "manifest_payload_roundtrip_audit.json"
PAYLOAD_GIT_POLICY_ANALYSIS = RESULTS / "analysis_payload_git_policy_audit.md"
PAYLOAD_GIT_POLICY_SUMMARY = RESULTS / "summary_payload_git_policy_audit.csv"
PAYLOAD_GIT_POLICY_MANIFEST = RESULTS / "manifest_payload_git_policy_audit.json"
PAYLOAD_EXTRACTION_SMOKE_ANALYSIS = RESULTS / "analysis_payload_extraction_smoke_audit.md"
PAYLOAD_EXTRACTION_SMOKE_SUMMARY = RESULTS / "summary_payload_extraction_smoke_audit.csv"
PAYLOAD_EXTRACTION_SMOKE_MANIFEST = RESULTS / "manifest_payload_extraction_smoke_audit.json"
PAYLOAD_LATEX_COMPILE_ANALYSIS = RESULTS / "analysis_payload_latex_compile_audit.md"
PAYLOAD_LATEX_COMPILE_SUMMARY = RESULTS / "summary_payload_latex_compile_audit.csv"
PAYLOAD_LATEX_COMPILE_MANIFEST = RESULTS / "manifest_payload_latex_compile_audit.json"
PAYLOAD_VERIFIER_SMOKE_ANALYSIS = RESULTS / "analysis_payload_verifier_smoke_audit.md"
PAYLOAD_VERIFIER_SMOKE_SUMMARY = RESULTS / "summary_payload_verifier_smoke_audit.csv"
PAYLOAD_VERIFIER_SMOKE_MANIFEST = RESULTS / "manifest_payload_verifier_smoke_audit.json"
GOAL_ANALYSIS = RESULTS / "analysis_goal_completion_audit.md"
GOAL_SUMMARY = RESULTS / "summary_goal_completion_audit.csv"
GOAL_MANIFEST = RESULTS / "manifest_goal_completion_audit.json"
CLAIM_SCOPE_ANALYSIS = RESULTS / "analysis_claim_scope_lint.md"
CLAIM_SCOPE_SUMMARY = RESULTS / "summary_claim_scope_lint.csv"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL_ANALYSIS = RESULTS / "analysis_comparison_protocol_audit.md"
COMPARISON_PROTOCOL_SUMMARY = RESULTS / "summary_comparison_protocol_audit.csv"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"
COMPARISON_PROTOCOL_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_protocol_audit.tex"
COMPARISON_TARGET_VALIDITY_ANALYSIS = RESULTS / "analysis_comparison_target_validity_audit.md"
COMPARISON_TARGET_VALIDITY_SUMMARY = RESULTS / "summary_comparison_target_validity_audit.csv"
COMPARISON_TARGET_VALIDITY_MANIFEST = RESULTS / "manifest_comparison_target_validity_audit.json"
COMPARISON_TARGET_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_target_validity_audit.tex"
COMPARISON_ANSWER_ANALYSIS = RESULTS / "analysis_comparison_answer_scorecard.md"
COMPARISON_ANSWER_SUMMARY = RESULTS / "summary_comparison_answer_scorecard.csv"
COMPARISON_ANSWER_MANIFEST = RESULTS / "manifest_comparison_answer_scorecard.json"
COMPARISON_ANSWER_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_answer_scorecard.tex"
RESOURCE_WEIGHT_SENSITIVITY_ANALYSIS = RESULTS / "analysis_resource_weight_sensitivity_audit.md"
RESOURCE_WEIGHT_SENSITIVITY_SUMMARY = RESULTS / "summary_resource_weight_sensitivity_audit.csv"
RESOURCE_WEIGHT_SENSITIVITY_RAW = RESULTS / "raw_resource_weight_sensitivity_audit.csv"
RESOURCE_WEIGHT_SENSITIVITY_MANIFEST = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
RESOURCE_WEIGHT_SENSITIVITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "resource_weight_sensitivity_audit.tex"
CNOT_CONSTRAINT_PROFILE_ANALYSIS = RESULTS / "analysis_cnot_constraint_profile_audit.md"
CNOT_CONSTRAINT_PROFILE_SUMMARY = RESULTS / "summary_cnot_constraint_profile_audit.csv"
CNOT_CONSTRAINT_PROFILE_RAW = RESULTS / "raw_resource_sweep.csv"
CNOT_CONSTRAINT_PROFILE_MANIFEST = RESULTS / "manifest_cnot_constraint_profile_audit.json"
CNOT_CONSTRAINT_PROFILE_TABLE = THIS_DIR / "paper_latex" / "tables" / "cnot_constraint_profile_audit.tex"
SSHR_REPRODUCTION_ANALYSIS = RESULTS / "analysis_sshr_reproduction_scope_audit.md"
SSHR_REPRODUCTION_SUMMARY = RESULTS / "summary_sshr_reproduction_scope_audit.csv"
SSHR_REPRODUCTION_MANIFEST = RESULTS / "manifest_sshr_reproduction_scope_audit.json"
SSHR_REPRODUCTION_TABLE = THIS_DIR / "paper_latex" / "tables" / "sshr_reproduction_scope_audit.tex"
THREATS_VALIDITY_ANALYSIS = RESULTS / "analysis_threats_to_validity_audit.md"
THREATS_VALIDITY_SUMMARY = RESULTS / "summary_threats_to_validity_audit.csv"
THREATS_VALIDITY_MANIFEST = RESULTS / "manifest_threats_to_validity_audit.json"
THREATS_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "threats_to_validity_audit.tex"
NOVELTY_SCORECARD_ANALYSIS = RESULTS / "analysis_novelty_comparison_scorecard.md"
NOVELTY_SCORECARD_SUMMARY = RESULTS / "summary_novelty_comparison_scorecard.csv"
NOVELTY_SCORECARD_MANIFEST = RESULTS / "manifest_novelty_comparison_scorecard.json"
NOVELTY_SCORECARD_TABLE = THIS_DIR / "paper_latex" / "tables" / "novelty_comparison_scorecard.tex"
ALGORITHM_CONTRACT_ANALYSIS = RESULTS / "analysis_algorithm_contract.md"
ALGORITHM_CONTRACT_SUMMARY = RESULTS / "summary_algorithm_contract.csv"
ALGORITHM_CONTRACT_MANIFEST = RESULTS / "manifest_algorithm_contract.json"
ALGORITHM_CONTRACT_TABLE = THIS_DIR / "paper_latex" / "tables" / "algorithm_contract.tex"
SEARCH_BUDGET_ANALYSIS = RESULTS / "analysis_search_budget_contract.md"
SEARCH_BUDGET_SUMMARY = RESULTS / "summary_search_budget_contract.csv"
SEARCH_BUDGET_MANIFEST = RESULTS / "manifest_search_budget_contract.json"
SEARCH_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "search_budget_contract.tex"
ROS_GAP_ANALYSIS = RESULTS / "analysis_ros_reproduction_gap_audit.md"
ROS_GAP_SUMMARY = RESULTS / "summary_ros_reproduction_gap_audit.csv"
ROS_GAP_MANIFEST = RESULTS / "manifest_ros_reproduction_gap_audit.json"
ROS_GAP_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_reproduction_gap_audit.tex"
ROS_GARBAGE_ANALYSIS = RESULTS / "analysis_ros_lut_garbage_proxy.md"
ROS_GARBAGE_SUMMARY = RESULTS / "summary_ros_lut_garbage_proxy.csv"
ROS_GARBAGE_MANIFEST = RESULTS / "manifest_ros_lut_garbage_proxy.json"
ROS_GARBAGE_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_proxy.tex"
ROS_GARBAGE_BUDGET_ANALYSIS = RESULTS / "analysis_ros_lut_garbage_budget_frontier.md"
ROS_GARBAGE_BUDGET_SUMMARY = RESULTS / "summary_ros_lut_garbage_budget_frontier.csv"
ROS_GARBAGE_BUDGET_MANIFEST = RESULTS / "manifest_ros_lut_garbage_budget_frontier.json"
ROS_GARBAGE_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_budget_frontier.tex"
ROS_CHECKPOINT_ANALYSIS = RESULTS / "analysis_ros_lut_checkpoint_optimizer.md"
ROS_CHECKPOINT_SUMMARY = RESULTS / "summary_ros_lut_checkpoint_optimizer.csv"
ROS_CHECKPOINT_MANIFEST = RESULTS / "manifest_ros_lut_checkpoint_optimizer.json"
ROS_CHECKPOINT_RAW = RESULTS / "raw_ros_lut_checkpoint_optimizer.csv"
ROS_CHECKPOINT_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_checkpoint_optimizer.tex"
STG_BENCHMARK_ANALYSIS = RESULTS / "analysis_stg_published_benchmark.md"
STG_BENCHMARK_SUMMARY = RESULTS / "summary_stg_published_benchmark.csv"
STG_BENCHMARK_MANIFEST = RESULTS / "manifest_stg_published_benchmark.json"
STG_BENCHMARK_TABLE = THIS_DIR / "paper_latex" / "tables" / "stg_published_benchmark.tex"
SCHEDULE_PROXY_ANALYSIS = RESULTS / "analysis_schedule_proxy_audit.md"
SCHEDULE_PROXY_SUMMARY = RESULTS / "summary_schedule_proxy_audit.csv"
SCHEDULE_PROXY_MANIFEST = RESULTS / "manifest_schedule_proxy_audit.json"
SCHEDULE_PROXY_TABLE = THIS_DIR / "paper_latex" / "tables" / "schedule_proxy_audit.tex"
RUNTIME_ENVELOPE_ANALYSIS = RESULTS / "analysis_runtime_envelope_audit.md"
RUNTIME_ENVELOPE_SUMMARY = RESULTS / "summary_runtime_envelope_audit.csv"
RUNTIME_ENVELOPE_MANIFEST = RESULTS / "manifest_runtime_envelope_audit.json"
RUNTIME_ENVELOPE_TABLE = THIS_DIR / "paper_latex" / "tables" / "runtime_envelope_audit.tex"
ULTRA_SCALE64_ANALYSIS = RESULTS / "analysis_screen_scale_ultra_scale64_stress.md"
ULTRA_SCALE64_SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_stress.csv"
ULTRA_SCALE64_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_stress.json"
ULTRA_SCALE64_TABLE = THIS_DIR / "paper_latex" / "tables" / "screen_scale_ultra_scale64_stress.tex"
ULTRA_SCALE64_PROFILE_ANALYSIS = RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md"
ULTRA_SCALE64_PROFILE_SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_resource_profile.csv"
ULTRA_SCALE64_PROFILE_DELTA_SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_resource_deltas.csv"
ULTRA_SCALE64_PROFILE_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json"
ULTRA_SCALE64_PROFILE_TABLE = THIS_DIR / "paper_latex" / "tables" / "screen_scale_ultra_scale64_resource_profile.tex"
CITATION_SUPPORT_ANALYSIS = RESULTS / "analysis_citation_support_audit.md"
CITATION_SUPPORT_SUMMARY = RESULTS / "summary_citation_support_audit.csv"
CITATION_SUPPORT_MANIFEST = RESULTS / "manifest_citation_support_audit.json"
RERUN_REGISTRY_ANALYSIS = RESULTS / "analysis_artifact_rerun_registry.md"
RERUN_REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
RERUN_REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
RERUN_REGISTRY_TABLE = THIS_DIR / "paper_latex" / "tables" / "artifact_rerun_registry.tex"
FIGURE_ASSET_ANALYSIS = RESULTS / "analysis_figure_asset_audit.md"
FIGURE_ASSET_SUMMARY = RESULTS / "summary_figure_asset_audit.csv"
FIGURE_ASSET_MANIFEST = RESULTS / "manifest_figure_asset_audit.json"
HEADLINE_NUMERIC_ANALYSIS = RESULTS / "analysis_headline_numeric_consistency.md"
HEADLINE_NUMERIC_SUMMARY = RESULTS / "summary_headline_numeric_consistency.csv"
HEADLINE_NUMERIC_MANIFEST = RESULTS / "manifest_headline_numeric_consistency.json"
LATEX_DEPENDENCY_ANALYSIS = RESULTS / "analysis_latex_dependency_audit.md"
LATEX_DEPENDENCY_SUMMARY = RESULTS / "summary_latex_dependency_audit.csv"
LATEX_DEPENDENCY_MANIFEST = RESULTS / "manifest_latex_dependency_audit.json"
PDF_VISUAL_ANALYSIS = RESULTS / "analysis_pdf_visual_audit.md"
PDF_VISUAL_SUMMARY = RESULTS / "summary_pdf_visual_audit.csv"
PDF_VISUAL_MANIFEST = RESULTS / "manifest_pdf_visual_audit.json"
PDF_TEXT_ANALYSIS = RESULTS / "analysis_pdf_text_audit.md"
PDF_TEXT_SUMMARY = RESULTS / "summary_pdf_text_audit.csv"
PDF_TEXT_MANIFEST = RESULTS / "manifest_pdf_text_audit.json"
PDF_METADATA_ANALYSIS = RESULTS / "analysis_pdf_metadata_audit.md"
PDF_METADATA_SUMMARY = RESULTS / "summary_pdf_metadata_audit.csv"
PDF_METADATA_MANIFEST = RESULTS / "manifest_pdf_metadata_audit.json"
SOURCE_PATH_PRIVACY_ANALYSIS = RESULTS / "analysis_source_path_privacy_audit.md"
SOURCE_PATH_PRIVACY_SUMMARY = RESULTS / "summary_source_path_privacy_audit.csv"
SOURCE_PATH_PRIVACY_MANIFEST = RESULTS / "manifest_source_path_privacy_audit.json"
PAIRED_EFFECT_ANALYSIS = RESULTS / "analysis_paired_effect_uncertainty.md"
PAIRED_EFFECT_SUMMARY = RESULTS / "summary_paired_effect_uncertainty.csv"
PAIRED_EFFECT_MANIFEST = RESULTS / "manifest_paired_effect_uncertainty.json"
PAIRED_EFFECT_TABLE = THIS_DIR / "paper_latex" / "tables" / "paired_effect_uncertainty.tex"
SEARCH_CONTROL_ANALYSIS = RESULTS / "analysis_search_control_baseline_audit.md"
SEARCH_CONTROL_SUMMARY = RESULTS / "summary_search_control_baseline_audit.csv"
SEARCH_CONTROL_MANIFEST = RESULTS / "manifest_search_control_baseline_audit.json"
SEARCH_CONTROL_TABLE = THIS_DIR / "paper_latex" / "tables" / "search_control_baseline_audit.tex"
LEARNED_CONTROL_ANALYSIS = RESULTS / "analysis_learned_control_audit.md"
LEARNED_CONTROL_SUMMARY = RESULTS / "summary_learned_control_audit.csv"
LEARNED_CONTROL_MANIFEST = RESULTS / "manifest_learned_control_audit.json"
LEARNED_CONTROL_TABLE = THIS_DIR / "paper_latex" / "tables" / "learned_control_audit.tex"
ROOT_ACTION_RANKER_ANALYSIS = RESULTS / "analysis_root_action_ranker_audit.md"
ROOT_ACTION_RANKER_SUMMARY = RESULTS / "summary_root_action_ranker_audit.csv"
ROOT_ACTION_RANKER_MANIFEST = RESULTS / "manifest_root_action_ranker_audit.json"
ROOT_ACTION_RANKER_TABLE = THIS_DIR / "paper_latex" / "tables" / "root_action_ranker_audit.tex"
NEURAL_MCTS_CLAIM_ANALYSIS = RESULTS / "analysis_neural_mcts_claim_calibration.md"
NEURAL_MCTS_CLAIM_SUMMARY = RESULTS / "summary_neural_mcts_claim_calibration.csv"
NEURAL_MCTS_CLAIM_MANIFEST = RESULTS / "manifest_neural_mcts_claim_calibration.json"
NEURAL_MCTS_CLAIM_TABLE = THIS_DIR / "paper_latex" / "tables" / "neural_mcts_claim_calibration.tex"
BITFLIP_RANDOM_PRIOR_ANALYSIS = RESULTS / "analysis_bitflip_random_prior_control.md"
BITFLIP_RANDOM_PRIOR_SUMMARY = RESULTS / "summary_bitflip_random_prior_control.csv"
BITFLIP_RANDOM_PRIOR_MANIFEST = RESULTS / "manifest_bitflip_random_prior_control.json"
BITFLIP_RANDOM_PRIOR_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_random_prior_control.tex"
BITFLIP_BUDGET_ANALYSIS = RESULTS / "analysis_bitflip_neural_budget_sweep.md"
BITFLIP_BUDGET_SUMMARY = RESULTS / "summary_bitflip_neural_budget_sweep.csv"
BITFLIP_BUDGET_MANIFEST = RESULTS / "manifest_bitflip_neural_budget_sweep.json"
BITFLIP_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_neural_budget_sweep.tex"
FRONTIER_RANDOM_DEPTH_ANALYSIS = RESULTS / "analysis_frontier_random_depth_control.md"
FRONTIER_RANDOM_DEPTH_SUMMARY = RESULTS / "summary_frontier_random_depth_control.csv"
FRONTIER_RANDOM_DEPTH_MANIFEST = RESULTS / "manifest_frontier_random_depth_control.json"
FRONTIER_RANDOM_DEPTH_TABLE = THIS_DIR / "paper_latex" / "tables" / "frontier_random_depth_control.tex"
STOCHASTIC_CONTROL_ANALYSIS = RESULTS / "analysis_stochastic_control_stability.md"
STOCHASTIC_CONTROL_SUMMARY = RESULTS / "summary_stochastic_control_stability.csv"
STOCHASTIC_CONTROL_MANIFEST = RESULTS / "manifest_stochastic_control_stability.json"
STOCHASTIC_CONTROL_TABLE = THIS_DIR / "paper_latex" / "tables" / "stochastic_control_stability.tex"
EDITORIAL_SCREENING_ANALYSIS = RESULTS / "analysis_editorial_screening_audit.md"
EDITORIAL_SCREENING_SUMMARY = RESULTS / "summary_editorial_screening_audit.csv"
EDITORIAL_SCREENING_MANIFEST = RESULTS / "manifest_editorial_screening_audit.json"
EDITORIAL_SCREENING_TABLE = THIS_DIR / "paper_latex" / "tables" / "editorial_screening_audit.tex"
TARGET_VENUE_DECISION_ANALYSIS = RESULTS / "analysis_target_venue_decision_audit.md"
TARGET_VENUE_DECISION_SUMMARY = RESULTS / "summary_target_venue_decision_audit.csv"
TARGET_VENUE_DECISION_MANIFEST = RESULTS / "manifest_target_venue_decision_audit.json"
TARGET_VENUE_DECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "target_venue_decision_audit.tex"
TARGET_VENUE_POLICY_ANALYSIS = RESULTS / "analysis_target_venue_policy_checklist.md"
TARGET_VENUE_POLICY_SUMMARY = RESULTS / "summary_target_venue_policy_checklist.csv"
TARGET_VENUE_POLICY_MANIFEST = RESULTS / "manifest_target_venue_policy_checklist.json"
TARGET_VENUE_POLICY_CHECKLIST = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
TARGET_VENUE_FORMAT_ANALYSIS = RESULTS / "analysis_target_venue_format_smoke.md"
TARGET_VENUE_FORMAT_SUMMARY = RESULTS / "summary_target_venue_format_smoke.csv"
TARGET_VENUE_FORMAT_MANIFEST = RESULTS / "manifest_target_venue_format_smoke.json"
TARGET_VENUE_FORMAT_SOURCE = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"
TARGET_VENUE_FORMAT_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.pdf"
SUPPORT_PACKET_ANALYSIS = RESULTS / "analysis_submission_support_packet_audit.md"
SUPPORT_PACKET_SUMMARY = RESULTS / "summary_submission_support_packet_audit.csv"
SUPPORT_PACKET_MANIFEST = RESULTS / "manifest_submission_support_packet_audit.json"
SUPPORT_PACKET_TABLE = THIS_DIR / "paper_latex" / "tables" / "submission_support_packet_audit.tex"
SUPPORT_FILES = [
    SUBMISSION_PACKAGE / "README.md",
    AUTHOR_INPUT_PACKET,
    SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md",
    SUBMISSION_PACKAGE / "artifact_reproduction_guide.md",
    SUBMISSION_PACKAGE / "cover_letter_template.md",
    SUBMISSION_PACKAGE / "author_declarations_template.md",
    SUBMISSION_PACKAGE / "submission_checklist.md",
    SUBMISSION_PACKAGE / "reviewer_concern_brief.md",
    SUBMISSION_PACKAGE / "editor_screening_brief.md",
    SUBMISSION_PACKAGE / "target_venue_brief.md",
    TARGET_VENUE_POLICY_CHECKLIST,
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pdf_pages(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        proc = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return "unknown"
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return match.group(1) if match else "unknown"


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def abstract_word_count(text: str) -> int:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, flags=re.DOTALL)
    if not match:
        return 0
    abstract = match.group(1)
    abstract = re.sub(r"\\[a-zA-Z]+(?:\{[^{}]*\})?", " ", abstract)
    abstract = re.sub(r"[^A-Za-z0-9.%/-]+", " ", abstract)
    return len([word for word in abstract.split() if word])


def build_rows() -> list[dict[str, str]]:
    text = read_text(PAPER)
    pages = pdf_pages(PDF)
    claim_scope_manifest = read_json(CLAIM_SCOPE_MANIFEST)
    claim_scope_unresolved = int(claim_scope_manifest.get("unresolved_count", -1)) if claim_scope_manifest else -1
    comparison_protocol_manifest = read_json(COMPARISON_PROTOCOL_MANIFEST)
    comparison_protocol_revisions = (
        int(comparison_protocol_manifest.get("needs_revision_count", -1)) if comparison_protocol_manifest else -1
    )
    comparison_protocol_counts = comparison_protocol_manifest.get("status_counts", {}) if comparison_protocol_manifest else {}
    comparison_target_validity_manifest = read_json(COMPARISON_TARGET_VALIDITY_MANIFEST)
    comparison_target_validity_revisions = (
        int(comparison_target_validity_manifest.get("needs_revision_count", -1))
        if comparison_target_validity_manifest
        else -1
    )
    comparison_target_validity_counts = (
        comparison_target_validity_manifest.get("status_counts", {}) if comparison_target_validity_manifest else {}
    )
    comparison_target_validity_rows = (
        comparison_target_validity_manifest.get("rows", "missing") if comparison_target_validity_manifest else "missing"
    )
    comparison_target_validity_roles = (
        comparison_target_validity_manifest.get("roles", []) if comparison_target_validity_manifest else []
    )
    comparison_target_validity_anchor = (
        bool(comparison_target_validity_manifest.get("table_anchor_present", False))
        if comparison_target_validity_manifest
        else False
    )
    comparison_answer_manifest = read_json(COMPARISON_ANSWER_MANIFEST)
    comparison_answer_revisions = (
        int(comparison_answer_manifest.get("needs_revision_count", -1)) if comparison_answer_manifest else -1
    )
    comparison_answer_counts = comparison_answer_manifest.get("status_counts", {}) if comparison_answer_manifest else {}
    comparison_answer_rows = comparison_answer_manifest.get("rows", "missing") if comparison_answer_manifest else "missing"
    comparison_answer_questions = (
        comparison_answer_manifest.get("questions", []) if comparison_answer_manifest else []
    )
    comparison_answer_anchor = (
        bool(comparison_answer_manifest.get("table_anchor_present", False)) if comparison_answer_manifest else False
    )
    resource_weight_manifest = read_json(RESOURCE_WEIGHT_SENSITIVITY_MANIFEST)
    resource_weight_revisions = (
        int(resource_weight_manifest.get("needs_revision_count", -1)) if resource_weight_manifest else -1
    )
    resource_weight_counts = resource_weight_manifest.get("status_counts", {}) if resource_weight_manifest else {}
    resource_weight_raw_rows = resource_weight_manifest.get("raw_rows", "missing") if resource_weight_manifest else "missing"
    resource_weight_summary_rows = (
        resource_weight_manifest.get("summary_rows", "missing") if resource_weight_manifest else "missing"
    )
    resource_weight_comparisons = resource_weight_manifest.get("comparisons", []) if resource_weight_manifest else []
    resource_weight_profiles = resource_weight_manifest.get("profiles", []) if resource_weight_manifest else []
    resource_weight_anchor = (
        bool(resource_weight_manifest.get("table_anchor_present", False)) if resource_weight_manifest else False
    )
    cnot_constraint_manifest = read_json(CNOT_CONSTRAINT_PROFILE_MANIFEST)
    cnot_constraint_revisions = (
        int(cnot_constraint_manifest.get("needs_revision_count", -1)) if cnot_constraint_manifest else -1
    )
    cnot_constraint_counts = cnot_constraint_manifest.get("status_counts", {}) if cnot_constraint_manifest else {}
    cnot_constraint_raw_rows = cnot_constraint_manifest.get("raw_rows", "missing") if cnot_constraint_manifest else "missing"
    cnot_constraint_summary_rows = (
        cnot_constraint_manifest.get("summary_rows", "missing") if cnot_constraint_manifest else "missing"
    )
    cnot_constraint_profiles = cnot_constraint_manifest.get("profiles", []) if cnot_constraint_manifest else []
    cnot_constraint_functions = (
        cnot_constraint_manifest.get("functions_cnot_only", "missing") if cnot_constraint_manifest else "missing"
    )
    cnot_constraint_anchor = (
        bool(cnot_constraint_manifest.get("table_anchor_present", False)) if cnot_constraint_manifest else False
    )
    cnot_constraint_anonymous_anchor = (
        bool(cnot_constraint_manifest.get("anonymous_table_anchor_present", False)) if cnot_constraint_manifest else False
    )
    cnot_constraint_acm_anchor = (
        bool(cnot_constraint_manifest.get("acm_table_anchor_present", False)) if cnot_constraint_manifest else False
    )
    sshr_reproduction_manifest = read_json(SSHR_REPRODUCTION_MANIFEST)
    sshr_reproduction_revisions = (
        int(sshr_reproduction_manifest.get("needs_revision_count", -1)) if sshr_reproduction_manifest else -1
    )
    sshr_reproduction_counts = (
        sshr_reproduction_manifest.get("status_counts", {}) if sshr_reproduction_manifest else {}
    )
    sshr_reproduction_coverage = (
        sshr_reproduction_manifest.get("coverage_counts", {}) if sshr_reproduction_manifest else {}
    )
    sshr_reproduction_rows = sshr_reproduction_manifest.get("rows", "missing") if sshr_reproduction_manifest else "missing"
    sshr_source_tree_available = (
        sshr_reproduction_manifest.get("source_tree_available", "missing") if sshr_reproduction_manifest else "missing"
    )
    sshr_reproduction_anchor = (
        bool(sshr_reproduction_manifest.get("table_anchor_present", False)) if sshr_reproduction_manifest else False
    )
    sshr_reproduction_anonymous_anchor = (
        bool(sshr_reproduction_manifest.get("anonymous_table_anchor_present", False))
        if sshr_reproduction_manifest
        else False
    )
    sshr_reproduction_acm_anchor = (
        bool(sshr_reproduction_manifest.get("acm_table_anchor_present", False))
        if sshr_reproduction_manifest
        else False
    )
    threats_validity_manifest = read_json(THREATS_VALIDITY_MANIFEST)
    threats_validity_revisions = (
        int(threats_validity_manifest.get("needs_revision_count", -1)) if threats_validity_manifest else -1
    )
    threats_validity_counts = threats_validity_manifest.get("status_counts", {}) if threats_validity_manifest else {}
    threats_validity_rows = threats_validity_manifest.get("rows", "missing") if threats_validity_manifest else "missing"
    threats_validity_threats = threats_validity_manifest.get("threats", []) if threats_validity_manifest else []
    threats_validity_anchor = (
        bool(threats_validity_manifest.get("table_anchor_present", False)) if threats_validity_manifest else False
    )
    novelty_scorecard_manifest = read_json(NOVELTY_SCORECARD_MANIFEST)
    novelty_scorecard_revisions = (
        int(novelty_scorecard_manifest.get("needs_revision_count", -1)) if novelty_scorecard_manifest else -1
    )
    novelty_scorecard_counts = novelty_scorecard_manifest.get("status_counts", {}) if novelty_scorecard_manifest else {}
    novelty_scorecard_rows = novelty_scorecard_manifest.get("rows", "missing") if novelty_scorecard_manifest else "missing"
    algorithm_contract_manifest = read_json(ALGORITHM_CONTRACT_MANIFEST)
    algorithm_contract_revisions = (
        int(algorithm_contract_manifest.get("needs_revision_count", -1)) if algorithm_contract_manifest else -1
    )
    algorithm_contract_counts = algorithm_contract_manifest.get("status_counts", {}) if algorithm_contract_manifest else {}
    algorithm_contract_rows = algorithm_contract_manifest.get("rows", "missing") if algorithm_contract_manifest else "missing"
    search_budget_manifest = read_json(SEARCH_BUDGET_MANIFEST)
    search_budget_revisions = int(search_budget_manifest.get("needs_revision_count", -1)) if search_budget_manifest else -1
    search_budget_counts = search_budget_manifest.get("status_counts", {}) if search_budget_manifest else {}
    search_budget_rows = search_budget_manifest.get("rows", "missing") if search_budget_manifest else "missing"
    ros_gap_manifest = read_json(ROS_GAP_MANIFEST)
    ros_gap_counts = ros_gap_manifest.get("status_counts", {}) if ros_gap_manifest else {}
    ros_gap_coverage = ros_gap_manifest.get("coverage_counts", {}) if ros_gap_manifest else {}
    ros_gap_revisions = int(ros_gap_manifest.get("needs_revision_count", -1)) if ros_gap_manifest else -1
    ros_gap_rows = ros_gap_manifest.get("rows", "missing") if ros_gap_manifest else "missing"
    ros_gap_fully_reproduced = bool(ros_gap_manifest.get("official_ros_fully_reproduced", True)) if ros_gap_manifest else True
    ros_gap_boundary_explicit = bool(ros_gap_manifest.get("full_ros_boundary_is_explicit", False)) if ros_gap_manifest else False
    ros_garbage_manifest = read_json(ROS_GARBAGE_MANIFEST)
    ros_garbage_revisions = int(ros_garbage_manifest.get("needs_revision_count", -1)) if ros_garbage_manifest else -1
    ros_garbage_counts = ros_garbage_manifest.get("status_counts", {}) if ros_garbage_manifest else {}
    ros_garbage_raw_rows = ros_garbage_manifest.get("raw_rows", "missing") if ros_garbage_manifest else "missing"
    ros_garbage_functions = ros_garbage_manifest.get("functions", "missing") if ros_garbage_manifest else "missing"
    ros_garbage_anchor = bool(ros_garbage_manifest.get("table_anchor_present", False)) if ros_garbage_manifest else False
    ros_garbage_budget_manifest = read_json(ROS_GARBAGE_BUDGET_MANIFEST)
    ros_garbage_budget_revisions = int(ros_garbage_budget_manifest.get("needs_revision_count", -1)) if ros_garbage_budget_manifest else -1
    ros_garbage_budget_counts = ros_garbage_budget_manifest.get("status_counts", {}) if ros_garbage_budget_manifest else {}
    ros_garbage_budget_raw_rows = ros_garbage_budget_manifest.get("raw_rows", "missing") if ros_garbage_budget_manifest else "missing"
    ros_garbage_budget_summary_rows = ros_garbage_budget_manifest.get("summary_rows", "missing") if ros_garbage_budget_manifest else "missing"
    ros_garbage_budget_functions = ros_garbage_budget_manifest.get("functions", "missing") if ros_garbage_budget_manifest else "missing"
    ros_garbage_budget_frontier_rows = ros_garbage_budget_manifest.get("frontier_rows", "missing") if ros_garbage_budget_manifest else "missing"
    ros_garbage_budget_anchor = bool(ros_garbage_budget_manifest.get("table_anchor_present", False)) if ros_garbage_budget_manifest else False
    ros_checkpoint_manifest = read_json(ROS_CHECKPOINT_MANIFEST)
    ros_checkpoint_revisions = int(ros_checkpoint_manifest.get("needs_revision_count", -1)) if ros_checkpoint_manifest else -1
    ros_checkpoint_counts = ros_checkpoint_manifest.get("status_counts", {}) if ros_checkpoint_manifest else {}
    ros_checkpoint_raw_rows = ros_checkpoint_manifest.get("raw_rows", "missing") if ros_checkpoint_manifest else "missing"
    ros_checkpoint_summary_rows = ros_checkpoint_manifest.get("summary_rows", "missing") if ros_checkpoint_manifest else "missing"
    ros_checkpoint_frontier_rows = ros_checkpoint_manifest.get("frontier_rows", "missing") if ros_checkpoint_manifest else "missing"
    ros_checkpoint_solved = ros_checkpoint_manifest.get("solved_functions", "missing") if ros_checkpoint_manifest else "missing"
    ros_checkpoint_traditional = ros_checkpoint_manifest.get("solved_traditional_n_le_6", "missing") if ros_checkpoint_manifest else "missing"
    ros_checkpoint_anchor = bool(ros_checkpoint_manifest.get("table_anchor_present", False)) if ros_checkpoint_manifest else False
    ros_checkpoint_exact = bool(ros_checkpoint_manifest.get("exact_over_checkpoint_candidates", False)) if ros_checkpoint_manifest else False
    ros_checkpoint_full_ros = bool(ros_checkpoint_manifest.get("official_ros_fully_reproduced", True)) if ros_checkpoint_manifest else True
    stg_manifest = read_json(STG_BENCHMARK_MANIFEST)
    stg_revisions = int(stg_manifest.get("needs_revision_count", -1)) if stg_manifest else -1
    stg_counts = stg_manifest.get("status_counts", {}) if stg_manifest else {}
    stg_benchmark_rows = stg_manifest.get("benchmark_rows", "missing") if stg_manifest else "missing"
    stg_raw_rows = stg_manifest.get("raw_rows", "missing") if stg_manifest else "missing"
    stg_usable_rows = stg_manifest.get("usable_rows", "missing") if stg_manifest else "missing"
    schedule_proxy_manifest = read_json(SCHEDULE_PROXY_MANIFEST)
    schedule_proxy_revisions = int(schedule_proxy_manifest.get("needs_revision_count", -1)) if schedule_proxy_manifest else -1
    schedule_proxy_counts = schedule_proxy_manifest.get("status_counts", {}) if schedule_proxy_manifest else {}
    schedule_proxy_rows = schedule_proxy_manifest.get("rows", "missing") if schedule_proxy_manifest else "missing"
    runtime_envelope_manifest = read_json(RUNTIME_ENVELOPE_MANIFEST)
    runtime_envelope_revisions = (
        int(runtime_envelope_manifest.get("needs_revision_count", -1)) if runtime_envelope_manifest else -1
    )
    runtime_envelope_counts = runtime_envelope_manifest.get("status_counts", {}) if runtime_envelope_manifest else {}
    runtime_envelope_rows = runtime_envelope_manifest.get("rows", "missing") if runtime_envelope_manifest else "missing"
    runtime_envelope_anchor = (
        bool(runtime_envelope_manifest.get("table_anchor_present", False)) if runtime_envelope_manifest else False
    )
    runtime_envelope_anonymous_anchor = (
        bool(runtime_envelope_manifest.get("anonymous_table_anchor_present", False))
        if runtime_envelope_manifest
        else False
    )
    runtime_envelope_acm_anchor = (
        bool(runtime_envelope_manifest.get("acm_table_anchor_present", False)) if runtime_envelope_manifest else False
    )
    ultra_scale64_manifest = read_json(ULTRA_SCALE64_MANIFEST)
    ultra_scale64_revisions = (
        int(ultra_scale64_manifest.get("needs_revision_count", -1)) if ultra_scale64_manifest else -1
    )
    ultra_scale64_counts = ultra_scale64_manifest.get("status_counts", {}) if ultra_scale64_manifest else {}
    ultra_scale64_rows = ultra_scale64_manifest.get("raw_rows", "missing") if ultra_scale64_manifest else "missing"
    ultra_scale64_plan = ultra_scale64_manifest.get("plan_verified_rows", "missing") if ultra_scale64_manifest else "missing"
    ultra_scale64_circuit = (
        ultra_scale64_manifest.get("circuit_verified_rows", "missing") if ultra_scale64_manifest else "missing"
    )
    ultra_scale64_mismatch = (
        ultra_scale64_manifest.get("max_circuit_mismatches", "missing") if ultra_scale64_manifest else "missing"
    )
    ultra_scale64_profile_manifest = read_json(ULTRA_SCALE64_PROFILE_MANIFEST)
    ultra_scale64_profile_revisions = (
        int(ultra_scale64_profile_manifest.get("needs_revision_count", -1))
        if ultra_scale64_profile_manifest
        else -1
    )
    ultra_scale64_profile_counts = (
        ultra_scale64_profile_manifest.get("status_counts", {}) if ultra_scale64_profile_manifest else {}
    )
    ultra_scale64_profile_rows = (
        ultra_scale64_profile_manifest.get("profile_rows", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_delta_rows = (
        ultra_scale64_profile_manifest.get("delta_rows", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_profile_raw_rows = (
        ultra_scale64_profile_manifest.get("raw_rows", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_profile_plan = (
        ultra_scale64_profile_manifest.get("plan_verified_rows", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_profile_circuit = (
        ultra_scale64_profile_manifest.get("circuit_verified_rows", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_profile_plan_mismatch = (
        ultra_scale64_profile_manifest.get("max_plan_mismatches", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    ultra_scale64_profile_circuit_mismatch = (
        ultra_scale64_profile_manifest.get("max_circuit_mismatches", "missing")
        if ultra_scale64_profile_manifest
        else "missing"
    )
    citation_support_manifest = read_json(CITATION_SUPPORT_MANIFEST)
    citation_support_revisions = (
        int(citation_support_manifest.get("needs_revision_count", -1)) if citation_support_manifest else -1
    )
    citation_support_counts = citation_support_manifest.get("status_counts", {}) if citation_support_manifest else {}
    citation_support_rows = citation_support_manifest.get("rows", "missing") if citation_support_manifest else "missing"
    citation_support_keys = citation_support_manifest.get("cited_key_count", "missing") if citation_support_manifest else "missing"
    search_control_manifest = read_json(SEARCH_CONTROL_MANIFEST)
    search_control_revisions = (
        int(search_control_manifest.get("needs_revision_count", -1)) if search_control_manifest else -1
    )
    search_control_counts = search_control_manifest.get("status_counts", {}) if search_control_manifest else {}
    search_control_rows = search_control_manifest.get("rows", "missing") if search_control_manifest else "missing"
    learned_control_manifest = read_json(LEARNED_CONTROL_MANIFEST)
    learned_control_revisions = (
        int(learned_control_manifest.get("needs_revision_count", -1)) if learned_control_manifest else -1
    )
    learned_control_counts = learned_control_manifest.get("status_counts", {}) if learned_control_manifest else {}
    learned_control_class_counts = (
        learned_control_manifest.get("claim_class_counts", {}) if learned_control_manifest else {}
    )
    learned_control_rows = learned_control_manifest.get("rows", "missing") if learned_control_manifest else "missing"
    learned_control_promoted = (
        learned_control_manifest.get("promoted_count", "missing") if learned_control_manifest else "missing"
    )
    learned_control_bounded = (
        learned_control_manifest.get("bounded_count", "missing") if learned_control_manifest else "missing"
    )
    learned_control_limited = (
        learned_control_manifest.get("limited_count", "missing") if learned_control_manifest else "missing"
    )
    root_action_manifest = read_json(ROOT_ACTION_RANKER_MANIFEST)
    root_action_revisions = int(root_action_manifest.get("needs_revision_count", -1)) if root_action_manifest else -1
    root_action_counts = root_action_manifest.get("status_counts", {}) if root_action_manifest else {}
    root_action_rows = root_action_manifest.get("rows", "missing") if root_action_manifest else "missing"
    root_action_pairs = root_action_manifest.get("combined_pairs", "missing") if root_action_manifest else "missing"
    root_action_wlt = root_action_manifest.get("combined_score_wlt", "missing") if root_action_manifest else "missing"
    neural_mcts_claim_manifest = read_json(NEURAL_MCTS_CLAIM_MANIFEST)
    neural_mcts_claim_revisions = (
        int(neural_mcts_claim_manifest.get("needs_revision_count", -1)) if neural_mcts_claim_manifest else -1
    )
    neural_mcts_claim_counts = neural_mcts_claim_manifest.get("status_counts", {}) if neural_mcts_claim_manifest else {}
    neural_mcts_claim_rows = neural_mcts_claim_manifest.get("rows", "missing") if neural_mcts_claim_manifest else "missing"
    neural_mcts_claim_anchors = (
        neural_mcts_claim_manifest.get("claim_anchors", []) if neural_mcts_claim_manifest else []
    )
    neural_mcts_claim_anchor_present = (
        bool(neural_mcts_claim_manifest.get("table_anchor_present", False)) if neural_mcts_claim_manifest else False
    )
    bitflip_random_manifest = read_json(BITFLIP_RANDOM_PRIOR_MANIFEST)
    bitflip_random_revisions = (
        int(bitflip_random_manifest.get("needs_revision_count", -1)) if bitflip_random_manifest else -1
    )
    bitflip_random_counts = bitflip_random_manifest.get("status_counts", {}) if bitflip_random_manifest else {}
    bitflip_random_rows = bitflip_random_manifest.get("rows", "missing") if bitflip_random_manifest else "missing"
    bitflip_budget_manifest = read_json(BITFLIP_BUDGET_MANIFEST)
    bitflip_budget_revisions = int(bitflip_budget_manifest.get("needs_revision_count", -1)) if bitflip_budget_manifest else -1
    bitflip_budget_counts = bitflip_budget_manifest.get("status_counts", {}) if bitflip_budget_manifest else {}
    bitflip_budget_raw_rows = bitflip_budget_manifest.get("raw_rows", "missing") if bitflip_budget_manifest else "missing"
    bitflip_budget_paired_rows = bitflip_budget_manifest.get("paired_rows", "missing") if bitflip_budget_manifest else "missing"
    bitflip_budget_low_rows = (
        bitflip_budget_manifest.get("low_budget_score_rows", "missing") if bitflip_budget_manifest else "missing"
    )
    bitflip_budget_positive_rows = (
        bitflip_budget_manifest.get("positive_low_budget_score_rows", "missing")
        if bitflip_budget_manifest
        else "missing"
    )
    bitflip_budget_anchor = (
        bool(bitflip_budget_manifest.get("table_anchor_present", False)) if bitflip_budget_manifest else False
    )
    frontier_random_manifest = read_json(FRONTIER_RANDOM_DEPTH_MANIFEST)
    frontier_random_revisions = (
        int(frontier_random_manifest.get("needs_revision_count", -1)) if frontier_random_manifest else -1
    )
    frontier_random_counts = frontier_random_manifest.get("status_counts", {}) if frontier_random_manifest else {}
    frontier_random_rows = frontier_random_manifest.get("rows", "missing") if frontier_random_manifest else "missing"
    stochastic_manifest = read_json(STOCHASTIC_CONTROL_MANIFEST)
    stochastic_revisions = int(stochastic_manifest.get("needs_revision_count", -1)) if stochastic_manifest else -1
    stochastic_counts = stochastic_manifest.get("status_counts", {}) if stochastic_manifest else {}
    stochastic_rows = stochastic_manifest.get("rows", "missing") if stochastic_manifest else "missing"
    stochastic_components = stochastic_manifest.get("components", []) if stochastic_manifest else []
    figure_asset_manifest = read_json(FIGURE_ASSET_MANIFEST)
    figure_asset_revisions = int(figure_asset_manifest.get("needs_revision_count", -1)) if figure_asset_manifest else -1
    figure_asset_counts = figure_asset_manifest.get("status_counts", {}) if figure_asset_manifest else {}
    figure_count = figure_asset_manifest.get("figures", "missing") if figure_asset_manifest else "missing"
    headline_numeric_manifest = read_json(HEADLINE_NUMERIC_MANIFEST)
    headline_numeric_revisions = (
        int(headline_numeric_manifest.get("needs_revision_count", -1)) if headline_numeric_manifest else -1
    )
    headline_numeric_counts = headline_numeric_manifest.get("status_counts", {}) if headline_numeric_manifest else {}
    headline_numeric_claims = headline_numeric_manifest.get("claims", "missing") if headline_numeric_manifest else "missing"
    latex_dependency_manifest = read_json(LATEX_DEPENDENCY_MANIFEST)
    latex_dependency_revisions = (
        int(latex_dependency_manifest.get("needs_revision_count", -1)) if latex_dependency_manifest else -1
    )
    latex_dependency_counts = latex_dependency_manifest.get("status_counts", {}) if latex_dependency_manifest else {}
    latex_dependency_count = latex_dependency_manifest.get("dependency_count", "missing") if latex_dependency_manifest else "missing"
    latex_dependency_types = (
        latex_dependency_manifest.get("dependency_type_counts", {}) if latex_dependency_manifest else {}
    )
    pdf_visual_manifest = read_json(PDF_VISUAL_MANIFEST)
    pdf_visual_revisions = int(pdf_visual_manifest.get("needs_revision_count", -1)) if pdf_visual_manifest else -1
    pdf_visual_counts = pdf_visual_manifest.get("status_counts", {}) if pdf_visual_manifest else {}
    pdf_visual_rows = pdf_visual_manifest.get("rows", "missing") if pdf_visual_manifest else "missing"
    pdf_text_manifest = read_json(PDF_TEXT_MANIFEST)
    pdf_text_revisions = int(pdf_text_manifest.get("needs_revision_count", -1)) if pdf_text_manifest else -1
    pdf_text_counts = pdf_text_manifest.get("status_counts", {}) if pdf_text_manifest else {}
    pdf_text_rows = pdf_text_manifest.get("rows", "missing") if pdf_text_manifest else "missing"
    pdf_text_anchor_count = pdf_text_manifest.get("required_anchor_count", "missing") if pdf_text_manifest else "missing"
    pdf_metadata_manifest = read_json(PDF_METADATA_MANIFEST)
    pdf_metadata_revisions = int(pdf_metadata_manifest.get("needs_revision_count", -1)) if pdf_metadata_manifest else -1
    pdf_metadata_counts = pdf_metadata_manifest.get("status_counts", {}) if pdf_metadata_manifest else {}
    pdf_metadata_rows = pdf_metadata_manifest.get("rows", "missing") if pdf_metadata_manifest else "missing"
    text_preview_manifest = read_json(TEXT_PREVIEW_MANIFEST)
    text_preview_counts = text_preview_manifest.get("status_counts", {}) if text_preview_manifest else {}
    private_outputs_ignored = bool(text_preview_manifest.get("private_outputs_are_git_ignored", False))
    metadata_validator_manifest = read_json(METADATA_VALIDATOR_MANIFEST)
    metadata_validator_revisions = int(metadata_validator_manifest.get("needs_revision_count", -1)) if metadata_validator_manifest else -1
    metadata_validator_counts = metadata_validator_manifest.get("status_counts", {}) if metadata_validator_manifest else {}
    metadata_selftest_manifest = read_json(METADATA_PIPELINE_SELFTEST_MANIFEST)
    metadata_selftest_revisions = int(metadata_selftest_manifest.get("needs_revision_count", -1)) if metadata_selftest_manifest else -1
    metadata_selftest_counts = metadata_selftest_manifest.get("status_counts", {}) if metadata_selftest_manifest else {}
    metadata_selftest_synthetic = bool(metadata_selftest_manifest.get("uses_synthetic_metadata_only", False))
    metadata_selftest_writes_private = bool(metadata_selftest_manifest.get("writes_private_metadata", True)) or bool(
        metadata_selftest_manifest.get("writes_private_preview_files", True)
    )
    anonymous_manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    anonymous_counts = anonymous_manifest.get("status_counts", {}) if anonymous_manifest else {}
    anonymous_revisions = int(anonymous_manifest.get("needs_revision_count", -1)) if anonymous_manifest else -1
    anonymous_author_input = int(anonymous_manifest.get("needs_author_input_count", -1)) if anonymous_manifest else -1
    author_input_closure_manifest = read_json(AUTHOR_INPUT_CLOSURE_MANIFEST)
    author_input_closure_counts = author_input_closure_manifest.get("status_counts", {}) if author_input_closure_manifest else {}
    author_input_closure_revisions = (
        int(author_input_closure_manifest.get("needs_revision_count", -1)) if author_input_closure_manifest else -1
    )
    author_input_required_paths = (
        author_input_closure_manifest.get("required_metadata_paths", "missing")
        if author_input_closure_manifest
        else "missing"
    )
    author_questionnaire_manifest = read_json(AUTHOR_QUESTIONNAIRE_COVERAGE_MANIFEST)
    author_questionnaire_counts = author_questionnaire_manifest.get("status_counts", {}) if author_questionnaire_manifest else {}
    author_questionnaire_revisions = (
        int(author_questionnaire_manifest.get("needs_revision_count", -1)) if author_questionnaire_manifest else -1
    )
    author_questionnaire_required = (
        author_questionnaire_manifest.get("required_paths", "missing") if author_questionnaire_manifest else "missing"
    )
    author_questionnaire_missing = (
        author_questionnaire_manifest.get("missing_required_paths", "missing") if author_questionnaire_manifest else "missing"
    )
    metadata_answer_manifest = read_json(METADATA_ANSWER_TEMPLATE_MANIFEST)
    metadata_answer_counts = metadata_answer_manifest.get("status_counts", {}) if metadata_answer_manifest else {}
    metadata_answer_revisions = (
        int(metadata_answer_manifest.get("needs_revision_count", -1)) if metadata_answer_manifest else -1
    )
    metadata_answer_required = (
        metadata_answer_manifest.get("required_metadata_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_template_paths = (
        metadata_answer_manifest.get("answer_template_required_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_starter_only = (
        metadata_answer_manifest.get("starter_only_required_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_missing = (
        metadata_answer_manifest.get("missing_required_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_unknown = (
        metadata_answer_manifest.get("unknown_answer_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_private_like = (
        metadata_answer_manifest.get("private_like_value_paths", "missing") if metadata_answer_manifest else "missing"
    )
    metadata_answer_remaining = (
        metadata_answer_manifest.get("remaining_author_paths_after_template_dry_run", "missing")
        if metadata_answer_manifest
        else "missing"
    )
    metadata_closure_manifest = read_json(METADATA_CLOSURE_MANIFEST)
    metadata_closure_counts = metadata_closure_manifest.get("status_counts", {}) if metadata_closure_manifest else {}
    metadata_closure_revisions = (
        int(metadata_closure_manifest.get("needs_revision_count", -1)) if metadata_closure_manifest else -1
    )
    metadata_closure_ready = (
        bool(metadata_closure_manifest.get("closure_path_ready", False)) if metadata_closure_manifest else False
    )
    metadata_closure_paths = (
        metadata_closure_manifest.get("required_metadata_paths", "missing") if metadata_closure_manifest else "missing"
    )
    editorial_screening_manifest = read_json(EDITORIAL_SCREENING_MANIFEST)
    editorial_screening_counts = (
        editorial_screening_manifest.get("status_counts", {}) if editorial_screening_manifest else {}
    )
    editorial_screening_revisions = (
        int(editorial_screening_manifest.get("needs_revision_count", -1)) if editorial_screening_manifest else -1
    )
    editorial_screening_rows = editorial_screening_manifest.get("rows", "missing") if editorial_screening_manifest else "missing"
    target_venue_manifest = read_json(TARGET_VENUE_DECISION_MANIFEST)
    target_venue_counts = target_venue_manifest.get("status_counts", {}) if target_venue_manifest else {}
    target_venue_revisions = (
        int(target_venue_manifest.get("needs_revision_count", -1)) if target_venue_manifest else -1
    )
    target_venue_rows = target_venue_manifest.get("rows", "missing") if target_venue_manifest else "missing"
    target_venue_first = (
        target_venue_manifest.get("recommended_first_choice", "missing") if target_venue_manifest else "missing"
    )
    target_venue_strong = target_venue_manifest.get("strong_fit_count", "missing") if target_venue_manifest else "missing"
    target_policy_manifest = read_json(TARGET_VENUE_POLICY_MANIFEST)
    target_policy_counts = target_policy_manifest.get("status_counts", {}) if target_policy_manifest else {}
    target_policy_revisions = (
        int(target_policy_manifest.get("needs_revision_count", -1)) if target_policy_manifest else -1
    )
    target_policy_rows = target_policy_manifest.get("rows", "missing") if target_policy_manifest else "missing"
    target_policy_venues = target_policy_manifest.get("venues", "missing") if target_policy_manifest else "missing"
    target_format_manifest = read_json(TARGET_VENUE_FORMAT_MANIFEST)
    target_format_counts = target_format_manifest.get("status_counts", {}) if target_format_manifest else {}
    target_format_revisions = (
        int(target_format_manifest.get("needs_revision_count", -1)) if target_format_manifest else -1
    )
    target_format_rows = target_format_manifest.get("rows", "missing") if target_format_manifest else "missing"
    target_format_pages = target_format_manifest.get("pdf_pages", "missing") if target_format_manifest else "missing"
    target_format_bytes = target_format_manifest.get("pdf_bytes", "missing") if target_format_manifest else "missing"
    support_packet_manifest = read_json(SUPPORT_PACKET_MANIFEST)
    support_packet_counts = support_packet_manifest.get("status_counts", {}) if support_packet_manifest else {}
    support_packet_revisions = (
        int(support_packet_manifest.get("needs_revision_count", -1)) if support_packet_manifest else -1
    )
    support_packet_rows = support_packet_manifest.get("rows", "missing") if support_packet_manifest else "missing"
    payload_roundtrip_manifest = read_json(PAYLOAD_ROUNDTRIP_MANIFEST)
    payload_roundtrip_counts = payload_roundtrip_manifest.get("status_counts", {}) if payload_roundtrip_manifest else {}
    payload_roundtrip_revisions = int(payload_roundtrip_manifest.get("needs_revision_count", -1)) if payload_roundtrip_manifest else -1
    payload_git_policy_manifest = read_json(PAYLOAD_GIT_POLICY_MANIFEST)
    payload_git_policy_counts = payload_git_policy_manifest.get("status_counts", {}) if payload_git_policy_manifest else {}
    payload_git_policy_revisions = (
        int(payload_git_policy_manifest.get("needs_revision_count", -1)) if payload_git_policy_manifest else -1
    )
    payload_git_policy_rows = payload_git_policy_manifest.get("rows", "missing") if payload_git_policy_manifest else "missing"
    source_path_privacy_manifest = read_json(SOURCE_PATH_PRIVACY_MANIFEST)
    source_path_privacy_counts = source_path_privacy_manifest.get("status_counts", {}) if source_path_privacy_manifest else {}
    source_path_privacy_revisions = (
        int(source_path_privacy_manifest.get("needs_revision_count", -1)) if source_path_privacy_manifest else -1
    )
    source_path_privacy_rows = source_path_privacy_manifest.get("rows", "missing") if source_path_privacy_manifest else "missing"
    source_path_privacy_payload_paths = (
        source_path_privacy_manifest.get("payload_local_path_files", "missing")
        if source_path_privacy_manifest
        else "missing"
    )
    payload_smoke_manifest = read_json(PAYLOAD_EXTRACTION_SMOKE_MANIFEST)
    payload_smoke_counts = payload_smoke_manifest.get("status_counts", {}) if payload_smoke_manifest else {}
    payload_smoke_revisions = int(payload_smoke_manifest.get("needs_revision_count", -1)) if payload_smoke_manifest else -1
    payload_latex_manifest = read_json(PAYLOAD_LATEX_COMPILE_MANIFEST)
    payload_latex_counts = payload_latex_manifest.get("status_counts", {}) if payload_latex_manifest else {}
    payload_latex_revisions = int(payload_latex_manifest.get("needs_revision_count", -1)) if payload_latex_manifest else -1
    payload_latex_compiled = payload_latex_manifest.get("compiled_manuscripts", "missing") if payload_latex_manifest else "missing"
    payload_verifier_manifest = read_json(PAYLOAD_VERIFIER_SMOKE_MANIFEST)
    payload_verifier_counts = payload_verifier_manifest.get("status_counts", {}) if payload_verifier_manifest else {}
    payload_verifier_revisions = (
        int(payload_verifier_manifest.get("needs_revision_count", -1)) if payload_verifier_manifest else -1
    )
    payload_verifier_returncode = (
        payload_verifier_manifest.get("verifier_returncode", "missing") if payload_verifier_manifest else "missing"
    )
    payload_verifier_rows = payload_verifier_manifest.get("verifier_rows", "missing") if payload_verifier_manifest else "missing"
    payload_verifier_source_rows = (
        payload_verifier_manifest.get("source_verifier_rows", "missing") if payload_verifier_manifest else "missing"
    )
    payload_verifier_row_delta = (
        payload_verifier_manifest.get("row_delta", "missing") if payload_verifier_manifest else "missing"
    )
    payload_verifier_expected_delta = (
        payload_verifier_manifest.get("expected_row_delta", "missing") if payload_verifier_manifest else "missing"
    )
    payload_verifier_delta_reason = (
        payload_verifier_manifest.get("row_delta_reason", "missing") if payload_verifier_manifest else "missing"
    )
    lower = text.lower()
    todo_hits = re.findall(r"\b(?:todo|tbd|placeholder)\b", lower)
    abstract_words = abstract_word_count(text)
    rebuild_cited = "rebuild_submission_package.sh" in text or r"rebuild\_submission\_package.sh" in text

    rows = [
        {
            "item": "Bounded abstract claim",
            "status": "pass"
            if contains_all(text, [r"\begin{abstract}", "logical-layer", "not a hardware-mapped"])
            else "needs revision",
            "evidence": "Abstract states logical-layer scope and excludes hardware-mapped/depth-only claims.",
            "next_action": "Keep hardware and mapping claims out of the abstract unless new evidence is added.",
        },
        {
            "item": "Abstract concision",
            "status": "pass" if 180 <= abstract_words <= 320 else "needs revision",
            "evidence": f"Abstract word count is {abstract_words}.",
            "next_action": "Keep the abstract compact; detailed per-baseline numbers belong in Results tables.",
        },
        {
            "item": "First-pages scope and assumptions",
            "status": "pass"
            if contains_all(
                text,
                [
                    "Scope and assumptions",
                    "logical-layer Boolean-oracle synthesis",
                    "hardware mapping",
                    "baseline comparability audit",
                    "universal leaderboard",
                ],
            )
            else "needs revision",
            "evidence": "Introduction states the logical-layer scope, excluded hardware assumptions, score role, and comparison boundary.",
            "next_action": "Keep the scope and assumptions visible in the first pages after venue-specific template conversion.",
        },
        {
            "item": "Contribution-to-evidence chain",
            "status": "pass" if "tab:contribution-map" in text else "needs revision",
            "evidence": "Introduction includes a contribution-to-evidence map.",
            "next_action": "Update the map whenever a headline contribution changes.",
        },
        {
            "item": "Executable method workflow",
            "status": "pass" if "tab:method-workflow" in text else "needs revision",
            "evidence": "Method includes an end-to-end synthesis and verification workflow table.",
            "next_action": "Keep the workflow table aligned with new candidate generators or verification stages.",
        },
        {
            "item": "Algorithm contract table",
            "status": "pass"
            if "tab:algorithm-contract" in text
            and ALGORITHM_CONTRACT_ANALYSIS.exists()
            and ALGORITHM_CONTRACT_SUMMARY.exists()
            and ALGORITHM_CONTRACT_MANIFEST.exists()
            and ALGORITHM_CONTRACT_TABLE.exists()
            and algorithm_contract_revisions == 0
            else "needs revision",
            "evidence": f"Method includes a source-anchored algorithm contract; rows={algorithm_contract_rows}; status_counts={algorithm_contract_counts}; needs_revision_count={algorithm_contract_revisions}.",
            "next_action": "Rerun analyze_algorithm_contract_table.py after changing core search implementation, method text, or source anchors.",
        },
        {
            "item": "Search-budget contract table",
            "status": "pass"
            if "tab:search-budget-contract" in text
            and SEARCH_BUDGET_ANALYSIS.exists()
            and SEARCH_BUDGET_SUMMARY.exists()
            and SEARCH_BUDGET_MANIFEST.exists()
            and SEARCH_BUDGET_TABLE.exists()
            and search_budget_revisions == 0
            else "needs revision",
            "evidence": f"Method includes an explicit search-budget and scalability contract; rows={search_budget_rows}; status_counts={search_budget_counts}; needs_revision_count={search_budget_revisions}.",
            "next_action": "Rerun analyze_search_budget_contract.py after changing SearchConfig defaults, MCTS budgets, portfolio caps, frontier controllers, or verification routes.",
        },
        {
            "item": "Baseline fairness and scope",
            "status": "pass"
            if contains_all(text, ["tab:baseline-claim-matrix", "tab:evidence-matrix", "tab:comparability-audit"])
            else "needs revision",
            "evidence": "Experimental design includes claim, evidence, and comparability matrices.",
            "next_action": "Keep cross-toolchain claims tied to the comparability audit.",
        },
        {
            "item": "Comparison protocol audit",
            "status": "pass"
            if COMPARISON_PROTOCOL_ANALYSIS.exists()
            and COMPARISON_PROTOCOL_SUMMARY.exists()
            and COMPARISON_PROTOCOL_MANIFEST.exists()
            and COMPARISON_PROTOCOL_TABLE.exists()
            and comparison_protocol_revisions == 0
            else "needs revision",
            "evidence": f"Comparison protocol audit checks layered baseline roles, evidence, comparability, counterpoints, and manuscript anchors; status_counts={comparison_protocol_counts}; needs_revision_count={comparison_protocol_revisions}.",
            "next_action": "Rerun analyze_comparison_protocol_audit.py after changing baseline claims, evidence matrices, counterpoint wording, or comparison-scope text.",
        },
        {
            "item": "Comparison target validity audit",
            "status": "pass"
            if "tab:comparison-target-validity" in text
            and COMPARISON_TARGET_VALIDITY_ANALYSIS.exists()
            and COMPARISON_TARGET_VALIDITY_SUMMARY.exists()
            and COMPARISON_TARGET_VALIDITY_MANIFEST.exists()
            and COMPARISON_TARGET_VALIDITY_TABLE.exists()
            and comparison_target_validity_revisions == 0
            and comparison_target_validity_anchor
            else "needs revision",
            "evidence": f"Comparison target validity audit labels primary benchmarks, external probes, exact reversible counterpoints, phase proxies, causal controls, scalability checks, and non-dominance boundaries; rows={comparison_target_validity_rows}; roles={comparison_target_validity_roles}; status_counts={comparison_target_validity_counts}; needs_revision_count={comparison_target_validity_revisions}; table_anchor_present={comparison_target_validity_anchor}.",
            "next_action": "Rerun analyze_comparison_target_validity_audit.py after changing comparison targets, role labels, claim boundaries, or baseline-scope manuscript text.",
        },
        {
            "item": "Comparison answer scorecard",
            "status": "pass"
            if "tab:comparison-answer-scorecard" in text
            and COMPARISON_ANSWER_ANALYSIS.exists()
            and COMPARISON_ANSWER_SUMMARY.exists()
            and COMPARISON_ANSWER_MANIFEST.exists()
            and COMPARISON_ANSWER_TABLE.exists()
            and comparison_answer_revisions == 0
            and comparison_answer_anchor
            else "needs revision",
            "evidence": f"Comparison answer scorecard gives reviewer-facing quantitative answers for comparison targets, evidence rows, outcomes, and excluded claims; rows={comparison_answer_rows}; questions={comparison_answer_questions}; status_counts={comparison_answer_counts}; needs_revision_count={comparison_answer_revisions}; table_anchor_present={comparison_answer_anchor}.",
            "next_action": "Rerun analyze_comparison_answer_scorecard.py after changing comparison outcomes, search-control rows, dominance rows, or comparison-scope manuscript text.",
        },
        {
            "item": "Resource-weight sensitivity audit",
            "status": "pass"
            if "tab:resource-weight-sensitivity" in text
            and RESOURCE_WEIGHT_SENSITIVITY_ANALYSIS.exists()
            and RESOURCE_WEIGHT_SENSITIVITY_SUMMARY.exists()
            and RESOURCE_WEIGHT_SENSITIVITY_RAW.exists()
            and RESOURCE_WEIGHT_SENSITIVITY_MANIFEST.exists()
            and RESOURCE_WEIGHT_SENSITIVITY_TABLE.exists()
            and resource_weight_revisions == 0
            and isinstance(resource_weight_raw_rows, int)
            and resource_weight_raw_rows >= 12000
            and isinstance(resource_weight_summary_rows, int)
            and resource_weight_summary_rows >= 72
            and len(resource_weight_comparisons) >= 12
            and len(resource_weight_profiles) >= 6
            and resource_weight_anchor
            else "needs revision",
            "evidence": f"Resource-weight sensitivity audit recomputes matched internal/external baselines under alternative logical-resource profiles; raw_rows={resource_weight_raw_rows}; summary_rows={resource_weight_summary_rows}; comparisons={len(resource_weight_comparisons)}; profiles={resource_weight_profiles}; status_counts={resource_weight_counts}; needs_revision_count={resource_weight_revisions}; table_anchor_present={resource_weight_anchor}.",
            "next_action": "Rerun analyze_resource_weight_sensitivity_audit.py after changing weighted-score claims, comparison targets, or resource-sensitivity manuscript text.",
        },
        {
            "item": "CNOT constraint profile audit",
            "status": "pass"
            if "tab:cnot-constraint-profile" in text
            and CNOT_CONSTRAINT_PROFILE_ANALYSIS.exists()
            and CNOT_CONSTRAINT_PROFILE_SUMMARY.exists()
            and CNOT_CONSTRAINT_PROFILE_RAW.exists()
            and CNOT_CONSTRAINT_PROFILE_MANIFEST.exists()
            and CNOT_CONSTRAINT_PROFILE_TABLE.exists()
            and cnot_constraint_revisions == 0
            and isinstance(cnot_constraint_raw_rows, int)
            and cnot_constraint_raw_rows >= 2000
            and isinstance(cnot_constraint_summary_rows, int)
            and cnot_constraint_summary_rows >= 6
            and "cnot_only" in cnot_constraint_profiles
            and isinstance(cnot_constraint_functions, int)
            and cnot_constraint_functions >= 47
            and cnot_constraint_anchor
            and cnot_constraint_anonymous_anchor
            and cnot_constraint_acm_anchor
            else "needs revision",
            "evidence": f"CNOT-only rerun audit checks that the search responds to a pure CNOT objective while preserving SSHR-H as the CNOT boundary; raw_rows={cnot_constraint_raw_rows}; summary_rows={cnot_constraint_summary_rows}; profiles={cnot_constraint_profiles}; functions_cnot_only={cnot_constraint_functions}; status_counts={cnot_constraint_counts}; needs_revision_count={cnot_constraint_revisions}; table_anchor_present={cnot_constraint_anchor}; anonymous_anchor={cnot_constraint_anonymous_anchor}; acm_anchor={cnot_constraint_acm_anchor}.",
            "next_action": "Rerun run_resource_sweep.py --resume and analyze_cnot_constraint_profile_audit.py after changing resource profiles or CNOT-only boundary wording.",
        },
        {
            "item": "SSHR reproduction-scope audit",
            "status": "pass"
            if "tab:sshr-reproduction-scope" in text
            and SSHR_REPRODUCTION_ANALYSIS.exists()
            and SSHR_REPRODUCTION_SUMMARY.exists()
            and SSHR_REPRODUCTION_MANIFEST.exists()
            and SSHR_REPRODUCTION_TABLE.exists()
            and sshr_reproduction_revisions == 0
            and isinstance(sshr_reproduction_rows, int)
            and sshr_reproduction_rows >= 8
            and sshr_reproduction_anchor
            and sshr_reproduction_anonymous_anchor
            and sshr_reproduction_acm_anchor
            else "needs revision",
            "evidence": f"SSHR reproduction-scope audit separates source-anchored SSHR paper-reference checks, same-function SSHR-H rows, timed SSHR-I rows, exact n<=4 pilot checks, and claim boundaries; rows={sshr_reproduction_rows}; status_counts={sshr_reproduction_counts}; coverage_counts={sshr_reproduction_coverage}; source_tree_available={sshr_source_tree_available}; needs_revision_count={sshr_reproduction_revisions}; table_anchor_present={sshr_reproduction_anchor}; anonymous_anchor={sshr_reproduction_anonymous_anchor}; acm_anchor={sshr_reproduction_acm_anchor}.",
            "next_action": "Rerun analyze_sshr_reproduction_scope_audit.py after changing SSHR baselines, source-reference wording, or comparison-boundary manuscript text.",
        },
        {
            "item": "Threats-to-validity audit",
            "status": "pass"
            if "tab:threats-validity" in text
            and THREATS_VALIDITY_ANALYSIS.exists()
            and THREATS_VALIDITY_SUMMARY.exists()
            and THREATS_VALIDITY_MANIFEST.exists()
            and THREATS_VALIDITY_TABLE.exists()
            and threats_validity_revisions == 0
            and threats_validity_anchor
            else "needs revision",
            "evidence": f"Threats-to-validity audit names reviewer risks, mitigation evidence, and residual boundaries; rows={threats_validity_rows}; threats={threats_validity_threats}; status_counts={threats_validity_counts}; needs_revision_count={threats_validity_revisions}; table_anchor_present={threats_validity_anchor}.",
            "next_action": "Rerun analyze_threats_to_validity_audit.py after changing limitations, claim boundaries, verification scope, or reproducibility artifacts.",
        },
        {
            "item": "Novelty/comparison scorecard",
            "status": "pass"
            if "tab:novelty-comparison-scorecard" in text
            and NOVELTY_SCORECARD_ANALYSIS.exists()
            and NOVELTY_SCORECARD_SUMMARY.exists()
            and NOVELTY_SCORECARD_MANIFEST.exists()
            and NOVELTY_SCORECARD_TABLE.exists()
            and novelty_scorecard_revisions == 0
            else "needs revision",
            "evidence": f"Novelty/comparison scorecard checks reviewer-facing method identity, baseline meaning, external probes, tradeoff visibility, AI/MCTS isolation, and scale boundary; rows={novelty_scorecard_rows}; status_counts={novelty_scorecard_counts}; needs_revision_count={novelty_scorecard_revisions}.",
            "next_action": "Rerun analyze_novelty_comparison_scorecard.py after changing contribution wording, comparison claims, reviewer/editor briefs, or baseline-scope tables.",
        },
        {
            "item": "ROS reproduction gap audit",
            "status": "pass"
            if ROS_GAP_ANALYSIS.exists()
            and ROS_GAP_SUMMARY.exists()
            and ROS_GAP_MANIFEST.exists()
            and ROS_GAP_TABLE.exists()
            and ros_gap_revisions == 0
            and not ros_gap_fully_reproduced
            and ros_gap_boundary_explicit
            else "needs revision",
            "evidence": f"ROS gap audit separates verified ROS-style LUT proxy evidence from full official ROS reproduction; rows={ros_gap_rows}; status_counts={ros_gap_counts}; coverage_counts={ros_gap_coverage}; official_ros_fully_reproduced={ros_gap_fully_reproduced}; full_ros_boundary_is_explicit={ros_gap_boundary_explicit}; needs_revision_count={ros_gap_revisions}.",
            "next_action": "Rerun analyze_ros_lut_line_sensitivity.py, analyze_ros_lut_garbage_proxy.py, and analyze_ros_reproduction_gap_audit.py after changing ROS-style LUT proxy results, line/garbage sensitivity rows, or ROS/full-tool reproduction wording.",
        },
        {
            "item": "ROS-style LUT garbage proxy",
            "status": "pass"
            if "tab:ros-garbage" in text
            and ROS_GARBAGE_ANALYSIS.exists()
            and ROS_GARBAGE_SUMMARY.exists()
            and ROS_GARBAGE_MANIFEST.exists()
            and ROS_GARBAGE_TABLE.exists()
            and ros_garbage_revisions == 0
            and ros_garbage_raw_rows == 927
            and ros_garbage_functions == 309
            and ros_garbage_anchor
            else "needs revision",
            "evidence": f"ROS-style garbage proxy re-runs verified best-K LUT DAGs under keep-all, fanout-checkpoint, and zero-checkpoint policies; raw_rows={ros_garbage_raw_rows}; functions={ros_garbage_functions}; status_counts={ros_garbage_counts}; needs_revision_count={ros_garbage_revisions}; table_anchor_present={ros_garbage_anchor}.",
            "next_action": "Rerun analyze_ros_lut_garbage_proxy.py after changing ROS-style LUT best-K rows, table anchors, or garbage-management wording.",
        },
        {
            "item": "ROS-style LUT garbage budget frontier",
            "status": "pass"
            if "tab:ros-garbage-budget-frontier" in text
            and ROS_GARBAGE_BUDGET_ANALYSIS.exists()
            and ROS_GARBAGE_BUDGET_SUMMARY.exists()
            and ROS_GARBAGE_BUDGET_MANIFEST.exists()
            and ROS_GARBAGE_BUDGET_TABLE.exists()
            and ros_garbage_budget_revisions == 0
            and ros_garbage_budget_raw_rows == 1059
            and ros_garbage_budget_summary_rows == 35
            and ros_garbage_budget_functions == 309
            and ros_garbage_budget_frontier_rows == 5
            and ros_garbage_budget_anchor
            else "needs revision",
            "evidence": f"ROS-style garbage budget frontier selects executable proxy schedules under relative line budgets; raw_rows={ros_garbage_budget_raw_rows}; summary_rows={ros_garbage_budget_summary_rows}; frontier_rows={ros_garbage_budget_frontier_rows}; functions={ros_garbage_budget_functions}; status_counts={ros_garbage_budget_counts}; needs_revision_count={ros_garbage_budget_revisions}; table_anchor_present={ros_garbage_budget_anchor}.",
            "next_action": "Rerun analyze_ros_lut_garbage_budget_frontier.py after changing ROS-style LUT garbage schedules, budget-frontier wording, or table anchors.",
        },
        {
            "item": "ROS-style exact checkpoint-subset optimizer",
            "status": "pass"
            if "tab:ros-checkpoint-optimizer" in text
            and ROS_CHECKPOINT_ANALYSIS.exists()
            and ROS_CHECKPOINT_SUMMARY.exists()
            and ROS_CHECKPOINT_MANIFEST.exists()
            and ROS_CHECKPOINT_RAW.exists()
            and ROS_CHECKPOINT_TABLE.exists()
            and ros_checkpoint_revisions == 0
            and ros_checkpoint_raw_rows == 474
            and ros_checkpoint_summary_rows == 35
            and ros_checkpoint_frontier_rows == 5
            and ros_checkpoint_solved == 192
            and ros_checkpoint_traditional == 177
            and ros_checkpoint_exact
            and not ros_checkpoint_full_ros
            and ros_checkpoint_anchor
            else "needs revision",
            "evidence": f"ROS-style checkpoint optimizer exhaustively enumerates checkpoint subsets on tractable verified LUT DAGs; raw_rows={ros_checkpoint_raw_rows}; summary_rows={ros_checkpoint_summary_rows}; frontier_rows={ros_checkpoint_frontier_rows}; solved_functions={ros_checkpoint_solved}; solved_traditional_n_le_6={ros_checkpoint_traditional}; exact_over_checkpoint_candidates={ros_checkpoint_exact}; official_ros_fully_reproduced={ros_checkpoint_full_ros}; status_counts={ros_checkpoint_counts}; needs_revision_count={ros_checkpoint_revisions}; table_anchor_present={ros_checkpoint_anchor}.",
            "next_action": "Rerun analyze_ros_lut_checkpoint_optimizer.py after changing ROS-style LUT checkpoint optimization, exact-scope wording, or table anchors.",
        },
        {
            "item": "Published STG counterpoint",
            "status": "pass"
            if "tab:stg-published" in text
            and STG_BENCHMARK_ANALYSIS.exists()
            and STG_BENCHMARK_SUMMARY.exists()
            and STG_BENCHMARK_MANIFEST.exists()
            and STG_BENCHMARK_TABLE.exists()
            and stg_revisions == 0
            and stg_benchmark_rows == 54
            and stg_raw_rows == 270
            and stg_usable_rows == 270
            else "needs revision",
            "evidence": f"Published STG benchmark counterpoint checks 54 public n=4/5 spectral representatives with 270 same-slice synthesis rows; status_counts={stg_counts}; needs_revision_count={stg_revisions}; benchmark_rows={stg_benchmark_rows}; raw_rows={stg_raw_rows}; usable_rows={stg_usable_rows}.",
            "next_action": "Rerun analyze_stg_published_benchmark.py after changing STG counterpoint wording, methods, raw rows, or the manuscript table anchor.",
        },
        {
            "item": "Schedule-proxy tradeoff audit",
            "status": "pass"
            if "tab:schedule-proxy-audit" in text
            and SCHEDULE_PROXY_ANALYSIS.exists()
            and SCHEDULE_PROXY_SUMMARY.exists()
            and SCHEDULE_PROXY_MANIFEST.exists()
            and SCHEDULE_PROXY_TABLE.exists()
            and schedule_proxy_revisions == 0
            else "needs revision",
            "evidence": f"Schedule-proxy audit checks score, T-depth proxy, and explicit auxiliary lifetime tradeoffs before hardware mapping; rows={schedule_proxy_rows}; status_counts={schedule_proxy_counts}; needs_revision_count={schedule_proxy_revisions}.",
            "next_action": "Rerun analyze_schedule_metrics.py and analyze_schedule_proxy_audit.py after changing high-dimensional frontier, truth-bridge, schedule-proxy, or auxiliary-lifetime claims.",
        },
        {
            "item": "Runtime-envelope audit",
            "status": "pass"
            if "tab:runtime-envelope-audit" in text
            and RUNTIME_ENVELOPE_ANALYSIS.exists()
            and RUNTIME_ENVELOPE_SUMMARY.exists()
            and RUNTIME_ENVELOPE_MANIFEST.exists()
            and RUNTIME_ENVELOPE_TABLE.exists()
            and runtime_envelope_revisions == 0
            and runtime_envelope_rows == 5
            and runtime_envelope_counts.get("pass", 0) == 5
            and runtime_envelope_anchor
            and runtime_envelope_anonymous_anchor
            and runtime_envelope_acm_anchor
            else "needs revision",
            "evidence": f"Runtime-envelope audit consolidates workstation wall-clock evidence for traditional, external-tool, symbolic-scale, truth-bridge, and learned-control slices; rows={runtime_envelope_rows}; status_counts={runtime_envelope_counts}; needs_revision_count={runtime_envelope_revisions}; author_anchor={runtime_envelope_anchor}; anonymous_anchor={runtime_envelope_anonymous_anchor}; acm_anchor={runtime_envelope_acm_anchor}.",
            "next_action": "Rerun analyze_runtime_envelope_audit.py after changing runtime-bearing raw CSVs, compute/reproducibility wording, or runtime-envelope table anchors.",
        },
        {
            "item": "Ultra-scale n=48--64 stress audit",
            "status": "pass"
            if "tab:ultra-scale64-stress" in text
            and ULTRA_SCALE64_ANALYSIS.exists()
            and ULTRA_SCALE64_SUMMARY.exists()
            and ULTRA_SCALE64_MANIFEST.exists()
            and ULTRA_SCALE64_TABLE.exists()
            and ultra_scale64_revisions == 0
            and ultra_scale64_rows == 480
            and ultra_scale64_plan == 480
            and ultra_scale64_circuit == 480
            and ultra_scale64_mismatch == 0
            else "needs revision",
            "evidence": f"Ultra-scale term-set stress covers n=48,56,64 with raw_rows={ultra_scale64_rows}; plan_verified={ultra_scale64_plan}; circuit_verified={ultra_scale64_circuit}; max_circuit_mismatches={ultra_scale64_mismatch}; status_counts={ultra_scale64_counts}; needs_revision_count={ultra_scale64_revisions}.",
            "next_action": "Rerun run_screen_scale_terms.py with --tag ultra_scale64, then analyze_ultra_scale64_stress.py after changing ultra-scale term-set evidence or manuscript anchors.",
        },
        {
            "item": "Ultra-scale n=48--64 resource profile",
            "status": "pass"
            if "tab:ultra-scale64-resource-profile" in text
            and ULTRA_SCALE64_PROFILE_ANALYSIS.exists()
            and ULTRA_SCALE64_PROFILE_SUMMARY.exists()
            and ULTRA_SCALE64_PROFILE_DELTA_SUMMARY.exists()
            and ULTRA_SCALE64_PROFILE_MANIFEST.exists()
            and ULTRA_SCALE64_PROFILE_TABLE.exists()
            and ultra_scale64_profile_revisions == 0
            and ultra_scale64_profile_raw_rows == 480
            and ultra_scale64_profile_plan == 480
            and ultra_scale64_profile_circuit == 480
            and ultra_scale64_profile_plan_mismatch == 0
            and ultra_scale64_profile_circuit_mismatch == 0
            and ultra_scale64_profile_rows == 20
            and ultra_scale64_delta_rows == 12
            else "needs revision",
            "evidence": f"Ultra-scale resource profile exposes score/T/CNOT/depth/ancilla/T-depth/lifetime/time means and deltas; raw_rows={ultra_scale64_profile_raw_rows}; profile_rows={ultra_scale64_profile_rows}; delta_rows={ultra_scale64_delta_rows}; plan_verified={ultra_scale64_profile_plan}; circuit_verified={ultra_scale64_profile_circuit}; max_plan_mismatches={ultra_scale64_profile_plan_mismatch}; max_circuit_mismatches={ultra_scale64_profile_circuit_mismatch}; status_counts={ultra_scale64_profile_counts}; needs_revision_count={ultra_scale64_profile_revisions}.",
            "next_action": "Rerun analyze_ultra_scale64_resource_profile.py after changing ultra-scale raw rows, resource columns, or manuscript anchors.",
        },
        {
            "item": "Search-control baseline audit",
            "status": "pass"
            if "tab:search-control-baseline-audit" in text
            and SEARCH_CONTROL_ANALYSIS.exists()
            and SEARCH_CONTROL_SUMMARY.exists()
            and SEARCH_CONTROL_MANIFEST.exists()
            and SEARCH_CONTROL_TABLE.exists()
            and search_control_revisions == 0
            else "needs revision",
            "evidence": f"Search-control audit separates heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, high-dimensional guard, bit-flip random-prior, frontier random-depth, and phase random-control evidence; rows={search_control_rows}; status_counts={search_control_counts}; needs_revision_count={search_control_revisions}.",
            "next_action": "Rerun analyze_search_control_baseline_audit.py after changing search ablations, learned-prior rows, bit-flip/frontier/phase random controls, or search-control manuscript claims.",
        },
        {
            "item": "Learned-control audit",
            "status": "pass"
            if "tab:learned-control-audit" in text
            and LEARNED_CONTROL_ANALYSIS.exists()
            and LEARNED_CONTROL_SUMMARY.exists()
            and LEARNED_CONTROL_MANIFEST.exists()
            and LEARNED_CONTROL_TABLE.exists()
            and learned_control_revisions == 0
            and isinstance(learned_control_rows, int)
            and learned_control_rows >= 9
            and isinstance(learned_control_promoted, int)
            and learned_control_promoted >= 4
            and isinstance(learned_control_bounded, int)
            and learned_control_bounded >= 2
            and isinstance(learned_control_limited, int)
            and learned_control_limited >= 2
            else "needs revision",
            "evidence": f"Learned-control audit classifies promoted, bounded, and limited AI/search controls; rows={learned_control_rows}; promoted_count={learned_control_promoted}; bounded_count={learned_control_bounded}; limited_count={learned_control_limited}; claim_class_counts={learned_control_class_counts}; status_counts={learned_control_counts}; needs_revision_count={learned_control_revisions}.",
            "next_action": "Rerun analyze_learned_control_audit.py after changing learned frontier policies, sparse depth gates, phase shortlist controls, neural guard/prior results, or AI-claim manuscript text.",
        },
        {
            "item": "Root-action ranker audit",
            "status": "pass"
            if ROOT_ACTION_RANKER_ANALYSIS.exists()
            and ROOT_ACTION_RANKER_SUMMARY.exists()
            and ROOT_ACTION_RANKER_MANIFEST.exists()
            and ROOT_ACTION_RANKER_TABLE.exists()
            and root_action_revisions == 0
            and isinstance(root_action_rows, int)
            and root_action_rows >= 5
            and isinstance(root_action_pairs, int)
            and root_action_pairs >= 30
            and root_action_wlt == "8/0/25"
            else "needs revision",
            "evidence": f"Root-action audit checks bounded learned candidate extension over n=14/n=16 root-action slices; rows={root_action_rows}; combined_pairs={root_action_pairs}; combined_score_wlt={root_action_wlt}; status_counts={root_action_counts}; needs_revision_count={root_action_revisions}.",
            "next_action": "Rerun analyze_root_action_ranker_audit.py after changing high-dimensional root-action ranker evidence or learned-control wording.",
        },
        {
            "item": "Neural/MCTS claim calibration",
            "status": "pass"
            if "tab:neural-mcts-claim-calibration" in text
            and NEURAL_MCTS_CLAIM_ANALYSIS.exists()
            and NEURAL_MCTS_CLAIM_SUMMARY.exists()
            and NEURAL_MCTS_CLAIM_MANIFEST.exists()
            and NEURAL_MCTS_CLAIM_TABLE.exists()
            and neural_mcts_claim_revisions == 0
            and neural_mcts_claim_rows == 7
            and neural_mcts_claim_anchor_present
            else "needs revision",
            "evidence": f"Neural/MCTS claim-calibration audit ties title-level neural, MCTS, resource-constrained, large-scale, and logical-layer terms to evidence gates and excluded claims; rows={neural_mcts_claim_rows}; claim_anchors={neural_mcts_claim_anchors}; status_counts={neural_mcts_claim_counts}; needs_revision_count={neural_mcts_claim_revisions}; table_anchor_present={neural_mcts_claim_anchor_present}.",
            "next_action": "Rerun analyze_neural_mcts_claim_calibration.py after changing the title, abstract, AI/MCTS wording, learned-control evidence, large-scale boundary, or logical-layer scope.",
        },
        {
            "item": "Bit-flip random-prior control",
            "status": "pass"
            if "tab:bitflip-random-prior" in text
            and BITFLIP_RANDOM_PRIOR_ANALYSIS.exists()
            and BITFLIP_RANDOM_PRIOR_SUMMARY.exists()
            and BITFLIP_RANDOM_PRIOR_MANIFEST.exists()
            and BITFLIP_RANDOM_PRIOR_TABLE.exists()
            and bitflip_random_revisions == 0
            else "needs revision",
            "evidence": f"Same-budget bit-flip random-prior control is manuscript-visible; rows={bitflip_random_rows}; status_counts={bitflip_random_counts}; needs_revision_count={bitflip_random_revisions}.",
            "next_action": "Rerun run_bitflip_random_prior_control.py and analyze_bitflip_random_prior_control.py after changing the neural prior, action features, or bit-flip learned-prior claims.",
        },
        {
            "item": "Bit-flip neural budget sweep",
            "status": "pass"
            if "tab:bitflip-budget-sweep" in text
            and BITFLIP_BUDGET_ANALYSIS.exists()
            and BITFLIP_BUDGET_SUMMARY.exists()
            and BITFLIP_BUDGET_MANIFEST.exists()
            and BITFLIP_BUDGET_TABLE.exists()
            and bitflip_budget_revisions == 0
            and isinstance(bitflip_budget_raw_rows, int)
            and bitflip_budget_raw_rows == 2124
            and isinstance(bitflip_budget_paired_rows, int)
            and bitflip_budget_paired_rows == 54
            and isinstance(bitflip_budget_low_rows, int)
            and bitflip_budget_low_rows == 6
            and isinstance(bitflip_budget_positive_rows, int)
            and bitflip_budget_positive_rows == 6
            and bitflip_budget_anchor
            else "needs revision",
            "evidence": f"Low-budget learned-prior sweep checks learned vs no-prior under compressed candidate/MCTS budgets; raw_rows={bitflip_budget_raw_rows}; paired_rows={bitflip_budget_paired_rows}; low_budget_score_rows={bitflip_budget_low_rows}; positive_low_budget_score_rows={bitflip_budget_positive_rows}; status_counts={bitflip_budget_counts}; table_anchor_present={bitflip_budget_anchor}; needs_revision_count={bitflip_budget_revisions}.",
            "next_action": "Rerun analyze_bitflip_neural_budget_sweep.py after changing low-budget learned-prior raw rows, budget labels, or manuscript table anchors.",
        },
        {
            "item": "Frontier random-depth control",
            "status": "pass"
            if "tab:frontier-random-depth" in text
            and FRONTIER_RANDOM_DEPTH_ANALYSIS.exists()
            and FRONTIER_RANDOM_DEPTH_SUMMARY.exists()
            and FRONTIER_RANDOM_DEPTH_MANIFEST.exists()
            and FRONTIER_RANDOM_DEPTH_TABLE.exists()
            and frontier_random_revisions == 0
            else "needs revision",
            "evidence": f"Same-candidate frontier random-depth control is manuscript-visible; rows={frontier_random_rows}; status_counts={frontier_random_counts}; needs_revision_count={frontier_random_revisions}.",
            "next_action": "Rerun analyze_frontier_random_depth_control.py after changing frontier policy rows, depth-2/3/4 screen candidates, or learned budget-allocation claims.",
        },
        {
            "item": "Stochastic-control stability summary",
            "status": "pass"
            if "tab:stochastic-control-stability" in text
            and STOCHASTIC_CONTROL_ANALYSIS.exists()
            and STOCHASTIC_CONTROL_SUMMARY.exists()
            and STOCHASTIC_CONTROL_MANIFEST.exists()
            and STOCHASTIC_CONTROL_TABLE.exists()
            and stochastic_revisions == 0
            and stochastic_rows == 6
            and stochastic_counts.get("pass", 0) == 6
            else "needs revision",
            "evidence": f"Stochastic-control stability summary consolidates random-prior, random-depth, phase-shortlist, and independent-seed sparse-gate checks; rows={stochastic_rows}; components={stochastic_components}; status_counts={stochastic_counts}; needs_revision_count={stochastic_revisions}.",
            "next_action": "Rerun analyze_stochastic_control_stability.py after changing random-control, phase shortlist, sparse-gate, or learned-control stability claims.",
        },
        {
            "item": "Citation support audit",
            "status": "pass"
            if CITATION_SUPPORT_ANALYSIS.exists()
            and CITATION_SUPPORT_SUMMARY.exists()
            and CITATION_SUPPORT_MANIFEST.exists()
            and citation_support_revisions == 0
            else "needs revision",
            "evidence": f"Citation support audit checks related-work families, cited BibTeX keys, bibliography resolution, and DOI/URL/eprint locator coverage; rows={citation_support_rows}; cited_keys={citation_support_keys}; status_counts={citation_support_counts}; needs_revision_count={citation_support_revisions}.",
            "next_action": "Rerun analyze_citation_support_audit.py after changing related-work text, citations, bibliography entries, or literature-positioning tables.",
        },
        {
            "item": "Paired effect uncertainty",
            "status": "pass"
            if "tab:paired-effect-uncertainty" in text
            and PAIRED_EFFECT_ANALYSIS.exists()
            and PAIRED_EFFECT_SUMMARY.exists()
            and PAIRED_EFFECT_MANIFEST.exists()
            and PAIRED_EFFECT_TABLE.exists()
            else "needs revision",
            "evidence": "Manuscript includes bootstrap uncertainty intervals for paired score-effect estimates.",
            "next_action": "Rerun analyze_paired_effect_uncertainty.py after changing paired comparisons or score fields.",
        },
        {
            "item": "Headline numeric consistency",
            "status": "pass"
            if HEADLINE_NUMERIC_ANALYSIS.exists()
            and HEADLINE_NUMERIC_SUMMARY.exists()
            and HEADLINE_NUMERIC_MANIFEST.exists()
            and headline_numeric_revisions == 0
            else "needs revision",
            "evidence": f"Headline numeric audit recomputes abstract-level numbers from CSV evidence and checks author/anonymous TeX tokens; claims={headline_numeric_claims}; status_counts={headline_numeric_counts}; needs_revision_count={headline_numeric_revisions}.",
            "next_action": "Rerun analyze_headline_numeric_consistency.py after changing headline numbers, comparison summaries, phase policy controls, or validation-row counts.",
        },
        {
            "item": "Claim-scope lint",
            "status": "pass"
            if CLAIM_SCOPE_ANALYSIS.exists()
            and CLAIM_SCOPE_SUMMARY.exists()
            and CLAIM_SCOPE_MANIFEST.exists()
            and claim_scope_unresolved == 0
            else "needs revision",
            "evidence": f"Claim-scope lint scans manuscript and handoff files; unresolved_count={claim_scope_unresolved}.",
            "next_action": "Rerun analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims.",
        },
        {
            "item": "Reproducibility evidence",
            "status": "pass" if "tab:reproducibility" in text else "needs revision",
            "evidence": "Manuscript includes compute, worker, artifact, and external-tool provenance table.",
            "next_action": "Rerun analyze_reproducibility_audit.py after adding scripts, tables, or figures.",
        },
        {
            "item": "Figure asset audit",
            "status": "pass"
            if FIGURE_ASSET_ANALYSIS.exists()
            and FIGURE_ASSET_SUMMARY.exists()
            and FIGURE_ASSET_MANIFEST.exists()
            and figure_asset_revisions == 0
            else "needs revision",
            "evidence": f"Figure asset audit checks manuscript figure references, generated PDF/PNG/SVG assets, and source-data CSVs; figures={figure_count}; status_counts={figure_asset_counts}; needs_revision_count={figure_asset_revisions}.",
            "next_action": "Rerun make_submission_figures.py and analyze_figure_asset_audit.py after changing figure code, source data, or TeX figure references.",
        },
        {
            "item": "LaTeX dependency audit",
            "status": "pass"
            if LATEX_DEPENDENCY_ANALYSIS.exists()
            and LATEX_DEPENDENCY_SUMMARY.exists()
            and LATEX_DEPENDENCY_MANIFEST.exists()
            and latex_dependency_revisions == 0
            else "needs revision",
            "evidence": f"LaTeX dependency audit checks author, anonymous, and ACM/TQC sources, table inputs, figure references, and bibliography files against local files and the upload payload; dependencies={latex_dependency_count}; type_counts={latex_dependency_types}; status_counts={latex_dependency_counts}; needs_revision_count={latex_dependency_revisions}.",
            "next_action": "Rerun make_submission_payload_archive.py and analyze_latex_dependency_audit.py after editing TeX inputs, figures, bibliography, or payload packaging.",
        },
        {
            "item": "PDF visual render audit",
            "status": "pass"
            if PDF_VISUAL_ANALYSIS.exists()
            and PDF_VISUAL_SUMMARY.exists()
            and PDF_VISUAL_MANIFEST.exists()
            and pdf_visual_revisions == 0
            else "needs revision",
            "evidence": f"PDF visual audit renders every author/anonymous page with Poppler and checks page count, dimensions, nonblank ink coverage, and render errors; rows={pdf_visual_rows}; status_counts={pdf_visual_counts}; needs_revision_count={pdf_visual_revisions}.",
            "next_action": "Rerun analyze_pdf_visual_audit.py after rebuilding PDFs; inspect rendered pages if any page is blank, clipped, or overfilled.",
        },
        {
            "item": "PDF text/searchability audit",
            "status": "pass"
            if PDF_TEXT_ANALYSIS.exists()
            and PDF_TEXT_SUMMARY.exists()
            and PDF_TEXT_MANIFEST.exists()
            and pdf_text_revisions == 0
            else "needs revision",
            "evidence": f"PDF text audit extracts author/anonymous PDFs with Poppler pdftotext and checks title, scope, baseline, availability, reference, headline-number, identity, and placeholder anchors; rows={pdf_text_rows}; required_anchors={pdf_text_anchor_count}; status_counts={pdf_text_counts}; needs_revision_count={pdf_text_revisions}.",
            "next_action": "Rerun analyze_pdf_text_audit.py after rebuilding PDFs; inspect extracted text if anchors, identity separation, or public-placeholder hygiene fail.",
        },
        {
            "item": "PDF metadata/privacy audit",
            "status": "pass"
            if PDF_METADATA_ANALYSIS.exists()
            and PDF_METADATA_SUMMARY.exists()
            and PDF_METADATA_MANIFEST.exists()
            and pdf_metadata_revisions == 0
            else "needs revision",
            "evidence": f"PDF metadata audit checks author/anonymous pdfinfo metadata, page geometry, encryption, JavaScript, forms, and privacy-sensitive metadata strings; rows={pdf_metadata_rows}; status_counts={pdf_metadata_counts}; needs_revision_count={pdf_metadata_revisions}.",
            "next_action": "Rerun analyze_pdf_metadata_audit.py after rebuilding PDFs; sanitize hyperref metadata or PDF flags if privacy or active-content checks fail.",
        },
        {
            "item": "Raw rerun registry",
            "status": "pass"
            if RERUN_REGISTRY_ANALYSIS.exists()
            and RERUN_REGISTRY_SUMMARY.exists()
            and RERUN_REGISTRY_MANIFEST.exists()
            and RERUN_REGISTRY_TABLE.exists()
            else "needs revision",
            "evidence": "Artifact rerun registry maps evidence families to driver scripts, raw CSV coverage, manifests, rerun tiers, and dependency boundaries.",
            "next_action": "Rerun analyze_artifact_rerun_registry.py after adding raw data families, run scripts, or external-tool probes.",
        },
        {
            "item": "Claim-to-artifact traceability",
            "status": "pass" if "tab:traceability-audit" in text else "needs revision",
            "evidence": "Manuscript includes a submission traceability audit linking claim families to scripts, data, tables, and figures.",
            "next_action": "Rerun analyze_submission_traceability_audit.py after adding or moving headline evidence.",
        },
        {
            "item": "Archive package manifest",
            "status": "pass"
            if contains_all(text, ["tab:archive-manifest", "submission archive manifest"])
            and ARCHIVE_ANALYSIS.exists()
            and ARCHIVE_SUMMARY.exists()
            and ARCHIVE_MANIFEST.exists()
            else "needs revision",
            "evidence": "Manuscript includes an archive-level payload manifest with generated CSV, Markdown, and JSON outputs.",
            "next_action": "Rerun analyze_submission_archive_manifest.py after adding tables, figures, scripts, models, or result files.",
        },
        {
            "item": "Submission support templates",
            "status": "pass" if all(path.exists() for path in SUPPORT_FILES) else "needs revision",
            "evidence": "Package README, author-input packet, Chinese final handoff, artifact guide, cover letter, author declarations, upload checklist, reviewer-concern brief, editor-screening brief, and target-venue brief are present.",
            "next_action": "Fill the author-specific fields before journal upload.",
        },
        {
            "item": "Editorial screening audit",
            "status": "pass"
            if EDITORIAL_SCREENING_ANALYSIS.exists()
            and EDITORIAL_SCREENING_SUMMARY.exists()
            and EDITORIAL_SCREENING_MANIFEST.exists()
            and EDITORIAL_SCREENING_TABLE.exists()
            and editorial_screening_revisions == 0
            else "needs revision",
            "evidence": f"Editorial screening audit checks scope, novelty, comparison route, counterpoints, AI-claim boundary, large-scale verification boundary, reproducibility path, author/venue gate, and editor reading path; rows={editorial_screening_rows}; status_counts={editorial_screening_counts}; needs_revision_count={editorial_screening_revisions}.",
            "next_action": "Rerun analyze_editorial_screening_audit.py after changing editor/reviewer briefs, claim-scope text, comparison protocol, metadata closure, or submission support docs.",
        },
        {
            "item": "Target-venue decision audit",
            "status": "pass"
            if TARGET_VENUE_DECISION_ANALYSIS.exists()
            and TARGET_VENUE_DECISION_SUMMARY.exists()
            and TARGET_VENUE_DECISION_MANIFEST.exists()
            and TARGET_VENUE_DECISION_TABLE.exists()
            and target_venue_revisions == 0
            else "needs revision",
            "evidence": f"Target-venue audit checks source-backed fit, risk, policy gates, metadata fields, and recommended order; rows={target_venue_rows}; status_counts={target_venue_counts}; recommended_first_choice={target_venue_first}; strong_fit_count={target_venue_strong}; needs_revision_count={target_venue_revisions}.",
            "next_action": "Rerun analyze_target_venue_decision_audit.py after changing target_venue_brief.md, metadata template fields, or venue shortlist/order.",
        },
        {
            "item": "Target-venue policy checklist",
            "status": "pass"
            if TARGET_VENUE_POLICY_ANALYSIS.exists()
            and TARGET_VENUE_POLICY_SUMMARY.exists()
            and TARGET_VENUE_POLICY_MANIFEST.exists()
            and TARGET_VENUE_POLICY_CHECKLIST.exists()
            and target_policy_revisions == 0
            else "needs revision",
            "evidence": f"Target-venue policy checklist maps ACM TQC, Quantum, and generic archive/license gates to private metadata fields; rows={target_policy_rows}; venues={target_policy_venues}; status_counts={target_policy_counts}; needs_revision_count={target_policy_revisions}.",
            "next_action": "Rerun analyze_target_venue_policy_checklist.py after changing target venue policy sources, metadata paths, or author-facing upload instructions.",
        },
        {
            "item": "Target-venue ACM/TQC format smoke",
            "status": "pass"
            if TARGET_VENUE_FORMAT_ANALYSIS.exists()
            and TARGET_VENUE_FORMAT_SUMMARY.exists()
            and TARGET_VENUE_FORMAT_MANIFEST.exists()
            and TARGET_VENUE_FORMAT_SOURCE.exists()
            and TARGET_VENUE_FORMAT_PDF.exists()
            and target_format_revisions == 0
            and target_format_rows == 5
            and isinstance(target_format_pages, int)
            and target_format_pages > 0
            else "needs revision",
            "evidence": f"ACM/TQC smoke draft checks acmart availability, generated anonymous review source, compiled PDF, text anchors, and recommended-venue alignment; rows={target_format_rows}; status_counts={target_format_counts}; pages={target_format_pages}; bytes={target_format_bytes}; needs_revision_count={target_format_revisions}.",
            "next_action": "Rerun make_acm_tqc_review_draft.py, compile the ACM/TQC source, and rerun analyze_target_venue_format_smoke.py after changing target venue formatting.",
        },
        {
            "item": "Submission support packet audit",
            "status": "pass"
            if SUPPORT_PACKET_ANALYSIS.exists()
            and SUPPORT_PACKET_SUMMARY.exists()
            and SUPPORT_PACKET_MANIFEST.exists()
            and SUPPORT_PACKET_TABLE.exists()
            and support_packet_revisions == 0
            else "needs revision",
            "evidence": f"Support packet audit checks cover letter, declarations, target-venue brief, venue policy checklist, upload checklist, handoff, comparison matrix, comparison evidence-entrypoint integrity, minimal author form, private-preview gate, anonymous-review fork, and editor/reviewer triage; rows={support_packet_rows}; status_counts={support_packet_counts}; needs_revision_count={support_packet_revisions}.",
            "next_action": "Rerun analyze_submission_support_packet_audit.py after changing cover letter, declarations, venue brief, venue-policy checklist, upload checklist, comparison docs, handoff docs, metadata template, or editor/reviewer support docs.",
        },
        {
            "item": "Submission metadata audit",
            "status": "pass"
            if METADATA_ANALYSIS.exists() and METADATA_SUMMARY.exists() and METADATA_MANIFEST.exists()
            else "needs revision",
            "evidence": "Author- and venue-specific metadata fields are enumerated in CSV, Markdown, and JSON audit outputs.",
            "next_action": "Rerun analyze_submission_metadata_audit.py after filling author declarations or choosing a target venue.",
        },
        {
            "item": "Submission metadata validator",
            "status": "pass"
            if METADATA_VALIDATOR_ANALYSIS.exists()
            and METADATA_VALIDATOR_SUMMARY.exists()
            and METADATA_VALIDATOR_MANIFEST.exists()
            and metadata_validator_revisions == 0
            else "needs revision",
            "evidence": f"Private metadata format validator exists; status_counts={metadata_validator_counts}; needs_revision_count={metadata_validator_revisions}.",
            "next_action": "Rerun validate_submission_metadata.py after filling private metadata; fix format or consistency rows before upload.",
        },
        {
            "item": "Submission metadata pipeline self-test",
            "status": "pass"
            if METADATA_PIPELINE_SELFTEST_ANALYSIS.exists()
            and METADATA_PIPELINE_SELFTEST_SUMMARY.exists()
            and METADATA_PIPELINE_SELFTEST_MANIFEST.exists()
            and metadata_selftest_revisions == 0
            and metadata_selftest_synthetic
            and not metadata_selftest_writes_private
            else "needs revision",
            "evidence": f"Synthetic metadata self-test exercises validator and preview renderers; status_counts={metadata_selftest_counts}; needs_revision_count={metadata_selftest_revisions}; synthetic_only={metadata_selftest_synthetic}; writes_private_outputs={metadata_selftest_writes_private}.",
            "next_action": "Rerun selftest_submission_metadata_pipeline.py after changing required metadata paths, validators, or preview renderers.",
        },
        {
            "item": "Private submission text preview",
            "status": "pass"
            if TEXT_PREVIEW_ANALYSIS.exists()
            and TEXT_PREVIEW_SUMMARY.exists()
            and TEXT_PREVIEW_MANIFEST.exists()
            and private_outputs_ignored
            else "needs revision",
            "evidence": f"Private preview generator audit exists; status_counts={text_preview_counts}; private_outputs_are_git_ignored={private_outputs_ignored}.",
            "next_action": "Rerun make_submission_text_preview.py after filling private metadata; generated_*.md files must remain ignored by Git.",
        },
        {
            "item": "Anonymous-review readiness path",
            "status": "pass"
            if ANONYMOUS_REVIEW_ANALYSIS.exists()
            and ANONYMOUS_REVIEW_SUMMARY.exists()
            and ANONYMOUS_REVIEW_MANIFEST.exists()
            and anonymous_revisions == 0
            else "needs revision",
            "evidence": f"Anonymous-review audit exists; status_counts={anonymous_counts}; needs_revision_count={anonymous_revisions}; needs_author_input_count={anonymous_author_input}.",
            "next_action": "If the selected venue requires double-blind review, produce an anonymized manuscript copy and anonymous artifact links before upload.",
        },
        {
            "item": "Author-input closure audit",
            "status": "pass"
            if AUTHOR_INPUT_CLOSURE_ANALYSIS.exists()
            and AUTHOR_INPUT_CLOSURE_SUMMARY.exists()
            and AUTHOR_INPUT_CLOSURE_MANIFEST.exists()
            and author_input_closure_revisions == 0
            else "needs revision",
            "evidence": f"Author-input closure audit checks metadata-template placeholder coverage, author packet coverage, support-document visibility, private Git protection, private-preview gates, anonymous-review decision gate, and metadata/packet count consistency; required_metadata_paths={author_input_required_paths}; status_counts={author_input_closure_counts}; needs_revision_count={author_input_closure_revisions}.",
            "next_action": "Rerun analyze_author_input_closure_audit.py after changing author/venue metadata fields, private-output names, support docs, or anonymous-review gates.",
        },
        {
            "item": "Author questionnaire coverage audit",
            "status": "pass"
            if AUTHOR_QUESTIONNAIRE_COVERAGE_ANALYSIS.exists()
            and AUTHOR_QUESTIONNAIRE_COVERAGE_SUMMARY.exists()
            and AUTHOR_QUESTIONNAIRE_COVERAGE_MANIFEST.exists()
            and author_questionnaire_revisions == 0
            and not author_questionnaire_missing
            else "needs revision",
            "evidence": f"Questionnaire coverage audit checks every private metadata path against AUTHOR_METADATA_QUESTIONNAIRE_zh.md; required_paths={author_questionnaire_required}; missing_required_paths={author_questionnaire_missing}; status_counts={author_questionnaire_counts}; needs_revision_count={author_questionnaire_revisions}.",
            "next_action": "Rerun analyze_author_questionnaire_coverage.py after changing submission_metadata_template.json or AUTHOR_METADATA_QUESTIONNAIRE_zh.md.",
        },
        {
            "item": "Metadata answer-template coverage audit",
            "status": "pass"
            if METADATA_ANSWER_TEMPLATE_ANALYSIS.exists()
            and METADATA_ANSWER_TEMPLATE_SUMMARY.exists()
            and METADATA_ANSWER_TEMPLATE_MANIFEST.exists()
            and metadata_answer_revisions == 0
            and not metadata_answer_missing
            and not metadata_answer_unknown
            and not metadata_answer_private_like
            else "needs revision",
            "evidence": f"Answer-template coverage audit checks the tracked short-answer JSON template against required private metadata paths; required_metadata_paths={metadata_answer_required}; answer_template_required_paths={metadata_answer_template_paths}; starter_only_required_paths={metadata_answer_starter_only}; missing_required_paths={metadata_answer_missing}; unknown_answer_paths={metadata_answer_unknown}; remaining_author_paths={metadata_answer_remaining}; private_like_value_paths={metadata_answer_private_like}; status_counts={metadata_answer_counts}; needs_revision_count={metadata_answer_revisions}.",
            "next_action": "Rerun analyze_metadata_answer_template_coverage.py after changing submission_metadata_answers_template.json, REQUIRED_METADATA_PATHS, or metadata starter behavior.",
        },
        {
            "item": "Submission metadata closure path",
            "status": "pass"
            if METADATA_CLOSURE_ANALYSIS.exists()
            and METADATA_CLOSURE_SUMMARY.exists()
            and METADATA_CLOSURE_MANIFEST.exists()
            and metadata_closure_revisions == 0
            and metadata_closure_ready
            else "needs revision",
            "evidence": f"Metadata closure-path audit checks structured intake coverage, safe public starter prefill, Git ignore protection, validator/private-preview gates, synthetic filled-metadata rehearsal, anonymous-review gate, handoff docs, and goal-closure consistency; required_metadata_paths={metadata_closure_paths}; status_counts={metadata_closure_counts}; needs_revision_count={metadata_closure_revisions}; closure_path_ready={metadata_closure_ready}.",
            "next_action": "Rerun analyze_submission_metadata_closure_path.py after changing metadata templates, validator behavior, preview outputs, anonymous-review policy fields, or author handoff docs.",
        },
        {
            "item": "Compiled anonymous review draft",
            "status": "pass" if ANONYMOUS_PAPER.exists() and ANONYMOUS_PDF.exists() else "needs revision",
            "evidence": f"anonymous_source_exists={ANONYMOUS_PAPER.exists()}; anonymous_pdf_exists={ANONYMOUS_PDF.exists()}.",
            "next_action": "Run make_anonymous_review_draft.py and rebuild the PDF if a double-blind venue is selected.",
        },
        {
            "item": "Goal completion audit",
            "status": "pass"
            if GOAL_ANALYSIS.exists() and GOAL_SUMMARY.exists() and GOAL_MANIFEST.exists()
            else "needs revision",
            "evidence": "The original project objective is mapped to concrete evidence files, boundaries, and remaining author-gated items.",
            "next_action": "Rerun analyze_goal_completion_audit.py after adding major evidence or filling author/venue metadata.",
        },
        {
            "item": "Uploadable payload archive",
            "status": "pass"
            if PAYLOAD_ARCHIVE.exists()
            and PAYLOAD_SHA256.exists()
            and PAYLOAD_ANALYSIS.exists()
            and PAYLOAD_SUMMARY.exists()
            and PAYLOAD_MANIFEST.exists()
            else "needs revision",
            "evidence": "Deterministic submission payload tarball, SHA256 sidecar, CSV, Markdown, and JSON manifest are present.",
            "next_action": "Rerun make_submission_payload_archive.py after adding or removing upload payload files.",
        },
        {
            "item": "Payload round-trip integrity",
            "status": "pass"
            if PAYLOAD_ROUNDTRIP_ANALYSIS.exists()
            and PAYLOAD_ROUNDTRIP_SUMMARY.exists()
            and PAYLOAD_ROUNDTRIP_MANIFEST.exists()
            and payload_roundtrip_revisions == 0
            else "needs revision",
            "evidence": f"Payload round-trip audit exists; status_counts={payload_roundtrip_counts}; needs_revision_count={payload_roundtrip_revisions}.",
            "next_action": "Rerun analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues.",
        },
        {
            "item": "Generated payload Git policy",
            "status": "pass"
            if PAYLOAD_GIT_POLICY_ANALYSIS.exists()
            and PAYLOAD_GIT_POLICY_SUMMARY.exists()
            and PAYLOAD_GIT_POLICY_MANIFEST.exists()
            and payload_git_policy_revisions == 0
            else "needs revision",
            "evidence": f"Payload tarball/sidecar are generated local artifacts, present after rebuild, SHA-checked, and excluded from Git; rows={payload_git_policy_rows}; status_counts={payload_git_policy_counts}; needs_revision_count={payload_git_policy_revisions}.",
            "next_action": "Rerun analyze_payload_git_policy_audit.py after payload creation and keep dist/*.tar.gz out of the Git index.",
        },
        {
            "item": "Source/path privacy audit",
            "status": "pass"
            if SOURCE_PATH_PRIVACY_ANALYSIS.exists()
            and SOURCE_PATH_PRIVACY_SUMMARY.exists()
            and SOURCE_PATH_PRIVACY_MANIFEST.exists()
            and source_path_privacy_revisions == 0
            else "needs revision",
            "evidence": f"Source/path privacy audit separates strict manuscript/support path gates from allowed experiment-provenance local paths; rows={source_path_privacy_rows}; payload_local_path_files={source_path_privacy_payload_paths}; status_counts={source_path_privacy_counts}; needs_revision_count={source_path_privacy_revisions}.",
            "next_action": "Rerun analyze_source_path_privacy_audit.py after payload creation and remove local paths from manuscript/support sources while keeping toolchain paths only in provenance outputs.",
        },
        {
            "item": "Payload extraction smoke test",
            "status": "pass"
            if PAYLOAD_EXTRACTION_SMOKE_ANALYSIS.exists()
            and PAYLOAD_EXTRACTION_SMOKE_SUMMARY.exists()
            and PAYLOAD_EXTRACTION_SMOKE_MANIFEST.exists()
            and payload_smoke_revisions == 0
            else "needs revision",
            "evidence": f"Payload extraction smoke audit runs lightweight checks from an extracted payload tree; status_counts={payload_smoke_counts}; needs_revision_count={payload_smoke_revisions}.",
            "next_action": "Rerun analyze_payload_extraction_smoke_audit.py after payload creation and fix extraction or in-payload script execution failures.",
        },
        {
            "item": "Payload verifier smoke audit",
            "status": "pass"
            if PAYLOAD_VERIFIER_SMOKE_ANALYSIS.exists()
            and PAYLOAD_VERIFIER_SMOKE_SUMMARY.exists()
            and PAYLOAD_VERIFIER_SMOKE_MANIFEST.exists()
            and payload_verifier_revisions == 0
            else "needs revision",
            "evidence": f"Payload verifier smoke audit extracts the upload tarball and runs verify_submission_package.sh inside the extracted payload tree; verifier_returncode={payload_verifier_returncode}; verifier_rows={payload_verifier_rows}; source_verifier_rows={payload_verifier_source_rows}; row_delta={payload_verifier_row_delta}; expected_row_delta={payload_verifier_expected_delta}; row_delta_reason={payload_verifier_delta_reason}; status_counts={payload_verifier_counts}; needs_revision_count={payload_verifier_revisions}.",
            "next_action": "Rerun analyze_payload_verifier_smoke_audit.py after payload creation and fix extracted one-command verifier failures.",
        },
        {
            "item": "Payload LaTeX compile audit",
            "status": "pass"
            if PAYLOAD_LATEX_COMPILE_ANALYSIS.exists()
            and PAYLOAD_LATEX_COMPILE_SUMMARY.exists()
            and PAYLOAD_LATEX_COMPILE_MANIFEST.exists()
            and payload_latex_revisions == 0
            else "needs revision",
            "evidence": f"Payload LaTeX compile audit extracts the upload tarball and rebuilds author, anonymous, and ACM/TQC PDFs from the extracted TeX sources; compiled_manuscripts={payload_latex_compiled}; status_counts={payload_latex_counts}; needs_revision_count={payload_latex_revisions}.",
            "next_action": "Rerun analyze_payload_latex_compile_audit.py after payload creation and restore missing extracted-payload LaTeX dependencies.",
        },
        {
            "item": "Terminal package verifier",
            "status": "pass"
            if VERIFY_SCRIPT.exists()
            and VERIFIER_ANALYSIS.exists()
            and VERIFIER_SUMMARY.exists()
            and VERIFIER_MANIFEST.exists()
            else "needs revision",
            "evidence": "Fast pre-upload verifier script and read-only verifier outputs check author/anonymous PDF availability, ACM/TQC format smoke, PDF visual rendering, PDF text/searchability, PDF metadata/privacy, source/path privacy, payload SHA consistency, readiness state, raw registry coverage, claim-scope lint, comparison-protocol coverage, citation support, headline numeric consistency, figure assets, LaTeX dependency closure, private metadata validation, metadata-pipeline self-test, anonymous-review readiness, author-input closure, private-preview protection, private payload exclusion, payload round-trip integrity, extraction smoke checks, extracted-payload LaTeX compilation, extracted-payload verifier smoke, and LaTeX log boundaries.",
            "next_action": "Run verify_submission_package.sh after rebuilding the payload archive.",
        },
        {
            "item": "Derived package rebuild command",
            "status": "pass" if REBUILD_SCRIPT.exists() and rebuild_cited else "needs revision",
            "evidence": "A lightweight rebuild script is present and cited in Data and Code Availability.",
            "next_action": "Keep the rebuild script aligned with paper-facing analysis, figure, audit, and PDF outputs.",
        },
        {
            "item": "Limitations and failure modes",
            "status": "pass"
            if contains_all(text, ["Several limitations are deliberate", "full ROS reproduction", "not a hardware mapping"])
            else "needs revision",
            "evidence": "Discussion names logical-layer, ROS-proxy, RevKit-derived, and high-dimensional bridge boundaries.",
            "next_action": "Add any new negative result to Discussion rather than hiding it in tables.",
        },
        {
            "item": "Data and code availability",
            "status": "pass" if "Data and Code Availability" in text else "needs revision",
            "evidence": "Manuscript has an availability section pointing to scripts, CSVs, manifests, tables, and figures.",
            "next_action": "Replace repository-relative wording with an archival DOI or anonymous link at submission time if required.",
        },
        {
            "item": "Clean submission source",
            "status": "pass" if not todo_hits else "needs revision",
            "evidence": f"{len(todo_hits)} TODO/TBD/placeholder markers in submission TeX.",
            "next_action": "Remove all source placeholders before journal upload.",
        },
        {
            "item": "Compiled PDF artifact",
            "status": "pass" if pages not in {"missing", "unknown"} else "needs revision",
            "evidence": f"Compiled PDF detected with {pages} pages.",
            "next_action": "Run latexmk and visual spot checks after each table or figure change.",
        },
        {
            "item": "Author-specific declarations",
            "status": "needs author input",
            "evidence": "Funding, acknowledgements, author metadata, competing interests, target-venue fields, and final archival links are author-specific even though templates, metadata audit, and goal-completion audit are prepared.",
            "next_action": "Complete `submission_package/author_declarations_template.md`, update the cover letter/checklist, and replace repository-relative availability links at the target journal's submission step.",
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "status", "evidence", "next_action"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Readiness Audit",
        "",
        "This audit checks paper-level readiness markers in `paper_latex/resource_nmcts_submission_v1.tex` and the compiled PDF.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| item | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_readiness_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_readiness_audit.md", rows)
    print(f"wrote {RESULTS / 'summary_submission_readiness_audit.csv'}")
    print(f"wrote {RESULTS / 'analysis_submission_readiness_audit.md'}")


if __name__ == "__main__":
    main()
