# STG Published Benchmark Counterpoint

This analysis compares the current logical-layer methods with the published
STG benchmark table for 4- and 5-input Boolean-function spectral representatives.
The STG rows are treated as a strong small-function optimum-library counterpoint,
not as a reproduced ROS SAT garbage-management run.

## Status counts

- pass: 22

- STG source: https://github.com/gmeuli/stg-benchmark
- benchmark functions: 54
- raw synthesis rows: 270
- correct usable rows: 270

## Key comparisons

| target | baseline | metric | items | W/L/T | mean change | target mean | baseline mean |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | STG T-count optimum | T | 54 | 0/40/14 | +88.58% | 25.78 | 13.19 |
| and_pareto_resource_nmcts | STG T-count optimum | T | 54 | 0/40/14 | +84.26% | 25.11 | 13.19 |
| and_pareto_resource_nmcts | STG qubit optimum | logical_qubits | 54 | 0/50/4 | +22.74% | 7.70 | 6.28 |
| and_pareto_resource_nmcts | direct_anf | score | 54 | 50/4/0 | -58.10% | 31.78 | 106.41 |
| and_pareto_resource_nmcts | and_direct_anf | score | 54 | 42/0/12 | -33.63% | 31.78 | 60.30 |
| and_pareto_resource_nmcts | and_resource_no_mcts | score | 54 | 19/0/35 | -3.01% | 31.78 | 33.15 |

## Interpretation

- Published STG optima remain much stronger on tiny spectral representatives.
- Resource-NMCTS and Pareto-Resource-NMCTS still substantially reduce the paper's
  own direct-ANF and AND-direct baselines on the same STG truth-table slice.
- The comparison should be cited as a small-function optimum-library boundary,
  not as evidence against the large-scale logical search contribution.
