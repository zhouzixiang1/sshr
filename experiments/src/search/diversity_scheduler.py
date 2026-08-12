"""Fixed-budget utility--diversity selection and auditable QUBO helpers.

The scheduler in this module selects *independent* search actions.  It does not
combine actions or change the semantics of an MCTS node.  Given utilities
``u_i`` and a symmetric pair-redundancy matrix ``r_ij``, every solver uses the
same fixed-cardinality objective

    F(x) = sum_i u_i x_i - gamma sum_{i<j} r_ij x_i x_j,
    sum_i x_i = B_eff,

where ``B_eff = min(B_requested, K)``.  The QUBO helpers intentionally live in
the same dependency-free module so small instances can be exhaustively audited
before a quantum solver is connected.
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import asdict, dataclass
from numbers import Integral
from typing import Iterable, Sequence


_METHOD_ALIASES = {
    "random": "random",
    "random-b": "random",
    "random_b": "random",
    "top-b": "top_b",
    "top_b": "top_b",
    "top": "top_b",
    "greedy": "greedy",
    "exact": "exact",
}


@dataclass(frozen=True)
class SelectionDiagnostics:
    """Machine-readable account of one scheduler decision."""

    method: str
    status: str
    candidate_count: int
    budget_requested: int
    budget_effective: int
    solver_invoked: bool
    seed: int | None
    redundancy_weight: float
    evaluations: int
    selection_order: tuple[int, ...]
    utility_sum: float
    pair_redundancy_sum: float
    weighted_redundancy_penalty: float
    objective: float
    tie_break: str = "lowest_candidate_index"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SelectionResult:
    """Selected candidate indices plus a complete decision diagnostic."""

    selected_indices: tuple[int, ...]
    bitstring: tuple[int, ...]
    diagnostics: SelectionDiagnostics

    def to_dict(self) -> dict:
        return {
            "selected_indices": list(self.selected_indices),
            "bitstring": list(self.bitstring),
            "diagnostics": self.diagnostics.to_dict(),
        }


@dataclass(frozen=True)
class QUBOModel:
    """Expanded binary polynomial for the cardinality-penalized objective.

    ``energy(x)`` evaluates

        constant + sum_i linear_i x_i + sum_{i<j} quadratic_ij x_i x_j.

    The constant offset is retained so energies remain comparable to the
    direct identity rather than only within a single problem instance.
    """

    candidate_count: int
    budget_effective: int
    redundancy_weight: float
    rho: float
    linear: tuple[float, ...]
    quadratic: tuple[tuple[int, int, float], ...]
    constant: float

    def energy(self, bitstring: Sequence[int]) -> float:
        bits = _validate_bitstring(bitstring, self.candidate_count)
        energy = self.constant
        energy += sum(coefficient * bits[index] for index, coefficient in enumerate(self.linear))
        energy += sum(
            coefficient * bits[left] * bits[right]
            for left, right, coefficient in self.quadratic
        )
        return float(energy)

    def to_dict(self) -> dict:
        return {
            "candidate_count": self.candidate_count,
            "budget_effective": self.budget_effective,
            "redundancy_weight": self.redundancy_weight,
            "rho": self.rho,
            "linear": list(self.linear),
            "quadratic": [list(term) for term in self.quadratic],
            "constant": self.constant,
        }


@dataclass(frozen=True)
class BitstringAuditRecord:
    """One row of an exhaustive small-instance QUBO audit."""

    bitstring: tuple[int, ...]
    cardinality: int
    feasible: bool
    objective: float
    identity_energy: float
    polynomial_energy: float
    identity_error: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QUBOAuditDiagnostics:
    """Summary checks derived from all ``2**K`` binary assignments."""

    candidate_count: int
    budget_effective: int
    total_bitstrings: int
    feasible_bitstrings: int
    max_identity_error: float
    energy_identity_holds: bool
    feasible_ordering_matches: bool
    feasible_optimal_bitstrings: tuple[tuple[int, ...], ...]
    global_minimum_bitstrings: tuple[tuple[int, ...], ...]
    all_global_minima_feasible: bool
    penalty_sufficient: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QUBOAuditResult:
    """Expanded model, every audited bitstring, and aggregate checks."""

    model: QUBOModel
    records: tuple[BitstringAuditRecord, ...]
    diagnostics: QUBOAuditDiagnostics

    def to_dict(self) -> dict:
        return {
            "model": self.model.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "diagnostics": self.diagnostics.to_dict(),
        }


@dataclass(frozen=True)
class _Problem:
    utilities: tuple[float, ...]
    redundancy: tuple[tuple[float, ...], ...]
    redundancy_weight: float

    @property
    def candidate_count(self) -> int:
        return len(self.utilities)


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite real number, not bool")
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


def _effective_budget(value: object, candidate_count: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError("budget_effective must be an integer")
    converted = int(value)
    if not 0 <= converted <= candidate_count:
        raise ValueError(
            f"budget_effective must be between 0 and K={candidate_count}, got {converted}"
        )
    return converted


def _validate_problem(
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    redundancy_weight: float,
) -> _Problem:
    utility_values = tuple(
        _finite_float(value, f"utilities[{index}]")
        for index, value in enumerate(utilities)
    )
    candidate_count = len(utility_values)
    rows = tuple(tuple(row) for row in redundancy)
    if len(rows) != candidate_count:
        raise ValueError(
            "redundancy must be a square K x K matrix matching utilities "
            f"(expected {candidate_count} rows, got {len(rows)})"
        )

    converted_rows: list[list[float]] = []
    for row_index, row in enumerate(rows):
        if len(row) != candidate_count:
            raise ValueError(
                "redundancy must be a square K x K matrix matching utilities "
                f"(row {row_index} has length {len(row)}, expected {candidate_count})"
            )
        converted_rows.append(
            [
                _finite_float(value, f"redundancy[{row_index}][{column_index}]")
                for column_index, value in enumerate(row)
            ]
        )

    # Accept harmless round-off asymmetry, but canonicalize each pair to its
    # mean so the result never depends on choosing the upper or lower triangle.
    for left in range(candidate_count):
        for right in range(left + 1, candidate_count):
            forward = converted_rows[left][right]
            backward = converted_rows[right][left]
            if not math.isclose(forward, backward, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(
                    "redundancy must be symmetric: "
                    f"[{left}][{right}]={forward} != [{right}][{left}]={backward}"
                )
            canonical = 0.5 * (forward + backward)
            converted_rows[left][right] = canonical
            converted_rows[right][left] = canonical

    weight = _finite_float(redundancy_weight, "redundancy_weight")
    if weight < 0.0:
        raise ValueError("redundancy_weight must be >= 0")
    return _Problem(
        utilities=utility_values,
        redundancy=tuple(tuple(row) for row in converted_rows),
        redundancy_weight=weight,
    )


def _validate_bitstring(bitstring: Sequence[int], candidate_count: int) -> tuple[int, ...]:
    bits = tuple(bitstring)
    if len(bits) != candidate_count:
        raise ValueError(
            f"bitstring length must equal K={candidate_count}, got {len(bits)}"
        )
    for index, bit in enumerate(bits):
        if isinstance(bit, bool):
            bit = int(bit)
        if not isinstance(bit, Integral) or int(bit) not in (0, 1):
            raise ValueError(f"bitstring[{index}] must be binary, got {bit!r}")
    return tuple(int(bit) for bit in bits)


def _objective_parts(
    problem: _Problem,
    selected_indices: Sequence[int],
) -> tuple[float, float, float, float]:
    selected = tuple(selected_indices)
    utility_sum = sum(problem.utilities[index] for index in selected)
    pair_redundancy_sum = sum(
        problem.redundancy[left][right]
        for offset, left in enumerate(selected)
        for right in selected[offset + 1 :]
    )
    weighted_penalty = problem.redundancy_weight * pair_redundancy_sum
    return (
        float(utility_sum),
        float(pair_redundancy_sum),
        float(weighted_penalty),
        float(utility_sum - weighted_penalty),
    )


def selection_objective(
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    selected_indices: Sequence[int],
    *,
    redundancy_weight: float = 1.0,
) -> float:
    """Evaluate ``F`` for a subset of candidate indices."""

    problem = _validate_problem(utilities, redundancy, redundancy_weight)
    selected = tuple(selected_indices)
    if len(set(selected)) != len(selected):
        raise ValueError("selected_indices must not contain duplicates")
    for index in selected:
        if isinstance(index, bool) or not isinstance(index, Integral):
            raise TypeError("selected_indices must contain integers")
        if not 0 <= int(index) < problem.candidate_count:
            raise IndexError(f"candidate index out of range: {index}")
    normalized = tuple(sorted(int(index) for index in selected))
    return _objective_parts(problem, normalized)[-1]


def _canonical_method(method: str) -> str:
    if not isinstance(method, str):
        raise TypeError("method must be a string")
    canonical = _METHOD_ALIASES.get(method.strip().lower())
    if canonical is None:
        allowed = ", ".join(sorted({"random", "top_b", "greedy", "exact"}))
        raise ValueError(f"unknown scheduling method {method!r}; expected one of: {allowed}")
    return canonical


def schedule_diverse_candidates(
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    budget_requested: int,
    *,
    method: str = "greedy",
    redundancy_weight: float = 1.0,
    seed: int = 0,
) -> SelectionResult:
    """Select exactly ``min(budget_requested, K)`` candidate indices.

    Four dependency-free paths are available: seeded ``random``, utility-only
    ``top_b``, marginal-objective ``greedy``, and exhaustive ``exact``.  All
    ties in the deterministic solvers prefer the lowest candidate index (and
    exact subset ties therefore prefer the lexicographically smallest tuple).
    """

    budget = _positive_integer(budget_requested, "budget_requested")
    canonical_method = _canonical_method(method)
    problem = _validate_problem(utilities, redundancy, redundancy_weight)
    candidate_count = problem.candidate_count
    budget_effective = min(budget, candidate_count)

    if isinstance(seed, bool) or not isinstance(seed, Integral):
        raise TypeError("seed must be an integer")
    normalized_seed = int(seed)

    if candidate_count == 0:
        selection_order: tuple[int, ...] = ()
        selected: tuple[int, ...] = ()
        status = "skipped_no_candidates"
        solver_invoked = False
        evaluations = 0
    elif candidate_count <= budget:
        selection_order = tuple(range(candidate_count))
        selected = selection_order
        status = "skipped_budget_covers_pool"
        solver_invoked = False
        evaluations = 0
    elif canonical_method == "random":
        selection_order = tuple(
            random.Random(normalized_seed).sample(range(candidate_count), budget_effective)
        )
        selected = tuple(sorted(selection_order))
        status = "selected"
        solver_invoked = True
        evaluations = 1
    elif canonical_method == "top_b":
        ranked = sorted(
            range(candidate_count),
            key=lambda index: (-problem.utilities[index], index),
        )
        selection_order = tuple(ranked[:budget_effective])
        selected = tuple(sorted(selection_order))
        status = "selected"
        solver_invoked = True
        evaluations = candidate_count
    elif canonical_method == "greedy":
        chosen: list[int] = []
        remaining = set(range(candidate_count))
        evaluations = 0
        while len(chosen) < budget_effective:
            best_index: int | None = None
            best_marginal = -math.inf
            for index in sorted(remaining):
                marginal = problem.utilities[index] - problem.redundancy_weight * sum(
                    problem.redundancy[index][prior] for prior in chosen
                )
                evaluations += 1
                if marginal > best_marginal:
                    best_marginal = marginal
                    best_index = index
            # budget_effective <= K and the loop removes one candidate at a
            # time, so this branch is unreachable unless that invariant changes.
            if best_index is None:  # pragma: no cover - defensive invariant
                raise RuntimeError("greedy scheduler exhausted candidates early")
            chosen.append(best_index)
            remaining.remove(best_index)
        selection_order = tuple(chosen)
        selected = tuple(sorted(chosen))
        status = "selected"
        solver_invoked = True
    else:  # exact
        best_subset: tuple[int, ...] | None = None
        best_objective = -math.inf
        evaluations = 0
        for subset in itertools.combinations(range(candidate_count), budget_effective):
            objective = _objective_parts(problem, subset)[-1]
            evaluations += 1
            # combinations are lexicographic, so retaining the first exact tie
            # implements the declared deterministic tie-break.
            if objective > best_objective:
                best_objective = objective
                best_subset = subset
        if best_subset is None:  # pragma: no cover - guarded by K > B > 0
            raise RuntimeError("exact scheduler found no feasible subset")
        selection_order = best_subset
        selected = best_subset
        status = "selected"
        solver_invoked = True

    utility_sum, pair_sum, weighted_penalty, objective = _objective_parts(problem, selected)
    selected_set = set(selected)
    bitstring = tuple(int(index in selected_set) for index in range(candidate_count))
    diagnostics = SelectionDiagnostics(
        method=canonical_method,
        status=status,
        candidate_count=candidate_count,
        budget_requested=budget,
        budget_effective=budget_effective,
        solver_invoked=solver_invoked,
        seed=normalized_seed if canonical_method == "random" else None,
        redundancy_weight=problem.redundancy_weight,
        evaluations=evaluations,
        selection_order=selection_order,
        utility_sum=utility_sum,
        pair_redundancy_sum=pair_sum,
        weighted_redundancy_penalty=weighted_penalty,
        objective=objective,
    )
    return SelectionResult(selected_indices=selected, bitstring=bitstring, diagnostics=diagnostics)


def build_qubo_model(
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    budget_effective: int,
    *,
    redundancy_weight: float = 1.0,
    rho: float,
) -> QUBOModel:
    """Expand ``-F + rho * (sum(x) - B_eff)**2`` into QUBO terms."""

    problem = _validate_problem(utilities, redundancy, redundancy_weight)
    budget = _effective_budget(budget_effective, problem.candidate_count)
    penalty = _finite_float(rho, "rho")
    if penalty <= 0.0:
        raise ValueError("rho must be > 0")

    linear = tuple(
        -utility + penalty * (1 - 2 * budget) for utility in problem.utilities
    )
    quadratic = tuple(
        (
            left,
            right,
            problem.redundancy_weight * problem.redundancy[left][right]
            + 2.0 * penalty,
        )
        for left in range(problem.candidate_count)
        for right in range(left + 1, problem.candidate_count)
    )
    return QUBOModel(
        candidate_count=problem.candidate_count,
        budget_effective=budget,
        redundancy_weight=problem.redundancy_weight,
        rho=penalty,
        linear=linear,
        quadratic=quadratic,
        constant=penalty * budget * budget,
    )


def qubo_energy(
    bitstring: Sequence[int],
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    budget_effective: int,
    *,
    redundancy_weight: float = 1.0,
    rho: float,
) -> float:
    """Evaluate the direct cardinality-penalized energy identity."""

    problem = _validate_problem(utilities, redundancy, redundancy_weight)
    budget = _effective_budget(budget_effective, problem.candidate_count)
    penalty = _finite_float(rho, "rho")
    if penalty <= 0.0:
        raise ValueError("rho must be > 0")
    bits = _validate_bitstring(bitstring, problem.candidate_count)
    selected = tuple(index for index, bit in enumerate(bits) if bit)
    objective = _objective_parts(problem, selected)[-1]
    return float(-objective + penalty * (sum(bits) - budget) ** 2)


def audit_qubo_bitstrings(
    utilities: Sequence[float] | Iterable[float],
    redundancy: Sequence[Sequence[float]] | Iterable[Sequence[float]],
    budget_effective: int,
    *,
    redundancy_weight: float = 1.0,
    rho: float,
    max_candidates: int = 16,
    tolerance: float = 1e-9,
) -> QUBOAuditResult:
    """Exhaustively audit the QUBO identity and feasible-set ordering.

    The explicit ``max_candidates`` guard prevents accidental exponential work;
    callers may raise it deliberately for a known-small audit environment.
    ``penalty_sufficient`` is true only when *every* global energy minimizer has
    cardinality ``B_eff``.  An insufficient ``rho`` is reported, not repaired or
    hidden.
    """

    problem = _validate_problem(utilities, redundancy, redundancy_weight)
    budget = _effective_budget(budget_effective, problem.candidate_count)
    max_k = _positive_integer(max_candidates, "max_candidates")
    if problem.candidate_count > max_k:
        raise ValueError(
            "exhaustive QUBO audit refused: "
            f"K={problem.candidate_count} exceeds max_candidates={max_k}"
        )
    absolute_tolerance = _finite_float(tolerance, "tolerance")
    if absolute_tolerance < 0.0:
        raise ValueError("tolerance must be >= 0")

    model = build_qubo_model(
        problem.utilities,
        problem.redundancy,
        budget,
        redundancy_weight=problem.redundancy_weight,
        rho=rho,
    )
    records: list[BitstringAuditRecord] = []
    for bits in itertools.product((0, 1), repeat=problem.candidate_count):
        selected = tuple(index for index, bit in enumerate(bits) if bit)
        objective = _objective_parts(problem, selected)[-1]
        identity_energy = -objective + model.rho * (sum(bits) - budget) ** 2
        polynomial_energy = model.energy(bits)
        records.append(
            BitstringAuditRecord(
                bitstring=bits,
                cardinality=sum(bits),
                feasible=sum(bits) == budget,
                objective=objective,
                identity_energy=float(identity_energy),
                polynomial_energy=polynomial_energy,
                identity_error=abs(float(identity_energy) - polynomial_energy),
            )
        )

    feasible = [record for record in records if record.feasible]
    # A valid 0 <= B_eff <= K always has at least one feasible bitstring,
    # including the unique empty assignment when K=B_eff=0.
    best_feasible_objective = max(record.objective for record in feasible)
    feasible_optima = tuple(
        record.bitstring for record in feasible if record.objective == best_feasible_objective
    )
    global_minimum_energy = min(record.polynomial_energy for record in records)
    global_minima = tuple(
        record.bitstring
        for record in records
        if record.polynomial_energy == global_minimum_energy
    )
    global_minimum_records = [
        record for record in records if record.polynomial_energy == global_minimum_energy
    ]

    objective_order = tuple(
        record.bitstring
        for record in sorted(feasible, key=lambda record: (-record.objective, record.bitstring))
    )
    energy_order = tuple(
        record.bitstring
        for record in sorted(
            feasible, key=lambda record: (record.polynomial_energy, record.bitstring)
        )
    )
    max_error = max(record.identity_error for record in records)
    identity_holds = all(
        math.isclose(
            record.identity_energy,
            record.polynomial_energy,
            rel_tol=0.0,
            abs_tol=absolute_tolerance,
        )
        for record in records
    )
    all_minima_feasible = all(record.feasible for record in global_minimum_records)
    diagnostics = QUBOAuditDiagnostics(
        candidate_count=problem.candidate_count,
        budget_effective=budget,
        total_bitstrings=len(records),
        feasible_bitstrings=len(feasible),
        max_identity_error=max_error,
        energy_identity_holds=identity_holds,
        feasible_ordering_matches=objective_order == energy_order,
        feasible_optimal_bitstrings=feasible_optima,
        global_minimum_bitstrings=global_minima,
        all_global_minima_feasible=all_minima_feasible,
        penalty_sufficient=identity_holds and all_minima_feasible,
    )
    return QUBOAuditResult(model=model, records=tuple(records), diagnostics=diagnostics)


__all__ = [
    "BitstringAuditRecord",
    "QUBOAuditDiagnostics",
    "QUBOAuditResult",
    "QUBOModel",
    "SelectionDiagnostics",
    "SelectionResult",
    "audit_qubo_bitstrings",
    "build_qubo_model",
    "qubo_energy",
    "schedule_diverse_candidates",
    "selection_objective",
]
