#!/usr/bin/env python3
"""Build a compact paired statistical evidence table for manuscript claims."""
from __future__ import annotations

import csv
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class ComparisonSpec:
    label: str
    target_method: str
    baseline_method: str
    target_files: tuple[str, ...]
    baseline_files: tuple[str, ...]
    metric: str = "score"


COMPARISONS = [
    ComparisonSpec(
        "n<=6 Pareto vs direct ANF",
        "and_pareto_resource_nmcts",
        "direct_anf",
        ("raw_traditional_resource.csv",),
        ("raw_traditional_resource.csv",),
    ),
    ComparisonSpec(
        "n<=6 Pareto vs ESOP beam",
        "and_pareto_resource_nmcts",
        "and_cube_beam",
        ("raw_traditional_resource.csv",),
        ("raw_traditional_resource.csv",),
    ),
    ComparisonSpec(
        "n<=6 Pareto vs ESOP-MILP",
        "and_pareto_resource_nmcts",
        "and_esop_milp",
        ("raw_traditional_resource.csv",),
        ("raw_traditional_resource.csv",),
    ),
    ComparisonSpec(
        "n<=6 Pareto vs SSHR-H",
        "and_pareto_resource_nmcts",
        "sshr_h",
        ("raw_traditional_resource.csv",),
        ("raw_traditional_resource.csv",),
    ),
    ComparisonSpec(
        "n<=6 Pareto vs SSHR-I CNOT",
        "and_pareto_resource_nmcts",
        "external_sshr_i_cnot",
        ("raw_traditional_resource.csv",),
        ("raw_external_traditional_resource_n6.csv",),
    ),
    ComparisonSpec(
        "n<=6 Pareto vs ABC-XAG",
        "and_pareto_resource_nmcts",
        "external_abc_xag",
        ("raw_traditional_resource.csv",),
        ("raw_external_traditional_resource_n6.csv",),
    ),
    ComparisonSpec(
        "ROS-style LUT best-K",
        "and_pareto_resource_nmcts",
        "external_ros_lut_proxy",
        (
            "raw_traditional_resource.csv",
            "raw_highdim_resource.csv",
            "raw_highdim_scale_resource.csv",
            "raw_ultra_highdim_resource.csv",
            "raw_mega_highdim_resource.csv",
        ),
        ("raw_ros_lut_proxy_best.csv",),
    ),
    ComparisonSpec(
        "mockturtle XAG n<=6",
        "and_pareto_resource_nmcts",
        "external_mockturtle_xag_k4",
        ("raw_traditional_resource.csv",),
        ("raw_mockturtle_xag_probe.csv",),
    ),
    ComparisonSpec(
        "mockturtle XAG n=14",
        "and_pareto_resource_nmcts",
        "external_mockturtle_xag_k4",
        ("raw_highdim_resource.csv",),
        ("raw_mockturtle_xag_highdim_probe.csv",),
    ),
    ComparisonSpec(
        "CirKit AIG/MC n<=6",
        "and_pareto_resource_nmcts",
        "external_cirkit_aig_mc",
        ("raw_traditional_resource.csv",),
        ("raw_cirkit_aig_probe.csv",),
    ),
    ComparisonSpec(
        "CirKit AIG/MC n=14",
        "and_pareto_resource_nmcts",
        "external_cirkit_aig_mc",
        ("raw_highdim_resource.csv",),
        ("raw_cirkit_aig_highdim_probe.csv",),
    ),
    ComparisonSpec(
        "RevKit CLI exact oracle",
        "and_pareto_resource_nmcts",
        "external_revkit_cli_best_score",
        ("raw_traditional_resource.csv",),
        ("raw_revkit_cli_multiflow_traditional.csv",),
    ),
    ComparisonSpec(
        "n=14 Pareto vs root beam",
        "and_pareto_resource_nmcts",
        "and_fprm_root_beam",
        ("raw_highdim_resource.csv",),
        ("raw_highdim_resource.csv",),
    ),
    ComparisonSpec(
        "n=16 Resource vs root beam",
        "and_resource_nmcts",
        "and_fprm_root_beam",
        ("raw_ultra_highdim_resource.csv",),
        ("raw_ultra_highdim_resource.csv",),
    ),
    ComparisonSpec(
        "n=18 Resource vs fast pair",
        "and_resource_nmcts",
        "and_fprm_linear_pair_fast",
        ("raw_mega_highdim_resource.csv",),
        ("raw_mega_highdim_resource.csv",),
    ),
]


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def falsey(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no"}


def usable(row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    if "correct" in row and falsey(row.get("correct")):
        return False
    for key in ("abc_blif_correct", "source_blif_correct", "verilog_correct"):
        if key in row and falsey(row.get(key)):
            return False
    for key in ("anf_verified", "circuit_anf_verified", "verified_up_to_global_phase"):
        if key in row and falsey(row.get(key)):
            return False
    return True


def read_methods(paths: tuple[str, ...], method: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in paths:
        path = RESULTS / name
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("method") == method and usable(row):
                    rows[row["name"]] = row
    return rows


def relative_pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def log10_sign_test_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 0.0
    k = min(wins, losses)
    log_terms = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2.0)
        for i in range(k + 1)
    ]
    m = max(log_terms)
    log_sum = m + math.log(sum(math.exp(term - m) for term in log_terms))
    log_p = min(0.0, math.log(2.0) + log_sum)
    return log_p / math.log(10.0)


def analyze(spec: ComparisonSpec) -> dict[str, object]:
    target = read_methods(spec.target_files, spec.target_method)
    baseline = read_methods(spec.baseline_files, spec.baseline_method)
    names = sorted(set(target) & set(baseline))
    if not names:
        raise RuntimeError(f"no matched rows for {spec.label}")

    wins = losses = ties = 0
    relatives: list[float] = []
    target_values: list[float] = []
    baseline_values: list[float] = []
    ns: set[int] = set()
    for name in names:
        t_row = target[name]
        b_row = baseline[name]
        t = float(t_row[spec.metric])
        b = float(b_row[spec.metric])
        target_values.append(t)
        baseline_values.append(b)
        relatives.append(relative_pct(t, b))
        if t < b - 1e-9:
            wins += 1
        elif t > b + 1e-9:
            losses += 1
        else:
            ties += 1
        n_value = t_row.get("n") or b_row.get("n")
        if n_value:
            ns.add(int(float(n_value)))

    log10_p = log10_sign_test_p(wins, losses)
    return {
        "comparison": spec.label,
        "metric": spec.metric,
        "n_scope": format_scope(ns),
        "pairs": len(names),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_target": statistics.mean(target_values),
        "mean_baseline": statistics.mean(baseline_values),
        "mean_relative_pct": statistics.mean(relatives),
        "median_relative_pct": statistics.median(relatives),
        "log10_sign_p": log10_p,
        "target_method": spec.target_method,
        "baseline_method": spec.baseline_method,
        "target_files": ";".join(spec.target_files),
        "baseline_files": ";".join(spec.baseline_files),
    }


def format_scope(values: set[int]) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    ranges: list[str] = []
    start = prev = ordered[0]
    for value in ordered[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = value
    ranges.append(f"{start}" if start == prev else f"{start}-{prev}")
    return "n=" + ",".join(ranges)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "comparison",
        "metric",
        "n_scope",
        "pairs",
        "wins",
        "losses",
        "ties",
        "mean_target",
        "mean_baseline",
        "mean_relative_pct",
        "median_relative_pct",
        "log10_sign_p",
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


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Paired Statistical Evidence",
        "",
        "Rows are recomputed from usable raw CSV rows matched by item name.",
        "The sign test is two-sided and ignores ties. Negative relative changes favor the target method.",
        "",
        "| comparison | scope | pairs | W/L/T | mean relative | median relative | log10 p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["comparison"]),
                    str(row["n_scope"]),
                    str(row["pairs"]),
                    f"{row['wins']}/{row['losses']}/{row['ties']}",
                    f"{float(row['mean_relative_pct']):+.2f}%",
                    f"{float(row['median_relative_pct']):+.2f}%",
                    f"{float(row['log10_sign_p']):.2f}",
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


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}Xr>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}p{0.13\linewidth}>{\raggedleft\arraybackslash}p{0.13\linewidth}>{\raggedleft\arraybackslash}p{0.10\linewidth}}",
        r"\toprule",
        r"Comparison & Pairs & W/L/T & Mean $\Delta$ & Median $\Delta$ & $\log_{10}p$ \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{tex_escape(str(row['comparison']))} & {row['pairs']} & "
            f"{row['wins']}/{row['losses']}/{row['ties']} & "
            f"${float(row['mean_relative_pct']):+.2f}\\%$ & "
            f"${float(row['median_relative_pct']):+.2f}\\%$ & "
            f"{float(row['log10_sign_p']):.2f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    raise_csv_field_limit()
    rows = [analyze(spec) for spec in COMPARISONS]
    write_csv(RESULTS / "summary_paired_statistical_evidence.csv", rows)
    write_markdown(RESULTS / "analysis_paired_statistical_evidence.md", rows)
    write_latex(TABLES / "paired_statistical_evidence.tex", rows)
    print(f"wrote {len(rows)} paired statistical comparisons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
