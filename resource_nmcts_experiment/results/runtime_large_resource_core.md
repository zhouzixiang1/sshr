# Runtime and Resource Tradeoff: large_resource_core

Rows: 1650; errors: 5; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 330 | 0 | 0 | 0.000 | 0.010 | 0.028 | 0.5 |
| AND-direct ANF | 330 | 0 | 0 | 0.000 | 0.011 | 0.053 | 0.6 |
| Fixed MCTS | 325 | 5 | 0 | 0.103 | 71.544 | 273.952 | 3425.5 |
| Affine-NMCTS | 330 | 0 | 0 | 0.719 | 120.451 | 300.420 | 5271.0 |
| Resource-NMCTS | 330 | 0 | 0 | 1.311 | 58.857 | 300.848 | 3146.9 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 330 | 809.31 | 422.82 | 423.06 | 1.28 | 835.48 |
| AND-direct ANF | 330 | 413.30 | 655.41 | 655.66 | 2.14 | 456.05 |
| Fixed MCTS | 325 | 215.16 | 399.35 | 399.60 | 1.89 | 242.51 |
| Affine-NMCTS | 330 | 245.30 | 448.90 | 451.00 | 1.95 | 275.73 |
| Resource-NMCTS | 330 | 243.38 | 447.04 | 449.51 | 1.95 | 273.72 |

## Timeout / error rows

| function | n | method | error |
|---|---:|---|---|
| anf_n12_30 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_31 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_40 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_42 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
| anf_n12_46 | 12 | and_mcts_factor | TaskTimeout('synthesis task timed out') |
