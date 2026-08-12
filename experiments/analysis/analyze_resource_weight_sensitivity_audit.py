#!/usr/bin/env python3
"""Audit resource-weight sensitivity across internal and external baselines.

The older weight-robustness table focuses on internal and high-dimensional
rows.  This audit is broader: it re-scores the matched comparison set that a
reviewer is most likely to question, including SSHR-I, ABC-XAG, ROS-style LUT,
RevKit, mockturtle, Caterpillar, and CirKit probes.  It is a post-hoc audit over already
verified CSV rows and does not rerun synthesis.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Callable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

RAW = RESULTS / "raw_resource_weight_sensitivity_audit.csv"
SUMMARY = RESULTS / "summary_resource_weight_sensitivity_audit.csv"
ANALYSIS = RESULTS / "analysis_resource_weight_sensitivity_audit.md"
MANIFEST = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
TABLE = TABLES / "resource_weight_sensitivity_audit.tex"


@dataclass(frozen=True)
class WeightProfile:
    key: str
    label: str
    t: float
    cnot: float
    depth: float
    gates: float
    ancilla: float


@dataclass(frozen=True)
class ComparisonSpec:
    key: str
    label: str
    role: str
    target_method: str
    baseline_method: str
    target_files: tuple[str, ...]
    baseline_files: tuple[str, ...]
    boundary: str
    target_filter: Callable[[dict[str, str]], bool] = lambda row: True
    baseline_filter: Callable[[dict[str, str]], bool] = lambda row: True


PROFILES = [
    WeightProfile("paper", "Paper score", 1.0, 0.04, 0.015, 0.01, 2.0),
    WeightProfile("t_only", "T-only", 1.0, 0.0, 0.0, 0.0, 0.0),
    WeightProfile("cnot_only", "CNOT-only", 0.0, 1.0, 0.0, 0.0, 0.0),
    WeightProfile("cnot_depth", "CNOT-depth", 0.65, 0.18, 0.08, 0.01, 2.0),
    WeightProfile("balanced", "Balanced", 1.0, 0.10, 0.05, 0.0, 2.0),
    WeightProfile("ancilla_tight", "Ancilla-tight", 1.0, 0.04, 0.015, 0.01, 8.0),
]


INTERNAL_SMALL = ("raw_traditional_resource.csv",)
INTERNAL_ALL = (
    "raw_traditional_resource.csv",
    "raw_highdim_resource.csv",
    "raw_highdim_scale_resource.csv",
    "raw_ultra_highdim_resource.csv",
    "raw_mega_highdim_resource.csv",
)


def budget_filter(name: str) -> Callable[[dict[str, str]], bool]:
    return lambda row: row.get("budget") == name


COMPARISONS = [
    ComparisonSpec(
        "direct_anf",
        "Pareto vs Direct ANF",
        "primary same-task baseline",
        "and_pareto_resource_nmcts",
        "direct_anf",
        INTERNAL_SMALL,
        INTERNAL_SMALL,
        "Direct algebraic expansion is a baseline, not a strong optimized compiler.",
    ),
    ComparisonSpec(
        "esop_milp",
        "Pareto vs ESOP-MILP",
        "primary exact/ILP counterpoint",
        "and_pareto_resource_nmcts",
        "and_esop_milp",
        INTERNAL_SMALL,
        INTERNAL_SMALL,
        "ILP is exact for its ESOP model but not a global quantum-circuit optimum.",
    ),
    ComparisonSpec(
        "sshr_h",
        "Pareto vs SSHR-H",
        "CNOT-oriented SSHR counterpoint",
        "and_pareto_resource_nmcts",
        "sshr_h",
        INTERNAL_SMALL,
        INTERNAL_SMALL,
        "CNOT-only rows are expected to expose SSHR's intended strength.",
    ),
    ComparisonSpec(
        "sshr_i_cnot",
        "Pareto vs SSHR-I CNOT",
        "ILP SSHR CNOT counterpoint",
        "and_pareto_resource_nmcts",
        "external_sshr_i_cnot",
        INTERNAL_SMALL,
        ("raw_external_traditional_resource_n6.csv",),
        "SSHR-I is a CNOT-oriented external result; weighted rows are not CNOT dominance claims.",
    ),
    ComparisonSpec(
        "abc_xag",
        "Pareto vs ABC-XAG",
        "external logic synthesis",
        "and_pareto_resource_nmcts",
        "external_abc_xag",
        INTERNAL_SMALL,
        ("raw_external_traditional_resource_n6.csv",),
        "ABC-XAG is a mature logic-synthesis probe under the same logical cost projection.",
    ),
    ComparisonSpec(
        "ros_best_k",
        "Pareto vs ROS LUT best-K",
        "ROS-style LUT proxy",
        "and_pareto_resource_nmcts",
        "external_ros_lut_proxy",
        INTERNAL_ALL,
        ("raw_ros_lut_proxy_best.csv",),
        "This is a verified LUT proxy, not the official ROS SAT garbage optimizer.",
    ),
    ComparisonSpec(
        "ros_minline",
        "Pareto vs ROS min-line budget",
        "ROS-style garbage-budget proxy",
        "and_pareto_resource_nmcts",
        "external_ros_lut_garbage_budget_minline",
        INTERNAL_ALL,
        ("raw_ros_lut_garbage_budget_frontier.csv",),
        "The min-line budget is a reversible-pebbling proxy over LUT DAGs, not full ROS reproduction.",
        baseline_filter=budget_filter("minline"),
    ),
    ComparisonSpec(
        "revkit_cli",
        "Pareto vs RevKit CLI",
        "exact reversible synthesis probe",
        "and_pareto_resource_nmcts",
        "external_revkit_cli_best_score",
        INTERNAL_SMALL,
        ("raw_revkit_cli_multiflow_traditional.csv",),
        "RevKit exact-oracle rows test a real reversible toolchain but not routed Clifford+T mapping.",
    ),
    ComparisonSpec(
        "mockturtle_xag",
        "Pareto vs mockturtle XAG",
        "external logic synthesis",
        "and_pareto_resource_nmcts",
        "external_mockturtle_xag_k4",
        INTERNAL_SMALL,
        ("raw_mockturtle_xag_probe.csv",),
        "mockturtle is a logic-network probe under the paper's logical resource projection.",
    ),
    ComparisonSpec(
        "caterpillar_api",
        "Pareto vs Caterpillar API",
        "external logic synthesis",
        "and_pareto_resource_nmcts",
        "external_caterpillar_xag_api_best",
        INTERNAL_SMALL,
        ("raw_caterpillar_xag_api_best.csv",),
        "Caterpillar API rows are verified ANF-XAG implementation-family probes, not full ROS or hardware mapping.",
    ),
    ComparisonSpec(
        "cirkit_aig_mc",
        "Pareto vs CirKit AIG/MC",
        "external logic synthesis",
        "and_pareto_resource_nmcts",
        "external_cirkit_aig_mc",
        INTERNAL_SMALL,
        ("raw_cirkit_aig_probe.csv",),
        "CirKit AIG/multiplicative-complexity rows are projected to the same logical resource fields.",
    ),
    ComparisonSpec(
        "n14_root_beam",
        "n=14 Pareto vs root beam",
        "high-dimensional internal counterpoint",
        "and_pareto_resource_nmcts",
        "and_fprm_root_beam",
        ("raw_highdim_resource.csv",),
        ("raw_highdim_resource.csv",),
        "Symbolic high-dimensional evidence, not exhaustive truth-table benchmarking.",
    ),
    ComparisonSpec(
        "n16_root_beam",
        "n=16 Resource vs root beam",
        "high-dimensional internal counterpoint",
        "and_resource_nmcts",
        "and_fprm_root_beam",
        ("raw_ultra_highdim_resource.csv",),
        ("raw_ultra_highdim_resource.csv",),
        "Symbolic high-dimensional evidence, not exhaustive truth-table benchmarking.",
    ),
]

COMPACT_KEYS = [
    "direct_anf",
    "esop_milp",
    "sshr_h",
    "sshr_i_cnot",
    "abc_xag",
    "ros_best_k",
    "ros_minline",
    "revkit_cli",
    "mockturtle_xag",
    "caterpillar_api",
    "cirkit_aig_mc",
    "n14_root_beam",
    "n16_root_beam",
]

COMPACT_PROFILES = ["paper", "t_only", "cnot_only", "cnot_depth", "ancilla_tight"]


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def falsey(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no"}


def usable(row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    for key in (
        "correct",
        "source_blif_correct",
        "verilog_correct",
        "anf_verified",
        "circuit_anf_verified",
        "verified_up_to_global_phase",
        "feasible",
    ):
        if key in row and falsey(row.get(key)):
            return False
    return True


def read_rows(files: tuple[str, ...], method: str, filter_fn: Callable[[dict[str, str]], bool]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in files:
        path = RESULTS / name
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("method") != method:
                    continue
                if not usable(row) or not filter_fn(row):
                    continue
                rows[row["name"]] = row
    return rows


def fnum(row: dict[str, str], key: str) -> float:
    return float(row.get(key) or 0.0)


def weighted_score(row: dict[str, str], profile: WeightProfile) -> float:
    return (
        profile.t * fnum(row, "T")
        + profile.cnot * fnum(row, "CNOT")
        + profile.depth * fnum(row, "depth")
        + profile.gates * fnum(row, "gates")
        + profile.ancilla * fnum(row, "peak_ancilla")
    )


def rel_pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def n_scope(rows: list[dict[str, str]]) -> str:
    values = sorted({int(float(row["n"])) for row in rows if row.get("n")})
    if not values:
        return ""
    ranges: list[str] = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = value
    ranges.append(f"{start}" if start == prev else f"{start}-{prev}")
    return "n=" + ",".join(ranges)


def build_pair_rows() -> list[dict[str, str]]:
    pair_rows: list[dict[str, str]] = []
    for spec in COMPARISONS:
        target = read_rows(spec.target_files, spec.target_method, spec.target_filter)
        baseline = read_rows(spec.baseline_files, spec.baseline_method, spec.baseline_filter)
        names = sorted(set(target) & set(baseline))
        for profile in PROFILES:
            for name in names:
                t_row = target[name]
                b_row = baseline[name]
                t_score = weighted_score(t_row, profile)
                b_score = weighted_score(b_row, profile)
                pair_rows.append(
                    {
                        "comparison_key": spec.key,
                        "comparison": spec.label,
                        "role": spec.role,
                        "profile": profile.key,
                        "profile_label": profile.label,
                        "name": name,
                        "n": t_row.get("n") or b_row.get("n", ""),
                        "target_method": spec.target_method,
                        "baseline_method": spec.baseline_method,
                        "target_weighted_score": f"{t_score:.6f}",
                        "baseline_weighted_score": f"{b_score:.6f}",
                        "relative_pct": f"{rel_pct(t_score, b_score):.6f}",
                        "target_T": t_row.get("T", ""),
                        "baseline_T": b_row.get("T", ""),
                        "target_CNOT": t_row.get("CNOT", ""),
                        "baseline_CNOT": b_row.get("CNOT", ""),
                        "target_depth": t_row.get("depth", ""),
                        "baseline_depth": b_row.get("depth", ""),
                        "target_peak_ancilla": t_row.get("peak_ancilla", ""),
                        "baseline_peak_ancilla": b_row.get("peak_ancilla", ""),
                        "boundary": spec.boundary,
                    }
                )
    return pair_rows


def build_summary_rows(pair_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in pair_rows:
        grouped.setdefault((row["comparison_key"], row["profile"]), []).append(row)

    spec_by_key = {spec.key: spec for spec in COMPARISONS}
    profile_by_key = {profile.key: profile for profile in PROFILES}
    summary: list[dict[str, str]] = []
    profile_order = {profile.key: idx for idx, profile in enumerate(PROFILES)}
    comparison_order = {key: idx for idx, key in enumerate(COMPACT_KEYS)}
    for comparison_key, profile_key in sorted(
        grouped,
        key=lambda item: (
            comparison_order.get(item[0], 999),
            profile_order.get(item[1], 999),
        ),
    ):
        rows = grouped[(comparison_key, profile_key)]
        wins = losses = ties = 0
        relatives: list[float] = []
        for row in rows:
            t = float(row["target_weighted_score"])
            b = float(row["baseline_weighted_score"])
            relatives.append(float(row["relative_pct"]))
            if t < b - 1e-9:
                wins += 1
            elif t > b + 1e-9:
                losses += 1
            else:
                ties += 1
        spec = spec_by_key[comparison_key]
        profile = profile_by_key[profile_key]
        status = "pass" if rows else "needs revision"
        summary.append(
            {
                "comparison_key": comparison_key,
                "comparison": spec.label,
                "role": spec.role,
                "profile": profile.key,
                "profile_label": profile.label,
                "n_scope": n_scope(rows),
                "pairs": str(len(rows)),
                "wins": str(wins),
                "losses": str(losses),
                "ties": str(ties),
                "wlt": f"{wins}/{losses}/{ties}",
                "mean_relative_pct": f"{mean(relatives):.6f}" if relatives else "nan",
                "median_relative_pct": f"{median(relatives):.6f}" if relatives else "nan",
                "status": status,
                "boundary": spec.boundary,
            }
        )
    return summary


def compact_cell(rows: list[dict[str, str]], key: str, profile: str) -> str:
    for row in rows:
        if row["comparison_key"] == key and row["profile"] == profile:
            return f"{row['wlt']}, {float(row['mean_relative_pct']):+.2f}%"
    return "missing"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary_rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in summary_rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Resource-Weight Sensitivity Audit",
        "",
        "This audit recomputes weighted logical-resource scores for matched internal and external baseline rows.",
        "It is post-hoc over verified CSV artifacts; it does not rerun synthesis or change the emitted circuits.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Weight profiles",
            "",
            "| profile | T | CNOT | depth | gates | peak ancilla |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for profile in PROFILES:
        lines.append(
            f"| {profile.label} | {profile.t:g} | {profile.cnot:g} | {profile.depth:g} | {profile.gates:g} | {profile.ancilla:g} |"
        )
    lines.extend(
        [
            "",
            "## Compact rows",
            "",
            "| comparison | role | pairs | Paper | T-only | CNOT-only | CNOT-depth | Ancilla-tight | boundary |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    by_key = {(row["comparison_key"], row["profile"]): row for row in summary_rows}
    for key in COMPACT_KEYS:
        paper = by_key.get((key, "paper"))
        if not paper:
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    paper["comparison"],
                    paper["role"],
                    paper["pairs"],
                    compact_cell(summary_rows, key, "paper"),
                    compact_cell(summary_rows, key, "t_only"),
                    compact_cell(summary_rows, key, "cnot_only"),
                    compact_cell(summary_rows, key, "cnot_depth"),
                    compact_cell(summary_rows, key, "ancilla_tight"),
                    paper["boundary"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Paper-score and T-only profiles test the main non-Clifford-resource claim.",
            "- CNOT-only is included as a deliberate non-dominance check; CNOT-oriented baselines can win there without contradicting the paper's stated claim.",
            "- CNOT-depth and ancilla-tight profiles test whether weighted-score gains disappear when two common secondary resources are emphasized.",
            "- ROS, Caterpillar, and RevKit rows remain proxy/external-toolchain stress tests rather than hardware-mapped or full ROS-reproduction results.",
            "",
            "## Full summary rows",
            "",
            "| comparison | profile | scope | pairs | W/L/T | mean relative | median relative | status |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary_rows:
        lines.append(
            "| {comparison} | {profile_label} | {n_scope} | {pairs} | {wlt} | {mean:+.2f}% | {median:+.2f}% | {status} |".format(
                comparison=row["comparison"],
                profile_label=row["profile_label"],
                n_scope=row["n_scope"],
                pairs=row["pairs"],
                wlt=row["wlt"],
                mean=float(row["mean_relative_pct"]),
                median=float(row["median_relative_pct"]),
                status=row["status"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )
    replacements = [
        ("n=3-6", r"$n=3$--$6$"),
        ("n=14", r"$n=14$"),
        ("n=16", r"$n=16$"),
        ("Pareto", r"Pareto"),
        ("CNOT", r"CNOT"),
        ("T-only", r"T-only"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


LATEX_LABELS = {
    "direct_anf": "Direct ANF",
    "esop_milp": "ESOP-MILP",
    "sshr_h": "SSHR-H",
    "sshr_i_cnot": "SSHR-I",
    "abc_xag": "ABC-XAG",
    "ros_best_k": "ROS best-K",
    "ros_minline": "ROS min-line",
    "revkit_cli": "RevKit",
    "mockturtle_xag": "mockturtle",
    "caterpillar_api": "Caterpillar",
    "cirkit_aig_mc": "CirKit",
    "n14_root_beam": r"$n=14$ root",
    "n16_root_beam": r"$n=16$ root",
}


def latex_compact_cell(rows: list[dict[str, str]], key: str, profile: str) -> str:
    for row in rows:
        if row["comparison_key"] == key and row["profile"] == profile:
            return f"{row['wlt']}; {float(row['mean_relative_pct']):+.1f}\\%"
    return "missing"


def write_latex(path: Path, summary_rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabular}{@{}lrrrrr@{}}",
        r"\toprule",
        r"Baseline & Paper & T-only & CNOT-only & CNOT-depth & Ancilla-tight \\",
        r"\midrule",
    ]
    for key in COMPACT_KEYS:
        paper = next((row for row in summary_rows if row["comparison_key"] == key and row["profile"] == "paper"), None)
        if not paper:
            continue
        lines.append(
            "{} & {} & {} & {} & {} & {} \\\\".format(
                LATEX_LABELS.get(key, latex_escape(paper["comparison"])),
                latex_compact_cell(summary_rows, key, "paper"),
                latex_compact_cell(summary_rows, key, "t_only"),
                latex_compact_cell(summary_rows, key, "cnot_only"),
                latex_compact_cell(summary_rows, key, "cnot_depth"),
                latex_compact_cell(summary_rows, key, "ancilla_tight"),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def paper_has_anchor(path: Path) -> bool:
    return path.exists() and "tab:resource-weight-sensitivity" in path.read_text(encoding="utf-8")


def write_manifest(path: Path, pair_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in summary_rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    profile_keys = [profile.key for profile in PROFILES]
    comparison_keys = [spec.key for spec in COMPARISONS]
    manifest = {
        "name": "resource_weight_sensitivity_audit",
        "raw_rows": len(pair_rows),
        "summary_rows": len(summary_rows),
        "comparisons": comparison_keys,
        "profiles": profile_keys,
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "compact_rows": len(COMPACT_KEYS),
        "table_anchor_present": paper_has_anchor(AUTHOR_PAPER),
        "anonymous_table_anchor_present": paper_has_anchor(ANON_PAPER),
        "acm_table_anchor_present": paper_has_anchor(ACM_PAPER),
        "outputs": [
            str(RAW.relative_to(THIS_DIR)),
            str(SUMMARY.relative_to(THIS_DIR)),
            str(ANALYSIS.relative_to(THIS_DIR)),
            str(TABLE.relative_to(THIS_DIR)),
        ],
        "boundary": "Post-hoc logical-resource sensitivity audit; no hardware mapping, routing, or full external compiler reproduction is claimed.",
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    raise_csv_field_limit()
    pair_rows = build_pair_rows()
    if not pair_rows:
        raise RuntimeError("no matched pair rows")
    summary_rows = build_summary_rows(pair_rows)
    write_csv(RAW, pair_rows)
    write_csv(SUMMARY, summary_rows)
    write_markdown(ANALYSIS, summary_rows)
    write_latex(TABLE, summary_rows)
    write_manifest(MANIFEST, pair_rows, summary_rows)
    print(f"wrote {len(pair_rows)} resource-weight sensitivity pair row(s)")
    print(f"wrote {len(summary_rows)} resource-weight sensitivity summary row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
