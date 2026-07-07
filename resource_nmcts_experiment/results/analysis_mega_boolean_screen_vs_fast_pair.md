# Paired Method Comparison

Target: `boolean-linear screen` from `/tmp/resource_nmcts_boolean_screen_n18/raw_mega_highdim_resource.csv` method `and_boolean_linear_pair_screen`.
Baseline: `fast linear pair` from `resource_nmcts_experiment/results/raw_mega_highdim_resource.csv` method `and_fprm_linear_pair_fast`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 12 | 0 | 11 | 1 | 10389.333 | 6754.000 | +39.48% |
| CNOT | 12 | 0 | 10 | 2 | 16268.417 | 11566.833 | +28.11% |
| depth | 12 | 1 | 10 | 1 | 16268.500 | 11568.417 | +26.55% |
| peak_ancilla | 12 | 1 | 6 | 5 | 3.083 | 2.667 | +8.33% |
| score | 12 | 0 | 11 | 1 | 11349.056 | 7439.927 | +37.84% |
| time_s | 12 | 12 | 0 | 0 | 0.843 | 69.442 | -98.27% |
