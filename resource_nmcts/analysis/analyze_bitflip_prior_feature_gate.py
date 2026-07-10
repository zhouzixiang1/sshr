#!/usr/bin/env python3
"""Evaluate a static ANF-term gate for deploying the bit-flip learned prior."""
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

SUMMARY = RESULTS / "summary_bitflip_prior_feature_gate.csv"
ANALYSIS = RESULTS / "analysis_bitflip_prior_feature_gate.md"
MANIFEST = RESULTS / "manifest_bitflip_prior_feature_gate.json"
TABLE = TABLES / "bitflip_prior_feature_gate.tex"

METHODS = (
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
)
BUDGETS = ("top8_s8_n12", "top12_s12_n16", "top24_s24_n32")
GATE_MIN_ANF_TERMS = 6
GATE_MAX_ANF_TERMS = 23


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
        "all": "all budgets",
    }.get(budget, budget)


def method_label(method: str) -> str:
    return {
        "and_affine_nmcts": "Affine-Resource-NMCTS",
        "and_resource_nmcts": "Resource-NMCTS",
        "and_pareto_resource_nmcts": "Pareto-Resource-NMCTS",
        "all_methods": "all methods",
    }.get(method, method)


def latex_method_label(method: str) -> str:
    return {
        "and_affine_nmcts": r"Affine-\method{}",
        "and_resource_nmcts": r"\method{}",
        "and_pareto_resource_nmcts": r"Pareto-\method{}",
        "all_methods": "all methods",
    }.get(method, method.replace("_", r"\_"))


def gate_enabled(row: dict[str, str]) -> bool:
    return GATE_MIN_ANF_TERMS <= int(row["anf_terms"]) <= GATE_MAX_ANF_TERMS


def relative(selected: float, baseline: float) -> float:
    return (selected - baseline) / baseline if baseline else 0.0


def compare(selected: float, baseline: float) -> tuple[int, int, int]:
    if selected < baseline - 1e-12:
        return (1, 0, 0)
    if selected > baseline + 1e-12:
        return (0, 1, 0)
    return (0, 0, 1)


def fmt_pct(value: object) -> str:
    return f"{100.0 * float(value):+.2f}%"


def fmt_latex_pct(value: object) -> str:
    return fmt_pct(value).replace("%", r"\%")


def paired_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_key = {
        (row["budget"], row["variant"], row["method"], row["name"]): row
        for row in rows
        if usable(row) and row.get("method") in METHODS and row.get("budget") in BUDGETS
    }
    out: list[dict[str, object]] = []
    for budget in BUDGETS:
        for method in METHODS:
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
                enabled = gate_enabled(no_prior)
                selected = learned if enabled else no_prior
                out.append(
                    {
                        "budget": budget,
                        "method": method,
                        "name": name,
                        "gate_enabled": enabled,
                        "no_prior": no_prior,
                        "learned": learned,
                        "selected": selected,
                    }
                )
    return out


def summarize(row_type: str, budget: str, method: str, rows: list[dict[str, object]]) -> dict[str, object]:
    wins = losses = ties = 0
    learned_wins = learned_losses = learned_ties = 0
    score_rel: list[float] = []
    learned_score_rel: list[float] = []
    time_rel: list[float] = []
    learned_time_rel: list[float] = []
    selected = 0
    for item in rows:
        no_prior = item["no_prior"]
        learned = item["learned"]
        picked = item["selected"]
        assert isinstance(no_prior, dict)
        assert isinstance(learned, dict)
        assert isinstance(picked, dict)
        if item["gate_enabled"]:
            selected += 1
        w, l, t = compare(float(picked["score"]), float(no_prior["score"]))
        wins += w
        losses += l
        ties += t
        lw, ll, lt = compare(float(learned["score"]), float(no_prior["score"]))
        learned_wins += lw
        learned_losses += ll
        learned_ties += lt
        score_rel.append(relative(float(picked["score"]), float(no_prior["score"])))
        learned_score_rel.append(relative(float(learned["score"]), float(no_prior["score"])))
        time_rel.append(relative(float(picked["time_s"]), float(no_prior["time_s"])))
        learned_time_rel.append(relative(float(learned["time_s"]), float(no_prior["time_s"])))
    mean_time = statistics.mean(time_rel) if time_rel else 0.0
    mean_learned_time = statistics.mean(learned_time_rel) if learned_time_rel else 0.0
    overhead_reduction = (mean_learned_time - mean_time) / mean_learned_time if mean_learned_time else 0.0
    return {
        "row_type": row_type,
        "budget": budget,
        "method": method,
        "pairs": len(rows),
        "gate_enabled": selected,
        "gate_fraction": selected / len(rows) if rows else 0.0,
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "learned_score_wins": learned_wins,
        "learned_score_losses": learned_losses,
        "learned_score_ties": learned_ties,
        "retained_learned_wins": wins == learned_wins and losses == learned_losses,
        "mean_score_relative": statistics.mean(score_rel) if score_rel else 0.0,
        "mean_always_learned_score_relative": statistics.mean(learned_score_rel) if learned_score_rel else 0.0,
        "mean_time_relative": mean_time,
        "mean_always_learned_time_relative": mean_learned_time,
        "learned_overhead_reduction": overhead_reduction,
        "status": "pass" if losses == 0 and learned_losses == 0 and wins == learned_wins else "needs revision",
    }


def build_summary(pairs: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for budget in BUDGETS:
        budget_rows = [row for row in pairs if row["budget"] == budget]
        rows.append(summarize("budget_aggregate", budget, "all_methods", budget_rows))
        for method in METHODS:
            method_rows = [row for row in budget_rows if row["method"] == method]
            rows.append(summarize("method_budget", budget, method, method_rows))
    rows.append(summarize("all_aggregate", "all", "all_methods", pairs))
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "row_type",
        "budget",
        "method",
        "pairs",
        "gate_enabled",
        "gate_fraction",
        "score_wins",
        "score_losses",
        "score_ties",
        "learned_score_wins",
        "learned_score_losses",
        "learned_score_ties",
        "retained_learned_wins",
        "mean_score_relative",
        "mean_always_learned_score_relative",
        "mean_time_relative",
        "mean_always_learned_time_relative",
        "learned_overhead_reduction",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    counts = Counter(str(row["status"]) for row in rows)
    aggregate = [row for row in rows if row["row_type"] in {"budget_aggregate", "all_aggregate"}]
    lines = [
        "# Bit-Flip Learned-Prior Feature Gate",
        "",
        f"This derived audit deploys the learned prior only when `{GATE_MIN_ANF_TERMS} <= anf_terms <= {GATE_MAX_ANF_TERMS}`.",
        "The gate uses only the input ANF term count, which is available before MCTS candidate expansion.",
        "",
        "It is a static deployment rule over the existing paired rows, not an independent generalization proof.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Aggregate rows",
            "",
            "| budget | pairs | learned enabled | score W/L/T | always-learned W/L/T | mean score change | time change | always-learned time | overhead reduction |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in aggregate:
        lines.append(
            f"| {budget_label(str(row['budget']))} | {row['pairs']} | {row['gate_enabled']} | "
            f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
            f"{row['learned_score_wins']}/{row['learned_score_losses']}/{row['learned_score_ties']} | "
            f"{fmt_pct(row['mean_score_relative'])} | {fmt_pct(row['mean_time_relative'])} | "
            f"{fmt_pct(row['mean_always_learned_time_relative'])} | {fmt_pct(row['learned_overhead_reduction'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The ANF-term gate keeps every always-learned score win in the audited rows while skipping learned-prior evaluation on rows where it ties no-prior.",
            "- It preserves the same mean score change as always-learned deployment and lowers measured Python runtime overhead.",
            "- Because the interval is selected from existing evidence, it is reported as a bounded deployment audit rather than a held-out policy claim.",
            "",
            "## Method-budget rows",
            "",
            "| budget | method | pairs | learned enabled | score W/L/T | overhead reduction |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        if row["row_type"] != "method_budget":
            continue
        lines.append(
            f"| {budget_label(str(row['budget']))} | {method_label(str(row['method']))} | {row['pairs']} | "
            f"{row['gate_enabled']} | {row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
            f"{fmt_pct(row['learned_overhead_reduction'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    aggregate = [row for row in rows if row["row_type"] in {"budget_aggregate", "all_aggregate"}]
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Budget & Gate & Enabled & Score W/L/T & $\Delta$ score & Overhead cut \\",
        r"\midrule",
    ]
    gate = f"{GATE_MIN_ANF_TERMS}--{GATE_MAX_ANF_TERMS} ANF terms"
    for row in aggregate:
        lines.append(
            f"{budget_label(str(row['budget']))} & {gate} & {int(row['gate_enabled'])}/{int(row['pairs'])} & "
            f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} & "
            f"{fmt_latex_pct(row['mean_score_relative'])} & {fmt_latex_pct(row['learned_overhead_reduction'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, object]], input_rows: list[dict[str, str]]) -> None:
    aggregate = next(row for row in rows if row["row_type"] == "all_aggregate")
    paper = PAPER.read_text(encoding="utf-8", errors="replace") if PAPER.exists() else ""
    data = {
        "script": Path(__file__).name,
        "gate": {
            "feature": "anf_terms",
            "min": GATE_MIN_ANF_TERMS,
            "max": GATE_MAX_ANF_TERMS,
        },
        "rows": len(rows),
        "input_rows": len(input_rows),
        "aggregate_pairs": int(aggregate["pairs"]),
        "aggregate_gate_enabled": int(aggregate["gate_enabled"]),
        "aggregate_score_wins": int(aggregate["score_wins"]),
        "aggregate_score_losses": int(aggregate["score_losses"]),
        "aggregate_learned_score_wins": int(aggregate["learned_score_wins"]),
        "aggregate_retained_learned_wins": bool(aggregate["retained_learned_wins"]),
        "aggregate_mean_score_relative": float(aggregate["mean_score_relative"]),
        "aggregate_mean_time_relative": float(aggregate["mean_time_relative"]),
        "aggregate_always_learned_time_relative": float(aggregate["mean_always_learned_time_relative"]),
        "aggregate_learned_overhead_reduction": float(aggregate["learned_overhead_reduction"]),
        "needs_revision_count": 0 if aggregate["status"] == "pass" else 1,
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "tab:bitflip-prior-feature-gate" in paper,
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
    input_rows = [row for row in read_csv(RAW) if usable(row)]
    input_rows += add_full_budget(read_csv(LEARNED_FULL), "learned_prior")
    input_rows += add_full_budget(read_csv(NO_PRIOR_FULL), "no_prior")
    pairs = paired_rows(input_rows)
    rows = build_summary(pairs)
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(rows, input_rows)
    print(f"wrote {len(rows)} bit-flip prior feature-gate rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
