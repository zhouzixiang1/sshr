#!/usr/bin/env python3
"""Exact small-n XAG multiplicative-complexity lower-bound analysis.

This script computes the minimum number of AND nodes needed to realize a
Boolean function over XOR, constants, and inputs.  For n<=4 the Boolean-function
space is small enough to run a target-specific breadth-first search over linear
spans of available XAG signals.  The resulting ``4 * AND`` value is a global
logic-level lower bound on T-count in the logical-AND accounting model used by
the Resource-NMCTS experiments.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import time
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from run_experiments import make_suite


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
METHOD = "and_exact_xag_mc"
METRICS = ["T", "score"]


def canonical_basis(vectors: Iterable[int]) -> tuple[int, ...]:
    basis: list[int] = []
    for raw in vectors:
        v = int(raw)
        for row in basis:
            pivot = row.bit_length() - 1
            if (v >> pivot) & 1:
                v ^= row
        if not v:
            continue
        pivot = v.bit_length() - 1
        basis = [row ^ v if ((row >> pivot) & 1) else row for row in basis]
        basis.append(v)
        basis.sort(key=lambda item: item.bit_length(), reverse=True)
    return tuple(basis)


def reduce_vector(value: int, basis: tuple[int, ...]) -> int:
    v = int(value)
    for row in basis:
        pivot = row.bit_length() - 1
        if (v >> pivot) & 1:
            v ^= row
    return v


def in_span(value: int, basis: tuple[int, ...]) -> bool:
    return reduce_vector(value, basis) == 0


@lru_cache(maxsize=None)
def span_values(basis: tuple[int, ...]) -> tuple[int, ...]:
    values = [0]
    for row in basis:
        values += [item ^ row for item in values]
    return tuple(sorted(values))


@lru_cache(maxsize=None)
def product_residuals(basis: tuple[int, ...]) -> tuple[int, ...]:
    values = span_values(basis)
    residuals: set[int] = set()
    for i, left in enumerate(values):
        for right in values[i:]:
            residual = reduce_vector(left & right, basis)
            if residual:
                residuals.add(residual)
    return tuple(sorted(residuals, key=lambda item: (item.bit_count(), item)))


def affine_basis(n: int) -> tuple[int, ...]:
    all_ones = (1 << (1 << n)) - 1
    rows = [all_ones]
    for var in range(n):
        mask = 0
        for x in range(1 << n):
            if (x >> var) & 1:
                mask |= 1 << x
        rows.append(mask)
    return canonical_basis(rows)


def exact_multiplicative_complexity(
    truth_table: int,
    n: int,
    max_and: int,
    max_states: int,
) -> tuple[int | None, int, int]:
    base = affine_basis(n)
    if in_span(truth_table, base):
        return 0, 1, 0

    seen = {base}
    frontier = deque([base])
    visited = 1
    max_frontier = 1
    for depth in range(max_and):
        next_frontier: deque[tuple[int, ...]] = deque()
        while frontier:
            basis = frontier.popleft()
            for residual in product_residuals(basis):
                candidate = canonical_basis((*basis, residual))
                if candidate in seen:
                    continue
                seen.add(candidate)
                visited += 1
                if in_span(truth_table, candidate):
                    return depth + 1, visited, max(max_frontier, len(next_frontier) + 1)
                if depth + 1 < max_and:
                    next_frontier.append(candidate)
                    if len(next_frontier) > max_frontier:
                        max_frontier = len(next_frontier)
                if visited > max_states:
                    return None, visited, max_frontier
        frontier = next_frontier
    return None, visited, max_frontier


def read_comparison_rows(paths: list[Path]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            if row.get("error") or row.get("skipped") or str(row.get("correct")) != "True":
                continue
            out[(row["name"], row["method"])] = row
    return out


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def compare(
    exact_rows: list[dict[str, object]],
    internal: dict[tuple[str, str], dict[str, str]],
    target: str,
    metric: str,
) -> dict[str, object]:
    wins = losses = ties = 0
    rel: list[float] = []
    pairs = 0
    for row in exact_rows:
        if row.get("error"):
            continue
        baseline = internal.get((str(row["name"]), target))
        if baseline is None:
            continue
        lower = float(row["T_lower_bound"] if metric == "T" else row["score_lower_bound"])
        value = float(baseline[metric])
        pairs += 1
        rel.append(pct(value, lower))
        if value < lower:
            wins += 1
        elif value > lower:
            losses += 1
        else:
            ties += 1
    return {
        "target": target,
        "metric": metric,
        "pairs": pairs,
        "below_lower": wins,
        "above_lower": losses,
        "on_lower": ties,
        "mean_relative_to_lower": statistics.mean(rel) if rel else float("nan"),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
    raw_path: Path,
    summary_path: Path,
    analysis_path: Path,
    latex_path: Path,
) -> None:
    write_csv(raw_path, rows)
    write_csv(summary_path, comparison_rows)

    errors = [row for row in rows if row.get("error")]
    solved = [row for row in rows if not row.get("error")]
    by_n: dict[int, list[dict[str, object]]] = {}
    for row in solved:
        by_n.setdefault(int(row["n"]), []).append(row)

    lines = [
        "# Exact XAG Multiplicative-Complexity Analysis",
        "",
        "This analysis computes the exact minimum number of AND nodes in an",
        "XAG/AND-XOR network for n<=4 target Boolean functions.  The value",
        "`4 * AND` is a global lower bound on logical-AND T-count, not a full",
        "CNOT/depth optimum.",
        "",
        f"Rows: {len(rows)}; solved: {len(solved)}; errors/unknown: {len(errors)}.",
        "",
        "## Exact lower-bound summary",
        "",
        "| n | functions | mean AND | mean T lower bound | max visited states |",
        "|---:|---:|---:|---:|---:|",
    ]
    for n, items in sorted(by_n.items()):
        lines.append(
            f"| {n} | {len(items)} | {statistics.mean(float(row['min_and']) for row in items):.2f} | "
            f"{statistics.mean(float(row['T_lower_bound']) for row in items):.2f} | "
            f"{max(int(row['visited_states']) for row in items)} |"
        )
    lines.extend(
        [
            "",
            "## Paired comparison to the lower bound",
            "",
            "| target method | metric | pairs | below lower | above lower | on lower | mean relative to lower |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        lines.append(
            f"| {row['target']} | {row['metric']} | {row['pairs']} | {row['below_lower']} | "
            f"{row['above_lower']} | {row['on_lower']} | {float(row['mean_relative_to_lower']):+.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `below lower` should be zero for T-count; otherwise the accounting models are inconsistent.",
            "- Equality means the method reaches the global multiplicative-complexity T lower bound for that function.",
            "- A positive relative gap is expected because the bound ignores CNOT, depth, uncomputation structure, and ancilla profile.",
        ]
    )
    analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    score_rows = [row for row in comparison_rows if row["metric"] == "T"]
    labels = {
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"\paretomethod{}",
        "and_esop_milp": "ESOP-MILP",
        "external_sshr_i_t": "SSHR-I-T",
    }
    table = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Method & Pairs & On lower & Above lower & Mean T gap \\",
        r"\midrule",
    ]
    for row in score_rows:
        label = labels.get(str(row["target"]), str(row["target"]).replace("_", r"\_"))
        table.append(
            f"{label} & {row['pairs']} & {row['on_lower']} & {row['above_lower']} & "
            f"${float(row['mean_relative_to_lower']):+.2f}\\%$ \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}"])
    latex_path.parent.mkdir(parents=True, exist_ok=True)
    latex_path.write_text("\n".join(table) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="traditional_resource")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-n", type=int, default=4)
    parser.add_argument("--max-and", type=int, default=5)
    parser.add_argument("--max-states", type=int, default=250_000)
    parser.add_argument("--comparison-csv", type=Path, action="append")
    parser.add_argument("--raw", type=Path, default=RESULTS / "raw_exact_xag_mc.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_exact_xag_mc.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_exact_xag_mc.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "exact_xag_mc.tex")
    args = parser.parse_args()

    suite = [(name, bf) for name, bf in make_suite(args.preset, args.seed) if bf.n <= args.max_n]
    rows: list[dict[str, object]] = []
    for index, (name, bf) in enumerate(suite, start=1):
        start = time.time()
        min_and, visited, max_frontier = exact_multiplicative_complexity(
            bf.truth_table,
            bf.n,
            args.max_and,
            args.max_states,
        )
        row: dict[str, object] = {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "min_and": "" if min_and is None else min_and,
            "T_lower_bound": "" if min_and is None else 4 * min_and,
            "score_lower_bound": "" if min_and is None else 4 * min_and,
            "visited_states": visited,
            "max_frontier": max_frontier,
            "time_s": time.time() - start,
            "error": "" if min_and is not None else f"not solved within max_and={args.max_and}, max_states={args.max_states}",
        }
        rows.append(row)
        print(f"{index}/{len(suite)} {name} min_and={min_and} visited={visited} time={row['time_s']:.3f}s")

    comparison_paths = args.comparison_csv or [
        RESULTS / "raw_traditional_resource.csv",
        RESULTS / "raw_external_traditional_resource_n6.csv",
    ]
    internal = read_comparison_rows(comparison_paths)
    targets = [
        "and_resource_nmcts",
        "and_pareto_resource_nmcts",
        "and_esop_milp",
        "external_sshr_i_t",
    ]
    comparison_rows = [compare(rows, internal, target, metric) for target in targets for metric in METRICS]
    write_outputs(rows, comparison_rows, args.raw, args.summary, args.analysis, args.latex_out)
    print(f"wrote {args.analysis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
