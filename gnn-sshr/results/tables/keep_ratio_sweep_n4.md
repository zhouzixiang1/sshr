# keep_ratio sweep @ n=4 (manually composed; eval/keep_ratio_sweep.py not yet present)

| method | keep_ratio | T | CNOT | Anc | n_evaluated | n_skipped | time_s |
|---|---|---|---|---|---|---|---|
| lgb_pruned_ilp | 0.10 | 11388 | 6802 | 6 | 221 | 0 | 1.38 |
| gnn_pruned_ilp | 0.10 | 33957 | 14645 | 11 | 221 | 0 | 1.17 |
| lgb_pruned_ilp | 0.15 | 8993 | 5976 | 5 | 221 | 0 | 1.96 |
| gnn_pruned_ilp | 0.15 | 16228 | 8493 | 8 | 221 | 0 | 2.73 |
| lgb_pruned_ilp | 0.20 | 8181 | 5604 | 3 | 221 | 0 | 3.14 |
| gnn_pruned_ilp | 0.20 | 9651 | 5819 | 4 | 221 | 0 | 4.27 |
| lgb_pruned_ilp | 0.30 | 7099 | 5267 | 3 | 221 | 0 | 4.09 |
| gnn_pruned_ilp | 0.30 | 9056 | 5509 | 4 | 221 | 0 | 5.56 |

Best CNOT per method: LGB=5267 @ 0.30; GNN=5509 @ 0.30. GNN/LGB=1.046 > 1.02 threshold.
