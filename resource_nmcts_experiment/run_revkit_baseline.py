#!/usr/bin/env python3
"""Run a RevKit oracle_synth baseline on complete truth-table benchmarks.

This is the first real RevKit-backed baseline in this project.  It deliberately
starts with complete truth-table rows (n <= 6 in the traditional benchmark),
because RevKit's Python API accepts truth tables directly and returns a
Clifford+T-style netlist.

The resource accounting is a logic-level netlist proxy:

- T counts explicit T/Tdg gates and odd multiples of Rz(pi/4).
- CNOT counts CX gates.
- depth is a qubit-conflict parallel layer count over the returned netlist.
- explicit/peak ancilla is num_qubits - n - 1 when RevKit allocates more than
  the input plus oracle target line.

This is not hardware mapping and not the legacy RevKit/CirKit command-line
flow.  It is, however, a local RevKit API synthesis baseline rather than an
ABC-only proxy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from run_external_baselines import DEFAULT_WEIGHTS


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

METRICS = ["T", "CNOT", "depth", "gates", "peak_ancilla", "score"]
DEFAULT_TARGETS = [
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_polarity_archive",
    "and_cube_beam",
    "and_esop_milp",
    "sshr_h",
    "direct_anf",
]


@dataclass(frozen=True)
class RevKitTask:
    name: str
    n: int
    truth_table_hex: str
    timeout: float


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_truth_tasks(path: Path, max_n: int | None, timeout: float) -> list[RevKitTask]:
    rows = load_csv(path)
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("skipped") or row.get("error"):
            continue
        if row["name"] in by_name:
            continue
        n = int(row["n"])
        if max_n is not None and n > max_n:
            continue
        if not row.get("truth_table_hex"):
            continue
        by_name[row["name"]] = row
    return [
        RevKitTask(
            name=row["name"],
            n=int(row["n"]),
            truth_table_hex=row["truth_table_hex"],
            timeout=timeout,
        )
        for row in sorted(by_name.values(), key=lambda item: (int(item["n"]), item["name"]))
    ]


def score(row: dict[str, object]) -> float:
    return (
        DEFAULT_WEIGHTS["t"] * float(row["T"])
        + DEFAULT_WEIGHTS["cnot"] * float(row["CNOT"])
        + DEFAULT_WEIGHTS["depth"] * float(row["depth"])
        + DEFAULT_WEIGHTS["gates"] * float(row["gates"])
        + DEFAULT_WEIGHTS["ancilla"] * float(row["peak_ancilla"])
    )


def gate_kind(gate) -> str:
    return str(gate.kind).split(".")[-1]


def gate_lines(gate) -> set[int]:
    lines = {int(target) for target in gate.targets}
    lines.update(int(control.index) for control in gate.controls)
    return lines


def is_t_angle(angle: float) -> bool:
    # T/Tdg are +/- pi/4 modulo pi/2.  Numerical angles come from floats.
    unit = math.pi / 4.0
    k = round(angle / unit)
    if abs(angle - k * unit) > 1e-5:
        return False
    return abs(k) % 2 == 1


def estimate_netlist(circuit, n: int) -> dict[str, int]:
    t_count = 0
    cnot = 0
    gate_count = 0
    line_ready: dict[int, int] = {}
    max_depth = 0
    for gate in circuit.gates:
        kind = gate_kind(gate)
        lines = gate_lines(gate)
        if kind in {"t", "t_dagger"}:
            t_count += 1
        elif kind == "rotation_z" and is_t_angle(float(gate.angle)):
            t_count += 1
        if kind == "cx":
            cnot += 1
        elif kind == "swap":
            cnot += 3
        elif kind in {"mcx", "mcz"}:
            # RevKit oracle_synth normally emits Clifford+T gates, but keep a
            # conservative fallback if a multi-control gate appears.
            controls = len(gate.controls)
            cnot += max(1, 6 * max(0, controls - 1) + 1)
            t_count += 4 * max(0, controls - 1)
        gate_count += 1
        if not lines:
            max_depth += 1
            continue
        layer = 1 + max((line_ready.get(line, 0) for line in lines), default=0)
        for line in lines:
            line_ready[line] = layer
        max_depth = max(max_depth, layer)
    num_qubits = int(circuit.num_qubits)
    explicit_ancilla = max(0, num_qubits - n - 1)
    return {
        "T": t_count,
        "CNOT": cnot,
        "depth": max_depth,
        "gates": gate_count,
        "explicit_ancilla": explicit_ancilla,
        "peak_ancilla": explicit_ancilla,
        "n_qubits": num_qubits,
    }


def synthesize_task(task: RevKitTask) -> dict[str, object]:
    started = time.time()
    base = {
        "name": task.name,
        "n": task.n,
        "truth_table_hex": task.truth_table_hex,
        "method": "external_revkit_oracle_synth",
        "correct": "RevKit oracle_synth accepted truth table",
        "skipped": "",
        "error": "",
    }
    try:
        from revkit import oracle_synth, truth_table

        width = 1 << task.n
        hex_digits = (width + 3) // 4
        tt_hex = task.truth_table_hex.strip().removeprefix("0x").zfill(hex_digits)
        function = truth_table.from_hex(tt_hex)
        inferred = int(function.num_vars)
        if inferred != task.n:
            raise ValueError(f"RevKit inferred {inferred} variables for n={task.n} hex={tt_hex}")
        circuit = oracle_synth(function)
        out: dict[str, object] = {**base, **estimate_netlist(circuit, task.n)}
        out["score"] = score(out)
        out["time_s"] = time.time() - started
        out["revkit_num_gates"] = int(circuit.num_gates)
        out["revkit_num_qubits"] = int(circuit.num_qubits)
        return out
    except Exception as exc:  # pragma: no cover - row-level reporting
        return {
            **base,
            "T": "",
            "CNOT": "",
            "depth": "",
            "gates": "",
            "explicit_ancilla": "",
            "peak_ancilla": "",
            "n_qubits": "",
            "score": "",
            "time_s": time.time() - started,
            "revkit_num_gates": "",
            "revkit_num_qubits": "",
            "error": repr(exc),
        }


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
        "time_s",
        "revkit_num_gates",
        "revkit_num_qubits",
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


def usable(row: dict[str, object]) -> bool:
    return not row.get("error") and not row.get("skipped") and row.get("score") not in {"", None}


def by_name_method(rows: Iterable[dict[str, object]]) -> dict[str, dict[str, dict[str, object]]]:
    out: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def rel(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare(joined: dict[str, dict[str, dict[str, object]]], target: str, baseline: str, metric: str) -> dict[str, object] | None:
    wins = losses = ties = 0
    relatives: list[float] = []
    by_n: dict[str, int] = {}
    for methods in joined.values():
        if target not in methods or baseline not in methods:
            continue
        try:
            new = float(methods[target][metric])
            old = float(methods[baseline][metric])
        except (KeyError, TypeError, ValueError):
            continue
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(new, old))
        n = str(methods[target].get("n", "?"))
        by_n[n] = by_n.get(n, 0) + 1
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
        "by_n": ";".join(f"{n}:{count}" for n, count in sorted(by_n.items())),
    }


def format_pct(value: float) -> str:
    return f"{value:+.2%}"


def format_latex_pct(value: float) -> str:
    return format_pct(value).replace("%", r"\%")


def write_analysis(
    analysis: Path,
    summary: Path,
    latex_out: Path,
    revkit_rows: list[dict[str, object]],
    internal_rows: list[dict[str, str]],
    targets: list[str],
) -> None:
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(revkit_rows).items():
        joined.setdefault(name, {}).update(methods)

    comparisons: list[dict[str, object]] = []
    for target in targets:
        for metric in METRICS:
            row = compare(joined, target, "external_revkit_oracle_synth", metric)
            if row is not None:
                comparisons.append(row)

    summary.parent.mkdir(parents=True, exist_ok=True)
    with summary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["target", "baseline", "metric", "items", "wins", "losses", "ties", "mean_relative", "by_n"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(comparisons)

    usable_rows = [row for row in revkit_rows if usable(row)]
    lines = [
        "# RevKit Oracle Synth Baseline",
        "",
        "This run uses the installed RevKit Python API (`oracle_synth`) on",
        "complete truth-table benchmark rows and estimates the returned",
        "Clifford+T netlist at the logic layer.  It is a real RevKit API",
        "baseline, not the ABC-only ROS-style LUT proxy, but it is still not",
        "hardware mapping and not the legacy CirKit CLI flow.",
        "",
        f"Rows: {len(revkit_rows)}; usable: {len(usable_rows)}.",
        "",
        "## Pairwise Comparisons",
        "",
        "| target | baseline | metric | items | W/L/T | mean relative |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in comparisons:
        lines.append(
            f"| {row['target']} | {row['baseline']} | {row['metric']} | {row['items']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | {format_pct(float(row['mean_relative']))} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Correctness is delegated to RevKit `oracle_synth` accepting the exact truth table.",
            "- The resource model counts Clifford+T netlist gates returned by RevKit; it is not the same MCT-level accounting used by the internal ANF/FPRM emitters.",
            "- These results should be presented as an external RevKit API baseline, not as a claim about hardware mapping.",
        ]
    )
    analysis.write_text("\n".join(lines) + "\n", encoding="utf-8")

    latex_out.parent.mkdir(parents=True, exist_ok=True)
    focus = [
        ("and_resource_nmcts", "score"),
        ("and_pareto_resource_nmcts", "score"),
        ("and_fprm_polarity_archive", "score"),
        ("sshr_h", "CNOT"),
        ("and_resource_nmcts", "T"),
    ]
    with latex_out.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Metric & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for target, metric in focus:
            row = compare(joined, target, "external_revkit_oracle_synth", metric)
            if row is None:
                continue
            comparison = f"{target} vs RevKit oracle_synth".replace("_", r"\_")
            f.write(
                f"{comparison} & {metric} & {row['items']} & "
                f"{row['wins']}/{row['losses']}/{row['ties']} & "
                f"{format_latex_pct(float(row['mean_relative']))} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_revkit_oracle_synth_traditional.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "revkit_oracle_synth_traditional.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_revkit_oracle_synth_traditional.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    tasks = load_truth_tasks(args.input, args.max_n, args.timeout)
    started = time.time()
    rows: list[dict[str, object]] = []
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(synthesize_task(task))
            if i % 25 == 0 or i == len(tasks):
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(synthesize_task, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % 25 == 0 or i == len(tasks):
                    print(f"{i}/{len(tasks)}", flush=True)
    rows.sort(key=lambda row: (int(row["n"]), str(row["name"])))
    internal_rows = [row for row in load_csv(args.input) if not row.get("error") and not row.get("skipped")]
    targets = [item.strip() for item in args.targets.split(",") if item.strip()]

    write_csv(args.raw_out, rows)
    write_analysis(args.analysis, args.summary, args.latex_out, rows, internal_rows, targets)
    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.run_manifest.write_text(
        json.dumps(
            {
                "input": str(args.input),
                "max_n": args.max_n,
                "workers": args.workers,
                "rows": len(rows),
                "usable_rows": sum(1 for row in rows if usable(row)),
                "elapsed_s": time.time() - started,
                "method": "external_revkit_oracle_synth",
                "claim_boundary": "RevKit Python oracle_synth API, Clifford+T netlist proxy, no hardware mapping.",
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
