#!/usr/bin/env python3
"""Build a compact answer to "what are we comparing against?".

The comparison protocol and validity audits explain why each baseline family
is admissible.  This scorecard adds the reviewer-facing quantitative answer:
which target family is used, how much verified evidence supports the row, what
the headline outcome is, and which stronger claim remains excluded.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"

EVIDENCE = RESULTS / "summary_comparison_evidence_matrix.csv"
PAIRED = RESULTS / "summary_paired_statistical_evidence.csv"
SEARCH_CONTROL = RESULTS / "summary_search_control_baseline_audit.csv"
DOMINANCE = RESULTS / "summary_multimetric_pairwise_dominance.csv"
NONDOMINATED = RESULTS / "summary_multimetric_nondominated.csv"
RESOURCE_WEIGHT_SENSITIVITY = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
CATERPILLAR_API = RESULTS / "manifest_caterpillar_xag_api_probe.json"

SUMMARY = RESULTS / "summary_comparison_answer_scorecard.csv"
ANALYSIS = RESULTS / "analysis_comparison_answer_scorecard.md"
MANIFEST = RESULTS / "manifest_comparison_answer_scorecard.json"
TABLE = TABLES / "comparison_answer_scorecard.tex"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row.get(key, ""): row for row in rows}


def paired(label: str) -> str:
    rows = by_key(read_rows(PAIRED), "comparison")
    row = rows.get(label)
    if not row:
        return f"{label}: missing"
    return (
        f"{row['wins']}/{row['losses']}/{row['ties']}, "
        f"{float(row['mean_relative_pct']):+.2f}%"
    )


def pct_value(value: str) -> float:
    return float(value.strip().rstrip("%"))


def control(comparison: str) -> str:
    for row in read_rows(SEARCH_CONTROL):
        if row.get("comparison") == comparison:
            return f"{row['score_wlt']}, {pct_value(row['mean_score_change']):+.2f}%"
    return f"{comparison}: missing"


def search_control_evidence() -> str:
    rows = read_rows(SEARCH_CONTROL)
    if not rows:
        return "Search-control audit: missing"
    passed = sum(row.get("status", "").strip().lower() == "pass" for row in rows)
    suffix = "" if passed == len(rows) else "; needs revision"
    return f"Search-control audit: {passed}/{len(rows)} pass{suffix}"


def evidence_block(name: str) -> dict[str, str]:
    rows = by_key(read_rows(EVIDENCE), "evidence_block")
    return rows.get(name, {})


def dominance_row(name: str) -> dict[str, str]:
    rows = by_key(read_rows(DOMINANCE), "baseline")
    return rows.get(name, {})


def nondominated(method: str) -> str:
    rows = by_key(read_rows(NONDOMINATED), "method")
    row = rows.get(method)
    if not row:
        return f"{method}: missing"
    return f"{row['nondominated']}/{row['available']} non-dominated"


def resource_weight_evidence() -> str:
    if not RESOURCE_WEIGHT_SENSITIVITY.exists():
        return "resource-weight sensitivity: missing"
    manifest = json.loads(RESOURCE_WEIGHT_SENSITIVITY.read_text(encoding="utf-8"))
    return (
        "resource-weight sensitivity "
        f"{manifest.get('raw_rows', 'missing')} pair/profile rows; "
        f"{len(manifest.get('comparisons', []))} comparisons; "
        f"{len(manifest.get('profiles', []))} profiles"
    )


def caterpillar_api_evidence() -> str:
    if not CATERPILLAR_API.exists():
        return "Caterpillar XAG API probe: missing"
    manifest = json.loads(CATERPILLAR_API.read_text(encoding="utf-8"))
    return (
        "Caterpillar ANF-XAG API probe: "
        f"{manifest.get('correct_rows', 'missing')}/{manifest.get('raw_rows', 'missing')} strategy rows; "
        f"{manifest.get('best_raw_rows', 'missing')} best rows; "
        f"Caterpillar score vs Pareto {manifest.get('score_wlt_vs_pareto', 'missing')}, "
        f"{float(manifest.get('score_mean_relative_vs_pareto_pct', 0.0)):+.2f}%; "
        f"Pareto CNOT vs Caterpillar {manifest.get('pareto_cnot_wlt_vs_caterpillar', 'missing')}"
    )


def caterpillar_api_headline() -> str:
    if not CATERPILLAR_API.exists():
        return "Caterpillar best API: missing"
    manifest = json.loads(CATERPILLAR_API.read_text(encoding="utf-8"))
    return (
        "Pareto vs Caterpillar API score "
        f"{manifest.get('pareto_score_wlt_vs_caterpillar', 'missing')}, "
        f"{float(manifest.get('pareto_score_mean_relative_vs_caterpillar_pct', 0.0)):+.2f}%; "
        f"CNOT {manifest.get('pareto_cnot_wlt_vs_caterpillar', 'missing')}"
    )


def dominance_text(baseline: str) -> str:
    row = dominance_row(baseline)
    if not row:
        return f"{baseline}: dominance missing"
    return (
        f"{baseline} four-resource dominance "
        f"{row['target_dominates']}/{row['baseline_dominates']}/"
        f"{row['incomparable']}/{row['equal']}"
    )


def verified(*names: str) -> str:
    parts: list[str] = []
    for name in names:
        row = evidence_block(name)
        if row:
            parts.append(f"{name}: {row['verified_rows']}")
        else:
            parts.append(f"{name}: missing")
    return "; ".join(parts)


def has_missing(text: str) -> bool:
    lowered = text.lower()
    return "missing" in lowered or "needs revision" in lowered


def build_rows() -> list[dict[str, str]]:
    rows = [
        {
            "reviewer_question": "Are gains only over weak algebraic baselines?",
            "comparison_target": "Direct ANF, ESOP beam/MILP, ABC/BDD exports",
            "role": "primary same-task benchmark",
            "verified_evidence": verified("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            "headline_answer": (
                "Pareto vs direct ANF "
                + paired("n<=6 Pareto vs direct ANF")
                + "; vs ESOP-MILP "
                + paired("n<=6 Pareto vs ESOP-MILP")
                + "; vs ABC-XAG "
                + paired("n<=6 Pareto vs ABC-XAG")
            ),
            "usable_claim": "Lower T-count and weighted score on matched logical bit-flip oracle benchmarks.",
            "excluded_claim": "No universal CNOT, depth, ancilla, line-count, or hardware-mapped optimality claim.",
            "sources": "summary_comparison_evidence_matrix.csv; summary_paired_statistical_evidence.csv",
        },
        {
            "reviewer_question": "Is SSHR the whole comparison target?",
            "comparison_target": "SSHR-H and SSHR-I CNOT",
            "role": "CNOT-oriented small-function counterpoint",
            "verified_evidence": verified("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            "headline_answer": (
                "Pareto vs SSHR-H "
                + paired("n<=6 Pareto vs SSHR-H")
                + "; vs SSHR-I CNOT "
                + paired("n<=6 Pareto vs SSHR-I CNOT")
                + "; "
                + dominance_text("SSHR-H")
            ),
            "usable_claim": "SSHR is an important CNOT-oriented baseline, but the method is not defined by SSHR's parallelotope search space.",
            "excluded_claim": "Do not claim CNOT dominance over SSHR; SSHR remains a real CNOT counterpoint.",
            "sources": "summary_paired_statistical_evidence.csv; summary_multimetric_pairwise_dominance.csv",
        },
        {
            "reviewer_question": "Does the advantage survive external logic synthesis?",
            "comparison_target": "ROS-style LUT/garbage-budget, mockturtle XAG, Caterpillar API, CirKit AIG/MC",
            "role": "external logical-toolchain stress test",
            "verified_evidence": verified(
                "ROS-style LUT proxy",
                "mockturtle KLUT-to-XAG probe",
                "Caterpillar XAG API probe",
                "CirKit AIG/MC probe",
            ),
            "headline_answer": (
                "ROS best-K "
                + paired("ROS-style LUT best-K")
                + "; mockturtle n<=6 "
                + paired("mockturtle XAG n<=6")
                + "; "
                + caterpillar_api_headline()
                + "; CirKit n<=6 "
                + paired("CirKit AIG/MC n<=6")
            ),
            "usable_claim": "The score/T-count advantage is not an artifact of comparing only against local hand-written baselines.",
            "excluded_claim": "Not a full ROS SAT garbage-management optimizer, reversible-emission, routing, or hardware-mapped comparison.",
            "sources": "summary_comparison_evidence_matrix.csv; summary_paired_statistical_evidence.csv; manifest_caterpillar_xag_api_probe.json",
        },
        {
            "reviewer_question": "Does it beat published tiny-function optima?",
            "comparison_target": "Published STG n=4/5 optimum table",
            "role": "small-function optimum-library counterpoint",
            "verified_evidence": verified("Published STG optimum-library counterpoint"),
            "headline_answer": evidence_block("Published STG optimum-library counterpoint").get("main_result", "missing"),
            "usable_claim": "The method improves its own direct logical baselines on the same STG truth-table slice, while public STG optima remain stronger on tiny precomputed representatives.",
            "excluded_claim": "No claim of beating published STG T-count, T-depth, or qubit optima on n=4/5 spectral representatives.",
            "sources": "summary_comparison_evidence_matrix.csv; summary_stg_published_benchmark.csv",
        },
        {
            "reviewer_question": "What does RevKit test?",
            "comparison_target": "Legacy RevKit exact oracle and RevKit phase/Rz branch",
            "role": "reversible and phase proxy counterpoint",
            "verified_evidence": verified("Legacy RevKit CLI exact oracle", "RevKit phase/Rz branch", "Learned phase pruning"),
            "headline_answer": (
                "RevKit CLI exact oracle "
                + paired("RevKit CLI exact oracle")
                + "; "
                + evidence_block("RevKit phase/Rz branch").get("main_result", "missing")
            ),
            "usable_claim": "A real reversible-synthesis portfolio and a verified phase/Rz proxy do not erase the T/score story.",
            "excluded_claim": "Not lower auxiliary-line count, routed depth, or final approximate-rotation Clifford+T synthesis.",
            "sources": "summary_comparison_evidence_matrix.csv; summary_paired_statistical_evidence.csv",
        },
        {
            "reviewer_question": "What part is actually AI/MCTS?",
            "comparison_target": "No-MCTS portfolio, Pareto archive, learned/random controls, fitted-Q Pareto budget control",
            "role": "causal search-control ablation",
            "verified_evidence": search_control_evidence(),
            "headline_answer": (
                "Resource over no-MCTS "
                + control("Resource-NMCTS over no-MCTS portfolio")
                + "; Pareto over no-MCTS "
                + control("Pareto Resource-NMCTS over no-MCTS portfolio")
                + "; learned vs random prior "
                + control("Learned bit-flip prior vs same-budget random-prior mean")
                + "; fitted-Q budget "
                + control("Fitted-Q budget policy vs Resource-NMCTS and always-Pareto")
            ),
            "usable_claim": "MCTS and Pareto selection add bounded quality gains; fitted-Q reinforcement learning allocates optional Pareto effort with a measured quality-time tradeoff.",
            "excluded_claim": "Do not state that deep reinforcement learning alone explains the full resource reduction or that the budget policy dominates always-on Pareto score.",
            "sources": "summary_search_control_baseline_audit.csv; summary_mcts_budget_policy.csv",
        },
        {
            "reviewer_question": "Is the evidence only small-scale?",
            "comparison_target": "n=20--64 symbolic runs and n=21--30 complete truth-table bridges",
            "role": "scaling and correctness verification",
            "verified_evidence": verified("High-dimensional frontier search", "Complete truth-table bridges"),
            "headline_answer": (
                evidence_block("High-dimensional frontier search").get("main_result", "missing")
                + "; "
                + evidence_block("Complete truth-table bridges").get("main_result", "missing")
            ),
            "usable_claim": "The logical emitter and verification harness scale beyond the n<=6 truth-table benchmark slice.",
            "excluded_claim": "Not exhaustive high-dimensional truth-table benchmarking or global optimality proof.",
            "sources": "summary_comparison_evidence_matrix.csv",
        },
        {
            "reviewer_question": "Does weighted score hide bad tradeoffs?",
            "comparison_target": "Four-resource dominance, non-dominated pool, and resource-weight sensitivity",
            "role": "non-dominance boundary",
            "verified_evidence": "12-method n<=6 dominance pool; 177 matched functions; " + resource_weight_evidence(),
            "headline_answer": (
                "Pareto-Resource-NMCTS is "
                + nondominated("Pareto-Resource-NMCTS")
                + "; "
                + dominance_text("RevKit CLI exact oracle")
                + "; "
                + dominance_text("CirKit AIG/MC")
                + "; Caterpillar CNOT-only 4/173/0 while paper score is 177/0/0"
            ),
            "usable_claim": "The method occupies a strong T/score point while preserving visible CNOT/depth/ancilla and coefficient-sensitivity tradeoffs.",
            "excluded_claim": "Do not turn weighted-score wins into a complete Pareto or hardware-dominance claim.",
            "sources": "summary_multimetric_pairwise_dominance.csv; summary_multimetric_nondominated.csv; manifest_resource_weight_sensitivity_audit.json",
        },
    ]
    for row in rows:
        fields = [
            row["verified_evidence"],
            row["headline_answer"],
            row["usable_claim"],
            row["excluded_claim"],
        ]
        row["status"] = "needs revision" if any(has_missing(field) for field in fields) else "pass"
        row["next_action"] = (
            "Rerun the upstream comparison, search-control, and dominance audits; then rerun this scorecard."
            if row["status"] != "pass"
            else "Keep this row aligned with the upstream comparison evidence and claim boundaries."
        )
    return rows


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("<=", r"$\leq$")
        .replace("--", r"--")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "Pareto-Resource-NMCTS": r"Pareto-\method{}",
        "Resource-NMCTS": r"\method{}",
        "AI/MCTS": r"AI/\mcts{}",
        "No-MCTS": r"No-\mcts{}",
        "ANF": r"\anf{}",
        "FPRM": r"\fprm{}",
        "Rz": r"\rz{}",
        "n=20--64": r"$n=20$--$64$",
        "n=21--30": r"$n=21$--$30$",
        "n=3-6": r"$n=3$--$6$",
        "n<=6": r"$n\leq6$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    escaped = re.sub(r"(?<![A-Za-z])MCTS(?![A-Za-z])", r"\\mcts{}", escaped)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "reviewer_question",
        "comparison_target",
        "role",
        "verified_evidence",
        "headline_answer",
        "usable_claim",
        "excluded_claim",
        "status",
        "sources",
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
        "# Comparison Answer Scorecard",
        "",
        "This audit gives a compact quantitative answer to what the method is compared against and what those comparisons mean.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| reviewer question | comparison target | role | verified evidence | headline answer | excluded claim | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {reviewer_question} | {comparison_target} | {role} | {verified_evidence} | {headline_answer} | {excluded_claim} | {status} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.18\linewidth}}",
        r"\toprule",
        r"Question & Target & Evidence & Quantitative answer & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["reviewer_question"]),
                latex_cell(row["comparison_target"]),
                latex_cell(row["verified_evidence"]),
                latex_cell(row["headline_answer"]),
                latex_cell(row["excluded_claim"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    manuscript_text = AUTHOR_PAPER.read_text(encoding="utf-8") + "\n" + ANON_PAPER.read_text(encoding="utf-8")
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "questions": [row["reviewer_question"] for row in rows],
        "roles": sorted({row["role"] for row in rows}),
        "table": "paper_latex/tables/comparison_answer_scorecard.tex",
        "table_anchor_present": "tab:comparison-answer-scorecard" in manuscript_text,
        "source_files": sorted({source for row in rows for source in row["sources"].split("; ")}),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {SUMMARY.relative_to(THIS_DIR)}")
    print(f"wrote {ANALYSIS.relative_to(THIS_DIR)}")
    print(f"wrote {MANIFEST.relative_to(THIS_DIR)}")
    print(f"wrote {TABLE.relative_to(THIS_DIR)}")


if __name__ == "__main__":
    main()
