#!/usr/bin/env python3
"""Train a tiny structure-level gate for high-dimensional Resource-NMCTS.

The gate learns when the adaptive Boolean-ring screen is sufficient and when
the expensive Resource-NMCTS tail is still needed.  It intentionally uses a
decision stump rather than a large model because the current labelled evidence
is small and should remain inspectable.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
MODELS = THIS_DIR / "models"
FEATURES = [
    "n",
    "anf_terms",
    "terms_per_var",
    "screen_score",
    "screen_T",
    "screen_CNOT",
    "screen_depth",
    "screen_peak_ancilla",
    "screen_vs_single_score_pct",
]


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def usable(row: dict[str, str]) -> bool:
    return not row.get("error") and not row.get("skipped") and row.get("correct") == "True"


def read_rows(path: Path) -> list[dict[str, str]]:
    raise_csv_field_limit()
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def by_method_name(rows: list[dict[str, str]], method: str) -> dict[str, dict[str, str]]:
    return {str(r["name"]): r for r in rows if r.get("method") == method and usable(r)}


def pct(target: float, baseline: float) -> float:
    return (target - baseline) / max(baseline, 1.0) * 100.0


def build_examples(
    inputs: list[Path],
    *,
    screen_method: str,
    resource_method: str,
    single_method: str,
    min_resource_gain_pct: float,
) -> list[dict[str, float | str | bool]]:
    examples: list[dict[str, float | str | bool]] = []
    seen: set[tuple[str, str]] = set()
    for path in inputs:
        rows = read_rows(path)
        screen = by_method_name(rows, screen_method)
        resource = by_method_name(rows, resource_method)
        single = by_method_name(rows, single_method)
        for name in sorted(set(screen) & set(resource) & set(single)):
            key = (str(path), name)
            if key in seen:
                continue
            seen.add(key)
            s = screen[name]
            r = resource[name]
            b = single[name]
            screen_score = float(s["score"])
            resource_score = float(r["score"])
            resource_gain_pct = pct(resource_score, screen_score)
            skip_resource = resource_gain_pct >= -abs(min_resource_gain_pct)
            n = float(s["n"])
            anf_terms = float(s["anf_terms"])
            examples.append(
                {
                    "source": str(path),
                    "name": name,
                    "skip_resource": skip_resource,
                    "resource_gain_pct": resource_gain_pct,
                    "n": n,
                    "anf_terms": anf_terms,
                    "terms_per_var": anf_terms / max(n, 1.0),
                    "screen_score": screen_score,
                    "screen_T": float(s["T"]),
                    "screen_CNOT": float(s["CNOT"]),
                    "screen_depth": float(s["depth"]),
                    "screen_peak_ancilla": float(s["peak_ancilla"]),
                    "screen_vs_single_score_pct": pct(screen_score, float(b["score"])),
                    "screen_time_s": float(s["time_s"]),
                    "resource_time_s": float(r["time_s"]),
                }
            )
    return examples


def candidate_thresholds(values: list[float]) -> list[float]:
    unique = sorted(set(values))
    if not unique:
        return []
    thresholds = [unique[0] - 1e-9, unique[-1] + 1e-9]
    thresholds.extend(unique)
    thresholds.extend((a + b) / 2.0 for a, b in zip(unique, unique[1:]))
    return sorted(set(thresholds))


def predict(feature_value: float, threshold: float, skip_if_ge: bool) -> bool:
    return feature_value >= threshold if skip_if_ge else feature_value < threshold


def train_stump(examples: list[dict[str, float | str | bool]]) -> dict[str, object]:
    if not examples:
        raise SystemExit("no training examples")
    best: tuple[tuple[int, int, float, int, float, float], str, float, bool] | None = None
    for feature in FEATURES:
        values = [float(ex[feature]) for ex in examples]
        for threshold in candidate_thresholds(values):
            for skip_if_ge in (True, False):
                false_skips = 0
                errors = 0
                saved_time = 0.0
                skips = 0
                for ex in examples:
                    pred = predict(float(ex[feature]), threshold, skip_if_ge)
                    truth = bool(ex["skip_resource"])
                    if pred != truth:
                        errors += 1
                    if pred and not truth:
                        false_skips += 1
                    if pred:
                        skips += 1
                        saved_time += max(0.0, float(ex["resource_time_s"]) - float(ex["screen_time_s"]))
                # Safety first: a false skip loses the Resource-NMCTS tail.
                # If two gates are otherwise tied on observed data, prefer the
                # narrower skip region to avoid midpoint extrapolation such as
                # learning n >= 19 from only n=18 and n=20 observations.
                complexity = 0.0 if feature == "n" else 1.0
                conservative_boundary = -threshold if skip_if_ge else threshold
                score = (false_skips, errors, -saved_time, -skips, conservative_boundary, complexity)
                if best is None or score < best[0]:
                    best = (score, feature, threshold, skip_if_ge)
    assert best is not None
    score, feature, threshold, skip_if_ge = best
    return {
        "kind": "decision_stump",
        "feature": feature,
        "threshold": threshold,
        "skip_if_ge": skip_if_ge,
        "training_false_skips": int(score[0]),
        "training_errors": int(score[1]),
        "training_examples": len(examples),
        "training_saved_time_s": -float(score[2]),
        "features": FEATURES,
    }


def evaluate(model: dict[str, object], examples: list[dict[str, float | str | bool]]) -> dict[str, object]:
    feature = str(model["feature"])
    threshold = float(model["threshold"])
    skip_if_ge = bool(model["skip_if_ge"])
    tp = tn = fp = fn = 0
    saved_time = 0.0
    score_penalty = 0.0
    rows = []
    for ex in examples:
        pred = predict(float(ex[feature]), threshold, skip_if_ge)
        truth = bool(ex["skip_resource"])
        if pred and truth:
            tp += 1
        elif not pred and not truth:
            tn += 1
        elif pred and not truth:
            fp += 1
            score_penalty += abs(float(ex["resource_gain_pct"]))
        else:
            fn += 1
        if pred:
            saved_time += max(0.0, float(ex["resource_time_s"]) - float(ex["screen_time_s"]))
        rows.append({**ex, "pred_skip_resource": pred})
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "saved_time_s": saved_time,
        "false_skip_score_penalty_pct_sum": score_penalty,
        "rows": rows,
    }


def write_analysis(path: Path, model: dict[str, object], evaluation: dict[str, object]) -> None:
    lines = [
        "# Structure Gate Training",
        "",
        "The gate predicts whether the adaptive Boolean-ring screen is sufficient,",
        "or whether the expensive Resource-NMCTS tail should still run.",
        "",
        "## Learned gate",
        "",
        f"- model: `{model['kind']}`",
        f"- feature: `{model['feature']}`",
        f"- threshold: `{float(model['threshold']):.6g}`",
        f"- skip if >= threshold: `{bool(model['skip_if_ge'])}`",
        f"- training examples: {model['training_examples']}",
        f"- training errors: {model['training_errors']}",
        f"- training false skips: {model.get('training_false_skips', 0)}",
        f"- apparent saved time: {float(evaluation['saved_time_s']):.3f} s",
        "",
        "## Confusion Matrix",
        "",
        "| truth / prediction | skip resource | run resource |",
        "|---|---:|---:|",
        f"| skip resource | {evaluation['tp']} | {evaluation['fn']} |",
        f"| run resource | {evaluation['fp']} | {evaluation['tn']} |",
        "",
        "## Training Rows",
        "",
        "| name | n | anf terms | resource gain vs screen | predicted skip | true skip | screen time | resource time |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in evaluation["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["name"]),
                    f"{float(row['n']):.0f}",
                    f"{float(row['anf_terms']):.0f}",
                    f"{float(row['resource_gain_pct']):+.2f}%",
                    str(bool(row["pred_skip_resource"])),
                    str(bool(row["skip_resource"])),
                    f"{float(row['screen_time_s']):.3f}",
                    f"{float(row['resource_time_s']):.3f}",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        nargs="+",
        type=Path,
        default=[
            RESULTS / "raw_mega_adaptive_screen_resource.csv",
            RESULTS / "raw_giga_adaptive_screen_resource.csv",
        ],
    )
    parser.add_argument("--screen-method", default="and_boolean_linear_pair_screen_adaptive")
    parser.add_argument("--resource-method", default="and_resource_nmcts")
    parser.add_argument("--single-method", default="and_boolean_linear_pair_screen")
    parser.add_argument("--min-resource-gain-pct", type=float, default=0.5)
    parser.add_argument("--out-model", type=Path, default=MODELS / "resource_structure_gate.json")
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_structure_gate.md")
    args = parser.parse_args(list(argv) if argv is not None else None)

    examples = build_examples(
        args.inputs,
        screen_method=args.screen_method,
        resource_method=args.resource_method,
        single_method=args.single_method,
        min_resource_gain_pct=args.min_resource_gain_pct,
    )
    model = train_stump(examples)
    model.update(
        {
            "screen_method": args.screen_method,
            "resource_method": args.resource_method,
            "single_method": args.single_method,
            "min_resource_gain_pct": args.min_resource_gain_pct,
            "training_inputs": [str(path) for path in args.inputs],
        }
    )
    evaluation = evaluate(model, examples)
    args.out_model.parent.mkdir(parents=True, exist_ok=True)
    args.out_model.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_analysis(args.out, model, evaluation)
    print(f"examples: {len(examples)}")
    print(f"model: {args.out_model}")
    print(f"analysis: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
