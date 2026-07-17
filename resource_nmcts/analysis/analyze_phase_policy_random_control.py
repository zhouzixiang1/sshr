#!/usr/bin/env python3
"""Audit learned phase-policy shortlists against same-budget random repeats.

The training script already stores eight random shortlists for every top-k
budget.  This analysis treats the held-out n=6 function as the independent
unit: random repeats are averaged per function before computing the paired sign
test, while seed-level means are reported only as a robustness check.
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
RAW = RESULTS / "raw_phase_affine_policy_rank_diverse.csv"
METRIC = "score_synth_tperrz30"
SPLIT = "test_n6"
TOPKS = [64, 128, 256, 512]
RANDOM_REPEATS = 8
RANK_PREFIX = "phase_parity_affine_policy_tperrz30"
DIVERSE_PREFIX = "phase_parity_affine_policy_diverse_tperrz30"


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


def random_names(topk: int) -> list[str]:
    return [
        f"phase_affine_random_top{topk}" if repeat == 0 else f"phase_affine_random_s{repeat}_top{topk}"
        for repeat in range(RANDOM_REPEATS)
    ]


def binom_two_sided(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    p = 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, p)


def fmt_pct(value: float) -> str:
    return f"{value:+.3f}%"


def latex_pct(value: float) -> str:
    return f"{value:+.3f}\\%"


def fmt_p(value: float) -> str:
    if value < 1e-4:
        return f"{value:.2e}"
    return f"{value:.4f}"


def latex_p(value: float) -> str:
    if value < 1e-4:
        exponent = int(math.floor(math.log10(value)))
        mantissa = value / (10**exponent)
        return rf"${mantissa:.2f}\times10^{{{exponent}}}$"
    return f"{value:.4f}"


def build_rows() -> list[dict[str, object]]:
    raw = [row for row in read_rows(RAW) if usable(row)]
    by_method: dict[str, dict[str, dict[str, str]]] = {}
    for row in raw:
        by_method.setdefault(row["method"], {})[row["name"]] = row

    out: list[dict[str, object]] = []
    for topk in TOPKS:
        random_methods = random_names(topk)
        for label, prefix in [("rank", RANK_PREFIX), ("diverse", DIVERSE_PREFIX)]:
            method = f"{prefix}_top{topk}"
            target_rows = by_method.get(method, {})
            names = sorted(target_rows)
            pairs: list[tuple[float, float, float]] = []
            seed_means: list[float] = []
            for random_method in random_methods:
                method_rows = by_method.get(random_method, {})
                values = [float(method_rows[name][METRIC]) for name in names if name in method_rows]
                if len(values) == len(names):
                    seed_means.append(statistics.mean(values))

            for name in names:
                random_values = []
                for random_method in random_methods:
                    random_row = by_method.get(random_method, {}).get(name)
                    if random_row is None:
                        break
                    random_values.append(float(random_row[METRIC]))
                if len(random_values) != RANDOM_REPEATS:
                    continue
                target = float(target_rows[name][METRIC])
                random_mean = statistics.mean(random_values)
                random_best = min(random_values)
                pairs.append((target, random_mean, random_best))

            wins = losses = ties = 0
            deltas = []
            rels = []
            best_or_equal = 0
            for target, random_mean, random_best in pairs:
                if target < random_mean - 1e-9:
                    wins += 1
                elif target > random_mean + 1e-9:
                    losses += 1
                else:
                    ties += 1
                deltas.append(target - random_mean)
                rels.append((target - random_mean) / max(abs(random_mean), 1.0))
                if target <= random_best + 1e-9:
                    best_or_equal += 1

            target_mean = statistics.mean(target for target, _, _ in pairs)
            random_mean_over_functions = statistics.mean(random_mean for _, random_mean, _ in pairs)
            seed_wins = sum(1 for seed_mean in seed_means if target_mean < seed_mean)
            mean_delta = target_mean - random_mean_over_functions
            mean_relative = mean_delta / max(abs(random_mean_over_functions), 1.0)
            p_value = binom_two_sided(wins, losses)
            out.append(
                {
                    "policy": label,
                    "topk": topk,
                    "functions": len(pairs),
                    "random_repeats": RANDOM_REPEATS,
                    "wins": wins,
                    "losses": losses,
                    "ties": ties,
                    "sign_p": p_value,
                    "target_mean": target_mean,
                    "random_mean": random_mean_over_functions,
                    "mean_delta": mean_delta,
                    "mean_relative": mean_relative,
                    "mean_pair_delta": statistics.mean(deltas),
                    "median_pair_delta": statistics.median(deltas),
                    "mean_pair_relative": statistics.mean(rels),
                    "seed_means_beaten": seed_wins,
                    "random_seed_means": len(seed_means),
                    "target_at_or_better_than_random_best": best_or_equal,
                    "method": method,
                }
            )
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Phase Policy Random-Control Audit",
        "",
        "This audit compares learned Affine-FPRM phase shortlists with eight same-budget random shortlists.",
        "The independent unit is the held-out n=6 function; random repeats are averaged per function before the sign test.",
        "",
        "| policy | top-k | functions | W/L/T vs random mean | sign p | target mean | random mean | mean delta | seed means beaten | target <= best random |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {policy} | {topk} | {functions} | {wins}/{losses}/{ties} | {p} | {target:.2f} | {random:.2f} | {delta:.3f} ({rel}) | {seed}/{seeds} | {best}/{functions} |".format(
                policy=row["policy"],
                topk=row["topk"],
                functions=row["functions"],
                wins=row["wins"],
                losses=row["losses"],
                ties=row["ties"],
                p=fmt_p(float(row["sign_p"])),
                target=float(row["target_mean"]),
                random=float(row["random_mean"]),
                delta=float(row["mean_delta"]),
                rel=fmt_pct(100.0 * float(row["mean_relative"])),
                seed=row["seed_means_beaten"],
                seeds=row["random_seed_means"],
                best=row["target_at_or_better_than_random_best"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Diverse top-512 is the strongest random-control row: it is never worse than the per-function random mean on non-tie functions and beats all eight random seed means.",
            "- Random repeats are dense in this candidate space, so the margins are small in absolute score units; the claim is reliable pruning, not global phase/Rz optimality.",
            "- Rows compare only the logic-layer T/Rz=30 synthesis proxy and do not synthesize approximate rotation sequences.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Policy & Top-$k$ & W/L/T & Sign $p$ & Mean target & Mean random & $\Delta$ mean \\",
        r"\midrule",
    ]
    for row in rows:
        label = "Rank" if row["policy"] == "rank" else "Diverse"
        lines.append(
            "{} & {} & {}/{}/{} & {} & {:.2f} & {:.2f} & {} \\\\".format(
                label,
                row["topk"],
                row["wins"],
                row["losses"],
                row["ties"],
                latex_p(float(row["sign_p"])),
                float(row["target_mean"]),
                float(row["random_mean"]),
                latex_pct(100.0 * float(row["mean_relative"])),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(RESULTS / "summary_phase_policy_random_control.csv", rows)
    write_markdown(RESULTS / "analysis_phase_policy_random_control.md", rows)
    write_latex(TABLES / "phase_policy_random_control.tex", rows)
    print(f"wrote {RESULTS / 'summary_phase_policy_random_control.csv'}")
    print(f"wrote {RESULTS / 'analysis_phase_policy_random_control.md'}")
    print(f"wrote {TABLES / 'phase_policy_random_control.tex'}")


if __name__ == "__main__":
    main()
