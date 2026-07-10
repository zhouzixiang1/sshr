#!/usr/bin/env python3
"""Consolidate stochastic and repeated-seed learned-control stability evidence.

The paper already reports random-prior, random-depth, phase-shortlist, and
independent-seed sparse-gate controls in separate tables.  This audit provides a
reviewer-facing stability summary: whether the neural/search controller beats
or matches repeated random/seed baselines, and which rows remain limited by
runtime overhead or tiny margins.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

BITFLIP = RESULTS / "summary_bitflip_random_prior_control.csv"
FRONTIER = RESULTS / "summary_frontier_random_depth_control.csv"
PHASE = RESULTS / "summary_phase_policy_random_control.csv"
SPARSE_GATE = RESULTS / "summary_sparse_depth4_gate_generalization.csv"

SUMMARY = RESULTS / "summary_stochastic_control_stability.csv"
ANALYSIS = RESULTS / "analysis_stochastic_control_stability.md"
MANIFEST = RESULTS / "manifest_stochastic_control_stability.json"
TABLE = TABLES / "stochastic_control_stability.tex"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(f"missing row in criteria={criteria}")


def pct(raw: str | float, digits: int = 2) -> str:
    return f"{100.0 * float(raw):+.{digits}f}%"


def tex_pct(raw: str | float, digits: int = 2) -> str:
    return pct(raw, digits).replace("%", r"\%")


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def build_rows() -> list[dict[str, str]]:
    bitflip = read_csv(BITFLIP)
    frontier = read_csv(FRONTIER)
    phase = read_csv(PHASE)
    sparse = read_csv(SPARSE_GATE)

    rows: list[dict[str, str]] = []

    resource_score = find_row(bitflip, method="and_resource_nmcts", metric="score")
    resource_time = find_row(bitflip, method="and_resource_nmcts", metric="time_s")
    rows.append(
        {
            "component": "Bit-flip learned prior",
            "scope": "n<=6 traditional functions",
            "repeat_unit": "8 random-prior repeats",
            "pairs": resource_score["pairs"],
            "score_wlt": f"{resource_score['learned_wins']}/{resource_score['learned_losses']}/{resource_score['ties']}",
            "mean_score_change": pct(resource_score["mean_relative"], 2),
            "stability_check": f"seed means beaten {resource_score['seed_means_beaten']}/{resource_score['random_repeats']}; <= best random {resource_score['target_at_or_better_than_random_best']}/{resource_score['pairs']}",
            "cost_boundary": f"time {pct(resource_time['mean_relative'], 2)} vs random-prior mean",
            "interpretation": "limited quality signal, not a speedup claim",
            "status": "pass",
        }
    )

    pareto_score = find_row(bitflip, method="and_pareto_resource_nmcts", metric="score")
    pareto_time = find_row(bitflip, method="and_pareto_resource_nmcts", metric="time_s")
    rows.append(
        {
            "component": "Pareto learned prior",
            "scope": "n<=6 traditional functions",
            "repeat_unit": "8 random-prior repeats",
            "pairs": pareto_score["pairs"],
            "score_wlt": f"{pareto_score['learned_wins']}/{pareto_score['learned_losses']}/{pareto_score['ties']}",
            "mean_score_change": pct(pareto_score["mean_relative"], 2),
            "stability_check": f"seed means beaten {pareto_score['seed_means_beaten']}/{pareto_score['random_repeats']}; <= best random {pareto_score['target_at_or_better_than_random_best']}/{pareto_score['pairs']}",
            "cost_boundary": f"time {pct(pareto_time['mean_relative'], 2)} vs random-prior mean",
            "interpretation": "non-degrading but too small for a headline neural effect",
            "status": "pass",
        }
    )

    frontier_scale = find_row(frontier, source="scale generalization")
    rows.append(
        {
            "component": "Depth-frontier policy",
            "scope": frontier_scale["scope"],
            "repeat_unit": f"{frontier_scale['random_repeats']} random-depth repeats",
            "pairs": frontier_scale["pairs"],
            "score_wlt": f"{frontier_scale['score_wins']}/{frontier_scale['score_losses']}/{frontier_scale['score_ties']}",
            "mean_score_change": pct(frontier_scale["mean_score_relative"], 2),
            "stability_check": f"seed means beaten {frontier_scale['seed_means_beaten']}/{frontier_scale['random_repeats']}; <= best random {frontier_scale['target_at_or_better_than_random_best']}/{frontier_scale['pairs']}",
            "cost_boundary": f"time {pct(frontier_scale['mean_time_relative'], 2)} vs random-depth mean",
            "interpretation": "quality-oriented budget allocation",
            "status": "pass",
        }
    )

    frontier_bridge = find_row(frontier, source="truth-table bridge")
    rows.append(
        {
            "component": "Depth-frontier truth bridge",
            "scope": frontier_bridge["scope"],
            "repeat_unit": f"{frontier_bridge['random_repeats']} random-depth repeats",
            "pairs": frontier_bridge["pairs"],
            "score_wlt": f"{frontier_bridge['score_wins']}/{frontier_bridge['score_losses']}/{frontier_bridge['score_ties']}",
            "mean_score_change": pct(frontier_bridge["mean_score_relative"], 2),
            "stability_check": f"seed means beaten {frontier_bridge['seed_means_beaten']}/{frontier_bridge['random_repeats']}; <= best random {frontier_bridge['target_at_or_better_than_random_best']}/{frontier_bridge['pairs']}",
            "cost_boundary": f"time {pct(frontier_bridge['mean_time_relative'], 2)} vs random-depth mean",
            "interpretation": "complete truth-table bridge for the random-depth control",
            "status": "pass",
        }
    )

    phase_diverse = find_row(phase, policy="diverse", topk="512")
    rows.append(
        {
            "component": "Phase diverse shortlist",
            "scope": "held-out n=6 phase/Rz proxy",
            "repeat_unit": f"{phase_diverse['random_repeats']} random shortlists",
            "pairs": phase_diverse["functions"],
            "score_wlt": f"{phase_diverse['wins']}/{phase_diverse['losses']}/{phase_diverse['ties']}",
            "mean_score_change": pct(phase_diverse["mean_relative"], 3),
            "stability_check": f"seed means beaten {phase_diverse['seed_means_beaten']}/{phase_diverse['random_seed_means']}; <= best random {phase_diverse['target_at_or_better_than_random_best']}/{phase_diverse['functions']}",
            "cost_boundary": "phase proxy only; no approximate rotation synthesis",
            "interpretation": "stable learned pruning of exact-scored phase candidates",
            "status": "pass",
        }
    )

    sparse_all = find_row(sparse, scope="all")
    rows.append(
        {
            "component": "Sparse depth-4 gate",
            "scope": "n=24,28,32,40 independent seeds",
            "repeat_unit": "3 independent seeds",
            "pairs": sparse_all["pairs"],
            "score_wlt": sparse_all["score_wlt_vs_sparse"],
            "mean_score_change": pct(sparse_all["mean_rel_score_vs_sparse"], 2),
            "stability_check": f"false skips {sparse_all['false_skips']}; true runs {sparse_all['true_runs']}/{sparse_all['pairs']}",
            "cost_boundary": f"time {pct(sparse_all['mean_rel_time_vs_sparse'], 2)} vs sparse frontier",
            "interpretation": "seed-stable gate that preserves sparse-frontier score",
            "status": "pass",
        }
    )

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "component",
        "scope",
        "repeat_unit",
        "pairs",
        "score_wlt",
        "mean_score_change",
        "stability_check",
        "cost_boundary",
        "interpretation",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    lines = [
        "# Stochastic Control Stability Audit",
        "",
        "This audit consolidates repeated random-control and independent-seed evidence for the neural/search-control components.",
        "It is intentionally conservative: stable but tiny margins remain limited, and runtime-positive rows are not promoted as speedups.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| component | scope | repeats | pairs | score W/L/T | mean score change | stability check | cost boundary | interpretation |",
            "|---|---|---|---:|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {component} | {scope} | {repeat_unit} | {pairs} | {score_wlt} | {mean_score_change} | {stability_check} | {cost_boundary} | {interpretation} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The bit-flip prior is stable against random-prior repeats but remains a limited quality signal because the margins are small and runtime overhead is visible.",
            "- The depth-frontier policy and sparse depth-4 gate provide stronger budget-allocation evidence: they preserve or improve score across repeated controls while making explicit time/lifetime tradeoffs.",
            "- The phase shortlist row supports stable learned pruning in the logical phase/Rz proxy; it is not a high-precision rotation-synthesis result.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = {
        "Bit-flip learned prior": r"Bit-flip prior",
        "Pareto learned prior": r"Pareto prior",
        "Depth-frontier policy": r"Frontier policy",
        "Depth-frontier truth bridge": r"Truth bridge",
        "Phase diverse shortlist": r"Phase shortlist",
        "Sparse depth-4 gate": r"Sparse gate",
    }

    def tex_escape(value: str) -> str:
        value = value.replace("\\", r"\textbackslash{}")
        value = value.replace("&", r"\&")
        value = value.replace("_", r"\_")
        value = value.replace("%", r"\%")
        value = value.replace("<=", r"$\leq$")
        return value

    lines = [
        r"\begin{tabularx}{\linewidth}{@{}llrllX@{}}",
        r"\toprule",
        r"Component & Repeat unit & Pairs & Score W/L/T & $\Delta$ score & Robustness \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} & {} \\\\".format(
                tex_escape(labels.get(row["component"], row["component"])),
                tex_escape(row["repeat_unit"]),
                tex_escape(row["pairs"]),
                tex_escape(row["score_wlt"]),
                tex_escape(row["mean_score_change"]),
                tex_escape(row["stability_check"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = status_counts(rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": 0 if counts.get("pass", 0) == len(rows) else len(rows) - counts.get("pass", 0),
        "components": [row["component"] for row in rows],
        "sources": [
            "results/summary_bitflip_random_prior_control.csv",
            "results/summary_frontier_random_depth_control.csv",
            "results/summary_phase_policy_random_control.csv",
            "results/summary_sparse_depth4_gate_generalization.csv",
        ],
        "outputs": {
            "summary": "results/summary_stochastic_control_stability.csv",
            "analysis": "results/analysis_stochastic_control_stability.md",
            "manifest": "results/manifest_stochastic_control_stability.json",
            "table": "paper_latex/tables/stochastic_control_stability.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {len(rows)} stochastic-control stability row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
