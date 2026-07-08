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
| 24 | adaptive_all_depth | screen_single | 20/0/4 | -9.11% | +36222.19% |
| 24 | adaptive_all_depth | screen_depth1 | 17/0/7 | -5.23% | +5525.54% |
| 24 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.90% | +1151.24% |
| 24 | depth_policy | screen_single | 20/0/4 | -6.34% | +2206.77% |
| 24 | depth_policy | screen_depth2 | 0/1/23 | +0.11% | -6.66% |
| 24 | depth_policy | adaptive_all_depth | 0/17/7 | +3.17% | -89.92% |
| 24 | depth_frontier_policy | screen_single | 20/0/4 | -9.11% | +23414.96% |
| 24 | depth_frontier_policy | screen_depth2 | 16/0/8 | -2.90% | +658.06% |
| 24 | depth_frontier_policy | screen_depth4 | 0/0/24 | +0.00% | -9.89% |
| 24 | depth_frontier_policy | adaptive_all_depth | 0/0/24 | +0.00% | -49.65% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.07% |
| 24 | screen_depth3 | screen_depth2 | 16/0/8 | -1.76% | +196.69% |
| 24 | screen_depth4 | screen_depth2 | 16/0/8 | -2.90% | +703.01% |
| 24 | screen_depth4 | screen_depth3 | 14/0/10 | -1.18% | +131.67% |
| 28 | adaptive_all_depth | screen_single | 21/0/3 | -8.26% | +38704.36% |
| 28 | adaptive_all_depth | screen_depth1 | 16/0/8 | -4.10% | +5817.90% |
| 28 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.26% | +1183.32% |
| 28 | depth_policy | screen_single | 21/0/3 | -6.17% | +2377.18% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.90% |
| 28 | depth_policy | adaptive_all_depth | 0/16/8 | +2.35% | -89.24% |
| 28 | depth_frontier_policy | screen_single | 21/0/3 | -8.06% | +23119.72% |
| 28 | depth_frontier_policy | screen_depth2 | 14/0/10 | -2.05% | +627.75% |
| 28 | depth_frontier_policy | screen_depth4 | 0/2/22 | +0.21% | -13.58% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/2/22 | +0.21% | -52.55% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 28 | screen_depth3 | screen_depth2 | 16/0/8 | -1.23% | +204.58% |
| 28 | screen_depth4 | screen_depth2 | 16/0/8 | -2.26% | +730.03% |
| 28 | screen_depth4 | screen_depth3 | 14/0/10 | -1.05% | +134.68% |
| 32 | adaptive_all_depth | screen_single | 18/0/6 | -7.55% | +29234.52% |
| 32 | adaptive_all_depth | screen_depth1 | 14/0/10 | -4.21% | +4351.54% |
| 32 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.18% | +950.13% |
| 32 | depth_policy | screen_single | 18/0/6 | -5.56% | +1932.94% |
| 32 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.96% |
| 32 | depth_policy | adaptive_all_depth | 0/13/11 | +2.30% | -86.06% |
| 32 | depth_frontier_policy | screen_single | 18/0/6 | -7.52% | +18397.76% |
| 32 | depth_frontier_policy | screen_depth2 | 13/0/11 | -2.14% | +491.87% |
| 32 | depth_frontier_policy | screen_depth4 | 0/1/23 | +0.04% | -6.21% |
| 32 | depth_frontier_policy | adaptive_all_depth | 0/1/23 | +0.04% | -55.41% |
| 32 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 32 | screen_depth3 | screen_depth2 | 13/0/11 | -1.22% | +154.74% |
| 32 | screen_depth4 | screen_depth2 | 13/0/11 | -2.18% | +530.64% |
| 32 | screen_depth4 | screen_depth3 | 11/0/13 | -0.99% | +97.36% |
| 40 | adaptive_all_depth | screen_single | 19/0/5 | -8.68% | +30578.95% |
| 40 | adaptive_all_depth | screen_depth1 | 15/0/9 | -4.53% | +4602.78% |
| 40 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.42% | +989.57% |
| 40 | depth_policy | screen_single | 19/0/5 | -6.48% | +2061.53% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.42% |
| 40 | depth_policy | adaptive_all_depth | 0/13/11 | +2.55% | -87.06% |
| 40 | depth_frontier_policy | screen_single | 19/0/5 | -8.54% | +17728.24% |
| 40 | depth_frontier_policy | screen_depth2 | 13/0/11 | -2.26% | +477.53% |
| 40 | depth_frontier_policy | screen_depth4 | 0/3/21 | +0.16% | -12.46% |
| 40 | depth_frontier_policy | adaptive_all_depth | 0/3/21 | +0.16% | -56.39% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 13/0/11 | -1.48% | +166.78% |
| 40 | screen_depth4 | screen_depth2 | 13/0/11 | -2.42% | +564.55% |
| 40 | screen_depth4 | screen_depth3 | 13/0/11 | -0.97% | +105.75% |
| all | adaptive_all_depth | screen_single | 78/0/18 | -8.40% | +33685.01% |
| all | adaptive_all_depth | screen_depth1 | 62/0/34 | -4.52% | +5074.44% |
| all | adaptive_all_depth | screen_depth2 | 58/0/38 | -2.44% | +1068.57% |
| all | depth_policy | screen_single | 78/0/18 | -6.14% | +2144.61% |
| all | depth_policy | screen_depth2 | 0/1/95 | +0.03% | -2.73% |
| all | depth_policy | adaptive_all_depth | 0/59/37 | +2.59% | -88.07% |
| all | depth_frontier_policy | screen_single | 78/0/18 | -8.31% | +20665.17% |
| all | depth_frontier_policy | screen_depth2 | 56/0/40 | -2.34% | +563.80% |
| all | depth_frontier_policy | screen_depth4 | 0/6/90 | +0.10% | -10.53% |
| all | depth_frontier_policy | adaptive_all_depth | 0/6/90 | +0.10% | -53.50% |
| all | depth2_guard_direct | screen_depth2 | 0/0/96 | +0.00% | -0.02% |
| all | screen_depth3 | screen_depth2 | 58/0/38 | -1.42% | +180.70% |
| all | screen_depth4 | screen_depth2 | 58/0/38 | -2.44% | +632.06% |
| all | screen_depth4 | screen_depth3 | 52/0/44 | -1.05% | +117.36% |
