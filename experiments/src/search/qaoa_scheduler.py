#!/usr/bin/env python3
"""Small, dependency-light QAOA sampler for branch-scheduling experiments.

This module deliberately implements a *real* QAOA circuit simulation rather
than hiding an exact combinatorial solver behind a quantum-looking API.  The
parameter optimiser only sees expectation values produced by alternating cost
and mixer layers, and the returned candidate is selected only from measured
shots.  Exhaustive enumeration is used to construct the diagonal Hamiltonian
for at most twelve qubits -- exactly what a statevector simulator must do --
but it is never used to select the optimum bitstring.

Bitstrings are tuples ``(x_0, x_1, ...)``.  A mapping-valued quadratic QUBO is
interpreted as ``sum(q[i, j] * x_i * x_j)``.  A dense quadratic matrix is
interpreted in the usual ``x.T @ Q @ x`` convention.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np


BitString = tuple[int, ...]
ObjectiveValue = float | tuple[float, bool] | None
ObjectiveEvaluator = Callable[[BitString], ObjectiveValue]
FeasibilityEvaluator = Callable[[BitString], bool]
RepairFunction = Callable[[BitString], Sequence[int]]

MAX_QUBITS = 12


@dataclass(frozen=True)
class QAOAResult:
    """A shot-derived QAOA result and an auditable execution record.

    ``bitstring`` is the returned candidate.  It differs from
    ``sampled_bitstring`` only when the caller supplied a repair function and
    no feasible raw shot was observed.  In that case ``probability`` remains
    the measured probability of the raw source sample; a repaired bitstring is
    never presented as if the quantum circuit had sampled it directly.
    """

    bitstring: BitString
    energy: float
    probability: float
    sampled_bitstring: BitString
    sampled_energy: float | None
    is_feasible: bool
    repaired: bool
    gammas: tuple[float, ...]
    betas: tuple[float, ...]
    counts: dict[str, int]
    diagnostics: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""

        return {
            "bitstring": list(self.bitstring),
            "energy": self.energy,
            "probability": self.probability,
            "sampled_bitstring": list(self.sampled_bitstring),
            "sampled_energy": self.sampled_energy,
            "is_feasible": self.is_feasible,
            "repaired": self.repaired,
            "gammas": list(self.gammas),
            "betas": list(self.betas),
            "counts": dict(self.counts),
            "diagnostics": dict(self.diagnostics),
        }


def _mapping_max_index(values: Mapping[object, object], *, quadratic: bool) -> int:
    maximum = -1
    for key in values:
        if quadratic:
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError("quadratic mapping keys must be (i, j) pairs")
            indices = key
        else:
            indices = (key,)
        for index in indices:
            if not isinstance(index, (int, np.integer)) or int(index) < 0:
                raise ValueError("QUBO indices must be non-negative integers")
            maximum = max(maximum, int(index))
    return maximum


def _infer_num_variables(
    linear: Sequence[float] | Mapping[int, float] | None,
    quadratic: Sequence[Sequence[float]] | Mapping[tuple[int, int], float] | None,
    num_variables: int | None,
) -> int:
    inferred: list[int] = []
    if linear is not None:
        if isinstance(linear, Mapping):
            maximum = _mapping_max_index(linear, quadratic=False)
            if maximum >= 0:
                inferred.append(maximum + 1)
        else:
            array = np.asarray(linear, dtype=float)
            if array.ndim != 1:
                raise ValueError("linear coefficients must be one-dimensional")
            inferred.append(int(array.shape[0]))

    if quadratic is not None:
        if isinstance(quadratic, Mapping):
            maximum = _mapping_max_index(quadratic, quadratic=True)
            if maximum >= 0:
                inferred.append(maximum + 1)
        else:
            array = np.asarray(quadratic, dtype=float)
            if array.ndim != 2 or array.shape[0] != array.shape[1]:
                raise ValueError("dense quadratic coefficients must be a square matrix")
            inferred.append(int(array.shape[0]))

    if num_variables is None:
        if not inferred:
            raise ValueError("num_variables is required when its size cannot be inferred")
        num_variables = max(inferred)
    elif not isinstance(num_variables, (int, np.integer)):
        raise TypeError("num_variables must be an integer")

    n = int(num_variables)
    if n < 1 or n > MAX_QUBITS:
        raise ValueError(f"num_variables must be between 1 and {MAX_QUBITS}")
    if any(size > n for size in inferred):
        raise ValueError("a QUBO coefficient index exceeds num_variables")
    return n


def _basis_bits(num_variables: int) -> np.ndarray:
    indices = np.arange(1 << num_variables, dtype=np.uint64)
    shifts = np.arange(num_variables, dtype=np.uint64)
    return ((indices[:, None] >> shifts[None, :]) & 1).astype(np.int8)


def _bitstring(index: int, num_variables: int) -> BitString:
    return tuple((int(index) >> variable) & 1 for variable in range(num_variables))


def _bitstring_index(bits: Sequence[int], num_variables: int) -> int:
    if len(bits) != num_variables:
        raise ValueError(f"bitstring must contain exactly {num_variables} bits")
    index = 0
    for variable, bit in enumerate(bits):
        if int(bit) not in (0, 1) or bit != int(bit):
            raise ValueError("bitstrings may contain only 0 and 1")
        index |= int(bit) << variable
    return index


def _count_key(index: int, num_variables: int) -> str:
    """Human-readable ``x_0 ... x_(n-1)`` order, not integer endianness."""

    return "".join(str(bit) for bit in _bitstring(index, num_variables))


def _qubo_energies(
    bits: np.ndarray,
    linear: Sequence[float] | Mapping[int, float] | None,
    quadratic: Sequence[Sequence[float]] | Mapping[tuple[int, int], float] | None,
) -> np.ndarray:
    n = bits.shape[1]
    energies = np.zeros(bits.shape[0], dtype=float)

    if linear is not None:
        coefficients = np.zeros(n, dtype=float)
        if isinstance(linear, Mapping):
            for index, value in linear.items():
                index = int(index)
                if index >= n:
                    raise ValueError("a linear coefficient index exceeds num_variables")
                coefficients[index] += float(value)
        else:
            values = np.asarray(linear, dtype=float)
            coefficients[: values.shape[0]] = values
        if not np.all(np.isfinite(coefficients)):
            raise ValueError("linear coefficients must be finite")
        energies += bits @ coefficients

    if quadratic is not None:
        if isinstance(quadratic, Mapping):
            for pair, value in quadratic.items():
                i, j = int(pair[0]), int(pair[1])
                if i >= n or j >= n:
                    raise ValueError("a quadratic coefficient index exceeds num_variables")
                coefficient = float(value)
                if not math.isfinite(coefficient):
                    raise ValueError("quadratic coefficients must be finite")
                energies += coefficient * bits[:, i] * bits[:, j]
        else:
            matrix = np.asarray(quadratic, dtype=float)
            if not np.all(np.isfinite(matrix)):
                raise ValueError("quadratic coefficients must be finite")
            padded = np.zeros((n, n), dtype=float)
            padded[: matrix.shape[0], : matrix.shape[1]] = matrix
            energies += np.einsum("bi,ij,bj->b", bits, padded, bits)
    return energies


def _evaluate_objective(
    basis: np.ndarray,
    objective: ObjectiveEvaluator,
) -> tuple[np.ndarray, np.ndarray]:
    energies = np.full(basis.shape[0], np.nan, dtype=float)
    valid = np.ones(basis.shape[0], dtype=bool)
    for index, row in enumerate(basis):
        value = objective(tuple(int(bit) for bit in row))
        if value is None:
            valid[index] = False
            continue
        if isinstance(value, tuple):
            if len(value) != 2:
                raise ValueError("objective tuples must be (energy, feasible)")
            energy, is_feasible = value
            valid[index] = bool(is_feasible)
        else:
            energy = value
        energy = float(energy)
        if not math.isfinite(energy):
            valid[index] = False
            continue
        energies[index] = energy
    return energies, valid


def _problem_energies(
    *,
    basis: np.ndarray,
    linear: Sequence[float] | Mapping[int, float] | None,
    quadratic: Sequence[Sequence[float]] | Mapping[tuple[int, int], float] | None,
    objective: ObjectiveEvaluator | None,
    feasible: FeasibilityEvaluator | None,
    infeasible_penalty: float | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None, str]:
    if objective is not None and (linear is not None or quadratic is not None):
        raise ValueError("provide either QUBO coefficients or objective, not both")
    if objective is None and linear is None and quadratic is None:
        raise ValueError("provide QUBO coefficients or an objective evaluator")

    if objective is None:
        reported = _qubo_energies(basis, linear, quadratic)
        valid = np.ones(basis.shape[0], dtype=bool)
        source = "qubo"
    else:
        reported, valid = _evaluate_objective(basis, objective)
        source = "enumerated_objective"

    if feasible is not None:
        for index, row in enumerate(basis):
            valid[index] &= bool(feasible(tuple(int(bit) for bit in row)))
    valid &= np.isfinite(reported)
    if not np.any(valid):
        raise ValueError("the objective has no feasible finite state")

    penalized = reported.copy()
    penalty_used: float | None = None
    if not np.all(valid):
        feasible_values = reported[valid]
        largest = float(np.max(feasible_values))
        span = float(np.ptp(feasible_values)) if feasible_values.size > 1 else 0.0
        if infeasible_penalty is None:
            penalty_used = largest + max(1.0, span, abs(largest) * 0.05)
        else:
            penalty_used = float(infeasible_penalty)
            if not math.isfinite(penalty_used) or penalty_used <= largest:
                raise ValueError("infeasible_penalty must exceed every feasible energy")
        penalized[~valid] = penalty_used
    return reported, penalized, valid, penalty_used, source


def _apply_mixer(state: np.ndarray, beta: float, num_variables: int) -> None:
    cosine = math.cos(beta)
    minus_i_sine = -1j * math.sin(beta)
    for variable in range(num_variables):
        stride = 1 << variable
        block = stride << 1
        blocks = state.reshape(-1, block)
        amplitude_zero = blocks[:, :stride].copy()
        amplitude_one = blocks[:, stride:].copy()
        blocks[:, :stride] = cosine * amplitude_zero + minus_i_sine * amplitude_one
        blocks[:, stride:] = minus_i_sine * amplitude_zero + cosine * amplitude_one


def _qaoa_probabilities(
    scaled_cost: np.ndarray,
    gammas: np.ndarray,
    betas: np.ndarray,
    num_variables: int,
) -> np.ndarray:
    state = np.full(scaled_cost.shape[0], 1.0 / math.sqrt(scaled_cost.shape[0]), dtype=np.complex128)
    for gamma, beta in zip(gammas, betas):
        state *= np.exp(-1j * float(gamma) * scaled_cost)
        _apply_mixer(state, float(beta), num_variables)
    probabilities = np.abs(state) ** 2
    probabilities /= float(np.sum(probabilities))
    return probabilities


def _optimise_angles(
    *,
    scaled_cost: np.ndarray,
    penalized_energies: np.ndarray,
    num_variables: int,
    p: int,
    rng: np.random.Generator,
    restarts: int,
    steps: int,
    initial_parameters: Sequence[float] | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, int]:
    periods = np.asarray([2.0 * math.pi] * p + [math.pi] * p, dtype=float)
    candidates: list[np.ndarray] = [
        np.concatenate(
            (
                np.linspace(0.35 * math.pi, 0.65 * math.pi, p),
                np.linspace(0.20 * math.pi, 0.10 * math.pi, p),
            )
        ),
        np.zeros(2 * p, dtype=float),
    ]
    if initial_parameters is not None:
        supplied = np.asarray(initial_parameters, dtype=float)
        if supplied.shape != (2 * p,) or not np.all(np.isfinite(supplied)):
            raise ValueError("initial_parameters must contain p gammas followed by p betas")
        candidates.insert(0, np.mod(supplied, periods))
    while len(candidates) < max(2, restarts):
        candidates.append(rng.random(2 * p) * periods)

    evaluations = 0

    def evaluate(theta: np.ndarray) -> tuple[float, np.ndarray]:
        nonlocal evaluations
        probabilities = _qaoa_probabilities(scaled_cost, theta[:p], theta[p:], num_variables)
        evaluations += 1
        return float(probabilities @ penalized_energies), probabilities

    best_theta = candidates[0]
    best_value, best_probabilities = evaluate(best_theta)
    for theta in candidates[1:]:
        value, probabilities = evaluate(theta)
        if value < best_value - 1e-13:
            best_theta, best_value, best_probabilities = theta, value, probabilities

    # A bounded pattern search is intentionally simple and deterministic.  It
    # evaluates only circuit expectation values and never queries argmin(cost).
    step_sizes = np.asarray([math.pi / 2.0] * p + [math.pi / 4.0] * p, dtype=float)
    for _ in range(steps):
        improved = False
        for coordinate in range(2 * p):
            local_theta = best_theta
            local_value = best_value
            local_probabilities = best_probabilities
            for direction in (-1.0, 1.0):
                trial = best_theta.copy()
                trial[coordinate] = (trial[coordinate] + direction * step_sizes[coordinate]) % periods[
                    coordinate
                ]
                value, probabilities = evaluate(trial)
                if value < local_value - 1e-13:
                    local_theta = trial
                    local_value = value
                    local_probabilities = probabilities
            if local_value < best_value - 1e-13:
                best_theta = local_theta
                best_value = local_value
                best_probabilities = local_probabilities
                improved = True
        if not improved:
            step_sizes *= 0.5
            if float(np.max(step_sizes)) < 1e-4:
                break
    return best_theta[:p], best_theta[p:], best_probabilities, best_value, evaluations


def _draw_samples(
    probabilities: np.ndarray,
    *,
    num_variables: int,
    shots: int,
    bitflip_probability: float,
    rng: np.random.Generator,
) -> np.ndarray:
    sampled = rng.choice(probabilities.shape[0], size=shots, p=probabilities).astype(np.int64)
    if bitflip_probability > 0.0:
        flips = rng.random((shots, num_variables)) < bitflip_probability
        masks = np.sum(flips.astype(np.int64) << np.arange(num_variables, dtype=np.int64), axis=1)
        sampled ^= masks
    return np.bincount(sampled, minlength=probabilities.shape[0])


def run_qaoa(
    linear: Sequence[float] | Mapping[int, float] | None = None,
    quadratic: Sequence[Sequence[float]] | Mapping[tuple[int, int], float] | None = None,
    *,
    num_variables: int | None = None,
    objective: ObjectiveEvaluator | None = None,
    feasible: FeasibilityEvaluator | None = None,
    p: int = 1,
    seed: int = 0,
    shots: int | None = 1024,
    noise_bitflip_probability: float = 0.0,
    repair: RepairFunction | None = None,
    infeasible_penalty: float | None = None,
    optimizer_restarts: int = 8,
    optimizer_steps: int = 20,
    initial_parameters: Sequence[float] | None = None,
) -> QAOAResult:
    """Optimise and sample a small QAOA problem.

    The function minimises either a QUBO or a caller-provided diagonal
    objective.  ``objective`` may return a number, ``(number, feasible)``, or
    ``None`` for an infeasible state.  ``feasible`` can impose an additional
    constraint.  Infeasible states receive a finite phase penalty above all
    feasible energies.

    With ``shots=None``, the result is the highest-probability ideal
    statevector outcome and its exact probability; diagnostics clearly mark
    that no measurement occurred.  With a positive shot count, every returned
    raw candidate comes from the sampled counts.  Noise is an independent
    measurement bit-flip channel applied after the ideal statevector circuit.
    This keeps the implementation dependency-light while giving shot/noise
    experiments an explicit, reproducible model.
    """

    if not isinstance(p, (int, np.integer)) or int(p) < 1:
        raise ValueError("p must be a positive integer")
    p = int(p)
    if shots is not None:
        if not isinstance(shots, (int, np.integer)) or int(shots) < 1:
            raise ValueError("shots must be a positive integer or None for ideal mode")
        shots = int(shots)
    if not 0.0 <= float(noise_bitflip_probability) <= 1.0:
        raise ValueError("noise_bitflip_probability must lie in [0, 1]")
    noise_bitflip_probability = float(noise_bitflip_probability)
    if shots is None and noise_bitflip_probability != 0.0:
        raise ValueError("ideal statevector mode does not accept measurement noise")
    if not isinstance(optimizer_restarts, (int, np.integer)) or int(optimizer_restarts) < 1:
        raise ValueError("optimizer_restarts must be a positive integer")
    if not isinstance(optimizer_steps, (int, np.integer)) or int(optimizer_steps) < 0:
        raise ValueError("optimizer_steps must be a non-negative integer")

    n = _infer_num_variables(linear, quadratic, num_variables)
    basis = _basis_bits(n)
    reported, penalized, valid, penalty_used, objective_source = _problem_energies(
        basis=basis,
        linear=linear,
        quadratic=quadratic,
        objective=objective,
        feasible=feasible,
        infeasible_penalty=infeasible_penalty,
    )

    cost_offset = float(np.min(penalized))
    cost_scale = float(np.max(penalized) - cost_offset)
    if cost_scale <= 1e-15:
        cost_scale = 1.0
    scaled_cost = (penalized - cost_offset) / cost_scale

    rng = np.random.default_rng(int(seed))
    gammas, betas, ideal_probabilities, expected_energy, evaluations = _optimise_angles(
        scaled_cost=scaled_cost,
        penalized_energies=penalized,
        num_variables=n,
        p=p,
        rng=rng,
        restarts=int(optimizer_restarts),
        steps=int(optimizer_steps),
        initial_parameters=initial_parameters,
    )
    repair_applied = False
    if shots is None:
        # Ideal mode reports the circuit's modal outcome, not argmin(cost).
        # np.argmax's deterministic first-index tie break does not inspect the
        # objective or feasibility oracle.
        source_index = int(np.argmax(ideal_probabilities))
        returned_index = source_index
        measured_counts: np.ndarray | None = None
        measured_probability = float(ideal_probabilities[source_index])
        selection_mode = "ideal_statevector_argmax"
        sampling_mode = "ideal_statevector"
    else:
        measured_counts = _draw_samples(
            ideal_probabilities,
            num_variables=n,
            shots=shots,
            bitflip_probability=noise_bitflip_probability,
            rng=rng,
        )
        observed = np.flatnonzero(measured_counts)
        feasible_observed = observed[valid[observed]]
        sampling_mode = "noisy_shots" if noise_bitflip_probability > 0.0 else "shots"

        if feasible_observed.size:
            source_index = min(
                (int(index) for index in feasible_observed),
                key=lambda index: (float(reported[index]), -int(measured_counts[index]), index),
            )
            returned_index = source_index
            selection_mode = "direct_qaoa_sample"
        else:
            # The source is still a measured QAOA shot.  The penalty is equal
            # for all infeasible states, so frequency is the honest tie-breaker.
            source_index = min(
                (int(index) for index in observed),
                key=lambda index: (float(penalized[index]), -int(measured_counts[index]), index),
            )
            returned_index = source_index
            selection_mode = "direct_qaoa_infeasible_sample"
        measured_probability = float(measured_counts[source_index]) / shots

    if not bool(valid[returned_index]) and repair is not None:
        repaired_bits = tuple(int(bit) for bit in repair(_bitstring(source_index, n)))
        returned_index = _bitstring_index(repaired_bits, n)
        if not bool(valid[returned_index]):
            raise ValueError("repair did not produce a feasible state")
        repair_applied = True
        selection_mode = (
            "repaired_ideal_statevector_outcome"
            if shots is None
            else "repaired_qaoa_sample"
        )

    source_energy = float(reported[source_index]) if math.isfinite(float(reported[source_index])) else None
    returned_feasible = bool(valid[returned_index])
    returned_energy = (
        float(reported[returned_index]) if math.isfinite(float(reported[returned_index])) else float("inf")
    )
    counts = (
        {}
        if measured_counts is None
        else {
            _count_key(int(index), n): int(measured_counts[index])
            for index in np.flatnonzero(measured_counts)
        }
    )
    diagnostics: dict[str, object] = {
        "backend": "numpy_statevector",
        "execution_mode": "direct_qaoa_statevector",
        "selection_mode": selection_mode,
        "sampling_mode": sampling_mode,
        "candidate_selection_scope": (
            "statevector_probability_argmax" if shots is None else "sampled_counts_only"
        ),
        "qaoa_circuit_executed": True,
        "direct_qaoa": not repair_applied,
        "repair_applied": repair_applied,
        "returned_bitstring_was_measured": shots is not None and returned_index == source_index,
        "num_qubits": n,
        "p": p,
        "shots": shots,
        "seed": int(seed),
        "objective_source": objective_source,
        "optimizer": "multistart_coordinate_search_on_qaoa_expectation",
        "optimizer_function_evaluations": evaluations,
        "optimized_expected_energy": expected_energy,
        "ideal_feasible_probability": float(np.sum(ideal_probabilities[valid])),
        "ideal_source_probability": float(ideal_probabilities[source_index]),
        "measured_source_probability": measured_probability if shots is not None else None,
        "reported_probability_semantics": (
            "ideal_statevector_probability" if shots is None else "measured_frequency"
        ),
        "noise_model": (
            "none" if noise_bitflip_probability == 0.0 else "independent_measurement_bitflip"
        ),
        "noise_bitflip_probability": noise_bitflip_probability,
        "cost_offset": cost_offset,
        "cost_scale": cost_scale,
        "infeasible_penalty": penalty_used,
        "bit_order": "x0_to_xn_minus_1",
    }
    return QAOAResult(
        bitstring=_bitstring(returned_index, n),
        energy=returned_energy,
        probability=measured_probability,
        sampled_bitstring=_bitstring(source_index, n),
        sampled_energy=source_energy,
        is_feasible=returned_feasible,
        repaired=repair_applied,
        gammas=tuple(float(value) for value in gammas),
        betas=tuple(float(value) for value in betas),
        counts=counts,
        diagnostics=diagnostics,
    )


# A verb-oriented alias reads naturally at call sites that treat this module as
# a sampler backend rather than a scheduler.
sample_qaoa = run_qaoa


__all__ = [
    "BitString",
    "MAX_QUBITS",
    "QAOAResult",
    "run_qaoa",
    "sample_qaoa",
]
