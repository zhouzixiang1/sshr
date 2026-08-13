# Search_Ablation_Traditional Analysis

Rows: 2301; usable: 2301; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_affine_greedy | 177 | -70.09% | -88.89% | +0.00% |
| and_affine_nmcts | 177 | -70.69% | -88.89% | +0.00% |
| and_direct_anf | 177 | -40.45% | -50.00% | +0.00% |
| and_fprm_greedy | 177 | -63.98% | -88.89% | +0.00% |
| and_fprm_linear_pair | 177 | -67.94% | -88.89% | +0.00% |
| and_fprm_root_beam | 177 | -64.49% | -88.89% | +0.00% |
| and_mcts_factor | 177 | -58.65% | -72.79% | +0.00% |
| and_pareto_resource_nmcts | 177 | -72.25% | -88.89% | +0.00% |
| and_resource_beam_only | 177 | -67.94% | -88.89% | +0.00% |
| and_resource_heuristic | 177 | -70.15% | -88.89% | +0.00% |
| and_resource_nmcts | 177 | -71.33% | -88.89% | +0.00% |
| and_resource_no_mcts | 177 | -70.99% | -88.89% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_affine_nmcts | and_affine_greedy | T | 32 | 0 | 145 | -2.13% |
| and_affine_nmcts | and_affine_greedy | CNOT | 43 | 15 | 119 | -1.70% |
| and_affine_nmcts | and_affine_greedy | depth | 48 | 13 | 116 | -1.99% |
| and_affine_nmcts | and_affine_greedy | peak_ancilla | 19 | 0 | 158 | -3.53% |
| and_affine_nmcts | and_affine_greedy | score | 66 | 0 | 111 | -2.23% |
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
| and_resource_nmcts | and_fprm_greedy | T | 155 | 0 | 22 | -20.04% |
| and_resource_nmcts | and_fprm_greedy | CNOT | 158 | 4 | 15 | -14.84% |
| and_resource_nmcts | and_fprm_greedy | depth | 156 | 6 | 15 | -13.89% |
| and_resource_nmcts | and_fprm_greedy | peak_ancilla | 22 | 8 | 147 | -1.65% |
| and_resource_nmcts | and_fprm_greedy | score | 162 | 0 | 15 | -18.10% |
| and_resource_nmcts | and_fprm_root_beam | T | 153 | 0 | 24 | -18.56% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 159 | 2 | 16 | -14.23% |
| and_resource_nmcts | and_fprm_root_beam | depth | 156 | 5 | 16 | -13.18% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 3 | 14 | 160 | +3.58% |
| and_resource_nmcts | and_fprm_root_beam | score | 161 | 1 | 15 | -16.44% |
| and_resource_nmcts | and_affine_greedy | T | 60 | 0 | 117 | -4.23% |
| and_resource_nmcts | and_affine_greedy | CNOT | 77 | 12 | 88 | -4.16% |
| and_resource_nmcts | and_affine_greedy | depth | 83 | 12 | 82 | -4.23% |
| and_resource_nmcts | and_affine_greedy | peak_ancilla | 19 | 7 | 151 | -1.32% |
| and_resource_nmcts | and_affine_greedy | score | 99 | 0 | 78 | -4.12% |
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
| and_fprm_linear_pair | and_fprm_root_beam | T | 117 | 0 | 60 | -9.14% |
| and_fprm_linear_pair | and_fprm_root_beam | CNOT | 125 | 1 | 51 | -7.14% |
| and_fprm_linear_pair | and_fprm_root_beam | depth | 116 | 6 | 55 | -6.39% |
| and_fprm_linear_pair | and_fprm_root_beam | peak_ancilla | 0 | 37 | 140 | +13.18% |
| and_fprm_linear_pair | and_fprm_root_beam | score | 127 | 0 | 50 | -7.29% |
| and_fprm_linear_pair | and_fprm_greedy | T | 124 | 0 | 53 | -10.73% |
| and_fprm_linear_pair | and_fprm_greedy | CNOT | 126 | 2 | 49 | -7.79% |
| and_fprm_linear_pair | and_fprm_greedy | depth | 118 | 6 | 53 | -7.14% |
| and_fprm_linear_pair | and_fprm_greedy | peak_ancilla | 16 | 28 | 133 | +7.67% |
| and_fprm_linear_pair | and_fprm_greedy | score | 130 | 0 | 47 | -9.07% |
| and_resource_nmcts | and_fprm_linear_pair | T | 90 | 0 | 87 | -10.23% |
| and_resource_nmcts | and_fprm_linear_pair | CNOT | 103 | 13 | 61 | -7.48% |
| and_resource_nmcts | and_fprm_linear_pair | depth | 105 | 12 | 60 | -7.10% |
| and_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 29 | 3 | 145 | -6.03% |
| and_resource_nmcts | and_fprm_linear_pair | score | 118 | 1 | 58 | -9.75% |
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
| and_pareto_resource_nmcts | and_fprm_linear_pair | T | 130 | 0 | 47 | -13.90% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | CNOT | 149 | 2 | 26 | -11.37% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | depth | 145 | 6 | 26 | -10.56% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 27 | 20 | 130 | -1.69% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | score | 153 | 0 | 24 | -12.96% |
| and_pareto_resource_nmcts | and_fprm_root_beam | T | 158 | 0 | 19 | -21.88% |
| and_pareto_resource_nmcts | and_fprm_root_beam | CNOT | 163 | 0 | 14 | -17.78% |
| and_pareto_resource_nmcts | and_fprm_root_beam | depth | 160 | 4 | 13 | -16.36% |
| and_pareto_resource_nmcts | and_fprm_root_beam | peak_ancilla | 2 | 29 | 146 | +8.29% |
| and_pareto_resource_nmcts | and_fprm_root_beam | score | 164 | 0 | 13 | -19.38% |
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
| and_fprm_root_beam | and_fprm_greedy | T | 50 | 0 | 127 | -1.74% |
| and_fprm_root_beam | and_fprm_greedy | CNOT | 48 | 15 | 114 | -0.70% |
| and_fprm_root_beam | and_fprm_greedy | depth | 50 | 14 | 113 | -0.80% |
| and_fprm_root_beam | and_fprm_greedy | peak_ancilla | 25 | 0 | 152 | -4.66% |
| and_fprm_root_beam | and_fprm_greedy | score | 66 | 0 | 111 | -1.92% |
| and_fprm_root_beam | and_affine_greedy | T | 18 | 122 | 37 | +21.89% |
| and_fprm_root_beam | and_affine_greedy | CNOT | 32 | 118 | 27 | +13.87% |
| and_fprm_root_beam | and_affine_greedy | depth | 29 | 125 | 23 | +12.12% |
| and_fprm_root_beam | and_affine_greedy | peak_ancilla | 24 | 1 | 152 | -4.14% |
| and_fprm_root_beam | and_affine_greedy | score | 25 | 130 | 22 | +18.03% |
| and_affine_greedy | and_fprm_greedy | T | 131 | 5 | 41 | -16.06% |
| and_affine_greedy | and_fprm_greedy | CNOT | 122 | 24 | 31 | -10.75% |
| and_affine_greedy | and_fprm_greedy | depth | 125 | 23 | 29 | -9.78% |
| and_affine_greedy | and_fprm_greedy | peak_ancilla | 11 | 9 | 157 | +0.33% |
| and_affine_greedy | and_fprm_greedy | score | 140 | 10 | 27 | -14.22% |
| and_affine_greedy | and_mcts_factor | T | 157 | 5 | 15 | -27.57% |
| and_affine_greedy | and_mcts_factor | CNOT | 157 | 8 | 12 | -25.20% |
| and_affine_greedy | and_mcts_factor | depth | 154 | 11 | 12 | -20.52% |
| and_affine_greedy | and_mcts_factor | peak_ancilla | 0 | 29 | 148 | +8.00% |
| and_affine_greedy | and_mcts_factor | score | 159 | 7 | 11 | -24.92% |

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

## Largest and-affine-greedy gains vs direct ANF

| function | n | direct T | and_affine_greedy T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| majority_n5 | 5 | 280 | 32 | -88.57% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| truth_n5_30 | 5 | 220 | 32 | -85.45% |
| truth_n4_44 | 4 | 76 | 12 | -84.21% |
| truth_n4_24 | 4 | 100 | 16 | -84.00% |
| truth_n4_37 | 4 | 100 | 16 | -84.00% |
| truth_n5_13 | 5 | 192 | 32 | -83.33% |
| truth_n5_62 | 5 | 264 | 44 | -83.33% |
| truth_n5_35 | 5 | 236 | 40 | -83.05% |
| truth_n5_39 | 5 | 232 | 40 | -82.76% |
| truth_n6_6 | 6 | 548 | 96 | -82.48% |

## Largest and-fprm-greedy gains vs direct ANF

| function | n | direct T | and_fprm_greedy T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| truth_n5_30 | 5 | 220 | 40 | -81.82% |
| truth_n5_62 | 5 | 264 | 48 | -81.82% |
| threshold3_n6 | 6 | 680 | 132 | -80.59% |
| truth_n4_24 | 4 | 100 | 20 | -80.00% |
| truth_n4_37 | 4 | 100 | 20 | -80.00% |
| truth_n5_45 | 5 | 260 | 56 | -78.46% |
| truth_n5_48 | 5 | 256 | 56 | -78.12% |
| truth_n6_17 | 6 | 500 | 112 | -77.60% |
| truth_n4_28 | 4 | 68 | 16 | -76.47% |
| truth_n5_57 | 5 | 220 | 52 | -76.36% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| truth_n5_62 | 5 | 264 | 44 | -83.33% |
| truth_n5_30 | 5 | 220 | 40 | -81.82% |
| threshold3_n6 | 6 | 680 | 124 | -81.76% |
| truth_n4_24 | 4 | 100 | 20 | -80.00% |
| truth_n4_37 | 4 | 100 | 20 | -80.00% |
| truth_n5_45 | 5 | 260 | 56 | -78.46% |
| truth_n6_17 | 6 | 500 | 108 | -78.40% |
| truth_n5_48 | 5 | 256 | 56 | -78.12% |
| truth_n6_3 | 6 | 560 | 124 | -77.86% |
| truth_n5_39 | 5 | 232 | 52 | -77.59% |

## Largest and-fprm-linear-pair gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair T | relative |
|---|---:|---:|---:|---:|
| truth_n4_48 | 4 | 108 | 12 | -88.89% |
| truth_n5_44 | 5 | 228 | 32 | -85.96% |
| threshold3_n6 | 6 | 680 | 104 | -84.71% |
| truth_n5_30 | 5 | 220 | 36 | -83.64% |
| truth_n5_62 | 5 | 264 | 44 | -83.33% |
| truth_n5_39 | 5 | 232 | 40 | -82.76% |
| truth_n5_45 | 5 | 260 | 48 | -81.54% |
| truth_n4_24 | 4 | 100 | 20 | -80.00% |
| truth_n4_37 | 4 | 100 | 20 | -80.00% |
| truth_n5_48 | 5 | 256 | 52 | -79.69% |
| truth_n6_3 | 6 | 560 | 116 | -79.29% |
| truth_n6_17 | 6 | 500 | 104 | -79.20% |
