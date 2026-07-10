#!/usr/bin/env python3
"""Recursive PUCT/MCTS solver for ANF factorization plans."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Optional

from src.factor_plan import (
    FactorAction,
    Plan,
    SearchConfig,
    candidate_actions,
    direct_plan,
    factor_cost,
    greedy_plan,
)


@dataclass(frozen=True)
class StateKey:
    terms: frozenset[int]
    prefix_len: int
    live_factor_ancilla: int


@dataclass
class ActionStats:
    visits: int = 0
    q: float = 0.0


@dataclass
class SearchNode:
    key: StateKey
    direct: Plan
    actions: list[FactorAction] = field(default_factory=list)
    visits: int = 0
    stats: Dict[int, ActionStats] = field(default_factory=dict)
    expanded: bool = False


class NeuralMCTSSolver:
    def __init__(
        self,
        config: SearchConfig,
        simulations: int = 96,
        c_puct: float = 1.35,
        seed: int = 0,
        neural_scorer=None,
    ) -> None:
        self.config = config
        self.simulations = simulations
        self.c_puct = c_puct
        self.rng = random.Random(seed)
        self.neural_scorer = neural_scorer
        self.nodes: Dict[StateKey, SearchNode] = {}
        self.greedy_memo: dict[tuple[frozenset[int], int, int], Plan] = {}

    def _node(self, key: StateKey) -> SearchNode:
        node = self.nodes.get(key)
        if node is None:
            direct = direct_plan(key.terms, key.prefix_len, key.live_factor_ancilla, self.config)
            node = SearchNode(key=key, direct=direct)
            self.nodes[key] = node
        return node

    def _expand(self, node: SearchNode) -> None:
        if node.expanded:
            return
        key = node.key
        node.actions = candidate_actions(
            key.terms,
            key.prefix_len,
            key.live_factor_ancilla,
            self.config,
            neural_scorer=self.neural_scorer,
        )
        node.stats = {i: ActionStats() for i in range(len(node.actions))}
        node.expanded = True

    def _greedy_value(self, key: StateKey) -> float:
        plan = greedy_plan(
            key.terms,
            key.prefix_len,
            key.live_factor_ancilla,
            self.config,
            self.neural_scorer,
            self.greedy_memo,
        )
        return plan.score(self.config.weights)

    def _simulate(self, key: StateKey, depth: int = 0) -> float:
        node = self._node(key)
        direct_score = node.direct.score(self.config.weights)
        if not key.terms:
            return 0.0
        self._expand(node)
        if not node.actions or depth > 64:
            return direct_score
        node.visits += 1

        total_prior = sum(max(0.0, a.prior) + 1e-3 for a in node.actions)
        sqrt_n = math.sqrt(max(1, node.visits))

        def select_key(i: int) -> tuple[float, float]:
            action = node.actions[i]
            st = node.stats[i]
            prior = (max(0.0, action.prior) + 1e-3) / total_prior
            if st.visits:
                q = st.q
            else:
                q = self._rollout_action_cost(key, action)
            bonus = self.c_puct * prior * sqrt_n / (1 + st.visits)
            return (q - bonus + self.rng.random() * 1e-9, -action.immediate_gain)

        idx = min(range(len(node.actions)), key=select_key)
        action = node.actions[idx]
        estimate = self._evaluate_action_recursive(key, action, depth)
        st = node.stats[idx]
        st.visits += 1
        st.q += (estimate - st.q) / st.visits
        return min(direct_score, estimate)

    def _rollout_action_cost(self, key: StateKey, action: FactorAction) -> float:
        group_key = StateKey(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1)
        rest_key = StateKey(action.rest, key.prefix_len, key.live_factor_ancilla)
        compute = factor_cost(
            action,
            direct_plan(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1, self.config),
            direct_plan(action.rest, key.prefix_len, key.live_factor_ancilla, self.config),
            key.live_factor_ancilla,
            self.config,
        ).score(self.config.weights)
        # Replace child direct plans by greedy value while keeping compute/uncompute cost.
        child_direct = (
            direct_plan(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1, self.config).score(self.config.weights)
            + direct_plan(action.rest, key.prefix_len, key.live_factor_ancilla, self.config).score(self.config.weights)
        )
        return compute - child_direct + self._greedy_value(group_key) + self._greedy_value(rest_key)

    def _evaluate_action_recursive(self, key: StateKey, action: FactorAction, depth: int) -> float:
        group_key = StateKey(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1)
        rest_key = StateKey(action.rest, key.prefix_len, key.live_factor_ancilla)
        group_score = self._simulate(group_key, depth + 1)
        rest_score = self._simulate(rest_key, depth + 1)
        compute = factor_cost(
            action,
            direct_plan(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1, self.config),
            direct_plan(action.rest, key.prefix_len, key.live_factor_ancilla, self.config),
            key.live_factor_ancilla,
            self.config,
        ).score(self.config.weights)
        child_direct = (
            direct_plan(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1, self.config).score(self.config.weights)
            + direct_plan(action.rest, key.prefix_len, key.live_factor_ancilla, self.config).score(self.config.weights)
        )
        return compute - child_direct + group_score + rest_score

    def solve(self, terms: frozenset[int]) -> Plan:
        root = StateKey(terms, 0, 0)
        for _ in range(self.simulations):
            self._simulate(root)
        return self._build_best(root)

    def _build_best(self, key: StateKey) -> Plan:
        node = self._node(key)
        self._expand(node)
        best = node.direct
        best_score = best.score(self.config.weights)
        for idx, action in enumerate(node.actions):
            st = node.stats.get(idx)
            if st is None or st.visits == 0:
                est = self._rollout_action_cost(key, action)
            else:
                est = st.q
            if est >= best_score:
                continue
            group_key = StateKey(action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1)
            rest_key = StateKey(action.rest, key.prefix_len, key.live_factor_ancilla)
            group = self._build_best(group_key)
            rest = self._build_best(rest_key)
            cost = factor_cost(action, group, rest, key.live_factor_ancilla, self.config)
            plan = Plan("factor", key.terms, cost, factor=action.factor, group=group, rest=rest)
            score = plan.score(self.config.weights)
            if score < best_score:
                best = plan
                best_score = score
        return best

