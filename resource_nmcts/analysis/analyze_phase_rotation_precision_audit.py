#!/usr/bin/env python3
"""Precision-sensitive phase/Rz rotation-cost audit.

The phase-search branch already reports a fixed ``T/Rz=30`` synthesis proxy.
This audit freezes the existing verified phase candidates and recomputes their
logical score under several approximation precisions.  It uses the standard
Ross--Selinger-style asymptotic estimate ``T(Rz, eps)=ceil(3 log2(1/eps))`` per
non-Clifford Z rotation as a sensitivity model.

This is still not rotation-sequence synthesis, physical mapping, routing, or a
hardware claim.  It is a reproducible logical-layer stress test for whether the
phase-search conclusions depend on the single fixed ``T/Rz=30`` constant.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

EPSILONS = (1e-3, 1e-6, 1e-9, 1e-12)

TRADITIONAL_SOURCES = {
    "RevKit oracle_synth": RESULTS / "raw_revkit_oracle_synth_traditional.csv",
    "Phase ANF": RESULTS / "raw_phase_parity_anf.csv",
    "FPRM": RESULTS / "raw_phase_parity_fprm.csv",
    "Affine-32": RESULTS / "raw_phase_parity_affine.csv",
    "Affine-128": RESULTS / "raw_phase_parity_affine_wide128.csv",
}

POLICY_SOURCE = RESULTS / "raw_phase_affine_policy_rank_diverse.csv"
POLICY_METHODS = {
    "Budget-32": "phase_affine_budget32_tperrz30",
    "Wide-128": "phase_affine_wide128_tperrz30",
    "Diverse-256": "phase_parity_affine_policy_diverse_tperrz30_top256",
    "Diverse-512": "phase_parity_affine_policy_diverse_tperrz30_top512",
}

SELECTED_TABLE_ROWS = {
    ("traditional", "Affine-128", "RevKit oracle_synth", 1e-3),
    ("traditional", "Affine-128", "RevKit oracle_synth", 1e-6),
    ("traditional", "Affine-128", "RevKit oracle_synth", 1e-9),
    ("traditional", "Affine-128", "Affine-32", 1e-6),
    ("policy", "Diverse-512", "Budget-32", 1e-6),
    ("policy", "Diverse-512", "Wide-128", 1e-6),
    ("policy", "Diverse-256", "Wide-128", 1e-6),
    ("policy", "Diverse-512", "Wide-128", 1e-9),
}


@dataclass(frozen=True)
class Comparison:
    scope: str
    target: str
    baseline: str


COMPARISONS = (
    Comparison("traditional", "Affine-128", "RevKit oracle_synth"),
    Comparison("traditional", "Affine-128", "Phase ANF"),
    Comparison("traditional", "Affine-128", "FPRM"),
    Comparison("traditional", "Affine-128", "Affine-32"),
    Comparison("policy", "Diverse-512", "Budget-32"),
    Comparison("policy", "Diverse-512", "Wide-128"),
    Comparison("policy", "Diverse-256", "Wide-128"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    if not row.get("score"):
        return False
    verified = str(row.get("verified_up_to_global_phase", "")).strip().lower()
    if verified in {"false", "0"}:
        return False
    return True


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in {"", None}:
        return default
    return float(value)


def t_per_rz(epsilon: float) -> int:
    return int(math.ceil(3.0 * math.log2(1.0 / float(epsilon))))


def precision_score(row: dict[str, str], epsilon: float) -> float:
    extra_t = t_per_rz(epsilon) * f(row, "rz_non_clifford")
    return (
        f(row, "T")
        + extra_t
        + 0.05 * f(row, "CNOT")
        + 0.02 * (f(row, "depth") + extra_t)
        + 0.01 * (f(row, "gates") + extra_t)
        + 0.50 * f(row, "peak_ancilla")
    )


def relative(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0)


def compare_pairs(pairs: Iterable[tuple[float, float]]) -> tuple[int, int, int, float]:
    wins = losses = ties = 0
    rels: list[float] = []
    for target, baseline in pairs:
        if target < baseline - 1e-9:
            wins += 1
        elif target > baseline + 1e-9:
            losses += 1
        else:
            ties += 1
        rels.append(relative(target, baseline))
    return wins, losses, ties, statistics.mean(rels) if rels else 0.0


def best_by_name(rows: list[dict[str, str]], epsilon: float) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if not usable(row):
            continue
        name = row["name"]
        current = out.get(name)
        key = (
            precision_score(row, epsilon),
            f(row, "rz_non_clifford"),
            f(row, "T"),
            f(row, "CNOT"),
            row.get("method", ""),
        )
        if current is None or key < (
            precision_score(current, epsilon),
            f(current, "rz_non_clifford"),
            f(current, "T"),
            f(current, "CNOT"),
            current.get("method", ""),
        ):
            out[name] = row
    return out


def load_traditional(epsilon: float) -> dict[str, dict[str, dict[str, str]]]:
    loaded: dict[str, dict[str, dict[str, str]]] = {}
    for label, path in TRADITIONAL_SOURCES.items():
        loaded[label] = best_by_name(read_csv(path), epsilon)
    return loaded


def load_policy(epsilon: float) -> dict[str, dict[str, dict[str, str]]]:
    raw = [
        row
        for row in read_csv(POLICY_SOURCE)
        if row.get("split") == "test_n6" and row.get("method") in set(POLICY_METHODS.values()) and usable(row)
    ]
    loaded: dict[str, dict[str, dict[str, str]]] = {}
    for label, method in POLICY_METHODS.items():
        loaded[label] = best_by_name([row for row in raw if row["method"] == method], epsilon)
    return loaded


def summarize(comparison: Comparison, epsilon: float) -> dict[str, object]:
    sources = load_traditional(epsilon) if comparison.scope == "traditional" else load_policy(epsilon)
    target_rows = sources[comparison.target]
    baseline_rows = sources[comparison.baseline]
    names = sorted(set(target_rows) & set(baseline_rows))
    pairs = [(precision_score(target_rows[name], epsilon), precision_score(baseline_rows[name], epsilon)) for name in names]
    wins, losses, ties, mean_rel = compare_pairs(pairs)
    target_scores = [precision_score(target_rows[name], epsilon) for name in names]
    baseline_scores = [precision_score(baseline_rows[name], epsilon) for name in names]
    target_rz = [f(target_rows[name], "rz_non_clifford") for name in names]
    baseline_rz = [f(baseline_rows[name], "rz_non_clifford") for name in names]
    target_total_rz = [f(target_rows[name], "rz_total") for name in names]
    baseline_total_rz = [f(baseline_rows[name], "rz_total") for name in names]
    status = "pass"
    if comparison.scope == "traditional" and len(names) != 177:
        status = "needs revision"
    if comparison.scope == "policy" and len(names) != 38:
        status = "needs revision"
    return {
        "scope": comparison.scope,
        "target": comparison.target,
        "baseline": comparison.baseline,
        "epsilon": f"{epsilon:g}",
        "t_per_nonclifford_rz": t_per_rz(epsilon),
        "items": len(names),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": mean_rel,
        "mean_target_score": statistics.mean(target_scores) if target_scores else float("nan"),
        "mean_baseline_score": statistics.mean(baseline_scores) if baseline_scores else float("nan"),
        "target_mean_nonclifford_rz": statistics.mean(target_rz) if target_rz else float("nan"),
        "baseline_mean_nonclifford_rz": statistics.mean(baseline_rz) if baseline_rz else float("nan"),
        "target_mean_total_rz": statistics.mean(target_total_rz) if target_total_rz else float("nan"),
        "baseline_mean_total_rz": statistics.mean(baseline_total_rz) if baseline_total_rz else float("nan"),
        "status": status,
    }


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for epsilon in EPSILONS:
        for comparison in COMPARISONS:
            rows.append(summarize(comparison, epsilon))
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float, digits: int = 2) -> str:
    return f"{100.0 * value:+.{digits}f}%"


def tex_pct(value: float, digits: int = 2) -> str:
    return pct(value, digits).replace("%", r"\%")


def row_label(row: dict[str, object]) -> str:
    return f"{row['target']} vs {row['baseline']}"


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    key_rows = [
        row
        for row in rows
        if (
            row["scope"],
            row["target"],
            row["baseline"],
            float(row["epsilon"]),
        )
        in SELECTED_TABLE_ROWS
    ]
    wide_revkit = next(
        row
        for row in rows
        if row["scope"] == "traditional"
        and row["target"] == "Affine-128"
        and row["baseline"] == "RevKit oracle_synth"
        and row["epsilon"] == "1e-06"
    )
    policy_budget = next(
        row
        for row in rows
        if row["scope"] == "policy"
        and row["target"] == "Diverse-512"
        and row["baseline"] == "Budget-32"
        and row["epsilon"] == "1e-06"
    )
    policy_wide = next(
        row
        for row in rows
        if row["scope"] == "policy"
        and row["target"] == "Diverse-512"
        and row["baseline"] == "Wide-128"
        and row["epsilon"] == "1e-06"
    )
    lines = [
        "# Phase Rotation-Precision Sensitivity Audit",
        "",
        "This audit freezes the verified phase/Rz candidates and recomputes logical resource scores",
        "under multiple approximation precisions.  Each non-Clifford Rz is charged",
        "`ceil(3 log2(1/epsilon))` T gates, with the same count added to logical depth and",
        "gate count.  The estimate follows the common Ross--Selinger asymptotic scaling for",
        "ancilla-free Clifford+T Z-rotation approximation.",
        "",
        "This is a precision-sensitive logical cost model, not exact rotation-sequence synthesis,",
        "not hardware mapping, and not a routed Clifford+T implementation.",
        "",
        "| scope | comparison | epsilon | T/Rz | items | W/L/T | mean delta | target non-Clifford Rz | baseline non-Clifford Rz |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in key_rows:
        lines.append(
            "| {scope} | {label} | {eps} | {tper} | {items} | {wins}/{losses}/{ties} | {delta} | {trz:.2f} | {brz:.2f} |".format(
                scope=row["scope"],
                label=row_label(row),
                eps=row["epsilon"],
                tper=row["t_per_nonclifford_rz"],
                items=row["items"],
                wins=row["wins"],
                losses=row["losses"],
                ties=row["ties"],
                delta=pct(float(row["mean_relative"]), 3),
                trz=float(row["target_mean_nonclifford_rz"]),
                brz=float(row["baseline_mean_nonclifford_rz"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- At epsilon=1e-6, Affine-128 vs RevKit oracle_synth is {wide_revkit['wins']}/{wide_revkit['losses']}/{wide_revkit['ties']} with {pct(float(wide_revkit['mean_relative']), 3)} mean score change under the precision model.",
            f"- At epsilon=1e-6, Diverse-512 vs Budget-32 is {policy_budget['wins']}/{policy_budget['losses']}/{policy_budget['ties']} with {pct(float(policy_budget['mean_relative']), 3)} mean score change.",
            f"- At epsilon=1e-6, Diverse-512 vs Wide-128 is {policy_wide['wins']}/{policy_wide['losses']}/{policy_wide['ties']} with {pct(float(policy_wide['mean_relative']), 3)} mean score gap, so the learned shortlist remains a pruning result rather than a better-than-wide-search claim.",
            "- The audit strengthens the phase/Rz boundary: results no longer depend on one hard-coded T/Rz=30 proxy, but they still do not claim synthesized rotation sequences.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    selected = [
        row
        for row in rows
        if (
            row["scope"],
            row["target"],
            row["baseline"],
            float(row["epsilon"]),
        )
        in SELECTED_TABLE_ROWS
    ]
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}X>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedleft\arraybackslash}p{0.10\linewidth}>{\raggedleft\arraybackslash}p{0.10\linewidth}}",
        r"\toprule",
        r"Scope & Comparison & $\epsilon$ & $T/R_z$ & W/L/T & $\Delta$ \\",
        r"\midrule",
    ]
    for row in selected:
        lines.append(
            "{} & {} & {} & {} & {}/{}/{} & {} \\\\".format(
                "trad." if row["scope"] == "traditional" else "policy",
                row_label(row).replace("_", r"\_"),
                row["epsilon"],
                row["t_per_nonclifford_rz"],
                row["wins"],
                row["losses"],
                row["ties"],
                tex_pct(float(row["mean_relative"]), 3),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    pass_rows = sum(1 for row in rows if row["status"] == "pass")
    critical = next(
        row
        for row in rows
        if row["scope"] == "policy"
        and row["target"] == "Diverse-512"
        and row["baseline"] == "Wide-128"
        and row["epsilon"] == "1e-06"
    )
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {
            status: sum(1 for row in rows if row["status"] == status)
            for status in sorted({str(row["status"]) for row in rows})
        },
        "needs_revision_count": 0 if pass_rows == len(rows) else len(rows) - pass_rows,
        "epsilons": [f"{eps:g}" for eps in EPSILONS],
        "t_per_rz": {f"{eps:g}": t_per_rz(eps) for eps in EPSILONS},
        "traditional_items": 177,
        "policy_items": 38,
        "critical_policy_wide128_epsilon": critical["epsilon"],
        "critical_policy_wide128_wlt": f"{critical['wins']}/{critical['losses']}/{critical['ties']}",
        "critical_policy_wide128_mean_relative": critical["mean_relative"],
        "sources": [str(path.relative_to(THIS_DIR)) for path in TRADITIONAL_SOURCES.values()] + [str(POLICY_SOURCE.relative_to(THIS_DIR))],
        "outputs": {
            "summary": "results/summary_phase_rotation_precision_audit.csv",
            "analysis": "results/analysis_phase_rotation_precision_audit.md",
            "manifest": "results/manifest_phase_rotation_precision_audit.json",
            "table": "paper_latex/tables/phase_rotation_precision_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_phase_rotation_precision_audit.csv", rows)
    write_markdown(RESULTS / "analysis_phase_rotation_precision_audit.md", rows)
    write_latex(TABLES / "phase_rotation_precision_audit.tex", rows)
    write_manifest(RESULTS / "manifest_phase_rotation_precision_audit.json", rows)
    print(f"wrote {len(rows)} phase rotation-precision audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
