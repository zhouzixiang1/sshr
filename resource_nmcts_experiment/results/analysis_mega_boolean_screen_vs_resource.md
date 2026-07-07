# Paired Method Comparison

Target: `boolean-linear screen` from `/tmp/resource_nmcts_boolean_screen_n18/raw_mega_highdim_resource.csv` method `and_boolean_linear_pair_screen`.
Baseline: `old Resource-NMCTS` from `resource_nmcts_experiment/results/raw_mega_highdim_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 0 | 12 | 0 | 10389.333 | 6641.667 | +44.43% |
| CNOT | 12 | 0 | 12 | 0 | 16268.417 | 11382.417 | +31.43% |
| depth | 12 | 1 | 11 | 0 | 16268.500 | 11383.667 | +30.10% |
| peak_ancilla | 12 | 2 | 0 | 10 | 3.083 | 3.250 | -10.42% |
| score | 12 | 0 | 12 | 0 | 11349.056 | 7317.875 | +42.45% |
| time_s | 12 | 12 | 0 | 0 | 0.843 | 85.631 | -98.48% |
