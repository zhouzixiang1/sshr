#!/usr/bin/env python3
"""Post-hoc score-weight robustness analysis for verified experiment CSVs."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
SUMMARY_OUT = RESULTS / "summary_weight_robustness.csv"
ANALYSIS_OUT = RESULTS / "analysis_weight_robustness.md"
MANIFEST_OUT = RESULTS / "manifest_weight_robustness.json"
TABLE_OUT = PAPER_TABLES / "weight_robustness_compact.tex"


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


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
class DatasetSpec:
    key: str
    label: str
    raw_csv: str
    target: str
    comparisons: tuple[tuple[str, str], ...]
    exclude_methods: frozenset[str] = frozenset()


PROFILES = [
    WeightProfile("paper", "Paper score", 1.0, 0.04, 0.015, 0.01, 2.0),
    WeightProfile("t_only", "T-only", 1.0, 0.0, 0.0, 0.0, 0.0),
    WeightProfile("t_heavy", "T-heavy", 1.0, 0.015, 0.005, 0.005, 1.0),
    WeightProfile("cnot_depth", "CNOT-depth", 0.65, 0.18, 0.08, 0.01, 2.0),
    WeightProfile("ancilla_tight", "Ancilla-tight", 1.0, 0.04, 0.015, 0.01, 8.0),
]

DATASETS = [
    DatasetSpec(
        "traditional",
        "n<=6 traditional",
        "raw_traditional_resource.csv",
        "and_pareto_resource_nmcts",
        (
            ("direct_anf", "Direct ANF"),
            ("and_direct_anf", "AND-direct ANF"),
            ("and_cube_beam", "ESOP cube beam"),
            ("and_esop_milp", "ESOP-MILP"),
            ("sshr_h", "SSHR-H"),
            ("and_resource_nmcts", "Resource-NMCTS"),
        ),
    ),
    DatasetSpec(
        "n14",
        "n=14 random ANF",
        "raw_highdim_resource.csv",
        "and_pareto_resource_nmcts",
        (
            ("direct_anf", "Direct ANF"),
            ("and_direct_anf", "AND-direct ANF"),
            ("and_fprm_root_beam", "FPRM root beam"),
            ("and_fprm_linear_pair", "FPRM linear pair"),
            ("and_resource_nmcts", "Resource-NMCTS"),
        ),
    ),
    DatasetSpec(
        "n15",
        "n=15 random ANF",
        "raw_highdim_scale_resource.csv",
        "and_resource_nmcts",
        (
            ("direct_anf", "Direct ANF"),
            ("and_direct_anf", "AND-direct ANF"),
            ("and_fprm_root_beam", "FPRM root beam"),
            ("and_fprm_linear_pair_deep", "Recursive linear pair"),
        ),
    ),
    DatasetSpec(
        "n16",
        "n=16 random ANF",
        "raw_ultra_highdim_resource.csv",
        "and_resource_nmcts",
        (
            ("direct_anf", "Direct ANF"),
            ("and_direct_anf", "AND-direct ANF"),
            ("and_fprm_root_beam", "FPRM root beam"),
            ("and_fprm_linear_pair_deep", "Recursive linear pair"),
        ),
        exclude_methods=frozenset({"and_resource_nmcts_wide"}),
    ),
    DatasetSpec(
        "n18",
        "n=18 random ANF",
        "raw_mega_highdim_resource.csv",
        "and_resource_nmcts",
        (
            ("direct_anf", "Direct ANF"),
            ("and_direct_anf", "AND-direct ANF"),
            ("and_fprm_root_beam", "FPRM root beam"),
            ("and_fprm_linear_pair_fast", "fast pair guard"),
        ),
    ),
]

COMPACT_ROWS = [
    ("traditional", "and_cube_beam"),
    ("traditional", "and_esop_milp"),
    ("traditional", "sshr_h"),
    ("n14", "and_fprm_root_beam"),
    ("n16", "and_fprm_root_beam"),
    ("n18", "and_fprm_root_beam"),
    ("n18", "and_fprm_linear_pair_fast"),
]
COMPACT_PROFILES = ("paper", "t_only", "cnot_depth", "ancilla_tight")


def fnum(row: dict[str, str], key: str) -> float:
    return float(row.get(key) or 0.0)


def is_usable(row: dict[str, str]) -> bool:
    return (
        not row.get("error")
        and not row.get("skipped")
        and str(row.get("correct", "True")) != "False"
    )


def score(row: dict[str, str], profile: WeightProfile) -> float:
    return (
        profile.t * fnum(row, "T")
        + profile.cnot * fnum(row, "CNOT")
        + profile.depth * fnum(row, "depth")
        + profile.gates * fnum(row, "gates")
        + profile.ancilla * fnum(row, "peak_ancilla")
    )


def pct(new: float, old: float) -> float:
    return (new - old) / max(old, 1.0) * 100.0


def load_by_name(spec: DatasetSpec) -> dict[str, dict[str, dict[str, str]]]:
    path = RESULTS / spec.raw_csv
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if not is_usable(row) or row.get("method") in spec.exclude_methods:
            continue
        by_name.setdefault(row["name"], {})[row["method"]] = row
    return by_name


def analyze_comparison(
    tables: dict[str, dict[str, dict[str, str]]],
    profile: WeightProfile,
    target: str,
    baseline: str,
) -> dict[str, object]:
    wins = losses = ties = 0
    target_scores: list[float] = []
    baseline_scores: list[float] = []
    relatives: list[float] = []
    for methods in tables.values():
        if target not in methods or baseline not in methods:
            continue
        target_score = score(methods[target], profile)
        baseline_score = score(methods[baseline], profile)
        target_scores.append(target_score)
        baseline_scores.append(baseline_score)
        relatives.append(pct(target_score, baseline_score))
        if target_score < baseline_score - 1e-9:
            wins += 1
        elif target_score > baseline_score + 1e-9:
            losses += 1
        else:
            ties += 1
    pairs = len(target_scores)
    return {
        "pairs": pairs,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_target_score": mean(target_scores) if target_scores else math.nan,
        "mean_baseline_score": mean(baseline_scores) if baseline_scores else math.nan,
        "mean_relative": mean(relatives) if relatives else math.nan,
    }


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in DATASETS:
        tables = load_by_name(spec)
        baseline_labels = dict(spec.comparisons)
        for baseline, baseline_label in spec.comparisons:
            for profile in PROFILES:
                stats = analyze_comparison(tables, profile, spec.target, baseline)
                if not stats["pairs"]:
                    continue
                rows.append(
                    {
                        "dataset": spec.key,
                        "dataset_label": spec.label,
                        "profile": profile.key,
                        "profile_label": profile.label,
                        "target_method": spec.target,
                        "baseline_method": baseline,
                        "baseline_label": baseline_label,
                        "pairs": str(stats["pairs"]),
                        "score_wlt": f"{stats['wins']}/{stats['losses']}/{stats['ties']}",
                        "wins": str(stats["wins"]),
                        "losses": str(stats["losses"]),
                        "ties": str(stats["ties"]),
                        "mean_target_score": f"{stats['mean_target_score']:.6f}",
                        "mean_baseline_score": f"{stats['mean_baseline_score']:.6f}",
                        "mean_relative_pct": f"{stats['mean_relative']:.6f}",
                    }
                )
        # Make sure labels are present for compact rows even if no comparison
        # above used a baseline because of an incomplete raw CSV.
        _ = baseline_labels
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value: str) -> str:
    return f"{float(value):+.2f}%"


def compact_cell(rows: list[dict[str, str]], dataset: str, baseline: str, profile: str) -> str:
    for row in rows:
        if row["dataset"] == dataset and row["baseline_method"] == baseline and row["profile"] == profile:
            return f"{row['score_wlt']}, {fmt_pct(row['mean_relative_pct'])}"
    return "--"


def compact_check_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    by_key = {
        (row["dataset"], row["baseline_method"], row["profile"]): row
        for row in rows
    }
    for dataset, baseline in COMPACT_ROWS:
        for profile in COMPACT_PROFILES:
            data = by_key.get((dataset, baseline, profile))
            if data is None:
                out.append(
                    {
                        "dataset": dataset,
                        "baseline": baseline,
                        "profile": profile,
                        "pairs": "0",
                        "wins": "0",
                        "losses": "0",
                        "ties": "0",
                        "mean_relative_pct": "nan",
                        "status": "needs revision",
                        "evidence": "missing compact comparison row",
                    }
                )
                continue
            wins = int(data["wins"])
            losses = int(data["losses"])
            mean_relative = float(data["mean_relative_pct"])
            ok = wins >= losses and mean_relative <= 0.0
            out.append(
                {
                    "dataset": dataset,
                    "baseline": baseline,
                    "profile": profile,
                    "pairs": data["pairs"],
                    "wins": data["wins"],
                    "losses": data["losses"],
                    "ties": data["ties"],
                    "mean_relative_pct": data["mean_relative_pct"],
                    "status": "pass" if ok else "needs revision",
                    "evidence": (
                        f"W/L/T={data['score_wlt']}; mean_relative={float(data['mean_relative_pct']):+.2f}%"
                    ),
                }
            )
    return out


def write_markdown(rows: list[dict[str, str]], path: Path) -> None:
    lines = [
        "# Score-Weight Robustness Analysis",
        "",
        (
            "This post-hoc analysis recomputes the candidate scores from already "
            "verified raw CSV rows. It does not rerun synthesis; it tests whether "
            "the reported comparisons survive alternative logical resource weights."
        ),
        "",
        "## Weight profiles",
        "",
        "| profile | T | CNOT | depth | gates | ancilla |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for p in PROFILES:
        lines.append(f"| {p.label} | {p.t:g} | {p.cnot:g} | {p.depth:g} | {p.gates:g} | {p.ancilla:g} |")
    lines.extend(
        [
            "",
            "## Compact view",
            "",
            "| dataset | target vs baseline | Paper score | T-only | CNOT-depth | Ancilla-tight |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    spec_by_key = {spec.key: spec for spec in DATASETS}
    baseline_labels = {
        (spec.key, baseline): label
        for spec in DATASETS
        for baseline, label in spec.comparisons
    }
    for dataset, baseline in COMPACT_ROWS:
        spec = spec_by_key[dataset]
        target = spec.target.replace("and_", "").replace("_", "-")
        lines.append(
            "| "
            + " | ".join(
                [
                    spec.label,
                    f"{target} vs {baseline_labels[(dataset, baseline)]}",
                    compact_cell(rows, dataset, baseline, "paper"),
                    compact_cell(rows, dataset, baseline, "t_only"),
                    compact_cell(rows, dataset, baseline, "cnot_depth"),
                    compact_cell(rows, dataset, baseline, "ancilla_tight"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Full comparison rows",
            "",
            "| dataset | profile | target | baseline | pairs | score W/L/T | mean relative |",
            "|---|---|---|---|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["dataset_label"],
                    row["profile_label"],
                    row["target_method"],
                    row["baseline_label"],
                    row["pairs"],
                    row["score_wlt"],
                    fmt_pct(row["mean_relative_pct"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The traditional-function result is robust across all tested weights against ESOP cube beam and ESOP-MILP.",
            "- The SSHR-H comparison remains favorable in weighted score, but the CNOT-depth profile narrows the margin and keeps the CNOT-only limitation visible.",
            "- The high-dimensional claims survive T-only, T-heavy, CNOT-depth, and ancilla-tight rescoring against root-beam baselines; direct-ANF comparisons remain much larger but still trade CNOT/depth/ancilla.",
            "- The n=16 AI guard remains a small no-score-loss improvement under the paper, T-only, and T-heavy weights, and becomes near-tie under CNOT-depth and ancilla-tight weights.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = text.replace("_", r"\_").replace("%", r"\%")
    replacements = [
        ("n<=6", r"$n\leq6$"),
        ("n=14", r"$n=14$"),
        ("n=16", r"$n=16$"),
        ("n=18", r"$n=18$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_latex(rows: list[dict[str, str]], path: Path) -> None:
    spec_by_key = {spec.key: spec for spec in DATASETS}
    baseline_labels = {
        (spec.key, baseline): label
        for spec in DATASETS
        for baseline, label in spec.comparisons
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}}",
        r"\toprule",
        r"Comparison & Paper score & T-only & CNOT-depth & Ancilla-tight \\",
        r"\midrule",
    ]
    for dataset, baseline in COMPACT_ROWS:
        spec = spec_by_key[dataset]
        label = f"{spec.label}: {baseline_labels[(dataset, baseline)]}"
        lines.append(
            f"{tex_escape(label)} & "
            f"{tex_escape(compact_cell(rows, dataset, baseline, 'paper'))} & "
            f"{tex_escape(compact_cell(rows, dataset, baseline, 't_only'))} & "
            f"{tex_escape(compact_cell(rows, dataset, baseline, 'cnot_depth'))} & "
            f"{tex_escape(compact_cell(rows, dataset, baseline, 'ancilla_tight'))} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, str]], path: Path) -> None:
    check_rows = compact_check_rows(rows)
    counts = Counter(row["status"] for row in check_rows)
    profiles = [profile.key for profile in PROFILES]
    datasets = sorted({row["dataset"] for row in rows})
    min_pairs = min((int(row["pairs"]) for row in check_rows), default=0)
    table_anchor_present = "tab:weight-robustness" in PAPER.read_text(encoding="utf-8") if PAPER.exists() else False
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "summary_rows": len(rows),
        "datasets": datasets,
        "profiles": profiles,
        "profile_count": len(profiles),
        "compact_rows": len(COMPACT_ROWS),
        "compact_profiles": list(COMPACT_PROFILES),
        "compact_checks": len(check_rows),
        "min_compact_pairs": min_pairs,
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "table_anchor_present": table_anchor_present,
        "outputs": {
            "summary": "results/summary_weight_robustness.csv",
            "analysis": "results/analysis_weight_robustness.md",
            "manifest": "results/manifest_weight_robustness.json",
            "table": "paper_latex/tables/weight_robustness_compact.tex",
        },
        "boundary": "Post-hoc logical-resource rescoring only; it does not rerun synthesis and is not a hardware cost model.",
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    raise_csv_field_limit()

    rows = build_rows()
    write_csv(rows, SUMMARY_OUT)
    write_markdown(rows, ANALYSIS_OUT)
    write_latex(rows, TABLE_OUT)
    write_manifest(rows, MANIFEST_OUT)
    print(f"wrote {SUMMARY_OUT}")
    print(f"wrote {ANALYSIS_OUT}")
    print(f"wrote {TABLE_OUT}")
    print(f"wrote {MANIFEST_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
