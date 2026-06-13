"""Hybrid XOR beam + ILP warm-start solver.

Strategy:
  1. Run XOR beam search to find a good heuristic solution
  2. Convert the beam path to ILP parallelotope indices
  3. Run SSHR-I ILP with the beam solution as Gurobi MIPStart
  4. Return whichever is better: beam or ILP

This gives Gurobi an immediate feasible upper bound, dramatically
speeding up branch-and-bound convergence.
"""
from __future__ import annotations

import time
from typing import List, Optional

from feature_extractor import (
    CandidateRecord,
    build_candidates,
    onset_mask,
    ensure_sshr_on_path,
)
from ai_guided_beam import (
    BeamSearchResult,
    ai_guided_beam,
)
from rankers import CandidateRanker, RuleRanker

ensure_sshr_on_path()

from bool_func import BooleanFunction, QuantumCircuit, mct_cost  # noqa: E402
from parallelotope import Parallelotope  # noqa: E402
from parallelotope_enum import enumerate_parallelotopes  # noqa: E402


def _cost(circ: QuantumCircuit, objective: str) -> int:
    """Compute CNOT or T cost of a circuit."""
    cnot = t = 0
    for g in circ.gates:
        if g.type == 'MCT':
            k = len(g.controls)
            c = mct_cost(k)
            cnot += c["CNOT"]
            t += 4 if k == 2 else c["T"]
        elif g.type == 'CNOT':
            cnot += 1
    return cnot if objective == "cnot" else t


def _beam_path_to_ilp_indices(
    bf: BooleanFunction,
    path: List[int],
    records: List[CandidateRecord],
) -> List[int]:
    """Convert beam path (record indices) to ILP parallelotope indices."""
    n = bf.n
    onset_set = set(bf.onset)
    all_minterms = list(range(1 << n))

    parallelotopes = enumerate_parallelotopes(all_minterms, n)
    seen_vsets = {p.vertices() for p in parallelotopes}
    for v in all_minterms:
        s = frozenset([v])
        if s not in seen_vsets:
            parallelotopes.append(Parallelotope(v, []))
            seen_vsets.add(s)
    parallelotopes = [p for p in parallelotopes if p.vertices() & onset_set]

    vset_to_ilp = {p.vertices(): i for i, p in enumerate(parallelotopes)}

    by_idx = {rec.idx: rec for rec in records}
    ilp_indices = []
    for rec_idx in path:
        rec = by_idx[rec_idx]
        vset = rec.p.vertices()
        if vset in vset_to_ilp:
            ilp_indices.append(vset_to_ilp[vset])

    return ilp_indices


def hybrid_xor_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 120.0,
    beam_width: int = 50,
    beam_branch: int = 10,
    ranker: Optional[CandidateRanker] = None,
    beam_R: float = 0.75,
    try_complement: bool = True,
) -> QuantumCircuit:
    """Hybrid XOR beam + ILP warm-start solver.

    1. Run XOR beam search to get a heuristic solution
    2. Convert beam path to ILP indices for Gurobi MIPStart
    3. Run ILP with warm start
    4. Return the best of: direct beam, complement beam, direct ILP, complement ILP
    """
    from sshr_i import _ilp_core

    if objective not in {"cnot", "t"}:
        raise ValueError("objective must be 'cnot' or 't'")

    n = bf.n
    if not bf.onset:
        return QuantumCircuit(n + 1)

    ranker = ranker or RuleRanker()
    records = build_candidates(n)
    full_mask = (1 << (1 << n)) - 1

    # --- Phase 1: XOR beam search ---
    t0 = time.time()

    # Direct
    beam_direct = ai_guided_beam(
        bf, objective, width=beam_width, branch=beam_branch,
        ranker=ranker, mode="xor", R_threshold=beam_R,
    )

    # Complement
    beam_comp_circ = None
    if try_complement:
        bf_comp = BooleanFunction(n, bf.truth_table ^ full_mask)
        if bf_comp.onset:
            beam_comp = ai_guided_beam(
                bf_comp, objective, width=beam_width, branch=beam_branch,
                ranker=ranker, mode="xor", R_threshold=beam_R,
            )
            beam_comp_circ = beam_comp.circuit

    beam_elapsed = time.time() - t0

    # Pick best beam direction
    best_beam = beam_direct.circuit
    best_beam_cost = _cost(best_beam, objective)
    if beam_comp_circ is not None:
        comp_cost = _cost(beam_comp_circ, objective)
        if comp_cost < best_beam_cost:
            best_beam = beam_comp_circ
            best_beam_cost = comp_cost

    # --- Phase 2: ILP with warm start ---
    ilp_time = max(10.0, timeout - beam_elapsed)

    # Convert beam path to ILP warm start
    warm_start = None
    best_beam_result = beam_direct  # Use direct for warm start
    if best_beam_result.completed and best_beam_result.path:
        warm_start = _beam_path_to_ilp_indices(bf, best_beam_result.path, records)

    # Direct ILP with warm start
    ilp_direct = _ilp_core(bf, objective, ilp_time, warm_start_path=warm_start)
    ilp_direct_cost = _cost(ilp_direct, objective)

    # Complement ILP
    ilp_comp_circ = None
    if try_complement:
        bf_comp = BooleanFunction(n, bf.truth_table ^ full_mask)
        if bf_comp.onset:
            ilp_comp_circ = _ilp_core(bf_comp, objective, ilp_time)
            ilp_comp_cost = _cost(ilp_comp_circ, objective)

    # --- Pick overall best ---
    best = best_beam
    best_cost = best_beam_cost

    if ilp_direct_cost < best_cost:
        best = ilp_direct
        best_cost = ilp_direct_cost

    if ilp_comp_circ is not None and _cost(ilp_comp_circ, objective) < best_cost:
        ilp_comp_circ.add_x(n)
        best = ilp_comp_circ
        best_cost = _cost(ilp_comp_circ, objective)  # X gate costs 0

    return best
