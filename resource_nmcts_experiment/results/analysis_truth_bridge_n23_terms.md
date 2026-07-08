# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=23 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 40/40 method rows passed.
ANF plan verification: 40/40 method rows passed.
Emitted-circuit ANF verification: 40/40 method rows passed; mismatches=0.
Mean truth-table build time per function: 199.22s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 23 | adaptive_all_depth | screen_single | 4/0/0 | -10.78% | +53518.41% |
| 23 | adaptive_all_depth | screen_depth2 | 4/0/0 | -3.11% | +1581.16% |
| 23 | depth_policy | screen_single | 4/0/0 | -7.94% | +3082.40% |
| 23 | depth_policy | adaptive_all_depth | 0/4/0 | +3.22% | -94.03% |
| 23 | depth_frontier_policy | screen_depth2 | 3/0/1 | -2.22% | +841.68% |
| 23 | depth_frontier_policy | screen_depth4 | 0/1/3 | +0.92% | -22.52% |
| 23 | depth_frontier_policy | adaptive_all_depth | 0/1/3 | +0.92% | -45.71% |
| 23 | depth2_guard_direct | screen_depth2 | 0/0/4 | +0.00% | +0.00% |
| 23 | screen_depth3 | screen_depth2 | 4/0/0 | -2.42% | +287.69% |
| 23 | screen_depth4 | screen_depth2 | 4/0/0 | -3.11% | +1068.93% |
| 23 | screen_depth4 | screen_depth3 | 4/0/0 | -0.70% | +201.02% |
| all | adaptive_all_depth | screen_single | 4/0/0 | -10.78% | +53518.41% |
| all | adaptive_all_depth | screen_depth2 | 4/0/0 | -3.11% | +1581.16% |
| all | depth_policy | screen_single | 4/0/0 | -7.94% | +3082.40% |
| all | depth_policy | adaptive_all_depth | 0/4/0 | +3.22% | -94.03% |
| all | depth_frontier_policy | screen_depth2 | 3/0/1 | -2.22% | +841.68% |
| all | depth_frontier_policy | screen_depth4 | 0/1/3 | +0.92% | -22.52% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/3 | +0.92% | -45.71% |
| all | depth2_guard_direct | screen_depth2 | 0/0/4 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/0 | -2.42% | +287.69% |
| all | screen_depth4 | screen_depth2 | 4/0/0 | -3.11% | +1068.93% |
| all | screen_depth4 | screen_depth3 | 4/0/0 | -0.70% | +201.02% |
