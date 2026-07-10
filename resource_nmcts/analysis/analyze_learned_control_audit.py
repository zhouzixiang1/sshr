#!/usr/bin/env python3
"""Assemble an evidence audit for learned search-control components."""
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


def pct(value: str | float) -> str:
    return f"{100.0 * float(value):+.2f}%"


def pct_plain(value: str | float) -> str:
    return f"{float(value):+.2f}%"


def pct_ratio(value: str | float) -> str:
    return f"{100.0 * float(value):+.2f}%"


def wlt(row: dict[str, str], *, prefix: str = "") -> str:
    if prefix:
        return f"{row[prefix + 'wins']}/{row[prefix + 'losses']}/{row[prefix + 'ties']}"
    return f"{row['wins']}/{row['losses']}/{row['ties']}"


def status_from(condition: bool) -> str:
    return "pass" if condition else "needs revision"


def build_rows() -> list[dict[str, str]]:
    frontier = read_csv(RESULTS / "summary_boolean_screen_depth_frontier_policy_large.csv")
    frontier_oracle = require_row(
        frontier,
        comparison="frontier_policy_vs_oracle_depth-2_3_4_frontier",
    )
    frontier_random = read_csv(RESULTS / "summary_frontier_random_depth_control.csv")
    frontier_random_scale = require_row(frontier_random, source="scale generalization")
    frontier_random_bridge = require_row(frontier_random, source="truth-table bridge")

    staged = read_csv(RESULTS / "summary_stage_gated_frontier.csv")
    staged_scale = require_row(
        staged,
        source="scale_generalization",
        method="stage_gated_frontier",
        baseline="adaptive_all_depth",
    )

    sparse_gate = read_csv(RESULTS / "summary_sparse_depth4_gate_generalization.csv")
    sparse_gate_all = require_row(sparse_gate, scope="all")

    phase = read_csv(RESULTS / "summary_phase_affine_policy_rank_diverse.csv")
    phase_budget = require_row(
        phase,
        split="test_n6",
        target="phase_parity_affine_policy_diverse_tperrz30_top512",
        baseline="phase_affine_budget32_tperrz30",
        metric="score_synth_tperrz30",
    )
    phase_wide = require_row(
        phase,
        split="test_n6",
        target="phase_parity_affine_policy_diverse_tperrz30_top512",
        baseline="phase_affine_wide128_tperrz30",
        metric="score_synth_tperrz30",
    )
    phase_frontier = require_row(
        read_csv(RESULTS / "summary_phase_policy_budget_frontier.csv"),
        policy="diverse",
        topk="512",
    )

    mcts_budget_policy = require_row(
        read_csv(RESULTS / "summary_mcts_budget_policy.csv"),
        threshold="0.6",
    )
    mcts_budget_manifest = json.loads(
        (RESULTS / "manifest_mcts_budget_policy.json").read_text(encoding="utf-8")
    )

    boolean_guard = read_csv(RESULTS / "summary_boolean_neural_guard_vs_deterministic.csv")
    boolean_score = require_row(boolean_guard, metric="score")
    boolean_time = require_row(boolean_guard, metric="time_s")

    bitflip_random = read_csv(RESULTS / "summary_bitflip_random_prior_control.csv")
    bitflip_score = require_row(bitflip_random, method="and_resource_nmcts", metric="score")
    bitflip_time = require_row(bitflip_random, method="and_resource_nmcts", metric="time_s")
    bitflip_budget = read_csv(RESULTS / "summary_bitflip_neural_budget_sweep.csv")
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
    bitflip_gate = require_row(
        read_csv(RESULTS / "summary_bitflip_prior_feature_gate.csv"),
        row_type="all_aggregate",
        budget="all",
        method="all_methods",
    )
    bitflip_gate_cv = require_row(
        read_csv(RESULTS / "summary_bitflip_prior_feature_gate_cv.csv"),
        row_type="aggregate",
        fold="all",
    )
    bitflip_gate_cv_random_rows = read_csv(
        RESULTS / "summary_bitflip_prior_feature_gate_cv_random_control.csv"
    )
    bitflip_gate_cv_random = require_row(
        bitflip_gate_cv_random_rows,
        row_type="learned_cv_gate",
    )
    bitflip_gate_cv_random_mean = require_row(
        bitflip_gate_cv_random_rows,
        row_type="random_mean",
    )
    bitflip_gate_cv_random_best = require_row(
        bitflip_gate_cv_random_rows,
        row_type="random_best_retention",
    )

    root_ranker = read_csv(RESULTS / "summary_root_action_ranker_audit.csv")
    root_union = require_row(root_ranker, component="Combined heuristic top-4 plus neural top-12 extension")

    return [
        {
            "component": "Depth-frontier policy",
            "claim_class": "promoted",
            "scope": "held-out n=28,40; 48 rows",
            "quality": f"vs oracle frontier {frontier_oracle['score_wins']}/{frontier_oracle['score_losses']}/{frontier_oracle['score_ties']}, {pct(frontier_oracle['mean_rel_score'])}",
            "cost": f"{pct(frontier_oracle['mean_rel_time'])} time vs all-depth frontier",
            "role": "promoted quality/time selector",
            "status": status_from(
                int(frontier_oracle["score_losses"]) <= 3
                and abs(float(frontier_oracle["mean_rel_score"])) <= 0.001
                and float(frontier_oracle["mean_rel_time"]) < 0.0
            ),
        },
        {
            "component": "Frontier random-depth control",
            "claim_class": "bounded",
            "scope": "held-out/scale/n=23; 8 random-depth repeats",
            "quality": (
                f"scale {frontier_random_scale['score_wins']}/{frontier_random_scale['score_losses']}/{frontier_random_scale['score_ties']}, "
                f"{pct_ratio(frontier_random_scale['mean_score_relative'])}; "
                f"n23 {frontier_random_bridge['score_wins']}/{frontier_random_bridge['score_losses']}/{frontier_random_bridge['score_ties']}, "
                f"{pct_ratio(frontier_random_bridge['mean_score_relative'])}; "
                f"seed means beaten {frontier_random_scale['seed_means_beaten']}/{frontier_random_scale['random_repeats']}"
            ),
            "cost": f"{pct_ratio(frontier_random_scale['mean_time_relative'])} scale planning time vs random-depth mean",
            "role": "quality-oriented budget allocation; not runtime claim",
            "status": status_from(
                int(frontier_random_scale["score_wins"]) > int(frontier_random_scale["score_losses"])
                and int(frontier_random_scale["seed_means_beaten"]) == int(frontier_random_scale["random_repeats"])
                and int(frontier_random_bridge["seed_means_beaten"]) == int(frontier_random_bridge["random_repeats"])
                and float(frontier_random_scale["mean_score_relative"]) < 0.0
                and float(frontier_random_bridge["mean_score_relative"]) < 0.0
            ),
        },
        {
            "component": "Stage-gated frontier",
            "claim_class": "promoted",
            "scope": "independent n=24,28,32,40; 96 rows",
            "quality": f"vs all-depth {staged_scale['score_wins']}/{staged_scale['score_losses']}/{staged_scale['score_ties']}, {pct(staged_scale['mean_rel_score'])}",
            "cost": f"{pct(staged_scale['mean_rel_time'])} staged planning time",
            "role": "promoted validation-calibrated guard",
            "status": status_from(
                int(staged_scale["score_losses"]) <= 4
                and abs(float(staged_scale["mean_rel_score"])) <= 0.001
                and float(staged_scale["mean_rel_time"]) < 0.0
            ),
        },
        {
            "component": "Sparse depth-4 gate",
            "claim_class": "promoted",
            "scope": "multi-seed n=24,28,32,40; 144 pairs",
            "quality": f"vs sparse frontier {sparse_gate_all['score_wlt_vs_sparse']}, {pct(sparse_gate_all['mean_rel_score_vs_sparse'])}; false skips {sparse_gate_all['false_skips']}",
            "cost": f"{pct(sparse_gate_all['mean_rel_time_vs_sparse'])} time vs sparse frontier",
            "role": "promoted budget gate after depth-2",
            "status": status_from(
                sparse_gate_all["score_wlt_vs_sparse"] == "0/0/144"
                and int(sparse_gate_all["false_skips"]) == 0
                and float(sparse_gate_all["mean_rel_time_vs_sparse"]) < 0.0
            ),
        },
        {
            "component": "Rank-diverse phase shortlist",
            "claim_class": "promoted",
            "scope": "held-out n=6 phase search; 38 rows",
            "quality": f"vs budget-32 {wlt(phase_budget)}, {pct(phase_budget['mean_relative'])}; vs wide-128 {wlt(phase_wide)}, {pct(phase_wide['mean_relative'])}",
            "cost": f"{phase_frontier['target_exact_forms']}/{phase_frontier['wide128_exact_forms']} exact forms; {float(phase_frontier['eval_reduction_vs_wide128_pct']):.2f}% fewer vs wide-128",
            "role": "promoted phase-search pruning",
            "status": status_from(
                int(phase_budget["wins"]) > int(phase_budget["losses"])
                and int(phase_budget["losses"]) == 0
                and abs(float(phase_wide["mean_relative"])) <= 0.001
                and float(phase_frontier["eval_reduction_vs_wide128_pct"]) >= 90.0
            ),
        },
        {
            "component": "Contextual-bandit Pareto budget policy",
            "claim_class": "promoted",
            "scope": "disjoint seed-45 random-truth test; 160 functions",
            "quality": (
                f"vs Resource {mcts_budget_policy['vs_resource_wins']}/"
                f"{mcts_budget_policy['vs_resource_losses']}/"
                f"{mcts_budget_policy['vs_resource_ties']}, "
                f"{pct_ratio(mcts_budget_policy['mean_relative_vs_resource_score'])}; "
                f"retains {100.0 * float(mcts_budget_policy['quality_gain_retained']):.2f}% Pareto gain"
            ),
            "cost": (
                f"{pct_ratio(mcts_budget_policy['time_change_vs_pareto'])} conservative time; "
                f"Pareto invoked {mcts_budget_policy['run_pareto']}/{mcts_budget_policy['pairs']}"
            ),
            "role": "promoted reinforcement-learned search-budget controller",
            "status": status_from(
                int(mcts_budget_manifest.get("needs_revision_count", -1)) == 0
                and int(mcts_budget_policy["pairs"]) == 160
                and int(mcts_budget_policy["vs_resource_losses"]) == 0
                and float(mcts_budget_policy["mean_relative_vs_resource_score"]) < 0.0
                and float(mcts_budget_policy["time_change_ci_high"]) < 0.0
                and float(mcts_budget_policy["quality_retained_ci_low"]) >= 0.90
            ),
        },
        {
            "component": "Bit-flip learned prior",
            "claim_class": "limited",
            "scope": "177 n<=6 functions; 8 random-prior repeats",
            "quality": (
                f"vs random mean {bitflip_score['learned_wins']}/{bitflip_score['learned_losses']}/{bitflip_score['ties']}, "
                f"{pct_ratio(bitflip_score['mean_relative'])}; "
                f"seed means beaten {bitflip_score['seed_means_beaten']}/{bitflip_score['random_repeats']}"
            ),
            "cost": f"{pct_ratio(bitflip_time['mean_relative'])} runtime vs random-prior mean",
            "role": "limited quality signal, not runtime claim",
            "status": status_from(
                int(bitflip_score["random_repeats"]) >= 8
                and int(bitflip_score["seed_means_beaten"]) == int(bitflip_score["random_repeats"])
                and float(bitflip_score["mean_relative"]) < 0.0
            ),
        },
        {
            "component": "Bit-flip low-budget prior",
            "claim_class": "bounded",
            "scope": "top-8/top-12 budgets; 6 score rows; 1062 pairs",
            "quality": (
                f"learned vs no-prior {low_budget_wins}/{low_budget_losses}/{low_budget_ties}, "
                f"{pct_ratio(low_budget_mean_rel)}"
            ),
            "cost": f"{pct_ratio(low_budget_mean_time)} runtime vs no-prior",
            "role": "bounded low-budget quality evidence, not speed claim",
            "status": status_from(
                len(low_budget_score_rows) == 6
                and low_budget_pairs == 6 * 177
                and low_budget_losses == 0
                and low_budget_wins > 0
                and low_budget_mean_rel < 0.0
            ),
        },
        {
            "component": "Bit-flip ANF-term prior gate",
            "claim_class": "bounded",
            "scope": (
                f"{bitflip_gate['pairs']} paired rows; "
                "static 6--23 ANF-term deployment gate"
            ),
            "quality": (
                f"retains {bitflip_gate['score_wins']}/{bitflip_gate['learned_score_wins']} "
                f"always-learned score wins; {bitflip_gate['score_losses']} score losses; "
                f"{pct_ratio(bitflip_gate['mean_score_relative'])}"
            ),
            "cost": (
                f"{pct_ratio(bitflip_gate['mean_time_relative'])} runtime vs no-prior; "
                f"{pct_ratio(bitflip_gate['learned_overhead_reduction'])} overhead cut vs always-learned"
            ),
            "role": "bounded deployment rule from input ANF terms; not held-out policy claim",
            "status": status_from(
                int(bitflip_gate["pairs"]) >= 1500
                and bitflip_gate["retained_learned_wins"] == "True"
                and int(bitflip_gate["score_losses"]) == 0
                and float(bitflip_gate["mean_score_relative"]) < 0.0
                and float(bitflip_gate["learned_overhead_reduction"]) > 0.1
            ),
        },
        {
            "component": "Bit-flip CV ANF-term prior gate",
            "claim_class": "bounded",
            "scope": (
                f"{bitflip_gate_cv['test_pairs']} held-out paired rows; "
                "5-fold train-support plus margin gate"
            ),
            "quality": (
                f"retains {bitflip_gate_cv['score_wins']}/{bitflip_gate_cv['learned_score_wins']} "
                f"held-out learned score wins; {bitflip_gate_cv['score_losses']} score losses; "
                f"{pct_ratio(bitflip_gate_cv['mean_score_relative'])}"
            ),
            "cost": (
                f"{pct_ratio(bitflip_gate_cv['mean_time_relative'])} runtime vs no-prior; "
                f"{pct_ratio(bitflip_gate_cv['learned_overhead_reduction'])} overhead cut vs always-learned"
            ),
            "role": "held-out input-feature gate stability; not a new large-scale policy theorem",
            "status": status_from(
                int(bitflip_gate_cv["test_pairs"]) >= 1500
                and bitflip_gate_cv["retained_learned_wins"] == "True"
                and int(bitflip_gate_cv["score_losses"]) == 0
                and float(bitflip_gate_cv["mean_score_relative"]) < 0.0
                and float(bitflip_gate_cv["learned_overhead_reduction"]) > 0.05
            ),
        },
        {
            "component": "Bit-flip CV gate random-interval control",
            "claim_class": "bounded",
            "scope": (
                f"{bitflip_gate_cv_random_mean['random_repeats']} same-width "
                "random interval assignments"
            ),
            "quality": (
                f"CV gate retains {bitflip_gate_cv_random['score_wins']}/"
                f"{bitflip_gate_cv_random['learned_score_wins']} learned wins; "
                f"best random retains {bitflip_gate_cv_random_best['score_wins']}/"
                f"{bitflip_gate_cv_random_best['learned_score_wins']}; "
                f"random mean retains "
                f"{100.0 * float(bitflip_gate_cv_random_mean['retained_learned_win_fraction']):.2f}%"
            ),
            "cost": (
                f"CV overhead cut {pct_ratio(bitflip_gate_cv_random['learned_overhead_reduction'])}; "
                "random intervals may cut more runtime by skipping useful learned rows"
            ),
            "role": "bounded specificity control for the CV input-feature gate",
            "status": status_from(
                int(bitflip_gate_cv_random["random_repeats"]) == 1
                and int(bitflip_gate_cv_random_mean["random_repeats"]) >= 200
                and int(float(bitflip_gate_cv_random["score_wins"]))
                == int(float(bitflip_gate_cv_random["learned_score_wins"]))
                and int(float(bitflip_gate_cv_random["score_losses"])) == 0
                and int(float(bitflip_gate_cv_random_mean["full_retained_repeats"])) == 0
                and int(float(bitflip_gate_cv_random_best["score_wins"]))
                < int(float(bitflip_gate_cv_random["score_wins"]))
            ),
        },
        {
            "component": "Boolean neural guard",
            "claim_class": "limited",
            "scope": "n=16 high-dimensional guard; 24 rows",
            "quality": f"vs deterministic {wlt(boolean_score)}, {pct_plain(boolean_score['mean_relative_pct'])}",
            "cost": f"{pct_plain(boolean_time['mean_relative_pct'])} runtime",
            "role": "limited quality guard, not runtime claim",
            "status": status_from(
                int(boolean_score["wins"]) > int(boolean_score["losses"])
                and float(boolean_score["mean_relative_pct"]) < 0.0
                and float(boolean_time["mean_relative_pct"]) > 0.0
            ),
        },
        {
            "component": "Root-action neural candidate extension",
            "claim_class": "bounded",
            "scope": f"{root_union['scope']}; {root_union['pairs']} pairs",
            "quality": (
                f"union top-4+neural12 vs beam4 {root_union['score_wlt']}, "
                f"{root_union['mean_relative_score_pct']}; oracle24 headroom {root_union['oracle_headroom_pct']}"
            ),
            "cost": "root-only one-step audit; runtime not claimed",
            "role": "bounded candidate-extension evidence",
            "status": status_from(root_union["status"] == "pass"),
        },
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["component", "claim_class", "scope", "quality", "cost", "role", "status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    class_counts = Counter(row["claim_class"] for row in rows)
    lines = [
        "# Learned-Control Evidence Audit",
        "",
        "This table separates promoted learned/search-control components from limited diagnostics.",
        "It is intentionally conservative: small or runtime-negative AI components are labeled as limited rather than promoted.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "## Claim-class counts", ""])
    for claim_class in sorted(class_counts):
        lines.append(f"- {claim_class}: {class_counts[claim_class]}")
    lines.extend(
        [
            "",
            "| component | claim class | scope | quality evidence | cost/evaluation evidence | paper role | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["component"],
                    row["claim_class"],
                    row["scope"],
                    row["quality"],
                    row["cost"],
                    row["role"],
                    row["status"],
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
    replacements = [
        ("n=24,28,32,40", r"$n=24,28,32,40$"),
        ("n=28,40", r"$n=28,40$"),
        ("n=16", r"$n=16$"),
        ("n=14", r"$n=14$"),
        ("n=6", r"$n=6$"),
        ("n=23", r"$n=23$"),
        ("n23", r"$n=23$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Component & Class & Scope & Quality evidence & Cost evidence & Paper role \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["component"]),
                    tex_escape(row["claim_class"]),
                    tex_escape(row["scope"]),
                    tex_escape(row["quality"]),
                    tex_escape(row["cost"]),
                    tex_escape(row["role"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = Counter(row["status"] for row in rows)
    class_counts = Counter(row["claim_class"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "claim_class_counts": dict(sorted(class_counts.items())),
        "needs_revision_count": status_counts.get("needs revision", 0),
        "promoted_count": class_counts.get("promoted", 0),
        "bounded_count": class_counts.get("bounded", 0),
        "limited_count": class_counts.get("limited", 0),
        "not_promoted_count": class_counts.get("not promoted", 0),
        "sources": [
            "results/summary_boolean_screen_depth_frontier_policy_large.csv",
            "results/summary_frontier_random_depth_control.csv",
            "results/summary_stage_gated_frontier.csv",
            "results/summary_sparse_depth4_gate_generalization.csv",
            "results/summary_phase_affine_policy_rank_diverse.csv",
            "results/summary_phase_policy_budget_frontier.csv",
            "results/summary_boolean_neural_guard_vs_deterministic.csv",
            "results/summary_bitflip_random_prior_control.csv",
            "results/summary_bitflip_neural_budget_sweep.csv",
            "results/summary_bitflip_prior_feature_gate.csv",
            "results/summary_bitflip_prior_feature_gate_cv.csv",
            "results/summary_bitflip_prior_feature_gate_cv_random_control.csv",
            "results/summary_root_action_ranker_audit.csv",
        ],
        "outputs": {
            "summary": "results/summary_learned_control_audit.csv",
            "analysis": "results/analysis_learned_control_audit.md",
            "manifest": "results/manifest_learned_control_audit.json",
            "table": "paper_latex/tables/learned_control_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_learned_control_audit.csv", rows)
    write_markdown(RESULTS / "analysis_learned_control_audit.md", rows)
    write_latex(TABLES / "learned_control_audit.tex", rows)
    write_manifest(RESULTS / "manifest_learned_control_audit.json", rows)
    print(f"wrote {len(rows)} learned-control audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
