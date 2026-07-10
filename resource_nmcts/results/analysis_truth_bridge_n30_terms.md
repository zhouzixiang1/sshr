# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=30 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 27.69s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 30 | adaptive_all_depth | screen_single | 4/0/2 | -9.39% | +36723.98% |
| 30 | adaptive_all_depth | screen_depth2 | 4/0/2 | -3.42% | +1193.00% |
| 30 | depth_policy | screen_single | 4/0/2 | -6.33% | +2092.95% |
| 30 | depth_policy | adaptive_all_depth | 0/4/2 | +3.62% | -88.77% |
| 30 | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.17% | +561.30% |
| 30 | depth_frontier_policy | screen_depth4 | 0/1/5 | +1.34% | -14.30% |
| 30 | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +1.34% | -56.22% |
| 30 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | -1.09% |
| 30 | screen_depth3 | screen_depth2 | 4/0/2 | -2.09% | +194.63% |
| 30 | screen_depth4 | screen_depth2 | 4/0/2 | -3.42% | +735.96% |
| 30 | screen_depth4 | screen_depth3 | 4/0/2 | -1.37% | +137.71% |
| all | adaptive_all_depth | screen_single | 4/0/2 | -9.39% | +36723.98% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -3.42% | +1193.00% |
| all | depth_policy | screen_single | 4/0/2 | -6.33% | +2092.95% |
| all | depth_policy | adaptive_all_depth | 0/4/2 | +3.62% | -88.77% |
| all | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.17% | +561.30% |
| all | depth_frontier_policy | screen_depth4 | 0/1/5 | +1.34% | -14.30% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +1.34% | -56.22% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | -1.09% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -2.09% | +194.63% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -3.42% | +735.96% |
| all | screen_depth4 | screen_depth3 | 4/0/2 | -1.37% | +137.71% |
