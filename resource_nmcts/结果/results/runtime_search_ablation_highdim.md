# Runtime and Resource Tradeoff: search_ablation_highdim

Rows: 128; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 16 | 0 | 0 | 0.008 | 0.009 | 0.009 | 0.1 |
| AND-direct ANF | 16 | 0 | 0 | 0.008 | 0.009 | 0.009 | 0.1 |
| FPRM-greedy | 16 | 0 | 0 | 3.281 | 20.964 | 21.122 | 98.6 |
| FPRM root beam | 16 | 0 | 0 | 3.648 | 27.874 | 28.359 | 120.4 |
| FPRM linear pair | 16 | 0 | 0 | 4.234 | 37.446 | 39.005 | 159.2 |
| Heuristic-only portfolio | 16 | 0 | 0 | 2.941 | 20.048 | 20.134 | 96.0 |
| Beam-only portfolio | 16 | 0 | 0 | 7.062 | 59.137 | 61.501 | 251.9 |
| No-MCTS portfolio | 16 | 0 | 0 | 21.770 | 98.450 | 105.322 | 566.4 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 16 | 10371.75 | 4788.19 | 4788.31 | 1.31 | 10641.17 |
| AND-direct ANF | 16 | 5204.50 | 8151.12 | 8151.25 | 2.25 | 5686.78 |
| FPRM-greedy | 16 | 3231.00 | 5541.19 | 5541.31 | 2.25 | 3561.57 |
| FPRM root beam | 16 | 3220.00 | 5537.75 | 5537.88 | 2.25 | 3550.39 |
| FPRM linear pair | 16 | 3135.75 | 5395.50 | 5396.00 | 3.12 | 3459.50 |
| Heuristic-only portfolio | 16 | 3231.00 | 5541.19 | 5541.31 | 2.25 | 3561.57 |
| Beam-only portfolio | 16 | 3135.75 | 5395.50 | 5396.00 | 3.12 | 3459.50 |
| No-MCTS portfolio | 16 | 3081.75 | 5312.56 | 5314.62 | 3.25 | 3400.92 |
