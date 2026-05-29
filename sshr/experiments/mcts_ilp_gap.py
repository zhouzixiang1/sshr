"""
Estimate MCTS vs ILP gap for n=5,6 and MCTS vs SSHR-H for n=6,7,8.

n=5: exact comparison (ILP feasible, same 50 functions)
n=6: small sample 20 fns, ILP timeout=120s (may not be optimal but best available)
n=7: 20 fns, MCTS vs SSHR-H only (ILP completely infeasible)
n=8: 20 fns, MCTS vs SSHR-H only
"""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bool_func import BooleanFunction, mct_cost
from sshr_h import sshr_h
from sshr_mcts import sshr_mcts
from sshr_i import sshr_i

def costs(circ):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']; anc = max(anc, c['ancilla'])
        elif g.type == 'CNOT':
            C += 1
    return T, C, anc

def make_fns(n, count, seed=42):
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

def run_comparison(n, fns, ilp_timeout, mcts_iters=500, label=""):
    print(f"\n{'='*60}")
    print(f"n={n} ({len(fns)} fns){label}")
    print(f"{'='*60}")

    TH, CH = 0, 0
    TM, CM = 0, 0
    TI, CI = 0, 0
    tH, tM, tI = 0.0, 0.0, 0.0
    has_ilp = ilp_timeout > 0

    for i, bf in enumerate(fns):
        # SSHR-H
        t0 = time.time()
        th, ch, _ = costs(sshr_h(bf))
        tH += time.time() - t0
        TH += th; CH += ch

        # SSHR-MCTS
        t0 = time.time()
        tm, cm, _ = costs(sshr_mcts(bf, n_iterations=mcts_iters,
                                     time_limit=ilp_timeout*0.8 if ilp_timeout>0 else 30,
                                     seed=42))
        tM += time.time() - t0
        TM += tm; CM += cm

        # SSHR-I (if feasible)
        if has_ilp:
            t0 = time.time()
            ti, ci, _ = costs(sshr_i(bf, objective='cnot', timeout=ilp_timeout))
            tI += time.time() - t0
            TI += ti; CI += ci

        if (i + 1) % 5 == 0:
            s = f'  {i+1}/{len(fns)}: H=CNOT{CH} M=CNOT{CM}'
            if has_ilp: s += f' I=CNOT{CI}'
            s += f' ({time.time()-t0:.0f}s/fn)'
            print(s, flush=True)

    print(f"\n  {'Method':<22} {'T':>8} {'CNOT':>8} {'Time(s)':>9}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*9}")
    print(f"  {'SSHR-H':<22} {TH:>8} {CH:>8} {tH:>9.1f}")
    print(f"  {'SSHR-MCTS('+str(mcts_iters)+')':<22} {TM:>8} {CM:>8} {tM:>9.1f}")
    if has_ilp:
        print(f"  {'SSHR-I('+str(ilp_timeout)+'s)':<22} {TI:>8} {CI:>8} {tI:>9.1f}")

    print(f"\n  CNOT gains vs SSHR-H:")
    print(f"    SSHR-MCTS: {100*(CH-CM)/CH:+.1f}%")
    if has_ilp and CI > 0:
        print(f"    SSHR-I:    {100*(CH-CI)/CH:+.1f}%")
        print(f"    MCTS gap vs ILP: {100*(CM-CI)/CI:+.1f}%  "
              f"(MCTS={CM}, ILP={CI})")


# ── n=5: 50 fns, exact ILP comparison ────────────────────────────────────
run_comparison(5, make_fns(5, 50), ilp_timeout=60, mcts_iters=500,
               label=" — exact ILP gap")

# ── n=6: 20 fns, ILP with 120s timeout ───────────────────────────────────
run_comparison(6, make_fns(6, 20), ilp_timeout=120, mcts_iters=500,
               label=" — ILP 120s timeout (may not be optimal)")

# ── n=7: 20 fns, MCTS vs SSHR-H only ────────────────────────────────────
run_comparison(7, make_fns(7, 20), ilp_timeout=0, mcts_iters=500,
               label=" — ILP infeasible, MCTS vs SSHR-H only")

# ── n=8: 20 fns, MCTS vs SSHR-H only ────────────────────────────────────
run_comparison(8, make_fns(8, 20), ilp_timeout=0, mcts_iters=500,
               label=" — ILP infeasible, MCTS vs SSHR-H only")
