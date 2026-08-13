# Runtime and Resource Tradeoff: traditional_resource

Rows: 1770; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.0 |
| AND-direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.0 |
| Fixed MCTS | 177 | 0 | 0 | 0.047 | 0.667 | 1.352 | 25.8 |
| Affine-NMCTS | 177 | 0 | 0 | 0.585 | 3.976 | 4.728 | 256.1 |
| Resource-NMCTS | 177 | 0 | 0 | 0.351 | 0.904 | 1.369 | 71.5 |
| Polarity archive | 177 | 0 | 0 | 0.060 | 0.765 | 0.946 | 30.5 |
| Pareto-Resource-NMCTS | 177 | 0 | 0 | 4.147 | 9.782 | 15.445 | 703.1 |
| ESOP cube beam | 177 | 0 | 0 | 0.008 | 0.063 | 0.101 | 2.9 |
| ESOP MILP | 177 | 0 | 0 | 1.239 | 10.015 | 10.029 | 670.5 |
| SSHR-H | 177 | 0 | 0 | 0.003 | 0.109 | 0.440 | 5.2 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 184.09 | 134.19 | 134.65 | 1.33 | 194.29 |
| AND-direct ANF | 177 | 100.99 | 166.47 | 166.93 | 2.18 | 115.17 |
| Fixed MCTS | 177 | 62.06 | 124.33 | 124.79 | 1.82 | 73.09 |
| Affine-NMCTS | 177 | 45.88 | 94.36 | 98.92 | 1.88 | 55.37 |
| Resource-NMCTS | 177 | 43.91 | 89.85 | 94.51 | 1.92 | 53.22 |
| Polarity archive | 177 | 43.01 | 86.85 | 91.49 | 2.11 | 52.50 |
| Pareto-Resource-NMCTS | 177 | 40.43 | 83.04 | 88.00 | 2.03 | 49.56 |
| ESOP cube beam | 177 | 71.32 | 115.28 | 139.51 | 2.55 | 83.82 |
| ESOP MILP | 177 | 83.59 | 133.51 | 159.56 | 2.32 | 96.73 |
| SSHR-H | 177 | 81.04 | 67.56 | 88.70 | 1.36 | 88.19 |
