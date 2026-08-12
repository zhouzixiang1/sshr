#!/usr/bin/env python3
"""Learned value estimation for the factorisation MCTS.

The solver previously evaluated an unexplored subtree by running a full
classical greedy decomposition (``factor_plan.greedy_plan``).  That is both the
dominant runtime cost and the reason a learned action prior showed almost no
benefit: a strong rollout evaluator masks whatever the prior contributes.

This module swaps that rollout for a learned estimate, under one invariant:

    estimate <= direct_plan score, always

``direct_plan`` is a feasible decomposition of any state, so no correct search
should ever report a worse value.  Enforcing it structurally means a
mispredicting network degrades the search back toward its current behaviour
instead of corrupting it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ValueStats:
    """Counters for reporting how much of the search the network actually drove."""

    calls: int = 0
    clamped: int = 0
    cache_hits: int = 0
    batches: int = 0
    batched_states: int = 0

    @property
    def mean_batch(self) -> float:
        """States per batched forward -- the factor the batching actually won."""
        return self.batched_states / self.batches if self.batches else 0.0

    def as_dict(self) -> dict[str, int]:
        return {
            "value_calls": self.calls,
            "value_clamped": self.clamped,
            "value_cache_hits": self.cache_hits,
            "value_batches": self.batches,
            "value_batched_states": self.batched_states,
        }


class LearnedValueEstimator:
    """Predict a state's achievable score from its term set.

    The network regresses ``log(achievable / direct)`` rather than the score
    itself.  Scores grow by orders of magnitude with the variable count, so
    regressing them directly would let large instances dominate training.  The
    relative target improves numerical comparability across scales, but does
    not by itself establish cross-scale generalisation.
    """

    #: Ratios below this would mean a >20x gain over direct, which is far
    #: outside anything measured.  Treated as a prediction failure and clamped.
    MIN_LOG_RATIO = -3.0

    def __init__(self, scorer, config, stats: ValueStats | None = None) -> None:
        self.scorer = scorer
        self.config = config
        self.stats = stats if stats is not None else ValueStats()
        # The search revisits states constantly, and the classical path it
        # replaces memoises its rollouts too (``NeuralMCTSSolver.greedy_memo``).
        # Without this the network re-encodes identical term sets hundreds of
        # times per solve and loses to the rollout it is meant to beat.
        self._cache: dict[tuple[frozenset[int], int, int], float] = {}

    def _store(self, cache_key, log_ratio: float) -> float:
        """Clamp a raw prediction into the admissible range and cache it."""
        if log_ratio < self.MIN_LOG_RATIO:
            self.stats.clamped += 1
            log_ratio = self.MIN_LOG_RATIO
        elif log_ratio > 0.0:
            self.stats.clamped += 1
            log_ratio = 0.0
        self._cache[cache_key] = log_ratio
        return log_ratio

    def prefetch(
        self,
        requests: Sequence[tuple[frozenset[int], int, int]],
    ) -> None:
        """Value a batch of states up front so later lookups are cache hits.

        The search compares every candidate action before picking one, and each
        unexplored candidate needs two subtree values.  Those are all known at
        the same moment, so they can go through the network as one batch instead
        of two dozen separate forward passes.
        """
        pending: list[tuple[frozenset[int], int, int]] = []
        seen: set[tuple[frozenset[int], int, int]] = set()
        for request in requests:
            terms = request[0]
            if not terms or request in self._cache or request in seen:
                continue
            seen.add(request)
            pending.append(request)

        if not pending:
            return

        self.stats.batches += 1
        self.stats.batched_states += len(pending)
        ratios = self.scorer.predict_log_ratio_batch(pending, self.config)
        for request, ratio in zip(pending, ratios):
            self._store(request, float(ratio))

    def estimate(
        self,
        terms: frozenset[int],
        prefix_len: int,
        live_factor_ancilla: int,
        direct_score: float,
    ) -> float:
        """Predicted score for ``terms``, guaranteed ``<= direct_score``."""
        if not terms:
            return 0.0

        self.stats.calls += 1
        cache_key = (terms, prefix_len, live_factor_ancilla)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self.stats.cache_hits += 1
            return direct_score * math.exp(cached)

        # The head is built to emit non-positive values; _store still guards the
        # range so a retrained head cannot silently break admissibility.
        log_ratio = self._store(
            cache_key,
            self.scorer.predict_log_ratio(terms, prefix_len, live_factor_ancilla, self.config),
        )
        return direct_score * math.exp(log_ratio)


class HybridValueEstimator:
    """Route each state to whichever evaluator is cheaper for its size.

    Measured on random ANF instances, the classical greedy rollout is *far*
    cheaper than a network forward pass on small term sets -- at a couple of
    dozen monomials it costs tens of microseconds, well under torch's
    per-call dispatch overhead.  Its cost then grows much faster than the
    network's as the term set widens, so the ordering reverses.

    Below ``term_threshold`` this defers to the solver's own rollout by
    returning ``None``; above it, the learned estimate takes over.  The
    threshold is hardware-dependent and should be measured, not assumed.

    Note that as of 2026-07-27 neither branch is fast enough to beat the
    existing baseline end to end -- see
    ``docs/project/TECHNICAL_DESIGN.md`` section 3.4c.
    Routing by size mitigates the per-call overhead but does not remove it;
    batched leaf evaluation is the actual fix.
    """

    def __init__(self, learned: LearnedValueEstimator, term_threshold: int) -> None:
        self.learned = learned
        self.term_threshold = int(term_threshold)

    @property
    def stats(self) -> ValueStats:
        return self.learned.stats

    def prefetch(
        self,
        requests: Sequence[tuple[frozenset[int], int, int]],
    ) -> None:
        """Batch only the requests this estimator will actually answer.

        Without this method the solver's ``getattr(..., "prefetch", None)``
        probe finds nothing and silently falls back to one forward pass per
        state -- the hybrid would lose the batching the pure learned estimator
        gets.  Sub-threshold states are dropped rather than forwarded: they are
        going to the classical rollout, so valuing them here would be wasted
        work whose result is never read.
        """
        above = [r for r in requests if len(r[0]) >= self.term_threshold]
        if above:
            self.learned.prefetch(above)

    def estimate(
        self,
        terms: frozenset[int],
        prefix_len: int,
        live_factor_ancilla: int,
        direct_score: float,
    ) -> float | None:
        """Learned estimate, or ``None`` to fall back to the classical rollout."""
        if len(terms) < self.term_threshold:
            return None
        return self.learned.estimate(terms, prefix_len, live_factor_ancilla, direct_score)
