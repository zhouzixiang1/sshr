# Runtime and Resource Tradeoff: highdim_resource

Rows: 448; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 0 | 0 | 0.017 | 0.056 | 0.083 | 1.3 |
| AND-direct ANF | 64 | 0 | 0 | 0.019 | 0.042 | 0.066 | 1.4 |
| FPRM-greedy | 64 | 0 | 0 | 3.464 | 65.991 | 85.556 | 969.6 |
| FPRM root beam | 64 | 0 | 0 | 2.834 | 37.226 | 49.268 | 542.6 |
| Affine-greedy | 64 | 0 | 0 | 6.647 | 107.887 | 129.176 | 1696.2 |
| Resource-NMCTS | 64 | 0 | 0 | 5.048 | 49.063 | 64.263 | 778.4 |
| Profile-Resource-NMCTS | 64 | 0 | 0 | 6.076 | 58.867 | 87.619 | 901.1 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 7159.38 | 3381.06 | 3381.20 | 1.22 | 7350.23 |
| AND-direct ANF | 64 | 3597.62 | 5642.02 | 5642.16 | 2.03 | 3932.45 |
| FPRM-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| FPRM root beam | 64 | 2248.81 | 3886.62 | 3886.77 | 2.03 | 2481.64 |
| Affine-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| Resource-NMCTS | 64 | 2248.75 | 3885.66 | 3885.80 | 2.03 | 2481.52 |
| Profile-Resource-NMCTS | 64 | 2248.75 | 3885.66 | 3885.80 | 2.03 | 2481.52 |
