#!/usr/bin/env python3
"""Run block-level RL/MCTS synthesis experiments."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = ROOT / "sshr"
AI_DIR = ROOT / "ai_sshr_experiment"
THIS_DIR = Path(__file__).resolve().parent
for p in [SSHR_DIR, AI_DIR, THIS_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from bool_func import BooleanFunction  # noqa: E402
from sshr_h import sshr_h  # noqa: E402
from sshr_h_paper import sshr_h_paper  # noqa: E402
from sshr_beam import sshr_beam  # noqa: E402
from sshr_mcts_v2 import sshr_mcts_v2  # noqa: E402
from ai_guided_beam import ai_guided_beam  # noqa: E402
from rankers import RuleRanker  # noqa: E402
from xor_beam_v2 import xor_beam_v2  # noqa: E402
from xor_beam_best import xor_beam_best  # noqa: E402
from block_pv_mcts import (  # noqa: E402
    SearchResult,
    circuit_cost,
    synthesize_greedy,
    synthesize_pv_mcts,
    verify_circuit,
)


def make_functions(n: int, count: int, seed: int) -> List[BooleanFunction]:
    if count < 0:
        return [BooleanFunction(n, tt) for tt in range(1, 1 << (1 << n))]
    rng = random.Random(seed)
    N = 1 << n
    max_unique = sum(math.comb(N, k) for k in range(1, N // 2 + 1))
    if count > max_unique:
        raise ValueError(f"cannot sample {count} unique on-sets for n={n}; max is {max_unique}")
    out: List[BooleanFunction] = []
    seen = set()
    while len(out) < count:
        k = rng.randint(1, N // 2)
        mints = tuple(sorted(rng.sample(range(N), k)))
        if mints in seen:
            continue
        seen.add(mints)
        tt = sum(1 << i for i in mints)
        out.append(BooleanFunction(n, tt))
    return out


def wrap_existing(method: str, bf: BooleanFunction, seed: int) -> SearchResult:
    t0 = time.time()
    if method == "sshr_h":
        circ = sshr_h(bf)
    elif method == "sshr_h_literal":
        circ = sshr_h_paper(bf)
    elif method == "beam":
        circ = sshr_beam(bf, objective="cnot", width=30, branch=8)
    elif method == "mcts_rollout":
        circ = sshr_mcts_v2(bf, objective="cnot", n_iterations=350, seed=seed)
    elif method == "xor_beam_rule":
        result = ai_guided_beam(
            bf,
            objective="cnot",
            width=30,
            branch=8,
            ranker=RuleRanker(),
            mode="xor",
            R_threshold=0.75,
        )
        circ = result.circuit
    elif method == "xor_beam_v2":
        result = xor_beam_v2(
            bf,
            objective="cnot",
            width=30,
            branch=8,
            ranker=RuleRanker(),
            n_greedy_restarts=12,
        )
        circ = result.circuit
    elif method == "xor_beam_best":
        result = xor_beam_best(
            bf,
            objective="cnot",
            width=30,
            branch=8,
            ranker=RuleRanker(),
            n_perturb=16,
        )
        circ = result.circuit
    else:
        raise ValueError(method)
    return SearchResult(
        circuit=circ,
        path=[],
        cost=circuit_cost(circ),
        time_s=time.time() - t0,
        correct=verify_circuit(circ, bf),
        steps=len(circ.gates),
        method=method,
    )


def run_method(method: str, bf: BooleanFunction, seed: int) -> SearchResult:
    if method == "pv_greedy":
        return synthesize_greedy(bf, lookahead=False)
    if method == "pv_greedy_lookahead":
        return synthesize_greedy(bf, lookahead=True)
    if method == "pv_mcts":
        return synthesize_pv_mcts(
            bf,
            simulations_per_step=96,
            expand_top_k=24,
            c_puct=1.25,
            seed=seed,
        )
    return wrap_existing(method, bf, seed)


PRESETS = {
    "smoke": {
        "suite": [(3, 16)],
        "methods": [
            "sshr_h",
            "beam",
            "xor_beam_rule",
            "pv_greedy",
            "pv_greedy_lookahead",
            "pv_mcts",
        ],
        "seed": 42,
    },
    "main": {
        "suite": [(3, -1), (4, 1024), (5, 256), (6, 48)],
        "methods": [
            "sshr_h",
            "sshr_h_literal",
            "beam",
            "mcts_rollout",
            "xor_beam_rule",
            "xor_beam_v2",
            "xor_beam_best",
            "pv_greedy",
            "pv_greedy_lookahead",
            "pv_mcts",
        ],
        "seed": 42,
    },
}


def summarize(rows: Sequence[Dict]) -> List[Dict]:
    groups: Dict[tuple, List[Dict]] = {}
    for row in rows:
        groups.setdefault((row["n"], row["method"]), []).append(row)
    out: List[Dict] = []
    for (n, method), items in sorted(groups.items()):
        costs = [int(r["cost"]) for r in items if r["correct"]]
        times = [float(r["time_s"]) for r in items]
        out.append(
            {
                "n": n,
                "method": method,
                "functions": len(items),
                "correct": sum(1 for r in items if r["correct"]),
                "total_cnot": sum(costs),
                "mean_cnot": statistics.mean(costs) if costs else float("nan"),
                "median_cnot": statistics.median(costs) if costs else float("nan"),
                "mean_time_s": statistics.mean(times) if times else float("nan"),
            }
        )
    return out


def write_csv(path: Path, rows: Sequence[Dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RL-MCTS Block Experiment Results",
        "",
        "| n | method | functions | correct | total CNOT | mean CNOT | median CNOT | mean time (s) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        lines.append(
            "| {n} | {method} | {functions} | {correct} | {total_cnot} | {mean_cnot:.2f} | {median_cnot:.2f} | {mean_time_s:.4f} |".format(
                **r
            )
        )

    # Add per-n improvement against beam and greedy baselines.
    by_n: Dict[int, Dict[str, Dict]] = {}
    for r in summary:
        by_n.setdefault(int(r["n"]), {})[str(r["method"])] = dict(r)
    lines.extend(["", "## Relative Comparisons", ""])
    lines.append("| n | comparison | delta total CNOT | relative |")
    lines.append("|---:|---|---:|---:|")
    for n, table in sorted(by_n.items()):
        pv = table.get("pv_mcts")
        if not pv:
            continue
        for base in [
            "pv_greedy",
            "pv_greedy_lookahead",
            "beam",
            "mcts_rollout",
            "xor_beam_rule",
            "xor_beam_v2",
            "xor_beam_best",
            "sshr_h",
        ]:
            if base not in table:
                continue
            delta = int(pv["total_cnot"]) - int(table[base]["total_cnot"])
            rel = delta / max(float(table[base]["total_cnot"]), 1.0) * 100.0
            lines.append(f"| {n} | pv_mcts vs {base} | {delta:+d} | {rel:+.2f}% |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--out-dir", default=str(THIS_DIR / "results"))
    args = ap.parse_args(list(argv) if argv is not None else None)

    cfg = PRESETS[args.preset]
    out_dir = Path(args.out_dir)
    rows: List[Dict] = []
    seed = int(cfg["seed"])

    manifest = {
        "preset": args.preset,
        "seed": seed,
        "suite": cfg["suite"],
        "methods": cfg["methods"],
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"manifest_{args.preset}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for n, count in cfg["suite"]:
        functions = make_functions(n, count, seed)
        print(f"n={n}: {len(functions)} functions")
        for fi, bf in enumerate(functions):
            for method in cfg["methods"]:
                try:
                    result = run_method(method, bf, seed + fi)
                    rows.append(
                        {
                            "preset": args.preset,
                            "n": n,
                            "func_id": fi,
                            "truth_table_hex": f"{bf.truth_table:X}",
                            "method": result.method,
                            "cost": int(result.cost),
                            "time_s": f"{result.time_s:.6f}",
                            "correct": bool(result.correct),
                            "steps": int(result.steps),
                        }
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "preset": args.preset,
                            "n": n,
                            "func_id": fi,
                            "truth_table_hex": f"{bf.truth_table:X}",
                            "method": method,
                            "cost": -1,
                            "time_s": "0.000000",
                            "correct": False,
                            "steps": 0,
                            "error": repr(exc),
                        }
                    )
            if (fi + 1) % 50 == 0:
                print(f"  {fi + 1}/{len(functions)}")

    raw_path = out_dir / f"raw_{args.preset}.csv"
    summary_path = out_dir / f"summary_{args.preset}.csv"
    md_path = out_dir / f"summary_{args.preset}.md"
    write_csv(raw_path, rows)
    summary = summarize(rows)
    write_csv(summary_path, summary)
    write_markdown(md_path, summary)
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
