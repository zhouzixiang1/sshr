# Phase/Rz Cost Portfolio Sensitivity

This analysis keeps the internal X/CNOT/MCT emitters unchanged and
compares score-reranked internal portfolios against the RevKit
`oracle_synth` Rz-phase lower-bound baseline after charging each
non-Clifford Rz rotation lambda score units.

It is a logic-layer sensitivity study, not exact Clifford+T rotation
synthesis and not hardware mapping.

## Portfolio Definitions

- `resource_nmcts_family`: and_resource_nmcts, and_pareto_resource_nmcts, and_fprm_polarity_archive
- `traditional_baseline_family`: direct_anf, and_direct_anf, and_cube_beam, and_esop_milp, sshr_h
- `all_internal_score_portfolio`: and_resource_nmcts, and_pareto_resource_nmcts, and_fprm_polarity_archive, direct_anf, and_direct_anf, and_cube_beam, and_esop_milp, sshr_h, and_mcts_factor, and_affine_nmcts

## Summary

| portfolio | lambda | W/L/T | mean relative | median break-even | covered | mean selected time | mean run-all time |
|---|---:|---:|---:|---:|---:|---:|---:|
| resource_nmcts_family | 0 | 6/171/0 | +711.60% | 0.80 | 6/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 0.25 | 8/169/0 | +140.92% | 0.80 | 8/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 0.5 | 16/161/0 | +45.16% | 0.80 | 16/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 0.75 | 66/111/0 | +4.64% | 0.80 | 66/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 1 | 157/20/0 | -17.89% | 0.80 | 157/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 1.5 | 177/0/0 | -42.26% | 0.80 | 177/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 2 | 177/0/0 | -55.24% | 0.80 | 177/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 4 | 177/0/0 | -75.84% | 0.80 | 177/177 | 2.4724 | 4.5492 |
| resource_nmcts_family | 10 | 177/0/0 | -88.94% | 0.80 | 177/177 | 2.4724 | 4.5492 |
| traditional_baseline_family | 0 | 6/171/0 | +978.71% | 1.05 | 6/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 0.25 | 8/169/0 | +218.08% | 1.05 | 8/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 0.5 | 9/168/0 | +91.02% | 1.05 | 9/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 0.75 | 15/162/0 | +37.37% | 1.05 | 15/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 1 | 80/97/0 | +7.58% | 1.05 | 80/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 1.5 | 160/17/0 | -24.59% | 1.05 | 160/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 2 | 176/1/0 | -41.71% | 1.05 | 176/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 4 | 177/0/0 | -68.85% | 1.05 | 177/177 | 1.4451 | 3.8339 |
| traditional_baseline_family | 10 | 177/0/0 | -86.09% | 1.05 | 177/177 | 1.4451 | 3.8339 |
| all_internal_score_portfolio | 0 | 6/171/0 | +711.04% | 0.80 | 6/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 0.25 | 8/169/0 | +140.74% | 0.80 | 8/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 0.5 | 16/161/0 | +45.05% | 0.80 | 16/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 0.75 | 66/111/0 | +4.55% | 0.80 | 66/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 1 | 157/20/0 | -17.96% | 0.80 | 157/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 1.5 | 177/0/0 | -42.31% | 0.80 | 177/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 2 | 177/0/0 | -55.28% | 0.80 | 177/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 4 | 177/0/0 | -75.87% | 0.80 | 177/177 | 1.9820 | 9.9754 |
| all_internal_score_portfolio | 10 | 177/0/0 | -88.95% | 0.80 | 177/177 | 1.9820 | 9.9754 |

## Winner Counts

- `resource_nmcts_family`: and_pareto_resource_nmcts:115;and_fprm_polarity_archive:62
- `traditional_baseline_family`: and_esop_milp:90;and_cube_beam:52;sshr_h:29;and_direct_anf:5;direct_anf:1
- `all_internal_score_portfolio`: and_affine_nmcts:93;and_fprm_polarity_archive:44;and_pareto_resource_nmcts:30;sshr_h:4;and_esop_milp:3;and_cube_beam:2;direct_anf:1

## Interpretation Boundary

- A lower lambda means a more favorable interpretation of RevKit's non-Clifford Rz rotations.
- The selected internal circuit remains the existing verified bit-flip oracle circuit.
- A future phase/Rz-aware emitter should replace this proxy by exact or approximate rotation synthesis costs.
