# Runtime and Resource Tradeoff: ablation_affine

Rows: 2254; errors: 1; skipped: 145.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 322 | 0 | 0 | 0.000 | 0.004 | 0.013 | 0.2 |
| AND-direct ANF | 322 | 0 | 0 | 0.000 | 0.004 | 0.012 | 0.2 |
| Fixed MCTS | 321 | 1 | 0 | 0.076 | 12.256 | 89.897 | 898.9 |
| Affine-greedy | 322 | 0 | 0 | 0.033 | 0.228 | 1.825 | 23.3 |
| Affine-no-guard | 322 | 0 | 0 | 0.093 | 3.620 | 4.851 | 207.4 |
| Affine-NMCTS | 322 | 0 | 0 | 0.609 | 13.670 | 300.025 | 1482.9 |
| SSHR-H | 177 | 0 | 145 | 0.003 | 0.124 | 0.704 | 6.4 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 322 | 491.88 | 275.16 | 275.44 | 1.28 | 509.82 |
| AND-direct ANF | 322 | 254.06 | 405.82 | 406.10 | 2.11 | 282.12 |
| Fixed MCTS | 321 | 155.17 | 291.43 | 291.71 | 1.85 | 176.09 |
| Affine-greedy | 322 | 154.09 | 280.80 | 283.58 | 1.99 | 174.72 |
| Affine-no-guard | 322 | 153.75 | 280.26 | 282.95 | 1.93 | 174.24 |
| Affine-NMCTS | 322 | 145.39 | 272.73 | 275.39 | 1.89 | 165.34 |
| SSHR-H | 177 | 81.04 | 67.56 | 88.70 | 1.36 | 88.19 |

## Timeout / error rows

| function | n | method | error |
|---|---:|---|---|
| anf_n12_10 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
