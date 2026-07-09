#!/usr/bin/env python3
"""Build a reviewer-facing evidence matrix for comparison baselines.

The manuscript already contains many focused analyses.  This script assembles
their coverage, verification status, headline paired result, and limitation
boundary into one reproducible table.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable_rows(path: Path) -> list[dict[str, str]]:
    rows = read_rows(path)
    out: list[dict[str, str]] = []
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        correct = str(row.get("correct", "")).strip().lower()
        if correct in {"false", "0"}:
            continue
        if str(row.get("verified_up_to_global_phase", "")).strip().lower() == "false":
            continue
        if str(row.get("anf_verified", "")).strip().lower() == "false":
            continue
        if str(row.get("circuit_anf_verified", "")).strip().lower() == "false":
            continue
        out.append(row)
    return out


def n_scope(rows: list[dict[str, str]]) -> str:
    values = sorted({int(row["n"]) for row in rows if row.get("n")})
    if not values:
        return ""
    if len(values) == 1:
        return f"n={values[0]}"
    if values == list(range(values[0], values[-1] + 1)):
        return f"n={values[0]}-{values[-1]}"
    return "n=" + ",".join(str(v) for v in values)


def rel_pct(new: float, old: float) -> float:
    return (new - old) / max(abs(old), 1.0) * 100.0


def pair_from_rows(
    paths: list[Path],
    target: str,
    baseline: str,
    metric: str = "score",
) -> tuple[int, int, int, int, float]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for path in paths:
        for row in usable_rows(path):
            name = row.get("name")
            method = row.get("method")
            if not name or not method:
                continue
            by_name.setdefault(name, {})[method] = row

    wins = losses = ties = 0
    rels: list[float] = []
    for methods in by_name.values():
        if target not in methods or baseline not in methods:
            continue
        new = float(methods[target][metric])
        old = float(methods[baseline][metric])
        rels.append(rel_pct(new, old))
        if new < old - 1e-9:
            wins += 1
        elif new > old + 1e-9:
            losses += 1
        else:
            ties += 1
    count = wins + losses + ties
    mean_rel = sum(rels) / len(rels) if rels else 0.0
    return count, wins, losses, ties, mean_rel


def find_summary_row(path: Path, target: str, baseline: str, metric: str = "score") -> dict[str, str]:
    for row in read_rows(path):
        if row.get("target") == target and row.get("baseline") == baseline and row.get("metric") == metric:
            return row
    raise KeyError(f"{path}: missing {target} vs {baseline} / {metric}")


def result_from_summary(path: Path, target: str, baseline: str, metric: str = "score") -> str:
    row = find_summary_row(path, target, baseline, metric)
    mean = 100.0 * float(row["mean_relative"])
    return f"{row['wins']}/{row['losses']}/{row['ties']}, {mean:+.2f}%"


def stage_result_from_summary(path: Path, source: str, method: str, baseline: str) -> str:
    for row in read_rows(path):
        if row.get("source") == source and row.get("method") == method and row.get("baseline") == baseline:
            mean = 100.0 * float(row["mean_rel_score"])
            return f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']}, {mean:+.2f}% score; {100.0 * float(row['mean_rel_time']):+.2f}% time"
    raise KeyError(f"{path}: missing {source} / {method} vs {baseline}")


def result_from_raw(paths: list[Path], target: str, baseline: str, metric: str = "score") -> str:
    count, wins, losses, ties, mean = pair_from_rows(paths, target, baseline, metric)
    if count == 0:
        return "no matched pairs"
    return f"{wins}/{losses}/{ties}, {mean:+.2f}%"


def raw_count(paths: list[Path]) -> tuple[int, int, str]:
    total = 0
    usable = 0
    all_rows: list[dict[str, str]] = []
    for path in paths:
        rows = read_rows(path)
        total += len(rows)
        ok = usable_rows(path)
        usable += len(ok)
        all_rows.extend(ok)
    return total, usable, n_scope(all_rows)


def csv_join(paths: list[Path]) -> str:
    return "; ".join(str(path.relative_to(THIS_DIR)) for path in paths)


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = [
        ("n=3,4,5,6,14,15,16,18", r"$n=3$--$6$, 14, 15, 16, 18"),
        ("n=20,24,28,32,40,48,56,64", r"$n=20$, 24, 28, 32, 40, 48, 56, 64"),
        ("n=20,24,28,32,40", r"$n=20$, 24, 28, 32, 40"),
        ("n=48,56,64", r"$n=48$, 56, 64"),
        ("n=3,4,5,6,14", r"$n=3$--$6$, 14"),
        ("n=21-26", r"$n=21$--$26$"),
        ("n=21-25", r"$n=21$--$25$"),
        ("n=3-6", r"$n=3$--$6$"),
        ("n<=6", r"$n\leq6$"),
        ("n=14", r"$n=14$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def build_matrix() -> list[dict[str, str]]:
    traditional = [RESULTS / "raw_traditional_resource.csv"]
    external_n6 = [RESULTS / "raw_traditional_resource.csv", RESULTS / "raw_external_traditional_resource_n6.csv"]
    ros_best = [RESULTS / "raw_ros_lut_proxy_best.csv"]
    ros_sweep = [RESULTS / "raw_ros_lut_proxy_sweep.csv"]
    ros_garbage = [RESULTS / "raw_ros_lut_garbage_proxy.csv"]
    ros_garbage_budget = [RESULTS / "raw_ros_lut_garbage_budget_frontier.csv"]
    stg_published = [RESULTS / "raw_stg_published_benchmark.csv"]
    stg_summary = RESULTS / "summary_stg_published_benchmark.csv"
    mockturtle = [RESULTS / "raw_mockturtle_xag_probe.csv", RESULTS / "raw_mockturtle_xag_highdim_probe.csv"]
    cirkit = [RESULTS / "raw_cirkit_aig_probe.csv", RESULTS / "raw_cirkit_aig_highdim_probe.csv"]
    revkit_cli = [RESULTS / "raw_revkit_cli_multiflow_traditional.csv"]
    phase = [RESULTS / "raw_phase_parity_affine.csv"]
    phase_policy = [RESULTS / "raw_phase_affine_policy_rank_diverse.csv"]
    truth_bridge = [
        RESULTS / "raw_truth_bridge_terms.csv",
        RESULTS / "raw_truth_bridge_n23_terms.csv",
        RESULTS / "raw_truth_bridge_n23_large_frontier_terms.csv",
        RESULTS / "raw_truth_bridge_n23_cost_time003_frontier_terms.csv",
        RESULTS / "raw_truth_bridge_n24_terms.csv",
        RESULTS / "raw_truth_bridge_n25_terms.csv",
        RESULTS / "raw_truth_bridge_n26_terms.csv",
    ]
    screen_scale = [
        RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
        RESULTS / "raw_screen_scale_depth_frontier_terms.csv",
        RESULTS / "raw_screen_scale_ultra_scale64_terms.csv",
    ]

    rows: list[dict[str, str]] = []

    total, usable, scope = raw_count(traditional)
    rows.append(
        {
            "evidence_block": "Internal logical baselines",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": (
                "Pareto vs direct ANF "
                + result_from_raw(traditional, "and_pareto_resource_nmcts", "direct_anf")
                + "; vs ESOP-MILP "
                + result_from_raw(traditional, "and_pareto_resource_nmcts", "and_esop_milp")
            ),
            "boundary": "Same verifier/cost model; includes direct, AND-direct, ESOP beam/MILP, SSHR-H, MCTS, affine, and Pareto variants.",
            "sources": csv_join(traditional),
        }
    )

    total, usable, scope = raw_count([RESULTS / "raw_external_traditional_resource_n6.csv"])
    rows.append(
        {
            "evidence_block": "Exported SSHR/ABC/BDD extension",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": (
                "Resource-NMCTS vs SSHR-I CNOT "
                + result_from_raw(external_n6, "and_resource_nmcts", "external_sshr_i_cnot")
                + "; vs ABC-XAG "
                + result_from_raw(external_n6, "and_resource_nmcts", "external_abc_xag")
            ),
            "boundary": "SSHR-I rows use an 8 s Gurobi budget; ABC/BDD rows are logical estimates over exported truth tables.",
            "sources": csv_join([RESULTS / "raw_external_traditional_resource_n6.csv"]),
        }
    )

    total_best, usable_best, scope = raw_count(ros_best)
    total_sweep, usable_sweep, _ = raw_count(ros_sweep)
    total_garbage, usable_garbage, _ = raw_count(ros_garbage)
    total_garbage_budget, usable_garbage_budget, _ = raw_count(ros_garbage_budget)
    rows.append(
        {
            "evidence_block": "ROS-style LUT proxy",
            "scope": scope,
            "verified_rows": f"{usable_best}/{total_best} best rows; {usable_sweep}/{total_sweep} K-sweep rows; {usable_garbage}/{total_garbage} garbage-proxy rows; {usable_garbage_budget}/{total_garbage_budget} garbage-budget rows",
            "main_result": "Pareto vs best-K proxy "
            + result_from_summary(
                RESULTS / "summary_ros_lut_proxy.csv",
                "and_pareto_resource_nmcts",
                "external_ros_lut_proxy",
            ),
            "boundary": "Verified LUT and executable garbage-pressure proxies only; no official ROS SAT garbage management, reversible emission, or hardware mapping.",
            "sources": csv_join(ros_best + ros_sweep + ros_garbage + ros_garbage_budget),
        }
    )

    total, usable, scope = raw_count(stg_published)
    rows.append(
        {
            "evidence_block": "Published STG optimum-library counterpoint",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": (
                "Pareto vs STG T-count optimum "
                + result_from_summary(stg_summary, "and_pareto_resource_nmcts", "STG T-count optimum", "T")
                + "; vs direct ANF on STG slice "
                + result_from_summary(stg_summary, "and_pareto_resource_nmcts", "direct_anf", "score")
            ),
            "boundary": "Public n=4/5 spectral-representative optimum-library table; this is a strong small-function counterpoint, not a reproduced ROS flow or scalable compiler baseline.",
            "sources": csv_join(stg_published + [stg_summary]),
        }
    )

    total, usable, scope = raw_count(mockturtle)
    rows.append(
        {
            "evidence_block": "mockturtle KLUT-to-XAG probe",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "n<=6 "
            + result_from_summary(
                RESULTS / "summary_mockturtle_xag_probe.csv",
                "and_pareto_resource_nmcts",
                "external_mockturtle_xag_k4",
            )
            + "; n=14 "
            + result_from_summary(
                RESULTS / "summary_mockturtle_xag_highdim_probe.csv",
                "and_pareto_resource_nmcts",
                "external_mockturtle_xag_k4",
            ),
            "boundary": "Official-header XAG resynthesis probe; still a logical proxy, not full ROS or reversible garbage management.",
            "sources": csv_join(mockturtle),
        }
    )

    total, usable, scope = raw_count(cirkit)
    rows.append(
        {
            "evidence_block": "CirKit AIG/MC probe",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "n<=6 "
            + result_from_summary(
                RESULTS / "summary_cirkit_aig_probe.csv",
                "and_pareto_resource_nmcts",
                "external_cirkit_aig_mc",
            )
            + "; n=14 "
            + result_from_summary(
                RESULTS / "summary_cirkit_aig_highdim_probe.csv",
                "and_pareto_resource_nmcts",
                "external_cirkit_aig_mc",
            ),
            "boundary": "AIG multiplicative-complexity probe; strongest current depth-oriented external counterpoint.",
            "sources": csv_join(cirkit),
        }
    )

    total, usable, scope = raw_count(revkit_cli)
    rows.append(
        {
            "evidence_block": "Legacy RevKit CLI exact oracle",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "Pareto vs best-score portfolio "
            + result_from_summary(
                RESULTS / "summary_revkit_cli_multiflow_traditional.csv",
                "and_pareto_resource_nmcts",
                "external_revkit_cli_best_score",
            ),
            "boundary": "Exact reversible oracle permutation; CNOT/depth are derived from Toffoli-control distributions and ancilla is a visible tradeoff.",
            "sources": csv_join(revkit_cli),
        }
    )

    total, usable, scope = raw_count(phase)
    rows.append(
        {
            "evidence_block": "RevKit phase/Rz branch",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "Affine phase vs RevKit oracle_synth "
            + result_from_summary(
                RESULTS / "summary_phase_parity_affine.csv",
                "phase_parity_affine_fprm_opt_tperrz30",
                "external_revkit_oracle_synth",
                "score_synth_tperrz30",
            ),
            "boundary": "Logical phase/Rz proxy verified up to global phase; sequence evidence is a coarse smoke check, not optimal Clifford+T synthesis.",
            "sources": csv_join(phase),
        }
    )

    total, usable, scope = raw_count(phase_policy)
    rows.append(
        {
            "evidence_block": "Learned phase pruning",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "Held-out n=6 rank-diverse top512 vs wide128 "
            + result_from_summary(
                RESULTS / "summary_phase_affine_policy_rank_diverse.csv",
                "phase_parity_affine_policy_diverse_tperrz30_top512",
                "phase_affine_wide128_tperrz30",
                "score_synth_tperrz30",
            ),
            "boundary": "Policy-pruned affine candidate ranking; evidence is held-out exact scoring, not a standalone compiler backend.",
            "sources": csv_join(phase_policy),
        }
    )

    total, usable, scope = raw_count(screen_scale)
    rows.append(
        {
            "evidence_block": "High-dimensional frontier search",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "Stage-gated vs all-depth scale "
            + stage_result_from_summary(
                RESULTS / "summary_stage_gated_frontier.csv",
                "scale_generalization",
                "stage_gated_frontier",
                "adaptive_all_depth",
            )
            + "; ultra n=48,56,64 stress 480/480 plan+circuit verified",
            "boundary": "Term-set symbolic verification with emitted-circuit ANF checks; depth frontier is a planning guard, not a hardware scheduler.",
            "sources": csv_join(screen_scale),
        }
    )

    total, usable, scope = raw_count(truth_bridge)
    rows.append(
        {
            "evidence_block": "Complete truth-table bridges",
            "scope": scope,
            "verified_rows": f"{usable}/{total}",
            "main_result": "Bridge rows verify plan, emitted symbolic circuit, and complete truth table for n=21-26.",
            "boundary": "Bridge set is intentionally narrow because complete truth tables grow exponentially.",
            "sources": csv_join(truth_bridge),
        }
    )

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["evidence_block", "scope", "verified_rows", "main_result", "boundary", "sources"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Comparison Evidence Matrix",
        "",
        "This table consolidates already-generated experiment evidence into the reviewer-facing comparison scope used by the manuscript.",
        "",
        "| evidence block | scope | verified rows | main result | boundary |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {evidence_block} | {scope} | {verified_rows} | {main_result} | {boundary} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Source files",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- {row['evidence_block']}: `{row['sources']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}}",
        r"\toprule",
        r"Evidence block & Scope & Verified rows & Main score result & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["evidence_block"]),
                latex_cell(row["scope"]),
                latex_cell(row["verified_rows"]),
                latex_cell(row["main_result"]),
                latex_cell(row["boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    raise_csv_field_limit()
    rows = build_matrix()
    write_csv(RESULTS / "summary_comparison_evidence_matrix.csv", rows)
    write_markdown(RESULTS / "analysis_comparison_evidence_matrix.md", rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    write_latex(TABLES / "comparison_evidence_matrix.tex", rows)
    print(f"wrote {RESULTS / 'summary_comparison_evidence_matrix.csv'}")
    print(f"wrote {RESULTS / 'analysis_comparison_evidence_matrix.md'}")
    print(f"wrote {TABLES / 'comparison_evidence_matrix.tex'}")


if __name__ == "__main__":
    main()
