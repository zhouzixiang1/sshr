# Paired Method Comparison

Target: `pairwise-wide Resource-NMCTS` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource_pairwise_wide_resource.csv` method `and_resource_nmcts`.
Baseline: `deterministic recursive linear-pair` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource.csv` method `and_fprm_linear_pair_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 9 | 0 | 15 | 3697.000 | 3700.333 | -0.18% |
| CNOT | 24 | 9 | 1 | 14 | 6396.833 | 6404.500 | -0.12% |
| depth | 24 | 9 | 1 | 14 | 6396.958 | 6404.625 | -0.12% |
| peak_ancilla | 24 | 0 | 1 | 23 | 3.417 | 3.375 | +1.04% |
| score | 24 | 10 | 0 | 14 | 4080.352 | 4084.047 | -0.18% |
| time_s | 24 | 0 | 24 | 0 | 111.771 | 27.846 | +274.75% |
