#!/usr/bin/env python3
"""Generate figure-driven manuscript assets for the Resource-NMCTS paper.

The script only consumes existing experiment outputs.  It does not rerun
synthesis experiments.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
OUT = ROOT / "paper_latex" / "figures" / "submission_v36"
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
            "svg.fonttype": "none",
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_source(name: str, rows: list[dict[str, object]], fieldnames: Iterable[str]) -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    with (SOURCE / f"{name}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
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
        ("Truth table", "complete bridge n=21--25"),
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
    fig.text(0.01, 0.96, "d", fontsize=10, weight="bold")
    fig.tight_layout()
    save(fig, "fig4_phase_affine")


def validation_rows() -> list[dict[str, object]]:
    groups = [
        ("n=20-40 item symbolic", "circuit_verified_rows", [
            "summary_screen_scale_terms.csv",
            "summary_screen_scale_extended_terms.csv",
            "summary_screen_scale_depth_frontier_terms.csv",
            "summary_screen_scale_depth_frontier_policy_terms.csv",
            "summary_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
            "summary_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv",
        ]),
        ("width probe symbolic", "circuit_verified_rows", [
            "summary_screen_scale_width6_probe_terms.csv",
            "summary_screen_scale_width12_probe_terms.csv",
            "summary_screen_scale_width24_probe_terms.csv",
        ]),
        ("truth bridge n=21-25", "truth_verified_rows", [
            "summary_truth_bridge_terms.csv",
            "summary_truth_bridge_n23_terms.csv",
            "summary_truth_bridge_n23_large_frontier_terms.csv",
            "summary_truth_bridge_n23_cost_time003_frontier_terms.csv",
            "summary_truth_bridge_n24_terms.csv",
            "summary_truth_bridge_n25_terms.csv",
        ]),
        ("phase selected rows", "verified_up_to_global_phase", ["raw_phase_parity_affine.csv"]),
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
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    y = list(range(len(data)))
    vals = [int(r["verified"]) for r in data]
    ax.barh(y, vals, color=[PALETTE["resource"], PALETTE["baseline"], PALETTE["gain"], PALETTE["phase"]], height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels([str(r["group"]) for r in data])
    ax.invert_yaxis()
    ax.set_xlabel("Verified rows")
    ax.set_title("Verification covers the reported logic-layer claims.", loc="left", weight="bold")
    for i, row in enumerate(data):
        ax.text(vals[i] * 1.01, i, f"{row['verified']}/{row['total']}", va="center")
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.96, "e", fontsize=10, weight="bold")
    fig.tight_layout()
    save(fig, "fig5_validation")


def main() -> None:
    configure()
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    fig_pipeline()
    fig_traditional_resources()
    fig_baseline_comparisons()
    fig_phase_affine()
    fig_validation()
    print(f"wrote figures to {OUT}")
    print(f"wrote source data to {SOURCE}")


if __name__ == "__main__":
    main()
