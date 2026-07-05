#!/usr/bin/env python3
"""Create compact Markdown analysis from experiment CSV output."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent


def pct(new: float, base: float) -> float:
    return (new - base) / max(base, 1.0) * 100.0


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
        "## Mean T-count improvement vs direct ANF",
        "",
        "| method | functions | mean relative T | best | worst |",
        "|---|---:|---:|---:|---:|",
    ]
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

    lines.extend(["", "## Largest FPRM-MCTS gains vs direct ANF", "", "| function | n | direct T | fprm_mcts T | relative |", "|---|---:|---:|---:|---:|"])
    cases = []
    for name, table in by_name.items():
        if "direct_anf" in table and "fprm_mcts" in table:
            rel = pct(float(table["fprm_mcts"]["T"]), float(table["direct_anf"]["T"]))
            cases.append((rel, name, table))
    for rel, name, table in sorted(cases)[:12]:
        lines.append(
            f"| {name} | {table['direct_anf']['n']} | {table['direct_anf']['T']} | {table['fprm_mcts']['T']} | {rel:+.2f}% |"
        )

    out = THIS_DIR / "results" / f"analysis_{args.preset}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

