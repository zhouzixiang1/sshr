#!/usr/bin/env python3
"""Round-trip audit for the deterministic submission payload archive.

This terminal audit opens the generated tarball, checks that the payload
manifest and archive contents agree, verifies every archived file hash, rejects
unsafe or private paths, and confirms deterministic tar metadata.  It does not
modify the payload archive.
"""
from __future__ import annotations

import csv
import json
import sys
import tarfile
from pathlib import Path

from make_submission_payload_archive import ARCHIVE, PAYLOAD_ROOT, THIS_DIR


RESULTS = THIS_DIR / "results"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"
PRIVATE_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}
REQUIRED_PAYLOAD_PATHS = {
    "paper_latex/resource_nmcts_submission_v1.tex",
    "paper_latex/resource_nmcts_submission_v1.pdf",
    "paper_latex/resource_nmcts_submission_anonymous.tex",
    "paper_latex/resource_nmcts_submission_anonymous.pdf",
    "paper_latex/resource_nmcts_submission_acm_tqc.tex",
    "paper_latex/resource_nmcts_submission_acm_tqc.pdf",
    "paper_latex/references.bib",
    "rebuild_submission_package.sh",
    "verify_submission_package.sh",
    "submission_package/README.md",
    "submission_package/AUTHOR_INPUT_REQUIRED.md",
    "submission_package/submission_checklist.md",
    "results/analysis_submission_archive_manifest.md",
    "results/analysis_submission_traceability_audit.md",
}
REVIEWER_ENTRYPOINT_PATHS = {
    "submission_package/artifact_reproduction_guide.md",
    "submission_package/editor_screening_brief.md",
    "submission_package/reviewer_concern_brief.md",
    "submission_package/target_venue_brief.md",
    "results/analysis_artifact_rerun_registry.md",
    "results/analysis_reproducibility_audit.md",
    "results/analysis_figure_asset_audit.md",
}
COMPARISON_PROTOCOL_PATHS = {
    "analyze_comparison_protocol_audit.py",
    "results/analysis_comparison_protocol_audit.md",
    "results/summary_comparison_protocol_audit.csv",
    "results/manifest_comparison_protocol_audit.json",
    "results/analysis_baseline_claim_matrix.md",
    "results/analysis_comparison_evidence_matrix.md",
    "results/analysis_baseline_comparability_audit.md",
    "results/analysis_counterpoint_claim_boundary.md",
    "results/analysis_paired_statistical_evidence.md",
    "results/analysis_multimetric_pareto_tradeoff.md",
    "paper_latex/tables/comparison_protocol_audit.tex",
}
COMPARISON_TARGET_VALIDITY_PATHS = {
    "analyze_comparison_target_validity_audit.py",
    "results/analysis_comparison_target_validity_audit.md",
    "results/summary_comparison_target_validity_audit.csv",
    "results/manifest_comparison_target_validity_audit.json",
    "paper_latex/tables/comparison_target_validity_audit.tex",
}
COMPARISON_ANSWER_SCORECARD_PATHS = {
    "analyze_comparison_answer_scorecard.py",
    "results/analysis_comparison_answer_scorecard.md",
    "results/summary_comparison_answer_scorecard.csv",
    "results/manifest_comparison_answer_scorecard.json",
    "paper_latex/tables/comparison_answer_scorecard.tex",
}
WEIGHT_ROBUSTNESS_PATHS = {
    "analyze_weight_robustness.py",
    "results/analysis_weight_robustness.md",
    "results/summary_weight_robustness.csv",
    "results/manifest_weight_robustness.json",
    "paper_latex/tables/weight_robustness_compact.tex",
}
RESOURCE_WEIGHT_SENSITIVITY_PATHS = {
    "analyze_resource_weight_sensitivity_audit.py",
    "results/raw_resource_weight_sensitivity_audit.csv",
    "results/analysis_resource_weight_sensitivity_audit.md",
    "results/summary_resource_weight_sensitivity_audit.csv",
    "results/manifest_resource_weight_sensitivity_audit.json",
    "paper_latex/tables/resource_weight_sensitivity_audit.tex",
}
NOVELTY_SCORECARD_PATHS = {
    "analyze_novelty_comparison_scorecard.py",
    "results/analysis_novelty_comparison_scorecard.md",
    "results/summary_novelty_comparison_scorecard.csv",
    "results/manifest_novelty_comparison_scorecard.json",
    "paper_latex/tables/novelty_comparison_scorecard.tex",
}
THREATS_VALIDITY_PATHS = {
    "analyze_threats_to_validity_audit.py",
    "results/analysis_threats_to_validity_audit.md",
    "results/summary_threats_to_validity_audit.csv",
    "results/manifest_threats_to_validity_audit.json",
    "paper_latex/tables/threats_to_validity_audit.tex",
}
ROS_GAP_PATHS = {
    "analyze_ros_lut_garbage_proxy.py",
    "analyze_ros_lut_garbage_budget_frontier.py",
    "analyze_ros_reproduction_gap_audit.py",
    "results/raw_ros_lut_garbage_proxy.csv",
    "results/raw_ros_lut_garbage_budget_frontier.csv",
    "results/analysis_ros_lut_garbage_proxy.md",
    "results/analysis_ros_lut_garbage_budget_frontier.md",
    "results/summary_ros_lut_garbage_proxy.csv",
    "results/summary_ros_lut_garbage_budget_frontier.csv",
    "results/manifest_ros_lut_garbage_proxy.json",
    "results/manifest_ros_lut_garbage_budget_frontier.json",
    "results/analysis_ros_reproduction_gap_audit.md",
    "results/summary_ros_reproduction_gap_audit.csv",
    "results/manifest_ros_reproduction_gap_audit.json",
    "paper_latex/tables/ros_lut_garbage_proxy.tex",
    "paper_latex/tables/ros_lut_garbage_budget_frontier.tex",
    "paper_latex/tables/ros_reproduction_gap_audit.tex",
}
STG_BENCHMARK_PATHS = {
    "analyze_stg_published_benchmark.py",
    "results/raw_stg_published_benchmark.csv",
    "results/analysis_stg_published_benchmark.md",
    "results/summary_stg_published_benchmark.csv",
    "results/manifest_stg_published_benchmark.json",
    "paper_latex/tables/stg_published_benchmark.tex",
}
SCHEDULE_PROXY_PATHS = {
    "analyze_schedule_metrics.py",
    "analyze_schedule_proxy_audit.py",
    "results/analysis_schedule_metrics.md",
    "results/summary_schedule_metrics.csv",
    "results/analysis_schedule_proxy_audit.md",
    "results/summary_schedule_proxy_audit.csv",
    "results/manifest_schedule_proxy_audit.json",
    "paper_latex/tables/schedule_proxy_audit.tex",
}
ULTRA_SCALE64_PATHS = {
    "run_screen_scale_terms.py",
    "analyze_ultra_scale64_stress.py",
    "analyze_ultra_scale64_resource_profile.py",
    "results/raw_screen_scale_ultra_scale64_terms.csv",
    "results/summary_screen_scale_ultra_scale64_terms.csv",
    "results/analysis_screen_scale_ultra_scale64_terms.md",
    "results/summary_screen_scale_ultra_scale64_stress.csv",
    "results/analysis_screen_scale_ultra_scale64_stress.md",
    "results/manifest_screen_scale_ultra_scale64_stress.json",
    "results/summary_screen_scale_ultra_scale64_resource_profile.csv",
    "results/summary_screen_scale_ultra_scale64_resource_deltas.csv",
    "results/analysis_screen_scale_ultra_scale64_resource_profile.md",
    "results/manifest_screen_scale_ultra_scale64_resource_profile.json",
    "paper_latex/tables/screen_scale_ultra_scale64_terms.tex",
    "paper_latex/tables/screen_scale_ultra_scale64_stress.tex",
    "paper_latex/tables/screen_scale_ultra_scale64_resource_profile.tex",
}
SEARCH_BUDGET_PATHS = {
    "analyze_search_budget_contract.py",
    "results/analysis_search_budget_contract.md",
    "results/summary_search_budget_contract.csv",
    "results/manifest_search_budget_contract.json",
    "paper_latex/tables/search_budget_contract.tex",
}
LEARNED_CONTROL_PATHS = {
    "analyze_learned_control_audit.py",
    "analyze_root_action_ranker_audit.py",
    "analyze_phase_rotation_precision_audit.py",
    "analyze_phase_rotation_sequence_smoke_audit.py",
    "analyze_phase_policy_budget_frontier.py",
    "results/analysis_learned_control_audit.md",
    "results/analysis_root_action_ranker_audit.md",
    "results/analysis_phase_rotation_precision_audit.md",
    "results/analysis_phase_rotation_sequence_smoke_audit.md",
    "results/analysis_phase_policy_budget_frontier.md",
    "results/raw_phase_rotation_sequence_smoke_audit.csv",
    "results/summary_learned_control_audit.csv",
    "results/summary_root_action_ranker_audit.csv",
    "results/summary_phase_rotation_precision_audit.csv",
    "results/summary_phase_rotation_sequence_smoke_audit.csv",
    "results/summary_phase_policy_budget_frontier.csv",
    "results/manifest_learned_control_audit.json",
    "results/manifest_root_action_ranker_audit.json",
    "results/manifest_phase_rotation_precision_audit.json",
    "results/manifest_phase_rotation_sequence_smoke_audit.json",
    "results/manifest_phase_policy_budget_frontier.json",
    "paper_latex/tables/learned_control_audit.tex",
    "paper_latex/tables/root_action_ranker_audit.tex",
    "paper_latex/tables/phase_rotation_precision_audit.tex",
    "paper_latex/tables/phase_rotation_sequence_smoke_audit.tex",
    "paper_latex/tables/phase_policy_budget_frontier.tex",
}
NEURAL_MCTS_CLAIM_CALIBRATION_PATHS = {
    "analyze_neural_mcts_claim_calibration.py",
    "results/analysis_neural_mcts_claim_calibration.md",
    "results/summary_neural_mcts_claim_calibration.csv",
    "results/manifest_neural_mcts_claim_calibration.json",
    "paper_latex/tables/neural_mcts_claim_calibration.tex",
}
BITFLIP_RANDOM_PRIOR_PATHS = {
    "run_bitflip_random_prior_control.py",
    "analyze_bitflip_random_prior_control.py",
    "results/raw_bitflip_random_prior_control.csv",
    "results/summary_bitflip_random_prior_control_run.csv",
    "results/manifest_bitflip_random_prior_control_run.json",
    "results/summary_bitflip_random_prior_control.csv",
    "results/analysis_bitflip_random_prior_control.md",
    "results/manifest_bitflip_random_prior_control.json",
    "paper_latex/tables/bitflip_random_prior_control.tex",
}
BITFLIP_NEURAL_BUDGET_PATHS = {
    "run_bitflip_neural_budget_sweep.py",
    "analyze_bitflip_neural_budget_sweep.py",
    "results/raw_bitflip_neural_budget_sweep.csv",
    "results/summary_bitflip_neural_budget_sweep_run.csv",
    "results/manifest_bitflip_neural_budget_sweep_run.json",
    "results/summary_bitflip_neural_budget_sweep.csv",
    "results/analysis_bitflip_neural_budget_sweep.md",
    "results/manifest_bitflip_neural_budget_sweep.json",
    "paper_latex/tables/bitflip_neural_budget_sweep.tex",
}
FRONTIER_RANDOM_DEPTH_PATHS = {
    "analyze_frontier_random_depth_control.py",
    "results/summary_frontier_random_depth_control.csv",
    "results/analysis_frontier_random_depth_control.md",
    "results/manifest_frontier_random_depth_control.json",
    "paper_latex/tables/frontier_random_depth_control.tex",
}
HEADLINE_NUMERIC_PATHS = {
    "analyze_headline_numeric_consistency.py",
    "results/analysis_headline_numeric_consistency.md",
    "results/summary_headline_numeric_consistency.csv",
    "results/manifest_headline_numeric_consistency.json",
}
CITATION_SUPPORT_PATHS = {
    "analyze_citation_support_audit.py",
    "results/analysis_citation_support_audit.md",
    "results/summary_citation_support_audit.csv",
    "results/manifest_citation_support_audit.json",
}
EDITORIAL_SCREENING_PATHS = {
    "analyze_editorial_screening_audit.py",
    "results/analysis_editorial_screening_audit.md",
    "results/summary_editorial_screening_audit.csv",
    "results/manifest_editorial_screening_audit.json",
    "paper_latex/tables/editorial_screening_audit.tex",
}
TARGET_VENUE_DECISION_PATHS = {
    "analyze_target_venue_decision_audit.py",
    "results/analysis_target_venue_decision_audit.md",
    "results/summary_target_venue_decision_audit.csv",
    "results/manifest_target_venue_decision_audit.json",
    "paper_latex/tables/target_venue_decision_audit.tex",
}
TARGET_VENUE_FORMAT_PATHS = {
    "make_acm_tqc_review_draft.py",
    "analyze_target_venue_format_smoke.py",
    "paper_latex/resource_nmcts_submission_acm_tqc.tex",
    "paper_latex/resource_nmcts_submission_acm_tqc.pdf",
    "results/analysis_target_venue_format_smoke.md",
    "results/summary_target_venue_format_smoke.csv",
    "results/manifest_target_venue_format_smoke.json",
}
SUPPORT_PACKET_PATHS = {
    "analyze_submission_support_packet_audit.py",
    "submission_package/COMPARISON_HANDOFF_zh.md",
    "results/analysis_submission_support_packet_audit.md",
    "results/summary_submission_support_packet_audit.csv",
    "results/manifest_submission_support_packet_audit.json",
    "paper_latex/tables/submission_support_packet_audit.tex",
}
AUTHOR_INPUT_CLOSURE_PATHS = {
    "analyze_author_input_closure_audit.py",
    "results/analysis_author_input_closure_audit.md",
    "results/summary_author_input_closure_audit.csv",
    "results/manifest_author_input_closure_audit.json",
}
METADATA_CLOSURE_PATHS = {
    "analyze_submission_metadata_closure_path.py",
    "results/analysis_submission_metadata_closure_path.md",
    "results/summary_submission_metadata_closure_path.csv",
    "results/manifest_submission_metadata_closure_path.json",
}
SOURCE_PATH_PRIVACY_PATHS = {
    "analyze_source_path_privacy_audit.py",
}
PAYLOAD_GIT_POLICY_PATHS = {
    "analyze_payload_git_policy_audit.py",
}
PAYLOAD_EXTRACTION_SMOKE_PATHS = {
    "analyze_payload_extraction_smoke_audit.py",
}
PAYLOAD_VERIFIER_SMOKE_PATHS = {
    "analyze_payload_verifier_smoke_audit.py",
}


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def safe_payload_path(path: str) -> bool:
    if path.startswith("/") or path.startswith("../") or "/../" in path:
        return False
    if path == "." or path.endswith("/"):
        return False
    parts = path.split("/")
    return "__MACOSX" not in parts and ".DS_Store" not in parts


def load_archive_members() -> tuple[list[tarfile.TarInfo], dict[str, bytes], str]:
    if not ARCHIVE.exists():
        return [], {}, "archive missing"
    try:
        members: list[tarfile.TarInfo] = []
        payload: dict[str, bytes] = {}
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for member in tar.getmembers():
                members.append(member)
                if not member.isfile():
                    continue
                extracted = tar.extractfile(member)
                payload[member.name] = extracted.read() if extracted is not None else b""
        return members, payload, ""
    except Exception as exc:
        return [], {}, f"{type(exc).__name__}: {exc}"


def build_rows() -> list[dict[str, str]]:
    manifest = read_json(PAYLOAD_MANIFEST)
    manifest_files = manifest.get("files", []) if manifest else []
    members, payload, archive_error = load_archive_members()
    rows: list[dict[str, str]] = []

    rows.append(
        row(
            "Payload archive readable",
            "pass" if not archive_error and members else "needs revision",
            f"archive={rel(ARCHIVE)}; members={len(members)}; error={archive_error or 'none'}.",
            "Regenerate the payload archive if it cannot be opened by Python tarfile.",
        )
    )

    archive_paths = sorted(path.removeprefix(f"{PAYLOAD_ROOT}/") for path in payload if path.startswith(f"{PAYLOAD_ROOT}/"))
    manifest_paths: list[str] = []
    manifest_sha: dict[str, str] = {}
    if isinstance(manifest_files, list):
        for item in manifest_files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            manifest_paths.append(path)
            manifest_sha[path] = str(item.get("sha256", ""))
    manifest_paths = sorted(manifest_paths)

    missing_from_archive = sorted(set(manifest_paths) - set(archive_paths))
    extra_in_archive = sorted(set(archive_paths) - set(manifest_paths))
    rows.append(
        row(
            "Payload manifest round-trip",
            "pass" if manifest and not missing_from_archive and not extra_in_archive else "needs revision",
            f"manifest_files={len(manifest_paths)}; archive_files={len(archive_paths)}; missing={missing_from_archive[:5] or 'none'}; extra={extra_in_archive[:5] or 'none'}.",
            "Regenerate make_submission_payload_archive.py outputs if manifest and archive contents diverge.",
        )
    )

    import hashlib

    mismatches: list[str] = []
    for path in manifest_paths:
        data = payload.get(f"{PAYLOAD_ROOT}/{path}")
        if data is None:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest_sha.get(path):
            mismatches.append(path)
    rows.append(
        row(
            "Payload per-file SHA256",
            "pass" if not mismatches else "needs revision",
            f"checked={len(manifest_paths) - len(missing_from_archive)}; mismatches={mismatches[:5] or 'none'}.",
            "Regenerate the payload archive and manifest if any archived file digest differs from the manifest.",
        )
    )

    unsafe = sorted(name for name in payload if not name.startswith(f"{PAYLOAD_ROOT}/") or not safe_payload_path(name.removeprefix(f"{PAYLOAD_ROOT}/")))
    private_hits = sorted(path for path in archive_paths if Path(path).name in PRIVATE_BASENAMES)
    rows.append(
        row(
            "Payload path hygiene",
            "pass" if not unsafe and not private_hits else "needs revision",
            f"unsafe_paths={unsafe[:5] or 'none'}; private_hits={private_hits or 'none'}.",
            "Remove unsafe, platform-generated, or private files from the payload inputs.",
        )
    )

    required_missing = sorted(REQUIRED_PAYLOAD_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload required artifacts",
            "pass" if not required_missing else "needs revision",
            f"required={len(REQUIRED_PAYLOAD_PATHS)}; missing={required_missing or 'none'}.",
            "Ensure the uploadable archive includes manuscript, bibliography, rebuild/verify scripts, handoff docs, and submission audits.",
        )
    )

    entry_missing = sorted(REVIEWER_ENTRYPOINT_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload reviewer entrypoints",
            "pass" if not entry_missing else "needs revision",
            f"reviewer_entries={len(REVIEWER_ENTRYPOINT_PATHS)}; missing={entry_missing or 'none'}.",
            "Ensure the uploadable archive includes reviewer-facing guide, editor/reviewer briefs, venue brief, registry, and reproducibility audit.",
        )
    )

    comparison_missing = sorted(COMPARISON_PROTOCOL_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload comparison protocol evidence",
            "pass" if not comparison_missing else "needs revision",
            f"comparison_protocol_files={len(COMPARISON_PROTOCOL_PATHS)}; missing={comparison_missing or 'none'}.",
            "Ensure the uploadable archive includes the comparison protocol audit plus its claim, evidence, comparability, counterpoint, statistical, and tradeoff sources.",
        )
    )

    comparison_target_validity_missing = sorted(COMPARISON_TARGET_VALIDITY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload comparison target validity evidence",
            "pass" if not comparison_target_validity_missing else "needs revision",
            f"comparison_target_validity_files={len(COMPARISON_TARGET_VALIDITY_PATHS)}; missing={comparison_target_validity_missing or 'none'}.",
            "Ensure the uploadable archive includes the comparison target validity audit script, generated evidence, and manuscript table.",
        )
    )

    comparison_answer_missing = sorted(COMPARISON_ANSWER_SCORECARD_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload comparison answer scorecard",
            "pass" if not comparison_answer_missing else "needs revision",
            f"comparison_answer_files={len(COMPARISON_ANSWER_SCORECARD_PATHS)}; missing={comparison_answer_missing or 'none'}.",
            "Ensure the uploadable archive includes the comparison answer scorecard script, generated evidence, and manuscript table.",
        )
    )

    weight_robustness_missing = sorted(WEIGHT_ROBUSTNESS_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload score-weight robustness evidence",
            "pass" if not weight_robustness_missing else "needs revision",
            f"weight_robustness_files={len(WEIGHT_ROBUSTNESS_PATHS)}; missing={weight_robustness_missing or 'none'}.",
            "Ensure the uploadable archive includes the score-weight robustness script, generated evidence, manifest, and manuscript table.",
        )
    )

    resource_weight_missing = sorted(RESOURCE_WEIGHT_SENSITIVITY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload resource-weight sensitivity evidence",
            "pass" if not resource_weight_missing else "needs revision",
            f"resource_weight_sensitivity_files={len(RESOURCE_WEIGHT_SENSITIVITY_PATHS)}; missing={resource_weight_missing or 'none'}.",
            "Ensure the uploadable archive includes the broader resource-weight sensitivity audit script, raw rows, generated evidence, manifest, and manuscript table.",
        )
    )

    novelty_missing = sorted(NOVELTY_SCORECARD_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload novelty/comparison scorecard",
            "pass" if not novelty_missing else "needs revision",
            f"novelty_scorecard_files={len(NOVELTY_SCORECARD_PATHS)}; missing={novelty_missing or 'none'}.",
            "Ensure the uploadable archive includes the novelty/comparison scorecard script, generated evidence, and manuscript table.",
        )
    )

    threats_missing = sorted(THREATS_VALIDITY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload threats-to-validity audit",
            "pass" if not threats_missing else "needs revision",
            f"threats_validity_files={len(THREATS_VALIDITY_PATHS)}; missing={threats_missing or 'none'}.",
            "Ensure the uploadable archive includes the threats-to-validity audit script, generated evidence, and manuscript table.",
        )
    )

    ros_gap_missing = sorted(ROS_GAP_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload ROS reproduction-boundary evidence",
            "pass" if not ros_gap_missing else "needs revision",
            f"ros_gap_files={len(ROS_GAP_PATHS)}; missing={ros_gap_missing or 'none'}.",
            "Ensure the uploadable archive includes the ROS reproduction gap audit script, generated evidence, and support table.",
        )
    )

    stg_missing = sorted(STG_BENCHMARK_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload published STG counterpoint",
            "pass" if not stg_missing else "needs revision",
            f"stg_benchmark_files={len(STG_BENCHMARK_PATHS)}; missing={stg_missing or 'none'}.",
            "Ensure the uploadable archive includes the STG counterpoint script, raw rows, generated evidence, manifest, and manuscript table.",
        )
    )

    schedule_proxy_missing = sorted(SCHEDULE_PROXY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload schedule-proxy evidence",
            "pass" if not schedule_proxy_missing else "needs revision",
            f"schedule_proxy_files={len(SCHEDULE_PROXY_PATHS)}; missing={schedule_proxy_missing or 'none'}.",
            "Ensure the uploadable archive includes the schedule metrics scripts, compact audit outputs, and manuscript schedule-proxy table.",
        )
    )

    ultra_scale64_missing = sorted(ULTRA_SCALE64_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload ultra-scale n=48--64 evidence",
            "pass" if not ultra_scale64_missing else "needs revision",
            f"ultra_scale64_files={len(ULTRA_SCALE64_PATHS)}; missing={ultra_scale64_missing or 'none'}.",
            "Ensure the uploadable archive includes the n=48--64 raw term-set stress rows, compact audit, and manuscript tables.",
        )
    )

    search_budget_missing = sorted(SEARCH_BUDGET_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload search-budget contract evidence",
            "pass" if not search_budget_missing else "needs revision",
            f"search_budget_files={len(SEARCH_BUDGET_PATHS)}; missing={search_budget_missing or 'none'}.",
            "Ensure the uploadable archive includes the search-budget contract script, generated evidence, and manuscript table.",
        )
    )

    learned_control_missing = sorted(LEARNED_CONTROL_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload learned-control evidence",
            "pass" if not learned_control_missing else "needs revision",
            f"learned_control_files={len(LEARNED_CONTROL_PATHS)}; missing={learned_control_missing or 'none'}.",
            "Ensure the uploadable archive includes the learned-control audit script, generated evidence, manifest, and manuscript table.",
        )
    )

    neural_mcts_missing = sorted(NEURAL_MCTS_CLAIM_CALIBRATION_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload neural/MCTS claim calibration",
            "pass" if not neural_mcts_missing else "needs revision",
            f"neural_mcts_claim_calibration_files={len(NEURAL_MCTS_CLAIM_CALIBRATION_PATHS)}; missing={neural_mcts_missing or 'none'}.",
            "Ensure the uploadable archive includes the neural/MCTS claim-calibration script, generated evidence, manifest, and manuscript table.",
        )
    )

    bitflip_random_missing = sorted(BITFLIP_RANDOM_PRIOR_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload bit-flip random-prior evidence",
            "pass" if not bitflip_random_missing else "needs revision",
            f"bitflip_random_prior_files={len(BITFLIP_RANDOM_PRIOR_PATHS)}; missing={bitflip_random_missing or 'none'}.",
            "Ensure the uploadable archive includes the bit-flip random-prior run script, analysis outputs, raw CSV, and manuscript table.",
        )
    )

    bitflip_budget_missing = sorted(BITFLIP_NEURAL_BUDGET_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload bit-flip low-budget learned-prior evidence",
            "pass" if not bitflip_budget_missing else "needs revision",
            f"bitflip_neural_budget_files={len(BITFLIP_NEURAL_BUDGET_PATHS)}; missing={bitflip_budget_missing or 'none'}.",
            "Ensure the uploadable archive includes the low-budget learned-prior run script, raw rows, analysis outputs, and manuscript table.",
        )
    )

    frontier_random_missing = sorted(FRONTIER_RANDOM_DEPTH_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload frontier random-depth evidence",
            "pass" if not frontier_random_missing else "needs revision",
            f"frontier_random_depth_files={len(FRONTIER_RANDOM_DEPTH_PATHS)}; missing={frontier_random_missing or 'none'}.",
            "Ensure the uploadable archive includes the frontier random-depth analysis script, generated evidence, and manuscript table.",
        )
    )

    headline_missing = sorted(HEADLINE_NUMERIC_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload headline numeric evidence",
            "pass" if not headline_missing else "needs revision",
            f"headline_numeric_files={len(HEADLINE_NUMERIC_PATHS)}; missing={headline_missing or 'none'}.",
            "Ensure the uploadable archive includes the headline numeric audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    citation_missing = sorted(CITATION_SUPPORT_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload citation support evidence",
            "pass" if not citation_missing else "needs revision",
            f"citation_support_files={len(CITATION_SUPPORT_PATHS)}; missing={citation_missing or 'none'}.",
            "Ensure the uploadable archive includes the citation support audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    editorial_missing = sorted(EDITORIAL_SCREENING_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload editorial screening evidence",
            "pass" if not editorial_missing else "needs revision",
            f"editorial_screening_files={len(EDITORIAL_SCREENING_PATHS)}; missing={editorial_missing or 'none'}.",
            "Ensure the uploadable archive includes the editorial screening audit script, generated evidence, and support table.",
        )
    )

    target_venue_missing = sorted(TARGET_VENUE_DECISION_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload target-venue decision evidence",
            "pass" if not target_venue_missing else "needs revision",
            f"target_venue_decision_files={len(TARGET_VENUE_DECISION_PATHS)}; missing={target_venue_missing or 'none'}.",
            "Ensure the uploadable archive includes the target-venue decision audit script, generated evidence, and support table.",
        )
    )

    target_format_missing = sorted(TARGET_VENUE_FORMAT_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload target-venue ACM/TQC format evidence",
            "pass" if not target_format_missing else "needs revision",
            f"target_venue_format_files={len(TARGET_VENUE_FORMAT_PATHS)}; missing={target_format_missing or 'none'}.",
            "Ensure the uploadable archive includes the ACM/TQC generated review source, compiled PDF, and format smoke audit.",
        )
    )

    support_packet_missing = sorted(SUPPORT_PACKET_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload support packet evidence",
            "pass" if not support_packet_missing else "needs revision",
            f"support_packet_files={len(SUPPORT_PACKET_PATHS)}; missing={support_packet_missing or 'none'}.",
            "Ensure the uploadable archive includes the support packet audit script, generated evidence, and support table.",
        )
    )

    author_input_missing = sorted(AUTHOR_INPUT_CLOSURE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload author-input closure evidence",
            "pass" if not author_input_missing else "needs revision",
            f"author_input_closure_files={len(AUTHOR_INPUT_CLOSURE_PATHS)}; missing={author_input_missing or 'none'}.",
            "Ensure the uploadable archive includes the author-input closure audit script and generated CSV/Markdown/JSON evidence.",
        )
    )

    metadata_closure_missing = sorted(METADATA_CLOSURE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload metadata closure-path evidence",
            "pass" if not metadata_closure_missing else "needs revision",
            f"metadata_closure_files={len(METADATA_CLOSURE_PATHS)}; missing={metadata_closure_missing or 'none'}.",
            "Ensure the uploadable archive includes the final metadata closure-path audit script and generated evidence.",
        )
    )

    source_path_missing = sorted(SOURCE_PATH_PRIVACY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload source/path privacy executable",
            "pass" if not source_path_missing else "needs revision",
            f"source_path_privacy_scripts={len(SOURCE_PATH_PRIVACY_PATHS)}; missing={source_path_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes source/path privacy audit code; generated terminal outputs are intentionally excluded and reproduced by the extracted-payload smoke test.",
        )
    )

    payload_git_policy_missing = sorted(PAYLOAD_GIT_POLICY_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload Git-policy executable",
            "pass" if not payload_git_policy_missing else "needs revision",
            f"payload_git_policy_scripts={len(PAYLOAD_GIT_POLICY_PATHS)}; missing={payload_git_policy_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes payload Git-policy audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree.",
        )
    )

    extraction_smoke_missing = sorted(PAYLOAD_EXTRACTION_SMOKE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload extraction smoke executable",
            "pass" if not extraction_smoke_missing else "needs revision",
            f"payload_extraction_smoke_scripts={len(PAYLOAD_EXTRACTION_SMOKE_PATHS)}; missing={extraction_smoke_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes the extraction smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree.",
        )
    )

    verifier_smoke_missing = sorted(PAYLOAD_VERIFIER_SMOKE_PATHS - set(archive_paths))
    rows.append(
        row(
            "Payload verifier smoke executable",
            "pass" if not verifier_smoke_missing else "needs revision",
            f"payload_verifier_smoke_scripts={len(PAYLOAD_VERIFIER_SMOKE_PATHS)}; missing={verifier_smoke_missing or 'none'}; terminal_outputs_excluded=3.",
            "Ensure the uploadable archive includes the verifier smoke audit code; generated terminal outputs are intentionally excluded and regenerated from the source tree.",
        )
    )

    metadata_bad: list[str] = []
    for member in members:
        if not member.name.startswith(f"{PAYLOAD_ROOT}/"):
            metadata_bad.append(f"{member.name}:root")
        if member.mtime != 0:
            metadata_bad.append(f"{member.name}:mtime={member.mtime}")
        if member.uid != 0 or member.gid != 0:
            metadata_bad.append(f"{member.name}:uidgid={member.uid}/{member.gid}")
        if member.uname or member.gname:
            metadata_bad.append(f"{member.name}:names")
        if member.isfile():
            expected_mode = 0o755 if member.name.endswith(".sh") else 0o644
            if member.mode != expected_mode:
                metadata_bad.append(f"{member.name}:mode={oct(member.mode)}")
    rows.append(
        row(
            "Payload deterministic tar metadata",
            "pass" if not metadata_bad else "needs revision",
            f"members_checked={len(members)}; metadata_issues={metadata_bad[:5] or 'none'}.",
            "Keep tar member mtime/uid/gid/user/group/mode normalized for deterministic payloads.",
        )
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
        "# Payload Round-Trip Audit",
        "",
        "This terminal audit opens the reviewer/upload tarball and checks manifest agreement, per-file hashes, path hygiene, required artifacts, and deterministic tar metadata.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "required_payload_paths": sorted(REQUIRED_PAYLOAD_PATHS),
        "reviewer_entrypoint_paths": sorted(REVIEWER_ENTRYPOINT_PATHS),
        "comparison_protocol_paths": sorted(COMPARISON_PROTOCOL_PATHS),
        "comparison_target_validity_paths": sorted(COMPARISON_TARGET_VALIDITY_PATHS),
        "comparison_answer_scorecard_paths": sorted(COMPARISON_ANSWER_SCORECARD_PATHS),
        "weight_robustness_paths": sorted(WEIGHT_ROBUSTNESS_PATHS),
        "resource_weight_sensitivity_paths": sorted(RESOURCE_WEIGHT_SENSITIVITY_PATHS),
        "threats_validity_paths": sorted(THREATS_VALIDITY_PATHS),
        "ros_gap_paths": sorted(ROS_GAP_PATHS),
        "stg_benchmark_paths": sorted(STG_BENCHMARK_PATHS),
        "schedule_proxy_paths": sorted(SCHEDULE_PROXY_PATHS),
        "search_budget_paths": sorted(SEARCH_BUDGET_PATHS),
        "learned_control_paths": sorted(LEARNED_CONTROL_PATHS),
        "neural_mcts_claim_calibration_paths": sorted(NEURAL_MCTS_CLAIM_CALIBRATION_PATHS),
        "bitflip_random_prior_paths": sorted(BITFLIP_RANDOM_PRIOR_PATHS),
        "bitflip_neural_budget_paths": sorted(BITFLIP_NEURAL_BUDGET_PATHS),
        "frontier_random_depth_paths": sorted(FRONTIER_RANDOM_DEPTH_PATHS),
        "headline_numeric_paths": sorted(HEADLINE_NUMERIC_PATHS),
        "citation_support_paths": sorted(CITATION_SUPPORT_PATHS),
        "editorial_screening_paths": sorted(EDITORIAL_SCREENING_PATHS),
        "target_venue_decision_paths": sorted(TARGET_VENUE_DECISION_PATHS),
        "target_venue_format_paths": sorted(TARGET_VENUE_FORMAT_PATHS),
        "support_packet_paths": sorted(SUPPORT_PACKET_PATHS),
        "author_input_closure_paths": sorted(AUTHOR_INPUT_CLOSURE_PATHS),
        "payload_extraction_smoke_paths": sorted(PAYLOAD_EXTRACTION_SMOKE_PATHS),
        "payload_verifier_smoke_paths": sorted(PAYLOAD_VERIFIER_SMOKE_PATHS),
        "private_basenames": sorted(PRIVATE_BASENAMES),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_payload_roundtrip_audit.csv"),
            "analysis": rel(RESULTS / "analysis_payload_roundtrip_audit.md"),
            "manifest": rel(RESULTS / "manifest_payload_roundtrip_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_roundtrip_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_roundtrip_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_roundtrip_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload round-trip audit row(s)")
    if failures:
        print(f"warning: {failures} payload round-trip row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
