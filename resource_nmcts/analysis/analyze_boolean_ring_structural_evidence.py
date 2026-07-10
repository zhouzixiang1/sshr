#!/usr/bin/env python3
"""Assemble Boolean-ring structural-search evidence from focused summaries.

This audit collects the high-dimensional Boolean-ring and Boolean-screen
comparisons that were previously scattered across focused analyses.  The goal is
to expose where structural actions improve resource quality, where a gate can
skip expensive work without changing the selected circuit, and where a fast
screen is only a speed baseline rather than a quality improvement.
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


def metric_row(path: Path, metric: str) -> dict[str, str]:
    for row in read_csv(path):
        if row.get("metric") == metric:
            return row
    raise KeyError(f"{path}: missing metric {metric}")


def pct(row: dict[str, str]) -> float:
    return float(row["mean_relative_pct"])


def pct_text(value: float) -> str:
    return f"{value:+.2f}%"


def wlt(row: dict[str, str]) -> str:
    return f"{row['wins']}/{row['losses']}/{row['ties']}"


def build_rows() -> list[dict[str, str]]:
    specs = [
        {
            "slice": "n=14",
            "comparison": "Boolean guard vs pairwise-wide",
            "summary": "summary_highdim_boolean_guard_vs_pairwise_wide.csv",
            "interpretation": "quality gain; slower exhaustive guard",
        },
        {
            "slice": "n=16",
            "comparison": "Boolean guard vs pairwise-wide",
            "summary": "summary_ultra_boolean_guard_vs_pairwise_wide.csv",
            "interpretation": "quality gain; slower guard",
        },
        {
            "slice": "n=16",
            "comparison": "Boolean guard vs deterministic deep",
            "summary": "summary_ultra_boolean_guard_vs_old_deep.csv",
            "interpretation": "stronger quality branch; expensive",
        },
        {
            "slice": "n=16",
            "comparison": "Boolean-linear deep vs pairwise-wide",
            "summary": "summary_ultra_boolean_linear_vs_pairwise_resource.csv",
            "interpretation": "fast structural variant with small quality gain",
        },
        {
            "slice": "n=20",
            "comparison": "Resource update vs Boolean screen",
            "summary": "summary_giga_resource_vs_boolean_screen.csv",
            "interpretation": "quality frontier; much slower",
        },
        {
            "slice": "n=20",
            "comparison": "Screen gate vs full Resource",
            "summary": "summary_giga_screen_gate_vs_resource.csv",
            "interpretation": "safe skip: same resources, less planning time",
        },
        {
            "slice": "n=20",
            "comparison": "Recursive Boolean screen vs old Resource",
            "summary": "summary_giga_screen_deeper_vs_old_resource.csv",
            "interpretation": "large-n positive screen; ancilla tradeoff",
        },
        {
            "slice": "n=18",
            "comparison": "Recursive Boolean screen vs old Resource",
            "summary": "summary_mega_screen_deep_vs_old_resource.csv",
            "interpretation": "speed-only negative control; not promoted",
        },
    ]

    rows: list[dict[str, str]] = []
    for spec in specs:
        path = RESULTS / spec["summary"]
        score = metric_row(path, "score")
        t_count = metric_row(path, "T")
        cnot = metric_row(path, "CNOT")
        depth = metric_row(path, "depth")
        ancilla = metric_row(path, "peak_ancilla")
        time_s = metric_row(path, "time_s")
        rows.append(
            {
                "slice": spec["slice"],
                "comparison": spec["comparison"],
                "pairs": score["pairs"],
                "score_wlt": wlt(score),
                "score_mean_relative_pct": pct_text(pct(score)),
                "t_mean_relative_pct": pct_text(pct(t_count)),
                "cnot_mean_relative_pct": pct_text(pct(cnot)),
                "depth_mean_relative_pct": pct_text(pct(depth)),
                "ancilla_mean_relative_pct": pct_text(pct(ancilla)),
                "time_mean_relative_pct": pct_text(pct(time_s)),
                "interpretation": spec["interpretation"],
                "source": str(path.relative_to(THIS_DIR)),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "slice",
        "comparison",
        "pairs",
        "score_wlt",
        "score_mean_relative_pct",
        "t_mean_relative_pct",
        "cnot_mean_relative_pct",
        "depth_mean_relative_pct",
        "ancilla_mean_relative_pct",
        "time_mean_relative_pct",
        "interpretation",
        "source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Boolean-Ring Structural Evidence",
        "",
        "This audit consolidates high-dimensional Boolean-ring and Boolean-screen comparisons.",
        "Negative relative changes favor the first method in the comparison.",
        "",
        "| slice | comparison | pairs | score W/L/T | mean score change | mean T change | mean CNOT change | mean depth change | mean ancilla change | mean time change | interpretation |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["slice"],
                    row["comparison"],
                    row["pairs"],
                    row["score_wlt"],
                    row["score_mean_relative_pct"],
                    row["t_mean_relative_pct"],
                    row["cnot_mean_relative_pct"],
                    row["depth_mean_relative_pct"],
                    row["ancilla_mean_relative_pct"],
                    row["time_mean_relative_pct"],
                    row["interpretation"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Boolean-ring guards improve score on the n=14 and n=16 slices, but the more exhaustive guard is slower.",
            "- The n=20 screen gate preserves the full Resource-NMCTS resource vector while reducing planning time.",
            "- The n=18 recursive screen row is a useful negative control: it is much faster but worse in score, so it should not be promoted as a quality result.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
    for old, new in [
        ("n=14", r"$n=14$"),
        ("n=16", r"$n=16$"),
        ("n=18", r"$n=18$"),
        ("n=20", r"$n=20$"),
    ]:
        escaped = escaped.replace(old, new)
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.09\linewidth}>{\raggedright\arraybackslash}p{0.25\linewidth}r>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Slice & Comparison & Pairs & Score W/L/T & Mean $\Delta$ score & Mean $\Delta$ time & Interpretation \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["slice"]),
                    tex_escape(row["comparison"]),
                    tex_escape(row["pairs"]),
                    tex_escape(row["score_wlt"]),
                    tex_escape(row["score_mean_relative_pct"]),
                    tex_escape(row["time_mean_relative_pct"]),
                    tex_escape(row["interpretation"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_boolean_ring_structural_evidence.csv", rows)
    write_markdown(RESULTS / "analysis_boolean_ring_structural_evidence.md", rows)
    write_latex(TABLES / "boolean_ring_structural_evidence.tex", rows)
    print(f"wrote {len(rows)} Boolean-ring structural evidence rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
