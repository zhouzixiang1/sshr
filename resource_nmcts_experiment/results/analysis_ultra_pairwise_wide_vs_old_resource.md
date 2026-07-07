# Paired Method Comparison

Target: `pairwise-wide Resource-NMCTS` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource_pairwise_wide_resource.csv` method `and_resource_nmcts`.
Baseline: `old Resource-NMCTS root-teacher` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 7 | 0 | 17 | 3697.000 | 3699.167 | -0.12% |
| CNOT | 24 | 9 | 1 | 14 | 6396.833 | 6404.417 | -0.13% |
| depth | 24 | 9 | 1 | 14 | 6396.958 | 6404.542 | -0.13% |
| peak_ancilla | 24 | 0 | 0 | 24 | 3.417 | 3.417 | +0.00% |
| score | 24 | 10 | 0 | 14 | 4080.352 | 4082.970 | -0.12% |
| time_s | 24 | 5 | 19 | 0 | 111.771 | 102.068 | +8.06% |
