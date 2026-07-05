# Pilot Analysis

Rows: 210; usable: 197; errors: 0; skipped: 13.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| fprm_greedy | 30 | -24.09% | -63.60% | +0.00% |
| fprm_mcts | 30 | -26.23% | -68.62% | +0.00% |
| greedy_factor | 30 | -20.96% | -50.00% | +0.00% |
| mcts_factor | 30 | -23.18% | -60.78% | +0.00% |
| neural_mcts | 30 | -23.18% | -60.78% | +0.00% |
| sshr_h | 17 | +1211.75% | -72.94% | +9600.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|
| fprm_greedy | 8 | 9 | +9.98% |
| fprm_mcts | 8 | 9 | +8.45% |
| greedy_factor | 8 | 9 | +17.63% |
| mcts_factor | 8 | 9 | +16.35% |
| neural_mcts | 8 | 9 | +16.35% |
| sshr_h | 0 | 17 | +0.00% |

## Largest FPRM-MCTS gains vs direct ANF

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
