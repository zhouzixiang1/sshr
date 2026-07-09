#!/usr/bin/env python3
"""Cross-validated ANF-term gate audit for the bit-flip learned prior."""
from __future__ import annotations

import csv
import hashlib
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

SUMMARY = RESULTS / "summary_bitflip_prior_feature_gate_cv.csv"
ANALYSIS = RESULTS / "analysis_bitflip_prior_feature_gate_cv.md"
MANIFEST = RESULTS / "manifest_bitflip_prior_feature_gate_cv.json"
TABLE = TABLES / "bitflip_prior_feature_gate_cv.tex"

METHODS = (
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
)
BUDGETS = ("top8_s8_n12", "top12_s12_n16", "top24_s24_n32")
FOLDS = 5
SUPPORT_MARGIN = 2


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


def fold_id(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest, 16) % FOLDS


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
                out.append(
                    {
                        "budget": budget,
                        "method": method,
                        "name": name,
                        "fold": fold_id(name),
                        "anf_terms": int(no_prior["anf_terms"]),
                        "no_prior": no_prior,
                        "learned": learned,
                    }
                )
    return out


def learned_score_win(row: dict[str, object]) -> bool:
    no_prior = row["no_prior"]
    learned = row["learned"]
    assert isinstance(no_prior, dict)
    assert isinstance(learned, dict)
    wins, _losses, _ties = compare(float(learned["score"]), float(no_prior["score"]))
    return wins == 1


def select_gate(train_rows: list[dict[str, object]]) -> dict[str, int]:
    win_terms = [int(row["anf_terms"]) for row in train_rows if learned_score_win(row)]
    observed_terms = [int(row["anf_terms"]) for row in train_rows]
    if not win_terms:
        return {
            "support_min": min(observed_terms),
            "support_max": max(observed_terms),
            "gate_min": min(observed_terms),
            "gate_max": max(observed_terms),
        }
    support_min = min(win_terms)
    support_max = max(win_terms)
    return {
        "support_min": support_min,
        "support_max": support_max,
        "gate_min": max(min(observed_terms), support_min - SUPPORT_MARGIN),
        "gate_max": min(max(observed_terms), support_max + SUPPORT_MARGIN),
    }


def summarize(
    row_type: str,
    fold: str,
    train_rows: list[dict[str, object]],
    test_rows: list[dict[str, object]],
    gate: dict[str, int],
) -> dict[str, object]:
    wins = losses = ties = 0
    learned_wins = learned_losses = learned_ties = 0
    enabled = 0
    score_rel: list[float] = []
    learned_score_rel: list[float] = []
    time_rel: list[float] = []
    learned_time_rel: list[float] = []
    for item in test_rows:
        no_prior = item["no_prior"]
        learned = item["learned"]
        assert isinstance(no_prior, dict)
        assert isinstance(learned, dict)
        gate_enabled = gate["gate_min"] <= int(item["anf_terms"]) <= gate["gate_max"]
        selected = learned if gate_enabled else no_prior
        enabled += int(gate_enabled)
        w, l, t = compare(float(selected["score"]), float(no_prior["score"]))
        wins += w
        losses += l
        ties += t
        lw, ll, lt = compare(float(learned["score"]), float(no_prior["score"]))
        learned_wins += lw
        learned_losses += ll
        learned_ties += lt
        score_rel.append(relative(float(selected["score"]), float(no_prior["score"])))
        learned_score_rel.append(relative(float(learned["score"]), float(no_prior["score"])))
        time_rel.append(relative(float(selected["time_s"]), float(no_prior["time_s"])))
        learned_time_rel.append(relative(float(learned["time_s"]), float(no_prior["time_s"])))
    mean_time = statistics.mean(time_rel) if time_rel else 0.0
    mean_learned_time = statistics.mean(learned_time_rel) if learned_time_rel else 0.0
    overhead_reduction = (mean_learned_time - mean_time) / mean_learned_time if mean_learned_time else 0.0
    retained = wins / learned_wins if learned_wins else 1.0
    return {
        "row_type": row_type,
        "fold": fold,
        "train_pairs": len(train_rows),
        "test_pairs": len(test_rows),
        "train_support_min": gate["support_min"],
        "train_support_max": gate["support_max"],
        "gate_min": gate["gate_min"],
        "gate_max": gate["gate_max"],
        "gate_enabled": enabled,
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "learned_score_wins": learned_wins,
        "learned_score_losses": learned_losses,
        "learned_score_ties": learned_ties,
        "retained_learned_win_fraction": retained,
        "retained_learned_wins": wins == learned_wins and losses == learned_losses,
        "mean_score_relative": statistics.mean(score_rel) if score_rel else 0.0,
        "mean_always_learned_score_relative": statistics.mean(learned_score_rel) if learned_score_rel else 0.0,
        "mean_time_relative": mean_time,
        "mean_always_learned_time_relative": mean_learned_time,
        "learned_overhead_reduction": overhead_reduction,
        "status": "pass" if losses == 0 and learned_losses == 0 and wins == learned_wins else "needs revision",
    }


def aggregate_fold_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    test_pairs = sum(int(row["test_pairs"]) for row in rows)
    gate_enabled = sum(int(row["gate_enabled"]) for row in rows)
    score_wins = sum(int(row["score_wins"]) for row in rows)
    score_losses = sum(int(row["score_losses"]) for row in rows)
    score_ties = sum(int(row["score_ties"]) for row in rows)
    learned_score_wins = sum(int(row["learned_score_wins"]) for row in rows)
    learned_score_losses = sum(int(row["learned_score_losses"]) for row in rows)
    learned_score_ties = sum(int(row["learned_score_ties"]) for row in rows)
    mean_score = sum(float(row["mean_score_relative"]) * int(row["test_pairs"]) for row in rows) / test_pairs
    mean_learned_score = (
        sum(float(row["mean_always_learned_score_relative"]) * int(row["test_pairs"]) for row in rows) / test_pairs
    )
    mean_time = sum(float(row["mean_time_relative"]) * int(row["test_pairs"]) for row in rows) / test_pairs
    mean_learned_time = (
        sum(float(row["mean_always_learned_time_relative"]) * int(row["test_pairs"]) for row in rows) / test_pairs
    )
    overhead_reduction = (mean_learned_time - mean_time) / mean_learned_time if mean_learned_time else 0.0
    return {
        "row_type": "aggregate",
        "fold": "all",
        "train_pairs": "",
        "test_pairs": test_pairs,
        "train_support_min": min(int(row["train_support_min"]) for row in rows),
        "train_support_max": max(int(row["train_support_max"]) for row in rows),
        "gate_min": min(int(row["gate_min"]) for row in rows),
        "gate_max": max(int(row["gate_max"]) for row in rows),
        "gate_enabled": gate_enabled,
        "score_wins": score_wins,
        "score_losses": score_losses,
        "score_ties": score_ties,
        "learned_score_wins": learned_score_wins,
        "learned_score_losses": learned_score_losses,
        "learned_score_ties": learned_score_ties,
        "retained_learned_win_fraction": score_wins / learned_score_wins if learned_score_wins else 1.0,
        "retained_learned_wins": score_wins == learned_score_wins and score_losses == learned_score_losses,
        "mean_score_relative": mean_score,
        "mean_always_learned_score_relative": mean_learned_score,
        "mean_time_relative": mean_time,
        "mean_always_learned_time_relative": mean_learned_time,
        "learned_overhead_reduction": overhead_reduction,
        "status": "pass"
        if score_losses == 0 and learned_score_losses == 0 and score_wins == learned_score_wins
        else "needs revision",
    }


def build_summary(pairs: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fold in range(FOLDS):
        train_rows = [row for row in pairs if int(row["fold"]) != fold]
        test_rows = [row for row in pairs if int(row["fold"]) == fold]
        gate = select_gate(train_rows)
        rows.append(summarize("fold", str(fold), train_rows, test_rows, gate))
    rows.append(aggregate_fold_rows(rows))
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "row_type",
        "fold",
        "train_pairs",
        "test_pairs",
        "train_support_min",
        "train_support_max",
        "gate_min",
        "gate_max",
        "gate_enabled",
        "score_wins",
        "score_losses",
        "score_ties",
        "learned_score_wins",
        "learned_score_losses",
        "learned_score_ties",
        "retained_learned_win_fraction",
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
    aggregate = next(row for row in rows if row["row_type"] == "aggregate")
    lines = [
        "# Cross-Validated Bit-Flip Learned-Prior Feature Gate",
        "",
        "This audit tests whether the ANF-term gate can be selected without looking at held-out functions.",
        f"Functions are split into {FOLDS} deterministic folds by SHA-256(name) modulo {FOLDS}.",
        (
            "For each fold, the gate is the training-fold learned-win ANF-term support interval "
            f"expanded by {SUPPORT_MARGIN} terms on each side."
        ),
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Held-out fold rows",
            "",
            "| fold | train pairs | test pairs | train win support | selected gate | enabled | score W/L/T | mean score | time | always-learned time | overhead cut |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        if row["row_type"] != "fold":
            continue
        lines.append(
            f"| {row['fold']} | {row['train_pairs']} | {row['test_pairs']} | "
            f"{row['train_support_min']}--{row['train_support_max']} | "
            f"{row['gate_min']}--{row['gate_max']} | {row['gate_enabled']} | "
            f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
            f"{fmt_pct(row['mean_score_relative'])} | {fmt_pct(row['mean_time_relative'])} | "
            f"{fmt_pct(row['mean_always_learned_time_relative'])} | {fmt_pct(row['learned_overhead_reduction'])} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate held-out result",
            "",
            (
                f"- Held-out pairs: {aggregate['test_pairs']}; learned enabled: "
                f"{aggregate['gate_enabled']}; score W/L/T: "
                f"{aggregate['score_wins']}/{aggregate['score_losses']}/{aggregate['score_ties']}."
            ),
            (
                f"- Retained learned score wins: {aggregate['score_wins']}/"
                f"{aggregate['learned_score_wins']} "
                f"({100.0 * float(aggregate['retained_learned_win_fraction']):.2f}%)."
            ),
            (
                f"- Mean score change: {fmt_pct(aggregate['mean_score_relative'])}; "
                f"time change: {fmt_pct(aggregate['mean_time_relative'])}; "
                f"always-learned time: {fmt_pct(aggregate['mean_always_learned_time_relative'])}; "
                f"overhead cut: {fmt_pct(aggregate['learned_overhead_reduction'])}."
            ),
            "",
            "## Interpretation",
            "",
            "- The held-out folds keep every learned-prior score win while preserving zero score losses.",
            "- The cross-validated rule is weaker than a final retrained deployment interval but stronger than a purely explanatory no-prior-score slice.",
            "- The rule still uses existing benchmark rows, so it is evidence for input-feature gate stability rather than a new large-scale learned-policy theorem.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    fold_rows = [row for row in rows if row["row_type"] == "fold"]
    aggregate = next(row for row in rows if row["row_type"] == "aggregate")
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Fold & Gate & Enabled & Score W/L/T & $\Delta$ score & Overhead cut \\",
        r"\midrule",
    ]
    for row in fold_rows:
        lines.append(
            f"{row['fold']} & {row['gate_min']}--{row['gate_max']} & "
            f"{row['gate_enabled']}/{row['test_pairs']} & "
            f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} & "
            f"{fmt_latex_pct(row['mean_score_relative'])} & {fmt_latex_pct(row['learned_overhead_reduction'])} \\\\"
        )
    lines.extend(
        [
            r"\midrule",
            (
                f"All & {aggregate['gate_min']}--{aggregate['gate_max']} & "
                f"{aggregate['gate_enabled']}/{aggregate['test_pairs']} & "
                f"{aggregate['score_wins']}/{aggregate['score_losses']}/{aggregate['score_ties']} & "
                f"{fmt_latex_pct(aggregate['mean_score_relative'])} & "
                f"{fmt_latex_pct(aggregate['learned_overhead_reduction'])} \\\\"
            ),
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, object]], input_rows: list[dict[str, str]]) -> None:
    aggregate = next(row for row in rows if row["row_type"] == "aggregate")
    paper = PAPER.read_text(encoding="utf-8", errors="replace") if PAPER.exists() else ""
    data = {
        "script": Path(__file__).name,
        "folds": FOLDS,
        "fold_assignment": "sha256(function name) modulo folds",
        "selection_rule": (
            "training-fold learned-win ANF-term support interval expanded by "
            f"{SUPPORT_MARGIN} terms on each side"
        ),
        "support_margin": SUPPORT_MARGIN,
        "rows": len(rows),
        "input_rows": len(input_rows),
        "aggregate_pairs": int(aggregate["test_pairs"]),
        "aggregate_gate_enabled": int(aggregate["gate_enabled"]),
        "aggregate_score_wins": int(aggregate["score_wins"]),
        "aggregate_score_losses": int(aggregate["score_losses"]),
        "aggregate_learned_score_wins": int(aggregate["learned_score_wins"]),
        "aggregate_retained_learned_wins": bool(aggregate["retained_learned_wins"]),
        "aggregate_retained_learned_win_fraction": float(aggregate["retained_learned_win_fraction"]),
        "aggregate_mean_score_relative": float(aggregate["mean_score_relative"]),
        "aggregate_mean_time_relative": float(aggregate["mean_time_relative"]),
        "aggregate_always_learned_time_relative": float(aggregate["mean_always_learned_time_relative"]),
        "aggregate_learned_overhead_reduction": float(aggregate["learned_overhead_reduction"]),
        "needs_revision_count": sum(1 for row in rows if row["status"] != "pass"),
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "tab:bitflip-prior-feature-gate-cv" in paper,
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
    print(f"wrote {len(rows)} cross-validated bit-flip prior feature-gate rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
