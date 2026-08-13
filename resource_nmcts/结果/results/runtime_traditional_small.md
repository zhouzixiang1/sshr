# Runtime and Resource Tradeoff: traditional_small

Rows: 1239; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.0 |
| AND-direct ANF | 177 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.0 |
| Fixed MCTS | 177 | 0 | 0 | 0.048 | 0.672 | 1.286 | 25.5 |
| Affine-NMCTS | 177 | 0 | 0 | 0.589 | 3.952 | 4.700 | 253.4 |
| ESOP cube beam | 177 | 0 | 0 | 0.008 | 0.062 | 0.075 | 2.9 |
| ESOP MILP | 177 | 0 | 0 | 1.228 | 10.020 | 10.039 | 670.1 |
| SSHR-H | 177 | 0 | 0 | 0.003 | 0.347 | 0.442 | 5.6 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 184.09 | 134.19 | 134.65 | 1.33 | 194.29 |
| AND-direct ANF | 177 | 100.99 | 166.47 | 166.93 | 2.18 | 115.17 |
| Fixed MCTS | 177 | 62.06 | 124.33 | 124.79 | 1.82 | 73.09 |
| Affine-NMCTS | 177 | 45.88 | 94.36 | 98.92 | 1.88 | 55.37 |
| ESOP cube beam | 177 | 71.32 | 115.28 | 139.51 | 2.55 | 83.82 |
| ESOP MILP | 177 | 83.55 | 133.46 | 159.54 | 2.32 | 96.67 |
| SSHR-H | 177 | 81.04 | 67.56 | 88.70 | 1.36 | 88.19 |
