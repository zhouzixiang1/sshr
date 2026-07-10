#!/usr/bin/env python3
"""Read-only verifier for the current submission package.

The verifier runs after the payload archive has been created.  It checks the
terminal package invariants that are easy to regress during final polishing:
compiled PDF availability, payload SHA consistency, readiness status, raw rerun
registry coverage, claim-scope hygiene, comparison-protocol coverage,
comparison-target validity,
comparison-claim hierarchy,
baseline fairness ledger,
comparison-route decision support,
benchmark-suite composition,
experimental evidence ladder,
score-weight robustness,
rerun CNOT-constraint profile,
SSHR reproduction-scope support,
threats-to-validity coverage,
novelty/comparison scorecard coverage,
public handoff freshness,
published STG counterpoint,
traditional structure-mechanism support,
search-control baseline coverage,
learned-control audit coverage,
limited learned-control boundary coverage,
learned-control effect-uncertainty coverage,
learned-prior difficulty-slice localization,
learned-prior feature-gate localization,
learned-prior cross-validated feature-gate localization,
learned-prior cross-validated feature-gate random control,
neural/MCTS claim-calibration coverage,
runtime-envelope feasibility coverage,
frontier random-depth control coverage,
ultra-scale n=48--64 stress coverage,
ultra-scale n=48--64 resource-profile coverage,
editorial screening support,
target-venue decision support,
submission support packet coverage,
ROS reproduction-boundary support,
citation support,
learning-guided citation verification,
headline-numeric consistency,
figure-asset coverage,
LaTeX dependency closure,
PDF visual rendering,
PDF text/searchability,
PDF metadata/privacy,
source/path privacy,
private-metadata starter dry-run, private-metadata validation,
synthetic metadata-pipeline self-testing, anonymous-review decision support,
author-input closure,
final human-gate closure,
final upload sequence closure,
upload bundle matrix closure,
final upload-plan generation closure,
private-preview protection, private payload exclusion, payload round-trip
integrity, generated-payload Git policy, extracted-payload smoke checks,
extracted-payload LaTeX compilation, extracted-payload verifier smoke,
and LaTeX log cleanliness.  It
writes a small audit report but does not rerun experiments or alter manuscript
sources.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
LOG = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.log"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
ANONYMOUS_LOG = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.log"
PAYLOAD = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
READINESS = RESULTS / "summary_submission_readiness_audit.csv"
ARCHIVE_MANIFEST_SUMMARY = RESULTS / "summary_submission_archive_manifest.csv"
ARCHIVE_MANIFEST_JSON = RESULTS / "manifest_submission_archive_manifest.json"
ARCHIVE_MANIFEST_TABLE = THIS_DIR / "paper_latex" / "tables" / "submission_archive_manifest.tex"
REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"
COMPARISON_PROTOCOL_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_protocol_audit.tex"
COMPARISON_TARGET_VALIDITY_MANIFEST = RESULTS / "manifest_comparison_target_validity_audit.json"
COMPARISON_TARGET_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_target_validity_audit.tex"
COMPARISON_CLAIM_HIERARCHY_MANIFEST = RESULTS / "manifest_comparison_claim_hierarchy.json"
COMPARISON_CLAIM_HIERARCHY_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_claim_hierarchy.tex"
COMPARISON_ANSWER_SCORECARD_MANIFEST = RESULTS / "manifest_comparison_answer_scorecard.json"
COMPARISON_ANSWER_SCORECARD_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_answer_scorecard.tex"
BASELINE_FAIRNESS_LEDGER_MANIFEST = RESULTS / "manifest_baseline_fairness_ledger.json"
BASELINE_FAIRNESS_LEDGER_TABLE = THIS_DIR / "paper_latex" / "tables" / "baseline_fairness_ledger.tex"
COMPARISON_ROUTE_DECISION_MANIFEST = RESULTS / "manifest_comparison_route_decision_audit.json"
COMPARISON_ROUTE_DECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_route_decision_audit.tex"
BENCHMARK_SUITE_MANIFEST = RESULTS / "manifest_benchmark_suite_audit.json"
BENCHMARK_SUITE_TABLE = THIS_DIR / "paper_latex" / "tables" / "benchmark_suite_audit.tex"
BENCHMARK_FUNCTION_DIVERSITY_MANIFEST = RESULTS / "manifest_benchmark_function_diversity_audit.json"
BENCHMARK_FUNCTION_DIVERSITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "benchmark_function_diversity_audit.tex"
EXPERIMENTAL_EVIDENCE_LADDER_MANIFEST = RESULTS / "manifest_experimental_evidence_ladder.json"
EXPERIMENTAL_EVIDENCE_LADDER_TABLE = THIS_DIR / "paper_latex" / "tables" / "experimental_evidence_ladder.tex"
WEIGHT_ROBUSTNESS_MANIFEST = RESULTS / "manifest_weight_robustness.json"
WEIGHT_ROBUSTNESS_TABLE = THIS_DIR / "paper_latex" / "tables" / "weight_robustness_compact.tex"
RESOURCE_WEIGHT_SENSITIVITY_MANIFEST = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
RESOURCE_WEIGHT_SENSITIVITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "resource_weight_sensitivity_audit.tex"
CNOT_CONSTRAINT_PROFILE_MANIFEST = RESULTS / "manifest_cnot_constraint_profile_audit.json"
CNOT_CONSTRAINT_PROFILE_TABLE = THIS_DIR / "paper_latex" / "tables" / "cnot_constraint_profile_audit.tex"
SSHR_REPRODUCTION_MANIFEST = RESULTS / "manifest_sshr_reproduction_scope_audit.json"
SSHR_REPRODUCTION_TABLE = THIS_DIR / "paper_latex" / "tables" / "sshr_reproduction_scope_audit.tex"
SSHR_TABLE8_RAW = RESULTS / "raw_sshr_table8_candidate_counts.csv"
SSHR_TABLE8_MANIFEST = RESULTS / "manifest_sshr_table8_candidate_counts.json"
SSHR_TABLE8_TABLE = THIS_DIR / "paper_latex" / "tables" / "sshr_table8_candidate_counts.tex"
SSHR_CROSSWALK_MANIFEST = RESULTS / "manifest_sshr_paper_table_crosswalk.json"
SSHR_CROSSWALK_SUMMARY = RESULTS / "summary_sshr_paper_table_crosswalk.csv"
SSHR_CROSSWALK_ANALYSIS = RESULTS / "analysis_sshr_paper_table_crosswalk.md"
SSHR_CROSSWALK_TABLE = THIS_DIR / "paper_latex" / "tables" / "sshr_paper_table_crosswalk.tex"
THREATS_VALIDITY_MANIFEST = RESULTS / "manifest_threats_to_validity_audit.json"
THREATS_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "threats_to_validity_audit.tex"
NOVELTY_SCORECARD_MANIFEST = RESULTS / "manifest_novelty_comparison_scorecard.json"
NOVELTY_SCORECARD_TABLE = THIS_DIR / "paper_latex" / "tables" / "novelty_comparison_scorecard.tex"
PUBLIC_HANDOFF_MANIFEST = RESULTS / "manifest_public_handoff_freshness_audit.json"
ROS_GAP_MANIFEST = RESULTS / "manifest_ros_reproduction_gap_audit.json"
CATERPILLAR_PROBE_MANIFEST = RESULTS / "manifest_caterpillar_ros_family_probe.json"
CATERPILLAR_PROBE_TABLE = THIS_DIR / "paper_latex" / "tables" / "caterpillar_ros_family_probe.tex"
CATERPILLAR_API_MANIFEST = RESULTS / "manifest_caterpillar_xag_api_probe.json"
CATERPILLAR_API_RAW = RESULTS / "raw_caterpillar_xag_api_probe.csv"
CATERPILLAR_API_BEST = RESULTS / "raw_caterpillar_xag_api_best.csv"
CATERPILLAR_API_TABLE = THIS_DIR / "paper_latex" / "tables" / "caterpillar_xag_api_probe.tex"
ROS_GARBAGE_MANIFEST = RESULTS / "manifest_ros_lut_garbage_proxy.json"
ROS_GARBAGE_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_proxy.tex"
ROS_GARBAGE_BUDGET_MANIFEST = RESULTS / "manifest_ros_lut_garbage_budget_frontier.json"
ROS_GARBAGE_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_budget_frontier.tex"
ROS_CHECKPOINT_MANIFEST = RESULTS / "manifest_ros_lut_checkpoint_optimizer.json"
ROS_CHECKPOINT_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_checkpoint_optimizer.tex"
STG_BENCHMARK_MANIFEST = RESULTS / "manifest_stg_published_benchmark.json"
STG_BENCHMARK_TABLE = THIS_DIR / "paper_latex" / "tables" / "stg_published_benchmark.tex"
TRADITIONAL_STRUCTURE_MANIFEST = RESULTS / "manifest_traditional_structure_mechanism.json"
TRADITIONAL_STRUCTURE_TABLE = THIS_DIR / "paper_latex" / "tables" / "traditional_structure_mechanism.tex"
SEARCH_BUDGET_MANIFEST = RESULTS / "manifest_search_budget_contract.json"
SEARCH_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "search_budget_contract.tex"
SCHEDULE_PROXY_MANIFEST = RESULTS / "manifest_schedule_proxy_audit.json"
SCHEDULE_PROXY_TABLE = THIS_DIR / "paper_latex" / "tables" / "schedule_proxy_audit.tex"
ULTRA_SCALE64_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_stress.json"
ULTRA_SCALE64_TABLE = THIS_DIR / "paper_latex" / "tables" / "screen_scale_ultra_scale64_stress.tex"
ULTRA_SCALE64_PROFILE_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json"
ULTRA_SCALE64_PROFILE_TABLE = THIS_DIR / "paper_latex" / "tables" / "screen_scale_ultra_scale64_resource_profile.tex"
SEARCH_CONTROL_MANIFEST = RESULTS / "manifest_search_control_baseline_audit.json"
LEARNED_CONTROL_MANIFEST = RESULTS / "manifest_learned_control_audit.json"
LEARNED_CONTROL_TABLE = THIS_DIR / "paper_latex" / "tables" / "learned_control_audit.tex"
LIMITED_LEARNED_BOUNDARY_MANIFEST = RESULTS / "manifest_limited_learned_control_boundary.json"
LIMITED_LEARNED_BOUNDARY_TABLE = THIS_DIR / "paper_latex" / "tables" / "limited_learned_control_boundary.tex"
LEARNED_EFFECT_UNCERTAINTY_MANIFEST = RESULTS / "manifest_learned_control_effect_uncertainty.json"
LEARNED_EFFECT_UNCERTAINTY_TABLE = THIS_DIR / "paper_latex" / "tables" / "learned_control_effect_uncertainty.tex"
RUNTIME_ENVELOPE_MANIFEST = RESULTS / "manifest_runtime_envelope_audit.json"
RUNTIME_ENVELOPE_TABLE = THIS_DIR / "paper_latex" / "tables" / "runtime_envelope_audit.tex"
ROOT_ACTION_RANKER_MANIFEST = RESULTS / "manifest_root_action_ranker_audit.json"
ROOT_ACTION_RANKER_TABLE = THIS_DIR / "paper_latex" / "tables" / "root_action_ranker_audit.tex"
PHASE_ROTATION_PRECISION_MANIFEST = RESULTS / "manifest_phase_rotation_precision_audit.json"
PHASE_ROTATION_PRECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_rotation_precision_audit.tex"
PHASE_ROTATION_SEQUENCE_MANIFEST = RESULTS / "manifest_phase_rotation_sequence_smoke_audit.json"
PHASE_ROTATION_SEQUENCE_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_rotation_sequence_smoke_audit.tex"
ROTATION_SYNTHESIS_BACKEND_MANIFEST = RESULTS / "manifest_rotation_synthesis_backend_audit.json"
ROTATION_SYNTHESIS_BACKEND_TABLE = THIS_DIR / "paper_latex" / "tables" / "rotation_synthesis_backend_audit.tex"
PHASE_POLICY_BUDGET_MANIFEST = RESULTS / "manifest_phase_policy_budget_frontier.json"
PHASE_POLICY_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_policy_budget_frontier.tex"
NEURAL_MCTS_CLAIM_MANIFEST = RESULTS / "manifest_neural_mcts_claim_calibration.json"
NEURAL_MCTS_CLAIM_TABLE = THIS_DIR / "paper_latex" / "tables" / "neural_mcts_claim_calibration.tex"
BITFLIP_RANDOM_PRIOR_MANIFEST = RESULTS / "manifest_bitflip_random_prior_control.json"
BITFLIP_RANDOM_PRIOR_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_random_prior_control.tex"
BITFLIP_NEURAL_BUDGET_MANIFEST = RESULTS / "manifest_bitflip_neural_budget_sweep.json"
BITFLIP_NEURAL_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_neural_budget_sweep.tex"
BITFLIP_PRIOR_DIFFICULTY_MANIFEST = RESULTS / "manifest_bitflip_prior_difficulty_slices.json"
BITFLIP_PRIOR_DIFFICULTY_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_prior_difficulty_slices.tex"
BITFLIP_PRIOR_FEATURE_GATE_MANIFEST = RESULTS / "manifest_bitflip_prior_feature_gate.json"
BITFLIP_PRIOR_FEATURE_GATE_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_prior_feature_gate.tex"
BITFLIP_PRIOR_FEATURE_GATE_CV_MANIFEST = RESULTS / "manifest_bitflip_prior_feature_gate_cv.json"
BITFLIP_PRIOR_FEATURE_GATE_CV_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_prior_feature_gate_cv.tex"
BITFLIP_PRIOR_FEATURE_GATE_CV_RANDOM_MANIFEST = (
    RESULTS / "manifest_bitflip_prior_feature_gate_cv_random_control.json"
)
BITFLIP_PRIOR_FEATURE_GATE_CV_RANDOM_TABLE = (
    THIS_DIR / "paper_latex" / "tables" / "bitflip_prior_feature_gate_cv_random_control.tex"
)
FRONTIER_RANDOM_DEPTH_MANIFEST = RESULTS / "manifest_frontier_random_depth_control.json"
FRONTIER_RANDOM_DEPTH_TABLE = THIS_DIR / "paper_latex" / "tables" / "frontier_random_depth_control.tex"
STOCHASTIC_CONTROL_STABILITY_MANIFEST = RESULTS / "manifest_stochastic_control_stability.json"
STOCHASTIC_CONTROL_STABILITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "stochastic_control_stability.tex"
EDITORIAL_SCREENING_MANIFEST = RESULTS / "manifest_editorial_screening_audit.json"
TARGET_VENUE_DECISION_MANIFEST = RESULTS / "manifest_target_venue_decision_audit.json"
TARGET_VENUE_DECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "target_venue_decision_audit.tex"
TARGET_VENUE_POLICY_MANIFEST = RESULTS / "manifest_target_venue_policy_checklist.json"
TARGET_VENUE_POLICY_CHECKLIST = THIS_DIR / "submission_package" / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
TARGET_VENUE_FORMAT_MANIFEST = RESULTS / "manifest_target_venue_format_smoke.json"
TARGET_VENUE_FORMAT_SOURCE = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"
TARGET_VENUE_FORMAT_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.pdf"
SUPPORT_PACKET_MANIFEST = RESULTS / "manifest_submission_support_packet_audit.json"
CITATION_SUPPORT_MANIFEST = RESULTS / "manifest_citation_support_audit.json"
ORACLE_RESOURCE_CITATION_MANIFEST = RESULTS / "manifest_oracle_resource_citation_audit.json"
ORACLE_RESOURCE_CITATION_TABLE = THIS_DIR / "paper_latex" / "tables" / "oracle_resource_citation_audit.tex"
LEARNING_CITATION_MANIFEST = RESULTS / "manifest_learning_citation_verification.json"
LEARNING_CITATION_TABLE = THIS_DIR / "paper_latex" / "tables" / "learning_citation_verification.tex"
HEADLINE_NUMERIC_MANIFEST = RESULTS / "manifest_headline_numeric_consistency.json"
FIGURE_ASSET_MANIFEST = RESULTS / "manifest_figure_asset_audit.json"
LATEX_DEPENDENCY_MANIFEST = RESULTS / "manifest_latex_dependency_audit.json"
PDF_VISUAL_MANIFEST = RESULTS / "manifest_pdf_visual_audit.json"
PDF_TEXT_MANIFEST = RESULTS / "manifest_pdf_text_audit.json"
PDF_METADATA_MANIFEST = RESULTS / "manifest_pdf_metadata_audit.json"
SOURCE_PATH_PRIVACY_MANIFEST = RESULTS / "manifest_source_path_privacy_audit.json"
METADATA_VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
METADATA_PIPELINE_SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
AUTHOR_INPUT_CLOSURE_MANIFEST = RESULTS / "manifest_author_input_closure_audit.json"
AUTHOR_QUESTIONNAIRE_COVERAGE_MANIFEST = RESULTS / "manifest_author_questionnaire_coverage.json"
AUTHOR_MINIMAL_FORM_COVERAGE_MANIFEST = RESULTS / "manifest_author_minimal_form_coverage.json"
METADATA_ANSWER_TEMPLATE_MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"
METADATA_CLOSURE_MANIFEST = RESULTS / "manifest_submission_metadata_closure_path.json"
FINAL_HUMAN_GATE_MANIFEST = RESULTS / "manifest_final_human_gate_audit.json"
FINAL_UPLOAD_SEQUENCE_MANIFEST = RESULTS / "manifest_final_upload_sequence_audit.json"
UPLOAD_BUNDLE_MATRIX_MANIFEST = RESULTS / "manifest_upload_bundle_matrix_audit.json"
FINAL_UPLOAD_PLAN_MANIFEST = RESULTS / "manifest_final_upload_plan.json"
FINAL_UPLOAD_PLAN_TOOL_MANIFEST = RESULTS / "manifest_final_upload_plan_tool_audit.json"
PAYLOAD_ROUNDTRIP_MANIFEST = RESULTS / "manifest_payload_roundtrip_audit.json"
PAYLOAD_GIT_POLICY_MANIFEST = RESULTS / "manifest_payload_git_policy_audit.json"
PAYLOAD_EXTRACTION_SMOKE_MANIFEST = RESULTS / "manifest_payload_extraction_smoke_audit.json"
PAYLOAD_VERIFIER_SMOKE_MANIFEST = RESULTS / "manifest_payload_verifier_smoke_audit.json"
PAYLOAD_LATEX_COMPILE_MANIFEST = RESULTS / "manifest_payload_latex_compile_audit.json"
METADATA_FROM_ANSWERS = THIS_DIR / "make_submission_metadata_from_answers.py"
METADATA_STARTER = THIS_DIR / "make_submission_metadata_starter.py"
METADATA_ANSWERS_FILE = THIS_DIR / "submission_package" / "submission_metadata_answers.json"
METADATA_FILE = THIS_DIR / "submission_package" / "submission_metadata.json"

PRIVATE_PAYLOAD_BASENAMES = {
    "submission_metadata_answers.json",
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
    "generated_upload_plan.md",
}
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


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


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def verify_pdf(path: Path, label: str) -> dict[str, str]:
    pages = pdf_pages(path)
    status = "pass" if pages not in {"missing", "unknown"} else "needs revision"
    return row(
        label,
        status,
        f"{rel(path)} pages={pages}, bytes={path.stat().st_size if path.exists() else 0}.",
        "Rebuild the submission package and inspect latexmk output if the PDF is missing.",
    )


def verify_payload_sha() -> list[dict[str, str]]:
    if EXTRACTED_PAYLOAD_MODE and not PAYLOAD.exists():
        manifest = read_json(PAYLOAD_MANIFEST)
        return [
            row(
                "Payload archive self-check",
                "pass",
                f"extracted_payload_mode=1; archive_absent_by_design={not PAYLOAD.exists()}; manifest_file_count={manifest.get('file_count', 'missing') if manifest else 'missing'}.",
                "Run the full payload SHA and archive round-trip checks from the source worktree before distributing the tarball.",
            )
        ]
    rows: list[dict[str, str]] = []
    if not PAYLOAD.exists() or not PAYLOAD_SHA.exists():
        return [
            row(
                "Payload SHA sidecar",
                "needs revision",
                "Payload archive or SHA256 sidecar is missing.",
                "Run make_submission_payload_archive.py or rebuild_submission_package.sh.",
            )
        ]
    actual = sha256_file(PAYLOAD)
    sidecar = PAYLOAD_SHA.read_text(encoding="utf-8").split()[0]
    rows.append(
        row(
            "Payload SHA sidecar",
            "pass" if actual == sidecar else "needs revision",
            f"actual={actual}; sidecar={sidecar}.",
            "Regenerate the payload archive if the digests differ.",
        )
    )
    summary_rows = read_csv(PAYLOAD_SUMMARY)
    manifest = read_json(PAYLOAD_MANIFEST)
    summary_sha = summary_rows[0].get("sha256", "") if summary_rows else ""
    manifest_sha = str(manifest.get("sha256", ""))
    rows.append(
        row(
            "Payload manifest consistency",
            "pass" if actual == summary_sha == manifest_sha else "needs revision",
            f"summary={summary_sha}; manifest={manifest_sha}; file_count={manifest.get('file_count', 'missing')}.",
            "Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree.",
        )
    )
    return rows


def verify_readiness() -> dict[str, str]:
    if EXTRACTED_PAYLOAD_MODE and not READINESS.exists():
        return row(
            "Readiness audit terminal state",
            "pass",
            "extracted_payload_mode=1; readiness summary is a source-worktree terminal audit and is intentionally excluded from the upload payload.",
            "Run analyze_submission_readiness_audit.py in the source worktree after rebuilding the payload.",
        )
    rows = read_csv(READINESS)
    if not rows:
        return row(
            "Readiness audit terminal state",
            "needs revision",
            "Readiness summary CSV is missing or empty.",
            "Run analyze_submission_readiness_audit.py.",
        )
    full_counts: dict[str, int] = {}
    for item in rows:
        full_counts[item.get("status", "")] = full_counts.get(item.get("status", ""), 0) + 1
    checked_rows = [item for item in rows if item.get("item") != "Terminal package verifier"]
    checked_counts: dict[str, int] = {}
    for item in checked_rows:
        checked_counts[item.get("status", "")] = checked_counts.get(item.get("status", ""), 0) + 1
    only_author_gate = checked_counts.get("needs author input", 0) == 1 and checked_counts.get("needs revision", 0) == 0
    return row(
        "Readiness audit terminal state",
        "pass" if only_author_gate else "needs revision",
        f"full_status_counts={full_counts}; checked_status_counts={checked_counts}; terminal_verifier_self_row_excluded=True.",
        "Resolve any needs-revision rows; author-specific declarations remain manual.",
    )


def verify_submission_archive_manifest() -> dict[str, str]:
    summary_rows = read_csv(ARCHIVE_MANIFEST_SUMMARY)
    manifest = read_json(ARCHIVE_MANIFEST_JSON)
    categories = manifest.get("categories", []) if manifest else []
    table_exists = ARCHIVE_MANIFEST_TABLE.exists()
    summary_categories = [item.get("category", "") for item in summary_rows]
    manifest_categories = [str(item.get("category", "")) for item in categories if isinstance(item, dict)]
    try:
        missing_total = sum(int(item.get("missing", "0") or 0) for item in summary_rows)
    except ValueError:
        missing_total = -1
    consistent = bool(summary_rows) and summary_categories == manifest_categories
    status = "pass" if consistent and missing_total == 0 and table_exists else "needs revision"
    return row(
        "Submission archive manifest freshness",
        status,
        f"summary_categories={len(summary_rows)}; manifest_categories={len(manifest_categories)}; missing_total={missing_total}; table_exists={table_exists}; categories_consistent={consistent}.",
        "Run analyze_submission_archive_manifest.py after changing scripts, public support files, tables, figures, models, or result files.",
    )


def verify_registry() -> dict[str, str]:
    registry_rows = read_csv(REGISTRY_SUMMARY)
    manifest = read_json(REGISTRY_MANIFEST)
    actual_raw_count = len(list(RESULTS.glob("raw_*.csv")))
    complete = bool(registry_rows) and all(item.get("status") == "complete" for item in registry_rows)
    unique_raw_files = int(manifest.get("unique_raw_files", -1)) if manifest else -1
    status = "pass" if complete and unique_raw_files == actual_raw_count else "needs revision"
    return row(
        "Artifact rerun registry coverage",
        status,
        f"families={len(registry_rows)}; registry_raw={unique_raw_files}; actual_raw={actual_raw_count}.",
        "Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts.",
    )


def verify_claim_scope() -> dict[str, str]:
    manifest = read_json(CLAIM_SCOPE_MANIFEST)
    unresolved = int(manifest.get("unresolved_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    status = "pass" if unresolved == 0 else "needs revision"
    return row(
        "Claim-scope lint",
        status,
        f"unresolved_count={unresolved}; status_counts={counts}.",
        "Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims.",
    )


def verify_comparison_protocol() -> dict[str, str]:
    manifest = read_json(COMPARISON_PROTOCOL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    layers = manifest.get("layers", "missing") if manifest else "missing"
    table_exists = COMPARISON_PROTOCOL_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Comparison protocol audit",
        status,
        f"layers={layers}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_comparison_protocol_audit.py and restore missing baseline-role, evidence, comparability, counterpoint, or manuscript anchors.",
    )


def verify_comparison_target_validity() -> dict[str, str]:
    manifest = read_json(COMPARISON_TARGET_VALIDITY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    roles = manifest.get("roles", []) if manifest else []
    table_exists = COMPARISON_TARGET_VALIDITY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and table_exists and anchor else "needs revision"
    return row(
        "Comparison target validity audit",
        status,
        f"rows={rows}; roles={roles}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_comparison_target_validity_audit.py and restore comparison-role labels, evidence gates, and manuscript table anchors.",
    )


def verify_comparison_answer_scorecard() -> dict[str, str]:
    manifest = read_json(COMPARISON_ANSWER_SCORECARD_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    questions = manifest.get("questions", []) if manifest else []
    table_exists = COMPARISON_ANSWER_SCORECARD_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and table_exists and anchor else "needs revision"
    return row(
        "Comparison answer scorecard",
        status,
        f"rows={rows}; questions={questions}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_comparison_answer_scorecard.py and restore comparison-answer rows, generated table, or manuscript anchor.",
    )


def verify_baseline_fairness_ledger() -> dict[str, str]:
    manifest = read_json(BASELINE_FAIRNESS_LEDGER_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    roles = manifest.get("roles", []) if manifest else []
    table_exists = BASELINE_FAIRNESS_LEDGER_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and rows >= 9 and table_exists and anchor else "needs revision"
    return row(
        "Baseline fairness ledger",
        status,
        f"rows={rows}; roles={roles}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_baseline_fairness_ledger.py and restore baseline fairness rows, generated table, or manuscript anchor.",
    )


def verify_comparison_claim_hierarchy() -> dict[str, str]:
    manifest = read_json(COMPARISON_CLAIM_HIERARCHY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    claim_tiers = manifest.get("claim_tiers", []) if manifest else []
    table_exists = COMPARISON_CLAIM_HIERARCHY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and rows >= 7 and table_exists and anchor else "needs revision"
    return row(
        "Comparison claim hierarchy",
        status,
        f"rows={rows}; claim_tiers={claim_tiers}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_comparison_claim_hierarchy.py and restore claim-tier rows, generated table, or manuscript anchors.",
    )


def verify_comparison_route_decision() -> dict[str, str]:
    manifest = read_json(COMPARISON_ROUTE_DECISION_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    routes = manifest.get("routes", []) if manifest else []
    table_exists = COMPARISON_ROUTE_DECISION_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and rows >= 8 and table_exists and anchor else "needs revision"
    return row(
        "Comparison route decision audit",
        status,
        f"rows={rows}; routes={routes}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_comparison_route_decision_audit.py and restore route-decision rows, generated table, or manuscript anchor.",
    )


def verify_benchmark_suite_audit() -> dict[str, str]:
    manifest = read_json(BENCHMARK_SUITE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    raw_rows = int(manifest.get("raw_rows", -1)) if manifest else -1
    verified_rows = int(manifest.get("verified_rows", -1)) if manifest else -1
    scopes = manifest.get("n_scopes", []) if manifest else []
    table_exists = BENCHMARK_SUITE_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 7
        and raw_rows >= 30000
        and verified_rows >= 30000
        and "n=20--64" in scopes
        and "n=21--30" in scopes
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Benchmark suite composition audit",
        status,
        f"rows={rows}; raw_rows={raw_rows}; verified_rows={verified_rows}; scopes={scopes}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_benchmark_suite_audit.py and restore benchmark coverage rows, generated table, or manuscript anchor.",
    )


def verify_benchmark_function_diversity_audit() -> dict[str, str]:
    manifest = read_json(BENCHMARK_FUNCTION_DIVERSITY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    exact_core = int(manifest.get("exact_truth_table_core_items", -1)) if manifest else -1
    scopes = manifest.get("n_scopes", []) if manifest else []
    table_exists = BENCHMARK_FUNCTION_DIVERSITY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 5
        and exact_core >= 177
        and "n=20--64" in scopes
        and "n=21--30" in scopes
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Benchmark function diversity audit",
        status,
        f"rows={rows}; exact_core={exact_core}; scopes={scopes}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_benchmark_function_diversity_audit.py and restore function-diversity rows, generated table, or manuscript anchor.",
    )


def verify_experimental_evidence_ladder() -> dict[str, str]:
    manifest = read_json(EXPERIMENTAL_EVIDENCE_LADDER_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    levels = int(manifest.get("experiment_levels", -1)) if manifest else -1
    verified_rows = int(manifest.get("verified_rows", -1)) if manifest else -1
    scopes = manifest.get("n_scopes", []) if manifest else []
    semantic_bridge = bool(manifest.get("semantic_bridge_present", False)) if manifest else False
    ultra_scale = bool(manifest.get("ultra_scale_present", False)) if manifest else False
    table_exists = EXPERIMENTAL_EVIDENCE_LADDER_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 8
        and levels >= 7
        and verified_rows >= 30000
        and "n=20--64" in scopes
        and "n=21--30" in scopes
        and semantic_bridge
        and ultra_scale
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Experimental evidence ladder",
        status,
        f"rows={rows}; levels={levels}; verified_rows={verified_rows}; scopes={scopes}; semantic_bridge_present={semantic_bridge}; ultra_scale_present={ultra_scale}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_experimental_evidence_ladder.py and restore evidence-ladder rows, generated table, or manuscript anchor.",
    )


def verify_weight_robustness() -> dict[str, str]:
    manifest = read_json(WEIGHT_ROBUSTNESS_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    summary_rows = int(manifest.get("summary_rows", -1)) if manifest else -1
    compact_checks = int(manifest.get("compact_checks", -1)) if manifest else -1
    profile_count = int(manifest.get("profile_count", -1)) if manifest else -1
    min_pairs = int(manifest.get("min_compact_pairs", -1)) if manifest else -1
    profiles = manifest.get("profiles", []) if manifest else []
    table_exists = WEIGHT_ROBUSTNESS_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and summary_rows >= 115
        and compact_checks >= 28
        and profile_count >= 5
        and min_pairs >= 12
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Score-weight robustness audit",
        status,
        f"summary_rows={summary_rows}; compact_checks={compact_checks}; profiles={profiles}; min_compact_pairs={min_pairs}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_weight_robustness.py and restore the post-hoc resource-weight sensitivity table and manifest.",
    )


def verify_resource_weight_sensitivity() -> dict[str, str]:
    manifest = read_json(RESOURCE_WEIGHT_SENSITIVITY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = int(manifest.get("raw_rows", -1)) if manifest else -1
    summary_rows = int(manifest.get("summary_rows", -1)) if manifest else -1
    comparisons = manifest.get("comparisons", []) if manifest else []
    profiles = manifest.get("profiles", []) if manifest else []
    table_exists = RESOURCE_WEIGHT_SENSITIVITY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows >= 12000
        and summary_rows >= 72
        and len(comparisons) >= 12
        and len(profiles) >= 6
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Resource-weight sensitivity audit",
        status,
        f"raw_rows={raw_rows}; summary_rows={summary_rows}; comparisons={len(comparisons)}; profiles={profiles}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_resource_weight_sensitivity_audit.py and restore the internal/external resource-weight sensitivity table and manuscript anchor.",
    )


def verify_cnot_constraint_profile() -> dict[str, str]:
    manifest = read_json(CNOT_CONSTRAINT_PROFILE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = int(manifest.get("raw_rows", -1)) if manifest else -1
    summary_rows = int(manifest.get("summary_rows", -1)) if manifest else -1
    profiles = manifest.get("profiles", []) if manifest else []
    functions = int(manifest.get("functions_cnot_only", -1)) if manifest else -1
    table_exists = CNOT_CONSTRAINT_PROFILE_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    anonymous_anchor = bool(manifest.get("anonymous_table_anchor_present", False)) if manifest else False
    acm_anchor = bool(manifest.get("acm_table_anchor_present", False)) if manifest else False
    winners = manifest.get("winner_counts_cnot_only", {}) if manifest else {}
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows >= 2000
        and summary_rows >= 6
        and "cnot_only" in profiles
        and functions >= 47
        and table_exists
        and anchor
        and anonymous_anchor
        and acm_anchor
        else "needs revision"
    )
    return row(
        "CNOT constraint profile audit",
        status,
        f"raw_rows={raw_rows}; summary_rows={summary_rows}; profiles={profiles}; functions_cnot_only={functions}; cnot_winner_counts={winners}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}; anonymous_anchor={anonymous_anchor}; acm_anchor={acm_anchor}.",
        "Run analyze_cnot_constraint_profile_audit.py after the CNOT-only resource sweep and restore the manuscript table anchors.",
    )


def verify_sshr_reproduction_scope() -> dict[str, str]:
    manifest = read_json(SSHR_REPRODUCTION_MANIFEST)
    table8_manifest = read_json(SSHR_TABLE8_MANIFEST)
    crosswalk_manifest = read_json(SSHR_CROSSWALK_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    coverage = manifest.get("coverage_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    source_tree = manifest.get("source_tree_available", "missing") if manifest else "missing"
    table8_rows = int(table8_manifest.get("rows", -1)) if table8_manifest else -1
    table8_match = bool(table8_manifest.get("all_match", False)) if table8_manifest else False
    table8_max_n = int(table8_manifest.get("max_n", -1)) if table8_manifest else -1
    table8_max_count = int(table8_manifest.get("max_sshr_count", -1)) if table8_manifest else -1
    crosswalk_rows = int(crosswalk_manifest.get("rows", -1)) if crosswalk_manifest else -1
    crosswalk_revisions = int(crosswalk_manifest.get("needs_revision_count", -1)) if crosswalk_manifest else -1
    crosswalk_counts = crosswalk_manifest.get("status_counts", {}) if crosswalk_manifest else {}
    crosswalk_coverage = crosswalk_manifest.get("coverage_counts", {}) if crosswalk_manifest else {}
    table_exists = SSHR_REPRODUCTION_TABLE.exists()
    table8_exists = SSHR_TABLE8_TABLE.exists()
    crosswalk_table_exists = SSHR_CROSSWALK_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    anonymous_anchor = bool(manifest.get("anonymous_table_anchor_present", False)) if manifest else False
    acm_anchor = bool(manifest.get("acm_table_anchor_present", False)) if manifest else False
    crosswalk_anchor = bool(crosswalk_manifest.get("table_anchor_present", False)) if crosswalk_manifest else False
    crosswalk_anonymous_anchor = (
        bool(crosswalk_manifest.get("anonymous_table_anchor_present", False)) if crosswalk_manifest else False
    )
    crosswalk_acm_anchor = bool(crosswalk_manifest.get("acm_table_anchor_present", False)) if crosswalk_manifest else False
    status = (
        "pass"
        if manifest
        and table8_manifest
        and crosswalk_manifest
        and revisions == 0
        and rows >= 8
        and SSHR_TABLE8_RAW.exists()
        and table8_rows == 6
        and table8_match
        and table8_max_n == 8
        and table8_max_count == 609441
        and SSHR_CROSSWALK_SUMMARY.exists()
        and SSHR_CROSSWALK_ANALYSIS.exists()
        and crosswalk_rows == 5
        and crosswalk_revisions == 0
        and table_exists
        and table8_exists
        and crosswalk_table_exists
        and anchor
        and anonymous_anchor
        and acm_anchor
        and crosswalk_anchor
        and crosswalk_anonymous_anchor
        and crosswalk_acm_anchor
        else "needs revision"
    )
    return row(
        "SSHR reproduction-scope audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; coverage_counts={coverage}; source_tree_available={source_tree}; table8_rows={table8_rows}; table8_all_match={table8_match}; table8_max_n={table8_max_n}; table8_max_count={table8_max_count}; crosswalk_rows={crosswalk_rows}; crosswalk_needs_revision_count={crosswalk_revisions}; crosswalk_status_counts={crosswalk_counts}; crosswalk_coverage_counts={crosswalk_coverage}; table_exists={table_exists}; table8_table_exists={table8_exists}; crosswalk_table_exists={crosswalk_table_exists}; table_anchor_present={anchor}; anonymous_anchor={anonymous_anchor}; acm_anchor={acm_anchor}; crosswalk_anchor={crosswalk_anchor}; crosswalk_anonymous_anchor={crosswalk_anonymous_anchor}; crosswalk_acm_anchor={crosswalk_acm_anchor}.",
        "Rerun reproduce_sshr_table8_candidate_counts.py and analyze_sshr_reproduction_scope_audit.py; restore SSHR reproduction rows, generated tables, or manuscript anchors.",
    )


def verify_threats_to_validity() -> dict[str, str]:
    manifest = read_json(THREATS_VALIDITY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    threats = manifest.get("threats", []) if manifest else []
    table_exists = THREATS_VALIDITY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and table_exists and anchor else "needs revision"
    return row(
        "Threats-to-validity audit",
        status,
        f"rows={rows}; threats={threats}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_threats_to_validity_audit.py and restore validity-threat rows, generated table, or manuscript anchor.",
    )


def verify_novelty_scorecard() -> dict[str, str]:
    manifest = read_json(NOVELTY_SCORECARD_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = NOVELTY_SCORECARD_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Novelty/comparison scorecard",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_novelty_comparison_scorecard.py and restore missing novelty/comparison artifacts, manuscript anchors, or reviewer/editor brief anchors.",
    )


def verify_public_handoff_freshness() -> dict[str, str]:
    manifest = read_json(PUBLIC_HANDOFF_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    snapshot = manifest.get("snapshot", {}) if manifest else {}
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Public handoff freshness audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; snapshot={snapshot}.",
        "Run analyze_public_handoff_freshness_audit.py and refresh public current-snapshot tokens in DELIVERABLE_zh.md, FINAL_SUBMISSION_HANDOFF_zh.md, or submission_checklist.md.",
    )


def verify_ros_gap() -> dict[str, str]:
    manifest = read_json(ROS_GAP_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    coverage = manifest.get("coverage_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    boundary_explicit = bool(manifest.get("full_ros_boundary_is_explicit", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and full_ros is False and boundary_explicit else "needs revision"
    return row(
        "ROS reproduction gap audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; coverage_counts={coverage}; official_ros_fully_reproduced={full_ros}; full_ros_boundary_is_explicit={boundary_explicit}.",
        "Run analyze_ros_lut_line_sensitivity.py and analyze_ros_reproduction_gap_audit.py and restore ROS proxy/full-reproduction boundary anchors.",
    )


def verify_caterpillar_probe() -> dict[str, str]:
    manifest = read_json(CATERPILLAR_PROBE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    coverage = manifest.get("coverage_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    source_tree = bool(manifest.get("source_tree_available", False)) if manifest else False
    compile_smoke = bool(manifest.get("compile_smoke_passed", False)) if manifest else False
    standalone_cli = bool(manifest.get("standalone_cli_detected", True)) if manifest else True
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    performance_baseline = bool(manifest.get("caterpillar_is_performance_baseline", True)) if manifest else True
    table_exists = CATERPILLAR_PROBE_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows == 8
        and source_tree
        and compile_smoke
        and not standalone_cli
        and full_ros is False
        and not performance_baseline
        and table_exists
        else "needs revision"
    )
    return row(
        "Caterpillar ROS-family source probe",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; coverage_counts={coverage}; source_tree_available={source_tree}; compile_smoke_passed={compile_smoke}; standalone_cli_detected={standalone_cli}; official_ros_fully_reproduced={full_ros}; caterpillar_is_performance_baseline={performance_baseline}; table_exists={table_exists}.",
        "Run analyze_caterpillar_ros_family_probe.py from the source worktree and keep Caterpillar framed as source/API/build smoke evidence, not a full ROS or standalone performance baseline.",
    )


def verify_caterpillar_api_probe() -> dict[str, str]:
    manifest = read_json(CATERPILLAR_API_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    best_rows = manifest.get("best_raw_rows", "missing") if manifest else "missing"
    correct_rows = manifest.get("correct_rows", "missing") if manifest else "missing"
    summary_rows = manifest.get("summary_rows", "missing") if manifest else "missing"
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    performance = bool(manifest.get("caterpillar_is_performance_baseline", False)) if manifest else False
    score_wlt = manifest.get("score_wlt_vs_pareto", "missing") if manifest else "missing"
    cnot_wlt = manifest.get("pareto_cnot_wlt_vs_caterpillar", "missing") if manifest else "missing"
    raw_exists = CATERPILLAR_API_RAW.exists()
    best_exists = CATERPILLAR_API_BEST.exists()
    table_exists = CATERPILLAR_API_TABLE.exists()
    paper_text = read_text(AUTHOR_TEX) + "\n" + read_text(ANON_TEX) + "\n" + read_text(ACM_TEX)
    anchor = "tab:caterpillar-xag-api" in paper_text
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 531
        and best_rows == 177
        and correct_rows == 531
        and summary_rows == 4
        and full_ros is False
        and performance
        and raw_exists
        and best_exists
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Caterpillar XAG API performance probe",
        status,
        f"raw_rows={raw_rows}; best_raw_rows={best_rows}; correct_rows={correct_rows}; summary_rows={summary_rows}; needs_revision_count={revisions}; official_ros_fully_reproduced={full_ros}; caterpillar_is_performance_baseline={performance}; score_wlt_vs_pareto={score_wlt}; pareto_cnot_wlt_vs_caterpillar={cnot_wlt}; raw_exists={raw_exists}; best_exists={best_exists}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run run_caterpillar_xag_api_probe.py in the source worktree and keep the table framed as a bounded ANF-XAG API counterpoint, not full ROS.",
    )


def verify_ros_garbage_proxy() -> dict[str, str]:
    manifest = read_json(ROS_GARBAGE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    summary_rows = manifest.get("summary_rows", "missing") if manifest else "missing"
    functions = manifest.get("functions", "missing") if manifest else "missing"
    policies = manifest.get("policies", []) if manifest else []
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    table_exists = ROS_GARBAGE_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 927
        and summary_rows == 3
        and functions == 309
        and full_ros is False
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "ROS-style LUT garbage proxy",
        status,
        f"raw_rows={raw_rows}; summary_rows={summary_rows}; functions={functions}; policies={policies}; needs_revision_count={revisions}; status_counts={counts}; official_ros_fully_reproduced={full_ros}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_ros_lut_garbage_proxy.py and keep the table anchored in the external baseline section.",
    )


def verify_ros_garbage_budget_frontier() -> dict[str, str]:
    manifest = read_json(ROS_GARBAGE_BUDGET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    summary_rows = manifest.get("summary_rows", "missing") if manifest else "missing"
    frontier_rows = manifest.get("frontier_rows", "missing") if manifest else "missing"
    functions = manifest.get("functions", "missing") if manifest else "missing"
    budgets = manifest.get("budgets", []) if manifest else []
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    table_exists = ROS_GARBAGE_BUDGET_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 1059
        and summary_rows == 35
        and frontier_rows == 5
        and functions == 309
        and full_ros is False
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "ROS-style LUT garbage budget frontier",
        status,
        f"raw_rows={raw_rows}; summary_rows={summary_rows}; frontier_rows={frontier_rows}; functions={functions}; budgets={budgets}; needs_revision_count={revisions}; status_counts={counts}; official_ros_fully_reproduced={full_ros}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_ros_lut_garbage_budget_frontier.py after changing ROS-style LUT garbage schedules, budget-frontier wording, or table anchors.",
    )


def verify_ros_checkpoint_optimizer() -> dict[str, str]:
    manifest = read_json(ROS_CHECKPOINT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    summary_rows = manifest.get("summary_rows", "missing") if manifest else "missing"
    frontier_rows = manifest.get("frontier_rows", "missing") if manifest else "missing"
    solved = manifest.get("solved_functions", "missing") if manifest else "missing"
    solved_traditional = manifest.get("solved_traditional_n_le_6", "missing") if manifest else "missing"
    exact = bool(manifest.get("exact_over_checkpoint_candidates", False)) if manifest else False
    full_ros = manifest.get("official_ros_fully_reproduced", "missing") if manifest else "missing"
    table_exists = ROS_CHECKPOINT_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 474
        and summary_rows == 35
        and frontier_rows == 5
        and solved == 192
        and solved_traditional == 177
        and exact
        and full_ros is False
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "ROS-style exact checkpoint-subset optimizer",
        status,
        f"raw_rows={raw_rows}; summary_rows={summary_rows}; frontier_rows={frontier_rows}; solved_functions={solved}; solved_traditional_n_le_6={solved_traditional}; exact_over_checkpoint_candidates={exact}; needs_revision_count={revisions}; status_counts={counts}; official_ros_fully_reproduced={full_ros}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_ros_lut_checkpoint_optimizer.py after changing ROS-style LUT checkpoint optimization, exact-scope wording, or table anchors.",
    )


def verify_stg_benchmark() -> dict[str, str]:
    manifest = read_json(STG_BENCHMARK_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    benchmark_rows = manifest.get("benchmark_rows", "missing") if manifest else "missing"
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    usable_rows = manifest.get("usable_rows", "missing") if manifest else "missing"
    table_exists = STG_BENCHMARK_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and benchmark_rows == 54
        and raw_rows == 270
        and usable_rows == 270
        and table_exists
        else "needs revision"
    )
    return row(
        "Published STG counterpoint",
        status,
        f"benchmark_rows={benchmark_rows}; raw_rows={raw_rows}; usable_rows={usable_rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_stg_published_benchmark.py and restore the STG counterpoint raw rows, manifest, and manuscript table.",
    )


def verify_traditional_structure_mechanism() -> dict[str, str]:
    manifest = read_json(TRADITIONAL_STRUCTURE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    functions = manifest.get("functions", "missing") if manifest else "missing"
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    summary_rows = manifest.get("summary_rows", "missing") if manifest else "missing"
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    table_exists = TRADITIONAL_STRUCTURE_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and functions == 177
        and raw_rows == 177
        and summary_rows == 11
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Traditional structure mechanism audit",
        status,
        f"functions={functions}; raw_rows={raw_rows}; summary_rows={summary_rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_traditional_structure_mechanism.py and restore the manuscript table anchor if structure-mechanism evidence changes.",
    )


def verify_schedule_proxy() -> dict[str, str]:
    manifest = read_json(SCHEDULE_PROXY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = SCHEDULE_PROXY_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Schedule-proxy tradeoff audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_schedule_metrics.py and analyze_schedule_proxy_audit.py and restore schedule-proxy table anchors.",
    )


def verify_ultra_scale64() -> dict[str, str]:
    manifest = read_json(ULTRA_SCALE64_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    plan_rows = manifest.get("plan_verified_rows", "missing") if manifest else "missing"
    circuit_rows = manifest.get("circuit_verified_rows", "missing") if manifest else "missing"
    mismatch = manifest.get("max_circuit_mismatches", "missing") if manifest else "missing"
    n_values = manifest.get("n_values", []) if manifest else []
    table_exists = ULTRA_SCALE64_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 480
        and plan_rows == 480
        and circuit_rows == 480
        and mismatch == 0
        and table_exists
        else "needs revision"
    )
    return row(
        "Ultra-scale n=48--64 stress audit",
        status,
        f"raw_rows={raw_rows}; plan_verified={plan_rows}; circuit_verified={circuit_rows}; max_circuit_mismatches={mismatch}; n_values={n_values}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_ultra_scale64_stress.py and restore the n=48--64 stress manifest and manuscript table.",
    )


def verify_ultra_scale64_resource_profile() -> dict[str, str]:
    manifest = read_json(ULTRA_SCALE64_PROFILE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    raw_rows = manifest.get("raw_rows", "missing") if manifest else "missing"
    plan_rows = manifest.get("plan_verified_rows", "missing") if manifest else "missing"
    circuit_rows = manifest.get("circuit_verified_rows", "missing") if manifest else "missing"
    plan_mismatch = manifest.get("max_plan_mismatches", "missing") if manifest else "missing"
    circuit_mismatch = manifest.get("max_circuit_mismatches", "missing") if manifest else "missing"
    profile_rows = manifest.get("profile_rows", "missing") if manifest else "missing"
    delta_rows = manifest.get("delta_rows", "missing") if manifest else "missing"
    table_exists = ULTRA_SCALE64_PROFILE_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and raw_rows == 480
        and plan_rows == 480
        and circuit_rows == 480
        and plan_mismatch == 0
        and circuit_mismatch == 0
        and profile_rows == 20
        and delta_rows == 12
        and table_exists
        else "needs revision"
    )
    return row(
        "Ultra-scale n=48--64 resource profile",
        status,
        f"raw_rows={raw_rows}; plan_verified={plan_rows}; circuit_verified={circuit_rows}; max_plan_mismatches={plan_mismatch}; max_circuit_mismatches={circuit_mismatch}; profile_rows={profile_rows}; delta_rows={delta_rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_ultra_scale64_resource_profile.py and restore the n=48--64 resource-profile manifest and manuscript table.",
    )


def verify_search_budget_contract() -> dict[str, str]:
    manifest = read_json(SEARCH_BUDGET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = SEARCH_BUDGET_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Search-budget contract audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_search_budget_contract.py and restore method search-budget table anchors.",
    )


def verify_search_control() -> dict[str, str]:
    manifest = read_json(SEARCH_CONTROL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Search-control baseline audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_search_control_baseline_audit.py and restore heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, bit-flip random-prior, frontier random-depth, and phase random-control evidence rows.",
    )


def verify_learned_control() -> dict[str, str]:
    manifest = read_json(LEARNED_CONTROL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    class_counts = manifest.get("claim_class_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    promoted = int(manifest.get("promoted_count", -1)) if manifest else -1
    bounded = int(manifest.get("bounded_count", -1)) if manifest else -1
    limited = int(manifest.get("limited_count", -1)) if manifest else -1
    table_exists = LEARNED_CONTROL_TABLE.exists()
    status = (
        "pass"
        if manifest and revisions == 0 and isinstance(rows, int) and rows >= 9 and promoted >= 4 and bounded >= 2 and limited >= 2 and table_exists
        else "needs revision"
    )
    return row(
        "Learned-control audit",
        status,
        f"rows={rows}; promoted_count={promoted}; bounded_count={bounded}; limited_count={limited}; needs_revision_count={revisions}; status_counts={counts}; claim_class_counts={class_counts}; table_exists={table_exists}.",
        "Run analyze_learned_control_audit.py and restore promoted/bounded/limited learned-control classifications and the manuscript table.",
    )


def verify_limited_learned_boundary() -> dict[str, str]:
    manifest = read_json(LIMITED_LEARNED_BOUNDARY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    limited_count = int(manifest.get("limited_boundary_count", -1)) if manifest else -1
    table_exists = LIMITED_LEARNED_BOUNDARY_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and isinstance(rows, int)
        and rows >= 6
        and limited_count == 2
        and table_exists
        else "needs revision"
    )
    return row(
        "Limited learned-control boundary",
        status,
        f"rows={rows}; limited_boundary_count={limited_count}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_limited_learned_control_boundary.py and keep runtime-negative learned diagnostics bounded rather than promoted.",
    )


def verify_learned_effect_uncertainty() -> dict[str, str]:
    manifest = read_json(LEARNED_EFFECT_UNCERTAINTY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    class_counts = manifest.get("claim_class_counts", {}) if manifest else {}
    rows = int(manifest.get("rows", -1)) if manifest else -1
    table_exists = LEARNED_EFFECT_UNCERTAINTY_TABLE.exists()
    paper_text = read_text(AUTHOR_TEX) + "\n" + read_text(ANON_TEX) + "\n" + read_text(ACM_TEX)
    anchor = "tab:learned-control-effect-uncertainty" in paper_text
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 8
        and class_counts.get("promoted", 0) >= 4
        and class_counts.get("bounded", 0) >= 2
        and class_counts.get("limited", 0) >= 2
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Learned-control effect uncertainty",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; claim_class_counts={class_counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_learned_control_effect_uncertainty.py and restore bootstrap intervals, class counts, generated table, or manuscript anchor.",
    )


def verify_root_action_ranker() -> dict[str, str]:
    manifest = read_json(ROOT_ACTION_RANKER_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    pairs = int(manifest.get("combined_pairs", -1)) if manifest else -1
    score_wlt = manifest.get("combined_score_wlt", "missing") if manifest else "missing"
    table_exists = ROOT_ACTION_RANKER_TABLE.exists()
    status = (
        "pass"
        if manifest and revisions == 0 and rows >= 5 and pairs >= 30 and score_wlt == "8/0/25" and table_exists
        else "needs revision"
    )
    return row(
        "Root-action ranker audit",
        status,
        f"rows={rows}; combined_pairs={pairs}; combined_score_wlt={score_wlt}; needs_revision_count={revisions}; table_exists={table_exists}.",
        "Run analyze_root_action_ranker_audit.py and restore the bounded root-action candidate-extension evidence.",
    )


def verify_phase_policy_budget_frontier() -> dict[str, str]:
    manifest = read_json(PHASE_POLICY_BUDGET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    heldout = int(manifest.get("heldout_functions", -1)) if manifest else -1
    best = manifest.get("best_policy", "missing") if manifest else "missing"
    budget_wlt = manifest.get("best_budget32_wlt", "missing") if manifest else "missing"
    eval_cut = float(manifest.get("best_eval_reduction_vs_wide128_pct", -1.0)) if manifest else -1.0
    wide_rel = float(manifest.get("best_mean_relative_vs_wide128", 1.0)) if manifest else 1.0
    table_exists = PHASE_POLICY_BUDGET_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 8
        and heldout >= 38
        and best == "diverse_top512"
        and budget_wlt == "17/0/21"
        and eval_cut >= 90.0
        and wide_rel <= 0.001
        and table_exists
        else "needs revision"
    )
    return row(
        "Phase policy budget-frontier audit",
        status,
        f"rows={rows}; heldout_functions={heldout}; best_policy={best}; best_budget32_wlt={budget_wlt}; eval_reduction_vs_wide128_pct={eval_cut:.2f}; mean_relative_vs_wide128={wide_rel:.6g}; needs_revision_count={revisions}; table_exists={table_exists}.",
        "Run analyze_phase_policy_budget_frontier.py and restore the learned phase budget-frontier table.",
    )


def verify_phase_rotation_precision() -> dict[str, str]:
    manifest = read_json(PHASE_ROTATION_PRECISION_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    traditional = int(manifest.get("traditional_items", -1)) if manifest else -1
    policy = int(manifest.get("policy_items", -1)) if manifest else -1
    critical_wlt = manifest.get("critical_policy_wide128_wlt", "missing") if manifest else "missing"
    critical_rel = float(manifest.get("critical_policy_wide128_mean_relative", 1.0)) if manifest else 1.0
    epsilons = manifest.get("epsilons", []) if manifest else []
    table_exists = PHASE_ROTATION_PRECISION_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 28
        and traditional == 177
        and policy == 38
        and critical_wlt == "0/7/31"
        and critical_rel <= 0.0001
        and set(epsilons) >= {"0.001", "1e-06", "1e-09", "1e-12"}
        and table_exists
        else "needs revision"
    )
    return row(
        "Phase rotation-precision audit",
        status,
        f"rows={rows}; traditional_items={traditional}; policy_items={policy}; epsilons={epsilons}; critical_wide128_wlt={critical_wlt}; critical_wide128_mean_relative={critical_rel:.6g}; needs_revision_count={revisions}; table_exists={table_exists}.",
        "Run analyze_phase_rotation_precision_audit.py and restore the precision-sensitive phase/Rz cost table.",
    )


def verify_phase_rotation_sequence_smoke() -> dict[str, str]:
    manifest = read_json(PHASE_ROTATION_SEQUENCE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    smoke_pass = int(manifest.get("smoke_pass_count", -1)) if manifest else -1
    tight_pass = int(manifest.get("tight_pass_count", -1)) if manifest else -1
    max_error = float(manifest.get("max_achieved_error", 1.0)) if manifest else 1.0
    denominators = set(manifest.get("target_denominators", [])) if manifest else set()
    backend = manifest.get("backend", "missing") if manifest else "missing"
    allowed_backend = "packaged_raw_sequence_verification" if EXTRACTED_PAYLOAD_MODE else "internal_matrix_beam"
    table_exists = PHASE_ROTATION_SEQUENCE_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 20
        and smoke_pass >= 20
        and tight_pass >= 5
        and max_error <= 0.125
        and denominators >= {8, 16, 32}
        and backend == allowed_backend
        and table_exists
        else "needs revision"
    )
    return row(
        "Phase rotation-sequence smoke audit",
        status,
        f"rows={rows}; smoke_pass_count={smoke_pass}; tight_pass_count={tight_pass}; max_achieved_error={max_error:.6g}; target_denominators={sorted(denominators)}; backend={backend}; needs_revision_count={revisions}; table_exists={table_exists}.",
        "Run analyze_phase_rotation_sequence_smoke_audit.py and restore the source-derived Clifford+T sequence smoke table.",
    )


def verify_rotation_synthesis_backend() -> dict[str, str]:
    manifest = read_json(ROTATION_SYNTHESIS_BACKEND_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    high_precision = bool(manifest.get("high_precision_backend_available", True)) if manifest else True
    commands = manifest.get("command_backends", {}) if manifest else {}
    modules = manifest.get("python_backends", {}) if manifest else {}
    table_exists = ROTATION_SYNTHESIS_BACKEND_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 4
        and high_precision is False
        and {"gridsynth", "newsynth", "pgridsynth"} <= set(commands)
        and {"pyzx", "qiskit", "cirq"} <= set(modules)
        and table_exists
        else "needs revision"
    )
    return row(
        "Rotation-synthesis backend audit",
        status,
        f"rows={rows}; high_precision_backend_available={high_precision}; command_backends={commands}; python_backends={modules}; needs_revision_count={revisions}; table_exists={table_exists}.",
        "Run analyze_rotation_synthesis_backend_audit.py and keep the phase/Rz backend boundary explicit.",
    )


def verify_neural_mcts_claim_calibration() -> dict[str, str]:
    manifest = read_json(NEURAL_MCTS_CLAIM_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    anchors = manifest.get("claim_anchors", []) if manifest else []
    table_exists = NEURAL_MCTS_CLAIM_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = "pass" if manifest and revisions == 0 and rows == 7 and table_exists and anchor else "needs revision"
    return row(
        "Neural/MCTS claim calibration",
        status,
        f"rows={rows}; claim_anchors={anchors}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_neural_mcts_claim_calibration.py and restore title-level claim anchors, generated table, or manuscript anchor.",
    )


def verify_runtime_envelope() -> dict[str, str]:
    manifest = read_json(RUNTIME_ENVELOPE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = RUNTIME_ENVELOPE_TABLE.exists()
    anchors = {
        "author": bool(manifest.get("table_anchor_present")) if manifest else False,
        "anonymous": bool(manifest.get("anonymous_table_anchor_present")) if manifest else False,
        "acm": bool(manifest.get("acm_table_anchor_present")) if manifest else False,
    }
    status = "pass" if manifest and revisions == 0 and rows == 5 and table_exists and all(anchors.values()) else "needs revision"
    return row(
        "Runtime-envelope audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}; anchors={anchors}.",
        "Run analyze_runtime_envelope_audit.py after author/anonymous/ACM sources are generated and restore runtime-envelope table anchors.",
    )


def verify_bitflip_random_prior() -> dict[str, str]:
    manifest = read_json(BITFLIP_RANDOM_PRIOR_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = BITFLIP_RANDOM_PRIOR_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Bit-flip random-prior control",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_bitflip_random_prior_control.py and restore the bit-flip random-prior manuscript table.",
    )


def verify_bitflip_neural_budget() -> dict[str, str]:
    manifest = read_json(BITFLIP_NEURAL_BUDGET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    paired_rows = int(manifest.get("paired_rows", -1)) if manifest else -1
    raw_rows = int(manifest.get("raw_rows", -1)) if manifest else -1
    low_budget_rows = int(manifest.get("low_budget_score_rows", -1)) if manifest else -1
    positive_rows = int(manifest.get("positive_low_budget_score_rows", -1)) if manifest else -1
    table_exists = BITFLIP_NEURAL_BUDGET_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and paired_rows >= 54
        and raw_rows >= 2124
        and low_budget_rows == 6
        and positive_rows == 6
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Bit-flip low-budget learned-prior sweep",
        status,
        f"paired_rows={paired_rows}; raw_rows={raw_rows}; low_budget_score_rows={low_budget_rows}; positive_low_budget_score_rows={positive_rows}; needs_revision_count={revisions}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_bitflip_neural_budget_sweep.py and restore the low-budget learned-prior table and manuscript anchor.",
    )


def verify_bitflip_prior_difficulty() -> dict[str, str]:
    manifest = read_json(BITFLIP_PRIOR_DIFFICULTY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = int(manifest.get("rows", -1)) if manifest else -1
    aggregate_rows = int(manifest.get("aggregate_rows", -1)) if manifest else -1
    losses = int(manifest.get("aggregate_score_losses", -1)) if manifest else -1
    middle_best = int(manifest.get("middle_best_budget_count", -1)) if manifest else -1
    table_exists = BITFLIP_PRIOR_DIFFICULTY_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows >= 36
        and aggregate_rows == 9
        and losses == 0
        and middle_best == 3
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Bit-flip learned-prior difficulty slices",
        status,
        f"rows={rows}; aggregate_rows={aggregate_rows}; aggregate_score_losses={losses}; middle_best_budget_count={middle_best}; needs_revision_count={revisions}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_bitflip_prior_difficulty_slices.py and restore the difficulty-sliced learned-prior table and manuscript anchor.",
    )


def verify_bitflip_prior_feature_gate() -> dict[str, str]:
    manifest = read_json(BITFLIP_PRIOR_FEATURE_GATE_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    pairs = int(manifest.get("aggregate_pairs", -1)) if manifest else -1
    enabled = int(manifest.get("aggregate_gate_enabled", -1)) if manifest else -1
    wins = int(manifest.get("aggregate_score_wins", -1)) if manifest else -1
    losses = int(manifest.get("aggregate_score_losses", -1)) if manifest else -1
    learned_wins = int(manifest.get("aggregate_learned_score_wins", -1)) if manifest else -1
    retained = bool(manifest.get("aggregate_retained_learned_wins", False)) if manifest else False
    overhead_cut = float(manifest.get("aggregate_learned_overhead_reduction", -1.0)) if manifest else -1.0
    table_exists = BITFLIP_PRIOR_FEATURE_GATE_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and pairs >= 1500
        and enabled >= 1000
        and wins == learned_wins
        and losses == 0
        and retained
        and overhead_cut > 0.1
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Bit-flip learned-prior feature gate",
        status,
        f"pairs={pairs}; gate_enabled={enabled}; score_wins={wins}; learned_score_wins={learned_wins}; score_losses={losses}; retained_learned_wins={retained}; learned_overhead_reduction={overhead_cut:.4f}; needs_revision_count={revisions}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_bitflip_prior_feature_gate.py and restore the feature-gated learned-prior table and manuscript anchor.",
    )


def verify_bitflip_prior_feature_gate_cv() -> dict[str, str]:
    manifest = read_json(BITFLIP_PRIOR_FEATURE_GATE_CV_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    pairs = int(manifest.get("aggregate_pairs", -1)) if manifest else -1
    enabled = int(manifest.get("aggregate_gate_enabled", -1)) if manifest else -1
    wins = int(manifest.get("aggregate_score_wins", -1)) if manifest else -1
    losses = int(manifest.get("aggregate_score_losses", -1)) if manifest else -1
    learned_wins = int(manifest.get("aggregate_learned_score_wins", -1)) if manifest else -1
    retained = bool(manifest.get("aggregate_retained_learned_wins", False)) if manifest else False
    retained_fraction = (
        float(manifest.get("aggregate_retained_learned_win_fraction", -1.0)) if manifest else -1.0
    )
    overhead_cut = float(manifest.get("aggregate_learned_overhead_reduction", -1.0)) if manifest else -1.0
    folds = int(manifest.get("folds", -1)) if manifest else -1
    table_exists = BITFLIP_PRIOR_FEATURE_GATE_CV_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and folds == 5
        and pairs >= 1500
        and enabled >= 1200
        and wins == learned_wins
        and losses == 0
        and retained
        and retained_fraction >= 0.999
        and overhead_cut > 0.05
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Bit-flip learned-prior cross-validated feature gate",
        status,
        f"folds={folds}; heldout_pairs={pairs}; gate_enabled={enabled}; score_wins={wins}; learned_score_wins={learned_wins}; score_losses={losses}; retained_learned_wins={retained}; retained_fraction={retained_fraction:.4f}; learned_overhead_reduction={overhead_cut:.4f}; needs_revision_count={revisions}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_bitflip_prior_feature_gate_cv.py and restore the cross-validated feature-gate table and manuscript anchor.",
    )


def verify_bitflip_prior_feature_gate_cv_random_control() -> dict[str, str]:
    manifest = read_json(BITFLIP_PRIOR_FEATURE_GATE_CV_RANDOM_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    repeats = int(manifest.get("random_repeats", -1)) if manifest else -1
    learned_wins = int(manifest.get("learned_score_wins", -1)) if manifest else -1
    learned_losses = int(manifest.get("learned_score_losses", -1)) if manifest else -1
    random_full = int(manifest.get("random_full_retained_count", -1)) if manifest else -1
    random_best = int(manifest.get("random_best_retained_wins", -1)) if manifest else -1
    learned_beats = bool(manifest.get("learned_beats_all_random_retention", False)) if manifest else False
    random_mean_retained = float(manifest.get("random_mean_retained_fraction", -1.0)) if manifest else -1.0
    table_exists = BITFLIP_PRIOR_FEATURE_GATE_CV_RANDOM_TABLE.exists()
    anchor = bool(manifest.get("table_anchor_present", False)) if manifest else False
    status = (
        "pass"
        if manifest
        and revisions == 0
        and repeats >= 200
        and learned_wins == 328
        and learned_losses == 0
        and random_full == 0
        and random_best < learned_wins
        and learned_beats
        and 0.0 < random_mean_retained < 0.9
        and table_exists
        and anchor
        else "needs revision"
    )
    return row(
        "Bit-flip learned-prior CV gate random-interval control",
        status,
        f"random_repeats={repeats}; learned_score_wins={learned_wins}; learned_score_losses={learned_losses}; random_full_retained_count={random_full}; random_best_retained_wins={random_best}; random_mean_retained_fraction={random_mean_retained:.4f}; learned_beats_all_random_retention={learned_beats}; needs_revision_count={revisions}; table_exists={table_exists}; table_anchor_present={anchor}.",
        "Run analyze_bitflip_prior_feature_gate_cv_random_control.py and restore the random-interval control table and manuscript anchor.",
    )


def verify_frontier_random_depth() -> dict[str, str]:
    manifest = read_json(FRONTIER_RANDOM_DEPTH_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    table_exists = FRONTIER_RANDOM_DEPTH_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Frontier random-depth control",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_frontier_random_depth_control.py and restore the frontier random-depth manuscript table.",
    )


def verify_stochastic_control_stability() -> dict[str, str]:
    manifest = read_json(STOCHASTIC_CONTROL_STABILITY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    components = manifest.get("components", []) if manifest else []
    table_exists = STOCHASTIC_CONTROL_STABILITY_TABLE.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows == 6
        and table_exists
        and counts.get("pass", 0) == 6
        else "needs revision"
    )
    return row(
        "Stochastic-control stability audit",
        status,
        f"rows={rows}; components={components}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_stochastic_control_stability.py and restore the stochastic learned-control stability table.",
    )


def verify_editorial_screening() -> dict[str, str]:
    manifest = read_json(EDITORIAL_SCREENING_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Editorial screening audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_editorial_screening_audit.py and restore scope, novelty, comparison, counterpoint, AI-boundary, scale-boundary, reproducibility, author-gate, or editor-reading anchors.",
    )


def verify_target_venue_decision() -> dict[str, str]:
    manifest = read_json(TARGET_VENUE_DECISION_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    first = manifest.get("recommended_first_choice", "missing") if manifest else "missing"
    strong = manifest.get("strong_fit_count", "missing") if manifest else "missing"
    table_exists = TARGET_VENUE_DECISION_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and table_exists else "needs revision"
    return row(
        "Target-venue decision audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; recommended_first_choice={first}; strong_fit_count={strong}; table_exists={table_exists}.",
        "Run analyze_target_venue_decision_audit.py and restore the source-backed target-venue decision packet.",
    )


def verify_target_venue_policy_checklist() -> dict[str, str]:
    manifest = read_json(TARGET_VENUE_POLICY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    venues = manifest.get("venues", []) if manifest else []
    checklist_exists = TARGET_VENUE_POLICY_CHECKLIST.exists()
    required_venues = {"ACM Transactions on Quantum Computing", "Quantum", "Any selected venue"}
    venue_set = set(venues) if isinstance(venues, list) else set()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and isinstance(rows, int)
        and rows >= 8
        and required_venues.issubset(venue_set)
        and checklist_exists
        else "needs revision"
    )
    return row(
        "Target-venue policy checklist",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; venues={venues}; checklist_exists={checklist_exists}.",
        "Run analyze_target_venue_policy_checklist.py and restore the author-facing venue-policy checklist.",
    )


def verify_target_venue_format() -> dict[str, str]:
    manifest = read_json(TARGET_VENUE_FORMAT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    pages = manifest.get("pdf_pages", "missing") if manifest else "missing"
    pdf_bytes = manifest.get("pdf_bytes", "missing") if manifest else "missing"
    source_exists = TARGET_VENUE_FORMAT_SOURCE.exists()
    pdf_exists = TARGET_VENUE_FORMAT_PDF.exists()
    status = (
        "pass"
        if manifest
        and revisions == 0
        and rows == 6
        and isinstance(pages, int)
        and pages > 0
        and source_exists
        and pdf_exists
        else "needs revision"
    )
    return row(
        "Target-venue ACM/TQC format smoke",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}; pages={pages}; bytes={pdf_bytes}; source_exists={source_exists}; pdf_exists={pdf_exists}.",
        "Run make_acm_tqc_review_draft.py, compile resource_nmcts_submission_acm_tqc.tex, and rerun analyze_target_venue_format_smoke.py.",
    )


def verify_support_packet() -> dict[str, str]:
    manifest = read_json(SUPPORT_PACKET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Submission support packet audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_submission_support_packet_audit.py and restore cover-letter, declaration, venue, checklist, handoff, anonymous-review, private-preview, or editor/reviewer support anchors.",
    )


def verify_citation_support() -> dict[str, str]:
    manifest = read_json(CITATION_SUPPORT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    cited_keys = manifest.get("cited_key_count", "missing") if manifest else "missing"
    bib_keys = manifest.get("bib_key_count", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Citation support audit",
        status,
        f"rows={rows}; cited_keys={cited_keys}; bib_keys={bib_keys}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_citation_support_audit.py and restore missing citations, BibTeX entries, or reference locators.",
    )


def verify_oracle_resource_citation() -> dict[str, str]:
    manifest = read_json(ORACLE_RESOURCE_CITATION_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    citation_rows = manifest.get("citation_rows", "missing") if manifest else "missing"
    sources = manifest.get("primary_sources", []) if manifest else []
    table_exists = ORACLE_RESOURCE_CITATION_TABLE.exists()
    status = (
        "pass"
        if manifest and revisions == 0 and rows == 4 and citation_rows == 3 and table_exists
        else "needs revision"
    )
    return row(
        "Oracle-resource citation boundary audit",
        status,
        f"rows={rows}; citation_rows={citation_rows}; primary_sources={len(sources) if isinstance(sources, list) else 'missing'}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_oracle_resource_citation_audit.py and restore recent oracle-resource citations, BibTeX locators, manuscript anchors, or boundary wording.",
    )


def verify_learning_citation_verification() -> dict[str, str]:
    manifest = read_json(LEARNING_CITATION_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    citation_rows = manifest.get("citation_rows", "missing") if manifest else "missing"
    sources = manifest.get("primary_sources", []) if manifest else []
    table_exists = LEARNING_CITATION_TABLE.exists()
    status = "pass" if manifest and revisions == 0 and rows == 13 and citation_rows == 12 and table_exists else "needs revision"
    return row(
        "Learning-citation verification audit",
        status,
        f"rows={rows}; citation_rows={citation_rows}; primary_sources={len(sources) if isinstance(sources, list) else 'missing'}; needs_revision_count={revisions}; status_counts={counts}; table_exists={table_exists}.",
        "Run analyze_learning_citation_verification.py and restore learning-related DOI/arXiv locators or scope-boundary wording.",
    )


def verify_headline_numeric() -> dict[str, str]:
    manifest = read_json(HEADLINE_NUMERIC_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    claims = manifest.get("claims", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Headline numeric consistency",
        status,
        f"claims={claims}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_headline_numeric_consistency.py and align abstract tokens with CSV-derived evidence.",
    )


def verify_figure_assets() -> dict[str, str]:
    manifest = read_json(FIGURE_ASSET_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    figures = manifest.get("figures", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Figure asset audit",
        status,
        f"figures={figures}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run make_submission_figures.py and analyze_figure_asset_audit.py to restore referenced PDF/PNG/SVG assets and source-data CSVs.",
    )


def verify_latex_dependencies() -> dict[str, str]:
    manifest = read_json(LATEX_DEPENDENCY_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "LaTeX dependency audit",
            "pass",
            "extracted_payload_mode=1; LaTeX dependency terminal manifest is intentionally excluded from the upload payload.",
            "Run analyze_latex_dependency_audit.py from the source worktree after rebuilding the payload archive.",
        )
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    dependencies = manifest.get("dependency_count", "missing") if manifest else "missing"
    type_counts = manifest.get("dependency_type_counts", {}) if manifest else {}
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "LaTeX dependency audit",
        status,
        f"dependencies={dependencies}; type_counts={type_counts}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_latex_dependency_audit.py after payload creation and restore missing TeX, table, figure, bibliography, or payload entries.",
    )


def verify_pdf_visual() -> dict[str, str]:
    manifest = read_json(PDF_VISUAL_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF visual render audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_visual_audit.py and inspect rendered PDF pages for blank, clipped, or overfilled output.",
    )


def verify_pdf_text() -> dict[str, str]:
    manifest = read_json(PDF_TEXT_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    anchors = manifest.get("required_anchor_count", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF text/searchability audit",
        status,
        f"rows={rows}; required_anchors={anchors}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_text_audit.py and inspect pdftotext output for missing anchors, identity leaks, or placeholder remnants.",
    )


def verify_pdf_metadata() -> dict[str, str]:
    manifest = read_json(PDF_METADATA_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "PDF metadata/privacy audit",
        status,
        f"rows={rows}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_pdf_metadata_audit.py and inspect pdfinfo metadata for privacy leaks, encryption, JavaScript, forms, or page-geometry drift.",
    )


def verify_source_path_privacy() -> dict[str, str]:
    manifest = read_json(SOURCE_PATH_PRIVACY_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    rows = manifest.get("rows", "missing") if manifest else "missing"
    payload_local_path_files = manifest.get("payload_local_path_files", "missing") if manifest else "missing"
    status = "pass" if manifest and revisions == 0 else "needs revision"
    return row(
        "Source/path privacy audit",
        status,
        f"rows={rows}; payload_local_path_files={payload_local_path_files}; needs_revision_count={revisions}; status_counts={counts}.",
        "Run analyze_source_path_privacy_audit.py and move local paths out of manuscript/support sources while keeping toolchain paths only in provenance outputs.",
    )


def verify_text_preview() -> dict[str, str]:
    manifest = read_json(TEXT_PREVIEW_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    ignored = bool(manifest.get("private_outputs_are_git_ignored", False))
    status = "pass" if manifest and ignored else "needs revision"
    return row(
        "Private submission text preview",
        status,
        f"status_counts={counts}; private_outputs_are_git_ignored={ignored}.",
        "Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git.",
    )


def verify_metadata_validator() -> dict[str, str]:
    manifest = read_json(METADATA_VALIDATOR_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Private metadata validator",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}.",
        "Run validate_submission_metadata.py and fix metadata format or consistency rows before upload.",
    )


def verify_metadata_starter_dry_run() -> dict[str, str]:
    before_exists = METADATA_FILE.exists()
    before_stat = METADATA_FILE.stat() if before_exists else None
    try:
        proc = subprocess.run(
            [sys.executable, str(METADATA_STARTER)],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        return row(
            "Metadata starter dry-run",
            "needs revision",
            f"starter execution failed: {exc}.",
            "Run make_submission_metadata_starter.py without --write-private and fix the exception.",
        )
    after_exists = METADATA_FILE.exists()
    after_stat = METADATA_FILE.stat() if after_exists else None
    private_created = after_exists and not before_exists
    private_modified = (
        before_stat is not None
        and after_stat is not None
        and (before_stat.st_mtime_ns, before_stat.st_size) != (after_stat.st_mtime_ns, after_stat.st_size)
    )
    expected_tokens = ("dry run only",) if EXTRACTED_PAYLOAD_MODE else (
        "filled: code_availability.repository_url",
        "filled: code_availability.commit_hash",
        "dry run only",
    )
    missing_tokens = [token for token in expected_tokens if token not in proc.stdout]
    status = (
        "pass"
        if proc.returncode == 0 and not missing_tokens and not private_created and not private_modified
        else "needs revision"
    )
    return row(
        "Metadata starter dry-run",
        status,
        f"returncode={proc.returncode}; missing_tokens={missing_tokens or 'none'}; private_preexisting={before_exists}; private_created={private_created}; private_modified={private_modified}.",
        "Run make_submission_metadata_starter.py without --write-private and keep it read-only until author input is explicit.",
    )


def verify_metadata_answers_dry_run() -> dict[str, str]:
    before_answers_exists = METADATA_ANSWERS_FILE.exists()
    before_answers_stat = METADATA_ANSWERS_FILE.stat() if before_answers_exists else None
    before_metadata_exists = METADATA_FILE.exists()
    before_metadata_stat = METADATA_FILE.stat() if before_metadata_exists else None
    try:
        proc = subprocess.run(
            [sys.executable, str(METADATA_FROM_ANSWERS)],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        return row(
            "Metadata answer converter dry-run",
            "needs revision",
            f"converter execution failed: {exc}.",
            "Run make_submission_metadata_from_answers.py without --write-private and fix the exception.",
        )
    after_answers_exists = METADATA_ANSWERS_FILE.exists()
    after_answers_stat = METADATA_ANSWERS_FILE.stat() if after_answers_exists else None
    after_metadata_exists = METADATA_FILE.exists()
    after_metadata_stat = METADATA_FILE.stat() if after_metadata_exists else None
    answers_created = after_answers_exists and not before_answers_exists
    metadata_created = after_metadata_exists and not before_metadata_exists
    answers_modified = (
        before_answers_stat is not None
        and after_answers_stat is not None
        and (before_answers_stat.st_mtime_ns, before_answers_stat.st_size)
        != (after_answers_stat.st_mtime_ns, after_answers_stat.st_size)
    )
    metadata_modified = (
        before_metadata_stat is not None
        and after_metadata_stat is not None
        and (before_metadata_stat.st_mtime_ns, before_metadata_stat.st_size)
        != (after_metadata_stat.st_mtime_ns, after_metadata_stat.st_size)
    )
    expected_tokens = (
        ("private answers missing",)
        if not before_answers_exists
        else ("filled metadata paths:", "dry run only")
    )
    missing_tokens = [token for token in expected_tokens if token not in proc.stdout]
    status = (
        "pass"
        if proc.returncode == 0
        and not missing_tokens
        and not answers_created
        and not metadata_created
        and not answers_modified
        and not metadata_modified
        else "needs revision"
    )
    return row(
        "Metadata answer converter dry-run",
        status,
        f"returncode={proc.returncode}; missing_tokens={missing_tokens or 'none'}; answers_preexisting={before_answers_exists}; answers_created={answers_created}; answers_modified={answers_modified}; metadata_preexisting={before_metadata_exists}; metadata_created={metadata_created}; metadata_modified={metadata_modified}.",
        "Run make_submission_metadata_from_answers.py without --write-private and keep both private answer and metadata files read-only until author input is explicit.",
    )


def verify_metadata_pipeline_selftest() -> dict[str, str]:
    manifest = read_json(METADATA_PIPELINE_SELFTEST_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    synthetic_only = bool(manifest.get("uses_synthetic_metadata_only", False))
    writes_private_metadata = bool(manifest.get("writes_private_metadata", True))
    writes_private_preview = bool(manifest.get("writes_private_preview_files", True))
    status = (
        "pass"
        if manifest
        and needs_revision == 0
        and synthetic_only
        and not writes_private_metadata
        and not writes_private_preview
        else "needs revision"
    )
    return row(
        "Metadata pipeline self-test",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}; synthetic_only={synthetic_only}; writes_private_metadata={writes_private_metadata}; writes_private_preview_files={writes_private_preview}.",
        "Run selftest_submission_metadata_pipeline.py and keep the fixture synthetic and non-private.",
    )


def verify_anonymous_review_audit() -> dict[str, str]:
    manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    needs_author_input = int(manifest.get("needs_author_input_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Anonymous-review readiness audit",
        status,
        f"needs_revision_count={needs_revision}; needs_author_input_count={needs_author_input}; status_counts={counts}.",
        "Run analyze_anonymous_review_readiness.py and resolve needs-revision rows; double-blind conversion remains venue-dependent author input.",
    )


def verify_author_input_closure() -> dict[str, str]:
    manifest = read_json(AUTHOR_INPUT_CLOSURE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_metadata_paths", "missing") if manifest else "missing"
    metadata_present = bool(manifest.get("metadata_present", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Author-input closure audit",
        status,
        f"needs_revision_count={needs_revision}; required_metadata_paths={required_paths}; metadata_present={metadata_present}; status_counts={counts}.",
        "Run analyze_author_input_closure_audit.py and restore author-packet coverage, private metadata protection, or support-document visibility.",
    )


def verify_author_questionnaire_coverage() -> dict[str, str]:
    manifest = read_json(AUTHOR_QUESTIONNAIRE_COVERAGE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_paths", "missing") if manifest else "missing"
    missing_required = manifest.get("missing_required_paths", "missing") if manifest else "missing"
    missing_template = manifest.get("missing_template_paths", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 and not missing_required and not missing_template else "needs revision"
    return row(
        "Author questionnaire coverage audit",
        status,
        f"required_paths={required_paths}; missing_required_paths={missing_required}; missing_template_paths={missing_template}; status_counts={counts}.",
        "Run analyze_author_questionnaire_coverage.py and align the Chinese questionnaire with every private metadata template field.",
    )


def verify_author_minimal_form_coverage() -> dict[str, str]:
    manifest = read_json(AUTHOR_MINIMAL_FORM_COVERAGE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_paths", "missing") if manifest else "missing"
    missing_required = manifest.get("missing_required_paths", "missing") if manifest else "missing"
    missing_template = manifest.get("missing_template_paths", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 and not missing_required and not missing_template else "needs revision"
    return row(
        "Author minimal response-form coverage audit",
        status,
        f"required_paths={required_paths}; missing_required_paths={missing_required}; missing_template_paths={missing_template}; status_counts={counts}.",
        "Run analyze_author_minimal_form_coverage.py and align the short Chinese response form with every private metadata template field.",
    )


def verify_metadata_answer_template_coverage() -> dict[str, str]:
    manifest = read_json(METADATA_ANSWER_TEMPLATE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_metadata_paths", "missing") if manifest else "missing"
    answer_paths = manifest.get("answer_template_required_paths", "missing") if manifest else "missing"
    starter_only = manifest.get("starter_only_required_paths", "missing") if manifest else "missing"
    missing_required = manifest.get("missing_required_paths", "missing") if manifest else "missing"
    unknown_paths = manifest.get("unknown_answer_paths", "missing") if manifest else "missing"
    private_like = manifest.get("private_like_value_paths", "missing") if manifest else "missing"
    remaining = manifest.get("remaining_author_paths_after_template_dry_run", "missing") if manifest else "missing"
    status = (
        "pass"
        if manifest and needs_revision == 0 and not missing_required and not unknown_paths and not private_like
        else "needs revision"
    )
    return row(
        "Metadata answer-template coverage audit",
        status,
        f"required_metadata_paths={required_paths}; answer_template_required_paths={answer_paths}; starter_only_required_paths={starter_only}; missing_required_paths={missing_required}; unknown_answer_paths={unknown_paths}; remaining_author_paths={remaining}; private_like_value_paths={private_like}; status_counts={counts}.",
        "Run analyze_metadata_answer_template_coverage.py and align the public answer template with required private metadata paths.",
    )


def verify_metadata_closure_path() -> dict[str, str]:
    manifest = read_json(METADATA_CLOSURE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    required_paths = manifest.get("required_metadata_paths", "missing") if manifest else "missing"
    metadata_present = bool(manifest.get("metadata_present", False)) if manifest else False
    ready = bool(manifest.get("closure_path_ready", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 and ready else "needs revision"
    return row(
        "Submission metadata closure path",
        status,
        f"needs_revision_count={needs_revision}; required_metadata_paths={required_paths}; metadata_present={metadata_present}; closure_path_ready={ready}; status_counts={counts}.",
        "Run analyze_submission_metadata_closure_path.py and keep the final author/venue metadata path explicit, ignored, and machine-checkable.",
    )


def verify_final_human_gate() -> dict[str, str]:
    manifest = read_json(FINAL_HUMAN_GATE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Final human-gate audit",
            "pass",
            "extracted_payload_mode=1; final human-gate terminal manifest is intentionally excluded from the upload payload.",
            "Run analyze_final_human_gate_audit.py in the source worktree after goal, metadata, anonymous-review, payload, or source-privacy audits change.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = manifest.get("rows", "missing") if manifest else "missing"
    human_gate_open = bool(manifest.get("human_gate_open", False)) if manifest else False
    machine_side_closed = bool(manifest.get("machine_side_closed", False)) if manifest else False
    blocker = manifest.get("remaining_blocker_class", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 and human_gate_open and machine_side_closed else "needs revision"
    return row(
        "Final human-gate audit",
        status,
        f"rows={rows}; needs_revision_count={needs_revision}; human_gate_open={human_gate_open}; machine_side_closed={machine_side_closed}; remaining_blocker_class={blocker}; status_counts={counts}.",
        "Run analyze_final_human_gate_audit.py after goal, metadata, anonymous-review, payload, or source-privacy audits change.",
    )


def verify_final_upload_sequence() -> dict[str, str]:
    manifest = read_json(FINAL_UPLOAD_SEQUENCE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Final upload sequence audit",
            "pass",
            "extracted_payload_mode=1; final upload-sequence terminal manifest is intentionally excluded from the upload payload.",
            "Run analyze_final_upload_sequence_audit.py in the source worktree after handoff, metadata, anonymous-review, or final human-gate audits change.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = manifest.get("rows", "missing") if manifest else "missing"
    sequence_ready = bool(manifest.get("sequence_ready", False)) if manifest else False
    terminal = bool(manifest.get("terminal_audit", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 and sequence_ready and terminal else "needs revision"
    return row(
        "Final upload sequence audit",
        status,
        f"rows={rows}; needs_revision_count={needs_revision}; sequence_ready={sequence_ready}; terminal_audit={terminal}; status_counts={counts}.",
        "Run analyze_final_upload_sequence_audit.py after changing final handoff docs, metadata templates, anonymous-review policy, comparison handoffs, or final human-gate outputs.",
    )


def verify_upload_bundle_matrix() -> dict[str, str]:
    manifest = read_json(UPLOAD_BUNDLE_MATRIX_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Upload bundle matrix audit",
            "pass",
            "extracted_payload_mode=1; upload bundle-matrix terminal manifest is intentionally excluded from the upload payload.",
            "Run analyze_upload_bundle_matrix_audit.py in the source worktree after payload, support-doc, target-format, or final upload-route outputs change.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = manifest.get("rows", "missing") if manifest else "missing"
    ready = bool(manifest.get("bundle_matrix_ready", False)) if manifest else False
    terminal = bool(manifest.get("terminal_audit", False)) if manifest else False
    bundles = manifest.get("bundles", []) if manifest else []
    status = "pass" if manifest and needs_revision == 0 and ready and terminal else "needs revision"
    return row(
        "Upload bundle matrix audit",
        status,
        f"rows={rows}; needs_revision_count={needs_revision}; bundle_matrix_ready={ready}; terminal_audit={terminal}; bundles={bundles}; status_counts={counts}.",
        "Run analyze_upload_bundle_matrix_audit.py after changing author/anonymous/ACM PDFs, payload packaging, support docs, private-file boundaries, target-format smoke, or final upload route docs.",
    )


def verify_final_upload_plan() -> dict[str, str]:
    manifest = read_json(FINAL_UPLOAD_PLAN_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Final upload plan generator",
            "pass",
            "extracted_payload_mode=1; final upload-plan manifest is allowed to be absent from extracted payloads.",
            "Run make_final_upload_plan.py in the source worktree after private metadata, final previews, or upload-route files change.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    needs_author = int(manifest.get("needs_author_input_count", -1)) if manifest else -1
    route = manifest.get("route", "missing") if manifest else "missing"
    generated = bool(manifest.get("generated_private_upload_plan", False)) if manifest else False
    ignored = bool(manifest.get("private_output_is_git_ignored", False)) if manifest else False
    status = "pass" if manifest and needs_revision == 0 and ignored else "needs revision"
    return row(
        "Final upload plan generator",
        status,
        f"route={route}; generated_private_upload_plan={generated}; needs_author_input_count={needs_author}; needs_revision_count={needs_revision}; private_output_is_git_ignored={ignored}; status_counts={counts}.",
        "Run make_final_upload_plan.py after filling private metadata; missing metadata may remain author input, but needs revision must stay zero.",
    )


def verify_final_upload_plan_tool_audit() -> dict[str, str]:
    manifest = read_json(FINAL_UPLOAD_PLAN_TOOL_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Final upload plan tool audit",
            "pass",
            "extracted_payload_mode=1; final upload-plan tool manifest is allowed to be absent from extracted payloads.",
            "Run analyze_final_upload_plan_tool_audit.py in the source worktree after changing the upload-plan generator, private output ignore rule, or route choices.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = manifest.get("rows", "missing") if manifest else "missing"
    routes = manifest.get("synthetic_routes", []) if manifest else []
    uses_private = bool(manifest.get("uses_private_metadata", True)) if manifest else True
    status = (
        "pass"
        if manifest and needs_revision == 0 and not uses_private and counts.get("pass", 0) == rows
        else "needs revision"
    )
    return row(
        "Final upload plan tool audit",
        status,
        f"rows={rows}; needs_revision_count={needs_revision}; synthetic_routes={routes}; uses_private_metadata={uses_private}; status_counts={counts}.",
        "Run analyze_final_upload_plan_tool_audit.py and restore author, anonymous, and ACM/TQC synthetic route coverage.",
    )


def verify_private_payload_exclusion() -> dict[str, str]:
    manifest = read_json(PAYLOAD_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Private metadata payload exclusion",
            "pass",
            f"extracted_payload_mode=1; payload manifest is intentionally excluded from the upload payload; checked_basenames={sorted(PRIVATE_PAYLOAD_BASENAMES)}.",
            "Run make_submission_payload_archive.py and analyze_payload_roundtrip_audit.py from the source worktree before distributing the tarball.",
        )
    files = manifest.get("files", []) if manifest else []
    leaked: list[str] = []
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            if Path(path).name in PRIVATE_PAYLOAD_BASENAMES:
                leaked.append(path)
    else:
        leaked.append("<payload manifest has invalid files list>")
    return row(
        "Private metadata payload exclusion",
        "pass" if manifest and not leaked else "needs revision",
        f"private_payload_hits={leaked or 'none'}; checked_basenames={sorted(PRIVATE_PAYLOAD_BASENAMES)}.",
        "Regenerate the payload after removing ignored private metadata or preview files from package inputs.",
    )


def verify_payload_roundtrip() -> dict[str, str]:
    manifest = read_json(PAYLOAD_ROUNDTRIP_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload round-trip audit",
            "pass",
            "extracted_payload_mode=1; archive round-trip manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_roundtrip_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload round-trip audit",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}.",
        "Run analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues.",
    )


def verify_payload_git_policy() -> dict[str, str]:
    manifest = read_json(PAYLOAD_GIT_POLICY_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Generated payload Git policy",
            "pass",
            "extracted_payload_mode=1; source-worktree Git-policy manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_git_policy_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    rows = manifest.get("rows", "missing") if manifest else "missing"
    extracted = manifest.get("extracted_payload_mode", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Generated payload Git policy",
        status,
        f"rows={rows}; needs_revision_count={needs_revision}; status_counts={counts}; extracted_payload_mode={extracted}.",
        "Run analyze_payload_git_policy_audit.py after payload creation and keep generated tarballs ignored and out of Git.",
    )


def verify_payload_extraction_smoke() -> dict[str, str]:
    manifest = read_json(PAYLOAD_EXTRACTION_SMOKE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload extraction smoke audit",
            "pass",
            "extracted_payload_mode=1; extraction-smoke terminal manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_extraction_smoke_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    smoke_scripts = manifest.get("smoke_scripts", []) if manifest else []
    script_count = len(smoke_scripts) if isinstance(smoke_scripts, list) else "invalid"
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload extraction smoke audit",
        status,
        f"needs_revision_count={needs_revision}; status_counts={counts}; smoke_scripts={script_count}.",
        "Run analyze_payload_extraction_smoke_audit.py after payload creation and fix extracted-payload script failures.",
    )


def verify_payload_verifier_smoke() -> dict[str, str]:
    manifest = read_json(PAYLOAD_VERIFIER_SMOKE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload verifier smoke audit",
            "pass",
            "extracted_payload_mode=1; verifier-smoke terminal manifest is intentionally excluded from the extracted upload payload.",
            "Run analyze_payload_verifier_smoke_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    verifier_returncode = manifest.get("verifier_returncode", "missing") if manifest else "missing"
    rows = manifest.get("rows", "missing") if manifest else "missing"
    verifier_rows = manifest.get("verifier_rows", "missing") if manifest else "missing"
    source_verifier_rows = manifest.get("source_verifier_rows", "missing") if manifest else "missing"
    row_delta = manifest.get("row_delta", "missing") if manifest else "missing"
    expected_row_delta = manifest.get("expected_row_delta", "missing") if manifest else "missing"
    row_delta_reason = manifest.get("row_delta_reason", "missing") if manifest else "missing"
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload verifier smoke audit",
        status,
        f"needs_revision_count={needs_revision}; verifier_returncode={verifier_returncode}; rows={rows}; verifier_rows={verifier_rows}; source_verifier_rows={source_verifier_rows}; row_delta={row_delta}; expected_row_delta={expected_row_delta}; row_delta_reason={row_delta_reason}; status_counts={counts}.",
        "Run analyze_payload_verifier_smoke_audit.py after payload creation and fix extracted one-command verifier failures.",
    )


def verify_payload_latex_compile() -> dict[str, str]:
    manifest = read_json(PAYLOAD_LATEX_COMPILE_MANIFEST)
    if EXTRACTED_PAYLOAD_MODE and not manifest:
        return row(
            "Payload LaTeX compile audit",
            "pass",
            "extracted_payload_mode=1; extracted-payload LaTeX compile manifest is intentionally excluded from the upload payload.",
            "Run analyze_payload_latex_compile_audit.py from the source worktree where the tarball exists.",
        )
    counts = manifest.get("status_counts", {}) if manifest else {}
    needs_revision = int(manifest.get("needs_revision_count", -1)) if manifest else -1
    compiled = manifest.get("compiled_manuscripts", "missing") if manifest else "missing"
    try:
        compiled_count = int(compiled)
    except Exception:
        compiled_count = -1
    status = "pass" if manifest and needs_revision == 0 and compiled_count >= 2 else "needs revision"
    return row(
        "Payload LaTeX compile audit",
        status,
        f"needs_revision_count={needs_revision}; compiled_manuscripts={compiled}; status_counts={counts}.",
        "Run analyze_payload_latex_compile_audit.py and restore missing extracted-payload TeX, table, figure, or bibliography dependencies.",
    )


def verify_latex_log(path: Path, label: str) -> dict[str, str]:
    if not path.exists():
        if EXTRACTED_PAYLOAD_MODE:
            return row(
                label,
                "pass",
                "extracted_payload_mode=1; LaTeX logs are intentionally excluded from the upload payload while the compiled PDF is present.",
                "Run latexmk and the local verifier from the source worktree to inspect full LaTeX logs.",
            )
        return row(label, "needs revision", "LaTeX log is missing.", "Rebuild the PDF with latexmk.")
    bad_patterns = re.compile(r"Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun")
    allowed = (
        "Package: rerunfilecheck",
        r"LaTeX Warning: Command \showhyphens",
    )
    unexpected: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not bad_patterns.search(line):
            continue
        if any(token in line for token in allowed):
            continue
        unexpected.append(f"{lineno}:{line.strip()}")
    return row(
        label,
        "pass" if not unexpected else "needs revision",
        "Only allowed rerunfilecheck/showhyphens log lines found." if not unexpected else "; ".join(unexpected[:5]),
        "Inspect the LaTeX log and fix unexpected warnings or errors.",
    )


def build_rows() -> list[dict[str, str]]:
    rows = [
        verify_pdf(PDF, "Compiled author PDF"),
        verify_pdf(ANONYMOUS_PDF, "Compiled anonymous PDF"),
    ]
    rows.extend(verify_payload_sha())
    rows.extend(
        [
            verify_readiness(),
            verify_submission_archive_manifest(),
            verify_registry(),
            verify_claim_scope(),
            verify_comparison_protocol(),
            verify_comparison_target_validity(),
            verify_comparison_claim_hierarchy(),
            verify_comparison_answer_scorecard(),
            verify_baseline_fairness_ledger(),
            verify_comparison_route_decision(),
            verify_benchmark_suite_audit(),
            verify_benchmark_function_diversity_audit(),
            verify_experimental_evidence_ladder(),
            verify_weight_robustness(),
            verify_resource_weight_sensitivity(),
            verify_cnot_constraint_profile(),
            verify_sshr_reproduction_scope(),
            verify_threats_to_validity(),
            verify_novelty_scorecard(),
            verify_public_handoff_freshness(),
            verify_ros_garbage_proxy(),
            verify_ros_garbage_budget_frontier(),
            verify_ros_checkpoint_optimizer(),
            verify_caterpillar_probe(),
            verify_caterpillar_api_probe(),
            verify_ros_gap(),
            verify_stg_benchmark(),
            verify_traditional_structure_mechanism(),
            verify_search_budget_contract(),
            verify_schedule_proxy(),
            verify_ultra_scale64(),
            verify_ultra_scale64_resource_profile(),
            verify_search_control(),
            verify_bitflip_neural_budget(),
            verify_bitflip_prior_difficulty(),
            verify_bitflip_prior_feature_gate(),
            verify_bitflip_prior_feature_gate_cv(),
            verify_bitflip_prior_feature_gate_cv_random_control(),
            verify_root_action_ranker(),
            verify_phase_rotation_precision(),
            verify_phase_rotation_sequence_smoke(),
            verify_rotation_synthesis_backend(),
            verify_phase_policy_budget_frontier(),
            verify_learned_control(),
            verify_limited_learned_boundary(),
            verify_learned_effect_uncertainty(),
            verify_neural_mcts_claim_calibration(),
            verify_runtime_envelope(),
            verify_bitflip_random_prior(),
            verify_frontier_random_depth(),
            verify_stochastic_control_stability(),
            verify_editorial_screening(),
            verify_target_venue_decision(),
            verify_target_venue_policy_checklist(),
            verify_target_venue_format(),
            verify_support_packet(),
            verify_citation_support(),
            verify_oracle_resource_citation(),
            verify_learning_citation_verification(),
            verify_headline_numeric(),
            verify_figure_assets(),
            verify_latex_dependencies(),
            verify_pdf_visual(),
            verify_pdf_text(),
            verify_pdf_metadata(),
            verify_source_path_privacy(),
            verify_metadata_answers_dry_run(),
            verify_metadata_starter_dry_run(),
            verify_metadata_validator(),
            verify_metadata_pipeline_selftest(),
            verify_anonymous_review_audit(),
            verify_author_input_closure(),
            verify_author_questionnaire_coverage(),
            verify_author_minimal_form_coverage(),
            verify_metadata_answer_template_coverage(),
            verify_metadata_closure_path(),
            verify_final_human_gate(),
            verify_final_upload_sequence(),
            verify_upload_bundle_matrix(),
            verify_final_upload_plan(),
            verify_final_upload_plan_tool_audit(),
            verify_text_preview(),
            verify_private_payload_exclusion(),
            verify_payload_roundtrip(),
            verify_payload_git_policy(),
            verify_payload_extraction_smoke(),
            verify_payload_verifier_smoke(),
            verify_payload_latex_compile(),
            verify_latex_log(LOG, "Author LaTeX log boundary"),
            verify_latex_log(ANONYMOUS_LOG, "Anonymous LaTeX log boundary"),
        ]
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Submission Package Verifier",
        "",
        "This read-only verifier checks the terminal package invariants after the payload archive has been created.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} | {item['next_action']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "extracted_payload_mode": EXTRACTED_PAYLOAD_MODE,
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "needs_revision_count": failures,
        "outputs": {
            "summary": "results/summary_submission_package_verifier.csv",
            "analysis": "results/analysis_submission_package_verifier.md",
            "manifest": "results/manifest_submission_package_verifier.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_package_verifier.csv", rows)
    write_markdown(RESULTS / "analysis_submission_package_verifier.md", rows)
    write_manifest(RESULTS / "manifest_submission_package_verifier.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} submission package verifier rows")
    if failures:
        print(f"warning: {failures} verifier row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
