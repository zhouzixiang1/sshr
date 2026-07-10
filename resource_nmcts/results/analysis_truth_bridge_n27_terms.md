# Truth-Table Bridge for High-Dimensional Boolean Screen

This bridge set builds full truth tables for generated n=27 ANF
term sets, emits X/CNOT/MCT oracle circuits, and verifies each circuit
with the bit-parallel truth-table oracle checker.  It is smaller than
the symbolic n=20--40 scale tests because truth-table construction is
the dominant cost.

Truth-table verification: 60/60 method rows passed.
ANF plan verification: 60/60 method rows passed.
Emitted-circuit ANF verification: 60/60 method rows passed; mismatches=0.
Mean truth-table build time per function: 1.36s.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean plan time |
|---:|---|---|---:|---:|---:|
| 27 | adaptive_all_depth | screen_single | 6/0/0 | -9.11% | +31966.65% |
| 27 | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.85% | +1014.30% |
| 27 | depth_policy | screen_single | 6/0/0 | -6.50% | +2131.87% |
| 27 | depth_policy | adaptive_all_depth | 0/4/2 | +3.01% | -85.48% |
| 27 | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.33% | +569.13% |
| 27 | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.54% | -11.70% |
| 27 | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.54% | -53.12% |
| 27 | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| 27 | screen_depth3 | screen_depth2 | 4/0/2 | -1.70% | +168.71% |
| 27 | screen_depth4 | screen_depth2 | 4/0/2 | -2.85% | +607.41% |
| 27 | screen_depth4 | screen_depth3 | 3/0/3 | -1.19% | +114.17% |
| all | adaptive_all_depth | screen_single | 6/0/0 | -9.11% | +31966.65% |
| all | adaptive_all_depth | screen_depth2 | 4/0/2 | -2.85% | +1014.30% |
| all | depth_policy | screen_single | 6/0/0 | -6.50% | +2131.87% |
| all | depth_policy | adaptive_all_depth | 0/4/2 | +3.01% | -85.48% |
| all | depth_frontier_policy | screen_depth2 | 3/0/3 | -2.33% | +569.13% |
| all | depth_frontier_policy | screen_depth4 | 0/1/5 | +0.54% | -11.70% |
| all | depth_frontier_policy | adaptive_all_depth | 0/1/5 | +0.54% | -53.12% |
| all | depth2_guard_direct | screen_depth2 | 0/0/6 | +0.00% | +0.00% |
| all | screen_depth3 | screen_depth2 | 4/0/2 | -1.70% | +168.71% |
| all | screen_depth4 | screen_depth2 | 4/0/2 | -2.85% | +607.41% |
| all | screen_depth4 | screen_depth3 | 3/0/3 | -1.19% | +114.17% |
