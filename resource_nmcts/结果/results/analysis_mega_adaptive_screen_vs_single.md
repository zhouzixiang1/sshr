# Paired Method Comparison

Target: `adaptive Boolean screen n18` from `results/raw_mega_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen_adaptive`.
Baseline: `single Boolean screen n18` from `results/raw_mega_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 11 | 0 | 1 | 9767.000 | 10389.333 | -6.58% |
| CNOT | 12 | 11 | 0 | 1 | 15301.583 | 16268.417 | -5.99% |
| depth | 12 | 11 | 0 | 1 | 15301.667 | 16268.500 | -5.99% |
| peak_ancilla | 12 | 0 | 5 | 7 | 3.500 | 3.083 | +10.28% |
| score | 12 | 11 | 0 | 1 | 10670.935 | 11349.056 | -6.47% |
| time_s | 12 | 0 | 12 | 0 | 4.390 | 0.815 | +350.96% |
