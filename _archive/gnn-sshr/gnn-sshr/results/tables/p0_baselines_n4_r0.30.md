# Method comparison @ n=4

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 7391 | 6540 | 308 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 6028 | 4696 | 212 | +28.20 | 0 | 0 | - | paper reference |
| paper_xag | 11692 | 19148 | 1459 | -192.78 | 0 | 0 | - | paper reference |
| our_sshr_h | 6726 | 6064 | 2 | +7.28 | 221 | 0 | 0.02 |  |
| our_sshr_beam | 7958 | 6711 | 4 | -2.61 | 221 | 0 | 0.37 | width=20 |
| rule_pruned_ilp | 10455 | 5757 | 5 | +11.97 | 221 | 0 | 5.67 | keep=0.3 |
| lgb_pruned_ilp | 7099 | 5267 | 3 | +19.46 | 221 | 0 | 4.09 | keep=0.3 |
| gnn_pruned_ilp | 9056 | 5509 | 4 | +15.76 | 221 | 0 | 5.56 | keep=0.3 |
