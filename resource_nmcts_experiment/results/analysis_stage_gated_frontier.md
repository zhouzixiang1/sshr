# Stage-Gated Depth Frontier

A progressive controller first evaluates depth-2 and depth-3 Boolean-ring screens, then evaluates depth-4 only when depth-3 improves over depth-2 by at least 1.250%.  The threshold is selected on the large frontier policy validation split and then applied unchanged to the independent scale and truth-bridge rows.

## Threshold selection

- validation score-gap budget: 0.050%
- selected threshold: 1.250%

| threshold | valid score gap | valid time | run depth-4 |
|---:|---:|---:|---:|
| -1.000% | +0.00% | +0.00% | 72 |
| 0.000% | +0.00% | +0.00% | 72 |
| 0.250% | +0.00% | -9.13% | 55 |
| 0.500% | +0.00% | -9.13% | 55 |
| 0.750% | +0.00% | -9.13% | 55 |
| 1.000% | +0.02% | -10.12% | 54 |
| 1.250% | +0.03% | -11.71% | 52 |
| 1.500% | +0.07% | -13.68% | 50 |
| 2.000% | +0.16% | -18.42% | 45 |
| 3.000% | +0.81% | -38.86% | 24 |
| 5.000% | +1.67% | -61.99% | 0 |

## Independent comparisons

| source | baseline | pairs | score W/L/T | mean score | mean time | T-depth | aux area | run depth-4 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| scale_generalization | adaptive_all_depth | 96 | 0/4/92 | +0.04% | -25.43% | +0.04% | -0.69% | 52 |
| scale_generalization | screen_depth2 | 96 | 58/0/38 | -2.40% | +893.25% | -2.33% | +30.03% | 52 |
| scale_generalization | depth_frontier_policy | 96 | 5/3/88 | -0.06% | +101.10% | -0.06% | +0.96% | 52 |
| truth_bridge_n23 | adaptive_all_depth | 6 | 0/0/6 | +0.00% | -11.51% | +0.00% | +0.00% | 5 |
| truth_bridge_n23 | screen_depth2 | 6 | 5/0/1 | -2.47% | +1322.09% | -2.20% | +44.19% | 5 |
| truth_bridge_n23 | depth_frontier_policy | 6 | 1/0/5 | -0.12% | +94.20% | -0.07% | +3.23% | 5 |

## Verification

- scale_generalization: selected rows verified 96/96
- truth_bridge_n23: selected rows verified 6/6
