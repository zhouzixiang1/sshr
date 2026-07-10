# Paired Method Comparison

Target: `recursive boolean screen n18` from `/tmp/resource_nmcts_boolean_screen_deep_n18/raw_mega_highdim_resource.csv` method `and_boolean_linear_pair_screen_deep`.
Baseline: `old Resource-NMCTS n18` from `resource_nmcts_experiment/results/raw_mega_highdim_resource.csv` method `and_resource_nmcts`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 0 | 11 | 1 | 10060.667 | 6641.667 | +38.75% |
| CNOT | 12 | 0 | 11 | 1 | 15757.917 | 11382.417 | +26.74% |
| depth | 12 | 1 | 10 | 1 | 15758.000 | 11383.667 | +25.41% |
| peak_ancilla | 12 | 1 | 4 | 7 | 3.500 | 3.250 | -0.83% |
| score | 12 | 0 | 11 | 1 | 10991.327 | 7317.875 | +36.94% |
| time_s | 12 | 12 | 0 | 0 | 1.449 | 85.631 | -97.90% |
