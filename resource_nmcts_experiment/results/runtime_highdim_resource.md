# Runtime and Resource Tradeoff: highdim_resource

Rows: 448; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 0 | 0 | 0.017 | 0.056 | 0.083 | 1.3 |
| AND-direct ANF | 64 | 0 | 0 | 0.019 | 0.042 | 0.066 | 1.4 |
| FPRM-greedy | 64 | 0 | 0 | 3.464 | 65.991 | 85.556 | 969.6 |
| FPRM root beam | 64 | 0 | 0 | 2.081 | 25.413 | 33.181 | 367.4 |
| Affine-greedy | 64 | 0 | 0 | 6.647 | 107.887 | 129.176 | 1696.2 |
| Resource-NMCTS | 64 | 0 | 0 | 3.519 | 36.896 | 88.982 | 609.9 |
| Profile-Resource-NMCTS | 64 | 0 | 0 | 4.027 | 59.688 | 78.236 | 733.7 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 7159.38 | 3381.06 | 3381.20 | 1.22 | 7350.23 |
| AND-direct ANF | 64 | 3597.62 | 5642.02 | 5642.16 | 2.03 | 3932.45 |
| FPRM-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| FPRM root beam | 64 | 2250.19 | 3886.28 | 3886.42 | 2.03 | 2482.99 |
| Affine-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| Resource-NMCTS | 64 | 2250.19 | 3886.28 | 3886.42 | 2.03 | 2482.99 |
| Profile-Resource-NMCTS | 64 | 2250.19 | 3886.28 | 3886.42 | 2.03 | 2482.99 |
