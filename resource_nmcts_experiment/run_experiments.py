#!/usr/bin/env python3
"""Run resource-constrained neural-MCTS oracle synthesis experiments."""
from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import queue
import random
import signal
import statistics
import sys
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


class TaskTimeout(TimeoutError):
    pass


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def _timeout_handler(signum, frame):
    raise TaskTimeout("synthesis task timed out")


PRESETS = {
    "smoke": {
        "methods": ["direct_anf", "and_direct_anf", "and_boolean_linear_pair_screen_ai_guard", "and_fprm_boolean_linear_pair_deep_ai_guard", "and_rc_nmcts", "and_affine_nmcts", "greedy_factor", "mcts_factor", "fprm_mcts", "and_fprm_mcts", "and_fprm_neural_mcts", "cube_greedy", "cube_beam", "neural_mcts", "sshr_h"],
        "random_truth": [(3, 4)],
        "random_anf": [(5, 4)],
        "structured_limit": 4,
        "workers": 1,
    },
    "pilot": {
        "methods": ["direct_anf", "and_direct_anf", "and_rc_nmcts", "and_affine_nmcts", "greedy_factor", "mcts_factor", "and_mcts_factor", "fprm_greedy", "fprm_mcts", "and_fprm_mcts", "and_fprm_neural_mcts", "cube_greedy", "cube_beam", "neural_mcts", "sshr_h"],
        "random_truth": [],
        "random_anf": [(8, 4)],
        "structured_limit": 10_000,
        "workers": 6,
    },
    "main": {
        "methods": ["direct_anf", "and_direct_anf", "and_rc_nmcts", "and_affine_nmcts", "greedy_factor", "mcts_factor", "and_mcts_factor", "fprm_greedy", "fprm_mcts", "and_fprm_mcts", "and_fprm_neural_mcts", "cube_greedy", "cube_beam", "neural_mcts", "fprm_neural_mcts", "sshr_h", "sshr_beam"],
        "random_truth": [(3, 255), (4, 256), (5, 128), (6, 64)],
        "random_anf": [(7, 256), (8, 256), (10, 128), (12, 64)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "large": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_fprm_mcts", "and_fprm_neural_mcts", "and_rc_nmcts", "sshr_h"],
        "random_truth": [(4, 96), (5, 96), (6, 64)],
        "random_anf": [(8, 96), (10, 96), (12, 64)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "large_fast": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_fprm_mcts", "and_fprm_neural_mcts", "and_rc_nmcts", "sshr_h"],
        "random_truth": [(4, 48), (5, 48), (6, 32)],
        "random_anf": [(8, 48), (10, 32)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "evidence": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_rc_nmcts", "sshr_h"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [(8, 64), (10, 48), (12, 24)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "evidence_affine": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "sshr_h"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [(8, 64), (10, 48), (12, 24)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "ablation_affine": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_greedy", "and_affine_no_guard", "and_affine_nmcts", "sshr_h"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [(8, 64), (10, 48), (12, 24)],
        "structured_limit": 10_000,
        "workers": 10,
    },
    "traditional_small": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_cube_beam", "and_esop_milp", "sshr_h"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [],
        "structured_limit": 10_000,
        "max_n": 6,
        "workers": 10,
    },
    "traditional_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_resource_nmcts", "and_fprm_polarity_archive", "and_pareto_resource_nmcts", "and_cube_beam", "and_esop_milp", "sshr_h"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [],
        "structured_limit": 10_000,
        "max_n": 6,
        "workers": 10,
    },
    "search_ablation_traditional": {
        "methods": ["direct_anf", "and_direct_anf", "and_fprm_greedy", "and_fprm_root_beam", "and_fprm_linear_pair", "and_affine_greedy", "and_mcts_factor", "and_affine_nmcts", "and_resource_heuristic", "and_resource_beam_only", "and_resource_no_mcts", "and_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [(4, 64), (5, 64), (6, 32)],
        "random_anf": [],
        "structured_limit": 10_000,
        "max_n": 6,
        "workers": 10,
    },
    "search_ablation_highdim": {
        "methods": ["direct_anf", "and_direct_anf", "and_fprm_greedy", "and_fprm_root_beam", "and_fprm_linear_pair", "and_fprm_boolean_linear_pair_deep", "and_resource_heuristic", "and_resource_beam_only", "and_resource_no_mcts"],
        "random_truth": [],
        "random_anf": [(14, 16)],
        "structured_limit": 0,
        "workers": 6,
    },
    "highdim_neural_prior": {
        "methods": ["and_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(14, 12)],
        "structured_limit": 0,
        "workers": 6,
    },
    "highdim_guard_upgrade": {
        "methods": ["and_resource_nmcts", "and_resource_nmcts_wide"],
        "random_truth": [],
        "random_anf": [(14, 12)],
        "structured_limit": 0,
        "workers": 6,
    },
    "large_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_resource_nmcts", "and_profile_resource_nmcts"],
        "random_truth": [(4, 48), (5, 48), (6, 32)],
        "random_anf": [(8, 64), (10, 64), (12, 48), (14, 24)],
        "structured_limit": 10_000,
        "workers": 4,
    },
    "large_resource_core": {
        "methods": ["direct_anf", "and_direct_anf", "and_mcts_factor", "and_affine_nmcts", "and_resource_nmcts", "and_profile_resource_nmcts"],
        "random_truth": [(4, 48), (5, 48), (6, 32)],
        "random_anf": [(8, 64), (10, 64), (12, 48)],
        "structured_limit": 10_000,
        "workers": 6,
    },
    "highdim_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_fprm_greedy", "and_fprm_root_beam", "and_fprm_linear_pair", "and_fprm_boolean_linear_pair_deep", "and_affine_greedy", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(14, 64)],
        "structured_limit": 0,
        "workers": 8,
    },
    "highdim_scale_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_fprm_greedy", "and_fprm_root_beam", "and_fprm_linear_pair", "and_fprm_linear_pair_deep", "and_fprm_boolean_linear_pair_deep", "and_fprm_linear_parity", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(15, 32)],
        "structured_limit": 0,
        "workers": 6,
    },
    "ultra_highdim_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_fprm_root_beam", "and_fprm_linear_pair", "and_fprm_linear_pair_deep", "and_fprm_boolean_linear_pair_deep", "and_fprm_boolean_linear_pair_deep_root_neural", "and_fprm_boolean_linear_pair_deep_ai_guard", "and_fprm_boolean_linear_pair_screen", "and_fprm_linear_pair_deep_root_neural", "and_fprm_linear_pair_deep_ai_guard", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(16, 24)],
        "structured_limit": 0,
        "workers": 6,
    },
    "mega_highdim_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_boolean_linear_pair_screen", "and_boolean_linear_pair_screen_deep", "and_boolean_linear_pair_screen_neural", "and_boolean_linear_pair_screen_deep_neural", "and_boolean_linear_pair_screen_ai_guard", "and_boolean_linear_pair_screen_deep_ai_guard", "and_fprm_root_beam", "and_fprm_linear_pair_fast", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(18, 12)],
        "structured_limit": 0,
        "workers": 4,
    },
    "giga_highdim_resource": {
        "methods": ["direct_anf", "and_direct_anf", "and_boolean_linear_pair_screen", "and_boolean_linear_pair_screen_deep", "and_boolean_linear_pair_screen_deeper", "and_boolean_linear_pair_screen_neural", "and_boolean_linear_pair_screen_deep_neural", "and_boolean_linear_pair_screen_ai_guard", "and_boolean_linear_pair_screen_deep_ai_guard", "and_fprm_root_beam", "and_fprm_linear_pair_fast", "and_resource_nmcts", "and_profile_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(20, 6)],
        "structured_limit": 0,
        "workers": 3,
    },
    "boolean_neural_highdim": {
        "methods": ["and_fprm_boolean_linear_pair_deep", "and_fprm_boolean_linear_pair_deep_root_neural", "and_fprm_boolean_linear_pair_deep_ai_guard", "and_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(16, 24)],
        "structured_limit": 0,
        "workers": 6,
    },
    "boolean_neural_mega": {
        "methods": ["and_fprm_boolean_linear_pair_deep", "and_fprm_boolean_linear_pair_deep_root_neural", "and_fprm_boolean_linear_pair_deep_ai_guard", "and_resource_nmcts", "and_pareto_resource_nmcts"],
        "random_truth": [],
        "random_anf": [(18, 12)],
        "structured_limit": 0,
        "workers": 4,
    },
}

BOUNDED_RESOURCE_PRESETS = {
    "smoke",
    "large_fast",
    "evidence",
    "evidence_affine",
    "ablation_affine",
    "traditional_small",
    "traditional_resource",
    "search_ablation_traditional",
    "large_resource",
    "large_resource_core",
    "highdim_resource",
    "search_ablation_highdim",
    "highdim_neural_prior",
    "highdim_guard_upgrade",
    "highdim_scale_resource",
    "ultra_highdim_resource",
    "mega_highdim_resource",
    "giga_highdim_resource",
    "boolean_neural_highdim",
    "boolean_neural_mega",
}

HIGH_RESOURCE_PRESETS = {
    "large_resource",
    "large_resource_core",
    "highdim_resource",
    "search_ablation_highdim",
    "highdim_neural_prior",
    "highdim_guard_upgrade",
    "highdim_scale_resource",
    "ultra_highdim_resource",
    "mega_highdim_resource",
    "giga_highdim_resource",
    "boolean_neural_highdim",
    "boolean_neural_mega",
}


def make_suite(preset: str, seed: int):
    cfg = PRESETS[preset]
    rng = random.Random(seed)
    suite: list[tuple[str, object]] = []
    max_n = cfg.get("max_n")
    structured = structured_suite()[: cfg["structured_limit"]]
    if max_n is not None:
        structured = [(name, bf) for name, bf in structured if bf.n <= max_n]
    suite.extend(structured)
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
        min_factor_count=config_dict.get("min_factor_count", 2),
        use_relative_phase=config_dict.get("use_relative_phase", True),
        mcts_simulations=config_dict["mcts_simulations"],
        neural_mcts_simulations=config_dict["neural_mcts_simulations"],
        max_polarities=config_dict["max_polarities"],
        gate_mode=config_dict.get("gate_mode", "mct"),
        neural_prior_weight=config_dict.get("neural_prior_weight", 1.0),
    )
    base_method = method[len("and_") :] if method.startswith("and_") else method
    neural_methods = {
        "neural_greedy",
        "neural_mcts",
        "fprm_neural_mcts",
        "affine_nmcts",
        "affine_no_guard",
        "rc_nmcts",
        "resource_nmcts",
        "resource_nmcts_wide",
        "profile_resource_nmcts",
        "pareto_resource_nmcts",
        "fprm_linear_pair_neural",
        "fprm_linear_pair_wide",
        "fprm_linear_pair_wide_fast",
        "fprm_linear_pair_root_neural",
        "fprm_linear_pair_fast_neural",
        "fprm_linear_pair_fast_root_neural",
        "fprm_linear_pair_deep_neural",
        "fprm_linear_pair_deep_ai_guard",
        "fprm_linear_pair_deep_ai_guard_wide",
        "fprm_linear_pair_deep_wide",
        "fprm_linear_pair_deep_root_neural",
        "fprm_linear_pair_deep_root_neural_wide",
        "boolean_linear_pair_screen_neural",
        "boolean_linear_pair_screen_deep_neural",
        "boolean_linear_pair_screen_ai_guard",
        "boolean_linear_pair_screen_deep_ai_guard",
        "fprm_boolean_linear_pair_deep_neural",
        "fprm_boolean_linear_pair_deep_root_neural",
        "fprm_boolean_linear_pair_deep_ai_guard",
        "fprm_boolean_linear_pair_screen_neural",
        "fprm_boolean_linear_pair_screen_ai_guard",
    }
    use_model = model_path if base_method in neural_methods and model_path else None
    if method == "esop_greedy" and bf.n > 4:
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "skipped": "legacy ESOP greedy is limited to n<=4 in this harness",
        }
    if base_method == "esop_milp" and bf.n > 6:
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "skipped": "ESOP MILP is limited to n<=6 in this harness",
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
        timeout_s = int(config_dict.get("task_timeout_s", 0) or 0)
        if timeout_s > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout_s)
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
    finally:
        signal.alarm(0)


def _isolated_worker(task, queue):
    try:
        queue.put(run_one(task))
    except BaseException as exc:
        name, bf, method, *_ = task
        queue.put(
            {
                "name": name,
                "n": bf.n,
                "truth_table_hex": f"{bf.truth_table:X}",
                "anf_terms": len(anf_monomials(bf)),
                "method": method,
                "correct": False,
                "error": repr(exc),
                "skipped": "",
            }
        )


def run_one_isolated(task):
    """Run one task in a disposable child process with a hard wall-time cap."""
    name, bf, method, _seed, config_dict, _model_path = task
    timeout_s = int(config_dict.get("task_timeout_s", 0) or 0)
    hard_timeout = timeout_s + 30 if timeout_s > 0 else 0
    if hard_timeout <= 0:
        return run_one(task)
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_isolated_worker, args=(task, result_queue))
    proc.start()
    result = None
    deadline = time.time() + hard_timeout
    while proc.is_alive() and time.time() < deadline:
        try:
            result = result_queue.get(timeout=0.25)
            break
        except queue.Empty:
            pass
    if result is not None:
        proc.join(5)
        if proc.is_alive():
            proc.terminate()
            proc.join(5)
        return result
    proc.join(max(0.0, deadline - time.time()))
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {
            "name": name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "anf_terms": len(anf_monomials(bf)),
            "method": method,
            "correct": False,
            "error": f"ProcessTimeout({hard_timeout}s)",
            "skipped": "",
        }
    try:
        return result_queue.get_nowait()
    except queue.Empty:
        pass
    return {
        "name": name,
        "n": bf.n,
        "truth_table_hex": f"{bf.truth_table:X}",
        "anf_terms": len(anf_monomials(bf)),
        "method": method,
        "correct": False,
        "error": f"ProcessExited({proc.exitcode})",
        "skipped": "",
    }


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
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
    raise_csv_field_limit()

    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--out-dir", default=str(RESULTS))
    ap.add_argument("--resume", action="store_true", help="skip rows already present in the raw CSV")
    ap.add_argument("--only-methods", default="", help="comma-separated method subset for targeted reruns")
    ap.add_argument("--replace-methods", action="store_true", help="drop existing rows for selected methods before a resume run")
    ap.add_argument("--checkpoint-every", type=int, default=None)
    ap.add_argument("--isolate-timeouts", action="store_true", help="run tasks in disposable child processes with a hard timeout")
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
        "min_factor_count": 2,
        "use_relative_phase": True,
        "mcts_simulations": 24 if args.preset in BOUNDED_RESOURCE_PRESETS else (48 if args.preset == "pilot" else (32 if args.preset == "large" else 96)),
        "neural_mcts_simulations": 32 if args.preset in BOUNDED_RESOURCE_PRESETS else (64 if args.preset == "pilot" else (32 if args.preset == "large" else 128)),
        "max_polarities": 32 if args.preset in {"smoke", "pilot"} else (12 if args.preset in (BOUNDED_RESOURCE_PRESETS - {"smoke", "large_fast"}) else (16 if args.preset == "large_fast" else (48 if args.preset == "large" else 384))),
        "gate_mode": "mct",
        "neural_prior_weight": 10.0 if args.preset == "highdim_neural_prior" else 2.5,
        "task_timeout_s": 300 if args.preset in (BOUNDED_RESOURCE_PRESETS - {"smoke", "large_fast"}) else (120 if args.preset == "pilot" else (180 if args.preset in {"large", "large_fast"} else (300 if args.preset == "main" else 0))),
    }
    methods = cfg["methods"]
    if args.only_methods:
        requested = [m.strip() for m in args.only_methods.split(",") if m.strip()]
        unknown = sorted(set(requested) - set(methods))
        if unknown:
            raise SystemExit(f"unknown methods for preset {args.preset}: {', '.join(unknown)}")
        methods = requested
    tasks = [
        (name, bf, method, args.seed + i, config_dict, model_path)
        for i, (name, bf) in enumerate(suite)
        for method in methods
    ]
    if args.preset in HIGH_RESOURCE_PRESETS:
        method_rank = {
            "direct_anf": 0,
            "and_direct_anf": 1,
            "and_fprm_greedy": 2,
            "and_fprm_root_beam": 3,
            "and_fprm_linear_pair": 4,
            "and_fprm_linear_pair_wide": 5,
            "and_fprm_linear_pair_wide_fast": 6,
            "and_fprm_linear_pair_neural": 7,
            "and_fprm_linear_pair_root_neural": 8,
            "and_fprm_linear_pair_fast": 9,
            "and_fprm_linear_pair_fast_neural": 10,
            "and_fprm_linear_pair_fast_root_neural": 11,
            "and_fprm_linear_pair_deep": 12,
            "and_fprm_linear_pair_deep_root_neural": 13,
            "and_fprm_linear_pair_deep_ai_guard": 14,
            "and_fprm_linear_pair_deep_root_neural_wide": 15,
            "and_fprm_linear_pair_deep_ai_guard_wide": 16,
            "and_fprm_linear_pair_deep_wide": 17,
            "and_fprm_linear_pair_deep_neural": 18,
            "and_boolean_linear_pair_screen": 19,
            "and_boolean_linear_pair_screen_deep": 20,
            "and_boolean_linear_pair_screen_deeper": 21,
            "and_boolean_linear_pair_screen_neural": 22,
            "and_boolean_linear_pair_screen_deep_neural": 23,
            "and_boolean_linear_pair_screen_ai_guard": 24,
            "and_boolean_linear_pair_screen_deep_ai_guard": 25,
            "and_fprm_boolean_linear_pair": 26,
            "and_fprm_boolean_linear_pair_deep": 27,
            "and_fprm_boolean_linear_pair_deep_neural": 28,
            "and_fprm_boolean_linear_pair_deep_root_neural": 29,
            "and_fprm_boolean_linear_pair_deep_ai_guard": 30,
            "and_fprm_boolean_linear_pair_screen": 31,
            "and_fprm_boolean_linear_pair_screen_neural": 32,
            "and_fprm_boolean_linear_pair_screen_ai_guard": 33,
            "and_fprm_linear_parity": 34,
            "and_mcts_factor": 35,
            "and_affine_greedy": 36,
            "and_affine_nmcts": 37,
            "and_resource_heuristic": 38,
            "and_resource_beam_only": 39,
            "and_resource_no_mcts": 40,
            "and_resource_nmcts": 41,
            "and_resource_nmcts_wide": 42,
            "and_profile_resource_nmcts": 43,
            "and_pareto_resource_nmcts": 44,
            "and_fprm_polarity_archive": 45,
        }
        tasks.sort(key=lambda t: (method_rank.get(t[2], 99), t[1].n, t[0]))

    started = time.time()
    rows: List[dict] = []
    out_dir = Path(args.out_dir)
    raw = out_dir / f"raw_{args.preset}.csv"
    summary_path = out_dir / f"summary_{args.preset}.csv"
    manifest = out_dir / f"manifest_{args.preset}.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    workers = args.workers if args.workers is not None else cfg["workers"]
    checkpoint_every = args.checkpoint_every or (25 if args.preset.startswith("evidence") else 100)
    if args.resume and raw.exists():
        with raw.open(newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
        if args.replace_methods:
            replace_set = set(methods)
            rows = [r for r in rows if r.get("method") not in replace_set]
        completed = {(r.get("name"), r.get("method")) for r in rows}
        tasks = [task for task in tasks if (task[0], task[2]) not in completed]
        print(f"resuming from {len(rows)} rows; remaining {len(tasks)}", flush=True)
    runner = run_one_isolated if args.isolate_timeouts else run_one
    if workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(runner(task))
            if i % checkpoint_every == 0:
                write_csv(raw, rows)
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(runner, task) for task in tasks]
            for i, fut in enumerate(as_completed(futures), 1):
                rows.append(fut.result())
                if i % checkpoint_every == 0:
                    write_csv(raw, rows)
                    print(f"{i}/{len(tasks)}", flush=True)

    write_csv(raw, rows)
    summary = summarize(rows)
    write_csv(summary_path, summary)
    elapsed = time.time() - started
    manifest.write_text(
        json.dumps(
            {
                "preset": args.preset,
                "seed": args.seed,
                "functions": len(suite),
                "methods": cfg["methods"],
                "last_run_methods": methods,
                "resume": args.resume,
                "raw_rows": len(rows),
                "raw_methods": sorted({str(r.get("method", "")) for r in rows if r.get("method")}),
                "model": model_path,
                "workers": workers,
                "seconds": None if args.resume else elapsed,
                "seconds_current_run": elapsed,
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
