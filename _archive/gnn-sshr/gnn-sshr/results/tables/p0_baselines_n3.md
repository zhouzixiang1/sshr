# Method comparison @ n=3

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 3588 | 3672 | 128 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 3280 | 3232 | 128 | +11.98 | 0 | 0 | - | paper reference |
| paper_xag | 4760 | 7914 | 579 | -115.52 | 0 | 0 | - | paper reference |
| our_sshr_h | 2993 | 3191 | 1 | +13.10 | 255 | 0 | 0.00 |  |
| our_sshr_beam | 3812 | 3652 | 1 | +0.54 | 255 | 0 | 0.05 | width=20 |
| rule_pruned_ilp | 0 | 24 | 0 | +99.35 | 15 | 240 | 0.15 | keep=0.2; skip=240 (ilp infeasible / no solution) |
| lgb_pruned_ilp | 3173 | 2899 | 1 | +21.05 | 191 | 64 | 0.31 | keep=0.2; skip=64 (ilp infeasible / no solution) |
| gnn_pruned_ilp | 3228 | 2993 | 3 | +18.49 | 166 | 89 | 0.49 | keep=0.2; skip=89 (ilp infeasible / no solution) |
