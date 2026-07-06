# External Baseline Analysis

External rows: 216; usable: 216.
Internal rows: 1416; usable: 1416.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_sshr_h | 3 | 3 | 5.33 | 12.67 | 6.12 | 0.000 |
| external_sshr_h | 4 | 69 | 28.58 | 29.74 | 32.50 | 0.000 |
| external_sshr_i_cnot | 3 | 3 | 2.67 | 8.33 | 3.28 | 0.058 |
| external_sshr_i_cnot | 4 | 69 | 24.64 | 23.52 | 28.12 | 0.294 |
| external_sshr_i_t | 3 | 3 | 2.67 | 8.33 | 3.20 | 0.057 |
| external_sshr_i_t | 4 | 69 | 24.64 | 23.70 | 28.11 | 0.623 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_sshr_h | T | 72 | 68 | 0 | 4 | -44.06% |
| and_resource_nmcts | external_sshr_h | CNOT | 72 | 27 | 42 | 3 | +10.44% |
| and_resource_nmcts | external_sshr_h | depth | 72 | 37 | 29 | 6 | -4.65% |
| and_resource_nmcts | external_sshr_h | peak_ancilla | 72 | 1 | 32 | 39 | +43.06% |
| and_resource_nmcts | external_sshr_h | score | 72 | 68 | 4 | 0 | -36.41% |
| and_resource_nmcts | external_sshr_i_cnot | T | 72 | 65 | 0 | 7 | -34.62% |
| and_resource_nmcts | external_sshr_i_cnot | CNOT | 72 | 0 | 65 | 7 | +36.17% |
| and_resource_nmcts | external_sshr_i_cnot | depth | 72 | 20 | 48 | 4 | +14.88% |
| and_resource_nmcts | external_sshr_i_cnot | peak_ancilla | 72 | 0 | 32 | 40 | +44.44% |
| and_resource_nmcts | external_sshr_i_cnot | score | 72 | 69 | 3 | 0 | -26.45% |
| and_resource_nmcts | external_sshr_i_t | T | 72 | 65 | 0 | 7 | -34.62% |
| and_resource_nmcts | external_sshr_i_t | CNOT | 72 | 1 | 62 | 9 | +35.36% |
| and_resource_nmcts | external_sshr_i_t | depth | 72 | 15 | 51 | 6 | +18.58% |
| and_resource_nmcts | external_sshr_i_t | peak_ancilla | 72 | 0 | 32 | 40 | +44.44% |
| and_resource_nmcts | external_sshr_i_t | score | 72 | 66 | 5 | 1 | -26.21% |
| and_affine_nmcts | external_sshr_h | T | 72 | 68 | 0 | 4 | -44.06% |
| and_affine_nmcts | external_sshr_h | CNOT | 72 | 26 | 43 | 3 | +10.88% |
| and_affine_nmcts | external_sshr_h | depth | 72 | 37 | 29 | 6 | -4.37% |
| and_affine_nmcts | external_sshr_h | peak_ancilla | 72 | 1 | 32 | 39 | +43.06% |
| and_affine_nmcts | external_sshr_h | score | 72 | 68 | 4 | 0 | -36.38% |
| and_affine_nmcts | external_sshr_i_cnot | T | 72 | 65 | 0 | 7 | -34.62% |
| and_affine_nmcts | external_sshr_i_cnot | CNOT | 72 | 0 | 65 | 7 | +36.65% |
| and_affine_nmcts | external_sshr_i_cnot | depth | 72 | 19 | 48 | 5 | +15.16% |
| and_affine_nmcts | external_sshr_i_cnot | peak_ancilla | 72 | 0 | 32 | 40 | +44.44% |
| and_affine_nmcts | external_sshr_i_cnot | score | 72 | 69 | 3 | 0 | -26.43% |
| and_affine_nmcts | external_sshr_i_t | T | 72 | 65 | 0 | 7 | -34.62% |
| and_affine_nmcts | external_sshr_i_t | CNOT | 72 | 1 | 62 | 9 | +35.83% |
| and_affine_nmcts | external_sshr_i_t | depth | 72 | 14 | 51 | 7 | +18.87% |
| and_affine_nmcts | external_sshr_i_t | peak_ancilla | 72 | 0 | 32 | 40 | +44.44% |
| and_affine_nmcts | external_sshr_i_t | score | 72 | 66 | 5 | 1 | -26.18% |
| and_cube_beam | external_sshr_h | T | 72 | 41 | 26 | 5 | +21.67% |
| and_cube_beam | external_sshr_h | CNOT | 72 | 13 | 59 | 0 | +58.31% |
| and_cube_beam | external_sshr_h | depth | 72 | 15 | 56 | 1 | +52.17% |
| and_cube_beam | external_sshr_h | peak_ancilla | 72 | 1 | 46 | 25 | +63.89% |
| and_cube_beam | external_sshr_h | score | 72 | 41 | 31 | 0 | +28.18% |
| and_cube_beam | external_sshr_i_cnot | T | 72 | 35 | 30 | 7 | +190.70% |
| and_cube_beam | external_sshr_i_cnot | CNOT | 72 | 0 | 72 | 0 | +150.11% |
| and_cube_beam | external_sshr_i_cnot | depth | 72 | 1 | 71 | 0 | +107.49% |
| and_cube_beam | external_sshr_i_cnot | peak_ancilla | 72 | 0 | 46 | 26 | +65.28% |
| and_cube_beam | external_sshr_i_cnot | score | 72 | 35 | 37 | 0 | +223.24% |
| and_cube_beam | external_sshr_i_t | T | 72 | 35 | 30 | 7 | +190.70% |
| and_cube_beam | external_sshr_i_t | CNOT | 72 | 0 | 72 | 0 | +149.14% |
| and_cube_beam | external_sshr_i_t | depth | 72 | 1 | 71 | 0 | +144.88% |
| and_cube_beam | external_sshr_i_t | peak_ancilla | 72 | 0 | 46 | 26 | +65.28% |
| and_cube_beam | external_sshr_i_t | score | 72 | 35 | 37 | 0 | +223.74% |
| and_esop_milp | external_sshr_h | T | 72 | 53 | 11 | 8 | -17.06% |
| and_esop_milp | external_sshr_h | CNOT | 72 | 18 | 53 | 1 | +23.45% |
| and_esop_milp | external_sshr_h | depth | 72 | 22 | 48 | 2 | +14.77% |
| and_esop_milp | external_sshr_h | peak_ancilla | 72 | 1 | 35 | 36 | +47.22% |
| and_esop_milp | external_sshr_h | score | 72 | 53 | 19 | 0 | -11.64% |
| and_esop_milp | external_sshr_i_cnot | T | 72 | 45 | 12 | 15 | -5.39% |
| and_esop_milp | external_sshr_i_cnot | CNOT | 72 | 0 | 69 | 3 | +51.64% |
| and_esop_milp | external_sshr_i_cnot | depth | 72 | 4 | 68 | 0 | +36.99% |
| and_esop_milp | external_sshr_i_cnot | peak_ancilla | 72 | 0 | 35 | 37 | +48.61% |
| and_esop_milp | external_sshr_i_cnot | score | 72 | 47 | 25 | 0 | +0.23% |
| and_esop_milp | external_sshr_i_t | T | 72 | 45 | 12 | 15 | -5.39% |
| and_esop_milp | external_sshr_i_t | CNOT | 72 | 1 | 69 | 2 | +50.80% |
| and_esop_milp | external_sshr_i_t | depth | 72 | 2 | 68 | 2 | +41.58% |
| and_esop_milp | external_sshr_i_t | peak_ancilla | 72 | 0 | 35 | 37 | +48.61% |
| and_esop_milp | external_sshr_i_t | score | 72 | 46 | 25 | 1 | +0.61% |
| sshr_h | external_sshr_h | T | 72 | 0 | 0 | 72 | +0.00% |
| sshr_h | external_sshr_h | CNOT | 72 | 0 | 0 | 72 | +0.00% |
| sshr_h | external_sshr_h | depth | 72 | 0 | 0 | 72 | +0.00% |
| sshr_h | external_sshr_h | peak_ancilla | 72 | 0 | 0 | 72 | +0.00% |
| sshr_h | external_sshr_h | score | 72 | 0 | 0 | 72 | +0.00% |
| sshr_h | external_sshr_i_cnot | T | 72 | 0 | 36 | 36 | +39.84% |
| sshr_h | external_sshr_i_cnot | CNOT | 72 | 0 | 61 | 11 | +38.23% |
| sshr_h | external_sshr_i_cnot | depth | 72 | 10 | 54 | 8 | +32.33% |
| sshr_h | external_sshr_i_cnot | peak_ancilla | 72 | 0 | 1 | 71 | +1.39% |
| sshr_h | external_sshr_i_cnot | score | 72 | 7 | 60 | 5 | +42.02% |
| sshr_h | external_sshr_i_t | T | 72 | 0 | 36 | 36 | +39.84% |
| sshr_h | external_sshr_i_t | CNOT | 72 | 0 | 58 | 14 | +37.37% |
| sshr_h | external_sshr_i_t | depth | 72 | 5 | 60 | 7 | +39.50% |
| sshr_h | external_sshr_i_t | peak_ancilla | 72 | 0 | 1 | 71 | +1.39% |
| sshr_h | external_sshr_i_t | score | 72 | 3 | 63 | 6 | +42.27% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
