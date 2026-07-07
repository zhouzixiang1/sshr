# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked by symbolic ANF plan expansion: direct
nodes return their monomial set, monomial factors multiply quotient
terms by the factor, and linear Boolean-ring factors expand over GF(2).

ANF plan verification: 1344/1344 method rows passed.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 45/0/3 | -7.11% | +3298.97% |
| 20 | adaptive_all_depth | screen_depth1 | 39/0/9 | -2.51% | +433.52% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +37.12% |
| 20 | depth_policy | screen_single | 45/0/3 | -6.95% | +2414.56% |
| 20 | depth_policy | screen_depth2 | 0/4/44 | +0.18% | -10.44% |
| 20 | depth_policy | adaptive_all_depth | 0/4/44 | +0.18% | -31.61% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.09% |
| 22 | adaptive_all_depth | screen_single | 42/0/6 | -6.70% | +3057.13% |
| 22 | adaptive_all_depth | screen_depth1 | 37/0/11 | -2.33% | +415.28% |
| 22 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +47.34% |
| 22 | depth_policy | screen_single | 42/0/6 | -6.66% | +2348.41% |
| 22 | depth_policy | screen_depth2 | 0/1/47 | +0.05% | -4.63% |
| 22 | depth_policy | adaptive_all_depth | 0/1/47 | +0.05% | -30.32% |
| 22 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.70% |
| 24 | adaptive_all_depth | screen_single | 42/0/6 | -6.82% | +3217.09% |
| 24 | adaptive_all_depth | screen_depth1 | 35/0/13 | -2.49% | +431.93% |
| 24 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +46.87% |
| 24 | depth_policy | screen_single | 42/0/6 | -6.75% | +2451.45% |
| 24 | depth_policy | screen_depth2 | 0/1/47 | +0.08% | -4.98% |
| 24 | depth_policy | adaptive_all_depth | 0/1/47 | +0.08% | -30.04% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.05% |
| 28 | adaptive_all_depth | screen_single | 40/0/8 | -5.89% | +2770.99% |
| 28 | adaptive_all_depth | screen_depth1 | 33/0/15 | -2.17% | +392.70% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +59.81% |
| 28 | depth_policy | screen_single | 40/0/8 | -5.89% | +2129.21% |
| 28 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -1.98% |
| 28 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -32.17% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.08% |
| all | adaptive_all_depth | screen_single | 169/0/23 | -6.63% | +3086.05% |
| all | adaptive_all_depth | screen_depth1 | 144/0/48 | -2.37% | +418.36% |
| all | adaptive_all_depth | screen_depth2 | 0/0/192 | +0.00% | +47.78% |
| all | depth_policy | screen_single | 169/0/23 | -6.56% | +2335.91% |
| all | depth_policy | screen_depth2 | 0/6/186 | +0.08% | -5.51% |
| all | depth_policy | adaptive_all_depth | 0/6/186 | +0.08% | -31.04% |
| all | depth2_guard_direct | screen_depth2 | 0/0/192 | +0.00% | -0.17% |
