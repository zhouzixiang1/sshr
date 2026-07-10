# External Baseline Analysis

External rows: 1416; usable: 1416.
Internal rows: 1770; usable: 1770.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 3 | 3 | 18.67 | 47.67 | 30.62 | 0.035 |
| external_abc_aig | 4 | 69 | 31.65 | 80.13 | 51.62 | 0.034 |
| external_abc_aig | 5 | 67 | 64.78 | 162.94 | 105.19 | 0.034 |
| external_abc_aig | 6 | 38 | 160.95 | 403.37 | 260.39 | 0.036 |
| external_abc_esop | 3 | 3 | 8.00 | 15.00 | 8.96 | 0.035 |
| external_abc_esop | 4 | 69 | 22.84 | 38.00 | 28.33 | 0.035 |
| external_abc_esop | 5 | 67 | 53.61 | 86.60 | 64.26 | 0.036 |
| external_abc_esop | 6 | 38 | 117.16 | 186.00 | 135.98 | 0.035 |
| external_abc_lut | 3 | 3 | 16.00 | 31.00 | 19.86 | 0.038 |
| external_abc_lut | 4 | 69 | 66.09 | 115.12 | 77.80 | 0.038 |
| external_abc_lut | 5 | 67 | 224.00 | 385.63 | 259.29 | 0.038 |
| external_abc_lut | 6 | 38 | 478.74 | 830.11 | 552.17 | 0.038 |
| external_abc_xag | 3 | 3 | 20.00 | 31.67 | 32.43 | 0.050 |
| external_abc_xag | 4 | 69 | 38.38 | 60.57 | 62.72 | 0.036 |
| external_abc_xag | 5 | 67 | 85.85 | 133.15 | 138.66 | 0.036 |
| external_abc_xag | 6 | 38 | 176.74 | 272.68 | 284.50 | 0.035 |
| external_bdd | 3 | 3 | 37.33 | 70.33 | 50.46 | 0.000 |
| external_bdd | 4 | 69 | 56.46 | 106.48 | 77.04 | 0.000 |
| external_bdd | 5 | 67 | 114.75 | 211.30 | 151.96 | 0.001 |
| external_bdd | 6 | 38 | 228.63 | 413.53 | 296.06 | 0.001 |
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
| and_resource_nmcts | external_abc_aig | T | 177 | 173 | 2 | 2 | -42.17% |
| and_resource_nmcts | external_abc_aig | CNOT | 177 | 177 | 0 | 0 | -51.88% |
| and_resource_nmcts | external_abc_aig | depth | 177 | 50 | 126 | 1 | +52.86% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 177 | 177 | 0 | 0 | -86.08% |
| and_resource_nmcts | external_abc_aig | score | 177 | 177 | 0 | 0 | -55.56% |
| and_resource_nmcts | external_abc_esop | T | 177 | 153 | 8 | 16 | -24.26% |
| and_resource_nmcts | external_abc_esop | CNOT | 177 | 95 | 67 | 15 | -3.45% |
| and_resource_nmcts | external_abc_esop | depth | 177 | 146 | 23 | 8 | -14.89% |
| and_resource_nmcts | external_abc_esop | peak_ancilla | 177 | 67 | 2 | 108 | -11.25% |
| and_resource_nmcts | external_abc_esop | score | 177 | 157 | 14 | 6 | -21.61% |
| and_resource_nmcts | external_abc_lut | T | 177 | 175 | 0 | 2 | -77.47% |
| and_resource_nmcts | external_abc_lut | CNOT | 177 | 177 | 0 | 0 | -73.59% |
| and_resource_nmcts | external_abc_lut | depth | 177 | 177 | 0 | 0 | -71.97% |
| and_resource_nmcts | external_abc_lut | peak_ancilla | 177 | 176 | 0 | 1 | -60.10% |
| and_resource_nmcts | external_abc_lut | score | 177 | 177 | 0 | 0 | -76.93% |
| and_resource_nmcts | external_abc_xag | T | 177 | 177 | 0 | 0 | -53.44% |
| and_resource_nmcts | external_abc_xag | CNOT | 177 | 174 | 3 | 0 | -37.28% |
| and_resource_nmcts | external_abc_xag | depth | 177 | 30 | 144 | 3 | +86.42% |
| and_resource_nmcts | external_abc_xag | peak_ancilla | 177 | 177 | 0 | 0 | -89.70% |
| and_resource_nmcts | external_abc_xag | score | 177 | 177 | 0 | 0 | -64.15% |
| and_resource_nmcts | external_bdd | T | 177 | 177 | 0 | 0 | -65.70% |
| and_resource_nmcts | external_bdd | CNOT | 177 | 177 | 0 | 0 | -61.37% |
| and_resource_nmcts | external_bdd | depth | 177 | 177 | 0 | 0 | -65.01% |
| and_resource_nmcts | external_bdd | peak_ancilla | 177 | 177 | 0 | 0 | -82.11% |
| and_resource_nmcts | external_bdd | score | 177 | 177 | 0 | 0 | -68.02% |
| and_resource_nmcts | external_sshr_h | T | 177 | 173 | 1 | 3 | -45.61% |
| and_resource_nmcts | external_sshr_h | CNOT | 177 | 41 | 131 | 5 | +25.03% |
| and_resource_nmcts | external_sshr_h | depth | 177 | 77 | 94 | 6 | +2.90% |
| and_resource_nmcts | external_sshr_h | peak_ancilla | 177 | 3 | 101 | 73 | +46.33% |
| and_resource_nmcts | external_sshr_h | score | 177 | 173 | 4 | 0 | -38.87% |
| and_resource_nmcts | external_sshr_i_cnot | T | 177 | 168 | 1 | 8 | -36.96% |
| and_resource_nmcts | external_sshr_i_cnot | CNOT | 177 | 0 | 168 | 9 | +70.26% |
| and_resource_nmcts | external_sshr_i_cnot | depth | 177 | 22 | 150 | 5 | +36.70% |
| and_resource_nmcts | external_sshr_i_cnot | peak_ancilla | 177 | 0 | 101 | 76 | +49.72% |
| and_resource_nmcts | external_sshr_i_cnot | score | 177 | 172 | 5 | 0 | -29.48% |
| and_resource_nmcts | external_sshr_i_t | T | 177 | 168 | 1 | 8 | -34.81% |
| and_resource_nmcts | external_sshr_i_t | CNOT | 177 | 4 | 161 | 12 | +41.11% |
| and_resource_nmcts | external_sshr_i_t | depth | 177 | 44 | 126 | 7 | +18.24% |
| and_resource_nmcts | external_sshr_i_t | peak_ancilla | 177 | 0 | 101 | 76 | +49.72% |
| and_resource_nmcts | external_sshr_i_t | score | 177 | 169 | 7 | 1 | -27.67% |
| and_affine_nmcts | external_abc_aig | T | 177 | 170 | 3 | 4 | -40.49% |
| and_affine_nmcts | external_abc_aig | CNOT | 177 | 177 | 0 | 0 | -50.34% |
| and_affine_nmcts | external_abc_aig | depth | 177 | 49 | 126 | 2 | +58.59% |
| and_affine_nmcts | external_abc_aig | peak_ancilla | 177 | 177 | 0 | 0 | -86.32% |
| and_affine_nmcts | external_abc_aig | score | 177 | 177 | 0 | 0 | -54.46% |
| and_affine_nmcts | external_abc_esop | T | 177 | 144 | 20 | 13 | -22.23% |
| and_affine_nmcts | external_abc_esop | CNOT | 177 | 93 | 71 | 13 | -0.55% |
| and_affine_nmcts | external_abc_esop | depth | 177 | 138 | 33 | 6 | -12.63% |
| and_affine_nmcts | external_abc_esop | peak_ancilla | 177 | 71 | 0 | 106 | -12.99% |
| and_affine_nmcts | external_abc_esop | score | 177 | 145 | 27 | 5 | -19.75% |
| and_affine_nmcts | external_abc_lut | T | 177 | 175 | 0 | 2 | -76.85% |
| and_affine_nmcts | external_abc_lut | CNOT | 177 | 177 | 0 | 0 | -72.78% |
| and_affine_nmcts | external_abc_lut | depth | 177 | 177 | 0 | 0 | -71.24% |
| and_affine_nmcts | external_abc_lut | peak_ancilla | 177 | 177 | 0 | 0 | -60.72% |
| and_affine_nmcts | external_abc_lut | score | 177 | 177 | 0 | 0 | -76.37% |
| and_affine_nmcts | external_abc_xag | T | 177 | 176 | 0 | 1 | -51.97% |
| and_affine_nmcts | external_abc_xag | CNOT | 177 | 168 | 9 | 0 | -35.14% |
| and_affine_nmcts | external_abc_xag | depth | 177 | 29 | 144 | 4 | +93.78% |
| and_affine_nmcts | external_abc_xag | peak_ancilla | 177 | 177 | 0 | 0 | -89.88% |
| and_affine_nmcts | external_abc_xag | score | 177 | 177 | 0 | 0 | -63.18% |
| and_affine_nmcts | external_bdd | T | 177 | 177 | 0 | 0 | -64.57% |
| and_affine_nmcts | external_bdd | CNOT | 177 | 177 | 0 | 0 | -59.98% |
| and_affine_nmcts | external_bdd | depth | 177 | 177 | 0 | 0 | -63.87% |
| and_affine_nmcts | external_bdd | peak_ancilla | 177 | 177 | 0 | 0 | -82.47% |
| and_affine_nmcts | external_bdd | score | 177 | 177 | 0 | 0 | -67.10% |
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
| and_cube_beam | external_abc_aig | T | 177 | 103 | 58 | 16 | +3.62% |
| and_cube_beam | external_abc_aig | CNOT | 177 | 165 | 12 | 0 | -33.18% |
| and_cube_beam | external_abc_aig | depth | 177 | 16 | 161 | 0 | +129.60% |
| and_cube_beam | external_abc_aig | peak_ancilla | 177 | 177 | 0 | 0 | -82.19% |
| and_cube_beam | external_abc_aig | score | 177 | 160 | 17 | 0 | -24.17% |
| and_cube_beam | external_abc_esop | T | 177 | 13 | 111 | 53 | +596.71% |
| and_cube_beam | external_abc_esop | CNOT | 177 | 15 | 132 | 30 | +186.18% |
| and_cube_beam | external_abc_esop | depth | 177 | 28 | 133 | 16 | +219.31% |
| and_cube_beam | external_abc_esop | peak_ancilla | 177 | 1 | 40 | 136 | +18.03% |
| and_cube_beam | external_abc_esop | score | 177 | 26 | 135 | 16 | +664.15% |
| and_cube_beam | external_abc_lut | T | 177 | 172 | 5 | 0 | +23.62% |
| and_cube_beam | external_abc_lut | CNOT | 177 | 172 | 5 | 0 | -43.23% |
| and_cube_beam | external_abc_lut | depth | 177 | 172 | 5 | 0 | -32.38% |
| and_cube_beam | external_abc_lut | peak_ancilla | 177 | 161 | 2 | 14 | -46.46% |
| and_cube_beam | external_abc_lut | score | 177 | 172 | 5 | 0 | -18.91% |
| and_cube_beam | external_abc_xag | T | 177 | 148 | 24 | 5 | -4.93% |
| and_cube_beam | external_abc_xag | CNOT | 177 | 146 | 30 | 1 | -3.65% |
| and_cube_beam | external_abc_xag | depth | 177 | 5 | 171 | 1 | +189.45% |
| and_cube_beam | external_abc_xag | peak_ancilla | 177 | 177 | 0 | 0 | -86.52% |
| and_cube_beam | external_abc_xag | score | 177 | 169 | 8 | 0 | -32.09% |
| and_cube_beam | external_bdd | T | 177 | 168 | 7 | 2 | -40.47% |
| and_cube_beam | external_bdd | CNOT | 177 | 170 | 7 | 0 | -47.67% |
| and_cube_beam | external_bdd | depth | 177 | 170 | 7 | 0 | -46.10% |
| and_cube_beam | external_bdd | peak_ancilla | 177 | 177 | 0 | 0 | -76.71% |
| and_cube_beam | external_bdd | score | 177 | 170 | 7 | 0 | -46.78% |
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
| and_esop_milp | external_abc_aig | T | 177 | 118 | 44 | 15 | -7.69% |
| and_esop_milp | external_abc_aig | CNOT | 177 | 156 | 21 | 0 | -40.25% |
| and_esop_milp | external_abc_aig | depth | 177 | 30 | 142 | 5 | +136.60% |
| and_esop_milp | external_abc_aig | peak_ancilla | 177 | 177 | 0 | 0 | -84.22% |
| and_esop_milp | external_abc_aig | score | 177 | 150 | 27 | 0 | -32.43% |
| and_esop_milp | external_abc_esop | T | 177 | 53 | 40 | 84 | +20.51% |
| and_esop_milp | external_abc_esop | CNOT | 177 | 56 | 62 | 59 | +20.98% |
| and_esop_milp | external_abc_esop | depth | 177 | 96 | 45 | 36 | +18.56% |
| and_esop_milp | external_abc_esop | peak_ancilla | 177 | 7 | 12 | 158 | +1.22% |
| and_esop_milp | external_abc_esop | score | 177 | 93 | 50 | 34 | +19.53% |
| and_esop_milp | external_abc_lut | T | 177 | 175 | 0 | 2 | -64.83% |
| and_esop_milp | external_abc_lut | CNOT | 177 | 177 | 0 | 0 | -67.39% |
| and_esop_milp | external_abc_lut | depth | 177 | 177 | 0 | 0 | -61.77% |
| and_esop_milp | external_abc_lut | peak_ancilla | 177 | 174 | 0 | 3 | -54.67% |
| and_esop_milp | external_abc_lut | score | 177 | 177 | 0 | 0 | -65.16% |
| and_esop_milp | external_abc_xag | T | 177 | 138 | 36 | 3 | -23.58% |
| and_esop_milp | external_abc_xag | CNOT | 177 | 137 | 40 | 0 | -20.10% |
| and_esop_milp | external_abc_xag | depth | 177 | 18 | 159 | 0 | +192.44% |
| and_esop_milp | external_abc_xag | peak_ancilla | 177 | 177 | 0 | 0 | -88.35% |
| and_esop_milp | external_abc_xag | score | 177 | 155 | 22 | 0 | -44.08% |
| and_esop_milp | external_bdd | T | 177 | 148 | 29 | 0 | -43.43% |
| and_esop_milp | external_bdd | CNOT | 177 | 158 | 18 | 1 | -50.21% |
| and_esop_milp | external_bdd | depth | 177 | 158 | 19 | 0 | -49.53% |
| and_esop_milp | external_bdd | peak_ancilla | 177 | 177 | 0 | 0 | -79.31% |
| and_esop_milp | external_bdd | score | 177 | 158 | 19 | 0 | -49.55% |
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
| sshr_h | external_abc_aig | T | 177 | 69 | 99 | 9 | +11.86% |
| sshr_h | external_abc_aig | CNOT | 177 | 177 | 0 | 0 | -59.49% |
| sshr_h | external_abc_aig | depth | 177 | 47 | 126 | 4 | +48.35% |
| sshr_h | external_abc_aig | peak_ancilla | 177 | 177 | 0 | 0 | -90.09% |
| sshr_h | external_abc_aig | score | 177 | 148 | 29 | 0 | -24.05% |
| sshr_h | external_abc_esop | T | 177 | 17 | 148 | 12 | +159.35% |
| sshr_h | external_abc_esop | CNOT | 177 | 149 | 27 | 1 | +7.38% |
| sshr_h | external_abc_esop | depth | 177 | 136 | 38 | 3 | +19.18% |
| sshr_h | external_abc_esop | peak_ancilla | 177 | 137 | 3 | 37 | -33.71% |
| sshr_h | external_abc_esop | score | 177 | 32 | 145 | 0 | +158.69% |
| sshr_h | external_abc_lut | T | 177 | 172 | 5 | 0 | -45.61% |
| sshr_h | external_abc_lut | CNOT | 177 | 172 | 5 | 0 | -73.65% |
| sshr_h | external_abc_lut | depth | 177 | 172 | 5 | 0 | -66.71% |
| sshr_h | external_abc_lut | peak_ancilla | 177 | 176 | 0 | 1 | -70.45% |
| sshr_h | external_abc_lut | score | 177 | 172 | 5 | 0 | -54.46% |
| sshr_h | external_abc_xag | T | 177 | 104 | 56 | 17 | -7.92% |
| sshr_h | external_abc_xag | CNOT | 177 | 174 | 3 | 0 | -46.19% |
| sshr_h | external_abc_xag | depth | 177 | 25 | 150 | 2 | +82.49% |
| sshr_h | external_abc_xag | peak_ancilla | 177 | 177 | 0 | 0 | -92.76% |
| sshr_h | external_abc_xag | score | 177 | 174 | 3 | 0 | -37.64% |
| sshr_h | external_bdd | T | 177 | 166 | 10 | 1 | -34.59% |
| sshr_h | external_bdd | CNOT | 177 | 177 | 0 | 0 | -68.31% |
| sshr_h | external_bdd | depth | 177 | 177 | 0 | 0 | -65.03% |
| sshr_h | external_bdd | peak_ancilla | 177 | 177 | 0 | 0 | -87.39% |
| sshr_h | external_bdd | score | 177 | 175 | 2 | 0 | -46.01% |
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
