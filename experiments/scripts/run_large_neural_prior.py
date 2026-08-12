#!/usr/bin/env python3
"""Large-function neural prior effectiveness test (file-logging version)."""
from __future__ import annotations
import sys
from pathlib import Path
_PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

import csv, random, statistics, time
from src.anf_utils import random_truth_function
from src.synthesizers import synthesize
from src.factor_plan import SearchConfig

CONFIG = SearchConfig()
OUTPUT_DIR = _PROJ_ROOT / "results"
LOG_FILE = _PROJ_ROOT / "tmp" / "large_neural_prior.log"

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')
    print(msg, flush=True)

def run_experiment():
    rng = random.Random(42)
    all_rows = []

    for n in [8, 10]:
        n_funcs = 20 if n == 8 else 10
        log(f"\n=== n={n}: {n_funcs} functions ===")

        v2_scores, noprior_scores = [], []
        random_scores_all = {s: [] for s in range(8)}

        for i in range(n_funcs):
            bf = random_truth_function(n, rng)
            while bf.truth_table == 0:
                bf = random_truth_function(n, rng)

            t0 = time.time()
            r0 = synthesize('and_resource_nmcts', bf, CONFIG, seed=42, model_path='')
            noprior_scores.append(r0.cost.score(CONFIG.weights))
            t_np = time.time() - t0

            t0 = time.time()
            r2 = synthesize('and_resource_nmcts', bf, CONFIG, seed=42,
                           model_path='models/action_scorer_v2.pt')
            v2_scores.append(r2.cost.score(CONFIG.weights))
            t_v2 = time.time() - t0

            for seed in range(8):
                rp = f'random-prior:{seed}'
                rr = synthesize('and_resource_nmcts', bf, CONFIG, seed=42, model_path=rp)
                random_scores_all[seed].append(rr.cost.score(CONFIG.weights))

            log(f"  fn{i}: noprior={noprior_scores[-1]:.2f} v2={v2_scores[-1]:.2f} "
                f"(t_np={t_np:.1f}s, t_v2={t_v2:.1f}s)")

            all_rows.append({
                'n': n, 'fn': i,
                'noprior_score': round(noprior_scores[-1], 4),
                'v2_score': round(v2_scores[-1], 4),
                'v2_time_s': round(t_v2, 2),
                'noprior_time_s': round(t_np, 2),
                **{f'random_s{seed}_score': round(random_scores_all[seed][-1], 4)
                   for seed in range(8)}
            })

        random_means = [statistics.mean(random_scores_all[s]) for s in range(8)]
        random_grand_mean = statistics.mean(random_means)
        v2_mean = statistics.mean(v2_scores)
        noprior_mean = statistics.mean(noprior_scores)

        w_vs_np = sum(1 for a, b in zip(v2_scores, noprior_scores) if a < b)
        l_vs_np = sum(1 for a, b in zip(v2_scores, noprior_scores) if a > b)

        log(f"\n--- n={n} Summary ---")
        log(f"  No-prior mean:  {noprior_mean:.4f}")
        log(f"  V2 mean:        {v2_mean:.4f}")
        log(f"  Random mean:    {random_grand_mean:.4f}")
        log(f"  V2 vs NoP: {w_vs_np}/{l_vs_np}/{n_funcs-w_vs_np-l_vs_np} W/L/T")
        log(f"  V2 vs NoP improve: {(noprior_mean-v2_mean)/noprior_mean*100:.3f}%")
        log(f"  V2 vs Random improve: {(random_grand_mean-v2_mean)/random_grand_mean*100:.3f}%")

    out_csv = OUTPUT_DIR / "raw_large_neural_prior.csv"
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        w.writeheader()
        w.writerows(all_rows)
    log(f"\nWrote {len(all_rows)} rows to {out_csv}")

if __name__ == "__main__":
    LOG_FILE.write_text("")  # clear log
    run_experiment()
    log("DONE")
