#!/usr/bin/env python3
"""Run RevKit oracle_synth high-dimensional probes with hard per-row timeouts.

The validated RevKit API baseline in ``run_revkit_baseline.py`` covers the
``n <= 6`` traditional truth-table suite.  Directly calling RevKit on larger
truth tables can hang for a long time, so this script runs each row in a
disposable subprocess and kills it after a configured wall-time cutoff.

The output is a scalability-boundary audit, not a paired performance benchmark:
timed-out rows have no circuit metrics and must not be averaged as if RevKit
had returned a circuit.
"""
from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import queue
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from run_revkit_baseline import RZ_PROXY_WEIGHTS, RevKitTask, load_csv, synthesize_task, usable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def load_probe_tasks(path: Path, min_n: int, max_n: int, limit: int | None, timeout: float) -> list[RevKitTask]:
    rows = load_csv(path)
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        if row["name"] in by_name:
            continue
        if not row.get("truth_table_hex"):
            continue
        n = int(row["n"])
        if n < min_n or n > max_n:
            continue
        by_name[row["name"]] = row
    tasks = [
        RevKitTask(
            name=row["name"],
            n=int(row["n"]),
            truth_table_hex=row["truth_table_hex"],
            timeout=timeout,
        )
        for row in sorted(by_name.values(), key=lambda item: (int(item["n"]), item["name"]))
    ]
    if limit is not None:
        return tasks[:limit]
    return tasks


def timeout_row(task: RevKitTask, elapsed: float, timeout: float, message: str) -> dict[str, object]:
    return {
        "name": task.name,
        "n": task.n,
        "method": "external_revkit_oracle_synth_timeout_probe",
        "T": "",
        "CNOT": "",
        "depth": "",
        "gates": "",
        "explicit_ancilla": "",
        "peak_ancilla": "",
        "n_qubits": "",
        "score": "",
        "score_lower_bound": "",
        **{f"score_rz{weight:g}": "" for weight in RZ_PROXY_WEIGHTS},
        "time_s": elapsed,
        "timeout_s": timeout,
        "revkit_num_gates": "",
        "revkit_num_qubits": "",
        "rz_total": "",
        "rz_clifford": "",
        "rz_t_like": "",
        "rz_non_clifford": "",
        "rz_max_denominator": "",
        "phase_ops": "",
        "ct_supported": "",
        "correct": "",
        "skipped": "",
        "error": message,
        "truth_table_hex": task.truth_table_hex,
    }


def _child_synthesize(task: RevKitTask, out_queue: mp.Queue) -> None:
    out_queue.put(synthesize_task(task))


def run_isolated(task: RevKitTask, timeout: float, kill_grace: float = 2.0) -> dict[str, object]:
    ctx = mp.get_context("spawn")
    out_queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_child_synthesize, args=(task, out_queue))
    started = time.time()
    proc.start()
    proc.join(timeout)
    elapsed = time.time() - started
    if proc.is_alive():
        proc.terminate()
        proc.join(kill_grace)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return timeout_row(task, time.time() - started, timeout, f"ProcessTimeout({timeout:g}s)")
    try:
        row = out_queue.get_nowait()
    except queue.Empty:
        return timeout_row(task, elapsed, timeout, f"NoResult(exitcode={proc.exitcode})")
    row["method"] = "external_revkit_oracle_synth_timeout_probe"
    row["timeout_s"] = timeout
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preferred = [
        "name",
        "n",
        "method",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "score_lower_bound",
        *[f"score_rz{weight:g}" for weight in RZ_PROXY_WEIGHTS],
        "time_s",
        "timeout_s",
        "revkit_num_gates",
        "revkit_num_qubits",
        "rz_total",
        "rz_clifford",
        "rz_t_like",
        "rz_non_clifford",
        "rz_max_denominator",
        "phase_ops",
        "ct_supported",
        "correct",
        "skipped",
        "error",
        "truth_table_hex",
    ]
    fieldnames = sorted({key for row in rows for key in row})
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_n: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        by_n.setdefault(int(row["n"]), []).append(row)
    summary: list[dict[str, object]] = []
    for n, subset in sorted(by_n.items()):
        timeouts = [row for row in subset if str(row.get("error", "")).startswith("ProcessTimeout")]
        errors = [row for row in subset if row.get("error") and row not in timeouts]
        usable_rows = [row for row in subset if usable(row)]
        times = [float(row.get("time_s") or 0.0) for row in subset]
        summary.append(
            {
                "n": n,
                "items": len(subset),
                "usable": len(usable_rows),
                "timeouts": len(timeouts),
                "other_errors": len(errors),
                "median_time_s": statistics.median(times) if times else 0.0,
                "max_time_s": max(times, default=0.0),
            }
        )
    return summary


def by_name_method(rows: list[dict[str, object]]) -> dict[str, dict[str, dict[str, object]]]:
    out: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def compare_values(target: float, baseline: float) -> str:
    if target < baseline - 1e-9:
        return "win"
    if target > baseline + 1e-9:
        return "loss"
    return "tie"


def rel(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0)


def returned_row_comparisons(
    rows: list[dict[str, object]],
    internal_rows: list[dict[str, object]],
    target_method: str,
) -> list[dict[str, object]]:
    internal = by_name_method(internal_rows)
    out: list[dict[str, object]] = []
    for row in rows:
        if not usable(row):
            continue
        target = internal.get(str(row["name"]), {}).get(target_method)
        if target is None:
            continue
        target_score = float(target["score"])
        lower_score = float(row["score"])
        rz1_score = float(row.get("score_rz1") or lower_score)
        out.append(
            {
                "name": row["name"],
                "n": row["n"],
                "target_method": target_method,
                "target_score": target_score,
                "target_T": float(target["T"]),
                "target_CNOT": float(target["CNOT"]),
                "revkit_lower_score": lower_score,
                "revkit_T": float(row["T"]),
                "revkit_CNOT": float(row["CNOT"]),
                "revkit_depth": float(row["depth"]),
                "revkit_non_clifford_rz": float(row.get("rz_non_clifford") or 0.0),
                "revkit_score_rz1": rz1_score,
                "lower_result": compare_values(target_score, lower_score),
                "lower_relative": rel(target_score, lower_score),
                "rz1_result": compare_values(target_score, rz1_score),
                "rz1_relative": rel(target_score, rz1_score),
            }
        )
    return out


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["n", "items", "usable", "timeouts", "other_errors", "median_time_s", "max_time_s"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(
    path: Path,
    summary: list[dict[str, object]],
    rows: list[dict[str, object]],
    comparisons: list[dict[str, object]],
    args: argparse.Namespace,
) -> None:
    usable_rows = [row for row in rows if usable(row)]
    timeout_rows = [row for row in rows if str(row.get("error", "")).startswith("ProcessTimeout")]
    other_errors = [row for row in rows if row.get("error") and row not in timeout_rows]
    lines = [
        "# RevKit High-dimensional Timeout Probe",
        "",
        f"Input: `{args.input}`",
        f"n range: {args.min_n}..{args.max_n}; requested limit: {args.limit}; per-row timeout: {args.timeout:g}s; workers: {args.workers}.",
        "",
        "Each RevKit `oracle_synth` call was executed in a disposable subprocess.",
        "Rows that exceeded the cutoff were terminated and recorded as timeout rows.",
        "",
        "## Summary",
        "",
        f"- rows attempted: {len(rows)}",
        f"- usable RevKit circuits returned: {len(usable_rows)}",
        f"- timed out rows: {len(timeout_rows)}",
        f"- other errors: {len(other_errors)}",
        "",
        "| n | items | usable | timeouts | other errors | median time (s) | max time (s) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['n']} | {row['items']} | {row['usable']} | {row['timeouts']} | "
            f"{row['other_errors']} | {float(row['median_time_s']):.2f} | {float(row['max_time_s']):.2f} |"
        )
    if comparisons:
        lines.extend(
            [
                "",
                f"## Returned-row Comparison Against `{args.target_method}`",
                "",
                "Only rows for which RevKit returned a circuit are included here.",
                "`lower-bound` is the raw RevKit phase-netlist score; `score+1/Rz` adds one score unit per non-Clifford Rz rotation.",
                "",
                "| name | target score | RevKit lower-bound score | non-Clifford Rz | lower-bound result | RevKit score+1/Rz | score+1/Rz result |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in comparisons:
            lines.append(
                f"| {row['name']} | {float(row['target_score']):.2f} | {float(row['revkit_lower_score']):.2f} | "
                f"{int(float(row['revkit_non_clifford_rz']))} | {row['lower_result']} ({float(row['lower_relative']):+.2%}) | "
                f"{float(row['revkit_score_rz1']):.2f} | {row['rz1_result']} ({float(row['rz1_relative']):+.2%}) |"
            )
    if other_errors:
        lines.extend(["", "## Other Errors", ""])
        for row in other_errors[:20]:
            lines.append(f"- `{row['name']}`: `{row['error']}`")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This is an engineering scalability and adapter-boundary probe, not a paired resource benchmark.",
            "- Timed-out rows have no RevKit circuit metrics and are not averaged against Resource-NMCTS.",
            "- Returned high-dimensional rows are still Rz-phase lower-bound netlists when `rz_non_clifford > 0`; rotation-aware scores are sensitivity checks, not emitted Clifford+T sequences.",
            "- The result supports restricting the current formal RevKit API comparison to the validated `n <= 6` truth-table suite.",
            "- Future RevKit high-dimensional comparison would need either a faster RevKit configuration, a different RevKit/CirKit flow, or smaller/highly structured functions that return within the same cutoff.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{rrrrrr}\n")
        f.write("\\toprule\n")
        f.write("$n$ & Items & Usable & Timeouts & Other errors & Median time (s) \\\\\n")
        f.write("\\midrule\n")
        for row in summary:
            f.write(
                f"{row['n']} & {row['items']} & {row['usable']} & {row['timeouts']} & "
                f"{row['other_errors']} & {float(row['median_time_s']):.2f} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def run_tasks(tasks: list[RevKitTask], timeout: float, workers: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if workers <= 1:
        for i, task in enumerate(tasks, 1):
            row = run_isolated(task, timeout)
            rows.append(row)
            print(f"{i}/{len(tasks)} {task.name} {row.get('error') or 'ok'}", flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(run_isolated, task, timeout): task for task in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            task = futures[fut]
            row = fut.result()
            rows.append(row)
            print(f"{i}/{len(tasks)} {task.name} {row.get('error') or 'ok'}", flush=True)
    rows.sort(key=lambda row: (int(row["n"]), str(row["name"])))
    return rows


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_highdim_resource.csv")
    parser.add_argument("--min-n", type=int, default=14)
    parser.add_argument("--max-n", type=int, default=14)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--target-method", default="and_resource_nmcts")
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_revkit_highdim_timeout_probe.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_revkit_highdim_timeout_probe.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_revkit_highdim_timeout_probe.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "revkit_highdim_timeout_probe.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_revkit_highdim_timeout_probe.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    tasks = load_probe_tasks(args.input, args.min_n, args.max_n, args.limit, args.timeout)
    started = time.time()
    rows = run_tasks(tasks, args.timeout, max(1, args.workers))
    summary = summarize(rows)
    comparisons = returned_row_comparisons(rows, load_csv(args.input), args.target_method)
    write_csv(args.raw_out, rows)
    write_summary_csv(args.summary, summary)
    write_analysis(args.analysis, summary, rows, comparisons, args)
    write_latex(args.latex_out, summary)
    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.run_manifest.write_text(
        json.dumps(
            {
                "input": str(args.input),
                "min_n": args.min_n,
                "max_n": args.max_n,
                "limit": args.limit,
                "timeout_s": args.timeout,
                "workers": args.workers,
                "target_method": args.target_method,
                "rows": len(rows),
                "usable_rows": sum(1 for row in rows if usable(row)),
                "timeout_rows": sum(1 for row in rows if str(row.get("error", "")).startswith("ProcessTimeout")),
                "returned_comparison_rows": len(comparisons),
                "elapsed_s": time.time() - started,
                "method": "external_revkit_oracle_synth_timeout_probe",
                "claim_boundary": "High-dimensional RevKit Python API subprocess-timeout probe; timed-out rows have no circuit metrics.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"elapsed {time.time() - started:.2f}s")
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.run_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
