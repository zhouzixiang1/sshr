# Pilot Analysis

Rows: 420; usable: 403; errors: 4; skipped: 13.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 30 | -28.63% | -50.00% | +0.00% |
| and_fprm_mcts | 29 | -39.37% | -84.12% | +0.00% |
| and_fprm_neural_mcts | 27 | -37.12% | -84.12% | +0.00% |
| and_mcts_factor | 30 | -39.07% | -74.11% | +0.00% |
| and_rc_nmcts | 30 | -40.83% | -84.12% | +0.00% |
| cube_beam | 30 | +41035.14% | -39.41% | +716800.00% |
| cube_greedy | 30 | +41061.40% | -38.67% | +716800.00% |
| fprm_greedy | 30 | -24.09% | -63.60% | +0.00% |
| fprm_mcts | 30 | -26.23% | -68.62% | +0.00% |
| greedy_factor | 30 | -20.96% | -50.00% | +0.00% |
| mcts_factor | 30 | -23.18% | -60.78% | +0.00% |
| neural_mcts | 30 | -22.80% | -60.78% | +0.00% |
| sshr_h | 17 | +1211.75% | -72.94% | +9600.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|
| and_direct_anf | 9 | 8 | +5.36% |
| and_fprm_mcts | 13 | 4 | -21.28% |
| and_fprm_neural_mcts | 13 | 4 | -21.28% |
| and_mcts_factor | 11 | 6 | -14.99% |
| and_rc_nmcts | 13 | 4 | -21.28% |
| cube_beam | 2 | 15 | +425.35% |
| cube_greedy | 2 | 15 | +434.82% |
| fprm_greedy | 8 | 9 | +9.98% |
| fprm_mcts | 8 | 9 | +8.45% |
| greedy_factor | 8 | 9 | +17.63% |
| mcts_factor | 8 | 9 | +16.35% |
| neural_mcts | 8 | 9 | +16.35% |
| sshr_h | 0 | 17 | +0.00% |

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_rc_nmcts | direct_anf | T | 19 | 0 | 11 | -40.83% |
| and_rc_nmcts | direct_anf | CNOT | 11 | 13 | 6 | +3.86% |
| and_rc_nmcts | direct_anf | depth | 11 | 13 | 6 | +4.57% |
| and_rc_nmcts | direct_anf | peak_ancilla | 0 | 13 | 17 | +41.11% |
| and_rc_nmcts | direct_anf | score | 19 | 5 | 6 | -37.89% |
| and_rc_nmcts | and_direct_anf | T | 19 | 0 | 11 | -22.98% |
| and_rc_nmcts | and_direct_anf | CNOT | 19 | 0 | 11 | -16.21% |
| and_rc_nmcts | and_direct_anf | depth | 19 | 0 | 11 | -15.69% |
| and_rc_nmcts | and_direct_anf | peak_ancilla | 3 | 0 | 27 | -2.89% |
| and_rc_nmcts | and_direct_anf | score | 19 | 0 | 11 | -21.79% |
| and_rc_nmcts | and_fprm_mcts | T | 1 | 0 | 28 | -0.25% |
| and_rc_nmcts | and_fprm_mcts | CNOT | 1 | 2 | 26 | +0.01% |
| and_rc_nmcts | and_fprm_mcts | depth | 1 | 2 | 26 | +0.15% |
| and_rc_nmcts | and_fprm_mcts | peak_ancilla | 1 | 1 | 27 | +0.00% |
| and_rc_nmcts | and_fprm_mcts | score | 3 | 0 | 26 | -0.28% |
| and_rc_nmcts | and_fprm_neural_mcts | T | 0 | 1 | 26 | +0.12% |
| and_rc_nmcts | and_fprm_neural_mcts | CNOT | 0 | 1 | 26 | +0.29% |
| and_rc_nmcts | and_fprm_neural_mcts | depth | 0 | 1 | 26 | +0.28% |
| and_rc_nmcts | and_fprm_neural_mcts | peak_ancilla | 0 | 1 | 26 | +1.23% |
| and_rc_nmcts | and_fprm_neural_mcts | score | 0 | 1 | 26 | +0.16% |
| and_rc_nmcts | sshr_h | T | 13 | 2 | 2 | -21.28% |
| and_rc_nmcts | sshr_h | CNOT | 7 | 10 | 0 | +19.53% |
| and_rc_nmcts | sshr_h | depth | 8 | 9 | 0 | +2.83% |
| and_rc_nmcts | sshr_h | peak_ancilla | 3 | 6 | 8 | +17.65% |
| and_rc_nmcts | sshr_h | score | 13 | 4 | 0 | -18.81% |
| and_fprm_neural_mcts | direct_anf | T | 16 | 0 | 11 | -37.12% |
| and_fprm_neural_mcts | direct_anf | CNOT | 10 | 11 | 6 | +2.99% |
| and_fprm_neural_mcts | direct_anf | depth | 10 | 11 | 6 | +3.73% |
| and_fprm_neural_mcts | direct_anf | peak_ancilla | 0 | 9 | 18 | +33.33% |
| and_fprm_neural_mcts | direct_anf | score | 16 | 5 | 6 | -34.14% |
| and_fprm_neural_mcts | and_direct_anf | T | 16 | 0 | 11 | -20.15% |
| and_fprm_neural_mcts | and_direct_anf | CNOT | 16 | 0 | 11 | -13.59% |
| and_fprm_neural_mcts | and_direct_anf | depth | 16 | 0 | 11 | -13.05% |
| and_fprm_neural_mcts | and_direct_anf | peak_ancilla | 3 | 0 | 24 | -3.95% |
| and_fprm_neural_mcts | and_direct_anf | score | 16 | 0 | 11 | -18.97% |
| and_fprm_neural_mcts | and_fprm_mcts | T | 1 | 0 | 26 | -0.38% |
| and_fprm_neural_mcts | and_fprm_mcts | CNOT | 2 | 1 | 24 | -0.26% |
| and_fprm_neural_mcts | and_fprm_mcts | depth | 2 | 1 | 24 | -0.11% |
| and_fprm_neural_mcts | and_fprm_mcts | peak_ancilla | 1 | 0 | 26 | -1.23% |
| and_fprm_neural_mcts | and_fprm_mcts | score | 3 | 0 | 24 | -0.45% |
| and_fprm_neural_mcts | sshr_h | T | 13 | 2 | 2 | -21.28% |
| and_fprm_neural_mcts | sshr_h | CNOT | 7 | 10 | 0 | +19.53% |
| and_fprm_neural_mcts | sshr_h | depth | 8 | 9 | 0 | +2.83% |
| and_fprm_neural_mcts | sshr_h | peak_ancilla | 3 | 6 | 8 | +17.65% |
| and_fprm_neural_mcts | sshr_h | score | 13 | 4 | 0 | -18.81% |
| and_fprm_mcts | sshr_h | T | 13 | 2 | 2 | -21.28% |
| and_fprm_mcts | sshr_h | CNOT | 7 | 10 | 0 | +19.53% |
| and_fprm_mcts | sshr_h | depth | 8 | 9 | 0 | +2.83% |
| and_fprm_mcts | sshr_h | peak_ancilla | 3 | 6 | 8 | +17.65% |
| and_fprm_mcts | sshr_h | score | 13 | 4 | 0 | -18.81% |

## Largest and-rc-nmcts gains vs direct ANF

| function | n | direct T | and_rc_nmcts T | relative |
|---|---:|---:|---:|---:|
| threshold3_n6 | 6 | 680 | 108 | -84.12% |
| threshold3_n7 | 7 | 1448 | 252 | -82.60% |
| majority_n8 | 8 | 3352 | 612 | -81.74% |
| threshold2_n5 | 5 | 160 | 44 | -72.50% |
| majority_n5 | 5 | 280 | 80 | -71.43% |
| majority_n7 | 7 | 840 | 240 | -71.43% |
| threshold4_n8 | 8 | 1736 | 520 | -70.05% |
| majority_n6 | 6 | 360 | 108 | -70.00% |
| mux_3_8 | 11 | 408 | 124 | -69.61% |
| adder_carry_w4 | 8 | 388 | 128 | -67.01% |
| adder_carry_w3 | 6 | 132 | 48 | -63.64% |
| majority_n4 | 4 | 88 | 32 | -63.64% |

## Largest and-fprm-neural-mcts gains vs direct ANF

| function | n | direct T | and_fprm_neural_mcts T | relative |
|---|---:|---:|---:|---:|
| threshold3_n6 | 6 | 680 | 108 | -84.12% |
| threshold3_n7 | 7 | 1448 | 244 | -83.15% |
| threshold2_n5 | 5 | 160 | 44 | -72.50% |
| majority_n5 | 5 | 280 | 80 | -71.43% |
| majority_n6 | 6 | 360 | 108 | -70.00% |
| mux_3_8 | 11 | 408 | 124 | -69.61% |
| adder_carry_w4 | 8 | 388 | 128 | -67.01% |
| adder_carry_w3 | 6 | 132 | 48 | -63.64% |
| majority_n4 | 4 | 88 | 32 | -63.64% |
| mul_w4_bit3 | 8 | 176 | 64 | -63.64% |
| anf_n8_3 | 8 | 104 | 44 | -57.69% |
| adder_carry_w2 | 4 | 36 | 16 | -55.56% |

## Largest and-fprm-mcts gains vs direct ANF

| function | n | direct T | and_fprm_mcts T | relative |
|---|---:|---:|---:|---:|
| threshold3_n6 | 6 | 680 | 108 | -84.12% |
| threshold3_n7 | 7 | 1448 | 272 | -81.22% |
| threshold2_n5 | 5 | 160 | 44 | -72.50% |
| majority_n5 | 5 | 280 | 80 | -71.43% |
| majority_n7 | 7 | 840 | 240 | -71.43% |
| threshold4_n8 | 8 | 1736 | 520 | -70.05% |
| majority_n6 | 6 | 360 | 108 | -70.00% |
| mux_3_8 | 11 | 408 | 124 | -69.61% |
| adder_carry_w4 | 8 | 388 | 128 | -67.01% |
| adder_carry_w3 | 6 | 132 | 48 | -63.64% |
| majority_n4 | 4 | 88 | 32 | -63.64% |
| mul_w4_bit3 | 8 | 176 | 64 | -63.64% |

## Largest fprm-mcts gains vs direct ANF

| function | n | direct T | fprm_mcts T | relative |
|---|---:|---:|---:|---:|
| majority_n8 | 8 | 3352 | 1052 | -68.62% |
| threshold3_n6 | 6 | 680 | 240 | -64.71% |
| mux_3_8 | 11 | 408 | 160 | -60.78% |
| threshold3_n7 | 7 | 1448 | 572 | -60.50% |
| majority_n4 | 4 | 88 | 44 | -50.00% |
| mux_2_4 | 6 | 80 | 40 | -50.00% |
| majority_n5 | 5 | 280 | 144 | -48.57% |
| adder_carry_w2 | 4 | 36 | 20 | -44.44% |
| majority_n7 | 7 | 840 | 480 | -42.86% |
| threshold2_n5 | 5 | 160 | 96 | -40.00% |
| threshold4_n8 | 8 | 1736 | 1068 | -38.48% |
| anf_n8_3 | 8 | 104 | 64 | -38.46% |

## and_rc_nmcts vs SSHR-H

| function | n | SSHR-H T | and_rc_nmcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| majority_n6 | 6 | 184 | 108 | -41.30% | 2 |
| threshold3_n6 | 6 | 184 | 108 | -41.30% | 2 |
| mux_2_4 | 6 | 60 | 36 | -40.00% | 1 |
| adder_carry_w2 | 4 | 24 | 16 | -33.33% | 1 |
| threshold2_n5 | 5 | 64 | 44 | -31.25% | 2 |
| majority_n4 | 4 | 44 | 32 | -27.27% | 2 |
| threshold2_n4 | 4 | 36 | 32 | -11.11% | 2 |
| adder_carry_w3 | 6 | 48 | 48 | +0.00% | 2 |
| majority_n5 | 5 | 80 | 80 | +0.00% | 2 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |

## and_fprm_neural_mcts vs SSHR-H

| function | n | SSHR-H T | and_fprm_neural_mcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| majority_n6 | 6 | 184 | 108 | -41.30% | 2 |
| threshold3_n6 | 6 | 184 | 108 | -41.30% | 2 |
| mux_2_4 | 6 | 60 | 36 | -40.00% | 1 |
| adder_carry_w2 | 4 | 24 | 16 | -33.33% | 1 |
| threshold2_n5 | 5 | 64 | 44 | -31.25% | 2 |
| majority_n4 | 4 | 44 | 32 | -27.27% | 2 |
| threshold2_n4 | 4 | 36 | 32 | -11.11% | 2 |
| adder_carry_w3 | 6 | 48 | 48 | +0.00% | 2 |
| majority_n5 | 5 | 80 | 80 | +0.00% | 2 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |

## and_fprm_mcts vs SSHR-H

| function | n | SSHR-H T | and_fprm_mcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| parity_n5 | 5 | 96 | 0 | -100.00% | 0 |
| parity_n6 | 6 | 96 | 0 | -100.00% | 0 |
| mul_w2_bit1 | 4 | 36 | 8 | -77.78% | 0 |
| mul_w3_bit2 | 6 | 48 | 20 | -58.33% | 2 |
| majority_n6 | 6 | 184 | 108 | -41.30% | 2 |
| threshold3_n6 | 6 | 184 | 108 | -41.30% | 2 |
| mux_2_4 | 6 | 60 | 36 | -40.00% | 1 |
| adder_carry_w2 | 4 | 24 | 16 | -33.33% | 1 |
| threshold2_n5 | 5 | 64 | 44 | -31.25% | 2 |
| majority_n4 | 4 | 44 | 32 | -27.27% | 2 |
| threshold2_n4 | 4 | 36 | 32 | -11.11% | 2 |
| adder_carry_w3 | 6 | 48 | 48 | +0.00% | 2 |
| majority_n5 | 5 | 80 | 80 | +0.00% | 2 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |
