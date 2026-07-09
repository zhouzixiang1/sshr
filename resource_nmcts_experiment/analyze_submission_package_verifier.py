#!/usr/bin/env python3
"""Read-only verifier for the current submission package.

The verifier runs after the payload archive has been created.  It checks the
terminal package invariants that are easy to regress during final polishing:
compiled PDF availability, payload SHA consistency, readiness status, raw rerun
registry coverage, claim-scope hygiene, comparison-protocol coverage,
comparison-target validity,
score-weight robustness,
threats-to-validity coverage,
novelty/comparison scorecard coverage,
public handoff freshness,
published STG counterpoint,
search-control baseline coverage,
learned-control audit coverage,
neural/MCTS claim-calibration coverage,
frontier random-depth control coverage,
ultra-scale n=48--64 stress coverage,
ultra-scale n=48--64 resource-profile coverage,
editorial screening support,
target-venue decision support,
submission support packet coverage,
ROS reproduction-boundary support,
citation support,
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
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
ANONYMOUS_LOG = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.log"
PAYLOAD = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
READINESS = RESULTS / "summary_submission_readiness_audit.csv"
REGISTRY_SUMMARY = RESULTS / "summary_artifact_rerun_registry.csv"
REGISTRY_MANIFEST = RESULTS / "manifest_artifact_rerun_registry.json"
PAYLOAD_SUMMARY = RESULTS / "summary_submission_payload_archive.csv"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"
COMPARISON_PROTOCOL_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_protocol_audit.tex"
COMPARISON_TARGET_VALIDITY_MANIFEST = RESULTS / "manifest_comparison_target_validity_audit.json"
COMPARISON_TARGET_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_target_validity_audit.tex"
COMPARISON_ANSWER_SCORECARD_MANIFEST = RESULTS / "manifest_comparison_answer_scorecard.json"
COMPARISON_ANSWER_SCORECARD_TABLE = THIS_DIR / "paper_latex" / "tables" / "comparison_answer_scorecard.tex"
WEIGHT_ROBUSTNESS_MANIFEST = RESULTS / "manifest_weight_robustness.json"
WEIGHT_ROBUSTNESS_TABLE = THIS_DIR / "paper_latex" / "tables" / "weight_robustness_compact.tex"
RESOURCE_WEIGHT_SENSITIVITY_MANIFEST = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
RESOURCE_WEIGHT_SENSITIVITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "resource_weight_sensitivity_audit.tex"
THREATS_VALIDITY_MANIFEST = RESULTS / "manifest_threats_to_validity_audit.json"
THREATS_VALIDITY_TABLE = THIS_DIR / "paper_latex" / "tables" / "threats_to_validity_audit.tex"
NOVELTY_SCORECARD_MANIFEST = RESULTS / "manifest_novelty_comparison_scorecard.json"
NOVELTY_SCORECARD_TABLE = THIS_DIR / "paper_latex" / "tables" / "novelty_comparison_scorecard.tex"
PUBLIC_HANDOFF_MANIFEST = RESULTS / "manifest_public_handoff_freshness_audit.json"
ROS_GAP_MANIFEST = RESULTS / "manifest_ros_reproduction_gap_audit.json"
ROS_GARBAGE_MANIFEST = RESULTS / "manifest_ros_lut_garbage_proxy.json"
ROS_GARBAGE_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_proxy.tex"
ROS_GARBAGE_BUDGET_MANIFEST = RESULTS / "manifest_ros_lut_garbage_budget_frontier.json"
ROS_GARBAGE_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "ros_lut_garbage_budget_frontier.tex"
STG_BENCHMARK_MANIFEST = RESULTS / "manifest_stg_published_benchmark.json"
STG_BENCHMARK_TABLE = THIS_DIR / "paper_latex" / "tables" / "stg_published_benchmark.tex"
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
ROOT_ACTION_RANKER_MANIFEST = RESULTS / "manifest_root_action_ranker_audit.json"
ROOT_ACTION_RANKER_TABLE = THIS_DIR / "paper_latex" / "tables" / "root_action_ranker_audit.tex"
PHASE_ROTATION_PRECISION_MANIFEST = RESULTS / "manifest_phase_rotation_precision_audit.json"
PHASE_ROTATION_PRECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_rotation_precision_audit.tex"
PHASE_ROTATION_SEQUENCE_MANIFEST = RESULTS / "manifest_phase_rotation_sequence_smoke_audit.json"
PHASE_ROTATION_SEQUENCE_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_rotation_sequence_smoke_audit.tex"
PHASE_POLICY_BUDGET_MANIFEST = RESULTS / "manifest_phase_policy_budget_frontier.json"
PHASE_POLICY_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "phase_policy_budget_frontier.tex"
NEURAL_MCTS_CLAIM_MANIFEST = RESULTS / "manifest_neural_mcts_claim_calibration.json"
NEURAL_MCTS_CLAIM_TABLE = THIS_DIR / "paper_latex" / "tables" / "neural_mcts_claim_calibration.tex"
BITFLIP_RANDOM_PRIOR_MANIFEST = RESULTS / "manifest_bitflip_random_prior_control.json"
BITFLIP_RANDOM_PRIOR_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_random_prior_control.tex"
BITFLIP_NEURAL_BUDGET_MANIFEST = RESULTS / "manifest_bitflip_neural_budget_sweep.json"
BITFLIP_NEURAL_BUDGET_TABLE = THIS_DIR / "paper_latex" / "tables" / "bitflip_neural_budget_sweep.tex"
FRONTIER_RANDOM_DEPTH_MANIFEST = RESULTS / "manifest_frontier_random_depth_control.json"
FRONTIER_RANDOM_DEPTH_TABLE = THIS_DIR / "paper_latex" / "tables" / "frontier_random_depth_control.tex"
EDITORIAL_SCREENING_MANIFEST = RESULTS / "manifest_editorial_screening_audit.json"
TARGET_VENUE_DECISION_MANIFEST = RESULTS / "manifest_target_venue_decision_audit.json"
TARGET_VENUE_DECISION_TABLE = THIS_DIR / "paper_latex" / "tables" / "target_venue_decision_audit.tex"
TARGET_VENUE_FORMAT_MANIFEST = RESULTS / "manifest_target_venue_format_smoke.json"
TARGET_VENUE_FORMAT_SOURCE = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"
TARGET_VENUE_FORMAT_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.pdf"
SUPPORT_PACKET_MANIFEST = RESULTS / "manifest_submission_support_packet_audit.json"
CITATION_SUPPORT_MANIFEST = RESULTS / "manifest_citation_support_audit.json"
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
METADATA_CLOSURE_MANIFEST = RESULTS / "manifest_submission_metadata_closure_path.json"
PAYLOAD_ROUNDTRIP_MANIFEST = RESULTS / "manifest_payload_roundtrip_audit.json"
PAYLOAD_GIT_POLICY_MANIFEST = RESULTS / "manifest_payload_git_policy_audit.json"
PAYLOAD_EXTRACTION_SMOKE_MANIFEST = RESULTS / "manifest_payload_extraction_smoke_audit.json"
PAYLOAD_VERIFIER_SMOKE_MANIFEST = RESULTS / "manifest_payload_verifier_smoke_audit.json"
PAYLOAD_LATEX_COMPILE_MANIFEST = RESULTS / "manifest_payload_latex_compile_audit.json"
METADATA_STARTER = THIS_DIR / "make_submission_metadata_starter.py"
METADATA_FILE = THIS_DIR / "submission_package" / "submission_metadata.json"

PRIVATE_PAYLOAD_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
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
    rows = [item for item in rows if item.get("item") != "Terminal package verifier"]
    counts: dict[str, int] = {}
    for item in rows:
        counts[item.get("status", "")] = counts.get(item.get("status", ""), 0) + 1
    only_author_gate = counts.get("needs author input", 0) == 1 and counts.get("needs revision", 0) == 0
    return row(
        "Readiness audit terminal state",
        "pass" if only_author_gate else "needs revision",
        f"status_counts={counts}; terminal_verifier_self_row_excluded=True.",
        "Resolve any needs-revision rows; author-specific declarations remain manual.",
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
        and rows == 6
        and smoke_pass == 6
        and tight_pass == 2
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
        and rows == 5
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
    status = "pass" if manifest and needs_revision == 0 else "needs revision"
    return row(
        "Payload verifier smoke audit",
        status,
        f"needs_revision_count={needs_revision}; verifier_returncode={verifier_returncode}; rows={rows}; status_counts={counts}.",
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
            verify_registry(),
            verify_claim_scope(),
            verify_comparison_protocol(),
            verify_comparison_target_validity(),
            verify_comparison_answer_scorecard(),
            verify_weight_robustness(),
            verify_resource_weight_sensitivity(),
            verify_threats_to_validity(),
            verify_novelty_scorecard(),
            verify_public_handoff_freshness(),
            verify_ros_garbage_proxy(),
            verify_ros_garbage_budget_frontier(),
            verify_ros_gap(),
            verify_stg_benchmark(),
            verify_search_budget_contract(),
            verify_schedule_proxy(),
            verify_ultra_scale64(),
            verify_ultra_scale64_resource_profile(),
            verify_search_control(),
            verify_bitflip_neural_budget(),
            verify_root_action_ranker(),
            verify_phase_rotation_precision(),
            verify_phase_rotation_sequence_smoke(),
            verify_phase_policy_budget_frontier(),
            verify_learned_control(),
            verify_neural_mcts_claim_calibration(),
            verify_bitflip_random_prior(),
            verify_frontier_random_depth(),
            verify_editorial_screening(),
            verify_target_venue_decision(),
            verify_target_venue_format(),
            verify_support_packet(),
            verify_citation_support(),
            verify_headline_numeric(),
            verify_figure_assets(),
            verify_latex_dependencies(),
            verify_pdf_visual(),
            verify_pdf_text(),
            verify_pdf_metadata(),
            verify_source_path_privacy(),
            verify_metadata_starter_dry_run(),
            verify_metadata_validator(),
            verify_metadata_pipeline_selftest(),
            verify_anonymous_review_audit(),
            verify_author_input_closure(),
            verify_metadata_closure_path(),
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
