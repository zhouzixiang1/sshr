#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the traceable XA-202609 AI ablation and attribution-boundary figure.

This figure intentionally reports a bounded negative result.  It separates
matched learned-prior ablations from portfolio-level branch selection and does
not treat training loss as a downstream circuit-resource result.

Run from ``resource_nmcts/`` with the ``mcts-qoracle`` Python interpreter.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image
from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "submission_competition" / "figures"
STEM = "F3_ai_ablation_attribution"
SOURCE_JSON = OUTDIR / "ai_ablation_figure_source.json"
SOURCE_CSV = OUTDIR / "ai_ablation_figure_source.csv"
MANIFEST_PATH = OUTDIR / "ai_ablation_figure_manifest.json"
CONTRACT_PATH = OUTDIR / "FIGURE_CONTRACT_AI_ABLATION.md"
TRAINING_MANIFEST = ROOT / "submission_competition" / "training_manifest_competition.json"
MODEL_PATH = ROOT / "models" / "action_scorer_competition.pt"

WIDTH_MM = 183.0
HEIGHT_MM = 112.0
MM = 1.0 / 25.4

# Restrained, print-safe semantics.  Color is backed by hatching and direct
# labels, so the conclusion remains readable in greyscale.
INK = "#172532"
MUTED = "#5F6D79"
BLUE = "#175AA6"
BLUE_DARK = "#124478"
BLUE_LIGHT = "#EAF2FA"
TEAL = "#2A7C5F"
TEAL_LIGHT = "#EAF5EF"
AMBER = "#B56A1F"
AMBER_LIGHT = "#FFF3E4"
RED = "#A44B43"
RED_LIGHT = "#F8ECEA"
GREY = "#74818C"
GREY_LIGHT = "#E3E8EC"
PANEL = "#FBFCFD"
GRID = "#CAD3DA"
WHITE = "#FFFFFF"

PILOT_FILES: Mapping[str, Path] = {
    "heuristic": ROOT / "results" / "pilot_ai_heuristic_v1.jsonl",
    "learned": ROOT / "results" / "pilot_ai_learned_v1.jsonl",
    "rollout": ROOT / "results" / "pilot_ai_rollout_v1.jsonl",
    "uniform": ROOT / "results" / "pilot_ai_uniform_v1.jsonl",
    "random": ROOT / "results" / "pilot_ai_random_v1.jsonl",
}

HARD_FILES: Mapping[str, Path] = {
    "heuristic": ROOT / "results" / "ai_hard_heuristic_v1.jsonl",
    "immediate": ROOT / "results" / "ai_hard_immediate_v1.jsonl",
    "rollout": ROOT / "results" / "ai_hard_rollout_v1.jsonl",
}

# Frozen attribution snapshot.  These immutable JSONLs reconstruct all 60
# verified primary20 Resource-NMCTS function × seed cells in the final audit.
ATTRIBUTION_FILES: tuple[Path, ...] = (
    ROOT / "results" / "recovered" / "final_core_aes_v1_ok.jsonl",
    ROOT / "results" / "recovered" / "final_core_random_anf_v1_ok.jsonl",
    ROOT / "results" / "recovered" / "final_core_random_truth_v1_ok.jsonl",
    ROOT / "results" / "recovered" / "final_core_structured_v1_ok.jsonl",
    ROOT / "results" / "recovered" / "recovery_aes_b0_s7_v2_ok.jsonl",
    ROOT / "results" / "recovery_primary20_randanf7_resource_v3.jsonl",
    ROOT / "results" / "recovery_primary20_randanf8_s173_resource_v3.jsonl",
    ROOT / "results" / "recovery_primary20_maj7_s7_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_maj7_s17_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_maj7_s29_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_thr6_t3_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_randtt6_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_aes_b0_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_aes_b7_s7_fast_v3.jsonl",
    ROOT / "results" / "recovery_primary20_aes_b7_s17_s29_fast_v3.jsonl",
)

PRIMARY20: tuple[str, ...] = (
    "and3",
    "and4",
    "parity4",
    "parity6",
    "maj3",
    "maj5",
    "maj7",
    "thr6_t3",
    "randtt4_s101",
    "randtt4_s103",
    "randtt4_s107",
    "randtt4_s109",
    "randtt5_s113",
    "randtt6_s139",
    "randanf6_s151",
    "randanf6_s157",
    "randanf7_s163",
    "randanf8_s173",
    "aes_sbox_b0",
    "aes_sbox_b7",
)

CONTROL_LABELS = {
    "heuristic": "heuristic prior",
    "uniform": "uniform prior",
    "rollout": "rollout scorer",
    "random": "random prior",
}

HARD_LABELS = {
    "immediate": "Immediate scorer",
    "rollout": "Rollout scorer",
}

METRIC_FIELDS = {
    "逻辑 T": "logic_T",
    "逻辑 CNOT": "logic_CNOT",
    "映射深度": "mapped_depth",
}

AI_POSSIBLE_SELECTED_METHODS = frozenset({"affine_nmcts"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _resolved_font() -> tuple[str, list[str]]:
    preferred = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for candidate in preferred:
        if candidate in installed:
            return candidate, preferred
    return "DejaVu Sans", preferred


RESOLVED_FONT, FONT_FALLBACK = _resolved_font()

# Nature-figure mandatory editable-font rules.  Keep every displayed label at
# 6 pt or above at the declared final size.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = FONT_FALLBACK
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams.update(
    {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 6.2,
        "axes.titlesize": 7.1,
        "axes.labelsize": 6.2,
        "xtick.labelsize": 6.0,
        "ytick.labelsize": 6.0,
        "legend.fontsize": 6.0,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    }
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"required evidence missing: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if row.get("status") != "ok":
                raise ValueError(f"non-ok row in locked figure evidence: {path}:{line_number}")
            rows.append(row)
    return rows


def _logical_cells(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    """Deduplicate map-many rows to one synthesis-level function×seed cell."""
    rows = _load_jsonl(path)
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["function_id"]), int(row["synthesis_seed"]))
        grouped.setdefault(key, []).append(row)

    cells: dict[tuple[str, int], dict[str, Any]] = {}
    fields = ("logic_T", "logic_CNOT", "logic_depth", "logic_gates", "selected_method")
    for key, variants in grouped.items():
        for field in fields:
            values = {json.dumps(item.get(field), sort_keys=True) for item in variants}
            if len(values) != 1:
                raise ValueError(f"map-many rows disagree on {field} for {path}:{key}")
        preferred = next((item for item in variants if item.get("target_name") == "cx_full"), variants[0])
        cells[key] = preferred
    return cells


def _wtl(candidate: Sequence[float], reference: Sequence[float]) -> dict[str, int]:
    if len(candidate) != len(reference):
        raise ValueError("paired vectors have different lengths")
    wins = ties = losses = 0
    for cand, ref in zip(candidate, reference):
        if cand < ref:
            wins += 1
        elif cand > ref:
            losses += 1
        else:
            ties += 1
    return {"wins": wins, "ties": ties, "losses": losses, "n": len(candidate)}


def _joint_dominance_wtl(
    candidate_rows: Sequence[Mapping[str, Any]],
    reference_rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> dict[str, int]:
    wins = ties = losses = tradeoffs = 0
    for cand, ref in zip(candidate_rows, reference_rows):
        deltas = [float(cand[field]) - float(ref[field]) for field in fields]
        if all(delta == 0 for delta in deltas):
            ties += 1
        elif all(delta <= 0 for delta in deltas) and any(delta < 0 for delta in deltas):
            wins += 1
        elif all(delta >= 0 for delta in deltas) and any(delta > 0 for delta in deltas):
            losses += 1
        else:
            tradeoffs += 1
    return {
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "tradeoffs": tradeoffs,
        "n": len(candidate_rows),
    }


def _paired_wilcoxon(candidate: Sequence[float], reference: Sequence[float]) -> dict[str, Any]:
    # The signed-rank test discards exact ties.  Defining the all-tie case as
    # p=1 makes the figure policy explicit and avoids SciPy's zero warning.
    deltas = [float(cand) - float(ref) for cand, ref in zip(candidate, reference)]
    nonzero = [value for value in deltas if value != 0.0]
    if not nonzero:
        return {"p_two_sided": 1.0, "nonzero_pairs": 0, "statistic": 0.0}
    result = wilcoxon(nonzero, alternative="two-sided", zero_method="wilcox", method="auto")
    return {
        "p_two_sided": float(result.pvalue),
        "nonzero_pairs": len(nonzero),
        "statistic": float(result.statistic),
    }


def _build_pilot_source() -> dict[str, Any]:
    cells = {name: _logical_cells(path) for name, path in PILOT_FILES.items()}
    learned_keys = sorted(cells["learned"])
    expected_keys = {
        (case_id, seed)
        for case_id in ("and4", "maj5", "randanf6_s151", "randtt4_s101")
        for seed in (7, 17)
    }
    if set(learned_keys) != expected_keys:
        raise ValueError(f"clean pilot keys drifted: {learned_keys}")
    if len(learned_keys) != 8:
        raise ValueError("clean pilot must contain exactly eight function×seed cells")

    comparisons: list[dict[str, Any]] = []
    learned_rows = [cells["learned"][key] for key in learned_keys]
    for control in ("heuristic", "uniform", "rollout", "random"):
        if set(cells[control]) != set(learned_keys):
            raise ValueError(f"pilot control is not matched: {control}")
        control_rows = [cells[control][key] for key in learned_keys]
        dominance = _joint_dominance_wtl(
            learned_rows,
            control_rows,
            fields=("logic_T", "logic_CNOT"),
        )
        if dominance["tradeoffs"]:
            raise ValueError(f"pilot joint comparison has unreported tradeoffs: {control}")

        learned_t = [float(row["logic_T"]) for row in learned_rows]
        control_t = [float(row["logic_T"]) for row in control_rows]
        learned_cnot = [float(row["logic_CNOT"]) for row in learned_rows]
        control_cnot = [float(row["logic_CNOT"]) for row in control_rows]
        runtime_ratio = statistics.median(
            float(cand["synth_time_s"]) / float(ref["synth_time_s"])
            for cand, ref in zip(learned_rows, control_rows)
        )
        comparisons.append(
            {
                "control": control,
                "control_label": CONTROL_LABELS[control],
                "pairing_unit": "Boolean function truth table × synthesis seed",
                "joint_metric": "Pareto dominance on logical T and logical CNOT (lower is better)",
                **dominance,
                "wilcoxon_T": _paired_wilcoxon(learned_t, control_t),
                "wilcoxon_CNOT": _paired_wilcoxon(learned_cnot, control_cnot),
                "median_runtime_ratio_learned_over_control": runtime_ratio,
            }
        )

    expected = {
        "heuristic": (0, 8, 0),
        "uniform": (0, 8, 0),
        "rollout": (0, 8, 0),
        "random": (2, 6, 0),
    }
    for item in comparisons:
        observed = (item["wins"], item["ties"], item["losses"])
        if observed != expected[item["control"]]:
            raise ValueError(f"pilot W/T/L drifted for {item['control']}: {observed}")
    random_row = next(item for item in comparisons if item["control"] == "random")
    if not math.isclose(random_row["wilcoxon_T"]["p_two_sided"], 0.5):
        raise ValueError("random-control T p-value drifted")
    if not math.isclose(random_row["wilcoxon_CNOT"]["p_two_sided"], 0.5):
        raise ValueError("random-control CNOT p-value drifted")

    return {
        "n_functions": 4,
        "seeds": [7, 17],
        "n_paired_cells": 8,
        "deduplication": "cx_full/cx_line map-many rows collapse to one synthesis-level cell",
        "comparisons": comparisons,
    }


def _build_hard_source() -> dict[str, Any]:
    rows = {name: _load_jsonl(path) for name, path in HARD_FILES.items()}
    keyed: dict[str, dict[str, dict[str, Any]]] = {}
    for name, items in rows.items():
        keyed[name] = {str(item["function_id"]): item for item in items}
        if len(keyed[name]) != len(items):
            raise ValueError(f"duplicate hard-case function rows: {name}")

    case_ids = ["maj7", "randtt6_s139", "aes_sbox_b0"]
    if any(set(keyed[name]) != set(case_ids) for name in keyed):
        raise ValueError("hard-case evidence is not matched across scorers")

    reference = keyed["heuristic"]
    variants: list[dict[str, Any]] = []
    for variant in ("immediate", "rollout"):
        metrics: list[dict[str, Any]] = []
        for metric_label, field in METRIC_FIELDS.items():
            candidate_values = [float(keyed[variant][case][field]) for case in case_ids]
            reference_values = [float(reference[case][field]) for case in case_ids]
            metrics.append(
                {
                    "metric": metric_label,
                    "field": field,
                    **_wtl(candidate_values, reference_values),
                }
            )
        runtime_ratio = statistics.median(
            float(keyed[variant][case]["synth_time_s"]) / float(reference[case]["synth_time_s"])
            for case in case_ids
        )
        variants.append(
            {
                "variant": variant,
                "variant_label": HARD_LABELS[variant],
                "reference": "heuristic prior",
                "n_cases": 3,
                "case_ids": case_ids,
                "metrics": metrics,
                "median_runtime_ratio_over_heuristic": runtime_ratio,
                "case_values": [
                    {
                        "case_id": case,
                        "candidate": {
                            label: keyed[variant][case][field] for label, field in METRIC_FIELDS.items()
                        },
                        "heuristic": {
                            label: reference[case][field] for label, field in METRIC_FIELDS.items()
                        },
                    }
                    for case in case_ids
                ],
            }
        )

    expected = {
        ("immediate", "逻辑 T"): (0, 2, 1),
        ("immediate", "逻辑 CNOT"): (0, 2, 1),
        ("immediate", "映射深度"): (1, 0, 2),
        ("rollout", "逻辑 T"): (1, 1, 1),
        ("rollout", "逻辑 CNOT"): (1, 1, 1),
        ("rollout", "映射深度"): (0, 0, 3),
    }
    for variant in variants:
        for metric in variant["metrics"]:
            observed = (metric["wins"], metric["ties"], metric["losses"])
            if observed != expected[(variant["variant"], metric["metric"])]:
                raise ValueError(
                    f"hard-case W/T/L drifted for {variant['variant']} {metric['metric']}: {observed}"
                )
    return {"variants": variants}


def _build_attribution_source() -> dict[str, Any]:
    primary = set(PRIMARY20)
    cells: dict[tuple[str, int], dict[str, Any]] = {}
    provenance: dict[tuple[str, int], list[str]] = {}
    for path in ATTRIBUTION_FILES:
        for row in _load_jsonl(path):
            if row.get("method") != "resource_nmcts":
                continue
            case_id = str(row["function_id"])
            seed = int(row["synthesis_seed"])
            if case_id not in primary or seed not in {7, 17, 29}:
                continue
            key = (case_id, seed)
            if key in cells:
                fields = ("selected_method", "logic_T", "logic_CNOT", "logic_depth")
                if any(cells[key].get(field) != row.get(field) for field in fields):
                    raise ValueError(f"conflicting Resource-NMCTS duplicate for {key}")
            else:
                cells[key] = row
            provenance.setdefault(key, []).append(_relative(path))

    selected_counts = Counter(str(row["selected_method"]) for row in cells.values())
    possible_ai = sum(
        count for method, count in selected_counts.items() if method in AI_POSSIBLE_SELECTED_METHODS
    )
    deterministic = len(cells) - possible_ai
    if (len(cells), deterministic, possible_ai) != (60, 54, 6):
        raise ValueError(
            "attribution snapshot drifted: "
            f"total={len(cells)}, deterministic={deterministic}, possible_ai={possible_ai}"
        )

    expected_counts = {
        "affine_greedy": 17,
        "fprm_greedy": 16,
        "direct_anf": 9,
        "fprm_linear_pair": 12,
        "affine_nmcts": 6,
    }
    if dict(selected_counts) != expected_counts:
        raise ValueError(f"selected_method counts drifted: {dict(selected_counts)}")

    return {
        "audit_unit": "unique verified primary20 Resource-NMCTS function×synthesis-seed cell",
        "seeds": [7, 17, 29],
        "total_verified_cells": len(cells),
        "deterministic_selected_cells": deterministic,
        "possible_ai_influence_cells": possible_ai,
        "deterministic_fraction": deterministic / len(cells),
        "possible_ai_fraction": possible_ai / len(cells),
        "possible_ai_rule": "selected_method == affine_nmcts; influence remains possible, not isolated",
        "selected_method_counts": dict(selected_counts),
        "cell_provenance": [
            {
                "function_id": case,
                "synthesis_seed": seed,
                "selected_method": cells[(case, seed)]["selected_method"],
                "attribution_class": (
                    "possible_ai_influence"
                    if cells[(case, seed)]["selected_method"] in AI_POSSIBLE_SELECTED_METHODS
                    else "explicitly_deterministic_selected_branch"
                ),
                "sources": provenance[(case, seed)],
            }
            for case, seed in sorted(cells)
        ],
    }


def _build_training_source() -> dict[str, Any]:
    if not TRAINING_MANIFEST.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError("training manifest or competition checkpoint is missing")
    manifest = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    model_sha = _sha256(MODEL_PATH)
    if model_sha != manifest["model"]["sha256"]:
        raise ValueError("competition checkpoint hash disagrees with training manifest")
    metadata = manifest["model"].get("metadata", {})
    architecture = metadata.get("architecture", {})
    hidden = int(architecture.get("hidden", 96))
    feature_dim = int(architecture.get("feature_dim", manifest["dataset"]["feature_dim"]))
    splits = manifest["dataset"]["splits"]
    return {
        "role": "supervised immediate-label action scorer; changes candidate ordering only",
        "architecture": f"{feature_dim}→{hidden}→{hidden}→{hidden}→1",
        "feature_dim": feature_dim,
        "hidden": hidden,
        "total_function_count": int(manifest["dataset"]["total_function_count"]),
        "total_action_row_count": int(manifest["dataset"]["total_row_count"]),
        "split_function_counts": {
            name: int(splits[name]["function_count"]) for name in ("train", "valid", "test")
        },
        "split_row_counts": {
            name: int(splits[name]["row_count"]) for name in ("train", "valid", "test")
        },
        "split_seed": int(manifest["dataset"]["split_seed"]),
        "normalization_source": manifest["normalization"]["source_split"],
        "training_seed": int(manifest["training"]["seed"]),
        "label_mode": manifest["training"]["label_mode"],
        "loss_mode": manifest["training"]["loss_mode"],
        "checkpoint_selection": manifest["training"]["checkpoint_selection"],
        "best_epoch": int(manifest["training"]["best_epoch"]),
        "test_loss_once_after_selection": float(manifest["metrics"]["test_loss_once_after_selection"]),
        "checkpoint_sha256": model_sha,
        "checkpoint_sha12": model_sha[:12],
        "training_device": manifest["runtime"]["training_device"],
        "cuda_device_name": manifest["runtime"]["cuda_device_name"],
        "torch_version": manifest["runtime"]["torch_version"],
        "torch_cuda_version": manifest["runtime"]["torch_cuda_version"],
        "integrity": {
            key: manifest["integrity"][key]
            for key in (
                "function_hash_splits_disjoint",
                "all_action_rows_assigned_once",
                "normalization_source_is_train_only",
                "checkpoint_uses_test",
                "test_evaluations",
            )
        },
        "claim_boundary": "offline regression MSE is not a downstream circuit-resource effect",
    }


def build_source() -> dict[str, Any]:
    input_paths = (
        [TRAINING_MANIFEST, MODEL_PATH, CONTRACT_PATH]
        + list(PILOT_FILES.values())
        + list(HARD_FILES.values())
        + list(ATTRIBUTION_FILES)
    )
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"figure input missing: {path}")

    source = {
        "schema_version": 1,
        "figure_id": STEM,
        "competition": "XA-202609",
        "core_conclusion": (
            "The current matched evidence does not isolate a stable circuit-resource gain from the "
            "learned prior: clean pilot controls are mostly tied, hard cases are mixed or adverse, "
            "and 54/60 verified Resource-NMCTS outcomes select explicitly deterministic branches."
        ),
        "archetype": "quantitative grid",
        "dimensions_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "panel_a_training_fact": _build_training_source(),
        "panel_b_clean_pilot": _build_pilot_source(),
        "panel_c_hard_cases": _build_hard_source(),
        "panel_d_portfolio_attribution": _build_attribution_source(),
        "statistics_policy": {
            "pairing_unit": "Boolean function truth table × synthesis seed",
            "lower_is_better": True,
            "pilot_joint_wtl": "Pareto dominance over logical T and logical CNOT",
            "hard_wtl": "per-metric paired comparison",
            "wilcoxon": "two-sided signed-rank after discarding exact-zero deltas",
            "all_tie_p_value": 1.0,
            "multiple_comparison_claim": "none; no significance claim is made",
        },
        "claim_policy": {
            "learned_prior_independent_gain_claimed": False,
            "training_loss_used_as_circuit_metric": False,
            "portfolio_gain_attributed_to_ai": False,
            "affine_nmcts_selected_cells_called_causal_ai_gain": False,
            "fitted_q_offline_result_included": False,
        },
        "evidence_files": [
            {
                "path": _relative(path),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in input_paths
        ],
    }
    SOURCE_JSON.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_source_csv(source)
    return source


def _write_source_csv(source: Mapping[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    training = source["panel_a_training_fact"]
    rows.extend(
        [
            {"panel": "a", "record_type": "training_fact", "label": "functions", "value": training["total_function_count"]},
            {"panel": "a", "record_type": "training_fact", "label": "action_rows", "value": training["total_action_row_count"]},
            {"panel": "a", "record_type": "training_fact", "label": "test_mse", "value": training["test_loss_once_after_selection"]},
            {"panel": "a", "record_type": "training_fact", "label": "checkpoint_sha12", "value": training["checkpoint_sha12"]},
        ]
    )
    for item in source["panel_b_clean_pilot"]["comparisons"]:
        rows.append(
            {
                "panel": "b",
                "record_type": "clean_pilot_joint_wtl",
                "label": item["control"],
                "metric": "logical_T_and_CNOT_Pareto",
                "wins": item["wins"],
                "ties": item["ties"],
                "losses": item["losses"],
                "n": item["n"],
                "p_T_two_sided": item["wilcoxon_T"]["p_two_sided"],
                "p_CNOT_two_sided": item["wilcoxon_CNOT"]["p_two_sided"],
                "runtime_ratio": item["median_runtime_ratio_learned_over_control"],
            }
        )
    for variant in source["panel_c_hard_cases"]["variants"]:
        for metric in variant["metrics"]:
            rows.append(
                {
                    "panel": "c",
                    "record_type": "hard3_metric_wtl",
                    "label": variant["variant"],
                    "metric": metric["metric"],
                    "wins": metric["wins"],
                    "ties": metric["ties"],
                    "losses": metric["losses"],
                    "n": metric["n"],
                    "runtime_ratio": variant["median_runtime_ratio_over_heuristic"],
                }
            )
    attribution = source["panel_d_portfolio_attribution"]
    for method, count in sorted(attribution["selected_method_counts"].items()):
        rows.append(
            {
                "panel": "d",
                "record_type": "selected_method_count",
                "label": method,
                "value": count,
                "n": attribution["total_verified_cells"],
                "attribution_class": (
                    "possible_ai_influence"
                    if method in AI_POSSIBLE_SELECTED_METHODS
                    else "explicitly_deterministic_selected_branch"
                ),
            }
        )

    fieldnames = sorted({key for row in rows for key in row})
    with SOURCE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.055,
        1.035,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.0,
        fontweight="bold",
        color=INK,
        clip_on=False,
    )


def _round_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    face: str = WHITE,
    edge: str = GRID,
    linewidth: float = 0.75,
    radius: float = 0.02,
    linestyle: str = "-",
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=face,
        edgecolor=edge,
        linewidth=linewidth,
        linestyle=linestyle,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def _draw_panel_a(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    ax.set_axis_off()
    split = source["split_function_counts"]
    _panel_label(ax, "a")
    ax.text(0.0, 0.995, "模型事实：监督排序器，而非正确性判定器", transform=ax.transAxes,
            fontsize=7.1, fontweight="bold", color=INK, va="top")

    # Compact, editable network schematic.
    xs = [0.06, 0.28, 0.49, 0.70, 0.92]
    labels = ["24", "96", "96", "96", "1"]
    for left, right in zip(xs[:-1], xs[1:]):
        ax.plot([left + 0.034, right - 0.034], [0.79, 0.79], transform=ax.transAxes,
                color=GRID, linewidth=1.0, zorder=1)
    for index, (x, label) in enumerate(zip(xs, labels)):
        face = BLUE if index in (0, 4) else BLUE_LIGHT
        edge = BLUE_DARK
        text_color = WHITE if index in (0, 4) else BLUE_DARK
        circle = plt.Circle((x, 0.79), 0.034, transform=ax.transAxes,
                            facecolor=face, edgecolor=edge, linewidth=0.8, zorder=2)
        ax.add_patch(circle)
        ax.text(x, 0.79, label, transform=ax.transAxes, ha="center", va="center",
                fontsize=6.2, fontweight="bold", color=text_color, zorder=3)
    ax.text(0.49, 0.875, source["architecture"], transform=ax.transAxes,
            ha="center", va="center", fontsize=6.2, color=BLUE_DARK)

    _round_box(ax, (0.0, 0.39), 0.48, 0.36, face=BLUE_LIGHT, edge=BLUE)
    ax.text(0.025, 0.70, "训练数据", transform=ax.transAxes, fontsize=6.4,
            fontweight="bold", color=BLUE_DARK, va="top")
    ax.text(0.025, 0.595, f"{source['total_action_row_count']:,} 动作行",
            transform=ax.transAxes, fontsize=6.1, color=INK, va="top")
    ax.text(0.025, 0.535, f"{source['total_function_count']:,} 个函数",
            transform=ax.transAxes, fontsize=6.1, color=INK, va="top")
    ax.text(0.025, 0.405, f"split {split['train']}/{split['valid']}/{split['test']}",
            transform=ax.transAxes, fontsize=6.0, color=MUTED, va="bottom")

    _round_box(ax, (0.52, 0.39), 0.48, 0.36, face=TEAL_LIGHT, edge=TEAL)
    ax.text(0.545, 0.70, "冻结检查点", transform=ax.transAxes, fontsize=6.4,
            fontweight="bold", color=TEAL, va="top")
    ax.text(0.545, 0.595, f"SHA-256 {source['checkpoint_sha12']}…",
            transform=ax.transAxes, fontsize=6.0, color=INK, va="top")
    ax.text(0.545, 0.535, f"RTX 5090 · CUDA {source['torch_cuda_version']}",
            transform=ax.transAxes, fontsize=6.0, color=INK, va="top")
    ax.text(0.545, 0.405, f"test MSE {source['test_loss_once_after_selection']:.2e}",
            transform=ax.transAxes, fontsize=6.0, color=MUTED, va="bottom")

    _round_box(ax, (0.0, 0.035), 1.0, 0.34, face=AMBER_LIGHT, edge=AMBER, linewidth=0.9)
    ax.text(0.03, 0.32, "证据边界", transform=ax.transAxes, fontsize=6.5,
            fontweight="bold", color=AMBER, va="top")
    ax.text(
        0.03,
        0.245,
        "immediate-label regression 只改变候选动作排序；",
        transform=ax.transAxes,
        fontsize=6.15,
        color=INK,
        va="top",
    )
    ax.text(0.03, 0.175, "训练/测试 MSE 不是线路 T、CNOT 或映射深度。",
            transform=ax.transAxes, fontsize=6.15, color=INK, va="top")
    ax.text(0.03, 0.07, "正确性仍由 GF(2)、线路与映射后精确验证给出。",
            transform=ax.transAxes, fontsize=6.0, color=AMBER, va="bottom")


def _stacked_wtl(
    ax: plt.Axes,
    y: float,
    wins: int,
    ties: int,
    losses: int,
    *,
    height: float,
) -> None:
    left = 0.0
    specs = (
        (wins, TEAL, "///", WHITE),
        (ties, GREY_LIGHT, "...", INK),
        (losses, RED, "xxx", WHITE),
    )
    for value, color, hatch, text_color in specs:
        if value <= 0:
            continue
        bars = ax.barh(y, value, left=left, height=height, color=color, edgecolor=WHITE,
                       linewidth=0.7, hatch=hatch, zorder=3)
        ax.text(left + value / 2.0, y, str(value), ha="center", va="center",
                fontsize=6.1, color=text_color, fontweight="bold", zorder=4)
        left += value


def _draw_panel_b(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    _panel_label(ax, "b")
    ax.set_title("干净 pilot：learned prior 未显示独立稳定收益", loc="left", pad=2,
                 fontweight="bold", color=INK)
    comparisons = source["comparisons"]
    y_positions = list(range(len(comparisons)))[::-1]
    for y, item in zip(y_positions, comparisons):
        _stacked_wtl(ax, y, item["wins"], item["ties"], item["losses"], height=0.54)
        p_t = item["wilcoxon_T"]["p_two_sided"]
        p_cnot = item["wilcoxon_CNOT"]["p_two_sided"]
        p_text = f"pT=pC={p_t:g}" if math.isclose(p_t, p_cnot) else f"pT={p_t:g}; pC={p_cnot:g}"
        ax.text(8.18, y, f"{item['wins']}/{item['ties']}/{item['losses']}",
                ha="left", va="center", fontsize=6.1, color=INK)
        ax.text(9.35, y, p_text, ha="left", va="center", fontsize=6.0, color=MUTED)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([item["control_label"] for item in comparisons])
    ax.set_xlim(0, 10.7)
    ax.set_ylim(-0.55, 3.72)
    ax.set_xticks([0, 2, 4, 6, 8])
    ax.set_xlabel("配对单元数（4 函数 × 2 seeds；逻辑 T/CNOT 联合支配）")
    ax.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.75, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.text(0.0, 0.985,
            "同一函数×seed 去重；绿/灰/红=胜/平/负；右列为 W/T/L 与双侧 Wilcoxon。",
            transform=ax.transAxes, fontsize=6.0, color=MUTED, va="top")


def _draw_panel_c(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    _panel_label(ax, "c")
    ax.set_title("hard3 反例：收益混合，映射深度可整体退化", loc="left", pad=2,
                 fontweight="bold", color=INK)
    rows: list[tuple[str, Mapping[str, Any], float]] = []
    for variant in source["variants"]:
        ratio = float(variant["median_runtime_ratio_over_heuristic"])
        for metric in variant["metrics"]:
            rows.append((variant["variant_label"], metric, ratio))
    y_positions = list(range(len(rows)))[::-1]
    for index, (y, (variant_label, metric, ratio)) in enumerate(zip(y_positions, rows)):
        if index < 3:
            ax.axhspan(y - 0.43, y + 0.43, color=BLUE_LIGHT, alpha=0.52, zorder=0)
        else:
            ax.axhspan(y - 0.43, y + 0.43, color=AMBER_LIGHT, alpha=0.52, zorder=0)
        _stacked_wtl(ax, y, metric["wins"], metric["ties"], metric["losses"], height=0.48)
        ax.text(3.13, y, f"{metric['wins']}/{metric['ties']}/{metric['losses']}",
                fontsize=6.0, color=INK, va="center", ha="left")
        if index in (0, 3):
            ax.text(4.13, y, f"中位耗时 {ratio:.1f}×", fontsize=6.0,
                    color=AMBER if ratio > 1 else TEAL, va="center", ha="left", fontweight="bold")
    ax.set_yticks(y_positions)
    ax.set_yticklabels([])
    short_variant = {"Immediate scorer": "I", "Rollout scorer": "R"}
    short_metric = {"逻辑 T": "T", "逻辑 CNOT": "CNOT", "映射深度": "映射深度"}
    for y, (variant, metric, _) in zip(y_positions, rows):
        ax.text(-0.08, y, f"{short_variant[variant]}·{short_metric[metric['metric']]}",
                fontsize=6.0, color=INK, va="center", ha="right")
    ax.set_xlim(-1.0, 5.6)
    ax.set_ylim(-0.55, 5.72)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("相对 heuristic prior 的配对单元数（n=3；胜/平/负）")
    ax.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.75, zorder=1)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.axhline(2.5, color=WHITE, linewidth=2.0, zorder=2)
    ax.text(0.0, 0.985, "I=immediate，R=rollout；maj7、randtt6_s139、AES-Sbox bit0；cx_full。",
            transform=ax.transAxes, fontsize=6.0, color=MUTED, va="top")


def _draw_panel_d(ax: plt.Axes, source: Mapping[str, Any]) -> None:
    ax.set_axis_off()
    _panel_label(ax, "d")
    ax.text(0.0, 1.015, "组合系统归因审计：大多数胜者是确定性分支", transform=ax.transAxes,
            fontsize=7.1, fontweight="bold", color=INK, va="bottom")

    total = int(source["total_verified_cells"])
    deterministic = int(source["deterministic_selected_cells"])
    possible = int(source["possible_ai_influence_cells"])
    det_frac = deterministic / total

    ax.text(0.03, 0.835, f"{deterministic}/{total}", transform=ax.transAxes,
            fontsize=13.0, fontweight="bold", color=BLUE_DARK, va="center")
    ax.text(0.03, 0.745, f"明确确定性 selected_method  ({100*det_frac:.1f}%)",
            transform=ax.transAxes, fontsize=6.2, color=BLUE_DARK, va="center")
    ax.text(0.72, 0.835, f"{possible}/{total}", transform=ax.transAxes,
            fontsize=13.0, fontweight="bold", color=AMBER, va="center")
    ax.text(0.72, 0.745, f"仅可能受 AI 影响  ({100*possible/total:.1f}%)",
            transform=ax.transAxes, fontsize=6.2, color=AMBER, va="center")

    x0, y0, width, height = 0.03, 0.58, 0.94, 0.105
    det_width = width * det_frac
    ax.add_patch(FancyBboxPatch((x0, y0), det_width, height,
                                boxstyle="round,pad=0.002,rounding_size=0.015",
                                transform=ax.transAxes, facecolor=BLUE_DARK,
                                edgecolor=WHITE, linewidth=0.8))
    ax.add_patch(FancyBboxPatch((x0 + det_width, y0), width - det_width, height,
                                boxstyle="round,pad=0.002,rounding_size=0.015",
                                transform=ax.transAxes, facecolor=AMBER_LIGHT,
                                edgecolor=AMBER, linewidth=1.0, hatch="///"))
    ax.text(x0 + det_width / 2, y0 + height / 2, f"{deterministic}",
            transform=ax.transAxes, ha="center", va="center", fontsize=7.0,
            color=WHITE, fontweight="bold")
    ax.text(x0 + det_width + (width - det_width) / 2, y0 + height / 2, "6",
            transform=ax.transAxes, ha="center", va="center", fontsize=6.4,
            color=AMBER, fontweight="bold")

    counts = source["selected_method_counts"]
    deterministic_text = (
        f"affine_greedy {counts['affine_greedy']}  ·  fprm_greedy {counts['fprm_greedy']}  ·  "
        f"Direct-ANF {counts['direct_anf']}  ·  fprm_linear_pair {counts['fprm_linear_pair']}"
    )
    ax.text(0.03, 0.515, deterministic_text, transform=ax.transAxes,
            fontsize=6.0, color=MUTED, va="top")
    ax.text(0.72, 0.465, f"affine_nmcts {counts['affine_nmcts']}", transform=ax.transAxes,
            fontsize=6.0, color=AMBER, va="top", fontweight="bold")

    _round_box(ax, (0.03, 0.055), 0.94, 0.34, face=AMBER_LIGHT, edge=AMBER, linewidth=0.9)
    ax.text(0.055, 0.345, "不能跨越的因果边界", transform=ax.transAxes,
            fontsize=6.5, color=AMBER, fontweight="bold", va="top")
    ax.text(0.055, 0.275, "selected_method 只说明最终分支；6 个 affine_nmcts 单元仍缺少",
            transform=ax.transAxes, fontsize=6.1, color=INK, va="top")
    ax.text(0.055, 0.205, "同预算 learned-off 配对，不能视作 6 个“AI 带来提升”的证据。",
            transform=ax.transAxes, fontsize=6.1, color=INK, va="top")
    ax.text(0.055, 0.095, "结论：Resource-NMCTS 的整体提升不得自动归因于 learned prior。",
            transform=ax.transAxes, fontsize=6.1, color=AMBER, va="bottom", fontweight="bold")


def draw_figure(source: Mapping[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_MM * MM, HEIGHT_MM * MM))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[0.42, 0.58],
        height_ratios=[0.46, 0.54],
        left=0.055,
        right=0.985,
        top=0.965,
        bottom=0.105,
        wspace=0.25,
        hspace=0.47,
    )
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])
    _draw_panel_a(ax_a, source["panel_a_training_fact"])
    _draw_panel_b(ax_b, source["panel_b_clean_pilot"])
    _draw_panel_c(ax_c, source["panel_c_hard_cases"])
    _draw_panel_d(ax_d, source["panel_d_portfolio_attribution"])
    return fig


def _save(fig: plt.Figure) -> list[Path]:
    outputs: list[Path] = []
    for suffix in ("svg", "pdf", "png"):
        path = OUTDIR / f"{STEM}.{suffix}"
        kwargs: dict[str, Any] = {}
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs


def _qa_outputs(outputs: Iterable[Path]) -> dict[str, Any]:
    by_suffix = {path.suffix.lower(): path for path in outputs}
    svg_text = by_suffix[".svg"].read_text(encoding="utf-8")
    image_elements = len(re.findall(r"<image\b", svg_text))
    text_elements = len(re.findall(r"<text\b", svg_text))

    import fitz  # PyMuPDF, used only for Python-backend export QA.

    with fitz.open(by_suffix[".pdf"]) as document:
        if len(document) != 1:
            raise ValueError("F3 PDF must contain exactly one page")
        rect = document[0].rect
        pdf_width_mm = rect.width * 25.4 / 72.0
        pdf_height_mm = rect.height * 25.4 / 72.0

    with Image.open(by_suffix[".png"]) as image:
        png_pixels = list(image.size)
        dpi = image.info.get("dpi", (None, None))
        png_dpi = [round(float(value), 3) if value is not None else None for value in dpi]

    qa = {
        "svg": {
            "embedded_image_elements": image_elements,
            "text_elements": text_elements,
            "editable_text_pass": image_elements == 0 and text_elements > 0,
        },
        "pdf": {
            "pages": 1,
            "width_mm": pdf_width_mm,
            "height_mm": pdf_height_mm,
            "single_page_pass": True,
            "declared_size_pass": (
                abs(pdf_width_mm - WIDTH_MM) < 0.2 and abs(pdf_height_mm - HEIGHT_MM) < 0.2
            ),
        },
        "png": {
            "pixels": png_pixels,
            "dpi_metadata": png_dpi,
            "expected_pixels_at_600dpi": [round(WIDTH_MM * 600 / 25.4), round(HEIGHT_MM * 600 / 25.4)],
            "preview_pass": (
                abs(png_pixels[0] - WIDTH_MM * 600 / 25.4) <= 2
                and abs(png_pixels[1] - HEIGHT_MM * 600 / 25.4) <= 2
            ),
        },
    }
    if not qa["svg"]["editable_text_pass"]:
        raise ValueError("SVG is not editable vector text")
    if not qa["pdf"]["declared_size_pass"]:
        raise ValueError("PDF dimensions drifted from the figure contract")
    if not qa["png"]["preview_pass"]:
        raise ValueError("PNG dimensions drifted from the 600 dpi export contract")
    return qa


def write_manifest(source: Mapping[str, Any], outputs: Sequence[Path], qa: Mapping[str, Any]) -> None:
    manifest = {
        "schema_version": 1,
        "figure_id": STEM,
        "purpose": "XA-202609 matched AI ablation and portfolio-attribution boundary",
        "contract": _relative(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "generator": _relative(Path(__file__)),
        "generator_sha256": _sha256(Path(__file__)),
        "source_data": [_relative(SOURCE_JSON), _relative(SOURCE_CSV)],
        "source_data_sha256": {
            _relative(SOURCE_JSON): _sha256(SOURCE_JSON),
            _relative(SOURCE_CSV): _sha256(SOURCE_CSV),
        },
        "backend": "Python/matplotlib only",
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "dimensions_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "font_policy": {
            "requested_fallback": FONT_FALLBACK,
            "resolved_primary": RESOLVED_FONT,
            "minimum_figure_label_pt": 6.0,
            "svg_fonttype": "none",
            "pdf_fonttype": 42,
        },
        "headline_values": {
            "clean_pilot_pairs": source["panel_b_clean_pilot"]["n_paired_cells"],
            "learned_vs_random_wtl": [2, 6, 0],
            "learned_vs_random_wilcoxon_p_T": 0.5,
            "learned_vs_random_wilcoxon_p_CNOT": 0.5,
            "resource_verified_cells": source["panel_d_portfolio_attribution"]["total_verified_cells"],
            "explicitly_deterministic_selected_cells": source["panel_d_portfolio_attribution"]["deterministic_selected_cells"],
            "possible_ai_influence_cells": source["panel_d_portfolio_attribution"]["possible_ai_influence_cells"],
        },
        "claim_policy": source["claim_policy"],
        "outputs": [
            {"path": _relative(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size}
            for path in outputs
        ],
        "qa": qa,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    source = build_source()
    fig = draw_figure(source)
    outputs = _save(fig)
    qa = _qa_outputs(outputs)
    write_manifest(source, outputs, qa)
    print(
        json.dumps(
            {
                "figure": STEM,
                "outputs": [_relative(path) for path in outputs],
                "source_json": _relative(SOURCE_JSON),
                "source_csv": _relative(SOURCE_CSV),
                "manifest": _relative(MANIFEST_PATH),
                "qa": qa,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
