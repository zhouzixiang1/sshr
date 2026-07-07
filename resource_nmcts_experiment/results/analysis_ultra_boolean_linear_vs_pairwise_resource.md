# Paired Method Comparison

Target: `boolean-linear-deep` from `/tmp/resource_nmcts_boolean_linear_n16/raw_ultra_highdim_resource.csv` method `and_fprm_boolean_linear_pair_deep`.
Baseline: `pairwise-wide Resource-NMCTS` from `resource_nmcts_experiment/results/raw_ultra_highdim_resource_pairwise_wide_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 12 | 4 | 8 | 3676.000 | 3697.000 | -0.21% |
| CNOT | 24 | 15 | 4 | 5 | 6360.292 | 6396.833 | -0.30% |
| depth | 24 | 15 | 4 | 5 | 6360.417 | 6396.958 | -0.30% |
| peak_ancilla | 24 | 2 | 2 | 20 | 3.417 | 3.417 | +0.35% |
| score | 24 | 14 | 6 | 4 | 4057.164 | 4080.352 | -0.22% |
| time_s | 24 | 24 | 0 | 0 | 27.417 | 111.771 | -72.31% |
