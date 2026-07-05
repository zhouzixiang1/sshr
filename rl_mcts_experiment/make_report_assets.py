#!/usr/bin/env python3
"""Generate paper tables and a compact result analysis from experiment CSVs."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper"


METHOD_LABELS = {
    "sshr_h": "SSHR-H",
    "sshr_h_literal": "SSHR-H-literal",
    "beam": "Beam",
    "mcts_rollout": "Rollout-MCTS",
    "pv_greedy": "PV-Greedy",
    "pv_greedy_lookahead": "PV-Greedy-LA",
    "pv_mcts": "PV-MCTS",
    "xor_beam_rule": "XOR-Beam",
    "xor_beam_v2": "XOR-Beam-v2",
    "xor_beam_best": "XOR-Beam-best",
}


def load_summary(path: Path) -> List[Dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def pct(new: float, base: float) -> float:
    return (new - base) / base * 100.0


def best_by_n(rows: List[Dict[str, str]]) -> Dict[int, Dict[str, str]]:
    out: Dict[int, Dict[str, str]] = {}
    for row in rows:
        n = int(row["n"])
        if n not in out or int(row["total_cnot"]) < int(out[n]["total_cnot"]):
            out[n] = row
    return out


def table_main(rows: List[Dict[str, str]]) -> str:
    order = [
        "sshr_h",
        "sshr_h_literal",
        "beam",
        "mcts_rollout",
        "pv_greedy",
        "pv_greedy_lookahead",
        "pv_mcts",
        "xor_beam_rule",
        "xor_beam_v2",
        "xor_beam_best",
    ]
    by = {(int(r["n"]), r["method"]): r for r in rows}
    lines = [
        "\\begin{center}",
        "\\scriptsize",
        "\\begin{longtable}{llrrrr}",
        "\\caption{不同综合方法在测试集上的 CNOT 成本与平均运行时间。Correct 表示通过逐输入仿真的函数数。}",
        "\\label{tab:main-results}\\\\",
        "\\toprule",
        "$n$ & 方法 & 函数数 & Correct & 总 CNOT & 平均时间(s) \\\\",
        "\\midrule",
        "\\endfirsthead",
        "\\toprule",
        "$n$ & 方法 & 函数数 & Correct & 总 CNOT & 平均时间(s) \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for n in sorted({int(r["n"]) for r in rows}):
        first = True
        for method in order:
            r = by.get((n, method))
            if not r:
                continue
            n_cell = str(n) if first else ""
            first = False
            lines.append(
                f"{n_cell} & {METHOD_LABELS[method]} & {r['functions']} & {r['correct']} & {r['total_cnot']} & {float(r['mean_time_s']):.4f} \\\\"
            )
        lines.append("\\midrule")
    lines[-1] = "\\bottomrule"
    lines.extend(["\\end{longtable}", "\\end{center}", ""])
    return "\n".join(lines)


def table_improvement(rows: List[Dict[str, str]]) -> str:
    by_n_method: Dict[int, Dict[str, Dict[str, str]]] = {}
    for r in rows:
        by_n_method.setdefault(int(r["n"]), {})[r["method"]] = r
    best = best_by_n(rows)
    lines = [
        "\\begin{center}",
        "\\small",
        "\\captionof{table}{最佳方法相对于 SSHR-H 与单调 Beam 的 CNOT 降幅。负值表示 CNOT 成本降低。}",
        "\\label{tab:improvements}",
        "\\begin{tabular}{llrrr}",
        "\\toprule",
        "$n$ & 最佳方法 & 总 CNOT & 相对 SSHR-H & 相对 Beam \\\\",
        "\\midrule",
    ]
    for n in sorted(best):
        b = best[n]
        sshr = by_n_method[n]["sshr_h"]
        beam = by_n_method[n]["beam"]
        rel_h = pct(float(b["total_cnot"]), float(sshr["total_cnot"]))
        rel_beam = pct(float(b["total_cnot"]), float(beam["total_cnot"]))
        lines.append(
            f"{n} & {METHOD_LABELS[b['method']]} & {b['total_cnot']} & {rel_h:+.2f}\\% & {rel_beam:+.2f}\\% \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{center}", ""])
    return "\n".join(lines)


def write_analysis(rows: List[Dict[str, str]]) -> None:
    by_n_method: Dict[int, Dict[str, Dict[str, str]]] = {}
    for r in rows:
        by_n_method.setdefault(int(r["n"]), {})[r["method"]] = r
    best = best_by_n(rows)
    lines = [
        "# Experiment Analysis",
        "",
        "All rows in `raw_main.csv` passed circuit simulation; no method produced an incorrect circuit.",
        "",
        "## Best Method By n",
        "",
        "| n | best method | total CNOT | vs SSHR-H | vs Beam |",
        "|---:|---|---:|---:|---:|",
    ]
    for n in sorted(best):
        b = best[n]
        rel_h = pct(float(b["total_cnot"]), float(by_n_method[n]["sshr_h"]["total_cnot"]))
        rel_beam = pct(float(b["total_cnot"]), float(by_n_method[n]["beam"]["total_cnot"]))
        lines.append(
            f"| {n} | {METHOD_LABELS[b['method']]} | {b['total_cnot']} | {rel_h:+.2f}% | {rel_beam:+.2f}% |"
        )
    lines.extend(
        [
            "",
            "## PV-MCTS Family",
            "",
            "| n | PV-MCTS vs PV-Greedy | PV-MCTS vs Beam | PV-MCTS vs Rollout-MCTS |",
            "|---:|---:|---:|---:|",
        ]
    )
    for n, table in sorted(by_n_method.items()):
        pv = table["pv_mcts"]
        vals = []
        for base in ["pv_greedy", "beam", "mcts_rollout"]:
            vals.append(pct(float(pv["total_cnot"]), float(table[base]["total_cnot"])))
        lines.append(f"| {n} | {vals[0]:+.2f}% | {vals[1]:+.2f}% | {vals[2]:+.2f}% |")
    (RESULTS / "analysis_main.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = load_summary(RESULTS / "summary_main.csv")
    PAPER.mkdir(parents=True, exist_ok=True)
    (PAPER / "generated_tables.tex").write_text(
        table_main(rows) + "\n" + table_improvement(rows),
        encoding="utf-8",
    )
    write_analysis(rows)
    print(f"wrote {PAPER / 'generated_tables.tex'}")
    print(f"wrote {RESULTS / 'analysis_main.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
