#!/usr/bin/env python3
"""Tests for the self-contained statevector/shot QAOA backend."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.search.qaoa_scheduler import run_qaoa


def _energy(bits, linear, quadratic) -> float:
    return sum(linear.get(i, 0.0) * bit for i, bit in enumerate(bits)) + sum(
        value * bits[i] * bits[j] for (i, j), value in quadratic.items()
    )


def _exact_test_only(num_variables, linear, quadratic):
    """Classical exact baseline for evaluating the test, never the backend."""

    candidates = [
        tuple((index >> variable) & 1 for variable in range(num_variables))
        for index in range(1 << num_variables)
    ]
    return min(candidates, key=lambda bits: _energy(bits, linear, quadratic))


def test_direct_qaoa_samples_separable_qubo_optimum() -> None:
    linear = {0: -1.0, 1: -1.0, 2: -1.0}
    quadratic = {}
    exact = _exact_test_only(3, linear, quadratic)

    result = run_qaoa(linear, quadratic, p=1, seed=7, shots=512)

    assert result.bitstring == exact == (1, 1, 1)
    assert result.energy == -3.0
    assert result.is_feasible
    assert not result.repaired
    assert result.diagnostics["execution_mode"] == "direct_qaoa_statevector"
    assert result.diagnostics["selection_mode"] == "direct_qaoa_sample"
    assert result.diagnostics["optimizer_function_evaluations"] > 1
    assert 0.0 < result.probability <= 1.0


def test_seed_reproduces_angles_samples_and_diagnostics() -> None:
    kwargs = dict(
        linear={0: -0.7, 1: 0.2, 2: -0.4},
        quadratic={(0, 1): 0.8, (1, 2): -0.3},
        p=2,
        seed=202609,
        shots=257,
        noise_bitflip_probability=0.07,
        optimizer_steps=6,
    )
    first = run_qaoa(**kwargs)
    second = run_qaoa(**kwargs)

    assert first == second
    assert sum(first.counts.values()) == 257
    assert first.diagnostics["noise_model"] == "independent_measurement_bitflip"


def test_ideal_mode_uses_statevector_argmax_and_discloses_no_measurement() -> None:
    result = run_qaoa(linear={0: -1.0, 1: -1.0}, p=1, seed=4, shots=None)

    assert result.bitstring == (1, 1)
    assert result.counts == {}
    assert result.diagnostics["sampling_mode"] == "ideal_statevector"
    assert result.diagnostics["selection_mode"] == "ideal_statevector_argmax"
    assert result.diagnostics["candidate_selection_scope"] == "statevector_probability_argmax"
    assert result.diagnostics["returned_bitstring_was_measured"] is False
    assert result.diagnostics["reported_probability_semantics"] == "ideal_statevector_probability"
    assert 0.0 < result.probability <= 1.0


def test_objective_and_feasibility_are_supported() -> None:
    def objective(bits):
        return -3.0 * bits[0] - 2.0 * bits[1] + bits[2]

    def feasible(bits):
        return sum(bits) == 2

    result = run_qaoa(
        num_variables=3,
        objective=objective,
        feasible=feasible,
        p=2,
        seed=3,
        shots=1024,
        optimizer_steps=12,
    )

    assert result.bitstring == (1, 1, 0)
    assert result.energy == -5.0
    assert result.is_feasible
    assert result.diagnostics["objective_source"] == "enumerated_objective"
    assert result.diagnostics["infeasible_penalty"] > result.energy


def test_repair_is_disclosed_and_not_counted_as_direct_sample() -> None:
    # A depth-one QAOA circuit exactly prepares the one-bit minimiser.  A
    # probability-one readout flip converts every measured 1 to 0, so repair
    # is exercised deterministically.
    result = run_qaoa(
        num_variables=1,
        objective=lambda bits: -float(sum(bits)),
        feasible=lambda bits: bits == (1,),
        p=1,
        seed=11,
        shots=256,
        noise_bitflip_probability=1.0,
        repair=lambda _bits: (1,),
    )

    assert result.sampled_bitstring == (0,)
    assert result.bitstring == (1,)
    assert result.repaired
    assert result.is_feasible
    assert result.probability == 1.0
    assert result.diagnostics["qaoa_circuit_executed"] is True
    assert result.diagnostics["direct_qaoa"] is False
    assert result.diagnostics["selection_mode"] == "repaired_qaoa_sample"
    assert result.diagnostics["repair_applied"] is True
    assert result.diagnostics["returned_bitstring_was_measured"] is False


def test_probability_one_noise_flips_measured_bits() -> None:
    clean = run_qaoa(linear={0: -1.0}, p=1, seed=5, shots=128)
    noisy = run_qaoa(
        linear={0: -1.0},
        p=1,
        seed=5,
        shots=128,
        noise_bitflip_probability=1.0,
    )

    assert clean.counts.get("1", 0) == 128
    assert noisy.counts.get("0", 0) == 128
    assert noisy.sampled_bitstring == (0,)
    assert noisy.diagnostics["noise_bitflip_probability"] == 1.0


def test_result_is_json_friendly_and_preserves_probability_semantics() -> None:
    result = run_qaoa(linear=[-1.0, 0.25], p=1, seed=8, shots=64)
    payload = result.as_dict()

    assert payload["bitstring"] == list(result.bitstring)
    assert payload["sampled_bitstring"] == list(result.sampled_bitstring)
    assert payload["probability"] == result.counts["".join(map(str, result.sampled_bitstring))] / 64
    assert math.isclose(sum(result.counts.values()), 64)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"num_variables": 13, "objective": lambda bits: 0.0}, "between 1 and 12"),
        ({"linear": [-1.0], "shots": 0}, "shots must be"),
        ({"linear": [-1.0], "noise_bitflip_probability": 1.1}, "lie in"),
        (
            {"linear": [-1.0], "objective": lambda bits: -bits[0]},
            "either QUBO coefficients or objective",
        ),
    ],
)
def test_invalid_inputs_are_rejected(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        run_qaoa(**kwargs)
