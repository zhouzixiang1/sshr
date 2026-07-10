# Method comparison @ n=4

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 7391 | 6540 | 308 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 6028 | 4696 | 212 | +28.20 | 0 | 0 | - | paper reference |
| paper_xag | 11692 | 19148 | 1459 | -192.78 | 0 | 0 | - | paper reference |
| our_sshr_h | 6726 | 6064 | 2 | +7.28 | 221 | 0 | 0.02 |  |
| our_sshr_beam | 7958 | 6711 | 4 | -2.61 | 221 | 0 | 0.36 | width=20 |
| rule_pruned_ilp | 23907 | 10909 | 7 | -66.80 | 221 | 0 | 1.13 | keep=0.1 |
| lgb_pruned_ilp | 11388 | 6802 | 6 | -4.01 | 221 | 0 | 1.38 | keep=0.1 |
| gnn_pruned_ilp | 33957 | 14645 | 11 | -123.93 | 221 | 0 | 1.17 | keep=0.1 |
