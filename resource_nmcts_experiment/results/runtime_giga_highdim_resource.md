# Runtime and Resource Tradeoff: giga_highdim_resource

Rows: 42; errors: 12; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 6 | 0 | 0 | 10.518 | 10.579 | 10.583 | 63.1 |
| AND-direct ANF | 6 | 0 | 0 | 10.490 | 10.503 | 10.506 | 63.0 |
| FPRM root beam | 0 | 6 | 0 | -- | -- | -- | -- |
| FPRM linear-pair fast | 0 | 6 | 0 | -- | -- | -- | -- |
| Resource-NMCTS | 6 | 0 | 0 | 300.006 | 300.007 | 300.007 | 1800.0 |
| Profile-Resource-NMCTS | 6 | 0 | 0 | 299.999 | 300.005 | 300.005 | 1800.0 |
| Pareto-Resource-NMCTS | 6 | 0 | 0 | 299.998 | 300.007 | 300.007 | 1800.0 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 6 | 42944.00 | 19600.33 | 19600.33 | 1.00 | 44037.63 |
| AND-direct ANF | 6 | 21516.67 | 33635.67 | 33635.67 | 1.67 | 23491.15 |
| FPRM root beam | 0 | -- | -- | -- | -- | -- |
| FPRM linear-pair fast | 0 | -- | -- | -- | -- | -- |
| Resource-NMCTS | 6 | 21516.67 | 33635.67 | 33635.67 | 1.67 | 23491.15 |
| Profile-Resource-NMCTS | 6 | 21516.67 | 33635.67 | 33635.67 | 1.67 | 23491.15 |
| Pareto-Resource-NMCTS | 6 | 21516.67 | 33635.67 | 33635.67 | 1.67 | 23491.15 |

## Timeout / error rows

| function | n | method | error |
|---|---:|---|---|
| anf_n20_0 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_1 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_2 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_3 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_4 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_5 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_0 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_1 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_2 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_3 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_4 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_5 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
