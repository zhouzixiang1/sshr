# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=29 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 6.40s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 29 | adaptive_all_depth | screen_single | 6/0/0 | -8.87% | +32028.65% |
| 29 | adaptive_all_depth | screen_depth2 | 4/0/2 | -1.76% | +973.95% |
| 29 | depth_policy | screen_single | 6/0/0 | -7.03% | +2316.68% |
| 29 | depth_policy | adaptive_all_depth | 0/5/1 | +2.03% | -89.03% |
| 29 | depth_frontier_policy | screen_depth2 | 3/0/3 | -1.37% | +516.59% |
| 29 | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.40% | -22.12% |
| 29 | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.40% | -55.39% |
| 29 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 29 | screen_depth3 | screen_depth2 | 4/0/2 | -1.22% | +177.13% |
| 29 | screen_depth4 | screen_depth2 | 4/0/2 | -1.76% | +563.61% |
| 29 | screen_depth4 | screen_depth3 | 3/0/3 | -0.56% | +104.18% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -8.87% | +32028.65% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -1.76% | +973.95% |
| all | depth_policy | screen_single | 6/0/0 | -7.03% | +2316.68% |
| all | depth_policy | adaptive_all_depth | 0/5/1 | +2.03% | -89.03% |
| all | depth_frontier_policy | screen_depth2 | 3/0/3 | -1.37% | +516.59% |
| all | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.40% | -22.12% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.40% | -55.39% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -1.22% | +177.13% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -1.76% | +563.61% |
| all | screen_depth4 | screen_depth3 | 3/0/3 | -0.56% | +104.18% |
