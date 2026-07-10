"""Training data collection pipeline for AI-SSHR.

Collects (features, label) pairs from teacher solvers:
  - ILP teacher (n<=4): exact WP-SCP solution, set-membership labels
  - Beam teacher (n>=5): high-quality beam solution, step-choice labels

Output CSV with 22 feature columns + metadata + label.
Must run in `sshr` env for ILP collection, `mcts-qoracle` for Beam.
"""
from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from feature_extractor import (
    CandidateRecord,
    build_candidates,
    candidate_features,
    feature_names,
    onset_mask,
    popcount,
    singleton_index,
    vertices_to_mask,
    ensure_sshr_on_path,
)

ensure_sshr_on_path()

from bool_func import BooleanFunction
from parallelotope import Parallelotope


# ---------------------------------------------------------------------------
# Function selection
# ---------------------------------------------------------------------------

def get_functions(
    n: int,
    seed: int = 42,
    count: int = 2000,
) -> List[BooleanFunction]:
    """Get test functions for data collection."""
    if n == 3:
        return [BooleanFunction(3, tt) for tt in range(1, 256)
                if bin(tt).count('1') > 0]
    elif n == 4:
        from npn_reps_n4 import NPN_REPS_N4
        return [BooleanFunction(4, tt) for tt in NPN_REPS_N4
                if bin(tt).count('1') > 0]
    else:
        rng = random.Random(seed)
        N = 1 << n
        fns = []
        while len(fns) < count:
            k = rng.randint(1, max(1, N // 2))
            tt = sum(1 << i for i in rng.sample(range(N), k))
            bf = BooleanFunction(n, tt)
            if bf.onset:
                fns.append(bf)
        return fns


# ---------------------------------------------------------------------------
# ILP teacher (n<=4, requires Gurobi / sshr env)
# ---------------------------------------------------------------------------

def collect_ilp(
    bf: BooleanFunction,
    objective: str = "cnot",
    timeout: float = 30.0,
) -> Tuple[List[dict], float]:
    """Collect labeled data from ILP teacher (set-membership labels).

    Returns (rows, total_cost).
    """
    from sshr_i import _solve_ilp_gurobi, _solve_ilp_gurobi_t_then_cnot

    n = bf.n
    records = build_candidates(n)
    a_mask = onset_mask(bf)

    if not a_mask:
        return [], 0.0

    all_minterms = list(range(1 << n))
    onset = bf.onset

    # Filter to candidates overlapping onset (same filter as _ilp_core)
    active_records = [rec for rec in records if rec.mask & a_mask]
    if not active_records:
        return [], float('inf')

    parallelotopes = [rec.p for rec in active_records]

    t0 = time.time()
    if objective == "cnot":
        costs = [float(rec.cnot_cost) for rec in active_records]
        selected_set = set(_solve_ilp_gurobi(
            parallelotopes, all_minterms, onset, costs, timeout,
        ))
    else:
        t_costs = [float(rec.t_cost) for rec in active_records]
        c_costs = [float(rec.cnot_cost) for rec in active_records]
        selected_set = set(_solve_ilp_gurobi_t_then_cnot(
            parallelotopes, all_minterms, onset, t_costs, c_costs, timeout,
        ))
    elapsed = time.time() - t0

    if not selected_set:
        return [], float('inf')

    total_cost = sum(active_records[i].cost(objective) for i in selected_set)

    rows = []
    for i, rec in enumerate(active_records):
        features = candidate_features(rec, a_mask, n, 0.0, objective)
        row = {
            "step": 0,
            "cand_idx": rec.idx,
            "label": 1.0 if i in selected_set else 0.0,
            "opt_cost": total_cost,
            "teacher_time_s": round(elapsed, 4),
            **features,
        }
        rows.append(row)

    return rows, total_cost


# ---------------------------------------------------------------------------
# Beam teacher (n>=5, mcts-qoracle env)
# ---------------------------------------------------------------------------

def _beam_with_path(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
) -> Tuple[List[int], float]:
    """Run beam search and return (selected_indices, total_cost).

    Wraps _BeamEngine to capture the action path.
    """
    from sshr_beam import _BeamEngine

    n = bf.n
    if not bf.onset:
        return [], 0.0

    engine = _BeamEngine(n, objective)
    A0 = sum(1 << v for v in bf.onset)

    uid = [0]

    def new_state(A_mask: int, cost: float, path: List[int]) -> tuple:
        lb = engine.greedy_lb(A_mask)
        uid[0] += 1
        return (cost + lb, uid[0], A_mask, cost, list(path))

    beam: List[tuple] = [new_state(A0, 0.0, [])]

    for _ in range(max(1, A0.bit_count())):
        complete = [s for s in beam if s[2] == 0]
        if complete:
            best = min(complete, key=lambda s: s[3])
            return best[4], best[3]

        all_next: List[tuple] = []
        for s in beam:
            _, _, A_mask, cost_so_far, path = s
            if A_mask == 0:
                all_next.append(s)
                continue
            actions = engine.top_k_actions(A_mask, branch)
            if not actions:
                A_remaining = A_mask
                total_cost = cost_so_far
                extended_path = list(path)
                while A_remaining:
                    v = (A_remaining & -A_remaining).bit_length() - 1
                    singleton_idx = len(engine.all_p) - (1 << n) + v
                    extended_path.append(singleton_idx)
                    total_cost += engine.costs_list[singleton_idx]
                    A_remaining ^= (1 << v)
                all_next.append(new_state(0, total_cost, extended_path))
                continue

            for orig_idx, action_cost in actions:
                bm = engine.bitmasks_list[orig_idx]
                new_A = A_mask ^ bm
                new_cost = cost_so_far + action_cost
                all_next.append(new_state(new_A, new_cost, path + [orig_idx]))

        if not all_next:
            break
        all_next.sort(key=lambda s: (s[0], s[1]))
        beam = all_next[:width]

    best = min(beam, key=lambda s: s[3])
    return best[4], best[3]


def collect_beam(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    max_neg_per_step: int = 20,
) -> Tuple[List[dict], float]:
    """Collect step-by-step labeled data from beam teacher.

    For each step, keeps the selected candidate + up to max_neg_per_step
    random unselected valid candidates (subsampling to control data size).
    """
    n = bf.n
    records = build_candidates(n)
    a_mask = onset_mask(bf)

    if not a_mask:
        return [], 0.0

    t0 = time.time()
    selected_path, total_cost = _beam_with_path(bf, objective, width, branch)
    elapsed = time.time() - t0

    if not selected_path:
        return [], float('inf')

    # Build idx -> record lookup
    rec_by_idx = {rec.idx: rec for rec in records}

    rows = []
    current_mask = a_mask
    current_cost = 0.0

    for step, sel_idx in enumerate(selected_path):
        # All valid candidates at this step (monotone: mask subset of current A)
        valid_records = [
            rec for rec in records
            if rec.mask and (rec.mask & current_mask) == rec.mask
        ]

        # Separate selected from unselected
        selected = [rec for rec in valid_records if rec.idx == sel_idx]
        negatives = [rec for rec in valid_records if rec.idx != sel_idx]

        # Subsample negatives
        if len(negatives) > max_neg_per_step:
            rng = random.Random(step * 1000 + hash(bf.truth_table) % 10000)
            negatives = rng.sample(negatives, max_neg_per_step)

        for rec in selected:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            row = {
                "step": step,
                "cand_idx": rec.idx,
                "label": 1.0,
                "opt_cost": total_cost,
                "teacher_time_s": round(elapsed, 4),
                **features,
            }
            rows.append(row)

        for rec in negatives:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            row = {
                "step": step,
                "cand_idx": rec.idx,
                "label": 0.0,
                "opt_cost": total_cost,
                "teacher_time_s": round(elapsed, 4),
                **features,
            }
            rows.append(row)

        # Advance state
        sel_rec = rec_by_idx[sel_idx]
        current_mask &= ~sel_rec.mask
        current_cost += sel_rec.cost(objective)

    return rows, total_cost


# ---------------------------------------------------------------------------
# XOR beam teacher (uses ai_guided_beam with XOR semantics)
# ---------------------------------------------------------------------------

def _xor_beam_with_path(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    R_threshold: float = 0.75,
) -> Tuple[List[int], float]:
    """Run XOR beam search and return (selected_indices, total_cost).

    Wraps the _xor_beam function from ai_guided_beam to capture the action path.
    Falls back to SSHR-H if XOR beam doesn't complete.
    """
    from ai_guided_beam import (
        _xor_beam,
        _build_circuit,
        BeamSearchResult,
    )
    from rankers import RuleRanker

    n = bf.n
    records = build_candidates(n)
    a_mask = onset_mask(bf)

    if not a_mask:
        return [], 0.0

    result = _xor_beam(
        bf, records, RuleRanker(), a_mask, n, objective,
        width=width, branch=branch,
        max_depth=max(1, 2 * popcount(a_mask)),
        R_threshold=R_threshold,
        use_rollout=True,
    )

    if result.completed and result.path:
        return result.path, result.cost
    else:
        return [], float('inf')


def collect_xor_beam(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 10,
    R_threshold: float = 0.75,
    max_neg_per_step: int = 20,
) -> Tuple[List[dict], float]:
    """Collect step-by-step labeled data from XOR beam teacher.

    For each step, keeps the selected candidate + up to max_neg_per_step
    random unselected valid candidates (filtered by R_threshold).
    """
    n = bf.n
    records = build_candidates(n)
    a_mask = onset_mask(bf)

    if not a_mask:
        return [], 0.0

    t0 = time.time()
    selected_path, total_cost = _xor_beam_with_path(bf, objective, width, branch, R_threshold)
    elapsed = time.time() - t0

    if not selected_path:
        return [], float('inf')

    rec_by_idx = {rec.idx: rec for rec in records}

    rows = []
    current_mask = a_mask
    current_cost = 0.0

    for step, sel_idx in enumerate(selected_path):
        # XOR semantics: valid candidates have cover_ratio >= R_threshold
        valid_records = []
        for rec in records:
            if not rec.mask:
                continue
            overlap = popcount(rec.mask & current_mask)
            ratio = overlap / rec.size if rec.size > 0 else 0
            if ratio >= R_threshold:
                valid_records.append(rec)

        selected = [rec for rec in valid_records if rec.idx == sel_idx]
        negatives = [rec for rec in valid_records if rec.idx != sel_idx]

        # Subsample negatives
        if len(negatives) > max_neg_per_step:
            rng = random.Random(step * 1000 + hash(bf.truth_table) % 10000)
            negatives = rng.sample(negatives, max_neg_per_step)

        for rec in selected:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            row = {
                "step": step,
                "cand_idx": rec.idx,
                "label": 1.0,
                "opt_cost": total_cost,
                "teacher_time_s": round(elapsed, 4),
                **features,
            }
            rows.append(row)

        for rec in negatives:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            row = {
                "step": step,
                "cand_idx": rec.idx,
                "label": 0.0,
                "opt_cost": total_cost,
                "teacher_time_s": round(elapsed, 4),
                **features,
            }
            rows.append(row)

        # Advance state with XOR update
        sel_rec = rec_by_idx[sel_idx]
        current_mask ^= sel_rec.mask
        current_cost += sel_rec.cost(objective)

    return rows, total_cost


# ---------------------------------------------------------------------------
# Random XOR exploration teacher (diverse solutions, differs from RuleRanker)
# ---------------------------------------------------------------------------

def _mcts_with_path(
    bf: BooleanFunction,
    objective: str = "cnot",
    n_iterations: int = 500,
    time_limit: float = 5.0,
) -> Tuple[List[int], float]:
    """Run MCTS and return (selected_indices, total_cost).

    Since MCTS doesn't expose its path directly, we use random XOR
    exploration to produce diverse solutions different from RuleRanker.
    """
    import random as _rng

    n = bf.n
    if not bf.onset:
        return [], 0.0

    records = build_candidates(n)
    a_mask = onset_mask(bf)

    path = []
    cost = 0.0
    steps = 0
    visited = set()

    while a_mask and steps < 2 * popcount(a_mask):
        # Find valid candidates (XOR semantics with relaxed threshold)
        valid = []
        for rec in records:
            if not rec.mask:
                continue
            overlap = popcount(rec.mask & a_mask)
            ratio = overlap / rec.size if rec.size > 0 else 0
            if ratio >= 0.5:
                valid.append(rec)

        if not valid:
            break

        # RANDOM selection with bias toward high coverage
        _rng.shuffle(valid)
        candidates = valid[:min(5, len(valid))]
        best = max(candidates, key=lambda r: popcount(r.mask & a_mask) / max(r.cost(objective), 1))

        new_a = a_mask ^ best.mask
        if new_a in visited:
            if len(valid) > 1:
                _rng.shuffle(valid)
                best = valid[0]
                new_a = a_mask ^ best.mask
                if new_a in visited:
                    break
            else:
                break

        visited.add(new_a)
        path.append(best.idx)
        cost += best.cost(objective)
        a_mask = new_a
        steps += 1

    if a_mask:
        while a_mask:
            v = (a_mask & -a_mask).bit_length() - 1
            idx = singleton_index(records, v)
            path.append(idx)
            cost += records[idx].cost(objective)
            a_mask ^= (1 << v)

    return path, cost


def collect_random_xor(
    bf: BooleanFunction,
    objective: str = "cnot",
    max_neg_per_step: int = 20,
    seed: int = 0,
) -> Tuple[List[dict], float]:
    """Collect data from random XOR exploration teacher.

    This teacher produces solutions DIFFERENT from RuleRanker,
    providing the diversity ML needs to learn beyond the rule formula.
    """
    import random as _rng
    _rng.seed(seed + hash(bf.truth_table) % 10000)

    n = bf.n
    records = build_candidates(n)
    a_mask = onset_mask(bf)

    if not a_mask:
        return [], 0.0

    t0 = time.time()
    selected_path, total_cost = _mcts_with_path(bf, objective)
    elapsed = time.time() - t0

    if not selected_path:
        return [], float('inf')

    rec_by_idx = {rec.idx: rec for rec in records}
    rows = []
    current_mask = a_mask
    current_cost = 0.0

    for step, sel_idx in enumerate(selected_path):
        valid_records = []
        for rec in records:
            if not rec.mask:
                continue
            overlap = popcount(rec.mask & current_mask)
            ratio = overlap / rec.size if rec.size > 0 else 0
            if ratio >= 0.3:
                valid_records.append(rec)

        selected = [rec for rec in valid_records if rec.idx == sel_idx]
        negatives = [rec for rec in valid_records if rec.idx != sel_idx]

        if len(negatives) > max_neg_per_step:
            _rng.shuffle(negatives)
            negatives = negatives[:max_neg_per_step]

        for rec in selected:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            rows.append({
                "step": step, "cand_idx": rec.idx, "label": 1.0,
                "opt_cost": total_cost, "teacher_time_s": round(elapsed, 4),
                **features,
            })

        for rec in negatives:
            features = candidate_features(rec, current_mask, n, current_cost, objective)
            rows.append({
                "step": step, "cand_idx": rec.idx, "label": 0.0,
                "opt_cost": total_cost, "teacher_time_s": round(elapsed, 4),
                **features,
            })

        sel_rec = rec_by_idx[sel_idx]
        current_mask ^= sel_rec.mask
        current_cost += sel_rec.cost(objective)

    return rows, total_cost


CSV_COLUMNS = [
    "func_n", "func_tt", "teacher", "objective", "label_type",
    "step", "cand_idx", "label",
] + feature_names() + [
    "opt_cost", "teacher_time_s",
]


def write_csv(
    path: Path,
    all_rows: List[dict],
    func_n: int,
    func_tt: int,
    teacher: str,
    objective: str,
    label_type: str,
) -> None:
    """Append rows to CSV, filling metadata columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()

    for row in all_rows:
        row["func_n"] = func_n
        row["func_tt"] = func_tt
        row["teacher"] = teacher
        row["objective"] = objective
        row["label_type"] = label_type

    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(all_rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AI-SSHR training data collection")
    parser.add_argument("--n", nargs="+", type=int, required=True)
    parser.add_argument("--teacher", choices=["ilp", "beam", "xor_beam", "random_xor", "all"], default="all")
    parser.add_argument("--objective", choices=["cnot", "t"], default="cnot")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).parent / "results" / "training_data")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--beam-width", type=int, default=50)
    parser.add_argument("--beam-branch", type=int, default=10)
    parser.add_argument("--fns", type=int, default=2000,
                        help="Max functions for n>=5 random sampling")
    parser.add_argument("--max-fns", type=int, default=None,
                        help="Override max functions for any n")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-neg-per-step", type=int, default=20)
    args = parser.parse_args()

    for n in args.n:
        max_fns = args.max_fns or (None if n <= 4 else args.fns)
        fns = get_functions(n, args.seed, max_fns if max_fns else len(get_functions(n, args.seed, 999999)))
        if max_fns:
            fns = fns[:max_fns]
        print(f"n={n}: {len(fns)} functions")

        teachers = []
        if args.teacher == "all":
            if n <= 4:
                teachers.append(("ilp", collect_ilp))
            teachers.append(("beam", collect_beam))
            teachers.append(("xor_beam", collect_xor_beam))
            teachers.append(("random_xor", collect_random_xor))
        elif args.teacher == "ilp":
            teachers.append(("ilp", collect_ilp))
        elif args.teacher == "beam":
            teachers.append(("beam", collect_beam))
        elif args.teacher == "xor_beam":
            teachers.append(("xor_beam", collect_xor_beam))
        elif args.teacher == "random_xor":
            teachers.append(("random_xor", collect_random_xor))

        for teacher_name, collect_fn in teachers:
            out_path = args.output_dir / f"data_n{n}_{teacher_name}_{args.objective}.csv"
            # Remove existing file to start fresh
            if out_path.exists():
                out_path.unlink()

            total_rows = 0
            errors = 0
            for i, bf in enumerate(fns):
                if not bf.onset:
                    continue
                try:
                    if teacher_name == "ilp":
                        rows, cost = collect_fn(bf, args.objective, args.timeout)
                    elif teacher_name == "xor_beam":
                        rows, cost = collect_fn(
                            bf, args.objective, args.beam_width, args.beam_branch,
                            0.75,  # R_threshold
                            args.max_neg_per_step,
                        )
                    elif teacher_name == "random_xor":
                        rows, cost = collect_fn(
                            bf, args.objective,
                            args.max_neg_per_step,
                            seed=i,
                        )
                    else:
                        rows, cost = collect_fn(
                            bf, args.objective, args.beam_width, args.beam_branch,
                            args.max_neg_per_step,
                        )
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"  ERROR fn={i} tt=0x{bf.truth_table:X}: {e}")
                    continue

                if rows:
                    write_csv(
                        out_path, rows,
                        func_n=n, func_tt=bf.truth_table,
                        teacher=teacher_name, objective=args.objective,
                        label_type="set_membership" if teacher_name == "ilp" else "step_choice",
                    )
                    total_rows += len(rows)

                if (i + 1) % 50 == 0:
                    print(f"  {teacher_name} n={n}: {i+1}/{len(fns)} fns, {total_rows} rows")

            print(f"  DONE {teacher_name} n={n}: {len(fns)} fns, {total_rows} rows, {errors} errors -> {out_path}")


if __name__ == "__main__":
    main()
