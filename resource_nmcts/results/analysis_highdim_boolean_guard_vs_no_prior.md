# Paired Method Comparison

Target: `boolean-guard Resource-NMCTS` from `/tmp/resource_nmcts_boolean_resource_n14/raw_highdim_neural_prior.csv` method `and_resource_nmcts`.
Baseline: `no-prior Resource-NMCTS` from `resource_nmcts_experiment/results/raw_highdim_neural_prior_no_prior.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 8 | 0 | 4 | 3282.000 | 3326.667 | -0.87% |
| CNOT | 12 | 9 | 0 | 3 | 5653.917 | 5736.500 | -0.94% |
| depth | 12 | 9 | 0 | 3 | 5655.750 | 5738.333 | -0.94% |
| peak_ancilla | 12 | 0 | 3 | 9 | 3.750 | 3.500 | +5.42% |
| score | 12 | 9 | 0 | 3 | 3622.222 | 3671.295 | -0.86% |
| time_s | 12 | 0 | 12 | 0 | 97.258 | 23.261 | +247.75% |
