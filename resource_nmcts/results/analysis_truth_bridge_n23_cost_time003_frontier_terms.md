# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=23 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 209.42s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 23 | adaptive_all_depth | screen_single | 5/0/1 | -8.77% | +44114.57% |
| 23 | adaptive_all_depth | screen_depth2 | 5/0/1 | -2.47% | +1394.46% |
| 23 | depth_policy | screen_single | 5/0/1 | -6.50% | +2515.92% |
| 23 | depth_policy | adaptive_all_depth | 0/5/1 | +2.56% | -91.66% |
| 23 | depth_frontier_policy | screen_depth2 | 4/0/2 | -1.46% | +196.09% |
| 23 | depth_frontier_policy | screen_depth4 | 0/5/1 | +1.04% | -60.40% |
| 23 | depth_frontier_policy | adaptive_all_depth | 0/5/1 | +1.04% | -80.46% |
| 23 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 23 | screen_depth3 | screen_depth2 | 5/0/1 | -1.94% | +240.94% |
| 23 | screen_depth4 | screen_depth2 | 5/0/1 | -2.47% | +901.06% |
| 23 | screen_depth4 | screen_depth3 | 5/0/1 | -0.55% | +169.30% |
| all | adaptive_all_depth | screen_single | 5/0/1 | -8.77% | +44114.57% |
| all | adaptive_all_depth | screen_depth2 | 5/0/1 | -2.47% | +1394.46% |
| all | depth_policy | screen_single | 5/0/1 | -6.50% | +2515.92% |
| all | depth_policy | adaptive_all_depth | 0/5/1 | +2.56% | -91.66% |
| all | depth_frontier_policy | screen_depth2 | 4/0/2 | -1.46% | +196.09% |
| all | depth_frontier_policy | screen_depth4 | 0/5/1 | +1.04% | -60.40% |
| all | depth_frontier_policy | adaptive_all_depth | 0/5/1 | +1.04% | -80.46% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 5/0/1 | -1.94% | +240.94% |
| all | screen_depth4 | screen_depth2 | 5/0/1 | -2.47% | +901.06% |
| all | screen_depth4 | screen_depth3 | 5/0/1 | -0.55% | +169.30% |
