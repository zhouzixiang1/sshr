# Experiment Analysis

All rows in `raw_main.csv` passed circuit simulation; no method produced an incorrect circuit.

## Best Method By n

| n | best method | total CNOT | vs SSHR-H | vs Beam |
|---:|---|---:|---:|---:|
| 3 | XOR-Beam-v2 | 3000 | -5.99% | -17.85% |
| 4 | XOR-Beam-v2 | 22792 | -14.39% | -24.95% |
| 5 | XOR-Beam-v2 | 10115 | -27.61% | -11.55% |
| 6 | XOR-Beam-best | 3282 | -28.09% | -7.60% |

## PV-MCTS Family

| n | PV-MCTS vs PV-Greedy | PV-MCTS vs Beam | PV-MCTS vs Rollout-MCTS |
|---:|---:|---:|---:|
| 3 | -0.44% | +0.00% | +0.00% |
| 4 | -0.77% | +0.00% | +0.00% |
| 5 | -1.74% | -0.14% | -0.24% |
| 6 | -6.86% | +0.17% | -2.09% |
