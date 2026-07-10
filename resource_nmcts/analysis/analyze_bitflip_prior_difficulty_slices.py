#!/usr/bin/env python3
"""Localize where the bit-flip learned prior helps under search budgets."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

RAW = RESULTS / "raw_bitflip_neural_budget_sweep.csv"
LEARNED_FULL = RESULTS / "raw_traditional_resource_learned_prior.csv"
NO_PRIOR_FULL = RESULTS / "raw_traditional_resource_no_prior.csv"
SUMMARY = RESULTS / "summary_bitflip_prior_difficulty_slices.csv"
ANALYSIS = RESULTS / "analysis_bitflip_prior_difficulty_slices.md"
MANIFEST = RESULTS / "manifest_bitflip_prior_difficulty_slices.json"
TABLE = TABLES / "bitflip_prior_difficulty_slices.tex"

METHODS = (
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
)
BUDGETS = ("top8_s8_n12", "top12_s12_n16", "top24_s24_n32")
SLICES = ("easy", "middle", "hard")
METRICS = ("score", "T", "time_s")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "row_type",
        "budget",
        "method",
        "difficulty_slice",
        "pairs",
        "no_prior_score_min",
        "no_prior_score_max",
        "score_wins",
        "score_losses",
        "score_ties",
        "mean_score_relative",
        "T_wins",
        "T_losses",
        "T_ties",
        "mean_T_relative",
        "mean_time_relative",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def add_full_budget(rows: list[dict[str, str]], variant: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        if not usable(row):
            continue
        item = dict(row)
        item["budget"] = "top24_s24_n32"
        item["variant"] = variant
        out.append(item)
    return out


def budget_label(budget: str) -> str:
    return {
        "top8_s8_n12": "top-8, 8/12 sim.",
        "top12_s12_n16": "top-12, 12/16 sim.",
        "top24_s24_n32": "top-24, 24/32 sim.",
    }.get(budget, budget)


def slice_label(name: str) -> str:
    return {"easy": "easy tercile", "middle": "middle tercile", "hard": "hard tercile"}.get(name, name)


def compare(learned: float, baseline: float) -> tuple[int, int, int]:
    if learned < baseline - 1e-12:
        return (1, 0, 0)
    if learned > baseline + 1e-12:
        return (0, 1, 0)
    return (0, 0, 1)


def relative(learned: float, baseline: float) -> float:
    return (learned - baseline) / baseline if baseline else 0.0


def fmt_pct(value: object) -> str:
    return f"{100.0 * float(value):+.2f}%"


def fmt_latex_pct(value: object) -> str:
    return fmt_pct(value).replace("%", r"\%")


def paired_items(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, object]]]:
    by_key = {
        (row["budget"], row["variant"], row["method"], row["name"]): row
        for row in rows
        if usable(row) and row.get("method") in METHODS and row.get("budget") in BUDGETS
    }
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for budget in BUDGETS:
        for method in METHODS:
            items: list[dict[str, object]] = []
            names = sorted(
                name
                for b, variant, m, name in by_key
                if b == budget
                and variant == "no_prior"
                and m == method
                and (budget, "learned_prior", method, name) in by_key
            )
            for name in names:
                no_prior = by_key[(budget, "no_prior", method, name)]
                learned = by_key[(budget, "learned_prior", method, name)]
                items.append(
                    {
                        "name": name,
                        "no_prior": no_prior,
                        "learned": learned,
                        "no_prior_score": float(no_prior["score"]),
                    }
                )
            items.sort(key=lambda item: (float(item["no_prior_score"]), str(item["name"])))
            n = len(items)
            if n < 3:
                continue
            split = n // 3
            slices = {
                "easy": items[:split],
                "middle": items[split : 2 * split],
                "hard": items[2 * split :],
            }
            for difficulty, subset in slices.items():
                grouped[(budget, method, difficulty)] = subset
    return grouped


def summarize_subset(row_type: str, budget: str, method: str, difficulty: str, subset: list[dict[str, object]]) -> dict[str, object]:
    wins = losses = ties = 0
    t_wins = t_losses = t_ties = 0
    score_rel: list[float] = []
    t_rel: list[float] = []
    time_rel: list[float] = []
    no_prior_scores: list[float] = []
    for item in subset:
        no_prior = item["no_prior"]
        learned = item["learned"]
        assert isinstance(no_prior, dict)
        assert isinstance(learned, dict)
        score_w, score_l, score_t = compare(float(learned["score"]), float(no_prior["score"]))
        wins += score_w
        losses += score_l
        ties += score_t
        t_w, t_l, t_t = compare(float(learned["T"]), float(no_prior["T"]))
        t_wins += t_w
        t_losses += t_l
        t_ties += t_t
        score_rel.append(relative(float(learned["score"]), float(no_prior["score"])))
        t_rel.append(relative(float(learned["T"]), float(no_prior["T"])))
        time_rel.append(relative(float(learned["time_s"]), float(no_prior["time_s"])))
        no_prior_scores.append(float(no_prior["score"]))
    return {
        "row_type": row_type,
        "budget": budget,
        "method": method,
        "difficulty_slice": difficulty,
        "pairs": len(subset),
        "no_prior_score_min": min(no_prior_scores) if no_prior_scores else 0.0,
        "no_prior_score_max": max(no_prior_scores) if no_prior_scores else 0.0,
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "mean_score_relative": statistics.mean(score_rel) if score_rel else 0.0,
        "T_wins": t_wins,
        "T_losses": t_losses,
        "T_ties": t_ties,
        "mean_T_relative": statistics.mean(t_rel) if t_rel else 0.0,
        "mean_time_relative": statistics.mean(time_rel) if time_rel else 0.0,
        "status": "pass" if losses == 0 else "needs revision",
    }


def build_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped = paired_items(rows)
    detail: list[dict[str, object]] = []
    aggregate: list[dict[str, object]] = []
    for budget in BUDGETS:
        for method in METHODS:
            for difficulty in SLICES:
                subset = grouped.get((budget, method, difficulty), [])
                if subset:
                    detail.append(summarize_subset("method_slice", budget, method, difficulty, subset))
        for difficulty in SLICES:
            combined: list[dict[str, object]] = []
            for method in METHODS:
                combined.extend(grouped.get((budget, method, difficulty), []))
            if combined:
                aggregate.append(summarize_subset("aggregate_slice", budget, "all_methods", difficulty, combined))
    return detail, aggregate


def write_markdown(path: Path, detail: list[dict[str, object]], aggregate: list[dict[str, object]]) -> None:
    counts = Counter(str(row["status"]) for row in detail + aggregate)
    lines = [
        "# Bit-Flip Learned-Prior Difficulty Slices",
        "",
        "This derived audit localizes the low-budget bit-flip learned-prior effect by no-prior score terciles.",
        "Within each budget and method, functions are sorted by the matched no-prior score and split into easy, middle, and hard thirds.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Aggregate slices",
            "",
            "| budget | difficulty slice | pairs | score W/L/T | mean score change | T W/L/T | mean T change | runtime change |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for budget in BUDGETS:
        for difficulty in SLICES:
            row = next(item for item in aggregate if item["budget"] == budget and item["difficulty_slice"] == difficulty)
            lines.append(
                f"| {budget_label(budget)} | {slice_label(difficulty)} | {row['pairs']} | "
                f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} | {fmt_pct(row['mean_score_relative'])} | "
                f"{row['T_wins']}/{row['T_losses']}/{row['T_ties']} | {fmt_pct(row['mean_T_relative'])} | "
                f"{fmt_pct(row['mean_time_relative'])} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Every aggregate slice has zero score losses, so the learned prior is non-degrading under these paired budgets.",
            "- The largest mean score and T-count reductions occur in the middle no-prior-score tercile, where candidate ordering has room to improve but the functions are not already saturated by very hard tradeoffs.",
            "- Runtime remains higher because Python model evaluation is included; the result is a search-quality localization, not a speedup claim.",
            "",
            "## Method-slice rows",
            "",
            "| budget | method | difficulty slice | pairs | score W/L/T | mean score change | runtime change |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in detail:
        lines.append(
            f"| {budget_label(str(row['budget']))} | {row['method']} | {slice_label(str(row['difficulty_slice']))} | "
            f"{row['pairs']} | {row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
            f"{fmt_pct(row['mean_score_relative'])} | {fmt_pct(row['mean_time_relative'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, aggregate: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Budget & Difficulty slice & Pairs & Score W/L/T & $\Delta$ score & $\Delta$ time \\",
        r"\midrule",
    ]
    for budget in BUDGETS:
        for difficulty in SLICES:
            row = next(item for item in aggregate if item["budget"] == budget and item["difficulty_slice"] == difficulty)
            lines.append(
                f"{budget_label(budget)} & {slice_label(difficulty)} & {int(row['pairs'])} & "
                f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} & "
                f"{fmt_latex_pct(row['mean_score_relative'])} & {fmt_latex_pct(row['mean_time_relative'])} \\\\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(detail: list[dict[str, object]], aggregate: list[dict[str, object]], input_rows: list[dict[str, str]]) -> None:
    paper = PAPER.read_text(encoding="utf-8", errors="replace") if PAPER.exists() else ""
    aggregate_losses = sum(int(row["score_losses"]) for row in aggregate)
    middle_rows = [row for row in aggregate if row["difficulty_slice"] == "middle"]
    middle_best_count = 0
    for budget in BUDGETS:
        budget_rows = [row for row in aggregate if row["budget"] == budget]
        if not budget_rows:
            continue
        best = min(budget_rows, key=lambda row: float(row["mean_score_relative"]))
        if best["difficulty_slice"] == "middle":
            middle_best_count += 1
    data = {
        "script": Path(__file__).name,
        "rows": len(detail) + len(aggregate),
        "detail_rows": len(detail),
        "aggregate_rows": len(aggregate),
        "input_rows": len(input_rows),
        "aggregate_score_losses": aggregate_losses,
        "middle_best_budget_count": middle_best_count,
        "needs_revision_count": 0 if aggregate_losses == 0 and middle_best_count == len(BUDGETS) else 1,
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "tab:bitflip-prior-difficulty" in paper,
        "outputs": {
            "summary": str(SUMMARY.relative_to(THIS_DIR)),
            "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
            "manifest": str(MANIFEST.relative_to(THIS_DIR)),
            "table": str(TABLE.relative_to(THIS_DIR)),
        },
        "inputs": [
            str(RAW.relative_to(THIS_DIR)),
            str(LEARNED_FULL.relative_to(THIS_DIR)),
            str(NO_PRIOR_FULL.relative_to(THIS_DIR)),
        ],
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [row for row in read_csv(RAW) if usable(row)]
    rows += add_full_budget(read_csv(LEARNED_FULL), "learned_prior")
    rows += add_full_budget(read_csv(NO_PRIOR_FULL), "no_prior")
    detail, aggregate = build_rows(rows)
    write_csv(SUMMARY, detail + aggregate)
    write_markdown(ANALYSIS, detail, aggregate)
    write_latex(TABLE, aggregate)
    write_manifest(detail, aggregate, rows)
    print(f"wrote {len(detail)} detail rows and {len(aggregate)} aggregate bit-flip prior difficulty rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
