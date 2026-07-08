# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 504/504 method rows passed.
Emitted-circuit ANF verification: 504/504 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 20 | adaptive_all_depth | screen_single | 23/0/1 | -6.90% | +3872.86% |
| 20 | adaptive_all_depth | screen_depth1 | 21/0/3 | -2.45% | +469.10% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +34.78% |
| 20 | depth_policy | screen_single | 23/0/1 | -6.67% | +2785.73% |
| 20 | depth_policy | screen_depth2 | 0/3/21 | +0.25% | -10.59% |
| 20 | depth_policy | adaptive_all_depth | 0/3/21 | +0.25% | -31.14% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.01% |
| 28 | adaptive_all_depth | screen_single | 20/0/4 | -5.36% | +3132.21% |
| 28 | adaptive_all_depth | screen_depth1 | 17/0/7 | -1.96% | +388.55% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +58.46% |
| 28 | depth_policy | screen_single | 20/0/4 | -5.36% | +2399.10% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -1.12% |
| 28 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -30.51% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +5.73% |
| 40 | adaptive_all_depth | screen_single | 18/0/6 | -6.26% | +2847.18% |
| 40 | adaptive_all_depth | screen_depth1 | 16/0/8 | -2.47% | +372.78% |
| 40 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +79.33% |
| 40 | depth_policy | screen_single | 18/0/6 | -6.26% | +2197.23% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +1.51% |
| 40 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -32.85% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| all | adaptive_all_depth | screen_single | 61/0/11 | -6.17% | +3284.08% |
| all | adaptive_all_depth | screen_depth1 | 54/0/18 | -2.29% | +410.14% |
| all | adaptive_all_depth | screen_depth2 | 0/0/72 | +0.00% | +57.52% |
| all | depth_policy | screen_single | 61/0/11 | -6.10% | +2460.69% |
| all | depth_policy | screen_depth2 | 0/3/69 | +0.08% | -3.40% |
| all | depth_policy | adaptive_all_depth | 0/3/69 | +0.08% | -31.50% |
| all | depth2_guard_direct | screen_depth2 | 0/0/72 | +0.00% | +1.91% |
