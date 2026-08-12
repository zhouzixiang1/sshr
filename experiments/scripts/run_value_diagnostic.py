#!/usr/bin/env python3
"""Measure how accurate the value head actually is, and against what.

The search's quality gap traces back to value-estimate error, so this reports
the error directly rather than inferring it from final scores.  Three things
matter and each is easy to get wrong:

1. **The right reference.**  The head is *trained* on the MCTS-achieved value
   (``min`` over visited action stats) but *deployed* as a replacement for
   ``greedy_plan``'s score.  Those need not be the same quantity; if they drift
   apart the head is optimised for something it is never asked to do.  Both are
   reported.

2. **The right baseline.**  An R^2 near zero can still look like a small MAE
   when the targets are tightly clustered.  The constant predictor (always
   predict the mean log-ratio) is the honest floor -- a head that cannot beat it
   has learned nothing, whatever its raw MAE.

3. **Bias direction.**  Underestimating is *optimism* in a minimisation search,
   and optimistic values are what made ``_build_best`` recurse into every branch
   (docs/project/TECHNICAL_DESIGN.md section 3.3b).  Signed mean error is reported separately
   from magnitude.

Held-out states come from a seed stream disjoint from the training script's, and
the states are harvested from real search trees rather than sampled
independently, so the distribution matches what the deployed search actually
queries.

Usage:
    python scripts/run_value_diagnostic.py --checkpoint models/boolean_oracle_fm.pt
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from dataclasses import asdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch

from src.anf_utils import anf_monomials
from src.contracts.codec import canonical_hex
from src.contracts.experiment import ExperimentManifest
from src.factor_plan import SearchConfig, greedy_plan
from src.foundation.adapter import FoundationScorer
from src.nmcts_solver import NeuralMCTSSolver
from src.resource_model import ResourceWeights
from src.sshr_lib.bool_func import BooleanFunction
from scripts._pilot_artifacts import (
    dataset_sha256,
    environment_record,
    model_record,
    source_record,
    utc_now,
    write_pilot_bundle,
)

PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)

#: Disjoint from train_expert_iteration.py, which draws on seed + 1..iterations
#: and seed + 9999.  Keep these apart or the "held-out" set is nothing of the kind.
HOLDOUT_SEED_BASE = 77000

MIN_LOG_RATIO = -3.0


def harvest(config, scorer, sizes, per_size, simulations, solver_seed=1):
    """Collect structured deployed/training target records from held-out trees."""
    rows = []
    for num_vars in sizes:
        for k in range(per_size):
            instance_seed = HOLDOUT_SEED_BASE + 1000 * num_vars + k
            case_id = f"heldout-random-n{num_vars}-k{k}"
            rng = random.Random(instance_seed)
            bf = BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))
            terms = frozenset(anf_monomials(bf))
            if not terms:
                continue
            solver = NeuralMCTSSolver(
                config, simulations=simulations, seed=solver_seed, neural_scorer=scorer
            )
            solver.solve(terms)
            ordered_nodes = sorted(
                solver.nodes.items(),
                key=lambda item: (
                    item[0].prefix_len,
                    item[0].live_factor_ancilla,
                    tuple(sorted(item[0].terms)),
                ),
            )
            for state_index, (key, node) in enumerate(ordered_nodes):
                if not key.terms or not node.visits:
                    continue
                direct = node.direct.score(config.weights)
                if direct <= 0:
                    continue
                deployed = greedy_plan(
                    key.terms, key.prefix_len, key.live_factor_ancilla, config, scorer, {}
                ).score(config.weights)
                achieved = min(
                    (st.q for st in node.stats.values() if st.visits > 0), default=direct
                )
                deployed_log_ratio = math.log(
                    max(deployed / direct, math.exp(MIN_LOG_RATIO))
                )
                training_log_ratio = math.log(
                    max(min(achieved / direct, 1.0), math.exp(MIN_LOG_RATIO))
                )
                predicted_log_ratio = scorer.predict_log_ratio(
                    key.terms, key.prefix_len, key.live_factor_ancilla, config
                )
                rows.append(
                    {
                        "schema_version": "xa.value-diagnostic-row.v1",
                        "case_id": case_id,
                        "state_id": f"{case_id}-state-{state_index:04d}",
                        "n_declared": num_vars,
                        "truth_table_hex": canonical_hex(
                            int(bf.truth_table),
                            min_nibbles=max(1, ((1 << num_vars) + 3) // 4),
                        ),
                        "terms_hex": [canonical_hex(term) for term in sorted(key.terms)],
                        "term_count": len(key.terms),
                        "prefix_len": key.prefix_len,
                        "live_factor_ancilla": key.live_factor_ancilla,
                        "direct_score": direct,
                        "greedy_score": deployed,
                        "achieved_score": achieved,
                        "deployed_log_ratio": deployed_log_ratio,
                        "training_log_ratio": training_log_ratio,
                        "predicted_log_ratio": predicted_log_ratio,
                        "instance_seed": instance_seed,
                        "solver_seed": solver_seed,
                        "simulations": simulations,
                    }
                )
    return rows


def metrics(truth: list[float], pred: list[float]) -> dict[str, float | int | None | str]:
    mean_truth = statistics.mean(truth)
    variance = statistics.pvariance(truth)
    mae = statistics.mean(abs(p - t) for p, t in zip(pred, truth))
    mae_constant = statistics.mean(abs(mean_truth - t) for t in truth)
    mse = statistics.mean((p - t) ** 2 for p, t in zip(pred, truth))
    bias = statistics.mean(p - t for p, t in zip(pred, truth))
    return {
        "count": len(truth),
        "truth_mean": mean_truth,
        "truth_sd": math.sqrt(variance),
        "truth_min": min(truth),
        "truth_max": max(truth),
        "network_mae": mae,
        "network_mse": mse,
        "network_r2": 1 - mse / variance if variance > 0 else None,
        "network_bias": bias,
        "bias_direction": "optimistic" if bias < 0 else "pessimistic",
        "constant_mae": mae_constant,
        "network_vs_constant_factor": mae_constant / mae if mae > 0 else None,
    }


def report(name: str, result: dict[str, float | int | None | str]) -> None:
    print(f"\n{name}")
    print(
        f"   truth      mean={result['truth_mean']:+.4f}  sd={result['truth_sd']:.4f}"
        f"  range=[{result['truth_min']:+.3f}, {result['truth_max']:+.3f}]"
    )
    r2_text = f"{result['network_r2']:+.3f}" if result["network_r2"] is not None else "undefined"
    print(
        f"   network    MAE={result['network_mae']:.4f}   R2={r2_text}"
        f"   bias={result['network_bias']:+.4f} ({result['bias_direction']})"
    )
    factor = result["network_vs_constant_factor"]
    factor_text = f"{factor:.2f}x" if factor is not None else "undefined"
    print(
        f"   constant   MAE={result['constant_mae']:.4f}   -> network is "
        f"{factor_text} better than predicting the mean"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=str, default="models/boolean_oracle_fm_v3.pt")
    parser.add_argument("--sizes", type=int, nargs="+", default=[5, 6, 7])
    parser.add_argument("--per-size", type=int, default=3)
    parser.add_argument("--simulations", type=int, default=48)
    parser.add_argument("--solver-seed", type=int, default=1)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    args = parser.parse_args()

    torch.set_num_threads(1)
    config = SearchConfig(weights=PAPER_WEIGHTS)
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    checkpoint_meta = model_record(checkpoint, _PROJECT_ROOT)
    scorer = FoundationScorer.from_checkpoint(checkpoint)
    run_started = utc_now()
    rows = harvest(
        config,
        scorer,
        args.sizes,
        args.per_size,
        args.simulations,
        solver_seed=args.solver_seed,
    )
    if not rows:
        print("no held-out states harvested")
        return 1

    deployed = [r["deployed_log_ratio"] for r in rows]
    trained_on = [r["training_log_ratio"] for r in rows]
    pred = [r["predicted_log_ratio"] for r in rows]
    deployed_metrics = metrics(deployed, pred)
    training_metrics = metrics(trained_on, pred)

    print(f"checkpoint: {args.checkpoint}")
    print(f"held-out states: {len(rows)}  (sizes {args.sizes})")
    report("vs GREEDY value  -- what the head replaces at deploy time", deployed_metrics)
    report("vs MCTS-achieved -- what training regressed onto", training_metrics)

    drift = statistics.mean(d - t for d, t in zip(deployed, trained_on))
    print(
        f"\ntarget drift (deployed - trained-on): {drift:+.4f} log units"
        f"  -- large values mean the head is optimised for the wrong quantity"
    )

    if args.out_dir is not None:
        finished_at = utc_now()
        run_id = args.run_id or (
            f"{run_started[:10].replace('-', '')}-{run_started[11:19].replace(':', '')}"
            f"-e1-value-pilot-s{args.solver_seed}"
        )
        for row in rows:
            row["checkpoint_sha256"] = checkpoint_meta["sha256"]
        summary = {
            "schema_version": "xa.value-diagnostic-summary.v1",
            "run_id": run_id,
            "state_count": len(rows),
            "deployed_target": deployed_metrics,
            "training_target": training_metrics,
            "target_drift_deployed_minus_training": drift,
        }
        unique_states = len({row["state_id"] for row in rows}) == len(rows)
        finite_values = all(
            math.isfinite(float(row[field]))
            for row in rows
            for field in (
                "direct_score",
                "greedy_score",
                "achieved_score",
                "deployed_log_ratio",
                "training_log_ratio",
                "predicted_log_ratio",
            )
        )
        recomputed_deployed = metrics(
            [row["deployed_log_ratio"] for row in rows],
            [row["predicted_log_ratio"] for row in rows],
        )
        recomputed_training = metrics(
            [row["training_log_ratio"] for row in rows],
            [row["predicted_log_ratio"] for row in rows],
        )
        verifier = {
            "schema_version": "xa.value-diagnostic-verifier.v1",
            "checks": {
                "nonempty_heldout_states": bool(rows),
                "unique_state_ids": unique_states,
                "all_numeric_values_finite": finite_values,
                "checkpoint_sha_consistent": all(
                    row["checkpoint_sha256"] == checkpoint_meta["sha256"] for row in rows
                ),
                "deployed_summary_recomputed": recomputed_deployed == deployed_metrics,
                "training_summary_recomputed": recomputed_training == training_metrics,
                "state_count_recomputed": summary["state_count"] == len(rows),
            },
        }
        verifier["ok"] = all(verifier["checks"].values())
        cases_by_id = {}
        for row in rows:
            cases_by_id.setdefault(
                row["case_id"],
                {
                    "case_id": row["case_id"],
                    "n_declared": row["n_declared"],
                    "truth_table_hex": row["truth_table_hex"],
                    "instance_seed": row["instance_seed"],
                },
            )
        dataset = {
            "generator_id": "xa.heldout-search-state-value.v1",
            "holdout_seed_base": HOLDOUT_SEED_BASE,
            "sizes": args.sizes,
            "per_size": args.per_size,
            "cases": sorted(cases_by_id.values(), key=lambda item: item["case_id"]),
            "solver_seed": args.solver_seed,
        }
        dataset["dataset_sha256"] = dataset_sha256(dataset)
        manifest = ExperimentManifest(
            run_id=run_id,
            track="e1-equivariant",
            experiment="value-diagnostic",
            status="complete" if verifier["ok"] else "failed",
            created_at_utc=run_started,
            source=source_record(_PROJECT_ROOT),
            environment=environment_record(),
            command={
                "entrypoint": "scripts/run_value_diagnostic.py",
                "sizes": args.sizes,
                "per_size": args.per_size,
                "simulations": args.simulations,
                "solver_seed": args.solver_seed,
            },
            dataset=dataset,
            config=asdict(config),
            model=checkpoint_meta,
            variants=("deployed-greedy-target", "training-mcts-achieved-target", "constant-mean"),
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
            counts={"cases": len(cases_by_id), "states": len(rows)},
            timing={"started_at_utc": run_started, "finished_at_utc": finished_at},
            claim_boundary=(
                "This diagnostic measures held-out value-target error on harvested search states. "
                "It does not by itself establish end-to-end synthesis improvement."
            ),
        )
        run_dir = args.out_dir.expanduser().resolve() / run_id
        bundle = write_pilot_bundle(
            run_dir=run_dir,
            run_record=manifest.to_dict(),
            raw_records=rows,
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
        print(f"\nbundle: {run_dir}  verifier_ok={verifier['ok']} bundle_ok={bundle.ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
