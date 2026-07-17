#!/usr/bin/env python3
"""Summarize workstation runtime evidence across the submission package.

The audit is descriptive and deliberately bounded.  It consolidates wall-clock
times from existing raw CSVs so the paper can show the practical execution
envelope without turning workstation timing into a portable algorithmic claim.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANONYMOUS = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TQC = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

SUMMARY = RESULTS / "summary_runtime_envelope_audit.csv"
ANALYSIS = RESULTS / "analysis_runtime_envelope_audit.md"
MANIFEST = RESULTS / "manifest_runtime_envelope_audit.json"
TABLE = TABLES / "runtime_envelope_audit.tex"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def qtile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def fmt(value: float, digits: int = 2) -> str:
    if math.isnan(value):
        return "n/a"
    return f"{value:.{digits}f}"


def stats(values: list[float]) -> dict[str, str]:
    if not values:
        return {"median_s": "n/a", "p95_s": "n/a", "max_s": "n/a"}
    return {
        "median_s": fmt(median(values)),
        "p95_s": fmt(qtile(values, 0.95)),
        "max_s": fmt(max(values)),
    }


def is_ok(row: dict[str, str]) -> bool:
    if row.get("skipped"):
        return False
    if row.get("error"):
        return False
    for key in ("correct", "truth_verified", "anf_verified", "circuit_anf_verified"):
        if key in row and row.get(key, "") not in ("", "True", "true", "1"):
            return False
    return True


def time_values(rows: list[dict[str, str]], key: str = "time_s") -> list[float]:
    return [value for row in rows if (value := num(row, key)) is not None]


def truth_bridge_rows() -> list[dict[str, str]]:
    filenames = [
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
    ]
    rows: list[dict[str, str]] = []
    for filename in filenames:
        rows.extend(read_csv(RESULTS / filename))
    return rows


def pass_row(
    slice_name: str,
    scope: str,
    rows: list[dict[str, str]],
    time_key: str,
    evidence: str,
    boundary: str,
    extra_times: dict[str, list[float]] | None = None,
) -> dict[str, str]:
    values = time_values(rows, time_key)
    timing = stats(values)
    if extra_times:
        extras = "; ".join(f"{label} median={fmt(median(vals))}s" for label, vals in extra_times.items() if vals)
        if extras:
            timing_text = f"median={timing['median_s']}s; p95={timing['p95_s']}s; max={timing['max_s']}s; {extras}"
        else:
            timing_text = f"median={timing['median_s']}s; p95={timing['p95_s']}s; max={timing['max_s']}s"
    else:
        timing_text = f"median={timing['median_s']}s; p95={timing['p95_s']}s; max={timing['max_s']}s"
    ok_count = sum(1 for row in rows if is_ok(row))
    return {
        "slice": slice_name,
        "scope": scope,
        "rows": str(len(rows)),
        "verified_or_correct": str(ok_count),
        "time_key": time_key,
        "median_s": timing["median_s"],
        "p95_s": timing["p95_s"],
        "max_s": timing["max_s"],
        "time_evidence": timing_text,
        "evidence": evidence,
        "boundary": boundary,
        "status": "pass" if rows and ok_count == len(rows) and values else "needs revision",
    }


def build_rows() -> list[dict[str, str]]:
    traditional = read_csv(RESULTS / "raw_traditional_resource.csv")
    pareto = [row for row in traditional if row.get("method") == "and_pareto_resource_nmcts"]

    external_files = [
        "raw_ros_lut_proxy_best.csv",
        "raw_caterpillar_xag_api_best.csv",
        "raw_mockturtle_xag_probe.csv",
        "raw_cirkit_aig_probe.csv",
        "raw_revkit_cli_multiflow_traditional.csv",
    ]
    external: list[dict[str, str]] = []
    external_counts: list[str] = []
    for filename in external_files:
        path = RESULTS / filename
        if not path.exists():
            continue
        rows = read_csv(path)
        external.extend(rows)
        external_counts.append(f"{filename.removeprefix('raw_').removesuffix('.csv')}={len(rows)}")

    symbolic_rows = read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv")
    symbolic_rows += read_csv(RESULTS / "raw_screen_scale_ultra_scale64_terms.csv")
    frontier_rows = [row for row in symbolic_rows if row.get("method") == "depth_frontier_policy"]

    bridge = truth_bridge_rows()
    bridge_frontier = [row for row in bridge if row.get("method") == "depth_frontier_policy"]

    budget = read_csv(RESULTS / "raw_bitflip_neural_budget_sweep.csv")
    budget_pareto = [row for row in budget if row.get("method") == "and_pareto_resource_nmcts"]
    mcts_budget_decisions = read_csv(RESULTS / "raw_mcts_budget_policy_decisions.csv")

    learned_summary = read_csv(RESULTS / "summary_learned_control_audit.csv")
    learned_costs = [
        row["cost"]
        for row in learned_summary
        if row.get("cost")
        and row.get("component")
        in {
            "Depth-frontier policy",
            "Sparse depth-4 gate",
            "Bit-flip low-budget prior",
            "Contextual-bandit Pareto budget policy",
        }
    ]

    return [
        pass_row(
            "Traditional n<=6 Resource-NMCTS",
            "177 matched benchmark functions",
            pareto,
            "time_s",
            "Pareto-Resource-NMCTS rows are correct on the small-function resource slice.",
            "Small-function timing context only; headline claims are paired logical-resource improvements.",
        ),
        pass_row(
            "External logic-tool probes",
            "ROS-style LUT, Caterpillar, mockturtle, CirKit, RevKit",
            external,
            "time_s",
            "; ".join(external_counts),
            "Tool rows are bounded logic-level probes or exact-oracle probes, not hardware-mapped baselines.",
        ),
        pass_row(
            "High-dimensional symbolic frontier",
            "n=24,28,32,40 plus n=48,56,64",
            frontier_rows,
            "time_s",
            "Depth-frontier policy rows selected from symbolic plan+circuit ANF verification slices.",
            "Symbolic emitted-circuit checks; no exhaustive truth tables outside bridge slices.",
        ),
        pass_row(
            "Complete truth-table bridge",
            "n=21--30 generated bridge slices",
            bridge_frontier,
            "plan_time_s",
            "Depth-frontier policy rows include truth-table, plan, and emitted-circuit checks.",
            "Complete checking is limited to generated bridge slices and is not global high-dimensional enumeration.",
            extra_times={"truth_verify": time_values(bridge_frontier, "truth_verify_time_s")},
        ),
        pass_row(
            "Learned-control runtime boundary",
            "compressed bit-flip budgets plus promoted learned controls",
            budget_pareto,
            "time_s",
            "Low-budget Pareto learned-prior rows are correct; selected learned-control cost rows: "
            + "; ".join(learned_costs),
            "Learned controls are quality/budget evidence with explicit overhead or savings, not a blanket speedup claim.",
            extra_times={
                "fitted-Q policy": time_values(mcts_budget_decisions, "policy_time_s"),
                "always-Pareto": time_values(mcts_budget_decisions, "pareto_time_s"),
            },
        ),
    ]


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("n<=6", r"$n\leq6$")
    text = text.replace("n=24,28,32,40", r"$n=24,28,32,40$")
    text = text.replace("n=48,56,64", r"$n=48,56,64$")
    text = text.replace("n=21--30", r"$n=21$--$30$")
    return text


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "slice",
        "scope",
        "rows",
        "verified_or_correct",
        "time_key",
        "median_s",
        "p95_s",
        "max_s",
        "time_evidence",
        "evidence",
        "boundary",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Runtime Envelope Audit",
        "",
        "This audit summarizes workstation wall-clock evidence already present in raw CSV artifacts.",
        "It supports reproducibility and feasibility checks, not portable runtime-speedup claims.",
        "",
        "## Status counts",
        "",
    ]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(
        [
            "",
            "| slice | scope | rows ok | time evidence | boundary | status |",
            "|---|---|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['slice']} | {row['scope']} | {row['verified_or_correct']}/{row['rows']} | "
            f"{row['time_evidence']} | {row['boundary']} | {row['status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.19\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}r>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Slice & Scope & Rows ok & Runtime evidence and boundary \\",
        r"\midrule",
    ]
    for row in rows:
        detail = f"{row['time_evidence']}. {row['boundary']}"
        lines.append(
            f"{tex_escape(row['slice'])} & {tex_escape(row['scope'])} & "
            f"{row['verified_or_correct']}/{row['rows']} & {tex_escape(detail)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    text_by_path = {
        "author": PAPER.read_text(encoding="utf-8") if PAPER.exists() else "",
        "anonymous": ANONYMOUS.read_text(encoding="utf-8") if ANONYMOUS.exists() else "",
        "acm": ACM_TQC.read_text(encoding="utf-8") if ACM_TQC.exists() else "",
    }
    path.write_text(
        json.dumps(
            {
                "script": Path(__file__).name,
                "rows": len(rows),
                "status_counts": counts,
                "needs_revision_count": counts.get("needs revision", 0),
                "table_anchor_present": "tab:runtime-envelope-audit" in text_by_path["author"],
                "anonymous_table_anchor_present": "tab:runtime-envelope-audit" in text_by_path["anonymous"],
                "acm_table_anchor_present": "tab:runtime-envelope-audit" in text_by_path["acm"],
                "summary": str(SUMMARY.relative_to(THIS_DIR)),
                "analysis": str(ANALYSIS.relative_to(THIS_DIR)),
                "table": str(TABLE.relative_to(THIS_DIR)),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {len(rows)} runtime-envelope audit row(s)")


if __name__ == "__main__":
    main()
