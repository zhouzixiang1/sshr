#!/usr/bin/env python3
"""Build a reviewer-facing audit of high-dimensional scale evidence.

The table deliberately separates three quantities that are easy to conflate:
generated functions or settings, method rows, and verified rows.  It also
reports resource means only for the representative paper-facing method in each
slice, rather than averaging unrelated baselines into one number.
"""
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key, "") != ""]
    return sum(values) / len(values) if values else 0.0


def fmt_float(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def verified_count(rows: list[dict[str, str]], keys: tuple[str, ...]) -> int:
    total = 0
    for row in rows:
        ok = True
        for key in keys:
            if key not in row or row[key] == "":
                continue
            if row[key] not in ("True", "true", "1"):
                ok = False
                break
        if ok:
            total += 1
    return total


def resource_summary(rows: list[dict[str, str]], time_key: str = "time_s") -> str:
    return (
        f"score {fmt_float(mean(rows, 'score'))}; "
        f"T/CNOT/depth {fmt_float(mean(rows, 'T'), 0)}/"
        f"{fmt_float(mean(rows, 'CNOT'), 0)}/{fmt_float(mean(rows, 'depth'), 0)}; "
        f"anc. {fmt_float(mean(rows, 'peak_ancilla'), 1)}; "
        f"time {fmt_float(mean(rows, time_key), 2)}s"
    )


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )
    replacements = {
        "n=20,28,40": r"$n=20,28,40$",
        "n=21--26": r"$n=21$--$26$",
        "n=21--25": r"$n=21$--$25$",
        "n=24,28,32,40": r"$n=24,28,32,40$",
        "n=20--40": r"$n=20$--$40$",
        "T/CNOT/depth": r"$T$/CNOT/depth",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def compact_scope_tex(text: str) -> str:
    if text == "n=24,28,32,40":
        return r"$24,28,32,40$"
    if text == "n=20,28,40":
        return r"$20,28,40$"
    if text == "n=48,56,64":
        return r"$48,56,64$"
    if text == "n=21--26":
        return r"$21$--$26$"
    if text == "n=21--25":
        return r"$21$--$25$"
    return tex_escape(text)


def build_rows() -> list[dict[str, str]]:
    scale_rows = read_csv(RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv")
    scale_rep = [row for row in scale_rows if row["method"] == "depth_frontier_policy"]

    staged_all = read_csv(RESULTS / "raw_stage_gated_frontier.csv")
    staged_rows = [row for row in staged_all if row["source"] == "scale_generalization"]
    run_depth4 = sum(1 for row in staged_rows if row["run_depth4"] == "1")

    width_rows: list[dict[str, str]] = []
    width6_rows: list[dict[str, str]] = []
    width_function_settings = 0
    for width in (6, 12, 24):
        rows = read_csv(RESULTS / f"raw_screen_scale_width{width}_probe_terms.csv")
        width_rows.extend(rows)
        width_function_settings += len({row["name"] for row in rows})
        if width == 6:
            width6_rows = [row for row in rows if row["method"] == "adaptive_all_depth"]

    truth_rows: list[dict[str, str]] = []
    for filename in (
        "raw_truth_bridge_terms.csv",
        "raw_truth_bridge_n23_terms.csv",
        "raw_truth_bridge_n23_large_frontier_terms.csv",
        "raw_truth_bridge_n23_cost_time003_frontier_terms.csv",
        "raw_truth_bridge_n24_terms.csv",
        "raw_truth_bridge_n25_terms.csv",
        "raw_truth_bridge_n26_terms.csv",
    ):
        truth_rows.extend(read_csv(RESULTS / filename))
    truth_rep = [row for row in truth_rows if row["method"] == "depth_frontier_policy"]
    truth_settings = len(truth_rows) // len({row["method"] for row in truth_rows})

    ultra_rows = read_csv(RESULTS / "raw_screen_scale_ultra_scale64_terms.csv")
    ultra_rep = [row for row in ultra_rows if row["method"] == "depth_frontier_policy"]

    return [
        {
            "slice": "Large term-set frontier",
            "n_scope": "n=24,28,32,40",
            "function_or_setting_count": str(len({row["name"] for row in scale_rows})),
            "method_rows": str(len(scale_rows)),
            "verified_rows": str(verified_count(scale_rows, ("anf_verified", "circuit_anf_verified"))),
            "verification": "symbolic plan+circuit ANF",
            "representative": "depth_frontier_policy",
            "representative_rows": str(len(scale_rep)),
            "mean_score": fmt_float(mean(scale_rep, "score")),
            "mean_T": fmt_float(mean(scale_rep, "T"), 0),
            "mean_CNOT": fmt_float(mean(scale_rep, "CNOT"), 0),
            "mean_depth": fmt_float(mean(scale_rep, "depth"), 0),
            "mean_peak_ancilla": fmt_float(mean(scale_rep, "peak_ancilla"), 1),
            "mean_time_s": fmt_float(mean(scale_rep, "time_s"), 2),
            "resource_text": resource_summary(scale_rep),
            "extra": "96 functions x 10 methods",
            "boundary": "Term-set validation; no full truth table beyond bridge slices.",
        },
        {
            "slice": "Stage-gated frontier",
            "n_scope": "n=24,28,32,40",
            "function_or_setting_count": str(len({row["name"] for row in staged_rows})),
            "method_rows": str(len(staged_rows)),
            "verified_rows": str(verified_count(staged_rows, ("verified",))),
            "verification": "symbolic selected plan",
            "representative": "stage_gated_frontier",
            "representative_rows": str(len(staged_rows)),
            "mean_score": fmt_float(mean(staged_rows, "score")),
            "mean_T": fmt_float(mean(staged_rows, "T"), 0),
            "mean_CNOT": fmt_float(mean(staged_rows, "CNOT"), 0),
            "mean_depth": fmt_float(mean(staged_rows, "depth"), 0),
            "mean_peak_ancilla": fmt_float(mean(staged_rows, "peak_ancilla"), 1),
            "mean_time_s": fmt_float(mean(staged_rows, "time_s"), 2),
            "resource_text": resource_summary(staged_rows),
            "extra": f"depth-4 evaluated on {run_depth4}/{len(staged_rows)} rows",
            "boundary": "Controller audit; still term-set symbolic verification.",
        },
        {
            "slice": "Action-width probe",
            "n_scope": "n=20,28,40",
            "function_or_setting_count": str(width_function_settings),
            "method_rows": str(len(width_rows)),
            "verified_rows": str(verified_count(width_rows, ("anf_verified", "circuit_anf_verified"))),
            "verification": "symbolic plan+circuit ANF",
            "representative": "width6 adaptive_all_depth",
            "representative_rows": str(len(width6_rows)),
            "mean_score": fmt_float(mean(width6_rows, "score")),
            "mean_T": fmt_float(mean(width6_rows, "T"), 0),
            "mean_CNOT": fmt_float(mean(width6_rows, "CNOT"), 0),
            "mean_depth": fmt_float(mean(width6_rows, "depth"), 0),
            "mean_peak_ancilla": fmt_float(mean(width6_rows, "peak_ancilla"), 1),
            "mean_time_s": fmt_float(mean(width6_rows, "time_s"), 2),
            "resource_text": resource_summary(width6_rows),
            "extra": "widths 6/12/24; 72 functions per width",
            "boundary": "Sensitivity check; wider root screens are not claimed as better.",
        },
        {
            "slice": "Ultra-scale term-set stress",
            "n_scope": "n=48,56,64",
            "function_or_setting_count": str(len({row["name"] for row in ultra_rows})),
            "method_rows": str(len(ultra_rows)),
            "verified_rows": str(verified_count(ultra_rows, ("anf_verified", "circuit_anf_verified"))),
            "verification": "symbolic plan+circuit ANF",
            "representative": "depth_frontier_policy",
            "representative_rows": str(len(ultra_rep)),
            "mean_score": fmt_float(mean(ultra_rep, "score")),
            "mean_T": fmt_float(mean(ultra_rep, "T"), 0),
            "mean_CNOT": fmt_float(mean(ultra_rep, "CNOT"), 0),
            "mean_depth": fmt_float(mean(ultra_rep, "depth"), 0),
            "mean_peak_ancilla": fmt_float(mean(ultra_rep, "peak_ancilla"), 1),
            "mean_time_s": fmt_float(mean(ultra_rep, "time_s"), 2),
            "resource_text": resource_summary(ultra_rep),
            "extra": "48 functions x 10 methods",
            "boundary": "Ultra-scale symbolic stress; no truth-table enumeration.",
        },
        {
            "slice": "Complete truth-table bridge",
            "n_scope": "n=21--26",
            "function_or_setting_count": str(truth_settings),
            "method_rows": str(len(truth_rows)),
            "verified_rows": str(
                verified_count(truth_rows, ("truth_verified", "anf_verified", "circuit_anf_verified"))
            ),
            "verification": "truth table + symbolic plan+circuit",
            "representative": "depth_frontier_policy",
            "representative_rows": str(len(truth_rep)),
            "mean_score": fmt_float(mean(truth_rep, "score")),
            "mean_T": fmt_float(mean(truth_rep, "T"), 0),
            "mean_CNOT": fmt_float(mean(truth_rep, "CNOT"), 0),
            "mean_depth": fmt_float(mean(truth_rep, "depth"), 0),
            "mean_peak_ancilla": fmt_float(mean(truth_rep, "peak_ancilla"), 1),
            "mean_time_s": fmt_float(mean(truth_rep, "plan_time_s"), 2),
            "resource_text": resource_summary(truth_rep, "plan_time_s")
            + f"; truth check {fmt_float(mean(truth_rep, 'truth_verify_time_s'), 2)}s",
            "extra": "46 function/settings x 10 methods",
            "boundary": "Complete checking on generated bridge slices only.",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "slice",
        "n_scope",
        "function_or_setting_count",
        "method_rows",
        "verified_rows",
        "verification",
        "representative",
        "representative_rows",
        "mean_score",
        "mean_T",
        "mean_CNOT",
        "mean_depth",
        "mean_peak_ancilla",
        "mean_time_s",
        "resource_text",
        "extra",
        "boundary",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Scaling and Resource Audit",
        "",
        "This audit separates generated functions/settings, method rows, verified rows, and representative resource means.",
        "The representative resources are method-specific and should not be read as averages over all baselines.",
        "",
        "| slice | n scope | functions/settings | rows verified | representative resources | boundary |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["slice"],
                    row["n_scope"],
                    row["function_or_setting_count"],
                    f"{row['verified_rows']}/{row['method_rows']}",
                    row["resource_text"],
                    row["boundary"],
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.17\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedleft\arraybackslash}p{0.10\linewidth}>{\raggedleft\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}p{0.27\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Slice & $n$ & Fn./settings & Rows verified & Representative resource mean & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["slice"]),
                    compact_scope_tex(row["n_scope"]),
                    row["function_or_setting_count"],
                    f"{row['verified_rows']}/{row['method_rows']}",
                    tex_escape(row["resource_text"]),
                    tex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_scaling_resource_audit.csv", rows)
    write_markdown(RESULTS / "analysis_scaling_resource_audit.md", rows)
    write_latex(TABLES / "scaling_resource_audit.tex", rows)
    print(f"wrote {len(rows)} scaling-resource audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
