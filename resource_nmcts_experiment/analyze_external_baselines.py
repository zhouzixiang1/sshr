#!/usr/bin/env python3
"""Compare external baseline CSV rows against in-harness experiment rows."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"


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


def latex_pct(value: float) -> str:
    return f"${value:+.2f}\\%$"


def method_label(method: str) -> str:
    labels = {
        "external_abc_aig": "ABC-AIG export",
        "external_abc_xag": "ABC-XAG export",
        "external_abc_lut": "ABC-LUT export",
        "external_bdd": "BDD export",
        "external_abc_esop": "ABC-ESOP export",
        "external_sshr_h": "SSHR-H export",
        "external_sshr_i_cnot": "SSHR-I CNOT-opt",
        "external_sshr_i_t": "SSHR-I T-opt",
    }
    return labels.get(method, method.replace("_", r"\_"))


def metric_label(metric: str) -> str:
    labels = {
        "T": "T-count",
        "CNOT": "CNOT",
        "depth": "Depth",
        "peak_ancilla": "Peak ancilla",
        "score": "Score",
    }
    return labels[metric]


def write_latex_table(
    joined: dict[str, dict[str, dict]],
    target: str,
    external_methods: list[str],
    out: Path,
) -> None:
    selected = [
        "external_abc_aig",
        "external_abc_xag",
        "external_abc_lut",
        "external_bdd",
        "external_abc_esop",
    ]
    selected.extend(method for method in ["external_sshr_h", "external_sshr_i_cnot", "external_sshr_i_t"] if method in external_methods)
    metrics_by_method = {
        "external_sshr_h": ["T", "CNOT", "score"],
        "external_sshr_i_cnot": ["T", "CNOT", "score"],
        "external_sshr_i_t": ["T", "CNOT", "score"],
    }
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"External baseline & Metric & Wins & Losses & Ties & Mean relative \\",
        r"\midrule",
    ]
    for baseline in selected:
        if baseline not in external_methods:
            continue
        for metric in metrics_by_method.get(baseline, ["T", "CNOT", "depth", "peak_ancilla", "score"]):
            wins, losses, ties, mean, count = compare(joined, target, baseline, metric)
            if not count:
                continue
            lines.append(
                " & ".join(
                    [
                        method_label(baseline),
                        metric_label(metric),
                        str(wins),
                        str(losses),
                        str(ties),
                        latex_pct(mean),
                    ]
                )
                + r" \\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-csv", type=Path, default=RESULTS / "raw_external_baselines.csv")
    parser.add_argument("--internal-csv", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_external_baselines.md")
    parser.add_argument("--latex-out", type=Path, default=None)
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
    if args.latex_out:
        write_latex_table(joined, targets[0], external_methods, args.latex_out)
        print(f"wrote {args.latex_out}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
