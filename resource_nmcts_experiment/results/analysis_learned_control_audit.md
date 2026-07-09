# Learned-Control Evidence Audit

This table separates promoted learned/search-control components from limited diagnostics.
It is intentionally conservative: small or runtime-negative AI components are labeled as limited rather than promoted.

## Status counts

- pass: 10

## Claim-class counts

- bounded: 4
- limited: 2
- promoted: 4

| component | claim class | scope | quality evidence | cost/evaluation evidence | paper role | status |
|---|---|---|---|---|---|---|
| Depth-frontier policy | promoted | held-out n=28,40; 48 rows | vs oracle frontier 0/3/45, +0.04% | -51.30% time vs all-depth frontier | promoted quality/time selector | pass |
| Frontier random-depth control | bounded | held-out/scale/n=23; 8 random-depth repeats | scale 55/3/38, -1.12%; n23 5/0/1, -0.89%; seed means beaten 8/8 | +58.78% scale planning time vs random-depth mean | quality-oriented budget allocation; not runtime claim | pass |
| Stage-gated frontier | promoted | independent n=24,28,32,40; 96 rows | vs all-depth 0/4/92, +0.04% | -25.43% staged planning time | promoted validation-calibrated guard | pass |
| Sparse depth-4 gate | promoted | multi-seed n=24,28,32,40; 144 pairs | vs sparse frontier 0/0/144, +0.00%; false skips 0 | -13.43% time vs sparse frontier | promoted budget gate after depth-2 | pass |
| Rank-diverse phase shortlist | promoted | held-out n=6 phase search; 38 rows | vs budget-32 17/0/21, -2.48%; vs wide-128 0/7/31, +0.00% | 512/8192 exact forms; 93.75% fewer vs wide-128 | promoted phase-search pruning | pass |
| Bit-flip learned prior | limited | 177 n<=6 functions; 8 random-prior repeats | vs random mean 17/8/152, -0.15%; seed means beaten 8/8 | +48.05% runtime vs random-prior mean | limited quality signal, not runtime claim | pass |
| Bit-flip low-budget prior | bounded | top-8/top-12 budgets; 6 score rows; 1062 pairs | learned vs no-prior 218/0/844, -1.04% | +24.22% runtime vs no-prior | bounded low-budget quality evidence, not speed claim | pass |
| Bit-flip ANF-term prior gate | bounded | 1593 paired rows; static 6--23 ANF-term deployment gate | retains 328/328 always-learned score wins; 0 score losses; -1.07% | +29.45% runtime vs no-prior; +14.61% overhead cut vs always-learned | bounded deployment rule from input ANF terms; not held-out policy claim | pass |
| Boolean neural guard | limited | n=16 high-dimensional guard; 24 rows | vs deterministic 4/0/20, -0.12% | +94.49% runtime | limited quality guard, not runtime claim | pass |
| Root-action neural candidate extension | bounded | n=14 and n=16 root-action slices; 33 pairs | union top-4+neural12 vs beam4 8/0/25, -0.08%; oracle24 headroom -0.10% | root-only one-step audit; runtime not claimed | bounded candidate-extension evidence | pass |
