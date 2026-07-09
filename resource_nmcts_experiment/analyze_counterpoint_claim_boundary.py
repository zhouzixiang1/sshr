#!/usr/bin/env python3
"""Build a counterpoint-and-claim-boundary audit table.

The comparison evidence matrix reports wins.  This companion audit reports the
strongest opposing evidence that should constrain the manuscript's claims:
SSHR is a CNOT counterpoint, CirKit is a depth counterpoint, RevKit is an
auxiliary-line counterpoint, learned priors are incremental, and large-scale
checks remain bounded by symbolic or bridge verification.
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


def falsey(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no"}


def usable(row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    for key in (
        "correct",
        "abc_blif_correct",
        "source_blif_correct",
        "verilog_correct",
        "anf_verified",
        "circuit_anf_verified",
        "verified_up_to_global_phase",
    ):
        if key in row and falsey(row.get(key)):
            return False
    return True


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_method(files: tuple[str, ...], method: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in files:
        for row in read_rows(RESULTS / name):
            if row.get("method") == method and usable(row):
                rows[row["name"]] = row
    return rows


def compare(
    target_files: tuple[str, ...],
    target: str,
    baseline_files: tuple[str, ...],
    baseline: str,
    metric: str,
) -> dict[str, object]:
    target_rows = read_method(target_files, target)
    baseline_rows = read_method(baseline_files, baseline)
    names = sorted(set(target_rows) & set(baseline_rows))
    wins = losses = ties = 0
    rels: list[float] = []
    for name in names:
        new = float(target_rows[name][metric])
        old = float(baseline_rows[name][metric])
        if metric == "time_s":
            denominator = old if abs(old) > 1.0e-12 else 1.0
        else:
            denominator = max(abs(old), 1.0)
        rels.append((new - old) / denominator * 100.0)
        if new < old - 1e-9:
            wins += 1
        elif new > old + 1e-9:
            losses += 1
        else:
            ties += 1
    mean = sum(rels) / len(rels) if rels else 0.0
    return {
        "pairs": len(names),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": mean,
    }


def fmt_cmp(item: dict[str, object]) -> str:
    return (
        f"{item['wins']}/{item['losses']}/{item['ties']}, "
        f"{float(item['mean_relative']):+.2f}%"
    )


def neural_prior_counterpoint() -> tuple[str, str]:
    score = compare(
        ("raw_traditional_resource_learned_prior.csv",),
        "and_pareto_resource_nmcts",
        ("raw_traditional_resource_no_prior.csv",),
        "and_pareto_resource_nmcts",
        "score",
    )
    time = compare(
        ("raw_traditional_resource_learned_prior.csv",),
        "and_pareto_resource_nmcts",
        ("raw_traditional_resource_no_prior.csv",),
        "and_pareto_resource_nmcts",
        "time_s",
    )
    favorable = f"score {fmt_cmp(score)}"
    opposing = f"time {fmt_cmp(time)} versus no-prior rerun"
    return favorable, opposing


def count_usable(files: tuple[str, ...]) -> str:
    total = 0
    ok = 0
    for name in files:
        rows = read_rows(RESULTS / name)
        total += len(rows)
        ok += sum(1 for row in rows if usable(row))
    return f"{ok}/{total}"


def build_rows() -> list[dict[str, str]]:
    traditional = ("raw_traditional_resource.csv",)
    external_n6 = ("raw_external_traditional_resource_n6.csv",)
    cirkit = ("raw_cirkit_aig_probe.csv",)
    revkit = ("raw_revkit_cli_multiflow_traditional.csv",)

    sshr_i_score = compare(
        traditional,
        "and_pareto_resource_nmcts",
        external_n6,
        "external_sshr_i_cnot",
        "score",
    )
    sshr_i_cnot = compare(
        traditional,
        "and_pareto_resource_nmcts",
        external_n6,
        "external_sshr_i_cnot",
        "CNOT",
    )
    sshr_h_score = compare(
        traditional,
        "and_pareto_resource_nmcts",
        traditional,
        "sshr_h",
        "score",
    )
    sshr_h_cnot = compare(
        traditional,
        "and_pareto_resource_nmcts",
        traditional,
        "sshr_h",
        "CNOT",
    )

    cirkit_score = compare(
        traditional,
        "and_pareto_resource_nmcts",
        cirkit,
        "external_cirkit_aig_mc",
        "score",
    )
    cirkit_depth = compare(
        traditional,
        "and_pareto_resource_nmcts",
        cirkit,
        "external_cirkit_aig_mc",
        "depth",
    )

    revkit_score = compare(
        traditional,
        "and_pareto_resource_nmcts",
        revkit,
        "external_revkit_cli_best_score",
        "score",
    )
    revkit_ancilla = compare(
        traditional,
        "and_pareto_resource_nmcts",
        revkit,
        "external_revkit_cli_best_score",
        "peak_ancilla",
    )

    neural_favorable, neural_opposing = neural_prior_counterpoint()

    highdim_symbolic = count_usable(
        (
            "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv",
            "raw_screen_scale_depth_frontier_terms.csv",
        )
    )
    truth_bridge = count_usable(
        (
            "raw_truth_bridge_terms.csv",
            "raw_truth_bridge_n23_terms.csv",
            "raw_truth_bridge_n23_large_frontier_terms.csv",
            "raw_truth_bridge_n23_cost_time003_frontier_terms.csv",
            "raw_truth_bridge_n24_terms.csv",
            "raw_truth_bridge_n25_terms.csv",
            "raw_truth_bridge_n26_terms.csv",
            "raw_truth_bridge_n27_terms.csv",
            "raw_truth_bridge_n28_terms.csv",
            "raw_truth_bridge_n29_terms.csv",
            "raw_truth_bridge_n30_terms.csv",
        )
    )

    return [
        {
            "counterpoint": "SSHR family CNOT optimum",
            "opposing_evidence": (
                f"vs SSHR-I CNOT: CNOT {fmt_cmp(sshr_i_cnot)}; "
                f"vs SSHR-H: CNOT {fmt_cmp(sshr_h_cnot)}"
            ),
            "favorable_evidence": (
                f"score vs SSHR-I CNOT {fmt_cmp(sshr_i_score)}; "
                f"score vs SSHR-H {fmt_cmp(sshr_h_score)}"
            ),
            "claim_boundary": "Use SSHR as a small-function CNOT counterpoint; claim T-count and weighted-score advantage, not CNOT dominance.",
        },
        {
            "counterpoint": "CirKit AIG/MC depth",
            "opposing_evidence": f"depth {fmt_cmp(cirkit_depth)}",
            "favorable_evidence": f"score {fmt_cmp(cirkit_score)}",
            "claim_boundary": "Use CirKit as a depth-oriented external probe; do not claim depth dominance over logic-network synthesis.",
        },
        {
            "counterpoint": "RevKit exact-oracle auxiliary lines",
            "opposing_evidence": f"peak ancilla {fmt_cmp(revkit_ancilla)}",
            "favorable_evidence": f"score {fmt_cmp(revkit_score)}",
            "claim_boundary": "Use RevKit CLI as an exact reversible-oracle probe; do not claim line-count or mapped Clifford+T dominance.",
        },
        {
            "counterpoint": "Learned prior is incremental",
            "opposing_evidence": neural_opposing,
            "favorable_evidence": neural_favorable,
            "claim_boundary": "Frame AI as search control, ranking, pruning, and gating; do not claim deep RL alone explains the main resource drop.",
        },
        {
            "counterpoint": "Large-n verification is bounded",
            "opposing_evidence": "complete truth-table enumeration is limited to bridge slices",
            "favorable_evidence": (
                f"symbolic scale rows {highdim_symbolic}; "
                f"complete truth-table bridge rows {truth_bridge}"
            ),
            "claim_boundary": "Claim logical correctness inside symbolic and bridge-verification envelopes, not exhaustive large-dimensional benchmarking.",
        },
    ]


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
        ("Resource-NMCTS", r"\method{}"),
        ("SSHR-I", "SSHR-I"),
        ("SSHR-H", "SSHR-H"),
        ("CNOT", "CNOT"),
        ("T-count", "T-count"),
        ("Clifford+T", "Clifford+T"),
        ("Large-n", r"Large-$n$"),
    ]
    for old, new in replacements:
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["counterpoint", "opposing_evidence", "favorable_evidence", "claim_boundary"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Counterpoint Claim-Boundary Audit",
        "",
        "This audit records the strongest opposing evidence that bounds the paper's comparison claims.",
        "",
        "| counterpoint | opposing evidence | favorable evidence | claim boundary |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {counterpoint} | {opposing_evidence} | {favorable_evidence} | {claim_boundary} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.24\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Counterpoint & Opposing evidence & Favorable evidence & Claim boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} \\\\".format(
                latex_cell(row["counterpoint"]),
                latex_cell(row["opposing_evidence"]),
                latex_cell(row["favorable_evidence"]),
                latex_cell(row["claim_boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    raise_csv_field_limit()
    rows = build_rows()
    write_csv(RESULTS / "summary_counterpoint_claim_boundary.csv", rows)
    write_markdown(RESULTS / "analysis_counterpoint_claim_boundary.md", rows)
    write_latex(TABLES / "counterpoint_claim_boundary.tex", rows)
    print(f"wrote {len(rows)} counterpoint claim-boundary row(s)")


if __name__ == "__main__":
    main()
