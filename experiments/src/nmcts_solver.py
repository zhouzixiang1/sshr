#!/usr/bin/env python3
"""Recursive PUCT/MCTS solver for ANF factorization plans."""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
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
from src.search.mcts_scheduler import (
    ActionScheduleDecision,
    DiversitySchedulerConfig,
    MCTSDiversityScheduler,
)
from src.search.execution_feedback import (
    ExecutionUtilityAdjustment,
    ExecutionUtilityAdjuster,
)


_USE_POLICY_SCORER = object()


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
    #: ``actions[:prefetched]`` have already had their subtree values batched.
    prefetched: int = 0
    #: A fixed-budget scheduler is evaluated at most once for each state.
    scheduler_decision: Optional[ActionScheduleDecision] = None
    #: Original indices into ``actions``; ``None`` means ordinary MCTS behavior.
    admitted_indices: Optional[tuple[int, ...]] = None
    #: Newly admitted edges receive one independent evaluation per simulation.
    pending_indices: list[int] = field(default_factory=list)


class NeuralMCTSSolver:
    def __init__(
        self,
        config: SearchConfig,
        simulations: int = 96,
        c_puct: float = 1.35,
        seed: int = 0,
        neural_scorer=None,
        value_estimator=None,
        widen_c: float = 2.0,
        rollout_scorer=_USE_POLICY_SCORER,
        scheduler_config: Optional[DiversitySchedulerConfig] = None,
        diversity_scheduler: Optional[MCTSDiversityScheduler] = None,
        execution_utility_adjuster: Optional[ExecutionUtilityAdjuster] = None,
    ) -> None:
        self.config = config
        self.simulations = simulations
        self.c_puct = c_puct
        self.rng = random.Random(seed)
        self.neural_scorer = neural_scorer
        # Legacy behavior uses the action-policy scorer inside classical greedy
        # rollouts too.  Causal ablations can now pass ``rollout_scorer=None``
        # to keep the value evaluator heuristic while changing only the MCTS
        # action policy.  The sentinel preserves every existing call site.
        self.rollout_scorer = (
            neural_scorer if rollout_scorer is _USE_POLICY_SCORER else rollout_scorer
        )
        # When absent, subtree values come from a classical greedy rollout --
        # the original behaviour, preserved exactly.
        self.value_estimator = value_estimator
        self.widen_c = widen_c
        self.nodes: Dict[StateKey, SearchNode] = {}
        self.greedy_memo: dict[tuple[frozenset[int], int, int], Plan] = {}
        if diversity_scheduler is not None and scheduler_config is not None:
            if diversity_scheduler.config != scheduler_config:
                raise ValueError(
                    "diversity_scheduler.config and scheduler_config disagree"
                )
        self.scheduler_config = (
            scheduler_config
            if scheduler_config is not None
            else (
                diversity_scheduler.config
                if diversity_scheduler is not None
                else DiversitySchedulerConfig(method="off")
            )
        )
        self.diversity_scheduler = (
            diversity_scheduler
            if diversity_scheduler is not None
            else MCTSDiversityScheduler(self.scheduler_config)
        )
        self.execution_utility_adjuster = execution_utility_adjuster
        self.scheduler_records: list[dict[str, object]] = []

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
        """Value of an unexplored subtree.

        With a learned estimator this is a single forward pass; without one it
        falls back to building an actual greedy plan, which is accurate but is
        the search's dominant cost.
        """
        if self.value_estimator is not None:
            direct = self._node(key).direct.score(self.config.weights)
            estimate = self.value_estimator.estimate(
                key.terms, key.prefix_len, key.live_factor_ancilla, direct
            )
            # A hybrid estimator returns None to hand small states back to the
            # classical rollout, which is cheaper than a forward pass there.
            if estimate is not None:
                return estimate
        plan = greedy_plan(
            key.terms,
            key.prefix_len,
            key.live_factor_ancilla,
            self.config,
            self.rollout_scorer,
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

        eligible_indices = self._eligible_indices(node, depth)
        self._prefetch_action_values(
            node,
            (
                min(self.scheduler_config.pool_size, len(node.actions))
                if node.admitted_indices is not None
                else self._considered_width(node)
            ),
        )

        total_prior = sum(
            max(0.0, node.actions[index].prior) + 1e-3
            for index in eligible_indices
        )
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

        if node.pending_indices:
            idx = node.pending_indices.pop(0)
        else:
            idx = min(eligible_indices, key=select_key)
        action = node.actions[idx]
        estimate = self._evaluate_action_recursive(key, action, depth)
        st = node.stats[idx]
        st.visits += 1
        st.q += (estimate - st.q) / st.visits
        return min(direct_score, estimate)

    @staticmethod
    def _state_id(key: StateKey) -> str:
        """Stable state identifier shared by logs from different processes."""

        payload = (
            f"prefix={key.prefix_len};live={key.live_factor_ancilla};terms="
            + ",".join(str(term) for term in sorted(key.terms))
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _action_signature(action: FactorAction) -> dict[str, object]:
        return {
            "factor": int(action.factor),
            "group": sorted(int(term) for term in action.group),
            "residuals": sorted(int(term) for term in action.residuals),
            "rest": sorted(int(term) for term in action.rest),
        }

    def _scheduler_applies(self, node: SearchNode, depth: int) -> bool:
        return (
            self.scheduler_config.method != "off"
            and depth <= self.scheduler_config.max_depth
            and bool(node.actions)
        )

    def _scheduler_seed(self, key: StateKey) -> int:
        payload = f"{self.scheduler_config.seed}:{self._state_id(key)}"
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    def _eligible_indices(self, node: SearchNode, depth: int) -> tuple[int, ...]:
        """Return selectable action indices, freezing scheduler decisions once."""

        # A transposed state can be reached at more than one recursion depth.
        # Once scheduled, its admitted edge set remains authoritative even if
        # a later path reaches it outside the configured invocation depth.
        if node.admitted_indices is not None:
            return node.admitted_indices
        if not self._scheduler_applies(node, depth):
            width = self._considered_width(node)
            return tuple(range(width))
        if node.scheduler_decision is None:
            self._schedule_node(node, depth)
        if not node.admitted_indices:
            # The scheduler contract guarantees a non-empty selection for a
            # non-empty pool and positive budget.  Treat violations as errors,
            # never silently widen to excluded actions.
            raise RuntimeError("diversity scheduler admitted no action")
        return node.admitted_indices

    def _schedule_node(self, node: SearchNode, depth: int) -> None:
        pool_width = min(self.scheduler_config.pool_size, len(node.actions))
        self._prefetch_action_values(node, pool_width)
        pool_actions = node.actions[:pool_width]
        direct_score = node.direct.score(self.config.weights)
        denominator = max(abs(direct_score), 1.0)
        utility_started = time.perf_counter()
        raw_utilities = tuple(
            (direct_score - self._rollout_action_cost(node.key, action)) / denominator
            for action in pool_actions
        )
        utility_elapsed = time.perf_counter() - utility_started
        if len(raw_utilities) != pool_width or any(
            not math.isfinite(value) for value in raw_utilities
        ):
            raise ValueError("raw scheduler utilities must be finite and match the pool")

        feedback_started = time.perf_counter()
        if self.execution_utility_adjuster is None:
            adjusted_utilities = raw_utilities
            feedback_audit: dict[str, object] = {
                "enabled": False,
                "predicted_execution_costs": [],
                "normalized_execution_penalties": [],
                "penalty_weight": 0.0,
                "cost_offset": 0.0,
                "cost_scale": 1.0,
                "model_metadata": {},
                "model_sha256": None,
            }
        else:
            adjustment = self.execution_utility_adjuster.adjust(
                node.key, pool_actions, raw_utilities
            )
            if not isinstance(adjustment, ExecutionUtilityAdjustment):
                raise TypeError(
                    "execution_utility_adjuster.adjust must return "
                    "ExecutionUtilityAdjustment"
                )
            adjusted_utilities = tuple(adjustment.adjusted_utilities)
            feedback_audit = {"enabled": True, **adjustment.audit_dict()}
        feedback_elapsed = time.perf_counter() - feedback_started
        if len(adjusted_utilities) != pool_width:
            raise ValueError(
                "adjusted scheduler utility count must match the candidate pool"
            )
        if any(not math.isfinite(value) for value in adjusted_utilities):
            raise ValueError("adjusted scheduler utilities must all be finite")

        decision = self.diversity_scheduler.select(
            pool_actions,
            adjusted_utilities,
            decision_seed=self._scheduler_seed(node.key),
        )
        selected = tuple(int(index) for index in decision.selected_indices)
        if len(set(selected)) != len(selected):
            raise RuntimeError("diversity scheduler returned duplicate action indices")
        if any(index < 0 or index >= pool_width for index in selected):
            raise RuntimeError("diversity scheduler returned an out-of-pool action index")

        pool_signatures = [self._action_signature(action) for action in pool_actions]
        pool_payload = json.dumps(
            pool_signatures,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        diagnostics = dict(decision.diagnostics)
        diagnostics.update(
            node_id=self._state_id(node.key),
            invocation_depth=int(depth),
            pool_width=int(pool_width),
            candidate_pool_sha256=hashlib.sha256(pool_payload).hexdigest(),
            candidate_action_signatures=pool_signatures,
            raw_utilities=list(raw_utilities),
            adjusted_utilities=list(adjusted_utilities),
            direct_score=float(direct_score),
            utility_elapsed_s=float(utility_elapsed),
            execution_feedback_elapsed_s=float(feedback_elapsed),
            execution_feedback=feedback_audit,
            execution_feedback_enabled=bool(feedback_audit["enabled"]),
            execution_feedback_model_metadata=feedback_audit["model_metadata"],
            execution_feedback_model_sha256=feedback_audit["model_sha256"],
            execution_feedback_penalty_weight=float(feedback_audit["penalty_weight"]),
            selected_action_signatures=[
                self._action_signature(node.actions[index]) for index in selected
            ],
        )
        persisted = ActionScheduleDecision(selected, diagnostics)
        node.scheduler_decision = persisted
        node.admitted_indices = selected
        node.pending_indices = list(selected)
        self.scheduler_records.append(persisted.to_dict())

    def scheduler_summary(self) -> dict[str, object]:
        """Aggregate disjoint QAOA invocation outcomes and edge evaluations."""

        diagnostics = [record["diagnostics"] for record in self.scheduler_records]
        scheduled_nodes = [
            node for node in self.nodes.values() if node.admitted_indices is not None
        ]
        return {
            "scheduler_method": self.scheduler_config.method,
            "scheduler_decisions": len(diagnostics),
            "qaoa_not_invoked": sum(
                item.get("status") == "qaoa_not_invoked" for item in diagnostics
            ),
            "qaoa_attempted": sum(
                bool(item.get("qaoa_attempted")) for item in diagnostics
            ),
            "qaoa_succeeded": sum(
                bool(item.get("qaoa_succeeded")) for item in diagnostics
            ),
            "qaoa_repaired": sum(
                bool(item.get("qaoa_repaired")) for item in diagnostics
            ),
            "qaoa_fallback": sum(
                bool(item.get("qaoa_fallback")) for item in diagnostics
            ),
            "selected_action_evaluations": sum(
                node.stats[index].visits
                for node in scheduled_nodes
                for index in (node.admitted_indices or ())
            ),
            "scheduler_wall_s": sum(
                float(item.get("total_elapsed_s", 0.0))
                + float(item.get("utility_elapsed_s", 0.0))
                + float(item.get("execution_feedback_elapsed_s", 0.0))
                for item in diagnostics
            ),
        }

    def _considered_width(self, node: SearchNode) -> int:
        """How many of the prior-ranked actions are selectable right now.

        Pricing every candidate on a node's first visit is what the classical
        rollout could afford and a network cannot: it costs two forward passes
        per action, and most of those actions are never visited again.  Widening
        the window with the visit count instead bounds that cost, and it is what
        makes the policy prior load-bearing -- ``candidate_actions`` returns
        actions sorted by prior, so anything the prior ranks low is not merely
        explored later, it is not evaluated at all until the node earns the
        visits.  A misranking therefore costs real search quality rather than
        being silently corrected by an exhaustive first sweep.

        Without a value estimator the rollout is cheap enough to price
        everything, and the original exhaustive behaviour is kept.
        """
        if self.value_estimator is None:
            return len(node.actions)
        width = int(self.widen_c * math.sqrt(node.visits))
        return max(1, min(len(node.actions), width))

    def _prefetch_action_values(self, node: SearchNode, width: int) -> None:
        """Value this node's newly-considered branches in one batched pass.

        Selection prices each unvisited action by valuing both the branch it
        factors out and the branch it leaves behind.  Within one visit those
        states are all known before the comparison starts, so an estimator that
        supports batching can evaluate them together rather than once per
        action.  Purely an evaluation-order change: the values obtained are
        identical either way.

        Only the actions that entered the window since the last visit are
        submitted -- re-deriving the whole window on every visit costs more
        Python than the batching saves.
        """
        if width <= node.prefetched:
            return
        prefetch = getattr(self.value_estimator, "prefetch", None)
        if prefetch is None:
            return

        key = node.key
        requests = []
        for action in node.actions[node.prefetched : width]:
            requests.append(
                (action.residuals, key.prefix_len + 1, key.live_factor_ancilla + 1)
            )
            requests.append((action.rest, key.prefix_len, key.live_factor_ancilla))
        node.prefetched = width
        if requests:
            prefetch(requests)

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
        candidate_indices = (
            node.admitted_indices
            if node.admitted_indices is not None
            else tuple(range(len(node.actions)))
        )
        for idx in candidate_indices:
            action = node.actions[idx]
            st = node.stats.get(idx)
            if st is None or st.visits == 0:
                # An unvisited action carries no search evidence.  The greedy
                # rollout returns an *achievable* score, so it prunes reliably;
                # a learned value is a lower bound on what might be achievable
                # and would pass this test almost everywhere, making the rebuild
                # recurse into every branch and blow up exponentially.  With a
                # learned estimator, trust only what the search actually visited.
                if self.value_estimator is not None or node.admitted_indices is not None:
                    continue
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
