# External Baseline Analysis

External rows: 531; usable: 531.
Internal rows: 1416; usable: 1416.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_sshr_h | 3 | 3 | 5.33 | 12.67 | 6.12 | 0.000 |
| external_sshr_h | 4 | 69 | 28.58 | 29.74 | 32.50 | 0.000 |
| external_sshr_h | 5 | 67 | 81.13 | 71.84 | 88.79 | 0.002 |
| external_sshr_h | 6 | 38 | 182.11 | 133.03 | 194.74 | 0.029 |
| external_sshr_i_cnot | 3 | 3 | 2.67 | 8.33 | 3.28 | 0.058 |
| external_sshr_i_cnot | 4 | 69 | 24.64 | 23.52 | 28.12 | 0.294 |
| external_sshr_i_cnot | 5 | 67 | 72.00 | 45.61 | 77.99 | 7.432 |
| external_sshr_i_cnot | 6 | 38 | 164.32 | 99.26 | 174.44 | 8.770 |
| external_sshr_i_t | 3 | 3 | 2.67 | 8.33 | 3.20 | 0.057 |
| external_sshr_i_t | 4 | 69 | 24.64 | 23.70 | 28.11 | 0.623 |
| external_sshr_i_t | 5 | 67 | 61.79 | 59.82 | 68.69 | 7.939 |
| external_sshr_i_t | 6 | 38 | 175.47 | 154.21 | 189.23 | 8.829 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_sshr_h | T | 177 | 171 | 1 | 5 | -44.20% |
| and_resource_nmcts | external_sshr_h | CNOT | 177 | 40 | 132 | 5 | +28.26% |
| and_resource_nmcts | external_sshr_h | depth | 177 | 75 | 96 | 6 | +5.57% |
| and_resource_nmcts | external_sshr_h | peak_ancilla | 177 | 3 | 96 | 78 | +44.35% |
| and_resource_nmcts | external_sshr_h | score | 177 | 171 | 6 | 0 | -37.51% |
| and_resource_nmcts | external_sshr_i_cnot | T | 177 | 164 | 3 | 10 | -35.34% |
| and_resource_nmcts | external_sshr_i_cnot | CNOT | 177 | 0 | 168 | 9 | +74.82% |
| and_resource_nmcts | external_sshr_i_cnot | depth | 177 | 22 | 150 | 5 | +40.53% |
| and_resource_nmcts | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 98 | 79 | +47.18% |
| and_resource_nmcts | external_sshr_i_cnot | score | 177 | 168 | 9 | 0 | -27.92% |
| and_resource_nmcts | external_sshr_i_t | T | 177 | 166 | 1 | 10 | -33.31% |
| and_resource_nmcts | external_sshr_i_t | CNOT | 177 | 2 | 163 | 12 | +44.35% |
| and_resource_nmcts | external_sshr_i_t | depth | 177 | 40 | 130 | 7 | +20.94% |
| and_resource_nmcts | external_sshr_i_t | peak_ancilla | 177 | 0 | 98 | 79 | +47.18% |
| and_resource_nmcts | external_sshr_i_t | score | 177 | 168 | 8 | 1 | -26.25% |
| and_affine_nmcts | external_sshr_h | T | 177 | 171 | 1 | 5 | -44.13% |
| and_affine_nmcts | external_sshr_h | CNOT | 177 | 39 | 133 | 5 | +29.17% |
| and_affine_nmcts | external_sshr_h | depth | 177 | 75 | 96 | 6 | +5.95% |
| and_affine_nmcts | external_sshr_h | peak_ancilla | 177 | 3 | 95 | 79 | +43.79% |
| and_affine_nmcts | external_sshr_h | score | 177 | 171 | 6 | 0 | -37.42% |
| and_affine_nmcts | external_sshr_i_cnot | T | 177 | 164 | 3 | 10 | -35.26% |
| and_affine_nmcts | external_sshr_i_cnot | CNOT | 177 | 0 | 168 | 9 | +75.87% |
| and_affine_nmcts | external_sshr_i_cnot | depth | 177 | 21 | 150 | 6 | +40.96% |
| and_affine_nmcts | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 97 | 80 | +46.61% |
| and_affine_nmcts | external_sshr_i_cnot | score | 177 | 168 | 9 | 0 | -27.82% |
| and_affine_nmcts | external_sshr_i_t | T | 177 | 166 | 1 | 10 | -33.24% |
| and_affine_nmcts | external_sshr_i_t | CNOT | 177 | 2 | 163 | 12 | +45.05% |
| and_affine_nmcts | external_sshr_i_t | depth | 177 | 38 | 131 | 8 | +21.21% |
| and_affine_nmcts | external_sshr_i_t | peak_ancilla | 177 | 0 | 97 | 80 | +46.61% |
| and_affine_nmcts | external_sshr_i_t | score | 177 | 168 | 8 | 1 | -26.17% |
| and_cube_beam | external_sshr_h | T | 177 | 122 | 46 | 9 | +4.87% |
| and_cube_beam | external_sshr_h | CNOT | 177 | 15 | 162 | 0 | +68.95% |
| and_cube_beam | external_sshr_h | depth | 177 | 19 | 155 | 3 | +59.28% |
| and_cube_beam | external_sshr_h | peak_ancilla | 177 | 1 | 151 | 25 | +91.81% |
| and_cube_beam | external_sshr_h | score | 177 | 119 | 58 | 0 | +11.72% |
| and_cube_beam | external_sshr_i_cnot | T | 177 | 109 | 55 | 13 | +582.29% |
| and_cube_beam | external_sshr_i_cnot | CNOT | 177 | 0 | 177 | 0 | +279.94% |
| and_cube_beam | external_sshr_i_cnot | depth | 177 | 1 | 176 | 0 | +190.03% |
| and_cube_beam | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 151 | 26 | +95.76% |
| and_cube_beam | external_sshr_i_cnot | score | 177 | 96 | 81 | 0 | +657.75% |
| and_cube_beam | external_sshr_i_t | T | 177 | 97 | 70 | 10 | +585.58% |
| and_cube_beam | external_sshr_i_t | CNOT | 177 | 3 | 174 | 0 | +245.44% |
| and_cube_beam | external_sshr_i_t | depth | 177 | 4 | 173 | 0 | +195.93% |
| and_cube_beam | external_sshr_i_t | peak_ancilla | 177 | 0 | 151 | 26 | +95.76% |
| and_cube_beam | external_sshr_i_t | score | 177 | 87 | 90 | 0 | +660.44% |
| and_esop_milp | external_sshr_h | T | 177 | 120 | 46 | 11 | -11.42% |
| and_esop_milp | external_sshr_h | CNOT | 177 | 33 | 140 | 4 | +60.92% |
| and_esop_milp | external_sshr_h | depth | 177 | 47 | 127 | 3 | +46.96% |
| and_esop_milp | external_sshr_h | peak_ancilla | 177 | 3 | 135 | 39 | +68.64% |
| and_esop_milp | external_sshr_h | score | 177 | 117 | 60 | 0 | -5.17% |
| and_esop_milp | external_sshr_i_cnot | T | 177 | 104 | 53 | 20 | +1.10% |
| and_esop_milp | external_sshr_i_cnot | CNOT | 177 | 0 | 172 | 5 | +117.07% |
| and_esop_milp | external_sshr_i_cnot | depth | 177 | 6 | 171 | 0 | +95.34% |
| and_esop_milp | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 135 | 42 | +72.60% |
| and_esop_milp | external_sshr_i_cnot | score | 177 | 105 | 72 | 0 | +8.13% |
| and_esop_milp | external_sshr_i_t | T | 177 | 101 | 54 | 22 | +2.51% |
| and_esop_milp | external_sshr_i_t | CNOT | 177 | 7 | 165 | 5 | +74.94% |
| and_esop_milp | external_sshr_i_t | depth | 177 | 16 | 159 | 2 | +62.59% |
| and_esop_milp | external_sshr_i_t | peak_ancilla | 177 | 0 | 135 | 42 | +72.60% |
| and_esop_milp | external_sshr_i_t | score | 177 | 102 | 74 | 1 | +8.82% |
| sshr_h | external_sshr_h | T | 177 | 0 | 0 | 177 | +0.00% |
| sshr_h | external_sshr_h | CNOT | 177 | 0 | 0 | 177 | +0.00% |
| sshr_h | external_sshr_h | depth | 177 | 0 | 0 | 177 | +0.00% |
| sshr_h | external_sshr_h | peak_ancilla | 177 | 0 | 0 | 177 | +0.00% |
| sshr_h | external_sshr_h | score | 177 | 0 | 0 | 177 | +0.00% |
| sshr_h | external_sshr_i_cnot | T | 177 | 31 | 102 | 44 | +132.84% |
| sshr_h | external_sshr_i_cnot | CNOT | 177 | 0 | 163 | 14 | +65.33% |
| sshr_h | external_sshr_i_cnot | depth | 177 | 12 | 155 | 10 | +52.02% |
| sshr_h | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 5 | 172 | +2.82% |
| sshr_h | external_sshr_i_cnot | score | 177 | 39 | 131 | 7 | +143.95% |
| sshr_h | external_sshr_i_t | T | 177 | 20 | 114 | 43 | +137.70% |
| sshr_h | external_sshr_i_t | CNOT | 177 | 40 | 118 | 19 | +44.29% |
| sshr_h | external_sshr_i_t | depth | 177 | 44 | 121 | 12 | +39.19% |
| sshr_h | external_sshr_i_t | peak_ancilla | 177 | 0 | 5 | 172 | +2.82% |
| sshr_h | external_sshr_i_t | score | 177 | 27 | 142 | 8 | +147.58% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
