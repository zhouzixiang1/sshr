# gnn-sshr Module-Level Design

Concrete interface design for the GNN-augmented SSHR pipeline. This document
records the actual function signatures and data layouts that exist today, plus
the planned PyG / PyTorch components that hang off them.

## 1. Module Map

| File | Public API | Caller(s) |
|---|---|---|
| `src/sshr_core/bool_func.py` | `BooleanFunction(n, truth_table)`, `QuantumCircuit`, `mct_cost`, `mct_cost_rp` | All teachers, encoders, search wrappers |
| `src/sshr_core/parallelotope.py` | `Parallelotope(v0, basis)`; `.vertices()`, `.dim`, `__len__` | Enumerator, encoders, search wrappers |
| `src/sshr_core/parallelotope_enum.py` | `enumerate_parallelotopes(universe, n, include_singletons=False)` | All teachers and graph builder |
| `src/sshr_core/block_synth.py` | `block_cnot_cost(p, n)`, `block_t_cost(p, n)`, `synth_block(p, n)` | Feature encoder, ILP wrapper, pruning cost-key |
| `src/sshr_core/sshr_h.py` | `sshr_h(bf, R=...)`; `_full_hypercube_parallelotopes(n)` | Teacher (`h`) in data_collector; fall-back solver in `run_pruned` |
| `src/sshr_core/sshr_i.py` | `_solve_ilp_gurobi`, `_solve_ilp_gurobi_t_then_cnot`, `block_t_cost_rp` | Teacher (`ilp`) and `_run_ilp_pruned` |
| `src/sshr_core/sshr_beam.py` | `sshr_beam(bf, ...)`, `_BeamEngine` | Teacher (`beam`) and `run_pruned(solver="beam")` |
| `src/data/feature_encoder.py` | `candidate_features(bf, candidates) -> np.ndarray (m, 14)`, `FEATURE_NAMES`, `NUM_FEATURES` | data_collector; LightGBM training; future ablations |
| `src/data/graph_builder.py` | `build_bipartite_graph(bf, candidates) -> dict`, `PARITY_FEATURE_NAMES`, `CANDIDATE_FEATURE_NAMES` | (planned) GNN dataloader; smoke CLI |
| `src/data/data_collector.py` | `collect(n, teacher, max_functions, out_csv, objective, timeout, seed, flush_every) -> pd.DataFrame`; CLI `python -m src.data.data_collector` | Offline dataset generation |
| `src/models/lightgbm_pruner.py` | `LightGBMPruner(params).fit(df, feature_cols, label_col, group_col)`, `.predict(df, feature_cols)`, `.save(path)`, `.load(path)`; CLI | Trains P0 ranker; consumed by `run_pruned` via `scores=` |
| `src/search/pruned_search.py` | `prune_candidates(candidates, scores, keep_ratio, ensure_coverage, onset, n) -> list[int]`; `run_pruned(bf, scores, keep_ratio, solver, ensure_coverage, **solver_kwargs) -> dict` | Evaluation harness; future GNN inference path |

## 2. Data Formats

### 2.1 Per-function CSV row schema (training data)

Written by `data_collector.collect`. One row per (function, candidate) pair.
Columns (in order; see `_csv_columns`):

| Column | Type | Source | Meaning |
|---|---|---|---|
| `func_id` | int | enumeration index | Used as LightGBM group key |
| `n` | int | `bf.n` | Variable count |
| `truth_table_hex` | str | `f"{bf.truth_table:0wX}"` | Onset bitmask, hex-formatted |
| `num_candidates` | int | `len(candidates)` | Same for all rows of a function |
| `on_size` | int | `len(bf.onset)` | |
| `optimal_cost` | float | teacher total cost (CNOT or T) | Constant within group |
| `cand_idx` | int | row index in candidate list | Stable across rows of the same function |
| `cand_dim` | int | `len(cand.basis)` | |
| `cand_size` | int | `1 << dim` | |
| `label` | int | `1` if candidate selected by teacher else `0` | Target |
| 14 feature cols | float | `feature_encoder.FEATURE_NAMES` | See section 3 |

Default path: `<repo>/data/ilp/n{n}_{teacher}_{objective}.csv`. Written
incrementally every `flush_every` functions.

### 2.2 Bipartite graph dict (`build_bipartite_graph` output)

```python
{
  "n":              int,                   # variable count
  "num_parity":     2 ** n,                # |V_parity|
  "num_candidates": len(candidates),       # |V_cand|
  "parity_features":    np.float32 (2**n, 5),
  "candidate_features": np.float32 (m, 11),
  "cover_edges":        np.int64  (2, E_cover),    # row 0 parity, row 1 cand
  "hypercube_edges":    np.int64  (2, n * 2**(n-1)) # u<v Hamming-1 pairs
}
```

`cover_edges[0, e] = parity index k` and `cover_edges[1, e] = candidate index j`
iff minterm `k` is a vertex of parallelotope `j`. `hypercube_edges` is
candidate-independent and depends only on `n`.

### 2.3 PyG `HeteroData` layout (planned, candidate_pruner)

Wrapping the dict above:

```python
data = HeteroData()
data['parity'].x      = torch.from_numpy(graph['parity_features'])     # (2**n, 5)
data['cand'].x        = torch.from_numpy(graph['candidate_features'])  # (m, 11)
data['parity', 'covers',  'cand'  ].edge_index = graph['cover_edges']
data['cand',   'covered', 'parity'].edge_index = graph['cover_edges'][[1, 0]]
data['parity', 'adj',     'parity'].edge_index = bidirectional(graph['hypercube_edges'])
data['cand'].y      = torch.from_numpy(label_array)         # 0/1 from teacher
data['cand'].group  = torch.full((m,), func_id)             # for ranking loss
```

Mini-batches built via `torch_geometric.loader.DataLoader` so multiple
functions are concatenated as block-diagonal hetero-graphs.

### 2.4 Value Network input format (planned)

Per-state input for the AI-Guided Beam value head:

```python
{
  "state_mask":   uint64       # remaining onset bitmask A
  "graph":        HeteroData,  # built from (bf restricted to A, candidates)
  "history":      LongTensor (T_max,) # action ids taken so far, padded with -1
  "step":         int,         # |history|
  "lower_bound":  float,       # engine.greedy_lb(A) precomputed
}
```

Output: scalar predicted optimal cost-to-go. Trained on
`(state, optimal_cost - cost_so_far)` pairs harvested from ILP teacher rollouts.

## 3. Feature Catalog

### 3.1 Parity-node features (`graph_builder`, K=5)

| Idx | Name | Definition |
|---|---|---|
| 0 | `is_onset` | `1.0` iff bit `k` of truth table is set |
| 1 | `hamming_weight` | `popcount(k)` |
| 2 | `neighbor_onset_ratio` | Fraction of `n` Hamming-1 neighbours of `k` in onset |
| 3 | `cover_count` | Number of candidates covering minterm `k` |
| 4 | `n` | Constant variable count (broadcast feature) |

### 3.2 Candidate-node features (`graph_builder`, K=11)

| Idx | Name | Definition |
|---|---|---|
| 0 | `dim` | `len(p.basis)` |
| 1 | `size` | `len(p.vertices())` = `2**dim` |
| 2 | `log2_size` | `log2(max(size, 1))` |
| 3 | `on_overlap` | `|verts ∩ onset|` |
| 4 | `off_overlap` | `size - on_overlap` |
| 5 | `on_ratio` | `on_overlap / size` (0 if `size==0`) |
| 6 | `dim_density` | `on_overlap / 2**dim` |
| 7 | `is_singleton` | `1.0` iff `dim == 0` |
| 8 | `cnot_cost` | `block_cnot_cost(p, n)` — exact per-block CNOT count (P0.2) |
| 9 | `t_cost` | `block_t_cost(p, n)` — exact per-block T count (P0.2) |
| 10 | `control_count` | `popcount(v0) + dim` — MCT control width (P0.2) |

Indices 0–7 are the original 8 geometric features; indices 8–10 are the
three **cost-aware features** added in P0.2 (see PROGRESS §9.1). They
are appended (not interleaved) so 8-dim P0.1 checkpoints still load,
surfacing a column-count warning. The cost columns come from
`sshr_core.block_synth.{block_cnot_cost, block_t_cost}`, which the audit
in `results/notes/cost_model_audit.md` verified byte-identical to paper
Table II. Adding them lifted n=3 GNN `val_recall@10%` from 0.5775 →
0.7480 and n=4 from 0.5680 → 0.7250.

### 3.3 Hand-crafted candidate features (`feature_encoder`, K=14)

Used by the LightGBM baseline and stored in the training CSV.

| Idx | Name | Definition |
|---|---|---|
| 0 | `dim` | as above |
| 1 | `size` | `len(verts)` (singletons treated as 1) |
| 2 | `log2_size` | equal to `dim` for parallelotopes |
| 3 | `on_overlap` | `|verts ∩ bf.onset|` |
| 4 | `off_overlap` | `|verts ∩ bf.offset|` |
| 5 | `on_ratio` | `on_overlap / size` |
| 6 | `cnot_cost_estimate` | `2 * max(0, dim-1) + 2 * popcount(v0)` |
| 7 | `t_cost_estimate` | `4 * max(0, dim-1)` |
| 8 | `control_count` | `popcount(v0) + dim` |
| 9 | `is_singleton` | `1.0` iff `dim == 0` |
| 10 | `overlap_ratio` | `(on_overlap + off_overlap) / size` (≈1 always) |
| 11 | `off_ratio` | `off_overlap / size` |
| 12 | `position_entropy` | Mean per-bit Shannon entropy across vertex bits |
| 13 | `structural_rarity` | `1 / |{c : dim(c) == dim(p)}|` over the candidate pool |

`position_entropy` for vertex set V on `n` variables: for each bit `b`, let
`p_b = |{v in V : v_b = 1}| / |V|`; entropy is the average of
`-p log2 p - (1-p) log2 (1-p)` across `b ∈ [0, n)`.

## 4. Teacher Solvers

All teachers are dispatched from `data_collector.collect(teacher=...)` and
return `(chosen_blocks: list[Parallelotope], total_cost: float)`. The block
list is hashed by `_block_key(p) = (v0, sorted(basis))` to recover the
binary `label` column.

### 4.1 `sshr_i` — ILP, exact, Gurobi-required

Wrapper: `data_collector._run_ilp_teacher(bf, objective, timeout)`.

* Reuses the candidate construction from `sshr_i._ilp_core`: enumerate
  dim≥1 parallelotopes over the full hypercube, append per-minterm
  singletons, then drop blocks that do not touch the onset.
* `objective="cnot"` calls `_solve_ilp_gurobi(parallelotopes, all_minterms,
  onset, costs, timeout)`.
* `objective="t"` first tries `_solve_ilp_gurobi_t_then_cnot` (lex T then
  CNOT) and falls back to plain ILP on T cost if infeasible.
* Total cost computed by summing `block_cnot_cost` or `block_t_cost_rp`
  over the selected blocks.
* Requires `gurobipy`; only available in the `sshr` conda env.

### 4.2 `sshr_beam` — heuristic, fast, monotone semantics

Wrapper: `data_collector._run_beam_teacher(bf, beam_width=8, objective)`.

* Drives `_BeamEngine` directly so action paths can be captured.
* State: `(cost + greedy_lb, uid, A_mask, cost, path)`. `A_mask` is the
  remaining onset bitmask.
* At each step: top-`branch=5` actions per state, then keep top
  `beam_width=8` by lower-bound-augmented cost.
* Termination: any state with `A_mask==0` (best by raw cost) or
  `max_steps = popcount(A0) + 1`.
* If a state has no actions, fills the rest with singletons.
* Monotone subset-removal semantics — different from XOR. Do not mix with
  XOR-derived labels in the same training run.

### 4.3 `sshr_h` — greedy, XOR semantics

Wrapper: `data_collector._run_h_teacher(bf)`.

* Hard-coded threshold `R = 3/4`.
* Iterates the full-hypercube candidate pool from
  `_full_hypercube_parallelotopes(n)`; picks the first candidate with
  `|verts ∩ A| / |verts| >= R` (deterministic order from the enumerator).
* Update is XOR: `A ^= pick.vertices()`. Off-set contamination can cascade.
* Adds singletons to mop up remaining `A` if no candidate qualifies.
* Cost reported as the CNOT total.

## 5. Pruning Algorithm

Implemented in `src/search/pruned_search.py::prune_candidates`. End-to-end
flow in `run_pruned`:

```
def prune_candidates(candidates, scores, keep_ratio, ensure_coverage=True,
                     onset=None, n=None) -> list[int]:
    m = len(candidates)
    assert len(scores) == m
    keep_ratio = clamp(keep_ratio, 0, 1)
    k = max(1, round(keep_ratio * m))
    order = argsort_desc(scores)
    kept  = set(order[:k])

    if ensure_coverage:
        covered = union(candidates[i].vertices() for i in kept)
        for v in onset:
            if v in covered:
                continue
            best = argmin over i not in kept,
                            v in candidates[i].vertices(),
                            key = (dim, size, block_cnot_cost(p, n), i)
            if best is not None:
                kept.add(best)
                covered |= candidates[best].vertices()

    return sorted(kept)
```

Combined with the runner:

```
def run_pruned(bf, scores, keep_ratio=0.1, solver="ilp",
               ensure_coverage=True, **solver_kwargs):
    candidates = _enumerate_with_singletons(bf)
    assert len(scores) == len(candidates)
    kept_idx = prune_candidates(candidates, scores, keep_ratio,
                                ensure_coverage, onset=bf.onset, n=bf.n)
    pruned   = [candidates[i] for i in kept_idx]
    if not _check_feasible(pruned, bf.onset):       # safety net
        return {"kept": ..., "cost": -1, "feasible": False, ...}
    if solver == "ilp":   circ = _run_ilp_pruned(bf, pruned, objective, timeout)
    elif solver == "beam": circ = sshr_beam(bf, ...)        # full enum (limitation)
    elif solver == "h":    circ = sshr_h(bf, R=...)         # full enum (limitation)
    return {"kept": len(pruned), "cost": _circuit_cost(circ, objective),
            "time_s": elapsed, "feasible": ...}
```

The "safety singletons" requirement is realised through the fall-back loop
that reinserts a covering candidate (preferring `dim=0`) for every uncovered
onset minterm. The feasibility check before solver dispatch protects WP-SCP
from being handed an infeasible instance.

Note: only `solver="ilp"` truly consumes the pruned set today;
`beam` and `h` re-enumerate internally.

## 6. Model Architectures

### 6.1 Candidate pruner — HeteroGraphSAGE (implemented)

**File**: `src/models/candidate_pruner.py` (238 LoC). **Import**:
`from models.candidate_pruner import CandidatePruner` (with `PYTHONPATH=src`).

Implementation closely follows the original sketch but uses a single
`HeteroConv` per layer that wraps three `SAGEConv` modules — one per relation
in the hetero graph:

| Relation | edge_type | Source | Target |
|---|---|---|---|
| covers | `("parity", "covers", "cand")` | parity | cand |
| covered | `("cand", "covered", "parity")` | cand | parity |
| adj | `("parity", "adj", "parity")` | parity | parity |

The `dict_to_hetero` helper duplicates the (sorted) hypercube edge list into
both `(u→v)` and `(v→u)` so the `adj` SAGEConv sees a symmetric graph.
Forward pass:

```
parity_x = Linear(5  -> H)(parity_in)        # ReLU + LayerNorm
cand_x   = Linear(11 -> H)(cand_in)          # ReLU + LayerNorm
for layer in 1..L:
    h = HeteroConv({covers, covered, adj} : SAGEConv(H -> H))(h, edge_index)
    h = {k: LayerNorm(ReLU(v)) for k, v in h.items()}
score = MLP_2L([cand_h, mean(parity_h).expand(m), max(parity_h).expand(m)]) -> R
```

* Defaults: `H=64`, `L=2`, dropout 0.1.
* Returns `Tensor (m,)` with un-normalised logits; the pruner downstream
  feeds `score.detach().cpu().numpy()` into
  `prune_candidates(..., scores=...)`.
* Supports variable `n` (parity count is `2**n`, candidate count is
  per-function, parity-pooling is global so the head shape is invariant).
* Smoke test on n=3 / `tt=0x05` returns shape `torch.Size([49])` matching
  Table VIII (49 candidates).

### 6.2 Value network — GIN + MLP

Used by AI-Guided Beam to score whole search states.

```
node_in   : Linear(d_x -> H)
for layer in 1..L:
    h = GINConv(MLP(2H -> H))(h, edge_index)
    h = ReLU(LayerNorm(h))
graph_h   = mean(h) ⊕ max(h) ⊕ sum(h)
state_h   = MLP([graph_h, action_history_emb, step_emb, lb_scalar])
value     = Linear(state_h -> 1)
```

* `action_history_emb` is a learnt embedding sequence pooled with a
  small Transformer encoder (or simple mean) over the partial path.
* `lb_scalar` is `engine.greedy_lb(A)` — provides a strong shortcut signal.

### 6.3 Trainer (implemented)

**File**: `src/train/train_pruner.py` (607 LoC). **CLI**:

```
train_pruner.py --csv <path> --n <int>
                [--epochs --batch-size --hidden --layers --dropout --lr
                 --weight-decay --warmup-epochs --clip-norm
                 --pairwise-weight --keep-ratio --val-frac
                 --out --log --seed]
```

* **Dataset**: Groups the CSV by `func_id`, sorts each group by `cand_idx`,
  reconstructs `BooleanFunction(n, int(truth_table_hex, 16))`, enumerates
  parallelotopes with `include_singletons=True`, places labels into a dense
  `(m,)` vector by `cand_idx`, builds a `HeteroData` via `dict_to_hetero`,
  and stashes `data['cand'].func_id` so the func id survives PyG batching.
* **Loss**:
  ```
  L = focal_bce_with_logits(score, label, alpha=0.25, gamma=2)
    + 0.5 * pairwise_margin_loss
  ```
  The pairwise term samples up to 256 (positive, negative) pairs per
  function with replacement and applies `softplus(neg_score - pos_score)`.
* **Optimisation**: AdamW (`lr=3e-4`, `weight_decay=1e-2`), cosine
  annealing with 5-epoch linear warm-up, grad-clip max-norm 1.0,
  device = `mps` if available else `cpu`. The trainer does not currently
  exercise `cuda.amp`.
* **Per-function forward**: `CandidatePruner` pools parity nodes globally,
  so `_forward_batch` calls `batch.to_data_list()` and forwards each
  function's graph independently before concatenating scores / labels /
  fids. Semantically equivalent to per-function inference; allows
  variable candidate counts per function within a batch.
* **Validation**: last 20% of sorted `func_id`s by default
  (`--val-frac 0.2`). Reports `val_loss`, `val_recall@10%`, `val_ndcg@10%`
  with `k = ceil(0.10 * m)` per function, then averaged across val funcs.
* **Outputs**:
  * Best-by-`val_loss` checkpoint to
    `results/models/gnn_pruner_n{n}.pt` (state_dict + hparams).
  * Per-epoch metrics appended (one JSON record per line) to
    `results/logs/gnn_pruner_n{n}_metrics.jsonl` (truncated at run start).
* **n=3 reference run** (`--n 3 --epochs 30`, default hparams): 30 epochs,
  204 train / 51 val funcs, MPS device, no NaNs. Train loss
  0.348 → 0.062, best `val_loss=0.1432` at epoch 27,
  `val_recall@10%=0.5775`, `val_ndcg@10%=0.5968`. Checkpoint 1.4 MB.

## 7. Training Procedure (Planned)

### 7.1 Losses

* **Pruner**: per-group ranking + per-row classification.
  ```
  L = α * focal_bce(score, label, γ=2)
    + β * pairwise_lambdarank(score_per_func, label_per_func)
  ```
  with `α=1.0, β=0.5`. Mirrors LightGBM's LambdaRank fall-back to BCE in
  `LightGBMPruner.fit` when groups are too small.

* **Value net**: Huber regression onto teacher cost-to-go,
  `L = HuberLoss(value, optimal_cost - cost_so_far)`.

### 7.2 Optimisation

* Optimiser: AdamW, `lr=3e-4`, `weight_decay=1e-2`.
* Schedule: cosine annealing with linear 5-epoch warm-up, `T_max = epochs`.
* Gradient clipping: `max_norm=1.0`.
* Mixed precision (`torch.cuda.amp`) when GPU is available.

### 7.3 Datasets and splits

* Functions partitioned 80/10/10 by `func_id` (LightGBM's `group_col`).
* Stratify by `n` so each split contains every variable count.
* For n=4, NPN representatives from `npn_reps_n4.NPN_REPS_N4` are preferred
  to remove function-equivalence redundancy.

### 7.4 Evaluation metrics

* `kept` (fraction of candidates retained) at fixed `keep_ratio`.
* `coverage_repair_rate` (how often `ensure_coverage` adds back blocks).
* `cost_gap = (cost_pruned - cost_full_ILP) / cost_full_ILP`.
* `wallclock_speedup` of pruned WP-SCP vs full ILP.
* nDCG@k of teacher-selected blocks against ranker scores.

## 8. P0.1 Coverage-Repair & Sweep Modules (June 13 2026)

### 8.1 `pruned_search.prune_candidates` — singleton-injection repair

The original `ensure_coverage` branch did set-union containment, which
is **insufficient** for WP-SCP. Replaced (`src/search/pruned_search.py`
lines 105–167) with onset-singleton injection:

```
if ensure_coverage:
    if onset is None:
        raise ValueError("ensure_coverage=True requires `onset`.")
    # Index every dim==0 candidate by its single vertex.
    singleton_idx = {p.vertex(): i for i, p in enumerate(candidates)
                                       if p.dim == 0}
    for v in onset:
        si = singleton_idx.get(v)
        if si is not None:
            kept.add(si)                # GF(2) unit vector — span guarantee
        else:
            # Fallback: cheapest covering candidate, ordered by
            # (dim, size, block_cnot_cost(p, n), idx).
            best_idx = argmin_over { i not in kept,
                                     v in candidates[i].vertices() }
            if best_idx is not None:
                kept.add(best_idx)
```

`_enumerate_with_singletons` (lines 175–188) already appends a singleton
parallelotope `Parallelotope(v, [])` for every minterm, so the primary
branch is always reachable — the fallback exists only for defensive
robustness (e.g. external callers that hand-build the candidate list).

Singletons are GF(2) unit vectors, so the trivial cover "select exactly
the onset singletons" is always available to Gurobi: WP-SCP feasibility
is now a *post-condition* of `ensure_coverage=True`. The `n_skipped`
column accordingly drops to 0 at every swept `keep_ratio` (see
`results/tables/keep_ratio_sweep_n{3,4}.md`).

### 8.2 `compare_methods --require-common-subset`

Flag added to `src/eval/compare_methods.py` (CLI definition at
line 730). When set, after `compare_methods(...)` produces the headline
rows the harness:

1. Calls `compute_common_subset(rows)` (line 488), which intersects the
   per-function feasible sets across `PRUNED_METHODS = ("rule_pruned_ilp",
   "lgb_pruned_ilp", "gnn_pruned_ilp")`. Methods with empty `per_func`
   (e.g. skipped due to missing checkpoint or Gurobi) are excluded so
   the intersection does not collapse to `∅`.
2. Calls `reaggregate_on_subset(rows, common, n)` (line 510), which
   rebuilds Row totals (T, CNOT, Anc, time_s) by summing per-function
   contributions only over `common`. Paper / heuristic rows that lack
   `per_func` are passed through with a note flag.
3. Emits a second markdown section "Common-feasible subset (|S|=...)"
   alongside the original table, plus
   `results/tables/p0_per_function_diff_n{n}.csv` containing
   `(func_id, truth_table_hex, gnn_cnot, lgb_cnot, diff_gnn_minus_lgb)`
   one row per function in `common`.

This decouples ranker-quality comparison from feasibility-rate
differences: with the singleton-injection repair `|S|=255` at n=3 and
`|S|=221` at n=4, so the totals match the headline table exactly, but
the harness retains the diff CSV for per-function diagnosis.

### 8.3 `src/eval/keep_ratio_sweep.py`

New harness (324 LoC) that iterates `--ratios` × `{rule, lgb, gnn}` and
runs the pruned-ILP pipeline against every truth table in
`build_test_set(...)`. Implementation reuses `_run_pruned_ilp_method`,
`_rule_scores`, `_lgb_score_fn`, `_gnn_score_fn` from
`eval.compare_methods`, never duplicating the pruning internals.

CLI:

```
PYTHONPATH=src /opt/anaconda3/envs/sshr/bin/python -m eval.keep_ratio_sweep \
    --csv data/ilp/n3_ilp_cnot.csv --n 3 \
    --gnn-ckpt results/models/gnn_pruner_n3.pt \
    --lgb-ckpt results/models/lgbm_n3.txt \
    --ratios 0.10,0.15,0.20,0.30,0.50 \
    --out    results/tables/keep_ratio_sweep_n3.csv \
    --out-md results/tables/keep_ratio_sweep_n3.md
```

CSV columns: `(ratio, method, n_evaluated, n_skipped, T_total,
CNOT_total, Anc_total, wallclock_s)`. Markdown emits two pivot tables
("CNOT_total by ratio × method", "n_skipped by ratio × method") plus a
"Recommended operating point" block selecting `min CNOT s.t.
n_skipped ≤ 10` per method.

## 9. P0.2 Cost-Aware Candidate Features (June 13 2026)

### 9.1 Three cost-aware columns

`graph_builder.CANDIDATE_FEATURE_NAMES` extended from 8 → **11 dims** by
appending `cnot_cost`, `t_cost`, `control_count` (see §3.2). The
per-block cost values come from
`sshr_core.block_synth.{block_cnot_cost, block_t_cost}`, which
`results/notes/cost_model_audit.md` verified byte-identical to paper
Table II. These are *exact* per-block costs, not the 14-dim estimates
in `feature_encoder.py` (`cnot_cost_estimate`,
`t_cost_estimate`) — they replace the proxies in the GNN's input only;
the LightGBM baseline still consumes the 14-dim `feature_encoder`
columns from the CSV.

### 9.2 Effect

GNN `val_recall@10%` before / after the feature widening
(best-by-`val_loss` epoch from `results/logs/gnn_pruner_n{3,4}_metrics.jsonl`):

| n | 8-dim (P0.1) | 11-dim (P0.2) |
|---|---|---|
| 3 | 0.5775 | 0.7480 |
| 4 | 0.5680 | 0.7250 |

End-to-end CNOT impact is recorded in PROGRESS §9.4–9.6 (n=3 PASS,
n=4 FAIL by 0.83 pp, n=5 PASS).

## 10. P0.2 Ancilla Aggregation (June 13 2026)

`src/eval/compare_methods.py:_aggregate_costs` was changed from
`anc = max(anc, d.get("ancilla", 0))` (per-function peak) to
`anc += int(d.get("ancilla", 0))` (cumulative sum across the test set),
matching the paper convention identified in
`results/notes/cost_model_audit.md`. The paper Table V "Ancillary"
column is the cumulative sum of per-function ancilla, each of which is
itself the cumulative sum over the circuit's blocks (1 per 3-MCT,
`⌈(k-2)/2⌉` per k-MCT for k≥4).

After the fix `our_sshr_h` n=3 Anc goes from `1` → **128**, exactly
matching paper Table V. CNOT/T columns are unchanged (the edit only
touches the ancilla accumulator). The downstream effect is visible in
PROGRESS §9.4 / §9.5 / §9.6 where the sweep tables now report
`Anc_total = 128` at n=3 (rule/lgb/gnn all matching) rather than the
old peak value of 1–3.
