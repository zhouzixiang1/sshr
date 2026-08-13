# Bit-Flip Learned-Prior Feature Gate

This derived audit deploys the learned prior only when `6 <= anf_terms <= 23`.
The gate uses only the input ANF term count, which is available before MCTS candidate expansion.

It is a static deployment rule over the existing paired rows, not an independent generalization proof.

## Status counts

- pass: 13

## Aggregate rows

| budget | pairs | learned enabled | score W/L/T | always-learned W/L/T | mean score change | time change | always-learned time | overhead reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| top-8, 8/12 sim. | 531 | 393 | 109/0/422 | 109/0/422 | -1.04% | +17.64% | +22.32% | +20.98% |
| top-12, 12/16 sim. | 531 | 393 | 109/0/422 | 109/0/422 | -1.04% | +23.91% | +26.12% | +8.45% |
| top-24, 24/32 sim. | 531 | 393 | 110/0/421 | 110/0/421 | -1.11% | +46.81% | +55.03% | +14.95% |
| all budgets | 1593 | 1179 | 328/0/1265 | 328/0/1265 | -1.07% | +29.45% | +34.49% | +14.61% |

## Interpretation

- The ANF-term gate keeps every always-learned score win in the audited rows while skipping learned-prior evaluation on rows where it ties no-prior.
- It preserves the same mean score change as always-learned deployment and lowers measured Python runtime overhead.
- Because the interval is selected from existing evidence, it is reported as a bounded deployment audit rather than a held-out policy claim.

## Method-budget rows

| budget | method | pairs | learned enabled | score W/L/T | overhead reduction |
|---|---|---:|---:|---:|---:|
| top-8, 8/12 sim. | Affine-Resource-NMCTS | 177 | 131 | 42/0/135 | +33.57% |
| top-8, 8/12 sim. | Resource-NMCTS | 177 | 131 | 38/0/139 | +8.04% |
| top-8, 8/12 sim. | Pareto-Resource-NMCTS | 177 | 131 | 29/0/148 | +1.00% |
| top-12, 12/16 sim. | Affine-Resource-NMCTS | 177 | 131 | 42/0/135 | +11.06% |
| top-12, 12/16 sim. | Resource-NMCTS | 177 | 131 | 38/0/139 | +7.00% |
| top-12, 12/16 sim. | Pareto-Resource-NMCTS | 177 | 131 | 29/0/148 | +5.38% |
| top-24, 24/32 sim. | Affine-Resource-NMCTS | 177 | 131 | 42/0/135 | +19.25% |
| top-24, 24/32 sim. | Resource-NMCTS | 177 | 131 | 39/0/138 | +8.93% |
| top-24, 24/32 sim. | Pareto-Resource-NMCTS | 177 | 131 | 29/0/148 | +11.68% |
