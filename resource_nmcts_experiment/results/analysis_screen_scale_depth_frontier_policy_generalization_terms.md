# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 960/960 method rows passed.
Emitted-circuit ANF verification: 960/960 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 24 | adaptive_all_depth | screen_single | 20/0/4 | -9.11% | +36320.51% |
| 24 | adaptive_all_depth | screen_depth1 | 17/0/7 | -5.23% | +5496.36% |
| 24 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.90% | +1154.08% |
| 24 | depth_policy | screen_single | 20/0/4 | -6.34% | +2208.56% |
| 24 | depth_policy | screen_depth2 | 0/1/23 | +0.11% | -6.37% |
| 24 | depth_policy | adaptive_all_depth | 0/17/7 | +3.17% | -89.91% |
| 24 | depth_frontier_policy | screen_single | 20/0/4 | -8.64% | +19178.54% |
| 24 | depth_frontier_policy | screen_depth2 | 12/0/12 | -2.38% | +525.77% |
| 24 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.54% | -23.02% |
| 24 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.54% | -58.35% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.01% |
| 24 | screen_depth3 | screen_depth2 | 16/0/8 | -1.76% | +198.36% |
| 24 | screen_depth4 | screen_depth2 | 16/0/8 | -2.90% | +703.94% |
| 24 | screen_depth4 | screen_depth3 | 14/0/10 | -1.18% | +130.80% |
| 28 | adaptive_all_depth | screen_single | 21/0/3 | -8.26% | +38741.16% |
| 28 | adaptive_all_depth | screen_depth1 | 16/0/8 | -4.10% | +5773.63% |
| 28 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.26% | +1181.30% |
| 28 | depth_policy | screen_single | 21/0/3 | -6.17% | +2384.10% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.95% |
| 28 | depth_policy | adaptive_all_depth | 0/16/8 | +2.35% | -89.37% |
| 28 | depth_frontier_policy | screen_single | 21/0/3 | -7.77% | +19874.36% |
| 28 | depth_frontier_policy | screen_depth2 | 11/0/13 | -1.72% | +520.34% |
| 28 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.56% | -24.63% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.56% | -59.21% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 28 | screen_depth3 | screen_depth2 | 16/0/8 | -1.23% | +204.86% |
| 28 | screen_depth4 | screen_depth2 | 16/0/8 | -2.26% | +726.55% |
| 28 | screen_depth4 | screen_depth3 | 14/0/10 | -1.05% | +134.08% |
| 32 | adaptive_all_depth | screen_single | 18/0/6 | -7.55% | +28827.91% |
| 32 | adaptive_all_depth | screen_depth1 | 14/0/10 | -4.21% | +4349.32% |
| 32 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.18% | +947.99% |
| 32 | depth_policy | screen_single | 18/0/6 | -5.56% | +1909.34% |
| 32 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.94% |
| 32 | depth_policy | adaptive_all_depth | 0/13/11 | +2.30% | -85.99% |
| 32 | depth_frontier_policy | screen_single | 18/0/6 | -7.07% | +14639.61% |
| 32 | depth_frontier_policy | screen_depth2 | 8/0/16 | -1.65% | +376.56% |
| 32 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.55% | -21.71% |
| 32 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.55% | -64.25% |
| 32 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 32 | screen_depth3 | screen_depth2 | 13/0/11 | -1.22% | +154.05% |
| 32 | screen_depth4 | screen_depth2 | 13/0/11 | -2.18% | +528.85% |
| 32 | screen_depth4 | screen_depth3 | 11/0/13 | -0.99% | +97.29% |
| 40 | adaptive_all_depth | screen_single | 19/0/5 | -8.68% | +31521.45% |
| 40 | adaptive_all_depth | screen_depth1 | 15/0/9 | -4.53% | +4730.41% |
| 40 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.42% | +1011.03% |
| 40 | depth_policy | screen_single | 19/0/5 | -6.48% | +2074.59% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.43% |
| 40 | depth_policy | adaptive_all_depth | 0/13/11 | +2.55% | -87.16% |
| 40 | depth_frontier_policy | screen_single | 19/0/5 | -8.01% | +15624.05% |
| 40 | depth_frontier_policy | screen_depth2 | 9/0/15 | -1.66% | +403.06% |
| 40 | depth_frontier_policy | screen_depth4 | 0/4/20 | +0.81% | -24.26% |
| 40 | depth_frontier_policy | adaptive_all_depth | 0/4/20 | +0.81% | -63.18% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 13/0/11 | -1.48% | +168.87% |
| 40 | screen_depth4 | screen_depth2 | 13/0/11 | -2.42% | +583.55% |
| 40 | screen_depth4 | screen_depth3 | 13/0/11 | -0.97% | +108.99% |
| all | adaptive_all_depth | screen_single | 78/0/18 | -8.40% | +33852.76% |
| all | adaptive_all_depth | screen_depth1 | 62/0/34 | -4.52% | +5087.43% |
| all | adaptive_all_depth | screen_depth2 | 58/0/38 | -2.44% | +1073.60% |
| all | depth_policy | screen_single | 78/0/18 | -6.14% | +2144.15% |
| all | depth_policy | screen_depth2 | 0/1/95 | +0.03% | -2.67% |
| all | depth_policy | adaptive_all_depth | 0/59/37 | +2.59% | -88.11% |
| all | depth_frontier_policy | screen_single | 78/0/18 | -7.87% | +17329.14% |
| all | depth_frontier_policy | screen_depth2 | 40/0/56 | -1.85% | +456.43% |
| all | depth_frontier_policy | screen_depth4 | 0/19/77 | +0.61% | -23.40% |
| all | depth_frontier_policy | adaptive_all_depth | 0/19/77 | +0.61% | -61.25% |
| all | depth2_guard_direct | screen_depth2 | 0/0/96 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 58/0/38 | -1.42% | +181.54% |
| all | screen_depth4 | screen_depth2 | 58/0/38 | -2.44% | +635.72% |
| all | screen_depth4 | screen_depth3 | 52/0/44 | -1.05% | +117.79% |
