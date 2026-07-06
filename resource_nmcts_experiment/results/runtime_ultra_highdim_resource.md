# Runtime and Resource Tradeoff: ultra_highdim_resource

Rows: 168; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 24 | 0 | 0 | 0.060 | 0.062 | 0.064 | 1.5 |
| AND-direct ANF | 24 | 0 | 0 | 0.060 | 0.061 | 0.061 | 1.4 |
| FPRM root beam | 24 | 0 | 0 | 5.935 | 21.194 | 31.908 | 202.9 |
| FPRM linear pair | 24 | 0 | 0 | 8.026 | 30.185 | 42.638 | 269.2 |
| Resource-NMCTS | 24 | 0 | 0 | 7.880 | 27.830 | 41.721 | 266.0 |
| Profile-Resource-NMCTS | 24 | 0 | 0 | 8.426 | 29.765 | 44.915 | 281.4 |
| Pareto-Resource-NMCTS | 24 | 0 | 0 | 130.923 | 301.097 | 303.565 | 3627.6 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 24 | 12053.67 | 5616.00 | 5616.12 | 1.38 | 12369.50 |
| AND-direct ANF | 24 | 6047.67 | 9491.17 | 9491.29 | 2.29 | 6608.70 |
| FPRM root beam | 24 | 3822.33 | 6613.50 | 6613.62 | 2.29 | 4216.21 |
| FPRM linear pair | 24 | 3759.67 | 6501.33 | 6501.46 | 3.21 | 4148.75 |
| Resource-NMCTS | 24 | 3759.67 | 6501.33 | 6501.46 | 3.21 | 4148.75 |
| Profile-Resource-NMCTS | 24 | 3759.67 | 6501.33 | 6501.46 | 3.21 | 4148.75 |
| Pareto-Resource-NMCTS | 24 | 3756.33 | 6504.17 | 6504.29 | 3.21 | 4145.59 |
