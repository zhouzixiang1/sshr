#!/usr/bin/env python3
"""Public synthesizer wrappers for experiments."""
from __future__ import annotations

import time
import json
from dataclasses import asdict, dataclass
from dataclasses import replace
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

from affine_search import affine_wrap_cost, candidate_transforms, emit_affine_wrapped, transform_function
from anf_utils import anf_monomials, shifted_function
from cube_search import cube_beam_plan, cube_greedy_plan, emit_cube_plan
from esop_milp import synthesize_esop_milp_circuit
from factor_plan import SearchConfig, affine_linear_pair_beam_plan, direct_plan, emit_plan_to_circuit, greedy_plan, linear_pair_beam_plan, linear_pair_screen_plan, root_beam_plan, root_child_beam_plan, verify_oracle
from neural_policy import NeuralScorer, RandomPriorScorer
from nmcts_solver import NeuralMCTSSolver
from resource_model import ResourceCost, ResourceWeights


STRUCTURE_GATE_MODEL = Path(__file__).resolve().parent / "models" / "resource_structure_gate.json"


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
    if model_path.startswith("random-prior:"):
        _, seed = model_path.split(":", 1)
        return RandomPriorScorer(int(seed))
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


def _ranked_polarities(
    bf: BooleanFunction,
    config: SearchConfig,
    seed: int,
    neural,
    neural_guided: bool,
) -> list[tuple[float, int, frozenset[int], object]]:
    max_pol = max(1, config.max_polarities)
    total = 1 << bf.n
    scored: dict[int, tuple[float, int, frozenset[int], object]] = {}

    def score_polarity(polarity: int) -> tuple[float, int, frozenset[int], object]:
        existing = scored.get(polarity)
        if existing is not None:
            return existing
        shifted = shifted_function(bf, polarity)
        terms = frozenset(anf_monomials(shifted))
        greedy = greedy_plan(
            terms,
            config=config,
            neural_scorer=neural if neural_guided else None,
        )
        score = (greedy.cost + _wrap_cost(polarity)).score(config.weights)
        item = (score, polarity, terms, greedy)
        scored[polarity] = item
        return item

    if total <= max_pol or not neural_guided:
        for polarity in _polarity_candidates(bf.n, seed, max_pol):
            score_polarity(polarity)
        return sorted(scored.values(), key=lambda x: (x[0], int(x[1]).bit_count(), x[1]))

    import random

    rng = random.Random(seed)
    seeds = {0, total - 1}
    while len(seeds) < min(total, max(6, max_pol // 2)):
        seeds.add(rng.randrange(total))
    for polarity in seeds:
        score_polarity(polarity)

    budget = min(total, max_pol)
    beam = max(4, min(10, max_pol // 2))
    while len(scored) < budget:
        expanded = False
        frontier = sorted(scored.values(), key=lambda x: (x[0], int(x[1]).bit_count(), x[1]))[:beam]
        for _, polarity, _, _ in frontier:
            bits = list(range(bf.n))
            rng.shuffle(bits)
            for bit in bits:
                cand = polarity ^ (1 << bit)
                if cand not in scored:
                    score_polarity(cand)
                    expanded = True
                    if len(scored) >= budget:
                        break
            if len(scored) >= budget:
                break
        if not expanded:
            while len(scored) < budget:
                score_polarity(rng.randrange(total))
                if len(scored) >= total:
                    break
            break

    return sorted(scored.values(), key=lambda x: (x[0], int(x[1]).bit_count(), x[1]))[:max_pol]


def _direct_screened_polarities(
    bf: BooleanFunction,
    config: SearchConfig,
    seed: int,
    budget: int,
    top_k: int,
) -> list[tuple[float, int, frozenset[int], object]]:
    """Rank many polarities by direct-cost screening before expensive planning."""
    import random

    total = 1 << bf.n
    rng = random.Random(seed)
    values = {0, total - 1}
    for bit in range(bf.n):
        values.add(1 << bit)
        values.add((total - 1) ^ (1 << bit))
    while len(values) < min(total, budget):
        values.add(rng.randrange(total))

    scored = []
    for polarity in values:
        shifted = shifted_function(bf, polarity)
        terms = frozenset(anf_monomials(shifted))
        direct = direct_plan(terms, 0, 0, config).cost + _wrap_cost(polarity)
        scored.append((direct.score(config.weights), polarity, terms, None))
    scored.sort(key=lambda x: (x[0], len(x[2]), int(x[1]).bit_count(), x[1]))
    selected = []
    seen = set()
    for item in scored:
        if item[1] in seen:
            continue
        selected.append(item)
        seen.add(item[1])
        if len(selected) >= top_k:
            break
    if 0 not in seen:
        for item in scored:
            if item[1] == 0:
                selected.append(item)
                break
    return selected


def _solve_plan(method: str, terms: frozenset[int], config: SearchConfig, seed: int, neural):
    if method in {"direct_anf", "fprm_direct"}:
        return direct_plan(terms, 0, 0, config)
    if method in {"greedy_factor", "neural_greedy", "fprm_greedy"}:
        return greedy_plan(terms, config=config, neural_scorer=neural if method == "neural_greedy" else None)
    if method in {"root_beam_factor", "fprm_root_beam"}:
        return root_beam_plan(terms, config=config, neural_scorer=neural if method == "root_beam_factor" else None)
    if method == "boolean_linear_pair_screen":
        return linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
    if method == "boolean_linear_pair_screen_deep":
        return linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            recursive_depth=1,
            boolean_ring=True,
        )
    if method == "boolean_linear_pair_screen_deeper":
        return linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            recursive_depth=2,
            boolean_ring=True,
        )
    if method == "boolean_linear_pair_screen_adaptive":
        candidates = [
            linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True),
            linear_pair_screen_plan(
                terms,
                config=config,
                action_width=6,
                recursive_depth=1,
                boolean_ring=True,
            ),
            linear_pair_screen_plan(
                terms,
                config=config,
                action_width=6,
                recursive_depth=2,
                boolean_ring=True,
            ),
        ]
        return min(candidates, key=lambda p: p.score(config.weights))
    if method == "boolean_linear_pair_screen_neural":
        return linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            boolean_ring=True,
            neural_scorer=neural,
        )
    if method == "boolean_linear_pair_screen_deep_neural":
        return linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            recursive_depth=1,
            boolean_ring=True,
            neural_scorer=neural,
        )
    if method == "boolean_linear_pair_screen_ai_guard":
        baseline = linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
        neural_plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            boolean_ring=True,
            neural_scorer=neural,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "boolean_linear_pair_screen_deep_ai_guard":
        baseline = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            recursive_depth=1,
            boolean_ring=True,
        )
        neural_plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            recursive_depth=1,
            boolean_ring=True,
            neural_scorer=neural,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "fprm_root_child_beam":
        return root_child_beam_plan(terms, config=config)
    if method == "fprm_linear_pair":
        return linear_pair_beam_plan(terms, config=config)
    if method == "fprm_linear_pair_wide":
        return linear_pair_beam_plan(terms, config=config, action_width=12)
    if method == "fprm_linear_pair_wide_fast":
        return linear_pair_beam_plan(
            terms,
            config=config,
            action_width=12,
            rest_greedy_term_limit=450,
            use_root_child_baseline=False,
        )
    if method == "fprm_linear_pair_fast":
        return linear_pair_beam_plan(
            terms,
            config=config,
            action_width=2,
            rest_greedy_term_limit=450,
            use_root_child_baseline=False,
        )
    if method == "fprm_linear_pair_deep":
        return linear_pair_beam_plan(terms, config=config, recursive_depth=1)
    if method == "fprm_linear_pair_deep_ai_guard":
        baseline = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
        neural_plan = linear_pair_beam_plan(
            terms,
            config=config,
            recursive_depth=1,
            neural_scorer=neural,
            root_neural_only=True,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "fprm_linear_pair_deep_root_neural_wide":
        return linear_pair_beam_plan(
            terms,
            config=config,
            action_width=8,
            recursive_depth=1,
            neural_scorer=neural,
            root_neural_only=True,
        )
    if method == "fprm_linear_pair_deep_ai_guard_wide":
        baseline = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
        neural_plan = linear_pair_beam_plan(
            terms,
            config=config,
            action_width=8,
            recursive_depth=1,
            neural_scorer=neural,
            root_neural_only=True,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "fprm_linear_pair_deep_wide":
        return linear_pair_beam_plan(terms, config=config, action_width=12, recursive_depth=1)
    if method == "fprm_boolean_linear_pair":
        return linear_pair_beam_plan(terms, config=config, boolean_ring=True)
    if method == "fprm_boolean_linear_pair_deep":
        return linear_pair_beam_plan(terms, config=config, recursive_depth=1, boolean_ring=True)
    if method == "fprm_boolean_linear_pair_deep_neural":
        return linear_pair_beam_plan(
            terms,
            config=config,
            recursive_depth=1,
            boolean_ring=True,
            neural_scorer=neural,
        )
    if method == "fprm_boolean_linear_pair_deep_root_neural":
        return linear_pair_beam_plan(
            terms,
            config=config,
            recursive_depth=1,
            boolean_ring=True,
            neural_scorer=neural,
            root_neural_only=True,
        )
    if method == "fprm_boolean_linear_pair_deep_ai_guard":
        baseline = linear_pair_beam_plan(terms, config=config, recursive_depth=1, boolean_ring=True)
        neural_plan = linear_pair_beam_plan(
            terms,
            config=config,
            recursive_depth=1,
            boolean_ring=True,
            neural_scorer=neural,
            root_neural_only=True,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "fprm_boolean_linear_pair_screen":
        return linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
    if method == "fprm_boolean_linear_pair_screen_neural":
        return linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            boolean_ring=True,
            neural_scorer=neural,
        )
    if method == "fprm_boolean_linear_pair_screen_ai_guard":
        baseline = linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
        neural_plan = linear_pair_screen_plan(
            terms,
            config=config,
            action_width=6,
            boolean_ring=True,
            neural_scorer=neural,
        )
        return min([baseline, neural_plan], key=lambda p: p.score(config.weights))
    if method == "fprm_linear_parity":
        return linear_pair_beam_plan(terms, config=config, max_linear_width=3)
    if method == "fprm_affine_linear_pair":
        return affine_linear_pair_beam_plan(terms, config=config)
    if method == "fprm_affine_linear_pair_deep":
        return affine_linear_pair_beam_plan(terms, config=config, recursive_depth=1)
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
    best = None
    neural_guided = method == "fprm_neural_mcts" and neural is not None
    # First rank polarities with fast factored plans; then run MCTS only on the
    # most promising few to keep large benchmarks tractable.  The neural-guided
    # path uses local search in polarity space, so the prior changes which
    # fixed-polarity Reed-Muller forms are explored rather than only reordering
    # factor actions inside a fixed polarity.
    if method in {
        "fprm_root_beam",
        "fprm_root_child_beam",
        "fprm_linear_pair",
        "fprm_linear_pair_wide",
        "fprm_linear_pair_wide_fast",
        "fprm_linear_pair_neural",
        "fprm_linear_pair_root_neural",
        "fprm_linear_pair_fast",
        "fprm_linear_pair_fast_neural",
        "fprm_linear_pair_fast_root_neural",
        "fprm_linear_pair_deep",
        "fprm_linear_pair_deep_ai_guard",
        "fprm_linear_pair_deep_ai_guard_wide",
        "fprm_linear_pair_deep_wide",
        "fprm_linear_pair_deep_neural",
        "fprm_linear_pair_deep_root_neural",
        "fprm_linear_pair_deep_root_neural_wide",
        "fprm_boolean_linear_pair",
        "fprm_boolean_linear_pair_deep",
        "fprm_boolean_linear_pair_deep_neural",
        "fprm_boolean_linear_pair_deep_root_neural",
        "fprm_boolean_linear_pair_deep_ai_guard",
        "fprm_boolean_linear_pair_screen",
        "fprm_boolean_linear_pair_screen_neural",
        "fprm_boolean_linear_pair_screen_ai_guard",
        "fprm_linear_parity",
        "fprm_affine_linear_pair",
        "fprm_affine_linear_pair_deep",
    } and bf.n > 12 and len(anf_monomials(bf)) > 128:
        if bf.n >= 16:
            screen_budget = max(8, min(16, 2 * max(1, config.max_polarities)))
            screen_top_k = 1
        else:
            screen_budget = max(32, min(64, 4 * max(1, config.max_polarities)))
            screen_top_k = 2
        ranked = _direct_screened_polarities(
            bf,
            config,
            seed,
            budget=screen_budget,
            top_k=screen_top_k,
        )
        trials = list(ranked)
    elif neural_guided:
        baseline_ranked = _ranked_polarities(bf, config, seed, neural=None, neural_guided=False)
        neural_ranked = _ranked_polarities(bf, config, seed, neural=neural, neural_guided=True)
        trials = []
        seen = set()

        def add_trials(items, limit):
            for item in items:
                polarity = item[1]
                if polarity in seen:
                    continue
                trials.append(item)
                seen.add(polarity)
                if len(trials) >= limit:
                    break

        add_trials(baseline_ranked[: min(8, len(baseline_ranked))], 8)
        add_trials(neural_ranked, min(12, len(baseline_ranked) + len(neural_ranked)))
        ranked = baseline_ranked + [item for item in neural_ranked if item[1] not in {x[1] for x in baseline_ranked}]
    else:
        ranked = _ranked_polarities(bf, config, seed, neural, neural_guided)
        trial_count = 1 if method in {"fprm_direct", "fprm_greedy", "fprm_root_beam"} else min(8, len(ranked))
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
        elif method == "fprm_root_beam":
            plan = root_beam_plan(terms, config=config)
        elif method == "fprm_root_child_beam":
            plan = root_child_beam_plan(terms, config=config)
        elif method == "fprm_linear_pair":
            plan = linear_pair_beam_plan(terms, config=config)
        elif method == "fprm_linear_pair_wide":
            plan = linear_pair_beam_plan(terms, config=config, action_width=12)
        elif method == "fprm_linear_pair_wide_fast":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=12,
                rest_greedy_term_limit=450,
                use_root_child_baseline=False,
            )
        elif method == "fprm_linear_pair_neural":
            plan = linear_pair_beam_plan(terms, config=config, neural_scorer=neural)
        elif method == "fprm_linear_pair_root_neural":
            plan = linear_pair_beam_plan(terms, config=config, neural_scorer=neural, root_neural_only=True)
        elif method == "fprm_linear_pair_fast":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=2,
                rest_greedy_term_limit=450,
                use_root_child_baseline=False,
            )
        elif method == "fprm_linear_pair_fast_neural":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=2,
                neural_scorer=neural,
                rest_greedy_term_limit=450,
                use_root_child_baseline=False,
            )
        elif method == "fprm_linear_pair_fast_root_neural":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=2,
                neural_scorer=neural,
                rest_greedy_term_limit=450,
                use_root_child_baseline=False,
                root_neural_only=True,
            )
        elif method == "fprm_linear_pair_deep":
            plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
        elif method == "fprm_linear_pair_deep_ai_guard":
            baseline_plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
            neural_plan = linear_pair_beam_plan(
                terms,
                config=config,
                recursive_depth=1,
                neural_scorer=neural,
                root_neural_only=True,
            )
            plan = min(
                [baseline_plan, neural_plan],
                key=lambda p: (p.cost + _wrap_cost(polarity)).score(config.weights),
            )
        elif method == "fprm_linear_pair_deep_root_neural_wide":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=8,
                recursive_depth=1,
                neural_scorer=neural,
                root_neural_only=True,
            )
        elif method == "fprm_linear_pair_deep_ai_guard_wide":
            baseline_plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
            neural_plan = linear_pair_beam_plan(
                terms,
                config=config,
                action_width=8,
                recursive_depth=1,
                neural_scorer=neural,
                root_neural_only=True,
            )
            plan = min(
                [baseline_plan, neural_plan],
                key=lambda p: (p.cost + _wrap_cost(polarity)).score(config.weights),
            )
        elif method == "fprm_linear_pair_deep_wide":
            plan = linear_pair_beam_plan(terms, config=config, action_width=12, recursive_depth=1)
        elif method == "fprm_linear_pair_deep_neural":
            plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1, neural_scorer=neural)
        elif method == "fprm_linear_pair_deep_root_neural":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                recursive_depth=1,
                neural_scorer=neural,
                root_neural_only=True,
            )
        elif method == "fprm_boolean_linear_pair":
            plan = linear_pair_beam_plan(terms, config=config, boolean_ring=True)
        elif method == "fprm_boolean_linear_pair_deep":
            plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1, boolean_ring=True)
        elif method == "fprm_boolean_linear_pair_deep_neural":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                recursive_depth=1,
                boolean_ring=True,
                neural_scorer=neural,
            )
        elif method == "fprm_boolean_linear_pair_deep_root_neural":
            plan = linear_pair_beam_plan(
                terms,
                config=config,
                recursive_depth=1,
                boolean_ring=True,
                neural_scorer=neural,
                root_neural_only=True,
            )
        elif method == "fprm_boolean_linear_pair_deep_ai_guard":
            baseline_plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1, boolean_ring=True)
            neural_plan = linear_pair_beam_plan(
                terms,
                config=config,
                recursive_depth=1,
                boolean_ring=True,
                neural_scorer=neural,
                root_neural_only=True,
            )
            plan = min(
                [baseline_plan, neural_plan],
                key=lambda p: (p.cost + _wrap_cost(polarity)).score(config.weights),
            )
        elif method == "fprm_boolean_linear_pair_screen":
            plan = linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
        elif method == "fprm_boolean_linear_pair_screen_neural":
            plan = linear_pair_screen_plan(
                terms,
                config=config,
                action_width=6,
                boolean_ring=True,
                neural_scorer=neural,
            )
        elif method == "fprm_boolean_linear_pair_screen_ai_guard":
            baseline_plan = linear_pair_screen_plan(terms, config=config, action_width=6, boolean_ring=True)
            neural_plan = linear_pair_screen_plan(
                terms,
                config=config,
                action_width=6,
                boolean_ring=True,
                neural_scorer=neural,
            )
            plan = min(
                [baseline_plan, neural_plan],
                key=lambda p: (p.cost + _wrap_cost(polarity)).score(config.weights),
            )
        elif method == "fprm_linear_parity":
            plan = linear_pair_beam_plan(terms, config=config, max_linear_width=3)
        elif method == "fprm_affine_linear_pair":
            plan = affine_linear_pair_beam_plan(terms, config=config)
        elif method == "fprm_affine_linear_pair_deep":
            plan = affine_linear_pair_beam_plan(terms, config=config, recursive_depth=1)
        elif method == "fprm_mcts":
            solver = NeuralMCTSSolver(config, simulations=config.mcts_simulations, seed=seed)
            plan = solver.solve(terms)
        elif method == "fprm_neural_mcts":
            baseline_solver = NeuralMCTSSolver(config, simulations=config.mcts_simulations, seed=seed)
            baseline_plan = baseline_solver.solve(terms)
            neural_solver = NeuralMCTSSolver(
                config,
                simulations=config.neural_mcts_simulations,
                seed=seed,
                neural_scorer=neural,
            )
            neural_plan = neural_solver.solve(terms)
            plan = min(
                [baseline_plan, neural_plan],
                key=lambda p: (p.cost + _wrap_cost(polarity)).score(config.weights),
            )
        else:
            raise ValueError(method)
        cost = plan.cost + _wrap_cost(polarity)
        score = cost.score(config.weights)
        if best is None or score < best[0]:
            best = (score, polarity, terms, plan, cost)
    assert best is not None
    return best[1], best[2], best[3], best[4]


def _best_ranked_polarity_archive(bf: BooleanFunction, config: SearchConfig, seed: int, neural):
    """Evaluate a compact archive after exhaustive polarity ranking on small functions."""
    archive_config = replace(config, max_polarities=max(config.max_polarities, 1 << bf.n))
    methods = [
        "fprm_greedy",
        "fprm_root_child_beam",
        "fprm_linear_pair",
        "fprm_affine_linear_pair",
    ]
    if config.max_factor_ancilla >= 2:
        methods.append("fprm_linear_pair_deep")
        methods.append("fprm_affine_linear_pair_deep")
    best = None
    for method in methods:
        try:
            polarity, terms, plan, cost = _best_polarity_plan(method, bf, archive_config, seed, neural)
        except Exception:
            continue
        score = cost.score(config.weights)
        item = (score, polarity, terms, plan, cost)
        if best is None or score < best[0]:
            best = item
    if best is None:
        terms = frozenset(anf_monomials(bf))
        plan = direct_plan(terms, 0, 0, config)
        best = (plan.cost.score(config.weights), 0, terms, plan, plan.cost)
    return best[1], best[2], best[3], best[4]


def _best_affine_plan(
    bf: BooleanFunction,
    config: SearchConfig,
    seed: int,
    neural,
    use_neural_refine: bool = True,
    use_guard: bool = True,
):
    best = None
    if bf.n <= 5:
        affine_budget = 10
        rank_polarities = 8
        rank_mcts = 16
        rank_neural_mcts = 20
        trial_limit = 3
        term_cap = None
    elif bf.n <= 6:
        affine_budget = 4
        rank_polarities = 6
        rank_mcts = 12
        rank_neural_mcts = 16
        trial_limit = 2
        term_cap = None
    elif bf.n <= 8:
        affine_budget = 2
        rank_polarities = 2
        rank_mcts = 8
        rank_neural_mcts = 10
        trial_limit = 1
        term_cap = 160
    else:
        affine_budget = 4 if not use_neural_refine else 1
        rank_polarities = 1
        rank_mcts = 6
        rank_neural_mcts = 8
        trial_limit = 1
        term_cap = 2200 if not use_neural_refine else 220
    budget = max(1, min(config.max_polarities, affine_budget))
    rank_config = replace(
        config,
        max_polarities=max(1, min(config.max_polarities, rank_polarities)),
        candidate_top_k=min(config.candidate_top_k, 16 if bf.n <= 6 else 10),
        mcts_simulations=max(1, min(config.mcts_simulations, rank_mcts)),
        neural_mcts_simulations=max(1, min(config.neural_mcts_simulations, rank_neural_mcts)),
    )
    ranked = []
    for transform in candidate_transforms(bf.n, seed, budget):
        shifted_bf = transform_function(bf, transform.rows)
        shifted_terms = frozenset(anf_monomials(shifted_bf))
        if term_cap is not None and len(shifted_terms) > term_cap and transform.rows != tuple(1 << i for i in range(bf.n)):
            continue
        try:
            polarity, terms, plan, cost = _best_polarity_plan("fprm_greedy", shifted_bf, rank_config, seed, neural)
        except Exception:
            continue
        total_cost = cost + affine_wrap_cost(transform.rows)
        ranked.append((total_cost.score(config.weights), transform, shifted_bf, polarity, terms, plan, total_cost))
    ranked.sort(key=lambda x: x[0])
    if (bf.n >= 6 or not use_neural_refine) and ranked:
        _, transform, _, polarity, terms, plan, total_cost = ranked[0]
        best = (total_cost.score(config.weights), transform, bf, polarity, terms, plan, total_cost)
    else:
        trials = ranked[: max(1, min(trial_limit, len(ranked)))]
        for _, transform, shifted_bf, _, _, _, _ in trials:
            try:
                polarity, terms, plan, cost = _best_polarity_plan("fprm_neural_mcts", shifted_bf, rank_config, seed, neural)
            except Exception:
                continue
            total_cost = cost + affine_wrap_cost(transform.rows)
            score = total_cost.score(config.weights)
            if best is None or score < best[0]:
                best = (score, transform, shifted_bf, polarity, terms, plan, total_cost)
    if best is None:
        terms = frozenset(anf_monomials(bf))
        solver = NeuralMCTSSolver(rank_config, simulations=rank_config.mcts_simulations, seed=seed)
        plan = solver.solve(terms)
        best = (plan.cost.score(config.weights), candidate_transforms(bf.n, seed, 1)[0], bf, 0, terms, plan, plan.cost)
    if use_guard and bf.n <= 12:
        try:
            terms = frozenset(anf_monomials(bf))
            solver = NeuralMCTSSolver(config, simulations=config.mcts_simulations, seed=seed)
            plan = solver.solve(terms)
            score = plan.cost.score(config.weights)
            if score < best[0]:
                best = (score, candidate_transforms(bf.n, seed, 1)[0], bf, 0, terms, plan, plan.cost)
        except Exception:
            pass
    return best[1], best[3], best[4], best[5], best[6]


def _profile_candidate_configs(config: SearchConfig) -> list[tuple[str, SearchConfig]]:
    """Return diverse bounded configs for resource-profile candidate generation."""
    base = replace(
        config,
        candidate_top_k=min(config.candidate_top_k, 18),
        mcts_simulations=min(config.mcts_simulations, 32),
        neural_mcts_simulations=min(config.neural_mcts_simulations, 40),
        max_polarities=min(config.max_polarities, 16),
    )
    configs: list[tuple[str, SearchConfig]] = [("base", base)]

    if config.max_factor_ancilla >= 2:
        configs.append(
            (
                "t_aggressive",
                replace(
                    config,
                    max_factor_size=min(max(config.max_factor_size, 6), 6),
                    candidate_top_k=min(max(config.candidate_top_k, 28), 32),
                    greedy_eval_limit=2,
                    max_polarities=min(max(config.max_polarities, 18), 24),
                    mcts_simulations=min(max(config.mcts_simulations, 28), 40),
                    neural_mcts_simulations=min(max(config.neural_mcts_simulations, 36), 48),
                ),
            )
        )

    configs.append(
        (
            "cnot_depth",
            replace(
                config,
                max_factor_ancilla=min(config.max_factor_ancilla, 2),
                max_factor_size=min(config.max_factor_size, 3),
                candidate_top_k=min(config.candidate_top_k, 16),
                greedy_eval_limit=2,
                max_polarities=min(config.max_polarities, 10),
                mcts_simulations=min(config.mcts_simulations, 24),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 32),
            ),
        )
    )
    configs.append(
        (
            "ancilla_tight",
            replace(
                config,
                max_factor_ancilla=min(config.max_factor_ancilla, 1),
                max_factor_size=min(config.max_factor_size, 3),
                candidate_top_k=min(config.candidate_top_k, 14),
                greedy_eval_limit=1,
                max_polarities=min(config.max_polarities, 8),
                mcts_simulations=min(config.mcts_simulations, 20),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 24),
            ),
        )
    )

    deduped: list[tuple[str, SearchConfig]] = []
    seen = set()
    for label, cfg in configs:
        key = (
            cfg.max_factor_ancilla,
            cfg.max_factor_size,
            cfg.candidate_top_k,
            cfg.greedy_eval_limit,
            cfg.max_polarities,
            cfg.mcts_simulations,
            cfg.neural_mcts_simulations,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, cfg))
    return deduped


def _pareto_candidate_configs(config: SearchConfig) -> list[tuple[str, SearchConfig]]:
    """Return configs optimized under intentionally different resource weights.

    The ordinary profile portfolio mostly changes search budgets.  These
    configs also change the scoring weights used inside the child searches, so
    the collected candidate set approximates a small Pareto archive rather than
    only a replicated weighted-score search.
    """
    base_top_k = max(10, min(config.candidate_top_k, 24))
    configs: list[tuple[str, SearchConfig]] = [
        (
            "active",
            replace(
                config,
                candidate_top_k=base_top_k,
                mcts_simulations=min(config.mcts_simulations, 32),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 40),
                max_polarities=min(config.max_polarities, 16),
            ),
        ),
        (
            "t_sparse",
            replace(
                config,
                weights=ResourceWeights(t=1.0, cnot=0.008, depth=0.003, gates=0.003, ancilla=0.6),
                max_factor_ancilla=config.max_factor_ancilla,
                max_factor_size=min(max(config.max_factor_size, 6), 6),
                candidate_top_k=min(max(base_top_k, 28), 32),
                greedy_eval_limit=2,
                max_polarities=min(max(config.max_polarities, 18), 24),
                mcts_simulations=min(max(config.mcts_simulations, 28), 40),
                neural_mcts_simulations=min(max(config.neural_mcts_simulations, 36), 48),
            ),
        ),
        (
            "cnot_depth",
            replace(
                config,
                weights=ResourceWeights(t=0.45, cnot=0.45, depth=0.20, gates=0.02, ancilla=1.2),
                max_factor_ancilla=min(config.max_factor_ancilla, 2),
                max_factor_size=min(config.max_factor_size, 3),
                candidate_top_k=min(base_top_k, 18),
                greedy_eval_limit=2,
                max_polarities=min(config.max_polarities, 10),
                mcts_simulations=min(config.mcts_simulations, 24),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 32),
            ),
        ),
        (
            "ancilla_tight",
            replace(
                config,
                weights=ResourceWeights(t=0.80, cnot=0.04, depth=0.015, gates=0.01, ancilla=20.0),
                max_factor_ancilla=min(config.max_factor_ancilla, 1),
                max_factor_size=min(config.max_factor_size, 3),
                candidate_top_k=min(base_top_k, 14),
                greedy_eval_limit=1,
                max_polarities=min(config.max_polarities, 8),
                mcts_simulations=min(config.mcts_simulations, 20),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 24),
            ),
        ),
        (
            "gate_slim",
            replace(
                config,
                weights=ResourceWeights(t=0.65, cnot=0.08, depth=0.03, gates=0.25, ancilla=2.0),
                max_factor_ancilla=min(config.max_factor_ancilla, 2),
                max_factor_size=min(config.max_factor_size, 4),
                candidate_top_k=min(base_top_k, 18),
                greedy_eval_limit=2,
                max_polarities=min(config.max_polarities, 10),
                mcts_simulations=min(config.mcts_simulations, 24),
                neural_mcts_simulations=min(config.neural_mcts_simulations, 32),
            ),
        ),
    ]

    deduped: list[tuple[str, SearchConfig]] = []
    seen = set()
    for label, cfg in configs:
        key = _config_key(cfg)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, cfg))
    return deduped


def _highdim_pareto_candidate_configs(config: SearchConfig, n: int) -> list[tuple[str, SearchConfig]]:
    """Return bounded multi-objective configs for n>12 ANF stress tests.

    The small-function Pareto archive can afford nested affine/MCTS candidates.
    High-dimensional random ANFs cannot: the useful diversity comes from
    scoring the same bounded FPRM/root/linear candidate families under
    intentionally different resource weights.  For n>=18 we keep only two
    configs so that the root-beam verification boundary remains tractable.
    """
    base_top_k = max(8, min(config.candidate_top_k, 24))
    active = (
        "active",
        replace(
            config,
            candidate_top_k=base_top_k,
            max_polarities=min(config.max_polarities, 12),
            mcts_simulations=min(config.mcts_simulations, 24),
            neural_mcts_simulations=min(config.neural_mcts_simulations, 32),
        ),
    )
    cnot_depth = (
        "cnot_depth",
        replace(
            config,
            weights=ResourceWeights(t=0.20, cnot=0.70, depth=0.35, gates=0.02, ancilla=1.0),
            max_factor_ancilla=min(config.max_factor_ancilla, 2),
            max_factor_size=min(config.max_factor_size, 3),
            candidate_top_k=min(base_top_k, 14),
            greedy_eval_limit=2,
            max_polarities=min(config.max_polarities, 8),
            mcts_simulations=min(config.mcts_simulations, 20),
            neural_mcts_simulations=min(config.neural_mcts_simulations, 24),
        ),
    )
    if n >= 18:
        configs = [active, cnot_depth]
    else:
        configs = [
            active,
            (
                "t_sparse",
                replace(
                    config,
                    weights=ResourceWeights(t=1.0, cnot=0.008, depth=0.003, gates=0.003, ancilla=0.6),
                    max_factor_size=min(max(config.max_factor_size, 6), 6),
                    candidate_top_k=min(max(base_top_k, 24), 28),
                    greedy_eval_limit=2,
                    max_polarities=min(max(config.max_polarities, 12), 16),
                    mcts_simulations=min(max(config.mcts_simulations, 24), 32),
                    neural_mcts_simulations=min(max(config.neural_mcts_simulations, 32), 40),
                ),
            ),
            cnot_depth,
            (
                "depth_first",
                replace(
                    config,
                    weights=ResourceWeights(t=0.08, cnot=0.30, depth=1.0, gates=0.01, ancilla=0.8),
                    max_factor_ancilla=min(config.max_factor_ancilla, 1),
                    max_factor_size=min(config.max_factor_size, 3),
                    candidate_top_k=min(base_top_k, 10),
                    greedy_eval_limit=1,
                    max_polarities=min(config.max_polarities, 6),
                    mcts_simulations=min(config.mcts_simulations, 16),
                    neural_mcts_simulations=min(config.neural_mcts_simulations, 20),
                ),
            ),
            (
                "ancilla_tight",
                replace(
                    config,
                    weights=ResourceWeights(t=0.80, cnot=0.04, depth=0.015, gates=0.01, ancilla=20.0),
                    max_factor_ancilla=min(config.max_factor_ancilla, 1),
                    max_factor_size=min(config.max_factor_size, 3),
                    candidate_top_k=min(base_top_k, 10),
                    greedy_eval_limit=1,
                    max_polarities=min(config.max_polarities, 6),
                    mcts_simulations=min(config.mcts_simulations, 16),
                    neural_mcts_simulations=min(config.neural_mcts_simulations, 20),
                ),
            ),
        ]

    deduped: list[tuple[str, SearchConfig]] = []
    seen = set()
    for label, cfg in configs:
        key = _config_key(cfg)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, cfg))
    return deduped


def _resource_dims(result: SynthesisResult) -> tuple[int, int, int, int, int]:
    return (
        result.cost.T,
        result.cost.CNOT,
        result.cost.depth,
        result.cost.gates,
        result.cost.peak_ancilla,
    )


def _dominates(lhs: SynthesisResult, rhs: SynthesisResult) -> bool:
    left = _resource_dims(lhs)
    right = _resource_dims(rhs)
    return all(a <= b for a, b in zip(left, right)) and any(a < b for a, b in zip(left, right))


def _pareto_front(portfolio: list[SynthesisResult]) -> list[SynthesisResult]:
    front: list[SynthesisResult] = []
    best_by_dims: dict[tuple[int, int, int, int, int], SynthesisResult] = {}
    for item in portfolio:
        dims = _resource_dims(item)
        existing = best_by_dims.get(dims)
        if existing is None or item.time_s < existing.time_s:
            best_by_dims[dims] = item
    unique = list(best_by_dims.values())
    for item in unique:
        if not any(other is not item and _dominates(other, item) for other in unique):
            front.append(item)
    return front or portfolio


def _config_key(cfg: SearchConfig) -> tuple:
    weights = cfg.weights
    return (
        cfg.max_factor_ancilla,
        cfg.max_factor_size,
        cfg.candidate_top_k,
        cfg.greedy_eval_limit,
        cfg.max_polarities,
        cfg.mcts_simulations,
        cfg.neural_mcts_simulations,
        cfg.gate_mode,
        weights.t,
        weights.cnot,
        weights.depth,
        weights.gates,
        weights.ancilla,
    )


def _resource_selection_key(result: SynthesisResult, weights) -> tuple[float, int, int, int, int]:
    score = result.cost.score(weights)
    if weights.ancilla >= max(4.0, 4.0 * weights.t):
        return (score, result.cost.peak_ancilla, result.cost.T, result.cost.CNOT, result.cost.depth)
    if weights.cnot >= 0.10 or weights.depth >= 0.05:
        return (score, result.cost.CNOT, result.cost.depth, result.cost.T, result.cost.peak_ancilla)
    return (score, result.cost.T, result.cost.CNOT, result.cost.depth, result.cost.peak_ancilla)


@lru_cache(maxsize=1)
def _load_structure_gate_model() -> dict:
    if not STRUCTURE_GATE_MODEL.exists():
        return {"kind": "fallback_scale_gate", "feature": "n", "threshold": 20.0, "skip_if_ge": True}
    return json.loads(STRUCTURE_GATE_MODEL.read_text(encoding="utf-8"))


def _structure_gate_features(
    bf: BooleanFunction,
    screen: SynthesisResult,
    single_screen: SynthesisResult,
    weights: ResourceWeights,
) -> dict[str, float]:
    def pct(target: float, baseline: float) -> float:
        return (target - baseline) / max(baseline, 1.0) * 100.0

    return {
        "n": float(bf.n),
        "anf_terms": float(screen.terms),
        "terms_per_var": float(screen.terms) / max(float(bf.n), 1.0),
        "screen_score": screen.cost.score(weights),
        "screen_T": float(screen.cost.T),
        "screen_CNOT": float(screen.cost.CNOT),
        "screen_depth": float(screen.cost.depth),
        "screen_peak_ancilla": float(screen.cost.peak_ancilla),
        "screen_vs_single_score_pct": pct(
            screen.cost.score(weights),
            single_screen.cost.score(weights),
        ),
    }


def _structure_gate_skip_resource(features: dict[str, float]) -> bool:
    model = _load_structure_gate_model()
    feature = str(model.get("feature", "n"))
    threshold = float(model.get("threshold", 20.0))
    skip_if_ge = bool(model.get("skip_if_ge", True))
    value = float(features.get(feature, 0.0))
    return value >= threshold if skip_if_ge else value < threshold


def _structure_gate_static_skip_resource(bf: BooleanFunction) -> bool | None:
    model = _load_structure_gate_model()
    feature = str(model.get("feature", "n"))
    if feature != "n":
        return None
    threshold = float(model.get("threshold", 20.0))
    skip_if_ge = bool(model.get("skip_if_ge", True))
    value = float(bf.n)
    return value >= threshold if skip_if_ge else value < threshold


def _portfolio_result(
    requested_method: str,
    portfolio: list[SynthesisResult],
    weights: ResourceWeights,
    elapsed_s: float,
) -> SynthesisResult:
    if not portfolio:
        raise RuntimeError(f"{requested_method} portfolio produced no correct candidate")
    best = min(portfolio, key=lambda r: _resource_selection_key(r, weights))
    return SynthesisResult(
        method=requested_method,
        cost=best.cost,
        time_s=elapsed_s,
        correct=best.correct,
        terms=best.terms,
        gates=best.gates,
        n_qubits=best.n_qubits,
    )


def _run_child_portfolio(
    bf: BooleanFunction,
    child_specs: list[tuple[str, SearchConfig]],
    seed: int,
    model_path: str | None,
) -> list[SynthesisResult]:
    portfolio: list[SynthesisResult] = []
    seen_specs = set()
    for child_method, child_config in child_specs:
        key = (child_method, _config_key(child_config))
        if key in seen_specs:
            continue
        seen_specs.add(key)
        try:
            child = synthesize(child_method, bf, child_config, seed=seed, model_path=model_path)
        except TimeoutError:
            if portfolio:
                break
            raise
        except Exception:
            continue
        if child.correct:
            portfolio.append(child)
    return portfolio


def synthesize(method: str, bf: BooleanFunction, config: SearchConfig, seed: int = 0, model_path: str | None = None) -> SynthesisResult:
    t0 = time.time()
    requested_method = method
    if method.startswith("and_"):
        config = replace(config, gate_mode="logical_and")
        method = method[len("and_") :]
    if method in {"resource_heuristic", "resource_no_mcts", "resource_beam_only"}:
        fast_config = replace(
            config,
            candidate_top_k=min(config.candidate_top_k, 18),
            mcts_simulations=min(config.mcts_simulations, 32),
            neural_mcts_simulations=min(config.neural_mcts_simulations, 40),
            max_polarities=min(config.max_polarities, 16),
        )
        cube_config = replace(
            config,
            candidate_top_k=min(config.candidate_top_k, 18),
            max_polarities=min(config.max_polarities, 8),
        )
        highdim_config = replace(fast_config, candidate_top_k=config.candidate_top_k)
        if method == "resource_heuristic":
            child_specs: list[tuple[str, SearchConfig]] = [
                ("direct_anf", config),
                ("fprm_greedy", fast_config),
            ]
            if bf.n <= 12:
                child_specs.append(("affine_greedy", fast_config))
        elif method == "resource_beam_only":
            child_specs = [
                ("direct_anf", config),
                ("fprm_root_beam", fast_config),
            ]
            if bf.n <= 15:
                child_specs.append(("fprm_linear_pair", highdim_config))
            if bf.n <= 6:
                child_specs.append(("cube_beam", cube_config))
        else:
            child_specs = [
                ("direct_anf", config),
                ("fprm_greedy", fast_config),
                ("fprm_root_beam", fast_config),
            ]
            if bf.n <= 12:
                child_specs.extend(
                    [
                        ("fprm_root_child_beam", fast_config),
                        ("fprm_linear_pair", fast_config),
                        ("affine_greedy", fast_config),
                    ]
                )
            elif bf.n == 16:
                child_specs.append(("fprm_linear_pair", highdim_config))
            elif bf.n >= 18:
                child_specs.append(("fprm_linear_pair_fast", highdim_config))
            else:
                child_specs.append(("fprm_linear_pair_deep", highdim_config))
            if bf.n <= 6:
                child_specs.append(("cube_beam", cube_config))
        portfolio = _run_child_portfolio(bf, child_specs, seed, model_path)
        return _portfolio_result(requested_method, portfolio, config.weights, time.time() - t0)
    if method == "resource_nmcts_screen_gate":
        if bf.n < 18:
            child = synthesize("resource_nmcts", bf, config, seed=seed, model_path=model_path)
            return SynthesisResult(
                method=requested_method,
                cost=child.cost,
                time_s=time.time() - t0,
                correct=child.correct,
                terms=child.terms,
                gates=child.gates,
                n_qubits=child.n_qubits,
            )
        static_skip = _structure_gate_static_skip_resource(bf)
        if static_skip is False:
            child = synthesize("resource_nmcts", bf, config, seed=seed, model_path=model_path)
            return SynthesisResult(
                method=requested_method,
                cost=child.cost,
                time_s=time.time() - t0,
                correct=child.correct,
                terms=child.terms,
                gates=child.gates,
                n_qubits=child.n_qubits,
            )
        if static_skip is True:
            adaptive_screen = synthesize(
                "boolean_linear_pair_screen_adaptive",
                bf,
                config,
                seed=seed,
                model_path=model_path,
            )
            if adaptive_screen.correct:
                return SynthesisResult(
                    method=requested_method,
                    cost=adaptive_screen.cost,
                    time_s=time.time() - t0,
                    correct=adaptive_screen.correct,
                    terms=adaptive_screen.terms,
                    gates=adaptive_screen.gates,
                    n_qubits=adaptive_screen.n_qubits,
                )
            child = synthesize("resource_nmcts", bf, config, seed=seed, model_path=model_path)
            return SynthesisResult(
                method=requested_method,
                cost=child.cost,
                time_s=time.time() - t0,
                correct=child.correct,
                terms=child.terms,
                gates=child.gates,
                n_qubits=child.n_qubits,
            )
        single_screen = synthesize("boolean_linear_pair_screen", bf, config, seed=seed, model_path=model_path)
        adaptive_screen = synthesize(
            "boolean_linear_pair_screen_adaptive",
            bf,
            config,
            seed=seed,
            model_path=model_path,
        )
        if adaptive_screen.correct and _structure_gate_skip_resource(
            _structure_gate_features(bf, adaptive_screen, single_screen, config.weights)
        ):
            return SynthesisResult(
                method=requested_method,
                cost=adaptive_screen.cost,
                time_s=time.time() - t0,
                correct=adaptive_screen.correct,
                terms=adaptive_screen.terms,
                gates=adaptive_screen.gates,
                n_qubits=adaptive_screen.n_qubits,
            )
        portfolio = [adaptive_screen] if adaptive_screen.correct else []
        try:
            resource = synthesize("resource_nmcts", bf, config, seed=seed, model_path=model_path)
            if resource.correct:
                portfolio.append(resource)
        except TimeoutError:
            if not portfolio:
                raise
        if not portfolio:
            raise RuntimeError("screen-gated Resource-NMCTS produced no correct candidate")
        best = min(portfolio, key=lambda r: _resource_selection_key(r, config.weights))
        return SynthesisResult(
            method=requested_method,
            cost=best.cost,
            time_s=time.time() - t0,
            correct=best.correct,
            terms=best.terms,
            gates=best.gates,
            n_qubits=best.n_qubits,
        )
    if method == "rc_nmcts":
        fast_config = replace(
            config,
            candidate_top_k=min(config.candidate_top_k, 18),
            mcts_simulations=min(config.mcts_simulations, 40),
            neural_mcts_simulations=min(config.neural_mcts_simulations, 48),
            max_polarities=min(config.max_polarities, 24),
        )
        portfolio: list[SynthesisResult] = []
        for child_method, child_config in [
            ("direct_anf", config),
            ("fprm_greedy", fast_config),
            ("affine_nmcts", fast_config),
            ("mcts_factor", config),
        ]:
            try:
                child = synthesize(child_method, bf, child_config, seed=seed, model_path=model_path)
            except TimeoutError:
                if portfolio:
                    break
                raise
            except Exception:
                continue
            if child.correct:
                portfolio.append(child)
        if not portfolio:
            raise RuntimeError("RC-NMCTS portfolio produced no correct candidate")
        best = min(portfolio, key=lambda r: (r.cost.score(config.weights), r.cost.T, r.cost.CNOT, r.cost.depth))
        return SynthesisResult(
            method=requested_method,
            cost=best.cost,
            time_s=time.time() - t0,
            correct=best.correct,
            terms=best.terms,
            gates=best.gates,
            n_qubits=best.n_qubits,
        )
    if method in {"resource_nmcts", "resource_nmcts_wide"}:
        fast_config = replace(
            config,
            candidate_top_k=min(config.candidate_top_k, 18),
            mcts_simulations=min(config.mcts_simulations, 32),
            neural_mcts_simulations=min(config.neural_mcts_simulations, 40),
            max_polarities=min(config.max_polarities, 16),
        )
        cube_config = replace(
            config,
            candidate_top_k=min(config.candidate_top_k, 18),
            max_polarities=min(config.max_polarities, 8),
        )
        portfolio: list[SynthesisResult] = []
        child_specs = [("direct_anf", config)]
        if bf.n <= 12:
            child_specs.append(("fprm_greedy", fast_config))
            child_specs.append(("fprm_root_beam", fast_config))
            child_specs.append(("fprm_root_child_beam", fast_config))
            child_specs.append(("fprm_linear_pair", fast_config))
            child_specs.append(("affine_greedy", fast_config))
            child_specs.append(("affine_nmcts", fast_config))
        else:
            # At n=14+ the deep linear branch subsumes the shallow linear-pair
            # candidate.  At n>=18 the cheap ANF-only Boolean-ring screen runs
            # first, then the stronger FPRM branches are attempted opportunistically.
            highdim_config = replace(fast_config, candidate_top_k=config.candidate_top_k)
            if bf.n >= 20:
                child_specs.append(("boolean_linear_pair_screen", highdim_config))
                child_specs.append(("boolean_linear_pair_screen_deep", highdim_config))
                child_specs.append(("boolean_linear_pair_screen_deeper", highdim_config))
                if model_path:
                    child_specs.append(("boolean_linear_pair_screen_ai_guard", highdim_config))
                    child_specs.append(("boolean_linear_pair_screen_deep_ai_guard", highdim_config))
            elif bf.n >= 18:
                # The ANF-only Boolean-ring screen is cheap enough for n=18
                # and runs before FPRM branches that can hit the timeout.
                child_specs.append(("boolean_linear_pair_screen", highdim_config))
                child_specs.append(("boolean_linear_pair_screen_deep", highdim_config))
                child_specs.append(("boolean_linear_pair_screen_deeper", highdim_config))
                if model_path:
                    child_specs.append(("boolean_linear_pair_screen_ai_guard", highdim_config))
                    child_specs.append(("boolean_linear_pair_screen_deep_ai_guard", highdim_config))
                child_specs.append(("fprm_linear_pair_deep", highdim_config))
            else:
                child_specs.append(("fprm_linear_pair_deep", highdim_config))
                child_specs.append(("fprm_boolean_linear_pair_deep", highdim_config))
            if model_path and bf.n < 20:
                neural_linear = (
                    "fprm_linear_pair_deep_ai_guard_wide"
                    if bf.n == 16
                    else "fprm_linear_pair_deep_root_neural_wide"
                )
                child_specs.append((neural_linear, highdim_config))
                child_specs.append(("fprm_boolean_linear_pair_deep_ai_guard", highdim_config))
            if method == "resource_nmcts_wide" and bf.n < 18:
                child_specs.append(("fprm_linear_pair_deep_wide", highdim_config))
                child_specs.append(("fprm_linear_pair_wide_fast", highdim_config))
        if bf.n <= 6:
            child_specs.append(("cube_beam", cube_config))
        if bf.n <= 10:
            child_specs.append(("mcts_factor", config))
        for child_method, child_config in child_specs:
            try:
                child = synthesize(child_method, bf, child_config, seed=seed, model_path=model_path)
            except TimeoutError:
                if portfolio:
                    break
                raise
            except Exception:
                continue
            if child.correct:
                portfolio.append(child)
        if not portfolio:
            raise RuntimeError("Resource-NMCTS portfolio produced no correct candidate")
        best = min(portfolio, key=lambda r: _resource_selection_key(r, config.weights))
        return SynthesisResult(
            method=requested_method,
            cost=best.cost,
            time_s=time.time() - t0,
            correct=best.correct,
            terms=best.terms,
            gates=best.gates,
            n_qubits=best.n_qubits,
        )
    if method == "pareto_resource_nmcts":
        portfolio: list[SynthesisResult] = []
        pareto_configs = _highdim_pareto_candidate_configs(config, bf.n) if bf.n > 12 else _pareto_candidate_configs(config)
        active_config = pareto_configs[0][1]
        if bf.n >= 16:
            child_specs: list[tuple[str, SearchConfig]] = [
                ("resource_nmcts", config),
            ]
        else:
            child_specs = [
                ("direct_anf", config),
                ("fprm_direct", config),
                ("resource_nmcts", config),
            ]
        if bf.n > 12:
            for label, child_config in pareto_configs:
                if bf.n >= 18:
                    continue
                child_specs.append(("fprm_root_beam", child_config))
                if bf.n < 18:
                    child_specs.append(("fprm_linear_pair", child_config))
                    if model_path:
                        child_specs.append(("fprm_linear_pair_root_neural", child_config))
                    child_specs.append(("fprm_linear_parity", child_config))
                    if bf.n <= 15 and child_config.max_factor_ancilla >= 2:
                        child_specs.append(("fprm_linear_pair_deep", child_config))
                        child_specs.append(("fprm_boolean_linear_pair_deep", child_config))
                        if model_path:
                            child_specs.append(("fprm_linear_pair_deep_root_neural_wide", child_config))
                            child_specs.append(("fprm_boolean_linear_pair_deep_ai_guard", child_config))
                elif label == "cnot_depth":
                    # Keep n=18 bounded: no linear-pair screen, but do include
                    # a depth-weighted root-beam candidate that can trade T for
                    # lower Clifford work under depth-heavy profiles.
                    child_specs.append(("fprm_direct", child_config))
        elif bf.n <= 6:
            child_specs.append(("profile_resource_nmcts", config))
            child_specs.append(("fprm_polarity_archive", active_config))
            for label, child_config in pareto_configs:
                child_specs.extend(
                    [
                        ("fprm_greedy", child_config),
                        ("fprm_root_child_beam", child_config),
                        ("fprm_linear_pair", child_config),
                        ("fprm_affine_linear_pair", child_config),
                        ("affine_greedy", child_config),
                        ("cube_beam", child_config),
                    ]
                )
                if child_config.max_factor_ancilla >= 2:
                    child_specs.append(("fprm_linear_pair_deep", child_config))
                    child_specs.append(("fprm_affine_linear_pair_deep", child_config))
                if label == "active" or (label == "t_sparse" and bf.n <= 5):
                    child_specs.append(("affine_nmcts", child_config))
            child_specs.append(("mcts_factor", active_config))
        elif bf.n <= 8:
            child_specs.extend(
                [
                    ("profile_resource_nmcts", config),
                    ("affine_nmcts", active_config),
                ]
            )
            for _label, child_config in pareto_configs[:4]:
                child_specs.extend(
                    [
                        ("fprm_greedy", child_config),
                        ("fprm_root_child_beam", child_config),
                        ("fprm_linear_pair", child_config),
                        ("fprm_affine_linear_pair", child_config),
                        ("affine_greedy", child_config),
                    ]
                )
        else:
            # At n=9--12 the method keeps the Pareto archive cheap: no nested
            # fixed-coordinate MCTS, only direct/FPRM/affine-greedy diversity.
            for _label, child_config in pareto_configs:
                child_specs.extend(
                    [
                        ("fprm_greedy", child_config),
                        ("affine_greedy", child_config),
                    ]
                )

        seen_specs = set()
        for child_method, child_config in child_specs:
            key = (child_method, _config_key(child_config))
            if key in seen_specs:
                continue
            seen_specs.add(key)
            try:
                child = synthesize(child_method, bf, child_config, seed=seed, model_path=model_path)
            except TimeoutError:
                if portfolio:
                    break
                raise
            except Exception:
                continue
            if child.correct:
                portfolio.append(child)
        if not portfolio:
            raise RuntimeError("Pareto-Resource-NMCTS portfolio produced no correct candidate")
        front = _pareto_front(portfolio)
        best = min(front, key=lambda r: _resource_selection_key(r, config.weights))
        return SynthesisResult(
            method=requested_method,
            cost=best.cost,
            time_s=time.time() - t0,
            correct=best.correct,
            terms=best.terms,
            gates=best.gates,
            n_qubits=best.n_qubits,
        )
    if method == "profile_resource_nmcts":
        if bf.n > 12:
            child = synthesize("resource_nmcts", bf, config, seed=seed, model_path=model_path)
            return SynthesisResult(
                method=requested_method,
                cost=child.cost,
                time_s=time.time() - t0,
                correct=child.correct,
                terms=child.terms,
                gates=child.gates,
                n_qubits=child.n_qubits,
            )
        portfolio: list[SynthesisResult] = []
        profile_configs = _profile_candidate_configs(config)
        base_config = profile_configs[0][1]
        if bf.n > 12:
            highdim_config = replace(base_config, candidate_top_k=config.candidate_top_k)
            child_specs: list[tuple[str, SearchConfig]] = [
                ("direct_anf", config),
                ("fprm_linear_pair_deep", highdim_config),
            ]
        else:
            child_specs = [("fprm_direct", config)]
        if bf.n <= 6:
            child_specs.append(("resource_nmcts", config))
            for _label, child_config in profile_configs:
                child_specs.extend(
                    [
                        ("fprm_greedy", child_config),
                        ("affine_greedy", child_config),
                    ]
                )
            child_specs.append(("affine_nmcts", base_config))
            for _label, child_config in profile_configs:
                child_specs.append(("cube_beam", child_config))
            child_specs.append(("mcts_factor", config))
        elif bf.n <= 8:
            child_specs.extend(
                [
                    ("resource_nmcts", config),
                    ("fprm_greedy", base_config),
                    ("affine_greedy", base_config),
                ]
            )
        elif bf.n <= 12:
            # Larger random-ANF instances are where broad profile portfolios can
            # create long tails.  Keep only cheap diversity on top of the stable
            # direct/FPRM candidates.
            child_specs.extend(
                [
                    ("fprm_greedy", base_config),
                    ("affine_greedy", base_config),
                ]
            )
        else:
            child_specs.append(("fprm_linear_pair" if bf.n == 16 else "fprm_linear_pair_deep", highdim_config))

        seen_specs = set()
        for child_method, child_config in child_specs:
            key = (
                child_method,
                child_config.max_factor_ancilla,
                child_config.max_factor_size,
                child_config.candidate_top_k,
                child_config.greedy_eval_limit,
                child_config.max_polarities,
            )
            if key in seen_specs:
                continue
            seen_specs.add(key)
            try:
                child = synthesize(child_method, bf, child_config, seed=seed, model_path=model_path)
            except TimeoutError:
                if portfolio:
                    break
                raise
            except Exception:
                continue
            if child.correct:
                portfolio.append(child)
        if not portfolio:
            raise RuntimeError("Profile-Resource-NMCTS portfolio produced no correct candidate")
        best = min(portfolio, key=lambda r: _resource_selection_key(r, config.weights))
        return SynthesisResult(
            method=requested_method,
            cost=best.cost,
            time_s=time.time() - t0,
            correct=best.correct,
            terms=best.terms,
            gates=best.gates,
            n_qubits=best.n_qubits,
        )
    terms = frozenset(anf_monomials(bf))
    neural = _cached_scorer(model_path or "")

    if method in {
        "direct_anf",
        "boolean_linear_pair_screen",
        "boolean_linear_pair_screen_deep",
        "boolean_linear_pair_screen_deeper",
        "boolean_linear_pair_screen_adaptive",
        "boolean_linear_pair_screen_neural",
        "boolean_linear_pair_screen_deep_neural",
        "boolean_linear_pair_screen_ai_guard",
        "boolean_linear_pair_screen_deep_ai_guard",
        "greedy_factor",
        "neural_greedy",
        "root_beam_factor",
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
    elif method == "fprm_polarity_archive":
        polarity, terms, plan, cost = _best_ranked_polarity_archive(bf, config, seed, neural)
        circ = emit_plan_to_circuit(
            plan,
            bf.n,
            min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            polarity=polarity,
        )
    elif method in {
        "fprm_direct",
        "fprm_greedy",
        "fprm_root_beam",
        "fprm_root_child_beam",
        "fprm_linear_pair",
        "fprm_linear_pair_wide",
        "fprm_linear_pair_wide_fast",
        "fprm_linear_pair_neural",
        "fprm_linear_pair_root_neural",
        "fprm_linear_pair_fast",
        "fprm_linear_pair_fast_neural",
        "fprm_linear_pair_fast_root_neural",
        "fprm_linear_pair_deep",
        "fprm_linear_pair_deep_ai_guard",
        "fprm_linear_pair_deep_ai_guard_wide",
        "fprm_linear_pair_deep_wide",
        "fprm_linear_pair_deep_neural",
        "fprm_linear_pair_deep_root_neural",
        "fprm_linear_pair_deep_root_neural_wide",
        "fprm_boolean_linear_pair",
        "fprm_boolean_linear_pair_deep",
        "fprm_boolean_linear_pair_deep_neural",
        "fprm_boolean_linear_pair_deep_root_neural",
        "fprm_boolean_linear_pair_deep_ai_guard",
        "fprm_boolean_linear_pair_screen",
        "fprm_boolean_linear_pair_screen_neural",
        "fprm_boolean_linear_pair_screen_ai_guard",
        "fprm_linear_parity",
        "fprm_affine_linear_pair",
        "fprm_affine_linear_pair_deep",
        "fprm_mcts",
        "fprm_neural_mcts",
    }:
        polarity, terms, plan, cost = _best_polarity_plan(method, bf, config, seed, neural)
        circ = emit_plan_to_circuit(
            plan,
            bf.n,
            min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            polarity=polarity,
        )
    elif method in {"affine_nmcts", "affine_no_guard", "affine_greedy", "affine_guard_greedy"}:
        transform, polarity, terms, plan, cost = _best_affine_plan(
            bf,
            config,
            seed,
            neural,
            use_neural_refine=method in {"affine_nmcts", "affine_no_guard"},
            use_guard=method in {"affine_nmcts", "affine_guard_greedy"},
        )
        body = emit_plan_to_circuit(
            plan,
            bf.n,
            min(config.max_factor_ancilla, plan.cost.explicit_ancilla),
            polarity=polarity,
        )
        circ = emit_affine_wrapped(body, transform.rows)
    elif method == "cube_greedy":
        plan = cube_greedy_plan(
            bf,
            config.weights,
            max_controls=min(bf.n, max(2, config.max_factor_size + 1)),
            use_relative_phase=config.use_relative_phase,
            gate_mode=config.gate_mode,
        )
        circ = emit_cube_plan(plan, bf.n)
        cost = plan.cost
    elif method == "cube_beam":
        plan = cube_beam_plan(
            bf,
            config.weights,
            max_controls=min(bf.n, max(2, config.max_factor_size + 1)),
            width=max(12, config.candidate_top_k),
            branch=max(8, config.candidate_top_k // 2),
            use_relative_phase=config.use_relative_phase,
            gate_mode=config.gate_mode,
        )
        circ = emit_cube_plan(plan, bf.n)
        cost = plan.cost
    elif method == "esop_milp":
        circ, milp_result = synthesize_esop_milp_circuit(
            bf,
            config.weights,
            max_controls=min(bf.n, max(2, config.max_factor_size + 1)),
            timeout=10.0 if bf.n <= 6 else 30.0,
            gate_mode=config.gate_mode,
        )
        cost = milp_result.plan.cost
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
        method=requested_method,
        cost=cost,
        time_s=dt,
        correct=correct,
        terms=len(terms),
        gates=len(circ.gates),
        n_qubits=circ.n_qubits,
    )
