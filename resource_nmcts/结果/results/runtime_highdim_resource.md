# Runtime and Resource Tradeoff: highdim_resource

Rows: 576; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 0 | 0 | 0.017 | 0.056 | 0.083 | 1.3 |
| AND-direct ANF | 64 | 0 | 0 | 0.019 | 0.042 | 0.066 | 1.4 |
| FPRM-greedy | 64 | 0 | 0 | 3.464 | 65.991 | 85.556 | 969.6 |
| FPRM root beam | 64 | 0 | 0 | 2.834 | 37.226 | 49.268 | 542.6 |
| FPRM linear pair | 64 | 0 | 0 | 2.574 | 30.760 | 41.593 | 460.7 |
| Affine-greedy | 64 | 0 | 0 | 6.647 | 107.887 | 129.176 | 1696.2 |
| Resource-NMCTS | 64 | 0 | 0 | 8.571 | 80.429 | 121.219 | 1418.0 |
| Profile-Resource-NMCTS | 64 | 0 | 0 | 9.294 | 84.226 | 122.849 | 1476.5 |
| Pareto-Resource-NMCTS | 64 | 0 | 0 | 67.788 | 300.019 | 300.414 | 7873.0 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 64 | 7159.38 | 3381.06 | 3381.20 | 1.22 | 7350.23 |
| AND-direct ANF | 64 | 3597.62 | 5642.02 | 5642.16 | 2.03 | 3932.45 |
| FPRM-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| FPRM root beam | 64 | 2248.81 | 3886.62 | 3886.77 | 2.03 | 2481.64 |
| FPRM linear pair | 64 | 2193.50 | 3790.83 | 3791.78 | 2.94 | 2422.51 |
| Affine-greedy | 64 | 2263.69 | 3894.78 | 3894.92 | 2.03 | 2496.97 |
| Resource-NMCTS | 64 | 2149.50 | 3724.91 | 3726.75 | 3.06 | 2374.91 |
| Profile-Resource-NMCTS | 64 | 2149.50 | 3724.91 | 3726.75 | 3.06 | 2374.91 |
| Pareto-Resource-NMCTS | 64 | 2148.81 | 3724.98 | 3726.72 | 3.06 | 2374.22 |
