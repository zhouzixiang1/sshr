"""
Checkpoint-based SSHR-I ILP experiment runner.

Saves results after each function to a JSON checkpoint file.
Can resume from the last checkpoint if the process is killed.

Usage:
  /opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 5 --objective cnot --timeout 120
  /opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 6 --objective cnot --timeout 120 --fns 100
  /opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 5 --objective cnot --resume  # resume from checkpoint
"""
import sys
import os
import time
import random
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bool_func import BooleanFunction, mct_cost
from sshr_i import sshr_i
from paper_data import TABLE_VI_SSHR_I_CNOT, TABLE_VII_SSHR_I_T
from npn_reps_n4 import NPN_REPS_N4


def gate_cost(circ, rp_toffoli=False):
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            k = len(g.controls)
            c = mct_cost(k)
            t_cost = 4 if (rp_toffoli and k == 2) else c['T']
            T += t_cost; C += c['CNOT']; anc += c['ancilla']
        elif g.type == 'CNOT':
            C += 1
    return T, C, anc


def get_fns(n, count=2000, seed=42):
    """Get test functions for each n (matching paper's test set)."""
    if n == 3:
        return [BooleanFunction(3, tt) for tt in range(1, 256) if BooleanFunction(3, tt).onset]
    elif n == 4:
        return [BooleanFunction(4, tt) for tt in NPN_REPS_N4 if BooleanFunction(4, tt).onset]
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


def verify_circuit(circ, bf):
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        if circ.simulate(bits)[n] != bf.evaluate(x):
            return False
    return True


def get_checkpoint_path(n, objective, fns_count, seed):
    ckpt_dir = os.path.join(os.path.dirname(__file__), 'checkpoints')
    os.makedirs(ckpt_dir, exist_ok=True)
    return os.path.join(ckpt_dir, f'ilp_n{n}_{objective}_fns{fns_count}_seed{seed}.json')


def load_checkpoint(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_checkpoint(path, data):
    with open(path + '.tmp', 'w') as f:
        json.dump(data, f)
    os.replace(path + '.tmp', path)


def run_ilp_checkpoint(n, objective, timeout, fns, ref_table, label, ckpt_path, resume=True):
    """Run SSHR-I with per-function checkpointing. Can resume after kill."""

    # Load existing checkpoint
    ckpt = load_checkpoint(ckpt_path) if resume else None
    if ckpt:
        T_total = ckpt['T_total']
        C_total = ckpt['C_total']
        anc_total = ckpt['anc_total']
        fails = ckpt['fails']
        timeouts = ckpt['timeouts']
        start_idx = ckpt['completed']
        elapsed_prev = ckpt.get('elapsed', 0.0)
        print(f"  [Resume] Loaded checkpoint: {start_idx}/{len(fns)} completed, "
              f"CNOT={C_total}, T={T_total}, timeouts={timeouts}")
    else:
        T_total = C_total = anc_total = fails = timeouts = 0
        start_idx = 0
        elapsed_prev = 0.0

    if start_idx >= len(fns):
        print(f"  [Already complete] {len(fns)}/{len(fns)}")
    else:
        t0 = time.time()

        for i in range(start_idx, len(fns)):
            bf = fns[i]
            t_fn = time.time()
            circ = sshr_i(bf, objective=objective, timeout=timeout)
            elapsed_fn = time.time() - t_fn

            if elapsed_fn >= timeout * 0.99:
                timeouts += 1
            if not verify_circuit(circ, bf):
                fails += 1

            T, C, anc = gate_cost(circ, rp_toffoli=(objective == 't'))
            T_total += T; C_total += C; anc_total += anc

            # Save checkpoint after every function
            elapsed_now = elapsed_prev + (time.time() - t0)
            save_checkpoint(ckpt_path, {
                'n': n, 'objective': objective, 'completed': i + 1,
                'T_total': T_total, 'C_total': C_total, 'anc_total': anc_total,
                'fails': fails, 'timeouts': timeouts, 'elapsed': elapsed_now,
            })

            if (i + 1) % 10 == 0 or (i + 1) == len(fns):
                elapsed = elapsed_prev + (time.time() - t0)
                print(f"  {i+1:4d}/{len(fns)}  T={T_total:8d}  CNOT={C_total:8d}  "
                      f"timeouts={timeouts}  ({elapsed:.0f}s)", flush=True)

    dt = elapsed_prev + (time.time() - t0 if start_idx < len(fns) else 0)

    ref = ref_table.get(n)
    print(f"\n  Result:  T={T_total}  CNOT={C_total}  Anc={anc_total}  fails={fails}  "
          f"timeouts={timeouts}  ({dt:.1f}s)")
    if ref:
        dT = T_total - ref[0]
        dC = C_total - ref[1]
        print(f"  Paper:   T={ref[0]}  CNOT={ref[1]}  Anc={ref[2]}")
        pct_t = 100 * dT / ref[0] if ref[0] else 0
        pct_c = 100 * dC / ref[1] if ref[1] else 0
        print(f"  Delta:   T={dT:+d} ({pct_t:+.1f}%)  CNOT={dC:+d} ({pct_c:+.1f}%)")
    return T_total, C_total, anc_total, fails, timeouts, dt


def main():
    parser = argparse.ArgumentParser(description='Checkpoint-based SSHR-I ILP runner')
    parser.add_argument('--n', type=int, required=True)
    parser.add_argument('--objective', choices=['cnot', 't'], default='cnot')
    parser.add_argument('--timeout', type=float, default=None)
    parser.add_argument('--fns', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--resume', action='store_true', default=True,
                        help='Resume from checkpoint if available (default: True)')
    parser.add_argument('--no-resume', dest='resume', action='store_false',
                        help='Start fresh, ignore existing checkpoint')
    args = parser.parse_args()

    n = args.n
    timeout = args.timeout if args.timeout else (30 if n <= 4 else 120)
    fns = get_fns(n, count=args.fns, seed=args.seed)
    ref_table = TABLE_VI_SSHR_I_CNOT if args.objective == 'cnot' else TABLE_VII_SSHR_I_T
    label = f'Table VI: CNOT objective' if args.objective == 'cnot' else 'Table VII: T objective'

    ckpt_path = get_checkpoint_path(n, args.objective, args.fns, args.seed)

    print("=" * 72)
    print(f"SSHR-I Checkpoint Runner: n={n}, objective={args.objective.upper()}")
    print(f"Checkpoint: {ckpt_path}")
    print("=" * 72)
    print(f"\n{'─'*72}")
    print(f"n={n}  {label}  [{len(fns)} functions, timeout={timeout}s]")
    print(f"{'─'*72}")

    run_ilp_checkpoint(n, args.objective, timeout, fns, ref_table, label,
                       ckpt_path, resume=args.resume)


if __name__ == '__main__':
    main()
