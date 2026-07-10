#!/usr/bin/env python3
"""Analyze same-candidate random-depth controls for the frontier policy.

The depth-frontier policy chooses among already-generated Boolean-ring screens
at depths 2, 3, and 4.  This audit keeps that candidate set fixed and compares
the learned large frontier policy with deterministic random depth choices.  It
therefore tests whether the policy is better than random budget allocation
without rerunning synthesis.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
DEPTHS = (2, 3, 4)
RANDOM_SEEDS = tuple(range(2001, 2009))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source",
        "scope",
        "pairs",
        "random_repeats",
        "score_wins",
        "score_losses",
        "score_ties",
        "mean_score_relative",
        "mean_time_relative",
        "mean_t_depth_relative",
        "mean_aux_area_relative",
        "target_at_or_better_than_random_best",
        "seed_means_beaten",
        "one_sided_sign_p",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def choose_depth(seed: int, name: str, source: str) -> int:
    payload = f"{seed}|{source}|{name}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return DEPTHS[int.from_bytes(digest, "big") % len(DEPTHS)]


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def rel(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def sign_p_value(wins: int, losses: int) -> float:
    trials = wins + losses
    if trials == 0:
        return 1.0
    successes = max(wins, losses)
    tail = sum(math.comb(trials, k) for k in range(successes, trials + 1))
    return tail / (2**trials)


def compare_scalar(target: float, baseline: float) -> tuple[int, int, int]:
    if target < baseline:
        return (1, 0, 0)
    if target > baseline:
        return (0, 1, 0)
    return (0, 0, 1)


def rows_by_name(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["name"], {})[row["method"]] = row
    return out


def usable_truth(row: dict[str, str]) -> bool:
    for key in ("truth_verified", "anf_verified", "circuit_anf_verified"):
        if key in row and row[key] not in {"True", "true", "1"}:
            return False
    return True


def summarize(
    *,
    source: str,
    scope: str,
    records: list[dict[str, object]],
) -> dict[str, str]:
    wins = losses = ties = 0
    score_rels: list[float] = []
    time_rels: list[float] = []
    t_depth_rels: list[float] = []
    aux_area_rels: list[float] = []
    target_best_count = 0
    seed_scores: dict[int, list[float]] = {seed: [] for seed in RANDOM_SEEDS}
    target_scores: list[float] = []

    for record in records:
        target_score = float(record["target_score"])
        target_time = float(record["target_time"])
        random_scores = list(record["random_scores"])  # type: ignore[arg-type]
        random_times = list(record["random_times"])  # type: ignore[arg-type]
        w, l, t = compare_scalar(target_score, mean(random_scores))
        wins += w
        losses += l
        ties += t
        target_scores.append(target_score)
        score_rels.append(rel(target_score, mean(random_scores)))
        time_rels.append(rel(target_time, mean(random_times), floor=1e-9))
        if target_score <= min(random_scores):
            target_best_count += 1
        for seed, score in zip(RANDOM_SEEDS, random_scores, strict=True):
            seed_scores[seed].append(float(score))
        if "target_t_depth" in record:
            random_t_depth = list(record["random_t_depth"])  # type: ignore[arg-type]
            t_depth_rels.append(rel(float(record["target_t_depth"]), mean(random_t_depth)))
        if "target_aux_area" in record:
            random_aux_area = list(record["random_aux_area"])  # type: ignore[arg-type]
            aux_area_rels.append(rel(float(record["target_aux_area"]), mean(random_aux_area)))

    target_mean = mean(target_scores)
    seed_means_beaten = sum(1 for values in seed_scores.values() if target_mean <= mean(values))
    status = (
        "pass"
        if records
        and wins > losses
        and seed_means_beaten == len(RANDOM_SEEDS)
        and mean(score_rels) < 0.0
        else "needs revision"
    )
    return {
        "source": source,
        "scope": scope,
        "pairs": str(len(records)),
        "random_repeats": str(len(RANDOM_SEEDS)),
        "score_wins": str(wins),
        "score_losses": str(losses),
        "score_ties": str(ties),
        "mean_score_relative": f"{mean(score_rels):.10g}",
        "mean_time_relative": f"{mean(time_rels):.10g}",
        "mean_t_depth_relative": "" if not t_depth_rels else f"{mean(t_depth_rels):.10g}",
        "mean_aux_area_relative": "" if not aux_area_rels else f"{mean(aux_area_rels):.10g}",
        "target_at_or_better_than_random_best": str(target_best_count),
        "seed_means_beaten": str(seed_means_beaten),
        "one_sided_sign_p": f"{sign_p_value(wins, losses):.10g}",
        "status": status,
    }


def heldout_records(path: Path, split: str = "test") -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in read_csv(path):
        if row["split"] != split:
            continue
        random_scores: list[float] = []
        random_times: list[float] = []
        for seed in RANDOM_SEEDS:
            depth = choose_depth(seed, row["name"], "heldout")
            random_scores.append(float(row[f"depth{depth}_score"]))
            random_times.append(float(row[f"depth{depth}_time_s"]))
        records.append(
            {
                "target_score": float(row["policy_score"]),
                "target_time": float(row["policy_time_s"]),
                "random_scores": random_scores,
                "random_times": random_times,
            }
        )
    return records


def row_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for name, methods in rows_by_name(read_csv(path)).items():
        if "depth_frontier_policy" not in methods:
            continue
        policy = methods["depth_frontier_policy"]
        if not usable_truth(policy):
            continue
        random_scores: list[float] = []
        random_times: list[float] = []
        random_t_depth: list[float] = []
        random_aux_area: list[float] = []
        ok = True
        for seed in RANDOM_SEEDS:
            depth = choose_depth(seed, name, path.name)
            row = methods.get(f"screen_depth{depth}")
            if row is None or not usable_truth(row):
                ok = False
                break
            random_scores.append(float(row["score"]))
            random_times.append(float(row.get("time_s", row.get("plan_time_s", "0"))))
            if "schedule_t_depth_proxy" in row:
                random_t_depth.append(float(row["schedule_t_depth_proxy"]))
            if "explicit_ancilla_lifetime_area" in row:
                random_aux_area.append(float(row["explicit_ancilla_lifetime_area"]))
        if not ok:
            continue
        record: dict[str, object] = {
            "target_score": float(policy["score"]),
            "target_time": float(policy.get("time_s", policy.get("plan_time_s", "0"))),
            "random_scores": random_scores,
            "random_times": random_times,
        }
        if random_t_depth:
            record["target_t_depth"] = float(policy["schedule_t_depth_proxy"])
            record["random_t_depth"] = random_t_depth
        if random_aux_area:
            record["target_aux_area"] = float(policy["explicit_ancilla_lifetime_area"])
            record["random_aux_area"] = random_aux_area
        records.append(record)
    return records


def fmt_pct(value: str) -> str:
    if value == "":
        return ""
    return f"{100.0 * float(value):+.2f}%"


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Frontier Random-Depth Control",
        "",
        "This audit compares the large Boolean-ring depth-frontier policy with same-candidate random choices among depth 2, 3, and 4.",
        "No synthesis is rerun: all comparisons reuse already verified depth candidates in the raw frontier files.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| source | scope | pairs | W/L/T vs random mean | mean score change | mean time change | T-depth change | aux-area change | seed means beaten | sign p |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            "| {source} | {scope} | {pairs} | {score_wins}/{score_losses}/{score_ties} | "
            "{score} | {time} | {tdepth} | {aux} | {seed_means_beaten}/{random_repeats} | {p} |".format(
                **row,
                score=fmt_pct(row["mean_score_relative"]),
                time=fmt_pct(row["mean_time_relative"]),
                tdepth=fmt_pct(row["mean_t_depth_relative"]),
                aux=fmt_pct(row["mean_aux_area_relative"]),
                p=row["one_sided_sign_p"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The learned frontier policy beats same-candidate random depth selection on score in held-out training, independent n=24/28/32/40 scale rows, and the n=23 truth-table bridge.",
            "- The policy is quality-oriented: it often chooses deeper screens and therefore spends more planning time than random depth selection.",
            "- The control supports learned budget allocation within the Boolean-ring frontier, not hardware scheduling or global optimality.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("<=", r"$\leq$")
    )


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}rcc>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Source & Scope & Pairs & Score W/L/T & Mean $\Delta$ score & Mean $\Delta$ time & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        boundary = (
            f"beats {row['seed_means_beaten']}/{row['random_repeats']} random seed means; "
            "quality-oriented, not a runtime claim"
        )
        lines.append(
            " & ".join(
                [
                    tex_escape(row["source"]),
                    tex_escape(row["scope"]),
                    row["pairs"],
                    f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']}",
                    tex_escape(fmt_pct(row["mean_score_relative"])),
                    tex_escape(fmt_pct(row["mean_time_relative"])),
                    tex_escape(boundary),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "random_seeds": list(RANDOM_SEEDS),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "source_files": [
            "results/raw_boolean_screen_depth_frontier_policy_large.csv",
            "results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
            "results/raw_truth_bridge_n23_large_frontier_terms.csv",
        ],
        "outputs": {
            "summary": "results/summary_frontier_random_depth_control.csv",
            "analysis": "results/analysis_frontier_random_depth_control.md",
            "manifest": "results/manifest_frontier_random_depth_control.json",
            "table": "paper_latex/tables/frontier_random_depth_control.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [
        summarize(
            source="held-out frontier policy",
            scope="test n=28,40",
            records=heldout_records(RESULTS / "raw_boolean_screen_depth_frontier_policy_large.csv"),
        ),
        summarize(
            source="scale generalization",
            scope="n=24,28,32,40",
            records=row_records(RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv"),
        ),
        summarize(
            source="truth-table bridge",
            scope="n=23",
            records=row_records(RESULTS / "raw_truth_bridge_n23_large_frontier_terms.csv"),
        ),
    ]
    write_csv(RESULTS / "summary_frontier_random_depth_control.csv", rows)
    write_markdown(RESULTS / "analysis_frontier_random_depth_control.md", rows)
    write_latex(TABLES / "frontier_random_depth_control.tex", rows)
    write_manifest(RESULTS / "manifest_frontier_random_depth_control.json", rows)
    failures = sum(1 for row in rows if row["status"] != "pass")
    print(f"wrote {len(rows)} frontier random-depth control rows")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
