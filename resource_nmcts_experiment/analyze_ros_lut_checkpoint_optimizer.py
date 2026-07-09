#!/usr/bin/env python3
"""Exact small-checkpoint optimizer for the ROS-style LUT garbage proxy.

The current ROS-facing proxy evaluates three executable schedules over verified
ABC LUT DAGs.  This audit moves one step closer to ROS-style garbage management
without claiming the unavailable official flow: for DAGs with a small number of
multi-fanout checkpoint candidates, it exhaustively enumerates every checkpoint
subset and selects the lowest-score schedule under several peak-ancilla budgets.

Large fanout-heavy DAGs are deliberately recorded as out of exact scope.  The
result is an exact subproblem over the existing verified LUT networks, not a
full reproduction of the ROS SAT garbage-management implementation.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

BEST_ROWS = RESULTS / "raw_ros_lut_proxy_best.csv"
GARBAGE_RAW = RESULTS / "raw_ros_lut_garbage_proxy.csv"
RAW_OUT = RESULTS / "raw_ros_lut_checkpoint_optimizer.csv"
SUMMARY_OUT = RESULTS / "summary_ros_lut_checkpoint_optimizer.csv"
ANALYSIS_OUT = RESULTS / "analysis_ros_lut_checkpoint_optimizer.md"
MANIFEST_OUT = RESULTS / "manifest_ros_lut_checkpoint_optimizer.json"
TABLE_OUT = TABLES / "ros_lut_checkpoint_optimizer.tex"

DEFAULT_INTERNAL = (
    RESULTS / "raw_traditional_resource.csv",
    RESULTS / "raw_highdim_resource.csv",
    RESULTS / "raw_highdim_scale_resource.csv",
    RESULTS / "raw_ultra_highdim_resource.csv",
    RESULTS / "raw_mega_highdim_resource.csv",
)

BUDGETS = (
    ("keep100", 1.00),
    ("line75", 0.75),
    ("line50", 0.50),
    ("line25", 0.25),
    ("minline", 0.00),
)
METRICS = ("score", "T", "peak_ancilla")
TARGETS = ("and_resource_nmcts", "and_pareto_resource_nmcts")


@dataclass(frozen=True)
class Cost:
    T: int = 0
    CNOT: int = 0
    gates: int = 0
    depth: int = 0
    explicit_ancilla: int = 0
    peak_ancilla: int = 0


def score(cost: Cost) -> float:
    return cost.T + 0.04 * cost.CNOT + 0.015 * cost.depth + 0.01 * cost.gates + 2.0 * cost.peak_ancilla


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "name",
        "n",
        "budget",
        "cap_fraction",
        "peak_cap",
        "method",
        "selected_policy",
        "solver_mode",
        "checkpoint_candidates",
        "selected_checkpoint_nodes",
        "evaluated_subsets",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "lut_nodes",
        "lut_edges",
        "selected_k",
        "exact_over_checkpoint_candidates",
        "official_ros_fully_reproduced",
        "error",
    ]
    ordered = [field for field in preferred if field in fields]
    ordered.extend(field for field in fields if field not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str] | dict[str, object], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in {"", None}:
        return default
    return float(value)


def int_field(row: dict[str, str], key: str) -> int:
    return int(float(row[key]))


def policy_key(row: dict[str, str]) -> tuple[str, str]:
    return (row["dataset"], row["name"])


def usable_policy_row(row: dict[str, str]) -> bool:
    return not row.get("error") and str(row.get("correct")) == "True"


def group_garbage_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    out: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in rows:
        if usable_policy_row(row):
            out.setdefault(policy_key(row), {})[row["policy"]] = row
    return out


def load_internal(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if path.exists():
            rows.extend(row for row in read_csv(path) if not row.get("error") and not row.get("skipped"))
    return rows


def by_name_method(rows: Iterable[dict[str, str] | dict[str, object]]) -> dict[str, dict[str, dict[str, str] | dict[str, object]]]:
    out: dict[str, dict[str, dict[str, str] | dict[str, object]]] = {}
    for row in rows:
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def cost_from_row(row: dict[str, str]) -> Cost:
    return Cost(
        T=int(round(f(row, "T"))),
        CNOT=int(round(f(row, "CNOT"))),
        gates=int(round(f(row, "gates"))),
        depth=int(round(f(row, "depth"))),
        explicit_ancilla=int(round(f(row, "explicit_ancilla"))),
        peak_ancilla=int(round(f(row, "peak_ancilla"))),
    )


def checkpoint_subset_cost(
    nodes,
    output: str,
    checkpoints: frozenset[str],
    output_cnot: int,
    output_gate: int,
) -> tuple[Cost, int]:
    from analyze_ros_lut_garbage_proxy import add_cost, build_local_nodes, checkpoint_setup_cost, recursive_compute_cost

    node_by_output = build_local_nodes(nodes)
    if output not in node_by_output:
        return Cost(CNOT=output_cnot, gates=output_gate, depth=output_gate), 0
    setup, setup_peak, setup_calls = checkpoint_setup_cost(nodes, node_by_output, checkpoints)
    cone, cone_peak, cone_calls = recursive_compute_cost(output, node_by_output, checkpoints, {})
    total = add_cost(setup, cone)
    total = Cost(
        T=2 * total.T,
        CNOT=2 * total.CNOT + output_cnot,
        gates=2 * total.gates + output_gate,
        depth=2 * total.depth + output_gate,
        explicit_ancilla=len(checkpoints) + 1,
        peak_ancilla=max(setup_peak, len(checkpoints) + cone_peak),
    )
    return total, 2 * (setup_calls + cone_calls)


def schedule_row(
    base: dict[str, str],
    budget: str,
    cap_fraction: float,
    peak_cap: float,
    selected: dict[str, object],
    keep: dict[str, str],
    solver_mode: str,
    checkpoint_candidates: int,
    evaluated_subsets: int,
) -> dict[str, object]:
    return {
        "dataset": base["dataset"],
        "name": base["name"],
        "n": int_field(base, "n"),
        "budget": budget,
        "cap_fraction": cap_fraction,
        "peak_cap": peak_cap,
        "method": f"external_ros_lut_checkpoint_opt_{budget}",
        "selected_policy": selected["selected_policy"],
        "solver_mode": solver_mode,
        "checkpoint_candidates": checkpoint_candidates,
        "selected_checkpoint_nodes": selected["selected_checkpoint_nodes"],
        "evaluated_subsets": evaluated_subsets,
        "T": selected["T"],
        "CNOT": selected["CNOT"],
        "depth": selected["depth"],
        "gates": selected["gates"],
        "explicit_ancilla": selected["explicit_ancilla"],
        "peak_ancilla": selected["peak_ancilla"],
        "n_qubits": int_field(base, "n") + 1 + int(round(float(selected["explicit_ancilla"]))),
        "score": selected["score"],
        "lut_nodes": f(keep, "lut_nodes"),
        "lut_edges": f(keep, "lut_edges"),
        "selected_k": int_field(base, "selected_k"),
        "exact_over_checkpoint_candidates": True,
        "official_ros_fully_reproduced": False,
        "error": "",
    }


def candidate_from_cost(
    policy: str,
    cost: Cost,
    expanded_calls: int,
    selected_checkpoint_nodes: int,
) -> dict[str, object]:
    return {
        "selected_policy": policy,
        "selected_checkpoint_nodes": selected_checkpoint_nodes,
        "expanded_compute_calls": expanded_calls,
        "T": cost.T,
        "CNOT": cost.CNOT,
        "depth": cost.depth,
        "gates": cost.gates,
        "explicit_ancilla": cost.explicit_ancilla,
        "peak_ancilla": cost.peak_ancilla,
        "score": score(cost),
    }


def enumerate_exact_candidates(
    best: dict[str, str],
    policies: dict[str, dict[str, str]],
    max_checkpoints: int,
) -> tuple[list[dict[str, object]], int, str]:
    from analyze_ros_lut_garbage_proxy import (
        DEFAULT_ABC_BIN,
        blif_lut_network_cost,
        bool_from_row,
        display_path,
        fanout_counts,
        load_manifest_index,
        output_toggle_cost,
        render_lut,
    )

    keep = policies["keep_all_bennett"]
    fanout_count = int_field(best, "_fanout_checkpoint_nodes")
    if fanout_count == 0:
        candidates = [
            candidate_from_cost("keep_all_bennett", cost_from_row(keep), int_field(keep, "expanded_compute_calls"), int_field(keep, "checkpoint_nodes")),
        ]
        zero = policies.get("zero_checkpoint")
        if zero is not None:
            candidates.append(
                candidate_from_cost("zero_checkpoint", cost_from_row(zero), int_field(zero, "expanded_compute_calls"), int_field(zero, "checkpoint_nodes"))
            )
        return candidates, 0, "trivial_no_fanout"
    if fanout_count > max_checkpoints:
        return [], fanout_count, "out_of_exact_scope"

    source = load_manifest_index(best["source_manifest"])[best["name"]]
    bf = bool_from_row(source)
    selected_k = int_field(best, "selected_k")
    abc_bin = Path(best.get("abc_binary") or display_path(DEFAULT_ABC_BIN)).expanduser()
    _inputs, output, nodes, correct = render_lut(source, selected_k, abc_bin, timeout=30.0)
    if not correct:
        raise RuntimeError(f"ABC LUT render did not verify for {best['name']}")
    fanout = fanout_counts(nodes)
    checkpoint_names = tuple(node.output for node in nodes if fanout[node.output] > 1 and node.output != output)
    if len(checkpoint_names) != fanout_count:
        fanout_count = len(checkpoint_names)
    if fanout_count > max_checkpoints:
        return [], fanout_count, "out_of_exact_scope"

    output_cnot, output_gate = output_toggle_cost(bf)
    candidates = [
        candidate_from_cost("keep_all_bennett", blif_lut_network_cost(_inputs, output, nodes, bf), 2 * len(nodes), len(nodes)),
    ]
    evaluated = 0
    for size in range(fanout_count + 1):
        for subset in itertools.combinations(checkpoint_names, size):
            checkpoints = frozenset(subset)
            cost, calls = checkpoint_subset_cost(nodes, output, checkpoints, output_cnot, output_gate)
            if size == 0:
                policy = "zero_checkpoint"
            elif size == fanout_count:
                policy = "fanout_checkpoint"
            else:
                policy = "checkpoint_subset"
            candidates.append(candidate_from_cost(policy, cost, calls, size))
            evaluated += 1
    return candidates, evaluated, "exact_exhaustive"


def select_budget_candidates(
    best: dict[str, str],
    keep: dict[str, str],
    candidates: list[dict[str, object]],
    solver_mode: str,
    checkpoint_candidates: int,
    evaluated_subsets: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    keep_peak = f(keep, "peak_ancilla")
    for budget, cap_fraction in BUDGETS:
        if budget == "minline":
            peak_cap = min(float(candidate["peak_ancilla"]) for candidate in candidates)
        else:
            peak_cap = max(1, int(math.floor(keep_peak * cap_fraction)))
        feasible = [candidate for candidate in candidates if float(candidate["peak_ancilla"]) <= peak_cap + 1e-9]
        if not feasible:
            continue
        selected = min(
            feasible,
            key=lambda candidate: (
                float(candidate["score"]),
                float(candidate["T"]),
                float(candidate["peak_ancilla"]),
                str(candidate["selected_policy"]),
                int(candidate["selected_checkpoint_nodes"]),
            ),
        )
        rows.append(
            schedule_row(
                best,
                budget,
                cap_fraction,
                peak_cap,
                selected,
                keep,
                solver_mode,
                checkpoint_candidates,
                evaluated_subsets,
            )
        )
    return rows


def build_raw_rows(best_rows: list[dict[str, str]], garbage_rows: list[dict[str, str]], max_checkpoints: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped = group_garbage_rows(garbage_rows)
    raw_rows: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for best in sorted(best_rows, key=lambda row: (row["dataset"], int(float(row.get("index") or 0)), row["name"])):
        policies = grouped.get(policy_key(best))
        if not policies or "keep_all_bennett" not in policies or "fanout_checkpoint" not in policies:
            skipped.append({**best, "skip_reason": "missing_garbage_policy_rows"})
            continue
        keep = policies["keep_all_bennett"]
        best = dict(best)
        best["_fanout_checkpoint_nodes"] = policies["fanout_checkpoint"]["checkpoint_nodes"]
        try:
            candidates, evaluated_subsets, solver_mode = enumerate_exact_candidates(best, policies, max_checkpoints)
            if not candidates:
                skipped.append(
                    {
                        "dataset": best["dataset"],
                        "name": best["name"],
                        "n": best["n"],
                        "checkpoint_candidates": best["_fanout_checkpoint_nodes"],
                        "skip_reason": solver_mode,
                    }
                )
                continue
            raw_rows.extend(
                select_budget_candidates(
                    best,
                    keep,
                    candidates,
                    solver_mode,
                    int(float(best["_fanout_checkpoint_nodes"])),
                    evaluated_subsets,
                )
            )
        except Exception as exc:
            skipped.append(
                {
                    "dataset": best["dataset"],
                    "name": best["name"],
                    "n": best["n"],
                    "checkpoint_candidates": best.get("_fanout_checkpoint_nodes", ""),
                    "skip_reason": repr(exc),
                }
            )
    return raw_rows, skipped


def summarize_frontier(raw_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for budget, _fraction in BUDGETS:
        rows = [row for row in raw_rows if row["budget"] == budget]
        if not rows:
            continue
        policies = Counter(str(row["selected_policy"]) for row in rows)
        modes = Counter(str(row["solver_mode"]) for row in rows)
        out.append(
            {
                "target": f"external_ros_lut_checkpoint_opt_{budget}",
                "baseline": "checkpoint-subset optimizer",
                "metric": "frontier",
                "items": len(rows),
                "wins": "",
                "losses": "",
                "ties": "",
                "mean_relative": "",
                "mean_peak_ancilla": statistics.mean(float(row["peak_ancilla"]) for row in rows),
                "mean_log10_score": statistics.mean(math.log10(float(row["score"]) + 1.0) for row in rows),
                "mean_evaluated_subsets": statistics.mean(float(row["evaluated_subsets"]) for row in rows),
                "mean_checkpoint_candidates": statistics.mean(float(row["checkpoint_candidates"]) for row in rows),
                "policy_counts": ";".join(f"{key}:{value}" for key, value in sorted(policies.items())),
                "mode_counts": ";".join(f"{key}:{value}" for key, value in sorted(modes.items())),
                "status": "pass",
            }
        )
    return out


def rel(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0)


def compare(
    joined: dict[str, dict[str, dict[str, str] | dict[str, object]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    relatives: list[float] = []
    wins = losses = ties = 0
    for methods in joined.values():
        if target not in methods or baseline not in methods:
            continue
        target_value = f(methods[target], metric)
        baseline_value = f(methods[baseline], metric)
        if target_value < baseline_value - 1e-9:
            wins += 1
        elif target_value > baseline_value + 1e-9:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(target_value, baseline_value))
    if not relatives:
        return None
    return {
        "target": target,
        "baseline": baseline,
        "metric": metric,
        "items": len(relatives),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives),
        "status": "pass",
    }


def build_summary_rows(raw_rows: list[dict[str, object]], internal_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(raw_rows).items():
        joined.setdefault(name, {}).update(methods)

    summary = summarize_frontier(raw_rows)
    for budget, _fraction in BUDGETS:
        baseline = f"external_ros_lut_checkpoint_opt_{budget}"
        for target in TARGETS:
            for metric in METRICS:
                row = compare(joined, target, baseline, metric)
                if row is not None:
                    summary.append(row)
    return summary


def pct_rel(value: float) -> str:
    return f"{100.0 * value:+.2f}%"


def tex_pct_rel(value: float) -> str:
    return pct_rel(value).replace("%", r"\%")


def write_analysis(raw_rows: list[dict[str, object]], skipped: list[dict[str, object]], summary_rows: list[dict[str, object]], max_checkpoints: int) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    comparison_rows = [row for row in summary_rows if row["metric"] != "frontier"]
    solved_functions = len({str(row["name"]) for row in raw_rows})
    solved_traditional = len({str(row["name"]) for row in raw_rows if int(float(row["n"])) <= 6})
    skipped_reasons = Counter(str(row.get("skip_reason", "")) for row in skipped)
    lines = [
        "# ROS-Style LUT Checkpoint Optimizer",
        "",
        "This audit strengthens the ROS-facing garbage-management proxy by solving",
        "an exact checkpoint-subset subproblem on verified ABC LUT DAGs with small",
        "multi-fanout candidate sets.",
        "",
        "It is not the official ROS SAT garbage-management implementation.  It is an",
        "exhaustive optimizer over the checkpoint candidates induced by the already",
        "verified LUT DAGs.",
        "",
        "## Scope",
        "",
        f"- max checkpoint candidates enumerated per DAG: {max_checkpoints}",
        f"- solved functions: {solved_functions}",
        f"- solved traditional n<=6 functions: {solved_traditional}",
        f"- skipped functions: {len(skipped)}",
    ]
    if skipped_reasons:
        lines.append("- skip reasons: " + "; ".join(f"{key}={value}" for key, value in sorted(skipped_reasons.items())))
    lines.extend(
        [
            "",
            "## Frontier summary",
            "",
            "| budget | functions | mean peak ancilla | mean log10(score+1) | mean checkpoint candidates | mean evaluated subsets | selected policies |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in frontier_rows:
        budget = str(row["target"]).replace("external_ros_lut_checkpoint_opt_", "")
        lines.append(
            "| {budget} | {items} | {peak:.2f} | {score:.2f} | {cand:.2f} | {subsets:.2f} | {policies} |".format(
                budget=budget,
                items=row["items"],
                peak=float(row["mean_peak_ancilla"]),
                score=float(row["mean_log10_score"]),
                cand=float(row["mean_checkpoint_candidates"]),
                subsets=float(row["mean_evaluated_subsets"]),
                policies=row["policy_counts"],
            )
        )
    lines.extend(
        [
            "",
            "## Resource comparisons on solved rows",
            "",
            "| target | optimized LUT baseline | metric | items | W/L/T | mean relative |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            "| {target} | {baseline} | {metric} | {items} | {wins}/{losses}/{ties} | {delta} |".format(
                target=row["target"],
                baseline=str(row["baseline"]).replace("external_ros_lut_checkpoint_opt_", ""),
                metric=row["metric"],
                items=row["items"],
                wins=row["wins"],
                losses=row["losses"],
                ties=row["ties"],
                delta=pct_rel(float(row["mean_relative"])),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This exact subproblem tests whether the three-policy garbage proxy hides a better checkpoint subset on tractable DAGs.",
            "- The coverage is strongest for the traditional n<=6 comparison slice; large fanout-heavy high-dimensional DAGs remain outside exact enumeration.",
            "- The row should be described as an exact ROS-style checkpoint-subset audit, not as full ROS reproduction or hardware mapping.",
        ]
    )
    ANALYSIS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(summary_rows: list[dict[str, object]]) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    comparison_lookup = {
        (row["target"], row["baseline"], row["metric"]): row
        for row in summary_rows
        if row["metric"] != "frontier"
    }
    focus = [
        ("and_pareto_resource_nmcts", "external_ros_lut_checkpoint_opt_keep100", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_checkpoint_opt_line50", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_checkpoint_opt_minline", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_checkpoint_opt_minline", "peak_ancilla"),
    ]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}rrrr>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Budget & Funcs. & Peak & log$_{10}$ score & Subsets & Selected policies \\",
        r"\midrule",
    ]
    for row in frontier_rows:
        budget = str(row["target"]).replace("external_ros_lut_checkpoint_opt_", "")
        policies = str(row["policy_counts"]).replace("_", r"\_").replace(";", "; ")
        lines.append(
            "{} & {} & {:.1f} & {:.2f} & {:.1f} & {} \\\\".format(
                budget,
                int(row["items"]),
                float(row["mean_peak_ancilla"]),
                float(row["mean_log10_score"]),
                float(row["mean_evaluated_subsets"]),
                policies,
            )
        )
    lines.extend(
        [
            r"\midrule",
            r"Comparison & Items & W/L/T & Mean $\Delta$ & & Boundary \\",
        ]
    )
    for target, baseline, metric in focus:
        row = comparison_lookup.get((target, baseline, metric))
        if row is None:
            continue
        budget = baseline.replace("external_ros_lut_checkpoint_opt_", "")
        label = f"Pareto vs {budget}"
        if metric == "peak_ancilla":
            label += " lines"
        lines.append(
            "{} & {} & {}/{}/{} & {} & & {} \\\\".format(
                label,
                row["items"],
                row["wins"],
                row["losses"],
                row["ties"],
                tex_pct_rel(float(row["mean_relative"])),
                "exact subproblem, not full ROS",
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(raw_rows: list[dict[str, object]], skipped: list[dict[str, object]], summary_rows: list[dict[str, object]], max_checkpoints: int) -> None:
    frontier_rows = [row for row in summary_rows if row["metric"] == "frontier"]
    solved_functions = len({(str(row["dataset"]), str(row["name"])) for row in raw_rows})
    solved_traditional = len({str(row["name"]) for row in raw_rows if int(float(row["n"])) <= 6})
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "raw_rows": len(raw_rows),
        "summary_rows": len(summary_rows),
        "frontier_rows": len(frontier_rows),
        "solved_functions": solved_functions,
        "solved_traditional_n_le_6": solved_traditional,
        "skipped_functions": len(skipped),
        "max_checkpoint_candidates": max_checkpoints,
        "budgets": [budget for budget, _fraction in BUDGETS],
        "status_counts": {"pass": len(summary_rows)},
        "needs_revision_count": 0,
        "official_ros_fully_reproduced": False,
        "exact_over_checkpoint_candidates": True,
        "table_anchor_present": "ros_lut_checkpoint_optimizer" in PAPER.read_text(encoding="utf-8", errors="replace"),
        "sources": [
            "results/raw_ros_lut_proxy_best.csv",
            "results/raw_ros_lut_garbage_proxy.csv",
            *[str(path.relative_to(THIS_DIR)) for path in DEFAULT_INTERNAL if path.exists()],
        ],
        "outputs": {
            "raw": str(RAW_OUT.relative_to(THIS_DIR)),
            "summary": str(SUMMARY_OUT.relative_to(THIS_DIR)),
            "analysis": str(ANALYSIS_OUT.relative_to(THIS_DIR)),
            "manifest": str(MANIFEST_OUT.relative_to(THIS_DIR)),
            "table": str(TABLE_OUT.relative_to(THIS_DIR)),
        },
    }
    MANIFEST_OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best", type=Path, default=BEST_ROWS)
    parser.add_argument("--garbage-raw", type=Path, default=GARBAGE_RAW)
    parser.add_argument("--raw-out", type=Path, default=RAW_OUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY_OUT)
    parser.add_argument("--analysis", type=Path, default=ANALYSIS_OUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_OUT)
    parser.add_argument("--latex-out", type=Path, default=TABLE_OUT)
    parser.add_argument("--internal", type=Path, action="append")
    parser.add_argument("--max-checkpoints", type=int, default=12)
    parser.add_argument("--rerun", action="store_true", help="recompute raw exact rows even if the raw CSV exists")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global RAW_OUT, SUMMARY_OUT, ANALYSIS_OUT, MANIFEST_OUT, TABLE_OUT
    RAW_OUT = args.raw_out
    SUMMARY_OUT = args.summary
    ANALYSIS_OUT = args.analysis
    MANIFEST_OUT = args.manifest
    TABLE_OUT = args.latex_out

    if RAW_OUT.exists() and not args.rerun:
        raw_rows = [dict(row) for row in read_csv(RAW_OUT)]
        skipped: list[dict[str, object]] = []
    else:
        best_rows = read_csv(args.best)
        garbage_rows = read_csv(args.garbage_raw)
        raw_rows, skipped = build_raw_rows(best_rows, garbage_rows, args.max_checkpoints)
        write_csv(RAW_OUT, raw_rows)
    internal_paths = tuple(args.internal) if args.internal else DEFAULT_INTERNAL
    summary_rows = build_summary_rows(raw_rows, load_internal(internal_paths))
    write_csv(SUMMARY_OUT, summary_rows)
    write_analysis(raw_rows, skipped, summary_rows, args.max_checkpoints)
    write_latex(summary_rows)
    write_manifest(raw_rows, skipped, summary_rows, args.max_checkpoints)
    print(f"wrote {len(raw_rows)} ROS-style LUT checkpoint optimizer row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
