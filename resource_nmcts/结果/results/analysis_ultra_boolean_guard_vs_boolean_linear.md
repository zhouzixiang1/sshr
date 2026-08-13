# Paired Method Comparison

Target: `boolean-guard Resource-NMCTS` from `/tmp/resource_nmcts_boolean_resource_n16/raw_ultra_highdim_resource.csv` method `and_resource_nmcts`.
Baseline: `boolean-linear-deep` from `/tmp/resource_nmcts_boolean_linear_n16/raw_ultra_highdim_resource.csv` method `and_fprm_boolean_linear_pair_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 24 | 4 | 0 | 20 | 3674.167 | 3676.000 | -0.13% |
| CNOT | 24 | 4 | 2 | 18 | 6358.833 | 6360.292 | -0.07% |
| depth | 24 | 4 | 2 | 18 | 6358.958 | 6360.417 | -0.07% |
| peak_ancilla | 24 | 1 | 1 | 22 | 3.417 | 3.417 | +0.35% |
| score | 24 | 6 | 0 | 18 | 4055.251 | 4057.164 | -0.12% |
| time_s | 24 | 0 | 24 | 0 | 133.068 | 27.417 | +358.30% |
