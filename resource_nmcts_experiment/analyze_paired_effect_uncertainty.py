#!/usr/bin/env python3
"""Bootstrap uncertainty intervals for paired score-effect estimates."""
from __future__ import annotations

import csv
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Callable

from analyze_paired_statistical_evidence import (
    COMPARISONS,
    RESULTS,
    TABLES,
    format_scope,
    read_methods,
    relative_pct,
)


BOOTSTRAP_SAMPLES = 4000
BOOTSTRAP_SEED = 20260709


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def bootstrap_ci(
    values: list[float],
    statistic: Callable[[list[float]], float],
    rng: random.Random,
) -> tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    if len(values) == 1:
        return values[0], values[0]
    samples: list[float] = []
    n = len(values)
    for _ in range(BOOTSTRAP_SAMPLES):
        resampled = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistic(resampled))
    return percentile(samples, 0.025), percentile(samples, 0.975)


def analyze() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx, spec in enumerate(COMPARISONS):
        target = read_methods(spec.target_files, spec.target_method)
        baseline = read_methods(spec.baseline_files, spec.baseline_method)
        names = sorted(set(target) & set(baseline))
        if not names:
            raise RuntimeError(f"no matched rows for {spec.label}")

        relatives: list[float] = []
        ns: set[int] = set()
        for name in names:
            t_row = target[name]
            b_row = baseline[name]
            t_value = float(t_row[spec.metric])
            b_value = float(b_row[spec.metric])
            relatives.append(relative_pct(t_value, b_value))
            n_value = t_row.get("n") or b_row.get("n")
            if n_value:
                ns.add(int(float(n_value)))

        rng = random.Random(BOOTSTRAP_SEED + idx)
        mean_ci = bootstrap_ci(relatives, statistics.mean, rng)
        median_ci = bootstrap_ci(relatives, statistics.median, rng)
        mean_value = statistics.mean(relatives)
        median_value = statistics.median(relatives)
        p10 = percentile(relatives, 0.10)
        p90 = percentile(relatives, 0.90)
        rows.append(
            {
                "comparison": spec.label,
                "metric": spec.metric,
                "n_scope": format_scope(ns),
                "pairs": len(names),
                "mean_relative_pct": mean_value,
                "mean_ci_low_pct": mean_ci[0],
                "mean_ci_high_pct": mean_ci[1],
                "median_relative_pct": median_value,
                "median_ci_low_pct": median_ci[0],
                "median_ci_high_pct": median_ci[1],
                "item_p10_pct": p10,
                "item_p90_pct": p90,
                "mean_ci_excludes_zero": mean_ci[1] < 0.0 or mean_ci[0] > 0.0,
                "median_ci_excludes_zero": median_ci[1] < 0.0 or median_ci[0] > 0.0,
                "target_method": spec.target_method,
                "baseline_method": spec.baseline_method,
                "target_files": ";".join(spec.target_files),
                "baseline_files": ";".join(spec.baseline_files),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "comparison",
        "metric",
        "n_scope",
        "pairs",
        "mean_relative_pct",
        "mean_ci_low_pct",
        "mean_ci_high_pct",
        "median_relative_pct",
        "median_ci_low_pct",
        "median_ci_high_pct",
        "item_p10_pct",
        "item_p90_pct",
        "mean_ci_excludes_zero",
        "median_ci_excludes_zero",
        "target_method",
        "baseline_method",
        "target_files",
        "baseline_files",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value: object) -> str:
    return f"{float(value):+.2f}%"


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Paired Effect Uncertainty",
        "",
        "Rows reuse the matched pairs from the paired statistical evidence table.",
        f"Mean and median intervals are deterministic percentile bootstrap intervals with {BOOTSTRAP_SAMPLES} resamples per comparison.",
        "Negative relative changes favor the target method.",
        "",
        "| comparison | scope | pairs | mean relative [95% CI] | median relative [95% CI] | item p10/p90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["comparison"]),
                    str(row["n_scope"]),
                    str(row["pairs"]),
                    f"{fmt_pct(row['mean_relative_pct'])} [{fmt_pct(row['mean_ci_low_pct'])}, {fmt_pct(row['mean_ci_high_pct'])}]",
                    f"{fmt_pct(row['median_relative_pct'])} [{fmt_pct(row['median_ci_low_pct'])}, {fmt_pct(row['median_ci_high_pct'])}]",
                    f"{fmt_pct(row['item_p10_pct'])}/{fmt_pct(row['item_p90_pct'])}",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
    replacements = [
        ("n=3-6,14-16,18", r"$n=3$--$6$, 14--16, 18"),
        ("n=3-6", r"$n=3$--$6$"),
        ("n<=6", r"$n\leq6$"),
        ("n=14", r"$n=14$"),
        ("n=16", r"$n=16$"),
        ("n=18", r"$n=18$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def ci_cell(row: dict[str, object], center_key: str, low_key: str, high_key: str) -> str:
    return (
        f"${float(row[center_key]):+.2f}\\%$ "
        f"[${float(row[low_key]):+.2f}$, ${float(row[high_key]):+.2f}$]"
    )


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}Xr>{\raggedleft\arraybackslash}p{0.22\linewidth}>{\raggedleft\arraybackslash}p{0.22\linewidth}>{\raggedleft\arraybackslash}p{0.14\linewidth}}",
        r"\toprule",
        r"Comparison & Pairs & Mean $\Delta$ [95\% CI] & Median $\Delta$ [95\% CI] & Item p10/p90 \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(str(row['comparison']))} & {row['pairs']} & "
            f"{ci_cell(row, 'mean_relative_pct', 'mean_ci_low_pct', 'mean_ci_high_pct')} & "
            f"{ci_cell(row, 'median_relative_pct', 'median_ci_low_pct', 'median_ci_high_pct')} & "
            f"${float(row['item_p10_pct']):+.2f}$/${float(row['item_p90_pct']):+.2f}$ \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "rows": len(rows),
        "mean_ci_excludes_zero": sum(1 for row in rows if bool(row["mean_ci_excludes_zero"])),
        "median_ci_excludes_zero": sum(1 for row in rows if bool(row["median_ci_excludes_zero"])),
        "outputs": {
            "summary": "results/summary_paired_effect_uncertainty.csv",
            "analysis": "results/analysis_paired_effect_uncertainty.md",
            "manifest": "results/manifest_paired_effect_uncertainty.json",
            "table": "paper_latex/tables/paired_effect_uncertainty.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = analyze()
    write_csv(RESULTS / "summary_paired_effect_uncertainty.csv", rows)
    write_markdown(RESULTS / "analysis_paired_effect_uncertainty.md", rows)
    write_latex(TABLES / "paired_effect_uncertainty.tex", rows)
    write_manifest(RESULTS / "manifest_paired_effect_uncertainty.json", rows)
    print(f"wrote {len(rows)} paired effect uncertainty rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
