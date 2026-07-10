#!/usr/bin/env python3
"""Run a ROS-style resource-constrained LUT oracle proxy.

This is not the official ROS implementation.  It is an external ABC k-LUT
mapping sweep that chooses the best mapped LUT network under the same logical
oracle resource score used by the project.  The goal is to provide a stronger
and reproducible LUT-based baseline than a single fixed K value while keeping
the claim honest: no SAT garbage management and no hardware mapping are used.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from run_external_baselines import (
    DEFAULT_ABC_BIN,
    DEFAULT_WEIGHTS,
    bool_from_row,
    load_manifest,
    run_abc_lut,
)


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]
DEFAULT_TARGETS = [
    "and_resource_nmcts",
    "and_profile_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_linear_pair",
    "and_fprm_linear_pair_fast",
    "and_boolean_linear_pair_screen_deeper",
    "and_direct_anf",
    "direct_anf",
]


@dataclass(frozen=True)
class LutTask:
    dataset: str
    row: dict[str, str]
    k: int
    timeout: float
    abc_bin: Path


def parse_labeled_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, path = value.split("=", 1)
    return label.strip(), Path(path.strip())


def parse_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else THIS_DIR / path


def score(cost, weights: dict[str, float]) -> float:
    return (
        weights["t"] * cost.T
        + weights["cnot"] * cost.CNOT
        + weights["depth"] * cost.depth
        + weights["gates"] * cost.gates
        + weights["ancilla"] * cost.peak_ancilla
    )


def evaluate_task(task: LutTask) -> dict[str, object]:
    bf = bool_from_row(task.row)
    base = {
        "dataset": task.dataset,
        "index": task.row.get("index", ""),
        "name": task.row["name"],
        "preset_name": task.row.get("preset_name", task.row["name"]),
        "n": bf.n,
        "anf_terms": task.row.get("anf_terms", ""),
        "method": f"external_ros_lut_k{task.k}",
        "selected_k": task.k,
        "source_manifest": task.row.get("_manifest_dir", ""),
        "abc_script": f"strash; if -K {task.k}",
    }
    try:
        started = time.time()
        cost, extra = run_abc_lut(
            task.row,
            bf,
            task.timeout,
            task.abc_bin,
            f"strash; if -K {task.k}",
        )
        elapsed = time.time() - started
        correct = bool(extra.pop("correct"))
        return {
            **base,
            "T": cost.T,
            "CNOT": cost.CNOT,
            "depth": cost.depth,
            "gates": cost.gates,
            "explicit_ancilla": cost.explicit_ancilla,
            "peak_ancilla": cost.peak_ancilla,
            "n_qubits": bf.n + 1 + cost.explicit_ancilla,
            "score": score(cost, DEFAULT_WEIGHTS),
            "correct": correct,
            "time_s": elapsed,
            "error": "",
            "skipped": "",
            **extra,
        }
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
            "correct": "",
            "time_s": "",
            "error": repr(exc),
            "skipped": "",
        }


def load_manifest_rows(inputs: list[str], min_n: int | None, max_n: int | None) -> list[tuple[str, dict[str, str]]]:
    out: list[tuple[str, dict[str, str]]] = []
    for raw in inputs:
        label, path = parse_labeled_path(raw)
        path = resolve_path(path)
        for row in load_manifest(path):
            n = int(row["n"])
            if min_n is not None and n < min_n:
                continue
            if max_n is not None and n > max_n:
                continue
            out.append((label, row))
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "index",
        "name",
        "preset_name",
        "n",
        "anf_terms",
        "method",
        "selected_k",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "correct",
        "time_s",
        "abc_lut_nodes",
        "abc_lut_max_fanin",
        "abc_script",
        "source_manifest",
        "skipped",
        "error",
    ]
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, object]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def select_best(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        if usable(row):
            grouped.setdefault((str(row["dataset"]), str(row["name"])), []).append(row)
    best_rows: list[dict[str, object]] = []
    for (_dataset, _name), items in sorted(grouped.items()):
        best = min(items, key=lambda row: (float(row["score"]), float(row["time_s"] or 0.0), int(row["selected_k"])))
        out = dict(best)
        out["method"] = "external_ros_lut_proxy"
        out["candidate_ks"] = ",".join(str(row["selected_k"]) for row in sorted(items, key=lambda row: int(row["selected_k"])))
        out["selected_k"] = int(best["selected_k"])
        best_rows.append(out)
    return best_rows


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_internal(inputs: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in inputs:
        _label, path = parse_labeled_path(raw)
        path = resolve_path(path)
        rows.extend(load_csv(path))
    return [row for row in rows if not row.get("error") and not row.get("skipped")]


def by_name_method(rows: Iterable[dict[str, object]]) -> dict[str, dict[str, dict[str, object]]]:
    out: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def rel(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare(
    joined: dict[str, dict[str, dict[str, object]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    relatives: list[float] = []
    wins = losses = ties = 0
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
        by_n[str(methods[target].get("n", "?"))] = by_n.get(str(methods[target].get("n", "?")), 0) + 1
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
    analysis_path: Path,
    summary_path: Path,
    table_path: Path,
    sweep_rows: list[dict[str, object]],
    best_rows: list[dict[str, object]],
    internal_rows: list[dict[str, str]],
    targets: list[str],
) -> None:
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(best_rows).items():
        joined.setdefault(name, {}).update(methods)
    for name, methods in by_name_method(sweep_rows).items():
        joined.setdefault(name, {}).update(methods)

    comparisons: list[dict[str, object]] = []
    for target in targets:
        for baseline in ["external_ros_lut_proxy", "external_ros_lut_k4"]:
            if target == baseline:
                continue
            for metric in METRICS:
                result = compare(joined, target, baseline, metric)
                if result is not None:
                    comparisons.append(result)
    best_vs_k4 = [
        compare(joined, "external_ros_lut_proxy", "external_ros_lut_k4", metric)
        for metric in METRICS
    ]
    comparisons.extend(result for result in best_vs_k4 if result is not None)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["target", "baseline", "metric", "items", "wins", "losses", "ties", "mean_relative", "by_n"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(comparisons)

    selected_counts: dict[tuple[str, str, str], int] = {}
    for row in best_rows:
        key = (str(row["dataset"]), str(row["n"]), str(row["selected_k"]))
        selected_counts[key] = selected_counts.get(key, 0) + 1

    lines = [
        "# ROS-Style LUT Proxy Sweep",
        "",
        "This analysis is a logic-level proxy for ROS-style resource-constrained LUT",
        "oracle synthesis. It uses exported BLIF benchmarks, runs ABC `if -K` for",
        "multiple K values, estimates each mapped LUT network as local-ANF",
        "compute/action/uncompute logic, and chooses the best K per function under",
        "the project score. It is not the official ROS, RevKit, or mockturtle flow.",
        "",
        f"Sweep rows: {len(sweep_rows)}; usable: {sum(1 for row in sweep_rows if usable(row))}.",
        f"Best-K rows: {len(best_rows)}.",
        "",
        "## Selected K Distribution",
        "",
        "| dataset | n | K | functions |",
        "|---|---:|---:|---:|",
    ]
    for (dataset, n, k), count in sorted(selected_counts.items(), key=lambda item: (item[0][0], int(item[0][1]), int(item[0][2]))):
        lines.append(f"| {dataset} | {n} | {k} | {count} |")

    lines.extend(
        [
            "",
            "## Pairwise Comparisons",
            "",
            "| target | baseline | metric | items | W/L/T | mean relative |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in comparisons:
        lines.append(
            f"| {row['target']} | {row['baseline']} | {row['metric']} | {row['items']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | {format_pct(float(row['mean_relative']))} |"
        )
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    table_path.parent.mkdir(parents=True, exist_ok=True)
    focus = [
        ("and_resource_nmcts", "external_ros_lut_proxy", "score"),
        ("and_profile_resource_nmcts", "external_ros_lut_proxy", "score"),
        ("and_pareto_resource_nmcts", "external_ros_lut_proxy", "score"),
        ("and_direct_anf", "external_ros_lut_proxy", "score"),
        ("external_ros_lut_proxy", "external_ros_lut_k4", "score"),
    ]
    with table_path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrr}\n")
        f.write("\\toprule\n")
        f.write("Comparison & Metric & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for target, baseline, metric in focus:
            row = compare(joined, target, baseline, metric)
            if row is None:
                continue
            comparison = f"{target} vs {baseline}".replace("_", r"\_")
            f.write(
                f"{comparison} & {metric} & {row['items']} & "
                f"{row['wins']}/{row['losses']}/{row['ties']} & "
                f"{format_latex_pct(float(row['mean_relative']))} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="append", required=True, help="LABEL=manifest.json; can be repeated")
    parser.add_argument("--internal", action="append", required=True, help="LABEL=raw_internal.csv; can be repeated")
    parser.add_argument("--ks", default="3,4,5")
    parser.add_argument("--min-n", type=int, default=None)
    parser.add_argument("--max-n", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--abc-bin", type=Path, default=DEFAULT_ABC_BIN)
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_ros_lut_proxy_sweep.csv")
    parser.add_argument("--best-out", type=Path, default=RESULTS / "raw_ros_lut_proxy_best.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_ros_lut_proxy.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_ros_lut_proxy.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "ros_lut_proxy.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_ros_lut_proxy.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    ks = parse_ints(args.ks)
    rows = load_manifest_rows(args.manifest, args.min_n, args.max_n)
    tasks = [
        LutTask(dataset=dataset, row=row, k=k, timeout=args.timeout, abc_bin=args.abc_bin)
        for dataset, row in rows
        for k in ks
    ]
    started = time.time()
    sweep_rows: list[dict[str, object]] = []
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            sweep_rows.append(evaluate_task(task))
            print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(evaluate_task, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                sweep_rows.append(fut.result())
                if i % 25 == 0 or i == len(tasks):
                    print(f"{i}/{len(tasks)}", flush=True)
    sweep_rows.sort(key=lambda row: (str(row["dataset"]), int(row["n"]), str(row["name"]), int(row["selected_k"])))
    best_rows = select_best(sweep_rows)
    internal_rows = load_internal(args.internal)
    targets = [item.strip() for item in args.targets.split(",") if item.strip()]

    write_csv(args.raw_out, sweep_rows)
    write_csv(args.best_out, best_rows)
    write_analysis(args.analysis, args.summary, args.latex_out, sweep_rows, best_rows, internal_rows, targets)

    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.run_manifest.write_text(
        json.dumps(
            {
                "manifests": args.manifest,
                "internal": args.internal,
                "ks": ks,
                "min_n": args.min_n,
                "max_n": args.max_n,
                "timeout": args.timeout,
                "workers": args.workers,
                "rows": len(rows),
                "sweep_rows": len(sweep_rows),
                "best_rows": len(best_rows),
                "elapsed_s": time.time() - started,
                "abc_bin": str(args.abc_bin),
                "claim_boundary": "ABC LUT sweep proxy, not official ROS/RevKit/mockturtle.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"elapsed {time.time() - started:.2f}s")
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.best_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.run_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
