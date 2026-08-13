# Paired Method Comparison

Target: `depth2 Boolean screen` from `results/raw_giga_screen_adaptive_resource.csv` method `and_boolean_linear_pair_screen_deeper`.
Baseline: `depth1 Boolean screen` from `results/raw_giga_screen_adaptive_resource.csv` method `and_boolean_linear_pair_screen_deep`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19542.000 | 20138.000 | -3.15% |
| CNOT | 6 | 5 | 0 | 1 | 30553.000 | 31480.500 | -2.61% |
| depth | 6 | 5 | 0 | 1 | 30553.000 | 31480.500 | -2.61% |
| peak_ancilla | 6 | 0 | 1 | 5 | 3.000 | 2.833 | +5.56% |
| score | 6 | 5 | 0 | 1 | 21338.525 | 21988.519 | -3.07% |
| time_s | 6 | 1 | 5 | 0 | 14.583 | 12.246 | +15.49% |
