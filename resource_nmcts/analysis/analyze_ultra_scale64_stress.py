#!/usr/bin/env python3
"""Audit the n=48/56/64 ultra-scale Boolean term-set stress slice."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

RAW = RESULTS / "raw_screen_scale_ultra_scale64_terms.csv"
SUMMARY = RESULTS / "summary_screen_scale_ultra_scale64_stress.csv"
ANALYSIS = RESULTS / "analysis_screen_scale_ultra_scale64_stress.md"
MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_stress.json"
LATEX = TABLES / "screen_scale_ultra_scale64_stress.tex"

NS = ("48", "56", "64")
METHODS = (
    "direct_logical_and",
    "screen_single",
    "screen_depth1",
    "screen_depth2",
    "screen_depth3",
    "screen_depth4",
    "adaptive_all_depth",
    "depth_policy",
    "depth_frontier_policy",
    "depth2_guard_direct",
)
COMPARISONS = (
    ("screen_depth4", "screen_depth2", "deterministic deep screen"),
    ("adaptive_all_depth", "screen_depth2", "quality ceiling"),
    ("depth_frontier_policy", "screen_depth2", "learned frontier vs cheap depth-2"),
    ("depth_frontier_policy", "screen_depth4", "learned frontier vs deepest screen"),
    ("depth_frontier_policy", "adaptive_all_depth", "learned frontier vs full measured frontier"),
)


def read_rows() -> list[dict[str, str]]:
    with RAW.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def rel_pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0) * 100.0


def by_name_method(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["name"], row["method"]): row for row in rows}


def compare(
    rows: list[dict[str, str]],
    target_method: str,
    baseline_method: str,
    n_scope: str,
    role: str,
) -> dict[str, str]:
    indexed = by_name_method(rows)
    names = sorted({row["name"] for row in rows if n_scope == "all" or row["n"] == n_scope})
    wins = losses = ties = 0
    score_delta: list[float] = []
    time_delta: list[float] = []
    t_delta: list[float] = []
    target_scores: list[float] = []
    baseline_scores: list[float] = []
    for name in names:
        target = indexed.get((name, target_method))
        baseline = indexed.get((name, baseline_method))
        if target is None or baseline is None:
            continue
        target_score = float(target["score"])
        baseline_score = float(baseline["score"])
        target_scores.append(target_score)
        baseline_scores.append(baseline_score)
        score_delta.append(rel_pct(target_score, baseline_score))
        time_delta.append(rel_pct(float(target["time_s"]), float(baseline["time_s"])))
        t_delta.append(rel_pct(float(target["T"]), float(baseline["T"])))
        if target_score < baseline_score - 1e-9:
            wins += 1
        elif target_score > baseline_score + 1e-9:
            losses += 1
        else:
            ties += 1
    return {
        "scope": "n=48/56/64" if n_scope == "all" else f"n={n_scope}",
        "target": target_method,
        "baseline": baseline_method,
        "role": role,
        "pairs": str(wins + losses + ties),
        "score_wlt": f"{wins}/{losses}/{ties}",
        "mean_score_delta_pct": f"{statistics.mean(score_delta):+.2f}" if score_delta else "",
        "median_score_delta_pct": f"{statistics.median(score_delta):+.2f}" if score_delta else "",
        "mean_time_delta_pct": f"{statistics.mean(time_delta):+.2f}" if time_delta else "",
        "mean_t_delta_pct": f"{statistics.mean(t_delta):+.2f}" if t_delta else "",
        "mean_target_score": f"{statistics.mean(target_scores):.2f}" if target_scores else "",
        "mean_baseline_score": f"{statistics.mean(baseline_scores):.2f}" if baseline_scores else "",
    }


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for target, baseline, role in COMPARISONS:
        out.append(compare(rows, target, baseline, "all", role))
    for n in NS:
        out.append(compare(rows, "depth_frontier_policy", "adaptive_all_depth", n, "per-n learned boundary"))
        out.append(compare(rows, "screen_depth4", "screen_depth2", n, "per-n deterministic depth gain"))
    return out


def verification(rows: list[dict[str, str]]) -> dict[str, object]:
    plan_pass = sum(1 for row in rows if truthy(row.get("anf_verified")))
    circuit_pass = sum(1 for row in rows if truthy(row.get("circuit_anf_verified")))
    max_plan_mismatch = max((int(float(row.get("plan_mismatches") or 0)) for row in rows), default=0)
    max_circuit_mismatch = max((int(float(row.get("circuit_mismatches") or 0)) for row in rows), default=0)
    max_wire_terms = max((int(float(row.get("circuit_max_wire_terms") or 0)) for row in rows), default=0)
    return {
        "raw_rows": len(rows),
        "plan_verified_rows": plan_pass,
        "circuit_verified_rows": circuit_pass,
        "max_plan_mismatches": max_plan_mismatch,
        "max_circuit_mismatches": max_circuit_mismatch,
        "max_circuit_max_wire_terms": max_wire_terms,
        "n_values": sorted({row["n"] for row in rows}),
        "methods": sorted({row["method"] for row in rows}),
        "functions": len({row["name"] for row in rows}),
    }


def write_csv(rows: list[dict[str, str]]) -> None:
    fields = list(rows[0].keys())
    with SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], meta: dict[str, object]) -> None:
    lines = [
        "# Ultra-Scale n=48/56/64 Stress Audit",
        "",
        "This audit checks the newly generated term-set stress slice beyond the main n=20--40 envelope.",
        "It remains a logical-layer symbolic test: no truth-table enumeration or hardware mapping is claimed.",
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
        f"- max circuit wire terms: {meta['max_circuit_max_wire_terms']}",
        "",
        "## Comparisons",
        "",
        "| scope | target | baseline | role | pairs | score W/L/T | mean score | mean time | mean T |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["scope"],
                    row["target"],
                    row["baseline"],
                    row["role"],
                    row["pairs"],
                    row["score_wlt"],
                    row["mean_score_delta_pct"] + "%",
                    row["mean_time_delta_pct"] + "%",
                    row["mean_t_delta_pct"] + "%",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Depth-4 and all-depth screens still reduce score relative to cheap depth-2 on many ultra-scale rows, but their planning cost is much higher.",
            "- The learned depth-frontier policy is a bounded budget controller: it saves time against the full measured frontier, while accepting a small score gap on this harder n=48--64 slice.",
            "- These rows extend the symbolic verification envelope; they do not replace complete truth-table bridge checks.",
        ]
    )
    ANALYSIS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    if text == "n=48/56/64":
        return r"$n=48,56,64$"
    if text in {"n=48", "n=56", "n=64"}:
        return f"${text}$"
    return text.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def write_latex(rows: list[dict[str, str]]) -> None:
    selected = [row for row in rows if row["scope"] == "n=48/56/64"] + [
        row
        for row in rows
        if row["role"] == "per-n learned boundary"
    ]
    labels = {
        "screen_depth2": "depth-2 screen",
        "screen_depth4": "depth-4 screen",
        "adaptive_all_depth": "all-depth frontier",
        "depth_frontier_policy": "learned frontier",
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedleft\arraybackslash}p{0.11\linewidth}>{\raggedleft\arraybackslash}p{0.10\linewidth}>{\raggedleft\arraybackslash}X}",
        r"\toprule",
        r"Scope & Target & Baseline & W/L/T & $\Delta$ score & $\Delta$ time \\",
        r"\midrule",
    ]
    for row in selected:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["scope"]),
                    tex_escape(labels.get(row["target"], row["target"])),
                    tex_escape(labels.get(row["baseline"], row["baseline"])),
                    tex_escape(row["score_wlt"]),
                    tex_escape(row["mean_score_delta_pct"] + "%"),
                    tex_escape(row["mean_time_delta_pct"] + "%"),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    LATEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, str]], meta: dict[str, object]) -> None:
    ok = (
        meta["raw_rows"] == 480
        and meta["plan_verified_rows"] == 480
        and meta["circuit_verified_rows"] == 480
        and meta["max_plan_mismatches"] == 0
        and meta["max_circuit_mismatches"] == 0
        and tuple(meta["n_values"]) == NS
        and tuple(meta["methods"]) == tuple(sorted(METHODS))
    )
    manifest = {
        "script": Path(__file__).name,
        "raw": str(RAW.relative_to(THIS_DIR)),
        "summary": str(SUMMARY.relative_to(THIS_DIR)),
        "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
        "table": str(LATEX.relative_to(THIS_DIR)),
        "rows": len(rows),
        "needs_revision_count": 0 if ok else 1,
        "status_counts": {"pass": len(rows)} if ok else {"needs revision": len(rows)},
        **meta,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = read_rows()
    summary = build_summary(rows)
    meta = verification(rows)
    write_csv(summary)
    write_markdown(summary, meta)
    write_latex(summary)
    write_manifest(summary, meta)
    print(f"wrote {SUMMARY}")
    print(f"wrote {ANALYSIS}")
    print(f"wrote {MANIFEST}")
    print(f"wrote {LATEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
