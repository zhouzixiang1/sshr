#!/usr/bin/env python3
"""Audit whether each comparison target has a meaningful role.

The comparison protocol audit checks completeness.  This companion audit is
more direct: it labels each target family as a primary benchmark, external
probe, exact reversible counterpoint, phase proxy, control, scalability check,
or trade-off counterpoint, and verifies that the supporting evidence and
claim-boundary artifacts exist.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"

CLAIM_MATRIX = RESULTS / "summary_baseline_claim_matrix.csv"
EVIDENCE_MATRIX = RESULTS / "summary_comparison_evidence_matrix.csv"
COMPARABILITY_AUDIT = RESULTS / "summary_baseline_comparability_audit.csv"
COUNTERPOINT_AUDIT = RESULTS / "summary_counterpoint_claim_boundary.csv"
RELATED_POSITIONING = RESULTS / "summary_related_work_positioning.csv"
SEARCH_CONTROL_AUDIT = RESULTS / "summary_search_control_baseline_audit.csv"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"


@dataclass(frozen=True)
class TargetSpec:
    family: str
    role: str
    compared_against: str
    meaning_test: str
    required_claim_tokens: tuple[str, ...]
    required_evidence_tokens: tuple[str, ...]
    required_comparability_tokens: tuple[str, ...]
    required_counterpoint_tokens: tuple[str, ...]
    required_related_tokens: tuple[str, ...]
    required_control_tokens: tuple[str, ...]
    required_artifacts: tuple[Path, ...]
    supported_statement: str
    invalid_statement: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_csv_text(path: Path) -> str:
    if not path.exists():
        return ""
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return "\n".join(" | ".join(str(value) for value in row.values()) for row in rows)


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def token_hits(text: str, tokens: tuple[str, ...]) -> int:
    return sum(1 for token in tokens if token in text)


def specs() -> list[TargetSpec]:
    return [
        TargetSpec(
            family="Same-task Boolean-oracle baselines",
            role="primary benchmark",
            compared_against="Direct ANF, AND-direct ANF, ESOP beam/MILP, BDD/ABC-ESOP, SSHR-H/SSHR-I",
            meaning_test="These baselines solve the same bit-flip Boolean-oracle task or the closest small-function CNOT-oriented variant under the logical resource model.",
            required_claim_tokens=("Primary resource-efficiency baselines",),
            required_evidence_tokens=("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            required_comparability_tokens=("Direct algebraic and ESOP baselines", "SSHR-H and SSHR-I"),
            required_counterpoint_tokens=("SSHR family CNOT optimum",),
            required_related_tokens=("SSHR geometric synthesis",),
            required_control_tokens=(),
            required_artifacts=(
                RESULTS / "raw_traditional_resource.csv",
                RESULTS / "raw_external_traditional_resource_n6.csv",
                RESULTS / "analysis_paired_statistical_evidence.md",
            ),
            supported_statement="Primary evidence for lower T-count and weighted score on matched small functions.",
            invalid_statement="Not evidence of universal CNOT, depth, ancilla, line-count, or hardware-mapped optimality.",
        ),
        TargetSpec(
            family="External logic-network probes",
            role="external stress test",
            compared_against="ABC AIG/XAG/LUT, ROS-style LUT and garbage-budget proxy, mockturtle KLUT-to-XAG, CirKit AIG/MC",
            meaning_test="These probes test whether mature Boolean-network and LUT/XAG/AIG optimization already removes the apparent advantage.",
            required_claim_tokens=("External logic-network probes",),
            required_evidence_tokens=("ROS-style LUT proxy", "mockturtle KLUT-to-XAG probe", "CirKit AIG/MC probe"),
            required_comparability_tokens=("ABC/BDD and exported logic networks", "ROS-style LUT, mockturtle, and CirKit probes"),
            required_counterpoint_tokens=("CirKit AIG/MC depth",),
            required_related_tokens=("LUT/ROS-style oracle synthesis", "XAG and multiplicative complexity", "Logic and reversible toolchains"),
            required_control_tokens=(),
            required_artifacts=(
                RESULTS / "raw_ros_lut_proxy_best.csv",
                RESULTS / "raw_ros_lut_garbage_budget_frontier.csv",
                RESULTS / "raw_mockturtle_xag_probe.csv",
                RESULTS / "raw_cirkit_aig_probe.csv",
                RESULTS / "analysis_ros_reproduction_gap_audit.md",
            ),
            supported_statement="Secondary evidence that the score/T-count advantage survives external logical toolchain probes.",
            invalid_statement="Not a full ROS SAT garbage-management optimizer, reversible-emission, routing, or hardware-mapped comparison.",
        ),
        TargetSpec(
            family="Published STG optimum-library counterpoint",
            role="small-function optimum counterpoint",
            compared_against="Public n=4/5 STG spectral-representative circuits optimized for T-count, T-depth, and qubit count",
            meaning_test="This target asks whether the generic logical search beats a precomputed tiny-function optimum library; the expected use is a boundary, not a headline win.",
            required_claim_tokens=(),
            required_evidence_tokens=("Published STG optimum-library counterpoint",),
            required_comparability_tokens=(),
            required_counterpoint_tokens=(),
            required_related_tokens=("LUT/ROS-style oracle synthesis",),
            required_control_tokens=(),
            required_artifacts=(
                RESULTS / "raw_stg_published_benchmark.csv",
                RESULTS / "analysis_stg_published_benchmark.md",
                TABLES / "stg_published_benchmark.tex",
            ),
            supported_statement="Evidence that public STG optima remain stronger on tiny precomputed representatives while the method still improves local direct baselines on the same slice.",
            invalid_statement="Not evidence of beating published STG T-count, T-depth, or qubit optima.",
        ),
        TargetSpec(
            family="Exact reversible-synthesis probe",
            role="exact reversible counterpoint",
            compared_against="Legacy RevKit CLI TBS/DBS/RMS exact-oracle portfolio",
            meaning_test="The baseline embeds each function as the exact reversible permutation and checks a genuine reversible-synthesis toolchain.",
            required_claim_tokens=("Exact reversible-synthesis probe",),
            required_evidence_tokens=("Legacy RevKit CLI exact oracle",),
            required_comparability_tokens=("Legacy RevKit CLI exact-oracle portfolio",),
            required_counterpoint_tokens=("RevKit exact-oracle auxiliary lines",),
            required_related_tokens=("Logic and reversible toolchains",),
            required_control_tokens=(),
            required_artifacts=(
                RESULTS / "raw_revkit_cli_multiflow_traditional.csv",
                RESULTS / "analysis_revkit_cli_multiflow_traditional.md",
            ),
            supported_statement="Evidence that a real reversible-synthesis portfolio does not erase the T/score advantage.",
            invalid_statement="Not evidence of lower auxiliary-line count, routed depth, or final mapped Clifford+T dominance.",
        ),
        TargetSpec(
            family="Phase/Rz branch",
            role="phase proxy",
            compared_against="RevKit oracle_synth, phase-parity ANF, FPRM, affine FPRM, learned phase shortlist",
            meaning_test="This branch tests whether the search framing transfers to verified logical phase/Rz proxy objectives.",
            required_claim_tokens=("Phase/Rz branch",),
            required_evidence_tokens=("RevKit phase/Rz branch", "Learned phase pruning"),
            required_comparability_tokens=("Phase/Rz baselines and learned shortlist",),
            required_counterpoint_tokens=(),
            required_related_tokens=("Logic and reversible toolchains",),
            required_control_tokens=("phase random control",),
            required_artifacts=(
                RESULTS / "raw_phase_parity_affine.csv",
                RESULTS / "raw_phase_affine_policy_rank_diverse.csv",
                RESULTS / "analysis_rz_synthesis_cost.md",
            ),
            supported_statement="Evidence for a related logical phase/Rz proxy and learned shortlist, not the main bit-flip claim.",
            invalid_statement="Not a final approximate-rotation synthesis or full Clifford+T sequence.",
        ),
        TargetSpec(
            family="AI/search-control ablations",
            role="causal control",
            compared_against="No-MCTS portfolio, beam-only, learned prior off, random prior, random depth, sparse gate",
            meaning_test="These controls separate representation/search-space effects from MCTS, neural ranking, guards, and budget allocation.",
            required_claim_tokens=("Internal search ablations",),
            required_evidence_tokens=(),
            required_comparability_tokens=(),
            required_counterpoint_tokens=("Learned prior is incremental",),
            required_related_tokens=("Learning-guided circuit synthesis",),
            required_control_tokens=("MCTS over deterministic portfolio", "bit-flip random control", "frontier random-depth control"),
            required_artifacts=(
                RESULTS / "analysis_search_control_baseline_audit.md",
                RESULTS / "analysis_learned_control_audit.md",
                RESULTS / "analysis_bitflip_random_prior_control.md",
                RESULTS / "analysis_frontier_random_depth_control.md",
            ),
            supported_statement="Evidence that learned/search controls add bounded quality or planning gains beyond deterministic construction.",
            invalid_statement="Not evidence that deep reinforcement learning alone causes the full resource reduction.",
        ),
        TargetSpec(
            family="Scaling and correctness bridges",
            role="scalability verification",
            compared_against="n=20,24,28,32,40 symbolic term-set runs, n=48,56,64 ultra-scale symbolic stress, and n=21-30 complete truth-table bridge rows",
            meaning_test="These rows test whether emitted logical oracles remain verifiable beyond the small truth-table benchmark slice.",
            required_claim_tokens=("Scaling and correctness bridges",),
            required_evidence_tokens=("High-dimensional frontier search", "Complete truth-table bridges"),
            required_comparability_tokens=("High-dimensional symbolic and bridge checks",),
            required_counterpoint_tokens=("Large-n verification is bounded",),
            required_related_tokens=(),
            required_control_tokens=(),
            required_artifacts=(
                RESULTS / "raw_screen_scale_depth_frontier_terms.csv",
                RESULTS / "raw_truth_bridge_terms.csv",
                RESULTS / "raw_truth_bridge_n26_terms.csv",
                RESULTS / "raw_truth_bridge_n27_terms.csv",
                RESULTS / "raw_truth_bridge_n28_terms.csv",
                RESULTS / "raw_truth_bridge_n29_terms.csv",
                RESULTS / "raw_truth_bridge_n30_terms.csv",
                RESULTS / "analysis_scaling_resource_audit.md",
            ),
            supported_statement="Evidence for logical-layer scaling and semantic verification within the symbolic/bridge envelope.",
            invalid_statement="Not exhaustive high-dimensional truth-table benchmarking or optimality evidence.",
        ),
        TargetSpec(
            family="Trade-off counterpoints",
            role="non-dominance boundary",
            compared_against="SSHR CNOT, CirKit depth, RevKit auxiliary lines, runtime-negative learned controls",
            meaning_test="These counterpoints keep the comparison meaningful by exposing metrics where other methods remain strong.",
            required_claim_tokens=("Trade-off audits",),
            required_evidence_tokens=(),
            required_comparability_tokens=(),
            required_counterpoint_tokens=("SSHR family CNOT optimum", "CirKit AIG/MC depth", "RevKit exact-oracle auxiliary lines"),
            required_related_tokens=(),
            required_control_tokens=("learned prior",),
            required_artifacts=(
                RESULTS / "analysis_counterpoint_claim_boundary.md",
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "analysis_weight_robustness.md",
            ),
            supported_statement="Evidence that the method occupies a strong T/score point with explicit resource tradeoffs.",
            invalid_statement="Not a single universal leaderboard or complete Pareto dominance claim.",
        ),
    ]


def evaluate(spec: TargetSpec, sources: dict[str, str]) -> dict[str, str]:
    claim_hits = token_hits(sources["claim"], spec.required_claim_tokens)
    evidence_hits = token_hits(sources["evidence"], spec.required_evidence_tokens)
    comparability_hits = token_hits(sources["comparability"], spec.required_comparability_tokens)
    counterpoint_hits = token_hits(sources["counterpoint"], spec.required_counterpoint_tokens)
    related_hits = token_hits(sources["related"], spec.required_related_tokens)
    control_hits = token_hits(sources["control"], spec.required_control_tokens)
    artifact_hits = sum(1 for path in spec.required_artifacts if path.exists())

    checks = [
        claim_hits == len(spec.required_claim_tokens),
        evidence_hits == len(spec.required_evidence_tokens),
        comparability_hits == len(spec.required_comparability_tokens),
        counterpoint_hits == len(spec.required_counterpoint_tokens),
        related_hits == len(spec.required_related_tokens),
        control_hits == len(spec.required_control_tokens),
        artifact_hits == len(spec.required_artifacts),
    ]
    status = "pass" if all(checks) else "needs revision"
    evidence = (
        f"claim={claim_hits}/{len(spec.required_claim_tokens)}; "
        f"evidence={evidence_hits}/{len(spec.required_evidence_tokens)}; "
        f"comparability={comparability_hits}/{len(spec.required_comparability_tokens)}; "
        f"counterpoint={counterpoint_hits}/{len(spec.required_counterpoint_tokens)}; "
        f"related={related_hits}/{len(spec.required_related_tokens)}; "
        f"controls={control_hits}/{len(spec.required_control_tokens)}; "
        f"artifacts={artifact_hits}/{len(spec.required_artifacts)}"
    )
    return {
        "family": spec.family,
        "role": spec.role,
        "status": status,
        "compared_against": spec.compared_against,
        "meaning_test": spec.meaning_test,
        "evidence": evidence,
        "supported_statement": spec.supported_statement,
        "invalid_statement": spec.invalid_statement,
        "next_action": (
            "No action needed; keep this comparison in the stated role."
            if status == "pass"
            else "Restore the missing role/evidence/control/literature artifacts before relying on this comparison target."
        ),
    }


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("Resource-NMCTS", r"\method{}"),
        ("ANF", r"\anf{}"),
        ("FPRM", r"\fprm{}"),
        ("MCTS", r"\mcts{}"),
        ("Rz", r"\rz{}"),
        ("T-count", "T-count"),
        ("CNOT", "CNOT"),
        ("n=20,24,28,32,40", r"$n=20$, 24, 28, 32, 40"),
        ("n=48,56,64", r"$n=48$, 56, 64"),
        ("n=21-30", r"$n=21$--$30$"),
        ("n=21-25", r"$n=21$--$25$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "family",
        "role",
        "status",
        "compared_against",
        "meaning_test",
        "evidence",
        "supported_statement",
        "invalid_statement",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Comparison Target Validity Audit",
        "",
        "This audit answers whether each comparison target is meaningful for the manuscript's bounded logical-layer claim.",
        "",
        "It labels each target family as a primary benchmark, external probe, exact reversible counterpoint, phase proxy, causal control, scalability check, or trade-off boundary.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| family | role | status | meaning test | supported statement | invalid statement |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {family} | {role} | {status} | {meaning_test} | {supported_statement} | {invalid_statement} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.26\linewidth}}",
        r"\toprule",
        r"Target family & Role & Why meaningful & Invalid statement \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["family"]),
                latex_cell(row["role"]),
                latex_cell(row["meaning_test"]),
                latex_cell(row["invalid_statement"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    manuscript_text = read_text(AUTHOR_PAPER) + "\n" + read_text(ANON_PAPER)
    protocol_manifest = read_json(COMPARISON_PROTOCOL_MANIFEST)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "roles": sorted({row["role"] for row in rows}),
        "table": "paper_latex/tables/comparison_target_validity_audit.tex",
        "table_anchor_present": "tab:comparison-target-validity" in manuscript_text,
        "comparison_protocol_needs_revision_count": protocol_manifest.get("needs_revision_count", "missing"),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    sources = {
        "claim": read_csv_text(CLAIM_MATRIX),
        "evidence": read_csv_text(EVIDENCE_MATRIX),
        "comparability": read_csv_text(COMPARABILITY_AUDIT),
        "counterpoint": read_csv_text(COUNTERPOINT_AUDIT),
        "related": read_csv_text(RELATED_POSITIONING),
        "control": read_csv_text(SEARCH_CONTROL_AUDIT),
    }
    rows = [evaluate(spec, sources) for spec in specs()]
    write_csv(RESULTS / "summary_comparison_target_validity_audit.csv", rows)
    write_markdown(RESULTS / "analysis_comparison_target_validity_audit.md", rows)
    write_latex(TABLES / "comparison_target_validity_audit.tex", rows)
    write_manifest(RESULTS / "manifest_comparison_target_validity_audit.json", rows)
    print(f"wrote {RESULTS / 'summary_comparison_target_validity_audit.csv'}")
    print(f"wrote {RESULTS / 'analysis_comparison_target_validity_audit.md'}")
    print(f"wrote {RESULTS / 'manifest_comparison_target_validity_audit.json'}")
    print(f"wrote {TABLES / 'comparison_target_validity_audit.tex'}")


if __name__ == "__main__":
    main()
