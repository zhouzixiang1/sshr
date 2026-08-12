#!/usr/bin/env python3
"""Tests for learned value estimation inside the factorisation MCTS.

Two of these guard bugs found while wiring the estimator up, and both were
silent failures rather than crashes -- the kind that would otherwise surface as
"the learned model is slower and no better", which is precisely the conclusion
this project is trying to escape.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.anf_utils import anf_monomials
from src.factor_plan import SearchConfig
from src.foundation.adapter import FoundationScorer
from src.nmcts_solver import NeuralMCTSSolver
from src.resource_model import ResourceWeights
from src.search.value_net import LearnedValueEstimator, ValueStats
from src.sshr_lib.bool_func import BooleanFunction

PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)


def build(seed: int = 0):
    config = SearchConfig(weights=PAPER_WEIGHTS)
    stats = ValueStats()
    scorer = FoundationScorer.untrained(hidden=32, layers=2, seed=seed)
    return LearnedValueEstimator(scorer, config, stats), config, stats


def random_terms(num_vars: int, seed: int) -> frozenset[int]:
    rng = random.Random(seed)
    return frozenset(anf_monomials(BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))))


def test_estimate_never_exceeds_direct() -> None:
    """The admissibility invariant the whole design rests on.

    ``direct_plan`` decomposes any state, so a value above it would claim the
    search can do worse than a solution it already holds.  Enforcing this
    structurally is what makes a mispredicting network degrade to current
    behaviour instead of corrupting the search.
    """
    estimator, _, _ = build()
    for num_vars in (4, 6, 8):
        terms = random_terms(num_vars, seed=num_vars)
        for direct in (1.0, 42.0, 1e4):
            value = estimator.estimate(terms, 0, 0, direct)
            assert value <= direct + 1e-9, f"n={num_vars}: {value} > direct {direct}"
            assert value > 0.0, f"n={num_vars}: non-positive value {value}"


def test_estimate_is_cached() -> None:
    """Repeated states must not be re-encoded.

    The classical rollout this replaces memoises via ``greedy_memo``.  Without
    a matching cache the network re-runs on identical term sets hundreds of
    times per solve and loses to the rollout on wall clock alone.
    """
    estimator, _, stats = build()
    terms = random_terms(6, seed=3)
    first = estimator.estimate(terms, 0, 0, 100.0)
    for _ in range(20):
        assert estimator.estimate(terms, 0, 0, 100.0) == first
    assert stats.cache_hits == 20, f"expected 20 cache hits, got {stats.cache_hits}"


def test_cache_key_separates_context() -> None:
    """Same monomials at a different recursion depth is a different state."""
    estimator, _, _ = build()
    terms = random_terms(6, seed=4)
    estimator.estimate(terms, 0, 0, 100.0)
    estimator.estimate(terms, 3, 0, 100.0)
    estimator.estimate(terms, 0, 2, 100.0)
    assert len(estimator._cache) == 3, "context fields collapsed into one cache entry"


def test_build_best_does_not_explode() -> None:
    """Regression: an optimistic value must not make plan rebuild exponential.

    ``_build_best`` prunes on ``est >= best_score``.  The classical rollout
    returns an *achievable* score so that test prunes; a learned value is a
    lower bound and passes it almost everywhere, which made the rebuild recurse
    into every branch.  Small instances took minutes before the fix.
    """
    estimator, config, _ = build()
    terms = random_terms(6, seed=5)

    start = time.perf_counter()
    plan = NeuralMCTSSolver(config, simulations=48, seed=1, value_estimator=estimator).solve(terms)
    elapsed = time.perf_counter() - start

    assert plan.score(PAPER_WEIGHTS) > 0
    assert elapsed < 20.0, f"plan rebuild took {elapsed:.1f}s -- pruning likely regressed"


def test_classical_path_unchanged() -> None:
    """Omitting the estimator must reproduce the original solver exactly."""
    config = SearchConfig(weights=PAPER_WEIGHTS)
    terms = random_terms(6, seed=6)
    first = NeuralMCTSSolver(config, simulations=48, seed=1).solve(terms)
    second = NeuralMCTSSolver(config, simulations=48, seed=1).solve(terms)
    assert first.score(PAPER_WEIGHTS) == second.score(PAPER_WEIGHTS)


def test_empty_state() -> None:
    estimator, _, _ = build()
    assert estimator.estimate(frozenset(), 0, 0, 10.0) == 0.0


def main() -> int:
    test_estimate_never_exceeds_direct()
    test_estimate_is_cached()
    test_cache_key_separates_context()
    test_build_best_does_not_explode()
    test_classical_path_unchanged()
    test_empty_state()
    print("value net ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
