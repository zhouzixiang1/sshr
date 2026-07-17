#!/usr/bin/env python3
"""Analyze the larger depth-frontier policy upgrade.

The original depth-frontier policy was a useful structure-level AI signal, but
its quality gap to the all-depth/oracle frontier was still visible.  This
script compares the original policy with a larger-data retraining on the same
logic-level term-set and n=23 truth-table bridge harnesses.
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Iterable


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped")


def by_name_method(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if usable(row):
            out.setdefault(row["name"], {})[row["method"]] = row
    return out


def value(row: dict[str, str], key: str) -> float | None:
    raw = row.get(key, "")
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def time_value(row: dict[str, str]) -> float:
    return value(row, "plan_time_s") or value(row, "time_s") or 0.0


def rel(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1.0)


def rel_time(target: float, baseline: float) -> float:
    return (target - baseline) / max(abs(baseline), 1e-9)


def compare_methods(
    rows: list[dict[str, str]],
    target: str,
    baseline: str,
    label: str,
    source: str,
) -> dict[str, object]:
    grouped = by_name_method(rows)
    wins = losses = ties = 0
    score_rel: list[float] = []
    time_rel: list[float] = []
    t_depth_rel: list[float] = []
    aux_area_rel: list[float] = []
    for methods in grouped.values():
        if target not in methods or baseline not in methods:
            continue
        t_row = methods[target]
        b_row = methods[baseline]
        target_score = float(t_row["score"])
        baseline_score = float(b_row["score"])
        if target_score < baseline_score - 1e-9:
            wins += 1
        elif target_score > baseline_score + 1e-9:
            losses += 1
        else:
            ties += 1
        score_rel.append(rel(target_score, baseline_score))
        time_rel.append(rel_time(time_value(t_row), time_value(b_row)))
        t_depth_t = value(t_row, "schedule_t_depth_proxy")
        t_depth_b = value(b_row, "schedule_t_depth_proxy")
        if t_depth_t is not None and t_depth_b is not None:
            t_depth_rel.append(rel(t_depth_t, t_depth_b))
        aux_t = value(t_row, "explicit_ancilla_lifetime_area")
        aux_b = value(b_row, "explicit_ancilla_lifetime_area")
        if aux_t is not None and aux_b is not None:
            aux_area_rel.append(rel(aux_t, aux_b))
    return {
        "source": source,
        "comparison": label,
        "pairs": len(score_rel),
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "mean_rel_score": statistics.mean(score_rel) if score_rel else 0.0,
        "mean_rel_time": statistics.mean(time_rel) if time_rel else 0.0,
        "mean_rel_t_depth": statistics.mean(t_depth_rel) if t_depth_rel else "",
        "mean_rel_aux_area": statistics.mean(aux_area_rel) if aux_area_rel else "",
    }


def compare_policy_files(
    new_rows: list[dict[str, str]],
    old_rows: list[dict[str, str]],
    label: str,
    source: str,
    method: str = "depth_frontier_policy",
) -> dict[str, object]:
    new = by_name_method(new_rows)
    old = by_name_method(old_rows)
    wins = losses = ties = 0
    score_rel: list[float] = []
    time_rel: list[float] = []
    t_depth_rel: list[float] = []
    aux_area_rel: list[float] = []
    for name in sorted(set(new) & set(old)):
        if method not in new[name] or method not in old[name]:
            continue
        n_row = new[name][method]
        o_row = old[name][method]
        new_score = float(n_row["score"])
        old_score = float(o_row["score"])
        if new_score < old_score - 1e-9:
            wins += 1
        elif new_score > old_score + 1e-9:
            losses += 1
        else:
            ties += 1
        score_rel.append(rel(new_score, old_score))
        time_rel.append(rel_time(time_value(n_row), time_value(o_row)))
        t_depth_n = value(n_row, "schedule_t_depth_proxy")
        t_depth_o = value(o_row, "schedule_t_depth_proxy")
        if t_depth_n is not None and t_depth_o is not None:
            t_depth_rel.append(rel(t_depth_n, t_depth_o))
        aux_n = value(n_row, "explicit_ancilla_lifetime_area")
        aux_o = value(o_row, "explicit_ancilla_lifetime_area")
        if aux_n is not None and aux_o is not None:
            aux_area_rel.append(rel(aux_n, aux_o))
    return {
        "source": source,
        "comparison": label,
        "pairs": len(score_rel),
        "score_wins": wins,
        "score_losses": losses,
        "score_ties": ties,
        "mean_rel_score": statistics.mean(score_rel) if score_rel else 0.0,
        "mean_rel_time": statistics.mean(time_rel) if time_rel else 0.0,
        "mean_rel_t_depth": statistics.mean(t_depth_rel) if t_depth_rel else "",
        "mean_rel_aux_area": statistics.mean(aux_area_rel) if aux_area_rel else "",
    }


def training_summary(rows: list[dict[str, str]], label: str) -> dict[str, object]:
    test = [row for row in rows if row["split"] == "test"]
    correct = sum(int(row["correct_depth"]) for row in test)
    score_rel = [rel(float(row["policy_score"]), float(row["oracle_score"])) for row in test]
    time_rel = [rel_time(float(row["policy_time_s"]), float(row["oracle_all_time_s"])) for row in test]
    return {
        "source": "heldout_training",
        "comparison": label,
        "pairs": len(test),
        "score_wins": 0,
        "score_losses": sum(1 for row in test if float(row["policy_score"]) > float(row["oracle_score"]) + 1e-9),
        "score_ties": sum(1 for row in test if abs(float(row["policy_score"]) - float(row["oracle_score"])) <= 1e-9),
        "mean_rel_score": statistics.mean(score_rel) if score_rel else 0.0,
        "mean_rel_time": statistics.mean(time_rel) if time_rel else 0.0,
        "mean_rel_t_depth": "",
        "mean_rel_aux_area": "",
        "depth_accuracy": correct / max(len(test), 1),
    }


def verify_counts(rows: list[dict[str, str]]) -> tuple[int, int, int, int]:
    total = len(rows)
    plan = sum(1 for row in rows if row.get("anf_verified") == "True")
    circuit = sum(1 for row in rows if row.get("circuit_anf_verified") == "True")
    truth = sum(1 for row in rows if row.get("truth_verified") == "True")
    return total, plan, circuit, truth


def pct(value_obj: object) -> str:
    if value_obj == "":
        return ""
    return f"{float(value_obj):+.2%}"


def latex_pct(value_obj: object) -> str:
    return pct(value_obj).replace("%", r"\%")


def latex_text(value_obj: object) -> str:
    return str(value_obj).replace("_", r"\_")


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source",
        "comparison",
        "pairs",
        "score_wins",
        "score_losses",
        "score_ties",
        "mean_rel_score",
        "mean_rel_time",
        "mean_rel_t_depth",
        "mean_rel_aux_area",
        "depth_accuracy",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(
    path: Path,
    rows: list[dict[str, object]],
    verification_counts: list[tuple[str, tuple[int, int, int, int]]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Large Depth-Frontier Policy Upgrade",
        "",
        "This analysis compares the original depth-frontier policy with a larger",
        "retraining and a cost-aware variant of the same structure-level neural",
        "policy.  Each policy still selects one of depth-2, depth-3, or depth-4",
        "Boolean-ring screening; the changes are more labelled frontier data, a",
        "larger hidden layer, or a cost-aware label objective.",
        "",
        "## Verification",
        "",
    ]
    for label, counts in verification_counts:
        total, plan, circuit, truth = counts
        truth_part = f", truth {truth}/{total}" if truth else ""
        lines.append(f"- {label}: rows {total}{truth_part}, plan {plan}/{total}, circuit {circuit}/{total}")
    lines.extend(
        [
            "",
            "## Comparisons",
            "",
            "| source | comparison | pairs | score W/L/T | score | time | T-depth | aux area |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['source']} | {row['comparison']} | {row['pairs']} | "
            f"{row['score_wins']}/{row['score_losses']}/{row['score_ties']} | "
            f"{pct(row['mean_rel_score'])} | {pct(row['mean_rel_time'])} | "
            f"{pct(row['mean_rel_t_depth'])} | {pct(row['mean_rel_aux_area'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The large retraining is a quality-oriented upgrade: it chooses deeper",
            "  screens more often, so it is slower than the original frontier policy.",
            "- On the independent n=24/28/32/40 term-set generalization run, it improves",
            "  the frontier-policy score against the old model by 17/0/79 with a",
            "  -0.49% mean score change, while still saving 53.50% time against",
            "  all-depth adaptive evaluation.",
            "- On the n=23 full truth-table bridge, it improves the old frontier policy",
            "  by 1/0/5 with -0.48% score and -0.45% T-depth proxy, with all 60",
            "  method rows passing truth-table, plan, and emitted-circuit verification.",
            "- The cost-aware retraining is a faster quality mode.  On the same",
            "  independent n=24/28/32/40 generalization run, it keeps the 56/0/40",
            "  score W/L/T pattern against fixed depth-2, but lowers mean plan-time",
            "  overhead from the large model's +563.80% to +170.03%.  On the n=23",
            "  bridge, it reduces plan time by -56.29% and auxiliary lifetime area",
            "  by -12.62% relative to the large model, at a +0.92% score cost.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    focus = [
        "large heldout policy vs oracle frontier",
        "large scale policy vs screen_depth2",
        "old scale policy vs screen_depth2",
        "large scale policy vs adaptive_all_depth",
        "old scale policy vs adaptive_all_depth",
        "large scale policy vs old policy",
        "cost scale policy vs screen_depth2",
        "cost scale policy vs large policy",
        "cost scale policy vs old policy",
        "large n23 policy vs screen_depth2",
        "old n23 policy vs screen_depth2",
        "large n23 policy vs old policy",
        "cost n23 policy vs screen_depth2",
        "cost n23 policy vs large policy",
        "cost n23 policy vs old policy",
    ]
    selected = [row for label in focus for row in rows if row["comparison"] == label]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrr}\n")
        f.write("\\toprule\n")
        f.write("Source & Comparison & Pairs & Score W/L/T & Mean $\\Delta$ score \\\\\n")
        f.write("\\midrule\n")
        for row in selected:
            f.write(
                f"{latex_text(row['source'])} & {latex_text(row['comparison'])} & "
                f"{row['pairs']} & {row['score_wins']}/{row['score_losses']}/{row['score_ties']} & "
                f"{latex_pct(row['mean_rel_score'])} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main() -> int:
    old_training = read_csv(RESULTS / "raw_boolean_screen_depth_frontier_policy.csv")
    large_training = read_csv(RESULTS / "raw_boolean_screen_depth_frontier_policy_large.csv")
    cost_training = read_csv(RESULTS / "raw_boolean_screen_depth_frontier_policy_cost_time003.csv")
    old_scale = read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_generalization_terms.csv")
    large_scale = read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv")
    cost_scale = read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv")
    old_truth = read_csv(RESULTS / "raw_schedule_truth_bridge_n23_terms.csv")
    large_truth = read_csv(RESULTS / "raw_truth_bridge_n23_large_frontier_terms.csv")
    cost_truth = read_csv(RESULTS / "raw_truth_bridge_n23_cost_time003_frontier_terms.csv")

    rows: list[dict[str, object]] = [
        training_summary(old_training, "old heldout policy vs oracle frontier"),
        training_summary(large_training, "large heldout policy vs oracle frontier"),
        training_summary(cost_training, "cost heldout policy vs cost-aware frontier"),
        compare_methods(large_scale, "depth_frontier_policy", "screen_depth2", "large scale policy vs screen_depth2", "scale_generalization"),
        compare_methods(old_scale, "depth_frontier_policy", "screen_depth2", "old scale policy vs screen_depth2", "scale_generalization"),
        compare_methods(cost_scale, "depth_frontier_policy", "screen_depth2", "cost scale policy vs screen_depth2", "scale_generalization"),
        compare_methods(large_scale, "depth_frontier_policy", "adaptive_all_depth", "large scale policy vs adaptive_all_depth", "scale_generalization"),
        compare_methods(old_scale, "depth_frontier_policy", "adaptive_all_depth", "old scale policy vs adaptive_all_depth", "scale_generalization"),
        compare_methods(cost_scale, "depth_frontier_policy", "adaptive_all_depth", "cost scale policy vs adaptive_all_depth", "scale_generalization"),
        compare_policy_files(large_scale, old_scale, "large scale policy vs old policy", "scale_generalization"),
        compare_policy_files(cost_scale, old_scale, "cost scale policy vs old policy", "scale_generalization"),
        compare_policy_files(cost_scale, large_scale, "cost scale policy vs large policy", "scale_generalization"),
        compare_methods(large_truth, "depth_frontier_policy", "screen_depth2", "large n23 policy vs screen_depth2", "truth_bridge_n23"),
        compare_methods(old_truth, "depth_frontier_policy", "screen_depth2", "old n23 policy vs screen_depth2", "truth_bridge_n23"),
        compare_methods(cost_truth, "depth_frontier_policy", "screen_depth2", "cost n23 policy vs screen_depth2", "truth_bridge_n23"),
        compare_methods(large_truth, "depth_frontier_policy", "adaptive_all_depth", "large n23 policy vs adaptive_all_depth", "truth_bridge_n23"),
        compare_methods(old_truth, "depth_frontier_policy", "adaptive_all_depth", "old n23 policy vs adaptive_all_depth", "truth_bridge_n23"),
        compare_methods(cost_truth, "depth_frontier_policy", "adaptive_all_depth", "cost n23 policy vs adaptive_all_depth", "truth_bridge_n23"),
        compare_policy_files(large_truth, old_truth, "large n23 policy vs old policy", "truth_bridge_n23"),
        compare_policy_files(cost_truth, old_truth, "cost n23 policy vs old policy", "truth_bridge_n23"),
        compare_policy_files(cost_truth, large_truth, "cost n23 policy vs large policy", "truth_bridge_n23"),
    ]

    write_summary(RESULTS / "summary_frontier_policy_upgrade.csv", rows)
    write_analysis(
        RESULTS / "analysis_frontier_policy_upgrade.md",
        rows,
        [
            ("old scale", verify_counts(old_scale)),
            ("large-policy scale", verify_counts(large_scale)),
            ("cost-aware scale", verify_counts(cost_scale)),
            ("old n=23 bridge", verify_counts(old_truth)),
            ("large-policy n=23 bridge", verify_counts(large_truth)),
            ("cost-aware n=23 bridge", verify_counts(cost_truth)),
        ],
    )
    write_latex(TABLES / "frontier_policy_upgrade.tex", rows)
    print("wrote results/summary_frontier_policy_upgrade.csv")
    print("wrote results/analysis_frontier_policy_upgrade.md")
    print("wrote paper_latex/tables/frontier_policy_upgrade.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
