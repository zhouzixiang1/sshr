#!/usr/bin/env python3
"""Assemble an evidence audit for learned search-control components."""
from __future__ import annotations

import csv
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


def build_rows() -> list[dict[str, str]]:
    frontier = read_csv(RESULTS / "summary_boolean_screen_depth_frontier_policy_large.csv")
    frontier_oracle = require_row(
        frontier,
        comparison="frontier_policy_vs_oracle_depth-2_3_4_frontier",
    )

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

    boolean_guard = read_csv(RESULTS / "summary_boolean_neural_guard_vs_deterministic.csv")
    boolean_score = require_row(boolean_guard, metric="score")
    boolean_time = require_row(boolean_guard, metric="time_s")

    bitflip_random = read_csv(RESULTS / "summary_bitflip_random_prior_control.csv")
    bitflip_score = require_row(bitflip_random, method="and_resource_nmcts", metric="score")
    bitflip_time = require_row(bitflip_random, method="and_resource_nmcts", metric="time_s")

    root_means = read_csv(RESULTS / "summary_highdim_root_action_oracle.csv")
    root_neural = require_row(root_means, method="root_neural_top4")
    root_beam = require_row(root_means, method="root_beam4_oracle_eval")
    root_oracle = require_row(root_means, method="root_oracle24")
    neural_vs_beam = (float(root_neural["mean_score"]) - float(root_beam["mean_score"])) / max(
        float(root_beam["mean_score"]), 1.0
    )
    oracle_vs_neural = (float(root_oracle["mean_score"]) - float(root_neural["mean_score"])) / max(
        float(root_neural["mean_score"]), 1.0
    )
    neural_time_vs_beam = (
        float(root_neural["mean_time_s"]) - float(root_beam["mean_time_s"])
    ) / max(float(root_beam["mean_time_s"]), 1e-9)

    return [
        {
            "component": "Depth-frontier policy",
            "scope": "held-out n=28,40; 48 rows",
            "quality": f"vs oracle frontier {frontier_oracle['score_wins']}/{frontier_oracle['score_losses']}/{frontier_oracle['score_ties']}, {pct(frontier_oracle['mean_rel_score'])}",
            "cost": f"{pct(frontier_oracle['mean_rel_time'])} time vs all-depth frontier",
            "role": "promoted quality/time selector",
        },
        {
            "component": "Stage-gated frontier",
            "scope": "independent n=24,28,32,40; 96 rows",
            "quality": f"vs all-depth {staged_scale['score_wins']}/{staged_scale['score_losses']}/{staged_scale['score_ties']}, {pct(staged_scale['mean_rel_score'])}",
            "cost": f"{pct(staged_scale['mean_rel_time'])} staged planning time",
            "role": "promoted validation-calibrated guard",
        },
        {
            "component": "Sparse depth-4 gate",
            "scope": "multi-seed n=24,28,32,40; 144 pairs",
            "quality": f"vs sparse frontier {sparse_gate_all['score_wlt_vs_sparse']}, {pct(sparse_gate_all['mean_rel_score_vs_sparse'])}; false skips {sparse_gate_all['false_skips']}",
            "cost": f"{pct(sparse_gate_all['mean_rel_time_vs_sparse'])} time vs sparse frontier",
            "role": "promoted budget gate after depth-2",
        },
        {
            "component": "Rank-diverse phase shortlist",
            "scope": "held-out n=6 phase search; 38 rows",
            "quality": f"vs budget-32 {wlt(phase_budget)}, {pct(phase_budget['mean_relative'])}; vs wide-128 {wlt(phase_wide)}, {pct(phase_wide['mean_relative'])}",
            "cost": "512/8192 exact forms per function",
            "role": "promoted phase-search pruning",
        },
        {
            "component": "Bit-flip learned prior",
            "scope": "177 n<=6 functions; 8 random-prior repeats",
            "quality": (
                f"vs random mean {bitflip_score['learned_wins']}/{bitflip_score['learned_losses']}/{bitflip_score['ties']}, "
                f"{pct_ratio(bitflip_score['mean_relative'])}; "
                f"seed means beaten {bitflip_score['seed_means_beaten']}/{bitflip_score['random_repeats']}"
            ),
            "cost": f"{pct_ratio(bitflip_time['mean_relative'])} runtime vs random-prior mean",
            "role": "limited quality signal, not runtime claim",
        },
        {
            "component": "Boolean neural guard",
            "scope": "n=16 high-dimensional guard; 24 rows",
            "quality": f"vs deterministic {wlt(boolean_score)}, {pct_plain(boolean_score['mean_relative_pct'])}",
            "cost": f"{pct_plain(boolean_time['mean_relative_pct'])} runtime",
            "role": "limited quality guard, not runtime claim",
        },
        {
            "component": "Root-action neural ranker",
            "scope": "n=14 root-action diagnostic; 10 rows",
            "quality": f"vs beam4 {100.0 * neural_vs_beam:+.2f}%; oracle24 headroom {100.0 * oracle_vs_neural:+.2f}%",
            "cost": f"{100.0 * neural_time_vs_beam:+.2f}% ranking time vs beam4 eval",
            "role": "not promoted; future root-ranker target",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["component", "scope", "quality", "cost", "role"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Learned-Control Evidence Audit",
        "",
        "This table separates promoted learned/search-control components from limited diagnostics.",
        "It is intentionally conservative: small or runtime-negative AI components are labeled as limited rather than promoted.",
        "",
        "| component | scope | quality evidence | cost/evaluation evidence | paper role |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join([row["component"], row["scope"], row["quality"], row["cost"], row["role"]])
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
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.19\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Component & Scope & Quality evidence & Cost evidence & Paper role \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["component"]),
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


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_learned_control_audit.csv", rows)
    write_markdown(RESULTS / "analysis_learned_control_audit.md", rows)
    write_latex(TABLES / "learned_control_audit.tex", rows)
    print(f"wrote {len(rows)} learned-control audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
