# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=23 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 208.61s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 23 | adaptive_all_depth | screen_single | 5/0/1 | -8.77% | +45211.92% |
| 23 | adaptive_all_depth | screen_depth2 | 5/0/1 | -2.47% | +1396.22% |
| 23 | depth_policy | screen_single | 5/0/1 | -6.50% | +2582.60% |
| 23 | depth_policy | adaptive_all_depth | 0/5/1 | +2.56% | -91.86% |
| 23 | depth_frontier_policy | screen_depth2 | 5/0/1 | -2.36% | +790.62% |
| 23 | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.12% | -11.39% |
| 23 | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.12% | -45.99% |
| 23 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 23 | screen_depth3 | screen_depth2 | 5/0/1 | -1.94% | +240.79% |
| 23 | screen_depth4 | screen_depth2 | 5/0/1 | -2.47% | +898.77% |
| 23 | screen_depth4 | screen_depth3 | 5/0/1 | -0.55% | +169.45% |
| all | adaptive_all_depth | screen_single | 5/0/1 | -8.77% | +45211.92% |
| all | adaptive_all_depth | screen_depth2 | 5/0/1 | -2.47% | +1396.22% |
| all | depth_policy | screen_single | 5/0/1 | -6.50% | +2582.60% |
| all | depth_policy | adaptive_all_depth | 0/5/1 | +2.56% | -91.86% |
| all | depth_frontier_policy | screen_depth2 | 5/0/1 | -2.36% | +790.62% |
| all | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.12% | -11.39% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.12% | -45.99% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 5/0/1 | -1.94% | +240.79% |
| all | screen_depth4 | screen_depth2 | 5/0/1 | -2.47% | +898.77% |
| all | screen_depth4 | screen_depth3 | 5/0/1 | -0.55% | +169.45% |
