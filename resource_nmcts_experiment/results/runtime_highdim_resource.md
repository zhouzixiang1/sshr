# Runtime and Resource Tradeoff: highdim_resource

Rows: 448; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 0 | 0 | 0.017 | 0.056 | 0.083 | 1.3 |
| AND-direct ANF | 64 | 0 | 0 | 0.019 | 0.042 | 0.066 | 1.4 |
| FPRM-greedy | 64 | 0 | 0 | 3.464 | 65.991 | 85.556 | 969.6 |
| FPRM root beam | 64 | 0 | 0 | 2.710 | 26.119 | 32.879 | 394.4 |
| Affine-greedy | 64 | 0 | 0 | 6.647 | 107.887 | 129.176 | 1696.2 |
| Resource-NMCTS | 64 | 0 | 0 | 5.134 | 38.834 | 49.301 | 651.6 |
| Profile-Resource-NMCTS | 64 | 0 | 0 | 5.116 | 38.586 | 49.042 | 638.8 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 7159.38 | 3381.06 | 3381.20 | 1.22 | 7350.23 |
| AND-direct ANF | 64 | 3597.62 | 5642.02 | 5642.16 | 2.03 | 3932.45 |
| FPRM-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| FPRM root beam | 64 | 2253.62 | 3887.70 | 3887.84 | 2.03 | 2486.51 |
| Affine-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| Resource-NMCTS | 64 | 2253.62 | 3887.70 | 3887.84 | 2.03 | 2486.51 |
| Profile-Resource-NMCTS | 64 | 2253.62 | 3887.70 | 3887.84 | 2.03 | 2486.51 |
