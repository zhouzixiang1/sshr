"""
Unified comparison: SSHR-H / SSHR-H(paper) / MCTS v2 / Beam on n=3..8.

Features:
  - tqdm progress bars per (n, method)
  - Per-n separate CSV (results/compare_n3.csv, ..., compare_n8.csv)
  - Multi-core parallelism (14 workers by default)
  - Runs n=3..8 directly, no args needed

Usage:
  # Default: n=3..8, 14 cores, paper-standard test sets
  python experiments/mcts/mcts_beam_compare.py

  # Quick test
  python experiments/mcts/mcts_beam_compare.py --n 3 --fns 50

  # Specific n values
  python experiments/mcts/mcts_beam_compare.py --n 5 6 --fns 2000

  # Skip methods
  python experiments/mcts/mcts_beam_compare.py --n 5 --skip-mcts
  python experiments/mcts/mcts_beam_compare.py --n 8 --skip-mcts

Output:
  results/compare_n3.csv ... compare_n8.csv  (per-n, one row per method)
  results/comparison_all.csv                 (combined summary)
"""
import sys
import os
import time
import random
import argparse
import csv
from multiprocessing import Pool
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_h_paper import sshr_h_paper
from sshr_mcts_v2 import sshr_mcts_v2
from sshr_beam import sshr_beam
from npn_reps_n4 import NPN_REPS_N4
from paper_data import TABLE_V_SSHR_H, t_count, cnot_count

PAPER_REF = {
    n: {'T': t_count(TABLE_V_SSHR_H, n), 'CNOT': cnot_count(TABLE_V_SSHR_H, n)}
    for n in TABLE_V_SSHR_H
}

N_CORES = 14


# ── Gate cost ────────────────────────────────────────────────────────────────

def gate_cost(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']; anc += c['ancilla']
        elif g.type == 'CNOT':
            C += 1
    return T, C, anc


# ── Test function generation ────────────────────────────────────────────────

def get_fns(n, count=2000, seed=42):
    if n == 3:
        return [BooleanFunction(3, tt) for tt in range(1, 256)]
    elif n == 4:
        return [BooleanFunction(4, tt) for tt in NPN_REPS_N4 if tt != 0]
    else:
        rng = random.Random(seed)
        N = 1 << n
        fns = []
        while len(fns) < count:
            k = rng.randint(1, N // 2)
            tt = sum(1 << i for i in rng.sample(range(N), k))
            bf = BooleanFunction(n, tt)
            if bf.onset:
                fns.append(bf)
        return fns


# ── Worker functions (top-level for multiprocessing pickling) ────────────────

def _worker_sshr_h(bf):
    return gate_cost(sshr_h(bf))


def _worker_sshr_h_paper(bf):
    return gate_cost(sshr_h_paper(bf))


def _worker_mcts_v2(args):
    bf, n_iters, seed = args
    return gate_cost(sshr_mcts_v2(bf, n_iterations=n_iters,
                                  time_limit=9999, seed=seed))


def _worker_beam(args):
    bf, width, branch = args
    return gate_cost(sshr_beam(bf, width=width, branch=branch))


# ── Parallel runner ─────────────────────────────────────────────────────────

def run_parallel(label, worker_fn, items, n_workers):
    chunksize = max(1, len(items) // (n_workers * 4))
    t0 = time.time()
    with Pool(n_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(worker_fn, items, chunksize=chunksize),
            total=len(items),
            desc=f"  {label}",
            ncols=100,
        ))
    T = sum(r[0] for r in results)
    C = sum(r[1] for r in results)
    anc = sum(r[2] for r in results)
    elapsed = time.time() - t0
    return T, C, anc, elapsed


# ── Formatting & CSV ────────────────────────────────────────────────────────

def fmt_delta(val, ref):
    if ref is None or ref == 0:
        return '     n/a'
    pct = 100 * (val - ref) / ref
    return f'{pct:>+6.1f}%'


def append_csv(path, rows):
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['n', 'method', 'n_functions', 'T', 'CNOT', 'ancilla', 'time_s'])
        for row in rows:
            writer.writerow(row)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Unified 4-method comparison (14-core parallel)')
    parser.add_argument('--n', type=int, nargs='+', default=[3, 4, 5, 6, 7, 8])
    parser.add_argument('--fns', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--mcts-iters', type=int, default=1000)
    parser.add_argument('--beam-width', type=int, default=50)
    parser.add_argument('--beam-branch', type=int, default=10)
    parser.add_argument('--skip-sshr-h', action='store_true')
    parser.add_argument('--skip-mcts', action='store_true')
    parser.add_argument('--skip-beam', action='store_true')
    parser.add_argument('--workers', type=int, default=N_CORES)
    args = parser.parse_args()

    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'results')
    os.makedirs(results_dir, exist_ok=True)

    all_rows = []

    for n in args.n:
        fns = get_fns(n, count=args.fns, seed=args.seed)
        ref = PAPER_REF.get(n)
        ref_T = ref['T'] if ref else None
        ref_C = ref['CNOT'] if ref else None
        skip_mcts = args.skip_mcts or (n == 8)
        n_csv = os.path.join(results_dir, f'compare_n{n}.csv')

        print(f"\n{'='*78}")
        print(f"n={n}  |  {len(fns)} functions  |  {args.workers} workers  |  seed={args.seed}")
        if ref:
            print(f"Paper ref: T={ref_T}  CNOT={ref_C}")
        if skip_mcts and n == 8:
            print(f"Note: MCTS skipped for n=8 (object mode too slow)")
        print(f"{'='*78}")
        print(f"  {'Method':<28} {'T':>8} {'dT':>8} "
              f"{'CNOT':>8} {'dCNOT':>8} {'Anc':>8} {'time':>7}")
        print(f"  {'-'*28} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")

        def do_method(label, worker_fn, items):
            T, C, anc, elapsed = run_parallel(label, worker_fn, items,
                                               args.workers)
            print(f"  {label:<28} {T:>8} {fmt_delta(T, ref_T):>8} "
                  f"{C:>8} {fmt_delta(C, ref_C):>8} {anc:>8} {elapsed:>6.0f}s")
            row = [n, label, len(fns), T, C, anc, f'{elapsed:.1f}']
            append_csv(n_csv, [row])
            all_rows.append(row)
            return T, C

        if not args.skip_sshr_h:
            do_method("sshr_h", _worker_sshr_h, fns)

        do_method("sshr_h_paper", _worker_sshr_h_paper, fns)

        if not skip_mcts:
            mcts_items = [(bf, args.mcts_iters, args.seed) for bf in fns]
            do_method(f"mcts_v2({args.mcts_iters}iters)",
                      _worker_mcts_v2, mcts_items)

        if not args.skip_beam:
            beam_items = [(bf, args.beam_width, args.beam_branch) for bf in fns]
            do_method(f"beam(w={args.beam_width},b={args.beam_branch})",
                      _worker_beam, beam_items)

        if ref:
            print(f"  {'[paper reference]':<28} {ref_T:>8} {'0.0%':>8} "
                  f"{ref_C:>8} {'0.0%':>8}")

    # Combined summary
    summary_path = os.path.join(results_dir, 'comparison_all.csv')
    with open(summary_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['n', 'method', 'n_functions', 'T', 'CNOT',
                         'ancilla', 'time_s'])
        for row in all_rows:
            writer.writerow(row)

    print(f"\nDone. Results: {results_dir}/compare_n*.csv, comparison_all.csv")


if __name__ == '__main__':
    main()
