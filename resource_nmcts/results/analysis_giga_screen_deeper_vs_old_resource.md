# Paired Method Comparison

Target: `deeper recursive boolean screen` from `/tmp/resource_nmcts_boolean_screen_deeper_n20/raw_giga_highdim_resource.csv` method `and_boolean_linear_pair_screen_deeper`.
Baseline: `old Resource-NMCTS` from `resource_nmcts_experiment/results/raw_giga_highdim_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19535.333 | 20786.000 | -7.64% |
| CNOT | 6 | 5 | 0 | 1 | 30542.500 | 32492.500 | -6.65% |
| depth | 6 | 5 | 0 | 1 | 30542.500 | 32492.500 | -6.65% |
| peak_ancilla | 6 | 0 | 3 | 3 | 3.000 | 2.500 | +13.06% |
| score | 6 | 5 | 0 | 1 | 21331.242 | 22695.153 | -7.47% |
| time_s | 6 | 4 | 2 | 0 | 20.152 | 21.385 | -7.32% |
