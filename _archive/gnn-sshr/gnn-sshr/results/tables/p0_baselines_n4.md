# Method comparison @ n=4

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 7391 | 6540 | 308 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 6028 | 4696 | 212 | +28.20 | 0 | 0 | - | paper reference |
| paper_xag | 11692 | 19148 | 1459 | -192.78 | 0 | 0 | - | paper reference |
| our_sshr_h | 6726 | 6064 | 2 | +7.28 | 221 | 0 | 0.02 |  |
| our_sshr_beam | 7958 | 6711 | 4 | -2.61 | 221 | 0 | 0.36 | width=20 |
| rule_pruned_ilp | 10693 | 5996 | 5 | +8.32 | 221 | 0 | 5.16 | keep=0.2 |
| lgb_pruned_ilp | 8181 | 5604 | 3 | +14.31 | 221 | 0 | 3.14 | keep=0.2 |
| gnn_pruned_ilp | 9651 | 5819 | 4 | +11.02 | 221 | 0 | 4.27 | keep=0.2 |
