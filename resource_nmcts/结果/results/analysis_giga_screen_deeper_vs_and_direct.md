# Paired Method Comparison

Target: `deeper recursive boolean screen` from `/tmp/resource_nmcts_boolean_screen_deeper_n20/raw_giga_highdim_resource.csv` method `and_boolean_linear_pair_screen_deeper`.
Baseline: `AND-direct ANF` from `resource_nmcts_experiment/results/raw_giga_highdim_resource.csv` method `and_direct_anf`.

Rows are matched by function name and include only correct, non-skipped, non-error results.
Negative mean relative values favor the target.

| metric | pairs | target wins | target losses | ties | target mean | baseline mean | mean relative |
|---|---:|---:|---:|---:|---:|---:|---:|
| T | 6 | 5 | 0 | 1 | 19535.333 | 21516.667 | -12.24% |
| CNOT | 6 | 5 | 0 | 1 | 30542.500 | 33635.667 | -11.02% |
| depth | 6 | 5 | 0 | 1 | 30542.500 | 33635.667 | -11.02% |
| peak_ancilla | 6 | 0 | 5 | 1 | 3.000 | 1.667 | +69.44% |
| score | 6 | 5 | 0 | 1 | 21331.242 | 23491.152 | -11.80% |
| time_s | 6 | 0 | 6 | 0 | 20.152 | 10.492 | +92.00% |
