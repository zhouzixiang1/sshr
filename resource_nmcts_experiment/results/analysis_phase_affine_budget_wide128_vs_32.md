# Phase Affine Budget Comparison

Comparison: Affine-FPRM transform-budget 128 vs 32.  Negative mean relative values favor the wider target search.

| method | metric | pairs | W/L/T | target mean | baseline mean | mean relative |
|---|---|---:|---:|---:|---:|---:|
| phase_parity_affine_fprm_opt_score | score | 177 | 38/0/139 | 8.36 | 8.58 | -1.59% |
| phase_parity_affine_fprm_opt_rz1 | score_rz1 | 177 | 40/0/137 | 29.91 | 30.26 | -0.93% |
| phase_parity_affine_fprm_opt_tperrz30 | score_synth_tperrz30 | 177 | 43/0/134 | 665.31 | 668.57 | -0.60% |
| phase_parity_affine_fprm_opt_tperrz30 | rz_non_clifford | 177 | 3/0/174 | 21.36 | 21.45 | -0.29% |
| phase_parity_affine_fprm_opt_tperrz30 | rz_total | 177 | 35/2/140 | 25.39 | 26.14 | -2.39% |
| phase_parity_affine_fprm_opt_tperrz30 | CNOT | 177 | 37/2/138 | 83.23 | 85.32 | -1.74% |
| phase_parity_affine_fprm_opt_tperrz30 | depth | 177 | 41/2/134 | 108.62 | 111.46 | -1.93% |

## Interpretation

- Increasing the affine transform budget gives a monotone selected-result improvement for the matched rank metric because the budget-32 candidates are contained in the wider search space for the same seed and deterministic prefix.
- The strongest paper-facing row is the `score_synth_tperrz30` comparison for `phase_parity_affine_fprm_opt_tperrz30`: it isolates the phase/Rz cost proxy used against RevKit.
- This is still a logic-layer phase-polynomial search result, not a hardware-mapped rotation synthesis result.
