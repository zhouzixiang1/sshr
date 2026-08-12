#!/usr/bin/env python3
"""Integration tests for wiring the foundation model into the search.

Symmetry of the trunk itself is covered by ``test_equivariance.py``.  What
matters here is that the model actually reaches the search and actually
influences it -- the project's history includes a learned prior that turned out
to be statistically indistinguishable from no prior at all, so "the plumbing
runs without raising" is not a sufficient bar.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.anf_utils import anf_monomials, majority_function
from src.factor_plan import SearchConfig, candidate_actions
from src.foundation.adapter import FoundationScorer, TermThresholdPolicyScorer
from src.resource_model import ResourceWeights, direct_cost_for_terms
from src.sshr_lib.bool_func import BooleanFunction

# The profile every scripts/run_*.py passes explicitly.  The ResourceWeights
# dataclass default differs; using it here would score a different objective
# than every published run.
PAPER_WEIGHTS = ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0)

# ValueHead saturates at -MIN_LOG_RATIO; anything at or past it means the head
# has bottomed out rather than predicted something.
VALUE_FLOOR = -(3.0 + 1e-6)


def build(seed: int = 0) -> tuple[FoundationScorer, SearchConfig]:
    return FoundationScorer.untrained(hidden=64, layers=3, seed=seed), SearchConfig(weights=PAPER_WEIGHTS)


def score_actions_for(scorer, config, terms):
    actions = candidate_actions(terms, 0, 0, config, neural_scorer=None)
    direct = direct_cost_for_terms(
        terms, 0, 0, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    return actions, scorer.score_actions(terms, 0, 0, actions, direct, config)


def test_scores_every_action() -> None:
    scorer, config = build()
    terms = frozenset(anf_monomials(majority_function(5)))
    actions, scores = score_actions_for(scorer, config, terms)
    assert actions, "majority_n5 should expose candidate factorisations"
    assert len(scores) == len(actions)
    assert all(isinstance(s, float) for s in scores)


def test_symmetric_function_collapses_scores() -> None:
    """Equivariance must map symmetric actions to (near-)identical scores.

    Majority is a fully symmetric Boolean function, so factorisations that
    differ only by relabelling variables are the *same* decision.  A model that
    scored them differently would be reading variable indices it should not see.
    """
    scorer, config = build()
    terms = frozenset(anf_monomials(majority_function(5)))
    _, scores = score_actions_for(scorer, config, terms)
    spread = max(scores) - min(scores)
    assert spread < 0.05, f"symmetric function produced a score spread of {spread:.4f}"


def test_asymmetric_function_separates_scores() -> None:
    """The head must actually depend on which action it is scoring.

    A head that ignored its action inputs would emit one constant per state.
    That failure mode is invisible in aggregate metrics and is exactly how a
    prior ends up ablatable, so it gets its own test.
    """
    scorer, config = build()
    rng = random.Random(7)
    for num_vars in (5, 6):
        terms = frozenset(anf_monomials(BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))))
        actions, scores = score_actions_for(scorer, config, terms)
        if len(actions) < 2:
            continue
        distinct = len({round(s, 6) for s in scores})
        assert distinct > 1, f"n={num_vars}: head emitted one constant across {len(actions)} actions"


def test_scorer_changes_action_order() -> None:
    """The prior has to reach the ranking the search consumes."""
    scorer, config = build()
    rng = random.Random(13)
    terms = frozenset(anf_monomials(BooleanFunction(6, rng.getrandbits(1 << 6))))

    plain = [a.factor for a in candidate_actions(terms, 0, 0, config, neural_scorer=None)]
    scored = [a.factor for a in candidate_actions(terms, 0, 0, config, neural_scorer=scorer)]
    assert plain and scored
    assert plain != scored, "scorer left the candidate ordering untouched"


def test_value_is_non_positive() -> None:
    """``direct_plan`` is always feasible, so the predicted ratio cannot exceed it."""
    scorer, config = build()
    rng = random.Random(29)
    for num_vars in (4, 6, 9):
        terms = frozenset(anf_monomials(BooleanFunction(num_vars, rng.getrandbits(1 << num_vars))))
        value = scorer.predict_log_ratio(terms, 0, 0, config)
        assert value <= 0.0, f"n={num_vars}: value head returned {value} > 0"
        assert value > VALUE_FLOOR, f"n={num_vars}: value head underflowed to {value}"


def test_legacy_protocol_refused_loudly() -> None:
    """Flat features cannot carry a term set; silently scoring them is worse."""
    scorer, _ = build()
    try:
        scorer.score_many([[0.0] * 24])
    except NotImplementedError:
        return
    raise AssertionError("score_many should refuse the flat-feature protocol")


def test_empty_state_is_safe() -> None:
    """Recursion bottoms out on empty term sets; encoding must not divide by zero."""
    scorer, config = build()
    assert scorer.score_actions(frozenset(), 0, 0, [], 1.0, config) == []
    assert scorer.predict_log_ratio(frozenset(), 0, 0, config) == 0.0


def test_term_threshold_policy_skips_small_states_and_delegates_large_states() -> None:
    scorer, config = build()
    gated = TermThresholdPolicyScorer(scorer, min_terms=10)

    small_terms = frozenset({1, 2, 3})
    small_actions = candidate_actions(small_terms, 0, 0, config, neural_scorer=None)
    small_scores = gated.score_actions(small_terms, 0, 0, small_actions, 1.0, config)
    assert small_scores == [0.0] * len(small_actions)
    assert gated.gated_states == 1
    assert scorer.cache_misses == 0

    large_terms = frozenset(anf_monomials(majority_function(5)))
    large_actions = candidate_actions(large_terms, 0, 0, config, neural_scorer=None)
    direct = direct_cost_for_terms(
        large_terms, 0, 0, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    scores = gated.score_actions(large_terms, 0, 0, large_actions, direct, config)
    assert len(scores) == len(large_actions)
    assert gated.learned_states == 1
    assert scorer.cache_misses == 1


def main() -> int:
    test_scores_every_action()
    test_symmetric_function_collapses_scores()
    test_asymmetric_function_separates_scores()
    test_scorer_changes_action_order()
    test_value_is_non_positive()
    test_legacy_protocol_refused_loudly()
    test_empty_state_is_safe()
    print("foundation adapter ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
