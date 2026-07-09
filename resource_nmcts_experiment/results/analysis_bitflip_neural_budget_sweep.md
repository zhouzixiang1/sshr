# Bit-Flip Neural Budget Sweep

This analysis compares the learned bit-flip action prior with a matched no-prior search under tighter MCTS/candidate budgets.
It asks whether the neural scorer is more useful when the search budget is explicitly constrained; correctness still comes from the same symbolic and truth-table checks.

## Raw status counts

- pass: 2124

## Paired score summary

| budget | method | pairs | score W/L/T | mean score change | T W/L/T | runtime change |
|---|---|---:|---:|---:|---:|---:|
| top-8, 8/12 sim. | Affine-Resource-NMCTS | 177 | 42/0/135 | -1.28% | 19/0/158 | +36.60% |
| top-8, 8/12 sim. | Resource-NMCTS | 177 | 38/0/139 | -1.06% | 15/0/162 | +20.75% |
| top-8, 8/12 sim. | Pareto-Resource-NMCTS | 177 | 29/0/148 | -0.78% | 9/0/168 | +9.61% |
| top-12, 12/16 sim. | Affine-Resource-NMCTS | 177 | 42/0/135 | -1.28% | 19/0/158 | +34.21% |
| top-12, 12/16 sim. | Resource-NMCTS | 177 | 38/0/139 | -1.06% | 15/0/162 | +28.62% |
| top-12, 12/16 sim. | Pareto-Resource-NMCTS | 177 | 29/0/148 | -0.78% | 9/0/168 | +15.51% |
| top-24, 24/32 sim. | Affine-Resource-NMCTS | 177 | 42/0/135 | -1.47% | 22/0/155 | +91.22% |
| top-24, 24/32 sim. | Resource-NMCTS | 177 | 39/0/138 | -1.10% | 17/0/160 | +55.11% |
| top-24, 24/32 sim. | Pareto-Resource-NMCTS | 177 | 29/0/148 | -0.78% | 9/0/168 | +18.77% |

## Interpretation

- The rows keep function set, method, legality checks, and verification route fixed while changing only the learned-prior availability and search budget.
- This is a resource-constrained search-control test; it does not turn the learned prior into the main source of the paper's resource reduction.
- Runtime changes include Python model-evaluation overhead on this workstation and are therefore reported separately from resource quality.
