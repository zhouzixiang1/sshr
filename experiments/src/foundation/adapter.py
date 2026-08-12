#!/usr/bin/env python3
"""Bridge the equivariant policy/value model into the existing search.

``src.factor_plan._apply_neural_prior`` dispatches on capability: a scorer that
exposes ``score_actions`` receives the raw term set, while anything else falls
back to the legacy ``score_many(features)`` path.  :class:`FoundationScorer`
implements the former, so switching between the old 24-feature MLP and the
term-set encoder is a matter of which object gets passed in -- no call site
changes, and every existing checkpoint keeps its exact prior behaviour.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import torch

from src.foundation.encoding import (
    STATE_CHANNELS,
    StateContext,
    collate_states,
    encode_state,
    sorted_terms,
)
from src.foundation.equivariant import EquivariantTrunk
from src.foundation.heads import ActionScoringHead, BooleanOracleModel


def _factor_variables(factor: int) -> list[int]:
    return [v for v in range(int(factor).bit_length()) if factor & (1 << v)]


def action_scalars(action, num_terms: int, direct_denom: float) -> list[float]:
    """Per-action scalars for :class:`ActionScoringHead`.

    Two ratios and two absolute sizes.  The ratios say how large the action is
    *relative to this state*; the log-sizes say how large it is at all, which is
    what the ratios drop and what the head needs to rank consistently across
    problem sizes.  Shared with training so the two paths cannot drift -- a
    mismatch here is silent, and would show up only as a checkpoint that scores
    worse than a random ranking.
    """
    return [
        float(action.immediate_gain) / direct_denom,
        len(action.group) / max(num_terms, 1),
        math.log1p(len(action.group)) / ActionScoringHead.LOG_SIZE_SCALE,
        math.log1p(num_terms) / ActionScoringHead.LOG_SIZE_SCALE,
    ]


def required_num_vars(terms: Sequence[int], actions: Sequence) -> int:
    """Variable count wide enough for the state *and* every candidate factor.

    A factor can only mention variables already present in the term set, but
    deriving the width from both sides keeps the encoder honest if that ever
    stops holding (linear/affine actions synthesise factors).
    """
    widest = max((int(t).bit_length() for t in terms), default=0)
    for action in actions:
        widest = max(widest, int(action.factor).bit_length())
    return max(widest, 1)


class FoundationScorer:
    """Score candidate actions with the shared equivariant trunk.

    Implements the structural ``score_actions`` protocol.  Also implements
    ``predict_value`` so the same checkpoint can drive the MCTS value estimate
    (see :mod:`src.search.value_net`).
    """

    #: Solves revisit states heavily; profiling a single n=7 solve showed
    #: ``score_actions`` entered 3322 times, re-encoding identical term sets.
    #: Bounded so long sweeps cannot grow the cache without limit.
    CACHE_LIMIT = 20000

    def __init__(
        self,
        model: BooleanOracleModel,
        device: torch.device | None = None,
    ) -> None:
        # Inference here is many tiny batches (<= candidate_top_k actions per
        # node), a regime where CPU beats MPS on this hardware; training may
        # still use the accelerator.
        self.device = torch.device("cpu") if device is None else device
        self.model = model.to(self.device)
        self.model.eval()
        self._score_cache: dict[tuple, list[float]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def clear_cache(self) -> None:
        self._score_cache.clear()
        self.cache_hits = self.cache_misses = 0

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    @classmethod
    def from_checkpoint(
        cls,
        path: str | Path,
        device: torch.device | None = None,
    ) -> "FoundationScorer":
        payload = torch.load(path, map_location="cpu")
        stored_channels = int(payload["in_channels"])
        if stored_channels != STATE_CHANNELS:
            raise ValueError(
                f"{path} was trained on {stored_channels} input channels but the "
                f"encoder now emits {STATE_CHANNELS}. Checkpoints are tied to the "
                "channel layout in src.foundation.encoding; retrain rather than "
                "loading this one."
            )
        trunk = EquivariantTrunk(
            in_channels=stored_channels,
            hidden=int(payload["hidden"]),
            layers=int(payload["layers"]),
        )
        model = BooleanOracleModel(trunk, mlp_hidden=int(payload.get("mlp_hidden", 128)))
        expected = model.action_head.mlp[0].in_features
        stored = payload["state_dict"]["action_head.mlp.0.weight"].shape[1]
        if stored != expected:
            raise ValueError(
                f"{path} has a {stored}-input action head but this build expects "
                f"{expected} (ActionScoringHead.NUM_SCALARS is now "
                f"{ActionScoringHead.NUM_SCALARS}); retrain rather than loading it."
            )
        model.load_state_dict(payload["state_dict"])
        return cls(model, device=device)

    @classmethod
    def untrained(
        cls,
        hidden: int = 128,
        layers: int = 6,
        seed: int | None = None,
        device: torch.device | None = None,
    ) -> "FoundationScorer":
        """A randomly initialised scorer, for smoke tests and shape checks."""
        if seed is not None:
            torch.manual_seed(seed)
        return cls(BooleanOracleModel(EquivariantTrunk(hidden=hidden, layers=layers)), device=device)

    def save(self, path: str | Path) -> None:
        trunk = self.model.trunk
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.model.state_dict(),
                "in_channels": trunk.in_channels,
                "hidden": trunk.hidden,
                "layers": len(trunk.blocks),
                "mlp_hidden": self.model.action_head.mlp[0].out_features,
            },
            path,
        )

    # ------------------------------------------------------------------
    # structural scoring protocol
    # ------------------------------------------------------------------
    @torch.no_grad()
    def score_actions(
        self,
        terms: frozenset[int],
        prefix_len: int,
        live_factor_ancilla: int,
        actions: Sequence,
        direct_total: float,
        config,
    ) -> list[float]:
        if not actions:
            return []

        ordered = sorted_terms(terms)
        if not ordered:
            return [0.0] * len(actions)

        # ``candidate_actions`` is a pure function of the state and config, so
        # identical states yield identical action lists and identical scores.
        # The factor tuple keeps the key honest if a caller ever passes a
        # filtered or reordered list.
        cache_key = (terms, prefix_len, live_factor_ancilla, tuple(a.factor for a in actions))
        cached = self._score_cache.get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            return cached
        self.cache_misses += 1

        row_of = {term: i for i, term in enumerate(ordered)}
        num_vars = required_num_vars(ordered, actions)

        context = StateContext.from_config(config, prefix_len, live_factor_ancilla)
        state = encode_state(ordered, num_vars, context, device=self.device)
        term_features, var_features, global_features = self.model.encode(state)

        group_rows = [[row_of[t] for t in a.group if t in row_of] for a in actions]
        factor_vars = [_factor_variables(a.factor) for a in actions]
        denom = max(abs(float(direct_total)), 1.0)
        scalars = torch.tensor(
            [action_scalars(a, len(ordered), denom) for a in actions],
            dtype=torch.float32,
            device=self.device,
        )

        scores = self.model.action_head(
            term_features, var_features, global_features, group_rows, factor_vars, scalars
        )
        result = scores.tolist()
        if len(self._score_cache) < self.CACHE_LIMIT:
            self._score_cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # value protocol
    # ------------------------------------------------------------------
    def _encode_request(self, terms: frozenset[int], prefix_len: int, live: int, config):
        ordered = sorted_terms(terms)
        num_vars = max(max(int(t).bit_length() for t in ordered), 1)
        context = StateContext.from_config(config, prefix_len, live)
        return encode_state(ordered, num_vars, context, device=self.device)

    @torch.no_grad()
    def predict_log_ratio(
        self,
        terms: frozenset[int],
        prefix_len: int,
        live_factor_ancilla: int,
        config,
    ) -> float:
        """Predicted ``log(achievable_score / direct_score)``; always ``<= 0``."""
        if not terms:
            return 0.0
        state = self._encode_request(terms, prefix_len, live_factor_ancilla, config)
        _, _, global_features = self.model.encode(state)
        return float(self.model.value_head(global_features.unsqueeze(0))[0])

    @torch.no_grad()
    def predict_log_ratio_batch(
        self,
        requests: Sequence[tuple[frozenset[int], int, int]],
        config,
    ) -> list[float]:
        """Value several states in one forward pass.

        The search needs many of these simultaneously -- selecting an action
        compares every candidate, and each unexplored candidate needs both its
        factored and residual branch valued -- so evaluating them one at a time
        pays torch's per-call dispatch cost dozens of times for what is a single
        small batch.  States of different shapes are padded and masked, and
        :func:`collate_states` guarantees padding is inert, so batched results
        match one-at-a-time results exactly.
        """
        if not requests:
            return []

        states = [self._encode_request(t, p, l, config) for t, p, l in requests]
        batch, term_mask, var_mask = collate_states(states)
        _, _, global_features = self.model.encode(batch, term_mask, var_mask)
        return self.model.value_head(global_features).tolist()

    # ------------------------------------------------------------------
    # legacy compatibility
    # ------------------------------------------------------------------
    def score_many(self, features) -> list[float]:
        """Legacy protocol guard.

        Reaching this means a caller bypassed ``score_actions`` and handed over
        pre-flattened features, which this model cannot consume -- the encoder
        needs the term set the features were derived from.  Failing loudly beats
        silently scoring zeros and looking like an ablatable model.
        """
        raise NotImplementedError(
            "FoundationScorer requires the structural score_actions protocol; "
            "the flat action_features vector does not carry the term set."
        )


class TermThresholdPolicyScorer:
    """Use the learned action policy only for sufficiently large term sets.

    Small subtrees are where torch dispatch dominates the classical heuristic.
    Returning zero neural adjustments preserves the deterministic heuristic
    ordering without changing the candidate generator or search semantics.
    The threshold must be chosen on a validation split and then frozen.
    """

    def __init__(self, scorer: FoundationScorer, min_terms: int) -> None:
        if min_terms < 0:
            raise ValueError("min_terms must be non-negative")
        self.scorer = scorer
        self.min_terms = int(min_terms)
        self.gated_states = 0
        self.learned_states = 0

    def score_actions(
        self,
        terms: frozenset[int],
        prefix_len: int,
        live_factor_ancilla: int,
        actions: Sequence,
        direct_total: float,
        config,
    ) -> list[float]:
        if len(terms) < self.min_terms:
            self.gated_states += 1
            return [0.0] * len(actions)
        self.learned_states += 1
        return self.scorer.score_actions(
            terms,
            prefix_len,
            live_factor_ancilla,
            actions,
            direct_total,
            config,
        )

    def clear_cache(self) -> None:
        self.scorer.clear_cache()
        self.gated_states = 0
        self.learned_states = 0
