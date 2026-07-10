# RUNNING — gnn-sshr smoke pipeline

Copy-pasteable commands for the end-to-end smoke pipeline. All commands are
expected to be run from the `gnn-sshr/` repository root.

---

## 1. Environment setup

Two conda environments are required. Use the absolute interpreter paths
(`conda run` is unreliable on this machine).

| Purpose | Interpreter |
|---|---|
| General (data graphs, LightGBM, sshr-h, beam, MCTS) | `/opt/anaconda3/envs/mcts-qoracle/bin/python` |
| Gurobi ILP (SSHR-I teacher, pruned WP-SCP) | `/opt/anaconda3/envs/sshr/bin/python` |

Gurobi (`gurobipy`) is installed **only** in the `sshr` env; the WLS academic
license is at `~/.gurobi/gurobi.lic`.

### Missing optional deps

The block-level GNN training pipeline depends on `torch` and
`torch_geometric`, which are **not** installed in either environment. Until
those are added:

- Block GNN training scripts (`src/train/`) will fail at import time.
- Data collection, feature/graph building, the LightGBM baseline, and the
  pruned ILP search all work with the existing envs.

---

## 2. Smoke commands

Run all commands from `gnn-sshr/` (i.e. `cd /Users/zhouzixiang/Desktop/tzb/src/gnn-sshr`).
`PYTHONPATH=src` is required so module names resolve without an `src.`
prefix (e.g. `data.data_collector`, not `src.data.data_collector`).

### a. Sanity import test

```bash
cd gnn-sshr && PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -c "import sshr_core; from sshr_core.parallelotope_enum import enumerate_parallelotopes; print(len(enumerate_parallelotopes(4)))"
```

Expected output: `257` (matches Table VIII for n=4).

### b. n=3 ILP data collection (small)

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m data.data_collector --n 3 --teacher ilp --max-functions 16
```

Uses the Gurobi-backed SSHR-I teacher; requires the `sshr` env.

### c. LightGBM baseline training

```bash
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m models.lightgbm_pruner --train data/ilp/n3_ilp_cnot.csv --out results/models/lgbm_n3.txt
```

Trains a learning-to-rank pruner over the rows produced in step (b).

### d. Pruned search smoke

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m search.pruned_search --n 3 --keep-ratio 0.2
```

Runs WP-SCP over the AI-pruned candidate pool; defaults solver to `h`,
objective to `cnot`, truth table to `0xB6`. Use `sshr` env because the
default `--solver ilp` (and any pruning safeguards) reach Gurobi.

---

## 3. Expected outputs

| Path | Notes |
|---|---|
| `data/ilp/n3_ilp_cnot.csv` | ~few hundred rows for `--max-functions 16`; full n=3 sweep ≈ 12K rows |
| `results/models/lgbm_n3.txt` | Serialised LightGBM ranker (text dump) |

---

## 4. Troubleshooting

- `ModuleNotFoundError: gurobipy` — you are on the `mcts-qoracle` env.
  Switch to `/opt/anaconda3/envs/sshr/bin/python` for any ILP step.
- `ModuleNotFoundError: src.data` (or `src.models`, `src.search`) — run with
  `PYTHONPATH=src` and use the module name **without** the `src.` prefix
  (e.g. `-m data.data_collector`, not `-m src.data.data_collector`).
- Gurobi license errors — verify `~/.gurobi/gurobi.lic` exists and is
  readable; the WLS academic license file must be present for any
  `--teacher ilp` or `--solver ilp` invocation.

---

## 5. P0 GNN training & evaluation

End-to-end commands to reproduce the P0 GNN result reported in
`PROGRESS.md §7`. All run from `/Users/zhouzixiang/Desktop/tzb/src/gnn-sshr`.

### a. (Re-)collect the n=3 ILP dataset

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m data.data_collector \
    --n 3 --teacher ilp --objective cnot \
    --out-csv data/ilp/n3_ilp_cnot.csv
```

* CLI flag is `--out-csv` (not `--out`).
* Uses Gurobi via the `sshr` env. The full sweep produces 12,495 rows
  (255 functions × 49 candidates) in ~1.2s.
* The trivial all-zero onset is excluded by the enumerator — expect
  255 / 256 functions, 0 ILP failures.

### b. Train the GNN pruner (PyTorch + PyG, MPS)

```bash
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m train.train_pruner \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 --epochs 30
```

* Writes checkpoint to `results/models/gnn_pruner_n3.pt` (best by `val_loss`).
* Appends one JSON record per epoch to
  `results/logs/gnn_pruner_n3_metrics.jsonl` (truncated at start of run).
* Reference outcome: train_loss 0.348 → 0.062, best epoch 27,
  val_loss=0.1432, val_recall@10%=0.5775, val_ndcg@10%=0.5968.
* Auto-selects `mps` if available else `cpu`. CUDA is not currently wired
  through the trainer.

### c. Run the 8-method comparison

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.compare_methods \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --keep-ratio 0.2 \
    --out results/tables/p0_baselines_n3.md
```

* Must run from the `sshr` env (Gurobi import gates the ILP rows).
* All 8 rows populate when both ranker checkpoints are passed and Gurobi
  is reachable. Without `--gnn-ckpt` / `--lgb-ckpt` the corresponding row
  is reported as `skipped (no <ckpt>)`; without Gurobi all `*_pruned_ilp`
  rows are reported as `skipped (no Gurobi)`.

---

## 6. P0 troubleshooting

- **Gurobi WLS license SSL flake** — the WLS warm-up against
  `token.gurobi.com` occasionally fails with `SSL: no alternative
  certificate subject name matches target hostname` on the first 1–3
  calls. Retry up to 5× with sleep; once cached, subsequent runs are
  instant. The data-collector now retries internally.
- **`ModuleNotFoundError: torch_geometric`** — install into
  `mcts-qoracle` (CPU/MPS wheel set):
  ```bash
  /opt/anaconda3/envs/mcts-qoracle/bin/pip install torch torch_geometric
  ```
- **MPS fallback to CPU** — set `PYTORCH_ENABLE_MPS_FALLBACK=1` if any
  unsupported op trips the trainer. The current pruner uses only standard
  ops (Linear, ReLU, LayerNorm, SAGEConv) and trains cleanly on MPS.
- **LightGBM `image not found: libomp.dylib`** — the `sshr` env needs a
  `libomp.dylib` symlink visible to lightgbm. Install once:
  `brew install libomp` and symlink under the env's `lib/` if necessary.
- **`compare_methods.py` reports all ILP rows skipped** — you ran from
  `mcts-qoracle`. Switch to the `sshr` env (`gurobipy` only lives there).
- **`rule_pruned_ilp` shows tiny CNOT total but huge `n_skipped`** — the
  rule-based pruner is too aggressive at `keep_ratio=0.2`; expect ~240
  infeasible skips and a misleadingly small CNOT sum. This is documented
  behaviour, not a bug.

---

## 7. P0.1 commands (June 13 2026)

End-to-end commands to reproduce PROGRESS §8. All run from
`/Users/zhouzixiang/Desktop/tzb/src/gnn-sshr`. The
`src/search/pruned_search.py` coverage-repair fix is now baked in;
re-running these with the existing checkpoints produces the post-fix
numbers cited in PROGRESS §8.

### a. n=3 coverage-fix re-eval (post-fix headline table)

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.compare_methods \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --keep-ratio 0.2 \
    --out results/tables/p0_baselines_n3_v2.md
```

Acceptance: `n_skipped == 0` for `rule_pruned_ilp`, `lgb_pruned_ilp`,
`gnn_pruned_ilp`. Verbatim post-fix totals: rule 8448 / lgb 4083
(after subset re-aggregation, see step b) / gnn 6694.

### b. n=3 common-subset run

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.compare_methods \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --keep-ratio 0.2 \
    --require-common-subset \
    --out results/tables/p0_baselines_n3_common.md
```

Emits a second markdown section "Common-feasible subset (|S|=255)" plus
`results/tables/p0_per_function_diff_n3.csv` (per-function gnn/lgb CNOT
diff). With the singleton-injection repair `|S|` equals the full eval
set (255 at n=3, 221 at n=4), so the subset table matches the headline.

### c. n=3 keep_ratio sweep

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --ratios 0.10,0.15,0.20,0.30,0.50 \
    --out    results/tables/keep_ratio_sweep_n3.csv \
    --out-md results/tables/keep_ratio_sweep_n3.md
```

Reference best CNOT (min subject to `n_skipped ≤ 10`): rule = 3439 @
0.50, lgb = 3354 @ 0.50, gnn = 3664 @ 0.50.

### d. n=4 ILP data collection (NPN reps)

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m data.data_collector \
    --n 4 --teacher ilp --objective cnot \
    --out-csv data/ilp/n4_ilp_cnot.csv
```

Output: 56,797 rows = 221 NPN-rep funcs × 257 candidates, 0 ILP
failures. Trivial all-zero onset excluded by the enumerator.

### e. n=4 LGB + GNN training

```bash
# LightGBM baseline
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m models.lightgbm_pruner \
    --train data/ilp/n4_ilp_cnot.csv \
    --out   results/models/lgbm_n4.txt

# GNN pruner (50 epochs, MPS / CPU)
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m train.train_pruner \
    --csv data/ilp/n4_ilp_cnot.csv --n 4 --epochs 50
```

Reference outcome (`results/logs/gnn_pruner_n4_metrics.jsonl`): best
epoch 34, val_loss = 0.2017, val_recall@10% = 0.568,
val_ndcg@10% = 0.393. Checkpoint `results/models/gnn_pruner_n4.pt`.

### f. n=4 comparison + sweep

```bash
# Headline table @ keep=0.20
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.compare_methods \
    --csv data/ilp/n4_ilp_cnot.csv --n 4 \
    --gnn-ckpt results/models/gnn_pruner_n4.pt \
    --lgb-ckpt results/models/lgbm_n4.txt \
    --keep-ratio 0.2 \
    --out results/tables/p0_baselines_n4.md

# keep_ratio sweep
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n4_ilp_cnot.csv --n 4 \
    --gnn-ckpt results/models/gnn_pruner_n4.pt \
    --lgb-ckpt results/models/lgbm_n4.txt \
    --ratios 0.10,0.15,0.20,0.30 \
    --out    results/tables/keep_ratio_sweep_n4.csv \
    --out-md results/tables/keep_ratio_sweep_n4.md
```

Reference best CNOT (`n_skipped == 0`): lgb = 5267 @ 0.30, gnn = 5509 @
0.30. Both pruned methods beat paper SSHR-H (6540) and our SSHR-H
(6064) at this ratio.

---

## 8. P0.2 commands (June 13 2026)

End-to-end commands to reproduce PROGRESS §9 (cost-aware 11-dim GNN,
ancilla-sum aggregation, n=3/n=4 retrain, n=5 first run). All run from
`/Users/zhouzixiang/Desktop/tzb/src/gnn-sshr`. The 11-dim candidate
features in `src/data/graph_builder.py` (§9.1 of DESIGN) and the
`_aggregate_costs` ancilla-sum change (§10 of DESIGN) are baked in.

### a. n=3 retrain (11-dim cost-aware GNN)

```bash
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m train.train_pruner \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 --epochs 50

PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --ratios 0.10,0.15,0.20,0.30,0.50 \
    --out    results/tables/keep_ratio_sweep_n3_v3.csv \
    --out-md results/tables/keep_ratio_sweep_n3_v3.md
```

Reference best CNOT (min subject to `n_skipped ≤ 10`): rule = 3439 @
0.50, lgb = 3354 @ 0.50, **gnn = 3232 @ 0.50** (GNN beats LGB by
3.64 %). Reference training: best epoch 42, val_loss=0.0696,
val_recall@10%=0.7480, val_ndcg@10%=0.7170.

### b. n=4 retrain — P0 PASS/FAIL decision point

```bash
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m train.train_pruner \
    --csv data/ilp/n4_ilp_cnot.csv --n 4 --epochs 50

PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n4_ilp_cnot.csv --n 4 \
    --gnn-ckpt results/models/gnn_pruner_n4.pt \
    --lgb-ckpt results/models/lgbm_n4.txt \
    --ratios 0.10,0.15,0.20,0.30,0.50 \
    --out    results/tables/keep_ratio_sweep_n4_v2.csv \
    --out-md results/tables/keep_ratio_sweep_n4_v2.md
```

Reference best CNOT (`n_skipped == 0`): lgb = 4939 @ 0.50, gnn = 5079 @
0.50. GNN/LGB = 1.0283 — **misses §5.2 "≤ 2 %" tolerance by 0.83 pp**
(n=4 P0: FAIL). Reference training: best epoch 35, val_loss=0.1590,
val_recall@10%=0.7250, val_ndcg@10%=0.5228.

### c. n=5 ILP data collection (first time at this scale)

```bash
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m data.data_collector \
    --n 5 --teacher ilp --objective cnot \
    --out-csv data/ilp/n5_ilp_cnot.csv
```

Output: 928,017 rows, 603 functions, 1,539 candidates each. Positive
label rate 0.140 % (1295 positives). This is the first n=5 run; no NPN
reduction is available so the function count is the raw random sample.

### d. n=5 GNN training + 100-function subset sweep

```bash
# GNN training on the full 603-function dataset (50 epochs, MPS)
PYTHONPATH=src /opt/anaconda3/envs/mcts-qoracle/bin/python -m train.train_pruner \
    --csv data/ilp/n5_ilp_cnot.csv --n 5 --epochs 50

# Sweep on a 100-function subset (153,900 rows) to keep wallclock bounded
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n5_ilp_cnot_100sub.csv --n 5 \
    --gnn-ckpt results/models/gnn_pruner_n5.pt \
    --lgb-ckpt results/models/lgbm_n5.txt \
    --ratios 0.05,0.10,0.15,0.20 \
    --out    results/tables/keep_ratio_sweep_n5.csv \
    --out-md results/tables/keep_ratio_sweep_n5.md
```

Reference best CNOT (`n_skipped == 0`): lgb = 2658 @ 0.10,
gnn = 2658 @ 0.20 — **exact tie on CNOT** (n=5 P0: PASS). GNN wins on
T (5379 vs 5396) and Anc (267 vs 268). Reference training: best epoch
29, val_loss=0.0036, val_recall@10%=1.0000, val_ndcg@10%=0.7941. Note
the 100-fn subset CSV is produced by sub-sampling the full
`n5_ilp_cnot.csv` to 100 distinct `func_id`s before the sweep.
