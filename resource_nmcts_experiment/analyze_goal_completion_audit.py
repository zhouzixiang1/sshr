#!/usr/bin/env python3
"""Audit progress against the original project objective.

This is a goal-level audit, not another experimental result.  It maps the
requested end state--design, literature positioning, implementation, baseline
reproduction, large-scale runs, compute use, figures/tables, LaTeX manuscript,
and submission package--to concrete artifacts in the current worktree.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
TABLES = THIS_DIR / "paper_latex" / "tables"
FIGURES = THIS_DIR / "paper_latex" / "figures" / "submission_v36"
PAYLOAD = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz"
PAYLOAD_SHA256 = THIS_DIR / "submission_package" / "dist" / "resource_nmcts_submission_payload.tar.gz.sha256"
FIGURE_ASSET_ANALYSIS = RESULTS / "analysis_figure_asset_audit.md"


@dataclass(frozen=True)
class GoalItem:
    requirement: str
    status: str
    evidence: str
    evidence_files: tuple[Path, ...]
    boundary: str
    next_action: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def file_count(root: Path, pattern: str) -> int:
    return sum(1 for _ in root.glob(pattern)) if root.exists() else 0


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


def exists_all(paths: tuple[Path, ...]) -> bool:
    return all(path.exists() for path in paths)


def status_if(paths: tuple[Path, ...], extra: bool = True) -> str:
    return "pass" if exists_all(paths) and extra else "needs evidence"


def metadata_counts() -> tuple[int, int]:
    text = read_text(RESULTS / "analysis_submission_metadata_audit.md")
    needs = re.search(r"^- needs author input: (\d+)", text, flags=re.MULTILINE)
    passed = re.search(r"^- pass: (\d+)", text, flags=re.MULTILINE)
    return int(needs.group(1)) if needs else 0, int(passed.group(1)) if passed else 0


def build_items() -> list[GoalItem]:
    paper_text = read_text(PAPER)
    figure_panels = file_count(FIGURES, "fig*.pdf")
    table_count = file_count(TABLES, "*.tex")
    pages = pdf_pages(PDF)
    metadata_needs, _ = metadata_counts()

    return [
        GoalItem(
            requirement="Design and literature positioning",
            status=status_if(
                (
                    RESULTS / "analysis_related_work_positioning.md",
                    RESULTS / "analysis_contribution_evidence_map.md",
                    RESULTS / "analysis_novelty_comparison_scorecard.md",
                    TABLES / "related_work_positioning.tex",
                    TABLES / "contribution_evidence_map.tex",
                    TABLES / "novelty_comparison_scorecard.tex",
                )
            ),
            evidence="Related-work, contribution, and novelty/comparison scorecard matrices position the method against BDD, LUT/ROS, XAG/MC, ABC/RevKit/mockturtle/CirKit, SSHR, and learning-guided synthesis.",
            evidence_files=(
                RESULTS / "analysis_related_work_positioning.md",
                RESULTS / "analysis_contribution_evidence_map.md",
                RESULTS / "analysis_novelty_comparison_scorecard.md",
                TABLES / "related_work_positioning.tex",
                TABLES / "contribution_evidence_map.tex",
                TABLES / "novelty_comparison_scorecard.tex",
            ),
            boundary="This establishes a manuscript framing and comparison map, not a claim that every cited system was fully reproduced.",
            next_action="Update this row only if the manuscript's claimed novelty or related-work scope changes.",
        ),
        GoalItem(
            requirement="Logical-layer scope without hardware mapping",
            status="pass" if "not a hardware-mapped" in paper_text and "logical-layer" in paper_text else "needs evidence",
            evidence="The abstract, limitations, availability text, and claim-scope lint state that results are logical-layer estimates and exclude hardware mapping/routing/noise claims.",
            evidence_files=(PAPER, RESULTS / "analysis_claim_scope_lint.md", RESULTS / "analysis_submission_readiness_audit.md"),
            boundary="No hardware placement, routing, native-gate scheduling, noise model, or magic-state-factory resource estimate is claimed.",
            next_action="Keep this boundary unless new hardware-mapping experiments are added.",
        ),
        GoalItem(
            requirement="Implemented Resource-NMCTS workflow",
            status=status_if(
                (
                    RESULTS / "analysis_method_workflow.md",
                    RESULTS / "analysis_algorithm_contract.md",
                    RESULTS / "analysis_search_budget_contract.md",
                    TABLES / "method_workflow.tex",
                    TABLES / "algorithm_contract.tex",
                    TABLES / "search_budget_contract.tex",
                    RESULTS / "raw_traditional_resource.csv",
                    RESULTS / "manifest_traditional_resource.json",
                )
            ),
            evidence="The method workflow, source-anchored algorithm contract, and search-budget contract cover input normalization, candidate generation, neural/MCTS/beam control, bounded search budgets, guarded selection, Pareto archiving, circuit emission, and verification/reporting.",
            evidence_files=(
                RESULTS / "analysis_method_workflow.md",
                RESULTS / "analysis_algorithm_contract.md",
                RESULTS / "analysis_search_budget_contract.md",
                TABLES / "method_workflow.tex",
                TABLES / "algorithm_contract.tex",
                TABLES / "search_budget_contract.tex",
                RESULTS / "raw_traditional_resource.csv",
                RESULTS / "manifest_traditional_resource.json",
            ),
            boundary="Correctness is tied to ANF, emitted-circuit, truth-table, or phase checks; learned components only rank, gate, or allocate bounded search.",
            next_action="Keep workflow artifacts aligned with any new candidate generator or verification stage.",
        ),
        GoalItem(
            requirement="Neural/MCTS and learned-control evidence",
            status=status_if(
                (
                    RESULTS / "analysis_search_control_baseline_audit.md",
                    TABLES / "search_control_baseline_audit.tex",
                    RESULTS / "analysis_bitflip_random_prior_control.md",
                    TABLES / "bitflip_random_prior_control.tex",
                    RESULTS / "analysis_frontier_random_depth_control.md",
                    TABLES / "frontier_random_depth_control.tex",
                    RESULTS / "analysis_learned_control_audit.md",
                    TABLES / "learned_control_audit.tex",
                    FIGURES / "fig7_learned_control_summary.pdf",
                )
            ),
            evidence="Search-control, bit-flip random-prior, frontier random-depth, and learned-control audits separate heuristic/beam/no-MCTS/MCTS/Pareto/prior comparisons, same-budget random-prior controls, same-candidate frontier budget controls, promoted frontier/gating/phase-pruning controls, and limited diagnostics.",
            evidence_files=(
                RESULTS / "analysis_search_control_baseline_audit.md",
                TABLES / "search_control_baseline_audit.tex",
                RESULTS / "analysis_bitflip_random_prior_control.md",
                TABLES / "bitflip_random_prior_control.tex",
                RESULTS / "analysis_frontier_random_depth_control.md",
                TABLES / "frontier_random_depth_control.tex",
                RESULTS / "analysis_learned_control_audit.md",
                TABLES / "learned_control_audit.tex",
                FIGURES / "fig7_learned_control_summary.pdf",
            ),
            boundary="The evidence supports bounded neural/search-control contributions, not a claim that deep RL alone explains all gains.",
            next_action="Do not promote runtime-negative or quality-weak neural diagnostics as main contributions.",
        ),
        GoalItem(
            requirement="Baseline reproduction and comparison breadth",
            status=status_if(
                (
                    RESULTS / "analysis_comparison_evidence_matrix.md",
                    RESULTS / "analysis_baseline_comparability_audit.md",
                    RESULTS / "analysis_comparison_target_validity_audit.md",
                    RESULTS / "analysis_novelty_comparison_scorecard.md",
                    TABLES / "comparison_target_validity_audit.tex",
                    RESULTS / "raw_mockturtle_xag_probe.csv",
                    RESULTS / "raw_cirkit_aig_probe.csv",
                    RESULTS / "raw_revkit_cli_multiflow_traditional.csv",
                    RESULTS / "raw_ros_lut_proxy_best.csv",
                )
            ),
            evidence="Comparison evidence, target-validity roles, and the novelty/comparison scorecard cover internal logical baselines, SSHR, ABC/BDD, ROS-style LUT, mockturtle, CirKit, RevKit CLI exact-oracle, controls, and phase/Rz probes.",
            evidence_files=(
                RESULTS / "analysis_comparison_evidence_matrix.md",
                RESULTS / "analysis_baseline_comparability_audit.md",
                RESULTS / "analysis_comparison_target_validity_audit.md",
                RESULTS / "analysis_novelty_comparison_scorecard.md",
                TABLES / "comparison_target_validity_audit.tex",
                RESULTS / "raw_mockturtle_xag_probe.csv",
                RESULTS / "raw_cirkit_aig_probe.csv",
                RESULTS / "raw_revkit_cli_multiflow_traditional.csv",
                RESULTS / "raw_ros_lut_proxy_best.csv",
            ),
            boundary="External rows are logic-level probes or exact-oracle reversible probes; they are not full ROS or hardware-mapped reproductions.",
            next_action="Use the comparability audit when writing any baseline claim.",
        ),
        GoalItem(
            requirement="Significant improvement over prior draft",
            status=status_if(
                (
                    RESULTS / "analysis_paired_statistical_evidence.md",
                    RESULTS / "analysis_paired_effect_uncertainty.md",
                    TABLES / "paired_statistical_evidence.tex",
                    TABLES / "paired_effect_uncertainty.tex",
                    FIGURES / "fig2_traditional_resources.pdf",
                    FIGURES / "fig3_baseline_comparisons.pdf",
                )
            ),
            evidence="Paired statistics and bootstrap effect intervals show score/T improvements over direct ANF, ESOP, SSHR variants, ABC-XAG, ROS-style LUT, mockturtle, CirKit, RevKit CLI, and high-dimensional root/fast baselines.",
            evidence_files=(
                RESULTS / "analysis_paired_statistical_evidence.md",
                RESULTS / "analysis_paired_effect_uncertainty.md",
                TABLES / "paired_statistical_evidence.tex",
                TABLES / "paired_effect_uncertainty.tex",
                FIGURES / "fig2_traditional_resources.pdf",
                FIGURES / "fig3_baseline_comparisons.pdf",
            ),
            boundary="The strongest claim is T-count and weighted-score improvement; raw CNOT/depth/ancilla tradeoffs remain explicit.",
            next_action="Keep effect-size claims paired and matched by function name.",
        ),
        GoalItem(
            requirement="Multi-resource tradeoff audit",
            status=status_if(
                (
                    RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                    RESULTS / "analysis_schedule_metrics.md",
                    RESULTS / "analysis_schedule_proxy_audit.md",
                    TABLES / "multimetric_pairwise_dominance.tex",
                    TABLES / "multimetric_nondominated.tex",
                    TABLES / "schedule_proxy_audit.tex",
                )
            ),
            evidence="Raw Pareto dominance and compact schedule-proxy audits are computed separately on T-count, CNOT, depth, peak ancilla, T-depth proxy, and explicit auxiliary lifetime so weighted-score wins are not overstated.",
            evidence_files=(
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "analysis_schedule_metrics.md",
                RESULTS / "analysis_schedule_proxy_audit.md",
                TABLES / "multimetric_pairwise_dominance.tex",
                TABLES / "multimetric_nondominated.tex",
                TABLES / "schedule_proxy_audit.tex",
            ),
            boundary="Many strong baselines remain incomparable on raw resources; schedule metrics are logical proxies before routing/native scheduling.",
            next_action="Do not convert weighted-score wins into universal raw-resource dominance claims.",
        ),
        GoalItem(
            requirement="Large-scale and bridge experiments",
            status=status_if(
                (
                    RESULTS / "analysis_scaling_resource_audit.md",
                    RESULTS / "analysis_screen_scale_ultra_scale64_stress.md",
                    RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md",
                    RESULTS / "manifest_screen_scale_ultra_scale64_stress.json",
                    RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json",
                    TABLES / "scaling_resource_audit.tex",
                    TABLES / "screen_scale_ultra_scale64_stress.tex",
                    TABLES / "screen_scale_ultra_scale64_resource_profile.tex",
                    RESULTS / "raw_screen_scale_ultra_scale64_terms.csv",
                    RESULTS / "raw_truth_bridge_terms.csv",
                    RESULTS / "raw_truth_bridge_n24_terms.csv",
                    RESULTS / "raw_truth_bridge_n25_terms.csv",
                    RESULTS / "raw_truth_bridge_n26_terms.csv",
                    FIGURES / "fig5_validation.pdf",
                )
            ),
            evidence="Scaling audit covers n=20,24,28,32,40 plus an n=48,56,64 ultra-scale symbolic stress and resource-profile slice and complete truth-table bridge checks for n=21--26 generated functions.",
            evidence_files=(
                RESULTS / "analysis_scaling_resource_audit.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_stress.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md",
                RESULTS / "manifest_screen_scale_ultra_scale64_stress.json",
                RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json",
                TABLES / "scaling_resource_audit.tex",
                TABLES / "screen_scale_ultra_scale64_stress.tex",
                TABLES / "screen_scale_ultra_scale64_resource_profile.tex",
                RESULTS / "raw_screen_scale_ultra_scale64_terms.csv",
                RESULTS / "raw_truth_bridge_terms.csv",
                RESULTS / "raw_truth_bridge_n24_terms.csv",
                RESULTS / "raw_truth_bridge_n25_terms.csv",
                RESULTS / "raw_truth_bridge_n26_terms.csv",
                FIGURES / "fig5_validation.pdf",
            ),
            boundary="High-dimensional rows outside generated bridge slices are symbolic checks, not exhaustive truth-table enumeration for all n=27--64 functions.",
            next_action="Keep large-scale claims tied to the scaling audit and bridge scope.",
        ),
        GoalItem(
            requirement="Multicore/GPU-aware reproducibility",
            status=status_if((RESULTS / "analysis_reproducibility_audit.md", TABLES / "reproducibility_audit.tex")),
            evidence="Compute audit records Apple M4 Pro CPU/GPU/MPS availability, worker counts up to 10, and external tool commit provenance.",
            evidence_files=(RESULTS / "analysis_reproducibility_audit.md", TABLES / "reproducibility_audit.tex"),
            boundary="Wall-clock timings are workstation context; portable claims remain logical resources and verification status.",
            next_action="Rerun reproducibility audit after adding scripts, raw data, summaries, manifests, tables, or figures.",
        ),
        GoalItem(
            requirement="Rich paper figures and tables",
            status="pass" if figure_panels >= 7 and table_count >= 100 and FIGURE_ASSET_ANALYSIS.exists() else "needs evidence",
            evidence=f"Current package has {figure_panels} submitted figure panels and {table_count} generated paper tables; figure asset audit checks PDF/PNG/SVG outputs and source-data CSVs.",
            evidence_files=(FIGURES, TABLES, FIGURE_ASSET_ANALYSIS, RESULTS / "analysis_reproducibility_audit.md"),
            boundary="Counts describe manuscript artifacts, not independent experimental datasets.",
            next_action="Spot-check figure/table readability after every layout or data update.",
        ),
        GoalItem(
            requirement="Complete LaTeX manuscript draft",
            status="pass" if pages not in {"missing", "unknown"} and PAPER.exists() else "needs evidence",
            evidence=f"Compiled submission PDF exists with {pages} pages and the TeX source is present; an ACM/TQC anonymous review-format smoke draft is generated and audited separately.",
            evidence_files=(
                PAPER,
                PDF,
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex",
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.pdf",
                RESULTS / "analysis_target_venue_format_smoke.md",
                RESULTS / "analysis_submission_readiness_audit.md",
            ),
            boundary="Author names, ACM CCS/rights metadata, target-venue final policy choices, and final declarations remain external author inputs.",
            next_action="After author metadata is supplied, recompile the author, anonymous, and ACM/TQC drafts and rerun readiness checks.",
        ),
        GoalItem(
            requirement="Reproducible submission payload",
            status=status_if(
                (
                    THIS_DIR / "rebuild_submission_package.sh",
                    THIS_DIR / "make_submission_payload_archive.py",
                    THIS_DIR / "analyze_payload_roundtrip_audit.py",
                    RESULTS / "analysis_submission_archive_manifest.md",
                    RESULTS / "analysis_submission_payload_archive.md",
                    RESULTS / "analysis_payload_roundtrip_audit.md",
                    PAYLOAD,
                    PAYLOAD_SHA256,
                )
            ),
            evidence="Rebuild script regenerates paper-facing outputs and the payload archive; archive, SHA256 sidecar, and payload round-trip integrity audit are present.",
            evidence_files=(
                THIS_DIR / "rebuild_submission_package.sh",
                THIS_DIR / "make_submission_payload_archive.py",
                THIS_DIR / "analyze_payload_roundtrip_audit.py",
                RESULTS / "analysis_submission_archive_manifest.md",
                RESULTS / "analysis_submission_payload_archive.md",
                RESULTS / "analysis_payload_roundtrip_audit.md",
                PAYLOAD,
                PAYLOAD_SHA256,
            ),
            boundary="The lightweight rebuild does not rerun raw sweeps, external probes, or neural training jobs; round-trip audit verifies packaging integrity, not scientific correctness.",
            next_action="Rerun the rebuild script after any payload-affecting edit.",
        ),
        GoalItem(
            requirement="Anonymous-review submission path",
            status=status_if(
                (
                    RESULTS / "analysis_anonymous_review_readiness.md",
                    RESULTS / "summary_anonymous_review_readiness.csv",
                    RESULTS / "manifest_anonymous_review_readiness.json",
                    ANONYMOUS_TEX,
                )
            ),
            evidence="Anonymous-review audit separates the current author-labeled draft from the double-blind path and a generated anonymous source draft is present.",
            evidence_files=(
                RESULTS / "analysis_anonymous_review_readiness.md",
                RESULTS / "summary_anonymous_review_readiness.csv",
                RESULTS / "manifest_anonymous_review_readiness.json",
                ANONYMOUS_TEX,
                ANONYMOUS_PDF,
            ),
            boundary="This prepares the double-blind path but does not make the current author-labeled manuscript itself double-blind ready.",
            next_action="If the target venue requires double-blind review, create an anonymized manuscript copy and anonymous archive/repository links before upload.",
        ),
        GoalItem(
            requirement="Final author and venue metadata",
            status="needs author input" if metadata_needs else "pass",
            evidence=f"Submission metadata audit reports {metadata_needs} author/venue field group(s) needing author input; target-venue decision auditing, ACM/TQC format smoke, private metadata validation, synthetic metadata-pipeline self-testing, metadata-closure-path auditing, and text-preview generation are prepared for filled metadata.",
            evidence_files=(
                RESULTS / "analysis_target_venue_decision_audit.md",
                RESULTS / "analysis_target_venue_format_smoke.md",
                RESULTS / "analysis_submission_metadata_audit.md",
                RESULTS / "analysis_submission_metadata_validator.md",
                RESULTS / "analysis_submission_metadata_pipeline_selftest.md",
                RESULTS / "analysis_submission_metadata_closure_path.md",
                RESULTS / "analysis_submission_text_preview.md",
                RESULTS / "analysis_anonymous_review_readiness.md",
                THIS_DIR / "submission_package" / "target_venue_brief.md",
                THIS_DIR / "submission_package" / "author_declarations_template.md",
                THIS_DIR / "submission_package" / "cover_letter_template.md",
                THIS_DIR / "submission_package" / "submission_checklist.md",
            ),
            boundary="These fields cannot be inferred from code or experiments and must be confirmed by the author or target venue.",
            next_action="Fill author order, affiliations, ORCIDs, funding, acknowledgements, competing interests, archive links, license, disclosure, and target-venue fields, then review generated private submission text previews.",
        ),
        GoalItem(
            requirement="Overall goal closure gate",
            status="needs author input" if metadata_needs else "pass",
            evidence=f"Metadata audit reports {metadata_needs} human-gated group(s); readiness audit remains the paper/package gate and is cited as a separate evidence file.",
            evidence_files=(
                RESULTS / "analysis_submission_readiness_audit.md",
                RESULTS / "analysis_submission_metadata_audit.md",
                RESULTS / "analysis_submission_metadata_validator.md",
                RESULTS / "analysis_submission_metadata_pipeline_selftest.md",
                RESULTS / "analysis_submission_metadata_closure_path.md",
                RESULTS / "analysis_submission_text_preview.md",
                RESULTS / "analysis_anonymous_review_readiness.md",
            ),
            boundary="The research/package side is audit-complete, but the full objective is not closed until author and target-venue metadata are supplied.",
            next_action="Do not mark the objective complete until the author-specific declarations and final archive/venue links are filled and audits rerun.",
        ),
    ]


def row_dict(item: GoalItem) -> dict[str, str]:
    return {
        "requirement": item.requirement,
        "status": item.status,
        "evidence": item.evidence,
        "evidence_files": "; ".join(rel(path) for path in item.evidence_files),
        "boundary": item.boundary,
        "next_action": item.next_action,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["requirement", "status", "evidence", "evidence_files", "boundary", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    complete = counts.get("needs author input", 0) == 0 and counts.get("needs evidence", 0) == 0
    lines = [
        "# Goal Completion Audit",
        "",
        "This audit maps the original project objective to concrete current-state evidence.",
        "",
        f"Overall closure: {'complete' if complete else 'not complete'}",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Requirement Matrix",
            "",
            "| requirement | status | evidence | boundary | next action |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {requirement} | {status} | {evidence} | {boundary} | {next_action} |".format(
                **row
            )
        )
    lines.extend(["", "## Evidence Files", ""])
    for row in rows:
        lines.append(f"- **{row['requirement']}**: {row['evidence_files']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "status_counts": counts,
        "overall_closure": "complete" if counts.get("needs author input", 0) == 0 and counts.get("needs evidence", 0) == 0 else "not complete",
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_goal_completion_audit.csv"),
            "analysis": rel(RESULTS / "analysis_goal_completion_audit.md"),
            "manifest": rel(RESULTS / "manifest_goal_completion_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [row_dict(item) for item in build_items()]
    write_csv(RESULTS / "summary_goal_completion_audit.csv", rows)
    write_markdown(RESULTS / "analysis_goal_completion_audit.md", rows)
    write_manifest(RESULTS / "manifest_goal_completion_audit.json", rows)
    print(f"wrote {len(rows)} goal completion rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
