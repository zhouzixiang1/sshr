#!/usr/bin/env python3
"""Build a submission traceability audit for headline claims.

The readiness audit checks whether manuscript sections exist.  This audit is
stricter: it links each paper-facing claim family to the script/data/table or
figure artifacts that support it, and marks rows incomplete if any listed
artifact is missing from the submission package.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
FIGURES = THIS_DIR / "paper_latex" / "figures" / "submission_v36"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def status_for(paths: list[Path]) -> tuple[str, str]:
    missing = [rel(path) for path in paths if not path.exists()]
    if missing:
        return "missing artifact", "; ".join(missing)
    return "complete", "all listed artifacts present"


def row(
    claim_family: str,
    claim_use: str,
    artifacts: list[Path],
    manuscript_anchor: str,
    boundary: str,
) -> dict[str, str]:
    status, evidence = status_for(artifacts)
    return {
        "claim_family": claim_family,
        "claim_use": claim_use,
        "artifact_chain": "; ".join(rel(path) for path in artifacts),
        "manuscript_anchor": manuscript_anchor,
        "boundary": boundary,
        "status": status,
        "evidence": evidence,
    }


def build_rows() -> list[dict[str, str]]:
    return [
        row(
            "Method formulation",
            "Defines Resource-NMCTS as a source-anchored logical ANF/FPRM search workflow.",
            [
                THIS_DIR / "analyze_method_workflow_table.py",
                THIS_DIR / "analyze_algorithm_contract_table.py",
                THIS_DIR / "analyze_search_budget_contract.py",
                RESULTS / "summary_method_workflow.csv",
                RESULTS / "summary_algorithm_contract.csv",
                RESULTS / "summary_search_budget_contract.csv",
                RESULTS / "analysis_method_workflow.md",
                RESULTS / "analysis_algorithm_contract.md",
                RESULTS / "analysis_search_budget_contract.md",
                TABLES / "method_workflow.tex",
                TABLES / "algorithm_contract.tex",
                TABLES / "search_budget_contract.tex",
            ],
            "Method, Tables method-workflow, algorithm-contract, and search-budget-contract",
            "Establishes executable stages, semantic/resource guarantees, and bounded search budgets, not a hardware compiler or global optimality proof.",
        ),
        row(
            "Contribution mapping",
            "Links each stated contribution to implementation, evidence, and claim boundary.",
            [
                THIS_DIR / "analyze_contribution_evidence_map.py",
                RESULTS / "summary_contribution_evidence_map.csv",
                RESULTS / "analysis_contribution_evidence_map.md",
                TABLES / "contribution_evidence_map.tex",
            ],
            "Introduction, Table contribution-map",
            "Prevents the introduction from making unsupported novelty claims.",
        ),
        row(
            "Novelty and comparison scorecard",
            "Answers reviewer-facing questions about method identity, comparison meaning, external probes, tradeoffs, AI isolation, and scale boundary.",
            [
                THIS_DIR / "analyze_novelty_comparison_scorecard.py",
                RESULTS / "summary_novelty_comparison_scorecard.csv",
                RESULTS / "analysis_novelty_comparison_scorecard.md",
                RESULTS / "manifest_novelty_comparison_scorecard.json",
                TABLES / "novelty_comparison_scorecard.tex",
                THIS_DIR / "submission_package" / "reviewer_concern_brief.md",
                THIS_DIR / "submission_package" / "editor_screening_brief.md",
            ],
            "Introduction, Table novelty-comparison-scorecard",
            "Provides a reviewer-facing index over existing evidence; it does not add a new metric or broaden the logical-layer scope.",
        ),
        row(
            "Primary small-function resources",
            "Supports T-count and weighted-score claims on matched n<=6 functions.",
            [
                THIS_DIR / "run_experiments.py",
                RESULTS / "manifest_traditional_resource.json",
                RESULTS / "raw_traditional_resource.csv",
                RESULTS / "analysis_traditional_resource.md",
                RESULTS / "analysis_paired_statistical_evidence.md",
                RESULTS / "analysis_paired_effect_uncertainty.md",
                TABLES / "paired_statistical_evidence.tex",
                TABLES / "paired_effect_uncertainty.tex",
                FIGURES / "fig2_traditional_resources.pdf",
            ],
            "Results, traditional functions",
            "Same logical cost model; not a CNOT-only or hardware-level claim.",
        ),
        row(
            "Baseline scope and fairness",
            "Explains why each baseline family is comparable and which claim it can support.",
            [
                THIS_DIR / "analyze_baseline_claim_matrix.py",
                THIS_DIR / "analyze_comparison_evidence_matrix.py",
                THIS_DIR / "analyze_baseline_comparability_audit.py",
                THIS_DIR / "analyze_counterpoint_claim_boundary.py",
                THIS_DIR / "analyze_comparison_target_validity_audit.py",
                THIS_DIR / "analyze_comparison_answer_scorecard.py",
                THIS_DIR / "analyze_sshr_reproduction_scope_audit.py",
                RESULTS / "analysis_sshr_reproduction_scope_audit.md",
                RESULTS / "manifest_sshr_reproduction_scope_audit.json",
                TABLES / "baseline_claim_matrix.tex",
                TABLES / "comparison_evidence_matrix.tex",
                TABLES / "comparison_target_validity_audit.tex",
                TABLES / "comparison_answer_scorecard.tex",
                TABLES / "sshr_reproduction_scope_audit.tex",
                TABLES / "baseline_comparability_audit.tex",
                TABLES / "counterpoint_claim_boundary.tex",
            ],
            "Experimental Design, baseline matrices, target-validity table, comparison answer scorecard, SSHR reproduction-scope audit, and counterpoint audit",
            "Treats comparisons as layered evidence with explicit roles and reports unfavorable metric counterpoints rather than a universal leaderboard.",
        ),
        row(
            "Threats to validity",
            "Links the main reviewer-facing validity threats to mitigation evidence and residual boundaries.",
            [
                THIS_DIR / "analyze_threats_to_validity_audit.py",
                RESULTS / "summary_threats_to_validity_audit.csv",
                RESULTS / "analysis_threats_to_validity_audit.md",
                RESULTS / "manifest_threats_to_validity_audit.json",
                TABLES / "threats_to_validity_audit.tex",
            ],
            "Discussion, Table threats-validity",
            "Names limitations and mitigations; it does not remove the logical-layer, proxy-baseline, or generated-slice boundaries.",
        ),
        row(
            "External toolchain probes",
            "Traces ROS-style LUT, published STG, mockturtle, CirKit, and RevKit CLI comparison evidence.",
            [
                RESULTS / "raw_ros_lut_proxy_best.csv",
                RESULTS / "raw_ros_lut_garbage_proxy.csv",
                RESULTS / "raw_ros_lut_garbage_budget_frontier.csv",
                RESULTS / "raw_ros_lut_checkpoint_optimizer.csv",
                RESULTS / "raw_stg_published_benchmark.csv",
                RESULTS / "raw_mockturtle_xag_probe.csv",
                RESULTS / "raw_cirkit_aig_probe.csv",
                RESULTS / "raw_revkit_cli_multiflow_traditional.csv",
                RESULTS / "analysis_ros_lut_garbage_proxy.md",
                RESULTS / "analysis_ros_lut_garbage_budget_frontier.md",
                RESULTS / "analysis_ros_lut_checkpoint_optimizer.md",
                RESULTS / "analysis_stg_published_benchmark.md",
                TABLES / "ros_lut_line_sensitivity.tex",
                TABLES / "ros_lut_garbage_proxy.tex",
                TABLES / "ros_lut_garbage_budget_frontier.tex",
                TABLES / "ros_lut_checkpoint_optimizer.tex",
                TABLES / "stg_published_benchmark.tex",
                TABLES / "cirkit_aig_probe.tex",
                TABLES / "revkit_cli_multiflow_traditional.tex",
                FIGURES / "fig3_baseline_comparisons.pdf",
            ],
            "Results, external probes",
            "Logic-level probes, published optimum-library counterpoint, or exact-oracle reversible probe; not full hardware mapping.",
        ),
        row(
            "Multi-resource tradeoff",
            "Audits whether weighted-score wins imply raw-resource, schedule-proxy, or auxiliary-lifetime dominance.",
            [
                THIS_DIR / "analyze_multimetric_pareto_tradeoff.py",
                THIS_DIR / "analyze_weight_robustness.py",
                THIS_DIR / "analyze_resource_weight_sensitivity_audit.py",
                THIS_DIR / "analyze_schedule_metrics.py",
                THIS_DIR / "analyze_schedule_proxy_audit.py",
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "analysis_weight_robustness.md",
                RESULTS / "manifest_weight_robustness.json",
                RESULTS / "analysis_resource_weight_sensitivity_audit.md",
                RESULTS / "raw_resource_weight_sensitivity_audit.csv",
                RESULTS / "summary_resource_weight_sensitivity_audit.csv",
                RESULTS / "manifest_resource_weight_sensitivity_audit.json",
                RESULTS / "analysis_schedule_metrics.md",
                RESULTS / "analysis_schedule_proxy_audit.md",
                RESULTS / "summary_weight_robustness.csv",
                RESULTS / "summary_schedule_proxy_audit.csv",
                TABLES / "multimetric_pairwise_dominance.tex",
                TABLES / "multimetric_nondominated.tex",
                TABLES / "weight_robustness_compact.tex",
                TABLES / "resource_weight_sensitivity_audit.tex",
                TABLES / "schedule_proxy_audit.tex",
            ],
            "Results, raw multi-resource dominance, score-weight robustness, resource-weight sensitivity, and schedule-proxy audit",
            "Dominance and sensitivity checks use logical T-count, CNOT, depth, gates, peak ancilla, T-depth proxy, and auxiliary lifetime; no routing or native-gate scheduling is claimed.",
        ),
        row(
            "Learned-control contribution",
            "Separates search-control baselines and promoted learned controllers from limited diagnostics.",
            [
                THIS_DIR / "analyze_search_control_baseline_audit.py",
                THIS_DIR / "analyze_bitflip_random_prior_control.py",
                THIS_DIR / "analyze_bitflip_neural_budget_sweep.py",
                THIS_DIR / "analyze_frontier_random_depth_control.py",
                THIS_DIR / "analyze_phase_rotation_precision_audit.py",
                THIS_DIR / "analyze_phase_rotation_sequence_smoke_audit.py",
                THIS_DIR / "analyze_phase_policy_budget_frontier.py",
                THIS_DIR / "analyze_root_action_ranker_audit.py",
                THIS_DIR / "analyze_learned_control_audit.py",
                THIS_DIR / "analyze_neural_mcts_claim_calibration.py",
                THIS_DIR / "train_sparse_depth4_gate.py",
                RESULTS / "analysis_search_control_baseline_audit.md",
                RESULTS / "analysis_bitflip_random_prior_control.md",
                RESULTS / "analysis_bitflip_neural_budget_sweep.md",
                RESULTS / "analysis_frontier_random_depth_control.md",
                RESULTS / "analysis_phase_rotation_precision_audit.md",
                RESULTS / "analysis_phase_rotation_sequence_smoke_audit.md",
                RESULTS / "raw_phase_rotation_sequence_smoke_audit.csv",
                RESULTS / "summary_phase_rotation_precision_audit.csv",
                RESULTS / "summary_phase_rotation_sequence_smoke_audit.csv",
                RESULTS / "manifest_phase_rotation_precision_audit.json",
                RESULTS / "manifest_phase_rotation_sequence_smoke_audit.json",
                RESULTS / "analysis_phase_policy_budget_frontier.md",
                RESULTS / "summary_phase_policy_budget_frontier.csv",
                RESULTS / "manifest_phase_policy_budget_frontier.json",
                RESULTS / "analysis_root_action_ranker_audit.md",
                RESULTS / "analysis_learned_control_audit.md",
                RESULTS / "analysis_neural_mcts_claim_calibration.md",
                RESULTS / "analysis_sparse_depth4_gate_generalization.md",
                TABLES / "search_control_baseline_audit.tex",
                TABLES / "bitflip_random_prior_control.tex",
                TABLES / "bitflip_neural_budget_sweep.tex",
                TABLES / "frontier_random_depth_control.tex",
                TABLES / "phase_rotation_precision_audit.tex",
                TABLES / "phase_rotation_sequence_smoke_audit.tex",
                TABLES / "phase_policy_budget_frontier.tex",
                TABLES / "root_action_ranker_audit.tex",
                TABLES / "learned_control_audit.tex",
                TABLES / "neural_mcts_claim_calibration.tex",
                TABLES / "sparse_depth4_gate_generalization.tex",
                FIGURES / "fig7_learned_control_summary.pdf",
            ],
            "Results, search contribution and ablation",
            "Supports guarded learned-control evidence, not a claim that RL alone explains all gains.",
        ),
        row(
            "High-dimensional verification",
            "Traces large symbolic checks through n=64, phase checks, and complete truth-table bridge slices.",
            [
                THIS_DIR / "analyze_scaling_resource_audit.py",
                THIS_DIR / "analyze_ultra_scale64_stress.py",
                THIS_DIR / "analyze_ultra_scale64_resource_profile.py",
                RESULTS / "analysis_scaling_resource_audit.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_stress.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md",
                RESULTS / "manifest_screen_scale_ultra_scale64_stress.json",
                RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json",
                RESULTS / "summary_screen_scale_ultra_scale64_resource_profile.csv",
                RESULTS / "summary_screen_scale_ultra_scale64_resource_deltas.csv",
                TABLES / "scaling_resource_audit.tex",
                TABLES / "screen_scale_ultra_scale64_stress.tex",
                TABLES / "screen_scale_ultra_scale64_resource_profile.tex",
                RESULTS / "raw_screen_scale_ultra_scale64_terms.csv",
                RESULTS / "raw_truth_bridge_terms.csv",
                RESULTS / "raw_truth_bridge_n24_terms.csv",
                RESULTS / "raw_truth_bridge_n25_terms.csv",
                RESULTS / "raw_truth_bridge_n26_terms.csv",
                FIGURES / "fig5_validation.pdf",
            ],
            "Results, high-dimensional verification",
            "Large rows are symbolic or bridge-slice verified, not exhaustive high-dimensional truth tables.",
        ),
        row(
            "Archive package integrity",
            "Hashes stable submission payload groups and records archive boundaries.",
            [
                THIS_DIR / "analyze_submission_archive_manifest.py",
                RESULTS / "summary_submission_archive_manifest.csv",
                RESULTS / "analysis_submission_archive_manifest.md",
                RESULTS / "manifest_submission_archive_manifest.json",
                TABLES / "submission_archive_manifest.tex",
            ],
            "Experimental Design, archive manifest",
            "Excludes terminal submission audits and compiled PDF from payload hashes to avoid self-reference.",
        ),
        row(
            "Submission support and venue gate",
            "Traces target-venue decision support, support-packet consistency, and author-gated submission metadata.",
            [
                THIS_DIR / "analyze_target_venue_decision_audit.py",
                THIS_DIR / "analyze_submission_support_packet_audit.py",
                THIS_DIR / "analyze_submission_metadata_closure_path.py",
                RESULTS / "analysis_target_venue_decision_audit.md",
                RESULTS / "analysis_submission_support_packet_audit.md",
                RESULTS / "analysis_submission_metadata_closure_path.md",
                TABLES / "target_venue_decision_audit.tex",
                TABLES / "submission_support_packet_audit.tex",
                THIS_DIR / "submission_package" / "target_venue_brief.md",
                THIS_DIR / "submission_package" / "AUTHOR_INPUT_REQUIRED.md",
                THIS_DIR / "submission_package" / "submission_metadata_template.json",
            ],
            "Submission package, target venue brief and author-input packet",
            "Supports a source-backed venue decision path; final venue, declarations, archive links, and anonymous-review status remain author input.",
        ),
        row(
            "Reproducibility package",
            "Documents compute envelope, worker manifests, artifact counts, raw rerun entry points, and availability section.",
            [
                THIS_DIR / "analyze_artifact_rerun_registry.py",
                THIS_DIR / "analyze_reproducibility_audit.py",
                THIS_DIR / "analyze_submission_readiness_audit.py",
                THIS_DIR / "analyze_submission_archive_manifest.py",
                THIS_DIR / "rebuild_submission_package.sh",
                RESULTS / "analysis_artifact_rerun_registry.md",
                RESULTS / "analysis_reproducibility_audit.md",
                RESULTS / "analysis_submission_archive_manifest.md",
                RESULTS / "analysis_submission_readiness_audit.md",
                TABLES / "artifact_rerun_registry.tex",
                TABLES / "reproducibility_audit.tex",
                TABLES / "submission_archive_manifest.tex",
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex",
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf",
            ],
            "Experimental Design and Data and Code Availability",
            "Repository-relative package until an archival DOI or anonymous link is supplied.",
        ),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim_family",
        "claim_use",
        "artifact_chain",
        "manuscript_anchor",
        "boundary",
        "status",
        "evidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Submission Traceability Audit",
        "",
        "This audit links headline manuscript claims to supporting scripts, raw/summary artifacts, tables, figures, and claim boundaries.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| claim family | claim use | manuscript anchor | boundary | status |",
            "|---|---|---|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            f"| {item['claim_family']} | {item['claim_use']} | {item['manuscript_anchor']} | {item['boundary']} | {item['status']} |"
        )
    lines.extend(["", "## Artifact chains", ""])
    for item in rows:
        lines.append(f"- **{item['claim_family']}**: {item['artifact_chain']}")
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
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.29\linewidth}>{\raggedright\arraybackslash}p{0.19\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Claim family & Paper-facing use & Manuscript anchor & Boundary \\",
        r"\midrule",
    ]
    for item in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(item["claim_family"]),
                    tex_escape(item["claim_use"]),
                    tex_escape(item["manuscript_anchor"]),
                    tex_escape(item["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_traceability_audit.csv"),
            "analysis": rel(RESULTS / "analysis_submission_traceability_audit.md"),
            "table": rel(TABLES / "submission_traceability_audit.tex"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_traceability_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_traceability_audit.md", rows)
    write_latex(TABLES / "submission_traceability_audit.tex", rows)
    write_manifest(RESULTS / "manifest_submission_traceability_audit.json", rows)
    missing = [row for row in rows if row["status"] != "complete"]
    print(f"wrote {len(rows)} submission traceability rows")
    if missing:
        print(f"warning: {len(missing)} rows have missing artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
