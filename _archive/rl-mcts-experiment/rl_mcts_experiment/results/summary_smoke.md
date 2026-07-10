# RL-MCTS Block Experiment Results

| n | method | functions | correct | total CNOT | mean CNOT | median CNOT | mean time (s) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | beam | 16 | 16 | 215 | 13.44 | 14.00 | 0.0002 |
| 3 | pv_greedy | 16 | 16 | 219 | 13.69 | 14.00 | 0.0002 |
| 3 | pv_greedy_lookahead | 16 | 16 | 215 | 13.44 | 14.00 | 0.0002 |
| 3 | pv_mcts | 16 | 16 | 215 | 13.44 | 14.00 | 0.0005 |
| 3 | sshr_h | 16 | 16 | 183 | 11.44 | 12.00 | 0.0000 |
| 3 | xor_beam_rule | 16 | 16 | 181 | 11.31 | 12.00 | 0.0001 |

## Relative Comparisons

| n | comparison | delta total CNOT | relative |
|---:|---|---:|---:|
| 3 | pv_mcts vs pv_greedy | -4 | -1.83% |
| 3 | pv_mcts vs pv_greedy_lookahead | +0 | +0.00% |
| 3 | pv_mcts vs beam | +0 | +0.00% |
| 3 | pv_mcts vs xor_beam_rule | +34 | +18.78% |
| 3 | pv_mcts vs sshr_h | +32 | +17.49% |
