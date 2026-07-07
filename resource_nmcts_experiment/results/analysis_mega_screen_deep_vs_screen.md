# Paired Method Comparison

Target: `recursive boolean screen n18` from `/tmp/resource_nmcts_boolean_screen_deep_n18/raw_mega_highdim_resource.csv` method `and_boolean_linear_pair_screen_deep`.
Baseline: `single boolean screen n18` from `resource_nmcts_experiment/results/raw_mega_boolean_linear_screen.csv` method `and_boolean_linear_pair_screen`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 11 | 0 | 1 | 10060.667 | 10389.333 | -4.08% |
| CNOT | 12 | 11 | 0 | 1 | 15757.917 | 16268.417 | -3.60% |
| depth | 12 | 11 | 0 | 1 | 15758.000 | 16268.500 | -3.60% |
| peak_ancilla | 12 | 0 | 5 | 7 | 3.500 | 3.083 | +10.28% |
| score | 12 | 11 | 0 | 1 | 10991.327 | 11349.056 | -3.99% |
| time_s | 12 | 1 | 11 | 0 | 1.449 | 0.843 | +58.81% |
