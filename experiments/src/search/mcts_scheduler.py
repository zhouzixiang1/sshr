"""MCTS-facing utility--diversity scheduling, including an audited QAOA path.

The scheduler selects a fixed subset of *independent* action edges.  It never
combines ``FactorAction`` objects and therefore cannot alter factor-plan
semantics.  Classical and QAOA paths consume the same utilities, redundancy
matrix, candidate pool and budget.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from numbers import Integral
from typing import Sequence

from src.search.diversity_scheduler import (
    build_qubo_model,
    schedule_diverse_candidates,
    selection_objective,
)
from src.search.qaoa_scheduler import run_qaoa


_CLASSICAL_METHODS = {"random", "top_b", "greedy", "exact"}
_QAOA_MODES = {"ideal", "shot", "noisy"}


@dataclass(frozen=True)
class DiversitySchedulerConfig:
    """Configuration kept separate from the logical synthesis contract."""

    method: str = "off"
    budget_requested: int = 4
    pool_size: int = 10
    min_candidates: int = 6
    max_depth: int = 0
    redundancy_weight: float = 0.25
    redundancy_alpha: float = 0.7
    utility_clip: float = 1.0
    exact_max_candidates: int = 16
    seed: int = 0
    qaoa_mode: str = "shot"
    qaoa_p: int = 1
    qaoa_shots: int = 512
    qaoa_noise_bitflip_probability: float = 0.02
    qaoa_penalty_rho: float | None = None
    qaoa_optimizer_restarts: int = 8
    qaoa_optimizer_steps: int = 20

    def __post_init__(self) -> None:
        method = self.method.strip().lower().replace("-", "_")
        if method not in {"off", "qaoa", *_CLASSICAL_METHODS}:
            raise ValueError(f"unsupported scheduler method: {self.method!r}")
        object.__setattr__(self, "method", method)
        mode = self.qaoa_mode.strip().lower()
        if mode not in _QAOA_MODES:
            raise ValueError(f"unsupported qaoa_mode: {self.qaoa_mode!r}")
        object.__setattr__(self, "qaoa_mode", mode)

        for name in (
            "budget_requested",
            "pool_size",
            "min_candidates",
            "exact_max_candidates",
            "qaoa_p",
            "qaoa_shots",
            "qaoa_optimizer_restarts",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if isinstance(self.max_depth, bool) or not isinstance(self.max_depth, Integral):
            raise ValueError("max_depth must be a non-negative integer")
        if self.max_depth < 0:
            raise ValueError("max_depth must be a non-negative integer")
        if (
            isinstance(self.qaoa_optimizer_steps, bool)
            or not isinstance(self.qaoa_optimizer_steps, Integral)
            or self.qaoa_optimizer_steps < 0
        ):
            raise ValueError("qaoa_optimizer_steps must be a non-negative integer")

        for name in (
            "redundancy_weight",
            "redundancy_alpha",
            "utility_clip",
            "qaoa_noise_bitflip_probability",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.redundancy_weight < 0.0:
            raise ValueError("redundancy_weight must be >= 0")
        if not 0.0 <= self.redundancy_alpha <= 1.0:
            raise ValueError("redundancy_alpha must lie in [0, 1]")
        if self.utility_clip <= 0.0:
            raise ValueError("utility_clip must be > 0")
        if not 0.0 <= self.qaoa_noise_bitflip_probability <= 1.0:
            raise ValueError("qaoa_noise_bitflip_probability must lie in [0, 1]")
        if self.qaoa_penalty_rho is not None:
            rho = float(self.qaoa_penalty_rho)
            if not math.isfinite(rho) or rho <= 0.0:
                raise ValueError("qaoa_penalty_rho must be finite and > 0")
        if method == "qaoa" and self.pool_size > 12:
            raise ValueError("the statevector QAOA backend supports pool_size <= 12")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ActionScheduleDecision:
    """One persistent decision for one MCTS node."""

    selected_indices: tuple[int, ...]
    diagnostics: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_indices": list(self.selected_indices),
            "diagnostics": dict(self.diagnostics),
        }


def _jaccard(left: frozenset[int], right: frozenset[int]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def action_redundancy_matrix(
    actions: Sequence[object], *, alpha: float = 0.7
) -> tuple[tuple[float, ...], ...]:
    """Build the symmetric group/rest Jaccard redundancy matrix."""

    alpha = float(alpha)
    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must lie in [0, 1]")
    groups = [frozenset(getattr(action, "group")) for action in actions]
    rests = [frozenset(getattr(action, "rest")) for action in actions]
    matrix = [[0.0 for _ in actions] for _ in actions]
    for left in range(len(actions)):
        for right in range(left + 1, len(actions)):
            value = alpha * _jaccard(groups[left], groups[right]) + (
                1.0 - alpha
            ) * _jaccard(rests[left], rests[right])
            matrix[left][right] = value
            matrix[right][left] = value
    return tuple(tuple(row) for row in matrix)


def _auto_penalty_rho(
    utilities: Sequence[float],
    redundancy: Sequence[Sequence[float]],
    redundancy_weight: float,
) -> float:
    """A conservative cardinality penalty larger than the objective span."""

    objective_bound = sum(abs(float(value)) for value in utilities)
    objective_bound += redundancy_weight * sum(
        abs(float(redundancy[left][right]))
        for left in range(len(redundancy))
        for right in range(left + 1, len(redundancy))
    )
    return max(1.0, 2.0 * objective_bound + 1.0)


def _repair_cardinality(
    bitstring: Sequence[int],
    utilities: Sequence[float],
    redundancy: Sequence[Sequence[float]],
    budget: int,
    redundancy_weight: float,
) -> tuple[int, ...]:
    """Deterministically repair cardinality while maximizing the same objective."""

    selected = {index for index, bit in enumerate(bitstring) if int(bit)}
    universe = set(range(len(utilities)))
    while len(selected) > budget:
        remove = min(
            selected,
            key=lambda index: (
                -selection_objective(
                    utilities,
                    redundancy,
                    tuple(sorted(selected - {index})),
                    redundancy_weight=redundancy_weight,
                ),
                index,
            ),
        )
        selected.remove(remove)
    while len(selected) < budget:
        add = min(
            universe - selected,
            key=lambda index: (
                -selection_objective(
                    utilities,
                    redundancy,
                    tuple(sorted(selected | {index})),
                    redundancy_weight=redundancy_weight,
                ),
                index,
            ),
        )
        selected.add(add)
    return tuple(int(index in selected) for index in range(len(utilities)))


class MCTSDiversityScheduler:
    """Select a persistent subset from a frozen MCTS candidate pool."""

    def __init__(self, config: DiversitySchedulerConfig) -> None:
        self.config = config

    def select(
        self,
        actions: Sequence[object],
        utilities: Sequence[float],
        *,
        decision_seed: int,
    ) -> ActionScheduleDecision:
        started = time.perf_counter()
        if len(actions) != len(utilities):
            raise ValueError("actions and utilities must have the same length")
        numeric_utilities = tuple(float(value) for value in utilities)
        if not all(math.isfinite(value) for value in numeric_utilities):
            raise ValueError("utilities must be finite")
        clipped = tuple(
            max(-self.config.utility_clip, min(self.config.utility_clip, value))
            for value in numeric_utilities
        )
        redundancy = action_redundancy_matrix(
            actions, alpha=self.config.redundancy_alpha
        )
        candidate_count = len(actions)
        budget_effective = min(self.config.budget_requested, candidate_count)
        base: dict[str, object] = {
            "scheduler_method": self.config.method,
            "candidate_count": candidate_count,
            "budget_requested": self.config.budget_requested,
            "budget_effective": budget_effective,
            "seed": int(decision_seed),
            "utilities": list(clipped),
            "redundancy_matrix": [list(row) for row in redundancy],
            "redundancy_weight": self.config.redundancy_weight,
            "redundancy_alpha": self.config.redundancy_alpha,
            "qaoa_eligible": False,
            "qaoa_attempted": False,
            "qaoa_succeeded": False,
            "qaoa_repaired": False,
            "qaoa_fallback": False,
            "fallback_solver": None,
            "fallback_reason": None,
        }

        if self.config.method == "off":
            selected = tuple(range(candidate_count))
            base.update(status="scheduler_off", selected_indices=list(selected))
            base["total_elapsed_s"] = time.perf_counter() - started
            return ActionScheduleDecision(selected, base)

        if self.config.method in _CLASSICAL_METHODS:
            result = schedule_diverse_candidates(
                clipped,
                redundancy,
                self.config.budget_requested,
                method=self.config.method,
                redundancy_weight=self.config.redundancy_weight,
                seed=decision_seed,
            )
            base.update(result.diagnostics.to_dict())
            base["selected_indices"] = list(result.selected_indices)
            base["total_elapsed_s"] = time.perf_counter() - started
            return ActionScheduleDecision(result.selected_indices, base)

        # Trivial pools and small non-eligible pools are solved classically and
        # recorded as not invoked, never as failed QAOA calls.
        qaoa_eligible = (
            candidate_count > self.config.budget_requested
            and candidate_count >= self.config.min_candidates
        )
        base["qaoa_eligible"] = qaoa_eligible
        if not qaoa_eligible:
            result = schedule_diverse_candidates(
                clipped,
                redundancy,
                self.config.budget_requested,
                method="greedy",
                redundancy_weight=self.config.redundancy_weight,
                seed=decision_seed,
            )
            base.update(
                status="qaoa_not_invoked",
                not_invoked_reason=result.diagnostics.status
                if candidate_count <= self.config.budget_requested
                else "below_min_candidates",
                selected_indices=list(result.selected_indices),
                effective_objective=result.diagnostics.objective,
            )
            base["total_elapsed_s"] = time.perf_counter() - started
            return ActionScheduleDecision(result.selected_indices, base)

        exact = None
        if candidate_count <= self.config.exact_max_candidates:
            exact = schedule_diverse_candidates(
                clipped,
                redundancy,
                self.config.budget_requested,
                method="exact",
                redundancy_weight=self.config.redundancy_weight,
            )
            base["exact_objective"] = exact.diagnostics.objective
            base["exact_selected_indices"] = list(exact.selected_indices)

        rho = self.config.qaoa_penalty_rho or _auto_penalty_rho(
            clipped, redundancy, self.config.redundancy_weight
        )
        model = build_qubo_model(
            clipped,
            redundancy,
            budget_effective,
            redundancy_weight=self.config.redundancy_weight,
            rho=rho,
        )
        linear = {index: value for index, value in enumerate(model.linear)}
        quadratic = {
            (left, right): value for left, right, value in model.quadratic
        }
        shots = None if self.config.qaoa_mode == "ideal" else self.config.qaoa_shots
        noise = (
            self.config.qaoa_noise_bitflip_probability
            if self.config.qaoa_mode == "noisy"
            else 0.0
        )
        base["qaoa_attempted"] = True
        qaoa_started = time.perf_counter()
        try:
            result = run_qaoa(
                linear,
                quadratic,
                num_variables=candidate_count,
                p=self.config.qaoa_p,
                seed=decision_seed,
                shots=shots,
                noise_bitflip_probability=noise,
                feasible=lambda bits: sum(bits) == budget_effective,
                repair=lambda bits: _repair_cardinality(
                    bits,
                    clipped,
                    redundancy,
                    budget_effective,
                    self.config.redundancy_weight,
                ),
                optimizer_restarts=self.config.qaoa_optimizer_restarts,
                optimizer_steps=self.config.qaoa_optimizer_steps,
            )
            selected = tuple(index for index, bit in enumerate(result.bitstring) if bit)
            if len(selected) != budget_effective:
                raise RuntimeError("QAOA result violated the effective budget")
            effective_objective = selection_objective(
                clipped,
                redundancy,
                selected,
                redundancy_weight=self.config.redundancy_weight,
            )
            raw_selected = tuple(
                index for index, bit in enumerate(result.sampled_bitstring) if bit
            )
            raw_objective = selection_objective(
                clipped,
                redundancy,
                raw_selected,
                redundancy_weight=self.config.redundancy_weight,
            )
            base.update(
                status="qaoa_selected",
                qaoa_succeeded=True,
                qaoa_repaired=result.repaired,
                selected_indices=list(selected),
                raw_qaoa_indices=list(raw_selected),
                raw_qaoa_objective=raw_objective,
                effective_objective=effective_objective,
                objective_regret=(
                    None
                    if exact is None
                    else exact.diagnostics.objective - effective_objective
                ),
                qubo=model.to_dict(),
                qaoa=result.as_dict(),
                qaoa_energy_with_constant=result.energy + model.constant,
            )
            base["qaoa_elapsed_s"] = time.perf_counter() - qaoa_started
            base["total_elapsed_s"] = time.perf_counter() - started
            return ActionScheduleDecision(selected, base)
        except Exception as exc:
            fallback = schedule_diverse_candidates(
                clipped,
                redundancy,
                self.config.budget_requested,
                method="greedy",
                redundancy_weight=self.config.redundancy_weight,
                seed=decision_seed,
            )
            base.update(
                status="qaoa_fallback",
                qaoa_fallback=True,
                fallback_solver="greedy",
                fallback_reason=f"{type(exc).__name__}: {exc}",
                selected_indices=list(fallback.selected_indices),
                effective_objective=fallback.diagnostics.objective,
            )
            base["qaoa_elapsed_s"] = time.perf_counter() - qaoa_started
            base["total_elapsed_s"] = time.perf_counter() - started
            return ActionScheduleDecision(fallback.selected_indices, base)


__all__ = [
    "ActionScheduleDecision",
    "DiversitySchedulerConfig",
    "MCTSDiversityScheduler",
    "action_redundancy_matrix",
]
