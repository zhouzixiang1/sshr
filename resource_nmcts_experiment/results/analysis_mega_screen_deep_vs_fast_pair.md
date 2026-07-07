# Paired Method Comparison

Target: `recursive boolean screen n18` from `/tmp/resource_nmcts_boolean_screen_deep_n18/raw_mega_highdim_resource.csv` method `and_boolean_linear_pair_screen_deep`.
Baseline: `fast pair guard n18` from `resource_nmcts_experiment/results/raw_mega_highdim_resource.csv` method `and_fprm_linear_pair_fast`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 1 | 11 | 0 | 10060.667 | 6754.000 | +34.07% |
| CNOT | 12 | 1 | 10 | 1 | 15757.917 | 11566.833 | +23.57% |
| depth | 12 | 2 | 10 | 0 | 15758.000 | 11568.417 | +22.01% |
| peak_ancilla | 12 | 1 | 6 | 5 | 3.500 | 2.667 | +22.22% |
| score | 12 | 1 | 11 | 0 | 10991.327 | 7439.927 | +32.57% |
| time_s | 12 | 12 | 0 | 0 | 1.449 | 69.442 | -97.58% |
