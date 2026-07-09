#!/usr/bin/env python3
"""Audit the bounded evidence for neural root-action candidate extension."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

SOURCES = (
    ("n=14 root-action slice", RESULTS / "raw_highdim_root_action_pairwise_widths.csv"),
    ("n=16 root-action slice", RESULTS / "raw_ultra_root_action_pairwise_widths.csv"),
)


def read_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for scope, path in SOURCES:
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["scope"] = scope
                rows.append(row)
    return rows


def is_usable(row: dict[str, str]) -> bool:
    return not row.get("error") and str(row.get("correct")) == "True"


def compare(
    rows: list[dict[str, str]],
    target: str,
    baseline: str,
    *,
    scope: str | None = None,
    metric: str = "score",
) -> dict[str, object]:
    by_key: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in rows:
        if not is_usable(row):
            continue
        if scope is not None and row["scope"] != scope:
            continue
        by_key.setdefault((row["scope"], row["name"]), {})[row["method"]] = row

    wins = losses = ties = 0
    relatives: list[float] = []
    for methods in by_key.values():
        if target not in methods or baseline not in methods:
            continue
        new = float(methods[target][metric])
        old = float(methods[baseline][metric])
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
        relatives.append((new - old) / max(old, 1.0) * 100.0)
    return {
        "pairs": wins + losses + ties,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative_pct": statistics.mean(relatives) if relatives else float("nan"),
    }


def wlt(stats: dict[str, object]) -> str:
    return f"{stats['wins']}/{stats['losses']}/{stats['ties']}"


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def status_from(condition: bool) -> str:
    return "pass" if condition else "needs revision"


def build_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    specs = [
        (
            "n=14 heuristic top-4 plus neural top-12 extension",
            "n=14 root-action slice",
            "root_union_h4_n12",
            "root_beam4_oracle_eval",
            "root_oracle24",
            "bounded candidate extension",
        ),
        (
            "n=16 heuristic top-4 plus neural top-12 extension",
            "n=16 root-action slice",
            "root_union_h4_n12",
            "root_beam4_oracle_eval",
            "root_oracle24",
            "bounded candidate extension",
        ),
        (
            "Combined heuristic top-4 plus neural top-12 extension",
            None,
            "root_union_h4_n12",
            "root_beam4_oracle_eval",
            "root_oracle24",
            "bounded candidate extension",
        ),
        (
            "Combined neural top-12 replacement",
            None,
            "root_neural_top12",
            "root_beam4_oracle_eval",
            "root_oracle24",
            "supporting replacement diagnostic",
        ),
        (
            "Combined oracle top-24 headroom",
            None,
            "root_oracle24",
            "root_beam4_oracle_eval",
            "root_oracle24",
            "one-step teacher boundary",
        ),
    ]
    for component, scope, target, baseline, oracle, role in specs:
        stats = compare(raw_rows, target, baseline, scope=scope)
        oracle_gap = compare(raw_rows, oracle, target, scope=scope)
        status = status_from(
            int(stats["pairs"]) > 0
            and int(stats["wins"]) >= int(stats["losses"])
            and float(stats["mean_relative_pct"]) <= 0.0
            and (role != "bounded candidate extension" or int(stats["losses"]) == 0)
        )
        rows.append(
            {
                "component": component,
                "scope": scope or "n=14 and n=16 root-action slices",
                "target": target,
                "baseline": baseline,
                "pairs": str(stats["pairs"]),
                "score_wlt": wlt(stats),
                "mean_relative_score_pct": fmt_pct(float(stats["mean_relative_pct"])),
                "oracle_headroom_pct": fmt_pct(float(oracle_gap["mean_relative_pct"])),
                "role": role,
                "boundary": "Root-only one-step greedy child-plan audit; not a global optimum or runtime claim.",
                "status": status,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "component",
        "scope",
        "target",
        "baseline",
        "pairs",
        "score_wlt",
        "mean_relative_score_pct",
        "oracle_headroom_pct",
        "role",
        "boundary",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Root-Action Neural Ranker Audit",
        "",
        "This audit consolidates the high-dimensional root-action diagnostics used",
        "to decide whether the learned root-action scorer can be described as a",
        "bounded candidate-extension signal.  It compares a conservative union",
        "policy that keeps the deterministic heuristic top-4 actions and adds",
        "neural top-12 actions against the existing heuristic top-4 root window.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| component | scope | target | baseline | pairs | score W/L/T | mean score change | oracle headroom | role | status |",
            "|---|---|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["component"],
                    row["scope"],
                    row["target"],
                    row["baseline"],
                    row["pairs"],
                    row["score_wlt"],
                    row["mean_relative_score_pct"],
                    row["oracle_headroom_pct"],
                    row["role"],
                    row["status"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The union policy is the only root-action row promoted into the learned-control audit, because it preserves the deterministic heuristic window and adds learned candidates.",
            "- The combined union row has zero score losses against heuristic top-4, but the mean gain is small; it supports bounded candidate extension, not a headline resource claim.",
            "- The oracle-headroom row records that a wider one-step teacher still has residual room, so the learned root-action scorer remains a bounded search-control component.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedleft\arraybackslash}p{0.09\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Component & Scope & Pairs & Score W/L/T & Mean $\Delta$ score & Role \\",
        r"\midrule",
    ]
    for row in rows:
        if row["component"].startswith("Combined neural top-12"):
            continue
        mean_score = row["mean_relative_score_pct"].replace("%", r"\%")
        lines.append(
            " & ".join(
                [
                    tex_escape(row["component"]),
                    tex_escape(row["scope"]),
                    row["pairs"],
                    row["score_wlt"],
                    f"${mean_score}$",
                    tex_escape(row["role"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    combined = next(row for row in rows if row["component"] == "Combined heuristic top-4 plus neural top-12 extension")
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "combined_pairs": int(combined["pairs"]),
        "combined_score_wlt": combined["score_wlt"],
        "combined_mean_relative_score_pct": combined["mean_relative_score_pct"],
        "combined_oracle_headroom_pct": combined["oracle_headroom_pct"],
        "sources": [f"results/{path.name}" for _scope, path in SOURCES],
        "outputs": {
            "summary": "results/summary_root_action_ranker_audit.csv",
            "analysis": "results/analysis_root_action_ranker_audit.md",
            "manifest": "results/manifest_root_action_ranker_audit.json",
            "table": "paper_latex/tables/root_action_ranker_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    raw_rows = read_rows()
    rows = build_rows(raw_rows)
    write_csv(RESULTS / "summary_root_action_ranker_audit.csv", rows)
    write_markdown(RESULTS / "analysis_root_action_ranker_audit.md", rows)
    write_latex(TABLES / "root_action_ranker_audit.tex", rows)
    write_manifest(RESULTS / "manifest_root_action_ranker_audit.json", rows)
    print(f"wrote {len(rows)} root-action ranker audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
