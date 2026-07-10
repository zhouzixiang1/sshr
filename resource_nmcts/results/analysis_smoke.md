# Smoke Analysis

Rows: 144; usable: 144; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 12 | -5.71% | -40.00% | +0.00% |
| and_fprm_mcts | 12 | -7.38% | -60.00% | +0.00% |
| and_fprm_neural_mcts | 12 | -7.38% | -60.00% | +0.00% |
| and_rc_nmcts | 12 | -7.38% | -60.00% | +0.00% |
| cube_beam | 12 | +2193.25% | +0.00% | +19200.00% |
| cube_greedy | 12 | +2232.14% | +0.00% | +19200.00% |
| fprm_mcts | 12 | -4.52% | -40.00% | +0.00% |
| greedy_factor | 12 | -3.33% | -40.00% | +0.00% |
| mcts_factor | 12 | -3.33% | -40.00% | +0.00% |
| neural_mcts | 12 | -3.33% | -40.00% | +0.00% |
| sshr_h | 12 | +105.48% | -66.67% | +800.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|
| and_direct_anf | 4 | 8 | +46.53% |
| and_fprm_mcts | 4 | 8 | +44.44% |
| and_fprm_neural_mcts | 4 | 8 | +44.44% |
| and_rc_nmcts | 4 | 8 | +44.44% |
| cube_beam | 0 | 12 | +461.81% |
| cube_greedy | 0 | 12 | +553.47% |
| fprm_mcts | 3 | 9 | +47.92% |
| greedy_factor | 3 | 9 | +49.31% |
| mcts_factor | 3 | 9 | +49.31% |
| neural_mcts | 3 | 9 | +49.31% |
| sshr_h | 0 | 12 | +0.00% |

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_rc_nmcts | direct_anf | T | 2 | 0 | 10 | -7.38% |
| and_rc_nmcts | direct_anf | CNOT | 1 | 7 | 4 | +5.34% |
| and_rc_nmcts | direct_anf | depth | 1 | 9 | 2 | +10.49% |
| and_rc_nmcts | direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | direct_anf | score | 2 | 8 | 2 | -5.44% |
| and_rc_nmcts | and_direct_anf | T | 1 | 0 | 11 | -2.78% |
| and_rc_nmcts | and_direct_anf | CNOT | 4 | 0 | 8 | -5.26% |
| and_rc_nmcts | and_direct_anf | depth | 1 | 1 | 10 | -0.47% |
| and_rc_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_direct_anf | score | 4 | 0 | 8 | -2.50% |
| and_rc_nmcts | and_fprm_mcts | T | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_mcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_mcts | depth | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_mcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_mcts | score | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_neural_mcts | T | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_neural_mcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_neural_mcts | depth | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_neural_mcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | and_fprm_neural_mcts | score | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | sshr_h | T | 4 | 5 | 3 | +44.44% |
| and_rc_nmcts | sshr_h | CNOT | 3 | 9 | 0 | +27.82% |
| and_rc_nmcts | sshr_h | depth | 3 | 8 | 1 | +21.16% |
| and_rc_nmcts | sshr_h | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_rc_nmcts | sshr_h | score | 4 | 8 | 0 | +41.64% |
| and_fprm_neural_mcts | direct_anf | T | 2 | 0 | 10 | -7.38% |
| and_fprm_neural_mcts | direct_anf | CNOT | 1 | 7 | 4 | +5.34% |
| and_fprm_neural_mcts | direct_anf | depth | 1 | 9 | 2 | +10.49% |
| and_fprm_neural_mcts | direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | direct_anf | score | 2 | 8 | 2 | -5.44% |
| and_fprm_neural_mcts | and_direct_anf | T | 1 | 0 | 11 | -2.78% |
| and_fprm_neural_mcts | and_direct_anf | CNOT | 4 | 0 | 8 | -5.26% |
| and_fprm_neural_mcts | and_direct_anf | depth | 1 | 1 | 10 | -0.47% |
| and_fprm_neural_mcts | and_direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | and_direct_anf | score | 4 | 0 | 8 | -2.50% |
| and_fprm_neural_mcts | and_fprm_mcts | T | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | and_fprm_mcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | and_fprm_mcts | depth | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | and_fprm_mcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | and_fprm_mcts | score | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | sshr_h | T | 4 | 5 | 3 | +44.44% |
| and_fprm_neural_mcts | sshr_h | CNOT | 3 | 9 | 0 | +27.82% |
| and_fprm_neural_mcts | sshr_h | depth | 3 | 8 | 1 | +21.16% |
| and_fprm_neural_mcts | sshr_h | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_fprm_neural_mcts | sshr_h | score | 4 | 8 | 0 | +41.64% |
| and_fprm_mcts | sshr_h | T | 4 | 5 | 3 | +44.44% |
| and_fprm_mcts | sshr_h | CNOT | 3 | 9 | 0 | +27.82% |
| and_fprm_mcts | sshr_h | depth | 3 | 8 | 1 | +21.16% |
| and_fprm_mcts | sshr_h | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_fprm_mcts | sshr_h | score | 4 | 8 | 0 | +41.64% |

## Largest and-rc-nmcts gains vs direct ANF

| function | n | direct T | and_rc_nmcts T | relative |
|---|---:|---:|---:|---:|
| truth_n3_1 | 3 | 20 | 8 | -60.00% |
| anf_n5_3 | 5 | 28 | 20 | -28.57% |
| anf_n5_0 | 5 | 4 | 4 | +0.00% |
| anf_n5_1 | 5 | 4 | 4 | +0.00% |
| anf_n5_2 | 5 | 4 | 4 | +0.00% |
| majority_n3 | 3 | 12 | 12 | +0.00% |
| parity_n3 | 3 | 0 | 0 | +0.00% |
| parity_n4 | 4 | 0 | 0 | +0.00% |
| threshold2_n3 | 3 | 12 | 12 | +0.00% |
| truth_n3_0 | 3 | 8 | 8 | +0.00% |
| truth_n3_2 | 3 | 8 | 8 | +0.00% |
| truth_n3_3 | 3 | 12 | 12 | +0.00% |

## Largest and-fprm-neural-mcts gains vs direct ANF

| function | n | direct T | and_fprm_neural_mcts T | relative |
|---|---:|---:|---:|---:|
| truth_n3_1 | 3 | 20 | 8 | -60.00% |
| anf_n5_3 | 5 | 28 | 20 | -28.57% |
| anf_n5_0 | 5 | 4 | 4 | +0.00% |
| anf_n5_1 | 5 | 4 | 4 | +0.00% |
| anf_n5_2 | 5 | 4 | 4 | +0.00% |
| majority_n3 | 3 | 12 | 12 | +0.00% |
| parity_n3 | 3 | 0 | 0 | +0.00% |
| parity_n4 | 4 | 0 | 0 | +0.00% |
| threshold2_n3 | 3 | 12 | 12 | +0.00% |
| truth_n3_0 | 3 | 8 | 8 | +0.00% |
| truth_n3_2 | 3 | 8 | 8 | +0.00% |
| truth_n3_3 | 3 | 12 | 12 | +0.00% |

## Largest and-fprm-mcts gains vs direct ANF

| function | n | direct T | and_fprm_mcts T | relative |
|---|---:|---:|---:|---:|
| truth_n3_1 | 3 | 20 | 8 | -60.00% |
| anf_n5_3 | 5 | 28 | 20 | -28.57% |
| anf_n5_0 | 5 | 4 | 4 | +0.00% |
| anf_n5_1 | 5 | 4 | 4 | +0.00% |
| anf_n5_2 | 5 | 4 | 4 | +0.00% |
| majority_n3 | 3 | 12 | 12 | +0.00% |
| parity_n3 | 3 | 0 | 0 | +0.00% |
| parity_n4 | 4 | 0 | 0 | +0.00% |
| threshold2_n3 | 3 | 12 | 12 | +0.00% |
| truth_n3_0 | 3 | 8 | 8 | +0.00% |
| truth_n3_2 | 3 | 8 | 8 | +0.00% |
| truth_n3_3 | 3 | 12 | 12 | +0.00% |

## Largest fprm-mcts gains vs direct ANF

| function | n | direct T | fprm_mcts T | relative |
|---|---:|---:|---:|---:|
| truth_n3_1 | 3 | 20 | 12 | -40.00% |
| anf_n5_3 | 5 | 28 | 24 | -14.29% |
| anf_n5_0 | 5 | 4 | 4 | +0.00% |
| anf_n5_1 | 5 | 4 | 4 | +0.00% |
| anf_n5_2 | 5 | 4 | 4 | +0.00% |
| majority_n3 | 3 | 12 | 12 | +0.00% |
| parity_n3 | 3 | 0 | 0 | +0.00% |
| parity_n4 | 4 | 0 | 0 | +0.00% |
| threshold2_n3 | 3 | 12 | 12 | +0.00% |
| truth_n3_0 | 3 | 8 | 8 | +0.00% |
| truth_n3_2 | 3 | 8 | 8 | +0.00% |
| truth_n3_3 | 3 | 12 | 12 | +0.00% |

## and_rc_nmcts vs SSHR-H

| function | n | SSHR-H T | and_rc_nmcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| truth_n3_1 | 3 | 16 | 8 | -50.00% | 1 |
| anf_n5_3 | 5 | 24 | 20 | -16.67% | 1 |
| anf_n5_0 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_1 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_2 | 5 | 4 | 4 | +0.00% | 0 |
| truth_n3_0 | 3 | 4 | 8 | +100.00% | 0 |
| truth_n3_2 | 3 | 4 | 8 | +100.00% | 0 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |
| truth_n3_3 | 3 | 4 | 12 | +200.00% | 0 |

## and_fprm_neural_mcts vs SSHR-H

| function | n | SSHR-H T | and_fprm_neural_mcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| truth_n3_1 | 3 | 16 | 8 | -50.00% | 1 |
| anf_n5_3 | 5 | 24 | 20 | -16.67% | 1 |
| anf_n5_0 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_1 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_2 | 5 | 4 | 4 | +0.00% | 0 |
| truth_n3_0 | 3 | 4 | 8 | +100.00% | 0 |
| truth_n3_2 | 3 | 4 | 8 | +100.00% | 0 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |
| truth_n3_3 | 3 | 4 | 12 | +200.00% | 0 |

## and_fprm_mcts vs SSHR-H

| function | n | SSHR-H T | and_fprm_mcts T | relative | peak ancilla |
|---|---:|---:|---:|---:|---:|
| parity_n3 | 3 | 8 | 0 | -100.00% | 0 |
| parity_n4 | 4 | 8 | 0 | -100.00% | 0 |
| truth_n3_1 | 3 | 16 | 8 | -50.00% | 1 |
| anf_n5_3 | 5 | 24 | 20 | -16.67% | 1 |
| anf_n5_0 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_1 | 5 | 4 | 4 | +0.00% | 0 |
| anf_n5_2 | 5 | 4 | 4 | +0.00% | 0 |
| truth_n3_0 | 3 | 4 | 8 | +100.00% | 0 |
| truth_n3_2 | 3 | 4 | 8 | +100.00% | 0 |
| majority_n3 | 3 | 4 | 12 | +200.00% | 0 |
| threshold2_n3 | 3 | 4 | 12 | +200.00% | 0 |
| truth_n3_3 | 3 | 4 | 12 | +200.00% | 0 |
