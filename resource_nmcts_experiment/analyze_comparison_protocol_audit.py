#!/usr/bin/env python3
"""Audit whether the baseline comparison protocol is reviewer-complete.

The manuscript uses many baseline families that are comparable at different
abstraction levels.  This audit verifies that every comparison layer has four
pieces of support: a role in the baseline-claim matrix, quantitative evidence
or artifact outputs, a comparability boundary, and a manuscript/brief anchor
that prevents the result from being presented as a universal leaderboard.
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

CLAIM_MATRIX = RESULTS / "summary_baseline_claim_matrix.csv"
EVIDENCE_MATRIX = RESULTS / "summary_comparison_evidence_matrix.csv"
COMPARABILITY = RESULTS / "summary_baseline_comparability_audit.csv"
COUNTERPOINT = RESULTS / "summary_counterpoint_claim_boundary.csv"


@dataclass(frozen=True)
class ProtocolSpec:
    layer: str
    reviewer_question: str
    claim_tokens: tuple[str, ...]
    evidence_tokens: tuple[str, ...]
    comparability_tokens: tuple[str, ...]
    counterpoint_tokens: tuple[str, ...]
    artifact_files: tuple[Path, ...]
    manuscript_tokens: tuple[str, ...]
    usable_conclusion: str
    excluded_conclusion: str


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def row_texts(rows: list[dict[str, str]]) -> list[str]:
    return [" | ".join(str(value) for value in row.values()) for row in rows]


def count_matches(haystacks: list[str], tokens: tuple[str, ...]) -> int:
    return sum(1 for token in tokens if any(token in haystack for haystack in haystacks))


def spec_rows() -> list[ProtocolSpec]:
    return [
        ProtocolSpec(
            layer="Primary same-task Boolean-oracle baselines",
            reviewer_question="Is the method only compared with weak or self-written constructions?",
            claim_tokens=("Primary resource-efficiency baselines",),
            evidence_tokens=("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            comparability_tokens=("Direct algebraic and ESOP baselines", "SSHR-H and SSHR-I"),
            counterpoint_tokens=("SSHR family CNOT optimum",),
            artifact_files=(
                RESULTS / "raw_traditional_resource.csv",
                RESULTS / "raw_external_traditional_resource_n6.csv",
                RESULTS / "analysis_paired_statistical_evidence.md",
            ),
            manuscript_tokens=("Direct \\anf{}", "ESOP", "SSHR", "Baseline claim matrix"),
            usable_conclusion="Matched bit-flip oracle baselines support lower T-count and weighted score under the paper's logical model.",
            excluded_conclusion="They do not prove universal CNOT, depth, ancilla, line-count, or hardware-mapped optimality.",
        ),
        ProtocolSpec(
            layer="External logic-network and LUT/XAG/AIG probes",
            reviewer_question="Does the advantage survive mature external logic-synthesis toolchains?",
            claim_tokens=("External logic-network probes",),
            evidence_tokens=("ROS-style LUT proxy", "mockturtle KLUT-to-XAG probe", "CirKit AIG/MC probe"),
            comparability_tokens=("ABC/BDD and exported logic networks", "ROS-style LUT, mockturtle, and CirKit probes"),
            counterpoint_tokens=("CirKit AIG/MC depth",),
            artifact_files=(
                RESULTS / "raw_ros_lut_proxy_best.csv",
                RESULTS / "raw_mockturtle_xag_probe.csv",
                RESULTS / "raw_cirkit_aig_probe.csv",
            ),
            manuscript_tokens=("ROS-style LUT", "mockturtle", "CirKit", "external or traditional baselines"),
            usable_conclusion="External probes test whether the score advantage persists beyond the project's internal baselines.",
            excluded_conclusion="They are not a full ROS SAT garbage-management flow, reversible emission, or hardware-mapped comparison.",
        ),
        ProtocolSpec(
            layer="Exact reversible-synthesis counterpoint",
            reviewer_question="Is there a reversible-synthesis comparison, not only logic-network proxies?",
            claim_tokens=("Exact reversible-synthesis probe",),
            evidence_tokens=("Legacy RevKit CLI exact oracle",),
            comparability_tokens=("Legacy RevKit CLI exact-oracle portfolio",),
            counterpoint_tokens=("RevKit exact-oracle auxiliary lines",),
            artifact_files=(
                RESULTS / "raw_revkit_cli_multiflow_traditional.csv",
                RESULTS / "analysis_revkit_cli_multiflow_traditional.md",
            ),
            manuscript_tokens=("Legacy RevKit CLI", "exact reversible-oracle", "auxiliary-line counterpoint"),
            usable_conclusion="RevKit CLI supports a genuine exact-oracle reversible-synthesis probe with lower T/score for Resource-NMCTS.",
            excluded_conclusion="It does not imply lower auxiliary-line count, routed depth, or mapped Clifford+T cost.",
        ),
        ProtocolSpec(
            layer="Phase/Rz proxy branch",
            reviewer_question="How is the RevKit phase/Rz gate-set mismatch handled?",
            claim_tokens=("Phase/Rz branch",),
            evidence_tokens=("RevKit phase/Rz branch", "Learned phase pruning"),
            comparability_tokens=("Phase/Rz baselines and learned shortlist",),
            counterpoint_tokens=(),
            artifact_files=(
                RESULTS / "raw_phase_parity_affine.csv",
                RESULTS / "raw_phase_affine_policy_rank_diverse.csv",
                RESULTS / "analysis_rz_synthesis_cost.md",
            ),
            manuscript_tokens=("phase/Rz", "global phase", "does not output approximate rotation sequences"),
            usable_conclusion="The phase branch supports a logical Rz/phase proxy and learned affine shortlist result.",
            excluded_conclusion="It is not a final approximate-rotation sequence or Clifford+T decomposition.",
        ),
        ProtocolSpec(
            layer="Internal search-control ablations",
            reviewer_question="Is the AI/MCTS contribution separated from the algebraic search space?",
            claim_tokens=("Internal search ablations",),
            evidence_tokens=(),
            comparability_tokens=(),
            counterpoint_tokens=("Learned prior is incremental",),
            artifact_files=(
                RESULTS / "analysis_search_contribution.md",
                RESULTS / "analysis_learned_control_audit.md",
                RESULTS / "analysis_sparse_depth_frontier.md",
                RESULTS / "analysis_sparse_depth4_gate_threshold_sensitivity.md",
            ),
            manuscript_tokens=("Search contribution decomposition", "Learned-control audit", "deep-RL-only"),
            usable_conclusion="Ablations support bounded search-control, pruning, gating, and planning-time gains.",
            excluded_conclusion="They do not show that deep reinforcement learning alone causes the main resource drop.",
        ),
        ProtocolSpec(
            layer="Scaling and correctness bridges",
            reviewer_question="Does the work go beyond small truth-table functions while preserving correctness evidence?",
            claim_tokens=("Scaling and correctness bridges",),
            evidence_tokens=("High-dimensional frontier search", "Complete truth-table bridges"),
            comparability_tokens=("High-dimensional symbolic and bridge checks",),
            counterpoint_tokens=("Large-n verification is bounded",),
            artifact_files=(
                RESULTS / "raw_screen_scale_depth_frontier_terms.csv",
                RESULTS / "raw_truth_bridge_terms.csv",
                RESULTS / "analysis_scaling_resource_audit.md",
            ),
            manuscript_tokens=("n=20", "n=21", "complete truth-table bridge", "symbolic"),
            usable_conclusion="Large rows support logical symbolic correctness and bridge-truth-table verification within the stated envelope.",
            excluded_conclusion="They do not prove exhaustive high-dimensional truth-table optimality or benchmarking completeness.",
        ),
        ProtocolSpec(
            layer="Trade-off and non-dominance audits",
            reviewer_question="Does the weighted score hide unfavorable CNOT, depth, ancilla, or runtime behavior?",
            claim_tokens=("Trade-off audits",),
            evidence_tokens=(),
            comparability_tokens=(),
            counterpoint_tokens=("SSHR family CNOT optimum", "CirKit AIG/MC depth", "RevKit exact-oracle auxiliary lines"),
            artifact_files=(
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "analysis_counterpoint_claim_boundary.md",
                RESULTS / "analysis_weight_robustness.md",
            ),
            manuscript_tokens=("Multi-resource tradeoff", "not a CNOT-only dominance", "universal leaderboard"),
            usable_conclusion="The paper can claim a strong T/weighted-score point while explicitly reporting unfavorable resource dimensions.",
            excluded_conclusion="It cannot report a single-metric score win as complete Pareto or hardware dominance.",
        ),
    ]


def evaluate(spec: ProtocolSpec, joined: dict[str, list[str]], manuscript_text: str) -> dict[str, str]:
    claim_hits = count_matches(joined["claim"], spec.claim_tokens)
    evidence_hits = count_matches(joined["evidence"], spec.evidence_tokens)
    comparability_hits = count_matches(joined["comparability"], spec.comparability_tokens)
    counterpoint_hits = count_matches(joined["counterpoint"], spec.counterpoint_tokens)
    artifact_hits = sum(1 for path in spec.artifact_files if path.exists())
    manuscript_hits = sum(1 for token in spec.manuscript_tokens if token in manuscript_text)

    checks = [
        claim_hits == len(spec.claim_tokens),
        evidence_hits == len(spec.evidence_tokens),
        comparability_hits == len(spec.comparability_tokens),
        counterpoint_hits == len(spec.counterpoint_tokens),
        artifact_hits == len(spec.artifact_files),
        manuscript_hits == len(spec.manuscript_tokens),
    ]
    status = "pass" if all(checks) else "needs revision"
    evidence = (
        f"claim={claim_hits}/{len(spec.claim_tokens)}; "
        f"evidence={evidence_hits}/{len(spec.evidence_tokens)}; "
        f"comparability={comparability_hits}/{len(spec.comparability_tokens)}; "
        f"counterpoint={counterpoint_hits}/{len(spec.counterpoint_tokens)}; "
        f"artifacts={artifact_hits}/{len(spec.artifact_files)}; "
        f"manuscript={manuscript_hits}/{len(spec.manuscript_tokens)}"
    )
    next_action = (
        "No action needed; keep this layer bounded by its excluded conclusion."
        if status == "pass"
        else "Add or regenerate the missing claim/evidence/comparability/counterpoint artifacts before relying on this comparison layer."
    )
    return {
        "layer": spec.layer,
        "status": status,
        "reviewer_question": spec.reviewer_question,
        "evidence": evidence,
        "usable_conclusion": spec.usable_conclusion,
        "excluded_conclusion": spec.excluded_conclusion,
        "next_action": next_action,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["layer", "status", "reviewer_question", "evidence", "usable_conclusion", "excluded_conclusion", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Comparison Protocol Audit",
        "",
        "This audit answers the reviewer-facing question: what is the method compared against, and why is each comparison meaningful?",
        "",
        "It cross-checks the baseline claim matrix, evidence matrix, comparability audit, counterpoint audit, manuscript anchors, and required artifacts.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Layers",
            "",
            "| comparison layer | status | reviewer question | evidence | usable conclusion | excluded conclusion |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {layer} | {status} | {reviewer_question} | {evidence} | {usable_conclusion} | {excluded_conclusion} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("Resource-NMCTS", r"\method{}"),
        ("MCTS", r"\mcts{}"),
        ("T-count", r"T-count"),
        ("CNOT", r"CNOT"),
        ("Rz", r"\rz{}"),
        ("n=20", r"$n=20$"),
        ("n=21", r"$n=21$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"Comparison layer & Reviewer question & Usable conclusion & Excluded conclusion \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["layer"]),
                latex_cell(row["reviewer_question"]),
                latex_cell(row["usable_conclusion"]),
                latex_cell(row["excluded_conclusion"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "layers": len(rows),
        "needs_revision_count": status_counts.get("needs revision", 0),
        "status_counts": status_counts,
        "source_files": {
            "claim_matrix": str(CLAIM_MATRIX.relative_to(THIS_DIR)),
            "evidence_matrix": str(EVIDENCE_MATRIX.relative_to(THIS_DIR)),
            "comparability": str(COMPARABILITY.relative_to(THIS_DIR)),
            "counterpoint": str(COUNTERPOINT.relative_to(THIS_DIR)),
            "paper": str(PAPER.relative_to(THIS_DIR)),
            "reviewer_brief": str(REVIEWER_BRIEF.relative_to(THIS_DIR)),
            "editor_brief": str(EDITOR_BRIEF.relative_to(THIS_DIR)),
        },
        "outputs": {
            "summary": "results/summary_comparison_protocol_audit.csv",
            "analysis": "results/analysis_comparison_protocol_audit.md",
            "manifest": "results/manifest_comparison_protocol_audit.json",
            "table": "paper_latex/tables/comparison_protocol_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    joined = {
        "claim": row_texts(read_csv(CLAIM_MATRIX)),
        "evidence": row_texts(read_csv(EVIDENCE_MATRIX)),
        "comparability": row_texts(read_csv(COMPARABILITY)),
        "counterpoint": row_texts(read_csv(COUNTERPOINT)),
    }
    manuscript_text = "\n".join([read_text(PAPER), read_text(REVIEWER_BRIEF), read_text(EDITOR_BRIEF)])
    rows = [evaluate(spec, joined, manuscript_text) for spec in spec_rows()]
    write_csv(RESULTS / "summary_comparison_protocol_audit.csv", rows)
    write_markdown(RESULTS / "analysis_comparison_protocol_audit.md", rows)
    write_latex(TABLES / "comparison_protocol_audit.tex", rows)
    write_manifest(RESULTS / "manifest_comparison_protocol_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} comparison protocol rows")
    if failures:
        print(f"warning: {failures} comparison protocol row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
