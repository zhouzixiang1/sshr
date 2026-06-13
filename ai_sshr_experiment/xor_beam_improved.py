"""Improved XOR beam search strategies for better n=6+ performance.

Strategy: Iterative refinement. Start with the best solution from v1 XOR beam,
then try to improve it via:
  1. Multi-restart greedy from intermediate states of the v1 solution
  2. Solution perturbation: randomly drop some parallelotopes and re-solve
  3. Local search: try replacing individual parallelotopes with better alternatives
"""
from __future__ import annotations

import random as _random
from typing import List, Optional, Set, Tuple

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
from block_synth import synth_block  # noqa: E402


def _cost_of_path(path: List[int], records: List[CandidateRecord],
                  objective: str) -> float:
    """Compute total cost of a path."""
    by_idx = {rec.idx: rec for rec in records}
    return sum(by_idx[idx].cost(objective) for idx in path)


def _path_to_mask(path: List[int], records: List[CandidateRecord]) -> int:
    """Compute the XOR of all masks in the path (should equal a0 for valid solution)."""
    by_idx = {rec.idx: rec for rec in records}
    mask = 0
    for idx in path:
        mask ^= by_idx[idx].mask
    return mask


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
    """Run greedy XOR from a given state, returning incremental (cost, path)."""
    cost = 0.0
    path: List[int] = []
    visited: Set[int] = {a_mask}
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
    """Try to improve a solution by dropping random subsets and re-solving.

    For each perturbation:
      1. Drop a random fraction of parallelotopes from the solution
      2. Compute the resulting XOR state
      3. Greedy-solve from that state
      4. Keep the best complete solution
    """
    rng = _random.Random(seed)
    best_cost = _cost_of_path(initial_path, records, objective)
    best_path = list(initial_path)
    by_idx = {rec.idx: rec for rec in records}

    path_len = len(initial_path)
    n_drop = max(1, int(path_len * drop_frac))

    for trial in range(n_perturb):
        # Choose which indices to drop
        drop_indices = set(rng.sample(range(path_len), min(n_drop, path_len)))
        keep_path = [initial_path[i] for i in range(path_len) if i not in drop_indices]

        # Compute current A state: A = a0 ^ (XOR of kept masks)
        xor_of_kept = 0
        keep_cost = 0.0
        for idx in keep_path:
            xor_of_kept ^= by_idx[idx].mask
            keep_cost += by_idx[idx].cost(objective)

        # Current state A = a0 ^ xor_of_kept
        a_state = a0 ^ xor_of_kept

        # Greedy solve from A state to 0
        result = _greedy_xor_from_state(
            a_state, records, ranker, n, objective,
            R_threshold=R_threshold, max_depth=100,
            seed_top_k=rng.randint(0, 3),
        )

        if result is not None:
            total_cost = keep_cost + result[0]
            total_path = keep_path + result[1]
            if total_cost < best_cost:
                best_cost = total_cost
                best_path = total_path

    return (best_cost, best_path)


def _local_search(
    initial_path: List[int],
    a0: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
) -> Optional[Tuple[float, List[int]]]:
    """Try replacing each parallelotope in the path with a better alternative.

    For each position i:
      1. Remove the i-th parallelotope
      2. Compute the XOR state up to position i-1
      3. Try all valid candidates for position i
      4. If a cheaper alternative is found, complete greedily
    """
    by_idx = {rec.idx: rec for rec in records}
    best_cost = _cost_of_path(initial_path, records, objective)
    best_path = list(initial_path)

    for i in range(len(initial_path)):
        # State up to position i-1: XOR of masks 0..i-1
        xor_before = 0
        cost_before = 0.0
        for j in range(i):
            xor_before ^= by_idx[initial_path[j]].mask
            cost_before += by_idx[initial_path[j]].cost(objective)

        # Current A state at position i: A = a0 ^ xor_before
        # The i-th mask XOR'd with A gives the next state
        current_target = by_idx[initial_path[i]]

        # Remaining path after i
        remaining_path = initial_path[i+1:]

        # XOR of remaining path
        xor_remaining = 0
        remaining_cost = 0.0
        for idx in remaining_path:
            xor_remaining ^= by_idx[idx].mask
            remaining_cost += by_idx[idx].cost(objective)

        # For the full path to be valid: a0 ^ xor_before ^ current.mask ^ xor_remaining = 0
        # i.e., current.mask = a0 ^ xor_before ^ xor_remaining
        needed_mask = a0 ^ xor_before ^ xor_remaining

        # Try alternative candidates for position i
        # The alternative mask must equal needed_mask for the full path to work,
        # but we can also re-solve the tail
        candidates = []
        for rec in records:
            if rec.idx == current_target.idx:
                continue
            overlap = popcount(rec.mask & needed_mask)
            if overlap > 0:
                ratio = overlap / rec.size if rec.size > 0 else 0
                if ratio >= 0.5:
                    candidates.append((rec.cost(objective), overlap, ratio, rec))

        candidates.sort(key=lambda x: (x[0], -x[1]))

        for alt_cost, _, _, alt_rec in candidates[:5]:
            if alt_cost >= current_target.cost(objective):
                break  # No point trying more expensive alternatives

            # New A state after replacing position i: A = a0 ^ xor_before ^ alt_rec.mask
            new_a_state = a0 ^ xor_before ^ alt_rec.mask
            new_cost_after = cost_before + alt_cost

            result = _greedy_xor_from_state(
                new_a_state, records, ranker, n, objective,
                R_threshold=0.75, max_depth=100,
            )

            if result is not None:
                total_cost = new_cost_after + result[0]
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_path = initial_path[:i] + [alt_rec.idx] + result[1]

    return (best_cost, best_path)


def xor_beam_improved(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    ranker: Optional[CandidateRanker] = None,
    max_steps: Optional[int] = None,
    use_rollout_priority: bool = True,
    R_threshold: float = 0.75,
    n_perturb: int = 50,
    do_local_search: bool = True,
) -> BeamSearchResult:
    """XOR beam search followed by iterative refinement.

    Phase 1: Standard XOR beam (v1) to get a good initial solution.
    Phase 2: Perturbation search — drop random subsets and re-solve.
    Phase 3 (optional): Local search — try replacing individual blocks.
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

    # Phase 1: Standard v1 XOR beam
    v1_result = ai_guided_beam(
        bf, objective, width=width, branch=branch,
        ranker=ranker, max_steps=max_steps,
        use_rollout_priority=use_rollout_priority,
        mode="xor", R_threshold=R_threshold,
    )

    if not v1_result.completed or not v1_result.path:
        return v1_result

    best_cost = v1_result.cost
    best_path = list(v1_result.path)

    # Phase 2: Perturbation search
    perturbed = _perturbation_search(
        best_path, a0, records, ranker, n, objective,
        n_perturb=n_perturb, drop_frac=0.3, seed=42,
        R_threshold=R_threshold,
    )
    if perturbed is not None and perturbed[0] < best_cost:
        best_cost = perturbed[0]
        best_path = perturbed[1]

    # Phase 3: Local search
    if do_local_search:
        improved = _local_search(best_path, a0, records, ranker, n, objective)
        if improved is not None and improved[0] < best_cost:
            best_cost = improved[0]
            best_path = improved[1]

    circ = _build_circuit(best_path, records, n)
    return BeamSearchResult(circ, best_path, best_cost, v1_result.expanded, True)
