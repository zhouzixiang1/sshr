"""Conflict-aware fixed-budget scheduling for isolated E6 shared actions.

The scheduler keeps E6 outside the scalar synthesis path.  Real shared-action
variables are augmented with ``B`` zero-utility dummy variables and the QUBO
enforces exactly ``B_eff=min(B, K_real)`` selected variables.  Consequently a
solver may choose *up to* ``B_eff`` real actions without violating a fixed
cardinality quantum optimization contract: unused slots are represented by
dummy selections.

Every solver uses the same real-action objective

    F(S) = sum(i in S) utility_i
           - gamma * sum(i < j in S) redundancy_ij,

subject to disjoint output/ANF footprints.  Greedy, exhaustive exact, and the
existing dependency-light direct QAOA backend are exposed.  Small QUBOs can be
audited across all ``2**K_augmented`` assignments.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass
from numbers import Integral
from typing import Iterable, Mapping, Sequence

from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    SharedAction,
    SharedOracleProgram,
    action_footprint,
    action_polynomial_terms,
    actions_conflict,
)
from src.bool_func import mct_cost
from src.search.qaoa_scheduler import run_qaoa


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite real number")
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite real number") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be a positive integer")
    converted = int(value)
    if converted <= 0:
        raise ValueError(f"{name} must be > 0")
    return converted


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be a non-negative integer")
    converted = int(value)
    if converted < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return converted


def _jaccard(left: frozenset[object], right: frozenset[object]) -> float:
    union = left | right
    return 0.0 if not union else len(left & right) / len(union)


@dataclass(frozen=True)
class SharedUtilityWeights:
    """Abstract logical-MCT proxy weights used only by the E6 MVP.

    The T/CNOT/depth numbers are deterministic logical-MCT cost proxies, not a
    hardware compilation.  In particular, the implicit workspace assumed by
    any MCT decomposition is deliberately excluded.  ``ancilla`` is applied
    once to the whole emitted program's reusable explicit-workspace peak, not
    once per candidate action.
    """

    t: float = 1.0
    cnot: float = 0.04
    depth: float = 0.015
    gates: float = 0.01
    ancilla: float = 2.0

    def __post_init__(self) -> None:
        for name in ("t", "cnot", "depth", "gates", "ancilla"):
            value = _finite(getattr(self, name), name)
            if value < 0.0:
                raise ValueError(f"{name} weight must be >= 0")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class _ToggleCost:
    t: int
    cnot: int
    depth: int
    gates: int

    def scaled(self, weights: SharedUtilityWeights) -> float:
        return float(
            weights.t * self.t
            + weights.cnot * self.cnot
            + weights.depth * self.depth
            + weights.gates * self.gates
        )

    def __add__(self, other: "_ToggleCost") -> "_ToggleCost":
        return _ToggleCost(
            self.t + other.t,
            self.cnot + other.cnot,
            self.depth + other.depth,
            self.gates + other.gates,
        )

    def times(self, count: int) -> "_ToggleCost":
        return _ToggleCost(
            self.t * count,
            self.cnot * count,
            self.depth * count,
            self.gates * count,
        )


_X_COST = _ToggleCost(t=0, cnot=0, depth=1, gates=1)
_CNOT_COST = _ToggleCost(t=0, cnot=1, depth=1, gates=1)


def _monomial_toggle_cost(monomial: int) -> _ToggleCost:
    degree = int(monomial).bit_count()
    if degree == 0:
        return _X_COST
    if degree == 1:
        return _CNOT_COST
    cost = mct_cost(degree)
    return _ToggleCost(
        t=int(cost["T"]),
        cnot=int(cost["CNOT"]),
        depth=max(1, int(cost["CNOT"])),
        gates=1,
    )


@dataclass(frozen=True)
class SharedUtilityBreakdown:
    action_kind: str
    fanout: int
    expanded_term_count: int
    direct_t: int
    direct_cnot: int
    direct_depth: int
    direct_gates: int
    shared_t: int
    shared_cnot: int
    shared_depth: int
    shared_gates: int
    direct_score: float
    shared_score: float
    explicit_ancilla: int
    explicit_ancilla_charge: float
    utility: float
    metric: str = "abstract_logical_mct_proxy_not_hardware"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def shared_action_utility_breakdown(
    action: SharedAction,
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> SharedUtilityBreakdown:
    """Compare direct per-output toggles with compute--fanout--uncompute."""

    terms = action_polynomial_terms(action)
    direct_one = _ToggleCost(0, 0, 0, 0)
    for term in terms:
        direct_one = direct_one + _monomial_toggle_cost(term)
    direct = direct_one.times(len(action.targets))

    if isinstance(action, MonomialSharedAction):
        compute = _monomial_toggle_cost(action.monomial)
        shared = compute.times(2) + _CNOT_COST.times(len(action.targets))
    elif isinstance(action, SemiAffineSharedAction):
        affine_operations = action.affine_mask.bit_count() + int(action.affine_const)
        affine_cost = _CNOT_COST.times(action.affine_mask.bit_count())
        if action.affine_const:
            affine_cost = affine_cost + _X_COST
        # The computed affine wire is one additional control.
        product_cost = _monomial_toggle_cost(
            action.base_monomial | (1 << action.base_monomial.bit_length())
        )
        # The synthetic high bit above is used only to count one extra control;
        # it is not a physical input variable or an ANF term.
        assert product_cost.gates == 1
        shared = (
            affine_cost.times(2)
            + product_cost.times(2)
            + _CNOT_COST.times(len(action.targets))
        )
        assert affine_operations >= 1
    else:  # pragma: no cover - closed SharedAction union
        raise TypeError("unsupported E6 shared-action type")

    direct_score = direct.scaled(weights)
    shared_score = shared.scaled(weights)
    # The same one/two explicit wires are reused by all selected blocks.  A
    # per-action charge would double count the program peak, so action utility
    # compares operations only.  ``program_resource_summary`` applies the peak
    # charge exactly once after emission.
    ancilla_charge = 0.0
    utility = direct_score - shared_score
    return SharedUtilityBreakdown(
        action_kind=action.kind,
        fanout=len(action.targets),
        expanded_term_count=len(terms),
        direct_t=direct.t,
        direct_cnot=direct.cnot,
        direct_depth=direct.depth,
        direct_gates=direct.gates,
        shared_t=shared.t,
        shared_cnot=shared.cnot,
        shared_depth=shared.depth,
        shared_gates=shared.gates,
        direct_score=direct_score,
        shared_score=shared_score,
        explicit_ancilla=action.ancilla_required,
        explicit_ancilla_charge=ancilla_charge,
        utility=float(utility),
    )


@dataclass(frozen=True)
class ProgramResourceSummary:
    """Whole-program abstract logical resource account for an emitted oracle."""

    logical_x: int
    logical_cnot: int
    logical_mct: int
    abstract_t: int
    abstract_cnot: int
    abstract_depth: int
    logical_gates: int
    explicit_workspace_peak: int
    explicit_workspace_limit: int
    abstract_operation_score: float
    explicit_workspace_peak_charge: float
    total_abstract_score: float
    resource_layer: str = "abstract_logical_X_CNOT_MCT"
    mct_decomposition_implicit_ancillas_included: bool = False
    exact_hardware_resource_claim: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def program_resource_summary(
    program: SharedOracleProgram,
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> ProgramResourceSummary:
    """Report explicit reusable workspace at whole-program peak granularity."""

    logical_x = logical_cnot = logical_mct = 0
    abstract = _ToggleCost(0, 0, 0, 0)
    for gate in program.circuit.gates:
        if gate.type == "X":
            logical_x += 1
            abstract = abstract + _X_COST
        elif gate.type == "CNOT":
            logical_cnot += 1
            abstract = abstract + _CNOT_COST
        elif gate.type == "MCT":
            logical_mct += 1
            abstract = abstract + _monomial_toggle_cost(
                sum(1 << control for control in gate.controls)
            )
        else:  # pragma: no cover - emitter has a closed logical gate set
            raise ValueError(f"unsupported logical gate in E6 program: {gate.type}")
    operation_score = abstract.scaled(weights)
    workspace_charge = weights.ancilla * program.explicit_workspace_peak
    return ProgramResourceSummary(
        logical_x=logical_x,
        logical_cnot=logical_cnot,
        logical_mct=logical_mct,
        abstract_t=abstract.t,
        abstract_cnot=abstract.cnot,
        abstract_depth=abstract.depth,
        logical_gates=abstract.gates,
        explicit_workspace_peak=program.explicit_workspace_peak,
        explicit_workspace_limit=2,
        abstract_operation_score=operation_score,
        explicit_workspace_peak_charge=workspace_charge,
        total_abstract_score=operation_score + workspace_charge,
    )


def shared_action_utility(
    action: SharedAction,
    *,
    weights: SharedUtilityWeights = SharedUtilityWeights(),
) -> float:
    return shared_action_utility_breakdown(action, weights=weights).utility


def action_conflict_matrix(
    actions: Sequence[SharedAction] | Iterable[SharedAction],
) -> tuple[tuple[bool, ...], ...]:
    actions = tuple(actions)
    return tuple(
        tuple(
            left != right and actions_conflict(action, actions[right])
            for right in range(len(actions))
        )
        for left, action in enumerate(actions)
    )


def action_redundancy_matrix(
    actions: Sequence[SharedAction] | Iterable[SharedAction],
    *,
    alpha: float = 0.7,
) -> tuple[tuple[float, ...], ...]:
    """Blend polynomial and target-set Jaccard redundancy.

    Footprint conflicts are kept in a separate hard-constraint matrix.  This
    soft measure can therefore penalise two non-conflicting actions that still
    request very similar computations or fanout patterns.
    """

    actions = tuple(actions)
    blend = _finite(alpha, "alpha")
    if not 0.0 <= blend <= 1.0:
        raise ValueError("alpha must lie in [0, 1]")
    rows = [[0.0] * len(actions) for _ in actions]
    for left in range(len(actions)):
        for right in range(left + 1, len(actions)):
            polynomial = _jaccard(
                frozenset(action_polynomial_terms(actions[left])),
                frozenset(action_polynomial_terms(actions[right])),
            )
            targets = _jaccard(
                frozenset(actions[left].targets), frozenset(actions[right].targets)
            )
            value = blend * polynomial + (1.0 - blend) * targets
            rows[left][right] = value
            rows[right][left] = value
    return tuple(tuple(row) for row in rows)


def _validate_square_float_matrix(
    matrix: Sequence[Sequence[float]],
    size: int,
    name: str,
) -> tuple[tuple[float, ...], ...]:
    rows = tuple(tuple(row) for row in matrix)
    if len(rows) != size or any(len(row) != size for row in rows):
        raise ValueError(f"{name} must be a square {size} x {size} matrix")
    converted = tuple(
        tuple(_finite(value, f"{name}[{i}][{j}]") for j, value in enumerate(row))
        for i, row in enumerate(rows)
    )
    for i in range(size):
        if not math.isclose(
            converted[i][i], 0.0, rel_tol=0.0, abs_tol=1e-12
        ):
            raise ValueError(f"{name} diagonal must be zero")
        for j in range(i + 1, size):
            if converted[i][j] < 0.0 or converted[j][i] < 0.0:
                raise ValueError(f"{name} entries must be non-negative")
            if not math.isclose(
                converted[i][j],
                converted[j][i],
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(f"{name} must be symmetric")
    return converted


@dataclass(frozen=True)
class SharedSchedulingProblem:
    actions: tuple[SharedAction, ...]
    utilities: tuple[float, ...]
    redundancy: tuple[tuple[float, ...], ...]
    conflicts: tuple[tuple[bool, ...], ...]
    redundancy_weight: float
    budget_requested: int
    budget_effective: int

    @property
    def real_candidate_count(self) -> int:
        return len(self.actions)

    def is_conflict_free(self, selected: Sequence[int]) -> bool:
        return not any(
            self.conflicts[left][right]
            for offset, left in enumerate(selected)
            for right in selected[offset + 1 :]
        )

    def objective(self, selected: Sequence[int]) -> float:
        selected = tuple(sorted(selected))
        return float(
            sum(self.utilities[index] for index in selected)
            - self.redundancy_weight
            * sum(
                self.redundancy[left][right]
                for offset, left in enumerate(selected)
                for right in selected[offset + 1 :]
            )
        )


def build_shared_scheduling_problem(
    actions: Sequence[SharedAction] | Iterable[SharedAction],
    budget_requested: int,
    *,
    utilities: Sequence[float] | Iterable[float] | None = None,
    utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
    redundancy: Sequence[Sequence[float]] | None = None,
    redundancy_weight: float = 0.25,
    redundancy_alpha: float = 0.7,
) -> SharedSchedulingProblem:
    actions = tuple(actions)
    budget = _positive_integer(budget_requested, "budget_requested")
    if utilities is None:
        utility_values = tuple(
            shared_action_utility(action, weights=utility_weights) for action in actions
        )
    else:
        utility_values = tuple(
            _finite(value, f"utilities[{index}]")
            for index, value in enumerate(utilities)
        )
    if len(utility_values) != len(actions):
        raise ValueError("utilities must have the same length as actions")

    gamma = _finite(redundancy_weight, "redundancy_weight")
    if gamma < 0.0:
        raise ValueError("redundancy_weight must be >= 0")
    if redundancy is None:
        redundancy_values = action_redundancy_matrix(actions, alpha=redundancy_alpha)
    else:
        redundancy_values = _validate_square_float_matrix(
            redundancy, len(actions), "redundancy"
        )
    conflicts = action_conflict_matrix(actions)
    return SharedSchedulingProblem(
        actions=actions,
        utilities=utility_values,
        redundancy=redundancy_values,
        conflicts=conflicts,
        redundancy_weight=gamma,
        budget_requested=budget,
        budget_effective=min(budget, len(actions)),
    )


def _validate_bits(bits: Sequence[int], size: int) -> tuple[int, ...]:
    bits = tuple(bits)
    if len(bits) != size:
        raise ValueError(f"bitstring must have length {size}")
    converted: list[int] = []
    for index, bit in enumerate(bits):
        if isinstance(bit, bool):
            bit = int(bit)
        if not isinstance(bit, Integral) or int(bit) not in (0, 1):
            raise ValueError(f"bitstring[{index}] must be binary")
        converted.append(int(bit))
    return tuple(converted)


@dataclass(frozen=True)
class DummyFixedCardinalityQUBO:
    """Expanded QUBO with real action variables followed by dummy variables."""

    real_candidate_count: int
    dummy_count: int
    budget_effective: int
    utilities: tuple[float, ...]
    redundancy: tuple[tuple[float, ...], ...]
    conflicts: tuple[tuple[bool, ...], ...]
    redundancy_weight: float
    objective_magnitude_bound: float
    rho_strict_lower_bound: float
    conflict_penalty_strict_lower_bound: float
    rho: float
    conflict_penalty: float
    linear: tuple[float, ...]
    quadratic: tuple[tuple[int, int, float], ...]
    constant: float

    @property
    def variable_count(self) -> int:
        return self.real_candidate_count + self.dummy_count

    def selected_real(self, bits: Sequence[int]) -> tuple[int, ...]:
        normalized = _validate_bits(bits, self.variable_count)
        return tuple(
            index for index in range(self.real_candidate_count) if normalized[index]
        )

    def conflict_count(self, bits: Sequence[int]) -> int:
        selected = self.selected_real(bits)
        return sum(
            self.conflicts[left][right]
            for offset, left in enumerate(selected)
            for right in selected[offset + 1 :]
        )

    def objective(self, bits: Sequence[int]) -> float:
        selected = self.selected_real(bits)
        return float(
            sum(self.utilities[index] for index in selected)
            - self.redundancy_weight
            * sum(
                self.redundancy[left][right]
                for offset, left in enumerate(selected)
                for right in selected[offset + 1 :]
            )
        )

    def identity_energy(self, bits: Sequence[int]) -> float:
        normalized = _validate_bits(bits, self.variable_count)
        return float(
            -self.objective(normalized)
            + self.conflict_penalty * self.conflict_count(normalized)
            + self.rho * (sum(normalized) - self.budget_effective) ** 2
        )

    def energy(self, bits: Sequence[int]) -> float:
        normalized = _validate_bits(bits, self.variable_count)
        return float(
            self.constant
            + sum(value * normalized[index] for index, value in enumerate(self.linear))
            + sum(
                value * normalized[left] * normalized[right]
                for left, right, value in self.quadratic
            )
        )

    def phase_energy(self, bits: Sequence[int]) -> float:
        """Energy actually passed to QAOA (the constant offset is omitted)."""

        return self.energy(bits) - self.constant

    def is_feasible(self, bits: Sequence[int]) -> bool:
        normalized = _validate_bits(bits, self.variable_count)
        return (
            sum(normalized) == self.budget_effective
            and self.conflict_count(normalized) == 0
        )

    def qaoa_coefficients(
        self,
    ) -> tuple[dict[int, float], dict[tuple[int, int], float]]:
        return (
            {index: value for index, value in enumerate(self.linear)},
            {(left, right): value for left, right, value in self.quadratic},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "real_candidate_count": self.real_candidate_count,
            "dummy_count": self.dummy_count,
            "variable_count": self.variable_count,
            "budget_effective": self.budget_effective,
            "utilities": list(self.utilities),
            "redundancy": [list(row) for row in self.redundancy],
            "conflicts": [list(row) for row in self.conflicts],
            "redundancy_weight": self.redundancy_weight,
            "objective_magnitude_bound": self.objective_magnitude_bound,
            "rho_strict_lower_bound": self.rho_strict_lower_bound,
            "conflict_penalty_strict_lower_bound": (
                self.conflict_penalty_strict_lower_bound
            ),
            "rho": self.rho,
            "conflict_penalty": self.conflict_penalty,
            "linear": list(self.linear),
            "quadratic": [list(term) for term in self.quadratic],
            "constant": self.constant,
        }


def build_dummy_fixed_cardinality_qubo(
    problem: SharedSchedulingProblem,
    *,
    rho: float | None = None,
    conflict_penalty: float | None = None,
) -> DummyFixedCardinalityQUBO:
    """Expand ``-F + conflict + rho*(sum(real,dummy)-B)^2``."""

    k = problem.real_candidate_count
    budget = problem.budget_effective
    dummy_count = budget
    variable_count = k + dummy_count
    objective_bound = float(
        sum(abs(value) for value in problem.utilities)
        + problem.redundancy_weight
        * sum(
            problem.redundancy[left][right]
            for left in range(k)
            for right in range(left + 1, k)
        )
    )
    # For every real subset, |F(S)| <= objective_bound.  The all-dummy
    # cardinality-feasible assignment has energy zero.  Therefore rho > bound
    # makes every cardinality violation strictly positive, and conflict >
    # bound makes every conflicting cardinality-feasible assignment strictly
    # positive.  This is conservative but analytic and independent of an
    # exhaustive audit.
    default_margin = max(1.0, objective_bound * 1e-9)
    cardinality_penalty = (
        objective_bound + default_margin if rho is None else _finite(rho, "rho")
    )
    pair_conflict_penalty = (
        objective_bound + default_margin
        if conflict_penalty is None
        else _finite(conflict_penalty, "conflict_penalty")
    )
    if cardinality_penalty <= objective_bound:
        raise ValueError(
            "rho override is analytically insufficient: require rho > "
            f"{objective_bound:.17g}, got {cardinality_penalty:.17g}"
        )
    if pair_conflict_penalty <= objective_bound:
        raise ValueError(
            "conflict_penalty override is analytically insufficient: require "
            f"conflict_penalty > {objective_bound:.17g}, got "
            f"{pair_conflict_penalty:.17g}"
        )

    linear = tuple(
        (
            -problem.utilities[index]
            if index < k
            else 0.0
        )
        + cardinality_penalty * (1 - 2 * budget)
        for index in range(variable_count)
    )
    quadratic = tuple(
        (
            left,
            right,
            2.0 * cardinality_penalty
            + (
                problem.redundancy_weight * problem.redundancy[left][right]
                + pair_conflict_penalty * int(problem.conflicts[left][right])
                if left < k and right < k
                else 0.0
            ),
        )
        for left in range(variable_count)
        for right in range(left + 1, variable_count)
    )
    return DummyFixedCardinalityQUBO(
        real_candidate_count=k,
        dummy_count=dummy_count,
        budget_effective=budget,
        utilities=problem.utilities,
        redundancy=problem.redundancy,
        conflicts=problem.conflicts,
        redundancy_weight=problem.redundancy_weight,
        objective_magnitude_bound=objective_bound,
        rho_strict_lower_bound=objective_bound,
        conflict_penalty_strict_lower_bound=objective_bound,
        rho=cardinality_penalty,
        conflict_penalty=pair_conflict_penalty,
        linear=linear,
        quadratic=quadratic,
        constant=cardinality_penalty * budget * budget,
    )


@dataclass(frozen=True)
class QUBOAuditRecord:
    bitstring: tuple[int, ...]
    cardinality: int
    selected_real: tuple[int, ...]
    dummy_selected: int
    conflicts: int
    feasible: bool
    objective: float
    identity_energy: float
    polynomial_energy: float
    identity_error: float
    phase_energy: float
    backend_coefficient_energy: float
    phase_identity_error: float
    constant_offset_error: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class QUBOAuditDiagnostics:
    variable_count: int
    real_candidate_count: int
    dummy_count: int
    budget_effective: int
    total_bitstrings: int
    expected_bitstrings: int
    feasible_bitstrings: int
    max_identity_error: float
    energy_identity_holds: bool
    max_phase_identity_error: float
    phase_energy_identity_holds: bool
    max_constant_offset_error: float
    phase_constant_offset_holds: bool
    analytic_penalty_bounds_hold: bool
    feasible_optimal_real_selections: tuple[tuple[int, ...], ...]
    global_minimum_bitstrings: tuple[tuple[int, ...], ...]
    all_global_minima_feasible: bool
    global_minimum_real_selections: tuple[tuple[int, ...], ...]
    exact_selection_matches_global_minima: bool
    penalty_sufficient: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class QUBOAuditResult:
    model: DummyFixedCardinalityQUBO
    records: tuple[QUBOAuditRecord, ...]
    diagnostics: QUBOAuditDiagnostics

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "diagnostics": self.diagnostics.to_dict(),
        }


def audit_dummy_fixed_cardinality_qubo(
    model: DummyFixedCardinalityQUBO,
    *,
    max_variables: int = 16,
    tolerance: float = 1e-9,
) -> QUBOAuditResult:
    """Audit all ``2**K`` augmented bitstrings and the exact-selection identity."""

    maximum = _positive_integer(max_variables, "max_variables")
    if model.variable_count > maximum:
        raise ValueError(
            "exhaustive QUBO audit refused: "
            f"K={model.variable_count} exceeds max_variables={maximum}"
        )
    absolute_tolerance = _finite(tolerance, "tolerance")
    if absolute_tolerance < 0.0:
        raise ValueError("tolerance must be >= 0")

    linear, quadratic = model.qaoa_coefficients()
    records: list[QUBOAuditRecord] = []
    for bits in itertools.product((0, 1), repeat=model.variable_count):
        selected = model.selected_real(bits)
        conflicts = model.conflict_count(bits)
        identity = model.identity_energy(bits)
        polynomial = model.energy(bits)
        phase = model.phase_energy(bits)
        backend_phase = float(
            sum(linear[index] * bit for index, bit in enumerate(bits))
            + sum(
                value * bits[left] * bits[right]
                for (left, right), value in quadratic.items()
            )
        )
        records.append(
            QUBOAuditRecord(
                bitstring=bits,
                cardinality=sum(bits),
                selected_real=selected,
                dummy_selected=sum(bits[model.real_candidate_count :]),
                conflicts=conflicts,
                feasible=model.is_feasible(bits),
                objective=model.objective(bits),
                identity_energy=identity,
                polynomial_energy=polynomial,
                identity_error=abs(identity - polynomial),
                phase_energy=phase,
                backend_coefficient_energy=backend_phase,
                phase_identity_error=abs(phase - backend_phase),
                constant_offset_error=abs(polynomial - (phase + model.constant)),
            )
        )

    feasible = [record for record in records if record.feasible]
    if not feasible:
        raise RuntimeError("dummy construction failed to provide a feasible assignment")
    best_objective = max(record.objective for record in feasible)
    feasible_optima = tuple(
        sorted(
            {
                record.selected_real
                for record in feasible
                if math.isclose(
                    record.objective,
                    best_objective,
                    rel_tol=0.0,
                    abs_tol=absolute_tolerance,
                )
            }
        )
    )
    minimum_energy = min(record.polynomial_energy for record in records)
    global_minimum_records = [
        record
        for record in records
        if math.isclose(
            record.polynomial_energy,
            minimum_energy,
            rel_tol=0.0,
            abs_tol=absolute_tolerance,
        )
    ]
    global_minimum_bitstrings = tuple(record.bitstring for record in global_minimum_records)
    global_real = tuple(sorted({record.selected_real for record in global_minimum_records}))
    max_error = max((record.identity_error for record in records), default=0.0)
    identity_holds = all(
        math.isclose(
            record.identity_energy,
            record.polynomial_energy,
            rel_tol=0.0,
            abs_tol=absolute_tolerance,
        )
        for record in records
    )
    max_phase_error = max((record.phase_identity_error for record in records), default=0.0)
    phase_identity_holds = all(
        math.isclose(
            record.phase_energy,
            record.backend_coefficient_energy,
            rel_tol=0.0,
            abs_tol=absolute_tolerance,
        )
        for record in records
    )
    max_constant_error = max(
        (record.constant_offset_error for record in records), default=0.0
    )
    constant_offset_holds = all(
        math.isclose(
            record.polynomial_energy,
            record.phase_energy + model.constant,
            rel_tol=0.0,
            abs_tol=absolute_tolerance,
        )
        for record in records
    )
    analytic_bounds_hold = (
        model.rho > model.rho_strict_lower_bound
        and model.conflict_penalty > model.conflict_penalty_strict_lower_bound
    )
    all_minima_feasible = all(record.feasible for record in global_minimum_records)
    exact_matches = all_minima_feasible and global_real == feasible_optima
    diagnostics = QUBOAuditDiagnostics(
        variable_count=model.variable_count,
        real_candidate_count=model.real_candidate_count,
        dummy_count=model.dummy_count,
        budget_effective=model.budget_effective,
        total_bitstrings=len(records),
        expected_bitstrings=1 << model.variable_count,
        feasible_bitstrings=len(feasible),
        max_identity_error=max_error,
        energy_identity_holds=identity_holds,
        max_phase_identity_error=max_phase_error,
        phase_energy_identity_holds=phase_identity_holds,
        max_constant_offset_error=max_constant_error,
        phase_constant_offset_holds=constant_offset_holds,
        analytic_penalty_bounds_hold=analytic_bounds_hold,
        feasible_optimal_real_selections=feasible_optima,
        global_minimum_bitstrings=global_minimum_bitstrings,
        all_global_minima_feasible=all_minima_feasible,
        global_minimum_real_selections=global_real,
        exact_selection_matches_global_minima=exact_matches,
        penalty_sufficient=(
            identity_holds
            and phase_identity_holds
            and constant_offset_holds
            and analytic_bounds_hold
            and exact_matches
        ),
    )
    return QUBOAuditResult(model=model, records=tuple(records), diagnostics=diagnostics)


def _exact_selected(problem: SharedSchedulingProblem) -> tuple[int, ...]:
    best: tuple[int, ...] = ()
    best_objective = 0.0
    for size in range(1, problem.budget_effective + 1):
        for subset in itertools.combinations(range(problem.real_candidate_count), size):
            if not problem.is_conflict_free(subset):
                continue
            objective = problem.objective(subset)
            if objective > best_objective + 1e-12:
                best = subset
                best_objective = objective
            elif math.isclose(
                objective, best_objective, rel_tol=0.0, abs_tol=1e-12
            ):
                # Dummies are preferred on a zero-gain tie, then the
                # lexicographically smallest real subset is deterministic.
                if len(subset) < len(best) or (len(subset) == len(best) and subset < best):
                    best = subset
    return best


def _greedy_selected(problem: SharedSchedulingProblem) -> tuple[int, ...]:
    selected: list[int] = []
    remaining = set(range(problem.real_candidate_count))
    while len(selected) < problem.budget_effective:
        best_index: int | None = None
        best_marginal = 0.0  # zero-utility dummy occupies non-positive slots
        for index in sorted(remaining):
            if any(problem.conflicts[index][prior] for prior in selected):
                continue
            marginal = problem.utilities[index] - problem.redundancy_weight * sum(
                problem.redundancy[index][prior] for prior in selected
            )
            if marginal > best_marginal + 1e-12:
                best_index = index
                best_marginal = marginal
        if best_index is None:
            break
        selected.append(best_index)
        remaining.remove(best_index)
    return tuple(sorted(selected))


def _augmented_bitstring(
    model: DummyFixedCardinalityQUBO,
    selected_real: Sequence[int],
) -> tuple[int, ...]:
    selected_set = set(selected_real)
    dummy_needed = model.budget_effective - len(selected_set)
    if dummy_needed < 0:
        raise ValueError("selected real actions exceed the effective budget")
    return tuple(
        int(index in selected_set) for index in range(model.real_candidate_count)
    ) + tuple(int(index < dummy_needed) for index in range(model.dummy_count))


def _decode_count_key(key: object, variable_count: int) -> tuple[int, ...]:
    if not isinstance(key, str) or len(key) != variable_count:
        raise ValueError(
            "QAOA count key must use x0..x(K-1) order with exactly "
            f"K={variable_count} binary characters"
        )
    if any(character not in "01" for character in key):
        raise ValueError("QAOA count key contains a non-binary character")
    return tuple(int(character) for character in key)


def _postselect_qaoa_counts(
    model: DummyFixedCardinalityQUBO,
    counts: Mapping[str, int],
    *,
    repair_bits: tuple[int, ...],
    expected_shots: int,
) -> tuple[tuple[int, ...], bool, dict[str, object]]:
    """Filter measured counts *after* a pure-QUBO phase-backend execution."""

    observed: list[tuple[tuple[int, ...], int]] = []
    for key, raw_count in counts.items():
        bits = _decode_count_key(key, model.variable_count)
        count = _positive_integer(raw_count, f"counts[{key!r}]")
        observed.append((bits, count))
    if not observed:
        raise RuntimeError("QAOA backend returned no sampled counts")

    feasible = [(bits, count) for bits, count in observed if model.is_feasible(bits)]
    selection_key = lambda item: (
        model.phase_energy(item[0]),
        -item[1],
        item[0],
    )
    source_bits, source_count = min(
        feasible if feasible else observed,
        key=selection_key,
    )
    if feasible:
        returned_bits = source_bits
        repaired = False
        selection_class = "direct_feasible_measured_qaoa_sample"
    else:
        if not model.is_feasible(repair_bits):
            raise RuntimeError("declared QAOA repair bitstring is not feasible")
        returned_bits = repair_bits
        repaired = True
        selection_class = "no_feasible_sample_exact_repair"

    total_shots = sum(count for _, count in observed)
    if total_shots != expected_shots:
        raise RuntimeError(
            f"QAOA counts sum to {total_shots}, expected {expected_shots} shots"
        )
    ledger = {
        "phase_backend_contract": "qubo_linear_quadratic_only_no_feasibility_oracle",
        "count_bit_order": "x0_to_xK_minus_1",
        "selection_rule": (
            "filter frozen-QUBO feasible measured counts, then minimise phase "
            "energy; ties use descending count then lexicographic bitstring"
        ),
        "selection_class": selection_class,
        "observed_bitstrings": len(observed),
        "feasible_observed_bitstrings": len(feasible),
        "feasible_observed_shots": sum(count for _, count in feasible),
        "total_shots": total_shots,
        "source_bitstring": list(source_bits),
        "source_count": source_count,
        "source_phase_energy": model.phase_energy(source_bits),
        "source_polynomial_energy": model.energy(source_bits),
        "returned_bitstring": list(returned_bits),
        "returned_phase_energy": model.phase_energy(returned_bits),
        "returned_polynomial_energy": model.energy(returned_bits),
        "returned_bitstring_was_measured": not repaired,
        "repair_applied": repaired,
        "repair_method": "classical_exact_feasible_projection" if repaired else None,
    }
    return returned_bits, repaired, ledger


@dataclass(frozen=True)
class SharedScheduleResult:
    selected_indices: tuple[int, ...]
    real_bitstring: tuple[int, ...]
    augmented_bitstring: tuple[int, ...]
    dummy_selected: int
    diagnostics: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_indices": list(self.selected_indices),
            "real_bitstring": list(self.real_bitstring),
            "augmented_bitstring": list(self.augmented_bitstring),
            "dummy_selected": self.dummy_selected,
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class SharedSchedulerConfig:
    method: str = "greedy"
    budget_requested: int = 2
    redundancy_weight: float = 0.25
    redundancy_alpha: float = 0.7
    qaoa_p: int = 1
    qaoa_seed: int = 20260906
    qaoa_shots: int = 512
    qaoa_optimizer_restarts: int = 2
    qaoa_optimizer_steps: int = 6
    qaoa_max_variables: int = 12
    audit_max_variables: int = 16
    rho: float | None = None
    conflict_penalty: float | None = None

    def __post_init__(self) -> None:
        aliases = {
            "greedy": "greedy",
            "exact": "exact",
            "qaoa": "qaoa",
            "direct_qaoa": "qaoa",
            "direct-qaoa": "qaoa",
        }
        if not isinstance(self.method, str) or self.method.strip().lower() not in aliases:
            raise ValueError("method must be one of greedy, exact, qaoa")
        object.__setattr__(self, "method", aliases[self.method.strip().lower()])
        object.__setattr__(
            self, "budget_requested", _positive_integer(self.budget_requested, "budget_requested")
        )
        gamma = _finite(self.redundancy_weight, "redundancy_weight")
        if gamma < 0.0:
            raise ValueError("redundancy_weight must be >= 0")
        object.__setattr__(self, "redundancy_weight", gamma)
        alpha = _finite(self.redundancy_alpha, "redundancy_alpha")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("redundancy_alpha must lie in [0, 1]")
        object.__setattr__(self, "redundancy_alpha", alpha)
        object.__setattr__(self, "qaoa_p", _positive_integer(self.qaoa_p, "qaoa_p"))
        if isinstance(self.qaoa_seed, bool) or not isinstance(self.qaoa_seed, Integral):
            raise TypeError("qaoa_seed must be an integer")
        object.__setattr__(self, "qaoa_seed", int(self.qaoa_seed))
        object.__setattr__(
            self, "qaoa_shots", _positive_integer(self.qaoa_shots, "qaoa_shots")
        )
        object.__setattr__(
            self,
            "qaoa_optimizer_restarts",
            _positive_integer(self.qaoa_optimizer_restarts, "qaoa_optimizer_restarts"),
        )
        object.__setattr__(
            self,
            "qaoa_optimizer_steps",
            _nonnegative_integer(self.qaoa_optimizer_steps, "qaoa_optimizer_steps"),
        )
        object.__setattr__(
            self,
            "qaoa_max_variables",
            _positive_integer(self.qaoa_max_variables, "qaoa_max_variables"),
        )
        if self.qaoa_max_variables > 12:
            raise ValueError("existing direct QAOA backend supports at most 12 variables")
        object.__setattr__(
            self,
            "audit_max_variables",
            _positive_integer(self.audit_max_variables, "audit_max_variables"),
        )
        for name in ("rho", "conflict_penalty"):
            raw = getattr(self, name)
            if raw is not None:
                value = _finite(raw, name)
                if value <= 0.0:
                    raise ValueError(f"{name} must be > 0")
                object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def schedule_shared_actions(
    actions: Sequence[SharedAction] | Iterable[SharedAction],
    *,
    config: SharedSchedulerConfig = SharedSchedulerConfig(),
    utilities: Sequence[float] | Iterable[float] | None = None,
    utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
    redundancy: Sequence[Sequence[float]] | None = None,
) -> SharedScheduleResult:
    """Select conflict-free shared actions with explicit dummy accounting."""

    problem = build_shared_scheduling_problem(
        actions,
        config.budget_requested,
        utilities=utilities,
        utility_weights=utility_weights,
        redundancy=redundancy,
        redundancy_weight=config.redundancy_weight,
        redundancy_alpha=config.redundancy_alpha,
    )
    model = build_dummy_fixed_cardinality_qubo(
        problem, rho=config.rho, conflict_penalty=config.conflict_penalty
    )
    if model.variable_count > config.audit_max_variables:
        raise ValueError(
            "fixed-QUBO schedule refused without exhaustive audit: "
            f"K={model.variable_count} exceeds audit_max_variables="
            f"{config.audit_max_variables}"
        )
    audit = audit_dummy_fixed_cardinality_qubo(
        model, max_variables=config.audit_max_variables
    )
    if not audit.diagnostics.penalty_sufficient:
        raise RuntimeError(
            "fixed-QUBO schedule failed closed because the exhaustive audit "
            "did not certify phase identity and penalty sufficiency"
        )

    qaoa_payload: dict[str, object] | None = None
    qaoa_attempted = False
    qaoa_succeeded = False
    qaoa_backend_succeeded = False
    qaoa_direct = False
    qaoa_repaired = False
    qaoa_fallback = False
    fallback_reason: str | None = None
    method_executed = config.method

    if problem.real_candidate_count == 0:
        selected = ()
        method_executed = "not_invoked_no_candidates"
    elif config.method == "greedy":
        selected = _greedy_selected(problem)
    elif config.method == "exact":
        selected = _exact_selected(problem)
    else:
        if model.variable_count > config.qaoa_max_variables:
            raise ValueError(
                "direct QAOA adapter refused augmented problem: "
                f"K={model.variable_count} exceeds qaoa_max_variables="
                f"{config.qaoa_max_variables}"
            )
        qaoa_attempted = True
        linear, quadratic = model.qaoa_coefficients()
        exact_bits = _augmented_bitstring(model, _exact_selected(problem))
        try:
            qaoa = run_qaoa(
                linear,
                quadratic,
                num_variables=model.variable_count,
                p=config.qaoa_p,
                seed=config.qaoa_seed,
                shots=config.qaoa_shots,
                optimizer_restarts=config.qaoa_optimizer_restarts,
                optimizer_steps=config.qaoa_optimizer_steps,
            )
            qaoa_backend_succeeded = True
            audited_phase_energies = tuple(
                record.backend_coefficient_energy for record in audit.records
            )
            expected_cost_offset = min(audited_phase_energies)
            expected_cost_scale = max(audited_phase_energies) - expected_cost_offset
            if expected_cost_scale <= 1e-15:
                expected_cost_scale = 1.0
            backend_diagnostics = qaoa.diagnostics
            if backend_diagnostics.get("objective_source") != "qubo":
                raise RuntimeError("QAOA backend did not report a QUBO phase source")
            if backend_diagnostics.get("infeasible_penalty") is not None:
                raise RuntimeError("QAOA backend unexpectedly added a feasibility penalty")
            for name, expected in (
                ("cost_offset", expected_cost_offset),
                ("cost_scale", expected_cost_scale),
            ):
                actual = backend_diagnostics.get(name)
                if actual is None or not math.isclose(
                    float(actual),
                    expected,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    raise RuntimeError(
                        f"QAOA backend {name} does not match the exhaustive "
                        "frozen-QUBO phase audit"
                    )
            augmented_bits, qaoa_repaired, postselection = _postselect_qaoa_counts(
                model,
                qaoa.counts,
                repair_bits=exact_bits,
                expected_shots=config.qaoa_shots,
            )
            selected = model.selected_real(augmented_bits)
            qaoa_payload = qaoa.as_dict()
            qaoa_payload["phase_input"] = {
                "source": "frozen_dummy_fixed_cardinality_qubo",
                "linear": dict(linear),
                "quadratic": {
                    f"{left},{right}": value
                    for (left, right), value in quadratic.items()
                },
                "constant_omitted_from_phase": model.constant,
                "feasibility_oracle_passed_to_backend": False,
                "repair_function_passed_to_backend": False,
                "full_phase_space_audited": True,
                "audited_backend_cost_offset": expected_cost_offset,
                "audited_backend_cost_scale": expected_cost_scale,
                "backend_affine_phase_scaling_matches_audit": True,
                "backend_result_is_feasible_semantics": (
                    "unconstrained phase-domain validity only; frozen-QUBO "
                    "feasibility is recomputed during E6 postselection"
                ),
            }
            qaoa_payload["postselection"] = postselection
            qaoa_succeeded = True
            qaoa_direct = not qaoa_repaired
            if qaoa_repaired:
                method_executed = "qaoa_no_feasible_sample_exact_repair"
        except Exception as exc:  # explicit mechanism fallback, never silent
            selected = _greedy_selected(problem)
            qaoa_fallback = True
            fallback_reason = f"{type(exc).__name__}: {exc}"
            method_executed = "qaoa_fallback_greedy"

    if not problem.is_conflict_free(selected):
        raise RuntimeError("scheduler returned footprint-conflicting actions")
    if len(selected) > problem.budget_effective:
        raise RuntimeError("scheduler exceeded the effective real-action budget")
    if config.method != "qaoa" or not qaoa_succeeded:
        augmented_bits = _augmented_bitstring(model, selected)
    real_bits = augmented_bits[: problem.real_candidate_count]
    dummy_selected = sum(augmented_bits[problem.real_candidate_count :])
    if sum(augmented_bits) != problem.budget_effective:
        raise RuntimeError("dummy-augmented schedule violated fixed cardinality")

    utility_sum = sum(problem.utilities[index] for index in selected)
    pair_redundancy = sum(
        problem.redundancy[left][right]
        for offset, left in enumerate(selected)
        for right in selected[offset + 1 :]
    )
    diagnostics: dict[str, object] = {
        "schema_version": "xa.e6-shared-schedule-decision.v1",
        "method_requested": config.method,
        "method_executed": method_executed,
        "real_candidate_count": problem.real_candidate_count,
        "dummy_candidate_count": model.dummy_count,
        "augmented_variable_count": model.variable_count,
        "budget_requested": problem.budget_requested,
        "budget_effective": problem.budget_effective,
        "selected_indices": list(selected),
        "dummy_selected": dummy_selected,
        "fixed_cardinality_holds": sum(augmented_bits) == problem.budget_effective,
        "footprint_conflict_free": problem.is_conflict_free(selected),
        "utility_sum": utility_sum,
        "pair_redundancy_sum": pair_redundancy,
        "weighted_redundancy_penalty": problem.redundancy_weight * pair_redundancy,
        "objective": problem.objective(selected),
        "qaoa_attempted": qaoa_attempted,
        "qaoa_backend_succeeded": qaoa_backend_succeeded,
        "qaoa_succeeded": qaoa_succeeded,
        "qaoa_direct": qaoa_direct,
        "qaoa_repaired": qaoa_repaired,
        "qaoa_fallback": qaoa_fallback,
        "qaoa_execution_class": (
            "direct_unrepaired"
            if qaoa_direct
            else "direct_repaired"
            if qaoa_repaired
            else "fallback"
            if qaoa_fallback
            else "not_invoked"
        ),
        "fallback_reason": fallback_reason,
        "qaoa": qaoa_payload,
        "qubo": model.to_dict(),
        "qubo_audit": audit.diagnostics.to_dict(),
        "evidence_role": "development_mvp_mechanism_only",
        "learned_head_connected": False,
        "replay_update_connected": False,
        "performance_evidence": False,
    }
    return SharedScheduleResult(
        selected_indices=tuple(selected),
        real_bitstring=tuple(real_bits),
        augmented_bitstring=tuple(augmented_bits),
        dummy_selected=dummy_selected,
        diagnostics=diagnostics,
    )


class SharedActionScheduler:
    """Small state-free adapter matching the existing scheduler style."""

    def __init__(self, config: SharedSchedulerConfig = SharedSchedulerConfig()) -> None:
        self.config = config

    def select(
        self,
        actions: Sequence[SharedAction] | Iterable[SharedAction],
        utilities: Sequence[float] | Iterable[float] | None = None,
        *,
        utility_weights: SharedUtilityWeights = SharedUtilityWeights(),
        redundancy: Sequence[Sequence[float]] | None = None,
    ) -> SharedScheduleResult:
        return schedule_shared_actions(
            actions,
            config=self.config,
            utilities=utilities,
            utility_weights=utility_weights,
            redundancy=redundancy,
        )


__all__ = [
    "DummyFixedCardinalityQUBO",
    "QUBOAuditDiagnostics",
    "QUBOAuditRecord",
    "QUBOAuditResult",
    "ProgramResourceSummary",
    "SharedActionScheduler",
    "SharedScheduleResult",
    "SharedSchedulerConfig",
    "SharedSchedulingProblem",
    "SharedUtilityBreakdown",
    "SharedUtilityWeights",
    "action_conflict_matrix",
    "action_redundancy_matrix",
    "audit_dummy_fixed_cardinality_qubo",
    "build_dummy_fixed_cardinality_qubo",
    "build_shared_scheduling_problem",
    "program_resource_summary",
    "schedule_shared_actions",
    "shared_action_utility",
    "shared_action_utility_breakdown",
]
