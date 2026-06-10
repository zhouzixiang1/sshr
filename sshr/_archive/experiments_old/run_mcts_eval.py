"""
Evaluation script: SSHR-H vs SSHR-I vs SSHR-MCTS

Usage:
  python run_mcts_eval.py --n 3          # n=3, all 256 fns
  python run_mcts_eval.py --n 4          # n=4, 222 NPN reps
  python run_mcts_eval.py --n 5          # n=5, 2000 random (seed=42)
  python run_mcts_eval.py --n 6 --mcts-only   # n=6, MCTS vs SSHR-H only
  python run_mcts_eval.py --n 3 --ablation    # ablation: iter=100/500/1000/5000
  python run_mcts_eval.py --n 4 --time-budget # time budget comparison
"""
import sys, os, time, random, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bool_func import BooleanFunction, mct_cost, mct_cost_rp
from sshr_h import sshr_h
from sshr_mcts import sshr_mcts, circuit_stats

# ── optional SSHR-I import ────────────────────────────────────────────────
try:
    from sshr_i import sshr_i
    HAS_ILP = True
except Exception:
    HAS_ILP = False


def get_test_functions(n: int, seed: int = 42):
    """Return list of BooleanFunction objects for the given n."""
    N = 1 << n
    if n == 3:
        return [BooleanFunction(n, tt) for tt in range(1, N * N) if tt != 0]
    elif n == 4:
        from npn_reps_n4 import NPN_REPS_N4
        fns = [BooleanFunction(n, tt) for tt in NPN_REPS_N4]
        return [f for f in fns if f.onset]
    else:
        rng = random.Random(seed)
        fns = []
        for _ in range(2000):
            k = rng.randint(1, N // 2)
            mints = set(rng.sample(range(N), k))
            tt = sum(1 << i for i in mints)
            bf = BooleanFunction(n, tt)
            if bf.onset:
                fns.append(bf)
        return fns


def run_method(method_fn, fns, label, objective="cnot", timeout=None, **kwargs):
    """Run a synthesis method on all functions, return aggregate stats."""
    T, C, anc = 0, 0, 0
    t0 = time.time()
    cost_fn = mct_cost_rp if objective == "t" else mct_cost
    for i, bf in enumerate(fns):
        kw = dict(kwargs)
        if timeout is not None and label.startswith("SSHR-I"):
            kw["timeout"] = timeout
        circ = method_fn(bf, **kw)
        for g in circ.gates:
            if g.type == "MCT":
                c = cost_fn(len(g.controls))
                T += c["T"]; C += c["CNOT"]; anc = max(anc, c["ancilla"])
            elif g.type == "CNOT":
                C += 1
        if (i + 1) % 50 == 0:
            print(f"    [{label}] {i+1}/{len(fns)} T={T} CNOT={C} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    elapsed = time.time() - t0
    return T, C, anc, elapsed


def print_table(rows, title):
    """Print a comparison table."""
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")
    print(f"  {'Method':<20} {'T':>8} {'CNOT':>8} {'Anc':>6} {'Time(s)':>8}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*6} {'-'*8}")
    for label, T, C, anc, elapsed in rows:
        print(f"  {label:<20} {T:>8} {C:>8} {anc:>6} {elapsed:>8.0f}")
    print(f"{'='*65}")

    # CNOT gain vs SSHR-H
    h_row = next((r for r in rows if "SSHR-H" in r[0]), None)
    if h_row:
        h_cnot = h_row[2]
        print("\n  CNOT gains vs SSHR-H:")
        for label, T, C, anc, elapsed in rows:
            if "SSHR-H" not in label and h_cnot > 0:
                gain = (h_cnot - C) / h_cnot * 100
                print(f"    {label:<20}: {gain:+.1f}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--objective", default="cnot", choices=["cnot", "t"])
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--mcts-only", action="store_true",
                        help="Skip SSHR-I (for large n)")
    parser.add_argument("--ablation", action="store_true",
                        help="Run ablation: iter=100/500/1000/5000")
    parser.add_argument("--time-budget", action="store_true",
                        help="Time budget comparison: 10s/60s/120s vs SSHR-I")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    n = args.n
    objective = args.objective
    print(f"\nLoading n={n} test functions (seed={args.seed})...")
    fns = get_test_functions(n, seed=args.seed)
    print(f"  {len(fns)} functions loaded.\n")

    # ── Standard comparison ───────────────────────────────────────────────
    if not args.ablation and not args.time_budget:
        rows = []

        # SSHR-H
        print(f"Running SSHR-H...")
        T, C, anc, elapsed = run_method(sshr_h, fns, "SSHR-H", objective=objective)
        rows.append(("SSHR-H", T, C, anc, elapsed))

        # SSHR-I (optional)
        if HAS_ILP and not args.mcts_only:
            print(f"Running SSHR-I (timeout=60s)...")
            T, C, anc, elapsed = run_method(
                sshr_i, fns, "SSHR-I", objective=objective, timeout=60)
            rows.append(("SSHR-I (60s)", T, C, anc, elapsed))

        # SSHR-MCTS
        print(f"Running SSHR-MCTS (iter={args.iterations}, "
              f"time_limit={args.time_limit}s)...")
        T, C, anc, elapsed = run_method(
            sshr_mcts, fns, "SSHR-MCTS", objective=objective,
            n_iterations=args.iterations, time_limit=args.time_limit,
            seed=args.seed)
        rows.append((f"SSHR-MCTS({args.iterations})", T, C, anc, elapsed))

        print_table(rows, f"n={n} {objective.upper()} objective")

    # ── Ablation A: fixed iteration counts ───────────────────────────────
    elif args.ablation:
        print("Ablation experiment: fixed iteration counts")
        rows = []
        # Baseline
        print("Running SSHR-H...")
        T, C, anc, elapsed = run_method(sshr_h, fns, "SSHR-H", objective=objective)
        rows.append(("SSHR-H", T, C, anc, elapsed))

        for iters in [100, 500, 1000, 5000]:
            print(f"Running SSHR-MCTS iter={iters}...")
            T, C, anc, elapsed = run_method(
                sshr_mcts, fns, f"MCTS-{iters}", objective=objective,
                n_iterations=iters, time_limit=9999.0, seed=args.seed)
            rows.append((f"SSHR-MCTS({iters})", T, C, anc, elapsed))

        if HAS_ILP and not args.mcts_only:
            print("Running SSHR-I (timeout=120s)...")
            T, C, anc, elapsed = run_method(
                sshr_i, fns, "SSHR-I", objective=objective, timeout=120)
            rows.append(("SSHR-I (optimal)", T, C, anc, elapsed))

        print_table(rows, f"Ablation n={n}: fixed iterations")

    # ── Ablation B: fixed time budgets ────────────────────────────────────
    elif args.time_budget:
        print("Ablation experiment: fixed time budgets")
        rows = []
        print("Running SSHR-H...")
        T, C, anc, elapsed = run_method(sshr_h, fns, "SSHR-H", objective=objective)
        rows.append(("SSHR-H", T, C, anc, elapsed))

        for tl in [10.0, 60.0, 120.0]:
            print(f"Running SSHR-MCTS time_limit={tl}s/fn...")
            T, C, anc, elapsed = run_method(
                sshr_mcts, fns, f"MCTS-{tl}s", objective=objective,
                n_iterations=99999, time_limit=tl, seed=args.seed)
            rows.append((f"SSHR-MCTS({tl}s)", T, C, anc, elapsed))

        if HAS_ILP and not args.mcts_only:
            for tl in [10, 60, 120]:
                print(f"Running SSHR-I timeout={tl}s...")
                T, C, anc, elapsed = run_method(
                    sshr_i, fns, f"SSHR-I-{tl}s", objective=objective,
                    timeout=float(tl))
                rows.append((f"SSHR-I({tl}s)", T, C, anc, elapsed))

        print_table(rows, f"Time budget n={n}")


if __name__ == "__main__":
    main()
