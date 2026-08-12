#!/usr/bin/env python3
"""Measure whether the learned action prior is actually load-bearing.

The honest test of a learned prior is not whether the system runs without it --
it always does -- but whether removing it costs search quality.  This script
measures that against two references on the same instances:

    shuffled   the prior's ranking permuted, everything else identical
               -> the floor: what the search achieves with no ranking signal
    model      the checkpoint's ranking                (what we ship)
    oracle     the same learned top-K shortlist sorted by a scorer-free
               classical rollout -> a conditional ranking ceiling

Reporting ``model`` without ``oracle`` is what makes prior ablations
misleading.  A prior that ties the shuffle could mean the model is weak, or it
could mean ranking simply does not matter for this search; only the oracle
column separates those, and they call for opposite responses.

The oracle is conditional on the model-selected top-K candidate pool.  It
measures action ordering within that frozen shortlist; it is not a global
perfect-policy ceiling over every legal factor action.

The oracle is a diagnostic, not a configuration: it prices every action with the
rollout the value net exists to avoid, so it is far more expensive than the
search it bounds.

Usage:
    python scripts/run_prior_ablation.py --sizes 6 7 8 --per-size 3
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch

from src.anf_utils import anf_monomials
from src.contracts.codec import canonical_hex
from src.contracts.experiment import ExperimentManifest
from src.factor_plan import (
    SearchConfig,
    emit_plan_to_circuit,
    factor_cost,
    greedy_plan,
    verify_circuit_anf,
    verify_oracle,
    verify_plan_anf,
)
from src.foundation.adapter import FoundationScorer
from src.nmcts_solver import NeuralMCTSSolver
from src.resource_model import ResourceWeights
from src.search.value_net import LearnedValueEstimator
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


class ShuffledPrior(NeuralMCTSSolver):
    """Destroy the ranking, keep every other component identical.

    The scorer still runs and still costs the same; only the *order* it induces
    is discarded.  A variant that simply dropped the scorer would also change
    the candidate pool -- ``candidate_actions`` truncates to ``candidate_top_k``
    *after* applying the prior -- and would confound the comparison.
    """

    def __init__(self, *args, shuffle_seed: int = 0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # A private stream: self.rng drives PUCT tie-breaking, and perturbing
        # that would be a second, uncontrolled change.
        self._shuffle_rng = random.Random(shuffle_seed)

    def _expand(self, node) -> None:
        was_expanded = node.expanded
        super()._expand(node)
        if not was_expanded and node.actions:
            self._shuffle_rng.shuffle(node.actions)


class OraclePrior(NeuralMCTSSolver):
    """Conditional upper bound for ordering the frozen model-selected shortlist.

    Sorts each node's already-truncated actions by a scorer-free classical
    rollout estimate.  Candidate-pool selection is deliberately unchanged so
    the comparison isolates ranking, but this also means the result is not a
    global oracle over every legal action.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Do not reuse ``self.greedy_memo``: normal solver rollouts may have
        # populated it with neural-scorer-guided plans, while the diagnostic
        # ceiling is defined by a scorer-free classical greedy rollout.
        self._oracle_greedy_memo = {}

    def _classical_rollout_action_cost(self, key, action) -> float:
        group = greedy_plan(
            action.residuals,
            key.prefix_len + 1,
            key.live_factor_ancilla + 1,
            self.config,
            neural_scorer=None,
            memo=self._oracle_greedy_memo,
        )
        rest = greedy_plan(
            action.rest,
            key.prefix_len,
            key.live_factor_ancilla,
            self.config,
            neural_scorer=None,
            memo=self._oracle_greedy_memo,
        )
        return factor_cost(
            action,
            group,
            rest,
            key.live_factor_ancilla,
            self.config,
        ).score(self.config.weights)

    def _expand(self, node) -> None:
        was_expanded = node.expanded
        super()._expand(node)
        if not was_expanded and node.actions:
            node.actions[:] = sorted(
                node.actions,
                key=lambda action: self._classical_rollout_action_cost(node.key, action),
            )


VARIANTS = {
    "shuffled": (ShuffledPrior, {"shuffle_seed": 1}),
    "model": (NeuralMCTSSolver, {}),
    "oracle": (OraclePrior, {}),
}


def instances(sizes, per_size):
    out = []
    for num_vars in sizes:
        for k in range(per_size):
            instance_seed = 1000 * num_vars + k
            rng = random.Random(instance_seed)
            bf = BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))
            terms = frozenset(anf_monomials(bf))
            if terms:
                out.append(
                    {
                        "case_id": f"random-n{num_vars}-k{k}",
                        "instance_seed": instance_seed,
                        "num_vars": num_vars,
                        "bf": bf,
                        "terms": terms,
                    }
                )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[6, 7, 8])
    parser.add_argument("--per-size", type=int, default=3)
    parser.add_argument("--simulations", type=int, default=48)
    parser.add_argument("--checkpoint", type=str, default="models/boolean_oracle_fm_v3.pt")
    parser.add_argument("--solver-seed", type=int, default=1)
    parser.add_argument("--shuffle-seed", type=int, default=1)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    args = parser.parse_args()

    torch.set_num_threads(1)
    config = SearchConfig(weights=PAPER_WEIGHTS)
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    checkpoint_meta = model_record(checkpoint, _PROJECT_ROOT)
    print(f"checkpoint: {args.checkpoint}   simulations: {args.simulations}\n")
    print(f"{'n':>3} {'terms':>6} " + " ".join(f"{name:>10}" for name in VARIANTS))

    ratios = {name: [] for name in VARIANTS}
    cases = instances(args.sizes, args.per_size)
    raw_records = []
    scores_by_case: dict[str, dict[str, float]] = {}
    run_started = utc_now()
    for case in cases:
        num_vars = case["num_vars"]
        terms = case["terms"]
        bf = case["bf"]
        scores = {}
        for name, (solver_cls, kwargs) in VARIANTS.items():
            scorer = FoundationScorer.from_checkpoint(checkpoint)
            variant_kwargs = dict(kwargs)
            if name == "shuffled":
                variant_kwargs["shuffle_seed"] = args.shuffle_seed
            solver = solver_cls(
                config,
                simulations=args.simulations,
                seed=args.solver_seed,
                neural_scorer=scorer,
                value_estimator=LearnedValueEstimator(scorer, config),
                **variant_kwargs,
            )
            t0 = time.perf_counter()
            plan = solver.solve(terms)
            elapsed_s = time.perf_counter() - t0
            scores[name] = plan.score(PAPER_WEIGHTS)
            circ = emit_plan_to_circuit(
                plan,
                num_vars,
                min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            )
            plan_check = verify_plan_anf(plan)
            circuit_check = verify_circuit_anf(circ, num_vars, terms)
            oracle_ok = verify_oracle(circ, bf)
            raw_records.append(
                {
                    "schema_version": "xa.prior-diagnostic-row.v1",
                    "case_id": case["case_id"],
                    "n_declared": num_vars,
                    "truth_table_hex": canonical_hex(
                        int(bf.truth_table), min_nibbles=max(1, ((1 << num_vars) + 3) // 4)
                    ),
                    "anf_terms_hex": [canonical_hex(term) for term in sorted(terms)],
                    "instance_seed": case["instance_seed"],
                    "solver_seed": args.solver_seed,
                    "shuffle_seed": args.shuffle_seed if name == "shuffled" else None,
                    "variant": name,
                    "checkpoint_sha256": checkpoint_meta["sha256"],
                    "simulations": args.simulations,
                    "score": scores[name],
                    "elapsed_s": elapsed_s,
                    "plan_anf_ok": plan_check.ok,
                    "circuit_anf_ok": circuit_check.ok,
                    "oracle_ok": oracle_ok,
                }
            )
        scores_by_case[case["case_id"]] = scores
        # Normalise per instance so cases of wildly different absolute cost
        # contribute equally to the mean.
        for name in VARIANTS:
            ratios[name].append(scores[name] / scores["shuffled"])
        print(
            f"{num_vars:>3} {len(terms):>6} "
            + " ".join(f"{scores[name]:10.1f}" for name in VARIANTS),
            flush=True,
        )

    print(f"\n{'variant':<12} {'vs shuffled':>12}   (lower is better)")
    for name in VARIANTS:
        mean = statistics.mean(ratios[name])
        print(f"{name:<12} {100.0 * (mean - 1.0):+11.2f}%")

    captured = (1.0 - statistics.mean(ratios["model"])) / max(
        1.0 - statistics.mean(ratios["oracle"]), 1e-9
    )
    print(
        f"\nheadroom of conditional rollout ordering: {100.0 * (1.0 - statistics.mean(ratios['oracle'])):.2f}%"
        f"\nfraction the checkpoint captures: {100.0 * captured:.1f}%"
    )

    if args.out_dir is not None:
        finished_at = utc_now()
        run_id = args.run_id or (
            f"{run_started[:10].replace('-', '')}-{run_started[11:19].replace(':', '')}"
            f"-e1-prior-pilot-s{args.solver_seed}"
        )
        variants_summary = {}
        for variant in VARIANTS:
            variant_rows = [row for row in raw_records if row["variant"] == variant]
            variants_summary[variant] = {
                "count": len(variant_rows),
                "score_mean": statistics.mean(row["score"] for row in variant_rows),
                "score_median": statistics.median(row["score"] for row in variant_rows),
                "elapsed_s_mean": statistics.mean(row["elapsed_s"] for row in variant_rows),
                "ratio_vs_shuffled_mean": statistics.mean(ratios[variant]),
            }

        def wlt(variant: str) -> dict[str, int]:
            pairs = [
                (scores[variant], scores["shuffled"])
                for scores in scores_by_case.values()
            ]
            return {
                "wins": sum(left < right for left, right in pairs),
                "losses": sum(left > right for left, right in pairs),
                "ties": sum(left == right for left, right in pairs),
            }

        oracle_headroom = 1.0 - statistics.mean(ratios["oracle"])
        summary = {
            "schema_version": "xa.prior-diagnostic-summary.v1",
            "run_id": run_id,
            "case_count": len(cases),
            "variants": variants_summary,
            "model_vs_shuffled_wlt": wlt("model"),
            "oracle_vs_shuffled_wlt": wlt("oracle"),
            "oracle_headroom_fraction": oracle_headroom,
            "model_captured_fraction": captured,
            "all_plan_anf_ok": all(row["plan_anf_ok"] for row in raw_records),
            "all_circuit_anf_ok": all(row["circuit_anf_ok"] for row in raw_records),
            "all_oracle_ok": all(row["oracle_ok"] for row in raw_records),
        }
        complete_variants = all(
            set(scores) == set(VARIANTS) for scores in scores_by_case.values()
        )
        verifier = {
            "schema_version": "xa.prior-diagnostic-verifier.v1",
            "checks": {
                "expected_record_count": len(raw_records) == len(cases) * len(VARIANTS),
                "complete_case_variant_matrix": complete_variants,
                "checkpoint_sha_consistent": all(
                    row["checkpoint_sha256"] == checkpoint_meta["sha256"]
                    for row in raw_records
                ),
                "plan_anf_100_percent": summary["all_plan_anf_ok"],
                "circuit_anf_100_percent": summary["all_circuit_anf_ok"],
                "oracle_100_percent": summary["all_oracle_ok"],
                "summary_counts_recomputed": all(
                    variants_summary[name]["count"]
                    == sum(row["variant"] == name for row in raw_records)
                    for name in VARIANTS
                ),
            },
        }
        verifier["ok"] = all(verifier["checks"].values())
        dataset = {
            "generator_id": "xa.random-truth-prior-pilot.v1",
            "sizes": args.sizes,
            "per_size": args.per_size,
            "cases": [
                {
                    "case_id": case["case_id"],
                    "n_declared": case["num_vars"],
                    "truth_table_hex": canonical_hex(
                        int(case["bf"].truth_table),
                        min_nibbles=max(1, ((1 << case["num_vars"]) + 3) // 4),
                    ),
                    "instance_seed": case["instance_seed"],
                }
                for case in cases
            ],
            "solver_seed": args.solver_seed,
            "shuffle_seed": args.shuffle_seed,
        }
        dataset["dataset_sha256"] = dataset_sha256(dataset)
        source = source_record(_PROJECT_ROOT)
        manifest = ExperimentManifest(
            run_id=run_id,
            track="e1-equivariant",
            experiment="prior-diagnostic",
            status="complete" if verifier["ok"] else "failed",
            created_at_utc=run_started,
            source=source,
            environment=environment_record(),
            command={
                "entrypoint": "scripts/run_prior_ablation.py",
                "sizes": args.sizes,
                "per_size": args.per_size,
                "simulations": args.simulations,
                "solver_seed": args.solver_seed,
                "shuffle_seed": args.shuffle_seed,
            },
            dataset=dataset,
            config=asdict(config),
            model=checkpoint_meta,
            variants=tuple(VARIANTS),
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
            claim_boundary=(
                "The scorer-free rollout oracle is a conditional ordering ceiling within "
                "the model-selected top-K shortlist, not a global policy oracle or a "
                "deployable method. This pilot alone does not establish generalization "
                "or end-to-end benefit."
            ),
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
        print(f"\nbundle: {run_dir}  verifier_ok={verifier['ok']} bundle_ok={bundle.ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
