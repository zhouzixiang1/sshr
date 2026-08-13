# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=25 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 0.45s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 25 | adaptive_all_depth | screen_single | 6/0/0 | -7.31% | +39171.94% |
| 25 | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.14% | +1215.08% |
| 25 | depth_policy | screen_single | 6/0/0 | -5.34% | +2393.41% |
| 25 | depth_policy | adaptive_all_depth | 0/4/2 | +2.23% | -88.91% |
| 25 | depth_frontier_policy | screen_depth2 | 4/0/2 | -2.14% | +744.84% |
| 25 | depth_frontier_policy | screen_depth4 | 0/0/6 | +0.00% | -8.87% |
| 25 | depth_frontier_policy | adaptive_all_depth | 0/0/6 | +0.00% | -46.09% |
| 25 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 25 | screen_depth3 | screen_depth2 | 4/0/2 | -1.34% | +211.63% |
| 25 | screen_depth4 | screen_depth2 | 4/0/2 | -2.14% | +763.25% |
| 25 | screen_depth4 | screen_depth3 | 4/0/2 | -0.82% | +140.28% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -7.31% | +39171.94% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.14% | +1215.08% |
| all | depth_policy | screen_single | 6/0/0 | -5.34% | +2393.41% |
| all | depth_policy | adaptive_all_depth | 0/4/2 | +2.23% | -88.91% |
| all | depth_frontier_policy | screen_depth2 | 4/0/2 | -2.14% | +744.84% |
| all | depth_frontier_policy | screen_depth4 | 0/0/6 | +0.00% | -8.87% |
| all | depth_frontier_policy | adaptive_all_depth | 0/0/6 | +0.00% | -46.09% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -1.34% | +211.63% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -2.14% | +763.25% |
| all | screen_depth4 | screen_depth3 | 4/0/2 | -0.82% | +140.28% |
