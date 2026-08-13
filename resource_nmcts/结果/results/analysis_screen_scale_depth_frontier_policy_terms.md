# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 720/720 method rows passed.
Emitted-circuit ANF verification: 720/720 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 23/0/1 | -10.16% | +40408.30% |
| 20 | adaptive_all_depth | screen_depth1 | 21/0/3 | -5.89% | +6001.31% |
| 20 | adaptive_all_depth | screen_depth2 | 19/0/5 | -3.57% | +1236.93% |
| 20 | depth_policy | screen_single | 23/0/1 | -6.67% | +2396.61% |
| 20 | depth_policy | screen_depth2 | 0/3/21 | +0.25% | -11.05% |
| 20 | depth_policy | adaptive_all_depth | 0/21/3 | +4.04% | -91.93% |
| 20 | depth_frontier_policy | screen_single | 23/0/1 | -9.66% | +23446.95% |
| 20 | depth_frontier_policy | screen_depth2 | 16/0/8 | -3.01% | +645.51% |
| 20 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.58% | -19.07% |
| 20 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.58% | -51.25% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.15% |
| 20 | screen_depth3 | screen_depth2 | 19/0/5 | -2.18% | +222.21% |
| 20 | screen_depth4 | screen_depth2 | 19/0/5 | -3.57% | +778.93% |
| 20 | screen_depth4 | screen_depth3 | 17/0/7 | -1.44% | +147.22% |
| 28 | adaptive_all_depth | screen_single | 20/0/4 | -7.96% | +33431.34% |
| 28 | adaptive_all_depth | screen_depth1 | 17/0/7 | -4.69% | +5035.51% |
| 28 | adaptive_all_depth | screen_depth2 | 15/0/9 | -2.83% | +1060.76% |
| 28 | depth_policy | screen_single | 20/0/4 | -5.36% | +2132.37% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.09% |
| 28 | depth_policy | adaptive_all_depth | 0/15/9 | +3.00% | -87.01% |
| 28 | depth_frontier_policy | screen_single | 20/0/4 | -7.60% | +20716.96% |
| 28 | depth_frontier_policy | screen_depth2 | 12/0/12 | -2.44% | +559.17% |
| 28 | depth_frontier_policy | screen_depth4 | 0/3/21 | +0.42% | -12.36% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/3/21 | +0.42% | -54.81% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.06% |
| 28 | screen_depth3 | screen_depth2 | 15/0/9 | -1.65% | +175.04% |
| 28 | screen_depth4 | screen_depth2 | 15/0/9 | -2.83% | +626.66% |
| 28 | screen_depth4 | screen_depth3 | 13/0/11 | -1.22% | +115.89% |
| 40 | adaptive_all_depth | screen_single | 18/0/6 | -8.91% | +33930.04% |
| 40 | adaptive_all_depth | screen_depth1 | 16/0/8 | -5.25% | +5100.25% |
| 40 | adaptive_all_depth | screen_depth2 | 15/0/9 | -2.91% | +1086.68% |
| 40 | depth_policy | screen_single | 18/0/6 | -6.26% | +2157.06% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +0.04% |
| 40 | depth_policy | adaptive_all_depth | 0/15/9 | +3.07% | -88.15% |
| 40 | depth_frontier_policy | screen_single | 18/0/6 | -7.31% | +12408.51% |
| 40 | depth_frontier_policy | screen_depth2 | 7/0/17 | -1.12% | +304.93% |
| 40 | depth_frontier_policy | screen_depth4 | 0/8/16 | +1.90% | -35.06% |
| 40 | depth_frontier_policy | adaptive_all_depth | 0/8/16 | +1.90% | -70.01% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 15/0/9 | -1.96% | +182.85% |
| 40 | screen_depth4 | screen_depth2 | 15/0/9 | -2.91% | +639.06% |
| 40 | screen_depth4 | screen_depth3 | 14/0/10 | -0.97% | +119.35% |
| all | adaptive_all_depth | screen_single | 61/0/11 | -9.01% | +35923.23% |
| all | adaptive_all_depth | screen_depth1 | 54/0/18 | -5.28% | +5379.02% |
| all | adaptive_all_depth | screen_depth2 | 49/0/23 | -3.10% | +1128.12% |
| all | depth_policy | screen_single | 61/0/11 | -6.10% | +2228.68% |
| all | depth_policy | screen_depth2 | 0/3/69 | +0.08% | -3.70% |
| all | depth_policy | adaptive_all_depth | 0/51/21 | +3.37% | -89.03% |
| all | depth_frontier_policy | screen_single | 61/0/11 | -8.19% | +18857.47% |
| all | depth_frontier_policy | screen_depth2 | 35/0/37 | -2.19% | +503.20% |
| all | depth_frontier_policy | screen_depth4 | 0/16/56 | +0.97% | -22.17% |
| all | depth_frontier_policy | adaptive_all_depth | 0/16/56 | +0.97% | -58.69% |
| all | depth2_guard_direct | screen_depth2 | 0/0/72 | +0.00% | -0.07% |
| all | screen_depth3 | screen_depth2 | 49/0/23 | -1.93% | +193.37% |
| all | screen_depth4 | screen_depth2 | 49/0/23 | -3.10% | +681.55% |
| all | screen_depth4 | screen_depth3 | 44/0/28 | -1.21% | +127.49% |
