# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=26 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 0.68s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 26 | adaptive_all_depth | screen_single | 6/0/0 | -10.94% | +41232.46% |
| 26 | adaptive_all_depth | screen_depth2 | 5/0/1 | -3.42% | +1215.99% |
| 26 | depth_policy | screen_single | 6/0/0 | -7.62% | +2673.14% |
| 26 | depth_policy | adaptive_all_depth | 0/6/0 | +3.74% | -92.19% |
| 26 | depth_frontier_policy | screen_depth2 | 2/0/4 | -1.73% | +370.04% |
| 26 | depth_frontier_policy | screen_depth4 | 0/3/3 | +1.76% | -47.09% |
| 26 | depth_frontier_policy | adaptive_all_depth | 0/3/3 | +1.76% | -68.71% |
| 26 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 26 | screen_depth3 | screen_depth2 | 5/0/1 | -2.31% | +226.94% |
| 26 | screen_depth4 | screen_depth2 | 5/0/1 | -3.42% | +758.44% |
| 26 | screen_depth4 | screen_depth3 | 3/0/3 | -1.14% | +141.11% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -10.94% | +41232.46% |
| all | adaptive_all_depth | screen_depth2 | 5/0/1 | -3.42% | +1215.99% |
| all | depth_policy | screen_single | 6/0/0 | -7.62% | +2673.14% |
| all | depth_policy | adaptive_all_depth | 0/6/0 | +3.74% | -92.19% |
| all | depth_frontier_policy | screen_depth2 | 2/0/4 | -1.73% | +370.04% |
| all | depth_frontier_policy | screen_depth4 | 0/3/3 | +1.76% | -47.09% |
| all | depth_frontier_policy | adaptive_all_depth | 0/3/3 | +1.76% | -68.71% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 5/0/1 | -2.31% | +226.94% |
| all | screen_depth4 | screen_depth2 | 5/0/1 | -3.42% | +758.44% |
| all | screen_depth4 | screen_depth3 | 3/0/3 | -1.14% | +141.11% |
