# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 1344/1344 method rows passed.
Emitted-circuit ANF verification: 1344/1344 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 45/0/3 | -7.11% | +3293.37% |
| 20 | adaptive_all_depth | screen_depth1 | 39/0/9 | -2.51% | +431.24% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +37.58% |
| 20 | depth_policy | screen_single | 45/0/3 | -6.95% | +2407.05% |
| 20 | depth_policy | screen_depth2 | 0/4/44 | +0.18% | -10.18% |
| 20 | depth_policy | adaptive_all_depth | 0/4/44 | +0.18% | -31.63% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.05% |
| 22 | adaptive_all_depth | screen_single | 42/0/6 | -6.70% | +3041.85% |
| 22 | adaptive_all_depth | screen_depth1 | 37/0/11 | -2.33% | +414.40% |
| 22 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +47.98% |
| 22 | depth_policy | screen_single | 42/0/6 | -6.66% | +2337.33% |
| 22 | depth_policy | screen_depth2 | 0/1/47 | +0.05% | -4.13% |
| 22 | depth_policy | adaptive_all_depth | 0/1/47 | +0.05% | -30.24% |
| 22 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.57% |
| 24 | adaptive_all_depth | screen_single | 42/0/6 | -6.82% | +3203.96% |
| 24 | adaptive_all_depth | screen_depth1 | 35/0/13 | -2.49% | +431.43% |
| 24 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +46.64% |
| 24 | depth_policy | screen_single | 42/0/6 | -6.75% | +2440.75% |
| 24 | depth_policy | screen_depth2 | 0/1/47 | +0.08% | -4.92% |
| 24 | depth_policy | adaptive_all_depth | 0/1/47 | +0.08% | -30.02% |
| 24 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.01% |
| 28 | adaptive_all_depth | screen_single | 40/0/8 | -5.89% | +2771.67% |
| 28 | adaptive_all_depth | screen_depth1 | 33/0/15 | -2.17% | +393.15% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +59.49% |
| 28 | depth_policy | screen_single | 40/0/8 | -5.89% | +2129.51% |
| 28 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -2.01% |
| 28 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -32.15% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.05% |
| all | adaptive_all_depth | screen_single | 169/0/23 | -6.63% | +3077.71% |
| all | adaptive_all_depth | screen_depth1 | 144/0/48 | -2.37% | +417.55% |
| all | adaptive_all_depth | screen_depth2 | 0/0/192 | +0.00% | +47.92% |
| all | depth_policy | screen_single | 169/0/23 | -6.56% | +2328.66% |
| all | depth_policy | screen_depth2 | 0/6/186 | +0.08% | -5.31% |
| all | depth_policy | adaptive_all_depth | 0/6/186 | +0.08% | -31.01% |
| all | depth2_guard_direct | screen_depth2 | 0/0/192 | +0.00% | -0.14% |
