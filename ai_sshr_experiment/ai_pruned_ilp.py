"""AI-pruned ILP synthesis: ML-guided candidate pruning + Gurobi ILP.

Pipeline:
  1. Enumerate all parallelotope candidates
  2. Rank and prune using ML ranker (keep top ratio + safety singletons)
  3. Solve WP-SCP ILP on the pruned candidate set
  4. Build and return quantum circuit

This must run in the `sshr` conda environment (requires Gurobi).
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List, Optional

from feature_extractor import (
    build_candidates,
    ensure_sshr_on_path,
    onset_mask,
)
from pruned_candidates import select_pruned_candidates
from rankers import RuleRanker

ensure_sshr_on_path()

from block_synth import synth_block
from bool_func import BooleanFunction, QuantumCircuit


def ai_pruned_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 120.0,
    keep_ratio: float = 0.1,
    keep_min: int = 100,
    ranker=None,
) -> QuantumCircuit:
    """Synthesize using ML-pruned candidates fed to ILP.

    Parameters
    ----------
    bf           : Boolean function to synthesize
    objective    : "cnot" or "t"
    timeout      : ILP solver time limit in seconds
    keep_ratio   : fraction of candidates to keep (after ranking)
    keep_min     : minimum number of candidates to keep
    ranker       : CandidateRanker instance (defaults to RuleRanker)

    Returns
    -------
    QuantumCircuit (n+1 qubits)
    """
    from sshr_i import _solve_ilp_gurobi, _solve_ilp_gurobi_t_then_cnot

    n = bf.n
    if not bf.onset:
        return QuantumCircuit(n + 1)

    if ranker is None:
        ranker = RuleRanker()

    # Step 1-2: Prune candidates
    pruned = select_pruned_candidates(
        bf, keep_ratio=keep_ratio, keep_min=keep_min,
        objective=objective, ranker=ranker,
    )

    if not pruned:
        # Fallback to SSHR-H
        from sshr_h import sshr_h
        return sshr_h(bf)

    # Step 3: Build ILP inputs
    parallelotopes = [rec.p for rec in pruned]
    all_minterms = list(range(1 << n))
    onset = bf.onset

    # Step 4: Solve ILP on pruned set
    if objective == "cnot":
        costs = [float(rec.cnot_cost) for rec in pruned]
        selected = _solve_ilp_gurobi(
            parallelotopes, all_minterms, onset, costs, timeout,
        )
    else:
        t_costs = [float(rec.t_cost) for rec in pruned]
        c_costs = [float(rec.cnot_cost) for rec in pruned]
        selected = _solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, c_costs, timeout,
        )

    if not selected:
        # Fallback to SSHR-H
        from sshr_h import sshr_h
        return sshr_h(bf)

    # Step 5: Build circuit
    circ = QuantumCircuit(n + 1)
    for i in selected:
        circ.add_block(synth_block(parallelotopes[i], n))
    return circ


def iterative_pruned_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 120.0,
    initial_keep_ratio: float = 0.3,
    expand_ratio: float = 0.1,
    max_rounds: int = 3,
    ranker=None,
) -> QuantumCircuit:
    """Iterative pruning: solve on small set, expand around solution, re-solve.

    Round 1: Prune to initial_keep_ratio, solve ILP.
    Round 2+: Keep solution candidates + expand neighborhood
              (candidates similar to solution by shared minterms)
              + top candidates from ranker. Solve again.
    """
    from sshr_i import _solve_ilp_gurobi, _solve_ilp_gurobi_t_then_cnot

    n = bf.n
    if not bf.onset:
        return QuantumCircuit(n + 1)

    if ranker is None:
        ranker = RuleRanker()

    records = build_candidates(n)
    a_mask = onset_mask(bf)
    total_candidates = len(records)

    # Track selected candidate indices across rounds
    all_selected: set = set()
    best_circuit = None
    best_cost = float("inf")

    for round_num in range(max_rounds):
        if round_num == 0:
            # Initial round: standard pruning
            keep_count = max(200, int(total_candidates * initial_keep_ratio))
            pruned = select_pruned_candidates(
                bf,
                keep_ratio=initial_keep_ratio,
                keep_min=keep_count,
                objective=objective,
                ranker=ranker,
            )
        else:
            # Expansion round: keep solution candidates + their neighbors + top-ranked
            selected_records = [rec for rec in records if rec.idx in all_selected]
            selected_mask = 0
            for rec in selected_records:
                selected_mask |= rec.mask

            # Neighbors: candidates sharing at least 1 minterm with solution
            neighbors = []
            for rec in records:
                if rec.idx not in all_selected and rec.mask & selected_mask:
                    neighbors.append(rec)

            # Top-ranked candidates not yet included
            from feature_extractor import candidate_features

            neighbor_idxs = {rec.idx for rec in neighbors}
            remaining = [
                rec
                for rec in records
                if rec.idx not in all_selected and rec.idx not in neighbor_idxs
            ]
            scored = []
            for rec in remaining:
                features = candidate_features(rec, a_mask, n, 0.0, objective)
                scored.append((ranker.score(features), rec))
            scored.sort(key=lambda x: x[0], reverse=True)

            expand_count = max(100, int(total_candidates * expand_ratio))
            top_remaining = [rec for _, rec in scored[:expand_count]]

            pruned_set = {
                rec.idx: rec for rec in selected_records + neighbors + top_remaining
            }
            # Add singletons that cover onset
            for rec in records:
                if rec.is_singleton and (rec.mask & a_mask):
                    pruned_set[rec.idx] = rec
            pruned = sorted(pruned_set.values(), key=lambda r: r.idx)

        if not pruned:
            break

        # Solve ILP
        parallelotopes = [rec.p for rec in pruned]
        idx_map = {i: rec.idx for i, rec in enumerate(pruned)}
        all_minterms = list(range(1 << n))
        onset = bf.onset

        try:
            round_timeout = timeout / max_rounds
            if objective == "cnot":
                costs = [float(rec.cnot_cost) for rec in pruned]
                selected = _solve_ilp_gurobi(
                    parallelotopes, all_minterms, onset, costs, round_timeout
                )
            else:
                t_costs = [float(rec.t_cost) for rec in pruned]
                c_costs = [float(rec.cnot_cost) for rec in pruned]
                selected = _solve_ilp_gurobi_t_then_cnot(
                    parallelotopes, all_minterms, onset, t_costs, c_costs, round_timeout
                )
        except Exception:
            break

        if not selected:
            break

        # Map back to global indices
        global_selected = {idx_map[i] for i in selected}
        all_selected.update(global_selected)

        # Compute cost
        cost = sum(pruned[i].cost(objective) for i in selected)
        if cost < best_cost:
            best_cost = cost
            best_circuit = QuantumCircuit(n + 1)
            for i in selected:
                best_circuit.add_block(synth_block(parallelotopes[i], n))

    if best_circuit is None:
        from sshr_h import sshr_h

        return sshr_h(bf)
    return best_circuit


def coverage_aware_pruned_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 120.0,
    keep_ratio: float = 0.8,
    keep_min: int = 200,
    min_coverage: int = 3,
    ranker=None,
) -> QuantumCircuit:
    """Coverage-aware pruning that guarantees ILP feasibility.

    Strategy:
    1. Rank all candidates and keep a large base set (like standard pruning)
    2. For each onset minterm, ensure at least min_coverage non-singleton
       candidates cover it. Add more from the ranked list if needed.
    3. Add all onset singletons (feasibility guarantee)
    4. Solve ILP on the resulting set

    This differs from standard pruning in step 2: it explicitly guarantees
    that every onset minterm has diverse coverage, which helps the ILP find
    better XOR-parity covers.
    """
    from sshr_i import _solve_ilp_gurobi, _solve_ilp_gurobi_t_then_cnot
    from feature_extractor import candidate_features, popcount

    n = bf.n
    if not bf.onset:
        return QuantumCircuit(n + 1)

    if ranker is None:
        ranker = RuleRanker()

    records = build_candidates(n)
    a_mask = onset_mask(bf)
    onset = bf.onset
    all_minterms = list(range(1 << n))

    # Step 1: Rank all candidates
    scored = []
    for rec in records:
        features = candidate_features(rec, a_mask, n, 0.0, objective)
        scored.append((ranker.score(features), rec))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Step 2: Keep large base set (same as standard pruning)
    keep_count = max(keep_min, int(len(records) * keep_ratio))
    keep_count = min(keep_count, len(records))
    selected_idx = {rec.idx for _, rec in scored[:keep_count]}

    # Step 3: Coverage-aware expansion
    # For each onset minterm, count how many non-singleton selected candidates cover it
    non_sing_selected = {rec.idx: rec for rec in records if rec.idx in selected_idx and not rec.is_singleton}
    minterm_coverage = {m: 0 for m in onset}

    for rec in non_sing_selected.values():
        for m in onset:
            if rec.mask & (1 << m):
                minterm_coverage[m] += 1

    # For under-covered minterms, add more candidates from the ranked list
    for m in sorted(minterm_coverage, key=lambda x: minterm_coverage[x]):
        while minterm_coverage[m] < min_coverage:
            added = False
            for score, rec in scored:
                if (rec.idx not in selected_idx
                        and not rec.is_singleton
                        and (rec.mask & (1 << m))):
                    selected_idx.add(rec.idx)
                    # Update coverage for all onset minterms this rec covers
                    for m2 in onset:
                        if rec.mask & (1 << m2):
                            minterm_coverage[m2] += 1
                    added = True
                    break
            if not added:
                break  # No more candidates cover this minterm

    # Step 4: Add all onset singletons (feasibility)
    for rec in records:
        if rec.is_singleton and (rec.mask & a_mask):
            selected_idx.add(rec.idx)

    # Build pruned list
    pruned = [rec for rec in records if rec.idx in selected_idx]
    total_non_sing = sum(1 for r in pruned if not r.is_singleton)
    print(f"  Coverage-aware pruned: {len(pruned)}/{len(records)} "
          f"(base={keep_count}, non-sing={total_non_sing})")

    # Step 5: Solve ILP
    parallelotopes = [rec.p for rec in pruned]
    if objective == "cnot":
        costs = [float(rec.cnot_cost) for rec in pruned]
        selected = _solve_ilp_gurobi(parallelotopes, all_minterms, onset, costs, timeout)
    else:
        t_costs = [float(rec.t_cost) for rec in pruned]
        c_costs = [float(rec.cnot_cost) for rec in pruned]
        selected = _solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, c_costs, timeout
        )

    if not selected:
        from sshr_h import sshr_h
        return sshr_h(bf)

    circ = QuantumCircuit(n + 1)
    for i in selected:
        circ.add_block(synth_block(parallelotopes[i], n))
    return circ


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Pruned ILP synthesis")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--hex", dest="hex_id")
    parser.add_argument("--tt", type=int)
    parser.add_argument("--objective", choices=["cnot", "t"], default="cnot")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--keep-ratio", type=float, default=0.1)
    parser.add_argument("--keep-min", type=int, default=100)
    parser.add_argument("--model", type=Path, default=None,
                        help="Path to trained LightGBM model")
    args = parser.parse_args()

    if args.hex_id:
        bf = BooleanFunction.from_hex(args.n, args.hex_id)
    elif args.tt is not None:
        bf = BooleanFunction(args.n, args.tt)
    else:
        raise ValueError("Must specify --hex or --tt")

    ranker = RuleRanker()
    if args.model:
        from ml_rankers import LightGBMRanker
        ranker = LightGBMRanker.load(args.model)
        print(f"Loaded ML model from {args.model}")

    print(f"n={bf.n} tt=0x{bf.truth_table:X} onset={len(bf.onset)}")

    t0 = time.time()
    circ = ai_pruned_ilp(
        bf, args.objective, args.timeout,
        args.keep_ratio, args.keep_min, ranker,
    )
    elapsed = time.time() - t0

    cost = {"T": 0, "CNOT": 0, "ancilla": 0}
    from bool_func import mct_cost
    cost_fn = mct_cost
    for g in circ.gates:
        if g.type == "MCT":
            c = cost_fn(len(g.controls))
            cost["T"] += c["T"]
            cost["CNOT"] += c["CNOT"]
            cost["ancilla"] = max(cost["ancilla"], c["ancilla"])
        elif g.type == "CNOT":
            cost["CNOT"] += 1

    # Verify
    correct = True
    for x in range(1 << bf.n):
        bits = [(x >> i) & 1 for i in range(bf.n)] + [0]
        if circ.simulate(bits)[bf.n] != bf.evaluate(x):
            correct = False
            break

    print(f"T={cost['T']} CNOT={cost['CNOT']} ancilla={cost['ancilla']} "
          f"time={elapsed:.4f}s correct={correct}")


if __name__ == "__main__":
    main()
