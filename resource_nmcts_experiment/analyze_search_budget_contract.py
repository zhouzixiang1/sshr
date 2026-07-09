#!/usr/bin/env python3
"""Generate and audit the Resource-NMCTS search-budget contract table."""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def config_values() -> dict[str, str]:
    text = (THIS_DIR / "factor_plan.py").read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for key in (
        "candidate_top_k",
        "max_factor_size",
        "min_factor_count",
        "max_factor_ancilla",
        "mcts_simulations",
        "neural_mcts_simulations",
        "max_polarities",
        "greedy_eval_limit",
    ):
        match = re.search(rf"^\s*{key}:\s*[^=]+=\s*([0-9.]+)", text, flags=re.MULTILINE)
        values[key] = match.group(1) if match else "missing"
    return values


def row_specs(values: dict[str, str]) -> list[dict[str, object]]:
    return [
        {
            "budget_family": "Action fan-out",
            "budget_or_cap": (
                f"candidate_top_k={values['candidate_top_k']}; "
                f"max_factor_size={values['max_factor_size']}; "
                f"min_factor_count={values['min_factor_count']}"
            ),
            "source_anchors": "factor_plan.py: SearchConfig, candidate_actions, actions[: config.candidate_top_k]",
            "required_files": ("factor_plan.py",),
            "required_tokens": ("class SearchConfig", "candidate_top_k", "candidate_actions", "actions[: config.candidate_top_k]"),
            "scalability_role": "Bounds the number of algebraic actions expanded at each ANF state.",
            "boundary": "The cap controls search cost; it is not a proof that the globally best factor action is always included.",
        },
        {
            "budget_family": "Ancilla and recursion",
            "budget_or_cap": f"max_factor_ancilla={values['max_factor_ancilla']}; depth guard=64 in MCTS recursion",
            "source_anchors": "factor_plan.py: live_factor_ancilla guard; nmcts_solver.py: depth > 64 fallback",
            "required_files": ("factor_plan.py", "nmcts_solver.py"),
            "required_tokens": ("live_factor_ancilla >= config.max_factor_ancilla", "depth > 64", "direct_score"),
            "scalability_role": "Prevents recursive factoring from allocating unbounded temporary factor lines.",
            "boundary": "This is a resource guard, not an ancilla-optimality theorem.",
        },
        {
            "budget_family": "PUCT/MCTS simulations",
            "budget_or_cap": (
                f"mcts_simulations={values['mcts_simulations']}; "
                f"neural_mcts_simulations={values['neural_mcts_simulations']}; c_puct=1.35"
            ),
            "source_anchors": "nmcts_solver.py: NeuralMCTSSolver, c_puct, _simulate; synthesizers.py: mcts_factor, neural_mcts",
            "required_files": ("nmcts_solver.py", "synthesizers.py"),
            "required_tokens": ("class NeuralMCTSSolver", "c_puct: float = 1.35", "_simulate", "mcts_factor", "neural_mcts"),
            "scalability_role": "Makes tree-search compute an explicit, rerunnable budget rather than an open-ended optimizer.",
            "boundary": "The MCTS budget supports a bounded search-control claim, not exact optimal synthesis.",
        },
        {
            "budget_family": "Polarity and affine search",
            "budget_or_cap": f"max_polarities={values['max_polarities']}; high-dimensional direct screening narrows expensive planning trials",
            "source_anchors": "synthesizers.py: _ranked_polarities, _direct_screened_polarities, screen_budget, screen_top_k",
            "required_files": ("synthesizers.py",),
            "required_tokens": ("_ranked_polarities", "_direct_screened_polarities", "screen_budget", "screen_top_k", "max_polarities"),
            "scalability_role": "Keeps fixed-polarity and affine preconditioning searches tractable on larger sparse term sets.",
            "boundary": "Screening is a controlled heuristic; missed polarities remain part of the search-boundary limitation.",
        },
        {
            "budget_family": "Resource portfolio",
            "budget_or_cap": "fast_config caps candidate_top_k<=18, MCTS<=32/40, max_polarities<=16/24 before portfolio selection",
            "source_anchors": "synthesizers.py: resource_heuristic/resource_no_mcts/resource_nmcts fast_config, _run_child_portfolio",
            "required_files": ("synthesizers.py",),
            "required_tokens": ("resource_no_mcts", "resource_nmcts", "candidate_top_k=min(config.candidate_top_k, 18)", "max_polarities=min(config.max_polarities, 16)", "_run_child_portfolio"),
            "scalability_role": "Separates cheap deterministic candidates from more expensive MCTS or affine branches.",
            "boundary": "Portfolio selection gives a best verified candidate among attempted children, not a certificate over all possible children.",
        },
        {
            "budget_family": "Pareto archive",
            "budget_or_cap": "Deduplicate by (T,CNOT,depth,gates,peak ancilla), remove dominated candidates, then rank the non-dominated front by active score",
            "source_anchors": "synthesizers.py: _resource_dims, _dominates, _pareto_front, _resource_selection_key",
            "required_files": ("synthesizers.py",),
            "required_tokens": ("_resource_dims", "_dominates", "_pareto_front", "_resource_selection_key"),
            "scalability_role": "Keeps multi-objective diversity without carrying every generated candidate into the final comparison.",
            "boundary": "The archive is Pareto over generated candidates only; it is not a global Pareto frontier.",
        },
        {
            "budget_family": "High-dimensional frontier controllers",
            "budget_or_cap": "Staged, sparse, and learned gates decide whether depth-3/depth-4 Boolean-ring screens are evaluated",
            "source_anchors": "train_sparse_depth4_gate.py: threshold; run_truth_bridge_terms.py: load_depth2_guard, depth_frontier_policy, screen_depth4",
            "required_files": ("train_sparse_depth4_gate.py", "run_truth_bridge_terms.py"),
            "required_tokens": ("threshold", "load_depth2_guard", "depth_frontier_policy", "screen_depth4"),
            "scalability_role": "Moves large-term-set runs from all-frontier evaluation toward validated budget control.",
            "boundary": "The controller is empirical on the audited slices and is not a proof that depth-4 can always be skipped.",
        },
        {
            "budget_family": "Verification route",
            "budget_or_cap": "Symbolic ANF/circuit checks for large rows; complete truth-table bridge slices where enumeration is feasible",
            "source_anchors": "factor_plan.py: verify_plan_anf, verify_circuit_anf, verify_oracle; run_truth_bridge_terms.py: truth bridge rows",
            "required_files": ("factor_plan.py", "run_truth_bridge_terms.py"),
            "required_tokens": ("verify_plan_anf", "verify_circuit_anf", "verify_oracle", "truth"),
            "scalability_role": "Allows high-dimensional evidence without pretending that every large instance was exhaustively enumerated.",
            "boundary": "Symbolic verification is exact for emitted GF(2) semantics but does not replace hardware mapping or exhaustive enumeration for all n.",
        },
    ]


def source_text(files: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for name in files:
        path = THIS_DIR / name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in row_specs(config_values()):
        files = tuple(spec["required_files"])
        tokens = tuple(spec["required_tokens"])
        text = source_text(files)
        missing_files = [name for name in files if not (THIS_DIR / name).exists()]
        missing_tokens = [token for token in tokens if token not in text]
        status = "pass" if not missing_files and not missing_tokens else "needs revision"
        rows.append(
            {
                "budget_family": str(spec["budget_family"]),
                "budget_or_cap": str(spec["budget_or_cap"]),
                "source_anchors": str(spec["source_anchors"]),
                "scalability_role": str(spec["scalability_role"]),
                "boundary": str(spec["boundary"]),
                "required_files": "; ".join(files),
                "required_tokens": "; ".join(tokens),
                "missing_files": "; ".join(missing_files),
                "missing_tokens": "; ".join(missing_tokens),
                "status": status,
                "next_action": "No action needed."
                if status == "pass"
                else "Update the budget contract or restore the implementation anchor before rebuilding.",
            }
        )
    return rows


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
        .replace("<=", r"$\leq$")
        .replace(">=", r"$\geq$")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("Resource-NMCTS", r"\method{}"),
        ("ANF", r"\anf{}"),
        ("MCTS", r"\mcts{}"),
        ("CNOT", r"CNOT"),
        ("T,CNOT,depth,gates,peak ancilla", r"T,CNOT,depth,gates,peak ancilla"),
        ("depth-3/depth-4", r"depth-3/depth-4"),
        ("GF(2)", r"GF(2)"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "budget_family",
        "budget_or_cap",
        "source_anchors",
        "scalability_role",
        "boundary",
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
        "# Search Budget Contract",
        "",
        "This audit records the explicit search budgets and scalability guards used by Resource-NMCTS.",
        "It is a method contract rather than a performance result.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| budget family | budget or cap | source anchors | scalability role | boundary | status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {budget_family} | {budget_or_cap} | `{source_anchors}` | {scalability_role} | {boundary} | {status} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Budget family & Explicit cap & Scalability role & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["budget_family"]),
                latex_cell(row["budget_or_cap"]),
                latex_cell(row["scalability_role"]),
                latex_cell(row["boundary"]),
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
        "search_config": config_values(),
        "outputs": {
            "summary": "results/summary_search_budget_contract.csv",
            "analysis": "results/analysis_search_budget_contract.md",
            "manifest": "results/manifest_search_budget_contract.json",
            "table": "paper_latex/tables/search_budget_contract.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_search_budget_contract.csv", rows)
    write_markdown(RESULTS / "analysis_search_budget_contract.md", rows)
    write_latex(TABLES / "search_budget_contract.tex", rows)
    write_manifest(RESULTS / "manifest_search_budget_contract.json", rows)
    failures = sum(1 for row in rows if row["status"] != "pass")
    print(f"wrote {len(rows)} search budget contract row(s)")
    if failures:
        print(f"warning: {failures} search budget contract row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
