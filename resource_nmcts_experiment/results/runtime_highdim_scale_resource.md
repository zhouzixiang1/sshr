# Runtime and Resource Tradeoff: highdim_scale_resource

Rows: 256; errors: 0; skipped: 0.

## Runtime by method

| method | completed | errors | skipped | median s | p95 s | max s | total completed s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct ANF | 32 | 0 | 0 | 0.025 | 0.047 | 0.053 | 0.9 |
| AND-direct ANF | 32 | 0 | 0 | 0.025 | 0.083 | 0.107 | 1.1 |
| FPRM-greedy | 32 | 0 | 0 | 1.466 | 44.433 | 46.581 | 281.8 |
| FPRM root beam | 32 | 0 | 0 | 3.033 | 59.293 | 70.221 | 376.7 |
| FPRM linear pair | 32 | 0 | 0 | 3.935 | 81.926 | 95.816 | 517.3 |
| FPRM linear pair deep | 32 | 0 | 0 | 4.019 | 79.418 | 95.601 | 511.6 |
| Resource-NMCTS | 32 | 0 | 0 | 12.531 | 203.821 | 232.943 | 1336.2 |
| Profile-Resource-NMCTS | 32 | 0 | 0 | 12.454 | 197.515 | 234.641 | 1331.8 |

## Mean resources by method

| method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 32 | 10591.75 | 4964.22 | 4964.28 | 1.16 | 10870.69 |
| AND-direct ANF | 32 | 5320.00 | 8339.88 | 8339.94 | 1.94 | 5812.77 |
| FPRM-greedy | 32 | 3315.62 | 5681.28 | 5681.34 | 1.94 | 3653.84 |
| FPRM root beam | 32 | 3302.50 | 5670.19 | 5670.25 | 1.94 | 3640.08 |
| FPRM linear pair | 32 | 3230.00 | 5545.50 | 5546.06 | 2.84 | 3562.05 |
| FPRM linear pair deep | 32 | 3226.00 | 5539.94 | 5540.50 | 3.00 | 3558.04 |
| Resource-NMCTS | 32 | 3226.00 | 5539.94 | 5540.50 | 3.00 | 3558.04 |
| Profile-Resource-NMCTS | 32 | 3226.00 | 5539.94 | 5540.50 | 3.00 | 3558.04 |
