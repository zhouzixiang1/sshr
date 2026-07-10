# Paired Method Comparison

Target: `Resource-NMCTS n18` from `results/raw_mega_adaptive_screen_resource.csv` method `and_resource_nmcts`.
Baseline: `adaptive Boolean screen n18` from `results/raw_mega_adaptive_screen_resource.csv` method `and_boolean_linear_pair_screen_adaptive`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 11 | 0 | 1 | 6639.333 | 9767.000 | -24.91% |
| CNOT | 12 | 11 | 0 | 1 | 11380.917 | 15301.583 | -18.08% |
| depth | 12 | 10 | 1 | 1 | 11382.167 | 15301.667 | -16.58% |
| peak_ancilla | 12 | 3 | 1 | 8 | 3.333 | 3.500 | +3.89% |
| score | 12 | 11 | 0 | 1 | 7315.619 | 10670.935 | -23.85% |
| time_s | 12 | 0 | 12 | 0 | 226.179 | 4.390 | +7526.64% |
