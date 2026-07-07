# Traditional_Resource Analysis

Rows: 1770; usable: 1770; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_affine_nmcts | 177 | -70.69% | -88.89% | +0.00% |
| and_cube_beam | 177 | +523.54% | -85.19% | +64000.00% |
| and_direct_anf | 177 | -40.45% | -50.00% | +0.00% |
| and_esop_milp | 177 | -56.79% | -85.19% | +0.00% |
| and_fprm_polarity_archive | 177 | -69.54% | -88.89% | +0.00% |
| and_mcts_factor | 177 | -58.65% | -72.79% | +0.00% |
| and_pareto_resource_nmcts | 177 | -72.25% | -88.89% | +0.00% |
| and_resource_nmcts | 177 | -71.33% | -88.89% | +0.00% |
| sshr_h | 177 | +70.71% | -82.46% | +9600.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|
| and_affine_nmcts | 171 | 6 | -44.13% |
| and_cube_beam | 122 | 55 | +4.87% |
| and_direct_anf | 39 | 138 | +25.31% |
| and_esop_milp | 120 | 57 | -11.42% |
| and_fprm_polarity_archive | 167 | 10 | -41.58% |
| and_mcts_factor | 132 | 45 | -16.30% |
| and_pareto_resource_nmcts | 173 | 4 | -47.93% |
| and_resource_nmcts | 173 | 4 | -45.61% |
| sshr_h | 0 | 177 | +0.00% |

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_affine_nmcts | direct_anf | T | 172 | 0 | 5 | -70.69% |
| and_affine_nmcts | direct_anf | CNOT | 163 | 10 | 4 | -29.39% |
| and_affine_nmcts | direct_anf | depth | 160 | 12 | 5 | -25.27% |
| and_affine_nmcts | direct_anf | peak_ancilla | 0 | 97 | 80 | +46.61% |
| and_affine_nmcts | direct_anf | score | 172 | 1 | 4 | -66.26% |
| and_affine_nmcts | and_direct_anf | T | 172 | 0 | 5 | -51.96% |
| and_affine_nmcts | and_direct_anf | CNOT | 172 | 0 | 5 | -40.53% |
| and_affine_nmcts | and_direct_anf | depth | 172 | 0 | 5 | -36.90% |
| and_affine_nmcts | and_direct_anf | peak_ancilla | 52 | 0 | 125 | -8.99% |
| and_affine_nmcts | and_direct_anf | score | 172 | 0 | 5 | -48.56% |
| and_affine_nmcts | and_mcts_factor | T | 158 | 0 | 19 | -29.22% |
| and_affine_nmcts | and_mcts_factor | CNOT | 159 | 1 | 17 | -26.53% |
| and_affine_nmcts | and_mcts_factor | depth | 157 | 3 | 17 | -22.21% |
| and_affine_nmcts | and_mcts_factor | peak_ancilla | 1 | 11 | 165 | +2.82% |
| and_affine_nmcts | and_mcts_factor | score | 160 | 0 | 17 | -26.69% |
| and_affine_nmcts | and_cube_beam | T | 171 | 3 | 3 | -34.61% |
| and_affine_nmcts | and_cube_beam | CNOT | 137 | 31 | 9 | -16.22% |
| and_affine_nmcts | and_cube_beam | depth | 170 | 6 | 1 | -26.13% |
| and_affine_nmcts | and_cube_beam | peak_ancilla | 107 | 0 | 70 | -22.98% |
| and_affine_nmcts | and_cube_beam | score | 171 | 5 | 1 | -32.16% |
| and_affine_nmcts | and_esop_milp | T | 162 | 1 | 14 | -29.45% |
| and_affine_nmcts | and_esop_milp | CNOT | 111 | 54 | 12 | -10.26% |
| and_affine_nmcts | and_esop_milp | depth | 151 | 19 | 7 | -18.94% |
| and_affine_nmcts | and_esop_milp | peak_ancilla | 73 | 0 | 104 | -13.28% |
| and_affine_nmcts | and_esop_milp | score | 164 | 8 | 5 | -26.88% |
| and_affine_nmcts | sshr_h | T | 171 | 1 | 5 | -44.13% |
| and_affine_nmcts | sshr_h | CNOT | 39 | 133 | 5 | +29.17% |
| and_affine_nmcts | sshr_h | depth | 75 | 96 | 6 | +5.95% |
| and_affine_nmcts | sshr_h | peak_ancilla | 3 | 95 | 79 | +43.79% |
| and_affine_nmcts | sshr_h | score | 171 | 6 | 0 | -37.42% |
| and_resource_nmcts | direct_anf | T | 172 | 0 | 5 | -71.33% |
| and_resource_nmcts | direct_anf | CNOT | 164 | 9 | 4 | -31.46% |
| and_resource_nmcts | direct_anf | depth | 162 | 10 | 5 | -27.21% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 101 | 76 | +49.72% |
| and_resource_nmcts | direct_anf | score | 172 | 1 | 4 | -66.90% |
| and_resource_nmcts | and_direct_anf | T | 172 | 0 | 5 | -53.13% |
| and_resource_nmcts | and_direct_anf | CNOT | 172 | 0 | 5 | -42.14% |
| and_resource_nmcts | and_direct_anf | depth | 172 | 0 | 5 | -38.37% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 49 | 4 | 124 | -7.02% |
| and_resource_nmcts | and_direct_anf | score | 172 | 0 | 5 | -49.63% |
| and_resource_nmcts | and_affine_nmcts | T | 33 | 0 | 144 | -2.12% |
| and_resource_nmcts | and_affine_nmcts | CNOT | 42 | 0 | 135 | -2.46% |
| and_resource_nmcts | and_affine_nmcts | depth | 42 | 2 | 133 | -2.24% |
| and_resource_nmcts | and_affine_nmcts | peak_ancilla | 1 | 8 | 168 | +2.31% |
| and_resource_nmcts | and_affine_nmcts | score | 44 | 0 | 133 | -1.91% |
| and_resource_nmcts | and_mcts_factor | T | 167 | 0 | 10 | -31.07% |
| and_resource_nmcts | and_mcts_factor | CNOT | 169 | 0 | 8 | -28.66% |
| and_resource_nmcts | and_mcts_factor | depth | 165 | 4 | 8 | -24.17% |
| and_resource_nmcts | and_mcts_factor | peak_ancilla | 1 | 18 | 158 | +5.08% |
| and_resource_nmcts | and_mcts_factor | score | 169 | 0 | 8 | -28.36% |
| and_resource_nmcts | and_cube_beam | T | 174 | 0 | 3 | -36.22% |
| and_resource_nmcts | and_cube_beam | CNOT | 146 | 20 | 11 | -18.55% |
| and_resource_nmcts | and_cube_beam | depth | 173 | 1 | 3 | -27.95% |
| and_resource_nmcts | and_cube_beam | peak_ancilla | 106 | 1 | 70 | -21.52% |
| and_resource_nmcts | and_cube_beam | score | 174 | 0 | 3 | -33.64% |
| and_resource_nmcts | and_esop_milp | T | 163 | 0 | 14 | -30.71% |
| and_resource_nmcts | and_esop_milp | CNOT | 113 | 51 | 13 | -12.09% |
| and_resource_nmcts | and_esop_milp | depth | 153 | 15 | 9 | -20.36% |
| and_resource_nmcts | and_esop_milp | peak_ancilla | 71 | 1 | 105 | -11.77% |
| and_resource_nmcts | and_esop_milp | score | 165 | 5 | 7 | -28.03% |
| and_resource_nmcts | sshr_h | T | 173 | 1 | 3 | -45.61% |
| and_resource_nmcts | sshr_h | CNOT | 41 | 131 | 5 | +25.03% |
| and_resource_nmcts | sshr_h | depth | 77 | 94 | 6 | +2.90% |
| and_resource_nmcts | sshr_h | peak_ancilla | 3 | 101 | 73 | +46.33% |
| and_resource_nmcts | sshr_h | score | 173 | 4 | 0 | -38.87% |
| and_pareto_resource_nmcts | and_fprm_polarity_archive | T | 79 | 0 | 98 | -8.13% |
| and_pareto_resource_nmcts | and_fprm_polarity_archive | CNOT | 98 | 13 | 66 | -6.11% |
| and_pareto_resource_nmcts | and_fprm_polarity_archive | depth | 90 | 19 | 68 | -5.33% |
| and_pareto_resource_nmcts | and_fprm_polarity_archive | peak_ancilla | 25 | 12 | 140 | -3.77% |
| and_pareto_resource_nmcts | and_fprm_polarity_archive | score | 115 | 0 | 62 | -7.77% |
| and_pareto_resource_nmcts | direct_anf | T | 172 | 0 | 5 | -72.25% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 164 | 9 | 4 | -34.20% |
| and_pareto_resource_nmcts | direct_anf | depth | 163 | 9 | 5 | -29.74% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 103 | 74 | +57.06% |
| and_pareto_resource_nmcts | direct_anf | score | 172 | 1 | 4 | -67.80% |
| and_pareto_resource_nmcts | and_direct_anf | T | 172 | 0 | 5 | -54.84% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 172 | 0 | 5 | -44.31% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 172 | 0 | 5 | -40.37% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 45 | 18 | 114 | -2.64% |
| and_pareto_resource_nmcts | and_direct_anf | score | 172 | 0 | 5 | -51.19% |
| and_pareto_resource_nmcts | and_resource_nmcts | T | 53 | 0 | 124 | -3.72% |
| and_pareto_resource_nmcts | and_resource_nmcts | CNOT | 66 | 0 | 111 | -3.90% |
| and_pareto_resource_nmcts | and_resource_nmcts | depth | 65 | 2 | 110 | -3.48% |
| and_pareto_resource_nmcts | and_resource_nmcts | peak_ancilla | 2 | 20 | 155 | +4.80% |
| and_pareto_resource_nmcts | and_resource_nmcts | score | 68 | 0 | 109 | -3.26% |
| and_pareto_resource_nmcts | and_affine_nmcts | T | 59 | 0 | 118 | -5.63% |
| and_pareto_resource_nmcts | and_affine_nmcts | CNOT | 76 | 0 | 101 | -6.15% |
| and_pareto_resource_nmcts | and_affine_nmcts | depth | 74 | 4 | 99 | -5.53% |
| and_pareto_resource_nmcts | and_affine_nmcts | peak_ancilla | 3 | 26 | 148 | +7.30% |
| and_pareto_resource_nmcts | and_affine_nmcts | score | 79 | 0 | 98 | -4.99% |
| and_pareto_resource_nmcts | and_mcts_factor | T | 168 | 0 | 9 | -33.93% |
| and_pareto_resource_nmcts | and_mcts_factor | CNOT | 169 | 0 | 8 | -31.64% |
| and_pareto_resource_nmcts | and_mcts_factor | depth | 166 | 4 | 7 | -26.93% |
| and_pareto_resource_nmcts | and_mcts_factor | peak_ancilla | 1 | 30 | 146 | +10.26% |
| and_pareto_resource_nmcts | and_mcts_factor | score | 170 | 0 | 7 | -30.91% |
| and_pareto_resource_nmcts | and_cube_beam | T | 174 | 0 | 3 | -38.95% |
| and_pareto_resource_nmcts | and_cube_beam | CNOT | 163 | 5 | 9 | -22.17% |
| and_pareto_resource_nmcts | and_cube_beam | depth | 174 | 0 | 3 | -30.76% |
| and_pareto_resource_nmcts | and_cube_beam | peak_ancilla | 90 | 4 | 83 | -18.22% |
| and_pareto_resource_nmcts | and_cube_beam | score | 174 | 0 | 3 | -36.09% |
| and_pareto_resource_nmcts | and_esop_milp | T | 166 | 0 | 11 | -32.77% |
| and_pareto_resource_nmcts | and_esop_milp | CNOT | 123 | 41 | 13 | -14.97% |
| and_pareto_resource_nmcts | and_esop_milp | depth | 156 | 12 | 9 | -22.54% |
| and_pareto_resource_nmcts | and_esop_milp | peak_ancilla | 58 | 7 | 112 | -8.00% |
| and_pareto_resource_nmcts | and_esop_milp | score | 167 | 3 | 7 | -29.84% |
| and_pareto_resource_nmcts | sshr_h | T | 173 | 0 | 4 | -47.93% |
| and_pareto_resource_nmcts | sshr_h | CNOT | 43 | 128 | 6 | +18.99% |
| and_pareto_resource_nmcts | sshr_h | depth | 87 | 84 | 6 | -1.35% |
| and_pareto_resource_nmcts | sshr_h | peak_ancilla | 3 | 103 | 71 | +53.67% |
| and_pareto_resource_nmcts | sshr_h | score | 173 | 4 | 0 | -41.06% |
| and_cube_beam | and_esop_milp | T | 35 | 101 | 41 | +589.39% |
| and_cube_beam | and_esop_milp | CNOT | 40 | 109 | 28 | +177.48% |
| and_cube_beam | and_esop_milp | depth | 37 | 118 | 22 | +213.37% |
| and_cube_beam | and_esop_milp | peak_ancilla | 1 | 36 | 140 | +17.75% |
| and_cube_beam | and_esop_milp | score | 37 | 118 | 22 | +656.74% |
| and_cube_beam | sshr_h | T | 122 | 46 | 9 | +4.87% |
| and_cube_beam | sshr_h | CNOT | 15 | 162 | 0 | +68.95% |
| and_cube_beam | sshr_h | depth | 19 | 155 | 3 | +59.28% |
| and_cube_beam | sshr_h | peak_ancilla | 1 | 151 | 25 | +91.81% |
| and_cube_beam | sshr_h | score | 119 | 58 | 0 | +11.72% |
| and_esop_milp | sshr_h | T | 120 | 46 | 11 | -11.42% |
| and_esop_milp | sshr_h | CNOT | 33 | 140 | 4 | +60.92% |
| and_esop_milp | sshr_h | depth | 47 | 127 | 3 | +46.96% |
| and_esop_milp | sshr_h | peak_ancilla | 3 | 135 | 39 | +68.64% |
| and_esop_milp | sshr_h | score | 117 | 60 | 0 | -5.17% |

## Largest and-affine-nmcts gains vs direct ANF

| function | n | direct T | and_affine_nmcts T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_62 | 5 | 264 | 36 | -86.36% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| truth_n5_30 | 5 | 220 | 32 | -85.45% |
| truth_n5_13 | 5 | 192 | 28 | -85.42% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_35 | 5 | 236 | 40 | -83.05% |
| truth_n5_39 | 5 | 232 | 40 | -82.76% |
| truth_n6_6 | 6 | 548 | 96 | -82.48% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_62 | 5 | 264 | 36 | -86.36% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| truth_n5_30 | 5 | 220 | 32 | -85.45% |
| truth_n5_13 | 5 | 192 | 28 | -85.42% |
| threshold3_n6 | 6 | 680 | 104 | -84.71% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_35 | 5 | 236 | 40 | -83.05% |
| truth_n5_39 | 5 | 232 | 40 | -82.76% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_44 | 5 | 228 | 28 | -87.72% |
| threshold3_n6 | 6 | 680 | 92 | -86.47% |
| truth_n5_62 | 5 | 264 | 36 | -86.36% |
| truth_n5_39 | 5 | 232 | 32 | -86.21% |
| truth_n6_27 | 6 | 532 | 76 | -85.71% |
| truth_n5_30 | 5 | 220 | 32 | -85.45% |
| truth_n5_13 | 5 | 192 | 28 | -85.42% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |

## Largest and-fprm-polarity-archive gains vs direct ANF

| function | n | direct T | and_fprm_polarity_archive T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| truth_n5_44 | 5 | 228 | 28 | -87.72% |
| threshold3_n6 | 6 | 680 | 92 | -86.47% |
| truth_n5_39 | 5 | 232 | 32 | -86.21% |
| truth_n6_27 | 6 | 532 | 76 | -85.71% |
| truth_n5_30 | 5 | 220 | 32 | -85.45% |
| truth_n5_62 | 5 | 264 | 44 | -83.33% |
| truth_n5_8 | 5 | 244 | 44 | -81.97% |
| truth_n5_45 | 5 | 260 | 48 | -81.54% |
| truth_n5_48 | 5 | 256 | 48 | -81.25% |
| truth_n6_10 | 6 | 576 | 108 | -81.25% |
| truth_n6_11 | 6 | 616 | 116 | -81.17% |

## Largest and-cube-beam gains vs direct ANF

| function | n | direct T | and_cube_beam T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 16 | -85.19% |
| truth_n5_30 | 5 | 220 | 44 | -80.00% |
| truth_n5_62 | 5 | 264 | 56 | -78.79% |
| truth_n5_39 | 5 | 232 | 52 | -77.59% |
| truth_n5_45 | 5 | 260 | 60 | -76.92% |
| truth_n6_27 | 6 | 532 | 124 | -76.69% |
| truth_n5_48 | 5 | 256 | 60 | -76.56% |
| truth_n4_31 | 4 | 84 | 20 | -76.19% |
| truth_n4_24 | 4 | 100 | 24 | -76.00% |
| truth_n6_11 | 6 | 616 | 152 | -75.32% |
| truth_n6_17 | 6 | 500 | 124 | -75.20% |
| truth_n6_19 | 6 | 508 | 128 | -74.80% |

## Largest and-esop-milp gains vs direct ANF

| function | n | direct T | and_esop_milp T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 16 | -85.19% |
| truth_n5_44 | 5 | 228 | 36 | -84.21% |
| truth_n5_30 | 5 | 220 | 40 | -81.82% |
| truth_n5_62 | 5 | 264 | 52 | -80.30% |
| truth_n5_45 | 5 | 260 | 52 | -80.00% |
| truth_n5_16 | 5 | 200 | 44 | -78.00% |
| truth_n5_39 | 5 | 232 | 52 | -77.59% |
| truth_n5_8 | 5 | 244 | 56 | -77.05% |
| truth_n5_27 | 5 | 208 | 48 | -76.92% |
| truth_n5_6 | 5 | 188 | 44 | -76.60% |
| truth_n5_48 | 5 | 256 | 60 | -76.56% |
| truth_n5_57 | 5 | 220 | 52 | -76.36% |

## and_affine_nmcts vs SSHR-H

| function | n | SSHR-H T | and_affine_nmcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n4_22 | 4 | 48 | 12 | -75.00% | 2 |
| truth_n4_18 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_34 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_49 | 4 | 28 | 8 | -71.43% | 1 |
| truth_n5_25 | 5 | 112 | 32 | -71.43% | 3 |
| truth_n5_21 | 5 | 88 | 28 | -68.18% | 2 |
| truth_n5_5 | 5 | 124 | 40 | -67.74% | 2 |
| truth_n5_37 | 5 | 56 | 20 | -64.29% | 1 |
| truth_n4_14 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n5_13 | 5 | 76 | 28 | -63.16% | 2 |
| truth_n5_62 | 5 | 96 | 36 | -62.50% | 2 |
| truth_n5_19 | 5 | 84 | 32 | -61.90% | 2 |
| truth_n5_40 | 5 | 92 | 36 | -60.87% | 2 |
| majority_n5 | 5 | 80 | 32 | -60.00% | 2 |
| truth_n5_22 | 5 | 108 | 44 | -59.26% | 2 |
| truth_n5_59 | 5 | 108 | 44 | -59.26% | 2 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| truth_n5_1 | 5 | 96 | 40 | -58.33% | 2 |
| truth_n6_6 | 6 | 228 | 96 | -57.89% | 3 |
| truth_n5_53 | 5 | 104 | 44 | -57.69% | 2 |
| truth_n4_10 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_41 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_48 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n5_41 | 5 | 84 | 36 | -57.14% | 2 |
| truth_n5_24 | 5 | 92 | 40 | -56.52% | 2 |
| truth_n5_38 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n5_60 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n4_24 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_52 | 4 | 36 | 16 | -55.56% | 1 |
| truth_n4_60 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_62 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_7 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n5_36 | 5 | 108 | 48 | -55.56% | 2 |
| truth_n5_17 | 5 | 80 | 36 | -55.00% | 2 |
| truth_n4_13 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_46 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_54 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_59 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n5_12 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_32 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_7 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_50 | 5 | 96 | 44 | -54.17% | 2 |
| truth_n5_26 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n5_48 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n5_16 | 5 | 76 | 36 | -52.63% | 3 |
| truth_n5_29 | 5 | 84 | 40 | -52.38% | 2 |
| truth_n5_51 | 5 | 100 | 48 | -52.00% | 2 |
| truth_n4_11 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_26 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_27 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_28 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_30 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_31 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_36 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_37 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_38 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_39 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_42 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_45 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_47 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_5 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_51 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_55 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_56 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_57 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_63 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n5_15 | 5 | 56 | 28 | -50.00% | 2 |
| truth_n5_33 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_35 | 5 | 80 | 40 | -50.00% | 2 |
| truth_n5_42 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_54 | 5 | 72 | 36 | -50.00% | 2 |
| truth_n5_61 | 5 | 64 | 32 | -50.00% | 2 |
| truth_n5_8 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n6_7 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n5_11 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_43 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_57 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_10 | 5 | 76 | 40 | -47.37% | 2 |
| truth_n5_30 | 5 | 60 | 32 | -46.67% | 2 |
| truth_n6_10 | 6 | 240 | 128 | -46.67% | 3 |
| truth_n5_2 | 5 | 104 | 56 | -46.15% | 2 |
| majority_n4 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_46 | 5 | 88 | 48 | -45.45% | 2 |
| truth_n5_20 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n5_28 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n5_39 | 5 | 72 | 40 | -44.44% | 2 |
| truth_n6_4 | 6 | 244 | 136 | -44.26% | 3 |
| truth_n6_19 | 6 | 200 | 112 | -44.00% | 3 |
| truth_n5_31 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n5_6 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n5_23 | 5 | 92 | 52 | -43.48% | 2 |
| truth_n4_17 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n5_47 | 5 | 84 | 48 | -42.86% | 2 |
| truth_n5_56 | 5 | 76 | 44 | -42.11% | 2 |
| majority_n6 | 6 | 184 | 108 | -41.30% | 2 |
| mux_2_4 | 6 | 60 | 36 | -40.00% | 1 |
| truth_n4_15 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_16 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_19 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_2 | 4 | 40 | 24 | -40.00% | 2 |
| truth_n4_23 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_33 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_44 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_50 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n5_3 | 5 | 80 | 48 | -40.00% | 2 |
| truth_n5_63 | 5 | 80 | 48 | -40.00% | 2 |
| truth_n6_23 | 6 | 212 | 128 | -39.62% | 3 |
| truth_n6_26 | 6 | 212 | 128 | -39.62% | 3 |
| truth_n6_5 | 6 | 204 | 124 | -39.22% | 3 |
| truth_n5_55 | 5 | 72 | 44 | -38.89% | 2 |
| truth_n5_9 | 5 | 52 | 32 | -38.46% | 2 |
| truth_n6_17 | 6 | 188 | 116 | -38.30% | 3 |
| threshold2_n5 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n4_35 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_53 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_0 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_34 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_49 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n6_30 | 6 | 192 | 120 | -37.50% | 3 |
| truth_n6_25 | 6 | 204 | 128 | -37.25% | 2 |
| truth_n5_14 | 5 | 76 | 48 | -36.84% | 2 |
| truth_n6_24 | 6 | 228 | 144 | -36.84% | 3 |
| truth_n6_11 | 6 | 232 | 148 | -36.21% | 3 |
| truth_n6_1 | 6 | 200 | 128 | -36.00% | 2 |
| truth_n6_9 | 6 | 200 | 128 | -36.00% | 3 |
| truth_n6_12 | 6 | 184 | 120 | -34.78% | 2 |
| truth_n6_16 | 6 | 196 | 128 | -34.69% | 3 |
| truth_n6_31 | 6 | 196 | 128 | -34.69% | 2 |
| truth_n6_0 | 6 | 188 | 124 | -34.04% | 3 |
| truth_n6_3 | 6 | 212 | 140 | -33.96% | 3 |
| truth_n6_22 | 6 | 224 | 148 | -33.93% | 4 |
| adder_carry_w2 | 4 | 24 | 16 | -33.33% | 1 |
| threshold2_n4 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_3 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_4 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_43 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_6 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n5_27 | 5 | 72 | 48 | -33.33% | 2 |
| truth_n6_15 | 6 | 192 | 128 | -33.33% | 3 |
| truth_n6_2 | 6 | 172 | 116 | -32.56% | 3 |
| truth_n5_18 | 5 | 52 | 36 | -30.77% | 2 |
| truth_n6_28 | 6 | 156 | 108 | -30.77% | 3 |
| truth_n6_20 | 6 | 184 | 128 | -30.43% | 3 |
| truth_n6_8 | 6 | 176 | 124 | -29.55% | 3 |
| truth_n5_45 | 5 | 68 | 48 | -29.41% | 2 |
| truth_n6_14 | 6 | 168 | 120 | -28.57% | 3 |
| threshold3_n6 | 6 | 184 | 132 | -28.26% | 2 |
| truth_n6_29 | 6 | 156 | 112 | -28.21% | 3 |
| truth_n5_52 | 5 | 60 | 44 | -26.67% | 2 |
| truth_n4_61 | 4 | 16 | 12 | -25.00% | 1 |
| truth_n6_21 | 6 | 200 | 152 | -24.00% | 3 |
| truth_n6_13 | 6 | 188 | 144 | -23.40% | 3 |
| truth_n4_0 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_12 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_21 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_29 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_32 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_40 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_58 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_8 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n5_44 | 5 | 40 | 32 | -20.00% | 2 |
| truth_n5_4 | 5 | 64 | 52 | -18.75% | 2 |
| truth_n6_18 | 6 | 156 | 128 | -17.95% | 3 |
| truth_n6_27 | 6 | 156 | 128 | -17.95% | 3 |
| adder_carry_w3 | 6 | 48 | 48 | +0.00% | 2 |
| majority_n3 | 3 | 4 | 4 | +0.00% | 0 |
| threshold2_n3 | 3 | 4 | 4 | +0.00% | 0 |
| truth_n4_1 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_9 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n5_58 | 5 | 24 | 28 | +16.67% | 1 |

## and_resource_nmcts vs SSHR-H

| function | n | SSHR-H T | and_resource_nmcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n4_22 | 4 | 48 | 12 | -75.00% | 2 |
| truth_n4_18 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_34 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_49 | 4 | 28 | 8 | -71.43% | 1 |
| truth_n5_25 | 5 | 112 | 32 | -71.43% | 3 |
| truth_n5_21 | 5 | 88 | 28 | -68.18% | 2 |
| truth_n5_5 | 5 | 124 | 40 | -67.74% | 2 |
| truth_n5_37 | 5 | 56 | 20 | -64.29% | 1 |
| truth_n4_14 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n4_46 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n5_13 | 5 | 76 | 28 | -63.16% | 2 |
| truth_n5_62 | 5 | 96 | 36 | -62.50% | 2 |
| truth_n5_19 | 5 | 84 | 32 | -61.90% | 2 |
| truth_n5_40 | 5 | 92 | 36 | -60.87% | 2 |
| majority_n5 | 5 | 80 | 32 | -60.00% | 2 |
| truth_n5_22 | 5 | 108 | 44 | -59.26% | 2 |
| truth_n5_59 | 5 | 108 | 44 | -59.26% | 2 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| truth_n5_1 | 5 | 96 | 40 | -58.33% | 2 |
| truth_n6_6 | 6 | 228 | 96 | -57.89% | 3 |
| truth_n5_53 | 5 | 104 | 44 | -57.69% | 2 |
| truth_n4_10 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_41 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_48 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n5_41 | 5 | 84 | 36 | -57.14% | 2 |
| truth_n5_24 | 5 | 92 | 40 | -56.52% | 2 |
| truth_n5_38 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n5_60 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n4_24 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_52 | 4 | 36 | 16 | -55.56% | 1 |
| truth_n4_60 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_62 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_7 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n5_36 | 5 | 108 | 48 | -55.56% | 2 |
| truth_n5_17 | 5 | 80 | 36 | -55.00% | 2 |
| truth_n4_13 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_54 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_59 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n5_12 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_32 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_7 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_50 | 5 | 96 | 44 | -54.17% | 2 |
| truth_n5_26 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n5_48 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n5_10 | 5 | 76 | 36 | -52.63% | 2 |
| truth_n5_16 | 5 | 76 | 36 | -52.63% | 3 |
| truth_n5_29 | 5 | 84 | 40 | -52.38% | 2 |
| truth_n5_51 | 5 | 100 | 48 | -52.00% | 2 |
| truth_n6_4 | 6 | 244 | 120 | -50.82% | 3 |
| adder_carry_w2 | 4 | 24 | 12 | -50.00% | 2 |
| truth_n4_11 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_2 | 4 | 40 | 20 | -50.00% | 2 |
| truth_n4_26 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_27 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_28 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_30 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_31 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_36 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_37 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_38 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_39 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_42 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_45 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_47 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_5 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_51 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_55 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_56 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_57 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_63 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n5_15 | 5 | 56 | 28 | -50.00% | 2 |
| truth_n5_33 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_35 | 5 | 80 | 40 | -50.00% | 2 |
| truth_n5_42 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_54 | 5 | 72 | 36 | -50.00% | 2 |
| truth_n5_61 | 5 | 64 | 32 | -50.00% | 2 |
| truth_n5_8 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n6_7 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n6_10 | 6 | 240 | 124 | -48.33% | 3 |
| truth_n5_23 | 5 | 92 | 48 | -47.83% | 2 |
| truth_n5_11 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_43 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_57 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n6_23 | 6 | 212 | 112 | -47.17% | 3 |
| truth_n6_25 | 6 | 204 | 108 | -47.06% | 3 |
| mux_2_4 | 6 | 60 | 32 | -46.67% | 1 |
| truth_n5_30 | 5 | 60 | 32 | -46.67% | 2 |
| truth_n5_2 | 5 | 104 | 56 | -46.15% | 2 |
| majority_n4 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_46 | 5 | 88 | 48 | -45.45% | 2 |
| truth_n6_3 | 6 | 212 | 116 | -45.28% | 3 |
| truth_n5_20 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n5_28 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n6_17 | 6 | 188 | 104 | -44.68% | 3 |
| truth_n5_39 | 5 | 72 | 40 | -44.44% | 2 |
| truth_n6_19 | 6 | 200 | 112 | -44.00% | 3 |
| truth_n5_31 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n5_6 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n6_30 | 6 | 192 | 108 | -43.75% | 4 |
| majority_n6 | 6 | 184 | 104 | -43.48% | 3 |
| threshold3_n6 | 6 | 184 | 104 | -43.48% | 3 |
| truth_n6_26 | 6 | 212 | 120 | -43.40% | 3 |
| truth_n4_17 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n5_47 | 5 | 84 | 48 | -42.86% | 2 |
| truth_n5_56 | 5 | 76 | 44 | -42.11% | 2 |
| truth_n6_24 | 6 | 228 | 132 | -42.11% | 3 |
| truth_n6_11 | 6 | 232 | 136 | -41.38% | 3 |
| truth_n6_14 | 6 | 168 | 100 | -40.48% | 3 |
| truth_n4_15 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_16 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_19 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_23 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_33 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_44 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_50 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n5_3 | 5 | 80 | 48 | -40.00% | 2 |
| truth_n5_63 | 5 | 80 | 48 | -40.00% | 2 |
| truth_n6_5 | 6 | 204 | 124 | -39.22% | 3 |
| truth_n6_12 | 6 | 184 | 112 | -39.13% | 3 |
| truth_n5_55 | 5 | 72 | 44 | -38.89% | 2 |
| truth_n6_16 | 6 | 196 | 120 | -38.78% | 3 |
| truth_n5_9 | 5 | 52 | 32 | -38.46% | 2 |
| threshold2_n5 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n4_35 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_53 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_0 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_34 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_49 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n6_15 | 6 | 192 | 120 | -37.50% | 3 |
| truth_n6_22 | 6 | 224 | 140 | -37.50% | 3 |
| truth_n5_14 | 5 | 76 | 48 | -36.84% | 2 |
| truth_n6_31 | 6 | 196 | 124 | -36.73% | 3 |
| truth_n6_0 | 6 | 188 | 120 | -36.17% | 3 |
| truth_n6_1 | 6 | 200 | 128 | -36.00% | 2 |
| truth_n6_9 | 6 | 200 | 128 | -36.00% | 3 |
| truth_n6_13 | 6 | 188 | 124 | -34.04% | 3 |
| adder_carry_w3 | 6 | 48 | 32 | -33.33% | 3 |
| threshold2_n4 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_3 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_4 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_43 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_6 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n5_27 | 5 | 72 | 48 | -33.33% | 2 |
| truth_n6_20 | 6 | 184 | 124 | -32.61% | 3 |
| truth_n6_2 | 6 | 172 | 116 | -32.56% | 3 |
| truth_n6_21 | 6 | 200 | 136 | -32.00% | 3 |
| truth_n5_18 | 5 | 52 | 36 | -30.77% | 2 |
| truth_n6_18 | 6 | 156 | 108 | -30.77% | 3 |
| truth_n6_28 | 6 | 156 | 108 | -30.77% | 3 |
| truth_n6_29 | 6 | 156 | 108 | -30.77% | 3 |
| truth_n6_8 | 6 | 176 | 124 | -29.55% | 3 |
| truth_n5_45 | 5 | 68 | 48 | -29.41% | 2 |
| truth_n5_52 | 5 | 60 | 44 | -26.67% | 2 |
| truth_n6_27 | 6 | 156 | 116 | -25.64% | 3 |
| truth_n4_61 | 4 | 16 | 12 | -25.00% | 1 |
| truth_n4_0 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_1 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_12 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_21 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_29 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_32 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_40 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_58 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_8 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n5_44 | 5 | 40 | 32 | -20.00% | 2 |
| truth_n5_4 | 5 | 64 | 52 | -18.75% | 2 |
| majority_n3 | 3 | 4 | 4 | +0.00% | 0 |
| threshold2_n3 | 3 | 4 | 4 | +0.00% | 0 |
| truth_n4_9 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n5_58 | 5 | 24 | 28 | +16.67% | 1 |

## and_pareto_resource_nmcts vs SSHR-H

| function | n | SSHR-H T | and_pareto_resource_nmcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n4_22 | 4 | 48 | 12 | -75.00% | 2 |
| truth_n4_18 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_34 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n4_49 | 4 | 28 | 8 | -71.43% | 1 |
| truth_n5_25 | 5 | 112 | 32 | -71.43% | 2 |
| truth_n5_21 | 5 | 88 | 28 | -68.18% | 2 |
| truth_n5_5 | 5 | 124 | 40 | -67.74% | 2 |
| truth_n5_37 | 5 | 56 | 20 | -64.29% | 1 |
| truth_n4_14 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n4_46 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n5_13 | 5 | 76 | 28 | -63.16% | 2 |
| truth_n5_22 | 5 | 108 | 40 | -62.96% | 2 |
| truth_n5_62 | 5 | 96 | 36 | -62.50% | 2 |
| truth_n5_19 | 5 | 84 | 32 | -61.90% | 2 |
| truth_n5_53 | 5 | 104 | 40 | -61.54% | 2 |
| truth_n5_40 | 5 | 92 | 36 | -60.87% | 2 |
| majority_n5 | 5 | 80 | 32 | -60.00% | 2 |
| truth_n5_38 | 5 | 100 | 40 | -60.00% | 2 |
| truth_n5_36 | 5 | 108 | 44 | -59.26% | 2 |
| truth_n5_59 | 5 | 108 | 44 | -59.26% | 2 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| truth_n5_1 | 5 | 96 | 40 | -58.33% | 2 |
| truth_n6_6 | 6 | 228 | 96 | -57.89% | 3 |
| truth_n4_10 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_41 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_48 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n5_41 | 5 | 84 | 36 | -57.14% | 2 |
| truth_n6_25 | 6 | 204 | 88 | -56.86% | 4 |
| truth_n5_24 | 5 | 92 | 40 | -56.52% | 2 |
| truth_n5_60 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n4_24 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_52 | 4 | 36 | 16 | -55.56% | 1 |
| truth_n4_60 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_62 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_7 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n5_39 | 5 | 72 | 32 | -55.56% | 3 |
| truth_n5_17 | 5 | 80 | 36 | -55.00% | 2 |
| truth_n6_10 | 6 | 240 | 108 | -55.00% | 3 |
| truth_n6_7 | 6 | 212 | 96 | -54.72% | 4 |
| truth_n4_13 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_54 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_59 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n5_12 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_32 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_42 | 5 | 88 | 40 | -54.55% | 3 |
| truth_n5_7 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_50 | 5 | 96 | 44 | -54.17% | 2 |
| truth_n6_4 | 6 | 244 | 112 | -54.10% | 3 |
| truth_n5_2 | 5 | 104 | 48 | -53.85% | 3 |
| truth_n5_26 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n5_48 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n6_23 | 6 | 212 | 100 | -52.83% | 3 |
| truth_n5_10 | 5 | 76 | 36 | -52.63% | 2 |
| truth_n5_16 | 5 | 76 | 36 | -52.63% | 3 |
| truth_n5_11 | 5 | 84 | 40 | -52.38% | 2 |
| truth_n5_29 | 5 | 84 | 40 | -52.38% | 2 |
| truth_n6_14 | 6 | 168 | 80 | -52.38% | 4 |
| truth_n5_23 | 5 | 92 | 44 | -52.17% | 2 |
| truth_n5_51 | 5 | 100 | 48 | -52.00% | 2 |
| truth_n6_11 | 6 | 232 | 112 | -51.72% | 4 |
| truth_n6_27 | 6 | 156 | 76 | -51.28% | 3 |
| truth_n6_17 | 6 | 188 | 92 | -51.06% | 4 |
| truth_n6_16 | 6 | 196 | 96 | -51.02% | 4 |
| adder_carry_w2 | 4 | 24 | 12 | -50.00% | 2 |
| majority_n6 | 6 | 184 | 92 | -50.00% | 3 |
| threshold3_n6 | 6 | 184 | 92 | -50.00% | 3 |
| truth_n4_11 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_2 | 4 | 40 | 20 | -50.00% | 2 |
| truth_n4_26 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_27 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_28 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_30 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_31 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_36 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_37 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_38 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_39 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_42 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_45 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_47 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_5 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_51 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_55 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_56 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_57 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_63 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n5_15 | 5 | 56 | 28 | -50.00% | 2 |
| truth_n5_20 | 5 | 80 | 40 | -50.00% | 2 |
| truth_n5_33 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_35 | 5 | 80 | 40 | -50.00% | 2 |
| truth_n5_54 | 5 | 72 | 36 | -50.00% | 2 |
| truth_n5_61 | 5 | 64 | 32 | -50.00% | 2 |
| truth_n5_8 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n6_12 | 6 | 184 | 92 | -50.00% | 3 |
| truth_n6_24 | 6 | 228 | 116 | -49.12% | 3 |
| truth_n6_26 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n6_3 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n6_22 | 6 | 224 | 116 | -48.21% | 3 |
| truth_n6_19 | 6 | 200 | 104 | -48.00% | 3 |
| truth_n6_30 | 6 | 192 | 100 | -47.92% | 4 |
| truth_n5_43 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_57 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n6_5 | 6 | 204 | 108 | -47.06% | 3 |
| truth_n6_31 | 6 | 196 | 104 | -46.94% | 3 |
| truth_n6_0 | 6 | 188 | 100 | -46.81% | 4 |
| mux_2_4 | 6 | 60 | 32 | -46.67% | 1 |
| truth_n5_30 | 5 | 60 | 32 | -46.67% | 2 |
| truth_n6_18 | 6 | 156 | 84 | -46.15% | 3 |
| majority_n4 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_46 | 5 | 88 | 48 | -45.45% | 2 |
| truth_n5_28 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n5_3 | 5 | 80 | 44 | -45.00% | 3 |
| truth_n5_55 | 5 | 72 | 40 | -44.44% | 3 |
| truth_n6_9 | 6 | 200 | 112 | -44.00% | 2 |
| truth_n5_31 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n5_6 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n6_15 | 6 | 192 | 108 | -43.75% | 3 |
| truth_n6_28 | 6 | 156 | 88 | -43.59% | 3 |
| truth_n6_20 | 6 | 184 | 104 | -43.48% | 4 |
| truth_n4_17 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n5_47 | 5 | 84 | 48 | -42.86% | 2 |
| truth_n5_14 | 5 | 76 | 44 | -42.11% | 3 |
| truth_n5_56 | 5 | 76 | 44 | -42.11% | 2 |
| truth_n6_21 | 6 | 200 | 116 | -42.00% | 3 |
| adder_carry_w3 | 6 | 48 | 28 | -41.67% | 4 |
| truth_n6_13 | 6 | 188 | 112 | -40.43% | 3 |
| truth_n4_15 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_16 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_19 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_23 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_33 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_44 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n4_50 | 4 | 20 | 12 | -40.00% | 1 |
| truth_n5_63 | 5 | 80 | 48 | -40.00% | 2 |
| truth_n6_1 | 6 | 200 | 120 | -40.00% | 4 |
| truth_n5_27 | 5 | 72 | 44 | -38.89% | 2 |
| truth_n5_18 | 5 | 52 | 32 | -38.46% | 2 |
| truth_n5_9 | 5 | 52 | 32 | -38.46% | 2 |
| truth_n6_29 | 6 | 156 | 96 | -38.46% | 3 |
| threshold2_n5 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n4_35 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_53 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_0 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_34 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_49 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n6_8 | 6 | 176 | 112 | -36.36% | 4 |
| truth_n5_45 | 5 | 68 | 44 | -35.29% | 2 |
| truth_n6_2 | 6 | 172 | 112 | -34.88% | 4 |
| threshold2_n4 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_3 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_4 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_43 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_6 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n5_4 | 5 | 64 | 44 | -31.25% | 3 |
| truth_n5_44 | 5 | 40 | 28 | -30.00% | 2 |
| truth_n5_52 | 5 | 60 | 44 | -26.67% | 2 |
| truth_n4_61 | 4 | 16 | 12 | -25.00% | 1 |
| truth_n4_0 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_1 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_12 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_21 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_29 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_32 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_40 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_58 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_8 | 4 | 20 | 16 | -20.00% | 1 |
| majority_n3 | 3 | 4 | 4 | +0.00% | 0 |
| threshold2_n3 | 3 | 4 | 4 | +0.00% | 0 |
| truth_n4_9 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n5_58 | 5 | 24 | 24 | +0.00% | 2 |

## and_fprm_polarity_archive vs SSHR-H

| function | n | SSHR-H T | and_fprm_polarity_archive T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n4_34 | 4 | 44 | 12 | -72.73% | 2 |
| truth_n5_25 | 5 | 112 | 32 | -71.43% | 2 |
| truth_n5_5 | 5 | 124 | 40 | -67.74% | 3 |
| truth_n5_37 | 5 | 56 | 20 | -64.29% | 1 |
| truth_n4_14 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n4_46 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n5_22 | 5 | 108 | 40 | -62.96% | 2 |
| truth_n5_53 | 5 | 104 | 40 | -61.54% | 2 |
| truth_n5_40 | 5 | 92 | 36 | -60.87% | 2 |
| truth_n5_36 | 5 | 108 | 44 | -59.26% | 2 |
| truth_n5_59 | 5 | 108 | 44 | -59.26% | 2 |
| truth_n5_21 | 5 | 88 | 36 | -59.09% | 2 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| truth_n4_22 | 4 | 48 | 20 | -58.33% | 2 |
| truth_n4_48 | 4 | 28 | 12 | -57.14% | 2 |
| truth_n4_49 | 4 | 28 | 12 | -57.14% | 1 |
| truth_n5_19 | 5 | 84 | 36 | -57.14% | 2 |
| truth_n6_25 | 6 | 204 | 88 | -56.86% | 4 |
| truth_n5_38 | 5 | 100 | 44 | -56.00% | 3 |
| truth_n5_60 | 5 | 100 | 44 | -56.00% | 2 |
| truth_n4_52 | 4 | 36 | 16 | -55.56% | 1 |
| truth_n4_60 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n4_62 | 4 | 36 | 16 | -55.56% | 2 |
| truth_n5_39 | 5 | 72 | 32 | -55.56% | 3 |
| truth_n5_17 | 5 | 80 | 36 | -55.00% | 3 |
| truth_n6_10 | 6 | 240 | 108 | -55.00% | 3 |
| truth_n4_13 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_18 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_54 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n4_59 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n5_32 | 5 | 88 | 40 | -54.55% | 3 |
| truth_n5_7 | 5 | 88 | 40 | -54.55% | 2 |
| truth_n5_62 | 5 | 96 | 44 | -54.17% | 2 |
| truth_n5_48 | 5 | 104 | 48 | -53.85% | 2 |
| truth_n6_23 | 6 | 212 | 100 | -52.83% | 3 |
| truth_n6_7 | 6 | 212 | 100 | -52.83% | 3 |
| truth_n5_10 | 5 | 76 | 36 | -52.63% | 2 |
| truth_n6_4 | 6 | 244 | 116 | -52.46% | 3 |
| truth_n5_24 | 5 | 92 | 44 | -52.17% | 3 |
| truth_n5_51 | 5 | 100 | 48 | -52.00% | 2 |
| truth_n6_27 | 6 | 156 | 76 | -51.28% | 3 |
| truth_n6_16 | 6 | 196 | 96 | -51.02% | 4 |
| truth_n6_6 | 6 | 228 | 112 | -50.88% | 3 |
| adder_carry_w2 | 4 | 24 | 12 | -50.00% | 2 |
| majority_n6 | 6 | 184 | 92 | -50.00% | 3 |
| threshold3_n6 | 6 | 184 | 92 | -50.00% | 3 |
| truth_n4_11 | 4 | 24 | 12 | -50.00% | 2 |
| truth_n4_2 | 4 | 40 | 20 | -50.00% | 2 |
| truth_n4_27 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_28 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_31 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_38 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_5 | 4 | 32 | 16 | -50.00% | 2 |
| truth_n4_56 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n4_57 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n5_1 | 5 | 96 | 48 | -50.00% | 2 |
| truth_n5_12 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_2 | 5 | 104 | 52 | -50.00% | 3 |
| truth_n5_20 | 5 | 80 | 40 | -50.00% | 2 |
| truth_n5_26 | 5 | 104 | 52 | -50.00% | 2 |
| truth_n5_33 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_42 | 5 | 88 | 44 | -50.00% | 2 |
| truth_n5_61 | 5 | 64 | 32 | -50.00% | 2 |
| truth_n5_8 | 5 | 88 | 44 | -50.00% | 3 |
| truth_n6_11 | 6 | 232 | 116 | -50.00% | 3 |
| truth_n6_12 | 6 | 184 | 92 | -50.00% | 3 |
| truth_n6_24 | 6 | 228 | 116 | -49.12% | 3 |
| truth_n6_26 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n6_3 | 6 | 212 | 108 | -49.06% | 3 |
| truth_n6_17 | 6 | 188 | 96 | -48.94% | 3 |
| truth_n6_22 | 6 | 224 | 116 | -48.21% | 3 |
| truth_n5_23 | 5 | 92 | 48 | -47.83% | 2 |
| truth_n5_11 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_29 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_41 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_43 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n5_57 | 5 | 84 | 44 | -47.62% | 2 |
| truth_n6_14 | 6 | 168 | 88 | -47.62% | 3 |
| truth_n6_5 | 6 | 204 | 108 | -47.06% | 3 |
| mux_2_4 | 6 | 60 | 32 | -46.67% | 2 |
| truth_n5_30 | 5 | 60 | 32 | -46.67% | 2 |
| truth_n6_18 | 6 | 156 | 84 | -46.15% | 3 |
| truth_n6_19 | 6 | 200 | 108 | -46.00% | 3 |
| truth_n6_30 | 6 | 192 | 104 | -45.83% | 3 |
| majority_n4 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_3 | 5 | 80 | 44 | -45.00% | 3 |
| truth_n6_31 | 6 | 196 | 108 | -44.90% | 3 |
| truth_n6_0 | 6 | 188 | 104 | -44.68% | 3 |
| truth_n4_24 | 4 | 36 | 20 | -44.44% | 2 |
| truth_n4_7 | 4 | 36 | 20 | -44.44% | 2 |
| truth_n5_54 | 5 | 72 | 40 | -44.44% | 3 |
| truth_n5_55 | 5 | 72 | 40 | -44.44% | 3 |
| truth_n5_31 | 5 | 64 | 36 | -43.75% | 2 |
| truth_n6_15 | 6 | 192 | 108 | -43.75% | 3 |
| truth_n6_28 | 6 | 156 | 88 | -43.59% | 3 |
| truth_n4_10 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n4_17 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n4_41 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n5_47 | 5 | 84 | 48 | -42.86% | 2 |
| truth_n5_56 | 5 | 76 | 44 | -42.11% | 3 |
| truth_n6_21 | 6 | 200 | 116 | -42.00% | 3 |
| adder_carry_w3 | 6 | 48 | 28 | -41.67% | 4 |
| truth_n5_50 | 5 | 96 | 56 | -41.67% | 2 |
| truth_n6_20 | 6 | 184 | 108 | -41.30% | 3 |
| truth_n5_46 | 5 | 88 | 52 | -40.91% | 2 |
| truth_n4_19 | 4 | 20 | 12 | -40.00% | 2 |
| truth_n5_28 | 5 | 80 | 48 | -40.00% | 3 |
| truth_n5_35 | 5 | 80 | 48 | -40.00% | 3 |
| truth_n6_9 | 6 | 200 | 120 | -40.00% | 4 |
| truth_n5_27 | 5 | 72 | 44 | -38.89% | 2 |
| truth_n5_18 | 5 | 52 | 32 | -38.46% | 2 |
| truth_n6_29 | 6 | 156 | 96 | -38.46% | 3 |
| truth_n6_13 | 6 | 188 | 116 | -38.30% | 3 |
| truth_n6_1 | 6 | 200 | 124 | -38.00% | 4 |
| truth_n4_26 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_35 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_37 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_39 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_47 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_63 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_0 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_49 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_6 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_13 | 5 | 76 | 48 | -36.84% | 3 |
| truth_n5_14 | 5 | 76 | 48 | -36.84% | 2 |
| truth_n5_16 | 5 | 76 | 48 | -36.84% | 2 |
| truth_n5_63 | 5 | 80 | 52 | -35.00% | 2 |
| truth_n6_2 | 6 | 172 | 112 | -34.88% | 4 |
| truth_n6_8 | 6 | 176 | 116 | -34.09% | 3 |
| threshold2_n4 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_3 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_30 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_36 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_43 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_45 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_51 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_6 | 4 | 24 | 16 | -33.33% | 1 |
| threshold2_n5 | 5 | 64 | 44 | -31.25% | 2 |
| truth_n5_34 | 5 | 64 | 44 | -31.25% | 2 |
| truth_n5_44 | 5 | 40 | 28 | -30.00% | 2 |
| truth_n5_45 | 5 | 68 | 48 | -29.41% | 2 |
| truth_n5_15 | 5 | 56 | 40 | -28.57% | 2 |
| majority_n5 | 5 | 80 | 60 | -25.00% | 3 |
| truth_n4_42 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_53 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n5_4 | 5 | 64 | 48 | -25.00% | 2 |
| truth_n5_9 | 5 | 52 | 40 | -23.08% | 2 |
| truth_n4_0 | 4 | 20 | 16 | -20.00% | 2 |
| truth_n4_1 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_16 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_21 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_23 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_29 | 4 | 20 | 16 | -20.00% | 2 |
| truth_n4_32 | 4 | 20 | 16 | -20.00% | 2 |
| truth_n4_33 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_40 | 4 | 20 | 16 | -20.00% | 2 |
| truth_n4_50 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n5_52 | 5 | 60 | 48 | -20.00% | 3 |
| truth_n4_4 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n4_55 | 4 | 24 | 20 | -16.67% | 2 |
| truth_n4_12 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_15 | 4 | 20 | 20 | +0.00% | 2 |
| truth_n4_58 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_8 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_9 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n5_58 | 5 | 24 | 24 | +0.00% | 2 |
| truth_n4_44 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_61 | 4 | 16 | 20 | +25.00% | 1 |
| majority_n3 | 3 | 4 | 8 | +100.00% | 1 |
| threshold2_n3 | 3 | 4 | 8 | +100.00% | 1 |

## and_cube_beam vs SSHR-H

| function | n | SSHR-H T | and_cube_beam T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n4_34 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n5_25 | 5 | 112 | 48 | -57.14% | 3 |
| mul_w3_bit2 | 6 | 48 | 24 | -50.00% | 2 |
| truth_n4_22 | 4 | 48 | 24 | -50.00% | 2 |
| truth_n5_53 | 5 | 104 | 56 | -46.15% | 3 |
| truth_n4_18 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n4_59 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_5 | 5 | 124 | 68 | -45.16% | 3 |
| truth_n4_52 | 4 | 36 | 20 | -44.44% | 1 |
| truth_n4_62 | 4 | 36 | 20 | -44.44% | 2 |
| truth_n5_59 | 5 | 108 | 60 | -44.44% | 3 |
| truth_n4_48 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n5_19 | 5 | 84 | 48 | -42.86% | 2 |
| truth_n5_26 | 5 | 104 | 60 | -42.31% | 3 |
| truth_n5_48 | 5 | 104 | 60 | -42.31% | 3 |
| truth_n5_62 | 5 | 96 | 56 | -41.67% | 3 |
| truth_n5_22 | 5 | 108 | 64 | -40.74% | 3 |
| truth_n5_38 | 5 | 100 | 60 | -40.00% | 3 |
| truth_n5_51 | 5 | 100 | 60 | -40.00% | 3 |
| truth_n6_25 | 6 | 204 | 124 | -39.22% | 3 |
| truth_n5_40 | 5 | 92 | 56 | -39.13% | 3 |
| truth_n5_29 | 5 | 84 | 52 | -38.10% | 2 |
| truth_n4_28 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_31 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_38 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_1 | 5 | 96 | 60 | -37.50% | 3 |
| truth_n4_13 | 4 | 44 | 28 | -36.36% | 2 |
| truth_n4_46 | 4 | 44 | 28 | -36.36% | 2 |
| truth_n5_12 | 5 | 88 | 56 | -36.36% | 3 |
| truth_n5_21 | 5 | 88 | 56 | -36.36% | 2 |
| truth_n6_19 | 6 | 200 | 128 | -36.00% | 4 |
| truth_n5_17 | 5 | 80 | 52 | -35.00% | 2 |
| truth_n6_11 | 6 | 232 | 152 | -34.48% | 4 |
| truth_n6_4 | 6 | 244 | 160 | -34.43% | 4 |
| truth_n6_17 | 6 | 188 | 124 | -34.04% | 3 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_24 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_27 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_30 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_36 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_45 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_51 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_56 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_57 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_60 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n5_50 | 5 | 96 | 64 | -33.33% | 3 |
| truth_n6_10 | 6 | 240 | 160 | -33.33% | 4 |
| truth_n5_60 | 5 | 100 | 68 | -32.00% | 3 |
| truth_n5_46 | 5 | 88 | 60 | -31.82% | 3 |
| truth_n5_13 | 5 | 76 | 52 | -31.58% | 3 |
| truth_n6_6 | 6 | 228 | 156 | -31.58% | 4 |
| truth_n5_36 | 5 | 108 | 76 | -29.63% | 3 |
| truth_n4_10 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n4_17 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n4_41 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n5_43 | 5 | 84 | 60 | -28.57% | 3 |
| truth_n5_47 | 5 | 84 | 60 | -28.57% | 3 |
| truth_n5_57 | 5 | 84 | 60 | -28.57% | 3 |
| truth_n6_26 | 6 | 212 | 152 | -28.30% | 4 |
| truth_n5_39 | 5 | 72 | 52 | -27.78% | 3 |
| truth_n5_8 | 5 | 88 | 64 | -27.27% | 3 |
| truth_n5_30 | 5 | 60 | 44 | -26.67% | 3 |
| truth_n6_31 | 6 | 196 | 144 | -26.53% | 4 |
| truth_n6_23 | 6 | 212 | 156 | -26.42% | 4 |
| truth_n6_3 | 6 | 212 | 156 | -26.42% | 4 |
| truth_n6_0 | 6 | 188 | 140 | -25.53% | 4 |
| truth_n6_5 | 6 | 204 | 152 | -25.49% | 4 |
| truth_n4_26 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_35 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_47 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_5 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_63 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n5_3 | 5 | 80 | 60 | -25.00% | 3 |
| truth_n6_30 | 6 | 192 | 144 | -25.00% | 4 |
| truth_n5_32 | 5 | 88 | 68 | -22.73% | 3 |
| truth_n5_42 | 5 | 88 | 68 | -22.73% | 3 |
| truth_n5_7 | 5 | 88 | 68 | -22.73% | 3 |
| truth_n4_7 | 4 | 36 | 28 | -22.22% | 2 |
| truth_n5_24 | 5 | 92 | 72 | -21.74% | 3 |
| truth_n5_37 | 5 | 56 | 44 | -21.43% | 2 |
| truth_n5_14 | 5 | 76 | 60 | -21.05% | 2 |
| truth_n5_56 | 5 | 76 | 60 | -21.05% | 3 |
| truth_n6_24 | 6 | 228 | 180 | -21.05% | 4 |
| truth_n6_18 | 6 | 156 | 124 | -20.51% | 4 |
| truth_n6_27 | 6 | 156 | 124 | -20.51% | 4 |
| truth_n4_2 | 4 | 40 | 32 | -20.00% | 2 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n6_21 | 6 | 200 | 160 | -20.00% | 4 |
| truth_n6_22 | 6 | 224 | 180 | -19.64% | 4 |
| truth_n5_2 | 5 | 104 | 84 | -19.23% | 3 |
| truth_n6_7 | 6 | 212 | 172 | -18.87% | 4 |
| truth_n5_0 | 5 | 64 | 52 | -18.75% | 2 |
| truth_n5_6 | 5 | 64 | 52 | -18.75% | 2 |
| truth_n6_16 | 6 | 196 | 160 | -18.37% | 4 |
| truth_n6_12 | 6 | 184 | 152 | -17.39% | 4 |
| adder_carry_w2 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n4_43 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n5_28 | 5 | 80 | 68 | -15.00% | 3 |
| truth_n5_63 | 5 | 80 | 68 | -15.00% | 3 |
| truth_n6_13 | 6 | 188 | 160 | -14.89% | 4 |
| truth_n6_15 | 6 | 192 | 164 | -14.58% | 4 |
| truth_n4_49 | 4 | 28 | 24 | -14.29% | 1 |
| truth_n5_41 | 5 | 84 | 72 | -14.29% | 3 |
| truth_n6_14 | 6 | 168 | 144 | -14.29% | 4 |
| truth_n6_1 | 6 | 200 | 172 | -14.00% | 4 |
| truth_n6_2 | 6 | 172 | 148 | -13.95% | 4 |
| truth_n4_42 | 4 | 32 | 28 | -12.50% | 2 |
| truth_n6_9 | 6 | 200 | 176 | -12.00% | 4 |
| truth_n5_45 | 5 | 68 | 60 | -11.76% | 3 |
| threshold2_n4 | 4 | 36 | 32 | -11.11% | 2 |
| truth_n4_3 | 4 | 36 | 32 | -11.11% | 2 |
| truth_n5_54 | 5 | 72 | 64 | -11.11% | 3 |
| truth_n6_20 | 6 | 184 | 164 | -10.87% | 4 |
| truth_n6_29 | 6 | 156 | 140 | -10.26% | 4 |
| truth_n5_20 | 5 | 80 | 72 | -10.00% | 3 |
| truth_n5_11 | 5 | 84 | 76 | -9.52% | 3 |
| majority_n4 | 4 | 44 | 40 | -9.09% | 2 |
| truth_n5_15 | 5 | 56 | 52 | -7.14% | 3 |
| truth_n6_8 | 6 | 176 | 164 | -6.82% | 4 |
| truth_n5_27 | 5 | 72 | 68 | -5.56% | 3 |
| truth_n6_28 | 6 | 156 | 152 | -2.56% | 4 |
| truth_n4_11 | 4 | 24 | 24 | +0.00% | 1 |
| truth_n4_16 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_23 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_33 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_54 | 4 | 44 | 44 | +0.00% | 2 |
| truth_n5_10 | 5 | 76 | 76 | +0.00% | 3 |
| truth_n5_16 | 5 | 76 | 76 | +0.00% | 3 |
| truth_n5_52 | 5 | 60 | 60 | +0.00% | 3 |
| truth_n5_55 | 5 | 72 | 72 | +0.00% | 3 |
| truth_n5_4 | 5 | 64 | 68 | +6.25% | 3 |
| truth_n5_49 | 5 | 64 | 68 | +6.25% | 3 |
| truth_n5_35 | 5 | 80 | 88 | +10.00% | 3 |
| truth_n5_31 | 5 | 64 | 72 | +12.50% | 3 |
| truth_n5_34 | 5 | 64 | 72 | +12.50% | 3 |
| truth_n5_61 | 5 | 64 | 72 | +12.50% | 3 |
| majority_n6 | 6 | 184 | 208 | +13.04% | 4 |
| threshold3_n6 | 6 | 184 | 208 | +13.04% | 4 |
| truth_n5_23 | 5 | 92 | 104 | +13.04% | 3 |
| mux_2_4 | 6 | 60 | 68 | +13.33% | 2 |
| majority_n5 | 5 | 80 | 92 | +15.00% | 3 |
| truth_n5_33 | 5 | 88 | 104 | +18.18% | 3 |
| truth_n4_0 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_19 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_21 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_29 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_32 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_40 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_58 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_8 | 4 | 20 | 24 | +20.00% | 1 |
| threshold2_n5 | 5 | 64 | 80 | +25.00% | 3 |
| truth_n4_37 | 4 | 32 | 40 | +25.00% | 2 |
| truth_n4_39 | 4 | 32 | 40 | +25.00% | 2 |
| truth_n5_18 | 5 | 52 | 68 | +30.77% | 3 |
| truth_n4_55 | 4 | 24 | 32 | +33.33% | 2 |
| truth_n4_14 | 4 | 44 | 60 | +36.36% | 2 |
| truth_n4_53 | 4 | 32 | 44 | +37.50% | 2 |
| truth_n4_15 | 4 | 20 | 28 | +40.00% | 2 |
| truth_n4_44 | 4 | 20 | 28 | +40.00% | 2 |
| truth_n4_4 | 4 | 24 | 36 | +50.00% | 2 |
| truth_n4_6 | 4 | 24 | 36 | +50.00% | 2 |
| truth_n4_1 | 4 | 20 | 32 | +60.00% | 2 |
| truth_n4_12 | 4 | 20 | 32 | +60.00% | 2 |
| truth_n4_9 | 4 | 20 | 32 | +60.00% | 2 |
| truth_n5_44 | 5 | 40 | 68 | +70.00% | 3 |
| truth_n5_9 | 5 | 52 | 92 | +76.92% | 3 |
| truth_n4_50 | 4 | 20 | 36 | +80.00% | 2 |
| truth_n4_61 | 4 | 16 | 32 | +100.00% | 2 |
| truth_n5_58 | 5 | 24 | 56 | +133.33% | 2 |
| parity_n5 | 5 | 96 | 256 | +166.67% | 3 |
| adder_carry_w3 | 6 | 48 | 144 | +200.00% | 4 |
| majority_n3 | 3 | 4 | 16 | +300.00% | 1 |
| parity_n3 | 3 | 8 | 32 | +300.00% | 1 |
| threshold2_n3 | 3 | 4 | 16 | +300.00% | 1 |
| parity_n6 | 6 | 96 | 640 | +566.67% | 4 |
| parity_n4 | 4 | 8 | 96 | +1100.00% | 2 |

## and_esop_milp vs SSHR-H

| function | n | SSHR-H T | and_esop_milp T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| truth_n5_25 | 5 | 112 | 40 | -64.29% | 3 |
| truth_n4_34 | 4 | 44 | 16 | -63.64% | 2 |
| truth_n4_22 | 4 | 48 | 20 | -58.33% | 2 |
| truth_n5_37 | 5 | 56 | 24 | -57.14% | 1 |
| truth_n5_36 | 5 | 108 | 48 | -55.56% | 3 |
| truth_n5_5 | 5 | 124 | 56 | -54.84% | 3 |
| truth_n4_18 | 4 | 44 | 20 | -54.55% | 2 |
| truth_n5_53 | 5 | 104 | 48 | -53.85% | 3 |
| truth_n5_41 | 5 | 84 | 40 | -52.38% | 2 |
| truth_n5_22 | 5 | 108 | 52 | -51.85% | 3 |
| mul_w3_bit2 | 6 | 48 | 24 | -50.00% | 2 |
| truth_n4_57 | 4 | 24 | 12 | -50.00% | 1 |
| truth_n5_1 | 5 | 96 | 48 | -50.00% | 3 |
| truth_n5_7 | 5 | 88 | 44 | -50.00% | 3 |
| truth_n5_59 | 5 | 108 | 56 | -48.15% | 3 |
| truth_n5_38 | 5 | 100 | 52 | -48.00% | 3 |
| truth_n5_24 | 5 | 92 | 48 | -47.83% | 2 |
| truth_n5_40 | 5 | 92 | 48 | -47.83% | 3 |
| truth_n5_19 | 5 | 84 | 44 | -47.62% | 2 |
| mux_2_4 | 6 | 60 | 32 | -46.67% | 1 |
| truth_n5_62 | 5 | 96 | 52 | -45.83% | 3 |
| truth_n4_14 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n4_46 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n4_59 | 4 | 44 | 24 | -45.45% | 2 |
| truth_n5_12 | 5 | 88 | 48 | -45.45% | 3 |
| truth_n5_21 | 5 | 88 | 48 | -45.45% | 2 |
| truth_n5_17 | 5 | 80 | 44 | -45.00% | 2 |
| truth_n4_52 | 4 | 36 | 20 | -44.44% | 1 |
| truth_n4_62 | 4 | 36 | 20 | -44.44% | 2 |
| truth_n5_51 | 5 | 100 | 56 | -44.00% | 3 |
| truth_n5_60 | 5 | 100 | 56 | -44.00% | 3 |
| truth_n4_48 | 4 | 28 | 16 | -42.86% | 2 |
| truth_n4_49 | 4 | 28 | 16 | -42.86% | 1 |
| truth_n5_48 | 5 | 104 | 60 | -42.31% | 3 |
| truth_n5_16 | 5 | 76 | 44 | -42.11% | 3 |
| truth_n5_32 | 5 | 88 | 52 | -40.91% | 2 |
| truth_n5_42 | 5 | 88 | 52 | -40.91% | 2 |
| truth_n5_46 | 5 | 88 | 52 | -40.91% | 3 |
| truth_n5_23 | 5 | 92 | 56 | -39.13% | 3 |
| truth_n5_29 | 5 | 84 | 52 | -38.10% | 2 |
| truth_n5_43 | 5 | 84 | 52 | -38.10% | 3 |
| truth_n5_57 | 5 | 84 | 52 | -38.10% | 3 |
| truth_n4_28 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_31 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n4_38 | 4 | 32 | 20 | -37.50% | 2 |
| truth_n5_0 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_50 | 5 | 96 | 60 | -37.50% | 3 |
| truth_n5_61 | 5 | 64 | 40 | -37.50% | 2 |
| truth_n5_10 | 5 | 76 | 48 | -36.84% | 2 |
| truth_n5_56 | 5 | 76 | 48 | -36.84% | 3 |
| truth_n4_13 | 4 | 44 | 28 | -36.36% | 2 |
| truth_n4_54 | 4 | 44 | 28 | -36.36% | 2 |
| truth_n5_33 | 5 | 88 | 56 | -36.36% | 3 |
| truth_n5_8 | 5 | 88 | 56 | -36.36% | 3 |
| truth_n5_26 | 5 | 104 | 68 | -34.62% | 3 |
| truth_n4_20 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_24 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_27 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_30 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_36 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_43 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_45 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_51 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_56 | 4 | 24 | 16 | -33.33% | 1 |
| truth_n4_60 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n4_7 | 4 | 36 | 24 | -33.33% | 2 |
| truth_n5_11 | 5 | 84 | 56 | -33.33% | 2 |
| truth_n5_27 | 5 | 72 | 48 | -33.33% | 3 |
| truth_n5_30 | 5 | 60 | 40 | -33.33% | 3 |
| truth_n5_47 | 5 | 84 | 56 | -33.33% | 3 |
| truth_n5_55 | 5 | 72 | 48 | -33.33% | 2 |
| truth_n5_13 | 5 | 76 | 52 | -31.58% | 3 |
| truth_n5_14 | 5 | 76 | 52 | -31.58% | 2 |
| truth_n5_6 | 5 | 64 | 44 | -31.25% | 2 |
| truth_n5_18 | 5 | 52 | 36 | -30.77% | 2 |
| truth_n4_2 | 4 | 40 | 28 | -30.00% | 2 |
| truth_n5_20 | 5 | 80 | 56 | -30.00% | 2 |
| truth_n5_3 | 5 | 80 | 56 | -30.00% | 3 |
| truth_n5_63 | 5 | 80 | 56 | -30.00% | 3 |
| truth_n4_10 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n4_17 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n4_41 | 4 | 28 | 20 | -28.57% | 2 |
| truth_n5_15 | 5 | 56 | 40 | -28.57% | 3 |
| truth_n5_39 | 5 | 72 | 52 | -27.78% | 3 |
| truth_n5_54 | 5 | 72 | 52 | -27.78% | 2 |
| majority_n4 | 4 | 44 | 32 | -27.27% | 2 |
| truth_n4_26 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_35 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_37 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_42 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_47 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_5 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_53 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n4_63 | 4 | 32 | 24 | -25.00% | 2 |
| truth_n5_28 | 5 | 80 | 60 | -25.00% | 2 |
| truth_n5_31 | 5 | 64 | 48 | -25.00% | 2 |
| truth_n5_45 | 5 | 68 | 52 | -23.53% | 3 |
| truth_n4_16 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_23 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_25 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n4_33 | 4 | 20 | 16 | -20.00% | 1 |
| truth_n5_34 | 5 | 64 | 52 | -18.75% | 2 |
| truth_n5_49 | 5 | 64 | 52 | -18.75% | 2 |
| adder_carry_w2 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n4_11 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n4_6 | 4 | 24 | 20 | -16.67% | 1 |
| truth_n5_2 | 5 | 104 | 88 | -15.38% | 3 |
| truth_n4_39 | 4 | 32 | 28 | -12.50% | 2 |
| threshold2_n4 | 4 | 36 | 32 | -11.11% | 2 |
| truth_n4_3 | 4 | 36 | 32 | -11.11% | 2 |
| truth_n5_35 | 5 | 80 | 72 | -10.00% | 2 |
| truth_n5_44 | 5 | 40 | 36 | -10.00% | 2 |
| truth_n5_52 | 5 | 60 | 56 | -6.67% | 3 |
| threshold2_n5 | 5 | 64 | 60 | -6.25% | 3 |
| majority_n6 | 6 | 184 | 176 | -4.35% | 4 |
| majority_n5 | 5 | 80 | 80 | +0.00% | 3 |
| truth_n4_0 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_1 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_19 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_21 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_29 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_32 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n4_4 | 4 | 24 | 24 | +0.00% | 1 |
| truth_n4_50 | 4 | 20 | 20 | +0.00% | 1 |
| truth_n5_4 | 5 | 64 | 64 | +0.00% | 3 |
| truth_n5_9 | 5 | 52 | 52 | +0.00% | 2 |
| truth_n6_17 | 6 | 188 | 196 | +4.26% | 4 |
| truth_n6_26 | 6 | 212 | 232 | +9.43% | 4 |
| truth_n6_11 | 6 | 232 | 260 | +12.07% | 4 |
| truth_n6_5 | 6 | 204 | 236 | +15.69% | 4 |
| truth_n4_55 | 4 | 24 | 28 | +16.67% | 2 |
| truth_n6_10 | 6 | 240 | 280 | +16.67% | 4 |
| truth_n4_12 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_40 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_58 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_8 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n4_9 | 4 | 20 | 24 | +20.00% | 1 |
| truth_n6_15 | 6 | 192 | 232 | +20.83% | 4 |
| truth_n6_25 | 6 | 204 | 248 | +21.57% | 3 |
| truth_n6_30 | 6 | 192 | 240 | +25.00% | 4 |
| truth_n6_8 | 6 | 176 | 220 | +25.00% | 4 |
| truth_n6_7 | 6 | 212 | 268 | +26.42% | 4 |
| truth_n6_6 | 6 | 228 | 316 | +38.60% | 4 |
| truth_n6_23 | 6 | 212 | 296 | +39.62% | 4 |
| truth_n4_15 | 4 | 20 | 28 | +40.00% | 2 |
| truth_n4_44 | 4 | 20 | 28 | +40.00% | 2 |
| truth_n6_4 | 6 | 244 | 344 | +40.98% | 4 |
| truth_n6_24 | 6 | 228 | 332 | +45.61% | 4 |
| truth_n6_22 | 6 | 224 | 328 | +46.43% | 4 |
| truth_n6_9 | 6 | 200 | 296 | +48.00% | 4 |
| truth_n6_31 | 6 | 196 | 292 | +48.98% | 4 |
| truth_n4_61 | 4 | 16 | 24 | +50.00% | 1 |
| truth_n5_58 | 5 | 24 | 36 | +50.00% | 1 |
| truth_n6_1 | 6 | 200 | 300 | +50.00% | 4 |
| truth_n6_28 | 6 | 156 | 236 | +51.28% | 4 |
| truth_n6_21 | 6 | 200 | 304 | +52.00% | 4 |
| truth_n6_20 | 6 | 184 | 284 | +54.35% | 4 |
| truth_n6_16 | 6 | 196 | 304 | +55.10% | 4 |
| truth_n6_3 | 6 | 212 | 332 | +56.60% | 4 |
| truth_n6_13 | 6 | 188 | 296 | +57.45% | 4 |
| truth_n6_12 | 6 | 184 | 292 | +58.70% | 4 |
| truth_n6_27 | 6 | 156 | 252 | +61.54% | 4 |
| truth_n6_0 | 6 | 188 | 324 | +72.34% | 4 |
| adder_carry_w3 | 6 | 48 | 84 | +75.00% | 3 |
| threshold3_n6 | 6 | 184 | 328 | +78.26% | 4 |
| truth_n6_19 | 6 | 200 | 372 | +86.00% | 4 |
| truth_n6_29 | 6 | 156 | 296 | +89.74% | 3 |
| truth_n6_14 | 6 | 168 | 328 | +95.24% | 4 |
| truth_n6_2 | 6 | 172 | 336 | +95.35% | 4 |
| truth_n6_18 | 6 | 156 | 408 | +161.54% | 4 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |
