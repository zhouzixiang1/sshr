#!/usr/bin/env python3
"""Build a threats-to-validity and mitigation audit for the manuscript.

This is a reviewer-facing synthesis audit.  It does not add new experimental
claims; it checks that the main validity threats are named, tied to existing
evidence files, and bounded by residual limitations.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
PACKAGE_README = THIS_DIR / "submission_package" / "README.md"

SUMMARY = RESULTS / "summary_threats_to_validity_audit.csv"
ANALYSIS = RESULTS / "analysis_threats_to_validity_audit.md"
MANIFEST = RESULTS / "manifest_threats_to_validity_audit.json"
TABLE = TABLES / "threats_to_validity_audit.tex"


@dataclass(frozen=True)
class ThreatSpec:
    threat: str
    risk: str
    evidence_files: tuple[Path, ...]
    required_tokens: tuple[str, ...]
    mitigation: str
    residual_boundary: str
    next_action: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def token_present(text: str, token: str) -> bool:
    return token.lower() in text.lower()


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def specs() -> list[ThreatSpec]:
    return [
        ThreatSpec(
            threat="Logical-layer abstraction",
            risk="Readers may infer hardware routing, native-gate, noise, or magic-state-factory resource claims.",
            evidence_files=(
                RESULTS / "analysis_claim_scope_lint.md",
                PAPER,
                PACKAGE_README,
            ),
            required_tokens=("logical-layer", "hardware mapping", "no hardware"),
            mitigation="The abstract, discussion, claim-scope lint, and payload README state that the paper reports logical-layer resources only.",
            residual_boundary="No placement, routing, native-gate scheduling, noise, or factory-level accounting is evaluated.",
            next_action="Keep every new result inside the logical-layer boundary unless a separate hardware-mapping study is added.",
        ),
        ThreatSpec(
            threat="Weighted-score aggregation",
            risk="A single score could hide unfavorable CNOT, depth, ancilla, or lifetime behavior.",
            evidence_files=(
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "analysis_schedule_proxy_audit.md",
                RESULTS / "analysis_weight_robustness.md",
                RESULTS / "analysis_resource_weight_sensitivity_audit.md",
                RESULTS / "analysis_counterpoint_claim_boundary.md",
            ),
            required_tokens=("Pareto", "schedule", "Weight profiles", "CNOT-only", "counterpoint"),
            mitigation="Raw dominance, schedule-proxy, weight-robustness, resource-weight sensitivity, and counterpoint audits expose resource dimensions separately from the weighted score.",
            residual_boundary="The method is presented as a strong T-count and weighted-score point, not complete raw-resource dominance.",
            next_action="Rerun the tradeoff and weight audits after changing the score model or adding a resource metric.",
        ),
        ThreatSpec(
            threat="Baseline comparability",
            risk="External logic-network, reversible, phase, and ROS-style rows could be mistaken for one fully uniform compiler benchmark.",
            evidence_files=(
                RESULTS / "analysis_baseline_comparability_audit.md",
                RESULTS / "analysis_comparison_answer_scorecard.md",
                RESULTS / "analysis_ros_reproduction_gap_audit.md",
                RESULTS / "analysis_comparison_target_validity_audit.md",
            ),
            required_tokens=("proxy", "full ROS", "comparison target", "hardware-mapped"),
            mitigation="The comparison matrices assign each baseline family a role, verified evidence, usable claim, and excluded claim.",
            residual_boundary="ROS-style and logic-network probes remain logical proxies; RevKit rows are exact-oracle or phase proxies, not mapped circuits.",
            next_action="Route any new baseline through the comparability, target-validity, and comparison-answer audits before citing it as evidence.",
        ),
        ThreatSpec(
            threat="AI/MCTS attribution",
            risk="The manuscript could overstate deep learning or MCTS as the sole reason for the gains.",
            evidence_files=(
                RESULTS / "analysis_search_control_baseline_audit.md",
                RESULTS / "analysis_bitflip_random_prior_control.md",
                RESULTS / "analysis_frontier_random_depth_control.md",
                RESULTS / "analysis_learned_control_audit.md",
            ),
            required_tokens=("random", "learned", "MCTS", "incremental"),
            mitigation="Search-control, random-prior, random-depth, and learned-control audits separate algebraic search space, MCTS, Pareto archives, and learned ranking.",
            residual_boundary="Learned controls are bounded and sometimes runtime-negative; they are not promoted as the whole resource-reduction mechanism.",
            next_action="Keep AI claims tied to same-budget controls and do not promote diagnostic rows as main contributions.",
        ),
        ThreatSpec(
            threat="High-dimensional verification envelope",
            risk="Large-n symbolic rows may be read as exhaustive truth-table benchmarking or optimality evidence.",
            evidence_files=(
                RESULTS / "analysis_scaling_resource_audit.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_stress.md",
                RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md",
                RESULTS / "analysis_truth_bridge_terms.md",
            ),
            required_tokens=("symbolic", "truth", "n=48", "bridge"),
            mitigation="Scaling, ultra-scale, resource-profile, and truth-bridge audits separate symbolic verification from complete truth-table checks.",
            residual_boundary="Complete truth-table verification is limited to generated n=21--30 bridge slices; n=31--64 rows are not exhaustive truth-table enumerations.",
            next_action="Label any new large-n result as symbolic, bridge, or complete-truth-table evidence according to its verifier.",
        ),
        ThreatSpec(
            threat="Statistical and benchmark representativeness",
            risk="Mean improvements could be driven by outliers or by an unrepresentative benchmark subset.",
            evidence_files=(
                RESULTS / "analysis_paired_statistical_evidence.md",
                RESULTS / "analysis_paired_effect_uncertainty.md",
                RESULTS / "analysis_headline_numeric_consistency.md",
            ),
            required_tokens=("wins", "95% CI", "headline", "matched"),
            mitigation="Paired statistics, bootstrap intervals, and headline consistency checks recompute matched comparisons from CSV evidence.",
            residual_boundary="The evidence covers the generated and benchmarked slices in the artifact package, not all Boolean functions.",
            next_action="Rerun paired and headline audits after adding benchmark families or changing headline numbers.",
        ),
        ThreatSpec(
            threat="Reproducibility and package drift",
            risk="A complete-looking manuscript could drift from the scripts, raw rows, tables, and archive manifest.",
            evidence_files=(
                RESULTS / "analysis_reproducibility_audit.md",
                RESULTS / "analysis_artifact_rerun_registry.md",
                RESULTS / "analysis_submission_archive_manifest.md",
            ),
            required_tokens=("artifact", "raw", "manifest", "archive"),
            mitigation="Reproducibility, artifact-registry, and archive-manifest audits connect scripts, raw rows, summaries, tables, and manuscript payload groups.",
            residual_boundary="The lightweight rebuild regenerates paper-facing artifacts but does not rerun heavy raw sweeps or neural training jobs.",
            next_action="Rerun the rebuild and verifier after any paper, table, figure, payload, or support-document edit.",
        ),
    ]


def evaluate(spec: ThreatSpec, paper_text: str) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.evidence_files if not path.exists()]
    evidence_text = "\n".join(read_text(path) for path in spec.evidence_files)
    combined = paper_text + "\n" + evidence_text
    missing_tokens = [token for token in spec.required_tokens if not token_present(combined, token)]
    status = "pass" if not missing_files and not missing_tokens else "needs revision"
    return {
        "threat": spec.threat,
        "status": status,
        "risk": spec.risk,
        "evidence_files": "; ".join(rel(path) for path in spec.evidence_files),
        "missing_files": "; ".join(missing_files),
        "missing_tokens": "; ".join(missing_tokens),
        "mitigation": spec.mitigation,
        "residual_boundary": spec.residual_boundary,
        "next_action": spec.next_action,
    }


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def latex_cell(text: str) -> str:
    text = latex_escape(text)
    replacements = {
        "T-count": r"T-count",
        "CNOT": r"CNOT",
        "MCTS": r"\mcts{}",
        "n=21--30": r"$n=21$--$30$",
        "n=31--64": r"$n=31$--$64$",
        "n=26--64": r"$n=26$--$64$",
        "n=48": r"$n=48$",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "threat",
        "status",
        "risk",
        "evidence_files",
        "missing_files",
        "missing_tokens",
        "mitigation",
        "residual_boundary",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    lines = [
        "# Threats-to-Validity Audit",
        "",
        "This audit checks that the manuscript names the main validity threats, ties them to generated evidence, and preserves the residual boundaries.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| threat | status | risk | mitigation | residual boundary |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {threat} | {status} | {risk} | {mitigation} | {residual_boundary} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.25\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}}",
        r"\toprule",
        r"Threat & Risk & Mitigation evidence & Residual boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["threat"]),
                latex_cell(row["risk"]),
                latex_cell(row["mitigation"]),
                latex_cell(row["residual_boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]], paper_text: str) -> None:
    counts = status_counts(rows)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "threats": [row["threat"] for row in rows],
        "table": "paper_latex/tables/threats_to_validity_audit.tex",
        "table_anchor_present": "tab:threats-validity" in paper_text,
        "evidence_files": sorted(
            {
                path
                for row in rows
                for path in row["evidence_files"].split("; ")
                if path
            }
        ),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    paper_text = read_text(PAPER)
    rows = [evaluate(spec, paper_text) for spec in specs()]
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows, paper_text)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(ANALYSIS)}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(TABLE)}")


if __name__ == "__main__":
    main()
