# Paired Method Comparison

Target: `adaptive Boolean screen n20` from `results/raw_giga_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen_adaptive`.
Baseline: `single Boolean screen n20` from `results/raw_giga_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19535.333 | 20786.000 | -7.64% |
| CNOT | 6 | 5 | 0 | 1 | 30542.500 | 32492.500 | -6.65% |
| depth | 6 | 5 | 0 | 1 | 30542.500 | 32492.500 | -6.65% |
| peak_ancilla | 6 | 0 | 3 | 3 | 3.000 | 2.500 | +13.06% |
| score | 6 | 5 | 0 | 1 | 21331.242 | 22695.153 | -7.47% |
| time_s | 6 | 1 | 5 | 0 | 20.668 | 10.699 | +89.58% |
