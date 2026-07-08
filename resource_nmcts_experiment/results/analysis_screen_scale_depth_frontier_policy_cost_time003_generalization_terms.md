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
| 24 | adaptive_all_depth | screen_single | 20/0/4 | -9.11% | +36338.41% |
| 24 | adaptive_all_depth | screen_depth1 | 17/0/7 | -5.23% | +5547.44% |
| 24 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.90% | +1155.53% |
| 24 | depth_policy | screen_single | 20/0/4 | -6.34% | +2202.39% |
| 24 | depth_policy | screen_depth2 | 0/1/23 | +0.11% | -6.69% |
| 24 | depth_policy | adaptive_all_depth | 0/17/7 | +3.17% | -89.94% |
| 24 | depth_frontier_policy | screen_single | 20/0/4 | -8.06% | +8320.96% |
| 24 | depth_frontier_policy | screen_depth2 | 16/0/8 | -1.76% | +189.10% |
| 24 | depth_frontier_policy | screen_depth4 | 0/14/10 | +1.20% | -49.13% |
| 24 | depth_frontier_policy | adaptive_all_depth | 0/14/10 | +1.20% | -77.05% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.03% |
| 24 | screen_depth3 | screen_depth2 | 16/0/8 | -1.76% | +198.61% |
| 24 | screen_depth4 | screen_depth2 | 16/0/8 | -2.90% | +705.88% |
| 24 | screen_depth4 | screen_depth3 | 14/0/10 | -1.18% | +130.92% |
| 28 | adaptive_all_depth | screen_single | 21/0/3 | -8.26% | +38504.52% |
| 28 | adaptive_all_depth | screen_depth1 | 16/0/8 | -4.10% | +5811.55% |
| 28 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.26% | +1187.81% |
| 28 | depth_policy | screen_single | 21/0/3 | -6.17% | +2356.71% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.86% |
| 28 | depth_policy | adaptive_all_depth | 0/16/8 | +2.35% | -89.37% |
| 28 | depth_frontier_policy | screen_single | 21/0/3 | -7.21% | +8110.57% |
| 28 | depth_frontier_policy | screen_depth2 | 14/0/10 | -1.12% | +175.26% |
| 28 | depth_frontier_policy | screen_depth4 | 0/15/9 | +1.18% | -50.74% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/15/9 | +1.18% | -78.21% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 28 | screen_depth3 | screen_depth2 | 16/0/8 | -1.23% | +205.75% |
| 28 | screen_depth4 | screen_depth2 | 16/0/8 | -2.26% | +732.27% |
| 28 | screen_depth4 | screen_depth3 | 14/0/10 | -1.05% | +135.15% |
| 32 | adaptive_all_depth | screen_single | 18/0/6 | -7.55% | +29164.47% |
| 32 | adaptive_all_depth | screen_depth1 | 14/0/10 | -4.21% | +4299.85% |
| 32 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.18% | +947.54% |
| 32 | depth_policy | screen_single | 18/0/6 | -5.56% | +1943.10% |
| 32 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.01% |
| 32 | depth_policy | adaptive_all_depth | 0/13/11 | +2.30% | -86.10% |
| 32 | depth_frontier_policy | screen_single | 18/0/6 | -6.67% | +6895.84% |
| 32 | depth_frontier_policy | screen_depth2 | 13/0/11 | -1.22% | +150.07% |
| 32 | depth_frontier_policy | screen_depth4 | 0/11/13 | +1.02% | -36.75% |
| 32 | depth_frontier_policy | adaptive_all_depth | 0/11/13 | +1.02% | -75.75% |
| 32 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 32 | screen_depth3 | screen_depth2 | 13/0/11 | -1.22% | +155.23% |
| 32 | screen_depth4 | screen_depth2 | 13/0/11 | -2.18% | +527.33% |
| 32 | screen_depth4 | screen_depth3 | 11/0/13 | -0.99% | +96.32% |
| 40 | adaptive_all_depth | screen_single | 19/0/5 | -8.68% | +30984.41% |
| 40 | adaptive_all_depth | screen_depth1 | 15/0/9 | -4.53% | +4602.05% |
| 40 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.42% | +992.40% |
| 40 | depth_policy | screen_single | 19/0/5 | -6.48% | +2080.57% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.41% |
| 40 | depth_policy | adaptive_all_depth | 0/13/11 | +2.55% | -87.06% |
| 40 | depth_frontier_policy | screen_single | 19/0/5 | -7.82% | +7424.60% |
| 40 | depth_frontier_policy | screen_depth2 | 13/0/11 | -1.48% | +165.69% |
| 40 | depth_frontier_policy | screen_depth4 | 0/13/11 | +0.99% | -39.59% |
| 40 | depth_frontier_policy | adaptive_all_depth | 0/13/11 | +0.99% | -75.15% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 13/0/11 | -1.48% | +167.72% |
| 40 | screen_depth4 | screen_depth2 | 13/0/11 | -2.42% | +566.37% |
| 40 | screen_depth4 | screen_depth3 | 13/0/11 | -0.97% | +105.28% |
| all | adaptive_all_depth | screen_single | 78/0/18 | -8.40% | +33747.95% |
| all | adaptive_all_depth | screen_depth1 | 62/0/34 | -4.52% | +5065.22% |
| all | adaptive_all_depth | screen_depth2 | 58/0/38 | -2.44% | +1070.82% |
| all | depth_policy | screen_single | 78/0/18 | -6.14% | +2145.69% |
| all | depth_policy | screen_depth2 | 0/1/95 | +0.03% | -2.74% |
| all | depth_policy | adaptive_all_depth | 0/59/37 | +2.59% | -88.12% |
| all | depth_frontier_policy | screen_single | 78/0/18 | -7.44% | +7687.99% |
| all | depth_frontier_policy | screen_depth2 | 56/0/40 | -1.39% | +170.03% |
| all | depth_frontier_policy | screen_depth4 | 0/53/43 | +1.10% | -44.05% |
| all | depth_frontier_policy | adaptive_all_depth | 0/53/43 | +1.10% | -76.54% |
| all | depth2_guard_direct | screen_depth2 | 0/0/96 | +0.00% | -0.01% |
| all | screen_depth3 | screen_depth2 | 58/0/38 | -1.42% | +181.83% |
| all | screen_depth4 | screen_depth2 | 58/0/38 | -2.44% | +632.96% |
| all | screen_depth4 | screen_depth3 | 52/0/44 | -1.05% | +116.92% |
