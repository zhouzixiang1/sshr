# Runtime and Resource Tradeoff: mega_highdim_resource

Rows: 60; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 12 | 0 | 0 | 0.719 | 0.730 | 0.735 | 8.7 |
| AND-direct ANF | 12 | 0 | 0 | 0.721 | 0.726 | 0.728 | 8.7 |
| FPRM root beam | 12 | 0 | 0 | 65.110 | 141.049 | 162.158 | 836.3 |
| Resource-NMCTS | 12 | 0 | 0 | 65.936 | 144.940 | 168.272 | 864.6 |
| Profile-Resource-NMCTS | 12 | 0 | 0 | 66.864 | 148.401 | 171.081 | 870.6 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 12 | 21460.67 | 9794.67 | 9794.75 | 1.25 | 22008.94 |
| AND-direct ANF | 12 | 10756.00 | 16840.50 | 16840.58 | 2.17 | 11747.41 |
| FPRM root beam | 12 | 6765.33 | 11585.17 | 11585.25 | 2.17 | 7451.30 |
| Resource-NMCTS | 12 | 6765.33 | 11585.17 | 11585.25 | 2.17 | 7451.30 |
| Profile-Resource-NMCTS | 12 | 6765.33 | 11585.17 | 11585.25 | 2.17 | 7451.30 |
