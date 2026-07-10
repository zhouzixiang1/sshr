#!/usr/bin/env python3
"""Generate a reproducible end-to-end Resource-NMCTS worked example.

The example is intentionally small enough for complete truth-table checking,
but nontrivial enough to expose competing root factors and a reusable
compute/action/uncompute plan.  It records the Boolean function, MCTS root
statistics, emitted logical circuit, resource accounting, and three semantic
verification layers used by the manuscript.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anf_utils import boolean_from_anf  # noqa: E402
from src.factor_plan import (  # noqa: E402
    Plan,
    SearchConfig,
    candidate_actions,
    direct_plan,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.neural_policy import NeuralScorer  # noqa: E402
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.synthesizers import _best_polarity_plan, synthesize  # noqa: E402


RESULTS = PROJECT_ROOT / "results"
TABLES = PROJECT_ROOT / "paper_latex" / "tables"
MODEL = PROJECT_ROOT / "models" / "action_scorer.pt"

N_INPUTS = 5
TERMS = frozenset((0b00111, 0b01011, 0b01110, 0b10011, 0b11100))
SEED = 7
SIMULATIONS = 128


@dataclass(frozen=True)
class WorkedExample:
    config: SearchConfig
    boolean_function: Any
    direct: Plan
    selected: Plan
    neural_mcts: Plan
    direct_circuit: Any
    selected_circuit: Any
    search_rows: list[dict[str, object]]
    resource_rows: list[dict[str, object]]
    truth_rows: list[dict[str, object]]
    gate_rows: list[dict[str, object]]
    verification: dict[str, object]
    full_result: Any


def make_config() -> SearchConfig:
    return SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=4,
        max_factor_size=5,
        candidate_top_k=24,
        min_factor_count=2,
        use_relative_phase=True,
        mcts_simulations=96,
        neural_mcts_simulations=SIMULATIONS,
        max_polarities=32,
        gate_mode="logical_and",
        neural_prior_weight=2.5,
    )


def monomial_ascii(mask: int) -> str:
    variables = [f"x{i}" for i in range(N_INPUTS) if (int(mask) >> i) & 1]
    return "*".join(variables) if variables else "1"


def monomial_latex(mask: int) -> str:
    variables = [f"x_{i}" for i in range(N_INPUTS) if (int(mask) >> i) & 1]
    return "".join(variables) if variables else "1"


def terms_ascii(terms: frozenset[int]) -> str:
    return " xor ".join(monomial_ascii(term) for term in sorted(terms)) if terms else "0"


def terms_latex(terms: frozenset[int]) -> str:
    return r" \oplus ".join(monomial_latex(term) for term in sorted(terms)) if terms else "0"


def plan_signature(plan: Plan) -> tuple[object, ...]:
    return (
        plan.kind,
        int(plan.factor),
        bool(plan.affine_const),
        tuple(sorted(int(term) for term in plan.terms)),
        plan_signature(plan.group) if plan.group is not None else None,
        plan_signature(plan.rest) if plan.rest is not None else None,
    )


def gate_signature(circuit: Any) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (gate.type, tuple(int(control) for control in gate.controls), int(gate.target))
        for gate in circuit.gates
    )


def wire_label(index: int) -> str:
    if index < N_INPUTS:
        return f"x{index}"
    if index == N_INPUTS:
        return "y"
    return f"a{index - N_INPUTS - 1}"


def circuit_rows(variant: str, circuit: Any, stages: list[str]) -> list[dict[str, object]]:
    if len(stages) != len(circuit.gates):
        raise AssertionError(f"stage/gate mismatch for {variant}: {len(stages)} != {len(circuit.gates)}")
    rows: list[dict[str, object]] = []
    for index, (gate, stage) in enumerate(zip(circuit.gates, stages), start=1):
        rows.append(
            {
                "variant": variant,
                "gate_index": index,
                "gate_type": gate.type,
                "controls": ";".join(wire_label(int(control)) for control in gate.controls),
                "target": wire_label(int(gate.target)),
                "stage": stage,
            }
        )
    return rows


def resource_row(label: str, plan: Plan, verification: dict[str, object], baseline_score: float) -> dict[str, object]:
    score = plan.score(make_config().weights)
    return {
        "method": label,
        "T": plan.cost.T,
        "CNOT": plan.cost.CNOT,
        "depth": plan.cost.depth,
        "gates": plan.cost.gates,
        "explicit_factor_ancilla": plan.cost.explicit_ancilla,
        "peak_ancilla": plan.cost.peak_ancilla,
        "score": score,
        "relative_score_change_pct": 100.0 * (score - baseline_score) / baseline_score,
        "plan_verified": verification["plan_verified"],
        "circuit_verified": verification["circuit_verified"],
        "truth_rows_verified": verification["truth_rows_verified"],
    }


def build_example() -> WorkedExample:
    if not MODEL.exists():
        raise FileNotFoundError(MODEL)

    config = make_config()
    bf = boolean_from_anf(N_INPUTS, TERMS)
    direct = direct_plan(TERMS, 0, 0, config)
    scorer = NeuralScorer(MODEL)

    solver = NeuralMCTSSolver(
        config,
        simulations=SIMULATIONS,
        seed=SEED,
        neural_scorer=scorer,
    )
    neural_mcts = solver.solve(TERMS)
    root_key = StateKey(TERMS, 0, 0)
    root = solver.nodes[root_key]
    heuristic_priors = {
        action.factor: action.prior
        for action in candidate_actions(TERMS, 0, 0, config, neural_scorer=None)
    }

    # Resource-NMCTS evaluates this fixed-polarity greedy candidate before the
    # later tied portfolio branches, so it is the emitted full-method result.
    fast_config = replace(
        config,
        candidate_top_k=min(config.candidate_top_k, 18),
        mcts_simulations=min(config.mcts_simulations, 32),
        neural_mcts_simulations=min(config.neural_mcts_simulations, 40),
        max_polarities=min(config.max_polarities, 16),
    )
    polarity, selected_terms, selected, _selected_cost = _best_polarity_plan(
        "fprm_greedy",
        bf,
        fast_config,
        SEED,
        scorer,
    )
    full_result = synthesize(
        "and_resource_nmcts",
        bf,
        config,
        seed=SEED,
        model_path=str(MODEL),
    )

    direct_circuit = emit_plan_to_circuit(direct, N_INPUTS, 0)
    selected_circuit = emit_plan_to_circuit(
        selected,
        N_INPUTS,
        min(config.max_factor_ancilla, selected.cost.explicit_ancilla),
        polarity=polarity,
    )
    neural_circuit = emit_plan_to_circuit(
        neural_mcts,
        N_INPUTS,
        min(config.max_factor_ancilla, neural_mcts.cost.explicit_ancilla),
    )

    direct_plan_check = verify_plan_anf(direct)
    selected_plan_check = verify_plan_anf(selected)
    direct_circuit_check = verify_circuit_anf(direct_circuit, N_INPUTS, TERMS)
    selected_circuit_check = verify_circuit_anf(selected_circuit, N_INPUTS, TERMS)
    direct_truth_ok = verify_oracle(direct_circuit, bf)
    selected_truth_ok = verify_oracle(selected_circuit, bf)

    expected_direct = (40, 65, 65, 25, 0, 1)
    expected_selected = (28, 55, 55, 23, 1, 1)
    direct_tuple = (
        direct.cost.T,
        direct.cost.CNOT,
        direct.cost.depth,
        direct.cost.gates,
        direct.cost.explicit_ancilla,
        direct.cost.peak_ancilla,
    )
    selected_tuple = (
        selected.cost.T,
        selected.cost.CNOT,
        selected.cost.depth,
        selected.cost.gates,
        selected.cost.explicit_ancilla,
        selected.cost.peak_ancilla,
    )
    assert polarity == 0
    assert selected_terms == TERMS
    assert plan_signature(selected) == plan_signature(neural_mcts)
    assert gate_signature(selected_circuit) == gate_signature(neural_circuit)
    assert full_result.cost == selected.cost and full_result.correct
    assert direct_tuple == expected_direct
    assert selected_tuple == expected_selected
    assert direct_plan_check.ok and selected_plan_check.ok
    assert direct_circuit_check.ok and selected_circuit_check.ok
    assert direct_truth_ok and selected_truth_ok
    assert len(direct_circuit.gates) == 5
    assert len(selected_circuit.gates) == 9

    search_rows: list[dict[str, object]] = []
    for index, action in enumerate(root.actions):
        stats = root.stats[index]
        rollout_score = solver._rollout_action_cost(root_key, action)
        estimated_score = stats.q if stats.visits else rollout_score
        heuristic_prior = heuristic_priors[action.factor]
        neural_score = (action.prior - heuristic_prior) / config.neural_prior_weight
        assert abs(action.prior - (heuristic_prior + config.neural_prior_weight * neural_score)) < 1e-12
        search_rows.append(
            {
                "rank": index + 1,
                "factor_mask": hex(action.factor),
                "factor": monomial_ascii(action.factor),
                "grouped_terms": terms_ascii(action.group),
                "group_size": len(action.group),
                "residual_terms": terms_ascii(action.residuals),
                "rest_terms": terms_ascii(action.rest),
                "immediate_gain": action.immediate_gain,
                "heuristic_prior": heuristic_prior,
                "neural_score": neural_score,
                "combined_prior": action.prior,
                "visits": stats.visits,
                "estimated_score": estimated_score,
                "value_source": "MCTS Q" if stats.visits else "greedy rollout",
                "selected_first": action.factor == selected.factor,
            }
        )

    truth_rows = []
    for assignment in range(1 << N_INPUTS):
        truth_rows.append(
            {
                "assignment": assignment,
                "bits_x4_to_x0": format(assignment, f"0{N_INPUTS}b"),
                **{f"x{i}": (assignment >> i) & 1 for i in range(N_INPUTS)},
                "f": bf.evaluate(assignment),
            }
        )

    verification = {
        "plan_verified": direct_plan_check.ok and selected_plan_check.ok,
        "plan_nodes": selected_plan_check.nodes,
        "plan_mismatches": selected_plan_check.mismatches,
        "circuit_verified": direct_circuit_check.ok and selected_circuit_check.ok,
        "circuit_gates": selected_circuit_check.gates,
        "input_mismatches": selected_circuit_check.input_mismatches,
        "output_mismatch": selected_circuit_check.output_mismatch,
        "ancilla_mismatches": selected_circuit_check.ancilla_mismatches,
        "truth_rows_verified": 1 << N_INPUTS,
        "truth_rows_total": 1 << N_INPUTS,
        "truth_verified": direct_truth_ok and selected_truth_ok,
        "portfolio_matches_neural_mcts_plan": plan_signature(selected) == plan_signature(neural_mcts),
    }
    baseline_score = direct.score(config.weights)
    resource_rows = [
        resource_row("AND-direct ANF", direct, verification, baseline_score),
        resource_row("Resource-NMCTS", selected, verification, baseline_score),
    ]

    direct_stages = [f"monomial {monomial_ascii(term)}" for term in sorted(TERMS)]
    selected_stages = [
        "compute x0*x1",
        "reuse with x2",
        "reuse with x3",
        "reuse with x4",
        "uncompute x0*x1",
        "compute x2*x3",
        "reuse with x1",
        "reuse with x4",
        "uncompute x2*x3",
    ]
    gate_rows = circuit_rows("direct", direct_circuit, direct_stages)
    gate_rows.extend(circuit_rows("resource_nmcts", selected_circuit, selected_stages))

    return WorkedExample(
        config=config,
        boolean_function=bf,
        direct=direct,
        selected=selected,
        neural_mcts=neural_mcts,
        direct_circuit=direct_circuit,
        selected_circuit=selected_circuit,
        search_rows=search_rows,
        resource_rows=resource_rows,
        truth_rows=truth_rows,
        gate_rows=gate_rows,
        verification=verification,
        full_result=full_result,
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_search_table(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.08\linewidth}>{\raggedright\arraybackslash}Xrrrrr}",
        r"\toprule",
        r"Factor & Grouped monomials & Heur. & Neural & Combined & Visits & Est. score \\",
        r"\midrule",
    ]
    for row in rows:
        factor = monomial_latex(int(str(row["factor_mask"]), 16))
        if bool(row["selected_first"]):
            factor = r"\mathbf{" + factor + "}"
        group_masks = frozenset(
            term for term in TERMS if (term & int(str(row["factor_mask"]), 16)) == int(str(row["factor_mask"]), 16)
        )
        lines.append(
            "${}$ & ${}$ & {:.3f} & {:.3f} & {:.3f} & {} & {:.3f} \\\\".format(
                factor,
                terms_latex(group_masks),
                float(row["heuristic_prior"]),
                float(row["neural_score"]),
                float(row["combined_prior"]),
                int(row["visits"]),
                float(row["estimated_score"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_resource_table(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"Plan & T & CNOT & Depth & Gates & Factor anc. & Peak anc. & Score & Verified \\",
        r"\midrule",
    ]
    for row in rows:
        label = str(row["method"])
        if label == "Resource-NMCTS":
            label = r"\method{}"
        verified = "32/32" if bool(row["truth_rows_verified"]) else "no"
        lines.append(
            "{} & {} & {} & {} & {} & {} & {} & {:.3f} & {} \\\\".format(
                label,
                int(row["T"]),
                int(row["CNOT"]),
                int(row["depth"]),
                int(row["gates"]),
                int(row["explicit_factor_ancilla"]),
                int(row["peak_ancilla"]),
                float(row["score"]),
                verified,
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_analysis(path: Path, example: WorkedExample) -> None:
    bf = example.boolean_function
    selected_row = next(row for row in example.resource_rows if row["method"] == "Resource-NMCTS")
    onset = ", ".join(str(value) for value in bf.onset)
    lines = [
        "# Resource-NMCTS Worked Example",
        "",
        "## Boolean function",
        "",
        f"- n: {N_INPUTS}",
        f"- ANF: `{terms_ascii(TERMS)}`",
        f"- factored form: `x0*x1*(x2 xor x3 xor x4) xor x2*x3*(x1 xor x4)`",
        f"- truth-table hex: `0x{bf.truth_table:08X}`",
        f"- on-set assignments: {{{onset}}}; all other assignments evaluate to 0",
        "",
        "## Root search trace",
        "",
        "The combined prior is h + 2.5*s_NN, where h is the deterministic heuristic and s_NN is the trained neural score. Lower estimated score is better.",
        "",
        "| rank | factor | grouped terms | heuristic | neural | combined | visits | estimated score | selected first |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in example.search_rows:
        lines.append(
            f"| {row['rank']} | `{row['factor']}` | {row['group_size']} | {float(row['heuristic_prior']):.3f} | "
            f"{float(row['neural_score']):.3f} | {float(row['combined_prior']):.3f} | "
            f"{row['visits']} | {float(row['estimated_score']):.3f} | {row['selected_first']} |"
        )
    lines.extend(
        [
            "",
            "The search selects x0*x1 first, then factors x2*x3 in the rest subproblem. The reverse root order reaches the same final score; deterministic ordering fixes the emitted sequence.",
            "",
            "## Resource change",
            "",
            "| method | T | CNOT | depth | gates | explicit factor ancilla | peak ancilla | score |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in example.resource_rows:
        lines.append(
            f"| {row['method']} | {row['T']} | {row['CNOT']} | {row['depth']} | {row['gates']} | "
            f"{row['explicit_factor_ancilla']} | {row['peak_ancilla']} | {float(row['score']):.3f} |"
        )
    lines.extend(
        [
            "",
            f"Relative score change: {float(selected_row['relative_score_change_pct']):+.2f}%.",
            "",
            "## Verification",
            "",
            f"- plan expansion: pass; nodes={example.verification['plan_nodes']}; mismatches={example.verification['plan_mismatches']}",
            f"- emitted-circuit ANF simulation: pass; gates={example.verification['circuit_gates']}; input/output/ancilla mismatches=0/0/0",
            f"- complete truth table: {example.verification['truth_rows_verified']}/{example.verification['truth_rows_total']} assignments pass",
            f"- full Resource-NMCTS portfolio and neural-MCTS branch emit the same plan: {example.verification['portfolio_matches_neural_mcts_plan']}",
            "",
            "## Claim boundary",
            "",
            "This example explains the core ANF factor-search and emitted circuit. It is not evidence that the neural prior is necessary on this easy instance, and it does not exercise the affine, phase/Rz, Pareto-budget, or high-dimensional frontier branches.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, example: WorkedExample) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "function": {
            "n": N_INPUTS,
            "anf_masks": sorted(TERMS),
            "truth_table_hex": f"0x{example.boolean_function.truth_table:08X}",
            "onset": example.boolean_function.onset,
        },
        "search": {
            "seed": SEED,
            "simulations": SIMULATIONS,
            "neural_prior_weight": example.config.neural_prior_weight,
            "combined_prior_formula": "heuristic_prior + neural_prior_weight * neural_score",
            "model": str(MODEL.relative_to(PROJECT_ROOT)),
            "model_sha256": sha256(MODEL),
            "root_actions": len(example.search_rows),
            "selected_factor": monomial_ascii(example.selected.factor),
        },
        "resource_weights": example.config.weights.__dict__,
        "gate_mode": example.config.gate_mode,
        "verification": example.verification,
        "status_counts": {"pass": 6},
        "needs_revision_count": 0,
        "outputs": {
            "search": "results/raw_worked_example_search.csv",
            "resources": "results/summary_worked_example.csv",
            "truth_table": "results/raw_worked_example_truth_table.csv",
            "gates": "results/raw_worked_example_gates.csv",
            "analysis": "results/analysis_worked_example.md",
            "manifest": "results/manifest_worked_example.json",
            "search_table": "paper_latex/tables/worked_example_search.tex",
            "resource_table": "paper_latex/tables/worked_example_resources.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    example = build_example()
    RESULTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    write_csv(RESULTS / "raw_worked_example_search.csv", example.search_rows)
    write_csv(RESULTS / "summary_worked_example.csv", example.resource_rows)
    write_csv(RESULTS / "raw_worked_example_truth_table.csv", example.truth_rows)
    write_csv(RESULTS / "raw_worked_example_gates.csv", example.gate_rows)
    write_analysis(RESULTS / "analysis_worked_example.md", example)
    write_manifest(RESULTS / "manifest_worked_example.json", example)
    write_search_table(TABLES / "worked_example_search.tex", example.search_rows)
    write_resource_table(TABLES / "worked_example_resources.tex", example.resource_rows)
    print("worked example: truth_table=0xB008C880, root_factor=x0*x1")
    print("resources: direct score=45.825, Resource-NMCTS score=33.255 (-27.43%)")
    print("verification: plan=pass, circuit=pass, truth_table=32/32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
