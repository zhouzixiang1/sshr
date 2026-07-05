# Smoke Analysis

Rows: 72; usable: 72; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| fprm_mcts | 12 | -4.52% | -40.00% | +0.00% |
| greedy_factor | 12 | -3.33% | -40.00% | +0.00% |
| mcts_factor | 12 | -3.33% | -40.00% | +0.00% |
| neural_mcts | 12 | -3.33% | -40.00% | +0.00% |
| sshr_h | 12 | +105.48% | -66.67% | +800.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|
| fprm_mcts | 3 | 9 | +47.92% |
| greedy_factor | 3 | 9 | +49.31% |
| mcts_factor | 3 | 9 | +49.31% |
| neural_mcts | 3 | 9 | +49.31% |
| sshr_h | 0 | 12 | +0.00% |

## Largest FPRM-MCTS gains vs direct ANF

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
