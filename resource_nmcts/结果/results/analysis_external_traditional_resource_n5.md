# External Baseline Analysis

External rows: 417; usable: 417.
Internal rows: 1416; usable: 1416.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_sshr_h | 3 | 3 | 5.33 | 12.67 | 6.12 | 0.000 |
| external_sshr_h | 4 | 69 | 28.58 | 29.74 | 32.50 | 0.000 |
| external_sshr_h | 5 | 67 | 81.13 | 71.84 | 88.79 | 0.002 |
| external_sshr_i_cnot | 3 | 3 | 2.67 | 8.33 | 3.28 | 0.058 |
| external_sshr_i_cnot | 4 | 69 | 24.64 | 23.52 | 28.12 | 0.294 |
| external_sshr_i_cnot | 5 | 67 | 72.00 | 45.61 | 77.99 | 7.432 |
| external_sshr_i_t | 3 | 3 | 2.67 | 8.33 | 3.20 | 0.057 |
| external_sshr_i_t | 4 | 69 | 24.64 | 23.70 | 28.11 | 0.623 |
| external_sshr_i_t | 5 | 67 | 61.79 | 59.82 | 68.69 | 7.939 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_sshr_h | T | 139 | 134 | 1 | 4 | -46.19% |
| and_resource_nmcts | external_sshr_h | CNOT | 139 | 38 | 96 | 5 | +17.52% |
| and_resource_nmcts | external_sshr_h | depth | 139 | 72 | 61 | 6 | -1.11% |
| and_resource_nmcts | external_sshr_h | peak_ancilla | 139 | 2 | 65 | 72 | +44.60% |
| and_resource_nmcts | external_sshr_h | score | 139 | 134 | 5 | 0 | -39.23% |
| and_resource_nmcts | external_sshr_i_cnot | T | 139 | 130 | 1 | 8 | -37.67% |
| and_resource_nmcts | external_sshr_i_cnot | CNOT | 139 | 0 | 131 | 8 | +61.03% |
| and_resource_nmcts | external_sshr_i_cnot | depth | 139 | 21 | 113 | 5 | +29.97% |
| and_resource_nmcts | external_sshr_i_cnot | peak_ancilla | 139 | 0 | 65 | 74 | +46.04% |
| and_resource_nmcts | external_sshr_i_cnot | score | 139 | 133 | 6 | 0 | -29.92% |
| and_resource_nmcts | external_sshr_i_t | T | 139 | 130 | 1 | 8 | -33.83% |
| and_resource_nmcts | external_sshr_i_t | CNOT | 139 | 1 | 127 | 11 | +41.91% |
| and_resource_nmcts | external_sshr_i_t | depth | 139 | 30 | 102 | 7 | +20.11% |
| and_resource_nmcts | external_sshr_i_t | peak_ancilla | 139 | 0 | 65 | 74 | +46.04% |
| and_resource_nmcts | external_sshr_i_t | score | 139 | 131 | 7 | 1 | -26.20% |
| and_affine_nmcts | external_sshr_h | T | 139 | 134 | 1 | 4 | -46.19% |
| and_affine_nmcts | external_sshr_h | CNOT | 139 | 37 | 97 | 5 | +17.75% |
| and_affine_nmcts | external_sshr_h | depth | 139 | 72 | 61 | 6 | -0.97% |
| and_affine_nmcts | external_sshr_h | peak_ancilla | 139 | 2 | 65 | 72 | +44.60% |
| and_affine_nmcts | external_sshr_h | score | 139 | 134 | 5 | 0 | -39.22% |
| and_affine_nmcts | external_sshr_i_cnot | T | 139 | 130 | 1 | 8 | -37.67% |
| and_affine_nmcts | external_sshr_i_cnot | CNOT | 139 | 0 | 131 | 8 | +61.28% |
| and_affine_nmcts | external_sshr_i_cnot | depth | 139 | 20 | 113 | 6 | +30.12% |
| and_affine_nmcts | external_sshr_i_cnot | peak_ancilla | 139 | 0 | 65 | 74 | +46.04% |
| and_affine_nmcts | external_sshr_i_cnot | score | 139 | 133 | 6 | 0 | -29.90% |
| and_affine_nmcts | external_sshr_i_t | T | 139 | 130 | 1 | 8 | -33.83% |
| and_affine_nmcts | external_sshr_i_t | CNOT | 139 | 1 | 127 | 11 | +42.15% |
| and_affine_nmcts | external_sshr_i_t | depth | 139 | 29 | 102 | 8 | +20.26% |
| and_affine_nmcts | external_sshr_i_t | peak_ancilla | 139 | 0 | 65 | 74 | +46.04% |
| and_affine_nmcts | external_sshr_i_t | score | 139 | 131 | 7 | 1 | -26.18% |
| and_cube_beam | external_sshr_h | T | 139 | 89 | 41 | 9 | +5.78% |
| and_cube_beam | external_sshr_h | CNOT | 139 | 14 | 125 | 0 | +59.87% |
| and_cube_beam | external_sshr_h | depth | 139 | 18 | 118 | 3 | +52.25% |
| and_cube_beam | external_sshr_h | peak_ancilla | 139 | 1 | 113 | 25 | +87.41% |
| and_cube_beam | external_sshr_h | score | 139 | 87 | 52 | 0 | +12.70% |
| and_cube_beam | external_sshr_i_cnot | T | 139 | 80 | 49 | 10 | +281.69% |
| and_cube_beam | external_sshr_i_cnot | CNOT | 139 | 0 | 139 | 0 | +198.50% |
| and_cube_beam | external_sshr_i_cnot | depth | 139 | 1 | 138 | 0 | +146.05% |
| and_cube_beam | external_sshr_i_cnot | peak_ancilla | 139 | 0 | 113 | 26 | +88.85% |
| and_cube_beam | external_sshr_i_cnot | score | 139 | 71 | 68 | 0 | +325.08% |
| and_cube_beam | external_sshr_i_t | T | 139 | 67 | 62 | 10 | +287.79% |
| and_cube_beam | external_sshr_i_t | CNOT | 139 | 1 | 138 | 0 | +175.82% |
| and_cube_beam | external_sshr_i_t | depth | 139 | 2 | 137 | 0 | +149.30% |
| and_cube_beam | external_sshr_i_t | peak_ancilla | 139 | 0 | 113 | 26 | +88.85% |
| and_cube_beam | external_sshr_i_t | score | 139 | 59 | 80 | 0 | +330.87% |
| and_esop_milp | external_sshr_h | T | 139 | 116 | 12 | 11 | -25.59% |
| and_esop_milp | external_sshr_h | CNOT | 139 | 30 | 105 | 4 | +22.28% |
| and_esop_milp | external_sshr_h | depth | 139 | 44 | 92 | 3 | +13.66% |
| and_esop_milp | external_sshr_h | peak_ancilla | 139 | 2 | 99 | 38 | +62.23% |
| and_esop_milp | external_sshr_h | score | 139 | 114 | 25 | 0 | -19.74% |
| and_esop_milp | external_sshr_i_cnot | T | 139 | 102 | 18 | 19 | -14.49% |
| and_esop_milp | external_sshr_i_cnot | CNOT | 139 | 0 | 135 | 4 | +66.41% |
| and_esop_milp | external_sshr_i_cnot | depth | 139 | 5 | 134 | 0 | +48.60% |
| and_esop_milp | external_sshr_i_cnot | peak_ancilla | 139 | 0 | 99 | 40 | +63.67% |
| and_esop_milp | external_sshr_i_cnot | score | 139 | 102 | 37 | 0 | -8.03% |
| and_esop_milp | external_sshr_i_t | T | 139 | 98 | 20 | 21 | -9.73% |
| and_esop_milp | external_sshr_i_t | CNOT | 139 | 6 | 129 | 4 | +48.35% |
| and_esop_milp | external_sshr_i_t | depth | 139 | 14 | 123 | 2 | +38.29% |
| and_esop_milp | external_sshr_i_t | peak_ancilla | 139 | 0 | 99 | 40 | +63.67% |
| and_esop_milp | external_sshr_i_t | score | 139 | 98 | 40 | 1 | -3.46% |
| sshr_h | external_sshr_h | T | 139 | 0 | 0 | 139 | +0.00% |
| sshr_h | external_sshr_h | CNOT | 139 | 0 | 0 | 139 | +0.00% |
| sshr_h | external_sshr_h | depth | 139 | 0 | 0 | 139 | +0.00% |
| sshr_h | external_sshr_h | peak_ancilla | 139 | 0 | 0 | 139 | +0.00% |
| sshr_h | external_sshr_h | score | 139 | 0 | 0 | 139 | +0.00% |
| sshr_h | external_sshr_i_cnot | T | 139 | 20 | 76 | 43 | +96.71% |
| sshr_h | external_sshr_i_cnot | CNOT | 139 | 0 | 126 | 13 | +60.39% |
| sshr_h | external_sshr_i_cnot | depth | 139 | 11 | 119 | 9 | +49.22% |
| sshr_h | external_sshr_i_cnot | peak_ancilla | 139 | 0 | 2 | 137 | +1.44% |
| sshr_h | external_sshr_i_cnot | score | 139 | 28 | 105 | 6 | +104.21% |
| sshr_h | external_sshr_i_t | T | 139 | 2 | 94 | 43 | +104.56% |
| sshr_h | external_sshr_i_t | CNOT | 139 | 13 | 107 | 19 | +44.84% |
| sshr_h | external_sshr_i_t | depth | 139 | 20 | 109 | 10 | +41.25% |
| sshr_h | external_sshr_i_t | peak_ancilla | 139 | 0 | 2 | 137 | +1.44% |
| sshr_h | external_sshr_i_t | score | 139 | 8 | 123 | 8 | +110.87% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
