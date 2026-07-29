#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate F4 from the frozen primary20 statistics without modifying them.

The figure deliberately applies the frozen three-part claim gate: family-wise
Holm rejection, a strictly negative upper confidence bound for the raw median
difference, and a strictly positive lower confidence bound for median relative
improvement.  Intervals that merely touch zero remain neutral.

Run from ``resource_nmcts/`` with the ``mcts-qoracle`` Python interpreter.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "submission_competition" / "figures"
STEM = "F4_frozen_primary_results"
SOURCE_CSV = OUTDIR / "primary_results_figure_source.csv"
SOURCE_JSON = OUTDIR / "primary_results_figure_source.json"
MANIFEST_PATH = OUTDIR / "primary_results_figure_manifest.json"
QA_PREVIEW = OUTDIR / "_qa_f4_preview.png"
QA_NOTES = OUTDIR / "PRIMARY_RESULTS_FIGURE_QA.md"
CONTRACT_PATH = OUTDIR / "FIGURE_CONTRACT_PRIMARY_RESULTS.md"
FINAL_ANALYSIS_MANIFEST = ROOT / "submission_competition" / "final_analysis_manifest.json"
FINAL_HEADLINE = ROOT / "results" / "final_stats" / "primary20_headline.json"

WIDTH_MM = 183.0
HEIGHT_MM = 130.0
MM = 1.0 / 25.4
PNG_DPI = 600
PREVIEW_WIDTH_PX = 1800

INK = "#182632"
MUTED = "#65737E"
GRID = "#CDD5DB"
NEUTRAL = "#7C8891"
NEUTRAL_LIGHT = "#F4F6F7"
SIGNAL = "#217A67"
SIGNAL_DARK = "#155B4D"
SIGNAL_LIGHT = "#DDEFEA"
ZERO = "#3F4B54"
WHITE = "#FFFFFF"

STAT_FILES: tuple[tuple[str, str, Path], ...] = (
    ("direct_anf", "Direct ANF", ROOT / "results" / "final_stats" / "resource_vs_direct_anf.json"),
    ("greedy_factor", "Greedy factor", ROOT / "results" / "final_stats" / "resource_vs_greedy_factor.json"),
    ("mcts_factor", "MCTS factor", ROOT / "results" / "final_stats" / "resource_vs_mcts_factor.json"),
    ("sshr_h", "SSHR-H", ROOT / "results" / "final_stats" / "resource_vs_sshr_h.json"),
    ("sshr_beam", "SSHR-Beam", ROOT / "results" / "final_stats" / "resource_vs_sshr_beam.json"),
)

METRICS: tuple[dict[str, str], ...] = (
    {"key": "t_count", "label": "T count", "scope": "logical", "family": "logical_primary"},
    {"key": "cnot_count", "label": "CNOT count", "scope": "logical", "family": "logical_primary"},
    {
        "key": "native_entangling_count",
        "label": "Native 2Q",
        "scope": "mapping",
        "family": "mapping_primary",
    },
    {"key": "mapped_depth", "label": "Mapped depth", "scope": "mapping", "family": "mapping_primary"},
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _resolved_font() -> tuple[str, list[str]]:
    preferred = ["Arial", "Microsoft YaHei", "DejaVu Sans", "Liberation Sans"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for candidate in preferred:
        if candidate in installed:
            return candidate, preferred
    return "DejaVu Sans", preferred


RESOLVED_FONT, FONT_FALLBACK = _resolved_font()

# Mandatory Nature-figure editable-text rules.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams.update(
    {
        "font.sans-serif": FONT_FALLBACK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 6.0,
        "axes.titlesize": 7.0,
        "axes.labelsize": 6.2,
        "xtick.labelsize": 5.6,
        "ytick.labelsize": 5.8,
        "legend.fontsize": 5.7,
        "axes.linewidth": 0.65,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    }
)


def _load_statistics(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"frozen statistics file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2:
        raise ValueError(f"unexpected statistics schema in {path}")
    input_meta = payload.get("input", {})
    if not input_meta.get("opened_read_only") or not input_meta.get("database_unchanged"):
        raise ValueError(f"statistics provenance is not read-only/unchanged: {path}")
    if input_meta.get("database_sha256_before") != input_meta.get("database_sha256_after"):
        raise ValueError(f"database hash changed during source analysis: {path}")
    return payload


def _strict_status(row: Mapping[str, Any]) -> tuple[bool, str]:
    holm_reject = bool(row["holm_reject"])
    ci_low = float(row["median_delta_ci_low"])
    ci_high = float(row["median_delta_ci_high"])
    relative_ci_low = float(row["median_relative_improvement_pct_ci_low"])
    relative_ci_high = float(row["median_relative_improvement_pct_ci_high"])
    strict = holm_reject and ci_high < 0.0 and relative_ci_low > 0.0
    if strict:
        return (
            True,
            "Holm rejected; raw median-delta CI is strictly below zero; "
            "median-relative-improvement CI is strictly above zero",
        )
    if not holm_reject:
        return False, "family-Holm test did not reject"
    if math.isclose(ci_high, 0.0, abs_tol=1e-12):
        return False, "raw median-delta CI touches zero"
    if ci_low < 0.0 < ci_high:
        return False, "raw median-delta CI crosses zero"
    if ci_low >= 0.0:
        return False, "raw median-delta CI is non-negative"
    if math.isclose(relative_ci_low, 0.0, abs_tol=1e-12):
        return False, "median-relative-improvement CI touches zero"
    if relative_ci_low < 0.0 < relative_ci_high:
        return False, "median-relative-improvement CI crosses zero"
    if relative_ci_high <= 0.0:
        return False, "median-relative-improvement CI is non-positive"
    return False, "strict gate not satisfied"


def _select_primary_row(
    payload: Mapping[str, Any], metric: Mapping[str, str], source_path: Path
) -> Mapping[str, Any]:
    rows = [
        row
        for row in payload["summaries"]
        if row.get("metric") == metric["key"] and row.get("scope") == metric["scope"]
    ]
    if len(rows) != 1:
        raise ValueError(
            f"expected exactly one {metric['scope']}:{metric['key']} row in {source_path}, got {len(rows)}"
        )
    row = rows[0]
    if row.get("holm_family") != metric["family"]:
        raise ValueError(f"primary family drifted for {source_path}:{metric['key']}")
    if not row.get("lower_is_better"):
        raise ValueError(f"metric direction drifted for {source_path}:{metric['key']}")
    return row


def _load_final_alignment(
    comparisons: Sequence[Mapping[str, Any]],
    *,
    analysis_contract_sha256: str,
    database_sha256: str,
    required_seeds: Sequence[int],
) -> dict[str, Any]:
    """Cross-check figure classification and timeout wording against final outputs."""
    for path in (FINAL_ANALYSIS_MANIFEST, FINAL_HEADLINE):
        if not path.exists():
            raise FileNotFoundError(f"final analysis alignment input is missing: {path}")
    manifest = json.loads(FINAL_ANALYSIS_MANIFEST.read_text(encoding="utf-8"))
    headline = json.loads(FINAL_HEADLINE.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or headline.get("schema_version") != 1:
        raise ValueError("unexpected final-analysis/headline schema")
    headline_path = _relative(FINAL_HEADLINE)
    recorded_headline_hash = manifest.get("outputs", {}).get(headline_path)
    actual_headline_hash = _sha256(FINAL_HEADLINE)
    if recorded_headline_hash != actual_headline_hash:
        raise ValueError("final-analysis manifest does not authenticate the headline JSON")
    if manifest.get("analysis_contract_sha256") != analysis_contract_sha256:
        raise ValueError("final-analysis contract hash differs from frozen pairwise statistics")
    if headline.get("analysis_contract_sha256") != analysis_contract_sha256:
        raise ValueError("headline contract hash differs from frozen pairwise statistics")
    if manifest.get("database_sha256") != database_sha256 or headline.get("database_sha256") != database_sha256:
        raise ValueError("final-analysis database hash differs from frozen pairwise statistics")
    if list(headline.get("required_seeds", [])) != list(required_seeds):
        raise ValueError("final headline required-seed contract drifted")

    headline_rows = {
        (str(row["reference_method"]), str(row["metric"])): row
        for row in headline.get("headline_rows", [])
    }
    if len(headline_rows) != len(comparisons):
        raise ValueError("final headline does not contain exactly the 20 primary comparisons")
    for row in comparisons:
        key = (str(row["reference_method"]), str(row["metric_key"]))
        if key not in headline_rows:
            raise ValueError(f"final headline is missing {key}")
        final_row = headline_rows[key]
        if bool(final_row["strict_significant_better"]) != bool(row["strict_supported"]):
            raise ValueError(f"strict classification differs from final headline for {key}")
        numeric_fields = (
            "median_delta_ci_high",
            "median_relative_improvement_pct_ci_low",
            "holm_p_adjusted",
        )
        if any(
            not math.isclose(float(final_row[field]), float(row[field]), rel_tol=0.0, abs_tol=1e-12)
            for field in numeric_fields
        ):
            raise ValueError(f"final headline numeric gate fields differ for {key}")

    computed_strict_count = sum(bool(row["strict_supported"]) for row in comparisons)
    if computed_strict_count != int(manifest["strict_significant_better_count"]):
        raise ValueError("strict result count differs from final-analysis manifest")

    coverage = manifest.get("coverage", {})
    missing = list(coverage.get("missing", []))
    if int(coverage.get("missing_cells", -1)) != len(missing):
        raise ValueError("final-analysis missing-cell count is inconsistent")
    if not missing:
        raise ValueError("expected the frozen SSHR-Beam timeout boundary")
    if any(row.get("requested_method") != "sshr_beam" for row in missing):
        raise ValueError("non-SSHR-Beam cell appears in the frozen missing set")
    if any(row.get("family") != "aes_sbox" for row in missing):
        raise ValueError("non-AES function appears in the SSHR-Beam missing set")

    timeout_values: set[int] = set()
    timeout_cases: dict[str, set[int]] = {}
    for row in missing:
        match = re.fullmatch(r"synthesis_timeout_(\d+)s", str(row.get("status")))
        if match is None:
            raise ValueError("unexpected missing-cell status in final analysis")
        timeout_values.add(int(match.group(1)))
        timeout_cases.setdefault(str(row["case_id"]), set()).add(int(row["synthesis_seed"]))
    if len(timeout_values) != 1:
        raise ValueError("SSHR-Beam timeout duration is not unique")
    expected_seeds = {int(value) for value in required_seeds}
    if any(seeds != expected_seeds for seeds in timeout_cases.values()):
        raise ValueError("not every missing AES function timed out for all required seeds")

    beam_n = next(
        int(row["n_functions"])
        for row in comparisons
        if row["baseline_key"] == "sshr_beam"
    )
    shared_n = max(int(row["n_functions"]) for row in comparisons)
    if shared_n - beam_n != len(timeout_cases):
        raise ValueError("SSHR-Beam complete-case n does not match the timeout case count")

    return {
        "analysis_id": manifest["analysis_id"],
        "analysis_payload_sha256": manifest["analysis_payload_sha256"],
        "claim_gate": headline["claim_gate"],
        "strict_significant_better_count": computed_strict_count,
        "coverage_boundary": {
            "method": "sshr_beam",
            "family": "aes_sbox",
            "case_ids": sorted(timeout_cases),
            "case_count": len(timeout_cases),
            "seeds": list(required_seeds),
            "seeds_per_case": len(required_seeds),
            "timeout_seconds": next(iter(timeout_values)),
            "missing_cells": len(missing),
            "complete_case_n": beam_n,
        },
        "alignment_inputs": [
            {
                "path": _relative(FINAL_ANALYSIS_MANIFEST),
                "sha256": _sha256(FINAL_ANALYSIS_MANIFEST),
                "generated_utc": manifest["generated_utc"],
            },
            {
                "path": _relative(FINAL_HEADLINE),
                "sha256": actual_headline_hash,
                "generated_utc": headline["generated_utc"] if "generated_utc" in headline else None,
            },
        ],
    }


def build_source() -> dict[str, Any]:
    comparisons: list[dict[str, Any]] = []
    input_files: list[dict[str, Any]] = []
    contracts: set[str] = set()
    database_hashes: set[str] = set()
    candidates: set[str] = set()
    experiments: set[str] = set()
    suites: set[str] = set()
    bootstrap_contracts: set[str] = set()
    required_seed_contracts: set[tuple[int, ...]] = set()

    for baseline_key, baseline_label, source_path in STAT_FILES:
        payload = _load_statistics(source_path)
        input_files.append(
            {
                "path": _relative(source_path),
                "sha256": _sha256(source_path),
                "generated_utc": payload["generated_utc"],
            }
        )
        contracts.add(str(payload["statistics"]["analysis_contract_sha256"]))
        database_hashes.add(str(payload["input"]["database_sha256_before"]))
        bootstrap_contracts.add(
            json.dumps(payload["statistics"]["bootstrap"], sort_keys=True, separators=(",", ":"))
        )
        required_seed_contracts.add(tuple(int(x) for x in payload["filters"]["required_seeds"]))

        expected_reference = payload["filters"]["reference_methods"]
        if expected_reference != [baseline_key]:
            raise ValueError(f"reference filter does not match filename contract: {source_path}")

        for metric_order, metric in enumerate(METRICS):
            row = _select_primary_row(payload, metric, source_path)
            strict, reason = _strict_status(row)
            candidates.add(str(row["candidate_method"]))
            experiments.add(str(row["experiment_slug"]))
            suites.add(str(row["suite"]))
            if row["reference_method"] != baseline_key:
                raise ValueError(f"selected summary reference mismatch: {source_path}:{metric['key']}")

            n = int(row["n_pairs"])
            wins = int(row["win_count"])
            ties = int(row["tie_count"])
            losses = int(row["loss_count"])
            if wins + ties + losses != n:
                raise ValueError(f"W/T/L does not sum to n: {source_path}:{metric['key']}")

            estimate = float(row["median_relative_improvement_pct"])
            ci_low = float(row["median_relative_improvement_pct_ci_low"])
            ci_high = float(row["median_relative_improvement_pct_ci_high"])
            if not ci_low <= estimate <= ci_high:
                raise ValueError(f"relative effect lies outside its CI: {source_path}:{metric['key']}")

            comparisons.append(
                {
                    "baseline_order": len(input_files) - 1,
                    "baseline_key": baseline_key,
                    "baseline_label": baseline_label,
                    "reference_method": row["reference_method"],
                    "candidate_method": row["candidate_method"],
                    "metric_order": metric_order,
                    "metric_key": metric["key"],
                    "metric_label": metric["label"],
                    "scope": metric["scope"],
                    "target_name": row.get("target_name"),
                    "transpile_spec_name": row.get("transpile_spec_name"),
                    "experiment_slug": row["experiment_slug"],
                    "suite": row["suite"],
                    "n_functions": n,
                    "required_seeds": json.loads(row["required_seeds_json"]),
                    "n_seed_pairs": int(row["n_seed_pairs"]),
                    "wins": wins,
                    "ties": ties,
                    "losses": losses,
                    "median_relative_improvement_pct": estimate,
                    "median_relative_improvement_pct_ci_low": ci_low,
                    "median_relative_improvement_pct_ci_high": ci_high,
                    "median_delta": float(row["median_delta"]),
                    "median_delta_ci_low": float(row["median_delta_ci_low"]),
                    "median_delta_ci_high": float(row["median_delta_ci_high"]),
                    "wilcoxon_p_raw": float(row["wilcoxon_p_raw"]),
                    "holm_family": row["holm_family"],
                    "holm_family_size": int(row["holm_family_size"]),
                    "holm_p_adjusted": float(row["holm_p_adjusted"]),
                    "holm_reject": bool(row["holm_reject"]),
                    "strict_supported": strict,
                    "strict_status_reason": reason,
                }
            )

    if len(comparisons) != len(STAT_FILES) * len(METRICS):
        raise ValueError("primary comparison grid is incomplete")
    if any(len(group) != 1 for group in (contracts, database_hashes, candidates, experiments, suites)):
        raise ValueError("frozen statistics do not share one analysis/database/candidate/experiment contract")
    if len(bootstrap_contracts) != 1 or len(required_seed_contracts) != 1:
        raise ValueError("bootstrap or required-seed contract differs between sources")

    # n must be stable across all four metrics within a baseline, while allowing
    # SSHR-Beam's frozen complete-case boundary to differ from other baselines.
    for baseline_key, _, _ in STAT_FILES:
        n_values = {row["n_functions"] for row in comparisons if row["baseline_key"] == baseline_key}
        if len(n_values) != 1:
            raise ValueError(f"n differs across primary metrics for {baseline_key}")

    bootstrap = json.loads(next(iter(bootstrap_contracts)))
    required_seeds = list(next(iter(required_seed_contracts)))
    analysis_contract_sha256 = next(iter(contracts))
    database_sha256 = next(iter(database_hashes))
    final_alignment = _load_final_alignment(
        comparisons,
        analysis_contract_sha256=analysis_contract_sha256,
        database_sha256=database_sha256,
        required_seeds=required_seeds,
    )
    input_files.extend(final_alignment.pop("alignment_inputs"))
    return {
        "schema_version": 1,
        "figure_id": STEM,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_method": next(iter(candidates)),
        "experiment_slug": next(iter(experiments)),
        "suite": next(iter(suites)),
        "database_sha256": database_sha256,
        "analysis_contract_sha256": analysis_contract_sha256,
        "input_files": input_files,
        "final_analysis_alignment": final_alignment,
        "statistics": {
            "inference_unit": "independent Boolean function",
            "required_seeds": required_seeds,
            "within_function_aggregation": "median of strictly paired seed results",
            "displayed_effect": "median 100*(baseline-candidate)/abs(baseline); positive favours candidate",
            "displayed_interval": bootstrap,
            "test": "paired two-sided Wilcoxon signed-rank",
            "multiplicity": "Holm step-down within frozen logical-primary or mapping-primary family",
            "strict_gate": (
                "holm_reject == true and median_delta_ci_high < 0 and "
                "median_relative_improvement_pct_ci_low > 0; zero-touching is not strict"
            ),
            "delta_definition": "candidate - baseline; negative favours candidate",
        },
        "baselines": [
            {
                "key": key,
                "label": label,
                "n_functions": next(
                    row["n_functions"] for row in comparisons if row["baseline_key"] == key
                ),
                "strict_supported_metric_count": sum(
                    bool(row["strict_supported"])
                    for row in comparisons
                    if row["baseline_key"] == key
                ),
            }
            for key, label, _ in STAT_FILES
        ],
        "metrics": list(METRICS),
        "comparisons": comparisons,
    }


CSV_FIELDS = (
    "baseline_order",
    "baseline_key",
    "baseline_label",
    "reference_method",
    "candidate_method",
    "metric_order",
    "metric_key",
    "metric_label",
    "scope",
    "target_name",
    "transpile_spec_name",
    "experiment_slug",
    "suite",
    "n_functions",
    "required_seeds",
    "n_seed_pairs",
    "wins",
    "ties",
    "losses",
    "median_relative_improvement_pct",
    "median_relative_improvement_pct_ci_low",
    "median_relative_improvement_pct_ci_high",
    "median_delta",
    "median_delta_ci_low",
    "median_delta_ci_high",
    "wilcoxon_p_raw",
    "holm_family",
    "holm_family_size",
    "holm_p_adjusted",
    "holm_reject",
    "strict_supported",
    "strict_status_reason",
)


def write_source(source: Mapping[str, Any]) -> None:
    SOURCE_JSON.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    with SOURCE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in source["comparisons"]:
            export = dict(row)
            export["required_seeds"] = json.dumps(export["required_seeds"], separators=(",", ":"))
            writer.writerow({field: export.get(field) for field in CSV_FIELDS})


def _comparison_map(source: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(row["baseline_key"]), str(row["metric_key"])): row
        for row in source["comparisons"]
    }


def _axis_limits(source: Mapping[str, Any]) -> tuple[float, float, list[float]]:
    values = [
        float(row[field])
        for row in source["comparisons"]
        for field in (
            "median_relative_improvement_pct_ci_low",
            "median_relative_improvement_pct_ci_high",
        )
    ]
    lower = min(min(values), 0.0)
    upper = max(max(values), 0.0)
    pad = max(5.0, 0.055 * (upper - lower))
    lo = math.floor((lower - pad) / 10.0) * 10.0
    hi = math.ceil((upper + pad) / 10.0) * 10.0
    tick_step = 50.0 if hi - lo > 120 else 40.0
    first_tick = math.ceil(lo / tick_step) * tick_step
    ticks = []
    value = first_tick
    while value <= hi + 1e-9:
        ticks.append(value)
        value += tick_step
    if 0.0 not in ticks:
        ticks.append(0.0)
        ticks.sort()
    return lo, hi, ticks


def _format_p(value: float) -> str:
    if value < 0.01:
        return f"{value:.2e}".replace("e-0", "e-").replace("e+0", "e+")
    return f"{value:.3f}"


def _paired_seed_and_beam_note(source: Mapping[str, Any]) -> tuple[str, str]:
    seeds = [int(value) for value in source["statistics"]["required_seeds"]]
    seed_text = ", ".join(str(value) for value in seeds)
    boundary = source["final_analysis_alignment"]["coverage_boundary"]
    seed_note = f"{len(seeds)} strictly paired seeds per function ({seed_text})"
    beam_note = (
        f"for SSHR-Beam, all {boundary['seeds_per_case']} seeds for "
        f"{boundary['case_count']} AES functions hit the {boundary['timeout_seconds']} s "
        f"synthesis timeout; hence n={boundary['complete_case_n']}"
    )
    return seed_note, beam_note


def _draw_effect_grid(fig: plt.Figure, cell: Any, source: Mapping[str, Any]) -> None:
    lookup = _comparison_map(source)
    subgrid = cell.subgridspec(1, len(METRICS), wspace=0.13)
    axes = [fig.add_subplot(subgrid[0, index]) for index in range(len(METRICS))]
    lo, hi, ticks = _axis_limits(source)
    baselines = source["baselines"]
    y_positions = list(range(len(baselines)))[::-1]

    for metric_index, (metric, ax) in enumerate(zip(METRICS, axes)):
        for row_index, (baseline, y) in enumerate(zip(baselines, y_positions)):
            row = lookup[(baseline["key"], metric["key"])]
            estimate = float(row["median_relative_improvement_pct"])
            ci_low = float(row["median_relative_improvement_pct_ci_low"])
            ci_high = float(row["median_relative_improvement_pct_ci_high"])
            strict = bool(row["strict_supported"])
            color = SIGNAL if strict else NEUTRAL
            marker_face = SIGNAL if strict else WHITE
            ax.errorbar(
                estimate,
                y,
                xerr=[[estimate - ci_low], [ci_high - estimate]],
                fmt="o",
                ms=4.8,
                mfc=marker_face,
                mec=color,
                mew=1.0,
                ecolor=color,
                elinewidth=1.25 if strict else 0.95,
                capsize=2.2,
                capthick=1.0,
                zorder=4,
            )
            span = hi - lo
            if estimate > hi - 0.19 * span:
                text_x, ha = estimate - 0.035 * span, "right"
            else:
                text_x, ha = estimate + 0.035 * span, "left"
            ax.text(
                text_x,
                y + 0.19,
                f"{estimate:+.1f}",
                ha=ha,
                va="bottom",
                fontsize=5.3,
                color=SIGNAL_DARK if strict else MUTED,
                fontweight="bold" if strict else "normal",
                zorder=5,
            )

        ax.axvline(0.0, color=ZERO, linestyle=(0, (2.4, 2.0)), linewidth=0.9, zorder=2)
        ax.set_xlim(lo, hi)
        ax.set_ylim(-0.55, len(baselines) - 0.30)
        ax.set_xticks(ticks)
        ax.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.85, zorder=0)
        ax.set_title(f"{metric['label']}\n({metric['scope']})", pad=4.0, fontweight="bold", color=INK)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        if metric_index == 0:
            ax.set_yticks(y_positions)
            ax.set_yticklabels(
                [f"{item['label']}  (n={item['n_functions']})" for item in baselines],
                color=INK,
            )
        else:
            ax.set_yticks(y_positions)
            ax.set_yticklabels([])

    fig.text(0.015, 0.975, "a", fontsize=8.5, fontweight="bold", color=INK, va="top")
    fig.text(
        0.185,
        0.975,
        "Function-level median relative improvement with 95% bootstrap CI",
        fontsize=7.2,
        fontweight="bold",
        color=INK,
        va="top",
    )
    fig.text(
        0.985,
        0.975,
        "positive favours Resource-NMCTS",
        fontsize=5.8,
        color=MUTED,
        ha="right",
        va="top",
    )
    fig.text(
        0.585,
        0.493,
        "Resource-NMCTS improvement over baseline (%)",
        fontsize=6.2,
        color=INK,
        ha="center",
        va="center",
    )


def _draw_audit_matrix(fig: plt.Figure, cell: Any, source: Mapping[str, Any]) -> None:
    ax = fig.add_subplot(cell)
    lookup = _comparison_map(source)
    baselines = source["baselines"]
    ax.set_xlim(-0.02, len(METRICS) + 0.02)
    ax.set_ylim(-0.05, len(baselines) + 0.10)
    ax.set_axis_off()

    for row_index, baseline in enumerate(baselines):
        y = len(baselines) - 1 - row_index
        ax.text(
            -0.08,
            y + 0.5,
            f"{baseline['label']}\n(n={baseline['n_functions']})",
            transform=ax.transData,
            ha="right",
            va="center",
            fontsize=5.8,
            color=INK,
            clip_on=False,
        )
        for metric_index, metric in enumerate(METRICS):
            row = lookup[(baseline["key"], metric["key"])]
            strict = bool(row["strict_supported"])
            x = metric_index
            rect = Rectangle(
                (x + 0.035, y + 0.08),
                0.93,
                0.82,
                facecolor=SIGNAL_LIGHT if strict else NEUTRAL_LIGHT,
                edgecolor=SIGNAL if strict else GRID,
                linewidth=1.05 if strict else 0.65,
                zorder=1,
            )
            ax.add_patch(rect)
            marker = "●" if strict else "○"
            status = "strict" if strict else "neutral"
            ax.text(
                x + 0.50,
                y + 0.72,
                f"{marker} {status}",
                ha="center",
                va="center",
                fontsize=5.1,
                color=SIGNAL_DARK if strict else MUTED,
                fontweight="bold" if strict else "normal",
                zorder=2,
            )
            ax.text(
                x + 0.50,
                y + 0.48,
                f"W/T/L  {row['wins']}/{row['ties']}/{row['losses']}",
                ha="center",
                va="center",
                fontsize=5.45,
                color=INK,
                zorder=2,
            )
            ax.text(
                x + 0.50,
                y + 0.25,
                f"pH  {_format_p(float(row['holm_p_adjusted']))}",
                ha="center",
                va="center",
                fontsize=5.25,
                color=SIGNAL_DARK if strict else MUTED,
                zorder=2,
            )

    for metric_index, metric in enumerate(METRICS):
        ax.text(
            metric_index + 0.50,
            len(baselines) + 0.02,
            metric["label"],
            ha="center",
            va="bottom",
            fontsize=6.1,
            color=INK,
            fontweight="bold",
        )

    fig.text(0.015, 0.442, "b", fontsize=8.5, fontweight="bold", color=INK, va="top")
    fig.text(
        0.185,
        0.442,
        "Inferential audit: W/T/L and family-Holm p",
        fontsize=7.2,
        fontweight="bold",
        color=INK,
        va="top",
    )


def draw_figure(source: Mapping[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_MM * MM, HEIGHT_MM * MM))
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=[0.54, 0.46],
        left=0.185,
        right=0.985,
        top=0.855,
        bottom=0.125,
        hspace=0.63,
    )
    _draw_effect_grid(fig, grid[0, 0], source)
    _draw_audit_matrix(fig, grid[1, 0], source)

    strict_handle = Line2D(
        [0],
        [0],
        marker="o",
        color=SIGNAL,
        markerfacecolor=SIGNAL,
        markeredgecolor=SIGNAL,
        linewidth=1.2,
        markersize=4.8,
        label="strict support",
    )
    neutral_handle = Line2D(
        [0],
        [0],
        marker="o",
        color=NEUTRAL,
        markerfacecolor=WHITE,
        markeredgecolor=NEUTRAL,
        linewidth=1.0,
        markersize=4.8,
        label="touches/crosses zero or Holm not rejected",
    )
    fig.legend(
        handles=[strict_handle, neutral_handle],
        loc="upper left",
        bbox_to_anchor=(0.18, 0.938),
        ncol=2,
        frameon=False,
        handlelength=1.6,
        columnspacing=1.3,
        borderaxespad=0.0,
    )

    seed_note, beam_note = _paired_seed_and_beam_note(source)

    fig.text(
        0.185,
        0.075,
        "Strict gate: family-Holm reject AND raw median Δ 95% CI upper<0 AND median relative-improvement 95% CI lower>0 (zero-touching is neutral).",
        fontsize=5.15,
        color=INK,
        ha="left",
        va="bottom",
    )
    fig.text(
        0.185,
        0.043,
        f"{seed_note}; {beam_note}. pH = family-Holm adjusted p.",
        fontsize=5.10,
        color=MUTED,
        ha="left",
        va="bottom",
    )
    return fig


def _save_figure(fig: plt.Figure) -> list[Path]:
    outputs: list[Path] = []
    for suffix in ("svg", "pdf", "png"):
        path = OUTDIR / f"{STEM}.{suffix}"
        kwargs: dict[str, Any] = {"metadata": {"Creator": "Python/matplotlib"}}
        if suffix == "png":
            kwargs["dpi"] = PNG_DPI
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)

    with Image.open(OUTDIR / f"{STEM}.png") as image:
        preview_height = round(image.height * PREVIEW_WIDTH_PX / image.width)
        preview = image.resize((PREVIEW_WIDTH_PX, preview_height), Image.Resampling.LANCZOS)
        preview.save(QA_PREVIEW, format="PNG", dpi=(200, 200), optimize=True)
    outputs.append(QA_PREVIEW)
    return outputs


def _qa_outputs(outputs: Iterable[Path], source: Mapping[str, Any]) -> dict[str, Any]:
    by_name = {path.name: path for path in outputs}
    svg_path = by_name[f"{STEM}.svg"]
    pdf_path = by_name[f"{STEM}.pdf"]
    png_path = by_name[f"{STEM}.png"]
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_images = len(re.findall(r"<image\b", svg_text))
    svg_text_nodes = len(re.findall(r"<text\b", svg_text))

    import fitz  # PyMuPDF; Python-only export QA.

    with fitz.open(pdf_path) as document:
        page_count = len(document)
        if page_count != 1:
            raise ValueError("F4 PDF must contain exactly one page")
        page = document[0]
        rect = page.rect
        pdf_width_mm = rect.width * 25.4 / 72.0
        pdf_height_mm = rect.height * 25.4 / 72.0
        pdf_text_characters = len(page.get_text("text").strip())

    with Image.open(png_path) as image:
        png_pixels = list(image.size)
        png_dpi_values = image.info.get("dpi", (None, None))
        png_dpi = [round(float(value), 3) if value is not None else None for value in png_dpi_values]
    with Image.open(QA_PREVIEW) as preview:
        preview_pixels = list(preview.size)

    expected_pixels = [round(WIDTH_MM * PNG_DPI / 25.4), round(HEIGHT_MM * PNG_DPI / 25.4)]
    lo, hi, _ = _axis_limits(source)
    ci_bounds_within_axes = all(
        lo <= float(row["median_relative_improvement_pct_ci_low"])
        and float(row["median_relative_improvement_pct_ci_high"]) <= hi
        for row in source["comparisons"]
    )
    strict_count = sum(bool(row["strict_supported"]) for row in source["comparisons"])
    strict_gate_recomputed_pass = all(
        bool(row["strict_supported"])
        == (
            bool(row["holm_reject"])
            and float(row["median_delta_ci_high"]) < 0.0
            and float(row["median_relative_improvement_pct_ci_low"]) > 0.0
        )
        for row in source["comparisons"]
    )
    zero_touching_neutral_pass = all(
        not bool(row["strict_supported"])
        for row in source["comparisons"]
        if math.isclose(float(row["median_delta_ci_high"]), 0.0, abs_tol=1e-12)
        or math.isclose(
            float(row["median_relative_improvement_pct_ci_low"]), 0.0, abs_tol=1e-12
        )
    )
    final_strict_count = int(
        source["final_analysis_alignment"]["strict_significant_better_count"]
    )

    qa = {
        "backend_exclusivity": "Python/matplotlib for figure and exports; Pillow for same-backend preview",
        "source": {
            "comparison_rows": len(source["comparisons"]),
            "expected_comparison_rows": len(STAT_FILES) * len(METRICS),
            "complete_grid_pass": len(source["comparisons"]) == len(STAT_FILES) * len(METRICS),
            "strict_supported_cells": strict_count,
            "neutral_cells": len(source["comparisons"]) - strict_count,
            "strict_gate_recomputed_pass": strict_gate_recomputed_pass,
            "zero_touching_neutral_pass": zero_touching_neutral_pass,
            "final_analysis_strict_count": final_strict_count,
            "final_analysis_alignment_pass": strict_count == final_strict_count,
            "final_analysis_id": source["final_analysis_alignment"]["analysis_id"],
            "all_ci_bounds_visible_pass": ci_bounds_within_axes,
            "common_x_limits_pct": [lo, hi],
        },
        "svg": {
            "embedded_image_elements": svg_images,
            "text_elements": svg_text_nodes,
            "editable_text_pass": svg_images == 0 and svg_text_nodes > 0,
        },
        "pdf": {
            "pages": page_count,
            "width_mm": pdf_width_mm,
            "height_mm": pdf_height_mm,
            "text_characters_extracted": pdf_text_characters,
            "single_page_pass": page_count == 1,
            "declared_size_pass": abs(pdf_width_mm - WIDTH_MM) < 0.2
            and abs(pdf_height_mm - HEIGHT_MM) < 0.2,
            "extractable_text_pass": pdf_text_characters > 100,
        },
        "png": {
            "pixels": png_pixels,
            "dpi_metadata": png_dpi,
            "expected_pixels_at_600dpi": expected_pixels,
            "dimensions_pass": all(abs(a - b) <= 2 for a, b in zip(png_pixels, expected_pixels)),
            "dpi_metadata_pass": all(value is not None and abs(value - PNG_DPI) < 1.0 for value in png_dpi),
        },
        "preview": {
            "pixels": preview_pixels,
            "width_contract_pass": preview_pixels[0] == PREVIEW_WIDTH_PX,
        },
    }
    required_passes = (
        qa["source"]["complete_grid_pass"],
        qa["source"]["strict_gate_recomputed_pass"],
        qa["source"]["zero_touching_neutral_pass"],
        qa["source"]["final_analysis_alignment_pass"],
        qa["source"]["all_ci_bounds_visible_pass"],
        qa["svg"]["editable_text_pass"],
        qa["pdf"]["single_page_pass"],
        qa["pdf"]["declared_size_pass"],
        qa["pdf"]["extractable_text_pass"],
        qa["png"]["dimensions_pass"],
        qa["png"]["dpi_metadata_pass"],
        qa["preview"]["width_contract_pass"],
    )
    if not all(required_passes):
        raise ValueError(f"F4 automated QA failed: {json.dumps(qa, ensure_ascii=False)}")
    return qa


def write_qa_notes(
    qa: Mapping[str, Any], source: Mapping[str, Any], visual_qa_pass: bool
) -> None:
    status = "PASS" if visual_qa_pass else "PENDING MANUAL VISUAL REVIEW"
    _, beam_note = _paired_seed_and_beam_note(source)
    visual_lines = (
        "- PASS — all four metric columns and all five baseline rows are legible at the declared 183 mm width.\n"
        "- PASS — no point estimate, confidence interval, W/T/L field, p-value or footer overlaps another element.\n"
        "- PASS — filled strict and hollow neutral markers remain distinguishable without relying on colour.\n"
        f"- PASS — the documented timeout boundary ({beam_note}) and three-part strict-gate definition are visible in the figure."
        if visual_qa_pass
        else "- Pending — inspect `_qa_f4_preview.png` before recording the final visual pass."
    )
    notes = f"""# F4 primary-results figure QA

## Status

{status}

## Automated export checks

- PASS — source grid: {qa['source']['comparison_rows']}/{qa['source']['expected_comparison_rows']} comparison cells.
- PASS — SVG: {qa['svg']['text_elements']} editable text nodes and {qa['svg']['embedded_image_elements']} embedded raster images.
- PASS — PDF: {qa['pdf']['pages']} page, {qa['pdf']['width_mm']:.3f} × {qa['pdf']['height_mm']:.3f} mm, extractable text present.
- PASS — PNG: {qa['png']['pixels'][0]} × {qa['png']['pixels'][1]} px at {qa['png']['dpi_metadata'][0]:.3f} dpi metadata.
- PASS — every displayed relative-effect confidence interval lies inside the common x-axis limits {qa['source']['common_x_limits_pct']}%.
- PASS — strict/neutral classification was recomputed with all three conditions (family-Holm rejection, raw median-delta CI upper < 0, relative-improvement CI lower > 0); zero-touching remains neutral.
- PASS — the recomputed {qa['source']['strict_supported_cells']} strict and {qa['source']['neutral_cells']} neutral cells match final analysis `{qa['source']['final_analysis_id']}`.

## Manual visual inspection

{visual_lines}

## Integrity boundary

The SVG/PDF are authoritative programmatic vector outputs. The PNG and QA preview are rasterizations of the same matplotlib figure. No source statistic, database record or manuscript file is modified by the generator.
"""
    QA_NOTES.write_text(notes, encoding="utf-8")


def write_manifest(
    source: Mapping[str, Any],
    outputs: Sequence[Path],
    qa: Mapping[str, Any],
    visual_qa_pass: bool,
) -> None:
    manifest = {
        "schema_version": 1,
        "figure_id": STEM,
        "purpose": "XA-202609 frozen primary20 function-level resource comparison",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contract": _relative(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "generator": _relative(Path(__file__)),
        "generator_sha256": _sha256(Path(__file__)),
        "backend": "Python/matplotlib only",
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "dimensions_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "font_policy": {
            "requested_fallback": FONT_FALLBACK,
            "resolved_primary": RESOLVED_FONT,
            "minimum_displayed_text_pt": 5.1,
            "svg_fonttype": "none",
            "pdf_fonttype": 42,
        },
        "frozen_inputs": source["input_files"],
        "database_sha256": source["database_sha256"],
        "analysis_contract_sha256": source["analysis_contract_sha256"],
        "final_analysis_id": source["final_analysis_alignment"]["analysis_id"],
        "final_analysis_payload_sha256": source["final_analysis_alignment"][
            "analysis_payload_sha256"
        ],
        "strict_gate": source["statistics"]["strict_gate"],
        "strict_significant_better_count": source["final_analysis_alignment"][
            "strict_significant_better_count"
        ],
        "sshr_beam_coverage_boundary": source["final_analysis_alignment"][
            "coverage_boundary"
        ],
        "source_data": [_relative(SOURCE_CSV), _relative(SOURCE_JSON)],
        "source_data_sha256": {
            _relative(SOURCE_CSV): _sha256(SOURCE_CSV),
            _relative(SOURCE_JSON): _sha256(SOURCE_JSON),
        },
        "qa_notes": _relative(QA_NOTES),
        "qa_notes_sha256": _sha256(QA_NOTES),
        "manual_visual_qa_pass": visual_qa_pass,
        "outputs": [
            {"path": _relative(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size}
            for path in outputs
        ],
        "qa": qa,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--visual-qa-pass",
        action="store_true",
        help="record the manual visual inspection as passed after reviewing the generated preview",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    source = build_source()
    write_source(source)
    figure = draw_figure(source)
    outputs = _save_figure(figure)
    qa = _qa_outputs(outputs, source)
    write_qa_notes(qa, source, visual_qa_pass=args.visual_qa_pass)
    write_manifest(source, outputs, qa, visual_qa_pass=args.visual_qa_pass)
    print(
        json.dumps(
            {
                "figure": STEM,
                "outputs": [_relative(path) for path in outputs],
                "source_csv": _relative(SOURCE_CSV),
                "source_json": _relative(SOURCE_JSON),
                "manifest": _relative(MANIFEST_PATH),
                "qa_notes": _relative(QA_NOTES),
                "manual_visual_qa_pass": args.visual_qa_pass,
                "qa": qa,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
