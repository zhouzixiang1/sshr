# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=28 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 2.85s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 28 | adaptive_all_depth | screen_single | 6/0/0 | -8.80% | +32952.87% |
| 28 | adaptive_all_depth | screen_depth2 | 4/0/2 | -1.60% | +1001.93% |
| 28 | depth_policy | screen_single | 6/0/0 | -7.30% | +2333.53% |
| 28 | depth_policy | adaptive_all_depth | 0/4/2 | +1.66% | -89.11% |
| 28 | depth_frontier_policy | screen_depth2 | 2/0/4 | -1.28% | +383.43% |
| 28 | depth_frontier_policy | screen_depth4 | 0/2/4 | +0.32% | -34.87% |
| 28 | depth_frontier_policy | adaptive_all_depth | 0/2/4 | +0.32% | -65.39% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 28 | screen_depth3 | screen_depth2 | 4/0/2 | -0.97% | +183.75% |
| 28 | screen_depth4 | screen_depth2 | 4/0/2 | -1.60% | +583.77% |
| 28 | screen_depth4 | screen_depth3 | 2/0/4 | -0.64% | +107.37% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -8.80% | +32952.87% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -1.60% | +1001.93% |
| all | depth_policy | screen_single | 6/0/0 | -7.30% | +2333.53% |
| all | depth_policy | adaptive_all_depth | 0/4/2 | +1.66% | -89.11% |
| all | depth_frontier_policy | screen_depth2 | 2/0/4 | -1.28% | +383.43% |
| all | depth_frontier_policy | screen_depth4 | 0/2/4 | +0.32% | -34.87% |
| all | depth_frontier_policy | adaptive_all_depth | 0/2/4 | +0.32% | -65.39% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -0.97% | +183.75% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -1.60% | +583.77% |
| all | screen_depth4 | screen_depth3 | 2/0/4 | -0.64% | +107.37% |
