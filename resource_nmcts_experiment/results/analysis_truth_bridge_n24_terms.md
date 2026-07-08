# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=24 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 0.18s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 24 | adaptive_all_depth | screen_single | 6/0/0 | -9.42% | +34710.06% |
| 24 | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.21% | +1070.36% |
| 24 | depth_policy | screen_single | 6/0/0 | -6.96% | +2155.21% |
| 24 | depth_policy | adaptive_all_depth | 0/5/1 | +2.76% | -92.20% |
| 24 | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.05% | +555.27% |
| 24 | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.16% | -27.08% |
| 24 | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.16% | -56.22% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 24 | screen_depth3 | screen_depth2 | 4/0/2 | -1.45% | +194.81% |
| 24 | screen_depth4 | screen_depth2 | 4/0/2 | -2.21% | +642.76% |
| 24 | screen_depth4 | screen_depth3 | 3/0/3 | -0.78% | +120.69% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -9.42% | +34710.06% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.21% | +1070.36% |
| all | depth_policy | screen_single | 6/0/0 | -6.96% | +2155.21% |
| all | depth_policy | adaptive_all_depth | 0/5/1 | +2.76% | -92.20% |
| all | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.05% | +555.27% |
| all | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.16% | -27.08% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.16% | -56.22% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -1.45% | +194.81% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -2.21% | +642.76% |
| all | screen_depth4 | screen_depth3 | 3/0/3 | -0.78% | +120.69% |
