#!/usr/bin/env python3
"""Audit how comparison targets support manuscript claims.

The existing comparison scorecards answer what the method is compared against.
This audit adds the missing hierarchy: which comparison families are allowed to
support headline claims, which ones are stress tests, which ones are
counterpoints, and which ones are attribution or scale checks.  The goal is to
make over-reading harder when the manuscript discusses many heterogeneous
baselines.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

SUMMARY = RESULTS / "summary_comparison_claim_hierarchy.csv"
ANALYSIS = RESULTS / "analysis_comparison_claim_hierarchy.md"
MANIFEST = RESULTS / "manifest_comparison_claim_hierarchy.json"
TABLE = TABLES / "comparison_claim_hierarchy.tex"


@dataclass(frozen=True)
class ClaimTier:
    tier: str
    role: str
    comparison_families: str
    required_files: tuple[str, ...]
    anchor_tokens: tuple[str, ...]
    supported_claim: str
    excluded_claim: str


TIERS = (
    ClaimTier(
        tier="Headline support",
        role="Primary matched logical-oracle evidence",
        comparison_families="Direct ANF, AND-direct, ESOP beam/MILP, ABC-ESOP/BDD same-task projections",
        required_files=(
            "results/analysis_comparison_answer_scorecard.md",
            "results/analysis_comparison_evidence_matrix.md",
            "results/analysis_baseline_claim_matrix.md",
            "results/analysis_paired_statistical_evidence.md",
        ),
        anchor_tokens=(
            "matching functions",
            "Direct \\anf{}",
            "Primary matched logical-oracle rows",
        ),
        supported_claim="Lower T-count and weighted score on matched logical bit-flip Boolean-oracle benchmarks.",
        excluded_claim="No universal CNOT, depth, ancilla, line-count, hardware-mapped, or global-optimality claim.",
    ),
    ClaimTier(
        tier="External stress test",
        role="Independent logical-toolchain pressure",
        comparison_families="ROS-style LUT, mockturtle, Caterpillar API, CirKit, RevKit CLI, ABC AIG/XAG/LUT",
        required_files=(
            "results/analysis_comparison_answer_scorecard.md",
            "results/analysis_caterpillar_xag_api_probe.md",
            "results/analysis_ros_reproduction_gap_audit.md",
            "results/analysis_cirkit_aig_probe.md",
            "results/analysis_revkit_cli_multiflow_traditional.md",
        ),
        anchor_tokens=(
            "ROS-style LUT",
            "mockturtle",
            "Caterpillar API",
            "CirKit",
            "RevKit CLI",
        ),
        supported_claim="The advantage is not an artifact of comparing only against local hand-written baselines.",
        excluded_claim="Not a full ROS SAT garbage-management, reversible-emission, routing, or hardware-mapped comparison.",
    ),
    ClaimTier(
        tier="Counterpoint boundary",
        role="Strong opposing-resource evidence",
        comparison_families="SSHR CNOT, CirKit depth, Caterpillar CNOT, RevKit line count, STG optima",
        required_files=(
            "results/analysis_counterpoint_claim_boundary.md",
            "results/analysis_comparison_target_validity_audit.md",
            "results/analysis_stg_published_benchmark.md",
            "results/analysis_cnot_constraint_profile_audit.md",
        ),
        anchor_tokens=(
            "CirKit is often shallower",
            "RevKit uses fewer",
            "not a hardware-mapped, depth-only, or universal-dominance claim",
        ),
        supported_claim="Other methods keep real CNOT, depth, line-count, or tiny-optimum advantages that bound the claim.",
        excluded_claim="A weighted-score win must not be reported as complete Pareto or hardware-level dominance.",
    ),
    ClaimTier(
        tier="Search-control attribution",
        role="Causal and ablation evidence for AI/search components",
        comparison_families="No-MCTS, beam-only, learned/no-prior, random-prior, random-depth, sparse/guard controls",
        required_files=(
            "results/analysis_search_control_baseline_audit.md",
            "results/analysis_bitflip_random_prior_control.md",
            "results/analysis_frontier_random_depth_control.md",
            "results/analysis_learned_control_audit.md",
            "results/analysis_limited_learned_control_boundary.md",
        ),
        anchor_tokens=(
            "random-prior",
            "random-depth",
            "deep reinforcement learning alone",
        ),
        supported_claim="Neural/MCTS controls provide bounded quality, pruning, or budget-allocation gains over strengthened deterministic controls.",
        excluded_claim="The paper does not claim that deep reinforcement learning alone causes the full resource reduction.",
    ),
    ClaimTier(
        tier="Scaling verification",
        role="Logical correctness beyond small exhaustive truth-table rows",
        comparison_families="n=20--64 symbolic term-set stress and n=21--30 complete truth-table bridges",
        required_files=(
            "results/analysis_scaling_resource_audit.md",
            "results/analysis_screen_scale_ultra_scale64_stress.md",
            "results/analysis_screen_scale_ultra_scale64_resource_profile.md",
            "results/analysis_benchmark_suite_audit.md",
        ),
        anchor_tokens=(
            "$n=48,56,64$",
            "$n=21$--$30$",
            "complete \\ttable{} bridge",
        ),
        supported_claim="Large symbolic circuits and bridge slices preserve logical correctness inside the stated verification envelope.",
        excluded_claim="Not exhaustive high-dimensional truth-table benchmarking or a proof of global optimality.",
    ),
    ClaimTier(
        tier="Related phase transfer",
        role="Secondary logical phase/Rz proxy",
        comparison_families="RevKit oracle_synth, ANF/FPRM phase parity, affine phase shortlist",
        required_files=(
            "results/analysis_phase_parity_affine.md",
            "results/analysis_phase_policy_budget_frontier.md",
            "results/analysis_phase_policy_random_control.md",
            "results/analysis_rotation_synthesis_backend_audit.md",
        ),
        anchor_tokens=(
            "In the phase branch",
            "RevKit phase/Rz",
            "phase/\\rz{} proxies",
        ),
        supported_claim="The search framing transfers to a verified logical phase/Rz proxy and learned shortlist setting.",
        excluded_claim="Not a final approximate-rotation Clifford+T synthesis or a bit-flip headline result.",
    ),
)


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
        .replace("Rz", r"\rz{}")
        .replace("n=20--64", r"$n=20$--$64$")
        .replace("n=21--30", r"$n=21$--$30$")
    )


def build_rows() -> list[dict[str, str]]:
    author = read_text(AUTHOR_TEX)
    anon = read_text(ANON_TEX)
    acm = read_text(ACM_TEX)
    manuscript_blob = "\n".join((author, anon, acm))
    rows: list[dict[str, str]] = []
    for spec in TIERS:
        missing_files = [path for path in spec.required_files if not (THIS_DIR / path).exists()]
        missing_tokens = [token for token in spec.anchor_tokens if token not in manuscript_blob]
        status = "pass" if not missing_files and not missing_tokens else "needs revision"
        rows.append(
            {
                "claim_tier": spec.tier,
                "role": spec.role,
                "comparison_families": spec.comparison_families,
                "supported_claim": spec.supported_claim,
                "excluded_claim": spec.excluded_claim,
                "status": status,
                "missing_files": "; ".join(missing_files) if missing_files else "none",
                "missing_manuscript_tokens": "; ".join(missing_tokens) if missing_tokens else "none",
            }
        )

    table_anchor = "\\input{tables/comparison_claim_hierarchy}"
    table_refs = [
        ("author", table_anchor in author),
        ("anonymous", table_anchor in anon),
        ("acm_tqc", table_anchor in acm),
    ]
    rows.append(
        {
            "claim_tier": "Manuscript integration",
            "role": "Generated table is included in all submission TeX variants",
            "comparison_families": "author, anonymous, ACM TQC",
            "supported_claim": "The claim hierarchy is visible where comparison scope is introduced.",
            "excluded_claim": "The hierarchy is not only a detached support-package audit.",
            "status": "pass" if all(ok for _, ok in table_refs) else "needs revision",
            "missing_files": "none",
            "missing_manuscript_tokens": "; ".join(name for name, ok in table_refs if not ok) or "none",
        }
    )
    return rows


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return counts


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "claim_tier",
        "role",
        "comparison_families",
        "supported_claim",
        "excluded_claim",
        "status",
        "missing_files",
        "missing_manuscript_tokens",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    lines = [
        "# Comparison Claim Hierarchy",
        "",
        "This audit classifies each comparison family by how it may be used in the manuscript claim.",
        "",
        "## Status counts",
        "",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "| claim tier | role | comparison families | supported claim | excluded claim | status |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {claim_tier} | {role} | {comparison_families} | {supported_claim} | {excluded_claim} | {status} |".format(
                **row
            )
        )
    lines += [
        "",
        "## Missing anchors",
        "",
        "| claim tier | missing files | missing manuscript tokens |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['claim_tier']} | {row['missing_files']} | {row['missing_manuscript_tokens']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    display_rows = [row for row in rows if row["claim_tier"] != "Manuscript integration"]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.21\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}}",
        r"\toprule",
        r"Claim tier & Role & Comparison families & Supported claim & Excluded claim \\",
        r"\midrule",
    ]
    for row in display_rows:
        lines.append(
            " & ".join(
                latex_cell(row[key])
                for key in (
                    "claim_tier",
                    "role",
                    "comparison_families",
                    "supported_claim",
                    "excluded_claim",
                )
            )
            + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    manuscript_blob = "\n".join(read_text(path) for path in (AUTHOR_TEX, ANON_TEX, ACM_TEX))
    manifest = {
        "summary": str(SUMMARY.relative_to(THIS_DIR)),
        "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
        "latex_table": str(TABLE.relative_to(THIS_DIR)),
        "rows": len(rows),
        "claim_tiers": [row["claim_tier"] for row in rows],
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "table_anchor_present": "\\input{tables/comparison_claim_hierarchy}" in manuscript_blob,
        "generated_from": [
            str(path.relative_to(THIS_DIR))
            for path in (AUTHOR_TEX, ANON_TEX, ACM_TEX)
        ],
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {SUMMARY.relative_to(THIS_DIR)}")
    print(f"status_counts={status_counts(rows)}")


if __name__ == "__main__":
    main()
