# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 45/0/3 | -7.11% | +3296.43% |
| 20 | adaptive_all_depth | screen_depth1 | 39/0/9 | -2.51% | +430.78% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +37.36% |
| 20 | depth_policy | screen_single | 45/0/3 | -6.95% | +2408.14% |
| 20 | depth_policy | screen_depth2 | 0/4/44 | +0.18% | -10.38% |
| 20 | depth_policy | adaptive_all_depth | 0/4/44 | +0.18% | -31.68% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.01% |
| 22 | adaptive_all_depth | screen_single | 42/0/6 | -6.70% | +3061.82% |
| 22 | adaptive_all_depth | screen_depth1 | 37/0/11 | -2.33% | +413.30% |
| 22 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +47.66% |
| 22 | depth_policy | screen_single | 42/0/6 | -6.66% | +2350.56% |
| 22 | depth_policy | screen_depth2 | 0/1/47 | +0.05% | -4.50% |
| 22 | depth_policy | adaptive_all_depth | 0/1/47 | +0.05% | -30.36% |
| 22 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.68% |
| 24 | adaptive_all_depth | screen_single | 42/0/6 | -6.82% | +3217.52% |
| 24 | adaptive_all_depth | screen_depth1 | 35/0/13 | -2.49% | +431.86% |
| 24 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +46.85% |
| 24 | depth_policy | screen_single | 42/0/6 | -6.75% | +2452.00% |
| 24 | depth_policy | screen_depth2 | 0/1/47 | +0.08% | -4.93% |
| 24 | depth_policy | adaptive_all_depth | 0/1/47 | +0.08% | -30.03% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.03% |
| 28 | adaptive_all_depth | screen_single | 40/0/8 | -5.89% | +2794.04% |
| 28 | adaptive_all_depth | screen_depth1 | 33/0/15 | -2.17% | +394.19% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +59.72% |
| 28 | depth_policy | screen_single | 40/0/8 | -5.89% | +2149.83% |
| 28 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -1.89% |
| 28 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -32.07% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.06% |
| all | adaptive_all_depth | screen_single | 169/0/23 | -6.63% | +3092.45% |
| all | adaptive_all_depth | screen_depth1 | 144/0/48 | -2.37% | +417.53% |
| all | adaptive_all_depth | screen_depth2 | 0/0/192 | +0.00% | +47.90% |
| all | depth_policy | screen_single | 169/0/23 | -6.56% | +2340.13% |
| all | depth_policy | screen_depth2 | 0/6/186 | +0.08% | -5.43% |
| all | depth_policy | adaptive_all_depth | 0/6/186 | +0.08% | -31.04% |
| all | depth2_guard_direct | screen_depth2 | 0/0/192 | +0.00% | -0.15% |
