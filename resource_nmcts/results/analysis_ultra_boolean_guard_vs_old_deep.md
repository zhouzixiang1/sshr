# Paired Method Comparison

Target: `boolean-guard Resource-NMCTS` from `/tmp/resource_nmcts_boolean_resource_n16/raw_ultra_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `old deterministic deep` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource.csv` method `and_fprm_linear_pair_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 16 | 0 | 8 | 3674.167 | 3700.333 | -0.52% |
| CNOT | 24 | 17 | 1 | 6 | 6358.833 | 6404.500 | -0.50% |
| depth | 24 | 17 | 1 | 6 | 6358.958 | 6404.625 | -0.50% |
| peak_ancilla | 24 | 0 | 1 | 23 | 3.417 | 3.375 | +0.83% |
| score | 24 | 18 | 0 | 6 | 4055.251 | 4084.047 | -0.52% |
| time_s | 24 | 0 | 24 | 0 | 133.068 | 27.846 | +356.64% |
