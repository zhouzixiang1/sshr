#!/usr/bin/env python3
"""Run resource-constrained neural-MCTS oracle synthesis experiments."""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List

from anf_utils import (
    anf_monomials,
    random_anf_function,
    random_truth_function,
    structured_suite,
)
from factor_plan import SearchConfig
from resource_model import ResourceWeights
from synthesizers import synthesize


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_MODEL = THIS_DIR / "models" / "action_scorer.pt"


PRESETS = {
    "smoke": {
        "methods": ["direct_anf", "greedy_factor", "mcts_factor", "fprm_mcts", "neural_mcts", "sshr_h"],
        "random_truth": [(3, 4)],
        "random_anf": [(5, 4)],
        "structured_limit": 4,
        "workers": 1,
    },
    "pilot": {
        "methods": ["direct_anf", "greedy_factor", "mcts_factor", "fprm_greedy", "fprm_mcts", "neural_mcts", "sshr_h"],
        "random_truth": [],
        "random_anf": [(8, 4)],
        "structured_limit": 10_000,
        "workers": 6,
    },
    "main": {
        "methods": ["direct_anf", "greedy_factor", "mcts_factor", "fprm_greedy", "fprm_mcts", "neural_mcts", "fprm_neural_mcts", "sshr_h", "sshr_beam"],
        "random_truth": [(3, 255), (4, 256), (5, 128), (6, 64)],
        "random_anf": [(7, 256), (8, 256), (10, 128), (12, 64)],
        "structured_limit": 10_000,
        "workers": 10,
    },
}


def make_suite(preset: str, seed: int):
    cfg = PRESETS[preset]
    rng = random.Random(seed)
    suite: list[tuple[str, object]] = []
    suite.extend(structured_suite()[: cfg["structured_limit"]])
    for n, count in cfg["random_truth"]:
        seen = set()
        for i in range(count):
            bf = random_truth_function(n, rng)
            while bf.truth_table == 0 or bf.truth_table in seen:
                bf = random_truth_function(n, rng)
            seen.add(bf.truth_table)
            suite.append((f"truth_n{n}_{i}", bf))
    for n, count in cfg["random_anf"]:
        for i in range(count):
            bf = random_anf_function(
                n,
                rng,
                term_prob=rng.uniform(0.035, 0.16),
                max_degree=rng.randint(2, min(n, 6)),
            )
            suite.append((f"anf_n{n}_{i}", bf))
    return suite


def run_one(task):
    name, bf, method, seed, config_dict, model_path = task
    weights = ResourceWeights(**config_dict["weights"])
    config = SearchConfig(
        weights=weights,
        max_factor_ancilla=config_dict["max_factor_ancilla"],
        max_factor_size=config_dict["max_factor_size"],
        candidate_top_k=config_dict["candidate_top_k"],
        mcts_simulations=config_dict["mcts_simulations"],
        neural_mcts_simulations=config_dict["neural_mcts_simulations"],
        max_polarities=config_dict["max_polarities"],
    )
    use_model = model_path if method in {"neural_greedy", "neural_mcts"} and model_path else None
    if method == "esop_greedy" and bf.n > 4:
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "skipped": "legacy ESOP greedy is limited to n<=4 in this harness",
        }
    if method.startswith("sshr") and bf.n > 6:
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "skipped": "n>6 for SSHR reference in this harness",
        }
    try:
        result = synthesize(method, bf, config, seed=seed, model_path=use_model)
        row = result.to_row()
        row.update(
            {
                "name": name,
                "n": bf.n,
                "truth_table_hex": f"{bf.truth_table:X}",
                "anf_terms": len(anf_monomials(bf)),
                "score": result.cost.score(config.weights),
                "skipped": "",
            }
        )
        return row
    except Exception as exc:  # keep batch experiments resumable
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "correct": False,
            "error": repr(exc),
            "skipped": "",
        }


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summarize(rows: List[dict]) -> List[dict]:
    groups: dict[tuple[str, int], list[dict]] = {}
    for r in rows:
        if r.get("skipped") or r.get("error"):
            continue
        groups.setdefault((str(r["method"]), int(r["n"])), []).append(r)
    out = []
    for (method, n), items in sorted(groups.items()):
        def vals(key):
            return [float(r[key]) for r in items if r.get(key) not in {None, ""}]

        out.append(
            {
                "method": method,
                "n": n,
                "functions": len(items),
                "correct": sum(1 for r in items if str(r.get("correct")) == "True"),
                "total_T": int(sum(vals("T"))),
                "total_CNOT": int(sum(vals("CNOT"))),
                "mean_score": statistics.mean(vals("score")) if vals("score") else float("nan"),
                "mean_depth": statistics.mean(vals("depth")) if vals("depth") else float("nan"),
                "mean_peak_ancilla": statistics.mean(vals("peak_ancilla")) if vals("peak_ancilla") else float("nan"),
                "mean_time_s": statistics.mean(vals("time_s")) if vals("time_s") else float("nan"),
            }
        )
    return out


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--out-dir", default=str(RESULTS))
    args = ap.parse_args(list(argv) if argv is not None else None)

    cfg = PRESETS[args.preset]
    suite = make_suite(args.preset, args.seed)
    model_path = args.model if Path(args.model).exists() else ""
    weights = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
    config_dict = {
        "weights": weights.__dict__,
        "max_factor_ancilla": 4,
        "max_factor_size": 5,
        "candidate_top_k": 24,
        "mcts_simulations": 24 if args.preset == "smoke" else (48 if args.preset == "pilot" else 96),
        "neural_mcts_simulations": 32 if args.preset == "smoke" else (64 if args.preset == "pilot" else 128),
        "max_polarities": 32 if args.preset == "smoke" else (32 if args.preset == "pilot" else 384),
    }
    methods = cfg["methods"]
    tasks = [
        (name, bf, method, args.seed + i, config_dict, model_path)
        for i, (name, bf) in enumerate(suite)
        for method in methods
    ]

    started = time.time()
    rows: List[dict] = []
    workers = args.workers if args.workers is not None else cfg["workers"]
    if workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(run_one(task))
            if i % 50 == 0:
                print(f"{i}/{len(tasks)}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(run_one, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % 100 == 0:
                    print(f"{i}/{len(tasks)}")

    out_dir = Path(args.out_dir)
    raw = out_dir / f"raw_{args.preset}.csv"
    summary_path = out_dir / f"summary_{args.preset}.csv"
    manifest = out_dir / f"manifest_{args.preset}.json"
    write_csv(raw, rows)
    summary = summarize(rows)
    write_csv(summary_path, summary)
    manifest.write_text(
        json.dumps(
            {
                "preset": args.preset,
                "seed": args.seed,
                "functions": len(suite),
                "methods": methods,
                "model": model_path,
                "workers": workers,
                "seconds": time.time() - started,
                "config": config_dict,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {raw}")
    print(f"wrote {summary_path}")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
