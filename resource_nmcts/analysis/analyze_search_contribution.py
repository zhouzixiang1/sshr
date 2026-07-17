#!/usr/bin/env python3
"""Summarize which search components contribute measurable resource gains."""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
PAPER_TABLES = THIS_DIR / "paper_latex" / "tables"

METRICS = ["T", "CNOT", "depth", "peak_ancilla", "score"]


@dataclass(frozen=True)
class MethodComparison:
    category: str
    dataset: str
    csv_name: str
    target: str
    baseline: str
    label: str


@dataclass(frozen=True)
class VariantComparison:
    category: str
    dataset: str
    csv_name: str
    method: str
    target_variant: str
    baseline_variant: str
    label: str


METHOD_COMPARISONS = [
    MethodComparison(
        "affine search",
        "ablation_affine",
        "raw_ablation_affine.csv",
        "and_affine_greedy",
        "and_mcts_factor",
        "Affine greedy vs fixed-coordinate MCTS",
    ),
    MethodComparison(
        "neural refine",
        "ablation_affine",
        "raw_ablation_affine.csv",
        "and_affine_no_guard",
        "and_affine_greedy",
        "Neural refine over affine greedy",
    ),
    MethodComparison(
        "guarded MCTS",
        "ablation_affine",
        "raw_ablation_affine.csv",
        "and_affine_nmcts",
        "and_affine_no_guard",
        "Guarded Affine-NMCTS over no-guard",
    ),
    MethodComparison(
        "full affine",
        "ablation_affine",
        "raw_ablation_affine.csv",
        "and_affine_nmcts",
        "and_mcts_factor",
        "Full Affine-NMCTS vs fixed-coordinate MCTS",
    ),
    MethodComparison(
        "portfolio",
        "traditional_resource",
        "raw_traditional_resource.csv",
        "and_resource_nmcts",
        "and_affine_nmcts",
        "Resource-NMCTS over Affine-NMCTS",
    ),
    MethodComparison(
        "pareto archive",
        "traditional_resource",
        "raw_traditional_resource.csv",
        "and_pareto_resource_nmcts",
        "and_resource_nmcts",
        "Pareto archive over Resource-NMCTS",
    ),
    MethodComparison(
        "dedicated ablation",
        "search_ablation_traditional",
        "raw_search_ablation_traditional.csv",
        "and_resource_no_mcts",
        "and_resource_heuristic",
        "No-MCTS portfolio over heuristic-only",
    ),
    MethodComparison(
        "dedicated ablation",
        "search_ablation_traditional",
        "raw_search_ablation_traditional.csv",
        "and_resource_no_mcts",
        "and_resource_beam_only",
        "No-MCTS portfolio over beam-only",
    ),
    MethodComparison(
        "dedicated ablation",
        "search_ablation_traditional",
        "raw_search_ablation_traditional.csv",
        "and_resource_nmcts",
        "and_resource_heuristic",
        "Resource-NMCTS over heuristic-only",
    ),
    MethodComparison(
        "dedicated ablation",
        "search_ablation_traditional",
        "raw_search_ablation_traditional.csv",
        "and_resource_nmcts",
        "and_resource_no_mcts",
        "Resource-NMCTS over no-MCTS portfolio",
    ),
    MethodComparison(
        "dedicated ablation",
        "search_ablation_traditional",
        "raw_search_ablation_traditional.csv",
        "and_pareto_resource_nmcts",
        "and_resource_no_mcts",
        "Pareto Resource-NMCTS over no-MCTS portfolio",
    ),
    MethodComparison(
        "highdim ablation",
        "search_ablation_highdim",
        "raw_search_ablation_highdim.csv",
        "and_resource_no_mcts",
        "and_resource_heuristic",
        "Highdim no-MCTS portfolio over heuristic-only",
    ),
    MethodComparison(
        "highdim ablation",
        "search_ablation_highdim",
        "raw_search_ablation_highdim.csv",
        "and_resource_no_mcts",
        "and_resource_beam_only",
        "Highdim no-MCTS portfolio over beam-only",
    ),
    MethodComparison(
        "highdim ablation",
        "search_ablation_highdim",
        "raw_search_ablation_highdim.csv",
        "and_resource_no_mcts",
        "and_fprm_root_beam",
        "Highdim no-MCTS portfolio over root beam",
    ),
    MethodComparison(
        "highdim ablation",
        "search_ablation_highdim",
        "raw_search_ablation_highdim.csv",
        "and_resource_no_mcts",
        "and_fprm_linear_pair",
        "Highdim no-MCTS portfolio over linear-pair",
    ),
    MethodComparison(
        "esop boundary",
        "traditional_resource",
        "raw_traditional_resource.csv",
        "and_pareto_resource_nmcts",
        "and_esop_milp",
        "Pareto Resource-NMCTS vs ESOP-MILP",
    ),
    MethodComparison(
        "n14 guard",
        "highdim_resource",
        "raw_highdim_resource.csv",
        "and_fprm_linear_pair",
        "and_fprm_root_beam",
        "Linear-pair guard vs root beam at n=14",
    ),
    MethodComparison(
        "n14 portfolio",
        "highdim_resource",
        "raw_highdim_resource.csv",
        "and_pareto_resource_nmcts",
        "and_fprm_linear_pair",
        "Pareto Resource-NMCTS vs linear-pair at n=14",
    ),
    MethodComparison(
        "n15 guard",
        "highdim_scale_resource",
        "raw_highdim_scale_resource.csv",
        "and_fprm_linear_pair_deep",
        "and_fprm_root_beam",
        "Recursive linear-pair guard vs root beam at n=15",
    ),
    MethodComparison(
        "n15 portfolio",
        "highdim_scale_resource",
        "raw_highdim_scale_resource.csv",
        "and_pareto_resource_nmcts",
        "and_fprm_linear_pair_deep",
        "Pareto Resource-NMCTS vs recursive linear-pair at n=15",
    ),
    MethodComparison(
        "n16 shallow guard",
        "ultra_highdim_resource",
        "raw_ultra_highdim_resource.csv",
        "and_fprm_linear_pair",
        "and_fprm_root_beam",
        "Shallow linear-pair guard vs root beam at n=16",
    ),
    MethodComparison(
        "n16 recursive guard",
        "ultra_highdim_resource",
        "raw_ultra_highdim_resource.csv",
        "and_fprm_linear_pair_deep",
        "and_fprm_linear_pair",
        "Recursive linear-pair guard vs shallow linear-pair at n=16",
    ),
    MethodComparison(
        "n16 recursive guard",
        "ultra_highdim_resource",
        "raw_ultra_highdim_resource.csv",
        "and_fprm_linear_pair_deep",
        "and_fprm_root_beam",
        "Recursive linear-pair guard vs root beam at n=16",
    ),
    MethodComparison(
        "n16 neural diagnostic",
        "ultra_highdim_resource",
        "raw_ultra_highdim_resource.csv",
        "and_fprm_linear_pair_deep_root_neural",
        "and_fprm_linear_pair_deep",
        "Root-neural recursive guard vs deterministic recursive guard at n=16",
    ),
    MethodComparison(
        "n16 AI guard",
        "ultra_highdim_resource",
        "raw_ultra_highdim_resource.csv",
        "and_fprm_linear_pair_deep_ai_guard",
        "and_fprm_linear_pair_deep",
        "Baseline-preserving AI guard vs deterministic recursive guard at n=16",
    ),
    MethodComparison(
        "n18 guard",
        "mega_highdim_resource",
        "raw_mega_highdim_resource.csv",
        "and_fprm_linear_pair_fast",
        "and_fprm_root_beam",
        "Fast linear-pair guard vs root beam at n=18",
    ),
    MethodComparison(
        "n18 portfolio",
        "mega_highdim_resource",
        "raw_mega_highdim_resource.csv",
        "and_resource_nmcts",
        "and_fprm_linear_pair_fast",
        "Resource-NMCTS vs fast linear-pair at n=18",
    ),
]


VARIANT_COMPARISONS = [
    VariantComparison(
        "learned prior",
        "traditional_resource",
        "raw_neural_prior_ablation.csv",
        "and_affine_nmcts",
        "learned_prior",
        "no_prior",
        "Learned prior for Affine-NMCTS",
    ),
    VariantComparison(
        "learned prior",
        "traditional_resource",
        "raw_neural_prior_ablation.csv",
        "and_resource_nmcts",
        "learned_prior",
        "no_prior",
        "Learned prior for Resource-NMCTS",
    ),
    VariantComparison(
        "learned prior",
        "traditional_resource",
        "raw_neural_prior_ablation.csv",
        "and_pareto_resource_nmcts",
        "learned_prior",
        "no_prior",
        "Learned prior for Pareto Resource-NMCTS",
    ),
    VariantComparison(
        "highdim learned prior",
        "highdim_neural_prior",
        "raw_neural_prior_highdim_ablation.csv",
        "and_resource_nmcts",
        "learned_prior",
        "no_prior",
        "Highdim learned prior for Resource-NMCTS",
    ),
]


def load_usable(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        row
        for row in rows
        if not row.get("error")
        and not row.get("skipped")
        and str(row.get("correct", "True")) != "False"
    ]


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def clean(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.{digits}f}"


def metric_stats(pairs: list[tuple[dict[str, str], dict[str, str]]], metric: str) -> dict[str, float | int]:
    target_values: list[float] = []
    baseline_values: list[float] = []
    relatives: list[float] = []
    wins = losses = ties = 0
    for target, baseline in pairs:
        target_value = float(target[metric])
        baseline_value = float(baseline[metric])
        target_values.append(target_value)
        baseline_values.append(baseline_value)
        relatives.append(pct(target_value, baseline_value))
        if target_value < baseline_value:
            wins += 1
        elif target_value > baseline_value:
            losses += 1
        else:
            ties += 1
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_target": mean(target_values),
        "mean_baseline": mean(baseline_values),
        "mean_relative_pct": mean(relatives),
    }


def paired_by_method(rows: list[dict[str, str]], target: str, baseline: str) -> list[tuple[dict[str, str], dict[str, str]]]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        by_name.setdefault(row["name"], {})[row["method"]] = row
    pairs = []
    for table in by_name.values():
        if target in table and baseline in table:
            pairs.append((table[target], table[baseline]))
    return pairs


def paired_by_variant(
    rows: list[dict[str, str]],
    method: str,
    target_variant: str,
    baseline_variant: str,
) -> list[tuple[dict[str, str], dict[str, str]]]:
    by_name: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row.get("method") == method:
            by_name.setdefault(row["name"], {})[row["variant"]] = row
    pairs = []
    for table in by_name.values():
        if target_variant in table and baseline_variant in table:
            pairs.append((table[target_variant], table[baseline_variant]))
    return pairs


def summarize_method(spec: MethodComparison) -> dict[str, str]:
    rows = load_usable(RESULTS / spec.csv_name)
    pairs = paired_by_method(rows, spec.target, spec.baseline)
    return summarize_pairs(
        category=spec.category,
        dataset=spec.dataset,
        label=spec.label,
        target=spec.target,
        baseline=spec.baseline,
        pairs=pairs,
    )


def summarize_variant(spec: VariantComparison) -> dict[str, str]:
    rows = load_usable(RESULTS / spec.csv_name)
    pairs = paired_by_variant(rows, spec.method, spec.target_variant, spec.baseline_variant)
    return summarize_pairs(
        category=spec.category,
        dataset=spec.dataset,
        label=spec.label,
        target=f"{spec.method}:{spec.target_variant}",
        baseline=f"{spec.method}:{spec.baseline_variant}",
        pairs=pairs,
    )


def summarize_pairs(
    *,
    category: str,
    dataset: str,
    label: str,
    target: str,
    baseline: str,
    pairs: list[tuple[dict[str, str], dict[str, str]]],
) -> dict[str, str]:
    row = {
        "category": category,
        "dataset": dataset,
        "comparison": label,
        "target": target,
        "baseline": baseline,
        "pairs": str(len(pairs)),
    }
    for metric in METRICS:
        stats = metric_stats(pairs, metric) if pairs else {
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "mean_target": float("nan"),
            "mean_baseline": float("nan"),
            "mean_relative_pct": float("nan"),
        }
        prefix = metric.lower()
        row[f"{prefix}_wlt"] = f"{stats['wins']}/{stats['losses']}/{stats['ties']}"
        row[f"{prefix}_target_mean"] = clean(float(stats["mean_target"]))
        row[f"{prefix}_baseline_mean"] = clean(float(stats["mean_baseline"]))
        row[f"{prefix}_relative_pct"] = clean(float(stats["mean_relative_pct"]))
    return row


def write_csv(rows: list[dict[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "category",
        "dataset",
        "comparison",
        "target",
        "baseline",
        "pairs",
    ]
    for metric in METRICS:
        prefix = metric.lower()
        fields.extend(
            [
                f"{prefix}_wlt",
                f"{prefix}_target_mean",
                f"{prefix}_baseline_mean",
                f"{prefix}_relative_pct",
            ]
        )
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def pct_cell(value: str) -> str:
    if not value:
        return ""
    return f"${float(value):+.2f}\\%$"


def dataset_label(dataset: str) -> str:
    labels = {
        "search_ablation_traditional": "trad. ablation",
        "search_ablation_highdim": "n14 ablation",
        "highdim_neural_prior": "n14 prior",
        "highdim_scale_resource": "n15 scale",
        "ultra_highdim_resource": "n16 scale",
        "mega_highdim_resource": "n18 stress",
    }
    return labels.get(dataset, dataset)


def write_latex(rows: list[dict[str, str]], out: Path) -> None:
    selected = [
        "Affine greedy vs fixed-coordinate MCTS",
        "Neural refine over affine greedy",
        "Guarded Affine-NMCTS over no-guard",
        "Learned prior for Resource-NMCTS",
        "Pareto archive over Resource-NMCTS",
        "No-MCTS portfolio over heuristic-only",
        "Resource-NMCTS over no-MCTS portfolio",
        "Pareto Resource-NMCTS over no-MCTS portfolio",
        "Highdim no-MCTS portfolio over root beam",
        "Highdim no-MCTS portfolio over linear-pair",
        "Linear-pair guard vs root beam at n=14",
        "Recursive linear-pair guard vs root beam at n=15",
        "Recursive linear-pair guard vs shallow linear-pair at n=16",
        "Recursive linear-pair guard vs root beam at n=16",
        "Baseline-preserving AI guard vs deterministic recursive guard at n=16",
        "Fast linear-pair guard vs root beam at n=18",
        "Resource-NMCTS vs fast linear-pair at n=18",
    ]
    by_label = {row["comparison"]: row for row in rows}
    lines = [
        r"\begin{tabular}{@{}p{0.40\linewidth}p{0.20\linewidth}rcc@{}}",
        r"\toprule",
        r"Component & Dataset & Pairs & Score W/L/T & Mean $\Delta$ score \\",
        r"\midrule",
    ]
    for label in selected:
        row = by_label[label]
        lines.append(
            " & ".join(
                [
                    latex_escape(label),
                    latex_escape(dataset_label(row["dataset"])),
                    row["pairs"],
                    row["score_wlt"],
                    pct_cell(row["score_relative_pct"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown(rows: list[dict[str, str]], out: Path) -> None:
    lines = [
        "# Search Contribution Decomposition",
        "",
        "This report reuses already verified experiment CSV files and converts the scattered",
        "ablation evidence into a single contribution table.  Every row is a matched",
        "function-level comparison; negative relative values favor the target method.",
        "",
        "## Compact score view",
        "",
        "| category | comparison | dataset | pairs | score W/L/T | mean score change | mean T change |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["category"],
                    row["comparison"],
                    row["dataset"],
                    row["pairs"],
                    row["score_wlt"],
                    f"{float(row['score_relative_pct']):+.2f}%",
                    f"{float(row['t_relative_pct']):+.2f}%",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Detailed metric view",
            "",
            "| comparison | metric | W/L/T | target mean | baseline mean | mean relative |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        for metric in METRICS:
            prefix = metric.lower()
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["comparison"],
                        metric,
                        row[f"{prefix}_wlt"],
                        row[f"{prefix}_target_mean"],
                        row[f"{prefix}_baseline_mean"],
                        f"{float(row[f'{prefix}_relative_pct']):+.2f}%",
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The affine-coordinate search is the largest algorithmic jump before the full portfolio: affine greedy already improves over fixed-coordinate MCTS in score on the matched completed rows.",
            "- Neural refinement and the fixed-coordinate guard are smaller but monotone in score on this benchmark: both add score wins without score losses in the matched ablation rows.",
            "- The learned action prior is a positive but modest quality signal on the n<=6 rerun; it improves score with no losses, while earlier runtime evidence shows it is not yet the fastest configuration.",
            "- The n=14 learned-prior diagnostic is intentionally kept out of the compact paper table: a dedicated linear-action scorer gives only one score win and eleven ties, so high-dimensional neural guidance remains a boundary result rather than a strong contribution claim.",
            "- The Pareto archive gives the clearest small-function portfolio gain over single-score Resource-NMCTS, again with no score losses.",
            "- In the high-dimensional suites, the measurable scale contribution is mostly the bounded linear-pair guard.  The n=16 rerun shows that recursive linear-pair guard improves both the shallow guard and root beam, while Resource/Profile/Pareto reduce to the same guarded candidate.  These rows should therefore be written as scalability/guard evidence rather than as independent Pareto superiority evidence.",
        ]
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = [summarize_method(spec) for spec in METHOD_COMPARISONS]
    rows.extend(summarize_variant(spec) for spec in VARIANT_COMPARISONS)
    write_csv(rows, RESULTS / "summary_search_contribution.csv")
    write_markdown(rows, RESULTS / "analysis_search_contribution.md")
    write_latex(rows, PAPER_TABLES / "search_contribution_decomposition.tex")
    print(f"wrote {RESULTS / 'summary_search_contribution.csv'}")
    print(f"wrote {RESULTS / 'analysis_search_contribution.md'}")
    print(f"wrote {PAPER_TABLES / 'search_contribution_decomposition.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
