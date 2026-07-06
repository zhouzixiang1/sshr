#!/usr/bin/env python3
"""Compare external baseline CSV rows against in-harness experiment rows."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"


def load_usable(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row for row in rows if not row.get("error") and not row.get("skipped") and str(row.get("correct", "True")) != "False"]


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def by_name_method(rows: Iterable[dict]) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for row in rows:
        out.setdefault(row["name"], {})[row["method"]] = row
    return out


def compare(
    joined: dict[str, dict[str, dict]],
    target: str,
    baseline: str,
    metric: str,
) -> tuple[int, int, int, float, int]:
    vals = []
    wins = losses = ties = 0
    for table in joined.values():
        if target not in table or baseline not in table:
            continue
        new = float(table[target][metric])
        old = float(table[baseline][metric])
        rel = pct(new, old)
        vals.append(rel)
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
    mean = sum(vals) / len(vals) if vals else float("nan")
    return wins, losses, ties, mean, len(vals)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-csv", type=Path, default=RESULTS / "raw_external_baselines.csv")
    parser.add_argument("--internal-csv", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_external_baselines.md")
    parser.add_argument(
        "--targets",
        default="and_resource_nmcts,and_profile_resource_nmcts,and_affine_nmcts,and_cube_beam,and_esop_milp,sshr_h",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    external = load_usable(args.external_csv)
    internal = load_usable(args.internal_csv)
    joined = by_name_method(internal)
    for name, methods in by_name_method(external).items():
        joined.setdefault(name, {}).update(methods)

    targets = [item.strip() for item in args.targets.split(",") if item.strip()]
    external_methods = sorted({row["method"] for row in external})
    metrics = ["T", "CNOT", "depth", "peak_ancilla", "score"]

    lines = [
        "# External Baseline Analysis",
        "",
        f"External rows: {len(list(csv.DictReader(args.external_csv.open(encoding='utf-8'))))}; usable: {len(external)}.",
        f"Internal rows: {len(list(csv.DictReader(args.internal_csv.open(encoding='utf-8'))))}; usable: {len(internal)}.",
        "",
        "## External Summary",
        "",
        "| method | n | functions | mean T | mean CNOT | mean score | mean time s |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    groups: dict[tuple[str, int], list[dict]] = {}
    for row in external:
        groups.setdefault((row["method"], int(row["n"])), []).append(row)
    for (method, n), items in sorted(groups.items()):
        mean = lambda key: sum(float(row[key]) for row in items) / len(items)
        lines.append(
            f"| {method} | {n} | {len(items)} | {mean('T'):.2f} | {mean('CNOT'):.2f} | {mean('score'):.2f} | {mean('time_s'):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Pairwise Comparisons on Common Functions",
            "",
            "| target | external baseline | metric | functions | wins | losses | ties | mean relative |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for target in targets:
        for baseline in external_methods:
            if target == baseline:
                continue
            for metric in metrics:
                wins, losses, ties, mean, count = compare(joined, target, baseline, metric)
                if count:
                    lines.append(
                        f"| {target} | {baseline} | {metric} | {count} | {wins} | {losses} | {ties} | {mean:+.2f}% |"
                    )

    lines.extend(
        [
            "",
            "## External Baseline Error/Skip Rows",
            "",
            "| function | n | method | skipped | error |",
            "|---|---:|---|---|---|",
        ]
    )
    with args.external_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("error") or row.get("skipped"):
                lines.append(
                    f"| {row.get('name', '')} | {row.get('n', '')} | {row.get('method', '')} | {row.get('skipped', '')} | {row.get('error', '')} |"
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
