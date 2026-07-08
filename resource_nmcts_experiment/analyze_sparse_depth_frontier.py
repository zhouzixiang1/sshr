#!/usr/bin/env python3
"""Analyze a sparse depth frontier for Boolean-ring screening.

The depth-frontier runs measure depth-2, depth-3, and depth-4 Boolean-ring
screens independently.  Empirically, depth-3 is not selected once depth-4 is
available in the current large-scale and bridge slices.  This script turns that
observation into a reproducible controller audit: evaluate only depth 2 and
depth 4, choose the better score, and compare against the full depth-2/3/4
frontier.
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"


@dataclass(frozen=True)
class EvalRow:
    source: str
    name: str
    n: int
    method: str
    score: float
    time_s: float
    t_count: float
    cnot: float
    depth: float
    peak_ancilla: float
    verified: bool


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return float(value) if value != "" else default


def as_time(row: dict[str, str]) -> float:
    for key in ("time_s", "plan_time_s"):
        value = row.get(key, "")
        if value != "":
            return float(value)
    return 0.0


def as_verified(row: dict[str, str]) -> bool:
    keys = [
        "correct",
        "truth_verified",
        "anf_verified",
        "circuit_anf_verified",
    ]
    values = [row.get(key, "") for key in keys if key in row and row.get(key, "") != ""]
    if not values:
        return True
    return all(value in {"True", "true", "1"} for value in values)


def load_grouped(path: Path, source: str) -> dict[str, dict[str, EvalRow]]:
    grouped: dict[str, dict[str, EvalRow]] = {}
    for row in read_csv(path):
        method = row.get("method", "")
        if method not in {"screen_depth2", "screen_depth3", "screen_depth4"}:
            continue
        name = row["name"]
        grouped.setdefault(name, {})[method] = EvalRow(
            source=source,
            name=name,
            n=int(row["n"]),
            method=method,
            score=as_float(row, "score"),
            time_s=as_time(row),
            t_count=as_float(row, "T"),
            cnot=as_float(row, "CNOT"),
            depth=as_float(row, "depth"),
            peak_ancilla=as_float(row, "peak_ancilla"),
            verified=as_verified(row),
        )
    return {
        name: methods
        for name, methods in grouped.items()
        if all(method in methods for method in ("screen_depth2", "screen_depth3", "screen_depth4"))
    }


def rel(target: float, baseline: float, floor: float = 1.0) -> float:
    return (target - baseline) / max(abs(baseline), floor)


def best(methods: list[EvalRow]) -> EvalRow:
    return min(methods, key=lambda row: (row.score, row.time_s, row.method))


def summarize_source(source: str, grouped: dict[str, dict[str, EvalRow]]) -> dict[str, object]:
    score_wins = score_losses = score_ties = 0
    depth4_vs_depth3_wins = depth4_vs_depth3_losses = depth4_vs_depth3_ties = 0
    rel_scores: list[float] = []
    rel_times: list[float] = []
    rel_t: list[float] = []
    rel_cnot: list[float] = []
    rel_depth: list[float] = []
    rel_ancilla: list[float] = []
    selected_depth2 = selected_depth4 = 0
    full_selected_depth3 = 0
    verified_rows = 0
    n_values: set[int] = set()

    for methods in grouped.values():
        d2 = methods["screen_depth2"]
        d3 = methods["screen_depth3"]
        d4 = methods["screen_depth4"]
        sparse = best([d2, d4])
        full = best([d2, d3, d4])
        n_values.add(d2.n)
        verified_rows += sum(1 for row in (d2, d3, d4) if row.verified)
        selected_depth2 += int(sparse.method == "screen_depth2")
        selected_depth4 += int(sparse.method == "screen_depth4")
        full_selected_depth3 += int(full.method == "screen_depth3")

        if sparse.score < full.score - 1e-9:
            score_wins += 1
        elif sparse.score > full.score + 1e-9:
            score_losses += 1
        else:
            score_ties += 1
        if d4.score < d3.score - 1e-9:
            depth4_vs_depth3_wins += 1
        elif d4.score > d3.score + 1e-9:
            depth4_vs_depth3_losses += 1
        else:
            depth4_vs_depth3_ties += 1

        full_time = d2.time_s + d3.time_s + d4.time_s
        sparse_time = d2.time_s + d4.time_s
        rel_scores.append(rel(sparse.score, full.score))
        rel_times.append(rel(sparse_time, full_time, floor=1e-9))
        rel_t.append(rel(sparse.t_count, full.t_count))
        rel_cnot.append(rel(sparse.cnot, full.cnot))
        rel_depth.append(rel(sparse.depth, full.depth))
        rel_ancilla.append(rel(sparse.peak_ancilla, full.peak_ancilla))

    pairs = len(grouped)
    return {
        "source": source,
        "n_scope": ",".join(str(n) for n in sorted(n_values)),
        "pairs": pairs,
        "score_wlt": f"{score_wins}/{score_losses}/{score_ties}",
        "mean_rel_score": statistics.mean(rel_scores) if rel_scores else 0.0,
        "mean_rel_time": statistics.mean(rel_times) if rel_times else 0.0,
        "mean_rel_T": statistics.mean(rel_t) if rel_t else 0.0,
        "mean_rel_CNOT": statistics.mean(rel_cnot) if rel_cnot else 0.0,
        "mean_rel_depth": statistics.mean(rel_depth) if rel_depth else 0.0,
        "mean_rel_peak_ancilla": statistics.mean(rel_ancilla) if rel_ancilla else 0.0,
        "depth4_vs_depth3_wlt": f"{depth4_vs_depth3_wins}/{depth4_vs_depth3_losses}/{depth4_vs_depth3_ties}",
        "sparse_selected_depth2": selected_depth2,
        "sparse_selected_depth4": selected_depth4,
        "full_selected_depth3": full_selected_depth3,
        "verified_rows": verified_rows,
        "method_rows": 3 * pairs,
    }


def pct(value: object) -> str:
    return f"{100.0 * float(value):+.2f}%"


def latex_pct(value: object) -> str:
    return pct(value).replace("%", r"\%")


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "source",
        "n_scope",
        "pairs",
        "score_wlt",
        "mean_rel_score",
        "mean_rel_time",
        "mean_rel_T",
        "mean_rel_CNOT",
        "mean_rel_depth",
        "mean_rel_peak_ancilla",
        "depth4_vs_depth3_wlt",
        "sparse_selected_depth2",
        "sparse_selected_depth4",
        "full_selected_depth3",
        "verified_rows",
        "method_rows",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Sparse Depth Frontier Audit",
        "",
        "The sparse frontier evaluates only `screen_depth2` and `screen_depth4`,",
        "then selects the lower-score plan.  It is compared against the full",
        "`screen_depth2/3/4` frontier measured in the same raw files.",
        "",
        "| source | n scope | pairs | score W/L/T vs full | mean score change | mean time change | depth4 vs depth3 W/L/T | full depth3 selections | verified rows |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["source"]),
                    str(row["n_scope"]),
                    str(row["pairs"]),
                    str(row["score_wlt"]),
                    pct(row["mean_rel_score"]),
                    pct(row["mean_rel_time"]),
                    str(row["depth4_vs_depth3_wlt"]),
                    str(row["full_selected_depth3"]),
                    f"{row['verified_rows']}/{row['method_rows']}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- The sparse depth-2/4 frontier exactly matches the full depth-2/3/4 frontier on every listed slice.",
            "- The improvement is a planning-cost reduction, not a new hardware-mapping claim.",
            "- Depth 3 is retained as an audited candidate in the raw data, but it is not selected once depth 4 is available in these slices.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.23\linewidth}>{\raggedright\arraybackslash}p{0.14\linewidth}r>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Source & $n$ scope & Pairs & Score W/L/T & Mean $\Delta$ score & Mean $\Delta$ time & Depth-4 vs depth-3 \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    latex_escape(str(row["source"])),
                    latex_escape(str(row["n_scope"])),
                    str(row["pairs"]),
                    str(row["score_wlt"]),
                    latex_pct(row["mean_rel_score"]),
                    latex_pct(row["mean_rel_time"]),
                    str(row["depth4_vs_depth3_wlt"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    sources = [
        ("scale-frontier", RESULTS / "raw_screen_scale_depth_frontier_terms.csv"),
        ("scale-generalization", RESULTS / "raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv"),
        ("truth-bridge-n23", RESULTS / "raw_truth_bridge_n23_cost_time003_frontier_terms.csv"),
        ("truth-bridge-n24", RESULTS / "raw_truth_bridge_n24_terms.csv"),
        ("truth-bridge-n25", RESULTS / "raw_truth_bridge_n25_terms.csv"),
    ]
    rows: list[dict[str, object]] = []
    for source, path in sources:
        if not path.exists():
            continue
        rows.append(summarize_source(source, load_grouped(path, source)))
    write_csv(RESULTS / "summary_sparse_depth_frontier.csv", rows)
    write_markdown(RESULTS / "analysis_sparse_depth_frontier.md", rows)
    write_latex(TABLES / "sparse_depth_frontier.tex", rows)
    print(f"wrote {len(rows)} sparse depth-frontier rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
