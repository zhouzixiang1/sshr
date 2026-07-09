#!/usr/bin/env python3
"""Bootstrap uncertainty intervals for learned-control effects.

The learned-control audit reports W/L/T summaries and role labels.  This
derived audit keeps the same claim boundary but adds paired percentile
bootstrap intervals for components with instance-level paired evidence.
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"

SUMMARY = RESULTS / "summary_learned_control_effect_uncertainty.csv"
ANALYSIS = RESULTS / "analysis_learned_control_effect_uncertainty.md"
MANIFEST = RESULTS / "manifest_learned_control_effect_uncertainty.json"
TABLE = TABLES / "learned_control_effect_uncertainty.tex"

BOOTSTRAP_SAMPLES = 3000
BOOTSTRAP_SEED = 20260710


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usable(row: dict[str, str]) -> bool:
    if row.get("error"):
        return False
    if row.get("skipped"):
        return False
    false_values = {"false", "0", "no"}
    for key in ("correct", "verified", "anf_verified", "circuit_anf_verified"):
        value = str(row.get(key, "")).strip().lower()
        if value in false_values:
            return False
    return True


def relative_pct(target: float, baseline: float) -> float:
    if baseline == 0.0:
        return 0.0 if target == 0.0 else math.copysign(float("inf"), target)
    return (target - baseline) / baseline * 100.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def bootstrap_ci(values: list[float], *, seed: int) -> tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        samples.append(statistics.mean(values[rng.randrange(n)] for _ in range(n)))
    return percentile(samples, 0.025), percentile(samples, 0.975)


def ci_excludes_zero(low: float, high: float) -> bool:
    return high < 0.0 or low > 0.0


def fmt_num(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.10g}"


def summarize_effect(
    *,
    component: str,
    claim_class: str,
    contrast: str,
    scope: str,
    score_rels: list[float],
    effort_rels: list[float],
    effort_metric: str,
    interpretation: str,
    source_files: Iterable[Path],
    min_pairs: int,
    seed_offset: int,
) -> dict[str, str]:
    score_ci = bootstrap_ci(score_rels, seed=BOOTSTRAP_SEED + seed_offset)
    effort_ci = bootstrap_ci(effort_rels, seed=BOOTSTRAP_SEED + 100 + seed_offset) if effort_rels else (float("nan"), float("nan"))
    score_mean = statistics.mean(score_rels) if score_rels else float("nan")
    effort_mean = statistics.mean(effort_rels) if effort_rels else float("nan")
    status = "pass" if len(score_rels) >= min_pairs and all(math.isfinite(v) for v in score_rels) else "needs revision"
    return {
        "component": component,
        "claim_class": claim_class,
        "contrast": contrast,
        "scope": scope,
        "pairs": str(len(score_rels)),
        "score_mean_pct": fmt_num(score_mean),
        "score_ci_low_pct": fmt_num(score_ci[0]),
        "score_ci_high_pct": fmt_num(score_ci[1]),
        "score_ci_excludes_zero": str(ci_excludes_zero(score_ci[0], score_ci[1])),
        "effort_metric": effort_metric,
        "effort_mean_pct": fmt_num(effort_mean),
        "effort_ci_low_pct": fmt_num(effort_ci[0]),
        "effort_ci_high_pct": fmt_num(effort_ci[1]),
        "effort_ci_excludes_zero": str(ci_excludes_zero(effort_ci[0], effort_ci[1])) if effort_rels else "",
        "interpretation": interpretation,
        "source_files": ";".join(str(path.relative_to(THIS_DIR)) for path in source_files),
        "status": status,
    }


def by_method_name(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        if usable(row):
            out.setdefault(row["name"], {})[row["method"]] = row
    return out


def depth_frontier_policy_effect() -> tuple[list[float], list[float]]:
    rows = [row for row in read_csv(RESULTS / "raw_boolean_screen_depth_frontier_policy_large.csv") if row["split"] == "test"]
    score_rels = [relative_pct(float(row["policy_score"]), float(row["oracle_score"])) for row in rows]
    time_rels = [relative_pct(float(row["policy_time_s"]), float(row["oracle_all_time_s"])) for row in rows]
    return score_rels, time_rels


def stage_gated_effect() -> tuple[list[float], list[float]]:
    staged = {
        row["name"]: row
        for row in read_csv(RESULTS / "raw_stage_gated_frontier.csv")
        if row["source"] == "scale_generalization" and usable(row)
    }
    baseline_rows = by_method_name(
        read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv")
    )
    score_rels: list[float] = []
    time_rels: list[float] = []
    for name, target in staged.items():
        baseline = baseline_rows.get(name, {}).get("adaptive_all_depth")
        if not baseline:
            continue
        score_rels.append(relative_pct(float(target["score"]), float(baseline["score"])))
        time_rels.append(relative_pct(float(target["time_s"]), float(baseline["time_s"])))
    return score_rels, time_rels


def sparse_gate_effect() -> tuple[list[float], list[float]]:
    rows = read_csv(RESULTS / "raw_sparse_depth4_gate_generalization.csv")
    score_rels = [float(row["rel_score_vs_sparse"]) * 100.0 for row in rows]
    time_rels = [float(row["rel_time_vs_sparse"]) * 100.0 for row in rows]
    return score_rels, time_rels


def phase_shortlist_effect() -> tuple[list[float], list[float]]:
    rows = read_csv(RESULTS / "raw_phase_affine_policy_rank_diverse.csv")
    methods = by_method_name([row for row in rows if row["split"] == "test_n6" and usable(row)])
    score_rels: list[float] = []
    effort_rels: list[float] = []
    for method_rows in methods.values():
        target = method_rows.get("phase_parity_affine_policy_diverse_tperrz30_top512")
        budget32 = method_rows.get("phase_affine_budget32_tperrz30")
        wide128 = method_rows.get("phase_affine_wide128_tperrz30")
        if not target or not budget32 or not wide128:
            continue
        score_rels.append(
            relative_pct(float(target["score_synth_tperrz30"]), float(budget32["score_synth_tperrz30"]))
        )
        effort_rels.append(relative_pct(float(target["exact_eval_forms"]), float(wide128["exact_eval_forms"])))
    return score_rels, effort_rels


def bitflip_random_prior_effect() -> tuple[list[float], list[float]]:
    learned = {
        row["name"]: row
        for row in read_csv(RESULTS / "raw_traditional_resource_learned_prior.csv")
        if usable(row) and row["method"] == "and_resource_nmcts"
    }
    random_by_name: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(RESULTS / "raw_bitflip_random_prior_control.csv"):
        if usable(row) and row["method"] == "and_resource_nmcts":
            random_by_name.setdefault(row["name"], []).append(row)
    score_rels: list[float] = []
    time_rels: list[float] = []
    for name, target in learned.items():
        random_rows = random_by_name.get(name, [])
        if not random_rows:
            continue
        random_score = statistics.mean(float(row["score"]) for row in random_rows)
        random_time = statistics.mean(float(row["time_s"]) for row in random_rows)
        score_rels.append(relative_pct(float(target["score"]), random_score))
        time_rels.append(relative_pct(float(target["time_s"]), random_time))
    return score_rels, time_rels


def bitflip_low_budget_effect() -> tuple[list[float], list[float]]:
    rows = [
        row
        for row in read_csv(RESULTS / "raw_bitflip_neural_budget_sweep.csv")
        if row["budget"] in {"top8_s8_n12", "top12_s12_n16"} and usable(row)
    ]
    by_key = {
        (row["budget"], row["variant"], row["method"], row["name"]): row
        for row in rows
    }
    score_rels: list[float] = []
    time_rels: list[float] = []
    for budget, variant, method, name in sorted(by_key):
        if variant != "learned_prior":
            continue
        baseline = by_key.get((budget, "no_prior", method, name))
        if not baseline:
            continue
        target = by_key[(budget, variant, method, name)]
        score_rels.append(relative_pct(float(target["score"]), float(baseline["score"])))
        time_rels.append(relative_pct(float(target["time_s"]), float(baseline["time_s"])))
    return score_rels, time_rels


def boolean_guard_effect() -> tuple[list[float], list[float]]:
    rows = read_csv(RESULTS / "raw_boolean_neural_guard_vs_deterministic.csv")
    score_rels = [float(row["relative_score_pct"]) for row in rows]
    time_rels = [float(row["relative_time_s_pct"]) for row in rows]
    return score_rels, time_rels


def root_action_effect() -> tuple[list[float], list[float]]:
    scoped_rows: list[dict[str, str]] = []
    for scope, path in (
        ("n14", RESULTS / "raw_highdim_root_action_pairwise_widths.csv"),
        ("n16", RESULTS / "raw_ultra_root_action_pairwise_widths.csv"),
    ):
        for row in read_csv(path):
            row = dict(row)
            row["scoped_name"] = f"{scope}:{row['name']}"
            scoped_rows.append(row)
    by_key: dict[str, dict[str, dict[str, str]]] = {}
    for row in scoped_rows:
        if usable(row):
            by_key.setdefault(row["scoped_name"], {})[row["method"]] = row
    score_rels: list[float] = []
    for methods in by_key.values():
        target = methods.get("root_union_h4_n12")
        baseline = methods.get("root_beam4_oracle_eval")
        if not target or not baseline:
            continue
        score_rels.append(relative_pct(float(target["score"]), float(baseline["score"])))
    return score_rels, []


def build_rows() -> list[dict[str, str]]:
    specs = [
        (
            "Depth-frontier policy",
            "promoted",
            "policy vs oracle depth-2/3/4 frontier",
            "held-out n=28,40",
            depth_frontier_policy_effect,
            "planning time",
            "Preserves oracle-frontier score within a narrow interval while reducing all-depth evaluation effort.",
            (RESULTS / "raw_boolean_screen_depth_frontier_policy_large.csv",),
            48,
        ),
        (
            "Stage-gated frontier",
            "promoted",
            "stage-gated frontier vs all-depth frontier",
            "independent n=24,28,32,40",
            stage_gated_effect,
            "planning time",
            "Validation-calibrated gate keeps score near the all-depth frontier while reducing planning time.",
            (
                RESULTS / "raw_stage_gated_frontier.csv",
                RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
            ),
            96,
        ),
        (
            "Sparse depth-4 gate",
            "promoted",
            "gate vs sparse frontier",
            "three independent seeds; n=24,28,32,40",
            sparse_gate_effect,
            "evaluation time",
            "Seed-stable skip gate preserves sparse-frontier score and reduces sparse-frontier evaluation time.",
            (RESULTS / "raw_sparse_depth4_gate_generalization.csv",),
            144,
        ),
        (
            "Rank-diverse phase shortlist",
            "promoted",
            "diverse top512 vs budget32 score; exact forms vs wide128",
            "held-out n=6 phase/Rz proxy",
            phase_shortlist_effect,
            "exact forms",
            "Policy shortlist improves the small-budget score while using far fewer exact evaluations than wide128.",
            (RESULTS / "raw_phase_affine_policy_rank_diverse.csv",),
            38,
        ),
        (
            "Bit-flip learned prior",
            "limited",
            "learned prior vs same-budget random-prior mean",
            "177 n<=6 functions",
            bitflip_random_prior_effect,
            "runtime",
            "Score effect is small and runtime-positive, so this remains a limited quality signal, not a speed claim.",
            (
                RESULTS / "raw_traditional_resource_learned_prior.csv",
                RESULTS / "raw_bitflip_random_prior_control.csv",
            ),
            177,
        ),
        (
            "Bit-flip low-budget prior",
            "bounded",
            "learned prior vs no-prior under top-8/top-12 budgets",
            "1062 budget/method/function pairs",
            bitflip_low_budget_effect,
            "runtime",
            "Low-budget learned prior has a bounded quality effect with visible runtime cost.",
            (RESULTS / "raw_bitflip_neural_budget_sweep.csv",),
            1062,
        ),
        (
            "Boolean neural guard",
            "limited",
            "neural guard vs deterministic Boolean guard",
            "24 n=16 high-dimensional rows",
            boolean_guard_effect,
            "runtime",
            "Quality effect is small and runtime-positive, so this remains a limited guard diagnostic.",
            (RESULTS / "raw_boolean_neural_guard_vs_deterministic.csv",),
            24,
        ),
        (
            "Root-action neural candidate extension",
            "bounded",
            "heuristic top-4 plus neural top-12 vs beam4",
            "n=14 and n=16 root-action slices",
            root_action_effect,
            "",
            "Root-only candidate extension is bounded score evidence; runtime is not claimed.",
            (
                RESULTS / "raw_highdim_root_action_pairwise_widths.csv",
                RESULTS / "raw_ultra_root_action_pairwise_widths.csv",
            ),
            33,
        ),
    ]
    rows: list[dict[str, str]] = []
    for idx, (
        component,
        claim_class,
        contrast,
        scope,
        effect_fn,
        effort_metric,
        interpretation,
        source_files,
        min_pairs,
    ) in enumerate(specs):
        score_rels, effort_rels = effect_fn()
        rows.append(
            summarize_effect(
                component=component,
                claim_class=claim_class,
                contrast=contrast,
                scope=scope,
                score_rels=score_rels,
                effort_rels=effort_rels,
                effort_metric=effort_metric,
                interpretation=interpretation,
                source_files=source_files,
                min_pairs=min_pairs,
                seed_offset=idx,
            )
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "component",
        "claim_class",
        "contrast",
        "scope",
        "pairs",
        "score_mean_pct",
        "score_ci_low_pct",
        "score_ci_high_pct",
        "score_ci_excludes_zero",
        "effort_metric",
        "effort_mean_pct",
        "effort_ci_low_pct",
        "effort_ci_high_pct",
        "effort_ci_excludes_zero",
        "interpretation",
        "source_files",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct_cell(row: dict[str, str], prefix: str) -> str:
    mean = float(row[f"{prefix}_mean_pct"])
    low = float(row[f"{prefix}_ci_low_pct"])
    high = float(row[f"{prefix}_ci_high_pct"])
    return f"{mean:+.2f}% [{low:+.2f}, {high:+.2f}]"


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Learned-Control Effect Uncertainty",
        "",
        "This audit adds deterministic paired bootstrap intervals to learned-control components with instance-level paired evidence.",
        f"Intervals use {BOOTSTRAP_SAMPLES} percentile bootstrap resamples per row.",
        "Negative score changes favor the learned or gated target.  Effort columns are planning time, runtime, exact evaluations, or blank when runtime is not claimed.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| component | class | pairs | score mean [95% CI] | effort mean [95% CI] | interpretation | status |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        effort = "" if not row["effort_metric"] else f"{row['effort_metric']}: {pct_cell(row, 'effort')}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["component"],
                    row["claim_class"],
                    row["pairs"],
                    pct_cell(row, "score"),
                    effort,
                    row["interpretation"],
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
        .replace("#", r"\#")
    )
    replacements = [
        ("n<=6", r"$n\leq6$"),
        ("n=14", r"$n=14$"),
        ("n=16", r"$n=16$"),
        ("n=24,28,32,40", r"$n=24,28,32,40$"),
        ("n=28,40", r"$n=28,40$"),
        ("n=6", r"$n=6$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def tex_pct_cell(row: dict[str, str], prefix: str) -> str:
    mean = float(row[f"{prefix}_mean_pct"])
    low = float(row[f"{prefix}_ci_low_pct"])
    high = float(row[f"{prefix}_ci_high_pct"])
    return f"${mean:+.2f}\\%$ [${low:+.2f}$, ${high:+.2f}$]"


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.10\linewidth}r>{\raggedleft\arraybackslash}p{0.21\linewidth}>{\raggedleft\arraybackslash}p{0.21\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Component & Class & Pairs & Score $\Delta$ [95\% CI] & Effort $\Delta$ [95\% CI] & Interpretation \\",
        r"\midrule",
    ]
    for row in rows:
        effort = "--"
        if row["effort_metric"]:
            effort = f"{tex_escape(row['effort_metric'])}: {tex_pct_cell(row, 'effort')}"
        lines.append(
            " & ".join(
                [
                    tex_escape(row["component"]),
                    tex_escape(row["claim_class"]),
                    row["pairs"],
                    tex_pct_cell(row, "score"),
                    effort,
                    tex_escape(row["interpretation"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    class_counts = Counter(row["claim_class"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "status_counts": dict(sorted(counts.items())),
        "claim_class_counts": dict(sorted(class_counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "score_ci_excludes_zero_count": sum(row["score_ci_excludes_zero"] == "True" for row in rows),
        "outputs": {
            "summary": str(SUMMARY.relative_to(THIS_DIR)),
            "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
            "manifest": str(MANIFEST.relative_to(THIS_DIR)),
            "table": str(TABLE.relative_to(THIS_DIR)),
        },
        "sources": sorted({source for row in rows for source in row["source_files"].split(";") if source}),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    failures = sum(1 for row in rows if row["status"] != "pass")
    print(f"wrote {len(rows)} learned-control effect-uncertainty rows")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
