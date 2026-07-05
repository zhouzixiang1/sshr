#!/usr/bin/env python3
"""Public synthesizer wrappers for experiments."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import BooleanFunction, QuantumCircuit  # noqa: E402
from baselines import esop_synthesize  # noqa: E402
from sshr_h import sshr_h  # noqa: E402
from sshr_beam import sshr_beam  # noqa: E402

from anf_utils import anf_monomials, shifted_function
from factor_plan import SearchConfig, direct_plan, emit_plan_to_circuit, greedy_plan, verify_oracle
from neural_policy import NeuralScorer
from nmcts_solver import NeuralMCTSSolver
from resource_model import ResourceCost


@dataclass
class SynthesisResult:
    method: str
    cost: ResourceCost
    time_s: float
    correct: bool
    terms: int
    gates: int
    n_qubits: int

    def to_row(self) -> dict:
        row = asdict(self)
        row.update(asdict(self.cost))
        row.pop("cost", None)
        return row


def circuit_resource_cost(circ: QuantumCircuit) -> ResourceCost:
    c = circ.cost()
    return ResourceCost(
        T=int(c["T"]),
        CNOT=int(c["CNOT"]),
        gates=len(circ.gates),
        depth=sum(1 if g.type in {"X", "CNOT"} else max(1, int(circ.cost()["CNOT"])) for g in []),
        explicit_ancilla=max(0, circ.n_qubits),
        peak_ancilla=int(c["ancilla"]),
    )


def _existing_circuit_cost(circ: QuantumCircuit, n_inputs: int) -> ResourceCost:
    T = CNOT = depth = 0
    peak = 0
    from bool_func import mct_cost_rp

    for g in circ.gates:
        if g.type == "X":
            d = 1
            depth += d
        elif g.type == "CNOT":
            CNOT += 1
            depth += 1
        elif g.type == "MCT":
            c = mct_cost_rp(len(g.controls))
            T += int(c["T"])
            CNOT += int(c["CNOT"])
            depth += max(1, int(c["CNOT"]))
            peak = max(peak, int(c.get("ancilla", 0)))
    explicit = max(0, circ.n_qubits - (n_inputs + 1))
    return ResourceCost(T=T, CNOT=CNOT, gates=len(circ.gates), depth=depth, explicit_ancilla=explicit, peak_ancilla=explicit + peak)


def _wrap_cost(polarity: int) -> ResourceCost:
    wraps = 2 * int(polarity).bit_count()
    return ResourceCost(gates=wraps, depth=wraps)


@lru_cache(maxsize=4)
def _cached_scorer(model_path: str):
    return NeuralScorer(model_path) if model_path else None


def _polarity_candidates(n: int, seed: int, max_polarities: int) -> list[int]:
    total = 1 << n
    if total <= max_polarities:
        return list(range(total))
    import random

    rng = random.Random(seed)
    values = {0, total - 1}
    while len(values) < max_polarities:
        values.add(rng.randrange(total))
    return sorted(values)


def _solve_plan(method: str, terms: frozenset[int], config: SearchConfig, seed: int, neural):
    if method in {"direct_anf", "fprm_direct"}:
        return direct_plan(terms, 0, 0, config)
    if method in {"greedy_factor", "neural_greedy", "fprm_greedy"}:
        return greedy_plan(terms, config=config, neural_scorer=neural if method == "neural_greedy" else None)
    if method in {"mcts_factor", "fprm_mcts"}:
        solver = NeuralMCTSSolver(config, simulations=config.mcts_simulations, seed=seed)
        return solver.solve(terms)
    if method in {"neural_mcts", "fprm_neural_mcts"}:
        solver = NeuralMCTSSolver(
            config,
            simulations=config.neural_mcts_simulations,
            seed=seed,
            neural_scorer=neural,
        )
        return solver.solve(terms)
    raise ValueError(method)


def _best_polarity_plan(method: str, bf: BooleanFunction, config: SearchConfig, seed: int, neural):
    max_pol = max(1, config.max_polarities)
    best = None
    # First rank polarities with greedy factoring; then run MCTS only on the
    # most promising few to keep large benchmarks tractable.
    ranked = []
    for polarity in _polarity_candidates(bf.n, seed, max_pol):
        shifted = shifted_function(bf, polarity)
        terms = frozenset(anf_monomials(shifted))
        greedy = greedy_plan(terms, config=config)
        score = (greedy.cost + _wrap_cost(polarity)).score(config.weights)
        ranked.append((score, polarity, terms, greedy))
    ranked.sort(key=lambda x: (x[0], int(x[1]).bit_count(), x[1]))
    trial_count = 1 if method in {"fprm_direct", "fprm_greedy"} else min(8, len(ranked))
    trials = list(ranked[:trial_count])
    if not any(polarity == 0 for _, polarity, _, _ in trials):
        for item in ranked:
            if item[1] == 0:
                trials.append(item)
                break
    for _, polarity, terms, greedy in trials:
        if method == "fprm_greedy":
            plan = greedy
        elif method == "fprm_direct":
            plan = direct_plan(terms, 0, 0, config)
        elif method == "fprm_mcts":
            solver = NeuralMCTSSolver(config, simulations=config.mcts_simulations, seed=seed)
            plan = solver.solve(terms)
        elif method == "fprm_neural_mcts":
            solver = NeuralMCTSSolver(config, simulations=config.neural_mcts_simulations, seed=seed, neural_scorer=neural)
            plan = solver.solve(terms)
        else:
            raise ValueError(method)
        cost = plan.cost + _wrap_cost(polarity)
        score = cost.score(config.weights)
        if best is None or score < best[0]:
            best = (score, polarity, terms, plan, cost)
    assert best is not None
    return best[1], best[2], best[3], best[4]


def synthesize(method: str, bf: BooleanFunction, config: SearchConfig, seed: int = 0, model_path: str | None = None) -> SynthesisResult:
    t0 = time.time()
    terms = frozenset(anf_monomials(bf))
    neural = _cached_scorer(model_path or "")

    if method in {
        "direct_anf",
        "greedy_factor",
        "neural_greedy",
        "mcts_factor",
        "neural_mcts",
    }:
        plan = _solve_plan(method, terms, config, seed, neural)
        cost = plan.cost
        polarity = 0
        circ = emit_plan_to_circuit(
            plan,
            bf.n,
            min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            polarity=polarity,
        )
    elif method in {"fprm_direct", "fprm_greedy", "fprm_mcts", "fprm_neural_mcts"}:
        polarity, terms, plan, cost = _best_polarity_plan(method, bf, config, seed, neural)
        circ = emit_plan_to_circuit(
            plan,
            bf.n,
            min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            polarity=polarity,
        )
    elif method == "esop_greedy":
        circ = esop_synthesize(bf)
        cost = _existing_circuit_cost(circ, bf.n)
    elif method == "sshr_h":
        circ = sshr_h(bf)
        cost = _existing_circuit_cost(circ, bf.n)
    elif method == "sshr_beam":
        circ = sshr_beam(bf, objective="cnot", width=30, branch=8)
        cost = _existing_circuit_cost(circ, bf.n)
    else:
        raise ValueError(method)

    dt = time.time() - t0
    correct = verify_oracle(circ, bf)
    return SynthesisResult(
        method=method,
        cost=cost,
        time_s=dt,
        correct=correct,
        terms=len(terms),
        gates=len(circ.gates),
        n_qubits=circ.n_qubits,
    )
