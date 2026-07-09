# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 480/480 method rows passed.
Emitted-circuit ANF verification: 480/480 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 48 | adaptive_all_depth | screen_single | 14/0/2 | -7.88% | +27778.56% |
| 48 | adaptive_all_depth | screen_depth1 | 10/0/6 | -2.70% | +4259.35% |
| 48 | adaptive_all_depth | screen_depth2 | 6/0/10 | -1.07% | +913.92% |
| 48 | depth_policy | screen_single | 14/0/2 | -6.88% | +1849.01% |
| 48 | depth_policy | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 48 | depth_policy | adaptive_all_depth | 0/6/10 | +1.11% | -85.35% |
| 48 | depth_frontier_policy | screen_single | 14/0/2 | -7.81% | +15591.74% |
| 48 | depth_frontier_policy | screen_depth2 | 5/0/11 | -1.00% | +385.63% |
| 48 | depth_frontier_policy | screen_depth4 | 0/1/15 | +0.07% | -25.62% |
| 48 | depth_frontier_policy | adaptive_all_depth | 0/1/15 | +0.07% | -64.87% |
| 48 | depth2_guard_direct | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 48 | screen_depth3 | screen_depth2 | 6/0/10 | -0.65% | +154.71% |
| 48 | screen_depth4 | screen_depth2 | 6/0/10 | -1.07% | +502.84% |
| 48 | screen_depth4 | screen_depth3 | 6/0/10 | -0.43% | +85.95% |
| 56 | adaptive_all_depth | screen_single | 11/0/5 | -7.41% | +32148.26% |
| 56 | adaptive_all_depth | screen_depth1 | 11/0/5 | -4.34% | +4866.14% |
| 56 | adaptive_all_depth | screen_depth2 | 10/0/6 | -2.23% | +1031.65% |
| 56 | depth_policy | screen_single | 11/0/5 | -5.34% | +2108.58% |
| 56 | depth_policy | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 56 | depth_policy | adaptive_all_depth | 0/10/6 | +2.32% | -87.80% |
| 56 | depth_frontier_policy | screen_single | 11/0/5 | -6.41% | +12245.03% |
| 56 | depth_frontier_policy | screen_depth2 | 4/0/12 | -1.13% | +287.60% |
| 56 | depth_frontier_policy | screen_depth4 | 0/6/10 | +1.14% | -38.20% |
| 56 | depth_frontier_policy | adaptive_all_depth | 0/6/10 | +1.14% | -71.57% |
| 56 | depth2_guard_direct | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 56 | screen_depth3 | screen_depth2 | 10/0/6 | -1.53% | +177.55% |
| 56 | screen_depth4 | screen_depth2 | 10/0/6 | -2.23% | +592.15% |
| 56 | screen_depth4 | screen_depth3 | 6/0/10 | -0.72% | +109.01% |
| 64 | adaptive_all_depth | screen_single | 12/0/4 | -8.08% | +21908.95% |
| 64 | adaptive_all_depth | screen_depth1 | 10/0/6 | -3.96% | +3381.76% |
| 64 | adaptive_all_depth | screen_depth2 | 8/0/8 | -2.13% | +787.75% |
| 64 | depth_policy | screen_single | 12/0/4 | -6.12% | +1701.43% |
| 64 | depth_policy | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 64 | depth_policy | adaptive_all_depth | 0/8/8 | +2.25% | -85.06% |
| 64 | depth_frontier_policy | screen_single | 12/0/4 | -6.47% | +3924.62% |
| 64 | depth_frontier_policy | screen_depth2 | 1/0/15 | -0.38% | +60.77% |
| 64 | depth_frontier_policy | screen_depth4 | 0/7/9 | +1.85% | -44.92% |
| 64 | depth_frontier_policy | adaptive_all_depth | 0/7/9 | +1.85% | -81.31% |
| 64 | depth2_guard_direct | screen_depth2 | 0/0/16 | +0.00% | +0.00% |
| 64 | screen_depth3 | screen_depth2 | 8/0/8 | -1.31% | +135.42% |
| 64 | screen_depth4 | screen_depth2 | 8/0/8 | -2.13% | +381.05% |
| 64 | screen_depth4 | screen_depth3 | 7/0/9 | -0.85% | +69.36% |
| all | adaptive_all_depth | screen_single | 37/0/11 | -7.79% | +27278.59% |
| all | adaptive_all_depth | screen_depth1 | 31/0/17 | -3.67% | +4169.08% |
| all | adaptive_all_depth | screen_depth2 | 24/0/24 | -1.81% | +911.11% |
| all | depth_policy | screen_single | 37/0/11 | -6.12% | +1886.34% |
| all | depth_policy | screen_depth2 | 0/0/48 | +0.00% | +0.00% |
| all | depth_policy | adaptive_all_depth | 0/24/24 | +1.89% | -86.07% |
| all | depth_frontier_policy | screen_single | 37/0/11 | -6.90% | +10587.13% |
| all | depth_frontier_policy | screen_depth2 | 10/0/38 | -0.84% | +244.67% |
| all | depth_frontier_policy | screen_depth4 | 0/14/34 | +1.02% | -36.25% |
| all | depth_frontier_policy | adaptive_all_depth | 0/14/34 | +1.02% | -72.58% |
| all | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 24/0/24 | -1.16% | +155.89% |
| all | screen_depth4 | screen_depth2 | 24/0/24 | -1.81% | +492.01% |
| all | screen_depth4 | screen_depth3 | 19/0/29 | -0.67% | +88.11% |
