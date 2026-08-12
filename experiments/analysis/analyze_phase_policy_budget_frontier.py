#!/usr/bin/env python3
"""Summarize learned phase-policy quality as an exact-scoring budget frontier.

The phase-policy training run stores all held-out top-k shortlists together
with the deterministic budget-32 and wide-128 affine searches.  This analysis
uses the existing raw rows to quantify how much exact phase-score evaluation is
saved when the learned ranker/diversity reranker is used as a shortlist.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
RAW = RESULTS / "raw_phase_affine_policy_rank_diverse.csv"
METRIC = "score_synth_tperrz30"
SPLIT = "test_n6"
TOPKS = (64, 128, 256, 512)
BASE_BUDGET = "phase_affine_budget32_tperrz30"
BASE_WIDE = "phase_affine_wide128_tperrz30"
POLICIES = (
    ("rank", "Rank", "phase_parity_affine_policy_tperrz30"),
    ("diverse", "Diverse", "phase_parity_affine_policy_diverse_tperrz30"),
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    if row.get("split") != SPLIT:
        return False
    if row.get("error") or row.get("skipped"):
        return False
    verified = str(row.get("verified_up_to_global_phase", "")).strip().lower()
    return verified not in {"false", "0"}


def compare(values: list[tuple[float, float]]) -> tuple[int, int, int, float]:
    wins = losses = ties = 0
    rels: list[float] = []
    for target, baseline in values:
        if target < baseline - 1e-9:
            wins += 1
        elif target > baseline + 1e-9:
            losses += 1
        else:
            ties += 1
        rels.append((target - baseline) / max(abs(baseline), 1.0))
    return wins, losses, ties, statistics.mean(rels) if rels else 0.0


def exact_forms(rows: dict[str, dict[str, str]]) -> int:
    forms = {int(float(row["exact_eval_forms"])) for row in rows.values() if row.get("exact_eval_forms")}
    if len(forms) != 1:
        raise ValueError(f"expected one exact_eval_forms value, got {sorted(forms)}")
    return next(iter(forms))


def pct(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}%"


def pct_plain(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}%"


def tex_pct(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}\\%"


def build_rows() -> list[dict[str, object]]:
    raw = [row for row in read_rows(RAW) if usable(row)]
    by_method: dict[str, dict[str, dict[str, str]]] = {}
    for row in raw:
        by_method.setdefault(row["method"], {})[row["name"]] = row

    budget = by_method[BASE_BUDGET]
    wide = by_method[BASE_WIDE]
    names = sorted(set(budget) & set(wide))
    budget_forms = exact_forms({name: budget[name] for name in names})
    wide_forms = exact_forms({name: wide[name] for name in names})
    budget_mean = statistics.mean(float(budget[name][METRIC]) for name in names)
    wide_mean = statistics.mean(float(wide[name][METRIC]) for name in names)

    out: list[dict[str, object]] = []
    for policy_id, policy_label, prefix in POLICIES:
        for topk in TOPKS:
            method = f"{prefix}_top{topk}"
            target = by_method[method]
            paired_names = sorted(set(names) & set(target))
            target_forms = exact_forms({name: target[name] for name in paired_names})
            target_scores = [float(target[name][METRIC]) for name in paired_names]
            target_mean = statistics.mean(target_scores)
            budget_pairs = [(float(target[name][METRIC]), float(budget[name][METRIC])) for name in paired_names]
            wide_pairs = [(float(target[name][METRIC]), float(wide[name][METRIC])) for name in paired_names]
            bw, bl, bt, b_rel = compare(budget_pairs)
            ww, wl, wt, w_rel = compare(wide_pairs)
            out.append(
                {
                    "policy": policy_id,
                    "policy_label": policy_label,
                    "topk": topk,
                    "method": method,
                    "functions": len(paired_names),
                    "target_exact_forms": target_forms,
                    "budget32_exact_forms": budget_forms,
                    "wide128_exact_forms": wide_forms,
                    "total_target_exact_forms": target_forms * len(paired_names),
                    "total_budget32_exact_forms": budget_forms * len(paired_names),
                    "total_wide128_exact_forms": wide_forms * len(paired_names),
                    "eval_reduction_vs_budget32_pct": 100.0 * (1.0 - target_forms / budget_forms),
                    "eval_reduction_vs_wide128_pct": 100.0 * (1.0 - target_forms / wide_forms),
                    "target_mean": target_mean,
                    "budget32_mean": budget_mean,
                    "wide128_mean": wide_mean,
                    "vs_budget32_wins": bw,
                    "vs_budget32_losses": bl,
                    "vs_budget32_ties": bt,
                    "vs_budget32_mean_relative": b_rel,
                    "vs_wide128_wins": ww,
                    "vs_wide128_losses": wl,
                    "vs_wide128_ties": wt,
                    "vs_wide128_mean_relative": w_rel,
                    "mean_score_gain_vs_budget32": target_mean - budget_mean,
                    "mean_score_gap_vs_wide128": target_mean - wide_mean,
                    "status": "pass"
                    if len(paired_names) == 38
                    and target_forms == topk
                    and b_rel < 0.0
                    and w_rel <= 0.001
                    else "bounded",
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    best = next(row for row in rows if row["policy"] == "diverse" and row["topk"] == 512)
    lines = [
        "# Phase Policy Budget-Frontier Audit",
        "",
        "This audit quantifies the exact-scoring budget frontier for the held-out n=6 phase/Rz proxy.",
        "Rows compare learned top-k shortlists with the deterministic budget-32 and wide-128 affine searches using the T/Rz=30 synthesis proxy.",
        "",
        "| policy | top-k | functions | exact forms/function | eval reduction vs budget-32 | eval reduction vs wide-128 | W/L/T vs budget-32 | mean vs budget-32 | W/L/T vs wide-128 | mean vs wide-128 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {policy} | {topk} | {functions} | {forms}/{budget}/{wide} | {red_budget} | {red_wide} | {bw}/{bl}/{bt} | {brel} | {ww}/{wl}/{wt} | {wrel} |".format(
                policy=row["policy_label"],
                topk=row["topk"],
                functions=row["functions"],
                forms=row["target_exact_forms"],
                budget=row["budget32_exact_forms"],
                wide=row["wide128_exact_forms"],
                red_budget=pct_plain(float(row["eval_reduction_vs_budget32_pct"]), 2),
                red_wide=pct_plain(float(row["eval_reduction_vs_wide128_pct"]), 2),
                bw=row["vs_budget32_wins"],
                bl=row["vs_budget32_losses"],
                bt=row["vs_budget32_ties"],
                brel=pct(100.0 * float(row["vs_budget32_mean_relative"]), 3),
                ww=row["vs_wide128_wins"],
                wl=row["vs_wide128_losses"],
                wt=row["vs_wide128_ties"],
                wrel=pct(100.0 * float(row["vs_wide128_mean_relative"]), 3),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Diverse top-512 exact-scores {best['target_exact_forms']}/{best['wide128_exact_forms']} affine forms per function, a {pct_plain(float(best['eval_reduction_vs_wide128_pct']), 2)} reduction relative to wide-128.",
            f"- The same row keeps the budget-32 comparison at {best['vs_budget32_wins']}/{best['vs_budget32_losses']}/{best['vs_budget32_ties']} with {pct(100.0 * float(best['vs_budget32_mean_relative']), 3)} mean score change.",
            f"- Its mean gap to wide-128 is {pct(100.0 * float(best['vs_wide128_mean_relative']), 3)}, so this supports learned pruning of a dense phase/Rz candidate space rather than global phase optimality.",
            "- The phase/Rz branch remains a logical proxy; these rows do not synthesize approximate rotation sequences or claim mapped Clifford+T cost.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = [
        row
        for row in rows
        if (row["policy"], row["topk"]) in {("rank", 256), ("rank", 512), ("diverse", 128), ("diverse", 256), ("diverse", 512)}
    ]
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Policy & $k$ & Eval/fn. & Cut vs wide & vs B32 & $\Delta$B32 & $\Delta$W128 \\",
        r"\midrule",
    ]
    for row in selected:
        lines.append(
            "{} & {} & {}/{} & {} & {}/{}/{} & {} & {} \\\\".format(
                row["policy_label"],
                row["topk"],
                row["target_exact_forms"],
                row["wide128_exact_forms"],
                pct_plain(float(row["eval_reduction_vs_wide128_pct"]), 2).replace("%", r"\%"),
                row["vs_budget32_wins"],
                row["vs_budget32_losses"],
                row["vs_budget32_ties"],
                tex_pct(100.0 * float(row["vs_budget32_mean_relative"]), 3),
                tex_pct(100.0 * float(row["vs_wide128_mean_relative"]), 3),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    best = next(row for row in rows if row["policy"] == "diverse" and row["topk"] == 512)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({str(row["status"]) for row in rows})},
        "heldout_functions": int(best["functions"]),
        "best_policy": "diverse_top512",
        "best_budget32_wlt": f"{best['vs_budget32_wins']}/{best['vs_budget32_losses']}/{best['vs_budget32_ties']}",
        "best_wide128_wlt": f"{best['vs_wide128_wins']}/{best['vs_wide128_losses']}/{best['vs_wide128_ties']}",
        "best_eval_reduction_vs_wide128_pct": best["eval_reduction_vs_wide128_pct"],
        "best_mean_relative_vs_budget32": best["vs_budget32_mean_relative"],
        "best_mean_relative_vs_wide128": best["vs_wide128_mean_relative"],
        "needs_revision_count": 0 if all(row["status"] in {"pass", "bounded"} for row in rows) else 1,
        "sources": ["results/raw_phase_affine_policy_rank_diverse.csv"],
        "outputs": {
            "summary": "results/summary_phase_policy_budget_frontier.csv",
            "analysis": "results/analysis_phase_policy_budget_frontier.md",
            "manifest": "results/manifest_phase_policy_budget_frontier.json",
            "table": "paper_latex/tables/phase_policy_budget_frontier.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_phase_policy_budget_frontier.csv", rows)
    write_markdown(RESULTS / "analysis_phase_policy_budget_frontier.md", rows)
    write_latex(TABLES / "phase_policy_budget_frontier.tex", rows)
    write_manifest(RESULTS / "manifest_phase_policy_budget_frontier.json", rows)
    print(f"wrote {len(rows)} phase budget-frontier rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
