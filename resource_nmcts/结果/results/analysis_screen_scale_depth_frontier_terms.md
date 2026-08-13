# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 648/648 method rows passed.
Emitted-circuit ANF verification: 648/648 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 23/0/1 | -10.16% | +40622.80% |
| 20 | adaptive_all_depth | screen_depth1 | 21/0/3 | -5.89% | +6028.54% |
| 20 | adaptive_all_depth | screen_depth2 | 19/0/5 | -3.57% | +1237.33% |
| 20 | depth_policy | screen_single | 23/0/1 | -6.67% | +2410.14% |
| 20 | depth_policy | screen_depth2 | 0/3/21 | +0.25% | -10.96% |
| 20 | depth_policy | adaptive_all_depth | 0/21/3 | +4.04% | -91.93% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.08% |
| 20 | screen_depth3 | screen_depth2 | 19/0/5 | -2.18% | +222.45% |
| 20 | screen_depth4 | screen_depth2 | 19/0/5 | -3.57% | +779.05% |
| 20 | screen_depth4 | screen_depth3 | 17/0/7 | -1.44% | +147.14% |
| 28 | adaptive_all_depth | screen_single | 20/0/4 | -7.96% | +33628.07% |
| 28 | adaptive_all_depth | screen_depth1 | 17/0/7 | -4.69% | +5037.36% |
| 28 | adaptive_all_depth | screen_depth2 | 15/0/9 | -2.83% | +1065.65% |
| 28 | depth_policy | screen_single | 20/0/4 | -5.36% | +2134.23% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +0.02% |
| 28 | depth_policy | adaptive_all_depth | 0/15/9 | +3.00% | -87.03% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.08% |
| 28 | screen_depth3 | screen_depth2 | 15/0/9 | -1.65% | +175.54% |
| 28 | screen_depth4 | screen_depth2 | 15/0/9 | -2.83% | +630.89% |
| 28 | screen_depth4 | screen_depth3 | 13/0/11 | -1.22% | +116.54% |
| 40 | adaptive_all_depth | screen_single | 18/0/6 | -8.91% | +33756.31% |
| 40 | adaptive_all_depth | screen_depth1 | 16/0/8 | -5.25% | +5111.72% |
| 40 | adaptive_all_depth | screen_depth2 | 15/0/9 | -2.91% | +1086.57% |
| 40 | depth_policy | screen_single | 18/0/6 | -6.26% | +2144.86% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.02% |
| 40 | depth_policy | adaptive_all_depth | 0/15/9 | +3.07% | -88.14% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 15/0/9 | -1.96% | +183.14% |
| 40 | screen_depth4 | screen_depth2 | 15/0/9 | -2.91% | +638.99% |
| 40 | screen_depth4 | screen_depth3 | 14/0/10 | -0.97% | +118.97% |
| all | adaptive_all_depth | screen_single | 61/0/11 | -9.01% | +36002.39% |
| all | adaptive_all_depth | screen_depth1 | 54/0/18 | -5.28% | +5392.54% |
| all | adaptive_all_depth | screen_depth2 | 49/0/23 | -3.10% | +1129.85% |
| all | depth_policy | screen_single | 61/0/11 | -6.10% | +2229.74% |
| all | depth_policy | screen_depth2 | 0/3/69 | +0.08% | -3.65% |
| all | depth_policy | adaptive_all_depth | 0/51/21 | +3.37% | -89.03% |
| all | depth2_guard_direct | screen_depth2 | 0/0/72 | +0.00% | -0.00% |
| all | screen_depth3 | screen_depth2 | 49/0/23 | -1.93% | +193.71% |
| all | screen_depth4 | screen_depth2 | 49/0/23 | -3.10% | +682.97% |
| all | screen_depth4 | screen_depth3 | 44/0/28 | -1.21% | +127.55% |
