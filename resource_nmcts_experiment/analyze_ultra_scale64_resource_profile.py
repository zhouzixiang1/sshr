#!/usr/bin/env python3
"""Summarize multi-resource profiles for the n=48/56/64 stress slice."""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

RAW = RESULTS / "raw_screen_scale_ultra_scale64_terms.csv"
SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_resource_profile.csv"
DELTA_SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_resource_deltas.csv"
ANALYSIS = RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md"
MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json"
LATEX = TABLES / "screen_scale_ultra_scale64_resource_profile.tex"

NS = ("48", "56", "64")
SELECTED_METHODS = (
    "direct_logical_and",
    "screen_depth2",
    "screen_depth4",
    "adaptive_all_depth",
    "depth_frontier_policy",
)
PAIRINGS = (
    ("screen_depth4", "screen_depth2", "deterministic depth-4 gain"),
    ("depth_frontier_policy", "screen_depth2", "learned frontier vs cheap depth-2"),
    ("depth_frontier_policy", "adaptive_all_depth", "learned frontier vs full frontier"),
)
RESOURCE_COLUMNS = (
    ("score", "mean_score"),
    ("T", "mean_T"),
    ("CNOT", "mean_CNOT"),
    ("depth", "mean_depth"),
    ("gates", "mean_gates"),
    ("peak_ancilla", "mean_peak_ancilla"),
    ("schedule_t_depth_proxy", "mean_t_depth_proxy"),
    ("explicit_ancilla_lifetime_area", "mean_ancilla_lifetime"),
    ("time_s", "mean_time_s"),
)

LABELS = {
    "direct_logical_and": "Direct AND",
    "screen_depth2": "Depth-2 screen",
    "screen_depth4": "Depth-4 screen",
    "adaptive_all_depth": "All-depth frontier",
    "depth_frontier_policy": "Learned frontier",
}


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_rows() -> list[dict[str, str]]:
    with RAW.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def mean_float(rows: list[dict[str, str]], key: str) -> float:
    return statistics.mean(float(row[key]) for row in rows)


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def rel_pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def scoped(rows: list[dict[str, str]], n_scope: str) -> list[dict[str, str]]:
    if n_scope == "all":
        return rows
    return [row for row in rows if row["n"] == n_scope]


def profile_row(rows: list[dict[str, str]], n_scope: str, method: str) -> dict[str, str]:
    method_rows = [row for row in scoped(rows, n_scope) if row["method"] == method]
    out = {
        "scope": "n=48/56/64" if n_scope == "all" else f"n={n_scope}",
        "method": method,
        "label": LABELS.get(method, method),
        "rows": str(len(method_rows)),
        "verified_rows": str(sum(1 for row in method_rows if truthy(row.get("anf_verified")) and truthy(row.get("circuit_anf_verified")))),
    }
    for source, target in RESOURCE_COLUMNS:
        out[target] = fmt(mean_float(method_rows, source), 4 if source == "peak_ancilla" else 2) if method_rows else ""
    return out


def build_profiles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    scopes = ("all",) + NS
    return [profile_row(rows, scope, method) for scope in scopes for method in SELECTED_METHODS]


def indexed(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["name"], row["method"]): row for row in rows}


def delta_row(rows: list[dict[str, str]], n_scope: str, target_method: str, baseline_method: str, role: str) -> dict[str, str]:
    index = indexed(rows)
    names = sorted({row["name"] for row in scoped(rows, n_scope)})
    wins = losses = ties = 0
    deltas: dict[str, list[float]] = {source: [] for source, _ in RESOURCE_COLUMNS}
    for name in names:
        target = index.get((name, target_method))
        baseline = index.get((name, baseline_method))
        if target is None or baseline is None:
            continue
        target_score = float(target["score"])
        baseline_score = float(baseline["score"])
        if target_score < baseline_score - 1e-9:
            wins += 1
        elif target_score > baseline_score + 1e-9:
            losses += 1
        else:
            ties += 1
        for source, _ in RESOURCE_COLUMNS:
            deltas[source].append(rel_pct(float(target[source]), float(baseline[source])))
    out = {
        "scope": "n=48/56/64" if n_scope == "all" else f"n={n_scope}",
        "target": target_method,
        "baseline": baseline_method,
        "target_label": LABELS.get(target_method, target_method),
        "baseline_label": LABELS.get(baseline_method, baseline_method),
        "role": role,
        "pairs": str(wins + losses + ties),
        "score_wlt": f"{wins}/{losses}/{ties}",
    }
    for source, _ in RESOURCE_COLUMNS:
        out[f"mean_delta_{source}_pct"] = f"{statistics.mean(deltas[source]):+.2f}" if deltas[source] else ""
    return out


def build_deltas(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    scopes = ("all",) + NS
    return [
        delta_row(rows, scope, target, baseline, role)
        for scope in scopes
        for target, baseline, role in PAIRINGS
    ]


def verification(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "raw_rows": len(rows),
        "functions": len({row["name"] for row in rows}),
        "n_values": sorted({row["n"] for row in rows}),
        "methods": sorted({row["method"] for row in rows}),
        "plan_verified_rows": sum(1 for row in rows if truthy(row.get("anf_verified"))),
        "circuit_verified_rows": sum(1 for row in rows if truthy(row.get("circuit_anf_verified"))),
        "max_plan_mismatches": max((int(float(row.get("plan_mismatches") or 0)) for row in rows), default=0),
        "max_circuit_mismatches": max((int(float(row.get("circuit_mismatches") or 0)) for row in rows), default=0),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(profiles: list[dict[str, str]], deltas: list[dict[str, str]], meta: dict[str, object]) -> None:
    overall_profiles = [row for row in profiles if row["scope"] == "n=48/56/64"]
    overall_deltas = [row for row in deltas if row["scope"] == "n=48/56/64"]
    lines = [
        "# Ultra-Scale n=48/56/64 Resource Profile",
        "",
        "This derived audit expands the ultra-scale stress slice from score/time comparisons into raw logical resource means.",
        "It reuses the verified term-set rows and does not rerun synthesis.",
        "",
        "## Verification",
        "",
        f"- raw rows: {meta['raw_rows']}",
        f"- functions: {meta['functions']}",
        f"- n values: {', '.join(meta['n_values'])}",
        f"- plan ANF verified rows: {meta['plan_verified_rows']}/{meta['raw_rows']}",
        f"- emitted-circuit ANF verified rows: {meta['circuit_verified_rows']}/{meta['raw_rows']}",
        f"- max plan mismatches: {meta['max_plan_mismatches']}",
        f"- max circuit mismatches: {meta['max_circuit_mismatches']}",
        "",
        "## Overall Method Means",
        "",
        "| method | rows | score | T | CNOT | depth | peak ancilla | T-depth proxy | ancilla lifetime | time s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in overall_profiles:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["label"],
                    row["rows"],
                    row["mean_score"],
                    row["mean_T"],
                    row["mean_CNOT"],
                    row["mean_depth"],
                    row["mean_peak_ancilla"],
                    row["mean_t_depth_proxy"],
                    row["mean_ancilla_lifetime"],
                    row["mean_time_s"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Overall Pairwise Deltas",
            "",
            "| target | baseline | pairs | score W/L/T | score | T | CNOT | depth | T-depth | ancilla lifetime | time |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in overall_deltas:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["target_label"],
                    row["baseline_label"],
                    row["pairs"],
                    row["score_wlt"],
                    row["mean_delta_score_pct"] + "%",
                    row["mean_delta_T_pct"] + "%",
                    row["mean_delta_CNOT_pct"] + "%",
                    row["mean_delta_depth_pct"] + "%",
                    row["mean_delta_schedule_t_depth_proxy_pct"] + "%",
                    row["mean_delta_explicit_ancilla_lifetime_area_pct"] + "%",
                    row["mean_delta_time_s_pct"] + "%",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Depth-4 and all-depth screens lower T-count, CNOT, logical depth, and T-depth proxy relative to the cheap depth-2 screen, but they substantially increase planning time and auxiliary lifetime.",
            "- The learned frontier sits between cheap depth-2 and the all-depth ceiling: it improves resource means over depth-2, saves time against all-depth, and accepts a small resource gap to the full frontier.",
            "- This makes the ultra-scale result a resource-frontier and budget-control claim, not a single-metric or hardware-mapped dominance claim.",
        ]
    )
    ANALYSIS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(profiles: list[dict[str, str]]) -> None:
    rows = [row for row in profiles if row["scope"] == "n=48/56/64"]
    lines = [
        r"\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrrrrrr}",
        r"\toprule",
        r"Method & Score & T & CNOT & Depth & Anc. & T-depth & Anc.-life & Time(s) \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    row["label"],
                    f"{float(row['mean_score']):.1f}",
                    f"{float(row['mean_T']):.1f}",
                    f"{float(row['mean_CNOT']):.1f}",
                    f"{float(row['mean_depth']):.1f}",
                    f"{float(row['mean_peak_ancilla']):.2f}",
                    f"{float(row['mean_t_depth_proxy']):.1f}",
                    f"{float(row['mean_ancilla_lifetime']):.1f}",
                    f"{float(row['mean_time_s']):.2f}",
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular*}"])
    LATEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(profiles: list[dict[str, str]], deltas: list[dict[str, str]], meta: dict[str, object]) -> None:
    expected_profile_rows = len(SELECTED_METHODS) * (1 + len(NS))
    expected_delta_rows = len(PAIRINGS) * (1 + len(NS))
    ok = (
        meta["raw_rows"] == 480
        and meta["functions"] == 48
        and meta["plan_verified_rows"] == 480
        and meta["circuit_verified_rows"] == 480
        and meta["max_plan_mismatches"] == 0
        and meta["max_circuit_mismatches"] == 0
        and tuple(meta["n_values"]) == NS
        and len(profiles) == expected_profile_rows
        and len(deltas) == expected_delta_rows
        and LATEX.exists()
    )
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "raw": rel(RAW),
        "summary": rel(SUMMARY),
        "delta_summary": rel(DELTA_SUMMARY),
        "analysis": rel(ANALYSIS),
        "table": rel(LATEX),
        "profile_rows": len(profiles),
        "delta_rows": len(deltas),
        "selected_methods": list(SELECTED_METHODS),
        "pairings": [list(item) for item in PAIRINGS],
        "needs_revision_count": 0 if ok else 1,
        "status_counts": {"pass": len(profiles) + len(deltas)} if ok else {"needs revision": len(profiles) + len(deltas)},
        **meta,
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = read_rows()
    profiles = build_profiles(rows)
    deltas = build_deltas(rows)
    meta = verification(rows)
    write_csv(SUMMARY, profiles)
    write_csv(DELTA_SUMMARY, deltas)
    write_markdown(profiles, deltas, meta)
    write_latex(profiles)
    write_manifest(profiles, deltas, meta)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(DELTA_SUMMARY)}")
    print(f"wrote {rel(ANALYSIS)}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(LATEX)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
