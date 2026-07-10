#!/usr/bin/env python3
"""Run same-budget random-prior controls for the bit-flip branch."""
from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from run_experiments import make_suite, run_one, write_csv


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
DEFAULT_METHODS = [
    "and_affine_nmcts",
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
]
DEFAULT_RANDOM_SEEDS = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_csv_list(raw: str, cast=str) -> list:
    if not raw.strip():
        return []
    return [cast(item.strip()) for item in raw.split(",") if item.strip()]


def add_random_metadata(row: dict, random_seed: int) -> dict:
    out = dict(row)
    out["variant"] = "random_prior"
    out["random_seed"] = str(random_seed)
    out["model"] = f"random-prior:{random_seed}"
    return out


def build_tasks(
    suite: list[tuple[str, object]],
    methods: list[str],
    config: dict,
    base_seed: int,
    random_seed: int,
):
    return [
        (name, bf, method, base_seed + i, config, f"random-prior:{random_seed}")
        for i, (name, bf) in enumerate(suite)
        for method in methods
    ]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=RESULTS / "manifest_traditional_resource_learned_prior.json")
    parser.add_argument("--out", type=Path, default=RESULTS / "raw_bitflip_random_prior_control.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_bitflip_random_prior_control_run.csv")
    parser.add_argument("--manifest-out", type=Path, default=RESULTS / "manifest_bitflip_random_prior_control_run.json")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--random-seeds", default=",".join(str(seed) for seed in DEFAULT_RANDOM_SEEDS))
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    args = parser.parse_args(list(argv) if argv is not None else None)

    source_manifest = read_json(args.manifest)
    preset = str(source_manifest.get("preset", "traditional_resource"))
    base_seed = int(source_manifest.get("seed", 42))
    config = dict(source_manifest["config"])
    methods = parse_csv_list(args.methods, str) or list(DEFAULT_METHODS)
    random_seeds = parse_csv_list(args.random_seeds, int) or list(DEFAULT_RANDOM_SEEDS)
    suite = make_suite(preset, base_seed)

    rows = read_existing(args.out) if args.resume else []
    completed = {
        (str(row.get("random_seed")), row.get("name"), row.get("method"))
        for row in rows
    }
    tasks = []
    for random_seed in random_seeds:
        for task in build_tasks(suite, methods, config, base_seed, random_seed):
            name, _bf, method, *_rest = task
            if args.resume and (str(random_seed), name, method) in completed:
                continue
            tasks.append((random_seed, task))

    started = time.time()
    if args.workers <= 1:
        for index, (random_seed, task) in enumerate(tasks, 1):
            rows.append(add_random_metadata(run_one(task), random_seed))
            if index % args.checkpoint_every == 0:
                write_csv(args.out, rows)
                print(f"{index}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_one, task): random_seed for random_seed, task in tasks}
            for index, future in enumerate(as_completed(futures), 1):
                rows.append(add_random_metadata(future.result(), futures[future]))
                if index % args.checkpoint_every == 0:
                    write_csv(args.out, rows)
                    print(f"{index}/{len(tasks)}", flush=True)

    write_csv(args.out, rows)

    summary_rows = []
    usable = [
        row
        for row in rows
        if not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"
    ]
    for method in methods:
        method_rows = [row for row in usable if row.get("method") == method]
        summary_rows.append(
            {
                "method": method,
                "functions": len({row["name"] for row in method_rows}),
                "random_repeats": len({row["random_seed"] for row in method_rows}),
                "rows": len(method_rows),
                "mean_score": sum(float(row["score"]) for row in method_rows) / max(len(method_rows), 1),
                "mean_time_s": sum(float(row["time_s"]) for row in method_rows) / max(len(method_rows), 1),
            }
        )
    write_csv(args.summary, summary_rows)

    elapsed = time.time() - started
    data = {
        "script": Path(__file__).name,
        "preset": preset,
        "seed": base_seed,
        "methods": methods,
        "random_seeds": random_seeds,
        "functions": len(suite),
        "workers": args.workers,
        "raw_rows": len(rows),
        "usable_rows": len(usable),
        "seconds_current_run": elapsed,
        "source_manifest": str(args.manifest.relative_to(THIS_DIR)),
        "outputs": {
            "raw": str(args.out.relative_to(THIS_DIR)),
            "summary": str(args.summary.relative_to(THIS_DIR)),
            "manifest": str(args.manifest_out.relative_to(THIS_DIR)),
        },
    }
    args.manifest_out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
