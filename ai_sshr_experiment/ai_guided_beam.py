"""AI-guided beam search with both monotone and XOR semantics.

XOR semantics (mode="xor"):
  - Candidates are valid when cover_ratio >= R_threshold
  - Update: A ^= vertices(P)  (XOR, allows off-set contamination)
  - Depth limit + state cache prevent infinite loops
  - Generally finds lower-cost solutions at small n

Monotone semantics (mode="monotone"):
  - Candidates valid only when vertices(P) subset A
  - Update: A -= vertices(P)  (strict subset removal)
  - No cycles possible, simpler search
  - Better at large n where XOR pollution dominates

Auto mode:
  - Uses XOR for n<=5, monotone for n>=6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from feature_extractor import (
    CandidateRecord,
    build_candidates,
    candidate_features,
    onset_mask,
    popcount,
    singleton_index,
    ensure_sshr_on_path,
)
from rankers import CandidateRanker, RuleRanker

ensure_sshr_on_path()

from block_synth import synth_block  # noqa: E402
from bool_func import BooleanFunction, QuantumCircuit  # noqa: E402


@dataclass
class BeamSearchResult:
    circuit: QuantumCircuit
    path: List[int]
    cost: float
    expanded: int
    completed: bool


def _candidate_by_idx(records: List[CandidateRecord]) -> dict[int, CandidateRecord]:
    return {rec.idx: rec for rec in records}


def _build_circuit(path: List[int], records: List[CandidateRecord], n: int) -> QuantumCircuit:
    by_idx = _candidate_by_idx(records)
    circuit = QuantumCircuit(n + 1)
    for idx in path:
        circuit.add_block(synth_block(by_idx[idx].p, n))
    return circuit


# ---------------------------------------------------------------------------
# Monotone beam (unchanged logic, extracted)
# ---------------------------------------------------------------------------

def _greedy_completion_cost_mono(
    a_mask: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    limit: int,
) -> float:
    """Greedy lower-bound estimate using monotone semantics."""
    total = 0.0
    steps = 0
    while a_mask and steps < limit:
        valid = [rec for rec in records if rec.mask and (rec.mask & a_mask) == rec.mask]
        if not valid:
            break
        # Batch feature extraction and scoring for performance
        features_list = [candidate_features(rec, a_mask, n, total, objective) for rec in valid]
        scores = ranker.score_many(features_list)
        scored = list(zip(scores, valid))
        scored.sort(key=lambda item: item[0], reverse=True)
        rec = scored[0][1]
        total += rec.cost(objective)
        a_mask &= ~rec.mask
        steps += 1
    return total


def _mono_beam(
    bf: BooleanFunction,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    a0: int,
    n: int,
    objective: str,
    width: int,
    branch: int,
    max_steps: int,
    use_rollout: bool,
) -> BeamSearchResult:
    """Monotone beam search (vertices(P) ⊆ A, A -= vertices(P))."""
    uid = 0
    expanded = 0

    def priority(a_mask: int, cost: float) -> float:
        if not use_rollout:
            return cost
        est = _greedy_completion_cost_mono(a_mask, records, ranker, n, objective, max_steps)
        return cost + est

    beam: List[Tuple[float, int, int, float, List[int]]] = [(priority(a0, 0.0), uid, a0, 0.0, [])]

    for _step in range(max_steps + 1):
        complete = [s for s in beam if s[2] == 0]
        if complete:
            best = min(complete, key=lambda s: s[3])
            circ = _build_circuit(best[4], records, n)
            return BeamSearchResult(circ, best[4], best[3], expanded, True)

        next_states: List[Tuple[float, int, int, float, List[int]]] = []
        for _, _, a_mask, cost, path in beam:
            valid = [rec for rec in records if rec.mask and (rec.mask & a_mask) == rec.mask]
            if not valid:
                continue
            # Batch feature extraction and scoring for performance
            features_list = [candidate_features(rec, a_mask, n, cost, objective) for rec in valid]
            scores = ranker.score_many(features_list)
            scored = list(zip(scores, valid))
            scored.sort(key=lambda item: item[0], reverse=True)
            for _, rec in scored[:branch]:
                new_a = a_mask & ~rec.mask
                new_cost = cost + rec.cost(objective)
                uid += 1
                expanded += 1
                next_states.append(
                    (priority(new_a, new_cost), uid, new_a, new_cost, path + [rec.idx])
                )

        if not next_states:
            break
        next_states.sort(key=lambda s: (s[0], s[1]))
        beam = next_states[:width]

    # Fallback: singleton completion
    best = min(beam, key=lambda s: s[3])
    _, _, a_mask, cost, path = best
    while a_mask:
        v = (a_mask & -a_mask).bit_length() - 1
        idx = singleton_index(records, v)
        path = path + [idx]
        cost += records[idx].cost(objective)
        a_mask &= ~(1 << v)
    circ = _build_circuit(path, records, n)
    return BeamSearchResult(circ, path, cost, expanded, False)


# ---------------------------------------------------------------------------
# XOR beam (new)
# ---------------------------------------------------------------------------

def _xor_beam(
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
) -> BeamSearchResult:
    """XOR beam search (A ^= vertices(P), with cover ratio threshold).

    Anti-oscillation mechanisms:
      1. Depth limit: max_depth bounds total steps
      2. State cache: skip states we've already visited in this beam
      3. Cover ratio threshold: only accept candidates with |P∩A|/|P| >= R
    """
    uid = 0
    expanded = 0
    universe = (1 << (1 << n)) - 1
    target_onset = a0  # remember the original target

    def priority(a_mask: int, cost: float, depth: int) -> float:
        if not use_rollout:
            return cost
        # Estimate remaining cost via greedy XOR rollout
        est = _greedy_xor_rollout(a_mask, records, ranker, n, objective,
                                  max_depth - depth, R_threshold)
        return cost + est

    # State: (priority, uid, A_mask, cost, path, depth)
    beam: List[Tuple[float, int, int, float, List[int], int]] = [
        (priority(a0, 0.0, 0), uid, a0, 0.0, [], 0)
    ]

    # Track visited states per beam position to detect cycles
    global_visited: Set[int] = set()

    best_result: Optional[Tuple[float, List[int]]] = None  # (cost, path)

    for step in range(max_depth):
        # Check for complete states
        for s in beam:
            _, _, a_mask, cost, path, depth = s
            # XOR cover is complete when A == target pattern (on-set covered odd times)
            # Actually: A represents current parity. We need A == 0 (all minterms covered correct parity)
            # With XOR semantics starting from a0 (onset), we need final A == 0
            if a_mask == 0:
                if best_result is None or cost < best_result[0]:
                    best_result = (cost, list(path))

        if best_result is not None:
            circ = _build_circuit(best_result[1], records, n)
            return BeamSearchResult(circ, best_result[1], best_result[0], expanded, True)

        next_states: List[Tuple[float, int, int, float, List[int], int]] = []
        for s in beam:
            _, _, a_mask, cost, path, depth = s
            if depth >= max_depth:
                continue

            # Filter candidates by cover ratio threshold
            valid = []
            for rec in records:
                if not rec.mask:
                    continue
                overlap = popcount(rec.mask & a_mask)
                ratio = overlap / rec.size if rec.size > 0 else 0
                if ratio >= R_threshold:
                    valid.append((ratio, overlap, rec))

            if not valid:
                continue

            # Batch feature extraction and scoring for performance
            valid_recs = [rec for _, _, rec in valid]
            features_list = [candidate_features(rec, a_mask, n, cost, objective) for rec in valid_recs]
            scores = ranker.score_many(features_list)
            scored = list(zip(scores, valid_recs))
            scored.sort(key=lambda item: item[0], reverse=True)

            for _, rec in scored[:branch]:
                new_a = a_mask ^ rec.mask  # XOR update
                new_cost = cost + rec.cost(objective)
                new_depth = depth + 1

                # Cycle detection: skip if we've seen this state
                state_key = new_a
                if state_key in global_visited:
                    continue
                global_visited.add(state_key)

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

    # If we have a best result from checking, use it
    if best_result is not None:
        circ = _build_circuit(best_result[1], records, n)
        return BeamSearchResult(circ, best_result[1], best_result[0], expanded, True)

    # Fallback for incomplete XOR beam: use SSHR-H (correctness guaranteed)
    from sshr_h import sshr_h
    circ = sshr_h(bf)
    return BeamSearchResult(circ, [], 0.0, expanded, False)


def _greedy_xor_rollout(
    a_mask: int,
    records: List[CandidateRecord],
    ranker: CandidateRanker,
    n: int,
    objective: str,
    limit: int,
    R_threshold: float = 0.75,
) -> float:
    """Greedy cost estimate using XOR semantics."""
    total = 0.0
    steps = 0
    visited: Set[int] = {a_mask}
    while a_mask and steps < limit:
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
        # Batch feature extraction and scoring for performance
        features_list = [candidate_features(rec, a_mask, n, total, objective) for rec in valid]
        scores = ranker.score_many(features_list)
        scored = list(zip(scores, valid))
        scored.sort(key=lambda item: item[0], reverse=True)
        rec = scored[0][1]
        total += rec.cost(objective)
        new_a = a_mask ^ rec.mask
        if new_a in visited:
            break  # cycle detected
        visited.add(new_a)
        a_mask = new_a
        steps += 1
    # Add penalty for remaining minterms
    remaining = popcount(a_mask)
    if remaining > 0:
        total += remaining * 10  # rough singleton cost estimate
    return total


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def ai_guided_beam(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    ranker: Optional[CandidateRanker] = None,
    max_steps: Optional[int] = None,
    use_rollout_priority: bool = True,
    mode: str = "auto",       # "monotone", "xor", "auto"
    R_threshold: float = 0.75,
) -> BeamSearchResult:
    """AI-guided beam search with selectable semantics.

    Parameters
    ----------
    mode : str
        "monotone" — vertices(P) ⊆ A, A -= vertices(P). No cycles.
        "xor" — A ^= vertices(P) when |P∩A|/|P| >= R_threshold.
                Cycles prevented via state cache + depth limit.
        "auto" — XOR for n<=5, monotone for n>=6.
    R_threshold : float
        Minimum cover ratio for XOR mode (default 0.75, matching SSHR-H).
    """
    if objective not in {"cnot", "t"}:
        raise ValueError("objective must be 'cnot' or 't'")

    n = bf.n
    records = build_candidates(n)
    ranker = ranker or RuleRanker()
    a0 = onset_mask(bf)
    if not a0:
        return BeamSearchResult(QuantumCircuit(n + 1), [], 0.0, 0, True)

    # Select mode
    if mode == "auto":
        effective_mode = "xor" if n <= 6 else "monotone"
    else:
        effective_mode = mode

    if effective_mode == "xor":
        if max_steps is None:
            # XOR needs more steps since A can grow temporarily
            max_steps = max(1, 2 * popcount(a0))
        return _xor_beam(
            bf, records, ranker, a0, n, objective,
            width=width, branch=branch,
            max_depth=max_steps,
            R_threshold=R_threshold,
            use_rollout=use_rollout_priority,
        )
    else:
        if max_steps is None:
            max_steps = max(1, popcount(a0))
        return _mono_beam(
            bf, records, ranker, a0, n, objective,
            width=width, branch=branch,
            max_steps=max_steps,
            use_rollout=use_rollout_priority,
        )
