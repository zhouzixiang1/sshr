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
| 24 | adaptive_all_depth | screen_single | 20/0/4 | -9.11% | +36402.38% |
| 24 | adaptive_all_depth | screen_depth1 | 17/0/7 | -5.23% | +5520.07% |
| 24 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.90% | +1161.13% |
| 24 | depth_policy | screen_single | 20/0/4 | -6.34% | +2198.12% |
| 24 | depth_policy | screen_depth2 | 0/1/23 | +0.11% | -6.73% |
| 24 | depth_policy | adaptive_all_depth | 0/17/7 | +3.17% | -89.97% |
| 24 | depth_frontier_policy | screen_single | 20/0/4 | -8.64% | +19311.42% |
| 24 | depth_frontier_policy | screen_depth2 | 12/0/12 | -2.38% | +533.77% |
| 24 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.54% | -23.07% |
| 24 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.54% | -58.19% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.06% |
| 24 | screen_depth3 | screen_depth2 | 16/0/8 | -1.76% | +196.75% |
| 24 | screen_depth4 | screen_depth2 | 16/0/8 | -2.90% | +713.12% |
| 24 | screen_depth4 | screen_depth3 | 14/0/10 | -1.18% | +134.23% |
| 28 | adaptive_all_depth | screen_single | 21/0/3 | -8.26% | +38656.49% |
| 28 | adaptive_all_depth | screen_depth1 | 16/0/8 | -4.10% | +5781.10% |
| 28 | adaptive_all_depth | screen_depth2 | 16/0/8 | -2.26% | +1178.83% |
| 28 | depth_policy | screen_single | 21/0/3 | -6.17% | +2386.27% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.91% |
| 28 | depth_policy | adaptive_all_depth | 0/16/8 | +2.35% | -89.33% |
| 28 | depth_frontier_policy | screen_single | 21/0/3 | -7.77% | +19725.22% |
| 28 | depth_frontier_policy | screen_depth2 | 11/0/13 | -1.72% | +517.22% |
| 28 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.56% | -24.60% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.56% | -59.24% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 28 | screen_depth3 | screen_depth2 | 16/0/8 | -1.23% | +207.50% |
| 28 | screen_depth4 | screen_depth2 | 16/0/8 | -2.26% | +721.43% |
| 28 | screen_depth4 | screen_depth3 | 14/0/10 | -1.05% | +131.35% |
| 32 | adaptive_all_depth | screen_single | 18/0/6 | -7.55% | +28416.22% |
| 32 | adaptive_all_depth | screen_depth1 | 14/0/10 | -4.21% | +4336.04% |
| 32 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.18% | +947.72% |
| 32 | depth_policy | screen_single | 18/0/6 | -5.56% | +1889.88% |
| 32 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.97% |
| 32 | depth_policy | adaptive_all_depth | 0/13/11 | +2.30% | -86.01% |
| 32 | depth_frontier_policy | screen_single | 18/0/6 | -7.07% | +14240.04% |
| 32 | depth_frontier_policy | screen_depth2 | 8/0/16 | -1.65% | +375.14% |
| 32 | depth_frontier_policy | screen_depth4 | 0/5/19 | +0.55% | -22.02% |
| 32 | depth_frontier_policy | adaptive_all_depth | 0/5/19 | +0.55% | -64.30% |
| 32 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 32 | screen_depth3 | screen_depth2 | 13/0/11 | -1.22% | +154.17% |
| 32 | screen_depth4 | screen_depth2 | 13/0/11 | -2.18% | +528.36% |
| 32 | screen_depth4 | screen_depth3 | 11/0/13 | -0.99% | +97.28% |
| 40 | adaptive_all_depth | screen_single | 19/0/5 | -8.68% | +31301.44% |
| 40 | adaptive_all_depth | screen_depth1 | 15/0/9 | -4.53% | +4683.28% |
| 40 | adaptive_all_depth | screen_depth2 | 13/0/11 | -2.42% | +1002.10% |
| 40 | depth_policy | screen_single | 19/0/5 | -6.48% | +2081.84% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.48% |
| 40 | depth_policy | adaptive_all_depth | 0/13/11 | +2.55% | -87.14% |
| 40 | depth_frontier_policy | screen_single | 19/0/5 | -8.01% | +15408.65% |
| 40 | depth_frontier_policy | screen_depth2 | 9/0/15 | -1.66% | +395.94% |
| 40 | depth_frontier_policy | screen_depth4 | 0/4/20 | +0.81% | -24.27% |
| 40 | depth_frontier_policy | adaptive_all_depth | 0/4/20 | +0.81% | -63.24% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| 40 | screen_depth3 | screen_depth2 | 13/0/11 | -1.48% | +167.99% |
| 40 | screen_depth4 | screen_depth2 | 13/0/11 | -2.42% | +576.02% |
| 40 | screen_depth4 | screen_depth3 | 13/0/11 | -0.97% | +107.73% |
| all | adaptive_all_depth | screen_single | 78/0/18 | -8.40% | +33694.13% |
| all | adaptive_all_depth | screen_depth1 | 62/0/34 | -4.52% | +5080.12% |
| all | adaptive_all_depth | screen_depth2 | 58/0/38 | -2.44% | +1072.45% |
| all | depth_policy | screen_single | 78/0/18 | -6.14% | +2139.03% |
| all | depth_policy | screen_depth2 | 0/1/95 | +0.03% | -2.77% |
| all | depth_policy | adaptive_all_depth | 0/59/37 | +2.59% | -88.11% |
| all | depth_frontier_policy | screen_single | 78/0/18 | -7.87% | +17171.33% |
| all | depth_frontier_policy | screen_depth2 | 40/0/56 | -1.85% | +455.52% |
| all | depth_frontier_policy | screen_depth4 | 0/19/77 | +0.61% | -23.49% |
| all | depth_frontier_policy | adaptive_all_depth | 0/19/77 | +0.61% | -61.24% |
| all | depth2_guard_direct | screen_depth2 | 0/0/96 | +0.00% | -0.01% |
| all | screen_depth3 | screen_depth2 | 58/0/38 | -1.42% | +181.60% |
| all | screen_depth4 | screen_depth2 | 58/0/38 | -2.44% | +634.73% |
| all | screen_depth4 | screen_depth3 | 52/0/44 | -1.05% | +117.65% |
