#!/usr/bin/env python3
"""Generate runtime and resource tradeoff tables from experiment CSV output."""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"

METHOD_ORDER = [
    "direct_anf",
    "and_direct_anf",
    "and_mcts_factor",
    "and_affine_greedy",
    "and_affine_no_guard",
    "and_affine_nmcts",
    "sshr_h",
]

METHOD_LABELS = {
    "direct_anf": "Direct ANF",
    "and_direct_anf": "AND-direct ANF",
    "and_mcts_factor": "Fixed MCTS",
    "and_affine_greedy": "Affine-greedy",
    "and_affine_no_guard": "Affine-no-guard",
    "and_affine_nmcts": "Affine-NMCTS",
    "sshr_h": "SSHR-H",
}


def fnum(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def qtile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def fmt(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "--"
    return f"{value:.{digits}f}"


def tex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("%", r"\%")


def load_rows(preset: str) -> list[dict[str, str]]:
    raw = RESULTS / f"raw_{preset}.csv"
    return list(csv.DictReader(raw.open(encoding="utf-8")))


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["method"]].append(row)
    return groups


def method_sort(method: str) -> tuple[int, str]:
    if method in METHOD_ORDER:
        return METHOD_ORDER.index(method), method
    return len(METHOD_ORDER), method


def summarize_method(method: str, rows: list[dict[str, str]]) -> dict[str, object]:
    usable = [r for r in rows if not r.get("error") and not r.get("skipped")]
    times = [v for r in usable if (v := fnum(r.get("time_s"))) is not None]
    out: dict[str, object] = {
        "method": method,
        "label": METHOD_LABELS.get(method, method),
        "rows": len(rows),
        "completed": len(usable),
        "errors": sum(1 for r in rows if r.get("error")),
        "skipped": sum(1 for r in rows if r.get("skipped")),
        "median_s": median(times) if times else float("nan"),
        "p95_s": qtile(times, 0.95),
        "max_s": max(times) if times else float("nan"),
        "total_s": sum(times) if times else float("nan"),
    }
    for key in ["T", "CNOT", "depth", "peak_ancilla", "score"]:
        vals = [v for r in usable if (v := fnum(r.get(key))) is not None]
        out[f"mean_{key}"] = mean(vals) if vals else float("nan")
    return out


def write_markdown(preset: str, summaries: list[dict[str, object]], rows: list[dict[str, str]]) -> Path:
    out = RESULTS / f"runtime_{preset}.md"
    lines = [
        f"# Runtime and Resource Tradeoff: {preset}",
        "",
        f"Rows: {len(rows)}; errors: {sum(1 for r in rows if r.get('error'))}; skipped: {sum(1 for r in rows if r.get('skipped'))}.",
        "",
        "## Runtime by method",
        "",
        "| method | completed | errors | skipped | median s | p95 s | max s | total completed s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            "| {label} | {completed} | {errors} | {skipped} | {median_s} | {p95_s} | {max_s} | {total_s} |".format(
                label=s["label"],
                completed=s["completed"],
                errors=s["errors"],
                skipped=s["skipped"],
                median_s=fmt(float(s["median_s"]), 3),
                p95_s=fmt(float(s["p95_s"]), 3),
                max_s=fmt(float(s["max_s"]), 3),
                total_s=fmt(float(s["total_s"]), 1),
            )
        )
    lines.extend(
        [
            "",
            "## Mean resources by method",
            "",
            "| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for s in summaries:
        lines.append(
            "| {label} | {completed} | {mean_T} | {mean_CNOT} | {mean_depth} | {mean_peak_ancilla} | {mean_score} |".format(
                label=s["label"],
                completed=s["completed"],
                mean_T=fmt(float(s["mean_T"]), 2),
                mean_CNOT=fmt(float(s["mean_CNOT"]), 2),
                mean_depth=fmt(float(s["mean_depth"]), 2),
                mean_peak_ancilla=fmt(float(s["mean_peak_ancilla"]), 2),
                mean_score=fmt(float(s["mean_score"]), 2),
            )
        )
    error_rows = [r for r in rows if r.get("error")]
    if error_rows:
        lines.extend(["", "## Timeout / error rows", "", "| function | n | method | error |", "|---|---:|---|---|"])
        for r in error_rows:
            lines.append(f"| {r.get('name', '')} | {r.get('n', '')} | {r.get('method', '')} | {r.get('error', '')} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_latex_tables(preset: str, summaries: list[dict[str, object]]) -> tuple[Path, Path]:
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    runtime = PAPER_TABLES / f"runtime_{preset}.tex"
    resource = PAPER_TABLES / f"resource_{preset}.tex"

    runtime_lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Method & Completed & Errors & Skipped & Median s & p95 s & Max s \\",
        r"\midrule",
    ]
    for s in summaries:
        runtime_lines.append(
            "{label} & {completed} & {errors} & {skipped} & {median_s} & {p95_s} & {max_s} \\\\".format(
                label=tex_escape(str(s["label"])),
                completed=s["completed"],
                errors=s["errors"],
                skipped=s["skipped"],
                median_s=fmt(float(s["median_s"]), 2),
                p95_s=fmt(float(s["p95_s"]), 2),
                max_s=fmt(float(s["max_s"]), 2),
            )
        )
    runtime_lines.extend([r"\bottomrule", r"\end{tabular}"])
    runtime.write_text("\n".join(runtime_lines) + "\n", encoding="utf-8")

    resource_lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Method & Mean T & Mean CNOT & Mean depth & Mean ancilla & Mean score \\",
        r"\midrule",
    ]
    for s in summaries:
        resource_lines.append(
            "{label} & {mean_T} & {mean_CNOT} & {mean_depth} & {mean_peak_ancilla} & {mean_score} \\\\".format(
                label=tex_escape(str(s["label"])),
                mean_T=fmt(float(s["mean_T"]), 1),
                mean_CNOT=fmt(float(s["mean_CNOT"]), 1),
                mean_depth=fmt(float(s["mean_depth"]), 1),
                mean_peak_ancilla=fmt(float(s["mean_peak_ancilla"]), 2),
                mean_score=fmt(float(s["mean_score"]), 1),
            )
        )
    resource_lines.extend([r"\bottomrule", r"\end{tabular}"])
    resource.write_text("\n".join(resource_lines) + "\n", encoding="utf-8")
    return runtime, resource


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="ablation_affine")
    args = ap.parse_args()

    rows = load_rows(args.preset)
    groups = group_rows(rows)
    summaries = [
        summarize_method(method, groups[method])
        for method in sorted(groups, key=method_sort)
    ]
    md = write_markdown(args.preset, summaries, rows)
    runtime, resource = write_latex_tables(args.preset, summaries)
    print(f"wrote {md}")
    print(f"wrote {runtime}")
    print(f"wrote {resource}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
