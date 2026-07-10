# Stochastic Control Stability Audit

This audit consolidates repeated random-control and independent-seed evidence for the neural/search-control components.
It is intentionally conservative: stable but tiny margins remain limited, and runtime-positive rows are not promoted as speedups.

## Status counts

- pass: 6

| component | scope | repeats | pairs | score W/L/T | mean score change | stability check | cost boundary | interpretation |
|---|---|---|---:|---:|---:|---|---|---|
| Bit-flip learned prior | n<=6 traditional functions | 8 random-prior repeats | 177 | 17/8/152 | -0.15% | seed means beaten 8/8; <= best random 169/177 | time +48.05% vs random-prior mean | limited quality signal, not a speedup claim |
| Pareto learned prior | n<=6 traditional functions | 8 random-prior repeats | 177 | 5/5/167 | -0.03% | seed means beaten 6/8; <= best random 172/177 | time +38.18% vs random-prior mean | non-degrading but too small for a headline neural effect |
| Depth-frontier policy | n=24,28,32,40 | 8 random-depth repeats | 96 | 55/3/38 | -1.12% | seed means beaten 8/8; <= best random 90/96 | time +58.78% vs random-depth mean | quality-oriented budget allocation |
| Depth-frontier truth bridge | n=23 | 8 random-depth repeats | 6 | 5/0/1 | -0.89% | seed means beaten 8/8; <= best random 5/6 | time +71.00% vs random-depth mean | complete truth-table bridge for the random-depth control |
| Phase diverse shortlist | held-out n=6 phase/Rz proxy | 8 random shortlists | 38 | 17/0/21 | -0.012% | seed means beaten 8/8; <= best random 32/38 | phase proxy only; no approximate rotation synthesis | stable learned pruning of exact-scored phase candidates |
| Sparse depth-4 gate | n=24,28,32,40 independent seeds | 3 independent seeds | 144 | 0/0/144 | +0.00% | false skips 0; true runs 94/144 | time -13.43% vs sparse frontier | seed-stable gate that preserves sparse-frontier score |

## Interpretation

- The bit-flip prior is stable against random-prior repeats but remains a limited quality signal because the margins are small and runtime overhead is visible.
- The depth-frontier policy and sparse depth-4 gate provide stronger budget-allocation evidence: they preserve or improve score across repeated controls while making explicit time/lifetime tradeoffs.
- The phase shortlist row supports stable learned pruning in the logical phase/Rz proxy; it is not a high-precision rotation-synthesis result.
