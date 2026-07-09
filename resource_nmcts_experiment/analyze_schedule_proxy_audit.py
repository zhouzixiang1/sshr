#!/usr/bin/env python3
"""Build a compact manuscript audit for logic-level schedule proxy tradeoffs."""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

SUMMARY = RESULTS / "summary_schedule_metrics.csv"
ANALYSIS = RESULTS / "analysis_schedule_metrics.md"


@dataclass(frozen=True)
class FocusSpec:
    evidence_slice: str
    dataset: str
    method: str
    baseline: str
    role: str
    boundary: str


FOCUS_SPECS = [
    FocusSpec(
        evidence_slice="n=24,28,32,40 scale",
        dataset="schedule_generalization",
        method="depth_frontier_policy",
        baseline="screen_depth2",
        role="learned frontier vs cheap depth-2",
        boundary="quality gain with more auxiliary lifetime",
    ),
    FocusSpec(
        evidence_slice="n=24,28,32,40 scale",
        dataset="schedule_generalization",
        method="depth_frontier_policy",
        baseline="adaptive_all_depth",
        role="learned frontier vs all-depth ceiling",
        boundary="near-ceiling quality with lower lifetime",
    ),
    FocusSpec(
        evidence_slice="n=21,22 bridge",
        dataset="schedule_truth_bridge",
        method="depth_frontier_policy",
        baseline="screen_depth2",
        role="complete-truth bridge vs cheap depth-2",
        boundary="truth-checked quality gain with lifetime cost",
    ),
    FocusSpec(
        evidence_slice="n=21,22 bridge",
        dataset="schedule_truth_bridge",
        method="depth_frontier_policy",
        baseline="adaptive_all_depth",
        role="complete-truth bridge vs all-depth ceiling",
        boundary="small score gap with lower lifetime",
    ),
    FocusSpec(
        evidence_slice="n=23 bridge",
        dataset="schedule_truth_bridge_n23",
        method="depth_frontier_policy",
        baseline="screen_depth2",
        role="larger truth bridge vs cheap depth-2",
        boundary="quality gain with lifetime cost",
    ),
    FocusSpec(
        evidence_slice="n=23 bridge",
        dataset="schedule_truth_bridge_n23",
        method="depth_frontier_policy",
        baseline="adaptive_all_depth",
        role="larger truth bridge vs all-depth ceiling",
        boundary="small score gap with lower lifetime",
    ),
    FocusSpec(
        evidence_slice="n=24,28,32,40 scale",
        dataset="schedule_generalization",
        method="adaptive_all_depth",
        baseline="screen_depth2",
        role="all-depth ceiling vs cheap depth-2",
        boundary="quality ceiling increases lifetime",
    ),
    FocusSpec(
        evidence_slice="n=23 bridge",
        dataset="schedule_truth_bridge_n23",
        method="adaptive_all_depth",
        baseline="screen_depth2",
        role="bridge all-depth ceiling vs cheap depth-2",
        boundary="truth-checked ceiling increases lifetime",
    ),
]

METRICS = {
    "score": "score",
    "schedule_t_depth_proxy": "t_depth",
    "explicit_ancilla_lifetime_area": "aux_lifetime",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metric_map(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        out[(row["dataset"], row["method"], row["baseline"], row["metric"])] = row
    return out


def format_pct(value: str) -> str:
    return f"{float(value):+.2%}"


def metric_cell(row: dict[str, str] | None) -> str:
    if row is None:
        return "missing"
    return f"{int(row['wins'])}/{int(row['losses'])}/{int(row['ties'])}; {format_pct(row['mean_relative'])}"


def build_rows() -> list[dict[str, str]]:
    source_rows = read_csv(SUMMARY)
    index = metric_map(source_rows)
    rows: list[dict[str, str]] = []
    for spec in FOCUS_SPECS:
        values = {
            short: index.get((spec.dataset, spec.method, spec.baseline, metric))
            for metric, short in METRICS.items()
        }
        status = "pass" if all(values.values()) else "needs revision"
        items = next((value["items"] for value in values.values() if value is not None), "missing")
        rows.append(
            {
                "evidence_slice": spec.evidence_slice,
                "comparison": f"{spec.method} vs {spec.baseline}",
                "role": spec.role,
                "status": status,
                "items": items,
                "score": metric_cell(values["score"]),
                "t_depth": metric_cell(values["t_depth"]),
                "aux_lifetime": metric_cell(values["aux_lifetime"]),
                "boundary": spec.boundary,
            }
        )
    return rows


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("depth-frontier", r"depth-frontier"),
        ("all-depth", r"all-depth"),
        ("T-depth", r"T-depth"),
        ("n=24,28,32,40", r"$n=24,28,32,40$"),
        ("n=21,22", r"$n=21,22$"),
        ("n=23", r"$n=23$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["evidence_slice", "comparison", "role", "status", "items", "score", "t_depth", "aux_lifetime", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Schedule Proxy Audit",
        "",
        "This compact audit promotes the logic-level schedule metrics that are most relevant to a resource-constrained claim.",
        "All metrics are computed before hardware mapping. Lower score, T-depth proxy, and explicit auxiliary lifetime area are better.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Focus rows",
            "",
            "| evidence slice | comparison | status | items | score W/L/T; mean | T-depth W/L/T; mean | aux lifetime W/L/T; mean | boundary |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {evidence_slice} | {comparison} | {status} | {items} | {score} | {t_depth} | {aux_lifetime} | {boundary} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Evidence slice & Comparison & Score & T-depth proxy & Aux. lifetime area & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["evidence_slice"]),
                latex_cell(row["role"]),
                latex_cell(row["score"]),
                latex_cell(row["t_depth"]),
                latex_cell(row["aux_lifetime"]),
                latex_cell(row["boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})}
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "source_files": {
            "summary_schedule_metrics": str(SUMMARY.relative_to(THIS_DIR)),
            "analysis_schedule_metrics": str(ANALYSIS.relative_to(THIS_DIR)),
        },
        "outputs": {
            "summary": "results/summary_schedule_proxy_audit.csv",
            "analysis": "results/analysis_schedule_proxy_audit.md",
            "manifest": "results/manifest_schedule_proxy_audit.json",
            "table": "paper_latex/tables/schedule_proxy_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_schedule_proxy_audit.csv", rows)
    write_markdown(RESULTS / "analysis_schedule_proxy_audit.md", rows)
    write_latex(TABLES / "schedule_proxy_audit.tex", rows)
    write_manifest(RESULTS / "manifest_schedule_proxy_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} schedule proxy audit rows")
    if failures:
        print(f"warning: {failures} schedule proxy row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
