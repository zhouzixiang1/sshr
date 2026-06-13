"""Best-of-breed XOR beam search combining multiple strategies.

Strategy:
  1. Run v1 XOR beam with multiple R thresholds, take the best
  2. Run iterative refinement (perturbation + local search) on the best result
  3. Also run multi-restart greedy XOR and take overall best
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from feature_extractor import (
    CandidateRecord,
    build_candidates,
    candidate_features,
    onset_mask,
    popcount,
    ensure_sshr_on_path,
)
from rankers import CandidateRanker, RuleRanker
from ai_guided_beam import (
    BeamSearchResult,
    _build_circuit,
)

ensure_sshr_on_path()

from bool_func import BooleanFunction, QuantumCircuit  # noqa: E402


def _greedy_xor_from_state(
    a_mask: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    R_threshold: float = 0.75,
    max_depth: int = 100,
    seed_top_k: int = 0,
) -> Optional[Tuple[float, List[int]]]:
    """Run greedy XOR from a given state."""
    cost = 0.0
    path: List[int] = []
    visited = {a_mask}
    steps = 0

    while a_mask and steps < max_depth:
        valid = []
        for rec in records:
            if not rec.mask:
                continue
            overlap = popcount(rec.mask & a_mask)
            ratio = overlap / rec.size if rec.size > 0 else 0
            if ratio >= R_threshold:
                valid.append(rec)
        if not valid:
            break

        features_list = [candidate_features(rec, a_mask, n, cost, objective) for rec in valid]
        scores = ranker.score_many(features_list)
        scored = list(zip(scores, valid))
        scored.sort(key=lambda item: item[0], reverse=True)

        chosen_idx = min(seed_top_k, len(scored) - 1)
        found = False
        for j in range(chosen_idx, min(chosen_idx + 10, len(scored))):
            rec = scored[j][1]
            new_a = a_mask ^ rec.mask
            if new_a not in visited:
                cost += rec.cost(objective)
                path.append(rec.idx)
                visited.add(new_a)
                a_mask = new_a
                found = True
                break
        if not found:
            break
        steps += 1

    if a_mask == 0:
        return (cost, path)
    return None


def _perturbation_search(
    initial_path: List[int],
    a0: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    n_perturb: int = 30,
    drop_frac: float = 0.3,
    seed: int = 42,
    R_threshold: float = 0.75,
) -> Optional[Tuple[float, List[int]]]:
    """Try to improve a solution by dropping random subsets and re-solving."""
    import random as _random
    rng = _random.Random(seed)
    by_idx = {rec.idx: rec for rec in records}
    best_cost = sum(by_idx[idx].cost(objective) for idx in initial_path)
    best_path = list(initial_path)
    path_len = len(initial_path)
    n_drop = max(1, int(path_len * drop_frac))

    for _ in range(n_perturb):
        drop_indices = set(rng.sample(range(path_len), min(n_drop, path_len)))
        keep_path = [initial_path[i] for i in range(path_len) if i not in drop_indices]

        xor_of_kept = 0
        keep_cost = 0.0
        for idx in keep_path:
            xor_of_kept ^= by_idx[idx].mask
            keep_cost += by_idx[idx].cost(objective)

        a_state = a0 ^ xor_of_kept
        result = _greedy_xor_from_state(
            a_state, records, ranker, n, objective,
            R_threshold=R_threshold, max_depth=100,
            seed_top_k=rng.randint(0, 3),
        )
        if result is not None:
            total_cost = keep_cost + result[0]
            if total_cost < best_cost:
                best_cost = total_cost
                best_path = keep_path + result[1]

    return (best_cost, best_path)


def xor_beam_best(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    ranker: Optional[CandidateRanker] = None,
    max_steps: Optional[int] = None,
    use_rollout_priority: bool = True,
    R_thresholds: Optional[List[float]] = None,
    n_perturb: int = 50,
) -> BeamSearchResult:
    """Best-of-breed XOR beam search combining multiple strategies.

    Strategy:
      1. Run v1 XOR beam with each R threshold, keep the best solution
      2. Run iterative refinement (perturbation search) on the best solution
      3. Return the overall best result
    """
    from ai_guided_beam import ai_guided_beam

    if objective not in {"cnot", "t"}:
        raise ValueError("objective must be 'cnot' or 't'")

    n = bf.n
    records = build_candidates(n)
    ranker = ranker or RuleRanker()
    a0 = onset_mask(bf)
    if not a0:
        return BeamSearchResult(QuantumCircuit(n + 1), [], 0.0, 0, True)

    if R_thresholds is None:
        R_thresholds = [0.75, 0.67]

    best_cost = float('inf')
    best_path: List[int] = []

    # Phase 1: Multi-R beam search
    for R in R_thresholds:
        result = ai_guided_beam(
            bf, objective, width=width, branch=branch,
            ranker=ranker, max_steps=max_steps,
            use_rollout_priority=use_rollout_priority,
            mode="xor", R_threshold=R,
        )
        if result.completed and result.cost < best_cost:
            best_cost = result.cost
            best_path = list(result.path)

    if not best_path:
        from sshr_h import sshr_h
        circ = sshr_h(bf)
        return BeamSearchResult(circ, [], 0.0, 0, False)

    # Phase 2: Perturbation refinement
    perturbed = _perturbation_search(
        best_path, a0, records, ranker, n, objective,
        n_perturb=n_perturb, drop_frac=0.3, seed=42,
        R_threshold=0.75,
    )
    if perturbed is not None and perturbed[0] < best_cost:
        best_cost = perturbed[0]
        best_path = perturbed[1]

    circ = _build_circuit(best_path, records, n)
    return BeamSearchResult(circ, best_path, best_cost, 0, True)
