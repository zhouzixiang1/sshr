#!/usr/bin/env python3
"""Parallel experiments: AES S-box + large-function neural prior.
Uses ProcessPoolExecutor to run all independent tasks across CPU cores."""
from __future__ import annotations
import sys, os
from pathlib import Path
_PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

import csv, json, random, statistics, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict

# Each worker process imports these fresh
def _worker_init():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- Task definitions (must be picklable, at module level) ---

def synth_one(args):
    """Run one synthesis: returns dict with resources."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.synthesizers import synthesize
    from src.factor_plan import SearchConfig
    from src.bool_func import BooleanFunction

    name, n, tt_hex, method, model_path = args
    bf = BooleanFunction(n, int(tt_hex, 16))
    config = SearchConfig()
    t0 = time.time()
    r = synthesize(method, bf, config, seed=42, model_path=model_path or '')
    elapsed = time.time() - t0
    return {
        'name': name, 'n': n, 'method': method, 'model_path': model_path,
        'score': r.cost.score(config.weights),
        'T': r.cost.T, 'CNOT': r.cost.CNOT,
        'depth': r.cost.depth, 'peak_ancilla': r.cost.peak_ancilla,
        'correct': r.correct, 'time_s': elapsed,
    }

AES_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]

OUTPUT_DIR = _PROJ_ROOT / "results"
LOG = _PROJ_ROOT / "tmp" / "parallel_experiments.log"

def log(msg):
    with open(LOG, 'a') as f:
        f.write(msg + '\n')
    print(msg, flush=True)

def build_tasks():
    tasks = []
    # --- AES S-box: 8 bits x 2 methods (direct + resource) ---
    for bit in range(8):
        tt = 0
        for x in range(256):
            if (AES_SBOX[x] >> bit) & 1:
                tt |= (1 << x)
        name = f'aes_sbox_bit{bit}'
        tt_hex = hex(tt)
        tasks.append((name, 8, tt_hex, 'and_direct_anf', ''))
        tasks.append((name, 8, tt_hex, 'and_resource_nmcts', 'models/action_scorer_v2.pt'))

    # --- Large neural prior: n=8 (20 funcs) + n=10 (10 funcs) ---
    rng = random.Random(42)
    for n in [8, 10]:
        n_funcs = 20 if n == 8 else 10
        for i in range(n_funcs):
            from src.anf_utils import random_truth_function
            bf = random_truth_function(n, rng)
            while bf.truth_table == 0:
                bf = random_truth_function(n, rng)
            name = f'large_n{n}_{i}'
            tt_hex = hex(bf.truth_table)
            # no-prior, v2, 8 random seeds = 10 tasks per function
            tasks.append((name, n, tt_hex, 'and_resource_nmcts', ''))
            tasks.append((name, n, tt_hex, 'and_resource_nmcts', 'models/action_scorer_v2.pt'))
            for seed in range(8):
                tasks.append((name, n, tt_hex, 'and_resource_nmcts', f'random-prior:{seed}'))

    return tasks

def main():
    LOG.write_text("")
    tasks = build_tasks()
    log(f"Total tasks: {len(tasks)}")
    log(f"Workers: {min(14, os.cpu_count() or 14)}")

    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=14) as ex:
        futures = {ex.submit(synth_one, task): task for task in tasks}
        done = 0
        for fut in as_completed(futures):
            try:
                res = fut.result()
                results.append(res)
                done += 1
                if done % 20 == 0 or done <= 5:
                    log(f"  {done}/{len(tasks)} done ({time.time()-t0:.0f}s) - "
                        f"last: {res['name']} {res['method']} {res['model_path'][:20]} "
                        f"score={res['score']:.1f} correct={res['correct']}")
            except Exception as e:
                done += 1
                task = futures[fut]
                log(f"  ERROR {done}/{len(tasks)}: {task} -> {e}")

    elapsed = time.time() - t0
    log(f"\nAll {len(results)} tasks done in {elapsed:.0f}s")

    # Save raw results
    out_csv = OUTPUT_DIR / "raw_parallel_experiments.csv"
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    log(f"Wrote {len(results)} rows to {out_csv}")

    # --- AES S-box summary ---
    aes_rows = [r for r in results if r['name'].startswith('aes_sbox')]
    aes_summary = []
    for bit in range(8):
        name = f'aes_sbox_bit{bit}'
        direct = [r for r in aes_rows if r['name'] == name and r['method'] == 'and_direct_anf']
        resource = [r for r in aes_rows if r['name'] == name and r['method'] == 'and_resource_nmcts']
        if direct and resource:
            d, r = direct[0], resource[0]
            improve = (d['score'] - r['score']) / max(d['score'], 0.001) * 100
            aes_summary.append({
                'bit': bit, 'direct_score': round(d['score'], 2),
                'resource_score': round(r['score'], 2),
                'direct_T': d['T'], 'resource_T': r['T'],
                'improvement_pct': round(improve, 2),
                'correct': r['correct'],
            })
    if aes_summary:
        with open(OUTPUT_DIR / 'summary_aes_sbox.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=aes_summary[0].keys())
            w.writeheader()
            w.writerows(aes_summary)
        mean_imp = statistics.mean(r['improvement_pct'] for r in aes_summary)
        all_correct = all(r['correct'] for r in aes_summary)
        log(f"\n=== AES S-box: mean improvement={mean_imp:.2f}%, all correct={all_correct} ===")

    # --- Large neural prior summary ---
    for n in [8, 10]:
        large_rows = [r for r in results if r['name'].startswith(f'large_n{n}')]
        if not large_rows:
            continue
        names = sorted(set(r['name'] for r in large_rows))
        v2_scores, np_scores = [], []
        rand_scores = {s: [] for s in range(8)}
        for name in names:
            v2 = [r for r in large_rows if r['name'] == name and r['model_path'] == 'models/action_scorer_v2.pt']
            np_ = [r for r in large_rows if r['name'] == name and r['model_path'] == '']
            if v2: v2_scores.append(v2[0]['score'])
            if np_: np_scores.append(np_[0]['score'])
            for s in range(8):
                rs = [r for r in large_rows if r['name'] == name and r['model_path'] == f'random-prior:{s}']
                if rs: rand_scores[s].append(rs[0]['score'])

        if not v2_scores:
            continue
        rand_means = [statistics.mean(rand_scores[s]) for s in range(8) if rand_scores[s]]
        rand_grand = statistics.mean(rand_means) if rand_means else 0
        v2_mean = statistics.mean(v2_scores)
        np_mean = statistics.mean(np_scores) if np_scores else 0
        nf = len(v2_scores)
        w_np = sum(1 for a, b in zip(v2_scores, np_scores) if a < b)
        log(f"\n=== n={n} ({nf} funcs): V2={v2_mean:.2f} NoP={np_mean:.2f} Rand={rand_grand:.2f} ===")
        log(f"  V2 vs NoP: {w_np}/{nf-w_np} W/L, {(np_mean-v2_mean)/max(np_mean,1)*100:.3f}%")
        log(f"  V2 vs Rand: {(rand_grand-v2_mean)/max(rand_grand,1)*100:.3f}%")

    log("\nDONE")

if __name__ == "__main__":
    main()
