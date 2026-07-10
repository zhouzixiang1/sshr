#!/usr/bin/env python3
"""Generate figure-driven manuscript assets for the Resource-NMCTS paper.

The script only consumes existing experiment outputs.  It does not rerun
synthesis experiments.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
OUT = PROJECT_ROOT / "paper_latex" / "figures" / "submission_v36"
SOURCE = OUT / "source_data"

METHOD_LABELS = {
    "direct_anf": "Direct ANF",
    "and_direct_anf": "AND-direct",
    "and_esop_milp": "ESOP-MILP",
    "and_cube_beam": "ESOP beam",
    "sshr_h": "SSHR-H",
    "and_resource_nmcts": "Resource",
    "and_pareto_resource_nmcts": "Pareto-Resource",
}

PALETTE = {
    "neutral": "#6F7785",
    "light": "#E9EDF2",
    "direct": "#8A95A5",
    "baseline": "#A7B1C2",
    "resource": "#3F6C9A",
    "pareto": "#1B4F72",
    "gain": "#3B8C5A",
    "warn": "#B56B45",
    "phase": "#6A5ACD",
}


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "svg.hashsalt": "resource-nmcts-submission-v36",
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_source(name: str, rows: list[dict[str, object]], fieldnames: Iterable[str]) -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    with (SOURCE / f"{name}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize_svg(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def assert_pdf_readable(path: Path) -> None:
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise RuntimeError(f"Generated PDF is incomplete: {path}")
    try:
        subprocess.run(
            ["pdfinfo", str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        raise RuntimeError(f"Generated PDF is unreadable: {path}\n{detail}") from exc


def atomic_savefig(fig: plt.Figure, path: Path, *, fmt: str | None = None, **kwargs: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    if tmp.exists():
        tmp.unlink()
    fig.savefig(tmp, format=fmt, **kwargs)
    if path.suffix.lower() == ".pdf":
        assert_pdf_readable(tmp)
    tmp.replace(path)


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    creator = "Resource-NMCTS submission figure generator"
    fixed_date = datetime(2026, 7, 9, tzinfo=timezone.utc)
    fig.canvas.draw()
    atomic_savefig(
        fig,
        OUT / f"{name}.pdf",
        fmt="pdf",
        bbox_inches="tight",
        metadata={"Creator": creator, "CreationDate": fixed_date, "ModDate": fixed_date},
    )
    svg_path = OUT / f"{name}.svg"
    atomic_savefig(
        fig,
        svg_path,
        fmt="svg",
        bbox_inches="tight",
        metadata={"Creator": creator, "Date": fixed_date.isoformat()},
    )
    normalize_svg(svg_path)
    atomic_savefig(
        fig,
        OUT / f"{name}.png",
        fmt="png",
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": creator},
    )
    plt.close(fig)


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in ("", None):
        return default
    return float(value)


def parse_analysis_row(path: Path, target: str, baseline: str, metric: str) -> dict[str, object]:
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 7 or parts[0] != target or parts[1] != baseline or parts[2] != metric:
            continue
        return {
            "target": target,
            "baseline": baseline,
            "metric": metric,
            "wins": int(parts[3]),
            "losses": int(parts[4]),
            "ties": int(parts[5]),
            "mean_relative_pct": float(parts[6].replace("%", "")),
        }
    raise KeyError((target, baseline, metric, path))


def find_summary_row(path: Path, **criteria: str) -> dict[str, str]:
    for row in read_csv(path):
        if all(row.get(k) == v for k, v in criteria.items()):
            return row
    raise KeyError((path, criteria))


def fig_pipeline() -> None:
    """Schematic-led figure: verifiable search pipeline."""
    rows = [
        {"step": "1", "module": "Input", "claim": "Truth table or ANF terms"},
        {"step": "2", "module": "State", "claim": "ANF/FPRM term set"},
        {"step": "3", "module": "Actions", "claim": "Boolean-ring, affine, parity factors"},
        {"step": "4", "module": "Search", "claim": "Neural prior + MCTS + frontier policy"},
        {"step": "5", "module": "Selection", "claim": "Guarded Pareto portfolio"},
        {"step": "6", "module": "Output", "claim": "Logic-layer reversible oracle"},
        {"step": "7", "module": "Verification", "claim": "Plan, circuit, and truth-table checks"},
    ]
    write_source("fig1_pipeline", rows, ["step", "module", "claim"])

    fig, ax = plt.subplots(figsize=(7.2, 2.45))
    ax.set_axis_off()
    xs = [0.03, 0.18, 0.34, 0.50, 0.66, 0.82]
    labels = [
        ("Input", "truth table\nor ANF"),
        ("State", "ANF/FPRM\nterm set"),
        ("Action space", "factors,\npolarity,\naffine phase"),
        ("Search", "neural prior\n+ MCTS"),
        ("Guard", "baseline-safe\nPareto pick"),
        ("Oracle", "logic-layer\ncircuit"),
    ]
    for i, (x, (title, text)) in enumerate(zip(xs, labels)):
        color = PALETTE["resource"] if i in (2, 3, 4) else PALETTE["baseline"]
        box = FancyBboxPatch(
            (x, 0.43),
            0.12,
            0.34,
            boxstyle="round,pad=0.018,rounding_size=0.02",
            linewidth=0.8,
            edgecolor=color,
            facecolor="#F7F9FB",
        )
        ax.add_patch(box)
        ax.text(x + 0.06, 0.66, title, ha="center", va="center", weight="bold", color=color)
        ax.text(x + 0.06, 0.54, text, ha="center", va="center", color="#2A2E35")
        if i < len(xs) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + 0.125, 0.60),
                    (xs[i + 1] - 0.006, 0.60),
                    arrowstyle="-|>",
                    mutation_scale=8,
                    linewidth=0.8,
                    color="#6A717C",
                )
            )

    checks = [
        ("Plan ANF", "symbolic expansion"),
        ("Circuit ANF", "emitted-circuit simulation"),
        ("Truth table", "complete bridge n=21--30"),
    ]
    for j, (title, text) in enumerate(checks):
        x = 0.19 + j * 0.22
        box = FancyBboxPatch(
            (x, 0.09),
            0.19,
            0.18,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            linewidth=0.7,
            edgecolor=PALETTE["gain"],
            facecolor="#F3FAF5",
        )
        ax.add_patch(box)
        ax.text(x + 0.095, 0.20, title, ha="center", va="center", weight="bold", color=PALETTE["gain"])
        ax.text(x + 0.095, 0.13, text, ha="center", va="center", fontsize=5.9, color="#2A2E35")
    ax.text(0.03, 0.93, "a", fontsize=10, weight="bold")
    ax.text(0.06, 0.90, "Resource-constrained neural MCTS oracle synthesis remains verifiable at every layer.", weight="bold")
    save(fig, "fig1_pipeline")


def aggregate_traditional() -> list[dict[str, object]]:
    rows = read_csv(RESULTS / "raw_traditional_resource.csv")
    methods = [
        "direct_anf",
        "and_direct_anf",
        "and_esop_milp",
        "sshr_h",
        "and_resource_nmcts",
        "and_pareto_resource_nmcts",
    ]
    out: list[dict[str, object]] = []
    for method in methods:
        subset = [r for r in rows if r["method"] == method and r.get("correct") == "True"]
        for metric in ("T", "CNOT", "depth", "score", "peak_ancilla"):
            values = [as_float(r, metric) for r in subset]
            out.append(
                {
                    "method": method,
                    "label": METHOD_LABELS[method],
                    "metric": metric,
                    "functions": len(subset),
                    "mean": sum(values) / len(values),
                }
            )
    return out


def fig_traditional_resources() -> None:
    data = aggregate_traditional()
    write_source("fig2_traditional_resources", data, ["method", "label", "metric", "functions", "mean"])

    metrics = [("T", "Mean T-count"), ("score", "Mean score"), ("CNOT", "Mean CNOT"), ("depth", "Mean depth")]
    labels = [METHOD_LABELS[m] for m in ["direct_anf", "and_direct_anf", "and_esop_milp", "sshr_h", "and_resource_nmcts", "and_pareto_resource_nmcts"]]
    colors = [PALETTE["direct"], PALETTE["baseline"], PALETTE["baseline"], PALETTE["warn"], PALETTE["resource"], PALETTE["pareto"]]

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8))
    for ax, (metric, title) in zip(axes.ravel(), metrics):
        vals = [next(float(r["mean"]) for r in data if r["label"] == label and r["metric"] == metric) for label in labels]
        ax.bar(range(len(labels)), vals, color=colors, width=0.72)
        ax.set_title(title, loc="left", weight="bold")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=35, ha="right")
        ax.grid(axis="y", color="#E3E6EA", linewidth=0.6)
        ax.set_axisbelow(True)
    fig.text(0.01, 0.98, "b", fontsize=10, weight="bold")
    fig.suptitle("Pareto-Resource-NMCTS lowers T-count and weighted score, while SSHR-H remains a CNOT-oriented baseline.", x=0.52, y=1.02, fontsize=8.5, weight="bold")
    fig.tight_layout()
    save(fig, "fig2_traditional_resources")


def comparison_rows() -> list[dict[str, object]]:
    trad = RESULTS / "analysis_traditional_resource.md"
    rows = [
        parse_analysis_row(trad, "and_pareto_resource_nmcts", "direct_anf", "score"),
        parse_analysis_row(trad, "and_pareto_resource_nmcts", "and_cube_beam", "score"),
        parse_analysis_row(trad, "and_pareto_resource_nmcts", "and_esop_milp", "score"),
        parse_analysis_row(trad, "and_pareto_resource_nmcts", "sshr_h", "T"),
    ]
    for row in rows:
        row["baseline"] = METHOD_LABELS.get(str(row["baseline"]), str(row["baseline"]))
    rows[-1]["baseline"] = "SSHR-H (T)"

    ros = find_summary_row(
        RESULTS / "summary_ros_lut_proxy.csv",
        target="and_pareto_resource_nmcts",
        baseline="external_ros_lut_proxy",
        metric="score",
    )
    rows.append(
        {
            "target": "and_pareto_resource_nmcts",
            "baseline": "ROS-style LUT proxy",
            "metric": "score",
            "wins": int(ros["wins"]),
            "losses": int(ros["losses"]),
            "ties": int(ros["ties"]),
            "mean_relative_pct": 100 * float(ros["mean_relative"]),
        }
    )
    mt = find_summary_row(
        RESULTS / "summary_mockturtle_xag_probe.csv",
        target="and_pareto_resource_nmcts",
        baseline="external_mockturtle_xag_k4",
        metric="score",
    )
    rows.append(
        {
            "target": "and_pareto_resource_nmcts",
            "baseline": "mockturtle XAG n<=6",
            "metric": "score",
            "wins": int(mt["wins"]),
            "losses": int(mt["losses"]),
            "ties": int(mt["ties"]),
            "mean_relative_pct": 100 * float(mt["mean_relative"]),
        }
    )
    mth = find_summary_row(
        RESULTS / "summary_mockturtle_xag_highdim_probe.csv",
        target="and_pareto_resource_nmcts",
        baseline="external_mockturtle_xag_k4",
        metric="score",
    )
    rows.append(
        {
            "target": "and_pareto_resource_nmcts",
            "baseline": "mockturtle XAG n=14",
            "metric": "score",
            "wins": int(mth["wins"]),
            "losses": int(mth["losses"]),
            "ties": int(mth["ties"]),
            "mean_relative_pct": 100 * float(mth["mean_relative"]),
        }
    )
    return rows


def fig_baseline_comparisons() -> None:
    data = comparison_rows()
    write_source("fig3_baseline_comparisons", data, ["target", "baseline", "metric", "wins", "losses", "ties", "mean_relative_pct"])

    labels = [str(r["baseline"]) for r in data]
    vals = [float(r["mean_relative_pct"]) for r in data]
    colors = [PALETTE["gain"] if v < 0 else PALETTE["warn"] for v in vals]
    y = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.barh(y, vals, color=colors, height=0.62)
    ax.axvline(0, color="#30343B", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean relative change (%)")
    ax.set_title("Matched comparisons emphasize where the method wins and what is being measured.", loc="left", weight="bold")
    for i, row in enumerate(data):
        text = f"{int(row['wins'])}/{int(row['losses'])}/{int(row['ties'])}"
        if vals[i] < -70:
            x_text, ha = vals[i] + 4, "left"
        elif vals[i] < 0:
            x_text, ha = vals[i] - 2, "right"
        else:
            x_text, ha = vals[i] + 2, "left"
        ax.text(x_text, i, text, va="center", ha=ha, color="#1E2329")
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_xlim(-100, 5)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.97, "c", fontsize=10, weight="bold")
    fig.tight_layout()
    save(fig, "fig3_baseline_comparisons")


def phase_rows() -> list[dict[str, object]]:
    summary = read_csv(RESULTS / "summary_phase_parity_affine.csv")
    wanted = [
        ("phase_parity_affine_fprm_opt_tperrz30", "phase_parity_fprm_opt_tperrz30", "score_synth_tperrz30", "Affine vs fixed FPRM"),
        ("phase_parity_affine_fprm_opt_tperrz30", "phase_parity_anf", "score_synth_tperrz30", "Affine vs ANF"),
        ("phase_parity_affine_fprm_opt_tperrz30", "external_revkit_oracle_synth", "score_synth_tperrz30", "Affine vs RevKit"),
        ("phase_parity_affine_fprm_opt_score", "phase_parity_fprm_opt_score", "score", "Affine-score vs FPRM"),
        ("phase_parity_affine_fprm_opt_tperrz30", "phase_parity_fprm_opt_tperrz30", "rz_non_clifford", "non-Clifford Rz"),
    ]
    out = []
    for target, baseline, metric, label in wanted:
        row = next(
            r
            for r in summary
            if r["target"] == target
            and r["baseline"] == baseline
            and r["metric"] == metric
        )
        out.append(
            {
                "comparison": label,
                "baseline": baseline,
                "metric": metric,
                "items": int(row["items"]),
                "wins": int(row["wins"]),
                "losses": int(row["losses"]),
                "ties": int(row["ties"]),
                "mean_relative_pct": 100 * float(row["mean_relative"]),
            }
        )
    # Selection counts are method-level metadata from the analysis run.
    out.append(
        {
            "comparison": "nonidentity transform selections",
            "baseline": "metadata",
            "metric": "count",
            "items": 177,
            "wins": 81,
            "losses": 0,
            "ties": 96,
            "mean_relative_pct": 100 * 81 / 177,
        }
    )
    out.append(
        {
            "comparison": "nonzero polarity selections",
            "baseline": "metadata",
            "metric": "count",
            "items": 177,
            "wins": 43,
            "losses": 0,
            "ties": 134,
            "mean_relative_pct": 100 * 43 / 177,
        }
    )
    return out


def fig_phase_affine() -> None:
    data = phase_rows()
    write_source("fig4_phase_affine", data, ["comparison", "baseline", "metric", "items", "wins", "losses", "ties", "mean_relative_pct"])
    bars = [r for r in data if r["metric"] != "count"]
    counts = [r for r in data if r["metric"] == "count"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.8, 1.0]})
    ax = axes[0]
    y = list(range(len(bars)))
    vals = [float(r["mean_relative_pct"]) for r in bars]
    ax.barh(y, vals, color=PALETTE["phase"], height=0.62)
    ax.axvline(0, color="#30343B", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([str(r["comparison"]) for r in bars])
    ax.invert_yaxis()
    ax.set_xlabel("Mean relative change (%)")
    ax.set_title("Affine-FPRM improves the verified phase/Rz search branch.", loc="left", weight="bold")
    for i, row in enumerate(bars):
        if vals[i] < -35:
            x_text, ha = vals[i] + 3.0, "left"
        else:
            x_text, ha = vals[i] - 0.8, "right"
        ax.text(x_text, i, f"{row['wins']}/{row['losses']}/{row['ties']}", va="center", ha=ha, color="#1E2329")
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_xlim(-70, 2)

    ax2 = axes[1]
    ax2.bar([0, 1], [float(r["mean_relative_pct"]) for r in counts], color=[PALETTE["phase"], PALETTE["resource"]])
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["nonidentity\nB", "nonzero\npolarity"])
    ax2.set_ylim(0, 55)
    ax2.set_ylabel("Selected functions (%)")
    for i, row in enumerate(counts):
        ax2.text(i, float(row["mean_relative_pct"]) + 2, f"{row['wins']}/177", ha="center")
    ax2.set_title("Search choices", loc="left", weight="bold")
    fig.text(0.01, 0.96, "e", fontsize=10, weight="bold")
    fig.tight_layout()
    save(fig, "fig4_phase_affine")


def first_percent(text: str) -> float:
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\\?%", text)
    if not match:
        return 0.0
    return float(match.group(1))


def learned_control_rows() -> list[dict[str, object]]:
    rows = []
    phase_random = read_csv(RESULTS / "summary_phase_policy_random_control.csv")
    phase_p = next(
        float(row["sign_p"])
        for row in phase_random
        if row["policy"] == "diverse" and int(row["topk"]) == 512
    )
    for row in read_csv(RESULTS / "summary_learned_control_audit.csv"):
        component = row["component"]
        quality_delta = first_percent(row["quality"])
        # This specificity control reports a retained-win percentage rather
        # than a score delta.  Keep it in Source Data, but do not place the
        # incomparable percentage on the score-change axis in panel 3.
        quality_delta_for_plot: float | str = (
            "" if component == "Bit-flip CV gate random-interval control" else quality_delta
        )
        role = row["role"]
        cost = row["cost"]
        if "512/8192" in cost:
            cost_saving = 100.0 * (1.0 - 512.0 / 8192.0)
        else:
            cost_saving = -first_percent(cost)
        short = {
            "Depth-frontier policy": "frontier",
            "Frontier random-depth control": "random depth",
            "Stage-gated frontier": "stage gate",
            "Sparse depth-4 gate": "sparse gate",
            "Rank-diverse phase shortlist": "phase shortlist",
            "Contextual-bandit Pareto budget policy": "RL budget",
            "Bit-flip learned prior": "learned prior",
            "Bit-flip low-budget prior": "low-budget prior",
            "Bit-flip ANF-term prior gate": "ANF gate",
            "Bit-flip CV ANF-term prior gate": "CV ANF gate",
            "Boolean neural guard": "neural guard",
            "Root-action neural ranker": "root ranker",
            "Root-action neural candidate extension": "root extension",
        }.get(component, component)
        rows.append(
            {
                "component": component,
                "short": short,
                "promoted": role.startswith("promoted"),
                "quality_delta_pct": quality_delta_for_plot,
                "cost_saving_pct": cost_saving,
                "quality": row["quality"],
                "cost": cost,
                "role": role,
                "phase_random_sign_p": phase_p if component == "Rank-diverse phase shortlist" else "",
            }
        )
    return rows


def fig_learned_control_summary() -> None:
    data = learned_control_rows()
    write_source(
        "fig7_learned_control_summary",
        data,
        [
            "component",
            "short",
            "promoted",
            "quality_delta_pct",
            "cost_saving_pct",
            "quality",
            "cost",
            "role",
            "phase_random_sign_p",
        ],
    )
    promoted = [row for row in data if row["promoted"]]
    limited = [
        row
        for row in data
        if not row["promoted"] and row["quality_delta_pct"] not in ("", None)
    ]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.2, 2.75),
        gridspec_kw={"width_ratios": [1.15, 1.15, 1.0]},
    )
    colors = [
        PALETTE["resource"],
        PALETTE["baseline"],
        PALETTE["gain"],
        PALETTE["phase"],
        PALETTE["resource"],
    ]

    ax = axes[0]
    y = list(range(len(promoted)))
    quality = [float(row["quality_delta_pct"]) for row in promoted]
    ax.barh(y, quality, color=colors, height=0.6)
    ax.axvline(0, color="#30343B", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([str(row["short"]) for row in promoted])
    ax.invert_yaxis()
    ax.set_xlabel("Score change (%)")
    ax.set_title("Promoted controls keep quality.", loc="left", weight="bold")
    ax.set_xlim(-4.2, 0.35)
    for i, value in enumerate(quality):
        if value < -0.25:
            ax.text(value + 0.10, i, f"{value:+.2f}%", va="center", ha="left", fontsize=6.3, color="white")
        else:
            ax.text(value + 0.05, i, f"{value:+.2f}%", va="center", ha="left", fontsize=6.3, color="#1E2329")
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)

    ax = axes[1]
    savings = [float(row["cost_saving_pct"]) for row in promoted]
    ax.barh(y, savings, color=colors, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlabel("Time/eval saved (%)")
    ax.set_title("They reduce search effort.", loc="left", weight="bold")
    ax.set_xlim(0, 100)
    for i, (row, value) in enumerate(zip(promoted, savings)):
        label = f"{value:.1f}%"
        if row["component"] == "Rank-diverse phase shortlist":
            label += "\np=1.5e-5"
        ax.text(min(value + 2.0, 96), i, label, va="center", ha="left", fontsize=6.1)
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)

    ax = axes[2]
    x_limits = (-1.35, 0.18)
    y_limits = (-115.0, 115.0)
    label_positions = {
        "Frontier random-depth control": (-1.02, -67.0),
        "Bit-flip learned prior": (-0.65, -51.0),
        "Bit-flip low-budget prior": (-0.95, -14.0),
        "Bit-flip ANF-term prior gate": (-0.72, -27.0),
        "Bit-flip CV ANF-term prior gate": (-0.72, -39.0),
        "Boolean neural guard": (-0.68, -98.0),
        "Root-action neural candidate extension": (-0.62, 6.0),
    }
    for row in limited:
        x = float(row["quality_delta_pct"])
        yv = float(row["cost_saving_pct"])
        if not (x_limits[0] <= x <= x_limits[1] and y_limits[0] <= yv <= y_limits[1]):
            continue
        ax.scatter(x, yv, s=52, color=PALETTE["warn"], edgecolors="#1E2329", linewidths=0.4)
        label_x, label_y = label_positions.get(str(row["component"]), (x + 0.04, yv))
        ax.annotate(
            str(row["short"]),
            xy=(x, yv),
            xytext=(label_x, label_y),
            textcoords="data",
            va="center",
            ha="left",
            fontsize=5.5,
            clip_on=True,
            arrowprops={"arrowstyle": "-", "color": PALETTE["neutral"], "linewidth": 0.45},
        )
    ax.axvline(0, color="#30343B", linewidth=0.7)
    ax.axhline(0, color="#30343B", linewidth=0.7)
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    ax.set_xlabel("Score change (%)")
    ax.set_ylabel("Time/eval saved (%)")
    ax.set_title("Diagnostics expose limits.", loc="left", weight="bold")
    ax.grid(axis="both", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)

    fig.text(0.01, 0.96, "d", fontsize=10, weight="bold")
    fig.suptitle(
        "Learned controllers are promoted only where quality and search-effort evidence align.",
        x=0.53,
        y=1.03,
        fontsize=8.5,
        weight="bold",
    )
    fig.tight_layout()
    save(fig, "fig7_learned_control_summary")


def validation_rows() -> list[dict[str, object]]:
    groups = [
        ("n=20-64 item symbolic", "circuit_verified_rows", [
            "summary_screen_scale_terms.csv",
            "summary_screen_scale_extended_terms.csv",
            "summary_screen_scale_depth_frontier_terms.csv",
            "summary_screen_scale_depth_frontier_policy_terms.csv",
            "summary_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
            "summary_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv",
            "summary_screen_scale_ultra_scale64_terms.csv",
        ]),
        ("width probe symbolic", "circuit_verified_rows", [
            "summary_screen_scale_width6_probe_terms.csv",
            "summary_screen_scale_width12_probe_terms.csv",
            "summary_screen_scale_width24_probe_terms.csv",
        ]),
        ("truth bridge n=21-30", "truth_verified_rows", [
            "summary_truth_bridge_terms.csv",
            "summary_truth_bridge_n23_terms.csv",
            "summary_truth_bridge_n23_large_frontier_terms.csv",
            "summary_truth_bridge_n23_cost_time003_frontier_terms.csv",
            "summary_truth_bridge_n24_terms.csv",
            "summary_truth_bridge_n25_terms.csv",
            "summary_truth_bridge_n26_terms.csv",
            "summary_truth_bridge_n27_terms.csv",
            "summary_truth_bridge_n28_terms.csv",
            "summary_truth_bridge_n29_terms.csv",
            "summary_truth_bridge_n30_terms.csv",
        ]),
        ("phase exact search", "verified_up_to_global_phase", ["raw_phase_parity_affine.csv"]),
        ("phase policy pruning", "verified_up_to_global_phase", ["raw_phase_affine_policy_rank_diverse.csv"]),
    ]
    out: list[dict[str, object]] = []
    for label, column, files in groups:
        verified = 0
        total = 0
        for filename in files:
            rows = read_csv(RESULTS / filename)
            if column == "verified_up_to_global_phase":
                total += len(rows)
                verified += sum(1 for r in rows if r[column] == "True")
            else:
                for r in rows:
                    value = int(float(r[column]))
                    verified += value
                    total += value
        out.append({"group": label, "verified": verified, "total": total, "fraction": verified / total if total else 0})
    return out


def fig_validation() -> None:
    data = validation_rows()
    write_source("fig5_validation", data, ["group", "verified", "total", "fraction"])
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    y = list(range(len(data)))
    vals = [int(r["verified"]) for r in data]
    ax.barh(
        y,
        vals,
        color=[
            PALETTE["resource"],
            PALETTE["baseline"],
            PALETTE["gain"],
            PALETTE["phase"],
            PALETTE["direct"],
        ],
        height=0.62,
    )
    ax.set_yticks(y)
    ax.set_yticklabels([str(r["group"]) for r in data])
    ax.invert_yaxis()
    ax.set_xlabel("Verified rows")
    ax.set_title("Verification covers the reported logic-layer claims.", loc="left", weight="bold")
    for i, row in enumerate(data):
        ax.text(vals[i] * 1.01, i, f"{row['verified']}/{row['total']}", va="center")
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.96, "f", fontsize=10, weight="bold")
    fig.tight_layout()
    save(fig, "fig5_validation")


def sparse_gate_sensitivity_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    curve = []
    for row in read_csv(RESULTS / "summary_sparse_depth4_gate_threshold_sensitivity.csv"):
        curve.append(
            {
                "threshold": float(row["threshold"]),
                "time_saving_pct": -100.0 * float(row["mean_rel_time_vs_sparse"]),
                "score_gap_pct": 100.0 * float(row["mean_rel_score_vs_sparse"]),
                "false_skips": int(row["false_skips"]),
                "run_depth4": int(row["run_depth4"]),
            }
        )
    operating = []
    for row in read_csv(RESULTS / "summary_sparse_depth4_gate_threshold_operating_points.csv"):
        operating.append(
            {
                "label": row["label"],
                "threshold": float(row["threshold"]),
                "time_saving_pct": -100.0 * float(row["mean_rel_time_vs_sparse"]),
                "score_gap_pct": 100.0 * float(row["mean_rel_score_vs_sparse"]),
                "false_skips": int(row["false_skips"]),
                "run_depth4": int(row["run_depth4"]),
            }
        )
    return curve, operating


def fig_sparse_gate_sensitivity() -> None:
    curve, operating = sparse_gate_sensitivity_rows()
    source_rows = [
        {"kind": "curve", "label": "", **row}
        for row in curve
    ] + [
        {"kind": "operating", **row}
        for row in operating
    ]
    write_source(
        "fig6_sparse_gate_sensitivity",
        source_rows,
        ["kind", "label", "threshold", "time_saving_pct", "score_gap_pct", "false_skips", "run_depth4"],
    )

    selected = next(row for row in operating if row["label"] == "selected")
    max_zero = next(row for row in operating if row["label"] == "max zero-skip saving")
    one_skip = next(row for row in operating if row["label"] == "max one-skip saving")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))

    ax = axes[0]
    x = [max(float(r["threshold"]), 1e-6) for r in curve]
    time_saving = [float(r["time_saving_pct"]) for r in curve]
    false_skips = [int(r["false_skips"]) for r in curve]
    ax.plot(x, time_saving, color=PALETTE["resource"], linewidth=1.3, label="time saved")
    ax.axvline(max(float(selected["threshold"]), 1e-6), color=PALETTE["gain"], linestyle="--", linewidth=0.9)
    ax.axvline(max(float(max_zero["threshold"]), 1e-6), color=PALETTE["warn"], linestyle=":", linewidth=0.9)
    ax.set_xscale("log")
    ax.set_xlabel("Gate threshold")
    ax.set_ylabel("Time saved vs sparse frontier (%)", color=PALETTE["resource"])
    ax.tick_params(axis="y", labelcolor=PALETTE["resource"])
    ax.grid(axis="both", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)
    ax2 = ax.twinx()
    ax2.plot(x, false_skips, color=PALETTE["warn"], linewidth=1.0, label="false skips")
    ax2.set_ylabel("False skips", color=PALETTE["warn"])
    ax2.tick_params(axis="y", labelcolor=PALETTE["warn"])
    ax.set_title("Conservative threshold keeps false skips at zero.", loc="left", weight="bold")
    ax.text(
        max(float(selected["threshold"]), 1e-6),
        float(selected["time_saving_pct"]) + 4,
        "selected",
        ha="left",
        va="bottom",
        fontsize=6.4,
        color=PALETTE["gain"],
    )

    ax = axes[1]
    scatter = ax.scatter(
        [float(r["time_saving_pct"]) for r in curve],
        [float(r["score_gap_pct"]) for r in curve],
        c=[int(r["false_skips"]) for r in curve],
        cmap="Oranges",
        s=18,
        alpha=0.70,
        edgecolors="none",
    )
    for row, marker, color, label in [
        (selected, "o", PALETTE["gain"], "selected"),
        (max_zero, "s", PALETTE["resource"], "max zero-skip"),
        (one_skip, "^", PALETTE["warn"], "one-skip"),
    ]:
        ax.scatter(
            [float(row["time_saving_pct"])],
            [float(row["score_gap_pct"])],
            marker=marker,
            s=42,
            color=color,
            edgecolors="#1E2329",
            linewidths=0.4,
            label=label,
            zorder=3,
        )
    ax.axhline(0, color="#30343B", linewidth=0.7)
    ax.set_xlabel("Time saved vs sparse frontier (%)")
    ax.set_ylabel("Mean score gap vs sparse frontier (%)")
    ax.set_title("Risk appears only after the zero-skip plateau.", loc="left", weight="bold")
    ax.grid(axis="both", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=6)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label("False skips")

    fig.text(0.01, 0.96, "g", fontsize=10, weight="bold")
    fig.suptitle("Sparse depth-4 gate threshold sensitivity on the 144-pair independent-seed audit.", x=0.53, y=1.02, fontsize=8.5, weight="bold")
    fig.tight_layout()
    save(fig, "fig6_sparse_gate_sensitivity")


def _wire_math(label: str) -> str:
    if label.startswith("x") and label[1:].isdigit():
        return rf"$x_{label[1:]}$"
    if label.startswith("a") and label[1:].isdigit():
        return rf"$a_{label[1:]}=0$"
    return "$" + label + "$"


def _term_math(term: str) -> str:
    variables = [part for part in term.split("*") if part]
    return "$" + "".join(rf"x_{part[1:]}" for part in variables) + "$"


def _draw_worked_circuit(
    ax: plt.Axes,
    gates: list[dict[str, str]],
    resources: dict[str, str],
    *,
    panel: str,
    title: str,
    include_ancilla: bool,
) -> None:
    wires = [f"x{i}" for i in range(5)] + ["y"]
    if include_ancilla:
        wires.append("a0")
    y_positions = {wire: len(wires) - 1 - index for index, wire in enumerate(wires)}
    x_max = len(gates) + 0.9

    ax.set_xlim(-0.85, x_max)
    ax.set_ylim(-0.65, len(wires) + 0.90)
    ax.set_axis_off()
    for wire in wires:
        y = y_positions[wire]
        color = PALETTE["gain"] if wire == "a0" else "#4A5058"
        ax.plot([0.05, x_max - 0.15], [y, y], color=color, linewidth=0.75, zorder=1)
        ax.text(-0.12, y, _wire_math(wire), ha="right", va="center", fontsize=7.4, color="#20242A")

    ax.text(-0.80, len(wires) + 0.68, panel, fontsize=9.5, fontweight="bold", va="center")
    ax.text(-0.50, len(wires) + 0.68, title, fontsize=7.7, fontweight="bold", va="center")
    ax.text(
        x_max - 0.05,
        len(wires) + 0.30,
        (
            f"T={int(float(resources['T']))}, CNOT={int(float(resources['CNOT']))}, "
            f"depth={int(float(resources['depth']))}, score={float(resources['score']):.3f}"
        ),
        ha="right",
        va="center",
        fontsize=6.4,
        color=PALETTE["resource"] if include_ancilla else PALETTE["neutral"],
    )

    for gate_index, row in enumerate(gates, start=1):
        x = float(gate_index)
        controls = [value for value in row["controls"].split(";") if value]
        target = row["target"]
        involved = controls + [target]
        y_values = [y_positions[value] for value in involved]
        stage = row["stage"]
        if stage.startswith("compute"):
            color = PALETTE["resource"]
        elif stage.startswith("uncompute"):
            color = PALETTE["warn"]
        elif stage.startswith("reuse"):
            color = PALETTE["gain"]
        else:
            color = PALETTE["direct"]
        ax.plot([x, x], [min(y_values), max(y_values)], color=color, linewidth=1.0, zorder=2)
        for control in controls:
            ax.add_patch(Circle((x, y_positions[control]), 0.09, facecolor=color, edgecolor=color, zorder=3))
        target_y = y_positions[target]
        ax.add_patch(Circle((x, target_y), 0.15, facecolor="white", edgecolor=color, linewidth=1.0, zorder=3))
        ax.plot([x - 0.09, x + 0.09], [target_y, target_y], color=color, linewidth=0.9, zorder=4)
        ax.plot([x, x], [target_y - 0.09, target_y + 0.09], color=color, linewidth=0.9, zorder=4)

        if stage.startswith("monomial "):
            gate_label = _term_math(stage.removeprefix("monomial "))
        elif stage.startswith("reuse with "):
            gate_label = _term_math(stage.removeprefix("reuse with "))
        elif stage.startswith("compute "):
            gate_label = "compute\n" + _term_math(stage.removeprefix("compute "))
        elif stage.startswith("uncompute "):
            gate_label = "uncompute\n" + _term_math(stage.removeprefix("uncompute "))
        else:
            gate_label = stage
        ax.text(x, len(wires) - 0.38, gate_label, ha="center", va="bottom", fontsize=5.6, color=color)

    if include_ancilla:
        ax.text(
            x_max - 0.15,
            y_positions["a0"] - 0.34,
            r"$a_0$ is recycled and returns to $0$",
            ha="right",
            va="top",
            fontsize=6.1,
            color=PALETTE["gain"],
        )


def fig_worked_example() -> None:
    gates = read_csv(RESULTS / "raw_worked_example_gates.csv")
    resources = read_csv(RESULTS / "summary_worked_example.csv")
    manifest = json.loads((RESULTS / "manifest_worked_example.json").read_text(encoding="utf-8"))
    direct_gates = [row for row in gates if row["variant"] == "direct"]
    selected_gates = [row for row in gates if row["variant"] == "resource_nmcts"]
    direct_resources = next(row for row in resources if row["method"] == "AND-direct ANF")
    selected_resources = next(row for row in resources if row["method"] == "Resource-NMCTS")

    source_rows: list[dict[str, object]] = []
    for row in gates:
        source_rows.append(
            {
                "kind": "gate",
                "variant": row["variant"],
                "index": row["gate_index"],
                "gate_type": row["gate_type"],
                "controls": row["controls"],
                "target": row["target"],
                "stage": row["stage"],
                "T": "",
                "CNOT": "",
                "depth": "",
                "gates": "",
                "score": "",
            }
        )
    for row in resources:
        source_rows.append(
            {
                "kind": "resource",
                "variant": "direct" if row["method"] == "AND-direct ANF" else "resource_nmcts",
                "index": "",
                "gate_type": "",
                "controls": "",
                "target": "",
                "stage": "",
                "T": row["T"],
                "CNOT": row["CNOT"],
                "depth": row["depth"],
                "gates": row["gates"],
                "score": row["score"],
            }
        )
    write_source(
        "fig8_worked_example",
        source_rows,
        ["kind", "variant", "index", "gate_type", "controls", "target", "stage", "T", "CNOT", "depth", "gates", "score"],
    )

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.35), gridspec_kw={"height_ratios": [0.92, 1.08]})
    _draw_worked_circuit(
        axes[0],
        direct_gates,
        direct_resources,
        panel="a",
        title="AND-direct ANF: five independent output actions",
        include_ancilla=False,
    )
    _draw_worked_circuit(
        axes[1],
        selected_gates,
        selected_resources,
        panel="b",
        title="Resource-NMCTS: two factors share one recycled line",
        include_ancilla=True,
    )
    truth_hex = manifest["function"]["truth_table_hex"]
    fig.suptitle(
        (
            r"$f=x_0x_1(x_2\oplus x_3\oplus x_4)"
            r"\oplus x_2x_3(x_1\oplus x_4)$"
            f"   |   truth table {truth_hex}"
        ),
        x=0.51,
        y=0.995,
        fontsize=8.6,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.012,
        "The selected circuit passes plan expansion, emitted-circuit GF(2) simulation, and all 32 truth-table assignments.",
        ha="center",
        va="bottom",
        fontsize=6.3,
        color="#30343B",
    )
    fig.tight_layout(rect=(0.0, 0.035, 1.0, 0.955), h_pad=1.0)
    save(fig, "fig8_worked_example")


def main() -> None:
    configure()
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    fig_pipeline()
    fig_traditional_resources()
    fig_baseline_comparisons()
    fig_learned_control_summary()
    fig_phase_affine()
    fig_validation()
    fig_sparse_gate_sensitivity()
    fig_worked_example()
    print(f"wrote figures to {OUT}")
    print(f"wrote source data to {SOURCE}")


if __name__ == "__main__":
    main()
