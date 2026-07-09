#!/usr/bin/env python3
"""Create a reviewer-facing registry for raw rerun entry points.

The registry maps evidence families to driver scripts, existing raw CSVs,
manifest files, and dependency boundaries.  It is an artifact guide rather
than a scientific result: its purpose is to make clear which claims are
verified by the lightweight rebuild and which require heavier raw reruns or
external tools.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class EvidenceFamily:
    family: str
    claim_use: str
    rerun_tier: str
    scripts: tuple[str, ...]
    raw_patterns: tuple[str, ...]
    manifest_patterns: tuple[str, ...]
    summary_patterns: tuple[str, ...]
    analysis_patterns: tuple[str, ...]
    dependency_boundary: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def collect_result(patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in RESULTS.glob(pattern) if path.is_file())
    return sorted(set(files), key=rel)


def script_paths(names: tuple[str, ...]) -> list[Path]:
    return [THIS_DIR / name for name in names]


def csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def raw_row_count(files: list[Path]) -> int:
    return sum(csv_rows(path) for path in files)


def unique_registry_raw_files() -> list[Path]:
    files: set[Path] = set()
    for spec in specs():
        files.update(collect_result(spec.raw_patterns))
    return sorted(files, key=rel)


def paths_text(files: list[Path], limit: int = 4) -> str:
    if not files:
        return ""
    shown = [rel(path) for path in files[:limit]]
    if len(files) > limit:
        shown.append(f"+{len(files) - limit} more")
    return "; ".join(shown)


def specs() -> list[EvidenceFamily]:
    return [
        EvidenceFamily(
            family="Lightweight paper-facing rebuild",
            claim_use="Regenerates manuscript-facing analyses, figures, audits, PDF, archive manifest, and payload from existing artifacts.",
            rerun_tier="quick rebuild",
            scripts=("rebuild_submission_package.sh",),
            raw_patterns=(),
            manifest_patterns=("manifest_submission_*.json", "manifest_goal_completion_audit.json"),
            summary_patterns=("summary_submission_*.csv", "summary_goal_completion_audit.csv"),
            analysis_patterns=("analysis_submission_*.md", "analysis_goal_completion_audit.md"),
            dependency_boundary="Python, latexmk, existing raw artifacts, and the bounded local Caterpillar API check; does not rerun heavy raw sweeps, neural training jobs, or full external-toolchain reproductions.",
        ),
        EvidenceFamily(
            family="Submission metadata closure path",
            claim_use="Verifies that the remaining author/venue metadata step is explicit, private, ignored by Git, and machine-checkable.",
            rerun_tier="quick metadata audit",
            scripts=(
                "analyze_submission_metadata_closure_path.py",
                "analyze_author_minimal_form_coverage.py",
                "analyze_metadata_answer_template_coverage.py",
                "make_submission_metadata_from_answers.py",
                "make_submission_metadata_starter.py",
                "validate_submission_metadata.py",
                "make_submission_text_preview.py",
                "analyze_final_human_gate_audit.py",
            ),
            raw_patterns=(),
            manifest_patterns=(
                "manifest_submission_metadata_closure_path.json",
                "manifest_author_minimal_form_coverage.json",
                "manifest_metadata_answer_template_coverage.json",
                "manifest_final_human_gate_audit.json",
            ),
            summary_patterns=(
                "summary_submission_metadata_closure_path.csv",
                "summary_author_minimal_form_coverage.csv",
                "summary_metadata_answer_template_coverage.csv",
                "summary_final_human_gate_audit.csv",
            ),
            analysis_patterns=(
                "analysis_submission_metadata_closure_path.md",
                "analysis_author_minimal_form_coverage.md",
                "analysis_metadata_answer_template_coverage.md",
                "analysis_final_human_gate_audit.md",
            ),
            dependency_boundary="Does not require private author metadata; verifies the public minimal response form, short-answer template, safe starter-only public fields, and ignored private-output path before author approval.",
        ),
        EvidenceFamily(
            family="Generated payload Git policy",
            claim_use="Verifies that the upload tarball is generated and SHA-checked locally while remaining ignored and untracked in Git.",
            rerun_tier="quick package audit",
            scripts=("analyze_payload_git_policy_audit.py",),
            raw_patterns=(),
            manifest_patterns=("manifest_payload_git_policy_audit.json",),
            summary_patterns=("summary_payload_git_policy_audit.csv",),
            analysis_patterns=("analysis_payload_git_policy_audit.md",),
            dependency_boundary="Requires a freshly built local tarball; the tarball itself is not versioned and is regenerated by rebuild_submission_package.sh.",
        ),
        EvidenceFamily(
            family="Editorial screening and reviewer-risk support",
            claim_use="Verifies that the editor/reviewer support package exposes scope, novelty, comparison, counterpoint, AI, scale, validity-threat, reproducibility, and author-gate boundaries.",
            rerun_tier="quick submission-support audit",
            scripts=("analyze_editorial_screening_audit.py", "analyze_threats_to_validity_audit.py"),
            raw_patterns=(),
            manifest_patterns=("manifest_editorial_screening_audit.json", "manifest_threats_to_validity_audit.json"),
            summary_patterns=("summary_editorial_screening_audit.csv", "summary_threats_to_validity_audit.csv"),
            analysis_patterns=("analysis_editorial_screening_audit.md", "analysis_threats_to_validity_audit.md"),
            dependency_boundary="Does not change scientific results; checks public submission-support consistency against existing audit outputs.",
        ),
        EvidenceFamily(
            family="Cover-letter and venue support packet",
            claim_use="Verifies that cover letter, declarations, venue brief, target-venue decision support, ACM/TQC format smoke, upload checklist, and handoff docs preserve claim boundaries and author-gated metadata.",
            rerun_tier="quick submission-support audit",
            scripts=(
                "analyze_comparison_support_reference_integrity.py",
                "make_acm_tqc_review_draft.py",
                "analyze_target_venue_decision_audit.py",
                "analyze_target_venue_format_smoke.py",
                "analyze_submission_support_packet_audit.py",
            ),
            raw_patterns=(),
            manifest_patterns=(
                "manifest_target_venue_decision_audit.json",
                "manifest_target_venue_format_smoke.json",
                "manifest_comparison_support_reference_integrity.json",
                "manifest_submission_support_packet_audit.json",
            ),
            summary_patterns=(
                "summary_target_venue_decision_audit.csv",
                "summary_target_venue_format_smoke.csv",
                "summary_comparison_support_reference_integrity.csv",
                "summary_submission_support_packet_audit.csv",
            ),
            analysis_patterns=(
                "analysis_target_venue_decision_audit.md",
                "analysis_target_venue_format_smoke.md",
                "analysis_comparison_support_reference_integrity.md",
                "analysis_submission_support_packet_audit.md",
            ),
            dependency_boundary="Does not choose a venue or fill private metadata; checks public upload-support consistency, comparison evidence-entrypoint integrity, and ACM/TQC template smoke compilation against existing audits.",
        ),
        EvidenceFamily(
            family="Public handoff freshness",
            claim_use="Verifies that public Chinese handoff, deliverable, and upload-checklist snapshots match current terminal audit counts.",
            rerun_tier="quick submission-support audit",
            scripts=("analyze_public_handoff_freshness_audit.py",),
            raw_patterns=(),
            manifest_patterns=("manifest_public_handoff_freshness_audit.json",),
            summary_patterns=("summary_public_handoff_freshness_audit.csv",),
            analysis_patterns=("analysis_public_handoff_freshness_audit.md",),
            dependency_boundary="Does not change scientific results; checks that public handoff counters are refreshed after rebuilds.",
        ),
        EvidenceFamily(
            family="Runtime envelope and execution cost",
            claim_use="Consolidates workstation wall-clock evidence for small benchmarks, external probes, high-dimensional symbolic rows, truth-bridge rows, and learned-control rows.",
            rerun_tier="quick derived audit",
            scripts=("analyze_runtime_envelope_audit.py",),
            raw_patterns=(
                "raw_traditional_resource.csv",
                "raw_ros_lut_proxy_best.csv",
                "raw_caterpillar_xag_api_best.csv",
                "raw_mockturtle_xag_probe.csv",
                "raw_cirkit_aig_probe.csv",
                "raw_revkit_cli_multiflow_traditional.csv",
                "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
                "raw_screen_scale_ultra_scale64_terms.csv",
                "raw_truth_bridge*.csv",
                "raw_bitflip_neural_budget_sweep.csv",
            ),
            manifest_patterns=("manifest_runtime_envelope_audit.json",),
            summary_patterns=("summary_runtime_envelope_audit.csv",),
            analysis_patterns=("analysis_runtime_envelope_audit.md",),
            dependency_boundary="Derived from existing raw timing columns; it records workstation feasibility and does not claim portable runtime speedups.",
        ),
        EvidenceFamily(
            family="Method workflow, algorithm, and budget contracts",
            claim_use="Verifies that the method description is connected to executable stages, source anchors, semantic/resource guarantees, and explicit search budgets.",
            rerun_tier="quick method audit",
            scripts=("analyze_method_workflow_table.py", "analyze_algorithm_contract_table.py", "analyze_search_budget_contract.py"),
            raw_patterns=(),
            manifest_patterns=("manifest_algorithm_contract.json", "manifest_search_budget_contract.json"),
            summary_patterns=("summary_method_workflow.csv", "summary_algorithm_contract.csv", "summary_search_budget_contract.csv"),
            analysis_patterns=("analysis_method_workflow.md", "analysis_algorithm_contract.md", "analysis_search_budget_contract.md"),
            dependency_boundary="Quick derived audit; checks implementation anchors and manuscript method exposition, not raw benchmark outcomes.",
        ),
        EvidenceFamily(
            family="Comparison protocol and claim boundaries",
            claim_use="Verifies the reviewer-facing baseline roles, evidence layers, comparability limits, counterpoints, and manuscript table.",
            rerun_tier="quick comparison audit",
            scripts=(
                "analyze_baseline_claim_matrix.py",
                "analyze_comparison_evidence_matrix.py",
                "analyze_baseline_comparability_audit.py",
                "analyze_counterpoint_claim_boundary.py",
                "analyze_comparison_protocol_audit.py",
                "analyze_comparison_target_validity_audit.py",
                "analyze_comparison_answer_scorecard.py",
                "analyze_comparison_route_decision_audit.py",
            ),
            raw_patterns=(),
            manifest_patterns=(
                "manifest_comparison_protocol_audit.json",
                "manifest_comparison_target_validity_audit.json",
                "manifest_comparison_answer_scorecard.json",
                "manifest_comparison_route_decision_audit.json",
            ),
            summary_patterns=(
                "summary_baseline_claim_matrix.csv",
                "summary_comparison_evidence_matrix.csv",
                "summary_baseline_comparability_audit.csv",
                "summary_counterpoint_claim_boundary.csv",
                "summary_comparison_protocol_audit.csv",
                "summary_comparison_target_validity_audit.csv",
                "summary_comparison_answer_scorecard.csv",
                "summary_comparison_route_decision_audit.csv",
            ),
            analysis_patterns=(
                "analysis_baseline_claim_matrix.md",
                "analysis_comparison_evidence_matrix.md",
                "analysis_baseline_comparability_audit.md",
                "analysis_counterpoint_claim_boundary.md",
                "analysis_comparison_protocol_audit.md",
                "analysis_comparison_target_validity_audit.md",
                "analysis_comparison_answer_scorecard.md",
                "analysis_comparison_route_decision_audit.md",
            ),
            dependency_boundary="Quick derived audit; it supports comparison wording but does not rerun raw baseline sweeps.",
        ),
        EvidenceFamily(
            family="Benchmark suite composition and representativeness",
            claim_use="Summarizes benchmark-family roles, n ranges, instance counts, raw/verified rows, verification routes, function-structure diversity, and residual representativeness boundaries.",
            rerun_tier="quick benchmark audit",
            scripts=("analyze_benchmark_suite_audit.py", "analyze_benchmark_function_diversity_audit.py"),
            raw_patterns=(
                "raw_traditional_resource.csv",
                "raw_external_traditional_resource_n*.csv",
                "raw_stg_published_benchmark.csv",
                "raw_ros_lut_proxy_best.csv",
                "raw_mockturtle_xag*.csv",
                "raw_caterpillar_xag_api_best.csv",
                "raw_cirkit_aig*.csv",
                "raw_revkit_*.csv",
                "raw_phase_*.csv",
                "raw_screen_scale*_terms.csv",
                "raw_truth_bridge*_terms.csv",
                "raw_schedule_truth_bridge*_terms.csv",
                "raw_bitflip_*.csv",
                "raw_sparse_depth4_gate_generalization.csv",
            ),
            manifest_patterns=("manifest_benchmark_suite_audit.json", "manifest_benchmark_function_diversity_audit.json"),
            summary_patterns=("summary_benchmark_suite_audit.csv", "summary_benchmark_function_diversity_audit.csv"),
            analysis_patterns=("analysis_benchmark_suite_audit.md", "analysis_benchmark_function_diversity_audit.md"),
            dependency_boundary="Descriptive derived audit over existing raw CSVs; it records coverage and verification routes but does not rerun synthesis, training, or external toolchains.",
        ),
        EvidenceFamily(
            family="Novelty and comparison scorecard",
            claim_use="Checks that reviewer-facing novelty/comparison questions are tied to manuscript evidence, support-brief anchors, and explicit limitations.",
            rerun_tier="quick comparison audit",
            scripts=("analyze_novelty_comparison_scorecard.py",),
            raw_patterns=(),
            manifest_patterns=("manifest_novelty_comparison_scorecard.json",),
            summary_patterns=("summary_novelty_comparison_scorecard.csv",),
            analysis_patterns=("analysis_novelty_comparison_scorecard.md",),
            dependency_boundary="Quick derived audit; it strengthens reviewer-facing positioning without rerunning raw experiments.",
        ),
        EvidenceFamily(
            family="Related-work and citation verification",
            claim_use="Verifies related-work positioning, cited BibTeX coverage, DOI/arXiv locators, and learning-guided synthesis scope boundaries.",
            rerun_tier="quick literature audit",
            scripts=(
                "analyze_related_work_positioning.py",
                "analyze_citation_support_audit.py",
                "analyze_learning_citation_verification.py",
            ),
            raw_patterns=(),
            manifest_patterns=(
                "manifest_citation_support_audit.json",
                "manifest_learning_citation_verification.json",
            ),
            summary_patterns=(
                "summary_related_work_positioning.csv",
                "summary_citation_support_audit.csv",
                "summary_learning_citation_verification.csv",
            ),
            analysis_patterns=(
                "analysis_related_work_positioning.md",
                "analysis_citation_support_audit.md",
                "analysis_learning_citation_verification.md",
            ),
            dependency_boundary="Offline locator and scope-boundary audit; it records source-backed related-work positioning but does not claim that adjacent AI/MCTS systems are same-task baselines.",
        ),
        EvidenceFamily(
            family="SSHR reproduction-scope audit",
            claim_use="Separates source-anchored SSHR paper references, same-function SSHR-H rows, timed SSHR-I rows, exact n<=4 pilot checks, and excluded full-paper SSHR reruns.",
            rerun_tier="quick comparison audit",
            scripts=("analyze_sshr_reproduction_scope_audit.py",),
            raw_patterns=(
                "raw_traditional_resource.csv",
                "raw_external_traditional_resource_n4.csv",
                "raw_external_traditional_resource_n6.csv",
            ),
            manifest_patterns=(
                "manifest_sshr_reproduction_scope_audit.json",
                "manifest_traditional_resource.json",
                "manifest_external_traditional_resource_n4.json",
                "manifest_external_traditional_resource_n6.json",
            ),
            summary_patterns=(
                "summary_sshr_reproduction_scope_audit.csv",
                "summary_exact_fprm_dp.csv",
                "summary_exact_xag_mc.csv",
            ),
            analysis_patterns=(
                "analysis_sshr_reproduction_scope_audit.md",
                "analysis_exact_fprm_dp.md",
                "analysis_resource_weight_sensitivity_audit.md",
            ),
            dependency_boundary="Quick scope audit over existing SSHR-facing rows and references; it does not rerun heavy SSHR-I/Gurobi or every published random table.",
        ),
        EvidenceFamily(
            family="Resource-weight sensitivity and robustness",
            claim_use="Recomputes verified internal and external resource rows under alternative logical-resource weights so weighted-score conclusions are not tied only to the paper coefficients.",
            rerun_tier="quick derived audit",
            scripts=("analyze_weight_robustness.py", "analyze_resource_weight_sensitivity_audit.py"),
            raw_patterns=(
                "raw_traditional_resource.csv",
                "raw_highdim_resource.csv",
                "raw_highdim_scale_resource.csv",
                "raw_ultra_highdim_resource.csv",
                "raw_mega_highdim_resource.csv",
                "raw_resource_weight_sensitivity_audit.csv",
                "raw_ros_lut_proxy_best.csv",
                "raw_ros_lut_garbage_budget_frontier.csv",
                "raw_revkit_cli_multiflow_traditional.csv",
                "raw_mockturtle_xag_probe.csv",
                "raw_cirkit_aig_probe.csv",
                "raw_external_traditional_resource_n6.csv",
            ),
            manifest_patterns=("manifest_weight_robustness.json", "manifest_resource_weight_sensitivity_audit.json"),
            summary_patterns=("summary_weight_robustness.csv", "summary_resource_weight_sensitivity_audit.csv"),
            analysis_patterns=("analysis_weight_robustness.md", "analysis_resource_weight_sensitivity_audit.md"),
            dependency_boundary="Post-hoc logical-resource rescoring only; it does not rerun synthesis and is not a hardware cost model.",
        ),
        EvidenceFamily(
            family="Traditional logical baselines",
            claim_use="Primary n<=6 same-task resource comparison against direct, AND-direct, ESOP, SSHR, affine, MCTS, and Pareto variants.",
            rerun_tier="raw Python rerun",
            scripts=("run_experiments.py", "analyze_traditional_structure_mechanism.py"),
            raw_patterns=("raw_traditional_resource.csv", "raw_traditional_resource_*.csv", "raw_traditional_structure_mechanism.csv", "raw_traditional_small.csv", "raw_stg_published_benchmark.csv"),
            manifest_patterns=("manifest_traditional_resource*.json", "manifest_traditional_structure_mechanism.json", "manifest_traditional_small.json"),
            summary_patterns=("summary_traditional*.csv", "summary_paired_statistical_evidence.csv"),
            analysis_patterns=("analysis_traditional*.md", "analysis_paired_statistical_evidence.md"),
            dependency_boundary="Python rerun; ILP-based subbaselines need Gurobi where enabled.",
        ),
        EvidenceFamily(
            family="External logical baseline extension",
            claim_use="Matched exported-function comparisons against SSHR-I, ABC/BDD, and related logical estimates.",
            rerun_tier="raw Python plus optional solvers",
            scripts=("run_external_baselines.py",),
            raw_patterns=("raw_external_traditional_resource_n*.csv",),
            manifest_patterns=("manifest_external_traditional_resource_n*.json",),
            summary_patterns=("summary_external_traditional_resource_n*.csv",),
            analysis_patterns=("analysis_external_traditional_resource_n*.md",),
            dependency_boundary="Python with optional Gurobi/logic-tool components; rows with skips/errors remain explicit.",
        ),
        EvidenceFamily(
            family="ROS-style LUT proxy",
            claim_use="Tests whether the score advantage survives LUT-style oracle-synthesis proxies, line-aware reselection, and executable garbage-pressure schedules.",
            rerun_tier="raw proxy rerun",
            scripts=("run_ros_lut_proxy.py", "analyze_ros_lut_line_sensitivity.py", "analyze_ros_lut_garbage_proxy.py", "analyze_ros_lut_garbage_budget_frontier.py", "analyze_ros_lut_checkpoint_optimizer.py"),
            raw_patterns=("raw_ros_lut_proxy_*.csv", "raw_ros_lut_line_sensitivity.csv", "raw_ros_lut_garbage_proxy.csv", "raw_ros_lut_garbage_budget_frontier.csv", "raw_ros_lut_checkpoint_optimizer.csv"),
            manifest_patterns=("manifest_ros_lut_proxy.json", "manifest_ros_lut_line_sensitivity.json", "manifest_ros_lut_garbage_proxy.json", "manifest_ros_lut_garbage_budget_frontier.json", "manifest_ros_lut_checkpoint_optimizer.json"),
            summary_patterns=("summary_ros_lut_*.csv",),
            analysis_patterns=("analysis_ros_lut_*.md",),
            dependency_boundary="Proxy-level LUT and garbage-pressure analysis only; not a full ROS SAT garbage-management rerun.",
        ),
        EvidenceFamily(
            family="ROS reproduction boundary audit",
            claim_use="Makes the distinction between ROS-style proxy evidence, Caterpillar source/API/performance probing, and unreproduced full ROS/SAT garbage management machine-checkable.",
            rerun_tier="quick audit",
            scripts=("analyze_caterpillar_ros_family_probe.py", "run_caterpillar_xag_api_probe.py", "analyze_ros_reproduction_gap_audit.py"),
            raw_patterns=("raw_caterpillar_xag_api_*.csv", "raw_ros_lut_proxy_*.csv", "raw_ros_lut_line_sensitivity.csv", "raw_ros_lut_garbage_proxy.csv", "raw_ros_lut_garbage_budget_frontier.csv", "raw_ros_lut_checkpoint_optimizer.csv"),
            manifest_patterns=("manifest_caterpillar_ros_family_probe.json", "manifest_caterpillar_xag_api_probe.json", "manifest_ros_reproduction_gap_audit.json", "manifest_ros_lut_proxy.json", "manifest_ros_lut_line_sensitivity.json", "manifest_ros_lut_garbage_proxy.json", "manifest_ros_lut_garbage_budget_frontier.json", "manifest_ros_lut_checkpoint_optimizer.json"),
            summary_patterns=("summary_caterpillar_ros_family_probe.csv", "summary_caterpillar_xag_api_probe.csv", "summary_ros_reproduction_gap_audit.csv"),
            analysis_patterns=("analysis_caterpillar_ros_family_probe.md", "analysis_caterpillar_xag_api_probe.md", "analysis_ros_reproduction_gap_audit.md"),
            dependency_boundary="Checks scope and evidence boundaries; Caterpillar API rows are bounded ANF-XAG implementation-family probes, and full official ROS is not reproduced.",
        ),
        EvidenceFamily(
            family="Published STG optimum-library counterpoint",
            claim_use="Compares the current logical methods on the public n=4/5 STG spectral-representative truth-table table and exposes the small-function optimum boundary.",
            rerun_tier="raw Python rerun",
            scripts=("analyze_stg_published_benchmark.py",),
            raw_patterns=("raw_stg_published_benchmark.csv",),
            manifest_patterns=("manifest_stg_published_benchmark.json",),
            summary_patterns=("summary_stg_published_benchmark.csv",),
            analysis_patterns=("analysis_stg_published_benchmark.md",),
            dependency_boundary="Published small-function optimum-library counterpoint; not full ROS SAT garbage management and not hardware mapping.",
        ),
        EvidenceFamily(
            family="mockturtle KLUT-to-XAG probe",
            claim_use="Official-header XAG resynthesis probe for external logic-network comparison.",
            rerun_tier="external toolchain rerun",
            scripts=("run_mockturtle_xag_probe.py",),
            raw_patterns=("raw_mockturtle_xag*.csv",),
            manifest_patterns=("manifest_mockturtle_xag*.json",),
            summary_patterns=("summary_mockturtle_xag*.csv",),
            analysis_patterns=("analysis_mockturtle_xag*.md",),
            dependency_boundary="Requires the recorded mockturtle checkout/header path; still a logical proxy, not reversible mapping.",
        ),
        EvidenceFamily(
            family="CirKit AIG/MC probe",
            claim_use="External AIG and multiplicative-complexity counterpoint, especially for depth-oriented tradeoffs.",
            rerun_tier="external toolchain rerun",
            scripts=("run_cirkit_aig_probe.py",),
            raw_patterns=("raw_cirkit_aig*.csv",),
            manifest_patterns=("manifest_cirkit_aig*.json",),
            summary_patterns=("summary_cirkit_aig*.csv",),
            analysis_patterns=("analysis_cirkit_aig*.md",),
            dependency_boundary="Requires the recorded CirKit executable/commit; results are logical estimates, not hardware mapping.",
        ),
        EvidenceFamily(
            family="RevKit exact and Rz probes",
            claim_use="Exact reversible-oracle CLI portfolio and phase/Rz sensitivity boundary for RevKit comparisons.",
            rerun_tier="external toolchain rerun",
            scripts=("run_revkit_cli_probe.py", "run_revkit_baseline.py", "run_revkit_highdim_timeout_probe.py"),
            raw_patterns=("raw_revkit_*.csv", "raw_rz_synthesis_cost.csv"),
            manifest_patterns=("manifest_revkit_*.json", "manifest_rz_synthesis_cost.json"),
            summary_patterns=("summary_revkit_*.csv", "summary_rz_synthesis_cost.csv"),
            analysis_patterns=("analysis_revkit_*.md", "analysis_rz_synthesis_cost.md"),
            dependency_boundary="Requires RevKit CLI/API availability; Rz rows are phase/sensitivity probes, not final Clifford+T decomposition.",
        ),
        EvidenceFamily(
            family="Phase and affine FPRM branch",
            claim_use="Checks whether the search framing extends to phase-oracle/Rz proxy objectives and affine shortlist policies.",
            rerun_tier="raw phase rerun and training",
            scripts=(
                "run_phase_parity_baseline.py",
                "run_phase_parity_affine_search.py",
                "run_phase_parity_fprm_search.py",
                "train_phase_affine_policy.py",
                "analyze_phase_rotation_precision_audit.py",
                "analyze_phase_rotation_sequence_smoke_audit.py",
                "analyze_rotation_synthesis_backend_audit.py",
                "analyze_phase_policy_budget_frontier.py",
            ),
            raw_patterns=("raw_phase_*.csv",),
            manifest_patterns=("manifest_phase_*.json",),
            summary_patterns=("summary_phase_*.csv",),
            analysis_patterns=("analysis_phase_*.md",),
            dependency_boundary="Logical phase verification up to global phase; sequence smoke is coarse; backend audit records that no high-precision gridsynth-style backend is present.",
        ),
        EvidenceFamily(
            family="Learned-control and ablations",
            claim_use="Separates neural/search-control effects from deterministic algebraic construction and guarded portfolio selection.",
            rerun_tier="training plus ablation rerun",
            scripts=(
                "train_neural_policy.py",
                "train_screen_depth_policy.py",
                "train_screen_depth_frontier_policy.py",
                "train_sparse_depth4_gate.py",
                "run_bitflip_random_prior_control.py",
                "analyze_bitflip_random_prior_control.py",
                "run_bitflip_neural_budget_sweep.py",
                "analyze_bitflip_neural_budget_sweep.py",
                "analyze_frontier_random_depth_control.py",
                "analyze_phase_rotation_precision_audit.py",
                "analyze_phase_rotation_sequence_smoke_audit.py",
                "analyze_rotation_synthesis_backend_audit.py",
                "analyze_phase_policy_budget_frontier.py",
                "analyze_phase_policy_random_control.py",
                "analyze_root_action_ranker_audit.py",
                "analyze_search_control_baseline_audit.py",
                "analyze_learned_control_audit.py",
                "analyze_stochastic_control_stability.py",
                "analyze_neural_mcts_claim_calibration.py",
            ),
            raw_patterns=("raw_neural_*.csv", "raw_highdim_neural_*.csv", "raw_bitflip_*.csv", "raw_*root_action*.csv", "raw_sparse_depth4_gate*.csv", "raw_search_ablation_*.csv"),
            manifest_patterns=("manifest_*neural*.json", "manifest_bitflip_*.json", "manifest_*root_action*.json", "manifest_frontier_random*.json", "manifest_stochastic_control_stability.json", "manifest_search_ablation_*.json", "manifest_learned_control_audit.json", "manifest_neural_mcts_claim_calibration.json"),
            summary_patterns=("summary_*neural*.csv", "summary_bitflip_*.csv", "summary_*root_action*.csv", "summary_frontier_random*.csv", "summary_phase_policy_random_control.csv", "summary_sparse_depth4_gate*.csv", "summary_stochastic_control_stability.csv", "summary_search_ablation_*.csv", "summary_search_control_baseline_audit.csv", "summary_learned_control_audit.csv", "summary_neural_mcts_claim_calibration.csv"),
            analysis_patterns=("analysis_*neural*.md", "analysis_bitflip_*.md", "analysis_*root_action*.md", "analysis_frontier_random*.md", "analysis_phase_policy_random_control.md", "analysis_sparse_depth4_gate*.md", "analysis_stochastic_control_stability.md", "analysis_search_ablation_*.md", "analysis_search_control_baseline_audit.md", "analysis_learned_control_audit.md", "analysis_neural_mcts_claim_calibration.md"),
            dependency_boundary="Training can use MPS/GPU when available; learned controls rank, gate, or allocate search only.",
        ),
        EvidenceFamily(
            family="Schedule proxy and lifetime tradeoffs",
            claim_use="Checks logic-level T-depth proxy and explicit auxiliary-lifetime tradeoffs for the high-dimensional frontier controllers.",
            rerun_tier="quick derived audit",
            scripts=("analyze_schedule_metrics.py", "analyze_schedule_proxy_audit.py"),
            raw_patterns=("raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv", "raw_schedule_truth_bridge*.csv"),
            manifest_patterns=("manifest_schedule_proxy_audit.json",),
            summary_patterns=("summary_schedule_metrics.csv", "summary_schedule_proxy_audit.csv"),
            analysis_patterns=("analysis_schedule_metrics.md", "analysis_schedule_proxy_audit.md"),
            dependency_boundary="Emitted-circuit logical schedule proxies only; not hardware routing, native-gate scheduling, or device execution.",
        ),
        EvidenceFamily(
            family="Runtime envelope and rerun feasibility",
            claim_use="Summarizes workstation wall-clock envelopes across small, external, high-dimensional, truth-bridge, and learned-control slices.",
            rerun_tier="quick runtime audit",
            scripts=("analyze_runtime_envelope_audit.py",),
            raw_patterns=(
                "raw_traditional_resource.csv",
                "raw_ros_lut_proxy_best.csv",
                "raw_caterpillar_xag_api_best.csv",
                "raw_mockturtle_xag_probe.csv",
                "raw_cirkit_aig_probe.csv",
                "raw_revkit_cli_multiflow_traditional.csv",
                "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
                "raw_screen_scale_ultra_scale64_terms.csv",
                "raw_truth_bridge*.csv",
                "raw_bitflip_neural_budget_sweep.csv",
            ),
            manifest_patterns=("manifest_runtime_envelope_audit.json",),
            summary_patterns=("summary_runtime_envelope_audit.csv",),
            analysis_patterns=("analysis_runtime_envelope_audit.md",),
            dependency_boundary="Descriptive workstation timing envelope over existing raw artifacts; supports rerun feasibility, not portable runtime-speedup claims.",
        ),
        EvidenceFamily(
            family="High-dimensional symbolic screen-scale runs",
            claim_use="Tests scaling behavior on n=20-64 generated term-set instances with symbolic emitted-circuit checks.",
            rerun_tier="large raw rerun",
            scripts=("run_screen_scale_terms.py", "analyze_ultra_scale64_stress.py", "analyze_ultra_scale64_resource_profile.py"),
            raw_patterns=("raw_screen_scale*.csv", "raw_highdim_*.csv", "raw_mega_*.csv", "raw_giga_*.csv", "raw_ultra_*.csv"),
            manifest_patterns=("manifest_highdim*.json", "manifest_mega*.json", "manifest_giga*.json", "manifest_ultra*.json", "manifest_screen_scale_ultra_scale64_stress.json", "manifest_screen_scale_ultra_scale64_resource_profile.json"),
            summary_patterns=("summary_screen_scale*.csv", "summary_highdim*.csv", "summary_mega*.csv", "summary_giga*.csv", "summary_ultra*.csv"),
            analysis_patterns=("analysis_screen_scale*.md", "analysis_highdim*.md", "analysis_mega*.md", "analysis_giga*.md", "analysis_ultra*.md"),
            dependency_boundary="Symbolic or generated-instance verification; not exhaustive truth-table enumeration for all large n.",
        ),
        EvidenceFamily(
            family="External high-dimensional resource extensions",
            claim_use="Auxiliary high-dimensional extensions for external/resource baselines used to stress-test scaling claims.",
            rerun_tier="large raw rerun",
            scripts=("run_external_baselines.py", "analyze_external_baselines.py"),
            raw_patterns=("raw_external_highdim*.csv", "raw_external_mega*.csv", "raw_external_ultra*.csv"),
            manifest_patterns=("manifest_external_highdim*.json", "manifest_external_mega*.json", "manifest_external_ultra*.json"),
            summary_patterns=("summary_external_highdim*.csv", "summary_external_mega*.csv", "summary_external_ultra*.csv"),
            analysis_patterns=("analysis_external_highdim*.md", "analysis_external_mega*.md", "analysis_external_ultra*.md"),
            dependency_boundary="Generated large-instance comparisons; external availability and timeout behavior are recorded in manifests.",
        ),
        EvidenceFamily(
            family="Boolean screen, frontier, and gate auxiliaries",
            claim_use="Auxiliary guard/frontier/gate slices used to decide which learned or screened controls are promoted or demoted.",
            rerun_tier="training plus ablation rerun",
            scripts=(
                "train_screen_depth_policy.py",
                "train_screen_depth_frontier_policy.py",
                "train_structure_gate.py",
                "analyze_stage_gated_frontier.py",
                "analyze_structure_gate_holdout.py",
            ),
            raw_patterns=("raw_boolean_*.csv", "raw_gate_holdout*.csv", "raw_stage_gated_frontier.csv"),
            manifest_patterns=("manifest_boolean*.json", "manifest_gate_holdout*.json", "manifest_stage_gated_frontier.json"),
            summary_patterns=("summary_boolean*.csv", "summary_gate_holdout*.csv", "summary_stage_gated_frontier.csv"),
            analysis_patterns=("analysis_boolean*.md", "analysis_gate_holdout*.md", "analysis_stage_gated_frontier.md"),
            dependency_boundary="Auxiliary policy-selection evidence; not all rows are promoted as final-quality gains.",
        ),
        EvidenceFamily(
            family="Exact, resource-sweep, and development probes",
            claim_use="Auxiliary exact-DP, XAG/MC, resource-sweep, pilot, smoke, and early evidence checks retained for auditability.",
            rerun_tier="auxiliary raw rerun",
            scripts=(
                "analyze_exact_fprm_dp.py",
                "analyze_exact_xag_mc.py",
                "run_resource_sweep.py",
                "analyze_resource_sweep.py",
                "analyze_cnot_constraint_profile_audit.py",
            ),
            raw_patterns=(
                "raw_ablation_affine.csv",
                "raw_evidence*.csv",
                "raw_exact_*.csv",
                "raw_large*.csv",
                "raw_pilot.csv",
                "raw_resource_sweep.csv",
                "raw_smoke.csv",
            ),
            manifest_patterns=(
                "manifest_ablation_affine.json",
                "manifest_evidence_affine.json",
                "manifest_large_resource_core.json",
                "manifest_pilot.json",
                "manifest_resource_sweep.json",
                "manifest_cnot_constraint_profile_audit.json",
                "manifest_smoke.json",
            ),
            summary_patterns=(
                "summary_ablation_affine.csv",
                "summary_evidence*.csv",
                "summary_exact_*.csv",
                "summary_large*.csv",
                "summary_pilot.csv",
                "summary_resource_sweep.csv",
                "summary_cnot_constraint_profile_audit.csv",
                "summary_smoke.csv",
            ),
            analysis_patterns=(
                "analysis_ablation_affine.md",
                "analysis_cnot_constraint_profile_audit.md",
                "analysis_evidence*.md",
                "analysis_exact_*.md",
                "analysis_large*.md",
                "analysis_pilot.md",
                "analysis_resource_sweep.md",
                "analysis_smoke.md",
            ),
            dependency_boundary="Development and auxiliary evidence retained in the payload; not all rows correspond to headline manuscript claims.",
        ),
        EvidenceFamily(
            family="Complete truth-table bridge slices",
            claim_use="Connects high-dimensional symbolic plans to complete truth-table simulation on n=21-30 bridge rows.",
            rerun_tier="bridge raw rerun",
            scripts=("run_truth_bridge_terms.py",),
            raw_patterns=("raw_truth_bridge*.csv", "raw_schedule_truth_bridge*.csv"),
            manifest_patterns=(),
            summary_patterns=("summary_truth_bridge*.csv", "summary_schedule_truth_bridge*.csv"),
            analysis_patterns=("analysis_truth_bridge*.md", "analysis_schedule_truth_bridge*.md"),
            dependency_boundary="Narrow bridge slices because full truth tables grow exponentially.",
        ),
    ]


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in specs():
        scripts = script_paths(spec.scripts)
        raw_files = collect_result(spec.raw_patterns)
        manifests = collect_result(spec.manifest_patterns)
        summaries = collect_result(spec.summary_patterns)
        analyses = collect_result(spec.analysis_patterns)
        missing_scripts = [rel(path) for path in scripts if not path.exists()]
        missing_raw = bool(spec.raw_patterns and not raw_files)
        status = "complete" if not missing_scripts and not missing_raw else "needs artifact"
        rows.append(
            {
                "evidence_family": spec.family,
                "claim_use": spec.claim_use,
                "rerun_tier": spec.rerun_tier,
                "driver_scripts": "; ".join(spec.scripts),
                "scripts_present": str(len(scripts) - len(missing_scripts)),
                "scripts_missing": "; ".join(missing_scripts),
                "raw_files": str(len(raw_files)),
                "raw_rows": str(raw_row_count(raw_files)),
                "manifest_files": str(len(manifests)),
                "summary_files": str(len(summaries)),
                "analysis_files": str(len(analyses)),
                "representative_raw": paths_text(raw_files),
                "dependency_boundary": spec.dependency_boundary,
                "status": status,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "evidence_family",
        "claim_use",
        "rerun_tier",
        "driver_scripts",
        "scripts_present",
        "scripts_missing",
        "raw_files",
        "raw_rows",
        "manifest_files",
        "summary_files",
        "analysis_files",
        "representative_raw",
        "dependency_boundary",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    unique_raw = unique_registry_raw_files()
    total_rows = raw_row_count(unique_raw)
    lines = [
        "# Artifact Rerun Registry",
        "",
        "This registry maps paper-facing evidence families to rerun entry points, existing raw CSV artifacts, manifest coverage, and dependency boundaries.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            f"- unique raw files covered by registry: {len(unique_raw)}",
            f"- unique raw CSV rows covered by registry: {total_rows}",
            "",
            "| evidence family | rerun tier | raw files | raw rows | manifests | status | dependency boundary |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['evidence_family']} | {row['rerun_tier']} | {row['raw_files']} | {row['raw_rows']} | "
            f"{row['manifest_files']} | {row['status']} | {row['dependency_boundary']} |"
        )
    lines.extend(["", "## Driver scripts and representative raw artifacts", ""])
    for row in rows:
        lines.append(f"- **{row['evidence_family']}**")
        lines.append(f"  - claim use: {row['claim_use']}")
        lines.append(f"  - scripts: `{row['driver_scripts']}`")
        if row["representative_raw"]:
            lines.append(f"  - representative raw: `{row['representative_raw']}`")
        else:
            lines.append("  - representative raw: not applicable for this tier")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("<=", r"$\leq$")
    return text


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.16\linewidth}rr>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Evidence family & Rerun tier & Raw files & Raw rows & Dependency boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["evidence_family"]),
                    tex_escape(row["rerun_tier"]),
                    row["raw_files"],
                    row["raw_rows"],
                    tex_escape(row["dependency_boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    unique_raw = unique_registry_raw_files()
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "complete_rows": sum(1 for row in rows if row["status"] == "complete"),
        "unique_raw_files": len(unique_raw),
        "unique_raw_rows": raw_row_count(unique_raw),
        "raw_file_names": [rel(path) for path in unique_raw],
        "outputs": {
            "summary": "results/summary_artifact_rerun_registry.csv",
            "analysis": "results/analysis_artifact_rerun_registry.md",
            "table": "paper_latex/tables/artifact_rerun_registry.tex",
        },
        "families": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_artifact_rerun_registry.csv", rows)
    write_markdown(RESULTS / "analysis_artifact_rerun_registry.md", rows)
    write_latex(TABLES / "artifact_rerun_registry.tex", rows)
    write_manifest(RESULTS / "manifest_artifact_rerun_registry.json", rows)
    print(f"wrote {len(rows)} artifact rerun registry rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
