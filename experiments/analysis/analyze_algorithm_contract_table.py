#!/usr/bin/env python3
"""Generate and audit the algorithm-level Resource-NMCTS contract table."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


ROWS = [
    {
        "stage": "Canonical state",
        "operational_rule": "Normalize a truth table, exported benchmark, or supplied term list into a square-free ANF monomial set; direct ANF remains the fallback plan at every state.",
        "source_anchors": "synthesizers.py: anf_monomials; factor_plan.py: frozenset, direct_plan",
        "required_files": ("synthesizers.py", "factor_plan.py"),
        "required_tokens": ("anf_monomials", "frozenset", "direct_plan"),
        "guarantee": "The search starts from the same Boolean function as the baseline and always has a syntactically valid logical oracle construction.",
    },
    {
        "stage": "Action generation",
        "operational_rule": "Generate monomial factors, linear/Boolean-ring factors, FPRM polarity actions, and affine/linear-pair candidates only when they have an explicit GF(2) expansion.",
        "source_anchors": "factor_plan.py: candidate_actions, linear_factor_actions, _linear_boolean_expansion; synthesizers.py: affine_linear_pair_beam_plan",
        "required_files": ("factor_plan.py", "synthesizers.py"),
        "required_tokens": (
            "candidate_actions",
            "linear_factor_actions",
            "_linear_boolean_expansion",
            "affine_linear_pair_beam_plan",
        ),
        "guarantee": "Learning never invents a semantic rule; it can only rank or select among algebraic actions that the emitter and verifier can expand.",
    },
    {
        "stage": "Prior-guided tree search",
        "operational_rule": "Use the neural scorer to bias action priors, then run PUCT/MCTS recursion with greedy rollouts and bounded candidate_top_k expansion.",
        "source_anchors": "neural_policy.py: NeuralScorer, score_many; nmcts_solver.py: NeuralMCTSSolver, c_puct; factor_plan.py: candidate_top_k",
        "required_files": ("neural_policy.py", "nmcts_solver.py", "factor_plan.py"),
        "required_tokens": ("class NeuralScorer", "score_many", "class NeuralMCTSSolver", "c_puct", "candidate_top_k"),
        "guarantee": "The neural component is a budget-allocation prior, not a correctness oracle or an unrestricted circuit generator.",
    },
    {
        "stage": "Baseline guard",
        "operational_rule": "Evaluate deterministic, beam, MCTS, neural, and screen candidates as a portfolio; guarded neural variants return the better of the baseline and learned candidate.",
        "source_anchors": "synthesizers.py: _run_child_portfolio, min([baseline, neural_plan], _portfolio_result, direct_anf",
        "required_files": ("synthesizers.py",),
        "required_tokens": ("_run_child_portfolio", "min([baseline, neural_plan]", "_portfolio_result", "direct_anf"),
        "guarantee": "A learned or expensive branch is allowed to help but is not allowed to replace a stronger verified deterministic candidate in guarded rows.",
    },
    {
        "stage": "Pareto archive",
        "operational_rule": "Collect candidates from multiple resource profiles, remove candidates dominated in T, CNOT, depth, gates, and peak ancilla, then select by the active score.",
        "source_anchors": "synthesizers.py: _pareto_front, _dominates, _resource_selection_key, pareto_resource_nmcts",
        "required_files": ("synthesizers.py",),
        "required_tokens": ("_pareto_front", "_dominates", "_resource_selection_key", "pareto_resource_nmcts"),
        "guarantee": "Weighted-score wins are kept separate from multi-resource dominance, which is why tradeoff tables remain part of the Results section.",
    },
    {
        "stage": "Reinforcement-learned budget control",
        "operational_rule": "After a verified base Resource-NMCTS result, a fitted-Q contextual-bandit policy chooses whether to stop or invoke Pareto-Resource-NMCTS under a validation-fixed threshold.",
        "source_anchors": "train_mcts_budget_policy.py: run_reward, fitted_q; evaluate_mcts_budget_policy.py: policy decisions and held-out gates",
        "required_files": ("train_mcts_budget_policy.py", "evaluate_mcts_budget_policy.py"),
        "required_tokens": ("def run_reward", "contextual_bandit_fitted_q_iteration", "run_pareto", "exact_fingerprint_overlap"),
        "guarantee": "The policy changes search effort only; both actions return semantically verified circuits, and nonzero regret against always-Pareto remains visible.",
    },
    {
        "stage": "Large-scale controllers",
        "operational_rule": "Use depth-frontier policies and sparse gates to decide which high-dimensional Boolean-ring screens to evaluate, with deterministic sparse/full frontiers kept as references.",
        "source_anchors": "run_truth_bridge_terms.py: load_depth2_guard, load_frontier_policy, depth_frontier_policy, screen_depth4",
        "required_files": ("run_truth_bridge_terms.py",),
        "required_tokens": ("load_depth2_guard", "load_frontier_policy", "depth_frontier_policy", "screen_depth4"),
        "guarantee": "High-dimensional controllers are planning-time controls over symbolic term-set verification, not hardware schedulers or exhaustive truth-table solvers.",
    },
    {
        "stage": "Emission and verification",
        "operational_rule": "Emit X/CNOT/MCT compute-action-uncompute circuits, verify ANF semantics symbolically, and use complete truth-table or phase checks where feasible before writing raw result rows.",
        "source_anchors": "factor_plan.py: emit_plan_to_circuit, verify_plan_anf, verify_circuit_anf, verify_oracle; run_experiments.py: correct",
        "required_files": ("factor_plan.py", "run_experiments.py"),
        "required_tokens": ("emit_plan_to_circuit", "verify_plan_anf", "verify_circuit_anf", "verify_oracle", "correct"),
        "guarantee": "Paper comparisons consume matched rows that passed the relevant semantic check; skipped, errored, or timed-out rows are not silently counted.",
    },
]


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


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
        ("ANF", r"\anf{}"),
        ("FPRM", r"\fprm{}"),
        ("MCTS", r"\mcts{}"),
        ("PUCT", r"PUCT"),
        ("GF(2)", r"GF(2)"),
        ("T, CNOT, depth, gates, and peak ancilla", r"T, CNOT, depth, gates, and peak ancilla"),
        ("X/CNOT/MCT", r"X/CNOT/\mct{}"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def source_text(files: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for name in files:
        path = THIS_DIR / name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in ROWS:
        files = tuple(row["required_files"])
        tokens = tuple(row["required_tokens"])
        text = source_text(files)
        missing_files = [name for name in files if not (THIS_DIR / name).exists()]
        missing_tokens = [token for token in tokens if token not in text]
        status = "pass" if not missing_files and not missing_tokens else "needs revision"
        rows.append(
            {
                "stage": row["stage"],
                "operational_rule": row["operational_rule"],
                "source_anchors": row["source_anchors"],
                "guarantee": row["guarantee"],
                "required_files": "; ".join(files),
                "required_tokens": "; ".join(tokens),
                "missing_files": "; ".join(missing_files),
                "missing_tokens": "; ".join(missing_tokens),
                "status": status,
                "next_action": "No action needed."
                if status == "pass"
                else "Update the manuscript contract or restore the implementation anchor before rebuilding.",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "stage",
        "operational_rule",
        "source_anchors",
        "guarantee",
        "required_files",
        "required_tokens",
        "missing_files",
        "missing_tokens",
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
        "# Algorithm Contract Table",
        "",
        "This audit converts the Resource-NMCTS method description into implementation-anchored algorithm contracts. Each row records the operational rule, source anchors, and reviewer-facing guarantee.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| stage | operational rule | source anchors | guarantee | status |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {stage} | {operational_rule} | `{source_anchors}` | {guarantee} | {status} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.27\linewidth}>{\raggedright\arraybackslash}p{0.24\linewidth}}",
        r"\toprule",
        r"Stage & Operational rule & Source anchors & Reviewer-facing guarantee \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["stage"]),
                latex_cell(row["operational_rule"]),
                latex_cell(row["source_anchors"]),
                latex_cell(row["guarantee"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "outputs": {
            "summary": "results/summary_algorithm_contract.csv",
            "analysis": "results/analysis_algorithm_contract.md",
            "manifest": "results/manifest_algorithm_contract.json",
            "table": "paper_latex/tables/algorithm_contract.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_algorithm_contract.csv", rows)
    write_markdown(RESULTS / "analysis_algorithm_contract.md", rows)
    write_latex(TABLES / "algorithm_contract.tex", rows)
    write_manifest(RESULTS / "manifest_algorithm_contract.json", rows)
    failures = sum(1 for row in rows if row["status"] != "pass")
    print(f"wrote {len(rows)} algorithm contract row(s)")
    if failures:
        print(f"warning: {failures} algorithm contract row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
