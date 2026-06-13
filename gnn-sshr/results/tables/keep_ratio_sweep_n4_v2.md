# keep_ratio sweep @ n=4

## CNOT_total by ratio x method

| ratio | rule | lgb | gnn |
|---|---|---|---|
| 0.10 | 10909 | 6802 | 6775 |
| 0.15 | 6501 | 5976 | 5928 |
| 0.20 | 5996 | 5604 | 5672 |
| 0.30 | 5757 | 5267 | 5345 |
| 0.50 | 5695 | 4939 | 5079 |


## n_skipped by ratio x method

| ratio | rule | lgb | gnn |
|---|---|---|---|
| 0.10 | 0 | 0 | 0 |
| 0.15 | 0 | 0 | 0 |
| 0.20 | 0 | 0 | 0 |
| 0.30 | 0 | 0 | 0 |
| 0.50 | 0 | 0 | 0 |


## Recommended operating point (min CNOT s.t. n_skipped <= 10)

| method | best_ratio | CNOT_total | T_total | Anc_total | n_skipped | wallclock_s |
|---|---|---|---|---|---|---|
| rule | 0.50 | 5695 | 10455 | 356 | 0 | 8.372 |
| lgb | 0.50 | 4939 | 6197 | 212 | 0 | 5.643 |
| gnn | 0.50 | 5079 | 6815 | 233 | 0 | 6.548 |
