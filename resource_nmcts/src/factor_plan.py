#!/usr/bin/env python3
"""ANF factorization plans and circuit emission."""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Iterable, List, Optional

from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit, mct_cost, mct_cost_rp

from src.anf_utils import anf_monomials
from src.resource_model import ResourceCost, ResourceWeights, direct_cost_for_terms, gate_cost, gate_uncompute_cost


LINEAR_REST_RECURSE_TERM_LIMIT = 900


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
    linear: bool = False
    affine_const: bool = False


@dataclass
class Plan:
    kind: str
    terms: frozenset[int]
    cost: ResourceCost
    factor: int = 0
    group: Optional["Plan"] = None
    rest: Optional["Plan"] = None
    affine_const: bool = False

    def score(self, weights: ResourceWeights) -> float:
        return self.cost.score(weights)


@dataclass(frozen=True)
class PlanAnfVerification:
    ok: bool
    nodes: int
    max_expanded_terms: int
    mismatches: int


@dataclass(frozen=True)
class CircuitAnfVerification:
    ok: bool
    gates: int
    max_wire_terms: int
    output_terms: int
    input_mismatches: int
    output_mismatch: int
    ancilla_mismatches: int


@dataclass(frozen=True)
class CircuitScheduleMetrics:
    """Logic-level schedule proxies for an emitted oracle circuit.

    These metrics deliberately avoid hardware mapping assumptions.  MCT gates
    are treated as logical operations that occupy all controls and the target
    for a decomposition-duration proxy.
    """

    logical_depth: int
    cnot_depth_proxy: int
    t_depth_proxy: int
    explicit_ancilla_live_peak: int
    explicit_ancilla_lifetime_area: int


def _xor_term_sets(*items: frozenset[int]) -> frozenset[int]:
    out: set[int] = set()
    for terms in items:
        for term in terms:
            if term in out:
                out.remove(term)
            else:
                out.add(term)
    return frozenset(out)


def _xor_term_values(values: Iterable[int]) -> frozenset[int]:
    out: set[int] = set()
    for raw in values:
        term = int(raw)
        if term in out:
            out.remove(term)
        else:
            out.add(term)
    return frozenset(out)


def _multiply_monomial_terms(terms: frozenset[int], factor: int) -> frozenset[int]:
    return _xor_term_values(int(term) | int(factor) for term in terms)


def _multiply_polynomial_terms(lhs: frozenset[int], rhs: frozenset[int]) -> frozenset[int]:
    if not lhs or not rhs:
        return frozenset()
    return _xor_term_values(int(left) | int(right) for left in lhs for right in rhs)


def _multiply_linear_terms(terms: frozenset[int], factor: int, affine_const: bool = False) -> frozenset[int]:
    out: set[int] = set()

    def toggle(term: int) -> None:
        if term in out:
            out.remove(term)
        else:
            out.add(term)

    if affine_const:
        for term in terms:
            toggle(int(term))
    bits = int(factor)
    while bits:
        bit = bits & -bits
        for term in terms:
            toggle(int(term) | bit)
        bits ^= bit
    return frozenset(out)


def expand_plan_anf_terms(plan: Plan) -> frozenset[int]:
    """Expand a factor plan back to the ANF terms it implements.

    This is a symbolic checker over GF(2) monomial sets.  It does not build a
    truth table, so it remains cheap for high-dimensional sparse ANF states.
    """
    if plan.kind == "direct":
        return frozenset(plan.terms)
    if plan.group is None or plan.rest is None:
        raise ValueError("malformed factor plan")
    group_terms = expand_plan_anf_terms(plan.group)
    rest_terms = expand_plan_anf_terms(plan.rest)
    if plan.kind == "factor":
        factored = _multiply_monomial_terms(group_terms, plan.factor)
    elif plan.kind == "linear_factor":
        factored = _multiply_linear_terms(group_terms, plan.factor, plan.affine_const)
    else:
        raise ValueError(f"unknown plan kind: {plan.kind}")
    return _xor_term_sets(factored, rest_terms)


def verify_plan_anf(plan: Plan) -> PlanAnfVerification:
    nodes = 0
    mismatches = 0
    max_expanded_terms = 0

    def rec(node: Plan) -> frozenset[int]:
        nonlocal nodes, mismatches, max_expanded_terms
        nodes += 1
        expanded = expand_plan_anf_terms(node)
        max_expanded_terms = max(max_expanded_terms, len(expanded))
        if expanded != node.terms:
            mismatches += 1
        if node.group is not None:
            rec(node.group)
        if node.rest is not None:
            rec(node.rest)
        return expanded

    rec(plan)
    return PlanAnfVerification(
        ok=mismatches == 0,
        nodes=nodes,
        max_expanded_terms=max_expanded_terms,
        mismatches=mismatches,
    )


def _failed_circuit_verification(
    circ: QuantumCircuit,
    max_wire_terms: int = 0,
    input_mismatches: int = 0,
    output_mismatch: int = 1,
    ancilla_mismatches: int = 0,
) -> CircuitAnfVerification:
    return CircuitAnfVerification(
        ok=False,
        gates=len(circ.gates),
        max_wire_terms=max_wire_terms,
        output_terms=0,
        input_mismatches=input_mismatches,
        output_mismatch=output_mismatch,
        ancilla_mismatches=ancilla_mismatches,
    )


def verify_circuit_anf(circ: QuantumCircuit, n_inputs: int, expected_terms: frozenset[int]) -> CircuitAnfVerification:
    """Verify an emitted oracle circuit symbolically over ANF polynomials.

    Unlike ``verify_oracle``, this does not enumerate a truth table.  Each wire
    is represented as a GF(2) set of monomial masks over the original inputs.
    ``MCT`` gates multiply control polynomials in the Boolean ring where
    variables are idempotent, so monomial products are represented by bitwise
    OR and duplicate terms cancel.
    """
    if circ.n_qubits <= n_inputs:
        return _failed_circuit_verification(circ)

    wires: list[frozenset[int]] = [frozenset({1 << i}) for i in range(n_inputs)]
    wires.extend(frozenset() for _ in range(circ.n_qubits - n_inputs))
    max_wire_terms = max((len(poly) for poly in wires), default=0)

    def valid_index(index: int) -> bool:
        return 0 <= index < circ.n_qubits

    for gate in circ.gates:
        target = int(gate.target)
        if not valid_index(target):
            return _failed_circuit_verification(circ, max_wire_terms=max_wire_terms)
        if gate.type == "X":
            wires[target] = _xor_term_sets(wires[target], frozenset({0}))
        elif gate.type == "CNOT":
            if len(gate.controls) != 1:
                return _failed_circuit_verification(circ, max_wire_terms=max_wire_terms)
            control = int(gate.controls[0])
            if not valid_index(control):
                return _failed_circuit_verification(circ, max_wire_terms=max_wire_terms)
            wires[target] = _xor_term_sets(wires[target], wires[control])
        elif gate.type == "MCT":
            controls = [int(control) for control in gate.controls]
            if any(not valid_index(control) for control in controls):
                return _failed_circuit_verification(circ, max_wire_terms=max_wire_terms)
            product = frozenset({0})
            for control in controls:
                product = _multiply_polynomial_terms(product, wires[control])
                if not product:
                    break
            wires[target] = _xor_term_sets(wires[target], product)
        else:
            return _failed_circuit_verification(circ, max_wire_terms=max_wire_terms)
        max_wire_terms = max(max_wire_terms, len(wires[target]))

    input_mismatches = sum(1 for i in range(n_inputs) if wires[i] != frozenset({1 << i}))
    output_terms = len(wires[n_inputs])
    output_mismatch = int(wires[n_inputs] != frozenset(expected_terms))
    ancilla_mismatches = sum(1 for poly in wires[n_inputs + 1 :] if poly)
    return CircuitAnfVerification(
        ok=input_mismatches == 0 and output_mismatch == 0 and ancilla_mismatches == 0,
        gates=len(circ.gates),
        max_wire_terms=max_wire_terms,
        output_terms=output_terms,
        input_mismatches=input_mismatches,
        output_mismatch=output_mismatch,
        ancilla_mismatches=ancilla_mismatches,
    )


def _mct_schedule_proxy(controls: int, use_relative_phase: bool = True) -> tuple[int, int]:
    """Return (CNOT-depth proxy, T-depth proxy) for one emitted MCT gate."""
    if controls <= 1:
        return (1 if controls == 1 else 0), 0
    cost = mct_cost_rp(controls) if use_relative_phase else mct_cost(controls)
    t_count = int(cost.get("T", 0))
    cnot_count = int(cost.get("CNOT", 0))
    # This is a decomposition-independent stage proxy, not a hardware T-depth.
    # It prevents a 32-T MCT and a 4-T Toffoli from looking identical while
    # avoiding unsupported claims about a specific Clifford+T template.
    t_depth = (t_count + 3) // 4
    return max(1, cnot_count), t_depth


def analyze_circuit_schedule(
    circ: QuantumCircuit,
    n_inputs: int,
    use_relative_phase: bool = True,
) -> CircuitScheduleMetrics:
    """Compute logic-level schedule proxies for an emitted circuit.

    ``logical_depth`` layers gates by wire conflicts. ``cnot_depth_proxy`` uses
    the CNOT count of a decomposed MCT as an occupation duration. ``t_depth`` is
    a non-Clifford stage proxy based on four T gates per stage.  Explicit
    ancillary lifetime is measured over emitted logical-gate layers for wires
    after the output qubit.
    """
    logical_ready = [0] * circ.n_qubits
    cnot_ready = [0] * circ.n_qubits
    t_ready = [0] * circ.n_qubits
    ancilla_spans: dict[int, list[int]] = {}

    for gate in circ.gates:
        involved = [int(control) for control in gate.controls] + [int(gate.target)]
        if any(wire < 0 or wire >= circ.n_qubits for wire in involved):
            continue
        logical_start = max((logical_ready[wire] for wire in involved), default=0)
        logical_end = logical_start + 1
        for wire in involved:
            logical_ready[wire] = logical_end
            if wire > n_inputs:
                span = ancilla_spans.setdefault(wire, [logical_start, logical_end])
                span[0] = min(span[0], logical_start)
                span[1] = max(span[1], logical_end)

        if gate.type == "X":
            cnot_duration, t_duration = 1, 0
        elif gate.type == "CNOT":
            cnot_duration, t_duration = 1, 0
        elif gate.type == "MCT":
            cnot_duration, t_duration = _mct_schedule_proxy(len(gate.controls), use_relative_phase)
        else:
            cnot_duration, t_duration = 1, 0

        cnot_start = max((cnot_ready[wire] for wire in involved), default=0)
        cnot_end = cnot_start + cnot_duration
        for wire in involved:
            cnot_ready[wire] = cnot_end

        t_start = max((t_ready[wire] for wire in involved), default=0)
        t_end = t_start + t_duration
        for wire in involved:
            t_ready[wire] = t_end

    events: list[tuple[int, int]] = []
    area = 0
    for first, last in ancilla_spans.values():
        if last <= first:
            continue
        area += last - first
        events.append((first, 1))
        events.append((last, -1))

    live = peak = 0
    for layer in sorted({layer for layer, _delta in events}):
        ending = sum(delta for event_layer, delta in events if event_layer == layer and delta < 0)
        starting = sum(delta for event_layer, delta in events if event_layer == layer and delta > 0)
        live += ending
        live += starting
        peak = max(peak, live)

    return CircuitScheduleMetrics(
        logical_depth=max(logical_ready, default=0),
        cnot_depth_proxy=max(cnot_ready, default=0),
        t_depth_proxy=max(t_ready, default=0),
        explicit_ancilla_live_peak=peak,
        explicit_ancilla_lifetime_area=area,
    )


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
        group_items = []
        residual_items = []
        rest_items = []
        for term in terms:
            if (term & factor) == factor:
                group_items.append(term)
                residual_items.append(term ^ factor)
            else:
                rest_items.append(term)
        group = frozenset(group_items)
        residuals = frozenset(residual_items)
        rest = frozenset(rest_items)
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


def _linear_factor_resource(factor: int, live_factor_ancilla: int, affine_const: bool = False) -> ResourceCost:
    width = int(factor).bit_count()
    live = live_factor_ancilla + 1
    x_ops = 1 if affine_const else 0
    return ResourceCost(CNOT=width, gates=width + x_ops, depth=width + x_ops, explicit_ancilla=live, peak_ancilla=live)


def _subsets_of_size(mask: int, size: int) -> Iterable[int]:
    bits = [i for i in range(mask.bit_length()) if (mask >> i) & 1]
    if len(bits) < size:
        return
    from itertools import combinations

    for combo in combinations(bits, size):
        s = 0
        for b in combo:
            s |= 1 << b
        yield s


def _linear_boolean_expansion(factor: int, residual: int) -> frozenset[int]:
    """Expand ``(xor factor variables) * residual`` in the Boolean ring."""
    out: set[int] = set()
    bits = int(factor)
    while bits:
        bit = bits & -bits
        term = int(residual) | bit
        if term in out:
            out.remove(term)
        else:
            out.add(term)
        bits ^= bit
    return frozenset(out)


def linear_factor_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
    action_width: int | None = None,
    max_linear_width: int = 2,
    neural_scorer=None,
) -> List[FactorAction]:
    """Find linear parity factors ``(x_i xor x_j xor ...) * g`` inside an ANF.

    The quotient terms are restricted to monomials that contain neither
    variable in the linear factor.  This keeps the transformation simple,
    circuit-emittable, and easy to verify while exposing a cheap CNOT-only
    factor type that monomial factoring cannot represent.
    """
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < 2 * config.min_factor_count:
        return []
    n_bits = max((int(t).bit_length() for t in terms), default=0)
    if n_bits < 2:
        return []

    termset = set(terms)
    support_by_residual: dict[int, int] = {}
    for term in termset:
        bits = int(term)
        while bits:
            bit = bits & -bits
            residual = term ^ bit
            support_by_residual[residual] = support_by_residual.get(residual, 0) | bit
            bits ^= bit

    residuals_by_factor: dict[int, set[int]] = {}
    max_width = max(2, min(max_linear_width, n_bits))
    for residual, support in support_by_residual.items():
        # Defensive masking keeps the quotient disjoint from every variable in
        # the linear factor even if future callers supply unusual term sets.
        available = support & ~residual
        available_count = available.bit_count()
        for width in range(2, max_width + 1):
            if available_count < width:
                continue
            for factor in _subsets_of_size(available, width):
                residuals_by_factor.setdefault(factor, set()).add(residual)

    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: List[FactorAction] = []
    for factor, residuals in residuals_by_factor.items():
        if len(residuals) < config.min_factor_count:
            continue
        factor_bits = [1 << i for i in range(factor.bit_length()) if (factor >> i) & 1]
        group_terms = {residual | bit for residual in residuals for bit in factor_bits}
        group = frozenset(group_terms)
        residual_set = frozenset(residuals)
        rest = frozenset(t for t in terms if t not in group_terms)
        group_direct = direct_cost_for_terms(
            group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        residual_direct = direct_cost_for_terms(
            residual_set,
            prefix_len + 1,
            live_factor_ancilla + 1,
            config.use_relative_phase,
            config.gate_mode,
        ).score(config.weights)
        compute = _linear_factor_resource(factor, live_factor_ancilla)
        uncompute = _linear_factor_resource(factor, live_factor_ancilla)
        gain = group_direct - compute.score(config.weights) - uncompute.score(config.weights) - residual_direct
        coverage = len(group) / max(len(terms), 1)
        density = sum(t.bit_count() for t in residual_set) / max(len(residual_set), 1)
        heuristic_prior = (
            gain / max(direct_total, 1.0)
            + 0.04 * len(group)
            + 0.08 * coverage
            + 0.02 * factor.bit_count()
            - 0.02 * density
        )
        actions.append(
            FactorAction(
                factor=factor,
                group=group,
                residuals=residual_set,
                rest=rest,
                immediate_gain=gain,
                prior=heuristic_prior,
                linear=True,
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

    width = action_width if action_width is not None else max(2, min(config.candidate_top_k, 8))
    actions.sort(key=lambda a: (-a.prior, -a.immediate_gain, -len(a.group), a.factor))
    return actions[: max(1, min(width, len(actions)))]


def boolean_linear_factor_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
    action_width: int | None = None,
    max_linear_width: int = 2,
    neural_scorer=None,
) -> List[FactorAction]:
    """Find linear factors in the square-free Boolean ring.

    Unlike ``linear_factor_actions``, quotient monomials may share variables
    with the parity factor.  Expansion uses ``x_i^2=x_i`` and cancels duplicate
    ANF terms over GF(2).  Candidate quotients are restricted to disjoint
    expansions already present in ``terms`` so the residual problem is still a
    monotone set subtraction.
    """
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < 2 * config.min_factor_count:
        return []
    n_bits = max((int(t).bit_length() for t in terms), default=0)
    if n_bits < 2:
        return []

    termset = set(terms)
    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: List[FactorAction] = []
    max_width = max(2, min(max_linear_width, n_bits))
    all_vars = (1 << n_bits) - 1

    for width in range(2, max_width + 1):
        for factor in _subsets_of_size(all_vars, width):
            factor_bits = [1 << i for i in range(factor.bit_length()) if (factor >> i) & 1]
            residual_candidates: dict[int, frozenset[int]] = {}
            for term in termset:
                residual_candidates.setdefault(term, _linear_boolean_expansion(factor, term))
                for bit in factor_bits:
                    if term & bit:
                        residual = term ^ bit
                        residual_candidates.setdefault(
                            residual,
                            _linear_boolean_expansion(factor, residual),
                        )

            scored_residuals: list[tuple[float, int, int, frozenset[int]]] = []
            for residual, expansion in residual_candidates.items():
                if not expansion or not expansion.issubset(termset):
                    continue
                group_direct = direct_cost_for_terms(
                    expansion,
                    prefix_len,
                    live_factor_ancilla,
                    config.use_relative_phase,
                    config.gate_mode,
                ).score(config.weights)
                residual_direct = direct_cost_for_terms(
                    frozenset({residual}),
                    prefix_len + 1,
                    live_factor_ancilla + 1,
                    config.use_relative_phase,
                    config.gate_mode,
                ).score(config.weights)
                local_gain = group_direct - residual_direct
                if local_gain <= 0:
                    continue
                scored_residuals.append((local_gain, len(expansion), residual, expansion))

            if len(scored_residuals) < config.min_factor_count:
                continue
            scored_residuals.sort(key=lambda item: (-item[0], -item[1], item[2]))

            used_terms: set[int] = set()
            selected_residuals: set[int] = set()
            for _gain, _size, residual, expansion in scored_residuals:
                if used_terms.intersection(expansion):
                    continue
                used_terms.update(expansion)
                selected_residuals.add(residual)

            if len(selected_residuals) < config.min_factor_count or len(used_terms) < 2 * config.min_factor_count:
                continue

            group = frozenset(used_terms)
            residual_set = frozenset(selected_residuals)
            rest = frozenset(t for t in terms if t not in used_terms)
            group_direct = direct_cost_for_terms(
                group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
            ).score(config.weights)
            residual_direct = direct_cost_for_terms(
                residual_set,
                prefix_len + 1,
                live_factor_ancilla + 1,
                config.use_relative_phase,
                config.gate_mode,
            ).score(config.weights)
            compute = _linear_factor_resource(factor, live_factor_ancilla)
            uncompute = _linear_factor_resource(factor, live_factor_ancilla)
            gain = group_direct - compute.score(config.weights) - uncompute.score(config.weights) - residual_direct
            if gain <= 0:
                continue
            coverage = len(group) / max(len(terms), 1)
            density = sum(t.bit_count() for t in residual_set) / max(len(residual_set), 1)
            overlap = sum(1 for residual in residual_set if residual & factor) / max(len(residual_set), 1)
            heuristic_prior = (
                gain / max(direct_total, 1.0)
                + 0.04 * len(group)
                + 0.10 * coverage
                + 0.02 * factor.bit_count()
                + 0.03 * overlap
                - 0.02 * density
            )
            actions.append(
                FactorAction(
                    factor=factor,
                    group=group,
                    residuals=residual_set,
                    rest=rest,
                    immediate_gain=gain,
                    prior=heuristic_prior,
                    linear=True,
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

    width = action_width if action_width is not None else max(2, min(config.candidate_top_k, 8))
    actions.sort(key=lambda a: (-a.prior, -a.immediate_gain, -len(a.group), a.factor))
    return actions[: max(1, min(width, len(actions)))]


def affine_linear_factor_actions(
    terms: frozenset[int],
    prefix_len: int,
    live_factor_ancilla: int,
    config: SearchConfig,
    action_width: int | None = None,
    max_linear_width: int = 2,
    neural_scorer=None,
) -> List[FactorAction]:
    """Find affine-linear factors ``(1 xor x_i xor ...) * g`` in an ANF."""
    if live_factor_ancilla >= config.max_factor_ancilla or len(terms) < 2 * config.min_factor_count:
        return []
    n_bits = max((int(t).bit_length() for t in terms), default=0)
    if n_bits < 1:
        return []

    termset = set(terms)
    support_by_residual: dict[int, int] = {}
    for term in termset:
        bits = int(term)
        while bits:
            bit = bits & -bits
            residual = term ^ bit
            support_by_residual[residual] = support_by_residual.get(residual, 0) | bit
            bits ^= bit

    residuals_by_factor: dict[int, set[int]] = {}
    max_width = max(1, min(max_linear_width, n_bits))
    for residual, support in support_by_residual.items():
        if residual not in termset:
            continue
        available = support & ~residual
        available_count = available.bit_count()
        for width in range(1, max_width + 1):
            if available_count < width:
                continue
            for factor in _subsets_of_size(available, width):
                residuals_by_factor.setdefault(factor, set()).add(residual)

    direct_total = direct_cost_for_terms(
        terms, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
    ).score(config.weights)
    actions: List[FactorAction] = []
    for factor, residuals in residuals_by_factor.items():
        if len(residuals) < config.min_factor_count:
            continue
        factor_bits = [1 << i for i in range(factor.bit_length()) if (factor >> i) & 1]
        group_terms = set(residuals)
        group_terms.update(residual | bit for residual in residuals for bit in factor_bits)
        group = frozenset(group_terms)
        residual_set = frozenset(residuals)
        rest = frozenset(t for t in terms if t not in group_terms)
        group_direct = direct_cost_for_terms(
            group, prefix_len, live_factor_ancilla, config.use_relative_phase, config.gate_mode
        ).score(config.weights)
        residual_direct = direct_cost_for_terms(
            residual_set,
            prefix_len + 1,
            live_factor_ancilla + 1,
            config.use_relative_phase,
            config.gate_mode,
        ).score(config.weights)
        compute = _linear_factor_resource(factor, live_factor_ancilla, affine_const=True)
        uncompute = _linear_factor_resource(factor, live_factor_ancilla, affine_const=True)
        gain = group_direct - compute.score(config.weights) - uncompute.score(config.weights) - residual_direct
        coverage = len(group) / max(len(terms), 1)
        density = sum(t.bit_count() for t in residual_set) / max(len(residual_set), 1)
        heuristic_prior = (
            gain / max(direct_total, 1.0)
            + 0.04 * len(group)
            + 0.08 * coverage
            + 0.02 * factor.bit_count()
            - 0.02 * density
            - 0.01
        )
        actions.append(
            FactorAction(
                factor=factor,
                group=group,
                residuals=residual_set,
                rest=rest,
                immediate_gain=gain,
                prior=heuristic_prior,
                linear=True,
                affine_const=True,
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

    width = action_width if action_width is not None else max(2, min(config.candidate_top_k, 8))
    actions.sort(key=lambda a: (-a.prior, -a.immediate_gain, -len(a.group), a.factor))
    return actions[: max(1, min(width, len(actions)))]


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
    if action.linear:
        compute = _linear_factor_resource(action.factor, live_factor_ancilla, action.affine_const)
        uncompute = _linear_factor_resource(action.factor, live_factor_ancilla, action.affine_const)
    else:
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


def root_beam_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    neural_scorer=None,
    root_width: int | None = None,
) -> Plan:
    """Evaluate several root factor choices, then use ordinary greedy subplans.

    This is a bounded-discrepancy variant of ``greedy_plan``.  It keeps the
    recursive subproblems cheap while correcting the most expensive failure mode
    seen on high-dimensional random ANF instances: a locally plausible first
    factor can dominate the rest of the plan.
    """
    best = direct_plan(terms, prefix_len, live_factor_ancilla, config)
    actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config, neural_scorer)
    if not actions:
        return best
    width = root_width if root_width is not None else max(2, config.candidate_top_k)
    memo: dict[tuple[frozenset[int], int, int], Plan] = {}
    child_config = replace(config, greedy_eval_limit=1)
    for action in actions[: max(1, min(width, len(actions)))]:
        group = greedy_plan(
            action.residuals,
            prefix_len + 1,
            live_factor_ancilla + 1,
            child_config,
            neural_scorer,
            memo,
        )
        rest = greedy_plan(
            action.rest,
            prefix_len,
            live_factor_ancilla,
            child_config,
            neural_scorer,
            memo,
        )
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan("factor", terms, cost, factor=action.factor, group=group, rest=rest)
        if plan.score(config.weights) < best.score(config.weights):
            best = plan
    return best


def root_child_beam_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    neural_scorer=None,
    root_width: int | None = None,
    root_refine_width: int = 2,
    child_width: int = 2,
) -> Plan:
    """Refine a few root choices with one bounded child-level root beam.

    This is intentionally baseline-preserving: it first computes the ordinary
    root beam, then tries a very small second discrepancy level under the first
    few root actions.  It gives high-dimensional Resource-NMCTS a deeper search
    candidate without turning every recursive subproblem into a broad beam.
    """
    best = root_beam_plan(
        terms,
        prefix_len,
        live_factor_ancilla,
        config,
        neural_scorer,
        root_width=root_width,
    )
    actions = candidate_actions(terms, prefix_len, live_factor_ancilla, config, neural_scorer)
    if not actions:
        return best
    best_score = best.score(config.weights)
    child_config = replace(config, greedy_eval_limit=1)
    width = root_width if root_width is not None else max(2, config.candidate_top_k)
    refine = max(1, min(root_refine_width, width, len(actions)))
    for action in actions[:refine]:
        group = root_beam_plan(
            action.residuals,
            prefix_len + 1,
            live_factor_ancilla + 1,
            child_config,
            neural_scorer,
            root_width=child_width,
        )
        rest = root_beam_plan(
            action.rest,
            prefix_len,
            live_factor_ancilla,
            child_config,
            neural_scorer,
            root_width=child_width,
        )
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan("factor", terms, cost, factor=action.factor, group=group, rest=rest)
        score = plan.score(config.weights)
        if score < best_score:
            best = plan
            best_score = score
    return best


def linear_pair_beam_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    action_width: int = 4,
    recursive_depth: int = 0,
    max_linear_width: int = 2,
    neural_scorer=None,
    rest_greedy_term_limit: int | None = None,
    use_root_child_baseline: bool = True,
    root_neural_only: bool = False,
    boolean_ring: bool = False,
) -> Plan:
    """Try CNOT-only pairwise XOR factors above cheap subplans.

    The plan is baseline-preserving against ``root_child_beam_plan``.  It adds
    a cheap linear factor candidate for high-dimensional random ANFs where
    monomial common factors miss repeated pair structure.  ``recursive_depth``
    enables bounded extra linear-factor layers in both the selected quotient and
    the remaining terms; the default keeps the historical one-layer result
    unchanged.
    """
    baseline_scorer = None if root_neural_only else neural_scorer
    child_scorer = None if root_neural_only else neural_scorer
    if use_root_child_baseline:
        best = root_child_beam_plan(terms, prefix_len, live_factor_ancilla, config, neural_scorer=baseline_scorer)
    else:
        best = root_beam_plan(terms, prefix_len, live_factor_ancilla, config, neural_scorer=baseline_scorer)
    best_score = best.score(config.weights)
    action_fn = boolean_linear_factor_actions if boolean_ring else linear_factor_actions
    actions = action_fn(
        terms,
        prefix_len,
        live_factor_ancilla,
        config,
        action_width=action_width,
        max_linear_width=max_linear_width,
        neural_scorer=neural_scorer,
    )
    if not actions:
        return best
    child_config = replace(config, greedy_eval_limit=1)
    memo: dict[tuple[frozenset[int], int, int], Plan] = {}
    for action in actions:
        if recursive_depth > 0 and live_factor_ancilla + 1 < config.max_factor_ancilla:
            group = linear_pair_beam_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                child_config,
                action_width=max(2, action_width - 1),
                recursive_depth=recursive_depth - 1,
                max_linear_width=max_linear_width,
                neural_scorer=child_scorer,
                rest_greedy_term_limit=rest_greedy_term_limit,
                use_root_child_baseline=use_root_child_baseline,
                boolean_ring=boolean_ring,
            )
        else:
            group = greedy_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                child_config,
                child_scorer,
                memo,
            )
        if recursive_depth > 0 and len(terms) <= LINEAR_REST_RECURSE_TERM_LIMIT:
            rest = linear_pair_beam_plan(
                action.rest,
                prefix_len,
                live_factor_ancilla,
                child_config,
                action_width=max(2, action_width - 1),
                recursive_depth=recursive_depth - 1,
                max_linear_width=max_linear_width,
                neural_scorer=child_scorer,
                rest_greedy_term_limit=rest_greedy_term_limit,
                use_root_child_baseline=use_root_child_baseline,
                boolean_ring=boolean_ring,
            )
        elif rest_greedy_term_limit is not None and len(action.rest) > rest_greedy_term_limit:
            rest = direct_plan(action.rest, prefix_len, live_factor_ancilla, child_config)
        else:
            rest = greedy_plan(action.rest, prefix_len, live_factor_ancilla, child_config, child_scorer, memo)
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan(
            "linear_factor",
            terms,
            cost,
            factor=action.factor,
            group=group,
            rest=rest,
            affine_const=action.affine_const,
        )
        score = plan.score(config.weights)
        if score < best_score:
            best = plan
            best_score = score
    return best


def linear_pair_screen_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    action_width: int = 4,
    max_linear_width: int = 2,
    recursive_depth: int = 0,
    neural_scorer=None,
    boolean_ring: bool = False,
) -> Plan:
    """Screened linear-factor plan with a direct baseline.

    This variant is intended for high-dimensional pressure tests where the
    root-beam baseline and recursive greedy children dominate runtime.  It is
    baseline-preserving against direct synthesis only: each candidate is scored
    against a direct plan.  ``recursive_depth`` enables bounded repeated
    screening on quotient/rest subproblems without opening an FPRM beam tail.
    Broader portfolios still compare the returned candidate against stronger
    root-beam/linear-pair plans when those are affordable.
    """
    best = direct_plan(terms, prefix_len, live_factor_ancilla, config)
    best_score = best.score(config.weights)
    action_fn = boolean_linear_factor_actions if boolean_ring else linear_factor_actions
    actions = action_fn(
        terms,
        prefix_len,
        live_factor_ancilla,
        config,
        action_width=action_width,
        max_linear_width=max_linear_width,
        neural_scorer=neural_scorer,
    )
    for action in actions:
        next_width = max(2, action_width - 1)
        if recursive_depth > 0 and live_factor_ancilla + 1 < config.max_factor_ancilla:
            group = linear_pair_screen_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                config,
                action_width=next_width,
                max_linear_width=max_linear_width,
                recursive_depth=recursive_depth - 1,
                neural_scorer=neural_scorer,
                boolean_ring=boolean_ring,
            )
        else:
            group = direct_plan(action.residuals, prefix_len + 1, live_factor_ancilla + 1, config)
        if recursive_depth > 0 and action.rest and len(action.rest) < len(terms):
            rest = linear_pair_screen_plan(
                action.rest,
                prefix_len,
                live_factor_ancilla,
                config,
                action_width=next_width,
                max_linear_width=max_linear_width,
                recursive_depth=recursive_depth - 1,
                neural_scorer=neural_scorer,
                boolean_ring=boolean_ring,
            )
        else:
            rest = direct_plan(action.rest, prefix_len, live_factor_ancilla, config)
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan(
            "linear_factor",
            terms,
            cost,
            factor=action.factor,
            group=group,
            rest=rest,
            affine_const=action.affine_const,
        )
        score = plan.score(config.weights)
        if score < best_score:
            best = plan
            best_score = score
    return best


def affine_linear_pair_beam_plan(
    terms: frozenset[int],
    prefix_len: int = 0,
    live_factor_ancilla: int = 0,
    config: SearchConfig = SearchConfig(),
    action_width: int = 4,
    recursive_depth: int = 0,
    max_linear_width: int = 2,
    neural_scorer=None,
) -> Plan:
    """Try local affine-linear factors above the linear-pair baseline."""
    best = linear_pair_beam_plan(
        terms,
        prefix_len,
        live_factor_ancilla,
        config,
        action_width=action_width,
        recursive_depth=0,
        max_linear_width=max_linear_width,
        neural_scorer=neural_scorer,
    )
    best_score = best.score(config.weights)
    actions = affine_linear_factor_actions(
        terms,
        prefix_len,
        live_factor_ancilla,
        config,
        action_width=action_width,
        max_linear_width=max_linear_width,
        neural_scorer=neural_scorer,
    )
    if not actions:
        return best
    child_config = replace(config, greedy_eval_limit=1)
    memo: dict[tuple[frozenset[int], int, int], Plan] = {}
    for action in actions:
        if recursive_depth > 0 and live_factor_ancilla + 1 < config.max_factor_ancilla:
            group = affine_linear_pair_beam_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                child_config,
                action_width=max(2, action_width - 1),
                recursive_depth=recursive_depth - 1,
                max_linear_width=max_linear_width,
                neural_scorer=neural_scorer,
            )
        else:
            group = greedy_plan(
                action.residuals,
                prefix_len + 1,
                live_factor_ancilla + 1,
                child_config,
                neural_scorer,
                memo,
            )
        if recursive_depth > 0 and len(terms) <= LINEAR_REST_RECURSE_TERM_LIMIT:
            rest = affine_linear_pair_beam_plan(
                action.rest,
                prefix_len,
                live_factor_ancilla,
                child_config,
                action_width=max(2, action_width - 1),
                recursive_depth=recursive_depth - 1,
                max_linear_width=max_linear_width,
                neural_scorer=neural_scorer,
            )
        else:
            rest = greedy_plan(action.rest, prefix_len, live_factor_ancilla, child_config, neural_scorer, memo)
        cost = factor_cost(action, group, rest, live_factor_ancilla, config)
        plan = Plan(
            "linear_factor",
            terms,
            cost,
            factor=action.factor,
            group=group,
            rest=rest,
            affine_const=action.affine_const,
        )
        score = plan.score(config.weights)
        if score < best_score:
            best = plan
            best_score = score
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
        if node.kind == "linear_factor":
            if node.affine_const:
                circ.add_x(anc)
            for control in controls:
                circ.add_cnot(control, anc)
        else:
            circ.add_mct(controls, anc)
        rec(node.group, prefix_controls + [anc])
        if node.kind == "linear_factor":
            for control in reversed(controls):
                circ.add_cnot(control, anc)
            if node.affine_const:
                circ.add_x(anc)
        else:
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


@lru_cache(maxsize=8)
def _parallel_input_masks(n: int) -> tuple[int, tuple[int, ...]]:
    assignments = 1 << n
    full_mask = (1 << assignments) - 1
    masks = []
    for bit in range(n):
        run = 1 << bit
        unit_width = run << 1
        mask = ((1 << run) - 1) << run
        width = unit_width
        while width < assignments:
            mask |= mask << width
            width <<= 1
        masks.append(mask & full_mask)
    return full_mask, tuple(masks)


def verify_oracle(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    n = bf.n
    if circ.n_qubits <= n:
        return False
    full_mask, input_masks = _parallel_input_masks(n)
    bits = list(input_masks) + [0] * (circ.n_qubits - n)
    for gate in circ.gates:
        target = int(gate.target)
        if target < 0 or target >= circ.n_qubits:
            return False
        if gate.type == "X":
            bits[target] ^= full_mask
        elif gate.type == "CNOT":
            if len(gate.controls) != 1:
                return False
            control = int(gate.controls[0])
            if control < 0 or control >= circ.n_qubits:
                return False
            bits[target] ^= bits[control]
        elif gate.type == "MCT":
            controls = [int(control) for control in gate.controls]
            if any(control < 0 or control >= circ.n_qubits for control in controls):
                return False
            active = full_mask
            for control in controls:
                active &= bits[control]
            bits[target] ^= active
        else:
            return False
    if bits[n] != (bf.truth_table & full_mask):
        return False
    if bits[:n] != list(input_masks):
        return False
    return all(value == 0 for value in bits[n + 1 :])


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
