#!/usr/bin/env python3
"""Expert iteration for the Boolean-oracle equivariant policy/value model.

Alternates self-play and supervised fitting, AlphaZero style, adapted to a
*minimisation* problem:

1. run MCTS on training functions with the current network
2. record ``(state, visit distribution, achieved log-ratio)``
3. fit the policy head to the visit counts and the value head to the ratios
4. keep the new weights only if held-out search does not get worse

Value targets are ``log(achieved / direct)`` rather than raw scores.  Scores
span orders of magnitude across ``n``, so regressing them directly would let
large instances dominate the gradient and would tie a checkpoint to one problem
size.  The relative target improves numerical comparability across scales, but
does not by itself establish cross-scale generalisation.

Self-play deliberately runs *without* the value net, on the classical greedy
rollout.  That is the expert: slower, but its visit counts and achieved scores
are the high-quality targets the network is meant to imitate.  Evaluation then
runs the fast configuration (value net + progressive widening), so the accept
gate measures exactly the deployed search.

Usage:
    python scripts/train_expert_iteration.py --iterations 5 --functions 200
"""
from __future__ import annotations

import argparse
import math
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch
from torch import nn

from src.anf_utils import anf_monomials
from src.factor_plan import SearchConfig
from src.foundation.adapter import (
    FoundationScorer,
    action_scalars,
    required_num_vars,
    _factor_variables,
)
from src.foundation.encoding import StateContext, collate_states, encode_state, sorted_terms
from src.foundation.equivariant import EquivariantTrunk
from src.foundation.heads import BooleanOracleModel
from src.nmcts_solver import NeuralMCTSSolver
from src.resource_model import ResourceWeights
from src.search.value_net import LearnedValueEstimator
from src.sshr_lib.bool_func import BooleanFunction

# Every scripts/run_*.py passes this profile explicitly; the ResourceWeights
# dataclass default differs and would train against a different objective.
PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)

#: Value targets are clamped to the same floor the deployed estimator enforces.
MIN_LOG_RATIO = -3.0


@dataclass
class Sample:
    """One visited search node: its state, its value, and its visit policy.

    Both targets come from the same node because both heads read the same trunk
    -- training them jointly is what keeps the shared backbone useful to each.
    ``group_rows`` indexes into ``sorted_terms(terms)``, matching exactly what
    :meth:`FoundationScorer.score_actions` builds at inference time.
    """

    terms: frozenset[int]
    num_vars: int
    prefix_len: int
    live_factor_ancilla: int
    log_ratio: float
    group_rows: list[list[int]] = field(default_factory=list)
    factor_vars: list[list[int]] = field(default_factory=list)
    scalars: list[list[float]] = field(default_factory=list)
    visits: list[float] = field(default_factory=list)

    @property
    def has_policy(self) -> bool:
        """True when at least two actions were visited, so the counts rank."""
        return sum(1 for v in self.visits if v > 0) >= 2


def sample_functions(count: int, min_vars: int, max_vars: int, seed: int) -> list[tuple[int, frozenset[int]]]:
    """Draw random ANF instances, weighting small ``n`` more heavily.

    Small instances are cheap to search, so they supply most of the signal per
    unit of compute; the tail keeps the model honest about larger states.
    """
    rng = random.Random(seed)
    sizes = list(range(min_vars, max_vars + 1))
    weights = [1.0 / n for n in sizes]
    out = []
    for _ in range(count):
        num_vars = rng.choices(sizes, weights=weights, k=1)[0]
        truth_table = rng.getrandbits(1 << num_vars)
        terms = frozenset(anf_monomials(BooleanFunction(num_vars, truth_table)))
        if terms:
            out.append((num_vars, terms))
    return out


def collect_samples(
    solver: NeuralMCTSSolver,
    config: SearchConfig,
) -> list[Sample]:
    """Harvest value and policy targets from a completed search tree.

    Every node the search actually visited carries an achieved score; pairing it
    with that node's ``direct_plan`` gives the scale-free value target.  The same
    node's per-action visit counts give the policy target.
    """
    samples: list[Sample] = []
    for key, node in solver.nodes.items():
        if not key.terms or not node.visits:
            continue
        direct = node.direct.score(config.weights)
        if direct <= 0:
            continue

        best = min(
            (stat.q for stat in node.stats.values() if stat.visits > 0),
            default=direct,
        )
        ratio = max(min(best / direct, 1.0), math.exp(MIN_LOG_RATIO))

        ordered = sorted_terms(key.terms)
        row_of = {term: i for i, term in enumerate(ordered)}
        denom = max(abs(direct), 1.0)
        sample = Sample(
            terms=key.terms,
            num_vars=required_num_vars(ordered, node.actions),
            prefix_len=key.prefix_len,
            live_factor_ancilla=key.live_factor_ancilla,
            log_ratio=math.log(ratio),
        )
        for index, action in enumerate(node.actions):
            stat = node.stats.get(index)
            sample.group_rows.append([row_of[t] for t in action.group if t in row_of])
            sample.factor_vars.append(_factor_variables(action.factor))
            # Shared with inference so the two paths cannot drift: a mismatch
            # here is silent and would surface only as a checkpoint that ranks
            # worse than random.
            sample.scalars.append(action_scalars(action, len(ordered), denom))
            sample.visits.append(float(stat.visits) if stat else 0.0)
        samples.append(sample)
    return samples


def _encode(sample: Sample, config: SearchConfig, device: torch.device) -> torch.Tensor:
    context = StateContext.from_config(config, sample.prefix_len, sample.live_factor_ancilla)
    return encode_state(sorted_terms(sample.terms), sample.num_vars, context, device=device)


def _policy_loss(
    model: BooleanOracleModel,
    sample: Sample,
    term_features: torch.Tensor,
    var_features: torch.Tensor,
    global_features: torch.Tensor,
    device: torch.device,
) -> torch.Tensor:
    """Cross-entropy between the action head and the search's visit counts.

    The search minimises, so a *high* visit count marks a *good* action and the
    head is trained to score it high -- the same orientation
    ``candidate_actions`` sorts by.
    """
    scores = model.action_head(
        term_features,
        var_features,
        global_features,
        sample.group_rows,
        sample.factor_vars,
        torch.tensor(sample.scalars, dtype=torch.float32, device=device),
    )
    counts = torch.tensor(sample.visits, dtype=torch.float32, device=device)
    target = counts / counts.sum()
    return -(target * torch.log_softmax(scores, dim=-1)).sum()


def fit(
    model: BooleanOracleModel,
    samples: list[Sample],
    config: SearchConfig,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    policy_weight: float,
    device: torch.device,
) -> tuple[float, float]:
    """Joint value + policy fit; returns the last epoch's mean losses.

    States are padded and run through the trunk as one batch per step.  The
    trunk dominates the cost and is shape-agnostic, so batching it is free
    accuracy-wise -- :func:`collate_states` keeps padding inert -- and is what
    makes fitting tens of thousands of nodes tractable.
    """
    if not samples:
        return float("nan"), float("nan")

    model.train()
    optimiser = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    mse = nn.MSELoss()
    last_value = last_policy = float("nan")

    for _ in range(epochs):
        random.shuffle(samples)
        value_total, policy_total, steps = 0.0, 0.0, 0
        for start in range(0, len(samples), batch_size):
            chunk = samples[start : start + batch_size]
            batch, term_mask, var_mask = collate_states([_encode(s, config, device) for s in chunk])
            term_features, var_features, global_features = model.encode(batch, term_mask, var_mask)

            value_loss = mse(
                model.value_head(global_features),
                torch.tensor([s.log_ratio for s in chunk], dtype=torch.float32, device=device),
            )

            # Action counts differ per node, so the policy term is accumulated
            # per sample; only the trunk -- the expensive part -- is batched.
            policy_terms = [
                _policy_loss(
                    model,
                    sample,
                    term_features[i, : len(sorted_terms(sample.terms))],
                    var_features[i, : sample.num_vars],
                    global_features[i],
                    device,
                )
                for i, sample in enumerate(chunk)
                if sample.has_policy
            ]
            policy_loss = (
                torch.stack(policy_terms).mean()
                if policy_terms
                else torch.zeros((), device=device)
            )

            loss = value_loss + policy_weight * policy_loss
            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()

            value_total += float(value_loss.detach())
            policy_total += float(policy_loss.detach())
            steps += 1
        last_value = value_total / max(steps, 1)
        last_policy = policy_total / max(steps, 1)

    model.eval()
    return last_value, last_policy


def evaluate(
    scorer: FoundationScorer,
    config: SearchConfig,
    functions: list[tuple[int, frozenset[int]]],
    simulations: int,
    use_value_net: bool,
) -> tuple[float, float]:
    """Mean score and total wall time over a held-out set."""
    total_score, start = 0.0, time.perf_counter()
    for _, terms in functions:
        estimator = LearnedValueEstimator(scorer, config) if use_value_net else None
        plan = NeuralMCTSSolver(
            config,
            simulations=simulations,
            seed=1,
            neural_scorer=scorer,
            value_estimator=estimator,
        ).solve(terms)
        total_score += plan.score(config.weights)
    return total_score / max(len(functions), 1), time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--functions", type=int, default=64, help="self-play functions per iteration")
    parser.add_argument("--holdout", type=int, default=16)
    parser.add_argument("--min-vars", type=int, default=4)
    parser.add_argument("--max-vars", type=int, default=8)
    parser.add_argument("--simulations", type=int, default=48)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--policy-weight", type=float, default=1.0)
    parser.add_argument(
        "--selfplay-prior",
        choices=("model", "heuristic"),
        default="model",
        help=(
            "Prior used to order candidates during self-play.  'heuristic' runs "
            "no forward pass at all, which matters because value targets come "
            "from the classical rollout and so do not depend on the model: with "
            "a large trunk, model-prior self-play costs an order of magnitude "
            "more for targets that are no better -- and at iteration 1, worse, "
            "since the model is still random."
        ),
    )
    parser.add_argument("--max-samples", type=int, default=6000, help="cap on nodes kept per iteration")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=str, default="models/boolean_oracle_fm.pt")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    torch.set_num_threads(1)
    device = torch.device("cpu")
    config = SearchConfig(weights=PAPER_WEIGHTS)

    model = BooleanOracleModel(EquivariantTrunk(hidden=args.hidden, layers=args.layers))
    scorer = FoundationScorer(model, device=device)

    # Held-out functions are drawn from a disjoint seed stream and never enter
    # self-play, matching the train/validation separation the project's other
    # learned components already use.
    holdout = sample_functions(args.holdout, args.min_vars, args.max_vars, seed=args.seed + 9999)

    base_score, base_time = evaluate(scorer, config, holdout, args.simulations, use_value_net=True)
    print(f"[init] holdout mean score {base_score:.4f}  ({base_time:.1f}s, untrained)", flush=True)

    best_score = base_score
    for iteration in range(1, args.iterations + 1):
        functions = sample_functions(
            args.functions, args.min_vars, args.max_vars, seed=args.seed + iteration
        )

        samples: list[Sample] = []
        played = time.perf_counter()
        selfplay_prior = scorer if args.selfplay_prior == "model" else None
        for _, terms in functions:
            solver = NeuralMCTSSolver(
                config, simulations=args.simulations, seed=iteration, neural_scorer=selfplay_prior
            )
            solver.solve(terms)
            samples.extend(collect_samples(solver, config))
        play_seconds = time.perf_counter() - played

        if len(samples) > args.max_samples:
            samples = random.sample(samples, args.max_samples)

        fitted = time.perf_counter()
        value_loss, policy_loss = fit(
            model,
            samples,
            config,
            args.epochs,
            args.batch_size,
            args.lr,
            args.policy_weight,
            device,
        )
        fit_seconds = time.perf_counter() - fitted
        scorer.clear_cache()

        score, seconds = evaluate(scorer, config, holdout, args.simulations, use_value_net=True)
        delta = 100.0 * (score / best_score - 1.0)
        verdict = "accept" if score <= best_score else "reject"
        print(
            f"[iter {iteration}] samples={len(samples)} play={play_seconds:.1f}s fit={fit_seconds:.1f}s "
            f"value={value_loss:.5f} policy={policy_loss:.4f} "
            f"holdout={score:.4f} ({delta:+.2f}%) eval={seconds:.1f}s -> {verdict}",
            flush=True,
        )
        if score <= best_score:
            best_score = score
            scorer.save(args.out)

    print(f"best holdout mean score {best_score:.4f}; checkpoint at {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
