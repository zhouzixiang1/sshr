#!/usr/bin/env python3
"""Run the fixed-budget classical/QAOA scheduler comparison.

The experiment freezes one root candidate pool, utility vector, redundancy
matrix and expansion budget for every Boolean function.  Seven schedulers then
consume that identical instance: random, utility-only top-B, diversity-greedy,
exact, and ideal/shot/noisy QAOA.  Every selected action remains an independent
MCTS edge; no record in this runner gives simultaneous-action semantics to a
``FactorAction``.

The default matrix is the smallest pre-registered evidence matrix intended for
paper/competition use (20 held-out functions x 3 search seeds x 7 variants).
``--tiny`` retains every contract and variant while reducing the matrix for a
fast integration smoke.  Tiny output is explicitly barred from performance
claims.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


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
from src.anf_utils import anf_monomials  # noqa: E402
from src.contracts.codec import (  # noqa: E402
    canonical_hex,
    canonical_json_bytes,
    sha256_bytes,
)
from src.contracts.experiment import ExperimentManifest  # noqa: E402
from src.factor_plan import (  # noqa: E402
    SearchConfig,
    emit_plan_to_circuit,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import (  # noqa: E402
    FoundationScorer,
    TermThresholdPolicyScorer,
)
from src.nmcts_solver import NeuralMCTSSolver, StateKey  # noqa: E402
from src.resource_model import ResourceWeights  # noqa: E402
from src.search.diversity_scheduler import audit_qubo_bitstrings  # noqa: E402
from src.search.mcts_scheduler import (  # noqa: E402
    DiversitySchedulerConfig,
    MCTSDiversityScheduler,
    action_redundancy_matrix,
)
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402


PAPER_WEIGHTS = ResourceWeights(
    t=1.0,
    cnot=0.04,
    depth=0.015,
    gates=0.01,
    ancilla=2.0,
)
VARIANTS = (
    "random",
    "top_b",
    "greedy",
    "exact",
    "qaoa_ideal",
    "qaoa_shot",
    "qaoa_noisy",
)
QAOA_VARIANTS = ("qaoa_ideal", "qaoa_shot", "qaoa_noisy")
RUNNER_SCHEMA = "xa.qaoa-scheduler-runner.v1"
POOL_SCHEMA = "xa.qaoa-scheduler-pool.v1"
AUDIT_SCHEMA = "xa.qaoa-scheduler-qubo-audit.v1"
TRIAL_SCHEMA = "xa.qaoa-scheduler-trial.v1"
BOUNDARY_SCHEMA = "xa.qaoa-scheduler-boundary.v1"


@dataclass(frozen=True)
class _BoundaryAction:
    group: frozenset[int]
    rest: frozenset[int]


def _bootstrap_mean_ci(
    values: Sequence[float], *, seed: int, resamples: int
) -> tuple[float, float]:
    if not values:
        raise ValueError("bootstrap values must be non-empty")
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(statistics.mean(sample))
    means.sort()
    low = means[int(0.025 * (resamples - 1))]
    high = means[int(0.975 * (resamples - 1))]
    return float(low), float(high)


def _cases(sizes: Sequence[int], per_size: int, seed_base: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for num_vars in sizes:
        for index in range(per_size):
            instance_seed = seed_base + 1000 * int(num_vars) + index
            rng = random.Random(instance_seed)
            bf = BooleanFunction(int(num_vars), rng.getrandbits(1 << int(num_vars)))
            terms = frozenset(anf_monomials(bf))
            if not terms:
                raise RuntimeError(f"generated empty ANF for seed {instance_seed}")
            cases.append(
                {
                    "case_id": f"qaoa-random-n{num_vars}-k{index}",
                    "instance_seed": instance_seed,
                    "bf": bf,
                    "terms": terms,
                }
            )
    return cases


def _action_signature(action: object) -> dict[str, Any]:
    return {
        "factor": int(getattr(action, "factor")),
        "group": sorted(int(term) for term in getattr(action, "group")),
        "residuals": sorted(int(term) for term in getattr(action, "residuals")),
        "rest": sorted(int(term) for term in getattr(action, "rest")),
        "immediate_gain": float(getattr(action, "immediate_gain")),
        "prior": float(getattr(action, "prior")),
        "linear": bool(getattr(action, "linear", False)),
        "affine_const": bool(getattr(action, "affine_const", False)),
    }


def _auto_penalty_rho(
    utilities: Sequence[float],
    redundancy: Sequence[Sequence[float]],
    redundancy_weight: float,
) -> float:
    objective_bound = sum(abs(float(value)) for value in utilities)
    objective_bound += float(redundancy_weight) * sum(
        abs(float(redundancy[left][right]))
        for left in range(len(redundancy))
        for right in range(left + 1, len(redundancy))
    )
    return max(1.0, 2.0 * objective_bound + 1.0)


def _variant_scheduler_config(
    args: argparse.Namespace, variant: str, *, scheduler_seed: int
) -> DiversitySchedulerConfig:
    method = variant
    qaoa_mode = "shot"
    if variant.startswith("qaoa_"):
        method = "qaoa"
        qaoa_mode = variant.removeprefix("qaoa_")
    return DiversitySchedulerConfig(
        method=method,
        budget_requested=args.scheduler_budget,
        pool_size=args.scheduler_pool_size,
        min_candidates=args.scheduler_min_candidates,
        max_depth=args.scheduler_max_depth,
        redundancy_weight=args.redundancy_weight,
        redundancy_alpha=args.redundancy_alpha,
        utility_clip=args.utility_clip,
        exact_max_candidates=args.exact_max_candidates,
        seed=scheduler_seed,
        qaoa_mode=qaoa_mode,
        qaoa_p=args.qaoa_p,
        qaoa_shots=args.qaoa_shots,
        qaoa_noise_bitflip_probability=args.qaoa_noise_bitflip_probability,
        qaoa_penalty_rho=args.qaoa_penalty_rho,
        qaoa_optimizer_restarts=args.qaoa_optimizer_restarts,
        qaoa_optimizer_steps=args.qaoa_optimizer_steps,
    )


def _pool_payload(
    *,
    case: dict[str, Any],
    node_id: str,
    actions: Sequence[object],
    utilities: Sequence[float],
    redundancy: Sequence[Sequence[float]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "schema_version": POOL_SCHEMA,
        "record_type": "pool_instance",
        "case_id": case["case_id"],
        "instance_seed": case["instance_seed"],
        "n_declared": int(case["bf"].n),
        "anf_term_count": len(case["terms"]),
        "node_id": node_id,
        "candidate_count": len(actions),
        "budget_requested": args.scheduler_budget,
        "budget_effective": min(args.scheduler_budget, len(actions)),
        "action_signatures": [_action_signature(action) for action in actions],
        "utilities": [float(value) for value in utilities],
        "redundancy": [[float(value) for value in row] for row in redundancy],
        "redundancy_weight": args.redundancy_weight,
        "redundancy_alpha": args.redundancy_alpha,
    }


def _pool_fingerprint(payload: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def _angle_fingerprint(diagnostics: dict[str, Any]) -> str | None:
    qaoa = diagnostics.get("qaoa")
    if not isinstance(qaoa, dict):
        return None
    angles = {"gammas": qaoa.get("gammas"), "betas": qaoa.get("betas")}
    if angles["gammas"] is None or angles["betas"] is None:
        return None
    return sha256_bytes(canonical_json_bytes(angles))


def _qaoa_direct(diagnostics: dict[str, Any]) -> bool:
    qaoa = diagnostics.get("qaoa")
    qdiag = qaoa.get("diagnostics", {}) if isinstance(qaoa, dict) else {}
    return bool(
        diagnostics.get("qaoa_succeeded")
        and not diagnostics.get("qaoa_repaired")
        and not diagnostics.get("qaoa_fallback")
        and isinstance(qdiag, dict)
        and qdiag.get("direct_qaoa")
    )


def _boundary_actions(count: int) -> tuple[_BoundaryAction, ...]:
    return tuple(
        _BoundaryAction(
            group=frozenset({index, index + 1}),
            rest=frozenset({index % 3, (index + 2) % max(3, count + 1)}),
        )
        for index in range(count)
    )


def _boundary_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    counts = (0, args.scheduler_budget - 1, args.scheduler_budget, args.scheduler_pool_size)
    labels = ("K=0", "K<B", "K=B", "K>B")
    records = []
    for offset, (label, count) in enumerate(zip(labels, counts)):
        actions = _boundary_actions(count)
        utilities = tuple(1.0 - 0.07 * index for index in range(count))
        results: dict[str, Any] = {}
        for variant in VARIANTS:
            config = _variant_scheduler_config(
                args,
                variant,
                scheduler_seed=args.scheduler_seed_base + 100000 + offset,
            )
            decision = MCTSDiversityScheduler(config).select(
                actions,
                utilities,
                decision_seed=args.scheduler_seed_base + 200000 + offset,
            )
            results[variant] = decision.to_dict()
        records.append(
            {
                "schema_version": BOUNDARY_SCHEMA,
                "record_type": "boundary_audit",
                "boundary": label,
                "candidate_count": count,
                "budget_requested": args.scheduler_budget,
                "budget_effective": min(args.scheduler_budget, count),
                "results": results,
            }
        )
    return records


def _cluster_summary(
    rows: Sequence[dict[str, Any]],
    all_rows: Sequence[dict[str, Any]],
    *,
    baseline: str,
    resamples: int,
    n_filter: int | None = None,
) -> dict[str, Any]:
    selected = [row for row in rows if n_filter is None or row["n_declared"] == n_filter]
    if not selected:
        return {"function_clusters": 0, "search_rows": 0}
    case_ids = sorted({row["case_id"] for row in selected})
    ratios: list[float] = []
    for case_id in case_ids:
        variant_scores = [
            float(row["score"]) for row in selected if row["case_id"] == case_id
        ]
        baseline_scores = [
            float(row["score"])
            for row in all_rows
            if row["case_id"] == case_id and row["variant"] == baseline
        ]
        ratios.append(statistics.mean(variant_scores) / statistics.mean(baseline_scores))
    seed = 202609 + (n_filter or 0) + sum(ord(char) for char in selected[0]["variant"])
    low, high = _bootstrap_mean_ci(ratios, seed=seed, resamples=resamples)
    tolerance = 1e-12
    return {
        "function_clusters": len(case_ids),
        "search_rows": len(selected),
        "score_ratio_mean": statistics.mean(ratios),
        "score_ratio_median": statistics.median(ratios),
        "score_ratio_mean_ci95": [low, high],
        "wlt_by_function": {
            "wins": sum(value < 1.0 - tolerance for value in ratios),
            "losses": sum(value > 1.0 + tolerance for value in ratios),
            "ties": sum(abs(value - 1.0) <= tolerance for value in ratios),
        },
    }


def _variant_summaries(
    trials: Sequence[dict[str, Any]], *, resamples: int
) -> dict[str, Any]:
    greedy = {
        (row["case_id"], row["solver_seed"]): row
        for row in trials
        if row["variant"] == "greedy"
    }
    exact = {
        (row["case_id"], row["solver_seed"]): row
        for row in trials
        if row["variant"] == "exact"
    }
    summaries: dict[str, Any] = {}
    for variant in VARIANTS:
        rows = [row for row in trials if row["variant"] == variant]
        paired_greedy = [
            (row["score"], greedy[(row["case_id"], row["solver_seed"])]["score"])
            for row in rows
        ]
        score_ratios_greedy = [left / right for left, right in paired_greedy]
        score_ratios_exact = [
            row["score"] / exact[(row["case_id"], row["solver_seed"])]["score"]
            for row in rows
        ]
        summaries[variant] = {
            "count": len(rows),
            "score_mean": statistics.mean(row["score"] for row in rows),
            "score_median": statistics.median(row["score"] for row in rows),
            "score_ratio_vs_greedy_mean": statistics.mean(score_ratios_greedy),
            "score_ratio_vs_exact_mean": statistics.mean(score_ratios_exact),
            "scheduler_objective_mean": statistics.mean(
                row["scheduler_objective"] for row in rows
            ),
            "objective_regret_vs_exact_mean": statistics.mean(
                row["objective_regret_vs_exact"] for row in rows
            ),
            "exact_hit_rate": statistics.mean(float(row["exact_hit"]) for row in rows),
            "elapsed_s_mean": statistics.mean(row["elapsed_s"] for row in rows),
            "total_elapsed_s_mean": statistics.mean(row["total_elapsed_s"] for row in rows),
            "scheduler_wall_s_mean": statistics.mean(row["scheduler_wall_s"] for row in rows),
            "search_nodes_mean": statistics.mean(row["search_nodes"] for row in rows),
            "cost_mean": {
                field: statistics.mean(row["cost"][field] for row in rows)
                for field in ("T", "CNOT", "depth", "gates", "explicit_ancilla", "peak_ancilla")
            },
            "qaoa": {
                "attempted": sum(bool(row["qaoa_attempted"]) for row in rows),
                "succeeded": sum(bool(row["qaoa_succeeded"]) for row in rows),
                "direct_nonfallback": sum(bool(row["qaoa_direct_nonfallback"]) for row in rows),
                "repaired": sum(bool(row["qaoa_repaired"]) for row in rows),
                "fallback": sum(bool(row["qaoa_fallback"]) for row in rows),
                "not_invoked": sum(row["scheduler_status"] == "qaoa_not_invoked" for row in rows),
            },
            "vs_greedy_wlt_by_search_row": {
                "wins": sum(left < right - 1e-12 for left, right in paired_greedy),
                "losses": sum(left > right + 1e-12 for left, right in paired_greedy),
                "ties": sum(abs(left - right) <= 1e-12 for left, right in paired_greedy),
            },
            "paired_function_clusters_vs_greedy": _cluster_summary(
                rows,
                trials,
                baseline="greedy",
                resamples=resamples,
            ),
            "by_n_vs_greedy": {
                str(num_vars): _cluster_summary(
                    rows,
                    trials,
                    baseline="greedy",
                    resamples=resamples,
                    n_filter=num_vars,
                )
                for num_vars in sorted({row["n_declared"] for row in rows})
            },
        }
    return summaries


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="models/boolean_oracle_fm_v3.pt")
    parser.add_argument("--sizes", type=int, nargs="+", default=[8, 9])
    parser.add_argument("--per-size", type=int, default=10)
    parser.add_argument("--split", choices=("validation", "test", "diagnostic"), default="test")
    parser.add_argument("--holdout-seed-base", type=int, default=120000)
    parser.add_argument("--solver-seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--scheduler-seed-base", type=int, default=202609)
    parser.add_argument("--simulations", type=int, default=24)
    parser.add_argument("--candidate-top-k", type=int, default=10)
    parser.add_argument("--scheduler-pool-size", type=int, default=10)
    parser.add_argument("--scheduler-budget", type=int, default=4)
    parser.add_argument("--scheduler-min-candidates", type=int, default=6)
    parser.add_argument("--scheduler-max-depth", type=int, default=0)
    parser.add_argument("--redundancy-weight", type=float, default=0.25)
    parser.add_argument("--redundancy-alpha", type=float, default=0.7)
    parser.add_argument("--utility-clip", type=float, default=1.0)
    parser.add_argument("--exact-max-candidates", type=int, default=12)
    parser.add_argument("--policy-term-threshold", type=int, default=96)
    parser.add_argument("--qaoa-p", type=int, default=1)
    parser.add_argument("--qaoa-shots", type=int, default=1024)
    parser.add_argument("--qaoa-noise-bitflip-probability", type=float, default=0.02)
    parser.add_argument("--qaoa-penalty-rho", type=float, default=None)
    parser.add_argument("--qaoa-optimizer-restarts", type=int, default=8)
    parser.add_argument("--qaoa-optimizer-steps", type=int, default=20)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    parser.add_argument(
        "--require-direct-each-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="require at least one direct non-repaired, non-fallback row per QAOA mode",
    )
    parser.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "results" / "xa202609")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--tiny",
        action="store_true",
        help="run one n=6 case, one seed and reduced QAOA effort; never publication evidence",
    )
    return parser.parse_args()


def _apply_tiny(args: argparse.Namespace) -> argparse.Namespace:
    if not args.tiny:
        return args
    args.sizes = [6]
    args.per_size = 1
    args.solver_seeds = [1]
    args.simulations = 4
    args.candidate_top_k = 6
    args.scheduler_pool_size = 6
    args.scheduler_budget = 2
    args.scheduler_min_candidates = 4
    args.exact_max_candidates = max(args.exact_max_candidates, 6)
    args.qaoa_shots = 128
    args.qaoa_optimizer_restarts = 2
    args.qaoa_optimizer_steps = 4
    args.bootstrap_resamples = min(args.bootstrap_resamples, 200)
    args.require_direct_each_mode = False
    return args


def _validate_args(args: argparse.Namespace) -> None:
    if not args.sizes or any(size < 1 or size > 12 for size in args.sizes):
        raise ValueError("sizes must lie in [1, 12]")
    if args.per_size < 1:
        raise ValueError("per_size must be positive")
    if not args.solver_seeds or len(set(args.solver_seeds)) != len(args.solver_seeds):
        raise ValueError("solver_seeds must be non-empty and unique")
    if args.scheduler_budget < 2:
        raise ValueError("scheduler_budget must be >= 2 to cover the K<B boundary")
    if args.scheduler_pool_size <= args.scheduler_budget:
        raise ValueError("scheduler_pool_size must exceed scheduler_budget")
    if args.scheduler_pool_size > 12:
        raise ValueError("scheduler_pool_size exceeds the 12-qubit QAOA backend")
    if args.candidate_top_k < args.scheduler_pool_size:
        raise ValueError("candidate_top_k must be >= scheduler_pool_size")
    if args.scheduler_min_candidates > args.scheduler_pool_size:
        raise ValueError("scheduler_min_candidates must be <= scheduler_pool_size")
    if args.exact_max_candidates < args.scheduler_pool_size:
        raise ValueError("exact_max_candidates must cover scheduler_pool_size")
    if args.simulations < args.scheduler_budget:
        raise ValueError("simulations must visit every admitted root edge at least once")
    if args.policy_term_threshold < 0:
        raise ValueError("policy_term_threshold must be non-negative")
    if args.bootstrap_resamples < 1:
        raise ValueError("bootstrap_resamples must be positive")
    # Exercise the complete config validator before any expensive model load.
    _variant_scheduler_config(args, "qaoa_noisy", scheduler_seed=args.scheduler_seed_base)


def main() -> int:
    args = _apply_tiny(_args())
    _validate_args(args)
    torch.set_num_threads(1)

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    checkpoint_meta = model_record(checkpoint, PROJECT_ROOT)
    search_config = SearchConfig(
        weights=PAPER_WEIGHTS,
        candidate_top_k=args.candidate_top_k,
        mcts_simulations=args.simulations,
        neural_mcts_simulations=args.simulations,
    )
    cases = _cases(args.sizes, args.per_size, args.holdout_seed_base)
    started_at = utc_now()
    wall_started = time.perf_counter()
    run_id = args.run_id or (
        f"{started_at[:10].replace('-', '')}-{started_at[11:19].replace(':', '')}"
        f"-e2-qaoa-{'tiny' if args.tiny else 'scheduler-v1'}-s{args.holdout_seed_base}"
    )

    print(
        f"cases={len(cases)} seeds={args.solver_seeds} variants={len(VARIANTS)} "
        f"K={args.scheduler_pool_size} B={args.scheduler_budget} simulations={args.simulations}",
        flush=True,
    )
    print(f"{'case':<24} {'seed':>4} {'variant':>12} {'score':>11} {'objective':>10} {'time_s':>9}")

    trials: list[dict[str, Any]] = []
    pools: dict[str, dict[str, Any]] = {}
    pool_hashes: dict[str, str] = {}
    audits: dict[str, dict[str, Any]] = {}

    for case in cases:
        bf = case["bf"]
        terms = case["terms"]
        for solver_seed in args.solver_seeds:
            scheduler_seed = args.scheduler_seed_base + int(solver_seed)
            for variant in VARIANTS:
                setup_started = time.perf_counter()
                scorer = FoundationScorer.from_checkpoint(checkpoint)
                policy_scorer = (
                    TermThresholdPolicyScorer(scorer, args.policy_term_threshold)
                    if args.policy_term_threshold > 0
                    else scorer
                )
                scheduler_config = _variant_scheduler_config(
                    args,
                    variant,
                    scheduler_seed=scheduler_seed,
                )
                solver = NeuralMCTSSolver(
                    config=search_config,
                    simulations=args.simulations,
                    seed=solver_seed,
                    neural_scorer=policy_scorer,
                    value_estimator=None,
                    rollout_scorer=None,
                    scheduler_config=scheduler_config,
                )
                setup_elapsed = time.perf_counter() - setup_started
                solve_started = time.perf_counter()
                plan = solver.solve(terms)
                solve_elapsed = time.perf_counter() - solve_started

                root = solver.nodes.get(StateKey(terms, 0, 0))
                if root is None or root.scheduler_decision is None or root.admitted_indices is None:
                    raise RuntimeError(
                        f"root scheduler was not invoked for {case['case_id']} / {variant}"
                    )
                decision = root.scheduler_decision
                diagnostics = dict(decision.diagnostics)
                pool_width = int(diagnostics["pool_width"])
                pool_actions = tuple(root.actions[:pool_width])
                utilities = tuple(float(value) for value in diagnostics["utilities"])
                redundancy = action_redundancy_matrix(
                    pool_actions,
                    alpha=args.redundancy_alpha,
                )
                pool_payload = _pool_payload(
                    case=case,
                    node_id=str(diagnostics["node_id"]),
                    actions=pool_actions,
                    utilities=utilities,
                    redundancy=redundancy,
                    args=args,
                )
                fingerprint = _pool_fingerprint(pool_payload)
                prior_fingerprint = pool_hashes.get(case["case_id"])
                pool_match = prior_fingerprint is None or prior_fingerprint == fingerprint
                if prior_fingerprint is None:
                    pool_hashes[case["case_id"]] = fingerprint
                    pool_payload["pool_instance_sha256"] = fingerprint
                    pools[case["case_id"]] = pool_payload
                    rho = args.qaoa_penalty_rho or _auto_penalty_rho(
                        utilities,
                        redundancy,
                        args.redundancy_weight,
                    )
                    audit = audit_qubo_bitstrings(
                        utilities,
                        redundancy,
                        min(args.scheduler_budget, pool_width),
                        redundancy_weight=args.redundancy_weight,
                        rho=rho,
                        max_candidates=args.exact_max_candidates,
                    )
                    audits[case["case_id"]] = {
                        "schema_version": AUDIT_SCHEMA,
                        "record_type": "qubo_audit",
                        "case_id": case["case_id"],
                        "pool_instance_sha256": fingerprint,
                        "rho": rho,
                        "diagnostics": audit.diagnostics.to_dict(),
                    }

                circuit = emit_plan_to_circuit(
                    plan,
                    bf.n,
                    min(search_config.max_factor_ancilla, plan.cost.explicit_ancilla),
                )
                plan_check = verify_plan_anf(plan)
                circuit_check = verify_circuit_anf(circuit, bf.n, terms)
                oracle_ok = verify_oracle(circuit, bf)

                selected = tuple(int(index) for index in decision.selected_indices)
                action_visits = [root.stats[index].visits for index in range(len(root.actions))]
                selected_set = set(selected)
                selected_visits = [action_visits[index] for index in selected]
                excluded_visits = sum(
                    visits
                    for index, visits in enumerate(action_visits)
                    if index not in selected_set
                )
                scheduler_objective = diagnostics.get(
                    "effective_objective",
                    diagnostics.get("objective"),
                )
                if scheduler_objective is None:
                    raise RuntimeError("scheduler did not report its effective objective")
                scheduler_summary = solver.scheduler_summary()
                trial = {
                    "schema_version": TRIAL_SCHEMA,
                    "record_type": "scheduler_trial",
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "instance_seed": case["instance_seed"],
                    "n_declared": bf.n,
                    "truth_table_hex": canonical_hex(
                        int(bf.truth_table),
                        min_nibbles=max(1, ((1 << bf.n) + 3) // 4),
                    ),
                    "anf_term_count": len(terms),
                    "variant": variant,
                    "solver_seed": solver_seed,
                    "scheduler_seed": scheduler_seed,
                    "simulations": args.simulations,
                    "checkpoint_sha256": checkpoint_meta["sha256"],
                    "pool_instance_sha256": fingerprint,
                    "pool_match": pool_match,
                    "candidate_count": pool_width,
                    "budget_requested": args.scheduler_budget,
                    "budget_effective": min(args.scheduler_budget, pool_width),
                    "selected_indices": list(selected),
                    "selected_action_visits": selected_visits,
                    "selected_action_visits_total": sum(selected_visits),
                    "excluded_action_visits_total": excluded_visits,
                    "pending_indices_after_solve": list(root.pending_indices),
                    "scheduler_status": diagnostics.get("status"),
                    "scheduler_objective": float(scheduler_objective),
                    "objective_regret_vs_exact": None,
                    "exact_hit": None,
                    "qaoa_mode": (
                        scheduler_config.qaoa_mode if variant in QAOA_VARIANTS else None
                    ),
                    "qaoa_attempted": bool(diagnostics.get("qaoa_attempted")),
                    "qaoa_succeeded": bool(diagnostics.get("qaoa_succeeded")),
                    "qaoa_direct_nonfallback": _qaoa_direct(diagnostics),
                    "qaoa_repaired": bool(diagnostics.get("qaoa_repaired")),
                    "qaoa_fallback": bool(diagnostics.get("qaoa_fallback")),
                    "qaoa_angle_sha256": _angle_fingerprint(diagnostics),
                    "scheduler_diagnostics": diagnostics,
                    "score": plan.score(search_config.weights),
                    "cost": asdict(plan.cost),
                    "gates": len(circuit.gates),
                    "n_qubits": circuit.n_qubits,
                    "search_nodes": len(solver.nodes),
                    "node_visits": sum(node.visits for node in solver.nodes.values()),
                    "root_visits": root.visits,
                    "scheduler_wall_s": float(scheduler_summary["scheduler_wall_s"]),
                    "setup_elapsed_s": setup_elapsed,
                    "elapsed_s": solve_elapsed,
                    "total_elapsed_s": setup_elapsed + solve_elapsed,
                    "policy_cache_misses": int(scorer.cache_misses),
                    "policy_cache_hits": int(scorer.cache_hits),
                    "policy_gated_states": int(getattr(policy_scorer, "gated_states", 0)),
                    "policy_learned_states": int(getattr(policy_scorer, "learned_states", 0)),
                    "root_policy_expected_active": (
                        args.policy_term_threshold == 0
                        or len(terms) >= args.policy_term_threshold
                    ),
                    "plan_anf_ok": plan_check.ok,
                    "circuit_anf_ok": circuit_check.ok,
                    "oracle_ok": oracle_ok,
                }
                trials.append(trial)
                print(
                    f"{case['case_id']:<24} {solver_seed:>4} {variant:>12} "
                    f"{trial['score']:>11.3f} {trial['scheduler_objective']:>10.5f} "
                    f"{solve_elapsed:>9.3f}",
                    flush=True,
                )

    exact_objectives = {
        (row["case_id"], row["solver_seed"]): row["scheduler_objective"]
        for row in trials
        if row["variant"] == "exact"
    }
    for row in trials:
        exact_objective = exact_objectives[(row["case_id"], row["solver_seed"])]
        regret = float(exact_objective) - float(row["scheduler_objective"])
        row["objective_regret_vs_exact"] = regret
        row["exact_hit"] = abs(regret) <= 1e-9

    boundary_records = _boundary_records(args)
    variant_summaries = _variant_summaries(
        trials,
        resamples=args.bootstrap_resamples,
    )
    claim_boundary = (
        "Execution-contract smoke only; --tiny results are not performance evidence. "
        if args.tiny
        else "Held-out random n=8,9 fixed-K/B evidence with function-cluster inference. "
    ) + (
        "The QAOA backend is a small NumPy statevector simulator at fixed p; noisy mode "
        "uses independent measurement bit flips only. Ideal returns the statevector modal "
        "outcome, while shot/noisy return the best feasible sampled outcome, so ideal is not "
        "an infinite-shot noise baseline. Learned value is disabled. No quantum speedup, "
        "hardware performance, or universal advantage is claimed."
    )
    summary = {
        "schema_version": "xa.qaoa-scheduler-summary.v1",
        "run_id": run_id,
        "case_count": len(cases),
        "pool_count": len(pools),
        "qubo_audit_count": len(audits),
        "boundary_audit_count": len(boundary_records),
        "trial_count": len(trials),
        "solver_seeds": args.solver_seeds,
        "variants": variant_summaries,
        "all_plan_anf_ok": all(row["plan_anf_ok"] for row in trials),
        "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in trials),
        "all_oracle_ok": all(row["oracle_ok"] for row in trials),
        "claim_boundary": claim_boundary,
    }

    expected_trials = len(cases) * len(args.solver_seeds) * len(VARIANTS)
    actual_matrix = {
        (row["case_id"], row["solver_seed"], row["variant"])
        for row in trials
    }
    expected_matrix = {
        (case["case_id"], seed, variant)
        for case in cases
        for seed in args.solver_seeds
        for variant in VARIANTS
    }
    audit_checks = [record["diagnostics"] for record in audits.values()]
    boundary_budget_ok = all(
        len(payload["selected_indices"]) == record["budget_effective"]
        and len(set(payload["selected_indices"])) == record["budget_effective"]
        for record in boundary_records
        for payload in record["results"].values()
    )
    boundary_status_ok = True
    for record in boundary_records:
        candidate_count = int(record["candidate_count"])
        for variant, payload in record["results"].items():
            diagnostics = payload["diagnostics"]
            status = diagnostics.get("status")
            if variant in QAOA_VARIANTS:
                if candidate_count <= args.scheduler_budget:
                    boundary_status_ok &= (
                        status == "qaoa_not_invoked"
                        and not diagnostics.get("qaoa_attempted")
                    )
                else:
                    boundary_status_ok &= bool(diagnostics.get("qaoa_attempted"))
                    boundary_status_ok &= status in {"qaoa_selected", "qaoa_fallback"}
            elif candidate_count == 0:
                boundary_status_ok &= status == "skipped_no_candidates"
            elif candidate_count <= args.scheduler_budget:
                boundary_status_ok &= status == "skipped_budget_covers_pool"
            else:
                boundary_status_ok &= status == "selected"
    qaoa_rows = [row for row in trials if row["variant"] in QAOA_VARIANTS]
    direct_by_mode = {
        variant: sum(
            row["qaoa_direct_nonfallback"]
            for row in qaoa_rows
            if row["variant"] == variant
        )
        for variant in QAOA_VARIANTS
    }
    angle_groups: dict[tuple[str, int], set[str]] = {}
    for row in qaoa_rows:
        if row["qaoa_angle_sha256"] is not None:
            angle_groups.setdefault((row["case_id"], row["solver_seed"]), set()).add(
                row["qaoa_angle_sha256"]
            )
    qaoa_accounted = all(
        row["qaoa_attempted"]
        and (
            (row["qaoa_succeeded"] and not row["qaoa_fallback"])
            or (row["qaoa_fallback"] and not row["qaoa_succeeded"])
        )
        for row in qaoa_rows
    )
    checks = {
        "expected_trial_count": len(trials) == expected_trials,
        "complete_case_seed_variant_matrix": actual_matrix == expected_matrix,
        "one_frozen_pool_per_case": len(pools) == len(cases),
        "pool_fingerprint_identical_across_variants_and_seeds": all(
            row["pool_match"] for row in trials
        ),
        "primary_pool_has_frozen_K": all(
            row["candidate_count"] == args.scheduler_pool_size for row in trials
        ),
        "selection_has_exact_effective_budget": all(
            len(row["selected_indices"]) == row["budget_effective"]
            and len(set(row["selected_indices"])) == row["budget_effective"]
            for row in trials
        ),
        "excluded_root_edges_never_visited": all(
            row["excluded_action_visits_total"] == 0 for row in trials
        ),
        "one_root_edge_evaluation_per_simulation": all(
            row["selected_action_visits_total"] == args.simulations
            and row["root_visits"] == args.simulations
            for row in trials
        ),
        "every_selected_root_edge_visited": all(
            all(visits >= 1 for visits in row["selected_action_visits"])
            and not row["pending_indices_after_solve"]
            for row in trials
        ),
        "qubo_energy_identity_all_pools": all(
            item["energy_identity_holds"] for item in audit_checks
        ),
        "qubo_feasible_ordering_all_pools": all(
            item["feasible_ordering_matches"] for item in audit_checks
        ),
        "qubo_penalty_sufficient_all_pools": all(
            item["penalty_sufficient"] and item["all_global_minima_feasible"]
            for item in audit_checks
        ),
        "boundary_matrix_exact_budget": boundary_budget_ok,
        "boundary_invocation_statuses_explicit": boundary_status_ok,
        "qaoa_primary_rows_all_attempted_and_accounted": qaoa_accounted,
        "qaoa_angles_paired_across_modes_when_available": all(
            len(values) == 1 for values in angle_groups.values()
        ),
        "qaoa_objective_never_exceeds_exact_beyond_tolerance": all(
            row["objective_regret_vs_exact"] >= -1e-9 for row in trials
        ),
        "direct_nonfallback_requirement": (
            not args.require_direct_each_mode
            or all(direct_by_mode[variant] > 0 for variant in QAOA_VARIANTS)
        ),
        "checkpoint_sha_consistent": all(
            row["checkpoint_sha256"] == checkpoint_meta["sha256"] for row in trials
        ),
        "root_policy_active_for_claim_matrix": (
            args.tiny or all(row["root_policy_expected_active"] for row in trials)
        ),
        "plan_anf_100_percent": summary["all_plan_anf_ok"],
        "circuit_anf_100_percent": summary["all_circuit_anf_ok"],
        "oracle_100_percent": summary["all_oracle_ok"],
        "summary_counts_recomputed": all(
            variant_summaries[variant]["count"]
            == sum(row["variant"] == variant for row in trials)
            for variant in VARIANTS
        ),
    }
    verifier = {
        "schema_version": "xa.qaoa-scheduler-verifier.v1",
        "checks": checks,
        "observations": {
            "direct_nonfallback_by_mode": direct_by_mode,
            "qaoa_attempted": sum(row["qaoa_attempted"] for row in qaoa_rows),
            "qaoa_succeeded": sum(row["qaoa_succeeded"] for row in qaoa_rows),
            "qaoa_repaired": sum(row["qaoa_repaired"] for row in qaoa_rows),
            "qaoa_fallback": sum(row["qaoa_fallback"] for row in qaoa_rows),
            "require_direct_each_mode": args.require_direct_each_mode,
        },
    }
    verifier["ok"] = all(checks.values())

    dataset = {
        "generator_id": "xa.qaoa-heldout-random.v1",
        "split": args.split,
        "holdout_seed_base": args.holdout_seed_base,
        "sizes": list(args.sizes),
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
                "anf_term_count": len(case["terms"]),
            }
            for case in cases
        ],
        "solver_seeds": list(args.solver_seeds),
    }
    dataset["dataset_sha256"] = dataset_sha256(dataset)
    finished_at = utc_now()
    total_wall_s = time.perf_counter() - wall_started
    qaoa_reference_config = _variant_scheduler_config(
        args,
        "qaoa_shot",
        scheduler_seed=args.scheduler_seed_base,
    )
    manifest = ExperimentManifest(
        run_id=run_id,
        track="e2-qaoa",
        experiment="fixed-budget-diversity-scheduler-comparison",
        status="complete" if verifier["ok"] else "failed",
        created_at_utc=started_at,
        source=source_record(PROJECT_ROOT),
        environment=environment_record(),
        command={
            "entrypoint": "scripts/run_qaoa_scheduler_pilot.py",
            "tiny": args.tiny,
            "sizes": list(args.sizes),
            "per_size": args.per_size,
            "split": args.split,
            "holdout_seed_base": args.holdout_seed_base,
            "solver_seeds": list(args.solver_seeds),
            "scheduler_seed_base": args.scheduler_seed_base,
            "simulations": args.simulations,
            "candidate_top_k": args.candidate_top_k,
            "policy_term_threshold": args.policy_term_threshold,
            "variants": list(VARIANTS),
        },
        dataset=dataset,
        config={
            "runner_schema": RUNNER_SCHEMA,
            "search": asdict(search_config),
            "scheduler_reference": qaoa_reference_config.to_dict(),
            "variant_mapping": {
                variant: _variant_scheduler_config(
                    args,
                    variant,
                    scheduler_seed=args.scheduler_seed_base,
                ).to_dict()
                for variant in VARIANTS
            },
            "bootstrap_resamples": args.bootstrap_resamples,
            "require_direct_each_mode": args.require_direct_each_mode,
        },
        model=checkpoint_meta,
        variants=VARIANTS,
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
        counts={
            "cases": len(cases),
            "pools": len(pools),
            "qubo_audits": len(audits),
            "boundary_audits": len(boundary_records),
            "trials": len(trials),
            "records": len(pools) + len(audits) + len(boundary_records) + len(trials),
        },
        timing={
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
            "total_wall_s": total_wall_s,
        },
        claim_boundary=claim_boundary,
    )
    raw_records: list[dict[str, Any]] = [
        *[pools[key] for key in sorted(pools)],
        *[audits[key] for key in sorted(audits)],
        *boundary_records,
        *trials,
    ]
    run_dir = args.out_dir.expanduser().resolve() / run_id
    bundle = write_pilot_bundle(
        run_dir=run_dir,
        run_record=manifest.to_dict(),
        raw_records=raw_records,
        summary=summary,
        verifier=verifier,
        events=(
            {"event": "run_started", "at_utc": started_at},
            {
                "event": "run_finished",
                "at_utc": finished_at,
                "ok": verifier["ok"],
                "total_wall_s": total_wall_s,
            },
        ),
        track="e2-qaoa",
    )
    if not bundle.ok:
        raise RuntimeError(f"bundle verification failed: {bundle.errors}")
    print(
        f"bundle={run_dir} verifier_ok={verifier['ok']} bundle_ok={bundle.ok} "
        f"wall_s={total_wall_s:.3f}",
        flush=True,
    )
    return 0 if verifier["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
