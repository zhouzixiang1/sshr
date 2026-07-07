# Paired Method Comparison

Target: `boolean-linear-deep` from `/tmp/resource_nmcts_boolean_linear_n16/raw_ultra_highdim_resource.csv` method `and_fprm_boolean_linear_pair_deep`.
Baseline: `old linear-pair-deep` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource.csv` method `and_fprm_linear_pair_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 15 | 3 | 6 | 3676.000 | 3700.333 | -0.39% |
| CNOT | 24 | 16 | 4 | 4 | 6360.292 | 6404.500 | -0.43% |
| depth | 24 | 16 | 4 | 4 | 6360.417 | 6404.625 | -0.43% |
| peak_ancilla | 24 | 1 | 2 | 21 | 3.417 | 3.375 | +1.18% |
| score | 24 | 17 | 3 | 4 | 4057.164 | 4084.047 | -0.39% |
| time_s | 24 | 12 | 12 | 0 | 27.417 | 27.846 | -0.19% |
