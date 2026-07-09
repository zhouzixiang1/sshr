#!/usr/bin/env python3
"""Build a reviewer-facing audit of search-control baselines.

The full search-contribution table is intentionally broad.  This audit
compresses the same verified raw evidence into the specific question a reviewer
is likely to ask: what search strategies are compared, and what conclusion can
each comparison support?
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require_row(rows: list[dict[str, str]], **keys: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in keys.items()):
            return row
    raise KeyError(f"missing row {keys}")


def pct(value: str | float, digits: int = 2) -> str:
    return f"{float(value):+.{digits}f}%"


def pct_ratio(value: str | float, digits: int = 2) -> str:
    return f"{100.0 * float(value):+.{digits}f}%"


def pass_status(row: dict[str, str]) -> str:
    wlt = row["score_wlt"].split("/")
    wins, losses = int(wlt[0]), int(wlt[1])
    rel = float(row["score_relative_pct"])
    return "pass" if wins > 0 and losses <= wins and rel <= 0.0 else "needs revision"


def paired_variant_stats(
    rows: list[dict[str, str]],
    *,
    method: str,
    target_variant: str,
    baseline_variant: str,
    metric: str,
) -> dict[str, str]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("method") == method and str(row.get("correct", "True")) != "False" and not row.get("skipped"):
            by_name.setdefault(row["name"], {})[row["variant"]] = row
    wins = losses = ties = 0
    rels: list[float] = []
    target_values: list[float] = []
    baseline_values: list[float] = []
    for table in by_name.values():
        if target_variant not in table or baseline_variant not in table:
            continue
        target = float(table[target_variant][metric])
        baseline = float(table[baseline_variant][metric])
        target_values.append(target)
        baseline_values.append(baseline)
        rels.append((target - baseline) / max(baseline, 1e-9) * 100.0)
        if target < baseline:
            wins += 1
        elif target > baseline:
            losses += 1
        else:
            ties += 1
    return {
        "pairs": str(len(rels)),
        "wlt": f"{wins}/{losses}/{ties}",
        "mean_target": f"{sum(target_values) / len(target_values):.6g}" if target_values else "",
        "mean_baseline": f"{sum(baseline_values) / len(baseline_values):.6g}" if baseline_values else "",
        "mean_relative": f"{sum(rels) / len(rels):.6g}" if rels else "",
        "wins": str(wins),
        "losses": str(losses),
        "ties": str(ties),
    }


def build_rows() -> list[dict[str, str]]:
    search = read_csv(RESULTS / "summary_search_contribution.csv")
    prior_raw = read_csv(RESULTS / "raw_neural_prior_ablation.csv")
    bitflip_random = read_csv(RESULTS / "summary_bitflip_random_prior_control.csv")
    bitflip_budget = read_csv(RESULTS / "summary_bitflip_neural_budget_sweep.csv")
    frontier_random = read_csv(RESULTS / "summary_frontier_random_depth_control.csv")
    phase_budget = read_csv(RESULTS / "summary_phase_policy_budget_frontier.csv")
    phase_random = read_csv(RESULTS / "summary_phase_policy_random_control.csv")

    def search_row(
        *,
        comparison: str,
        layer: str,
        scope: str,
        conclusion: str,
        boundary: str,
    ) -> dict[str, str]:
        row = require_row(search, comparison=comparison)
        return {
            "layer": layer,
            "evidence_source": row["dataset"],
            "comparison": comparison,
            "scope": scope,
            "pairs": row["pairs"],
            "score_wlt": row["score_wlt"],
            "mean_score_change": pct(row["score_relative_pct"]),
            "cost_or_runtime": "not the claimed dimension",
            "supported_conclusion": conclusion,
            "boundary": boundary,
            "status": pass_status(row),
        }

    prior_score = paired_variant_stats(
        prior_raw,
        method="and_resource_nmcts",
        target_variant="learned_prior",
        baseline_variant="no_prior",
        metric="score",
    )
    prior_time = paired_variant_stats(
        prior_raw,
        method="and_resource_nmcts",
        target_variant="learned_prior",
        baseline_variant="no_prior",
        metric="time_s",
    )
    bitflip_random_score = require_row(bitflip_random, method="and_resource_nmcts", metric="score")
    bitflip_random_time = require_row(bitflip_random, method="and_resource_nmcts", metric="time_s")
    low_budget_score_rows = [
        row
        for row in bitflip_budget
        if row["budget"] in {"top8_s8_n12", "top12_s12_n16"} and row["metric"] == "score"
    ]
    low_budget_time_rows = [
        row
        for row in bitflip_budget
        if row["budget"] in {"top8_s8_n12", "top12_s12_n16"} and row["metric"] == "time_s"
    ]
    low_budget_pairs = sum(int(row["pairs"]) for row in low_budget_score_rows)
    low_budget_wins = sum(int(row["learned_wins"]) for row in low_budget_score_rows)
    low_budget_losses = sum(int(row["learned_losses"]) for row in low_budget_score_rows)
    low_budget_ties = sum(int(row["ties"]) for row in low_budget_score_rows)
    low_budget_mean_rel = sum(float(row["mean_relative"]) for row in low_budget_score_rows) / max(len(low_budget_score_rows), 1)
    low_budget_mean_time = sum(float(row["mean_relative"]) for row in low_budget_time_rows) / max(len(low_budget_time_rows), 1)
    frontier_random_scale = require_row(frontier_random, source="scale generalization")
    frontier_random_bridge = require_row(frontier_random, source="truth-table bridge")
    phase = require_row(phase_random, policy="diverse", topk="512")
    phase_frontier = require_row(phase_budget, policy="diverse", topk="512")

    rows = [
        search_row(
            comparison="Affine greedy vs fixed-coordinate MCTS",
            layer="search-space baseline",
            scope="321 matched affine pairs",
            conclusion="Changing the algebraic action space is a major source of score improvement.",
            boundary="This is not a neural-only effect.",
        ),
        search_row(
            comparison="No-MCTS portfolio over heuristic-only",
            layer="deterministic search controls",
            scope="177 n<=6 functions",
            conclusion="A deterministic portfolio improves over a single heuristic baseline.",
            boundary="This row does not isolate MCTS.",
        ),
        search_row(
            comparison="No-MCTS portfolio over beam-only",
            layer="deterministic search controls",
            scope="177 n<=6 functions",
            conclusion="The no-MCTS portfolio is stronger than the beam-only child in the same slice.",
            boundary="Beam is a child/search baseline, not the full method.",
        ),
        search_row(
            comparison="Resource-NMCTS over no-MCTS portfolio",
            layer="MCTS over deterministic portfolio",
            scope="177 n<=6 functions",
            conclusion="MCTS adds a small but non-degrading score gain over the strengthened no-MCTS portfolio.",
            boundary="The magnitude is incremental, not the whole resource drop.",
        ),
        search_row(
            comparison="Pareto Resource-NMCTS over no-MCTS portfolio",
            layer="Pareto search control",
            scope="177 n<=6 functions",
            conclusion="The Pareto archive makes the search-control gain clearer than base Resource-NMCTS alone.",
            boundary="Ancilla tradeoffs still need separate reporting.",
        ),
        {
            "layer": "learned prior",
            "evidence_source": "traditional_resource no-prior rerun",
            "comparison": "Learned prior for Resource-NMCTS",
            "scope": "177 n<=6 functions",
            "pairs": prior_score["pairs"],
            "score_wlt": prior_score["wlt"],
            "mean_score_change": pct(prior_score["mean_relative"]),
            "cost_or_runtime": f"time {pct(prior_time['mean_relative'])}",
            "supported_conclusion": "The learned scorer is a quality signal under the same functions and methods.",
            "boundary": "It is not a runtime claim and should not be promoted as the main source of improvement.",
            "status": "pass" if prior_score["losses"] == "0" and float(prior_score["mean_relative"]) < 0 else "needs revision",
        },
        {
            "layer": "bit-flip random control",
            "evidence_source": "bit-flip same-budget random-prior audit",
            "comparison": "Learned bit-flip prior vs same-budget random-prior mean",
            "scope": "177 n<=6 functions; eight random-prior repeats",
            "pairs": bitflip_random_score["pairs"],
            "score_wlt": f"{bitflip_random_score['learned_wins']}/{bitflip_random_score['learned_losses']}/{bitflip_random_score['ties']}",
            "mean_score_change": pct_ratio(bitflip_random_score["mean_relative"]),
            "cost_or_runtime": f"time {pct_ratio(bitflip_random_time['mean_relative'])}",
            "supported_conclusion": "The learned scorer beats deterministic random action priors as a bounded quality signal.",
            "boundary": "The margin is small and runtime-negative; this is not a claim that neural ranking explains the full gain.",
            "status": "pass"
            if int(bitflip_random_score["pairs"]) == 177
            and int(bitflip_random_score["random_repeats"]) >= 8
            and float(bitflip_random_score["mean_relative"]) < 0.0
            else "needs revision",
        },
        {
            "layer": "bit-flip low-budget control",
            "evidence_source": "bit-flip neural budget sweep",
            "comparison": "Learned prior vs no-prior under compressed candidate/MCTS budgets",
            "scope": "2 budgets x 3 methods x 177 n<=6 functions",
            "pairs": str(low_budget_pairs),
            "score_wlt": f"{low_budget_wins}/{low_budget_losses}/{low_budget_ties}",
            "mean_score_change": pct_ratio(low_budget_mean_rel),
            "cost_or_runtime": f"time {pct_ratio(low_budget_mean_time)}",
            "supported_conclusion": "The learned prior remains a positive quality signal when candidate and MCTS budgets are tightened.",
            "boundary": "The same rows still show runtime overhead, so this is budget-allocation quality evidence rather than a speedup claim.",
            "status": "pass"
            if len(low_budget_score_rows) == 6
            and low_budget_pairs == 6 * 177
            and low_budget_losses == 0
            and low_budget_wins > 0
            and low_budget_mean_rel < 0.0
            else "needs revision",
        },
        {
            "layer": "frontier random-depth control",
            "evidence_source": "frontier same-candidate random-depth audit",
            "comparison": "Large frontier policy vs same-candidate random depth",
            "scope": f"{frontier_random_scale['pairs']} n=24,28,32,40 scale rows; {frontier_random_bridge['pairs']} n=23 truth-bridge rows; eight random-depth repeats",
            "pairs": str(int(frontier_random_scale["pairs"]) + int(frontier_random_bridge["pairs"])),
            "score_wlt": f"{frontier_random_scale['score_wins']}/{frontier_random_scale['score_losses']}/{frontier_random_scale['score_ties']}; {frontier_random_bridge['score_wins']}/{frontier_random_bridge['score_losses']}/{frontier_random_bridge['score_ties']}",
            "mean_score_change": pct_ratio(frontier_random_scale["mean_score_relative"]),
            "cost_or_runtime": f"time {pct_ratio(frontier_random_scale['mean_time_relative'])}",
            "supported_conclusion": "The large frontier policy allocates depth budget better than random selection among the same verified candidates on scale and bridge slices.",
            "boundary": "The control is quality-positive but runtime-negative against random depth; it is not a speed, hardware-scheduling, or global-optimality claim.",
            "status": "pass"
            if int(frontier_random_scale["pairs"]) >= 96
            and int(frontier_random_scale["random_repeats"]) >= 8
            and int(frontier_random_scale["score_wins"]) > int(frontier_random_scale["score_losses"])
            and int(frontier_random_scale["seed_means_beaten"]) == int(frontier_random_scale["random_repeats"])
            and int(frontier_random_bridge["seed_means_beaten"]) == int(frontier_random_bridge["random_repeats"])
            and float(frontier_random_scale["mean_score_relative"]) < 0.0
            and float(frontier_random_bridge["mean_score_relative"]) < 0.0
            else "needs revision",
        },
        search_row(
            comparison="Highdim no-MCTS portfolio over root beam",
            layer="high-dimensional deterministic control",
            scope="16 n=14 ANF instances",
            conclusion="High-dimensional gains also need strong deterministic guards, not only MCTS.",
            boundary="This is symbolic/high-dimensional evidence, not exhaustive truth-table optimality.",
        ),
        {
            "layer": "phase budget frontier",
            "evidence_source": "phase policy budget-frontier audit",
            "comparison": "Diverse phase shortlist top-512 vs budget-32 and wide-128",
            "scope": "38 held-out n=6 phase functions",
            "pairs": phase_frontier["functions"],
            "score_wlt": f"{phase_frontier['vs_budget32_wins']}/{phase_frontier['vs_budget32_losses']}/{phase_frontier['vs_budget32_ties']}; {phase_frontier['vs_wide128_wins']}/{phase_frontier['vs_wide128_losses']}/{phase_frontier['vs_wide128_ties']}",
            "mean_score_change": f"{pct_ratio(phase_frontier['vs_budget32_mean_relative'], digits=3)} vs budget-32; {pct_ratio(phase_frontier['vs_wide128_mean_relative'], digits=3)} vs wide-128",
            "cost_or_runtime": f"{phase_frontier['target_exact_forms']}/{phase_frontier['wide128_exact_forms']} exact forms; {float(phase_frontier['eval_reduction_vs_wide128_pct']):.2f}% fewer vs wide-128",
            "supported_conclusion": "The learned/diverse shortlist preserves the wide-search phase proxy while exact-scoring far fewer candidates.",
            "boundary": "This is a logical phase/Rz budget-efficiency result, not a final rotation-synthesis or hardware-mapped claim.",
            "status": "pass"
            if phase_frontier["vs_budget32_losses"] == "0"
            and float(phase_frontier["vs_budget32_mean_relative"]) < 0.0
            and float(phase_frontier["vs_wide128_mean_relative"]) <= 0.001
            else "needs revision",
        },
        {
            "layer": "phase random control",
            "evidence_source": "phase affine policy random-control audit",
            "comparison": "Diverse phase shortlist top-512 vs same-budget random mean",
            "scope": "38 held-out n=6 phase functions; eight random repeats",
            "pairs": phase["functions"],
            "score_wlt": f"{phase['wins']}/{phase['losses']}/{phase['ties']}",
            "mean_score_change": pct(100.0 * float(phase["mean_relative"]), digits=3),
            "cost_or_runtime": "512/8192 exact forms",
            "supported_conclusion": "The phase shortlist is better than same-budget random controls on this proxy.",
            "boundary": "This is a phase/Rz proxy control, not a bit-flip random baseline or rotation synthesis.",
            "status": "pass" if phase["losses"] == "0" and phase["seed_means_beaten"] == phase["random_seed_means"] else "needs revision",
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "layer",
        "evidence_source",
        "comparison",
        "scope",
        "pairs",
        "score_wlt",
        "mean_score_change",
        "cost_or_runtime",
        "supported_conclusion",
        "boundary",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Search-Control Baseline Audit",
        "",
        "This audit answers the reviewer-facing question: which search/control baselines are compared, and what does each comparison mean?",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| layer | comparison | scope | score W/L/T | mean score change | supported conclusion | boundary | status |",
            "|---|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["layer"],
                    row["comparison"],
                    row["scope"],
                    row["score_wlt"],
                    row["mean_score_change"],
                    row["supported_conclusion"],
                    row["boundary"],
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
            "- The bit-flip branch compares against heuristic-only, beam-only, no-MCTS, MCTS, Pareto, learned-prior/no-prior, and same-budget random-prior controls.",
            "- Random controls now cover the bit-flip action-prior scorer, the high-dimensional frontier depth allocator, and the phase/Rz shortlist branch; the phase budget-frontier row separately quantifies exact-scoring savings relative to budget-32 and wide-128 searches.",
            "- The evidence supports resource-aware search control, not a claim that reinforcement learning alone causes the full improvement.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
    for token in ["n<=6", "n=24,28,32,40", "n=23", "n=14", "n=6"]:
        escaped = escaped.replace(token, f"${token}$")
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedleft\arraybackslash}p{0.045\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Layer & Comparison & Pairs & Score W/L/T & Mean $\Delta$ score & Claim boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["layer"]),
                    tex_escape(row["comparison"]),
                    row["pairs"],
                    row["score_wlt"],
                    row["mean_score_change"].replace("%", r"\%"),
                    tex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "sources": [
            "results/summary_search_contribution.csv",
            "results/raw_neural_prior_ablation.csv",
            "results/summary_bitflip_random_prior_control.csv",
            "results/summary_frontier_random_depth_control.csv",
            "results/summary_phase_policy_budget_frontier.csv",
            "results/summary_phase_policy_random_control.csv",
        ],
        "outputs": {
            "summary": "results/summary_search_control_baseline_audit.csv",
            "analysis": "results/analysis_search_control_baseline_audit.md",
            "manifest": "results/manifest_search_control_baseline_audit.json",
            "table": "paper_latex/tables/search_control_baseline_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_search_control_baseline_audit.csv", rows)
    write_markdown(RESULTS / "analysis_search_control_baseline_audit.md", rows)
    write_latex(TABLES / "search_control_baseline_audit.tex", rows)
    write_manifest(RESULTS / "manifest_search_control_baseline_audit.json", rows)
    print(f"wrote {len(rows)} search-control baseline audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
