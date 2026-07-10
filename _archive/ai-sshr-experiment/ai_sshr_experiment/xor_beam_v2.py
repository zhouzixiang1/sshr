"""Improved XOR beam search with multi-restart greedy seeding.

Key improvements over the base XOR beam (ai_guided_beam.py):
  1. Multi-restart greedy: run K independent greedy XOR searches with varied
     R thresholds and seed selections to find a good upper bound quickly.
  2. Cost-based pruning: once a complete solution is found, prune states whose
     accumulated cost already exceeds it.
  3. Adaptive R threshold: progressively relax from R=0.75 to R=0.50 as depth
     increases, allowing more candidates when fewer options remain.
  4. No global visited set: the v1 global_visited was too aggressive, pruning
     better paths to the same state. v2 only prunes by cost upper bound.
"""
from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Greedy XOR solver with configurable seed
# ---------------------------------------------------------------------------

def _greedy_xor_solve(
    a0: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    R_threshold: float = 0.75,
    max_depth: int = 200,
    seed_top_k: int = 0,
) -> Optional[Tuple[float, List[int]]]:
    """Run a single greedy XOR search, returning (cost, path) or None."""
    a_mask = a0
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

        # Try seed_top_k-th candidate; if cycle, try nearby alternatives
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


def _multistart_xor_greedy(
    a0: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    n_restarts: int = 20,
    max_depth: int = 200,
) -> Optional[Tuple[float, List[int]]]:
    """Run multiple greedy XOR searches with varied parameters."""
    best: Optional[Tuple[float, List[int]]] = None
    configs = []
    for R in [0.75, 0.67, 0.60, 0.50]:
        for k in range(5):
            configs.append((R, k))
    configs = configs[:n_restarts]

    for R, k in configs:
        result = _greedy_xor_solve(a0, records, ranker, n, objective,
                                   R_threshold=R, max_depth=max_depth,
                                   seed_top_k=k)
        if result is not None:
            if best is None or result[0] < best[0]:
                best = result
    return best


# ---------------------------------------------------------------------------
# XOR beam v2 (no global visited, cost-based pruning, adaptive R)
# ---------------------------------------------------------------------------

def _xor_beam_v2(
    bf: BooleanFunction,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    a0: int,
    n: int,
    objective: str,
    width: int,
    branch: int,
    max_depth: int,
    R_threshold: float = 0.75,
    use_rollout: bool = True,
    initial_ub: Optional[float] = None,
) -> BeamSearchResult:
    """XOR beam search with cost-based pruning and adaptive R."""
    uid = 0
    expanded = 0
    best_result: Optional[Tuple[float, List[int]]] = None
    ub: float = initial_ub if initial_ub is not None else float('inf')

    def priority(a_mask: int, cost: float, depth: int) -> float:
        if not use_rollout:
            return cost
        remaining = popcount(a_mask)
        if remaining == 0:
            return cost
        # Lightweight estimate: ~2 CNOT per remaining minterm
        return cost + remaining * 2.0

    # State: (priority, uid, A_mask, cost, path, depth)
    beam: List[Tuple[float, int, int, float, List[int], int]] = [
        (0.0, uid, a0, 0.0, [], 0)
    ]

    for step in range(max_depth):
        next_states: List[Tuple[float, int, int, float, List[int], int]] = []

        for s in beam:
            _, _, a_mask, cost, path, depth = s

            # Check if this state is complete
            if a_mask == 0:
                if best_result is None or cost < best_result[0]:
                    best_result = (cost, list(path))
                    ub = cost
                continue

            if depth >= max_depth:
                continue

            # Prune by upper bound
            if cost >= ub:
                continue

            # Adaptive R: relax as depth increases
            current_R = max(0.50, R_threshold - 0.05 * (depth // 5))

            valid = []
            for rec in records:
                if not rec.mask:
                    continue
                overlap = popcount(rec.mask & a_mask)
                ratio = overlap / rec.size if rec.size > 0 else 0
                if ratio >= current_R:
                    valid.append(rec)

            if not valid:
                continue

            features_list = [candidate_features(rec, a_mask, n, cost, objective) for rec in valid]
            scores = ranker.score_many(features_list)
            scored = list(zip(scores, valid))
            scored.sort(key=lambda item: item[0], reverse=True)

            for _, rec in scored[:branch]:
                new_a = a_mask ^ rec.mask
                new_cost = cost + rec.cost(objective)
                new_depth = depth + 1

                # Prune by upper bound
                if new_cost >= ub:
                    continue

                uid += 1
                expanded += 1
                next_states.append(
                    (priority(new_a, new_cost, new_depth), uid, new_a, new_cost,
                     path + [rec.idx], new_depth)
                )

        if not next_states:
            break

        next_states.sort(key=lambda s: (s[0], s[1]))
        beam = next_states[:width]

    # Return best result found
    if best_result is not None:
        circ = _build_circuit(best_result[1], records, n)
        return BeamSearchResult(circ, best_result[1], best_result[0], expanded, True)

    # Fallback: use SSHR-H
    from sshr_h import sshr_h
    circ = sshr_h(bf)
    return BeamSearchResult(circ, [], 0.0, expanded, False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def xor_beam_v2(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    ranker: Optional[CandidateRanker] = None,
    max_steps: Optional[int] = None,
    use_rollout_priority: bool = True,
    R_threshold: float = 0.75,
    n_greedy_restarts: int = 20,
) -> BeamSearchResult:
    """Improved XOR beam search with multi-restart greedy + beam refinement.

    Phase 1: Multi-restart greedy XOR with varied R thresholds and seed selections
             to quickly find a good upper bound.
    Phase 2: Beam search with cost-based pruning using the upper bound from Phase 1.
    """
    if objective not in {"cnot", "t"}:
        raise ValueError("objective must be 'cnot' or 't'")

    n = bf.n
    records = build_candidates(n)
    ranker = ranker or RuleRanker()
    a0 = onset_mask(bf)
    if not a0:
        return BeamSearchResult(QuantumCircuit(n + 1), [], 0.0, 0, True)

    if max_steps is None:
        max_steps = max(1, 2 * popcount(a0))

    # Phase 1: Multi-restart greedy to get upper bound
    greedy_best = _multistart_xor_greedy(
        a0, records, ranker, n, objective,
        n_restarts=n_greedy_restarts,
        max_depth=max_steps,
    )

    initial_ub = greedy_best[0] if greedy_best is not None else None

    # Phase 2: Beam search with upper bound pruning
    beam_result = _xor_beam_v2(
        bf, records, ranker, a0, n, objective,
        width=width, branch=branch,
        max_depth=max_steps,
        R_threshold=R_threshold,
        use_rollout=use_rollout_priority,
        initial_ub=initial_ub,
    )

    # Return whichever is better: greedy or beam
    if greedy_best is not None and beam_result.completed:
        greedy_cost = greedy_best[0]
        beam_cost = beam_result.cost
        if greedy_cost < beam_cost:
            circ = _build_circuit(greedy_best[1], records, n)
            return BeamSearchResult(circ, greedy_best[1], greedy_cost,
                                    beam_result.expanded, True)

    if not beam_result.completed and greedy_best is not None:
        circ = _build_circuit(greedy_best[1], records, n)
        return BeamSearchResult(circ, greedy_best[1], greedy_best[0],
                                beam_result.expanded, True)

    return beam_result
