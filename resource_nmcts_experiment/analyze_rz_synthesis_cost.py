#!/usr/bin/env python3
"""Approximate non-Clifford Rz synthesis cost for RevKit oracle_synth outputs.

The RevKit Python baseline emits Rz-phase netlists.  Previous analyses treated
each non-Clifford Rz as a symbolic score charge.  This script converts that
symbol into a configurable Clifford+T approximation proxy:

    T_per_Rz = ceil(slope * log2(1/epsilon) + offset)

The defaults include a Ross-Selinger-style z-rotation proxy and a more
conservative Selinger SU(2)-style proxy.  These are deliberately model costs,
not exact synthesis: no gate sequence is emitted and no hardware mapping is
claimed.  The goal is to quantify whether the RevKit lower-bound advantage
survives a standard fault-tolerant rotation-synthesis accounting.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from analyze_phase_rz_portfolio import (
    BASELINE_METHODS,
    RESOURCE_METHODS,
    by_name_method,
    f,
    load_csv,
    rel,
    select_best,
    usable,
)
from run_external_baselines import DEFAULT_WEIGHTS


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class PortfolioSpec:
    name: str
    methods: tuple[str, ...]


@dataclass(frozen=True)
class SynthesisModel:
    name: str
    slope: float
    offset: float


PORTFOLIOS = [
    PortfolioSpec("resource_nmcts_family", tuple(RESOURCE_METHODS)),
    PortfolioSpec("traditional_baseline_family", tuple(BASELINE_METHODS)),
]

DEFAULT_MODELS = [
    SynthesisModel("ross_selinger_z", 3.0, 0.0),
    SynthesisModel("selinger_su2", 4.0, 10.0),
]
DEFAULT_EPSILONS = [1e-3, 1e-6, 1e-10]


def parse_models(raw: str) -> list[SynthesisModel]:
    models: list[SynthesisModel] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 3:
            raise ValueError(f"model must be name:slope:offset, got {item!r}")
        models.append(SynthesisModel(parts[0], float(parts[1]), float(parts[2])))
    return models


def model_t_per_rz(model: SynthesisModel, epsilon: float) -> int:
    if not (0 < epsilon < 1):
        raise ValueError(f"epsilon must be in (0, 1), got {epsilon}")
    return max(0, int(math.ceil(model.slope * math.log2(1.0 / epsilon) + model.offset)))


def score_from_counts(T: float, CNOT: float, depth: float, gates: float, peak_ancilla: float) -> float:
    return (
        DEFAULT_WEIGHTS["t"] * T
        + DEFAULT_WEIGHTS["cnot"] * CNOT
        + DEFAULT_WEIGHTS["depth"] * depth
        + DEFAULT_WEIGHTS["gates"] * gates
        + DEFAULT_WEIGHTS["ancilla"] * peak_ancilla
    )


def compare_pairs(pairs: list[tuple[float, float]]) -> dict[str, object]:
    wins = losses = ties = 0
    relatives: list[float] = []
    for target, baseline in pairs:
        if target < baseline - 1e-9:
            wins += 1
        elif target > baseline + 1e-9:
            losses += 1
        else:
            ties += 1
        relatives.append(rel(target, baseline))
    return {
        "items": len(pairs),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives) if relatives else 0.0,
    }


def analyze(
    internal_rows: list[dict[str, str]],
    revkit_rows: list[dict[str, str]],
    epsilons: list[float],
    models: list[SynthesisModel],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    internal = by_name_method(internal_rows)
    revkit = by_name_method(revkit_rows)
    raw: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []

    for name, baselines in sorted(revkit.items()):
        rev = baselines.get("external_revkit_oracle_synth")
        if rev is None or not usable(rev):
            continue
        methods = internal.get(name, {})
        for spec in PORTFOLIOS:
            selected = select_best(methods, spec.methods)
            if selected is None:
                continue
            for model in models:
                for epsilon in epsilons:
                    t_per_rz = model_t_per_rz(model, epsilon)
                    rz_non = f(rev, "rz_non_clifford")
                    extra_t = rz_non * t_per_rz
                    rev_T = f(rev, "T") + extra_t
                    rev_gates = f(rev, "gates") + extra_t
                    # A conservative logic-layer stage proxy: approximate
                    # synthesized rotations serialize on their qubit.
                    rev_depth = f(rev, "depth") + extra_t
                    rev_score = score_from_counts(
                        rev_T,
                        f(rev, "CNOT"),
                        rev_depth,
                        rev_gates,
                        f(rev, "peak_ancilla"),
                    )
                    raw.append(
                        {
                            "name": name,
                            "n": int(rev["n"]),
                            "portfolio": spec.name,
                            "selected_method": selected["method"],
                            "selected_score": f(selected, "score"),
                            "selected_T": f(selected, "T"),
                            "selected_CNOT": f(selected, "CNOT"),
                            "revkit_lower_score": f(rev, "score"),
                            "revkit_non_clifford_rz": rz_non,
                            "model": model.name,
                            "epsilon": epsilon,
                            "t_per_rz": t_per_rz,
                            "extra_T": extra_t,
                            "revkit_synth_T": rev_T,
                            "revkit_synth_depth": rev_depth,
                            "revkit_synth_gates": rev_gates,
                            "revkit_synth_score": rev_score,
                            "relative": rel(f(selected, "score"), rev_score),
                            "win": int(f(selected, "score") < rev_score - 1e-9),
                        }
                    )

    for spec in PORTFOLIOS:
        for model in models:
            for epsilon in epsilons:
                rows = [
                    row
                    for row in raw
                    if row["portfolio"] == spec.name and row["model"] == model.name and float(row["epsilon"]) == epsilon
                ]
                if not rows:
                    continue
                stats = compare_pairs(
                    [(float(row["selected_score"]), float(row["revkit_synth_score"])) for row in rows]
                )
                winner_counts: dict[str, int] = {}
                for row in rows:
                    method = str(row["selected_method"])
                    winner_counts[method] = winner_counts.get(method, 0) + 1
                summary.append(
                    {
                        "portfolio": spec.name,
                        "model": model.name,
                        "epsilon": epsilon,
                        "t_per_rz": model_t_per_rz(model, epsilon),
                        "items": stats["items"],
                        "wins": stats["wins"],
                        "losses": stats["losses"],
                        "ties": stats["ties"],
                        "mean_relative": stats["mean_relative"],
                        "mean_selected_score": statistics.mean(float(row["selected_score"]) for row in rows),
                        "mean_revkit_synth_score": statistics.mean(float(row["revkit_synth_score"]) for row in rows),
                        "mean_extra_T": statistics.mean(float(row["extra_T"]) for row in rows),
                        "winner_counts": ";".join(
                            f"{name}:{count}"
                            for name, count in sorted(winner_counts.items(), key=lambda item: (-item[1], item[0]))
                        ),
                    }
                )
    return raw, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{value:+.2%}"


def latex_pct(value: float) -> str:
    return pct(value).replace("%", r"\%")


def write_analysis(path: Path, summary: list[dict[str, object]]) -> None:
    lines = [
        "# Approximate Rz Synthesis Cost Analysis",
        "",
        "This analysis charges every non-Clifford Rz in the RevKit `oracle_synth`",
        "netlist by a configurable approximate Clifford+T synthesis model",
        "`ceil(slope*log2(1/epsilon)+offset)` T gates.",
        "",
        "The default `ross_selinger_z` proxy uses slope 3 and offset 0, reflecting",
        "the typical z-rotation asymptotic T-count reported by Ross and Selinger.",
        "The `selinger_su2` proxy uses slope 4 and offset 10 as a more conservative",
        "single-qubit approximation proxy.",
        "",
        "This remains a logic-layer cost model: no approximate rotation sequence is",
        "emitted, no synthesis runtime is measured, and no hardware mapping is used.",
        "",
        "## Summary",
        "",
        "| portfolio | model | epsilon | T/Rz | W/L/T | mean relative | mean RevKit synth score | mean extra T |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['portfolio']} | {row['model']} | {float(row['epsilon']):.0e} | "
            f"{row['t_per_rz']} | {row['wins']}/{row['losses']}/{row['ties']} | "
            f"{pct(float(row['mean_relative']))} | {float(row['mean_revkit_synth_score']):.2f} | "
            f"{float(row['mean_extra_T']):.2f} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is stricter than the lower-bound Rz-phase score but still not exact synthesis.",
            "- Exact or approximate rotation synthesis can change constants and depth scheduling.",
            "- The result should be used to set a phase/Rz-aware emitter target, not as a final Clifford+T proof.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary: list[dict[str, object]]) -> None:
    focus = {
        ("resource_nmcts_family", "ross_selinger_z", 1e-3),
        ("resource_nmcts_family", "ross_selinger_z", 1e-6),
        ("resource_nmcts_family", "ross_selinger_z", 1e-10),
        ("traditional_baseline_family", "ross_selinger_z", 1e-6),
        ("resource_nmcts_family", "selinger_su2", 1e-6),
    }
    labels = {
        "resource_nmcts_family": "Resource-NMCTS family",
        "traditional_baseline_family": "Traditional baseline family",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{llrrrr}\n")
        f.write("\\toprule\n")
        f.write("Portfolio & Model/$\\epsilon$ & T/Rz & Items & W/L/T & Mean $\\Delta$ \\\\\n")
        f.write("\\midrule\n")
        for row in summary:
            key = (str(row["portfolio"]), str(row["model"]), float(row["epsilon"]))
            if key not in focus:
                continue
            label = labels.get(str(row["portfolio"]), str(row["portfolio"]))
            model_eps = f"{row['model']}/{float(row['epsilon']):.0e}".replace("_", r"\_")
            f.write(
                f"{label} & {model_eps} & {row['t_per_rz']} & {row['items']} & "
                f"{row['wins']}/{row['losses']}/{row['ties']} & "
                f"{latex_pct(float(row['mean_relative']))} \\\\\n"
            )
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--revkit", type=Path, default=RESULTS / "raw_revkit_oracle_synth_traditional.csv")
    parser.add_argument("--epsilons", default=",".join(f"{value:g}" for value in DEFAULT_EPSILONS))
    parser.add_argument(
        "--models",
        default=",".join(f"{model.name}:{model.slope:g}:{model.offset:g}" for model in DEFAULT_MODELS),
    )
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_rz_synthesis_cost.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_rz_synthesis_cost.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_rz_synthesis_cost.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "rz_synthesis_cost.tex")
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_rz_synthesis_cost.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    started = time.time()
    epsilons = [float(item.strip()) for item in args.epsilons.split(",") if item.strip()]
    models = parse_models(args.models)
    raw, summary = analyze(load_csv(args.internal), load_csv(args.revkit), epsilons, models)
    write_csv(args.raw_out, raw)
    write_csv(args.summary, summary)
    write_analysis(args.analysis, summary)
    write_latex(args.latex_out, summary)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(
            {
                "internal": str(args.internal),
                "revkit": str(args.revkit),
                "epsilons": epsilons,
                "models": [model.__dict__ for model in models],
                "raw_out": str(args.raw_out),
                "summary": str(args.summary),
                "analysis": str(args.analysis),
                "latex_out": str(args.latex_out),
                "rows": len(raw),
                "summary_rows": len(summary),
                "elapsed_s": time.time() - started,
                "claim_boundary": "Approximate logic-layer Rz synthesis cost model; no emitted rotation sequences and no hardware mapping.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"elapsed {time.time() - started:.2f}s")
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
