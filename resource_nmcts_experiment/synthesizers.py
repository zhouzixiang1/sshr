#!/usr/bin/env python3
"""Public synthesizer wrappers for experiments."""
from __future__ import annotations

import time
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
from factor_plan import SearchConfig, direct_plan, emit_plan_to_circuit, greedy_plan, linear_pair_beam_plan, root_beam_plan, root_child_beam_plan, verify_oracle
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
    if method == "fprm_root_child_beam":
        return root_child_beam_plan(terms, config=config)
    if method == "fprm_linear_pair":
        return linear_pair_beam_plan(terms, config=config)
    if method == "fprm_linear_pair_deep":
        return linear_pair_beam_plan(terms, config=config, recursive_depth=1)
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
    if method in {"fprm_root_beam", "fprm_root_child_beam", "fprm_linear_pair", "fprm_linear_pair_deep"} and bf.n > 12 and len(anf_monomials(bf)) > 128:
        ranked = _direct_screened_polarities(
            bf,
            config,
            seed,
            budget=max(32, min(64, 4 * max(1, config.max_polarities))),
            top_k=2,
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
        elif method == "fprm_linear_pair_deep":
            plan = linear_pair_beam_plan(terms, config=config, recursive_depth=1)
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


def _resource_selection_key(result: SynthesisResult, weights) -> tuple[float, int, int, int, int]:
    score = result.cost.score(weights)
    if weights.ancilla >= max(4.0, 4.0 * weights.t):
        return (score, result.cost.peak_ancilla, result.cost.T, result.cost.CNOT, result.cost.depth)
    if weights.cnot >= 0.10 or weights.depth >= 0.05:
        return (score, result.cost.CNOT, result.cost.depth, result.cost.T, result.cost.peak_ancilla)
    return (score, result.cost.T, result.cost.CNOT, result.cost.depth, result.cost.peak_ancilla)


def synthesize(method: str, bf: BooleanFunction, config: SearchConfig, seed: int = 0, model_path: str | None = None) -> SynthesisResult:
    t0 = time.time()
    requested_method = method
    if method.startswith("and_"):
        config = replace(config, gate_mode="logical_and")
        method = method[len("and_") :]
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
    if method == "resource_nmcts":
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
            child_specs.append(("affine_nmcts", fast_config))
        else:
            # At n=14+ the FPRM linear-pair branch keeps the root-child beam
            # baseline and adds a CNOT-only XOR-factor candidate.
            highdim_config = replace(fast_config, candidate_top_k=config.candidate_top_k)
            child_specs.append(("fprm_linear_pair", highdim_config))
            if bf.n >= 15:
                child_specs.append(("fprm_linear_pair_deep", highdim_config))
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
    if method == "profile_resource_nmcts":
        portfolio: list[SynthesisResult] = []
        profile_configs = _profile_candidate_configs(config)
        base_config = profile_configs[0][1]
        if bf.n > 12:
            highdim_config = replace(base_config, candidate_top_k=config.candidate_top_k)
            child_specs: list[tuple[str, SearchConfig]] = [
                ("direct_anf", config),
                ("fprm_linear_pair", highdim_config),
            ]
            if bf.n >= 15:
                child_specs.append(("fprm_linear_pair_deep", highdim_config))
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
            child_specs.append(("fprm_linear_pair", highdim_config))
            if bf.n >= 15:
                child_specs.append(("fprm_linear_pair_deep", highdim_config))

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
    elif method in {"fprm_direct", "fprm_greedy", "fprm_root_beam", "fprm_root_child_beam", "fprm_linear_pair", "fprm_linear_pair_deep", "fprm_mcts", "fprm_neural_mcts"}:
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
