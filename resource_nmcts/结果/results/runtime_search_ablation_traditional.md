# Runtime and Resource Tradeoff: search_ablation_traditional

Rows: 2301; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.001 | 0.0 |
| AND-direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.004 | 0.0 |
| FPRM-greedy | 177 | 0 | 0 | 0.003 | 0.027 | 0.107 | 1.2 |
| FPRM root beam | 177 | 0 | 0 | 0.005 | 0.099 | 0.251 | 3.5 |
| FPRM linear pair | 177 | 0 | 0 | 0.020 | 0.274 | 0.679 | 11.5 |
| Fixed MCTS | 177 | 0 | 0 | 0.006 | 0.133 | 0.350 | 4.9 |
| Affine-greedy | 177 | 0 | 0 | 0.018 | 0.105 | 0.249 | 4.8 |
| Affine-NMCTS | 177 | 0 | 0 | 0.176 | 1.111 | 1.520 | 66.5 |
| Heuristic-only portfolio | 177 | 0 | 0 | 0.021 | 0.098 | 0.271 | 5.5 |
| Beam-only portfolio | 177 | 0 | 0 | 0.029 | 0.491 | 0.669 | 17.5 |
| No-MCTS portfolio | 177 | 0 | 0 | 0.065 | 0.544 | 0.871 | 25.4 |
| Resource-NMCTS | 177 | 0 | 0 | 0.381 | 0.922 | 1.208 | 74.6 |
| Pareto-Resource-NMCTS | 177 | 0 | 0 | 4.174 | 9.942 | 15.723 | 711.3 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 184.09 | 134.19 | 134.65 | 1.33 | 194.29 |
| AND-direct ANF | 177 | 100.99 | 166.47 | 166.93 | 2.18 | 115.17 |
| FPRM-greedy | 177 | 54.37 | 104.93 | 109.59 | 2.00 | 64.71 |
| FPRM root beam | 177 | 52.50 | 103.12 | 107.64 | 1.86 | 62.44 |
| FPRM linear pair | 177 | 47.41 | 94.46 | 99.16 | 2.07 | 57.28 |
| Fixed MCTS | 177 | 62.06 | 124.33 | 124.79 | 1.82 | 73.09 |
| Affine-greedy | 177 | 46.82 | 95.75 | 100.75 | 1.99 | 56.63 |
| Affine-NMCTS | 177 | 45.88 | 94.36 | 98.92 | 1.88 | 55.37 |
| Heuristic-only portfolio | 177 | 46.69 | 95.28 | 100.30 | 1.99 | 56.46 |
| Beam-only portfolio | 177 | 47.41 | 94.04 | 99.00 | 2.07 | 57.26 |
| No-MCTS portfolio | 177 | 44.41 | 90.38 | 95.34 | 1.99 | 53.90 |
| Resource-NMCTS | 177 | 43.91 | 89.85 | 94.51 | 1.92 | 53.22 |
| Pareto-Resource-NMCTS | 177 | 40.43 | 83.04 | 88.00 | 2.03 | 49.56 |
