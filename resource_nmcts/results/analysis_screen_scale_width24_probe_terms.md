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
| 20 | adaptive_all_depth | screen_single | 23/0/1 | -6.99% | +32482.81% |
| 20 | adaptive_all_depth | screen_depth1 | 21/0/3 | -2.55% | +1372.54% |
| 20 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +21.66% |
| 20 | depth_policy | screen_single | 23/0/1 | -6.76% | +30078.23% |
| 20 | depth_policy | screen_depth2 | 0/3/21 | +0.25% | -11.87% |
| 20 | depth_policy | adaptive_all_depth | 0/3/21 | +0.25% | -22.98% |
| 20 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.01% |
| 28 | adaptive_all_depth | screen_single | 20/0/4 | -5.49% | +25168.24% |
| 28 | adaptive_all_depth | screen_depth1 | 17/0/7 | -2.10% | +1118.06% |
| 28 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +49.71% |
| 28 | depth_policy | screen_single | 20/0/4 | -5.49% | +23668.91% |
| 28 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | -0.16% |
| 28 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -23.81% |
| 28 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | -0.16% |
| 40 | adaptive_all_depth | screen_single | 18/0/6 | -6.36% | +14104.14% |
| 40 | adaptive_all_depth | screen_depth1 | 16/0/8 | -2.50% | +803.55% |
| 40 | adaptive_all_depth | screen_depth2 | 0/0/24 | +0.00% | +57.76% |
| 40 | depth_policy | screen_single | 18/0/6 | -6.36% | +13000.93% |
| 40 | depth_policy | screen_depth2 | 0/0/24 | +0.00% | +0.02% |
| 40 | depth_policy | adaptive_all_depth | 0/0/24 | +0.00% | -26.73% |
| 40 | depth2_guard_direct | screen_depth2 | 0/0/24 | +0.00% | +0.00% |
| all | adaptive_all_depth | screen_single | 61/0/11 | -6.28% | +23918.40% |
| all | adaptive_all_depth | screen_depth1 | 54/0/18 | -2.38% | +1098.05% |
| all | adaptive_all_depth | screen_depth2 | 0/0/72 | +0.00% | +43.04% |
| all | depth_policy | screen_single | 61/0/11 | -6.20% | +22249.36% |
| all | depth_policy | screen_depth2 | 0/3/69 | +0.08% | -4.00% |
| all | depth_policy | adaptive_all_depth | 0/3/69 | +0.08% | -24.51% |
| all | depth2_guard_direct | screen_depth2 | 0/0/72 | +0.00% | -0.05% |
