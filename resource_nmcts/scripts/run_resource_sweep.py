#!/usr/bin/env python3
"""Run a small resource-weight sweep for logical oracle synthesis."""
from __future__ import annotations

import argparse
import csv
import json
import random
import signal
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from src.anf_utils import anf_monomials, random_truth_function, structured_suite
from src.factor_plan import SearchConfig
from src.resource_model import ResourceWeights
from src.synthesizers import synthesize


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_MODEL = THIS_DIR / "models" / "action_scorer_rollout_logical_and.pt"

PROFILES = {
    "t_heavy": {
        "label": "T-heavy",
        "weights": ResourceWeights(t=1.0, cnot=0.015, depth=0.005, gates=0.005, ancilla=1.0),
        "max_factor_ancilla": 4,
    },
    "balanced": {
        "label": "Balanced",
        "weights": ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        "max_factor_ancilla": 4,
    },
    "cnot_depth": {
        "label": "CNOT-depth",
        "weights": ResourceWeights(t=0.65, cnot=0.18, depth=0.08, gates=0.01, ancilla=2.0),
        "max_factor_ancilla": 4,
    },
    "cnot_only": {
        "label": "CNOT-only",
        "weights": ResourceWeights(t=0.0, cnot=1.0, depth=0.0, gates=0.0, ancilla=0.0),
        "max_factor_ancilla": 4,
    },
    "ancilla_tight": {
        "label": "Ancilla-tight",
        "weights": ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=8.0),
        "max_factor_ancilla": 1,
    },
}

METHODS = [
    "and_direct_anf",
    "and_mcts_factor",
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_profile_resource_nmcts",
    "and_fprm_polarity_archive",
    "and_pareto_resource_nmcts",
    "and_cube_beam",
    "sshr_h",
]
RANDOM_TRUTH = [(4, 12), (5, 12), (6, 6)]


class TaskTimeout(TimeoutError):
    pass


def _timeout_handler(signum, frame):
    raise TaskTimeout("synthesis task timed out")


def make_suite(seed: int) -> list[tuple[str, object]]:
    rng = random.Random(seed)
    suite = [(name, bf) for name, bf in structured_suite() if bf.n <= 6]
    for n, count in RANDOM_TRUTH:
        seen = set()
        for i in range(count):
            bf = random_truth_function(n, rng)
            while bf.truth_table == 0 or bf.truth_table in seen:
                bf = random_truth_function(n, rng)
            seen.add(bf.truth_table)
            suite.append((f"sweep_truth_n{n}_{i}", bf))
    return suite


def config_for_profile(profile: str) -> dict:
    p = PROFILES[profile]
    weights = p["weights"]
    return {
        "weights": weights.__dict__,
        "max_factor_ancilla": p["max_factor_ancilla"],
        "max_factor_size": 5,
        "candidate_top_k": 24,
        "min_factor_count": 2,
        "use_relative_phase": True,
        "mcts_simulations": 24,
        "neural_mcts_simulations": 32,
        "max_polarities": 12,
        "gate_mode": "mct",
        "neural_prior_weight": 2.5,
        "task_timeout_s": 120,
    }


def run_one(task):
    profile, name, bf, method, seed, config_dict, model_path = task
    weights = ResourceWeights(**config_dict["weights"])
    config = SearchConfig(
        weights=weights,
        max_factor_ancilla=config_dict["max_factor_ancilla"],
        max_factor_size=config_dict["max_factor_size"],
        candidate_top_k=config_dict["candidate_top_k"],
        min_factor_count=config_dict["min_factor_count"],
        use_relative_phase=config_dict["use_relative_phase"],
        mcts_simulations=config_dict["mcts_simulations"],
        neural_mcts_simulations=config_dict["neural_mcts_simulations"],
        max_polarities=config_dict["max_polarities"],
        gate_mode=config_dict["gate_mode"],
        neural_prior_weight=config_dict["neural_prior_weight"],
    )
    base_method = method[len("and_") :] if method.startswith("and_") else method
    neural_methods = {"affine_nmcts", "resource_nmcts", "profile_resource_nmcts", "pareto_resource_nmcts"}
    use_model = model_path if base_method in neural_methods and model_path else None
    try:
        timeout_s = int(config_dict.get("task_timeout_s", 0) or 0)
        if timeout_s > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout_s)
        result = synthesize(method, bf, config, seed=seed, model_path=use_model)
        row = result.to_row()
        row.update(
            {
                "profile": profile,
                "profile_label": PROFILES[profile]["label"],
                "name": name,
                "n": bf.n,
                "truth_table_hex": f"{bf.truth_table:X}",
                "anf_terms": len(anf_monomials(bf)),
                "score": result.cost.score(config.weights),
                "skipped": "",
                "error": "",
            }
        )
        return row
    except Exception as exc:
        return {
            "profile": profile,
            "profile_label": PROFILES[profile]["label"],
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "correct": False,
            "score": "",
            "skipped": "",
            "error": repr(exc),
        }
    finally:
        signal.alarm(0)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--out-dir", default=str(RESULTS))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--only-methods", default="", help="comma-separated method subset for targeted reruns")
    ap.add_argument("--replace-methods", action="store_true", help="drop existing rows for selected methods before a resume run")
    ap.add_argument("--checkpoint-every", type=int, default=50)
    args = ap.parse_args(list(argv) if argv is not None else None)

    suite = make_suite(args.seed)
    model_path = args.model if Path(args.model).exists() else ""
    out_dir = Path(args.out_dir)
    raw = out_dir / "raw_resource_sweep.csv"
    manifest = out_dir / "manifest_resource_sweep.json"
    methods = METHODS
    if args.only_methods:
        requested = [m.strip() for m in args.only_methods.split(",") if m.strip()]
        unknown = sorted(set(requested) - set(METHODS))
        if unknown:
            raise SystemExit(f"unknown methods for resource sweep: {', '.join(unknown)}")
        methods = requested

    tasks = []
    for profile in PROFILES:
        config_dict = config_for_profile(profile)
        for i, (name, bf) in enumerate(suite):
            for method in methods:
                tasks.append((profile, name, bf, method, args.seed + i, config_dict, model_path))

    rows: list[dict] = []
    if args.resume and raw.exists():
        with raw.open(newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
        if args.replace_methods:
            replace_set = set(methods)
            rows = [r for r in rows if r.get("method") not in replace_set]
        completed = {(r.get("profile"), r.get("name"), r.get("method")) for r in rows}
        tasks = [task for task in tasks if (task[0], task[1], task[3]) not in completed]
        print(f"resuming from {len(rows)} rows; remaining {len(tasks)}", flush=True)

    started = time.time()
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(run_one(task))
            if i % args.checkpoint_every == 0:
                write_csv(raw, rows)
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(run_one, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % args.checkpoint_every == 0:
                    write_csv(raw, rows)
                    print(f"{i}/{len(tasks)}", flush=True)

    write_csv(raw, rows)
    manifest.write_text(
        json.dumps(
            {
                "seed": args.seed,
                "functions": len(suite),
                "methods": METHODS,
                "last_run_methods": methods,
                "profiles": {
                    name: {
                        "label": p["label"],
                        "weights": p["weights"].__dict__,
                        "max_factor_ancilla": p["max_factor_ancilla"],
                    }
                    for name, p in PROFILES.items()
                },
                "model": model_path,
                "workers": args.workers,
                "seconds": time.time() - started,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {raw}")
    print(f"wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
