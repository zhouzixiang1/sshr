# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=21/22 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 120/120 method rows passed.
ANF plan verification: 120/120 method rows passed.
Emitted-circuit ANF verification: 120/120 method rows passed; mismatches=0.
Mean truth-table build time per function: 30.34s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 21 | adaptive_all_depth | screen_single | 6/0/0 | -9.47% | +37746.28% |
| 21 | adaptive_all_depth | screen_depth2 | 5/0/1 | -3.06% | +1167.80% |
| 21 | depth_policy | screen_single | 6/0/0 | -6.63% | +2402.60% |
| 21 | depth_policy | adaptive_all_depth | 0/5/1 | +3.21% | -90.38% |
| 21 | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.43% | +539.47% |
| 21 | depth_frontier_policy | screen_depth4 | 0/2/4 | +0.65% | -25.24% |
| 21 | depth_frontier_policy | adaptive_all_depth | 0/2/4 | +0.65% | -56.95% |
| 21 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 21 | screen_depth3 | screen_depth2 | 5/0/1 | -1.68% | +207.05% |
| 21 | screen_depth4 | screen_depth2 | 5/0/1 | -3.06% | +724.07% |
| 21 | screen_depth4 | screen_depth3 | 4/0/2 | -1.42% | +136.18% |
| 22 | adaptive_all_depth | screen_single | 5/0/1 | -10.92% | +37746.25% |
| 22 | adaptive_all_depth | screen_depth2 | 5/0/1 | -4.56% | +1210.23% |
| 22 | depth_policy | screen_single | 5/0/1 | -6.30% | +2141.69% |
| 22 | depth_policy | adaptive_all_depth | 0/5/1 | +5.35% | -91.93% |
| 22 | depth_frontier_policy | screen_depth2 | 5/0/1 | -4.56% | +729.95% |
| 22 | depth_frontier_policy | screen_depth4 | 0/0/6 | +0.00% | -5.85% |
| 22 | depth_frontier_policy | adaptive_all_depth | 0/0/6 | +0.00% | -44.78% |
| 22 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | -0.03% |
| 22 | screen_depth3 | screen_depth2 | 5/0/1 | -2.98% | +209.33% |
| 22 | screen_depth4 | screen_depth2 | 5/0/1 | -4.56% | +745.75% |
| 22 | screen_depth4 | screen_depth3 | 4/0/2 | -1.64% | +143.36% |
| all | adaptive_all_depth | screen_single | 11/0/1 | -10.19% | +37746.26% |
| all | adaptive_all_depth | screen_depth2 | 10/0/2 | -3.81% | +1189.02% |
| all | depth_policy | screen_single | 11/0/1 | -6.46% | +2272.14% |
| all | depth_policy | adaptive_all_depth | 0/10/2 | +4.28% | -91.16% |
| all | depth_frontier_policy | screen_depth2 | 8/0/4 | -3.50% | +634.71% |
| all | depth_frontier_policy | screen_depth4 | 0/2/10 | +0.32% | -15.54% |
| all | depth_frontier_policy | adaptive_all_depth | 0/2/10 | +0.32% | -50.87% |
| all | depth2_guard_direct | screen_depth2 | 0/0/12 | +0.00% | -0.01% |
| all | screen_depth3 | screen_depth2 | 10/0/2 | -2.33% | +208.19% |
| all | screen_depth4 | screen_depth2 | 10/0/2 | -3.81% | +734.91% |
| all | screen_depth4 | screen_depth3 | 8/0/4 | -1.53% | +139.77% |
