# Paired Method Comparison

Target: `recursive boolean screen` from `/tmp/resource_nmcts_boolean_screen_deep_n20/raw_giga_highdim_resource.csv` method `and_boolean_linear_pair_screen_deep`.
Baseline: `old Resource-NMCTS` from `resource_nmcts_experiment/results/raw_giga_highdim_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 20138.000 | 20786.000 | -4.62% |
| CNOT | 6 | 5 | 0 | 1 | 31480.500 | 32492.500 | -4.11% |
| depth | 6 | 5 | 0 | 1 | 31480.500 | 32492.500 | -4.11% |
| peak_ancilla | 6 | 0 | 2 | 4 | 2.833 | 2.500 | +7.50% |
| score | 6 | 5 | 0 | 1 | 21988.519 | 22695.153 | -4.52% |
| time_s | 6 | 6 | 0 | 0 | 12.732 | 21.385 | -40.73% |
