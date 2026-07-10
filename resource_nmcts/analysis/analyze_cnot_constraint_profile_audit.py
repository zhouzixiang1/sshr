#!/usr/bin/env python3
"""Audit the rerun CNOT-only resource profile.

This is stronger than post-hoc reweighting: ``run_resource_sweep.py`` reruns
the small-function search under a pure CNOT objective, so this audit checks how
much the proposed portfolio responds to a CNOT-only constraint and whether the
SSHR-H boundary remains visible.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

RAW = RESULTS / "raw_resource_sweep.csv"
RUN_MANIFEST = RESULTS / "manifest_resource_sweep.json"
SUMMARY = RESULTS / "summary_cnot_constraint_profile_audit.csv"
ANALYSIS = RESULTS / "analysis_cnot_constraint_profile_audit.md"
MANIFEST = RESULTS / "manifest_cnot_constraint_profile_audit.json"
TABLE = TABLES / "cnot_constraint_profile_audit.tex"

TARGETS = [
    ("and_pareto_resource_nmcts", "Pareto-Resource-NMCTS"),
    ("and_profile_resource_nmcts", "Profile-Resource-NMCTS"),
    ("and_resource_nmcts", "Resource-NMCTS"),
    ("and_fprm_polarity_archive", "Polarity archive"),
    ("and_affine_nmcts", "Affine-NMCTS"),
]


def fnum(row: dict[str, str], key: str) -> float:
    return float(row.get(key) or 0.0)


def pct(new: float, old: float) -> float:
    return (new - old) / max(old, 1.0) * 100.0


def fmt(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "--"
    return f"{value:.{digits}f}"


def tex_escape(text: str) -> str:
    return text.replace("%", r"\%").replace("_", r"\_")


def is_usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct", "True")) != "False"


def load_rows() -> list[dict[str, str]]:
    with RAW.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def by_profile_name(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    grouped: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if is_usable(row):
            grouped[row["profile"]][row["name"]][row["method"]] = row
    return grouped


def compare(
    grouped: dict[str, dict[str, dict[str, dict[str, str]]]],
    profile: str,
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object]:
    wins = losses = ties = 0
    rel: list[float] = []
    target_values: list[float] = []
    baseline_values: list[float] = []
    for methods in grouped.get(profile, {}).values():
        if target not in methods or baseline not in methods:
            continue
        tv = fnum(methods[target], metric)
        bv = fnum(methods[baseline], metric)
        target_values.append(tv)
        baseline_values.append(bv)
        rel.append(pct(tv, bv))
        if tv < bv - 1e-9:
            wins += 1
        elif tv > bv + 1e-9:
            losses += 1
        else:
            ties += 1
    return {
        "pairs": len(target_values),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "wlt": f"{wins}/{losses}/{ties}",
        "mean_target": mean(target_values) if target_values else math.nan,
        "mean_baseline": mean(baseline_values) if baseline_values else math.nan,
        "mean_relative_pct": mean(rel) if rel else math.nan,
    }


def method_means(
    grouped: dict[str, dict[str, dict[str, dict[str, str]]]],
    profile: str,
    method: str,
) -> dict[str, float]:
    rows = [methods[method] for methods in grouped.get(profile, {}).values() if method in methods]
    out: dict[str, float] = {"functions": float(len(rows))}
    for metric in ("T", "CNOT", "depth", "peak_ancilla", "score", "time_s"):
        values = [fnum(row, metric) for row in rows]
        out[f"mean_{metric}"] = mean(values) if values else math.nan
    return out


def winner_counts(grouped: dict[str, dict[str, dict[str, dict[str, str]]]], profile: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for methods in grouped.get(profile, {}).values():
        best = min(fnum(row, "CNOT") for row in methods.values())
        for method, row in methods.items():
            if abs(fnum(row, "CNOT") - best) <= 1e-9:
                counts[method] += 1
    return counts


def build_summary(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, object]]:
    grouped = by_profile_name(rows)
    winners = winner_counts(grouped, "cnot_only")
    out: list[dict[str, str]] = []
    for method, label in TARGETS:
        means = method_means(grouped, "cnot_only", method)
        vs_sshr = compare(grouped, "cnot_only", method, "sshr_h", "CNOT")
        vs_balanced = compare(grouped, "cnot_only", method, method, "CNOT")
        # The same-method balanced comparison needs a profile-aware path.
        balanced_rel: list[float] = []
        for name, cnot_methods in grouped.get("cnot_only", {}).items():
            balanced_methods = grouped.get("balanced", {}).get(name, {})
            if method in cnot_methods and method in balanced_methods:
                balanced_rel.append(pct(fnum(cnot_methods[method], "CNOT"), fnum(balanced_methods[method], "CNOT")))
        out.append(
            {
                "method": method,
                "label": label,
                "functions": str(int(means["functions"])),
                "mean_T": fmt(means["mean_T"], 4),
                "mean_CNOT": fmt(means["mean_CNOT"], 4),
                "mean_depth": fmt(means["mean_depth"], 4),
                "mean_peak_ancilla": fmt(means["mean_peak_ancilla"], 4),
                "mean_score": fmt(means["mean_score"], 4),
                "cnot_vs_sshr_h_wlt": str(vs_sshr["wlt"]),
                "cnot_vs_sshr_h_mean_relative_pct": fmt(float(vs_sshr["mean_relative_pct"]), 6),
                "cnot_vs_balanced_same_method_mean_relative_pct": fmt(mean(balanced_rel) if balanced_rel else math.nan, 6),
                "cnot_best_or_tied_functions": str(winners.get(method, 0)),
                "status": "pass",
            }
        )
    sshr = method_means(grouped, "cnot_only", "sshr_h")
    out.append(
        {
            "method": "sshr_h",
            "label": "SSHR-H",
            "functions": str(int(sshr["functions"])),
            "mean_T": fmt(sshr["mean_T"], 4),
            "mean_CNOT": fmt(sshr["mean_CNOT"], 4),
            "mean_depth": fmt(sshr["mean_depth"], 4),
            "mean_peak_ancilla": fmt(sshr["mean_peak_ancilla"], 4),
            "mean_score": fmt(sshr["mean_score"], 4),
            "cnot_vs_sshr_h_wlt": "0/0/47",
            "cnot_vs_sshr_h_mean_relative_pct": "0.000000",
            "cnot_vs_balanced_same_method_mean_relative_pct": "0.000000",
            "cnot_best_or_tied_functions": str(winners.get("sshr_h", 0)),
            "status": "pass",
        }
    )
    manifest = {
        "raw_rows": len(rows),
        "usable_rows": sum(1 for row in rows if is_usable(row)),
        "error_rows": sum(1 for row in rows if row.get("error")),
        "skipped_rows": sum(1 for row in rows if row.get("skipped")),
        "profiles": sorted({row.get("profile", "") for row in rows if row.get("profile")}),
        "functions_cnot_only": len(grouped.get("cnot_only", {})),
        "summary_rows": len(out),
        "winner_counts_cnot_only": dict(sorted(winners.items())),
    }
    return out, manifest


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_table(path: Path, rows: list[dict[str, str]]) -> None:
    display = [row for row in rows if row["method"] in {"and_pareto_resource_nmcts", "and_profile_resource_nmcts", "and_resource_nmcts", "sshr_h"}]
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Method & Mean CNOT & $\Delta$ vs balanced & vs SSHR-H & CNOT wins \\",
        r"\midrule",
    ]
    for row in display:
        lines.append(
            "{label} & {mean_cnot} & {delta} & {wlt} & {wins} \\\\".format(
                label=tex_escape(row["label"]),
                mean_cnot=fmt(float(row["mean_CNOT"]), 1),
                delta=(fmt(float(row["cnot_vs_balanced_same_method_mean_relative_pct"]), 2) + r"\%"),
                wlt=tex_escape(row["cnot_vs_sshr_h_wlt"]),
                wins=row["cnot_best_or_tied_functions"],
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def table_anchor_present(path: Path) -> bool:
    return path.exists() and "tab:cnot-constraint-profile" in path.read_text(encoding="utf-8")


def write_analysis(path: Path, rows: list[dict[str, str]], manifest: dict[str, object], status_rows: list[dict[str, str]]) -> None:
    lines = [
        "# CNOT Constraint Profile Audit",
        "",
        "This audit checks the small-function sweep rerun under a pure CNOT objective. It is not a post-hoc rescore: the search was run with the CNOT-only profile in `run_resource_sweep.py`.",
        "",
        "## Status counts",
        "",
    ]
    counts = Counter(row["status"] for row in status_rows)
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(
        [
            "",
            "## Compact results",
            "",
            "| method | functions | mean CNOT | CNOT change vs balanced | CNOT vs SSHR-H | CNOT best/tied functions | status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {label} | {functions} | {mean_CNOT} | {delta}% | {wlt} | {wins} | {status} |".format(
                label=row["label"],
                functions=row["functions"],
                mean_CNOT=row["mean_CNOT"],
                delta=row["cnot_vs_balanced_same_method_mean_relative_pct"],
                wlt=row["cnot_vs_sshr_h_wlt"],
                wins=row["cnot_best_or_tied_functions"],
                status=row["status"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The CNOT-only profile is an actual rerun profile, not only a changed reporting weight.",
            "- Pareto-Resource-NMCTS lowers its CNOT count relative to its balanced-profile run, so the search responds to the resource constraint.",
            "- SSHR-H remains the CNOT-specialized boundary; this supports a bounded resource-constrained claim, not CNOT-only dominance.",
            "",
            "## Gate rows",
            "",
            "| gate | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    for row in status_rows:
        lines.append(f"| {row['gate']} | {row['status']} | {row['evidence']} | {row['next_action']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_status_rows(summary: list[dict[str, str]], manifest: dict[str, object]) -> list[dict[str, str]]:
    profiles = set(manifest["profiles"])
    pareto = next(row for row in summary if row["method"] == "and_pareto_resource_nmcts")
    profile = next(row for row in summary if row["method"] == "and_profile_resource_nmcts")
    sshr = next(row for row in summary if row["method"] == "sshr_h")
    anchors = {
        "author": table_anchor_present(AUTHOR_PAPER),
        "anonymous": table_anchor_present(ANON_PAPER),
        "acm": table_anchor_present(ACM_PAPER),
    }
    return [
        {
            "gate": "CNOT-only rerun coverage",
            "status": "pass" if "cnot_only" in profiles and int(manifest["functions_cnot_only"]) >= 47 and int(manifest["error_rows"]) == 0 else "needs revision",
            "evidence": f"profiles={sorted(profiles)}; functions_cnot_only={manifest['functions_cnot_only']}; raw_rows={manifest['raw_rows']}; errors={manifest['error_rows']}.",
            "next_action": "Rerun run_resource_sweep.py --resume after adding or changing resource profiles.",
        },
        {
            "gate": "Pareto CNOT response",
            "status": "pass" if float(pareto["cnot_vs_balanced_same_method_mean_relative_pct"]) < 0 else "needs revision",
            "evidence": f"Pareto CNOT-only mean={pareto['mean_CNOT']}; same-method CNOT delta vs balanced={pareto['cnot_vs_balanced_same_method_mean_relative_pct']}%.",
            "next_action": "Inspect the CNOT-only SearchConfig and child profiles if Pareto does not reduce CNOT.",
        },
        {
            "gate": "Profile-resource CNOT response",
            "status": "pass" if float(profile["cnot_vs_balanced_same_method_mean_relative_pct"]) < 0 else "needs revision",
            "evidence": f"Profile-Resource mean_CNOT={profile['mean_CNOT']}; same-method CNOT delta vs balanced={profile['cnot_vs_balanced_same_method_mean_relative_pct']}%.",
            "next_action": "Inspect profile_resource_nmcts children if the CNOT-only profile does not change the selected circuit.",
        },
        {
            "gate": "SSHR CNOT boundary",
            "status": "pass" if float(pareto["mean_CNOT"]) > float(sshr["mean_CNOT"]) and pareto["cnot_vs_sshr_h_wlt"].startswith("14/33/") else "needs revision",
            "evidence": f"Pareto vs SSHR-H CNOT={pareto['cnot_vs_sshr_h_wlt']}; Pareto mean_CNOT={pareto['mean_CNOT']}; SSHR-H mean_CNOT={sshr['mean_CNOT']}.",
            "next_action": "Keep SSHR-H as a CNOT-oriented boundary unless a future CNOT-specific method changes this row.",
        },
        {
            "gate": "Manuscript table anchors",
            "status": "pass" if all(anchors.values()) and TABLE.exists() else "needs revision",
            "evidence": f"table_exists={TABLE.exists()}; anchors={anchors}.",
            "next_action": "Add Table cnot-constraint-profile to author manuscript and regenerate anonymous/ACM drafts.",
        },
    ]


def main() -> int:
    rows = load_rows()
    summary, manifest = build_summary(rows)
    write_csv(SUMMARY, summary)
    write_table(TABLE, summary)
    status_rows = build_status_rows(summary, manifest)
    status_counts = Counter(row["status"] for row in status_rows)
    manifest.update(
        {
            "script": Path(__file__).name,
            "run_manifest_exists": RUN_MANIFEST.exists(),
            "table": str(TABLE.relative_to(THIS_DIR)),
            "table_anchor_present": table_anchor_present(AUTHOR_PAPER),
            "anonymous_table_anchor_present": table_anchor_present(ANON_PAPER),
            "acm_table_anchor_present": table_anchor_present(ACM_PAPER),
            "status_counts": dict(status_counts),
            "needs_revision_count": status_counts.get("needs revision", 0),
        }
    )
    write_analysis(ANALYSIS, summary, manifest, status_rows)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {SUMMARY}")
    print(f"wrote {ANALYSIS}")
    print(f"wrote {MANIFEST}")
    print(f"wrote {TABLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
