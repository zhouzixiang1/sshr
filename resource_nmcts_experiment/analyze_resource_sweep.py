#!/usr/bin/env python3
"""Analyze resource-weight sweep output."""
from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"

PROFILE_ORDER = ["t_heavy", "balanced", "cnot_depth", "ancilla_tight"]
PROFILE_LABELS = {
    "t_heavy": "T-heavy",
    "balanced": "Balanced",
    "cnot_depth": "CNOT-depth",
    "ancilla_tight": "Ancilla-tight",
}
METHOD_ORDER = ["and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_cube_beam", "sshr_h"]
METHOD_LABELS = {
    "and_direct_anf": "AND-direct ANF",
    "and_mcts_factor": "Fixed MCTS",
    "and_affine_nmcts": "Affine-NMCTS",
    "and_cube_beam": "ESOP cube beam",
    "sshr_h": "SSHR-H",
}


def fnum(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "--"
    return f"{value:.{digits}f}"


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def tex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("%", r"\%")


def method_sort(method: str) -> tuple[int, str]:
    return (METHOD_ORDER.index(method) if method in METHOD_ORDER else len(METHOD_ORDER), method)


def profile_sort(profile: str) -> tuple[int, str]:
    return (PROFILE_ORDER.index(profile) if profile in PROFILE_ORDER else len(PROFILE_ORDER), profile)


def summarize(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not row.get("error") and not row.get("skipped"):
            groups[(row["profile"], row["method"])].append(row)
    summaries = []
    for (profile, method), items in sorted(groups.items(), key=lambda x: (profile_sort(x[0][0]), method_sort(x[0][1]))):
        out: dict[str, object] = {
            "profile": profile,
            "profile_label": PROFILE_LABELS.get(profile, profile),
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "completed": len(items),
        }
        for key in ["T", "CNOT", "depth", "peak_ancilla", "score", "time_s"]:
            vals = [v for row in items if (v := fnum(row.get(key))) is not None]
            out[f"mean_{key}"] = mean(vals) if vals else float("nan")
        summaries.append(out)
    return summaries


def by_profile_name(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    out: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out[row["profile"]][row["name"]][row["method"]] = row
    return out


def comparison(
    grouped: dict[str, dict[str, dict[str, dict[str, str]]]],
    profile: str,
    target: str,
    base: str,
    metric: str,
) -> tuple[int, int, int, float]:
    vals: list[float] = []
    wins = losses = ties = 0
    for table in grouped.get(profile, {}).values():
        if target not in table or base not in table:
            continue
        new = float(table[target][metric])
        old = float(table[base][metric])
        vals.append(pct(new, old))
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties, mean(vals) if vals else float("nan")


def winner_counts(grouped: dict[str, dict[str, dict[str, dict[str, str]]]]) -> dict[str, Counter[str]]:
    winners: dict[str, Counter[str]] = {}
    for profile, functions in grouped.items():
        counts: Counter[str] = Counter()
        for table in functions.values():
            best = min(table.values(), key=lambda row: (float(row["score"]), float(row["T"]), float(row["CNOT"])))
            counts[best["method"]] += 1
        winners[profile] = counts
    return winners


def write_latex_affine_table(summaries: list[dict[str, object]]) -> Path:
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    out = PAPER_TABLES / "resource_sweep_affine.tex"
    rows = [s for s in summaries if s["method"] == "and_affine_nmcts"]
    rows.sort(key=lambda s: profile_sort(str(s["profile"])))
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Profile & Mean T & Mean CNOT & Mean depth & Mean ancilla & Mean score \\",
        r"\midrule",
    ]
    for s in rows:
        lines.append(
            "{profile} & {mean_T} & {mean_CNOT} & {mean_depth} & {mean_peak_ancilla} & {mean_score} \\\\".format(
                profile=tex_escape(str(s["profile_label"])),
                mean_T=fmt(float(s["mean_T"]), 1),
                mean_CNOT=fmt(float(s["mean_CNOT"]), 1),
                mean_depth=fmt(float(s["mean_depth"]), 1),
                mean_peak_ancilla=fmt(float(s["mean_peak_ancilla"]), 2),
                mean_score=fmt(float(s["mean_score"]), 1),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_latex_winner_table(winners: dict[str, Counter[str]]) -> Path:
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    out = PAPER_TABLES / "resource_sweep_winners.tex"
    columns = ["and_affine_nmcts", "and_mcts_factor", "sshr_h", "and_direct_anf", "and_cube_beam"]
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Profile & Affine & Fixed MCTS & SSHR-H & AND-direct & ESOP beam \\",
        r"\midrule",
    ]
    for profile in sorted(winners, key=profile_sort):
        counts = winners[profile]
        lines.append(
            "{profile} & {values} \\\\".format(
                profile=tex_escape(PROFILE_LABELS.get(profile, profile)),
                values=" & ".join(str(counts.get(method, 0)) for method in columns),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    raw = RESULTS / "raw_resource_sweep.csv"
    rows = list(csv.DictReader(raw.open(encoding="utf-8")))
    usable = [row for row in rows if not row.get("error") and not row.get("skipped")]
    summaries = summarize(rows)
    grouped = by_profile_name(rows)
    winners = winner_counts(grouped)

    lines = [
        "# Resource Sweep Analysis",
        "",
        f"Rows: {len(rows)}; usable: {len(usable)}; errors: {sum(1 for r in rows if r.get('error'))}; skipped: {sum(1 for r in rows if r.get('skipped'))}.",
        "",
        "## Mean resources by profile and method",
        "",
        "| profile | method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            "| {profile} | {method} | {completed} | {mean_T} | {mean_CNOT} | {mean_depth} | {mean_peak_ancilla} | {mean_score} | {mean_time_s} |".format(
                profile=s["profile_label"],
                method=s["method_label"],
                completed=s["completed"],
                mean_T=fmt(float(s["mean_T"]), 2),
                mean_CNOT=fmt(float(s["mean_CNOT"]), 2),
                mean_depth=fmt(float(s["mean_depth"]), 2),
                mean_peak_ancilla=fmt(float(s["mean_peak_ancilla"]), 2),
                mean_score=fmt(float(s["mean_score"]), 2),
                mean_time_s=fmt(float(s["mean_time_s"]), 3),
            )
        )

    lines.extend(
        [
            "",
            "## Objective winners by profile",
            "",
            "| profile | winner method | functions |",
            "|---|---|---:|",
        ]
    )
    for profile in sorted(winners, key=profile_sort):
        for method, count in winners[profile].most_common():
            lines.append(f"| {PROFILE_LABELS.get(profile, profile)} | {METHOD_LABELS.get(method, method)} | {count} |")

    lines.extend(
        [
            "",
            "## Focused Affine-NMCTS comparisons",
            "",
            "| profile | baseline | metric | wins | losses | ties | mean relative |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for profile in sorted(grouped, key=profile_sort):
        for base in ["and_mcts_factor", "and_cube_beam", "sshr_h"]:
            for metric in ["score", "T", "CNOT", "depth", "peak_ancilla"]:
                wins, losses, ties, rel = comparison(grouped, profile, "and_affine_nmcts", base, metric)
                lines.append(
                    f"| {PROFILE_LABELS.get(profile, profile)} | {METHOD_LABELS.get(base, base)} | {metric} | {wins} | {losses} | {ties} | {rel:+.2f}% |"
                )

    affine_tex = write_latex_affine_table(summaries)
    winners_tex = write_latex_winner_table(winners)
    out = RESULTS / "analysis_resource_sweep.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"wrote {affine_tex}")
    print(f"wrote {winners_tex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
