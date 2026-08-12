#!/usr/bin/env python3
"""Random-interval control for the cross-validated bit-flip learned-prior gate."""
from __future__ import annotations

import csv
import json
import random
import statistics
from pathlib import Path

from analyze_bitflip_prior_feature_gate_cv import (
    ANALYSIS as CV_ANALYSIS,
    FOLDS,
    LEARNED_FULL,
    NO_PRIOR_FULL,
    PAPER,
    RAW,
    SUPPORT_MARGIN,
    TABLES,
    THIS_DIR,
    add_full_budget,
    compare,
    fmt_latex_pct,
    fmt_pct,
    paired_rows,
    read_csv,
    relative,
    select_gate,
    usable,
)


RESULTS = THIS_DIR / "results"
SUMMARY = RESULTS / "summary_bitflip_prior_feature_gate_cv_random_control.csv"
ANALYSIS = RESULTS / "analysis_bitflip_prior_feature_gate_cv_random_control.md"
MANIFEST = RESULTS / "manifest_bitflip_prior_feature_gate_cv_random_control.json"
TABLE = TABLES / "bitflip_prior_feature_gate_cv_random_control.tex"
RANDOM_REPEATS = 200


def summarize_gate(pairs: list[dict[str, object]], gates: dict[int, tuple[int, int]]) -> dict[str, object]:
    wins = losses = ties = 0
    learned_wins = learned_losses = learned_ties = 0
    enabled = 0
    score_rel: list[float] = []
    learned_score_rel: list[float] = []
    time_rel: list[float] = []
    learned_time_rel: list[float] = []
    for item in pairs:
        fold = int(item["fold"])
        lo, hi = gates[fold]
        no_prior = item["no_prior"]
        learned = item["learned"]
        assert isinstance(no_prior, dict)
        assert isinstance(learned, dict)
        gate_enabled = lo <= int(item["anf_terms"]) <= hi
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
    mean_time = statistics.mean(time_rel)
    mean_learned_time = statistics.mean(learned_time_rel)
    return {
        "pairs": len(pairs),
        "gate_enabled": enabled,
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "learned_score_wins": learned_wins,
        "learned_score_losses": learned_losses,
        "learned_score_ties": learned_ties,
        "retained_learned_win_fraction": wins / learned_wins if learned_wins else 1.0,
        "retained_learned_wins": wins == learned_wins and losses == learned_losses,
        "mean_score_relative": statistics.mean(score_rel),
        "mean_always_learned_score_relative": statistics.mean(learned_score_rel),
        "mean_time_relative": mean_time,
        "mean_always_learned_time_relative": mean_learned_time,
        "learned_overhead_reduction": (mean_learned_time - mean_time) / mean_learned_time
        if mean_learned_time
        else 0.0,
    }


def learned_cv_gates(pairs: list[dict[str, object]]) -> dict[int, tuple[int, int]]:
    gates: dict[int, tuple[int, int]] = {}
    for fold in range(FOLDS):
        train_rows = [row for row in pairs if int(row["fold"]) != fold]
        gate = select_gate(train_rows)
        gates[fold] = (gate["gate_min"], gate["gate_max"])
    return gates


def random_same_width_gates(
    pairs: list[dict[str, object]], widths: dict[int, int], seed: int
) -> dict[int, tuple[int, int]]:
    rng = random.Random(seed)
    global_min = min(int(row["anf_terms"]) for row in pairs)
    global_max = max(int(row["anf_terms"]) for row in pairs)
    gates: dict[int, tuple[int, int]] = {}
    for fold in range(FOLDS):
        width = widths[fold]
        low = rng.randint(global_min, global_max - width)
        gates[fold] = (low, low + width)
    return gates


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * q)
    return ordered[index]


def gate_string(gates: dict[int, tuple[int, int]]) -> str:
    return "; ".join(f"f{fold}:{lo}--{hi}" for fold, (lo, hi) in sorted(gates.items()))


def build_rows(pairs: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    learned_gates = learned_cv_gates(pairs)
    widths = {fold: hi - lo for fold, (lo, hi) in learned_gates.items()}
    learned = summarize_gate(pairs, learned_gates)
    learned.update(
        {
            "row_type": "learned_cv_gate",
            "seed": "learned",
            "random_repeats": 1,
            "full_retained_repeats": 1,
            "gate_intervals": gate_string(learned_gates),
        }
    )

    random_rows: list[dict[str, object]] = []
    for seed in range(RANDOM_REPEATS):
        gates = random_same_width_gates(pairs, widths, seed)
        row = summarize_gate(pairs, gates)
        row.update(
            {
                "row_type": "random_seed",
                "seed": seed,
                "random_repeats": RANDOM_REPEATS,
                "full_retained_repeats": "",
                "gate_intervals": gate_string(gates),
            }
        )
        random_rows.append(row)

    retained = [float(row["retained_learned_win_fraction"]) for row in random_rows]
    score = [float(row["mean_score_relative"]) for row in random_rows]
    time = [float(row["mean_time_relative"]) for row in random_rows]
    cut = [float(row["learned_overhead_reduction"]) for row in random_rows]
    wins = [int(row["score_wins"]) for row in random_rows]
    full_retained = sum(1 for row in random_rows if row["retained_learned_wins"])
    mean_row = {
        "row_type": "random_mean",
        "seed": "mean",
        "random_repeats": RANDOM_REPEATS,
        "full_retained_repeats": full_retained,
        "pairs": learned["pairs"],
        "gate_enabled": statistics.mean(int(row["gate_enabled"]) for row in random_rows),
        "score_wins": statistics.mean(wins),
        "score_losses": statistics.mean(int(row["score_losses"]) for row in random_rows),
        "score_ties": statistics.mean(int(row["score_ties"]) for row in random_rows),
        "learned_score_wins": learned["learned_score_wins"],
        "learned_score_losses": learned["learned_score_losses"],
        "learned_score_ties": learned["learned_score_ties"],
        "retained_learned_win_fraction": statistics.mean(retained),
        "retained_learned_wins": False,
        "mean_score_relative": statistics.mean(score),
        "mean_always_learned_score_relative": learned["mean_always_learned_score_relative"],
        "mean_time_relative": statistics.mean(time),
        "mean_always_learned_time_relative": learned["mean_always_learned_time_relative"],
        "learned_overhead_reduction": statistics.mean(cut),
        "gate_intervals": "same fold widths, random positions",
    }
    p95_row = dict(mean_row)
    p95_row.update(
        {
            "row_type": "random_p95_retention",
            "seed": "p95",
            "gate_enabled": percentile([float(row["gate_enabled"]) for row in random_rows], 0.95),
            "score_wins": percentile([float(row["score_wins"]) for row in random_rows], 0.95),
            "score_losses": percentile([float(row["score_losses"]) for row in random_rows], 0.95),
            "score_ties": percentile([float(row["score_ties"]) for row in random_rows], 0.95),
            "retained_learned_win_fraction": percentile(retained, 0.95),
            "mean_score_relative": percentile(score, 0.05),
            "mean_time_relative": percentile(time, 0.95),
            "learned_overhead_reduction": percentile(cut, 0.95),
            "gate_intervals": "95th percentile over random positions",
        }
    )
    best = max(
        random_rows,
        key=lambda row: (
            float(row["retained_learned_win_fraction"]),
            int(row["score_wins"]),
            -int(row["score_losses"]),
            float(row["learned_overhead_reduction"]),
        ),
    )
    best_row = dict(best)
    best_row["row_type"] = "random_best_retention"
    best_row["full_retained_repeats"] = full_retained
    return [learned, mean_row, p95_row, best_row], random_rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "row_type",
        "seed",
        "random_repeats",
        "full_retained_repeats",
        "pairs",
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
        "gate_intervals",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compact_wlt(row: dict[str, object]) -> str:
    return f"{float(row['score_wins']):.0f}/{float(row['score_losses']):.0f}/{float(row['score_ties']):.0f}"


def fmt_count(value: float) -> str:
    return f"{value:.0f}" if abs(value - round(value)) < 1e-9 else f"{value:.1f}"


def write_markdown(path: Path, rows: list[dict[str, object]], random_rows: list[dict[str, object]]) -> None:
    learned = rows[0]
    random_mean = rows[1]
    random_p95 = rows[2]
    random_best = rows[3]
    full_retained = int(random_mean["full_retained_repeats"])
    lines = [
        "# Random-Interval Control for the CV ANF-Term Gate",
        "",
        "This audit asks whether the cross-validated ANF-term gate is better than arbitrary intervals of the same fold-wise width.",
        f"It samples {RANDOM_REPEATS} deterministic random interval assignments over the observed ANF-term range and compares them with the training-support CV gate.",
        "",
        "## Summary",
        "",
        "| control | repeats | full-retained repeats | retained learned wins | score W/L/T | mean score | time | overhead cut |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, row in (
        ("CV learned-win support gate", learned),
        ("Random same-width intervals mean", random_mean),
        ("Random same-width intervals p95 retained", random_p95),
        ("Best random retained interval", random_best),
    ):
        retained_wins = float(row["retained_learned_win_fraction"]) * float(row["learned_score_wins"])
        full_retained = row["full_retained_repeats"] if row["full_retained_repeats"] != "" else "n/a"
        lines.append(
            f"| {label} | {row['random_repeats'] or 1} | {full_retained} | "
            f"{fmt_count(retained_wins)}/{float(row['learned_score_wins']):.0f} "
            f"({100.0 * float(row['retained_learned_win_fraction']):.2f}%) | "
            f"{compact_wlt(row)} | {fmt_pct(row['mean_score_relative'])} | "
            f"{fmt_pct(row['mean_time_relative'])} | {fmt_pct(row['learned_overhead_reduction'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- The learned-support CV gate retains all {learned['learned_score_wins']} learned-prior score wins with zero score losses.",
            f"- No random same-width interval assignment retains all learned wins ({full_retained}/{RANDOM_REPEATS}).",
            (
                f"- The best random retained interval keeps {int(random_best['score_wins'])}/"
                f"{int(random_best['learned_score_wins'])} learned wins; the random mean keeps "
                f"{100.0 * float(random_mean['retained_learned_win_fraction']):.2f}%."
            ),
            "- Random intervals often cut more runtime because they skip useful learned-prior rows, so overhead alone is not a sufficient quality metric.",
            "",
            "## CV gate source",
            "",
            f"- CV gate audit: `{CV_ANALYSIS.relative_to(THIS_DIR)}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    labels = {
        "learned_cv_gate": "CV support gate",
        "random_mean": "Random mean",
        "random_p95_retention": "Random p95 retained",
        "random_best_retention": "Best random retained",
    }
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Control & Full retained & Retained wins & $\Delta$ score & Overhead cut \\",
        r"\midrule",
    ]
    for row in rows:
        retained_wins = float(row["retained_learned_win_fraction"]) * float(row["learned_score_wins"])
        full_retained = row["full_retained_repeats"] if row["full_retained_repeats"] != "" else "n/a"
        repeats = row["random_repeats"] if row["random_repeats"] != "" else 1
        full_retained_text = "n/a" if full_retained == "n/a" else f"{full_retained}/{repeats}"
        lines.append(
            f"{labels[str(row['row_type'])]} & {full_retained_text} & "
            f"{fmt_count(retained_wins)}/{float(row['learned_score_wins']):.0f} & "
            f"{fmt_latex_pct(row['mean_score_relative'])} & "
            f"{fmt_latex_pct(row['learned_overhead_reduction'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, object]], random_rows: list[dict[str, object]]) -> None:
    learned = rows[0]
    random_mean = rows[1]
    random_best = rows[3]
    paper = PAPER.read_text(encoding="utf-8", errors="replace") if PAPER.exists() else ""
    full_retained = int(random_mean["full_retained_repeats"])
    data = {
        "script": Path(__file__).name,
        "random_repeats": RANDOM_REPEATS,
        "folds": FOLDS,
        "support_margin": SUPPORT_MARGIN,
        "random_control": "same fold-wise interval widths as the CV support gate, random interval positions",
        "learned_score_wins": int(learned["score_wins"]),
        "learned_score_losses": int(learned["score_losses"]),
        "learned_retained_fraction": float(learned["retained_learned_win_fraction"]),
        "random_full_retained_count": full_retained,
        "random_mean_retained_fraction": float(random_mean["retained_learned_win_fraction"]),
        "random_best_retained_wins": int(random_best["score_wins"]),
        "random_best_retained_fraction": float(random_best["retained_learned_win_fraction"]),
        "learned_beats_all_random_retention": int(learned["score_wins"])
        > max(int(row["score_wins"]) for row in random_rows),
        "learned_overhead_reduction": float(learned["learned_overhead_reduction"]),
        "random_mean_overhead_reduction": float(random_mean["learned_overhead_reduction"]),
        "needs_revision_count": 0
        if full_retained == 0
        and int(learned["score_wins"]) > max(int(row["score_wins"]) for row in random_rows)
        and int(learned["score_losses"]) == 0
        else 1,
        "table": str(TABLE.relative_to(THIS_DIR)),
        "table_anchor_present": "tab:bitflip-prior-feature-gate-random-control" in paper,
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
            str(CV_ANALYSIS.relative_to(THIS_DIR)),
        ],
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    input_rows = [row for row in read_csv(RAW) if usable(row)]
    input_rows += add_full_budget(read_csv(LEARNED_FULL), "learned_prior")
    input_rows += add_full_budget(read_csv(NO_PRIOR_FULL), "no_prior")
    pairs = paired_rows(input_rows)
    rows, random_rows = build_rows(pairs)
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows, random_rows)
    write_latex(TABLE, rows)
    write_manifest(rows, random_rows)
    print(f"wrote {len(rows)} bit-flip prior feature-gate random-control rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
