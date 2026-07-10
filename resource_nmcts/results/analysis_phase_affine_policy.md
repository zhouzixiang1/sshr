# Learned Phase Affine Policy

This experiment trains a neural scorer over Affine-FPRM phase-search candidates.
Training uses n<=5 functions; the paper-facing test split is held-out n=6.
The policy ranks all affine/polarity candidates from cheap structural features and exact-scores only a top-k shortlist.

- transform budget: 128
- target metric: score_synth_tperrz30
- train functions: 114
- valid functions: 25
- held-out n=6 test functions: 38
- train MSE: 0.3288
- valid MSE: 0.3444
- elapsed seconds: 41.11

## Held-out n=6 comparison

| method | exact forms/function | mean target | vs budget-32 W/L/T | vs budget-32 mean relative | vs wide-128 W/L/T | vs wide-128 mean relative |
|---|---:|---:|---:|---:|---:|---:|
| phase_affine_prefix16_tperrz30 | 1024 | 1497.20 | 0/6/32 | +0.13% | 0/18/20 | +3.74% |
| phase_parity_affine_policy_tperrz30_top64 | 64 | 1483.07 | 13/4/21 | -2.31% | 0/15/23 | +0.22% |
| phase_parity_affine_policy_tperrz30_top128 | 128 | 1482.11 | 15/1/22 | -2.39% | 0/11/27 | +0.14% |
| phase_parity_affine_policy_tperrz30_top256 | 256 | 1482.06 | 15/0/23 | -2.41% | 0/9/29 | +0.10% |
| phase_parity_affine_policy_tperrz30_top512 | 512 | 1482.01 | 17/0/21 | -2.47% | 0/6/32 | +0.01% |
| phase_affine_random_top64 | 64 | 1482.71 | 12/6/20 | -2.34% | 0/16/22 | +0.19% |
| phase_affine_random_top128 | 128 | 1482.20 | 14/3/21 | -2.43% | 0/14/24 | +0.06% |
| phase_affine_random_top256 | 256 | 1482.25 | 15/3/20 | -2.43% | 0/14/24 | +0.06% |
| phase_affine_random_top512 | 512 | 1482.08 | 17/0/21 | -2.47% | 0/11/27 | +0.01% |
| phase_affine_budget32_tperrz30 | 2048 | 1496.96 | - | - | - | - |
| phase_affine_wide128_tperrz30 | 8192 | 1481.91 | - | - | - | - |

## Interpretation

- A positive row against budget-32 means the learned scorer found useful candidates outside the deterministic budget-32 prefix while exact-scoring fewer affine forms.
- Same-budget random shortlists are intentionally included because this candidate space is dense; the current neural policy is best read as a pruned-search feasibility result, not as a decisive learned-vs-random win.
- A small gap against wide-128 is expected because wide-128 is the exhaustive oracle over the same transform budget.
- This remains a logic-layer phase-polynomial search result; it does not synthesize approximate rotations or include hardware mapping.
