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
| 20 | adaptive_all_depth | screen_single | 23/0/1 | -6.96% | +12139.79% |
| 20 | adaptive_all_depth | screen_depth1 | 21/0/3 | -2.52% | +830.94% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +31.75% |
| 20 | depth_policy | screen_single | 23/0/1 | -6.73% | +10265.10% |
| 20 | depth_policy | screen_depth2 | 0/3/21 | +0.25% | -8.92% |
| 20 | depth_policy | adaptive_all_depth | 0/3/21 | +0.25% | -25.16% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +1.69% |
| 28 | adaptive_all_depth | screen_single | 20/0/4 | -5.49% | +8193.95% |
| 28 | adaptive_all_depth | screen_depth1 | 17/0/7 | -2.10% | +634.83% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +54.50% |
| 28 | depth_policy | screen_single | 20/0/4 | -5.49% | +7143.40% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +0.03% |
| 28 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -26.40% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.02% |
| 40 | adaptive_all_depth | screen_single | 18/0/6 | -6.36% | +6668.44% |
| 40 | adaptive_all_depth | screen_depth1 | 16/0/8 | -2.50% | +598.76% |
| 40 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +59.27% |
| 40 | depth_policy | screen_single | 18/0/6 | -6.36% | +5806.84% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +0.82% |
| 40 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -27.45% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| all | adaptive_all_depth | screen_single | 61/0/11 | -6.27% | +9000.73% |
| all | adaptive_all_depth | screen_depth1 | 54/0/18 | -2.37% | +688.18% |
| all | adaptive_all_depth | screen_depth2 | 0/0/72 | +0.00% | +48.51% |
| all | depth_policy | screen_single | 61/0/11 | -6.19% | +7738.45% |
| all | depth_policy | screen_depth2 | 0/3/69 | +0.08% | -2.69% |
| all | depth_policy | adaptive_all_depth | 0/3/69 | +0.08% | -26.34% |
| all | depth2_guard_direct | screen_depth2 | 0/0/72 | +0.00% | +0.57% |
