# Runtime and Resource Tradeoff: mega_highdim_resource

Rows: 84; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 12 | 0 | 0 | 0.719 | 0.730 | 0.735 | 8.7 |
| AND-direct ANF | 12 | 0 | 0 | 0.721 | 0.726 | 0.728 | 8.7 |
| FPRM root beam | 12 | 0 | 0 | 65.110 | 141.049 | 162.158 | 836.3 |
| FPRM linear-pair fast | 12 | 0 | 0 | 65.476 | 138.670 | 160.915 | 833.3 |
| Resource-NMCTS | 12 | 0 | 0 | 83.313 | 173.181 | 205.101 | 1027.6 |
| Profile-Resource-NMCTS | 12 | 0 | 0 | 83.339 | 173.780 | 205.328 | 1028.9 |
| Pareto-Resource-NMCTS | 12 | 0 | 0 | 83.500 | 172.934 | 205.443 | 1027.4 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 12 | 21460.67 | 9794.67 | 9794.75 | 1.25 | 22008.94 |
| AND-direct ANF | 12 | 10756.00 | 16840.50 | 16840.58 | 2.17 | 11747.41 |
| FPRM root beam | 12 | 6765.33 | 11585.17 | 11585.25 | 2.17 | 7451.30 |
| FPRM linear-pair fast | 12 | 6754.00 | 11566.83 | 11568.42 | 2.67 | 7439.93 |
| Resource-NMCTS | 12 | 6641.67 | 11382.42 | 11383.67 | 3.25 | 7317.88 |
| Profile-Resource-NMCTS | 12 | 6641.67 | 11382.42 | 11383.67 | 3.25 | 7317.88 |
| Pareto-Resource-NMCTS | 12 | 6641.67 | 11382.42 | 11383.67 | 3.25 | 7317.88 |
