#!/usr/bin/env python3
"""Build a reviewer-facing novelty and comparison scorecard.

This audit answers a narrow but important submission question: what is the
method compared with, and why are those comparisons meaningful rather than a
single cherry-picked leaderboard?  It ties each reviewer concern to concrete
artifacts and manuscript/support-document anchors.
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
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
REVIEWER_BRIEF = THIS_DIR / "submission_package" / "reviewer_concern_brief.md"
EDITOR_BRIEF = THIS_DIR / "submission_package" / "editor_screening_brief.md"


@dataclass(frozen=True)
class ScorecardRow:
    question: str
    answer: str
    artifacts: tuple[str, ...]
    manuscript_tokens: tuple[str, ...]
    support_tokens: tuple[str, ...]
    evidence_latex: str
    limitation: str


ROWS = (
    ScorecardRow(
        question="Is this only an SSHR variant?",
        answer="No. Resource-NMCTS searches ANF/FPRM and Boolean-ring actions; SSHR is a CNOT-oriented small-function counterpoint.",
        artifacts=(
            "results/analysis_contribution_evidence_map.md",
            "results/analysis_baseline_claim_matrix.md",
            "results/analysis_counterpoint_claim_boundary.md",
            "paper_latex/tables/contribution_evidence_map.tex",
            "paper_latex/tables/counterpoint_claim_boundary.tex",
        ),
        manuscript_tokens=(
            "rather than as an SSHR",
            "SSHR is used only as a CNOT-oriented",
            "not an SSHR parallelotope search",
        ),
        support_tokens=("Is this only an SSHR variant?", "does not use SSHR parallelotope candidates"),
        evidence_latex=r"Tables~\ref{tab:contribution-map}, \ref{tab:counterpoint-boundary}",
        limitation="SSHR remains a strong CNOT reference; the paper claims T-count and weighted-score gains, not CNOT dominance.",
    ),
    ScorecardRow(
        question="Are the primary baselines matched to the oracle task?",
        answer="Yes. Direct ANF, AND-direct ANF, ESOP/MILP, BDD/ABC, and SSHR rows are paired on the same Boolean-oracle functions and resource score.",
        artifacts=(
            "results/analysis_comparison_evidence_matrix.md",
            "results/analysis_esop_baseline.md",
            "results/analysis_paired_statistical_evidence.md",
            "results/raw_traditional_resource.csv",
            "paper_latex/tables/comparison_evidence_matrix.tex",
            "paper_latex/tables/paired_statistical_evidence.tex",
        ),
        manuscript_tokens=("Direct \\anf{}", "ESOP", "matched", "weighted score"),
        support_tokens=("Direct ANF, ESOP", "layered comparisons"),
        evidence_latex=r"Tables~\ref{tab:evidence-matrix}, \ref{tab:paired-statistics}",
        limitation="These prove matched logical-resource improvements, not hardware-mapped optimality.",
    ),
    ScorecardRow(
        question="Does the comparison go beyond internal baselines?",
        answer="Yes. The package includes ROS-style LUT, mockturtle, Caterpillar API, CirKit, RevKit CLI, ABC/BDD, and RevKit phase/Rz probes.",
        artifacts=(
            "results/raw_ros_lut_proxy_best.csv",
            "results/raw_mockturtle_xag_probe.csv",
            "results/raw_caterpillar_xag_api_best.csv",
            "results/analysis_caterpillar_xag_api_probe.md",
            "results/raw_cirkit_aig_probe.csv",
            "results/raw_revkit_cli_multiflow_traditional.csv",
            "results/analysis_ros_reproduction_gap_audit.md",
            "paper_latex/tables/caterpillar_xag_api_probe.tex",
            "paper_latex/tables/revkit_cli_multiflow_traditional.tex",
        ),
        manuscript_tokens=("ROS-style LUT", "mockturtle", "Caterpillar API", "CirKit", "RevKit CLI"),
        support_tokens=("External toolchain probes", "Caterpillar API", "RevKit CLI"),
        evidence_latex=r"Fig.~\ref{fig:baselines}; Tables~\ref{tab:ros-line}, \ref{tab:caterpillar-xag-api}, \ref{tab:revkit-cli}",
        limitation="External rows are logic-level or exact-oracle probes; they are not full hardware mapping or full ROS reproduction.",
    ),
    ScorecardRow(
        question="Does a score win hide unfavorable resources?",
        answer="No. Counterpoint, Pareto, and schedule-proxy audits report where SSHR, Caterpillar, CirKit, and RevKit remain strong.",
        artifacts=(
            "results/analysis_counterpoint_claim_boundary.md",
            "results/analysis_multimetric_pareto_tradeoff.md",
            "results/analysis_schedule_proxy_audit.md",
            "paper_latex/tables/counterpoint_claim_boundary.tex",
            "paper_latex/tables/multimetric_nondominated.tex",
            "paper_latex/tables/schedule_proxy_audit.tex",
        ),
        manuscript_tokens=(
            "not that \\method{} dominates every metric",
            "Caterpillar API is a strong",
            "CirKit AIG/MC remains a",
            "RevKit CLI uses fewer auxiliary lines",
        ),
        support_tokens=("Does the method dominate every resource?", "Caterpillar API", "not universal dominance"),
        evidence_latex=r"Tables~\ref{tab:counterpoint-boundary}, \ref{tab:multimetric-nondominated}, \ref{tab:schedule-proxy-audit}",
        limitation="The correct claim is a strong T/weighted-score point with explicit CNOT, depth, ancilla, and runtime tradeoffs.",
    ),
    ScorecardRow(
        question="Is AI/MCTS actually isolated from deterministic search?",
        answer="Yes. The search-control audit separates heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, random-prior, random-depth, and phase controls.",
        artifacts=(
            "results/analysis_search_control_baseline_audit.md",
            "results/analysis_bitflip_random_prior_control.md",
            "results/analysis_frontier_random_depth_control.md",
            "results/analysis_learned_control_audit.md",
            "paper_latex/tables/search_control_baseline_audit.tex",
            "paper_latex/tables/learned_control_audit.tex",
        ),
        manuscript_tokens=("Search-control baseline audit", "random-prior", "random-depth", "deep reinforcement learning alone"),
        support_tokens=("bounded controls", "not as evidence that deep learning alone explains"),
        evidence_latex=r"Tables~\ref{tab:search-control-baseline-audit}, \ref{tab:learned-control-audit}",
        limitation="The learned components are promoted only where they give bounded quality, pruning, or budget-allocation evidence.",
    ),
    ScorecardRow(
        question="Does the study go beyond small truth-table functions?",
        answer="Yes. Large n=20,24,28,32,40 symbolic term-set runs and an n=48,56,64 ultra-scale stress slice are paired with n=21--30 complete truth-table bridge slices.",
        artifacts=(
            "results/analysis_scaling_resource_audit.md",
            "results/raw_truth_bridge_terms.csv",
            "results/raw_truth_bridge_n24_terms.csv",
            "results/raw_truth_bridge_n25_terms.csv",
            "results/raw_truth_bridge_n26_terms.csv",
            "results/raw_truth_bridge_n27_terms.csv",
            "results/raw_truth_bridge_n28_terms.csv",
            "results/raw_truth_bridge_n29_terms.csv",
            "results/raw_truth_bridge_n30_terms.csv",
            "results/analysis_screen_scale_ultra_scale64_stress.md",
            "results/analysis_screen_scale_ultra_scale64_resource_profile.md",
            "paper_latex/tables/scaling_resource_audit.tex",
            "paper_latex/tables/screen_scale_ultra_scale64_stress.tex",
            "paper_latex/tables/screen_scale_ultra_scale64_resource_profile.tex",
            "paper_latex/figures/submission_v36/fig5_validation.pdf",
        ),
        manuscript_tokens=("$n=20,24,28,32,40$", "$n=48,56,64$", "$n=21$--$30$", "complete truth-table bridge"),
        support_tokens=("Complete truth-table checks are used only for bridge slices", "logical-layer"),
        evidence_latex=r"Tables~\ref{tab:scale-audit}, \ref{tab:ultra-scale64-stress}, \ref{tab:ultra-scale64-resource-profile}; Fig.~\ref{fig:validation}",
        limitation="Large-dimensional evidence is symbolic plus bridge-verified, not exhaustive truth-table benchmarking for all large n.",
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def latex_cell(text: str) -> str:
    return (
        latex_escape(text)
        .replace("Resource-NMCTS", r"\method{}")
        .replace("ANF", r"\anf{}")
        .replace("FPRM", r"\fprm{}")
        .replace("MCTS", r"\mcts{}")
        .replace("n=20,24,28,32,40", r"$n=20$, 24, 28, 32, 40")
        .replace("n=48,56,64", r"$n=48$, 56, 64")
        .replace("n=21--30", r"$n=21$--$30$")
        .replace("n=21--25", r"$n=21$--$25$")
    )


def build_rows() -> list[dict[str, str]]:
    paper = read_text(PAPER)
    support = "\n".join(read_text(path) for path in (REVIEWER_BRIEF, EDITOR_BRIEF))
    rows: list[dict[str, str]] = []
    for spec in ROWS:
        missing_files = [path for path in spec.artifacts if not (THIS_DIR / path).exists()]
        missing_manuscript_tokens = [token for token in spec.manuscript_tokens if token not in paper]
        missing_support_tokens = [token for token in spec.support_tokens if token not in support]
        status = "pass" if not missing_files and not missing_manuscript_tokens and not missing_support_tokens else "needs revision"
        rows.append(
            {
                "question": spec.question,
                "status": status,
                "answer": spec.answer,
                "evidence": "; ".join(spec.artifacts),
                "paper_evidence": spec.evidence_latex,
                "limitation": spec.limitation,
                "missing_files": "; ".join(missing_files) if missing_files else "none",
                "missing_manuscript_tokens": "; ".join(missing_manuscript_tokens) if missing_manuscript_tokens else "none",
                "missing_support_tokens": "; ".join(missing_support_tokens) if missing_support_tokens else "none",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "question",
        "status",
        "answer",
        "evidence",
        "paper_evidence",
        "limitation",
        "missing_files",
        "missing_manuscript_tokens",
        "missing_support_tokens",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return counts


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    lines = [
        "# Novelty and Comparison Scorecard",
        "",
        "This scorecard answers whether the comparison set is meaningful and whether the novelty claim is bounded by explicit evidence.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| reviewer question | status | answer | evidence | limitation |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {question} | {status} | {answer} | {paper_evidence} | {limitation} |".format(**safe)
        )
    lines.extend(["", "## Missing Anchors", "", "| reviewer question | missing files | missing manuscript tokens | missing support tokens |", "|---|---|---|---|"])
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {question} | {missing_files} | {missing_manuscript_tokens} | {missing_support_tokens} |".format(**safe)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"Reviewer question & Answer & Evidence & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["question"]),
                latex_cell(row["answer"]),
                row["paper_evidence"],
                latex_cell(row["limitation"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "pass_count": counts.get("pass", 0),
        "outputs": {
            "summary": "results/summary_novelty_comparison_scorecard.csv",
            "analysis": "results/analysis_novelty_comparison_scorecard.md",
            "manifest": "results/manifest_novelty_comparison_scorecard.json",
            "table": "paper_latex/tables/novelty_comparison_scorecard.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_novelty_comparison_scorecard.csv", rows)
    write_markdown(RESULTS / "analysis_novelty_comparison_scorecard.md", rows)
    write_latex(TABLES / "novelty_comparison_scorecard.tex", rows)
    write_manifest(RESULTS / "manifest_novelty_comparison_scorecard.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} novelty/comparison scorecard row(s)")
    if failures:
        print(f"warning: {failures} novelty/comparison row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
