# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=21,22 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 120/120 method rows passed.
ANF plan verification: 120/120 method rows passed.
Emitted-circuit ANF verification: 120/120 method rows passed; mismatches=0.
Mean truth-table build time per function: 31.21s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 21 | adaptive_all_depth | screen_single | 6/0/0 | -9.47% | +37783.20% |
| 21 | adaptive_all_depth | screen_depth2 | 5/0/1 | -3.06% | +1166.68% |
| 21 | depth_policy | screen_single | 6/0/0 | -6.63% | +2406.26% |
| 21 | depth_policy | adaptive_all_depth | 0/5/1 | +3.21% | -90.36% |
| 21 | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.43% | +542.66% |
| 21 | depth_frontier_policy | screen_depth4 | 0/2/4 | +0.65% | -25.29% |
| 21 | depth_frontier_policy | adaptive_all_depth | 0/2/4 | +0.65% | -56.85% |
| 21 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 21 | screen_depth3 | screen_depth2 | 5/0/1 | -1.68% | +206.36% |
| 21 | screen_depth4 | screen_depth2 | 5/0/1 | -3.06% | +723.79% |
| 21 | screen_depth4 | screen_depth3 | 4/0/2 | -1.42% | +136.61% |
| 22 | adaptive_all_depth | screen_single | 5/0/1 | -10.92% | +36824.24% |
| 22 | adaptive_all_depth | screen_depth2 | 5/0/1 | -4.56% | +1204.18% |
| 22 | depth_policy | screen_single | 5/0/1 | -6.30% | +2093.81% |
| 22 | depth_policy | adaptive_all_depth | 0/5/1 | +5.35% | -91.93% |
| 22 | depth_frontier_policy | screen_depth2 | 5/0/1 | -4.56% | +724.25% |
| 22 | depth_frontier_policy | screen_depth4 | 0/0/6 | +0.00% | -5.57% |
| 22 | depth_frontier_policy | adaptive_all_depth | 0/0/6 | +0.00% | -44.91% |
| 22 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | -0.35% |
| 22 | screen_depth3 | screen_depth2 | 5/0/1 | -2.98% | +209.84% |
| 22 | screen_depth4 | screen_depth2 | 5/0/1 | -4.56% | +739.69% |
| 22 | screen_depth4 | screen_depth3 | 4/0/2 | -1.64% | +141.00% |
| all | adaptive_all_depth | screen_single | 11/0/1 | -10.19% | +37303.72% |
| all | adaptive_all_depth | screen_depth2 | 10/0/2 | -3.81% | +1185.43% |
| all | depth_policy | screen_single | 11/0/1 | -6.46% | +2250.03% |
| all | depth_policy | adaptive_all_depth | 0/10/2 | +4.28% | -91.15% |
| all | depth_frontier_policy | screen_depth2 | 8/0/4 | -3.50% | +633.45% |
| all | depth_frontier_policy | screen_depth4 | 0/2/10 | +0.32% | -15.43% |
| all | depth_frontier_policy | adaptive_all_depth | 0/2/10 | +0.32% | -50.88% |
| all | depth2_guard_direct | screen_depth2 | 0/0/12 | +0.00% | -0.18% |
| all | screen_depth3 | screen_depth2 | 10/0/2 | -2.33% | +208.10% |
| all | screen_depth4 | screen_depth2 | 10/0/2 | -3.81% | +731.74% |
| all | screen_depth4 | screen_depth3 | 8/0/4 | -1.53% | +138.81% |
