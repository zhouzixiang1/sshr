# RL-MCTS Block Experiment Results

| n | method | functions | correct | total CNOT | mean CNOT | median CNOT | mean time (s) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | beam | 255 | 255 | 3652 | 14.32 | 14.00 | 0.0002 |
| 3 | mcts_rollout | 255 | 255 | 3652 | 14.32 | 14.00 | 0.0014 |
| 3 | pv_greedy | 255 | 255 | 3668 | 14.38 | 14.00 | 0.0002 |
| 3 | pv_greedy_lookahead | 255 | 255 | 3652 | 14.32 | 14.00 | 0.0002 |
| 3 | pv_mcts | 255 | 255 | 3652 | 14.32 | 14.00 | 0.0008 |
| 3 | sshr_h | 255 | 255 | 3191 | 12.51 | 14.00 | 0.0000 |
| 3 | sshr_h_literal | 255 | 255 | 3788 | 14.85 | 15.00 | 0.0000 |
| 3 | xor_beam_best | 255 | 255 | 3024 | 11.86 | 14.00 | 0.0011 |
| 3 | xor_beam_rule | 255 | 255 | 3024 | 11.86 | 14.00 | 0.0003 |
| 3 | xor_beam_v2 | 255 | 255 | 3000 | 11.76 | 14.00 | 0.0007 |
| 4 | beam | 1024 | 1024 | 30369 | 29.66 | 30.00 | 0.0016 |
| 4 | mcts_rollout | 1024 | 1024 | 30369 | 29.66 | 30.00 | 0.0030 |
| 4 | pv_greedy | 1024 | 1024 | 30605 | 29.89 | 30.00 | 0.0014 |
| 4 | pv_greedy_lookahead | 1024 | 1024 | 30369 | 29.66 | 30.00 | 0.0017 |
| 4 | pv_mcts | 1024 | 1024 | 30369 | 29.66 | 30.00 | 0.0029 |
| 4 | sshr_h | 1024 | 1024 | 26622 | 26.00 | 26.00 | 0.0001 |
| 4 | sshr_h_literal | 1024 | 1024 | 31759 | 31.01 | 32.00 | 0.0000 |
| 4 | xor_beam_best | 1024 | 1024 | 23161 | 22.62 | 24.00 | 0.0047 |
| 4 | xor_beam_rule | 1024 | 1024 | 23161 | 22.62 | 24.00 | 0.0020 |
| 4 | xor_beam_v2 | 1024 | 1024 | 22792 | 22.26 | 24.00 | 0.0023 |
| 5 | beam | 256 | 256 | 11436 | 44.67 | 46.00 | 0.0188 |
| 5 | mcts_rollout | 256 | 256 | 11448 | 44.72 | 46.00 | 0.0187 |
| 5 | pv_greedy | 256 | 256 | 11622 | 45.40 | 47.00 | 0.0148 |
| 5 | pv_greedy_lookahead | 256 | 256 | 11422 | 44.62 | 46.00 | 0.0294 |
| 5 | pv_mcts | 256 | 256 | 11420 | 44.61 | 46.00 | 0.0349 |
| 5 | sshr_h | 256 | 256 | 13972 | 54.58 | 59.50 | 0.0008 |
| 5 | sshr_h_literal | 256 | 256 | 12368 | 48.31 | 50.00 | 0.0003 |
| 5 | xor_beam_best | 256 | 256 | 10123 | 39.54 | 42.00 | 0.0823 |
| 5 | xor_beam_rule | 256 | 256 | 10164 | 39.70 | 42.00 | 0.0397 |
| 5 | xor_beam_v2 | 256 | 256 | 10115 | 39.51 | 42.00 | 0.0160 |
| 6 | beam | 48 | 48 | 3552 | 74.00 | 78.00 | 0.2410 |
| 6 | mcts_rollout | 48 | 48 | 3634 | 75.71 | 78.00 | 0.1952 |
| 6 | pv_greedy | 48 | 48 | 3820 | 79.58 | 82.00 | 0.1832 |
| 6 | pv_greedy_lookahead | 48 | 48 | 3564 | 74.25 | 78.00 | 0.4452 |
| 6 | pv_mcts | 48 | 48 | 3558 | 74.12 | 78.00 | 0.5728 |
| 6 | sshr_h | 48 | 48 | 4564 | 95.08 | 101.00 | 0.0117 |
| 6 | sshr_h_literal | 48 | 48 | 4058 | 84.54 | 92.00 | 0.0017 |
| 6 | xor_beam_best | 48 | 48 | 3282 | 68.38 | 75.00 | 1.9161 |
| 6 | xor_beam_rule | 48 | 48 | 3306 | 68.88 | 75.00 | 0.9490 |
| 6 | xor_beam_v2 | 48 | 48 | 3508 | 73.08 | 83.00 | 0.1643 |

## Relative Comparisons

| n | comparison | delta total CNOT | relative |
|---:|---|---:|---:|
| 3 | pv_mcts vs pv_greedy | -16 | -0.44% |
| 3 | pv_mcts vs pv_greedy_lookahead | +0 | +0.00% |
| 3 | pv_mcts vs beam | +0 | +0.00% |
| 3 | pv_mcts vs mcts_rollout | +0 | +0.00% |
| 3 | pv_mcts vs xor_beam_rule | +628 | +20.77% |
| 3 | pv_mcts vs xor_beam_v2 | +652 | +21.73% |
| 3 | pv_mcts vs xor_beam_best | +628 | +20.77% |
| 3 | pv_mcts vs sshr_h | +461 | +14.45% |
| 4 | pv_mcts vs pv_greedy | -236 | -0.77% |
| 4 | pv_mcts vs pv_greedy_lookahead | +0 | +0.00% |
| 4 | pv_mcts vs beam | +0 | +0.00% |
| 4 | pv_mcts vs mcts_rollout | +0 | +0.00% |
| 4 | pv_mcts vs xor_beam_rule | +7208 | +31.12% |
| 4 | pv_mcts vs xor_beam_v2 | +7577 | +33.24% |
| 4 | pv_mcts vs xor_beam_best | +7208 | +31.12% |
| 4 | pv_mcts vs sshr_h | +3747 | +14.07% |
| 5 | pv_mcts vs pv_greedy | -202 | -1.74% |
| 5 | pv_mcts vs pv_greedy_lookahead | -2 | -0.02% |
| 5 | pv_mcts vs beam | -16 | -0.14% |
| 5 | pv_mcts vs mcts_rollout | -28 | -0.24% |
| 5 | pv_mcts vs xor_beam_rule | +1256 | +12.36% |
| 5 | pv_mcts vs xor_beam_v2 | +1305 | +12.90% |
| 5 | pv_mcts vs xor_beam_best | +1297 | +12.81% |
| 5 | pv_mcts vs sshr_h | -2552 | -18.27% |
| 6 | pv_mcts vs pv_greedy | -262 | -6.86% |
| 6 | pv_mcts vs pv_greedy_lookahead | -6 | -0.17% |
| 6 | pv_mcts vs beam | +6 | +0.17% |
| 6 | pv_mcts vs mcts_rollout | -76 | -2.09% |
| 6 | pv_mcts vs xor_beam_rule | +252 | +7.62% |
| 6 | pv_mcts vs xor_beam_v2 | +50 | +1.43% |
| 6 | pv_mcts vs xor_beam_best | +276 | +8.41% |
| 6 | pv_mcts vs sshr_h | -1006 | -22.04% |
