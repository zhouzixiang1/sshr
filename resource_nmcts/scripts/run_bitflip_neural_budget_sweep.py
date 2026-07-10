#!/usr/bin/env python3
"""Run low-budget learned-prior sweeps for the bit-flip branch."""
from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from run_experiments import DEFAULT_MODEL, make_suite, run_one, write_csv
from src.resource_model import ResourceWeights


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_METHODS = [
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
]
DEFAULT_BUDGETS = {
    "top8_s8_n12": {
        "candidate_top_k": 8,
        "mcts_simulations": 8,
        "neural_mcts_simulations": 12,
        "max_polarities": 8,
    },
    "top12_s12_n16": {
        "candidate_top_k": 12,
        "mcts_simulations": 12,
        "neural_mcts_simulations": 16,
        "max_polarities": 8,
    },
}


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_csv_list(raw: str, cast=str) -> list:
    return [cast(item.strip()) for item in raw.split(",") if item.strip()]


def config_for_budget(budget: str, overrides: dict[str, int]) -> dict:
    weights = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
    return {
        "weights": weights.__dict__,
        "max_factor_ancilla": 4,
        "max_factor_size": 5,
        "candidate_top_k": overrides["candidate_top_k"],
        "min_factor_count": 2,
        "use_relative_phase": True,
        "mcts_simulations": overrides["mcts_simulations"],
        "neural_mcts_simulations": overrides["neural_mcts_simulations"],
        "max_polarities": overrides["max_polarities"],
        "gate_mode": "mct",
        "neural_prior_weight": 2.5,
        "task_timeout_s": 300,
        "budget": budget,
    }


def add_metadata(row: dict, budget: str, variant: str, model_path: str, config: dict) -> dict:
    out = dict(row)
    out["budget"] = budget
    out["variant"] = variant
    out["model"] = model_path if model_path else "no_prior"
    out["candidate_top_k"] = str(config["candidate_top_k"])
    out["mcts_simulations"] = str(config["mcts_simulations"])
    out["neural_mcts_simulations"] = str(config["neural_mcts_simulations"])
    out["max_polarities"] = str(config["max_polarities"])
    return out


def build_tasks(
    suite: list[tuple[str, object]],
    methods: list[str],
    budgets: dict[str, dict[str, int]],
    variants: list[str],
    model: str,
    seed: int,
):
    tasks = []
    for budget_name, overrides in budgets.items():
        config = config_for_budget(budget_name, overrides)
        for variant in variants:
            model_path = model if variant == "learned_prior" else ""
            for index, (name, bf) in enumerate(suite):
                for method in methods:
                    task = (name, bf, method, seed + index, config, model_path)
                    tasks.append((budget_name, variant, model_path, config, task))
    return tasks


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="traditional_resource")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--out", type=Path, default=RESULTS / "raw_bitflip_neural_budget_sweep.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_bitflip_neural_budget_sweep_run.csv")
    parser.add_argument("--manifest-out", type=Path, default=RESULTS / "manifest_bitflip_neural_budget_sweep_run.json")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--budgets", default=",".join(DEFAULT_BUDGETS))
    parser.add_argument("--variants", default="learned_prior,no_prior")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    args = parser.parse_args(list(argv) if argv is not None else None)

    model = args.model if Path(args.model).exists() else ""
    methods = parse_csv_list(args.methods, str) or list(DEFAULT_METHODS)
    budget_names = parse_csv_list(args.budgets, str) or list(DEFAULT_BUDGETS)
    unknown_budgets = sorted(set(budget_names) - set(DEFAULT_BUDGETS))
    if unknown_budgets:
        raise SystemExit(f"unknown budget(s): {', '.join(unknown_budgets)}")
    budgets = {name: DEFAULT_BUDGETS[name] for name in budget_names}
    variants = parse_csv_list(args.variants, str) or ["learned_prior", "no_prior"]
    suite = make_suite(args.preset, args.seed)

    rows = read_existing(args.out) if args.resume else []
    completed = {
        (row.get("budget"), row.get("variant"), row.get("name"), row.get("method"))
        for row in rows
    }
    tasks = []
    for item in build_tasks(suite, methods, budgets, variants, model, args.seed):
        budget, variant, _model_path, _config, task = item
        name, _bf, method, *_rest = task
        if args.resume and (budget, variant, name, method) in completed:
            continue
        tasks.append(item)

    started = time.time()
    if args.workers <= 1:
        for index, (budget, variant, model_path, config, task) in enumerate(tasks, 1):
            rows.append(add_metadata(run_one(task), budget, variant, model_path, config))
            if index % args.checkpoint_every == 0:
                write_csv(args.out, rows)
                print(f"{index}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_one, task): (budget, variant, model_path, config) for budget, variant, model_path, config, task in tasks}
            for index, future in enumerate(as_completed(futures), 1):
                budget, variant, model_path, config = futures[future]
                rows.append(add_metadata(future.result(), budget, variant, model_path, config))
                if index % args.checkpoint_every == 0:
                    write_csv(args.out, rows)
                    print(f"{index}/{len(tasks)}", flush=True)

    write_csv(args.out, rows)
    usable = [
        row
        for row in rows
        if not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"
    ]
    summary_rows = []
    for budget in budget_names:
        for variant in variants:
            for method in methods:
                items = [row for row in usable if row.get("budget") == budget and row.get("variant") == variant and row.get("method") == method]
                summary_rows.append(
                    {
                        "budget": budget,
                        "variant": variant,
                        "method": method,
                        "functions": len({row["name"] for row in items}),
                        "rows": len(items),
                        "mean_score": sum(float(row["score"]) for row in items) / max(len(items), 1),
                        "mean_time_s": sum(float(row["time_s"]) for row in items) / max(len(items), 1),
                    }
                )
    write_csv(args.summary, summary_rows)

    elapsed = time.time() - started
    manifest = {
        "script": Path(__file__).name,
        "preset": args.preset,
        "seed": args.seed,
        "methods": methods,
        "budgets": budgets,
        "variants": variants,
        "functions": len(suite),
        "workers": args.workers,
        "raw_rows": len(rows),
        "usable_rows": len(usable),
        "seconds_current_run": elapsed,
        "outputs": {
            "raw": str(args.out.relative_to(THIS_DIR)),
            "summary": str(args.summary.relative_to(THIS_DIR)),
            "manifest": str(args.manifest_out.relative_to(THIS_DIR)),
        },
    }
    args.manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
