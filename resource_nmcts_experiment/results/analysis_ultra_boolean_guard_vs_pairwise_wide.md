# Paired Method Comparison

Target: `boolean-guard Resource-NMCTS` from `/tmp/resource_nmcts_boolean_resource_n16/raw_ultra_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `pairwise-wide Resource-NMCTS` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource_pairwise_wide_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 12 | 0 | 12 | 3674.167 | 3697.000 | -0.34% |
| CNOT | 24 | 13 | 0 | 11 | 6358.833 | 6396.833 | -0.38% |
| depth | 24 | 13 | 0 | 11 | 6358.958 | 6396.958 | -0.38% |
| peak_ancilla | 24 | 1 | 1 | 22 | 3.417 | 3.417 | +0.00% |
| score | 24 | 14 | 0 | 10 | 4055.251 | 4080.352 | -0.34% |
| time_s | 24 | 0 | 24 | 0 | 133.068 | 111.771 | +22.80% |
