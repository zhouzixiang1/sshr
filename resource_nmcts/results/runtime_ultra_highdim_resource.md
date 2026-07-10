# Runtime and Resource Tradeoff: ultra_highdim_resource

Rows: 240; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 24 | 0 | 0 | 0.060 | 0.062 | 0.064 | 1.5 |
| AND-direct ANF | 24 | 0 | 0 | 0.060 | 0.061 | 0.061 | 1.4 |
| FPRM root beam | 24 | 0 | 0 | 5.935 | 21.194 | 31.908 | 202.9 |
| FPRM linear pair | 24 | 0 | 0 | 8.026 | 30.185 | 42.638 | 269.2 |
| FPRM linear pair deep | 24 | 0 | 0 | 22.856 | 59.493 | 84.913 | 668.3 |
| FPRM deep root-neural | 24 | 0 | 0 | 23.982 | 60.879 | 84.750 | 687.4 |
| FPRM deep AI guard | 24 | 0 | 0 | 54.138 | 146.697 | 215.235 | 1614.1 |
| Resource-NMCTS | 24 | 0 | 0 | 80.633 | 227.312 | 300.012 | 2449.6 |
| Profile-Resource-NMCTS | 24 | 0 | 0 | 71.084 | 195.863 | 275.318 | 2166.8 |
| Pareto-Resource-NMCTS | 24 | 0 | 0 | 146.767 | 300.829 | 301.025 | 3926.4 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 24 | 12053.67 | 5616.00 | 5616.12 | 1.38 | 12369.50 |
| AND-direct ANF | 24 | 6047.67 | 9491.17 | 9491.29 | 2.29 | 6608.70 |
| FPRM root beam | 24 | 3822.33 | 6613.50 | 6613.62 | 2.29 | 4216.21 |
| FPRM linear pair | 24 | 3759.67 | 6501.33 | 6501.46 | 3.21 | 4148.75 |
| FPRM linear pair deep | 24 | 3700.33 | 6404.50 | 6404.62 | 3.38 | 4084.05 |
| FPRM deep root-neural | 24 | 3705.33 | 6415.25 | 6415.38 | 3.42 | 4089.77 |
| FPRM deep AI guard | 24 | 3699.17 | 6404.42 | 6404.54 | 3.42 | 4082.97 |
| Resource-NMCTS | 24 | 3699.17 | 6404.42 | 6404.54 | 3.42 | 4082.97 |
| Profile-Resource-NMCTS | 24 | 3699.17 | 6404.42 | 6404.54 | 3.42 | 4082.97 |
| Pareto-Resource-NMCTS | 24 | 3699.83 | 6406.08 | 6406.21 | 3.38 | 4083.64 |
