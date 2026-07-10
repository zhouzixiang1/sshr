# keep_ratio sweep @ n=5

## CNOT_total by ratio x method

| ratio | rule | lgb | gnn |
|---|---|---|---|
| 0.05 | 6384 | 2682 | 2698 |
| 0.10 | 6384 | 2658 | 2666 |
| 0.15 | 6384 | 2658 | 2666 |
| 0.20 | 6384 | 2658 | 2658 |


## n_skipped by ratio x method

| ratio | rule | lgb | gnn |
|---|---|---|---|
| 0.05 | 0 | 0 | 0 |
| 0.10 | 0 | 0 | 0 |
| 0.15 | 0 | 0 | 0 |
| 0.20 | 0 | 0 | 0 |


## Recommended operating point (min CNOT s.t. n_skipped <= 10)

| method | best_ratio | CNOT_total | T_total | Anc_total | n_skipped | wallclock_s |
|---|---|---|---|---|---|---|
| rule | 0.05 | 6384 | 14592 | 912 | 0 | 2.570 |
| lgb | 0.10 | 2658 | 5396 | 268 | 0 | 3.290 |
| gnn | 0.20 | 2658 | 5379 | 267 | 0 | 3.691 |
