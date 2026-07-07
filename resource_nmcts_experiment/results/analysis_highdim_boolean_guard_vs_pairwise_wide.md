# Paired Method Comparison

Target: `boolean-guard Resource-NMCTS` from `/tmp/resource_nmcts_boolean_resource_n14/raw_highdim_neural_prior.csv` method `and_resource_nmcts`.
Baseline: `pairwise-wide Resource-NMCTS` from `resource_nmcts_experiment/results/raw_highdim_neural_prior_pairwise_wide.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 8 | 0 | 4 | 3282.000 | 3324.667 | -0.81% |
| CNOT | 12 | 9 | 0 | 3 | 5653.917 | 5737.833 | -0.95% |
| depth | 12 | 9 | 0 | 3 | 5655.750 | 5739.667 | -0.95% |
| peak_ancilla | 12 | 0 | 2 | 10 | 3.750 | 3.583 | +3.75% |
| score | 12 | 9 | 0 | 3 | 3622.222 | 3669.552 | -0.82% |
| time_s | 12 | 0 | 12 | 0 | 97.258 | 71.290 | +32.80% |
