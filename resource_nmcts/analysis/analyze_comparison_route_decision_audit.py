#!/usr/bin/env python3
"""Audit the decision rule behind the comparison set.

The paper already contains quantitative comparison tables.  This derived audit
answers a narrower reviewer question: when a claim is made, which comparator
family is the right one to read, and which comparator family should not be
over-read as a universal leaderboard entry.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

ANSWER_SCORECARD = RESULTS / "summary_comparison_answer_scorecard.csv"
TARGET_VALIDITY = RESULTS / "summary_comparison_target_validity_audit.csv"
BENCHMARK_SUITE = RESULTS / "summary_benchmark_suite_audit.csv"
COMPARABILITY = RESULTS / "summary_baseline_comparability_audit.csv"
COUNTERPOINT = RESULTS / "summary_counterpoint_claim_boundary.csv"
RESOURCE_SENSITIVITY = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
SEARCH_CONTROL = RESULTS / "summary_search_control_baseline_audit.csv"

SUMMARY = RESULTS / "summary_comparison_route_decision_audit.csv"
ANALYSIS = RESULTS / "analysis_comparison_route_decision_audit.md"
MANIFEST = RESULTS / "manifest_comparison_route_decision_audit.json"
TABLE = TABLES / "comparison_route_decision_audit.tex"


@dataclass(frozen=True)
class RouteSpec:
    route: str
    reviewer_question: str
    right_comparator: str
    same_task_level: str
    resource_readout: str
    required_answer_tokens: tuple[str, ...]
    required_target_tokens: tuple[str, ...]
    required_suite_tokens: tuple[str, ...]
    required_support_files: tuple[Path, ...]
    use_when_claiming: str
    do_not_claim: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def csv_blob(path: Path) -> str:
    rows = read_rows(path)
    return "\n".join(" | ".join(row.values()) for row in rows)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def route_specs() -> list[RouteSpec]:
    return [
        RouteSpec(
            route="Main same-task resource claim",
            reviewer_question="Are the gains only over weak algebraic baselines?",
            right_comparator="Direct ANF, ESOP beam/MILP, ABC/BDD exports, and matched SSHR rows",
            same_task_level="same bit-flip oracle task on enumerable small functions",
            resource_readout="T-count, CNOT, depth, ancilla, weighted score, and paired W/L/T",
            required_answer_tokens=("Are gains only over weak algebraic baselines?", "Direct ANF"),
            required_target_tokens=("Same-task Boolean-oracle baselines", "primary benchmark"),
            required_suite_tokens=("Matched small Boolean oracles",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, BENCHMARK_SUITE),
            use_when_claiming="The method improves logical bit-flip oracle resources on matched small-function tasks.",
            do_not_claim="This row does not prove hardware-mapped, universal Pareto, or large-n optimality.",
        ),
        RouteSpec(
            route="CNOT-oriented geometric counterpoint",
            reviewer_question="Is SSHR the whole comparison target?",
            right_comparator="SSHR-H and timed SSHR-I rows",
            same_task_level="closest small-function CNOT-oriented method, not the proposed search space",
            resource_readout="CNOT boundary plus score/T tradeoff and four-resource dominance",
            required_answer_tokens=("Is SSHR the whole comparison target?", "SSHR-H"),
            required_target_tokens=("Same-task Boolean-oracle baselines", "SSHR-H/SSHR-I"),
            required_suite_tokens=("Matched small Boolean oracles",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, COUNTERPOINT),
            use_when_claiming="The method is competitive with a CNOT-oriented SSHR baseline while optimizing a different resource objective.",
            do_not_claim="Do not state CNOT dominance over SSHR or define the contribution as an SSHR variant.",
        ),
        RouteSpec(
            route="External logical-toolchain stress test",
            reviewer_question="Does the advantage survive mature logic synthesis?",
            right_comparator="ROS-style LUT, mockturtle, Caterpillar API, CirKit, and ABC-family probes",
            same_task_level="logical network/proxy comparison with bounded task mismatch",
            resource_readout="score/T trends, CNOT pressure, depth counterpoints, and verification route",
            required_answer_tokens=("Does the advantage survive external logic synthesis?", "Caterpillar"),
            required_target_tokens=("External logic-network probes", "external stress test"),
            required_suite_tokens=("External logic-network probes",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, COMPARABILITY, BENCHMARK_SUITE),
            use_when_claiming="The resource advantage is not an artifact of only comparing with project-internal implementations.",
            do_not_claim="Do not present these probes as full ROS, routed reversible, or hardware-mapped reproductions.",
        ),
        RouteSpec(
            route="Exact reversible and phase counterpoint",
            reviewer_question="What does RevKit test?",
            right_comparator="Legacy RevKit exact-oracle portfolio and RevKit/affine phase-Rz rows",
            same_task_level="exact reversible embedding plus related phase/Rz proxy",
            resource_readout="T/score comparison, auxiliary-line counterpoint, and phase verification",
            required_answer_tokens=("What does RevKit test?", "RevKit"),
            required_target_tokens=("Exact reversible-synthesis probe", "Phase/Rz branch"),
            required_suite_tokens=("RevKit reversible and phase probes",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, BENCHMARK_SUITE),
            use_when_claiming="A real reversible-synthesis portfolio and related phase branch were checked as bounded counterpoints.",
            do_not_claim="Do not claim fewer auxiliary lines, routed depth, or final approximate Clifford+T rotation synthesis.",
        ),
        RouteSpec(
            route="Tiny optimum-library boundary",
            reviewer_question="Does it beat published tiny-function optima?",
            right_comparator="Published STG n=4/5 optimum-library circuits",
            same_task_level="tiny public representative boundary, not the main benchmark",
            resource_readout="T-count, T-depth, qubit count, and local direct-baseline delta",
            required_answer_tokens=("Does it beat published tiny-function optima?", "STG"),
            required_target_tokens=("Published STG optimum-library counterpoint",),
            required_suite_tokens=("Published tiny-function optimum counterpoint",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, BENCHMARK_SUITE),
            use_when_claiming="The paper reports a negative control where precomputed tiny-function optima remain stronger.",
            do_not_claim="Do not claim to beat published STG optima on T-count, T-depth, or qubit count.",
        ),
        RouteSpec(
            route="AI/MCTS attribution",
            reviewer_question="What part is actually AI or MCTS?",
            right_comparator="No-MCTS, beam, learned-prior, random-prior, random-depth, stochastic, and always-on Pareto controls",
            same_task_level="same search scaffold or same-budget control, not a competing synthesizer family",
            resource_readout="bounded score deltas, W/L/T, seed stability, paired confidence intervals, and runtime/control tradeoffs",
            required_answer_tokens=("What part is actually AI/MCTS?", "No-MCTS"),
            required_target_tokens=("AI/search-control ablations", "causal control"),
            required_suite_tokens=("Learned-control and stochastic controls",),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, SEARCH_CONTROL, BENCHMARK_SUITE),
            use_when_claiming="Neural ranking and MCTS add bounded gains, while fitted-Q reinforcement learning allocates optional Pareto effort.",
            do_not_claim="Do not say deep reinforcement learning alone explains the full resource reduction or that the policy dominates always-on Pareto score.",
        ),
        RouteSpec(
            route="Large-scale semantic verification",
            reviewer_question="Is the evidence only small-scale?",
            right_comparator="n=20--64 symbolic term-set stress and n=21--30 complete truth-table bridges",
            same_task_level="large logical emitter verification, not exhaustive optimality benchmarking",
            resource_readout="plan ANF verification, emitted-circuit checks, bridge truth tables, and runtime envelope",
            required_answer_tokens=("Is the evidence only small-scale?", "n=20--64"),
            required_target_tokens=("Scaling and correctness bridges",),
            required_suite_tokens=("Large symbolic term-set scaling", "Complete truth-table bridge slices"),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, BENCHMARK_SUITE),
            use_when_claiming="The emitted logical oracle and verification harness scale beyond the n<=6 truth-table benchmark slice.",
            do_not_claim="Do not claim exhaustive high-dimensional truth-table benchmarking or global optimality.",
        ),
        RouteSpec(
            route="Weighted-score and tradeoff boundary",
            reviewer_question="Does weighted score hide bad tradeoffs?",
            right_comparator="Four-resource dominance, non-dominated rows, SSHR/CirKit/RevKit counterpoints, and weight profiles",
            same_task_level="resource-tradeoff audit over matched and external rows",
            resource_readout="dominance counts, non-dominated count, alternative weight profiles, and unfavorable metrics",
            required_answer_tokens=("Does weighted score hide bad tradeoffs?", "resource-weight sensitivity"),
            required_target_tokens=("Trade-off counterpoints", "non-dominance boundary"),
            required_suite_tokens=("Matched small Boolean oracles", "External logic-network probes"),
            required_support_files=(ANSWER_SCORECARD, TARGET_VALIDITY, RESOURCE_SENSITIVITY),
            use_when_claiming="The method occupies a strong T/score point with visible CNOT, depth, and ancilla tradeoffs.",
            do_not_claim="Do not turn weighted-score wins into a universal leaderboard or complete Pareto-dominance claim.",
        ),
    ]


def token_hits(text: str, tokens: tuple[str, ...]) -> int:
    return sum(1 for token in tokens if token in text)


def build_rows() -> list[dict[str, str]]:
    answer_text = csv_blob(ANSWER_SCORECARD)
    target_text = csv_blob(TARGET_VALIDITY)
    suite_text = csv_blob(BENCHMARK_SUITE)
    rows: list[dict[str, str]] = []
    for spec in route_specs():
        answer_hits = token_hits(answer_text, spec.required_answer_tokens)
        target_hits = token_hits(target_text, spec.required_target_tokens)
        suite_hits = token_hits(suite_text, spec.required_suite_tokens)
        existing_files = [path for path in spec.required_support_files if path.exists()]
        status = "pass"
        if answer_hits != len(spec.required_answer_tokens):
            status = "needs revision"
        if target_hits != len(spec.required_target_tokens):
            status = "needs revision"
        if suite_hits != len(spec.required_suite_tokens):
            status = "needs revision"
        if len(existing_files) != len(spec.required_support_files):
            status = "needs revision"
        rows.append(
            {
                "route": spec.route,
                "reviewer_question": spec.reviewer_question,
                "right_comparator": spec.right_comparator,
                "same_task_level": spec.same_task_level,
                "resource_readout": spec.resource_readout,
                "evidence_gate": (
                    f"answer={answer_hits}/{len(spec.required_answer_tokens)}; "
                    f"target={target_hits}/{len(spec.required_target_tokens)}; "
                    f"suite={suite_hits}/{len(spec.required_suite_tokens)}; "
                    f"files={len(existing_files)}/{len(spec.required_support_files)}"
                ),
                "use_when_claiming": spec.use_when_claiming,
                "do_not_claim": spec.do_not_claim,
                "status": status,
                "next_action": (
                    "Restore the corresponding answer-scorecard, target-validity, suite, or support file evidence."
                    if status != "pass"
                    else "Keep this route aligned with comparison wording and support-package claims."
                ),
            }
        )
    return rows


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("<=", r"$\leq$")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "ANF": r"\anf{}",
        "Rz": r"\rz{}",
        "MCTS": r"\mcts{}",
        "n=4/5": r"$n=4/5$",
        "n=20--64": r"$n=20$--$64$",
        "n=21--30": r"$n=21$--$30$",
        "n<=6": r"$n\leq 6$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    escaped = escaped.replace(r"n$\leq$6", r"$n\leq 6$")
    escaped = re.sub(r"n=(\d+)--(\d+)", r"$n=\1$--$\2$", escaped)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "route",
        "reviewer_question",
        "right_comparator",
        "same_task_level",
        "resource_readout",
        "evidence_gate",
        "use_when_claiming",
        "do_not_claim",
        "status",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Comparison Route Decision Audit",
        "",
        "This audit states which comparator family should be used for each reviewer-facing claim and which stronger interpretation remains excluded.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Decision routes",
            "",
            "| route | reviewer question | right comparator | evidence gate | usable claim | excluded claim | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {route} | {reviewer_question} | {right_comparator} | {evidence_gate} | {use_when_claiming} | {do_not_claim} | {status} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    compact = {
        "Main same-task resource claim": (
            "Same-task resources",
            "ANF, ESOP, ABC, BDD, SSHR",
            "main bit-flip resource gains",
            "hardware or global optimality",
        ),
        "CNOT-oriented geometric counterpoint": (
            "SSHR CNOT boundary",
            "SSHR-H or SSHR-I",
            "CNOT counterpoint",
            "CNOT dominance or SSHR variant",
        ),
        "External logical-toolchain stress test": (
            "External toolchains",
            "ROS, mockturtle, Caterpillar, CirKit",
            "external logical stress",
            "full ROS, routing, or hardware mapping",
        ),
        "Exact reversible and phase counterpoint": (
            "RevKit phase",
            "RevKit CLI and phase Rz",
            "reversible and phase counterpoint",
            "line or Clifford+T dominance",
        ),
        "Tiny optimum-library boundary": (
            "Tiny optima",
            "STG n=4/5 optima",
            "tiny optimum boundary",
            "beating published STG optima",
        ),
        "AI/MCTS attribution": (
            "AI and MCTS controls",
            "no-MCTS, random, learned controls",
            "search attribution",
            "deep RL only explanation",
        ),
        "Large-scale semantic verification": (
            "Large-scale check",
            "n=20--64 symbolic; n=21--30 bridge",
            "large-n verification",
            "exhaustive high-n optima",
        ),
        "Weighted-score and tradeoff boundary": (
            "Tradeoff boundary",
            "dominance and weight profiles",
            "score and resource tradeoff",
            "universal Pareto dominance",
        ),
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Route & Comparator & Use for & Do not claim \\",
        r"\midrule",
    ]
    for row in rows:
        route, comparator, use_for, excluded = compact[row["route"]]
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(route),
                latex_cell(comparator),
                latex_cell(use_for),
                latex_cell(excluded),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    author_text = read_text(AUTHOR_TEX)
    anon_text = read_text(ANON_TEX)
    acm_text = read_text(ACM_TEX)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "routes": [row["route"] for row in rows],
        "questions": [row["reviewer_question"] for row in rows],
        "table": "paper_latex/tables/comparison_route_decision_audit.tex",
        "table_anchor_present": "tab:comparison-route-decision" in author_text,
        "anonymous_table_anchor_present": "tab:comparison-route-decision" in anon_text,
        "acm_table_anchor_present": "tab:comparison-route-decision" in acm_text,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(ANALYSIS)}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(TABLE)}")


if __name__ == "__main__":
    main()
