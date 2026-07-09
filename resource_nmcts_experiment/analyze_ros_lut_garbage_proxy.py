#!/usr/bin/env python3
"""ROS-style LUT garbage-management proxy over verified ABC LUT DAGs.

The existing ROS-style baseline sweeps ABC ``if -K`` mappings and scores the
resulting LUT network with a keep-all Bennett-style estimate.  Full ROS also
contains SAT-based quantum garbage management; that official flow is not
available in this package.  This script therefore adds a bounded proxy that
keeps the same verified LUT DAGs but changes only the garbage policy:

* keep-all: compute all LUT nodes, toggle the oracle output, uncompute all;
* fanout-checkpoint: keep only multi-fanout LUT nodes as checkpoints and
  recursively recompute non-checkpoint cones;
* zero-checkpoint: recursively recompute every internal cone.

The proxy intentionally reports both resource wins and operation blow-up.  It
must not be described as official ROS SAT garbage management.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

try:
    from run_external_baselines import (
        DEFAULT_ABC_BIN,
        DEFAULT_WEIGHTS,
        BlifNode,
        Cost,
        _anf_terms_from_truth,
        _cover_local_truth,
        _logical_and_gate_cost,
        blif_lut_network_cost,
        blif_truth_table,
        bool_from_row,
        display_path,
        load_manifest,
        output_toggle_cost,
        parse_blif,
    )
    BASELINE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised in extracted payloads
    DEFAULT_ABC_BIN = Path("tmp/abc/abc")
    DEFAULT_WEIGHTS = {"t": 1.0, "cnot": 0.04, "depth": 0.015, "gates": 0.01, "ancilla": 2.0}
    BlifNode = object  # type: ignore[assignment]
    Cost = object  # type: ignore[assignment]
    BASELINE_IMPORT_ERROR = exc


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

BEST_ROWS = RESULTS / "raw_ros_lut_proxy_best.csv"
RAW = RESULTS / "raw_ros_lut_garbage_proxy.csv"
SUMMARY = RESULTS / "summary_ros_lut_garbage_proxy.csv"
ANALYSIS = RESULTS / "analysis_ros_lut_garbage_proxy.md"
MANIFEST = RESULTS / "manifest_ros_lut_garbage_proxy.json"
TABLE = TABLES / "ros_lut_garbage_proxy.tex"
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


@dataclass(frozen=True)
class LocalNode:
    inputs: tuple[str, ...]
    output: str
    cost: Cost
    helper_peak: int


@dataclass(frozen=True)
class PolicyCost:
    T: int
    CNOT: int
    gates: int
    depth: int
    explicit_ancilla: int
    peak_ancilla: int
    score: float
    expanded_compute_calls: int
    checkpoint_nodes: int


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "name",
        "n",
        "selected_k",
        "policy",
        "correct",
        "lut_nodes",
        "lut_edges",
        "max_fanin",
        "checkpoint_nodes",
        "expanded_compute_calls",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "delta_T_vs_keep_all",
        "delta_peak_ancilla_vs_keep_all",
        "delta_score_vs_keep_all",
        "source_manifest",
        "abc_script",
        "abc_binary",
        "error",
    ]
    ordered = [field for field in preferred if field in fields]
    ordered.extend(field for field in fields if field not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def score(cost: Cost | PolicyCost) -> float:
    return (
        DEFAULT_WEIGHTS["t"] * cost.T
        + DEFAULT_WEIGHTS["cnot"] * cost.CNOT
        + DEFAULT_WEIGHTS["depth"] * cost.depth
        + DEFAULT_WEIGHTS["gates"] * cost.gates
        + DEFAULT_WEIGHTS["ancilla"] * cost.peak_ancilla
    )


def local_node_cost(node: BlifNode) -> tuple[Cost, int]:
    total = Cost()
    helper_peak = 0
    truth = _cover_local_truth(len(node.inputs), node.cover)
    for term in _anf_terms_from_truth(truth, len(node.inputs)):
        base = _logical_and_gate_cost(int(term).bit_count())
        total = Cost(
            T=total.T + base.T,
            CNOT=total.CNOT + base.CNOT,
            gates=total.gates + base.gates,
            depth=total.depth + base.depth,
            explicit_ancilla=max(total.explicit_ancilla, base.explicit_ancilla),
            peak_ancilla=max(total.peak_ancilla, base.peak_ancilla),
        )
        helper_peak = max(helper_peak, base.peak_ancilla)
    return total, helper_peak


def build_local_nodes(nodes: list[BlifNode]) -> dict[str, LocalNode]:
    out: dict[str, LocalNode] = {}
    for node in nodes:
        cost, helper_peak = local_node_cost(node)
        out[node.output] = LocalNode(inputs=node.inputs, output=node.output, cost=cost, helper_peak=helper_peak)
    return out


def add_cost(a: Cost, b: Cost) -> Cost:
    return Cost(
        T=a.T + b.T,
        CNOT=a.CNOT + b.CNOT,
        gates=a.gates + b.gates,
        depth=a.depth + b.depth,
        explicit_ancilla=max(a.explicit_ancilla, b.explicit_ancilla),
        peak_ancilla=max(a.peak_ancilla, b.peak_ancilla),
    )


def recursive_compute_cost(
    output: str,
    node_by_output: dict[str, LocalNode],
    checkpoints: frozenset[str],
    memo: dict[str, tuple[Cost, int, int]],
) -> tuple[Cost, int, int]:
    """Return cost, peak live scratch lines, and expanded node calls.

    The returned state leaves only ``output`` live for non-checkpoint nodes.
    Checkpoint outputs are treated as precomputed live values.
    """
    if output not in node_by_output or output in checkpoints:
        return Cost(), 0, 0
    if output in memo:
        return memo[output]
    node = node_by_output[output]
    total = Cost()
    peak = 0
    expanded = 1
    live_children = 0
    for fanin in node.inputs:
        child_cost, child_peak, child_calls = recursive_compute_cost(fanin, node_by_output, checkpoints, memo)
        total = add_cost(total, child_cost)
        peak = max(peak, live_children + child_peak)
        expanded += child_calls
        if fanin in node_by_output and fanin not in checkpoints:
            live_children += 1
    total = add_cost(total, node.cost)
    peak = max(peak, live_children + 1 + node.helper_peak)
    # Non-checkpoint children are uncomputed after this node has been computed.
    for fanin in reversed(node.inputs):
        if fanin not in node_by_output or fanin in checkpoints:
            continue
        child_cost, child_peak, child_calls = recursive_compute_cost(fanin, node_by_output, checkpoints, memo)
        total = add_cost(total, child_cost)
        peak = max(peak, live_children + child_peak)
        expanded += child_calls
        live_children -= 1
    memo[output] = (total, peak, expanded)
    return memo[output]


def fanout_counts(nodes: list[BlifNode]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for node in nodes:
        for fanin in node.inputs:
            counts[fanin] += 1
    return counts


def checkpoint_setup_cost(
    nodes: list[BlifNode],
    node_by_output: dict[str, LocalNode],
    checkpoints: frozenset[str],
) -> tuple[Cost, int, int]:
    if not checkpoints:
        return Cost(), 0, 0
    total = Cost()
    live_checkpoints: set[str] = set()
    peak = 0
    calls = 0
    for node in nodes:
        if node.output not in checkpoints:
            continue
        subtotal, subpeak, subcalls = recursive_compute_cost(node.output, node_by_output, frozenset(live_checkpoints), {})
        total = add_cost(total, subtotal)
        peak = max(peak, len(live_checkpoints) + subpeak)
        live_checkpoints.add(node.output)
        peak = max(peak, len(live_checkpoints))
        calls += subcalls
    return total, peak, calls


def policy_cost(
    policy: str,
    nodes: list[BlifNode],
    output: str,
    bf_n: int,
    output_cnot: int,
    output_gate: int,
) -> PolicyCost:
    node_by_output = build_local_nodes(nodes)
    if policy == "keep_all":
        raise ValueError("keep_all is handled by the existing Bennett estimator")
    if output not in node_by_output:
        return PolicyCost(
            T=0,
            CNOT=output_cnot,
            gates=output_gate,
            depth=output_gate,
            explicit_ancilla=0,
            peak_ancilla=0,
            score=0.0,
            expanded_compute_calls=0,
            checkpoint_nodes=0,
        )
    fanout = fanout_counts(nodes)
    if policy == "zero_checkpoint":
        checkpoints = frozenset()
    elif policy == "fanout_checkpoint":
        checkpoints = frozenset(node.output for node in nodes if fanout[node.output] > 1 and node.output != output)
    else:
        raise ValueError(f"unknown policy: {policy}")
    setup, setup_peak, setup_calls = checkpoint_setup_cost(nodes, node_by_output, checkpoints)
    cone, cone_peak, cone_calls = recursive_compute_cost(output, node_by_output, checkpoints, {})
    total = add_cost(setup, cone)
    # Toggle the oracle output, then uncompute the cone and checkpoint setup.
    total = Cost(
        T=2 * total.T,
        CNOT=2 * total.CNOT + output_cnot,
        gates=2 * total.gates + output_gate,
        depth=2 * total.depth + output_gate,
        explicit_ancilla=0,
        peak_ancilla=0,
    )
    checkpoint_count = len(checkpoints)
    peak = max(setup_peak, checkpoint_count + cone_peak)
    result = PolicyCost(
        T=total.T,
        CNOT=total.CNOT,
        gates=total.gates,
        depth=total.depth,
        explicit_ancilla=checkpoint_count + (1 if output in node_by_output else 0),
        peak_ancilla=peak,
        score=0.0,
        expanded_compute_calls=2 * (setup_calls + cone_calls),
        checkpoint_nodes=checkpoint_count,
    )
    return PolicyCost(
        T=result.T,
        CNOT=result.CNOT,
        gates=result.gates,
        depth=result.depth,
        explicit_ancilla=result.explicit_ancilla,
        peak_ancilla=result.peak_ancilla,
        score=score(result),
        expanded_compute_calls=result.expanded_compute_calls,
        checkpoint_nodes=result.checkpoint_nodes,
    )


def load_manifest_index(source_manifest: str) -> dict[str, dict[str, str]]:
    manifest_dir = (THIS_DIR / source_manifest).resolve()
    rows = load_manifest(manifest_dir / "manifest.csv")
    return {row["name"]: row for row in rows}


def render_lut(row: dict[str, str], selected_k: int, abc_bin: Path, timeout: float) -> tuple[list[str], str, list[BlifNode], bool]:
    bf = bool_from_row(row)
    rel_blif = row.get("blif")
    if not rel_blif:
        raise ValueError("manifest row has no BLIF path")
    blif = (Path(row["_manifest_abs_dir"]) / rel_blif).resolve()
    with tempfile.TemporaryDirectory(prefix="abc_lut_garbage_") as tmp:
        opt_blif = Path(tmp) / f"{row['name']}.k{selected_k}.blif"
        command = f"read_blif {blif}; strash; if -K {selected_k}; write_blif {opt_blif}; print_stats"
        proc = subprocess.run(
            [str(abc_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"ABC-LUT failed with code {proc.returncode}: {combined[-1000:]}")
        inputs, output, nodes = parse_blif(opt_blif)
        correct = len(inputs) == bf.n and blif_truth_table(inputs, output, nodes, bf.n) == bf.truth_table
    return inputs, output, nodes, correct


def row_for_cost(
    base: dict[str, str],
    policy: str,
    cost_obj: Cost | PolicyCost,
    keep_all: Cost,
    correct: bool,
    lut_nodes: int,
    lut_edges: int,
    max_fanin: int,
    checkpoint_nodes: int,
    expanded_calls: int,
) -> dict[str, object]:
    cost_score = score(cost_obj) if isinstance(cost_obj, Cost) else cost_obj.score
    return {
        "dataset": base["dataset"],
        "name": base["name"],
        "n": base["n"],
        "selected_k": base["selected_k"],
        "policy": policy,
        "correct": correct,
        "lut_nodes": lut_nodes,
        "lut_edges": lut_edges,
        "max_fanin": max_fanin,
        "checkpoint_nodes": checkpoint_nodes,
        "expanded_compute_calls": expanded_calls,
        "T": cost_obj.T,
        "CNOT": cost_obj.CNOT,
        "depth": cost_obj.depth,
        "gates": cost_obj.gates,
        "explicit_ancilla": cost_obj.explicit_ancilla,
        "peak_ancilla": cost_obj.peak_ancilla,
        "n_qubits": int(base["n"]) + 1 + cost_obj.explicit_ancilla,
        "score": f"{cost_score:.6f}",
        "delta_T_vs_keep_all": cost_obj.T - keep_all.T,
        "delta_peak_ancilla_vs_keep_all": cost_obj.peak_ancilla - keep_all.peak_ancilla,
        "delta_score_vs_keep_all": f"{cost_score - score(keep_all):.6f}",
        "source_manifest": base["source_manifest"],
        "abc_script": f"strash; if -K {base['selected_k']}",
        "abc_binary": base.get("abc_binary", display_path(DEFAULT_ABC_BIN)),
        "error": "",
    }


def evaluate_best_row(best: dict[str, str], abc_bin_value: str, timeout: float) -> list[dict[str, object]]:
    abc_bin = Path(abc_bin_value).resolve()
    row_bundle: list[dict[str, object]] = []
    try:
        source = load_manifest_index(best["source_manifest"])[best["name"]]
        best = dict(best)
        best["abc_binary"] = display_path(abc_bin)
        bf = bool_from_row(source)
        selected_k = int(best["selected_k"])
        inputs, output, nodes, correct = render_lut(source, selected_k, abc_bin, timeout)
        if len(inputs) != bf.n:
            raise RuntimeError(f"input count mismatch: {len(inputs)} != {bf.n}")
        output_cnot, output_gate = output_toggle_cost(bf)
        keep = blif_lut_network_cost(inputs, output, nodes, bf)
        node_outputs = {node.output for node in nodes}
        lut_edges = sum(1 for node in nodes for fanin in node.inputs if fanin in node_outputs)
        max_fanin = max((len(node.inputs) for node in nodes), default=0)
        row_bundle.append(
            row_for_cost(
                best,
                "keep_all_bennett",
                keep,
                keep,
                correct,
                len(nodes),
                lut_edges,
                max_fanin,
                len(nodes),
                2 * len(nodes),
            )
        )
        for policy in ("fanout_checkpoint", "zero_checkpoint"):
            pcost = policy_cost(policy, nodes, output, bf.n, output_cnot, output_gate)
            row_bundle.append(
                row_for_cost(
                    best,
                    policy,
                    pcost,
                    keep,
                    correct,
                    len(nodes),
                    lut_edges,
                    max_fanin,
                    pcost.checkpoint_nodes,
                    pcost.expanded_compute_calls,
                )
            )
        return row_bundle
    except Exception as exc:  # pragma: no cover - row-level audit
        return [
            {
                "dataset": best.get("dataset", ""),
                "name": best.get("name", ""),
                "n": best.get("n", ""),
                "selected_k": best.get("selected_k", ""),
                "policy": "error",
                "correct": "",
                "source_manifest": best.get("source_manifest", ""),
                "abc_binary": str(abc_bin),
                "error": repr(exc),
            }
        ]


def build_raw_rows(args: argparse.Namespace) -> list[dict[str, object]]:
    best_rows = load_csv(args.best)
    if args.limit:
        best_rows = best_rows[: args.limit]
    raw_rows: list[dict[str, object]] = []
    workers = max(1, int(args.workers))
    if workers == 1:
        for best in best_rows:
            raw_rows.extend(evaluate_best_row(best, str(args.abc_bin), args.timeout))
        return raw_rows
    bundles: dict[int, list[dict[str, object]]] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(evaluate_best_row, best, str(args.abc_bin), args.timeout): idx
            for idx, best in enumerate(best_rows)
        }
        for future in as_completed(futures):
            bundles[futures[future]] = future.result()
    for idx in range(len(best_rows)):
        raw_rows.extend(bundles[idx])
    return raw_rows


def policy_rows(rows: list[dict[str, object]], policy: str) -> list[dict[str, object]]:
    return [row for row in rows if row.get("policy") == policy and not row.get("error")]


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    keep_by_key = {
        (row["dataset"], row["name"]): row
        for row in rows
        if row.get("policy") == "keep_all_bennett" and not row.get("error")
    }
    out: list[dict[str, object]] = []
    for policy in ("keep_all_bennett", "fanout_checkpoint", "zero_checkpoint"):
        items = policy_rows(rows, policy)
        if not items:
            continue
        wins_peak = losses_peak = ties_peak = 0
        wins_score = losses_score = ties_score = 0
        deltas_peak: list[float] = []
        deltas_t: list[float] = []
        deltas_score: list[float] = []
        for row in items:
            keep = keep_by_key[(row["dataset"], row["name"])]
            peak_delta = float(row["peak_ancilla"]) - float(keep["peak_ancilla"])
            t_delta = float(row["T"]) - float(keep["T"])
            score_delta = float(row["score"]) - float(keep["score"])
            deltas_peak.append(peak_delta)
            deltas_t.append(t_delta)
            deltas_score.append(score_delta)
            if peak_delta < 0:
                wins_peak += 1
            elif peak_delta > 0:
                losses_peak += 1
            else:
                ties_peak += 1
            if score_delta < 0:
                wins_score += 1
            elif score_delta > 0:
                losses_score += 1
            else:
                ties_score += 1
        out.append(
            {
                "policy": policy,
                "rows": len(items),
                "correct_rows": sum(str(row.get("correct")) == "True" for row in items),
                "mean_T": statistics.mean(float(row["T"]) for row in items),
                "mean_log10_T_plus_1": statistics.mean(math.log10(float(row["T"]) + 1.0) for row in items),
                "mean_peak_ancilla": statistics.mean(float(row["peak_ancilla"]) for row in items),
                "mean_score": statistics.mean(float(row["score"]) for row in items),
                "mean_log10_score_plus_1": statistics.mean(math.log10(float(row["score"]) + 1.0) for row in items),
                "peak_vs_keep_all_wins": wins_peak,
                "peak_vs_keep_all_ties": ties_peak,
                "peak_vs_keep_all_losses": losses_peak,
                "score_vs_keep_all_wins": wins_score,
                "score_vs_keep_all_ties": ties_score,
                "score_vs_keep_all_losses": losses_score,
                "mean_delta_T_vs_keep_all": statistics.mean(deltas_t),
                "mean_delta_peak_ancilla_vs_keep_all": statistics.mean(deltas_peak),
                "mean_delta_score_vs_keep_all": statistics.mean(deltas_score),
                "mean_expanded_compute_calls": statistics.mean(float(row["expanded_compute_calls"]) for row in items),
                "mean_checkpoint_nodes": statistics.mean(float(row["checkpoint_nodes"]) for row in items),
            }
        )
    return out


def fmt_pct(value: float) -> str:
    return f"{100.0 * value:.2f}\\%"


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    write_csv(path, rows)


def write_analysis(summary_rows: list[dict[str, object]], raw_rows: list[dict[str, object]]) -> None:
    counts = Counter("pass" if not row.get("error") and str(row.get("correct")) == "True" else "needs revision" for row in raw_rows)
    keep = next(row for row in summary_rows if row["policy"] == "keep_all_bennett")
    lines = [
        "# ROS-Style LUT Garbage Proxy",
        "",
        "This analysis re-runs the verified best-K ABC LUT mappings and compares",
        "three reversible garbage policies over the same LUT DAG. It is a",
        "resource-pressure proxy, not official ROS SAT garbage management.",
        "",
        "## Status counts",
        "",
    ]
    lines.extend(f"- {status}: {count}" for status, count in sorted(counts.items()))
    lines.extend(
        [
            "",
            "## Policy summary",
            "",
            "| policy | rows | correct | mean log10(T+1) | mean peak ancilla | mean log10(score+1) | peak vs keep-all | score vs keep-all |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in summary_rows:
        lines.append(
            "| {policy} | {rows} | {correct_rows} | {mean_log10_T_plus_1:.2f} | {mean_peak_ancilla:.2f} | {mean_log10_score_plus_1:.2f} | "
            "{peak_vs_keep_all_wins}/{peak_vs_keep_all_ties}/{peak_vs_keep_all_losses} | "
            "{score_vs_keep_all_wins}/{score_vs_keep_all_ties}/{score_vs_keep_all_losses} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Fanout-checkpoint and zero-checkpoint rows measure the qubit/operation trade-off that a garbage-management stage is meant to expose.",
            "- A lower peak-ancilla result is useful only as a line-pressure sensitivity result when its T-count and score increase are reported alongside it.",
            "- These rows strengthen the ROS-facing comparison boundary but still exclude claims about the official ROS SAT algorithm.",
        ]
    )
    ANALYSIS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latex_lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Policy & Rows & $\log_{10}(T+1)$ & Peak ancilla & $\log_{10}(\mathrm{score}+1)$ \\",
        r"\midrule",
    ]
    for row in summary_rows:
        policy_name = str(row["policy"]).replace("_", r"\_")
        latex_lines.append(
            f"{policy_name} & {int(row['rows'])} & "
            f"{float(row['mean_log10_T_plus_1']):.2f} & {float(row['mean_peak_ancilla']):.1f} & "
            f"{float(row['mean_log10_score_plus_1']):.2f} \\\\"
        )
    latex_lines.extend([r"\bottomrule", r"\end{tabular}"])
    TABLE.write_text("\n".join(latex_lines) + "\n", encoding="utf-8")


def write_manifest(summary_rows: list[dict[str, object]], raw_rows: list[dict[str, object]]) -> None:
    counts = Counter("pass" if not row.get("error") and str(row.get("correct")) == "True" else "needs revision" for row in raw_rows)
    data = {
        "script": Path(__file__).name,
        "raw_rows": len(raw_rows),
        "functions": len({(row.get("dataset"), row.get("name")) for row in raw_rows if row.get("policy") != "error"}),
        "policies": sorted({str(row.get("policy")) for row in raw_rows if row.get("policy") != "error"}),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "summary_rows": len(summary_rows),
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "ros_lut_garbage_proxy" in PAPER.read_text(encoding="utf-8", errors="replace"),
        "official_ros_fully_reproduced": False,
        "outputs": {
            "raw": str(RAW.relative_to(THIS_DIR)),
            "summary": str(SUMMARY.relative_to(THIS_DIR)),
            "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
            "manifest": str(MANIFEST.relative_to(THIS_DIR)),
            "table": str(TABLE.relative_to(THIS_DIR)),
        },
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best", type=Path, default=BEST_ROWS)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--abc-bin", type=Path, default=DEFAULT_ABC_BIN)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="debug limit over best-K rows")
    parser.add_argument("--run-proxy", action="store_true", help="rerun ABC and recompute raw policy rows instead of reusing the existing raw CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_proxy or not args.raw.exists():
        if BASELINE_IMPORT_ERROR is not None:
            raise SystemExit(f"run_external_baselines import failed: {BASELINE_IMPORT_ERROR!r}")
        raw_rows = build_raw_rows(args)
        write_csv(RAW, raw_rows)
    else:
        raw_rows = load_csv(args.raw)
    summary_rows = summarize(raw_rows)
    write_summary(SUMMARY, summary_rows)
    write_analysis(summary_rows, raw_rows)
    write_manifest(summary_rows, raw_rows)
    print(f"wrote {len(raw_rows)} ROS-style LUT garbage proxy row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
