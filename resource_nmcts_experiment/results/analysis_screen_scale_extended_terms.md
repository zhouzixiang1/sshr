# Term-Set Boolean Screen Scale

Large-scale logic-level ANF term-set evaluation. These rows do not build
full truth tables; they evaluate the synthesis search state directly.
Each method row is also checked twice: first by symbolic ANF plan
expansion, then by symbolic simulation of the emitted X/CNOT/MCT
oracle circuit over GF(2) polynomials.

ANF plan verification: 1008/1008 method rows passed.
Emitted-circuit ANF verification: 1008/1008 method rows passed; mismatches=0.

## Paired comparisons

| n | method | baseline | score W/L/T | mean score | mean time |
|---:|---|---|---:|---:|---:|
| 32 | adaptive_all_depth | screen_single | 38/0/10 | -5.93% | +2876.94% |
| 32 | adaptive_all_depth | screen_depth1 | 34/0/14 | -2.10% | +403.49% |
| 32 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +60.44% |
| 32 | depth_policy | screen_single | 38/0/10 | -5.93% | +2234.74% |
| 32 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -1.69% |
| 32 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -31.52% |
| 32 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | -0.01% |
| 36 | adaptive_all_depth | screen_single | 35/0/13 | -4.55% | +2468.55% |
| 36 | adaptive_all_depth | screen_depth1 | 27/0/21 | -1.62% | +359.36% |
| 36 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +68.72% |
| 36 | depth_policy | screen_single | 35/0/13 | -4.55% | +1866.80% |
| 36 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -2.58% |
| 36 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -35.68% |
| 36 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.00% |
| 40 | adaptive_all_depth | screen_single | 37/0/11 | -6.16% | +2696.31% |
| 40 | adaptive_all_depth | screen_depth1 | 31/0/17 | -2.25% | +382.95% |
| 40 | adaptive_all_depth | screen_depth2 | 0/0/48 | +0.00% | +63.95% |
| 40 | depth_policy | screen_single | 37/0/11 | -6.16% | +2081.79% |
| 40 | depth_policy | screen_depth2 | 0/0/48 | +0.00% | -0.01% |
| 40 | depth_policy | adaptive_all_depth | 0/0/48 | +0.00% | -32.21% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/48 | +0.00% | +0.00% |
| all | adaptive_all_depth | screen_single | 110/0/34 | -5.55% | +2680.60% |
| all | adaptive_all_depth | screen_depth1 | 92/0/52 | -1.99% | +381.94% |
| all | adaptive_all_depth | screen_depth2 | 0/0/144 | +0.00% | +64.37% |
| all | depth_policy | screen_single | 110/0/34 | -5.55% | +2061.11% |
| all | depth_policy | screen_depth2 | 0/0/144 | +0.00% | -1.43% |
| all | depth_policy | adaptive_all_depth | 0/0/144 | +0.00% | -33.14% |
| all | depth2_guard_direct | screen_depth2 | 0/0/144 | +0.00% | -0.00% |
