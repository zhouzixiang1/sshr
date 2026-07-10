# Method comparison @ n=3

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 3588 | 3672 | 128 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 3280 | 3232 | 128 | +11.98 | 0 | 0 | - | paper reference |
| paper_xag | 4760 | 7914 | 579 | -115.52 | 0 | 0 | - | paper reference |
| our_sshr_h | 2993 | 3191 | 1 | +13.10 | 255 | 0 | 0.00 |  |
| our_sshr_beam | 3812 | 3652 | 1 | +0.54 | 255 | 0 | 0.04 | width=20 |
| rule_pruned_ilp | 9472 | 8448 | 4 | -130.07 | 255 | 0 | 1.62 | keep=0.2 |
| lgb_pruned_ilp | 4445 | 4083 | 2 | -11.19 | 255 | 0 | 0.30 | keep=0.2 |
| gnn_pruned_ilp | 7372 | 6694 | 4 | -82.30 | 255 | 0 | 0.43 | keep=0.2 |

# Common-feasible subset (|S|=255) @ n=3

| Method | T | CNOT | Anc | gain_vs_paper_sshr_h_cnot (%) | n_evaluated | n_skipped | time_s | note |
|---|---|---|---|---|---|---|---|---|
| paper_sshr_h | 3588 | 3672 | 128 | +0.00 | 0 | 0 | - | paper reference |
| paper_sshr_i_cnot | 3280 | 3232 | 128 | +11.98 | 0 | 0 | - | paper reference |
| paper_xag | 4760 | 7914 | 579 | -115.52 | 0 | 0 | - | paper reference |
| our_sshr_h | 2993 | 3191 | 1 | +13.10 | 255 | 0 | 0.00 |  |
| our_sshr_beam | 3812 | 3652 | 1 | +0.54 | 255 | 0 | 0.04 | width=20 |
| rule_pruned_ilp | 9472 | 8448 | 4 | -130.07 | 255 | 0 | 1.62 | keep=0.2; common-subset|S|=255 |
| lgb_pruned_ilp | 4445 | 4083 | 2 | -11.19 | 255 | 0 | 0.30 | keep=0.2; common-subset|S|=255 |
| gnn_pruned_ilp | 7372 | 6694 | 4 | -82.30 | 255 | 0 | 0.43 | keep=0.2; common-subset|S|=255 |
