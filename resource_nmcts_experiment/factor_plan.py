#!/usr/bin/env python3
"""ANF factorization plans and circuit emission."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import BooleanFunction, QuantumCircuit  # noqa: E402

from anf_utils import anf_monomials
from resource_model import ResourceCost, ResourceWeights, direct_cost_for_terms, gate_cost, gate_uncompute_cost


@dataclass(frozen=True)
class SearchConfig:
    weights: ResourceWeights = ResourceWeights()
    max_factor_ancilla: int = 4
    max_factor_size: int = 5
    candidate_top_k: int = 24
    min_factor_count: int = 2
    use_relative_phase: bool = True
    mcts_simulations: int = 96
    neural_mcts_simulations: int = 128
    max_polarities: int = 384
    gate_mode: str = "mct"
    neural_prior_weight: float = 1.0
    greedy_eval_limit: int = 1


@dataclass(frozen=True)
class FactorAction:
    factor: int
    group: frozenset[int]
    residuals: frozenset[int]
    rest: frozenset[int]
    immediate_gain: float
    prior: float


@dataclass
class Plan:
    kind: str
    terms: frozenset[int]
    cost: ResourceCost
    factor: int = 0
    group: Optional["Plan"] = None
    rest: Optional["Plan"] = None

    def score(self, weights: ResourceWeights) -> float:
        return self.cost.score(weights)


def _subsets(mask: int, max_size: int) -> Iterable[int]:
    bits = [i for i in range(mask.bit_length()) if (mask >> i) & 1]
    lim = min(max_size, len(bits))
    for size in range(2, lim + 1):
        # Local import keeps the hot module load cheap.
        from itertools import combinations

        for combo in combinations(bits, size):
            s = 0
            for b in combo:
                s |= 1 << b
            yield s


def candidate_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
    neural_scorer=None,
) -> List[FactorAction]:
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < config.min_factor_count:
        return []

    counts: dict[int, int] = {}
    for term in terms:
        if term.bit_count() < 2:
            continue
        for s in _subsets(term, config.max_factor_size):
            counts[s] = counts.get(s, 0) + 1

    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: List[FactorAction] = []
    for factor, cnt in counts.items():
        if cnt < config.min_factor_count:
            continue
        group = frozenset(t for t in terms if (t & factor) == factor)
        residuals = frozenset(t ^ factor for t in group)
        rest = frozenset(t for t in terms if (t & factor) != factor)
        if not residuals:
            continue

        group_direct = direct_cost_for_terms(
            group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        residual_direct = direct_cost_for_terms(
            residuals, prefix_len + 1, live_factor_ancilla + 1, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        compute = gate_cost(
            factor.bit_count(),
            live_factor_ancilla,
            use_relative_phase=config.use_relative_phase,
            alloc_target_ancilla=True,
            gate_mode=config.gate_mode,
        )
        uncompute = gate_uncompute_cost(
            factor.bit_count(),
            live_factor_ancilla,
            use_relative_phase=config.use_relative_phase,
            alloc_target_ancilla=True,
            gate_mode=config.gate_mode,
        )
        gain = group_direct - compute.score(config.weights) - uncompute.score(config.weights) - residual_direct
        coverage = len(group) / max(len(terms), 1)
        density = sum(t.bit_count() for t in residuals) / max(len(residuals), 1)
        heuristic_prior = (
            gain / max(direct_total, 1.0)
            + 0.08 * factor.bit_count()
            + 0.04 * len(group)
            - 0.02 * density
            + 0.04 * coverage
        )
        actions.append(
            FactorAction(
                factor=factor,
                group=group,
                residuals=residuals,
                rest=rest,
                immediate_gain=gain,
                prior=heuristic_prior,
            )
        )

    if neural_scorer is not None and actions:
        features = [
            action_features(
                terms,
                prefix_len,
                live_factor_ancilla,
                action.factor,
                action.group,
                action.residuals,
                action.rest,
                action.immediate_gain,
                direct_total,
            )
            for action in actions
        ]
        scores = neural_scorer.score_many(features)
        actions = [
            replace(action, prior=action.prior + config.neural_prior_weight * float(score))
            for action, score in zip(actions, scores)
        ]

    actions.sort(key=lambda a: (-a.prior, -a.immediate_gain, -a.factor.bit_count(), a.factor))
    return actions[: config.candidate_top_k]


def action_features(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    factor: int,
    group: frozenset[int],
    residuals: frozenset[int],
    rest: frozenset[int],
    gain: float,
    direct_total: float,
) -> List[float]:
    degrees = [t.bit_count() for t in terms] or [0]
    residual_degrees = [t.bit_count() for t in residuals] or [0]
    return [
        float(len(terms)),
        float(sum(degrees) / len(degrees)),
        float(max(degrees)),
        float(prefix_len),
        float(live_factor_ancilla),
        float(factor.bit_count()),
        float(len(group)),
        float(len(rest)),
        float(sum(residual_degrees) / len(residual_degrees)),
        float(max(residual_degrees)),
        float(gain / max(direct_total, 1.0)),
        float(len(group) / max(len(terms), 1)),
    ]


def direct_plan(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
) -> Plan:
    return Plan(
        kind="direct",
        terms=terms,
        cost=direct_cost_for_terms(
            terms,
            prefix_len,
            live_factor_ancilla,
            config.use_relative_phase,
            config.gate_mode,
        ),
    )


def factor_cost(
    action: FactorAction,
    group_plan: Plan,
    rest_plan: Plan,
    live_factor_ancilla: int,
    config: SearchConfig,
) -> ResourceCost:
    compute = gate_cost(
        action.factor.bit_count(),
        live_factor_ancilla,
        use_relative_phase=config.use_relative_phase,
        alloc_target_ancilla=True,
        gate_mode=config.gate_mode,
    )
    uncompute = gate_uncompute_cost(
        action.factor.bit_count(),
        live_factor_ancilla,
        use_relative_phase=config.use_relative_phase,
        alloc_target_ancilla=True,
        gate_mode=config.gate_mode,
    )
    return compute + group_plan.cost + uncompute + rest_plan.cost


def greedy_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    neural_scorer=None,
    memo: Optional[dict[tuple[frozenset[int], int, int], Plan]] = None,
) -> Plan:
    memo = {} if memo is None else memo
    key = (terms, prefix_len, live_factor_ancilla)
    if key in memo:
        return memo[key]
    best = direct_plan(terms, prefix_len, live_factor_ancilla, config)
    actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config, neural_scorer)
    limit = max(1, min(config.greedy_eval_limit, config.candidate_top_k))
    for action in actions[:limit]:
        group = greedy_plan(
            action.residuals, prefix_len + 1, live_factor_ancilla + 1, config, neural_scorer, memo
        )
        rest = greedy_plan(action.rest, prefix_len, live_factor_ancilla, config, neural_scorer, memo)
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan("factor", terms, cost, factor=action.factor, group=group, rest=rest)
        if plan.score(config.weights) < best.score(config.weights):
            best = plan
    memo[key] = best
    return best


def _emit_direct(circ: QuantumCircuit, terms: frozenset[int], prefix_controls: List[int], n_inputs: int) -> None:
    output = n_inputs
    for term in sorted(terms, key=lambda x: (x.bit_count(), x)):
        controls = list(prefix_controls) + [i for i in range(n_inputs) if (term >> i) & 1]
        circ.add_mct(controls, output)


def emit_plan_to_circuit(
    plan: Plan,
    n_inputs: int,
    max_factor_ancilla: int,
    polarity: int = 0,
) -> QuantumCircuit:
    circ = QuantumCircuit(n_inputs + 1 + max_factor_ancilla)
    free_ancilla = list(range(n_inputs + 1, n_inputs + 1 + max_factor_ancilla))

    def rec(node: Plan, prefix_controls: List[int]) -> None:
        if node.kind == "direct":
            _emit_direct(circ, node.terms, prefix_controls, n_inputs)
            return
        if node.group is None or node.rest is None:
            raise ValueError("malformed factor plan")
        if not free_ancilla:
            raise ValueError("plan requires more factor ancilla than allocated")
        anc = free_ancilla.pop(0)
        controls = [i for i in range(n_inputs) if (node.factor >> i) & 1]
        circ.add_mct(controls, anc)
        rec(node.group, prefix_controls + [anc])
        circ.add_mct(controls, anc)
        free_ancilla.insert(0, anc)
        rec(node.rest, prefix_controls)

    for b in range(n_inputs):
        if (polarity >> b) & 1:
            circ.add_x(b)
    rec(plan, [])
    for b in range(n_inputs):
        if (polarity >> b) & 1:
            circ.add_x(b)
    return circ


def verify_oracle(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0] * (circ.n_qubits - n)
        out = circ.simulate(bits)
        if out[n] != bf.evaluate(x):
            return False
        if out[:n] != bits[:n]:
            return False
        if any(out[n + 1 :]):
            return False
    return True


def plan_for_function(
    bf: BooleanFunction,
    config: SearchConfig,
    method: str = "greedy",
    neural_scorer=None,
):
    terms = frozenset(anf_monomials(bf))
    if method == "direct":
        plan = direct_plan(terms, 0, 0, config)
    elif method == "greedy":
        plan = greedy_plan(terms, config=config, neural_scorer=neural_scorer)
    else:
        raise ValueError(method)
    circ = emit_plan_to_circuit(plan, bf.n, config.max_factor_ancilla)
    return plan, circ
