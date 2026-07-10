# Learned Phase Affine Policy

This experiment trains a neural scorer over Affine-FPRM phase-search candidates.
Training uses n<=5 functions; the paper-facing test split is held-out n=6.
The policy ranks all affine/polarity candidates from cheap structural features and exact-scores only a top-k shortlist.

- transform budget: 128
- target metric: score_synth_tperrz30
- label mode: rank
- diverse prepool multiplier: 8
- diverse weight: 0.35
- random repeats per top-k: 8
- train functions: 114
- valid functions: 25
- held-out n=6 test functions: 38
- train MSE: 0.0982
- valid MSE: 0.1149
- elapsed seconds: 61.99

## Held-out n=6 comparison

| method | exact forms/function | mean target | vs budget-32 W/L/T | vs budget-32 mean relative | vs wide-128 W/L/T | vs wide-128 mean relative |
|---|---:|---:|---:|---:|---:|---:|
| phase_affine_prefix16_tperrz30 | 1024 | 1497.20 | 0/6/32 | +0.13% | 0/18/20 | +3.74% |
| phase_parity_affine_policy_tperrz30_top64 | 64 | 1482.48 | 11/6/21 | -1.40% | 0/13/25 | +1.77% |
| phase_parity_affine_policy_tperrz30_top128 | 128 | 1482.29 | 14/4/20 | -1.90% | 0/13/25 | +0.94% |
| phase_parity_affine_policy_tperrz30_top256 | 256 | 1482.14 | 15/3/20 | -2.39% | 0/12/26 | +0.14% |
| phase_parity_affine_policy_tperrz30_top512 | 512 | 1482.03 | 17/0/21 | -2.40% | 0/9/29 | +0.13% |
| phase_parity_affine_policy_diverse_tperrz30_top64 | 64 | 1482.40 | 12/6/20 | -1.90% | 0/13/25 | +0.95% |
| phase_parity_affine_policy_diverse_tperrz30_top128 | 128 | 1482.15 | 15/3/20 | -2.39% | 0/12/26 | +0.14% |
| phase_parity_affine_policy_diverse_tperrz30_top256 | 256 | 1482.06 | 16/2/20 | -2.47% | 0/9/29 | +0.01% |
| phase_parity_affine_policy_diverse_tperrz30_top512 | 512 | 1481.95 | 17/0/21 | -2.48% | 0/7/31 | +0.00% |
| phase_affine_random_top64 | 64 | 1482.63 | 10/8/20 | -2.12% | 0/17/21 | +0.38% |
| phase_affine_random_top128 | 128 | 1482.45 | 15/3/20 | -2.40% | 0/13/25 | +0.11% |
| phase_affine_random_top256 | 256 | 1482.36 | 13/3/22 | -2.45% | 0/15/23 | +0.04% |
| phase_affine_random_top512 | 512 | 1482.18 | 16/2/20 | -2.44% | 0/13/25 | +0.06% |
| phase_affine_budget32_tperrz30 | 2048 | 1496.96 | - | - | - | - |
| phase_affine_wide128_tperrz30 | 8192 | 1481.91 | - | - | - | - |

## Same-budget random-repeat control

| target | top-k | target mean | random mean +/- sd | target better than random seeds | relative vs random mean |
|---|---:|---:|---:|---:|---:|
| phase_parity_affine_policy_tperrz30_top64 | 64 | 1482.48 | 1482.80 +/- 0.12 | 8/8 | -0.02% |
| phase_parity_affine_policy_diverse_tperrz30_top64 | 64 | 1482.40 | 1482.80 +/- 0.12 | 8/8 | -0.03% |
| phase_parity_affine_policy_tperrz30_top128 | 128 | 1482.29 | 1482.52 +/- 0.12 | 8/8 | -0.02% |
| phase_parity_affine_policy_diverse_tperrz30_top128 | 128 | 1482.15 | 1482.52 +/- 0.12 | 8/8 | -0.02% |
| phase_parity_affine_policy_tperrz30_top256 | 256 | 1482.14 | 1482.32 +/- 0.06 | 8/8 | -0.01% |
| phase_parity_affine_policy_diverse_tperrz30_top256 | 256 | 1482.06 | 1482.32 +/- 0.06 | 8/8 | -0.02% |
| phase_parity_affine_policy_tperrz30_top512 | 512 | 1482.03 | 1482.13 +/- 0.08 | 8/8 | -0.01% |
| phase_parity_affine_policy_diverse_tperrz30_top512 | 512 | 1481.95 | 1482.13 +/- 0.08 | 8/8 | -0.01% |

## Interpretation

- A positive row against budget-32 means the learned scorer found useful candidates outside the deterministic budget-32 prefix while exact-scoring fewer affine forms.
- Same-budget random shortlists are intentionally repeated because this candidate space is dense; policy-vs-random claims should use the repeat-control table rather than a single random seed.
- The diverse policy reranker selects from high-scoring predicted candidates while covering distinct transforms and polarities.  It is still a cheap-feature shortlist, not an exact-score oracle.
- A small gap against wide-128 is expected because wide-128 is the exhaustive oracle over the same transform budget.
- This remains a logic-layer phase-polynomial search result; it does not synthesize approximate rotations or include hardware mapping.
