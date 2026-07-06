#!/usr/bin/env python3
"""Create compact Markdown analysis from experiment CSV output."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


def comparison_rows(
    by_name: dict[str, dict[str, dict]],
    target: str,
    base: str,
    metric: str,
) -> tuple[int, int, int, float]:
    vals = []
    wins = losses = ties = 0
    for table in by_name.values():
        if target not in table or base not in table:
            continue
        new = float(table[target][metric])
        old = float(table[base][metric])
        vals.append(pct(new, old))
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties, sum(vals) / len(vals) if vals else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="pilot")
    args = ap.parse_args()

    raw = THIS_DIR / "results" / f"raw_{args.preset}.csv"
    rows = list(csv.DictReader(raw.open(encoding="utf-8")))
    usable = [r for r in rows if not r.get("error") and not r.get("skipped")]
    by_name: dict[str, dict[str, dict]] = {}
    for r in usable:
        by_name.setdefault(r["name"], {})[r["method"]] = r

    lines = [
        f"# {args.preset.title()} Analysis",
        "",
        f"Rows: {len(rows)}; usable: {len(usable)}; errors: {sum(1 for r in rows if r.get('error'))}; skipped: {sum(1 for r in rows if r.get('skipped'))}.",
        "",
    ]
    error_rows = [r for r in rows if r.get("error")]
    if error_rows:
        lines.extend(
            [
                "## Timeout / error rows",
                "",
                "| function | n | method | error |",
                "|---|---:|---|---|",
            ]
        )
        for r in error_rows:
            lines.append(f"| {r.get('name', '')} | {r.get('n', '')} | {r.get('method', '')} | {r.get('error', '')} |")
        lines.append("")

    lines.extend(
        [
        "## Mean T-count improvement vs direct ANF",
        "",
        "| method | functions | mean relative T | best | worst |",
        "|---|---:|---:|---:|---:|",
        ]
    )
    methods = sorted({r["method"] for r in usable if r["method"] != "direct_anf"})
    for method in methods:
        vals = []
        for table in by_name.values():
            if "direct_anf" in table and method in table:
                vals.append(pct(float(table[method]["T"]), float(table["direct_anf"]["T"])))
        if vals:
            lines.append(f"| {method} | {len(vals)} | {sum(vals)/len(vals):+.2f}% | {min(vals):+.2f}% | {max(vals):+.2f}% |")

    lines.extend(["", "## T-count wins/losses vs SSHR-H", "", "| method | wins | losses | mean relative T |", "|---|---:|---:|---:|"])
    for method in methods:
        vals = []
        for table in by_name.values():
            if "sshr_h" in table and method in table:
                vals.append(pct(float(table[method]["T"]), float(table["sshr_h"]["T"])))
        if vals:
            wins = sum(1 for v in vals if v < 0)
            losses = sum(1 for v in vals if v >= 0)
            lines.append(f"| {method} | {wins} | {losses} | {sum(vals)/len(vals):+.2f}% |")

    lines.extend(
        [
            "",
            "## Focused method comparisons",
            "",
            "| target | baseline | metric | wins | losses | ties | mean relative |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    focus_pairs = [
        ("and_rc_nmcts", "direct_anf"),
        ("and_rc_nmcts", "and_direct_anf"),
        ("and_rc_nmcts", "and_mcts_factor"),
        ("and_rc_nmcts", "and_affine_nmcts"),
        ("and_rc_nmcts", "and_fprm_mcts"),
        ("and_rc_nmcts", "and_fprm_neural_mcts"),
        ("and_rc_nmcts", "sshr_h"),
        ("and_affine_nmcts", "and_affine_greedy"),
        ("and_affine_nmcts", "and_affine_no_guard"),
        ("and_affine_nmcts", "direct_anf"),
        ("and_affine_nmcts", "and_direct_anf"),
        ("and_affine_nmcts", "and_mcts_factor"),
        ("and_affine_nmcts", "and_cube_beam"),
        ("and_affine_nmcts", "and_esop_milp"),
        ("and_affine_nmcts", "sshr_h"),
        ("and_resource_nmcts", "direct_anf"),
        ("and_resource_nmcts", "and_direct_anf"),
        ("and_resource_nmcts", "and_fprm_greedy"),
        ("and_resource_nmcts", "and_fprm_root_beam"),
        ("and_resource_nmcts", "and_affine_greedy"),
        ("and_resource_nmcts", "and_affine_nmcts"),
        ("and_resource_nmcts", "and_mcts_factor"),
        ("and_resource_nmcts", "and_cube_beam"),
        ("and_resource_nmcts", "and_esop_milp"),
        ("and_resource_nmcts", "sshr_h"),
        ("and_profile_resource_nmcts", "direct_anf"),
        ("and_profile_resource_nmcts", "and_direct_anf"),
        ("and_profile_resource_nmcts", "and_fprm_greedy"),
        ("and_profile_resource_nmcts", "and_fprm_root_beam"),
        ("and_profile_resource_nmcts", "and_affine_greedy"),
        ("and_profile_resource_nmcts", "and_resource_nmcts"),
        ("and_profile_resource_nmcts", "and_affine_nmcts"),
        ("and_profile_resource_nmcts", "and_mcts_factor"),
        ("and_profile_resource_nmcts", "and_cube_beam"),
        ("and_profile_resource_nmcts", "and_esop_milp"),
        ("and_profile_resource_nmcts", "sshr_h"),
        ("and_fprm_linear_pair", "and_fprm_root_beam"),
        ("and_fprm_linear_pair", "and_fprm_greedy"),
        ("and_fprm_linear_pair_deep", "and_fprm_linear_pair"),
        ("and_fprm_linear_pair_deep", "and_fprm_root_beam"),
        ("and_fprm_linear_pair_deep", "and_fprm_greedy"),
        ("and_fprm_linear_parity", "and_fprm_linear_pair"),
        ("and_fprm_linear_parity", "and_fprm_linear_pair_deep"),
        ("and_fprm_linear_parity", "and_fprm_root_beam"),
        ("and_fprm_linear_parity", "and_fprm_greedy"),
        ("and_fprm_polarity_archive", "and_fprm_linear_pair"),
        ("and_fprm_polarity_archive", "and_fprm_greedy"),
        ("and_pareto_resource_nmcts", "and_fprm_polarity_archive"),
        ("and_resource_nmcts", "and_fprm_linear_pair"),
        ("and_resource_nmcts", "and_fprm_linear_pair_deep"),
        ("and_resource_nmcts", "and_fprm_linear_parity"),
        ("and_profile_resource_nmcts", "and_fprm_linear_pair"),
        ("and_profile_resource_nmcts", "and_fprm_linear_pair_deep"),
        ("and_profile_resource_nmcts", "and_fprm_linear_parity"),
        ("and_pareto_resource_nmcts", "direct_anf"),
        ("and_pareto_resource_nmcts", "and_direct_anf"),
        ("and_pareto_resource_nmcts", "and_resource_nmcts"),
        ("and_pareto_resource_nmcts", "and_profile_resource_nmcts"),
        ("and_pareto_resource_nmcts", "and_fprm_linear_pair"),
        ("and_pareto_resource_nmcts", "and_fprm_linear_pair_deep"),
        ("and_pareto_resource_nmcts", "and_fprm_root_beam"),
        ("and_pareto_resource_nmcts", "and_affine_nmcts"),
        ("and_pareto_resource_nmcts", "and_mcts_factor"),
        ("and_pareto_resource_nmcts", "and_cube_beam"),
        ("and_pareto_resource_nmcts", "and_esop_milp"),
        ("and_pareto_resource_nmcts", "sshr_h"),
        ("and_affine_no_guard", "and_affine_greedy"),
        ("and_affine_no_guard", "and_mcts_factor"),
        ("and_fprm_root_beam", "and_fprm_greedy"),
        ("and_fprm_root_beam", "and_affine_greedy"),
        ("and_affine_greedy", "and_fprm_greedy"),
        ("and_affine_greedy", "and_mcts_factor"),
        ("and_cube_beam", "and_esop_milp"),
        ("and_cube_beam", "sshr_h"),
        ("and_esop_milp", "sshr_h"),
        ("and_fprm_neural_mcts", "direct_anf"),
        ("and_fprm_neural_mcts", "and_direct_anf"),
        ("and_fprm_neural_mcts", "and_fprm_mcts"),
        ("and_fprm_neural_mcts", "sshr_h"),
        ("and_fprm_mcts", "sshr_h"),
    ]
    for target, base in focus_pairs:
        if not any(target in table and base in table for table in by_name.values()):
            continue
        for metric in ["T", "CNOT", "depth", "peak_ancilla", "score"]:
            wins, losses, ties, mean = comparison_rows(by_name, target, base, metric)
            lines.append(f"| {target} | {base} | {metric} | {wins} | {losses} | {ties} | {mean:+.2f}% |")

    for focus in ["and_rc_nmcts", "and_affine_nmcts", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts", "and_affine_no_guard", "and_affine_greedy", "and_fprm_greedy", "and_fprm_root_beam", "and_fprm_linear_pair", "and_fprm_linear_pair_deep", "and_fprm_linear_parity", "and_fprm_polarity_archive", "and_cube_beam", "and_esop_milp", "and_fprm_neural_mcts", "and_fprm_mcts", "fprm_mcts"]:
        if not any(focus in table for table in by_name.values()):
            continue
        label = focus.replace("_", "-")
        lines.extend(
            [
                "",
                f"## Largest {label} gains vs direct ANF",
                "",
                f"| function | n | direct T | {focus} T | relative |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        cases = []
        for name, table in by_name.items():
            if "direct_anf" in table and focus in table:
                rel = pct(float(table[focus]["T"]), float(table["direct_anf"]["T"]))
                cases.append((rel, name, table))
        for rel, name, table in sorted(cases)[:12]:
            lines.append(
                f"| {name} | {table['direct_anf']['n']} | {table['direct_anf']['T']} | {table[focus]['T']} | {rel:+.2f}% |"
            )

    for focus in ["and_rc_nmcts", "and_affine_nmcts", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts", "and_affine_no_guard", "and_affine_greedy", "and_fprm_polarity_archive", "and_cube_beam", "and_esop_milp", "and_fprm_neural_mcts", "and_fprm_mcts"]:
        if not any("sshr_h" in table and focus in table for table in by_name.values()):
            continue
        lines.extend(
            [
                "",
                f"## {focus} vs SSHR-H",
                "",
                f"| function | n | SSHR-H T | {focus} T | relative | peak ancilla |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        cases = []
        for name, table in by_name.items():
            if "sshr_h" in table and focus in table:
                rel = pct(float(table[focus]["T"]), float(table["sshr_h"]["T"]))
                cases.append((rel, name, table))
        for rel, name, table in sorted(cases):
            lines.append(
                f"| {name} | {table['sshr_h']['n']} | {table['sshr_h']['T']} | {table[focus]['T']} | {rel:+.2f}% | {table[focus]['peak_ancilla']} |"
            )

    out = THIS_DIR / "results" / f"analysis_{args.preset}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
