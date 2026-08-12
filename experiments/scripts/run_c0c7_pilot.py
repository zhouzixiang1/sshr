#!/usr/bin/env python3
"""Run the causal C0-C7 policy/value/width matrix on held-out functions.

The runner keeps the MCTS simulation budget, candidate cap, checkpoint, cases
and solver seeds fixed.  Only the three intended mechanisms change:

* action policy: heuristic, learned, shuffled learned, or conditional rollout;
* subtree value: classical greedy rollout or learned value head;
* action width: exhaustive or progressive widening.

C7 is diagnostic only.  Its scorer-free classical rollout reorders the same
model-selected top-K shortlist, so it is a conditional ranking upper bound and
not a global oracle over every legal action.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402

from scripts._pilot_artifacts import (  # noqa: E402
    dataset_sha256,
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
)
from scripts.run_prior_ablation import OraclePrior, ShuffledPrior  # noqa: E402
from src.anf_utils import anf_monomials  # noqa: E402
from src.contracts.codec import canonical_hex  # noqa: E402
from src.contracts.experiment import ExperimentManifest  # noqa: E402
from src.factor_plan import (  # noqa: E402
    SearchConfig,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import FoundationScorer, TermThresholdPolicyScorer  # noqa: E402
from src.nmcts_solver import NeuralMCTSSolver  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.search.value_net import LearnedValueEstimator, ValueStats  # noqa: E402
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)
HOLDOUT_SEED_BASE = 88000


VARIANTS = {
    "C0": {"policy": "heuristic", "value": "greedy", "width": "exhaustive"},
    "C1": {"policy": "learned", "value": "greedy", "width": "exhaustive"},
    "C2": {"policy": "heuristic", "value": "learned", "width": "exhaustive"},
    "C3": {"policy": "learned", "value": "learned", "width": "exhaustive"},
    "C4": {"policy": "heuristic", "value": "learned", "width": "progressive"},
    "C5": {"policy": "learned", "value": "learned", "width": "progressive"},
    "C6": {"policy": "shuffled_learned", "value": "learned", "width": "progressive"},
    "C7": {
        "policy": "conditional_classical_rollout",
        "value": "learned",
        "width": "progressive",
    },
}


class ExhaustiveWidthSolver(NeuralMCTSSolver):
    """Force every shortlisted action into the selection window."""

    def _considered_width(self, node) -> int:
        return len(node.actions)


def _bootstrap_mean_ci(
    values: list[float],
    *,
    seed: int,
    resamples: int = 5000,
) -> tuple[float, float]:
    """Deterministic percentile CI over independent function clusters."""

    if not values:
        raise ValueError("bootstrap values must be non-empty")
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(statistics.mean(sample))
    means.sort()
    low = means[int(0.025 * (resamples - 1))]
    high = means[int(0.975 * (resamples - 1))]
    return low, high


def _cases(sizes: list[int], per_size: int, seed_base: int) -> list[dict]:
    cases = []
    for num_vars in sizes:
        for index in range(per_size):
            instance_seed = seed_base + 1000 * num_vars + index
            rng = random.Random(instance_seed)
            bf = BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))
            terms = frozenset(anf_monomials(bf))
            if terms:
                cases.append(
                    {
                        "case_id": f"c0c7-random-n{num_vars}-k{index}",
                        "instance_seed": instance_seed,
                        "bf": bf,
                        "terms": terms,
                    }
                )
    return cases


def _build_solver(
    variant: str,
    config: SearchConfig,
    checkpoint: Path,
    simulations: int,
    solver_seed: int,
    shuffle_seed: int,
    widen_c: float,
    policy_term_threshold: int,
):
    spec = VARIANTS[variant]
    needs_model = spec["policy"] != "heuristic" or spec["value"] == "learned"
    scorer = FoundationScorer.from_checkpoint(checkpoint) if needs_model else None
    if spec["policy"] != "heuristic":
        neural_scorer = (
            TermThresholdPolicyScorer(scorer, policy_term_threshold)
            if policy_term_threshold > 0
            else scorer
        )
    else:
        neural_scorer = None
    value_stats = ValueStats()
    value_estimator = (
        LearnedValueEstimator(scorer, config, stats=value_stats)
        if spec["value"] == "learned"
        else None
    )
    kwargs = {
        "config": config,
        "simulations": simulations,
        "seed": solver_seed,
        "neural_scorer": neural_scorer,
        "value_estimator": value_estimator,
        "widen_c": widen_c,
        # Freeze the classical rollout evaluator across C0/C1.  Without this,
        # learned policy also changes the supposed greedy-value baseline and
        # the matrix cannot identify a policy main effect.
        "rollout_scorer": None,
    }
    if variant == "C6":
        solver = ShuffledPrior(**kwargs, shuffle_seed=shuffle_seed)
    elif variant == "C7":
        solver = OraclePrior(**kwargs)
    elif spec["width"] == "exhaustive":
        solver = ExhaustiveWidthSolver(**kwargs)
    else:
        solver = NeuralMCTSSolver(**kwargs)
    return solver, scorer, value_stats, neural_scorer


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="models/boolean_oracle_fm_v3.pt")
    parser.add_argument("--sizes", type=int, nargs="+", default=[6, 7, 8])
    parser.add_argument("--per-size", type=int, default=1)
    parser.add_argument("--split", choices=("validation", "test", "diagnostic"), default="diagnostic")
    parser.add_argument("--holdout-seed-base", type=int, default=HOLDOUT_SEED_BASE)
    parser.add_argument("--simulations", type=int, default=24)
    parser.add_argument("--solver-seeds", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--shuffle-seed-base", type=int, default=99000)
    parser.add_argument("--widen-c", type=float, default=2.0)
    parser.add_argument("--candidate-top-k", type=int, default=24)
    parser.add_argument(
        "--policy-term-threshold",
        type=int,
        default=0,
        help="use learned action scores only when a state has at least this many ANF terms",
    )
    parser.add_argument("--variants", nargs="+", choices=tuple(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> int:
    args = _args()
    if "C0" not in args.variants:
        raise ValueError("C0 must be included because every pilot summary is paired to C0")
    torch.set_num_threads(1)
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    checkpoint_meta = model_record(checkpoint, PROJECT_ROOT)
    config = SearchConfig(weights=PAPER_WEIGHTS, candidate_top_k=args.candidate_top_k)
    cases = _cases(args.sizes, args.per_size, args.holdout_seed_base)
    if not cases:
        raise RuntimeError("no non-empty held-out cases were generated")
    run_started = utc_now()
    run_id = args.run_id or (
        f"{run_started[:10].replace('-', '')}-{run_started[11:19].replace(':', '')}"
        "-e1-c0c7-pilot"
    )
    print(
        f"checkpoint: {args.checkpoint}  cases: {len(cases)}  "
        f"seeds: {args.solver_seeds}  simulations: {args.simulations}"
    )
    print(f"{'case':<24} {'seed':>4} {'variant':>7} {'score':>11} {'time_s':>9} {'nodes':>7}")

    raw_records = []
    for case in cases:
        bf = case["bf"]
        terms = case["terms"]
        for solver_seed in args.solver_seeds:
            for variant in args.variants:
                shuffle_seed = args.shuffle_seed_base + case["instance_seed"] + solver_seed
                setup_t0 = time.perf_counter()
                solver, scorer, value_stats, policy_scorer = _build_solver(
                    variant,
                    config,
                    checkpoint,
                    args.simulations,
                    solver_seed,
                    shuffle_seed,
                    args.widen_c,
                    args.policy_term_threshold,
                )
                setup_elapsed_s = time.perf_counter() - setup_t0
                t0 = time.perf_counter()
                plan = solver.solve(terms)
                elapsed_s = time.perf_counter() - t0
                score = plan.score(config.weights)
                circ = emit_plan_to_circuit(
                    plan,
                    bf.n,
                    min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
                )
                plan_check = verify_plan_anf(plan)
                circuit_check = verify_circuit_anf(circ, bf.n, terms)
                oracle_ok = verify_oracle(circ, bf)
                spec = VARIANTS[variant]
                row = {
                    "schema_version": "xa.c0c7-row.v1",
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "instance_seed": case["instance_seed"],
                    "n_declared": bf.n,
                    "truth_table_hex": canonical_hex(
                        int(bf.truth_table), min_nibbles=max(1, ((1 << bf.n) + 3) // 4)
                    ),
                    "anf_term_count": len(terms),
                    "variant": variant,
                    "policy": spec["policy"],
                    "value": spec["value"],
                    "width": spec["width"],
                    "solver_seed": solver_seed,
                    "shuffle_seed": shuffle_seed if variant == "C6" else None,
                    "simulations": args.simulations,
                    "widen_c": args.widen_c,
                    "candidate_top_k": args.candidate_top_k,
                    "policy_term_threshold": args.policy_term_threshold,
                    "checkpoint_sha256": checkpoint_meta["sha256"],
                    "score": score,
                    "cost": asdict(plan.cost),
                    "setup_elapsed_s": setup_elapsed_s,
                    "elapsed_s": elapsed_s,
                    "total_elapsed_s": setup_elapsed_s + elapsed_s,
                    "gates": len(circ.gates),
                    "n_qubits": circ.n_qubits,
                    "search_nodes": len(solver.nodes),
                    "node_visits": sum(node.visits for node in solver.nodes.values()),
                    "expanded_actions": sum(len(node.actions) for node in solver.nodes.values()),
                    "policy_cache_misses": int(scorer.cache_misses) if scorer else 0,
                    "policy_cache_hits": int(scorer.cache_hits) if scorer else 0,
                    "policy_gated_states": int(getattr(policy_scorer, "gated_states", 0)),
                    "policy_learned_states": int(getattr(policy_scorer, "learned_states", 0)),
                    **value_stats.as_dict(),
                    "value_mean_batch": value_stats.mean_batch,
                    "model_forward_calls_estimate": (
                        (int(scorer.cache_misses) if scorer else 0)
                        + value_stats.batches
                        + max(0, value_stats.calls - value_stats.cache_hits)
                    ),
                    "plan_anf_ok": plan_check.ok,
                    "circuit_anf_ok": circuit_check.ok,
                    "oracle_ok": oracle_ok,
                }
                raw_records.append(row)
                print(
                    f"{case['case_id']:<24} {solver_seed:>4} {variant:>7} "
                    f"{score:>11.2f} {elapsed_s:>9.3f} {len(solver.nodes):>7}",
                    flush=True,
                )

    keys = {(row["case_id"], row["solver_seed"]): row for row in raw_records if row["variant"] == "C0"}
    def cluster_summary(rows: list[dict], *, n_filter: int | None = None) -> dict:
        selected = [row for row in rows if n_filter is None or row["n_declared"] == n_filter]
        case_ids = sorted({row["case_id"] for row in selected})
        score_ratios = []
        time_ratios = []
        for case_id in case_ids:
            variant_case = [row for row in selected if row["case_id"] == case_id]
            baseline_case = [
                row
                for row in raw_records
                if row["variant"] == "C0" and row["case_id"] == case_id
            ]
            score_ratios.append(
                statistics.mean(row["score"] for row in variant_case)
                / statistics.mean(row["score"] for row in baseline_case)
            )
            time_ratios.append(
                statistics.mean(row["elapsed_s"] for row in variant_case)
                / max(statistics.mean(row["elapsed_s"] for row in baseline_case), 1e-12)
            )
        low, high = _bootstrap_mean_ci(
            score_ratios,
            seed=202609 + (n_filter or 0) + sum(ord(char) for char in selected[0]["variant"]),
        )
        return {
            "function_clusters": len(case_ids),
            "search_rows": len(selected),
            "score_ratio_mean": statistics.mean(score_ratios),
            "score_ratio_median": statistics.median(score_ratios),
            "score_ratio_mean_ci95": [low, high],
            "time_ratio_mean": statistics.mean(time_ratios),
            "wlt_by_function": {
                "wins": sum(value < 1.0 for value in score_ratios),
                "losses": sum(value > 1.0 for value in score_ratios),
                "ties": sum(value == 1.0 for value in score_ratios),
            },
        }

    variants_summary = {}
    for variant in args.variants:
        rows = [row for row in raw_records if row["variant"] == variant]
        ratios = [
            row["score"] / keys[(row["case_id"], row["solver_seed"])]["score"]
            for row in rows
        ]
        paired = [
            (row["score"], keys[(row["case_id"], row["solver_seed"])]["score"])
            for row in rows
        ]
        variants_summary[variant] = {
            "count": len(rows),
            "score_mean": statistics.mean(row["score"] for row in rows),
            "score_median": statistics.median(row["score"] for row in rows),
            "ratio_vs_c0_mean": statistics.mean(ratios),
            "elapsed_s_mean": statistics.mean(row["elapsed_s"] for row in rows),
            "setup_elapsed_s_mean": statistics.mean(row["setup_elapsed_s"] for row in rows),
            "total_elapsed_s_mean": statistics.mean(row["total_elapsed_s"] for row in rows),
            "search_nodes_mean": statistics.mean(row["search_nodes"] for row in rows),
            "model_forward_calls_estimate_mean": statistics.mean(
                row["model_forward_calls_estimate"] for row in rows
            ),
            "vs_c0_wlt": {
                "wins": sum(left < right for left, right in paired),
                "losses": sum(left > right for left, right in paired),
                "ties": sum(left == right for left, right in paired),
            },
            "paired_function_clusters": cluster_summary(rows),
            "by_n": {
                str(num_vars): cluster_summary(rows, n_filter=num_vars)
                for num_vars in sorted({row["n_declared"] for row in rows})
            },
        }
    summary = {
        "schema_version": "xa.c0c7-summary.v1",
        "run_id": run_id,
        "case_count": len(cases),
        "solver_seeds": args.solver_seeds,
        "variants": variants_summary,
        "all_plan_anf_ok": all(row["plan_anf_ok"] for row in raw_records),
        "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in raw_records),
        "all_oracle_ok": all(row["oracle_ok"] for row in raw_records),
        "claim_boundary": (
            "Pilot evidence only. C7 is conditional on the learned top-K shortlist; "
            "no multi-seed confidence interval or cross-family generalization claim is made."
        ),
    }
    expected = len(cases) * len(args.solver_seeds) * len(args.variants)
    matrix = {
        (row["case_id"], row["solver_seed"], row["variant"])
        for row in raw_records
    }
    expected_matrix = {
        (case["case_id"], seed, variant)
        for case in cases
        for seed in args.solver_seeds
        for variant in args.variants
    }
    verifier = {
        "schema_version": "xa.c0c7-verifier.v1",
        "checks": {
            "expected_record_count": len(raw_records) == expected,
            "complete_case_seed_variant_matrix": matrix == expected_matrix,
            "checkpoint_sha_consistent": all(
                row["checkpoint_sha256"] == checkpoint_meta["sha256"] for row in raw_records
            ),
            "plan_anf_100_percent": summary["all_plan_anf_ok"],
            "circuit_anf_100_percent": summary["all_circuit_anf_ok"],
            "oracle_100_percent": summary["all_oracle_ok"],
            "summary_counts_recomputed": all(
                variants_summary[variant]["count"]
                == sum(row["variant"] == variant for row in raw_records)
                for variant in args.variants
            ),
            "function_cluster_counts_recomputed": all(
                variants_summary[variant]["paired_function_clusters"]["function_clusters"]
                == len(cases)
                for variant in args.variants
            ),
            "c7_boundary_recorded": "C7 is conditional" in summary["claim_boundary"],
        },
    }
    verifier["ok"] = all(verifier["checks"].values())
    dataset = {
        "generator_id": "xa.c0c7-heldout-random.v1",
        "split": args.split,
        "holdout_seed_base": args.holdout_seed_base,
        "sizes": args.sizes,
        "per_size": args.per_size,
        "cases": [
            {
                "case_id": case["case_id"],
                "instance_seed": case["instance_seed"],
                "n_declared": case["bf"].n,
                "truth_table_hex": canonical_hex(
                    int(case["bf"].truth_table),
                    min_nibbles=max(1, ((1 << case["bf"].n) + 3) // 4),
                ),
            }
            for case in cases
        ],
        "solver_seeds": args.solver_seeds,
    }
    dataset["dataset_sha256"] = dataset_sha256(dataset)
    finished_at = utc_now()
    manifest = ExperimentManifest(
        run_id=run_id,
        track="e1-equivariant",
        experiment="c0c7-causal-pilot",
        status="complete" if verifier["ok"] else "failed",
        created_at_utc=run_started,
        source=source_record(PROJECT_ROOT),
        environment=environment_record(),
        command={
            "entrypoint": "scripts/run_c0c7_pilot.py",
            "sizes": args.sizes,
            "per_size": args.per_size,
            "split": args.split,
            "holdout_seed_base": args.holdout_seed_base,
            "simulations": args.simulations,
            "solver_seeds": args.solver_seeds,
            "widen_c": args.widen_c,
            "candidate_top_k": args.candidate_top_k,
            "policy_term_threshold": args.policy_term_threshold,
            "variants": args.variants,
        },
        dataset=dataset,
        config=asdict(config),
        model=checkpoint_meta,
        variants=tuple(args.variants),
        expected_artifacts=(
            "run.json",
            "raw.jsonl",
            "summary.json",
            "verifier.json",
            "events.jsonl",
            "stdout.log",
            "stderr.log",
            "artifacts.manifest.json",
            "checksums.sha256",
        ),
        counts={"cases": len(cases), "records": len(raw_records)},
        timing={"started_at_utc": run_started, "finished_at_utc": finished_at},
        claim_boundary=summary["claim_boundary"],
    )
    run_dir = args.out_dir.expanduser().resolve() / run_id
    bundle = write_pilot_bundle(
        run_dir=run_dir,
        run_record=manifest.to_dict(),
        raw_records=raw_records,
        summary=summary,
        verifier=verifier,
        events=(
            {"event": "run_started", "at_utc": run_started},
            {"event": "run_finished", "at_utc": finished_at, "ok": verifier["ok"]},
        ),
        track="e1-equivariant",
    )
    if not bundle.ok:
        raise RuntimeError(f"bundle verification failed: {bundle.errors}")
    print(f"bundle: {run_dir}  verifier_ok={verifier['ok']} bundle_ok={bundle.ok}")
    return 0 if verifier["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
