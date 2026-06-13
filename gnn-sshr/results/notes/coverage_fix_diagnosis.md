# Coverage-fix diagnosis (n=3, keep_ratio=0.20)

## TL;DR

`prune_candidates(...).ensure_coverage` was a *set-union* coverage check.
This is **insufficient** for the WP-SCP ILP, which requires the onset
characteristic vector to lie in the **GF(2)** column-span of the kept
candidates. Replacing the set-union repair with a *singleton-injection*
repair drops the ILP-infeasibility rate from `240/64/89 (rule/lgb/gnn) → 0/0/0`
at `n=3, keep_ratio=0.20`.

## Example: `tt = 0xB6` (n=3, onset = {1, 2, 4, 5, 7})

Top-20% of 43 candidates, scored by the hand-written rule
`dim − 0.1·off_overlap`, surfaces only the dim-3 cube `{0..7}` and the
six dim-2 even-weight pairs:

| idx | dim | verts |
|----|----|-------|
| 0 | 3 | {0..7} |
| 1 | 2 | {0,1,2,3} |
| 2 | 2 | {0,1,4,5} |
| 3 | 2 | {0,1,6,7} |
| ... | 2 | ... |
| 12 | 2 | {4,5,6,7} |

Set-union cover ⊇ onset → "feasible" by the old check. **But the GF(2)
column-span of those 13 vectors is 4-dimensional**, whereas the onset
characteristic vector has Hamming weight 5 and odd parity in coordinate 7,
which is *not* representable as any XOR of the kept candidates' 0/1 incidence
vectors restricted to all 8 minterms while keeping every off-set coordinate
even. Gurobi correctly returns `INFEASIBLE`. The old "any-coverage" repair
adds nothing because every onset minterm is already in the union.

## Root cause

`ensure_coverage` was solving the wrong problem. `WP-SCP` is a parity-cover
problem over **GF(2)**, not a set-cover problem over `2^X`. A kept set whose
union covers the onset can still be parity-infeasible.

## Fix

In `src/search/pruned_search.py`, the `ensure_coverage` branch now forces
**every onset singleton** `{v}` into the kept set. `_enumerate_with_singletons`
already includes one singleton per onset minterm. Singletons are unit
vectors in the GF(2) coverage matrix, so the onset characteristic vector
is *always* in the span of the kept set, and the trivially-feasible
"select exactly the onset singletons" solution is always available to
Gurobi — guaranteeing feasibility while letting the ILP still pick cheaper
parallelotopes when the ranker has surfaced any.

Fallback (no singleton present) keeps the previous lowest-cost-coverer
behaviour.

## Before / after at n=3 keep_ratio=0.20

| Ranker | n_evaluated (before / after) | n_skipped (before / after) | T (before/after) | CNOT (before/after) |
|---|---|---|---|---|
| rule | 15 / 255 | 240 / 0 | 0 / 9472 | 24 / 8448 |
| lgb  | 191 / 255 | 64 / 0 | 3173 / 5149 | 2899 / 4629 |
| gnn  | 166 / 255 | 89 / 0 | 3228 / 7372 | 2993 / 6694 |

Acceptance: `gnn n_skipped ≤ 10` and `lgb n_skipped ≤ 10` — **both met
(0 / 0)**. Rule is fixed for free even though it was not required.

The CNOT-count regression is expected and acceptable: singleton candidates
have CNOT cost `mct_cost(n)["CNOT"] = 14` for `n=3`, and the ILP picks them
whenever the ranker omits a cheaper cover from the top-20%. With singletons
guaranteed present the ILP is always feasible; surfacing better covers is a
ranker-quality issue, not a coverage-repair issue.

## Files touched

- `src/search/pruned_search.py` — replaced the set-union repair in
  `prune_candidates` with onset-singleton injection (plus updated docstring).
- `results/tables/p0_baselines_n3_v2.md` — refreshed comparison output.
