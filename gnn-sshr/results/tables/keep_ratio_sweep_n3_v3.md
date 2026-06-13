# keep_ratio sweep @ n=3

## CNOT_total by ratio x method

| ratio | rule | lgb | gnn |
|---|---|---|---|
| 0.10 | 8850 | 6132 | 7544 |
| 0.15 | 8469 | 4465 | 6508 |
| 0.20 | 8448 | 4083 | 5372 |
| 0.30 | 8105 | 3635 | 3553 |
| 0.50 | 3439 | 3354 | 3232 |


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
| rule | 0.50 | 3439 | 3588 | 128 | 0 | 1.204 |
| lgb | 0.50 | 3354 | 3490 | 128 | 0 | 0.784 |
| gnn | 0.50 | 3232 | 3280 | 128 | 0 | 0.924 |
